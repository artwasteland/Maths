#!/usr/bin/env python3
"""Run the same nine mutations before and after each relevant fix."""
from pathlib import Path
import os
import sys
import subprocess
import json
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
REPO = Path('<repo>')
CASES = {
    'R1': ('rereview/false-count', 1907, 'ccfce9dc5f', 'COUNTS: inventory 24-69.keep.g6 records: metadata 777 != checked files 0'),
    'R2': ('rereview/missing-prune', 1444, 'ccfce9dc5f', 'RECORDS: 20-49: required prune record is missing'),
    'R3': ('rereview/g4-one-cell', 1907, 'ccfce9dc5f', "G4: replay cells differ: expected 41 populated cells, got 1; missing ['11-17', '11-18', '11-19'], extra []"),
    'R4': ('rereview/false-export', 1444, 'ccfce9dc5f', 'COUNTS: 17-37 shard [0, 10000] children: metadata 818 != checked files 819'),
    'R5': ('rereview/missing-retained', 1907, 'ccfce9dc5f', "RECEIPT: retained file set differs from copy policy: missing ['24-69.certs.jsonl'], extra []"),
    'R6': ('rereview/marker-relabel', 1445, 'ccfce9dc5f', 'MARKER: receipts do not name requested slice [12, 1445, 1920]'),
    'T1': ('review3/g4-downgrade', 1907, 'bd1e5bcc1a', 'G4: whole check requires a full-mode replay'),
    'T2': ('review3/reach-k', 1444, 'bd1e5bcc1a', 'PARAMETERS: 20-49 reach k: metadata 99 != derived 4'),
    'T3': ('review3/old-marker', 1907, 'bd1e5bcc1a', 'MARKER: worker/evidence hashes differ; current receipt audit rejected bound bundle: COUNTS: structure 24-69.keep.g6 records: metadata 777 != checked files 0'),
}

def child(case, version):
    directory, index, ref, want = CASES[case]
    code = REPO if version == 'HEAD' else BASE / 'archive' / version
    sys.path.insert(0, str(code / 'research/unit-distance-24/tools'))
    import evidence as e
    import receipt_audit as audit
    import worker
    root = BASE / directory

    def action():
        if case == 'R6':
            env = dict(TAG='history', U23_OUT=str(root / 'out'), U23_RES=str(root / 'res'),
                       U23_PUSH='0', U23_TOOLCHAIN='0', U24_KEEP_RUNS='1', U24_SKIP_RUNBOOK='0',
                       U24_CHECKER_SHA256=e.sha(worker.CHECKER))
            with patch.dict(os.environ, env), patch.object(sys, 'argv', ['worker.py', '1445']), \
                    patch.object(worker, 'measured', side_effect=AssertionError('no child may start')):
                assert worker.main() == 0
        elif case == 'T3':
            mp = BASE / 'history-old-marker.json'
            assert worker.verified_marker(mp, e.sha(worker.CHECKER), False)['slice'] == [12, 1907, 1920]
        else:
            result = root / f'res/24-69-L12-tri-pf74/s{index}of1920'
            text = root / f'res/check/s{index}of1920-fixcheck.txt'
            assert audit.validate(result, text)['result'] == 'OK'
    try:
        action()
    except ValueError as error:
        assert version == 'HEAD' and str(error) == want, (case, version, str(error), want)
        print(f'{case} HEAD RED: {error}', flush=True)
    else:
        assert version != 'HEAD', case + ': current mutation accepted'
        print(f'{case} {version} ACCEPTED: the current red assertion would fail here', flush=True)
    for i in (1907, 1444):
        result = BASE / f'fixtures/res/24-69-L12-tri-pf74/s{i}of1920'
        text = BASE / f'fixtures/res/check/s{i}of1920-fixcheck.txt'
        got = audit.validate(result, text)
        assert got['result'] == 'OK' and got['target_files']['.keep.g6']['records'] == 0
    print(f'{case} {version} GREEN: both original whole/partial receipts accepted', flush=True)

if len(sys.argv) == 4 and sys.argv[1] == '--child':
    child(sys.argv[2], sys.argv[3])
else:
    chosen = list(CASES) if len(sys.argv) == 1 else [sys.argv[1]]
    marker = json.loads((BASE / 'review3/old-marker/marker.json').read_text())
    marker.pop('worker_sha256', None)
    marker.pop('evidence_sha256', None)
    (BASE / 'history-old-marker.json').write_text(json.dumps(marker)+'\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(BASE / 'tmp'))
    logs = []
    for case in chosen:
        for version in (CASES[case][2], 'HEAD'):
            command = ['/usr/bin/python3', '-B', str(Path(__file__).resolve()), '--child', case, version]
            p = subprocess.run(command, cwd=BASE, env=env, capture_output=True, text=True)
            logs.append(p.stdout+p.stderr)
            print(p.stdout+p.stderr, end='', flush=True)
            if p.returncode:
                (BASE / 'history.log').write_text(''.join(logs))
                raise SystemExit(p.returncode)
    (BASE / 'history.log').write_text(''.join(logs))
    print('HISTORY OK: all selected mutations accepted before fix, rejected at HEAD, originals green', flush=True)
