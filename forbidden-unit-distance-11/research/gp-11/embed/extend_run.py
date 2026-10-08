"""Durable streaming, sample replay, and compressed shards for extend.py."""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import gzip
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def input_codes(path):
    previous = None
    with Path(path).open("r", encoding="ascii") as stream:
        for raw in stream:
            if not raw.endswith("\n") or raw == "\n":
                raise ValueError("input_line_format")
            code = raw[:-1]
            if previous is not None and code <= previous:
                raise ValueError("input_not_sorted_unique")
            previous = code
            yield code


def recover_journal(path):
    """Only an incomplete last write may be discarded; complete corruption stops."""
    count = 0
    if not path.exists():
        return count
    with path.open("r+b") as stream:
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                return count
            if not line.endswith(b"\n"):
                stream.truncate(offset)
                return count
            entry = json.loads(line)
            if set(entry) != {"record", "stats"}:
                raise ValueError("journal_schema")
            if entry["record"]["g6"] != entry["stats"]["g6"]:
                raise ValueError("journal_graph_mismatch")
            count += 1


def append_entry(stream, api, record, stats):
    stream.write(api.compact({"record": record, "stats": stats}) + "\n")
    stream.flush()
    # The record and timing share one durable line, so resume never pairs a
    # certificate with another graph's timing after a partial append.
    os.fsync(stream.fileno())


def summarize(journal):
    counts = Counter({"embedded": 0, "unknown": 0})
    reasons = Counter()
    attempts = Counter()
    degree = Counter()
    durations = []
    check_seconds = 0.0
    cpu_seconds = 0.0
    nonbiconnected = Counter()
    with journal.open() as stream:
        for line in stream:
            entry = json.loads(line)
            record, stats = entry["record"], entry["stats"]
            counts[record["verdict"]] += 1
            durations.append(stats["seconds"])
            check_seconds += stats.get("check_seconds", 0)
            cpu_seconds += stats.get("cpu_seconds", 0)
            if record["verdict"] == "unknown":
                reasons[record["cert"]["reason"]] += 1
            if record["verdict"] == "embedded":
                degree[len(record["cert"]["field"]["minpoly"]) - 1] += 1
            rows = stats.get("attempts", [])
            attempts.update(row.get("reason", "interrupted_attempt") for row in rows)
            if any(row.get("reason") == "base_not_biconnected" for row in rows):
                nonbiconnected[record["verdict"]] += 1
    ordered = sorted(durations)

    def percentile(fraction):
        return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))] if ordered else 0

    return {"count": len(durations), "counts": dict(counts), "unknown_reasons": dict(reasons),
            "attempt_reasons": dict(attempts), "field_degrees": dict(degree),
            "graphs_with_attempted_nonbiconnected_base": dict(nonbiconnected),
            "graph_seconds": sum(durations), "graph_cpu_seconds": cpu_seconds,
            "online_check_seconds": check_seconds,
            "mean_seconds": sum(durations) / len(durations) if durations else 0,
            "median_seconds": percentile(0.5), "p95_seconds": percentile(0.95),
            "max_seconds": max(durations, default=0)}


def replay(api, directory, scratch, guard):
    """Run the frozen CLI, including framing, canonical labels, and coverage."""
    started = time.monotonic()
    cpu_started = api.cpu_seconds()
    with tempfile.TemporaryDirectory(prefix="replay-", dir=scratch) as temporary:
        run = Path(temporary)
        for name in ("input.g6", "UNKNOWN.g6", "run.json"):
            shutil.copyfile(directory / name, run / name)
        with gzip.open(directory / "records.jsonl.gz", "rb") as source:
            with (run / "records.jsonl").open("wb") as target:
                shutil.copyfileobj(source, target)
        with (run / "checker.log").open("w") as log:
            child = subprocess.Popen([sys.executable, "-B", str(api.CHECKER_PATH), str(run),
                                      "--output", str(run / "checked")], stdout=log, stderr=log)
            try:
                with guard.watch():
                    child.wait()
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
        report_path = run / "checked/report.json"
        shutil.copyfile(run / "checker.log", directory / "checker.log")
        if not report_path.exists():
            raise RuntimeError("frozen_checker_missing_report")
        report = json.loads(report_path.read_text())
        shutil.copyfile(report_path, directory / "checker-report.json")
        if child.returncode or report["status"] != "ACCEPT":
            raise RuntimeError("frozen_checker_rejected_run")
    return report, time.monotonic() - started, api.cpu_seconds() - cpu_started


def finalize(api, directory, scratch, guard, setup_seconds):
    journal = directory / "journal.jsonl"
    summary = summarize(journal)
    with (directory / "UNKNOWN.g6").open("w") as unknown:
        with (directory / "records.jsonl.gz.tmp").open("wb") as records_raw:
            with (directory / "timings.jsonl.gz.tmp").open("wb") as stats_raw:
                with gzip.GzipFile(fileobj=records_raw, mode="wb", filename="", mtime=0) as records:
                    with gzip.GzipFile(fileobj=stats_raw, mode="wb", filename="", mtime=0) as stats:
                        with journal.open() as stream:
                            for line in stream:
                                entry = json.loads(line)
                                record = entry["record"]
                                records.write((api.compact(record) + "\n").encode())
                                stats.write((api.compact(entry["stats"]) + "\n").encode())
                                if record["verdict"] == "unknown":
                                    unknown.write(record["g6"] + "\n")
    for name in ("records", "timings"):
        (directory / f"{name}.jsonl.gz.tmp").replace(directory / f"{name}.jsonl.gz")
    atomic_json(directory / "run.json", {"profile": "sample", "input": "input.g6",
                "input_sha256": api.digest(directory / "input.g6"), "records": ["records.jsonl"],
                "forbidden_limit": 0, "derive": False})
    report, seconds, replay_cpu = replay(api, directory, scratch, guard)
    if any(report["counts"].get(key, 0) != value for key, value in summary["counts"].items()):
        raise RuntimeError("checker_count_mismatch")
    summary.update({"completed": True, "checker_status": report["status"],
                    "checker_sha256": api.digest(api.CHECKER_PATH), "replay_seconds": seconds,
                    "replay_cpu_seconds": replay_cpu,
                    "setup_seconds": setup_seconds, "min_MemAvailable_kib": guard.minimum_kib,
                    "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "max_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                    "artifacts": {name: {"sha256": api.digest(directory / name),
                                         "bytes": (directory / name).stat().st_size}
                                  for name in ("input.g6", "UNKNOWN.g6", "records.jsonl.gz",
                                               "timings.jsonl.gz", "checker-report.json", "run.json")}})
    atomic_json(directory / "summary.json", summary)
    journal.unlink()
    print(api.compact(summary), flush=True)


def run(api, args):
    api.limits()
    started = time.monotonic()
    guard = api.Guard()
    guard.check()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # An advisory lock prevents two resumes from both appending the next graph.
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = {"source_sha256": api.digest(args.input), "shard_index": args.shard_index,
                  "shard_count": args.shard_count, "seconds": args.seconds, "degree_cap": args.degree_cap,
                  "attempt_seconds": args.attempt_seconds,
                  "memory_cap_bytes": api.MEMORY_CAP_BYTES, "memory_floor_kib": api.MEMORY_FLOOR_KIB,
                  "source_hashes": {p.name: api.digest(p) for p in (
                      api.HERE / "extend.py", api.HERE / "extend_run.py", api.HERE / "extension.gp",
                      api.HERE / "index.py", api.GP10 / "drive/graph6.py", api.CHECKER_PATH,
                      api.GP10 / "cloud/lean3/records.jsonl.gz", api.GP10 / "data/B10.g6")}}
        if (directory / "job.json").exists():
            if not args.resume:
                raise ValueError("output_exists_use_resume")
            if json.loads((directory / "job.json").read_text()) != config:
                raise ValueError("resume_config_or_source_changed")
        else:
            if any(p.name != ".lock" for p in directory.iterdir()):
                raise ValueError("output_directory_not_empty")
            atomic_json(directory / "job.json", config)
        if (directory / "summary.json").exists():
            summary = json.loads((directory / "summary.json").read_text())
            for name, receipt in summary["artifacts"].items():
                if api.digest(directory / name) != receipt["sha256"]:
                    raise ValueError("completed_artifact_changed:" + name)
            print(api.compact(summary), flush=True)
            return 0
        selected = directory / "input.g6.tmp"
        with selected.open("w", encoding="ascii") as target:
            for code in input_codes(args.input):
                if api.seed_for(code) % args.shard_count == args.shard_index:
                    target.write(code + "\n")
        if (directory / "input.g6").exists() and api.digest(selected) != api.digest(directory / "input.g6"):
            raise ValueError("resume_input_changed")
        selected.replace(directory / "input.g6")
        journal = directory / "journal.jsonl"
        completed = recover_journal(journal)
        codes = iter(input_codes(directory / "input.g6"))
        if completed:
            with journal.open() as stream:
                for line in stream:
                    if json.loads(line)["record"]["g6"] != next(codes, None):
                        raise ValueError("journal_not_input_prefix")
        args.scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="extend-", dir=args.scratch) as temporary:
            scratch = Path(temporary)
            with guard.watch():
                index = api.EmbeddingIndex()
                checker = api.load_checker()
            extender = api.Extender(index, checker, scratch, guard, args.seconds, args.degree_cap,
                                    args.attempt_seconds)
            setup_seconds = time.monotonic() - started
            pending_path = directory / "pending.json"
            pending = json.loads(pending_path.read_text()) if pending_path.exists() else None
            last_code = None
            if completed:
                with journal.open() as stream:
                    for line in stream:
                        last_code = json.loads(line)["record"]["g6"]
            if pending and pending["g6"] == last_code:
                pending = None
                pending_path.unlink()
            with journal.open("a", encoding="utf-8") as output:
                for code in codes:
                    guard.check()
                    if pending:
                        if pending["g6"] != code:
                            raise ValueError("pending_not_next_input")
                        record = extender.unknown(code, "interrupted")
                        stats = {"g6": code, "seed": api.seed_for(code), "seconds": 0.0,
                                 "reason": "interrupted", "verdict": "unknown", "attempts": []}
                        pending = None
                    else:
                        atomic_json(pending_path, {"g6": code})
                        record, stats = extender.run(code)
                    append_entry(output, api, record, stats)
                    pending_path.unlink(missing_ok=True)
                    completed += 1
                    if completed % 100 == 0:
                        print(f"completed={completed} last={code} verdict={record['verdict']}", file=sys.stderr, flush=True)
                    if stats.get("stop"):
                        atomic_json(directory / "STOP.json", stats)
                        return 75
            (directory / "STOP.json").unlink(missing_ok=True)
            del index, extender
            finalize(api, directory, args.scratch, guard, setup_seconds)
    return 0


def main(api, argv=None):
    parser = argparse.ArgumentParser(description=api.__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/gp11-extend"))
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--degree-cap", type=int, default=256)
    parser.add_argument("--attempt-seconds", type=float, default=1.0)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if not all(math.isfinite(v) and v > 0 for v in (args.seconds, args.attempt_seconds)):
        parser.error("finite positive graph and attempt seconds required")
    if not 1 <= args.degree_cap <= 256:
        parser.error("degree cap in 1..256 required")
    if not 0 <= args.shard_index < args.shard_count:
        parser.error("require 0 <= shard-index < shard-count")
    if args.scratch.resolve().is_relative_to(api.HERE.parent.parent.parent):
        parser.error("scratch must be outside the repository")

    def interrupted(*_):
        raise api.Interrupted("signal")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        return run(api, args)
    except (api.MemoryFloor, api.Interrupted) as exc:
        print(f"STOP: {exc}; resume the same output directory", file=sys.stderr)
        return 75
