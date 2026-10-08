"""Exact finite-direction DFS in Q(sqrt(3), sqrt(11))."""
from functools import lru_cache
import random
from exact import Q, textq, adjacency

SCALE = 60
ZERO = (0,) * 8

def add(a, b):
    return tuple(x + y for x, y in zip(a, b))

def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))

def fieldmul(a, b):
    out = [Q(0)] * 4
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            overlap = i & j
            out[i ^ j] += x * y * (3 if overlap & 1 else 1) * (11 if overlap & 2 else 1)
    return tuple(out)

def cmul(a, b):
    ac, bd = fieldmul(a[:4], b[:4]), fieldmul(a[4:], b[4:])
    ad, bc = fieldmul(a[:4], b[4:]), fieldmul(a[4:], b[:4])
    return tuple(x-y for x,y in zip(ac,bd)) + tuple(x+y for x,y in zip(ad,bc))

def unit(a):
    x, y = a[:4], a[4:]
    return (sum(z[0]**2 + 3*z[1]**2 + 11*z[2]**2 + 33*z[3]**2 for z in (x,y)) == SCALE**2
        and sum(z[0]*z[1] + 11*z[2]*z[3] for z in (x,y)) == 0
        and sum(z[0]*z[2] + 3*z[1]*z[3] for z in (x,y)) == 0
        and sum(z[0]*z[3] + z[1]*z[2] for z in (x,y)) == 0)

@lru_cache(maxsize=3)
def directions(kind):
    one = (Q(1),) + (Q(0),)*7
    turn = (Q(1,2),0,0,0,0,Q(1,2),0,0)
    if kind == 'lattice36':
        turn = (0,Q(1,2),0,0,Q(1,2),0,0,0)
    base = [one, (Q(5,6),0,0,0,0,0,Q(1,6),0),
            (Q(5,6),0,0,0,0,0,Q(-1,6),0)]
    if kind == 'lattice30':
        base.extend([(Q(3,5),0,0,0,Q(4,5),0,0,0),
                     (Q(3,5),0,0,0,Q(-4,5),0,0,0)])
    out, rot = [], one
    for _ in range(12 if kind == 'lattice36' else 6):
        for b in base:
            values = [Q(v)*SCALE for v in cmul(rot,b)]
            assert all(v.denominator == 1 for v in values)
            z = tuple(int(v) for v in values)
            if z not in out:
                out.append(z)
        rot = cmul(rot,turn)
    assert all(unit(v) for v in out)
    return tuple(out), tuple(out[:len(base)])

def certificate(points):
    def convert(z):
        a,b,c,d = z
        return [textq(Q(a-7*d,SCALE)), textq(Q(-20*b+36*c,16*SCALE)),
                textq(Q(d,2*SCALE)), textq(Q(b-c,16*SCALE))]
    return {'type':'exact','field':{'minpoly':[64,0,-28,0,1],
             'interval':['5/1','6/1']},
            'coords':[[convert(p[:4]),convert(p[4:])] for p in points]}

def search(n, edges, seed, kind='lattice18', node_cap=20000):
    dirs, first_dirs = directions(kind)
    dirs, first_dirs = list(dirs), list(first_dirs)
    rng = random.Random(seed)
    rng.shuffle(dirs)
    rng.shuffle(first_dirs)
    adj = adjacency(n, edges)
    degrees = [a.bit_count() for a in adj]
    points, used = [None]*n, set()
    nodes = 0
    unit_cached = lru_cache(maxsize=20000)(unit)
    def rec(mask):
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            raise NodeLimit
        if mask == (1<<n)-1:
            return True
        v = max((v for v in range(n) if not (mask>>v)&1),
                key=lambda v: ((adj[v]&mask).bit_count(),degrees[v],-v))
        neighbors = [u for u in range(n) if (adj[v]&mask)>>u&1]
        if not neighbors:
            candidates = [ZERO if not mask else (SCALE*8*n*mask.bit_count(),)+(0,)*7]
        else:
            choices = first_dirs if mask.bit_count()==1 else dirs
            candidates = list(dict.fromkeys(add(points[u],d) for u in neighbors for d in choices))
        for z in candidates:
            if z in used or any(not unit_cached(sub(z,points[u])) for u in neighbors):
                continue
            points[v] = z
            used.add(z)
            if rec(mask | (1<<v)):
                return True
            used.remove(z)
            points[v] = None
        return False
    try:
        found = rec(0)
    except NodeLimit:
        return None, {'nodes':nodes, 'reason':'node_cap'}
    return (certificate(points) if found else None), {'nodes':nodes,'reason':'found' if found else 'exhausted'}

class NodeLimit(Exception):
    pass
