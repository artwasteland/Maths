#!/usr/bin/env python3
"""Red tests for fleet_audit.py's own logic: judge.judge and judge.summary_audit are replaced by fakes, so each test
says which wrapper rule must turn the verdict to FAIL (the checker itself is tested with judge.py)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fleet_audit  # noqa: E402
import judge  # noqa: E402

GOOD = {'pilot': list(range(0, 42)), 'full': list(range(42, 1883)), 'phaseB': list(range(1883, 1920))}


class FleetAuditTests(unittest.TestCase):
    def run_audit(self, slices=GOOD, verdicts=None, union_status='complete', union_problems=()):
        verdicts = verdicts or {}
        union_calls = []

        def fake_summary_audit(dirs, total, work):
            if total == 1920:
                union_calls.append(list(dirs))
                line = ('COVERAGE (summary only) OK: all present' if union_status == 'complete'
                        else 'COVERAGE (summary only) PARTIAL')
                return {'status': union_status, 'problems': list(union_problems), 'unresolved': [],
                        'missing_slices': 0, 'exit': 3, 'record': {}, 'stdout': line + '\n'}
            return {'status': 'per-slice OK', 'problems': [], 'unresolved': [], 'missing_slices': 1920 - total,
                    'exit': 3, 'record': {}, 'stdout': ''}

        def fake_judge(root, plan, work):
            name = work.name
            dirs = [work / f's{i}of1920' for i in slices[name]]
            judge.summary_audit(dirs, len(slices[name]), work)  # the wrapper's capture hook
            return {'verdict': verdicts.get(name, 'OK'), 'exit': 0 if verdicts.get(name, 'OK') == 'OK' else 1,
                    'accepted_slices': list(slices[name])}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(judge, 'summary_audit', side_effect=fake_summary_audit), \
                mock.patch.object(judge, 'judge', side_effect=fake_judge):
            report = fleet_audit.audit(Path(tmp), Path(tmp))
        return report, union_calls

    def test_good_union_is_ok_and_audits_every_staged_copy(self):
        report, union_calls = self.run_audit()
        self.assertEqual(report['verdict'], 'OK', report['problems'])
        self.assertEqual(len(union_calls), 1)
        self.assertEqual(len(union_calls[0]), 1920)
        self.assertEqual(report['union_slices'], 1920)

    def test_overlapping_plans_fail(self):
        slices = dict(GOOD, full=[0] + GOOD['full'])
        report, _ = self.run_audit(slices)
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertTrue(any(p.startswith('OVERLAP: slice 0') for p in report['problems']))

    def test_missing_slice_fails(self):
        slices = dict(GOOD, phaseB=GOOD['phaseB'][:-1])
        report, _ = self.run_audit(slices)
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertTrue(any(p.startswith('COVERAGE:') for p in report['problems']))

    def test_plan_verdict_fail_fails(self):
        report, _ = self.run_audit(verdicts={'full': 'FAIL'})
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertIn('PLAN full: verdict FAIL', report['problems'])

    def test_union_audit_not_complete_fails(self):
        report, _ = self.run_audit(union_status='per-slice OK')
        self.assertEqual(report['verdict'], 'FAIL')

    def test_union_audit_problem_fails(self):
        report, _ = self.run_audit(union_problems=['SUMMARY: shares of (12,20) do not add up'])
        self.assertEqual(report['verdict'], 'FAIL')

    def test_real_summary_audit_restored(self):
        real = judge.summary_audit
        self.run_audit()
        self.assertIs(judge.summary_audit, real)


if __name__ == '__main__':
    unittest.main()
