#!/usr/bin/env python3
"""Boundary controls, independent deletion-index checks, and checked bundle tests.

Run under guard.py. No historical ten-vertex certificate is opened by this test.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from control_b10_guard import GP10, GP11


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    triangle = {'g6': 'Bw', 'verdict': 'embedded', 'cert': {'type': 'exact',
        'field': {'minpoly': [-3, 0, 1], 'interval': ['1', '2']},
        'coords': [[['0', '0'], ['0', '0']], [['1', '0'], ['0', '0']], [['1/2', '0'], ['0', '1/2']]]}}
    good = args.output / 'nine-or-less.jsonl'
    good.write_text(json.dumps(triangle) + '\n')
    # A real, fresh ten-vertex exact embedding: ten distinct rational points
    # for the edgeless graph. The guard must reject even valid mathematics.
    ten = {'g6': 'I????????', 'verdict': 'embedded', 'cert': {'type': 'exact',
        'field': triangle['cert']['field'], 'coords': [[[str(v), '0'], ['0', '0']] for v in range(10)]}}
    from control_b10_runtime import f9_checker
    ck = f9_checker(args.output / 'fixture-check')
    ck.check_canonical([ten['g6']])
    ck.Checker(9).verify(ten)
    handmade = args.output / 'handmade-ten.jsonl'
    handmade.write_text(json.dumps(ten) + '\n')
    mixed = args.output / 'mixed.jsonl'
    mixed.write_text(json.dumps(triangle) + '\n' + json.dumps(ten) + '\n')
    pointer = args.output / 'hidden-pointer.jsonl'
    pointer.write_text(json.dumps(dict(triangle, cert={'type': 'super', 'g6': 'I????????', 'map': [0, 1, 2]})) + '\n')
    alias = args.output / 'innocent.jsonl'
    alias.symlink_to(GP10 / 'cloud/lean3/records.jsonl.gz')
    binary = args.output / 'opaque-index.bin'
    binary.write_bytes(b'\xff\x00\x10not a base stream')
    duplicate = args.output / 'duplicate-key.jsonl'
    duplicate.write_text('{"g6":"I????????",' + json.dumps(triangle)[1:] + '\n')
    controls = [
        ('GP10_B10', GP10 / 'cloud/lean3/records.jsonl.gz', 'answer_source'),
        ('B11_embedding_index', GP11 / 'embed/index.py', 'answer_source'),
        ('handmade_ten', handmade, 'answer_order'),
        ('mixed_late_ten', mixed, 'answer_order'),
        ('hidden_ten_pointer', pointer, 'answer_order'),
        ('symlink_to_B10', alias, 'answer_source'),
        ('opaque_index', binary, 'source_format'),
        ('duplicate_key', duplicate, 'duplicate_json_key'),
        ('withheld_F10', GP11.parent / 'unit-distance-22/data/forbidden-398.json', 'answer_source'),
    ]
    if Path('/tmp/gp11-index').is_dir():
        controls.append(('B11_poset_index', Path('/tmp/gp11-index'), 'answer_source'))
    rows = []
    for name, source, rule in controls:
        state, output = args.output / (name + '-state'), args.output / (name + '-run')
        command = [sys.executable, '-B', str(HERE / 'control_b10.py'), '--state', str(state), '--output', str(output),
                   '--sample', '1', '--bases', str(source)]
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode != 2 or not result.stdout.startswith('REFUSED leak_guard:' + rule + ' ') or 'search_started=false' not in result.stdout or state.exists() or output.exists():
            raise AssertionError((name, result.returncode, result.stdout, result.stderr))
        rows.append({'name': name, 'exit': result.returncode, 'stdout': result.stdout.strip(), 'state_created': False})
        print(result.stdout.strip())
    positive = subprocess.run([sys.executable, '-B', str(HERE / 'control_b10.py'), '--state', str(args.output / 'positive-state'),
        '--output', str(args.output / 'positive-run'), '--sample', '1', '--bases', str(good), '--guard-only'], text=True, capture_output=True)
    assert positive.returncode == 0, positive.stderr
    print(positive.stdout.strip())
    # Exercise late runtime denial in a fresh interpreter, including copied data
    # outside the repository. A search's generic Exception handler must not hide it.
    program = 'from control_b10_guard import *\ninstall_read_guard([], Path(sys.argv[1]), Path(sys.argv[2]))\ntry:\n Path(sys.argv[3]).read_bytes()\nexcept Refused as e:\n print(e); sys.exit(2)\n'
    for source in (GP10 / 'cloud/lean3/records.jsonl.gz', handmade):
        result = subprocess.run([sys.executable, '-B', '-c', program, str(args.output / 'private-state'),
            str(args.output / 'private-out'), str(source)], cwd=HERE, text=True, capture_output=True)
        assert result.returncode == 2 and 'leak_guard:runtime_read' in result.stdout, (result.stdout, result.stderr)
        rows.append({'name': 'runtime_read', 'stdout': result.stdout.strip()})
    (args.output / 'results.json').write_text(json.dumps({'status': 'PASS', 'controls': rows, 'positive': positive.stdout.strip()}, indent=2)+'\n')
    print(f'PASS leak controls={len(rows)}; original lower-order source accepted')


if __name__ == '__main__':
    main()
