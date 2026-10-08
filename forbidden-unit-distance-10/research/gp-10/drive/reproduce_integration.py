"""Reproduce known-pointer and stale-output failures using a real control run."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from driver import _write_known_refuted
from integration import invoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = {r['g6']: r for r in map(json.loads, (args.run / 'records.jsonl').read_text().splitlines())}
    (args.out / 'empty.g6').write_text('')
    _write_known_refuted(args.out / 'supported.jsonl', records)
    full = [r for r in records.values() if r['verdict'] == 'refuted']
    (args.out / 'with-pointers.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in full))
    script = Path(__file__).resolve().parents[1] / 'refute' / 'gp10refute.py'

    def attempt(name, known, seconds, output_name):
        argv = [str(args.out / 'empty.g6'), '--out', str(args.out / (output_name + '.jsonl')),
                '--unknown', str(args.out / (output_name + '.unknown.g6')),
                '--forbidden', str(args.run / 'forbidden-in-force.json'),
                '--refuted', str(args.out / known), '--time-limit', str(seconds), '--methods', 'tree']
        log = args.out / (name + '.log')
        status = invoke(script, argv, log)
        return {'status': status, 'log': str(log), 'tail': log.read_text().splitlines()[-4:]}

    good = attempt('supported', 'supported.jsonl', 1, 'good')
    bad = attempt('with-pointers', 'with-pointers.jsonl', 1, 'bad')
    stale = attempt('changed-budget', 'supported.jsonl', 2, 'good')
    # A one-field mutation of a genuine tree record also exercises the exact
    # unsupported-type dispatch reason independently of the aggregate stream.
    tree = next(r for r in full if r['cert']['type'] == 'tree')
    (args.out / 'tree.jsonl').write_text(json.dumps(tree) + '\n')
    mutation = json.loads(json.dumps(tree))
    mutation['cert']['type'] = 'sub'
    (args.out / 'tree-mutated.jsonl').write_text(json.dumps(mutation) + '\n')
    positive = attempt('tree-positive', 'tree.jsonl', 1, 'tree-positive')
    negative = attempt('tree-type-mutation', 'tree-mutated.jsonl', 1, 'tree-mutation-output')
    assert good['status'] == positive['status'] == 0
    assert bad['status'] == negative['status'] == stale['status'] == 2
    assert 'resume configuration or source changed' in Path(stale['log']).read_text()
    assert 'algebra: invalid type' in Path(bad['log']).read_text()
    assert 'algebra: invalid type' in Path(negative['log']).read_text()
    # Store exact exception wording for review instead of guessing from exit 2.
    result = {'supported': good, 'with_pointers': bad, 'changed_budget': stale,
              'tree_positive': positive, 'tree_type_mutation': negative}
    (args.out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
