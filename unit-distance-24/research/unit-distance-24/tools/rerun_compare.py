#!/usr/bin/env python3
"""Compare a fresh from-scratch re-run of a u(24) slice with the copy the judge counted.

Written 2026-10-06 for the five accepted copies the full-plan judge reports as RESUMED (slices 239, 830, 1069, 1352,
1641: copies that carry recovered/resumed cells from the 2026-10-01 legacy supervisor). Slice 247's re-run showed
that such a copy can lose work while passing its own audit, so each of the five was re-run from scratch on the u24 VM
(tags vmr1, vmr2) and is compared here with the counted copy.

Each ROOT is an extracted `research/unit-distance-24/results/u24` directory (one worker branch's). Compared:
`counts.json` (every cell's counts at every level: children, kept, pruned by kind; slice 247's lossy copy differed
here), `hashes.json` (sha256 and record count of each file the runbook keeps: the prefix files of levels 0 to 12 and
the top-level files of levels 22 to 24; the intermediate level files are deleted after the check, so no byte
comparison of them is possible), `reach.json`, `run-config.json`, and the known-graph control's `known.json` without
its `run` field (the machine's working directory). The fresh copy's receipt must carry exactly one `pass` verdict.
Not compared: the structure and inventory files, which list retained intermediate files and differ by runbook
version.

Each row also records both copies' recovered (resumed) cell counts from their receipts' structure files, and
`fresh_from_scratch` (the fresh copy recovered nothing). IDENTICAL is about content; a from-scratch twin also needs
`fresh_from_scratch`.

Usage: rerun_compare.py SLICE KEPT_ROOT KEPT_TAG FRESH_ROOT FRESH_TAG    (prints one JSON object; exit 0 iff IDENTICAL)
       rerun_compare.py --self-test SLICE KEPT_ROOT KEPT_TAG             (each mutation must be reported DIFFERENT)
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

CELL = '24-69-L12-tri-pf74'
SLICE_FILES = ('hashes.json', 'counts.json', 'reach.json', 'run-config.json')


def load(path):
    return json.loads(Path(path).read_text())


def compare(slice_, kept_root, kept_tag, fresh_root, fresh_tag):
    kept_root, fresh_root = Path(kept_root), Path(fresh_root)
    name = f's{slice_}of1920'
    out = {'slice': slice_, 'kept_tag': kept_tag, 'fresh_tag': fresh_tag, 'files': {}}
    for f in SLICE_FILES:
        out['files'][f] = load(kept_root / CELL / name / f) == load(fresh_root / CELL / name / f)
    known = [load(root / 'check' / f'{name}-{tag}.known.json') for root, tag in ((kept_root, kept_tag), (fresh_root, fresh_tag))]
    for k in known:
        k.pop('run', None)
    out['files']['known.json without run'] = known[0] == known[1]
    receipt = (fresh_root / 'check' / f'{name}-{fresh_tag}.txt').read_text()
    out['fresh_verdict_pass'] = receipt.count('\n# u24-worker verdict: pass\n') == 1
    # Freshness (added 2026-10-07 after the u24 referee read): a twin must itself have run from scratch. The receipt's
    # structure records the cells a resumed run recovered; a fresh copy has none.
    for role, root, tag in (('kept', kept_root, kept_tag), ('fresh', fresh_root, fresh_tag)):
        rc = load(root / 'check' / f'{name}-{tag}.structure.json').get('recovered_cells') or []
        out[f'{role}_recovered_cells'] = len(rc) if isinstance(rc, (list, dict)) else int(rc)
    out['fresh_from_scratch'] = out['fresh_recovered_cells'] == 0
    hashes = load(fresh_root / CELL / name / 'hashes.json')
    out['hashed_files'] = len(hashes['files'])
    counts = load(fresh_root / CELL / name / 'counts.json')
    out['cells'] = len(counts)
    out['kept_above_12'] = sum(r[-1].get('kept', 0) for r in counts if isinstance(r[-1], dict) and r[0] > 12)
    out['verdict'] = 'IDENTICAL' if all(out['files'].values()) and out['fresh_verdict_pass'] else 'DIFFERENT'
    return out


def self_test(slice_, kept_root, kept_tag):
    """Compare the kept copy with itself (IDENTICAL), then with copies carrying one mutation each (DIFFERENT)."""
    name = f's{slice_}of1920'
    base = compare(slice_, kept_root, kept_tag, kept_root, kept_tag)
    results = {'self': base['verdict'] == 'IDENTICAL'}

    def mutated(edit):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'u24'
            (root / CELL).mkdir(parents=True)
            shutil.copytree(Path(kept_root) / CELL / name, root / CELL / name)
            shutil.copytree(Path(kept_root) / 'check', root / 'check',
                            ignore=lambda d, names: [n for n in names if not n.startswith(name + '-')])
            edit(root)
            return compare(slice_, kept_root, kept_tag, root, kept_tag)['verdict']

    def bump_record(root):
        p = root / CELL / name / 'hashes.json'
        h = load(p)
        last = sorted(h['files'])[-1]
        h['files'][last]['records'] += 1
        p.write_text(json.dumps(h))

    def bump_count(root):
        p = root / CELL / name / 'counts.json'
        c = load(p)
        row = [r for r in c if isinstance(r[-1], dict)][-1]
        row[-1]['input'] += 1
        p.write_text(json.dumps(c))

    def change_known(root):
        p = root / 'check' / f'{name}-{kept_tag}.known.json'
        k = load(p)
        k['__mutated__'] = 1
        p.write_text(json.dumps(k))

    def flip_verdict(root):
        p = root / 'check' / f'{name}-{kept_tag}.txt'
        p.write_text(p.read_text().replace('\n# u24-worker verdict: pass\n', '\n# u24-worker verdict: FAIL\n'))

    for label, edit in (('one record count', bump_record), ('one cell count', bump_count),
                        ('known.json', change_known), ('verdict', flip_verdict)):
        results[label] = mutated(edit) == 'DIFFERENT'
    return results


def main(argv):
    if argv[:1] == ['--self-test'] and len(argv) == 4:
        res = self_test(int(argv[1]), argv[2], argv[3])
        print(json.dumps(res))
        return 0 if all(res.values()) else 1
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    res = compare(int(argv[0]), argv[1], argv[2], argv[3], argv[4])
    print(json.dumps(res, sort_keys=True))
    return 0 if res['verdict'] == 'IDENTICAL' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
