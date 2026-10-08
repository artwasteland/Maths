"""Exact cofactor helpers for the two-circle obstruction, no new wire type."""
from algebra import add_scaled,reduce_problem

def helpers39(code,frame,sat,ctx,c,gens,helpers):
    zero,one=ctx.constant(0),ctx.constant(1)
    A,B,R,z,q,b,r,s=[c[i] for i in [6,7,5,8,1,4,2,3]]
    def edge(u,v):
        u,v=sorted((u,v))
        return {} if [u,v]==sorted(frame) else {f"e:{u},{v}":one}
    def linear_identity(poly):
        _,rem,identity=reduce_problem(ctx,helpers,poly)
        if rem:raise ValueError("circle helper linear relation is not proved")
        return identity
    LA=[A[j]-q[j]-b[j]+z[j] for j in (0,1)]
    LB=[B[j]-r[j]-s[j]+z[j] for j in (0,1)]
    PA,PB=edge(3,4),edge(1,2)
    for j in (0,1):
        add_scaled(PA,linear_identity(LA[j]),LA[j]-2*(s[j]-b[j]))
        add_scaled(PB,linear_identity(LB[j]),LB[j]-2*(q[j]-r[j]))
    RA,RB=edge(5,6),edge(5,7)
    L,K,M={},{},{}
    for obj,lc,kc,mc in [(RA,1,1,1),(RB,-1,-1,1),(PA,-1,1,-1),(PB,1,-1,-1)]:
        for result,w in [(L,lc),(K,kc),(M,mc)]:add_scaled(result,obj,one*w/2)
    P=[q[j]+s[j]-z[j] for j in (0,1)]
    Q=[A[j]+B[j]-P[j] for j in (0,1)]
    D=[B[j]-A[j] for j in (0,1)];N=[-D[1],D[0]]
    X=[R[j]-P[j] for j in (0,1)];Y=[R[j]-Q[j] for j in (0,1)]
    kp=sum((D[j]*Y[j] for j in (0,1)),zero)
    t=ctx.gen(14+sat.index([6,7]))
    out=[]
    for i in (0,1):
        for j in (0,1):
            poly=X[i]*Y[j];identity={}
            add_scaled(identity,M,t*N[i]*N[j])
            add_scaled(identity,L,t*(D[i]*Y[j]-(kp if i==j else zero)))
            add_scaled(identity,K,t*D[j]*X[i])
            add_scaled(identity,{"s:6,7":one},-poly)
            if sum((p*gens[k] for k,p in identity.items()),zero)!=poly:raise ValueError("circle identity failed")
            out.append((poly,identity))
    return out
