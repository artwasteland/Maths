#!/usr/bin/env python3
"""Blind GP-10 certificate checker. See FORMAT.md for the accepted wire format."""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import re
import resource
import sqlite3
import subprocess
import sys
import tempfile
import time

# This assignment precedes every possible SymPy import, including the trusted kernel.
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
import flint
from flint import fmpq, fmpq_mpoly_ctx
import networkx as nx

HERE = Path(__file__).resolve().parent
GP = HERE.parent
TRUSTED = GP.parent / "unit-distance-22"
SCRATCH = Path("/tmp/gp10-check")
os.environ["TMPDIR"] = str(SCRATCH)
os.environ["SQLITE_TMPDIR"] = str(SCRATCH)
LABELG = "/usr/bin/nauty-labelg"
CHUNK = 128
MAX_LINE = 8 * 1024 * 1024
MAX_CHUNK = 8 * 1024 * 1024
CONTROL_ORDERS = {f"B{n}p": n for n in range(4, 10)}
FROZEN_ORDERS = {**CONTROL_ORDERS, "B10": 10}


class Rejection(Exception):
    def __init__(self, reason, detail=""):
        self.reason, self.detail = reason, str(detail)
        super().__init__(reason + (": " + self.detail if self.detail else ""))


def need(condition, reason, detail=""):
    if not condition:
        raise Rejection(reason, detail)


def keys(obj, required, optional=(), where="object"):
    need(isinstance(obj, dict), "schema", where + " must be an object")
    need(set(required) <= set(obj) <= set(required) | set(optional), "schema",
         f"{where}: missing={sorted(set(required)-set(obj))} extra={sorted(set(obj)-set(required)-set(optional))}")


def integer(value, where="integer"):
    need(type(value) is int, "schema", where + " must be an integer")
    return value


def rational(value):
    need(isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+(?:/[0-9]+)?", value),
         "rational", "expected an exact rational string")
    try:
        return Q(value)
    except (ValueError, ZeroDivisionError):
        raise Rejection("rational", "invalid denominator or numerator")


def no_duplicates(items):
    result = {}
    for k, v in items:
        need(k not in result, "duplicate_json_key", k)
        result[k] = v
    return result


def finite_float(raw):
    value = float(raw)
    need(math.isfinite(value), "json_constant", raw)
    return value


def loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=no_duplicates, parse_float=finite_float,
                          parse_constant=lambda x: (_ for _ in ()).throw(Rejection("json_constant", x)))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise Rejection("json", str(exc))


def read_json(path):
    return loads(Path(path).read_bytes())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def lines(path):
    with Path(path).open("rb") as stream:
        index = 0
        while True:
            offset = stream.tell()
            raw = stream.readline(MAX_LINE + 1)
            if not raw:
                break
            index += 1
            need(len(raw) <= MAX_LINE, "record_limit", f"{path}:{index}")
            need(raw.endswith(b"\n") and raw != b"\n", "line_format", f"{path}:{index}")
            yield index, offset, raw


def chunks(iterator):
    chunk, size = [], 0
    for item in iterator:
        raw_size = len(item[-1])
        if chunk and (len(chunk) >= CHUNK or size + raw_size > MAX_CHUNK):
            yield chunk
            chunk, size = [], 0
        chunk.append(item)
        size += raw_size
    if chunk:
        yield chunk


@dataclass
class Graph:
    n: int
    edges: set

    def nx(self):
        g = nx.Graph()
        g.add_nodes_from(range(self.n))
        g.add_edges_from(self.edges)
        return g


def decode(code):
    need(isinstance(code, str) and bool(code), "g6", "expected graph6 string")
    need(not code.startswith(">>") and all(63 <= ord(c) <= 126 for c in code), "g6", "bad alphabet")
    vals = [ord(c) - 63 for c in code]
    if vals[0] < 63:
        n, start = vals[0], 1
    else:
        need(len(vals) >= 4 and vals[1] != 63, "g6", "unsupported order encoding")
        n, start = (vals[1] << 12) | (vals[2] << 6) | vals[3], 4
        need(n >= 63, "g6", "nonminimal order encoding")
    bits = n * (n - 1) // 2
    need(len(vals) - start == (bits + 5) // 6, "g6", "wrong length")
    if bits % 6:
        need(vals[-1] & ((1 << (6 - bits % 6)) - 1) == 0, "g6", "nonzero padding")
    edges, k = set(), 0
    for v in range(1, n):
        for u in range(v):
            if vals[start + k // 6] & (1 << (5 - k % 6)):
                edges.add((u, v))
            k += 1
    return Graph(n, edges)


def encode(graph):
    return nx.to_graph6_bytes(graph.nx(), header=False).decode("ascii").rstrip("\n")


def canonical_many(codes):
    if not codes:
        return []
    for c in codes:
        decode(c)
    try:
        proc = subprocess.run([LABELG, "-q"], input="\n".join(codes) + "\n", text=True,
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Rejection("canonical_tool", str(exc))
    result = proc.stdout.splitlines()
    need(proc.returncode == 0 and len(result) == len(codes), "canonical_tool", proc.stderr)
    for c in result:
        decode(c)
    return result


def canonical(graph):
    return canonical_many([encode(graph)])[0]


def check_canonical(codes):
    actual = canonical_many(codes)
    for a, b in zip(codes, actual):
        need(a == b, "noncanonical_g6", a)


def mapping(source, target, raw, where="map"):
    need(isinstance(raw, list) and len(raw) == source.n, "map_length", where)
    need(all(type(x) is int and 0 <= x < target.n for x in raw), "map_range", where)
    need(len(set(raw)) == len(raw), "map_not_injective", where)
    for u, v in sorted(source.edges):
        image = tuple(sorted((raw[u], raw[v])))
        need(image in target.edges, "map_not_edge_preserving", f"{where}: {u,v} -> {image}")
    return raw


def pair(raw, n):
    need(isinstance(raw, list) and len(raw) == 2, "pair", "expected two vertices")
    need(all(type(i) is int and 0 <= i < n for i in raw) and raw[0] != raw[1], "pair", "invalid vertices")
    return tuple(sorted(raw))


def trim(p):
    p = list(p)
    while p and not p[-1]:
        p.pop()
    return p


def padd(p, q):
    return trim([(p[i] if i < len(p) else Q(0)) + (q[i] if i < len(q) else Q(0))
                 for i in range(max(len(p), len(q)))])


def psub(p, q):
    return padd(p, [-x for x in q])


def pmul(p, q):
    if not p or not q:
        return []
    out = [Q(0)] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] += a * b
    return trim(out)


def pdiv(p, q):
    p, q = trim(p), trim(q)
    need(bool(q), "polynomial_zero_divisor")
    quot = [Q(0)] * max(0, len(p) - len(q) + 1)
    while p and len(p) >= len(q):
        k, c = len(p) - len(q), p[-1] / q[-1]
        quot[k] = c
        for i, a in enumerate(q):
            p[k + i] -= c * a
        p = trim(p)
    return trim(quot), p


def peval(p, x):
    answer = Q(0)
    for c in reversed(p):
        answer = answer * x + c
    return answer


def interval_poly(p, lo, hi):
    a = b = Q(0)
    for c in reversed(p):
        products = (a * lo, a * hi, b * lo, b * hi)
        a, b = min(products) + c, max(products) + c
    return a, b


def sturm_real_roots(raw):
    """Count distinct real roots, including repeated roots, using signs at infinity."""
    p = trim([Q(x) for x in raw])
    need(bool(p), "sturm_zero_polynomial")
    if len(p) == 1:
        return 0
    sequence = [p, [i * p[i] for i in range(1, len(p))]]
    while sequence[-1]:
        _, remainder = pdiv(sequence[-2], sequence[-1])
        if not remainder:
            break
        sequence.append([-x for x in remainder])
    def changes(negative):
        signs = []
        for q in sequence:
            sign = 1 if q[-1] > 0 else -1
            if negative and (len(q) - 1) % 2:
                sign = -sign
            signs.append(sign)
        return sum(a != b for a, b in zip(signs, signs[1:]))
    return changes(True) - changes(False)


def exact_embedding(graph, cert):
    keys(cert, {"type", "field", "coords"}, where="E-exact")
    spec = cert["field"]
    keys(spec, {"minpoly", "interval"}, where="field")
    raw = spec["minpoly"]
    need(isinstance(raw, list) and len(raw) >= 2 and all(type(c) is int for c in raw) and raw[-1] != 0,
         "minpoly", "expected positive degree integer polynomial")
    poly, degree = list(map(Q, raw)), len(raw) - 1
    iv = spec["interval"]
    need(isinstance(iv, list) and len(iv) == 2, "interval", "expected two endpoints")
    lo, hi = map(rational, iv)
    need(lo < hi and peval(poly, lo) * peval(poly, hi) < 0, "interval_sign_change")
    coords = cert["coords"]
    need(isinstance(coords, list) and len(coords) == graph.n, "coordinate_count")
    points = []
    for xy in coords:
        need(isinstance(xy, list) and len(xy) == 2, "coordinate_shape")
        for p in xy:
            need(isinstance(p, list) and len(p) == degree, "coordinate_degree")
        points.append([[rational(c) for c in p] for p in xy])
    distances = []
    for u in range(graph.n):
        for v in range(u + 1, graph.n):
            dx, dy = (psub(points[u][i], points[v][i]) for i in (0, 1))
            dist = padd(pmul(dx, dx), pmul(dy, dy))
            if (u, v) in graph.edges:
                need(not pdiv(psub(dist, [Q(1)]), poly)[1], "edge_equation", str((u, v)))
            distances.append((u, v, dist))
    for u, v, dist in distances:
        need(bool(pdiv(dist, poly)[1]), "exact_collision", str((u, v)))
    # A single shared interval selects one root for ALL pairs, even for reducible polynomials.
    pending = distances
    for step in range(2049):
        pending = [(u, v, p) for u, v, p in pending if interval_poly(p, lo, hi)[0] <= 0]
        if not pending:
            return {"interval_bisections": step}
        need(step < 2048, "distinctness_unresolved", "certified interval budget exhausted")
        mid = (lo + hi) / 2
        fm = peval(poly, mid)
        if not fm:
            for u, v, p in distances:
                need(peval(p, mid) > 0, "exact_collision", str((u, v)))
            return {"interval_bisections": step + 1, "rational_root": str(mid)}
        if peval(poly, lo) * fm < 0:
            hi = mid
        else:
            lo = mid
    raise Rejection("distinctness_unresolved", "certified interval budget exhausted")


def polynomial(raw, ctx, nvars):
    need(isinstance(raw, list), "sparse_polynomial", "expected term list")
    terms = {}
    for term in raw:
        need(isinstance(term, list) and len(term) == 2, "sparse_polynomial", "expected [coefficient, exponents]")
        c, exps = rational(term[0]), term[1]
        need(isinstance(exps, list) and len(exps) == nvars and all(type(e) is int and e >= 0 for e in exps),
             "sparse_exponents")
        exps = tuple(exps)
        need(exps not in terms, "sparse_duplicate_monomial")
        terms[exps] = fmpq(c.numerator, c.denominator)
    return ctx.from_dict(terms)


def serialize_polynomial(p):
    return [[str(c), list(e)] for e, c in sorted(p.to_dict().items()) if c]


def regenerate(graph, frame, sat):
    edge = pair(frame, graph.n)
    need(edge in graph.edges, "frame_not_edge")
    need(isinstance(sat, list), "sat", "expected pair list")
    sat_pairs = [pair(p, graph.n) for p in sat]
    need(len(set(sat_pairs)) == len(sat_pairs), "sat_duplicate")
    need(all(list(p) == q for p, q in zip(sat_pairs, sat)), "sat_pair_order", "use u < v")
    a, b = frame
    names = [f"{axis}_{i}" for i in range(graph.n) if i not in (a, b) for axis in ("x", "y")]
    names += [f"t_{i}" for i in range(len(sat))]
    # flint supports a zero-variable polynomial context for the two-vertex case.
    ctx = fmpq_mpoly_ctx.get(tuple(names), ordering="lex")
    var = dict(zip(names, ctx.gens()))
    zero, one = ctx.constant(0), ctx.constant(1)
    coords = {a: (zero, zero), b: (one, zero)}
    for i in range(graph.n):
        if i not in coords:
            coords[i] = (var[f"x_{i}"], var[f"y_{i}"])
    def d2(u, v):
        return (coords[u][0] - coords[v][0]) ** 2 + (coords[u][1] - coords[v][1]) ** 2
    gens = {f"e:{u},{v}": d2(u, v) - one for u, v in sorted(graph.edges) if (u, v) != edge}
    for k, (u, v) in enumerate(sat_pairs):
        gens[f"s:{u},{v}"] = var[f"t_{k}"] * d2(u, v) - one
    return ctx, names, gens


def algebra(graph, cert):
    is_real = cert["type"] == "real"
    required = {"type", "frame", "sat", "cofactors"} | ({"f"} if is_real else set())
    keys(cert, required, {"system", "sturm", "sos"} if is_real else {"system"}, "R-algebra")
    ctx, names, gens = regenerate(graph, cert["frame"], cert["sat"])
    def parse(p):
        return polynomial(p, ctx, len(names))
    if "system" in cert:
        stated = cert["system"]
        need(isinstance(stated, dict) and set(stated) == set(gens), "system_mismatch", "generator keys")
        need(all(parse(stated[k]) == g for k, g in gens.items()), "system_mismatch", "generator polynomials")
    cof = cert["cofactors"]
    need(isinstance(cof, dict) and set(cof) <= set(gens), "cofactor_generator", "unknown generator")
    total = ctx.constant(0)
    for k, raw in cof.items():
        total += parse(raw) * gens[k]
    target = parse(cert["f"]) if is_real else ctx.constant(1)
    need(total == target, "cofactor_identity")
    if not is_real:
        return {"variables": len(names), "generators": len(gens)}
    return real_no_zero(cert, ctx, names, target, parse)


def real_no_zero(cert, ctx, names, target, parse):
    need(("sturm" in cert) != ("sos" in cert), "real_proof_choice")
    if "sturm" in cert:
        variable = cert["sturm"]
        need(isinstance(variable, str) and variable in names, "sturm_variable")
        index = names.index(variable)
        coeffs = {}
        for exps, c in target.to_dict().items():
            need(all(e == 0 for j, e in enumerate(exps) if j != index), "sturm_multivariate")
            coeffs[exps[index]] = Q(str(c))
        dense = [coeffs.get(i, Q(0)) for i in range(max(coeffs, default=0) + 1)]
        count = sturm_real_roots(dense)
        need(count == 0, "sturm_real_root", str(count))
        return {"real_roots": count}
    sos = cert["sos"]
    keys(sos, {"c", "squares"}, where="SOS")
    c = rational(sos["c"])
    need(c > 0, "sos_constant_positive")
    result = ctx.constant(fmpq(c.numerator, c.denominator))
    need(isinstance(sos["squares"], list), "sos_squares")
    for term in sos["squares"]:
        need(isinstance(term, list) and len(term) == 2, "sos_square")
        weight = rational(term[0])
        need(weight > 0, "sos_weight_positive")
        result += fmpq(weight.numerator, weight.denominator) * parse(term[1]) ** 2
    need(result == target, "sos_identity")
    return {"sos_squares": len(sos["squares"])}


def canonical_polynomial(raw, ctx, nvars):
    result = polynomial(raw, ctx, nvars)
    need(all(rational(c) != 0 for c, _ in raw), "sparse_noncanonical", "zero coefficient")
    need(all(tuple(a[1]) < tuple(b[1]) for a, b in zip(raw, raw[1:])),
         "sparse_noncanonical", "terms must be in increasing exponent order")
    return result


def algebra_dag(graph, cert):
    is_real = cert["type"] == "real-dag"
    required = {"type", "frame", "sat", "rows"} | ({"f"} if is_real else set())
    keys(cert, required, {"sturm", "sos"} if is_real else set(), "R-algebra-dag")
    ctx, names, gens = regenerate(graph, cert["frame"], cert["sat"])
    def parse(p):
        return canonical_polynomial(p, ctx, len(names))
    rows = cert["rows"]
    need(isinstance(rows, list) and bool(rows), "dag_rows", "expected nonempty row list")
    need(len(rows) <= 256, "dag_row_limit")
    sources = dict(gens)
    last = None
    for k, row in enumerate(rows):
        keys(row, {"poly", "cofactors"}, where=f"DAG row {k}")
        cof = row["cofactors"]
        need(isinstance(cof, dict), "dag_source", "expected cofactor dictionary")
        total = ctx.constant(0)
        for key, raw in cof.items():
            if isinstance(key, str) and re.fullmatch(r"aux:(0|[1-9][0-9]*)", key):
                # The length guard avoids converting arbitrarily long untrusted integers.
                digits = key[4:]
                need(len(digits) <= 3 and int(digits) < k, "dag_reference_order", f"row {k}: {key}")
            need(key in sources, "dag_source", f"row {k}: {key}")
            total += parse(raw) * sources[key]
        last = parse(row["poly"])
        need(total == last, "dag_row_identity", f"row {k}")
        sources[f"aux:{k}"] = last
    target = parse(cert["f"]) if is_real else ctx.constant(1)
    need(last == target, "dag_last_real" if is_real else "dag_last_null")
    detail = {"variables": len(names), "generators": len(gens), "rows": len(rows)}
    if is_real:
        detail.update(real_no_zero(cert, ctx, names, target, parse))
    return detail


_KERNEL = None


def kernel():
    global _KERNEL
    if _KERNEL is None:
        spec = importlib.util.spec_from_file_location("gp10_trusted_udcheck", TRUSTED / "check/udcheck.py")
        _KERNEL = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = _KERNEL
        spec.loader.exec_module(_KERNEL)
    return _KERNEL


class Checker:
    def __init__(self, forbidden_limit=9):
        need(type(forbidden_limit) is int and 0 <= forbidden_limit <= 9, "forbidden_limit")
        self.forbidden_limit = forbidden_limit
        raw = read_json(TRUSTED / "data/forbidden-74.json")
        self.forbidden = [Graph(1 + max(max(e) for e in es), {tuple(sorted(e)) for e in es}) for es in raw]
        need(len(self.forbidden) == 74, "trusted_data", "forbidden count")
        self.gadgets = read_json(TRUSTED / "data/tu-gadgets.json")
        self.forbidden_codes = canonical_many([encode(g) for g in self.forbidden])
        self.patterns = [g.nx() for g in self.forbidden]

    def in_force(self, index):
        integer(index)
        need(0 <= index < len(self.forbidden) and self.forbidden[index].n <= self.forbidden_limit,
             "forbidden_not_in_force", str(index))
        return self.forbidden[index]

    def verify(self, record):
        keys(record, {"g6", "verdict", "cert"}, where="record")
        graph = decode(record["g6"])
        verdict, cert = record["verdict"], record["cert"]
        need(isinstance(verdict, str) and verdict in ("embedded", "refuted", "unknown"), "verdict_allowlist")
        if verdict == "unknown":
            keys(cert, {"reason", "budget"}, where="unknown")
            need(isinstance(cert["reason"], str) and bool(cert["reason"].strip()), "unknown_reason")
            need(isinstance(cert["budget"], dict), "unknown_budget")
            return None, {"budget": cert["budget"], "reason": cert["reason"]}
        need(isinstance(cert, dict) and isinstance(cert.get("type"), str), "certificate_type")
        kind = cert["type"]
        if verdict == "embedded":
            if kind == "exact":
                return None, exact_embedding(graph, cert)
            need(kind == "super", "certificate_type", "embedded requires exact or super")
            keys(cert, {"type", "g6", "map"}, where="E-ptr")
            target = decode(cert["g6"])
            check_canonical([cert["g6"]])
            mapping(graph, target, cert["map"], "E-ptr")
            return cert["g6"], {}
        if kind == "tree":
            keys(cert, {"type", "witness"}, where="R-tree")
            trusted = kernel()
            try:
                count = trusted.verify_refutation(trusted.Graph(graph.n, graph.edges), cert["witness"], "R-tree")
            except trusted.CheckError as exc:
                raise Rejection("tree", str(exc))
            return None, {"proof_nodes": count}
        if kind in ("null", "real"):
            return None, algebra(graph, cert)
        if kind in ("null-dag", "real-dag"):
            return None, algebra_dag(graph, cert)
        if kind == "sub":
            keys(cert, {"type", "g6", "map"}, {"index"}, "R-ptr")
            source = decode(cert["g6"])
            check_canonical([cert["g6"]])
            mapping(source, graph, cert["map"], "R-ptr")
            if "index" in cert:
                self.in_force(cert["index"])
                need(cert["g6"] == self.forbidden_codes[cert["index"]], "forbidden_index_graph")
                return None, {}
            return cert["g6"], {}
        need(kind == "tu", "certificate_type", "unknown refutation type")
        keys(cert, {"type", "steps", "end"}, where="R-tu")
        need(isinstance(cert["steps"], list) and bool(cert["steps"]), "tu_steps")
        augmented = Graph(graph.n, set(graph.edges))
        for k, step in enumerate(cert["steps"]):
            keys(step, {"gadget", "map", "pair"}, where="TU step")
            index = integer(step["gadget"])
            need(0 <= index < len(self.gadgets), "gadget_index")
            gadget = self.gadgets[index]
            pattern = Graph(gadget["n"], {tuple(e) for e in gadget["edges"]})
            m = mapping(pattern, augmented, step["map"], f"TU step {k}")
            actual = pair(step["pair"], graph.n)
            expected = tuple(sorted(m[v] for v in gadget["pair"]))
            need(actual == expected, "tu_distinguished_pair")
            need(actual not in augmented.edges, "tu_pair_already_edge")
            augmented.edges.add(actual)
        end = cert["end"]
        need(isinstance(end, dict), "tu_end")
        if "forbidden" in end:
            keys(end, {"forbidden", "map"}, where="TU end")
            mapping(self.in_force(end["forbidden"]), augmented, end["map"], "TU forbidden end")
            return None, {"tu_steps": len(cert["steps"])}
        keys(end, {"refuted", "map"}, where="TU end")
        source = decode(end["refuted"])
        check_canonical([end["refuted"]])
        mapping(source, augmented, end["map"], "TU refuted end")
        return end["refuted"], {"tu_steps": len(cert["steps"])}

    def contains_forbidden(self, graph, limit=9):
        target = graph.nx()
        for i, pattern in enumerate(self.forbidden):
            if pattern.n > min(limit, graph.n) or len(pattern.edges) > len(graph.edges):
                continue
            if nx.algorithms.isomorphism.GraphMatcher(target, self.patterns[i]).subgraph_is_monomorphic():
                return i
        return None

    def block_evidence(self, graph, max_order):
        target = graph.nx()
        need(not nx.is_biconnected(target), "block_is_biconnected")
        covered, evidence = set(), []
        for vertices in nx.biconnected_components(target):
            vertices = sorted(vertices)
            block = target.subgraph(vertices)
            need(len(vertices) <= max_order <= 9, "block_order")
            edges = {tuple(sorted(e)) for e in block.edges}
            need(not (covered & edges), "block_overlap")
            covered.update(edges)
            reindex = {v: i for i, v in enumerate(vertices)}
            small = Graph(len(vertices), {(min(reindex[u], reindex[v]), max(reindex[u], reindex[v])) for u, v in edges})
            need(self.contains_forbidden(small) is None, "block_forbidden")
            evidence.append({"vertices": vertices, "edges": [list(e) for e in sorted(edges)]})
        need(covered == graph.edges, "block_edge_coverage")
        return {"blocks": evidence, "isolated": list(nx.isolates(target))}


def environment():
    import sympy
    return {"python": sys.version.split()[0], "executable": sys.executable,
            "sympy": sympy.__version__, "flint": flint.__version__,
            "SYMPY_GROUND_TYPES": os.environ.get("SYMPY_GROUND_TYPES"),
            "nice": os.getpriority(os.PRIO_PROCESS, 0), "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def relative(root, value):
    need(isinstance(value, str) and bool(value), "path")
    return (root / value).resolve()


def graph_list(path):
    result = []
    for _, _, raw in lines(path):
        try:
            c = raw[:-1].decode("ascii")
        except UnicodeError:
            raise Rejection("g6", "non-ASCII graph list")
        decode(c)
        result.append(c)
    need(result == sorted(set(result)), "graph_list_order", str(path))
    return result


def compare_control_minimals(profile, minimal, checker):
    n = CONTROL_ORDERS[profile]
    expected = {c for c, g in zip(checker.forbidden_codes, checker.forbidden) if g.n == n}
    need(set(minimal) == expected, "control_minimal_list",
         f"missing={sorted(expected-set(minimal))} extra={sorted(set(minimal)-expected)}")
    return len(expected)


def named_graphs():
    # Golomb: a hexagonal wheel, plus a triangle joined to alternate rim vertices.
    golomb = nx.wheel_graph(7)
    golomb.add_edges_from([(7, 8), (8, 9), (7, 9), (7, 1), (8, 3), (9, 5)])
    mobius = nx.cycle_graph(10)
    mobius.add_edges_from((i, i + 5) for i in range(5))
    graphs = [nx.petersen_graph(), golomb, nx.circular_ladder_graph(5), decode("IISpZATaw").nx(), mobius]
    codes = canonical_many([nx.to_graph6_bytes(g, header=False).decode().strip() for g in graphs])
    return dict(zip(("Petersen", "Golomb", "pentagonal_prism", "extremal", "Moebius"), codes))


class Run:
    def __init__(self, directory, output=None, emit=print):
        self.directory = Path(directory).resolve()
        self.output = Path(output).resolve() if output else self.directory / "checked"
        self.emit = emit
        self.summary = {"status": "REJECT", "scope": "certificate-and-run-checks", "claim_authorized": False}

    def line(self, status, code, reason):
        self.emit(f"{status} record {code} {reason}")
        self.record_log.write(json.dumps({"status": status, "g6": code, "reason": reason}) + "\n")

    def execute(self, stack=()):
        # Refuse an output path that would overwrite any supplied input stream.
        products = ("report.json", "report.json.tmp", "L10.g6", "L4.g6", "L5.g6", "L6.g6", "L7.g6", "L8.g6", "L9.g6", "minimal.g6",
                    "minimality.jsonl", "records.jsonl", "unknown-budgets.jsonl")
        try:
            early = read_json(self.directory / "run.json")
            keys(early, {"profile", "input", "input_sha256", "records"},
                 {"hosts", "unknown", "minimal_claim", "cross_checks", "controls", "provenance", "predictions", "forbidden_limit", "derive"}, "run manifest")
            refs = ["run.json", early["input"], early.get("unknown", "UNKNOWN.g6")]
            if isinstance(early["records"], list):
                refs.extend(early["records"])
            refs.extend(early[k] for k in ("hosts", "minimal_claim", "cross_checks", "provenance") if k in early)
            if isinstance(early.get("predictions"), dict) and "path" in early["predictions"]:
                refs.append(early["predictions"]["path"])
            inputs = {relative(self.directory, p) for p in refs}
            need(not inputs & {(self.output / p).resolve() for p in products}, "output_input_collision")
        except (Rejection, OSError, ValueError, TypeError) as exc:
            self.summary.update({"reason": exc.reason if isinstance(exc, Rejection) else "checker_error", "detail": str(exc), "environment": environment()})
            self.emit("REJECT run " + self.summary["reason"])
            return self.summary
        self.output.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        # Invalidate a previous report before checking changed inputs.
        json_write(self.output / "report.json", {**self.summary, "reason": "checking"})
        for name in ("L10.g6", "L4.g6", "L5.g6", "L6.g6", "L7.g6", "L8.g6", "L9.g6", "minimal.g6", "minimality.jsonl", "records.jsonl", "unknown-budgets.jsonl"):
            (self.output / name).unlink(missing_ok=True)
        try:
            need(self.directory not in stack and len(stack) < 8, "control_cycle")
            self.manifest = read_json(self.directory / "run.json")
            m = self.manifest
            keys(m, {"profile", "input", "input_sha256", "records"},
                 {"hosts", "unknown", "minimal_claim", "cross_checks", "controls", "provenance", "predictions", "forbidden_limit", "derive"}, "run manifest")
            profile = m["profile"]
            need(profile in ("sample", *FROZEN_ORDERS, "named", "regressions"), "profile")
            need(isinstance(m["records"], list) and bool(m["records"]), "record_files")
            if "derive" in m:
                need(type(m["derive"]) is bool, "schema", "derive must be boolean")
            need(profile == "B10" or not ({"controls", "predictions"} & set(m)), "profile_override")
            need(profile == "named" or "provenance" not in m, "profile_override")
            self.profile = profile
            self.limit = (FROZEN_ORDERS[profile] - 1 if profile in FROZEN_ORDERS else
                          {"named": 9, "regressions": 0}.get(profile, m.get("forbidden_limit", 9)))
            if profile != "sample":
                need("forbidden_limit" not in m and "derive" not in m, "profile_override")
            self.checker = Checker(self.limit)
            self.input = relative(self.directory, m["input"])
            need(isinstance(m["input_sha256"], str) and digest(self.input) == m["input_sha256"], "input_hash")
            self.summary.update({"profile": profile, "input_sha256": m["input_sha256"], "checker_sha256": digest(Path(__file__)),
                                 "kernel_sha256": digest(TRUSTED / "check/udcheck.py"), "forbidden_limit": self.limit,
                                 "trusted_data_sha256": {name: digest(TRUSTED / "data" / name) for name in ("forbidden-74.json", "tu-gadgets.json")}})
            if profile in FROZEN_ORDERS:
                sums = {name: sha for sha, name in (line.split() for line in (GP / "data/SHA256SUMS").read_text().splitlines())}
                need(m["input_sha256"] == sums[profile + ".g6"], "frozen_input_hash")
            if profile == "B10":
                self.controls(stack + (self.directory,))
            SCRATCH.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="index-", dir=SCRATCH) as tmp:
                self.db = sqlite3.connect(str(Path(tmp) / "index.sqlite"))
                try:
                    self.db.executescript("""
                      PRAGMA cache_size=-8192; PRAGMA temp_store=FILE;
                      CREATE TABLE inputs(g6 TEXT PRIMARY KEY);
                      CREATE TABLE records(g6 TEXT PRIMARY KEY, verdict TEXT, host INTEGER, dep TEXT,
                        status TEXT, reason TEXT, details TEXT);
                      CREATE INDEX dependency ON records(dep);
                    """)
                    with (self.output / "records.jsonl").open("w") as self.record_log:
                        self.load_input()
                        self.load_records()
                        self.resolve()
                        self.coverage()
                        self.unknowns()
                        self.cross_checks()
                        derive = profile in FROZEN_ORDERS or (profile == "sample" and m.get("derive", False))
                        if derive:
                            self.minimality()
                        else:
                            need("minimal_claim" not in m, "minimality_not_requested")
                            self.summary.update({"minimal": [], "conditional_minimal": []})
                        self.profile_controls()
                finally:
                    self.db.close()
            self.summary["status"] = "ACCEPT"
            self.summary["reason"] = "verified"
        except (Rejection, OSError, ValueError, TypeError, KeyError, RecursionError, MemoryError, sqlite3.Error) as exc:
            self.summary["reason"] = exc.reason if isinstance(exc, Rejection) else "checker_error"
            self.summary["detail"] = str(exc)
        self.summary["elapsed_seconds"] = time.monotonic() - started
        self.summary["environment"] = environment()
        json_write(self.output / "report.json", self.summary)
        self.emit(self.summary["status"] + " run " + self.summary["reason"])
        return self.summary

    def controls(self, stack):
        controls = self.manifest.get("controls")
        need(isinstance(controls, dict), "controls_required")
        keys(controls, {*CONTROL_ORDERS, "named", "regressions"}, where="B10 controls")
        accepted = {}
        for name, value in controls.items():
            path = relative(self.directory, value)
            need(path.is_relative_to(self.directory) and path != self.directory, "control_outside_run_tree")
            report_path = path / "checked/report.json"
            need(report_path.exists(), "control_report_missing", name)
            old = read_json(report_path)
            need(old.get("status") == "ACCEPT" and old.get("profile") == name, "control_report_not_accepted", name)
            replay = Run(path, emit=self.emit).execute(stack)
            need(replay["status"] == "ACCEPT" and replay.get("profile") == name, "control_replay_failed", name)
            accepted[name] = digest(report_path)
        prediction = self.manifest.get("predictions")
        keys(prediction, {"path", "sha256"}, where="predictions")
        path = relative(self.directory, prediction["path"])
        need(path.is_relative_to(self.directory) and digest(path) == prediction["sha256"] and path.stat().st_size > 0,
             "predictions_hash")
        self.summary["controls"] = accepted
        self.summary["predictions"] = {**prediction, "chronology": "not established by certificates"}

    def load_input(self):
        previous, count = None, 0
        consumed_hash = hashlib.sha256()
        for chunk in chunks(lines(self.input)):
            codes = [raw[:-1].decode("ascii") for _, _, raw in chunk]
            for _, _, raw in chunk:
                consumed_hash.update(raw)
            check_canonical(codes)
            for c in codes:
                need(previous is None or previous < c, "input_sorted_unique")
                if self.profile in FROZEN_ORDERS:
                    g = decode(c)
                    need(g.n == FROZEN_ORDERS[self.profile] and nx.is_biconnected(g.nx()), "input_graph_class")
                self.db.execute("INSERT INTO inputs VALUES (?)", (c,))
                previous, count = c, count + 1
        need(consumed_hash.hexdigest() == self.manifest["input_sha256"], "input_hash", "consumed input differs from frozen digest")
        self.summary["input_count"] = count

    def load_records(self):
        paths = [(relative(self.directory, x), False) for x in self.manifest["records"]]
        if "hosts" in self.manifest:
            paths.insert(0, (relative(self.directory, self.manifest["hosts"]), True))
        need(len({p for p, _ in paths}) == len(paths), "record_file_duplicate")
        hashes, failures = [], 0
        for path, host in paths:
            consumed_hash = hashlib.sha256()
            for chunk in chunks(lines(path)):
                parsed = []
                for lineno, _, raw in chunk:
                    consumed_hash.update(raw)
                    try:
                        record = loads(raw)
                        keys(record, {"g6", "verdict", "cert"}, where="record")
                        decode(record["g6"])
                        parsed.append(record)
                    except Rejection as exc:
                        failures += 1
                        self.line("REJECT", f"{path.name}:{lineno}", str(exc))
                canonical_codes = canonical_many([r["g6"] for r in parsed])
                for record, canon in zip(parsed, canonical_codes):
                    code, verdict = record["g6"], record["verdict"]
                    previous = self.db.execute("SELECT verdict FROM records WHERE g6=?", (code,)).fetchone()
                    if previous:
                        conflict = isinstance(verdict, str) and {previous[0], verdict} == {"embedded", "refuted"}
                        reason = "embedded_refuted_conflict" if conflict else "duplicate_record"
                        self.line("REJECT", code, reason)
                        raise Rejection(reason, code)
                    try:
                        need(code == canon, "noncanonical_g6", code)
                        if host:
                            need(verdict == "embedded" and isinstance(record["cert"], dict) and record["cert"].get("type") == "exact", "host_not_exact")
                            need(self.db.execute("SELECT 1 FROM inputs WHERE g6=?", (code,)).fetchone() is None, "host_input_overlap")
                        dep, details = self.checker.verify(record)
                        status, reason = ("pending", "pointer_pending") if dep else ("ACCEPT", "verified")
                    except Rejection as exc:
                        dep, details, status, reason = None, {}, "REJECT", str(exc)
                        failures += 1
                    self.db.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?)",
                                    (code, verdict if isinstance(verdict, str) else "invalid", int(host), dep, status, reason, json.dumps(details)))
                    if status != "pending":
                        self.line(status, code, reason)
                self.db.commit()
                # Do not retain decoded certificates while reading the next chunk.
                parsed.clear()
                del chunk
                record = None
                details = verdict = None
                raw = None
            hashes.append({"path": str(path), "sha256": consumed_hash.hexdigest(), "hosts": host})
        self.summary["files"] = hashes
        self.summary["direct_rejections"] = failures

    def resolve(self):
        # Kahn order, held on disk. Even arbitrarily long chains never recurse.
        self.db.executescript("CREATE TABLE queue(id INTEGER PRIMARY KEY, g6 TEXT UNIQUE);"
                              "INSERT INTO queue(g6) SELECT g6 FROM records WHERE dep IS NULL ORDER BY g6;")
        # Missing targets are terminal errors and can unblock their dependents.
        missing = self.db.execute("SELECT g6 FROM records WHERE dep IS NOT NULL AND dep NOT IN (SELECT g6 FROM records)").fetchall()
        for (code,) in missing:
            self.db.execute("UPDATE records SET status='REJECT', reason='pointer_target_missing', dep=NULL WHERE g6=?", (code,))
            self.db.execute("INSERT OR IGNORE INTO queue(g6) VALUES (?)", (code,))
            self.line("REJECT", code, "pointer_target_missing")
        cursor = 0
        while True:
            row = self.db.execute("SELECT id,g6 FROM queue WHERE id>? ORDER BY id LIMIT 1", (cursor,)).fetchone()
            if row is None:
                break
            cursor, target = row
            tv, ts = self.db.execute("SELECT verdict,status FROM records WHERE g6=?", (target,)).fetchone()
            for code, verdict in self.db.execute("SELECT g6,verdict FROM records WHERE dep=? AND status='pending' ORDER BY g6", (target,)):
                reason = "verified" if ts == "ACCEPT" and tv == verdict else "pointer_target_not_accepted_" + verdict
                status = "ACCEPT" if reason == "verified" else "REJECT"
                self.db.execute("UPDATE records SET status=?,reason=? WHERE g6=?", (status, reason, code))
                self.db.execute("INSERT OR IGNORE INTO queue(g6) VALUES (?)", (code,))
                self.line(status, code, reason)
        for (code,) in self.db.execute("SELECT g6 FROM records WHERE status='pending' ORDER BY g6"):
            self.db.execute("UPDATE records SET status='REJECT', reason='pointer_cycle' WHERE g6=?", (code,))
            self.line("REJECT", code, "pointer_cycle")
        rejected = self.db.execute("SELECT COUNT(*) FROM records WHERE status='REJECT'").fetchone()[0]
        need(rejected == 0 and self.summary["direct_rejections"] == 0, "records_rejected", str(rejected))

    def coverage(self):
        missing = self.db.execute("SELECT g6 FROM inputs EXCEPT SELECT g6 FROM records WHERE host=0").fetchall()
        extra = self.db.execute("SELECT g6 FROM records WHERE host=0 EXCEPT SELECT g6 FROM inputs").fetchall()
        need(not missing and not extra, "coverage", f"missing={len(missing)} extra={len(extra)}")
        counts = {k: self.db.execute("SELECT COUNT(*) FROM records WHERE host=0 AND verdict=?", (k,)).fetchone()[0]
                  for k in ("embedded", "refuted", "unknown")}
        need(sum(counts.values()) == self.summary["input_count"], "coverage_totals")
        self.summary["counts"] = counts
        self.summary["hosts"] = self.db.execute("SELECT COUNT(*) FROM records WHERE host=1").fetchone()[0]

    def unknowns(self):
        path = relative(self.directory, self.manifest.get("unknown", "UNKNOWN.g6"))
        need(path.exists(), "unknown_file_missing")
        actual = iter(lines(path))
        count = 0
        with (self.output / "unknown-budgets.jsonl").open("w") as budgets:
            for code, details in self.db.execute("SELECT g6,details FROM records WHERE host=0 AND verdict='unknown' ORDER BY g6"):
                row = next(actual, None)
                need(row is not None and row[-1] == (code + "\n").encode("ascii"), "unknown_exactness")
                budgets.write(json.dumps({"g6": code, **json.loads(details)}) + "\n")
                count += 1
            need(next(actual, None) is None, "unknown_exactness")
        self.summary["unknown_rate"] = {"numerator": count, "denominator": self.summary["input_count"], "budgets": "unknown-budgets.jsonl"}
        self.summary["conditional"] = count != 0

    def cross_checks(self):
        path = self.manifest.get("cross_checks")
        count = 0
        if path is not None:
            for _, _, raw in lines(relative(self.directory, path)):
                row = loads(raw)
                keys(row, {"refuted", "embedded"}, where="cross check")
                a, b = row["refuted"], row["embedded"]
                va = self.db.execute("SELECT verdict,status FROM records WHERE g6=?", (a,)).fetchone()
                vb = self.db.execute("SELECT verdict,status FROM records WHERE g6=?", (b,)).fetchone()
                need(va == ("refuted", "ACCEPT") and vb == ("embedded", "ACCEPT"), "cross_check_records")
                found = nx.algorithms.isomorphism.GraphMatcher(decode(b).nx(), decode(a).nx()).subgraph_is_monomorphic()
                need(not found, "monotonicity_conflict", a + " into " + b)
                count += 1
        self.summary["cross_checks"] = count

    def minimality(self):
        minimal, conditional, ruled_out = [], [], {}
        outname = "minimal.g6" if self.profile == "sample" else "L" + str(FROZEN_ORDERS[self.profile]) + ".g6"
        with (self.output / "minimality.jsonl").open("w") as evidence:
            for (code,) in self.db.execute("SELECT g6 FROM records WHERE host=0 AND verdict='refuted' ORDER BY g6"):
                g = decode(code)
                need(4 <= g.n <= 10 and nx.is_biconnected(g.nx()), "minimality_graph_class", code)
                need(self.checker.contains_forbidden(g, self.limit) is None, "minimality_not_free", code)
                rows, biconnected = [], []
                for e in sorted(g.edges):
                    deletion = Graph(g.n, g.edges - {e})
                    if nx.is_biconnected(deletion.nx()):
                        biconnected.append((e, encode(deletion)))
                    else:
                        rows.append({"edge": list(e), "verdict": "embedded_by_blocks",
                                     **self.checker.block_evidence(deletion, g.n - 1)})
                for (e, _), child in zip(biconnected, canonical_many([c for _, c in biconnected])):
                    row = self.db.execute("SELECT verdict,status FROM records WHERE g6=?", (child,)).fetchone()
                    need(row is not None and row[1] == "ACCEPT", "minimality_deletion_missing", child)
                    rows.append({"edge": list(e), "g6": child, "verdict": row[0]})
                refuted = sorted({r["g6"] for r in rows if r["verdict"] == "refuted"})
                unknown = sorted({r["g6"] for r in rows if r["verdict"] == "unknown"})
                if refuted:
                    status = "not_minimal"
                    ruled_out[code] = refuted
                else:
                    minimal.append(code)
                    status = "minimal" if not unknown else "minimal_if_all_listed_deletions_embed"
                    if unknown:
                        conditional.append({"g6": code, "requires_embedded": unknown})
                evidence.write(json.dumps({"g6": code, "status": status, "deletions": rows}) + "\n")
        (self.output / outname).write_text("".join(c + "\n" for c in minimal), encoding="ascii")
        self.summary.update({"minimal": minimal, "minimal_count": len(minimal), "minimal_file": outname,
                             "conditional_minimal": conditional, "nonminimal_count": len(ruled_out)})
        if "minimal_claim" in self.manifest:
            claim = graph_list(relative(self.directory, self.manifest["minimal_claim"]))
            need(not set(claim) & set(ruled_out), "minimality_claim_refuted_deletion")
            need(claim == minimal, "minimality_claim_mismatch")

    def profile_controls(self):
        profile = self.profile
        if profile == "sample":
            self.summary["control"] = "not_a_control"
            return
        if profile in (*CONTROL_ORDERS, "named", "regressions"):
            need(self.summary["counts"]["unknown"] == 0, "control_unknown")
        if profile in CONTROL_ORDERS:
            count = compare_control_minimals(profile, self.summary["minimal"], self.checker)
            if profile == "B9p":
                for code, verdict in self.db.execute("SELECT g6,verdict FROM records WHERE host=0"):
                    free = self.checker.contains_forbidden(decode(code)) is None
                    need((verdict == "embedded") == free, "control_F9_free_verdict", code)
            self.summary["control"] = {"status": "PASS", "minimal_members": count}
        elif profile == "named":
            names = named_graphs()
            expected = {g6: ("refuted" if name == "Moebius" else "embedded") for name, g6 in names.items()}
            self.expected_verdicts(expected)
            need("provenance" in self.manifest, "control_provenance_missing")
            provenance = read_json(relative(self.directory, self.manifest["provenance"]))
            required = {g6 for g6, verdict in expected.items() if verdict == "embedded"}
            need(isinstance(provenance, dict) and set(provenance) == required, "control_provenance_set")
            for code, row in provenance.items():
                keys(row, {"method", "evidence"}, where="provenance")
                need(row["method"] == "general-search" and isinstance(row["evidence"], str) and row["evidence"].strip(), "control_not_general_search")
                # An E-ptr is a library hit and cannot satisfy this control.
                dep = self.db.execute("SELECT dep FROM records WHERE g6=?", (code,)).fetchone()[0]
                need(dep is None, "control_library_pointer")
            self.summary["control"] = {"status": "PASS", "provenance": "general-search asserted by producer; not proved by certificates"}
        elif profile == "regressions":
            codes = canonical_many([encode(Graph(4, set(itertools.combinations(range(4), 2)))),
                                    encode(Graph(5, {(u, v) for u in range(2) for v in range(2, 5)}))])
            expected = {c: "refuted" for c in codes + [self.checker.forbidden_codes[i] for i in (4, 9, 10, 17, 18)]}
            expected["F`o~_"] = "embedded"
            self.expected_verdicts(expected)
            self.summary["control"] = {"status": "PASS", "forbidden_limit": 0}

    def expected_verdicts(self, expected):
        rows = dict(self.db.execute("SELECT g6,verdict FROM records WHERE host=0"))
        need(rows == expected, "control_expected_verdicts")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = Run(args.run_directory, args.output).execute()
    return 0 if result["status"] == "ACCEPT" else 1


if __name__ == "__main__":
    sys.exit(main())
