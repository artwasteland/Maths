#!<repo>/pyenv-gp10/bin/python
"""Positive certificates, one-field mutations, wrapper controls and resume checks."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import contextlib
import copy
import io
import itertools
import json
import resource
import tempfile
import time
from pathlib import Path
from fractions import Fraction
from graphs import MODULE, SCRATCH, decode, patterns, verify_tree, verify_tu, tu_search
from algebra import (AlgebraError, system, verify_algebra, basis, lift, sparse,
                     fmpq_mpoly_ctx, expanded_parse)
import gp10refute as producer

RESULTS=[]

def expect_reason(name,function,substring):
    try:
        function()
    except Exception as exc:
        reason=str(exc)
        assert substring in reason,(name,substring,reason)
        RESULTS.append({"control":name,"rejected_reason":reason})
        return
    raise AssertionError(name+" accepted mutated control")

def obtain(code,method,seconds=5):
    cert,detail=producer.run_method(code,method,seconds)
    assert cert is not None,(method,detail)
    return cert

def main(output_root=None):
    output_root=MODULE if output_root is None else Path(output_root)
    (output_root/"fixtures").mkdir(parents=True,exist_ok=True)
    (output_root/"evidence").mkdir(parents=True,exist_ok=True)
    producer.configure()
    import amp_core
    codes=(MODULE/"fixtures/gp74.g6").read_text().splitlines()
    named=json.loads((MODULE/"fixtures/named.json").read_text())
    tree=obtain(codes[0],"tree")
    verify_tree(codes[0],tree)
    bad=copy.deepcopy(tree);bad["witness"]["tree"]["move"]["pair"]=[0,0]
    expect_reason("tree collision pair",lambda:verify_tree(codes[0],bad),"invalid distinct vertices")
    null=obtain(codes[1],"null")
    verify_algebra(codes[1],null)
    bad=copy.deepcopy(null);key=next(iter(bad["cofactors"]))
    bad["cofactors"][key][0][0]=str(Fraction(bad["cofactors"][key][0][0])+1)
    expect_reason("null coefficient",lambda:verify_algebra(codes[1],bad),"identity: expansion")
    n,edges=decode(codes[1]);nonedge=next(p for p in itertools.combinations(range(n),2) if p not in edges)
    bad=copy.deepcopy(null);bad["frame"]=list(nonedge)
    expect_reason("null nonedge frame",lambda:verify_algebra(codes[1],bad),"frame: not an edge")
    bad=copy.deepcopy(null);bad["cofactors"][f"e:{nonedge[0]},{nonedge[1]}"]=[]
    expect_reason("extra nonedge generator",lambda:verify_algebra(codes[1],bad),"unexpected generator")
    bad=copy.deepcopy(null);bad["generators"]={"extra":"x=0"}
    expect_reason("certificate supplied system",lambda:verify_algebra(codes[1],bad),"unexpected system")
    real=obtain(codes[0],"real")
    verify_algebra(codes[0],real)
    assert "sos" in real
    bad=copy.deepcopy(real);bad["sos"]["c"]="0"
    expect_reason("real zero constant",lambda:verify_algebra(codes[0],bad),"sos: c must be positive")
    sturm=obtain(codes[4],"real")
    assert "sturm" in sturm
    verify_algebra(codes[4],sturm)
    ctx,_,_=system(codes[4],sturm["frame"],sturm["sat"])
    bad=copy.deepcopy(sturm)
    bad["sturm"]=next(n[0]+"_"+n[1:] for n in ctx.names() if n[0]+"_"+n[1:]!=sturm["sturm"])
    expect_reason("real univariate variable",lambda:verify_algebra(codes[4],bad),"not univariate")
    known={codes[0]:{"g6":codes[0],"verdict":"refuted","cert":tree}}
    tu=None
    for code in codes[1:]:
        cert,detail=producer.run_method(code,"tu",0.5,(),known)
        if cert and cert["steps"]:
            tu=(code,cert);break
    assert tu is not None
    code,cert=tu
    verify_tu(code,cert,[],known)
    target_n,target_edges=decode(code);augmented=set(target_edges)
    for step in cert["steps"]:augmented.add(tuple(step["pair"]))
    pattern_n,pattern_edges=decode(codes[0])
    broken=next(list(mapping) for mapping in itertools.permutations(range(target_n),pattern_n)
                if any(tuple(sorted((mapping[u],mapping[v]))) not in augmented for u,v in pattern_edges))
    bad=copy.deepcopy(cert);bad["end"]["map"]=broken
    expect_reason("TU terminal map",lambda:verify_tu(code,bad,[],known),"tu end map: not edge-preserving")
    bad=copy.deepcopy(cert);bad["end"]={}
    expect_reason("bare TU gadget",lambda:verify_tu(code,bad,[],known),"missing terminal refutation")
    bad=copy.deepcopy(cert);bad["steps"][0]["pair"]=[0,0]
    expect_reason("TU distinguished pair",lambda:verify_tu(code,bad,[],known),"missing distinguished pair")
    # Same endpoint can also be authorized explicitly as an in-force forbidden pattern.
    listed=copy.deepcopy(cert);listed["end"]={"forbidden":0,"map":cert["end"]["map"]}
    forbidden=[decode(codes[0])]
    verify_tu(code,listed,forbidden,{})
    bad=copy.deepcopy(listed);bad["end"]["map"]=broken
    expect_reason("TU forbidden map",lambda:verify_tu(code,bad,forbidden,{}),"tu end map: not edge-preserving")
    expect_reason("TU forbidden list in force",lambda:verify_tu(code,listed,[],{}),"index is not in force")
    # The producer must reject a nonedge frame even on an embeddable input.
    prism=named["prism"];n,edges=decode(prism)
    config={"frame":list(min(edges)),"sat":[]}
    system(prism,**config)
    wrong=copy.deepcopy(config)
    wrong["frame"]=list(next(p for p in itertools.combinations(range(n),2) if p not in edges))
    expect_reason("pentagonal prism frame mutation",lambda:system(prism,**wrong),"frame: not an edge")
    # A positive and a one-generator mutation prove that the CAS wrapper can say no.
    ctx=fmpq_mpoly_ctx.get(("z",),"degrevlex");z=ctx.gen(0)
    polynomials=[z*z+1,z]
    assert ctx.constant(1) in basis(ctx,polynomials,2)
    assert lift(ctx,polynomials,ctx.constant(1),2) is not None
    negative=polynomials.copy();negative[1]=ctx.constant(0)
    assert ctx.constant(1) not in basis(ctx,negative,2)
    assert lift(ctx,negative,ctx.constant(1),2) is None
    RESULTS.append({"control":"Singular positive and one-generator red","reason":"no exact identity marker for nonmember"})
    assert expanded_parse(ctx,"z^2-2*z+1")== (z-1)**2
    expect_reason("pre-expanded grammar",lambda:expanded_parse(ctx,"(z-1)^2"),"not pre-expanded")
    original=producer.tu_search
    try:
        producer.tu_search=lambda *args:(_ for _ in ()).throw(RuntimeError("injected graph failure"))
        cert,detail=producer.run_method(codes[0],"tu",0.2)
        assert cert is None and "injected graph failure" in detail["reason"]
    finally:producer.tu_search=original
    assert obtain(codes[0],"tree") is not None
    cert,detail=producer.isolated(lambda:os._exit(17),0.2)
    assert cert is None and "worker crash" in detail["reason"]
    cert,detail=producer.run_method(codes[0],"tree",0.0001)
    assert cert is None and any(s in detail["reason"] for s in ["Deadline","timeout"])
    RESULTS.append({"control":"exceptions, native child exit, timeout, next graph","reason":"all failures unknown; following positive accepted"})
    # Test L3's second child after the first unknown using the actual reducer.
    trace=amp_core.SearchTrace();budget=amp_core.SearchBudget(10,0,None,trace)
    graph=amp_core.Graph.from_graph6(codes[0]);matrix=amp_core.sp.zeros(0,graph.n)
    saved={name:getattr(amp_core,name) for name in ["find_l1","find_l2","find_l3"]}
    try:
        amp_core.find_l1=lambda *a,**k: ({"kind":"L1a","collision":[0,1]} if trace.states_visited==3 else None)
        amp_core.find_l2=lambda *a,**k: None
        amp_core.find_l3=lambda *a,**k: (({"kind":"L3","edges":[[0,1],[0,2],[1,2]],"discriminant":"3"},
                                          [(0,)*graph.n,(0,)*graph.n]) if trace.states_visited==1 else None)
        verdict,payload=amp_core.reduce_state(graph,matrix,budget)
        assert verdict=="unknown" and trace.states_visited==3 and trace.moves["L1a"]==1
    finally:
        for name,value in saved.items():setattr(amp_core,name,value)
    RESULTS.append({"control":"L3 visits both children","reason":"unknown then contradiction visits both and leaves parent unknown"})
    with tempfile.TemporaryDirectory(prefix="selftest-",dir=SCRATCH) as tmp:
        tmp=Path(tmp);inp=tmp/"in.g6";out=tmp/"out.jsonl";unknown=tmp/"unknown.g6";empty=tmp/"empty.json"
        inp.write_text(codes[0]+"\n"+named["prism"]+"\n");empty.write_text("[]\n")
        args=[str(inp),"--out",str(out),"--unknown",str(unknown),"--forbidden",str(empty),"--methods","null","--time-limit","0.4"]
        with contextlib.redirect_stdout(io.StringIO()):producer.main(args)
        saved=out.read_bytes();records=[json.loads(s) for s in saved.splitlines()]
        assert len(records)==2 and records[0]["verdict"]=="refuted" and records[1]["verdict"]=="unknown"
        unknown.write_text("wrong\n")
        with out.open("ab") as handle:handle.write(b'{"g6":')
        with contextlib.redirect_stdout(io.StringIO()):producer.main(args)
        assert out.read_bytes()==saved and unknown.read_text()==named["prism"]+"\n"
        altered=args.copy();altered[-1]="0.5"
        expect_reason("resume changed budget",lambda:producer.main(altered),"resume configuration or source changed")
        bad=copy.deepcopy(records);bad[0]["g6"]=named["prism"]
        out.write_text("\n".join(json.dumps(r) for r in bad)+"\n")
        expect_reason("resume altered graph",lambda:producer.main(args),"coverage or order mismatch")
        out.write_bytes(saved)
        # Simulate a durable checkpoint followed by a main-process interruption.
        out.write_text(json.dumps(records[0])+"\n")
        Path(str(out)+".pending.json").write_text(json.dumps({"g6":named["prism"]})+"\n")
        with contextlib.redirect_stdout(io.StringIO()):producer.main(args)
        recovered=[json.loads(line) for line in out.read_text().splitlines()]
        assert len(recovered)==2 and "recovered on resume" in recovered[1]["cert"]["reason"]
        assert unknown.read_text()==named["prism"]+"\n"
        RESULTS.append({"control":"interrupted main-process recovery","reason":"pending graph becomes unknown, coverage remains exact"})
        # Explicit known records must be accepted, and self cycles rejected.
        knownpath=tmp/"known.jsonl"
        knownpath.write_text(json.dumps(known[codes[0]])+"\n")
        assert list(producer.load_known(knownpath,[]))==[codes[0]]
        bad=copy.deepcopy(known[codes[0]])
        bad["cert"]={"type":"tu","steps":[],"end":{"refuted":codes[0],"map":list(range(4))}}
        knownpath.write_text(json.dumps(bad)+"\n")
        expect_reason("known pointer cycle",lambda:producer.load_known(knownpath,[]),"pointer cycle")
    positives={"tree":known[codes[0]],"null":{"g6":codes[1],"verdict":"refuted","cert":null},
               "real-sos":{"g6":codes[0],"verdict":"refuted","cert":real},
               "real-sturm":{"g6":codes[4],"verdict":"refuted","cert":sturm},
               "tu":{"g6":code,"verdict":"refuted","cert":cert if cert else tu[1]}}
    positives["tu"]["cert"]=tu[1]
    for name,record in positives.items():
        (output_root/"fixtures"/("positive-"+name+".json")).write_text(json.dumps(record,sort_keys=True)+"\n")
    import sympy,flint
    result={"status":"PASS","controls":RESULTS,"count":len(RESULTS),
            "environment":{"sympy":sympy.__version__,"flint":flint.__version__,"SYMPY_GROUND_TYPES":os.environ["SYMPY_GROUND_TYPES"],
                           "nice":os.getpriority(os.PRIO_PROCESS,0),"RLIMIT_AS":resource.getrlimit(resource.RLIMIT_AS)},"argv":sys.argv}
    (output_root/"evidence/selftest.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
