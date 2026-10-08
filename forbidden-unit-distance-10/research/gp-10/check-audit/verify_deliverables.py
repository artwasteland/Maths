#!/usr/bin/env python3
"""Check retained evidence, required report sections, and module boundaries."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def main():
    report = (HERE / "REPORT.md").read_text()
    index = json.loads((HERE / "cases/index.json").read_text())
    results = json.loads((HERE / "cases/results.json").read_text())
    findings = json.loads((HERE / "findings.json").read_text())
    assert results["summary"]["matched"] == len(index) == results["summary"]["total"]
    assert not results["summary"]["false_accepts"] and not results["summary"]["mismatches"]
    assert [r["name"] for r in results["cases"]] == [s["name"] for s in index]
    expected_sections = ["## VERDICT", "## TEST CASES", "## CODE REVIEW", "## UNCERTAIN"]
    assert [line for line in report.splitlines() if line.startswith("## ")] == expected_sections
    assert len(re.findall(r"^### [0-9]+\. ", report, re.M)) == len(index)
    names = {s["name"] for s in index}
    assert len(names) == len(index)
    assert {p.name for p in (HERE / "cases").iterdir() if p.is_dir()} == names
    parents = {s["parent"] for s in index if s["parent"]}
    assert all(s["name"] in parents for s in index if s["status"] == "ACCEPT")
    for result in results["cases"]:
        path = HERE / "cases" / result["name"]
        assert result["passed"]
        assert (path / "observed.stdout").read_text() == result["stdout"]
        if result["kind"] == "run":
            current = json.loads((path / "observed-report.json").read_text())
            assert current["status"] == result["observed_status"]
            assert current["reason"] == result["observed_reason"]
            assert current["environment"]["SYMPY_GROUND_TYPES"] == "python"
            assert current["environment"]["nice"] >= 15
    summary = results["summary"]
    for key, path in (("checker_sha256", HERE.parent / "check/gp10check.py"),
                      ("kernel_sha256", HERE.parent.parent / "unit-distance-22/check/udcheck.py")):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == summary[key]
    counts = Counter(f["severity"] for f in findings)
    assert f"BLOCKER: {counts['BLOCKER']}. MAJOR: {counts['MAJOR']}. MINOR: {counts['MINOR']}." in report
    files = [p for p in HERE.rglob("*") if p.is_file()]
    for path in files:
        assert chr(8212).encode() not in path.read_bytes(), str(path)
        assert path.suffix != ".pyc", str(path)
    scripts = list(HERE.glob("*.py"))
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    output = {"status": "PASS", "cases": len(index), "module_files": len(files),
              "module_bytes": sum(p.stat().st_size for p in files), "python_scripts": len(scripts),
              "report_sections": expected_sections, "findings": {k: counts[k] for k in ("BLOCKER", "MAJOR", "MINOR")}}
    (HERE / "validation.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print("DELIVERABLES " + json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
