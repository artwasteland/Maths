#!/usr/bin/env python3
"""Count, per planned range, the parents that pass the AMP minimum-degree guard (i.e. are
actually extended rather than skipped), using only the parent records and the target m."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import enum2
plan = json.loads(Path(sys.argv[1]).read_text())["plan"]
cache = {}
total = proc = 0
per_cell = {}
for p in plan:
    if p["parent_file"] not in cache:
        cache.clear()
        cache[p["parent_file"]] = [l.rstrip("\n") for l in open(p["parent_file"]) if l.strip() and not l.startswith(">>")]
    recs = cache[p["parent_file"]]
    k = 0
    for code in recs[p["a"]:p["b"]]:
        g = enum2.graph6_decode(code)
        d = p["m"] - g.m
        if d < 0 or d > g.n:
            continue
        degs = [g.degree(v) for v in range(g.n)]
        delta = min(degs)
        if delta <= d - 2:
            continue
        if delta == d - 1 and degs.count(delta) > d:
            continue
        k += 1
    total += p["b"] - p["a"]; proc += k
    c = per_cell.setdefault(p["cell"], [0, 0]); c[0] += p["b"] - p["a"]; c[1] += k
for cell in sorted(per_cell, key=lambda x: tuple(map(int, x.split("-")))):
    print(cell, "replayed", per_cell[cell][0], "pass_guard", per_cell[cell][1])
print("total replayed", total, "pass_guard", proc)
