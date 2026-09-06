#!/usr/bin/env python3
"""Decide exact real realizability of contract PTS instances when certified."""

from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing
import sys
import time
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "chiro"))
sys.path.insert(0, str(HERE))
from chirosat import PTS, iter_input_lines, parse_pts_line  # noqa: E402
from core import (  # noqa: E402
    build_system,
    choose_construction,
    nf_reduce,
    pegg_witness,
    rational_assignment,
    rational_witness,
    saturated_groebner,
    verify_real_witness,
)


def algebraic_univariate_witness(pts: PTS, system, saturation):
    variables = system["parameters"]
    if len(variables) != 1:
        return None
    variable = variables[0]
    equations = [sp.Poly(eq, variable, domain=sp.QQ) for eq in system["block_equations"] if eq != 0]
    if not equations:
        return None
    common = equations[0]
    for equation in equations[1:]:
        common = sp.gcd(common, equation)
    if common.degree() < 1:
        return None
    factors = [factor.monic() for factor, _power in sp.factor_list(common)[1]]
    admissible = []
    excluded_real = []
    for factor in factors:
        bad = [g for g in saturation["nondegeneracies"] if sp.Poly(g, variable, domain=sp.QQ).rem(factor).is_zero]
        real_count = factor.count_roots(-sp.oo, sp.oo)
        if bad:
            excluded_real.append({"factor": str(factor.as_expr()), "real_roots": int(real_count),
                                  "violating_nondegeneracies": len(bad)})
        else:
            admissible.append((factor, int(real_count)))
    for factor, real_count in admissible:
        if not real_count:
            continue
        intervals = factor.intervals(eps=sp.Rational(1, 10**8))
        interval = next(bounds for bounds, multiplicity in intervals if multiplicity and bounds[0] != bounds[1])
        alpha = sp.Symbol("alpha")
        modulus = sp.Poly(factor.as_expr().subs(variable, alpha), alpha, domain=sp.QQ)
        points = []
        for point in range(pts.v):
            points.append([
                str(nf_reduce(value.subs(variable, alpha), alpha, modulus))
                for value in system["coordinates"][point]
            ])
        witness = {
            "field": {
                "type": "number-field",
                "generator": "alpha",
                "minimal_polynomial": str(modulus.as_expr()),
                "isolating_interval": [str(interval[0]), str(interval[1])],
            },
            "points": points,
        }
        accepted, detail = verify_real_witness(pts, witness)
        if accepted:
            return "real", witness, {"root_isolation": detail}
    complex_factors = [factor for factor, real_count in admissible if real_count == 0]
    if complex_factors and not any(real_count for _factor, real_count in admissible):
        factor = complex_factors[0]
        alpha = sp.Symbol("alpha")
        modulus = sp.Poly(factor.as_expr().subs(variable, alpha), alpha, domain=sp.QQ)
        points = [[str(nf_reduce(value.subs(variable, alpha), alpha, modulus))
                   for value in system["coordinates"][point]] for point in range(pts.v)]
        witness = {
            "field": {
                "type": "number-field-complex",
                "generator": "alpha",
                "minimal_polynomial": str(modulus.as_expr()),
                "real_root_count": 0,
            },
            "points": points,
        }
        evidence = {
            "case": "all algebraically admissible irreducible factors have no real root",
            "admissible_factors": [str(item.as_expr()) for item in complex_factors],
            "excluded_real_factors": excluded_real,
        }
        return "complex-only", witness, evidence
    return None


def decide(pts: PTS) -> dict:
    started = time.perf_counter()
    special = pegg_witness(pts)
    if special is not None:
        accepted, detail = verify_real_witness(pts, special)
        if not accepted:
            raise RuntimeError(f"internal Pegg exact witness failed: {detail}")
        return {
            "pts": pts.line,
            "verdict": "real",
            "certificate_kind": "exact coordinates in Q(alpha)",
            "witness": special,
            "prover_exact_check": detail,
            "wall_seconds": round(time.perf_counter() - started, 6),
        }

    construction = choose_construction(pts)
    system = build_system(pts, construction)
    assignment = rational_assignment(system)
    if assignment is not None:
        witness = rational_witness(system, assignment)
        accepted, detail = verify_real_witness(pts, witness)
        if not accepted:
            raise RuntimeError(f"internal rational witness failed: {detail}")
        return {
            "pts": pts.line,
            "verdict": "real",
            "certificate_kind": "exact rational projective coordinates",
            "witness": witness,
            "construction": system["construction"],
            "parameter_assignment": {str(key): str(value) for key, value in assignment.items()},
            "prover_exact_check": detail,
            "wall_seconds": round(time.perf_counter() - started, 6),
        }
    if system["has_free_step"]:
        return {
            "pts": pts.line,
            "verdict": "unknown",
            "certificate_kind": None,
            "reason": "the selected construction needs a free-point affine chart; all projective charts were not exhausted",
            "construction": system["construction"],
            "wall_seconds": round(time.perf_counter() - started, 6),
        }

    saturation = saturated_groebner(system)
    if saturation["is_unit"]:
        witness = {
            "construction": system["construction"],
            "ideal_blocks": [list(block) for block in pts.blocks],
            "parameters": [str(variable) for variable in system["parameters"]],
            "block_equation_count": len(system["block_equations"]),
            "nondegeneracy_count": len(system["nondegeneracies"]),
            "reduced_groebner_basis": [str(value) for value in saturation["basis"]],
            "saturation_product_remainder": str(saturation["product_remainder"]),
            "derivation": saturation["reason"],
            "scope": "no realization over any field of characteristic 0; characteristic p is not claimed",
        }
        return {
            "pts": pts.line,
            "verdict": "no-realization",
            "certificate_kind": "unit Groebner basis after Rabinowitsch saturation",
            "witness": witness,
            "wall_seconds": round(time.perf_counter() - started, 6),
        }

    algebraic = algebraic_univariate_witness(pts, system, saturation)
    if algebraic is not None:
        verdict, witness, evidence = algebraic
        return {
            "pts": pts.line,
            "verdict": verdict,
            "certificate_kind": "exact univariate number-field witness and real-root isolation",
            "witness": witness,
            "evidence": evidence,
            "construction": system["construction"],
            "wall_seconds": round(time.perf_counter() - started, 6),
        }
    return {
        "pts": pts.line,
        "verdict": "unknown",
        "certificate_kind": None,
        "reason": "saturated ideal is nontrivial but the exact solver did not certify its real locus",
        "construction": system["construction"],
        "saturated_basis": [str(value) for value in saturation["basis"]],
        "wall_seconds": round(time.perf_counter() - started, 6),
    }


def _worker(connection, pts: PTS):
    try:
        connection.send(decide(pts))
    except Exception as exc:  # An algebra failure is an honest unknown, never a negative verdict.
        connection.send({"pts": pts.line, "verdict": "unknown", "certificate_kind": None,
                         "reason": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


def decide_with_timeout(pts: PTS, timeout: float) -> dict:
    if timeout <= 0:
        return decide(pts)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, pts))
    started = time.perf_counter()
    process.start()
    child.close()
    if not parent.poll(timeout):
        process.kill()
        process.join()
        return {"pts": pts.line, "verdict": "unknown", "certificate_kind": None,
                "reason": f"finite time limit of {timeout} seconds reached",
                "wall_seconds": round(time.perf_counter() - started, 6)}
    result = parent.recv()
    process.join()
    result.setdefault("wall_seconds", round(time.perf_counter() - started, 6))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="contract PTS file, or -")
    parser.add_argument("--timeout", type=float, default=300.0, help="finite seconds per PTS; 0 disables")
    parser.add_argument("--out", type=Path, help="write JSONL instead of stdout")
    args = parser.parse_args()
    records = []
    try:
        for line in iter_input_lines(args.input):
            records.append(decide_with_timeout(parse_pts_line(line), args.timeout))
        if not records:
            raise ValueError("input contains no PTS lines")
        text = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError) as exc:
        print(f"realize: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
