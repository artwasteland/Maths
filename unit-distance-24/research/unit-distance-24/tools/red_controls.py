#!/usr/bin/env python3
"""Deployment controls on a retained (24,69) run; mutations never write through hard links.

Usage: red_controls.py RUN [--from-n 13] [--out DIR]
Each refusal must include its own exact PROBLEM/FAIL line.
The unchanged real evidence is checked again after every mutation.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import known_graphs as known
import worker

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("diff", ROOT / "research/unit-distance-23/tools/lean_diff.py")
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)
spec = importlib.util.spec_from_file_location("strict", Path(__file__).with_name("checker_diff.py"))
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)


def replace(path, data):
    tmp = path.with_name(path.name + ".red-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def faithful_copy(run, dest):
    shutil.copytree(run, dest, copy_function=os.link)
    for path in dest.rglob("*.json"):
        data = path.read_bytes()
        rebased = data.replace(str(run).encode(), str(dest).encode())
        if rebased != data:
            replace(path, rebased)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--from-n", type=int, default=13)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    run = a.run.resolve()
    args = ["--check", "--from-n", str(a.from_n), "--expect-target", "24", "69", "--expect-seed", "10",
            "--expect-slices", "12", "1920"]
    base = diff.child_peak(worker.CHECKER, run, args)
    assert base["code"] == 3 and base["out"].splitlines()[-1] == f"CHAIN PARTIAL (levels below {a.from_n} not inspected (--from-n {a.from_n}))", base
    cells = known.catalogue()
    clean_known = known.slice_control(run, cells)
    assert clean_known["result"] == "OK"
    reports = []

    def recheck():
        now = diff.child_peak(worker.CHECKER, run, args)
        assert all(now[k] == base[k] for k in ("code", "out", "err")), "real checker verdict changed"
        assert known.slice_control(run, cells) == clean_known, "real control verdict changed"

    with tempfile.TemporaryDirectory(prefix="u24-deployment-red-", dir=a.out) as tmp:
        clone = Path(tmp) / run.name
        faithful_copy(run, clone)
        faithful = diff.child_peak(worker.CHECKER, clone, args)
        assert faithful["code"] == base["code"], faithful
        cases = [("u-bar(24) changed without override", lambda r: r["ubar"].__setitem__("24", 71),
                  "PROBLEM: reach.json u-bar(24) = 71 is not the built-in 72 and no override is recorded"),
                 ("override below the known lower bound", lambda r: (r["ubar"].__setitem__("24", 67),
                   r["ubar_override"].__setitem__("24", {"builtin": 72, "value": 67})),
                  "PROBLEM: reach.json override of u-bar(24) {'builtin': 72, 'value': 67} is not a lowering of 72 to at least the known lower bound 68"),
                 ("unjustified root k 6", lambda r: r.__setitem__("root_k", 6),
                  "PROBLEM: reach.json root k 6 is not justified: Schade's bound is 69 - u-bar(23) = 5, and no lemma is recorded for (24,69)")]
        path = clone / "reach.json"
        original = path.read_bytes()
        for name, mutate, want in cases:
            try:
                r = json.loads(original)
                mutate(r)
                replace(path, (json.dumps(r) + "\n").encode())
                red = diff.child_peak(worker.CHECKER, clone, args)
                assert red["code"] == 1 and want in red["out"].splitlines(), red
                reports.append({"control": name, "rule": want})
                print(name + ": " + want, flush=True)
            finally:
                replace(path, original)
            recheck()
        cell = diff.pruned_cell(clone, a.from_n)
        assert cell is not None, "no inspected cell for lean_diff's faults"
        for name, rel, change, _ in diff.faults(clone, cell):
            path = clone / rel
            original = path.read_bytes()
            try:
                strict.active.update(cell=cell, name=name, rel=rel, original=original)
                replace(path, change(original))
                want = strict.expected(clone)
                red = diff.child_peak(worker.CHECKER, clone, args)
                assert red["code"] == 1 and want in red["out"].splitlines(), (want, red)
                reports.append({"control": name, "rule": want})
                print(name + ": " + want, flush=True)
            finally:
                replace(path, original)
            recheck()
        matches = [(name, row["files"]["keep"]["indices"]) for name, row in clean_known["cells"].items()
                   if row["files"]["keep"] and row["files"]["keep"]["indices"]]
        seeded = not matches
        if seeded:
            # A light pilot may hit no Engel form. Make the positive premise explicit
            # in a real, inspected cell before testing the independent control's rule.
            name, c = next((name, c) for name, c in cells.items() if c["eligible_indices"])
            indices = [min(c["eligible_indices"])]
        else:
            name, indices = matches[0]
        index = indices[0]
        code = next(code for code, i in cells[name]["codes"].items() if i == index)
        paths = [clone / f"{name}.keep.g6", clone / f"{name}.certs.jsonl"]
        originals = [p.read_bytes() for p in paths]
        seed_originals = {}
        try:
            if seeded:
                for suffix in (".g6", ".reach.g6", ".keep.g6", ".certs.jsonl"):
                    p = clone / (name + suffix)
                    seed_originals[p] = p.read_bytes()
                    extra = ((json.dumps({"g6": code.decode(), "verdict": "unknown"}) + "\n").encode()
                             if suffix == ".certs.jsonl" else code + b"\n")
                    replace(p, seed_originals[p] + extra)
                positive = known.slice_control(clone, cells)
                assert positive["result"] == "OK" and index in positive["cells"][name]["files"]["keep"]["indices"]
                print(f"KNOWN positive fixture: no Engel form found in this pilot; seeded {name} index {index} in full/reach/keep and certificates before its removal", flush=True)
            replace(paths[0], b"".join(l for l in paths[0].read_bytes().splitlines(keepends=True) if l != code + b"\n"))
            replace(paths[1], b"".join(l for l in paths[1].read_bytes().splitlines(keepends=True) if json.loads(l)["g6"].encode() != code))
            red = known.slice_control(clone, cells)
            want = f"PRUNED {name}: Engel indices in reach but not keep: [{index}]"
            assert red["result"] == "FAIL" and red["problems"] == [want], red
            # Removing both cannot fail the keep-versus-certificates list rule.
            kept = [json.loads(l)["g6"].encode() for l in paths[1].read_bytes().splitlines()
                    if json.loads(l)["verdict"] in ("embedded", "unknown")]
            assert paths[0].read_bytes().splitlines() == kept
            reports.append({"control": "Engel form removed from keep and certificates", "rule": "FAIL: " + want,
                            "seeded_positive_fixture": seeded})
            print("known graph removed: FAIL: " + want, flush=True)
        finally:
            for path, original in zip(paths, originals):
                replace(path, original)
            for path, original in seed_originals.items():
                replace(path, original)
        recheck()
        prefix = run.parent / ("prefix-24-69" + worker.KEY)
        assert worker.prefix_diff(prefix, clone).startswith("identical,")
        path = next(p for p in sorted(clone.glob("12-*.g6"))
                    if p.name.count(".") == 1 and p.stat().st_size)
        original = path.read_bytes()
        try:
            replace(path, original[:1] + bytes([original[1] ^ 1]) + original[2:])
            want = "PREFIX: differs: " + path.name
            try:
                worker.prefix_diff(prefix, clone)
            except ValueError as error:
                assert str(error) == want
            else:
                raise AssertionError("prefix corruption accepted")
            reports.append({"control": "one byte of the later prefix changed", "rule": "FAIL: " + want})
            print("prefix byte changed: FAIL: " + want, flush=True)
        finally:
            replace(path, original)
        assert worker.prefix_diff(prefix, clone).startswith("identical,")
        recheck()
    if a.out:
        (a.out / "red-controls.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(f"U24 RED-CONTROLS OK: {len(reports)} exact rules asserted; real evidence rechecked after each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
