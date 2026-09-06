#!/usr/bin/env python3
"""Compare every worker's published prefix-hashes-w<N>.json (sha256 + record count of each
level <= 13 file of its first slice) against a reference (w1 by default), reading them from the
workers' branches on origin. Prints one line per worker: identical / differing / missing files.
Exit status 1 if any file differs. Usage: compare-prefix-hashes.py [--ref w1] [--fetch]"""
import argparse, json, subprocess, sys
p = argparse.ArgumentParser(); p.add_argument('--ref', default='w1'); p.add_argument('--fetch', action='store_true')
p.add_argument('--workers', default=','.join(f'w{i}' for i in range(1, 13)))
a = p.parse_args()
def load(w):
    br = f'claude/reaching-noether-cloud-u22-{w}'
    if a.fetch: subprocess.run(['git', 'fetch', '-q', 'origin', br], stderr=subprocess.DEVNULL)
    r = subprocess.run(['git', 'show', f'origin/{br}:research/unit-distance-22/results/u22/prefix-hashes-{w}.json'],
                       capture_output=True, text=True)
    if r.returncode: return None
    try: return json.loads(r.stdout)
    except json.JSONDecodeError: return None
ref = load(a.ref)
if not ref: sys.exit(f'no reference file for {a.ref}')
rf = ref['files']; bad = 0
print(f"reference {a.ref}: {len(rf)} files, complete={ref.get('complete')}")
for w in a.workers.split(','):
    if w == a.ref: continue
    d = load(w)
    if not d: print(f'{w}: no prefix-hashes file published yet'); continue
    f = d['files']; same = diff = 0; missing = []
    # <n>-<m>.slice-<i>-of-<K>.g6 is the worker's own hash partition of a shared cell: per slice
    # by construction, so it is reported (record counts) rather than compared.
    slices = {k: v['records'] for k, v in f.items() if '.slice-' in k}
    for name, info in rf.items():
        if '.slice-' in name: continue
        if name not in f: missing.append(name); continue
        if f[name]['sha256'] == info['sha256'] and f[name]['records'] == info['records']: same += 1
        else: diff += 1; print(f'  {w} DIFF {name}: {f[name]} vs {info}')
    extra = sorted(k for k in set(f) - set(rf) if '.slice-' not in k)
    print(f"{w}: {same} identical, {diff} different, {len(missing)} missing, {len(extra)} extra, complete={d.get('complete')}; "
          f"slice files: {sum(slices.values())} records in {len(slices)} cells")
    bad += diff
sys.exit(1 if bad else 0)
