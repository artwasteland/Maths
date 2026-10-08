#!/usr/bin/env python3
"""Reconstruct the missing fixture root from unchanged preserved receipt copies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import io

BASE = Path(__file__).resolve().parent
REPO = Path('<repo>')
TMP = BASE / 'tmp'
TMP.mkdir(exist_ok=True)
DEST = BASE / 'fixtures'
FIXES = Path('/tmp/u24-rereview-fixes-xJ9521')
FALSE_COUNT = FIXES / 'controls-final/false-count'
FALSE_EXPORT = FIXES / 'controls-final/false-export'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + '\n')

if not DEST.exists():
    shutil.copytree(FALSE_COUNT / 'res', DEST / 'res')
    shutil.rmtree(DEST / 'res/24-69-L12-tri-pf74/s1907of1920')
    shutil.copytree(FALSE_EXPORT / 'res/24-69-L12-tri-pf74/s1907of1920', DEST / 'res/24-69-L12-tri-pf74/s1907of1920')
    for path in (FALSE_EXPORT / 'res/check').glob('s1907of1920-fixcheck.*'):
        shutil.copyfile(path, DEST / 'res/check' / path.name)
    out = DEST / 'out'
    out.mkdir()
    prefix_marker = json.loads((FIXES / 'real-worker/out/checked-prefix-24-69-L12-tri-pf74.json').read_text())
    original_hashes = {Path(k).name: v for k, v in prefix_marker['receipts'].items()}
    for name, expected in original_hashes.items():
        assert digest(DEST / 'res/check' / name) == expected, name
    for index in (1907, 1444):
        marker = dict(prefix_marker)
        text = DEST / f'res/check/s{index}of1920-fixcheck.txt'
        paths = [text.with_suffix(ext) for ext in ('.txt', '.structure.json', '.inventory.jsonl.gz', '.known.json')]
        marker.update(slice=[12, index, 1920], whole=index == 1907,
                      text_receipt=str(text), structure_receipt=str(text.with_suffix('.structure.json')),
                      receipts={str(p): digest(p) for p in paths})
        if index == 1444:
            marker['run'] = marker['run'].replace('1907', '1444')
        dump(out / f'checked-24-69-L12-tri-pf74-s{index}of1920.json', marker)
        if index == 1907:
            dump(out / 'checked-prefix-24-69-L12-tri-pf74.json', marker)
    # G4 only reads aggregate manifest fingerprints from this whole-run view.
    whole = out / 'dag-24-69-L12-tri-pf74-s1907of1920'
    whole.mkdir()
    structure = json.loads((FIXES / 'fresh-whole/res/check/s1907of1920-fixcheck.structure.json').read_text())
    for name, row in structure['manifests'].items():
        if '/' not in name:
            (whole / name).write_text(row['text'])
    for path in (FIXES / 'real-worker/out/prefix-24-69-L12-tri-pf74').glob('*.manifest.json'):
        if path.name.split('.')[1] == 'manifest' and not (whole / path.name).exists():
            shutil.copyfile(path, whole / path.name)
    # The original receipt's result and the raw run have different relocated JSON
    # paths. Restore matching JSON bytes locally for review3's retained-copy check.
    partial = out / 'dag-24-69-L12-tri-pf74-s1444of1920'
    raw_source = FIXES / 'real-worker/out' / partial.name
    partial.mkdir()
    result = DEST / 'res/24-69-L12-tri-pf74/s1444of1920'
    for path in result.rglob('*'):
        if path.is_file() and path.name not in ('counts.json', 'hashes.json') and path.parent.name != 'replay':
            target = partial / path.name
            shutil.copyfile(path, target)
    expanded = json.loads((FIXES / 'fresh-whole/res/check/s1444of1920-fixcheck.structure.json').read_text())
    for name, row in expanded['manifests'].items():
        if '/' not in name:
            (partial / name).write_text(row['text'])
    for path in (FIXES / 'real-worker/out/prefix-24-69-L12-tri-pf74').glob('*.manifest.json'):
        if path.name.split('.')[1] == 'manifest' and not (partial / path.name).exists():
            shutil.copyfile(path, partial / path.name)
    dump(BASE / 'fixture-provenance.json', {
        'original_1907_receipt_hashes': original_hashes,
        'source_1907': str(FALSE_EXPORT), 'source_1444': str(FALSE_COUNT),
        'whole_run_view': 'Only preserved aggregate manifests; used only for G4 fingerprint checks.',
        'markers': 'Receipt paths relocated; 1444 identity reconstructed around unchanged honest receipt bytes.',
        'partial_run_view': 'Only unchanged retained files; used for missing-parameter controls before reconciliation.',
        'raw_1444_source_for_separate_integration': str(raw_source)})

for ref in ('ccfce9dc5f', 'bd1e5bcc1a'):
    dest = BASE / 'archive' / ref
    if not dest.exists():
        dest.mkdir(parents=True)
        paths = ['research/unit-distance-24/tools', 'research/unit-distance-23/tools',
                 'research/unit-distance-22/enum/verify-chain-u24.py', 'research/unit-distance-22/enum2',
                 'research/unit-distance-22/sources/engel-dataset/engel-22-60.g6']
        data = subprocess.check_output(['git', 'archive', ref, '--', *paths], cwd=REPO)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(dest, filter='data')
        print('ARCHIVE', ref, len(data), 'bytes', flush=True)
print('FIXTURES READY', DEST, flush=True)
