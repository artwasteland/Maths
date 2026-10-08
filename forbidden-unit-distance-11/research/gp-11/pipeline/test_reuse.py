#!/usr/bin/env python3
"""Exercise a real TU dependency and rollback between decision and attempt writes."""
from common import *
import argparse
import gzip
import sqlite3
from graph6 import canonicalize, decode_graph6, pair_index
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
    tu = TU(poset)
    for code in (GP11 / "design/prototypes/tu-all-refuted.g6").read_text().splitlines():
        chain = tu.closure(code)
        if len(chain["steps"]) < 2:
            continue
        n, mask = decode_graph6(code)
        prefix = chain["steps"][:1]
        endpoint = canonicalize(n, mask | 1 << pair_index(n, *prefix[0]["pair"]))
        if endpoint.g6 in poset.ids:
            break
    else:
        raise AssertionError("no_real_two_step_fixture")
    gid = poset.ids[code]
    config = {"policy": "tu_dependency_control"}
    store = Store(args.output / "tu-state", poset, [gid], config, guard)
    info = {"g6": endpoint.g6, "old_to_new": list(endpoint.old_to_new), "steps": prefix,
            "end": None, "fixed_point": False}
    # A prefix is enough for transport; fixed-point closure is a search policy.
    store.db.execute("INSERT INTO tu_classes VALUES (?,?,?)", (gid, endpoint.g6, compact(info)))
    store.db.commit()
    assert tu.transport(code, info, store) is None
    tu.drain(store)
    assert not store.has(code)
    proposed, _ = tu.propose(endpoint.g6, store)
    assert proposed["verdict"] == "refuted"
    store.accept(proposed, "checked_endpoint")
    store.propagate(endpoint.g6)
    assert not store.has(code)
    tu.drain(store)
    assert store.decided[code] == "refuted"
    store.verify(store.record(code))
    assert store.record(code)["cert"]["end"]["refuted"] == endpoint.g6
    store.close()

    with gzip.open(GP11 / "embed/results/extension/architect-500/records.jsonl.gz", "rt") as source:
        embedding = next(row for line in source if (row := json.loads(line))["verdict"] == "embedded")
    gid = poset.ids[embedding["g6"]]
    config = {"policy": "transaction_control"}
    store = Store(args.output / "transaction-state", poset, [gid], config, guard)
    token = store.lease(gid, "fault", 60)
    store.db.execute("CREATE TRIGGER fault BEFORE INSERT ON attempts BEGIN SELECT RAISE(ABORT,'injected_transaction_fault'); END")
    store.db.commit()
    try:
        store.finish(gid, "fault", token, embedding, {}, 0, {})
    except sqlite3.IntegrityError as exc:
        assert str(exc) == "injected_transaction_fault"
    else:
        raise AssertionError("transaction_fault_not_injected")
    assert not store.has(embedding["g6"])
    assert store.db.execute("SELECT COUNT(*) FROM accepted").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0
    assert store.db.execute("SELECT token FROM leases").fetchone() == (token,)
    store.db.execute("DROP TRIGGER fault")
    store.db.commit()
    store.finish(gid, "fault", token, embedding, {}, 0, {})
    store.close()
    store = Store(args.output / "transaction-state", poset, [gid], config, guard, resume=True)
    store.replay()
    assert store.record(embedding["g6"]) == embedding
    assert store.counts() == {"embedded": 1, "refuted": 0, "unknown": 0}
    store.close()
    guard.stop.set()
    result = {"status": "PASS", "tu_input": code, "checked_endpoint": endpoint.g6,
              "bare_chain_remained_unknown": True, "checked_chain_transported": True,
              "decision_attempt_lease_transaction_rollback": True, "positive_after": "ACCEPT"}
    write_json(args.output / "reuse.json", result)
    print(compact(result))


if __name__ == "__main__":
    main()
