"""Local prototype for a proposed encoding; never emits producer records."""
from algebra import system,sparse,unsparse,add_scaled

def verify_document(doc):
 if set(doc)!={'schema','g6','frame','sat','rows'} or doc['schema']!='gp10-ideal-derivation-proposal-v1':raise ValueError('proposal schema')
 ctx,c,gens=system(doc['g6'],doc['frame'],doc['sat']);zero=ctx.constant(0)
 if not 1<=len(doc['rows'])<=256:raise ValueError('proposal row budget')
 values=dict(gens)
 for i,row in enumerate(doc['rows']):
  if set(row)!={'poly','cofactors'}:raise ValueError('proposal row fields')
  if not set(row['cofactors'])<=set(values):raise ValueError('proposal forward or missing source')
  p=unsparse(ctx,row['poly']);total=sum((unsparse(ctx,h)*values[k] for k,h in row['cofactors'].items()),zero)
  if p!=total:raise ValueError('proposal identity at row '+str(i))
  values['aux:'+str(i)]=p
 if p!=ctx.constant(1):raise ValueError('proposal final target is not one')
 return len(doc['rows'])

def make_document(code,frame,sat,ctx,original,work,substitutions,full,substitute):
 one=ctx.constant(1);rows=[]
 def row(poly,cofactors):
  key='aux:'+str(len(rows));rows.append({'poly':sparse(poly),'cofactors':{k:sparse(h) for k,h in cofactors.items() if h}});return key
 relations=[]
 for index,replacement,proof in substitutions:
  relations.append(row(ctx.gen(index)-replacement,proof))
 aliases={}
 for key,poly in original.items():
  if poly==work[key]:aliases[key]=key;continue
  cof={key:one};current=poly
  for source,(index,replacement,proof) in zip(relations,substitutions):
   rest=substitute(current,index,replacement);q,r=divmod(current-rest,ctx.gen(index)-replacement);assert not r
   if q:cof[source]=-q
   current=rest
  assert current==work[key];aliases[key]=row(current,cof)
 row(one,{aliases[k]:h for k,h in full.items() if h})
 doc={'schema':'gp10-ideal-derivation-proposal-v1','g6':code,'frame':frame,'sat':sat,'rows':rows}
 verify_document(doc);return doc
