"""Summarize real integration artifacts without generating certificates."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from graph6 import contains_subgraph, decode_graph6, load_graph6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = {}
    frozen = Path(__file__).resolve().parents[2] / 'unit-distance-22' / 'data' / 'forbidden-74.g6'
    patterns = [(g, decode_graph6(g)) for g in load_graph6(frozen)]
    for label in ('B8p-F7', 'B9p-F8'):
        run = args.root / label
        if not (run / 'CONTROL.json').exists():
            continue
        records = [json.loads(s) for s in (run / 'records.jsonl').read_text().splitlines()]
        counts = Counter(r['verdict'] for r in records)
        certs = Counter(r['cert'].get('type', 'unknown') for r in records)
        unknowns = [r for r in records if r['verdict'] == 'unknown']
        diagnostics = []
        for row in unknowns:
            n, mask = decode_graph6(row['g6'])
            matches = [g for g, (pn, pm) in patterns
                       if contains_subgraph(pn, pm, n, mask)]
            history = row['cert']['budget'].get('history', [])
            latest = {kind: next((h for h in reversed(history) if h['kind'] == kind), None)
                      for kind in ('embed', 'refute')}
            diagnostics.append({'g6': row['g6'], 'matching_forbidden': matches,
                                'expected': 'refuted' if matches else 'embedded',
                                'latest': latest, 'attempts': history})
        requests = []
        for command in sorted((run / 'requests').glob('*/command.json')):
            value = json.loads(command.read_text())
            argv = value['command']
            code = command.parent
            log = (code / 'producer.log').read_text().splitlines()
            status = json.loads(log[-1])['exit_status']
            rows = [json.loads(s) for s in (code / 'records.jsonl').read_text().splitlines()] if (code / 'records.jsonl').exists() else []
            requested = load_graph6(code / 'input.g6')
            coverage_ok = sorted(r['g6'] for r in rows) == sorted(requested)
            unknown_path = code / 'unknown.g6'
            unknown_ok = unknown_path.exists() and load_graph6(unknown_path) == sorted(
                r['g6'] for r in rows if r['verdict'] == 'unknown')
            requests.append({'directory': str(code), 'producer': Path(argv[1]).name,
                             'budget': float(argv[argv.index('--time-limit') + 1]),
                             'sample_count': value['sample_count'], 'status': status,
                             'coverage_ok': coverage_ok, 'unknown_projection_ok': unknown_ok,
                             'counts': dict(Counter(r['verdict'] for r in rows))})
        checker_report = run / 'checked' / 'report.json'
        result[label] = {'counts': dict(counts), 'certificate_types': dict(certs),
                         'control': json.loads((run / 'CONTROL.json').read_text()),
                         'checker': json.loads(checker_report.read_text()) if checker_report.exists() else None,
                         'unknowns': unknowns, 'unknown_diagnostics': diagnostics,
                         'unknown_expected_counts': dict(Counter(d['expected'] for d in diagnostics)),
                         'requests': requests}
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({label: {'counts': value['counts'], 'certificate_types': value['certificate_types'],
                             'unknown_g6': [r['g6'] for r in value['unknowns']],
                             'unknown_expected_counts': value['unknown_expected_counts'],
                             'checker_final_line': value['control']['checker_final_line'],
                             'request_count': len(value['requests']),
                             'request_coverage_ok': all(r['coverage_ok'] and r['unknown_projection_ok']
                                                        for r in value['requests']),
                             'nonzero_producer_statuses': [r for r in value['requests'] if r['status']]}
                      for label, value in result.items()}, sort_keys=True))


if __name__ == '__main__':
    main()
