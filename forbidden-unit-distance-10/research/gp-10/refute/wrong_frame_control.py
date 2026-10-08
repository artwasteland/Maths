#!<repo>/pyenv-gp10/bin/python
"""Deliberately disable framing validation only inside an isolated red fixture."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import copy
import itertools
import json
import time
from fractions import Fraction
import networkx as nx
from graphs import MODULE,decode,encode,kernel
from gp10refute import configure,timed
from algebra import algebra_search,system,unsparse,verify_algebra

def main():
    configure();started=time.monotonic()
    code=json.loads((MODULE/"fixtures/named.json").read_text())["prism"]
    target=nx.from_graph6_bytes(code.encode())
    mapping=next(nx.algorithms.isomorphism.GraphMatcher(nx.circular_ladder_graph(5),target).isomorphisms_iter())
    good_frame=[mapping[0],mapping[5]]
    bad_frame=[mapping[0],mapping[7]]
    # theta=sin(72 degrees). Rotated pentagon vertices, then translated by (1,0).
    zero=["0"]*4
    base=[(zero,zero),(zero,["-1","0","0","0"]),
          (["0","1","0","0"],["1/2","0","-2","0"]),
          (["0","-2","0","4"],["-1/2","0","0","0"]),
          (["0","1","0","0"],["-3/2","0","2","0"])]
    coords=[None]*10
    for i,(x,y) in enumerate(base):
        coords[mapping[i]]=[x.copy(),y.copy()]
        translated=x.copy();translated[0]=str(Fraction(translated[0])+1)
        coords[mapping[i+5]]=[translated,y.copy()]
    field={"minpoly":[5,0,-20,0,16],"interval":["19/20","24/25"]}
    witness={"field":field,"coordinates":coords}
    k=kernel();graph=k.decode_graph6(code)
    k.verify_embedding(graph,witness,"prism-positive")
    K=k.RealField(field,"prism-field")
    points=[(K.parse(x,"x"),K.parse(y,"y")) for x,y in coords]
    distances={}
    for u,v in itertools.combinations(range(10),2):
        dx=points[u][0]-points[v][0];dy=points[u][1]-points[v][1]
        d=dx*dx+dy*dy
        assert K.sign(d)>0
        distances[(u,v)]=d
    assert points[good_frame[0]]==(K.zero,K.zero)
    assert points[good_frame[1]]==(K.one,K.zero)
    altered=copy.deepcopy(witness)
    altered["coordinates"][good_frame[0]][0][0]="1"
    try:k.verify_embedding(graph,altered,"prism-coordinate-mutation")
    except Exception as exc:
        assert "collide" in str(exc)
        embedding_red_reason=str(exc)
    else:raise AssertionError("coincident-point mutation accepted")
    n,edges=decode(code)
    augmented=encode(n,set(edges)|{tuple(sorted(bad_frame))})
    # This is a genuine null certificate for the augmented labelled graph.
    with timed(8):
        cert,detail=algebra_search(augmented,"null",8,frame=bad_frame)
    assert cert is not None,detail
    verify_algebra(augmented,cert)
    good={"frame":good_frame,"sat":cert["sat"]}
    system(code,**good)
    for u,v in cert["sat"]:
        d=distances[(u,v)]
        assert d.inverse()*d==K.one
    changed=copy.deepcopy(good);changed["frame"]=bad_frame
    assert good["sat"]==changed["sat"]
    try:system(code,**changed)
    except Exception as exc:
        assert "frame: not an edge" in str(exc)
        guard_reason=str(exc)
    else:raise AssertionError("production frame guard accepted nonedge")
    # Emulate only the forbidden bug. These are exactly the prism generators
    # with the frame guard disabled. No nonedge equation is explicitly inserted.
    ctx,_,gens=system(code,**changed,allow_nonedge=True)
    unsafe_identity=sum((unsparse(ctx,p)*gens[name] for name,p in cert["cofactors"].items()),ctx.constant(0))
    assert unsafe_identity==ctx.constant(1)
    bad_record={"g6":code,"verdict":"refuted","cert":cert}
    try:verify_algebra(code,cert)
    except Exception as exc:
        assert "frame: not an edge" in str(exc)
        certificate_reason=str(exc)
    else:raise AssertionError("false prism certificate accepted")
    # A soundness harness expecting unknown would go red under this mutation.
    try:assert bad_record["verdict"]!="refuted","soundness bug: prism refuted after wrong frame"
    except AssertionError as exc:outer_reason=str(exc)
    else:raise AssertionError("deliberate wrong-frame bug did not trigger control")
    exact={"g6":code,"verdict":"embedded","cert":{"type":"exact","field":field,"coords":coords}}
    (MODULE/"fixtures/prism-exact-control.json").write_text(json.dumps(exact,sort_keys=True)+"\n")
    (MODULE/"fixtures/red-prism-nonedge-frame.json").write_text(json.dumps(bad_record,sort_keys=True)+"\n")
    result={"status":"PASS","g6":code,"good_frame":good_frame,"mutated_frame":bad_frame,
            "sat_unchanged":True,"embedding_edges_exact":True,"distinct_pairs_positive":len(distances),
            "positive_system_has_exact_real_point":True,"unsafe_identity_equals_one":True,
            "production_guard_reason":guard_reason,"certificate_rejection_reason":certificate_reason,
            "outer_soundness_red_reason":outer_reason,"embedding_mutation_reason":embedding_red_reason,
            "false_refutation_emitted_by_producer":False,"seconds":time.monotonic()-started,"argv":sys.argv}
    (MODULE/"evidence/wrong-frame.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
