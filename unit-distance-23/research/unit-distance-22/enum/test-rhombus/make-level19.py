#!/usr/bin/env python3
"""A level-19 sample of the real (23,65) tree, for the throughput measurement (the supervisor's
descent samples stop at level 18).

Method (the supervisor's descent65.py, one level further): its level-18 sampled TU-kept graphs are
already split into the parent files of the level-19 cells, <w1>/d-19-45.parents.g6 and
d-19-46.parents.g6 (Mode 74, reach table of (23,65) with root k 5 and u-bar(22) = 60). Here udenum
(Mode 74, this tree's binary) generates those cells, the reach filter keeps minimum degree >= k(19,m),
udfilter (set 74) keeps the TU survivors, and a seeded uniform sample of at most 1500 of them is
written to samples/w1-measure-19.g6 (in the order of the survivors). The descent log reports 4803
children and 2333 kept at level 19; this script prints its own counts next to those.

usage: make-level19.py [--descent DIR]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

from rhlib import DATA, ENUM, HERE, SCRATCH, UDFILTER, g6_lines, log, write_lines

DESCENT = Path("<scratch>/scratchpad/rh65/w1")


def reach_k() -> dict:
    spec = importlib.util.spec_from_file_location("run_dag2_for_reach", ENUM / "run-dag2.py")
    rd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rd)
    ubar = dict(rd.UBAR)
    ubar[22] = 60
    return rd.reach_table(23, 65, 5, 10, ubar)


def min_degree(code: str) -> int:
    n = ord(code[0]) - 63
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    deg = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                deg[i] += 1
                deg[j] += 1
            k += 1
    return min(deg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--descent", type=Path, default=DESCENT)
    a = ap.parse_args()
    table = reach_k()
    work = SCRATCH / "level19"
    work.mkdir(parents=True, exist_ok=True)
    kids: list[str] = []
    written = 0
    for m in sorted(table[19]):
        parents = a.descent / f"d-19-{m}.parents.g6"
        if not parents.is_file():
            log(f"(19,{m}): no parent file {parents}")
            continue
        out = work / f"19-{m}.g6"
        cmd = ["nice", "-n", "10", str(ENUM / "udenum"), "--parents", str(parents), "--forbidden",
               str(DATA / "forbidden-74.json"), "--n", "19", "--m", str(m), "--output", str(out),
               "--manifest", str(work / f"19-{m}.manifest.json"), "--shard-id", f"l19-{m}", "--overwrite"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit(f"udenum failed: {p.stderr[-300:]}")
        stats = json.loads(p.stderr.strip().splitlines()[-1])
        children = g6_lines(out)
        written += len(children)
        k = table[19][m]
        reach = [c for c in children if min_degree(c) >= k]
        log(f"(19,{m}): {len(g6_lines(parents))} parents, {len(children)} children, k = {k}: {len(reach)} after reach; "
            f"udenum cpu {stats.get('cpu_seconds')}")
        kids += reach
    p = subprocess.run(["nice", "-n", "10", str(UDFILTER), "-f", str(DATA / "forbidden-74.json"), "-t",
                        str(DATA / "tu-gadgets.json")], input="".join(c + "\n" for c in kids),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"udfilter failed: {p.stderr[-300:]}")
    verdicts = [json.loads(x)["verdict"] for x in p.stdout.splitlines()]
    if "forbidden" in verdicts or len(verdicts) != len(kids):
        raise SystemExit("udfilter output is not a tu/pass verdict per child")
    kept = [c for c, v in zip(kids, verdicts) if v == "pass"]
    sample = kept if len(kept) <= 1500 else [kept[i] for i in sorted(random.Random(20260926).sample(range(len(kept)), 1500))]
    write_lines(HERE / "samples" / "w1-measure-19.g6", sample)
    log(f"level 19: {written} children, {len(kids)} after reach, {len(kept)} TU-kept (descent log: 4803 written, "
        f"2333 kept); sample of {len(sample)} written to samples/w1-measure-19.g6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
