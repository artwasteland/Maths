#!/usr/bin/env python3
"""Round-two bounded batches, durable artifacts, and merged checker inputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from fractions import Fraction
from msolve_exact import limits, timer, Deadline, invoke, certify, prepare_binary, sha, decode_output
from rigid_system import make_system, public_system, generic_rank
from exact import verify
from round2_phase import isolated

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
OUT = RESULTS / 'round2'
SAMPLES = ('maximal', 'B9p', 'uniform500')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)


def task_id(code): return hashlib.sha256(code.encode()).hexdigest()[:20]


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    labels = json.loads((RESULTS / 'B9p/labels.json').read_text())
    manifest = {'samples': {}, 'order': list(SAMPLES), 'first_cap_seconds': 20,
                'second_cap_seconds': 120, 'seed': 'sha256(g6)',
                'process_ceiling': 2, 'address_space_bytes': 1000000 * 1024}
    for sample in SAMPLES:
        source = RESULTS / sample / 'UNKNOWN.g6'
        codes = source.read_text().splitlines()
        if sample == 'B9p': codes = [c for c in codes if labels[c] == 'F9_free']
        text = ''.join(c + '\n' for c in codes)
        directory = OUT / sample; directory.mkdir(exist_ok=True)
        (directory / 'input.g6').write_text(text)
        manifest['samples'][sample] = {'count': len(codes), 'input_sha256': sha(text.encode()),
            'round1_unknown_source': str(source.relative_to(HERE)),
            'round1_unknown_sha256': sha(source.read_bytes())}
    executable, provenance = prepare_binary()
    manifest['msolve'] = provenance
    manifest['temporary_executable'] = str(executable)
    write_json(OUT / 'manifest.json', manifest)
    return manifest


def stored_system(system):
    result = public_system(system)
    result['text'] = system['text']
    result['terms'] = [[[list(powers), str(coef)] for powers, coef in p.items()]
                       for p in system['polynomials']]
    return result


def load_system(path):
    system = json.loads(path.read_text())
    system['polynomials'] = [{tuple(powers): Fraction(coef) for powers, coef in p}
                             for p in system.pop('terms')]
    return system


def solve_one(code, sample, seconds=20, pass_number=1):
    directory = OUT / sample / ('pass' + str(pass_number)) / task_id(code)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / 'record.json').exists():
        record = json.loads((directory / 'record.json').read_text())
        if record['g6'] != code: raise ValueError('resume:graph_mismatch')
        if record['verdict'] == 'embedded': verify(code, record['cert'], max_refinements=256)
        return record, json.loads((directory / 'stats.json').read_text())
    started = time.monotonic()
    stats = {'g6': code, 'sample': sample, 'pass': pass_number, 'cap_seconds': seconds,
             'triage': False, 'timeout': False}
    candidate = None
    try:
        prep_started = time.monotonic()
        if pass_number == 1:
            rank, evidence = generic_rank(code)
            from exact import graph6
            stats.update(rank=rank, k=2 * graph6(code)[0] - 3 - rank, rank_evidence=evidence)
            saved = isolated(lambda: stored_system(make_system(code)), 8)
            system_path = directory / 'system.json'
            write_json(system_path, saved)
            system = load_system(system_path)
        else:
            system = load_system(OUT / sample / 'pass1' / task_id(code) / 'system.json')
        stats['preparation_seconds'] = time.monotonic() - prep_started
        stats.update(k=system['k'], rank=system['rank'], pins=system['pins'])
        write_json(directory / 'system.json', stored_system(system))
        raw, call = invoke(system, directory, seconds, parse=False)
        stats.update(call)
        if raw is not None:
            checking_started = time.monotonic()
            def convert():
                parsed = decode_output(raw, system['variables'],
                    progress=lambda row: write_json(directory / 'conversion-progress.json', row))
                return certify(code, system, parsed)
            candidate, checked = isolated(convert, 15)
            stats.update(checked)
            stats['certification_seconds'] = time.monotonic() - checking_started
    except Deadline:
        stats['reason'] = 'preparation_or_certification_deadline'
    except Exception as exc:
        stats['reason'] = type(exc).__name__ + ':' + str(exc)[:1000]
    if (directory / 'conversion-progress.json').exists():
        progress = json.loads((directory / 'conversion-progress.json').read_text())
        stats.update({key: value for key, value in progress.items() if key not in stats})
    stats['wall_seconds'] = time.monotonic() - started
    if candidate is not None:
        record = {'g6': code, 'verdict': 'embedded', 'cert': candidate}
    else:
        record = {'g6': code, 'verdict': 'unknown', 'cert': {'reason': stats.get('reason', 'no_candidate'),
            'budget': {'method': 'round2_msolve', 'pass': pass_number,
                       'msolve_cap_seconds': seconds, 'wall_seconds': stats['wall_seconds']}}}
    write_json(directory / 'stats.json', stats)
    write_json(directory / 'record.json', record)
    return record, stats


def batch(sample, start, stop, seconds, pass_number):
    codes = (OUT / sample / 'input.g6').read_text().splitlines()
    if pass_number == 2:
        codes = [c for c in codes if (OUT / sample / 'pass1' / task_id(c) / 'stats.json').exists()
                 and json.loads((OUT / sample / 'pass1' / task_id(c) / 'stats.json').read_text())['timeout']]
    chosen = codes[start:stop]
    # Imports before fork share immutable library pages and avoid repeated startup.
    import sympy
    import scipy.optimize
    batch_started = time.monotonic()
    counts = Counter()
    for index, code in enumerate(chosen, start):
        record, stats = solve_one(code, sample, seconds, pass_number)
        counts[record['verdict']] += 1
        print(json.dumps({'index': index, 'g6': code, 'verdict': record['verdict'],
            'k': stats.get('k'), 'degree': stats.get('degree'), 'reason': stats.get('reason', '').split('{', 1)[0],
            'seconds': stats['wall_seconds']}), flush=True)
    result = {'sample': sample, 'start': start, 'stop': stop, 'actual_count': len(chosen),
              'pass': pass_number, 'cap_seconds': seconds, 'counts': dict(counts),
              'wall_seconds': time.monotonic() - batch_started}
    write_json(OUT / 'batches' / f'{sample}-pass{pass_number}-{start}-{stop}.json', result)
    print(json.dumps({'batch': result}), flush=True)


def collect():
    all_records, all_stats, summary, triage = {}, [], {}, {}
    timeout_rows = []
    for sample in SAMPLES:
        codes = (OUT / sample / 'input.g6').read_text().splitlines()
        records = []
        sample_stats = []
        for code in codes:
            final = None
            for pass_number in (1, 2):
                directory = OUT / sample / ('pass' + str(pass_number)) / task_id(code)
                if not (directory / 'record.json').exists(): continue
                record = json.loads((directory / 'record.json').read_text())
                stats = json.loads((directory / 'stats.json').read_text())
                if final is None or final['verdict'] == 'unknown' or record['verdict'] == 'embedded': final = record
                all_stats.append(stats); sample_stats.append(stats)
                if stats.get('timeout'): timeout_rows.append({'g6': code, 'sample': sample, 'pass': pass_number})
                if stats.get('triage'): triage[code] = stats
            if final is None:
                final = {'g6': code, 'verdict': 'unknown', 'cert': {'reason': 'round2_not_attempted', 'budget': {}}}
            if final['verdict'] == 'embedded': verify(code, final['cert'], max_refinements=256)
            records.append(final)
            if code not in all_records or final['verdict'] == 'embedded': all_records[code] = final
        (OUT / sample / 'records.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))
        (OUT / sample / 'UNKNOWN.g6').write_text(''.join(r['g6'] + '\n' for r in records if r['verdict'] == 'unknown'))
        summary[sample] = {'requested': len(codes), 'attempted': len({r['g6'] for r in sample_stats}),
            'embedded': sum(r['verdict'] == 'embedded' for r in records),
            'unknown': sum(r['verdict'] == 'unknown' for r in records),
            'first_timeouts': sum(r.get('timeout', False) for r in sample_stats if r['pass'] == 1),
            'second_attempted': sum(r['pass'] == 2 for r in sample_stats),
            'rigid_triage': len({r['g6'] for r in sample_stats if r.get('triage')}),
            'reason_counts': dict(Counter(r.get('reason') for r in sample_stats)),
            'reason_categories': dict(Counter(r.get('reason', '').split('{', 1)[0] for r in sample_stats)),
            'generic_dof': dict(sorted(Counter(r['k'] for r in sample_stats if r['pass'] == 1 and 'k' in r).items())),
            'msolve_calls': sum('msolve_seconds' in r for r in sample_stats),
            'pinned_calls': sum(bool(r.get('pins')) and 'msolve_seconds' in r for r in sample_stats),
            'pinned_successes': sum(r.get('reason') == 'exact_embedding' and bool(r.get('pins')) for r in sample_stats),
            'eliminant_degrees': dict(sorted(Counter(r['degree'] for r in sample_stats if 'degree' in r).items())),
            'certificate_degrees': dict(sorted(Counter(len(r['cert']['field']['minpoly']) - 1 for r in records if r['verdict'] == 'embedded').items())),
            'wall_seconds_sum': sum(r['wall_seconds'] for r in sample_stats),
            'msolve_seconds_sum': sum(r.get('msolve_seconds', 0) for r in sample_stats)}
    old = {r['g6']: r for r in map(json.loads, (RESULTS / 'union-records.jsonl').read_text().splitlines())}
    merged = dict(old)
    for code, record in all_records.items():
        if code not in merged or record['verdict'] == 'embedded' or merged[code]['verdict'] == 'unknown':
            merged[code] = record
    new_codes = sorted(c for c in merged if merged[c]['verdict'] == 'embedded' and old.get(c, {}).get('verdict') != 'embedded')
    for code in triage:
        if merged[code]['verdict'] == 'embedded': raise ValueError('triage_conflicts_with_embedding:' + code)
    (OUT / 'rigid-no-embedding.g6').write_text(''.join(c + '\n' for c in sorted(triage)))
    (OUT / 'rigid-no-embedding.jsonl').write_text(''.join(json.dumps(triage[c]) + '\n' for c in sorted(triage)))
    (OUT / 'timeouts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in timeout_rows))
    for number in (1, 2):
        (OUT / f'timeouts-pass{number}.g6').write_text(''.join(c + '\n' for c in sorted({r['g6'] for r in timeout_rows if r['pass'] == number})))
    (OUT / 'new-embedded.g6').write_text(''.join(c + '\n' for c in new_codes))
    (OUT / 'stats.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in all_stats))
    union = ''.join(json.dumps(merged[c]) + '\n' for c in sorted(merged))
    (OUT / 'union-records.jsonl').write_text(union)
    run = OUT / 'run'; run.mkdir(exist_ok=True)
    input_text = ''.join(c + '\n' for c in sorted(merged))
    (run / 'input.g6').write_text(input_text)
    unknown = ''.join(c + '\n' for c in sorted(merged) if merged[c]['verdict'] == 'unknown')
    (run / 'UNKNOWN.g6').write_text(unknown)
    (OUT / 'UNKNOWN.g6').write_text(unknown)
    write_json(run / 'run.json', {'profile': 'sample', 'input': 'input.g6',
        'input_sha256': sha(input_text.encode()), 'records': ['../union-records.jsonl'],
        'unknown': 'UNKNOWN.g6', 'derive': False})
    summary['union'] = {'records': len(merged), 'embedded': sum(r['verdict'] == 'embedded' for r in merged.values()),
        'unknown': sum(r['verdict'] == 'unknown' for r in merged.values()),
        'new_unique_embeddings': len(new_codes), 'rigid_triage': len(triage),
        'round2_unique_inputs': len(all_records), 'union_sha256': sha(union.encode())}
    write_json(OUT / 'summary.json', summary)
    return summary


def main():
    limits()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare'); sub.add_parser('collect')
    run = sub.add_parser('batch')
    run.add_argument('--sample', choices=SAMPLES, required=True)
    run.add_argument('--start', type=int, default=0); run.add_argument('--stop', type=int, required=True)
    run.add_argument('--cap', type=float, default=20)
    run.add_argument('--pass-number', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if args.command == 'prepare': print(json.dumps(prepare(), indent=2))
    elif args.command == 'collect': print(json.dumps(collect(), indent=2))
    else: batch(args.sample, args.start, args.stop, args.cap, args.pass_number)


if __name__ == '__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='input':
        del sys.argv[1]
        from generic_exact import cli
        cli('msolve')
    else: main()
