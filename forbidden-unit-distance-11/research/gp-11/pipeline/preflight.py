"""Fail before research work if the worker's existing GP-10 tools are incomplete."""
from common import *
import importlib.metadata
import shutil
import subprocess


def run(scratch):
    executables = {}
    for name in ("cc", "ld", "nauty-labelg", "gp", "Singular", "msolve"):
        path = shutil.which(name)
        if path is None:
            raise ValueError("missing_tool:" + name)
        executables[name] = {"path": path, "sha256": digest(path)}
    versions = {name: importlib.metadata.version(name) for name in
                ("python-flint", "networkx", "pynauty", "numpy", "scipy", "sympy", "mpmath")}
    import msolve_exact
    redirect(scratch)
    _, binary = msolve_exact.prepare_binary()
    subprocess.run(["cc", "-O2", "-fPIC", "-c", str(GP / "embed/msolve_seed.c"),
                    "-o", str(scratch / "msolve_seed.o")], check=True)
    subprocess.run(["ld", "-shared", str(scratch / "msolve_seed.o"), "-ldl",
                    "-o", str(scratch / "msolve_seed.so")], check=True)
    ck = checker(scratch / "check")
    triangle = {"g6": "Bw", "verdict": "embedded", "cert": {"type": "exact",
        "field": {"minpoly": [-3, 0, 1], "interval": ["1", "2"]},
        "coords": [[["0", "0"], ["0", "0"]], [["1", "0"], ["0", "0"]], [["1/2", "0"], ["0", "1/2"]]]}}
    ck.Checker(9).verify(triangle)
    return {"status": "PASS", "python": sys.version, "packages": versions,
            "executables": executables, "msolve": binary, "frozen_exact_control": "ACCEPT"}
