"""Cross-check verify_refutations.py primitives against independent implementations."""
import os, sys, json, itertools
os.environ.setdefault('SYMPY_GROUND_TYPES', 'python')
import networkx as nx
import sympy
import verify_refutations as V

data = V.DEFAULT_DATA
g6s = [l.strip() for l in open(os.path.join(data, 'L10.g6')) if l.strip()]
bad = 0
for g in g6s:
    n, E = V.decode_g6(g)
    G = nx.from_graph6_bytes(g.encode())
    if n != G.number_of_nodes() or E != {tuple(sorted(e)) for e in G.edges()}:
        bad += 1
    # 4-cycles: sum over vertex pairs of C(common neighbours, 2), each cycle counted twice
    cnt = sum(len(set(G[u]) & set(G[v])) * (len(set(G[u]) & set(G[v])) - 1) // 2
              for u, v in itertools.combinations(range(n), 2)) // 2
    if cnt != len(V.four_cycles(n, E)):
        bad += 1
        print('4-cycle mismatch', g)
print('g6 + 4-cycle cross-check over', len(g6s), 'graphs, mismatches:', bad)
print('IISpZATaw edges', len(V.decode_g6('IISpZATaw')[1]), '(AMP: 20)')

# sympy re-expansion of polynomial identities for the smallest records of each type
want_types = {'null': 3, 'real': 3, 'null-dag': 3, 'real-dag': 3}
picked = {}
with open(sys.argv[1], 'rb') as fh:
    for line in fh:
        if len(line) > 400000:
            continue
        rec = json.loads(line)
        t = rec['cert']['type']
        if t in want_types and len(picked.setdefault(t, [])) < want_types[t]:
            picked[t].append(rec)

def sp_poly(terms, syms):
    expr = sympy.Integer(0)
    for c, e in terms:
        m = sympy.Rational(c)
        for s_, k in zip(syms, e):
            if k:
                m *= s_ ** k
        expr += m
    return sympy.Poly(expr, *syms, domain='QQ')

for t, recs in picked.items():
    for rec in recs:
        n, E = V.decode_g6(rec['g6'])
        c = rec['cert']
        a, b = c['frame']
        names = []
        for i in range(n):
            if i not in (a, b):
                names += ['x_%d' % i, 'y_%d' % i]
        names += ['t_%d' % k for k in range(len(c['sat']))]
        syms = sympy.symbols(names)
        S = dict(zip(names, syms))
        def X(i): return 0 if i == a else (1 if i == b else S['x_%d' % i])
        def Y(i): return 0 if i in (a, b) else S['y_%d' % i]
        gens = {}
        for (u, v) in sorted(E):
            if {u, v} != {a, b}:
                gens['e:%d,%d' % (u, v)] = sympy.Poly((X(u) - X(v))**2 + (Y(u) - Y(v))**2 - 1, *syms, domain='QQ')
        for k, (u, v) in enumerate(c['sat']):
            gens['s:%d,%d' % (u, v)] = sympy.Poly(S['t_%d' % k] * ((X(u) - X(v))**2 + (Y(u) - Y(v))**2) - 1, *syms, domain='QQ')
        if 'cofactors' in c:
            total = sympy.Poly(0, *syms, domain='QQ')
            for k, terms in c['cofactors'].items():
                total += sp_poly(terms, syms) * gens[k]
        else:
            aux = []
            for rw in c['rows']:
                P = sp_poly(rw['poly'], syms)
                acc = sympy.Poly(0, *syms, domain='QQ')
                for k, terms in rw['cofactors'].items():
                    src = gens[k] if k in gens else aux[int(k[4:])]
                    acc += sp_poly(terms, syms) * src
                assert acc == P, (rec['g6'], 'row identity fails in sympy')
                aux.append(P)
            total = aux[-1]
        target = sympy.Poly(1, *syms, domain='QQ') if t in ('null', 'null-dag') else sp_poly(c['f'], syms)
        print('sympy', t, rec['g6'], 'identity holds:', total == target)
