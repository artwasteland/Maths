"""Invoke unmodified sibling entry points with driver-owned scratch paths.

Real producers already launch one worker. Running their CLI main in the driver
process leaves two processes total, including that worker. Only scratch-path
globals are redirected. Search and verification functions are unchanged.
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import traceback

SCRATCH = Path('/tmp/gp10-drive/integration')
MODULES = {}


def configure():
    os.environ['SYMPY_GROUND_TYPES'] = 'python'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 15:
        os.nice(15 - current)
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = min(1_000_000_000, hard) if hard != resource.RLIM_INFINITY else 1_000_000_000
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(SCRATCH)
    os.environ['SQLITE_TMPDIR'] = str(SCRATCH)
    tempfile.tempdir = str(SCRATCH)


def load_entry(script):
    configure()
    path = Path(script).resolve()
    key = str(path)
    if key not in MODULES:
        sys.path.insert(0, str(path.parent))
        name = '_gp10_drive_' + path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        MODULES[key] = module
    module = MODULES[key]
    # These modules import Path constants by value. Redirect all copies before
    # invoking main, which is the first point that creates scratch files.
    for candidate in (module, sys.modules.get('graphs'), sys.modules.get('algebra')):
        if candidate is not None and hasattr(candidate, 'SCRATCH'):
            candidate.SCRATCH = SCRATCH
    configure()  # The checker sets TMPDIR at import time.
    return module


@contextlib.contextmanager
def captured_output(log):
    """Capture Python streams and inherited native stdout/stderr descriptors."""
    sys.stdout.flush()
    sys.stderr.flush()
    log.flush()
    saved = (os.dup(1), os.dup(2))
    try:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            yield
    finally:
        try:
            log.flush()
        finally:
            for descriptor, original in zip((1, 2), saved):
                os.dup2(original, descriptor)
                os.close(original)


def invoke(script, argv, log_path):
    """Capture the CLI's stdout, stderr, traceback and exact return status."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', buffering=1) as log:
        log.write(json.dumps({'script': str(script), 'argv': list(argv)}) + '\n')
        with captured_output(log):
            try:
                result = load_entry(script).main(list(argv))
                status = int(result or 0)
            except SystemExit as exc:
                status = 0 if exc.code is None else (exc.code if isinstance(exc.code, int) else 1)
                if not isinstance(exc.code, (int, type(None))):
                    print(exc.code, file=sys.stderr)
            except Exception:
                traceback.print_exc()
                status = 2
        log.write(json.dumps({'exit_status': status}) + '\n')
    return status


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', required=True)
    parser.add_argument('--log', required=True)
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    tail = args.args[1:] if args.args[:1] == ['--'] else args.args
    raise SystemExit(invoke(args.script, tail, args.log))
