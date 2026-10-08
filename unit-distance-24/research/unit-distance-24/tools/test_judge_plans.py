#!/usr/bin/env python3
"""Plan regressions: python3 -B -m unittest discover -s research/unit-distance-24/tools -p test_judge_plans.py -v

Judge flow tests use synthetic audited copies and timings: this slim snapshot
lacks the u(23) modules and retained receipt fixtures. Plan validation, discovery,
ownership, copy gates, target-file comparison and the cost estimator run normally.
"""
import copy
import hashlib
from pathlib import Path
import random
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
import judge


def load_plan(name):
    return judge.evidence.load(judge.ROOT / f"coordination/cloud-workers/u24-{name}-plan.json")


def subset(tasks, slices):
    return {"target": [24, 69], "slice_level": 12, "count": 1920, "slices": slices, "tasks": tasks}


PUBLISHED = ("pilot", "full", "phaseb", "repro")


def main_owners():
    return {i: tag for name in ("pilot", "full", "phaseb") for i, tag in judge.plan_owners(load_plan(name)).items()}


def untouched_full_slice():
    """A full-plan slice still owned by the task that lists it, untouched by every published move, prune, rerun and
    validation record and in no other plan. The fixtures below used slice 49 (v19) until the 2026-10-05 wave gave it a
    rerun record (v19 -> w47); picking by property keeps them valid as the published plans grow."""
    full = load_plan("full")
    owners = judge.plan_owners(full)
    touched = {75, 344}  # slices other fixtures use directly
    for name in PUBLISHED:
        plan = load_plan(name)
        touched |= {i for r in plan.get("moved", []) for i in r["slices"]}
        touched |= {i for r in plan.get("pruned", []) for v in r["removed"].values() for i in v}
        touched |= {r["slice"] for field in ("rerun", "validation") for r in judge.copy_requests(plan, field)}
        if name != "full":
            touched |= set(judge.plan_owners(plan))
    for tag, slices in sorted(full["tasks"].items()):
        for i in sorted(slices):
            if i not in touched and owners[i] == tag:
                return i, tag
    raise AssertionError("no untouched full-plan slice")


def published_rerun_count():
    return sum(len(list(judge.copy_requests(load_plan(name), "rerun"))) for name in PUBLISHED)


class PlanTests(unittest.TestCase):
    def test_current_plans_and_partition(self):
        pilot, full, repro = (load_plan(name) for name in ("pilot", "full", "repro"))
        before = copy.deepcopy([pilot, full, repro])
        p, a, r = (set(judge.plan_check(plan)) for plan in (pilot, full, repro))
        b = set(full["phase_b"]["slices"])
        self.assertEqual((len(p), len(a), len(b), len(r)), (42, 1841, 37, 50))
        self.assertFalse(p & a or p & b or a & b)
        self.assertEqual(p | a | b, set(range(1920)))
        self.assertEqual(r, set(repro["random"] + repro["chosen"]["heavy"]))
        self.assertEqual([pilot, full, repro], before)

    def test_pruned_and_moved_ownership(self):
        for name in ("pilot", "full"):
            plan = load_plan(name)
            owners = judge.plan_owners(plan)
            for record in plan["pruned"]:
                for tag, values in record["removed"].items():
                    for i in values:
                        self.assertEqual(owners[i], tag)
            final = {}
            for record in plan.get("moved", []):  # a chained move: the LAST record naming a slice owns it
                for i in record["slices"]:
                    final[i] = record["to"]
            for i, tag in final.items():
                self.assertEqual(owners[i], tag)
        plan = subset({"live": [4]}, [1, 2, 3, 4])
        plan["pruned"] = [{"removed": {"done": [1]}}, {"removed": {"earlier": [2]}}]
        plan["moved"] = [{"from": "old", "to": "new", "slices": [3]}]
        self.assertEqual(judge.plan_check(plan), [1, 2, 3, 4])
        self.assertEqual(judge.plan_owners(plan), {1: "done", 2: "earlier", 3: "new", 4: "live"})

    def test_missing_slice_is_rejected(self):
        for name in ("pilot", "full", "repro"):
            for source in (("tasks", "pruned") if name != "repro" else ("tasks",)):
                with self.subTest(plan=name, source=source):
                    plan = load_plan(name)
                    table = plan["tasks"] if source == "tasks" else plan["pruned"][0]["removed"]
                    next(values for values in table.values() if values).pop(0)
                    with self.assertRaisesRegex(ValueError, "do not cover the declared slices exactly once"):
                        judge.plan_check(plan)

    def test_slice_owned_twice_is_rejected(self):
        for source in ("tasks", "pruned", "moved"):
            with self.subTest(source=source):
                plan = subset({"owner": [1]}, [1])
                if source == "tasks":
                    plan["tasks"]["other"] = [1]
                elif source == "pruned":
                    plan["pruned"] = [{"removed": {"other": [1]}}]
                else:
                    plan["moved"] = [{"from": "owner", "to": "other", "slices": [1]}]
                with self.assertRaisesRegex(ValueError, "more than once"):
                    judge.plan_check(plan)

    def test_move_can_already_be_in_receivers_tasks(self):
        plan = subset({"receiver": [1]}, [1])
        plan["moved"] = [{"from": "donor", "to": "receiver", "slices": [1]}]
        self.assertEqual(judge.plan_check(plan), [1])
        self.assertEqual(judge.plan_owners(plan), {1: "receiver"})

    def test_full_partition_overlap_and_wrong_pilot_are_rejected(self):
        full = load_plan("full")
        full["phase_b"]["slices"][0] = full["pilot"]["slices"][0]
        with self.assertRaisesRegex(ValueError, "must partition"):
            judge.plan_check(full)
        full = load_plan("full")
        full["pilot"]["slices"][0] = full["tasks"]["v01"][0]
        with self.assertRaisesRegex(ValueError, "differ from the reconstructed pilot"):
            judge.plan_check(full)

    def test_repro_seed_draw_and_heavy_schema(self):
        for change, message in (({"seed": True}, "seed must be an integer"),
                                ({"seed": 20261004}, "published sampling rule"),
                                ({"random": []}, "published sampling rule"),
                                ({"chosen": {"heavy": []}}, "chosen heavy"),
                                ({"chosen": {"heavy": [10]}}, "disjoint")):
            with self.subTest(change=change):
                plan = load_plan("repro")
                plan.update(change)
                with self.assertRaisesRegex(ValueError, message):
                    judge.plan_check(plan)

    def test_legacy_declarations_and_pilot_sampling_rule(self):
        self.assertEqual(judge.plan_check(subset({"worker": [1, 2]}, [1, 2])), [1, 2])
        all_plan = subset({"worker": list(range(1920))}, list(range(1920)))
        all_plan["all"] = True
        all_plan["job"] = "u24-full"
        self.assertEqual(judge.plan_check(all_plan), list(range(1920)))
        pilot = load_plan("pilot")
        pilot["random_seed"] += 1
        with self.assertRaisesRegex(ValueError, "published sampling rule"):
            judge.plan_check(pilot)

    def test_superseded_schema_is_checked(self):
        valid = {"slice": 1, "tag": "old", "receipt_sha256": "a" * 64, "reason": "rerun"}
        invalid = [None, {}, [None], [dict(valid, slice=True)], [dict(valid, tag="bad/tag")],
                   [dict(valid, receipt_sha256="bad")], [dict(valid, tag=None)],
                   [dict(valid, reason=" ")], [valid, valid]]
        for records in invalid:
            with self.subTest(records=records):
                plan = subset({"owner": [1]}, [1])
                plan["superseded"] = records
                with self.assertRaisesRegex(ValueError, "PLAN: .*superseded"):
                    judge.plan_check(plan)

    def test_rerun_transfers_tasks_pruned_and_chained_moves(self):
        listed = subset({"old": [1]}, [1])
        pruned = dict(subset({"old": []}, [1]), pruned=[{"removed": {"old": [1]}}])
        moved = dict(subset({"worker": [2]}, [1, 2]), moved=[
            {"from": "first", "to": "middle", "slices": [1]},
            {"from": "middle", "to": "old", "slices": [1]}])
        for plan in (listed, pruned, moved):
            with self.subTest(plan=plan):
                plan["rerun"] = [{"slice": 1, "from": "old", "to": "new", "why": "suspect overlap"}]
                before = copy.deepcopy(plan)
                self.assertEqual(judge.plan_check(plan), plan["slices"])
                self.assertEqual(judge.plan_owners(plan)[1], "new")
                self.assertEqual(plan, before)

    def test_rerun_refuses_wrong_source_duplicate_and_existing_destination(self):
        request = {"slice": 1, "from": "old", "to": "new", "why": "suspect overlap"}
        for records, message in (([dict(request, **{"from": "stranger"})], "not the current owner"),
                                 ([dict(request, to="old")], "already owns"),
                                 ([request, dict(request, **{"from": "new", "to": "next"})], "duplicate rerun")):
            with self.subTest(records=records):
                plan = dict(subset({"old": [1]}, [1]), rerun=records)
                with self.assertRaisesRegex(ValueError, message):
                    judge.plan_check(plan)

    def test_rerun_and_validation_schema(self):
        for field, tags in (("rerun", {"from": "old", "to": "new"}), ("validation", {"tag": "check"})):
            valid = dict(slice=1, why="independent run", **tags)
            invalid = [None, {}, [None], [dict(valid, slice=True)], [dict(valid, slice=1920)],
                       [dict(valid, why=" ")], [dict(valid, **{next(iter(tags)): "bad/tag"})], [valid, valid]]
            for records in invalid:
                with self.subTest(field=field, records=records):
                    plan = dict(subset({"old": [1]}, [1]), **{field: records})
                    with self.assertRaisesRegex(ValueError, f"PLAN: .*{field}"):
                        judge.plan_check(plan)

    def test_validation_cannot_relabel_current_or_retired_owner(self):
        for tag in ("old", "new"):
            with self.subTest(tag=tag):
                plan = subset({"old": [1]}, [1])
                plan["rerun"] = [{"slice": 1, "from": "old", "to": "new", "why": "suspect"}]
                plan["validation"] = [{"slice": 1, "tag": tag, "why": "check"}]
                with self.assertRaisesRegex(ValueError, "owner or a retired owner"):
                    judge.plan_check(plan)


class JudgeFlowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix=".judge-plans-", dir=judge.ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fleet = self.root / "fleet"
        self.fleet.mkdir()
        self.baseline = {"plan": {"target": [23, 65]}, "coverage": {"complete": 1920},
                         "cost": {"slices_timed": 1920, "slices_excluded_resumed": 0, "rule": "test"},
                         "slices": {str(i): {"seconds_known": 1, "replay": {"run_dag2_wall_seconds": 1}}
                                    for i in range(1920)}}
        self.mock_judge("reference", return_value=({}, {i: set() for i in range(1920)}))
        self.mock_judge("known_check", return_value=([], None))
        self.mock_judge("summary_audit", side_effect=lambda dirs, total, work: {
            "problems": [], "unresolved": [], "status": "per-slice OK", "missing_slices": 1920 - total})
        self.mock_judge("accepted_copy", side_effect=lambda c, structure, body: dict(
            c, prefix=(("prefix", "same"),), options={}, counts={}, upper={}, keep_lines=[],
            structure={"target_files": {"keep": body}, "g4": {"result": "PASS"}}))
        self.mock_judge("timing", side_effect=lambda c: {
            "source": c["worker"], "accepted": c["accepted"], "lower_bound": not c["accepted"],
            "step_seconds": 2, "run_dag2_seconds": 2, "issues": [],
            **{phase + "_seconds": 1 for phase in ("g4", "check", "control", "evidence")}})
        real_sha = judge.evidence.sha
        self.start_patch(patch.object(judge.evidence, "sha", side_effect=lambda path:
            judge.CHECKER_PIN if path in (judge.BASELINE, judge.worker.CHECKER) else real_sha(path)))

        def audit(result, receipt, dest):
            if "# u24-worker verdict: FAIL" in receipt.read_text().splitlines():
                raise ValueError("RECEIPT: worker did not pass")
            return {}

        self.prepare = self.start_patch(patch.object(judge.receipt_audit, "prepare", side_effect=audit))
        self.compare = Mock(return_value=[])
        self.start_patch(patch.dict(sys.modules, {"aggregate_fleet": types.SimpleNamespace(compare_copies=self.compare)}))
        # The published full plan's `superseded` and `validation` records (Liam's 2026-10-06 amendment, pinned by
        # LiveAmendmentTests below) name copies that exist only in the real fleet; a superseded record must match
        # exactly one discovered copy, so these synthetic fleets see the published plans without those two fields,
        # as they were written. Each flow test adds its own records where it needs them.
        real_load = judge.evidence.load
        published = {judge.PILOT, judge.FULL, judge.PHASEB, judge.REPRO}
        self.start_patch(patch.object(judge.evidence, "load", side_effect=lambda path: (
            {k: v for k, v in real_load(path).items() if k not in ("superseded", "validation")}
            if path in published else real_load(path))))

    def start_patch(self, patcher):
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def mock_judge(self, name, **kwargs):
        return self.start_patch(patch.object(judge, name, **kwargs))

    def receipt(self, i, tag, branch=None, body="matching"):
        base = self.fleet / (branch or tag) / judge.SUB
        check = base / "check"
        check.mkdir(parents=True, exist_ok=True)
        result = base / judge.KIND / f"s{i}of1920"
        result.mkdir(parents=True, exist_ok=True)
        path = check / f"s{i}of1920-{tag}.txt"
        path.write_text(body)
        return path

    def evaluate(self, plan):
        return judge.judge(self.fleet, plan, self.root / "work", baseline=self.baseline)

    def result_dir(self, receipt):
        index = int(judge.RECEIPT_NAME.fullmatch(receipt.stem)[1])
        return receipt.parent.parent / judge.KIND / f"s{index}of1920"

    def bare_result(self, i, branch="old-branch"):
        path = self.fleet / branch / judge.SUB / judge.KIND / f"s{i}of1920"
        path.mkdir(parents=True)
        return path

    def supersede(self, plan, i, tag, receipt=None):
        record = {"slice": i, "tag": tag,
                  "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt else None,
                  "reason": "interrupted; rerun from scratch"}
        plan.setdefault("superseded", []).append(record)
        return record

    def plant_survivor(self, result):
        graph = (Path(__file__).resolve().parents[1] / "fixtures/nonempty24/24-69.g6").read_bytes()
        (result / "24-69.keep.g6").write_bytes(graph)
        return graph.decode().strip()

    def rerun(self, plan, i=1, source="old", dest="new"):
        plan.setdefault("rerun", []).append({"slice": i, "from": source, "to": dest, "why": "suspect overlap; fresh run"})

    def validation(self, plan, i=1, tag="check"):
        plan.setdefault("validation", []).append({"slice": i, "tag": tag, "why": "independent validation"})

    def repro_with_main_owners(self):
        # Seed 0 was chosen to avoid phase B while it was held; phase B now has owners (w24 and others) too.
        plan = load_plan("repro")
        plan["seed"] = 0
        plan["random"] = sorted(random.Random(0).sample(range(1920), 48))
        plan["tasks"] = {"repro": plan["random"] + plan["chosen"]["heavy"]}
        owners = {i: tag for name in ("pilot", "full", "phaseb")
                  for i, tag in judge.plan_owners(load_plan(name)).items()}
        return plan, owners

    def test_non_owner_receipt_is_rejected_before_audit(self):
        self.receipt(1, "intruder")
        result = self.evaluate(subset({"owner": [1]}, [1]))
        self.assertEqual((result["verdict"], result["exit"], result["accepted_copies"]), ("FAIL", 1, 0))
        self.assertEqual(result["missing"], [1])
        self.assertIn("OWNERSHIP: tag intruder does not own slice 1", result["rejected"][0])
        self.assertEqual(result["cost"]["rows"], {})
        self.prepare.assert_not_called()

    def test_moved_donor_receipt_is_rejected(self):
        # Slice 384 moved u18 -> u15 (2026-10-01), then u15 -> w13 (2026-10-05): every donor in the chain is rejected.
        plan = load_plan("pilot")
        donors = [m["from"] for m in plan["moved"] if 384 in m["slices"]]
        owner = judge.plan_owners(plan)[384]
        self.assertTrue(donors and owner not in donors)
        for tag in donors + [owner]:
            self.receipt(384, tag)
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["accepted_copies"], 1)
        self.assertEqual(len(result["rejected"]), len(donors))
        for tag in donors:
            self.assertIn(f"OWNERSHIP: tag {tag} does not own slice 384", " ".join(result["rejected"]))

    def test_reconstructed_pilot_is_the_cost_sample(self):
        plan = load_plan("pilot")
        for i, tag in judge.plan_owners(plan).items():
            self.receipt(i, tag)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["accepted_copies"]), ("OK", 0, 42))
        self.assertEqual(result["cost"]["sample_measured"], {"heavy": 10, "random": 32})
        self.assertEqual(result["cost"]["estimates"]["step"]["unavailable"], [])
        self.assertAlmostEqual(result["cost"]["estimates"]["step"]["T24_seconds"], 3840)
        self.assertEqual(len(judge.plan_check(result["provenance"]["cost_sample"])), 42)

    def test_current_repro_with_one_copy_is_partial(self):
        plan = load_plan("repro")
        for i, tag in judge.plan_owners(plan).items():
            self.receipt(i, tag)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["accepted_copies"]), ("PARTIAL", 3, 50))
        self.assertEqual(result["missing"], [])
        self.assertEqual(len(result["pending"]), 50)
        self.assertIn("COPIES: slice 344: no accepted main copy", result["pending"])
        self.assertFalse(result["problems"])

    def test_two_copies_from_same_role_are_insufficient(self):
        plan, main = self.repro_with_main_owners()
        for role in ("main", "repro"):
            with self.subTest(role=role), tempfile.TemporaryDirectory(dir=self.root) as tmp:
                with patch.object(self, "fleet", Path(tmp)):
                    for i, tag in judge.plan_owners(plan).items():
                        owner = main[i] if role == "main" else tag
                        self.receipt(i, owner)
                        self.receipt(i, owner, branch=owner + "-copy")
                    result = self.evaluate(plan)
                self.assertEqual((result["verdict"], result["accepted_copies"]), ("PARTIAL", 100))
                missing_role = "repro" if role == "main" else "main"
                self.assertIn(f"COPIES: slice 344: no accepted {missing_role} copy", result["pending"])
                self.assertFalse(result["problems"])

    def test_matching_main_and_repro_copies_pass_disagreement_fails(self):
        plan, main = self.repro_with_main_owners()
        for i, tag in judge.plan_owners(plan).items():
            self.receipt(i, main[i])
            self.receipt(i, tag)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["accepted_copies"]), ("OK", 0, 100))
        self.assertEqual(len(result["duplicates"]), 50)
        self.assertEqual(self.compare.call_count, 50)
        self.assertEqual(result["pending"], [])
        self.receipt(344, "repro", body="different target measurement")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"]), ("FAIL", 1))
        self.assertIn("COPIES: slice 344: accepted copies disagree on target file measurements", result["problems"])
        self.assertEqual(result["pending"], [])

    def test_rejected_second_copy_does_not_satisfy_repro(self):
        plan, main = self.repro_with_main_owners()
        for i, tag in judge.plan_owners(plan).items():
            self.receipt(i, main[i])
            self.receipt(i, tag)

        def audit(result, receipt, dest):
            if receipt.name == "s344of1920-repro.txt":
                raise ValueError("invalid receipt")
            return {}

        self.prepare.side_effect = audit
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("FAIL", 99))
        self.assertEqual(result["pending"], ["COPIES: slice 344: no accepted repro copy"])

    def test_one_owner_cannot_fill_both_repro_roles(self):
        plan = load_plan("repro")
        plan["tasks"][main_owners()[344]] = plan["tasks"].pop("r01")
        with self.assertRaisesRegex(ValueError, "main and repro owners must differ"):
            self.evaluate(plan)

    def test_phase_b_owner_is_the_main_copy_of_a_phase_b_repro_slice(self):
        # Slice 1270 is in phase B (owner w24) and in the repro plan (owner r03).
        plan = load_plan("repro")
        self.receipt(1270, "r03")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["accepted_copies"]), ("PARTIAL", 3, 1))
        self.assertIn("COPIES: slice 1270: no accepted main copy", result["pending"])
        self.assertFalse(result["rejected"] or result["problems"])
        self.receipt(1270, "unassigned")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("FAIL", 1))
        self.assertIn("COPIES: slice 1270: no accepted main copy", result["pending"])
        self.assertIn("OWNERSHIP: tag unassigned does not own slice 1270", result["rejected"][0])
        self.receipt(1270, "w24")
        result = self.evaluate(plan)
        self.assertEqual(result["accepted_copies"], 2)
        self.assertFalse([p for p in result["pending"] if p.startswith("COPIES: slice 1270:")])
        self.assertEqual(len(result["rejected"]), 1)

    def test_superseded_failed_copy_needs_current_owner_replacement(self):
        plan = subset({"new": [1]}, [1])
        plan["moved"] = [{"from": "old", "to": "new", "slices": [1]}]
        failed = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        self.supersede(plan, 1, "old", failed)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["missing"]), ("PARTIAL", 3, [1]))
        self.assertEqual(result["pending"], ["COVERAGE: slice 1: no accepted copy"])
        self.assertFalse(result["rejected"] or result["problems"] or result["cost"]["rows"])
        self.receipt(1, "new")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["superseded"], [dict(plan["superseded"][0], copy=str(failed.relative_to(self.fleet)))])
        self.assertEqual(len(result["cost"]["rows"]["1"]), 1)
        self.assertIn("SUPERSEDED: slice 1, tag old:", judge.render(result))
        self.assertIn(plan["superseded"][0]["reason"], judge.render(result))
        del plan["superseded"]
        self.assertEqual(self.evaluate(plan)["verdict"], "FAIL")

    def test_superseded_must_match_slice_tag_and_receipt_hash(self):
        plan = subset({"new": [1]}, [1])
        failed = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        record = self.supersede(plan, 1, "old", failed)
        for change in ({"slice": 2}, {"tag": "other"}, {"receipt_sha256": "0" * 64}, {"receipt_sha256": None}):
            with self.subTest(change=change):
                bad = dict(plan, superseded=[dict(record, **change)])
                with self.assertRaisesRegex(ValueError, "PLAN: superseded.*exactly one.*found 0"):
                    self.evaluate(bad)

    def test_superseded_ambiguous_receipt_is_plan_error(self):
        plan = subset({"new": [1]}, [1])
        failed = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        self.receipt(1, "old", branch="old-copy", body=failed.read_text())
        self.supersede(plan, 1, "old", failed)
        with self.assertRaisesRegex(ValueError, "PLAN: superseded.*exactly one.*found 2"):
            self.evaluate(plan)

    def test_superseded_requires_an_unambiguous_fail_verdict(self):
        for body in ("# u24-worker verdict: pass\n", "missing verdict\n",
                     "# u24-worker verdict: FAIL\n# u24-worker verdict: pass\n"):
            with self.subTest(body=body):
                plan = subset({"owner": [1]}, [1])
                receipt = self.receipt(1, "owner", body=body)
                self.supersede(plan, 1, "owner", receipt)
                with self.assertRaisesRegex(ValueError, "PLAN: superseded.*must have a FAIL verdict or no receipt"):
                    self.evaluate(plan)

    def test_superseded_missing_receipts_remove_only_the_matched_pending_copy(self):
        for tag in (None, "old"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory(dir=self.root) as tmp:
                with patch.object(self, "fleet", Path(tmp)):
                    plan = subset({"new": [1]}, [1])
                    if tag is None:
                        self.bare_result(1)
                    else:
                        path = self.receipt(1, tag)
                        path.with_suffix(".structure.json").write_text("{}")
                        path.unlink()
                    self.supersede(plan, 1, tag)
                    result = self.evaluate(plan)
                    self.assertEqual(result["verdict"], "PARTIAL")
                    self.assertEqual(result["pending"], ["COVERAGE: slice 1: no accepted copy"])
                    self.receipt(1, "new")
                    result = self.evaluate(plan)
                    self.assertEqual(result["verdict"], "OK")
                    self.assertEqual(len(result["superseded"]), 1)
                    self.assertEqual(result["pending"], [])
                    # No wildcard tag matching for a bare result with tag None.
                    if tag is None:
                        plan["superseded"][0]["tag"] = "old"
                        with self.assertRaisesRegex(ValueError, "PLAN: superseded.*found 0"):
                            self.evaluate(plan)

    def test_unreceipted_becomes_information_only_after_acceptance(self):
        plan = subset({"owner": [1]}, [1])
        self.bare_result(1)
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertTrue(any("result pushed without receipts" in p for p in result["pending"]))
        self.assertEqual(result["unreceipted"], [])
        self.receipt(1, "owner", branch="same-tag-new-branch")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(result["pending"], [])
        self.assertEqual(len(result["unreceipted"]), 1)
        self.assertIn("UNRECEIPTED: slice 1, tag None:", judge.render(result))

    def test_incomplete_tagged_bundle_still_pending_without_supersession(self):
        plan = subset({"owner": [1]}, [1])
        path = self.receipt(1, "owner", branch="incomplete")
        path.with_suffix(".known.json").write_text("{}")
        path.unlink()
        self.receipt(1, "owner", branch="complete")
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertTrue(any("receipt bundle has no text receipt" in p for p in result["pending"]))
        self.assertEqual(result["unreceipted"], [])

    def test_foreign_copies_do_not_count_for_coverage_or_cost(self):
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        self.receipt(344, "r01", body="# u24-worker verdict: FAIL\n")
        i, tag = untouched_full_slice()
        self.receipt(i, tag)  # An unplanned slice from another published plan.
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["missing"]), ("PARTIAL", [344]))
        self.assertEqual(len(result["foreign"]), 2)
        self.assertEqual(result["cost"]["rows"], {})
        self.assertFalse(result["rejected"] or result["problems"])
        self.prepare.assert_not_called()
        self.receipt(344, "u01")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(result["unplanned_slices"], [i])
        self.assertEqual(list(result["cost"]["rows"]), ["344"])
        self.assertEqual(len(result["cost"]["rows"]["344"]), 1)
        self.assertIn("FOREIGN: slice 344, tag r01:", judge.render(result))

    def test_foreign_ownership_is_specific_to_slice_and_another_plan(self):
        plan = dict(subset({"replacement": [344]}, [344]), job="u24-pilot")
        self.receipt(344, "u01")  # The old selected-plan owner is not foreign.
        self.receipt(344, "r04")  # This repro tag owns other slices, not 344.
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(len(result["rejected"]), 2)
        self.assertEqual(result["foreign"], [])

    def test_other_published_plans_supersessions_apply_to_mixed_root(self):
        full = load_plan("full")
        i, tag = untouched_full_slice()
        full["tasks"][tag].remove(i)
        full["tasks"]["replacement"] = [i]
        full.setdefault("moved", []).append({"from": tag, "to": "replacement", "slices": [i]})
        failed = self.receipt(i, tag, body="# u24-worker verdict: FAIL\n")
        self.supersede(full, i, tag, failed)
        self.receipt(i, "replacement")
        self.receipt(344, "u01")
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        load = judge.evidence.load
        with patch.object(judge.evidence, "load", side_effect=lambda path: full if path == judge.FULL else load(path)):
            result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(len(result["superseded"]), 1)
        self.assertEqual(result["superseded"][0]["tag"], tag)
        self.assertEqual(len(result["foreign"]), 1)
        self.assertEqual(result["foreign"][0]["tag"], "replacement")

    def test_foreign_incomplete_bundle_is_not_pending(self):
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        path = self.receipt(344, "r01")
        path.with_suffix(".structure.json").write_text("{}")
        path.unlink()
        self.receipt(344, "u01")
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "OK")
        self.assertEqual(len(result["foreign"]), 1)
        self.assertEqual(result["pending"], [])

    def test_superseded_only_survivor_is_fail(self):
        plan = subset({"new": [1]}, [1])
        failed = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        self.supersede(plan, 1, "old", failed)
        graph = self.plant_survivor(self.result_dir(failed))
        replacement = self.receipt(1, "new")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"]), ("FAIL", 1))
        self.assertEqual(result["problems"], [f"TARGET: survivor in a non-accepted copy only: slice 1: graph6 {graph}"])
        self.assertEqual(result["survivors"][0]["graph6"], graph)
        self.assertFalse(result["survivors"][0]["copies"][0]["accepted"])
        self.assertIn("SURVIVOR: slices [1]:", judge.render(result))
        self.plant_survivor(self.result_dir(replacement))
        self.assertEqual(self.evaluate(plan)["verdict"], "OK")

    def test_other_nonaccepted_survivors_need_same_slice_accepted_survivor(self):
        for kind in ("unreceipted", "foreign", "rejected"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=self.root) as tmp:
                with patch.object(self, "fleet", Path(tmp)):
                    plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
                    if kind == "unreceipted":
                        other = self.bare_result(344)
                    else:
                        tag = "r01" if kind == "foreign" else "intruder"
                        other = self.result_dir(self.receipt(344, tag))
                    graph = self.plant_survivor(other)
                    current = self.result_dir(self.receipt(344, "u01"))
                    result = self.evaluate(plan)
                    self.assertEqual(result["verdict"], "FAIL")
                    self.assertIn(f"TARGET: survivor in a non-accepted copy only: slice 344: graph6 {graph}", result["problems"])
                    self.assertEqual(result["survivors"][0]["graph6"], graph)
                    self.plant_survivor(current)
                    result = self.evaluate(plan)
                    self.assertEqual(result["verdict"], "FAIL" if kind == "rejected" else "OK")
                    self.assertFalse(any("non-accepted copy only" in p for p in result["problems"]))

    def test_nonaccepted_survivors_remain_visible_without_accepted_copy(self):
        for kind in ("superseded", "unreceipted", "foreign"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=self.root) as tmp:
                with patch.object(self, "fleet", Path(tmp)):
                    plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
                    if kind == "unreceipted":
                        result_dir = self.bare_result(344)
                    else:
                        tag = "old" if kind == "superseded" else "r01"
                        receipt = self.receipt(344, tag, body="# u24-worker verdict: FAIL\n")
                        result_dir = self.result_dir(receipt)
                        if kind == "superseded":
                            self.supersede(plan, 344, tag, receipt)
                    graph = self.plant_survivor(result_dir)
                    result = self.evaluate(plan)
                    self.assertEqual(result["verdict"], "PARTIAL")
                    self.assertEqual(result["missing"], [344])
                    self.assertEqual(result["survivors"][0]["graph6"], graph)
                    self.assertFalse(result["survivors"][0]["copies"][0]["accepted"])

    def test_survivor_in_different_accepted_slice_is_not_a_replacement(self):
        plan = subset({"new": [1, 2]}, [1, 2])
        old = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        self.supersede(plan, 1, "old", old)
        self.plant_survivor(self.result_dir(old))
        self.receipt(1, "new")
        self.plant_survivor(self.result_dir(self.receipt(2, "new")))
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any("non-accepted copy only: slice 1:" in p for p in result["problems"]))

    def test_unplanned_foreign_survivor_is_still_read(self):
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        self.receipt(344, "u01")
        graph = self.plant_survivor(self.result_dir(self.receipt(49, "v19")))
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "OK")
        self.assertEqual(result["survivors"][0]["graph6"], graph)
        self.assertEqual(result["survivors"][0]["slices"], [49])
        self.assertFalse(result["survivors"][0]["copies"][0]["accepted"])

    def test_resumed_copy_count_and_slices_are_informational(self):
        plan = subset({"owner": [1, 2, 3]}, [1, 2, 3])
        self.receipt(1, "owner", branch="first")
        self.receipt(1, "owner", branch="second")
        self.receipt(2, "owner")
        self.receipt(3, "owner")
        self.prepare.side_effect = lambda result, receipt, dest: {
            "recovered_cells": ["16-33", "17-37"] if result.name in ("s1of1920", "s2of1920") else []}
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 4))
        self.assertEqual(result["resumed_copies"], 3)
        self.assertEqual(result["resumed_slices"], [1, 2])
        self.assertEqual(result["pending"], [])
        self.assertIn("RESUMED: 3 accepted copies carry recovered/resumed cells; slices [1, 2]", judge.render(result))

    def test_rerun_supersedes_all_old_pass_copies_without_coverage(self):
        plan = subset({"old": [1]}, [1])
        self.rerun(plan)
        body = "# u24-worker verdict: pass\n"
        self.receipt(1, "old", branch="first", body=body)
        self.receipt(1, "old", branch="second", body=body)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"], result["missing"]), ("PARTIAL", 0, [1]))
        published = published_rerun_count()  # the subset has no job, so every published plan's reruns count too
        self.assertEqual(result["rerun_count"], 1 + published)
        self.assertEqual(result["rerun_copies"], 2)
        self.assertTrue(all(row["accepted_looking"] for row in result["superseded"]))
        self.assertTrue(all(row["reason"] == plan["rerun"][0]["why"] for row in result["superseded"]))
        self.assertFalse(result["problems"] or result["rejected"] or result["cost"]["rows"])
        self.receipt(1, "new", body=body)
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(len(result["cost"]["rows"]["1"]), 1)
        self.assertEqual(result["rerun_disagreements"], [])
        self.assertIn(f"RERUN: {1 + published} transfers; 2 superseded copies; 0 disagreements", judge.render(result))

    def test_rerun_handles_failed_or_absent_old_receipt(self):
        plan = subset({"old": [1]}, [1])
        self.rerun(plan)
        self.receipt(1, "new")
        self.assertEqual(self.evaluate(plan)["verdict"], "OK")
        failed = self.receipt(1, "old", body="# u24-worker verdict: FAIL\n")
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "OK")
        self.assertFalse(result["superseded"][0]["accepted_looking"])
        self.assertIn("worker did not pass", result["superseded"][0]["audit_error"])
        failed.with_suffix(".structure.json").write_text("{}")
        failed.unlink()
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "OK")
        self.assertEqual(result["rerun_copies"], 1)
        self.assertEqual(result["pending"], [])

    def test_rerun_disagreements_are_findings_not_failures(self):
        plan = subset({"old": [1]}, [1])
        self.rerun(plan)
        self.receipt(1, "old", body="different target file measurements")
        self.receipt(1, "new")
        self.compare.return_value = ["cell counts differ", "file hashes differ"]
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertFalse(result["problems"] or result["rejected"])
        self.assertEqual(len(result["rerun_disagreements"]), 1)
        finding = result["rerun_disagreements"][0]
        self.assertEqual(finding["slice"], 1)
        self.assertIn("s1of1920-old.txt", finding["old_copy"])
        self.assertIn("s1of1920-new.txt", finding["new_copy"])
        self.assertTrue(any("counts" in d for d in finding["differences"]))
        self.assertTrue(any("target file measurements" in d for d in finding["differences"]))
        self.assertIn("RERUN DISAGREEMENT (informational): slice 1:", judge.render(result))
        # The old copy enters neither the known-graph audit nor the summary audit.
        self.assertEqual(len(judge.known_check.call_args.args[0][1]), 1)
        self.assertEqual(len(judge.summary_audit.call_args.args[0]), 1)

    def test_rerun_pass_survivor_cannot_be_hidden(self):
        plan = subset({"old": [1]}, [1])
        self.rerun(plan)
        body = "# u24-worker verdict: pass\n"
        old = self.receipt(1, "old", body=body)
        new = self.receipt(1, "new", body=body)
        graph = self.plant_survivor(self.result_dir(old))
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"]), ("FAIL", 1))
        self.assertIn(f"TARGET: survivor in a non-accepted copy only: slice 1: graph6 {graph}", result["problems"])
        self.assertTrue(result["superseded"][0]["accepted_looking"])
        self.assertFalse(result["survivors"][0]["copies"][0]["accepted"])
        self.assertIn(graph, judge.render(result))
        self.plant_survivor(self.result_dir(new))
        self.assertEqual(self.evaluate(plan)["verdict"], "OK")

    def test_validation_cannot_hide_survivor_absent_from_rerun_owner(self):
        plan = subset({"old": [1]}, [1])
        self.rerun(plan)
        self.validation(plan)
        old = self.receipt(1, "old")
        self.receipt(1, "new")
        validation = self.receipt(1, "check")
        graph = self.plant_survivor(self.result_dir(old))
        self.plant_survivor(self.result_dir(validation))
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn(f"TARGET: survivor in a non-accepted copy only: slice 1: graph6 {graph}", result["problems"])

    def test_published_reruns_and_validation_copies_work_in_mixed_root(self):
        full = load_plan("full")
        i, tag = untouched_full_slice()
        self.rerun(full, i, tag, "cx24-fresh")
        self.validation(full, 75, "cx24-pilot-75e")
        self.receipt(i, tag)
        self.receipt(i, "cx24-fresh")
        self.receipt(75, "cx24-pilot-75e")
        self.receipt(344, "u01")
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        load = judge.evidence.load
        with patch.object(judge.evidence, "load", side_effect=lambda path: full if path == judge.FULL else load(path)):
            result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 1))
        self.assertEqual(result["rerun_copies"], 1)
        self.assertEqual(result["superseded"][0]["tag"], tag)
        self.assertEqual(len(result["foreign"]), 2)
        self.assertEqual(result["validation_copies"], 0)

    def test_validation_is_audited_and_compared_but_excluded_from_cost(self):
        plan = subset({"v19": [75]}, [75])
        self.validation(plan, 75, "cx24-pilot-75e")
        self.receipt(75, "v19")
        self.receipt(75, "cx24-pilot-75e")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 2))
        self.assertEqual(result["accepted_slices"], [75])
        self.assertEqual((result["validation_count"], result["validation_copies"]), (1, 1))
        self.assertTrue(result["validation"][0]["accepted"])
        self.assertEqual(len(result["cost"]["rows"]["75"]), 1)
        self.assertEqual(len(judge.known_check.call_args.args[0][75]), 2)
        self.assertEqual(len(judge.summary_audit.call_args.args[0]), 2)
        self.assertEqual(self.compare.call_count, 1)
        self.assertIn("VALIDATION: 1 declared; 1 accepted copies (do not count toward coverage)", judge.render(result))

    def test_validation_never_fills_owner_coverage(self):
        plan = subset({"owner": [1]}, [1])
        self.validation(plan)
        self.receipt(1, "check")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["validation_copies"]), ("PARTIAL", 1))
        self.assertEqual(result["accepted_slices"], [])
        self.assertEqual(result["missing"], [1])
        self.assertEqual(result["cost"]["rows"], {})
        self.assertIn("VALIDATION: slice 1: no accepted owner copy (owner)", result["pending"])

    def test_validation_must_arrive_and_pass(self):
        plan = subset({"owner": [1]}, [1])
        self.validation(plan)
        self.receipt(1, "owner")
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertIn("VALIDATION: slice 1, tag check: no accepted validation copy", result["pending"])
        validation = self.receipt(1, "check", body="# u24-worker verdict: FAIL\n")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["validation_copies"]), ("FAIL", 0))
        self.assertIn("worker did not pass", result["rejected"][0])
        validation.with_suffix(".structure.json").write_text("{}")
        validation.unlink()
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertTrue(any("no text receipt" in p for p in result["pending"]))

    def test_validation_disagreement_fails(self):
        plan = subset({"owner": [1]}, [1])
        self.validation(plan)
        self.receipt(1, "owner")
        self.receipt(1, "check", body="different target file measurements")
        self.compare.return_value = ["file hashes differ"]
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["exit"], result["validation_copies"]), ("FAIL", 1, 1))
        self.assertTrue(any("hashes" in p for p in result["problems"]))
        self.assertTrue(any("target file measurements" in p for p in result["problems"]))
        self.assertEqual(result["rerun_disagreements"], [])

    def test_validation_of_unplanned_seed_requires_its_owner_without_expanding_coverage(self):
        plan = dict(subset({"u01": [344]}, [344]), job="u24-pilot")
        self.validation(plan, 75, "cx24-pilot-75e")
        self.receipt(344, "u01")
        self.receipt(75, "cx24-pilot-75e")
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertIn("VALIDATION: slice 75: no accepted owner copy (v19)", result["pending"])
        self.receipt(75, "v19")
        result = self.evaluate(plan)
        self.assertEqual((result["verdict"], result["accepted_copies"]), ("OK", 3))
        self.assertEqual(result["accepted_slices"], [344])
        self.assertEqual(result["unplanned_slices"], [75])
        self.assertEqual(list(result["cost"]["rows"]), ["344"])

    def test_validation_cannot_substitute_for_rerun_repro_role(self):
        plan, main = self.repro_with_main_owners()
        self.rerun(plan, 344, "repro", "new-repro")
        self.validation(plan, 344)
        for i, tag in judge.plan_owners(plan).items():
            self.receipt(i, main[i])
            self.receipt(i, tag)
        self.receipt(344, "repro")
        self.receipt(344, "check")
        self.assertEqual(self.evaluate(plan)["verdict"], "OK")
        self.receipt(344, "new-repro").unlink()
        result = self.evaluate(plan)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertIn("COPIES: slice 344: no accepted repro copy", result["pending"])
        self.assertEqual(result["validation_copies"], 1)

    def test_absent_evidence_remains_partial(self):
        result = self.evaluate(subset({"owner": [1]}, [1]))
        self.assertEqual((result["verdict"], result["exit"]), ("PARTIAL", 3))
        self.assertEqual(result["pending"], ["COVERAGE: slice 1: no accepted copy"])
        self.assertFalse(result["problems"])


class ChainedMoveTests(unittest.TestCase):
    """2026-10-01: a slice moved v -> Codex tag -> prepared-route tag (the middle tag's task ran out of time)."""
    def plan(self, moves):
        # As in the real plan, a moved slice is no longer in its donor's task list.
        return {"tasks": {"v01": [1]}, "moved": moves}

    def test_move_while_donor_still_lists_the_slice_is_refused(self):
        with self.assertRaisesRegex(ValueError, "more than once"):
            judge.plan_owners({"tasks": {"v01": [1, 2]}, "moved": [{"from": "v01", "to": "cxa", "slices": [2]}]})

    def test_chained_move_from_current_owner(self):
        owners = judge.plan_owners(self.plan([{"from": "v01", "to": "cxa", "slices": [2]},
                                              {"from": "cxa", "to": "cxb", "slices": [2]}]))
        self.assertEqual(owners, {1: "v01", 2: "cxb"})

    def test_move_from_a_non_owner_is_refused(self):
        with self.assertRaises(ValueError):
            judge.plan_owners(self.plan([{"from": "v01", "to": "cxa", "slices": [2]},
                                         {"from": "v01", "to": "cxb", "slices": [2]}]))


class LiveAmendmentTests(unittest.TestCase):
    """Liam's 2026-10-06 amendment of the published full plan, after the first full-fleet judge runs: it retires
    exactly the three non-owner FAIL copies of moved slices, declares slice 75's Codex pilot copy a validation copy,
    and re-points slice 610's undelivered re-run to the fresh VM run vm610. Real-fleet matching of these records is
    the judge run's job; this pins their shape so a later edit cannot widen them silently."""

    def setUp(self):
        self.full = load_plan("full")

    def test_live_plans_still_validate(self):
        for name in PUBLISHED:
            with self.subTest(plan=name):
                judge.plan_check(load_plan(name))

    def test_superseded_records_are_exactly_the_three_moved_from_fail_copies(self):
        records = judge.superseded_records(self.full)
        self.assertEqual(sorted((r["slice"], r["tag"]) for r in records), [(1175, "v19"), (1299, "v29"), (1591, "v31")])
        owners = judge.plan_owners(self.full)
        for r in records:
            with self.subTest(slice=r["slice"]):
                self.assertRegex(r["receipt_sha256"], r"^[0-9a-f]{64}$")
                self.assertNotEqual(owners[r["slice"]], r["tag"])
                self.assertTrue(any(m["from"] == r["tag"] and r["slice"] in m["slices"] for m in self.full["moved"]))

    def test_validation_record_is_only_slice_75_pilot(self):
        records = list(judge.copy_requests(self.full, "validation"))
        self.assertEqual([(r["slice"], r["tag"]) for r in records], [(75, "cx24-pilot-75e")])
        self.assertEqual(judge.plan_owners(self.full)[75], "v19")

    def test_slice_610_reruns_to_the_vm(self):
        records = [r for r in judge.copy_requests(self.full, "rerun") if r["slice"] == 610]
        self.assertEqual([(r["from"], r["to"]) for r in records], [("v14", "vm610")])
        self.assertEqual(judge.plan_owners(self.full)[610], "vm610")


if __name__ == "__main__":
    unittest.main()
