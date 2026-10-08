#!/usr/bin/env python3
"""Packet integrity/red tests. All temporary files stay below this directory."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import make_packets as packets

HERE = Path(__file__).resolve().parent
CODE = "J??????????"  # Canonical edgeless eleven-vertex graph (test only).


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".packet-test-", dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.record = {"g6": CODE, "verdict": "unknown", "cert": {"reason": "test residue", "budget": {"stages": []}}}
        self.frontier = {"g6": CODE, "id": 42, "edges": [], "tu_closure": {
            "g6": CODE, "old_to_new": list(range(11)), "steps": [], "end": None, "fixed_point": True}}
        self.attempt = {"id": 42, "stage": "esc-branch", "reason": "no_separated_seed", "outcome": "unknown",
                        "budget": {"seconds": 30}, "record": self.record}
        self.zipped("records.jsonl.gz", [self.record])
        self.zipped("frontier.jsonl.gz", [self.frontier])
        self.zipped("attempts.jsonl.gz", [self.attempt])
        self.zipped("packets.jsonl.gz", [{"graphs": [CODE], "id": "P1"}])
        for name in ("UNKNOWN.g6", "input.g6", "assigned.g6"):
            (self.bundle / name).write_text(CODE + "\n")
        for name, obj in (("run.json", {}), ("job.json", {"policy": "full"}), ("checker-report.json", {"status": "ACCEPT"})):
            packets.write(self.bundle / name, obj)
        self.refresh()

    def zipped(self, name, values):
        raw = "".join(packets.compact(v) + "\n" for v in values).encode()
        (self.bundle / name).write_bytes(gzip.compress(raw, mtime=0))

    def refresh(self):
        raw = gzip.decompress((self.bundle / "records.jsonl.gz").read_bytes())
        summary = {"completed": True, "checker_status": "ACCEPT", "counts": {"embedded": 0, "refuted": 0, "unknown": 1},
                   "records_sha256": hashlib.sha256(raw).hexdigest(),
                   "artifacts": {p.name: packets.sha(p) for p in self.bundle.iterdir() if p.name != "summary.json"}}
        packets.write(self.bundle / "summary.json", summary)

    def build(self, name="out", select=None):
        out = self.root / name
        result = packets.build([self.bundle], out, select=select)
        packet = packets.loads(next((out / "packets").glob("*/packet.json")).read_bytes()) if result["packets"] else None
        return out, result, packet

    def test_complete_history_missing_evidence_and_determinism(self):
        out, result, packet = self.build()
        self.assertEqual(result["packets"], 1)
        self.assertEqual(packet["failure_class"]["primary"], "no_separated_seed")
        self.assertIn("saved_proposals", packet["missing_evidence"])
        self.assertFalse(packet["numerical"]["available"])
        again, _, _ = self.build("again")
        self.assertEqual((out / "SHA256SUMS.json").read_bytes(), (again / "SHA256SUMS.json").read_bytes())
        for name, digest in packets.loads((out / "SHA256SUMS.json").read_bytes()).items():
            self.assertEqual(packets.sha(out / name), digest)

    def test_tampered_bundle_fails_before_publish(self):
        (self.bundle / "UNKNOWN.g6").write_text("")
        with self.assertRaisesRegex(ValueError, "bundle_hash:UNKNOWN"):
            self.build()
        self.assertFalse((self.root / "out").exists())

    def test_unknown_mismatch_fails_with_fresh_hashes(self):
        (self.bundle / "UNKNOWN.g6").write_text("")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "unknown_or_counts_mismatch"):
            self.build()

    def test_attempt_id_graph_mismatch(self):
        self.attempt["record"] = {**self.record, "g6": "I????????"}
        self.zipped("attempts.jsonl.gz", [self.attempt])
        self.refresh()
        with self.assertRaisesRegex(ValueError, "attempt_graph_id_mismatch"):
            self.build()

    def test_bad_tu_map(self):
        self.frontier["tu_closure"]["old_to_new"][0] = 1
        self.zipped("frontier.jsonl.gz", [self.frontier])
        self.refresh()
        with self.assertRaisesRegex(ValueError, "tu_permutation"):
            self.build()

    def test_saved_proposal_survives_as_unverified(self):
        proposed = {"g6": CODE, "verdict": "embedded", "cert": {"type": "exact", "field": {"minpoly": [0, 1]}, "coords": []}}
        self.attempt.update(record=proposed, outcome="PROPOSED", reason="checker:Deadline")
        self.zipped("attempts.jsonl.gz", [self.attempt])
        self.refresh()
        out, _, packet = self.build()
        row = packet["saved_proposals"]["records"][0]
        self.assertEqual(row["status"], "unverified proposal")
        path = next((out / "packets").iterdir()) / row["path"]
        self.assertEqual(packets.loads(path.read_bytes()), proposed)
        self.assertIn("checker_deadline", packet["failure_class"]["flags"])

    def test_deadline_does_not_change_no_seed_class(self):
        result = packets.classify([self.attempt, {"reason": "attempt_error:Deadline"}])
        self.assertEqual(result["primary"], "no_separated_seed")
        self.assertIn("attempt_deadline_unspecified", result["flags"])
        self.assertNotIn("checker_deadline", result["flags"])

    def test_control_command_does_not_import_f10_wrapper(self):
        code = "I????????"
        self.record["g6"] = code
        self.frontier.update(g6=code)
        self.frontier["tu_closure"].update(g6=code, old_to_new=list(range(10)))
        for name in ("UNKNOWN.g6", "input.g6", "assigned.g6"):
            (self.bundle / name).write_text(code + "\n")
        self.zipped("records.jsonl.gz", [self.record])
        self.zipped("frontier.jsonl.gz", [self.frontier])
        self.zipped("attempts.jsonl.gz", [self.attempt])
        self.zipped("packets.jsonl.gz", [{"graphs": [code]}])
        packets.write(self.bundle / "job.json", {"schema": "control51-v1", "forbidden_limit": 9})
        self.refresh()
        out, _, packet = self.build()
        directory = next((out / "packets").iterdir())
        self.assertEqual(packet["checker"]["pinned_command"], ["bash", "check.sh"])
        self.assertIn("gp10check.py", (directory / "check.sh").read_text())
        self.assertNotIn("gp11check.py", (directory / "check.sh").read_text())
        self.assertNotIn("forbidden-398", (directory / "CHECKER_SHA256SUMS").read_text())

    def test_geometry_labels_and_conditional_identities(self):
        value = packets.geometry(4, [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)])
        self.assertEqual(value["triangles"], [[0, 1, 2], [1, 2, 3]])
        self.assertEqual(value["rhombi"][0]["opposite_pairs"], [[0, 3], [1, 2]])

    def test_select_unknown_only(self):
        select = self.root / "select.g6"
        select.write_text("")
        _, result, _ = self.build(select=select)
        self.assertEqual(result["packets"], 0)
        select.write_text("I????????\n")
        with self.assertRaisesRegex(ValueError, "selected_graph_not_unknown"):
            self.build("missing", select)

    def test_noncanonical_and_traversal(self):
        with self.assertRaisesRegex(ValueError, "noncanonical_graph6"):
            packets.canonical(["J_?????????"], Path("/usr/bin/nauty-labelg"))
        with self.assertRaisesRegex(ValueError, "unsafe_artifact"):
            packets.safe_file(self.bundle, "../outside")

    def test_duplicate_and_nonfinite_json(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'):
            with self.assertRaises(ValueError):
                packets.loads(raw)


if __name__ == "__main__":
    unittest.main()
