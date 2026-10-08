from common import *
import types,json,hashlib,collections
sys.path.insert(0,str(GP/'embed'))
source=(GP/'embed/rigid_system.py').read_text()
mod=types.ModuleType('rigid_system');mod.__file__=str(OUT/'rigid_system_order11.py')
patched=source.replace('n > 10 or not edges','n > 11 or not edges')
assert source!=patched
(OUT/'rigid_system_order11.py').write_text(patched);exec(compile(patched,mod.__file__,'exec'),mod.__dict__);sys.modules['rigid_system']=mod
import generic_exact as ge,msolve_exact,scipy.optimize,sympy,gp10check as ck
redirect();start_monitor();checker=ck.Checker(9);redirect()
codes=pathlib.Path(sys.argv[1]).read_text().splitlines();began=time.monotonic();counts=collections.Counter();rec=open(OUT/'msolve-records.jsonl','w',buffering=1);stats=open(OUT/'msolve-stats.jsonl','w',buffering=1)
for i,g in enumerate(codes):
 memory();t=time.monotonic();cert=None;meta={};rank=None
 try:
  with timer(22):
   rank,rm=mod.generic_rank(g);cert,meta=ge.msolve_stage(g,OUT/'msolve-cases'/hashlib.sha256(g.encode()).hexdigest()[:12],19-rank,20,2,2)
 except (Exception,Deadline) as exc:meta['error']=str(exc)
 sec=time.monotonic()-t;checkseconds=0
 if cert:
  r={'g6':g,'verdict':'embedded','cert':cert};t=time.monotonic()
  try:
   with timer(30):checker.verify(r)
  except (Exception,Deadline) as exc:meta['checker_error']=str(exc);cert=None
  checkseconds=time.monotonic()-t
 if not cert:r={'g6':g,'verdict':'unknown','cert':{'reason':'No exact embedding in scratch order11 msolve pilot','budget':{'cap':20,'seconds':sec}}}
 counts[r['verdict']]+=1;rec.write(json.dumps(r,separators=(',',':'))+'\n');stats.write(json.dumps({'g6':g,'seconds':sec,'checker_seconds':checkseconds,'verdict':r['verdict'],'rank':rank,'meta':meta})+'\n');print(json.dumps({'done':i+1,'counts':dict(counts),'seconds':time.monotonic()-began}),flush=True)
(OUT/'msolve-summary.json').write_text(json.dumps({'count':len(codes),'counts':dict(counts),'seconds':time.monotonic()-began,'producer_patch':'generic_rank ceiling 10 -> 11; scratch paths redirected; all other make_system/msolve_stage/invoke/certify code unchanged',**usage()},indent=2))
