"""Round 3 certificate runs and append-only candidate stream snapshots."""
import os
os.environ['SYMPY_GROUND_TYPES']='python'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import sys
sys.dont_write_bytecode=True
import json,hashlib,contextlib,time
from pathlib import Path
from gp10refute import configure,flush_line
from graphs import MODULE,SCRATCH,ROOT,UD,decode,forbidden_canonical
from round2 import check,records
R=MODULE/'evidence/round3'
C=SCRATCH/'cand'
SOURCE=Path('<scratch>/scratchpad/cand')

def check_run(directory,rows,limit=9,expected='ACCEPT run verified',reason=None):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);rows=list(rows)
 codes=sorted(r['g6'] for r in rows);assert len(codes)==len(set(codes))
 data=(''.join(c+'\n' for c in codes)).encode();(directory/'input.g6').write_bytes(data)
 with (directory/'records.jsonl').open('w') as f:
  for r in rows:flush_line(f,r)
 (directory/'UNKNOWN.g6').write_text(''.join(r['g6']+'\n' for r in sorted(rows,key=lambda r:r['g6']) if r['verdict']=='unknown'))
 (directory/'run.json').write_text(json.dumps({'profile':'sample','input':'input.g6','input_sha256':hashlib.sha256(data).hexdigest(),'records':['records.jsonl'],'unknown':'UNKNOWN.g6','forbidden_limit':limit},indent=2)+'\n')
 start=time.monotonic()
 with (directory/'check.log').open('w') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):rc=check(directory)
 output=(directory/'check.log').read_text();assert output.splitlines()[-1]==expected,output[-2000:]
 if reason:assert reason in output,output
 result={'directory':str(directory),'records':len(rows),'refuted':sum(r['verdict']=='refuted' for r in rows),'forbidden_limit':limit,'checker_exit':rc,'final_line':output.splitlines()[-1],'seconds':time.monotonic()-start,'checker_sha256':hashlib.sha256((ROOT/'research/gp-10/check/gp10check.py').read_bytes()).hexdigest()}
 (directory/'verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

def close39():
 configure();R.mkdir(exist_ok=True)
 doc=json.loads((MODULE/'evidence/round2/39-ideal-derivation.json').read_text())
 cert={'type':'null-dag','frame':doc['frame'],'sat':doc['sat'],'rows':doc['rows']}
 rec={'g6':doc['g6'],'verdict':'refuted','cert':cert}
 path=R/'F39.null-dag.jsonl'
 with path.open('w') as f:flush_line(f,rec)
 result={'row_count':len(cert['rows']),'record_bytes':path.stat().st_size,'runs':[check_run(R/('checker-F39-F'+str(limit)),[rec],limit) for limit in [0,8]]}
 (R/'F39.summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':close39()
