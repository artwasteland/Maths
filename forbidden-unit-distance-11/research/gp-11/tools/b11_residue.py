#!/usr/bin/env python3
"""Audit round selection, assemble B11, and compare UNKNOWN against round evidence.

No stage code is imported or changed. No certificate is mathematically accepted
here. All 80 returns are required unless --not-run explicitly stops f3.
Final replay remains mandatory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import b11_campaign as campaign
import b11_check as check
import make_packets as packets
import b11_stopped as stopped

require, sha, loads, atomic = campaign.require, campaign.sha, campaign.loads, campaign.atomic
ROOT, HERE = campaign.ROOT, campaign.HERE
ROUND_SHA = '4f4b94f3e43daea1ee1c8b2bd0b71f5af7d8143bb59edd1ccfffdb4405c4597a'


def f3_job(job, assigned, input_sha, indices):
    require(job['policy'] == 'long' and job['shard_count'] == 80 and job['selection']['input_sha256'] == input_sha and
            job['population_sha256'] == check.B11_SHA, 'f3_job')
    index = job['shard_index']
    require(type(index) is int and 0 <= index < 80 and index not in indices and
            all(int.from_bytes(hashlib.sha256(c.encode()).digest()[:8], 'big') % 80 == index for c in assigned), 'f3_sharding')
    indices.add(index)


def unknown_matches(path, expected):
    actual, expected = packets.graph_list(path), sorted(expected)
    extra, missing = sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual))
    require(actual == expected, 'assembled_unknown_mismatch:' + packets.compact({
        'extra_count': len(extra), 'missing_count': len(missing), 'extra_first20': extra[:20], 'missing_first20': missing[:20]}))


def bundle(path, decisions, receipt=None):
    summary, job, pin = packets.validate_bundle(path)
    if receipt is not None:
        require(pin['summary_sha256'] == receipt['summary_sha256'] and
                pin['artifact_hashes']['records.jsonl.gz'] == receipt['records_jsonl_gz_sha256'], 'round_bundle_pin')
    assigned = set(packets.graph_list(path / 'assigned.g6'))
    expected = set(packets.graph_list(path / 'input.g6'))
    unknown = set(packets.graph_list(path / 'UNKNOWN.g6'))
    statuses, seen, actual_unknown, h = {}, set(), set(), hashlib.sha256()
    for _, raw, row in packets.rows(path / 'records.jsonl.gz', check.LIMIT):
        code, verdict = row['g6'], row['verdict']
        require(code not in seen and verdict in ('embedded', 'refuted', 'unknown'), 'bundle_record_header')
        seen.add(code)
        h.update(raw)
        if verdict != 'unknown':
            require(code not in decisions or decisions[code] == verdict, 'round_decision_conflict')
            decisions.setdefault(code, verdict)
        else:
            actual_unknown.add(code)
        if code in assigned:
            statuses[code] = verdict
    require(seen == expected and set(statuses) == assigned and actual_unknown == unknown and unknown <= assigned, 'bundle_exact_coverage')
    require(h.hexdigest() == summary['records_sha256'], 'bundle_raw_hash')
    require({v: Counter(statuses.values())[v] for v in ('embedded', 'refuted', 'unknown')} == summary['counts'], 'bundle_actual_counts')
    # Detect concurrent re-export while reading.
    require(sha(path / 'summary.json') == pin['summary_sha256'], 'bundle_changed')
    campaign.check_hashes(path, pin['artifact_hashes'])
    return assigned, statuses, pin, job


def audit_round(round_dir, f3, strict=True, not_run=None):
    r = loads((round_dir / 'round.json').read_bytes())
    if strict:
        require(sha(round_dir / 'round.json') == ROUND_SHA, 'f3_round_pin')
        require(r['count'] == 525 and r['base']['assigned'] == 17505 and r['base']['shard_count'] == 192, 'round_population')
    campaign.check_hashes(round_dir, r['artifacts'])
    initial = set(packets.graph_list(round_dir / 'input.g6'))
    require(len(initial) == r['count'] and r['overlay_order'] == ['f2', 'p2'], 'round_contract')
    selected, decisions, statuses, receipts = [], {}, {}, []
    base_indices, base_unknown, base_codes = set(), set(), set()
    predecessors = r['predecessors']
    ranks = {'f1': 0, 'f1b': 0, 'f2': 1, 'p2': 2}
    require([ranks[x['round']] for x in predecessors] == sorted(ranks[x['round']] for x in predecessors), 'round_order')
    for entry in predecessors:
        path = Path(entry['bundle']).resolve()
        assigned, current, pin, job = bundle(path, decisions, entry)
        name = entry['round']
        if name in ('f1', 'f1b'):
            require(entry['shard_index'] not in base_indices and not assigned & base_codes, 'base_overlap')
            base_indices.add(entry['shard_index'])
            base_codes.update(assigned)
            base_unknown.update(c for c, v in current.items() if v == 'unknown')
        else:
            require(assigned <= base_unknown, 'overlay_not_base_unknown')
        for code, verdict in current.items():
            if statuses.get(code, 'unknown') == 'unknown':
                statuses[code] = verdict
        selected.append(path)
        receipts.append(pin)
        if not_run is not None and len(selected) % 25 == 0:
            print(f'AUDIT PREDECESSORS {len(selected)}/{len(predecessors)}', flush=True)
    require(base_indices == set(r['base']['shard_indices']) and len(base_codes) == r['base']['assigned'], 'base_coverage')
    if strict:
        base_input = round_dir.parent / 'f1-input/input.g6'
        require(sha(base_input) == r['base']['input_sha256'] and set(packets.graph_list(base_input)) == base_codes, 'base_input_equality')
    for entry in r.get('displaced_f1b_bundles', []):
        # Check contradictions without giving displaced proofs selection priority.
        bundle(Path(entry['bundle']).resolve(), decisions, entry)
        require(any(x['round'] == 'f1' and x['shard_index'] == entry['shard_index'] for x in predecessors), 'f1_first')
    require({c for c, v in statuses.items() if v == 'unknown'} == initial, 'round_unknown_equality')
    require({v: Counter(statuses.values())[v] for v in ('embedded', 'refuted', 'unknown')} == r['counts'], 'round_counts')
    seen, pending, f3_receipts, indices = set(), set(), [], set()
    returned = {}
    for path in f3:
        assigned, current, pin, job = bundle(path, decisions)
        require(not assigned & seen and assigned <= initial, 'f3_assignment_overlap_or_extra')
        if strict or not_run is not None:
            f3_job(job, assigned, sha(round_dir / 'input.g6'), indices)
        if not_run is not None:
            require(path.name == f"f3-{job['shard_index']:03d}", 'f3_directory_job')
            returned[job['shard_index']] = assigned
        seen.update(assigned)
        pending.update(c for c, v in current.items() if v == 'unknown')
        f3_receipts.append(pin)
    receipt = {'round_sha256': sha(round_dir / 'round.json'), 'predecessors': receipts,
               'f3': f3_receipts, 'before_f3': len(initial)}
    if not_run is None:
        require(seen == initial and (not strict or indices == set(range(80))), 'f3_complete_coverage')
    else:
        _, source = stopped.round_records(round_dir)
        info = stopped.partition(initial, returned, not_run, pending, source)
        receipt['f3_stopped'] = info
        pending.update(info['carried_graphs'])
    receipt['after_f3'] = len(pending)
    return selected, pending, receipt


def admitted_exports(exports, pending):
    seeds, decided = [], set()
    for path in exports:
        hashes = loads((path / 'SHA256SUMS.json').read_bytes())
        campaign.check_hashes(path, hashes)
        require(campaign.tree_hashes(path) == {**hashes, 'SHA256SUMS.json': sha(path / 'SHA256SUMS.json')}, 'export_file_set')
        inventory = loads((path / 'admissions.json').read_bytes())
        expected = []
        for entry in inventory['entries']:
            event = entry['event']
            require(event['status'] == 'ACCEPTED' and entry['g6'] == event['g6'] and event['campaign_id'] == inventory['campaign_id'], 'export_admission')
            code = entry['g6']
            require(code in pending and code not in decided, 'export_target')
            source = path / event['case_id']
            require(source.parent == path and source.name.startswith('packet-'), 'export_path')
            campaign.check_hashes(source, event['artifacts'])
            raw, row = check.record_bytes(source / 'record.jsonl', code)
            result = loads((source / 'check-result.json').read_bytes())
            require(result['status'] == 'ACCEPTED' and result['checker_exit'] == 0 and result['record_sha256'] == hashlib.sha256(raw).hexdigest() and
                    result['report_sha256'] == sha(source / 'report.json') and result['check_log_sha256'] == sha(source / 'check.log') and
                    'ACCEPT run verified' in (source / 'check.log').read_text().splitlines(), 'export_receipt')
            check.accepted_report(loads((source / 'report.json').read_bytes()), code, hashlib.sha256(raw).hexdigest(), row['verdict'])
            expected.append((source / 'record.jsonl', hashlib.sha256(raw).hexdigest()))
            decided.add(code)
        # At most the analyst residue (hundreds), each record remains capped.
        with (path / 'records.jsonl').open('rb') as stream:
            for source, pin in expected:
                require(hashlib.sha256(stream.readline(check.LIMIT + 1)).hexdigest() == pin, 'export_stream')
            require(stream.read(1) == b'', 'export_stream')
        seeds.append(path / 'records.jsonl')
    return seeds, decided


def assemble(args):
    require(not args.out.exists(), 'new_assembly_required')
    require(sha(args.input) == check.B11_SHA, 'population_input_pin')
    f3 = sorted(p.resolve() for p in args.f3.glob('f3-[0-9][0-9][0-9]') if (p / 'summary.json').exists())
    option = getattr(args, 'not_run', None)
    not_run = stopped.selection(f3, option) if option is not None else None
    if not_run is None:
        require([p.name for p in f3] == [f'f3-{i:03d}' for i in range(80)], 'f3_complete_coverage')
    selected, pending, receipt = audit_round(args.round, f3, not_run=not_run)
    analyst_seeds, decided = admitted_exports(args.analyst_export, pending)
    expected = sorted(pending - decided)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.b11-assembly-', dir=args.out.parent) as temporary:
        stage = Path(temporary) / 'assembled'
        command = [args.python, '-B', str(HERE / 'lean_assemble11.py'), '--input', str(args.input), '--out', str(stage),
                   '--scratch', str(Path(temporary)),
                   '--rewrite-outside-ends', '--forbidden-limit', '10', '--no-propagate', str(args.cheap),
                   *map(str, selected), *map(str, f3), *map(str, analyst_seeds)]
        # Full operational invocation; this script's fixture tests never call it at population scale.
        subprocess.run(['/usr/bin/nice', '-n', '15', *command], check=True)
        unknown_matches(stage / 'UNKNOWN.g6', expected)
        if not_run is not None:
            records, _ = stopped.round_records(args.round)
            stopped.restore_unknown(stage, records, receipt['f3_stopped'], decided)
        subprocess.run(['/usr/bin/nice', '-n', '15', args.python, '-B', str(HERE / 'lean_assemble11.py'),
                        '--check', str(stage), '--input', str(args.input)], check=True)
        # Recheck all pinned source artifacts after assembly before publishing.
        for pin in receipt['predecessors'] + receipt['f3']:
            path = Path(pin['bundle'])
            require(sha(path / 'summary.json') == pin['summary_sha256'], 'assembly_source_changed')
            campaign.check_hashes(path, pin['artifact_hashes'])
        receipt.update(analyst_exports={str(p): sha(p / 'SHA256SUMS.json') for p in args.analyst_export},
                       admitted=len(decided), expected_unknown=expected, unknown_sha256=sha(stage / 'UNKNOWN.g6'),
                       command=command, scope='structural only; final frozen replay required')
        if not_run is None:
            atomic(stage / 'residue-audit.json', receipt)
        else:
            stopped.check_source(receipt['f3_stopped'])
            require(f3 == sorted(p.resolve() for p in args.f3.glob('f3-[0-9][0-9][0-9]')
                                 if (p / 'summary.json').exists()), 'f3_returns_changed')
            stopped.bind_assembly(stage, receipt)
        stage.rename(args.out)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--round', type=Path, default=ROOT / 'research/gp-11/pipeline/cloud/f3-input')
    p.add_argument('--f3', type=Path, required=True, help='parent with f3-NNN checked returns')
    p.add_argument('--not-run', help='explicit stopped f3: sorted JSON shard-index list file, or auto (compute and print)')
    p.add_argument('--cheap', type=Path, required=True, help='read-only completed cheap pipeline state (all 448708 inputs)')
    p.add_argument('--analyst-export', type=Path, action='append', default=[])
    p.add_argument('--input', type=Path, default=ROOT / 'research/gp-11/data/B11.g6')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--python', default=campaign.control.DEFAULT_PYTHON)
    a = p.parse_args()
    for name in ('round', 'f3', 'cheap', 'input', 'out'):
        setattr(a, name, getattr(a, name).resolve())
    a.analyst_export = [x.resolve() for x in a.analyst_export]
    try:
        result = assemble(a)
        print('ASSEMBLED UNKNOWN=' + str(len(result['expected_unknown'])))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('RESIDUE ERROR ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
