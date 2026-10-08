#!/usr/bin/env python3
"""Complete the enumeration with the JSON embedded in structure.manifests.text."""
import gzip
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
data = json.loads((BASE / 'outputs-r2/field-enumeration.json').read_text())
SNAP = Path('<scratch>/scratchpad/u24-fleet-final3.69EnLQ')
EVIDENCE = BASE / 'repo/research/unit-distance-24/evidence/judge-final-2026-10-06'
schemas, counts = defaultdict(set), Counter()
def walk(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            if path.split('.')[-1] in ('inputs_sha256', 'outputs_sha256', 'software_sha256', 'table_level', 'table_parent_level'):
                key = '*'
            yield from walk(child, path + ('.' if path else '') + key)
    elif isinstance(value, list):
        if not value:
            yield path + '[]'
        for child in value:
            yield from walk(child, path + '[]')
    else:
        yield path
sources = set()
for plan in ('pilot', 'full', 'phaseb', 'repro'):
    with gzip.open(EVIDENCE / ('judge-' + plan + '.json.gz'), 'rt') as stream:
        sources.update(r['source'] for r in json.load(stream)['cost']['chosen'].values())
paths = [SNAP / source.split('/')[0] / source.split('/', 1)[1] for source in sorted(sources)]
paths = [p.with_suffix('.structure.json') for p in paths]
paths += [Path('/tmp/u24-rereview-fixes-xJ9521/fresh-whole/res/check/s1907of1920-fixcheck.structure.json')]
for number, path in enumerate(paths, 1):
    for name, row in json.loads(path.read_text())['manifests'].items():
        kind = 'export-shard' if name.startswith('shards/') else 'export-stage'
        schemas[kind].update(walk(json.loads(row['text'])))
        counts[kind] += 1
    if number % 200 == 0:
        print('export envelopes enumerated', number, flush=True)
for kind, fields in schemas.items():
    data['schemas'][kind] = sorted(fields)
data['files'].update(counts)
data['schemas']['known'] = sorted({re.sub(r'cells\.\d+-\d+', 'cells.*', path) for path in data['schemas']['known']})
(BASE / 'outputs-r2/field-enumeration-complete.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(dict(exports=dict(counts), fields={k: len(v) for k, v in schemas.items()})), flush=True)
