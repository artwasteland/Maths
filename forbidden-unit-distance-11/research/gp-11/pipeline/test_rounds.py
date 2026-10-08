#!/usr/bin/env python3
"""Return a small frontier round and merge its checked improvements with its parent."""
from common import *
import argparse
import gzip
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--merge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rounds = load("round_allocation", HERE / "coordinator/rounds.py")
    source = args.merge / "pointers-result"
    selection = args.output / "selection"
    manifest = rounds.prepare(source, selection)
    assert manifest["count"] == 2
    assert (selection / "input.g6").read_bytes() == (source / "UNKNOWN.g6").read_bytes()
    with gzip.open(source / "records.jsonl.gz", "rb") as original:
        with gzip.open(selection / "unknown-records.jsonl.gz", "rb") as copied:
            assert original.read() == copied.read()
    codes = (selection / "input.g6").read_text().splitlines()
    for modulus in range(2, 100):
        buckets = {int.from_bytes(hashlib.sha256(code.encode()).digest()[:8], "big") % modulus for code in codes}
        if len(buckets) == 2:
            break
    else:
        raise AssertionError("no_two_nonempty_fixture_shards")

    def run(name, extra):
        output = args.output / (name + "-result")
        command = [sys.executable, "-B", str(HERE / "drive.py"), "run", "--index", str(args.index),
                   "--state", str(args.output / (name + "-state")), "--output", str(output),
                   "--input", str(selection / "input.g6"), "--policy", "cheap", "--intake-only"] + extra
        path = args.output / (name + ".log")
        with path.open("w") as stream:
            result = subprocess.run(command, stdout=stream, stderr=stream)
        assert result.returncode == 0, path.read_text()
        assert json.loads((output / "summary.json").read_text())["checker_status"] == "ACCEPT"
        return output

    bundles = []
    for bucket in sorted(buckets):
        bundles.append(run("worker-" + str(bucket), ["--shard-count", str(modulus), "--shard-index", str(bucket),
                       "--records", str(selection / "unknown-records.jsonl.gz"),
                       "--records", str(args.merge / "seed-records.jsonl")]))

    def positive():
        report = rounds.coverage(selection, bundles)
        assert report["coverage_status"] == "PASS" and report["count"] == 2
        assert report["certificates_rechecked"] is False

    positive()
    reds = []
    for bad, expected in [(bundles[:1], "round_union_coverage: missing=1 extra=0"),
                          (bundles + bundles[:1], "round_union_duplicate"),
                          (bundles + [args.merge / "seeds-result"], "round_union_coverage: missing=0 extra=2")]:
        try:
            rounds.coverage(selection, bad)
        except ValueError as exc:
            assert str(exc) == expected, str(exc)
            reds.append({"exact_message": str(exc), "positive_after": "PASS"})
        else:
            raise AssertionError("round_assignment_control_accepted")
        positive()
    extra = ["--bundle", str(source)]
    for path in bundles:
        extra += ["--bundle", str(path)]
    merged = run("merged", extra)
    summary = json.loads((merged / "summary.json").read_text())
    assert summary["counts"] == {"embedded": 1, "refuted": 1, "unknown": 0}
    assert rounds.prepare(merged, args.output / "empty-next-round")["count"] == 0
    report = {"status": "PASS", "before": {"embedded": 0, "refuted": 0, "unknown": 2},
              "after": summary["counts"], "history_bytes_preserved": True, "worker_bundles": "ACCEPT",
              "coordinator_replay": "ACCEPT", "empty_frontier": True, "controls": reds}
    write_json(args.output / "rounds.json", report)
    print(compact(report))


if __name__ == "__main__":
    main()
