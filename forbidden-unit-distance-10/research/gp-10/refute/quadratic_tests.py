"""Positive and one-coefficient negative controls for SOS target discovery."""
from round3 import *
from algebra import fmpq_mpoly_ctx,verify_positivity,system,prepared_helpers,basis,choose_sat,sparse
from quadratic_sos import discover
from gp10refute import timed,run_method

def main():
 configure();ctx=fmpq_mpoly_ctx.get(('x','y'),'degrevlex');x,y=ctx.gens();zero=ctx.constant(0);coords={0:(zero,zero),1:(ctx.constant(1),zero),2:(x,y)};edges={(0,1),(0,2),(1,2)}
 positive,detail=discover(ctx,[x*x+y*y+1],coords,edges,1);assert positive is not None,detail;verify_positivity(ctx,positive[1],positive[0])
 negative,red=discover(ctx,[x*x+y*y-1],coords,edges,1);assert negative is None and red['lp_status']==2,red
 result={'positive':detail,'one_constant_mutation':red,'status':'PASS'}
 # Exercise the geometric target selector on the previous centroid stall.
 code=forbidden_canonical()[66];n,edges=decode(code);sat=[list(p) for p in sorted(set(choose_sat(n,edges))|{(0,6),(0,7)})];ctx,coords,gens=system(code,[6,7],sat)
 try:
  with timed(10):
   helpers=prepared_helpers(code,[6,7],sat,ctx,coords,gens);gb=basis(ctx,[p for p,h in helpers],5);target,info=discover(ctx,gb,coords,edges,1)
   result['centroid_trial']={'found':target is not None,'detail':info}
   if target:
    verify_positivity(ctx,target[1],target[0]);(R/'quadratic-centroid-target.json').write_text(json.dumps({'target':sparse(target[0]),'proof':target[1]},separators=(',',':'))+'\n')
 except Exception as e:result['centroid_trial']={'found':False,'reason':type(e).__name__+': '+str(e)}
 named=json.loads((MODULE/'fixtures/named.json').read_text());result['safe_controls']=[]
 for name in ['prism','petersen','spindle']:
  cert,detail=run_method(named[name],'portfolio',1);assert cert is None,('soundness failure',name);result['safe_controls'].append({'name':name,'detail':detail})
 (R/'quadratic-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
