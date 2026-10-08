"""Low-degree SOS for the opposite orientations of two equilateral triangles."""
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
    configure();p=argparse.ArgumentParser();p.add_argument("--pivot",type=int,choices=[0,1,2],default=0);p.add_argument("--frame",type=int,nargs=2,default=[0,3]);p.add_argument("--seconds",type=float,default=55);p.add_argument("--slim",action="store_true");p.add_argument("--reduce",action="store_true");p.add_argument("--scale",action="store_true");p.add_argument("--homogeneous",action="store_true");p.add_argument("--padding",type=int,default=6);p.add_argument("--tag",required=True);a=p.parse_args()
    b=json.loads((R/"candidate66-2-x0.json").read_text());code=forbidden_canonical()[66];n,edges=decode(code);b["sat"]=[list(x) for x in sorted(set(choose_sat(n,edges))|{(a.pivot,v) for v in {0:[6,7],1:[6,8],2:[7,8]}[a.pivot]})];ctx,c,g=system(code,a.frame,b["sat"]);helpers=prepared_helpers(code,a.frame,b["sat"],ctx,c,g);zero=ctx.constant(0)
    qs=[sum((c[i][j] for i in [0,1,2]),zero)-sum((c[i][j] for i in [3,4,5]),zero) for j in (0,1)]
    target=ctx.constant(2)+sum((q*q/3 for q in qs),zero);proof={"sos":{"c":"2","squares":[["1/3",sparse(q)] for q in qs]}}
    start=time.monotonic();stages=[];cert=None
    def trace(stage):
        row={"stage":stage,"seconds":time.monotonic()-start};stages.append(row);print(json.dumps(row),flush=True)
    detail={}
    try:
        with timed(a.seconds):
            difference={}
            if a.reduce:helpers,target,difference=reduce_problem(ctx,helpers,target)
            trace("reduced:"+str(len(helpers)))
            if a.homogeneous:
                cofs=homogeneous_lift(ctx,[p for p,h in helpers],target,a.seconds,padding=a.padding,algorithm="slimgb" if a.slim else "std")
            else:
                cofs=lift(ctx,[p for p,h in helpers],target,a.seconds,algorithm="slimgb" if a.slim else "std")
            trace("lift:"+str(cofs is not None))
            if cofs:
                full=dict(difference)
                for cf,(q,h) in zip(cofs,helpers):add_scaled(full,h,cf)
                terms=sum(len(v.to_dict()) for v in full.values());trace("terms:"+str(terms));detail["terms"]=terms
                if terms>210000:raise ValueError("certificate term budget")
                original_target=ctx.constant(2)+sum((q*q/3 for q in qs),zero)
                if a.scale:
                    from collections import Counter
                    counts=Counter(str(v) for p in full.values() for e,v in p.terms())
                    values=[(fmpq(v),n) for v,n in counts.items()]
                    choices=[fmpq(1)]+[fmpq(3*2**k) for k in range(25)]
                    factor=min(choices,key=lambda factor:sum(n*len(str(v*factor)) for v,n in values))
                    full={k:p*factor for k,p in full.items()};original_target*=factor
                    proof["sos"]["c"]=str(fmpq(proof["sos"]["c"])*factor)
                    for sq in proof["sos"]["squares"]:sq[0]=str(fmpq(sq[0])*factor)
                    detail["scale"]=str(factor);trace("scaled:"+str(factor))
                cert={"type":"real","frame":a.frame,"sat":b["sat"],"cofactors":{k:sparse(q) for k,q in full.items() if q},"f":sparse(original_target),**proof}
                verify_algebra(code,cert);trace("verified")
                detail["bytes"]=len(json.dumps({"g6":code,"verdict":"refuted","cert":cert},separators=(",",":")))+1
                if detail["bytes"]>8*1024*1024:raise ValueError("checker line budget")
    except Exception as exc:cert=None;detail["reason"]=type(exc).__name__+": "+str(exc)[:200]
    detail.update({"g6":code,"frame":a.frame,"seconds":time.monotonic()-start,"limit":a.seconds,"stages":stages,"verdict":"refuted" if cert else "unknown"})
    with (R/(a.tag+".jsonl")).open("w") as f:flush_line(f,{"g6":code,"verdict":detail["verdict"],"cert":cert or {"reason":detail.get("reason","no lift"),"budget":detail}})
    (R/(a.tag+".summary.json")).write_text(json.dumps(detail,indent=2)+"\n");print(json.dumps(detail),flush=True)
if __name__=="__main__":main()
