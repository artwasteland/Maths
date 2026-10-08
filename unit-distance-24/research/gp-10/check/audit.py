#!/usr/bin/env python3
"""Audit the delivered module without executing a producer or writing bytecode."""
import ast
import json
import os
from pathlib import Path
import sys
os.environ["SYMPY_GROUND_TYPES"]="python"
sys.dont_write_bytecode=True
import gp10check as ck


def main():
    root=Path(__file__).resolve().parent
    required=("gp10check.py","selftest.py","fixtures","FORMAT.md","REPORT.md")
    assert all((root/p).exists() for p in required)
    for path in root.glob("*.py"):
        ast.parse(path.read_text(),filename=str(path))
    for path in root.rglob("*"):
        if path.is_file():
            assert chr(0x2014).encode() not in path.read_bytes(),str(path)
    report=(root/"REPORT.md").read_text()
    assert report.rsplit("\n## ",1)[1].startswith("UNCERTAIN\n")
    for name in ("kernel-selftest.log","selftest.log","benchmark.log","fixture-build.log","cli-positive.log","cli-negative.log"):
        assert (root/name).read_text() in report,name
    required_reds={"verdict-tu","tu-final-edge","coordinate-perturbed","collision-edges-fine","interval-no-sign",
                   "frame-nonedge","extra-nonedge-generator","cofactor-coefficient","sos-zero-constant",
                   "pointer-noninjective","pointer-cycle","coverage-missing","coverage-duplicate","minimality-false-claim"}
    record_cases=ck.read_json(root/"fixtures/cases.json")
    run_cases=ck.read_json(root/"fixtures/run-cases.json")
    names={r["name"] for r in record_cases if r["status"]=="REJECT"}|{r["name"] for r in run_cases}
    assert required_reds<=names,required_reds-names
    benchmark=ck.read_json(root/"benchmark.json")
    measured=ck.read_json(Path(benchmark["run_report"]))
    assert measured["status"]=="ACCEPT" and measured["checker_sha256"]==ck.digest(root/"gp10check.py")
    assert measured["counts"]["unknown"]==benchmark["records"]
    old_scratch=ck.TRUSTED/"check/scratch"
    old_scratch_entries=sorted(p.name for p in old_scratch.iterdir()) if old_scratch.exists() else []
    result={"status":"PASS","required_deliverables":list(required),"required_red_fixtures":len(required_reds),
            "record_fixture_cases":len(record_cases),"run_fixture_mutations":len(run_cases),
            "python_syntax":"PASS","no_em_dash":"PASS","verbatim_logs":"PASS","uncertain_last":"PASS",
            "benchmark_checker_hash":"PASS","benchmark_peak_mib":benchmark["peak_self_rss_kib"]/1024,
            "trusted_scratch_entries_now":old_scratch_entries,"environment":ck.environment()}
    ck.json_write(root/"audit.json",result)
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":sys.exit(main())
