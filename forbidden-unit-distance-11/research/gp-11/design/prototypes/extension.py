from common import *
import sqlite3,json,subprocess,hashlib
from functools import lru_cache
from exact import graph6,adjacency,verify,CertificateError
from graph6 import decode_graph6,canonicalize,encode_graph6,pair_index
from gp_field import PRELUDE
from msolve_exact import parse_literal
from exact import textq
def gp_output(code,out,points):
 lines=out.splitlines()
 if not lines or lines[-1]!='GP_FIELD_OK':raise ValueError('pari:missing_exact_success')
 def item(label):
  found=[line[len(label):] for line in lines if line.startswith(label)]
  if len(found)!=1:raise ValueError('pari:output_field')
  return parse_literal(found[0]+':')
 coeff=item('GP_FIELD_POLY ');interval=item('GP_FIELD_INTERVAL ');coords=item('GP_FIELD_COORDS ')
 cert={'type':'exact','field':{'minpoly':coeff,'interval':[textq(str(v)) for v in interval]},'coords':[[[textq(str(v)) for v in coords[2*i+j]] for j in (0,1)] for i in range(points)]}
 return verify(code,cert,max_refinements=256)
DB=sqlite3.connect(OUT/'gp10.sqlite')
@lru_cache(maxsize=2000)
def resolve(code):
 row=DB.execute('SELECT verdict,raw FROM records WHERE g6=?',(code,)).fetchone()
 if row is None or row[0]!='embedded':return None
 c=json.loads(row[1])['cert']
 if c['type']=='exact':return c
 assert c['type']=='super'
 host=resolve(c['g6'])
 if host is None:raise ValueError('missing dependency '+c['g6'])
 return {'type':'exact','field':host['field'],'coords':[host['coords'][i] for i in c['map']]}
def gp_poly(cs):return '+'.join('('+str(c)+')*t^'+str(i) for i,c in enumerate(cs)) or '0'
def extend_gp(code,cert,v,keep,near,seconds):
 ids=[[0,0] for _ in range(11)];stm=[];k=0
 for old,p in zip(keep,cert['coords']):
  for j in (0,1):k+=1;ids[old][j]=k;stm.append('push('+gp_poly(p[j])+');')
 stm.append('reducefield();')
 a,b=near; ax,ay=ids[a];bx,by=ids[b]
 stm+=['push(R[%d]-R[%d]);'%(bx,ax),'push(R[%d]-R[%d]);'%(by,ay),'push((R[%d]+R[%d])/2);'%(ax,bx),'push((R[%d]+R[%d])/2);'%(ay,by)]
 dx,dy,mx,my=k+1,k+2,k+3,k+4;k+=4
 stm+=['dd=R[%d]^2+R[%d]^2;'%(dx,dy),'if(value(dd)>4+1e-50,error("extension:far"));','zz=1/dd-1/4;','if(zz!=0 && value(zz)<0,error("extension:far"));','push(rootfield(zz));'];k+=1;sqrtid=k
 stm+=['sgn=0;forstep(s=1,-1,-2,px=R[%d]+s*R[%d]*R[%d];py=R[%d]-s*R[%d]*R[%d];ok=1;for(j=1,10,if(px==R[2*j-1] && py==R[2*j],ok=0));if(ok,sgn=s;break));if(sgn==0,error("extension:collision"));'%(mx,dy,sqrtid,my,dx,sqrtid),'push(px);','push(py);'];ids[v]=[k+1,k+2]
 coeff=gp_poly(cert['field']['minpoly']);lo,hi=cert['field']['interval']
 init='P='+coeff+';rr=polrootsreal(P);idx=0;for(j=1,#rr,if(rr[j]>'+lo+' && rr[j]<'+hi+',idx=j;break));if(idx==0,error("base:root"));TH=rr[idx];R=List();'
 source=PRELUDE+'\nmain()={\n'+init+'\n'+'\n'.join(stm)+'\nfinish('+str([i for pair in ids for i in pair])+');\n};\nmain();\nquit;\n'
 p=OUT/'extension-current.gp';p.write_text(source)
 child=subprocess.Popen(['gp','-fq','-s','64000000',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:stdout,stderr=child.communicate(timeout=seconds)
 except BaseException:child.kill();child.communicate();raise
 if not stdout.splitlines() or stdout.splitlines()[-1]!='GP_FIELD_OK':raise ValueError(stderr[-400:])
 return gp_output(code,stdout,11)
def extension(code,cap=3):
 t=time.monotonic();n,edges=graph6(code);a=adjacency(n,edges);vertices=[v for v in range(n) if a[v].bit_count()==2]
 meta={'degree2_vertices':len(vertices),'deletions_in_B10':0,'attempts':[]}
 for v in vertices:
  if time.monotonic()-t>=cap:break
  keep=[u for u in range(n) if u!=v];inv={u:i for i,u in enumerate(keep)}
  mask=sum(1<<pair_index(10,inv[x],inv[y]) for x,y in edges if v not in (x,y))
  cf=canonicalize(10,mask);c=resolve(cf.g6)
  if c is None:continue
  meta['deletions_in_B10']+=1
  c={'type':'exact','field':c['field'],'coords':[c['coords'][cf.old_to_new[u]] for u in range(10)]}
  near=[u for u in range(n) if a[v]>>u&1];start=time.monotonic()
  try:
   verify(encode_graph6(10,mask),c)
   candidate=extend_gp(code,c,v,keep,near,max(.001,cap-(time.monotonic()-t)))
   candidate=verify(code,candidate)
   meta['attempts'].append({'v':v,'base':cf.g6,'seconds':time.monotonic()-start,'result':'exact','degree':len(candidate['field']['minpoly'])-1});return candidate,meta
  except Exception as exc:meta['attempts'].append({'v':v,'base':cf.g6,'seconds':time.monotonic()-start,'error':type(exc).__name__+':'+str(exc)[-250:]})
 return None,meta
