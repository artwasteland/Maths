#!/usr/bin/env python3
"""A repeated merge must retain distinct attempts without multiplying old history."""
from common import *
import argparse
from drive import intake
from poset import Poset
from store import Store
from tu import TU


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    limits(args.output / "scratch")
    guard = Guard()
    guard.start()
    poset = Poset(args.index)
    code = poset.codes[0]
    store = Store(args.output / "state", poset, [0], {"policy": "history_control"}, guard)
    tu = TU(poset)
    stage = {"stage": "tree", "outcome": "unknown", "reason": "state_budget", "budget": {"nodes": 12}}
    paths = []
    earlier = []
    for number in range(1, 4):
        # Identical method/budget/outcome can still be three different attempts.
        record = unknown(code, "stages_exhausted", {"stages": earlier + [stage]})
        path = args.output / f"round-{number}.jsonl"
        atomic(path, compact(record) + "\n")
        paths.append(path)
        intake(store, [path], tu)
        output = store.unknown_record(0)
        store.verify(output)
        earlier = output["cert"]["budget"]["stages"]
        assert len(earlier) == number, "history_duplicate_ancestor"
        assert len({row["prior_run"] for row in earlier}) == number
        assert all({k: v for k, v in row.items() if k != "prior_run"} == stage for row in earlier)
    before = compact(store.unknown_record(0))
    intake(store, list(reversed(paths)), tu)
    assert compact(store.unknown_record(0)) == before
    store.close()
    # The same certificate history survives a process restart and another import.
    resumed = Store(args.output / "state", poset, [0], {"policy": "history_control"}, guard, True)
    resumed.replay()
    intake(resumed, paths, tu)
    assert compact(resumed.unknown_record(0)) == before
    resumed.verify(resumed.unknown_record(0))
    resumed.close()
    guard.stop.set()
    report = {"status": "PASS", "rounds": 3, "distinct_attempts_preserved": 3,
              "duplicate_ancestor_history_removed": True, "repeated_import_identical": True,
              "resume_identical": True, "unknown_record": "ACCEPT"}
    write_json(args.output / "history.json", report)
    print(compact(report))


if __name__ == "__main__":
    main()
