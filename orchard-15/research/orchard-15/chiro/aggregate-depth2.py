#!/usr/bin/env python3
"""Audit depth-2 cube JSONL coverage against exist.py's independent listing."""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def expected_names(v: int, b: int, cube_index: int) -> list[str]:
    maths_python = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"
    listing_python = str(maths_python) if maths_python.is_file() else sys.executable
    command = [
        listing_python,
        str(Path(__file__).with_name("exist.py")),
        str(v),
        str(b),
        "--backend",
        "pysat",
        "--list-cubes",
        "--cube-depth",
        "2",
        "--cube-index",
        str(cube_index),
    ]
    process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"cube listing failed with exit {process.returncode}: {detail}")
    listing = json.loads(process.stdout)
    children = listing["level2"][str(cube_index)]["children"]
    return [child["name"] for child in children]


def read_records(paths: Sequence[Path]) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    problems: list[str] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    problems.append(f"invalid JSON at {path}:{line_number}: {exc.msg}")
                    continue
                if not isinstance(record, dict):
                    problems.append(f"record at {path}:{line_number} is not a JSON object")
                    continue
                records.append(record)
    return records, problems


def coverage_problems(expected: Sequence[str], records: Sequence[dict[str, object]]) -> list[str]:
    problems: list[str] = []
    expected_set = set(expected)
    names = [record.get("cube_name") for record in records]
    counts = collections.Counter(name for name in names if isinstance(name, str))

    for name in expected:
        if counts[name] == 0:
            problems.append(f"missing {name}")
        elif counts[name] > 1:
            problems.append(f"duplicated {name}: {counts[name]} records")
    for name in sorted(counts.keys() - expected_set):
        problems.append(f"unexpected name {name}")
    unnamed = sum(not isinstance(name, str) for name in names)
    if unnamed:
        problems.append(f"unexpected name: {unnamed} record(s) have no string cube_name")

    for number, record in enumerate(records, start=1):
        name = record.get("cube_name")
        label = name if isinstance(name, str) else f"record {number}"
        if record.get("verdict") != "UNSAT":
            problems.append(f"wrong verdict for {label}: {record.get('verdict')!r}")
        if record.get("proof_verified") is not True:
            problems.append(f"unverified {label}: proof_verified is not true")
        for field in ("cnf_sha256", "proof_sha256"):
            value = record.get(field)
            if not isinstance(value, str) or not value:
                problems.append(f"missing hash for {label}: {field}")
        tail = record.get("checker_tail")
        if not isinstance(tail, str) or "s VERIFIED" not in tail.splitlines():
            problems.append(f"unverified {label}: checker_tail lacks exact line s VERIFIED")
    return problems


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v", type=int, required=True)
    parser.add_argument("--b", type=int, required=True)
    parser.add_argument("--cube-index", type=int, required=True)
    parser.add_argument("--mutate", action="store_true", help="drop one record after reading")
    parser.add_argument(
        "--mutate-dup",
        action="store_true",
        help="replace one record by a duplicate of another",
    )
    parser.add_argument("jsonl", type=Path, nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.mutate and args.mutate_dup:
        print("COVERAGE FAIL: --mutate and --mutate-dup are mutually exclusive")
        return 1
    try:
        expected = expected_names(args.v, args.b, args.cube_index)
        records, problems = read_records(args.jsonl)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"COVERAGE FAIL: {type(exc).__name__}: {exc}")
        return 1
    if args.mutate:
        if records:
            records = records[:-1]
        else:
            problems.append("mutation could not drop a record from empty input")
    if args.mutate_dup:
        if len(records) >= 2:
            records = list(records)
            records[-1] = records[0]
        else:
            problems.append("duplicate mutation needs at least two records")
    problems.extend(coverage_problems(expected, records))
    if not problems:
        print(f"COVERAGE PASS: {len(expected)} expected children, each appears exactly once and is verified UNSAT")
        return 0
    print(f"COVERAGE FAIL: {len(problems)} problem(s)")
    for problem in problems[:10]:
        print(f"- {problem}")
    if len(problems) > 10:
        print(f"- ... {len(problems) - 10} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
