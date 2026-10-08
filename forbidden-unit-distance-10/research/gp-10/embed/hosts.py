"""Bitset monomorphisms and exact GP/AMP coordinate candidates."""
import ast
import json
from functools import lru_cache
from pathlib import Path
from exact import adjacency, graph6

HERE=Path(__file__).resolve().parent

def expression(text, numeric=False):
    if numeric:
        import mpmath as m
        m.mp.dps=60
        integer=m.mpf;root=m.sqrt
    else:
        from algebraic import sympy_module
        sp=sympy_module();integer=sp.Integer;root=sp.sqrt
    names={'ROOT3':root(integer(3)),'ROOT11':root(integer(11)),'ROOT33':root(integer(33))}
    names['EXTRA']=root((11+4*names['ROOT33'])/148)
    def ev(n):
        if isinstance(n,ast.Constant) and type(n.value) is int:return integer(n.value)
        if isinstance(n,ast.Name) and n.id in names:return names[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -ev(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
            if isinstance(n.op,ast.Pow):return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):
            values=[ev(a) for a in n.args]
            if n.func.id=='sqrt' and len(values)==1:return root(values[0])
            if n.func.id=='Integer' and len(values)==1:return values[0]
            if n.func.id=='Rational' and len(values)==2:return values[0]/values[1]
        raise ValueError('host:unsupported_expression')
    return ev(ast.parse(text,mode='eval').body)

@lru_cache(maxsize=1)
def database():
    import mpmath as mp
    raw=json.loads((HERE/'host_sources.json').read_text())['hosts']
    ready={}
    compiled=HERE/'host_certificates.json'
    exact=json.loads(compiled.read_text()) if compiled.exists() else {}
    for name in ('G27','G118','AMP33','G118_simple'):
        if name not in raw:continue
        exprs=raw[name]
        p=[tuple(expression(v,True) for v in pt) for pt in exprs]
        if any(abs(mp.im(c))>mp.mpf('1e-45') for pt in p for c in pt):
            raise ValueError('host:nonreal_source')
        # Numeric adjacency proposes mappings only. Every output must be
        # converted to a power basis and checked against the INPUT edges.
        p=[tuple(mp.re(v) for v in pt) for pt in p]
        edges=[(u,v) for v in range(len(p)) for u in range(v)
               if abs(sum((p[u][k]-p[v][k])**2 for k in (0,1))-1)<mp.mpf('1e-40')]
        ready[name]={'expressions':exprs,'adj':adjacency(len(p),edges),'edges':edges,
                     'exact':exact.get(name),'size':len(p)}
    return ready

def monomorphism(pattern, host, node_cap=100000):
    """Injective non-induced embedding. Extra host edges are unrestricted."""
    n,m=len(pattern),len(host)
    if n>m:return None,0
    hd=[a.bit_count() for a in host];pd=[a.bit_count() for a in pattern]
    initial=[sum(1<<v for v in range(m) if hd[v]>=pd[u]) for u in range(n)]
    mapping=[-1]*n;nodes=0
    def rec(left,used):
        nonlocal nodes
        nodes+=1
        if nodes>node_cap:return False
        if not left:return True
        best=None
        for u in left:
            candidates=initial[u]&~used
            for v in range(n):
                if mapping[v]>=0 and pattern[u]>>v&1:
                    candidates &= host[mapping[v]]
            if not candidates:return False
            score=(candidates.bit_count(),-sum(mapping[v]>=0 and bool(pattern[u]>>v&1) for v in range(n)),-pd[u],u)
            if best is None or score<best[0]:best=(score,u,candidates)
        _,u,candidates=best
        rest=left-{u}
        while candidates:
            bit=candidates&-candidates;candidates-=bit
            v=bit.bit_length()-1;mapping[u]=v
            if rec(rest,used|bit):return True
            mapping[u]=-1
        return False
    return (mapping[:] if rec(set(range(n)),0) else None),nodes

def check_mapping(pattern,host,mapping):
    if len(mapping)!=len(pattern) or any(type(v) is not int or v<0 or v>=len(host) for v in mapping):
        raise ValueError('host_map:range')
    if len(set(mapping))!=len(mapping):raise ValueError('host_map:noninjective')
    for u in range(len(pattern)):
        for v in range(u+1,len(pattern)):
            if pattern[u]>>v&1 and not host[mapping[u]]>>mapping[v]&1:
                raise ValueError(f'host_map:edge:{u},{v}')
    return True

def search(n,edges,seed,node_cap=100000):
    from algebraic import certificate
    pattern=adjacency(n,edges);attempts=[]
    # The compact exact hosts are cheaper than the full nested radical host.
    db=database()
    for name in ('G27','AMP33','G118_simple','G118'):
        if name not in db:continue
        host=db[name]
        mapping,nodes=monomorphism(pattern,host['adj'],node_cap)
        attempts.append({'host':name,'nodes':nodes,'matched':mapping is not None})
        if mapping is None:continue
        check_mapping(pattern,host['adj'],mapping)
        if host['exact'] is not None:
            source=host['exact']
            c={'type':'exact','field':source['field'],'coords':[source['coords'][v] for v in mapping]}
        else:
            points=[tuple(expression(c) for c in host['expressions'][v]) for v in mapping]
            c=certificate(points)
        return c,{'reason':'candidate','host':name,'map':mapping,'attempts':attempts}
    return None,{'reason':'no_host_match','attempts':attempts}
