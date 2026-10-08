"""Round 3 genuine seed fixtures and one-field mutations, using the official checker."""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from driver import run_pipeline
from graph6 import canonicalize, decode_graph6, load_graph6, save_graph6
from integration import invoke
from poset import build_poset
from runfiles import write_manifests
from seeds import CHECKER

MODULE = Path(__file__).resolve().parent
FIXTURES = MODULE.parent / 'check' / 'fixtures'
F9 = MODULE.parents[1] / 'unit-distance-22' / 'data' / 'forbidden-74.json'


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def raw(record):
    return ('  ' + json.dumps(record, separators=(', ', ': ')) + ' \n').encode()


class SeedTests(unittest.TestCase):
    def setUp(self):
        retained = os.environ.get('GP10_DRIVE_TEST_ARTIFACTS')
        if retained:
            self.root = Path(retained) / self._testMethodName
            self.root.mkdir(parents=True, exist_ok=False)
        else:
            self.temp = tempfile.TemporaryDirectory(prefix='seed-test-', dir='/tmp/gp10-drive')
            self.addCleanup(self.temp.cleanup)
            self.root = Path(self.temp.name)

    def assemble(self, graphs, chunks, name='run', forbidden=None, resume=False):
        source = self.root / f'{name}-input.g6'
        save_graph6(source, sorted(graphs))
        paths = []
        for i, chunk in enumerate(chunks):
            path = self.root / f'{name}-seed-{i}.jsonl'
            path.write_bytes(chunk)
            paths.append(path)
        directory = self.root / name
        with patch.object(importlib.import_module(run_pipeline.__module__), '_run_batches') as producers:
            summary = run_pipeline(source, directory, 'unused', 'unused', forbidden, [],
                                   seed_paths=paths, validate_seeds=True, no_producers=True,
                                   resume=resume)
            producers.assert_not_called()
        return directory, summary

    def check(self, directory):
        status = invoke(CHECKER, [str(directory / 'sample')], directory / 'final-check.log')
        report = json.loads((directory / 'sample/checked/report.json').read_text())
        self.assertEqual(status, 0, report)
        self.assertEqual(report['status'], 'ACCEPT', report)
        return report

    def test_first_decided_verbatim_and_downward_propagation_resume(self):
        parent = fixture('triangle.json')
        child = canonicalize(3, decode_graph6('Bw')[1] & ~1).g6
        mutated = deepcopy(parent)
        mutated['cert']['coords'][1][0] = ['2', '0']
        unknown = {'g6': parent['g6'], 'verdict': 'unknown', 'cert': {}}
        directory, summary = self.assemble([parent['g6'], child],
                                          [raw(unknown) + raw(parent), raw(mutated)])
        self.assertEqual(summary['embedded_count'], 2)
        self.assertEqual(summary['unknown_count'], 0)
        self.assertIn(raw(parent), (directory / 'records.jsonl').read_bytes().splitlines(keepends=True))
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['selected_count'], 1)
        self.assertEqual(report['rejected_count'], 0)
        self.check(directory)
        self.assemble([parent['g6'], child], [], resume=True)
        self.assertIn(raw(parent), (directory / 'records.jsonl').read_bytes().splitlines(keepends=True))
        self.check(directory)

    def test_dependency_closure_and_bad_parent_cannot_poison(self):
        parent = fixture('triangle.json')
        child = canonicalize(3, decode_graph6('Bw')[1] & ~1).g6
        relation = build_poset([child, 'Bw']).relation('Bw', child)
        pointer = {'g6': child, 'verdict': 'embedded',
                   'cert': {'type': 'super', 'g6': 'Bw', 'map': list(relation.map)}}
        directory, summary = self.assemble([child, 'Bw'], [raw(pointer) + raw(parent)], 'good')
        self.assertEqual(summary['embedded_count'], 2)
        self.check(directory)
        parent['cert']['coords'][1][0] = ['2', '0']
        directory, summary = self.assemble([child, 'Bw'], [raw(pointer) + raw(parent)], 'bad')
        self.assertEqual(summary['unknown_count'], 2)
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['rejected_count'], 2)
        self.assertEqual(report['outcomes']['Bw']['reason'].split(':')[0], 'edge_equation')
        self.assertEqual(report['outcomes'][child]['reason'], 'pointer_target_not_accepted_embedded')
        self.assertEqual(load_graph6(directory / 'UNKNOWN.g6'), sorted([child, 'Bw']))
        self.check(directory)

    def test_external_exact_host_and_pointer_map_mutation(self):
        form = canonicalize(3, 1)
        old = [[['0'], ['0']], [['1'], ['0']], [['5'], ['0']]]
        host = {'g6': form.g6, 'verdict': 'embedded', 'cert': {'type': 'exact',
                'field': {'minpoly': [0, 1], 'interval': ['-1', '1']},
                'coords': [old[i] for i in form.new_to_old]}}
        pointer = {'g6': 'A_', 'verdict': 'embedded', 'cert': {'type': 'super',
                   'g6': form.g6, 'map': list(form.old_to_new[:2])}}
        directory, summary = self.assemble(['A_'], [raw(pointer) + raw(host)], 'good')
        self.assertEqual(summary['embedded_count'], 1)
        self.assertEqual((directory / 'hosts.jsonl').read_bytes(), raw(host))
        self.check(directory)
        pointer['cert']['map'][1] = pointer['cert']['map'][0]
        directory, summary = self.assemble(['A_'], [raw(pointer) + raw(host)], 'bad')
        self.assertEqual(summary['unknown_count'], 1)
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['outcomes']['A_']['reason'].split(':')[0], 'map_not_injective')
        self.check(directory)

    def test_external_refuted_target_is_not_a_host(self):
        parent = fixture('round3/k4-isolate-null-dag.json')
        parent['cert'] = {'type': 'sub', 'g6': 'C~', 'map': [1, 2, 3, 4]}
        directory, summary = self.assemble([parent['g6']],
                                          [raw(parent) + raw(fixture('k4-tree.json'))])
        self.assertEqual(summary['unknown_count'], 1)
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['host_count'], 0)
        self.assertEqual(report['outcomes'][parent['g6']]['reason'], 'pointer_target_missing')
        self.check(directory)

    def test_dag_types_and_one_coefficient_mutation(self):
        for i, name in enumerate(['round3/k23-null-dag.json', 'round3/k4-real-dag-sos.json']):
            record = fixture(name)
            directory, summary = self.assemble([record['g6']], [raw(record)], f'good-{i}')
            self.assertEqual(summary['refuted_count'], 1)
            self.assertEqual((directory / 'records.jsonl').read_bytes(), raw(record))
            self.check(directory)
            record['cert']['rows'][0]['poly'][0][0] = '3'
            directory, summary = self.assemble([record['g6']], [raw(record)], f'bad-{i}')
            self.assertEqual(summary['unknown_count'], 1)
            report = json.loads((directory / 'seeds/SEEDS.json').read_text())
            self.assertEqual(report['outcomes'][record['g6']]['reason'].split(':')[0], 'dag_row_identity')
            self.check(directory)

    def test_indexed_forbidden_seed_and_upward_propagation(self):
        record = fixture('round3/k23-null-dag.json')
        child = record['g6']
        n, mask = decode_graph6(child)
        missing = next(i for i in range(n * (n - 1) // 2) if not mask & (1 << i))
        parent = canonicalize(n, mask | (1 << missing)).g6
        record['cert'] = {'type': 'sub', 'g6': child, 'index': 1, 'map': list(range(n))}
        directory, summary = self.assemble([child, parent], [raw(record)], forbidden=F9)
        self.assertEqual(summary['refuted_count'], 2)
        self.assertEqual(summary['unknown_count'], 0)
        self.check(directory)

    def test_rejected_first_seed_has_no_later_fallback(self):
        first = fixture('triangle.json')
        first['extra'] = 'one-field schema mutation'
        directory, summary = self.assemble(['Bw'], [raw(first), raw(fixture('triangle.json'))])
        self.assertEqual(summary['unknown_count'], 1)
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['selected_count'], 1)
        self.assertEqual(report['rejected_count'], 1)
        self.check(directory)

    def test_unterminated_seed_is_rejected_without_hiding_framed_seed(self):
        first = fixture('round3/k4-isolate-null-dag.json')
        second = fixture('round3/k23-null-dag.json')
        directory, summary = self.assemble([first['g6'], second['g6']],
                                          [raw(first).rstrip(), raw(second)])
        self.assertEqual(summary['unknown_count'], 1)
        self.assertEqual(summary['refuted_count'], 1)
        report = json.loads((directory / 'seeds/SEEDS.json').read_text())
        self.assertEqual(report['rejected_count'], 1)
        self.check(directory)

    def test_normal_producers_only_receive_the_unresolved_remainder(self):
        driver = importlib.import_module(run_pipeline.__module__)
        form = canonicalize(3, 5)
        old = [[['0'], ['0']], [['1'], ['0']], [['2'], ['0']]]
        record = {'g6': form.g6, 'verdict': 'embedded', 'cert': {'type': 'exact',
                  'field': {'minpoly': [0, 1], 'interval': ['-1', '1']},
                  'coords': [old[i] for i in form.new_to_old]}}
        seed = self.root / 'seed.jsonl'
        seed.write_bytes(raw(record))
        source = self.root / 'input.g6'
        save_graph6(source, sorted(['Bw', form.g6, canonicalize(3, 1).g6]))
        attempts = []

        def exhausted(kind, graphs, *args, **kwargs):
            attempts.append((kind, graphs))
            return driver.BatchResult({}, {g: {'reason': 'fixture exhausted', 'budget': {}}
                                          for g in graphs}, [])

        with patch.object(driver, '_run_batches', side_effect=exhausted):
            summary = run_pipeline(source, self.root / 'run', 'unused', 'unused', None, [1],
                                   seed_paths=[seed], validate_seeds=True)
        self.assertEqual(attempts, [('embed', ['Bw']), ('refute', ['Bw'])])
        self.assertEqual(summary['embedded_count'], 2)
        self.assertEqual(summary['unknown_count'], 1)
        self.check(self.root / 'run')

    def test_B10_manifest_cannot_bypass_controls_and_sample_derives(self):
        directory = self.root / 'gated'
        directory.mkdir()
        write_manifests(directory, MODULE.parent / 'data/B10.g6', 9, profile='B10')
        sample = json.loads((directory / 'sample/run.json').read_text())
        self.assertTrue(sample['derive'])
        self.assertEqual(sample['forbidden_limit'], 9)
        self.assertEqual(sample['profile'], 'sample')
        status = invoke(CHECKER, [str(directory)], directory / 'checker.log')
        report = json.loads((directory / 'checked/report.json').read_text())
        self.assertEqual(status, 1)
        self.assertEqual(report['reason'], 'controls_required')
        self.assertFalse(report['claim_authorized'])


if __name__ == '__main__':
    unittest.main()
