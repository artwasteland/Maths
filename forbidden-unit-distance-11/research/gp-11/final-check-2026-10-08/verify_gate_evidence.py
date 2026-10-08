#!/usr/bin/env python3
"""Check every evidence file that gates.json names against the copy kept in this directory.

gates.json was written on the run machine with every evidence path relative to the run directory (RUN). This
directory keeps the same files, with three differences of layout:
  - PREDICTIONS.md is research/gp-11/PREDICTIONS.md (one level up);
  - execution/outcome.json is outcome.json here;
  - checked/minimality.jsonl is kept gzipped, as checked/minimality.jsonl.gz.
Every hash is compared on the uncompressed bytes, so a match means the file is the one the gate attested.

    python3 verify_gate_evidence.py               # exit 0 iff all evidence files match
    python3 verify_gate_evidence.py --self-test   # also: a one-byte change in a copy must be caught
"""
import gzip
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def located(root, rel):
    """Where this directory keeps the file that gates.json calls RUN/<rel>."""
    if rel == 'PREDICTIONS.md':
        return root.parent / 'PREDICTIONS.md'
    if rel == 'execution/outcome.json':
        return root / 'outcome.json'
    if rel == 'checked/minimality.jsonl':
        return root / 'checked/minimality.jsonl.gz'
    return root / rel


def read(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == '.gz' else data


def check(root):
    gates = json.loads((root / 'gates.json').read_text())
    good, bad = 0, []
    for gate, entry in sorted(gates.items()):
        for ev in entry['evidence']:
            rel = ev['path']
            path = located(root, rel)
            if not path.is_file():
                bad.append(f'{gate} {rel}: missing ({path})')
                continue
            if hashlib.sha256(read(path)).hexdigest() == ev['sha256']:
                good += 1
            else:
                bad.append(f'{gate} {rel}: sha256 differs')
    return good, bad


def main():
    good, bad = check(HERE)
    for b in bad:
        print('MISMATCH', b)
    print(f'{good} evidence files match gates.json, {len(bad)} do not')
    if '--self-test' in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'run'
            shutil.copytree(HERE, copy / 'final-check')
            shutil.copy(HERE.parent / 'PREDICTIONS.md', copy / 'PREDICTIONS.md')
            root = copy / 'final-check'
            target = root / 'gate-evidence/G0/recount-receipt.json'
            raw = bytearray(target.read_bytes())
            raw[len(raw) // 2] ^= 1
            target.write_bytes(bytes(raw))
            g2, b2 = check(root)
            caught = len(b2) == 1 and 'recount-receipt.json' in b2[0]
            print(f'self-test: one flipped bit in a copy of G0/recount-receipt.json -> {len(b2)} mismatch(es); '
                  f'{"caught" if caught else "NOT CAUGHT"}')
            if not caught:
                return 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
