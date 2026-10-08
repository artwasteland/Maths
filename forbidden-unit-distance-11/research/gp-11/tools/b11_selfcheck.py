#!/usr/bin/env python3
"""Analyst convenience only. Admission always uses a coordinator-owned fresh copy."""
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
import b11_check

root = Path.cwd()
parent = root / 'self-checks'
parent.mkdir(exist_ok=True)
index = 1
while (parent / f'check-{index:04d}').exists():
    index += 1
target = parent / f'check-{index:04d}'
target.mkdir()
seed = b11_check.loads((root / 'SEED.json').read_bytes())
for name, pin in seed.items():
    b11_check.require(b11_check.sha(root / name) == pin, 'seed_changed:' + name)
    path = target / name
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, path)
shutil.copyfile(root / 'record.jsonl', target / 'record.jsonl')
(target / 'scratch').mkdir()
answer = b11_check.check(target.resolve())
print(target, answer['status'], answer['reason'])
raise SystemExit(0 if answer['status'] == 'ACCEPTED' else 1)
