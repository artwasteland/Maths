#!/usr/bin/env python3
"""Blind exact checker for stage-3 real and no-realization certificates."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "chiro"))
sys.path.insert(0, str(HERE))
from chirosat import parse_pts_line  # noqa: E402
from core import build_system, saturated_groebner, verify_real_witness  # noqa: E402


def check_record(pts, record: dict) -> tuple[bool, str]:
    if record.get("pts") != pts.line:
        return False, "certificate PTS does not exactly match the input PTS"
    verdict = record.get("verdict")
    if verdict == "real":
        return verify_real_witness(pts, record.get("witness", {}))
    if verdict == "no-realization":
        witness = record.get("witness", {})
        stated_blocks = witness.get("ideal_blocks")
        if stated_blocks != [list(block) for block in pts.blocks]:
            return False, "stated ideal omits, adds, or reorders a PTS block"
        try:
            system = build_system(pts, witness.get("construction", {}))
        except (TypeError, ValueError) as exc:
            return False, f"invalid construction: {exc}"
        if system["has_free_step"]:
            return False, "a one-chart free-point construction is not a complete negative proof"
        if witness.get("parameters") != [str(variable) for variable in system["parameters"]]:
            return False, "stated parameter list differs from the reconstructed construction"
        if witness.get("block_equation_count") != len(system["block_equations"]):
            return False, "stated block-equation count differs from the PTS-derived system"
        if witness.get("nondegeneracy_count") != len(system["nondegeneracies"]):
            return False, "stated non-degeneracy count differs from the PTS-derived system"
        recomputed = saturated_groebner(system)
        if not recomputed["is_unit"]:
            return False, "recomputed saturated ideal does not have Groebner basis {1}"
        basis = [str(value) for value in recomputed["basis"]]
        if witness.get("reduced_groebner_basis") != basis or basis != ["1"]:
            return False, "stated reduced Groebner basis differs from the recomputation"
        if witness.get("saturation_product_remainder") != str(recomputed["product_remainder"]):
            return False, "stated saturation remainder differs from the recomputation"
        return True, "recomputed from the PTS: the characteristic-zero saturated ideal has basis {1}"
    if verdict == "unknown":
        return False, "unknown is honest but has no certificate to accept"
    return False, f"checker does not accept verdict {verdict!r}"


def load_one_pts(path: Path):
    lines = [line for line in path.read_text(encoding="ascii").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) != 1:
        raise ValueError("PTS input must contain exactly one instance")
    return parse_pts_line(lines[0])


def load_record(path: Path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError("certificate input must contain exactly one JSON record")
    value = json.loads(lines[0])
    if not isinstance(value, dict):
        raise ValueError("certificate JSON must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pts", type=Path)
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        pts = load_one_pts(args.pts)
        record = load_record(args.certificate)
        accepted, detail = check_record(pts, record)
        print(json.dumps({"accepted": accepted, "detail": detail,
                          "wall_seconds": round(time.perf_counter() - started, 6)}, sort_keys=True))
        return 0 if accepted else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"accepted": False, "detail": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
