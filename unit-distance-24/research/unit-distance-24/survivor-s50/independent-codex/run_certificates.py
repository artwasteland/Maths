#!/usr/bin/env python3
"""Replay the unchanged GP-11 CLI; confine its hardcoded scratch directory."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PYTHON = '<repo>/pyenv-gp10/bin/python'
CHECKER = Path('<repo>/research/gp-11/check/gp11check.py')


def main():
    search = json.loads((ROOT / 'search-results.json').read_text())
    runs = ROOT / 'checker-runs'
    runs.mkdir(exist_ok=True)
    scratch = ROOT / 'checker-scratch'
    scratch.mkdir(exist_ok=True)
    results = {
        'checker_path': str(CHECKER),
        'checker_sha256': hashlib.sha256(CHECKER.read_bytes()).hexdigest(),
        'isolation': 'bwrap read-only /, writable workspace, private /tmp with /tmp/gp10-check bound to workspace/checker-scratch',
        'records': [],
    }

    def check(name, raw, damaged=False):
        record = json.loads(raw)
        directory = Path(tempfile.mkdtemp(prefix=name + '-', dir=runs))
        input_bytes = (record['g6'] + '\n').encode('ascii')
        (directory / 'input.g6').write_bytes(input_bytes)
        (directory / 'UNKNOWN.g6').write_bytes(b'')
        (directory / 'records.jsonl').write_bytes(raw)
        manifest = {'profile': 'fixture11', 'input': 'input.g6',
                    'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
                    'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6',
                    'derive': False, 'forbidden_limit': 10}
        (directory / 'run.json').write_text(json.dumps(manifest) + '\n')
        # This changes only filesystem visibility; the checker command and source
        # are exactly those requested. No verifier module is patched or wrapped.
        argv = ['nice', '-n', '15', 'timeout', '1800',
                'bwrap', '--die-with-parent', '--ro-bind', '/', '/',
                '--bind', str(ROOT), str(ROOT), '--tmpfs', '/tmp',
                '--dir', '/tmp/gp10-check', '--bind', str(scratch), '/tmp/gp10-check',
                '--', PYTHON, '-B', str(CHECKER), str(directory)]
        started = time.monotonic()
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        (directory / 'stdout.log').write_text(completed.stdout)
        (directory / 'stderr.log').write_text(completed.stderr)
        report_path = directory / 'checked' / 'report.json'
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        row = {'file': name, 'damaged': damaged, 'g6': record['g6'],
               'directory': str(directory.relative_to(ROOT)), 'command': argv,
               'exit_code': completed.returncode, 'seconds': time.monotonic() - started,
               'stdout': completed.stdout, 'stderr': completed.stderr,
               'status': report.get('status'), 'reason': report.get('reason'),
               'detail': report.get('detail'), 'counts': report.get('counts')}
        results['records'].append(row)
        (ROOT / 'checker-results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps({k: v for k, v in row.items() if k != 'command'}), flush=True)
        if not damaged:
            assert completed.returncode == 0, row
            assert 'ACCEPT record ' + record['g6'] + ' verified' in completed.stdout, row
            assert 'ACCEPT run verified' in completed.stdout, row
            assert row['status'] == 'ACCEPT' and row['reason'] == 'verified', row
        else:
            assert row['status'] == 'REJECT', row
            assert 'REJECT record ' + record['g6'] in completed.stdout, row
            assert 'REJECT run ' in completed.stdout, row

    for row in search['records']:
        if row['embeds']:
            path = ROOT / 'records' / row['file']
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['record_sha256']
            check(path.name, raw)
    control = ROOT / 'records' / 'packet-45b8802d634afbe1.record.jsonl'
    raw = control.read_bytes()
    before, after = b'"sos":{"c":"1/2"', b'"sos":{"c":"1/3"'
    assert raw.count(before) == 1
    damaged = raw.replace(before, after, 1)
    assert len(raw) == len(damaged) and sum(a != b for a, b in zip(raw, damaged)) == 1
    results['damage'] = {'source': control.name, 'certificate_path': 'cert.sos.c',
                         'old': '1/2', 'new': '1/3', 'changed_bytes': 1}
    check('damaged-' + control.name, damaged, damaged=True)
    assert hashlib.sha256(CHECKER.read_bytes()).hexdigest() == results['checker_sha256']
    assert hashlib.sha256((ROOT / 'survivor.g6').read_bytes()).hexdigest() == search['host_sha256']
    for row in search['records']:
        assert hashlib.sha256((ROOT / 'records' / row['file']).read_bytes()).hexdigest() == row['record_sha256']
    results['all_original_inputs_and_checker_unchanged'] = True
    (ROOT / 'checker-results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
