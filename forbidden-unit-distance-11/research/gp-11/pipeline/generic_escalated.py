"""Resumable graph6 input mode for G118 images and framed/pinned exact solving."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import time
from msolve_exact import limits, sha, invoke, decode_output, certify, parse_literal
from exact import verify, graph6, adjacency, textq
from hosts import database, monomorphism, check_mapping
from gp_field import program
from rigid_system import generic_rank, make_system, seed_for
from round2 import stored_system, load_system, write_json, task_id, HERE
from round2_phase import isolated

def frame_variants(code, k, frames=3, pins=2):
    n, edges = graph6(code)
    order = list(edges)
    random.Random(seed_for(code) + 49979687).shuffle(order)
    selected = [edges[0]] + [edge for edge in order if edge != edges[0]]
    selected = selected[:frames]
    return [{'frame': list(edge), 'variant': i * pins + j} for i, edge in enumerate(selected) for j in range(pins if k else 1)]

def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('method:wall_budget_exhausted')
    return value

def gp_output(code, out, points):
    lines = out.splitlines()
    if not lines or lines[-1] != 'GP_FIELD_OK':
        raise ValueError('pari:missing_exact_success')

    def item(label):
        found = [line[len(label):] for line in lines if line.startswith(label)]
        if len(found) != 1:
            raise ValueError('pari:output_field')
        return parse_literal(found[0] + ':')
    coeff = item('GP_FIELD_POLY ')
    interval = item('GP_FIELD_INTERVAL ')
    coords = item('GP_FIELD_COORDS ')
    if not all((type(c) is int for c in coeff)):
        raise ValueError('pari:noninteger_polynomial')
    cert = {'type': 'exact', 'field': {'minpoly': coeff, 'interval': [textq(str(v)) for v in interval]}, 'coords': [[[textq(str(v)) for v in coords[2 * i + j]] for j in (0, 1)] for i in range(points)]}
    return verify(code, cert, max_refinements=256)

def host_stage(code, directory, host, seconds):
    began = time.monotonic()
    deadline = began + seconds
    meta = {'method': 'G118_image', 'cap_seconds': seconds}
    cert = None
    directory.mkdir(parents=True, exist_ok=True)
    try:
        n, edges = graph6(code)
        pattern = adjacency(n, edges)
        mapping, nodes = isolated(lambda: monomorphism(pattern, host['adj'], 2000000), min(3.0, remaining(deadline)))
        meta.update(map=mapping, mapping_nodes=nodes)
        if mapping is None:
            raise ValueError('host:map_node_cap' if nodes > 2000000 else 'host:no_map')
        check_mapping(pattern, host['adj'], mapping)
        points = [host['expressions'][i] for i in mapping]
        write_json(directory / 'proposal.json', {'g6': code, 'map': mapping, 'expressions': points})
        source = isolated(lambda: program(points), min(1.5, remaining(deadline)))
        seed = int(sha(code.encode())[:16], 16)
        source = 'setrand(' + str(seed) + ');\n' + source
        script = directory / 'field.gp'
        script.write_text(source)
        call_cap = max(0.001, remaining(deadline) - min(1.0, remaining(deadline) / 4))
        started = time.monotonic()
        with (directory / 'field.log').open('w') as stdout, (directory / 'field.stderr').open('w') as stderr:
            child = subprocess.Popen(['gp', '-fq', '-s', '128000000', str(script)], stdout=stdout, stderr=stderr)
            try:
                status = child.wait(timeout=call_cap)
                timed_out = False
            except subprocess.TimeoutExpired:
                child.kill()
                status = child.wait()
                timed_out = True
            except BaseException:
                child.kill()
                child.wait()
                raise
        meta.update(pari_seconds=time.monotonic() - started, pari_cap_seconds=call_cap, returncode=status, timeout=timed_out, seed=seed, threads=1, input_sha256=sha(source.encode()))
        if timed_out:
            raise TimeoutError('pari:timeout')
        if status:
            raise ValueError('pari:child_exit:' + str(status))
        output = directory / 'field.log'
        if output.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('pari:output_size')
        raw = output.read_text()
        meta['output_sha256'] = sha(raw.encode())
        cert = isolated(lambda: gp_output(code, raw, n), remaining(deadline))
        meta.update(reason='exact_embedding', degree=len(cert['field']['minpoly']) - 1)
    except Exception as exc:
        meta['reason'] = type(exc).__name__ + ':' + str(exc)[:300]
    meta['wall_seconds'] = time.monotonic() - began
    write_json(directory / 'stats.json', meta)
    return (cert, meta)

def msolve_stage(code, directory, k, seconds, frames, pins):
    began = time.monotonic()
    deadline = began + seconds
    meta = {'method': 'framed_pinned_msolve', 'cap_seconds': seconds, 'attempts': [], 'triage': False}
    cert = None
    directory.mkdir(parents=True, exist_ok=True)
    try:
        if k is None:
            raise ValueError('rigidity:unsupported_graph')
        variants = frame_variants(code, k, frames, pins)
        for i, variant in enumerate(variants):
            if deadline - time.monotonic() < 0.05:
                break
            target = directory / f'attempt-{i:02d}'
            target.mkdir(exist_ok=True)
            row = {'frame': variant['frame'], 'variant': variant['variant'], 'k': k, 'triage': False}
            started = time.monotonic()
            try:
                saved = isolated(lambda: stored_system(make_system(code, frame=variant['frame'], variant=variant['variant'])), min(15.0, remaining(deadline)))
                write_json(target / 'system.json', saved)
                system = load_system(target / 'system.json')
                row['pins'] = system['pins']
                left = remaining(deadline)
                cap = max(0.001, (left - min(2.0, left / 4)) / (len(variants) - i))
                raw, call = invoke(system, target, cap, parse=False)
                row.update(call)
                if raw is not None:

                    def check():
                        parsed = decode_output(raw, system['variables'], progress=lambda p: write_json(target / 'conversion-progress.json', p))
                        return certify(code, system, parsed)
                    cert, checked = isolated(check, min(20.0, remaining(deadline)))
                    row.update(checked)
                if row.get('triage'):
                    meta['triage'] = True
            except Exception as exc:
                row['reason'] = type(exc).__name__ + ':' + str(exc)[:400]
            progress = target / 'conversion-progress.json'
            if progress.exists():
                for key, value in json.loads(progress.read_text()).items():
                    row.setdefault(key, value)
            row['wall_seconds'] = time.monotonic() - started
            meta['attempts'].append(row)
            write_json(target / 'stats.json', row)
            if cert is not None or meta['triage']:
                break
        meta['reason'] = 'exact_embedding' if cert is not None else 'rigid_no_distinct_real_solution' if meta['triage'] else 'no_certificate_within_budget'
    except Exception as exc:
        meta['reason'] = type(exc).__name__ + ':' + str(exc)[:300]
    meta['wall_seconds'] = time.monotonic() - began
    if cert is not None:
        meta['degree'] = len(cert['field']['minpoly']) - 1
    write_json(directory / 'stats.json', meta)
    return (cert, meta)
