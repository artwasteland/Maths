#!/usr/bin/env python3
"""Run every fixed control through chirosat.py batch mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from batch_bench import write_marked
from controls import CONTROLS


def require_verdict(name: str, actual: object, expected: str) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: got {actual}, expected {expected}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("scratch/batch-controls-final"))
    args = parser.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    grouped: dict[int, list[tuple[str, object, str]]] = {}
    for name, (instance, expected) in CONTROLS.items():
        grouped.setdefault(instance.v, []).append((name, instance, expected))

    all_records: dict[str, dict[str, object]] = {}
    for v, entries in sorted(grouped.items()):
        input_path = args.outdir / f"controls-v{v}.txt"
        write_marked(input_path, (entry[1] for entry in entries))
        output_path = args.outdir / f"controls-v{v}.jsonl"
        artifact_path = args.outdir / f"artifacts-v{v}"
        command = [
            sys.executable,
            "chirosat.py",
            "--batch",
            str(input_path),
            "--out",
            str(output_path),
            "--artifacts",
            str(artifact_path),
            "--proof-sample-rate",
            "1",
            "--second-solver",
            "kissat",
        ]
        process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0:
            raise RuntimeError(f"batch controls failed for v={v}: {process.stderr}")
        records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
        if len(records) != len(entries):
            raise AssertionError(f"v={v}: output count mismatch")
        for (name, _instance, expected), record in zip(entries, records):
            require_verdict(name, record["verdict"], expected)
            all_records[name] = record
            print(
                f"BATCH CONTROL {name} v={v} verdict={record['verdict']} "
                f"expected={expected} proof_sampled={record['proof_sampled']} "
                f"second_solver={record.get('second_solver', {}).get('agreement', '-')} PASS"
            )

    first_input = args.outdir / "controls-v7.txt"
    missing_input = args.outdir / "missing-marker.txt"
    missing_input.write_bytes(first_input.read_bytes())
    rejected = subprocess.run(
        [
            sys.executable,
            "chirosat.py",
            "--batch",
            str(missing_input),
            "--out",
            str(args.outdir / "should-not-exist.jsonl"),
            "--proof-sample-rate",
            "0",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if rejected.returncode == 0 or "missing completion marker" not in rejected.stderr:
        raise AssertionError("batch input without DONE marker was accepted")
    print("MUTATION batch-missing-done rejected=true PASS")

    fano = all_records["fano"]
    wrong_expected = "pseudoline" if fano["verdict"] == "no-pseudoline" else "no-pseudoline"
    try:
        require_verdict("inverted-batch-fano", fano["verdict"], wrong_expected)
    except AssertionError as exc:
        print(f"MUTATION batch-expected-verdict rejected={str(exc)!r} PASS")
    else:
        raise AssertionError("inverted batch expectation was accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
