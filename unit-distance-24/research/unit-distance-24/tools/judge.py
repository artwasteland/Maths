#!/usr/bin/env python3
"""Judge fetched u(24) trees, without fetching, modifying them, or trusting pass labels.

Usage (Python with pynauty): judge.py ROOT --plan PLAN.json [--out REPORT.json]
ROOT contains one directory per fetched branch, each with research/unit-distance-24/
results/u24/{check,24-69-L12-tri-pf74}. A single extracted branch is also allowed.
Plans have target=[24,69], slice_level=12, count=1920, and tasks={tag:[indices]}.
Declare coverage separately with slices=[...], heavy+random (the pilot), all=true,
or the published full/repro schema. Tasks include pruned, moved and rerun ownership.
Reruns retire suspect copies; validation copies are audited without filling coverage.
The full plan judges phase A; its pilot and held phase B complete the partition.
The repro plan requires matching accepted copies from both main and repro owners.
The published pilot remains the cost sample when judging a subset or the whole run.

Exit 0: every planned slice accepted, no unresolved evidence. Exit 3: missing or
pending evidence. Exit 1: contradiction. Survivors are reported for refutation;
JUDGE OK is an evidence verdict, never by itself a determination of u(24).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import evidence
import known_graphs as known
import receipt_audit
import worker

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research/unit-distance-23/tools"))

SUB = Path("research/unit-distance-24/results/u24")
KIND = "24-69-L12-tri-pf74"
PILOT = ROOT / "coordination/cloud-workers/u24-pilot-plan.json"
FULL = ROOT / "coordination/cloud-workers/u24-full-plan.json"
REPRO = ROOT / "coordination/cloud-workers/u24-repro-plan.json"
PHASEB = ROOT / "coordination/cloud-workers/u24-phaseb-plan.json"
BASELINE = ROOT / "research/unit-distance-23/results/u23/result-inputs/aggregate.json"
CHECKER_PIN = "a231bfc384702231f57fc21461b4c700ec8eed842bceb981076963c79d2cc86a"
SUFFIXES = (".txt", ".known.json", ".inventory.jsonl.gz", ".structure.json")
RECEIPT_NAME = re.compile(r"s(\d+)of1920-([A-Za-z0-9_-]+)")
READ_ERRORS = (OSError, EOFError, ValueError, KeyError, TypeError, AttributeError, IndexError, StopIteration)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def indices(value, label):
    if (not isinstance(value, list) or any(type(i) is not int or not 0 <= i < 1920 for i in value)
            or len(value) != len(set(value))):
        raise ValueError(f"PLAN: {label} must contain distinct slice indices in 0..1919")
    return value


def copy_requests(plan, field):
    """Validate rerun/validation declarations independently of receipt discovery."""
    records = plan.get(field, [])
    if not isinstance(records, list):
        raise ValueError(f"PLAN: {field} must be a list of records")
    tags = ("from", "to") if field == "rerun" else ("tag",)
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not {"slice", "why", *tags} <= record.keys():
            raise ValueError(f"PLAN: incomplete {field} record")
        i = record["slice"]
        if (type(i) is not int or not 0 <= i < 1920
                or any(not isinstance(record[k], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", record[k]) for k in tags)
                or not isinstance(record["why"], str) or not record["why"].strip()):
            raise ValueError(f"PLAN: invalid {field} slice, tag or reason")
        key = i if field == "rerun" else (i, record["tag"])
        if key in seen:
            raise ValueError(f"PLAN: duplicate {field} for slice {i}")
        seen.add(key)
    return records


def plan_owners(plan):
    """Recover completed and reassigned work without giving a slice two owners."""
    tasks = plan.get("tasks")
    if not isinstance(tasks, dict) or not tasks:
        raise ValueError("PLAN: tasks must be a nonempty worker table")
    owners, origin = {}, {}

    def assign(tag, values, label, moved=False, source=None):
        if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", tag):
            raise ValueError("PLAN: invalid worker tag")
        for i in indices(values, label):
            # Moves can already appear in the receiver's current task list. A later move may take a slice from its
            # current owner only when that ownership itself came from an earlier MOVE (a chained move, e.g. a Codex
            # tag whose task ran out of time); a donor that still lists the slice in tasks/pruned owns it twice.
            chained = moved and owners.get(i) == source and origin.get(i) == "moved"
            if i in owners and (not moved or owners[i] != tag) and not chained:
                raise ValueError(f"PLAN: tasks assign a slice more than once: {i} ({owners[i]}, {tag})")
            owners[i] = tag
            origin[i] = "moved" if moved else "listed"

    for tag, values in tasks.items():
        assign(tag, values, f"tasks[{tag}]")
    for field in ("pruned", "moved"):
        records = plan.get(field, [])
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise ValueError(f"PLAN: {field} must be a list of records")
        for record in records:
            if field == "pruned":
                removed = record.get("removed")
                if not isinstance(removed, dict):
                    raise ValueError("PLAN: pruned removed must be a worker table")
                for tag, values in removed.items():
                    assign(tag, values, f"pruned[{tag}]")
            else:
                source = record.get("from")
                if (not isinstance(source, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", source)
                        or source == record.get("to")):
                    raise ValueError("PLAN: invalid move source")
                assign(record.get("to"), record.get("slices"), "moved slices", moved=True, source=source)
    for record in copy_requests(plan, "rerun"):
        i, source, dest = record["slice"], record["from"], record["to"]
        if owners.get(i) == dest:
            raise ValueError(f"PLAN: rerun slice {i}: destination {dest} already owns it")
        if owners.get(i) != source:
            raise ValueError(f"PLAN: rerun slice {i}: {source} is not the current owner")
        owners[i] = dest
    return owners


def plan_check(plan):
    if (plan.get("target") != [24, 69] or plan.get("slice_level") != 12 or plan.get("count") != 1920):
        raise ValueError("PLAN: expected target (24,69), slice level 12 and count 1920")
    owners = plan_owners(plan)
    assigned = set(owners)
    superseded_records(plan)
    retired = {(r["slice"], r["from"]) for r in copy_requests(plan, "rerun")}
    for record in copy_requests(plan, "validation"):
        i, tag = record["slice"], record["tag"]
        if owners.get(i) == tag or (i, tag) in retired:
            raise ValueError(f"PLAN: validation slice {i}: tag {tag} is an owner or a retired owner")
    declared = []
    if plan.get("all") is True:
        declared.append(set(range(1920)))
    if "slices" in plan:
        declared.append(set(indices(plan["slices"], "slices")))
    if plan.get("job") == "u24-repro":
        sample = indices(plan.get("random"), "random")
        heavy = indices(plan.get("chosen", {}).get("heavy"), "chosen.heavy")
        if type(plan.get("seed")) is not int:
            raise ValueError("PLAN: repro seed must be an integer")
        draw = sorted(random.Random(plan["seed"]).sample(range(1920), 48))
        if sorted(sample) != draw:
            raise ValueError("PLAN: repro random slices differ from the published sampling rule")
        if not heavy or set(heavy) & set(sample):
            raise ValueError("PLAN: repro requires chosen heavy slices disjoint from the random draw")
        declared.append(set(heavy + sample))
    elif "heavy" in plan or "random" in plan:
        heavy, sample = indices(plan.get("heavy"), "heavy"), indices(plan.get("random"), "random")
        if len(heavy) != 10 or len(sample) != 32 or set(heavy) & set(sample):
            raise ValueError("PLAN: estimator requires ten heavy and 32 disjoint random slices")
        if type(plan.get("random_seed")) is not int:
            raise ValueError("PLAN: random_seed must be an integer")
        draw = sorted(random.Random(plan["random_seed"]).sample(sorted(set(range(1920)) - set(heavy)), 32))
        if sorted(sample) != draw:
            raise ValueError("PLAN: random slices differ from the published sampling rule")
        if not plan.get("all"):
            declared.append(set(heavy + sample))
    if plan.get("job") == "u24-full" and ("phase_a" in plan or "phase_b" in plan):
        pilot = set(indices(plan["pilot"]["slices"], "pilot.slices"))
        held = set(indices(plan["phase_b"]["slices"], "phase_b.slices"))
        if (len(pilot) != 42 or len(held) != 37 or pilot & held
                or plan["phase_a"]["count"] != 1841 or plan["phase_b"]["count"] != 37):
            raise ValueError("PLAN: pilot/phase A/phase B must partition 1920 slices as 42/1841/37")
        if pilot != set(plan_check(evidence.load(PILOT))):
            raise ValueError("PLAN: full plan pilot slices differ from the reconstructed pilot")
        declared.append(set(range(1920)) - pilot - held)
    if not declared:
        raise ValueError("PLAN: declare coverage with slices, heavy/random, all=true, or the full/repro schema")
    if any(d != declared[0] for d in declared[1:]):
        raise ValueError("PLAN: coverage declarations disagree")
    expected = declared[0]
    if not expected:
        raise ValueError("PLAN: empty coverage")
    if assigned != expected:
        raise ValueError(f"PLAN: tasks do not cover the declared slices exactly once; "
                         f"missing {sorted(expected - assigned)}, extra {sorted(assigned - expected)}")
    return sorted(expected)


def superseded_records(plan):
    records = plan.get("superseded", [])
    if not isinstance(records, list):
        raise ValueError("PLAN: superseded must be a list of records")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not {"slice", "tag", "receipt_sha256", "reason"} <= record.keys():
            raise ValueError("PLAN: incomplete superseded record")
        i, tag, digest = record["slice"], record["tag"], record["receipt_sha256"]
        if (type(i) is not int or not 0 <= i < 1920
                or (tag is not None and (not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", tag)))
                or (digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)))
                or (tag is None and digest is not None)
                or not isinstance(record["reason"], str) or not record["reason"].strip()):
            raise ValueError("PLAN: invalid superseded slice, tag, receipt hash or reason")
        key = i, tag, digest
        if key in seen:
            raise ValueError("PLAN: duplicate superseded record")
        seen.add(key)
    return records


def match_superseded(plan, copies):
    matched = {}
    for record in superseded_records(plan):
        label = f"superseded slice {record['slice']}, tag {record['tag']}"
        try:
            matches = [n for n, c in enumerate(copies)
                       if (c["slice"], c["tag"]) == (record["slice"], record["tag"])
                       and (evidence.sha(c["receipt"]) if c["receipt"] else None) == record["receipt_sha256"]]
            if len(matches) != 1:
                raise ValueError(f"must match exactly one discovered copy; found {len(matches)}")
            n, = matches
            receipt = copies[n]["receipt"]
            if receipt:
                verdicts = re.findall(r"^# u24-worker verdict: (.*)$", receipt.read_text(), re.M)
                if verdicts != ["FAIL"]:
                    raise ValueError("must have a FAIL verdict or no receipt; cannot supersede an accepted copy")
        except READ_ERRORS as error:
            raise ValueError(f"PLAN: {label}: {error}") from error
        matched[n] = record
    return matched


@lru_cache(maxsize=1)
def reference():
    """Compute predictions locally from pinned data, never from worker-supplied maps."""
    import known_slices
    cells = known.catalogue()
    table = {int(n): {int(m): k for m, k in row.items()} for n, row in known.production_table().items()}
    files = [str(known.DATA / cell["dataset"]["file"]) for cell in cells.values()]
    prediction = known_slices.run(table, 10, 12, 1920, None, files)
    expected = {(int(n), int(m), i) for name, cell in cells.items()
                for n, m in [name.split("-")] for i in cell["eligible_indices"]}
    placed = [tuple(g) for values in prediction["by_slice"].values() for g in values]
    if (prediction["violations"] or prediction["missing_from_prefix"] or len(placed) != 97912
            or len(set(placed)) != len(placed) or set(placed) != expected):
        raise ValueError("KNOWN: prediction does not place all 97912 eligible graphs exactly once")
    return cells, {i: set(map(tuple, prediction["by_slice"].get(str(i), []))) for i in range(1920)}


def discover(root, planned):
    bases = ([root / SUB] if (root / SUB).is_dir() else
             [p / SUB for p in sorted(root.iterdir()) if p.is_dir() and (p / SUB).is_dir()])
    copies, pending, extra = [], [], set()
    for base in bases:
        stems = set()
        check = base / "check"
        for path in sorted(check.glob("s*of1920-*")):
            for suffix in SUFFIXES:
                if path.name.endswith(suffix):
                    stems.add(path.name[:-len(suffix)])
                    break
        receipted = set()
        for stem in sorted(stems):
            match = RECEIPT_NAME.fullmatch(stem)
            if not match:
                raise ValueError(f"DISCOVERY: invalid receipt name {check / stem}")
            index, tag = int(match[1]), match[2]
            if index not in planned:
                extra.add(index)
            receipted.add(index)
            receipt = check / (stem + ".txt")
            result = base / KIND / f"s{index}of1920"
            c = {"slice": index, "tag": tag, "receipt": receipt, "dir": result,
                 "worker": str(receipt.relative_to(root)), "base": base}
            if not receipt.is_file():
                c["pending"] = f"PENDING: slice {index}: receipt bundle has no text receipt ({c['worker']})"
                if index in planned:
                    pending.append(c["pending"])
                c["receipt"] = None
            copies.append(c)
        for result in sorted((base / KIND).glob("s*of1920")):
            match = re.fullmatch(r"s(\d+)of1920", result.name)
            if not match:
                continue
            index = int(match[1])
            if index not in planned:
                extra.add(index)
            if index not in receipted:
                c = {"slice": index, "tag": None, "receipt": None, "dir": result,
                     "worker": str(result.relative_to(root)), "base": base,
                     "pending": f"PENDING: slice {index}: result pushed without receipts ({result.relative_to(root)})"}
                copies.append(c)
                if index in planned:
                    pending.append(c["pending"])
    return copies, pending, sorted(extra)


def target_records(result):
    """Read even a rejected/pending copy, so false metadata cannot conceal a survivor."""
    path = result / "24-69.keep.g6"
    if not path.exists():
        return None
    codes = [code.decode("ascii") for code in known.records(path)]
    for code in codes:
        if known.graph_stats(code.encode())[:2] != (24, 69):
            raise ValueError("TARGET: retained keep file contains a graph outside (24,69)")
    if len(set(codes)) != len(codes):
        raise ValueError("TARGET: retained keep file contains duplicate graph6 records")
    return codes


def prefix_binding(c, structure, body):
    head = re.search(r"^# u24-worker ([A-Za-z0-9_-]+), slice s(\d+)of1920, checked (whole|from level 13):", body, re.M)
    if not head or (head[1], int(head[2])) != (c["tag"], c["slice"]):
        raise ValueError(f"IDENTITY: slice {c['slice']}: receipt header and filename disagree")
    if head[3] == "whole":
        if "CHAIN OK" not in body.splitlines():
            raise ValueError(f"PREFIX: slice {c['slice']}: whole receipt has no whole check")
        return True
    binding = structure.get("prefix_receipt", {})
    name = binding.get("name", "")
    suffix = ".structure.json"
    match = RECEIPT_NAME.fullmatch(name[:-len(suffix)]) if name.endswith(suffix) else None
    if not match or match[2] != c["tag"]:
        raise ValueError(f"PREFIX: slice {c['slice']}: later slice is not bound to a whole check of worker {c['tag']}")
    prefix_text = c["receipt"].parent / (name[:-len(suffix)] + ".txt")
    old = prefix_text.read_text()
    if (not old.startswith(f"# u24-worker {c['tag']}, slice s{match[1]}of1920, checked whole:")
            or "CHAIN OK" not in old.splitlines()):
        raise ValueError(f"PREFIX: slice {c['slice']}: later slice is not bound to a whole check of worker {c['tag']}")
    # receipt_audit recursively checks this whole receipt, its result, and the binding SHA256.
    return False


def accepted_copy(c, structure, body):
    import aggregate_fleet as aggregate23

    d, i = c["dir"], c["slice"]
    if structure["slice"] != [12, i, 1920] or structure["target"] != [24, 69]:
        raise ValueError(f"IDENTITY: slice {i}: result is filed under another slice")
    whole = prefix_binding(c, structure, body)
    config = evidence.load(d / "run-config.json")
    known.production_reach(evidence.load(d / "reach.json"))
    required = {"seed_n": 10, "reach": True, "reach_root_k": 5, "prune": True, "prune_from": 12,
                "prune_filter_only": True, "forbidden_set": 398, "verify_stages": True,
                "triangles": True, "prune_filter_set": 74}
    if any(canonical(config.get(k)) != canonical(v) for k, v in required.items()):
        raise ValueError(f"CONFIG: slice {i}: not the production run options")
    if evidence.load(d / "run-summary.json").get("completed_through_n") != 24:
        raise ValueError(f"RECEIPT: slice {i}: accepted check has unfinished result")
    hashes = evidence.load(d / "hashes.json")["files"]
    prefix = tuple(sorted((name, row["sha256"]) for name, row in hashes.items()
                          if int(name.split("-")[0]) <= 12))
    if not prefix:
        raise ValueError(f"PREFIX: slice {i}: empty prefix file set")
    rows = evidence.load(d / "counts.json")
    counts = {(n, m): aggregate23.row(ch, dict(sorted(pc.items())) if pc is not None else None)
              for n, m, ch, pc in rows}
    upper = {name: (row["sha256"], row["records"]) for name, row in hashes.items()
             if int(name.split("-")[0]) > 12}
    receipt = evidence.load(c["receipt"].with_suffix(".known.json"))
    if receipt.get("reach_sha256") != evidence.sha(d / "reach.json") or receipt.get("run_config_sha256") != evidence.sha(d / "run-config.json"):
        raise ValueError(f"KNOWN: slice {i}: control is not bound to its reach and configuration")
    # The full exported manifests have already entered the staged history. Do not
    # retain ~2,000 copies of that archive in RAM for the fleet-wide comparisons.
    compact = {k: structure[k] for k in ("target_files", "g4")}
    return dict(c, structure=compact, whole=whole, prefix=prefix, counts=counts, upper=upper,
                keep_lines=target_records(d), known=receipt, options={k: v for k, v in config.items() if k != "slice"})


def compare_copies(copies):
    import aggregate_fleet as aggregate23

    problems, duplicates = [], {}
    for i, cs in sorted(copies.items()):
        if len(cs) > 1:
            duplicates[str(i)] = [c["worker"] for c in cs]
        for c in cs[1:]:
            differences = aggregate23.compare_copies(cs[0], c)
            if differences:
                kind = "counts" if any("cell" in d for d in differences) else "hashes" if any("file" in d for d in differences) else "target records"
                problems.append(f"COPIES: slice {i}: accepted copies disagree on {kind} ({cs[0]['worker']}, {c['worker']})")
            if cs[0]["structure"]["target_files"] != c["structure"]["target_files"]:
                problems.append(f"COPIES: slice {i}: accepted copies disagree on target file measurements")
    all_copies = [c for cs in copies.values() for c in cs]
    if all_copies:
        first = all_copies[0]
        for c in all_copies[1:]:
            if c["prefix"] != first["prefix"]:
                problems.append(f"PREFIX: slice {c['slice']}: hashes.json prefix differs between workers or copies")
            if canonical(c["options"]) != canonical(first["options"]):
                problems.append(f"CONFIG: slice {c['slice']}: accepted copies use different run options")
    return problems, duplicates


def known_check(copies, cells, predicted):
    problems = []
    chosen = []
    for i, cs in sorted(copies.items()):
        for c in cs:
            try:
                sets = known.receipt_sets(c["known"], cells)
                # All Engel cells are above the compacted prefix; even legacy
                # inventories have these rows explicitly. Their receipt was audited.
                inventory = receipt_audit.InventoryFiles(c["receipt"].with_suffix(".inventory.jsonl.gz"), {"file_counts": {}})
                found = set()
                for name, stages in sets.items():
                    n, m = map(int, name.split("-"))
                    expected = {index for gn, gm, index in predicted[i] if (gn, gm) == (n, m)}
                    problems.extend(f"KNOWN: slice {i}: {p}" for p in known.soundness(name, stages, cells[name]["eligible_indices"]))
                    for stage, f in c["known"]["cells"][name]["files"].items():
                        if f["records"] != inventory.count(f["name"]):
                            problems.append(f"KNOWN: slice {i}: {f['name']} record count differs from checked inventory")
                    # A predicted kept form also has to have been found in both inputs.
                    # Report missing keep records below, once, with their graph identities.
                    for stage in ("full", "reach"):
                        got = stages[stage] & cells[name]["eligible_indices"]
                        if got != expected and stages["keep"] == expected:
                            problems.append(f"KNOWN: slice {i}: {name} {stage} eligible indices differ from prediction")
                    found.update((n, m, index) for index in stages["keep"])
                for n, m, index in sorted(predicted[i] - found):
                    problems.append(f"KNOWN: slice {i}: missing predicted Engel graph ({n},{m}) #{index}")
                for n, m, index in sorted(found - predicted[i]):
                    problems.append(f"KNOWN: slice {i}: unexpected Engel graph ({n},{m}) #{index}")
            except READ_ERRORS as error:
                problems.append(f"KNOWN: slice {i}: {error}")
        chosen.append(cs[0]["known"])
    fleet = known.fleet_control(chosen, cells, set(copies) == set(range(1920))) if chosen else None
    if fleet:
        problems.extend(f"KNOWN: {p}" for p in fleet["problems"])
    return problems, fleet


def summary_audit(dirs, total, work):
    """u(23) target_check.audit's policy, with strict exit/JSON/coverage checking."""
    if not dirs:
        return {"status": "pending", "problems": [], "unresolved": [], "missing_slices": 1920}
    command = [sys.executable, str(worker.CHECKER), "--summary-only", "--expect-target", "24", "69",
               "--expect-seed", "10", "--expect-slices", "12", "1920", "--require-hashes", "--require-g4", *map(str, dirs)]
    run = subprocess.run(command, capture_output=True, text=True)
    (work / "summary-audit.txt").write_text(run.stdout + run.stderr)
    lines = run.stdout.splitlines()
    problems, unresolved, omitted = [], [], []
    missing = re.compile(r"fleet \(24,69\) sliced 1920 ways at level 12: (\d+) slices have no summary \(.*\)")
    for line in lines:
        if line.startswith("PROBLEM: "):
            body = line[len("PROBLEM: "):]
            match = missing.fullmatch(body)
            if match and total < 1920 and int(match[1]) == 1920 - total:
                omitted.append(body)
            else:
                problems.append("SUMMARY: " + body)
        if line.startswith("UNRESOLVED: "):
            unresolved.append("SUMMARY: " + line[len("UNRESOLVED: "):])
    try:
        records = [json.loads(line) for line in lines if line.startswith("{")]
        record, = records
        fleets, = record["fleets"]
        expected_exit = 1 if record["problems"] else 4 if record["unresolved"] else 3
        if (run.returncode != expected_exit or record["audited"] != len(dirs) or record["runs"] != len(dirs)
                or record["problems"] != len(problems) + len(omitted) or record["unresolved"] != len(unresolved)
                or fleets["slice_indices"] != total or fleets["missing_slices"] != 1920 - total
                or len(omitted) != int(total < 1920) or run.stderr
                or not any(line.startswith("COVERAGE (summary only) ") for line in lines)
                or (total == 1920 and not problems and not unresolved and not any(line.startswith("COVERAGE (summary only) OK:") for line in lines))):
            raise ValueError("inconsistent audit output")
    except READ_ERRORS:
        problems.append(f"SUMMARY: checker did not produce a complete, consistent summary audit (exit {run.returncode})")
        record = None
    return {"status": "FAIL" if problems else "pending" if unresolved else "complete" if total == 1920 else "per-slice OK",
            "problems": problems, "unresolved": unresolved, "missing_slices": 1920 - total,
            "omitted_coverage_only": omitted, "record": record, "stdout": run.stdout, "stderr": run.stderr, "exit": run.returncode}


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def timing(c):
    """Keep measured wall clocks separate from the u(23) four-shard cost convention."""
    import fleet_status as status23

    out = {"source": c["worker"], "accepted": c.get("accepted", False), "issues": []}
    d = c["dir"]
    try:
        summary = evidence.load(d / "run-summary.json")
        # Call the old rule itself. Reject nonfinite or negative times before it sums them.
        for e in summary.get("levels", []):
            values = [s.get("wall_seconds", 0) or 0 for s in e.get("shards") or []]
            values += [(e.get("prune") or {}).get("step_wall_seconds", 0) or 0,
                       (e.get("verify") or {}).get("wall_seconds", 0) or 0]
            if any(not number(v) for v in values):
                raise ValueError("invalid step timing")
        timed = status23.slice_record(d)
        out["step_seconds"] = timed["seconds_known"]
        out["resumed_cells"] = timed["resumed_cells"]
        partial = any(e.get("reach", {}).get("resumed") or e.get("verify", {}).get("resumed")
                      or any(s.get("resumed") for s in e.get("shards", [])) for e in summary["levels"] if e["n"] > 12)
        out["lower_bound"] = not c.get("accepted") or summary.get("completed_through_n") != 24 or bool(timed["resumed_cells"]) or partial
    except READ_ERRORS as error:
        out.update(step_seconds=0.0, resumed_cells=None, lower_bound=True)
        out["issues"].append(str(error))
    measured = {}
    if c.get("receipt"):
        try:
            matches = re.findall(r"^# measured: (.+)$", c["receipt"].read_text(), re.M)
            raw, = matches
            measured = json.loads(raw)
        except READ_ERRORS as error:
            out["issues"].append(f"missing/unreadable measured timings: {error}")
    try:
        fp = evidence.load(d / "replay/fingerprint.json")
    except READ_ERRORS:
        fp = {}
    for key, old in (("run_dag2_seconds", "run_dag2_wall_seconds"), ("g4_seconds", "replay_wall_seconds")):
        value = measured.get(key, fp.get(old))
        if not number(value):
            out["issues"].append(f"{key} unavailable")
            value = None
        if key in measured and value != fp.get(old):
            out["issues"].append(f"{key} disagrees with replay fingerprint")
            value = None
        out[key] = value
    for phase in ("check", "control", "evidence"):
        value = measured.get(phase, {}).get("seconds")
        out[phase + "_seconds"] = value if number(value) else None
        rss = measured.get(phase, {}).get("peak_rss_kib")
        out[phase + "_peak_rss_kib"] = rss if number(rss) and rss > 0 else None
    out["run_peak_rss_kib"] = None
    out["disk_peak_bytes"] = None
    out["disk_at_check_bytes"] = None
    if c.get("receipt"):
        try:
            with gzip.open(c["receipt"].with_suffix(".inventory.jsonl.gz"), "rt") as stream:
                header = json.loads(next(stream))
                rows = [json.loads(line) for line in stream]
            # Legacy inventories compact the prefix. New ones include it explicitly.
            upper = [r for r in rows if not re.match(r"(?:shards/|_parents/)?(?:10|11|12)-", r["path"]) or ".slice-" in r["path"]]
            out["disk_at_check_bytes"] = header["bytes"] + sum(r["bytes"] for r in upper)
        except READ_ERRORS as error:
            out["issues"].append(f"disk inventory unavailable: {error}")
    return out


def cost_report(candidates, baseline, sample):
    heavy, sample_random = sample["heavy"], sample["random"]
    weights = {i: 1.0 for i in heavy} | {i: 1910 / 32 for i in sample_random}
    if (baseline["plan"]["target"] != [23, 65] or baseline["coverage"]["complete"] != 1920
            or baseline["cost"]["slices_timed"] != 1920 or baseline["cost"]["slices_excluded_resumed"]):
        raise ValueError("COST: baseline is not the complete timed (23,65) fleet")
    all_rows, chosen = {}, {}
    for i, cs in sorted(candidates.items()):
        rows = [timing(c) for c in cs]
        previous = baseline["slices"][str(i)]
        for row in rows:
            row["sample_group"] = "heavy" if i in heavy else "random" if i in sample_random else "outside sample"
            row["estimator_weight"] = weights.get(i)
            row["t23_step_seconds"] = previous["seconds_known"]
            row["t23_wall_seconds"] = previous["replay"]["run_dag2_wall_seconds"]
            row["step_delta_seconds"] = row["step_seconds"] - row["t23_step_seconds"]
            row["wall_delta_seconds"] = None if row["run_dag2_seconds"] is None else row["run_dag2_seconds"] - row["t23_wall_seconds"]
        all_rows[str(i)] = rows
        # A complete accepted run first, then the strongest recorded lower bound.
        chosen[i] = min(rows, key=lambda r: (not r["accepted"], r["lower_bound"], -r["step_seconds"], r["source"]))
    estimates = {}
    for kind, key in (("step", "step_seconds"), ("wall", "run_dag2_seconds")):
        old = {int(i): r["seconds_known"] if kind == "step" else r["replay"]["run_dag2_wall_seconds"]
               for i, r in baseline["slices"].items()}
        if set(old) != set(range(1920)) or any(not number(t) for t in old.values()):
            raise ValueError(f"COST: invalid {kind} baseline timings")
        t23 = sum(old.values())
        deltas = {group: sum(weights[i] * ((chosen.get(i, {}).get(key) or 0) - old[i]) for i in values)
                  for group, values in (("heavy", heavy), ("random", sample_random))}
        unavailable = [i for i in weights if i not in chosen or chosen[i].get(key) is None]
        unfinished = [i for i in weights if i in chosen and chosen[i]["lower_bound"]]
        estimates[kind] = {"T23_seconds": t23, "heavy_delta_seconds": deltas["heavy"],
                           "weighted_random_delta_seconds": deltas["random"],
                           "T24_seconds": t23 + sum(deltas.values()),
                           "lower_bound": bool(unavailable or unfinished), "unavailable": unavailable, "unfinished": unfinished}
    overheads = {}
    for phase in ("g4", "check", "control", "evidence"):
        key = phase + "_seconds"
        overheads[phase] = {"weighted_seconds": sum(w * (chosen.get(i, {}).get(key) or 0) for i, w in weights.items()),
                            "unavailable": [i for i in weights if chosen.get(i, {}).get(key) is None],
                            "unfinished": [i for i in weights if i in chosen and not chosen[i]["accepted"]]}
    observed = {key: sum(r.get(key) or 0 for r in chosen.values()) for key in
                ("step_seconds", "run_dag2_seconds", "g4_seconds", "check_seconds", "control_seconds", "evidence_seconds")}
    paired = [r for r in chosen.values() if all(r.get(k) is not None for k in ("run_dag2_seconds", "g4_seconds", "check_seconds", "control_seconds"))]
    pair_wall = sum(r["run_dag2_seconds"] for r in paired)
    multiplier = 1 + sum(r[p + "_seconds"] for r in paired for p in ("g4", "check", "control")) / pair_wall if pair_wall else None
    projected_overhead = sum(overheads[p]["weighted_seconds"] for p in ("g4", "check", "control"))
    projected_wall = estimates["wall"]["T24_seconds"]
    complete = not estimates["wall"]["lower_bound"] and not any(overheads[p]["unavailable"] or overheads[p]["unfinished"] for p in ("g4", "check", "control"))
    return {"rule": baseline["cost"]["rule"], "estimator": sample.get("estimator", "T23 + heavy delta + (1910/32) * random delta"), "random_weight": 1910 / 32,
            "sample_measured": {"heavy": sum(i in chosen for i in heavy), "random": sum(i in chosen for i in sample_random)},
            "estimates": estimates, "overheads": overheads, "observed": observed,
            "observed_multiplier": multiplier, "multiplier_paired_slices": len(paired),
            "projected_total_wall_seconds": projected_wall + projected_overhead,
            "projected_multiplier": 1 + projected_overhead / projected_wall if complete and projected_wall > 0 else None,
            "rows": all_rows, "chosen": {str(i): r for i, r in chosen.items()},
            "longest": sorted((dict(slice=i, **r) for i, r in chosen.items()), key=lambda r: -(r.get("run_dag2_seconds") or 0))[:10],
            "notes": ["Step estimate applies the identical fleet_status.slice_record rule on both targets (four-shard normalization).",
                      "Wall estimate uses run-dag2 clocks on both targets; includes prefix/startup, and after restart only the last session.",
                      "Unfinished/resumed slices are lower bounds; missing t24 is zero, with its full t23 still subtracted. These bound the estimator, not the actual unsampled fleet cost.",
                      "Overheads use weight 1 for heavy and 1910/32 for random; evidence audit is shown separately from G4+check+control.",
                      "Receipts do not measure run-wide RSS or disk peaks. Disk-at-check is a lower bound on peak logical file bytes, not allocated blocks."]}


def judge(root, plan, work, baseline=None, sample=None):
    planned = plan_check(plan)
    owners = plan_owners(plan)
    main_owners = {}
    published_main = {}
    foreign_owners = defaultdict(set)
    supersession_plan = {"superseded": list(plan.get("superseded", []))}
    reruns = list(copy_requests(plan, "rerun"))
    validation_requests = {(r["slice"], r["tag"]): r for r in copy_requests(plan, "validation")}
    repro = plan.get("job") == "u24-repro"
    # Phase B (37 slices) was held out of the full plan, then released and run in the 2026-10-05 wave: its
    # owners are main owners too, so repro slices such as 1270 (phase-B owner w24) can pair main with repro.
    for path in (PILOT, FULL, PHASEB, REPRO):
        published = evidence.load(path)
        plan_check(published)
        if published.get("job") != plan.get("job"):
            supersession_plan["superseded"].extend(published.get("superseded", []))
            reruns.extend(copy_requests(published, "rerun"))
            for record in copy_requests(published, "validation"):
                foreign_owners[record["slice"]].add(record["tag"])
        for i, tag in plan_owners(published).items():
            if path in (PILOT, FULL, PHASEB):
                published_main[i] = tag
            # An amended selected plan replaces its published version; old
            # owners of that same plan do not become foreign owners.
            if published.get("job") != plan.get("job"):
                foreign_owners[i].add(tag)
            if repro and path in (PILOT, FULL, PHASEB):
                if i in main_owners:
                    raise ValueError(f"PLAN: main run assigns slice {i} more than once")
                if owners.get(i) == tag:
                    raise ValueError(f"PLAN: slice {i}: main and repro owners must differ")
                main_owners[i] = tag
    rerun_sources = {}
    for record in reruns:
        key = record["slice"], record["from"]
        if key in rerun_sources:
            raise ValueError(f"PLAN: duplicate rerun source {key}")
        rerun_sources[key] = record
    validation_owners = {}
    for i, tag in validation_requests:
        owner = owners.get(i, published_main.get(i))
        if owner is None:
            raise ValueError(f"PLAN: validation slice {i}: no declared owner")
        if tag in (owner, main_owners.get(i)) or (i, tag) in rerun_sources:
            raise ValueError(f"PLAN: validation slice {i}: tag {tag} is an owner or a retired owner")
        validation_owners[i] = owner
    sample = (plan if "heavy" in plan and "random" in plan else evidence.load(PILOT)) if sample is None else sample
    plan_check(sample)
    baseline = evidence.load(BASELINE) if baseline is None else baseline
    if evidence.sha(worker.CHECKER) != CHECKER_PIN:
        raise ValueError("CHECKER: verify-chain-u24.py differs from the reviewed pin")
    cells, predicted = reference()
    copies, _, extra = discover(root, set(planned))
    supersessions = match_superseded(supersession_plan, copies)
    accepted, candidates, survivors = defaultdict(list), defaultdict(list), defaultdict(list)
    primary, validated, rerun_old = defaultdict(list), defaultdict(list), defaultdict(list)
    problems, staged, rejected, pending = [], [], [], []
    superseded, foreign, unreceipted, incomplete, resumed = [], [], [], [], []
    validation, rerun_disagreements = [], []
    rerun_copies = 0
    for number_, c in enumerate(copies):
        i = c["slice"]
        c["accepted"] = False
        owns = (c["tag"] is not None and i in owners
                and (c["tag"] == owners[i] or c["tag"] == main_owners.get(i)))
        companion = i not in owners and c["tag"] is not None and c["tag"] == validation_owners.get(i)
        rerun = rerun_sources.get((i, c["tag"]))
        validation_request = validation_requests.get((i, c["tag"]))
        info = {"slice": i, "tag": c["tag"], "copy": c["worker"]}
        if validation_request:
            validation_row = dict(info, why=validation_request["why"], accepted=False)
            validation.append(validation_row)
        try:
            records = target_records(c["dir"])
        except READ_ERRORS as error:
            records = None
            problems.append(f"TARGET: slice {i}: {error}")
        if number_ in supersessions or rerun:
            row = dict(supersessions.get(number_, {}), **info)
            if rerun:
                rerun_copies += 1
                row.update(reason=rerun["why"], rerun=True, to=rerun["to"], accepted_looking=False,
                           receipt_sha256=evidence.sha(c["receipt"]) if c["receipt"] else None)
                if c["receipt"]:
                    try:
                        dest = work / f"copy-{number_:05d}" / f"s{i}of1920"
                        structure = receipt_audit.prepare(c["dir"], c["receipt"], dest)
                        old = accepted_copy(c, structure, c["receipt"].read_text())
                        rerun_old[i].append((rerun, old))
                        row["accepted_looking"] = True
                    except READ_ERRORS as error:
                        row["audit_error"] = str(error)
            superseded.append(row)
        elif not owns and not companion and not validation_request and c["tag"] in foreign_owners.get(i, set()):
            foreign.append(info)
        else:
            if i in owners and (c["tag"] is None or owns):
                candidates[i].append(c)
            try:
                if c["tag"] is not None and not (owns or companion or validation_request):
                    raise ValueError(f"OWNERSHIP: tag {c['tag']} does not own slice {i}")
                if c["receipt"]:
                    dest = work / f"copy-{number_:05d}" / f"s{i}of1920"
                    # prepare validates the receipt and stages the history interface.
                    structure = receipt_audit.prepare(c["dir"], c["receipt"], dest)
                    checked = accepted_copy(c, structure, c["receipt"].read_text())
                    c["accepted"] = checked["accepted"] = True
                    if validation_request:
                        validated[i].append(checked)
                        validation_row["accepted"] = True
                    else:
                        primary[i].append(checked)
                        if owns:
                            accepted[i].append(checked)
                    staged.append(dest)
                    if structure.get("recovered_cells"):
                        resumed.append(i)
                else:
                    incomplete.append((c, info))
            except READ_ERRORS as error:
                reason = f"REJECTED: slice {i}: {error} ({c['worker']})"
                problems.append(reason)
                rejected.append(reason)
        for graph in records or []:
            survivors[graph].append({"slice": i, "copy": c["worker"], "accepted": c["accepted"],
                                     "validation": bool(validation_request)})
    for c, info in incomplete:
        if c["tag"] is None and (c["slice"] in accepted or c["slice"] not in owners):
            unreceipted.append(info)
        elif c["slice"] in owners:
            pending.append(c["pending"])
    trusted = {i: primary.get(i, []) + validated.get(i, []) for i in sorted(primary.keys() | validated.keys())}
    differences, duplicates = compare_copies(trusted)
    problems.extend(differences)
    for i, olds in sorted(rerun_old.items()):
        for rerun, old in olds:
            for new in primary.get(i, []):
                if new["tag"] != rerun["to"]:
                    continue
                differences, _ = compare_copies({i: [new, old]})
                if differences:
                    rerun_disagreements.append({"slice": i, "old_copy": old["worker"], "new_copy": new["worker"],
                                                "differences": differences})
    kp, fleet_known = known_check(trusted, cells, predicted)
    problems.extend(kp)
    audit = summary_audit(staged, len(trusted), work)
    problems.extend(audit["problems"])
    pending.extend(audit["unresolved"])
    for graph, sources in survivors.items():
        slices = sorted({s["slice"] for s in sources if s["accepted"]})
        if len(slices) > 1:
            problems.append(f"TARGET: graph6 {graph} retained in different slices {slices}")
        unaccepted_slices = {s["slice"] for s in sources if not s["accepted"]}
        owner_slices = {s["slice"] for s in sources if s["accepted"] and not s["validation"]}
        for i in sorted((unaccepted_slices & primary.keys()) - owner_slices):
            problems.append(f"TARGET: survivor in a non-accepted copy only: slice {i}: graph6 {graph}")
    missing = sorted(set(planned) - accepted.keys())
    pending.extend(f"COVERAGE: slice {i}: no accepted copy" for i in missing)
    for i, tag in validation_requests:
        if not any(c["tag"] == tag for c in validated.get(i, [])):
            pending.append(f"VALIDATION: slice {i}, tag {tag}: no accepted validation copy")
        if not any(c["tag"] == validation_owners[i] for c in primary.get(i, [])):
            pending.append(f"VALIDATION: slice {i}: no accepted owner copy ({validation_owners[i]})")
    if repro:
        for i in planned:
            tags = {c["tag"] for c in accepted.get(i, [])}
            for role, tag in (("main", main_owners.get(i)), ("repro", owners[i])):
                if tag not in tags:
                    pending.append(f"COPIES: slice {i}: no accepted {role} copy")
    costs = cost_report(candidates, baseline, sample)
    # Missing timing prevents a definitive cost, not a mathematical evidence verdict.
    result = "FAIL" if problems else "PARTIAL" if pending else "OK"
    return {"schema": "u24-fleet-judge-v1", "verdict": result, "exit": {"OK": 0, "PARTIAL": 3, "FAIL": 1}[result],
            "planned": planned, "accepted_slices": sorted(accepted), "accepted_copies": sum(map(len, trusted.values())),
            "missing": missing, "unplanned_slices": extra, "duplicates": duplicates, "rejected": rejected,
            "superseded": superseded, "unreceipted": unreceipted, "foreign": foreign,
            "rerun_count": len(reruns), "rerun_copies": rerun_copies, "rerun_disagreements": rerun_disagreements,
            "validation_count": len(validation_requests), "validation_copies": sum(map(len, validated.values())),
            "validation": validation,
            "resumed_copies": len(resumed), "resumed_slices": sorted(set(resumed)),
            "problems": problems, "pending": pending, "prefix_files": len(next(iter(trusted.values()))[0]["prefix"]) if trusted else 0,
            "g4": dict(Counter(c["structure"]["g4"]["result"] for cs in trusted.values() for c in cs)),
            "survivors": [{"graph6": g, "slices": sorted({s["slice"] for s in sources}), "copies": sources} for g, sources in sorted(survivors.items())],
            "known": {"predicted_for_plan": sum(len(predicted[i]) for i in planned),
                      "predicted_for_accepted": sum(len(predicted[i]) for i in trusted), "total": 97912, "fleet": fleet_known},
            "summary": audit, "cost": costs,
            "provenance": {"checker_sha256": CHECKER_PIN, "baseline_sha256": evidence.sha(BASELINE),
                           "prediction_tool_sha256": evidence.sha(Path(__file__).with_name("known_slices.py")),
                           "plan": plan, "cost_sample": sample}}


def render(r):
    lines = [f"FLEET: {len(r['accepted_slices'])}/{len(r['planned'])} planned slices accepted; "
             f"{r['accepted_copies']} accepted copies; {len(r['duplicates'])} duplicated slices; {len(r['rejected'])} rejected copies",
             f"RERUN: {r['rerun_count']} transfers; {r['rerun_copies']} superseded copies; "
             f"{len(r['rerun_disagreements'])} disagreements (informational)",
             f"VALIDATION: {r['validation_count']} declared; {r['validation_copies']} accepted copies (do not count toward coverage)",
             f"RESUMED: {r['resumed_copies']} accepted copies carry recovered/resumed cells; slices {r['resumed_slices']}",
             f"PREFIX: {r['prefix_files']} prefix files compared; whole-check bindings checked per worker",
             "G4: " + (", ".join(f"{key} {n}" for key, n in sorted(r["g4"].items())) or "no accepted copies"),
             f"KNOWN: predicted {r['known']['predicted_for_plan']} for plan, {r['known']['predicted_for_accepted']} for accepted slices; "
             f"{r['known']['total']} eligible in whole fleet",
             f"SUMMARY: {r['summary']['status']}; {r['summary']['missing_slices']} of 1920 slices absent",
             f"TARGET: {len(r['survivors'])} distinct graph6 survivors measured from retained 24-69.keep.g6 files"]
    for category in ("superseded", "unreceipted", "foreign"):
        for row in r[category]:
            lines.append(f"{category.upper()}: slice {row['slice']}, tag {row['tag']}: {row['copy']}" +
                         (f"; {row['reason']}" if category == "superseded" else ""))
    for row in r["validation"]:
        lines.append(f"VALIDATION COPY: slice {row['slice']}, tag {row['tag']}: {row['copy']}; "
                     f"{'accepted' if row['accepted'] else 'not accepted'}; {row['why']}")
    for row in r["rerun_disagreements"]:
        lines.append(f"RERUN DISAGREEMENT (informational): slice {row['slice']}: "
                     f"{row['old_copy']} vs {row['new_copy']}: " + "; ".join(row["differences"]))
    for row in r["survivors"]:
        trusted = any(c["accepted"] for c in row["copies"])
        lines.append(f"SURVIVOR: slices {row['slices']}: {row['graph6']} (needs refutation; {'accepted evidence' if trusted else 'unaccepted evidence'})")
    for i, sources in r["duplicates"].items():
        lines.append(f"DUPLICATE: slice {i}: " + ", ".join(sources))
    c = r["cost"]
    lines += ["COST definition: " + c["rule"],
              "COST wall definition: run-dag2 wall clocks on both targets; last session only after restart",
              f"COST sample: {c['sample_measured']['heavy']}/10 heavy, {c['sample_measured']['random']}/32 random; random weight 1910/32 = 59.6875"]
    for kind, e in c["estimates"].items():
        lines.append(f"COST {kind} {'LOWER BOUND' if e['lower_bound'] else 'ESTIMATE'}: T23 {e['T23_seconds']:.3f} + "
                     f"heavy delta {e['heavy_delta_seconds']:.3f} + weighted random delta {e['weighted_random_delta_seconds']:.3f} "
                     f"= T24 {e['T24_seconds']:.3f} s ({e['T24_seconds']/3600:.3f} h)")
    lines.append("COST observed: " + ", ".join(f"{k.removesuffix('_seconds')} {v:.3f} s" for k, v in c["observed"].items()))
    lines.append("COST projected overhead" + (" LOWER BOUNDS: " if any(v["unavailable"] or v["unfinished"] for v in c["overheads"].values()) else ": ") +
                 ", ".join(f"{p} {v['weighted_seconds']:.3f} s" for p, v in c["overheads"].items()))
    mult = c["observed_multiplier"]
    lines.append(f"COST (run+G4+check+control)/run: observed {mult:.6f}x over {c['multiplier_paired_slices']} paired slices" if mult is not None else "COST overhead multiplier: unavailable")
    projected = c["projected_multiplier"]
    lines.append(f"COST projected total wall: {c['projected_total_wall_seconds']:.3f} s; multiplier " +
                 (f"{projected:.6f}x" if projected is not None else "pending (a ratio of lower bounds is not a bound)"))
    for i, row in c["chosen"].items():
        fmt = lambda k: "unavailable" if row.get(k) is None else f"{row[k]:.3f}"
        lines.append(f"COST slice {i}: step {fmt('step_seconds')} s{' lower-bound' if row['lower_bound'] else ''}; "
                     f"run {fmt('run_dag2_seconds')} s; G4 {fmt('g4_seconds')} s; check {fmt('check_seconds')} s; "
                     f"control {fmt('control_seconds')} s; checker RSS {fmt('check_peak_rss_kib')} KiB; "
                     f"disk-at-check {fmt('disk_at_check_bytes')} bytes; run RSS/disk peaks unavailable")
        lines.append(f"COST baseline slice {i}: t23 step {fmt('t23_step_seconds')} s, wall {fmt('t23_wall_seconds')} s; "
                     f"deltas step {fmt('step_delta_seconds')} s, wall {fmt('wall_delta_seconds')} s; {row['sample_group']}")
        lines.extend(f"COST slice {i} unavailable: {issue}" for issue in row["issues"])
    lines.append("COST longest by recorded run wall: " + ", ".join(f"s{r['slice']} {r.get('run_dag2_seconds')} s" for r in c["longest"]))
    lines.extend("COST note: " + note for note in c["notes"][2:])
    lines.extend(r["pending"])
    lines.extend("PROBLEM: " + p for p in r["problems"])
    lines.append(f"JUDGE {r['verdict']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--out", type=Path, help="write the complete JSON report outside fetched trees")
    ap.add_argument("--guarded", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    try:
        if not a.root.is_dir():
            raise ValueError("DISCOVERY: fleet root is not a directory")
        if a.out and a.out.resolve().is_relative_to(a.root.resolve()):
            raise ValueError("OUTPUT: report must be outside the fetched trees")
        plan = evidence.load(a.plan)
        plan_check(plan)
        if not a.guarded:
            print("Judging receipts and deriving the pinned Engel slice prediction...", file=sys.stderr, flush=True)
            os.environ["U24_MIN_AVAILABLE_MB"] = "1536"
            with tempfile.TemporaryDirectory(prefix="u24-judge-guard-") as tmp:
                log = Path(tmp) / "judge.log"
                # worker.measured starts in the repository root; preserve the
                # caller's relative-path meanings across that guarded re-exec.
                command = [sys.executable, "-B", str(Path(__file__).resolve()), str(a.root.resolve()),
                           "--plan", str(a.plan.resolve()), "--guarded"]
                if a.out:
                    command += ["--out", str(a.out.resolve())]
                measured = worker.measured(command, log, timed=True)
                print(log.read_text(), end="")
            if measured["memory_stop"]:
                if a.out:
                    a.out.write_text(json.dumps({"schema": "u24-fleet-judge-v1", "verdict": "PARTIAL", "exit": 3,
                                                 "pending": ["MEMORY STOP: MemAvailable below 1536 MiB"]}) + "\n")
                print("PENDING: memory guard stopped the judge below 1536 MiB available\nJUDGE PARTIAL")
                return 3
            return measured["exit"]
        with tempfile.TemporaryDirectory(prefix="u24-judge-") as tmp:
            report = judge(a.root, plan, Path(tmp))
        if a.out:
            a.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(render(report))
        return report["exit"]
    except (*READ_ERRORS, ImportError) as error:
        # A failed refresh must not leave an earlier OK report at --out. Keep
        # the read-only input-tree restriction even on this error path.
        if a.out and not a.out.resolve().is_relative_to(a.root.resolve()):
            try:
                a.out.write_text(json.dumps({"schema": "u24-fleet-judge-v1", "verdict": "FAIL", "exit": 1,
                                             "problems": [str(error)]}) + "\n")
            except OSError:
                pass  # stdout and exit 1 remain authoritative if output is unwritable
        print(f"PROBLEM: {error}\nJUDGE FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
