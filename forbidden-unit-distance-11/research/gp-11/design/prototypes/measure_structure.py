from common import *
import json,collections,platform
from exact import graph6
start_monitor();t=time.monotonic();hist=collections.Counter();mind=collections.Counter();deg2=0;count=0
for c in (OUT/'B11.g6').read_text().splitlines():
 n,e=graph6(c);d=[0]*n
 for a,b in e:d[a]+=1;d[b]+=1
 hist[len(e)]+=1;mind[min(d)]+=1;deg2+=2 in d;count+=1
 if count%4096==0:memory()
import sympy,flint,numpy,scipy,networkx,pynauty
result={'graphs':count,'edge_counts':hist,'minimum_degrees':mind,'has_degree2':deg2,'seconds':time.monotonic()-t,'environment':{'python':platform.python_version(),'sympy':sympy.__version__,'flint':flint.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__,'networkx':networkx.__version__,'pynauty':pynauty.__version__},**usage()}
(OUT/'population-summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
