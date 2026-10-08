from common import *
import numpy as np,scipy.sparse as ss,json,collections
from graph6 import canonicalize,decode_graph6,remove_edge,iter_edges
start_monitor();t=time.monotonic()
codes=(OUT/'B11.g6').read_text().splitlines();idx={g:i for i,g in enumerate(codes)};N=len(codes)
edges=np.fromfile(OUT/'relations.u32',dtype=np.uint32).reshape(-1,2)
a=ss.csr_matrix((np.ones(len(edges),dtype=np.uint8),(edges[:,0],edges[:,1])),shape=(N,N));b=a.transpose().tocsr()
assert a.nnz==len(edges)
(OUT/'population-poset.json').write_text(json.dumps({'n':N,'relations':a.nnz,'maxima':int(np.count_nonzero(b.indptr[1:]==b.indptr[:-1])),'minima':int(np.count_nonzero(a.indptr[1:]==a.indptr[:-1])),'csr_bytes':a.data.nbytes+a.indices.nbytes+a.indptr.nbytes,'max_children':int(np.diff(a.indptr).max()),'max_parents':int(np.diff(b.indptr).max()),'load_seconds':time.monotonic()-t,**usage()},indent=2))
# Check complete sets of one-edge neighbours for the 500 sampled parents against unmodified Python driver primitives.
sample=(OUT/'sample.g6').read_text().splitlines();s=time.monotonic();checks=0
for g in sample:
 i=idx[g];n,m=decode_graph6(g);actual={idx[c] for u,v in iter_edges(n,m) if (c:=canonicalize(n,remove_edge(n,m,u,v)).g6) in idx}
 assert actual==set(a.indices[a.indptr[i]:a.indptr[i+1]]),g;checks+=len(actual)
(OUT/'poset-validation.json').write_text(json.dumps({'sample_parents':500,'matching_relations':checks,'seconds':time.monotonic()-s}))
def reach(seeds,mat):
 seen=set(seeds);todo=list(seeds)
 for v in todo:
  for w in mat.indices[mat.indptr[v]:mat.indptr[v+1]]:
   if int(w) not in seen:seen.add(int(w));todo.append(int(w))
 return seen
rows=[]
for g in sample:
 i=idx[g];dn=reach([i],a);up=reach([i],b);n,mask=decode_graph6(g);degs=[0]*n
 for u,v in iter_edges(n,mask):degs[u]+=1;degs[v]+=1
 rows.append({'g6':g,'edges':mask.bit_count(),'degree2':degs.count(2),'direct_children':int(a.indptr[i+1]-a.indptr[i]),'direct_parents':int(b.indptr[i+1]-b.indptr[i]),'descendants_including_self':len(dn),'ancestors_including_self':len(up)})
(OUT/'propagation-per-sample.json').write_text(json.dumps(rows,indent=2))
# Read every currently finished method file; invalid/non-independent producer artifacts are excluded by caller conventions.
E=set();R=set();methods={}
for method in sys.argv[1:]:
 ee=set();rr=set()
 for line in open(OUT/(method+'-records.jsonl')):
  rec=json.loads(line);g=rec['g6'];v=rec['verdict']
  if v=='embedded':ee.add(idx[g])
  elif v=='refuted':rr.add(idx[g])
 E|=ee;R|=rr;methods[method]={'direct_E':len(ee),'direct_R':len(rr),'closure_E':len(reach(ee,a)),'closure_R':len(reach(rr,b))}
e=reach(E,a);r=reach(R,b);assert not e&r
(OUT/'propagated-embedded.g6').write_text(''.join(codes[i]+'\n' for i in sorted(e)))
(OUT/'propagated-refuted.g6').write_text(''.join(codes[i]+'\n' for i in sorted(r)))
summary={'methods':methods,'direct_E':len(E),'direct_R':len(R),'closure_E':len(e),'closure_R':len(r),'sample_E':sum(idx[g] in e for g in sample),'sample_R':sum(idx[g] in r for g in sample),'sample_unknown':sum(idx[g] not in e|r for g in sample),'seconds':time.monotonic()-t,**usage()}
(OUT/'propagation-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
