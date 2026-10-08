#!/usr/bin/env python3
"""Measure every retained level file of every counted u(24) copy, independently of the receipts and the audit.

Written 2026-10-07 after the G1 verification (Codex, <repo>/REPORT.md) reproduced an acceptance gap
in receipt_audit.py: the retained level-23 outputs are compared by hash with the worker's inventory, but their record
counts are taken from the inventory, and they are not compared with their producer's prune manifest. This tool asks
the question that matters for the result: does any judged copy actually have such a mismatch?

For each copy (each coverage and reproduction plan's chosen copy, from the judge reports' `cost.chosen`), in its
retained result directory, every `n-m.g6`, `n-m.keep.g6`, `n-m.UNKNOWN.g6` and `n-m.certs.jsonl` is read and:
  1. its sha256 and record count (newline-terminated lines) equal its `hashes.json` entry (the .g6 files; hashes.json
     does not list certificate files);
  2. its sha256 equals every manifest in the directory that names it in `outputs_sha256` (the prune manifest binds
     the certificate, keep and UNKNOWN files; the stage manifest binds the level file);
  3. against the cell's prune manifest counts: certificates == input (one certificate line per input graph), keep ==
     kept, UNKNOWN == unknown, and those counts equal the cell's row in `counts.json`;
  4. a certificate, keep or UNKNOWN file with no prune manifest naming it is a problem;
  5. (added after the G1 verification's second round) every level file equals its enumeration stage manifest
     (`n-m.manifest.json`): records == children_written and sha256 == children_file_sha256, and a stage manifest
     that records children for a level file that is not retained is a problem.

Usage: retained_scan.py SNAPSHOT EVIDENCE_DIR        (exit 0 iff no problem)
       retained_scan.py --self-test SLICE_DIR        (copies one retained directory and mutates it; each must fail)
"""
import gzip
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

R = 'research/unit-distance-24/results/u24'
CELL = '24-69-L12-tri-pf74'
KINDS = ('.certs.jsonl', '.keep.g6', '.UNKNOWN.g6')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def records(p):
    n = 0
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            n += b.count(b'\n')
    return n


def scan_dir(d, label):
    problems, measured = [], 0
    hashes = json.loads((d / 'hashes.json').read_text())['files']
    counts = {(row[0], row[1]): row[-1] for row in json.loads((d / 'counts.json').read_text()) if isinstance(row[-1], dict)}
    named = {}
    prunes = {}
    for m in sorted(d.glob('*manifest.json')):
        data = json.loads(m.read_text())
        for k, v in (data.get('outputs_sha256') or {}).items():
            named.setdefault(Path(k).name, []).append((m.name, v))
        if data.get('kind') == 'prune':
            prunes[tuple(data['level'])] = (m.name, data)
    stages = {}
    for m in sorted(d.glob('*.manifest.json')):
        if m.name.endswith('.prune.manifest.json'):
            continue
        data = json.loads(m.read_text())
        if 'children_written' in data or 'children_file_sha256' in data:
            stages[m.name[:-len('.manifest.json')] + '.g6'] = (m.name, data)
    for p in sorted(d.iterdir()):
        if not p.is_file() or not (p.name.endswith('.g6') or p.name.endswith('.certs.jsonl')):
            continue
        measured += 1
        got_sha, got_rec = sha(p), records(p)
        if p.name.endswith('.g6'):
            entry = hashes.get(p.name)
            if entry is None:
                problems.append(f'{label}: {p.name} retained but not in hashes.json')
            elif (entry['sha256'], entry['records']) != (got_sha, got_rec):
                problems.append(f'{label}: {p.name} measured ({got_sha[:12]}, {got_rec}) != hashes.json '
                                f'({entry["sha256"][:12]}, {entry["records"]})')
        if p.name in stages:  # the enumeration stage that wrote this level file: its child count and file hash
            mname, data = stages.pop(p.name)
            if data.get('children_written') != got_rec or data.get('children_file_sha256') != got_sha:
                problems.append(f'{label}: {p.name} measured ({got_sha[:12]}, {got_rec}) != {mname} children '
                                f'({str(data.get("children_file_sha256"))[:12]}, {data.get("children_written")})')
        for mname, v in named.get(p.name, []):
            if v != got_sha:
                problems.append(f'{label}: {p.name} sha {got_sha[:12]} != {mname} outputs_sha256 {v[:12]}')
        if p.name.endswith(KINDS):
            n, m = (int(x) for x in p.name.split('.')[0].split('-'))
            if (n, m) not in prunes or p.name not in {Path(k).name for k in prunes[(n, m)][1].get('outputs_sha256', {})}:
                problems.append(f'{label}: {p.name} has no prune manifest naming it')
                continue
            mname, data = prunes[(n, m)]
            key = {'.certs.jsonl': 'input', '.keep.g6': 'kept', '.UNKNOWN.g6': 'unknown'}[next(k for k in KINDS if p.name.endswith(k))]
            if data['counts'].get(key) != got_rec:
                problems.append(f'{label}: {p.name} records {got_rec} != {mname} counts[{key}] {data["counts"].get(key)}')
            cell = counts.get((n, m))
            if cell is None or any(cell.get(k) != data['counts'].get(k) for k in ('input', 'kept', 'unknown', 'pruned')):
                problems.append(f'{label}: counts.json cell ({n},{m}) disagrees with {mname} counts')
    for name, (mname, _) in sorted(stages.items()):
        problems.append(f'{label}: {mname} records children for {name}, which is not retained')
    return problems, measured


def copies(evidence):
    out = {}
    for plan in ('pilot', 'full', 'phaseb', 'repro'):
        j = json.load(gzip.open(Path(evidence) / f'judge-{plan}.json.gz'))
        for s, row in j['cost']['chosen'].items():
            out.setdefault(row['source'], (int(s), plan))
    return out


def main(argv):
    if argv[:1] == ['--self-test'] and len(argv) == 2:
        src = Path(argv[1])
        base, _ = scan_dir(src, 'original')
        results = {'original clean': not base}

        def mutate(edit):
            with tempfile.TemporaryDirectory() as tmp:
                d = Path(tmp) / src.name
                shutil.copytree(src, d)
                edit(d)
                return bool(scan_dir(d, 'mutated')[0])

        def add_cert(d):  # the G1 probe's shape: one record more in the level-23 certificate file
            with open(d / '23-64.certs.jsonl', 'a') as f:
                f.write(json.dumps({'g6': 'V' + '?' * 43, 'verdict': 'unknown', 'witness': None}) + '\n')

        def add_cert_rebind(d):  # the same, with the prune manifest's output hash rebound to the altered file
            add_cert(d)
            m = d / '23-64.prune.manifest.json'
            data = json.loads(m.read_text())
            for k in data['outputs_sha256']:
                if k.endswith('23-64.certs.jsonl'):
                    data['outputs_sha256'][k] = sha(d / '23-64.certs.jsonl')
            m.write_text(json.dumps(data))

        def drop_keep_line(d):  # a level-23 keep file one graph short, hashes.json refreshed to match
            p = d / '23-64.keep.g6'
            lines = p.read_bytes().splitlines(keepends=True)
            p.write_bytes(b''.join(lines[:-1]) if lines else b'X?\n')
            h = json.loads((d / 'hashes.json').read_text())
            h['files']['23-64.keep.g6'] = {'sha256': sha(p), 'records': records(p)}
            (d / 'hashes.json').write_text(json.dumps(h))

        results['level-23 certificate record added'] = mutate(add_cert)
        results['... and its producer hash rebound'] = mutate(add_cert_rebind)
        results['level-23 keep file altered, hashes.json refreshed'] = mutate(drop_keep_line)

        def stage_count(d):  # the G1 round-2 probe's shape: the stage manifest claims more children than the file
            m = d / '23-64.manifest.json'
            data = json.loads(m.read_text())
            data['children_written'] = data['children_written'] + 777
            m.write_text(json.dumps(data))

        def stage_hash(d):
            m = d / '23-64.manifest.json'
            data = json.loads(m.read_text())
            data['children_file_sha256'] = '0' * 64
            m.write_text(json.dumps(data))

        results['stage manifest child count raised'] = mutate(stage_count)
        results['stage manifest child-file hash changed'] = mutate(stage_hash)
        print(json.dumps(results))
        return 0 if all(results.values()) else 1
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    snap, evidence = Path(argv[0]), Path(argv[1])
    problems, files, n = [], 0, 0
    for src, (s, plan) in sorted(copies(evidence).items()):
        d = snap / src.split('/')[0] / R / CELL / f's{s}of1920'
        if not d.is_dir():
            problems.append(f'{plan} s{s} {src.split("/")[0]}: result directory missing')
            continue
        p, m = scan_dir(d, f'{plan} s{s} {src.split("/")[0]}')
        problems += p
        files += m
        n += 1
    for p in problems:
        print('PROBLEM', p)
    print(f'RETAINED SCAN {"OK" if not problems else "FAIL"}: {n} copies, {files} retained level files measured, '
          f'{len(problems)} problem(s)')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
