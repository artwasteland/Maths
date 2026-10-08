"""Compile a smaller saturation lift into the original checker grammar."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse,json,time
from algebra import *
from graphs import MODULE,forbidden_canonical
from gp10refute import configure,timed,flush_line
from round2 import R

def factored(code,frame,sat,target,extra,seconds,trace=lambda s:None,homogeneous=False):
    deadline=time.monotonic()+seconds
    remaining=lambda:max(.001,deadline-time.monotonic())
    ctx,coords,gens=system(code,frame,sat)
    target=unsparse(ctx,target)
    helpers=prepared_helpers(code,frame,sat,ctx,coords,gens,include_sat=False)
    one,zero=ctx.constant(1),ctx.constant(0)
    D,T=one,one;telescoping={}
    for pair in extra:
        u,v=sorted(pair);d=sum(((coords[u][j]-coords[v][j])**2 for j in (0,1)),zero)
        t=ctx.gen(2*(decode(code)[0]-2)+sat.index([u,v]))
        telescoping[f"s:{u},{v}"]=T*D
        T*=t;D*=d
    Z=T*D
    for power in [1,2,3]:
        trace("power:"+str(power))
        cofs=(homogeneous_lift if homogeneous else lift)(ctx,[p for p,c in helpers],target*D**power,remaining())
        if cofs is None: continue
        trace("lifted")
        full={}
        for c,(p,identity) in zip(cofs,helpers):add_scaled(full,identity,c*T**power)
        add_scaled(full,telescoping,-target*sum((Z**i for i in range(power)),zero))
        assert sum((p*gens[k] for k,p in full.items()),zero)==target
        trace("expanded:"+str(sum(len(p.to_dict()) for p in full.values())))
        return {k:sparse(p) for k,p in full.items() if p},{"power":power,"terms":sum(len(p.to_dict()) for p in full.values())}
    return None,{"reason":"no small power lift"}

def main():
    configure();p=argparse.ArgumentParser();p.add_argument("--homogeneous",action="store_true");p.add_argument("--candidate",required=True);p.add_argument("--index",type=int,required=True);p.add_argument("--seconds",type=float,default=90);p.add_argument("--tag",required=True);a=p.parse_args()
    b=json.loads((R/a.candidate).read_text());code=forbidden_canonical()[a.index];start=time.monotonic();stages=[]
    def trace(stage):
        row={"stage":stage,"seconds":time.monotonic()-start};stages.append(row);print(json.dumps(row),flush=True)
    cert=None
    try:
        with timed(a.seconds):
            cofs,detail=factored(code,b["frame"],b["sat"],b["target"],b["extra"],a.seconds,trace,a.homogeneous)
            if cofs:
                cert={"type":"real","frame":b["frame"],"sat":b["sat"],"cofactors":cofs,"f":b["target"],**b["proof"]}
                verify_algebra(code,cert);trace("verified")
    except Exception as exc:cert=None;detail={"reason":type(exc).__name__+": "+str(exc)[:300]}
    detail.update({"g6":code,"verdict":"refuted" if cert else "unknown","seconds":time.monotonic()-start,"limit":a.seconds,"stages":stages})
    with (R/(a.tag+".jsonl")).open("w") as f:flush_line(f,{"g6":code,"verdict":detail["verdict"],"cert":cert or {"reason":detail.get("reason","exhausted"),"budget":detail}})
    (R/(a.tag+".summary.json")).write_text(json.dumps(detail,indent=2)+"\n");print(json.dumps(detail),flush=True)
if __name__=="__main__": main()
