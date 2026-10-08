"""Audit saved coverage, verbatim seeds, source prefixes and checker identities."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from integration import configure


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args()
    configure()
    run = args.run_dir.resolve()
    seeds = json.loads((run / 'seeds/SEEDS.json').read_text())
    sample = json.loads((run / 'sample/run.json').read_text())
    official = json.loads((run / 'sample/checked/report.json').read_text())
    assembly = json.loads((run / 'ASSEMBLY.json').read_text())
    inputs = Path(sample['input']).read_text().splitlines()
    assert len(inputs) == len(set(inputs)) == 33162
    assert sha(sample['input']) == sample['input_sha256'] == assembly['input_sha256']
    assert sample['derive'] is True and sample['forbidden_limit'] == 9
    records, rows = {}, {}
    with (run / 'records.jsonl').open('rb') as stream:
        for line in stream:
            row = json.loads(line)
            assert row['g6'] not in records
            records[row['g6']] = line
            rows[row['g6']] = row
    assert set(records) == set(inputs)
    unknown = sorted(g for g, row in rows.items() if row['verdict'] == 'unknown')
    assert (run / 'UNKNOWN.g6').read_text().splitlines() == unknown
    preserved = 0
    with (run / 'seeds/accepted.jsonl').open('rb') as stream:
        for line in stream:
            row = json.loads(line)
            graph = row['g6']
            assert line == records[graph]
            assert hashlib.sha256(line).hexdigest() == seeds['selection'][graph]['record_sha256']
            assert seeds['outcomes'][graph]['status'] == 'ACCEPT'
            preserved += 1
    assert preserved == seeds['accepted_count']
    checker_identities = set()
    for check in seeds['checks']:
        report = json.loads((Path(check['directory']) / 'checked/report.json').read_text())
        checker_identities.add((report['checker_sha256'], report['kernel_sha256']))
    assert checker_identities == {(official['checker_sha256'], official['kernel_sha256'])}
    source_counts, changed_prefixes, bytes_read = Counter(), [], 0
    for source in seeds['sources']:
        source_counts.update(source['counts'])
        remaining = source['bytes_consumed']
        digest = hashlib.sha256()
        with Path(source['path']).open('rb') as stream:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
        bytes_read += source['bytes_consumed'] - remaining
        if remaining or digest.hexdigest() != source['sha256']:
            changed_prefixes.append(source['path'])
    counts = dict(Counter(row['verdict'] for row in rows.values()))
    assert counts == official['counts'] == assembly['record_counts']
    minimal = (run / 'sample/checked/minimal.g6').read_text().splitlines()
    assert minimal == official['minimal']
    assert len(minimal) == official['minimal_count'] == assembly['derived_minimal_count']
    assert len(official['conditional_minimal']) == assembly['conditional_count']
    assert official['status'] == 'ACCEPT' and assembly['final_line'] == 'ACCEPT run verified'
    result = {'audit': 'PASS', 'source_files': len(seeds['sources']),
              'source_counters': dict(source_counts), 'source_prefix_bytes_rehashed': bytes_read,
              'source_prefixes_changed_since_consumption': changed_prefixes,
              'changed_during_initial_read': [s['path'] for s in seeds['sources'] if s['changed_during_read']],
              'preserved_verbatim_seeds': preserved, 'coverage_by_exact_set': len(inputs),
              'record_counts': counts, 'unknown_exact_count': len(unknown),
              'minimal_count': len(minimal), 'conditional_minimal_count': assembly['conditional_count'],
              'whole_run_conditional': official.get('conditional'),
              'checker_identities': sorted(checker_identities),
              'records_sha256': sha(run / 'records.jsonl'),
              'unknown_sha256': sha(run / 'UNKNOWN.g6'),
              'minimal_sha256': sha(run / 'sample/checked/minimal.g6')}
    (run / 'AUDIT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
