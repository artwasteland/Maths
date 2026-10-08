#!/usr/bin/env python3
"""GP-11 control 5.1 producer. Run under tools/guard.py; see CONTROL51-RUNBOOK.txt."""
import argparse
import json
import os
from pathlib import Path
import random
import sys
import time
from control_b10_guard import (B10, B10_SHA, DATA, F9_SHA, ROOT, Refused,
                               bases, install_read_guard, refuse, sha, sources)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--input', type=Path, help='Sorted B10 subset, graph6 only')
    p.add_argument('--sample', type=int)
    p.add_argument('--seed', type=int, default=20261001)
    p.add_argument('--shard-count', type=int, default=1)
    p.add_argument('--shard-index', type=int, default=0)
    p.add_argument('--policy', choices=('cheap', 'standard', 'full'), default='full')
    p.add_argument('--bases', type=Path, action='append', default=[], help='Optional direct exact embeddings, ALL rows at most order nine')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--validate-index', action='store_true')
    p.add_argument('--guard-only', action='store_true', help='Validate source boundary without importing or running search')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    started = time.monotonic()
    # This is deliberately before any producer/checker import or directory creation.
    try:
        base_records, base_sources = bases(args.bases)
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError, MemoryError) as exc:
        refuse('source_format', str(exc))
    if (sha(B10) != B10_SHA or sha(DATA / 'forbidden-74.json') != F9_SHA
            or sha(DATA / 'tu-gadgets.json') != 'a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629'):
        refuse('frozen_input_hash', 'B10, F9 or TU gadgets')
    population = B10.read_text().splitlines()
    if args.sample is not None and not 1 <= args.sample <= len(population):
        raise ValueError('sample_size_must_be_between_1_and_33162')
    if args.input and args.sample or not 0 <= args.shard_index < args.shard_count:
        raise ValueError('selection_parameters')
    if args.input:
        try:
            selected = args.input.read_text().splitlines()
        except (OSError, UnicodeError) as exc:
            refuse('input_graphs_only', str(exc))
        if selected != sorted(set(selected)) or not set(selected) <= set(population):
            refuse('input_graphs_only', 'requires sorted B10 graph6 subset')
    elif args.sample:
        selected = sorted(random.Random(args.seed).sample(population, args.sample))
    else:
        selected = population
    import hashlib
    selected = [c for c in selected if int.from_bytes(hashlib.sha256(c.encode()).digest()[:8], 'big') % args.shard_count == args.shard_index]
    if not selected:
        raise ValueError('empty_assignment')
    if args.guard_only:
        print('ACCEPT leak_guard sources_validated search_started=false')
        return 0
    state, output = args.state.resolve(), args.output.resolve()
    if state == output or state.is_relative_to(output) or output.is_relative_to(state):
        raise ValueError('state_output_overlap')
    src = sources()
    selected_set = set(selected)
    config = {'schema': 'control51-v1', 'population_sha256': B10_SHA,
              'assigned_ids': [i for i, c in enumerate(population) if c in selected_set],
              'selection': {'input_sha256': sha(args.input) if args.input else None, 'sample': args.sample, 'seed': args.seed},
              'shard_count': args.shard_count, 'shard_index': args.shard_index, 'policy': args.policy,
              'sources': src, 'base_sources': base_sources, 'forbidden_limit': 9,
              'GP11_ALG': os.environ.get('GP11_ALG', 'std'),
              'base_policy': 'at_most_nine; fresh graph-derived lattice placements by default; no cached hosts'}
    for directory in (state, output):
        if directory.exists() and any(directory.iterdir()):
            path = directory / 'job.json'
            if not args.resume or not path.exists() or json.loads(path.read_text()) != config:
                refuse('prior_state', str(directory))
    state.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    allowed = [ROOT / name for name in src] + [Path(p) for p in base_sources]
    # Export uses only newly generated files in output. Existing output was bound above.
    opened = install_read_guard(allowed, state, output)
    from common import Guard, MemoryFloor, Interrupted, limits, write_json, compact, descendants
    from control_b10_runtime import Poset, Store, F9TU, run_policy
    from export import export
    import fcntl
    import resource

    class Resources(Guard):
        peak_tree_kib = 0

        def check(self):
            super().check()
            rss = 0
            for pid in {os.getpid(), *descendants(os.getpid())}:
                try:
                    values = Path(f'/proc/{pid}/status').read_text().splitlines()
                    rss += next((int(s.split()[1]) for s in values if s.startswith('VmRSS:')), 0)
                except (FileNotFoundError, ProcessLookupError):
                    pass
            self.peak_tree_kib = max(self.peak_tree_kib, rss)
            if rss > 1400000:
                raise MemoryFloor('process tree exceeds 1400000 KiB RSS')

    limits(state / 'scratch')
    guard = Resources()
    store = None
    lock = (state / '.control51.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Bind even a partially built index/export to this job. A crash before
        # Store construction or midway through export remains resumable.
        for directory in (state, output):
            if not (directory / 'job.json').exists():
                write_json(directory / 'job.json', config)
        guard.start()
        # Full graph-only deletion index is scheduling data, never answer evidence.
        poset = Poset(state / 'index', guard)
        if args.validate_index:
            write_json(state / 'index-validation.json', poset.validate(selected[:200]))
        # Prior state permission and equality were checked before opening it.
        store = Store(state, poset, config['assigned_ids'], config, guard, resume=True)
        store.replay()
        tu = F9TU(poset)
        measurements = run_policy(store, tu, base_records, args.policy)
        summary = export(store, tu, output)
        stats = []
        from stages import POLICIES
        for stage in POLICIES[args.policy]:
            rows = store.db.execute('SELECT outcome,seconds FROM attempts WHERE stage=?', (stage.name,)).fetchall()
            stats.append({'stage': stage.name, 'attempts': len(rows),
                          'embedded': sum(v == 'embedded' for v, _ in rows),
                          'refuted': sum(v == 'refuted' for v, _ in rows),
                          'attempt_seconds': sum(t for _, t in rows)})
        metrics = {'elapsed_seconds': time.monotonic()-started, 'stages': stats, 'stage_wall': measurements,
                   'peak_tree_rss_kib': guard.peak_tree_kib, 'parent_max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'min_available_kib': guard.minimum_kib, 'producer_read_paths': sorted(opened),
                   'counts': store.counts(), 'claim_authorized': False}
        write_json(output / 'metrics.json', metrics)
        print(compact({'event': 'producer_complete', 'counts': summary['counts'], 'elapsed_seconds': metrics['elapsed_seconds']}), flush=True)
        return 0
    except (MemoryFloor, Interrupted) as exc:
        print('RESOURCE STOP ' + str(exc), flush=True)
        return 75
    finally:
        guard.stop.set()
        if store:
            store.close()
        lock.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Refused as exc:
        print(str(exc), flush=True)
        sys.exit(2)
