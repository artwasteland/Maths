#!/usr/bin/env python3
"""(d) Speed of the optimized Mode 398, with REPORT-398's methodology and parents.

The parents are exactly those speed.py measured (its work directory: measure-L-M.all.g6, the
sampled level-L parents of every target cell (L+1, M), and measure-L-M.free.g6, their 398-free
part).  Per level, every configuration runs over all target cells; --reps repetitions alternate
between configurations and the median of the per-level CPU sums is kept.

  old74    the u(22) production binary (test-398/old/enum/udenum), set 74, all parents
  new74    the new enum/udenum, set 74, all parents
  base398  the CURRENT Mode 398 (test-398/base398/udenum), set 398, all parents   ("398 same")
  base398f the same on the 398-free parents only                                   ("398 free")
  new398   the new enum/udenum, set 398, all parents
  new398f  the same on the 398-free parents only

Ratios per level: speedup base398f/new398f (the 398 tree's own workload) and base398/new398 (same
parents); R_L = new398f/new74 as in REPORT-398 5 (the 398 tree's generator cost at level L relative
to the 74 tree's), next to the old R_L = base398f/new74.  Children written are recorded for every
configuration, and every run's output is compared byte for byte with base398's (a speed run is not
an identity proof, but a difference here would be a failure).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from speed398lib import (BASE398_SHA256, BASE398_UDENUM, NEW_UDENUM, OLD74_UDENUM, PRODUCTION_UDENUM_SHA256, SCRATCH,
                         compare_runs, g6_lines, run_udenum, sha256)

CONFIGS = {"old74": (OLD74_UDENUM, 74, "all"), "new74": (NEW_UDENUM, 74, "all"),
           "base398": (BASE398_UDENUM, 398, "all"), "base398f": (BASE398_UDENUM, 398, "free"),
           "new398": (NEW_UDENUM, 398, "all"), "new398f": (NEW_UDENUM, 398, "free")}


def level_files(speed_work: Path, L: int) -> list[tuple[int, Path, Path]]:
    out = []
    for f in speed_work.glob(f"measure-{L}-*.all.g6"):
        M = int(f.name.split("-")[2].split(".")[0])
        out.append((M, f, f.with_name(f"measure-{L}-{M}.free.g6")))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed-work", type=Path, required=True, help="speed.py's work directory")
    ap.add_argument("--levels", default="12,13,14,15,16,17,18,19,21")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-speed")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-speed.json")
    a = ap.parse_args()
    if sha256(BASE398_UDENUM) != BASE398_SHA256 or sha256(OLD74_UDENUM) != PRODUCTION_UDENUM_SHA256:
        print("reference binaries are not the pinned ones")
        return 2
    print(f"old74 {PRODUCTION_UDENUM_SHA256[:16]}, base398 {BASE398_SHA256[:16]}, new {sha256(NEW_UDENUM)[:16]}",
          flush=True)
    results = []
    all_same = True
    for L in (int(x) for x in a.levels.split(",")):
        files = level_files(a.speed_work, L)
        cpu = {c: [0.0] * a.reps for c in CONFIGS}
        children = {c: 0 for c in CONFIGS}
        parents = {"all": sum(len(g6_lines(f)) for _, f, _ in files),
                   "free": sum(len(g6_lines(g)) for _, _, g in files)}
        identical = True
        for r in range(a.reps):
            order = list(CONFIGS) if r % 2 == 0 else list(reversed(CONFIGS))
            for M, fall, ffree in files:
                runs = {}
                for c in order:
                    binary, fs, which = CONFIGS[c]
                    out = a.work / f"L{L}" / f"{M}-{c}.g6"
                    runs[c] = run_udenum(binary, fall if which == "all" else ffree, L + 1, M, out, forbidden_set=fs)
                    if runs[c]["returncode"] != 0:
                        raise SystemExit(f"{c} failed at level {L} cell {M}: {runs[c]['stderr_tail']}")
                    cpu[c][r] += runs[c]["cpu"]
                    if r == 0:
                        children[c] += runs[c]["stats"]["children_written"]
                if r == 0:
                    identical &= not compare_runs(runs["base398"], runs["new398"])
                    identical &= not compare_runs(runs["base398f"], runs["new398f"])
                    identical &= not compare_runs(runs["old74"], runs["new74"])
        med = {c: statistics.median(v) for c, v in cpu.items()}

        def ratio(x, y):
            return med[x] / med[y] if med[y] > 0 else None
        rec = {"level": L, "cells": [M for M, _, _ in files], "parents_all": parents["all"], "parents_free": parents["free"],
               "cpu_median": med, "cpu_all_reps": cpu, "children": children, "outputs_identical": identical,
               "ms_per_parent": {c: 1000 * med[c] / parents[CONFIGS[c][2]] for c in CONFIGS if parents[CONFIGS[c][2]]},
               "speedup_free": ratio("base398f", "new398f"), "speedup_same": ratio("base398", "new398"),
               "R_new": ratio("new398f", "new74"), "R_old": ratio("base398f", "new74"),
               "same_over_74_new": ratio("new398", "new74"), "same_over_74_old": ratio("base398", "new74")}
        all_same &= identical
        results.append(rec)
        f = lambda v: f"{v:6.2f}" if v is not None else "   n/a"
        print(f"L{L:2d} parents {parents['all']:5d} (free {parents['free']:4d}) cpu s: " +
              " ".join(f"{c} {med[c]:7.3f}" for c in CONFIGS) +
              f" | speedup free {f(rec['speedup_free'])} same {f(rec['speedup_same'])} | R_L old {f(rec['R_old'])} "
              f"new {f(rec['R_new'])} | identical {identical}", flush=True)
    summary = {"binaries": {c: str(v[0]) for c, v in CONFIGS.items()}, "new_sha256": sha256(NEW_UDENUM),
               "reps": a.reps, "levels": results, "outputs_identical": all_same}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print("outputs identical at every level:", all_same)
    return 0 if all_same else 1


if __name__ == "__main__":
    sys.exit(main())
