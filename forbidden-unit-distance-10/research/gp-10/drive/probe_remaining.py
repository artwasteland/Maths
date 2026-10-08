"""Bounded real-producer probes of unresolved records; never certify a control."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from driver import _run_batches, PYTHON_DEFAULT
from graph6 import load_graph6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--kind', choices=('embed', 'refute'), required=True)
    parser.add_argument('--methods', required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--from-g6', type=Path)
    parser.add_argument('--extra', action='append', default=[])
    args = parser.parse_args()
    if args.seconds <= 0 or args.count < 1 or args.seconds * args.count > 240:
        parser.error('positive probe limits must total at most 240 nominal seconds')
    state = json.loads((args.run / 'STATE.json').read_text())
    graphs = sorted(state['unknown'])
    if args.from_g6:
        selected = set(load_graph6(args.from_g6))
        graphs = [g for g in graphs if g in selected]
    graphs = graphs[:args.count]
    args.out.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parents[1] / args.kind / ('gp10' + args.kind + '.py')
    result = _run_batches(args.kind, graphs, 0, args.seconds, args.out, 1,
                          PYTHON_DEFAULT, str(script), args.run / 'forbidden-in-force.json',
                          state['resolved'], state['unknown'],
                          ['--methods', args.methods, *args.extra])
    value = {'graphs': graphs, 'methods': args.methods, 'seconds': args.seconds,
             'records': result.records, 'unknown': result.unknown, 'logs': result.logs,
             'note': 'Diagnostic only; the control STATE and verdicts were not changed.'}
    (args.out / 'probe.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'graphs': graphs, 'resolved': list(result.records),
                      'unknown': list(result.unknown), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
