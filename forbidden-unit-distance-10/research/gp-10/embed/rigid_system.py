"""Edge framing, exact rigidity probes, and provisional rational direction pins."""
import os
os.environ['SYMPY_GROUND_TYPES'] = 'python'
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
from fractions import Fraction
import hashlib
import random
from flint import fmpq_mat
from exact import graph6


def seed_for(code): return int.from_bytes(hashlib.sha256(code.encode()).digest(), 'big')


def rigidity(n, edges, points, free=None):
    free = list(range(n)) if free is None else free
    columns = {v: i for i, v in enumerate(free)}
    rows = []
    for u, v in edges:
        row = [0] * (2 * len(free))
        for j in (0, 1):
            delta = points[u][j] - points[v][j]
            if u in columns: row[2 * columns[u] + j] = delta
            if v in columns: row[2 * columns[v] + j] = -delta
        rows.append(row)
    return rows


def laman_rank(n, edges):
    """Greedy rank in the (2,3)-sparsity matroid, all subsets checked, n <= 10."""
    subsets = [s for s in range(1 << n) if s.bit_count() >= 2]
    counts = {s: 0 for s in subsets}
    chosen = []
    for u, v in edges:
        mask = (1 << u) | (1 << v)
        supersets = [s for s in subsets if s & mask == mask]
        if all(counts[s] + 1 <= 2 * s.bit_count() - 3 for s in supersets):
            chosen.append([u, v])
            for s in supersets: counts[s] += 1
    return len(chosen)


def generic_rank(code):
    n, edges = graph6(code)
    if n < 2 or n > 10 or not edges: raise ValueError('rigidity:unsupported_graph')
    rng = random.Random(seed_for(code))
    ranks = []
    for _ in range(3):
        points = [(rng.randrange(-1000, 1001), rng.randrange(-1000, 1001)) for _ in range(n)]
        ranks.append(fmpq_mat(rigidity(n, edges, points)).rank())
    upper = min(len(edges), 2 * n - 3)
    combinatorial = upper if max(ranks) == upper else laman_rank(n, edges)
    if max(ranks) != combinatorial: raise ValueError('rigidity:probe_did_not_reach_generic_rank')
    return combinatorial, {'integer_placement_exact_ranks': ranks,
                           'generic_upper_bound': combinatorial,
                           'upper_bound_method': 'edge_and_rigid_motion' if combinatorial == upper else 'Laman_matroid'}


def choose_pins(code, k, rank, frame=None, variant=0):
    if not k: return [], {'numeric_required': False}
    import numpy as np
    from numeric import fit
    n, edges = graph6(code)
    selected = tuple(frame) if frame is not None else edges[0]
    if selected not in edges: raise ValueError('pinning:frame_not_edge')
    edges = [selected] + [edge for edge in edges if edge != selected]
    a, b = selected; free = [v for v in range(n) if v not in (a, b)]
    points = meta = None
    for attempt in range(12):
        points, meta = fit(n, edges, seed_for(code) + variant * 15485863 + attempt * 104729, restarts=1)
        if meta['residual'] <= 1e-9 and meta['minimum_distance'] >= 1e-5: break
    meta['round2_restarts'] = attempt + 1
    meta['numeric_required'] = True
    if meta['residual'] > 1e-9 or meta['minimum_distance'] < 1e-5:
        raise ValueError('pinning:no_distinct_numeric_embedding:' + str(meta))
    matrix = np.asarray(rigidity(n, edges, points, free), dtype=float)
    actual_rank = int(np.linalg.matrix_rank(matrix, tol=1e-7))
    if actual_rank != rank - 1:
        raise ValueError('pinning:singular_numeric_configuration')
    pins = []
    columns = {v: i for i, v in enumerate(free)}
    candidates = edges[1:]
    if variant: random.Random(seed_for(code) + variant * 32452843).shuffle(candidates)
    for u, v in candidates:
        dx, dy = points[v] - points[u]
        length = float(np.hypot(dx, dy)); dx, dy = dx / length, dy / length
        t = None if abs(1 + dx) < 1e-10 else Fraction(float(dy / (1 + dx))).limit_denominator((64, 32, 128)[variant % 3])
        c, s = (Fraction(-1), Fraction(0)) if t is None else ((1-t*t)/(1+t*t), 2*t/(1+t*t))
        row = np.zeros(2 * len(free))
        for vertex, sign in ((v, 1), (u, -1)):
            if vertex in columns:
                row[2 * columns[vertex]] = -sign * float(s)
                row[2 * columns[vertex] + 1] = sign * float(c)
        augmented = np.vstack((matrix, row))
        new_rank = int(np.linalg.matrix_rank(augmented, tol=1e-7))
        if new_rank > actual_rank:
            pins.append({'edge': [u, v], 'cos': str(c), 'sin': str(s),
                         't': None if t is None else str(t)})
            matrix, actual_rank = augmented, new_rank
        if len(pins) == k: break
    if len(pins) != k or actual_rank != 2 * len(free):
        raise ValueError('pinning:directions_do_not_complete_rank')
    meta.update(augmented_numeric_rank=actual_rank, points=points.tolist(),
                persistence_proved=False,
                caveat='Direction pins are proposals near a numerical regular point. No certified persistence radius.')
    return pins, meta


def make_system(code, pins_override=None, frame=None, variant=0):
    import sympy as sp
    n, edges = graph6(code)
    rank, rank_meta = generic_rank(code)
    k = 2 * n - 3 - rank
    a, b = tuple(frame) if frame is not None else edges[0]
    if (a, b) not in edges: raise ValueError('system:frame_not_edge')
    free = [v for v in range(n) if v not in (a, b)]
    variables = [axis + str(v) for v in free for axis in ('x', 'y')]
    symbols = sp.symbols(','.join(variables))
    values = dict(zip(variables, symbols))
    points = [(sp.Integer(0), sp.Integer(0)) for _ in range(n)]
    points[b] = (sp.Integer(1), sp.Integer(0))
    for v in free: points[v] = (values[f'x{v}'], values[f'y{v}'])
    if pins_override is None:
        pins, numeric_meta = choose_pins(code, k, rank, frame=[a, b], variant=variant)
    else:
        pins, numeric_meta = pins_override, {'test_override': True}
        if len(pins) != k: raise ValueError('pinning:override_count')
    expressions = []
    for u, v in edges:
        x = points[u][0] - points[v][0]; y = points[u][1] - points[v][1]
        eq = sp.expand(x*x + y*y - 1)
        if eq: expressions.append(eq)
    for pin in pins:
        u, v = pin['edge']; c, s = sp.Rational(pin['cos']), sp.Rational(pin['sin'])
        if c*c + s*s != 1: raise ValueError('pinning:not_a_rational_unit_direction')
        # Two linear equations replace the edge's existing unit equation.
        # Their net addition is one constraint on its direction.
        expressions.append(sp.expand(points[v][0] - points[u][0] - c))
        expressions.append(sp.expand(points[v][1] - points[u][1] - s))
    polynomials = []
    expanded = []
    for expression in expressions:
        poly = sp.Poly(expression, *symbols, domain=sp.QQ).clear_denoms()[1]
        expanded.append(str(poly.as_expr()).replace('**', '^').replace(' ', ''))
        polynomials.append({tuple(powers): Fraction(int(c)) for powers, c in poly.terms()})
    text = ','.join(variables) + '\n0\n' + ',\n'.join(expanded) + '\n'
    return {'g6': code, 'n': n, 'edges': len(edges), 'frame': [a, b], 'rank': rank, 'k': k,
            'rank_evidence': rank_meta, 'pins': pins, 'numeric': numeric_meta, 'variant': variant,
            'pin_equations': 'oriented_unit_vector_two_linear_equations',
            'variables': variables, 'separator_policy': 'msolve c2, graph-hash seeded srand',
            'polynomials': polynomials, 'text': text}


def public_system(system):
    return {key: value for key, value in system.items() if key not in ('polynomials', 'text')}
