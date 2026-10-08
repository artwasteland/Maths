#!/usr/bin/env python3
"""Enumerate leaf schemas of all retained fleet JSON, envelopes and inventories."""
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
SNAP = Path('<scratch>/scratchpad/u24-fleet-final3.69EnLQ')
EVIDENCE = BASE / 'repo/research/unit-distance-24/evidence/judge-final-2026-10-06'
schemas, examples, files = defaultdict(set), {}, Counter()
MAPS = {'inputs_sha256', 'outputs_sha256', 'software_sha256', 'retained', 'file_counts',
        'manifests', 'target_files', 'files', 'ubar', 'table', 'table_level', 'table_parent_level',
        'schade_windows', 'ubar_override', 'ubar_justification'}

def walk(value, path=''):
    if isinstance(value, dict):
        if not value:
            yield path + '{}'
        for key, child in sorted(value.items()):
            segment = '*' if path.split('.')[-1] in MAPS or key.isdigit() else key
            yield from walk(child, path + ('.' if path else '') + segment)
    elif isinstance(value, list):
        if not value:
            yield path + '[]'
        for child in value:
            yield from walk(child, path + '[]')
    else:
        yield path

def add(kind, data, path):
    files[kind] += 1
    schemas[kind].update(walk(data))
    examples.setdefault(kind, str(path))

def inspect(result, text):
    for path in sorted(result.rglob('*.json')):
        if 'history' in path.relative_to(result).parts:
            continue
        name = path.relative_to(result).as_posix()
        kind = ('prune' if name.endswith('.prune.manifest.json') else
                'verify' if name.endswith('.verify.manifest.json') else
                'stage' if name.endswith('.manifest.json') else name)
        add(kind, json.loads(path.read_text()), path)
    stem = text.with_suffix('')
    for kind in ('structure', 'known'):
        path = Path(str(stem) + '.' + kind + '.json')
        add(kind, json.loads(path.read_text()), path)
    path = text.with_suffix('.inventory.jsonl.gz')
    with gzip.open(path, 'rt') as stream:
        for row in map(json.loads, stream):
            add('inventory-row' if 'path' in row else 'inventory-header', row, path)
    for line in text.read_text().splitlines():
        if line.startswith('{'):
            add('receipt-checker', json.loads(line), text)
        elif line.startswith('# inventory:'):
            add('receipt-inventory', json.loads(line.split('; ', 1)[1]), text)

copies = {}
for plan in ('pilot', 'full', 'phaseb', 'repro'):
    with gzip.open(EVIDENCE / ('judge-' + plan + '.json.gz'), 'rt') as stream:
        for index, row in json.load(stream)['cost']['chosen'].items():
            copies.setdefault(row['source'], int(index))
for number, (source, index) in enumerate(sorted(copies.items()), 1):
    root = SNAP / source.split('/')[0] / 'research/unit-distance-24/results/u24'
    result = root / '24-69-L12-tri-pf74' / f's{index}of1920'
    receipt = root / 'check' / (source.split('/')[-1] + '.txt')
    # source is the receipt stem's relative path, not necessarily the directory name.
    if not receipt.exists():
        receipt = SNAP / source.split('/')[0] / source.split('/', 1)[1]
        if receipt.suffix != '.txt':
            receipt = receipt.with_suffix('.txt')
    inspect(result, receipt)
    if number % 100 == 0:
        print('enumerated', number, flush=True)
inspect(BASE / 'fixtures/res/24-69-L12-tri-pf74/s1907of1920', BASE / 'fixtures/res/check/s1907of1920-fixcheck.txt')
inspect(Path('/tmp/u24-rereview-fixes-xJ9521/fresh-whole/res/24-69-L12-tri-pf74/s1907of1920'),
        Path('/tmp/u24-rereview-fixes-xJ9521/fresh-whole/res/check/s1907of1920-fixcheck.txt'))
out = dict(copies=len(copies), files=dict(files), examples=examples,
           schemas={kind: sorted(paths) for kind, paths in sorted(schemas.items())})
(BASE / 'outputs-r2/field-enumeration.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(dict(copies=len(copies), fields={kind: len(paths) for kind, paths in schemas.items()})), flush=True)
