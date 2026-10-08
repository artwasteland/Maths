#!/usr/bin/env python3
"""Own-rule controls and a receipt assembled only after every G0 check passes."""

import json
from pathlib import Path
import re
import shutil
import sys
import time

from guard import SCRATCH, run
from run_recount import (B11_SHA256, DATA, ENV, FROZEN, HERE, ROOT, checked, compare,
                         replay, write_json)
from verify import encode, graph6, sha256


def stable(receipt):
    return {k: v for k, v in receipt.items() if k != 'wall_seconds'}


def controls():
    inputs = SCRATCH / 'control.inputs.g6'
    survivors = SCRATCH / 'control.survivors.g6'
    witnesses = SCRATCH / 'control.witnesses.tsv'
    independent = SCRATCH / 'independent.sorted.g6'
    baseline_replay = replay(inputs, survivors, witnesses, 'control-baseline-replay')
    baseline_lists = compare(FROZEN, independent, 'control-baseline-lists')
    chunk0 = json.loads((SCRATCH / 'chunks.jsonl').read_text().splitlines()[0])
    if any(baseline_replay[k] != chunk0[k] for k in stable(baseline_replay)):
        raise RuntimeError('real control chunk differs from its original replay receipt')
    witness_args = [sys.executable, str(HERE / 'verify.py'), 'replay',
                    '--patterns', str(DATA / 'forbidden-398.json'), '--inputs', str(inputs)]
    outcomes = []

    def expect(name, command, message, mutation):
        output = SCRATCH / f'{name}.stdout'
        errors = SCRATCH / f'{name}.stderr'
        try:
            with output.open('wb') as out, errors.open('wb') as err:
                run(command, stdout=out, stderr=err, env=ENV)
        except RuntimeError as error:
            if not str(error).startswith('child exited 1:'):
                raise
        else:
            raise RuntimeError(f'{name}: red control was accepted')
        actual = errors.read_text().rstrip('\n')
        if actual != message or output.read_bytes():
            raise RuntimeError(f'{name}: wrong rejection: {actual!r}')
        # Restore the entire real chunk and both full survivor lists after each red.
        green_replay = replay(inputs, survivors, witnesses, f'{name}-restored-replay')
        green_lists = compare(FROZEN, independent, f'{name}-restored-lists')
        if stable(green_replay) != stable(baseline_replay) or green_lists != baseline_lists:
            raise RuntimeError(f'{name}: original result did not return')
        outcomes.append({'name': name, 'status': 'PASS', 'exact_message': actual,
                         'mutation': mutation, 'restored_replay': green_replay,
                         'restored_lists': green_lists})

    bad_witness = SCRATCH / 'red-injective.tsv'
    with witnesses.open('rb') as source, bad_witness.open('wb') as target:
        fields = source.readline().rstrip(b'\n').split(b'\t')
        entries = fields[2].split(b',')
        entries[1] = entries[0]
        fields[2] = b','.join(entries)
        target.write(b'\t'.join(fields) + b'\n')
        shutil.copyfileobj(source, target)
    expect('red-injectivity', witness_args + ['--survivors', str(survivors), '--witnesses', str(bad_witness)],
           'REJECT: line 1: map is not injective', 'map[1] := map[0] in first real witness')
    bad_witness.unlink()

    with inputs.open('rb') as source:
        first = source.readline()
    with witnesses.open('rb') as source:
        rejected_first = source.readline().split(b'\t', 1)[0] + b'\n' == first
    original = witnesses if rejected_first else survivors
    omitted = SCRATCH / 'red-coverage-output'
    with original.open('rb') as source, omitted.open('wb') as target:
        source.readline()
        shutil.copyfileobj(source, target)
    expect('red-coverage', witness_args +
           ['--survivors', str(survivors if rejected_first else omitted),
            '--witnesses', str(omitted if rejected_first else witnesses)],
           'REJECT: coverage: input 1 occurs in neither output class',
           {'omitted_host': first.decode().strip(), 'removed_from': 'witnesses' if rejected_first else 'survivors'})
    omitted.unlink()

    values = independent.read_bytes().splitlines()
    original = values[0]
    n, edges = graph6(original)
    replacement = None
    for v in range(1, n):
        for u in range(v):
            if (u, v) in edges:
                continue
            (SCRATCH / 'red-list-candidate.g6').write_bytes(encode(n, edges + [(u, v)]) + b'\n')
            checked(['nauty-labelg', '-q'], 'red-list-labelg', SCRATCH / 'red-list-candidate.g6',
                    SCRATCH / 'red-list-canonical.g6')
            candidate = (SCRATCH / 'red-list-canonical.g6').read_bytes().rstrip(b'\n')
            if candidate not in values:
                replacement = candidate
                break
        if replacement is not None:
            break
    if replacement is None:
        raise RuntimeError('cannot construct a distinct canonical graph6 list mutation')
    graph6(replacement)
    altered = SCRATCH / 'red-list.g6'
    altered.write_bytes(b''.join(s + b'\n' for s in sorted([replacement] + values[1:])))
    expect('red-list-equality', [sys.executable, str(HERE / 'verify.py'), 'compare', str(FROZEN), str(altered)],
           'REJECT: list equality: canonical survivor bytes differ',
           {'original': original.decode(), 'replacement': replacement.decode(),
            'method': 'add one missing edge, labelg defaults, re-sort', 'count_preserved': len(values)})
    altered.unlink()
    write_json(SCRATCH / 'controls.json', {'status': 'PASS', 'results': outcomes})


def finalize():
    provenance = json.loads((SCRATCH / 'provenance.json').read_bytes())
    anchor = json.loads((SCRATCH / 'anchor11.json').read_bytes())
    log = (SCRATCH / 'anchor11.stderr').read_text()
    found = re.search(r'>Z (\d+) graphs generated in ([0-9.]+) sec', log)
    if not found or int(found[1]) != 900969091:
        raise RuntimeError('missing full biconnected anchor')
    anchor.update(count=int(found[1]), expected=900969091, geng_cpu_seconds=float(found[2]),
                  OEIS='https://oeis.org/A002218/b002218.txt', status='ACCEPT', geng_stderr=log)
    write_json(SCRATCH / 'anchor11.json', anchor)
    census = json.loads((SCRATCH / 'census.json').read_bytes())
    independent = json.loads((SCRATCH / 'independent.json').read_bytes())
    controls = json.loads((SCRATCH / 'controls.json').read_bytes())
    lower = json.loads((SCRATCH / 'lower.json').read_bytes())
    chunks = [json.loads(row) for row in (SCRATCH / 'chunks.jsonl').read_text().splitlines()]
    first = 1
    totals = {'input': 0, 'survivors': 0, 'replayed': 0}
    for number, chunk in enumerate(chunks):
        if chunk['status'] != 'ACCEPT' or chunk['chunk'] != number or chunk['first_input'] != first:
            raise RuntimeError('chunk manifest coverage is incomplete')
        if chunk['last_input'] - first + 1 != chunk['input']:
            raise RuntimeError('chunk manifest interval size is wrong')
        if chunk['input'] != chunk['survivors'] + chunk['replayed']:
            raise RuntimeError('chunk manifest output counts do not cover the input')
        if chunk['input_sha256'] != chunk['union_sha256']:
            raise RuntimeError('chunk manifest union differs from its input')
        first = chunk['last_input'] + 1
        for key in totals:
            totals[key] += chunk[key]
    if totals != {'input': 68232100, 'survivors': 448708, 'replayed': 67783392}:
        raise RuntimeError('replay totals disagree with the registered census')
    if len(chunks) != census['chunks'] or sha256(SCRATCH / 'hosts.g6') != census['input_sha256']:
        raise RuntimeError('manifest differs from its generator stream')
    if controls['status'] != 'PASS' or len(controls['results']) != 3:
        raise RuntimeError('own-rule controls are incomplete')
    equality = compare(FROZEN, SCRATCH / 'independent.sorted.g6', 'final-equality')
    if equality['actual_sha256'] != B11_SHA256:
        raise RuntimeError('B11 differs from the architect generation')
    compare(FROZEN, SCRATCH / 'primary.sorted.g6', 'final-primary-equality')
    # Include every guarded command, so peak scratch and memory claims cover all phases.
    timings = {p.name: json.loads(p.read_bytes()) for p in SCRATCH.glob('*.time.json')}
    resources = list(timings.values()) + [anchor]
    resources += [c['filter_timing'] for c in chunks] + [c['replay_guard'] for c in chunks]
    result = {'gate': 'G0', 'status': 'PASS', 'scope': 'input freeze and recount only',
              'frozen_sha256': sha256(FROZEN), 'independent_sha256': equality['actual_sha256'],
              'provenance': provenance, 'anchor': anchor, 'census': census,
              'independent': independent, 'controls': controls, 'lower': lower,
              'replay': dict(totals, chunks=len(chunks),
                             wall_seconds=round(sum(c['wall_seconds'] for c in chunks), 6),
                             guarded_wall_seconds=round(sum(c['replay_guard']['wall_seconds'] for c in chunks), 6),
                             filter_wall_seconds=round(sum(c['filter_timing']['wall_seconds'] for c in chunks), 6),
                             chunks_sha256=sha256(SCRATCH / 'chunks.jsonl')),
              'resources': {'min_MemAvailable_kib': min(r['min_MemAvailable_kib'] for r in resources),
                            'peak_scratch_bytes': max(r['peak_scratch_bytes'] for r in resources),
                            'heavy_processes_at_once': 1},
              'timings': timings}
    write_json(SCRATCH / 'receipt.json', result)


if __name__ == '__main__':
    controls()
