#!/usr/bin/env python3
"""Check a retained level-23 certificate's record count independently."""
from pathlib import Path
import sys
import os
import shutil
import json
import subprocess
import argparse

BASE = Path(__file__).resolve().parent
REPO = Path('<repo>')
os.environ['TMPDIR'] = str(BASE / 'tmp')
sys.path.insert(0, str(REPO / 'research/unit-distance-24/tools'))
import evidence as e
import receipt_audit as audit
import judge
from rereview_controls import dump, inventory, write_inventory, seal

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--expect-rejected', action='store_true')
ap.add_argument('--out', type=Path, default=BASE / 'retained-probe')
args = ap.parse_args()
dest = args.out.resolve()
assert dest.is_relative_to(BASE), dest
if dest.exists():
    shutil.rmtree(dest)
shutil.copytree(BASE / 'fixtures/res', dest / 'res')
result = dest / 'res/24-69-L12-tri-pf74/s1907of1920'
text = dest / 'res/check/s1907of1920-fixcheck.txt'
sp = text.with_suffix('.structure.json')
ip = text.with_suffix('.inventory.jsonl.gz')
honest = audit.validate(result, text)
print('GREEN: original whole receipt accepted; 23-64 certificates empty', flush=True)
name = '23-64.certs.jsonl'
assert (result / name).read_bytes() == b''
original_sha = e.sha(result / name)
producer = e.load(result / '23-64.prune.manifest.json')
producer_hashes = [v for k, v in producer['outputs_sha256'].items() if Path(k).name == name]
assert producer_hashes == [original_sha], producer_hashes
record = {'g6': 'V' + '?' * 43, 'verdict': 'unknown', 'witness': None}
dump(result / name, record)
actual = e.Files(result).read(name)
assert actual['records'] == 1
s = e.load(sp)
s['retained'][name] = actual['sha256']
rows = inventory(ip)
for row in rows:
    if row.get('path') == name:
        assert row['newlines'] == 0
        row.update(bytes=actual['bytes'], sha256=actual['sha256'])
if name in s['file_counts']:
    s['file_counts'][name].update(bytes=actual['bytes'], sha256=actual['sha256'])
write_inventory(ip, rows)
dump(sp, s)
seal(text, sp, ip)
# Counts, graph bytes, manifests, known receipts and checker output are unchanged.
try:
    accepted = audit.prepare(result, text, dest / 'staged')
except ValueError as error:
    if not args.expect_rejected:
        raise
    assert str(error) == 'COUNTS: inventory 23-64.certs.jsonl records: metadata 0 != checked files 1', str(error)
    print('RED CURRENT: '+str(error), flush=True)
    for index in (1907, 1444):
        got = audit.validate(BASE / f'fixtures/res/24-69-L12-tri-pf74/s{index}of1920', BASE / f'fixtures/res/check/s{index}of1920-fixcheck.txt')
        assert got['result'] == 'OK'
        print(f'GREEN CURRENT: untouched {index} receipt accepted', flush=True)
    raise SystemExit(0)
assert not args.expect_rejected, 'current audit still accepted the original gap'
print('ACCEPTED: current receipt_audit.prepare; certificate actual records 1, inventory/summary records 0', flush=True)
copy = dict(dir=result, receipt=text, slice=1907, tag='fixcheck')
judge.accepted_copy(copy, accepted, text.read_text())
print('ACCEPTED: judge.accepted_copy', flush=True)
assert e.load(result / '23-64.prune.manifest.json') == producer
assert actual['sha256'] != producer_hashes[0]
print('PRODUCER MISMATCH: unchanged retained prune manifest still binds the original empty certificate SHA256', flush=True)
cmd = ['/usr/bin/python3', '-B', str(judge.worker.CHECKER), '--summary-only', str(dest / 'staged'), '--require-hashes', '--require-g4']
p = subprocess.run(cmd, text=True, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
(dest / 'summary.log').write_text(p.stdout+p.stderr)
problems = [line for line in p.stdout.splitlines() if line.startswith(('PROBLEM', 'UNRESOLVED'))]
assert p.returncode == 1 and len(problems) == 1 and '1919 slices have no summary' in problems[0], p.stdout+p.stderr
print('SUMMARY: only expected 1919 missing slices; no mutation diagnostic', flush=True)
print('HASHES: original e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; mutated '+actual['sha256'], flush=True)
# A consistent measured newline row should make the current audit refuse this same file.
for row in rows:
    if row.get('path') == name:
        row['newlines'] = actual['records']
if name in s['file_counts']:
    s['file_counts'][name]['records'] = actual['records']
write_inventory(ip, rows)
dump(sp, s)
seal(text, sp, ip)
try:
    audit.validate(result, text)
except ValueError as error:
    assert str(error) == 'COUNTS: 23-64 certificates: metadata 1 != checked files 0', str(error)
    print('RED with honest inventory record count: '+str(error), flush=True)
else:
    raise AssertionError('measured record count should reject the same file')
# Restore the accepted reproduction and recheck the untouched source again.
for row in rows:
    if row.get('path') == name:
        row['newlines'] = 0
if name in s['file_counts']:
    s['file_counts'][name]['records'] = 0
write_inventory(ip, rows)
dump(sp, s)
seal(text, sp, ip)
audit.validate(result, text)
audit.validate(BASE / 'fixtures/res/24-69-L12-tri-pf74/s1907of1920', BASE / 'fixtures/res/check/s1907of1920-fixcheck.txt')
print('GREEN: unchanged original receipts still accepted', flush=True)
