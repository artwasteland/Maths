"""Amendment 5 producer and local exact expansion checks."""
import re
from algebra import system,sparse,unsparse,verify_positivity,AlgebraError

def canonical_poly(ctx,value):
 p=unsparse(ctx,value)
 if any(not c for c in p.to_dict().values()) or len(value)!=len(p.to_dict()):raise AlgebraError('dag: zero coefficient')
 exponents=[tuple(term[1]) for term in value]
 if exponents!=sorted(exponents):raise AlgebraError('dag: noncanonical sparse order')
 return p

def verify_dag(code,cert):
 typ=cert.get('type');required={'type','frame','sat','rows'}
 if typ=='real-dag':
  if ('sturm' in cert)==('sos' in cert):raise AlgebraError('dag: exactly one positivity proof required')
  required|={'f','sturm' if 'sturm' in cert else 'sos'}
 elif typ!='null-dag':raise AlgebraError('dag: invalid type')
 if set(cert)!=required:raise AlgebraError('dag: invalid fields')
 ctx,c,gens=system(code,cert['frame'],cert['sat']);zero=ctx.constant(0);values=dict(gens)
 rows=cert['rows']
 if not isinstance(rows,list) or not 1<=len(rows)<=256:raise AlgebraError('dag: row budget')
 for i,row in enumerate(rows):
  if not isinstance(row,dict) or set(row)!={'poly','cofactors'} or not isinstance(row['cofactors'],dict):raise AlgebraError('dag: row fields')
  total=zero
  for key,value in row['cofactors'].items():
   if key not in values:
    if re.fullmatch(r'aux:(0|[1-9][0-9]*)',key):raise AlgebraError('dag: forward or self reference')
    raise AlgebraError('dag: unknown source')
   total+=canonical_poly(ctx,value)*values[key]
  poly=canonical_poly(ctx,row['poly'])
  if total!=poly:raise AlgebraError('dag: row identity '+str(i))
  values['aux:'+str(i)]=poly
 target=ctx.constant(1) if typ=='null-dag' else canonical_poly(ctx,cert['f'])
 if poly!=target:raise AlgebraError('dag: wrong last target')
 if typ=='real-dag':
  if 'sos' in cert:
   for weight,square in cert['sos']['squares']:canonical_poly(ctx,square)
  verify_positivity(ctx,cert,target)
 return True

def build_dag(ctx,frame,sat,helpers,cofs,target,proof):
 rows=[];last={}
 for (poly,identity),cofactor in zip(helpers,cofs):
  if not cofactor:continue
  source='aux:'+str(len(rows));rows.append({'poly':sparse(poly),'cofactors':{k:sparse(p) for k,p in identity.items() if p}});last[source]=sparse(cofactor)
 rows.append({'poly':sparse(target),'cofactors':last})
 cert={'type':'null-dag' if target==ctx.constant(1) else 'real-dag','frame':frame,'sat':sat,'rows':rows}
 if cert['type']=='real-dag':cert.update(f=sparse(target),**proof)
 return cert

def collision_dag(code,frame,sat,ctx,helpers,cofs,distance,pair):
 new_sat=[*sat,list(pair)];new_ctx,_,gens=system(code,frame,new_sat)
 if tuple(new_ctx.names()[:-1])!=tuple(ctx.names()):raise AlgebraError('collision: variable extension mismatch')
 def mapped(p):return new_ctx.from_dict({tuple(e)+(0,):c for e,c in p.terms()})
 new_helpers=[(mapped(p),{k:mapped(h) for k,h in identity.items()}) for p,identity in helpers]
 new_cofs=[mapped(h) for h in cofs];target=mapped(distance);rows=[];last={}
 for (poly,identity),cofactor in zip(new_helpers,new_cofs):
  if not cofactor:continue
  source='aux:'+str(len(rows));rows.append({'poly':sparse(poly),'cofactors':{k:sparse(h) for k,h in identity.items() if h}});last[source]=sparse(cofactor)
 source='aux:'+str(len(rows));rows.append({'poly':sparse(target),'cofactors':last})
 rows.append({'poly':sparse(new_ctx.constant(1)),'cofactors':{source:sparse(new_ctx.gen(new_ctx.nvars()-1)),f's:{pair[0]},{pair[1]}':sparse(new_ctx.constant(-1))}})
 cert={'type':'null-dag','frame':frame,'sat':new_sat,'rows':rows};verify_dag(code,cert);return cert
