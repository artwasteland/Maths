#!/usr/bin/env python3
"""Soundness fuzz with KNOWN embeddings (a positive control beyond B10).

Point sets: random subsets of unions of triangular-lattice patches, each rotated by a random angle from a set that
makes many cross unit distances (0, the Moser angle arccos(5/6), arccos(7/8), the 3-4-5 angle, ...) and shifted by a
lattice or unit vector.  Graphs: the unit-distance graph of the points (faithful), and copies with random edges
deleted (still unit-distance graphs, with the same embedding, but not faithful, so forced unit distances on
non-edges are legitimate).  udtriangle must never refute one, and for every tu verdict the embedding and its mirror
image, followed through the case tree by their own triangle orientations, must reach a unit leaf whose relation
f(a) - f(b) = w^k (f(p) - f(q)) holds (to 1e-9 in double precision; the coordinates are exact to ~1e-14).

usage: fuzz_ud.py OUTDIR COUNT SEED     (writes OUTDIR/fuzz-ud.g6 and OUTDIR/fuzz-ud.coords.json)
       fuzz_ud.py --check OUTDIR        (after udtriangle wrote OUTDIR/fuzz-ud.out)
"""
import cmath
import itertools
import json
import math
import random
import sys
from pathlib import Path

import networkx as nx

W = cmath.exp(1j * math.pi / 3)
ANGLES = [0.0, math.acos(5 / 6), math.acos(7 / 8), math.atan2(4, 3), math.acos(1 / 3), math.acos(3 / 4)]
TOL = 1e-9


def patch(radius):
    return [a + b * W for a in range(-radius, radius + 1) for b in range(-radius, radius + 1) if abs(a + b) <= radius]


def point_set(rng):
    pts = []
    for _ in range(rng.randint(1, 3)):
        rot = cmath.exp(1j * rng.choice(ANGLES)) * rng.choice([1, W, W * W])
        shift = rng.choice([0, 1, W, cmath.exp(1j * rng.choice(ANGLES)), 1 + cmath.exp(1j * rng.choice(ANGLES))])
        for z in patch(rng.randint(1, 3)):
            q = rot * z + shift
            if all(abs(q - p) > 1e-6 for p in pts):
                pts.append(q)
    rng.shuffle(pts)
    return pts


def grown_set(rng, n):
    """Random growth: attach equilateral triangles on unit pairs (either side), unit spokes at angles from a
    finite set, and circle intersections of two points less than 2 apart; keeps points distinct."""
    pts = [0j, 1 + 0j, W]
    phis = [k * math.pi / 3 + a for k in range(6) for a in (0.0, math.acos(5 / 6), math.atan2(4, 3))]

    def add(q):
        if all(abs(q - p) > 1e-6 for p in pts):
            pts.append(q)

    while len(pts) < n:
        op = rng.random()
        if op < 0.45:
            units = [(i, j) for i, j in itertools.combinations(range(len(pts)), 2) if abs(abs(pts[i] - pts[j]) - 1) < 1e-9]
            i, j = rng.choice(units)
            add(pts[i] + (W if rng.random() < 0.5 else W.conjugate()) * (pts[j] - pts[i]))
        elif op < 0.75:
            add(rng.choice(pts) + cmath.exp(1j * rng.choice(phis)))
        else:
            i, j = rng.sample(range(len(pts)), 2)
            d = pts[j] - pts[i]
            if 1e-6 < abs(d) < 2 - 1e-6:
                h = math.sqrt(1 - (abs(d) / 2) ** 2)
                mid = pts[i] + d / 2
                add(mid + (1 if rng.random() < 0.5 else -1) * 1j * d / abs(d) * h)
    rng.shuffle(pts)
    return pts


def unit_graph(pts):
    G = nx.Graph()
    G.add_nodes_from(range(len(pts)))
    for i, j in itertools.combinations(range(len(pts)), 2):
        if abs(abs(pts[i] - pts[j]) - 1) < 1e-9:
            G.add_edge(i, j)
    return G


def generate(outdir, count, seed):
    rng = random.Random(seed)
    graphs, coords = [], []
    while len(graphs) < count:
        n = rng.randint(6, 24)
        pts = point_set(rng) if rng.random() < 0.4 else grown_set(rng, rng.randint(n, 30))
        if len(pts) < n:
            continue
        # a connected-ish random subset: grow from a random point along unit distances, then pad
        start = rng.randrange(len(pts))
        full = unit_graph(pts)
        chosen = [start]
        frontier = set(full[start])
        while len(chosen) < n and frontier:
            v = rng.choice(sorted(frontier))
            chosen.append(v)
            frontier |= set(full[v])
            frontier -= set(chosen)
        if len(chosen) < n:
            continue
        sub = [pts[v] for v in chosen]
        G = unit_graph(sub)
        if G.number_of_edges() < n:
            continue
        variants = [G]
        for _ in range(2):                                   # non-faithful: delete up to 3 random edges
            H = G.copy()
            es = sorted(H.edges())
            for e in rng.sample(es, min(len(es), rng.randint(1, 3))):
                H.remove_edge(*e)
            variants.append(H)
        for H in variants:
            graphs.append(nx.to_graph6_bytes(H, header=False).decode().strip())
            coords.append([[z.real, z.imag] for z in sub])
    Path(outdir).mkdir(parents=True, exist_ok=True)
    Path(outdir, "fuzz-ud.g6").write_text("\n".join(graphs) + "\n")
    Path(outdir, "fuzz-ud.coords.json").write_text(json.dumps(coords))


def check(outdir):
    graphs = Path(outdir, "fuzz-ud.g6").read_text().split()
    coords = json.loads(Path(outdir, "fuzz-ud.coords.json").read_text())
    verdicts = [json.loads(l) for l in Path(outdir, "fuzz-ud.out").read_text().splitlines()]
    assert len(graphs) == len(coords) == len(verdicts)
    stats = {"graphs": len(graphs), "pass": 0, "tu": 0, "refuted": 0, "leaf_checks": 0, "split_trees": 0}
    bad = []
    for g6, xy, rec in zip(graphs, coords, verdicts):
        stats[rec["verdict"]] += 1
        if rec["verdict"] == "pass":
            continue
        if rec["verdict"] == "refuted":
            bad.append((g6, "refuted a unit-distance graph"))
            continue
        z0 = [complex(x, y) for x, y in xy]
        tree = rec["witness"]["tri"]["tree"]
        stats["split_trees"] += "split" in tree
        for mirror in (False, True):
            z = [p.conjugate() for p in z0] if mirror else z0
            node = tree
            while "split" in node:
                a, b, c = node["split"]
                r = (z[c] - z[a]) / (z[b] - z[a])
                if abs(r - W) < TOL:
                    node = node["plus"]
                elif abs(r - W.conjugate()) < TOL:
                    node = node["minus"]
                else:
                    raise SystemExit(f"{g6}: split triangle not equilateral")
            L = node["leaf"]
            stats["leaf_checks"] += 1
            if "edge" not in L:
                bad.append((g6, f"mirror={mirror}: reached a collision leaf"))
                continue
            a, b = L["pair"]
            p, q = L["edge"]
            if abs((z[a] - z[b]) - W ** L["zeta"] * (z[p] - z[q])) > TOL or abs(abs(z[a] - z[b]) - 1) > TOL:
                bad.append((g6, f"mirror={mirror}: forced pair {a},{b} at distance {abs(z[a] - z[b])}"))
    print("fuzz-ud:", " ".join(f"{k}={v}" for k, v in stats.items()), f"failures={len(bad)}")
    for b in bad[:20]:
        print("  FAIL", *b)
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        sys.exit(check(sys.argv[2]))
    generate(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
