#!/usr/bin/env python3
"""Thin stdin/stdout wrapper for the C filter."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
args = [str(HERE / "udfilter"), "-f", str(HERE.parent / "data/forbidden-74.json"),
        "-t", str(HERE.parent / "data/tu-gadgets.json")]
args.extend(sys.argv[1:])
raise SystemExit(subprocess.run(args, stdin=sys.stdin, stdout=sys.stdout,
                                stderr=sys.stderr).returncode)
