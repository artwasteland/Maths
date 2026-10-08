#!/usr/bin/env python3
"""B11 G6 writer. New reviewed logic; no GP-10 file is modified.

B11 W1: complete B11 report/list and current artifact receipts, never fixture11.
B11 W2: require G0..G5 evidence, prior-commit attestations and current review hashes.
B11 W3: render only checker counts/list; protect evidence from output collisions.
The gate file contains attestations, not mathematical certificates. See FORMAT.md.
"""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "check"))
import gp11check as ck


def validate_report(report, checked, expected_hash):  # B11 W1.
    ck.need(isinstance(report, dict) and report.get("status") == "ACCEPT"
            and report.get("reason") == "verified", "writer_not_accepted")
    ck.need(report.get("profile") == "B11", "writer_profile")
    ck.need(isinstance(report.get("counts"), dict), "writer_counts")
    ck.need(report.get("counts", {}).get("unknown") == 0 and report.get("conditional") is False
            and report.get("conditional_minimal") == [], "writer_conditional")
    ck.need(report.get("direct_rejections") == 0, "writer_rejections")
    ck.need(report.get("profile_sources") == ck.source_hashes(), "writer_source_hash")
    ck.need(report.get("input_sha256") == expected_hash == report.get("frozen_B11_sha256")
            and ck.digest(ck.GP11 / "data/B11.g6") == expected_hash, "writer_input_hash")
    counts = report["counts"]
    ck.need(set(counts) == {"embedded", "refuted", "unknown"}
            and all(type(n) is int and n >= 0 for n in counts.values())
            and sum(counts.values()) == report.get("input_count") == 448708, "writer_counts")
    ck.need(report.get("minimal_file") == "L11.g6", "writer_minimal_file")
    minimal = ck.graph_list(checked / "L11.g6")
    ck.need(minimal == report.get("minimal") and len(minimal) == report.get("minimal_count")
            and all(ck.decode(c).n == 11 for c in minimal)
            and len(minimal) + report.get("nonminimal_count", -1) == counts["refuted"], "writer_minimal_list")
    return minimal


def validate_gates(gates, run, checked, report):  # B11 W2.
    ck.keys(gates, {f"G{i}" for i in range(6)}, where="publication gates")
    protected = set()
    for name, gate in gates.items():
        ck.need(isinstance(gate, dict) and gate.get("status") == "PASS", "writer_gate_open", name)
        evidence = gate.get("evidence")
        ck.need(isinstance(evidence, list) and bool(evidence), "writer_gate_evidence", name)
        for item in evidence:
            ck.keys(item, {"path", "sha256"}, where="gate evidence")
            path = ck.relative(run, item["path"])
            ck.need(path.is_file() and ck.digest(path) == item["sha256"], "writer_evidence_hash", name)
            protected.add(path)
    ck.need(gates["G0"].get("input_sha256") == report["input_sha256"], "writer_g0_input")
    ck.need(gates["G1"].get("sources") == ck.source_hashes()
            and gates["G1"].get("selftest_committed") is True, "writer_g1_sources")
    ck.need(gates["G2"].get("predictions_sha256") == report.get("predictions", {}).get("sha256")
            and gates["G2"].get("predictions_committed_before_run") is True, "writer_prediction_chronology")
    ck.need(gates["G3"].get("report_sha256") == ck.digest(checked / "report.json"), "writer_report_hash")
    ck.need(gates["G4"].get("L11_sha256") == ck.digest(checked / "L11.g6"), "writer_g4_list")
    review = gates["G5"]
    ck.need(review.get("sources") == ck.source_hashes(), "writer_stale_review")
    ck.need(review.get("findings_answered") is True and isinstance(review.get("outside_reviewer"), str)
            and bool(review["outside_reviewer"].strip()), "writer_review_open")
    return protected


def write_result(run, checked, gates_path, output, expected_hash):  # B11 W1,W2,W3.
    run, checked, gates_path, output = (Path(p).resolve() for p in (run, checked, gates_path, output))
    report = ck.read_json(checked / "report.json")
    minimal = validate_report(report, checked, expected_hash)
    gates = ck.read_json(gates_path)
    protected = validate_gates(gates, run, checked, report)
    artifacts = report.get("artifacts")
    ck.need(isinstance(artifacts, dict) and bool(artifacts), "writer_artifacts")
    # Reconstruct the required set; a receipt missing a consumed file is not sufficient.
    required = ck.input_paths(run) | {checked / p for p in ("L11.g6", "minimality.jsonl", "records.jsonl", "unknown-budgets.jsonl")}
    for path in ck.control_report_paths(run):
        required.add(path)
        control = ck.read_json(path)
        if "minimal_file" in control:
            required.add(path.parent / control["minimal_file"])
    for path in required:
        key = ck.os.path.relpath(path, run)
        ck.need(key in artifacts, "writer_artifact_missing", key)
    for name, sha in artifacts.items():
        path = ck.relative(run, name)
        ck.need(path.is_file() and ck.digest(path) == sha, "writer_artifact_hash", name)
        protected.add(path)
    ck.consumed_receipts(run, report, artifacts)
    controls = report.get("controls")
    ck.need(isinstance(controls, dict) and set(controls) == set(ck.CONTROL_NAMES), "writer_controls")
    manifest = ck.read_json(run / "run.json")
    ck.need(manifest.get("profile") == "B11" and set(manifest.get("controls", {})) == set(ck.CONTROL_NAMES), "writer_controls")
    checker = ck.Checker()
    for name, item in controls.items():
        path = ck.relative(run, item["path"])
        expected = (ck.relative(run, manifest["controls"][name]) / "checked/report.json").resolve()
        ck.need(path == expected and path.is_relative_to(run), "writer_control_path", name)
        ck.need(ck.digest(path) == item["sha256"], "writer_control_hash", name)
        control = ck.read_json(path)
        ck.need(control.get("status") == "ACCEPT" and control.get("profile") == name, "writer_control_not_accepted", name)
        if name == "B10":
            provenance = ck.complete_b10(control, path.parent, checker)
            ck.need(provenance == report.get("F10_provenance"), "writer_f10_provenance")
        else:
            ck.need(control.get("control", {}).get("status") == "PASS", "writer_control_not_pass", name)
    protected.update((checked / "report.json", gates_path))
    protected.update(ck.ROOT / p for p in ck.source_hashes())
    ck.need(output not in protected, "writer_output_collision")
    counts = report["counts"]
    by_edges = Counter(len(ck.decode(c).edges) for c in minimal)
    text = ["# GP-11 result", "", "Generated from the B11 checker report and L11.g6 after G0 to G5.", "",
            f"A graph on at most 11 vertices is a unit-distance graph if and only if it contains none of the "
            f"398 graphs of `forbidden-398.json` and none of the {len(minimal)} graphs in `L11.g6`.", "",
            "This rests on GP-10's result and Globus and Parshall's classification, re-derived by the controls.", "",
            f"Candidates: {report['input_count']}. Embedded: {counts['embedded']}. Refuted: {counts['refuted']}. "
            f"Unknown: {counts['unknown']}. Minimal forbidden: {len(minimal)}.", "",
            f"B11 sha256: `{report['input_sha256']}`.", "",
            f"Report sha256: `{ck.digest(checked / 'report.json')}`.", "",
            "| Edges | Minimal forbidden graphs |", "|---:|---:|",
            *[f"| {edges} | {n} |" for edges, n in sorted(by_edges.items())], "", "```",
            *minimal, "```", ""]
    temporary = output.with_name(output.name + ".tmp")
    ck.need(temporary not in protected, "writer_output_collision")
    temporary.write_text("\n".join(text))
    temporary.replace(output)
    return len(minimal)


def main(argv=None):  # B11 W3.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("gates", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--checked", type=Path)
    parser.add_argument("--b11-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        count = write_result(args.run, args.checked or args.run / "checked", args.gates, args.output, args.b11_sha256)
        print(f"WROTE {args.output}: {count} members")
        return 0
    except (ck.Rejection, OSError, ValueError, TypeError, KeyError) as exc:
        print("REFUSED " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
