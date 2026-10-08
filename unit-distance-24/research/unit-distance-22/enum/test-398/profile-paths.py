#!/usr/bin/env python3
"""Where set 398's extra generator time goes: udenum's two bad-set paths, timed separately.

For a parent H and target (n+1, M), udenum sets d = M - m(H) and
  skips H            if delta(H) <= d-2, or delta(H) = d-1 with more than d minimum-degree vertices;
  RESTRICTED path    if delta(H) = d-1: build_restricted_bad_family enumerates the candidate masks
                     containing every minimum-degree vertex and runs contains_forbidden on each child
                     (every forbidden graph searched in the whole child);
  PATTERN path       otherwise: build_bad_family embeds each deletion pattern F - v with |N(v)| <= d.
This script classifies the sampled parents of speed.py (sample-level-L.g6 in its work directory)
by path, and times set 74 and set 398 on each class separately (median of --reps CPU seconds).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

from t398lib import F398, F74, HERE, NEW_UDENUM, SCRATCH, g6_lines, g6_order_size, run_udenum, write_lines

sys.path.insert(0, str(HERE))
from importlib import import_module  # noqa: E402

speed = import_module("speed")


def degrees(line: bytes) -> list[int]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    deg = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                deg[i] += 1
                deg[j] += 1
            k += 1
    return deg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed-work", type=Path, required=True)
    ap.add_argument("--levels", default="12,15,18,21")
    ap.add_argument("--max-parents", type=int, default=1500)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--work", type=Path, default=SCRATCH / "profile-paths")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "profile-paths.json")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    table = json.loads(speed.REACH.read_text())["table"]
    out = {}
    for L in (int(x) for x in a.levels.split(",")):
        pool = g6_lines(a.speed_work / f"sample-level-{L}.g6")   # generation order: sample, never slice
        parents = random.Random(a.seed + L).sample(pool, min(a.max_parents, len(pool)))
        by_m: dict[int, list[bytes]] = {}
        for g in parents:
            by_m.setdefault(g6_order_size(g)[1], []).append(g)
        classes = {"restricted": {}, "pattern": {}}
        counts = {"skipped": 0, "restricted": 0, "pattern": 0}
        for M in sorted(int(x) for x in table[str(L + 1)]):
            for m in speed.sources(table, L, M):
                d = M - m
                for g in by_m.get(m, []):
                    deg = degrees(g)
                    delta = min(deg)
                    if delta <= d - 2 or (delta == d - 1 and deg.count(delta) > d):
                        counts["skipped"] += 1
                    elif delta == d - 1:
                        counts["restricted"] += 1
                        classes["restricted"].setdefault(M, []).append(g)
                    else:
                        counts["pattern"] += 1
                        classes["pattern"].setdefault(M, []).append(g)
        rec = {"parent_records": counts}
        for cls, cells in classes.items():
            cpu = {"74": [0.0] * a.reps, "398": [0.0] * a.reps}
            for M, gs in cells.items():
                f = a.work / f"L{L}-{cls}-{M}.g6"
                write_lines(f, gs)
                for r in range(a.reps):
                    for s, extra, forb in (("74", [], F74), ("398", ["--forbidden-set", "398"], F398)):
                        st = run_udenum(NEW_UDENUM, f, L + 1, M, a.work / f"L{L}-{cls}-{M}-{s}.out.g6",
                                        extra=extra, forbidden=forb)
                        cpu[s][r] += st["cpu_seconds"]
            med = {s: statistics.median(v) for s, v in cpu.items()}
            rec[cls] = {"cpu_seconds_median": med, "ratio_398_over_74": med["398"] / med["74"] if med["74"] else None}
        out[str(L)] = rec
        print(f"level {L}: parent records {counts}; restricted path cpu 74 {rec['restricted']['cpu_seconds_median']['74']:.3f} "
              f"s, 398 {rec['restricted']['cpu_seconds_median']['398']:.3f} s; pattern path cpu 74 "
              f"{rec['pattern']['cpu_seconds_median']['74']:.3f} s, 398 {rec['pattern']['cpu_seconds_median']['398']:.3f} s",
              flush=True)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
