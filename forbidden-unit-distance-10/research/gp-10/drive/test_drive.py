"""Regression tests for the GP-10 driver module.

The tests include the two pre-registered driver red controls: line-count
coverage and an identity pointer map.  They use only the frozen B8' input and
the local stub producer, so they do not claim anything about the real
embedder or refuter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

try:
    from .aggregate import (
        coverage_errors,
        done_by_set,
        records_by_g6,
        validate_pointers,
    )
    from .driver import run_pipeline
    from .graph6 import decode_graph6, map_edges, load_graph6
    from .poset import build_poset
except ImportError:
    from aggregate import coverage_errors, done_by_set, records_by_g6, validate_pointers  # type: ignore
    from driver import run_pipeline  # type: ignore
    from graph6 import decode_graph6, load_graph6, map_edges  # type: ignore
    from poset import build_poset  # type: ignore


MODULE = Path(__file__).resolve().parent
B8 = MODULE.parent / "data" / "B8p.g6"
PYTHON = str(Path.home() / "tools" / "pyenv-gp10" / "bin" / "python")
PARENT = "G?AZVk"
CHILD = "G?BHvc"


def exact_stub(graph: str, verdict: str) -> dict[str, object]:
    return {"g6": graph, "verdict": verdict, "cert": {"type": "exact"}}


class DriverTests(unittest.TestCase):
    def test_b8_poset_statistics_and_map_direction(self) -> None:
        poset = build_poset(load_graph6(B8))
        self.assertEqual(poset.stats["input_count"], 383)
        self.assertEqual(poset.stats["relation_count"], 1606)
        self.assertEqual(poset.stats["maximal_count"], 53)
        relation = poset.relation(PARENT, CHILD)
        self.assertIsNotNone(relation)
        assert relation is not None
        self.assertEqual(list(relation.map), [0, 3, 1, 2, 4, 5, 6, 7])
        n, child_mask = decode_graph6(CHILD)
        _, parent_mask = decode_graph6(PARENT)
        self.assertTrue(map_edges(n, child_mask, n, parent_mask, relation.map))
        self.assertFalse(map_edges(n, child_mask, n, parent_mask, list(range(n))))

    def test_done_is_set_equality_not_line_count(self) -> None:
        input_g6 = [PARENT, CHILD]
        duplicated = [PARENT, PARENT]
        self.assertTrue(done_by_set(input_g6, [CHILD, PARENT]))
        self.assertFalse(done_by_set(input_g6, duplicated))
        errors = coverage_errors(
            input_g6,
            [exact_stub(PARENT, "embedded"), exact_stub(PARENT, "embedded")],
        )
        self.assertTrue(any("duplicate" in error for error in errors))
        self.assertTrue(any("missing" in error for error in errors))

    def test_identity_pointer_map_goes_red(self) -> None:
        poset = build_poset([PARENT, CHILD])
        relation = poset.relation(PARENT, CHILD)
        self.assertIsNotNone(relation)
        assert relation is not None
        records = records_by_g6(
            [
                exact_stub(PARENT, "embedded"),
                {
                    "g6": CHILD,
                    "verdict": "embedded",
                    "cert": {
                        "type": "super",
                        "g6": PARENT,
                        "map": list(range(8)),
                    },
                },
            ]
        )
        errors = validate_pointers(records, poset=poset)
        self.assertTrue(any("edge-preserving" in error for error in errors))

        good_records = records_by_g6(
            [
                exact_stub(PARENT, "embedded"),
                {
                    "g6": CHILD,
                    "verdict": "embedded",
                    "cert": {"type": "super", "g6": PARENT, "map": list(relation.map)},
                },
            ]
        )
        self.assertEqual(validate_pointers(good_records, poset=poset), [])

    def test_r_pointer_uses_the_same_child_to_parent_map(self) -> None:
        poset = build_poset([PARENT, CHILD])
        relation = poset.relation(PARENT, CHILD)
        self.assertIsNotNone(relation)
        assert relation is not None
        records = records_by_g6(
            [
                exact_stub(CHILD, "refuted"),
                {
                    "g6": PARENT,
                    "verdict": "refuted",
                    "cert": {"type": "sub", "g6": CHILD, "map": list(relation.map)},
                },
            ]
        )
        self.assertEqual(validate_pointers(records, poset=poset), [])
        records[PARENT]["cert"] = {"type": "sub", "g6": CHILD, "map": list(range(8))}
        errors = validate_pointers(records, poset=poset)
        self.assertTrue(any("edge-preserving" in error for error in errors))

    def test_cycle_is_reported(self) -> None:
        poset = build_poset([PARENT, CHILD])
        records = records_by_g6(
            [
                {
                    "g6": PARENT,
                    "verdict": "embedded",
                    "cert": {"type": "super", "g6": CHILD, "map": list(range(8))},
                },
                {
                    "g6": CHILD,
                    "verdict": "embedded",
                    "cert": {"type": "super", "g6": PARENT, "map": list(range(8))},
                },
            ]
        )
        errors = validate_pointers(records, poset=poset)
        self.assertTrue(any("pointer cycle" in error for error in errors))

    def test_stub_pipeline_writes_exact_unknown_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gp10-drive-", dir="/tmp/gp10-drive") as temporary:
            run_dir = Path(temporary) / "run"
            summary = run_pipeline(
                B8,
                run_dir,
                str(MODULE / "stub_producers.py"),
                str(MODULE / "stub_producers.py"),
                None,
                [0.1],
                workers=1,
                python=PYTHON,
                embedder_extra=["--mode", "unknown"],
                refuter_extra=["--mode", "unknown"],
            )
            self.assertTrue(summary["done"])
            self.assertEqual(summary["unknown_count"], 383)
            self.assertEqual(load_graph6(run_dir / "UNKNOWN.g6"), load_graph6(B8))
            self.assertTrue((run_dir / "records.jsonl").exists())
            self.assertTrue((run_dir / "MINIMALITY.json").exists())

    def test_resume_retries_a_covered_unknown_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gp10-drive-resume-", dir="/tmp/gp10-drive") as temporary:
            run_dir = Path(temporary) / "run"
            first = run_pipeline(
                B8,
                run_dir,
                str(MODULE / "stub_producers.py"),
                str(MODULE / "stub_producers.py"),
                None,
                [0.1],
                workers=1,
                python=PYTHON,
                embedder_extra=["--mode", "unknown"],
                refuter_extra=["--mode", "unknown"],
            )
            self.assertEqual(first["unknown_count"], 383)
            second = run_pipeline(
                B8,
                run_dir,
                str(MODULE / "stub_producers.py"),
                str(MODULE / "stub_producers.py"),
                None,
                [0.1],
                workers=1,
                python=PYTHON,
                resume=True,
                embedder_extra=["--mode", "all-embedded"],
                refuter_extra=["--mode", "all-refuted"],
            )
            self.assertEqual(second["unknown_count"], 0)
            self.assertEqual(second["embedded_count"], 383)

    def test_failed_parent_does_not_hide_child_at_any_budget(self) -> None:
        import importlib
        BatchResult = importlib.import_module(run_pipeline.__module__).BatchResult
        attempts = []

        def unknown_batch(kind, graphs, round_number, budget, *args, **kwargs):
            attempts.extend((kind, graph, budget) for graph in graphs)
            return BatchResult({}, {g: {'reason': 'fixture exhausted', 'budget': {}}
                                    for g in graphs}, [])

        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            root = Path(temporary)
            source = root / 'input.g6'
            source.write_text('\n'.join(sorted([PARENT, CHILD])) + '\n')
            with patch.object(importlib.import_module(run_pipeline.__module__), '_run_batches',
                              side_effect=unknown_batch):
                run_pipeline(source, root / 'run', 'fixture', 'fixture', None, [1, 5], workers=1)
        self.assertEqual([a for a in attempts if a[0] == 'embed'],
                         [('embed', PARENT, 1), ('embed', CHILD, 1),
                          ('embed', PARENT, 5), ('embed', CHILD, 5)])
        self.assertEqual([a for a in attempts if a[0] == 'refute'],
                         [('refute', CHILD, 1), ('refute', PARENT, 1),
                          ('refute', CHILD, 5), ('refute', PARENT, 5)])

    def test_known_export_omits_sub_and_dependent_tu(self) -> None:
        import importlib
        driver = importlib.import_module(run_pipeline.__module__)
        records = {
            CHILD: {'g6': CHILD, 'verdict': 'refuted', 'cert': {'type': 'tree', 'witness': {}}},
            PARENT: {'g6': PARENT, 'verdict': 'refuted',
                     'cert': {'type': 'sub', 'g6': CHILD, 'map': list(range(8))}},
            'dependent': {'g6': 'dependent', 'verdict': 'refuted',
                          'cert': {'type': 'tu', 'end': {'refuted': PARENT}}},
        }
        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            target = Path(temporary) / 'known.jsonl'
            driver._write_known_refuted(target, records)
            exported = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(exported, [records[CHILD]])

    def test_unknown_preserves_methods_and_prior_budgets(self) -> None:
        import importlib
        driver = importlib.import_module(run_pipeline.__module__)
        record = {'g6': CHILD, 'verdict': 'unknown',
                  'cert': {'reason': 'exhausted', 'budget': {'methods': ['null'],
                           'attempts': [{'reason': 'timeout'}]}}}
        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            target = Path(temporary) / 'output.jsonl'
            target.write_text(json.dumps(record) + '\n')
            first = driver._parse_batch_records('refute', [CHILD], target, 0, 1, 0, {})
            second = driver._parse_batch_records('refute', [CHILD], target, 0, 5, 1, first.unknown)
        budget = second.unknown[CHILD]['budget']
        self.assertEqual([h['time_limit'] for h in budget['history']], [1, 5])
        self.assertEqual(budget['producer_budget'], record['cert']['budget'])

    def test_each_retry_has_a_fresh_request_and_preserved_log(self) -> None:
        import importlib
        driver = importlib.import_module(run_pipeline.__module__)
        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            root = Path(temporary)
            first = driver._run_batches('embed', [CHILD], 0, 0.1, root, 1, PYTHON,
                                        str(MODULE / 'stub_producers.py'), None, {}, {},
                                        ['--mode', 'unknown'])
            saved = Path(first.logs[0]).read_bytes()
            second = driver._run_batches('embed', [PARENT], 0, 0.1, root, 1, PYTHON,
                                         str(MODULE / 'stub_producers.py'), None, {}, {},
                                         ['--mode', 'all-embedded'])
            self.assertNotEqual(first.logs[0], second.logs[0])
            self.assertEqual(Path(first.logs[0]).read_bytes(), saved)
            self.assertEqual(set(first.unknown), {CHILD})
            self.assertEqual(set(second.records), {PARENT})

    def test_inprocess_log_captures_native_stderr_and_exception(self) -> None:
        import importlib
        import os
        from types import SimpleNamespace
        package = run_pipeline.__module__.rpartition('.')[0]
        integration = importlib.import_module(package + '.integration' if package else 'integration')

        def positive(argv):
            os.write(2, b'native stderr positive\n')
            return 0

        def negative(argv):
            os.write(2, b'native stderr negative\n')
            raise ValueError('fixture log failure')

        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            target = Path(temporary) / 'positive.log'
            with patch.object(integration, 'load_entry', return_value=SimpleNamespace(main=positive)):
                self.assertEqual(integration.invoke('fixture', [], target), 0)
            self.assertIn('native stderr positive', target.read_text())
            target = Path(temporary) / 'negative.log'
            with patch.object(integration, 'load_entry', return_value=SimpleNamespace(main=negative)):
                self.assertEqual(integration.invoke('fixture', [], target), 2)
            self.assertIn('native stderr negative', target.read_text())
            self.assertIn('ValueError: fixture log failure', target.read_text())

    def test_duplicate_unknowns_are_reported_for_the_expected_reason(self) -> None:
        import importlib
        driver = importlib.import_module(run_pipeline.__module__)
        row = {'g6': CHILD, 'verdict': 'unknown',
               'cert': {'reason': 'bounded search exhausted', 'budget': {'seconds': 1}}}
        with tempfile.TemporaryDirectory(dir='/tmp/gp10-drive') as temporary:
            target = Path(temporary) / 'records.jsonl'
            target.write_text(json.dumps(row) + '\n')
            positive = driver._parse_batch_records('embed', [CHILD], target, 0, 1, 0, {})
            self.assertEqual(positive.unknown[CHILD]['reason'], 'bounded search exhausted')
            target.write_text((json.dumps(row) + '\n') * 3)
            negative = driver._parse_batch_records('embed', [CHILD], target, 0, 1, 0, {})
            self.assertEqual(negative.records, {})
            self.assertEqual(negative.unknown[CHILD]['reason'], 'producer returned duplicate records')


if __name__ == "__main__":
    unittest.main()
