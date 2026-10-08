#!/usr/bin/env python3
"""Replay the independent audit as read-only data and test the amended profiles.

No auditor or producer code is imported. All checker calls are in-process,
leaving nauty as the only child. Captured evidence stays in the allowed scratch.
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import sys
import time
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
import gp10check as ck

SOURCE = ck.GP / "check-audit/cases"
OUTPUT = ck.SCRATCH / "round2/regression"
# Amendment 1 makes these profiles valid. Their declared unknowns still reject.
REASON_UPDATES = {f"unsupported-B{n}p": "control_unknown" for n in range(4, 8)}


def canonical_json(value):
    # bool and int must compare differently in mutation audits.
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def changed_field(parent, child, path):
    assert path, "a mutation must identify a field"
    assert canonical_json(parent) != canonical_json(child), "inert mutation"
    rebuilt = copy.deepcopy(parent)
    a, b = rebuilt, child
    for key in path[:-1]:
        a, b = a[key], b[key]
    key = path[-1]
    if isinstance(b, dict) and key not in b:
        del a[key]
    else:
        a[key] = copy.deepcopy(b[key])
    assert canonical_json(rebuilt) == canonical_json(child), "mutation changes more than its declared field"


def fingerprint(directory):
    h = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        h.update(path.relative_to(directory).as_posix().encode())
        h.update(b"\0")
        h.update(ck.digest(path).encode())
    return h.hexdigest()


def mutation_check(case, by_name):
    parent_name = case["parent"]
    if parent_name is None:
        assert case["mutation"] is None and case["status"] == "ACCEPT"
        return False
    parent = by_name[parent_name]
    assert parent["status"] == "ACCEPT", (case["name"], "parent is not a positive")
    mutation = case["mutation"]
    before = SOURCE / parent_name / mutation["file"]
    after = SOURCE / case["name"] / mutation["file"]
    if mutation["scope"] == "file":
        assert (before.read_bytes() if before.exists() else None) != (after.read_bytes() if after.exists() else None)
    else:
        a, b = json.loads(before.read_text()), json.loads(after.read_text())
        assert mutation["scope"] in ("record", "polynomial")
        changed_field(a, b, mutation["path"])
    return True


def replay(case):
    name = case["name"]
    output = OUTPUT / name
    output.mkdir(parents=True, exist_ok=True)
    original_reason = case["reason"]
    reason = REASON_UPDATES.get(name, original_reason)
    if name in REASON_UPDATES:
        assert case["kind"] == "run" and original_reason == "profile" and case["status"] == "REJECT"
        assert ck.read_json(SOURCE / name / "run.json")["profile"] == name.removeprefix("unsupported-")
    if case["kind"] == "run":
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            code = ck.main([str(SOURCE / name), "--output", str(output / "checked")])
        stdout = captured.getvalue()
        (output / "observed.stdout").write_text(stdout)
        assert code == (0 if case["status"] == "ACCEPT" else 1), (name, code, stdout)
        assert stdout.splitlines()[-1] == f'{case["status"]} run {reason}', (name, reason, stdout)
        if case["record_reason"]:
            records = output / "checked/records.jsonl"
            assert records.exists(), (name, "missing per-record evidence")
            wanted = case["record_reason"]
            assert any(r["status"] == "REJECT" and
                       (r["reason"] == wanted or r["reason"].startswith(wanted + ":"))
                       for r in (ck.loads(line) for line in records.read_text().splitlines())), (name, wanted, stdout)
        result = {"name": name, "kind": "run", "status": case["status"], "reason": reason,
                  "record_reason": case["record_reason"], "exit_code": code, "stdout": str(output / "observed.stdout")}
    else:
        assert case["kind"] == "sturm"
        polynomial = ck.read_json(SOURCE / name / "polynomial.json")
        try:
            count = ck.sturm_real_roots(polynomial)
        except ck.Rejection as exc:
            assert case["count"] is None and exc.reason == reason, (name, str(exc))
            stdout = f"REJECT helper {exc.reason}\n"
            count = None
        else:
            assert reason == "returned" and count == case["count"], (name, count, case)
            assert case["status"] == ("ACCEPT" if count == 0 else "REJECT")
            stdout = f"RETURN sturm_real_roots {count}\n"
        (output / "observed.stdout").write_text(stdout)
        result = {"name": name, "kind": "sturm", "status": case["status"], "reason": reason, "count": count,
                  "stdout": str(output / "observed.stdout")}
    if original_reason != reason:
        result["original_audit_reason"] = original_reason
    suffix = f" (amended from {original_reason})" if original_reason != reason else ""
    print(f'PASS audit {name}: {case["status"]} {reason}{suffix}', flush=True)
    return result


def round2_profiles():
    root = ck.HERE / "fixtures/round2"
    checker = ck.Checker()
    results = []
    counts = {"B4p": 1, "B5p": 1, "B6p": 1, "B7p": 3}
    for case in ck.read_json(root / "minimal-comparisons.json"):
        profile = case["profile"]
        changed_field(case["positive"], case["negative"], case["mutation_path"])
        count = ck.compare_control_minimals(profile, case["positive"]["minimal"], checker)
        assert count == counts[profile]
        results.append({"name": profile + "-minimal-comparison", "status": "ACCEPT", "count": count, "scope": "comparison helper"})
        print(f"PASS new {profile} minimal comparison: ACCEPT members={count}", flush=True)
        try:
            ck.compare_control_minimals(profile, case["negative"]["minimal"], checker)
        except ck.Rejection as exc:
            assert exc.reason == case["reason"]
            results.append({"name": profile + "-wrong-derived-list", "status": "REJECT", "reason": exc.reason,
                            "scope": "comparison helper", "positive": profile + "-minimal-comparison"})
            print(f"PASS new {profile} wrong derived list: REJECT {exc.reason}", flush=True)
        else:
            raise AssertionError(profile + " wrong list was accepted")
    assert {r["name"] for r in results if r["status"] == "ACCEPT"} == {p + "-minimal-comparison" for p in counts}
    good = ck.Run(root / "B4p-accepted", OUTPUT / "new-B4p-accepted", emit=lambda _: None).execute()
    assert good["status"] == "ACCEPT" and good["profile"] == "B4p", good
    assert good["forbidden_limit"] == 3 and good["counts"] == {"embedded": 2, "refuted": 1, "unknown": 0}, good
    assert good["control"] == {"status": "PASS", "minimal_members": 1}, good
    assert (OUTPUT / "new-B4p-accepted/L4.g6").read_text() == "C~\n"
    results.append({"name": "B4p-frozen-complete", "status": "ACCEPT", "scope": "full frozen control",
                    "report": str(OUTPUT / "new-B4p-accepted/report.json")})
    print("PASS new B4p complete frozen run: ACCEPT embedded=2 refuted=1 unknown=0", flush=True)
    changed_files = [p.name for p in (root / "B4p-accepted").iterdir()
                     if p.read_bytes() != (root / "B4p-wrong-claim" / p.name).read_bytes()]
    assert changed_files == ["claim.g6"], changed_files
    bad = ck.Run(root / "B4p-wrong-claim", OUTPUT / "new-B4p-wrong-claim", emit=lambda _: None).execute()
    assert bad["status"] == "REJECT" and bad["reason"] == "minimality_claim_mismatch", bad
    results.append({"name": "B4p-wrong-claim", "status": "REJECT", "reason": bad["reason"],
                    "scope": "full frozen control", "positive": "B4p-frozen-complete"})
    print("PASS new B4p wrong claimed list: REJECT minimality_claim_mismatch", flush=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--all", action="store_true")
    choice.add_argument("--case", help="one retained audit case, including its accepted parent")
    args = parser.parse_args(argv)
    cases = ck.read_json(SOURCE / "index.json")
    by_name = {case["name"]: case for case in cases}
    assert len(by_name) == len(cases)
    if args.case:
        assert args.case in by_name, args.case
        selected = {args.case}
        if by_name[args.case]["parent"]:
            selected.add(by_name[args.case]["parent"])
        cases = [c for c in cases if c["name"] in selected]
    else:
        parents = {c["parent"] for c in cases if c["parent"] is not None}
        assert {c["name"] for c in cases if c["status"] == "ACCEPT"} <= parents
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_before = fingerprint(SOURCE)
    checker_before = ck.digest(ck.HERE / "gp10check.py")
    started = time.monotonic()
    links = sum(mutation_check(c, by_name) for c in cases)
    # Replay every selected positive before any dependent mutation.
    ordered = [c for c in cases if c["parent"] is None] + [c for c in cases if c["parent"] is not None]
    results = [replay(c) for c in ordered]
    additions = round2_profiles() if not args.case else []
    assert fingerprint(SOURCE) == source_before, "audit source fixtures changed"
    assert ck.digest(ck.HERE / "gp10check.py") == checker_before, "checker changed during regression"
    summary = {"status": "PASS", "audit_cases": len(results), "audit_run_cases": sum(c["kind"] == "run" for c in cases),
               "audit_sturm_cases": sum(c["kind"] == "sturm" for c in cases), "mutation_links": links,
               "audit_accepted": sum(c["status"] == "ACCEPT" for c in cases),
               "audit_rejected": sum(c["status"] == "REJECT" for c in cases),
               "new_profile_cases": len(additions), "total_checks": len(results) + len(additions),
               "seconds": time.monotonic() - started, "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "source_fixtures_sha256": source_before, "checker_sha256": checker_before,
               "reason_updates": {r["name"]: r["reason"] for r in results if "original_audit_reason" in r},
               "environment": ck.environment(), "results": results, "new_profile_results": additions}
    path = ck.HERE / "round2-regression.json" if not args.case else OUTPUT / "selected-regression.json"
    ck.json_write(path, summary)
    print(f'REGRESSION PASS audit={len(results)} new={len(additions)} total={summary["total_checks"]} mutation_links={links}', flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
