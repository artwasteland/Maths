"""Additional real, automatic DAG, and rational spelling regressions."""
from round3 import *
from gp10refute import run_method
from dag import verify_dag
from algebra import system,sparse,unsparse,fmpq_mpoly_ctx
import copy

def main():
 configure();results=[]
 # Reuse the already generated automatic-encoding test proof.
 rec=next(records(R/'tests-automatic-dag/records.jsonl'));results.append(check_run(R/'tests-automatic-dag',[rec],0));results[-1]['type']=rec['cert']['type']
 rec=next(records(R/'tests-portfolio-4/records.jsonl'));old=rec['cert'];rec['cert']={k:v for k,v in old.items() if k!='cofactors'};rec['cert']['type']='real-dag';rec['cert']['rows']=[{'poly':old['f'],'cofactors':old['cofactors']}]
 rec=json.loads(json.dumps(rec));verify_dag(rec['g6'],rec['cert']);results.append(check_run(R/'tests-real-dag-sturm',[rec],0))
 bad=copy.deepcopy(rec);bad['cert']['f'][0][0]='1234567';results.append(check_run(R/'tests-real-dag-sturm-red',[bad],0,'REJECT run records_rejected','dag_last_real'))
 rec=next(records(R/'tests-generated-null/records.jsonl'));ctx,_,_=system(rec['g6'],rec['cert']['frame'],rec['cert']['sat']);rec['cert'].update(type='real-dag',f=sparse(ctx.constant(1)),sturm=ctx.names()[0][0]+'_'+ctx.names()[0][1:]);verify_dag(rec['g6'],rec['cert']);results.append(check_run(R/'tests-real-dag-constant',[rec],0))
 bad=copy.deepcopy(rec);bad['cert']['sturm']='x_99';results.append(check_run(R/'tests-real-dag-constant-red',[bad],0,'REJECT run records_rejected','sturm_variable'))
 ctx=fmpq_mpoly_ctx.get(('x',),'degrevlex');assert unsparse(ctx,[['+1/01',[0]]])==ctx.constant(1)
 try:unsparse(ctx,[['+1/0',[0]]])
 except ValueError as e:assert 'denominator must be positive' in str(e);results.append({'rational_red':str(e)})
 else:raise AssertionError('zero denominator accepted')
 (R/'dag-additional-tests.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({'status':'PASS','checks':len(results),'automatic_type':results[0]['type']}),flush=True)
if __name__=='__main__':main()
