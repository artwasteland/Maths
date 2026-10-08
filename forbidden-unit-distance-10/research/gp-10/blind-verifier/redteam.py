#!/usr/bin/env python3
"""redteam.py: mutation controls for verify_refutations.py.

Usage: python redteam.py ../data/records.jsonl redteam.json

Picks real records of every certificate type, checks that each original is ACCEPTED, then
applies mutations (each asserted to change the record) and requires REJECT for every one.
Also includes 'attack' certificates: syntactically valid certificates that would prove a
false or unproved statement if a verifier were too lax (e.g. a saturation pair [u,u], whose
Rabinowitsch polynomial is the constant -1).
"""
import os
os.environ.setdefault('SYMPY_GROUND_TYPES', 'python')
import sys
import json
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_refutations as V

# records used as mutation sources (chosen from the survey; small and covering every branch)
PICK = {
    'tu_forbidden': 'I?ERPrCwW',      # one step, forbidden-74[17] end
    'tu_refuted': 'I?CYKMqYO',        # one step, end at refuted record I?GPYMX{? (a tree)
    'tu_two_step': 'IAh?HKyco',       # two steps (gadget 0 then gadget 5), forbidden end
    'tu_target_tree': 'I?GPYMX{?',
    'tu_pointing_to_tu': 'I?l@Glo_w',  # end at refuted IAh?HKyco (itself a tu record)
    'null': 'I?D@Yib}?',
    'null2': 'I?EJPjOwW',
    'null_dag': 'IRaAQGbFG',
    'null_dag2': 'IhEEOgdAw',
    'real_sos': 'I@@KTHQMW',
    'real_sturm': None,               # filled by scanning (smallest real+sturm)
    'real_dag_sos': 'I_CbWyooW',
    'real_dag_sturm': 'IGDLGqPwW',
    'tree_L2_L1a': 'I??OzIJ}?',
    'tree_L3_L1a': 'I?L@GuTw_',
    'tree_L3_L1c': 'I@AGv@M[o',
    'tree_L1b': 'I@hUE?hDg',
    'tree_big': 'I?_y`fGwW',
}


def load_records(path):
    want = {g for g in PICK.values() if g}
    got = {}
    best_sturm = None
    with open(path, 'rb') as fh:
        for line in fh:
            rec = json.loads(line)
            g = rec['g6']
            if g in want:
                got[g] = rec
            c = rec['cert']
            if c['type'] == 'real' and 'sturm' in c:
                if best_sturm is None or len(line) < best_sturm[0]:
                    best_sturm = (len(line), g, rec)
    PICK['real_sturm'] = best_sturm[1]
    got[best_sturm[1]] = best_sturm[2]
    return got


def dumps(rec):
    return (json.dumps(rec) + '\n').encode()


def run(lines_by_g6, ctx, focus):
    """Verify every given record line and resolve pointers among them; return focus result."""
    res = [V.verify_line(line, ctx) for line in lines_by_g6]
    V.resolve(res)
    for r in res:
        if r.get('g6') == focus or (focus is None):
            return r
    return res[0]


# ------------------------------------------------------------------------------ helpers

def bump(c):
    """Return a different rational string."""
    q = V.parse_rat_str(c, 'bump') + 1
    return str(q.p) if q.q == 1 else '%d/%d' % (q.p, q.q)


def neg(x):
    q = -V.parse_rat_tree(x, 'neg')
    return str(q.p) if q.q == 1 else '%d/%d' % (q.p, q.q)


def first_nonempty_cofactor(cof):
    for k in sorted(cof):
        if cof[k]:
            return k
    raise RuntimeError('no nonempty cofactor')


def walk(node, path=()):
    yield path, node
    for i, c in enumerate(node['children']):
        yield from walk(c, path + (i,))


def node_at(tree, path):
    n = tree
    for i in path:
        n = n['children'][i]
    return n


def find(tree, kind):
    for p, n in walk(tree):
        if n['move']['kind'] == kind:
            return p, n
    raise RuntimeError('no %s node' % kind)


def g6_encode(n, E):
    bits = []
    for j in range(1, n):
        for i in range(j):
            bits.append(1 if (i, j) in E else 0)
    while len(bits) % 6:
        bits.append(0)
    out = chr(63 + n)
    for k in range(0, len(bits), 6):
        v = 0
        for b in bits[k:k + 6]:
            v = (v << 1) | b
        out += chr(63 + v)
    return out


# ------------------------------------------------------------------------------ mutations

def tu_mutations(recs):
    out = []
    g = PICK['tu_forbidden']
    base = recs[g]
    n, E = V.decode_g6(g)

    def m(desc, f, extra=None, focus=None):
        r = copy.deepcopy(base)
        f(r)
        out.append(('tu', g if focus is None else focus, desc, r, extra))

    m('duplicate the step: the second application points at a pair that is already an edge',
      lambda r: r['cert']['steps'].append(copy.deepcopy(r['cert']['steps'][0])))
    step_pair = tuple(base['cert']['steps'][0]['pair'])

    def add_pair_edge(r):
        E2 = set(E)
        E2.add(V.norm_edge(*step_pair))
        r['g6'] = g6_encode(n, E2)
    m('graph already contains the step pair as an edge (step points at an existing edge)',
      add_pair_edge)

    def swap_step_map(r):
        mp = r['cert']['steps'][0]['map']
        mp[0], mp[1] = mp[1], mp[0]
    m('swap two entries of the step map', swap_step_map)

    def swap_end_map(r):
        mp = r['cert']['end']['map']
        mp[0], mp[2] = mp[2], mp[0]
    m('swap two entries of the end (forbidden) map', swap_end_map)

    def end_idx(r):
        r['cert']['end']['forbidden'] = 16
    m('end cites a different forbidden-74 index (16 instead of 17)', end_idx)

    def gad_idx(r):
        r['cert']['steps'][0]['gadget'] = 1
    m('step cites a different gadget (1 instead of 0)', gad_idx)

    def pair_wrong(r):
        st = r['cert']['steps'][0]
        img = set(st['pair'])
        other = next(v for v in range(n) if v not in img)
        st['pair'] = [st['pair'][0], other]
    m('step pair is not the image of the distinguished pair', pair_wrong)

    def noninj(r):
        mp = r['cert']['end']['map']
        mp[1] = mp[0]
    m('end map not injective', noninj)

    def empty_steps(r):
        r['cert']['steps'] = []
    m('zero-step chain (direct containment is an R-ptr, not a tu chain)', empty_steps)

    def extra(r):
        r['cert']['note'] = 'x'
    m('unknown extra field in the certificate', extra)

    def verdict_tu(r):
        r['verdict'] = 'tu'
    m('record verdict "tu" instead of "refuted" (contract red fixture)', verdict_tu)

    def bool_vertex(r):
        r['cert']['steps'][0]['gadget'] = False  # boolean in place of integer 0
    m('boolean in place of the integer gadget index', bool_vertex)

    # two-step chain: drop the first step so the second map loses its added edge
    g2 = PICK['tu_two_step']
    b2 = recs[g2]
    r = copy.deepcopy(b2)
    del r['cert']['steps'][0]
    out.append(('tu', g2, 'two-step chain with its first step deleted', r, None))
    r = copy.deepcopy(b2)
    r['cert']['steps'].reverse()
    out.append(('tu', g2, 'two-step chain with its steps reversed', r, None))

    # refuted end: target not in the run / target rejected / pointer cycle
    g3 = PICK['tu_refuted']
    tgt = PICK['tu_target_tree']
    r = copy.deepcopy(recs[g3])
    r['cert']['end']['refuted'] = 'I??OzIJ}?' if False else g6_encode(10, {(i, j) for i in range(10) for j in range(i + 1, 10) if (i + j) % 3 == 0})
    out.append(('tu', g3, 'end points at a refuted-graph g6 with no record in the run', r,
                {'with': [tgt]}))
    tmut = copy.deepcopy(recs[tgt])
    tmut['cert']['witness']['tree']['move']['omega'] = [1] if tmut['cert']['witness']['tree']['move'].get('omega') != [1] else [-1]
    out.append(('tu', g3, 'end target record is present but its own certificate is broken', copy.deepcopy(recs[g3]),
                {'with_records': [tmut]}))
    # a pointer cycle: the chain ends at the record ITSELF with the identity map, which IS
    # edge-preserving into G + pair, so only cycle detection can reject it
    ra = copy.deepcopy(recs[g])
    ra['cert']['end'] = {'refuted': g, 'map': list(range(10))}
    out.append(('tu', g, 'pointer cycle: chain ends at its own record (identity map is valid)', ra, None))
    # a two-record cycle: A -> B -> A where B is A's chain pointing back
    ga = PICK['tu_pointing_to_tu']   # I?l@Glo_w -> IAh?HKyco
    gb = PICK['tu_two_step']
    rb = copy.deepcopy(recs[gb])
    rb['cert']['end'] = {'refuted': ga, 'map': list(range(10))}
    out.append(('tu', ga, 'two-record pointer loop (target rewritten to point back)', copy.deepcopy(recs[ga]),
                {'with_records': [rb]}))
    return out


def poly_common_mutations(kind, g, base, out):
    c = base['cert']

    def m(desc, f):
        r = copy.deepcopy(base)
        f(r['cert'])
        out.append((kind, g, desc, r, None))

    n, E = V.decode_g6(g)
    fa, fb = c['frame']
    nonedge = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E)

    def frame_nonedge(cc):
        cc['frame'] = [nonedge[0], nonedge[1]]
    m('frame is a non-edge (contract red fixture)', frame_nonedge)

    def frame_rev(cc):
        cc['frame'] = [fb, fa]
    m('frame reversed (a valid frame, but a different system)', frame_rev)

    if len(c['sat']) >= 2:
        def sat_swap(cc):
            cc['sat'][0], cc['sat'][1] = cc['sat'][1], cc['sat'][0]
        m('swap two saturation entries (t-variable naming changes)', sat_swap)

    def sat_dup(cc):
        cc['sat'].append(list(cc['sat'][0]))
    m('duplicated saturation pair', sat_dup)

    def extra(cc):
        cc['comment'] = 'x'
    m('unknown extra field', extra)


def null_mutations(recs):
    out = []
    for key in ('null', 'null2'):
        g = PICK[key]
        base = recs[g]

        def m(desc, f):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append(('null', g, desc, r, None))

        def coef(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            cc['cofactors'][k][0][0] = bump(cc['cofactors'][k][0][0])
        m('change one rational coefficient of one cofactor', coef)

        def drop_term(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            del cc['cofactors'][k][-1]
        m('drop one cofactor term', drop_term)

        def drop_key(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            del cc['cofactors'][k]
        m('drop one whole cofactor', drop_key)

        if key == 'null':
            n, E = V.decode_g6(g)
            nonedge = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E)

            def extra_gen(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors']['e:%d,%d' % nonedge] = copy.deepcopy(cc['cofactors'][k])
            m('extra non-edge-equals-1 generator e:u,v for a non-edge (contract red fixture)', extra_gen)

            def num_coef(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                t = cc['cofactors'][k][0]
                q = V.parse_rat_str(t[0], 'x')
                t[0] = int(q.p) if q.q == 1 else t[0]
                if not isinstance(t[0], int):
                    t[0] = 1
            m('coefficient as a JSON number instead of a rational string', num_coef)

            def dup_mono(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                t = copy.deepcopy(cc['cofactors'][k][0])
                t[0] = '0'
                cc['cofactors'][k].append(t)
            m('duplicate monomial (zero-coefficient copy of an existing term)', dup_mono)

            def bad_system(cc):
                # a stated system that differs from the regenerated one in one generator
                sysm = V.System(n, E, cc['frame'], cc['sat'])
                st = {}
                for k2, gpoly in sysm.gens.items():
                    terms = []
                    for exps, cf in gpoly.to_dict().items():
                        terms.append([str(cf), [int(e) for e in exps]])
                    st[k2] = terms
                k0 = sorted(st)[0]
                st[k0][0][0] = bump(st[k0][0][0])
                cc['system'] = st
            m('stated system present but one generator differs from the regenerated one', bad_system)

            def exp_len(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors'][k][0][1] = cc['cofactors'][k][0][1] + [0]
            m('exponent vector one entry too long', exp_len)

        poly_common_mutations('null', g, base, out)
    return out


def dag_mutations(recs, kind, keys):
    out = []
    for key in keys:
        g = PICK[key]
        base = recs[g]

        def m(desc, f):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append((kind, g, desc, r, None))

        def row_cof(cc):
            row = next(rw for rw in cc['rows'] if any(rw['cofactors'].values()))
            k = first_nonempty_cofactor(row['cofactors'])
            row['cofactors'][k][0][0] = bump(row['cofactors'][k][0][0])
        m('change one coefficient of a row cofactor', row_cof)

        def row_poly(cc):
            row = next(rw for rw in cc['rows'] if rw['poly'])
            row['poly'][0][0] = bump(row['poly'][0][0])
        m('change one coefficient of a row polynomial', row_poly)

        def drop_cof_term(cc):
            row = next(rw for rw in cc['rows'] if any(len(v) > 1 for v in rw['cofactors'].values()))
            k = next(kk for kk in sorted(row['cofactors']) if len(row['cofactors'][kk]) > 1)
            del row['cofactors'][k][-1]
        m('drop one cofactor term in a row', drop_cof_term)

        def self_ref(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:')]
                if auxk:
                    rw['cofactors']['aux:%d' % k] = rw['cofactors'].pop(auxk[0])
                    return
            raise RuntimeError('no aux reference')
        m('self reference aux:k in row k', self_ref)

        def fwd_ref(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:')]
                if auxk and k + 1 < len(cc['rows']):
                    rw['cofactors']['aux:%d' % (k + 1)] = rw['cofactors'].pop(auxk[0])
                    return
            nv = len(cc['rows'][0]['poly'][0][1])
            cc['rows'][0]['cofactors']['aux:1'] = [['1', [0] * nv]]
        m('forward reference to a later row', fwd_ref)

        def lead_zero(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:') and kk != 'aux:0']
                if auxk:
                    j = auxk[0][4:]
                    rw['cofactors']['aux:0' + j] = rw['cofactors'].pop(auxk[0])
                    return
            raise RuntimeError('no aux reference')
        m('aux index spelled with a leading zero', lead_zero)

        def drop_last(cc):
            cc['rows'].pop()
        m('drop the last row', drop_last)

        def swap_terms(cc):
            row = next(rw for rw in cc['rows'] if len(rw['poly']) >= 2)
            row['poly'][0], row['poly'][1] = row['poly'][1], row['poly'][0]
        m('two terms of a row polynomial out of lexicographic order', swap_terms)

        def zero_term(cc):
            row = cc['rows'][0]
            nv = len(row['poly'][0][1])
            big = [50] * nv
            row['poly'].append(['0', big])
        m('zero-coefficient term appended to a row polynomial', zero_term)

        def too_many(cc):
            nv = len(cc['rows'][0]['poly'][0][1])
            last = cc['rows'].pop()
            for _ in range(257):
                cc['rows'].append({'poly': [], 'cofactors': {}})
            cc['rows'].append(last)
        m('more than 256 rows (padding with zero rows)', too_many)

        def bogus_src(cc):
            row = cc['rows'][0]
            k = first_nonempty_cofactor(row['cofactors'])
            row['cofactors']['q:1,2'] = row['cofactors'].pop(k)
        m('unknown source name', bogus_src)

        def row_extra(cc):
            cc['rows'][0]['note'] = 1
        m('extra field in a row', row_extra)

        if kind == 'null-dag':
            def last_two(cc):
                cc['rows'][-1]['poly'][0][0] = '2'
            m('last row claims 2 instead of the derived value', last_two)

            def claim_one(cc):
                cc['rows'] = [{'poly': [['1', [0] * len(cc['rows'][0]['poly'][0][1])]], 'cofactors': {}}]
            m('attack: a single row claiming 1 with no cofactors', claim_one)
        poly_common_mutations(kind, g, base, out)
    return out


def real_mutations(recs, kind, keys, common=True):
    out = []
    for key in keys:
        g = PICK[key]
        base = recs[g]

        def m(desc, f):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append((kind, g, desc, r, None))

        def f_coef(cc):
            cc['f'][0][0] = bump(cc['f'][0][0])
        m('change one coefficient of f', f_coef)

        if kind == 'real':
            def drop_term(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                del cc['cofactors'][k][-1]
            m('drop one cofactor term', drop_term)

            def coef(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors'][k][0][0] = bump(cc['cofactors'][k][0][0])
            m('change one rational coefficient of one cofactor', coef)
        else:
            def row_cof(cc):
                row = next(rw for rw in cc['rows'] if any(rw['cofactors'].values()))
                k = first_nonempty_cofactor(row['cofactors'])
                row['cofactors'][k][0][0] = bump(row['cofactors'][k][0][0])
            m('change one coefficient of a row cofactor', row_cof)

            def last_row_f(cc):
                cc['rows'][-1]['poly'][0][0] = bump(cc['rows'][-1]['poly'][0][0])
            m('last row polynomial differs from f', last_row_f)

        if 'sos' in base['cert']:
            def c_zero(cc):
                cc['sos']['c'] = '0'
            m('SOS constant c = 0 (contract red fixture)', c_zero)

            def c_neg(cc):
                cc['sos']['c'] = '-' + cc['sos']['c'].lstrip('+-')
            m('SOS constant c negative', c_neg)

            def w_neg(cc):
                if cc['sos']['squares']:
                    cc['sos']['squares'][0][0] = '-' + cc['sos']['squares'][0][0].lstrip('+-')
            m('SOS weight negative', w_neg)

            def drop_sq(cc):
                cc['sos']['squares'].pop()
            m('drop one SOS square', drop_sq)

            def both(cc):
                cc['sturm'] = 'x_%d' % next(i for i in range(10) if i not in cc['frame'])
            m('both sturm and sos present', both)
        else:
            def other_var(cc):
                n, E = V.decode_g6(g)
                sysm = V.System(n, E, cc['frame'], cc['sat'])
                cc['sturm'] = next(v for v in sysm.names if v != cc['sturm'])
            m('Sturm names a different variable than the one f uses', other_var)

            def bad_var(cc):
                cc['sturm'] = 'x_%d' % cc['frame'][0]
            m('Sturm names a frame coordinate that is not a variable', bad_var)

            def to_sos(cc):
                del cc['sturm']
                cc['sos'] = {'c': '1', 'squares': []}
            m('Sturm proof replaced by an SOS claim f = 1', to_sos)
        if common:
            poly_common_mutations(kind, g, base, out)
    return out


def attack_certificates(recs):
    """Certificates that would prove falsehoods if the verifier were lax."""
    out = []
    g = PICK['null']
    n, E = V.decode_g6(g)
    a, b = recs[g]['cert']['frame']
    nv0 = 2 * (n - 2)
    # 1. saturation pair [u,u]: t*d2(u,u) - 1 = -1, so cofactor -1 gives 1
    u = next(i for i in range(n) if i not in (a, b))
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'null', 'frame': [a, b], 'sat': [[u, u]],
         'cofactors': {'s:%d,%d' % (u, u): [['-1', [0] * (nv0 + 1)]]}}}
    out.append(('null', g, 'attack: saturation pair [u,u] (generator = -1)', r, None))
    # 2. same with reversed pair [v,u] with v > u and a real pair, cofactor making 1 impossible
    #    -> exercises u < v rule
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'null', 'frame': [a, b], 'sat': [[max(a, b), min(a, b)]],
         'cofactors': {}}}
    out.append(('null', g, 'attack: saturation pair stored with u > v', r, None))
    # 3. frame pinned on a NON-edge: p(a)=(0,0), p(b)=(1,0) with an edge equation for a pair
    #    that includes a third pinned vertex is impossible to state; instead frame = [a, a]
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'null', 'frame': [a, a], 'sat': [], 'cofactors': {}}}
    out.append(('null', g, 'attack: degenerate frame [a, a]', r, None))
    # 4. Sturm on a univariate f WITH a real root: s:a,b gives t_0*1 - 1 = t_0 - 1
    lo, hi = min(a, b), max(a, b)
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'real', 'frame': [a, b], 'sat': [[lo, hi]],
         'cofactors': {'s:%d,%d' % (lo, hi): [['1', [0] * (nv0 + 1)]]},
         'f': [['-1', [0] * (nv0 + 1)], ['1', [0] * nv0 + [1]]], 'sturm': 't_0'}}
    out.append(('real', g, 'attack: identity is valid but f = t_0 - 1 has a real root (Sturm must say 1)', r, None))
    # 5. SOS claiming f = t_0 - 1 is a positive constant
    r = copy.deepcopy(r)
    del r['cert']['sturm']
    r['cert']['sos'] = {'c': '1', 'squares': []}
    out.append(('real', g, 'attack: f = t_0 - 1 with a bogus SOS c=1 and no squares', r, None))
    # 6. real-dag: zero f with Sturm
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'real-dag', 'frame': [a, b], 'sat': [],
         'rows': [{'poly': [], 'cofactors': {}}], 'f': [], 'sturm': 'x_%d' % u}}
    out.append(('real-dag', g, 'attack: f = 0 (the zero polynomial) with Sturm', r, None))
    return out


def tree_mutations(recs):
    out = []

    def m(key, desc, f):
        g = PICK[key]
        r = copy.deepcopy(recs[g])
        f(r['cert']['witness'])
        out.append(('tree', g, desc, r, None))

    def alter_root_A(w):
        A = w['tree']['A']
        e = A[0][0]
        A[0][0] = [2] if e != [2] else [3]
    m('tree_L2_L1a', 'alter one entry of the root matrix A', alter_root_A)

    def alter_deep_A(w):
        p, nd = find(w['tree'], 'L1a')
        nd['A'][-1][-1] = ['7/3']
    m('tree_L2_L1a', 'alter one entry of the leaf matrix A', alter_deep_A)

    def drop_A_row(w):
        w['tree']['A'].pop()
    m('tree_L2_L1a', 'delete one row of the root matrix A (strictness: row-space equality)', drop_A_row)

    def add_A_row(w):
        row = [[0]] * 10
        row = [list(x) for x in row]
        row[0] = [1]
        row[1] = [-1]
        w['tree']['A'].append(row)
        w['tree']['move'] = {'kind': 'L1a', 'pair': [0, 1]}
        w['tree']['children'] = []
    m('tree_L2_L1a', 'attack: root A gains the unproved row e0-e1 and the root becomes an L1a leaf', add_A_row)

    def del_child_L2(w):
        p, nd = find(w['tree'], 'L2')
        nd['children'] = []
    m('tree_L2_L1a', 'delete the child of an L2 node', del_child_L2)

    def omega_flip(w):
        p, nd = find(w['tree'], 'L2')
        om = nd['move']['omega']
        nd['move']['omega'] = [1] if om == [-1] else [-1]
    m('tree_L2_L1a', 'flip the sign of an L2 omega', omega_flip)

    def omega_nonunit(w):
        p, nd = find(w['tree'], 'L2')
        nd['move']['omega'] = [2]
    m('tree_L2_L1a', 'L2 omega of modulus 2', omega_nonunit)

    def l2_existing(w):
        p, nd = find(w['tree'], 'L2')
        nd['move']['edges'][1] = list(nd['move']['edges'][0])
    m('tree_L2_L1a', 'L2 second pair is already an edge', l2_existing)

    def l1a_pair(w):
        p, nd = find(w['tree'], 'L1a')
        u, v = nd['move']['pair']
        nd['move']['pair'] = [u, 9 if v != 9 else 8]
    m('tree_L2_L1a', 'L1a names a pair that is not forced to collide', l1a_pair)

    def root_edges(w):
        E = w['tree']['edges']
        n, Eg = V.decode_g6(PICK['tree_L2_L1a'])
        ne = next([u, v] for u in range(10) for v in range(u + 1, 10) if (u, v) not in Eg)
        E.append(ne)
        E.sort()
    m('tree_L2_L1a', 'root graph state gains a non-edge', root_edges)

    def child_edges(w):
        p, nd = find(w['tree'], 'L1a')
        nd['edges'].pop()
    m('tree_L2_L1a', 'leaf graph state loses an edge', child_edges)

    def interval_bad(w):
        w['field']['interval'] = [1, 2]
    m('tree_L2_L1a', 'field interval without a root', interval_bad)

    def whole_leaf(w):
        t = w['tree']
        t['move'] = {'kind': 'L1a', 'pair': [0, 1]}
        t['children'] = []
    m('tree_L2_L1a', 'attack: root replaced by an unforced L1a leaf', whole_leaf)

    # L3 / L1a tree over Q(sqrt 3)
    def d_bad(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['d'] = [0, 2]
    m('tree_L3_L1a', 'L3 d changed (d^2 != discriminant)', d_bad)

    def l3_one_child(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'].pop()
    m('tree_L3_L1a', 'delete one child of an L3 node', l3_one_child)

    def l3_swap(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'].reverse()
    m('tree_L3_L1a', 'swap the two L3 children (+d / -d branches)', l3_swap)

    def l3_dup(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'][1] = copy.deepcopy(nd['children'][0])
    m('tree_L3_L1a', 'L3 second child replaced by a copy of the first (one branch covered twice)', l3_dup)

    def l3_coef(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['coefficients'][2] = [2]
    m('tree_L3_L1a', 'L3 coefficient changed', l3_coef)

    def l3_zero(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['coefficients'][1] = [0]
    m('tree_L3_L1a', 'L3 coefficient zero', l3_zero)

    def minpoly_red(w):
        w['field']['minpoly'] = [-3, 0, 1, 0]  # leading zero coefficient
    m('tree_L3_L1a', 'minpoly with a zero leading coefficient', minpoly_red)

    def minpoly_reducible(w):
        w['field']['minpoly'] = [0, -3, 0, 1]  # x^3 - 3x = x (x^2 - 3), reducible
        w['field']['interval'] = ['32592/18817', '18817/10864']
    m('tree_L3_L1a', 'reducible minpoly x^3 - 3x', minpoly_reducible)

    def entry_float_like(w):
        w['tree']['A'][0][0] = ['1.0']
    m('tree_L3_L1a', 'decimal string entry in A', entry_float_like)

    # L3 with L1c leaves
    def l1c_coef(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['coefficients'] = [[1], [1], [1]]
    m('tree_L3_L1c', 'L1c coefficients replaced by (1,1,1): relation not forced and discriminant 3 > 0', l1c_coef)

    def l1c_disc(w):
        p, nd = find(w['tree'], 'L1c')
        # keep the relation but make it a positive-discriminant claim by scaling one coefficient
        cs = nd['move']['coefficients']
        nd['move']['coefficients'] = [cs[0], cs[1], cs[2]]
        nd['move']['kind'] = 'L1c'
        nd['move']['edges'][0], nd['move']['edges'][1] = nd['move']['edges'][1], nd['move']['edges'][0]
    m('tree_L3_L1c', 'L1c edges swapped (relation no longer in the row space)', l1c_disc)

    def l1c_children(w):
        p, nd = find(w['tree'], 'L1c')
        nd['children'] = [copy.deepcopy(nd)]
    m('tree_L3_L1c', 'L1c leaf given a child', l1c_children)

    def l1c_as_l3(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['kind'] = 'L3'
        nd['move']['d'] = [0]
    m('tree_L3_L1c', 'L1c relabelled L3 with d = 0 (d^2 != negative discriminant)', l1c_as_l3)

    # L1b
    def l1b_unit(w):
        p, nd = find(w['tree'], 'L1b')
        nd['move']['omega'] = [-1]
    m('tree_L1b', 'L1b omega replaced by -1 (modulus 1)', l1b_unit)

    def l1b_conj(w):
        p, nd = find(w['tree'], 'L1b')
        om = nd['move']['omega']
        assert isinstance(om, dict)
        om['im'] = [neg(x) for x in om['im']]
    m('tree_L1b', 'L1b omega conjugated (same modulus, relation not forced)', l1b_conj)

    def l1b_edge_nonedge(w):
        p, nd = find(w['tree'], 'L1b')
        n, Eg = V.decode_g6(PICK['tree_L1b'])
        # current graph is the node's edge list
        cur = {tuple(e) for e in nd['edges']}
        ne = next([u, v] for u in range(10) for v in range(u + 1, 10) if (u, v) not in cur)
        nd['move']['edges'][1] = ne
    m('tree_L1b', 'L1b second edge is a non-edge', l1b_edge_nonedge)

    def unknown_kind(w):
        w['tree']['move']['kind'] = 'L4'
    m('tree_big', 'unknown move kind', unknown_kind)

    def extra_node_field(w):
        w['tree']['note'] = 1
    m('tree_big', 'extra field in a node', extra_node_field)

    def deep_entry(w):
        # alter an entry deep in the biggest tree (last node visited)
        last = None
        for p, nd in walk(w['tree']):
            last = nd
        row = last['A'][0]
        j = next(k for k, x in enumerate(row) if x == [0] or x == ['0'])
        row[j] = [1]
    m('tree_big', 'alter one zero entry of the deepest node matrix A', deep_entry)
    return out


def main(argv):
    src, dst = argv[1], argv[2]
    ctx = V.load_context(V.DEFAULT_DATA)
    recs = load_records(src)
    originals = []
    for key, g in PICK.items():
        rec = recs[g]
        others = []
        if key == 'tu_refuted':
            others = [dumps(recs[PICK['tu_target_tree']])]
        if key == 'tu_pointing_to_tu':
            others = [dumps(recs[PICK['tu_two_step']])]
        r = run([dumps(rec)] + others, ctx, g)
        originals.append({'key': key, 'g6': g, 'type': rec['cert']['type'], 'verdict': r['verdict'],
                          'reason': r['reason']})
    muts = []
    muts += tu_mutations(recs)
    muts += null_mutations(recs)
    muts += dag_mutations(recs, 'null-dag', ['null_dag', 'null_dag2'])
    muts += real_mutations(recs, 'real', ['real_sos', 'real_sturm'])
    muts += dag_mutations(recs, 'real-dag', ['real_dag_sos', 'real_dag_sturm'])
    muts += real_mutations(recs, 'real-dag', ['real_dag_sos', 'real_dag_sturm'], common=False)
    muts += tree_mutations(recs)
    muts += attack_certificates(recs)
    import redteam_attacks as RA
    for typ, desc, fn in RA.ATTACKS:
        muts.append((typ, 'synthetic', desc, fn(), None))
    results = []
    for typ, g, desc, rec, extra in muts:
        orig = recs.get(g)
        line = dumps(rec)
        companions_changed = any(dumps(tr) != dumps(recs[tr['g6']]) for tr in (extra or {}).get('with_records', [])
                                 if tr['g6'] in recs)
        if orig is not None and line == dumps(orig) and not companions_changed:
            results.append({'type': typ, 'source_g6': g, 'mutation': desc, 'verdict': 'NO-OP',
                            'reason': 'mutation did not change the record', 'pass': False})
            continue
        others = []
        if extra:
            for tg in extra.get('with', []):
                others.append(dumps(recs[tg]))
            for tr in extra.get('with_records', []):
                others.append(dumps(tr))
        focus = rec['g6']
        r = run([line] + others, ctx, focus)
        results.append({'type': typ, 'source_g6': g, 'mutation': desc, 'verdict': r['verdict'],
                        'reason': r['reason'], 'pass': r['verdict'] == V.REJECT})
    # raw-line controls (JSON strictness and graph6 framing) and a few structural extras
    raw = []
    tu_line = dumps(recs[PICK['tu_forbidden']]).decode()
    raw.append(('tu', PICK['tu_forbidden'], 'duplicate JSON key "type" in the certificate',
                tu_line.replace('"type": "tu"', '"type": "tu", "type": "tu"', 1)))
    raw.append(('tu', PICK['tu_forbidden'], 'graph6 with nonzero padding bits',
                tu_line.replace('"I?ERPrCwW"', '"I?ERPrCwX"', 1)))
    raw.append(('tu', PICK['tu_forbidden'], 'graph6 one character short',
                tu_line.replace('"I?ERPrCwW"', '"I?ERPrCw"', 1)))
    raw.append(('tu', PICK['tu_forbidden'], 'truncated JSON line',
                tu_line[:len(tu_line) // 2] + '\n'))
    nl = dumps(recs[PICK['null2']]).decode()
    k0 = first_nonempty_cofactor(recs[PICK['null2']]['cert']['cofactors'])
    c0 = recs[PICK['null2']]['cert']['cofactors'][k0][0][0]
    i0 = nl.index('"%s": [["%s"' % (k0, c0))
    j0 = i0 + len('"%s": [[' % k0)
    raw.append(('null', PICK['null2'], 'coefficient written as a JSON float literal',
                nl[:j0] + '1.5' + nl[j0 + len(c0) + 2:]))
    tl = dumps(recs[PICK['tree_L2_L1a']]).decode()
    raw.append(('tree', PICK['tree_L2_L1a'], 'NaN in the field interval',
                tl.replace('"interval": [-1, 1]', '"interval": [NaN, 1]', 1)))
    for typ, g, desc, line in raw:
        assert line != (dumps(recs[g]).decode()), desc
        r = run([line.encode()], ctx, None)
        results.append({'type': typ, 'source_g6': g, 'mutation': desc, 'verdict': r['verdict'],
                        'reason': r['reason'], 'pass': r['verdict'] == V.REJECT})
    extra_struct = []
    r = copy.deepcopy(recs[PICK['tree_L3_L1a']])
    r['cert']['witness']['field'] = {'minpoly': [1, -3, 0, 1], 'interval': [-2, 2]}
    extra_struct.append(('tree', PICK['tree_L3_L1a'], 'irreducible minpoly x^3-3x+1 whose interval holds 3 real roots', r))
    r = copy.deepcopy(recs[PICK['tree_L2_L1a']])
    pth, nd = find(r['cert']['witness']['tree'], 'L1a')
    nd['children'] = [copy.deepcopy(nd)]
    extra_struct.append(('tree', PICK['tree_L2_L1a'], 'L1a leaf given a child', r))
    r = copy.deepcopy(recs[PICK['tree_L1b']])
    pth, nd = find(r['cert']['witness']['tree'], 'L1b')
    nd['children'] = [copy.deepcopy(nd)]
    extra_struct.append(('tree', PICK['tree_L1b'], 'L1b leaf given a child', r))
    r = copy.deepcopy(recs[PICK['tree_L2_L1a']])
    pth, nd = find(r['cert']['witness']['tree'], 'L2')
    nd['move']['omega'] = {'re': [-1], 'im': [0]}
    extra_struct.append(('tree', PICK['tree_L2_L1a'], 'control that should still ACCEPT: omega -1 respelled as {re:[-1], im:[0]}', r))
    for typ, g, desc, rec in extra_struct:
        r = run([dumps(rec)], ctx, None)
        want = V.ACCEPT if desc.startswith('control that should still ACCEPT') else V.REJECT
        results.append({'type': typ, 'source_g6': g, 'mutation': desc, 'verdict': r['verdict'],
                        'reason': r['reason'], 'pass': r['verdict'] == want,
                        'expected': want})

    # data control: a gadget whose TU property is broken must make the context refuse to load
    import tempfile
    with open(os.path.join(V.DEFAULT_DATA, 'tu-gadgets.json')) as fh:
        gad = json.load(fh)
    for gi, drop in ((0, [0, 3]), (3, [2, 3]), (5, [5, 6])):
        bad = copy.deepcopy(gad)
        bad[gi]['edges'] = [e for e in bad[gi]['edges'] if e != drop]
        bad[gi]['m'] = len(bad[gi]['edges'])
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, dir=os.path.dirname(os.path.abspath(__file__)))
        json.dump(bad, tmp)
        tmp.close()
        try:
            V.load_gadgets(tmp.name)
            verdict, why = 'LOADED', 'broken gadget accepted as TU'
        except RuntimeError as exc:
            verdict, why = V.REJECT, str(exc)
        finally:
            os.unlink(tmp.name)
        results.append({'type': 'tu-gadget-data', 'source_g6': 'tu-gadgets.json[%d]' % gi,
                        'mutation': 'gadget %d with edge %s deleted (TU proof must fail)' % (gi, drop),
                        'verdict': verdict, 'reason': why, 'pass': verdict == V.REJECT})
    summary = {}
    for x in results:
        x.setdefault('expected', V.REJECT)
        s = summary.setdefault(x['type'], {'negative_controls': 0, 'rejected': 0,
                                           'positive_controls': 0, 'accepted': 0})
        if x['expected'] == V.REJECT:
            s['negative_controls'] += 1
            s['rejected'] += int(x['verdict'] == V.REJECT)
        else:
            s['positive_controls'] += 1
            s['accepted'] += int(x['verdict'] == V.ACCEPT)
    out = {'originals': originals,
           'originals_all_accepted': all(o['verdict'] == V.ACCEPT for o in originals),
           'mutations': results,
           'summary_by_type': summary,
           'all_negative_controls_rejected': all(x['verdict'] == V.REJECT for x in results
                                                 if x['expected'] == V.REJECT),
           'all_positive_controls_accepted': all(x['verdict'] == V.ACCEPT for x in results
                                                 if x['expected'] == V.ACCEPT),
           'all_controls_as_expected': all(x['pass'] for x in results)}
    with open(dst, 'w') as fo:
        json.dump(out, fo, indent=1)
    for o in originals:
        print('ORIGINAL %-18s %-10s %s %s' % (o['key'], o['type'], o['verdict'], o['reason'][:80]))
    for x in results:
        print('%-4s %-9s %-11s %-60s | %s' % ('ok' if x['pass'] else 'FAIL', x['type'], x['verdict'],
                                             x['mutation'][:60], x['reason'][:110]))
    print(json.dumps(summary))
    print('originals_all_accepted', out['originals_all_accepted'], 'all_negative_controls_rejected',
          out['all_negative_controls_rejected'], 'all_positive_controls_accepted',
          out['all_positive_controls_accepted'])
    return 0 if out['originals_all_accepted'] and out['all_controls_as_expected'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
