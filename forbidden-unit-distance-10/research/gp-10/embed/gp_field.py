"""Per-image radical fields through a bounded PARI child, checked by E-exact."""
import ast
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import time
from msolve_exact import parse_literal, sha, limits
from exact import verify

PRELUDE = r"""
default(nbthreads,1);
default(realprecision,250);
default(parisizemax,512000000);
x='x;t='t;
P=t; NF=nfinit(P); TH=0.; R=List();
value(a)=real(subst(lift(a),t,TH));
remap(a)=for(j=1,#R,R[j]=Mod(subst(lift(R[j]),t,a),P));
reducefield()={my(red,oldth,roots,idx,err,v);red=polredbest(P,1);oldth=TH;P=red[1];roots=polrootsreal(P);idx=1;err=1e100;for(j=1,#roots,v=abs(subst(lift(red[2]),t,roots[j])-oldth);if(v<err,err=v;idx=j));if(err>1e-100,error("field:embedding_reduction"));TH=roots[idx];remap(lift(red[2]));NF=nfinit(P);};
rootfield(a)={my(v,roots,b,ext,oldth,mapold);if(a==0,return(Mod(0,P)));v=value(a);if(v<=0,error("field:nonpositive_radicand"));roots=nfroots(NF,x^2-a);if(#roots,for(j=1,#roots,if(value(roots[j])>0,return(Mod(lift(roots[j]),P))));error("field:no_positive_root"));oldth=TH;ext=rnfequation(NF,x^2-a,1);P=subst(ext[1],x,t);mapold=subst(lift(ext[2]),x,t);TH=sqrt(v)+ext[3]*oldth;remap(mapold);b=Mod(t-ext[3]*mapold,P);listput(R,b);if(poldegree(P)>256,error("field:degree_cap"));reducefield();b=R[#R];listpop(R);print("GP_EXTENSION ",poldegree(P));return(b);};
push(a)={listput(R,Mod(lift(a),P));return(#R);};
finish(ids)={my(d=#ids,dim=poldegree(P),C,B,T,Q,degree,U,V,ok,red,oldth,roots,idx,err,z,lo,hi,den);C=matrix(dim,d,i,j,polcoef(lift(R[ids[j]]),i-1,t));ok=0;for(trial=1,8,T=sum(j=1,d,(j+trial-1)^trial*R[ids[j]]);Q=minpoly(T);degree=poldegree(Q);B=matrix(dim,degree,i,j,polcoef(lift(T^(j-1)),i-1,t));U=matinverseimage(B,C);if(matsize(U)==[degree,d] && B*U==C,ok=1;break));if(!ok,error("field:coordinate_primitive"));oldth=value(T);Q=subst(Q,variable(Q),t);red=polredbest(Q,1);Q=red[1];roots=polrootsreal(Q);idx=1;err=1e100;for(j=1,#roots,z=abs(subst(lift(red[2]),t,roots[j])-oldth);if(z<err,err=z;idx=j));if(err>1e-100,error("field:coordinate_embedding"));TH=roots[idx];V=vector(d,j,Mod(subst(sum(i=1,degree,U[i,j]*t^(i-1)),t,lift(red[2])),Q));Q=Q*denominator(Q);Q=Q/content(Q);den=2^160;lo=floor(TH*den)/den;hi=lo+1/den;if(subst(Q,t,lo)*subst(Q,t,hi)>=0,error("field:root_interval"));print("GP_FIELD_POLY ",vector(degree+1,i,polcoef(Q,i-1,t)));print("GP_FIELD_INTERVAL ",[lo,hi]);print("GP_FIELD_COORDS ",vector(d,j,vector(degree,i,polcoef(lift(V[j]),i-1,t))));print("GP_FIELD_OK");};
"""


def program(points):
    """Whitelist expressions and emit a DAG of exact rational operations."""
    ops=[]; memo={}
    def visit(node):
        key=ast.dump(node)
        if key in memo:return memo[key]
        if isinstance(node,ast.Constant) and type(node.value) is int:
            expr=str(node.value)
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):
            expr=f'-R[{visit(node.operand)}]'
        elif isinstance(node,ast.BinOp):
            a=visit(node.left)
            if isinstance(node.op,ast.Pow):
                power=Fraction(ast.literal_eval(node.right)) if isinstance(node.right,ast.Constant) else None
                if isinstance(node.right,ast.BinOp) and isinstance(node.right.op,ast.Div):
                    power=Fraction(ast.literal_eval(node.right.left),ast.literal_eval(node.right.right))
                if power is None or power.denominator not in (1,2):raise ValueError('field:exponent')
                expr=f'R[{a}]^{power.numerator}' if power.denominator==1 else f'rootfield(R[{a}])^{power.numerator}'
            else:
                b=visit(node.right);op={ast.Add:'+',ast.Sub:'-',ast.Mult:'*',ast.Div:'/'}.get(type(node.op))
                if op is None:raise ValueError('field:operator')
                expr=f'R[{a}]{op}R[{b}]'
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='sqrt' and len(node.args)==1:
            expr=f'rootfield(R[{visit(node.args[0])}])'
        else:raise ValueError('field:expression')
        index=len(ops)+1;ops.append(f'push({expr});');memo[key]=index;return index
    ids=[visit(ast.parse(s,mode='eval').body) for pt in points for s in pt]
    return PRELUDE+'\nmain()={\n'+'\n'.join(ops)+'\nfinish('+str(ids)+');\n};\nmain();\nquit;\n'


def convert(points,directory,seconds=180,g6=None):
    limits();directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if not isinstance(g6,str) or not g6:raise ValueError('pari:graph_seed_required')
    seed=int(sha(g6.encode())[:16],16)
    source='setrand('+str(seed)+');\n'+program(points);(directory/'field.gp').write_text(source)
    start=time.monotonic();command=['gp','-fq','-s','128000000',str(directory/'field.gp')]
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:out,err=child.communicate(timeout=seconds);timeout=False
    except subprocess.TimeoutExpired:
        child.kill();out,err=child.communicate();timeout=True
    (directory/'field.log').write_text(out);(directory/'field.stderr').write_text(err)
    meta={'command':command,'seconds':time.monotonic()-start,'cap_seconds':seconds,'returncode':child.returncode,
          'timeout':timeout,'seed':seed,'threads':1,'input_sha256':sha(source.encode()),'output_sha256':sha(out.encode())}
    (directory/'field-call.json').write_text(json.dumps(meta,indent=2)+'\n')
    if timeout:raise TimeoutError('pari:timeout')
    if child.returncode or not out.splitlines() or out.splitlines()[-1]!='GP_FIELD_OK':
        raise ValueError('pari:missing_exact_success:'+err[-500:])
    def field(label):
        rows=[line[len(label):] for line in out.splitlines() if line.startswith(label)]
        if len(rows)!=1:raise ValueError('pari:output_field')
        return parse_literal(rows[0]+':')
    coeff=field('GP_FIELD_POLY ');interval=field('GP_FIELD_INTERVAL ');coords=field('GP_FIELD_COORDS ')
    if any(type(c) is not int for c in coeff):raise ValueError('pari:noninteger_polynomial')
    def q(v):v=Fraction(v);return f'{v.numerator}/{v.denominator}'
    cert={'type':'exact','field':{'minpoly':coeff,'interval':[q(v) for v in interval]},
          'coords':[[[q(v) for v in coords[2*i+k]] for k in (0,1)] for i in range(len(points))]}
    return cert,meta
