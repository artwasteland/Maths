#!/usr/bin/env python3
"""Run the original checker, redirecting only scratch and bytecode writes."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRATCH = Path("/tmp/gp10-checkaudit")

def load_checker():
    path = HERE.parent / "check/gp10check.py"
    spec = importlib.util.spec_from_file_location("gp10check_audit_target", path)
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    checker.SCRATCH = SCRATCH
    os.environ["TMPDIR"] = str(SCRATCH)
    os.environ["SQLITE_TMPDIR"] = str(SCRATCH)
    tempfile.tempdir = str(SCRATCH)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return checker

if __name__ == "__main__":
    raise SystemExit(load_checker().main())
