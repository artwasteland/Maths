#!/usr/bin/env python3
"""Verify the narrow Round 2 change and inventory every changed line without git."""
import argparse
import ast
import copy
import difflib
import json
import os
from pathlib import Path
import re
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import gp10check as ck

ROOT = ck.HERE
BEGIN = "<!-- ROUND2_RANGES_BEGIN -->"
END = "<!-- ROUND2_RANGES_END -->"
ALLOWED = {"compare_control_minimals", "Run.execute", "Run.controls", "Run.load_input",
           "Run.minimality", "Run.profile_controls"}


def functions(body, prefix=""):
    result = {}
    for node in body:
        if isinstance(node, ast.ClassDef):
            result.update(functions(node.body, prefix + node.name + "."))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[prefix + node.name] = node
    return result


def checker_review(baseline):
    before = ast.parse((baseline / "gp10check.py").read_text())
    after = ast.parse((ROOT / "gp10check.py").read_text())
    old, new = functions(before.body), functions(after.body)
    assert old.keys() == new.keys(), "checker functions were added or removed"
    changed = {name for name in old if ast.dump(old[name]) != ast.dump(new[name])}
    assert changed == ALLOWED, sorted(changed)
    # All mathematical work inside minimality is unchanged; only its filename differs.
    a, b = copy.deepcopy(old["Run.minimality"]), copy.deepcopy(new["Run.minimality"])
    assert isinstance(a.body[1], ast.Assign) and a.body[1].targets[0].id == "outname"
    assert isinstance(b.body[1], ast.Assign) and b.body[1].targets[0].id == "outname"
    a.body.pop(1); b.body.pop(1)
    assert ast.dump(a) == ast.dump(b), "minimality decision logic changed"
    def globals_and_classes(tree, remove_profiles=False):
        items = []
        for original in tree.body:
            node = copy.deepcopy(original)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(node, ast.ClassDef):
                node.body = [n for n in node.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if remove_profiles and isinstance(node, ast.Assign) and any(
                    isinstance(n, ast.Name) and n.id in {"CONTROL_ORDERS", "FROZEN_ORDERS"} for n in node.targets):
                continue
            items.append(ast.dump(node))
        return items
    assert globals_and_classes(before) == globals_and_classes(after, True), "unrelated checker globals changed"
    return {"functions_checked": len(old), "unchanged_functions": len(old) - len(changed), "changed_functions": sorted(changed),
            "minimality_decision_logic": "unchanged", "unrelated_globals": "unchanged"}


def line_inventory(baseline):
    old = {p.relative_to(baseline).as_posix(): p for p in baseline.rglob("*") if p.is_file()}
    new = {p.relative_to(ROOT).as_posix(): p for p in ROOT.rglob("*") if p.is_file()}
    result = []
    for name in sorted(old.keys() | new.keys()):
        a = old[name].read_text().splitlines() if name in old else []
        b = new[name].read_text().splitlines() if name in new else []
        if name in old and name in new and old[name].read_bytes() == new[name].read_bytes():
            continue
        ranges = [{"operation": op, "old_start": i1 + 1, "old_end": i2,
                   "new_start": j1 + 1, "new_end": j2}
                  for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != "equal"]
        result.append({"path": name, "kind": "new" if name not in old else "deleted" if name not in new else "modified",
                       "old_lines": len(a), "new_lines": len(b), "ranges": ranges})
    return result


def table(inventory):
    rows = ["| File | Old lines | New lines |", "| --- | --- | --- |"]
    for item in inventory:
        if not item["ranges"]:
            rows.append(f'| `{item["path"]}` | absent | empty new file |')
        for span in item["ranges"]:
            def location(start, end, kind):
                if kind == "new":
                    return "absent"
                return str(start) if start == end else f"{start}-{end}" if start < end else f"after {end} (insertion)"
            old = location(span["old_start"], span["old_end"], item["kind"])
            new = location(span["new_start"], span["new_end"], "existing")
            rows.append(f'| `{item["path"]}` | {old} | {new} |')
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("/tmp/gp10-check/round2/baseline"))
    parser.add_argument("--update-ranges", action="store_true")
    args = parser.parse_args(argv)
    review = checker_review(args.baseline)
    expected = re.search(r"Checker SHA256: `([0-9a-f]{64})`", (ck.GP / "check-audit/REPORT.md").read_text()).group(1)
    assert ck.digest(args.baseline / "gp10check.py") == expected
    regression = ck.read_json(ROOT / "round2-regression.json")
    measured = ck.read_json(ROOT / "benchmark.json")
    benchmark = ck.read_json(Path(measured["run_report"]))
    assert regression["status"] == "PASS" and benchmark["status"] == "ACCEPT"
    assert regression["checker_sha256"] == benchmark["checker_sha256"] == ck.digest(ROOT / "gp10check.py")
    assert regression["reason_updates"] == {f"unsupported-B{n}p": "control_unknown" for n in range(4, 8)}
    assert (ROOT / "round2-selftest.log").read_bytes() == (ROOT / "selftest.log").read_bytes()
    report_path = ROOT / "REPORT.md"
    report = report_path.read_text()
    assert report.rsplit("\n## ", 1)[1].startswith("UNCERTAIN\n")
    assert "\n## Round 2\n" in report
    for name in ("round2-regression.log", "round2-benchmark.log", "round2-selftest.log"):
        assert (ROOT / name).read_text() in report, name
    for path in ROOT.rglob("*"):
        if path.is_file():
            assert chr(0x2014).encode() not in path.read_bytes(), str(path)
    for path in ROOT.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    status = {"status": "PASS", "audited_baseline_sha256": expected, "checker_sha256": ck.digest(ROOT / "gp10check.py"),
              "baseline": str(args.baseline), "source_review": review, "regression_checks": regression["total_checks"],
              "original_selftest_output": "identical", "syntax": "PASS", "no_em_dash": "PASS"}
    log = (f'ROUND2 REVIEW PASS functions={review["functions_checked"]} unchanged={review["unchanged_functions"]} '
           f'changed={len(review["changed_functions"])} regression={regression["total_checks"]}\n')
    if args.update_ranges:
        (ROOT / "round2-review.log").write_text(log)
        for _ in range(12):
            before_report = report_path.read_text()
            inventory = line_inventory(args.baseline)
            payload = {**status, "files": inventory}
            old_payload = ck.read_json(ROOT / "round2-review.json") if (ROOT / "round2-review.json").exists() else None
            ck.json_write(ROOT / "round2-review.json", payload)
            prefix, tail = before_report.split(BEGIN, 1)
            _, suffix = tail.split(END, 1)
            updated = prefix + BEGIN + "\n" + table(inventory) + "\n" + END + suffix
            report_path.write_text(updated)
            if old_payload == payload and before_report == updated:
                break
        else:
            raise AssertionError("changed-line inventory did not stabilize")
    inventory = line_inventory(args.baseline)
    saved = ck.read_json(ROOT / "round2-review.json")
    assert saved == {**status, "files": inventory}, "saved review does not match current files"
    actual_table = report_path.read_text().split(BEGIN, 1)[1].split(END, 1)[0].strip()
    assert actual_table == table(inventory), "REPORT range table is stale"
    print(log, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
