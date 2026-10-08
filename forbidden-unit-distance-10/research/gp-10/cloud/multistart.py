"""Second independent numeric search (triage only): random-start least squares on all coordinates."""
import sys, json, itertools
import numpy as np, networkx as nx
from scipy.optimize import least_squares
for line in open(sys.argv[1]):
    g=line.strip()
    if not g: continue
    G=nx.from_graph6_bytes(g.encode()); E=list(G.edges()); n=G.number_of_nodes()
    rng=np.random.default_rng(int.from_bytes(g.encode(),'little')%(2**32)); best=(0.0,None)
    def res(x):
        P=x.reshape(n,2); return np.array([np.sum((P[u]-P[v])**2)-1 for u,v in E])
    for s in range(int(sys.argv[2]) if len(sys.argv)>2 else 600):
        r=least_squares(res,rng.normal(size=2*n)*rng.uniform(0.6,1.8),xtol=1e-15,ftol=1e-15,gtol=1e-15,max_nfev=2000)
        if max(abs(res(r.x)))<1e-10:
            P=r.x.reshape(n,2)
            md=min(np.linalg.norm(P[u]-P[v]) for u,v in itertools.combinations(range(n),2))
            if md>best[0]: best=(md,P.tolist())
    print(json.dumps({'g6':g,'best_min_distance':best[0],'coords':best[1]}),flush=True)
