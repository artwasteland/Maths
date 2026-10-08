"""Red and green fixtures for gate_paths.py (G5 follow-up 0020, MINOR-2) and for the pinned checker's CLI exit status
(0020 NOTE: B11 9 had no red fixture). Neither touches a pinned file: the writer and the self-test stay at their
reviewed hashes. Run: python -m unittest test_gate_paths (from research/gp-11/tools)."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "check"))
import gate_paths  # noqa: E402
import gp11check as ck  # noqa: E402


class GatePaths(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gate-paths-"))
        self.run_dir = self.tmp / "run"
        self.run_dir.mkdir()
        (self.run_dir / "evidence.txt").write_text("inside\n")
        (self.tmp / "outside.txt").write_text("inside\n")  # same bytes: only containment can tell them apart

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def gates(self, path):
        gates = {f"G{i}": {"status": "PASS", "evidence": [{"path": "evidence.txt", "sha256": "x"}]} for i in range(6)}
        gates["G3"]["evidence"] = [{"path": path, "sha256": "x"}]
        return gates

    def test_relative_inside_passes(self):
        self.assertEqual(gate_paths.uncontained(self.gates("evidence.txt"), self.run_dir), [])
        self.assertEqual(gate_paths.uncontained(self.gates("./sub/../evidence.txt"), self.run_dir), [])

    def test_escaping_paths_are_refused(self):
        for path in ("../outside.txt", str(self.tmp / "outside.txt"), "", None):
            with self.subTest(path=path):
                self.assertEqual(gate_paths.uncontained(self.gates(path), self.run_dir), [("G3", path)])

    def test_symlink_out_of_run_is_refused(self):
        os.symlink(self.tmp / "outside.txt", self.run_dir / "link.txt")
        self.assertEqual(gate_paths.uncontained(self.gates("link.txt"), self.run_dir), [("G3", "link.txt")])

    def test_missing_evidence_fails_closed(self):
        gates = self.gates("evidence.txt")
        gates["G4"]["evidence"] = []
        gates["G5"] = "PASS"
        self.assertEqual(gate_paths.uncontained(gates, self.run_dir), [("G4", None), ("G5", None)])

    def test_cli_exit_status(self):
        path = self.tmp / "gates.json"
        for gate_path, code in (("evidence.txt", 0), ("../outside.txt", 1)):
            with self.subTest(path=gate_path):
                path.write_text(json.dumps(self.gates(gate_path)))
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(gate_paths.main([str(self.run_dir), str(path)]), code)
                self.assertIn("PASS" if code == 0 else "REJECT G3", out.getvalue())


class CheckerCli(unittest.TestCase):
    """B11 9: the pinned CLI's exit status follows the report's verdict; --require-complete-b10 is enforced."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gp11-cli-"))
        self.run_dir = self.tmp / "named11"
        shutil.copytree(HERE.parent / "check/fixtures/named11", self.run_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = ck.main([str(self.run_dir), *args])
        return code, out.getvalue(), ck.read_json(self.run_dir / "checked/report.json")["status"]

    def test_accepted_run_exits_zero(self):
        code, _, status = self.cli()
        self.assertEqual((code, status), (0, "ACCEPT"))

    def test_complete_b10_required_of_a_run_without_one(self):
        code, out, status = self.cli("--require-complete-b10")
        self.assertEqual((code, status), (1, "ACCEPT"))
        self.assertIn("REJECT B10", out)

    def test_rejected_run_exits_one(self):
        provenance = ck.read_json(self.run_dir / "provenance.json")
        provenance[next(iter(provenance))]["method"] = "coordinate-lookup"
        ck.json_write(self.run_dir / "provenance.json", provenance)
        code, _, status = self.cli()
        self.assertEqual((code, status), (1, "REJECT"))


if __name__ == "__main__":
    unittest.main()
