#!/usr/bin/env python3
"""Crash/resume controls; replay real certificates with the frozen sample CLI."""
from __future__ import annotations

from argparse import Namespace
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import extend
import extend_run


class StreamingTests(unittest.TestCase):
    def test_crash_resume_coverage_and_tamper_detection(self):
        archive = extend.HERE / "results/extension/architect-500/records.jsonl.gz"
        records = []
        with gzip.open(archive, "rt") as stream:
            for line in stream:
                record = json.loads(line)
                if record["verdict"] == "embedded":
                    records.append(record)
                    if len(records) == 2:
                        break
        self.assertEqual(len(records), 2)
        records.sort(key=lambda item: item["g6"])
        calls = []

        class SimulatedExtender:
            def __init__(self, *args):
                pass

            def run(self, code):
                calls.append(code)
                if len(calls) == 2:
                    raise SystemExit("simulated worker death")
                record = next(copy.deepcopy(r) for r in records if r["g6"] == code)
                return record, {"g6": code, "seconds": 0.0, "verdict": record["verdict"]}

            def unknown(self, code, reason):
                return {"g6": code, "verdict": "unknown", "cert": {"reason": reason, "budget": {}}}

        with tempfile.TemporaryDirectory(prefix="gp11-stream-test-", dir="/tmp") as temporary:
            root = Path(temporary)
            source = root / "source.g6"
            source.write_text("".join(r["g6"] + "\n" for r in records))
            args = Namespace(input=source, output=root / "out", scratch=root / "scratch",
                             seconds=3.0, attempt_seconds=1.0, degree_cap=256,
                             shard_count=1, shard_index=0, resume=False)
            with patch.object(extend, "EmbeddingIndex", return_value=None), \
                    patch.object(extend, "load_checker", return_value=None), \
                    patch.object(extend, "Extender", SimulatedExtender):
                with self.assertRaisesRegex(SystemExit, "simulated worker death"):
                    extend_run.run(extend, args)
                self.assertEqual(json.loads((args.output / "pending.json").read_text())["g6"], records[1]["g6"])
                with (args.output / "journal.jsonl").open("a") as stream:
                    stream.write('{"record":')
                args.resume = True
                self.assertEqual(extend_run.run(extend, args), 0)
                # The interrupted graph gets a durable UNKNOWN; it is neither
                # skipped nor silently retried as if the crash had not happened.
                self.assertEqual(calls, [r["g6"] for r in records])
                with gzip.open(args.output / "records.jsonl.gz", "rt") as stream:
                    actual = [json.loads(line) for line in stream]
                self.assertEqual(actual[0], records[0])
                self.assertEqual(actual[1]["cert"]["reason"], "interrupted")
                summary = json.loads((args.output / "summary.json").read_text())
                self.assertEqual(summary["counts"], {"embedded": 1, "unknown": 1})
                self.assertEqual(summary["checker_status"], "ACCEPT")
                before = (args.output / "records.jsonl.gz").read_bytes()
                self.assertEqual(extend_run.run(extend, args), 0)
                self.assertEqual((args.output / "records.jsonl.gz").read_bytes(), before)
                args.seconds = 4
                with self.assertRaisesRegex(ValueError, "resume_config_or_source_changed"):
                    extend_run.run(extend, args)
                args.seconds = 3.0
                (args.output / "records.jsonl.gz").write_bytes(before + b"changed")
                with self.assertRaisesRegex(ValueError, "completed_artifact_changed"):
                    extend_run.run(extend, args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
