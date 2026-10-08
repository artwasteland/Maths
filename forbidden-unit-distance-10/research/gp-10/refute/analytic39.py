"""An exact two-circle proof compiled directly to R-null."""
import os
os.environ["SYMPY_GROUND_TYPES"]="python"
import sys
sys.dont_write_bytecode=True
import argparse,json,time
from algebra import *
from graphs import forbidden_canonical,MODULE
from gp10refute import configure,isolated,flush_line
from circle_helpers import helpers39
from cofactor_reduce import reduce_cofactors,count
from round2 import R as EVIDENCE

def substitute(poly,index,replacement):
    ctx=poly.context();groups={}
    for exponent,value in poly.terms():
        exponent=list(exponent);power=exponent[index];exponent[index]=0
        groups.setdefault(power,{})[tuple(exponent)]=value
    return sum((ctx.from_dict(terms)*replacement**power for power,terms in groups.items()),ctx.constant(0))

def construct(code,frame,setup_only=False,derivation_only=False):
    n,edges=decode(code)
    sat=[list(x) for x in sorted(set(choose_sat(n,edges))|{(0,1),(0,2),(0,3),(0,4),(5,8),(6,7)})]
    ctx,c,gens=system(code,frame,sat);zero,one=ctx.constant(0),ctx.constant(1)
    helpers=prepared_helpers(code,frame,sat,ctx,c,gens)
    original_gens=gens
    substitutions=[]
    for vertex,u,v in [(6,1,4),(7,2,3)]:
        for j,axis in enumerate("xy"):
            index=list(ctx.names()).index(f"{axis}{vertex}")
            replacement=c[u][j]+c[v][j]-c[8][j]
            relation=ctx.gen(index)-replacement
            _,remainder,proof=reduce_problem(ctx,helpers,relation)
            assert not remainder
            assert sum((p*original_gens[k] for k,p in proof.items()),zero)==relation
            substitutions.append((index,replacement,proof))
    gens={}
    for key,poly in original_gens.items():
        for index,replacement,proof in substitutions:poly=substitute(poly,index,replacement)
        gens[key]=poly
    c=dict(c)
    c[6]=tuple(c[1][j]+c[4][j]-c[8][j] for j in (0,1))
    c[7]=tuple(c[2][j]+c[3][j]-c[8][j] for j in (0,1))
    helpers=[]
    def edge(u,v):
        u,v=sorted((u,v));return {} if [u,v]==sorted(frame) else {f"e:{u},{v}":one}
    def lin(poly):
        _,rem,cert=reduce_problem(ctx,helpers,poly)
        assert not rem
        return cert
    def expand(cert,system=gens):return sum((v*system[k] for k,v in cert.items()),zero)
    def d2(a,b):return sum(((a[j]-b[j])**2 for j in (0,1)),zero)
    def inverse(u,v):return ctx.gen(14+sat.index(sorted([u,v])))
    if frame!=[0,8]:raise ValueError("compact circle proof uses the edge frame [0,8]")
    local=[(gens[f"e:{min(u,v)},{max(u,v)}"],edge(u,v)) for u,v in [(1,8),(2,8),(3,8),(4,8),(0,5)]]
    reduced_sats={}
    for v in [1,2,3,4]:
        t=inverse(0,v);h=2*t*c[v][0]-one;hc={f"s:0,{v}":one,f"e:{v},8":-t}
        assert expand(hc)==h
        local.append((h,hc));reduced_sats[v]=hc
        rp=2*t*c[v][1]**2+c[v][0]-2*one;rc={}
        add_scaled(rc,edge(v,8),2*t);add_scaled(rc,hc,2*one-c[v][0])
        assert expand(rc)==rp
        local.append((rp,rc))
    t=inverse(5,8);h=2*t*(one-c[5][0])-one;hc={"s:5,8":one,"e:0,5":-t}
    assert expand(hc)==h
    local.append((h,hc))
    rp=2*t*c[5][1]**2-c[5][0]-one;rc={}
    add_scaled(rc,edge(0,5),2*t);add_scaled(rc,hc,c[5][0]+one)
    assert expand(rc)==rp
    local.append((rp,rc))
    # Two independent unit-triangle ideals. Every supplied basis row is checked
    # against its five local generators, then mapped to original cofactors.
    template=json.loads((MODULE/"fixtures/triangle-ideal.json").read_text())
    for first,second in [(1,2),(3,4)]:
        indices=[list(ctx.names()).index(v) for v in [f"x{first}",f"y{first}",f"x{second}",f"y{second}"]]+[14+sat.index([0,first]),14+sat.index([0,second])]
        def mapped(value):
            result={}
            for coefficient,powers in value:
                exponent=[0]*ctx.nvars()
                for i,power in zip(indices,powers):exponent[i]=power
                result[tuple(exponent)]=fmpq(coefficient)
            return ctx.from_dict(result)
        identities=[edge(first,8),edge(second,8),edge(first,second),reduced_sats[first],reduced_sats[second]]
        base=[expand(identity) for identity in identities]
        assert base==[mapped(poly) for poly in template["generators"]]
        for row in template["basis"]:
            poly=mapped(row["poly"]);identity={}
            for cofactor,source in zip(row["cofactors"],identities):add_scaled(identity,source,mapped(cofactor))
            assert expand(identity)==poly
            local.append((poly,identity))
    def normal(p):
        difference={}
        for iteration in range(100):
            changed=False
            for h,hc in local:
                quotient,p=divmod(p,h)
                if quotient:add_scaled(difference,hc,quotient);changed=True
            if not changed:return p,difference
        raise ValueError("local normal form iteration budget")
    if setup_only:return ctx,c,gens,local,normal,substitutions,original_gens,sat
    A,B,W,z,q,b,r,s,V=[c[i] for i in [6,7,5,8,1,4,2,3,0]]
    P=[q[j]+s[j]-z[j] for j in (0,1)];Q=[r[j]+b[j]-z[j] for j in (0,1)]
    X=[W[j]-P[j] for j in (0,1)];Y=[W[j]-Q[j] for j in (0,1)]
    LA=[A[j]-q[j]-b[j]+z[j] for j in (0,1)];LB=[B[j]-r[j]-s[j]+z[j] for j in (0,1)]
    products=helpers39(code,frame,sat,ctx,c,gens,helpers)
    xy={}
    for i in (0,1):
        for j in (0,1):
            poly,cert=products[2*i+j];cert=dict(cert)
            add_scaled(cert,lin(LA[j]+LB[j]),X[i])
            assert expand(cert)==X[i]*Y[j]
            xy[i,j]=cert
    print("analytic branch products verified",sum(len(p.to_dict()) for h in xy.values() for p in h.values()),flush=True)
    def branch(point,other,branch_rows,pid,oid,prefix):
        # Centres z,W, known neighbour point, actual neighbour V.
        extra={f"{prefix}:{j}":branch_rows[j] for j in (0,1)}
        allgens={**gens,**extra}
        PA=edge(pid,8);PB=edge(oid,8)
        for j in (0,1):add_scaled(PB,{f"{prefix}:{j}":one},2*(other[j]-z[j])+branch_rows[j])
        RA,RB=edge(0,8),edge(0,5)
        L,K,M={},{},{}
        for obj,lc,kc,mc in [(RA,1,1,1),(RB,-1,-1,1),(PA,-1,1,-1),(PB,1,-1,-1)]:
            for out,w in [(L,lc),(K,kc),(M,mc)]:add_scaled(out,obj,one*w/2)
        reflected=[z[j]+W[j]-point[j] for j in (0,1)]
        xx=[V[j]-point[j] for j in (0,1)];yy=[V[j]-reflected[j] for j in (0,1)]
        dd=[W[j]-z[j] for j in (0,1)];nn=[-dd[1],dd[0]]
        kp=sum((dd[j]*yy[j] for j in (0,1)),zero);t=inverse(5,8)
        cert={}
        for i in (0,1):
            for j in (0,1):
                poly=xx[i]*yy[j];pc={}
                add_scaled(pc,M,t*nn[i]*nn[j])
                add_scaled(pc,L,t*(dd[i]*yy[j]-(kp if i==j else zero)))
                add_scaled(pc,K,t*dd[j]*xx[i])
                add_scaled(pc,{"s:5,8":one},-poly)
                assert expand(pc,allgens)==poly
                add_scaled(cert,pc,poly)
        first=d2(V,point)
        for j in (0,1):add_scaled(cert,{f"{prefix}:{j}":one},first*(2*(V[j]-reflected[j])+branch_rows[j]))
        f=first*d2(V,other)
        assert expand(cert,allgens)==f
        branchcofs=[cert.pop(f"{prefix}:{j}",zero) for j in (0,1)]
        f,difference=normal(f);add_scaled(cert,difference,-one)
        for j in (0,1):
            branchcofs[j],difference=normal(branchcofs[j])
            add_scaled(cert,difference,branch_rows[j])
        scale=inverse(0,pid)*inverse(0,oid)
        branchcofs=[normal(scale*h)[0] for h in branchcofs]
        f=one
        residual=f-sum((h*p for h,p in zip(branchcofs,branch_rows)),zero)
        rem,fresh=normal(residual)
        if rem:raise ValueError("unit branch normal form failed")
        cert=fresh
        assert expand(cert)==residual
        print("branch coefficients",prefix,sum(len(p.to_dict()) for p in cert.values()),"fresh",not bool(rem),flush=True)
        print("branch reduced",prefix,str(f),[len(h.to_dict()) for h in branchcofs],flush=True)
        return f,cert,branchcofs
    FA,ca,ha=branch(q,s,X,1,3,"a")
    FB,cb,hb=branch(r,b,Y,2,4,"b")
    print("analytic branch identities verified",flush=True)
    productcert={};add_scaled(productcert,ca,FB)
    add_scaled(productcert,cb,sum((ha[j]*X[j] for j in (0,1)),zero))
    for i in (0,1):
        for j in (0,1):
            weight,difference=normal(ha[i]*hb[j])
            add_scaled(productcert,xy[i,j],weight)
            add_scaled(productcert,difference,X[i]*Y[j])
    assert expand(productcert)==FA*FB
    print("analytic product verified",sum(len(p.to_dict()) for p in productcert.values()),flush=True)
    local_keys={k for poly,identity in local for k in identity}
    projected={}
    for key,poly in productcert.items():
        if key not in local_keys:
            remainder,_=normal(poly)
            if remainder:projected[key]=remainder
    remainder,local_cert=normal(one-expand(projected))
    if remainder:raise ValueError("local quotient compression did not close")
    add_scaled(projected,local_cert,one)
    full=projected
    print("quotient compressed",count(full),{k:len(p.to_dict()) for k,p in full.items() if k not in local_keys},flush=True)
    assert expand(full)==one
    if derivation_only:
        from ideal_derivation import make_document
        return make_document(code,frame,sat,ctx,original_gens,gens,substitutions,full,substitute)
    residual=one-sum((p*original_gens[k] for k,p in full.items()),zero)
    full=dict(full)
    for index,replacement,proof in substitutions:
        remainder=substitute(residual,index,replacement)
        quotient,check=divmod(residual-remainder,ctx.gen(index)-replacement)
        assert not check
        quotient,difference=normal(quotient)
        add_scaled(full,difference,ctx.gen(index)-replacement)
        add_scaled(full,proof,quotient)
        print("restoration quotient",ctx.names()[index],len(quotient.to_dict()),flush=True)
        residual=remainder
    assert not residual
    assert sum((p*original_gens[k] for k,p in full.items()),zero)==one
    terms=count(full);print("analytic null verified",terms,flush=True)
    if terms>130000:return None,{"reason":"certificate term budget","terms":terms}
    cert={"type":"null","frame":frame,"sat":sat,"cofactors":{k:sparse(p) for k,p in full.items() if p}}
    verify_algebra(code,cert)
    size=len(json.dumps({"g6":code,"verdict":"refuted","cert":cert},separators=(",",":")))+1
    if size>8*1024*1024:return None,{"reason":"checker line budget","bytes":size,"terms":terms}
    return cert,{"terms":terms,"bytes":size}

def main():
    configure();p=argparse.ArgumentParser();p.add_argument("--frame",type=int,nargs=2,default=[0,8]);p.add_argument("--seconds",type=float,default=55);p.add_argument("--tag",required=True);a=p.parse_args();code=forbidden_canonical()[39];start=time.monotonic()
    cert,detail=isolated(lambda:construct(code,a.frame),a.seconds)
    detail.update({"g6":code,"frame":a.frame,"seconds":time.monotonic()-start,"limit":a.seconds,"verdict":"refuted" if cert else "unknown"})
    with (EVIDENCE/(a.tag+".jsonl")).open("w") as f:flush_line(f,{"g6":code,"verdict":detail["verdict"],"cert":cert or {"reason":detail.get("reason","exhausted"),"budget":detail}})
    (EVIDENCE/(a.tag+".summary.json")).write_text(json.dumps(detail,indent=2)+"\n");print(json.dumps(detail),flush=True)
if __name__=="__main__":main()
