#!/usr/bin/env python3
"""Replay full checker commands in-process, leaving room for one nauty child."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import shutil
import sys
import time
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
from runner import load_checker
HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
SCRATCH = Path("/tmp/gp10-checkaudit")
CHECKER = HERE.parent / "check/gp10check.py"


def deadline(signum, frame):
    raise TimeoutError("audit per-case deadline")


def mutation_check(spec):
    if not spec["parent"]:
        return
    a = CASES / spec["parent"]
    b = CASES / spec["name"]
    mut = spec["mutation"]
    if mut["scope"] in ("record", "polynomial"):
        original = json.loads((a / mut["file"]).read_text())
        changed = json.loads((b / mut["file"]).read_text())
        recreated = copy.deepcopy(original)
        x, y = recreated, changed
        for key in mut["path"][:-1]:
            x, y = x[key], y[key]
        x[mut["path"][-1]] = copy.deepcopy(y[mut["path"][-1]])
        assert json.dumps(recreated, sort_keys=True) == json.dumps(changed, sort_keys=True), spec["name"]
        assert json.dumps(original, sort_keys=True) != json.dumps(changed, sort_keys=True), spec["name"]
    else:
        inputs = {p.name for p in a.iterdir() if p.is_file() and p.suffix in (".g6", ".json", ".jsonl") and not p.name.startswith("observed")}
        other = {p.name for p in b.iterdir() if p.is_file() and p.suffix in (".g6", ".json", ".jsonl") and not p.name.startswith("observed")}
        assert inputs == other, (spec["name"], inputs, other)
        changed = sorted(p for p in inputs if (a / p).read_bytes() != (b / p).read_bytes())
        assert changed == [mut["file"]], (spec["name"], changed)


def execute(ck, spec):
    path = CASES / spec["name"]
    for old in path.glob("observed*"):
        if old.is_file():
            old.unlink()
    if spec["kind"] == "sturm":
        poly = json.loads((path / "polynomial.json").read_text())
        try:
            count = ck.sturm_real_roots(poly)
            stdout = "RETURN sturm_real_roots " + str(count) + "\n"
            reason = "returned"
        except ck.Rejection as exc:
            count = None
            stdout = "REJECT helper " + str(exc) + "\n"
            reason = exc.reason
        (path / "observed.stdout").write_text(stdout)
        return {**spec, "passed": count == spec["count"] and reason == spec["reason"], "stdout": stdout,
                "observed_status": "ACCEPT" if count == 0 else "REJECT", "observed_count": count,
                "observed_reason": reason, "error": None, "returncode": None,
                "in_process_command": "gp10check.sturm_real_roots(" + repr(poly) + ")"}
    output = SCRATCH / "results" / spec["name"]
    if output.exists():
        shutil.rmtree(output)
    argv = [str(path), "--output", str(output)]
    captured = io.StringIO()
    started = time.monotonic()
    error = None
    returncode = None
    signal.alarm(45)
    try:
        with contextlib.redirect_stdout(captured):
            returncode = ck.main(argv)
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
    finally:
        signal.alarm(0)
    stdout = captured.getvalue()
    report = json.loads((output / "report.json").read_text()) if (output / "report.json").exists() else {}
    logs = [json.loads(s) for s in (output / "records.jsonl").read_text().splitlines()] if (output / "records.jsonl").exists() else []
    reasons = [r["reason"].split(":", 1)[0] for r in logs if r["status"] == "REJECT"]
    passed = error is None and report.get("status") == spec["status"] and report.get("reason") == spec["reason"]
    passed = passed and returncode == (0 if spec["status"] == "ACCEPT" else 1)
    if spec["record_reason"]:
        passed = passed and spec["record_reason"] in reasons
    if spec.get("record_detail"):
        passed = passed and spec["record_detail"] in [r["reason"] for r in logs if r["status"] == "REJECT"]
    expected_final = spec["status"] + " run " + spec["reason"]
    passed = passed and bool(stdout.splitlines()) and stdout.splitlines()[-1] == expected_final
    (path / "observed.stdout").write_text(stdout)
    (path / "observed-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (path / "observed-records.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in logs))
    for name in ("minimal.g6", "minimality.jsonl", "unknown-budgets.jsonl"):
        product = output / name
        if product.exists():
            (path / ("observed-" + name)).write_bytes(product.read_bytes())
    result = {**spec, "passed": bool(passed), "stdout": stdout, "returncode": returncode,
              "observed_status": report.get("status"), "observed_reason": report.get("reason"),
              "observed_record_reasons": reasons, "error": error, "elapsed_seconds": time.monotonic() - started,
              "in_process_command": [str(CHECKER), *argv], "report": str(path / "observed-report.json")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--all", action="store_true")
    choice.add_argument("--case")
    args = parser.parse_args()
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 15, "run under nice -n 15"
    assert 0 < resource.getrlimit(resource.RLIMIT_AS)[0] <= 1024000000, "set ulimit -v 1000000"
    signal.signal(signal.SIGALRM, deadline)
    index = json.loads((CASES / "index.json").read_text())
    if args.all:
        parents = {s["parent"] for s in index if s["parent"]}
        assert all(s["name"] in parents for s in index if s["status"] == "ACCEPT"), "unpaired positive control"
    by_name = {s["name"]: s for s in index}
    selected = index if args.all else [by_name[args.case]]
    if not args.all and selected[0]["parent"]:
        selected = [by_name[selected[0]["parent"]], *selected]
    ck = load_checker()
    before = ck.digest(CHECKER)
    started = time.monotonic()
    results = []
    seen = {}
    for spec in selected:
        mutation_check(spec)
        result = execute(ck, spec)
        if spec["parent"]:
            assert seen[spec["parent"]]["passed"] and seen[spec["parent"]]["observed_status"] == "ACCEPT", spec["parent"]
        seen[spec["name"]] = result
        results.append(result)
        if not args.all:
            print("CASE " + spec["name"])
            print(result["stdout"], end="")
        if not result["passed"]:
            print("MISMATCH " + spec["name"] + " " + json.dumps(result, sort_keys=True), flush=True)
    assert before == ck.digest(CHECKER), "checker changed during audit"
    summary = {"total": len(results), "full_runs": sum(r["kind"] == "run" for r in results), "sturm_helpers": sum(r["kind"] == "sturm" for r in results), "matched": sum(r["passed"] for r in results),
               "expected_accept": sum(r["status"] == "ACCEPT" for r in results),
               "expected_reject": sum(r["status"] == "REJECT" for r in results),
               "false_accepts": [r["name"] for r in results if r["status"] == "REJECT" and r["observed_status"] == "ACCEPT"],
               "mismatches": [r["name"] for r in results if not r["passed"]],
               "paired_mutations": sum(r["parent"] is not None for r in results),
               "elapsed_seconds": time.monotonic() - started, "checker_sha256": before,
               "kernel_sha256": ck.digest(ck.TRUSTED / "check/udcheck.py"), "environment": ck.environment(),
               "address_space_bytes": resource.getrlimit(resource.RLIMIT_AS)[0]}
    if args.all:
        (CASES / "results.json").write_text(json.dumps({"summary": summary, "cases": results}, indent=2, sort_keys=True) + "\n")
    print("AUDIT " + json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary["matched"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
