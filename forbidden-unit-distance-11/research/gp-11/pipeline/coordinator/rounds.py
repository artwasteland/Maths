#!/usr/bin/env python3
"""Allocate a checked frontier; certificate acceptance remains the driver's job."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

MAX_RECORD = 8 * 1024 * 1024


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def codes(path):
    rows = path.read_text().splitlines()
    if rows != sorted(set(rows)):
        raise ValueError("round_input_order")
    return rows


def bundle(directory):
    summary = json.loads((directory / "summary.json").read_text())
    if not summary.get("completed") or summary.get("checker_status") != "ACCEPT":
        raise ValueError("incomplete_bundle")
    required = {"assigned.g6", "UNKNOWN.g6", "records.jsonl.gz"}
    if not required <= summary["artifacts"].keys():
        raise ValueError("round_bundle_artifacts")
    for name, expected in summary["artifacts"].items():
        if Path(name).name != name or digest(directory / name) != expected:
            raise ValueError("bundle_artifact_hash:" + name)
    return summary


def prepare(source, output):
    summary = bundle(source)
    assigned = set(codes(source / "assigned.g6"))
    frontier = codes(source / "UNKNOWN.g6")
    if not set(frontier) <= assigned or len(frontier) != summary["counts"]["unknown"]:
        raise ValueError("round_frontier_coverage")
    if output.exists():
        raise ValueError("round_output_exists")
    output.mkdir(parents=True)
    selected = set()
    # Only UNKNOWN records travel here. No positive or negative receipt becomes a seed.
    with gzip.open(source / "records.jsonl.gz", "rb") as stream:
        with (output / "unknown-records.jsonl.gz").open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as target:
                while line := stream.readline(MAX_RECORD + 1):
                    if len(line) > MAX_RECORD:
                        raise ValueError("record_size_cap")
                    record = json.loads(line)
                    if record["verdict"] != "unknown":
                        continue
                    code = record["g6"]
                    if code not in assigned or code in selected:
                        raise ValueError("round_frontier_coverage")
                    selected.add(code)
                    target.write(line)
    if selected != set(frontier):
        raise ValueError("round_frontier_coverage")
    (output / "input.g6").write_bytes((source / "UNKNOWN.g6").read_bytes())
    manifest = {"schema": 1, "purpose": "frontier_allocation_only", "count": len(frontier),
                "predecessor_summary_sha256": digest(source / "summary.json"),
                "helper_sha256": digest(Path(__file__)),
                "artifacts": {name: digest(output / name) for name in ("input.g6", "unknown-records.jsonl.gz")}}
    write_json(output / "round.json", manifest)
    return manifest


def coverage(selection, directories):
    manifest = json.loads((selection / "round.json").read_text())
    for name, expected in manifest["artifacts"].items():
        if Path(name).name != name or digest(selection / name) != expected:
            raise ValueError("round_input_hash:" + name)
    expected = set(codes(selection / "input.g6"))
    if len(expected) != manifest["count"]:
        raise ValueError("round_input_count")
    union = set()
    receipts = []
    for directory in sorted(directories):
        bundle(directory)
        current = set(codes(directory / "assigned.g6"))
        if union & current:
            raise ValueError("round_union_duplicate")
        union.update(current)
        receipts.append(digest(directory / "summary.json"))
    if union != expected:
        raise ValueError(f"round_union_coverage: missing={len(expected-union)} extra={len(union-expected)}")
    # The subsequent drive.py merge independently checks every returned certificate.
    return {"coverage_status": "PASS", "count": len(union), "bundle_summary_sha256": receipts,
            "round_manifest_sha256": digest(selection / "round.json"), "certificates_rechecked": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    first = commands.add_parser("prepare")
    first.add_argument("source", type=Path)
    first.add_argument("output", type=Path)
    check = commands.add_parser("coverage")
    check.add_argument("selection", type=Path)
    check.add_argument("bundles", type=Path, nargs="+")
    args = parser.parse_args()
    result = prepare(args.source, args.output) if args.command == "prepare" else coverage(args.selection, args.bundles)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
