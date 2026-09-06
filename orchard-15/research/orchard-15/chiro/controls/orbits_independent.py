#!/usr/bin/env python3
"""orbits_independent.py -- from-scratch control for the (15,32) cube split.

Written 2026-09-05 for the AUDIT-15-32.md ledger.  The referee's objection was
that cnfcheck.py's "independent recomputation" imports exist.py's own group and
cube code, so a bug in the orbit/stabiliser code would be reproduced by the check.
This script therefore imports NOTHING from exist.py, chirosat.py or cnfcheck.py
and copies none of their group code: everything below is rebuilt from the
combinatorial definitions in REPORT-EXIST.md (Lemmas 6, 7, 7') using only the
standard library (itertools, json, glob, ...).

Setting, (v,b) = (15,32): points 0..14; row 0 is {0,1,2},{0,3,4},...,{0,13,14};
point 1 is full, so besides {0,1,2} it lies on six blocks {1,a,b}, a,b in 3..14,
whose pairs {a,b} form a perfect matching of {3..14} avoiding the six row-0 pairs.
G1 = permutations fixing 0,1,2 and preserving row 0 = (Z2 wr S6), order 46080.

Recomputed (each printed next to its expected value):
  (a) number of row-1 configurations: 6040 (brute force AND inclusion-exclusion);
  (b) G1-orbits: sizes 120, 1440, 640, 3840, stabilisers 384, 32, 72, 12, and the
      cycle-type invariant (half-lengths of the cycles of M0 u M1) of each orbit,
      with the per-type counts as a second, group-free route to the orbit sizes;
  (c) the lexicographically least representative of each orbit, compared with
      the representatives exist.py wrote to scratch/*/cubes-15-32-depth1.jsonl;
  (d) Lemma 7' depth-2 split of the size-3840 orbit ("cube 3"): G2 = Stab_G1(c1)
      (order 12) acting on every row of point 2; expected 5393 children with
      child-stabiliser orders {1: 4638, 2: 674, 3: 2, 4: 64, 6: 9, 12: 6}; the
      orbit count is also recomputed by Burnside's lemma.

Orbits are computed by applying EVERY element of the group to the orbit's
minimum (not by generator closure), so no union-find or generator code is
trusted; disjointness, coverage and the orbit-stabiliser identity are asserted.

Negative controls (the check must not be able to pass vacuously):
  * (b) with G1 minus the within-pair swaps (order 720) must give different sizes;
  * (a) without the row-0 exclusion must give 11!! = 10395, not 6040;
  * (d) with a proper subgroup of G2 must give a different child count;
  * (d) with the stabiliser of the WRONG cube must trip the closure check.

Exit status 0 with final line "ORBITS_INDEPENDENT PASS" iff every recomputed
number equals its expected value and every negative control differs; otherwise
exit status 1 with "ORBITS_INDEPENDENT FAIL <what differs>".
"""
import glob
import itertools
import json
import os
import random
import re
import sys
import time
from collections import Counter

T0 = time.time()

# ----------------------------------------------------------------------------
# The setting
# ----------------------------------------------------------------------------
V, B = 15, 32
E = V * (V - 1) // 2 - 3 * B          # leave edges: 105 - 96 = 9
P = (V - 1) % 2                       # parity / minimum leave degree: 0
ROW0_BLOCKS = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (0, 7, 8), (0, 9, 10), (0, 11, 12), (0, 13, 14)]
M0 = [(3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14)]   # row-0 pairs on {3..14}
M0_SET = frozenset(M0)
ROW_PTS = tuple(range(3, V))          # 3..14

EXPECTED = {
    'row1_configs': 6040,
    'G1_order': 2 ** 6 * 720,                          # 46080
    'orbits': {                                        # size -> (stabiliser order, cycle type)
        120: (384, (2, 2, 2)),
        1440: (32, (4, 2)),
        640: (72, (3, 3)),
        3840: (12, (6,)),
    },
    'exist_cubes': {                                   # AUDIT-15-32.md ledger: cube -> (orbit, stabiliser)
        'cube000': (120, 384), 'cube001': (1440, 32), 'cube002': (640, 72), 'cube003': (3840, 12),
    },
    'depth2_children': 5393,
    'depth2_stab': {1: 4638, 2: 674, 3: 2, 4: 64, 6: 9, 12: 6},
}

# exist.py's depth-1 representatives, as read from scratch/regen-c{0,1,2,3}/
# cubes-15-32-depth1.jsonl (field "cube"[0]["blocks"], point 1 dropped) on
# 2026-09-05.  Used only if those gitignored files are not present.
FALLBACK_EXIST_REPS = {
    'cube000': [(3, 5), (4, 6), (7, 9), (8, 10), (11, 13), (12, 14)],
    'cube001': [(3, 5), (4, 6), (7, 9), (8, 11), (10, 13), (12, 14)],
    'cube002': [(3, 5), (4, 7), (6, 8), (9, 11), (10, 13), (12, 14)],
    'cube003': [(3, 5), (4, 7), (6, 9), (8, 11), (10, 13), (12, 14)],
}

# ----------------------------------------------------------------------------
# Bookkeeping
# ----------------------------------------------------------------------------
RESULTS = []      # (label, got, expected, ok)


def check(label, got, expected):
    ok = (got == expected)
    RESULTS.append((label, got, expected, ok))
    print(f"  [{'ok' if ok else 'MISMATCH'}] {label}: recomputed {got!r}  expected {expected!r}")
    return ok


def check_differs(label, got, must_differ_from):
    ok = (got != must_differ_from)
    RESULTS.append((label, got, f"anything but {must_differ_from!r}", ok))
    print(f"  [{'ok' if ok else 'MISMATCH'}] {label}: got {got!r}  must differ from {must_differ_from!r}"
          f"  -> {'differs' if ok else 'SAME (control failed to go red)'}")
    return ok


def key(conf):
    """Canonical (lexicographic) key of a configuration = a set of pairs."""
    return tuple(sorted(conf))


def fmt(conf):
    return '[' + ', '.join(f'{{{a},{b}}}' for a, b in sorted(conf)) + ']'


def act(g, conf):
    """Image of a set of pairs under a point permutation g (g[i] = image of i)."""
    out = []
    for a, b in conf:
        x, y = g[a], g[b]
        out.append((x, y) if x < y else (y, x))
    return frozenset(out)


def compose(g, h):
    """(g o h)[i] = g[h[i]]."""
    return tuple(g[h[i]] for i in range(V))


# ----------------------------------------------------------------------------
# (a) row-1 configurations
# ----------------------------------------------------------------------------
def perfect_matchings(points, forbidden):
    """All perfect matchings of `points` using no pair in `forbidden`.
    The least remaining point is paired with every admissible remaining point."""
    def rec(remaining):
        if not remaining:
            yield ()
            return
        a = remaining[0]
        for i in range(1, len(remaining)):
            b = remaining[i]
            if (a, b) in forbidden:
                continue
            for m in rec(remaining[1:i] + remaining[i + 1:]):
                yield ((a, b),) + m
    for m in rec(tuple(points)):
        yield frozenset(m)


def double_factorial(n):
    return 1 if n <= 0 else n * double_factorial(n - 2)


def comb(n, k):
    from math import comb as c
    return c(n, k)


print("=" * 78)
print(f"(a) row-1 configurations for (v,b)=({V},{B}): perfect matchings of {{3..14}} avoiding row-0 pairs")
print("=" * 78)
row1 = list(perfect_matchings(ROW_PTS, M0_SET))
row1_set = set(row1)
assert len(row1_set) == len(row1), "enumeration produced a duplicate"
# sanity: every configuration really is a perfect matching avoiding M0
for c in row1:
    pts = [p for pr in c for p in pr]
    assert len(c) == 6 and sorted(pts) == list(ROW_PTS) and not (c & M0_SET)
check("(a) row-1 configurations, brute force", len(row1), EXPECTED['row1_configs'])
# inclusion-exclusion: matchings of K12 containing j prescribed row-0 pairs = (11-2j)!!
incl_excl = sum((-1) ** j * comb(6, j) * double_factorial(11 - 2 * j) for j in range(7))
check("(a) row-1 configurations, inclusion-exclusion sum_j (-1)^j C(6,j) (11-2j)!!", incl_excl,
      EXPECTED['row1_configs'])
# negative control on the enumerator: forgetting the exclusion must give 11!! = 10395
no_excl = sum(1 for _ in perfect_matchings(ROW_PTS, frozenset()))
check("(a) control: enumerator WITHOUT the row-0 exclusion gives 11!!", no_excl, double_factorial(11))
check_differs("(a) control: that count differs from 6040", no_excl, EXPECTED['row1_configs'])

# ----------------------------------------------------------------------------
# G1, built from the definition (not from exist.py)
# ----------------------------------------------------------------------------
def build_group(pair_perms, swap_vectors):
    """Point permutations of 0..14 fixing 0,1,2 that send row-0 pair i to row-0
    pair sigma[i], swapped within the pair when swaps[i] is set."""
    elems = set()
    for sigma in pair_perms:
        for swaps in swap_vectors:
            g = list(range(V))
            for i, (a, b) in enumerate(M0):
                c, d = M0[sigma[i]]
                if swaps[i]:
                    c, d = d, c
                g[a], g[b] = c, d
            elems.add(tuple(g))
    return sorted(elems)


def group_sanity(name, G, expected_order, sample=20000, seed=1):
    """Checks that G is a set of the right kind of permutations and (by
    sampling) closed under composition and inverses."""
    problems = []
    Gset = set(G)
    if len(Gset) != len(G):
        problems.append("duplicate elements")
    for g in G:
        if sorted(g) != list(range(V)):
            problems.append("not a permutation"); break
        if g[0] != 0 or g[1] != 1 or g[2] != 2:
            problems.append("does not fix 0,1,2"); break
        if act(g, M0_SET) != M0_SET:
            problems.append("does not preserve the row-0 pairs"); break
        if frozenset(tuple(sorted(g[x] for x in blk)) for blk in ROW0_BLOCKS) != frozenset(ROW0_BLOCKS):
            problems.append("does not preserve the row-0 blocks"); break
    rng = random.Random(seed)
    for _ in range(sample):
        g, h = rng.choice(G), rng.choice(G)
        if compose(g, h) not in Gset:
            problems.append("not closed under composition"); break
    for _ in range(sample):
        g = rng.choice(G)
        inv = [0] * V
        for i, gi in enumerate(g):
            inv[gi] = i
        if tuple(inv) not in Gset:
            problems.append("not closed under inverses"); break
    print(f"  {name}: {len(G)} elements; sanity problems: {problems or 'none'}"
          f" (all fix 0,1,2 and preserve row 0; {sample} sampled compositions and inverses closed)")
    check(f"  |{name}|", len(G), expected_order)
    return not problems


print()
print("=" * 78)
print("G1 = permutations fixing 0,1,2 and preserving row 0, built as (pair permutation, within-pair swaps)")
print("=" * 78)
ALL_PAIR_PERMS = list(itertools.permutations(range(6)))
ALL_SWAPS = list(itertools.product((False, True), repeat=6))
G1 = build_group(ALL_PAIR_PERMS, ALL_SWAPS)
g1_ok = group_sanity("G1", G1, EXPECTED['G1_order'])
print("  Completeness argument: any permutation fixing 0,1,2 and preserving row 0 permutes the six")
print("  row-0 pairs and orients each, so there are at most 2^6 * 6! = 46080 of them; the 46080")
print("  distinct elements built above are all of that kind, hence they are the whole group.")
IDENTITY = tuple(range(V))
assert IDENTITY in G1

# ----------------------------------------------------------------------------
# (b) orbits by applying the FULL group to each orbit minimum
# ----------------------------------------------------------------------------
def orbits_full(group, confs):
    """Orbits of `group` (its complete element list) on the set `confs`.
    Scans configurations in lexicographic order; the first unseen element of
    an orbit is that orbit's lexicographic minimum.  Every orbit is obtained by
    applying EVERY group element to its minimum; the stabiliser order is the
    number of elements fixing the minimum.  Returns (orbits, problems) with
    orbits = [(rep, orbit_frozenset, stabiliser_order), ...]."""
    confset = set(confs)
    seen = set()
    out = []
    problems = []
    for rep in sorted(confs, key=key):
        if rep in seen:
            continue
        images = [act(g, rep) for g in group]
        orbit = frozenset(images)
        stab = sum(1 for im in images if im == rep)
        if not orbit <= confset:
            problems.append(f"orbit of {fmt(rep)} leaves the configuration set (action not closed)")
        if orbit & seen:
            problems.append(f"orbit of {fmt(rep)} overlaps an earlier orbit")
        if len(orbit) * stab != len(group):
            problems.append(f"orbit-stabiliser identity fails at {fmt(rep)}: {len(orbit)} * {stab} != {len(group)}")
        if min(orbit, key=key) != rep:
            problems.append(f"{fmt(rep)} is not the minimum of its orbit")
        seen |= orbit
        out.append((rep, orbit, stab))
    if seen != confset:
        problems.append("orbits do not cover the configuration set")
    return out, problems


def cycle_type(conf):
    """Half-lengths of the cycles of the 2-regular graph M0 u conf on {3..14},
    as a partition of 6 (descending).  Since conf avoids M0 every cycle has
    length >= 4.  Invariant under G1 (which preserves M0)."""
    adj = {p: [] for p in ROW_PTS}
    for a, b in list(M0) + sorted(conf):
        adj[a].append(b)
        adj[b].append(a)
    seen = set()
    parts = []
    for s in ROW_PTS:
        if s in seen:
            continue
        n, prev, x = 0, None, s
        while True:
            seen.add(x)
            n += 1
            nxt = adj[x][0] if adj[x][0] != prev else adj[x][1]
            prev, x = x, nxt
            if x == s:
                break
        assert n % 2 == 0 and n >= 4
        parts.append(n // 2)
    return tuple(sorted(parts, reverse=True))


TYPE_NAME = {(2, 2, 2): '2+2+2', (4, 2): '4+2', (3, 3): '3+3', (6,): '6'}

print()
print("=" * 78)
print("(b) G1-orbits of the 6040 row-1 configurations (full-group expansion of each orbit minimum)")
print("=" * 78)
t = time.time()
orbits, problems = orbits_full(G1, row1)
print(f"  orbit scan: {len(orbits)} orbits in {time.time() - t:.2f} s; problems: {problems or 'none'}")
check("(b) orbit scan problems", problems, [])
check("(b) number of G1-orbits", len(orbits), len(EXPECTED['orbits']))
check("(b) sum of orbit sizes", sum(len(o) for _, o, _ in orbits), EXPECTED['row1_configs'])
got_sizes = sorted(len(o) for _, o, _ in orbits)
check("(b) orbit sizes (sorted)", got_sizes, sorted(EXPECTED['orbits']))
got_size_to_stab = {len(o): s for _, o, s in orbits}
check("(b) stabiliser order by orbit size", got_size_to_stab,
      {sz: st for sz, (st, _) in EXPECTED['orbits'].items()})
# cycle-type invariant: constant on each orbit, and distinct across orbits
type_by_orbit = {}
for rep, orb, st in orbits:
    types = {cycle_type(c) for c in orb}
    type_by_orbit[len(orb)] = types
check("(b) each orbit has a single cycle type", all(len(ts) == 1 for ts in type_by_orbit.values()), True)
got_size_to_type = {sz: next(iter(ts)) for sz, ts in type_by_orbit.items()}
check("(b) cycle type by orbit size", got_size_to_type, {sz: ty for sz, (_, ty) in EXPECTED['orbits'].items()})
# group-free cross-check: count configurations by cycle type directly
type_counts = Counter(cycle_type(c) for c in row1)
check("(b) configurations per cycle type (no group used)", dict(type_counts),
      {ty: sz for sz, (_, ty) in EXPECTED['orbits'].items()})

# ----------------------------------------------------------------------------
# (b) negative control: G1 without the within-pair swaps (order 720)
# ----------------------------------------------------------------------------
print()
print("-" * 78)
print("(b) NEGATIVE CONTROL: the same orbit computation with the WRONG group (no within-pair swaps)")
print("-" * 78)
G1_noswap = build_group(ALL_PAIR_PERMS, [(False,) * 6])
group_sanity("G1_noswap", G1_noswap, 720)
orbits_wrong, problems_wrong = orbits_full(G1_noswap, row1)
wrong_sizes = sorted(Counter(len(o) for _, o, _ in orbits_wrong).items())
print(f"  wrong group: {len(orbits_wrong)} orbits, problems {problems_wrong or 'none'}; size multiset {wrong_sizes}")
check_differs("(b) control: orbit sizes under the wrong group", sorted(len(o) for _, o, _ in orbits_wrong),
              got_sizes)
check_differs("(b) control: number of orbits under the wrong group", len(orbits_wrong), len(orbits))

# ----------------------------------------------------------------------------
# (c) canonical representatives, compared with exist.py's
# ----------------------------------------------------------------------------
print()
print("=" * 78)
print("(c) lexicographically least representative of each orbit, vs exist.py's cube representatives")
print("=" * 78)
HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.normpath(os.path.join(HERE, '..', 'scratch'))


def read_exist_reps():
    files = sorted(glob.glob(os.path.join(SCRATCH, '**', 'cubes-15-32-depth1.jsonl'), recursive=True))
    reps = {}   # name -> {conf: [files]}
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get('v') != V or d.get('b') != B or not d.get('cube'):
                    continue
                row1_entries = [c for c in d['cube'] if c.get('point') == 1]
                if len(row1_entries) != 1:
                    continue
                conf = frozenset(tuple(sorted(x for x in blk if x != 1)) for blk in row1_entries[0]['blocks'])
                name = d.get('cube_name')
                if not name:      # the 08:50 cube-0 record predates the cube_name key; take it from the CNF path
                    m = re.search(r'cube(\d{3})', d.get('cnf', '') or '')
                    name = 'cube' + m.group(1) if m else '?'
                reps.setdefault(name, {}).setdefault(conf, []).append(os.path.relpath(f, HERE))
    return reps


exist_reps = read_exist_reps()
if exist_reps:
    source = "scratch/*/cubes-15-32-depth1.jsonl"
else:
    source = "FALLBACK copy in this script (scratch files not present)"
    exist_reps = {n: {frozenset(p): ['(fallback)']} for n, p in FALLBACK_EXIST_REPS.items()}
print(f"  exist.py representatives read from: {source}")
for name in sorted(exist_reps):
    for conf, files in exist_reps[name].items():
        print(f"    {name}: {fmt(conf)}   <- {', '.join(files)}")
    if len(exist_reps[name]) != 1:
        print(f"    !! {name} has {len(exist_reps[name])} different row descriptions across files")
check("(c) every exist.py cube name has exactly one row description", all(len(v) == 1 for v in exist_reps.values()), True)

# my orbits, in lexicographic order of their minima
print("  this script's orbits (ordered by lexicographic minimum):")
my_index_map = {}
for k, (rep, orb, st) in enumerate(orbits):
    ty = TYPE_NAME[cycle_type(rep)]
    print(f"    orbit {k}: size {len(orb):5d}  stabiliser {st:4d}  cycle type {ty:6s}  min rep {fmt(rep)}")
    my_index_map[k] = (rep, orb, st)

exist_ok = True
match_lexmin = True
for name in sorted(exist_reps):
    conf = next(iter(exist_reps[name]))
    k = int(name[4:]) if name.startswith('cube') and name[4:].isdigit() else None
    home = [(kk, rep, orb, st) for kk, (rep, orb, st) in my_index_map.items() if conf in orb]
    if len(home) != 1:
        print(f"    {name}: NOT in exactly one orbit ({len(home)})"); exist_ok = False
        continue
    kk, rep, orb, st = home[0]
    exp_size, exp_stab = EXPECTED['exist_cubes'].get(name, (None, None))
    same = (conf == rep)
    match_lexmin &= same
    ok = (kk == k and len(orb) == exp_size and st == exp_stab)
    exist_ok &= ok
    print(f"    {name}: lies in this script's orbit {kk} (size {len(orb)}, stabiliser {st}); ledger says"
          f" (orbit {exp_size}, stabiliser {exp_stab}) -> {'consistent' if ok else 'INCONSISTENT'};"
          f" identical to this script's lex-min representative: {'YES' if same else 'NO'}")
check("(c) each exist.py cube k lies in this script's orbit k with the ledger's size and stabiliser", exist_ok, True)
check("(c) exist.py's representatives are exactly this script's lex-min representatives", match_lexmin, True)

# ----------------------------------------------------------------------------
# (d) Lemma 7' depth-2 split of cube 3
# ----------------------------------------------------------------------------
print()
print("=" * 78)
print("(d) Lemma 7' depth-2 split of the size-3840 orbit (cube 3): rows of point 2 under G2 = Stab_G1(c1)")
print("=" * 78)
def fail_now(what):
    """Depth-2 needs a sound depth-1 result; if that is missing, end with a clean FAIL line."""
    bad = [(label, got, exp) for label, got, exp, ok in RESULTS if not ok]
    detail = '; '.join(f"{label}: got {got!r} expected {exp!r}" for label, got, exp in bad)
    print(f"ORBITS_INDEPENDENT FAIL {what}" + (f"; {detail}" if detail else ''))
    sys.exit(1)


c1_candidates = [rep for rep, orb, st in orbits if len(orb) == 3840]
if len(c1_candidates) != 1:
    fail_now(f"(d) expected exactly one depth-1 orbit of size 3840, found {len(c1_candidates)}")
c1 = c1_candidates[0]
print(f"  c1 = {fmt(c1)}")
G2 = [g for g in G1 if act(g, c1) == c1]
# G2 is a group: full closure table (12 x 12)
G2set = set(G2)
closed = all(compose(g, h) in G2set for g in G2 for h in G2)
print(f"  G2 = elements of G1 fixing c1: {len(G2)} elements; closed under composition (all pairs): {closed}")
check("(d) |G2|", len(G2), 12)
check("(d) G2 closed under composition", closed, True)

top = min(V - 3, 2 * E - (V - 1) * P)
all_degrees_minimum = (2 * E == V * P)
D_VALUES = [P] if all_degrees_minimum else list(range(P, top + 1, 2))
print(f"  Lemma 7': e = {E}, p = {P}, top = min(v-3, 2e-(v-1)p) = {top}, all_degrees_minimum = {all_degrees_minimum}")
print(f"  admissible leave degrees d of point 2: {D_VALUES}; a row-2 configuration with leave degree d is a")
print(f"  set of (v-1-d)/2 - 1 pairs on {{3..14}} avoiding the row-0 pairs and c1, the other d points being")
print(f"  point 2's leave partners (so pairs and leave set partition {{3..14}}).")
print("  Reading of the text adopted: d ranges over p, p+2, ..., top with NO further restriction (the lemma")
print("  states no other), and the configuration is identified with its pair set (the leave set is implied).")


def row2_configurations(c1):
    forbidden = M0_SET | c1
    confs = {}      # conf -> d
    per_d = {}
    dups = 0
    for d in D_VALUES:
        need = (V - 1 - d) // 2 - 1

        def rec(remaining, pairs, leave):
            if not remaining:
                if len(pairs) == need and len(leave) == d:
                    yield frozenset(pairs)
                return
            a, rest = remaining[0], remaining[1:]
            if len(leave) < d:                       # a is a leave partner of point 2
                yield from rec(rest, pairs, leave + (a,))
            if len(pairs) < need:                    # {2, a, b} is a block
                for i, b in enumerate(rest):
                    if (a, b) in forbidden:
                        continue
                    yield from rec(rest[:i] + rest[i + 1:], pairs + ((a, b),), leave)

        n = 0
        for conf in rec(ROW_PTS, (), ()):
            n += 1
            if conf in confs:
                dups += 1
            confs[conf] = d
        per_d[d] = n
    return confs, per_d, dups


t = time.time()
row2, per_d, dups = row2_configurations(c1)
print(f"  row-2 configurations: {len(row2)} (per d: {per_d}; duplicate descriptions removed: {dups}) in {time.time() - t:.2f} s")
# sanity: every configuration avoids forbidden pairs, is a partial matching, has the right size for its d
forb = M0_SET | c1
for conf, d in row2.items():
    pts = [p for pr in conf for p in pr]
    assert len(pts) == len(set(pts)) and not (conf & forb) and len(conf) == (V - 1 - d) // 2 - 1

t = time.time()
children, problems2 = orbits_full(G2, list(row2))
print(f"  G2-orbit scan: {len(children)} children in {time.time() - t:.2f} s; problems: {problems2 or 'none'}")
check("(d) depth-2 orbit scan problems", problems2, [])
check("(d) number of depth-2 children of cube 3", len(children), EXPECTED['depth2_children'])
stab_dist = dict(sorted(Counter(st for _, _, st in children).items()))
check("(d) child stabiliser-order distribution", stab_dist, EXPECTED['depth2_stab'])
check("(d) sum over children of |G2|/|H| equals the number of row-2 configurations",
      sum(len(G2) // st for _, _, st in children), len(row2))
# children per leave degree, for the record
per_d_children = Counter(row2[rep] for rep, _, _ in children)
print(f"  children per leave degree d: {dict(sorted(per_d_children.items()))}")
# Burnside: number of orbits = (1/|G2|) sum_g |Fix(g)|
fix_total = 0
for g in G2:
    fix_total += sum(1 for conf in row2 if act(g, conf) == conf)
print(f"  Burnside: sum_g |Fix(g)| = {fix_total}, / |G2| = {fix_total / len(G2)}")
check("(d) Burnside orbit count (sum_g |Fix(g)| / |G2|)", fix_total // len(G2) if fix_total % len(G2) == 0 else fix_total / len(G2),
      EXPECTED['depth2_children'])

# ----------------------------------------------------------------------------
# (d) negative controls
# ----------------------------------------------------------------------------
print()
print("-" * 78)
print("(d) NEGATIVE CONTROLS")
print("-" * 78)


def order(g):
    n, x = 1, g
    while x != IDENTITY:
        x = compose(g, x)
        n += 1
    return n


gmax = max(G2, key=order)
cyc = [IDENTITY]
x = gmax
while x != IDENTITY:
    cyc.append(x)
    x = compose(gmax, x)
if len(cyc) == len(G2):     # G2 cyclic: fall back to the trivial subgroup
    cyc = [IDENTITY]
print(f"  proper subgroup of G2: <element of order {order(gmax)}>, {len(cyc)} elements")
children_sub, problems_sub = orbits_full(cyc, list(row2))
print(f"  children under that subgroup: {len(children_sub)} (problems {problems_sub or 'none'})")
check_differs("(d) control: child count under a proper subgroup of G2", len(children_sub), len(children))

c1_wrong_candidates = [rep for rep, orb, st in orbits if len(orb) == 120]
if len(c1_wrong_candidates) != 1:
    fail_now(f"(d) control needs exactly one depth-1 orbit of size 120, found {len(c1_wrong_candidates)}")
c1_wrong = c1_wrong_candidates[0]
G2_wrong = [g for g in G1 if act(g, c1_wrong) == c1_wrong]
_, problems_wrongG2 = orbits_full(G2_wrong, list(row2))
n_leave = sum('leaves the configuration set' in p for p in problems_wrongG2)
print(f"  stabiliser of the WRONG cube (cube 0, order {len(G2_wrong)}) applied to cube 3's row-2 configurations:")
print(f"    closure violations reported: {n_leave} (of {len(problems_wrongG2)} problems)")
check_differs("(d) control: the closure check goes red under the wrong stabiliser", n_leave, 0)

# ----------------------------------------------------------------------------
# verdict
# ----------------------------------------------------------------------------
print()
print("=" * 78)
elapsed = time.time() - T0
bad = [(label, got, exp) for label, got, exp, ok in RESULTS if not ok]
print(f"checks: {len(RESULTS)} total, {len(RESULTS) - len(bad)} passed, {len(bad)} failed; runtime {elapsed:.1f} s")
if bad:
    what = '; '.join(f"{label}: got {got!r} expected {exp!r}" for label, got, exp in bad)
    print(f"ORBITS_INDEPENDENT FAIL {what}")
    sys.exit(1)
print("ORBITS_INDEPENDENT PASS")
sys.exit(0)
