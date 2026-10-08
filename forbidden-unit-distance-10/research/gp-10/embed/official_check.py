#!/usr/bin/env python3
"""Run the unchanged official checker, redirecting only forbidden scratch paths."""
import importlib.util
import os
from pathlib import Path
import sys
from msolve_exact import limits, sha


def main():
    limits()
    path = Path(__file__).resolve().parent.parent / 'check/gp10check.py'
    before = sha(path.read_bytes())
    spec = importlib.util.spec_from_file_location('gp10_official_check', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    scratch = Path('/tmp/gp10-embed/official-check')
    module.SCRATCH = scratch
    os.environ['TMPDIR'] = str(scratch)
    os.environ['SQLITE_TMPDIR'] = str(scratch)
    # tempfile can cache its default, although this checker passes dir explicitly.
    module.tempfile.tempdir = str(scratch)
    result = module.main(sys.argv[1:])
    if sha(path.read_bytes()) != before: raise RuntimeError('checker_source_changed_during_run')
    return result


if __name__ == '__main__': sys.exit(main())
