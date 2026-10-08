#!/usr/bin/env python3
"""make_sample11.py: a stratified, reproducible sample of refuted GP-11 records.

Usage: python make_sample11.py INDEX.jsonl SELECT.txt [SEED]

Reads the index written by `verify_refutations11.py scan` and the records file it points to (to
learn each tree's field degree and each real certificate's proof kind), then selects:
  * the 20 largest refuted records;
  * every null and every real record (the rare types), every TU chain ending at a refuted
    record, every TU chain of three steps, and every R-ptr to a tree;
  * a seeded random sample of the rest: tu 60, sub 60, tree 20 / 50 / 20 by field degree
    1 / 2 / 4, null-dag 30, real-dag 25 Sturm + 15 SOS;
  * the pointer target of every selected R-ptr or TU-to-record chain (so pointers resolve).
Writes one graph6 per line.
"""
import json
import random
import sys


def main(argv):
    index_path, out = argv[1], argv[2]
    seed = int(argv[3]) if len(argv) > 3 else 20261007
    idx = [json.loads(x) for x in open(index_path)]
    with open(index_path + '.meta.json') as fh:
        records = json.load(fh)['records']
    by = {e['g6']: e for e in idx}
    rng = random.Random(seed)
    fh = open(records, 'rb')

    def load(e):
        fh.seek(e['offset'])
        return json.loads(fh.read(e['length']))
    sel = {}

    def add(e, why):
        sel.setdefault(e['g6'], why)
    for e in sorted(idx, key=lambda e: -e['length'])[:20]:
        add(e, 'largest-20')
    strata = {}
    for e in idx:
        t = e['type']
        key = t
        if t in ('null', 'real'):
            add(e, 'all-%s' % t)
            continue
        if t == 'tu' and e['ptr']:
            add(e, 'all-tu-to-record')
            continue
        if t == 'sub' and by[e['ptr']]['type'] != 'tu':
            add(e, 'all-sub-to-%s' % by[e['ptr']]['type'])
            continue
        if t == 'tree' or t == 'real-dag' or t == 'tu':
            c = load(e)['cert']
            if t == 'tree':
                key = 'tree-deg%d' % (len(c['witness']['field']['minpoly']) - 1)
            elif t == 'real-dag':
                key = 'real-dag-' + ('sturm' if 'sturm' in c else 'sos')
            elif len(c['steps']) == 3:
                add(e, 'all-tu-3-step')
                continue
        strata.setdefault(key, []).append(e)
    want = {'tu': 60, 'sub': 60, 'tree-deg1': 20, 'tree-deg2': 50, 'tree-deg4': 20, 'null-dag': 30,
            'real-dag-sturm': 25, 'real-dag-sos': 15}
    for key, k in want.items():
        pool = sorted(strata.get(key, []), key=lambda e: e['i'])
        for e in rng.sample(pool, min(k, len(pool))):
            add(e, 'random-%s' % key)
    for g in list(sel):
        p = by[g]['ptr']
        if p:
            add(by[p], 'pointer-target')
    with open(out, 'w') as fo:
        for g in sorted(sel):
            fo.write(g + '\n')
    with open(out + '.why.json', 'w') as fo:
        json.dump(sel, fo, indent=0)
    from collections import Counter
    print(json.dumps({'selected': len(sel), 'by_reason': Counter(sel.values()),
                      'by_type': Counter(by[g]['type'] for g in sel), 'seed': seed}))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
