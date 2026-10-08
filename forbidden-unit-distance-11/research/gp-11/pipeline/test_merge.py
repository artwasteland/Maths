#!/usr/bin/env python3
"""Real cross-shard propagation, dependency replay, and incomplete-union rejection."""
from common import *
import argparse
import gzip
import shutil
import sqlite3
import subprocess
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    limits(args.output / "scratch")
    guard = Guard()
    guard.start()
    db = sqlite3.connect(f"file:{args.controls / 'state/state.sqlite'}?mode=ro", uri=True)
    groups = {"seeds": [], "pointers": []}
    records = []
    with (args.controls / "state/certificates.jsonl").open("rb") as source:
        for code, origin, value, offset, length in db.execute(
                "SELECT g6,origin,accepted.hash,offset,size FROM accepted JOIN blobs ON accepted.hash=blobs.hash ORDER BY seq"):
            source.seek(offset)
            raw = source.read(length)
            assert hashlib.sha256(raw).hexdigest() == value
            if origin == "control":
                groups["seeds"].append(code)
            elif origin == "propagation":
                groups["pointers"].append(code)
            if origin != "propagation":
                records.append(raw)
    db.close()
    assert {name: len(codes) for name, codes in groups.items()} == {"seeds": 2, "pointers": 2}
    record_path = args.output / "seed-records.jsonl"
    atomic(record_path, b"".join(records))
    groups["merged"] = groups["seeds"] + groups["pointers"]
    for name, codes in groups.items():
        atomic(args.output / (name + ".g6"), "".join(code + "\n" for code in sorted(codes)))

    def run(name, extra, expected=None):
        selection = name if name in groups else "merged"
        command = [sys.executable, "-B", str(HERE / "drive.py"), "run", "--index", str(args.index),
                   "--state", str(args.output / (name + "-state")),
                   "--output", str(args.output / (name + "-result")),
                   "--input", str(args.output / (selection + ".g6")), "--policy", "cheap", "--intake-only"] + extra
        log_path = args.output / (name + ".log")
        with log_path.open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=log)
        if expected:
            assert result.returncode != 0 and expected in log_path.read_text(), log_path.read_text()
            return
        assert result.returncode == 0, log_path.read_text()
        summary = json.loads((args.output / (name + "-result/summary.json")).read_text())
        assert summary["checker_status"] == "ACCEPT"
        return summary["counts"]

    assert run("seeds", ["--records", str(record_path)]) == {"embedded": 1, "refuted": 1, "unknown": 0}
    assert run("pointers", []) == {"embedded": 0, "refuted": 0, "unknown": 2}
    bundle_args = ["--bundle", str(args.output / "seeds-result"), "--bundle", str(args.output / "pointers-result")]
    assert run("merged", bundle_args) == {"embedded": 2, "refuted": 2, "unknown": 0}
    with gzip.open(args.output / "merged-result/records.jsonl.gz", "rt") as source:
        merged = {row["g6"]: row for line in source if (row := json.loads(line))["g6"] in groups["pointers"]}
    assert {row["cert"]["type"] for row in merged.values()} == {"sub", "super"}
    run("incomplete", bundle_args + ["--require-complete-union"], "shard_union_coverage")
    run("duplicate", bundle_args + ["--bundle", str(args.output / "seeds-result"), "--require-complete-union"], "shard_union_duplicate")
    # Re-run the positive merge after both valid-input union controls.
    assert run("positive-after", bundle_args) == {"embedded": 2, "refuted": 2, "unknown": 0}
    import export
    from poset import Poset
    poset = Poset(args.index)
    ck = checker(args.output / "scratch/check")
    positive = args.output / "pointers-result"
    with gzip.open(positive / "records.jsonl.gz", "rb") as source:
        original = source.read()
    for name, expected in (("extra-record", "bundle_record_count"), ("large-record", "record_size_cap")):
        target = args.output / name
        shutil.copytree(positive, target)
        if name == "extra-record":
            altered = original + original.splitlines(keepends=True)[0]
        else:
            rows = [json.loads(line) for line in original.splitlines()]
            rows[0]["cert"]["reason"] = "x" * 5000
            altered = "".join(compact(row) + "\n" for row in rows).encode()
        for line in altered.splitlines():
            ck.loads(line)
        with gzip.open(target / "records.jsonl.gz", "wb") as stream:
            stream.write(altered)
        receipt = json.loads((target / "summary.json").read_text())
        receipt["records_sha256"] = hashlib.sha256(altered).hexdigest()
        receipt["artifacts"]["records.jsonl.gz"] = digest(target / "records.jsonl.gz")
        write_json(target / "summary.json", receipt)
        try:
            with patch.object(export, "MAX_RECORD", 4096):
                export.replay_bundle(target, ck, args.output / "scratch", poset)
        except ValueError as exc:
            assert str(exc) == expected, str(exc)
        else:
            raise AssertionError("bundle_limit_not_enforced:" + name)
        assert export.replay_bundle(positive, ck, args.output / "scratch", poset)["status"] == "ACCEPT"
    report = {"status": "PASS", "before_import": {"embedded": 0, "refuted": 0, "unknown": 2},
              "after_import": {"embedded": 2, "refuted": 2, "unknown": 0},
              "cross_shard_pointer_types": ["sub", "super"],
              "incomplete_union": "shard_union_coverage", "duplicate_union": "shard_union_duplicate",
              "valid_json_bundle_limits": ["bundle_record_count", "record_size_cap"],
              "positive_after": "ACCEPT"}
    write_json(args.output / "merge.json", report)
    print(compact(report))
    guard.stop.set()


if __name__ == "__main__":
    main()
