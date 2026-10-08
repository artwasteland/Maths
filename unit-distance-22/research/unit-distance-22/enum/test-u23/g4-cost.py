#!/usr/bin/env python3
"""What the G4 replay (enum2/replay-398.py, run by coordination/cloud-workers/u23-slice.sh after every slice) costs on
a fleet slice of the (23,65) pipeline, and so which fraction and whole-max the runbook can afford.

1. measure: replay-398.py's own per-parent pool task (enum2_children with the parent check) and udenum (the fast
   Mode-398 binary, as production runs it) on the same REAL (23,65) parents. Parents: a sampled descent through the
   (23,65) Mode-398 tree (--descent DIR holding d-<n>-<m>.parents.g6, the TU-kept, reach-filtered parents of cell
   (n, m), levels 13-19; the supervisor's rh65/w3), filtered by filter/udtriangle to its "pass" graphs (the fleet runs
   --triangles, so its keep files hold only those); --per-cell parents per cell, seeded. Level 20: the (19,45)
   children of the descent's (19,45) parents grown with udenum, kept as the fleet keeps them (minimum degree >= 4,
   udfilter -s 74 pass, udtriangle pass), timed as parents of (20,50) and (20,51).
2. model: per pilot slice (--slice RUN_SUMMARY:SECONDS, the slice's run-summary.json and its wall time above the
   prefix), for each fraction F and whole-max W: every production shard [a, b) of every cell above the slice level
   gets k = b - a parents if b - a <= W, else max(2, ceil(F (b - a))) (the replay's rule with --min-per-shard 2);
   cost = sum of k times the cell's measured mean (cells not measured: the level's parent-weighted mean; levels >= 20:
   the level-20 fixed cost plus 150 times the cell's own udenum core-seconds per parent in the pilot, 150 being the
   enum2/udenum ratio measured on the processed-heavy cells of levels 17-19), divided by 4 cores and by the speed of
   this machine against the worker (the median, over cells with at least 1,000 parents, of udenum's core-seconds per
   parent here on the descent's parents over the worker's on the pilot cell), plus 12 to 20 seconds outside enum2
   (the level-12 stage checks: keep+slice re-derivation over ~1.9M keep and ~4.2M reach records, about 5.5 s,
   measured at quarter scale; parent loading, children indexing, pool start-up and drain at each cell).

usage: g4-cost.py measure --descent DIR --out COST.json [--per-cell 40]
       g4-cost.py model --cost COST.json --slice RUN_SUMMARY:SECONDS [--slice ...]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from u23lib import F398, UD, UDENUM, UDFILTER

REPLAY = UD / "enum2" / "replay-398.py"
UDTRIANGLE = UD / "filter" / "udtriangle"
FIXED = (12.0, 20.0)  # seconds per slice outside enum2 (see the docstring)
RATIO = 150.0
LEVEL20_FIXED = {20: 0.11, 21: 0.13, 22: 0.15, 23: 0.2}


def load_replay():
    spec = importlib.util.spec_from_file_location("replay398", REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verdicts(cmd: list[str], codes: list[str]) -> list[str]:
    p = subprocess.run(["nice", "-n", "10", *cmd], input="".join(c + "\n" for c in codes), capture_output=True,
                       text=True, check=True)
    out = [json.loads(x)["verdict"] for x in p.stdout.splitlines()]
    assert len(out) == len(codes)
    return out


def udenum(parents: list[str], n: int, m: int, work: Path, tag: str) -> tuple[dict, list[str]]:
    pf, out = work / f"{tag}.parents.g6", work / f"{tag}.g6"
    pf.write_text("".join(c + "\n" for c in parents))
    p = subprocess.run(["nice", "-n", "10", str(UDENUM), "--parents", str(pf), "--forbidden", str(F398),
                        "--forbidden-set", "398", "--n", str(n), "--m", str(m), "--output", str(out),
                        "--manifest", str(work / f"{tag}.manifest.json"), "--shard-id", tag, "--overwrite"],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stderr.strip().splitlines()[-1]), [x for x in out.read_text().split("\n") if x]


def time_cell(replay, parents: list[str], n: int, m: int, work: Path, tag: str) -> dict:
    times, processed, kids = [], 0, 0
    for c in parents:
        t0 = time.process_time()
        got = replay.enum2_children(c, m, "398", True)
        times.append(time.process_time() - t0)
        processed += got["processed"]
        kids += len(set(got["kids"]))
    stats, _ = udenum(parents, n, m, work, tag) if parents else ({}, [])
    row = {"cell": f"{n}-{m}", "timed": len(parents), "processed": processed, "children": kids,
           "enum2_mean": sum(times) / len(times) if times else None, "enum2_max": max(times) if times else None,
           "udenum_per_parent": stats.get("cpu_seconds", 0) / len(parents) if parents else None,
           "udenum_children": stats.get("children_written")}
    if row["enum2_mean"] and row["udenum_per_parent"]:
        row["ratio"] = row["enum2_mean"] / max(row["udenum_per_parent"], 1e-9)
    return row


def measure(a) -> int:
    replay = load_replay()
    work = a.out.parent / "g4-cost-work"
    work.mkdir(parents=True, exist_ok=True)
    rows = {}
    files = sorted(a.descent.glob("d-*-*.parents.g6"), key=lambda p: tuple(int(x) for x in p.name.split(".")[0].split("-")[1:]))
    for path in files:
        n, m = (int(x) for x in path.name.split(".")[0].split("-")[1:])
        codes = [x for x in path.read_text().split("\n") if x]
        pool = random.Random(f"{a.seed}/{n}-{m}").sample(codes, min(len(codes), 4 * a.per_cell))
        tri = verdicts([str(UDTRIANGLE)], pool)
        chosen = [c for c, v in zip(pool, tri) if v == "pass"][:a.per_cell]
        row = time_cell(replay, chosen, n, m, work, f"{n}-{m}")
        row.update({"parents_in_file": len(codes), "drawn": len(pool), "tri_pass": tri.count("pass")})
        rows[row["cell"]] = row
        print(json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in row.items()}), flush=True)
    base = a.descent / "d-19-45.parents.g6"
    if base.is_file():     # level 20: the kept (19,45) graphs as parents
        _, kids = udenum([x for x in base.read_text().split("\n") if x], 19, 45, work, "l19-45")
        reach = [c for c in kids if replay.min_degree(c) >= 4]
        tu = verdicts([str(UDFILTER), "-s", "74", "-f", str(UD / "data" / "forbidden-74.json"), "-t",
                       str(UD / "data" / "tu-gadgets.json")], reach)
        surv = [c for c, v in zip(reach, tu) if v == "pass"]
        keep = [c for c, v in zip(surv, verdicts([str(UDTRIANGLE)], surv)) if v == "pass"]
        chosen = random.Random(f"{a.seed}/l20").sample(keep, min(len(keep), a.per_cell))
        for m in (50, 51):
            row = time_cell(replay, chosen, 20, m, work, f"20-{m}")
            row.update({"parents_in_file": len(keep), "drawn": len(kids), "tri_pass": len(keep)})
            rows[row["cell"]] = row
            print(json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in row.items()}), flush=True)
    a.out.write_text(json.dumps(rows, indent=1) + "\n")
    return 0


def model(a) -> int:
    costs = {k: v for k, v in json.loads(a.cost.read_text()).items() if v.get("enum2_mean") and v.get("timed", 0) >= 5}
    by_level = defaultdict(list)
    for k, v in costs.items():
        by_level[int(k.split("-")[0])].append(v)
    level_mean = {n: sum(v["enum2_mean"] * v["parents_in_file"] for v in vs) / sum(v["parents_in_file"] for v in vs)
                  for n, vs in by_level.items()}
    print(f"{'cell':>6} {'timed':>5} {'processed':>9} {'enum2 s/parent':>14} {'udenum s/parent':>15} {'ratio':>7}")
    for k in sorted(costs, key=lambda x: tuple(int(y) for y in x.split("-"))):
        v = costs[k]
        print(f"{k:>6} {v['timed']:>5} {v['processed']:>9} {v['enum2_mean']:>14.4f} {v['udenum_per_parent']:>15.5f} "
              f"{v.get('ratio', 0):>7.0f}")
    for spec in a.slice:
        path, _, seconds = spec.rpartition(":")
        summary, wall = json.loads(Path(path).read_text()), float(seconds)
        sl = summary["slice"][0]
        ud_pp = {(e["n"], e["m"]): sum(s.get("wall_seconds", 0) or 0 for s in e["shards"]) / e["parents"]
                 for e in summary["levels"] if e.get("shards") and e.get("parents")}

        def t(n: int, m: int) -> float:
            if f"{n}-{m}" in costs:
                return costs[f"{n}-{m}"]["enum2_mean"]
            if n in LEVEL20_FIXED:
                return LEVEL20_FIXED[n] + RATIO * ud_pp.get((n, m), 0.0)
            return level_mean[n]

        cells = [e for e in summary["levels"] if e["n"] > sl and e.get("shards")]
        speed = sorted(costs[f"{e['n']}-{e['m']}"]["udenum_per_parent"] / ud_pp[(e["n"], e["m"])] for e in cells
                       if e["parents"] >= 1000 and f"{e['n']}-{e['m']}" in costs and ud_pp.get((e["n"], e["m"])))
        slow = speed[len(speed) // 2] if speed else 1.0
        print(f"\n{path}: slice {summary['slice']}, {len(cells)} cells above level {sl}, "
              f"{sum(e['parents'] for e in cells)} parents, {wall:.0f} s above the prefix; this machine is {slow:.2f}x "
              f"the worker's udenum time per parent (median of {len(speed)} cells: "
              f"{', '.join(f'{x:.2f}' for x in speed)})")
        for W in (400, 200, 100, 50):
            for F in (0.005, 0.003, 0.002, 0.001):
                sampled, cost, per_level = 0, 0.0, defaultdict(float)
                for e in cells:
                    for s in e["shards"]:
                        size = s["range"][1] - s["range"][0]
                        if size <= 0:
                            continue
                        k = size if size <= W else min(size, max(2, math.ceil(F * size)))
                        sampled += k
                        cost += k * t(e["n"], e["m"])
                        per_level[e["n"]] += k * t(e["n"], e["m"])
                lo, hi = cost / 4 / slow + FIXED[0], cost / 4 + FIXED[1]
                top = sorted(per_level.items(), key=lambda kv: -kv[1])[:3]
                print(f"  whole-max {W:>3} fraction {F:<6} sampled {sampled:>5}  enum2 {cost:>6.0f} core-s here  replay "
                      f"{lo:>4.0f}-{hi:<4.0f} s = {100 * lo / wall:>4.1f}-{100 * hi / wall:<4.1f}% of the slice   "
                      f"top levels (core-s) {[(n, round(c)) for n, c in top]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--descent", type=Path, required=True)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--per-cell", type=int, default=40)
    m.add_argument("--seed", default="20260926")
    o = sub.add_parser("model")
    o.add_argument("--cost", type=Path, required=True)
    o.add_argument("--slice", action="append", required=True)
    a = ap.parse_args()
    return measure(a) if a.cmd == "measure" else model(a)


if __name__ == "__main__":
    sys.exit(main())
