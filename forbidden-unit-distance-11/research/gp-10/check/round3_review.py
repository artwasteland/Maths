#!/usr/bin/env python3
"""Prove the old checker branches unchanged and inventory Round 3 without git."""
import argparse
import ast
import copy
import os
from pathlib import Path
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import gp10check as ck
from round2_review import functions, line_inventory, table

ROOT = ck.HERE
BEGIN = "<!-- ROUND3_RANGES_BEGIN -->"
END = "<!-- ROUND3_RANGES_END -->"


def statements(body):
    return [ast.dump(node) for node in body]


def source_review(baseline):
    before = ast.parse((baseline / "gp10check.py").read_text())
    after = ast.parse((ROOT / "gp10check.py").read_text())
    old, new = functions(before.body), functions(after.body)
    added = {"real_no_zero", "canonical_polynomial", "algebra_dag"}
    assert set(new) - set(old) == added and set(old) <= set(new)
    changed = {name for name in old if ast.dump(old[name]) != ast.dump(new[name])}
    assert changed == {"algebra", "Checker.verify"}, changed
    # The original real-proof tail is moved verbatim into a callable helper.
    cut = len(new["algebra"].body) - 1
    assert statements(old["algebra"].body[:cut]) == statements(new["algebra"].body[:cut])
    expected = ast.parse("return real_no_zero(cert, ctx, names, target, parse)").body[0]
    assert ast.dump(new["algebra"].body[-1]) == ast.dump(expected)
    assert statements(old["algebra"].body[cut:]) == statements(new["real_no_zero"].body)
    dispatch = ast.parse('if kind in ("null-dag", "real-dag"):\n    return None, algebra_dag(graph, cert)').body[0]
    existing = copy.deepcopy(new["Checker.verify"])
    matches = [i for i, node in enumerate(existing.body) if ast.dump(node) == ast.dump(dispatch)]
    assert len(matches) == 1
    existing.body.pop(matches[0])
    assert ast.dump(existing) == ast.dump(old["Checker.verify"])
    def globals_only(tree):
        result = []
        for original in tree.body:
            node = copy.deepcopy(original)
            if isinstance(node, ast.FunctionDef):
                continue
            if isinstance(node, ast.ClassDef):
                node.body = [n for n in node.body if not isinstance(n, ast.FunctionDef)]
            result.append(ast.dump(node))
        return result
    assert globals_only(before) == globals_only(after)
    insertion = "    from dag_selftest import run as dag_selftest\n    dag_selftest(checker, passed, expect_error)\n"
    assert (ROOT / "selftest.py").read_text().replace(insertion, "") == (baseline / "selftest.py").read_text()
    original_log = (baseline / "round2-selftest.log").read_text().splitlines()[:-1]
    current_log = (ROOT / "round3-selftest.log").read_text().splitlines()
    assert current_log[:len(original_log)] == original_log
    preserved = [p for p in baseline.rglob("*") if p.is_file() and (
        p.relative_to(baseline).parts[0] == "fixtures" or p.name.startswith("round2") or
        p.name in {"audit_regression.py", "kernel_selftest.py"})]
    assert all(p.read_bytes() == (ROOT / p.relative_to(baseline)).read_bytes() for p in preserved)
    return {"original_functions": len(old), "identical_functions": len(old) - len(changed),
            "changed_functions": sorted(changed), "added_functions": sorted(added),
            "original_real_proof_statements": "identical after extraction",
            "existing_dispatch_branches": "identical", "original_selftest_cases_and_output": "identical",
            "preserved_historical_files": len(preserved), "unrelated_globals": "identical"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("/tmp/gp10-check/round3/baseline"))
    parser.add_argument("--update-ranges", action="store_true")
    args = parser.parse_args(argv)
    review = source_review(args.baseline)
    report_path = ROOT / "REPORT.md"
    report = report_path.read_text()
    assert report.rsplit("\n## ", 1)[1].startswith("UNCERTAIN\n")
    assert "\n## Round 3\n" in report
    for name in ("round3-selftest.log", "round3-kernel-selftest.log", "round3-fixture-build.log", "round3-benchmark.log"):
        assert (ROOT / name).read_text() in report, name
    final_lines = {name: (ROOT / name).read_text().splitlines()[-1] for name in
                   ("round3-selftest.log", "round3-kernel-selftest.log", "round3-regression.log")}
    assert all(line in report for line in final_lines.values())
    for path in ROOT.rglob("*"):
        if path.is_file():
            assert chr(0x2014).encode() not in path.read_bytes(), path
    for path in ROOT.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    regression = ck.read_json(ROOT / "round3-regression.json")
    benchmark = ck.read_json(ROOT / "benchmark.json")
    checked = ck.read_json(Path(benchmark["run_report"]))
    assert regression["status"] == "PASS" and checked["status"] == "ACCEPT"
    assert regression["checker_sha256"] == checked["checker_sha256"] == ck.digest(ROOT / "gp10check.py")
    assert ck.read_json(ROOT / "audit.json")["status"] == "PASS"
    status = {"status": "PASS", "baseline": str(args.baseline),
              "baseline_checker_sha256": ck.digest(args.baseline / "gp10check.py"),
              "checker_sha256": ck.digest(ROOT / "gp10check.py"), "source_review": review,
              "required_final_lines": final_lines, "syntax": "PASS", "no_em_dash": "PASS"}
    log = (f'ROUND3 REVIEW PASS original_functions={review["original_functions"]} '
           f'identical={review["identical_functions"]} moved_real_proof=identical existing_branches=identical\n')
    if args.update_ranges:
        (ROOT / "round3-review.log").write_text(log)
        for _ in range(12):
            previous = report_path.read_text()
            inventory = line_inventory(args.baseline)
            payload = {**status, "files": inventory}
            old_payload = ck.read_json(ROOT / "round3-review.json") if (ROOT / "round3-review.json").exists() else None
            ck.json_write(ROOT / "round3-review.json", payload)
            prefix, tail = previous.split(BEGIN, 1)
            _, suffix = tail.split(END, 1)
            updated = prefix + BEGIN + "\n" + table(inventory) + "\n" + END + suffix
            report_path.write_text(updated)
            if old_payload == payload and previous == updated:
                break
        else:
            raise AssertionError("range inventory did not stabilize")
    inventory = line_inventory(args.baseline)
    assert ck.read_json(ROOT / "round3-review.json") == {**status, "files": inventory}
    actual = report_path.read_text().split(BEGIN, 1)[1].split(END, 1)[0].strip()
    assert actual == table(inventory)
    print(log, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
