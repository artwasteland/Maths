"""Round 4 positive certificates, one-field red controls and safe inputs."""
from round4 import *
import round4,copy,tempfile
from algebra import fmpq_mpoly_ctx,verify_positivity
from quadratic_sos import discover
from fractions import Fraction

def main():
 configure();R4.mkdir(parents=True,exist_ok=True)
 ctx=fmpq_mpoly_ctx.get(('x','y','z','w'),'degrevlex');x,y,z,w=ctx.gens()
 coords={0:(ctx.constant(0),ctx.constant(0)),1:(x,y),2:(z,w)};edges={(0,2),(1,2)}
 polynomials=[x*x+y*y-5,z*z+w*w-1,(x-z)**2+(y-w)**2-1]
 target,positive=discover(ctx,polynomials,coords,edges,1,max_rows=600,lens=True)
 assert target is not None,positive;verify_positivity(ctx,target[1],target[0])
 bad=polynomials.copy();bad[0]=x*x+y*y-3
 target,negative=discover(ctx,bad,coords,edges,1,max_rows=600,lens=True)
 assert target is None and negative['lp_status']==2,negative
 official=[];gp=forbidden_canonical()
 for method,index in [('null',1),('real',4)]:
  cert,detail=algebra_attempt(gp[index],method,10,None);assert cert,detail
  record={'g6':gp[index],'verdict':'refuted','cert':cert}
  check=check_run(R4/('tests-'+method+'-positive'),[record],0);check['producer_detail']=detail;official.append(check)
  bad=copy.deepcopy(record)
  if cert['type'].endswith('-dag'):
   cofs=bad['cert']['rows'][0]['cofactors'];reason='dag_row_identity'
  else:cofs=bad['cert']['cofactors'];reason='cofactor_identity'
  key=next(iter(cofs));cofs[key][0][0]=str(Fraction(cofs[key][0][0])+1)
  official.append(check_run(R4/('tests-'+method+'-red'),[bad],0,'REJECT run records_rejected',reason))
 saved=round4.HINT_ROOT
 with tempfile.TemporaryDirectory(prefix='r4-hints-',dir=SCRATCH) as tmp:
  round4.HINT_ROOT=Path(tmp);p=Path(tmp)/'likely-forbidden.g6'
  n,es=decode(gp[1]);pair=next([u,v] for u in range(n) for v in range(u+1,n) if (u,v) not in es)
  obj={'g6':gp[1],'reason':'forced collision','collision_pair':pair}
  p.write_text(json.dumps(obj)+'\n');hints,meta=read_hints({gp[1]});assert hints[gp[1]]['pairs']==[pair]
  obj['g6']=gp[0];p.write_text(json.dumps(obj)+'\n');hints,meta=read_hints({gp[1]});assert not hints and meta['ignored_lines'][0]['reason']=='outside_frozen_B10_or_unparsed'
 round4.HINT_ROOT=saved
 safe=[];named=json.loads((MODULE/'fixtures/named.json').read_text())
 for name in ['prism','petersen','spindle']:
  for method in ['null','real']:
   cert,detail=algebra_attempt(named[name],method,1,None);assert cert is None,('soundness failure',name,method)
   safe.append({'name':name,'detail':detail})
 result={'status':'PASS','lens_positive':positive,'lens_one_constant_mutation':negative,'official_checks':official,'hint_mutation_reason':'outside_frozen_B10_or_unparsed','safe_controls':safe,'source_sha256':source_hashes()}
 (R4/'tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','official_checks':len(official),'safe_controls':len(safe)}),flush=True)
if __name__=='__main__':main()
