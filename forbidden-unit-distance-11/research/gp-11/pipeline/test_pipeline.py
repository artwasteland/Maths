#!/usr/bin/env python3
"""Rule-specific controls, always followed by replay of the positive parent."""
from common import *
import argparse
import copy
import gzip
from poset import Poset
from store import Store
from tu import TU


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    limits(args.output / "scratch")
    guard = Guard()
    guard.start()
    poset = Poset(args.index)
    tu = TU(poset)
    with gzip.open(GP11 / "embed/results/extension/architect-500/records.jsonl.gz", "rt") as source:
        for line in source:
            embedding = json.loads(line)
            if embedding["verdict"] == "embedded":
                eid = poset.ids[embedding["g6"]]
                down = list(poset.neighbours(eid, "embedded"))
                if down:
                    break
    child, _ = down[0]
    refuted = None
    for code in (GP11 / "design/prototypes/tu-all-refuted.g6").read_text().splitlines():
        rid = poset.ids[code]
        up = list(poset.neighbours(rid, "refuted"))
        rdown = list(poset.neighbours(rid, "embedded"))
        if up and rdown:
            refuted = code
            break
    assert refuted is not None
    parent, _ = up[0]
    assigned = [eid, child, rid, parent]
    config = {"policy": "controls", "assigned_ids": sorted(assigned)}
    store = Store(args.output / "state", poset, assigned, config, guard)
    reds = []
    try:
        store.accept(embedding, "control")
        store.propagate(embedding["g6"])
        negative, _ = tu.propose(refuted, store)
        store.accept(negative, "control")
        store.propagate(refuted)
        eptr = store.record(poset.codes[child])
        rptr = store.record(poset.codes[parent])
        assert eptr["cert"]["type"] == "super"
        assert rptr["cert"]["type"] == "sub"

        def positive():
            for record in (embedding, eptr, negative, rptr):
                store.verify(record)
            assert store.counts() == {"embedded": 2, "refuted": 2, "unknown": 0}
            return dict(store.counts())

        def red(name, record, expected):
            # Parse exactly the serialized mutation: all reds are valid JSON.
            record = store.ck.loads(compact(record))
            try:
                store.verify(record)
            except store.ck.Rejection as exc:
                assert exc.reason == expected, (name, str(exc))
                message = str(exc)
            else:
                raise AssertionError("red_accepted:" + name)
            reds.append({"control": name, "reason": expected, "exact_message": message,
                         "valid_json": True, "positive_after": positive()})

        bad = copy.deepcopy(eptr)
        found = False
        for a in range(11):
            for b in range(a):
                altered = copy.deepcopy(eptr)
                altered["cert"]["map"][a], altered["cert"]["map"][b] = altered["cert"]["map"][b], altered["cert"]["map"][a]
                try:
                    store.check.verify(altered)
                except store.ck.Rejection as exc:
                    if exc.reason == "map_not_edge_preserving":
                        bad = altered
                        found = True
                        break
            if found:
                break
        assert found
        red("E-ptr_wrong_map", bad, "map_not_edge_preserving")
        bad = copy.deepcopy(rptr)
        bad["g6"] = poset.codes[rdown[0][0]]
        red("R-propagation_downward", bad, "map_not_edge_preserving")
        bad = copy.deepcopy(negative)
        bad["cert"]["end"] = None
        red("TU_without_endpoint", bad, "tu_end")
        bad = copy.deepcopy(eptr)
        bad["verdict"] = "refuted"
        red("propagated_verdict_disagreement", bad, "embedded_refuted_conflict")

        fixture = args.output / "coverage"
        fixture.mkdir()
        codes = sorted([embedding["g6"], eptr["g6"]])
        atomic(fixture / "input.g6", "".join(code+"\n" for code in codes))
        atomic(fixture / "UNKNOWN.g6", "")
        write_json(fixture / "run.json", {"profile": "sample", "input": "input.g6",
                    "input_sha256": digest(fixture / "input.g6"), "records": ["records.jsonl"], "derive": False})
        good = "".join(compact(record)+"\n" for record in (embedding, eptr))
        atomic(fixture / "records.jsonl", good)
        assert store.ck.Run(fixture, emit=lambda _: None).execute()["status"] == "ACCEPT"
        atomic(fixture / "records.jsonl", compact(embedding)+"\n")
        report = store.ck.Run(fixture, emit=lambda _: None).execute()
        assert report["status"] == "REJECT" and report["reason"] == "coverage", report
        atomic(fixture / "records.jsonl", good)
        assert store.ck.Run(fixture, emit=lambda _: None).execute()["status"] == "ACCEPT"
        reds.append({"control": "missing_graph", "reason": "coverage", "exact_message": report["detail"],
                     "valid_json": True, "positive_after": positive()})

        token = store.lease(eid, "lease_control", -1)
        assert store.expire() == 1
        assert store.expire() == 0
        replacement = store.lease(eid, "lease_control", 30)
        assert replacement != token
        try:
            store.finish(eid, "lease_control", token, embedding, {}, 0, {})
        except ValueError as exc:
            assert str(exc) == "stale_lease"
        else:
            raise AssertionError("stale_lease_accepted")
        positive()
        before = digest(store.directory / "certificates.jsonl")
        value = store.db.execute("SELECT hash FROM accepted WHERE g6=?", (eptr["g6"],)).fetchone()[0]
        offset, size = store.db.execute("SELECT offset,size FROM blobs WHERE hash=?", (value,)).fetchone()
        with (store.directory / "certificates.jsonl").open("r+b") as stream:
            stream.seek(offset)
            raw = stream.read(size)
            altered = raw.replace(b'"type":"super"', b'"type":"surer"', 1)
            assert altered != raw and len(altered) == len(raw)
            store.ck.loads(altered)
            stream.seek(offset)
            stream.write(altered)
        try:
            store.read(value)
        except ValueError as exc:
            assert str(exc) == "certificate_hash_mismatch"
        else:
            raise AssertionError("stale_certificate_hash_accepted")
        with (store.directory / "certificates.jsonl").open("r+b") as stream:
            stream.seek(offset)
            stream.write(raw)
        assert digest(store.directory / "certificates.jsonl") == before
        positive()
        saved_decisions = dict(store.decided)
        root_hash = store.db.execute("SELECT hash FROM accepted WHERE g6=?", (embedding["g6"],)).fetchone()[0]
        store.db.execute("UPDATE accepted SET hash=? WHERE g6=?", (root_hash, eptr["g6"]))
        store.db.commit()
        try:
            store.replay()
        except ValueError as exc:
            assert str(exc) == "accepted_index_mismatch"
        else:
            raise AssertionError("mismatched_index_graph_accepted")
        store.db.execute("UPDATE accepted SET hash=? WHERE g6=?", (value, eptr["g6"]))
        store.db.commit()
        store.decided = saved_decisions
        store.replay()
        positive()
        write_json(args.output / "controls.json", {"status": "PASS", "red_controls": reds,
                   "expired_lease_requeued_once": True, "stale_lease_rejected": True, "tampered_certificate_rejected": True,
                   "tampered_hash_fixture_valid_json": True,
                   "mismatched_index_graph": "accepted_index_mismatch", "positive_after_index_control": "ACCEPT"})
        print(compact(reds), flush=True)
    finally:
        store.close()
        guard.stop.set()


if __name__ == "__main__":
    main()
