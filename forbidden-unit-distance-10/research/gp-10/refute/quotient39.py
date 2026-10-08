"""Discover two circle-centre collision cofactors modulo checked local ideals."""
from analytic39 import *
from pathlib import Path

def quotient_lift(ctx,local,polynomials,target,seconds,algorithm="std"):
 if algorithm not in ("std","slimgb"):raise ValueError("quotient algorithm")
 script=cas_prefix(ctx,local).replace('ideal I=','ideal L=')
 script+='L=std(L);qring s=L;ideal I='+','.join(str(p).replace(' ','') for p in polynomials)+';ideal J='+str(target).replace(' ','')+';\n'
 script+='matrix U;matrix T=lift(I,J,U,"'+algorithm+'");poly V=-J[1];for(int k=1;k<=size(I);k++){V=V+I[k]*T[k,1];}if(reduce(V,std(ideal(0)))==0){print("GP10_QUOTIENT_EXACT");for(int j=1;j<=size(I);j++){print(string(T[j,1]));}print("GP10_QUOTIENT_END");}quit;\n'
 out=cas_run(script,seconds);lines=out.splitlines()
 if lines.count('GP10_QUOTIENT_EXACT')!=1 or lines.count('GP10_QUOTIENT_END')!=1:return None,out
 a,b=lines.index('GP10_QUOTIENT_EXACT'),lines.index('GP10_QUOTIENT_END')
 if b-a-1!=len(polynomials):raise ValueError('quotient cofactor count')
 return [expanded_parse(ctx,x) for x in lines[a+1:b]],out

def main():
 configure();p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=55);p.add_argument('--algorithm',default='slimgb',choices=['std','slimgb']);p.add_argument('--tag',required=True);a=p.parse_args()
 code=forbidden_canonical()[39];start=time.monotonic();detail={"limit":a.seconds}
 try:
  ctx,c,g,local,normal,subs,original,sat=construct(code,[0,8],True);zero=ctx.constant(0);one=ctx.constant(1)
  D=sum(((c[6][j]-c[7][j])**2 for j in (0,1)),zero)
  rung=[g['e:5,6'],g['e:5,7']]
  cofs,out=quotient_lift(ctx,[p for p,h in local],rung,D,a.seconds,a.algorithm)
  (EVIDENCE/(a.tag+'.cas.txt')).write_text(out)
  if cofs is None:raise ValueError('no exact quotient marker')
  rem,lh=normal(D-sum((h*p for h,p in zip(cofs,rung)),zero));assert not rem
  full={'e:5,6':cofs[0],'e:5,7':cofs[1]};add_scaled(full,lh,one)
  t=ctx.gen(14+sat.index([6,7]));full={k:p*t for k,p in full.items()};full['s:6,7']=-one
  assert sum((p*g[k] for k,p in full.items()),zero)==one
  print('quotient sizes',[len(p.to_dict()) for p in cofs],count(full),flush=True)
  residual=one-sum((p*original[k] for k,p in full.items()),zero)
  for index,replacement,proof in subs:
   remainder=substitute(residual,index,replacement);quotient,check=divmod(residual-remainder,ctx.gen(index)-replacement);assert not check;add_scaled(full,proof,quotient);residual=remainder
  assert not residual
  assert sum((p*original[k] for k,p in full.items()),zero)==one
  terms=count(full);detail['terms']=terms;print('restored',terms,flush=True)
  cert={'type':'null','frame':[0,8],'sat':sat,'cofactors':{k:sparse(p) for k,p in full.items() if p}}
  verify_algebra(code,cert);rec={'g6':code,'verdict':'refuted','cert':cert};encoded=json.dumps(rec,separators=(',',':'))+'\n';detail['bytes']=len(encoded)
  if len(encoded)>8*1024*1024:raise ValueError('checker line budget')
  (EVIDENCE/(a.tag+'.jsonl')).write_text(encoded);detail['verdict']='refuted'
 except Exception as e:detail.update(verdict='unknown',reason=type(e).__name__+': '+str(e))
 detail['seconds']=time.monotonic()-start;(EVIDENCE/(a.tag+'.summary.json')).write_text(json.dumps(detail,indent=2)+'\n');print(json.dumps(detail),flush=True)
if __name__=='__main__':main()
