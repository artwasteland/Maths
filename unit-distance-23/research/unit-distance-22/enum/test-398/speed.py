#!/usr/bin/env python3
"""(d) Speed: set 74 against set 398, per parent and in children written, at several levels.

The (22,61) tree above level 13 was generated only on cloud workers; its level files are not in
the repository.  Parents at every level are therefore produced here by SAMPLED DESCENT through the
production tree itself: start from a uniform sample of the production level-12 stage files (the
TU-pruned keep files of the local (22,61) run, identical on every worker), and at each level
  1. run udenum (set 74) for every target cell (n+1, M) of the reach table, the parent file of a
     cell being the sampled parents of the allowed source cells (L4(ii): d = M - m' >= k(n+1, M));
  2. apply the reach filter (minimum degree >= k(n+1, M)) and the filter-only TU prune (udfilter,
     set 74; "tu" removed, anything else kept; a "forbidden" verdict aborts), exactly the stage
     rules of the production run (run-config: reach root 5, prune from 12, filter only);
  3. keep a uniform sample of the result as the next level's parents.
Each graph has exactly one canonical parent, so sampling parents uniformly and keeping all their
children samples the next level uniformly (siblings are correlated, the marginals are uniform).
Level 21 is not sampled: the real 743 level-21 keep graphs of all 48 slices are used.

Measured per level L (on the same sampled level-L parents, every target cell of level L+1):
  old74   the production binary (set 74)
  new74   the new binary, set 74
  new398  the new binary, set 398, on the SAME parents
  new398f the new binary, set 398, on the 398-free parents only (what a set-398 tree processes)
each repeated (--reps, alternating) and the median CPU seconds kept; plus children written, and
the fraction f_L of the level-L sample that is 398-free (udfilter -s 398).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import sys
from pathlib import Path

from t398lib import (F398, F74, HERE, NEW_UDENUM, NEW_UDFILTER, OLD_UDENUM, SCRATCH, TU, g6_lines, g6_order_size,
                     run_udenum, sha256, write_lines)

REACH = HERE.parent / "out-22" / "dag-22-61-f12" / "reach.json"


def min_degree(line: bytes) -> int:
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
    return min(deg)


def udfilter_verdicts(lines: list[bytes], work: Path, tag: str, forbidden_set: str) -> list[str]:
    src = work / f"{tag}.in.g6"
    write_lines(src, lines)
    args = ["-s", "398", "-f", str(F398)] if forbidden_set == "398" else ["-f", str(F74)]
    with open(src, "rb") as stdin:
        p = subprocess.run(["nice", "-n", "10", str(NEW_UDFILTER), "-t", str(TU), *args], stdin=stdin,
                           capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"udfilter failed: {p.stderr.decode()}")
    out = [json.loads(x)["verdict"] for x in p.stdout.split(b"\n") if x]
    if len(out) != len(lines):
        raise SystemExit("udfilter record count mismatch")
    return out


def sources(table: dict, n: int, M: int) -> list[int]:
    """Parent edge counts m' at level n for the target cell (n+1, M), exactly as run-dag2.py's
    parent_edge_counts: the Schade window m' >= ceil(M (N-2) / N) with N = n+1, the reach bound
    M - m' >= k(N, M) (L4(ii)), and m' a reach level of order n."""
    N = n + 1
    k = table[str(N)][str(M)]
    lower = -(-M * (N - 2) // N)
    return sorted(int(m) for m in table[str(n)] if int(m) >= lower and M - int(m) >= k)


def descend(level12_dir: Path, table: dict, sizes: dict[int, int], top: int, work: Path, rng, log,
            yields: dict) -> dict:
    """Return {level: [graph6 lines]} of uniform samples of the production stage sets."""
    stage12 = []
    for m in sorted(table["12"], key=int):
        f = level12_dir / f"12-{m}.keep.g6"
        got = g6_lines(f) if f.exists() else []
        print(f"level 12 stage 12-{m}: {len(got)} graphs", file=log, flush=True)
        stage12 += got
    samples = {12: rng.sample(stage12, min(sizes.get(12, 3000), len(stage12)))}
    del stage12
    for n in range(12, top):
        parents = samples[n]
        by_m: dict[int, list[bytes]] = {}
        for g in parents:
            by_m.setdefault(g6_order_size(g)[1], []).append(g)
        children = []
        for M in sorted((int(x) for x in table[str(n + 1)])):
            src = [g for m in sources(table, n, M) for g in by_m.get(m, [])]
            if not src:
                continue
            pf = work / f"descent-{n + 1}-{M}.parents.g6"
            write_lines(pf, src)
            run_udenum(NEW_UDENUM, pf, n + 1, M, work / f"descent-{n + 1}-{M}.g6")
            k = table[str(n + 1)][str(M)]
            kids = [g for g in g6_lines(work / f"descent-{n + 1}-{M}.g6") if min_degree(g) >= k]
            children += kids
        verdicts = udfilter_verdicts(children, work, f"descent-{n + 1}-tu", "74")
        if "forbidden" in verdicts:
            raise SystemExit(f"a generated level-{n + 1} graph is not 74-free: generator bug")
        kept = [g for g, v in zip(children, verdicts) if v != "tu"]
        samples[n + 1] = kept if len(kept) <= sizes.get(n + 1, 3000) else rng.sample(kept, sizes.get(n + 1, 3000))
        yields[n] = {"sampled_parents": len(parents), "children_after_reach": len(children), "kept_after_tu": len(kept),
                     "kept_per_parent": len(kept) / len(parents) if parents else None}
        print(f"level {n + 1}: {len(children)} children of {len(parents)} sampled level-{n} parents after reach, "
              f"{len(kept)} kept after TU, sample {len(samples[n + 1])}", file=log, flush=True)
    return samples


def measure(level: int, parents: list[bytes], table: dict, reps: int, work: Path, log) -> dict:
    verd = udfilter_verdicts(parents, work, f"measure-{level}-398", "398")
    free = [g for g, v in zip(parents, verd) if v != "forbidden"]
    by_m: dict[int, list[bytes]] = {}
    for g in parents:
        by_m.setdefault(g6_order_size(g)[1], []).append(g)
    free_set = set(free)
    configs = {"old74": (OLD_UDENUM, [], F74, False), "new74": (NEW_UDENUM, [], F74, False),
               "new398": (NEW_UDENUM, ["--forbidden-set", "398"], F398, False),
               "new398f": (NEW_UDENUM, ["--forbidden-set", "398"], F398, True)}
    cpu = {c: [0.0] * reps for c in configs}
    written = {c: 0 for c in configs}
    seen = {c: 0 for c in configs}
    processed = {c: 0 for c in configs}
    targets = [M for M in sorted(int(x) for x in table[str(level + 1)])]
    for M in targets:
        src = [g for m in sources(table, level, M) for g in by_m.get(m, [])]
        if not src:
            continue
        files = {False: work / f"measure-{level}-{M}.all.g6", True: work / f"measure-{level}-{M}.free.g6"}
        write_lines(files[False], src)
        write_lines(files[True], [g for g in src if g in free_set])
        for r in range(reps):
            for c, (binary, extra, forb, only_free) in configs.items():
                st = run_udenum(binary, files[only_free], level + 1, M, work / f"measure-{level}-{M}-{c}.g6",
                                extra=extra, forbidden=forb)
                cpu[c][r] += st["cpu_seconds"]
                if r == 0:
                    written[c] += st["children_written"]
                    seen[c] += st["parents_seen"]
                    processed[c] += st["parents_processed"]
    med = {c: statistics.median(v) for c, v in cpu.items()}
    rec = {"level": level, "parents": len(parents), "parents_398_free": len(free),
           "fraction_398_free": len(free) / len(parents) if parents else None,
           "targets": targets, "cpu_seconds_median": med, "cpu_seconds_all_reps": cpu,
           "children_written": written, "parent_records_seen": seen, "parent_records_processed": processed,
           "cpu_ms_per_parent": {c: 1000 * med[c] / (len(free) if c == "new398f" else len(parents))
                                 for c in configs if (len(free) if c == "new398f" else len(parents))},
           "ratio_new398_over_new74_same_parents": med["new398"] / med["new74"] if med["new74"] else None,
           "ratio_new74_over_old74": med["new74"] / med["old74"] if med["old74"] else None}
    print(f"level {level}: {len(parents)} parents ({len(free)} 398-free); cpu s median "
          + ", ".join(f"{c} {med[c]:.3f}" for c in configs)
          + "; children " + ", ".join(f"{c} {written[c]}" for c in configs), file=log, flush=True)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--level12-dir", type=Path, required=True,
                    help="directory with the production 12-<m>.keep.g6 stage files of the (22,61) run")
    ap.add_argument("--slices", type=Path, required=True, help="results/u22 of the worker branches (s0of48..)")
    ap.add_argument("--levels", default="12,15,18,21")
    ap.add_argument("--sizes", default="12:1500,13:3000,14:3000,15:6000,16:20000,17:20000,18:20000,19:20000,20:20000",
                    help="uniform sample kept per level during the descent, LEVEL:SIZE,...")
    ap.add_argument("--measure-size", type=int, default=1500)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "speed.json")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    log = sys.stdout
    rng = random.Random(a.seed)
    table = json.loads(REACH.read_text())["table"]
    print(f"old udenum {sha256(OLD_UDENUM)}; new udenum {sha256(NEW_UDENUM)}; reach.json {sha256(REACH)}", file=log)
    levels = [int(x) for x in a.levels.split(",")]
    top = max(x for x in levels if x <= 20)
    sizes = {int(k): int(v) for k, v in (x.split(":") for x in a.sizes.split(","))}
    yields: dict = {}
    samples = descend(a.level12_dir, table, sizes, top, a.work, rng, log, yields)
    l21 = []
    for s in range(48):
        l21 += g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")
    samples[21] = l21
    results = []
    for L in levels:
        parents = samples[L]
        if len(parents) > a.measure_size:
            parents = rng.sample(parents, a.measure_size)
        results.append(measure(L, parents, table, a.reps, a.work, log))
    summary = {"old_udenum": sha256(OLD_UDENUM), "new_udenum": sha256(NEW_UDENUM), "seed": a.seed,
               "sizes_requested": sizes, "descent_yields": yields,
               "sample_sizes": {L: len(v) for L, v in samples.items()}, "levels": results}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    for L, v in samples.items():
        write_lines(a.work / f"sample-level-{L}.g6", v)
    print("done", file=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
