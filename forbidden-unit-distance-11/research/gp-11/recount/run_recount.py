#!/usr/bin/env python3
"""Reproduce G0 sequentially; all generated working files stay in /tmp/gp11-freeze."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from guard import SCRATCH, run
from verify import encode, graph6, load_patterns, sha256


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'research/unit-distance-22/data'
OLD = ROOT / 'research/gp-10'
FROZEN = HERE.parent / 'data/B11.g6'
F10_SHA256 = '8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c'
B11_SHA256 = 'ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f'
CHUNK_SIZE = 1_000_000
ENV = dict(os.environ, LC_ALL='C', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
           PYTHONDONTWRITEBYTECODE='1')


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def checked(command, name, input_path=None, output_path=None):
    output_path = output_path or SCRATCH / f'{name}.stdout'
    with output_path.open('wb') as output, (SCRATCH / f'{name}.stderr').open('wb') as errors:
        if input_path is None:
            receipt = run(command, stdout=output, stderr=errors, env=ENV)
        else:
            with input_path.open('rb') as source:
                receipt = run(command, stdin=source, stdout=output, stderr=errors, env=ENV)
    write_json(SCRATCH / f'{name}.time.json', receipt)
    return receipt


def canonicalize(source, name):
    canon = SCRATCH / f'{name}.canon.g6'
    target = SCRATCH / f'{name}.sorted.g6'
    checked(['nauty-labelg', '-q'], f'{name}-labelg', source, canon)
    checked(['sort', '--parallel=1', '-S', '64M', '-T', str(SCRATCH), str(canon)],
            f'{name}-sort', output_path=target)
    return target


def compare(expected, actual, name):
    checked([sys.executable, str(HERE / 'verify.py'), 'compare', str(expected), str(actual)], name)
    return json.loads((SCRATCH / f'{name}.stdout').read_bytes())


def replay(inputs, survivors, witnesses, name, order=11):
    checked([sys.executable, str(HERE / 'verify.py'), 'replay',
             '--patterns', str(DATA / 'forbidden-398.json'), '--inputs', str(inputs),
             '--survivors', str(survivors), '--witnesses', str(witnesses), '--order', str(order)], name)
    return json.loads((SCRATCH / f'{name}.stdout').read_bytes())


def source_hashes():
    sources = list(HERE.glob('*.py')) + list(HERE.glob('*.c'))
    sources += [DATA / name for name in ['forbidden-398.json', 'forbidden-398.g6',
                                        'forbidden-74.json', 'tu-gadgets.json']]
    sources += [DATA.parent / 'filter' / name for name in ['udfilter.c', 'udfilter.h']]
    sources += [OLD / 'recount' / name for name in ['matcher.c', 'verify_witness.py']]
    sources += [OLD / 'runs/B10-final-2026-09-25' / name for name in ['L10.g6', 'report.json']]
    sources += list((OLD / 'data').glob('*.g6'))
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}


def prepare():
    if sha256(DATA / 'forbidden-398.json') != F10_SHA256:
        raise RuntimeError('F10 JSON hash mismatch')
    checked(['cc', '-O3', '-std=c11', '-Wall', '-Wextra', '-pedantic', str(HERE / 'matcher.c'),
             '-lz', '-o', str(SCRATCH / 'matcher')], 'compile-independent')
    checked(['cc', '-O3', '-std=c11', '-Wall', '-Wextra', '-pedantic',
             '-I', str(DATA.parent / 'filter'), str(HERE / 'filter.c'),
             str(DATA.parent / 'filter/udfilter.c'), '-o', str(SCRATCH / 'filter')], 'compile-primary')
    patterns = load_patterns(DATA / 'forbidden-398.json')
    if Counter(n for n, _ in patterns) != {4: 1, 5: 1, 6: 1, 7: 3, 8: 13, 9: 55, 10: 324}:
        raise RuntimeError('F10 order histogram mismatch')
    if patterns[0] != (4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]):
        raise RuntimeError('F10 index 0 is not K4')
    rows = [encode(n, edges) + b'\n' for n, edges in patterns]
    (SCRATCH / 'F10.g6').write_bytes(b''.join(rows))
    checked(['nauty-labelg', '-q'], 'patterns-json-labelg', SCRATCH / 'F10.g6', SCRATCH / 'F10.canon.g6')
    checked(['nauty-labelg', '-q'], 'patterns-g6-labelg', DATA / 'forbidden-398.g6', SCRATCH / 'published.canon.g6')
    if (SCRATCH / 'F10.canon.g6').read_bytes() != (SCRATCH / 'published.canon.g6').read_bytes():
        raise RuntimeError('F10 JSON and graph6 member order disagree')
    json_rows = json.loads((DATA / 'forbidden-398.json').read_bytes())
    if json_rows[:74] != json.loads((DATA / 'forbidden-74.json').read_bytes()):
        raise RuntimeError('F10 prefix disagrees with GP74 JSON labels')
    suffix = sorted((SCRATCH / 'F10.canon.g6').read_bytes().splitlines(keepends=True)[74:])
    l10 = OLD / 'runs/B10-final-2026-09-25/L10.g6'
    if b''.join(suffix) != l10.read_bytes():
        raise RuntimeError('F10 suffix disagrees with checker-derived L10')
    report = json.loads((l10.parent / 'report.json').read_bytes())
    if (report['status'], report['counts']['unknown'], report['conditional'], report['minimal_count']) != \
            ('ACCEPT', 0, False, 324):
        raise RuntimeError('GP10 report is incomplete')
    if [s.decode().rstrip('\n') for s in suffix] != report['minimal']:
        raise RuntimeError('GP10 report minimal list disagrees with L10')
    checked(['dpkg-query', '-W', 'nauty'], 'nauty-version')
    if '2.8.8' not in (SCRATCH / 'nauty-version.stdout').read_text():
        raise RuntimeError('nauty 2.8.8 is required')
    versions = {'nauty': (SCRATCH / 'nauty-version.stdout').read_text().strip(),
                'python': sys.version,
                'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0]}
    executables = {name: {'path': shutil.which(name), 'sha256': sha256(shutil.which(name))}
                   for name in ['nauty-geng', 'nauty-labelg', 'sort', 'cc']}
    for name in ['matcher', 'filter']:
        executables[name] = {'path': str(SCRATCH / name), 'sha256': sha256(SCRATCH / name)}
    write_json(SCRATCH / 'provenance.json', {'status': 'ACCEPT', 'sources': source_hashes(),
               'versions': versions, 'executables': executables, 'patterns': len(patterns),
               'F10_g6_sha256': sha256(SCRATCH / 'F10.g6'),
               'prefix_matches_GP74': True, 'suffix_matches_checker_L10': True,
               'JSON_graph6_member_order_matches': True})


def check_provenance():
    saved = json.loads((SCRATCH / 'provenance.json').read_bytes())
    if saved['sources'] != source_hashes():
        raise RuntimeError('sources changed since prepare; rerun prepare')
    for name, record in saved['executables'].items():
        if sha256(record['path']) != record['sha256']:
            raise RuntimeError(f'executable changed since prepare: {name}')
    if sha256(SCRATCH / 'F10.g6') != saved['F10_g6_sha256']:
        raise RuntimeError('JSON-labelled patterns changed since prepare')


def anchor():
    timing = checked(['nauty-geng', '-Cu', '11'], 'anchor11')
    log = (SCRATCH / 'anchor11.stderr').read_text()
    found = re.search(r'>Z (\d+) graphs generated in ([0-9.]+) sec', log)
    if not found or int(found[1]) != 900969091:
        raise RuntimeError(f'A002218(11) mismatch: {log}')
    write_json(SCRATCH / 'anchor11.json', dict(timing, count=int(found[1]),
               geng_cpu_seconds=float(found[2]), OEIS='https://oeis.org/A002218/b002218.txt',
               expected=900969091, status='ACCEPT', geng_stderr=log))


def census():
    checked(['nauty-geng', '-Ck', '11', '11:24'], 'generate11', output_path=SCRATCH / 'hosts.g6')
    total = Counter()
    primary = SCRATCH / 'primary.raw.g6'
    receipts = SCRATCH / 'chunks.jsonl'
    stream_hash = hashlib.sha256()
    first = 1
    with (SCRATCH / 'hosts.g6').open('rb') as source, primary.open('wb') as kept, receipts.open('w') as journal:
        for chunk in range(1000):
            # All order-11 graph6 records have 12 bytes, including the newline.
            data = source.read(CHUNK_SIZE * 12)
            if not data:
                break
            if len(data) % 12:
                raise RuntimeError('generator stream has a partial record')
            stem = 'control' if chunk == 0 else 'current'
            inputs = SCRATCH / f'{stem}.inputs.g6'
            survivors = SCRATCH / f'{stem}.survivors.g6'
            witnesses = SCRATCH / f'{stem}.witnesses.tsv'
            inputs.write_bytes(data)
            stream_hash.update(data)
            count = len(data) // 12
            timing = checked([str(SCRATCH / 'filter'), str(DATA / 'forbidden-398.json'),
                               str(DATA / 'tu-gadgets.json'), str(survivors), str(witnesses)],
                              'chunk-filter', inputs)
            primary_counts = json.loads((SCRATCH / 'chunk-filter.stdout').read_bytes())
            receipt = replay(inputs, survivors, witnesses, 'chunk-replay')
            if (receipt['input'], receipt['survivors'], receipt['replayed']) != \
                    (count, primary_counts['survivors'], primary_counts['removed']):
                raise RuntimeError('chunk census and independent replay counts disagree')
            if receipt['input_sha256'] != receipt['union_sha256']:
                raise RuntimeError('chunk input and output union digests disagree')
            if receipt['input_sha256'] != hashlib.sha256(data).hexdigest():
                raise RuntimeError('chunk bytes disagree with generator stream')
            with survivors.open('rb') as accepted:
                shutil.copyfileobj(accepted, kept)
            receipt.update(chunk=chunk, first_input=first, last_input=first + count - 1,
                           primary_counts=primary_counts, filter_timing=timing,
                           replay_guard=json.loads((SCRATCH / 'chunk-replay.time.json').read_bytes()))
            journal.write(json.dumps(receipt, sort_keys=True) + '\n')
            journal.flush()
            total.update(primary_counts)
            first += count
            print(json.dumps({'chunk': chunk, 'input': count, 'replayed': receipt['replayed'],
                              'survivors': receipt['survivors'], 'total_input': total['input']}), flush=True)
            if chunk:
                inputs.unlink()
                survivors.unlink()
                witnesses.unlink()
        else:
            raise RuntimeError('unexpectedly long host stream')
    if dict(total) != {'input': 68232100, 'pass': 294516, 'removed': 67783392,
                       'tu': 154192, 'survivors': 448708}:
        raise RuntimeError(f'census mismatch: {total}')
    target = canonicalize(primary, 'primary')
    result = compare(FROZEN, target, 'primary-equality')
    if result['actual_sha256'] != B11_SHA256:
        raise RuntimeError('architect B11 digest changed')
    write_json(SCRATCH / 'census.json', {'status': 'ACCEPT', 'counts': dict(total),
               'input_sha256': stream_hash.hexdigest(), 'chunk_size': CHUNK_SIZE,
               'chunks': chunk, 'equality': result})


def match(source, name, max_n=10):
    checked([str(SCRATCH / 'matcher'), '--patterns', str(SCRATCH / 'F10.g6'),
             '--max-pattern-n', str(max_n), '--survivors', str(SCRATCH / f'{name}.raw.g6'),
             '--summary', str(SCRATCH / f'{name}.summary')], name, source)
    return {key: int(value) for key, value in
            (line.split('=') for line in (SCRATCH / f'{name}.summary').read_text().splitlines())}


def independent():
    counts = match(SCRATCH / 'hosts.g6', 'independent')
    if (counts['input_graphs'], counts['removed'], counts['survivors'], counts['patterns']) != \
            (68232100, 67783392, 448708, 398):
        raise RuntimeError(f'independent recount mismatch: {counts}')
    target = canonicalize(SCRATCH / 'independent.raw.g6', 'independent')
    result = compare(FROZEN, target, 'independent-equality')
    compare(SCRATCH / 'primary.sorted.g6', target, 'producer-equality')
    # A second labelling pass must leave every canonical byte unchanged.
    checked(['nauty-labelg', '-q'], 'label-round-trip', target, SCRATCH / 'round-trip.g6')
    compare(target, SCRATCH / 'round-trip.g6', 'round-trip-equality')
    write_json(SCRATCH / 'independent.json', {'status': 'ACCEPT', 'counts': counts, 'equality': result})


def lower():
    results = []
    expected_inputs = {4: 3, 5: 10, 6: 56, 7: 468, 8: 7123, 9: 194066, 10: 9743542}
    for n in range(4, 11):
        name = f'B{n}p' if n < 10 else 'B10'
        hosts = SCRATCH / f'{name}.hosts.g6'
        checked(['nauty-geng', '-C', str(n)], f'{name}-generate', output_path=hosts)
        counts = match(hosts, name, n - 1)
        if counts['input_graphs'] != expected_inputs[n]:
            raise RuntimeError(f'lower-order generator anchor failed: {name}')
        target = canonicalize(SCRATCH / f'{name}.raw.g6', name)
        equality = compare(OLD / f'data/{name}.g6', target, f'{name}-equality')
        results.append({'name': name, 'counts': counts, 'equality': equality,
                        'timing': json.loads((SCRATCH / f'{name}.time.json').read_bytes())})
        if n in (8, 9):
            extra = match(hosts, f'B{n}-F9', 9)
            if extra['survivors'] != {8: 366, 9: 2984}[n]:
                raise RuntimeError(f'GP printed count failed: n={n}')
            results.append({'name': f'B{n}-F9', 'counts': extra,
                            'timing': json.loads((SCRATCH / f'B{n}-F9.time.json').read_bytes())})
        hosts.unlink()
    # K2,3 plus an extra edge contains F10[1] only as a non-induced subgraph.
    n, edges = load_patterns(DATA / 'forbidden-398.json')[1]
    missing = next((u, v) for v in range(1, n) for u in range(v) if (u, v) not in edges)
    host = encode(n, edges + [missing]) + b'\n'
    (SCRATCH / 'noninduced.inputs.g6').write_bytes(host)
    checked([str(SCRATCH / 'matcher'), '--patterns', str(SCRATCH / 'F10.g6'),
             '--survivors', str(SCRATCH / 'noninduced.survivors.g6'),
             '--witness', str(SCRATCH / 'noninduced.witnesses.gz')],
            'noninduced', SCRATCH / 'noninduced.inputs.g6')
    with gzip.open(SCRATCH / 'noninduced.witnesses.gz', 'rb') as source:
        witness = source.read()
    if witness.split(b'\t')[1] != b'1' or (SCRATCH / 'noninduced.survivors.g6').read_bytes():
        raise RuntimeError('matcher missed a non-induced K2,3')
    (SCRATCH / 'noninduced.witnesses.tsv').write_bytes(witness)
    result = replay(SCRATCH / 'noninduced.inputs.g6', SCRATCH / 'noninduced.survivors.g6',
                    SCRATCH / 'noninduced.witnesses.tsv', 'noninduced-replay', n)
    results.append({'name': 'noninduced', 'host': host.decode().strip(), 'replay': result})
    write_json(SCRATCH / 'lower.json', results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['prepare', 'anchor', 'census', 'independent', 'lower',
                                           'controls', 'finalize', 'all'], default='all')
    args = parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    stages = {'prepare': prepare, 'anchor': anchor, 'census': census,
              'independent': independent, 'lower': lower}
    # Imported late so the verifier used in controls stays independent of the producers.
    from controls import controls, finalize
    stages.update(controls=controls, finalize=finalize)
    for name, action in stages.items():
        if args.stage not in ('all', name):
            continue
        if name != 'prepare':
            check_provenance()
        print(f'BEGIN {name}', flush=True)
        action()
        print(f'ACCEPT {name}', flush=True)


if __name__ == '__main__':
    main()
