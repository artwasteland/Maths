"""Bounded homogeneous R-null lifts for the two-circle obstruction."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse,json,time
from algebra import *
from graphs import forbidden_canonical
from gp10refute import configure,timed,flush_line
from round2 import R

def main():
    configure();p=argparse.ArgumentParser();p.add_argument("--frame",type=int,nargs=2,default=[1,8]);p.add_argument("--degree",type=int,default=12);p.add_argument("--seconds",type=float,default=55);p.add_argument("--slim",action="store_true");p.add_argument("--circles",action="store_true");p.add_argument("--direct",action="store_true");p.add_argument("--tag",required=True);a=p.parse_args()
    code=forbidden_canonical()[39];n,edges=decode(code);sat=[list(x) for x in sorted(set(choose_sat(n,edges))|{(0,1),(0,2),(0,3),(0,4),(5,8),(6,7)})];ctx,c,g=system(code,a.frame,sat);helpers=prepared_helpers(code,a.frame,sat,ctx,c,g);one=ctx.constant(1)
    if a.circles:
        from circle_helpers import helpers39
        helpers+=helpers39(code,a.frame,sat,ctx,c,g,helpers)
    helpers,target,difference=reduce_problem(ctx,helpers,one)
    start=time.monotonic();stages=[];cert=None;detail={}
    def trace(stage):
        row={"stage":stage,"seconds":time.monotonic()-start};stages.append(row);print(json.dumps(row),flush=True)
    try:
        with timed(a.seconds):
            if a.direct:
                cofs=lift(ctx,[p for p,h in helpers],target,a.seconds,algorithm="slimgb" if a.slim else "std")
            else:
                cofs=homogeneous_lift(ctx,[p for p,h in helpers],target,a.seconds,padding=a.degree,algorithm="slimgb" if a.slim else "std")
            trace("lift:"+str(cofs is not None))
            if cofs:
                full=dict(difference)
                for cf,(q,h) in zip(cofs,helpers):add_scaled(full,h,cf)
                terms=sum(len(v.to_dict()) for v in full.values());detail["terms"]=terms;trace("terms:"+str(terms))
                if terms>150000:raise ValueError("certificate term budget")
                cert={"type":"null","frame":a.frame,"sat":sat,"cofactors":{k:sparse(p) for k,p in full.items() if p}}
                verify_algebra(code,cert);trace("verified")
                detail["bytes"]=len(json.dumps({"g6":code,"verdict":"refuted","cert":cert},separators=(",",":")))+1
                if detail["bytes"]>8*1024*1024:raise ValueError("checker line budget")
    except Exception as exc:cert=None;detail["reason"]=type(exc).__name__+": "+str(exc)[:200]
    detail.update({"g6":code,"frame":a.frame,"degree":a.degree,"seconds":time.monotonic()-start,"limit":a.seconds,"stages":stages,"verdict":"refuted" if cert else "unknown"})
    with (R/(a.tag+".jsonl")).open("w") as f:flush_line(f,{"g6":code,"verdict":detail["verdict"],"cert":cert or {"reason":detail.get("reason","no homogeneous lift"),"budget":detail}})
    (R/(a.tag+".summary.json")).write_text(json.dumps(detail,indent=2)+"\n");print(json.dumps(detail),flush=True)
if __name__=="__main__":main()
