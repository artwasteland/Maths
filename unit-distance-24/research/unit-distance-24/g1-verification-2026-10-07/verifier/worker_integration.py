#!/usr/bin/env python3
"""Use the original omission/restoration integration assertion on a private raw copy."""
from pathlib import Path
import os
import sys
import shutil
import json

BASE = Path(__file__).resolve().parent
REPO = Path('<repo>')
os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(BASE / 'tmp'), U24_MIN_AVAILABLE_MB='1536')
sys.path.insert(0, str(REPO / 'research/unit-distance-24/tools'))
from rereview_controls import worker_case, atomic_replace

source = BASE / 'integration-source'
if not source.exists():
    shutil.copytree(BASE / 'fixtures/res', source / 'res')
    original = Path('/tmp/u24-rereview-fixes-xJ9521/real-worker/out/dag-24-69-L12-tri-pf74-s1444of1920')
    raw = source / 'out' / original.name
    shutil.copytree(original, raw)
    for path in raw.rglob('*.json'):
        data = path.read_bytes()
        new = data.replace(str(original).encode(), str(raw).encode())
        if data != new:
            atomic_replace(path, new)
    prefix_original = Path('/tmp/u24-rereview-fixes-xJ9521/real-worker/out/prefix-24-69-L12-tri-pf74')
    prefix = source / 'out' / prefix_original.name
    prefix.mkdir()
    info = json.loads((prefix_original / 'prefix.json').read_text())
    for name in info['files']:
        # All shared bytes already exist in the local full raw copy.
        assert (raw / name).is_file(), name
        os.link(raw / name, prefix / name)
    shutil.copyfile(prefix_original / 'prefix.json', prefix / 'prefix.json')
    shutil.copyfile(BASE / 'fixtures/out/checked-prefix-24-69-L12-tri-pf74.json', source / 'out/checked-prefix-24-69-L12-tri-pf74.json')
    print('PRIVATE RAW COPY READY', flush=True)
dest = BASE / 'worker-integration'
if dest.exists():
    shutil.rmtree(dest)
worker_case(source, dest)
print('WORKER INTEGRATION OK', flush=True)
