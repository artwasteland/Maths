#!/usr/bin/env python3
"""Reproduce the seven review findings using retained evidence, never enumeration or git writes.

Defaults name the retained evidence from the review. Each refusal asserts its exact
new rule and reruns the same check on the unmutated evidence before continuing.
Run this under worker.measured with U24_MIN_AVAILABLE_MB=1536 on small machines.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import evidence
import known_graphs as known
import red_controls
import worker


def mirror_result(run, original, dest):
    """Reproduce the runbook's copy step after rebasing a scratch run's JSON paths."""
    shutil.copytree(original, dest)
    for p in list(dest.iterdir()):
        if p.is_file() and (run / p.name).is_file():
            shutil.copyfile(run / p.name, p)
    for p in run.glob("*.verify.manifest.json"):
        shutil.copyfile(p, dest / "verify" / p.name)
    summary = evidence.load(run / "run-summary.json")
    (dest / "counts.json").write_text(json.dumps([[e["n"], e["m"], e.get("children"),
                   (e.get("prune") or {}).get("counts")] for e in summary["levels"]]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pilot", type=Path, default=Path("/tmp/u24-worker-check-oo1ip077/pilot"))
    ap.add_argument("--resumed", type=Path, default=Path("/tmp/u24-adversarial-yqotkysv/resumed-1444"))
    ap.add_argument("--legacy", type=Path, default=Path("/tmp/u24-pilot-check-f4ha3hb2/after/runbook-17-43"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    reports = []
    run = a.pilot / "out/dag-24-69-L12-tri-pf74-s1907of1920"
    result = a.pilot / "res/24-69-L12-tri-pf74/s1907of1920"

    def red(name, action, want, green):
        try:
            action()
        except ValueError as error:
            assert str(error) == want, (name, want, str(error))
        else:
            raise AssertionError(f"{name}: mutation accepted")
        print("REVIEW red: " + want, flush=True)
        green()
        print("REVIEW green: " + name + ": original passing result restored", flush=True)
        reports.append({"control": name, "output": want})

    # The review's syntactically valid false-zero metadata, with actual nonempty target files.
    legacy = a.legacy / "out/dag-17-43-s0of3"
    legacy_result = a.legacy / "res/17-43/s0of3"
    clone = a.out / "zero-run"
    red_controls.faithful_copy(legacy, clone)
    copied = a.out / "zero-result"
    mirror_result(clone, legacy_result, copied)
    original_summary = (clone / "run-summary.json").read_bytes()
    summary = json.loads(original_summary)
    entry = next(e for e in summary["levels"] if (e["n"], e["m"]) == (17, 43))
    entry["children"] = 0
    for key in ("input", "kept", "dropped"):
        if key in entry["reach"]:
            entry["reach"][key] = 0
    for key in entry["prune"]["counts"]:
        entry["prune"]["counts"][key] = 0
    for shard in entry.get("shards", []):
        shard["children"] = 0
    for directory in (clone, copied):
        red_controls.replace(directory / "run-summary.json", (json.dumps(summary) + "\n").encode())
    hashes = evidence.load(copied / "hashes.json")
    for name, value in hashes["files"].items():
        if name.startswith("17-43."):
            value["records"] = 0
    (copied / "hashes.json").write_text(json.dumps(hashes))
    digest = evidence.hash_records(legacy, legacy_result)
    def green_hashes():
        assert evidence.hash_records(legacy, legacy_result) == digest
    red("zeroed hashes counts", lambda: evidence.hash_records(clone, copied),
        "COUNTS: hashes.json 17-43.UNKNOWN.g6 records: metadata 0 != checked files 1", green_hashes)
    # Keep hashes honest in the summary-only mutation so removing reconciliation makes it pass.
    shutil.copyfile(legacy_result / "hashes.json", copied / "hashes.json")
    (copied / "counts.json").write_text(json.dumps([[e["n"], e["m"], e.get("children"),
                          (e.get("prune") or {}).get("counts")] for e in summary["levels"]]))
    baseline_legacy = evidence.reconcile(legacy, legacy_result)
    def green_summary():
        assert evidence.reconcile(legacy, legacy_result) == baseline_legacy
    red("zeroed summary counts", lambda: evidence.reconcile(clone, copied),
        "COUNTS: 17-43 children: metadata 0 != checked files 1", green_summary)
    # Every prune count is checked independently; compensating totals cannot hide a changed category.
    cell = "17-37"
    original = next(e for e in evidence.load(run / "run-summary.json")["levels"] if (e["n"], e["m"]) == (17, 37))
    actual = evidence.prune_counts(run, cell, evidence.Files(run), "triangles")
    assert actual == original["prune"]["counts"]
    for key, count in actual.items():
        changed = copy.deepcopy(original)
        changed["prune"]["counts"][key] = count + 1
        want = f"COUNTS: {cell} prune {key}: metadata {count + 1} != checked files {count}"
        def green_prune():
            assert evidence.checked_prune(run, original, evidence.Files(run), "triangles") == actual
        red("prune " + key, lambda: evidence.checked_prune(run, changed, evidence.Files(run), "triangles"), want, green_prune)

    def skip_without_keep():
        with patch.dict(os.environ, {"TAG": "review", "U23_PUSH": "1", "U24_SKIP_RUNBOOK": "1", "U24_KEEP_RUNS": "0"}), \
                patch.object(sys, "argv", ["worker.py", "1907"]), \
                patch.object(worker, "measured", side_effect=AssertionError("must refuse before starting any child")), \
                patch.object(worker, "push_receipt", side_effect=AssertionError("must refuse before git")), \
                patch.object(worker.shutil, "rmtree", side_effect=AssertionError("must refuse before deletion")):
            worker.main()
    base = evidence.reconcile(run, result)
    base["g4"] = evidence.g4(run, result, base)
    assert base["g4"]["result"] == "PASS"
    def green_g4():
        assert evidence.g4(run, result, base)["result"] == "PASS" and run.is_dir()
    red("skip-runbook deletion", skip_without_keep, "RUNBOOK: U24_SKIP_RUNBOOK=1 requires U24_KEEP_RUNS=1", green_g4)

    damaged = a.out / "damaged-result"
    shutil.copytree(result, damaged)
    hashes = evidence.load(damaged / "hashes.json")
    hashes["files"]["24-69.keep.g6"]["records"] = 777
    (damaged / "hashes.json").write_text(json.dumps(hashes))
    digest = worker.files_digest(run, result)
    def green_digest():
        assert worker.files_digest(run, result) == digest
    red("false u24 target records", lambda: worker.files_digest(run, damaged),
        "COUNTS: hashes.json 24-69.keep.g6 records: metadata 777 != checked files 0", green_digest)
    shutil.copyfile(result / "hashes.json", damaged / "hashes.json")
    (damaged / "replay/summary.json").unlink()
    red("G4 missing summary", lambda: evidence.g4(run, damaged, base), "G4: replay/summary.json is required", green_g4)
    replay = evidence.load(result / "replay/summary.json")
    for key, value, want in (("fraction", 0.001, "G4: replay summary fraction must be 0.002"),
                             ("mismatching_parents", 1, "G4: replay summary mismatching_parents must be 0"),
                             ("sampled_parents", 0, "G4: PASS requires sampled_parents above 0")):
        bad = dict(replay, **{key: value})
        (damaged / "replay/summary.json").write_text(json.dumps(bad))
        red("G4 " + key, lambda: evidence.g4(run, damaged, base), want, green_g4)
    shutil.copyfile(result / "replay/summary.json", damaged / "replay/summary.json")
    fp = evidence.load(damaged / "replay/fingerprint.json")
    fp["fingerprint"] = "0" * 64
    (damaged / "replay/fingerprint.json").write_text(json.dumps(fp))
    red("G4 stale fingerprint", lambda: evidence.g4(run, damaged, base),
        "G4: fingerprint differs from checked manifests, tools or settings", green_g4)

    retained = evidence.retained_files(run, result)
    def green_retained():
        assert evidence.retained_files(run, result) == retained
    for name in ("24-69.g6", "24-69.certs.jsonl"):
        original = (damaged / name).read_bytes()
        (damaged / name).write_bytes(b"garbage\n")
        red("garbage retained " + name, lambda: evidence.retained_files(run, damaged),
            f"RESULT BINDING: retained {name} differs from checked file", green_retained)
        (damaged / name).write_bytes(original)
    (damaged / "24-69.certs.jsonl").unlink()
    red("missing retained certificate", lambda: evidence.retained_files(run, damaged),
        "RESULT BINDING: retained file set differs: missing ['24-69.certs.jsonl'], extra []", green_retained)

    resumed = a.out / "resumed-1444"
    red_controls.faithful_copy(a.resumed, resumed)
    resumed_result = a.out / "resumed-result"
    mirror_result(resumed, a.pilot / "res/24-69-L12-tri-pf74/s1444of1920", resumed_result)
    resumed_summary = evidence.load(resumed / "run-summary.json")
    entry = next(e for e in resumed_summary["levels"] if (e["n"], e["m"]) == (17, 37))
    assert entry["resumed"] and "parent_sources" not in entry
    exported = evidence.reconcile(resumed, resumed_result, 13, base)
    assert exported["recovered_cells"] == ["17-37"]
    evidence.g4(resumed, resumed_result, exported, whole=False, prefix=base)
    missing_export = copy.deepcopy(exported["summary"])
    missing_export["levels"] = [entry if (e["n"], e["m"]) == (17, 37) else e for e in missing_export["levels"]]
    def green_export():
        fresh = evidence.structural_entry(resumed, entry, evidence.Files(resumed), {})
        assert fresh == next(e for e in exported["summary"]["levels"] if (e["n"], e["m"]) == (17, 37))
        evidence.require_structure(resumed_summary, exported["summary"])
    red("resumed cell without export", lambda: evidence.require_structure(resumed_summary, missing_export),
        "STRUCTURE: 17-37: resumed cell has no exported parent sources, parent count and shards", green_export)
    saved = resumed / "17-37.manifest.json"
    original = saved.read_bytes()
    saved.unlink()
    want = f"STRUCTURE: 17-37: cannot export resumed parent sources, parent count and shards: [Errno 2] No such file or directory: '{saved}'"
    def restore_export():
        saved.write_bytes(original)
        green_export()
    red("resumed cell cannot export", lambda: evidence.structural_entry(resumed, entry, evidence.Files(resumed), {}), want, restore_export)
    # The existing summary checker consumes the export through its history interface.
    history = resumed_result / "history"
    history.mkdir()
    (history / "export.json").write_text(json.dumps(exported["summary"]))
    (history / "INDEX.json").write_text(json.dumps({"commits": ["export"]}))
    audit = subprocess.run([sys.executable, "-B", str(worker.CHECKER), "--summary-only", str(resumed_result),
                            "--require-hashes", "--require-g4"], capture_output=True, text=True)
    (a.out / "resumed-summary.log").write_text(audit.stdout + audit.stderr)
    stats = json.loads(audit.stdout.splitlines()[0])
    expected_missing = "PROBLEM: fleet (24,69) sliced 1920 ways at level 12: 1919 slices have no summary"
    problems = [line for line in audit.stdout.splitlines() if line.startswith("PROBLEM:")]
    assert (audit.returncode == 1 and stats["unresolved"] == 0 and len(problems) == 1
            and problems[0].startswith(expected_missing)
            and stats["fleets"][0]["cells_recovered_from_history"] == 16), audit.stdout
    print("REVIEW green: resumed 17-37 exported; unchanged summary checker reports no unresolved resumed cells", flush=True)
    (a.out / "1907.structure.json").write_text(json.dumps(base))
    (a.out / "1444.structure.json").write_text(json.dumps(exported))

    cells = known.catalogue()
    clean_known = known.slice_control(run, cells)
    assert clean_known["result"] == "OK"
    empty = a.out / "no-graphs"
    empty.mkdir()
    for name in ("run-config.json", "reach.json"):
        shutil.copyfile(run / name, empty / name)
    bad = known.slice_control(empty, cells)
    want = "FILE 16-35.g6: required production stage file is missing"
    assert bad["result"] == "FAIL" and bad["problems"][0] == want and len(bad["problems"]) == 87
    print("REVIEW red: " + want + " (87 missing stage files)", flush=True)
    assert known.slice_control(run, cells) == clean_known
    print("REVIEW green: real known-graph evidence passed again", flush=True)
    reports.append({"control": "empty run directory", "output": want})
    table = a.out / "empty-table.json"
    table.write_text(json.dumps({"seed_n": 10, "table": {}}))
    py = str(Path.home() / "tools/pyenv-maths/bin/python")
    command = [py, "-B", str(Path(__file__).with_name("known_slices.py")), "--reach"]
    bad = subprocess.run([*command, str(table)], text=True, capture_output=True)
    want = "KNOWN-SLICES FAIL: CONFIG: not the production (24,69) reach table with seed 10 and root k 5"
    assert bad.returncode == 1 and bad.stdout.strip() == want, bad
    print("REVIEW red: " + want, flush=True)
    with (a.out / "known-slices.log").open("w") as log:
        green = subprocess.run([*command, str(run / "reach.json"), "--prefix", str(run), "--self-test"], stdout=log, stderr=subprocess.STDOUT)
    text = (a.out / "known-slices.log").read_text()
    assert green.returncode == 0 and "KNOWN-SLICES OK: 97912 eligible, 97912 placed" in text, text[-3000:]
    print("REVIEW green: KNOWN-SLICES OK: 97912 eligible, 97912 placed", flush=True)
    reports.append({"control": "empty reach table", "output": want})
    (a.out / "review-controls.json").write_text(json.dumps(reports, indent=1) + "\n")
    print(f"REVIEW CONTROLS OK: {len(reports)} exact refusals; unmutated evidence passed after every control", flush=True)


if __name__ == "__main__":
    main()
