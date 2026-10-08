#!<repo>/pyenv-gp10/bin/python
"""Reproducible bounded samples, with immediate stop on an embedded control refutation."""
from __future__ import annotations
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse
import hashlib
import json
import time
from pathlib import Path
import networkx as nx
from graphs import MODULE, ROOT, UD, canonical, decode, encode, maps, patterns, seed
from gp10refute import configure, run_method, flush_line

EVIDENCE=MODULE/"evidence"
FIXTURES=MODULE/"fixtures"

def prepare():
    FIXTURES.mkdir(exist_ok=True); EVIDENCE.mkdir(exist_ok=True)
    gpraw=(UD/"data/forbidden-74.g6").read_text().splitlines()
    gp=canonical(gpraw)
    forbidden=patterns(json.loads((UD/"data/forbidden-74.json").read_text()))
    assert len(gp)==len(forbidden)==74
    for code,pattern in zip(gp,forbidden):
        assert next(maps(pattern,decode(code)),None) is not None
    amp=canonical((UD/"sources/amp/anc/graph6.txt").read_text().splitlines())
    spindle=nx.Graph([(0,1),(0,2),(1,2),(1,3),(2,3),(0,4),(0,5),(4,5),(4,6),(5,6),(3,6)])
    mobius=nx.cycle_graph(10);mobius.add_edges_from((i,i+5) for i in range(5))
    named={"K4":nx.complete_graph(4),"K23":nx.complete_bipartite_graph(2,3),
           "mobius10":mobius,"prism":nx.circular_ladder_graph(5),"petersen":nx.petersen_graph(),"spindle":spindle}
    namedcodes=canonical([encode(len(g),g.edges()) for g in named.values()])
    namedmap=dict(zip(named,namedcodes))
    candidates=(ROOT/"research/gp-10/data/B9p.g6").read_text().splitlines()
    selected=[];scanned=0
    for code in sorted(candidates,key=lambda c:(seed(c),c)):
        scanned+=1
        if all(next(maps(p,decode(code)),None) is None for p in forbidden):
            selected.append(code)
        if len(selected)==500:
            break
    assert len(selected)==500
    assert canonical(selected)==selected
    suites={"gp74":gp,"amp":amp,"named":namedcodes,"b9":selected}
    for name,codes in suites.items():
        (FIXTURES/(name+".g6")).write_text("\n".join(codes)+"\n")
    (FIXTURES/"empty.json").write_text("[]\n")
    (FIXTURES/"named.json").write_text(json.dumps(namedmap,indent=2)+"\n")
    info={"counts":{k:len(v) for k,v in suites.items()},"b9_candidates_scanned":scanned,
          "named":namedmap,"gp_original":gpraw,
          "input_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [UD/"data/forbidden-74.g6",UD/"data/forbidden-74.json",UD/"data/tu-gadgets.json",
               UD/"sources/amp/anc/graph6.txt",ROOT/"research/gp-10/data/B9p.g6"]}}
    (EVIDENCE/"preparation.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps(info["counts"]|{"b9_candidates_scanned":scanned}),flush=True)

def main():
    configure()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--suite",choices=["gp74","amp","named","b9"])
    parser.add_argument("--method",choices=["tu","tree","null","real"])
    parser.add_argument("--seconds",type=float,default=2)
    parser.add_argument("--states",type=int,default=200)
    parser.add_argument("--start",type=int,default=0)
    parser.add_argument("--count",type=int)
    parser.add_argument("--tag",default="")
    parser.add_argument("--indices",default="")
    parser.add_argument("--all-sat",action="store_true")
    parser.add_argument("--extra-sat",type=int,nargs=2,action="append",default=[])
    parser.add_argument("--progress-every",type=int,default=1)
    args=parser.parse_args()
    if args.prepare:
        prepare();return
    if not args.suite or not args.method:
        parser.error("suite and method required")
    if args.method=="tree":
        import amp_core
    if args.method=="real":
        import sympy
    codes=(FIXTURES/(args.suite+".g6")).read_text().splitlines()
    end=len(codes) if args.count is None else args.start+args.count
    selected_indices=list(range(len(codes)))[args.start:end]
    if args.indices:
        selected_indices=[int(s) for s in args.indices.split(",")]
    codes=[codes[i] for i in selected_indices]
    if len(codes)*args.seconds>285:
        parser.error("split this sample so its total method budget is below five minutes")
    named=json.loads((FIXTURES/"named.json").read_text())
    safe=set(named[name] for name in ["prism","petersen","spindle"])
    if args.suite in ("amp","b9"):
        safe.update(codes)
    name=f"{args.suite}-{args.method}{args.tag}"
    path=EVIDENCE/(name+".jsonl")
    if path.exists():
        parser.error("evidence already exists; use a new tag")
    elapsed=time.monotonic(); rows=[]
    soundness_forbidden=patterns(json.loads((UD/"data/forbidden-74.json").read_text()))
    with path.open("w") as out:
        for i,code in enumerate(codes):
            active_forbidden=soundness_forbidden if args.method=="tu" and code in safe else []
            cert,detail=run_method(code,args.method,args.seconds,active_forbidden,{},args.states,args.all_sat,args.extra_sat)
            detail["forbidden_in_force"]=len(active_forbidden)
            record={"g6":code,"verdict":"refuted" if cert else "unknown","cert":cert or
                    {"reason":detail.get("reason","bounded method exhausted"),"budget":detail}}
            flush_line(out,record)
            rows.append({"index":selected_indices[i],"g6":code,"verdict":record["verdict"],"detail":detail})
            if (i+1)%args.progress_every==0 or i+1==len(codes):
                print(json.dumps({"suite":args.suite,"method":args.method,"index":selected_indices[i],
                      "verdict":record["verdict"],"seconds":round(detail["seconds"],4)}),flush=True)
            if cert and code in safe:
                failure={"record":record,"detail":detail}
                (EVIDENCE/(name+"-SOUNDNESS-FAILURE.json")).write_text(json.dumps(failure,indent=2)+"\n")
                (MODULE/"LABNOTES.md").write_text("# Stopped control\n\nUnexpected refutation: `"+code+"`. See `evidence/"+name+"-SOUNDNESS-FAILURE.json`.\n")
                raise RuntimeError("soundness control refuted; stop and investigate")
    import sympy,flint
    summary={"suite":args.suite,"method":args.method,"count":len(rows),"refuted":sum(r["verdict"]=="refuted" for r in rows),
             "unknown":sum(r["verdict"]=="unknown" for r in rows),"seconds_per_graph":args.seconds,
             "max_states":args.states,"all_sat":args.all_sat,"extra_sat":args.extra_sat,"total_seconds":time.monotonic()-elapsed,"rows":rows,
             "environment":{"sympy":sympy.__version__,"flint":flint.__version__,"SYMPY_GROUND_TYPES":os.environ["SYMPY_GROUND_TYPES"]},
             "argv":sys.argv,"source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob("*.py")}}
    (EVIDENCE/(name+".summary.json")).write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("rows","environment","argv","source_sha256")}),flush=True)

if __name__=="__main__":
    main()
