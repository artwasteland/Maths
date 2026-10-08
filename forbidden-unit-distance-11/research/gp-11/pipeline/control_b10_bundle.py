#!/usr/bin/env python3
"""Checker-side replay, disjoint assembly and control-tree preparation for 5.1.

This process never runs a producer. Historical named controls and F10 are visible
only here and to gp11check, after a producer has closed its certificate bundle.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from control_b10_guard import B10, B10_SHA, GP10, GP11, sha


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def read_bundle(bundle):
    summary = json.loads((bundle / 'summary.json').read_text())
    job = json.loads((bundle / 'job.json').read_text())
    if not summary.get('completed') or job.get('schema') != 'control51-v1' or job.get('population_sha256') != B10_SHA:
        raise ValueError('control51_bundle_required')
    for name, expected in summary['artifacts'].items():
        if Path(name).name != name or sha(bundle / name) != expected:
            raise ValueError('bundle_artifact_hash:' + name)
    assigned = (bundle / 'assigned.g6').read_text().splitlines()
    population = B10.read_text().splitlines()
    if assigned != sorted(set(assigned)) or assigned != [population[i] for i in job['assigned_ids']]:
        raise ValueError('assignment_mismatch')
    selection = job['selection']
    if selection['input_sha256'] is None:
        import random
        expected = sorted(random.Random(selection['seed']).sample(population, selection['sample'])) if selection['sample'] else population
        expected = [c for c in expected if int.from_bytes(hashlib.sha256(c.encode()).digest()[:8], 'big') % job['shard_count'] == job['shard_index']]
        if assigned != expected:
            raise ValueError('assignment_selection')
    return assigned, summary


def checker(run, complete=False):
    command = [sys.executable, '-B', str(GP11 / 'check/gp11check.py'), str(run)]
    if complete:
        command.append('--require-complete-b10')
    with (run / 'gp11-check.log').open('w') as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    report = json.loads((run / 'checked/report.json').read_text())
    if process.returncode or report.get('status') != 'ACCEPT' or report.get('direct_rejections') != 0:
        raise ValueError('checker_rejected:' + str(run / 'gp11-check.log'))
    if complete:
        required = 'PASS B10 COMPLETE derived=324'
        if required not in (run / 'gp11-check.log').read_text().splitlines():
            raise ValueError('complete_line_missing')
        if report.get('profile') != 'B10' or report['counts']['unknown'] != 0 or report.get('conditional') is not False:
            raise ValueError('complete_report_invariant')
        print(required)
    return report


def replay(bundle, output):
    started = time.monotonic()
    assigned, summary = read_bundle(bundle)
    output.mkdir(parents=True, exist_ok=False)
    for name in ('run.json', 'input.g6', 'UNKNOWN.g6'):
        shutil.copyfile(bundle / name, output / name)
    with gzip.open(bundle / 'records.jsonl.gz', 'rb') as source, (output / 'records.jsonl').open('wb') as target:
        shutil.copyfileobj(source, target)
    if sha(output / 'records.jsonl') != summary['records_sha256']:
        raise ValueError('bundle_record_hash')
    report = checker(output)
    if report['profile'] != 'sample' or report.get('forbidden_limit') != 9:
        raise ValueError('sample_profile_required')
    actual = {c: 0 for c in assigned}
    counts = dict(embedded=0, refuted=0, unknown=0)
    with (output / 'records.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['g6'] in actual:
                actual[row['g6']] += 1
                counts[row['verdict']] += 1
    if set(actual.values()) != {1} or counts != summary['counts']:
        raise ValueError('bundle_assigned_coverage')
    receipt = {'status': 'ACCEPT', 'counts': counts, 'profile': 'sample',
               'elapsed_seconds': time.monotonic()-started, 'report_sha256': sha(output / 'checked/report.json'),
               'source_summary_sha256': sha(bundle / 'summary.json'), 'claim_authorized': False}
    write(output / 'replay-receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))
    return report


def controls(output):
    """Extract only the eight checker prerequisites. Never copy root B10 records."""
    target = output / 'controls'
    target.mkdir(parents=True, exist_ok=False)
    archive_path = GP10 / 'cloud/final/tree-public.tar.gz'
    with tarfile.open(archive_path) as archive:
        for member in archive:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('unsafe_control_archive')
            if len(path.parts) < 4 or path.parts[:2] != ('tree', 'controls') or 'checked' in path.parts or not member.isfile():
                continue
            relative = Path(*path.parts[2:])
            if relative.parts[0] not in [*(f'B{n}p' for n in range(4, 10)), 'named', 'regressions']:
                raise ValueError('unexpected_control')
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, dest.open('wb') as sink:
                shutil.copyfileobj(source, sink)
    for name in [*(f'B{n}p' for n in range(4, 10)), 'named', 'regressions']:
        directory = target / name
        manifest = json.loads((directory / 'run.json').read_text())
        if name.startswith('B'):
            shutil.copyfile(GP10 / 'data' / (name + '.g6'), directory / 'input.g6')
        manifest['input'] = 'input.g6'
        write(directory / 'run.json', manifest)
        report = checker(directory)
        if report.get('profile') != name:
            raise ValueError('control_profile_mismatch')
    write(output / 'controls-provenance.json', {'archive_sha256': sha(archive_path),
          'scope': 'Checker prerequisites only; inaccessible to the producer; historical replay is not a new producer control.'})
    print('CHECKER PREREQUISITES ACCEPT; no B10 completeness claim')


def assemble(bundles, overlays, output, sample_union=False):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    assigned = set()
    population = set(B10.read_text().splitlines())
    original_unknown = set()
    for bundle in bundles:
        codes, _ = read_bundle(bundle)
        if assigned.intersection(codes):
            raise ValueError('shard_union_duplicate')
        assigned.update(codes)
        original_unknown.update((bundle / 'UNKNOWN.g6').read_text().splitlines())
    if not sample_union and assigned != population:
        raise ValueError(f'shard_union_coverage missing={len(population-assigned)} extra={len(assigned-population)}')
    overlay_assigned = set()
    for bundle in overlays:
        codes, _ = read_bundle(bundle)
        if not set(codes) <= original_unknown or overlay_assigned.intersection(codes):
            raise ValueError('overlay_not_disjoint_unknown_subset')
        overlay_assigned.update(codes)
    # SQLite bounds memory even for long exact coordinates. Keep alternative
    # proofs until a dependency-grounded one is found, avoiding merge cycles.
    db = sqlite3.connect(output / 'assembly.sqlite')
    db.executescript('PRAGMA cache_size=-8192; CREATE TABLE candidates(g6 TEXT, verdict TEXT, dep TEXT, raw TEXT, PRIMARY KEY(g6,raw));'
                     'CREATE TABLE chosen(g6 TEXT PRIMARY KEY, verdict TEXT, raw TEXT);')
    from common import load
    profile = load('control51_assembly_checker', GP11 / 'check/gp11check.py')
    ck = profile.base.Checker(9)
    receipts = []
    for i, bundle in enumerate([*bundles, *overlays]):
        replay(bundle, output / f'intake-{i:04d}')
        receipts.append({'path': str(bundle.resolve()), 'summary_sha256': sha(bundle / 'summary.json')})
        with gzip.open(bundle / 'records.jsonl.gz', 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                if row['g6'] not in population:
                    raise ValueError('support_outside_B10')
                dep, _ = ck.verify(row)
                if row['verdict'] != 'unknown':
                    conflict = db.execute("SELECT 1 FROM candidates WHERE g6=? AND verdict NOT IN (?, 'unknown')", (row['g6'], row['verdict'])).fetchone()
                    if conflict:
                        raise ValueError('embedded_refuted_conflict')
                db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?)', (row['g6'], row['verdict'], dep, line))
        db.commit()
    while True:
        progress = 0
        for code, verdict, dep, raw in db.execute("SELECT g6,verdict,dep,raw FROM candidates WHERE verdict!='unknown' AND g6 NOT IN (SELECT g6 FROM chosen) ORDER BY length(raw),raw"):
            if db.execute('SELECT 1 FROM chosen WHERE g6=?', (code,)).fetchone():
                continue
            if dep:
                result = db.execute('SELECT verdict FROM chosen WHERE g6=?', (dep,)).fetchone()
                if result is None:
                    continue
                if result[0] != verdict:
                    raise ValueError('pointer_target_verdict')
            db.execute('INSERT INTO chosen VALUES (?,?,?)', (code, verdict, raw))
            progress += 1
        db.commit()
        if not progress:
            break
    if db.execute("SELECT 1 FROM candidates WHERE verdict!='unknown' AND g6 NOT IN (SELECT g6 FROM chosen)").fetchone():
        raise ValueError('intake_dependency_cycle_or_missing')
    codes = sorted(assigned | {c for (c,) in db.execute('SELECT g6 FROM chosen')})
    if not sample_union and set(codes) != population:
        raise ValueError('B10_exact_coverage')
    unknowns = []
    with (output / 'records.jsonl').open('w') as stream:
        for code in codes:
            result = db.execute('SELECT raw FROM chosen WHERE g6=?', (code,)).fetchone()
            if result:
                stream.write(result[0])
            else:
                histories = [json.loads(raw)['cert'] for (raw,) in db.execute('SELECT raw FROM candidates WHERE g6=? ORDER BY raw', (code,))]
                stream.write(json.dumps({'g6': code, 'verdict': 'unknown', 'cert': {'reason': 'control51_residue', 'budget': {'prior_attempts': histories}}}, sort_keys=True) + '\n')
                unknowns.append(code)
    db.close()
    (output / 'UNKNOWN.g6').write_text(''.join(c+'\n' for c in unknowns))
    (output / 'input.g6').write_text(''.join(c+'\n' for c in codes))
    manifest = {'profile': 'sample' if sample_union else 'B10', 'input': 'input.g6',
                'input_sha256': sha(output / 'input.g6'), 'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6'}
    if sample_union:
        manifest.update(forbidden_limit=9, derive=False)
    else:
        if manifest['input_sha256'] != B10_SHA:
            raise ValueError('frozen_B10_hash')
        controls(output)
        (output / 'predictions.txt').write_text('Control 5.1 follows the pre-registered GP-11 CONTRACT.\nOnly the checker may establish complete agreement with the withheld target.\n')
        manifest.update(controls={name: 'controls/'+name for name in [*(f'B{n}p' for n in range(4, 10)), 'named', 'regressions']},
                        predictions={'path': 'predictions.txt', 'sha256': sha(output / 'predictions.txt')})
    write(output / 'run.json', manifest)
    write(output / 'assembly.json', {'bundles': receipts, 'assigned': len(assigned), 'unknown': len(unknowns),
          'elapsed_seconds': time.monotonic()-started, 'claim_authorized': False})
    checker(output)
    print(f'ASSEMBLED profile={manifest["profile"]} unknown={len(unknowns)}; completeness requires --require-complete-b10')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('replay')
    r.add_argument('bundle', type=Path)
    r.add_argument('--output', type=Path, required=True)
    c = sub.add_parser('controls')
    c.add_argument('--output', type=Path, required=True)
    a = sub.add_parser('assemble')
    a.add_argument('--bundle', type=Path, action='append', required=True)
    a.add_argument('--overlay', type=Path, action='append', default=[])
    a.add_argument('--output', type=Path, required=True)
    a.add_argument('--sample-union', action='store_true', help='Test assembly only; cannot produce B10 profile')
    check = sub.add_parser('complete')
    check.add_argument('run', type=Path)
    args = p.parse_args()
    if args.command == 'replay':
        replay(args.bundle, args.output)
    elif args.command == 'controls':
        controls(args.output)
    elif args.command == 'assemble':
        assemble(args.bundle, args.overlay, args.output, args.sample_union)
    else:
        checker(args.run, complete=True)


if __name__ == '__main__':
    main()
