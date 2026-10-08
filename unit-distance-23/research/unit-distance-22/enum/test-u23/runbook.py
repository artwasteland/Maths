#!/usr/bin/env python3
"""Local test of coordination/cloud-workers/u23-slice.sh on a small target (no cloud worker).

The runbook runs exactly as on a worker except for the environment overrides it documents:
target (17,43) with root k 2 (Schade's bound there), 3 slices at level 13, JOBS=1, no toolchain
step, no commit or push, run and result directories in scratch, U23_CLEANUP=0 (R2, R3 and R5 read
the run directories; runbook-g4.py tests the cleanup) and U23_MIN_FREE_GB=0 (a local disk). The u-bar override and its
justification are left at their production values (--ubar 22=60 is recorded in reach.json and
cannot change a (17,43) tree, which never reads u-bar(22)), so the quoting of the production
command line is exercised too.

PASS iff
  R1 the runbook exits 0 and runs every self-check; slices 1 and 2 hard-link levels <= 13 from
     slice 0; every run-config.json says set 398, stage verification, the override, the slice;
  R2 levels <= 13 are byte-identical across the three slices (their hashes.json) and equal the
     unsliced Mode 398 run of e2e.py (new398) file by file;
  R3 at every level >= 14 and every stage, the three slices are disjoint, each is a subsequence
     of the unsliced file, and their union is the unsliced file: the slices partition the tree;
  R4 the union of the three (17,43) keep files is new398's keep file (as sets), which holds all
     of AMP's known (17,43) graphs;
  R5 verify-chain.py --check accepts slice 0 whole (CHAIN OK) and slices 1 and 2 from level 14 (CHAIN PARTIAL: their
     levels <= 13 are hard links of slice 0's, verified there);
  R6 the result directory holds small files only (none over 4 MB);
  R7 red: a slice index equal to the count, a count of 0, and a non-numeric index make the
     runbook exit 2 before doing anything.

usage: runbook.py --e2e-dir <U23_SCRATCH>/e2e-17-43
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from u23lib import KNOWN, REPO, SCRATCH, UD, canonical, decode_g6, g6_lines, log

RUNBOOK = REPO / "coordination" / "cloud-workers" / "u23-slice.sh"
TN, TM, COUNT = 17, 43, 3
problems: list[str] = []
LEVEL_RE = re.compile(r"^(\d+)-(\d+)(\.reach|\.keep|\.UNKNOWN)?\.g6$|^(\d+)-(\d+)\.certs\.jsonl$")


def env(work: Path) -> dict[str, str]:
    e = dict(os.environ)
    e.update({"U23_TARGET_N": str(TN), "U23_TARGET_M": str(TM), "U23_ROOT_K": "2",
              "U23_PRUNE_FROM": "12", "U23_SLICE_LEVEL": "13", "U23_OUT": str(work / "out"),
              "U23_RES": str(work / "res"), "U23_PUSH": "0", "U23_TOOLCHAIN": "0", "JOBS": "1",
              "PY": sys.executable, "U23_CLEANUP": "0", "U23_MIN_FREE_GB": "0"})
    e.pop("U23_UBAR", None)
    e.pop("U23_UBAR_JUSTIFICATION", None)
    return e


def level_name(name: str) -> tuple[int, int] | None:
    mm = LEVEL_RE.match(name)
    if not mm:
        return None
    return int(mm.group(1) or mm.group(4)), int(mm.group(2) or mm.group(5))


def records(path: Path) -> list[bytes]:
    return [x for x in path.read_bytes().split(b"\n") if x]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e2e-dir", type=Path, required=True)
    ap.add_argument("--skip-run", action="store_true")
    a = ap.parse_args()
    unsliced = a.e2e_dir / "new398"
    work = SCRATCH / "runbook-17-43"
    if not a.skip_run:
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        # R7 first: argument errors must stop the runbook before anything happens
        for label, argv in (("index = count", [str(COUNT), str(COUNT)]), ("count 0", ["0", "0"]),
                            ("index x", [str(COUNT), "x"])):
            p = subprocess.run(["bash", str(RUNBOOK), *argv], env=env(work / "red"), capture_output=True,
                               text=True, cwd=REPO)
            made = (work / "red").exists()
            log(f"R7 {label}: exit {p.returncode}: {p.stderr.strip()[:100]}; anything written: {made}")
            if p.returncode != 2 or made:
                problems.append(f"R7 {label}: exit {p.returncode}, wrote files: {made}")
        with (work / "runbook.log").open("w") as logf:
            p = subprocess.run(["nice", "-n", "15", "bash", str(RUNBOOK), str(COUNT), "0", "1", "2"],
                               env=env(work), stdout=logf, stderr=subprocess.STDOUT, cwd=REPO)
        text = (work / "runbook.log").read_text()
        log(f"R1 runbook exit {p.returncode}; log:\n" + "\n".join("    " + x for x in text.splitlines()))
        if p.returncode != 0:
            problems.append(f"R1: runbook exit {p.returncode}")
        for s in (1, 2):
            if f"slice s{s}of{COUNT}: levels <= 13 hard-linked from" not in text:
                problems.append(f"R1: slice {s} did not hard-link the prefix")
    text = (work / "runbook.log").read_text()
    if "pins and self-checks passed" not in text:
        problems.append("R1: the self-checks did not run")
    out = work / "out"
    dirs = {s: out / f"dag-{TN}-{TM}-s{s}of{COUNT}" for s in range(COUNT)}
    for s, d in dirs.items():
        config = json.loads((d / "run-config.json").read_text())
        reach = json.loads((d / "reach.json").read_text())
        want = {"forbidden_set": 398, "verify_stages": True, "slice": [13, s, COUNT],
                "ubar_override": {"22": {"builtin": 62, "value": 60}}}
        bad = {k: config.get(k) for k, v in want.items() if config.get(k) != v}
        if bad or reach.get("ubar_override") != want["ubar_override"] or "RESULT-u22.md" not in reach.get(
                "ubar_justification", ""):
            problems.append(f"R1: slice {s} run-config/reach.json do not record the production options: {bad}")
    # R2 prefix identical across slices and equal to the unsliced run
    hashes = [json.loads((work / "res" / f"{TN}-{TM}" / f"s{s}of{COUNT}" / "hashes.json").read_text())["files"]
              for s in range(COUNT)]
    prefix = {k: v for k, v in hashes[0].items() if int(k.split("-")[0]) <= 13}
    same = all({k: v for k, v in h.items() if int(k.split("-")[0]) <= 13} == prefix for h in hashes)
    names = sorted(name for name in os.listdir(dirs[0]) if level_name(name) and level_name(name)[0] <= 13)
    differ = [name for name in names if (dirs[0] / name).read_bytes() != (unsliced / name).read_bytes()]
    log(f"R2 levels <= 13: {len(prefix)} .g6 files hashed, identical in all {COUNT} slices: {same}; "
        f"{len(names)} level files of slice 0 equal to the unsliced run: {len(names) - len(differ)}")
    if not same or differ or not names:
        problems.append(f"R2: prefix differs across slices ({same}) or from the unsliced run: {differ[:5]}")
    # R3 partition above the slice level
    upper = sorted({name for name in os.listdir(unsliced) if level_name(name) and level_name(name)[0] >= 14})
    part_ok = 0
    for name in upper:
        whole = records(unsliced / name)
        if name.endswith(".certs.jsonl"):
            key = [json.loads(x)["g6"] for x in whole]
        else:
            key = whole
        position = {k: i for i, k in enumerate(key)}
        pieces = []
        for s in range(COUNT):
            p = dirs[s] / name
            got = records(p) if p.is_file() else []
            gkey = [json.loads(x)["g6"] for x in got] if name.endswith(".certs.jsonl") else got
            idx = [position.get(k, -1) for k in gkey]
            if -1 in idx or idx != sorted(idx) or any(whole[i] != line for i, line in zip(idx, got)):
                problems.append(f"R3 {name}: slice {s} is not a subsequence of the unsliced file")
            pieces.append(set(idx))
        union = set().union(*pieces)
        disjoint = sum(len(x) for x in pieces) == len(union)
        if not disjoint or union != set(range(len(whole))):
            problems.append(f"R3 {name}: slices not a partition ({sum(len(x) for x in pieces)} records, "
                            f"{len(union)} distinct, {len(whole)} unsliced)")
        else:
            part_ok += 1
    log(f"R3 levels >= 14: {part_ok} of {len(upper)} files partitioned exactly by the {COUNT} slices "
        f"(disjoint, order-preserving, union = unsliced)")
    # R4 the top keep
    top = f"{TN}-{TM}.keep.g6"
    union = set()
    for s in range(COUNT):
        union |= set(records(dirs[s] / top))
    whole = set(records(unsliced / top))
    known = canonical([x for x in g6_lines(KNOWN) if (decode_g6(x)[0], len(decode_g6(x)[1])) == (TN, TM)])
    present = sum(1 for x in known if x in union)
    log(f"R4 {top}: union over slices {len(union)} graphs, unsliced {len(whole)}, equal {union == whole}; "
        f"AMP's known ({TN},{TM}) graphs present {present}/{len(known)}")
    if union != whole or present != len(known):
        problems.append("R4: the top keep union differs from the unsliced run or misses a known graph")
    # R5 the stranger's check
    for s in range(COUNT):
        cmd = [sys.executable, str(UD / "enum" / "verify-chain.py"), str(dirs[s]), "--check"]
        if s:
            cmd += ["--from-n", "14"]
        p = subprocess.run(["nice", "-n", "15", *cmd], capture_output=True, text=True)
        lines = p.stdout.strip().splitlines()
        log(f"R5 verify-chain slice {s}{' --from-n 14' if s else ''}: exit {p.returncode}: "
            f"{lines[-1] if lines else p.stderr.strip()}; {lines[0][:200] if lines else ''}")
        # slice 0 whole is exhaustive (CHAIN OK); slices 1 and 2 from level 14 are an explicit PARTIAL (exit 3)
        ok = (p.returncode == 0 and lines and lines[-1] == "CHAIN OK") if not s else \
            (p.returncode == 3 and lines and lines[-1].startswith("CHAIN PARTIAL") and "levels below 14" in lines[-1])
        if not ok:
            problems.append(f"R5 slice {s}: {[x for x in lines if x.startswith('PROBLEM')][:3]} {lines[-1] if lines else ''}")
    # R6 small result files only
    res = work / "res"
    files = [p for p in res.rglob("*") if p.is_file()]
    big = [p for p in files if p.stat().st_size >= 4_000_000]
    total = sum(p.stat().st_size for p in files)
    log(f"R6 results: {len(files)} files, {total / 1e3:.0f} kB in all, largest "
        f"{max((p.stat().st_size for p in files), default=0) / 1e3:.0f} kB; per slice: "
        f"{sorted(p.name for p in (res / f'{TN}-{TM}' / 's0of3').iterdir())}; per worker: "
        f"{sorted(p.name for p in res.iterdir() if p.is_file())}")
    if big:
        problems.append(f"R6: large result files {big}")
    for p in problems:
        log("PROBLEM:", p)
    log("RUNBOOK", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
