"""Reproduce the Round 3 read-only seed discovery, assembly and official sample check."""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import resource
import time

from driver import _cli
from graph6 import _canonicalize_cached
from integration import configure, invoke
from seeds import CHECKER

GP = Path(__file__).resolve().parents[1]
EMBED = Path('<repo>/research/gp-10/embed/results')
REFUTE = Path('<repo>/research/gp-10/refute/evidence')
CAND = Path('<scratch>/scratchpad/cand')
REFUTE_CAND = Path('/tmp/gp10-refute/cand')
MINIMAL = Path('<repo>/research/gp-10/runs/M10-minimal/records.jsonl')


def discover():
    paths = [EMBED / 'union-records.jsonl', EMBED / 'round2/union-records.jsonl',
             EMBED / 'round3/union-records.jsonl']
    missing = []
    if (EMBED / 'round4').exists():
        paths += sorted((EMBED / 'round4').rglob('*.jsonl'))
    else:
        missing.append(str(EMBED / 'round4'))
    paths += [CAND / 'tree5.jsonl', CAND / 'emb.jsonl']
    paths += sorted(REFUTE.rglob('*.jsonl'))
    if REFUTE_CAND.exists():
        paths += sorted(REFUTE_CAND.rglob('*.jsonl'))
    else:
        missing.append(str(REFUTE_CAND))
    paths.append(MINIMAL)
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    return paths, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--poset', type=Path)
    args = parser.parse_args()
    configure()
    run = args.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    paths, missing = discover()
    (run / 'DISCOVERY.json').write_text(json.dumps({
        'ordered_seed_paths': list(map(str, paths)), 'optional_missing': missing,
        'policy': 'brief order; sorted recursive JSONL within optional directories; no source writes',
    }, indent=2) + '\n')
    (run / 'PREDICTIONS.md').write_text(
        '# Round 3 B10 assembly predictions\n\n'
        'Written before reading seed contents or running assembly. These are estimates, not results.\n\n'
        '- Input: 33162 graphs.\n- Predicted embedded: 30000.\n'
        '- Predicted refuted: 1000.\n- Predicted unknown: 2162.\n'
        '- Basis: rough prior that most input graphs embed; no seed-count measurement.\n'
        '- Time model: one serial driver job, dependency-closed seed samples of at most 128 roots, '
        'then one official sample-profile check over the full B10 input with F9 and derive true. '
        'No producer search. Existing poset may be reused.\n'
        '- B10-profile acceptance is gated on genuine replayable controls. They are not fabricated here.\n')
    forbidden = GP.parent / 'unit-distance-22/data/forbidden-74.json'
    argv = ['--input', str(GP / 'data/B10.g6'), '--run-dir', str(run),
            '--forbidden', str(forbidden), '--forbidden-g6', str(forbidden.with_suffix('.g6')),
            '--processes', '1', '--validate-seeds', '--no-producers', '--profile', 'B10', '--derive']
    if args.poset:
        argv += ['--poset', str(args.poset.resolve())]
    for path in paths:
        argv += ['--seed', str(path)]
    (run / 'COMMAND.json').write_text(json.dumps(argv, indent=2) + '\n')
    started = time.monotonic()
    print(json.dumps({'event': 'assembly-start', 'seed_files': len(paths), 'run': str(run)}), flush=True)
    _cli(argv)
    assembly_seconds = time.monotonic() - started
    _canonicalize_cached.cache_clear()
    gc.collect()
    print(json.dumps({'event': 'full-B10-sample-check-start', 'derive': True, 'forbidden_limit': 9,
                      'assembly_seconds': assembly_seconds}), flush=True)
    status = invoke(CHECKER, [str(run / 'sample')], run / 'sample/checker.log')
    report_path = run / 'sample/checked/report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    final = [line for line in (run / 'sample/checker.log').read_text().splitlines()
             if line.startswith(('ACCEPT run ', 'REJECT run '))]
    seed_report = json.loads((run / 'seeds/SEEDS.json').read_text())
    counts = Counter()
    cert_types = Counter()
    with (run / 'records.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            counts[row['verdict']] += 1
            cert_types[row['cert'].get('type', 'unknown')] += 1
    conditional = len(report.get('conditional_minimal', []))
    minimal_path = run / 'sample/checked/minimal.g6'
    minimal = len(minimal_path.read_text().splitlines()) if minimal_path.exists() else None
    result = {'status': status, 'final_line': final[-1] if final else None,
              'record_counts': dict(counts), 'certificate_types': dict(cert_types),
              'derived_minimal_count': minimal, 'conditional_count': conditional,
              'proved_minimal_count': None if minimal is None else minimal - conditional,
              'unknown_count': len((run / 'UNKNOWN.g6').read_text().splitlines()),
              'seeds_selected': seed_report['selected_count'],
              'seeds_accepted': seed_report['accepted_count'],
              'seeds_rejected': seed_report['rejected_count'],
              'seed_validation_samples': len(seed_report['checks']),
              'assembly_seconds': assembly_seconds, 'total_seconds': time.monotonic() - started,
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'address_space_limit_bytes': resource.getrlimit(resource.RLIMIT_AS)[0],
              'input_sha256': hashlib.sha256((GP / 'data/B10.g6').read_bytes()).hexdigest(),
              'checker_report': str(report_path), 'checker_report_summary': report,
              'B10_profile_checked': False,
              'B10_profile_note': 'Draft manifest only: genuine replayable controls still required.'}
    (run / 'ASSEMBLY.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'event': 'assembly-finished', **result}, sort_keys=True), flush=True)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
