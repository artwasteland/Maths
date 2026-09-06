#!/usr/bin/env python3
"""Aggregate the 48 slices of the (22,61) enumeration from the workers' branches on origin.

Reads, per worker branch claude/reaching-noether-cloud-u22-w<N>:
  results/u22/interim/w<N>-dag-22-61-s<i>of48-counts.json   (hourly interim counts)
  results/u22/interim/w<N>-dag-22-61-s<i>of48-g3/<cell>.*    (G3 cells: 16-41, 17-43, 18-46)
  results/u22/s<i>of48/counts.json, hashes.json, 22-61.*      (final, written by the runbook)
and prints: slice coverage (each of 0..47 exactly once, or which are missing/duplicated),
per-level totals over the slices seen (children, kept), the G3 union sizes against AMP's
after-TU counts 1 / 8 / 38, and the (22,61) keep and UNKNOWN totals over finished slices.
Duplicated slices (w4 and w13 both own slice 3) are compared cell by cell.
Usage: aggregate-slices.py [--fetch] [--workers w1,...,w13] [--g3-dir DIR]  (exit 1 on any conflict)"""
import argparse, collections, json, os, subprocess, sys
p = argparse.ArgumentParser(); p.add_argument('--fetch', action='store_true')
p.add_argument('--workers', default=','.join(f'w{i}' for i in range(1, 14)))
p.add_argument('--g3-dir', default=None, help='write the G3 union keep sets here')
a = p.parse_args()
AMP_AFTER_TU = {(16, 41): 1, (17, 43): 8, (18, 46): 38}
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
def git(*args):
    r = subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True); return r.stdout if r.returncode == 0 else None
seen = collections.defaultdict(list)   # slice -> [(worker, source, cells)]
g3 = {c: {} for c in AMP_AFTER_TU}      # cell -> {g6 line: [(worker, slice)]}
final = {}                              # slice -> (worker, counts)
top = {}                                # (22,61) keep graphs -> [(worker, slice)]
conflicts = 0
for w in a.workers.split(','):
    br = f'origin/claude/reaching-noether-cloud-u22-{w}'
    if a.fetch: subprocess.run(['git', 'fetch', '-q', 'origin', br.split('origin/', 1)[1]], stderr=subprocess.DEVNULL)
    tree = git('ls-tree', '-r', '--name-only', br, 'research/unit-distance-22/results/u22/')
    if tree is None: continue
    for path in tree.split():
        base = os.path.basename(path)
        if '/interim/' in path and base.endswith('-counts.json'):
            d = json.loads(git('show', f'{br}:{path}') or '{}')
            if d.get('slice'): seen[d['slice'][1]].append((w, 'interim', d.get('completed_through_n'), {(c['n'], c['m']): c for c in d['cells']}))
        elif '/interim/' in path and '-g3/' in path and base.endswith('.keep.g6'):
            n, m = (int(x) for x in base.split('.')[0].split('-'))
            sl = int(path.split('-s')[1].split('of')[0])
            for line in (git('show', f'{br}:{path}') or '').split('\n'):
                if line and not line.startswith('>>'): g3[(n, m)].setdefault(line, []).append((w, sl))
        elif path.endswith('/counts.json') and '/s' in path and 'of48/' in path:
            sl = int(path.split('/s')[-1].split('of')[0])
            counts = json.loads(git('show', f'{br}:{path}') or '[]')
            final.setdefault(sl, []).append((w, counts))
            # a finished slice's counts.json is authoritative: feed it in as the most advanced record
            cells = {(n, m): {'n': n, 'm': m, 'children': ch, 'kept': (pc or {}).get('kept'), 'tu': (pc or {}).get('tu')} for n, m, ch, pc in counts}
            seen[sl].append((w, 'final', 99, cells))
        elif path.endswith('/22-61.keep.g6') and '/s' in path and 'of48/' in path:
            sl = int(path.split('/s')[-1].split('of')[0])
            for line in (git('show', f'{br}:{path}') or '').split('\n'):
                if line and not line.startswith('>>'): top.setdefault(line, []).append((w, sl))
print(f'slices with any data: {len(seen)} of 48; finished (counts.json): {sorted(final)}')
print(f'(22,61) keep union over finished slices: {len(top)} graphs' + (f'  <-- SURVIVORS: {sorted(top)[:5]}' if top else ''))
missing = [i for i in range(48) if i not in seen]
print('missing entirely:', missing)
# per-slice: pick the most advanced record; compare duplicates cell by cell where both have the cell
totals = collections.defaultdict(lambda: [0, 0, 0])   # level -> [children, kept, slices]
for sl, recs in sorted(seen.items()):
    recs.sort(key=lambda r: -(r[2] or -1))
    best = recs[0]
    for other in recs[1:]:
        for cell, c in other[3].items():
            b = best[3].get(cell)
            if b and b.get('kept') is not None and c.get('kept') is not None and (b['children'], b['kept']) != (c['children'], c['kept']):
                conflicts += 1; print(f'CONFLICT slice {sl} cell {cell}: {best[0]} {b["children"]}/{b["kept"]} vs {other[0]} {c["children"]}/{c["kept"]}')
    for (n, m), c in best[3].items():
        if n >= 14 and c.get('kept') is not None:
            totals[n][0] += c['children'] or 0; totals[n][1] += c['kept']; 
    for n in set(n for (n, m) in best[3] if n >= 14): totals[n][2] += 1
print('level: children / kept over the slices that completed it (slices counted)')
for n in sorted(totals): print(f'  {n}: {totals[n][0]:,} / {totals[n][1]:,}  ({totals[n][2]} slices)')
print('G3 union (after-TU survivors over the slices seen) vs AMP:')
for cell, expect in AMP_AFTER_TU.items():
    lines = g3[cell]; dup = {g: ws for g, ws in lines.items() if len(set(s for _, s in ws)) > 1}
    print(f'  {cell}: {len(lines)} distinct graphs (AMP {expect}); in more than one slice: {len(dup)}')
    if dup: conflicts += 1; print('   CONFLICT: a graph in two slices breaks the partition:', list(dup.items())[:3])
    if a.g3_dir:
        os.makedirs(a.g3_dir, exist_ok=True)
        with open(os.path.join(a.g3_dir, f'{cell[0]}-{cell[1]}.union.keep.g6'), 'w') as fh:
            fh.write(''.join(g + '\n' for g in sorted(lines)))
sys.exit(1 if conflicts else 0)
