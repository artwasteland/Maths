#!/usr/bin/env python3
"""Seal a new B11 run, then perform exactly one guarded final replay.

prepare never checks the population. launch requires the externally retained seal
digest and refuses retries, cached reports, or incomplete non-rehearsal inputs.
Exit: 0 verified; 2 integrity; 3 incomplete; 4 checker rejection; 74 transport;
75 resource stop; 76 censored timeout. No publishing or git mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
import b11_campaign as campaign
import b11_check as check
import lean_assemble11 as lean
import make_packets as packets
import b11_stopped as stopped

require, sha, loads, atomic = campaign.require, campaign.sha, campaign.loads, campaign.atomic
ROOT = campaign.ROOT
CONTROLS = {**{f'B{n}p': f'controls/B10/controls/B{n}p' for n in range(4, 10)},
            'B10': 'controls/B10', 'named11': 'controls/named11', 'regressions': 'controls/B10/controls/regressions'}
PREDICTION_SHA = '12a37f573d087c304dc6ab629d2abf49ec555f038174ca63605aa53fd750b906'
B10_SHA = '3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f'
L10_SHA = 'a899e36cec0f135f253e0c9942d2fecd29280da44189a01d00752e8a5af971b8'
GP10_SUMS = 'b8e196cea3802ab6bc74050bb345691f54b6a25bec3dc54fb6026892034a7b45'
CONTROL51_STATUS = '820ec2c7d3bf66808cace80947793fa725b2254c82210459a66f763fdcb3d504'


class Incomplete(ValueError):
    pass


class Transport(ValueError):
    pass


def complete_gate(unknown, rehearsal):
    try:
        require(rehearsal or not unknown, 'assembled_UNKNOWN_not_empty')
    except ValueError as exc:
        raise Incomplete(str(exc)) from exc


def inside(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts and p != Path('.'), 'run_relative_path')
    path = root / p
    require(path.resolve().is_relative_to(root.resolve()) and not any((root / parent).is_symlink() for parent in (p, *p.parents)), 'run_path_escape')
    return path


def control_complete(directory, name):
    report = loads((directory / 'checked/report.json').read_bytes())
    require(report.get('status') == 'ACCEPT' and report.get('reason') == 'verified' and report.get('profile') == name, 'control_profile')
    require(report.get('counts', {}).get('unknown') == 0 and report.get('direct_rejections') == 0 and
            report.get('conditional') is False and report.get('conditional_minimal') == [], 'control_complete')
    if name == 'B10':
        require(report.get('input_count') == 33162 and report.get('input_sha256') == B10_SHA and report.get('forbidden_limit') == 9 and
                report.get('minimal_file') == 'L10.g6' and report.get('minimal_count') == 324, 'control_B10')
        codes = packets.graph_list(directory / 'checked/L10.g6')
        require(len(codes) == 324 and codes == report.get('minimal') and sha(directory / 'checked/L10.g6') == L10_SHA, 'control_L10')
        provenance = loads((directory / 'checked/F10-provenance.json').read_bytes())
        require(provenance == {'status': 'COMPLETE', 'members': 324, 'L10_sha256': L10_SHA,
                'forbidden_sha256': check.PINS['research/unit-distance-22/data/forbidden-398.json']}, 'control_F10_provenance')
    else:
        require(report.get('control', {}).get('status') == 'PASS', 'control_PASS')
    return report


def run_inputs(directory, root, stack=()):
    """Recursively bind every manifest-consumed path; reject symlinks and cycles."""
    require(directory not in stack and len(stack) < 8, 'control_cycle')
    m = loads((directory / 'run.json').read_bytes())
    require(isinstance(m.get('records'), list) and bool(m['records']), 'manifest_records')
    names = ['run.json', m['input'], m.get('unknown', 'UNKNOWN.g6'), *m['records']]
    names += [m[k] for k in ('hosts', 'provenance', 'cross_checks', 'minimal_claim') if k in m]
    if 'predictions' in m:
        names.append(m['predictions']['path'])
    found = set()
    for name in names:
        path = inside(directory, name)
        require('checked' not in path.relative_to(root).parts and 'execution' not in path.relative_to(root).parts, 'input_output_overlap')
        campaign.control.regular(path)
        found.add(path)
    require(sha(inside(directory, m['input'])) == m['input_sha256'], 'manifest_input_hash')
    for name, child in m.get('controls', {}).items():
        sub = inside(directory, child)
        control_complete(sub, name)
        found.update(run_inputs(sub, root, (*stack, directory)))
    return found


def frozen_sources(repo, target):
    check.verify_sources(repo)
    files = dict(check.PINS)
    require(sha(repo / 'research/gp-10/data/SHA256SUMS') == GP10_SUMS, 'GP10_input_pins')
    files['research/gp-10/data/SHA256SUMS'] = GP10_SUMS
    for line in (repo / 'research/gp-10/data/SHA256SUMS').read_text().splitlines():
        pin, name = line.split()
        files['research/gp-10/data/' + name] = pin
    files['research/gp-11/data/B11.g6'] = check.B11_SHA
    files['research/gp-11/data/SHA256SUMS'] = sha(repo / 'research/gp-11/data/SHA256SUMS')
    campaign.check_hashes(repo, files)
    for name in files:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, dest)
    campaign.check_hashes(target, files)
    return files


def control51_tree(repo, b10):
    evidence = repo / 'research/gp-11/control51/final-status.json'
    require(sha(evidence) == CONTROL51_STATUS, 'control51_status_pin')
    status = loads(evidence.read_bytes())
    require(status['status'] == 'PASS' and status['execution']['exit'] == 0 and status['pass_line'] == 'PASS B10 COMPLETE derived=324' and
            sha(b10 / 'MERGE.json') == status['merge_sha256'], 'control51_fresh_merge')
    merge = loads((b10 / 'MERGE.json').read_bytes())
    campaign.check_hashes(b10, merge['files'])
    for name, pin in status['artifacts'].items():
        if name.startswith('B10-final/'):
            require(sha(b10 / name.removeprefix('B10-final/')) == pin, 'control51_receipt')
    return evidence


def transport(args):
    if args.transport_receipt is None:
        require(args.transport_root is None and args.transport_sha256 is None, 'transport_options')
        return None
    try:
        require(args.transport_root is not None and sha(args.transport_receipt) == args.transport_sha256, 'transport_receipt_digest')
        hashes = loads(args.transport_receipt.read_bytes())
        campaign.check_hashes(args.transport_root, hashes)
        return {'receipt_sha256': args.transport_sha256, 'parts': hashes}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Transport(str(exc)) from exc


def preflight_assembly(assembly, input_path, expected_sha, rehearsal):
    require(sha(assembly / 'assembly.json') == expected_sha, 'external_assembly_digest')
    report, files = campaign.assembly_receipt(assembly)
    stopped.provenance(assembly, report)
    require(report['input']['sha256'] == sha(input_path), 'assembly_input')
    lean.structural_check(assembly, input_path)
    count = len(packets.graph_list(input_path))
    unknown = packets.graph_list(assembly / 'UNKNOWN.g6')
    complete_gate(unknown, rehearsal)
    require(rehearsal or (sha(input_path) == check.B11_SHA and count == 448708), 'final_B11_input')
    require(not rehearsal or 0 < count <= 100, 'small_rehearsal_only')
    return report, files, count, len(unknown)


def prepare(args):
    require(not args.run.exists(), 'new_run_required')
    shipment = transport(args)
    report, assembly_files, count, pending = preflight_assembly(args.assembly, args.input, args.assembly_sha256, args.dry_rehearsal)
    if not args.dry_rehearsal:
        require(args.b10 is not None and args.named11 is not None and args.chronology is not None, 'final_prerequisites')
        require(sha(args.predictions) == PREDICTION_SHA, 'precommitted_predictions')
        chronology = loads(args.chronology.read_bytes())
        require(chronology.get('predictions_sha256') == PREDICTION_SHA and chronology.get('predates_B11_run') is True and
                re.fullmatch('[0-9a-f]{40}', chronology.get('commit', '')) is not None and
                bool(chronology.get('attested_by')) and bool(chronology.get('evidence')), 'prediction_chronology_attestation')
        control_complete(args.b10, 'B10')
        control_complete(args.named11, 'named11')
        control51_evidence = control51_tree(args.repo, args.b10)
    payload_bytes = sum((args.assembly / p).stat().st_size for p in assembly_files)
    # Disk admission includes source/control staging plus 2 GiB scratch, 0.5 GiB
    # output, 10 GiB reserve. Rehearsals reserve just 64 MiB.
    controls_bytes = 0
    for source in (() if args.dry_rehearsal else (args.b10, args.named11)):
        controls_bytes += sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
    args.run.parent.mkdir(parents=True, exist_ok=True)
    required_disk = payload_bytes + controls_bytes + (64 * 1024**2 if args.dry_rehearsal else int(12.5 * 1024**3))
    require(shutil.disk_usage(args.run.parent).free >= required_disk, 'disk_headroom')
    with tempfile.TemporaryDirectory(prefix='.b11-seal-', dir=args.run.parent) as tmp:
        stage = Path(tmp) / 'run'
        stage.mkdir()
        for name in assembly_files:
            dest = inside(stage, name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.assembly / name, dest)
        if (args.assembly / 'residue-audit.json').exists():
            shutil.copyfile(args.assembly / 'residue-audit.json', stage / 'residue-audit.json')
        shutil.copyfile(args.input, stage / 'input.g6')
        sources = frozen_sources(args.repo, stage / 'source')
        m = {'profile': 'fixture11' if args.dry_rehearsal else 'B11', 'input': 'input.g6',
             'input_sha256': sha(stage / 'input.g6'), 'records': ['records.jsonl', 'unknown-records.jsonl'],
             'hosts': 'hosts.jsonl', 'unknown': 'UNKNOWN.g6'}
        if args.dry_rehearsal:
            m.update(forbidden_limit=10, derive=False)
        else:
            for name, source in (('B10', args.b10), ('named11', args.named11)):
                pins = campaign.tree_hashes(source)  # Refuse links/special files; never follow outside data.
                shutil.copytree(source, stage / 'controls' / name)
                campaign.check_hashes(stage / 'controls' / name, pins)
            shutil.copyfile(args.predictions, stage / 'PREDICTIONS.md')
            shutil.copyfile(args.chronology, stage / 'prediction-chronology.json')
            shutil.copyfile(control51_evidence, stage / 'control51-final-status.json')
            m.update(controls=CONTROLS, predictions={'path': 'PREDICTIONS.md', 'sha256': PREDICTION_SHA})
        atomic(stage / 'run.json', m)
        consumed = run_inputs(stage, stage)
        # Freeze copies of prerequisite ACCEPT reports before the checker rewrites
        # their working checked/ outputs (nested controls replay more than once).
        initial_reports = {}
        for p in list((stage / 'controls').rglob('*')):
            if not p.is_file() or 'checked' not in p.relative_to(stage).parts:
                continue
            name = p.relative_to(stage).as_posix()
            dest = stage / 'prerequisites' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            initial_reports[name] = sha(p)
        all_files = campaign.tree_hashes(stage)
        immutable = {k: v for k, v in all_files.items() if 'checked' not in Path(k).parts or k.startswith('prerequisites/')}
        require(all(p.relative_to(stage).as_posix() in immutable for p in consumed), 'immutable_consumed_inputs')
        seal = {'schema': 'b11-final-v1', 'profile': m['profile'], 'dry_rehearsal': args.dry_rehearsal,
                'input_count': count, 'unknown_count': pending, 'immutable': immutable, 'initial_reports': initial_reports,
                'source_pins': sources, 'python': args.python, 'input_sha256': m['input_sha256'],
                'python_sha256': sha(Path(args.python)),
                'assembly_sha256': args.assembly_sha256, 'transport': shipment, 'required_disk_bytes': required_disk,
                'launcher_sha256': sha(Path(__file__)), 'check_wrapper_sha256': sha(Path(check.__file__)),
                'scope': 'DRY REHEARSAL ONLY' if args.dry_rehearsal else 'B11 final replay; publication gates remain separate'}
        if report.get('f3_stopped') is not None:
            seal['f3_stopped'] = stopped.provenance(stage, report)
        atomic(stage / 'seal.json', seal)
        seal_sha = sha(stage / 'seal.json')
        (stage / 'seal.json.sha256').write_text(seal_sha + '  seal.json\n')
        for name in (*immutable, 'seal.json', 'seal.json.sha256'):
            (stage / name).chmod(0o444)
        (stage / 'execution').mkdir()
        (stage / 'checked').mkdir()
        # Input directories cannot accidentally be replaced; only checker outputs
        # and the execution log/claim directory are writable. The owner can still
        # chmod files, so externally retained hashes remain the authority.
        stage.rename(args.run)
        for directory in [args.run, *(p for p in args.run.rglob('*') if p.is_dir())]:
            rel = directory.relative_to(args.run)
            writable = (rel.parts[:1] == ('execution',) or
                        ('checked' in rel.parts and rel.parts[:1] != ('prerequisites',)))
            directory.chmod(0o755 if writable else 0o555)
    print('SEALED ' + str(args.run) + ' ' + seal_sha)
    return seal_sha


def accepted_final(report, log, exit_code, run, seal):
    require(exit_code == 0, 'final_exit')
    require('ACCEPT run verified' in log.splitlines(), 'final_accept_line')
    require(report.get('status') == 'ACCEPT' and report.get('reason') == 'verified', 'final_status')
    require(report.get('profile') == seal['profile'] and report.get('input_count') == seal['input_count'] and
            report.get('input_sha256') == seal['input_sha256'], 'final_identity')
    require(report.get('profile_sources') == check.PROFILE_PINS, 'final_sources')
    require(report.get('direct_rejections') == 0, 'final_rejections')
    # Every selected stream, including an empty UNKNOWN stream and hosts, must
    # be in the checker's consumed-file receipts with the exact sealed digest.
    expected = {str(run / name): seal['immutable'][name] for name in ('records.jsonl', 'unknown-records.jsonl', 'hosts.jsonl')}
    actual = {x['path']: x['sha256'] for x in report.get('files', [])}
    require(actual == expected and len(report['files']) == 3, 'final_consumed')
    if seal['dry_rehearsal']:
        require(report.get('scope') == 'fixture-only' and report.get('counts', {}).get('unknown') == seal['unknown_count'], 'rehearsal_scope')
        return
    require(seal['profile'] == 'B11' and seal['input_count'] == 448708 and seal['input_sha256'] == check.B11_SHA and
            report.get('frozen_B11_sha256') == check.B11_SHA, 'final_external_digest')
    require(report.get('counts', {}).get('unknown') == 0 and report.get('conditional') is False and
            report.get('conditional_minimal') == [], 'final_complete')
    require(report.get('minimal_file') == 'L11.g6', 'final_L11_name')
    minimal = packets.graph_list(run / 'checked/L11.g6')
    require(minimal == report.get('minimal') and len(minimal) == report.get('minimal_count') and
            report.get('artifacts', {}).get('checked/L11.g6') == sha(run / 'checked/L11.g6') and
            report.get('artifacts', {}).get('checked/minimality.jsonl') == sha(run / 'checked/minimality.jsonl'), 'final_L11_evidence')
    require(report.get('F10_provenance') == {'status': 'COMPLETE', 'members': 324, 'L10_sha256': L10_SHA,
            'forbidden_sha256': check.PINS['research/unit-distance-22/data/forbidden-398.json']}, 'final_F10')
    require(set(report.get('controls', {})) == set(CONTROLS), 'final_controls')
    for name, path in CONTROLS.items():
        control_complete(run / path, name)
        require(report['controls'][name] == {'path': path + '/checked/report.json', 'sha256': sha(run / path / 'checked/report.json')}, 'final_control_receipt')
    require(report.get('predictions', {}).get('sha256') == PREDICTION_SHA, 'final_predictions')


def launch(run, seal_sha, seconds=None):
    # Separate run directories must not accidentally start concurrent full
    # replays on this host. The inherited flock releases after a crash.
    with campaign.control.coordinator_lock(Path('/tmp/gp11-final-lane')):
        return launch_locked(run, seal_sha, seconds)


def launch_locked(run, seal_sha, seconds=None):
    require(sha(run / 'seal.json') == seal_sha and (run / 'seal.json.sha256').read_text() == seal_sha + '  seal.json\n', 'external_seal_digest')
    seal = loads((run / 'seal.json').read_bytes())
    require(seal['schema'] == 'b11-final-v1' and seal['launcher_sha256'] == sha(Path(__file__)) and
            seal['check_wrapper_sha256'] == sha(Path(check.__file__)), 'launcher_changed')
    campaign.check_hashes(run, seal['immutable'])
    campaign.check_hashes(run, seal['initial_reports'])
    check.verify_sources(run / 'source')
    require(sha(Path(seal['python'])) == seal['python_sha256'], 'python_changed')
    m = loads((run / 'run.json').read_bytes())
    require(m['profile'] == seal['profile'] and bool(seal['dry_rehearsal']) == (m['profile'] == 'fixture11'), 'launch_profile')
    complete_gate((run / 'UNKNOWN.g6').stat().st_size, seal['dry_rehearsal'])
    require(not any((run / 'execution').iterdir()) and not any((run / 'checked').iterdir()), 'single_launch_only')
    # O_EXCL handles a simultaneous second launcher after the preflight checks.
    with (run / 'execution/STARTED.json').open('x') as started:
        json.dump({'seal_sha256': seal_sha, 'pid': os.getpid(), 'environment': {
            'python': seal['python'], 'platform': sys.platform, 'labelg_sha256': sha(Path('/usr/bin/nauty-labelg'))}}, started)
        started.flush()
        os.fsync(started.fileno())
    command = [seal['python'], '-B', str(run / 'source' / check.GUARD), '--', seal['python'], '-B',
               str(run / 'source/research/gp-11/check/gp11check.py'), str(run)]
    if not seal['dry_rehearsal']:
        command += ['--b11-sha256', check.B11_SHA]
    cost = check.monitored(command, run / 'execution/check.log', (seconds or 540) if seal['dry_rehearsal'] else seconds, Path('/tmp/gp10-check'))
    atomic(run / 'execution/cost.json', {**cost, 'command': command})
    log = (run / 'execution/check.log').read_text()
    code, status = 4, 'REJECTED'
    if cost['reason'] == 'memory_floor' or 'RESOURCE STOP' in log:
        code, status = 75, 'RESOURCE_STOP'
    elif cost['censored']:
        code, status = 76, 'TIMEOUT'
    else:
        try:
            campaign.check_hashes(run, seal['immutable'])
            result = loads((run / 'checked/report.json').read_bytes())
            accepted_final(result, log, cost['exit'], run, seal)
            code, status = 0, 'VERIFIED_REHEARSAL' if seal['dry_rehearsal'] else 'VERIFIED_B11'
        except (OSError, ValueError, KeyError, TypeError) as exc:
            status += ': ' + str(exc)
    artifacts = {p.relative_to(run).as_posix(): sha(p) for p in run.rglob('*') if p.is_file() and
                 ('checked' in p.relative_to(run).parts or 'execution' in p.relative_to(run).parts)}
    atomic(run / 'execution/outcome.json', {'status': status, 'exit': code, 'seal_sha256': seal_sha, 'artifacts': artifacts})
    print(status)
    return code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'launch'))
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--repo', type=Path, default=ROOT)
    p.add_argument('--assembly', type=Path)
    p.add_argument('--assembly-sha256')
    p.add_argument('--input', type=Path, default=ROOT / 'research/gp-11/data/B11.g6')
    p.add_argument('--b10', type=Path)
    p.add_argument('--named11', type=Path)
    p.add_argument('--predictions', type=Path, default=ROOT / 'research/gp-11/PREDICTIONS.md')
    p.add_argument('--chronology', type=Path, help='reviewed commit chronology attestation JSON')
    p.add_argument('--transport-root', type=Path)
    p.add_argument('--transport-receipt', type=Path, help='JSON map of part paths to independently retained SHA256')
    p.add_argument('--transport-sha256')
    p.add_argument('--python', default=campaign.control.DEFAULT_PYTHON)
    p.add_argument('--dry-rehearsal', action='store_true', help='fixture11 only, <=100 inputs, never a final B11 result')
    p.add_argument('--seal-sha256', help='independently retained digest printed by prepare')
    p.add_argument('--seconds', type=int, help='optional observation cap; a timeout never succeeds')
    a = p.parse_args()
    for k, v in vars(a).items():
        if isinstance(v, Path):
            setattr(a, k, v.resolve())
    try:
        if a.action == 'prepare':
            require(a.assembly is not None and a.assembly_sha256 is not None, 'assembly_required')
            prepare(a)
            return 0
        return launch(a.run, a.seal_sha256, a.seconds)
    except Transport as exc:
        print('TRANSPORT ERROR ' + str(exc), file=sys.stderr)
        return 74
    except Incomplete as exc:
        print('INCOMPLETE ' + str(exc), file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('LAUNCH ERROR ' + str(exc), file=sys.stderr)
        return 75 if str(exc) == 'memory_floor' else 2


if __name__ == '__main__':
    raise SystemExit(main())
