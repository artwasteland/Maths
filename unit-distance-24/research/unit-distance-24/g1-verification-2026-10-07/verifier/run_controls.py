#!/usr/bin/env python3
"""Run unmodified repository control assertions with relocated fixtures."""
from pathlib import Path
import os
import subprocess
import sys
import time
import json
import shutil

BASE = Path(__file__).resolve().parent
REPO = Path('<repo>')
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(BASE / 'tmp'), U24_MIN_AVAILABLE_MB='1536')
name = sys.argv[1]
assert name in ('rereview', 'review3')
if (BASE / name).exists():
    shutil.rmtree(BASE / name)
cmd = ['/usr/bin/python3', '-B', str(REPO / f'research/unit-distance-24/tools/{name}_controls.py'),
       '--source', str(BASE / 'fixtures'), '--out', str(BASE / name)]
if name == 'review3':
    cmd += ['--rereview', '/tmp/u24-rereview-fixes-xJ9521/real-worker', '--review3', '/tmp/u24-review3-bd1e5bcc1a']
start = time.monotonic()
with (BASE / f'{name}.log').open('w') as log:
    proc = subprocess.run(cmd, env=env, cwd=BASE, stdout=log, stderr=subprocess.STDOUT)
info = dict(command=cmd, exit=proc.returncode, seconds=round(time.monotonic()-start, 3))
(BASE / f'{name}-run.json').write_text(json.dumps(info, indent=2)+'\n')
print(json.dumps(info), flush=True)
print('\n'.join((BASE / f'{name}.log').read_text().splitlines()[-8:]), flush=True)
raise SystemExit(proc.returncode)
