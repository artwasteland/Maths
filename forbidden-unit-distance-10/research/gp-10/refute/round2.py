#!<repo>/pyenv-gp10/bin/python
"""Round 2 bounded experiments and official-checker adapter."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
import sys
sys.dont_write_bytecode=True
import argparse, hashlib, importlib.util, json, time
from pathlib import Path
from graphs import MODULE,ROOT,UD,SCRATCH,decode,patterns,maps,canonical,forbidden_canonical
from gp10refute import configure,run_method,flush_line
R=MODULE/"evidence/round2"
F=MODULE/"fixtures"
ST=[22,38,39,66]

def records(path):
    with Path(path).open() as f:
        for line in f:
            yield json.loads(line)

def prepare():
    R.mkdir(exist_ok=True)
    full=json.loads((UD/"data/forbidden-74.json").read_text())
    ps=patterns(full)
    for k in [6,19]: (F/f"F{k}.json").write_text(json.dumps(full[:k])+"\n")
    rows={}
    for suite in ["B8p","B9p"]:
        codes=(ROOT/f"research/gp-10/data/{suite}.g6").read_text().splitlines()
        selected=[]
        for code in codes:
            g=decode(code)
            for j,p in enumerate(ps):
                m=next(maps(p,g),None)
                if m is not None:
                    selected.append({"g6":code,"index":j,"map":m});break
        assert len(selected)==(17 if suite=="B8p" else 101)
        rows[suite]=selected
        (R/f"{suite}.g6").write_text("\n".join(r["g6"] for r in selected)+"\n")
        print(suite,len(codes),len(selected),flush=True)
    (R/"selection.json").write_text(json.dumps(rows,indent=2)+"\n")

def sweep(a):
    R.mkdir(exist_ok=True)
    gp=forbidden_canonical()
    codes=[gp[i] for i in ST] if a.suite=="stalls" else (R/f"{a.suite}.g6").read_text().splitlines()
    codes=codes[a.start:a.start+a.count]
    assert len(codes)*a.seconds<=285
    full=patterns(json.loads((UD/"data/forbidden-74.json").read_text()))
    forbidden=full[:a.prefix]
    known={r["g6"]:True for r in records(MODULE/"evidence/GP74.refuted.jsonl")} if a.known else {}
    if a.method=="tree": import amp_core
    path=R/(a.tag+".jsonl")
    if path.exists(): raise ValueError("choose a fresh tag")
    rows=[];started=time.monotonic()
    with path.open("w") as f:
        for code in codes:
            cert,detail=run_method(code,a.method,a.seconds,forbidden,known,1000,a.all_sat)
            rec={"g6":code,"verdict":"refuted" if cert else "unknown","cert":cert or {"reason":detail.get("reason","exhausted"),"budget":detail}}
            flush_line(f,rec)
            row={"g6":code,"gp_index":gp.index(code) if code in gp else None,"verdict":rec["verdict"],"detail":detail}
            rows.append(row);print(json.dumps(row),flush=True)
    summary={"argv":sys.argv,"rows":rows,"seconds":time.monotonic()-started,"prefix":a.prefix,"known":a.known,
             "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob("*.py")}}
    (R/(a.tag+".summary.json")).write_text(json.dumps(summary,indent=2)+"\n")

def check(directory):
    # Only relocate scratch. No parsing, proof, limits or verdict logic is modified.
    path=ROOT/"research/gp-10/check/gp10check.py"
    spec=importlib.util.spec_from_file_location("gp10_official_checker",path)
    ck=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ck;spec.loader.exec_module(ck)
    ck.SCRATCH=SCRATCH/"official-checker"
    os.environ["TMPDIR"]=os.environ["SQLITE_TMPDIR"]=str(ck.SCRATCH)
    return ck.main([str(directory)])

def export(tag,paths,limit,dependencies=False):
    directory=R/tag;directory.mkdir(exist_ok=True)
    selected={}
    for path in paths:
        for rec in records(path):
            old=selected.get(rec["g6"])
            if old is None or (rec["verdict"]=="refuted" and (old["verdict"]!="refuted" or len(json.dumps(rec))<len(json.dumps(old)))):
                selected[rec["g6"]]=rec
    if dependencies:
        library={r["g6"]:r for r in records(MODULE/"evidence/GP74.refuted.jsonl")}
        for rec in list(selected.values()):
            c=rec["cert"]
            target=c.get("end",{}).get("refuted") if c.get("type")=="tu" else c.get("g6") if c.get("type")=="sub" and "index" not in c else None
            if target and target not in selected: selected[target]=library[target]
    inputbytes=("\n".join(sorted(selected))+"\n").encode()
    (directory/"input.g6").write_bytes(inputbytes)
    with (directory/"records.jsonl").open("w") as f:
        for code in sorted(selected): flush_line(f,selected[code])
    unknown=sorted(r["g6"] for r in selected.values() if r["verdict"]=="unknown")
    (directory/"UNKNOWN.g6").write_text("".join(c+"\n" for c in unknown))
    (directory/"run.json").write_text(json.dumps({"profile":"sample","input":"input.g6","input_sha256":hashlib.sha256(inputbytes).hexdigest(),"records":["records.jsonl"],"forbidden_limit":limit,"unknown":"UNKNOWN.g6"},indent=2)+"\n")
    return directory

def main():
    configure();p=argparse.ArgumentParser();p.add_argument("action",choices=["prepare","sweep","check","export"])
    p.add_argument("--suite",choices=["stalls","B8p","B9p"],default="stalls")
    p.add_argument("--method",choices=["tu","tree","null","real"],default="tu")
    p.add_argument("--seconds",type=float,default=5);p.add_argument("--start",type=int,default=0);p.add_argument("--count",type=int,default=101)
    p.add_argument("--prefix",type=int,default=19);p.add_argument("--known",action="store_true");p.add_argument("--all-sat",action="store_true")
    p.add_argument("--tag");p.add_argument("--path",action="append",default=[]);p.add_argument("--limit",type=int,default=0)
    a=p.parse_args()
    if a.action=="prepare": prepare()
    elif a.action=="sweep": sweep(a)
    elif a.action=="check": return check(Path(a.path[0]))
    else: print(export(a.tag,a.path,a.limit,a.known))
    return 0
if __name__=="__main__": raise SystemExit(main())
