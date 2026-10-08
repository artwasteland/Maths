#!/usr/bin/env python3
"""Use the existing lean_diff harness on lean versus u24, without editing its G5 pin.

Arguments are lean_diff.py's; defaults compare the two streaming checkers.
--faults also asserts each fault's own PROBLEM text and rechecks clean evidence.
"""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ENUM = ROOT / "research/unit-distance-22/enum"
spec = importlib.util.spec_from_file_location("lean_diff", ROOT / "research/unit-distance-23/tools/lean_diff.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
LEAN = ENUM / "verify-chain-lean.py"
U24 = ENUM / "verify-chain-u24.py"
harness.G5_SHA256 = "6658191122188546847b7f13d0413be954bb131491556520ccfd90e8660c30e6"
original_faults = harness.faults
original_child = harness.child_peak
active = {}
baseline = {}


def faults(run, cell):
    out = []
    for name, rel, change, differently in original_faults(run, cell):
        def plant(data, name=name, rel=rel, change=change):
            active.update(run=run, cell=cell, name=name, rel=rel, original=data)
            return change(data)
        out.append((name, rel, plant, differently))
    return out


def expected(run):
    n, m = active["cell"]
    name, rel = active["name"], active["rel"]
    certs = f"{n}-{m}.certs.jsonl"
    rows = active["original"].splitlines()
    if name == "a certificate's g6 changed":
        stage = f"{n}-{m}.reach.g6" if (run / f"{n}-{m}.reach.g6").exists() else f"{n}-{m}.g6"
        return f"PROBLEM: {certs}: record list is not the stage input {stage}"
    if name == "a verdict renamed":
        return f"PROBLEM: {certs}: verdict bogus for {json.loads(rows[0])['g6']}"
    if name == "a refuted or tu record's witness removed":
        r = next(json.loads(l) for l in rows if json.loads(l).get("verdict") in ("tu", "refuted"))
        return f"PROBLEM: {certs}: pruned graph {r['g6']} has no witness"
    if name == "a keep line dropped":
        return f"PROBLEM: {n}-{m}.keep.g6: is not the embedded and unknown records in order"
    if name == "a parent source changed":
        return f"PROBLEM: {n}-{m}: parent source {Path(rel).name} hash differs from the manifest"
    if name == "the certificate file without its final newline":
        return f"PROBLEM: required cell ({n},{m}) could not be checked: Bad('{run / certs}: missing final newline')"
    if name == "a non-ASCII byte in the certificate file":
        raw = (run / certs).open("rb").readline()[:-1]
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as error:
            return f"PROBLEM: required cell ({n},{m}) could not be checked: {error!r}"
    raise AssertionError(name)


def child(checker, run, args):
    r = original_child(checker, run, args)
    key = (str(checker), str(run), tuple(args))
    if not active:
        baseline[key] = r
    else:
        want = expected(run)
        assert r["code"] == 1 and want in r["out"].splitlines(), (active["name"], want, r["out"])
        if checker == U24:
            print("    rule asserted:", want)
            for c in (LEAN, U24):
                clean = original_child(c, active["run"], args)
                before = baseline[(str(c), str(active["run"]), tuple(args))]
                assert all(clean[k] == before[k] for k in ("code", "out", "err")), "control leaked into real evidence"
            active.clear()
    return r


def main():
    harness.faults = faults
    harness.child_peak = child
    sys.argv[1:1] = ["--g5", str(LEAN), "--lean", str(U24)]
    return harness.main()


if __name__ == "__main__":
    raise SystemExit(main())
