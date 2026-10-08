"""Drawings for the 398 minimal forbidden graphs: every edge unit length except one.

usage: python gallery_embed.py FORBIDDEN74.g6 L10.g6 OUT.json [--workers 2] [--starts 1024] [--rounds 3]

A minimal forbidden graph G is not a unit-distance graph, but G - e is one for every edge e. For each G and each edge
e, batched Levenberg-Marquardt from random angles finds many unit-distance embeddings of G - e (one angle per
spanning-tree edge, so tree edges are unit by construction), each scored for legibility: the smallest distance
between two points and between a point and an edge it is not on (the dashed edge included), with the dashed edge's
distance from length 1 as the tie-break. The best (e, embedding) is refined by Gauss-Newton at 50 digits and kept
only if every solid edge is unit to 1e-35 with the points still apart, so every drawn solid edge is unit length and
the one dashed edge, necessarily, is not.
"""
import sys, json, math, time
from multiprocessing import Pool
import numpy as np
import networkx as nx
import mpmath

F74, L10P, OUT = sys.argv[1:4]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
WORKERS, STARTS, ROUNDS = arg("--workers", 2), arg("--starts", 1024), arg("--rounds", 3)
ITERS = 120


def setup(G):
    n = G.number_of_nodes()
    root = max(G.nodes(), key=G.degree)
    T = nx.bfs_tree(G, root)
    order = list(T.nodes())
    parent = {v: p for p, v in T.edges()}
    idx = {v: k for k, v in enumerate(order[1:])}
    A = np.zeros((n, n - 1))
    for w in range(n):
        x = w
        while x != root:
            A[w, idx[x]] = 1.0
            x = parent[x]
    tree = {frozenset((parent[v], v)) for v in order[1:]}
    F = [(u, v) for u, v in G.edges() if frozenset((u, v)) not in tree]
    return A, np.array([u for u, _ in F], dtype=int), np.array([v for _, v in F], dtype=int)


def lm(G, rng):
    """One batch of LM from random angles; returns (theta, X, Y, maxres) arrays."""
    A, U, V = setup(G)
    n = G.number_of_nodes()
    th = rng.uniform(-np.pi, np.pi, size=(STARTS, n - 1)); th[:, 0] = 0.0
    if len(U) == 0:                                   # a tree: every start is a solution
        c, s = np.cos(th), np.sin(th)
        return th, c @ A.T, s @ A.T, np.zeros(STARTS)
    D = A[U] - A[V]
    lam = np.full(STARTS, 1e-2)

    def res(t):
        c, s = np.cos(t), np.sin(t)
        X, Y = c @ A.T, s @ A.T
        dx, dy = X[:, U] - X[:, V], Y[:, U] - Y[:, V]
        return dx * dx + dy * dy - 1.0, dx, dy, c, s, X, Y

    R, dx, dy, c, s, X, Y = res(th)
    cost = (R * R).sum(1)
    for _ in range(ITERS):
        J = (2.0 * D[None] * (-dx[..., None] * s[:, None, :] + dy[..., None] * c[:, None, :]))[:, :, 1:]
        JtJ = np.einsum("bmk,bml->bkl", J, J)
        g = np.einsum("bmk,bm->bk", J, R)
        k = JtJ.shape[1]
        H = JtJ + lam[:, None, None] * (np.eye(k)[None] * (1.0 + np.einsum("bkk->bk", JtJ)[:, :, None]))
        step = -np.linalg.solve(H, g[..., None])[..., 0]
        tn = th.copy(); tn[:, 1:] += step
        Rn, dxn, dyn, cn, sn, Xn, Yn = res(tn)
        cn_ = (Rn * Rn).sum(1)
        ok = cn_ < cost
        th[ok], R[ok], dx[ok], dy[ok], c[ok], s[ok], X[ok], Y[ok], cost[ok] = \
            tn[ok], Rn[ok], dxn[ok], dyn[ok], cn[ok], sn[ok], Xn[ok], Yn[ok], cn_[ok]
        lam = np.where(ok, np.maximum(lam * 0.3, 1e-12), np.minimum(lam * 2.0, 1e8))
    return th, X, Y, np.abs(R).max(1)


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-300), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))


def legibility(P, edges):
    """(score, gap, clearance): the smallest point-point and point-edge distances; score is their minimum."""
    n = len(P)
    gap = min(float(np.linalg.norm(P[i] - P[j])) for i in range(n) for j in range(i + 1, n))
    clr = min((seg_dist(P[w], P[u], P[v]) for u, v in edges for w in range(n) if w not in (u, v)), default=1.0)
    return min(gap, clr), gap, clr


def polish(G, th0, dps=50, steps=40):
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
        if not R:
            break
        J = mpmath.matrix(len(R), n - 2)
        for e, (u, v) in enumerate(zip(U, V)):
            for k in range(1, n - 1):
                d = A[u, k] - A[v, k]
                if d:
                    J[e, k - 1] = 2 * d * (-(P[u][0] - P[v][0]) * s[k] + (P[u][1] - P[v][1]) * c[k])
        Rm = mpmath.matrix(R)
        try:
            st = mpmath.lu_solve(J.T * J, -(J.T * Rm)) if len(R) >= n - 2 else J.T * mpmath.lu_solve(J * J.T, -Rm)
        except ZeroDivisionError:
            break
        for k in range(1, n - 1):
            t[k] += st[k - 1]
    P, _, _ = pos(t)
    edges_all = list(G.edges())
    worst = max((abs((P[u][0] - P[v][0]) ** 2 + (P[u][1] - P[v][1]) ** 2 - 1) for u, v in edges_all), default=mpmath.mpf(0))
    return P, worst


def draw_one(job):
    idx, g6, source = job
    rng = np.random.default_rng([20260925, idx])
    G = nx.from_graph6_bytes(g6.encode())
    n = G.number_of_nodes()
    best = None
    tried = 0
    for e in sorted(G.edges()):
        H = G.copy(); H.remove_edge(*e)
        for _ in range(ROUNDS):
            th, X, Y, mr = lm(H, rng)
            tried += STARTS
            Pall = np.stack([X, Y], -1)
            dist = np.linalg.norm(Pall[:, :, None, :] - Pall[:, None, :, :], axis=-1)
            dist[:, np.arange(n), np.arange(n)] = np.inf
            gaps = dist.reshape(len(Pall), -1).min(1)
            cand = np.where((mr < 1e-10) & (gaps > 1e-4))[0]
            for b in cand[np.argsort(-gaps[cand])][:24]:      # full scoring only for the best-separated
                P = Pall[b]
                score, gap, clr = legibility(P, list(G.edges()))
                ell = float(np.linalg.norm(P[e[0]] - P[e[1]]))
                key = (round(score, 3), abs(ell - 1))
                if best is None or key > best[0]:
                    best = (key, e, th[b].copy(), score, gap, clr, ell)
            if best is not None and best[1] == e and best[3] > 0.3:
                break
    if best is None:
        return {"g6": g6, "source": source, "n": n, "error": "no embedding of any G - e found"}
    _, e, th, score, gap, clr, ell = best
    H = G.copy(); H.remove_edge(*e)
    Pm, worst_solid = polish(H, th)
    P = np.array([[float(x), float(y)] for x, y in Pm])
    # a genuine embedding keeps its points apart after refinement
    score2, gap2, clr2 = legibility(P, list(G.edges()))
    ell2 = float(np.linalg.norm(P[e[0]] - P[e[1]]))
    # canonical pose for display: centre, principal axis horizontal
    P = P - P.mean(0)
    w, vecs = np.linalg.eigh(P.T @ P)
    P = P @ vecs[:, ::-1]
    return {"g6": g6, "source": source, "n": n, "m": G.number_of_edges(), "removed_edge": list(e),
            "coords": [[round(x, 10), round(y, 10)] for x, y in P], "dashed_length": round(ell2, 10),
            "solid_residual_50digit": mpmath.nstr(worst_solid, 3), "min_gap": round(gap2, 6),
            "min_point_edge_clearance": round(clr2, 6), "genuine": bool(worst_solid < mpmath.mpf(10) ** -35 and gap2 > 1e-6),
            "starts_tried": tried, "degrees": sorted((d for _, d in G.degree()), reverse=True)}


if __name__ == "__main__":
    T0 = time.time()
    jobs = [(i, l.strip(), "GP") for i, l in enumerate(open(F74)) if l.strip()]
    jobs += [(len(jobs) + i, l.strip(), "L10") for i, l in enumerate(open(L10P)) if l.strip()]
    out = []
    with Pool(WORKERS) as pool:
        for k, r in enumerate(pool.imap(draw_one, jobs, chunksize=1)):
            out.append(r)
            if (k + 1) % 25 == 0 or "error" in r or not r.get("genuine", False):
                print(f"{k + 1}/{len(jobs)} {r['g6']} " + (r.get("error") or
                      f"genuine={r['genuine']} gap={r['min_gap']} clr={r['min_point_edge_clearance']} dashed={r['dashed_length']}")
                      + f" {time.time() - T0:.0f}s", flush=True)
    json.dump({"generated_by": "tools/gallery_embed.py", "graphs": out, "seconds": round(time.time() - T0)},
              open(OUT, "w"), indent=0)
    bad = [r["g6"] for r in out if not r.get("genuine")]
    print(json.dumps({"graphs": len(out), "not_genuine": len(bad), "seconds": round(time.time() - T0)}), flush=True)
