"""Verbatim first-wins seeds, checked by the official kernel before propagation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile

try:
    from .graph6 import save_graph6
    from .integration import invoke
except ImportError:
    from graph6 import save_graph6
    from integration import invoke

MAX_LINE = 8 * 1024 * 1024
CHECKER = Path(__file__).resolve().parents[1] / 'check' / 'gp10check.py'


@dataclass
class Seed:
    raw: bytes
    source: str
    line: int

    def record(self):
        return json.loads(self.raw)

    def origin(self):
        return {'path': self.source, 'line': self.line,
                'record_sha256': hashlib.sha256(self.raw).hexdigest()}


def forbidden_limit(edges):
    """The checker can encode complete vertex-order prefixes only."""
    lengths = {0: 0, 1: 4, 2: 5, 3: 6, 6: 7, 19: 8, 74: 9}
    if len(edges) not in lengths:
        raise ValueError('checker manifest requires a complete vertex-order forbidden prefix')
    return lengths[len(edges)]


def dependency(record):
    cert = record.get('cert')
    if not isinstance(cert, dict):
        return None
    if cert.get('type') in ('super', 'sub') and 'index' not in cert:
        target = cert.get('g6')
    elif cert.get('type') == 'tu' and isinstance(cert.get('end'), dict):
        target = cert['end'].get('refuted')
    else:
        return None
    return target if isinstance(target, str) else None


def select(paths, inputs):
    """Stream fixed file prefixes. Non-record rows and unknowns are not seeds."""
    selected, external, sources = {}, {}, []
    input_set = set(inputs)
    for path in map(Path, paths):
        path = path.resolve()
        before = path.stat()
        counts, sha = Counter(), hashlib.sha256()
        remaining, line_number = before.st_size, 0
        with path.open('rb') as stream:
            while remaining:
                raw = stream.readline(min(MAX_LINE + 1, remaining))
                if not raw:
                    raise ValueError(f'seed source shrank while reading: {path}')
                remaining -= len(raw)
                sha.update(raw)
                line_number += 1
                counts['lines'] += 1
                if len(raw) > MAX_LINE:
                    # The official checker cannot accept this framing. Drain
                    # without parsing or retaining an unbounded polynomial.
                    while remaining and not raw.endswith(b'\n'):
                        raw = stream.readline(min(MAX_LINE + 1, remaining))
                        if not raw:
                            raise ValueError(f'seed source shrank while reading: {path}')
                        remaining -= len(raw)
                        sha.update(raw)
                    counts['overlong_lines'] += 1
                    continue
                if not raw.strip():
                    counts['blank_lines'] += 1
                    continue
                try:
                    row = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError):
                    counts['invalid_json_lines'] += 1
                    continue
                if (not isinstance(row, dict) or not isinstance(row.get('g6'), str)
                        or row.get('verdict') not in ('embedded', 'refuted')):
                    counts['non_decided_or_non_record_lines'] += 1
                    continue
                code = row['g6']
                entry = Seed(raw, str(path), line_number)
                if code in input_set:
                    if code not in selected:
                        selected[code] = entry
                        counts['selected_input'] += 1
                    else:
                        counts['later_input_records_ignored'] += 1
                        if row['verdict'] != selected[code].record()['verdict']:
                            counts['later_conflicting_verdicts_ignored'] += 1
                elif (row['verdict'] == 'embedded' and isinstance(row.get('cert'), dict)
                      and row['cert'].get('type') == 'exact'):
                    if code not in external:
                        external[code] = entry
                    counts['external_exact_candidates'] += 1
                else:
                    counts['out_of_input_ignored'] += 1
        after = path.stat()
        sources.append({'path': str(path), 'bytes_consumed': before.st_size,
                        'sha256': sha.hexdigest(), 'counts': dict(counts),
                        'changed_during_read': (before.st_size, before.st_mtime_ns) !=
                                               (after.st_size, after.st_mtime_ns)})
        if after.st_size == before.st_size and after.st_mtime_ns != before.st_mtime_ns:
            raise ValueError(f'seed source changed in place while reading: {path}')
        print(json.dumps({'event': 'seed-source', 'path': str(path),
                          'selected_input': counts['selected_input']}), flush=True)
    # Only direct E-exact hosts are legal outside the run's input set.
    needed = set()
    for entry in selected.values():
        row = entry.record()
        cert = row.get('cert', {})
        if isinstance(cert, dict) and row['verdict'] == 'embedded' and cert.get('type') == 'super':
            target = dependency(row)
            if target in external:
                needed.add(target)
    return selected, {g: external[g] for g in sorted(needed)}, sources


def manifest(directory, inputs, records, limit, hosts=None, derive=False):
    directory.mkdir(parents=True, exist_ok=True)
    save_graph6(directory / 'input.g6', sorted(inputs))
    with (directory / 'records.jsonl').open('wb') as handle:
        for graph in sorted(records):
            handle.write(records[graph].raw)
    (directory / 'UNKNOWN.g6').write_text('')
    value = {'profile': 'sample', 'input': 'input.g6',
             'input_sha256': hashlib.sha256((directory / 'input.g6').read_bytes()).hexdigest(),
             'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6',
             'forbidden_limit': limit, 'derive': derive}
    if hosts:
        with (directory / 'hosts.jsonl').open('wb') as handle:
            for graph in sorted(hosts):
                handle.write(hosts[graph].raw)
        value['hosts'] = 'hosts.jsonl'
    (directory / 'run.json').write_text(json.dumps(value, indent=2) + '\n')


def validate(selected, hosts, directory, limit, sample_size=128):
    """Check dependency-closed samples; only explicit record ACCEPTs survive."""
    if not 1 <= sample_size <= 128:
        raise ValueError('seed validation sample size must be between 1 and 128')
    directory.mkdir(parents=True, exist_ok=True)
    outcomes, checks = {}, []
    graphs = sorted(selected)
    # An unterminated record would consume the next line. Isolate it so that
    # this framing failure cannot hide unrelated certificates in the sample.
    framed = [g for g in graphs if selected[g].raw.endswith(b'\n')]
    groups = [framed[i:i + sample_size] for i in range(0, len(framed), sample_size)]
    groups += [[g] for g in graphs if not selected[g].raw.endswith(b'\n')]
    for number, roots in enumerate(groups):
        closure, external, queue = set(), set(), list(roots)
        while queue:
            graph = queue.pop()
            if graph in closure:
                continue
            closure.add(graph)
            target = dependency(selected[graph].record())
            if target in selected:
                queue.append(target)
            elif target in hosts:
                external.add(target)
        job = directory / f'sample-{number:04d}'
        manifest(job, closure, {g: selected[g] for g in closure}, limit,
                 {g: hosts[g] for g in external})
        print(json.dumps({'event': 'seed-check-start', 'sample': number,
                          'roots': len(roots), 'with_dependencies': len(closure)}), flush=True)
        status = invoke(CHECKER, [str(job)], job / 'checker.log')
        checked = job / 'checked' / 'records.jsonl'
        rows = [json.loads(s) for s in checked.read_text().splitlines()] if checked.exists() else []
        by_graph = {r['g6']: r for r in rows}
        report_path = job / 'checked' / 'report.json'
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        # A fatal framing/tool failure may prevent dependency resolution.
        # Unconfirmed roots are dropped, never inferred from an exit status.
        for graph in roots:
            row = by_graph.get(graph, {'status': 'REJECT',
                                      'reason': report.get('reason', 'checker_unconfirmed')})
            outcomes[graph] = {'status': row['status'], 'reason': row['reason'],
                               'validation_directory': str(job), **selected[graph].origin()}
        checks.append({'directory': str(job), 'status': status,
                       'reason': report.get('reason', 'checker_unconfirmed'),
                       'roots': len(roots), 'with_dependencies': len(closure)})
        print(json.dumps({'event': 'seed-check-finished', 'sample': number, 'status': status,
                          'accepted_roots': sum(outcomes[g]['status'] == 'ACCEPT' for g in roots)}), flush=True)
    kept = {g: s for g, s in selected.items() if outcomes[g]['status'] == 'ACCEPT'}
    # Dependencies may have been checked more than once. Do not retain a
    # pointer if its independently selected target was dropped in another
    # sample (for example because of a tool failure).
    while True:
        drop = [g for g, s in kept.items()
                if dependency(s.record()) in selected and dependency(s.record()) not in kept]
        if not drop:
            break
        for graph in drop:
            del kept[graph]
            outcomes[graph].update(status='REJECT', reason='seed_dependency_dropped')
    used_hosts = {dependency(s.record()) for s in kept.values()}
    kept_hosts = {g: s for g, s in hosts.items() if g in used_hosts}
    return kept, kept_hosts, outcomes, checks


def load_seeds(paths, inputs, run, limit, validate_seeds=False, sample_size=128):
    base = Path(run) / 'seeds'
    base.mkdir(parents=True, exist_ok=True)
    selected, hosts, sources = select(paths, inputs)
    original = dict(selected)
    outcomes, checks = {}, []
    if validate_seeds:
        validation = Path(tempfile.mkdtemp(prefix='validation-', dir=base))
        selected, hosts, outcomes, checks = validate(selected, hosts, validation, limit, sample_size)
    report = {'sources': sources, 'selected_count': len(original), 'accepted_count': len(selected),
              'rejected_count': len(original) - len(selected), 'validated': validate_seeds,
              'host_count': len(hosts), 'outcomes': outcomes, 'checks': checks,
              'selection': {g: s.origin() for g, s in original.items()},
              'policy': 'first parsed decided input record wins; rejected selections have no later fallback'}
    (base / 'SEEDS.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    with (base / 'accepted.jsonl').open('wb') as stream:
        for g in sorted(selected):
            stream.write(selected[g].raw)
    print(json.dumps({'event': 'seeds-loaded', 'selected': len(original),
                      'accepted': len(selected), 'rejected': report['rejected_count'],
                      'hosts': len(hosts), 'validated': validate_seeds}), flush=True)
    return selected, hosts, report
