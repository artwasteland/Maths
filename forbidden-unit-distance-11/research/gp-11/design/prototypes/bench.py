from common import *
import hashlib,json,collections
import numeric,scipy.optimize,sympy
from exact import graph6,verify
import gp10refute,algebra,graphs,gp10check
redirect()
start_monitor()
method=sys.argv[1];tag=os.environ.get('GP11_STAGE_TAG',method);cap=float(sys.argv[2]) if len(sys.argv)>2 else 2.0
codes=pathlib.Path(sys.argv[3] if len(sys.argv)>3 else OUT/'sample.g6').read_text().splitlines()
if method=='extension':from extension import extension
if method.startswith('lattice'):from lattice import search
if method=='host':
 from hosts import search as host_search,database
 database()
if method=='tree':import amp_core
checker=gp10check.Checker(9)
redirect()
records=open(OUT/(tag+'-records.jsonl'),'w',buffering=1);stats=open(OUT/(tag+'-stats.jsonl'),'w',buffering=1)
began=time.monotonic();counts=collections.Counter();extra=collections.Counter()
for i,code in enumerate(codes):
 memory();n,edges=graph6(code);seed=int.from_bytes(hashlib.sha256(code.encode()).digest(),'big');t=time.monotonic();cert=None;meta={};stage='start'
 try:
  with timer(cap):
   if method=='extension':cert,meta=extension(code,cap-.02)
   elif method=='numeric':
    stage='fit';s=time.monotonic();points,meta=numeric.fit(n,edges,seed);meta['fit_seconds']=time.monotonic()-s
    if meta['residual']<=1e-8:
     stage='exactification';s=time.monotonic();cert=numeric.reconstruct(n,edges,points,seed);meta['exact_seconds']=time.monotonic()-s;cert=verify(code,cert)
   elif method.startswith('lattice'):cert,meta=search(n,edges,seed,'lattice18' if method=='lattice' else method,20000)
   elif method=='host':cert,meta=host_search(n,edges,seed,20000)
   elif method=='tree':cert,meta=gp10refute.tree_search(code,1200)
   elif method in ('null','real','dag','portfolio'):
    cert,meta=algebra.algebra_search(code,'real' if method=='dag' else method,cap-.02,dag='auto' if method!='dag' else True,all_pairs=os.environ.get('GP11_ALL_PAIRS')=='1')
 except (Exception,Deadline) as exc:cert=None;meta.update(reason=type(exc).__name__+':'+str(exc)[:180],interrupted_stage=stage)
 seconds=time.monotonic()-t;checkseconds=0
 if cert:
  rec={'g6':code,'verdict':'embedded' if (method in ('numeric','extension','host') or method.startswith('lattice')) else 'refuted','cert':cert}
  s=time.monotonic()
  try:
   with timer(15):checker.verify(rec)
  except (Exception,Deadline) as exc:meta['checker_error']=str(exc);cert=None;extra['checker_rejected']+=1
  checkseconds=time.monotonic()-s
 if not cert:rec={'g6':code,'verdict':'unknown','cert':{'reason':meta.get('reason','no_certificate'),'budget':{'method':method,'cap':cap,'seconds':seconds}}}
 counts[rec['verdict']]+=1
 records.write(json.dumps(rec,separators=(',',':'))+'\n')
 stats.write(json.dumps({'i':i,'g6':code,'method':method,'verdict':rec['verdict'],'seconds':seconds,'checker_seconds':checkseconds,'meta':meta})+'\n')
 if (i+1)%25==0:print(json.dumps({'method':method,'done':i+1,'counts':dict(counts),'seconds':time.monotonic()-began,**usage()}),flush=True)
summary={'method':method,'cap':cap,'count':len(codes),'counts':dict(counts),'extra':dict(extra),'seconds':time.monotonic()-began,**usage()}
(OUT/(tag+'-summary.json')).write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
