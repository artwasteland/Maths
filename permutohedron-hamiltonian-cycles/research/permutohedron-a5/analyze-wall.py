#!/usr/bin/env python3
# The wall, remeasured: merge the external-memory sweep's measured per-level
# state counts (levels.csv from count_frontier5_ext) with the edge ordering's
# cut-width profile, compare each level against the combinatorial bound on
# mate-window states at that width, and project the peak.
#
# Usage: python3 analyze-wall.py levels.csv bs5_bfs.dat
#
# The two projection models it reports (both stated with their assumptions):
#   A. band-equilibrium: within a cut-width band, the measured state count
#      rises then settles/falls (observed at widths 19 and 20); the settling
#      discount below the combinatorial bound, applied to the width-23 bound,
#      gives the low projection.
#   B. sustained-growth: the measured per-level growth through band entries
#      continues until the discount reaches O(10); gives the high projection.
import csv, sys
from math import comb

def widths_of(datfile):
    lines = open(datfile).read().strip().split('\n')
    edges, seen = [], set()
    for u, ln in enumerate(lines, 1):
        for w in map(int, ln.split()):
            k = (min(u, w), max(u, w))
            if k not in seen:
                seen.add(k); edges.append(k)
    E = len(edges); first, last = {}, {}
    for i, (a, b) in enumerate(edges):
        for v in (a, b):
            first.setdefault(v, i); last[v] = i
    return E, [sum(1 for v in first if first[v] <= i < last[v]) for i in range(E)]

def bound(w):
    # states of a mate window with w active slots: choose 2k slots paired off
    # (path endpoints, (2k-1)!! pairings), every other slot 0 or self
    t = 0
    for k in range(w // 2 + 1):
        d = 1
        for j in range(2 * k - 1, 0, -2): d *= j
        t += comb(w, 2 * k) * d * (2 ** (w - 2 * k))
    return t

def main():
    lv, dat = sys.argv[1], sys.argv[2]
    E, widths = widths_of(dat)
    rows = [r for r in csv.DictReader(open(lv)) if int(r['states_out']) > 0]
    print(f'{"level":>5} {"width":>5} {"states_out":>15} {"bound(width)":>18} {"discount":>10} {"secs":>5}')
    band_end = {}   # width -> last (deepest-level) states seen in that band
    for r in rows:
        L, s = int(r['level']), int(r['states_out'])
        w = widths[E - L]; b = bound(w)
        band_end[w] = (L, s, b / s)
        print(f'{L:>5} {w:>5} {s:>15,} {b:>18,} {b/s:>10.0f} {r["secs"]:>5}')
    print('\nband-end discounts (deepest measured level per width):')
    for w in sorted(band_end):
        L, s, d = band_end[w]
        print(f'  width {w:>2} (level {L:>3}): states {s:>15,}  discount {d:>10.0f}')
    peakb = bound(23)
    print(f'\ncombinatorial bound at the plateau width 23: {peakb:,}  (~{peakb:.1e})')
    ds = [band_end[w][2] for w in (19, 20) if w in band_end]
    if ds:
        lo, hi = max(ds), min(ds)
        print(f'model A (band-equilibrium, discount {lo:.0f}..{hi:.0f}): peak ~ {peakb/lo:.1e} .. {peakb/hi:.1e} states/level')
    print(f'model B (sustained growth to discount ~10): peak ~ {peakb/10:.1e} states/level')
    print('either way: orders of magnitude beyond a 64 GB machine '
          '(40 B/state in RAM; measured ~3.3 B/state all-in live on disk at the 2.5e9 scale; plan 6-12 B/state at peak).')

main()
