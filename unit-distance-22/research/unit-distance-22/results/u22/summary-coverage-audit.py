#!/usr/bin/env python3
"""The summary-only coverage audit of the 48 u(22) slices (enum/verify-chain.py --summary-only).

The slices' run directories are gone; what survives of each is what its worker pushed to its branch:
research/unit-distance-22/results/u22/s<i>of48/{run-config.json, run-summary.json, reach.json}. This script
finds every copy of those three files on the origin branches (a slice re-fired on a second worker has two or
more copies), extracts each copy into OUT/<branch>/s<i>of48/, and runs verify-chain.py --summary-only on all of
them together, so the audit covers every copy and the fleet (all 48 slice indices, the shared prefix, the
slice partition of the level-13 cells). The earlier pushed versions of each run-summary.json (its git history on
the branch) go into OUT/<branch>/s<i>of48/history/, where verify-chain.py finds the parent records of the cells
the final summary lists as resumed. No level, keep, parent or certificate file is read: the verdict is a
coverage statement about the summaries, never CHAIN OK.

usage: summary-coverage-audit.py [--out DIR] [--branch-glob PATTERN]   (from the repository, after git fetch)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent.parent
PREFIX = "research/unit-distance-22/results/u22"
FILES = ("run-config.json", "run-summary.json", "reach.json")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=UD.parent.parent, capture_output=True, text=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "u22-summary-coverage-audit")
    ap.add_argument("--branch-glob", default="origin/claude/reaching-noether-cloud-u22-w*")
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    a.out.mkdir(parents=True)
    branches = [b.strip() for b in git("branch", "-r").splitlines() if "->" not in b]
    branches = [b for b in branches if fnmatch.fnmatch(b, a.branch_glob)]
    dirs = []
    for branch in sorted(branches):
        head = git("rev-parse", branch).strip()
        paths = git("ls-tree", "-r", "--name-only", branch, "--", f"{PREFIX}/").splitlines()
        slices = sorted({int(m.group(1)) for p in paths
                         for m in [re.fullmatch(rf"{re.escape(PREFIX)}/s(\d+)of48/run-summary\.json", p)] if m})
        for i in slices:
            dest = a.out / branch.split("/")[-1] / f"s{i}of48"
            dest.mkdir(parents=True)
            for name in FILES:
                path = f"{PREFIX}/s{i}of48/{name}"
                if path in paths:
                    (dest / name).write_text(git("show", f"{branch}:{path}"))
            # the earlier pushed versions of run-summary.json (newest first; the newest commit is the final version):
            # a cell the final summary lists as resumed was made by an earlier invocation that recorded its parents
            summary_path = f"{PREFIX}/s{i}of48/run-summary.json"
            commits = git("log", "--format=%H", branch, "--", summary_path).split()[1:]
            (dest / "history").mkdir()
            for commit in commits:
                (dest / "history" / f"{commit}.json").write_text(git("show", f"{commit}:{summary_path}"))
            (dest / "history" / "INDEX.json").write_text(json.dumps({"branch": branch, "commits": commits}) + "\n")
            (dest / "SOURCE").write_text(f"{branch} {head}; {len(commits)} earlier versions of run-summary.json\n")
            dirs.append(dest)
    print(f"{len(dirs)} slice summaries from {len(branches)} branches matching {a.branch_glob}", flush=True)
    for d in dirs:
        print(f"  {d.relative_to(a.out)}: {(d / 'SOURCE').read_text().strip()}", flush=True)
    result = subprocess.run([sys.executable, str(UD / "enum" / "verify-chain.py"), "--summary-only", *map(str, dirs)])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
