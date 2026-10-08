"""Exact circle construction and conversion to an ordinary power basis."""
import os
os.environ['SYMPY_GROUND_TYPES'] = 'python'
from fractions import Fraction
from functools import lru_cache
import random
from exact import rational, textq, adjacency

def sympy_module():
    import sympy as sp
    return sp

def points_from_cert(cert):
    sp = sympy_module()
    if cert['field']['minpoly'] == [64,0,-28,0,1]:
        theta = sp.sqrt(3) + sp.sqrt(11)
    elif cert['field']['minpoly'] == [0,1]:
        theta = sp.Integer(0)
    else:
        raise ValueError('construction:unsupported_core_field')
    return [tuple(sp.expand(sum(sp.Rational(c)*theta**i for i,c in enumerate(z))) for z in pt)
            for pt in cert['coords']]

def certificate(points, degree_cap=32):
    sp = sympy_module()
    values = [sp.expand(v) for pt in points for v in pt]
    if any(v.has(sp.Float) for v in values):
        raise ValueError('algebraic:float')
    irrational = list(dict.fromkeys(v for v in values if not v.is_Rational))
    if not irrational:
        return {'type':'exact','field':{'minpoly':[0,1],'interval':['-1/1','1/1']},
                'coords':[[[textq(str(x))],[textq(str(y))]] for x,y in points]}
    theta = sp.to_number_field(irrational)
    if theta.minpoly.degree() > degree_cap:
        raise ValueError('algebraic:degree_cap')
    approx = complex(theta.root.evalf(70))
    if abs(approx.imag) > 1e-40:
        raise ValueError('algebraic:nonreal')
    p = sp.Poly(theta.minpoly).clear_denoms()[1]
    coeff = [int(c) for c in reversed(p.all_coeffs())]
    choices = [(a,b) for (a,b),m in p.intervals(eps=sp.Rational(1,2**40))
               if a != b and p.eval(a)*p.eval(b)<0]
    if not choices:
        raise ValueError('algebraic:no_sign_change')
    lo,hi = min(choices,key=lambda ab: abs(float((ab[0]+ab[1])/2)-approx.real))
    d = p.degree()
    @lru_cache(maxsize=256)
    def convert(v):
        if v.is_Rational:
            out = [v]
        else:
            out = list(reversed(sp.to_number_field(v,theta).coeffs()))
        return [f'{sp.numer(c)}/{sp.denom(c)}' for c in out+[sp.Integer(0)]*(d-len(out))]
    return {'type':'exact','field':{'minpoly':coeff,
            'interval':[f'{sp.numer(lo)}/{sp.denom(lo)}',f'{sp.numer(hi)}/{sp.denom(hi)}']},
            'coords':[[convert(sp.expand(x)),convert(sp.expand(y))] for x,y in points]}

def circles(a,b):
    sp = sympy_module()
    dx,dy = sp.expand(b[0]-a[0]),sp.expand(b[1]-a[1])
    d2 = sp.simplify(dx*dx+dy*dy)
    if d2 == 0 or d2.is_positive is False:
        return []
    disc = sp.simplify(1/d2-sp.Rational(1,4))
    if disc.is_negative or float(sp.re(disc.evalf())) < -1e-12:
        return []
    t = sp.sqrt(disc)
    mid = ((a[0]+b[0])/2,(a[1]+b[1])/2)
    return [tuple(sp.expand(z) for z in (mid[0]+sign*dy*t,mid[1]-sign*dx*t)) for sign in (1,-1)]

def rational_directions():
    sp = sympy_module()
    out = [(sp.Integer(-1),sp.Integer(0))]
    for t in (0,1,-1,sp.Rational(1,2),sp.Rational(-1,2),2,-2,sp.Rational(1,3)):
        t=sp.Rational(t)
        out.append((sp.cancel((1-t*t)/(1+t*t)),sp.cancel(2*t/(1+t*t))))
    return out

def cyclic_construction(n, edges):
    """Search two regular polygon layers with unit spokes, by graph structure.

    This enumerates a graph family and derives its coordinates. It contains
    no named graph codes or source coordinates.
    """
    if n<6 or n%2 or any(a.bit_count()!=3 for a in adjacency(n,edges)):
        return None
    from hosts import monomorphism
    sp=sympy_module();m=n//2
    pattern=adjacency(n,edges)
    for step in range(1,(m+1)//2):
        template=set()
        for v in range(m):
            template.update((tuple(sorted((v,(v+1)%m))),
                             tuple(sorted((m+v,m+(v+step)%m))), (v,m+v)))
        mapping,_=monomorphism(pattern,adjacency(n,template),10000)
        if mapping is None:continue
        R=1/(2*sp.sin(sp.pi/m));r=1/(2*sp.sin(sp.pi*step/m))
        c=sp.simplify((R*R+r*r-1)/(2*R*r));s=sp.sqrt(sp.simplify(1-c*c))
        if s.is_real is False:continue
        points=[]
        for v in range(m):
            angle=2*sp.pi*v/m
            points.append((sp.simplify(R*sp.cos(angle)),sp.simplify(R*sp.sin(angle))))
        for v in range(m):
            angle=2*sp.pi*v/m;x,y=sp.cos(angle),sp.sin(angle)
            points.append((sp.simplify(r*(c*x-s*y)),sp.simplify(r*(s*x+c*y))))
        if len(set(points))!=n:continue
        return certificate([points[v] for v in mapping]), {'reason':'cyclic_construction','polygon_size':m,'step':step}
    return None

def constructive(n, edges, seed, node_cap=2000):
    from lattice import search
    cyclic=cyclic_construction(n,edges)
    if cyclic is not None:return cyclic
    adj = adjacency(n,edges)
    remaining = set(range(n)); removed = []
    while remaining:
        candidates = [v for v in remaining if sum((adj[v]>>u)&1 for u in remaining)<=2]
        if not candidates:
            break
        v = min(candidates,key=lambda v:(sum((adj[v]>>u)&1 for u in remaining),v))
        remaining.remove(v); removed.append(v)
    if not removed:
        return None, {'reason':'no_degree_two_elimination','removed':0}
    if len(removed)>n:
        raise AssertionError
    core = sorted(remaining); inverse = {v:i for i,v in enumerate(core)}
    core_edges = [(inverse[u],inverse[v]) for u,v in edges if u in remaining and v in remaining]
    c,meta = search(len(core),core_edges,seed,node_cap=node_cap)
    if c is None:
        return None, {'reason':'core_not_embedded','removed':len(removed)}
    points = {v:p for v,p in zip(core,points_from_cert(c))}
    rng = random.Random(seed); dirs = rational_directions();rng.shuffle(dirs)
    order = list(reversed(removed)); tries = 0
    sp = sympy_module()
    def rec(k):
        nonlocal tries
        if k==len(order):
            return [points[v] for v in range(n)]
        v = order[k]; near = [u for u in points if adj[v]>>u&1]
        if len(near)==2:
            options = circles(points[near[0]],points[near[1]])
        elif len(near)==1:
            a = points[near[0]]
            options = [(a[0]+dx,a[1]+dy) for dx,dy in dirs]
        else:
            options = [(sp.Integer(8*n*len(points)),sp.Integer(0))]
        for p in options:
            tries+=1
            if tries>128:
                return None
            # This heuristic may discard close valid points. Acceptance below
            # still uses exact reduction and rational interval arithmetic.
            if any(sum(abs(complex((a-b).evalf())) for a,b in zip(p,q))<1e-10 for q in points.values()):
                continue
            points[v]=p
            result=rec(k+1)
            if result is not None:
                return result
            del points[v]
        return None
    result = rec(0)
    if result is None:
        return None, {'reason':'placement_exhausted','removed':len(removed),'placements':tries}
    return certificate(result), {'reason':'candidate','removed':len(removed),'placements':tries}
