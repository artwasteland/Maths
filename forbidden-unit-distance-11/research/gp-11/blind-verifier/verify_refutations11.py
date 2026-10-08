#!/usr/bin/env python3
"""verify_refutations11.py: blind, independent second verifier for GP-11 refutation certificates.

Extends gp10-blind-verifier/verify_refutations.py (sha256 3af7b336...) to the GP-11 records.
Written only from the specification in ./spec (GP-11 CONTRACT/FORMAT/PROOFS; GP-10 CONTRACT,
FORMAT and PROOFS, whose certificate format GP-11 keeps; the u(22) CONTRACT and gadget proofs;
AMP Section 4) and the predecessor's own code.  It imports no checker, kernel, producer or
pipeline code.  Every change from the predecessor is marked "GP-11:" in a comment.

Subcommands
-----------
  scan RECORDS --index INDEX.jsonl
        Stream RECORDS once; write one index line per refuted record (byte offset, length, g6,
        type, pointer target) and INDEX.jsonl.meta.json (size, sha256, verdict counts,
        duplicate g6 count).  Only the refuted records are verified later.
  check RECORDS --index INDEX.jsonl --out PART.jsonl [--shard i/n] [--jobs N]
        [--select FILE] [--timeout S] [--mem-gb G] [--order 11]
        Verify the refuted records of shard i of n (records dealt to shards by size, so the
        shards carry similar bytes).  Each record is verified in its own forked process, so its
        wall time, CPU time and peak resident memory are measured by the operating system (wait4).
        Results are appended as they finish; rerunning the same command resumes.
  resolve --index INDEX.jsonl --out VERDICTS.jsonl --summary SUMMARY.json PART.jsonl ...
        Merge the parts, check coverage, resolve record pointers (sub, and tu ends at a refuted
        record) across shards with cycle detection, and write the final verdicts and summary.
        --sample marks a run over a selected subset (coverage is then not required).
  run RECORDS --out VERDICTS.jsonl --summary SUMMARY.json [--jobs N]
        scan + check (all shards) + resolve in one invocation; index and part files are written
        next to VERDICTS.jsonl.

Verdicts (per refuted record)
  ACCEPT       the certificate proves the record's graph has no unit-distance embedding (an
               injective map V -> R^2 with every edge of length exactly 1).  A TU chain ending
               at an F10 member also rests on that member being forbidden (GP's theorem for
               indices 0..73, GP-10's result for 74..397); the reason names the index.
  REJECT       some step failed; the reason names the step.
  UNSUPPORTED  this verifier does not implement the construct, ran out of a resource limit, or
               crashed (never a statement about the certificate).

Exact arithmetic only (python-flint fmpq / fmpq_poly / fmpq_mpoly; sympy rationals as a second
opinion for Sturm counts).  No floats are used in any decision.
"""
import os
os.environ.setdefault('SYMPY_GROUND_TYPES', 'python')
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

import sys
import json
import re
import time
import hashlib
import itertools
import argparse
import resource
import signal

import flint
from flint import fmpq, fmpq_poly, fmpq_mpoly_ctx

ACCEPT, REJECT, UNSUPPORTED = 'ACCEPT', 'REJECT', 'UNSUPPORTED'

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, 'data')                       # GP-11: workspace layout

MAX_DAG_ROWS = 256          # amendment 5
MAX_EXPONENT = 10000        # resource guard only (can reject, never accept)
MAX_TREE_DEPTH = 400        # resource guard only
SIGN_BISECTION_BUDGET = 4000

# GP-11: CONTRACT Section 1.  F10 = the 398 graphs of forbidden-398.json, in file order; its
# prefixes of length 1, 2, 3, 6, 19, 74, 398 are the members on at most 4, 5, ..., 10 vertices.
F10_SHA256_PREFIX = '8e8a81a145f75a65'
F10_PREFIX_LENGTHS = {4: 1, 5: 2, 6: 3, 7: 6, 8: 19, 9: 74, 10: 398}
GP74_COMPOSITION = {(4, 6): 1, (5, 6): 1, (6, 9): 1, (7, 10): 1, (7, 11): 2, (8, 12): 3,
                    (8, 13): 10, (9, 13): 2, (9, 14): 19, (9, 15): 34}
GP11_ORDER = 11


class Reject(Exception):
    """The certificate does not prove what it claims (reason in args[0])."""


class Unsupported(Exception):
    """This verifier does not implement the construct (reason in args[0])."""


# ---------------------------------------------------------------------------------------------
# Strict JSON and scalar grammar (unchanged from the predecessor)
# ---------------------------------------------------------------------------------------------

def _pairs_hook(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise Reject('json: duplicate key %r' % (k,))
        d[k] = v
    return d


def _bad_constant(s):
    raise Reject('json: non-finite constant %s' % s)


def _bad_float(s):
    raise Reject('json: floating-point literal %s' % s[:40])


def strict_loads(data):
    try:
        return json.loads(data, object_pairs_hook=_pairs_hook,
                          parse_constant=_bad_constant, parse_float=_bad_float)
    except Reject:
        raise
    except Exception as exc:  # malformed JSON
        raise Reject('json: %s' % (str(exc)[:120],))


def is_int(x):
    return type(x) is int  # excludes bool


def need_keys(obj, keys, where):
    if not isinstance(obj, dict):
        raise Reject('%s: expected an object' % where)
    got = set(obj.keys())
    want = set(keys)
    if got != want:
        extra = sorted(got - want)
        missing = sorted(want - got)
        raise Reject('%s: schema (extra %s, missing %s)' % (where, extra, missing))


RAT_RE = re.compile(r'[+-]?[0-9]+(?:/[0-9]+)?')
_RAT_CACHE = {}


def parse_rat_str(s, where):
    """GP-10 rational: a JSON string [+-]?digits(/digits)? with a positive denominator."""
    if type(s) is not str:
        raise Reject('%s: bad rational %r' % (where, s))
    q = _RAT_CACHE.get(s)                       # GP-11: memo (speed only; same grammar)
    if q is not None:
        return q
    if RAT_RE.fullmatch(s) is None:
        raise Reject('%s: bad rational %r' % (where, s[:40]))
    if '/' in s:
        p, d = s.split('/')
        d = int(d)
        if d == 0:
            raise Reject('%s: zero denominator' % where)
        q = fmpq(int(p), d)
    else:
        q = fmpq(int(s))
    if len(_RAT_CACHE) > 200000:
        _RAT_CACHE.clear()
    _RAT_CACHE[s] = q
    return q


def parse_rat_tree(x, where):
    """Tree-witness rational: a JSON integer or a rational string of the same grammar."""
    if is_int(x):
        return fmpq(x)
    return parse_rat_str(x, where)


def parse_int_tree(x, where):
    """GP-11: an integer in the tree witness's integer-or-rational grammar: a JSON integer, or
    a rational string (amendment 3 spelling) whose value is an integer, such as "-3" or "6/2".
    "3/2", "x", "1.0" and booleans are rejected."""
    q = parse_rat_tree(x, where)
    if q.q != 1:
        raise Reject('%s: %r is not an integer' % (where, x))
    return q


def parse_vertex(x, n, where):
    if not is_int(x) or not (0 <= x < n):
        raise Reject('%s: bad vertex %r' % (where, x))
    return x


# ---------------------------------------------------------------------------------------------
# graph6 (unchanged)
# ---------------------------------------------------------------------------------------------

def decode_g6(s):
    """Decode a graph6 string (no header, no whitespace, zero padding, minimal order encoding).
    Returns (n, frozenset of (u, v) with u < v)."""
    if type(s) is not str or not s:
        raise Reject('g6: not a nonempty string')
    try:
        b = s.encode('ascii')
    except UnicodeEncodeError:
        raise Reject('g6: non-ascii')
    if any(c < 63 or c > 126 for c in b):
        raise Reject('g6: character out of range')
    if b[0] == 126:
        if len(b) >= 2 and b[1] == 126:
            raise Unsupported('g6: 6-byte order encoding not supported')
        if len(b) < 4:
            raise Reject('g6: truncated order')
        n = ((b[1] - 63) << 12) | ((b[2] - 63) << 6) | (b[3] - 63)
        if n <= 62:
            raise Reject('g6: non-minimal order encoding')
        body = b[4:]
    else:
        n = b[0] - 63
        body = b[1:]
    nbits = n * (n - 1) // 2
    if len(body) != (nbits + 5) // 6:
        raise Reject('g6: wrong length for n=%d' % n)
    bits = []
    for c in body:
        v = c - 63
        for k in range(5, -1, -1):
            bits.append((v >> k) & 1)
    if any(bits[nbits:]):
        raise Reject('g6: nonzero padding bits')
    edges = set()
    idx = 0
    for j in range(1, n):
        for i in range(j):
            if bits[idx]:
                edges.add((i, j))
            idx += 1
    return n, frozenset(edges)


def norm_edge(u, v):
    return (u, v) if u < v else (v, u)


# ---------------------------------------------------------------------------------------------
# Number field K = Q[x]/(m) with a chosen real root theta, and complex elements of K(i)
# (unchanged)
# ---------------------------------------------------------------------------------------------

def sturm_sequence(p):
    seq = [p, p.derivative()]
    while not seq[-1].is_zero():
        r = seq[-2] % seq[-1]
        seq.append(-r)
    seq.pop()  # the trailing zero
    return seq


def _sign(q):
    return (q > 0) - (q < 0)


def _variations(signs):
    s = [x for x in signs if x != 0]
    return sum(1 for a, b in zip(s, s[1:]) if a != b)


def sturm_count_R(p):
    """Number of DISTINCT real roots of a nonzero fmpq_poly p, by an exact Sturm sequence."""
    if p.is_zero():
        raise ValueError('zero polynomial')
    if p.degree() == 0:
        return 0
    seq = sturm_sequence(p)
    at_pos = [_sign(q.leading_coefficient()) for q in seq]
    at_neg = [_sign(q.leading_coefficient()) * (-1 if q.degree() % 2 else 1) for q in seq]
    return _variations(at_neg) - _variations(at_pos)


def sturm_count_interval(p, lo, hi):
    """Distinct real roots of p in (lo, hi] (lo < hi); exact."""
    seq = sturm_sequence(p)
    return _variations([_sign(q(lo)) for q in seq]) - _variations([_sign(q(hi)) for q in seq])


def interval_eval(p, lo, hi):
    """Exact rational enclosure of {p(t) : lo <= t <= hi} by interval Horner (lo <= hi)."""
    cs = p.coeffs()
    if not cs:
        return fmpq(0), fmpq(0)
    a = b = fmpq(cs[-1])
    for c in reversed(cs[:-1]):
        prods = (a * lo, a * hi, b * lo, b * hi)
        a, b = min(prods) + c, max(prods) + c
    return a, b


class Field:
    """K = Q[x]/(m) with m irreducible over Q and exactly one real root theta in [lo, hi].
    Elements are fmpq_poly of degree < deg(m); evaluation at theta is injective on K, so
    K is a real field and K(i) is a field."""

    def __init__(self, coeffs, lo, hi):
        if len(coeffs) < 2 or coeffs[-1] == 0:
            raise Reject('field: minpoly must have positive degree and nonzero leading coeff')
        self.m = fmpq_poly(coeffs)
        self.deg = self.m.degree()
        _content, facs = self.m.factor()
        if len(facs) != 1 or facs[0][1] != 1 or facs[0][0].degree() != self.deg:
            raise Reject('field: minpoly is not irreducible over Q')
        if not lo < hi:
            raise Reject('field: interval needs lo < hi')
        mlo, mhi = self.m(lo), self.m(hi)
        if not (mlo * mhi < 0):
            raise Reject('field: minpoly has no strict sign change on the interval')
        if sturm_count_interval(self.m, lo, hi) != 1:
            raise Reject('field: interval does not isolate exactly one real root')
        self.lo, self.hi = lo, hi
        self.zero = fmpq_poly([])
        self.one = fmpq_poly([1])

    def red(self, p):
        return p % self.m

    def inv(self, p):
        p = self.red(p)
        if p.is_zero():
            raise Reject('field: division by zero')
        g, s, _t = p.xgcd(self.m)
        if g.degree() != 0:
            raise Reject('field: non-invertible element')
        return self.red(s * (fmpq(1) / g.coeffs()[0]))

    def sign(self, p):
        """Exact sign of p(theta)."""
        p = self.red(p)
        if p.is_zero():
            return 0
        lo, hi = self.lo, self.hi
        mlo_sign = _sign(self.m(lo))
        for _ in range(SIGN_BISECTION_BUDGET):
            a, b = interval_eval(p, lo, hi)
            if a > 0:
                return 1
            if b < 0:
                return -1
            mid = (lo + hi) / 2
            mm = _sign(self.m(mid))
            if mm == 0:  # theta == mid exactly (only possible for degree 1)
                return _sign(p(mid))
            if mm != mlo_sign:
                hi = mid
            else:
                lo, mlo_sign = mid, mm
        raise Reject('field: sign bisection budget exhausted')

    # complex elements are pairs (re, im) of reduced fmpq_poly
    def c(self, re, im=None):
        return (self.red(re), self.red(im) if im is not None else self.zero)

    def cadd(self, x, y):
        return (x[0] + y[0], x[1] + y[1])

    def csub(self, x, y):
        return (x[0] - y[0], x[1] - y[1])

    def cneg(self, x):
        return (-x[0], -x[1])

    def cmul(self, x, y):
        a, b = x
        c, d = y
        return (self.red(a * c - b * d), self.red(a * d + b * c))

    def cscale(self, r, x):  # r real (fmpq_poly), x complex
        return (self.red(r * x[0]), self.red(r * x[1]))

    def cnorm2(self, x):
        return self.red(x[0] * x[0] + x[1] * x[1])

    def cinv(self, x):
        n2 = self.cnorm2(x)
        if n2.is_zero():
            raise Reject('field: complex division by zero')
        ni = self.inv(n2)
        return (self.red(x[0] * ni), self.red(-x[1] * ni))

    def ciszero(self, x):
        return x[0].is_zero() and x[1].is_zero()


QFIELD = None


def rational_field():
    global QFIELD
    if QFIELD is None:
        QFIELD = Field([fmpq(0), fmpq(1)], fmpq(-1), fmpq(1))  # K = Q, theta = 0
    return QFIELD


class RowSpace:
    """Row space over K(i) of complex vectors of length n, kept in reduced row echelon form."""

    def __init__(self, F, n, rows=()):
        self.F, self.n = F, n
        self.basis, self.pivots = [], []
        for r in rows:
            self.add(r)

    def copy(self):
        rs = RowSpace(self.F, self.n)
        rs.basis = [list(b) for b in self.basis]
        rs.pivots = list(self.pivots)
        return rs

    def reduce(self, v):
        F = self.F
        v = list(v)
        for b, j in zip(self.basis, self.pivots):
            if not F.ciszero(v[j]):
                f = v[j]
                v = [F.csub(vx, F.cmul(f, bx)) for vx, bx in zip(v, b)]
        return v

    def contains(self, v):
        return all(self.F.ciszero(x) for x in self.reduce(v))

    def add(self, v):
        F = self.F
        if len(v) != self.n:
            raise Reject('linear algebra: row of wrong length')
        r = self.reduce(v)
        j = next((k for k, x in enumerate(r) if not F.ciszero(x)), None)
        if j is None:
            return False
        inv = F.cinv(r[j])
        r = [F.cmul(inv, x) for x in r]
        for bi, b in enumerate(self.basis):
            if not F.ciszero(b[j]):
                f = b[j]
                self.basis[bi] = [F.csub(bx, F.cmul(f, rx)) for bx, rx in zip(b, r)]
        self.basis.append(r)
        self.pivots.append(j)
        return True

    def rank(self):
        return len(self.basis)

    def contains_space(self, other):
        return all(self.contains(b) for b in other.basis)


def unit_vec(F, n, pairs):
    """Complex vector from {vertex: complex coefficient} contributions."""
    v = [(F.zero, F.zero)] * n
    v = list(v)
    for idx, coef in pairs:
        v[idx] = F.cadd(v[idx], coef)
    return v


def four_cycles(n, E):
    """All 4-cycles (v1,v2,v3,v4) of the graph, each once; the rhombus row is
    e_v1 - e_v2 + e_v3 - e_v4 (f(v1) + f(v3) = f(v2) + f(v4))."""
    out = []
    for quad in itertools.combinations(range(n), 4):
        a, b, c, d = quad
        for (p1, p2, p3, p4) in ((a, b, c, d), (a, b, d, c), (a, c, b, d)):
            if (norm_edge(p1, p2) in E and norm_edge(p2, p3) in E and
                    norm_edge(p3, p4) in E and norm_edge(p4, p1) in E):
                out.append((p1, p2, p3, p4))
    return out


def rhombus_rows(F, n, E):
    one = F.c(F.one)
    mone = F.c(-F.one)
    return [unit_vec(F, n, [(p1, one), (p2, mone), (p3, one), (p4, mone)])
            for (p1, p2, p3, p4) in four_cycles(n, E)]


# ---------------------------------------------------------------------------------------------
# Trusted data: the F10 list and the TU gadgets (the gadgets' TU property is re-proved here)
# ---------------------------------------------------------------------------------------------

def _parse_edge_list(el, where):
    es = set()
    if not isinstance(el, list):
        raise RuntimeError('%s: not an edge list' % where)
    for e in el:
        if (not isinstance(e, list) or len(e) != 2 or not is_int(e[0]) or not is_int(e[1])
                or e[0] == e[1] or e[0] < 0 or e[1] < 0):
            raise RuntimeError('%s: bad edge %r' % (where, e))
        ne = norm_edge(e[0], e[1])
        if ne in es:
            raise RuntimeError('%s: duplicate edge' % where)
        es.add(ne)
    k = 1 + max(max(e) for e in es)
    if {v for e in es for v in e} != set(range(k)):
        raise RuntimeError('%s: vertex labels not 0..k-1' % where)
    return k, frozenset(es)


def load_forbidden(path):
    """GP-11: F10 (398 graphs).  Stored JSON labels, file order.  Checks the contract's digest
    prefix, the prefix structure by vertex count, and GP's composition of the first 74."""
    with open(path, 'rb') as fh:
        blob = fh.read()
    digest = hashlib.sha256(blob).hexdigest()
    if not digest.startswith(F10_SHA256_PREFIX):
        raise RuntimeError('forbidden-398.json: sha256 %s does not match the contract prefix %s'
                           % (digest[:16], F10_SHA256_PREFIX))
    raw = strict_loads(blob)
    if not isinstance(raw, list) or len(raw) != 398:
        raise RuntimeError('forbidden-398.json: expected 398 graphs')
    out = [_parse_edge_list(el, 'forbidden-398.json[%d]' % i) for i, el in enumerate(raw)]
    for i in range(1, len(out)):
        if out[i][0] < out[i - 1][0]:
            raise RuntimeError('forbidden-398.json: not sorted by vertex count')
    for nv, plen in F10_PREFIX_LENGTHS.items():
        if sum(1 for k, _ in out if k <= nv) != plen:
            raise RuntimeError('forbidden-398.json: prefix for <= %d vertices is not %d' % (nv, plen))
    comp = {}
    for k, es in out[:74]:
        comp[(k, len(es))] = comp.get((k, len(es)), 0) + 1
    if comp != GP74_COMPOSITION:
        raise RuntimeError('forbidden-398.json: first 74 have composition %r, not GP\'s' % comp)
    return out, digest


def gadget_is_tu(n, E, pair):
    """Re-prove the TU property as in U22-GADGET-PROOFS.md: the displacement of the
    distinguished pair equals +-(displacement of an existing edge) modulo the rhombus
    relations of the gadget's 4-cycles, so it has length 1 in every embedding.
    Returns the witnessing edge and sign, or None."""
    F = rational_field()
    rs = RowSpace(F, n, rhombus_rows(F, n, E))
    a, b = pair
    one, mone = F.c(F.one), F.c(-F.one)
    for (u, v) in sorted(E):
        for s in (1, -1):
            su, sv = (mone, one) if s == 1 else (one, mone)
            vec = unit_vec(F, n, [(a, one), (b, mone), (u, su), (v, sv)])
            if rs.contains(vec):
                return (u, v, s)
    return None


def load_gadgets(path):
    with open(path, 'rb') as fh:
        blob = fh.read()
    raw = strict_loads(blob)
    if not isinstance(raw, list) or len(raw) != 6:
        raise RuntimeError('tu-gadgets.json: expected 6 gadgets')
    out = []
    for i, g in enumerate(raw):
        need_keys(g, ['n', 'm', 'edges', 'pair'], 'gadget %d' % i)
        n = g['n']
        es = set()
        for e in g['edges']:
            u, v = parse_vertex(e[0], n, 'gadget'), parse_vertex(e[1], n, 'gadget')
            if u == v or norm_edge(u, v) in es:
                raise RuntimeError('gadget %d: bad edge' % i)
            es.add(norm_edge(u, v))
        if len(es) != g['m']:
            raise RuntimeError('gadget %d: edge count' % i)
        a, b = parse_vertex(g['pair'][0], n, 'gadget'), parse_vertex(g['pair'][1], n, 'gadget')
        if a == b or norm_edge(a, b) in es:
            raise RuntimeError('gadget %d: distinguished pair must be a non-edge' % i)
        es = frozenset(es)
        if gadget_is_tu(n, es, (a, b)) is None:
            raise RuntimeError('gadget %d: TU property NOT re-proved by rhombus algebra' % i)
        out.append((n, es, (a, b)))
    return out, hashlib.sha256(blob).hexdigest()


def load_context(data_dir, order=GP11_ORDER):
    forb, fsha = load_forbidden(os.path.join(data_dir, 'forbidden-398.json'))
    gad, gsha = load_gadgets(os.path.join(data_dir, 'tu-gadgets.json'))
    return {'forbidden': forb, 'gadgets': gad, 'order': order,
            'forbidden_sha256': fsha, 'gadgets_sha256': gsha}


def premise_of(j):
    """GP-11: who proves F10[j] forbidden (the lower-order premise, PROOFS 'The lower-order
    premise')."""
    return 'GP theorem' if j < 74 else 'GP-10 result'


# ---------------------------------------------------------------------------------------------
# R-tu
# ---------------------------------------------------------------------------------------------

def check_map(mp, src_n, src_E, dst_n, dst_E, where):
    """mp: JSON list; must be an injective, edge-preserving map src -> dst."""
    if not isinstance(mp, list) or len(mp) != src_n:
        raise Reject('%s: map must be a list of length %d' % (where, src_n))
    img = [parse_vertex(x, dst_n, where + ' map') for x in mp]
    if len(set(img)) != len(img):
        raise Reject('%s: map not injective' % where)
    for (u, v) in sorted(src_E):
        if norm_edge(img[u], img[v]) not in dst_E:
            raise Reject('%s: map not edge-preserving (edge %d-%d -> %d-%d is not an edge)'
                         % (where, u, v, img[u], img[v]))
    return img


def verify_tu(n, E, cert, ctx):
    need_keys(cert, ['type', 'steps', 'end'], 'tu')
    steps = cert['steps']
    if not isinstance(steps, list) or not steps:
        raise Reject('tu: steps must be a nonempty list')
    cur = set(E)
    for i, st in enumerate(steps):
        where = 'tu step %d' % i
        need_keys(st, ['gadget', 'map', 'pair'], where)
        k = st['gadget']
        if not is_int(k) or not (0 <= k < len(ctx['gadgets'])):
            raise Reject('%s: bad gadget index %r' % (where, k))
        gn, gE, (ga, gb) = ctx['gadgets'][k]
        img = check_map(st['map'], gn, gE, n, cur, where)
        pr = st['pair']
        if not isinstance(pr, list) or len(pr) != 2:
            raise Reject('%s: pair must be a list of two vertices' % where)
        p0, p1 = parse_vertex(pr[0], n, where), parse_vertex(pr[1], n, where)
        if {p0, p1} != {img[ga], img[gb]} or p0 == p1:
            raise Reject('%s: pair is not the image of the gadget distinguished pair' % where)
        pe = norm_edge(p0, p1)
        if pe in cur:
            raise Reject('%s: pair %d-%d is already an edge' % (where, p0, p1))
        cur.add(pe)
    end = cert['end']
    if not isinstance(end, dict):
        raise Reject('tu end: expected an object')
    if 'forbidden' in end:
        need_keys(end, ['forbidden', 'map'], 'tu end')
        j = end['forbidden']
        # GP-11: the list in force for B11 is all of F10 (398 graphs, JSON order, JSON labels)
        if not is_int(j) or not (0 <= j < len(ctx['forbidden'])):
            raise Reject('tu end: bad forbidden index %r' % (j,))
        fk, fE = ctx['forbidden'][j]
        check_map(end['map'], fk, fE, n, cur, 'tu end forbidden[%d]' % j)
        return ('tu chain of %d step(s) ending at F10[%d] (%d vertices; premise: %s that it is '
                'forbidden)' % (len(steps), j, fk, premise_of(j))), [], {'premise': j}
    if 'refuted' in end:
        need_keys(end, ['refuted', 'map'], 'tu end')
        tg = end['refuted']
        tn, tE = decode_g6(tg)
        check_map(end['map'], tn, tE, n, cur, 'tu end refuted %s' % tg)
        return ('tu chain of %d step(s) ending at refuted record %s' % (len(steps), tg)), [tg], {}
    raise Reject('tu end: needs forbidden or refuted')


# ---------------------------------------------------------------------------------------------
# GP-11: R-ptr (sub).  FORMAT 'Refutation certificates': exactly type, g6, map, optionally
# index.  The map sends the target H (its own canonical labels, i.e. the labels of its g6
# string) into the current graph G.  Without index, H must have an accepted refuted record in
# the same run (resolved later, with cycle detection).  With index, H must be that F10 member.
# ---------------------------------------------------------------------------------------------

def _isomorphic(n1, E1, n2, E2):
    """Exact isomorphism test by backtracking with degree refinement (small graphs only)."""
    if n1 != n2 or len(E1) != len(E2):
        return False
    adj1 = [set() for _ in range(n1)]
    adj2 = [set() for _ in range(n2)]
    for u, v in E1:
        adj1[u].add(v)
        adj1[v].add(u)
    for u, v in E2:
        adj2[u].add(v)
        adj2[v].add(u)
    if sorted(len(a) for a in adj1) != sorted(len(a) for a in adj2):
        return False
    order = sorted(range(n1), key=lambda v: -len(adj1[v]))
    img = {}
    used = set()

    def bt(k):
        if k == n1:
            return True
        v = order[k]
        for w in range(n2):
            if w in used or len(adj2[w]) != len(adj1[v]):
                continue
            if all((img[u] in adj2[w]) == (u in adj1[v]) for u in img):
                img[v] = w
                used.add(w)
                if bt(k + 1):
                    return True
                del img[v]
                used.discard(w)
        return False
    return bt(0)


def verify_sub(n, E, cert, ctx):
    keys = set(cert.keys()) if isinstance(cert, dict) else set()
    if keys == {'type', 'g6', 'map'}:
        has_index = False
    elif keys == {'type', 'g6', 'map', 'index'}:
        has_index = True
    else:
        raise Reject('sub: schema (keys %s; want type, g6, map, optional index)' % sorted(keys))
    hg = cert['g6']
    hn, hE = decode_g6(hg)
    check_map(cert['map'], hn, hE, n, E, 'sub %s' % hg)
    if has_index:
        j = cert['index']
        if not is_int(j) or not (0 <= j < len(ctx['forbidden'])):
            raise Reject('sub: bad F10 index %r' % (j,))
        fk, fE = ctx['forbidden'][j]
        # Reading: "H must equal the canonical form of that member" is checked as exact
        # isomorphism H ~ F10[j] (the property soundness needs), not by recomputing nauty's form.
        if not _isomorphic(hn, hE, fk, fE):
            raise Reject('sub: target %s is not isomorphic to F10[%d]' % (hg, j))
        return ('R-ptr: contains F10[%d] (%d vertices; premise: %s that it is forbidden)'
                % (j, fk, premise_of(j))), [], {'premise': j}
    if hg == '' or hn == 0:
        raise Reject('sub: empty target')
    return 'R-ptr: contains refuted record %s' % hg, [hg], {}


# ---------------------------------------------------------------------------------------------
# R-tree (AMP Section 4 proof trees; moves L1a, L1b, L1c, L2, L3) -- unchanged
# ---------------------------------------------------------------------------------------------

def parse_real_elem(F, x, where):
    if is_int(x) or type(x) is str:     # GP-11: a bare value is that element of Q (zero as "0")
        return F.red(fmpq_poly([parse_rat_tree(x, where)]))
    if not isinstance(x, list) or not (1 <= len(x) <= F.deg):
        raise Reject('%s: real element must be a list of 1..%d coefficients' % (where, F.deg))
    return F.red(fmpq_poly([parse_rat_tree(c, where) for c in x]))


def parse_complex_elem(F, x, where):
    if isinstance(x, list) or is_int(x) or type(x) is str:     # GP-11: bare values too
        return (parse_real_elem(F, x, where), F.zero)
    if isinstance(x, dict):
        need_keys(x, ['re', 'im'], where)
        return (parse_real_elem(F, x['re'], where), parse_real_elem(F, x['im'], where))
    raise Reject('%s: bad field element' % where)


def parse_move_edge(e, n, E, where, must_be_edge=True):
    if not isinstance(e, list) or len(e) != 2:
        raise Reject('%s: edge must be [u, v]' % where)
    u, v = parse_vertex(e[0], n, where), parse_vertex(e[1], n, where)
    if u == v:
        raise Reject('%s: degenerate pair' % where)
    if must_be_edge and norm_edge(u, v) not in E:
        raise Reject('%s: %d-%d is not an edge of the current graph' % (where, u, v))
    return u, v


def disp(F, n, u, v, coef):
    """coef * (e_u - e_v): the directed displacement f(u) - f(v) scaled by coef."""
    return unit_vec(F, n, [(u, coef), (v, F.cneg(coef))])


def vadd(F, *vs):
    out = vs[0]
    for w in vs[1:]:
        out = [F.cadd(a, b) for a, b in zip(out, w)]
    return out


def verify_tree(n, E, cert, ctx):
    need_keys(cert, ['type', 'witness'], 'tree')
    w = cert['witness']
    need_keys(w, ['field', 'tree'], 'tree witness')
    fld = w['field']
    need_keys(fld, ['interval', 'minpoly'], 'tree field')
    mp = fld['minpoly']
    if not isinstance(mp, list):
        raise Reject('tree field: minpoly must be a list of integers')
    mp = [parse_int_tree(c, 'tree field minpoly') for c in mp]     # GP-11: "-3" as well as -3
    iv = fld['interval']
    if not isinstance(iv, list) or len(iv) != 2:
        raise Reject('tree field: interval must be [lo, hi]')
    lo, hi = parse_rat_tree(iv[0], 'interval'), parse_rat_tree(iv[1], 'interval')
    F = Field([fmpq(c) for c in mp], lo, hi)
    stats = {'nodes': 0, 'leaves': {}, 'deg': F.deg}
    root_space = RowSpace(F, n, rhombus_rows(F, n, E))
    _verify_node(F, n, w['tree'], set(E), root_space, 0, stats, 'root')
    leaves = ','.join('%s:%d' % kv for kv in sorted(stats['leaves'].items()))
    return ('proof tree over field of degree %d: %d nodes, leaves %s' % (
        F.deg, stats['nodes'], leaves)), [], {'nodes': stats['nodes'], 'field_degree': F.deg}


def _verify_node(F, n, node, E, space, depth, stats, path):
    """E: current graph edge set; space: RowSpace of the linear constraints PROVED at this
    node (rhombus rows of every 4-cycle of the current graph, plus the L3 branch rows on the
    path).  Every unit-distance embedding of the input graph that reaches this node lies in
    ker(space).  The node is refuted if its move is valid and all its children are refuted."""
    if depth > MAX_TREE_DEPTH:
        raise Reject('tree: depth limit')
    stats['nodes'] += 1
    where = 'tree node %s' % path
    need_keys(node, ['A', 'children', 'edges', 'move'], where)
    # graph state at this node must be exactly the tracked graph, sorted, u < v
    ed = node['edges']
    if not isinstance(ed, list):
        raise Reject('%s: edges must be a list' % where)
    parsed = []
    for e in ed:
        if not isinstance(e, list) or len(e) != 2:
            raise Reject('%s: bad edge entry' % where)
        u, v = parse_vertex(e[0], n, where), parse_vertex(e[1], n, where)
        if not u < v:
            raise Reject('%s: edge entries must have u < v' % where)
        parsed.append((u, v))
    if parsed != sorted(E):
        raise Reject('%s: stated graph differs from the graph derived by the moves' % where)
    # constraint matrix: its row space must equal the regenerated (proved) row space
    A = node['A']
    if not isinstance(A, list):
        raise Reject('%s: A must be a list of rows' % where)
    Aspace = RowSpace(F, n)
    for ri, row in enumerate(A):
        if not isinstance(row, list) or len(row) != n:
            raise Reject('%s: A row %d must have %d entries' % (where, ri, n))
        Aspace.add([parse_complex_elem(F, x, '%s A[%d]' % (where, ri)) for x in row])
    if not space.contains_space(Aspace):
        raise Reject('%s: A contains a row that is not implied by the proved constraints' % where)
    if not Aspace.contains_space(space):
        raise Reject('%s: A row space is smaller than the regenerated constraint space '
                     '(strict equality reading)' % where)
    mv = node['move']
    if not isinstance(mv, dict) or 'kind' not in mv:
        raise Reject('%s: move must be an object with a kind' % where)
    kind = mv['kind']
    ch = node['children']
    if not isinstance(ch, list):
        raise Reject('%s: children must be a list' % where)
    one = F.c(F.one)
    if kind == 'L1a':
        need_keys(mv, ['kind', 'pair'], where + ' L1a')
        u, v = parse_move_edge(mv['pair'], n, E, where + ' L1a pair', must_be_edge=False)
        if not Aspace.contains(disp(F, n, u, v, one)):
            raise Reject('%s: L1a collision %d=%d is not forced by A' % (where, u, v))
        if ch:
            raise Reject('%s: L1a leaf must have no children' % where)
        stats['leaves']['L1a'] = stats['leaves'].get('L1a', 0) + 1
        return
    if kind in ('L1b', 'L2'):
        need_keys(mv, ['edges', 'kind', 'omega'], where + ' ' + kind)
        es = mv['edges']
        if not isinstance(es, list) or len(es) != 2:
            raise Reject('%s: %s needs two edges' % (where, kind))
        v1, v2 = parse_move_edge(es[0], n, E, where + ' first edge')
        v3, v4 = parse_move_edge(es[1], n, E, where + ' second edge', must_be_edge=(kind == 'L1b'))
        om = parse_complex_elem(F, mv['omega'], where + ' omega')
        # relation f(v1) - f(v2) = omega (f(v3) - f(v4)) for all f in ker A
        rel = vadd(F, disp(F, n, v1, v2, one), disp(F, n, v3, v4, F.cneg(om)))
        if not Aspace.contains(rel):
            raise Reject('%s: %s relation is not in the row space of A' % (where, kind))
        n2 = F.cnorm2(om)
        is_unit = F.red(n2 - F.one).is_zero()
        if kind == 'L1b':
            if is_unit:
                raise Reject('%s: L1b needs |omega| != 1' % where)
            if ch:
                raise Reject('%s: L1b leaf must have no children' % where)
            stats['leaves']['L1b'] = stats['leaves'].get('L1b', 0) + 1
            return
        if not is_unit:
            raise Reject('%s: L2 needs |omega| = 1' % where)
        ne = norm_edge(v3, v4)
        if ne in E:
            raise Reject('%s: L2 second pair %d-%d is already an edge' % (where, v3, v4))
        if len(ch) != 1:
            raise Reject('%s: L2 must have exactly one child' % where)
        E2 = set(E)
        E2.add(ne)
        sp2 = space.copy()
        for r in rhombus_rows(F, n, E2):
            sp2.add(r)
        _verify_node(F, n, ch[0], E2, sp2, depth + 1, stats, path + '.0')
        return
    if kind in ('L3', 'L1c'):
        keys = ['coefficients', 'edges', 'kind'] + (['d'] if kind == 'L3' else [])
        need_keys(mv, keys, where + ' ' + kind)
        es, cs = mv['edges'], mv['coefficients']
        if not isinstance(es, list) or len(es) != 3 or not isinstance(cs, list) or len(cs) != 3:
            raise Reject('%s: %s needs three edges and three coefficients' % (where, kind))
        (u1, w1), (u2, w2), (u3, w3) = [parse_move_edge(e, n, E, where + ' edge') for e in es]
        a, b, c = [parse_complex_elem(F, x, where + ' coefficient') for x in cs]
        if F.ciszero(a) or F.ciszero(b) or F.ciszero(c):
            raise Reject('%s: %s coefficients must all be nonzero' % (where, kind))
        rel = vadd(F, disp(F, n, u1, w1, a), disp(F, n, u2, w2, b), disp(F, n, u3, w3, c))
        if not Aspace.contains(rel):
            raise Reject('%s: %s relation is not in the row space of A' % (where, kind))
        al2, be2, ga2 = F.cnorm2(a), F.cnorm2(b), F.cnorm2(c)
        s = al2 + be2 - ga2
        D = F.red(4 * al2 * be2 - s * s)
        if kind == 'L1c':
            if F.sign(D) >= 0:
                raise Reject('%s: L1c discriminant is not strictly negative' % where)
            if ch:
                raise Reject('%s: L1c leaf must have no children' % where)
            stats['leaves']['L1c'] = stats['leaves'].get('L1c', 0) + 1
            return
        d = parse_real_elem(F, mv['d'], where + ' d')
        if not F.red(d * d - D).is_zero():
            raise Reject('%s: L3 d^2 != 4|a|^2|b|^2 - (|a|^2+|b|^2-|c|^2)^2' % where)
        if len(ch) != 2:
            raise Reject('%s: L3 must have exactly two children' % where)
        two_al2_b = F.cscale(F.red(2 * al2), b)
        for k, sgn in ((0, 1), (1, -1)):
            coef1 = F.cmul(F.c(s, sgn * d), a)  # (|a|^2+|b|^2-|c|^2 +- i d) a
            row = vadd(F, disp(F, n, u1, w1, coef1), disp(F, n, u2, w2, two_al2_b))
            spk = space.copy()
            spk.add(row)
            _verify_node(F, n, ch[k], E, spk, depth + 1, stats, path + '.%d' % k)
        return
    raise Reject('%s: unknown move kind %r' % (where, kind))


# ---------------------------------------------------------------------------------------------
# Polynomial certificates: R-null, R-real, R-null-dag, R-real-dag (mathematics unchanged)
# ---------------------------------------------------------------------------------------------

_CTX_CACHE = {}


def get_ctx(names):
    key = tuple(names)
    if key not in _CTX_CACHE:
        if len(_CTX_CACHE) > 64:
            _CTX_CACHE.clear()
        _CTX_CACHE[key] = fmpq_mpoly_ctx.get(key, 'lex')
    return _CTX_CACHE[key]


_INT_TYPE_SET = {int}


class System:
    """The regenerated polynomial system of CONTRACT 3.2 / FORMAT 'Sparse polynomials'."""

    def __init__(self, n, E, frame, sat):
        if not isinstance(frame, list) or len(frame) != 2:
            raise Reject('frame: must be [a, b]')
        a, b = parse_vertex(frame[0], n, 'frame'), parse_vertex(frame[1], n, 'frame')
        if a == b:
            raise Reject('frame: vertices must be distinct')
        if norm_edge(a, b) not in E:
            raise Reject('frame: %d-%d is not an edge' % (a, b))
        if not isinstance(sat, list):
            raise Reject('sat: must be a list')
        pairs = []
        seen = set()
        for p in sat:
            if not isinstance(p, list) or len(p) != 2:
                raise Reject('sat: entries must be [u, v]')
            u, v = parse_vertex(p[0], n, 'sat'), parse_vertex(p[1], n, 'sat')
            if not u < v:
                raise Reject('sat: pair must have u < v')
            if (u, v) in seen:
                raise Reject('sat: duplicate pair')
            seen.add((u, v))
            pairs.append((u, v))
        self.n, self.a, self.b, self.sat = n, a, b, pairs
        names = []
        vidx = {}
        for i in range(n):
            if i in (a, b):
                continue
            vidx[i] = len(names)
            names.append('x_%d' % i)
            names.append('y_%d' % i)
        for k in range(len(pairs)):
            names.append('t_%d' % k)
        self.names = names
        self.nv = len(names)
        self.ctx = ctx = get_ctx(names)
        gens = ctx.gens()
        zero, onep = ctx.constant(0), ctx.constant(1)

        def X(i):
            if i == a:
                return zero
            if i == b:
                return onep
            return gens[vidx[i]]

        def Y(i):
            if i in (a, b):
                return zero
            return gens[vidx[i] + 1]

        def d2(u, v):
            dx = X(u) - X(v)
            dy = Y(u) - Y(v)
            return dx * dx + dy * dy

        self.gens = {}
        for (u, v) in sorted(E):
            if (u, v) == norm_edge(a, b):
                continue
            self.gens['e:%d,%d' % (u, v)] = d2(u, v) - 1
        for k, (u, v) in enumerate(pairs):
            self.gens['s:%d,%d' % (u, v)] = gens[2 * (n - 2) + k] * d2(u, v) - 1

    def parse_poly(self, terms, canonical, where):
        if not isinstance(terms, list):
            raise Reject('%s: polynomial must be a list of terms' % where)
        d = {}
        prev = None
        nv = self.nv
        for t in terms:
            if type(t) is not list or len(t) != 2:
                raise Reject('%s: term must be [coefficient, exponents]' % where)
            q = parse_rat_str(t[0], where)
            e = t[1]
            if type(e) is not list or len(e) != nv:
                raise Reject('%s: exponent vector must have %d entries' % (where, nv))
            # GP-11: the same per-exponent rule as the predecessor (an int, not a bool, >= 0,
            # within the resource limit), evaluated with C-level builtins for speed
            if set(map(type, e)) != _INT_TYPE_SET:
                raise Reject('%s: bad exponent (not an integer)' % where)
            if min(e) < 0:
                raise Reject('%s: bad exponent (negative)' % where)
            if max(e) > MAX_EXPONENT:
                raise Reject('%s: exponent over resource limit' % where)
            et = tuple(e)
            if et in d:
                raise Reject('%s: duplicate monomial' % where)
            if canonical:
                if q == 0:
                    raise Reject('%s: zero coefficient in canonical sparse polynomial' % where)
                if prev is not None and not prev < et:
                    raise Reject('%s: terms not in strictly increasing lexicographic order' % where)
                prev = et
            d[et] = q
        return self.ctx.from_dict({k: v for k, v in d.items() if v != 0})


def verify_sturm(sysm, f, var):
    if type(var) is not str or var not in sysm.names:
        raise Reject('sturm: %r is not a variable of the regenerated system' % (var,))
    if f.is_zero():
        raise Reject('sturm: f is the zero polynomial')
    idx = sysm.names.index(var)
    coeffs = {}
    for exps, cf in f.to_dict().items():
        for i, e in enumerate(exps):
            if i != idx and e != 0:
                raise Reject('sturm: f involves a variable other than %s' % var)
        coeffs[exps[idx]] = fmpq(cf)
    deg = max(coeffs)
    p = fmpq_poly([coeffs.get(k, fmpq(0)) for k in range(deg + 1)])
    cnt = sturm_count_R(p)
    # second opinion, sympy exact rationals
    import sympy
    xs = sympy.Symbol('z')
    sp = sympy.Poly([sympy.Rational(int(coeffs.get(k, fmpq(0)).p), int(coeffs.get(k, fmpq(0)).q))
                     for k in range(deg, -1, -1)], xs, domain='QQ')
    cnt2 = sp.count_roots() if deg > 0 else 0
    if (cnt == 0) != (cnt2 == 0):
        raise Reject('sturm: internal disagreement between Sturm implementations (%d vs %d)'
                     % (cnt, cnt2))
    if cnt != 0:
        raise Reject('sturm: f has %d real root(s) in %s' % (cnt, var))
    return 'univariate in %s of degree %d with no real root' % (var, deg)


def verify_sos(sysm, f, sos, canonical):
    need_keys(sos, ['c', 'squares'], 'sos')
    c = parse_rat_str(sos['c'], 'sos c')
    if not c > 0:
        raise Reject('sos: c must be strictly positive')
    sq = sos['squares']
    if not isinstance(sq, list):
        raise Reject('sos: squares must be a list')
    total = sysm.ctx.constant(c)
    for i, ent in enumerate(sq):
        if not isinstance(ent, list) or len(ent) != 2:
            raise Reject('sos: square %d must be [w, q]' % i)
        wgt = parse_rat_str(ent[0], 'sos weight')
        if not wgt > 0:
            raise Reject('sos: weight %d must be strictly positive' % i)
        q = sysm.parse_poly(ent[1], canonical, 'sos square %d' % i)
        total = total + q * q * wgt
    if total != f:
        raise Reject('sos: c + sum w q^2 != f')
    return 'f = c + sum of %d weighted squares, c > 0' % len(sq)


def verify_poly_cert(n, E, cert, kind, ctx):
    t = cert
    if kind == 'null':
        base, opt = ['type', 'frame', 'sat', 'cofactors'], ['system']
    elif kind == 'real':
        base, opt = ['type', 'frame', 'sat', 'cofactors', 'f'], ['system']
    elif kind == 'null-dag':
        base, opt = ['type', 'frame', 'sat', 'rows'], []
    else:
        base, opt = ['type', 'frame', 'sat', 'rows', 'f'], []
    keys = set(t.keys())
    tail = keys - set(base) - set(opt)
    if kind in ('real', 'real-dag'):
        ns = ('sturm' in keys) + ('sos' in keys)
        if ns != 1:
            raise Reject('%s: needs exactly one of sturm or sos' % kind)
        tail -= {'sturm', 'sos'}
    if tail or not set(base) <= keys:
        raise Reject('%s: schema (extra %s, missing %s)' % (kind, sorted(tail),
                                                             sorted(set(base) - keys)))
    sysm = System(n, E, t['frame'], t['sat'])
    canonical = kind.endswith('-dag')
    if 'system' in t:
        stated = t['system']
        if not isinstance(stated, dict) or set(stated.keys()) != set(sysm.gens.keys()):
            raise Reject('system: stated generator keys differ from the regenerated system')
        for k, g in sysm.gens.items():
            if sysm.parse_poly(stated[k], False, 'system ' + k) != g:
                raise Reject('system: stated generator %s differs from the regenerated one' % k)
    nterms = 0
    if kind in ('null', 'real'):
        cof = t['cofactors']
        if not isinstance(cof, dict):
            raise Reject('cofactors: must be an object')
        total = sysm.ctx.constant(0)
        for k in sorted(cof.keys()):
            if k not in sysm.gens:
                raise Reject('cofactors: unknown generator key %r' % (k,))
            nterms += len(cof[k]) if isinstance(cof[k], list) else 0
            total = total + sysm.parse_poly(cof[k], False, 'cofactor ' + k) * sysm.gens[k]
        detail = '%d cofactors' % len(cof)
        nrows = 0
    else:
        rows = t['rows']
        if not isinstance(rows, list) or not rows:
            raise Reject('dag_rows: rows must be a nonempty list')
        if len(rows) > MAX_DAG_ROWS:
            raise Reject('dag_row_limit: more than %d rows' % MAX_DAG_ROWS)
        aux = []
        for k, row in enumerate(rows):
            need_keys(row, ['poly', 'cofactors'], 'dag row %d' % k)
            P = sysm.parse_poly(row['poly'], True, 'dag row %d poly' % k)
            cof = row['cofactors']
            if not isinstance(cof, dict):
                raise Reject('dag row %d: cofactors must be an object' % k)
            S = sysm.ctx.constant(0)
            for key in sorted(cof.keys()):
                if key in sysm.gens:
                    src = sysm.gens[key]
                else:
                    m = re.fullmatch(r'aux:(0|[1-9][0-9]*)', key)
                    if m is None:
                        raise Reject('dag_source: row %d names unknown source %r' % (k, key))
                    j = int(m.group(1))
                    if j >= k:
                        raise Reject('dag_reference_order: row %d references aux:%d' % (k, j))
                    src = aux[j]
                nterms += len(cof[key]) if isinstance(cof[key], list) else 0
                S = S + sysm.parse_poly(cof[key], True, 'dag row %d cofactor %s' % (k, key)) * src
            if S != P:
                raise Reject('dag_row_identity: row %d poly != sum(cofactor * source)' % k)
            aux.append(P)
            row.clear()             # GP-11: release the row's JSON once its identity passed
        total = aux[-1]
        detail = '%d rows' % len(rows)
        nrows = len(rows)
        del aux
    stats = {'rows': nrows, 'cofactor_terms': nterms, 'sat': len(sysm.sat), 'vars': sysm.nv}
    if kind in ('null', 'null-dag'):
        if total != 1:
            raise Reject('%s: sum(cofactor * generator) != 1' % kind)
        return ('Nullstellensatz identity = 1 (%s; frame %d,%d; %d sat pairs; %d vars)'
                % (detail, sysm.a, sysm.b, len(sysm.sat), sysm.nv)), [], stats
    f = sysm.parse_poly(t['f'], canonical, 'f')
    if total != f:
        raise Reject('%s: sum(cofactor * generator) != f' % kind)
    if 'sturm' in t:
        why = verify_sturm(sysm, f, t['sturm'])
    else:
        why = verify_sos(sysm, f, t['sos'], canonical)
    return ('identity = f (%s; frame %d,%d; %d sat pairs); %s'
            % (detail, sysm.a, sysm.b, len(sysm.sat), why)), [], stats


# ---------------------------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------------------------

def verify_record_obj(rec, ctx):
    """Verify one parsed record.  Returns (g6, type, reason, deps, stats); raises
    Reject/Unsupported."""
    need_keys(rec, ['g6', 'verdict', 'cert'], 'record')
    g6 = rec['g6']
    n, E = decode_g6(g6)
    # GP-11: every B11 record has exactly 11 vertices (FORMAT: the order check applies to every
    # record).  ctx['order'] = None disables this, for synthetic controls on small graphs.
    if ctx.get('order') is not None and n != ctx['order']:
        raise Reject('order: graph has %d vertices, a B11 record has %d' % (n, ctx['order']))
    cert = rec['cert']
    if not isinstance(cert, dict):
        raise Reject('cert: expected an object')
    typ = cert.get('type')
    if type(typ) is not str:
        raise Reject('cert: missing type')
    if rec['verdict'] != 'refuted':
        raise Reject('record verdict is %r, not refuted' % (rec['verdict'],))
    if typ == 'tu':
        reason, deps, stats = verify_tu(n, E, cert, ctx)
    elif typ == 'tree':
        reason, deps, stats = verify_tree(n, E, cert, ctx)
    elif typ in ('null', 'real', 'null-dag', 'real-dag'):
        reason, deps, stats = verify_poly_cert(n, E, cert, typ, ctx)
    elif typ == 'sub':
        reason, deps, stats = verify_sub(n, E, cert, ctx)       # GP-11: R-ptr implemented
    else:
        raise Reject('unknown refutation certificate type %r' % (typ,))
    return g6, typ, reason, deps, stats


def verify_line(line, ctx):
    """Returns dict with g6, type, own (ACCEPT/REJECT/UNSUPPORTED), reason, deps, seconds."""
    t0 = time.perf_counter()
    g6, typ, deps, stats = None, None, [], {}
    try:
        rec = strict_loads(line)
        if isinstance(rec, dict):
            g6 = rec.get('g6') if type(rec.get('g6')) is str else None
            c = rec.get('cert')
            typ = c.get('type') if isinstance(c, dict) and type(c.get('type')) is str else None
        g6, typ, reason, deps, stats = verify_record_obj(rec, ctx)
        own = ACCEPT
    except Reject as exc:
        own, reason = REJECT, str(exc.args[0])
    except Unsupported as exc:
        own, reason = UNSUPPORTED, str(exc.args[0])
    except MemoryError:
        own, reason = UNSUPPORTED, 'resource: out of memory'
    except RecursionError:
        own, reason = UNSUPPORTED, 'resource: recursion limit'
    except Exception as exc:  # a bug of this verifier, never a verdict on the certificate
        own, reason = UNSUPPORTED, 'internal-error: %s: %s' % (type(exc).__name__, str(exc)[:200])
    return {'g6': g6, 'type': typ, 'own': own, 'reason': reason[:600], 'deps': deps,
            'stats': stats, 'seconds': round(time.perf_counter() - t0, 3)}


# ---------------------------------------------------------------------------------------------
# Pointer resolution (GP-11: iterative, works across shards)
# ---------------------------------------------------------------------------------------------

def resolve(results):
    """A record whose certificate depends on other records (sub; tu ending at a refuted graph)
    is accepted only if every dependency is an ACCEPTED refuted record of this run, with no
    cycles.  Sets r['verdict'] and r['reason'] on every result."""
    by_g6 = {}
    dup = set()
    for r in results:
        if r['g6'] is None:
            continue
        if r['g6'] in by_g6:
            dup.add(r['g6'])
        by_g6.setdefault(r['g6'], r)
    final = {}
    for root in results:
        if id(root) in final:
            continue
        path = [root]
        pos = {id(root): 0}
        onstack = {id(root)}
        while path:
            r = path[-1]
            rid = id(r)
            verdict = None
            if r['own'] != ACCEPT:
                verdict = (r['own'], r['reason'])
            elif r['g6'] in dup:
                verdict = (REJECT, 'duplicate record for this graph6 in the run')
            else:
                i = pos[rid]
                deps = r['deps']
                if i < len(deps):
                    d = deps[i]
                    tgt = by_g6.get(d)
                    if tgt is None:
                        verdict = (REJECT, 'pointer target %s has no refuted record in this run' % d)
                    elif id(tgt) in final:
                        v, why = final[id(tgt)]
                        if v != ACCEPT:
                            verdict = (REJECT, 'pointer target %s is not accepted (%s: %s)'
                                       % (d, v, why[:160]))
                        else:
                            pos[rid] = i + 1
                            continue
                    elif id(tgt) in onstack:
                        verdict = (REJECT, 'pointer cycle through %s' % d)
                    else:
                        path.append(tgt)
                        pos[id(tgt)] = 0
                        onstack.add(id(tgt))
                        continue
                else:
                    verdict = (ACCEPT, r['reason'])
            final[rid] = verdict
            onstack.discard(rid)
            path.pop()
    for r in results:
        r['verdict'], r['reason'] = final[id(r)]
    return results


def chain_premises(results):
    """For each accepted record, the F10 premises its proof uses, following record pointers."""
    by_g6 = {r['g6']: r for r in results if r['g6'] is not None}
    memo = {}

    def prem(r, seen):
        if r['g6'] in memo:
            return memo[r['g6']]
        out = set()
        if r['stats'].get('premise') is not None:
            out.add(r['stats']['premise'])
        for d in r['deps']:
            t = by_g6.get(d)
            if t is not None and d not in seen:
                out |= prem(t, seen | {r['g6']})
        memo[r['g6']] = out
        return out
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    return {r['g6']: sorted(prem(r, frozenset())) for r in results
            if r['verdict'] == ACCEPT and r['g6'] is not None}


# ---------------------------------------------------------------------------------------------
# scan: one streaming pass, index of the refuted records
# ---------------------------------------------------------------------------------------------

TAILS = {b'"verdict":"embedded"}': 'embedded', b'"verdict":"refuted"}': 'refuted',
         b'"verdict":"unknown"}': 'unknown'}


def _last_g6(body):
    """The record-level g6 of a sorted-key compact line (the last "g6" key), JSON-unescaped."""
    k = body.rfind(b'"g6":"')
    if k < 0:
        return None
    e = k + 6
    while e < len(body) and body[e] != 34:
        e += 2 if body[e] == 92 else 1
    try:
        return json.loads(body[k + 5:e + 1])
    except Exception:
        return None


def cmd_scan(records, index_path):
    t0 = time.time()
    sha = hashlib.sha256()
    counts = {}
    seen = {}
    dups = []
    n_ref = 0
    offset = 0
    with open(records, 'rb', buffering=1 << 22) as fh, open(index_path + '.tmp', 'w') as fo:
        for lineno, line in enumerate(fh, 1):
            sha.update(line)
            length = len(line)
            body = line[:-1] if line.endswith(b'\n') else line
            verdict = None
            for tail, v in TAILS.items():
                if body.endswith(tail):
                    verdict = v
                    break
            rec = None
            if verdict != 'embedded' and verdict != 'unknown':
                try:
                    rec = json.loads(body)
                    v2 = rec.get('verdict') if isinstance(rec, dict) else None
                    verdict = v2 if isinstance(v2, str) else 'malformed'
                except Exception:
                    # an unparsable line goes into the index so that check reports it (REJECT)
                    verdict = 'refuted' if verdict == 'refuted' else 'malformed'
            counts[verdict] = counts.get(verdict, 0) + 1
            if rec is not None and isinstance(rec, dict):
                g6 = rec.get('g6') if type(rec.get('g6')) is str else None
            else:
                g6 = _last_g6(body)
            if g6 is not None:
                if g6 in seen:
                    dups.append({'g6': g6, 'lines': [seen[g6], lineno]})
                else:
                    seen[g6] = lineno
            if verdict in ('refuted', 'malformed'):
                ent = {'i': n_ref, 'line': lineno, 'offset': offset, 'length': length,
                       'g6': g6, 'type': None, 'ptr': None}
                if isinstance(rec, dict) and isinstance(rec.get('cert'), dict):
                    c = rec['cert']
                    ent['type'] = c.get('type') if isinstance(c.get('type'), str) else None
                    if ent['type'] == 'sub' and 'index' not in c:
                        ent['ptr'] = c.get('g6')
                    elif ent['type'] == 'tu' and isinstance(c.get('end'), dict):
                        ent['ptr'] = c['end'].get('refuted')
                fo.write(json.dumps(ent) + '\n')
                n_ref += 1
            del rec
            offset += length
            if lineno % 100000 == 0:
                sys.stderr.write('scan: %d lines, %.2f GB, %.0f s, refuted %d\n'
                                 % (lineno, offset / 1e9, time.time() - t0, n_ref))
    os.replace(index_path + '.tmp', index_path)
    meta = {'records': os.path.abspath(records), 'bytes': offset, 'sha256': sha.hexdigest(),
            'lines': sum(counts.values()), 'verdicts': counts, 'refuted_indexed': n_ref,
            'duplicate_g6': len(dups), 'duplicates': dups[:20],
            'seconds': round(time.time() - t0, 1)}
    with open(index_path + '.meta.json', 'w') as fo:
        json.dump(meta, fo, indent=1)
    sys.stderr.write('scan: %s\n' % json.dumps({k: meta[k] for k in (
        'lines', 'verdicts', 'refuted_indexed', 'duplicate_g6', 'seconds')}))
    return meta


def load_index(index_path):
    with open(index_path) as fh:
        return [json.loads(x) for x in fh if x.strip()]


# ---------------------------------------------------------------------------------------------
# check: verify a shard of the refuted records, one forked process per record
# ---------------------------------------------------------------------------------------------

def shard_of(index, shard, nshards):
    """Deal records to shards in snake order of decreasing size, so each shard carries similar
    bytes; deterministic from the index alone."""
    order = sorted(index, key=lambda e: (-e['length'], e['i']))
    mine = []
    for pos, e in enumerate(order):
        rnd, k = divmod(pos, nshards)
        s = k if rnd % 2 == 0 else nshards - 1 - k
        if s == shard:
            mine.append(e)
    return mine


def _child(records, ent, ctx, mem_bytes, tmp_path):
    """Runs in a forked child: verify one record, write the result JSON, exit."""
    try:
        if mem_bytes:
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            if hard != resource.RLIM_INFINITY:
                mem_bytes = min(mem_bytes, hard)      # cannot raise an inherited hard limit
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        with open(records, 'rb') as fh:
            fh.seek(ent['offset'])
            line = fh.read(ent['length'])
        if len(line) != ent['length'] or not line.endswith(b'\n'):
            r = {'g6': ent['g6'], 'type': ent['type'], 'own': REJECT, 'deps': [], 'stats': {},
                 'reason': 'record line %d is truncated or lacks its newline' % ent['line'],
                 'seconds': 0.0}
        else:
            r = verify_line(line, ctx)
            del line
            if r['g6'] != ent['g6'] and r['own'] == ACCEPT:
                r['own'], r['reason'] = REJECT, 'index mismatch: line %d holds %r, index says %r' % (
                    ent['line'], r['g6'], ent['g6'])
        with open(tmp_path + '.w', 'w') as fo:
            json.dump(r, fo)
        os.replace(tmp_path + '.w', tmp_path)
        os._exit(0)
    except BaseException:
        os._exit(3)


def cmd_check(records, index, out_path, shard=0, nshards=1, jobs=1, timeout=7200,
              mem_gb=8.0, select=None, order=GP11_ORDER, data_dir=DEFAULT_DATA, quiet=False,
              index_meta=None):
    ctx = load_context(data_dir, order)
    import sympy  # noqa: F401  (imported once here so each forked child has it)
    if index_meta is not None and os.path.getsize(records) != index_meta.get('bytes'):
        raise SystemExit('check: %s has %d bytes but the index was built from %s bytes; rescan'
                         % (records, os.path.getsize(records), index_meta.get('bytes')))
    mine = shard_of(index, shard, nshards)
    if select is not None:
        mine = [e for e in mine if e['g6'] in select or e['i'] in select]
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for x in fh:
                try:
                    done.add(json.loads(x)['i'])
                except Exception:
                    pass
    pending = sorted((e for e in mine if e['i'] not in done), key=lambda e: (-e['length'], e['i']))
    tmpdir = out_path + '.tmp.d'
    os.makedirs(tmpdir, exist_ok=True)
    base_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mem_bytes = int(mem_gb * (1 << 30)) if mem_gb else 0
    sys.stderr.write('check: shard %d/%d: %d records (%d already done), jobs %d, verifier rss '
                     'before fork %.0f MB\n' % (shard, nshards, len(mine), len(done), jobs,
                                                base_rss / 1024))
    active = {}
    t_start = time.time()
    finished = 0
    with open(out_path, 'a') as fo:
        while pending or active:
            while pending and len(active) < jobs:
                ent = pending.pop(0)
                tmp_path = os.path.join(tmpdir, '%d.json' % ent['i'])
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                sys.stdout.flush()
                sys.stderr.flush()
                pid = os.fork()
                if pid == 0:
                    signal.signal(signal.SIGINT, signal.SIG_DFL)
                    _child(records, ent, ctx, mem_bytes, tmp_path)
                active[pid] = (ent, time.time(), tmp_path)
            pid, status, ru = os.wait4(-1, os.WNOHANG)
            if pid == 0:
                now = time.time()
                for p, (ent, st, _tp) in list(active.items()):
                    if timeout and now - st > timeout:
                        try:
                            os.kill(p, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                time.sleep(0.02)
                continue
            if pid not in active:
                continue
            ent, st, tmp_path = active.pop(pid)
            wall = time.time() - st
            r = None
            if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0 and os.path.exists(tmp_path):
                with open(tmp_path) as fh:
                    r = json.load(fh)
                os.unlink(tmp_path)
            if r is None:
                if os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL and timeout \
                        and wall >= timeout:
                    why = 'resource: timeout after %.0f s' % wall
                elif os.WIFSIGNALED(status):
                    why = 'resource: verifier process died with signal %d (memory limit %s GB?)' % (
                        os.WTERMSIG(status), mem_gb)
                else:
                    why = 'internal-error: verifier process exit status %d' % os.WEXITSTATUS(status)
                r = {'g6': ent['g6'], 'type': ent['type'], 'own': UNSUPPORTED, 'reason': why,
                     'deps': [], 'stats': {}, 'seconds': round(wall, 3)}
            r.update({'i': ent['i'], 'line': ent['line'], 'bytes': ent['length'],
                      'wall_seconds': round(wall, 3),
                      'cpu_seconds': round(ru.ru_utime + ru.ru_stime, 3),
                      'peak_rss_mb': round(ru.ru_maxrss / 1024, 1),
                      'base_rss_mb': round(base_rss / 1024, 1)})
            fo.write(json.dumps(r) + '\n')
            fo.flush()
            finished += 1
            if not quiet:
                sys.stderr.write('%5d %-12s %-9s %-11s %8.2fs %7.0fMB %9d B %s\n' % (
                    ent['i'], r['g6'], r['type'], r['own'], r['wall_seconds'], r['peak_rss_mb'],
                    ent['length'], r['reason'][:90]))
                sys.stderr.flush()
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass
    sys.stderr.write('check: shard %d/%d finished %d records in %.1f s\n'
                     % (shard, nshards, finished, time.time() - t_start))


# ---------------------------------------------------------------------------------------------
# resolve: merge parts, coverage, pointers, summary
# ---------------------------------------------------------------------------------------------

def _source_sha256():
    with open(os.path.abspath(__file__), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def cmd_resolve(index, parts, out_path, summary_path, sample=False, data_dir=DEFAULT_DATA,
                meta=None):
    results = {}
    dup_results = 0
    for p in parts:
        with open(p) as fh:
            for x in fh:
                if not x.strip():
                    continue
                r = json.loads(x)
                if r['i'] in results:
                    dup_results += 1
                results[r['i']] = r
    by_i = {e['i']: e for e in index}
    missing = sorted(set(by_i) - set(results))
    extra = sorted(set(results) - set(by_i))
    res = [results[i] for i in sorted(results) if i in by_i]
    resolve(res)
    prem = chain_premises(res)
    counts = {}
    for r in res:
        key = '%s/%s' % (r['type'], r['verdict'])
        counts[key] = counts.get(key, 0) + 1
    totals = {v: sum(1 for r in res if r['verdict'] == v) for v in (ACCEPT, REJECT, UNSUPPORTED)}
    not_accepted = [{'i': r['i'], 'line': r['line'], 'g6': r['g6'], 'type': r['type'],
                     'verdict': r['verdict'], 'reason': r['reason']}
                    for r in res if r['verdict'] != ACCEPT]
    direct = {}
    for r in res:
        j = r.get('stats', {}).get('premise')
        if j is not None and r['verdict'] == ACCEPT:
            direct[premise_of(j)] = direct.get(premise_of(j), 0) + 1
    via = {'none (self-contained)': 0, 'GP theorem only': 0, 'uses GP-10 result': 0}
    for g, ps in prem.items():
        if not ps:
            via['none (self-contained)'] += 1
        elif all(j < 74 for j in ps):
            via['GP theorem only'] += 1
        else:
            via['uses GP-10 result'] += 1
    with open(out_path + '.tmp', 'w') as fo:
        for r in res:
            fo.write(json.dumps({'i': r['i'], 'line': r['line'], 'g6': r['g6'], 'type': r['type'],
                                 'verdict': r['verdict'], 'reason': r['reason'],
                                 'deps': r['deps'], 'f10_premises': prem.get(r['g6'], []),
                                 'stats': r.get('stats', {}), 'bytes': r.get('bytes'),
                                 'wall_seconds': r.get('wall_seconds'),
                                 'cpu_seconds': r.get('cpu_seconds'),
                                 'peak_rss_mb': r.get('peak_rss_mb')}) + '\n')
    os.replace(out_path + '.tmp', out_path)
    walls = [r.get('wall_seconds') or 0 for r in res]
    cpus = [r.get('cpu_seconds') or 0 for r in res]
    rss = [r.get('peak_rss_mb') or 0 for r in res]
    by_type_time = {}
    for r in res:
        s = by_type_time.setdefault(r['type'], {'n': 0, 'cpu_seconds': 0.0, 'max_wall': 0.0,
                                                'max_rss_mb': 0.0, 'bytes': 0})
        s['n'] += 1
        s['cpu_seconds'] = round(s['cpu_seconds'] + (r.get('cpu_seconds') or 0), 3)
        s['max_wall'] = max(s['max_wall'], r.get('wall_seconds') or 0)
        s['max_rss_mb'] = max(s['max_rss_mb'], r.get('peak_rss_mb') or 0)
        s['bytes'] += r.get('bytes') or 0
    summary = {
        'verifier': os.path.abspath(__file__), 'verifier_sha256': _source_sha256(),
        'flint': flint.__version__, 'python': sys.version.split()[0],
        'SYMPY_GROUND_TYPES': os.environ.get('SYMPY_GROUND_TYPES'),
        'records_meta': meta,
        'mode': 'sample (coverage not required)' if sample else 'full',
        'indexed_refuted': len(index), 'results': len(res), 'missing': len(missing),
        'missing_first': missing[:20], 'extra_results': len(extra), 'duplicate_results': dup_results,
        'coverage_complete': (not missing and not extra),
        'totals': totals, 'by_type_and_verdict': dict(sorted(counts.items())),
        'not_accepted': not_accepted,
        'direct_F10_premises': direct, 'accepted_by_premise_chain': via,
        'cpu_seconds_total': round(sum(cpus), 1), 'wall_seconds_sum': round(sum(walls), 1),
        'max_wall_seconds': max(walls) if walls else 0, 'max_peak_rss_mb': max(rss) if rss else 0,
        'by_type_time': by_type_time,
        'slowest_10': [{'g6': r['g6'], 'type': r['type'], 'bytes': r.get('bytes'),
                        'wall_seconds': r.get('wall_seconds'), 'peak_rss_mb': r.get('peak_rss_mb')}
                       for r in sorted(res, key=lambda r: -(r.get('wall_seconds') or 0))[:10]],
        'largest_rss_10': [{'g6': r['g6'], 'type': r['type'], 'bytes': r.get('bytes'),
                            'wall_seconds': r.get('wall_seconds'),
                            'peak_rss_mb': r.get('peak_rss_mb')}
                           for r in sorted(res, key=lambda r: -(r.get('peak_rss_mb') or 0))[:10]],
    }
    ok = (totals[REJECT] == 0 and totals[UNSUPPORTED] == 0 and
          (sample or summary['coverage_complete']))
    summary['status'] = ('ALL %d ACCEPT' % len(res)) if ok else 'NOT ALL ACCEPT (see not_accepted)'
    with open(summary_path, 'w') as fo:
        json.dump(summary, fo, indent=1)
    sys.stderr.write('resolve: %s\n' % json.dumps({k: summary[k] for k in (
        'mode', 'indexed_refuted', 'results', 'missing', 'totals', 'by_type_and_verdict',
        'cpu_seconds_total', 'max_wall_seconds', 'max_peak_rss_mb', 'status')}))
    return summary


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def _shard_arg(s):
    m = re.fullmatch(r'(\d+)/(\d+)', s)
    if not m or not (0 <= int(m.group(1)) < int(m.group(2))):
        raise argparse.ArgumentTypeError('--shard wants i/n with 0 <= i < n')
    return int(m.group(1)), int(m.group(2))


def _read_select(path):
    sel = set()
    with open(path) as fh:
        for x in fh:
            x = x.rstrip('\n')
            if not x:
                continue
            if x.startswith('{'):
                o = json.loads(x)
                sel.add(o['g6'] if 'g6' in o else o['i'])
            else:
                sel.add(x)
    return sel


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('scan')
    a.add_argument('records')
    a.add_argument('--index', required=True)
    c = sp.add_parser('check')
    c.add_argument('records')
    c.add_argument('--index', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--shard', type=_shard_arg, default=(0, 1))
    c.add_argument('--jobs', type=int, default=1)
    c.add_argument('--timeout', type=float, default=7200, help='seconds per record (0 = none)')
    c.add_argument('--mem-gb', type=float, default=8.0, help='address-space limit per record')
    c.add_argument('--select', help='file of g6 strings (one per line) to check')
    c.add_argument('--order', type=int, default=GP11_ORDER)
    c.add_argument('--data', default=DEFAULT_DATA)
    r = sp.add_parser('resolve')
    r.add_argument('parts', nargs='+')
    r.add_argument('--index', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--summary', required=True)
    r.add_argument('--sample', action='store_true')
    u = sp.add_parser('run')
    u.add_argument('records')
    u.add_argument('--out', required=True)
    u.add_argument('--summary', required=True)
    u.add_argument('--jobs', type=int, default=1)
    u.add_argument('--timeout', type=float, default=7200)
    u.add_argument('--mem-gb', type=float, default=8.0)
    u.add_argument('--order', type=int, default=GP11_ORDER)
    u.add_argument('--data', default=DEFAULT_DATA)
    args = ap.parse_args(argv[1:])
    if args.cmd == 'scan':
        cmd_scan(args.records, args.index)
        return 0
    if args.cmd == 'check':
        index = load_index(args.index)
        sel = _read_select(args.select) if args.select else None
        meta = None
        if os.path.exists(args.index + '.meta.json'):
            with open(args.index + '.meta.json') as fh:
                meta = json.load(fh)
        cmd_check(args.records, index, args.out, args.shard[0], args.shard[1], args.jobs,
                  args.timeout, args.mem_gb, sel, args.order, args.data, index_meta=meta)
        return 0
    if args.cmd == 'resolve':
        index = load_index(args.index)
        meta = None
        if os.path.exists(args.index + '.meta.json'):
            with open(args.index + '.meta.json') as fh:
                meta = json.load(fh)
        s = cmd_resolve(index, args.parts, args.out, args.summary, args.sample, meta=meta)
        return 0 if s['status'].startswith('ALL') else 1
    if args.cmd == 'run':
        base = os.path.splitext(args.out)[0]
        idx = base + '.index.jsonl'
        part = base + '.part.jsonl'
        meta = cmd_scan(args.records, idx)
        index = load_index(idx)
        cmd_check(args.records, index, part, 0, 1, args.jobs, args.timeout, args.mem_gb, None,
                  args.order, args.data, index_meta=meta)
        s = cmd_resolve(index, [part], args.out, args.summary, False, meta=meta)
        return 0 if s['status'].startswith('ALL') else 1
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
