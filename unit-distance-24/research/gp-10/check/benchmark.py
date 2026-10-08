#!/usr/bin/env python3
"""Synthetic, all-unknown streaming benchmark using every frozen B10 graph."""
import json
import os
from pathlib import Path
import resource
import sys
import time
os.environ["SYMPY_GROUND_TYPES"]="python"
sys.dont_write_bytecode=True
import gp10check as ck


def main():
    run=ck.SCRATCH/"benchmark"
    run.mkdir(parents=True,exist_ok=True)
    frozen=ck.GP/"data/B10.g6"
    count=0
    with (run/"records.jsonl").open("w") as records, (run/"UNKNOWN.g6").open("w") as unknown:
        for _,_,raw in ck.lines(frozen):
            code=raw[:-1].decode("ascii")
            records.write(json.dumps({"g6":code,"verdict":"unknown","cert":{"reason":"synthetic streaming fixture, no search", "budget":{"seconds":0,"synthetic":True}}},separators=(",",":"))+"\n")
            unknown.write(code+"\n")
            count+=1
    ck.json_write(run/"run.json",{"profile":"sample","input":str(frozen),"input_sha256":ck.digest(frozen),"records":["records.jsonl"]})
    started=time.monotonic()
    emitted={"ACCEPT record":0,"REJECT record":0,"ACCEPT run":0,"REJECT run":0}
    def emit(line):
        emitted[" ".join(line.split()[:2])]+=1
    report=ck.Run(run,emit=emit).execute()
    elapsed=time.monotonic()-started
    assert report["status"]=="ACCEPT",report
    assert report["counts"]=={"embedded":0,"refuted":0,"unknown":count},report
    assert emitted["ACCEPT record"]==count and emitted["ACCEPT run"]==1,emitted
    result={"scope":"synthetic all-unknown records, no geometric search or proof workload", "records":count,
            "seconds":elapsed,"records_per_second":count/elapsed,"peak_self_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "peak_child_rss_kib":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "record_bytes":(run/"records.jsonl").stat().st_size,"emitted":emitted,"environment":ck.environment(),
            "run_report":str(run/"checked/report.json")}
    ck.json_write(ck.HERE/"benchmark.json",result)
    print(json.dumps(result,sort_keys=True))
    # The accepted sample differs in exactly its profile; a B10 report needs controls first.
    manifest=ck.read_json(run/"run.json");manifest["profile"]="B10"
    ck.json_write(run/"run.json",manifest)
    gated=ck.Run(run,run/"gate-rejection",emit=lambda _:None).execute()
    assert gated["status"]=="REJECT" and gated["reason"]=="controls_required",gated
    manifest["profile"]="sample";ck.json_write(run/"run.json",manifest)
    print("PASS one-field B10 profile mutation: REJECT controls_required")
    return 0

if __name__=="__main__":sys.exit(main())
