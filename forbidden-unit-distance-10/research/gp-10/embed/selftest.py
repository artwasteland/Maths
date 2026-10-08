"""Positive controls and one-field mutations, with exact reason assertions."""
import copy
import json
import os
from pathlib import Path
import signal
import time
import networkx as nx
from exact import verify,CertificateError,rational_certificate,graph6,adjacency
from gp10embed import run_one,main,limits,warm
from hosts import monomorphism,check_mapping

HERE=Path(__file__).resolve().parent
SCRATCH=Path('/tmp/gp10-embed/selftest')

def code(n,edges):
    g=nx.Graph();g.add_nodes_from(range(n));g.add_edges_from(edges)
    return nx.to_graph6_bytes(g,header=False).decode().strip()

def rejected(g,c,reason):
    try:verify(g,c)
    except CertificateError as exc:
        assert str(exc).startswith(reason),(str(exc),reason)
        return str(exc)
    raise AssertionError('mutation accepted')

def fault_callback(fixture):
    def callback(method,g,n,e,s,cap):
        if fixture['mode']=='crash':os._exit(23)
        if fixture['mode']=='timeout':
            signal.signal(signal.SIGALRM,signal.SIG_IGN)
            while True:time.sleep(0.01)
        if fixture['mode']=='exception':raise RuntimeError('injected')
        return rational_certificate([(0,0),(1,0),(2,0)]),{'reason':'fixture'}
    return callback

def run():
    limits();SCRATCH.mkdir(parents=True,exist_ok=True)
    checks=[]
    g=code(3,[(0,1),(1,2)]);base=rational_certificate([(0,0),(1,0),(2,0)])
    verify(g,base)
    bad=copy.deepcopy(base);bad['coords'][2][0][0]='0/1'
    checks.append({'control':'coincident points with exact edges','positive':'accepted','mutation':rejected(g,bad,'distinctness:0,2:zero')})
    bad=copy.deepcopy(base);bad['coords'][1][0][0]='3/2'
    checks.append({'control':'coordinate coefficient','positive':'accepted','mutation':rejected(g,bad,'edge:0,1')})
    bad=copy.deepcopy(base);bad['field']['interval']=['1/1','2/1']
    checks.append({'control':'sign interval','positive':'accepted','mutation':rejected(g,bad,'sign_change')})
    reducible={'type':'exact','field':{'minpoly':[0,-1,0,1],'interval':['-1/2','1/2']},
               'coords':[[['0/1']*3,['0/1']*3],[['1/1','1/1','0/1'],['0/1']*3]]}
    isolated=code(2,[]);verify(isolated,reducible)
    bad=copy.deepcopy(reducible);bad['coords'][1][0][0]='0/1'
    checks.append({'control':'distinctness at selected root of reducible polynomial','positive':'accepted','mutation':rejected(isolated,bad,'distinctness:0,1:interval')})
    quadratic={'type':'exact','field':{'minpoly':[-2,0,1],'interval':['1/1','2/1']},
               'coords':[[['0/1','0/1'],['0/1','0/1']],[['1/1','0/1'],['0/1','0/1']]]}
    edge=code(2,[(0,1)]);verify(edge,quadratic)
    bad=copy.deepcopy(quadratic);bad['field']['minpoly']=[1,0,1]
    checks.append({'control':'complex field','positive':'accepted','mutation':rejected(edge,bad,'sign_change')})
    pattern=adjacency(3,[(0,1),(1,2)]);host=adjacency(4,[(0,1),(0,2),(1,2)])
    mapping,_=monomorphism(pattern,host);assert mapping is not None
    assert check_mapping(pattern,host,mapping)
    for replacement,reason in ((mapping[1],'host_map:noninjective'),(3,'host_map:edge:0,1')):
        bad=mapping[:];bad[0]=replacement
        try:check_mapping(pattern,host,bad)
        except ValueError as exc:assert str(exc)==reason
        else:raise AssertionError('host map mutation accepted')
        checks.append({'control':'non-induced host map','positive':mapping,'mutation':reason})
    fixture={'mode':'positive'}
    r,_=run_one(g,1,('lattice18',),100,callback=fault_callback(fixture));assert r['verdict']=='embedded'
    for mode in ('crash','timeout','exception'):
        changed=dict(fixture,mode=mode)
        r,s=run_one(g,0.1,('lattice18',),100,callback=fault_callback(changed))
        assert r['verdict']=='unknown'
        if mode=='exception':
            reason=s['budget']['attempts'][0]['reason'];assert reason=='method_exception:RuntimeError:injected'
        else:
            reason=r['cert']['reason'];assert reason==('timeout' if mode=='timeout' else 'worker_crash')
        checks.append({'control':'worker '+mode,'positive':'embedded','mutation':reason})
    r1,_=run_one(g,1,('lattice18',),1000);r2,_=run_one(g,1,('lattice18',),1000)
    assert r1==r2 and r1['verdict']=='embedded'
    changed,_=run_one(g,1,('lattice18',),1)
    assert changed['verdict']=='unknown' and changed['cert']['budget']['attempts'][0]['reason']=='node_cap'
    checks.append({'control':'deterministic search and node budget','positive':'identical certificates','mutation':'node_cap'})
    source=SCRATCH/'input.g6';out=SCRATCH/'out.jsonl';unk=SCRATCH/'unknown.g6';stats=SCRATCH/'stats.jsonl'
    invalid='invalid!'
    source.write_text(g+'\n'+invalid+'\n'+edge+'\n')
    for p in (out,unk,stats):
        if p.exists():p.unlink()
    argv=[str(source),'--out',str(out),'--unknown',str(unk),'--time-limit','1','--methods','lattice18','--stats',str(stats)]
    main(argv);original=out.read_bytes();main(argv);assert out.read_bytes()==original
    assert json.loads(out.read_text().splitlines()[-1])['verdict']=='embedded'
    # One extra trailing fragment is the mutation of a genuine output.
    with out.open('ab') as f:f.write(b'{"g6":')
    main(argv)
    assert out.read_bytes()==original and unk.read_text()==invalid+'\n'
    checks.append({'control':'resume after partial last record','positive':'unchanged on resume','mutation':'fragment removed'})
    unk.write_text('stale\n');main(argv)
    assert out.read_bytes()==original and unk.read_text()==invalid+'\n'
    checks.append({'control':'unknown projection on resume','positive':'matches output','mutation':'stale projection repaired'})
    # A permissive numeric least-squares solve of K2,3 converges to three
    # equal circle intersections. It is deliberately run without repulsion
    # to exercise the residual-only failure mode, not to claim a production hit.
    from numeric import fit
    import numpy as np
    k23=code(5,[(0,2),(0,3),(0,4),(1,2),(1,3),(1,4)])
    _,edges=graph6(k23)
    initial=np.array([[0.,0.],[2.,0.],[1.,0.],[1.,1e-8],[1.,-1e-8]])
    positions,meta=fit(5,edges,7,1,False,initial)
    assert meta['residual']<1e-12,meta
    collapsed=rational_certificate([(0,0),(2,0),(1,0),(1,0),(1,0)])
    reason=rejected(k23,collapsed,'distinctness:2,3:zero')
    # Pair this red certificate with an actual exact positive by deleting
    # the two offending edges to vertex 4, then changing its x coordinate.
    positive_graph=code(5,[(0,2),(0,3),(1,2),(1,3)])
    positive={'type':'exact','field':{'minpoly':[-3,0,1],'interval':['1/1','2/1']},
      'coords':[[['0/1','0/1'],['0/1','0/1']],[['1/1','0/1'],['0/1','0/1']],
                [['1/2','0/1'],['0/1','1/2']],[['1/2','0/1'],['0/1','-1/2']],
                [['3/1','0/1'],['0/1','0/1']]]}
    verify(positive_graph,positive)
    bad=copy.deepcopy(positive);bad['coords'][4][0][0]='0/1'
    mutation=rejected(positive_graph,bad,'distinctness:0,4:zero')
    checks.append({'control':'numeric convergence does not certify','numeric':meta,'exact_refusal':reason,'positive':'accepted','mutation':mutation})
    from exact import rational,textq
    for method in ('constructive','host','numeric'):
        warm((method,))
        r,stats=run_one(g,8,(method,),2000)
        assert r['verdict']=='embedded',(method,stats)
        bad=copy.deepcopy(r['cert']);bad['coords'][0][0][0]=textq(rational(bad['coords'][0][0][0])+100)
        reason=rejected(g,bad,'edge:0,1')
        checks.append({'control':'production '+method,'positive':'embedded','mutation':reason})
    from unittest.mock import patch
    import gp10embed
    original_propose=gp10embed.propose
    def crash_one(method,c,n,e,seed,cap):
        if c==g:os._exit(23)
        return original_propose(method,c,n,e,seed,cap)
    source.write_text(g+'\n'+edge+'\n')
    for p in (out,unk):
        if p.exists():p.unlink()
    with patch('gp10embed.propose',crash_one):main(argv)
    rows=[json.loads(line) for line in out.read_text().splitlines()]
    assert rows[0]['cert']['reason']=='worker_crash' and rows[1]['verdict']=='embedded'
    checks.append({'control':'CLI continues after worker crash','positive':'same input passed earlier','mutation':'worker_crash followed by embedded'})
    result={'checks':checks,'passed':len(checks)}
    (HERE/'selftest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':run()
