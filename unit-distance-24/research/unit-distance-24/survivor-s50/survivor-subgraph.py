# Does the (24,69) slice-50 survivor contain any GP-11-refuted 11-vertex graph as a (not necessarily induced) subgraph?
# A non-unit-distance subgraph refutes the whole graph (an embedding restricts to every subgraph).
import sys, time
from multiprocessing import Pool
import igraph as ig
import networkx as nx
T6 = 'W@iiac_CA?O?GICD@C_HH?U?AWM@SE?i?GAh@?dWABT?OIr'
def to_ig(g6):
    g = nx.from_graph6_bytes(g6.encode())
    return ig.Graph(n=g.number_of_nodes(), edges=list(g.edges())), g
TARGET, TNX = to_ig(T6)
def test(g6):
    pat, pnx = to_ig(g6)
    t = time.time()
    res = TARGET.subisomorphic_lad(pat, induced=False, return_mapping=True)
    found, mapping = (res[0], res[1]) if isinstance(res, tuple) else (res, None)
    ok = None
    if found:
        m = mapping  # pattern vertex i -> target vertex m[i] (LAD's mapping for the pattern)
        ok = len(set(m)) == pat.vcount() and all(TNX.has_edge(m[u], m[v]) for u, v in pnx.edges())
    return g6, bool(found), ok, round(time.time() - t, 2)
if __name__ == '__main__':
    pats = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    print('target n', TARGET.vcount(), 'e', TARGET.ecount(), 'patterns', len(pats), flush=True)
    hits, slow = [], []
    with Pool(int(sys.argv[2])) as pool:
        for g6, found, ok, sec in pool.imap_unordered(test, pats):
            if found: hits.append((g6, ok)); print('HIT', g6, 'verified' if ok else 'MAPPING CHECK FAILED', sec, flush=True)
            if sec > 60: slow.append((g6, sec))
    print('done: hits', len(hits), 'verified', sum(1 for _, ok in hits if ok), 'slow(>60s)', slow, flush=True)
