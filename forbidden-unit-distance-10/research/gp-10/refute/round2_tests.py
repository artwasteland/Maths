"""Positive and one-field red controls for the Round 2 changes."""
from round2 import *
from algebra import *
from graphs import validate_forbidden,verify_sub,verify_tu
from gp10refute import load_known
from quotient39 import quotient_lift
import copy,contextlib

def main():
 configure();results=[]
 def red(name,fn,reason):
  try:fn()
  except Exception as e:
   assert reason in str(e),(name,str(e));results.append({'control':name,'rejected_reason':str(e)})
  else:raise AssertionError(name+' accepted')
 full=patterns(json.loads((UD/'data/forbidden-74.json').read_text()));validate_forbidden(full[:19]);bad=full[:19];bad[0]=full[1]
 red('nonprefix list',lambda:validate_forbidden(bad),'must be a prefix')
 code=forbidden_canonical()[0];cert,detail=run_method(code,'tu',1,full[:6],{});assert cert and cert['type']=='sub';rec={'g6':code,'cert':cert};verify_sub(code,cert,full[:6],{})
 bad=copy.deepcopy(rec['cert']);bad['index']=6
 red('global index outside F7',lambda:verify_sub(rec['g6'],bad,full[:6],{}),'index is not in force')
 bad=copy.deepcopy(rec['cert']);bad['map'][1]=bad['map'][0]
 red('noninjective sub map',lambda:verify_sub(rec['g6'],bad,full[:6],{}),'injective')
 rec=next(r for r in records(R/'B9p-tu.jsonl') if r['verdict']=='refuted' and r['cert']['type']=='tu');verify_tu(rec['g6'],rec['cert'],full[:19],{})
 bad=copy.deepcopy(rec['cert']);bad['steps']=[]
 red('zero-step TU',lambda:verify_tu(rec['g6'],bad,full[:19],{}),'steps must be nonempty')
 ctx=fmpq_mpoly_ctx.get(('z',),'degrevlex');z=ctx.gen(0);one=ctx.constant(1)
 for algorithm in ['std','slimgb']:
  for homogeneous in [False,True]:
   fn=(lambda ps:homogeneous_lift(ctx,ps,one,2,padding=2,algorithm=algorithm)) if homogeneous else (lambda ps:lift(ctx,ps,one,2,algorithm=algorithm))
   assert fn([z*z+1,z]) is not None
   assert fn([z*z+1,ctx.constant(0)]) is None
   results.append({'control':algorithm+(' homogeneous' if homogeneous else ' ordinary')+' lift','rejected_reason':'one-generator mutation has no exact identity marker'})
 ctx=fmpq_mpoly_ctx.get(('x','y'),'degrevlex');x,y=ctx.gens();one=ctx.constant(1)
 gb=basis(ctx,[x-y,y*y+1],2,variable_order=['y','x']);out=fglm_basis(ctx,gb,2,target='x',variable_order=['y','x']);assert x*x+1 in out
 gb=basis(ctx,[x-y,ctx.constant(0)],2,variable_order=['y','x']);assert fglm_basis(ctx,gb,2,target='x',variable_order=['y','x'])==[]
 results.append({'control':'FGLM source variable order','rejected_reason':'one-generator mutation has positive dimension and returns skip'})
 for algorithm in ['std','slimgb']:
  cofs,out=quotient_lift(ctx,[x*x-1],[y],y,2,algorithm);assert cofs is not None and cofs[0]*y==y
  cofs,out=quotient_lift(ctx,[x*x-1],[y],y+1,2,algorithm);assert cofs is None
  results.append({'control':algorithm+' quotient lift','rejected_reason':'one-target mutation has no exact quotient marker'})
 # Reuse must verify its copied certificate, even when called without the CLI loader.
 rec=next(records(R/'final-stall22.jsonl'));cert,detail=run_method(rec['g6'],'reuse',5,(),{rec['g6']:rec});assert cert is not None,detail
 bad=copy.deepcopy(rec);key=next(iter(bad['cert']['cofactors']));bad['cert']['cofactors'][key][0][0]='1234567'
 cert,detail=run_method(rec['g6'],'reuse',5,(),{rec['g6']:bad});assert cert is None and 'identity: expansion' in detail['reason'],detail
 results.append({'control':'replayed coefficient mutation','rejected_reason':detail['reason']})
 # Check the actual new real certificate and two one-field mutations independently.
 rec=next(records(R/'final-stall22.jsonl'));source=R/'red-source.jsonl'
 for name,mutate,expected in [('positive',lambda r:None,'ACCEPT run verified'),('cofactor',lambda r:r['cert']['cofactors'][next(iter(r['cert']['cofactors']))][0].__setitem__(0,'1234567'),'cofactor_identity'),('sos',lambda r:r['cert']['sos'].__setitem__('c','0'),'sos_constant_positive')]:
  bad=copy.deepcopy(rec);mutate(bad);source.write_text(json.dumps(bad,separators=(',',':'))+'\n');run=export('checker-control-'+name,[source],0)
  with (run/'check.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):rc=check(run)
  output=(run/'check.log').read_text();assert expected in output and (rc==0)==(name=='positive'),output
  results.append({'control':'official '+name,'checker_exit':rc,'final_line':output.splitlines()[-1]})
 source.unlink()
 (R/'round2-tests.json').write_text(json.dumps({'status':'PASS','controls':results,'count':len(results)},indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
