from common import *
import ctypes,json,collections,sqlite3
from graph6 import canonicalize,pair_index
start_monitor()
lib=ctypes.CDLL(str(OUT/'tu.so'));lib.init.argtypes=[ctypes.c_char_p]*2;lib.closure.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_int)]
assert lib.init(str(ROOT/'research/unit-distance-22/data/forbidden-398.json').encode(),str(ROOT/'research/unit-distance-22/data/tu-gadgets.json').encode())
raw=json.loads((ROOT/'research/unit-distance-22/data/forbidden-398.json').read_text());frozen=[]
for es in raw:
 n=1+max(max(e) for e in es);cf=canonicalize(n,sum(1<<pair_index(n,*e) for e in es));frozen.append(cf)
sample=set((OUT/'sample.g6').read_text().splitlines());counts=collections.Counter();lens=collections.Counter();terminals=collections.Counter();mem=(ctypes.c_int*4096)();began=time.monotonic();out=open(OUT/'tu-stats.jsonl','w',buffering=1);rec=open(OUT/'tu-records.jsonl','w',buffering=1);verdicts=open(OUT/'tu-all-refuted.g6','w',buffering=1)
for i,c in enumerate((OUT/'B11.g6').read_text().splitlines()):
 t=time.monotonic();length=lib.closure(c.encode(),mem);elapsed=time.monotonic()-t;assert length>0;k=1;steps=[];terminal=None
 for s in range(mem[0]):
  assert mem[k]==2
  gid,pn=mem[k+1],mem[k+2];mp=list(mem[k+3:k+3+pn]);pair=sorted(list(mem[k+3+pn:k+5+pn]));steps.append({'gadget':gid,'map':mp,'pair':pair});k+=5+pn
 status=mem[k];assert status in (0,1)
 if status==1:
  j,pn=mem[k+1],mem[k+2];mp=list(mem[k+3:k+3+pn]);lens[len(steps)]+=1;terminals[j]+=1;verdicts.write(c+'\n')
  assert steps
  end={'forbidden':j,'map':mp} if j<74 else {'refuted':frozen[j].g6,'map':[mp[x] for x in frozen[j].new_to_old]}
  r={'g6':c,'verdict':'refuted','cert':{'type':'tu','steps':steps,'end':end}}
 else:r={'g6':c,'verdict':'unknown','cert':{'reason':'TU closure has no terminal forbidden subgraph','budget':{'steps':len(steps)}}}
 counts[r['verdict']]+=1
 if c in sample:
  out.write(json.dumps({'g6':c,'seconds':elapsed,'steps':len(steps),'verdict':r['verdict']})+'\n');rec.write(json.dumps(r,separators=(',',':'))+'\n')
 if i%4096==0:memory()
summary={'count':i+1,'counts':dict(counts),'refuted_chain_lengths':dict(lens),'terminal_indices':dict(terminals),'seconds':time.monotonic()-began,**usage()};(OUT/'tu-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
