#!/usr/bin/env python3
"""Hand-written stopped-f3 sets and guard-disable tests; no population replay."""
import ast
import gzip
import hashlib
import io
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import b11_campaign as c
import b11_final as f
import b11_residue as r
import b11_stopped as s
import make_packets as p
from test_b11_workflow import Tests as WorkflowTests
from test_b11_endgame import proof, encoded

# Independently written fixture identities/sets. No production sharder, audit,
# packet builder or selection result is used to construct expected sets.
A, B = 'J??????????', 'J?????????_'
NOT_RUN = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
           24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46,
           47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
           70, 71, 72, 73, 74, 75, 76, 77, 78, 79]
ALL_SHARDS = sorted([23, *NOT_RUN])
RAW_A = b'{ "g6": "J??????????", "verdict": "unknown", "cert": {"reason": "prior only", "budget": {"policy": "prior", "stages": []}} }\n'
RAW_B = b'{ "g6": "J?????????_", "verdict": "unknown", "cert": {"reason": "prior only", "budget": {"stages": []}} }\n'
REDS = []


class Tests(unittest.TestCase):
    bundle = WorkflowTests.bundle
    event = WorkflowTests.event

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='b11-stopped-')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for path in [self.root, *self.root.rglob('*')]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        self.tmp.cleanup()

    def refresh(self, directory):
        summary = p.loads((directory / 'summary.json').read_bytes())
        summary['artifacts'] = {x.name: p.sha(x) for x in directory.iterdir() if x.name != 'summary.json'}
        summary['records_sha256'] = hashlib.sha256(gzip.decompress((directory / 'records.jsonl.gz').read_bytes())).hexdigest()
        p.write(directory / 'summary.json', summary)

    def round_refresh(self, directory, manifest):
        manifest['artifacts'] = {n: p.sha(directory / n) for n in ('input.g6', 'unknown-records.jsonl.gz')}
        p.write(directory / 'round.json', manifest)

    def rounds(self, decided=False):
        base = self.bundle('f1-000', [(A, 'unknown'), (B, 'unknown')])
        directory = self.root / 'f3-input'
        directory.mkdir()
        (directory / 'input.g6').write_text(A + '\n' + B + '\n')
        (directory / 'unknown-records.jsonl.gz').write_bytes(gzip.compress(RAW_A + RAW_B, mtime=0))
        entry = {'round': 'f1', 'shard_index': 0, 'bundle': str(base), 'summary_sha256': p.sha(base / 'summary.json'),
                 'records_jsonl_gz_sha256': p.sha(base / 'records.jsonl.gz')}
        manifest = {'count': 2, 'overlay_order': ['f2', 'p2'], 'base': {'assigned': 2, 'shard_indices': [0]},
                    'counts': {'embedded': 0, 'refuted': 0, 'unknown': 2}, 'predecessors': [entry]}
        self.round_refresh(directory, manifest)
        returned = self.bundle('f3-023', [(B, 'embedded' if decided else 'unknown')])
        if decided:
            record = proof()
            record['g6'] = B  # Last two consecutive rational points form the only edge.
            (returned / 'records.jsonl.gz').write_bytes(gzip.compress(encoded(record), mtime=0))
        else:
            (returned / 'frontier.jsonl.gz').write_bytes(gzip.compress(encoded({'id': 7, 'g6': B}), mtime=0))
        p.write(returned / 'job.json', {'policy': 'long', 'shard_count': 80, 'shard_index': 23,
                'population_sha256': r.check.B11_SHA, 'selection': {'input_sha256': p.sha(directory / 'input.g6')}})
        self.refresh(returned)
        return directory, returned, manifest

    def export(self):
        config, event, source = self.event()
        out = self.root / 'export'
        shutil.copytree(source, out / event['case_id'])
        (out / 'records.jsonl').write_bytes(encoded(proof()))
        p.write(out / 'admissions.json', {'campaign_id': 'unit', 'entries': [{'g6': A, 'event': event}]})
        p.write(out / 'SHA256SUMS.json', c.tree_hashes(out))
        return out

    def assemble(self, decided=False, admitted=False, real=False, changed=False, state=False):
        directory, returned, manifest = self.rounds(decided)
        cheap = self.root / 'cheap.jsonl'
        cheap.write_bytes(b'')
        if state:
            cheap = self.root / 'cheap-state'
            cheap.mkdir()
            (cheap / 'certificates.jsonl').write_bytes(b'')
            db = sqlite3.connect(cheap / 'state.sqlite')
            db.executescript('CREATE TABLE accepted(seq INTEGER, g6 TEXT, verdict TEXT, hash TEXT, dep TEXT, origin TEXT);'
                             'CREATE TABLE blobs(hash TEXT, offset INTEGER, size INTEGER);')
            db.close()
        option = self.root / 'not-run.json'
        p.write(option, NOT_RUN)
        args = types.SimpleNamespace(out=self.root / 'assembly', input=directory / 'input.g6', round=directory,
                f3=self.root, cheap=cheap, not_run=str(option), python=c.control.DEFAULT_PYTHON,
                analyst_export=[self.export()] if admitted else [])
        original_audit = r.audit_round

        def audit(*a, **kw):
            return original_audit(*a, strict=False, **kw)

        def lean(command, **kw):
            if '--out' not in command:
                return
            stage = Path(command[command.index('--out') + 1])
            stage.mkdir()
            # Written fixture outputs, independent of the code under test.
            unknown = [] if decided and admitted else ([A] if decided else ([B] if admitted else [A, B]))
            (stage / 'UNKNOWN.g6').write_text(''.join(x + '\n' for x in unknown))
            (stage / 'unknown-records.jsonl').write_bytes(b''.join(encoded({'g6': x, 'verdict': 'unknown',
                      'cert': {'reason': 'assembly placeholder', 'budget': {}}}) for x in unknown))
            (stage / 'records.jsonl').write_bytes(b'')
            (stage / 'hosts.jsonl').write_bytes(b'')
            outputs = {n: {'sha256': p.sha(stage / n), 'bytes': (stage / n).stat().st_size}
                       for n in ('UNKNOWN.g6', 'unknown-records.jsonl', 'records.jsonl', 'hosts.jsonl')}
            p.write(stage / 'assembly.json', {'input': {'sha256': p.sha(args.input)}, 'outputs': outputs})
            if changed:
                (self.root / 'f3-047').mkdir()
                (self.root / 'f3-047/summary.json').write_text('{}')

        # Only the production-population pin is substituted for this two-graph
        # fixture. All stopped-round, bundle, set and admission checks execute.
        job = p.loads((returned / 'job.json').read_bytes())
        job['population_sha256'] = p.sha(args.input)
        p.write(returned / 'job.json', job)
        self.refresh(returned)
        with patch.object(r, 'audit_round', side_effect=audit), patch.object(r.check, 'B11_SHA', p.sha(args.input)):
            if real:
                receipt = r.assemble(args)
            else:
                with patch.object(r.subprocess, 'run', side_effect=lean):
                    receipt = r.assemble(args)
        return args, returned, receipt

    def test_hand_written_partition_and_driver_indices(self):
        self.assertEqual(s.shard(A), 47)
        self.assertEqual(s.shard(B), 23)
        directory, returned, _ = self.rounds()
        _, pending, audit = r.audit_round(directory, [returned], strict=False, not_run=NOT_RUN)
        self.assertEqual(pending, {A, B})
        info = audit['f3_stopped']
        self.assertEqual(info['carried_graphs'], [A])
        self.assertEqual(info['returned_graphs'], [B])
        self.assertEqual(info['f3_decisions'], [])
        self.assertEqual(info['returned_shards'], [23])
        self.assertEqual(info['not_run_shards'], NOT_RUN)
        self.assertEqual(s.selection([returned], 'auto'), NOT_RUN)

    def test_zero_returns_and_all_returns(self):
        directory, _, _ = self.rounds()
        self.assertEqual(r.audit_round(directory, [], strict=False, not_run=ALL_SHARDS)[1], {A, B})
        info = s.partition({A, B}, {i: ({A} if i == 47 else {B} if i == 23 else set()) for i in ALL_SHARDS}, [], {A}, {})
        self.assertEqual(info['carried_graphs'], [])
        self.assertEqual(info['f3_decisions'], [B])

    def test_decisions_and_admitted_carried_target(self):
        args, _, audit = self.assemble(decided=True, admitted=True)
        self.assertEqual(audit['expected_unknown'], [])  # {A,B} minus {B} minus {A}.
        self.assertEqual(audit['f3_stopped']['f3_decisions'], [B])
        self.assertEqual(audit['f3_stopped']['admitted_targets'], [A])
        self.assertEqual(audit['f3_stopped']['remaining_carried_graphs'], [])
        self.assertEqual((args.out / 'unknown-records.jsonl').read_bytes(), b'')

    def test_admitted_carry_keeps_returned_unknown(self):
        args, _, audit = self.assemble(admitted=True)
        self.assertEqual(audit['expected_unknown'], [B])  # {A,B} minus {} minus {A}.
        self.assertEqual(audit['f3_stopped']['remaining_carried_graphs'], [])
        self.assertEqual((args.out / 'UNKNOWN.g6').read_text(), B + '\n')

    def test_packets_disjoint_and_original_bytes_and_budget(self):
        args, returned, audit = self.assemble()
        self.assertEqual(audit['expected_unknown'], [A, B])
        result = p.build([returned], self.root / 'packets', select=args.out / 'UNKNOWN.g6',
                         round_input=args.round, assembly=args.out)
        self.assertEqual(result['packets'], 2)
        manifest = p.loads((self.root / 'packets/manifest.json').read_bytes())
        self.assertEqual([x['g6'] for x in manifest['packet_index']], [A, B])
        data = [p.loads((self.root / 'packets' / x['path']).read_bytes()) for x in manifest['packet_index']]
        first = self.root / 'packets' / manifest['packet_index'][0]['path']
        self.assertEqual((first.parent / 'original-unknown.jsonl').read_bytes(), RAW_A)
        self.assertEqual(data[0]['source']['f3_status'], 'NOT RUN')
        self.assertIsNone(data[0]['source']['summary_sha256'])
        self.assertEqual(data[0]['attempt_history']['prior_and_current_budget'], {'policy': 'prior', 'stages': []})
        self.assertEqual(data[0]['attempt_history']['count'], 0)
        self.assertNotIn('f3_status', data[1]['source'])
        self.assertEqual(data[1]['attempt_history']['prior_and_current_budget'], {})
        a = types.SimpleNamespace(out=self.root / 'campaign', assembly=args.out, packets=self.root / 'packets', repo=c.ROOT,
                python=c.control.DEFAULT_PYTHON, seconds=60, check_seconds=60, model='gpt-6-astra', effort='max')
        with c.control.coordinator_lock(a.out):
            config = c.prepare(a)
            self.assertEqual([case['g6'] for case in config['cases']], [A, B])
            for case in config['cases']:
                c.scan(a.out / 'seeds' / case['id'], case['files'])

    def test_packets_with_no_returned_bundles(self):
        args, _, audit = self.assemble()
        records, source = s.round_records(args.round)
        audit['f3'] = []
        audit['f3_stopped'] = s.partition({A, B}, {}, ALL_SHARDS, set(), source)
        s.restore_unknown(args.out, records, audit['f3_stopped'], set())
        s.bind_assembly(args.out, audit)
        result = p.build([], self.root / 'packets', select=args.out / 'UNKNOWN.g6',
                         round_input=args.round, assembly=args.out)
        self.assertEqual(result['packets'], 2)
        self.assertEqual((self.root / 'packets/UNKNOWN.g6').read_text(), A + '\n' + B + '\n')
        self.assertEqual((args.out / 'unknown-records.jsonl').read_bytes(), RAW_A + RAW_B)

    def test_real_tiny_assembly_and_final_seal_provenance(self):
        # Exercise the state-snapshot rename with output on the workspace mount.
        # The sandbox's /tmp can be a different mount from this worktree.
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory(prefix='.b11-stopped-state-', dir=c.ROOT)
        self.root = Path(self.tmp.name)
        args, _, audit = self.assemble(decided=True, real=True, state=True)
        command = audit['command']
        self.assertIn('--scratch', command)
        self.assertEqual(Path(command[command.index('--scratch') + 1]),
                         Path(command[command.index('--out') + 1]).parent)
        self.assertEqual((args.out / 'seed-0-snapshot.jsonl').read_bytes(), b'')
        self.assertEqual(audit['expected_unknown'], [A])
        self.assertEqual((args.out / 'unknown-records.jsonl').read_bytes(), RAW_A)
        report, _ = c.assembly_receipt(args.out)
        self.assertEqual(report['f3_stopped']['not_run_shards'], NOT_RUN)
        a = types.SimpleNamespace(run=self.root / 'sealed', assembly=args.out, assembly_sha256=c.sha(args.out / 'assembly.json'),
                input=args.input, dry_rehearsal=True, repo=c.ROOT, python=c.control.DEFAULT_PYTHON,
                transport_receipt=None, transport_root=None, transport_sha256=None)
        f.prepare(a)
        seal = p.loads((a.run / 'seal.json').read_bytes())
        self.assertEqual(seal['f3_stopped'], report['f3_stopped'])
        self.assertIn('residue-audit.json', seal['immutable'])

    def test_all_new_rejections_have_disable_cases(self):
        required = set()
        for node in ast.walk(ast.parse(Path(s.__file__).read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'require':
                required.add(node.args[1].value)
        self.assertEqual(required - {rule for mod, rule, _ in REDS if mod is s}, set())
        for mod, rules in [(r, {'f3_directory_job', 'f3_returns_changed'}),
                           (p, {'packet_sources_required', 'assembly_requires_round_input', 'output_input_collision'})]:
            self.assertEqual(rules - {rule for m, rule, _ in REDS if m is mod}, set())


def reject(name, module, rule, action):
    def test(self):
        with self.assertRaisesRegex(ValueError, '^' + re.escape(rule)):
            action(self)
    test.__name__ = 'test_reject_' + name
    setattr(Tests, test.__name__, test)
    REDS.append((module, rule, test.__name__))


for name, value in [('duplicate', [47, 47]), ('unsorted', [47, 23]), ('negative', [-1]), ('too_large', [80]),
                    ('bool', [True]), ('object', {}), ('string', ['47'])]:
    reject(name, s, 'not_run_sorted_unique_indices', lambda self, x=value: s.not_run_list(x))
reject('bad_directory', s, 'returned_directory_indices', lambda self: s.selection([self.root / 'f3-080'], 'auto'))


def bad_selection(self, value):
    path = self.root / 'list.json'
    p.write(path, value)
    s.selection([self.root / 'f3-023'], str(path))


reject('missing_not_run', s, 'not_run_returned_partition', lambda self: bad_selection(self, []))
reject('returned_also_not_run', s, 'not_run_returned_partition', lambda self: bad_selection(self, ALL_SHARDS))
reject('shard_partition', s, 'stopped_shard_partition', lambda self: s.partition({A, B}, {23: {B}}, [], {B}, {}))
reject('truncated_return', s, 'f3_exact_shard_assignment', lambda self: s.partition({A, B}, {23: set()}, NOT_RUN, set(), {}))
reject('wrong_return', s, 'f3_exact_shard_assignment', lambda self: s.partition({A, B}, {23: {A}}, NOT_RUN, {A}, {}))


def bad_round(self, kind):
    directory, _, manifest = self.rounds()
    record = directory / 'unknown-records.jsonl.gz'
    if kind == 'artifacts':
        del manifest['artifacts']['unknown-records.jsonl.gz']
        p.write(directory / 'round.json', manifest)
    elif kind == 'hash':
        record.write_bytes(gzip.compress(RAW_A.replace(b'prior only', b'tampered') + RAW_B, mtime=0))
    else:
        raw = {'duplicate': RAW_A + RAW_B + RAW_A, 'decided': RAW_A.replace(b'unknown', b'refuted') + RAW_B,
               'missing': RAW_A, 'extra': RAW_A + RAW_B.replace(b'J?????????_', b'J????????@?')}[kind]
        record.write_bytes(gzip.compress(raw, mtime=0))
        self.round_refresh(directory, manifest)
    s.round_records(directory)


for kind, rule in [('artifacts', 'carry_round_artifacts'), ('hash', 'carry_round_hash'), ('duplicate', 'carry_unknown_record'),
                   ('decided', 'carry_unknown_record'), ('missing', 'carry_round_record_coverage'), ('extra', 'carry_round_record_coverage')]:
    reject('round_' + kind, s, rule, lambda self, k=kind: bad_round(self, k))


def bad_job(self):
    directory, returned, _ = self.rounds()
    renamed = self.root / 'f3-024'
    returned.rename(renamed)
    r.audit_round(directory, [renamed], strict=False, not_run=NOT_RUN)


reject('directory_job', r, 'f3_directory_job', bad_job)
reject('late_return', r, 'f3_returns_changed', lambda self: self.assemble(changed=True))


def changed_source(self, artifact=False):
    directory, _, _ = self.rounds()
    _, info = s.round_records(directory)
    (directory / ('input.g6' if artifact else 'round.json')).write_text('{}\n')
    s.check_source(info)


reject('changed_round', s, 'carry_source_changed', changed_source)
reject('changed_artifact', s, 'carry_source_changed', lambda self: changed_source(self, True))


def missing_carried(self):
    (self.root / 'unknown-records.jsonl').write_bytes(b'')
    s.restore_unknown(self.root, {A: RAW_A}, {'carried_graphs': [A]}, set())


reject('missing_carried', s, 'carry_missing_from_assembly', missing_carried)


def bad_provenance(self, kind):
    args, _, _ = self.assemble()
    report = p.loads((args.out / 'assembly.json').read_bytes())
    if kind == 'binding':
        del report['outputs']['residue-audit.json']
    else:
        report['f3_stopped']['returned_shards'] = []
    s.provenance(args.out, report)


reject('audit_binding', s, 'stopped_audit_binding', lambda self: bad_provenance(self, 'binding'))
reject('provenance_equality', s, 'stopped_provenance_equality', lambda self: bad_provenance(self, 'equality'))
reject('require_assembly', s, 'round_packets_require_assembly_selection', lambda self: s.packet_source(self.root, None, [], None))


def bad_packets(self, kind):
    args, returned, audit = self.assemble()
    select = args.out / 'UNKNOWN.g6'
    bundles = [returned]
    if kind == 'selection':
        select = self.root / 'wrong.g6'
        select.write_text(A + '\n')
    elif kind == 'sources':
        bundles = []
    else:
        info = audit['f3_stopped']
        if kind == 'round':
            info['round'] = '/wrong-round'
        elif kind == 'carry':
            info['carried_graphs'] = [A, B]
        elif kind == 'record':
            info['carried_record_sha256'][A] = '0' * 64
        s.bind_assembly(args.out, audit)
    s.packet_source(args.round, args.out, bundles, select)


for kind, rule in [('selection', 'round_packets_assembly_selection'), ('sources', 'round_packets_returned_sources'),
                   ('round', 'round_packets_source_binding'), ('carry', 'round_packets_carry_set'), ('record', 'round_packets_record_binding')]:
    reject('packets_' + kind, s, rule, lambda self, k=kind: bad_packets(self, k))


def reexport_during_packets(self):
    args, returned, _ = self.assemble()
    validate = p.validate_bundle
    def changed(directory):
        summary = p.loads((directory / 'summary.json').read_bytes())
        summary['generation'] = 'changed after assembly source preflight'
        p.write(directory / 'summary.json', summary)
        return validate(directory)
    with patch.object(p, 'validate_bundle', side_effect=changed):
        p.build([returned], self.root / 'packets', select=args.out / 'UNKNOWN.g6',
                round_input=args.round, assembly=args.out)


reject('reexport_during_packets', s, 'round_packets_returned_sources', reexport_during_packets)


def overlapping_sources(self):
    args, _, audit = self.assemble()
    stage = self.root / 'packet-stage'
    (stage / 'sources').mkdir(parents=True)
    s.append_packets(stage, {A: RAW_A}, audit['f3_stopped'], set(), {A}, '', Path('/usr/bin/nauty-labelg'))


reject('source_overlap', s, 'round_packets_overlapping_sources', overlapping_sources)


def round_output_collision(self):
    args, returned, _ = self.assemble()
    p.build([returned], args.round / 'new-output', select=args.out / 'UNKNOWN.g6',
            round_input=args.round, assembly=args.out)


reject('round_output_collision', p, 'output_input_collision', round_output_collision)


def cli(self, extras):
    with patch.object(sys, 'argv', ['make_packets.py', '--out', str(self.root / 'out'), *extras]), \
            patch('sys.stderr', new_callable=io.StringIO) as err:
        result = p.main()
    if result == 2:
        raise ValueError(err.getvalue().strip().removeprefix('PACKET ERROR '))


reject('empty_cli', p, 'packet_sources_required', lambda self: cli(self, []))


def stray_assembly(self):
    _, returned, _ = self.rounds()
    cli(self, [str(returned), '--assembly', str(self.root)])


reject('stray_assembly', p, 'assembly_requires_round_input', stray_assembly)


def mutations():
    for module, rule, method in REDS:
        original = module.require
        def disabled(ok, reason):
            if reason != rule:
                original(ok, reason)
        with patch.object(module, 'require', disabled):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([Tests(method)]))
        assert not result.wasSuccessful(), 'SURVIVED: ' + method
        print('RED ' + module.__name__ + ':' + rule + ' ' + method)
    print('PASS all ' + str(len(REDS)) + ' stopped-f3 rejection tests fail with their guard disabled')
    # This regression also fails on a single-filesystem host by checking the
    # command contract; on split mounts the old invocation fails with EXDEV.
    import inspect
    source = inspect.getsource(r.assemble).replace('def assemble(', 'def without_scratch(')
    source = source.replace("                   '--scratch', str(Path(temporary)),\n", '')
    exec(compile(source, r.__file__, 'exec'), r.__dict__)
    try:
        with patch.object(r, 'assemble', r.without_scratch):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.TestSuite([Tests('test_real_tiny_assembly_and_final_seal_provenance')]))
        assert not result.wasSuccessful(), 'SURVIVED: scratch placement'
        print('RED scratch placement: real state-snapshot test fails when --scratch is omitted')
    finally:
        del r.without_scratch


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if '--mutations' in sys.argv:
        mutations()
