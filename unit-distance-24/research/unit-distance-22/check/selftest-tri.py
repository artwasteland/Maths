#!/usr/bin/env python3
"""Self-test for check/tri_verify.py, the checker of RHOMBUS-SPEC.md Section 4 (triangle case trees, amendments 1-2).

What it does, with no input beyond data/tu-gadgets.json and nauty-labelg:

* builds valid certificates with its own test prover: exact linear algebra over Q(w), w^2 = w - 1, elements as pairs
  of Fractions, depth-first over triangle splits; every leaf it emits is re-verified with its own arithmetic;
* shows ACCEPT on the positive controls (K4, K_{1,1,3}, the six TU gadgets, a root-closed graph, genuine two- and
  three-level trees, trees on real (23,65) samples, overlapping pair/edge leaves, a triangle-only leaf, and the exact
  boundaries of every limit), and cross-checks every accepted leaf in floating point with w = e^(i pi/3) itself;
* shows REJECT, with the specific reason, on red controls covering every rule;
* runs each binding red mutant of amendment 2 (wrong ring, sign flip in t(T, s), repeated cycle vertex, dropped
  child, int64 wrap, unsorted leaf triangle) twice: tri_verify must REJECT it, and a reference checker carrying that
  one bug must ACCEPT it, which shows the control catches exactly that bug;
* makes tri_verify REJECT plausible-looking certificates for the Moser spindle and the W6 wheel (both unit-distance
  graphs, so no valid certificate exists), and follows each one's true embedding to the leaf that is false;
* runs every certificate through a plain reference re-implementation too (differential: the two must agree), and
  exercises the command line (file structure, strict JSON, canonical graph6, --graphs, the ACCEPT line).

usage: selftest-tri.py [--labelg PATH]
       selftest-tri.py --make-certs OUT.jsonl GRAPHS.g6 ... [--max-nodes N]   (test-prover certificates, for timing)
       selftest-tri.py --bench-certs CERTS.jsonl ...                           (records/s of tri_verify, by leaves)
Exit status 0 if and only if every expectation holds.
"""

from __future__ import annotations

import argparse
import cmath
import collections
import copy
import hashlib
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import types
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The module under test: check/tri_verify.py, or the file named by TRI_VERIFY_PATH (the --mutants runner uses this).
# It is compiled from its source text, never from a cached .pyc, so a mutant is always the code that runs.
TV_PATH = Path(os.environ.get("TRI_VERIFY_PATH") or HERE / "tri_verify.py").resolve()
TV_SOURCE = TV_PATH.read_bytes()
TV_SHA256 = hashlib.sha256(TV_SOURCE).hexdigest()
TV = types.ModuleType("tri_verify")
TV.__file__ = str(TV_PATH)
sys.modules["tri_verify"] = TV
exec(compile(TV_SOURCE, str(TV_PATH), "exec"), TV.__dict__)
DATA = HERE.parent / "data"
LABELG = "/usr/bin/nauty-labelg"
F0, F1 = Fr(0), Fr(1)
B62 = 1 << 62


# =================================================================================================================
# Part 1. The test prover: exact linear algebra over Q(w) with elements (Fraction, Fraction) = x + y w.

class Ring:
    """Q(w) with w^2 = w - 1; for red controls only, the wrong ring w^2 = -w - 1 or a wrong constant for w^(-1)."""

    def __init__(self, wrong: bool = False, w_minus=(1, -1)):
        self.wrong = wrong
        self.zero = (F0, F0)
        self.one = (F1, F0)
        self.w_plus = (F0, F1)
        self.w_minus = (Fr(w_minus[0]), Fr(w_minus[1]))

    def mul(self, a, b):
        x1, y1 = a
        x2, y2 = b
        if self.wrong:
            return (x1 * x2 - y1 * y2, x1 * y2 + x2 * y1 - y1 * y2)
        return (x1 * x2 - y1 * y2, x1 * y2 + x2 * y1 + y1 * y2)

    def inv(self, a):
        x, y = a
        if self.wrong:                                  # conjugate x + y w^2 = (x - y) - y w, norm x^2 - xy + y^2
            nrm = x * x - x * y + y * y
            return ((x - y) / nrm, -y / nrm)
        nrm = x * x + x * y + y * y                     # conjugate x + y (1 - w) = (x + y) - y w
        return ((x + y) / nrm, -y / nrm)

    def pow_w(self, k):
        r = self.one
        for _ in range(k % 6):
            r = self.mul(r, self.w_plus)
        return r


def qadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def qsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def qneg(a):
    return (-a[0], -a[1])


def qzero(a):
    return a[0] == 0 and a[1] == 0


def vec_axpy(ring, v, f, u):
    """v <- v - f u for sparse vectors (dicts), in place."""
    for col, val in u.items():
        new = qsub(v.get(col, (F0, F0)), ring.mul(f, val))
        if qzero(new):
            v.pop(col, None)
        else:
            v[col] = new


class Basis:
    """Fully reduced echelon basis; each basis row carries its combination of the original rows."""

    def __init__(self, ring, rows=None):
        self.ring = ring
        self.rows = rows if rows is not None else []    # [pivot, vec, combo]

    def copy(self):
        return Basis(self.ring, [[p, dict(v), dict(c)] for p, v, c in self.rows])

    def reduce(self, vec):
        r = dict(vec)
        comb = {}
        for p, bv, bc in self.rows:
            f = r.get(p)
            if f is not None:
                vec_axpy(self.ring, r, f, bv)
                for j, x in bc.items():
                    comb[j] = qadd(comb.get(j, (F0, F0)), self.ring.mul(f, x))
        return r, {j: x for j, x in comb.items() if not qzero(x)}

    def insert(self, vec, combo):
        ring = self.ring
        r, comb = self.reduce(vec)
        if not r:
            return False
        c = dict(combo)
        for j, x in comb.items():
            c[j] = qsub(c.get(j, (F0, F0)), x)
        c = {j: x for j, x in c.items() if not qzero(x)}
        p = min(r)
        inv = ring.inv(r[p])
        r = {k: ring.mul(inv, x) for k, x in r.items()}
        c = {k: ring.mul(inv, x) for k, x in c.items()}
        for row in self.rows:
            g = row[1].get(p)
            if g is not None:
                vec_axpy(ring, row[1], g, r)
                for j, x in c.items():
                    new = qsub(row[2].get(j, (F0, F0)), ring.mul(g, x))
                    if qzero(new):
                        row[2].pop(j, None)
                    else:
                        row[2][j] = new
        self.rows.append([p, r, c])
        return True


def vkey(v):
    return tuple(sorted(v.items()))


class Graph:
    def __init__(self, n, edges):
        self.n = n
        self.edges = sorted({tuple(sorted(e)) for e in edges})
        self.eset = set(self.edges)

    def has(self, u, v):
        return (min(u, v), max(u, v)) in self.eset

    def triangles(self):
        return [t for t in itertools.combinations(range(self.n), 3)
                if self.has(t[0], t[1]) and self.has(t[0], t[2]) and self.has(t[1], t[2])]

    def cycles(self):
        """Each 4-cycle once, as [u, v, w, x] with u the least vertex and v < x."""
        out = []
        for quad in itertools.combinations(range(self.n), 4):
            for tail in itertools.permutations(quad[1:]):
                cyc = (quad[0],) + tail
                if cyc[1] < cyc[3] and all(self.has(cyc[i], cyc[(i + 1) % 4]) for i in range(4)):
                    out.append(list(cyc))
        return out


def g6_encode(n, edges):
    assert n <= 62
    es = {tuple(sorted(e)) for e in edges}
    bits = [1 if (i, j) in es else 0 for j in range(1, n) for i in range(j)]
    bits += [0] * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2)) for k in range(0, len(bits), 6))


def g6_decode(code):
    n = ord(code[0]) - 63
    bits = [(ord(ch) - 63) >> s & 1 for ch in code[1:] for s in range(5, -1, -1)]
    pairs = [(i, j) for j in range(1, n) for i in range(j)]
    return n, [e for e, b in zip(pairs, bits) if b]


def canonical(codes, labelg=LABELG):
    proc = subprocess.run([labelg, "-q"], input=("\n".join(codes) + "\n").encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)
    return proc.stdout.decode().split()


def iso_map(n, edges_from, edges_to):
    """An isomorphism from one labelled graph to another, by plain backtracking (graphs here are small)."""
    adj1 = [set() for _ in range(n)]
    adj2 = [set() for _ in range(n)]
    for u, v in edges_from:
        adj1[u].add(v)
        adj1[v].add(u)
    for u, v in edges_to:
        adj2[u].add(v)
        adj2[v].add(u)
    order = sorted(range(n), key=lambda v: -len(adj1[v]))
    mapping, used = {}, set()

    def extend(i):
        if i == n:
            return True
        v = order[i]
        for t in range(n):
            if t in used or len(adj2[t]) != len(adj1[v]):
                continue
            if all((mapping[u] in adj2[t]) == (u in adj1[v]) for u in mapping):
                mapping[v] = t
                used.add(t)
                if extend(i + 1):
                    return True
                del mapping[v]
                used.discard(t)
        return False

    if not extend(0):
        raise ValueError("graphs are not isomorphic")
    return mapping


def canonical_graph(n, edges, labelg=LABELG):
    """(canonical g6, Graph on the canonical labels, map original label -> canonical label)."""
    code = canonical([g6_encode(n, edges)], labelg)[0]
    cn, cedges = g6_decode(code)
    return code, Graph(cn, cedges), iso_map(n, [tuple(e) for e in edges], cedges)


class Prover:
    """Case trees over triangle orientations, exact over Q(w).

    order:      "undecided" splits the first triangle whose orientation the node's rows do not decide; "naive" the
                first unsplit triangle.
    fill_open:  None; "sibling" closes an open branch with its sibling's leaf (a plausible sign bug); "drop" omits
                open children (a dropped-child bug).
    overlap:    prefer unit leaves whose pair and edge share a vertex, with zeta not 0 or 3.
    target_pair: only look for a forced unit distance on this pair (the gadgets).
    """

    def __init__(self, g, ring=None, order="undecided", fill_open=None, max_nodes=4000, lam=(1, 0), overlap=False,
                 target_pair=None):
        self.g, self.ring = g, ring or Ring()
        self.order, self.fill_open, self.max_nodes = order, fill_open, max_nodes
        self.lam = (Fr(lam[0]), Fr(lam[1]))
        self.overlap, self.target_pair = overlap, target_pair
        self.nodes = 0
        self.rows = []
        self.tris = g.triangles()
        for cyc in g.cycles():
            u, v, w, x = cyc
            self.rows.append((("c", tuple(cyc)), {u: (F1, F0), v: (-F1, F0), w: (F1, F0), x: (-F1, F0)}))
        self.tri_row = {}
        for t in self.tris:
            for s in (1, -1):
                self.tri_row[(t, s)] = len(self.rows)
                self.rows.append((("t", t, s), self.t_vec(t, s)))

    def t_vec(self, t, s):
        """t(T, s) = e_c - e_a - w^s (e_b - e_a) in this prover's ring."""
        ring = self.ring
        a, b, c = t
        ws = ring.w_plus if s == 1 else ring.w_minus
        vec = {}
        for col, val in ((c, ring.one), (a, qneg(ring.one)), (b, qneg(ws)), (a, ws)):
            vec[col] = qadd(vec.get(col, ring.zero), val)
        return {k: v for k, v in vec.items() if not qzero(v)}

    def closure(self, basis):
        g, ring, n = self.g, self.ring, self.g.n
        nf = [basis.reduce({v: ring.one})[0] for v in range(n)]
        if self.target_pair is None:
            seen = {}
            for v in range(n):
                k = vkey(nf[v])
                if k in seen:
                    return ("collision", seen[k], v, None, None, None)
                seen[k] = v

        def diff(a, b):
            d = dict(nf[a])
            vec_axpy(ring, d, ring.one, nf[b])
            return d

        if self.overlap:
            for a, b in itertools.permutations(range(n), 2):
                if g.has(a, b):
                    continue
                dk = vkey(diff(a, b))
                for p, q in itertools.permutations(range(n), 2):
                    if not g.has(p, q) or not ({a, b} & {p, q}):
                        continue
                    e = diff(p, q)
                    for k in (1, 2, 4, 5):
                        wk = ring.pow_w(k)
                        if vkey({c: ring.mul(wk, x) for c, x in e.items()}) == dk:
                            return ("unit", a, b, p, q, k)
            return None                 # overlap mode: keep splitting until such a relation appears
        dirs = {}
        for p, q in g.edges:
            d = diff(p, q)
            for k in range(6):
                wk = ring.pow_w(k)
                dirs.setdefault(vkey({c: ring.mul(wk, x) for c, x in d.items()}), (p, q, k))
        pairs = ([self.target_pair] if self.target_pair is not None
                 else [(a, b) for a, b in itertools.combinations(range(n), 2) if not g.has(a, b)])
        for a, b in pairs:
            hit = dirs.get(vkey(diff(a, b)))
            if hit is not None:
                return ("unit", a, b) + hit
        return None

    def leaf(self, basis, found, path):
        ring = self.ring
        kind, a, b, p, q, k = found
        target = {a: ring.one}
        target[b] = qsub(target.get(b, ring.zero), ring.one)
        if kind == "unit":
            wk = ring.pow_w(k)
            target[p] = qsub(target.get(p, ring.zero), wk)
            target[q] = qadd(target.get(q, ring.zero), wk)
        resid, comb = basis.reduce({c: x for c, x in target.items() if not qzero(x)})
        assert not resid, "closure without a combination"
        den = 1
        for c in comb.values():
            for x in c:
                den = den * x.denominator // math.gcd(den, x.denominator)
        cycles, ccoef, tris, tcoef = [], [], [], []
        for j in sorted(comb):
            coeff = ring.mul(self.lam, (comb[j][0] * den, comb[j][1] * den))
            label = self.rows[j][0]
            if label[0] == "c":
                cycles.append(list(label[1]))
                ccoef.append(coeff)
            else:
                assert path.get(label[1]) == label[2], "a leaf row that is not on the path"
                tris.append(list(label[1]))
                tcoef.append(coeff)
        scale = ring.mul(self.lam, (Fr(den), F0))
        ints = [x for c in ccoef + tcoef + [scale] for x in c]
        assert all(x.denominator == 1 for x in ints)
        gcd = 0
        for x in ints:
            gcd = math.gcd(gcd, int(x))
        lf = {"cycles": cycles, "cycle_coefficients": [[int(c[0]) // gcd, int(c[1]) // gcd] for c in ccoef],
              "triangles": tris, "triangle_coefficients": [[int(c[0]) // gcd, int(c[1]) // gcd] for c in tcoef],
              "scale": [int(scale[0]) // gcd, int(scale[1]) // gcd], "pair": [a, b]}
        if kind == "unit":
            lf["edge"] = [p, q]
            lf["zeta"] = k
        assert self.check_leaf(lf, path), "the prover's own exact re-check failed"
        return {"leaf": lf}

    def check_leaf(self, lf, path):
        """Exact re-check of a leaf identity in this prover's ring (Fractions)."""
        ring = self.ring
        lhs = {}
        for cyc, c in zip(lf["cycles"], lf["cycle_coefficients"]):
            cc = (Fr(c[0]), Fr(c[1]))
            for vert, sgn in zip(cyc, (1, -1, 1, -1)):
                lhs[vert] = qadd(lhs.get(vert, ring.zero), cc if sgn == 1 else qneg(cc))
        for t, m in zip(lf["triangles"], lf["triangle_coefficients"]):
            mm = (Fr(m[0]), Fr(m[1]))
            for col, val in self.t_vec(tuple(t), path[tuple(t)]).items():
                lhs[col] = qadd(lhs.get(col, ring.zero), ring.mul(mm, val))
        scale = (Fr(lf["scale"][0]), Fr(lf["scale"][1]))
        a, b = lf["pair"]
        tgt = {a: ring.one}
        tgt[b] = qsub(tgt.get(b, ring.zero), ring.one)
        if "edge" in lf:
            p, q = lf["edge"]
            wk = ring.pow_w(lf["zeta"])
            tgt[p] = qsub(tgt.get(p, ring.zero), wk)
            tgt[q] = qadd(tgt.get(q, ring.zero), wk)
        return all(lhs.get(v, ring.zero) == ring.mul(scale, tgt.get(v, ring.zero)) for v in set(lhs) | set(tgt))

    def decided(self, basis, t):
        return any(not basis.reduce(self.t_vec(t, s))[0] for s in (1, -1))

    def build(self, basis=None, path=None):
        if basis is None:
            basis = Basis(self.ring)
            for i, (label, vec) in enumerate(self.rows):
                if label[0] == "c":
                    basis.insert(vec, {i: self.ring.one})
            path = {}
        self.nodes += 1
        if self.nodes > self.max_nodes:
            return None
        found = self.closure(basis)
        if found is not None:
            return self.leaf(basis, found, path)
        t = next((t for t in self.tris if t not in path and (self.order == "naive" or not self.decided(basis, t))),
                 None)
        if t is None:
            return None
        kids = {}
        for s, name in ((1, "plus"), (-1, "minus")):
            child = basis.copy()
            child.insert(self.rows[self.tri_row[(t, s)]][1], {self.tri_row[(t, s)]: self.ring.one})
            kids[name] = self.build(child, {**path, t: s})
        if self.fill_open == "sibling":
            for me, sib in (("plus", "minus"), ("minus", "plus")):
                if kids[me] is None and kids[sib] is not None and "leaf" in kids[sib]:
                    kids[me] = copy.deepcopy(kids[sib])
        node = {"split": list(t)}
        for name in ("plus", "minus"):
            if kids[name] is not None:
                node[name] = kids[name]
            elif self.fill_open != "drop":
                return None
        return node


def tree_leaves(tree):
    """(leaf, path signs, location) for every leaf, depth first, plus before minus."""
    out = []

    def walk(node, path, loc):
        if "leaf" in node:
            out.append((node["leaf"], path, loc))
            return
        t = tuple(node["split"])
        for name, s in (("plus", 1), ("minus", -1)):
            if name in node:
                walk(node[name], {**path, t: s}, loc + "." + name)

    walk(tree, {}, "tree")
    return out


def verdict_of(tree):
    return "tu" if any("edge" in lf for lf, _, _ in tree_leaves(tree)) else "refuted"


# =================================================================================================================
# Part 2. A plain reference checker (independent code, recursion and sets), with one optional deliberate bug.

BUGS = ("wrong-ring", "sign-flip", "repeat-vertex", "missing-child", "int64", "set-lookup", "overwrite-target")


def ref_check(n, edges, verdict, witness, bug=None):
    """Section 4 re-implemented plainly; returns (ok, reason). `bug` switches on exactly one defect."""
    assert bug is None or bug in BUGS
    E = {frozenset(e) for e in edges}
    isint = lambda x: type(x) is int  # noqa: E731

    class Bad(Exception):
        pass

    def need(cond, msg):
        if not cond:
            raise Bad(msg)

    def fix(v):                                     # the int64 bug wraps every sum and product to 64 bits
        return ((v + (1 << 63)) % (1 << 64)) - (1 << 63) if bug == "int64" else v

    def mul(a, b):
        x1, y1 = a
        x2, y2 = b
        yy = -y1 * y2 if bug == "wrong-ring" else y1 * y2          # w^2 = -w - 1 against w^2 = w - 1
        return (fix(x1 * x2 - y1 * y2), fix(x1 * y2 + x2 * y1 + yy))

    wpow = [(1, 0)]
    for _ in range(5):
        wpow.append(mul(wpow[-1], (0, 1)))
    wsign = {1: (0, 1), -1: (1, -1)}

    def vert(x):
        need(isint(x) and 0 <= x < n, f"bad vertex {x!r}")
        return x

    def zw(c):
        need(isinstance(c, list) and len(c) == 2 and all(isint(t) and -B62 < t < B62 for t in c), f"bad Z[w] {c!r}")
        return (c[0], c[1])

    state = {"nodes": 0, "edge": False}

    def visit(node, path, depth):
        state["nodes"] += 1
        need(state["nodes"] <= 100000 and depth <= 64, "tree limits")
        need(isinstance(node, dict), "node is not an object")
        if set(node) == {"leaf"}:
            leaf(node["leaf"], path)
            return
        if bug == "missing-child":
            need("split" in node and set(node) <= {"split", "plus", "minus"}, "split node keys")
        else:
            need(set(node) == {"split", "plus", "minus"}, "split node keys")
        t = node["split"]
        need(isinstance(t, list) and len(t) == 3, "split shape")
        a, b, c = (vert(x) for x in t)
        need(a < b < c, "split not sorted")
        need(frozenset((a, b)) in E and frozenset((a, c)) in E and frozenset((b, c)) in E, "split not a triangle")
        need((a, b, c) not in path, "split twice")
        for name, s in (("plus", 1), ("minus", -1)):
            if name in node:
                visit(node[name], {**path, (a, b, c): s}, depth + 1)

    def leaf(lf, path):
        need(isinstance(lf, dict), "leaf is not an object")
        base = {"cycles", "cycle_coefficients", "triangles", "triangle_coefficients", "scale", "pair"}
        need(set(lf) in (base, base | {"edge", "zeta"}), "leaf keys")
        cyc, cco, tri, tco = lf["cycles"], lf["cycle_coefficients"], lf["triangles"], lf["triangle_coefficients"]
        need(all(isinstance(x, list) for x in (cyc, cco, tri, tco)), "leaf lists")
        need(len(cyc) == len(cco) and len(tri) == len(tco) and len(cyc) <= 4096 and (cyc or tri), "list lengths")
        acc = {}

        def put(v, val):
            x, y = acc.get(v, (0, 0))
            acc[v] = (fix(x + val[0]), fix(y + val[1]))

        for C, l in zip(cyc, cco):
            need(isinstance(C, list) and len(C) == 4, "cycle shape")
            vs = [vert(x) for x in C]
            if bug != "repeat-vertex":
                need(len(set(vs)) == 4, "cycle repeats a vertex")
            need(all(frozenset((vs[i], vs[(i + 1) % 4])) in E and vs[i] != vs[(i + 1) % 4] for i in range(4)),
                 "cycle edge missing")
            lz = zw(l)
            need(lz != (0, 0), "zero coefficient")
            for v, sg in zip(vs, (1, -1, 1, -1)):
                put(v, lz if sg == 1 else (-lz[0], -lz[1]))
        for T, m in zip(tri, tco):
            need(isinstance(T, list) and len(T) == 3 and all(isint(x) for x in T), "triangle shape")
            if bug == "set-lookup":                 # finds the split by its vertex set, then uses T's own order
                keys = [k for k in path if set(k) == set(T)]
                need(keys, "triangle not on the path")
                s = path[keys[0]]
            else:
                need(tuple(T) in path, "triangle not on the path")
                s = path[tuple(T)]
            if bug == "sign-flip":
                s = -s
            a, b, c = T
            mz = zw(m)
            need(mz != (0, 0), "zero coefficient")
            ws = wsign[s]
            for v, val in ((c, (1, 0)), (a, (-1, 0)), (b, (-ws[0], -ws[1])), (a, ws)):   # e_c - e_a - w^s(e_b - e_a)
                put(v, mul(mz, val))
        sc = zw(lf["scale"])
        need(sc != (0, 0), "zero scale")
        P = lf["pair"]
        need(isinstance(P, list) and len(P) == 2, "pair shape")
        a, b = vert(P[0]), vert(P[1])
        need(a != b, "pair not distinct")
        tgt = {}

        def tput(v, val):
            if bug == "overwrite-target":
                tgt[v] = val
            else:
                x, y = tgt.get(v, (0, 0))
                tgt[v] = (x + val[0], y + val[1])

        tput(a, (1, 0))
        tput(b, (-1, 0))
        if "edge" in lf:
            Q = lf["edge"]
            need(isinstance(Q, list) and len(Q) == 2, "edge shape")
            p, q = vert(Q[0]), vert(Q[1])
            need(p != q and frozenset((p, q)) in E, "edge is not an edge")
            need(frozenset((a, b)) not in E, "pair is an edge")
            k = lf["zeta"]
            need(isint(k) and 0 <= k <= 5, "zeta range")
            tput(p, (-wpow[k][0], -wpow[k][1]))
            tput(q, wpow[k])
            state["edge"] = True
        for v in range(n):
            need(acc.get(v, (0, 0)) == mul(sc, tgt.get(v, (0, 0))), f"identity fails at vertex {v}")

    try:
        need(isinstance(verdict, str) and verdict in ("refuted", "tu"), "verdict")
        need(isinstance(witness, dict) and set(witness) == {"tri"}, "witness keys")
        need(isinstance(witness["tri"], dict) and set(witness["tri"]) == {"tree"}, "tri keys")
        visit(witness["tri"]["tree"], {}, 0)
        need((verdict == "tu") == state["edge"], "verdict does not match the leaves")
    except Bad as exc:
        return False, str(exc)
    return True, ""


# =================================================================================================================
# Part 3. Fixtures and the harness.

class Fx:
    """A certificate record together with its graph."""

    def __init__(self, name, code, g, verdict, tree):
        self.name, self.code, self.g = name, code, g
        self.rec = {"g6": code, "verdict": verdict, "witness": {"tri": {"tree": tree}}}

    @property
    def tree(self):
        return self.rec["witness"]["tri"]["tree"]

    def mutate(self, fn):
        new = copy.copy(self)
        new.rec = copy.deepcopy(self.rec)
        fn(new.rec)
        return new

    def line(self):
        return json.dumps(self.rec, separators=(",", ":"))


def T(rec):
    return rec["witness"]["tri"]["tree"]


def node_at(tree, loc):
    node = tree
    for step in loc.split(".")[1:]:
        node = node[step]
    return node


def first_leaf(tree, pred=lambda lf: True):
    for lf, path, loc in tree_leaves(tree):
        if pred(lf):
            return lf, path, loc
    raise AssertionError("no such leaf")


def fixture(name, n, edges, labelg, **kw):
    code, g, mp = canonical_graph(n, edges, labelg)
    tree = Prover(g, **kw).build()
    assert tree is not None, f"the test prover found no certificate for {name}"
    return Fx(name, code, g, verdict_of(tree), tree)


def float_check(fx):
    """Every leaf identity evaluated at random complex points with w = e^(i pi/3) (independent of Z[w] code)."""
    w = cmath.exp(1j * math.pi / 3)
    rnd = __import__("random").Random(20260926)
    z = [complex(rnd.gauss(0, 1), rnd.gauss(0, 1)) for _ in range(fx.g.n)]
    val = lambda p: p[0] + p[1] * w  # noqa: E731
    for lf, path, loc in tree_leaves(fx.tree):
        terms = [val(l) * (z[u] - z[v] + z[x] - z[y]) for (u, v, x, y), l in zip(lf["cycles"],
                                                                                  lf["cycle_coefficients"])]
        for (a, b, c), m in zip(lf["triangles"], lf["triangle_coefficients"]):
            terms.append(val(m) * (z[c] - z[a] - w ** path[(a, b, c)] * (z[b] - z[a])))
        a, b = lf["pair"]
        tgt = z[a] - z[b]
        if "edge" in lf:
            p, q = lf["edge"]
            tgt -= w ** lf["zeta"] * (z[p] - z[q])
        rhs = val(lf["scale"]) * tgt
        size = sum(abs(t) for t in terms) + abs(rhs) + 1.0
        if abs(sum(terms) - rhs) > 1e-9 * size:
            return False
    return True


class Harness:
    def __init__(self):
        self.lines = []
        self.failures = []

    def expect(self, ok, text):
        self.lines.append(("ok  " if ok else "FAIL") + "  " + text)
        print(self.lines[-1], flush=True)
        if not ok:
            self.failures.append(text)

    def section(self, title):
        print(f"\n== {title} ==", flush=True)

    def tv(self, fx):
        return TV.verify_tri_witness(fx.g.n, fx.g.edges, fx.rec["verdict"], fx.rec["witness"])

    def ref(self, fx, bug=None):
        return ref_check(fx.g.n, fx.g.edges, fx.rec["verdict"], fx.rec["witness"], bug)

    def accept(self, fx, label, floats=True):
        ok, reason, st = self.tv(fx)
        rok, rreason = self.ref(fx)
        fl = float_check(fx) if ok and floats else None
        good = ok and rok and fl is not False
        detail = (f"{fx.rec['verdict']}, {st['leaves']} leaves, depth {st['depth']}"
                  + (", float check ok" if fl else "") if ok else f"tri_verify said: {reason}")
        if not rok:
            detail += f"; reference said: {rreason}"
        self.expect(good, f"ACCEPT  {label}  [{detail}]")
        return good

    def reject(self, fx, label, expect, sharp=None):
        ok, reason, _ = self.tv(fx)
        rok, rreason = self.ref(fx)
        good = (not ok) and expect in reason and not rok
        text = f"REJECT  {label}\n            -> {reason if not ok else 'ACCEPTED (wrong)'}"
        if expect not in reason:
            text += f"\n            (expected the reason to contain {expect!r})"
        if rok:
            text += "\n            (the reference checker ACCEPTED it: disagreement)"
        if sharp is not None:
            sok, sreason = self.ref(fx, bug=sharp)
            good = good and sok
            text += (f"\n            a checker with the bug '{sharp}' ACCEPTS it, so this control catches that bug"
                     if sok else f"\n            the checker with the bug '{sharp}' did NOT accept it ({sreason}): "
                                 f"the control is not sharp")
        self.expect(good, text)

    def cli(self, label, content, args=(), expect_ok=True, expect=None, graphs=None, workdir=None):
        path = Path(workdir) / "certs.jsonl"
        path.write_bytes(content)
        argv = [sys.executable, str(TV_PATH), str(path), *args]
        if graphs is not None:
            gpath = Path(workdir) / "graphs.g6"
            gpath.write_bytes(graphs)
            argv += ["--graphs", str(gpath)]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = (proc.stdout + proc.stderr).decode(errors="replace").strip()
        good = (proc.returncode == 0) == expect_ok and (expect is None or expect in out)
        self.expect(good, f"CLI {'ACCEPT' if expect_ok else 'REJECT'}  {label}\n            -> exit {proc.returncode}: "
                          f"{out[:300]}")
        return out


# =================================================================================================================
# Part 4. Graphs.

K3 = (3, [(0, 1), (0, 2), (1, 2)])
K4 = (4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
K113 = (5, [(0, 1)] + [(0, t) for t in (2, 3, 4)] + [(1, t) for t in (2, 3, 4)])
W5 = (6, [(0, i) for i in range(1, 6)] + [(i, i % 5 + 1) for i in range(1, 6)])
W6 = (7, [(0, i) for i in range(1, 7)] + [(i, i % 6 + 1) for i in range(1, 7)])
# Moser spindle: apex 0; rhombus 0,1,2,3 (triangles 012 and 123); rhombus 0,4,5,6 (triangles 045 and 456); edge 3-6
MOSER = (7, [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (0, 4), (0, 5), (4, 5), (4, 6), (5, 6), (3, 6)])
K9 = (9, list(itertools.combinations(range(9), 2)))
TWO_LEVEL = "FCY^O"         # 7 vertices, 10 edges: open at the root, closed by a two-level tree (the only one
                            # among connected 7-vertex graphs of minimum degree 2, with this prover's split order)
THREE_LEVEL = "G?bLbk"      # 8 vertices, 12 edges: needs three levels
OVERLAP_GRAPHS = ("EUZ_", "F?zTo", "FCpfw")
# (23,65) Mode-74 tree samples (levels 15, 17, 18): refuted trees with splits and a 30-leaf tu tree
REAL = [("level-15 sample, refuted", "N?@HAAOE?BsHB_Kcw[O"),
        ("level-17 sample, refuted, g6 with a backslash", "PGCW?UOH@G?USOO__\\cOi_A{"),
        ("level-18 sample, refuted", "Q_OWs??G@E_S@LCG@Gi?flOR_k?"),
        ("level-18 sample, tu", "Q@?A?qK_AH?wAdGCAaYQQg`RoW?")]


def moser_embedding():
    """The Moser spindle in the plane (original labels), as complex numbers."""
    s3 = math.sqrt(3)
    th = 2 * math.asin(1 / (2 * s3))
    e = lambda a: cmath.exp(1j * a)  # noqa: E731
    return {0: 0j, 1: e(math.pi / 6), 2: e(-math.pi / 6), 3: s3 + 0j,
            4: e(th + math.pi / 6), 5: e(th - math.pi / 6), 6: s3 * e(th)}


def w6_embedding():
    return {0: 0j, **{i: cmath.exp(1j * math.pi / 3 * (i - 1)) for i in range(1, 7)}}


def check_embedding(n, edges, f):
    es = {frozenset(e) for e in edges}
    pts_distinct = all(abs(f[a] - f[b]) > 1e-6 for a, b in itertools.combinations(range(n), 2))
    edges_unit = all(abs(abs(f[a] - f[b]) - 1) < 1e-9 for a, b in edges)
    nonedges_not_unit = all(abs(abs(f[a] - f[b]) - 1) > 1e-6 for a, b in itertools.combinations(range(n), 2)
                            if frozenset((a, b)) not in es)
    return pts_distinct and edges_unit, nonedges_not_unit


def follow(tree, f):
    """The root-to-leaf path the embedding f follows; returns (leaf or None if a child is missing, path, loc)."""
    w = cmath.exp(1j * math.pi / 3)
    node, path, loc = tree, {}, "tree"
    while "leaf" not in node:
        a, b, c = node["split"]
        if abs(f[c] - f[a] - w * (f[b] - f[a])) < 1e-9:
            s = 1
        else:
            assert abs(f[c] - f[a] - (1 / w) * (f[b] - f[a])) < 1e-9
            s = -1
        path[(a, b, c)] = s
        name = "plus" if s == 1 else "minus"
        loc += "." + name
        if name not in node:
            return None, path, loc
        node = node[name]
    return node["leaf"], path, loc


def value_at(lf, path, f):
    """(|sum of the leaf's relations at f|, |scale * target at f|): relations are evaluated with their TRUE geometry
    (an unsorted entry is evaluated literally, as a set-lookup checker would use it)."""
    w = cmath.exp(1j * math.pi / 3)
    val = lambda p: p[0] + p[1] * w  # noqa: E731
    lhs = sum(val(l) * (f[u] - f[v] + f[x] - f[y]) for (u, v, x, y), l in zip(lf["cycles"], lf["cycle_coefficients"]))
    for t, m in zip(lf["triangles"], lf["triangle_coefficients"]):
        a, b, c = t
        s = path[tuple(sorted(t))]
        lhs += val(m) * (f[c] - f[a] - w ** s * (f[b] - f[a]))
    a, b = lf["pair"]
    tgt = f[a] - f[b]
    if "edge" in lf:
        p, q = lf["edge"]
        tgt -= w ** lf["zeta"] * (f[p] - f[q])
    return abs(lhs), abs(val(lf["scale"]) * tgt)


# =================================================================================================================
# Part 5. The controls.

def run_selftest(labelg):
    H = Harness()
    t_start = time.time()
    print(f"module under test: {TV_PATH} sha256 {TV_SHA256}", flush=True)
    gadgets = json.loads((DATA / "tu-gadgets.json").read_text())

    # ---------------------------------------------------------------------------------------------------------
    H.section("positive controls: tri_verify ACCEPTS, the reference agrees, every leaf passes the float check")
    fk4 = fixture("K4", *K4, labelg)
    H.accept(fk4, "K4, refuted (closed at the root)")
    fk113 = fixture("K_{1,1,3}", *K113, labelg)
    H.accept(fk113, "K_{1,1,3}, refuted (closed at the root)")
    fw5 = fixture("W5", *W5, labelg)
    single = len(tree_leaves(fw5.tree)) == 1 and "leaf" in fw5.tree
    H.expect(single, "the W5 wheel closes at the root with no split: its tree is a single leaf")
    H.accept(fw5, "W5 wheel, refuted, a single-leaf tree (closed at the root, no split)")
    gadget_fx = []
    for i, gd in enumerate(gadgets):
        code, g, mp = canonical_graph(gd["n"], [tuple(e) for e in gd["edges"]], labelg)
        a, b = sorted((mp[gd["pair"][0]], mp[gd["pair"][1]]))
        tree = Prover(g, target_pair=(a, b)).build()
        fx = Fx(f"gadget {i}", code, g, verdict_of(tree), tree)
        lf = tree["leaf"]
        gadget_fx.append(fx)
        H.accept(fx, f"TU gadget {i} ({code}), tu on its own pair {[a, b]} by rhombus rows alone "
                     f"(edge {lf['edge']}, zeta {lf['zeta']})")
        H.expect(not lf["triangles"] and lf["zeta"] in (0, 3) and set(lf["pair"]) == {a, b},
                 f"gadget {i}: the forced pair is the gadget's pair, with rhombus rows only and zeta in {{0, 3}}")
    n2, e2 = g6_decode(TWO_LEVEL)
    f2 = fixture("two-level", n2, e2, labelg)
    st2 = H.tv(f2)[2]
    H.expect(st2["depth"] == 2 and st2["leaves"] == 4 and Prover(f2.g).closure(Basis(Ring())) is None,
             f"{TWO_LEVEL} ({f2.code}) is open at the root and closes with a two-level split tree")
    H.accept(f2, f"two-level split tree on {f2.code}")
    n3, e3 = g6_decode(THREE_LEVEL)
    f3 = fixture("three-level", n3, e3, labelg)
    H.accept(f3, f"three-level split tree on {f3.code}")
    real_fx = []
    for label, code in REAL:
        n, edges = g6_decode(code)
        fx = fixture(label, n, edges, labelg, max_nodes=400)
        real_fx.append(fx)
        H.accept(fx, f"{label}: {code}")
    # overlapping pair and edge (amendment 2): a == p, b == q, a == q, b == p, with zeta not in {0, 3}
    kinds = {}
    for code in OVERLAP_GRAPHS:
        n, edges = g6_decode(code)
        fx = fixture("overlap", n, edges, labelg, overlap=True)
        for lf, path, loc in tree_leaves(fx.tree):
            if "edge" in lf:
                (a, b), (p, q) = lf["pair"], lf["edge"]
                for kind, hit in (("a == p", a == p), ("b == q", b == q), ("a == q", a == q), ("b == p", b == p)):
                    if hit and kind not in kinds:
                        kinds[kind] = (fx, loc, lf)
    for kind in ("a == p", "b == q", "a == q", "b == p"):
        if kind in kinds:
            fx, loc, lf = kinds[kind]
            H.accept(fx, f"overlapping target, {kind}: {fx.code} {loc} pair {lf['pair']} edge {lf['edge']} "
                         f"zeta {lf['zeta']}")
    H.expect("a == p" in kinds, "an accepted fixture has a unit leaf with a == p (the target accumulates)")
    if "a == p" in kinds:
        fx = kinds["a == p"][0]
        bad, reason = H.ref(fx, bug="overwrite-target")
        H.expect(not bad, f"a checker that overwrites target entries instead of adding them REJECTS the a == p "
                          f"fixture ({reason}): the fixture is sharp")
    # zeta coverage
    zetas = sorted({lf["zeta"] for fx in [*gadget_fx, f2, f3, *real_fx, *(v[0] for v in kinds.values())]
                    for lf, _, _ in tree_leaves(fx.tree) if "edge" in lf})
    H.expect(zetas == [0, 1, 2, 3, 4, 5], f"accepted unit leaves use every zeta in 0..5 (seen {zetas})")
    # K4 by hand: a refuted two-level tree with triangle-only leaves and rhombus-only leaves
    tri_leaf = {"cycles": [], "cycle_coefficients": [], "triangles": [[0, 1, 2], [0, 1, 3]],
                "triangle_coefficients": [[1, 0], [-1, 0]], "scale": [1, 0], "pair": [2, 3]}
    rh_leaf = {"cycles": [[0, 1, 2, 3], [0, 1, 3, 2]], "cycle_coefficients": [[1, 0], [1, 0]], "triangles": [],
               "triangle_coefficients": [], "scale": [2, 0], "pair": [0, 1]}
    k4tree = {"split": [0, 1, 2],
              "plus": {"split": [0, 1, 3], "plus": {"leaf": tri_leaf}, "minus": {"leaf": rh_leaf}},
              "minus": {"split": [0, 1, 3], "plus": {"leaf": rh_leaf}, "minus": {"leaf": tri_leaf}}}
    fk4h = Fx("K4 by hand", fk4.code, fk4.g, "refuted", copy.deepcopy(k4tree))
    H.accept(fk4h, "K4, hand-built two-level tree: same-sign leaves close on triangle rows alone (cycles EMPTY), "
                   "mixed-sign leaves on rhombus rows alone (triangles EMPTY)")
    # multiplying a whole leaf by lambda in Z[w] keeps it valid
    def times(lam):
        def fn(rec):
            for lf, _, _ in tree_leaves(T(rec)):
                for key in ("cycle_coefficients", "triangle_coefficients"):
                    lf[key] = [list(TV.zmul(tuple(c), lam)) for c in lf[key]]
                lf["scale"] = list(TV.zmul(tuple(lf["scale"]), lam))
        return fn
    H.accept(f2.mutate(times((2, 3))), f"{f2.code} with every leaf multiplied by 2 + 3w (Z[w] products in the "
                                       f"coefficients and the scale)")
    H.accept(f3.mutate(times((0, 1))), f"{f3.code} with every leaf multiplied by the unit w")
    # coefficient bound: 2^62 - 1 accepted (K_{1,1,3} collision written with coefficients +-(2^62 - 1)(1 + w))
    code113, g113, mp113 = canonical_graph(*K113, labelg)
    x, y = mp113[0], mp113[1]
    t1, t2, t3 = (mp113[v] for v in (2, 3, 4))
    L = B62 - 1

    def k113_leaf(l1, l2, sc):
        return {"leaf": {"cycles": [[x, t1, y, t2], [x, t1, y, t3]], "cycle_coefficients": [l1, l2],
                         "triangles": [], "triangle_coefficients": [], "scale": sc, "pair": [t3, t2]}}
    fbig = Fx("bound", code113, g113, "refuted", k113_leaf([L, L], [-L, -L], [L, L]))
    H.accept(fbig, "coefficients and scale with entries +-(2^62 - 1), the largest allowed")
    # exact arithmetic: intermediate sums of 2^64 that cancel
    cyc0 = rh_leaf["cycles"][0]
    fk4b = Fx("K4 big sums", fk4.code, fk4.g, "refuted", {"leaf": copy.deepcopy(rh_leaf)})

    def add_copies(total_sign):
        def fn(rec):
            lf = T(rec)["leaf"]
            for sgn in total_sign:
                for c in ([L, 0], [L, 0], [L, 0], [L, 0], [4, 0]):   # these five sum to 2^64
                    lf["cycles"].append(list(cyc0))
                    lf["cycle_coefficients"].append([sgn * c[0], 0])
        return fn
    H.accept(fk4b.mutate(add_copies((1, -1))), "K4 leaf plus copies of one cycle summing to +2^64 and to -2^64 "
                                               "(partial sums above 2^63, exact total unchanged)")
    # duplicates inside a leaf are allowed; 4096 cycles is the limit
    def dup_pairs(count):
        def fn(rec):
            lf = T(rec)["leaf"]
            rot = cyc0[1:] + cyc0[:1]               # r(rotated C) = -r(C)
            for _ in range(count):
                lf["cycles"] += [list(cyc0), list(rot)]
                lf["cycle_coefficients"] += [[1, 0], [1, 0]]
        return fn
    H.accept(fk4b.mutate(dup_pairs(1)), "a leaf listing one 4-cycle twice (duplicates are not forbidden)")
    H.accept(fk4b.mutate(dup_pairs(2047)), "a leaf with exactly 4096 cycles (the limit)", floats=False)
    # depth and node limits on K9 (84 triangles; the K4 rhombus leaf is valid everywhere)
    code9, g9, _ = canonical_graph(*K9, labelg)
    tris9 = g9.triangles()

    def caterpillar(depth):
        node = {"leaf": rh_leaf}
        for d in reversed(range(depth)):
            node = {"split": list(tris9[d]), "plus": node, "minus": {"leaf": rh_leaf}}
        return node

    def bushy(splits):
        root = {"t": {"leaf": rh_leaf}}
        queue = collections.deque([(root, "t", 0)])
        for _ in range(splits):
            parent, key, depth = queue.popleft()
            node = {"split": list(tris9[depth]), "plus": {"leaf": rh_leaf}, "minus": {"leaf": rh_leaf}}
            parent[key] = node
            queue.append((node, "plus", depth + 1))
            queue.append((node, "minus", depth + 1))
        return root["t"]
    f64 = Fx("K9 depth 64", code9, g9, "refuted", caterpillar(64))
    H.accept(f64, "K9 caterpillar with 64 splits on one path (depth 64, the limit)", floats=False)
    fnodes = Fx("K9 99,999 nodes", code9, g9, "refuted", bushy(49999))
    H.accept(fnodes, "K9 tree with 99,999 nodes (the largest binary tree within 100,000)", floats=False)

    # ---------------------------------------------------------------------------------------------------------
    H.section("red controls: tri_verify REJECTS with the specific reason (and the reference also rejects)")
    base = f2                                     # a genuine two-level tu tree
    root_t = base.tree["split"]
    na = next(v for v in range(base.g.n) if not base.g.has(root_t[0], v) and v != root_t[0])

    def boolify(triple):
        """The triple with its vertex 0 or 1 written false or true (equal and hash-equal to the int in Python),
        else with its first vertex written as a float."""
        for i, v in enumerate(triple):
            if v in (0, 1):
                return [bool(v) if j == i else u for j, u in enumerate(triple)]
        return [float(triple[0])] + list(triple[1:])
    rule1 = [
        ("split on a non-triangle", lambda r: T(r).__setitem__("split", sorted([root_t[0], root_t[1], na])),
         "is not a triangle of G"),
        ("split triple not sorted", lambda r: T(r).__setitem__("split", [root_t[0], root_t[2], root_t[1]]),
         "is not a sorted triple"),
        ("split vertex out of range", lambda r: T(r).__setitem__("split", [root_t[0], root_t[1], 99]),
         "split: vertex out of range"),
        (f"split vertex {root_t[0]} written {root_t[0] - base.g.n} (a negative index aliases it in Python)",
         lambda r: T(r).__setitem__("split", [root_t[0] - base.g.n, root_t[1], root_t[2]]),
         "split: vertex out of range"),
        ("split with four vertices", lambda r: T(r).__setitem__("split", root_t + [6]), "expected a triple"),
        (f"split vertex written as a bool or float: {boolify(root_t)}",
         lambda r: T(r).__setitem__("split", boolify(root_t)), "must be JSON integers"),
        ("the same triangle split twice on one path",
         lambda r: T(r).__setitem__("plus", {"split": list(root_t), "plus": T(r)["plus"], "minus": T(r)["minus"]}),
         "split twice on one root-to-leaf path"),
        ("a split node with its minus child dropped", lambda r: T(r).pop("minus"), "missing keys ['minus']"),
        ("a split child that is a list, not a node", lambda r: T(r).__setitem__("minus", []),
         "expected a node object"),
        ("a split child that is an empty object", lambda r: T(r).__setitem__("minus", {}),
         "a node needs exactly the key 'leaf'"),
        ("a node with both split and leaf keys", lambda r: T(r).__setitem__("leaf", rh_leaf), "extra keys"),
        ("a leaf node with an extra key", lambda r: node_at(T(r), first_leaf(T(r))[2]).__setitem__("note", 1),
         "extra keys ['note']"),
    ]
    for label, fn, expect in rule1:
        H.reject(base.mutate(fn), f"rule 1: {label}", expect)
    H.reject(Fx("K9 depth 65", code9, g9, "refuted", caterpillar(65)),
             "rule 1: K9 caterpillar with 65 splits on one path", "deeper than 64")
    H.reject(Fx("K9 100,001 nodes", code9, g9, "refuted", bushy(50000)),
             "rule 1: K9 tree with 100,001 nodes", "more than 100000 nodes")

    lf0, path0, loc0 = first_leaf(base.tree, lambda lf: lf["triangles"] and lf["cycles"])

    def at_leaf(fn):
        def mut(rec):
            fn(node_at(T(rec), loc0)["leaf"])
        return mut
    other_tri = next(t for t in base.g.triangles() if t not in path0)
    cu, cv, cw_, cx = lf0["cycles"][0]
    cz = next(z for z in range(base.g.n) if z not in (cu, cv, cw_) and not (base.g.has(cw_, z) and base.g.has(z, cu)))
    rule2 = [
        ("a leaf triangle that is not split on its path",
         at_leaf(lambda lf: lf["triangles"].__setitem__(0, list(other_tri))), "is not a triangle split on the path"),
        (f"a leaf triangle written with a bool or float vertex: {boolify(lf0['triangles'][0])}",
         at_leaf(lambda lf: lf["triangles"].__setitem__(0, boolify(lf["triangles"][0]))), "must be JSON integers"),
        (f"a cycle that is not a 4-cycle of G: {[cu, cv, cw_, cz]}",
         at_leaf(lambda lf: lf["cycles"].__setitem__(0, [cu, cv, cw_, cz])), "is not a 4-cycle of G"),
        ("a cycle with a repeated vertex", at_leaf(lambda lf: lf["cycles"].__setitem__(
            0, [lf["cycles"][0][0], lf["cycles"][0][1], lf["cycles"][0][0], lf["cycles"][0][3]])),
         "is not pairwise distinct"),
        ("a cycle of three vertices", at_leaf(lambda lf: lf["cycles"][0].pop()), "expected four vertices"),
        ("a cycle vertex out of range", at_leaf(lambda lf: lf["cycles"][0].__setitem__(3, 23)),
         "cycles[0]: vertex out of range"),
        ("a cycle vertex v written v - n (a negative index aliases it in Python)",
         at_leaf(lambda lf: lf["cycles"][0].__setitem__(3, lf["cycles"][0][3] - base.g.n)),
         "cycles[0]: vertex out of range"),
        ("cycle_coefficients shorter than cycles", at_leaf(lambda lf: lf["cycle_coefficients"].pop()),
         "as long as cycles"),
        ("triangle_coefficients longer than triangles", at_leaf(lambda lf: lf["triangle_coefficients"].append([1, 0])),
         "as long as triangles"),
        ("a coefficient given as a float", at_leaf(lambda lf: lf["cycle_coefficients"].__setitem__(
            0, [float(lf["cycle_coefficients"][0][0]), lf["cycle_coefficients"][0][1]])), "must be JSON integers"),
        ("a coefficient given as a bool", at_leaf(lambda lf: lf["triangle_coefficients"].__setitem__(0, [True, 0])),
         "must be JSON integers"),
        ("a coefficient that is not a pair", at_leaf(lambda lf: lf["cycle_coefficients"].__setitem__(0, [1, 0, 0])),
         "expected a Z[w] pair"),
        ("a coefficient [0, 0] (appended to a valid identity, which it leaves unchanged)",
         at_leaf(lambda lf: (lf["cycles"].append(list(lf["cycles"][0])), lf["cycle_coefficients"].append([0, 0]))),
         "cycle_coefficients[1]: coefficient is [0, 0]"),
        ("a triangle coefficient [0, 0] (appended to a valid identity, which it leaves unchanged)",
         at_leaf(lambda lf: (lf["triangles"].append(list(lf["triangles"][0])),
                             lf["triangle_coefficients"].append([0, 0]))), "triangle_coefficients"),
        ("both lists empty", at_leaf(lambda lf: lf.update(cycles=[], cycle_coefficients=[], triangles=[],
                                                          triangle_coefficients=[])), "both empty"),
        ("'cycles' given as a string", at_leaf(lambda lf: lf.__setitem__("cycles", "0123")), "cycles: expected a list"),
        ("'triangles' given as an object", at_leaf(lambda lf: lf.__setitem__("triangles", {})),
         "triangles: expected a list"),
        ("a triangle coefficient that is not a pair",
         at_leaf(lambda lf: lf["triangle_coefficients"].__setitem__(0, [1])), "triangle_coefficients[0]: expected a Z[w] pair"),
        ("a scale of three integers", at_leaf(lambda lf: lf.__setitem__("scale", lf["scale"] + [0])),
         "scale: expected a Z[w] pair"),
        ("a leaf value that is a list, not an object",
         lambda r: node_at(T(r), loc0).__setitem__("leaf", []), "leaf: expected an object"),
        ("a scale given as a string", at_leaf(lambda lf: lf.__setitem__("scale", ["1", 0])), "must be JSON integers"),
    ]
    for label, fn, expect in rule2:
        H.reject(base.mutate(fn), f"rule 2: {label}", expect)
    # coefficient bound: 2^62 in one entry, and -2^62, with the identity scaled to stay true
    H.reject(Fx("bound", code113, g113, "refuted", k113_leaf([B62, 0], [-B62, 0], [B62, 0])),
             "rule 2: coefficients and scale 2^62 (identity true, only the bounds fail)",
             "cycle_coefficients[0]: Z[w] entry of absolute value 2^62 or more")
    H.reject(Fx("bound", code113, g113, "refuted", k113_leaf([L, -B62], [-L, B62], [L, -B62])),
             "rule 2: an entry of -2^62 (identity true, only the bounds fail)",
             "cycle_coefficients[0]: Z[w] entry of absolute value 2^62 or more")
    for sgn in (1, -1):
        H.reject(fk4b.mutate(lambda r, sgn=sgn: (T(r)["leaf"]["cycles"].extend([list(cyc0), cyc0[1:] + cyc0[:1]]),
                                                 T(r)["leaf"]["cycle_coefficients"].extend([[sgn * B62, 0]] * 2))),
                 f"rule 2: a cancelling pair of cycle coefficients {'-' if sgn < 0 else ''}2^62 on the K4 leaf "
                 f"(identity true with scale 2; only the coefficient bound fails)",
                 "cycle_coefficients[2]: Z[w] entry of absolute value 2^62 or more")
    q60 = 1 << 60
    big_scale = {"leaf": {"cycles": [[x, t1, y, t2]] * 4 + [[x, t1, y, t3]] * 4,
                          "cycle_coefficients": [[q60, 0]] * 4 + [[-q60, 0]] * 4, "triangles": [],
                          "triangle_coefficients": [], "scale": [B62, 0], "pair": [t3, t2]}}
    H.reject(Fx("bound", code113, g113, "refuted", copy.deepcopy(big_scale)),
             "rule 2: scale 2^62 with every coefficient 2^60 (identity true, only the scale's bound fails)",
             "leaf.scale: Z[w] entry of absolute value 2^62 or more")
    H.reject(fk4b.mutate(dup_pairs(2048)), "rule 2: a leaf with 4098 cycles (identity true, only the count fails)",
             "more than 4096 entries")
    # a cycle vertex written false (equal and hash-equal to 0, so adj[False] would silently work)
    H.reject(fk4h.mutate(lambda r: node_at(T(r), "tree.plus.minus")["leaf"]["cycles"].__setitem__(0, [False, 1, 2, 3])),
             "rule 2: a cycle vertex written false instead of 0: [false, 1, 2, 3]", "must be JSON integers")
    H.reject(fk4h.mutate(lambda r: node_at(T(r), "tree.plus.plus")["leaf"]["triangles"].__setitem__(0, [0, 1])),
             "rule 2: a leaf triangle with two vertices", "expected a triple")
    # triangle coefficients at the bound: the triangle-only K4 leaf scaled by 2^62 - 1 (accepted) and by 2^62
    def tri_scaled(lam):
        def fn(rec):
            lf = node_at(T(rec), "tree.plus.plus")["leaf"]
            lf["triangle_coefficients"] = [[lam, 0], [-lam, 0]]
            lf["scale"] = [lam, 0]
        return fn
    H.accept(fk4h.mutate(tri_scaled(L)), "triangle coefficients and scale of 2^62 - 1 in a triangle-only leaf")
    H.reject(fk4h.mutate(tri_scaled(B62)), "rule 2: triangle coefficients 2^62 in a triangle-only leaf (identity true, "
             "only the bounds fail)", "triangle_coefficients[0]: Z[w] entry of absolute value 2^62 or more")

    def tri_cancel(rec):
        lf = node_at(T(rec), "tree.plus.plus")["leaf"]
        lf["triangles"] += [[0, 1, 2], [0, 1, 2]]
        lf["triangle_coefficients"] += [[B62, 0], [-B62, 0]]
    H.reject(fk4h.mutate(tri_cancel), "rule 2: a cancelling pair of triangle coefficients +-2^62 (identity true with "
             "scale 1; only the coefficient bound fails)",
             "triangle_coefficients[2]: Z[w] entry of absolute value 2^62 or more")
    # leaf triangle split only in the sibling subtree
    k4bad = copy.deepcopy(k4tree)
    k4bad["minus"] = {"leaf": copy.deepcopy(tri_leaf)}
    H.reject(Fx("K4", fk4.code, fk4.g, "refuted", k4bad),
             "rule 2: a leaf using a triangle split only in its sibling subtree", "is not a triangle split on the path")
    # zero scale, with a true identity 0 = 0 (a cycle and its rotation cancel)
    rot0 = cyc0[1:] + cyc0[:1]
    zero_leaf = {"cycles": [list(cyc0), list(rot0)], "cycle_coefficients": [[1, 0], [1, 0]], "triangles": [],
                 "triangle_coefficients": [], "scale": [0, 0], "pair": [0, 1]}
    H.reject(Fx("K4", fk4.code, fk4.g, "refuted", {"leaf": zero_leaf}),
             "rule 2: scale [0, 0] with relations summing to 0 (0 = 0 * target holds; only the scale rule fails)",
             "the scale is [0, 0]")

    # rule 3
    lfu, pathu, locu = first_leaf(base.tree, lambda lf: "edge" in lf)

    def at_unit(fn):
        def mut(rec):
            fn(node_at(T(rec), locu)["leaf"])
        return mut
    ea, eb = lfu["edge"]
    k1a, k1b = mp113[2], mp113[3]                 # a non-adjacent pair of K_{1,1,3}
    rule3 = [
        ("a pair with one vertex twice, relations summing to 0 (0 = scale * 0 holds)",
         lambda r: T(r).__setitem__("leaf", {**zero_leaf, "scale": [1, 0], "pair": [2, 2]}), "must be distinct",
         fk4, "refuted"),
        ("a pair vertex out of range", at_unit(lambda lf: lf.__setitem__("pair", [lf["pair"][0], 7])),
         "pair: vertex out of range", base, None),
        ("a pair vertex v written v - n (a negative index aliases it in Python)",
         at_unit(lambda lf: lf.__setitem__("pair", [lf["pair"][0], lf["pair"][1] - base.g.n])),
         "pair: vertex out of range", base, None),
        ("zeta without edge", at_unit(lambda lf: lf.pop("edge")), "'edge' and 'zeta' must appear together",
         base, None),
        ("edge without zeta", at_unit(lambda lf: lf.pop("zeta")), "'edge' and 'zeta' must appear together",
         base, None),
        ("an edge with p == q", at_unit(lambda lf: lf.__setitem__("edge", [ea, ea])), "must be distinct", base, None),
        ("a pair of one vertex", at_unit(lambda lf: lf.__setitem__("pair", lf["pair"][:1])), "pair: expected [u, v]",
         base, None),
    ]
    for label, fn, expect, src, verdict in rule3:
        fx = src.mutate(fn)
        if verdict:
            fx.rec["verdict"] = verdict
        H.reject(fx, f"rule 3: {label}", expect)
    # zeta controls built so that only the zeta rule fails
    def zeta_ctrl(label, want, new):
        for fx in [*gadget_fx, f2, f3, *real_fx, *(v[0] for v in kinds.values())]:
            for lf, _, loc in tree_leaves(fx.tree):
                if "edge" in lf and lf["zeta"] == want:
                    H.reject(fx.mutate(lambda r: node_at(T(r), loc)["leaf"].__setitem__("zeta", new)),
                             f"rule 3: {label} on {fx.code} {loc}", "0..5")
                    return
        H.expect(False, f"no fixture has a unit leaf with zeta {want} for: {label}")
    zeta_ctrl("zeta 6 (w^6 = w^0, so the identity of zeta 0 would hold)", 0, 6)
    zeta_ctrl("zeta -1 (w^-1 = w^5, so the identity of zeta 5 would hold)", 5, -1)
    zeta_ctrl("zeta given as true (true == 1 in Python)", 1, True)
    # pair and edge vertices written as bools (false == 0, true == 1: a checker without type checks would accept)
    H.reject(fk4h.mutate(lambda r: node_at(T(r), "tree.plus.minus")["leaf"].__setitem__("pair", [False, 1])),
             "rule 3: a pair written [false, 1] instead of [0, 1]", "must be JSON integers")
    bool_edge = next(((fx, loc, lf) for fx in [*gadget_fx, f2, f3, *real_fx] for lf, _, loc in tree_leaves(fx.tree)
                      if "edge" in lf and set(lf["edge"]) & {0, 1}), None)
    H.expect(bool_edge is not None, "a fixture has a unit leaf whose edge contains vertex 0 or 1")
    if bool_edge:
        fx, loc, lf = bool_edge
        H.reject(fx.mutate(lambda r: node_at(T(r), loc)["leaf"].__setitem__("edge", boolify(lf["edge"]))),
                 f"rule 3: an edge written {json.dumps(boolify(lf['edge']))} on {fx.code} {loc}",
                 "must be JSON integers")
    p_, q_ = next(iter(g113.edges))
    pe = {"cycles": [[x, t1, y, t2], [t1, y, t2, x]], "cycle_coefficients": [[1, 0], [1, 0]], "triangles": [],
          "triangle_coefficients": [], "scale": [1, 0], "pair": [p_, q_], "edge": [p_, q_], "zeta": 0}
    H.reject(Fx("K113", code113, g113, "tu", {"leaf": pe}),
             "rule 3: a tu leaf whose pair IS an edge (pair = edge, zeta 0, relations sum to 0: 0 = 0 holds)",
             "is an edge of G")
    ne = dict(pe, pair=[k1a, k1b], edge=[k1a, k1b])
    H.reject(Fx("K113", code113, g113, "tu", {"leaf": ne}),
             "rule 3: a tu leaf whose edge is NOT an edge (edge = pair, zeta 0, relations sum to 0: 0 = 0 holds)",
             "is not an edge of G")

    # rule 4
    rule4 = [
        ("a wrong w^s: zeta moved by one", at_unit(lambda lf: lf.__setitem__("zeta", (lf["zeta"] + 1) % 6)),
         "identity fails"),
        ("the identity off by w in one entry", at_leaf(lambda lf: lf["cycle_coefficients"][0].__setitem__(
            1, lf["cycle_coefficients"][0][1] + 1)), "identity fails"),
        ("the scale doubled", at_leaf(lambda lf: lf.__setitem__("scale", [2 * v for v in lf["scale"]])),
         "identity fails"),
        ("a coefficient negated", at_leaf(lambda lf: lf["triangle_coefficients"].__setitem__(
            0, [-v for v in lf["triangle_coefficients"][0]])), "identity fails"),
        ("a plus branch whose subtree is only valid for the minus sign (children swapped at one split)",
         lambda r: T(r).update(plus=T(r)["minus"], minus=T(r)["plus"]) if "leaf" in T(r)["plus"]
         else T(r)["plus"].update(plus=T(r)["plus"]["minus"], minus=T(r)["plus"]["plus"]), "identity fails"),
    ]
    for label, fn, expect in rule4:
        H.reject(base.mutate(fn), f"rule 4: {label}", expect)

    # rule 5 and the schema
    H.reject(base.mutate(lambda r: r.__setitem__("verdict", "refuted")),
             "rule 5: verdict refuted on a tree with unit leaves", "verdict refuted but the leaf")
    H.reject(fk4.mutate(lambda r: r.__setitem__("verdict", "tu")),
             "rule 5: verdict tu on a tree with collision leaves only", "verdict tu but no leaf has an edge")
    schema = [
        ("an extra key in a leaf", at_leaf(lambda lf: lf.__setitem__("comment", "x")), "extra keys ['comment']"),
        ("a missing key in a leaf (scale)", at_leaf(lambda lf: lf.pop("scale")), "missing keys ['scale']"),
        ("an extra key beside tri in the witness", lambda r: r["witness"].__setitem__("rhombus", {}), "extra keys"),
        ("an extra key beside tree in tri", lambda r: r["witness"]["tri"].__setitem__("depth", 2), "extra keys"),
        ("a tri witness with verdict embedded", lambda r: r.__setitem__("verdict", "embedded"), "needs verdict"),
        ("a witness that is a list", lambda r: r.__setitem__("witness", [r["witness"]]),
         "witness: expected an object with exactly the key 'tri'"),
        ("a tri value that is a list", lambda r: r["witness"].__setitem__("tri", [r["witness"]["tri"]]),
         "witness.tri: expected an object with exactly the key 'tree'"),
    ]
    for label, fn, expect in schema:
        H.reject(base.mutate(fn), f"schema: {label}", expect)
    for label, n_, edges_, expect in (("the order -1", -1, [], "the order n"), ("the order true", True, [], "the order n"),
                                       ("a loop edge (0, 0)", 4, [(0, 0)], "invalid edge"),
                                       ("an edge of three vertices", 4, [(0, 1, 2)], "invalid edge")):
        ok, reason, _ = TV.verify_tri_witness(n_, edges_, fk4.rec["verdict"], fk4.rec["witness"])
        H.expect(not ok and expect in reason, f"REJECT  library input with {label}\n            -> {reason}")

    # ---------------------------------------------------------------------------------------------------------
    H.section("binding red mutants of amendment 2: tri_verify REJECTS, a checker with exactly that bug ACCEPTS")
    # wrong ring: a certificate built by the prover in Z[w]/(w^2 + w + 1); on W6 it even "proves" a unit distance
    cw, gw6, mpw6 = canonical_graph(*W6, labelg)
    tw = Prover(gw6, ring=Ring(wrong=True)).build()
    H.expect(tw is not None, "the prover in the wrong ring (w^2 = -w - 1) emits a certificate for W6")
    if tw is not None:
        H.reject(Fx("W6 wrong ring", cw, gw6, verdict_of(tw), tw),
                 "wrong ring: W6 certificate computed with w^2 = -w - 1", "identity fails", sharp="wrong-ring")

    def swap_all(node):
        if "split" in node:
            node["plus"], node["minus"] = node["minus"], node["plus"]
            swap_all(node["plus"])
            swap_all(node["minus"])
    H.reject(f2.mutate(lambda r: swap_all(T(r))), f"sign flip in t(T, s): {f2.code} with plus and minus swapped at "
             f"every split (valid only if t(T, s) used w^(-s))", "identity fails", sharp="sign-flip")
    code3, g3, _ = canonical_graph(*K3, labelg)
    rep = {"cycles": [[0, 1, 0, 2], [1, 0, 1, 2]], "cycle_coefficients": [[1, 0], [-1, 0]], "triangles": [],
           "triangle_coefficients": [], "scale": [3, 0], "pair": [0, 1]}
    H.reject(Fx("K3", code3, g3, "refuted", {"leaf": rep}),
             "repeated cycle vertex: 'cycles' [0,1,0,2] and [1,0,1,2] would refute K3, an equilateral triangle",
             "is not pairwise distinct", sharp="repeat-vertex")
    tdrop = Prover(gw6, order="naive", fill_open="drop").build()
    H.reject(Fx("W6 dropped", cw, gw6, verdict_of(tdrop), tdrop),
             "dropped child: W6 case tree with its open (embeddable) branches left out", "missing keys",
             sharp="missing-child")
    H.reject(fk4b.mutate(add_copies((1,))),
             "int64: K4 leaf plus five copies of one cycle with coefficients summing to 2^64 (false over Z, "
             "true modulo 2^64)", "identity fails", sharp="int64")
    # unsorted leaf triangle: the sibling's leaf moved across with the split triangle written [b, a, c]
    split2 = next(loc for lf, path, loc in tree_leaves(f2.tree) if loc.endswith(".plus"))
    parent_loc = split2[: -len(".plus")]

    def move_sibling(rec):
        parent = node_at(T(rec), parent_loc)
        a, b, c = parent["split"]
        lf = copy.deepcopy(parent["minus"]["leaf"])
        lf["triangles"] = [[b, a, c] if t == [a, b, c] else t for t in lf["triangles"]]
        parent["plus"] = {"leaf": lf}
    H.reject(f2.mutate(move_sibling), f"unsorted leaf triangle: {f2.code}, the minus leaf copied to the plus branch "
             f"with the split triangle written [b, a, c]", "is not a sorted triple", sharp="set-lookup")

    # ---------------------------------------------------------------------------------------------------------
    H.section("Moser spindle and W6: unit-distance graphs, so no valid certificate exists")
    cm, gm, mpm = canonical_graph(*MOSER, labelg)
    fm = {mpm[v]: z for v, z in moser_embedding().items()}
    f6 = {mpw6[v]: z for v, z in w6_embedding().items()}
    for name, g, f in (("Moser spindle", gm, fm), ("W6 wheel", gw6, f6)):
        emb, faithful = check_embedding(g.n, g.edges, f)
        H.expect(emb and faithful, f"{name}: the explicit embedding has distinct points, every edge of length 1 and "
                                   f"no other unit distance (so neither a refutation nor a tu certificate is true)")
        for order in ("undecided", "naive"):
            H.expect(Prover(g, order=order).build() is None,
                     f"{name}: the exact test prover ({order} split order) finds no certificate")
    fakes = []

    def set_lookup_fake(g):
        a, b, c = g.triangles()[0]
        lf = lambda s: {"leaf": {"cycles": [], "cycle_coefficients": [], "triangles": [[a, b, c], [b, a, c]],  # noqa
                                 "triangle_coefficients": [[1, 0], [-1, 0]],
                                 "scale": [-1, 2] if s == 1 else [1, -2], "pair": [a, b]}}
        return {"split": [a, b, c], "plus": lf(1), "minus": lf(-1)}
    for name, code, g, f in (("Moser spindle", cm, gm, fm), ("W6 wheel", cw, gw6, f6)):
        fakes.append((name, "set-lookup trap: one split, each leaf lists the split triangle as [a,b,c] and [b,a,c]",
                      Fx(name, code, g, "refuted", set_lookup_fake(g)), "is not a sorted triple", "set-lookup", f))
        t = Prover(g, order="naive", fill_open="drop").build()
        fakes.append((name, "dropped children: the exact prover's tree with the embeddable branches left out",
                      Fx(name, code, g, verdict_of(t), t), "missing keys", "missing-child", f))
        t = Prover(g, ring=Ring(w_minus=(-1, 1))).build()
        if t is not None:
            fakes.append((name, "w^(-1) slip: the prover used w^2 = w - 1 where w^(-1) = 1 - w belongs",
                          Fx(name, code, g, verdict_of(t), t), "identity fails", None, f))
        t = Prover(g, order="naive", fill_open="sibling").build()
        fakes.append((name, "sign bug: each embeddable branch closed with its sibling's leaf",
                      Fx(name, code, g, verdict_of(t), t), "identity fails", None, f))
        t = Prover(g, ring=Ring(wrong=True)).build()
        if t is not None:
            fakes.append((name, "wrong ring: the prover's arithmetic used w^2 = -w - 1",
                          Fx(name, code, g, verdict_of(t), t), "identity fails", "wrong-ring", f))
    for name, label, fx, expect, sharp, f in fakes:
        H.reject(fx, f"{name}, {fx.rec['verdict']} certificate, {label}", expect, sharp=sharp)
        lf, path, loc = follow(fx.tree, f)
        if lf is None:
            H.expect(True, f"    oracle: the embedding follows {loc}, which the certificate does not contain")
        else:
            lhs, rhs = value_at(lf, path, f)
            if sharp == "set-lookup":
                H.expect(lhs > 1e-6 and rhs > 1e-6,
                         f"    oracle: the embedding reaches {loc}; the leaf's relations, read as a set-lookup checker "
                         f"reads [b, a, c], sum to {lhs:.3f} there instead of 0: that relation is false")
            else:
                H.expect(lhs < 1e-9 and rhs > 1e-6,
                         f"    oracle: the embedding reaches {loc}; there the leaf's relations sum to {lhs:.1e} but "
                         f"scale * target is {rhs:.3f}, so the leaf's identity is false")

    # ---------------------------------------------------------------------------------------------------------
    H.section("differential fuzz: random single mutations, tri_verify and the reference must agree")
    pool = [fk4, fk113, fw5, *gadget_fx, f2, f3, fk4h, *(v[0] for v in kinds.values()), real_fx[0]]
    fz = fuzz(pool, 4000, 20260926)
    H.expect(not fz["disagree"], f"{fz['total']} random single mutations of valid certificates: tri_verify and the "
                                 f"reference agree on every one ({fz['accepted']} accepted, "
                                 f"{fz['total'] - fz['accepted']} rejected)"
             + "".join(f"\n            disagreement: {d}" for d in fz["disagree"][:5]))
    if fz["accepted"]:
        H.expect(not fz["unsound"], f"every accepted mutation also passes the floating-point identity check "
                                    f"({fz['accepted']} checked)"
                 + "".join(f"\n            float check failed: {d}" for d in fz["unsound"][:5]))
    H.expect(not fz["false_reject"] and fz["equivalent"] > 0,
             f"{fz['equivalent']} validity-preserving rewrites (a leaf times lambda in Z[w], rows reordered, a cycle "
             f"rotated or reversed, pair and edge reversed with the scale negated, a cancelling pair appended): "
             f"tri_verify, the reference and the float check all accept every one"
             + "".join(f"\n            wrongly rejected: {d}" for d in fz["false_reject"][:5]))

    # ---------------------------------------------------------------------------------------------------------
    H.section("command line")
    with tempfile.TemporaryDirectory() as tmp:
        pos = [fk4, fk113, fw5, *[gadget_fx[i] for i in (0, 1, 2, 3, 5)], f2, f3, *real_fx, f64]
        content = "".join(fx.line() + "\n" for fx in pos).encode()
        graphs = "".join(fx.code + "\n" for fx in pos).encode()
        want = (f"ACCEPT tri records={len(pos)} refuted={sum(fx.rec['verdict'] == 'refuted' for fx in pos)} "
                f"tu={sum(fx.rec['verdict'] == 'tu' for fx in pos)} "
                f"nodes={sum(H.tv(fx)[2]['nodes'] for fx in pos)}")
        H.cli("positive controls in one file, with --graphs", content, expect_ok=True, expect=want, graphs=graphs,
              workdir=tmp)
        H.cli("the same file, --expect-n 7", content, ["--expect-n", "7"], expect_ok=False,
              expect="expected 7 vertices", workdir=tmp)
        H.cli("the same file, --expect-m 7", content, ["--expect-m", "7"], expect_ok=False,
              expect="expected 7 edges", workdir=tmp)
        H.cli("a --graphs file without its final newline", content, expect_ok=False, expect="missing final newline",
              graphs=graphs[:-1], workdir=tmp)
        H.cli("a --graphs file with a blank line", content, expect_ok=False, expect="blank graph6 record",
              graphs=graphs + b"\n", workdir=tmp)
        for label, code, expect in (("a g6 string one character too long", f2.code + "?", "wrong graph6 length"),
                                    ("a g6 string with a byte below 63", f2.code[:-1] + "!", "non-graph6 byte"),
                                    ("a g6 string with the '>>graph6<<' header", ">>graph6<<" + f2.code,
                                     "unsupported header"),
                                    ("a g6 value that is a number, not a string", 7, "expected a nonempty graph6 string")):
            H.cli(label, (json.dumps(dict(f2.rec, g6=code), separators=(",", ":")) + "\n").encode(),
                  expect_ok=False, expect=expect, workdir=tmp)
        swapped = "".join(fx.code + "\n" for fx in [pos[1], pos[0], *pos[2:]]).encode()
        H.cli("--graphs listing two records in the other order", content, expect_ok=False,
              expect="do not exactly equal", graphs=swapped, workdir=tmp)
        line = f2.line()
        H.cli("an extra top-level key", (line[:-1] + ',"note":1}\n').encode(), expect_ok=False, expect="extra keys",
              workdir=tmp)
        H.cli("a record without its witness", (json.dumps({"g6": f2.code, "verdict": "tu"}) + "\n").encode(),
              expect_ok=False, expect="missing keys ['witness']", workdir=tmp)
        lfz, _, _ = first_leaf(f2.tree, lambda lf: "edge" in lf)
        good = f'"zeta":{lfz["zeta"]}'
        dup = line.replace(good, f'"zeta":{(lfz["zeta"] + 1) % 6},{good}', 1)
        H.cli("a duplicate JSON key (a wrong zeta, then the right one: the last one wins without the hook)",
              (dup + "\n").encode(), expect_ok=False, expect="duplicate key 'zeta'", workdir=tmp)
        lax = json.loads(dup)
        H.expect(TV.verify_tri_witness(f2.g.n, f2.g.edges, lax["verdict"], lax["witness"])[0],
                 "    the same record parsed without the duplicate-key hook passes rule 4: only the hook rejects it")
        H.cli("NaN in a coefficient", line.replace('"scale":[', '"scale":[NaN,0,', 1).encode() + b"\n",
              expect_ok=False, expect="non-standard JSON constant NaN", workdir=tmp)
        # A gadget certificate (rhombus rows only, so relabelling touches no triangle orientation) moved to the
        # reversed labelling: a valid certificate, but on a graph6 string that is not canonical.
        g0 = gadget_fx[0]
        perm = list(range(g0.g.n))[::-1]
        pe2 = [(perm[u], perm[v]) for u, v in g0.g.edges]
        noncanon = g6_encode(g0.g.n, pe2)

        def relabel_tree(rec):
            lf = T(rec)["leaf"]
            lf["cycles"] = [[perm[v] for v in c] for c in lf["cycles"]]
            for key in ("pair", "edge"):
                lf[key] = [perm[v] for v in lf[key]]
            rec["g6"] = noncanon
        frel = g0.mutate(relabel_tree)
        frel.g = Graph(g0.g.n, pe2)
        okrel = H.tv(frel)[0]
        H.expect(okrel and noncanon != canonical([noncanon], labelg)[0],
                 f"    a relabelled copy of gadget 0's certificate is valid on {noncanon}, a NON-canonical g6")
        H.cli("a valid certificate whose g6 is not nauty-labelg canonical", (frel.line() + "\n").encode(),
              expect_ok=False, expect="not nauty-labelg canonical", workdir=tmp)
        H.cli("the same record twice", (line + "\n" + line + "\n").encode(), expect_ok=False,
              expect="duplicate graph6 record", workdir=tmp)
        H.cli("no final newline", line.encode(), expect_ok=False, expect="missing final newline", workdir=tmp)
        H.cli("a blank line", (line + "\n\n").encode(), expect_ok=False, expect="blank certificate record", workdir=tmp)
        H.cli("JSON nested 100,000 deep", ("[" * 100000 + "]" * 100000 + "\n").encode(), expect_ok=False,
              expect="invalid JSON", workdir=tmp)
        H.cli("an integer of 5,000 digits", line.replace('"scale":[', '"scale":[' + "9" * 5000 + ",0,", 1).encode()
              + b"\n", expect_ok=False, expect="invalid JSON", workdir=tmp)
        H.cli("bytes that are not UTF-8", line.encode()[:-2] + b"\xff}\n", expect_ok=False, expect="invalid JSON",
              workdir=tmp)
        H.cli("a record that is a JSON list", b"[1,2]\n", expect_ok=False, expect="expected a JSON object",
              workdir=tmp)
        padfx = next(fx for fx in pos if (fx.g.n * (fx.g.n - 1) // 2) % 6)
        badpad = padfx.code[:-1] + chr(((ord(padfx.code[-1]) - 63) | 1) + 63)     # set the last padding bit
        H.cli(f"a g6 string with a nonzero padding bit ({badpad})",
              (json.dumps(dict(padfx.rec, g6=badpad), separators=(",", ":")) + "\n").encode(),
              expect_ok=False, expect="nonzero graph6 padding bits", workdir=tmp)
        H.cli("an empty file", b"", expect_ok=True, expect="ACCEPT tri records=0 refuted=0 tu=0 nodes=0",
              workdir=tmp)

    elapsed = time.time() - t_start
    print(f"\n== summary ==\n{len(H.lines)} expectations, {len(H.failures)} failed ({elapsed:.1f} s)")
    for text in H.failures:
        print("FAILED: " + text.splitlines()[0])
    return 0 if not H.failures else 1


def equivalent(rec, rnd):
    """Apply one validity-preserving rewrite to a random leaf; returns its description."""
    leaves = [lf for lf, _, _ in tree_leaves(T(rec))]
    lf = rnd.choice(leaves)
    op = rnd.randrange(6)
    if op == 0:                                     # multiply the whole leaf by a nonzero lambda in Z[w]
        lam = (0, 0)
        while lam == (0, 0):
            lam = (rnd.randint(-3, 3), rnd.randint(-3, 3))
        values = [TV.zmul(tuple(c), lam) for key in ("cycle_coefficients", "triangle_coefficients")
                  for c in lf[key]] + [TV.zmul(tuple(lf["scale"]), lam)]
        if any(abs(v) >= B62 for z in values for v in z):
            lam = (-1, 0)                           # keep inside the 2^62 bound
        for key in ("cycle_coefficients", "triangle_coefficients"):
            lf[key] = [list(TV.zmul(tuple(c), lam)) for c in lf[key]]
        lf["scale"] = list(TV.zmul(tuple(lf["scale"]), lam))
        return f"leaf times {lam}"
    if op == 1:                                     # reorder the rows (each with its coefficient)
        for rows, coefs in (("cycles", "cycle_coefficients"), ("triangles", "triangle_coefficients")):
            both = list(zip(lf[rows], lf[coefs]))
            rnd.shuffle(both)
            lf[rows], lf[coefs] = [list(r) for r, _ in both], [list(c) for _, c in both]
        return "rows shuffled"
    if op == 2 and lf["cycles"]:                    # rotate a cycle by one place: r(C) changes sign
        j = rnd.randrange(len(lf["cycles"]))
        lf["cycles"][j] = lf["cycles"][j][1:] + lf["cycles"][j][:1]
        lf["cycle_coefficients"][j] = [-v for v in lf["cycle_coefficients"][j]]
        return "a cycle rotated, its coefficient negated"
    if op == 3 and lf["cycles"]:                    # reverse a cycle's direction: r(C) is unchanged
        j = rnd.randrange(len(lf["cycles"]))
        u, v, w, x = lf["cycles"][j]
        lf["cycles"][j] = [u, x, w, v]
        return "a cycle reversed"
    if op == 4:                                     # swap pair (and edge): the target changes sign
        lf["pair"] = lf["pair"][::-1]
        if "edge" in lf:
            lf["edge"] = lf["edge"][::-1]
        lf["scale"] = [-v for v in lf["scale"]]
        return "pair and edge reversed, scale negated"
    if lf["cycles"]:                                # append a cancelling pair C, rotated C with equal coefficients
        c = lf["cycles"][0]
        coef = [rnd.randint(-5, 5), rnd.randint(1, 5)]
        lf["cycles"] += [list(c), c[1:] + c[:1]]
        lf["cycle_coefficients"] += [list(coef), list(coef)]
        return "a cancelling pair of cycles appended"
    return "unchanged"


def fuzz(pool, count, seed):
    """Random single mutations of valid certificates, and random validity-preserving rewrites.

    Returns disagreements between tri_verify and the reference, accepted certificates that fail the floating-point
    identity check, and rewrites that either checker rejected."""
    import random
    rnd = random.Random(seed)
    out = {"total": 0, "accepted": 0, "disagree": [], "unsound": [], "equivalent": 0, "false_reject": []}
    for _ in range(count // 4):
        fx = rnd.choice(pool)
        rec = copy.deepcopy(fx.rec)
        what = equivalent(rec, rnd)
        ok, reason, _ = TV.verify_tri_witness(fx.g.n, fx.g.edges, rec["verdict"], rec["witness"])
        rok, rreason = ref_check(fx.g.n, fx.g.edges, rec["verdict"], rec["witness"])
        probe = Fx(fx.name, fx.code, fx.g, rec["verdict"], T(rec))
        out["equivalent"] += 1
        if not (ok and rok and float_check(probe)):
            out["false_reject"].append(f"{fx.name}: {what}: tri_verify {ok} ({reason}), reference {rok} ({rreason})")
    junk = [True, False, 1.0, 0.0, "1", None, [], {}, [0, 0], [1, 0, 0], -1, 2 ** 62, 2 ** 63]
    while out["total"] < count:
        fx = rnd.choice(pool)
        rec = copy.deepcopy(fx.rec)
        slots = []

        def walk(obj):
            if isinstance(obj, dict):
                for k in list(obj):
                    slots.append((obj, k))
                    walk(obj[k])
            elif isinstance(obj, list):
                for i in range(len(obj)):
                    slots.append((obj, i))
                    walk(obj[i])
        walk(rec["witness"])
        cont, key = rnd.choice(slots)
        val = cont[key]
        op = rnd.randrange(9)
        if op == 0 and type(val) is int:
            cont[key] = val + rnd.choice((-1, 1))
            what = f"{key}: {val} -> {cont[key]}"
        elif op == 1 and type(val) is int:
            cont[key] = rnd.randrange(-2, fx.g.n + 2)
            what = f"{key}: {val} -> {cont[key]}"
        elif op == 2:
            cont[key] = copy.deepcopy(rnd.choice(junk))
            what = f"{key}: {val!r} -> {cont[key]!r}"
        elif op == 3 and isinstance(cont, dict):
            del cont[key]
            what = f"deleted key {key}"
        elif op == 4 and isinstance(cont, dict):
            cont[rnd.choice(["x", "edge", "zeta", "leaf", "split", "plus", "minus"])] = copy.deepcopy(val)
            what = f"added a key beside {key}"
        elif op == 5 and isinstance(cont, list):
            cont.insert(key, copy.deepcopy(val))
            what = f"duplicated list element {key}"
        elif op == 6 and isinstance(cont, list):
            del cont[key]
            what = f"deleted list element {key}"
        elif op == 7 and isinstance(val, dict) and {"plus", "minus"} <= set(val):
            val["plus"], val["minus"] = val["minus"], val["plus"]
            what = "swapped the children of a split"
        else:
            rec["verdict"] = rnd.choice(["tu", "refuted", "embedded", None])
            what = f"verdict -> {rec['verdict']!r}"
        if repr(rec) == repr(fx.rec):           # a no-op (same value written back): draw again
            continue
        ok = TV.verify_tri_witness(fx.g.n, fx.g.edges, rec["verdict"], rec["witness"])[0]
        rok = ref_check(fx.g.n, fx.g.edges, rec["verdict"], rec["witness"])[0]
        out["total"] += 1
        if ok != rok:
            out["disagree"].append(f"{fx.name}: {what}: tri_verify {ok}, reference {rok}")
        if ok:
            out["accepted"] += 1
            probe = Fx(fx.name, fx.code, fx.g, rec["verdict"], rec["witness"]["tri"]["tree"])
            if not float_check(probe):
                out["unsound"].append(f"{fx.name}: {what}")
    return out


# =================================================================================================================
# Part 6. Mutation testing of the checker: each mutant is tri_verify.py with one deliberate defect; the self-test
# must FAIL against every one (exact substrings; a substring that no longer occurs exactly once is reported).

MUTANTS = [
    ("cycle vertices need not be pairwise distinct",
     [("if u == v or u == w or u == x or v == w or v == x or w == x:", "if False:")]),
    ("cycle edges not checked",
     [("if not ((adj[u] >> v) & (adj[v] >> w) & (adj[w] >> x) & (adj[x] >> u) & 1):", "if False:")]),
    ("cycle vertices not type-checked (a bool passes as 0 or 1)",
     [("if type(u) is not int or type(v) is not int or type(w) is not int or type(x) is not int:", "if False:")]),
    ("leaf triangle looked up as a set (the unsorted-lookup trap)",
     [("        if not a < b < c3:", "        if False:"),
      ("s = path.get((a, b, c3))", "s = path.get(tuple(sorted((a, b, c3))))")]),
    ("leaf triangle sortedness not checked", [("        if not a < b < c3:", "        if False:")]),
    ("sign flip: the minus branch keeps s = +1", [("stack.append((key, -1))", "stack.append((key, 1))")]),
    ("wrong ring in the triangle product (w^2 = -w - 1)",
     [("Y[a] += mx * a1 + a0 * my + my * a1", "Y[a] += mx * a1 + a0 * my - my * a1")]),
    ("wrong ring in zmul (caught by the import-time self-check)",
     [("return (x1 * x2 - y1 * y2, x1 * y2 + x2 * y1 + y1 * y2)",
       "return (x1 * x2 - y1 * y2, x1 * y2 + x2 * y1 - y1 * y2)")]),
    ("w^(-1) written as w - 1 (caught by the import-time self-check)",
     [("W_MINUS = (1, -1)", "W_MINUS = (-1, 1)")]),
    ("target entries overwritten instead of added",
     [("target[p] = zadd(target.get(p, Z_ZERO), zneg(wk))", "target[p] = zneg(wk)")]),
    ("scale [0, 0] allowed", [("if scale == Z_ZERO:", "if False:")]),
    ("zero cycle coefficient allowed", [("if lx == 0 and ly == 0:", "if False:")]),
    ("zero triangle coefficient allowed", [("if mx == 0 and my == 0:", "if False:")]),
    ("coefficient bound inclusive (2^62 allowed)",
     [("if not (-B < lx < B and -B < ly < B):", "if not (-B <= lx <= B and -B <= ly <= B):")]),
    ("scale bound not checked",
     [("if not (-COEFF_BOUND < x < COEFF_BOUND and -COEFF_BOUND < y < COEFF_BOUND):", "if False:")]),
    ("pair may be an edge in a unit leaf", [("if (adj[a] >> b) & 1:", "if False:")]),
    ("edge need not be an edge", [("if not (adj[p] >> q) & 1:", "if False:")]),
    ("pair (and edge) vertices need not be distinct", [("    if u == v:\n", "    if False:\n")]),
    ("zeta may be 6", [("not 0 <= k <= 5", "not 0 <= k <= 6")]),
    ("zeta not type-checked (true passes as 1)",
     [("if type(k) is not int or not 0 <= k <= 5:", "if not 0 <= k <= 5:")]),
    ("verdict tu allowed with collision leaves only", [('if verdict == "tu" and not any_edge:', "if False:")]),
    ("verdict refuted allowed with a unit leaf", [('if verdict == "refuted":', "if False:")]),
    ("depth 65 allowed", [("MAX_DEPTH = 64", "MAX_DEPTH = 65")]),
    ("100,001 nodes allowed", [("if nodes > MAX_NODES:", "if nodes > MAX_NODES + 2:")]),
    ("4098 cycles allowed", [("len(cycles) > MAX_LEAF_CYCLES", "len(cycles) > MAX_LEAF_CYCLES + 2")]),
    ("both leaf lists may be empty", [("if not cycles and not tris:", "if False:")]),
    ("coefficient list length not checked",
     [("if type(ccoef) is not list or len(ccoef) != len(cycles):", "if type(ccoef) is not list:")]),
    ("a triangle may be split twice on one path", [("if key in path:", "if False:")]),
    ("split triangle edges not checked", [("    for u, v in ((a, b), (a, c), (b, c)):", "    for u, v in ():")]),
    ("split triple need not be sorted", [("    if not a < b < c:", "    if False:")]),
    ("a missing child is skipped (half trees accepted)",
     [("            if node.keys() != _SPLIT_KEYS:", "            if not node.keys() <= _SPLIT_KEYS:"),
      ('stack.append((node["minus"], depth + 1, (loc, "minus")))',
       'stack.append((node.get("minus", {"leaf": None}), depth + 1, (loc, "minus")))'),
      ('stack.append((node["plus"], depth + 1, (loc, "plus")))',
       'stack.append((node.get("plus", {"leaf": None}), depth + 1, (loc, "plus")))'),
      ("    if type(leaf) is not dict:\n        raise TriReject(f\"{_where(loc)}.leaf: expected an object\")",
       "    if leaf is None:\n        return False\n    if type(leaf) is not dict:\n"
       "        raise TriReject(f\"{_where(loc)}.leaf: expected an object\")")]),
    ("a leaf node may carry extra keys", [("            if len(node) != 1:", "            if False:")]),
    ("duplicate JSON keys allowed (no hook)",
     [("object_pairs_hook=_no_duplicate_keys,", "object_pairs_hook=None,")]),
    ("NaN allowed", [("parse_constant=_no_constant)", ")")]),
    ("canonical graph6 not checked", [("    _check_canonical(codes, labelg)\n", "    pass\n")]),
    ("--graphs not compared", [("if graphs is not None and _read_graph_list(graphs) != codes:", "if False:")]),
    ("duplicate records allowed", [("if code in seen:", "if False:")]),
    ("pair and edge vertices not type-checked (false passes as 0)",
     [("if type(u) is not int or type(v) is not int:", "if False:")]),
    ("triangle coefficient bound inclusive (2^62 allowed)",
     [("if not (-B < mx < B and -B < my < B):", "if not (-B <= mx <= B and -B <= my <= B):")]),
    ("leaf triangle length not checked", [("if type(tri) is not list or len(tri) != 3:", "if type(tri) is not list:")]),
    ("graph6 padding bits ignored", [("            elif bit:", "            elif False:")]),
    ("graph6 length not checked", [("if len(vals) - pos != (need_bits + 5) // 6:", "if False:")]),
    ("--expect-m ignored", [("if expect_m is not None and m != expect_m:", "if False:")]),
    ("--graphs file may lack its final newline", [('if raw and not raw.endswith(b"\\n"):', "if False:")]),
    ("library: a bad graph order accepted", [("if type(n) is not int or n < 0:", "if False:")]),
    ("cycle vertices not range-checked (negative indices alias)",
     [("if not (0 <= u < n and 0 <= v < n and 0 <= w < n and 0 <= x < n):", "if False:")]),
    ("pair and edge vertices not range-checked", [("    if not (0 <= u < n and 0 <= v < n):\n", "    if False:\n")]),
    ("split vertices not range-checked", [("    if not (0 <= a < n and 0 <= b < n and 0 <= c < n):", "    if False:")]),
    ("scale shape not checked",
     [('or len(value) != 2:\n        raise TriReject(f"{_where(where)}.leaf.{field}: expected a Z[w] pair',
       'or False:\n        raise TriReject(f"{_where(where)}.leaf.{field}: expected a Z[w] pair')]),
    ("pair shape not checked",
     [('or len(value) != 2:\n        raise TriReject(f"{_where(loc)}.leaf.{field}: expected [u, v]',
       'or False:\n        raise TriReject(f"{_where(loc)}.leaf.{field}: expected [u, v]')]),
    ("leaf value not type-checked", [('    if type(leaf) is not dict:\n', '    if False:\n')]),
    ("'cycles' not type-checked", [("    if type(cycles) is not list:\n", "    if False:\n")]),
    ("'triangles' not type-checked", [("    if type(tris) is not list:\n", "    if False:\n")]),
    ("triangle coefficient shape not checked",
     [("if type(m) is not list or len(m) != 2:", "if type(m) is not list:")]),
    ("witness not type-checked", [("        if type(witness) is not dict:\n", "        if False:\n")]),
    ("g6 not type-checked", [("if type(code) is not str or not code:", "if not code:")]),
    ("--graphs file may contain blank lines", [("    if any(not line for line in lines):", "    if False:")]),
]


def run_mutants(labelg):
    src = TV_PATH.read_text()
    killed, survived, broken = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, subs) in enumerate(MUTANTS):
            text = src
            for old, new in subs:
                if text.count(old) != 1:
                    broken.append(f"{name}: {old!r} occurs {text.count(old)} times")
                    break
                text = text.replace(old, new)
            else:
                mdir = Path(tmp) / f"mutant-{i:02d}"         # a fresh directory each time: no stale bytecode
                mdir.mkdir()
                mpath = mdir / "tri_verify.py"
                mpath.write_text(text)
                want = hashlib.sha256(text.encode()).hexdigest()
                env = dict(os.environ, TRI_VERIFY_PATH=str(mpath), PYTHONDONTWRITEBYTECODE="1")
                t0 = time.time()
                proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--labelg", labelg], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
                out = proc.stdout.decode(errors="replace").splitlines()
                err = proc.stderr.decode(errors="replace").strip().splitlines()
                loaded = next((line.split()[-1] for line in out if line.startswith("module under test:")), None)
                if loaded is not None and loaded != want:
                    broken.append(f"{name}: the self-test ran {loaded}, not the mutant {want}")
                    continue
                fails = [line[len("FAILED: "):] for line in out if line.startswith("FAILED: ")]
                why = fails[0] if fails else (err[-1] if err else "no output")
                if loaded is None:                            # the mutant did not even import
                    why = "import failed: " + why
                row = f"{name}\n            -> {len(fails)} failed expectation(s), first: {why[:160]}"
                (killed if proc.returncode != 0 else survived).append(row)
                print(("killed   " if proc.returncode != 0 else "SURVIVED ") + row + f"  ({time.time() - t0:.0f} s)",
                      flush=True)
    print(f"\n{len(MUTANTS)} mutants: {len(killed)} killed, {len(survived)} survived, {len(broken)} did not apply")
    for row in broken:
        print("did not apply: " + row)
    return 0 if not survived and not broken else 1


# =================================================================================================================
# Part 7. Timing helpers (not part of the pass/fail self-test).

def make_certs(out, paths, max_nodes, labelg):
    codes = [line.strip() for p in paths for line in open(p) if line.strip()]
    canon = canonical(codes, labelg)
    kept = 0
    seen = set()
    with open(out, "w") as fh:
        for code in canon:
            if code in seen:
                continue
            seen.add(code)
            n, edges = g6_decode(code)
            tree = Prover(Graph(n, edges), max_nodes=max_nodes).build()
            if tree is not None:
                fh.write(json.dumps({"g6": code, "verdict": verdict_of(tree), "witness": {"tri": {"tree": tree}}},
                                    separators=(",", ":")) + "\n")
                kept += 1
    print(f"{kept} certificates written to {out} from {len(seen)} graphs")
    return 0


def bench_certs(paths, reps=3):
    """records/s of tri_verify (JSON parse with the duplicate-key hook, graph6 decode, verification)."""
    raws = [raw for p in paths for raw in open(p, "rb") if raw.strip()]

    def nleaves(t):
        return 1 if "leaf" in t else nleaves(t["plus"]) + nleaves(t["minus"])

    def one(raw):
        rec = json.loads(raw.decode("utf-8"), object_pairs_hook=TV._no_duplicate_keys,
                         parse_constant=TV._no_constant)
        n, adj, _ = TV.decode_graph6(rec["g6"])
        TV._check_witness(n, adj, rec["verdict"], rec["witness"], TV._new_stats())

    buckets = collections.defaultdict(list)
    by_n = collections.defaultdict(list)
    for raw in raws:
        rec = json.loads(raw)
        L = nleaves(rec["witness"]["tri"]["tree"])
        n = TV.decode_graph6(rec["g6"])[0]
        best = min((lambda t0: (one(raw), time.perf_counter() - t0)[1])(time.perf_counter()) for _ in range(reps))
        b = next(f"{lo}-{hi}" for lo, hi in ((1, 1), (2, 5), (6, 10), (11, 20), (21, 30), (31, 10 ** 6))
                 if lo <= L <= hi)
        buckets[b].append(best)
        by_n[n].append(best)
    total = sum(sum(v) for v in buckets.values())
    count = sum(len(v) for v in buckets.values())
    print(f"{count} records: {count / total:,.0f} records/s overall (best of {reps} per record)")
    for b in ("1-1", "2-5", "6-10", "11-20", "21-30", "31-1000000"):
        if buckets.get(b):
            v = buckets[b]
            print(f"  leaves {b:>10s}: {len(v):5d} records, {len(v) / sum(v):9,.0f} records/s")
    for n in sorted(by_n):
        v = by_n[n]
        print(f"  n = {n:2d}: {len(v):5d} records, {len(v) / sum(v):9,.0f} records/s")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labelg", default=LABELG)
    ap.add_argument("--make-certs", nargs="+", metavar=("OUT", "GRAPHS"))
    ap.add_argument("--max-nodes", type=int, default=128)
    ap.add_argument("--bench-certs", nargs="+", metavar="CERTS")
    ap.add_argument("--mutants", action="store_true", help="run the self-test against every mutant of tri_verify.py")
    args = ap.parse_args(argv)
    if args.mutants:
        return run_mutants(args.labelg)
    if args.make_certs:
        return make_certs(args.make_certs[0], args.make_certs[1:], args.max_nodes, args.labelg)
    if args.bench_certs:
        return bench_certs(args.bench_certs)
    return run_selftest(args.labelg)


if __name__ == "__main__":
    sys.exit(main())
