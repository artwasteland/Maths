#!/usr/bin/env python3
"""Where the time goes after the Mode 398 speed work: profile-paths.py's measurement, three binaries.

Exactly profile-paths.py's parents and classification: per level L, random.Random(seed + L) samples
up to --max-parents of speed.py's sample-level-L.g6; each (parent, target cell) is classified as
skipped, RESTRICTED path (delta = d - 1) or PATTERN path (otherwise), and each class is timed
separately (median of --reps CPU seconds) with
  74       the new enum/udenum in set 74 (whose code is unchanged)
  base398  the CURRENT Mode 398 (test-398/base398/udenum)
  new398   the new enum/udenum in set 398
Outputs of base398 and new398 are compared byte for byte on every class file.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from importlib import import_module
from pathlib import Path

from speed398lib import BASE398_UDENUM, HERE, NEW_UDENUM, SCRATCH, compare_runs, g6_lines, g6_order_size, run_udenum, write_lines

sys.path.insert(0, str(HERE))
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
    ap.add_argument("--levels", default="12,13,15,16,17,18")
    ap.add_argument("--max-parents", type=int, default=1500)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-paths")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "speed398-paths.json")
    a = ap.parse_args()
    table = json.loads(speed.REACH.read_text())["table"]
    configs = {"74": (NEW_UDENUM, 74), "base398": (BASE398_UDENUM, 398), "new398": (NEW_UDENUM, 398)}
    out = {}
    identical = True
    for L in (int(x) for x in a.levels.split(",")):
        pool = g6_lines(a.speed_work / f"sample-level-{L}.g6")
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
            cpu = {c: [0.0] * a.reps for c in configs}
            for M, gs in cells.items():
                f = a.work / f"L{L}-{cls}-{M}.g6"
                write_lines(f, gs)
                for r in range(a.reps):
                    runs = {}
                    for c in (configs if r % 2 == 0 else list(reversed(configs))):
                        binary, fs = configs[c]
                        runs[c] = run_udenum(binary, f, L + 1, M, a.work / f"L{L}-{cls}-{M}-{c}.out.g6", forbidden_set=fs)
                        cpu[c][r] += runs[c]["cpu"]
                    if r == 0:
                        identical &= not compare_runs(runs["base398"], runs["new398"])
            med = {c: statistics.median(v) for c, v in cpu.items()}
            rec[cls] = {"cpu_seconds_median": med,
                        "speedup_398": med["base398"] / med["new398"] if med["new398"] else None,
                        "new398_over_74": med["new398"] / med["74"] if med["74"] else None,
                        "base398_over_74": med["base398"] / med["74"] if med["74"] else None}
        out[str(L)] = rec
        print(f"level {L}: parent records {counts}; " + "; ".join(
            f"{cls} cpu 74 {rec[cls]['cpu_seconds_median']['74']:.3f} base398 {rec[cls]['cpu_seconds_median']['base398']:.3f} "
            f"new398 {rec[cls]['cpu_seconds_median']['new398']:.3f} (speedup {rec[cls]['speedup_398'] or float('nan'):.2f}, "
            f"new/74 {rec[cls]['new398_over_74'] or float('nan'):.2f})" for cls in classes), flush=True)
    out["outputs_identical"] = identical
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(out, indent=1) + "\n")
    print("base398 and new398 outputs identical on every class file:", identical)
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
