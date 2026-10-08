#!/usr/bin/env python3
"""crosscheck11.py: cross-check verify_refutations11.py's primitives against independent code.

Usage: python crosscheck11.py INDEX.jsonl OUT.json

1. graph6: every refuted record's g6 and every pointer target decoded by networkx agrees with
   the verifier's own decoder (vertex count 11, identical edge set).
2. 4-cycles: for 300 refuted graphs, the verifier's 4-cycle list agrees with the count
   sum over vertex pairs of C(common neighbours, 2) / 2.
3. Polynomial identities: the two smallest records of each polynomial type re-expanded in
   SymPy's sparse polynomial ring over QQ (pure Python, not FLINT), including the SOS
   expansion, and the univariate f's real-root count by SymPy.
4. nauty-labelg audits (do not affect verdicts): every refuted g6 and pointer target is in
   canonical form; the 398 F10 members are pairwise non-isomorphic; the sha256 of the sorted
   canonical forms of F10[0:74] and F10[74:398] (to compare with GP's 74 and GP-10's L10.g6).
"""
import os
os.environ.setdefault('SYMPY_GROUND_TYPES', 'python')
import sys
import json
import hashlib
import itertools
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_refutations11 as V          # noqa: E402
import networkx as nx                     # noqa: E402
import sympy                              # noqa: E402
from sympy import QQ                      # noqa: E402
from sympy.polys.rings import ring        # noqa: E402


def labelg(g6s):
    p = subprocess.run(['nauty-labelg', '-q'], input=''.join(x + '\n' for x in g6s).encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=600)
    out = p.stdout.decode().split('\n')
    assert len(out) >= len(g6s)
    return out[:len(g6s)]


def g6_encode(n, E):
    bits = [1 if (i, j) in E else 0 for j in range(1, n) for i in range(j)]
    while len(bits) % 6:
        bits.append(0)
    s = chr(63 + n)
    for k in range(0, len(bits), 6):
        v = 0
        for b in bits[k:k + 6]:
            v = (v << 1) | b
        s += chr(63 + v)
    return s


def qq(s):
    """A rational string 'p' or 'p/q' as an element of SymPy's QQ (own parser)."""
    if '/' in s:
        p, q = s.split('/')
        return QQ(int(p), int(q))
    return QQ(int(s))


def sympy_identity(rec):
    """Re-verify a polynomial certificate's identity in SymPy's sparse ring.  Returns a dict."""
    n, E = V.decode_g6(rec['g6'])
    c = rec['cert']
    a, b = c['frame']
    names = []
    for i in range(n):
        if i not in (a, b):
            names += ['x_%d' % i, 'y_%d' % i]
    names += ['t_%d' % k for k in range(len(c['sat']))]
    R, *gens = ring(','.join(names), QQ)
    S = dict(zip(names, gens))

    def X(i):
        return R(0) if i == a else (R(1) if i == b else S['x_%d' % i])

    def Y(i):
        return R(0) if i in (a, b) else S['y_%d' % i]

    def d2(u, v):
        return (X(u) - X(v)) ** 2 + (Y(u) - Y(v)) ** 2
    G = {}
    for (u, v) in sorted(E):
        if {u, v} != {a, b}:
            G['e:%d,%d' % (u, v)] = d2(u, v) - 1
    for k, (u, v) in enumerate(c['sat']):
        G['s:%d,%d' % (u, v)] = S['t_%d' % k] * d2(u, v) - 1

    def P(terms):
        return R({tuple(e): qq(q) for q, e in terms}) if terms else R(0)
    if 'cofactors' in c:
        total = R(0)
        for k, terms in c['cofactors'].items():
            total += P(terms) * G[k]
        rows = 0
    else:
        aux = []
        for ri, rw in enumerate(c['rows']):
            acc = R(0)
            for k, terms in rw['cofactors'].items():
                acc += P(terms) * (G[k] if k in G else aux[int(k[4:])])
            if acc != P(rw['poly']):
                return {'g6': rec['g6'], 'type': c['type'], 'rows': len(c['rows']), 'vars': len(names),
                        'identity_holds': False, 'failed_row': ri}
            aux.append(acc)
        total = aux[-1]
        rows = len(aux)
    out = {'g6': rec['g6'], 'type': c['type'], 'rows': rows, 'vars': len(names)}
    if c['type'] in ('null', 'null-dag'):
        out['identity_holds'] = total == R(1)
        return out
    f = P(c['f'])
    out['identity_holds'] = total == f
    if 'sos' in c:
        tot = R(qq(c['sos']['c']))
        for w, q in c['sos']['squares']:
            tot += qq(w) * P(q) ** 2
        out['sos_holds'] = (tot == f and sympy.Rational(c['sos']['c']) > 0 and
                            all(sympy.Rational(w) > 0 for w, _ in c['sos']['squares']))
    else:
        var = c['sturm']
        k = names.index(var)
        z = sympy.Symbol('z')
        expr = sympy.Integer(0)
        ok_uni = True
        for mon, coeff in f.terms():
            if any(e for i, e in enumerate(mon) if i != k):
                ok_uni = False
            expr += sympy.Rational(coeff.numerator, coeff.denominator) * z ** mon[k]
        out['univariate'] = ok_uni
        out['real_roots'] = int(sympy.Poly(expr, z).count_roots()) if ok_uni else None
        out['sturm_holds'] = ok_uni and out['real_roots'] == 0
    return out


def main(argv):
    index_path, dst = argv[1], argv[2]
    idx = V.load_index(index_path)
    with open(index_path + '.meta.json') as fh:
        records = json.load(fh)['records']
    report = {}
    # 1. graph6
    targets = sorted({e['g6'] for e in idx} | {e['ptr'] for e in idx if e['ptr']})
    bad = []
    for g in targets:
        n, E = V.decode_g6(g)
        Gx = nx.from_graph6_bytes(g.encode())
        if n != 11 or Gx.number_of_nodes() != 11 or E != {tuple(sorted(e)) for e in Gx.edges()}:
            bad.append(g)
    report['g6_decode'] = {'graphs': len(targets), 'mismatches': bad}
    # 2. 4-cycles
    mism = 0
    for g in targets[:300]:
        n, E = V.decode_g6(g)
        Gx = nx.from_graph6_bytes(g.encode())
        cnt = sum(len(set(Gx[u]) & set(Gx[v])) * (len(set(Gx[u]) & set(Gx[v])) - 1) // 2
                  for u, v in itertools.combinations(range(n), 2)) // 2
        mism += cnt != len(V.four_cycles(n, E))
    report['four_cycles'] = {'graphs': min(300, len(targets)), 'mismatches': mism}
    # 3. SymPy re-expansion
    fh = open(records, 'rb')
    res = []
    for typ in ('null', 'real', 'null-dag', 'real-dag'):
        es = sorted((e for e in idx if e['type'] == typ), key=lambda e: e['length'])
        picked = es[:2]
        if typ == 'real':
            # make sure both proof kinds are present
            kinds = {}
            for e in es:
                fh.seek(e['offset'])
                c = json.loads(fh.read(e['length']))['cert']
                kinds.setdefault('sturm' if 'sturm' in c else 'sos', e)
                if len(kinds) == 2:
                    break
            picked = list(kinds.values())
        if typ == 'real-dag':
            kinds = {}
            for e in es:
                fh.seek(e['offset'])
                c = json.loads(fh.read(e['length']))['cert']
                kinds.setdefault('sturm' if 'sturm' in c else 'sos', e)
                if len(kinds) == 2:
                    break
            picked = list(kinds.values())
        for e in picked:
            fh.seek(e['offset'])
            rec = json.loads(fh.read(e['length']))
            r = sympy_identity(rec)
            r['bytes'] = e['length']
            # red control for this instrument: one cofactor coefficient bumped must break it
            c = rec['cert']
            cof = c['cofactors'] if 'cofactors' in c else c['rows'][-1]['cofactors']
            k = next(kk for kk in sorted(cof) if cof[kk])
            q = qq(cof[k][0][0]) + 1
            cof[k][0][0] = '%d/%d' % (q.numerator, q.denominator) if q != 0 else '2'
            r['red_control_identity_holds'] = sympy_identity(rec)['identity_holds']
            res.append(r)
            sys.stderr.write('sympy %s\n' % json.dumps(r))
    report['sympy_reexpansion'] = res
    # 4. nauty-labelg audits
    canon = labelg(targets)
    noncanon = [g for g, c in zip(targets, canon) if g != c]
    # red control for this instrument: a relabelled copy must be flagged and map back
    n0, E0 = V.decode_g6(targets[0])
    perm = list(range(n0))[::-1]
    relab = g6_encode(n0, {tuple(sorted((perm[u], perm[v]))) for u, v in E0})
    back = labelg([relab])[0]
    report['canonical_red_control'] = {'relabelled': relab, 'flagged': relab != back,
                                       'maps_back_to_original': back == targets[0]}
    report['canonical_g6'] = {'graphs': len(targets), 'non_canonical': noncanon[:20],
                              'non_canonical_count': len(noncanon)}
    ctx = V.load_context(V.DEFAULT_DATA)
    f10 = [g6_encode(k, E) for k, E in ctx['forbidden']]
    fc = labelg(f10)
    report['F10'] = {
        'members': len(fc), 'distinct_canonical_forms': len(set(fc)),
        'sha256_sorted_canonical_0_74': hashlib.sha256(''.join(x + '\n' for x in sorted(fc[:74])).encode()).hexdigest(),
        'sha256_sorted_canonical_74_398': hashlib.sha256(''.join(x + '\n' for x in sorted(fc[74:])).encode()).hexdigest(),
        'note': 'compare the second digest with sha256 of GP-10 L10.g6 (sorted canonical, newline-terminated)'}
    with open(os.path.join(os.path.dirname(os.path.abspath(dst)), 'F10-74-398-canonical.g6'), 'w') as fo:
        fo.write(''.join(x + '\n' for x in sorted(fc[74:])))
    ok = (not bad and mism == 0 and all(r['identity_holds'] and r.get('sos_holds', True) and
                                         r.get('sturm_holds', True) and not r['red_control_identity_holds']
                                         for r in res)
          and report['canonical_red_control']['flagged'] and report['canonical_red_control']['maps_back_to_original'])
    report['all_agree'] = ok
    with open(dst, 'w') as fo:
        json.dump(report, fo, indent=1)
    print(json.dumps({k: (v if k != 'sympy_reexpansion' else len(v)) for k, v in report.items()}, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
