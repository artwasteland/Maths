#!/usr/bin/env python3
"""Independent, bounded, one-record fixture11/F10 admission. No producer imports."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from control51_f9_check import LIMIT, FLOOR, PINS as F9_PINS, available, loads, regular, require, sha

PROFILE_PINS = {
    **F9_PINS,
    'research/unit-distance-22/data/forbidden-398.json': '8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c',
    'research/unit-distance-22/sources/amp/anc/graph6.txt': '4f7da8729d4818712e8718daabce29fb7f423cd7abec07eb195f0a04d6601a49',
    'research/gp-11/check/gp11check.py': 'ac1e3d94571fcabfd3f99d083ffd54cddb78ccff2138111913e67513b4560baa',
    'research/gp-11/check/selftest.py': '6cfa561fb4fe73bbf05762e0d4dea30a47446fbf16940ac40aa45e9fbfb83691',
    'research/gp-11/CONTRACT.md': 'dc4ea1bb1df5fc2011772724003799623778ebc694778965201fd18a4697ab21',
    'research/gp-11/PROOFS.md': 'b8b090aea7dd7dfa89f4c2468e029c5e69b351d3098d3ca0cf35568b397da22b',
    'research/gp-11/tools/write_result.py': '736ae0a31fe7ada02fb31a02908161aa105333d3d20ecc319f48b57760bbfcb0',
}
GUARD = 'research/gp-11/tools/guard.py'
PINS = {**PROFILE_PINS, GUARD: '9721b456c26f982fd9cc7ccd47eed6d382de71c512f3789fbc0a4defaea3913d'}
B11_SHA = 'ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f'
LABELG_SHA = '96e973e3a13442c6f626012b6b1059ef88e750aff284be6bfc6cd77ee7f185bf'


def manifest(graph):
    return {'profile': 'fixture11', 'input': 'input.g6',
            'input_sha256': hashlib.sha256((graph + '\n').encode()).hexdigest(),
            'records': ['records.jsonl'], 'unknown': 'UNKNOWN.g6', 'derive': False, 'forbidden_limit': 10}


def record_bytes(path, graph):
    regular(path)
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT and raw.endswith(b'\n') and raw.count(b'\n') == 1, 'record_framing')
    row = loads(raw)
    require(isinstance(row, dict) and set(row) == {'g6', 'verdict', 'cert'} and row['g6'] == graph, 'record_graph')
    cert = row['cert']
    require(isinstance(cert, dict), 'record_certificate')
    kind = cert.get('type')
    if row['verdict'] == 'embedded':
        require(kind == 'exact', 'record_exact')
    else:
        require(row['verdict'] == 'refuted' and kind in ('tree', 'null', 'real', 'null-dag', 'real-dag', 'sub', 'tu'), 'record_refutation')
        if kind == 'sub':
            require(type(cert.get('index')) is int and 0 <= cert['index'] < 398, 'record_indexed_F10')
        if kind == 'tu':
            end = cert.get('end')
            require(isinstance(end, dict) and set(end) == {'forbidden', 'map'} and
                    type(end['forbidden']) is int and 0 <= end['forbidden'] < 398, 'record_F10_TU')
    # Rational spelling, graph/map labels, equations and injectivity are checked
    # by the frozen parser/verifier, never approximated by a second proof parser.
    return raw, row


def accepted_report(report, graph, record_sha, verdict):
    require(report.get('status') == 'ACCEPT' and report.get('reason') == 'verified', 'admission_status')
    require(report.get('profile') == 'fixture11' and report.get('forbidden_limit') == 10 and
            report.get('scope') == 'fixture-only', 'admission_profile')
    counts = {'embedded': int(verdict == 'embedded'), 'refuted': int(verdict == 'refuted'), 'unknown': 0}
    require(report.get('input_count') == 1 and report.get('counts') == counts, 'admission_counts')
    require(report.get('input_sha256') == hashlib.sha256((graph + '\n').encode()).hexdigest(), 'admission_input')
    require(report.get('direct_rejections') == 0 and report.get('conditional') is False and
            report.get('conditional_minimal') == [], 'admission_complete')
    require(report.get('profile_sources') == PROFILE_PINS and
            report.get('checker_sha256') == F9_PINS['research/gp-10/check/gp10check.py'] and
            report.get('kernel_sha256') == F9_PINS['research/unit-distance-22/check/udcheck.py'], 'admission_sources')
    require(report.get('trusted_data_sha256') == {Path(k).name: PINS[k] for k in
            ('research/unit-distance-22/data/forbidden-398.json', 'research/unit-distance-22/data/tu-gadgets.json')}, 'admission_data')
    files = report.get('files', [])
    require(len(files) == 1 and files[0].get('sha256') == record_sha and files[0].get('hosts') is False, 'admission_consumed')


def verify_sources(root):
    for name, pin in PINS.items():
        regular(root / name)
        require(sha(root / name) == pin, 'frozen_source:' + name)
    require(sha(Path('/usr/bin/nauty-labelg')) == LABELG_SHA, 'canonicalizer_hash')


def tree_sample(pid):
    """Simultaneous RSS/CPU sample for the process and descendants (not summed peaks)."""
    pending, rss, cpu = [pid], 0, 0.0
    while pending:
        current = pending.pop()
        try:
            text = Path(f'/proc/{current}/stat').read_text().rsplit(')', 1)[1].split()
            cpu += (int(text[11]) + int(text[12])) / os.sysconf('SC_CLK_TCK')
            rss += int(text[21]) * os.sysconf('SC_PAGE_SIZE') // 1024
            pending += [int(v) for v in Path(f'/proc/{current}/task/{current}/children').read_text().split()]
        except (OSError, ValueError, IndexError):
            pass  # A child can disappear between /proc reads.
    return rss, cpu


def scratch_bytes(path):
    total = 0
    for p in path.rglob('*'):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except FileNotFoundError:
            pass
    return total


def monitored(command, log, seconds, scratch, stop=None):
    """External censoring cap; entire process group is killed on timeout/floor."""
    require(seconds is None or seconds > 0, 'positive_budget')
    started, minimum = time.monotonic(), available()
    require(minimum >= FLOOR, 'memory_floor')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               PYTHONINTMAXSTRDIGITS='4300', SYMPY_GROUND_TYPES='python')
    for key in ('PYTHONPATH', 'PYTHONHOME'):
        env.pop(key, None)
    env.update({k: '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')})
    peak, cpu, disk, reason = 0, 0.0, 0, 'completed'
    usage_path = log.with_name(log.name + '.rusage.json')
    with log.open('wb') as stream:
        child = subprocess.Popen(['/usr/bin/time', '-q', '-o', str(usage_path), '-f',
                                  '{"user_cpu_seconds":%U,"system_cpu_seconds":%S,"peak_process_rss_kib":%M}',
                                  '/usr/bin/nice', '-n', '15', *command], stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            tick = 0
            while child.poll() is None:
                minimum = min(minimum, available())
                rss, elapsed_cpu = tree_sample(child.pid)
                peak, cpu = max(peak, rss), max(cpu, elapsed_cpu)
                if tick % 4 == 0:
                    disk = max(disk, scratch_bytes(scratch))
                tick += 1
                if (stop is not None and stop.is_set()) or minimum < FLOOR or (seconds is not None and time.monotonic() - started > seconds):
                    reason = 'interrupted' if stop is not None and stop.is_set() else ('memory_floor' if minimum < FLOOR else 'timeout')
                    os.killpg(child.pid, signal.SIGKILL)
                    break
                time.sleep(0.25)
            child.wait()
        finally:
            # Also kill descendants if a wrapper returned with stray children.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
    usage = {'user_cpu_seconds': None, 'system_cpu_seconds': None, 'peak_process_rss_kib': None}
    if usage_path.exists() and usage_path.stat().st_size:
        usage.update(loads(usage_path.read_bytes()))
    return {**usage, 'exit': child.returncode, 'reason': reason, 'censored': reason != 'completed',
            'wall_seconds': time.monotonic() - started, 'sampled_tree_cpu_seconds': cpu,
            'sampled_peak_tree_rss_kib': peak, 'sampled_scratch_high_water_bytes': disk,
            'min_available_kib': minimum, 'memory_floor_events': int(minimum < FLOOR),
            'sampling': '250 ms RSS/CPU, 1 s logical scratch bytes; lower bounds, exited children may be missed'}


def check(work, seconds=540):
    started = time.monotonic()
    result = {'status': 'UNRESOLVED', 'scope': 'one-record fixture11/F10 admission'}
    # A workspace check is single-use. Production recovery always makes a new one.
    require(not (work / 'check/checked').exists() and not (work / 'check-result.json').exists(), 'fresh_check_required')
    try:
        verify_sources(work)
        graph = loads((work / 'packet.json').read_bytes())['graph']['g6']
        require(loads((work / 'check/run.json').read_bytes()) == manifest(graph), 'check_manifest')
        require((work / 'check/input.g6').read_text() == graph + '\n' and (work / 'check/UNKNOWN.g6').read_bytes() == b'', 'check_input')
        raw, row = record_bytes(work / 'record.jsonl', graph)
        (work / 'check/records.jsonl').write_bytes(raw)
        record_sha = hashlib.sha256(raw).hexdigest()
        result.update(record_sha256=record_sha, verdict=row['verdict'], g6=graph, bytes=len(raw),
                      field_degree=len(row['cert'].get('field', {}).get('minpoly', [])) - 1,
                      max_integer_token_chars=max((len(t) for t in __import__('re').findall(rb'-?\d+', raw)), default=0))
        command = [sys.executable, '-B', str(work / GUARD), '--', sys.executable, '-B',
                   str(work / 'research/gp-11/check/gp11check.py'), str(work / 'check')]
        cost = monitored(command, work / 'check.log', seconds, work / 'scratch')
        result.update(cost=cost, checker_exit=cost['exit'])
        require(cost['exit'] == 0 and not cost['censored'], 'checker_exit:' + cost['reason'])
        require('ACCEPT run verified' in (work / 'check.log').read_text().splitlines(), 'checker_accept_line')
        report = loads((work / 'check/checked/report.json').read_bytes())
        accepted_report(report, graph, record_sha, row['verdict'])
        require(sha(work / 'record.jsonl') == record_sha and sha(work / 'check/records.jsonl') == record_sha, 'record_changed')
        verify_sources(work)
        result.update(status='ACCEPTED', reason='verified', report_sha256=sha(work / 'check/checked/report.json'),
                      check_log_sha256=sha(work / 'check.log'))
    except (OSError, ValueError, TypeError, KeyError, MemoryError) as exc:
        result.update(reason=str(exc))
    result['wall_seconds'] = time.monotonic() - started
    (work / 'check-result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--seconds', type=float, default=540)
    args = parser.parse_args()
    answer = check(args.workspace.resolve(), args.seconds)
    print(answer['status'] + ' ' + answer['reason'])
    raise SystemExit(0 if answer['status'] == 'ACCEPTED' else 1)
