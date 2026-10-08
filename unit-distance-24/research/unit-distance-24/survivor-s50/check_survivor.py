#!/usr/bin/env python3
"""Re-check the refutation of the one (24,69) survivor of the u(24) enumeration (slice 50), from repository files only.

1. The survivor W@iiac_CA?O?GICD@C_HH?U?AWM@SE?i?GAh@?dWABT?OIr has 24 vertices and 69 edges.
2. mapping.json sends the 11-vertex graph J?iP?dHPb`_ injectively into it, every pattern edge onto a survivor edge, so
   any unit-distance embedding of the survivor would restrict to one of the pattern.
3. The pattern's GP-11 refutation record (refutation-*.record.jsonl, ACCEPTED in the GP-11 campaign as packet
   a5561d906d5f885d) is re-checked by the frozen checker research/gp-11/check/gp11check.py, run exactly as the GP-11
   admission runs it (fixture11 manifest, one input graph, one record): it must print ACCEPT run verified with verdict
   refuted.
Exit 0 only if all three hold. Usage: python3 -B check_survivor.py  (any Python with networkx; the checker's own
requirements are those of the GP-11 checker, e.g. ~/tools/pyenv-gp10/bin/python). An optional argument names another
bundle directory (mapping.json plus record) to check against the same repository checker; the red-checks use it.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUNDLE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
CHECKER = ROOT / 'research/gp-11/check/gp11check.py'


def fail(message):
    print('SURVIVOR REFUTATION FAIL:', message)
    sys.exit(1)


def main():
    m = json.loads((BUNDLE / 'mapping.json').read_text())
    survivor = nx.from_graph6_bytes(m['survivor'].encode())
    pattern = nx.from_graph6_bytes(m['pattern'].encode())
    if (survivor.number_of_nodes(), survivor.number_of_edges()) != (24, 69):
        fail('survivor is not a (24,69) graph')
    image = {int(k): v for k, v in m['pattern_to_survivor'].items()}
    if sorted(image) != list(range(pattern.number_of_nodes())) or len(set(image.values())) != len(image):
        fail('mapping is not an injective map of all pattern vertices')
    if not all(0 <= v < 24 for v in image.values()):
        fail('mapping leaves the survivor')
    missing = [(u, v) for u, v in pattern.edges() if not survivor.has_edge(image[u], image[v])]
    if missing:
        fail(f'pattern edges not mapped onto survivor edges: {missing}')
    raw = (BUNDLE / m['record']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != m['record_sha256']:
        fail('record hash differs from mapping.json')
    row = json.loads(raw)
    if row.get('g6') != m['pattern'] or row.get('verdict') != 'refuted':
        fail('record is not a refutation of the pattern graph')
    with tempfile.TemporaryDirectory() as tmp:
        check = Path(tmp) / 'check'
        check.mkdir()
        graph = m['pattern']
        (check / 'input.g6').write_text(graph + '\n')
        (check / 'UNKNOWN.g6').write_text('')
        (check / 'records.jsonl').write_bytes(raw)
        (check / 'run.json').write_text(json.dumps({
            'profile': 'fixture11', 'input': 'input.g6',
            'input_sha256': hashlib.sha256((graph + '\n').encode()).hexdigest(),
            'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6', 'derive': False, 'forbidden_limit': 10}))
        result = subprocess.run([sys.executable, '-B', str(CHECKER), str(check)], capture_output=True, text=True, timeout=1800)
        lines = result.stdout.splitlines()
        print('\n'.join(lines[-3:]))
        if result.returncode != 0 or 'ACCEPT run verified' not in lines or f'ACCEPT record {graph} verified' not in lines:
            fail(f'frozen checker did not accept the record (exit {result.returncode})')
    print(f'SURVIVOR REFUTATION OK: {m["survivor"]} contains {m["pattern"]} (refuted, frozen checker ACCEPT)')


if __name__ == '__main__':
    main()
