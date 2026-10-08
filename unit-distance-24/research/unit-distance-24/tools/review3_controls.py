#!/usr/bin/env python3
"""Third-review controls from retained evidence; no enumeration or git writes.

Run under worker.measured with U24_MIN_AVAILABLE_MB=1536. Envelopes are checked
independently before each fault, and the original evidence must pass afterwards.
"""
import argparse
import copy
import os
from pathlib import Path
import re
import shutil
import sys
from unittest.mock import patch

import evidence as e
import receipt_audit as audit
from rereview_controls import atomic_replace, dump, inventory, seal, write_inventory
import worker


def envelope(result, text):
    structure = e.load(text.with_suffix(".structure.json"))
    for label, suffix in (("structure receipt", ".structure.json"), ("inventory", ".inventory.jsonl.gz"),
                          ("known receipt", ".known.json")):
        assert re.search(r"^# " + label + ": sha256 " + e.sha(text.with_suffix(suffix)) + ",", text.read_text(), re.M)
    assert structure["run_summary_sha256"] == e.sha(result / "run-summary.json")
    for name, digest in structure["retained"].items():
        assert e.sha(result / name) == digest, name
    for row in inventory(text.with_suffix(".inventory.jsonl.gz")):
        name = row.get("path", "")
        path = result / name
        if name and path.is_file():
            raw = path.read_bytes()
            assert row["sha256"] == e.sha(path) and row["bytes"] == len(raw) and row["newlines"] == raw.count(b"\n"), name
    return structure


def sync(result, text, structure, changed):
    ip = text.with_suffix(".inventory.jsonl.gz")
    rows = inventory(ip)
    for name in changed:
        path = result / name
        raw = path.read_bytes()
        structure["retained"][name] = e.sha(path)
        for row in rows:
            if row.get("path") == name:
                row.update(sha256=e.sha(path), bytes=len(raw), newlines=raw.count(b"\n"))
    write_inventory(ip, rows)
    structure["run_summary_sha256"] = e.sha(result / "run-summary.json")
    sp = text.with_suffix(".structure.json")
    dump(sp, structure)
    seal(text, sp, ip)
    envelope(result, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=Path("/tmp/u24-fixes-yE1TRr/worker"))
    ap.add_argument("--rereview", type=Path, default=Path("/tmp/u24-rereview-fixes-xJ9521/real-worker"))
    ap.add_argument("--review3", type=Path, default=Path("/tmp/u24-review3-bd1e5bcc1a"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    reports = []

    def paths(root, index=1907, tag="fixcheck"):
        return root / f"res/24-69-L12-tri-pf74/s{index}of1920", root / f"res/check/s{index}of1920-{tag}.txt"

    def green(index=1907):
        if worker.available_mb() < 1536:
            raise RuntimeError("MEMORY STOP: MemAvailable below 1536 MiB")
        result, text = paths(a.source, index)
        s = audit.validate(result, text)
        prefix = audit.validate(*paths(a.source)) if index != 1907 else None
        assert e.g4(a.source / f"out/dag-24-69-L12-tri-pf74-s{index}of1920", result, s,
                    whole=index == 1907, prefix=prefix)["result"] == "PASS"
        assert s["target_files"][".keep.g6"]["records"] == 0
        worker.verified_marker(a.source / f"out/checked-24-69-L12-tri-pf74-s{index}of1920.json",
                               e.sha(worker.CHECKER), False, [12, index, 1920])
        return s

    def red(name, action, want, index=1907):
        try:
            action()
        except ValueError as error:
            assert str(error) == want, (name, want, str(error))
        else:
            raise AssertionError(name + ": mutation accepted")
        print("REVIEW3 red: " + want, flush=True)
        green(index)
        print(f"REVIEW3 green: {name}: original {index} evidence and marker pass, measured survivors 0", flush=True)
        reports.append({"control": name, "output": want})

    def setup(name, index=1907, source=None):
        root = a.out / name
        shutil.copytree((source or a.source) / "res", root / "res")
        result, text = paths(root, index)
        return root, result, text, envelope(result, text)

    base = green()
    green(1444)
    # Use the exact third-review mutation: full prefix/seed/red records removed,
    # slice-mode totals and manifest fingerprint recomputed, all envelopes valid.
    root, result, text, s = setup("g4-downgrade", source=a.review3 / "extra/g4-downgrade")
    want = "G4: whole check requires a full-mode replay"
    red("whole receipt downgraded", lambda: audit.validate(result, text), want)
    red("whole worker downgraded", lambda: e.g4(a.source / "out/dag-24-69-L12-tri-pf74-s1907of1920", result, s), want)

    # Detailed seed/red outcomes still have to establish the full-mode claims.
    for name in ("seed-not-recomputed", "red-not-red"):
        root, result, text, s = setup(name)
        sm = e.load(result / "replay/summary.json")
        changed = ["replay/summary.json"]
        if name == "seed-not-recomputed":
            seed = next(v for v in sm["seeds"] if v["cell"].startswith("10-"))
            seed["full_check"] = False
            want = (f"G4 SCOPE: a full G4 replay whose seed cell {seed['cell']} is not recomputed in full over its "
                    f"{seed['records']} audited graphs: records {seed['records']}, enum2 {seed['enum2_records']}")
        else:
            sm["red_controls"][0].update(only_production=0, only_enum2=0)
            dump(result / "replay/red.json", sm["red_controls"])
            changed.append("replay/red.json")
            want = "G4 SCOPE: a full G4 replay whose red controls ['R1'] are not red by their own recorded outcome"
        dump(result / "replay/summary.json", sm)
        sync(result, text, s, changed)
        red(name, lambda: audit.validate(result, text), want)

    root, result, text, s = setup("different-prefix", 1444)
    s["g4"]["prefix_fingerprint"] = "0" * 64
    dump(result / "replay/fingerprint.json", s["g4"])
    sync(result, text, s, ["replay/fingerprint.json"])
    red("different replay prefix", lambda: audit.validate(result, text),
        "G4: slice-mode prefix fingerprint differs from passed full replay", 1444)
    result0, _ = paths(a.source, 1444)
    s0 = e.load(paths(a.source, 1444)[1].with_suffix(".structure.json"))
    red("slice worker without full anchor", lambda: e.g4(None, result0, s0, whole=False),
        "G4: slice-mode replay requires a passed full-mode prefix replay", 1444)

    root, result, text, s = setup("reach-k", 1444, a.review3 / "extra/reach-k")
    want = "PARAMETERS: 20-49 reach k: metadata 99 != derived 4"
    red("reach k receipt", lambda: audit.validate(result, text), want, 1444)
    run = root / "run"
    shutil.copytree(a.source / "out/dag-24-69-L12-tri-pf74-s1444of1920", run, copy_function=os.link)
    atomic_replace(run / "run-summary.json", (result / "run-summary.json").read_bytes())
    e.retained_files(run, result)  # the rest of the copy policy is still satisfied
    red("reach k worker", lambda: e.reconcile(run, result, 13, base), want, 1444)

    # Cover parameters on seed, resumed-prefix, resumed-upper and target entries,
    # and the other summary stage identities (replay's stage_fields is also used).
    for cell in ((10, 14), (11, 17), (17, 37), (24, 69)):
        root, result, text, s = setup(f"reach-{cell[0]}-{cell[1]}", 1444)
        raw = e.load(result / "run-summary.json")
        for sm in (raw, s["summary"]):
            row = next(v for v in sm["levels"] if (v["n"], v["m"]) == cell)
            expected = row["reach"]["k"]
            row["reach"]["k"] = 99
        dump(result / "run-summary.json", raw)
        sync(result, text, s, ["run-summary.json"])
        red(f"reach k {cell}", lambda: audit.validate(result, text),
            f"PARAMETERS: {cell[0]}-{cell[1]} reach k: metadata 99 != derived {expected}", 1444)
    for field, value, want in (
            ("prune", "20-49.g6", "PARAMETERS: 20-49 prune source: metadata '20-49.g6' != derived '20-49.reach.g6'"),
            ("reach_k", 99, "PARAMETERS: 20-49 reach_k: metadata 99 != derived 4"),
            ("verify", "full", "RECORDS: 20-49: verification must read keep")):
        root, result, text, s = setup("stage-" + field, 1444)
        raw = e.load(result / "run-summary.json")
        for sm in (raw, s["summary"]):
            row = next(v for v in sm["levels"] if (v["n"], v["m"]) == (20, 49))
            if field == "reach_k":
                row[field] = value
            else:
                row[field]["source" if field == "prune" else "stage_kind"] = value
        dump(result / "run-summary.json", raw)
        sync(result, text, s, ["run-summary.json"])
        red("stage " + field, lambda: audit.validate(result, text), want, 1444)

    # The exact older marker accepted by the third reviewer despite a false target
    # count; rebase its paths and hashes together, without changing the fault.
    root, result, text, s = setup("old-marker", source=a.review3 / "extra/same-slice-bad-marker")
    marker = e.load(a.review3 / "extra/same-slice-bad-marker/marker.json")
    marker.update(text_receipt=str(text), structure_receipt=str(text.with_suffix(".structure.json")),
                  receipts={str(text.with_suffix(suffix)): e.sha(text.with_suffix(suffix)) for suffix in
                            (".txt", ".structure.json", ".known.json", ".inventory.jsonl.gz")})
    mp = root / "marker.json"
    want = ("MARKER: worker/evidence hashes differ; current receipt audit rejected bound bundle: "
            "COUNTS: structure 24-69.keep.g6 records: metadata 777 != checked files 0")
    for variant in ("missing", "worker_sha256", "evidence_sha256"):
        changed = copy.deepcopy(marker)
        if variant != "missing":
            changed.update(worker.implementation_hashes())
            changed[variant] = "0" * 64
        dump(mp, changed)
        red("old marker " + variant, lambda: worker.verified_marker(mp, e.sha(worker.CHECKER), False), want)
    # The restart path must refuse before starting a child or deleting the run.
    out = root / "out"
    out.mkdir()
    shutil.copyfile(mp, out / "checked-24-69-L12-tri-pf74-s1907of1920.json")
    with patch.dict(os.environ, dict(TAG="review3", U23_OUT=str(out), U23_RES=str(root / "res"), U23_PUSH="0",
                                    U23_TOOLCHAIN="0", U24_KEEP_RUNS="1", U24_SKIP_RUNBOOK="1",
                                    U24_CHECKER_SHA256=e.sha(worker.CHECKER))), \
            patch.object(sys, "argv", ["worker.py", "1907"]), \
            patch.object(worker, "measured", side_effect=AssertionError("must refuse before starting a child")), \
            patch.object(worker.shutil, "rmtree", side_effect=AssertionError("must refuse before deleting")):
        red("old marker restart", worker.main, want)

    # Both legacy workers' honest bundles remain valid, as does the fast path for
    # a marker bearing both current hashes.
    result, text = paths(a.rereview, 1444, "rereview")
    assert audit.validate(result, text)["result"] == "OK"
    old = a.rereview / "out/checked-24-69-L12-tri-pf74-s1444of1920.json"
    worker.verified_marker(old, e.sha(worker.CHECKER), False, result_root=a.rereview / "res")
    print("REVIEW3 compatibility: ccfce9dc5f whole/partial and bd1e5bcc1a partial receipts and markers accepted", flush=True)
    current = e.load(a.source / "out/checked-24-69-L12-tri-pf74-s1907of1920.json")
    current.update(worker.implementation_hashes())
    dump(a.out / "current-marker.json", current)
    with patch.object(audit, "validate", side_effect=AssertionError("current marker should use its hashes")):
        worker.verified_marker(a.out / "current-marker.json", e.sha(worker.CHECKER), False)
    dump(a.out / "review3-controls.json", reports)
    print(f"REVIEW3 CONTROLS OK: {len(reports)} exact refusals; original evidence passed after every red", flush=True)


if __name__ == "__main__":
    main()
