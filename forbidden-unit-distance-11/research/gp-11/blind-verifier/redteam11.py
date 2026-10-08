#!/usr/bin/env python3
"""redteam11.py: red controls for verify_refutations11.py on GP-11 records.

Usage:
    python redteam11.py RECORDS.jsonl INDEX.jsonl OUT.json [--workdir DIR]

Every control is RIGHT-shaped: it mutates a copy of a real record's certificate (or builds a
synthetic certificate), asserts the mutant differs from its source, and requires the verdict
REJECT with a reason matching the rule the mutation was aimed at.  Each source record is
verified unmutated in the same run and must be ACCEPTED, both before the mutations and again
at the end (so no mutation can leak into the evidence through shared objects).  Positive
controls (constructions that are genuinely valid) must be ACCEPTED.

The end-to-end section writes a small records file of mutants and originals with distinct
graph6 strings and runs the real command line (scan, check with forked workers, resolve) on it.
"""
import os
os.environ.setdefault('SYMPY_GROUND_TYPES', 'python')
import sys
import json
import copy
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_refutations11 as V          # noqa: E402
import redteam_attacks11 as RA            # noqa: E402

ACCEPT, REJECT = V.ACCEPT, V.REJECT

# Source records (chosen from the GP-11 survey: small, and covering every branch).  None means
# "choose automatically from the index" (see pick_auto).
PICK = {
    'tu_gp': 'J??G|?wTV@?',            # one step (gadget 0), ends at F10[j] with j < 74
    'tu_gp10': 'J???g[{weQ_',          # one step (gadget 0), ends at F10[j] with j >= 74
    'tu_refuted': 'J_A_ZKW[Gt?',       # one step, ends at another refuted record (companion)
    'tu_two_step': 'J?Ce_WDMMB?',      # gadgets 0 then 5
    'tu_three_step': 'J@?KJOQRN`?',    # gadgets 3, 3, 4
    'sub_tu': 'J???xZOx@r?',           # R-ptr to a tu record (companion)
    'sub_tree': None,                  # R-ptr to a tree record
    'tu_dag': None,                    # TU chain ending at a null-dag record (companion)
    'null': 'JkGOOKI@^`_',
    'null2': 'Jk??OKiD^w?',
    'null_dag': 'J`??]Otp`s_',
    'null_dag2': 'Jg?OtDGHWx?',
    'real_sos': 'Ji?XcCKAXB_',
    'real_sturm': None,                # smallest real + sturm
    'real_dag_sos': 'JCUB?WDGhb_',
    'real_dag_sturm': 'JoC?I?xHy{?',
    'tree_L2_L1a': 'JGGaSeKDIa_',      # field of degree 1
    'tree_L3_L1a': 'J?H@oWsc]E?',      # degree 2
    'tree_L3_L1c': 'Jo?Yo_dQPB_',      # degree 2
    'tree_L1b': None,                  # smallest tree with an L1b move whose omega is non-real
    'tree_deg4': 'Jo?Q?TXJPk_',        # degree 4: L3 and L1c
    'tree_deg4_all': 'Jq??Wodiql?',    # degree 4: all five moves
    'tree_big': None,                  # the largest tree
    'tree_strfield': 'JQ`@HKYE]W?',    # the one tree with minpoly/interval as strings and zero as "0"
}


def compact(rec):
    return (json.dumps(rec, separators=(',', ':'), sort_keys=True) + '\n').encode()


def g6_encode(n, E):
    bits = [1 if (i, j) in E else 0 for j in range(1, n) for i in range(j)]
    while len(bits) % 6:
        bits.append(0)
    out = chr(63 + n)
    for k in range(0, len(bits), 6):
        v = 0
        for b in bits[k:k + 6]:
            v = (v << 1) | b
        out += chr(63 + v)
    return out


def walk(node, path=()):
    yield path, node
    for i, c in enumerate(node['children']):
        yield from walk(c, path + (i,))


def find(tree, kind):
    for p, n in walk(tree):
        if n['move']['kind'] == kind:
            return p, n
    raise RuntimeError('no %s node' % kind)


def bump(c):
    """A different, NONZERO rational string (a zero would trip the canonical-term rule of the
    DAG types instead of the identity the mutation is aimed at)."""
    q = V.parse_rat_str(c, 'bump') + 1
    if q == 0:
        q += 1
    return str(q.p) if q.q == 1 else '%d/%d' % (q.p, q.q)


def neg(x):
    q = -V.parse_rat_tree(x, 'neg')
    return str(q.p) if q.q == 1 else '%d/%d' % (q.p, q.q)


def first_nonempty_cofactor(cof):
    for k in sorted(cof):
        if cof[k]:
            return k
    raise RuntimeError('no nonempty cofactor')


# ------------------------------------------------------------------------------ loading

class Records:
    def __init__(self, path, index):
        self.path = path
        self.index = index
        self.by_g6 = {e['g6']: e for e in index}
        self.fh = open(path, 'rb')
        self.cache = {}

    def line(self, g6):
        e = self.by_g6[g6]
        self.fh.seek(e['offset'])
        b = self.fh.read(e['length'])
        assert b.endswith(b'\n') and len(b) == e['length']
        return b

    def rec(self, g6):
        if g6 not in self.cache:
            self.cache[g6] = json.loads(self.line(g6))
        return copy.deepcopy(self.cache[g6])


def pick_auto(R):
    idx = R.index
    by = R.by_g6
    if PICK['sub_tree'] is None:
        PICK['sub_tree'] = min((e for e in idx if e['type'] == 'sub' and by[e['ptr']]['type'] == 'tree'),
                               key=lambda e: (by[e['ptr']]['length'], e['g6']))['g6']
    if PICK['tu_dag'] is None:
        PICK['tu_dag'] = min((e for e in idx if e['type'] == 'tu' and e['ptr'] and by[e['ptr']]['type'] == 'null-dag'),
                             key=lambda e: (by[e['ptr']]['length'], e['g6']))['g6']
    if PICK['real_sturm'] is None:
        best = None
        for e in sorted((e for e in idx if e['type'] == 'real'), key=lambda e: e['length']):
            if 'sturm' in R.rec(e['g6'])['cert']:
                best = e['g6']
                break
        PICK['real_sturm'] = best
    if PICK['tree_L1b'] is None:
        for e in sorted((e for e in idx if e['type'] == 'tree'), key=lambda e: e['length']):
            r = R.rec(e['g6'])
            ok = False
            for _p, nd in walk(r['cert']['witness']['tree']):
                om = nd['move'].get('omega')
                if nd['move']['kind'] == 'L1b' and isinstance(om, dict) and any(
                        V.parse_rat_tree(x, 'im') != 0 for x in om['im']):
                    ok = True
                    break
            if ok:
                PICK['tree_L1b'] = e['g6']
                break
    if PICK['tree_big'] is None:
        PICK['tree_big'] = max((e for e in idx if e['type'] == 'tree'), key=lambda e: e['length'])['g6']


def companions_of(R, g6):
    """Records a source needs in the same run (its pointer target)."""
    e = R.by_g6[g6]
    return [R.rec(e['ptr'])] if e.get('ptr') else []


# ------------------------------------------------------------------------------ running

CTX = {}


def run(lines, ctx_kind='b11', focus=None):
    ctx = CTX[ctx_kind]
    res = [V.verify_line(l, ctx) for l in lines]
    V.resolve(res)
    if focus is not None:
        for r in res:
            if r['g6'] == focus:
                return r
    return res[0]


class C:
    """One control."""

    def __init__(self, typ, source, desc, rec, companions=(), expected=REJECT, regex=None,
                 ctx_kind='b11', raw=None):
        self.typ, self.source, self.desc = typ, source, desc
        self.rec, self.companions = rec, list(companions)
        self.expected, self.regex, self.ctx_kind, self.raw = expected, regex, ctx_kind, raw


# ------------------------------------------------------------------------------ tu

def tu_controls(R):
    out = []

    def mk(key, desc, f, regex, comps=None):
        base = R.rec(PICK[key])
        r = copy.deepcopy(base)
        f(r)
        out.append(C('tu', key, desc, r, companions_of(R, PICK[key]) if comps is None else comps,
                     REJECT, regex))

    g = PICK['tu_gp']
    base = R.rec(g)
    n, E = V.decode_g6(g)
    j = base['cert']['end']['forbidden']
    assert j < 74
    mk('tu_gp', 'duplicate the step: the second application names a pair that is already an edge',
       lambda r: r['cert']['steps'].append(copy.deepcopy(r['cert']['steps'][0])),
       r'^tu step 1: pair \d+-\d+ is already an edge')
    step_pair = tuple(base['cert']['steps'][0]['pair'])

    def add_pair_edge(r):
        E2 = set(E)
        E2.add(V.norm_edge(*step_pair))
        r['g6'] = g6_encode(n, E2)
    mk('tu_gp', 'graph already contains the step pair as an edge', add_pair_edge,
       r'^tu step 0: pair \d+-\d+ is already an edge')

    def swap_step_map(r):
        mp = r['cert']['steps'][0]['map']
        mp[0], mp[1] = mp[1], mp[0]
    mk('tu_gp', 'swap two entries of the step map', swap_step_map,
       r'^tu step 0: (map not edge-preserving|pair is not the image)')

    def swap_end_map(r):
        mp = r['cert']['end']['map']
        mp[0], mp[2] = mp[2], mp[0]
    mk('tu_gp', 'swap two entries of the end (F10) map', swap_end_map,
       r'^tu end forbidden\[%d\]: map not edge-preserving' % j)
    for jj in (j + 1, j - 1):
        mk('tu_gp', 'REQUIRED: forbidden index shifted in a TU certificate (%d -> %d)' % (j, jj),
           lambda r, jj=jj: r['cert']['end'].__setitem__('forbidden', jj),
           r'^tu end forbidden\[%d\]: map (must be a list of length \d+|not edge-preserving)' % jj)
    mk('tu_gp', 'forbidden index 398 (one past the end of F10)',
       lambda r: r['cert']['end'].__setitem__('forbidden', 398), r'^tu end: bad forbidden index 398')
    mk('tu_gp', 'forbidden index as a string', lambda r: r['cert']['end'].__setitem__('forbidden', str(j)),
       r"^tu end: bad forbidden index '%d'" % j)

    def gad_idx(r):
        r['cert']['steps'][0]['gadget'] = 1
    mk('tu_gp', 'step cites a different gadget (1 instead of 0)', gad_idx,
       r'^tu step 0: map must be a list of length 7')

    def pair_wrong(r):
        st = r['cert']['steps'][0]
        img = set(st['pair'])
        other = next(v for v in range(n) if v not in img and V.norm_edge(st['pair'][0], v) not in E)
        st['pair'] = [st['pair'][0], other]
    mk('tu_gp', 'step pair is not the image of the distinguished pair', pair_wrong,
       r'^tu step 0: pair is not the image of the gadget distinguished pair')

    def noninj(r):
        mp = r['cert']['end']['map']
        mp[1] = mp[0]
    mk('tu_gp', 'end map not injective', noninj, r'^tu end forbidden\[%d\]: map not injective' % j)
    mk('tu_gp', 'zero-step chain (direct containment is an R-ptr, not a tu chain)',
       lambda r: r['cert'].__setitem__('steps', []), r'^tu: steps must be a nonempty list')
    mk('tu_gp', 'unknown extra field in the certificate', lambda r: r['cert'].__setitem__('note', 'x'),
       r'^tu: schema')
    mk('tu_gp', 'record verdict "tu" instead of "refuted" (contract red fixture)',
       lambda r: r.__setitem__('verdict', 'tu'), r"^record verdict is 'tu', not refuted")
    mk('tu_gp', 'boolean in place of the integer gadget index',
       lambda r: r['cert']['steps'][0].__setitem__('gadget', False), r'^tu step 0: bad gadget index False')

    # an F10 end that rests on GP-10's 324 (index >= 74)
    g10 = PICK['tu_gp10']
    j10 = R.rec(g10)['cert']['end']['forbidden']
    assert j10 >= 74
    mk('tu_gp10', 'REQUIRED: forbidden index shifted in a TU certificate ending in GP-10\'s range (%d -> %d)'
       % (j10, j10 + 1), lambda r: r['cert']['end'].__setitem__('forbidden', j10 + 1),
       r'^tu end forbidden\[%d\]: map (must be a list of length \d+|not edge-preserving)' % (j10 + 1))
    mk('tu_gp10', 'end map entry moved to a vertex outside the graph',
       lambda r: r['cert']['end']['map'].__setitem__(0, 11), r'^tu end forbidden\[%d\] map: bad vertex 11' % j10)

    # chains of more than one step
    two_three = r'^tu (step \d+: (map not edge-preserving|pair \d+-\d+ is already an edge|pair is not the image)|end forbidden\[\d+\]: map not edge-preserving)'
    mk('tu_two_step', 'two-step chain with its first step deleted',
       lambda r: r['cert']['steps'].pop(0), two_three)
    mk('tu_two_step', 'two-step chain with its steps reversed',
       lambda r: r['cert']['steps'].reverse(), two_three)
    mk('tu_three_step', 'three-step chain with its middle step deleted',
       lambda r: r['cert']['steps'].pop(1), two_three)
    mk('tu_three_step', 'three-step chain with its last step deleted',
       lambda r: r['cert']['steps'].pop(2), two_three)

    # ends at a refuted record: resolution rules
    gr = PICK['tu_refuted']
    tgt = R.rec(gr)['cert']['end']['refuted']
    tn, tE = V.decode_g6(tgt)
    e0 = sorted(tE)[0]
    sub_tgt = g6_encode(tn, set(tE) - {e0})       # a subgraph of the target: the map still works

    def end_nonrecord(r):
        r['cert']['end']['refuted'] = sub_tgt
    mk('tu_refuted', 'end points at a graph (target minus an edge, so the map is valid) with no record',
       end_nonrecord, r'^pointer target .* has no refuted record in this run')
    tmut = R.rec(tgt)
    tmut_cert = tmut['cert']
    if tmut_cert['type'] == 'tu':
        tmut_cert['end']['map'][1] = tmut_cert['end']['map'][0]
    elif tmut_cert['type'] == 'tree':
        tmut_cert['witness']['tree']['move'] = {'kind': 'L1a', 'pair': [0, 1]}
        tmut_cert['witness']['tree']['children'] = []
    elif tmut_cert['type'] in ('null-dag', 'real-dag'):
        tmut_cert['rows'][-1]['poly'][0][0] = bump(tmut_cert['rows'][-1]['poly'][0][0])
    else:
        raise RuntimeError('unexpected target type %r' % tmut_cert['type'])
    out.append(C('tu', 'tu_refuted', 'end target record is present but its own certificate is broken',
                 R.rec(gr), [tmut], REJECT, r'^pointer target .* is not accepted \(REJECT'))

    def self_loop(r):
        r['cert']['end'] = {'refuted': r['g6'], 'map': list(range(11))}
    mk('tu_gp', 'pointer cycle: the chain ends at its own record (identity map, which is valid)',
       self_loop, r'^pointer cycle through', comps=[])

    # a genuine two-record loop: A tu-> B (B = A + pair, identity), B sub-> A (identity)
    A = R.rec(PICK['tu_gp'])
    B_E = set(E) | {V.norm_edge(*step_pair)}
    Bg6 = g6_encode(n, B_E)
    A['cert']['end'] = {'refuted': Bg6, 'map': list(range(n))}
    B = {'g6': Bg6, 'verdict': 'refuted', 'cert': {'type': 'sub', 'g6': A['g6'], 'map': list(range(n))}}
    out.append(C('tu', 'tu_gp', 'two-record pointer loop A tu-> B, B sub-> A (both maps valid)',
                 A, [B], REJECT, r'^pointer (cycle through|target .* is not accepted)'))
    return out


# ------------------------------------------------------------------------------ sub (GP-11)

def labelg(g6s):
    p = subprocess.run(['nauty-labelg', '-q'], input=''.join(x + '\n' for x in g6s).encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
    return p.stdout.decode().split('\n')[:len(g6s)]


def find_iso(n1, E1, n2, E2):
    """An explicit isomorphism v -> w from graph 1 onto graph 2 (backtracking), or None."""
    adj1 = [set() for _ in range(n1)]
    adj2 = [set() for _ in range(n2)]
    for u, v in E1:
        adj1[u].add(v)
        adj1[v].add(u)
    for u, v in E2:
        adj2[u].add(v)
        adj2[v].add(u)
    if n1 != n2 or len(E1) != len(E2):
        return None
    img, used = {}, set()

    def bt(v):
        if v == n1:
            return True
        for w in range(n2):
            if w in used or len(adj2[w]) != len(adj1[v]):
                continue
            if all((img[u] in adj2[w]) == (u in adj1[v]) for u in img):
                img[v] = w
                used.add(w)
                if bt(v + 1):
                    return True
                del img[v]
                used.discard(w)
        return False
    return dict(img) if bt(0) else None


def sub_controls(R):
    out = []

    def mk(key, desc, f, regex, comps=None, expected=REJECT):
        r = R.rec(PICK[key])
        f(r)
        out.append(C('sub', key, desc, r, companions_of(R, PICK[key]) if comps is None else comps,
                     expected, regex))

    g = PICK['sub_tu']
    base = R.rec(g)
    hg = base['cert']['g6']
    hn, hE = V.decode_g6(hg)
    mk('sub_tu', 'map not injective', lambda r: r['cert']['map'].__setitem__(1, r['cert']['map'][0]),
       r'^sub .*: map not injective')

    def swap(r):
        mp = r['cert']['map']
        # swap two vertices of different degree in H, so no automorphism can save the map
        deg = [sum(1 for e in hE if v in e) for v in range(hn)]
        a = 0
        b = next(v for v in range(hn) if deg[v] != deg[a])
        mp[a], mp[b] = mp[b], mp[a]
    mk('sub_tu', 'swap the images of two target vertices of different degree', swap,
       r'^sub .*: map not edge-preserving')
    mk('sub_tu', 'map one entry short', lambda r: r['cert']['map'].pop(), r'^sub .*: map must be a list of length 11')
    mk('sub_tu', 'map entry outside the graph', lambda r: r['cert']['map'].__setitem__(0, 11),
       r'^sub .* map: bad vertex 11')
    other = PICK['sub_tree']
    other_tgt = R.by_g6[other]['ptr']

    def other_target(r):
        r['cert']['g6'] = other_tgt
    mk('sub_tu', 'target replaced by another accepted refuted record (map no longer embeds it)',
       other_target, r'^sub .*: map not edge-preserving',
       comps=companions_of(R, g) + [R.rec(other_tgt)])
    e0 = sorted(hE)[0]
    nonrec = g6_encode(hn, set(hE) - {e0})

    def nonrecord(r):
        r['cert']['g6'] = nonrec
    mk('sub_tu', 'target is a graph with no record (the old target minus an edge; the map still embeds it)',
       nonrecord, r'^pointer target .* has no refuted record in this run')
    tmut = R.rec(hg)
    assert tmut['cert']['type'] == 'tu'
    tmut['cert']['steps'][0]['gadget'] = (tmut['cert']['steps'][0]['gadget'] + 1) % 6
    out.append(C('sub', 'sub_tu', 'target record present but its own certificate is broken',
                 R.rec(g), [tmut], REJECT, r'^pointer target .* is not accepted \(REJECT'))
    mk('sub_tu', 'pointer cycle: R-ptr to its own record with the identity map',
       lambda r: r['cert'].update({'g6': r['g6'], 'map': list(range(11))}), r'^pointer cycle through',
       comps=[])
    mk('sub_tu', 'unknown extra field', lambda r: r['cert'].__setitem__('note', 1), r'^sub: schema')
    mk('sub_tu', 'index added naming an F10 member the target is not',
       lambda r: r['cert'].__setitem__('index', 0), r'^sub: target .* is not isomorphic to F10\[0\]')
    mk('sub_tu', 'record verdict "embedded" with an R-ptr certificate',
       lambda r: r.__setitem__('verdict', 'embedded'), r"^record verdict is 'embedded', not refuted")
    mk('sub_tree', 'map not edge-preserving (two entries swapped) for an R-ptr to a tree',
       lambda r: r['cert']['map'].reverse(), r'^sub .*: map not edge-preserving')
    r = R.rec(PICK['tu_dag'])
    r['cert']['end']['map'].reverse()
    out.append(C('tu', 'tu_dag', 'end map reversed for a TU chain ending at a null-dag record', r,
                 companions_of(R, PICK['tu_dag']), REJECT, r'^tu end refuted .*: map not edge-preserving'))

    # an R-ptr WITH an F10 index (FORMAT: H is the canonical form of F10[index], the map uses
    # its canonical labels).  No B11 record can use one (B11 is F10-free), so the positive control
    # is built from a TU record: its augmented graph G* contains F10[j] via the end map.
    tb = R.rec(PICK['tu_gp10'])
    n, E = V.decode_g6(tb['g6'])
    st = tb['cert']['steps'][0]
    Gs = set(E) | {V.norm_edge(*st['pair'])}
    j = tb['cert']['end']['forbidden']
    endmap = tb['cert']['end']['map']
    fk, fE = CTX['b11']['forbidden'][j]
    Hc = labelg([g6_encode(fk, fE)])[0]
    hn2, hE2 = V.decode_g6(Hc)
    iso = find_iso(hn2, hE2, fk, fE)            # canonical label -> stored JSON label
    assert iso is not None
    cmap = [endmap[iso[v]] for v in range(hn2)]
    synth = {'g6': g6_encode(n, Gs), 'verdict': 'refuted',
             'cert': {'type': 'sub', 'g6': Hc, 'map': cmap, 'index': j}}
    out.append(C('sub', 'tu_gp10', 'POSITIVE: R-ptr with F10 index %d (canonical labels via nauty-labelg) '
                 'on the TU-augmented graph G*' % j, synth, [], ACCEPT, r'^R-ptr: contains F10\[%d\]' % j))
    s2 = copy.deepcopy(synth)
    s2['cert']['index'] = j + 1
    out.append(C('sub', 'tu_gp10', 'REQUIRED: forbidden index shifted in a containment (R-ptr) certificate '
                 '(%d -> %d)' % (j, j + 1), s2, [], REJECT, r'^sub: target .* is not isomorphic to F10\[%d\]' % (j + 1)))
    s3 = copy.deepcopy(synth)
    s3['cert']['index'] = 398
    out.append(C('sub', 'tu_gp10', 'containment index 398 (one past the end of F10)', s3, [], REJECT,
                 r'^sub: bad F10 index 398'))
    s4 = copy.deepcopy(synth)
    del s4['cert']['index']
    out.append(C('sub', 'tu_gp10', 'the same containment without its index: F10[j] has no record in the run',
                 s4, [], REJECT, r'^pointer target .* has no refuted record in this run'))
    s5 = copy.deepcopy(synth)
    s5['g6'] = tb['g6']                         # the un-augmented graph: F10-free, so the map must fail
    out.append(C('sub', 'tu_gp10', 'the containment moved onto the original (F10-free) graph G',
                 s5, [], REJECT, r'^sub .*: map not edge-preserving'))
    return out


# ------------------------------------------------------------------------------ polynomials

IDFAIL = {'null': r'^null: sum\(cofactor \* generator\) != 1',
          'real': r'^real: sum\(cofactor \* generator\) != f',
          'null-dag': r'^dag_row_identity: row \d+',
          'real-dag': r'^dag_row_identity: row \d+'}


def poly_common(kind, key, R, out):
    g = PICK[key]
    base = R.rec(g)
    c = base['cert']
    n, E = V.decode_g6(g)

    def m(desc, f, regex):
        r = copy.deepcopy(base)
        f(r['cert'])
        out.append(C(kind, key, desc, r, [], REJECT, regex))
    fa, fb = c['frame']
    nonedge = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E)
    m('frame is a non-edge (contract red fixture)', lambda cc: cc.__setitem__('frame', list(nonedge)),
      r'^frame: \d+-\d+ is not an edge')
    m('frame reversed (a valid frame, but a different system)', lambda cc: cc.__setitem__('frame', [fb, fa]),
      IDFAIL[kind])
    if len(c['sat']) >= 2:
        def sat_swap(cc):
            cc['sat'][0], cc['sat'][1] = cc['sat'][1], cc['sat'][0]
        m('swap two saturation entries (t-variable naming changes)', sat_swap, IDFAIL[kind])
    if c['sat']:
        m('duplicated saturation pair', lambda cc: cc['sat'].append(list(cc['sat'][0])), r'^sat: duplicate pair')
        m('saturation pair stored with u > v', lambda cc: cc['sat'].__setitem__(0, cc['sat'][0][::-1]),
          r'^sat: pair must have u < v')
    m('unknown extra field', lambda cc: cc.__setitem__('comment', 'x'), r'^%s: schema' % re.escape(kind))


def null_controls(R):
    out = []
    for key in ('null', 'null2'):
        g = PICK[key]
        base = R.rec(g)
        n, E = V.decode_g6(g)

        def m(desc, f, regex):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append(C('null', key, desc, r, [], REJECT, regex))

        def coef(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            cc['cofactors'][k][0][0] = bump(cc['cofactors'][k][0][0])
        m('REQUIRED: cofactor coefficient changed (one rational in one cofactor)', coef, IDFAIL['null'])

        def drop_term(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            del cc['cofactors'][k][-1]
        m('drop one cofactor term', drop_term, IDFAIL['null'])

        def drop_key(cc):
            k = first_nonempty_cofactor(cc['cofactors'])
            del cc['cofactors'][k]
        m('drop one whole cofactor', drop_key, IDFAIL['null'])
        if key == 'null':
            nonedge = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E)

            def extra_gen(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors']['e:%d,%d' % nonedge] = copy.deepcopy(cc['cofactors'][k])
            m('extra non-edge-equals-1 generator e:u,v for a non-edge (contract red fixture)', extra_gen,
              r"^cofactors: unknown generator key 'e:\d+,\d+'")

            def num_coef(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                t = cc['cofactors'][k][0]
                q = V.parse_rat_str(t[0], 'x')
                t[0] = int(q.p) if q.q == 1 else 1
            m('coefficient as a JSON number instead of a rational string', num_coef, r'bad rational')

            def dup_mono(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                t = copy.deepcopy(cc['cofactors'][k][0])
                t[0] = '0'
                cc['cofactors'][k].append(t)
            m('duplicate monomial (zero-coefficient copy of an existing term)', dup_mono, r'duplicate monomial')

            def bad_system(cc):
                sysm = V.System(n, E, cc['frame'], cc['sat'])
                st = {}
                for k2, gpoly in sysm.gens.items():
                    st[k2] = [[str(cf), [int(e) for e in exps]] for exps, cf in gpoly.to_dict().items()]
                k0 = sorted(st)[0]
                st[k0][0][0] = bump(st[k0][0][0])
                cc['system'] = st
            m('stated system present but one generator differs from the regenerated one', bad_system,
              r'^system: stated generator .* differs from the regenerated one')

            def exp_len(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors'][k][0][1] = cc['cofactors'][k][0][1] + [0]
            m('exponent vector one entry too long', exp_len, r'exponent vector must have \d+ entries')

            def exp_bool(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                e = cc['cofactors'][k][0][1]
                i = next(ii for ii, x in enumerate(e) if x in (0, 1))
                e[i] = bool(e[i])
            m('boolean in place of an integer exponent', exp_bool, r'bad exponent \(not an integer\)')

            def exp_neg(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors'][k][0][1][0] = -1
            m('negative exponent', exp_neg, r'bad exponent \(negative\)')
        poly_common('null', key, R, out)
    return out


def dag_controls(R, kind, keys):
    out = []
    for key in keys:
        g = PICK[key]
        base = R.rec(g)

        def m(desc, f, regex):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append(C(kind, key, desc, r, [], REJECT, regex))

        def row_cof(cc):
            row = next(rw for rw in cc['rows'] if any(rw['cofactors'].values()))
            k = first_nonempty_cofactor(row['cofactors'])
            row['cofactors'][k][0][0] = bump(row['cofactors'][k][0][0])
        m('REQUIRED: cofactor coefficient changed (one coefficient of a row cofactor)', row_cof,
          r'^dag_row_identity: row \d+')

        def row_poly(cc):
            row = next(rw for rw in cc['rows'] if rw['poly'])
            row['poly'][0][0] = bump(row['poly'][0][0])
        m('change one coefficient of a row polynomial', row_poly, r'^dag_row_identity: row \d+')

        def drop_cof_term(cc):
            row = next(rw for rw in cc['rows'] if any(len(v) > 1 for v in rw['cofactors'].values()))
            k = next(kk for kk in sorted(row['cofactors']) if len(row['cofactors'][kk]) > 1)
            del row['cofactors'][k][-1]
        m('drop one cofactor term in a row', drop_cof_term, r'^dag_row_identity: row \d+')

        def self_ref(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:')]
                if auxk:
                    rw['cofactors']['aux:%d' % k] = rw['cofactors'].pop(auxk[0])
                    return
            raise RuntimeError('no aux reference')
        m('self reference aux:k in row k', self_ref, r'^dag_reference_order: row (\d+) references aux:\1$')

        def fwd_ref(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:')]
                if auxk and k + 1 < len(cc['rows']):
                    rw['cofactors']['aux:%d' % (k + 1)] = rw['cofactors'].pop(auxk[0])
                    return
            # only the last row uses aux sources: give row 0 a reference to row 1 instead
            nv = len(cc['rows'][0]['poly'][0][1])
            cc['rows'][0]['cofactors']['aux:1'] = [['1', [0] * nv]]
        m('forward reference to a later row', fwd_ref, r'^dag_reference_order: row (\d+) references aux:\d+$')

        def lead_zero(cc):
            for k, rw in enumerate(cc['rows']):
                auxk = [kk for kk in rw['cofactors'] if kk.startswith('aux:') and kk != 'aux:0']
                if auxk:
                    rw['cofactors']['aux:0' + auxk[0][4:]] = rw['cofactors'].pop(auxk[0])
                    return
            raise RuntimeError('no aux reference')
        m('aux index spelled with a leading zero', lead_zero, r"^dag_source: row \d+ names unknown source 'aux:0\d+'")
        last_regex = (r'^null-dag: sum\(cofactor \* generator\) != 1' if kind == 'null-dag'
                      else r'^real-dag: sum\(cofactor \* generator\) != f')
        m('REQUIRED: derivation row dropped (the last row)', lambda cc: cc['rows'].pop(), last_regex)

        # dropping an earlier row renumbers every later row, so a later row either references
        # itself / a later row (reference order) or combines the wrong polynomial (identity)
        def drop_ref_row(cc):
            refd = sorted({int(kk[4:]) for rw in cc['rows'] for kk in rw['cofactors'] if kk.startswith('aux:')})
            del cc['rows'][refd[len(refd) // 2]]
        m('REQUIRED: derivation row dropped (an intermediate row that later rows use)', drop_ref_row,
          r'^(dag_row_identity: row \d+|dag_reference_order: row \d+ references aux:\d+)')

        def swap_terms(cc):
            row = next(rw for rw in cc['rows'] if len(rw['poly']) >= 2)
            row['poly'][0], row['poly'][1] = row['poly'][1], row['poly'][0]
        m('two terms of a row polynomial out of lexicographic order', swap_terms,
          r'terms not in strictly increasing lexicographic order')

        def zero_term(cc):
            row = cc['rows'][0]
            nv = len(row['poly'][0][1])
            row['poly'].append(['0', [50] * nv])
        m('zero-coefficient term appended to a row polynomial', zero_term,
          r'zero coefficient in canonical sparse polynomial')

        def too_many(cc):
            last = cc['rows'].pop()
            for _ in range(257):
                cc['rows'].append({'poly': [], 'cofactors': {}})
            cc['rows'].append(last)
        m('more than 256 rows (padding with zero rows)', too_many, r'^dag_row_limit')

        def bogus_src(cc):
            row = cc['rows'][0]
            k = first_nonempty_cofactor(row['cofactors'])
            row['cofactors']['q:1,2'] = row['cofactors'].pop(k)
        m('unknown source name', bogus_src, r"^dag_source: row 0 names unknown source 'q:1,2'")
        m('extra field in a row', lambda cc: cc['rows'][0].__setitem__('note', 1), r'^dag row 0: schema')
        m('empty rows list', lambda cc: cc.__setitem__('rows', []), r'^dag_rows')
        m('top-level cofactors added to a DAG', lambda cc: cc.__setitem__('cofactors', {}), r'^%s: schema' % kind)
        if kind == 'null-dag':
            m('last row claims 2 instead of the derived value',
              lambda cc: cc['rows'][-1]['poly'][0].__setitem__(0, '2'), r'^dag_row_identity: row \d+')

            def claim_one(cc):
                nv = len(cc['rows'][0]['poly'][0][1])
                cc['rows'] = [{'poly': [['1', [0] * nv]], 'cofactors': {}}]
            m('attack: a single row claiming 1 with no cofactors', claim_one, r'^dag_row_identity: row 0 poly != sum')
        poly_common(kind, key, R, out)
    return out


def real_controls(R, kind, keys, common=True):
    out = []
    for key in keys:
        g = PICK[key]
        base = R.rec(g)

        def m(desc, f, regex):
            r = copy.deepcopy(base)
            f(r['cert'])
            out.append(C(kind, key, desc, r, [], REJECT, regex))
        neqf = r'^%s: sum\(cofactor \* generator\) != f' % kind
        m('change one coefficient of f', lambda cc: cc['f'][0].__setitem__(0, bump(cc['f'][0][0])), neqf)
        if kind == 'real':
            def drop_term(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                del cc['cofactors'][k][-1]
            m('drop one cofactor term', drop_term, neqf)

            def coef(cc):
                k = first_nonempty_cofactor(cc['cofactors'])
                cc['cofactors'][k][0][0] = bump(cc['cofactors'][k][0][0])
            m('REQUIRED: cofactor coefficient changed', coef, neqf)
        else:
            def row_cof(cc):
                row = next(rw for rw in cc['rows'] if any(rw['cofactors'].values()))
                k = first_nonempty_cofactor(row['cofactors'])
                row['cofactors'][k][0][0] = bump(row['cofactors'][k][0][0])
            m('change one coefficient of a row cofactor', row_cof, r'^dag_row_identity: row \d+')
            m('last row polynomial differs from f',
              lambda cc: cc['rows'][-1]['poly'][0].__setitem__(0, bump(cc['rows'][-1]['poly'][0][0])),
              r'^dag_row_identity: row \d+')
        if 'sos' in base['cert']:
            m('SOS constant c = 0 (contract red fixture)', lambda cc: cc['sos'].__setitem__('c', '0'),
              r'^sos: c must be strictly positive')
            m('SOS constant c negative', lambda cc: cc['sos'].__setitem__('c', '-' + cc['sos']['c'].lstrip('+-')),
              r'^sos: c must be strictly positive')
            m('SOS constant c changed (c + 1)', lambda cc: cc['sos'].__setitem__('c', bump(cc['sos']['c'])),
              r'^sos: c \+ sum w q\^2 != f')
            m('REQUIRED: SOS weight changed (w_0 + 1)',
              lambda cc: cc['sos']['squares'][0].__setitem__(0, bump(cc['sos']['squares'][0][0])),
              r'^sos: c \+ sum w q\^2 != f')
            m('SOS weight negative',
              lambda cc: cc['sos']['squares'][0].__setitem__(0, '-' + cc['sos']['squares'][0][0].lstrip('+-')),
              r'^sos: weight 0 must be strictly positive')
            m('SOS weight zero', lambda cc: cc['sos']['squares'][0].__setitem__(0, '0'),
              r'^sos: weight 0 must be strictly positive')

            def sq_coef(cc):
                q = cc['sos']['squares'][0][1]
                q[0][0] = bump(q[0][0])
            m('one coefficient inside an SOS square changed', sq_coef, r'^sos: c \+ sum w q\^2 != f')
            m('drop one SOS square', lambda cc: cc['sos']['squares'].pop(), r'^sos: c \+ sum w q\^2 != f')

            def both(cc):
                n, E = V.decode_g6(g)
                cc['sturm'] = next('x_%d' % i for i in range(n) if i not in cc['frame'])
            m('both sturm and sos present', both, r'needs exactly one of sturm or sos')
        else:
            def other_var(cc):
                n, E = V.decode_g6(g)
                sysm = V.System(n, E, cc['frame'], cc['sat'])
                cc['sturm'] = next(v for v in sysm.names if v != cc['sturm'])
            m('Sturm names a different variable than the one f uses', other_var,
              r'^sturm: f involves a variable other than')
            m('Sturm names a frame coordinate that is not a variable',
              lambda cc: cc.__setitem__('sturm', 'x_%d' % cc['frame'][0]),
              r'^sturm: .x_\d+. is not a variable of the regenerated system')

            def to_sos(cc):
                del cc['sturm']
                cc['sos'] = {'c': '1', 'squares': []}
            m('Sturm proof replaced by an SOS claim f = 1', to_sos, r'^sos: c \+ sum w q\^2 != f')
            m('no proof of f at all (sturm removed)', lambda cc: cc.pop('sturm'),
              r'needs exactly one of sturm or sos')
        if common:
            poly_common(kind, key, R, out)
    return out


# ------------------------------------------------------------------------------ trees

ANOT = r'A contains a row that is not implied by the proved constraints|A row space is smaller than the regenerated'


def tree_controls(R):
    out = []

    def m(key, desc, f, regex):
        r = R.rec(PICK[key])
        f(r['cert']['witness'])
        out.append(C('tree', key, desc, r, [], REJECT, regex))
    n = 11

    def alter_root_A(w):
        A = w['tree']['A']
        A[0][0] = [2] if A[0][0] != [2] else [3]
    m('tree_L2_L1a', 'REQUIRED: matrix entry changed (one entry of the root matrix A)', alter_root_A, ANOT)

    def alter_deep_A(w):
        p, nd = find(w['tree'], 'L1a')
        nd['A'][-1][-1] = ['7/3']
    m('tree_L2_L1a', 'REQUIRED: matrix entry changed (one entry of a leaf matrix A)', alter_deep_A, ANOT)

    def drop_A_row(w):
        F = V.Field([V.fmpq(c) for c in w['field']['minpoly']], V.parse_rat_tree(w['field']['interval'][0], 'x'),
                    V.parse_rat_tree(w['field']['interval'][1], 'x'))
        A = w['tree']['A']
        full = V.RowSpace(F, n, [[V.parse_complex_elem(F, x, 'x') for x in row] for row in A]).rank()
        for i in range(len(A) - 1, -1, -1):        # a row whose deletion lowers the rank
            rest = A[:i] + A[i + 1:]
            if V.RowSpace(F, n, [[V.parse_complex_elem(F, x, 'x') for x in row] for row in rest]).rank() < full:
                del A[i]
                return
        raise RuntimeError('every row redundant')
    m('tree_L2_L1a', 'delete an independent row of the root matrix A (strict row-space equality)', drop_A_row,
      r'A row space is smaller than the regenerated constraint space')

    def add_A_row(w):
        row = [[0] for _ in range(n)]
        row[0] = [1]
        row[1] = [-1]
        w['tree']['A'].append(row)
        w['tree']['move'] = {'kind': 'L1a', 'pair': [0, 1]}
        w['tree']['children'] = []
    m('tree_L2_L1a', 'attack: root A gains the unproved row e0-e1 and the root becomes an L1a leaf', add_A_row,
      r'A contains a row that is not implied by the proved constraints')

    def del_child_L2(w):
        p, nd = find(w['tree'], 'L2')
        nd['children'] = []
    m('tree_L2_L1a', 'delete the child of an L2 node', del_child_L2, r'L2 must have exactly one child')

    def omega_flip(w):
        p, nd = find(w['tree'], 'L2')
        om = nd['move']['omega']
        nd['move']['omega'] = [1] if om == [-1] else [-1]
    m('tree_L2_L1a', 'flip the sign of an L2 omega', omega_flip, r'L2 relation is not in the row space of A')

    def omega_nonunit(w):
        p, nd = find(w['tree'], 'L2')
        nd['move']['omega'] = [2]
    m('tree_L2_L1a', 'L2 omega of modulus 2', omega_nonunit, r'L2 relation is not in the row space of A')

    def l2_existing(w):
        p, nd = find(w['tree'], 'L2')
        nd['move']['edges'][1] = list(nd['move']['edges'][0])
    m('tree_L2_L1a', 'L2 second pair is already an edge', l2_existing,
      r'L2 (second pair \d+-\d+ is already an edge|relation is not in the row space of A)')

    def l1a_pair(w):
        p, nd = find(w['tree'], 'L1a')
        u, v = nd['move']['pair']
        nd['move']['pair'] = [u, next(x for x in range(n - 1, -1, -1) if x not in (u, v))]
    m('tree_L2_L1a', 'L1a names a pair that is not forced to collide', l1a_pair,
      r'L1a collision \d+=\d+ is not forced by A')

    def root_edges(w):
        E = w['tree']['edges']
        cur = {tuple(e) for e in E}
        E.append(next([u, v] for u in range(n) for v in range(u + 1, n) if (u, v) not in cur))
        E.sort()
    m('tree_L2_L1a', 'root graph state gains a non-edge', root_edges, r'stated graph differs from the graph derived')

    def child_edges(w):
        p, nd = find(w['tree'], 'L1a')
        nd['edges'].pop()
    m('tree_L2_L1a', 'leaf graph state loses an edge', child_edges, r'stated graph differs from the graph derived')

    def interval_bad(w):
        mp = w['field']['minpoly']
        B = 2 + sum(abs(c) for c in mp)        # beyond every real root
        w['field']['interval'] = [B, B + 1]
    m('tree_L2_L1a', 'field interval without a root', interval_bad,
      r'field: minpoly has no strict sign change on the interval')

    def whole_leaf(w):
        t = w['tree']
        t['move'] = {'kind': 'L1a', 'pair': [0, 1]}
        t['children'] = []
    m('tree_L2_L1a', 'attack: root replaced by an unforced L1a leaf', whole_leaf, r'L1a collision 0=1 is not forced by A')

    def d_bad(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['d'] = [0, 2]
    m('tree_L3_L1a', 'L3 d changed (d^2 != discriminant)', d_bad, r'L3 d\^2 != ')

    def l3_one_child(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'].pop()
    m('tree_L3_L1a', 'delete one child of an L3 node', l3_one_child, r'L3 must have exactly two children')

    def l3_swap(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'].reverse()
    m('tree_L3_L1a', 'swap the two L3 children (+d / -d branches)', l3_swap, ANOT)

    def l3_dup(w):
        p, nd = find(w['tree'], 'L3')
        nd['children'][1] = copy.deepcopy(nd['children'][0])
    m('tree_L3_L1a', 'L3 second child replaced by a copy of the first (one branch covered twice)', l3_dup, ANOT)

    def l3_coef(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['coefficients'][2] = [2] if nd['move']['coefficients'][2] != [2] else [3]
    m('tree_L3_L1a', 'L3 coefficient changed', l3_coef, r'L3 relation is not in the row space of A')

    def l3_zero(w):
        p, nd = find(w['tree'], 'L3')
        nd['move']['coefficients'][1] = [0]
    m('tree_L3_L1a', 'L3 coefficient zero', l3_zero, r'L3 coefficients must all be nonzero')

    def minpoly_red(w):
        w['field']['minpoly'] = w['field']['minpoly'] + [0]
    m('tree_L3_L1a', 'minpoly with a zero leading coefficient', minpoly_red,
      r'field: minpoly must have positive degree and nonzero leading coeff')

    def minpoly_reducible(w):
        w['field']['minpoly'] = [0] + w['field']['minpoly']      # multiplied by x
    m('tree_L3_L1a', 'reducible minpoly (the minpoly times x)', minpoly_reducible,
      r'field: minpoly is not irreducible over Q')
    m('tree_L3_L1a', 'decimal string entry in A', lambda w: w['tree']['A'][0].__setitem__(0, ['1.0']),
      r'bad rational')

    def l1c_coef(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['coefficients'] = [[1], [1], [1]]
    m('tree_L3_L1c', 'L1c coefficients replaced by (1,1,1)', l1c_coef, r'L1c relation is not in the row space of A')

    def l1c_swap(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['edges'][0], nd['move']['edges'][1] = nd['move']['edges'][1], nd['move']['edges'][0]
    m('tree_L3_L1c', 'L1c edges swapped (relation no longer in the row space)', l1c_swap,
      r'L1c relation is not in the row space of A')

    def l1c_children(w):
        p, nd = find(w['tree'], 'L1c')
        nd['children'] = [copy.deepcopy(nd)]
    m('tree_L3_L1c', 'L1c leaf given a child', l1c_children, r'L1c leaf must have no children')

    def l1c_as_l3(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['kind'] = 'L3'
        nd['move']['d'] = [0]
    m('tree_L3_L1c', 'L1c relabelled L3 with d = 0 (d^2 != negative discriminant)', l1c_as_l3, r'L3 d\^2 != ')

    def l1b_unit(w):
        p, nd = find(w['tree'], 'L1b')
        nd['move']['omega'] = [-1]
    m('tree_L1b', 'L1b omega replaced by -1 (modulus 1)', l1b_unit,
      r'L1b (relation is not in the row space of A|needs \|omega\| != 1)')

    def l1b_conj(w):
        p, nd = find(w['tree'], 'L1b')
        om = nd['move']['omega']
        assert isinstance(om, dict)
        om['im'] = [neg(x) for x in om['im']]
    m('tree_L1b', 'L1b omega conjugated (same modulus, relation not forced)', l1b_conj,
      r'L1b relation is not in the row space of A')

    def l1b_edge_nonedge(w):
        p, nd = find(w['tree'], 'L1b')
        cur = {tuple(e) for e in nd['edges']}
        nd['move']['edges'][1] = next([u, v] for u in range(n) for v in range(u + 1, n) if (u, v) not in cur)
    m('tree_L1b', 'L1b second edge is a non-edge', l1b_edge_nonedge, r'second edge: \d+-\d+ is not an edge')

    def l1b_children(w):
        p, nd = find(w['tree'], 'L1b')
        nd['children'] = [copy.deepcopy(nd)]
    m('tree_L1b', 'L1b leaf given a child', l1b_children, r'L1b leaf must have no children')
    m('tree_big', 'unknown move kind', lambda w: w['tree']['move'].__setitem__('kind', 'L4'), r"unknown move kind 'L4'")
    m('tree_big', 'extra field in a node', lambda w: w['tree'].__setitem__('note', 1), r'tree node root: schema')

    def deep_entry(w):
        last = None
        for p, nd in walk(w['tree']):
            last = nd
        row = last['A'][0]
        j = next(k for k, x in enumerate(row) if x in ([0], ['0']))
        row[j] = [1]
    m('tree_big', 'REQUIRED: matrix entry changed (a zero entry of the deepest node matrix A)', deep_entry, ANOT)

    # GP-11: degree-4 fields (new at GP-11)
    def deg4_minpoly(w):
        w['field']['minpoly'][0] += 1
    m('tree_deg4', 'degree-4 minpoly constant term changed', deg4_minpoly,
      r'field: (minpoly has no strict sign change on the interval|interval does not isolate|minpoly is not irreducible)|' + ANOT)

    def deg4_wide(w):
        w['field']['interval'] = [-1000, 1000]
    m('tree_deg4', 'degree-4 interval widened to [-1000, 1000] (root no longer isolated)', deg4_wide,
      r'field: (minpoly has no strict sign change on the interval|interval does not isolate exactly one real root)')

    def deg4_l3coef(w):
        p, nd = find(w['tree'], 'L3')
        c = nd['move']['coefficients'][0]
        if isinstance(c, dict):
            c['re'] = list(c['re']) + [0] * (4 - len(c['re']))
            c['re'][3] = bump(str(c['re'][3]))
        else:
            c2 = list(c) + [0] * (4 - len(c))
            c2[3] = bump(str(c2[3]))
            nd['move']['coefficients'][0] = c2
    m('tree_deg4', 'degree-4 L3 coefficient changed in its theta^3 component', deg4_l3coef,
      r'L3 relation is not in the row space of A')

    def deg4_l1c(w):
        p, nd = find(w['tree'], 'L1c')
        nd['move']['coefficients'][1], nd['move']['coefficients'][2] = (nd['move']['coefficients'][2],
                                                                        nd['move']['coefficients'][1])
    m('tree_deg4', 'degree-4 L1c coefficients b and c exchanged', deg4_l1c, r'L1c relation is not in the row space of A')

    def deg4_A(w):
        p, nd = find(w['tree'], 'L3')
        ch = nd['children'][0]
        ch['A'][-1][-1] = [1, 1, 1, 1] if ch['A'][-1][-1] != [1, 1, 1, 1] else [2]
    m('tree_deg4_all', 'REQUIRED: matrix entry changed (degree-4 field, an L3 child)', deg4_A, ANOT)

    def deg4_elem_long(w):
        p, nd = find(w['tree'], 'L3')
        c = nd['move']['coefficients'][0]
        nd['move']['coefficients'][0] = (list(c) if isinstance(c, list) else c['re']) + [0, 0, 0, 0]
    m('tree_deg4_all', 'field element with more coefficients than the field degree', deg4_elem_long,
      r'real element must be a list of 1\.\.4 coefficients')
    return out


# ------------------------------------------------------------------------------ tree number grammar

def tree_grammar_controls(R):
    """The tree witness's integer-or-rational grammar (added after the full run's one REJECT):
    integer-valued strings where an integer is required (minpoly), bare values as elements of Q
    (zero as "0"); anything that is not an integer, or not a rational at all, still rejected."""
    out = []

    def m(key, desc, f, regex, expected=REJECT):
        r = R.rec(PICK[key])
        f(r['cert']['witness'])
        out.append(C('tree', key, desc, r, [], expected, regex))
    ok59 = r'^proof tree over field of degree 2: 59 nodes, leaves L1a:4,L1b:8,L1c:4$'
    assert R.rec(PICK['tree_strfield'])['cert']['witness']['field'] == {'minpoly': ['-3', '0', '1'],
                                                                        'interval': ['1', '3']}
    for bad, rx in (('3/2', r"^tree field minpoly: '3/2' is not an integer$"),
                    ('x', r"^tree field minpoly: bad rational 'x'$"),
                    ('1.0', r"^tree field minpoly: bad rational '1\.0'$"),
                    (True, r'^tree field minpoly: bad rational True$')):
        m('tree_strfield', 'minpoly coefficient "-3" replaced by %r (an integer is required)' % (bad,),
          lambda w, bad=bad: w['field']['minpoly'].__setitem__(0, bad), rx)
    m('tree_strfield', 'minpoly coefficient "-3" replaced by "-2" (a legal integer string, another field)',
      lambda w: w['field']['minpoly'].__setitem__(0, '-2'),
      ANOT + r'|L3 d\^2 != |relation is not in the row space of A')
    m('tree_strfield', 'interval endpoint "1" replaced by "1.0"',
      lambda w: w['field']['interval'].__setitem__(0, '1.0'), r"^interval: bad rational '1\.0'$")
    m('tree_strfield', 'POSITIVE: minpoly spelled "-6/2", "0/5", "1" (unreduced spellings, amendment 3)',
      lambda w: w['field'].__setitem__('minpoly', ['-6/2', '0/5', '1']), ok59, ACCEPT)
    m('tree_strfield', 'POSITIVE: minpoly and interval re-encoded as JSON integers',
      lambda w: w['field'].update({'minpoly': [-3, 0, 1], 'interval': [1, 3]}), ok59, ACCEPT)
    for bad, rx in (('x', r"^tree node root A\[0\]: bad rational 'x'$"),
                    ('1.0', r"^tree node root A\[0\]: bad rational '1\.0'$"),
                    (True, r'^tree node root A\[0\]: bad field element$'),
                    ('1', ANOT)):
        m('tree_strfield', 'bare "0" in the root matrix replaced by %r' % (bad,),
          lambda w, bad=bad: w['tree']['A'][0].__setitem__(0, bad), rx)

    def zeros_as_lists(w):
        n = 0
        for _p, nd in walk(w['tree']):
            for row in nd['A']:
                for k, x in enumerate(row):
                    if x == '0':
                        row[k] = ['0']
                        n += 1
                    elif isinstance(x, dict) and x['re'] == '0':
                        x['re'] = ['0']
                        n += 1
            om = nd['move'].get('omega')
            if isinstance(om, dict) and om['re'] == '0':
                om['re'] = ['0']
                n += 1
        assert n == 3182, n
    m('tree_strfield', 'POSITIVE: all 3,182 bare "0" elements re-encoded as ["0"]', zeros_as_lists, ok59, ACCEPT)
    # the same two encodings applied to a tree that uses JSON integers and coefficient lists
    src = R.rec(PICK['tree_L3_L1a'])['cert']['witness']
    ok_src = r'^proof tree over field of degree %d: ' % (len(src['field']['minpoly']) - 1)

    def as_strings(w):
        w['field']['minpoly'] = [str(c) for c in w['field']['minpoly']]
        w['field']['interval'] = [str(c) for c in w['field']['interval']]
    m('tree_L3_L1a', 'POSITIVE: string-encoded field (minpoly and interval as strings) on a JSON-integer tree',
      as_strings, ok_src, ACCEPT)

    def bare_zeros(w):
        n = 0
        for _p, nd in walk(w['tree']):
            for row in nd['A']:
                for k, x in enumerate(row):
                    if x in ([0], ['0']):
                        row[k] = '0' if n % 2 else 0
                        n += 1
        assert n > 0
    m('tree_L3_L1a', 'POSITIVE: zero matrix entries written as bare "0" / 0 on a list-encoded tree',
      bare_zeros, ok_src, ACCEPT)
    m('tree_L3_L1a', 'string-encoded field with a non-integer minpoly coefficient "-3/2"',
      lambda w: (as_strings(w), w['field']['minpoly'].__setitem__(0, '-3/2')),
      r"^tree field minpoly: '-3/2' is not an integer$")
    return out


# ------------------------------------------------------------------------------ transplants

def transplant_controls(R):
    """REQUIRED: a valid certificate transplanted onto a different graph.  (a) onto another
    refuted record's graph of the same certificate type; (b) onto the graph minus one edge the
    certificate uses (the hardest case: a subgraph)."""
    out = []
    pairs = [('tu', 'tu_gp', 'tu_two_step', r'^tu (step \d+|end forbidden\[\d+\]): '),
             ('sub', 'sub_tu', 'sub_tree', r'^sub .*: map not edge-preserving'),
             ('tree', 'tree_L3_L1c', 'tree_L3_L1a', r'stated graph differs from the graph derived'),
             ('null', 'null', 'null2', r'^frame: \d+-\d+ is not an edge|^cofactors: unknown generator key|' + IDFAIL['null']),
             ('null-dag', 'null_dag', 'null_dag2', r'^frame: \d+-\d+ is not an edge|^dag_source|^dag_row_identity'),
             ('real', 'real_sos', 'real_sturm', r'^frame: \d+-\d+ is not an edge|^cofactors: unknown generator key|' + IDFAIL['real']),
             ('real-dag', 'real_dag_sos', 'real_dag_sturm', r'^frame: \d+-\d+ is not an edge|^dag_source|^dag_row_identity')]
    for typ, src, dst, regex in pairs:
        a = R.rec(PICK[src])
        b = R.rec(PICK[dst])
        t = {'g6': b['g6'], 'verdict': 'refuted', 'cert': a['cert']}
        comps = companions_of(R, PICK[src])
        out.append(C(typ, src, 'REQUIRED: certificate of %s transplanted onto %s (another refuted record)'
                     % (PICK[src], PICK[dst]), t, comps, REJECT, regex))
    # (b) onto G - e for an edge e the certificate needs
    for typ, src in (('tu', 'tu_gp'), ('sub', 'sub_tu'), ('tree', 'tree_deg4_all'), ('null', 'null'),
                     ('null-dag', 'null_dag'), ('real', 'real_sos'), ('real-dag', 'real_dag_sturm')):
        a = R.rec(PICK[src])
        n, E = V.decode_g6(a['g6'])
        c = a['cert']
        if typ == 'tu':
            gn, gE, _p = CTX['b11']['gadgets'][c['steps'][0]['gadget']]
            img = c['steps'][0]['map']
            u, v = sorted(gE)[0]
            e = V.norm_edge(img[u], img[v])
            regex = r'^tu step 0: map not edge-preserving'
        elif typ == 'sub':
            hn, hE = V.decode_g6(c['g6'])
            u, v = sorted(hE)[0]
            e = V.norm_edge(c['map'][u], c['map'][v])
            regex = r'^sub .*: map not edge-preserving'
        elif typ == 'tree':
            e = sorted(E)[0]
            regex = r'stated graph differs from the graph derived'
        elif typ in ('null', 'real'):
            fr = V.norm_edge(*c['frame'])
            k = next(k for k in sorted(c['cofactors']) if k.startswith('e:') and c['cofactors'][k]
                     and tuple(int(x) for x in k[2:].split(',')) != fr)
            e = tuple(int(x) for x in k[2:].split(','))
            regex = r"^cofactors: unknown generator key 'e:%d,%d'" % e
        else:
            fr = V.norm_edge(*c['frame'])
            keys = [k for rw in c['rows'] for k in rw['cofactors'] if k.startswith('e:')
                    and tuple(int(x) for x in k[2:].split(',')) != fr]
            e = tuple(int(x) for x in keys[0][2:].split(','))
            regex = r"^dag_source: row \d+ names unknown source 'e:%d,%d'" % e
        t = {'g6': g6_encode(n, set(E) - {e}), 'verdict': 'refuted', 'cert': c}
        out.append(C(typ, src, 'REQUIRED: certificate transplanted onto its own graph minus edge %d-%d, '
                     'which the certificate uses' % e, t, companions_of(R, PICK[src]), REJECT, regex))
    # (c) POSITIVE: onto the graph PLUS one edge.  G + e contains G, so a refutation of G that
    # names only G's generators (or a TU chain whose pairs stay non-edges) is a genuine
    # refutation of G + e and must be ACCEPTED: a verifier that rejects every moved certificate
    # would fail here.  (A tree states its exact graph at every node, so it cannot move.)
    for typ, src, rx in (('null', 'null', r'^Nullstellensatz identity = 1'),
                         ('real-dag', 'real_dag_sos', r'^identity = f'),
                         ('tu', 'tu_gp', r'^tu chain of 1 step'),
                         ('sub', 'sub_tu', r'^R-ptr: contains refuted record')):
        a = R.rec(PICK[src])
        n, E = V.decode_g6(a['g6'])
        c = a['cert']
        avoid = set()
        if typ == 'tu':
            avoid = {V.norm_edge(*st['pair']) for st in c['steps']}
        e = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E and (u, v) not in avoid)
        t = {'g6': g6_encode(n, set(E) | {e}), 'verdict': 'refuted', 'cert': c}
        out.append(C(typ, src, 'POSITIVE: certificate moved onto its own graph PLUS edge %d-%d (a supergraph)' % e,
                     t, companions_of(R, PICK[src]), ACCEPT, rx))
    tr = R.rec(PICK['tree_L3_L1c'])
    n, E = V.decode_g6(tr['g6'])
    e = next((u, v) for u in range(n) for v in range(u + 1, n) if (u, v) not in E)
    t = {'g6': g6_encode(n, set(E) | {e}), 'verdict': 'refuted', 'cert': tr['cert']}
    out.append(C('tree', 'tree_L3_L1c', 'a tree moved onto its graph plus an edge (trees state their exact graph)',
                 t, [], REJECT, r'stated graph differs from the graph derived'))
    return out


# ------------------------------------------------------------------------------ synthetic attacks

def attack_controls(R):
    out = []
    g = PICK['null']
    base = R.rec(g)
    n, E = V.decode_g6(g)
    a, b = base['cert']['frame']
    nv0 = 2 * (n - 2)
    u = next(i for i in range(n) if i not in (a, b))
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'null', 'frame': [a, b], 'sat': [[u, u]],
         'cofactors': {'s:%d,%d' % (u, u): [['-1', [0] * (nv0 + 1)]]}}}
    out.append(C('null', 'null', 'attack: saturation pair [u,u] (its generator is the constant -1)', r, [], REJECT,
                 r'^sat: pair must have u < v'))
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'null', 'frame': [a, a], 'sat': [], 'cofactors': {}}}
    out.append(C('null', 'null', 'attack: degenerate frame [a, a]', r, [], REJECT, r'^frame: vertices must be distinct'))
    lo, hi = min(a, b), max(a, b)
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'real', 'frame': [a, b], 'sat': [[lo, hi]],
         'cofactors': {'s:%d,%d' % (lo, hi): [['1', [0] * (nv0 + 1)]]},
         'f': [['-1', [0] * (nv0 + 1)], ['1', [0] * nv0 + [1]]], 'sturm': 't_0'}}
    out.append(C('real', 'null', 'attack: valid identity, but f = t_0 - 1 has a real root (Sturm must count 1)',
                 r, [], REJECT, r'^sturm: f has 1 real root\(s\) in t_0'))
    r2 = copy.deepcopy(r)
    del r2['cert']['sturm']
    r2['cert']['sos'] = {'c': '1', 'squares': []}
    out.append(C('real', 'null', 'attack: f = t_0 - 1 with a bogus SOS c = 1 and no squares', r2, [], REJECT,
                 r'^sos: c \+ sum w q\^2 != f'))
    r = {'g6': g, 'verdict': 'refuted', 'cert': {'type': 'real-dag', 'frame': [a, b], 'sat': [],
         'rows': [{'poly': [], 'cofactors': {}}], 'f': [], 'sturm': 'x_%d' % u}}
    out.append(C('real-dag', 'null', 'attack: f = 0 (the zero polynomial) with Sturm', r, [], REJECT,
                 r'^sturm: f is the zero polynomial'))
    expect = [r'^frame: 2-3 is not an edge', r"^cofactors: unknown generator key 'e:2,3'",
              r"^dag_source: row 0 names unknown source 'e:2,3'", r'L1b needs \|omega\| != 1',
              r'L1c discriminant is not strictly negative', r'L1a collision 0=2 is not forced by A',
              r'L2 needs \|omega\| = 1', r'second edge: 2-3 is not an edge']
    assert len(expect) == len(RA.ATTACKS)
    for (typ, desc, fn), rx in zip(RA.ATTACKS, expect):
        out.append(C(typ, 'synthetic', desc, fn(), [], REJECT, rx, ctx_kind='noorder'))
    # the same attack graphs under the B11 profile are stopped by the order check first
    out.append(C('null', 'synthetic', 'order check: a 4-vertex record in the B11 run', RA.ATTACKS[0][2](), [],
                 REJECT, r'^order: graph has 4 vertices, a B11 record has 11'))
    # a 10-vertex record (GP-10 size) carrying a correct-looking TU certificate
    tb = R.rec(PICK['tu_gp'])
    tb['g6'] = 'IISpZATaw'
    out.append(C('tu', 'tu_gp', 'order check: a 10-vertex graph6 in the B11 run', tb, [], REJECT,
                 r'^order: graph has 10 vertices, a B11 record has 11'))
    # positive control for the synthetic harness: K4 (F10[0], forbidden) refuted by a genuine L1a
    # tree (the rhombus rows of K4's 4-cycles force a collision), order check off
    F = V.rational_field()
    K4 = {(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)}
    rows = V.rhombus_rows(F, 4, K4)
    pair = next((u2, v2) for u2 in range(4) for v2 in range(u2 + 1, 4)
                if V.RowSpace(F, 4, rows).contains(V.disp(F, 4, u2, v2, F.c(F.one))))
    t = RA.node(F, 4, K4, rows, {'kind': 'L1a', 'pair': list(pair)}, [])
    k4 = {'g6': g6_encode(4, K4), 'verdict': 'refuted',
          'cert': {'type': 'tree', 'witness': {'field': {'interval': [-1, 1], 'minpoly': [0, 1]}, 'tree': t}}}
    out.append(C('tree', 'synthetic', 'POSITIVE: K4 refuted by a genuine one-node L1a tree (order check off)',
                 k4, [], ACCEPT, r'^proof tree over field of degree 1: 1 nodes, leaves L1a:1', ctx_kind='noorder'))
    return out


# ------------------------------------------------------------------------------ raw lines

def raw_controls(R):
    out = []
    tl = compact(R.rec(PICK['tu_gp'])).decode()
    g = PICK['tu_gp']
    assert g.endswith('?')
    out.append(C('tu', 'tu_gp', 'duplicate JSON key "type" in the certificate', None, [], REJECT,
                 r"^json: duplicate key 'type'", raw=tl.replace('"type":"tu"', '"type":"tu","type":"tu"', 1)))
    out.append(C('tu', 'tu_gp', 'graph6 with nonzero padding bits', None, [], REJECT, r'^g6: nonzero padding bits',
                 raw=tl.replace('"g6":"%s"' % g, '"g6":"%s"' % (g[:-1] + '@'), 1)))
    out.append(C('tu', 'tu_gp', 'graph6 one character short', None, [], REJECT, r'^g6: wrong length for n=11',
                 raw=tl.replace('"g6":"%s"' % g, '"g6":"%s"' % g[:-1], 1)))
    out.append(C('tu', 'tu_gp', 'truncated JSON line', None, [], REJECT, r'^json: ',
                 raw=tl[:len(tl) // 2] + '\n'))
    nl = compact(R.rec(PICK['null2'])).decode()
    k0 = first_nonempty_cofactor(R.rec(PICK['null2'])['cert']['cofactors'])
    c0 = R.rec(PICK['null2'])['cert']['cofactors'][k0][0][0]
    i0 = nl.index('"%s":[["%s"' % (k0, c0))
    j0 = i0 + len('"%s":[[' % k0)
    out.append(C('null', 'null2', 'coefficient written as a JSON float literal', None, [], REJECT,
                 r'^json: floating-point literal 1\.5', raw=nl[:j0] + '1.5' + nl[j0 + len(c0) + 2:]))
    trl = compact(R.rec(PICK['tree_L2_L1a'])).decode()
    iv = R.rec(PICK['tree_L2_L1a'])['cert']['witness']['field']['interval']
    s_iv = '"interval":%s' % json.dumps(iv, separators=(',', ':'))
    assert s_iv in trl
    out.append(C('tree', 'tree_L2_L1a', 'NaN in the field interval', None, [], REJECT, r'^json: non-finite constant NaN',
                 raw=trl.replace(s_iv, '"interval":[NaN,%s]' % json.dumps(iv[1]), 1)))
    out.append(C('tu', 'tu_gp', 'record with an extra top-level key', None, [], REJECT, r'^record: schema',
                 raw=tl.replace('{"cert"', '{"aux":1,"cert"', 1)))
    return out


# ------------------------------------------------------------------------------ data controls

def data_controls():
    res = []
    with open(os.path.join(V.DEFAULT_DATA, 'tu-gadgets.json')) as fh:
        gad = json.load(fh)
    for gi, drop in ((0, [0, 3]), (3, [2, 3]), (5, [5, 6])):
        bad = copy.deepcopy(gad)
        bad[gi]['edges'] = [e for e in bad[gi]['edges'] if e != drop]
        bad[gi]['m'] = len(bad[gi]['edges'])
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, dir=HERE) as tmp:
            json.dump(bad, tmp)
        try:
            V.load_gadgets(tmp.name)
            verdict, why = 'LOADED', 'broken gadget accepted as TU'
        except RuntimeError as exc:
            verdict, why = REJECT, str(exc)
        finally:
            os.unlink(tmp.name)
        res.append({'type': 'data', 'source': 'tu-gadgets.json[%d]' % gi,
                    'mutation': 'gadget %d with edge %s deleted (TU proof must fail)' % (gi, drop),
                    'expected': REJECT, 'verdict': verdict, 'reason': why,
                    'pass': verdict == REJECT and 'TU property NOT re-proved' in why})
    with open(os.path.join(V.DEFAULT_DATA, 'forbidden-398.json')) as fh:
        forb = json.load(fh)
    cases = []
    b1 = copy.deepcopy(forb)
    b1[200] = b1[200][:-1]                                    # one edge removed from a GP-10 member
    cases.append(('F10 member 200 loses an edge (digest check on)', b1, None, r'does not match the contract prefix'))
    cases.append(('F10 member 200 loses an edge (digest check off)', b1, '', None))
    b2 = copy.deepcopy(forb)
    b2[5], b2[6] = b2[6], b2[5]                               # a 7-vertex and an 8-vertex member swapped
    cases.append(('two F10 members swapped across the 7/8-vertex boundary (digest off)', b2, '',
                  r'not sorted by vertex count'))
    b3 = copy.deepcopy(forb)
    b3[40] = b3[40] + [[0, 8]] if [0, 8] not in b3[40] and [8, 0] not in b3[40] else b3[40][:-1]
    cases.append(('a GP member gains an edge (composition of the first 74 changes; digest off)', b3, '',
                  r'composition'))
    b4 = forb[:-1]
    cases.append(('F10 truncated to 397 graphs (digest off)', b4, '', r'expected 398 graphs'))
    for desc, data, prefix, rx in cases:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, dir=HERE) as tmp:
            json.dump(data, tmp)
        old = V.F10_SHA256_PREFIX
        if prefix is not None:
            V.F10_SHA256_PREFIX = prefix
        try:
            V.load_forbidden(tmp.name)
            verdict, why = 'LOADED', 'altered F10 list loaded'
        except RuntimeError as exc:
            verdict, why = REJECT, str(exc)
        finally:
            V.F10_SHA256_PREFIX = old
            os.unlink(tmp.name)
        if rx is None:
            # an edge removed from a 10-vertex member changes neither order nor GP's 74: with the
            # digest check off it LOADS, which is why the digest check exists (recorded, expected)
            res.append({'type': 'data', 'source': 'forbidden-398.json', 'mutation': desc,
                        'expected': 'LOADED (digest check is the only guard; recorded on purpose)',
                        'verdict': verdict, 'reason': why, 'pass': verdict == 'LOADED'})
        else:
            res.append({'type': 'data', 'source': 'forbidden-398.json', 'mutation': desc, 'expected': REJECT,
                        'verdict': verdict, 'reason': why, 'pass': verdict == REJECT and re.search(rx, why) is not None})
    return res


# ------------------------------------------------------------------------------ end to end

def end_to_end(R, controls, workdir):
    """Write mutants (one per source, distinct graph6) and unmutated originals into one records
    file and run the real command line on it."""
    os.makedirs(workdir, exist_ok=True)
    chosen = []
    used = set()
    for c in controls:
        if c.raw is not None or c.ctx_kind != 'b11' or c.expected != REJECT:
            continue
        g = c.rec['g6']
        comp_g6 = {x['g6'] for x in c.companions}
        if g in used or comp_g6 & used or g in comp_g6:
            continue
        if not any(t in c.desc for t in ('REQUIRED', 'pointer', 'target')):
            continue
        chosen.append(c)
        used.add(g)
        used |= comp_g6
    lines = []
    expect = {}
    for c in chosen:
        lines.append(compact(c.rec))
        expect[c.rec['g6']] = (REJECT, c.regex, c.desc)
        for x in c.companions:
            lines.append(compact(x))
            expect.setdefault(x['g6'], (None, None, 'companion'))
    for key in ('tu_gp10', 'tree_deg4', 'real_dag_sos', 'null2', 'tu_dag'):
        g = PICK[key]
        if g in used:
            continue
        lines.append(R.line(g))
        expect[g] = (ACCEPT, None, 'unmutated original %s' % key)
        used.add(g)
        for x in companions_of(R, g):
            if x['g6'] not in used:
                lines.append(compact(x))
                used.add(x['g6'])
                expect.setdefault(x['g6'], (None, None, 'companion'))
    # more unmutated originals: the two smallest records of every type not used above
    extra_orig = []
    for typ in ('tu', 'sub', 'tree', 'null', 'null-dag', 'real', 'real-dag'):
        k = 0
        for e in sorted((e for e in R.index if e['type'] == typ), key=lambda e: (e['length'], e['g6'])):
            if k == 2:
                break
            if e['g6'] in used or (e['ptr'] and e['ptr'] in used):
                continue
            lines.append(R.line(e['g6']))
            expect[e['g6']] = (ACCEPT, None, 'unmutated record %s (%s)' % (e['g6'], typ))
            used.add(e['g6'])
            extra_orig.append(e['g6'])
            if e['ptr']:
                lines.append(R.line(e['ptr']))
                used.add(e['ptr'])
                expect.setdefault(e['ptr'], (ACCEPT, None, 'unmutated pointer target %s' % e['ptr']))
            k += 1
    recp = os.path.join(workdir, 'records.jsonl')
    with open(recp, 'wb') as fo:
        for l in lines:
            fo.write(l)
    py = sys.executable
    me = os.path.join(HERE, 'verify_refutations11.py')
    idx = os.path.join(workdir, 'index.jsonl')
    parts = [os.path.join(workdir, 'part%d.jsonl' % i) for i in range(2)]
    for p in parts:
        if os.path.exists(p):
            os.unlink(p)
    subprocess.run([py, me, 'scan', recp, '--index', idx], check=True, stderr=subprocess.DEVNULL)
    for i, p in enumerate(parts):
        subprocess.run([py, me, 'check', recp, '--index', idx, '--out', p, '--shard', '%d/2' % i,
                        '--jobs', '2', '--mem-gb', '3'], check=True, stderr=subprocess.DEVNULL)
    ver = os.path.join(workdir, 'verdicts.jsonl')
    summ = os.path.join(workdir, 'summary.json')
    subprocess.run([py, me, 'resolve', '--index', idx, '--out', ver, '--summary', summ, '--sample'] + parts,
                   stderr=subprocess.DEVNULL)
    got = {}
    with open(ver) as fh:
        for x in fh:
            o = json.loads(x)
            got[o['g6']] = o
    res = []
    for g, (want, rx, desc) in expect.items():
        o = got.get(g)
        if want is None:
            continue
        ok = o is not None and o['verdict'] == want and (rx is None or re.search(rx, o['reason']) is not None)
        res.append({'type': 'end-to-end', 'g6': g, 'mutation': desc, 'expected': want,
                    'verdict': o['verdict'] if o else 'MISSING', 'reason': o['reason'] if o else '', 'pass': ok})
    # a stale index: two entries' offsets exchanged, so each line holds the other record
    ix = V.load_index(idx)
    a, b = next((x, y) for x in ix for y in ix if x['g6'] in extra_orig and y['g6'] in extra_orig and x['i'] < y['i'])
    a2, b2 = dict(a), dict(b)
    a2['offset'], a2['length'], b2['offset'], b2['length'] = b['offset'], b['length'], a['offset'], a['length']
    bad_idx = os.path.join(workdir, 'index-stale.jsonl')
    with open(bad_idx, 'w') as fo:
        fo.write(json.dumps(a2) + '\n' + json.dumps(b2) + '\n')
    stale = os.path.join(workdir, 'part-stale.jsonl')
    if os.path.exists(stale):
        os.unlink(stale)
    subprocess.run([py, me, 'check', recp, '--index', bad_idx, '--out', stale, '--jobs', '1'],
                   check=True, stderr=subprocess.DEVNULL)
    with open(stale) as fh:
        for x in fh:
            o = json.loads(x)
            ok = o['own'] == REJECT and o['reason'].startswith('index mismatch')
            res.append({'type': 'end-to-end', 'g6': o['g6'], 'mutation': 'stale index (offsets of two records exchanged)',
                        'expected': REJECT, 'verdict': o['own'], 'reason': o['reason'], 'pass': ok})
    # a records file that is not the one the index was built from (one extra line): refused
    longer = os.path.join(workdir, 'records-longer.jsonl')
    with open(recp, 'rb') as fi, open(longer, 'wb') as fo:
        fo.write(fi.read() + lines[0])
    longer_out = os.path.join(workdir, 'part-longer.jsonl')
    if os.path.exists(longer_out):
        os.unlink(longer_out)
    pr = subprocess.run([py, me, 'check', longer, '--index', idx, '--out', longer_out, '--jobs', '1'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    msg = pr.stderr.decode().strip().split('\n')[-1]
    res.append({'type': 'end-to-end', 'g6': None, 'mutation': 'records file differs in size from the indexed one',
                'expected': REJECT, 'verdict': REJECT if pr.returncode != 0 else 'RAN',
                'reason': msg[:200], 'pass': pr.returncode != 0 and 'rescan' in msg and not os.path.exists(longer_out)})
    return res, len(lines)


# ------------------------------------------------------------------------------ main

def main(argv):
    records, index_path, dst = argv[1], argv[2], argv[3]
    workdir = os.path.join(os.path.dirname(os.path.abspath(dst)), 'redteam-e2e')
    if '--workdir' in argv:
        workdir = argv[argv.index('--workdir') + 1]
    CTX['b11'] = V.load_context(V.DEFAULT_DATA, 11)
    CTX['noorder'] = dict(CTX['b11'], order=None)
    R = Records(records, V.load_index(index_path))
    pick_auto(R)
    sys.stderr.write('picks: %s\n' % json.dumps(PICK))

    def originals_pass(label):
        out = []
        for key, g in PICK.items():
            lines = [R.line(g)] + [compact(x) for x in companions_of(R, g)]
            r = run(lines, 'b11', g)
            out.append({'key': key, 'g6': g, 'type': R.by_g6[g]['type'], 'verdict': r['verdict'],
                        'reason': r['reason'], 'when': label})
        return out
    originals = originals_pass('before mutations')
    controls = []
    controls += tu_controls(R)
    controls += sub_controls(R)
    controls += null_controls(R)
    controls += dag_controls(R, 'null-dag', ['null_dag', 'null_dag2'])
    controls += real_controls(R, 'real', ['real_sos', 'real_sturm'])
    controls += dag_controls(R, 'real-dag', ['real_dag_sos', 'real_dag_sturm'])
    controls += real_controls(R, 'real-dag', ['real_dag_sos', 'real_dag_sturm'], common=False)
    controls += tree_controls(R)
    controls += tree_grammar_controls(R)
    controls += transplant_controls(R)
    controls += attack_controls(R)
    controls += raw_controls(R)
    results = []
    for c in controls:
        if c.raw is not None:
            line = c.raw.encode()
            src = compact(R.rec(PICK[c.source])) if c.source in PICK else None
            changed = src is None or line != src
            r = run([line], c.ctx_kind)
        else:
            line = compact(c.rec)
            src_g6 = PICK.get(c.source)
            changed = True
            if src_g6 is not None and c.rec.get('g6') == src_g6:
                changed = line != compact(R.rec(src_g6))
            if c.expected == ACCEPT:
                changed = True
            comps = [compact(x) for x in c.companions]
            if not changed and c.companions:
                changed = any(compact(x) != compact(R.rec(x['g6'])) for x in c.companions if x['g6'] in R.by_g6)
            r = run([line] + comps, c.ctx_kind, c.rec.get('g6'))
        if not changed:
            results.append({'type': c.typ, 'source': c.source, 'mutation': c.desc, 'expected': c.expected,
                            'verdict': 'NO-OP', 'reason': 'mutation did not change the record', 'pass': False})
            continue
        ok = r['verdict'] == c.expected and (c.regex is None or re.search(c.regex, r['reason']) is not None)
        results.append({'type': c.typ, 'source': c.source, 'source_g6': PICK.get(c.source), 'mutation': c.desc,
                        'expected': c.expected, 'expected_reason': c.regex, 'verdict': r['verdict'],
                        'reason': r['reason'], 'pass': ok})
    dl = R.line(PICK['tu_gp10'])
    rr = [V.verify_line(dl, CTX['b11']), V.verify_line(dl, CTX['b11'])]
    V.resolve(rr)
    results.append({'type': 'run', 'source': 'tu_gp10', 'mutation': 'the same record twice in one run (duplicate graph6)',
                    'expected': REJECT, 'verdict': rr[0]['verdict'], 'reason': rr[0]['reason'],
                    'pass': all(x['verdict'] == REJECT and x['reason'].startswith('duplicate record') for x in rr)})
    data = data_controls()
    e2e, e2e_lines = end_to_end(R, controls, workdir)
    originals_after = originals_pass('after mutations')
    allres = results + data + e2e
    summary = {}
    for x in allres:
        s = summary.setdefault(x['type'], {'negative': 0, 'rejected_as_expected': 0, 'positive': 0,
                                           'accepted': 0, 'other': 0, 'other_pass': 0})
        if x['expected'] == REJECT:
            s['negative'] += 1
            s['rejected_as_expected'] += int(x['pass'])
        elif x['expected'] == ACCEPT:
            s['positive'] += 1
            s['accepted'] += int(x['pass'])
        else:
            s['other'] += 1
            s['other_pass'] += int(x['pass'])
    required = [x for x in results if 'REQUIRED' in x['mutation']]
    out = {'picks': PICK,
           'originals_before': originals, 'originals_after': originals_after,
           'originals_all_accepted': all(o['verdict'] == ACCEPT for o in originals + originals_after),
           'controls': allres, 'summary_by_type': summary,
           'required_controls': [{k: x[k] for k in ('mutation', 'source', 'verdict', 'reason', 'pass')}
                                 for x in required],
           'end_to_end_records': e2e_lines,
           'all_controls_pass': all(x['pass'] for x in allres),
           'n_controls': len(allres), 'n_failed': sum(1 for x in allres if not x['pass'])}
    with open(dst, 'w') as fo:
        json.dump(out, fo, indent=1)
    for o in originals:
        print('ORIGINAL %-15s %-9s %s %s' % (o['key'], o['type'], o['verdict'], o['reason'][:80]))
    for x in allres:
        print('%-4s %-10s %-11s %-70s | %s' % ('ok' if x['pass'] else 'FAIL', x['type'], x['verdict'],
                                               x['mutation'][:70], x['reason'][:100]))
    print(json.dumps(summary))
    print('originals_all_accepted', out['originals_all_accepted'], 'all_controls_pass', out['all_controls_pass'],
          'n_controls', out['n_controls'], 'n_failed', out['n_failed'])
    return 0 if out['originals_all_accepted'] and out['all_controls_pass'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
