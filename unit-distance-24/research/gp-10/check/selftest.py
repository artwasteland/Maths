#!/usr/bin/env python3
"""Paired positive and one-field adversarial tests for the blind checker."""
import copy
from fractions import Fraction as Q
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
os.environ["SYMPY_GROUND_TYPES"]="python"
sys.dont_write_bytecode=True
import gp10check as ck

FIX=Path(__file__).resolve().parent/"fixtures"
PASSED=0
POSITIVE=0
RED=0


def passed(name, positive=True, detail=""):
    global PASSED, POSITIVE, RED
    PASSED+=1
    if positive: POSITIVE+=1
    else: RED+=1
    print("PASS "+name+(": "+detail if detail else ""),flush=True)


def one_field(base, changed, path):
    clone=copy.deepcopy(base)
    a,b=clone,changed
    for key in path[:-1]: a,b=a[key],b[key]
    a[path[-1]]=copy.deepcopy(b[path[-1]])
    assert clone==changed, "mutation changed more than its stated field"
    assert base!=changed, "mutation is inert"


def expect_error(name, operation, reason, detail=None):
    try:
        operation()
    except ck.Rejection as exc:
        assert exc.reason==reason,(name,reason,str(exc))
        if detail: assert detail in exc.detail,(detail,exc.detail)
        passed(name,False,str(exc))
    else:
        raise AssertionError(name+" was accepted")


def main():
    ck.SCRATCH.mkdir(exist_ok=True)
    checker=ck.Checker()
    for case in ck.read_json(FIX/"cases.json"):
        record=ck.read_json(FIX/case["file"])
        ck.check_canonical([record["g6"]])
        if case["status"]=="ACCEPT":
            dep,_=checker.verify(record)
            assert dep is None
            passed(case["name"])
        else:
            base=ck.read_json(FIX/case["positive"])
            assert checker.verify(base)[0] is None
            one_field(base,record,case["mutation_path"])
            expect_error(case["name"],lambda:checker.verify(record),case["reason"],
                         "invalid distinct vertices" if case["name"]=="tree-collision-pair" else None)
    with tempfile.TemporaryDirectory(prefix="selftest-",dir=ck.SCRATCH) as temp:
        temp=Path(temp)
        results={}
        positive_runs=("pointers","mixed","unknown","refutation-pointer","frozen-pointer","tu-refuted-pointer","minimality","conditional-minimality")
        for name in positive_runs:
            result=ck.Run(FIX/name,temp/name,emit=lambda _:None).execute()
            assert result["status"]=="ACCEPT",(name,result)
            results[name]=result
            passed("run "+name,detail="ACCEPT")
        assert len(results["conditional-minimality"]["conditional_minimal"])==1
        assert results["conditional-minimality"]["conditional"] is True
        assert results["mixed"]["cross_checks"]==1
        assert results["minimality"]["minimal_count"]==1
        assert results["minimality"]["nonminimal_count"]==1
        assert results["unknown"]["unknown_rate"]["numerator"]==1
        for case in ck.read_json(FIX/"run-cases.json"):
            baseline=FIX/case["positive"]; mutation=FIX/case["name"]
            assert results[case["positive"]]["status"]=="ACCEPT"
            files={p.name for p in baseline.iterdir() if p.is_file()}
            assert files=={p.name for p in mutation.iterdir() if p.is_file()}
            changed=[p for p in files if (baseline/p).read_bytes()!=(mutation/p).read_bytes()]
            assert changed==[case["changed_file"]],changed
            result=ck.Run(mutation,temp/case["name"],emit=lambda _:None).execute()
            assert result["status"]=="REJECT" and result["reason"]==case["reason"],(case,result)
            if case["record_reason"]:
                logs=[ck.loads(s) for s in (temp/case["name"]/"records.jsonl").read_text().splitlines()]
                assert any(r["status"]=="REJECT" and r["reason"].split(":",1)[0]==case["record_reason"] for r in logs),(case,logs)
            passed("run "+case["name"],False,case["reason"]+(" / "+case["record_reason"] if case["record_reason"] else ""))
        # Unknown edge deletions are provisional, and never erase a known refuted deletion.
        source=FIX/"minimality"; target=temp/"conditional"
        shutil.copytree(source,target)
        records=[ck.loads(s) for s in (target/"records.jsonl").read_text().splitlines()]
        known=records[1]["g6"]
        records[1]={"g6":known,"verdict":"unknown","cert":{"reason":"synthetic budget","budget":{"seconds":0}}}
        (target/"records.jsonl").write_text("".join(json.dumps(r)+"\n" for r in records))
        # Its dependent pointer must reject, demonstrating that unknown is never accepted as a proof.
        result=ck.Run(target,temp/"unknown-target",emit=lambda _:None).execute()
        assert result["status"]=="REJECT" and result["reason"]=="records_rejected",result
        logs=(temp/"unknown-target/records.jsonl").read_text()
        assert "pointer_target_not_accepted_refuted" in logs
        passed("pointer to unknown target",False,"pointer_target_not_accepted_refuted")
    # Independent hand-known exact Sturm cases and one-coefficient red companions.
    for name,positive,negative,count in [
        ("quadratic",[1,0,1],[-1,0,1],2),
        ("repeated",[1,0,2,0,1],[-1,0,2,0,1],2),
        ("constant",[1],[0],None),
    ]:
        assert ck.sturm_real_roots(positive)==0
        passed("Sturm "+name+" positive")
        if count is None:
            expect_error("Sturm zero polynomial",lambda:ck.sturm_real_roots(negative),"sturm_zero_polynomial")
        else:
            assert ck.sturm_real_roots(negative)==count
            passed("Sturm "+name+" coefficient mutation",False,"real roots="+str(count))
    assert ck.sturm_real_roots([1,-2,1])==1
    passed("Sturm repeated real root",False,"real roots=1")
    # Reducibility is permitted. Bisection must choose the same root for every pair.
    raw={"g6":"A?","verdict":"embedded","cert":{"type":"exact","field":{"minpoly":[0,-4,0,1],"interval":["-3","3"]},"coords":[[["0","0","0"],["0","0","0"]],[["1","0","0"],["0","0","0"]]]}}
    checker.verify(raw); passed("reducible minpoly exact embedding")
    mutated=copy.deepcopy(raw); mutated["cert"]["coords"][1][0]=["0","1","0"]
    one_field(raw,mutated,["cert","coords",1,0])
    expect_error("rational midpoint collision",lambda:checker.verify(mutated),"exact_collision")
    # Close rational points remain distinct without a floating tolerance.
    close=copy.deepcopy(raw); close["cert"]["coords"][1][0]=["1/"+str(10**100),"0","0"]
    checker.verify(close); passed("tiny exact separation")
    close_bad=copy.deepcopy(close); close_bad["cert"]["coords"][1][0][0]="0"
    expect_error("tiny separation zero mutation",lambda:checker.verify(close_bad),"exact_collision")
    refining={"g6":"A?","verdict":"embedded","cert":{"type":"exact","field":{"minpoly":[-2,0,1],"interval":["1","2"]},"coords":[[["0","0"],["0","0"]],[["-1","1"],["0","0"]]]}}
    _,details=checker.verify(refining)
    assert details["interval_bisections"]>0
    passed("whole interval bisection",detail=str(details["interval_bisections"]))
    mutated=copy.deepcopy(refining);mutated["cert"]["coords"][1][0]=["0","0"]
    expect_error("bisection positive collision mutation",lambda:checker.verify(mutated),"exact_collision")
    trap={"g6":"C?","verdict":"embedded","cert":{"type":"exact","field":{"minpoly":[0,-4,0,1],"interval":["-3","3"]},"coords":[[[str(i),"0","0"],["0","0","0"]] for i in range(4)]}}
    checker.verify(trap);passed("shared-root positive")
    mutated=copy.deepcopy(trap)
    mutated["cert"]["coords"]=[[["0","0","0"],["0","0","0"]]]+[[[str(a),"1","0"],["0","0","0"]] for a in (-2,0,2)]
    one_field(trap,mutated,["cert","coords"])
    expect_error("all roots collide with different pairs",lambda:checker.verify(mutated),"exact_collision")
    for profile in ("B8p","B9p"):
        n={"B8p":8,"B9p":9}[profile]
        expected=[c for c,g in zip(checker.forbidden_codes,checker.forbidden) if g.n==n]
        assert ck.compare_control_minimals(profile,expected,checker)==len(expected)
        passed(profile+" expected canonical minimal members",detail=str(len(expected)))
        expect_error(profile+" missing minimal member",lambda:ck.compare_control_minimals(profile,expected[:-1],checker),"control_minimal_list")
    # Strict JSON receives a syntactically valid positive before each mutation.
    assert ck.loads('{"v":1}')=={"v":1}; passed("strict JSON positive")
    expect_error("duplicate JSON key",lambda:ck.loads('{"v":1,"v":2}'),"duplicate_json_key")
    expect_error("JSON NaN",lambda:ck.loads('{"v":NaN}'),"json_constant")
    expect_error("JSON overflowing exponent",lambda:ck.loads('{"v":1e9999}'),"json_constant")
    record_hash=ck.digest(FIX/"mixed/records.jsonl")
    guarded=ck.Run(FIX/"mixed",FIX/"mixed",emit=lambda _:None).execute()
    assert guarded["status"]=="REJECT" and guarded["reason"]=="output_input_collision",guarded
    assert ck.digest(FIX/"mixed/records.jsonl")==record_hash
    passed("output argument input collision",False,"output_input_collision")
    from dag_selftest import run as dag_selftest
    dag_selftest(checker, passed, expect_error)
    print(f"SELFTEST PASS checks={PASSED} positive={POSITIVE} rejected_mutations={RED}")
    return 0

if __name__=="__main__":sys.exit(main())
