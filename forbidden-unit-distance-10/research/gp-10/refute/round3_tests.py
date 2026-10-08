"""Official positive and one-field red interoperability checks for DAG output."""
from round3 import *
from gp10refute import run_method
from dag import verify_dag
import copy

def main():
 configure();R.mkdir(exist_ok=True);results=[]
 null=next(records(R/'F39.null-dag.jsonl'));verify_dag(null['g6'],null['cert'])
 cases=[]
 bad=copy.deepcopy(null);key=next(iter(bad['cert']['rows'][0]['cofactors']));bad['cert']['rows'][0]['cofactors'][key][0][0]='1234567';cases.append(('null-row-coefficient',bad,'dag_row_identity'))
 bad=copy.deepcopy(null);key=next(iter(bad['cert']['rows'][0]['cofactors']));value=bad['cert']['rows'][0]['cofactors'].pop(key);bad['cert']['rows'][0]['cofactors']['aux:0']=value;cases.append(('null-self-reference',bad,'dag_reference_order'))
 bad=copy.deepcopy(null);bad['cert']['rows'][0]['poly'].reverse();cases.append(('null-term-order',bad,'sparse_noncanonical'))
 real=next(records(MODULE/'evidence/round2/final-stall22.jsonl'));old=real['cert'];real['cert']={k:v for k,v in old.items() if k!='cofactors'};real['cert']['type']='real-dag';real['cert']['rows']=[{'poly':old['f'],'cofactors':old['cofactors']}];verify_dag(real['g6'],real['cert'])
 results.append(check_run(R/'tests-real-positive',[real],0))
 bad=copy.deepcopy(real);bad['cert']['sos']['c']='0';cases.append(('real-sos-zero',bad,'sos_constant_positive'))
 code=forbidden_canonical()[1];cert,detail=run_method(code,'dag',5);assert cert is not None,detail;verify_dag(code,cert)
 generated={'g6':code,'verdict':'refuted','cert':cert};results.append(check_run(R/'tests-generated-null',[generated],0));results[-1]['producer_detail']=detail
 for name,rec,reason in cases:
  result=check_run(R/('tests-'+name),[rec],0,'REJECT run records_rejected',reason);result['expected_reason']=reason;results.append(result)
 named=json.loads((MODULE/'fixtures/named.json').read_text());safe=[]
 for name in ['prism','petersen','spindle']:
  cert,detail=run_method(named[name],'dag',1);assert cert is None,('soundness failure',name);safe.append({'name':name,'g6':named[name],'detail':detail})
 result={'status':'PASS','official_runs':results,'safe_dag_controls':safe,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob('*.py')}}
 (R/'dag-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','official_runs':len(results),'safe_dag_controls':len(safe)}),flush=True)
if __name__=='__main__':main()
