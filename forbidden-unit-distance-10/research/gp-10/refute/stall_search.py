#!<repo>/pyenv-gp10/bin/python
"""Bounded edge-frame and saturation experiments for the four stalls."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse,itertools,json,time,hashlib
from gp10refute import configure,timed,flush_line
from graphs import MODULE,decode,forbidden_canonical
from algebra import algebra_search,choose_sat
from round2 import R

def main():
    configure();p=argparse.ArgumentParser()
    p.add_argument("--index",type=int,required=True);p.add_argument("--seconds",type=float,default=15)
    p.add_argument("--sat",choices=["default","distance2","all"],default="default")
    p.add_argument("--ordering",choices=["dp","lp"],default="dp")
    p.add_argument("--slim",action="store_true")
    p.add_argument("--fglm",action="store_true")
    p.add_argument("--t-first",action="store_true")
    p.add_argument("--extra-sat",type=int,nargs=2,action="append",default=[])
    p.add_argument("--target");p.add_argument("--start",type=int,default=0);p.add_argument("--count",type=int,default=100)
    p.add_argument("--tag",required=True)
    a=p.parse_args();code=forbidden_canonical()[a.index];n,edges=decode(code)
    frames=sorted(edges)[a.start:a.start+a.count];assert len(frames)*a.seconds<=285
    sat=choose_sat(n,edges,a.sat=="all")
    if a.sat=="distance2":
        sat=sorted(set(sat)|{(u,v) for u,v in itertools.combinations(range(n),2) if (u,v) not in edges and any(tuple(sorted((u,w))) in edges and tuple(sorted((v,w))) in edges for w in range(n))})
    sat=sorted(set(sat)|{tuple(x) for x in a.extra_sat})
    out=R/(a.tag+".jsonl");log=R/(a.tag+".attempts.jsonl")
    if out.exists() or log.exists(): raise ValueError("choose a fresh tag")
    with out.open("w") as f,log.open("w") as journal:
        for frame in frames:
            names=[v for i in range(n) if i not in frame for v in (f"x{i}",f"y{i}")]+[f"t{i}" for i in range(len(sat))]
            order=([v for v in names if v.startswith("t")]+[v for v in names if not v.startswith("t")]) if a.t_first else None
            if a.target:
                if a.target not in names: continue
                order=[v for v in (order or names) if v!=a.target]+[a.target]
            start=time.monotonic();cert=None;stages=[]
            def trace(stage):
                row={"stage":stage,"seconds":time.monotonic()-start};stages.append(row);print(json.dumps(row),flush=True)
            try:
                with timed(a.seconds):
                    cert,detail=algebra_search(code,"real",a.seconds,frame=list(frame),extra_sat=sat,variable_order=order,ordering=a.ordering,fglm=a.fglm,trace=trace,algorithm="slimgb" if a.slim else "std")
            except Exception as exc: detail={"reason":type(exc).__name__+": "+str(exc)[:200]}
            row={"index":a.index,"g6":code,"frame":frame,"sat":a.sat,"ordering":a.ordering,"target":a.target,"limit":a.seconds,"seconds":time.monotonic()-start,"verdict":"refuted" if cert else "unknown","detail":detail,"stages":stages}
            flush_line(journal,row);print(json.dumps(row),flush=True)
            if cert:
                flush_line(f,{"g6":code,"verdict":"refuted","cert":cert});break
    (R/(a.tag+".meta.json")).write_text(json.dumps({"argv":sys.argv,"source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob("*.py")}},indent=2)+"\n")
if __name__=="__main__": main()
