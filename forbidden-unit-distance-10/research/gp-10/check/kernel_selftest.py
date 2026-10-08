#!/usr/bin/env python3
"""Run the trusted self-test with only environment and harness adaptations."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import types

os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2] / "unit-distance-22" / "check"
SCRATCH = Path("/tmp/gp10-check/kernel-selftest")
SCRATCH.mkdir(parents=True, exist_ok=True)
source = (ROOT / "selftest.py").read_text()
assert source.count('scratch_root = HERE / "scratch"') == 1
source = source.replace('scratch_root = HERE / "scratch"', 'scratch_root = Path("/tmp/gp10-check/kernel-selftest")')
namespace = {"__file__": str(ROOT / "selftest.py"), "__name__": "trusted_selftest_adapted"}
exec(compile(source, str(ROOT / "selftest.py"), "exec"), namespace)
namespace["PYTHON"] = Path(sys.executable)
kernel = runpy.run_path(str(ROOT / "udcheck.py"), run_name="trusted_kernel_adapted")


def run(args, **kwargs):
    # Run only Python checker invocations in-process; nauty and zstd remain children.
    if len(args) >= 2 and str(args[1]) == str(ROOT / "udcheck.py"):
        assert str(args[0]) == sys.executable
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            code = kernel["main"](list(args[2:]))
        return subprocess.CompletedProcess(args, code, capture.getvalue())
    return subprocess.run(args, **kwargs)

namespace["subprocess"] = types.SimpleNamespace(run=run, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT)
if __name__ == "__main__":
    print("HARNESS Python=" + sys.executable + " SYMPY_GROUND_TYPES=" + os.environ["SYMPY_GROUND_TYPES"])
    print("HARNESS checker calls in-process; scratch=/tmp/gp10-check/kernel-selftest")
    sys.exit(namespace["main"]())
