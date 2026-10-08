"""Bounded floating discovery, with exact reconstruction, of quadratic SOS targets."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import itertools,time,warnings
from fractions import Fraction
from algebra import fmpq,sparse

def discover(ctx,gb,coords,edges,seconds=0.3,max_rows=250,lens=False):
 from scipy.optimize import linprog,OptimizeWarning
 from scipy.sparse import coo_matrix
 rows=[];zero=ctx.constant(0);one=ctx.constant(1)
 for p in gb:
  degree=max((sum(e) for e in p.to_dict()),default=0)
  if not p or degree>2:continue
  rows.append(p)
  if degree==1:rows.extend(p*ctx.gen(i) for i in range(ctx.nvars()))
 if not rows or len(rows)>max_rows:return None,{'reason':'quadratic row budget','rows':len(rows)}
 n=len(coords);forms={}
 def add(q):
  if not q:return
  q=q/q.leading_coefficient();forms.setdefault(str(q),q)
 for point in coords.values():
  for q in point:add(q)
 for u,v in itertools.combinations(range(n),2):
  for j in (0,1):add(coords[u][j]-coords[v][j]);add(coords[u][j]+coords[v][j])
 if lens:
  for u,v in itertools.combinations(range(n),2):
   for w in range(n):
    if tuple(sorted((u,w))) in edges and tuple(sorted((v,w))) in edges:
     for j in (0,1):add(coords[u][j]+coords[v][j]-2*coords[w][j])
 triangles=[t for t in itertools.combinations(range(n),3) if all(tuple(sorted(p)) in edges for p in itertools.combinations(t,2))]
 for tri in triangles:
  for other in itertools.combinations(range(n),3):
   if set(tri)&set(other):continue
   for j in (0,1):add(sum((coords[v][j] for v in tri),zero)-sum((coords[v][j] for v in other),zero))
 qs=list(forms.values());polys=rows+[-q*q for q in qs]
 powers=sorted({(0,)*ctx.nvars()}|{e for p in polys for e in p.to_dict()});positions={e:i for i,e in enumerate(powers)}
 ri=[];ci=[];values=[]
 for j,p in enumerate(polys):
  for e,c in p.terms():ri.append(positions[e]);ci.append(j);values.append(float(c))
 matrix=coo_matrix((values,(ri,ci)),shape=(len(powers),len(polys))).tocsc();rhs=[0.0]*len(powers);rhs[positions[(0,)*ctx.nvars()]]=1.0
 start=time.monotonic()
 with warnings.catch_warnings():
  warnings.simplefilter('ignore',OptimizeWarning)
  result=linprog([0.0]*len(rows)+[1.0]*len(qs),A_eq=matrix,b_eq=rhs,bounds=[(None,None)]*len(rows)+[(0,None)]*len(qs),method='highs-ds',options={'time_limit':max(.001,seconds),'threads':1,'parallel':False})
 detail={'rows':len(rows),'square_candidates':len(qs),'lp_seconds':time.monotonic()-start,'lp_status':int(result.status)}
 if not result.success:return None,detail
 for bound in [1000,1000000]:
  coeffs=[fmpq(str(Fraction(float(x)).limit_denominator(bound))) for x in result.x]
  if any(x<0 for x in coeffs[len(rows):]):continue
  target=sum((a*p for a,p in zip(coeffs,rows)),zero)
  sos=one+sum((a*q*q for a,q in zip(coeffs[len(rows):],qs)),zero)
  if target!=sos:continue
  proof={'sos':{'c':'1','squares':[[str(a),sparse(q)] for a,q in zip(coeffs[len(rows):],qs) if a]}}
  return (target,proof),detail
 detail['reason']='exact reconstruction failed';return None,detail
