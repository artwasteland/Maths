#!/usr/bin/env python3
"""Fail-closed receipt guards; git calls are simulated, never executed by this test."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import worker


def main():
    record = {"target": [24, 69], "seed_n": 10, "slice": [12, 1, 1920], "certs_replayed": 70,
              "pruned_cells_inspected": 70, "pinned": {"target": [24, 69], "seed": 10, "slices": [12, 1920]}}
    partial = "CHAIN PARTIAL (levels below 13 not inspected (--from-n 13))"
    clean = json.dumps(record) + "\nCOVERAGE partial: levels below 13 not inspected (--from-n 13)\n" + partial + "\n"
    assert worker.check_accept(clean, 3, 1, False) == []
    want = "CHECK: expected exit 3 and exactly " + partial + ", without PROBLEM"
    for text, code in ((clean, 137), (clean.replace(partial, partial[:-1] + "; no --check)"), 3),
                       (clean + "PROBLEM: planted\n", 3), (clean + partial + "\n", 3)):
        assert want in worker.check_accept(text, code, 1, False)
        print("WORKER SELF-TEST red: FAIL:", want)
        assert worker.check_accept(clean, 3, 1, False) == []
    broken = dict(record, certs_replayed=69)
    text = clean.replace(json.dumps(record), json.dumps(broken))
    want = "CHECK: certificates not all replayed, or wrong target, seed, slice or pins"
    assert want in worker.check_accept(text, 3, 1, False)
    print("WORKER SELF-TEST red: FAIL:", want)
    assert worker.check_accept(clean, 3, 1, False) == []
    with tempfile.TemporaryDirectory(prefix="u24-worker-red-") as tmp:
        root = Path(tmp)
        first, later = root / "first", root / "later"
        first.mkdir()
        later.mkdir()
        for d in (first, later):
            (d / "12-20.g6").write_bytes(b"K??????????\n")
        assert worker.prefix_diff(first, later) == "identical, file for file (1 files)"
        (later / "12-20.g6").write_bytes(b"K?????????@\n")
        try:
            worker.prefix_diff(first, later)
        except ValueError as error:
            assert str(error) == "PREFIX: differs: 12-20.g6"
            print("WORKER SELF-TEST red: FAIL:", error)
        else:
            raise AssertionError("different prefix accepted")
        (later / "12-20.g6").write_bytes((first / "12-20.g6").read_bytes())
        assert worker.prefix_diff(first, later) == "identical, file for file (1 files)"
        try:
            worker.prefix_diff(root / "missing", later)
        except FileNotFoundError:
            print("WORKER SELF-TEST: comparison exception propagates, never counts as identical")
        else:
            raise AssertionError("missing comparison directory accepted")
        result = root / "result"
        result.mkdir()
        cert = result / "24-69.certs.jsonl"
        cert.write_bytes(b"checked certificate\n")
        retained = {cert.name: worker.sha(cert)}
        with patch.object(worker, "ROOT", root), patch.object(worker, "git", lambda *args: "commit"), \
                patch.object(worker.subprocess, "check_output", return_value=b"damaged committed certificate\n"):
            try:
                worker.committed_result(result, retained)
            except ValueError as error:
                assert str(error) == "RESULT BINDING: committed 24-69.certs.jsonl differs from checked result"
                print("WORKER SELF-TEST red: FAIL:", error)
            else:
                raise AssertionError("different committed result accepted")
        with patch.object(worker, "ROOT", root), patch.object(worker, "git", lambda *args: "commit"), \
                patch.object(worker.subprocess, "check_output", return_value=cert.read_bytes()):
            assert worker.committed_result(result, retained) == "commit"
        # Count actual attempted push commands and delays, including a third-try success.
        for statuses, expected in (([1, 1, 1], False), ([1, 1, 0], True)):
            calls, sleeps = [], []
            remaining = iter(statuses)

            def fake_run(args, **kwargs):
                calls.append(args)
                code = next(remaining) if args[1] == "push" else 1 if args[1] == "diff" else 0
                if kwargs.get("check") and code:
                    raise subprocess.CalledProcessError(code, args)
                return SimpleNamespace(returncode=code)

            with patch.object(worker.subprocess, "run", fake_run), patch.object(worker.time, "sleep", sleeps.append):
                assert worker.push_receipt([root / "receipt.txt"], "test") is expected
            assert sum(c[1] == "push" for c in calls) == 3 and sleeps == [30, 30]
            assert "--only" in next(c for c in calls if c[1] == "commit")
            print(f"WORKER SELF-TEST: simulated pushes {statuses}, accepted {expected}, delays {sleeps}")
        with patch.dict(worker.os.environ, {"U24_MIN_AVAILABLE_MB": "1536"}), patch.object(worker, "available_mb", lambda: 1000):
            stopped = worker.measured([sys.executable, "-c", "raise AssertionError('must not start')"], root / "memory.log")
        want = "MEMORY STOP: MemAvailable below 1536 MiB before starting\n"
        assert stopped["exit"] == 137 and (root / "memory.log").read_text() == want
        print("WORKER SELF-TEST red: FAIL:", want.strip())
        with patch.dict(worker.os.environ, {"U24_MIN_AVAILABLE_MB": "0"}), patch.object(worker.os, "access", lambda *_: False):
            sampled = worker.measured([sys.executable, "-c", "import time; a=bytearray(32*1024*1024); time.sleep(0.6)"],
                                      root / "sampler.log", timed=True)
        assert sampled["exit"] == 0 and sampled["peak_rss_kib"] >= 32768, sampled
        assert sampled["peak_method"] == "process-group RSS sampler (250 ms)"
        print("WORKER SELF-TEST: fallback sampler peak", sampled["peak_rss_kib"], "KiB; clean command passed after memory control")
    print("WORKER SELF-TEST OK: acceptance, comparison errors and three-attempt push guards")


if __name__ == "__main__":
    main()
