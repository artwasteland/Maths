#!/usr/bin/env python3
"""Thin stdin/stdout wrapper for the C filter.

Forbidden set 74 (default) reads data/forbidden-74.json; `-s 398` or `--forbidden-set 398`
reads data/forbidden-398.json (the C filter checks its pinned sha256).  Other arguments pass
through unchanged, and a later `-f FILE` still overrides the default file.
"""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
extra = sys.argv[1:]
forbidden_set = "74"
for flag, value in zip(extra, extra[1:]):
    if flag in ("-s", "--forbidden-set"):
        forbidden_set = value
forbidden = "forbidden-398.json" if forbidden_set == "398" else "forbidden-74.json"
args = [str(HERE / "udfilter"), "-f", str(HERE.parent / "data" / forbidden),
        "-t", str(HERE.parent / "data/tu-gadgets.json")]
args.extend(extra)
raise SystemExit(subprocess.run(args, stdin=sys.stdin, stdout=sys.stdout,
                                stderr=sys.stderr).returncode)
