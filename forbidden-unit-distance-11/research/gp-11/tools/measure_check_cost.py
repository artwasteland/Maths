#!/usr/bin/env python3
"""Time isolated certificates without changing the frozen checker.

Default: a complete sample/fixture11 replay, in a complete source checkout.
--exact-only: time only the frozen E-exact arithmetic (also usable in the slim
snapshot). This is NOT a run ACCEPT or a completeness check. Each source must
contain exactly one self-contained record. All writes go below --out.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research/gp-10/check/gp10check.py"
PROFILE = ROOT / "research/gp-11/check/gp11check.py"
PIN = "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(path):
    spec = importlib.util.spec_from_file_location("cost_checker", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def worker(run, exact_only):
    if sha(BASE) != PIN:
        raise ValueError("frozen_checker_hash")
    started = time.monotonic()
    checker = load(BASE if exact_only else PROFILE)
    base = checker if exact_only else checker.base
    # Operational relocation only: the proof routines and source bytes stay
    # unchanged. Record this explicitly; TMPDIR alone cannot override SCRATCH.
    scratch = run / "scratch"
    scratch.mkdir()
    base.SCRATCH = scratch
    os.environ.update(TMPDIR=str(scratch), SQLITE_TMPDIR=str(scratch))
    tempfile.tempdir = str(scratch)
    rows = list(base.lines(run / "records.jsonl"))
    if len(rows) != 1:
        raise ValueError("one_record_required")
    record = base.loads(rows[0][-1])
    base.keys(record, {"g6", "verdict", "cert"})
    base.check_canonical([record["g6"]])
    graph = base.decode(record["g6"])
    cert = record["cert"]
    result = {"g6": record["g6"], "bytes": (run / "records.jsonl").stat().st_size,
              "checker_sha256": sha(BASE), "profile_sha256": sha(PROFILE),
              "scratch_relocation": str(scratch), "certificate_sha256": sha(run / "records.jsonl"),
              "environment": base.environment(), "certificate_type": cert.get("type"),
              "field_degree": len(cert.get("field", {}).get("minpoly", [])) - 1}
    verification_started = time.monotonic()
    if exact_only:
        if record["verdict"] != "embedded" or cert.get("type") != "exact":
            raise ValueError("exact_embedding_required")
        result.update(scope="E-exact arithmetic only; NOT a run ACCEPT", status="ARITHMETIC_PASS",
                      details=base.exact_embedding(graph, cert))
    else:
        (run / "input.g6").write_text(record["g6"] + "\n")
        (run / "UNKNOWN.g6").write_text("")
        manifest = {"profile": "fixture11" if graph.n == 11 else "sample", "input": "input.g6",
                    "input_sha256": sha(run / "input.g6"), "records": ["records.jsonl"],
                    "unknown": "UNKNOWN.g6", "derive": False, "forbidden_limit": 10 if graph.n == 11 else 9}
        write(run / "run.json", manifest)
        report = checker.Run(run).execute()
        result.update(scope="one-record frozen run; NOT B10/B11 completeness", status=report["status"],
                      report_sha256=sha(run / "checked/report.json"), reason=report.get("reason"))
        if report["status"] != "ACCEPT" or report.get("direct_rejections") != 0:
            write(run / "cost.json", result)
            return 1
    result.update(verification_seconds=time.monotonic() - verification_started,
                  worker_seconds=time.monotonic() - started,
                  peak_self_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    write(run / "cost.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="*", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seconds", type=float, default=900)
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker.resolve(), args.exact_only)
    if not args.out or not args.records or args.seconds <= 0:
        parser.error("--out, certificate files and positive --seconds required")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for i, source in enumerate(args.records):
        run = out / f"case-{i:03d}"
        run.mkdir()
        # Bounded read even if an entire population stream was supplied by mistake.
        with source.open("rb") as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024 or raw.count(b"\n") != 1 or not raw.endswith(b"\n"):
            raise ValueError("one_record_at_most_8_MiB_required:" + str(source))
        (run / "records.jsonl").write_bytes(raw)
        command = [sys.executable, "-B", str(ROOT / "research/gp-11/tools/guard.py"), "--",
                   sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(run)]
        if args.exact_only:
            command.append("--exact-only")
        started = time.monotonic()
        with (run / "check.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=args.seconds)
            except subprocess.TimeoutExpired:
                # guard.py starts its worker as a new session; terminating the
                # guard lets its finally block reap that session.
                process.send_signal(signal.SIGINT)
                code = process.wait()
                code = 124
        row = {"source": str(source.resolve()), "command": command, "exit": code,
               "wall_seconds": time.monotonic() - started, "timeout_seconds": args.seconds,
               "timed_out": code == 124}
        if (run / "cost.json").exists():
            row.update(json.loads((run / "cost.json").read_text()))
        results.append(row)
        write(out / "measurements.json", results)
        print(json.dumps(row, sort_keys=True), flush=True)
    return int(any(row["exit"] for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
