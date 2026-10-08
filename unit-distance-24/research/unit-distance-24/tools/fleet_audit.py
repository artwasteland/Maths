#!/usr/bin/env python3
"""G3's fleet-wide summary audit: the union of the three coverage plans' accepted copies, audited as one fleet.

judge.py judges one published plan at a time, and its summary audit (`verify-chain-u24.py --summary-only`) sees only
that plan's slices, so each per-plan report says "N of 1920 slices absent" and stops at "per-slice OK". CONTRACT G3
asks for the fleet's summary audit complete, which includes the check that the slices' recorded shares of every
level-12 parent cell add up to the stage file once every slice is present.

This tool runs judge.judge() for the pilot, full and phase-B plans on one fleet root, each in its own staging
directory, and records the copies each run hands to its summary audit. It requires each plan's verdict OK, the
three plans' accepted slices to be pairwise disjoint with union exactly 0..1919, and then runs judge.summary_audit()
itself over the union of the staged copies with total 1920. Exit 0 only if that audit's status is "complete" with no
problems and no unresolved lines (judge.summary_audit already demands the "COVERAGE (summary only) OK:" line then).

Usage: fleet_audit.py ROOT --out REPORT.json      (ROOT: the same extracted fleet tree judge.py reads)
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402
import evidence  # noqa: E402
import worker  # noqa: E402

PLANS = (('pilot', judge.PILOT), ('full', judge.FULL), ('phaseB', judge.PHASEB))


def audit(root, work):
    real = judge.summary_audit
    plans = {}
    for name, path in PLANS:
        captured = {}

        def capture(dirs, total, w, captured=captured):
            captured['dirs'] = list(dirs)
            captured['total'] = total
            return real(dirs, total, w)

        judge.summary_audit = capture
        try:
            plan_work = work / name
            plan_work.mkdir()
            report = judge.judge(root, evidence.load(path), plan_work)
        finally:
            judge.summary_audit = real
        plans[name] = {'plan': str(path.relative_to(judge.ROOT)) if path.is_relative_to(judge.ROOT) else str(path),
                       'plan_sha256': evidence.sha(path), 'verdict': report['verdict'], 'exit': report['exit'],
                       'accepted_slices': report['accepted_slices'], 'staged': captured.get('dirs', []),
                       'per_plan_audit_total': captured.get('total')}
    problems = [f'PLAN {n}: verdict {p["verdict"]}' for n, p in plans.items() if p['verdict'] != 'OK']
    seen = {}
    for name, p in plans.items():
        for i in p['accepted_slices']:
            if i in seen:
                problems.append(f'OVERLAP: slice {i} accepted in plans {seen[i]} and {name}')
            seen[i] = name
    if sorted(seen) != list(range(1920)):
        problems.append(f'COVERAGE: the plans accept {len(seen)} distinct slices, not exactly 0..1919')
    union = [d for p in plans.values() for d in p['staged']]
    union_work = work / 'union'
    union_work.mkdir()
    result = real(union, 1920, union_work)
    problems.extend(result['problems'])
    coverage = [line for line in result['stdout'].splitlines() if line.startswith('COVERAGE (summary only)')]
    ok = not problems and not result['unresolved'] and result['status'] == 'complete'
    return {'schema': 'u24-fleet-audit-v1', 'verdict': 'OK' if ok else 'FAIL', 'exit': 0 if ok else 1,
            'checker_sha256': evidence.sha(worker.CHECKER),
            'plans': {n: {k: v for k, v in p.items() if k != 'staged'} | {'staged_copies': len(p['staged'])}
                      for n, p in plans.items()},
            'union_copies': len(union), 'union_slices': len(seen),
            'audit': {k: result[k] for k in ('status', 'problems', 'unresolved', 'missing_slices', 'exit', 'record')},
            'coverage_lines': coverage, 'problems': problems}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--guarded', action='store_true', help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.out.resolve().is_relative_to(a.root.resolve()):
        raise SystemExit('the report must be written outside the fetched trees')
    if not a.guarded:
        # The same memory guard judge.py's main uses (this desktop has 7.8 GB).
        os.environ['U24_MIN_AVAILABLE_MB'] = '1536'
        with tempfile.TemporaryDirectory(prefix='u24-fleet-audit-guard-') as tmp:
            log = Path(tmp) / 'audit.log'
            command = [sys.executable, '-B', str(Path(__file__).resolve()), str(a.root.resolve()),
                       '--out', str(a.out.resolve()), '--guarded']
            measured = worker.measured(command, log, timed=True)
            print(log.read_text(), end='')
        if measured['memory_stop']:
            print('PENDING: memory guard stopped the audit below 1536 MiB available\nFLEET AUDIT PARTIAL')
            return 3
        return measured['exit']
    with tempfile.TemporaryDirectory(prefix='u24-fleet-audit-') as tmp:
        report = audit(a.root, Path(tmp))
    a.out.write_text(json.dumps(report, indent=1) + '\n')
    for n, p in report['plans'].items():
        print(f"PLAN {n}: verdict {p['verdict']}, {len(p['accepted_slices'])} slices, {p['staged_copies']} staged copies")
    print(f"UNION: {report['union_copies']} copies, {report['union_slices']} slices")
    for line in report['coverage_lines']:
        print(line)
    for p in report['problems']:
        print('PROBLEM:', p)
    print(f"FLEET AUDIT {report['verdict']} (summary audit status {report['audit']['status']}, exit {report['audit']['exit']})")
    return report['exit']


if __name__ == '__main__':
    raise SystemExit(main())
