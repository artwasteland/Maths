"""Framed/pinned GP10 msolve with selected noncollision saturation variables.

Additional equations are producer choices. Only ordinary E-exact certificates
are emitted, and every original edge and distinctness condition is checked.
"""
from common import *
import json, ast, collections
from fractions import Fraction
import sympy as sp
import numpy as np
import rigid_system
from numeric_branch import normalize
from exact import graph6
from rigid_system import make_system, generic_rank
from msolve_exact import invoke, decode_output, certify
from round2_phase import isolated
from algebra import cycles4

def augment(system, pairs):
    names = system['variables']
    extra = ['sat' + str(i) for i in range(len(pairs))]
    allnames = names + extra
    syms = sp.symbols(','.join(allnames))
    v = dict(zip(allnames, syms))
    a, b = system['frame']
    P = [(sp.Integer(0), sp.Integer(0)) for _ in range(system['n'])]
    P[b] = (sp.Integer(1), sp.Integer(0))
    for i in range(system['n']):
        if i not in (a, b):
            P[i] = (v['x' + str(i)], v['y' + str(i)])
    polynomials = [{tuple(e) + (0,) * len(extra): c for e, c in p.items()} for p in system['polynomials']]
    _, edges = graph6(system['g6'])
    rhombus_rows = 0
    # GP10's four-cycle parallelogram equations, used here only as positive
    # search constraints. Final acceptance checks the original graph alone.
    for a0, b0, c0, d0 in cycles4(system['n'], set(edges)):
        for axis in (0, 1):
            expression = P[a0][axis] + P[c0][axis] - P[b0][axis] - P[d0][axis]
            poly = sp.Poly(sp.expand(expression), *syms, domain=sp.QQ).clear_denoms()[1]
            if not poly.is_zero:
                polynomials.append({tuple(e): Fraction(int(c)) for e, c in poly.terms()})
                rhombus_rows += 1
    for i, (u, w) in enumerate(pairs):
        dx = P[u][0] - P[w][0]
        dy = P[u][1] - P[w][1]
        poly = sp.Poly(sp.expand(v[extra[i]] * (dx * dx + dy * dy) - 1), *syms, domain=sp.QQ).clear_denoms()[1]
        polynomials.append({tuple(e): Fraction(int(c)) for e, c in poly.terms()})
    expanded = []
    for p in polynomials:
        expression = sum((sp.Rational(c.numerator, c.denominator) * sp.prod((x ** e for x, e in zip(syms, powers))) for powers, c in p.items()))
        expanded.append(str(sp.expand(expression)).replace('**', '^').replace(' ', ''))
    result = dict(system, variables=allnames, polynomials=polynomials, text=','.join(allnames) + '\n0\n' + ',\n'.join(expanded) + '\n', saturation_pairs=pairs, rhombus_rows=rhombus_rows)
    return result

def search(code, evidence, directory, seconds):
    start = time.monotonic()
    deadline = start + seconds
    n, edges = graph6(code)
    meta = {'method': 'framed_pinned_selected_saturation_msolve', 'cap_seconds': seconds, 'attempts': []}
    frequent = []
    if evidence:
        for pair, count in sorted(evidence.get('collision_pairs', {}).items(), key=lambda kv: -kv[1]):
            p = tuple(ast.literal_eval(pair))
            if p not in edges:
                frequent.append(p)
    if not frequent:
        frequent = [(a, b) for b in range(n) for a in range(b) if (a, b) not in edges]
    configs = []
    for size in (1, 3, 6):
        pairs = frequent[:size]
        if pairs not in configs:
            configs.append(pairs)
    degree = collections.Counter((v for e in edges for v in e))
    alternate_frames = [e for e in sorted(edges, key=lambda e: (-degree[e[0]] - degree[e[1]], e)) if e != edges[0]]
    frames = [edges[0]] + alternate_frames[:2] if seconds >= 500 else [edges[0]] * len(configs)
    cert = None
    proposal_rank = None
    generic_value, generic_meta = generic_rank(code)
    if evidence and evidence.get('best_gap', 0) > 0.0001 and evidence.get('coords'):
        points = normalize(evidence['coords'], edges[0])
        free = [v for v in range(n) if v not in edges[0]]
        rank = int(np.linalg.matrix_rank(np.asarray(rigid_system.rigidity(n, edges, points, free)), tol=1e-07))
        if rank + 1 < generic_value:
            proposal_rank = rank + 1
    meta.update(generic_rank=generic_value, numerical_rank_proposal=proposal_rank, rank_caveat='Extra rational direction pins are positive search choices, never a refutation or a proof of dimension.')
    for i, pairs in enumerate(configs):
        target = directory / f'sat-{i:02d}'
        target.mkdir(parents=True, exist_ok=True)
        t = time.monotonic()
        frame = frames[i % len(frames)]
        row = {'pairs': pairs, 'frame': list(frame)}
        if deadline - t < 1:
            break
        try:
            original_rank = rigid_system.generic_rank
            use_rank_proposal = proposal_rank is not None and i > 0
            row['used_numerical_rank_pin_proposal'] = use_rank_proposal
            if use_rank_proposal:
                rigid_system.generic_rank = lambda g: (proposal_rank, {'method': 'numerical_rank_pin_proposal', 'original_generic_rank': generic_value, 'not_a_proof': True})
            try:
                system = augment(make_system(code, frame=list(frame), variant=0), pairs)
            finally:
                rigid_system.generic_rank = original_rank
            (target / 'system.json').write_text(json.dumps({k: v for k, v in system.items() if k != 'polynomials'}, indent=2))
            available = deadline - time.monotonic()
            solvercap = max(0.01, (available - min(10, available / 4)) / (len(configs) - i))
            raw, detail = invoke(system, target, solvercap, parse=False)
            row.update(detail)
            if raw is not None:

                def convert():
                    parsed = decode_output(raw, system['variables'])
                    return certify(code, system, parsed)
                cert, checked = isolated(convert, max(0.01, min(20, deadline - time.monotonic())))
                row.update(checked)
        except Exception as exc:
            row['error'] = type(exc).__name__ + ':' + str(exc)[-400:]
        row['seconds'] = time.monotonic() - t
        meta['attempts'].append(row)
        (target / 'stats.json').write_text(json.dumps(row, indent=2))
        if cert:
            break
    meta['seconds'] = time.monotonic() - start
    meta['reason'] = 'exact_embedding' if cert else 'no_exact_certificate'
    return (cert, meta)

def coordinate_pin_search(code, evidence, directory, seconds):
    """Positive search through a flexible numerical branch, never a refuter."""
    start = time.monotonic()
    deadline = start + seconds
    n, edges = graph6(code)
    meta = {'method': 'numeric_branch_coordinate_pins', 'attempts': [], 'dimension_claim_is_proof': False}
    if not evidence or evidence.get('best_gap', 0) <= 0.0001 or (not evidence.get('coords')):
        return (None, dict(meta, reason='no_separated_numerical_seed'))
    frame = edges[0]
    p = normalize(evidence['coords'], frame)
    free = [v for v in range(n) if v not in frame]
    J = np.asarray(rigid_system.rigidity(n, edges, p, free), dtype=float)
    d = 2 * len(free)
    rank = int(np.linalg.matrix_rank(J, tol=1e-07))
    initial_rank = rank
    selected = []
    while rank < d:
        _, _, vh = np.linalg.svd(J, full_matrices=True)
        scores = np.sum(vh[rank:] ** 2, axis=0)
        for c in np.argsort(-scores):
            row = np.zeros(d)
            row[c] = 1
            aug = np.vstack((J, row))
            newrank = int(np.linalg.matrix_rank(aug, tol=1e-07))
            if newrank > rank:
                selected.append(int(c))
                J = aug
                rank = newrank
                break
        else:
            return (None, dict(meta, reason='could_not_select_transverse_coordinate_pins'))
    meta.update(numerical_free_rank=initial_rank, coordinate_columns=selected)
    if not selected:
        return (None, dict(meta, reason='numerically_isolated_no_coordinate_pin_needed'))
    frequent = []
    for pair, count in sorted(evidence.get('collision_pairs', {}).items(), key=lambda kv: -kv[1]):
        pair = tuple(ast.literal_eval(pair))
        if pair not in edges:
            frequent.append(pair)
    for attempt, bound in enumerate((16, 64)):
        target = directory / f'coordinate-{attempt:02d}'
        target.mkdir(parents=True, exist_ok=True)
        detail = {'denominator_bound': bound, 'coordinate_pins': []}
        began = time.monotonic()
        cert = None
        if deadline - began < 1:
            break
        try:
            oldrank = rigid_system.generic_rank
            rigid_system.generic_rank = lambda g: (2 * n - 3, {'method': 'unpinned_positive_system_for_coordinate_proposal'})
            try:
                system = make_system(code, frame=list(frame), variant=0)
            finally:
                rigid_system.generic_rank = oldrank
            system = augment(system, frequent[:1 if attempt == 0 else 3])
            for col in selected:
                vertex = free[col // 2]
                axis = col % 2
                name = ('x' if axis == 0 else 'y') + str(vertex)
                value = Fraction(float(p[vertex, axis])).limit_denominator(bound)
                exponent = [0] * len(system['variables'])
                exponent[system['variables'].index(name)] = 1
                poly = {tuple(exponent): Fraction(value.denominator), tuple([0] * len(exponent)): Fraction(-value.numerator)}
                system['polynomials'].append(poly)
                expression = str(value.denominator) + '*' + name + ('-' + str(value.numerator) if value.numerator >= 0 else '+' + str(-value.numerator))
                system['text'] = system['text'].rstrip() + ',\n' + expression + '\n'
                detail['coordinate_pins'].append({'variable': name, 'value': str(value)})
            system['pins'] = detail['coordinate_pins']
            system['k'] = len(selected)
            (target / 'system.json').write_text(json.dumps({k: v for k, v in system.items() if k != 'polynomials'}, indent=2))
            available = deadline - time.monotonic()
            raw, invoke_meta = invoke(system, target, max(0.01, (available - 10) / (2 - attempt)), parse=False)
            detail.update(invoke_meta)
            if raw is not None:
                cert, conversion = isolated(lambda: certify(code, system, decode_output(raw, system['variables'])), max(0.01, min(25, deadline - time.monotonic())))
                detail.update(conversion)
        except Exception as exc:
            detail['error'] = type(exc).__name__ + ':' + str(exc)[-350:]
        detail['seconds'] = time.monotonic() - began
        meta['attempts'].append(detail)
        (target / 'stats.json').write_text(json.dumps(detail, indent=2))
        if cert:
            return (cert, meta)
    return (None, dict(meta, reason='no_exact_certificate'))
