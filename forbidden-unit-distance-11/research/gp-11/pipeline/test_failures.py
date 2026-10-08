#!/usr/bin/env python3
"""A producer failure cannot hide an accepted endpoint or drop its task record."""
from common import *
import argparse
import sqlite3
from unittest.mock import patch
import drive
import stages
from poset import Poset
from store import Store
from tu import TU


def fixture(directory):
    db = sqlite3.connect(f"file:{directory / 'state/state.sqlite'}?mode=ro", uri=True)
    result = []
    with (directory / "state/certificates.jsonl").open("rb") as source:
        for origin, value, offset, length in db.execute(
                "SELECT origin,accepted.hash,offset,size FROM accepted JOIN blobs ON accepted.hash=blobs.hash ORDER BY seq"):
            source.seek(offset)
            raw = source.read(length)
            assert hashlib.sha256(raw).hexdigest() == value
            record = json.loads(raw)
            if record["verdict"] == "refuted" and origin != "propagation":
                result.append(record)
    db.close()
    return result


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
    poset = Poset(args.index)
    records = fixture(args.controls)
    endpoint = next(row for row in records if row["g6"] in poset.ids)
    root = poset.ids[endpoint["g6"]]
    child = next(poset.neighbours(root, "embedded"))[0]
    parent = next(poset.neighbours(root, "refuted"))[0]
    config = {"policy": "failure_control"}
    store = Store(args.output / "state", poset, [child, parent], config, guard)
    tu = TU(poset)
    for row in records:
        if row is not endpoint:
            store.accept(row, "support")

    def fail_after_endpoint(producer, code, stage):
        assert code == poset.codes[child]
        producer.store.accept(endpoint, stage.name + ":endpoint")
        raise MemoryError("injected_after_accepted_endpoint")

    with patch.dict(stages.POLICIES, failure_control=[stages.Stage("fault", "tu", 1)]):
        with patch.object(stages.Producers, "propose", fail_after_endpoint):
            stages.run(store, tu, "failure_control")
    assert store.counts() == {"embedded": 0, "refuted": 1, "unknown": 1}
    assert store.record(poset.codes[parent])["cert"]["type"] == "sub"
    assert store.db.execute("SELECT COUNT(*) FROM attempts").fetchone() == (1,)
    attempt = store.db.execute("SELECT hash FROM attempts").fetchone()[0]
    assert store.read(attempt)["cert"]["reason"] == "checker:MemoryError"
    for row in records:
        store.verify(row)
    store.verify(store.record(poset.codes[parent]))
    store.verify(store.unknown_record(child))

    raw = args.output / "oversized.jsonl"
    atomic(raw, compact(unknown(poset.codes[child], "x" * 300, {})) + "\n")
    try:
        with patch.object(drive, "MAX_RECORD", 128):
            drive.intake(store, [raw], tu)
    except ValueError as exc:
        assert str(exc) == "record_size_cap"
    else:
        raise AssertionError("oversized_record_accepted")
    atomic(raw, compact(endpoint) + "\n")
    drive.intake(store, [raw], tu)
    store.verify(endpoint)
    prior_budget = {"seconds": 17, "attempts": 2}
    atomic(raw, compact(unknown(poset.codes[child], "upstream_budget_exhausted", prior_budget)) + "\n")
    drive.intake(store, [raw], tu)
    history = store.unknown_record(child)["cert"]["budget"]["stages"]
    assert any(row["reason"] == "upstream_budget_exhausted" and row["budget"] == prior_budget for row in history)
    store.verify(store.unknown_record(child))
    store.close()
    guard.stop.set()

    stopped = args.output / "initial-floor"
    with patch.object(Guard, "check", side_effect=MemoryFloor("injected_initial_floor")):
        status = drive.main(["run", "--index", str(args.index), "--state", str(stopped),
                             "--output", str(args.output / "stopped-result"), "--sample", "1", "--policy", "cheap"])
    assert status == 75
    assert json.loads((stopped / "STOP.json").read_text())["reason"] == "MemoryFloor"
    assert not (args.output / "stopped-result/summary.json").exists()
    report = {"status": "PASS", "accepted_endpoint_propagated_after_parent_failure": True,
              "failed_task_record": "checker:MemoryError", "next_decided_task_skipped": True,
              "oversized_valid_json": "record_size_cap", "initial_memory_floor_exit": 75,
              "raw_unknown_reason_and_budget_preserved": True,
              "positive_after": "ACCEPT"}
    write_json(args.output / "failures.json", report)
    print(compact(report))


if __name__ == "__main__":
    main()
