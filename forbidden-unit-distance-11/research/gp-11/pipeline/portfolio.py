"""Escalation adapters ported from the measured run; all output remains untrusted.

The wall caps are policy in stages.py. Saved CAS files are positive-search
proposals, never evidence for a negative verdict.
"""
from common import *
import ast
import collections
import pathlib
import numpy as np
import numeric
import rigid_system as mod
import msolve_exact
import algebra
from exact import graph6
from numeric_branch import normalize, enumerate_branches, branch_exact

def run(method, g, cap, directory, work, evidence, original, closure):
    OUT = work
    current_code = original
    search_code = g
    structure = {original: {'tu_closure_old_to_new': closure['old_to_new']}}
    numeric_evidence = lambda code: evidence
    original_fit = numeric.fit
    trace = []
    t = time.monotonic()

    def seeded_fit(n, edges, seed, restarts=3, penalty=True, initial=None):
        ev = numeric_evidence(current_code)
        if ev and ev['best_gap'] > 0.0001 and ev['coords']:
            points = ev['coords']
            if search_code != current_code and method not in ('msolve_sat', 'numeric_pin'):
                mp = structure[current_code]['tu_closure_old_to_new']
                points = [points[mp.index(i)] for i in range(n)]
            initial = normalize(points, edges[0])
            return original_fit(n, edges, seed, restarts=1, penalty=False, initial=initial)
        return original_fit(n, edges, seed, restarts, penalty, initial)

    def branch_only(g, directory):
        ev = numeric_evidence(g)
        meta = {'method': 'branch_radical_exactification', 'attempts': []}
        if not ev or ev.get('best_gap', 0) <= 0.0001 or (not ev.get('coords')):
            return (None, dict(meta, reason='no_separated_seed'))
        _, edges = graph6(g)
        frame = edges[0]
        candidates, nodes, steps = enumerate_branches(ev['coords'], edges, frame, time.monotonic() + 2)
        meta.update(branch_nodes=nodes, branch_configurations=len(candidates), placement_steps=steps)
        if not candidates or candidates[0][0] <= 0.0001:
            return (None, dict(meta, reason='no_separated_branch'))
        gap, p, signs = candidates[0]
        for bound in (16, 64, 256):
            t0 = time.monotonic()
            row = {'denominator_bound': bound}
            try:
                cert = branch_exact(g, p, frame, signs, steps, directory, min(8, cap / 3 - 0.1), bound)
                row.update(result='exact', seconds=time.monotonic() - t0)
                meta['attempts'].append(row)
                return (cert, meta)
            except Exception as exc:
                row['error'] = type(exc).__name__ + ':' + str(exc)[-300:]
            row['seconds'] = time.monotonic() - t0
            meta['attempts'].append(row)
        return (None, dict(meta, reason='no_exact_certificate'))

    def framed(g, directory):
        started = time.monotonic()
        ev = numeric_evidence(g)
        branch_attempts = []
        if ev and ev.get('best_gap', 0) > 0.0001 and ev.get('coords'):
            _, edges = graph6(g)
            frame = edges[0]
            candidates, nodes, steps = enumerate_branches(ev['coords'], edges, frame, time.monotonic() + 2)
            if candidates and candidates[0][0] > 0.0001:
                gap, p, signs = candidates[0]
                for bound in (16, 64, 256):
                    t0 = time.monotonic()
                    row = {'denominator_bound': bound}
                    try:
                        cert = branch_exact(g, p, frame, signs, steps, directory / 'branch-exact', min(8, cap / 10), bound)
                        return (cert, {'method': 'branch_radical_exactification', 'rank': None, 'branch_nodes': nodes, 'branch_attempts': branch_attempts + [{'result': 'exact', 'seconds': time.monotonic() - t0, 'denominator_bound': bound}], 'wall_seconds': time.monotonic() - started})
                    except Exception as exc:
                        row['error'] = type(exc).__name__ + ':' + str(exc)[-300:]
                    row['seconds'] = time.monotonic() - t0
                    branch_attempts.append(row)
        # Same solver; give preparation/conversion meaningful budgets too.
        import generic_escalated as gm
        rank, rm = mod.generic_rank(g)
        numeric.fit = seeded_fit
        try:
            cert, meta = gm.msolve_stage(g, directory, 19 - rank, max(0.01, cap - 0.2 - (time.monotonic() - started)), 3, 3)
        finally:
            numeric.fit = original_fit
        meta['rank'] = rank
        meta['numeric_seed_supplied'] = numeric_evidence(g) is not None
        meta['branch_exact_attempts'] = branch_attempts
        return (cert, meta)

    def targeted(g, directory):
        # Adapter of cloud/targeted.py: the identical algebra_search call, with
        # explicit frame/extra saturation/DAG. Verification is in this process,
        # avoiding a checker grandchild and preserving the process ceiling.
        n, edges = graph6(g)
        ev = numeric_evidence(current_code)
        pairs = []
        if ev:
            for pair, count in sorted(ev['collision_pairs'].items(), key=lambda kv: -kv[1])[:3]:
                import ast
                p = tuple(ast.literal_eval(pair))
                if g != current_code:
                    p = tuple(sorted((structure[current_code]['tu_closure_old_to_new'][v] for v in p)))
                if p not in edges:
                    pairs.append(p)
        deg = collections.Counter((v for e in edges for v in e))
        frames = sorted(edges, key=lambda e: (-deg[e[0]] - deg[e[1]], e))
        frame = frames[0] if frames[0] != edges[0] else frames[min(1, len(frames) - 1)]
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'configuration.json').write_text(json.dumps({'adapter_of': str(GP / 'cloud/targeted.py'), 'frame': frame, 'extra_sat': pairs, 'method': 'real', 'dag': True, 'cap': cap}, indent=2))
        cert, meta = algebra.algebra_search(g, 'real', cap - 0.2, frame=list(frame), extra_sat=pairs, dag=True, trace=lambda s: trace.append({'stage': s, 'seconds': time.monotonic() - t}))
        meta.update(adapter_of=str(GP / 'cloud/targeted.py'), frame=frame, extra_sat=pairs, dag=True)
        return (cert, meta)

    def targeted_components(g, directory):
        # CAS factor/collision information proposes saturation pairs only. The
        # final identity is generated and checked from the original edge system.
        digest = hashlib.sha256(current_code.encode()).hexdigest()[:16]
        options = []
        for parent in OUT.glob('esc-*-cases'):
            for file in (parent / digest).glob('sat-*/stats.json'):
                row = json.loads(file.read_text())
                systemfile = file.with_name('system.json')
                if not systemfile.exists() or not row.get('factors'):
                    continue
                saved = json.loads(systemfile.read_text())
                if saved.get('g6') != g:
                    continue
                bad = [{tuple(p) for p in f['coincidences']} for f in row['factors'] if f.get('coincidences')]
                cover = []
                while bad:
                    counts = collections.Counter((p for component in bad for p in component))
                    p = min(counts, key=lambda p: (-counts[p], p))
                    cover.append(p)
                    bad = [component for component in bad if p not in component]
                extra = sorted(set(map(tuple, row.get('pairs', []))) | set(cover))
                options.append((len(extra), row.get('degree', 100000), str(file), extra, saved['frame'], cover))
        if not options:
            return (None, {'reason': 'no_finite_component_diagnostics'})
        _, degree, file, extra, frame, cover = min(options)
        picked_target = None
        target_note = {}
        try:
            source_dir = pathlib.Path(file).parent
            saved = json.loads((source_dir / 'system.json').read_text())
            diagnostic = json.loads(pathlib.Path(file).read_text())
            parsed = msolve_exact.decode_output((source_dir / 'output.ms').read_text(), saved['variables'])
            factors = sorted(parsed['p'].factor()[1], key=lambda item: (item[0].degree(), tuple((str(c) for c in item[0]))))
            scores = {name: float('inf') for name in saved['variables'] if name[0] in 'xy'}
            considered = 0
            for (f, multiplicity), status in zip(factors, diagnostic['factors']):
                if status.get('coincidences') or status.get('real_roots'):
                    continue
                gcd, inverse, _ = (parsed['den'] % f).xgcd(f)
                if gcd != msolve_exact.Poly([1]):
                    continue
                values = [-(num % f * inverse) / divisor % f for num, divisor in parsed['numerators']] + [msolve_exact.Poly([0, 1]) % f]
                functions = dict(zip(parsed['parameter_order'], values))
                roots = np.roots([float(c) for c in reversed(list(f))])
                considered += 1
                for name in scores:
                    q = functions[name]
                    vals = np.polynomial.polynomial.polyval(roots, [float(c) for c in q])
                    scores[name] = min(scores[name], float(np.min(np.abs(np.imag(vals)))))
            if considered:
                candidate = max(scores, key=lambda name: (scores[name], name))
                if scores[candidate] > 1e-06:
                    picked_target = candidate
                target_note = {'nonreal_factors_examined': considered, 'numerical_projection_scores': scores, 'selection_is_heuristic': True}
        except Exception as exc:
            target_note = {'projection_hint_error': type(exc).__name__ + ':' + str(exc)[-250:]}
        directory.mkdir(parents=True, exist_ok=True)
        algorithm = os.environ.get('GP11_ALG', 'std')
        (directory / 'configuration.json').write_text(json.dumps({'source_diagnostics': file, 'source_degree': degree, 'component_cover': cover, 'extra_sat': extra, 'frame': frame, 'method': 'real', 'fglm': True, 'fglm_target': picked_target, 'target_note': target_note, 'dag': True, 'algorithm': algorithm, 'cap': cap}, indent=2))
        original_fglm = algebra.fglm_basis
        if picked_target:
            algebra.fglm_basis = lambda ctx, gb, seconds, target=None, variable_order=None: original_fglm(ctx, gb, seconds, target=picked_target, variable_order=variable_order)
        try:
            cert, meta = algebra.algebra_search(g, 'real', max(0.01, cap - 0.2 - (time.monotonic() - t)), frame=frame, extra_sat=extra, fglm=True, dag=True, algorithm=algorithm, trace=lambda s: trace.append({'stage': s, 'seconds': time.monotonic() - t}))
        finally:
            algebra.fglm_basis = original_fglm
        meta.update(method='targeted_real_component_cover_FGLM', source_diagnostics=file, source_degree=degree, component_cover=cover, extra_sat=extra, frame=frame)
        return (cert, meta)

    def saved_exact(g, directory):
        # A positive-certificate retry only. Proposal pins and saturation equations
        # need not be verified to accept coordinates: the original graph's exact
        # edge equations and distinctness are independently checked twice below.
        from round2_phase import isolated
        digest = hashlib.sha256(current_code.encode()).hexdigest()[:16]
        candidates = []
        checker_timed_out = False
        for file in OUT.glob('esc-*-stats.jsonl'):
            for line in file.read_text().splitlines():
                record = json.loads(line)
                if record['g6'] == current_code and record.get('meta', {}).get('checker_error', '').startswith('Deadline:'):
                    checker_timed_out = True
        for parent in OUT.glob('esc-*-cases'):
            for file in (parent / digest).glob('sat-*/stats.json'):
                detail = json.loads(file.read_text())
                systemfile = file.with_name('system.json')
                rawfile = file.with_name('output.ms')
                retry = detail.get('error', '').startswith('PhaseError:') or (checker_timed_out and detail.get('reason') == 'exact_embedding')
                if not retry or not systemfile.exists() or (not rawfile.exists()):
                    continue
                if not 0 < rawfile.stat().st_size < 8 * 1024 * 1024:
                    continue
                system = json.loads(systemfile.read_text())
                if system.get('g6') == g:
                    candidates.append((rawfile.stat().st_size, str(file), system))
        candidates.sort()
        meta = {'method': 'saved_RUR_positive_exactification', 'attempts': [], 'candidate_count': len(candidates), 'checker_timeout_retry': checker_timed_out, 'proposal_equations_omitted': True, 'acceptance': 'Ordinary exact coordinates; all original graph edges and pair distinctness checked by GP10 local and frozen official checkers.'}
        started = time.monotonic()
        for i, (size, file, system) in enumerate(candidates[:2]):
            remaining = cap - 0.3 - (time.monotonic() - started)
            if remaining < 1:
                break
            row = {'source_stats': file, 'output_bytes': size}
            begin = time.monotonic()
            try:
                system = dict(system, polynomials=[])

                def convert():
                    raw = pathlib.Path(file).with_name('output.ms').read_text()
                    parsed = msolve_exact.decode_output(raw, system['variables'])
                    return msolve_exact.certify(g, system, parsed)
                cert, detail = isolated(convert, remaining / (min(2, len(candidates)) - i))
                row.update(detail)
                row['seconds'] = time.monotonic() - begin
                meta['attempts'].append(row)
                if cert:
                    directory.mkdir(parents=True, exist_ok=True)
                    (directory / 'unverified-coordinate-proposal.json').write_text(json.dumps({'g6': g, 'cert': cert}, separators=(',', ':')))
                    available = cap - 0.3 - (time.monotonic() - started)
                    largest_rational = max((len(q) for point in cert['coords'] for axis in point for q in axis))
                    meta['largest_coordinate_rational_characters'] = largest_rational
                    if (checker_timed_out or largest_rational > 1000) and available > 1:
                        from reduce_exact import reduce_candidate
                        try:
                            reduced, detail = reduce_candidate(g, cert, directory / 'field-reduction', min(60, available))
                            cert = reduced
                            meta['field_reduction'] = detail
                        except Exception as exc:
                            meta['field_reduction_error'] = type(exc).__name__ + ':' + str(exc)[-250:]
                    return (cert, meta)
            except Exception as exc:
                row['error'] = type(exc).__name__ + ':' + str(exc)[-350:]
                row['seconds'] = time.monotonic() - begin
                meta['attempts'].append(row)
        meta['reason'] = 'no_timed_out_saved_candidate' if not candidates else 'no_exact_certificate'
        return (None, meta)
    if method == 'msolve_long':
        return framed(g, directory)
    if method == 'branch_exact':
        return branch_only(g, directory)
    if method == 'targeted':
        return targeted(g, directory)
    if method == 'targeted_components':
        return targeted_components(g, directory)
    if method == 'saved_exact':
        return saved_exact(g, directory)
    if method in ('msolve_sat', 'numeric_pin'):
        from saturated_embed import search, coordinate_pin_search
        numeric.fit = seeded_fit
        try:
            return (search if method == 'msolve_sat' else coordinate_pin_search)(g, evidence, directory, cap)
        finally:
            numeric.fit = original_fit
    raise ValueError('unknown_escalation_method:' + method)
