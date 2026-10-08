#!/usr/bin/env python3
"""Evidence for an explicitly stopped f3 round. NOT RUN is not a checker result.

Only round-input UNKNOWN bytes are carried. Interrupted scratch is never read.
This module imports no pipeline stage and makes no mathematical decisions.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import make_packets as packets

require, sha, loads = packets.require, packets.sha, packets.loads


def shard(code):
    return int.from_bytes(hashlib.sha256(code.encode('ascii')).digest()[:8], 'big') % 80


def not_run_list(value):
    require(isinstance(value, list) and all(type(i) is int and 0 <= i < 80 for i in value)
            and value == sorted(set(value)), 'not_run_sorted_unique_indices')
    return value


def selection(f3, option):
    """A present but invalid return is an error, never silently NOT RUN."""
    returned = [int(p.name[3:]) for p in f3]
    require(len(set(returned)) == len(returned) and all(0 <= i < 80 for i in returned), 'returned_directory_indices')
    missing = sorted(set(range(80)) - set(returned))
    result = missing if option == 'auto' else loads(Path(option).read_bytes())
    not_run_list(result)
    require(result == missing, 'not_run_returned_partition')
    print('F3 RETURNED ' + packets.compact(sorted(returned)), flush=True)
    print('F3 NOT RUN ' + packets.compact(result), flush=True)
    return result


def round_records(directory):
    manifest = loads((directory / 'round.json').read_bytes())
    artifacts = manifest['artifacts']
    require({'input.g6', 'unknown-records.jsonl.gz'} <= artifacts.keys(), 'carry_round_artifacts')
    for name, pin in artifacts.items():
        require(sha(packets.safe_file(directory, name)) == pin, 'carry_round_hash')
    codes = packets.graph_list(directory / 'input.g6')
    records = {}
    for _, raw, row in packets.rows(directory / 'unknown-records.jsonl.gz', packets.RECORD_LIMIT):
        code = row['g6']
        require(code not in records and row['verdict'] == 'unknown' and isinstance(row['cert']['budget'], dict),
                'carry_unknown_record')
        records[code] = raw
    require(set(records) == set(codes) and len(codes) == manifest['count'], 'carry_round_record_coverage')
    return records, {'round': str(directory), 'round_sha256': sha(directory / 'round.json'), 'artifacts': artifacts}


def partition(initial, returned, not_run, pending, source):
    not_run_list(not_run)
    indices = sorted(returned)
    require(not set(indices) & set(not_run) and set(indices) | set(not_run) == set(range(80)), 'stopped_shard_partition')
    for index, assigned in returned.items():
        require(assigned == {code for code in initial if shard(code) == index}, 'f3_exact_shard_assignment')
    seen = set().union(*returned.values())
    carried = {code for code in initial if shard(code) in not_run}
    # Exact per-shard equality plus the shard partition proves disjoint/exhaustive
    # graph coverage; a second, logically redundant rejection would add no audit.
    return {**source, 'status': 'STOPPED', 'not_run_status': 'NOT RUN', 'shard_count': 80,
            'shard_rule': 'int.from_bytes(SHA256(graph6).digest()[:8], big) % 80',
            'returned_shards': indices, 'not_run_shards': not_run,
            'carried_graphs': sorted(carried), 'returned_graphs': sorted(seen),
            'f3_decisions': sorted(seen - pending),
            'scope': 'No checked f3 return for NOT RUN shards; any interrupted work is excluded.'}


def check_source(info):
    directory = Path(info['round'])
    require(sha(directory / 'round.json') == info['round_sha256'], 'carry_source_changed')
    for name, pin in info['artifacts'].items():
        require(sha(packets.safe_file(directory, name)) == pin, 'carry_source_changed')


def restore_unknown(stage, records, info, admitted):
    """Lean emits placeholders; replace carried ones with byte-identical input."""
    carried = set(info['carried_graphs']) - admitted
    path = stage / 'unknown-records.jsonl'
    current = list(packets.rows(path, packets.RECORD_LIMIT))
    require(carried <= {row['g6'] for _, _, row in current}, 'carry_missing_from_assembly')
    path.write_bytes(b''.join(records[row['g6']] if row['g6'] in carried else raw for _, raw, row in current))
    info['carried_record_sha256'] = {code: hashlib.sha256(records[code]).hexdigest() for code in info['carried_graphs']}
    info['admitted_targets'] = sorted(admitted)
    info['remaining_carried_graphs'] = sorted(carried)


def bind_assembly(stage, audit):
    """Bind the audit to the externally retained assembly digest and final seal."""
    packets.write(stage / 'residue-audit.json', audit)
    report = loads((stage / 'assembly.json').read_bytes())
    report['f3_stopped'] = audit['f3_stopped']
    for name in ('unknown-records.jsonl', 'residue-audit.json'):
        report['outputs'][name] = {'sha256': sha(stage / name), 'bytes': (stage / name).stat().st_size}
    packets.write(stage / 'assembly.json', report)
    (stage / 'assembly.json.sha256').write_text(sha(stage / 'assembly.json') + '  assembly.json\n')


def provenance(directory, report):
    info = report.get('f3_stopped')
    if info is None:
        return None
    not_run_list(info['not_run_shards'])
    require('residue-audit.json' in report['outputs'] and
            sha(directory / 'residue-audit.json') == report['outputs']['residue-audit.json']['sha256'], 'stopped_audit_binding')
    audit = loads((directory / 'residue-audit.json').read_bytes())
    require(audit.get('f3_stopped') == info, 'stopped_provenance_equality')
    return info


def packet_source(directory, assembly, bundles, select):
    # Local import avoids a cycle through campaign -> make_packets.
    import b11_campaign as campaign
    require(assembly is not None and select is not None, 'round_packets_require_assembly_selection')
    report, _ = campaign.assembly_receipt(assembly)
    info = provenance(assembly, report)
    require(info is not None and packets.graph_list(select) == packets.graph_list(assembly / 'UNKNOWN.g6'),
            'round_packets_assembly_selection')
    records, source = round_records(directory)
    require(all(info[k] == v for k, v in source.items()), 'round_packets_source_binding')
    audit = loads((assembly / 'residue-audit.json').read_bytes())
    pins = audit['f3']
    require([str(b) for b in bundles] == sorted(p['bundle'] for p in pins) and
            all(sha(Path(p['bundle']) / 'summary.json') == p['summary_sha256'] for p in pins), 'round_packets_returned_sources')
    carried = {code for code in records if shard(code) in info['not_run_shards']}
    require(sorted(carried) == info['carried_graphs'] and not carried & set(info['returned_graphs']), 'round_packets_carry_set')
    require(all(hashlib.sha256(records[c]).hexdigest() == info['carried_record_sha256'][c] for c in carried),
            'round_packets_record_binding')
    return {code: records[code] for code in carried}, {
        **info, 'returned_summaries': {p['bundle']: p['summary_sha256'] for p in pins}}


def append_packets(stage, records, info, chosen, assignments, python, labelg):
    require(not assignments & records.keys(), 'round_packets_overlapping_sources')
    codes = sorted(records.keys() if chosen is None else records.keys() & chosen)
    packets.canonical(codes, labelg)
    source_dir = stage / 'sources' / 'round-input'
    source_dir.mkdir()
    receipt = {**info, 'id': 'round-input', 'mode': 'b11', 'kind': 'round-input', 'status': 'NOT RUN',
               'bundle': info['round'], 'summary_sha256': None,
               'evidence': 'Only original round-input UNKNOWN; no f3 attempt, frontier or checker receipt.'}
    packets.write(source_dir / 'receipt.json', receipt)
    published = []
    for code in codes:
        directory = stage / 'packets' / ('packet-' + hashlib.sha256(code.encode()).hexdigest()[:16])
        published.append(packets.make_packet(directory, code, {'id': None}, loads(records[code]), [], [], receipt, python,
                                             original_raw=records[code]))
    check_source(info)
    return published, receipt
