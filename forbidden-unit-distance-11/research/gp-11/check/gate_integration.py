#!/usr/bin/env python3
"""Exercise B11's actual execute path before the full freeze/control run exists.

Only the freeze directory and its source-report plumbing are redirected to a
temporary fixture. No checker/control method is replaced. A one-field profile
mutation must hit controls_required, before the later census-size check.
"""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
import gp11check as ck


def main():  # B11 integration test addition.
    sources = ck.source_hashes()
    record = ck.read_json(ck.HERE / "fixtures/lattice11.json")
    with tempfile.TemporaryDirectory(prefix="gp11-gate-integration-") as tmp:
        root = Path(tmp)
        run = root / "run"
        frozen = root / "freeze/data"
        run.mkdir()
        frozen.mkdir(parents=True)
        (run / "input.g6").write_text(record["g6"] + "\n")
        (run / "records.jsonl").write_text(ck.json.dumps(record) + "\n")
        (run / "UNKNOWN.g6").write_text("")
        sha = ck.digest(run / "input.g6")
        (frozen / "B11.g6").write_bytes((run / "input.g6").read_bytes())
        (frozen / "SHA256SUMS").write_text(sha + "  B11.g6\n")
        manifest = {"profile": "fixture11", "input": "input.g6", "input_sha256": sha, "records": ["records.jsonl"]}
        ck.json_write(run / "run.json", manifest)
        with patch.object(ck, "GP11", frozen.parent), patch.object(ck, "source_hashes", return_value=sources):
            positive = ck.Run(run, b11_sha256=sha, emit=lambda _: None).execute()
            assert positive["status"] == "ACCEPT", positive
            print("PASS integration positive: ACCEPT exact eleven-vertex fixture")
            ck.json_write(run / "run.json", {**manifest, "profile": "B11"})
            for label, pin, expected in (("controls invoked by B11", sha, "controls_required"),
                                         ("wrong external digest", "0" * 64, "frozen_input_hash"),
                                         ("missing external digest", None, "b11_hash_required")):
                result = ck.Run(run, b11_sha256=pin, emit=lambda _: None).execute()
                assert result["status"] == "REJECT" and result["reason"] == expected, result
                print(f"PASS integration {label}: REJECT {expected}")
            ck.json_write(run / "run.json", manifest)
            restored = ck.Run(run, b11_sha256=sha, emit=lambda _: None).execute()
            assert restored["status"] == "ACCEPT" and restored["counts"] == positive["counts"], restored
            print("PASS integration originals restored: same ACCEPT and counts")
    print("B11 GATE INTEGRATION PASS")


if __name__ == "__main__":
    main()
