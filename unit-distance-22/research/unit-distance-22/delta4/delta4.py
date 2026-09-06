#!/usr/bin/env python3
"""The delta = 4 case of (22,61): every (22,61) UDG with a degree-4 vertex v has G - v a
(21,57) UDG, hence one of the five known extremal graphs (AMP Theorem 1(c)). Enumerate all
degree-4 extensions of those five, canonicalise, deduplicate, and filter (F-free, TU).
Output: children-raw count, children-canonical count, filter verdict histogram, survivors."""
import itertools, subprocess, json, collections, sys, os
import networkx as nx
HERE=os.path.dirname(os.path.abspath(__file__))
known=[l.strip() for l in open(os.path.join(HERE,'..','sources','amp','anc','graph6.txt')) if l.strip()]
parents=[g for g in known if nx.from_graph6_bytes(g.encode()).number_of_nodes()==21]
assert len(parents)==5, len(parents)
children=[]
for g6 in parents:
    G=nx.from_graph6_bytes(g6.encode()); assert G.number_of_edges()==57
    for S in itertools.combinations(range(21),4):
        H=G.copy(); H.add_node(21); H.add_edges_from((21,s) for s in S)
        children.append(nx.to_graph6_bytes(H, header=False).decode().strip())
print('raw children:', len(children), file=sys.stderr)
raw=os.path.join(HERE,'children-raw.g6'); open(raw,'w').write('\n'.join(children)+'\n')
canon=subprocess.run(['nauty-labelg','-q',raw],capture_output=True,text=True,check=True).stdout.split()
uniq=sorted(set(canon)); print('canonical distinct children:', len(uniq), file=sys.stderr)
open(os.path.join(HERE,'children-22-61.g6'),'w').write('\n'.join(uniq)+'\n')
out=subprocess.run([os.path.join(HERE,'..','filter','udfilter')],input='\n'.join(uniq)+'\n',capture_output=True,text=True,check=True).stdout
recs=[json.loads(l) for l in out.splitlines() if l.strip()]
hist=collections.Counter(r['verdict'] for r in recs); print('verdicts:', dict(hist), file=sys.stderr)
open(os.path.join(HERE,'filter-verdicts.jsonl'),'w').write(out)
surv=[r['g6'] for r in recs if r['verdict']=='pass']
open(os.path.join(HERE,'survivors-22-61.g6'),'w').write('\n'.join(surv)+('\n' if surv else ''))
json.dump({'parents':5,'raw_children':len(children),'canonical_children':len(uniq),'verdicts':dict(hist),'survivors':len(surv)}, open(os.path.join(HERE,'summary.json'),'w'), indent=1)
print('survivors (pass both filters):', len(surv), file=sys.stderr)
