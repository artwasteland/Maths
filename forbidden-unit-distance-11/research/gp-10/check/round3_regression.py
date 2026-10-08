#!/usr/bin/env python3
"""Run the unchanged audit replay while retaining Round 2's historical evidence."""
import os
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import audit_regression as replay
import gp10check as ck


def main():
    historical = ck.HERE / "round2-regression.json"
    saved = historical.read_bytes()
    replay.OUTPUT = ck.SCRATCH / "round3/regression"
    try:
        code = replay.main(["--all"])
        (ck.HERE / "round3-regression.json").write_bytes(historical.read_bytes())
        return code
    finally:
        historical.write_bytes(saved)


if __name__ == "__main__":
    sys.exit(main())
