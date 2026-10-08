"""Bounded fresh discovery retries selected from unsuccessful control sweeps."""
from round2 import *
from gp10refute import run_method

def main():
 configure();p=argparse.ArgumentParser();p.add_argument('--indices',type=int,nargs='+',required=True);p.add_argument('--method',choices=['tree','null','real'],required=True);p.add_argument('--seconds',type=float,required=True);p.add_argument('--all-sat',action='store_true');p.add_argument('--tag',required=True);a=p.parse_args()
 assert len(a.indices)*a.seconds<=285
 gp=forbidden_canonical();rows=[];start=time.monotonic();path=R/(a.tag+'.jsonl');assert not path.exists()
 if a.method=='tree':import amp_core
 with path.open('w') as f:
  for i in a.indices:
   cert,detail=run_method(gp[i],a.method,a.seconds,(),{},1000,a.all_sat)
   rec={'g6':gp[i],'verdict':'refuted' if cert else 'unknown','cert':cert or {'reason':detail.get('reason','exhausted'),'budget':detail}};flush_line(f,rec)
   row={'index':i,'g6':gp[i],'verdict':rec['verdict'],'detail':detail};rows.append(row);print(json.dumps(row),flush=True)
 (R/(a.tag+'.summary.json')).write_text(json.dumps({'argv':sys.argv,'rows':rows,'seconds':time.monotonic()-start,'prefix':0,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in MODULE.glob('*.py')}},indent=2)+'\n')
if __name__=='__main__':main()
