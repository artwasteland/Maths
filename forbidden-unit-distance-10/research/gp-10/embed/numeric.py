"""Floating point proposals, followed by mandatory exact reconstruction."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
os.environ['SYMPY_GROUND_TYPES']='python'
import random
from fractions import Fraction
from exact import verify, CertificateError

def fit(n,edges,seed,restarts=3,penalty=True,initial=None):
    import numpy as np
    from scipy.optimize import least_squares
    if not edges:
        return np.array([[3*v,0.] for v in range(n)]), {'residual':0.0,'restarts':0}
    a,b=edges[0]; free=[v for v in range(n) if v not in (a,b)]
    rng=np.random.default_rng(seed%(2**64)); edge_array=np.array(edges)
    pairs=np.array([(u,v) for v in range(n) for u in range(v)])
    def unpack(z):
        p=np.zeros((n,2));p[b]=[1.,0.];p[free]=z.reshape(-1,2);return p
    def residual(z):
        p=unpack(z);diff=p[edge_array[:,0]]-p[edge_array[:,1]]
        out=(diff*diff).sum(axis=1)-1
        if penalty:
            delta=p[pairs[:,0]]-p[pairs[:,1]]
            repel=np.maximum(0.,0.015-(delta*delta).sum(axis=1))*0.1
            out=np.concatenate((out,repel))
        return out
    best=None;best_err=float('inf');runs=0
    for r in range(restarts):
        z=(np.asarray(initial)[free].ravel() if initial is not None and r==0 else rng.normal(size=2*len(free)))
        if free:
            result=least_squares(residual,z,max_nfev=160,ftol=1e-12,xtol=1e-12,gtol=1e-12)
            p=unpack(result.x)
        else:
            p=unpack(z)
        delta=p[edge_array[:,0]]-p[edge_array[:,1]]
        error=float(np.max(np.abs((delta*delta).sum(axis=1)-1)))
        runs+=1
        if error<best_err:best,best_err=p,error
        if error<1e-12:break
    sep=min((float(np.linalg.norm(best[u]-best[v])) for u,v in pairs),default=0.)
    return best,{'residual':best_err,'restarts':runs,'minimum_distance':sep,'penalty':penalty}

def reconstruct(n,edges,positions,seed):
    from algebraic import sympy_module,circles,certificate
    from exact import adjacency
    sp=sympy_module();adj=adjacency(n,edges)
    if not edges:
        return certificate([(sp.Integer(3*v),sp.Integer(0)) for v in range(n)])
    a,b=edges[0];points={a:(sp.Integer(0),sp.Integer(0)),b:(sp.Integer(1),sp.Integer(0))}
    while len(points)<n:
        v=max((v for v in range(n) if v not in points),key=lambda v:(sum((adj[v]>>u)&1 for u in points),adj[v].bit_count(),-v))
        near=[u for u in points if adj[v]>>u&1]
        if len(near)>=2:
            options=circles(points[near[0]],points[near[1]])
            if not options:raise ValueError('numeric:no_real_circle_intersection')
            p=min(options,key=lambda q:sum((float(sp.re(c.evalf()))-z)**2 for c,z in zip(q,positions[v])))
        elif near:
            u=near[0];dx,dy=positions[v]-positions[u]
            t=Fraction(float(dy/(1+dx))) .limit_denominator(12) if abs(1+dx)>1e-8 else None
            direction=(-sp.Integer(1),sp.Integer(0)) if t is None else ((1-sp.Rational(t.numerator,t.denominator)**2)/(1+sp.Rational(t.numerator,t.denominator)**2),2*sp.Rational(t.numerator,t.denominator)/(1+sp.Rational(t.numerator,t.denominator)**2))
            p=tuple(sp.expand(c+d) for c,d in zip(points[u],direction))
        else:
            p=(sp.Integer(8*n*len(points)),sp.Integer(0))
        points[v]=p
    return certificate([points[v] for v in range(n)])

def search(code,n,edges,seed):
    positions,meta=fit(n,edges,seed)
    if meta['residual']>1e-8:
        return None,dict(meta,reason='numeric_not_converged')
    from budget import StageTimeout
    try:
        candidate=reconstruct(n,edges,positions,seed)
    except StageTimeout:
        return None,dict(meta,reason='exact_timeout')
    except Exception as exc:
        return None,dict(meta,reason='exact_exception:'+type(exc).__name__+':'+str(exc)[:160])
    try:
        candidate=verify(code,candidate)
    except CertificateError as exc:
        return None,dict(meta,reason='exact_refused:'+str(exc))
    return candidate,dict(meta,reason='candidate')
