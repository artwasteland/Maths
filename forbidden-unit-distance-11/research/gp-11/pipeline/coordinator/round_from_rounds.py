#!/usr/bin/env python3
"""Allocate f3 from checked f1/f1b shards, then f2 and p2 overlays.

The base uses f1 first for each shard. Overlays must have been UNKNOWN in
that base; decisions are permanent and the latest still-UNKNOWN bytes travel.
Support records and displaced f1b records are checked for conflicting decisions
but do not change the allocation. This accepts no new certificates.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rounds import MAX_RECORD, bundle, codes, digest, write_json  # noqa: E402
from round_from_shards import shard_of  # noqa: E402

VERDICTS = ("embedded", "refuted", "unknown")
CLOUD = Path(__file__).resolve().parents[1] / "cloud"


def discover(root, name):
    found = {}
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or not directory.name.startswith(name + "-"):
            continue
        match = re.fullmatch(re.escape(name) + r"-([0-9]{3})", directory.name)
        if not match:
            raise ValueError("bundle_directory_name:" + str(directory))
        index = int(match[1])
        if index in found:
            raise ValueError(f"duplicate_shard_index:{name} index={index}")
        found[index] = directory
    return found


def remember_decision(decisions, code, verdict, directory):
    if verdict == "unknown":
        return
    previous = decisions.get(code)
    if previous and previous[0] != verdict:
        raise ValueError(f"conflicting_decisions:g6={code!r} "
                         f"first={previous[1]}:{previous[0]} other={directory}:{verdict}")
    decisions.setdefault(code, (verdict, str(directory)))


@dataclass
class CheckedBundle:
    assigned: set
    statuses: dict
    unknown: dict
    receipt: dict


def read_bundle(directory, name, index, decisions):
    summary = bundle(directory)  # Checks ACCEPT, completion, and every artifact hash.
    assigned = set(codes(directory / "assigned.g6"))
    frontier = set(codes(directory / "UNKNOWN.g6"))
    if not frontier <= assigned or len(frontier) != summary["counts"]["unknown"]:
        raise ValueError("round_frontier_coverage:" + str(directory))
    statuses, unknown, seen = {}, {}, set()
    with gzip.open(directory / "records.jsonl.gz", "rb") as stream:
        while line := stream.readline(MAX_RECORD + 1):
            if len(line) > MAX_RECORD:
                raise ValueError("record_size_cap:" + str(directory))
            record = json.loads(line)
            if (not isinstance(record, dict) or not isinstance(record.get("g6"), str)
                    or record.get("verdict") not in VERDICTS or not line.endswith(b"\n")):
                raise ValueError("round_record_shape:" + str(directory))
            code, verdict = record["g6"], record["verdict"]
            if code in seen:
                raise ValueError(f"round_record_duplicate:{directory} g6={code!r}")
            seen.add(code)
            remember_decision(decisions, code, verdict, directory)
            if code in assigned:
                statuses[code] = verdict
            if verdict == "unknown":
                if code not in frontier:
                    raise ValueError("round_frontier_coverage:" + str(directory))
                unknown[code] = line
    if set(unknown) != frontier:
        raise ValueError("round_frontier_coverage:" + str(directory))
    observed = {verdict: sum(v == verdict for v in statuses.values()) for verdict in VERDICTS}
    if (set(statuses) != assigned or observed != summary["counts"]
            or len(assigned) != summary["assigned_count"]):
        raise ValueError("round_record_coverage:" + str(directory))
    receipt = {"bundle": str(directory), "round": name, "shard_index": index,
               "summary_sha256": digest(directory / "summary.json"),
               "records_jsonl_gz_sha256": summary["artifacts"]["records.jsonl.gz"],
               "counts": summary["counts"], "assigned": len(assigned), "unknown": len(unknown),
               "supporting_records": len(seen - assigned)}
    return CheckedBundle(assigned, statuses, unknown, receipt)


def prepare(output, source, f1, f1b, f2, p2, *, shard_count=192, expected_count=17505,
            overlay_inputs=None):
    if output.exists():
        raise ValueError("round_output_exists")
    if shard_count < 1:
        raise ValueError("shard_count_positive")
    expected = set(codes(source))
    if len(expected) != expected_count:
        raise ValueError(f"base_input_count:expected={expected_count} actual={len(expected)}")
    inputs = overlay_inputs or {}
    first, fallback = discover(f1, "f1"), discover(f1b, "f1b")
    available = first.keys() | fallback.keys()
    missing = sorted(set(range(shard_count)) - available)
    extra = sorted(available - set(range(shard_count)))
    if missing:
        raise ValueError(f"base_missing_shards:indices={missing}")
    if extra:
        raise ValueError(f"base_extra_shards:indices={extra}")
    displaced_indices = sorted(first.keys() & fallback.keys())
    decisions, base, unknown, owners = {}, {}, {}, {}
    receipts, displaced = [], []
    assignments = {}
    for index in sorted(available):
        name, directory = ("f1", first[index]) if index in first else ("f1b", fallback[index])
        checked = read_bundle(directory, name, index, decisions)
        overlap = checked.assigned & base.keys()
        if overlap:
            indices = sorted({index} | {owners[c] for c in overlap})
            raise ValueError(f"base_duplicate_assignment:indices={indices} graphs={sorted(overlap)}")
        base.update(checked.statuses)
        unknown.update(checked.unknown)
        owners.update((code, index) for code in checked.assigned)
        assignments[index] = checked.assigned
        receipts.append(checked.receipt)

    absent, surplus = expected - base.keys(), base.keys() - expected
    if absent or surplus:
        raise ValueError(f"base_input_coverage:missing={len(absent)} extra={len(surplus)} "
                         f"missing_shards={sorted({shard_of(c, shard_count) for c in absent})} "
                         f"extra_shards={sorted({owners[c] for c in surplus})}")
    misplaced = {index for index, here in assignments.items()
                 if any(shard_of(code, shard_count) != index for code in here)}
    if misplaced:
        raise ValueError(f"base_shard_assignment:indices={sorted(misplaced)}")

    # Even unused copies must not contradict a checked decision. Their UNKNOWN
    # histories and decisions otherwise have no effect under the f1-first rule.
    for index in displaced_indices:
        checked = read_bundle(fallback[index], "f1b", index, decisions)
        if checked.assigned != assignments[index]:
            raise ValueError(f"displaced_shard_assignment:indices={[index]}")
        displaced.append(checked.receipt)

    base_unknown = set(unknown)
    final_status = dict(base)
    overlay_receipts, effects, previous_overlay = [], [], set()
    for name, root in (("f2", f2), ("p2", p2)):
        assigned, statuses, latest = set(), {}, {}
        counts = Counter({v: 0 for v in VERDICTS})
        for index, directory in sorted(discover(root, name).items()):
            checked = read_bundle(directory, name, index, decisions)
            if assigned & checked.assigned:
                raise ValueError(f"overlay_duplicate_assignment:{name} index={index}")
            assigned.update(checked.assigned)
            statuses.update(checked.statuses)
            latest.update(checked.unknown)
            counts.update(checked.receipt["counts"])
            overlay_receipts.append(checked.receipt)
        invalid = assigned - base_unknown
        if invalid:
            raise ValueError(f"overlay_base_not_unknown:{name} "
                             f"graphs={[(c, base.get(c, 'absent')) for c in sorted(invalid)]}")
        input_receipt = None
        if name in inputs:
            overlay_expected = set(codes(inputs[name]))
            if assigned != overlay_expected:
                raise ValueError(f"overlay_input_coverage:{name} "
                                 f"missing={len(overlay_expected-assigned)} extra={len(assigned-overlay_expected)}")
            input_receipt = {"input": str(inputs[name]), "sha256": digest(inputs[name]),
                             "count": len(overlay_expected)}
        effect = {"round": name, "assigned": len(assigned), "counts": dict(counts),
                  "input": input_receipt, "base_unknown_subset": True,
                  "overlap_with_previous_overlays": sorted(assigned & previous_overlay),
                  "all_in_previous_overlays": bool(assigned) and assigned <= previous_overlay,
                  "dropped_as_decided": 0, "dropped_by_verdict": {"embedded": 0, "refuted": 0},
                  "records_replaced": 0, "already_decided_same_verdict": 0,
                  "unknown_after_decision_ignored": 0}
        for code in sorted(assigned):
            verdict = statuses[code]
            if verdict != "unknown":
                if code in unknown:
                    del unknown[code]
                    effect["dropped_as_decided"] += 1
                    effect["dropped_by_verdict"][verdict] += 1
                else:
                    effect["already_decided_same_verdict"] += 1
                final_status[code] = verdict
            elif final_status[code] == "unknown":
                unknown[code] = latest[code]
                effect["records_replaced"] += 1
            else:
                effect["unknown_after_decision_ignored"] += 1
        previous_overlay.update(assigned)
        effect["remaining_unknown"] = len(unknown)
        effects.append(effect)

    selected = sorted(unknown)
    output.mkdir(parents=True)
    (output / "input.g6").write_text("".join(code + "\n" for code in selected))
    with (output / "unknown-records.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as target:
            for code in selected:
                target.write(unknown[code])
    manifest = {"schema": 1, "purpose": "frontier_allocation_only", "count": len(selected),
                "predecessors": receipts + overlay_receipts,
                "base": {"input": str(source), "input_sha256": digest(source),
                         "assigned": len(base), "shard_count": shard_count,
                         "shard_indices": sorted(assignments),
                         "counts": {v: sum(s == v for s in base.values()) for v in VERDICTS},
                         "bundles_by_round": dict(Counter(r["round"] for r in receipts))},
                "base_rule": "A shard returned by both rounds is used once, the f1 copy first.",
                "displaced_f1b_shards": displaced_indices, "displaced_f1b_bundles": displaced,
                "overlay_order": ["f2", "p2"], "overlay_effects": effects,
                "decision_rule": "Decisions persist; later UNKNOWN cannot restore a decided graph. "
                                 "All sources, including support and displaced records, must agree on decisions.",
                "bundle_unknown": len(base_unknown),
                "counts": {v: sum(s == v for s in final_status.values()) for v in VERDICTS},
                "excluded_decided_by_overlays": sum(e["dropped_as_decided"] for e in effects),
                "records_replaced_by_overlays": sum(e["records_replaced"] for e in effects),
                "excluded_decided_by_state": 0, "state": None, "added_unrun_shards": None,
                "helper_sha256": digest(Path(__file__)),
                "artifacts": {name: digest(output / name)
                              for name in ("input.g6", "unknown-records.jsonl.gz")}}
    write_json(output / "round.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", type=Path)
    parser.add_argument("--input", type=Path, default=CLOUD / "f1-input/input.g6")
    parser.add_argument("--f1", type=Path, required=True, help="parent of f1-NNN bundles")
    parser.add_argument("--f1b", type=Path, required=True, help="parent of f1b-NNN bundles")
    parser.add_argument("--f2", type=Path, required=True, help="parent of f2-NNN bundles")
    parser.add_argument("--p2", type=Path, required=True, help="parent of p2-NNN bundles")
    parser.add_argument("--f2-input", type=Path, default=CLOUD / "f2-input/input.g6")
    parser.add_argument("--p2-input", type=Path, default=CLOUD / "p2-input/input.g6")
    parser.add_argument("--shard-count", type=int, default=192)
    parser.add_argument("--expected-count", type=int, default=17505)
    args = parser.parse_args()
    try:
        manifest = prepare(args.output, args.input, args.f1, args.f1b, args.f2, args.p2,
                           shard_count=args.shard_count, expected_count=args.expected_count,
                           overlay_inputs={"f2": args.f2_input, "p2": args.p2_input})
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(manifest, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
