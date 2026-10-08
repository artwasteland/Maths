#!/usr/bin/env python3
"""Stdlib synthetic allocation tests; expected residues are written by hand.

Run normally for green tests, or with --mutation-checks to run the fatal tests
against in-memory copies with one guard disabled. No production file is edited.
These fixture receipts model bundle structure, not mathematical certificates.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import round_from_rounds as merge
import rounds


def record(code, verdict="unknown", marker="base"):
    return (json.dumps({"g6": code, "verdict": verdict,
                        "cert": {"reason": marker, "budget": {"stages": [marker]}}}) + "\n").encode()


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parents = {name: self.root / name for name in ("f1", "f1b", "f2", "p2")}
        for parent in self.parents.values():
            parent.mkdir()
        self.source = self.root / "source.g6"
        self.source.write_bytes(b"A?\nA_\nB@\nBA\nBD\nBE\n")
        self.output = self.root / "output"
        # Independently fixed fixture buckets, SHA256's first 8 bytes mod 3:
        # shard 0: A_, BA; shard 1: A?, BE; shard 2: B@, BD.
        self.make_bundle("f1", 0, [record("A_"), record("BA")])
        self.make_bundle("f1", 1, [record("A?"), record("BE", "refuted")])
        self.make_bundle("f1b", 2, [record("B@"), record("BD", "embedded")])

    def make_bundle(self, name, index, lines, assigned=None):
        directory = self.parents[name] / f"{name}-{index:03d}"
        directory.mkdir(exist_ok=True)
        records = [json.loads(line) for line in lines]
        if assigned is None:
            assigned = {r["g6"] for r in records}
        (directory / "assigned.g6").write_text("".join(c + "\n" for c in sorted(assigned)))
        frontier = sorted(r["g6"] for r in records if r["verdict"] == "unknown")
        (directory / "UNKNOWN.g6").write_text("".join(c + "\n" for c in frontier))
        with (directory / "records.jsonl.gz").open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
                stream.write(b"".join(lines))
        summary = {"completed": True, "checker_status": "ACCEPT", "assigned_count": len(assigned),
                   "counts": {v: sum(r["verdict"] == v and r["g6"] in assigned for r in records)
                              for v in ("embedded", "refuted", "unknown")},
                   "artifacts": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                                 for name in ("assigned.g6", "UNKNOWN.g6", "records.jsonl.gz")}}
        (directory / "summary.json").write_text(json.dumps(summary) + "\n")
        return directory

    def prepare(self, output=None, overlay_inputs=None):
        return merge.prepare(output or self.output, self.source, **self.parents,
                             shard_count=3, expected_count=len(self.source.read_text().splitlines()),
                             overlay_inputs=overlay_inputs)

    def residue(self):
        return (self.output / "input.g6").read_bytes()

    def unknown_bytes(self):
        with gzip.open(self.output / "unknown-records.jsonl.gz", "rb") as stream:
            return stream.read()

    def test_base_residue_and_manifest(self):
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"A?\nA_\nB@\nBA\n")
        self.assertEqual(manifest["base"]["counts"], {"embedded": 1, "refuted": 1, "unknown": 4})
        self.assertEqual(manifest["base"]["shard_indices"], [0, 1, 2])
        self.assertEqual(manifest["count"], 4)
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["purpose"], "frontier_allocation_only")
        self.assertEqual(manifest["helper_sha256"], hashlib.sha256(Path(merge.__file__).read_bytes()).hexdigest())
        for receipt in manifest["predecessors"]:
            directory = Path(receipt["bundle"])
            self.assertEqual(receipt["records_jsonl_gz_sha256"],
                             hashlib.sha256((directory / "records.jsonl.gz").read_bytes()).hexdigest())
            self.assertEqual(receipt["counts"], json.loads((directory / "summary.json").read_text())["counts"])

    def test_f1_first_displacement(self):
        self.make_bundle("f1b", 0, [record("A_", "embedded"), record("BA", marker="displaced")])
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"A?\nA_\nB@\nBA\n")
        self.assertEqual(self.unknown_bytes(), record("A?") + record("A_") + record("B@") + record("BA"))
        self.assertEqual(manifest["displaced_f1b_shards"], [0])
        self.assertEqual(manifest["base"]["bundles_by_round"], {"f1": 2, "f1b": 1})
        self.assertEqual(manifest["displaced_f1b_bundles"][0]["counts"],
                         {"embedded": 1, "refuted": 0, "unknown": 1})

    def test_overlay_decided_drops_embedded_and_refuted(self):
        self.make_bundle("f2", 0, [record("A_", "embedded"), record("A?", "refuted")])
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"B@\nBA\n")
        self.assertEqual(self.unknown_bytes(), record("B@") + record("BA"))
        self.assertEqual(manifest["overlay_effects"][0]["dropped_as_decided"], 2)
        self.assertEqual(manifest["overlay_effects"][0]["dropped_by_verdict"], {"embedded": 1, "refuted": 1})

    def test_overlay_unknown_replaces_exact_bytes_in_order(self):
        first = b'{ "g6":"BA", "verdict":"unknown", "cert":{"reason":"f2", "budget":{}} }\n'
        latest = (b'{ "verdict" : "unknown", "g6" : "BA", "cert" : '
                  b'{"budget":{"stages":[{"stage":"p2", "prior":[1,2]}]}, "reason":"late \\u03bb"} }\n')
        self.make_bundle("f2", 0, [first])
        self.prepare()
        self.assertEqual(self.residue(), b"A?\nA_\nB@\nBA\n")
        self.assertEqual(self.unknown_bytes(), record("A?") + record("A_") + record("B@") + first)
        self.output = self.root / "after-p2"
        self.make_bundle("p2", 0, [latest])
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"A?\nA_\nB@\nBA\n")
        # The expected replacement is the literal fixture bytes, not a parsed
        # and reserialized record or an answer obtained from the merge logic.
        self.assertEqual(self.unknown_bytes(), record("A?") + record("A_") + record("B@") + latest)
        self.assertEqual([e["records_replaced"] for e in manifest["overlay_effects"]], [1, 1])
        self.assertEqual(manifest["overlay_effects"][1]["overlap_with_previous_overlays"], ["BA"])
        self.assertTrue(manifest["overlay_effects"][1]["all_in_previous_overlays"])

    def test_missing_shard_fatal(self):
        # An empty bucket still needs its bundle: union coverage alone would
        # miss this error, so removing the shard-presence guard turns this red.
        self.source.write_bytes(b"A?\nA_\nBA\nBE\n")
        shutil.rmtree(self.parents["f1b"] / "f1b-002")
        with self.assertRaisesRegex(ValueError, r"base_missing_shards:indices=\[2\]"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_duplicate_base_assignment_fatal(self):
        self.make_bundle("f1", 1, [record("A?"), record("A_"), record("BE", "refuted")])
        with self.assertRaisesRegex(ValueError, r"base_duplicate_assignment:indices=\[0, 1\]"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_overlay_not_unknown_in_base_fatal(self):
        for code in ("BD", "BE"):
            with self.subTest(base_decided=code):
                self.output = self.root / ("output-" + code)
                self.make_bundle("f2", 0, [record(code)])
                with self.assertRaisesRegex(ValueError, "overlay_base_not_unknown:f2"):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_conflicting_overlay_decisions_fatal(self):
        self.make_bundle("f2", 0, [record("A_", "embedded")])
        self.make_bundle("p2", 0, [record("A_", "refuted")])
        with self.assertRaisesRegex(ValueError, "conflicting_decisions:g6='A_'"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_conflicting_displaced_decisions_fatal(self):
        self.make_bundle("f1b", 1, [record("A?"), record("BE", "embedded")])
        with self.assertRaisesRegex(ValueError, "conflicting_decisions:g6='BE'"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_missing_base_graph_fatal(self):
        self.make_bundle("f1b", 2, [record("B@")])
        with self.assertRaisesRegex(ValueError, r"base_input_coverage:missing=1 extra=0 missing_shards=\[2\]"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_extra_base_graph_fatal(self):
        self.make_bundle("f1", 1, [record("A?"), record("BE", "refuted"), record("BF")])
        with self.assertRaisesRegex(ValueError, r"base_input_coverage:missing=0 extra=1 missing_shards=\[\] extra_shards=\[1\]"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_shard_assignment_fatal(self):
        self.make_bundle("f1", 0, [record("A?"), record("BE", "refuted")])
        self.make_bundle("f1", 1, [record("A_"), record("BA")])
        with self.assertRaisesRegex(ValueError, r"base_shard_assignment:indices=\[0, 1\]"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_incomplete_overlay_input_fatal(self):
        wanted = self.root / "p2-input.g6"
        wanted.write_bytes(b"BA\n")
        with self.assertRaisesRegex(ValueError, "overlay_input_coverage:p2 missing=1 extra=0"):
            self.prepare(overlay_inputs={"p2": wanted})
        self.assertFalse(self.output.exists())

    def test_decision_persists_and_same_decision_is_not_counted_twice(self):
        self.make_bundle("f2", 0, [record("A_", "embedded"), record("BA", "embedded")])
        self.make_bundle("p2", 0, [record("A_", "embedded"), record("BA")])
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"A?\nB@\n")
        effect = manifest["overlay_effects"][1]
        self.assertEqual(effect["dropped_as_decided"], 0)
        self.assertEqual(effect["records_replaced"], 0)
        self.assertEqual(effect["already_decided_same_verdict"], 1)
        self.assertEqual(effect["unknown_after_decision_ignored"], 1)

    def test_support_records_do_not_change_allocation(self):
        self.make_bundle("f1", 0, [record("A_"), record("BA"), record("B?", "refuted")],
                         assigned={"A_", "BA"})
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"A?\nA_\nB@\nBA\n")
        self.assertEqual(manifest["predecessors"][0]["supporting_records"], 1)

    def test_empty_residue(self):
        self.make_bundle("f2", 0, [record("A?", "embedded"), record("A_", "embedded"),
                                   record("B@", "refuted"), record("BA", "refuted")])
        manifest = self.prepare()
        self.assertEqual(self.residue(), b"")
        self.assertEqual(self.unknown_bytes(), b"")
        self.assertEqual(manifest["count"], 0)

    def test_rounds_coverage_compatibility_and_determinism(self):
        self.prepare()
        again = self.root / "again"
        self.prepare(output=again)
        for name in ("input.g6", "unknown-records.jsonl.gz", "round.json"):
            self.assertEqual((self.output / name).read_bytes(), (again / name).read_bytes())
        # A synthetic return covering the HAND-WRITTEN expected frontier lets
        # the existing rounds.coverage validate the new allocation format.
        returned = self.make_bundle("p2", 0, [record("A?"), record("A_"), record("B@"), record("BA")])
        report = rounds.coverage(self.output, [returned])
        self.assertEqual(report["coverage_status"], "PASS")
        self.assertEqual(report["count"], 4)
        self.assertFalse(report["certificates_rechecked"])


def mutation_checks():
    """Every fatal test must fail an assertion with its own guard disabled."""
    original = merge
    source = Path(original.__file__).read_text()
    cases = [
        ("missing_shard", "    if missing:\n", ["test_missing_shard_fatal"]),
        ("duplicate_base", "        if overlap:\n", ["test_duplicate_base_assignment_fatal"]),
        ("base_unknown", "        if invalid:\n", ["test_overlay_not_unknown_in_base_fatal"]),
        ("conflict", "    if previous and previous[0] != verdict:\n",
         ["test_conflicting_overlay_decisions_fatal", "test_conflicting_displaced_decisions_fatal"]),
        ("input_coverage", "    if absent or surplus:\n",
         ["test_missing_base_graph_fatal", "test_extra_base_graph_fatal"]),
        ("shard_assignment", "    if misplaced:\n", ["test_wrong_shard_assignment_fatal"]),
        ("overlay_coverage", "            if assigned != overlay_expected:\n", ["test_incomplete_overlay_input_fatal"]),
    ]
    checked = 0
    try:
        for label, guard, names in cases:
            if source.count(guard) != 1:
                raise AssertionError("mutation_guard_not_unique:" + label)
            mutant = types.ModuleType("round_from_rounds_mutant")
            mutant.__file__ = original.__file__
            sys.modules[mutant.__name__] = mutant
            disabled = guard[:guard.index("if ")] + "if False:\n"
            exec(compile(source.replace(guard, disabled),
                         original.__file__, "exec"), mutant.__dict__)
            globals()["merge"] = mutant
            for name in names:
                log = io.StringIO()
                result = unittest.TextTestRunner(stream=log, verbosity=2).run(MergeTests(name))
                print(f"MUTATION {label}: {name}")
                print(log.getvalue(), end="")
                if result.wasSuccessful() or result.errors or not result.failures:
                    raise AssertionError("mutation_not_killed_by_assertion:" + name)
                checked += 1
    finally:
        globals()["merge"] = original
        sys.modules.pop("round_from_rounds_mutant", None)
    print(f"PASS: {checked} fatal tests went red across {len(cases)} disabled guards; source files unchanged.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--mutation-checks"]:
        mutation_checks()
    else:
        unittest.main()
