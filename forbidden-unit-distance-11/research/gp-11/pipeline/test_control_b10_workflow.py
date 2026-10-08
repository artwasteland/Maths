#!/usr/bin/env python3
"""Small real certificate tests of resume, shard assembly and checker isolation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    results = {}

    def call(name, command, error=None):
        with (work / (name+'.log')).open('w') as log:
            process = subprocess.run([sys.executable, '-B', *map(str, command)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        text = (work / (name+'.log')).read_text()
        if error is None:
            assert process.returncode == 0, text[-2500:]
        else:
            assert process.returncode != 0 and error in text, text[-2500:]
        results[name] = {'exit': process.returncode, 'expected_rule': error}

    bundles = []
    for index in (0, 1):
        bundle = work / f'shard-{index}'
        command = [HERE / 'control_b10.py', '--state', work / f'state-{index}', '--output', bundle,
                   '--sample', '12', '--seed', '20261001', '--shard-count', '2', '--shard-index', str(index),
                   '--policy', 'cheap', '--validate-index']
        call(f'run-{index}', command)
        names = ('records.jsonl.gz', 'assigned.g6', 'input.g6', 'UNKNOWN.g6', 'attempts.jsonl.gz', 'frontier.jsonl.gz', 'packets.jsonl.gz')
        before = {name: hashlib.sha256((bundle/name).read_bytes()).hexdigest() for name in names}
        call(f'resume-{index}', command + ['--resume'])
        assert before == {name: hashlib.sha256((bundle/name).read_bytes()).hexdigest() for name in names}
        results[f'resume-{index}']['byte_identical_artifacts'] = list(names)
        call(f'replay-{index}', [HERE / 'control_b10_bundle.py', 'replay', bundle, '--output', work / f'replay-{index}'])
        bundles.append(bundle)
    command = [HERE / 'control_b10_bundle.py', 'assemble', '--bundle', bundles[0], '--bundle', bundles[1]]
    call('assemble', command + ['--sample-union', '--output', work / 'merged'])
    report = json.loads((work / 'merged/checked/report.json').read_text())
    assert report['profile'] == 'sample' and report['status'] == 'ACCEPT' and report['direct_rejections'] == 0
    results['assemble']['checker_counts'] = report['counts']
    call('missing_population', command + ['--output', work / 'missing'], 'shard_union_coverage')
    call('duplicate_assignment', [HERE / 'control_b10_bundle.py', 'assemble', '--bundle', bundles[0], '--bundle', bundles[0],
        '--sample-union', '--output', work / 'duplicate'], 'shard_union_duplicate')
    call('no_sample_complete', [HERE / 'control_b10_bundle.py', 'complete', work / 'merged'], 'checker_rejected')
    # A retained receipt never excuses byte corruption.
    target = bundles[0] / 'UNKNOWN.g6'
    raw = target.read_bytes()
    target.write_bytes(raw + b'Bw\n')
    call('corrupt_bundle', [HERE / 'control_b10_bundle.py', 'replay', bundles[0], '--output', work / 'corrupt-replay'], 'bundle_artifact_hash:UNKNOWN.g6')
    target.write_bytes(raw)
    call('restored_bundle', [HERE / 'control_b10_bundle.py', 'replay', bundles[0], '--output', work / 'restored-replay'])
    # The tree containing named order-ten answers is created only after every
    # producer subprocess has exited. It is never supplied as a producer base.
    call('checker_controls', [HERE / 'control_b10_bundle.py', 'controls', '--output', work / 'checker-only'])
    control_reports = {p.parent.parent.name: json.loads(p.read_text()) for p in (work / 'checker-only/controls').glob('*/checked/report.json')}
    assert len(control_reports) == 8 and all(r['status'] == 'ACCEPT' for r in control_reports.values())
    results['checker_controls']['profiles'] = sorted(control_reports)
    (work / 'results.json').write_text(json.dumps({'status': 'PASS', 'tests': results}, indent=2)+'\n')
    print('PASS control51 workflow; resume bytes, two shards, checker replay, own-rule reds, eight checker prerequisites')


if __name__ == '__main__':
    main()
