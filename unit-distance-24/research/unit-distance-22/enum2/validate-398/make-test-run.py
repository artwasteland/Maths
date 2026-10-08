#!/usr/bin/env python3
"""A small Mode-398 run in enum/run-dag2.py's own layout, to test replay-398.py.

enum/run-dag2.py (owned by another agent, not modified here) had no --forbidden-set yet
when this was written, and udenum refuses the 398 file in its default Mode 74.  So this
script copies run-dag2.py into the scratch directory and changes exactly one thing: every
udenum command it builds gets "--forbidden-set 398" appended (both the seed filter and the
level shards).  The patched copy's diff is printed and recorded; everything else (reach
table, windows, shards, slicing, manifests, stage files) is run-dag2.py's own code.

  make-test-run.py --out DIR --target-n N --target-m M [--slice-level L --slice-index I
                   --slice-count C] [--shard-size S] [--verify-parents]
"""
from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from pathlib import Path

from v398lib import DATA, SCRATCH, UD, UDENUM, UDENUM_SHA256, sha256

SRC = UD / "enum" / "run-dag2.py"
NEEDLES = [
    ('        *software_args(args, Path(__file__).resolve(), args.geng),\n    ]\n',
     '        *software_args(args, Path(__file__).resolve(), args.geng),\n    ]\n'
     '    command += ["--forbidden-set", "398"]  # make-test-run.py: Mode 398\n'),
    ('            *software_args(args, Path(__file__).resolve()),\n        ]\n',
     '            *software_args(args, Path(__file__).resolve()),\n        ]\n'
     '        command += ["--forbidden-set", "398"]  # make-test-run.py: Mode 398\n'),
]


def patched_copy(dest: Path) -> tuple[Path, str]:
    text = SRC.read_text()
    new = text
    for old, repl in NEEDLES:
        if new.count(old) != 1:
            raise SystemExit(f"run-dag2.py changed: cannot find the udenum command block {old!r}")
        new = new.replace(old, repl)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new)
    diff = "".join(difflib.unified_diff(text.splitlines(True), new.splitlines(True),
                                        "enum/run-dag2.py", str(dest)))
    return dest, diff


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target-n", type=int, required=True)
    ap.add_argument("--target-m", type=int, required=True)
    ap.add_argument("--shard-size", type=int, default=500)
    ap.add_argument("--slice-level", type=int)
    ap.add_argument("--slice-index", type=int)
    ap.add_argument("--slice-count", type=int)
    ap.add_argument("--verify-parents", action="store_true")
    a = ap.parse_args()
    if sha256(UDENUM) != UDENUM_SHA256:
        raise SystemExit("enum/udenum is not the pinned Mode-398 binary")
    runner, diff = patched_copy(SCRATCH / "run-dag2-398" / "run-dag2.py")
    print(diff)
    (a.out.parent / f"{a.out.name}.run-dag2.diff").parent.mkdir(parents=True, exist_ok=True)
    (a.out.parent / f"{a.out.name}.run-dag2.diff").write_text(diff)
    cmd = [sys.executable, str(runner), "--target-n", str(a.target_n), "--target-m", str(a.target_m),
           "--output-dir", str(a.out), "--reach", "--shard-size", str(a.shard_size), "--jobs", "1",
           "--udenum", str(UDENUM), "--forbidden", str(DATA / "forbidden-398.json")]
    if a.slice_level is not None:
        cmd += ["--slice-level", str(a.slice_level), "--slice-index", str(a.slice_index),
                "--slice-count", str(a.slice_count)]
    if a.verify_parents:
        cmd.append("--verify-parents")
    print(" ".join(cmd), flush=True)
    return subprocess.run(["nice", "-n", "15", *cmd]).returncode


if __name__ == "__main__":
    sys.exit(main())
