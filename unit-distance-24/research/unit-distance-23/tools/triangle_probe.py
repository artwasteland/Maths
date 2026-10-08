"""Prototype: how much more would triangle orientations add to the rhombus rule?

Positions as complex numbers z_i. Besides the rhombus rows (every unit 4-cycle u-v-w-x has z_u - z_v + z_w - z_x = 0,
rhombus_probe.py), every triangle {a < b < c} has z_c - z_a = w^s (z_b - z_a) with w = e^(i pi/3) and s = +1 (a, b, c
counterclockwise) or -1. Two triangles on one edge {x, y} have their third vertices on opposite sides of x->y (else
the third vertices coincide), which ties their signs: s_2 = -s_1 * par_1 * par_2, par_T = +1 when (x, y, t) is a
cyclic rotation of T's sorted (a, b, c), else -1. So the signs of each edge-connected component of triangles are fixed
by one bit (a component whose ties contradict themselves cannot be embedded at all), and the mirror image fixes one
component's bit. Every embedding realises one assignment; a graph is closed when EVERY assignment forces a collision
(z_a = z_b) or a unit distance on a non-edge (z_a - z_b = zeta (z_p - z_q), pq an edge, zeta a sixth root of unity).

Linear algebra over F_p with p = 2^61 - 1 = 1 mod 6 (so w exists) as a stand-in for Q(w): a measurement, not a proof.
This is AMP's L3 split (a three-edge relation with coefficients 1, 1, 1 has discriminant 3) followed by L1a and L2,
restricted to the triangles.

usage: python triangle_probe.py FILE.g6 [...]   (reports, per file, the verdicts of the rhombus rule and of the
       extension on the graphs the rhombus rule leaves)
"""
import sys, itertools, collections
import networkx as nx
from rhombus_probe import P, probe as rhombus

SQRT_M3 = pow(P - 3, (P + 1) // 4, P)          # P = 3 mod 4 and -3 is a square mod P (P = 1 mod 3)
assert SQRT_M3 * SQRT_M3 % P == P - 3
INV2 = pow(2, P - 2, P)
W = (1 + SQRT_M3) * INV2 % P                     # a primitive sixth root of unity: W^2 - W + 1 = 0
assert (W * W - W + 1) % P == 0
W_INV = pow(W, P - 2, P)
SIXTH = [pow(W, k, P) for k in range(6)]
MAX_CASES = 1 << 12


def rref(rows, n):
    piv = []
    for r in rows:
        r = [x % P for x in r]
        for c, pr in piv:
            if r[c]:
                f = r[c]
                r = [(a - f * b) % P for a, b in zip(r, pr)]
        lead = next((i for i, x in enumerate(r) if x), None)
        if lead is None:
            continue
        inv = pow(r[lead], P - 2, P)
        r = [x * inv % P for x in r]
        piv = [(c, [(a - pr[lead] * b) % P for a, b in zip(pr, r)] if pr[lead] else pr) for c, pr in piv]
        piv.append((lead, r))
    return piv


def reduce(v, piv):
    v = list(v)
    for c, pr in piv:
        if v[c]:
            f = v[c]
            v = [(a - f * b) % P for a, b in zip(v, pr)]
    return v


def closed(rows, n, edges, nonedges):
    """"collision" or "unit" when these relations force a collision or a unit distance on a non-edge, else None."""
    piv = rref(rows, n)
    red = [reduce([1 if i == v else 0 for i in range(n)], piv) for v in range(n)]
    diff = lambda a, b: [(x - y) % P for x, y in zip(red[a], red[b])]
    seen = set()
    for a, b in itertools.combinations(range(n), 2):
        if red[a] == red[b]:
            return "collision"
    edge_dirs = set()
    for p, q in edges:
        d = diff(p, q)
        for z in SIXTH:
            edge_dirs.add(tuple(z * x % P for x in d))
    return "unit" if any(tuple(diff(a, b)) in edge_dirs for a, b in nonedges) else None


def triangle_verdict(G):
    n = G.number_of_nodes()
    adj = [set(G[v]) for v in range(n)]
    edges = [tuple(sorted(e)) for e in G.edges()]
    edgeset = set(edges)
    nonedges = [(a, b) for a, b in itertools.combinations(range(n), 2) if (a, b) not in edgeset]
    base = []
    for u, w in itertools.combinations(range(n), 2):
        for v, x in itertools.combinations(sorted(adj[u] & adj[w]), 2):
            r = [0] * n; r[u] += 1; r[w] += 1; r[v] -= 1; r[x] -= 1; base.append(r)
    tris = [t for t in itertools.combinations(range(n), 3) if all(tuple(sorted(e)) in edgeset
                                                              for e in itertools.combinations(t, 2))]
    if not tris:
        return "no-triangles"
    by_edge = collections.defaultdict(list)
    for i, t in enumerate(tris):
        for e in itertools.combinations(t, 2):
            by_edge[e].append(i)

    def par(t, x, y):
        third = next(v for v in t if v not in (x, y))
        return 1 if (x, y, third) in (t, (t[1], t[2], t[0]), (t[2], t[0], t[1])) else -1
    # components with their sign propagation (s_j = -s_i * par_i * par_j across a shared edge)
    rel = [None] * len(tris)
    comps = []
    for s in range(len(tris)):
        if rel[s] is not None:
            continue
        rel[s] = 1; comp = [s]; stack = [s]
        while stack:
            i = stack.pop()
            for e in itertools.combinations(tris[i], 2):
                for j in by_edge[e]:
                    if j == i:
                        continue
                    want = -rel[i] * par(tris[i], *e) * par(tris[j], *e)
                    if rel[j] is None:
                        rel[j] = want; comp.append(j); stack.append(j)
                    elif rel[j] != want:
                        return "closed-inconsistent"     # two triangles forced onto one side of an edge
        comps.append(comp)
    if 1 << (len(comps) - 1) > MAX_CASES:
        return "too-many-cases"
    kinds = set()
    for bits in itertools.product((1, -1), repeat=len(comps) - 1):
        signs = [1, *bits]
        rows = list(base)
        for c, comp in zip(signs, comps):
            for i in comp:
                a, b, t = tris[i]
                wz = W if c * rel[i] == 1 else W_INV
                r = [0] * n; r[t] += 1; r[a] -= 1; r[b] -= wz; r[a] += wz; rows.append(r)
        k = closed(rows, n, edges, nonedges)
        if k is None:
            return "open"
        kinds.add(k)
    return "closed-collision" if kinds == {"collision"} else "closed"


if __name__ == "__main__":
    for path in sys.argv[1:]:
        c = collections.Counter(); left = 0
        for line in open(path):
            g6 = line.strip()
            if not g6:
                continue
            G = nx.from_graph6_bytes(g6.encode())
            v, _ = rhombus(G)
            if v != "none":
                c["rhombus"] += 1; continue
            left += 1
            c[triangle_verdict(G)] += 1
        total = sum(c.values())
        extra = c["closed"] + c["closed-inconsistent"] + c["closed-collision"]
        print(f"{path.rsplit('/', 1)[-1]:24s} graphs {total:5d}  rhombus {c['rhombus']:5d}  left {left:5d}  "
              f"triangles close {extra:5d} ({100 * extra / max(left, 1):5.1f}% of left)  {dict(c)}", flush=True)
