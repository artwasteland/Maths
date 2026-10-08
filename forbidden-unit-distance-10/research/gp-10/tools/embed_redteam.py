"""Numeric red team for the GP-10 refutations: try hard to EMBED every one of the 324 minimal forbidden graphs.

usage: python embed_redteam.py L10.g6 B10.g6 RECORDS.jsonl OUT.json [--starts 2048] [--rounds 8] [--seed 20260925]
       [--part k/K]

Independent of every certificate, of the checker and of the producers: numpy, with networkx only for graph6 and a
spanning tree. A graph is parametrised by one angle per spanning-tree edge (tree edges are unit by construction, the
first angle is fixed to remove rotation), and batched Levenberg-Marquardt from random angles drives every other edge's
squared length to 1. A solution counts only if every edge is unit to 1e-10 and no two points are closer than 1e-4: a
collision is exactly how many forbidden graphs "embed" degenerately. Every float candidate is then refined by
Gauss-Newton at 50 digits: a genuine embedding keeps its gap while the residual falls below 1e-35; a near-miss beside a
degenerate solution family slides into the collision (its gap falls to ~1e-15), and is counted as a near-miss. The same
rule decides members and controls, so the controls measure the power of exactly the test the members face.

A search that never finds anything proves nothing unless its power is measured, so for every L10 member the same
budget is spent on two embeddable controls: (a) the member minus one edge, chosen to stay biconnected (embedded, by
minimality), and (b) an embedded B10 graph with the same number of edges, with the same degree sequence when one
exists. A hit on an L10 member would contradict its refutation certificate: it is re-polished at 60 digits and
reported, never filtered.
"""
import sys, json, time, random
import numpy as np
import networkx as nx
import mpmath

L10_PATH, B10_PATH, REC_PATH, OUT = sys.argv[1:5]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
STARTS, ROUNDS, SEED = arg("--starts", 2048), arg("--rounds", 8), arg("--seed", 20260925)
PART = arg("--part", "0/1")                                 # k/K: members k, k+K, k+2K, ...
EDGE_TOL, GAP_MIN, ITERS, PER_ROUND = 1e-10, 1e-4, 120, 3
graph = lambda g6: nx.from_graph6_bytes(g6.encode())


def setup(G):
    n = G.number_of_nodes()
    T = nx.bfs_tree(G, 0)
    order = list(T.nodes())
    parent = {v: p for p, v in T.edges()}
    idx = {v: k for k, v in enumerate(order[1:])}          # tree edge k ends at order[k + 1]
    A = np.zeros((n, n - 1))
    for w in range(n):
        x = w
        while x != 0:
            A[w, idx[x]] = 1.0
            x = parent[x]
    tree = {frozenset((parent[v], v)) for v in order[1:]}
    F = [(u, v) for u, v in G.edges() if frozenset((u, v)) not in tree]
    return A, np.array([u for u, _ in F]), np.array([v for _, v in F])


def residuals(th, A, U, V):
    c, s = np.cos(th), np.sin(th)
    X, Y = c @ A.T, s @ A.T
    dx, dy = X[:, U] - X[:, V], Y[:, U] - Y[:, V]
    return dx * dx + dy * dy - 1.0, dx, dy, c, s, X, Y


def search(G, rng, stop_on_hit):
    """Batched LM from random angles; returns (genuine hits as (theta, polished residual, polished gap), polished gaps of
    the near-misses, starts used)."""
    A, U, V = setup(G)
    n = G.number_of_nodes()
    D = A[U] - A[V]                                        # m x (n-1)
    hits, near, used = [], [], 0
    for _ in range(ROUNDS):
        th = rng.uniform(-np.pi, np.pi, size=(STARTS, n - 1)); th[:, 0] = 0.0
        lam = np.full(STARTS, 1e-2)
        R, dx, dy, c, s, X, Y = residuals(th, A, U, V)
        cost = (R * R).sum(1)
        for _ in range(ITERS):
            J = 2.0 * D[None] * (-dx[..., None] * s[:, None, :] + dy[..., None] * c[:, None, :])
            J = J[:, :, 1:]                                # the first angle is fixed
            JtJ = np.einsum("bmk,bml->bkl", J, J)
            g = np.einsum("bmk,bm->bk", J, R)
            k = JtJ.shape[1]
            H = JtJ + lam[:, None, None] * (np.eye(k)[None] * (1.0 + np.einsum("bkk->bk", JtJ)[:, :, None]))
            step = -np.linalg.solve(H, g[..., None])[..., 0]
            tn = th.copy(); tn[:, 1:] += step
            Rn, dxn, dyn, cn, sn, Xn, Yn = residuals(tn, A, U, V)
            cn_ = (Rn * Rn).sum(1)
            ok = cn_ < cost
            th[ok], R[ok], dx[ok], dy[ok], c[ok], s[ok], X[ok], Y[ok], cost[ok] = \
                tn[ok], Rn[ok], dxn[ok], dyn[ok], cn[ok], sn[ok], Xn[ok], Yn[ok], cn_[ok]
            lam = np.where(ok, np.maximum(lam * 0.3, 1e-12), np.minimum(lam * 2.0, 1e8))
        used += STARTS
        maxres = np.abs(R).max(1)
        P = np.stack([X, Y], -1)
        dist = np.linalg.norm(P[:, :, None, :] - P[:, None, :, :], axis=-1)
        dist[:, np.arange(n), np.arange(n)] = np.inf
        gap = dist.reshape(STARTS, -1).min(1)
        good = np.where((maxres < EDGE_TOL) & (gap > GAP_MIN))[0]
        for b in good[:PER_ROUND]:
            res, gp = polish(G, th[b])
            if res < mpmath.mpf(10) ** -35 and gp > mpmath.mpf(10) ** -6:
                hits.append((th[b].copy(), mpmath.nstr(res, 3), mpmath.nstr(gp, 8)))
            else:
                near.append(mpmath.nstr(gp, 3))
        if hits and stop_on_hit:
            break
    return hits, near, used


def polish(G, th0, dps=50, steps=40):
    """Gauss-Newton at `dps` digits from a float solution; a genuine embedding keeps its gap as the residual -> 0."""
    mpmath.mp.dps = dps
    A, U, V = setup(G)
    n = G.number_of_nodes()
    t = [mpmath.mpf(float(x)) for x in th0]
    def pos(t):
        c = [mpmath.cos(x) for x in t]; s = [mpmath.sin(x) for x in t]
        return [(sum(c[k] for k in range(n - 1) if A[w, k]), sum(s[k] for k in range(n - 1) if A[w, k])) for w in range(n)], c, s
    for _ in range(steps):
        P, c, s = pos(t)
        R = [(P[u][0] - P[v][0]) ** 2 + (P[u][1] - P[v][1]) ** 2 - 1 for u, v in zip(U, V)]
        J = mpmath.matrix(len(R), n - 2)
        for e, (u, v) in enumerate(zip(U, V)):
            for k in range(1, n - 1):
                d = A[u, k] - A[v, k]
                if d:
                    J[e, k - 1] = 2 * d * (-(P[u][0] - P[v][0]) * s[k] + (P[u][1] - P[v][1]) * c[k])
        Rm = mpmath.matrix(R)
        try:
            if len(R) >= n - 2:
                st = mpmath.lu_solve(J.T * J, -(J.T * Rm))
            else:
                st = J.T * mpmath.lu_solve(J * J.T, -Rm)
        except ZeroDivisionError:
            break
        for k in range(1, n - 1):
            t[k] += st[k - 1]
    P, _, _ = pos(t)
    R = [(P[u][0] - P[v][0]) ** 2 + (P[u][1] - P[v][1]) ** 2 - 1 for u, v in zip(U, V)]
    gap = min(mpmath.sqrt((P[a][0] - P[b][0]) ** 2 + (P[a][1] - P[b][1]) ** 2) for a in range(n) for b in range(a + 1, n))
    return max(abs(r) for r in R), gap


T0 = time.time()
L10 = [l.strip() for l in open(L10_PATH) if l.strip()]
L10 = L10[int(PART.split("/")[0])::int(PART.split("/")[1])]
B10 = [l.strip() for l in open(B10_PATH) if l.strip()]
verdict = {}
with open(REC_PATH) as f:
    for line in f:
        r = json.loads(line)
        verdict[r["g6"]] = r["verdict"]
        del r
emb_by = {}
for g in B10:
    if verdict.get(g) == "embedded":
        H = graph(g)
        emb_by.setdefault(H.number_of_edges(), {}).setdefault(tuple(sorted(d for _, d in H.degree())), []).append(g)

rng = np.random.default_rng([SEED, int(PART.split("/")[0])])
prng = random.Random(f"{SEED}-{PART}")
used_controls = set()
rows = []
for i, g in enumerate(L10):
    G = graph(g)
    m, ds = G.number_of_edges(), tuple(sorted(d for _, d in G.degree()))
    hits, near, used = search(G, rng, stop_on_hit=False)
    row = {"g6": g, "edges": m, "starts": used, "hits": len(hits), "near_misses": len(near), "near_miss_gaps": near[:3]}
    if hits:
        row["polished"] = [(res, gp) for _, res, gp in hits[:2]]
        print("GENUINE HIT on L10 member", g, row["polished"], flush=True)
    # control (a): minus one edge, still biconnected
    es = list(G.edges()); prng.shuffle(es)
    for e in es:
        Dg = G.copy(); Dg.remove_edge(*e)
        if nx.is_biconnected(Dg):
            break
    h, nr, u = search(Dg, rng, stop_on_hit=True)
    row["minus_edge"] = {"edge": list(e), "found": bool(h), "starts": u, "near_misses": len(nr)}
    # control (b): an embedded B10 graph with the same edge count (same degree sequence if possible)
    pool = [x for x in emb_by.get(m, {}).get(ds, []) if x not in used_controls]
    kind = "same_degrees"
    if not pool:
        pool = [x for seqs in emb_by.get(m, {}).values() for x in seqs if x not in used_controls]; kind = "same_edges"
    if pool:
        c = prng.choice(sorted(pool)); used_controls.add(c)
        h, nr, u = search(graph(c), rng, stop_on_hit=True)
        row["lookalike"] = {"g6": c, "kind": kind, "found": bool(h), "starts": u, "near_misses": len(nr)}
    rows.append(row)
    if (i + 1) % 25 == 0:
        fa = sum(r["minus_edge"]["found"] for r in rows); fb = sum(r.get("lookalike", {}).get("found", False) for r in rows)
        print(f"{i + 1}/{len(L10)} members, genuine hits {sum(r['hits'] for r in rows)}, near-misses {sum(r['near_misses'] for r in rows)}; controls found: minus-edge {fa}/{len(rows)},"
              f" look-alike {fb}/{sum('lookalike' in r for r in rows)}; {time.time() - T0:.0f}s", flush=True)


def rate(key, pred=lambda r: True):
    rs = [r for r in rows if key in r and pred(r)]
    return {"tested": len(rs), "found": sum(r[key]["found"] for r in rs)}


by_m = {}
for m in sorted({r["edges"] for r in rows}):
    p = lambda r, m=m: r["edges"] == m
    by_m[m] = {"members": sum(p(r) for r in rows), "member_hits": sum(r["hits"] for r in rows if p(r)),
               "minus_edge": rate("minus_edge", p), "lookalike": rate("lookalike", p)}
rep = {"budget_per_member": STARTS * ROUNDS, "iterations": ITERS, "edge_tol": EDGE_TOL, "gap_min": GAP_MIN, "seed": SEED,
       "genuine_rule": "50-digit Gauss-Newton refinement: residual < 1e-35 and gap > 1e-6",
       "members_with_near_misses": sum(1 for r in rows if r["near_misses"]),
       "members": len(rows), "members_with_numeric_embedding": [r["g6"] for r in rows if r["hits"]],
       "controls_minus_edge": rate("minus_edge"), "controls_lookalike": rate("lookalike"), "by_edges": by_m,
       "seconds": round(time.time() - T0), "rows": rows}
rep["verdict"] = ("NO EMBEDDING FOUND for any of the %d members" % len(rows)) if not rep["members_with_numeric_embedding"] \
    else "EMBEDDING FOUND for %d members: investigate" % len(rep["members_with_numeric_embedding"])
json.dump(rep, open(OUT, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("verdict", "controls_minus_edge", "controls_lookalike", "by_edges", "seconds")}), flush=True)
