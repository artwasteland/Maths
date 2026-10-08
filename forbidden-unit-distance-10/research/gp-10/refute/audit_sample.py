#!<repo>/pyenv-gp10/bin/python
"""Independent NetworkX monomorphism check of the selected B9 soundness sample."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import json
import time
from pathlib import Path
import networkx as nx
from gp10refute import configure
from graphs import MODULE,UD
configure()
start=time.monotonic()
codes=(MODULE/"fixtures/b9.g6").read_text().splitlines()
forbidden=[nx.Graph(edges) for edges in json.loads((UD/"data/forbidden-74.json").read_text())]
comparisons=0
for i,code in enumerate(codes):
    target=nx.from_graph6_bytes(code.encode())
    for pattern in forbidden:
        if len(pattern)>len(target) or pattern.number_of_edges()>target.number_of_edges():
            continue
        comparisons+=1
        assert not nx.algorithms.isomorphism.GraphMatcher(target,pattern).subgraph_is_monomorphic(),(i,code)
    if (i+1)%100==0:
        print(json.dumps({"checked":i+1}),flush=True)
result={"status":"PASS","count":len(codes),"comparisons":comparisons,"seconds":time.monotonic()-start,"argv":sys.argv}
(MODULE/"evidence/sample-audit.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
