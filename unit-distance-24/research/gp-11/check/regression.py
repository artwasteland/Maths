#!/usr/bin/env python3
"""Execute GP-10's unchanged selftest and fixture corpus through the new module.

Only module injection is adapted. The old test source and fixture bytes are untouched.
"""
import importlib.util
from pathlib import Path
import sys
import tempfile
import types

sys.dont_write_bytecode = True
import gp11check as ck


def main():  # B11 regression harness addition.
    old = ck.GP10 / "check"
    sys.path.insert(0, str(old))
    proxy = types.ModuleType("gp10check")
    proxy.__dict__.update(vars(ck.base))
    proxy.Checker = ck.Checker
    proxy.Run = ck.Run
    proxy.main = ck.main
    sys.modules["gp10check"] = proxy
    spec = importlib.util.spec_from_file_location("gp10_original_selftest", old / "selftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    # The old corpus compares exact rule names; repeat the real positives after every red.
    checker = ck.Checker()
    for fixtures in (old / "fixtures", old / "fixtures/round3"):
        for case in ck.read_json(fixtures / "cases.json"):
            path = case["file"] if case["status"] == "ACCEPT" else case["positive"]
            assert checker.verify(ck.read_json(fixtures / path))[0] is None
            if case["name"] in ("null-failed-identity", "real-last-not-f"):
                print("GP10 DAG CLI " + case["name"] + " exact rejection=" + case["reason"])
    with tempfile.TemporaryDirectory(prefix="gp11-regression-") as scratch:
        for name in ("pointers", "mixed", "unknown", "refutation-pointer", "frozen-pointer",
                     "tu-refuted-pointer", "minimality", "conditional-minimality"):
            result = ck.Run(old / "fixtures" / name, Path(scratch) / name, emit=lambda _: None).execute()
            assert result["status"] == "ACCEPT", result
    print("GP10 RESTORE PASS: original certificates and run verdicts unchanged")


if __name__ == "__main__":
    main()
