#!/usr/bin/env python3
"""B11 profile around the unchanged, G5-closed GP-10 verifier. NEW REVIEW REQUIRED.

B11 1: pin/import the frozen verifier, kernel, F9, gadgets, F10 and AMP instances; source receipts.
B11 2: extend the pattern table through ten, preserving indices and the default nine.
B11 3: reconstruct blocks through ten; explicitly search through ten (not default nine).
B11 4: separate B11, named11 and fixture11 orchestration; external B11 hash pin,
       frozen-file equality, 448708 candidates, L11 cleanup and input/output guards.
B11 5: replay same-tree controls; require COMPLETE B10 and exact derived F10 provenance.
B11 6: L-min through eleven; retain GP-10's conditional and refuted-deletion semantics.
B11 7: named11's two AMP graphs, direct embeddings and general-search provenance.
B11 8: hash receipts for consumed artifacts; legacy profiles delegate without proof edits.
B11 9: CLI, including an explicit complete-B10 control check for the cloud replay.

Every added/overridden function is marked B11 below. No producer is imported.
Base gp10check.py: d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04.
Kernel udcheck.py: 63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de.
fixture11 exercises the new rules with small inputs; it is NEVER a B11 result.
Control evidence proves the F10 premise only after an actual full replay.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
GP11 = HERE.parent
ROOT = GP11.parents[1]
GP10 = GP11.parent / "gp-10"
U22 = GP11.parent / "unit-distance-22"
PINS = {
    GP10 / "check/gp10check.py": "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04",
    U22 / "check/udcheck.py": "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de",
    U22 / "data/forbidden-74.json": "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
    U22 / "data/forbidden-398.json": "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c",
    U22 / "data/tu-gadgets.json": "a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629",
    U22 / "sources/amp/anc/graph6.txt": "4f7da8729d4818712e8718daabce29fb7f423cd7abec07eb195f0a04d6601a49",
}
# Check before executing imported source, including the kernel's later lazy import.
for _path, _sha in PINS.items():
    if hashlib.sha256(_path.read_bytes()).hexdigest() != _sha:
        raise RuntimeError("frozen_source_hash: " + str(_path))
_spec = importlib.util.spec_from_file_location("gp11_frozen_gp10", GP10 / "check/gp10check.py")
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)
need = base.need
PROFILE_AT_IMPORT = base.digest(Path(__file__))
CONTROL_NAMES = (*base.CONTROL_ORDERS, "B10", "named11", "regressions")
NEW_PROFILES = ("B11", "fixture11", "named11")
PRODUCTS = ("report.json", "report.json.tmp", "L11.g6", "minimal.g6", "minimality.jsonl",
            "records.jsonl", "unknown-budgets.jsonl")


def __getattr__(name):  # B11 8: expose unchanged helpers to the regression adapter.
    return getattr(base, name)


def verify_frozen():  # B11 1: also guard long-lived callers after import.
    for path, sha in PINS.items():
        need(base.digest(path) == sha, "frozen_source_hash", str(path.relative_to(ROOT)))


def source_hashes():  # B11 1: the exact review surface, shared with the writer.
    need(base.digest(Path(__file__)) == PROFILE_AT_IMPORT, "profile_changed_since_import")
    paths = [*PINS, GP11 / "CONTRACT.md", GP11 / "PROOFS.md",
             Path(__file__), GP11 / "tools/write_result.py", HERE / "selftest.py"]
    return {str(p.relative_to(ROOT)): base.digest(p) for p in paths}


def input_paths(directory, stack=()):  # B11 8: retain every input, including nested controls.
    directory = Path(directory).resolve()
    need(directory not in stack and len(stack) < 8, "control_cycle")
    m = base.read_json(directory / "run.json")
    need(isinstance(m, dict), "schema", "run manifest must be an object")
    need(isinstance(m.get("records"), list) and bool(m["records"]), "record_files")
    need(isinstance(m.get("controls", {}), dict), "controls_required")
    values = ["run.json", m["input"], m.get("unknown", "UNKNOWN.g6"), *m["records"]]
    values += [m[k] for k in ("hosts", "minimal_claim", "cross_checks", "provenance") if k in m]
    if "predictions" in m:
        values.append(m["predictions"]["path"])
    paths = {base.relative(directory, p) for p in values}
    for value in m.get("controls", {}).values():
        child = base.relative(directory, value)
        need(child.is_relative_to(directory) and child != directory, "control_outside_run_tree")
        paths.update(input_paths(child, (*stack, directory)))
    return paths


def artifact_hashes(directory, paths):  # B11 8: portable paths relative to the run root.
    return {os.path.relpath(p, directory): base.digest(p) for p in sorted(paths)}


def control_report_paths(directory, stack=()):  # B11 8: only controls the manifests actually name.
    directory = Path(directory).resolve()
    need(directory not in stack and len(stack) < 8, "control_cycle")
    result = set()
    controls = base.read_json(directory / "run.json").get("controls", {})
    need(isinstance(controls, dict), "controls_required")
    for value in controls.values():
        child = base.relative(directory, value)
        need(child.is_relative_to(directory) and child != directory, "control_outside_run_tree")
        report = child / "checked/report.json"
        need(report.resolve().is_relative_to(directory), "control_outside_run_tree")
        result.add(report)
        result.update(control_report_paths(child, (*stack, directory)))
    return result


def consumed_receipts(directory, report, snapshot):  # B11 8: bind streamed bytes, not just before/after files.
    for row in report["files"]:
        name = os.path.relpath(row["path"], directory)
        need(snapshot.get(name) == row["sha256"], "consumed_record_hash", name)


class Checker(base.Checker):
    def __init__(self, forbidden_limit=9):  # B11 2: the new entries are withheld below ten.
        verify_frozen()
        need(type(forbidden_limit) is int and 0 <= forbidden_limit <= 10, "forbidden_limit")
        super().__init__(min(forbidden_limit, 9))
        raw = base.read_json(U22 / "data/forbidden-398.json")
        need(raw[:74] == base.read_json(U22 / "data/forbidden-74.json"), "f10_prefix")
        extra = [base.Graph(1 + max(max(e) for e in es), {tuple(sorted(e)) for e in es}) for es in raw[74:]]
        need(len(extra) == 324 and all(g.n == 10 for g in extra), "f10_orders")
        self.forbidden_limit = forbidden_limit
        self.forbidden.extend(extra)
        self.forbidden_codes.extend(base.canonical_many([base.encode(g) for g in extra]))
        need(len(set(self.forbidden_codes)) == 398, "f10_duplicates")
        self.patterns.extend(g.nx() for g in extra)

    def block_evidence(self, graph, max_order):  # B11 3: two deliberate deltas from GP-10.
        target = graph.nx()
        need(not base.nx.is_biconnected(target), "block_is_biconnected")
        covered, evidence = set(), []
        for vertices in base.nx.biconnected_components(target):
            vertices = sorted(vertices)
            block = target.subgraph(vertices)
            need(len(vertices) <= max_order <= 10, "block_order")
            edges = {tuple(sorted(e)) for e in block.edges}
            need(not (covered & edges), "block_overlap")
            covered.update(edges)
            reindex = {v: i for i, v in enumerate(vertices)}
            small = base.Graph(len(vertices), {tuple(sorted((reindex[u], reindex[v]))) for u, v in edges})
            need(self.contains_forbidden(small, limit=10) is None, "block_forbidden")
            evidence.append({"vertices": vertices, "edges": [list(e) for e in sorted(edges)]})
        need(covered == graph.edges, "block_edge_coverage")
        return {"blocks": evidence, "isolated": list(base.nx.isolates(target))}


def complete_b10(report, output, checker):  # B11 5: ordinary ACCEPT also permits partial runs.
    need(isinstance(report, dict) and report.get("status") == "ACCEPT" and report.get("profile") == "B10"
         and report.get("reason") == "verified", "b10_not_accepted")
    need(isinstance(report.get("counts"), dict) and report["counts"].get("unknown") == 0 and report.get("conditional") is False
         and report.get("conditional_minimal") == [] and report.get("direct_rejections") == 0,
         "b10_incomplete")
    need(report.get("forbidden_limit") == 9 and report.get("input_count") == 33162
         and report.get("input_sha256") == base.digest(GP10 / "data/B10.g6"), "b10_control_input")
    need(report.get("minimal_file") == "L10.g6", "b10_minimal_file")
    actual = base.graph_list(Path(output) / "L10.g6")
    expected = sorted(c for c, g in zip(checker.forbidden_codes, checker.forbidden) if g.n == 10)
    need(len(actual) == 324 and actual == expected and report.get("minimal") == actual
         and report.get("minimal_count") == 324, "b10_derived_list")
    return {"status": "COMPLETE", "members": len(actual), "L10_sha256": base.digest(Path(output) / "L10.g6"),
            "forbidden_sha256": base.digest(U22 / "data/forbidden-398.json")}


class Run(base.Run):
    def __init__(self, directory, output=None, emit=print, b11_sha256=None):  # B11 4.
        super().__init__(directory, output, emit)
        self.b11_sha256 = b11_sha256

    def execute(self, stack=()):  # B11 4,8: legacy decisions delegate; new ones use the methods below.
        try:
            verify_frozen()
            m = base.read_json(self.directory / "run.json")
            need(isinstance(m, dict), "schema", "run manifest must be an object")
            if m.get("profile") not in NEW_PROFILES:
                # The old runner also owns its error ordering and output-collision protection.
                result = base.Run(self.directory, self.output, self.emit).execute(stack)
                if result["status"] == "ACCEPT":
                    result["profile_sources"] = source_hashes()
                    base.json_write(self.output / "report.json", result)
                self.summary = result
                return result
            self.manifest = m
            base.keys(m, {"profile", "input", "input_sha256", "records"},
                      {"hosts", "unknown", "minimal_claim", "cross_checks", "controls", "provenance",
                       "predictions", "forbidden_limit", "derive"}, "run manifest")
            need(isinstance(m["records"], list) and bool(m["records"]), "record_files")
            paths = input_paths(self.directory)
            need(not paths & {(self.output / p).resolve() for p in PRODUCTS}, "output_input_collision")
            for value in m.get("controls", {}).values():
                control = base.relative(self.directory, value)
                need(not self.output.is_relative_to(control), "output_control_collision")
        except (base.Rejection, OSError, ValueError, TypeError, KeyError) as exc:
            self.summary.update(reason=exc.reason if isinstance(exc, base.Rejection) else "checker_error", detail=str(exc))
            self.emit("REJECT run " + self.summary["reason"])
            return self.summary
        self.output.mkdir(parents=True, exist_ok=True)
        base.json_write(self.output / "report.json", {**self.summary, "reason": "checking"})
        for name in PRODUCTS:
            if name not in ("report.json", "report.json.tmp"):
                (self.output / name).unlink(missing_ok=True)
        started = time.monotonic()
        try:
            need(self.directory not in stack and len(stack) < 8, "control_cycle")
            self.profile = m["profile"]
            fixture = self.profile == "fixture11"
            need(self.profile == "B11" or not ({"controls", "predictions"} & set(m)), "profile_override")
            need(self.profile == "named11" or "provenance" not in m, "profile_override")
            need(fixture or not ({"forbidden_limit", "derive"} & set(m)), "profile_override")
            need("derive" not in m or type(m["derive"]) is bool, "schema", "derive must be boolean")
            self.limit = m.get("forbidden_limit", 10) if fixture else (10 if self.profile == "B11" else 0)
            self.input = base.relative(self.directory, m["input"])
            need(base.digest(self.input) == m["input_sha256"], "input_hash")
            if self.profile == "B11":
                self.frozen_input()
                paths.update((GP11 / "data/B11.g6", GP11 / "data/SHA256SUMS"))
            if self.profile == "named11":
                paths.add(U22 / "sources/amp/anc/graph6.txt")
            before = artifact_hashes(self.directory, paths)
            self.summary.update(profile=self.profile, input_sha256=m["input_sha256"], forbidden_limit=self.limit,
                                checker_sha256=PINS[GP10 / "check/gp10check.py"],
                                kernel_sha256=PINS[U22 / "check/udcheck.py"], profile_sources=source_hashes(),
                                trusted_data_sha256={p.name: base.digest(p) for p in
                                    (U22 / "data/forbidden-398.json", U22 / "data/tu-gadgets.json")})
            self.checker = Checker(self.limit)
            if self.profile == "B11":
                self.controls((*stack, self.directory))
            else:
                self.summary["scope"] = "fixture-only" if fixture else "named-control-only"
            base.SCRATCH.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="gp11-", dir=base.SCRATCH) as tmp:
                self.db = sqlite3.connect(str(Path(tmp) / "index.sqlite"))
                try:
                    self.db.executescript("""
                      PRAGMA cache_size=-8192; PRAGMA temp_store=FILE;
                      CREATE TABLE inputs(g6 TEXT PRIMARY KEY);
                      CREATE TABLE records(g6 TEXT PRIMARY KEY, verdict TEXT, host INTEGER, dep TEXT,
                        status TEXT, reason TEXT, details TEXT);
                      CREATE INDEX dependency ON records(dep);
                    """)
                    with (self.output / "records.jsonl").open("w") as self.record_log:
                        self.load_input()
                        self.load_records()
                        self.resolve()
                        self.coverage()
                        self.unknowns()
                        self.cross_checks()
                        if self.profile == "B11" or (fixture and m.get("derive", False)):
                            self.minimality()
                        else:
                            need("minimal_claim" not in m, "minimality_not_requested")
                            self.summary.update(minimal=[], conditional_minimal=[])
                        self.profile_controls()
                finally:
                    self.db.close()
            need(before == artifact_hashes(self.directory, paths), "inputs_changed_during_check")
            consumed_receipts(self.directory, self.summary, before)
            need(self.summary["profile_sources"] == source_hashes(), "sources_changed_during_check")
            paths.update(p for p in self.output.iterdir() if p.name in PRODUCTS and p.name != "report.json")
            for report_path in control_report_paths(self.directory):
                report = base.read_json(report_path)
                consumed_receipts(self.directory, report, before)
                paths.add(report_path)
                if "minimal_file" in report:
                    paths.add(report_path.parent / report["minimal_file"])
            self.summary["artifacts"] = artifact_hashes(self.directory, paths)
            self.summary.update(status="ACCEPT", reason="verified")
        except (base.Rejection, OSError, ValueError, TypeError, KeyError, RecursionError, MemoryError, sqlite3.Error) as exc:
            self.summary.update(reason=exc.reason if isinstance(exc, base.Rejection) else "checker_error", detail=str(exc))
        self.summary["elapsed_seconds"] = time.monotonic() - started
        self.summary["environment"] = base.environment()
        base.json_write(self.output / "report.json", self.summary)
        self.emit(self.summary["status"] + " run " + self.summary["reason"])
        return self.summary

    def frozen_input(self):  # B11 4: the producer's self-declared hash is insufficient.
        need(isinstance(self.b11_sha256, str) and len(self.b11_sha256) == 64
             and all(c in "0123456789abcdef" for c in self.b11_sha256), "b11_hash_required")
        need(self.manifest["input_sha256"] == self.b11_sha256, "frozen_input_hash")
        frozen = GP11 / "data/B11.g6"
        need(frozen.is_file() and base.digest(frozen) == self.b11_sha256, "frozen_input_hash")
        sums = {name: sha for sha, name in (line.split() for line in (GP11 / "data/SHA256SUMS").read_text().splitlines())}
        need(sums.get("B11.g6") == self.b11_sha256, "frozen_input_hash")
        self.summary["frozen_B11_sha256"] = self.b11_sha256

    def load_input(self):  # B11 4: inherited streaming/canonical coverage, then order and count.
        super().load_input()
        for (code,) in self.db.execute("SELECT g6 FROM inputs"):
            graph = base.decode(code)
            need(graph.n == 11, "input_graph_class")
            if self.profile == "B11":
                need(base.nx.is_biconnected(graph.nx()), "input_graph_class")
        if self.profile == "B11":
            need(self.summary["input_count"] == 448708, "b11_input_count")

    def control_reports(self):  # B11 5: reject incomplete prerequisites before a heavy replay.
        controls = self.manifest.get("controls")
        need(isinstance(controls, dict), "controls_required")
        need(set(controls) == set(CONTROL_NAMES), "controls_required")
        reports = {}
        for name in CONTROL_NAMES:
            path = base.relative(self.directory, controls[name])
            need(path.is_relative_to(self.directory) and path != self.directory, "control_outside_run_tree")
            report_path = path / "checked/report.json"
            need(report_path.resolve().is_relative_to(self.directory), "control_outside_run_tree")
            need(report_path.is_file(), "control_report_missing", name)
            old = base.read_json(report_path)
            need(isinstance(old, dict) and old.get("status") == "ACCEPT" and old.get("profile") == name,
                 "control_report_not_accepted", name)
            if name == "B10":
                complete_b10(old, path / "checked", self.checker)
            reports[name] = path
        return reports

    def controls(self, stack):  # B11 5: accepted reports never substitute for certificate replay.
        accepted = {}
        reports = self.control_reports()
        for name, path in reports.items():
            report_path = path / "checked/report.json"
            replay = Run(path, emit=self.emit).execute(stack)
            need(replay["status"] == "ACCEPT" and replay.get("profile") == name, "control_replay_failed", name)
            if name == "B10":
                self.summary["F10_provenance"] = complete_b10(replay, path / "checked", self.checker)
            else:
                need(replay.get("control", {}).get("status") == "PASS", "control_not_pass", name)
        # A B10 replay can refresh a nested lower control also named by B11.
        for name, path in reports.items():
            report_path = path / "checked/report.json"
            accepted[name] = {"path": str(report_path.relative_to(self.directory)), "sha256": base.digest(report_path)}
        prediction = self.manifest.get("predictions")
        base.keys(prediction, {"path", "sha256"}, where="predictions")
        path = base.relative(self.directory, prediction["path"])
        need(path.is_relative_to(self.directory) and base.digest(path) == prediction["sha256"]
             and path.stat().st_size > 0, "predictions_hash")
        self.summary["controls"] = accepted
        self.summary["predictions"] = {**prediction, "chronology": "requires G2 attestation of prior commit"}

    def minimality(self):  # B11 6: GP-10's algorithm, with order eleven and L11 output.
        minimal, conditional, ruled_out = [], [], {}
        outname = "L11.g6" if self.profile == "B11" else "minimal.g6"
        with (self.output / "minimality.jsonl").open("w") as evidence:
            for (code,) in self.db.execute("SELECT g6 FROM records WHERE host=0 AND verdict='refuted' ORDER BY g6"):
                g = base.decode(code)
                need(4 <= g.n <= 11 and base.nx.is_biconnected(g.nx()), "minimality_graph_class", code)
                need(self.checker.contains_forbidden(g, self.limit) is None, "minimality_not_free", code)
                rows, biconnected = [], []
                for e in sorted(g.edges):
                    deletion = base.Graph(g.n, g.edges - {e})
                    if base.nx.is_biconnected(deletion.nx()):
                        biconnected.append((e, base.encode(deletion)))
                    else:
                        rows.append({"edge": list(e), "verdict": "embedded_by_blocks",
                                     **self.checker.block_evidence(deletion, g.n - 1)})
                for (e, _), child in zip(biconnected, base.canonical_many([c for _, c in biconnected])):
                    row = self.db.execute("SELECT verdict,status FROM records WHERE g6=?", (child,)).fetchone()
                    need(row is not None and row[1] == "ACCEPT", "minimality_deletion_missing", child)
                    rows.append({"edge": list(e), "g6": child, "verdict": row[0]})
                refuted = sorted({r["g6"] for r in rows if r["verdict"] == "refuted"})
                unknown = sorted({r["g6"] for r in rows if r["verdict"] == "unknown"})
                if refuted:
                    status = "not_minimal"
                    ruled_out[code] = refuted
                else:
                    minimal.append(code)
                    status = "minimal" if not unknown else "minimal_if_all_listed_deletions_embed"
                    if unknown:
                        conditional.append({"g6": code, "requires_embedded": unknown})
                evidence.write(json.dumps({"g6": code, "status": status, "deletions": rows}) + "\n")
        (self.output / outname).write_text("".join(c + "\n" for c in minimal), encoding="ascii")
        self.summary.update(minimal=minimal, minimal_count=len(minimal), minimal_file=outname,
                            conditional_minimal=conditional, nonminimal_count=len(ruled_out))
        if "minimal_claim" in self.manifest:
            claim = base.graph_list(base.relative(self.directory, self.manifest["minimal_claim"]))
            need(not set(claim) & set(ruled_out), "minimality_claim_refuted_deletion")
            need(claim == minimal, "minimality_claim_mismatch")

    def profile_controls(self):  # B11 7: source graph6 only, never a coordinate lookup.
        if self.profile != "named11":
            self.summary["control"] = "not_a_control"
            return
        source = U22 / "sources/amp/anc/graph6.txt"
        names = [c for c in source.read_text().splitlines() if base.decode(c).n == 11]
        need(len(names) == 2 and all(len(base.decode(c).edges) == 23 for c in names), "named11_source")
        expected = dict.fromkeys(base.canonical_many(names), "embedded")
        self.expected_verdicts(expected)
        need("provenance" in self.manifest, "control_provenance_missing")
        provenance = base.read_json(base.relative(self.directory, self.manifest["provenance"]))
        need(isinstance(provenance, dict) and set(provenance) == set(expected), "control_provenance_set")
        for code, row in provenance.items():
            base.keys(row, {"method", "evidence"}, where="provenance")
            need(row["method"] == "general-search" and isinstance(row["evidence"], str)
                 and row["evidence"].strip(), "control_not_general_search")
            need(self.db.execute("SELECT dep FROM records WHERE g6=?", (code,)).fetchone()[0] is None,
                 "control_library_pointer")
        self.summary["control"] = {"status": "PASS", "provenance": "general-search asserted by producer; not proved by certificates"}


def main(argv=None):  # B11 9.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--b11-sha256")
    parser.add_argument("--require-complete-b10", action="store_true")
    args = parser.parse_args(argv)
    run = Run(args.run_directory, args.output, b11_sha256=args.b11_sha256)
    result = run.execute()
    if result["status"] != "ACCEPT":
        return 1
    if args.require_complete_b10:
        try:
            receipt = complete_b10(result, run.output, Checker())
            base.json_write(run.output / "F10-provenance.json", receipt)
            print("PASS B10 COMPLETE derived=324")
        except base.Rejection as exc:
            print("REJECT B10 " + str(exc))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
