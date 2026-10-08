"""Compile the subhost using only sqrt(3), sqrt(11) and sqrt(33)."""
import ast
import copy
import json
import time
from pathlib import Path
import networkx as nx
from gp10embed import limits,timer
from algebraic import certificate
from hosts import expression,HERE
from exact import verify,rational,textq,CertificateError

def main():
    limits();started=time.monotonic()
    source=HERE/'host_sources.json';raw=json.loads(source.read_text());original=raw['hosts']['G118']
    def simple(s):
        for node in ast.walk(ast.parse(s,mode='eval')):
            if isinstance(node,ast.Call) and getattr(node.func,'id',None)=='sqrt':
                if len(node.args)!=1 or not isinstance(node.args[0],ast.Constant) or node.args[0].value not in (3,11,33):return False
        return True
    indices=[i for i,pt in enumerate(original) if all(simple(s) for s in pt)]
    exprs=[original[i] for i in indices]
    with timer(60):
        points=[tuple(expression(s) for s in p) for p in exprs]
        numeric=[tuple(expression(s,True) for s in p) for p in exprs]
        import mpmath as mp
        edges=[(u,v) for v in range(len(points)) for u in range(v) if abs(sum((numeric[u][k]-numeric[v][k])**2 for k in (0,1))-1)<mp.mpf('1e-40')]
        graph=nx.Graph();graph.add_nodes_from(range(len(points)));graph.add_edges_from(edges)
        code=nx.to_graph6_bytes(graph,header=False).decode().strip()
        cert=verify(code,certificate(points))
        bad=copy.deepcopy(cert);bad['coords'][0][0][0]=textq(rational(bad['coords'][0][0][0])+100)
        try:verify(code,bad)
        except CertificateError as exc:
            reason=str(exc);assert reason.startswith('edge:')
        else:raise AssertionError('host mutation accepted')
    raw['hosts']['G118_simple']=exprs;raw['provenance']['G118_simple_indices']=indices
    compiled=json.loads((HERE/'host_certificates.json').read_text());compiled['G118_simple']=cert
    source.write_text(json.dumps(raw,sort_keys=True)+'\n')
    (HERE/'host_certificates.json').write_text(json.dumps(compiled,sort_keys=True)+'\n')
    summary={'vertices':len(points),'edges':len(edges),'source_indices':indices,'degree':len(cert['field']['minpoly'])-1,
             'seconds':time.monotonic()-started,'limit_seconds':60,'status':'certified','mutation_reason':reason}
    (HERE/'g118-subset-preparation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
