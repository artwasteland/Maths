"""Convert an exact zero sum of squares plus a radical lift to existing R-real."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import json,time,argparse
from flint import fmpq
from algebra import system,choose_sat,rhombus_helpers,lift,sparse,add_scaled,verify_algebra
from graphs import MODULE,decode,forbidden_canonical
from gp10refute import configure,timed,flush_line
from round2 import R

def flatten(ctx,cofs,helpers,gens):
    full={}
    for c,(p,identity) in zip(cofs,helpers): add_scaled(full,identity,c)
    for k,c in zip(gens,cofs[len(helpers):]):
        if c: full[k]=full.get(k,ctx.constant(0))+c
    return full

def radical_certificate(code,frame,sat,square_builder,seconds):
    deadline=time.monotonic()+seconds
    remaining=lambda:max(.001,deadline-time.monotonic())
    ctx,coords,gens=system(code,frame,sat)
    helpers=rhombus_helpers(code,frame,sat,ctx,coords,gens)
    polynomials=[p for p,c in helpers]+list(gens.values())
    squares=square_builder(ctx,coords)
    zero,one=ctx.constant(0),ctx.constant(1)
    S=sum((w*q*q for w,q in squares),zero)
    print("LIFT zero SOS",len(squares),flush=True)
    # The saturation equations are not normally needed to prove S=0, beyond
    # the checked rhombus helpers. Avoid them in this first discovery lift.
    edgegens={k:v for k,v in gens.items() if k.startswith("e:")}
    scofs=lift(ctx,[p for p,c in helpers]+list(edgegens.values()),S,remaining())
    if scofs is None: return None,{"reason":"zero SOS not in helper/edge ideal"}
    cofsS=flatten(ctx,scofs,helpers,edgegens)
    assert sum((p*gens[k] for k,p in cofsS.items()),zero)==S
    print("LIFT radical unit",flush=True)
    cofs=lift(ctx,[q for w,q in squares]+polynomials,one,remaining())
    if cofs is None: return None,{"reason":"radical lift did not yield 1"}
    hs=cofs[:len(squares)];cofsA=flatten(ctx,cofs[len(squares):],helpers,gens)
    A=sum((p*gens[k] for k,p in cofsA.items()),zero)
    Q=sum((q*h for (w,q),h in zip(squares,hs)),zero)
    assert A+Q==one
    T=sum((h*h/w for (w,q),h in zip(squares,hs)),zero)
    full={};add_scaled(full,cofsS,T);add_scaled(full,cofsA,2*one-A)
    out_squares=[]
    for i,((wi,qi),hi) in enumerate(zip(squares,hs)):
        for (wj,qj),hj in list(zip(squares,hs))[i+1:]:
            q=qi*hj-(wj/wi)*qj*hi
            if q: out_squares.append([str(wi/wj),sparse(q)])
    f=one+S*T-Q*Q
    cert={"type":"real","frame":frame,"sat":sat,"cofactors":{k:sparse(p) for k,p in full.items() if p},"f":sparse(f),"sos":{"c":"1","squares":out_squares}}
    verify_algebra(code,cert)
    return cert,{"zero_sos_squares":len(squares),"output_squares":len(out_squares)}

def main():
    configure();p=argparse.ArgumentParser();p.add_argument("--index",type=int,required=True);p.add_argument("--seconds",type=float,default=60);p.add_argument("--tag",required=True);a=p.parse_args()
    maps=json.loads((R/"appendix-maps.json").read_text());m=maps[str(a.index)]["map"]
    code=forbidden_canonical()[a.index];n,edges=decode(code)
    frame=sorted((m[0],m[1])) if a.index==38 else sorted((m[0],m[2]))
    sat=[list(x) for x in choose_sat(n,edges)]
    # Include all pairs for radical collision exclusion, using the published grammar.
    import itertools
    sat=[list(x) for x in itertools.combinations(range(n),2) if x not in edges]
    def squares(ctx,c):
        P=lambda i,j:c[m[i-1]][j]
        if a.index==22:
            return [(fmpq(1),P(b,j)-P(a,j)-P(3,j)+P(1,j)) for a,b in [(1,8),(8,9),(9,6)] for j in (0,1)]
        if a.index==38:
            return [(fmpq(2),P(mid,j)-(P(u,j)+P(v,j))/2) for mid,u,v in [(9,1,7),(8,5,4)] for j in (0,1)]
        raise ValueError("no geometric builder")
    start=time.monotonic();cert=None
    try:
        with timed(a.seconds): cert,detail=radical_certificate(code,frame,sat,squares,a.seconds)
    except Exception as exc: detail={"reason":type(exc).__name__+": "+str(exc)[:300]}
    detail.update({"index":a.index,"g6":code,"frame":frame,"seconds":time.monotonic()-start,"limit":a.seconds,"verdict":"refuted" if cert else "unknown"})
    with (R/(a.tag+".jsonl")).open("w") as f: flush_line(f,{"g6":code,"verdict":"refuted" if cert else "unknown","cert":cert or {"reason":detail.get("reason","exhausted"),"budget":detail}})
    (R/(a.tag+".summary.json")).write_text(json.dumps(detail,indent=2)+"\n");print(json.dumps(detail),flush=True)
if __name__=="__main__": main()
