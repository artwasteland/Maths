#!/usr/bin/env python3
"""GP-11 check 3: try to embed every independently derived L11 member.

Adapted from GP-10 embed_redteam.py: spanning-tree angles, batched LM, and
high-precision refinement. Uses a local graph decoder/BFS, bounded processes,
stable per-graph seeds and shards. Search failure is evidence, never a proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

for _variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_variable] = "1"
import numpy as np
import mpmath as mp

from independent_core import (adjacency, biconnected, bounded_map, decode_g6,
    encode_g6, lines, record, require, shard, write_json, source_hashes, guard_outputs, digest)

EDGE_TOL, GAP_MIN = 1e-10, 1e-4


def setup(graph):
    n, edges = graph
    adj = adjacency(n, edges)
    order, parent = [0], {}
    for v in order:
        for w in sorted(adj[v]):
            if w != 0 and w not in parent:
                parent[w] = v
                order.append(w)
    require(len(order) == n, "search_graph", "angle search requires a connected graph")
    idx = {v: k for k, v in enumerate(order[1:])}
    a = np.zeros((n, n - 1))
    for v in range(n):
        w = v
        while w:
            a[v, idx[w]] = 1.0
            w = parent[w]
    tree = {tuple(sorted((v, parent[v]))) for v in order[1:]}
    others = sorted(edges - tree)
    return a, np.array([u for u, v in others], dtype=int), np.array([v for u, v in others], dtype=int)


def residuals(theta, a, u, v):
    c, s = np.cos(theta), np.sin(theta)
    x, y = c @ a.T, s @ a.T
    dx, dy = x[:, u] - x[:, v], y[:, u] - y[:, v]
    return dx * dx + dy * dy - 1, dx, dy, c, s, x, y


def polish(graph, initial, dps=60, steps=80):
    """Damped high-precision Gauss-Newton; all actual edges checked at end."""
    mp.mp.dps = dps
    a, u, v = setup(graph)
    n, edges = graph
    theta = [mp.mpf(float(t)) for t in initial]
    damp = mp.mpf("1e-12")

    def positions(t):
        c, s = [mp.cos(z) for z in t], [mp.sin(z) for z in t]
        pts = [(sum((c[k] for k in range(n - 1) if a[w, k]), mp.mpf(0)),
                sum((s[k] for k in range(n - 1) if a[w, k]), mp.mpf(0))) for w in range(n)]
        return pts, c, s

    def residual(pts):
        return [(pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 - 1 for i, j in zip(u, v)]

    for _ in range(steps):
        pts, c, s = positions(theta)
        r = residual(pts)
        if not r or max(map(abs, r)) < mp.mpf(10) ** (12 - dps):
            break
        j = mp.matrix(len(r), n - 2)
        for e, (i, k) in enumerate(zip(u, v)):
            for column in range(1, n - 1):
                diff = int(a[i, column] - a[k, column])
                if diff:
                    j[e, column - 1] = 2 * diff * (-(pts[i][0] - pts[k][0]) * s[column]
                                                   + (pts[i][1] - pts[k][1]) * c[column])
        rm = mp.matrix(r)
        try:
            if len(r) >= n - 2:
                normal = j.T * j
                for k in range(n - 2):
                    normal[k, k] += damp
                step = mp.lu_solve(normal, -(j.T * rm))
            else:
                normal = j * j.T
                for k in range(len(r)):
                    normal[k, k] += damp
                step = j.T * mp.lu_solve(normal, -rm)
        except ZeroDivisionError:
            damp *= 100
            continue
        oldcost = sum(z * z for z in r)
        accepted = False
        scale = mp.mpf(1)
        for _ in range(12):
            candidate = [theta[0]] + [theta[k] + scale * step[k - 1] for k in range(1, n - 1)]
            trial, _, _ = positions(candidate)
            if sum(z * z for z in residual(trial)) < oldcost:
                theta, accepted = candidate, True
                break
            scale /= 2
        damp = max(mp.mpf(10) ** (10 - dps), damp / 10) if accepted else damp * 100
    pts, _, _ = positions(theta)
    all_res = [(pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 - 1 for i, j in edges]
    gap = min(mp.sqrt((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2)
              for i in range(n) for j in range(i + 1, n))
    return max(map(abs, all_res), default=mp.mpf(0)), gap, theta, pts


def search(graph, rng, cfg, stop_on_hit):
    a, u, v = setup(graph)
    n, edges = graph
    d = a[u] - a[v]
    hits, near, used = [], [], 0
    for _ in range(cfg["rounds"]):
        theta = rng.uniform(-np.pi, np.pi, size=(cfg["starts"], n - 1))
        theta[:, 0] = 0.0
        lam = np.full(cfg["starts"], 1e-2)
        r, dx, dy, c, s, x, y = residuals(theta, a, u, v)
        cost = (r * r).sum(1)
        for _ in range(cfg["iters"]):
            j = 2 * d[None] * (-dx[..., None] * s[:, None, :] + dy[..., None] * c[:, None, :])
            j = j[:, :, 1:]
            normal, gradient = np.einsum("bmk,bml->bkl", j, j), np.einsum("bmk,bm->bk", j, r)
            k = normal.shape[1]
            h = normal + lam[:, None, None] * (np.eye(k)[None] * (1 + np.einsum("bkk->bk", normal)[:, :, None]))
            step = -np.linalg.solve(h, gradient[..., None])[..., 0]
            trial = theta.copy()
            trial[:, 1:] += step
            rn, dxn, dyn, cn, sn, xn, yn = residuals(trial, a, u, v)
            nextcost = (rn * rn).sum(1)
            accept = nextcost < cost
            theta[accept], r[accept], dx[accept], dy[accept], c[accept], s[accept], x[accept], y[accept], cost[accept] = (
                trial[accept], rn[accept], dxn[accept], dyn[accept], cn[accept], sn[accept], xn[accept], yn[accept], nextcost[accept])
            lam = np.where(accept, np.maximum(lam * .3, 1e-12), np.minimum(lam * 2, 1e8))
        used += cfg["starts"]
        maxres = np.abs(r).max(1) if len(u) else np.zeros(cfg["starts"])
        pts = np.stack([x, y], axis=-1)
        distances = np.linalg.norm(pts[:, :, None] - pts[:, None], axis=-1)
        distances[:, np.arange(n), np.arange(n)] = np.inf
        gap = distances.reshape(cfg["starts"], -1).min(1)
        candidates = np.where((maxres < EDGE_TOL) & (gap > GAP_MIN))[0]
        for b in candidates[:cfg["polish_per_round"]]:
            residue, polished_gap, angles, coords = polish(graph, theta[b], dps=60)
            if residue < mp.mpf("1e-45") and polished_gap > mp.mpf("1e-6"):
                hits.append({"residue": mp.nstr(residue, 12), "gap": mp.nstr(polished_gap, 12),
                             "angles": [mp.nstr(t, 60) for t in angles],
                             "coordinates": [[mp.nstr(z, 60) for z in point] for point in coords]})
            else:
                near.append({"residue": mp.nstr(residue, 8), "gap": mp.nstr(polished_gap, 8)})
        if hits and stop_on_hit:
            break
    return {"found": bool(hits), "hits": hits[:3], "starts": used,
            "near_misses": len(near), "near_miss_details": near[:3]}


def worker(task):
    g, control, cfg = task
    t0 = time.monotonic()
    material = f"{cfg['seed']}\0{g}".encode()
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(material).digest()[:16], "big"))
    graph = decode_g6(g)
    result = search(graph, rng, cfg, False)
    row = {"g6": g, "edges": len(graph[1]), "member": result}
    # Same stopping/acceptance rule and same budget ceiling for every control.
    n, edges = graph
    removed = next((e for e in sorted(edges) if biconnected(n, edges - {e})), None)
    require(removed is not None, "control", "no biconnected edge deletion available")
    row["minus_edge"] = {"edge": list(removed), **search((n, edges - {removed}), rng, cfg, True)}
    row["embedded_B11_control"] = {"g6": control, **search(decode_g6(control), rng, cfg, True)}
    row["seconds"] = round(time.monotonic() - t0, 3)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("l11")
    p.add_argument("b11")
    p.add_argument("records")
    p.add_argument("out")
    p.add_argument("--starts", type=int, default=2048)
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--iters", type=int, default=120)
    p.add_argument("--polish-per-round", type=int, default=3)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--shard", default="0/1")
    p.add_argument("--limit", type=int)
    p.add_argument("--seed", type=int, default=20261007)
    p.add_argument("--details", help="append small per-graph results as they complete")
    a = p.parse_args()
    guard_outputs([a.l11, a.b11, a.records], [a.out] + ([a.details] if a.details else []))
    sources = source_hashes("independent_core.py", "embed_redteam.py")
    require(min(a.starts, a.rounds, a.iters, a.jobs, a.polish_per_round) > 0,
            "arguments", "budgets/jobs must be positive")
    t0 = time.monotonic()
    si, sn = shard(a.shard)
    all_members = [raw[:-1].decode("ascii") for _, raw in lines(a.l11)]
    require(all_members == sorted(set(all_members)), "L11", "L11 must be sorted and unique")
    members = all_members[si::sn]
    if a.limit:
        require(a.limit > 0, "arguments", "limit must be positive")
        members = members[:a.limit]
    require(members, "L11", "no members selected; this is not a successful search")
    population = {raw[:-1].decode("ascii") for _, raw in lines(a.b11)}
    require(set(members) <= population, "L11", "member is outside B11 input")
    emb_by, seen = {}, set()
    records_hash = hashlib.sha256()
    for _, raw in lines(a.records):
        records_hash.update(raw)
        rec = record(raw)
        require(rec["g6"] not in seen, "duplicate_record", f"duplicate record {rec['g6']}")
        seen.add(rec["g6"])
        if rec["verdict"] == "embedded" and rec["g6"] in population:
            n, edges = decode_g6(rec["g6"])
            degrees = tuple(sorted(map(len, adjacency(n, edges))))
            emb_by.setdefault(len(edges), {}).setdefault(degrees, []).append(rec["g6"])
    require(population == seen, "coverage", "search control records must cover supplied B11 exactly")
    require(emb_by, "control", "no embedded B11 controls")
    cfg = {key: getattr(a, key) for key in ("starts", "rounds", "iters", "polish_per_round", "seed")}

    def tasks():
        for g in members:
            n, edges = decode_g6(g)
            degrees = tuple(sorted(map(len, adjacency(n, edges))))
            bucket = emb_by.get(len(edges), {})
            pool = bucket.get(degrees) or [h for hosts in bucket.values() for h in hosts]
            if not pool:
                nearest = min(emb_by, key=lambda m: abs(m - len(edges)))
                pool = [h for hosts in emb_by[nearest].values() for h in hosts]
            chooser = random.Random(f"{a.seed}:{g}:control")
            yield g, chooser.choice(sorted(pool)), cfg

    rows, errors = [], []
    details = open(a.details, "w") if a.details else None
    try:
        for row in bounded_map(worker, tasks(), a.jobs, pending_per_job=1):
            rows.append(row)
            if details:
                details.write(json.dumps(row, sort_keys=True) + "\n")
                details.flush()
            print(f"{len(rows)}/{len(members)} {row['g6']} member_found={row['member']['found']} "
                  f"minus_edge={row['minus_edge']['found']} embedded_control={row['embedded_B11_control']['found']}", flush=True)
        rows.sort(key=lambda r: r["g6"])
        hits = [r["g6"] for r in rows if r["member"]["found"]]
        power = all(r["minus_edge"]["found"] and r["embedded_B11_control"]["found"] for r in rows)
        require(sources == source_hashes("independent_core.py", "embed_redteam.py"),
                "source_changed", "tool source changed during numerical checking")
        status = "COUNTEREXAMPLE_CANDIDATE" if hits else "NO_COUNTEREXAMPLE_FOUND" if power else "INCONCLUSIVE_CONTROLS"
        rep = {"status": status, "scope": "sample-or-shard" if a.limit or sn > 1 else "all provided L11",
               "search_is_not_a_proof": True, "members": len(rows), "total_L11": len(all_members),
               "member_hits": hits, "controls_all_found": power, "shard": a.shard,
               "source_hashes": sources,
               "input_hashes": {"L11": digest(a.l11), "B11": digest(a.b11), "records": records_hash.hexdigest()},
               "config": cfg, "budget_per_graph": a.starts * a.rounds, "float_edge_tol": EDGE_TOL,
               "float_gap_min": GAP_MIN, "genuine_rule": "60-digit refinement; all edge residues <1e-45; all pair gaps >1e-6",
               "controls_minus_edge_found": sum(r["minus_edge"]["found"] for r in rows),
               "controls_embedded_B11_found": sum(r["embedded_B11_control"]["found"] for r in rows),
               "seconds": round(time.monotonic() - t0, 3), "worker_seconds": sum(r["seconds"] for r in rows), "rows": rows}
        write_json(a.out, rep)
        print(json.dumps({k: rep[k] for k in ("status", "members", "controls_all_found", "seconds")}), flush=True)
        return 0 if status == "NO_COUNTEREXAMPLE_FOUND" else 1 if hits else 2
    finally:
        if details:
            details.close()


if __name__ == "__main__":
    sys.exit(main())
