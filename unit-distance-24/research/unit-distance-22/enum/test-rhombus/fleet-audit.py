#!/usr/bin/env python3
"""The summary-only coverage audit of a running fleet's pushed results (read-only), with the fleet pinned.

Finds every slice result directory under ROOT (default: the extracted pushed results of the (23,65) fleet,
<scratchpad>/fleet/results/<worker>/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s<i>of1920) and runs
enum/verify-chain.py --summary-only on all of them together, pinned to target (23,65), seed level 10, slice level 12,
1920 slices, with hashes.json and the G4 replays required. Nothing under ROOT is written. Missing slices fail by
design while the fleet runs; the question is what ELSE fails.

usage: fleet-audit.py [--root DIR] [--glob PATTERN]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent.parent
DEFAULT_ROOT = Path("<scratch>/scratchpad/fleet/results")
DEFAULT_GLOB = "*/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s*of1920"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--glob", default=DEFAULT_GLOB)
    a = ap.parse_args()
    dirs = sorted(p for p in a.root.glob(a.glob) if (p / "run-summary.json").is_file())
    workers = sorted({p.relative_to(a.root).parts[0] for p in dirs})
    print(f"{len(dirs)} slice result directories from {len(workers)} workers under {a.root}", flush=True)
    cmd = [sys.executable, str(UD / "enum" / "verify-chain.py"), "--summary-only", "--expect-target", "23", "65",
           "--expect-seed", "10", "--expect-slices", "12", "1920", "--require-hashes", "--require-g4", *map(str, dirs)]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
