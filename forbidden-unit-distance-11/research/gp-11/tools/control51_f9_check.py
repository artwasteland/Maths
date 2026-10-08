#!/usr/bin/env python3
"""One-record F9 check for a blinded workspace. No producer is imported."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
LIMIT = 8 * 1024 * 1024
FLOOR = 1572864
PINS = {
    "research/gp-10/check/gp10check.py": "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04",
    "research/unit-distance-22/check/udcheck.py": "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de",
    "research/unit-distance-22/data/forbidden-74.json": "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
    "research/unit-distance-22/data/tu-gadgets.json": "a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629",
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def regular(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "regular_unlinked_file_required:" + str(path))


def loads(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def bad(value):
        raise ValueError("nonfinite_json:" + value)

    def floating(value):
        answer = float(value)
        require(math.isfinite(answer), "nonfinite_json:" + value)
        return answer

    return json.loads(raw, object_pairs_hook=unique, parse_constant=bad, parse_float=floating)


def record_bytes(path, graph):
    regular(path)
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT and raw.endswith(b"\n") and raw.count(b"\n") == 1, "one_record_within_8_MiB_required")
    row = loads(raw)
    require(set(row) == {"g6", "verdict", "cert"} and row["g6"] == graph, "assigned_graph_record_required")
    cert = row["cert"]
    require(isinstance(cert, dict), "certificate_object_required")
    kind = cert.get("type")
    if row["verdict"] == "embedded":
        require(kind == "exact", "self_contained_exact_required")
    else:
        require(row["verdict"] == "refuted" and kind in ("tree", "null", "real", "null-dag", "real-dag", "sub", "tu"), "self_contained_refutation_required")
        if kind == "sub":
            require(type(cert.get("index")) is int and 0 <= cert["index"] < 74, "indexed_F9_required")
        if kind == "tu":
            end = cert.get("end", {})
            require(set(end) == {"forbidden", "map"} and type(end["forbidden"]) is int and 0 <= end["forbidden"] < 74, "self_contained_F9_TU_end_required")
    return raw, row


def accepted_report(report, code, record_sha, verdict):
    expected_counts = {"embedded": int(verdict == "embedded"), "refuted": int(verdict == "refuted"), "unknown": 0}
    require(report.get("status") == "ACCEPT" and report.get("reason") == "verified", "checker_not_accepted")
    require(report.get("profile") == "sample" and report.get("forbidden_limit") == 9, "F9_sample_required")
    require(report.get("input_count") == 1 and report.get("counts") == expected_counts, "checker_counts")
    require(report.get("input_sha256") == hashlib.sha256((code + "\n").encode()).hexdigest(), "checker_input_hash")
    require(report.get("direct_rejections") == 0 and report.get("conditional") is False and report.get("conditional_minimal") == [], "checker_incomplete")
    require(report.get("checker_sha256") == PINS["research/gp-10/check/gp10check.py"] and
            report.get("kernel_sha256") == PINS["research/unit-distance-22/check/udcheck.py"], "checker_source_hash")
    require(report.get("trusted_data_sha256") == {Path(k).name: v for k, v in PINS.items() if "/data/" in k}, "checker_data_hash")
    files = report.get("files", [])
    require(len(files) == 1 and files[0].get("sha256") == record_sha and files[0].get("hosts") is False, "checker_consumed_record_hash")


def available():
    return int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")))


def limits():
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (1024000000, 1024000000))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=900)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    os.chdir(root)
    started = time.monotonic()
    result = {"status": "UNRESOLVED", "scope": "independent one-record F9 replay"}
    child = None
    try:
        require(args.seconds > 0, "positive_check_budget_required")
        for name, pin in PINS.items():
            regular(root / name)
            require(sha(root / name) == pin, "frozen_source_hash:" + name)
        packet = loads((root / "packet.json").read_bytes())
        graph = packet["graph"]["g6"]
        # New checker outputs only; a malformed replacement cannot reuse an old ACCEPT.
        require((root / "check").is_dir() and not (root / "check").is_symlink(), "check_directory")
        for name in ("check.log", "check-result.json"):
            if (root / name).exists() or (root / name).is_symlink():
                regular(root / name)
        checked = root / "check/checked"
        if checked.exists():
            require(checked.is_dir() and not checked.is_symlink(), "checked_directory")
            for path in checked.iterdir():
                regular(path)
                path.unlink()
        for name in ("input.g6", "UNKNOWN.g6", "run.json"):
            regular(root / "check" / name)
        require((root / "check/input.g6").read_text() == graph + "\n" and (root / "check/UNKNOWN.g6").read_bytes() == b"", "check_input")
        expected = {"profile": "sample", "input": "input.g6", "input_sha256": hashlib.sha256((graph + "\n").encode()).hexdigest(),
                    "records": ["records.jsonl"], "unknown": "UNKNOWN.g6", "forbidden_limit": 9, "derive": False}
        require(loads((root / "check/run.json").read_bytes()) == expected, "check_manifest")
        raw, row = record_bytes(root / "record.jsonl", graph)
        target = root / "check/records.jsonl"
        if target.exists() or target.is_symlink():
            regular(target)
        target.write_bytes(raw)
        result.update(g6=graph, record_sha256=hashlib.sha256(raw).hexdigest(), verdict=row["verdict"],
                      bytes=len(raw), field_degree=len(row["cert"].get("field", {}).get("minpoly", [])) - 1)
        minimum = available()
        require(minimum >= FLOOR, "memory_floor")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", SYMPY_GROUND_TYPES="python")
        env.update({name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        with (root / "check.log").open("w") as log:
            child = subprocess.Popen([sys.executable, "-B", str(root / "research/gp-10/check/gp10check.py"), "check"],
                                     stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True, preexec_fn=limits)
            while child.poll() is None:
                minimum = min(minimum, available())
                if minimum < FLOOR or time.monotonic() - started > args.seconds:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    raise ValueError("memory_floor" if minimum < FLOOR else "checker_timeout")
                time.sleep(0.25)
        result.update(checker_exit=child.returncode, min_available_kib=minimum)
        require(child.returncode == 0, "checker_exit:" + str(child.returncode))
        require("ACCEPT run verified" in (root / "check.log").read_text().splitlines(), "checker_accept_line_missing")
        report = loads((checked / "report.json").read_bytes())
        accepted_report(report, graph, result["record_sha256"], row["verdict"])
        require(sha(target) == result["record_sha256"] and sha(root / "record.jsonl") == result["record_sha256"], "record_changed_during_check")
        result.update(status="ACCEPTED", reason="verified", report_sha256=sha(checked / "report.json"),
                      check_log_sha256=sha(root / "check.log"))
    except (OSError, ValueError, TypeError, KeyError, MemoryError) as exc:
        result.update(reason=str(exc))
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    result.update(wall_seconds=time.monotonic() - started,
                  peak_checker_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (root / "check-result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("ACCEPT run verified" if result["status"] == "ACCEPTED" else "UNRESOLVED " + result["reason"], flush=True)
    return int(result["status"] != "ACCEPTED")


if __name__ == "__main__":
    raise SystemExit(main())
