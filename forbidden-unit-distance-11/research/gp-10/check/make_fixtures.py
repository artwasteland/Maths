#!/usr/bin/env python3
"""Build small independent positive certificates and one-field mutations only."""
import copy
from fractions import Fraction as Q
import itertools
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import networkx as nx
import sympy as sp
import gp10check as ck

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
FIX.mkdir(exist_ok=True)
CASES = []


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def jsonl(path, records):
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records))


def canon(n, edges):
    graph = ck.Graph(n, set(tuple(sorted(e)) for e in edges))
    code = ck.canonical(graph)
    target = ck.decode(code)
    m = next(nx.algorithms.isomorphism.GraphMatcher(graph.nx(), target.nx()).isomorphisms_iter())
    return code, m


def exact(n, edges, coords, poly=None, interval=None):
    poly = [0, 1] if poly is None else poly
    interval = ["-1", "1"] if interval is None else interval
    code, m = canon(n, edges)
    d = len(poly) - 1
    arranged = [None] * n
    for i, xy in enumerate(coords):
        arranged[m[i]] = [[str(Q(a)) for a in list(p) + [0] * (d - len(p))] for p in xy]
    return {"g6": code, "verdict": "embedded", "cert": {"type": "exact", "field": {"minpoly": poly, "interval": interval}, "coords": arranged}}


def positive(name, record):
    path = FIX / (name + ".json")
    write(path, record)
    CASES.append({"name": name, "kind": "record", "file": path.name, "status": "ACCEPT"})
    return record


def red(name, base_name, base, path, value, reason):
    mutated = copy.deepcopy(base)
    obj = mutated
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value
    target = FIX / (name + ".json")
    write(target, mutated)
    CASES.append({"name": name, "kind": "record", "file": target.name, "status": "REJECT", "reason": reason,
                  "positive": base_name + ".json", "mutation_path": path})


def sparse(expr, variables):
    p = sp.Poly(sp.expand(expr), *variables)
    return [[str(c), list(exps)] for exps, c in sorted(p.terms()) if c]


def singular_lift(gens, variables, red_control=False):
    # All powers have monomial bases; SymPy expands before crossing the tool boundary.
    terms = [str(sp.expand(g)).replace("**", "^") for g in gens]
    source = "ring r=0,(" + ",".join(map(str, variables)) + "),dp;\nshort=0;\n"
    source += "ideal I=" + ",".join(terms) + ";\nmatrix L=lift(I,ideal(1));\n"
    if red_control:
        source += "L[1,1]=L[1,1]+1;\n"
    source += 'matrix V=matrix(I)*L;\nif(V[1,1]==1){print("LIFT_IDENTITY_OK");}else{print("LIFT_IDENTITY_NO");}\n'
    source += 'for(int i=1;i<=nrows(L);i++){print("COFACTOR "+string(i)+":"+string(L[i,1]));}\nquit;\n'
    p = subprocess.run(["/usr/bin/Singular", "-q"], input=source, text=True, capture_output=True, timeout=90)
    marker = "LIFT_IDENTITY_OK" in p.stdout.splitlines()
    if red_control:
        assert not marker and "LIFT_IDENTITY_NO" in p.stdout.splitlines(), p.stdout
        print("PASS Singular wrapper one-coefficient red control: LIFT_IDENTITY_NO")
        return
    assert marker, p.stdout + p.stderr
    rows = [line.split(":", 1)[1] for line in p.stdout.splitlines() if line.startswith("COFACTOR ")]
    assert len(rows) == len(gens), p.stdout
    (FIX / "singular-lift.sing").write_text(source)
    (FIX / "singular-lift.stdout").write_text(p.stdout)
    print("PASS Singular wrapper positive: LIFT_IDENTITY_OK")
    return [sp.sympify(row.replace("^", "**"), locals={str(v): v for v in variables}) for row in rows]


def null_record(n, edges, frame, sat=(), wrapper_red=False):
    code, m = canon(n, edges)
    frame = [m[v] for v in frame]
    sat = [sorted(m[v] for v in p) for p in sat]
    a, b = frame
    names = [f"{axis}_{i}" for i in range(n) if i not in (a,b) for axis in ("x", "y")]
    names += [f"t_{i}" for i in range(len(sat))]
    variables = tuple(sp.Symbol(name) for name in names)
    syms = dict(zip(names, variables))
    points = {a: (sp.Integer(0), sp.Integer(0)), b: (sp.Integer(1), sp.Integer(0))}
    points.update({i: (syms[f"x_{i}"], syms[f"y_{i}"]) for i in range(n) if i not in (a,b)})
    def dist(u,v):
        return sp.expand(sum((points[u][k]-points[v][k])**2 for k in (0,1)))
    gens = {f"e:{u},{v}": dist(u,v)-1 for u,v in sorted(ck.decode(code).edges) if (u,v) != tuple(sorted(frame))}
    for k,(u,v) in enumerate(sat):
        gens[f"s:{u},{v}"] = sp.expand(syms[f"t_{k}"]*dist(u,v)-1)
    cofs = singular_lift(list(gens.values()), variables)
    if wrapper_red:
        singular_lift(list(gens.values()), variables, True)
    cert = {"type": "null", "frame": frame, "sat": sat,
            "cofactors": {key: sparse(c, variables) for key,c in zip(gens, cofs)},
            "system": {key: sparse(g, variables) for key,g in gens.items()}}
    return {"g6": code, "verdict": "refuted", "cert": cert}, variables, cofs


def tree_collision(n, edges, collision):
    code,m = canon(n, edges)
    graph = ck.decode(code)
    rows, seen = [], set()
    for vs in itertools.combinations(range(n),4):
        for tail in itertools.permutations(vs[1:]):
            cycle=(vs[0],)+tail
            if cycle[1]>cycle[-1] or not all(tuple(sorted((cycle[i],cycle[(i+1)%4]))) in graph.edges for i in range(4)):
                continue
            row=[0]*n
            for i,v in enumerate(cycle): row[v] += (-1)**i
            key=min(tuple(row),tuple(-a for a in row))
            if key not in seen: seen.add(key); rows.append(row)
    witness={"field":{"minpoly":[0,1],"interval":[-1,1]},"tree":{"edges":[list(e) for e in sorted(graph.edges)],"A":rows,
             "move":{"kind":"L1a","pair":[m[v] for v in collision]},"children":[]}}
    return {"g6":code,"verdict":"refuted","cert":{"type":"tree","witness":witness}}


def run_fixture(name, records, hosts=None, **options):
    path = FIX / name
    path.mkdir(exist_ok=True)
    frozen = sorted({r["g6"] for r in records})
    (path / "input.g6").write_text("".join(c+"\n" for c in frozen))
    (path / "UNKNOWN.g6").write_text("".join(sorted(r["g6"]+"\n" for r in records if r["verdict"]=="unknown")))
    jsonl(path / "records.jsonl", records)
    manifest = {"profile":"sample", "input":"input.g6", "input_sha256":ck.digest(path/"input.g6"), "records":["records.jsonl"], **options}
    if hosts is not None:
        jsonl(path / "hosts.jsonl", hosts)
        manifest["hosts"]="hosts.jsonl"
    write(path / "run.json", manifest)
    return path


def main():
    c4 = positive("c4", exact(4,[(0,1),(1,2),(2,3),(3,0)], [([0],[0]),([1],[0]),([1],[1]),([0],[1])]))
    triangle = positive("triangle", exact(3,[(0,1),(0,2),(1,2)],[([0],[0]),([1],[0]),([Q(1,2)],[0,Q(1,2)])],[-3,0,1],["1","2"]))
    # Two rhombi sharing their bottom vertex, rotated so their top vertices are unit apart.
    s3=[0,Q(-5,4),0,Q(1,16)]; s11=[0,Q(9,4),0,Q(-1,16)]; s33=[-7,0,Q(1,2),0]
    def scale(p,c): return [a*c for a in p]
    def add(p,q): return [(p[i] if i<len(p) else 0)+(q[i] if i<len(q) else 0) for i in range(max(len(p),len(q)))]
    coords=[([0],[0]),([Q(1,2)],scale(s3,Q(1,2))),([-Q(1,2)],scale(s3,Q(1,2))),([0],s3),
            (add([Q(5,12)],scale(s33,-Q(1,12))),add(scale(s11,Q(1,12)),scale(s3,Q(5,12)))),
            (add([-Q(5,12)],scale(s33,-Q(1,12))),add(scale(s11,-Q(1,12)),scale(s3,Q(5,12)))),
            (scale(s33,-Q(1,6)),scale(s3,Q(5,6)))]
    moser=positive("moser",exact(7,[(0,1),(0,2),(1,2),(1,3),(2,3),(0,4),(0,5),(4,5),(4,6),(5,6),(3,6)],coords,[64,0,-28,0,1],["5","6"]))
    red("coordinate-perturbed","c4",c4,["cert","coords",0,0,0],"7/3","edge_equation")
    graph=ck.decode(c4["g6"])
    u,v=next(p for p in itertools.combinations(range(4),2) if p not in graph.edges)
    red("collision-edges-fine","c4",c4,["cert","coords",v],c4["cert"]["coords"][u],"exact_collision")
    red("interval-no-sign","triangle",triangle,["cert","field","interval"],["2","3"],"interval_sign_change")
    red("unknown-record-field","c4",c4,["unexpected"],1,"schema")
    for verdict in ("tu","pass","forbidden"):
        red("verdict-"+verdict,"c4",c4,["verdict"],verdict,"verdict_allowlist")
    k4tree=positive("k4-tree",tree_collision(4,list(itertools.combinations(range(4),2)),[0,1]))
    red("tree-collision-pair","k4-tree",k4tree,["cert","witness","tree","move","pair"],[0,0],"tree")
    k23edges=[(u,v) for u in range(2) for v in range(2,5)]
    k23tree=positive("k23-tree",tree_collision(5,k23edges,[2,3]))
    kn,variables,cofs = null_record(5,list(itertools.combinations(range(4),2)),[0,1],wrapper_red=True)
    positive("k4-isolate-null",kn)
    kg=ck.decode(kn["g6"])
    nonedge=list(next(p for p in itertools.combinations(range(5),2) if p not in kg.edges))
    red("frame-nonedge","k4-isolate-null",kn,["cert","frame"],nonedge,"frame_not_edge")
    badsystem=copy.deepcopy(kn["cert"]["system"])
    badsystem[f"e:{nonedge[0]},{nonedge[1]}"]=[["1",[0]*len(variables)]]
    red("extra-nonedge-generator","k4-isolate-null",kn,["cert","system"],badsystem,"system_mismatch")
    key=next(k for k,v in kn["cert"]["cofactors"].items() if v)
    red("cofactor-coefficient","k4-isolate-null",kn,["cert","cofactors",key,0,0],str(Q(kn["cert"]["cofactors"][key][0][0])+1),"cofactor_identity")
    real=copy.deepcopy(kn); real["cert"]["type"]="real"
    f=variables[0]**2+1
    real["cert"]["cofactors"]={key:sparse(c*f,variables) for key,c in zip(kn["cert"]["cofactors"],cofs)}
    real["cert"]["f"]=sparse(f,variables)
    real["cert"]["sos"]={"c":"1","squares":[["1",sparse(variables[0],variables)]]}
    positive("k4-real-sos",real)
    red("sos-zero-constant","k4-real-sos",real,["cert","sos","c"],"0","sos_constant_positive")
    red("sos-negative-weight","k4-real-sos",real,["cert","sos","squares",0,0],"-1","sos_weight_positive")
    red("sos-wrong-square","k4-real-sos",real,["cert","sos","squares",0,1],sparse(variables[0]+1,variables),"sos_identity")
    sturm=copy.deepcopy(real); del sturm["cert"]["sos"]; sturm["cert"]["sturm"]=str(variables[0])
    positive("k4-real-sturm",sturm)
    red("sturm-wrong-variable","k4-real-sturm",sturm,["cert","sturm"],str(variables[1]),"sturm_multivariate")
    k23null,_,_ = null_record(5,k23edges,[0,2],[(0,1),(2,3),(2,4),(3,4)])
    positive("k23-saturated-null",k23null)
    skey=next(k for k,v in k23null["cert"]["cofactors"].items() if k.startswith("s:") and v)
    red("saturation-cofactor","k23-saturated-null",k23null,["cert","cofactors",skey],[],"cofactor_identity")
    # The second gadget uses the first newly forced edge, then completes a K4.
    gadget=ck.read_json(ck.TRUSTED/"data/tu-gadgets.json")[0]
    first=list(range(6)); second=[1,5,6,7,8,9]
    edges=set(tuple(e) for e in gadget["edges"])
    edges.update(tuple(sorted((second[u],second[v]))) for u,v in gadget["edges"] if (u,v)!=(0,1))
    edges.update((min(u,v),max(u,v)) for u,v in itertools.combinations([5,9,10,11],2) if {u,v}!={5,9})
    code,m=canon(12,edges)
    steps=[{"gadget":0,"map":[m[v] for v in arr],"pair":[m[arr[v]] for v in gadget["pair"]]} for arr in (first,second)]
    checker=ck.Checker()
    final=ck.decode(code); final.edges.update(tuple(sorted(s["pair"])) for s in steps)
    index=0
    gm=nx.algorithms.isomorphism.GraphMatcher(final.nx(),checker.forbidden[index].nx())
    inv=next(gm.subgraph_monomorphisms_iter()); fmap=[next(u for u,v in inv.items() if v==j) for j in range(checker.forbidden[index].n)]
    tu={"g6":code,"verdict":"refuted","cert":{"type":"tu","steps":steps,"end":{"forbidden":index,"map":fmap}}}
    positive("tu-chain",tu)
    badmap=next(list(p) for p in itertools.permutations(range(12),len(fmap)) if not all(tuple(sorted((p[u],p[v]))) in final.edges for u,v in checker.forbidden[0].edges))
    red("tu-final-edge","tu-chain",tu,["cert","end","map"],badmap,"map_not_edge_preserving")
    red("tu-future-edge","tu-chain",tu,["cert","steps"],list(reversed(steps)),"map_not_edge_preserving")
    red("tu-already-edge","tu-chain",tu,["cert","steps"],[steps[0],steps[0]],"tu_pair_already_edge")
    badpair=[m[0],m[2]]
    red("tu-wrong-pair","tu-chain",tu,["cert","steps",0,"pair"],badpair,"tu_distinguished_pair")
    # Run-level controls use genuine certificates. Children deliberately precede targets.
    edge=exact(2,[(0,1)],[([0],[0]),([1],[0])])
    eptr={"g6":edge["g6"],"verdict":"embedded","cert":{"type":"super","g6":triangle["g6"],"map":[0,1]}}
    run_fixture("pointers",[eptr],hosts=[triangle])
    run_fixture("mixed",[c4,moser,k4tree])
    run_fixture("unknown",[{"g6":edge["g6"],"verdict":"unknown","cert":{"reason":"fixture budget exhausted","budget":{"seconds":0}}}])
    source=ck.decode(k4tree["g6"]); target=ck.decode(kn["g6"])
    im=next(nx.algorithms.isomorphism.GraphMatcher(target.nx(),source.nx()).subgraph_monomorphisms_iter())
    rmap=[next(u for u,v in im.items() if v==j) for j in range(source.n)]
    rptr={"g6":kn["g6"],"verdict":"refuted","cert":{"type":"sub","g6":k4tree["g6"],"map":rmap}}
    run_fixture("refutation-pointer",[rptr,k4tree])
    indexed=copy.deepcopy(rptr); indexed["cert"]["index"]=0
    run_fixture("frozen-pointer",[indexed])
    tu_ref=copy.deepcopy(tu)
    im=next(nx.algorithms.isomorphism.GraphMatcher(final.nx(),source.nx()).subgraph_monomorphisms_iter())
    tu_ref["cert"]["end"]={"refuted":k4tree["g6"],"map":[next(u for u,v in im.items() if v==j) for j in range(source.n)]}
    run_fixture("tu-refuted-pointer",[tu_ref,k4tree])
    supercode,sm=canon(5,k23edges+[(0,1)])
    subsource=ck.decode(k23tree["g6"]); supergraph=ck.decode(supercode)
    im=next(nx.algorithms.isomorphism.GraphMatcher(supergraph.nx(),subsource.nx()).subgraph_monomorphisms_iter())
    superrecord={"g6":supercode,"verdict":"refuted","cert":{"type":"sub","g6":k23tree["g6"],"map":[next(u for u,v in im.items() if v==j) for j in range(5)]}}
    path=run_fixture("minimality",[superrecord,k23tree],forbidden_limit=4,derive=True,minimal_claim="claim.g6")
    (path/"claim.g6").write_text(k23tree["g6"]+"\n")
    supertree=tree_collision(5,k23edges+[(0,1)],[2,3])
    conditional_records=[supertree,{"g6":k23tree["g6"],"verdict":"unknown","cert":{"reason":"conditional fixture, no search","budget":{"seconds":0}}}]
    run_fixture("conditional-minimality",conditional_records,forbidden_limit=4,derive=True)
    # Include a requested, independently searched monotonicity comparison.
    mixed=FIX/"mixed"
    jsonl(mixed/"cross.jsonl",[{"refuted":k4tree["g6"],"embedded":moser["g6"]}])
    manifest=ck.read_json(mixed/"run.json");manifest["cross_checks"]="cross.jsonl";write(mixed/"run.json",manifest)
    run_cases=[]
    def run_red(name, positive_name, filename, mutate, reason, record_reason=None):
        source=FIX/positive_name; destination=FIX/name
        if destination.exists(): shutil.rmtree(destination)
        shutil.copytree(source,destination)
        old=(source/filename).read_text()
        new=mutate(old)
        assert new!=old
        (destination/filename).write_text(new)
        run_cases.append({"name":name,"positive":positive_name,"changed_file":filename,"reason":reason,"record_reason":record_reason})
    def mutate_jsonl(raw,path,value):
        records=[json.loads(x) for x in raw.splitlines()]
        obj=records
        for k in path[:-1]: obj=obj[k]
        obj[path[-1]]=value
        return "".join(json.dumps(r,separators=(",",":"))+"\n" for r in records)
    run_red("pointer-noninjective","pointers","records.jsonl",lambda s:mutate_jsonl(s,[0,"cert","map"],[0,0]),"records_rejected","map_not_injective")
    run_red("pointer-cycle","pointers","records.jsonl",lambda s:mutate_jsonl(s,[0,"cert","g6"],edge["g6"]),"records_rejected","pointer_cycle")
    run_red("pointer-missing","pointers","hosts.jsonl",lambda s:"","records_rejected","pointer_target_missing")
    run_red("coverage-missing","mixed","records.jsonl",lambda s:"\n".join(s.splitlines()[1:])+"\n","coverage")
    run_red("coverage-extra","mixed","records.jsonl",lambda s:s+json.dumps(edge)+"\n","coverage")
    run_red("coverage-duplicate","mixed","records.jsonl",lambda s:s+s.splitlines()[0]+"\n","duplicate_record")
    conflict={"g6":c4["g6"],"verdict":"refuted","cert":k4tree["cert"]}
    run_red("verdict-conflict","mixed","records.jsonl",lambda s:s+json.dumps(conflict)+"\n","embedded_refuted_conflict")
    run_red("unknown-missing","unknown","UNKNOWN.g6",lambda s:"","unknown_exactness")
    run_red("unknown-extra","mixed","UNKNOWN.g6",lambda s:edge["g6"]+"\n","unknown_exactness")
    run_red("minimality-false-claim","minimality","claim.g6",lambda s:"".join(c+"\n" for c in sorted([supercode,k23tree["g6"]])),"minimality_claim_refuted_deletion")
    run_red("withheld-index","frozen-pointer","run.json",lambda s:json.dumps({**json.loads(s),"forbidden_limit":0})+"\n","records_rejected","forbidden_not_in_force")
    run_red("cross-check-wrong-verdict","mixed","cross.jsonl",lambda s:mutate_jsonl(s,[0,"refuted"],c4["g6"]),"cross_check_records")
    run_red("conditional-unknown-missing","conditional-minimality","UNKNOWN.g6",lambda s:"","unknown_exactness")
    write(FIX/"run-cases.json",run_cases)
    write(FIX/"cases.json",CASES)
    print("FIXTURES",len(CASES),"record cases")

if __name__=="__main__": main()
