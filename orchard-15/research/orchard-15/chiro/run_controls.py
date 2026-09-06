#!/usr/bin/env python3
"""Run the required fixed controls and deliberate failure controls."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
from typing import Sequence

from chirosat import (
    InputError,
    find_executable,
    parse_pts_line,
    solve_one,
    verify_witness,
    build_encoding,
)
from controls import CONTROLS, FANO, PAPPUS


def require_verdict(name: str, actual: object, expected: str) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: got {actual}, expected {expected}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", choices=tuple(CONTROLS))
    parser.add_argument("--artifacts", default="scratch/control-artifacts")
    parser.add_argument("--solver")
    parser.add_argument("--drat-trim")
    parser.add_argument("--mutations", action="store_true")
    return parser


def run_mutations(
    artifact_dir: Path,
    solver: str,
    checker: str,
    results: dict[str, dict[str, object]],
) -> None:
    mutant = solve_one(
        FANO,
        artifact_dir / "mutation-drop-positive",
        solver,
        checker,
        drop_gp_family="positive",
    )
    require_verdict("drop-positive", mutant["verdict"], "pseudoline")
    print(
        "MUTATION drop-positive-gp fano "
        f"verdict={mutant['verdict']} clauses={mutant['clauses']} PASS"
    )

    fano = results["fano"]
    proof = Path(str(fano["witness"]))
    cnf = Path(str(fano["cnf"]))
    corrupt = artifact_dir / "mutation-corrupt-fano.drat"
    proof_lines = proof.read_bytes().splitlines(keepends=True)
    corrupt.write_bytes(b"".join(proof_lines[: max(1, len(proof_lines) // 2)]))
    checked = subprocess.run(
        [checker, str(cnf), str(corrupt)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    rejected = checked.returncode != 0 and "NOT VERIFIED" in checked.stdout
    if not rejected:
        raise AssertionError("truncated DRAT proof was not rejected")
    print(
        "MUTATION truncate-drat fano "
        f"checker_exit={checked.returncode} not_verified=true PASS"
    )

    pappus_witness = str(results["pappus"]["witness"])
    first_nonzero = pappus_witness.index(next(x for x in pappus_witness if x != "0"))
    bad_witness = pappus_witness[:first_nonzero] + "0" + pappus_witness[first_nonzero + 1 :]
    try:
        verify_witness(build_encoding(PAPPUS), bad_witness)
    except RuntimeError as exc:
        print(f"MUTATION witness-zero pappus rejected={str(exc)!r} PASS")
    else:
        raise AssertionError("bad Pappus witness was accepted")

    try:
        parse_pts_line("5 2 : 0 1 2 , 0 1 3 ;")
    except InputError as exc:
        print(f"MUTATION repeated-pair parser rejected={str(exc)!r} PASS")
    else:
        raise AssertionError("non-PTS repeated pair was accepted")

    try:
        require_verdict("inverted-fano-expectation", "no-pseudoline", "pseudoline")
    except AssertionError as exc:
        print(f"MUTATION expected-verdict rejected={str(exc)!r} PASS")
    else:
        raise AssertionError("wrong expected verdict was accepted")


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    solver = find_executable(args.solver, ("/usr/bin/cadical", "cadical"))
    checker = find_executable(
        args.drat_trim,
        (
            "~/tools/sat/drat-trim/drat-trim",
            str(Path(__file__).resolve().parent / "scratch" / "drat-trim"),
            "drat-trim",
        ),
    )
    artifact_dir = Path(args.artifacts)
    names = args.names or list(CONTROLS)
    if args.mutations:
        for needed in ("fano", "pappus"):
            if needed not in names:
                names.append(needed)
    results: dict[str, dict[str, object]] = {}
    for name in names:
        instance, expected = CONTROLS[name]
        instance = parse_pts_line(instance.line)
        result = solve_one(instance, artifact_dir / name, solver, checker)
        require_verdict(name, result["verdict"], expected)
        results[name] = result
        check_seconds = result.get("check_seconds", "-")
        print(
            f"CONTROL {name} v={instance.v} b={len(instance.blocks)} "
            f"verdict={result['verdict']} expected={expected} "
            f"vars={result['variables']} clauses={result['clauses']} "
            f"encode_s={result['encode_seconds']} write_s={result['write_seconds']} "
            f"solve_s={result['solve_seconds']} check_s={check_seconds} "
            f"total_s={result['total_seconds']} PASS"
        )
    if args.mutations:
        run_mutations(artifact_dir, solver, checker, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
