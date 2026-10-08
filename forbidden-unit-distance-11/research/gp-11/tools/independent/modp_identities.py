#!/usr/bin/env python3
"""GP-11 check 6: every refutation identity, with Python integer arithmetic.

Adapted from GP-10 modp_identities.py, adding system claims, proof-tree field
equalities/row spaces, bounded multiprocessing, deterministic record seeds,
shards, streaming, and paired red controls. Runs under /usr/bin/python3 -S.
Sturm counts, selected-root signs and TU gadget lemmas are not identities.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time

from independent_core import (Failure, adjacency, bounded_map, decode_g6, integer,
    keys, lines, rational, record, require, shard, write_json, source_hashes, guard_outputs)

PRIMES = ((1 << 61) - 1, (1 << 127) - 1)
POLY = {"null", "real", "null-dag", "real-dag"}
ALL_REFUTATIONS = POLY | {"tree", "tu", "sub"}


class SparseEvaluator:
    def __init__(self, nv, canonical=False):
        self.nv, self.canonical = nv, canonical
        self.compiled, self.rats = {}, {}
        self.max_degree = 0

    def compile(self, poly):
        key = id(poly)
        if key in self.compiled:
            return self.compiled[key]
        require(isinstance(poly, list), "sparse_schema", "polynomial must be a term list")
        terms, seen, previous = [], set(), None
        for term in poly:
            require(isinstance(term, list) and len(term) == 2, "sparse_schema", "expected [coefficient, exponents]")
            coeff, exponents = term
            require(isinstance(exponents, list) and len(exponents) == self.nv
                    and all(integer(e) and e >= 0 for e in exponents),
                    "sparse_exponents", "wrong exponent count or noninteger/negative exponent")
            ex = tuple(exponents)
            require(ex not in seen, "sparse_duplicate", "duplicate exponent vector")
            seen.add(ex)
            if coeff not in self.rats:
                self.rats[coeff] = rational(coeff)
            q = self.rats[coeff]
            if self.canonical:
                require(q != 0 and (previous is None or previous < ex),
                        "sparse_noncanonical", "DAG terms must be nonzero and increasing lexicographically")
            previous = ex
            self.max_degree = max(self.max_degree, sum(ex))
            terms.append((q.numerator, q.denominator, tuple((i, e) for i, e in enumerate(ex) if e)))
        self.compiled[key] = terms
        return terms

    def point(self, prime, values):
        residues, powers, polys = {}, {}, {}

        def rat(q):
            pair = (q.numerator, q.denominator)
            if pair not in residues:
                require(q.denominator % prime, "modular_denominator", "rational denominator vanishes modulo prime")
                residues[pair] = q.numerator % prime * pow(q.denominator, -1, prime) % prime
            return residues[pair]

        def ev(poly):
            key = id(poly)
            if key in polys:
                return polys[key]
            total = 0
            for numerator, denominator, ex in self.compile(poly):
                pair = numerator, denominator
                if pair not in residues:
                    require(denominator % prime, "modular_denominator", "rational denominator vanishes modulo prime")
                    residues[pair] = numerator % prime * pow(denominator, -1, prime) % prime
                value = residues[pair]
                for i, exponent in ex:
                    pk = i, exponent
                    if pk not in powers:
                        powers[pk] = pow(values[i], exponent, prime)
                    value = value * powers[pk] % prime
                total = (total + value) % prime
            polys[key] = total
            return total
        return ev, rat


def polynomial_identities(rec, rng, points):
    c, t = rec["cert"], rec["cert"]["type"]
    dag, real = t.endswith("-dag"), t.startswith("real")
    required = {"type", "frame", "sat", "rows" if dag else "cofactors"} | ({"f"} if real else set())
    optional = ({"sturm", "sos"} if real else set()) | ({"system"} if not dag else set())
    keys(c, required, optional)
    require(not real or (("sturm" in c) != ("sos" in c)), "real_proof", "real certificate needs exactly one of sturm or sos")
    n, edges = decode_g6(rec["g6"])
    frame = c["frame"]
    require(isinstance(frame, list) and len(frame) == 2 and all(integer(v) and 0 <= v < n for v in frame)
            and tuple(sorted(frame)) in edges, "frame", "frame is not an actual edge")
    a, b = frame
    sat = c["sat"]
    require(isinstance(sat, list), "saturation", "saturation must be a pair list")
    seen = set()
    for pair in sat:
        require(isinstance(pair, list) and len(pair) == 2 and all(integer(v) for v in pair)
                and 0 <= pair[0] < pair[1] < n and tuple(pair) not in seen,
                "saturation", "invalid, reversed or duplicate saturation pair")
        seen.add(tuple(pair))
    names = [f"{z}_{i}" for i in range(n) if i not in (a, b) for z in ("x", "y")]
    names += [f"t_{k}" for k in range(len(sat))]
    evaluator = SparseEvaluator(len(names), dag)
    if dag:
        rows = c["rows"]
        require(isinstance(rows, list) and 1 <= len(rows) <= 256, "dag_rows", "expected 1..256 rows")
        for row in rows:
            keys(row, {"poly", "cofactors"})
    else:
        rows = []
    idents = Counter()
    for p in PRIMES:
        for _ in range(points):
            values = [rng.randrange(p) for _ in names]
            named = dict(zip(names, values))
            ev, rat = evaluator.point(p, values)

            def x(i):
                return 0 if i == a else 1 if i == b else named[f"x_{i}"]

            def y(i):
                return 0 if i in (a, b) else named[f"y_{i}"]

            def d2(u, v):
                return ((x(u) - x(v)) ** 2 + (y(u) - y(v)) ** 2) % p

            generators = {f"e:{u},{v}": (d2(u, v) - 1) % p
                          for u, v in edges if (u, v) != tuple(sorted(frame))}
            generators.update({f"s:{u},{v}": (named[f"t_{k}"] * d2(u, v) - 1) % p
                               for k, (u, v) in enumerate(sat)})
            if "system" in c:
                require(isinstance(c["system"], dict) and set(c["system"]) == set(generators),
                        "system_keys", "supplied system does not have exactly the regenerated keys")
                for key, value in generators.items():
                    require(ev(c["system"][key]) == value, "system_identity", f"regenerated system differs at {key}")
                    idents["system"] += 1

            def combination(cofactors, aux):
                require(isinstance(cofactors, dict), "cofactor_schema", "cofactors must be a source dictionary")
                total = 0
                for key, poly in cofactors.items():
                    if key in generators:
                        source = generators[key]
                    elif dag and re.fullmatch(r"aux:(0|[1-9][0-9]*)", key):
                        j = int(key[4:])
                        require(j < len(aux), "dag_reference", f"unknown or forward source {key}")
                        source = aux[j]
                    else:
                        raise Failure("cofactor_source", f"unknown source {key}")
                    total = (total + ev(poly) * source) % p
                return total

            target = ev(c["f"]) if real else 1
            if dag:
                aux = []
                for k, row in enumerate(rows):
                    value = ev(row["poly"])
                    require(combination(row["cofactors"], aux) == value,
                            "row_identity", f"row {k} identity fails", row=k, prime=str(p))
                    aux.append(value)
                    idents["dag_row"] += 1
                require(aux[-1] == target, "last_target", "last row is not the required target", prime=str(p))
                idents["dag_target"] += 1
            else:
                require(combination(c["cofactors"], []) == target,
                        "cofactor_identity", "cofactor identity fails", prime=str(p))
                idents["cofactor"] += 1
            if real and "sos" in c:
                s = c["sos"]
                keys(s, {"c", "squares"})
                constant = rational(s["c"])
                require(constant > 0 and isinstance(s["squares"], list), "sos_positive", "SOS constant must be positive")
                value = rat(constant)
                for square in s["squares"]:
                    require(isinstance(square, list) and len(square) == 2, "sos_schema", "expected weight and square")
                    weight, poly = rational(square[0]), square[1]
                    require(weight > 0, "sos_positive", "SOS weight must be positive")
                    value = (value + rat(weight) * ev(poly) ** 2) % p
                require(value == target, "sos_identity", "SOS identity fails", prime=str(p))
                idents["sos"] += 1
            if real and "sturm" in c:
                require(c["sturm"] in named, "sturm_variable", "Sturm variable is absent from the regenerated system")
                var = names.index(c["sturm"])
                terms = evaluator.compile(c["f"])
                require(any(num != 0 for num, den, ex in terms)
                        and all(num == 0 or all(i == var for i, exp in ex) for num, den, ex in terms),
                        "sturm_support", "Sturm target must be nonzero and univariate")
    return dict(idents), evaluator.max_degree


class ModularField:
    """Fp[T]/(m), then complex pairs (re,im). Only Python integers.

    No assumption that m stays irreducible mod p. A nonunit inversion is a
    reported failure, never silently skipped. True equalities are tested as
    coefficient vectors, stronger than evaluating their reduced polynomials.
    """
    def __init__(self, modulus, p):
        self.p = p
        self.modulus = tuple(self.rat(q) for q in modulus)
        self.d = len(modulus) - 1
        require(self.modulus[-1], "tree_modulus", "leading coefficient vanishes modulo prime")
        self.zero = (tuple([0] * self.d), tuple([0] * self.d))
        self.one = self.scalar(1)

    def rat(self, q):
        require(q.denominator % self.p, "modular_denominator", "tree rational denominator vanishes modulo prime")
        return q.numerator % self.p * pow(q.denominator, -1, self.p) % self.p

    def reduce(self, a):
        a = list(a)
        while len(a) > self.d:
            k = len(a) - self.d - 1
            c = a[-1] * pow(self.modulus[-1], -1, self.p) % self.p
            for i, v in enumerate(self.modulus):
                a[k + i] = (a[k + i] - c * v) % self.p
            a.pop()
        return tuple(a + [0] * (self.d - len(a)))

    def real(self, value):
        if isinstance(value, list):
            require(len(value) <= self.d, "tree_element", "tree field element exceeds the field degree")
            return self.reduce([self.rat(rational(x, tree=True)) for x in value])
        return self.reduce([self.rat(rational(value, tree=True))])

    def element(self, value):
        if isinstance(value, dict):
            keys(value, {"re", "im"})
            return self.real(value["re"]), self.real(value["im"])
        return self.real(value), tuple([0] * self.d)

    def scalar(self, n):
        return self.reduce([n % self.p]), tuple([0] * self.d)

    def radd(self, a, b):
        return tuple((x + y) % self.p for x, y in zip(a, b))

    def rneg(self, a):
        return tuple(-x % self.p for x in a)

    def rmul(self, a, b):
        out = [0] * (2 * self.d - 1)
        for i, x in enumerate(a):
            if x:
                for j, y in enumerate(b):
                    out[i + j] = (out[i + j] + x * y) % self.p
        return self.reduce(out)

    def rinv(self, a):
        # Solve the multiplication-by-a matrix against 1. This avoids any
        # external polynomial implementation, even for extension fields.
        columns = [self.rmul(a, self.reduce([0] * k + [1])) for k in range(self.d)]
        mat = [[columns[j][i] for j in range(self.d)] + [int(i == 0)] for i in range(self.d)]
        for k in range(self.d):
            pivot = next((i for i in range(k, self.d) if mat[i][k]), None)
            require(pivot is not None, "tree_modular_nonunit", "tree elimination needs a nonunit modulo prime")
            mat[k], mat[pivot] = mat[pivot], mat[k]
            factor = pow(mat[k][k], -1, self.p)
            mat[k] = [x * factor % self.p for x in mat[k]]
            for i in range(self.d):
                if i != k and mat[i][k]:
                    f = mat[i][k]
                    mat[i] = [(x - f * y) % self.p for x, y in zip(mat[i], mat[k])]
        return tuple(row[-1] for row in mat)

    def add(self, a, b):
        return self.radd(a[0], b[0]), self.radd(a[1], b[1])

    def neg(self, a):
        return self.rneg(a[0]), self.rneg(a[1])

    def sub(self, a, b):
        return self.add(a, self.neg(b))

    def mul(self, a, b):
        return (self.radd(self.rmul(a[0], b[0]), self.rneg(self.rmul(a[1], b[1]))),
                self.radd(self.rmul(a[0], b[1]), self.rmul(a[1], b[0])))

    def norm(self, a):
        return self.radd(self.rmul(a[0], a[0]), self.rmul(a[1], a[1])), self.zero[1]

    def inverse(self, a):
        scale = self.rinv(self.norm(a)[0])
        return self.rmul(a[0], scale), self.rneg(self.rmul(a[1], scale))

    def rref(self, rows, n):
        require(all(len(row) == n for row in rows), "tree_matrix", "tree A has wrong column count")
        mat, rank = [list(row) for row in rows], 0
        for column in range(n):
            pivot = next((i for i in range(rank, len(mat)) if mat[i][column] != self.zero), None)
            if pivot is None:
                continue
            mat[rank], mat[pivot] = mat[pivot], mat[rank]
            inv = self.inverse(mat[rank][column])
            mat[rank] = [self.mul(x, inv) for x in mat[rank]]
            for i in range(len(mat)):
                if i != rank and mat[i][column] != self.zero:
                    f = mat[i][column]
                    mat[i] = [self.sub(x, self.mul(f, y)) for x, y in zip(mat[i], mat[rank])]
            rank += 1
            if rank == len(mat):
                break
        return tuple(tuple(row) for row in mat[:rank])


def tree_identities(rec, rng, points):
    cert = rec["cert"]
    keys(cert, {"type", "witness"})
    witness = cert["witness"]
    keys(witness, {"field", "tree"})
    keys(witness["field"], {"minpoly", "interval"})
    modulus = witness["field"]["minpoly"]
    require(isinstance(modulus, list) and len(modulus) >= 2, "tree_modulus", "invalid tree minimal polynomial")
    modulus = [rational(x, tree=True) for x in modulus]
    require(modulus[-1] != 0, "tree_modulus", "zero leading coefficient")
    n, initial_edges = decode_g6(rec["g6"])
    idents = Counter()
    for p in PRIMES:
        field = ModularField(modulus, p)

        def test(a, b, code, reason):
            diff = field.sub(a, b)
            # Random evaluation of each coefficient remainder, followed by the
            # stronger all-coefficients test. Field identities are modulo m.
            for _ in range(points):
                value = rng.randrange(p)
                for part in diff:
                    acc = 0
                    for coefficient in reversed(part):
                        acc = (acc * value + coefficient) % p
                    require(acc == 0, code, reason, prime=str(p))
            require(diff == field.zero, code, reason, prime=str(p))
            idents[code] += points

        def displacement(pair):
            require(isinstance(pair, list) and len(pair) == 2
                    and all(integer(v) and 0 <= v < n for v in pair) and pair[0] != pair[1],
                    "tree_pair", "invalid directed pair")
            row = [field.zero] * n
            row[pair[0]], row[pair[1]] = field.one, field.neg(field.one)
            return row

        def relation(pairs, coefficients):
            row = [field.zero] * n
            for pair, coef in zip(pairs, coefficients):
                row = [field.add(x, field.mul(coef, y)) for x, y in zip(row, displacement(pair))]
            return row

        def rhombi(edges):
            adj, result, seen = adjacency(n, edges), [], set()
            for a in range(n):
                for c in range(a + 1, n):
                    common = sorted(adj[a] & adj[c])
                    for j, b in enumerate(common):
                        for d in common[j + 1:]:
                            cycle = frozenset({tuple(sorted(e)) for e in ((a, b), (b, c), (c, d), (d, a))})
                            if cycle not in seen:
                                seen.add(cycle)
                                result.append(relation([[a, b], [c, d]], [field.one, field.one]))
            return result

        def visit(node, expected_edges, expected_rows, path):
            keys(node, {"edges", "A", "move", "children"})
            require(isinstance(node["edges"], list), "tree_edges", "node edges must be a list")
            edges = set()
            for pair in node["edges"]:
                displacement(pair)
                edges.add(tuple(sorted(pair)))
            require(len(edges) == len(node["edges"]) and edges == expected_edges,
                    "tree_state", f"wrong graph state at {path}")
            require(isinstance(node["A"], list), "tree_matrix", "A must be a matrix")
            matrix = [[field.element(x) for x in row] for row in node["A"]]
            normal = field.rref(matrix, n)
            require(normal == field.rref(expected_rows, n), "tree_rowspace",
                    f"regenerated constraint row space differs at {path}", prime=str(p))
            idents["tree_rowspace"] += points
            move, children = node["move"], node["children"]
            require(isinstance(move, dict) and isinstance(children, list), "tree_move", "invalid move or children")
            kind = move.get("kind")

            def belongs(row):
                require(field.rref(list(normal) + [row], n) == normal, "tree_relation",
                        f"move relation outside A at {path}", prime=str(p))
                idents["tree_relation"] += points

            if kind == "L1a":
                keys(move, {"kind", "pair"})
                belongs(displacement(move["pair"]))
                require(not children, "tree_children", "L1a must be a leaf")
            elif kind in {"L1b", "L2"}:
                keys(move, {"kind", "edges", "omega"})
                pairs = move["edges"]
                require(isinstance(pairs, list) and len(pairs) == 2, "tree_move", "expected two directed pairs")
                omega = field.element(move["omega"])
                belongs(relation(pairs, [field.one, field.neg(omega)]))
                if kind == "L1b":
                    require(all(tuple(sorted(e)) in edges for e in pairs) and not children,
                            "tree_move", "L1b needs two edges and no children")
                    # Inequality at the selected real root is outside check 6.
                else:
                    test(field.norm(omega), field.one, "tree_unit_ratio", f"L2 ratio is not unit at {path}")
                    missing = {tuple(sorted(e)) for e in pairs} - edges
                    require(len(missing) == 1 and len(children) == 1
                            and sum(tuple(sorted(e)) in edges for e in pairs) == 1,
                            "tree_move", "L2 needs one existing edge and one forced nonedge")
                    augmented = edges | missing
                    visit(children[0], augmented, list(normal) + rhombi(augmented), path + "/L2")
            elif kind in {"L1c", "L3"}:
                keys(move, {"kind", "edges", "coefficients"} | ({"d"} if kind == "L3" else set()))
                pairs, coefficients = move["edges"], move["coefficients"]
                require(isinstance(pairs, list) and len(pairs) == 3 and isinstance(coefficients, list)
                        and len(coefficients) == 3 and all(tuple(sorted(e)) in edges for e in pairs),
                        "tree_move", "Heron move requires three directed edges")
                aa, bb, cc = [field.element(x) for x in coefficients]
                require(all(v != field.zero for v in (aa, bb, cc)), "tree_move", "Heron coefficients must be nonzero")
                belongs(relation(pairs, [aa, bb, cc]))
                if kind == "L1c":
                    require(not children, "tree_children", "L1c must be a leaf")
                else:
                    require(len(children) == 2, "tree_children", "L3 needs two ordered children")
                    na, nb, nc = [field.norm(x) for x in (aa, bb, cc)]
                    q = field.sub(field.add(na, nb), nc)
                    discriminant = field.sub(field.mul(field.scalar(4), field.mul(na, nb)), field.mul(q, q))
                    d = (field.real(move["d"]), field.zero[1])
                    test(field.mul(d, d), discriminant, "tree_discriminant", f"L3 d^2 identity fails at {path}")
                    imaginary_d = (field.zero[0], d[0])
                    for k, sign in enumerate((1, -1)):
                        qid = field.add(q, imaginary_d if sign == 1 else field.neg(imaginary_d))
                        row = relation(pairs[:2], [field.mul(qid, aa), field.mul(field.scalar(2), field.mul(na, bb))])
                        visit(children[k], edges, list(normal) + [row], path + f"/L3:{k}")
            else:
                raise Failure("tree_move", f"unsupported proof-tree move {kind}")

        visit(witness["tree"], initial_edges, rhombi(initial_edges), "root")
    return dict(idents), len(modulus) - 1


def check(rec, points=3, seed=20261007):
    t = rec["cert"].get("type")
    require(rec["verdict"] == "refuted" and isinstance(t, str) and t in ALL_REFUTATIONS,
            "refutation_type", f"unexpected refutation type {t!r}")
    # Stable under worker completion order, reordering, or sharding.
    material = f"{seed}\0{rec['g6']}\0{t}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))
    if t in POLY:
        return polynomial_identities(rec, rng, points)
    if t == "tree":
        return tree_identities(rec, rng, points)
    return {}, 0


def worker(task):
    number, raw, points, seed = task
    g, t = f"line:{number}", None
    started = time.monotonic()
    try:
        rec = record(raw)
        g, t = rec["g6"], rec["cert"].get("type")
        if rec["verdict"] != "refuted":
            return {"line": number, "g6": g, "type": t, "status": "not_refuted", "identities": {}}
        identities, degree = check(rec, points, seed)
        return {"line": number, "g6": g, "type": t, "status": "PASS", "identities": identities,
                "max_input_degree": degree, "seconds": round(time.monotonic() - started, 4)}
    except Failure as exc:
        return {"line": number, "g6": g, "type": t, "status": "FAIL", "code": exc.code,
                "reason": exc.reason, **exc.details, "identities": {}}
    except (KeyError, TypeError, IndexError, ArithmeticError) as exc:
        return {"line": number, "g6": g, "type": t, "status": "FAIL", "code": "schema",
                "reason": str(exc), "identities": {}}


def bump(poly, keep_nonzero=False):
    require(bool(poly), "control", "control needs a nonempty polynomial")
    q = rational(poly[0][0])
    poly[0][0] = str(q - 1 if keep_nonzero and q == -1 else q + 1)


def red_controls(firsts, points, seed):
    results = []

    def run(name, rec, mutate, expected):
        try:
            check(rec, points, seed)
            positive = True
        except Failure as exc:
            results.append({"name": name, "g6": rec["g6"], "positive_pass": False,
                            "red": False, "reason": str(exc)})
            return
        mutant = copy.deepcopy(rec)
        mutate(mutant["cert"])
        require(mutant != rec, "control", "mutation changed nothing")
        try:
            check(mutant, points, seed)
            results.append({"name": name, "g6": rec["g6"], "positive_pass": positive, "red": False})
        except Failure as exc:
            results.append({"name": name, "g6": rec["g6"], "positive_pass": positive,
                            "red": exc.code in expected, "code": exc.code, "reason": exc.reason,
                            "expected_codes": sorted(expected)})

    for t in sorted(POLY & set(firsts)):
        rec = firsts[t]
        if t.endswith("-dag"):
            row = next((i for i, r in enumerate(rec["cert"]["rows"]) if r["poly"]), None)
            if row is not None:
                run(t + ": row coefficient perturbed", rec, lambda c, i=row: bump(c["rows"][i]["poly"], True), {"row_identity"})
            run(t + ": final cofactors removed", rec, lambda c: c["rows"][-1].__setitem__("cofactors", {}), {"row_identity"})
        else:
            name = next((k for k, v in rec["cert"]["cofactors"].items() if v and rational(v[0][0]) != 0), None)
            if name:
                run(t + ": cofactor coefficient +1", rec, lambda c, k=name: bump(c["cofactors"][k]), {"cofactor_identity"})
                run(t + ": cofactor term removed", rec, lambda c, k=name: c["cofactors"][k].pop(0), {"cofactor_identity"})
        run(t + ": invalid frame", rec, lambda c: c.__setitem__("frame", [c["frame"][0]] * 2), {"frame"})
        if t == "real-dag":
            run(t + ": target coefficient perturbed", rec, lambda c: bump(c["f"], True), {"last_target"})
        if t == "null-dag" and len(rec["cert"]["rows"]) > 1:
            prior = rec["cert"]["rows"][-2]["poly"]
            prior_is_one = len(prior) == 1 and rational(prior[0][0]) == 1 and not any(prior[0][1])
            if not prior_is_one:
                run(t + ": last row removed", rec, lambda c: c["rows"].pop(), {"last_target"})
        if "system" in rec["cert"]:
            k = next(iter(rec["cert"]["system"]))
            run(t + ": supplied system coefficient +1", rec, lambda c, k=k: bump(c["system"][k]), {"system_identity"})
    for key, rec in sorted(firsts.items()):
        if key.endswith("+sos"):
            run(key + ": SOS constant +1", rec, lambda c: c["sos"].__setitem__("c", str(rational(c["sos"]["c"]) + 1)), {"sos_identity"})
            squares = rec["cert"]["sos"]["squares"]
            j = next((i for i, (w, q) in enumerate(squares) if q), None)
            if j is not None:
                run(key + ": SOS weight doubled", rec,
                    lambda c, j=j: c["sos"]["squares"][j].__setitem__(0, str(2 * rational(c["sos"]["squares"][j][0]))), {"sos_identity"})
    if "tree" in firsts:
        rec = firsts["tree"]

        def perturb_matrix(c):
            root = c["witness"]["tree"]
            cell = root["A"][0][0]
            if isinstance(cell, dict):
                cell = cell["re"]
                cell[0] = str(rational(cell[0], tree=True) + 1)
            elif isinstance(cell, list):
                cell[0] = str(rational(cell[0], tree=True) + 1)
            else:
                root["A"][0][0] = str(rational(cell, tree=True) + 1)
        if rec["cert"]["witness"]["tree"]["A"]:
            run("tree: matrix entry +1", rec, perturb_matrix, {"tree_rowspace"})
        # Exercise branch identities even if the first tree terminates at L1.
        def find_l3(node):
            if node["move"]["kind"] == "L3":
                return node
            for child in node["children"]:
                hit = find_l3(child)
                if hit:
                    return hit
            return None
        l3 = find_l3(rec["cert"]["witness"]["tree"])
        if l3:
            def perturb_d(c):
                move = find_l3(c["witness"]["tree"])["move"]
                if isinstance(move["d"], list):
                    move["d"][0] = str(rational(move["d"][0], tree=True) + 2)
                else:
                    move["d"] = str(rational(move["d"], tree=True) + 2)
            run("tree: L3 d +2", rec, perturb_d, {"tree_discriminant"})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records")
    parser.add_argument("out")
    parser.add_argument("--points", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--shard", default="0/1")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--no-red-controls", action="store_true", help="explicitly mark controls NOT RUN")
    parser.add_argument("--details", help="stream small per-refutation results to this JSONL")
    a = parser.parse_args()
    require(a.jobs > 0 and a.points > 0 and (a.limit is None or a.limit > 0), "arguments", "positive jobs, points and limit required")
    si, sn = shard(a.shard)
    guard_outputs([a.records], [a.out] + ([a.details] if a.details else []))
    sources = source_hashes("independent_core.py", "modp_identities.py")
    t0 = time.monotonic()
    counts, totals, failures, firsts = Counter(), Counter(), [], {}
    consumed_hash, selected_hash, scanned = hashlib.sha256(), hashlib.sha256(), 0
    max_degree, worker_seconds = 0, 0.0

    def tasks():
        nonlocal scanned
        for number, raw in lines(a.records, a.limit):
            consumed_hash.update(raw)
            scanned = number
            if (number - 1) % sn != si:
                continue
            selected_hash.update(raw)
            try:
                r = record(raw)
                if r["verdict"] == "refuted":
                    t = r["cert"].get("type")
                    if isinstance(t, str) and t not in firsts and t in POLY | {"tree"}:
                        firsts[t] = r
                    if isinstance(t, str) and "sos" in r["cert"] and t + "+sos" not in firsts:
                        firsts[t + "+sos"] = r
            except Failure:
                pass  # Worker records this named failure; it is not discarded.
            yield number, raw, a.points, a.seed

    details = open(a.details, "w") if a.details else None
    try:
        for result in bounded_map(worker, tasks(), a.jobs):
            counts[f"{result['type']}/{result['status']}"] += 1
            totals.update(result["identities"])
            max_degree = max(max_degree, result.get("max_input_degree", 0))
            worker_seconds += result.get("seconds", 0.0)
            if result["status"] == "FAIL":
                failures.append(result)
                print("FAIL", json.dumps(result), flush=True)
            if details and result["status"] != "not_refuted":
                details.write(json.dumps(result, sort_keys=True) + "\n")
            if sum(counts.values()) % 10000 == 0:
                print(f"selected {sum(counts.values())}; identities {sum(totals.values())}; {time.monotonic()-t0:.1f}s", flush=True)
        reds = [] if a.no_red_controls else red_controls(firsts, a.points, a.seed)
        require(sources == source_hashes("independent_core.py", "modp_identities.py"),
                "source_changed", "tool source changed during identity checking")
        # Empty identity samples cannot serve as a successful check 6 run.
        all_red = bool(reds) and all(x.get("red") and x.get("positive_pass") for x in reds)
        status = "PASS" if not failures and sum(totals.values()) > 0 and (all_red or a.no_red_controls) else "FAIL"
        rep = {"status": status, "scope": "sample-or-shard" if a.limit or sn > 1 else "provided-stream",
               "counts": dict(counts), "failures": failures, "primes": [str(p) for p in PRIMES],
               "points_per_prime": a.points, "seed": a.seed, "shard": a.shard,
               "scanned_records": scanned, "selected_records": sum(counts.values()),
               "consumed_sha256": consumed_hash.hexdigest(), "selected_sha256": selected_hash.hexdigest(),
               "source_hashes": sources,
               "identities": dict(totals), "identities_per_point": sum(totals.values()) // (2 * a.points),
               "max_input_polynomial_degree": max_degree, "red_controls": reds, "all_red": all_red,
               "polynomial_identity_degree_bound": max(2 * max_degree, max_degree + 3),
               "controls_status": "NOT RUN" if a.no_red_controls else "PASS" if all_red else "FAIL",
               "worker_seconds": round(worker_seconds, 3), "seconds": round(time.monotonic() - t0, 3),
               "nonidentities_not_checked": ["Sturm root count", "selected-root signs/irreducibility",
                   "TU forcing lemmas", "sub-pointer containment/dependencies"],
               "tree_method": "regenerated rhombi and row spaces over modular quotient rings; random remainder evaluation plus coefficient equality",
               "probability_caveat": "Schwartz-Zippel applies only if the rational difference remains a nonzero polynomial modulo a chosen prime; deliberate prime-multiple discrepancies are outside this fixed-prime control"}
        write_json(a.out, rep)
        print(json.dumps({k: rep[k] for k in ("status", "counts", "identities_per_point", "all_red", "seconds")}), flush=True)
        return 0 if status == "PASS" else 1
    except (Failure, OSError) as exc:
        write_json(a.out, {"status": "FAIL", "failures": [{"code": getattr(exc, "code", "io"), "reason": str(exc)}]})
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    finally:
        if details:
            details.close()


if __name__ == "__main__":
    sys.exit(main())
