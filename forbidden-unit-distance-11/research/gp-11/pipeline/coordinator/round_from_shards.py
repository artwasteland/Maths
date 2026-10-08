#!/usr/bin/env python3
"""Allocate the next round from MANY checked shard bundles (rounds.py prepare takes one coordinator result).

usage: round_from_shards.py OUTPUT [--bundles DIR ...] [--exclude-state STATE.sqlite] [--add-shards INPUT.g6 COUNT I ...]

Collects every UNKNOWN graph of the given bundles with its UNKNOWN record (the attempt history travels; no decided
record does), drops the graphs a predecessor state has since accepted (read-only SQLite snapshot of a pipeline state,
table accepted), and adds, with no record, every graph of INPUT.g6 that falls in shards I ... of COUNT under the
driver's own rule (drive.py: SHA256(graph6)[:8] big endian mod COUNT) and is in no given bundle: shards a round
never ran. Writes input.g6 (sorted), unknown-records.jsonl.gz and round.json in the format rounds.py coverage reads.
It accepts no certificate; the driver rechecks everything it imports.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rounds import MAX_RECORD, bundle, codes, digest, write_json  # noqa: E402


def shard_of(code, count):
    return int.from_bytes(hashlib.sha256(code.encode()).digest()[:8], "big") % count


def prepare(output, directories, state=None, add=None):
    if output.exists():
        raise ValueError("round_output_exists")
    unknown, assigned, receipts = {}, set(), []
    for directory in sorted(directories):
        summary = bundle(directory)
        here = set(codes(directory / "assigned.g6"))
        if assigned & here:
            raise ValueError("round_union_duplicate:" + str(directory))
        assigned |= here
        frontier = set(codes(directory / "UNKNOWN.g6"))
        if not frontier <= here or len(frontier) != summary["counts"]["unknown"]:
            raise ValueError("round_frontier_coverage:" + str(directory))
        seen = set()
        with gzip.open(directory / "records.jsonl.gz", "rb") as stream:
            while line := stream.readline(MAX_RECORD + 1):
                if len(line) > MAX_RECORD:
                    raise ValueError("record_size_cap")
                record = json.loads(line)
                if record["verdict"] != "unknown":
                    continue
                if record["g6"] not in frontier or record["g6"] in seen:
                    raise ValueError("round_frontier_coverage:" + str(directory))
                seen.add(record["g6"])
                unknown[record["g6"]] = line
        if seen != frontier:
            raise ValueError("round_frontier_coverage:" + str(directory))
        receipts.append({"bundle": str(directory), "summary_sha256": digest(directory / "summary.json"),
                         "assigned": len(here), "unknown": len(frontier)})
    excluded = set()
    if state:
        db = sqlite3.connect(f"file:{state}?mode=ro", uri=True, timeout=60)
        db.execute("BEGIN")
        decided = {g for (g,) in db.execute("SELECT g6 FROM accepted")}
        db.rollback()
        excluded = set(unknown) & decided
    added = set()
    if add:
        source, count, indices = Path(add[0]), int(add[1]), {int(i) for i in add[2:]}
        for code in codes(source):
            if shard_of(code, count) in indices and code not in assigned:
                added.add(code)
        if state:
            excluded_added = added & decided
            added -= excluded_added
            excluded |= excluded_added
    selected = sorted((set(unknown) - excluded) | added)
    output.mkdir(parents=True)
    (output / "input.g6").write_text("".join(c + "\n" for c in selected))
    with (output / "unknown-records.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as target:
            for code in selected:
                if code in unknown:
                    target.write(unknown[code])
    manifest = {"schema": 1, "purpose": "frontier_allocation_only", "count": len(selected),
                "predecessors": receipts, "bundle_unknown": len(unknown),
                "excluded_decided_by_state": len(excluded), "state": str(state) if state else None,
                "added_unrun_shards": {"input": add[0], "count": int(add[1]), "indices": sorted(int(i) for i in add[2:]),
                                       "graphs": len(added)} if add else None,
                "helper_sha256": digest(Path(__file__)),
                "artifacts": {name: digest(output / name) for name in ("input.g6", "unknown-records.jsonl.gz")}}
    write_json(output / "round.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bundles", type=Path, nargs="*", default=[])
    parser.add_argument("--exclude-state", type=Path)
    parser.add_argument("--add-shards", nargs="+", metavar="ARG", help="INPUT.g6 COUNT I [I ...]")
    args = parser.parse_args()
    if args.add_shards is not None and len(args.add_shards) < 3:
        parser.error("--add-shards needs INPUT.g6 COUNT and at least one index")
    if not args.bundles and not args.add_shards:
        parser.error("nothing to allocate: give --bundles, --add-shards, or both")
    print(json.dumps(prepare(args.output, args.bundles, args.exclude_state, args.add_shards), sort_keys=True))


if __name__ == "__main__":
    main()
