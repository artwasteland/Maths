#!/usr/bin/env python3
"""Strong positive control for udtriangle on GP-10's embedded B10 graphs.

For every graph udtriangle calls refuted or tu, take the graph's real embedding from GP-10's final records
(research/gp-10/cloud/lean3/records.jsonl.gz, the records of research/gp-10/runs/B10-final-2026-09-25: an "exact"
certificate is a real number field, a minimal polynomial with an isolating interval, and coordinates in that field;
a "super" certificate maps the graph into another embedded record, followed until an exact one), evaluate it to 100
digits with mpmath, and follow the case tree: at each split [a, b, c] the embedding's own orientation
(f(c) - f(a)) / (f(b) - f(a)) must be w or w^-1 to 1e-30 and picks the child.  The reached leaf must carry an edge
(an embedding at a collision leaf would be a soundness failure), and its forced relation must hold numerically:
|(f(a) - f(b)) - w^k (f(p) - f(q))| < 1e-30 and | |f(a) - f(b)| - 1 | < 1e-30.  The same is done for the mirror
image of the embedding (complex conjugate), which must reach the mirrored leaf.  A refuted verdict is a failure
outright.  Sanity: every edge of G has length 1 to 1e-30 and distinct vertices are > 1e-12 apart.

usage: b10_embed_check.py RECORDS.jsonl.gz GRAPHS.g6 VERDICTS.jsonl
"""
import collections
import gzip
import json
import sys
from fractions import Fraction

import mpmath as mp

mp.mp.dps = 100
TOL = mp.mpf(10) ** -30
W = mp.exp(1j * mp.pi / 3)
WPOW = [W ** k for k in range(6)]


def decode_g6(s):
    v = [ord(c) - 63 for c in s]
    n = v[0]
    flat = [(x >> sh) & 1 for x in v[1:] for sh in range(5, -1, -1)]
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if flat[k]:
                edges.add((i, j))
            k += 1
    return n, edges


def mpq(s):
    q = Fraction(s)
    return mp.mpf(q.numerator) / q.denominator


ROOTS = {}


def field_root(field):
    key = json.dumps(field, sort_keys=True)
    if key in ROOTS:
        return ROOTS[key]
    coeffs = [int(c) for c in field["minpoly"]]            # ascending
    desc = coeffs[::-1]
    der = [c * i for i, c in enumerate(coeffs)][1:][::-1]
    f = lambda x: mp.polyval(desc, x)
    lo, hi = mpq(field["interval"][0]), mpq(field["interval"][1])
    flo = f(lo)
    assert flo * f(hi) < 0, "interval does not bracket a sign change"
    a, b = lo, hi
    for _ in range(80):                                     # bisection, then Newton
        m = (a + b) / 2
        fm = f(m)
        if fm == 0:
            a = b = m
            break
        if (fm > 0) == (flo > 0):
            a = m
        else:
            b = m
    x = (a + b) / 2
    for _ in range(12):
        x = x - f(x) / mp.polyval(der, x)
    assert lo < x < hi and abs(f(x)) < mp.mpf(10) ** -80 * (1 + max(abs(c) for c in coeffs)), "root refinement failed"
    ROOTS[key] = x
    return x


def main(records, graphs_path, verdicts_path):
    ptr = {}
    with gzip.open(records, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r["verdict"] != "embedded":
                continue
            c = r["cert"]
            ptr[r["g6"]] = ("super", c["g6"], c["map"]) if c["type"] == "super" else ("exact", line)
    cache = {}

    def coords(start):
        chain, g = [], start
        while g not in cache:
            kind = ptr[g]
            if kind[0] == "exact":
                c = json.loads(kind[1])["cert"]
                alpha = field_root(c["field"])
                pw = [alpha ** i for i in range(len(c["field"]["minpoly"]) - 1)]
                cache[g] = [mp.mpc(sum(mpq(q) * p for q, p in zip(x, pw)), sum(mpq(q) * p for q, p in zip(y, pw)))
                            for x, y in c["coords"]]
                break
            chain.append(g)
            g = kind[1]
        while chain:                                       # unwind super pointers: f_G(u) = f_H(map[u])
            h = chain.pop()
            _, target, m = ptr[h]
            H = cache[target]
            cache[h] = [H[m[u]] for u in range(len(m))]
        return cache[start]

    graphs = [l.strip() for l in open(graphs_path) if l.strip()]
    verdicts = [json.loads(l) for l in open(verdicts_path)]
    assert len(graphs) == len(verdicts)
    stats = collections.Counter()
    failures = []
    worst = mp.mpf(0)
    for g6, rec in zip(graphs, verdicts):
        if rec["verdict"] == "pass":
            continue
        if rec["verdict"] == "refuted":
            failures.append((g6, "REFUTED an embedded graph"))
            continue
        stats["tu"] += 1
        n, edges = decode_g6(g6)
        z = coords(g6)
        assert len(z) == n
        for u, v in edges:
            assert abs(abs(z[u] - z[v]) - 1) < TOL, f"{g6}: edge {u}{v} not unit in the embedding"
        for u in range(n):
            for v in range(u + 1, n):
                assert abs(z[u] - z[v]) > mp.mpf(10) ** -12, f"{g6}: embedding not injective"
        for mirror in (False, True):
            pts = [mp.conj(p) for p in z] if mirror else z
            node, depth = rec["witness"]["tri"]["tree"], 0
            while "split" in node:
                a, b, c = node["split"]
                ratio = (pts[c] - pts[a]) / (pts[b] - pts[a])
                if abs(ratio - W) < TOL:
                    node = node["plus"]
                elif abs(ratio - mp.conj(W)) < TOL:
                    node = node["minus"]
                else:
                    raise SystemExit(f"{g6}: triangle {a, b, c} is not equilateral in the embedding (Lemma T fails?)")
                depth += 1
            L = node["leaf"]
            stats[f"reached depth {depth}"] += 1
            if "edge" not in L:
                failures.append((g6, f"embedding (mirror={mirror}) reaches a COLLISION leaf"))
                continue
            a, b = L["pair"]
            p, q = L["edge"]
            k = L["zeta"]
            rel = abs((pts[a] - pts[b]) - WPOW[k] * (pts[p] - pts[q]))
            dist = abs(abs(pts[a] - pts[b]) - 1)
            worst = max(worst, rel, dist)
            if rel < TOL and dist < TOL:
                stats["unit leaf holds"] += 1
            else:
                failures.append((g6, f"mirror={mirror}: forced pair {a},{b} at distance {mp.nstr(abs(pts[a] - pts[b]), 20)}"))
    print(f"checked tu graphs: {stats['tu']}  leaf checks (embedding + mirror): {2 * stats['tu']}  "
          f"unit leaves holding: {stats['unit leaf holds']}  worst residual: {mp.nstr(worst, 5)}  "
          f"exact embeddings evaluated: {sum(1 for g in cache if ptr[g][0] == 'exact')}  fields: {len(ROOTS)}")
    print("reached depths:", {k: v for k, v in sorted(stats.items()) if k.startswith("reached")})
    print(f"FAILURES: {len(failures)}")
    for f in failures[:50]:
        print("  ", *f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
