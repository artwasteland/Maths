#!/usr/bin/env python3
"""Regression controls for the two subtle order adapters. Run under guard.py."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from control_b10_runtime import ControlProducers, Producers
from graph6 import canonicalize, decode_graph6, pair_index, is_biconnected
from rigid_system import generic_rank
import generic_escalated as gm


def cycle(n):
    return canonicalize(n, sum(1 << pair_index(n, min(v, (v+1) % n), max(v, (v+1) % n)) for v in range(n))).g6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    producer = object.__new__(ControlProducers)
    visited = []
    producer.base = lambda code: visited.append(code)
    # C10-v is a path. Adding its missing end-to-end edge restores C9.
    # Rebase must consider it even though the unaugmented deletion has a cut.
    producer.extension(cycle(10), 3, args.output, alternatives=True)
    assert len(visited) == 10 and set(visited) == {cycle(9)}, visited
    assert all(is_biconnected(*decode_graph6(code)) for code in visited)
    results = {'cycle_rebase': {'eligible_B9_bases': len(visited), 'status': 'PASS'}}
    original_propose, original_msolve = Producers.propose, gm.msolve_stage
    try:
        gm.msolve_stage = lambda code, directory, k, seconds, frames, pins: k
        # Emulate portfolio.framed's fixed 19-rank call. The adapter must repair
        # this at the solver boundary, without changing the shared portfolio.
        Producers.propose = lambda self, code, stage: gm.msolve_stage(code, args.output, 19-generic_rank(code)[0], 1, 3, 3)
        for n in (10, 11):
            k = producer.propose(cycle(n), SimpleNamespace(method='msolve_long'))
            assert k == n-3, (n, k)
            results[f'msolve_order_{n}'] = {'k': k, 'status': 'PASS'}
    finally:
        Producers.propose, gm.msolve_stage = original_propose, original_msolve
    (args.output / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print('PASS cycle rebase and framed dimensions n=10,11')


if __name__ == '__main__':
    main()
