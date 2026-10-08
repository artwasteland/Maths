#!/usr/bin/env python3
"""Evidence-mutation tests, never modifying the evidence repository.

    U24_TEST_REPO=REPO [U24_TEST_ROOT=FLEET] \
        nice -n 15 timeout 1800 /usr/bin/python3 -B -m unittest -v test_write_result

The COMPLETE fixture copies the real saved inputs and adds a synthetic audit in
the actual u24-fleet-audit-v1 schema and an explicit CLOSED G1 record. Every red test changes a copied INPUT FILE,
then invokes the generator afresh. The final, lexically last test regenerates
from the untouched real files, compares all outputs with the first generation
apart from the generation timestamp, verifies no input digest changed, and writes
the real outputs beside the generator. All scratch writes are beside this file.
"""

import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest import mock

import write_result as wr

# Scratch and the final regeneration's outputs go outside the repository (2026-10-07: writing beside the
# generator left RESULT-u24.md and the values files in tools/). U24_TEST_WORK names a directory to keep them.
WORK = Path(os.environ.get("U24_TEST_WORK") or tempfile.mkdtemp(prefix="u24-write-result-tests-")).resolve()
REAL_REPO = Path(os.environ.get("U24_TEST_REPO", wr.REPO)).resolve()
REAL_ROOT = os.environ.get("U24_TEST_ROOT")
EVIDENCE = Path("research/unit-distance-24/evidence/judge-final-2026-10-07-r2")
ORIGINAL_EVIDENCE = Path("research/unit-distance-24/evidence/judge-final-2026-10-06")
U24 = Path("research/unit-distance-24")


def load_gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def save_gz(path, obj):
    path.write_bytes(gzip.compress((json.dumps(obj, sort_keys=True) + "\n").encode(), mtime=0))


def headline(doc):
    match = re.search(r"^\*\*Headline: (COMPLETE|INCOMPLETE)\.\*\*", doc, re.M)
    if not match:
        raise AssertionError("headline absent")
    return match[1]


def failing_gates(values):
    return [r["gate"] for r in values["gate_table"] if r["status"] == "not met"]


def synthetic_audit(repo):
    """A complete audit of exactly the copied reports, not a generic OK label."""
    reports = {p: load_gz(repo / EVIDENCE / f"judge-{p}.json.gz") for p in wr.PLANS}
    slices = sorted({i for j in reports.values() for i in j["accepted_slices"]})
    copies = sum(j["accepted_copies"] for j in reports.values())
    names = {"pilot": "pilot", "full": "full", "phaseb": "phaseB"}
    fleet = copy.deepcopy(reports["pilot"]["summary"]["record"]["fleets"][0])
    fleet.update(summaries=copies, slice_indices=len(slices), missing_slices=0,
                 prefix_files_identical_in=copies, g4_results={"PASS": copies})
    # Correct the whole-fleet parent shares in this synthetic completed audit.
    for row in fleet["slice_partition"].values():
        row.update(sum=row["stage_file"], slices_recording=len(slices))
    for key in ("children", "kept"):
        fleet["target_cell"][key] = sum(j["summary"]["record"]["fleets"][0]["target_cell"][key] for j in reports.values())
    record = copy.deepcopy(reports["pilot"]["summary"]["record"])
    record.update(runs=copies, audited=copies, fleets=[fleet], problems=0, unresolved=0)
    return {"schema": "u24-fleet-audit-v1", "verdict": "OK", "exit": 0,
            "checker_sha256": reports["pilot"]["provenance"]["checker_sha256"],
            "plans": {names[p]: {"plan": j["provenance"]["plan"]["job"], "plan_sha256": "synthetic",
                                   "verdict": j["verdict"], "exit": j["exit"],
                                   "accepted_slices": j["accepted_slices"], "staged_copies": j["accepted_copies"],
                                   "per_plan_audit_total": len(j["accepted_slices"])} for p, j in reports.items()},
            "union_copies": copies, "union_slices": len(slices),
            "audit": {"status": "complete", "problems": [], "unresolved": [], "missing_slices": 0,
                      "exit": 3, "record": record},
            "coverage_lines": ["COVERAGE (summary only) OK: synthetic complete fixture"], "problems": []}


def normalize_doc(doc):
    return re.sub(r"Generated \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", "Generated TIMESTAMP", doc)


def normalize_values_bytes(raw):
    # Preserve every byte, including ordering and whitespace, except the exact
    # generation timestamp (top-level metadata and its provenance value).
    timestamp = json.loads(raw)["generated_utc"].encode()
    return raw.replace(b'"' + timestamp + b'"', b'"TIMESTAMP"')


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (REAL_REPO / U24 / "CONTRACT.md").exists():
            raise RuntimeError("set U24_TEST_REPO to the real evidence repository")
        cls.scratch = tempfile.TemporaryDirectory(prefix="write-result-tests-", dir=WORK)
        cls.work = Path(cls.scratch.name)
        cls.first_args = wr.options(["--repo", str(REAL_REPO), "--out", str(cls.work / "first/RESULT-u24.md"),
                                     "--values", str(cls.work / "first/result-values.json")] +
                                    (["--root", REAL_ROOT] if REAL_ROOT else []))
        cls.first_doc, cls.first_values, cls.first_decision = wr.generate(cls.first_args)
        cls.pristine = cls.work / "pristine"
        cls.pristine.mkdir()
        cls.real_hashes = {}
        for source in cls.first_values["sources"].values():
            path = Path(source["file"])
            if path.is_absolute() or source.get("artifact"):
                continue
            original = REAL_REPO / path
            cls.real_hashes[path] = source["sha256"]
            if source["missing"]:
                continue
            dest = cls.pristine / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, dest)
        audit = cls.pristine / EVIDENCE / "fleet-audit.json"
        audit.write_text(json.dumps(synthetic_audit(cls.pristine)))
        closure = cls.pristine / U24 / "G1-verification-2026-10-07.md"
        if not closure.exists():
            closure.write_text("G1 verdict: CLOSED\nSynthetic closure for mutation controls.\n")
        else:
            closure.write_text(re.sub(r"^G1 verdict: (CLOSED|NOT CLOSED)\b", "G1 verdict: CLOSED", closure.read_text(), count=1, flags=re.M))
        args = wr.options(["--repo", str(cls.pristine), "--out", str(cls.work / "complete.md"),
                           "--values", str(cls.work / "complete.json")])
        cls.complete_doc, cls.complete_values, _ = wr.generate(args)
        if headline(cls.complete_doc) != "COMPLETE":
            raise AssertionError("positive fixture must start COMPLETE: " + str(cls.complete_values["decision"]))

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=self.work)
        self.case = Path(self.temp.name)
        self.repo = self.case / "repo"
        shutil.copytree(self.pristine, self.repo)
        self.args = wr.options(["--repo", str(self.repo), "--out", str(self.case / "result.md"),
                                "--values", str(self.case / "values.json")])

    def tearDown(self):
        self.temp.cleanup()

    def edit_judge(self, plan, edit):
        path = self.repo / EVIDENCE / f"judge-{plan}.json.gz"
        report = load_gz(path)
        edit(report)
        save_gz(path, report)

    def edit_audit(self, edit):
        path = self.repo / EVIDENCE / "fleet-audit.json"
        report = json.loads(path.read_text())
        edit(report)
        path.write_text(json.dumps(report))

    def edit_reruns(self, edit):
        path = self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        edit(rows)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def publish_fresh_addresses(self, rows):
        """Supply explicit synthetic addresses for new comparison fixtures."""
        path = self.repo / U24 / "evidence/fresh-copies-2026-10-07.json"
        manifest = json.loads(path.read_text())
        for row in rows:
            tag, index = row["fresh_tag"], str(row["slice"])
            entry = manifest["tags"].setdefault(tag, {"branch": "test-fresh-" + tag, "commit": "a" * 40, "slices": {}})
            entry["slices"].setdefault(index, {
                "receipt": f"research/unit-distance-24/results/u24/check/s{index}of1920-{tag}.txt",
                "receipt_sha256": "b" * 64, "structure_sha256": "c" * 64})
        path.write_text(json.dumps(manifest))

    def remove_comparisons(self, slice_index):
        for path in (self.repo / U24 / "evidence").glob("rerun-resumed-*.jsonl"):
            rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows if row["slice"] != slice_index))

    def assert_red(self, gate):
        # This baseline asserts the transition, not merely an INCOMPLETE label.
        self.assertEqual(headline(self.complete_doc), "COMPLETE")
        doc, values, decision = wr.generate(self.args)
        self.assertEqual(headline(doc), "INCOMPLETE")
        self.assertIn(gate, failing_gates(values))
        self.assertIn(gate, decision["failing_gates"])
        self.assertIn(f"| {gate} | not met |", doc)

    def test_000_complete_fixture_is_green(self):
        doc, values, decision = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        self.assertEqual(decision["failing_items"], [])
        self.assertTrue(all(row["status"] == "met" for row in values["gate_table"]))
        self.assertEqual(len(values["gate_table"]), 7)

    def test_g1_absent_flips_headline(self):
        self.args.g1.unlink()
        self.assert_red("G1")
        self.assertIn("G1 closure record is absent", self.args.out.read_text())

    def test_g1_not_closed_flips_headline(self):
        self.args.g1.write_text("G1 verdict: NOT CLOSED\n")
        self.assert_red("G1")
        self.assertIn("first G1 verdict NOT CLOSED", self.args.out.read_text())

    def test_g1_first_matching_line_decides(self):
        self.args.g1.write_text("# A closure note\nG1 verdict: NOT CLOSED\nG1 verdict: CLOSED\n")
        self.assert_red("G1")
        self.args.g1.write_text("# A closure note\nG1 verdict: CLOSED\nG1 verdict: NOT CLOSED\n")
        self.assertEqual(headline(wr.generate(self.args)[0]), "COMPLETE")

    def test_g1_no_matching_line_flips_headline(self):
        self.args.g1.write_text("G1 fixes addressed; reviewer closure pending.\n")
        self.assert_red("G1")

    def test_g1_closure_basis_is_shown_and_evidence_bound(self):
        doc, values, _ = wr.generate(self.args)
        row = next(r for r in values["gate_table"] if r["gate"] == "G1")
        self.assertIn("first G1 verdict CLOSED", row["detail"])
        self.assertIn("verification rounds 1, 2, 3", row["detail"])
        self.assertIn("656 field families", row["detail"])
        self.assertIn("1,936 copies, 15,488 files, 0 problems", row["detail"])
        self.assertIn("four-plan re-judge JUDGE OK", row["detail"])
        self.assertIn("Historical (deleted-content) fields rest on the worker's check before deletion", doc)
        self.assertIn("Sampling is not exhaustive", doc)
        text = self.args.g1.read_text().replace("656 field families", "657 field families")
        self.args.g1.write_text(text)
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(values["v"]["g1.basis"]["value"]["families"], 657)
        self.assertIn("657 field families", doc)

    def test_original_key_field_mutations_flip_headline_for_every_plan(self):
        # Change only the original report. Current judge/audit predicates still
        # pass, so each transition depends on the newly requested comparison.
        keys = ("verdict", "accepted_slices", "accepted_copies", "missing", "duplicates", "rejected",
                "g4", "survivors", "resumed_slices", "rerun_disagreements")
        for plan in wr.ALL_PLANS:
            path = self.repo / ORIGINAL_EVIDENCE / f"judge-{plan}.json.gz"
            pristine = path.read_bytes()
            report = load_gz(path)
            for key in keys:
                with self.subTest(plan=plan, field=key):
                    mutated = copy.deepcopy(report)
                    mutated[key] = None
                    save_gz(path, mutated)
                    doc, values, decision = wr.generate(self.args)
                    self.assertEqual(headline(doc), "INCOMPLETE")
                    self.assertIn("G3", failing_gates(values))
                    self.assertIn("rejudge-equality", decision["failing_items"])
                    row = next(r for r in values["v"]["rejudge.comparisons"]["value"] if r["plan"] == plan)
                    self.assertEqual(row["different_fields"], [key])
                    path.write_bytes(pristine)

    def test_current_non_gate_key_mutation_flips_headline(self):
        self.edit_judge("phaseb", lambda j: j["duplicates"].update({"272": ["mutation"]}))
        self.assert_red("G3")
        values = json.loads(self.args.values.read_text())
        self.assertIn("rejudge-equality", values["decision"]["failing_items"])

    def test_original_report_absent_flips_headline(self):
        (self.repo / ORIGINAL_EVIDENCE / "judge-full.json.gz").unlink()
        self.assert_red("G3")
        self.assertIn("original/final key-field differences", self.args.out.read_text())

    def test_original_snapshot_sources_diverge_flips_headline(self):
        path = self.repo / ORIGINAL_EVIDENCE / "sources.tsv"
        lines = path.read_text().splitlines()
        fields = lines[0].split("\t")
        fields[1] = "0" * 40
        lines[0] = "\t".join(fields)
        path.write_text("\n".join(lines) + "\n")
        self.assert_red("G3")
        self.assertIn("same snapshot sources False", self.args.out.read_text())

    def test_section_eight_identifies_original_and_final_evidence(self):
        doc, values, _ = wr.generate(self.args)
        text = doc.split("## 8. How to check it", 1)[1]
        self.assertIn("2026-10-06 reports", text)
        self.assertIn("the original judge of this snapshot", text)
        self.assertIn("The r2 reports", text)
        self.assertIn("identical in every key field", text)
        self.assertEqual(values["v"]["rejudge.same_snapshot"]["value"], True)
        self.assertTrue(all(r["matching"] for r in values["v"]["rejudge.comparisons"]["value"]))

    def test_retained_scan_summaries_and_coverage_are_read_verbatim(self):
        doc, _, _ = wr.generate(self.args)
        section = doc.split("## 5. Cross-checks that were actually run", 1)[1].split("## 6.", 1)[0]
        for path in self.args.retained_scan:
            for line in path.read_text().splitlines():
                if line.startswith("RETAINED SCAN ") or line.startswith("# coverage "):
                    self.assertIn(line, section)
        path = self.args.retained_scan[1]
        text = path.read_text().replace("15488 retained", "15489 retained").replace("3872 retained", "3873 retained")
        path.write_text(text)
        doc, _, _ = wr.generate(self.args)
        section = doc.split("## 5. Cross-checks that were actually run", 1)[1].split("## 6.", 1)[0]
        self.assertIn("15489 retained level files measured", section)
        self.assertIn("3873 retained level files", section)

    def test_original_evidence_and_retained_scan_options_override(self):
        args = wr.options(["--repo", str(self.repo), "--original-evidence", "custom-original",
                           "--retained-scan", "scan-a.txt", "scan-b.txt", "--retained-scan", "scan-c.txt"])
        self.assertEqual(args.original_evidence, Path("custom-original"))
        self.assertEqual(args.retained_scan, [Path("scan-a.txt"), Path("scan-b.txt"), Path("scan-c.txt")])

    def test_g2_pilot_fail_flips_headline(self):
        self.edit_judge("pilot", lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G2")

    def test_g2_pilot_missing_planned_slice_flips_headline(self):
        self.edit_judge("pilot", lambda j: j["accepted_slices"].pop())
        self.assert_red("G2")

    def test_g2_jobs_section_absent_flips_headline(self):
        text = self.args.jobs.read_text()
        self.args.jobs.write_text(text.replace("## u24-pilot", "## archived-pilot"))
        self.assert_red("G2")
        self.assertIn("u24-pilot section is absent", self.args.out.read_text())

    def test_full_plan_fail_flips_headline(self):
        self.edit_judge("full", lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G3")

    def test_pilot_plan_fail_flips_headline(self):
        self.edit_judge("pilot", lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G3")

    def test_phaseb_plan_fail_flips_headline(self):
        self.edit_judge("phaseb", lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G3")

    def test_g4_failure_with_ok_judge_label_flips_headline(self):
        self.edit_judge("full", lambda j: j.update(g4={"FAIL": j["accepted_copies"]}))
        self.assert_red("G3")

    def test_summary_problem_with_ok_judge_label_flips_headline(self):
        self.edit_judge("full", lambda j: j["summary"].update(problems=["parent share differs"]))
        self.assert_red("G3")

    def test_missing_slice_from_all_plans_flips_headline(self):
        self.edit_judge("full", lambda j: j["accepted_slices"].remove(0))
        self.assert_red("G3")

    def test_overlapping_coverage_flips_headline(self):
        self.edit_judge("phaseb", lambda j: j["accepted_slices"].append(0))
        self.assert_red("G3")

    def test_wrong_partition_preserving_length_flips_headline(self):
        self.edit_judge("full", lambda j: j["accepted_slices"].__setitem__(0, 1))
        self.assert_red("G3")

    def test_fleet_audit_missing_flips_headline(self):
        (self.repo / EVIDENCE / "fleet-audit.json").unlink()
        self.assert_red("G3")
        self.assertIn("G3's fleet-wide audit has not run", self.args.out.read_text())

    def test_fleet_audit_per_slice_ok_flips_headline(self):
        self.edit_audit(lambda j: j["audit"].update(status="per-slice OK"))
        self.assert_red("G3")

    def test_fleet_audit_fail_flips_headline(self):
        self.edit_audit(lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G3")

    def test_fleet_audit_unresolved_flips_headline(self):
        self.edit_audit(lambda j: j["audit"].update(unresolved=["unbound resumed cell"]))
        self.assert_red("G3")

    def test_fleet_audit_unbound_plan_flips_headline(self):
        self.edit_audit(lambda j: j["plans"]["full"]["accepted_slices"].pop())
        self.assert_red("G3")

    def test_fleet_audit_without_coverage_line_flips_headline(self):
        self.edit_audit(lambda j: j.update(coverage_lines=[]))
        self.assert_red("G3")

    def test_known_accepted_count_off_one_flips_headline(self):
        self.edit_judge("full", lambda j: j["known"].update(predicted_for_accepted=j["known"]["predicted_for_accepted"] - 1))
        self.assert_red("G4")

    def test_known_total_sum_off_one_flips_headline(self):
        for p in wr.PLANS:
            self.edit_judge(p, lambda j: j["known"].update(total=j["known"]["total"] + 1))
        self.assert_red("G4")

    def test_known_plan_prediction_off_one_flips_headline(self):
        self.edit_judge("pilot", lambda j: j["known"].update(predicted_for_plan=j["known"]["predicted_for_plan"] + 1))
        self.assert_red("G4")

    def test_known_control_failure_flips_headline(self):
        self.edit_judge("phaseb", lambda j: j["known"]["fleet"].update(result="FAIL"))
        self.assert_red("G4")

    def test_repro_fail_flips_headline(self):
        self.edit_judge("repro", lambda j: j.update(verdict="FAIL", exit=1))
        self.assert_red("G5")

    def test_repro_missing_sample_flips_headline(self):
        self.edit_judge("repro", lambda j: j["accepted_slices"].pop())
        self.assert_red("G5")

    def test_second_survivor_without_refutation_flips_headline(self):
        self.edit_judge("phaseb", lambda j: j["survivors"].append({"graph6": "W" + "?" * 46, "slices": [3], "copies": []}))
        self.assert_red("G3")
        self.assertIn("unrefuted survivors", self.args.out.read_text())

    def test_omitted_survivor_is_not_vacuously_refuted(self):
        for p in wr.ALL_PLANS:
            self.edit_judge(p, lambda j: j.update(survivors=[]))
        self.assert_red("G3")

    def test_saved_check_without_success_flips_headline(self):
        path = self.repo / U24 / "survivor-s50/check_survivor.out"
        path.write_text(path.read_text().replace("SURVIVOR REFUTATION OK", "SURVIVOR REFUTATION missing"))
        self.assert_red("G3")

    def test_saved_check_wrong_exit_flips_headline(self):
        path = self.repo / U24 / "survivor-s50/check_survivor.out"
        path.write_text(path.read_text().replace("(exit 0)", "(exit 1)"))
        self.assert_red("G3")

    def test_saved_check_wrong_graph_flips_headline(self):
        path = self.repo / U24 / "survivor-s50/check_survivor.out"
        path.write_text(path.read_text().replace("contains J?iP?dHPb`_", "contains unrelated"))
        self.assert_red("G3")

    def test_missing_saved_check_flips_headline(self):
        (self.repo / U24 / "survivor-s50/check_survivor.out").unlink()
        self.assert_red("G3")

    def test_noninjective_mapping_flips_headline(self):
        path = self.repo / U24 / "survivor-s50/mapping.json"
        mapping = json.loads(path.read_text())
        mapping["pattern_to_survivor"]["0"] = mapping["pattern_to_survivor"]["1"]
        path.write_text(json.dumps(mapping))
        self.assert_red("G3")

    def test_record_changed_flips_headline(self):
        bundle = self.repo / U24 / "survivor-s50"
        mapping = json.loads((bundle / "mapping.json").read_text())
        path = bundle / mapping["record"]
        path.write_bytes(path.read_bytes() + b" ")
        self.assert_red("G3")

    def test_frozen_checker_changed_flips_headline(self):
        path = self.repo / "research/gp-11/check/gp11check.py"
        path.write_text(path.read_text() + "\n# mutation\n")
        self.assert_red("G3")

    def test_rerun_different_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0].update(verdict="DIFFERENT"))
        self.assert_red("G3")

    def test_rerun_not_from_scratch_flips_headline_and_does_not_count(self):
        self.edit_reruns(lambda rows: rows[0].update(fresh_from_scratch=False, fresh_recovered_cells=7))
        self.assert_red("G3")
        values = json.loads(self.args.values.read_text())
        twin = next(r for r in values["v"]["resume.twins"]["value"] if r["slice"] == 239)
        self.assertTrue(twin["missing"])
        self.assertIn("twin itself resumed (7 recovered cells)", twin["twin"])

    def test_rerun_fresh_flag_false_even_with_zero_recovery_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0].update(fresh_from_scratch=False, fresh_recovered_cells=0))
        self.assert_red("G3")

    def test_rerun_positive_recovery_even_with_true_fresh_flag_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0].update(fresh_from_scratch=True, fresh_recovered_cells=1))
        self.assert_red("G3")

    def test_rerun_freshness_flag_absent_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0].pop("fresh_from_scratch"))
        self.assert_red("G3")

    def test_rerun_fresh_recovered_count_absent_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0].pop("fresh_recovered_cells"))
        self.assert_red("G3")

    def test_repro_twin_resumed_cells_stop_it_counting(self):
        _, before, _ = wr.generate(self.args)
        twin = next(r for r in before["v"]["resume.twins"]["value"] if r["slice"] == 344)
        self.assertFalse(twin["missing"])
        self.edit_judge("repro", lambda j: j["cost"]["chosen"]["344"].update(resumed_cells=47))
        doc, after, _ = wr.generate(self.args)
        twin = next(r for r in after["v"]["resume.twins"]["value"] if r["slice"] == 344)
        self.assertTrue(twin["missing"])
        self.assertIn("twin itself resumed (47 recovered cells)", twin["twin"])
        self.assertTrue(any(r["slice"] == 344 for r in after["v"]["resume.missing"]["value"]))
        # Missing fresh twins are explicitly non-vetoing; the transition tested
        # here is the twin assignment, not an unrelated headline predicate.
        self.assertEqual(headline(doc), "COMPLETE")

    def test_repro_twin_unknown_resumed_count_is_not_assumed_fresh(self):
        self.edit_judge("repro", lambda j: j["cost"]["chosen"]["344"].pop("resumed_cells"))
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        twin = next(r for r in values["v"]["resume.twins"]["value"] if r["slice"] == 344)
        self.assertTrue(twin["missing"])
        self.assertIn("freshness not recorded", twin["twin"])

    def test_slice_1270_waits_for_a_fresh_rerun_then_clears(self):
        self.remove_comparisons(1270)
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        twin = next(r for r in values["v"]["resume.twins"]["value"] if r["slice"] == 1270)
        self.assertTrue(twin["missing"])
        self.assertIn("twin itself resumed (47 recovered cells)", twin["twin"])
        template = json.loads((self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl").read_text().splitlines()[0])
        template.update(slice=1270, kept_tag="w24", fresh_tag="vmr6", kept_recovered_cells=67,
                        fresh_recovered_cells=0, fresh_from_scratch=True)
        self.publish_fresh_addresses([template])
        supervisor = self.repo / U24 / "evidence/rerun-resumed-supervisor-2026-10-07.jsonl"
        supervisor.write_text(supervisor.read_text() + json.dumps(template) + "\n")
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        twin = next(r for r in values["v"]["resume.twins"]["value"] if r["slice"] == 1270)
        self.assertFalse(twin["missing"])
        self.assertIn("vmr6 (IDENTICAL)", twin["twin"])
        self.assertFalse(any(r["slice"] == 1270 for r in values["v"]["resume.missing"]["value"]))
        self.assertIn("test-fresh-vmr6", doc)
        self.assertIn("vmr6", values["v"]["fresh.bindings"]["value"]["tags"])

    def test_rerun_missing_row_lists_twin_without_gate_failure(self):
        self.edit_reruns(lambda rows: rows.pop())
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        missing = values["v"]["resume.missing"]["value"]
        self.assertTrue(any(r["slice"] == 1641 for r in missing))
        self.assertIn("no from-scratch twin is recorded", doc)

    def test_rerun_false_file_with_identical_label_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0]["files"].update({"counts.json": False}))
        self.assert_red("G3")

    def test_rerun_omitted_file_with_identical_label_flips_headline(self):
        self.edit_reruns(lambda rows: rows[0]["files"].pop("counts.json"))
        self.assert_red("G3")

    def test_rerun_absent_lists_twins_without_gate_failure(self):
        (self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl").unlink()
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        self.assertTrue({239, 830, 1069, 1352, 1641}.issubset({r["slice"] for r in values["v"]["resume.missing"]["value"]}))

    def test_second_rerun_file_different_flips_headline(self):
        row = json.loads((self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl").read_text().splitlines()[0])
        row.update(slice=276, kept_tag="w08", fresh_tag="vmr3", verdict="DIFFERENT")
        second = self.repo / U24 / "evidence/rerun-resumed-supervisor-2026-10-07.jsonl"
        second.write_text(json.dumps(row) + "\n")
        self.assert_red("G3")
        self.assertIn("vmr3 (DIFFERENT)", self.args.out.read_text())

    def test_supervisor_slice_without_twin_is_listed(self):
        for path in (self.repo / U24 / "evidence").glob("rerun-resumed-*.jsonl"):
            rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows if row["slice"] != 276))
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        self.assertTrue(any(r["slice"] == 276 for r in values["v"]["resume.missing"]["value"]))
        self.assertRegex(doc, r"(?s)Resumed accepted copies with no recorded from-scratch twin:.*slice 276")

    def test_second_rerun_file_supplies_twin(self):
        row = json.loads((self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl").read_text().splitlines()[0])
        row.update(slice=276, kept_tag="w08", fresh_tag="vmr3")
        self.publish_fresh_addresses([row])
        second = self.repo / U24 / "evidence/rerun-resumed-supervisor-2026-10-07.jsonl"
        second.write_text(json.dumps(row) + "\n")
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        twins = values["v"]["resume.twins"]["value"]
        self.assertTrue(any(r["slice"] == 276 and "vmr3 (IDENTICAL)" in r["twin"] for r in twins))
        self.assertFalse(any(r["slice"] == 276 for r in values["v"]["resume.missing"]["value"]))

    def test_every_accepted_resumed_copy_is_listed(self):
        self.remove_comparisons(1270)
        _, values, _ = wr.generate(self.args)
        rows = values["v"]["resume.twins"]["value"]
        self.assertEqual(len(rows), 23)
        self.assertEqual(sum(r["slice"] == 1209 for r in rows), 2)
        self.assertEqual(sum(r["slice"] == 1639 for r in rows), 2)
        self.assertTrue(any(r["slice"] == 272 for r in rows))
        self.assertTrue(any(r["slice"] == 344 and "reproduction comparison" in r["twin"] and not r["missing"] for r in rows))
        self.assertTrue(any(r["slice"] == 1270 and "twin itself resumed" in r["twin"] and r["missing"] for r in rows))

    def test_complete_supervisor_comparisons_fit_compact_values(self):
        template = json.loads((self.repo / U24 / "evidence/rerun-resumed-2026-10-06.jsonl").read_text().splitlines()[0])
        comparisons = []
        for plan in ("pilot", "phaseb"):
            report = load_gz(self.repo / EVIDENCE / f"judge-{plan}.json.gz")
            for i in report["resumed_slices"]:
                if i == 344:
                    continue
                tag = re.search(r"-([^/]+)\.txt$", report["cost"]["chosen"][str(i)]["source"])[1]
                row = copy.deepcopy(template)
                row.update(slice=i, kept_tag=tag, fresh_tag="vmr6" if i == 1270 else "vmr3")
                comparisons.append(row)
        self.assertEqual(len(comparisons), 15)
        self.publish_fresh_addresses(comparisons)
        path = self.repo / U24 / "evidence/rerun-resumed-supervisor-2026-10-07.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in comparisons))
        if REAL_ROOT:
            self.args.root = Path(REAL_ROOT)
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        self.assertLess(self.args.values.stat().st_size, 300_000)
        self.assertEqual(values["v"]["resume.missing"]["value"], [])
        twins = values["v"]["resume.twins"]["value"]
        for i in (1209, 1639):
            self.assertEqual(sum(r["slice"] == i and "via the counted copy" in r["twin"] for r in twins), 1)

    def test_g0_absent_flips_headline(self):
        (self.repo / U24 / "G0-literature-2026-10-06.md").unlink()
        self.assert_red("G0")

    def test_no_root_omits_table_and_explains(self):
        doc, _, _ = wr.generate(self.args)
        self.assertIn("per-level table is omitted because `--root` was not supplied", doc)
        self.assertNotIn("| level | window | cells |", doc)

    def test_requested_incomplete_root_flips_headline(self):
        self.args.root = self.case / "empty-fleet"
        self.args.root.mkdir()
        self.assert_red("G6")
        self.assertNotIn("| level | window | cells |", self.args.out.read_text())

    def test_contract_quotes_preserve_line_content(self):
        doc, _, _ = wr.generate(self.args)
        contract = (self.repo / U24 / "CONTRACT.md").read_text()
        for n in (0, 1, 3, 4):
            quoted = "\n".join("> " + line for line in wr.section(contract, n).splitlines())
            self.assertIn(quoted, doc)

    def test_every_value_has_resolvable_source_and_hash(self):
        _, values, _ = wr.generate(self.args)
        def resolve(ref):
            if "source_group" in ref:
                for child in values["source_groups"][ref["source_group"]]:
                    yield from resolve(child)
            else:
                yield ref
        for key, record in values["v"].items():
            self.assertTrue(record["sources"], key)
            for ref in record["sources"]:
                for child in resolve(ref):
                    leaf = values["sources"][child["source"]]
                    self.assertIn("file", leaf, key)
                    self.assertIn("sha256", leaf, key)
                    self.assertIn("location", child, key)
                    if leaf.get("missing"):
                        self.assertIsNone(leaf["sha256"])
                    else:
                        self.assertRegex(leaf["sha256"], r"^[0-9a-f]{64}$", key)
            for parent in record.get("inputs", []):
                self.assertIn(parent, values["v"], key)
        source = values["sources"]["judge_full"]
        self.assertEqual(source["sha256"], hashlib.sha256((self.repo / source["file"]).read_bytes()).hexdigest())

    def test_compact_values_and_sidecar_digest(self):
        _, values, _ = wr.generate(self.args)
        self.assertLess(self.args.values.stat().st_size, 300_000)
        self.assertFalse(any(key.startswith("tree.") for key in values["sources"]))
        self.assertNotIn("value", values["v"]["judge_full"])
        raw = self.args.sources.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), values["source_sidecar"]["sha256"])
        self.assertEqual(values["source_sidecar"]["file"], self.args.sources.name)
        self.assertEqual(json.loads(gzip.decompress(raw))["counted_copies"], 0)

    def test_slice_disagreement_prose_and_reasons_are_evidence_bound(self):
        doc, values, _ = wr.generate(self.args)
        self.assertIn("The earlier copy was resumed under the legacy supervisor", doc)
        self.assertIn("The counted copy is the rerun", doc)
        self.assertIn("does not name the differing cells", doc)
        self.assertEqual(sum(r["requests"] for r in values["v"]["history.reasons"]["value"]), 245)
        def mutate(j):
            j["rerun_disagreements"][0]["differing_cells"] = [[23, 66], [23, 73]]
            j["provenance"]["plan"]["rerun"][0]["why"] = "Distinct test reason"
        self.edit_judge("full", mutate)
        doc, values, _ = wr.generate(self.args)
        self.assertIn("names cells: [[23,66],[23,73]]", doc)
        self.assertIn("Distinct test reason", doc)
        self.assertTrue(any(r == {"why": "Distinct test reason", "requests": 1} for r in values["v"]["history.reasons"]["value"]))

    def test_rerun_reported_pair_count_off_one_flips_headline(self):
        self.edit_judge("full", lambda j: j.update(rerun_count=j["rerun_count"] + 1))
        self.assert_red("G3")
        self.assertIn("rerun reason groups total 245; judge requested pairs 246", self.args.out.read_text())

    def test_rerun_reason_removed_flips_headline(self):
        self.edit_judge("full", lambda j: j["provenance"]["plan"]["rerun"].pop())
        self.assert_red("G3")
        self.assertIn("rerun reason groups total 244; judge requested pairs 245", self.args.out.read_text())

    def test_rerun_groups_keep_exact_reasons_and_signed_lead_ranges(self):
        why = ["test resumed (lead -4 s); reassigned",
               "test resumed (lead 0 s); other tail",
               "test resumed (lead 12 s); a repeated tail",
               "test resumed (lead 12 s); a repeated tail",
               "test resumed; tail (lead 90 s)",
               "test reassigned; tail (lead 50 s)",
               "test immediate; reassigned (extra)",
               "test first; tail (nested explanation)",
               "test first (extra); different tail"]
        def mutate(j):
            for row, text in zip(j["provenance"]["plan"]["rerun"], why):
                row["why"] = text
        self.edit_judge("full", mutate)
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        groups = {r["why"]: r for r in values["v"]["history.reason_groups"]["value"]}
        self.assertEqual(groups["test resumed"]["requests"], 5)
        self.assertEqual(groups["test resumed"]["lead_seconds_range"], "-4..90")
        self.assertEqual((groups["test reassigned"]["lead_seconds_min"], groups["test reassigned"]["lead_seconds_max"]), (50, 50))
        self.assertEqual(groups["test first"]["requests"], 2)
        self.assertIsNone(groups["test immediate"]["lead_seconds_range"])
        full = values["v"]["history.reasons"]["value"]
        self.assertIn({"why": why[2], "requests": 2}, full)
        for text in (why[0], why[1], why[4], why[8]):
            self.assertIn({"why": text, "requests": 1}, full)
        self.assertIn("| test resumed | 5 | -4..90 |", doc)
        self.assertIn("| test immediate | 1 | not recorded |", doc)
        self.assertIn("full verbatim reason list and each reason's count", doc)

    def test_real_reason_groups_and_full_verbatim_counts_are_retained(self):
        doc, values, _ = wr.generate(self.args)
        groups = values["v"]["history.reason_groups"]["value"]
        self.assertEqual(len(groups), 3)
        self.assertEqual(sorted(r["requests"] for r in groups), [26, 28, 191])
        self.assertTrue(any(r["lead_seconds_range"] == "-1..647" for r in groups))
        full = values["v"]["history.reasons"]["value"]
        report = load_gz(self.args.judge_full)
        counts = {}
        for row in report["provenance"]["plan"]["rerun"]:
            counts[row["why"]] = counts.get(row["why"], 0) + 1
        self.assertEqual({r["why"]: r["requests"] for r in full}, counts)
        self.assertEqual(values["v"]["history.grouped_requests"]["value"], report["rerun_count"])
        table = doc.split("Rerun requests grouped by the reason's leading clause", 1)[1].split("The full verbatim reason list", 1)[0]
        self.assertEqual(sum(line.startswith("| suspect:") for line in table.splitlines()), 3)

    def test_fresh_source_addresses_and_digests_are_bound_and_input_driven(self):
        path = self.repo / U24 / "evidence/fresh-copies-2026-10-07.json"
        manifest = json.loads(path.read_text())
        address = manifest["tags"]["vmr1"]
        doc, values, _ = wr.generate(self.args)
        self.assertIn(address["branch"], doc)
        self.assertIn(address["commit"], doc)
        bindings = values["v"]["fresh.bindings"]["value"]["tags"]["vmr1"]
        self.assertEqual(bindings["slices"]["239"], address["slices"]["239"])
        address.update(branch="mutation-fresh-branch", commit="f" * 40)
        address["slices"]["239"]["receipt_sha256"] = "e" * 64
        path.write_text(json.dumps(manifest))
        doc, values, _ = wr.generate(self.args)
        self.assertIn("mutation-fresh-branch", doc)
        self.assertIn("f" * 40, doc)
        bindings = values["v"]["fresh.bindings"]["value"]["tags"]["vmr1"]
        self.assertEqual(bindings["slices"]["239"]["receipt_sha256"], "e" * 64)
        self.assertEqual(values["sources"]["fresh_copies"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIn('git archive "$fresh_commit"', doc)
        self.assertIn('record["receipt_sha256"]', doc)
        self.assertIn('record["structure_sha256"]', doc)

    def test_completeness_bridge_and_first_use_definitions(self):
        doc, values, _ = wr.generate(self.args)
        bridge = doc.split("## 3. The enumeration\n\n", 1)[1].split("\n\n", 1)[0]
        for phrase in ("Canonical augmentation by minimum-degree deletion", "unique construction path",
                       "Record-hash slicing", "partitions that tree", "known u(j)", "Lemmas R and T",
                       "every subgraph of a unit-distance graph", "induced ancestor", "proved upper bound"):
            self.assertIn(phrase, bridge)
        self.assertIn("research/unit-distance-22/enum/PRUNING.md", bridge)
        self.assertIn("research/unit-distance-23/RESULT-u23.md", bridge)
        self.assertIn("A TU gadget is a totally unfaithful graph", doc)
        self.assertIn("The reach table records the ancestor vertex-and-edge cells", doc)
        self.assertIn("The filter-only prune applies the sound", doc)
        self.assertIn("keeps every graph they leave undecided", doc)
        self.assertIn("Gate G4 means the known-graph control", doc)
        self.assertIn("receipt label `G4 replay` means the independent augmentation replay", doc)
        self.assertIn("samples 0.2%", doc)
        self.assertEqual(values["v"]["replay.percent"]["value"], 0.2)
        contract = self.args.contract.read_text().replace("fraction** (0.002)", "fraction** (0.004)")
        self.args.contract.write_text(contract)
        doc, values, _ = wr.generate(self.args)
        self.assertIn("samples 0.4%", doc)
        self.assertEqual(values["v"]["replay.percent"]["value"], 0.4)

    def test_fleet_share_equalities_are_displayed_and_gate_checked(self):
        doc, values, _ = wr.generate(self.args)
        audit = json.loads(self.args.fleet_audit.read_text())
        shares = audit["audit"]["record"]["fleets"][0]["slice_partition"]
        self.assertEqual(len(shares), 8)
        for cell, row in shares.items():
            self.assertIn(f"| {cell} | {row['sum']:,} | {row['stage_file']:,} |", doc)
        first = next(iter(shares))
        self.edit_audit(lambda a: a["audit"]["record"]["fleets"][0]["slice_partition"][first].update(sum=shares[first]["sum"] + 1))
        self.assert_red("G3")

    def test_survivor_certificate_type_and_derivation_are_read_from_record(self):
        doc, values, _ = wr.generate(self.args)
        self.assertIn("`real-dag` certificate uses 14 exact rational polynomial identities", doc)
        self.assertIn("positive constant plus 4 positively weighted squares", doc)
        for text in ("research/gp-10/check/FORMAT.md", "research/gp-11/check/FORMAT.md",
                     "research/gp-10/check/gp10check.py", "`regenerate`, `algebra_dag` and `real_no_zero`"):
            self.assertIn(text, doc)
        cert = values["v"]["survivor.0.certificate"]["value"]
        self.assertEqual(cert, {"type": "real-dag", "rows": 14, "sos": True, "squares": 4})
        mapping = json.loads((self.repo / U24 / "survivor-s50/mapping.json").read_text())
        path = self.repo / U24 / "survivor-s50" / mapping["record"]
        record = json.loads(path.read_text())
        record["cert"]["type"] = "test-alternative-certificate"
        path.write_text(json.dumps(record))
        doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "INCOMPLETE")  # The record hash also changed.
        self.assertEqual(values["v"]["survivor.0.certificate"]["value"]["type"], "test-alternative-certificate")
        self.assertIn("declares certificate type `test-alternative-certificate`", doc)
        self.assertNotIn("`real-dag` certificate uses 14", doc)

    def test_survivor_certificate_row_and_square_counts_are_not_literals(self):
        mapping = json.loads((self.repo / U24 / "survivor-s50/mapping.json").read_text())
        path = self.repo / U24 / "survivor-s50" / mapping["record"]
        record = json.loads(path.read_text())
        record["cert"]["rows"].pop()
        record["cert"]["sos"]["squares"].pop()
        path.write_text(json.dumps(record))
        doc, values, _ = wr.generate(self.args)
        self.assertIn("`real-dag` certificate uses 13 exact rational polynomial identities", doc)
        self.assertIn("positive constant plus 3 positively weighted squares", doc)
        self.assertEqual(values["v"]["survivor.0.certificate"]["value"]["rows"], 13)

    def test_revised_dependencies_survivor_known_sum_and_commands(self):
        doc, _, _ = wr.generate(self.args)
        self.assertNotIn("For Boris Alexeev, via Liam.", doc)
        self.assertIn("neither yet independently published", doc)
        self.assertIn("GP-11 classification (the census of minimal non-unit-distance graphs on eleven vertices)", doc)
        self.assertIn("the narrative note", doc)
        self.assertIn("found 12 GP-11-refuted graphs on eleven vertices embedded", doc)
        self.assertIn("frozen checker accepts 12 of 12 original records", doc)
        self.assertIn("82,582 + 5,293 + 10,037 = 97,912", doc)
        self.assertIn("was found there, unpruned", doc)
        self.assertIn("| PASS 44 |", doc)
        self.assertNotIn('{"PASS":44}', doc)
        commands = doc.split("## 8. How to check it", 1)[1]
        for plan in ("pilot", "full", "phaseb", "repro"):
            self.assertIn(f"--plan coordination/cloud-workers/u24-{plan}-plan.json", commands)
        for text in ("git archive", "sources.tsv", "fleet_audit.py", "test_fleet_audit.py", "--self-test 239",
                     "check_survivor.py", "blind_check.py", "run_certificates.py", "test_write_result.py"):
            self.assertIn(text, commands)

    def test_policy_quote_and_location_match_jobs(self):
        doc, values, _ = wr.generate(self.args)
        text = values["v"]["resume.policy"]["value"]
        self.assertIn(text, self.args.jobs.read_text())
        self.assertIn(wr.quote(text), doc)
        self.assertRegex(doc, r"JOBS.md:\d+ \(the 10:40Z paragraph\)")

    def test_reruns_and_g1_options_override(self):
        args = wr.options(["--repo", str(self.repo), "--g1", "custom-G1.md",
                           "--reruns", "one.jsonl", "two.jsonl", "--reruns", "three.jsonl"])
        self.assertEqual(args.g1, Path("custom-G1.md"))
        self.assertEqual(args.reruns, sorted(Path(p).resolve() for p in ("one.jsonl", "two.jsonl", "three.jsonl")))

    def marked(self):
        values = wr.collect(self.args)
        wr.pack_sources(values, self.args.sources, self.args.values)
        return wr.render(values, wr.decide(values))

    def test_lint_fixed_text_numeral_fails(self):
        marked = self.marked()
        self.assertEqual(wr.lint(marked), [])
        self.assertTrue(any("numeral" in p for p in wr.lint(marked + "\nThere were 17 workers.\n")))

    def test_lint_unconditional_claim_inside_value_fails(self):
        marked = self.marked()
        self.assertTrue(any("unconditional" in p for p in wr.lint(marked + "\n" + wr.E("u(24) = 68.") + "\n")))

    def test_lint_condition_does_not_leak_across_sentences(self):
        marked = self.marked()
        red = marked + "\nIf the gates close, the argument holds. " + wr.E("u(24) = 68.") + "\n"
        self.assertTrue(any("unconditional" in p for p in wr.lint(red)))

    def test_lint_fixed_status_fails(self):
        self.assertTrue(any("status word" in p for p in wr.lint(self.marked() + "\nThe audit is COMPLETE.\n")))

    def test_lint_failure_writes_neither_output(self):
        with mock.patch.object(wr, "render", return_value="There were 17 workers.\n"):
            with self.assertRaises(wr.LintError):
                wr.generate(self.args)
        self.assertFalse(self.args.out.exists())
        self.assertFalse(self.args.values.exists())
        self.assertFalse(self.args.sources.exists())

    def test_bad_gzip_is_input_error(self):
        self.args.judge_full.write_bytes(b"invalid gzip")
        with self.assertRaises(wr.InputError):
            wr.generate(self.args)
        self.assertFalse(self.args.out.exists())

    def test_cli_complete_and_incomplete_exit_codes(self):
        argv = ["--repo", str(self.repo), "--out", str(self.args.out), "--values", str(self.args.values)]
        with mock.patch("builtins.print"):
            self.assertEqual(wr.main(argv), 0)
            (self.repo / EVIDENCE / "fleet-audit.json").unlink()
            self.assertEqual(wr.main(argv), 3)

    def test_options_default_paths_and_overrides(self):
        args = wr.options(["--repo", str(self.repo), "--g0", str(self.case / "custom-note.md"),
                           "--survivor-output", str(self.case / "custom-check.out")])
        self.assertEqual(args.contract, self.repo / U24 / "CONTRACT.md")
        self.assertEqual(args.out, self.repo / U24 / "RESULT-u24.md")
        self.assertEqual(args.g0, self.case / "custom-note.md")
        self.assertEqual(args.g1, self.repo / U24 / "G1-verification-2026-10-07.md")
        self.assertEqual(args.evidence, self.repo / EVIDENCE)
        self.assertEqual(args.original_evidence, self.repo / ORIGINAL_EVIDENCE)
        self.assertEqual(args.fleet_audit, self.repo / EVIDENCE / "fleet-audit.json")
        self.assertEqual(args.judge_full, self.repo / EVIDENCE / "judge-full.json.gz")
        self.assertEqual(args.retained_scan, [self.repo / U24 / "evidence/retained-scan-2026-10-07.txt",
                                              self.repo / U24 / "evidence/retained-scan-2026-10-07b.txt"])
        self.assertEqual(args.sources, self.repo / U24 / "result-sources.json.gz")
        self.assertEqual(args.fresh_copies, self.repo / U24 / "evidence/fresh-copies-2026-10-07.json")
        self.assertEqual(args.pruning, self.repo / "research/unit-distance-22/enum/PRUNING.md")
        self.assertEqual(args.gp10_format, self.repo / "research/gp-10/check/FORMAT.md")
        self.assertEqual(args.gp11_format, self.repo / "research/gp-11/check/FORMAT.md")
        self.assertEqual(args.gp10_checker, self.repo / "research/gp-10/check/gp10check.py")
        self.assertEqual(args.survivor_output, self.case / "custom-check.out")
        self.assertEqual(wr.REPO, Path(wr.__file__).resolve().parents[3])

    def test_live_option_isolates_checker_and_uses_supplied_python(self):
        self.args.live_survivor = True
        self.args.checker_python = Path("/checker-environment/python")
        saved = (self.repo / U24 / "survivor-s50/check_survivor.out").read_text().split("\n", 1)[1]
        run = wr.subprocess.CompletedProcess([], 0, saved, "")
        with mock.patch.object(wr.shutil, "which", return_value="/usr/bin/bwrap"), \
                mock.patch.object(wr.subprocess, "run", return_value=run) as called:
            doc, values, _ = wr.generate(self.args)
        self.assertEqual(headline(doc), "COMPLETE")
        command = called.call_args.args[0]
        self.assertIn("--unshare-net", command)
        self.assertEqual(command[command.index("--ro-bind") + 1:command.index("--ro-bind") + 3], ["/", "/"])
        self.assertIn(str(self.args.checker_python), command)
        self.assertIn("/tmp/gp10-check", command)
        self.assertTrue(Path(called.call_args.kwargs["env"]["TMPDIR"]).is_relative_to(self.case))
        self.assertTrue(values["sources"]["survivor.0.output"]["file"].endswith("survivor.0.live.out"))

    def test_live_option_failed_exit_flips_headline(self):
        self.args.live_survivor = True
        saved = (self.repo / U24 / "survivor-s50/check_survivor.out").read_text().split("\n", 1)[1]
        run = wr.subprocess.CompletedProcess([], 1, saved, "checker failed")
        with mock.patch.object(wr.shutil, "which", return_value="/usr/bin/bwrap"), \
                mock.patch.object(wr.subprocess, "run", return_value=run):
            self.assert_red("G3")

    def test_live_option_without_isolation_never_invokes_checker(self):
        self.args.live_survivor = True
        with mock.patch.object(wr.shutil, "which", return_value=None), mock.patch.object(wr.subprocess, "run") as called:
            with self.assertRaises(wr.InputError):
                wr.generate(self.args)
        called.assert_not_called()

    def test_output_cannot_replace_input(self):
        self.args.out = self.args.contract
        before = self.args.contract.read_bytes()
        with self.assertRaises(wr.InputError):
            wr.generate(self.args)
        self.assertEqual(self.args.contract.read_bytes(), before)

    def test_output_cannot_write_into_fleet(self):
        self.args.root = self.case / "fleet"
        self.args.out = self.args.root / "result.md"
        with self.assertRaises(wr.InputError):
            wr.generate(self.args)
        self.assertFalse(self.args.out.exists())

    def test_zzzz_real_regeneration_bytes_and_input_digests(self):
        # Keep this lexically LAST. It runs after every mutation/red control.
        for rel, expected in self.real_hashes.items():
            path = REAL_REPO / rel
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            self.assertEqual(actual, expected, f"real evidence changed: {rel}")
        args = copy.copy(self.first_args)
        args.out = WORK / "RESULT-u24.md"
        args.values = WORK / "result-values.json"
        args.sources = WORK / "result-sources.json.gz"
        doc, values, _ = wr.generate(args)
        self.assertEqual(normalize_doc(doc).encode(), normalize_doc(self.first_doc).encode())
        self.assertEqual(normalize_values_bytes(args.values.read_bytes()), normalize_values_bytes(self.first_args.values.read_bytes()))
        self.assertEqual(args.out.read_bytes(), doc.encode())
        self.assertEqual(args.sources.read_bytes(), self.first_args.sources.read_bytes())
        self.assertEqual(values["source_sidecar"]["sha256"], hashlib.sha256(args.sources.read_bytes()).hexdigest())
        self.assertLess(len(args.values.read_bytes()), 300_000)
        self.assertEqual(headline(doc), self.first_decision["headline"])
        if REAL_ROOT:
            self.assertEqual(values["v"]["tree"]["value"]["counted_copies"], 1920)
            self.assertEqual(values["v"]["tree"]["value"]["problems"], [])
            sidecar = json.loads(gzip.decompress(args.sources.read_bytes()))
            self.assertEqual(len(sidecar["selected"]), 1920)
            self.assertEqual(len({row["slice"] for row in sidecar["selected"]}), 1920)
            self.assertEqual(sidecar["counted_copies"], 1920)


class AggregationTests(unittest.TestCase):
    """Small independently specified counts exercise the optional snapshot path."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aggregate-test-", dir=WORK)
        self.root = Path(self.temp.name) / "fleet"
        self.root.mkdir()
        self.fixture = self.root.parent / "inputs.json"
        self.fixture.write_text("{}")
        self.v = wr.Values(self.root.parent)
        self.v.read("fixture", self.fixture)
        for key, value in (("plan.count", 3), ("plan.level", 12), ("claim.n", 24), ("claim.top", 69)):
            self.v.put(key, value, "fixture")
        for i, p in enumerate(wr.PLANS):
            result = self.root / p / "research/unit-distance-24/results/u24"
            directory = result / "24-69-L12-tri-pf74" / f"s{i}of3"
            directory.mkdir(parents=True)
            child = 1 if i == 0 else 0
            rows = [[13, 23, 4, {"input": 4, "kept": 2, "pruned": 2, "tu": 1, "tri_refuted": 1}],
                    [24, 69, child, {"input": child, "kept": child, "pruned": 0, "tu": 0, "tri_refuted": 0}]]
            (directory / "counts.json").write_text(json.dumps(rows))
            summary = {"slice": [12, i, 3], "target": [24, 69], "completed_through_n": 24,
                       "levels": [{"n": n, "m": m, "children": ch, "prune": {"counts": pc}} for n, m, ch, pc in rows]}
            (directory / "run-summary.json").write_text(json.dumps(summary))
            report = {"accepted_slices": [i], "cost": {"chosen": {str(i): {"accepted": True,
                       "source": str((result / "check" / f"s{i}of3.txt").relative_to(self.root))}}},
                       "summary": {"record": {"fleets": [{"target_cell": {"children": child, "kept": child}}]}}}
            self.v.put("judge_" + p, report, "fixture")

    def tearDown(self):
        self.temp.cleanup()

    def test_per_level_totals_from_selected_copies(self):
        wr.aggregate(self.v, self.root)
        tree = self.v.get("tree")
        self.assertEqual(tree["problems"], [])
        self.assertEqual(tree["counted_copies"], 3)
        first, top = tree["levels"]
        self.assertEqual((first["children"], first["kept"], first["pruned"], first["tu"], first["tri_refuted"]), (12, 6, 6, 3, 3))
        self.assertEqual(top["kept"], 1)
        self.assertEqual(first["pruned_percent"], 50)

    def test_corrupted_counts_omits_table(self):
        path = next(self.root.glob("pilot/**/counts.json"))
        rows = json.loads(path.read_text())
        rows[0][3]["kept"] += 1
        path.write_text(json.dumps(rows))
        wr.aggregate(self.v, self.root)
        self.assertTrue(self.v.get("tree")["problems"])
        self.assertEqual(self.v.get("tree")["levels"], [])

    def test_second_unselected_copy_is_not_double_counted(self):
        result = self.root / "pilot/research/unit-distance-24/results/u24"
        duplicate = self.root / "unselected/research/unit-distance-24/results/u24"
        shutil.copytree(result, duplicate)
        wr.aggregate(self.v, self.root)
        self.assertEqual(self.v.get("tree")["counted_copies"], 3)
        self.assertEqual(self.v.get("tree")["levels"][-1]["kept"], 1)

    def test_sidecar_is_deterministic_and_pins_counted_sources(self):
        wr.aggregate(self.v, self.root)
        destination = self.root.parent / "result-sources.json.gz"
        wr.pack_sources(self.v, destination, self.root.parent / "values.json")
        first = self.v.sidecar
        obj = json.loads(gzip.decompress(first))
        self.assertEqual(len(obj["selected"]), 3)
        for row in obj["selected"]:
            ref = row["counts"]
            self.assertEqual(ref["sha256"], hashlib.sha256((self.v.repo / ref["file"]).read_bytes()).hexdigest())
        wr.pack_sources(self.v, destination, self.root.parent / "values.json")
        self.assertEqual(first, self.v.sidecar)


def load_tests(loader, tests, pattern):
    # Aggregation checks run first; the real-evidence restoration stays LAST
    # across the entire suite, rather than only within its own class.
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(AggregationTests))
    suite.addTests(loader.loadTestsFromTestCase(EvidenceTests))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
