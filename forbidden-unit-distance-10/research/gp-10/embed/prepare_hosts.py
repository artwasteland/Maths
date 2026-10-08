"""Compile reusable exact host fields under explicit per-host deadlines."""
import json
import sys
import time
from pathlib import Path
from gp10embed import limits,timer,StageTimeout
from hosts import database,expression,HERE
from algebraic import certificate
from exact import verify

def main():
    import networkx as nx
    limits();db=database();results={};stats=[]
    for name in ('G27','AMP33','G118'):
        start=time.monotonic();meta={'host':name,'vertices':db[name]['size'],'edges':len(db[name]['edges']),'limit_seconds':60}
        try:
            with timer(60):
                points=[tuple(expression(v) for v in pt) for pt in db[name]['expressions']]
                candidate=certificate(points)
                graph=nx.Graph();graph.add_nodes_from(range(len(points)));graph.add_edges_from(db[name]['edges'])
                code=nx.to_graph6_bytes(graph,header=False).decode().strip()
                results[name]=verify(code,candidate)
                meta['status']='certified';meta['degree']=len(candidate['field']['minpoly'])-1
        except StageTimeout:meta['status']='timeout'
        except Exception as exc:meta['status']=type(exc).__name__+':'+str(exc)
        meta['seconds']=time.monotonic()-start;stats.append(meta)
        (HERE/'host_certificates.json').write_text(json.dumps(results,sort_keys=True)+'\n')
        (HERE/'host-preparation.json').write_text(json.dumps(stats,indent=2)+'\n')
        print(json.dumps(meta),flush=True)
if __name__=='__main__':main()
