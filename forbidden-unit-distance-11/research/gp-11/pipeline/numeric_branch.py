"""Numeric evidence only until an ordinary exact certificate is checked.

Analytic-Jacobian multistart (same equations as GP10 cloud/multistart),
followed by enumeration of BOTH intersections at every two-circle step.
"""
from common import *
import numpy as np
from scipy.optimize import least_squares
from collections import Counter
from fractions import Fraction
import math, json, hashlib, subprocess
from exact import graph6, verify
from gp_field import PRELUDE
from extension import gp_output

def normalize(p, frame):
    a, b = frame
    p = np.asarray(p, dtype=float)
    v = p[b] - p[a]
    d = np.linalg.norm(v)
    return (p - p[a]) @ np.array([[v[0], -v[1]], [v[1], v[0]]]) / d

def diagnostics(p, edges):
    delta = p[np.array(edges)[:, 0]] - p[np.array(edges)[:, 1]]
    error = float(np.max(np.abs(np.einsum('ij,ij->i', delta, delta) - 1)))
    gap, a, b = min(((float(np.linalg.norm(p[a] - p[b])), a, b) for b in range(len(p)) for a in range(b)))
    return (error, gap, (a, b))

def order_for(n, edges, frame):
    adj = [set() for _ in range(n)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    remaining = set(range(n))
    removed = []
    while len(remaining) > 2:
        eligible = [v for v in remaining if v not in frame and len(adj[v] & remaining) <= 2]
        if not eligible:
            break
        v = min(eligible, key=lambda v: (len(adj[v] & remaining), v))
        remaining.remove(v)
        removed.append(v)
    if remaining == set(frame):
        done = list(frame)
        steps = []
        for v in reversed(removed):
            steps.append((v, [w for w in done if w in adj[v]]))
            done.append(v)
        return steps
    done = list(frame)
    steps = []
    while len(done) < n:
        v = max((v for v in range(n) if v not in done), key=lambda v: (len(adj[v] & set(done)), len(adj[v]), -v))
        near = [w for w in done if w in adj[v]]
        steps.append((v, near))
        done.append(v)
    return steps

def enumerate_branches(seed, edges, frame, deadline, max_nodes=8192):
    n = len(seed)
    seed = normalize(seed, frame)
    steps = order_for(n, edges, frame)
    points = np.zeros((n, 2))
    points[frame[1], 0] = 1
    nodes = 0
    out = []
    signs = []

    def rec(k):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or time.monotonic() > deadline:
            return
        if k == len(steps):
            err, gap, pair = diagnostics(points, edges)
            if err <= 1e-08:
                out.append((gap, points.copy(), list(signs)))
            return
        v, near = steps[k]
        if len(near) >= 2:
            a, b = near[:2]
            delta = points[b] - points[a]
            dd = float(delta @ delta)
            if dd < 1e-14 or dd > 4 + 1e-10:
                return
            mid = (points[a] + points[b]) / 2
            perp = np.array([-delta[1], delta[0]]) * math.sqrt(max(0, 1 / dd - 0.25))
            options = [(mid + perp, 1), (mid - perp, -1)]
        elif near:
            a = near[0]
            delta = seed[v] - seed[a]
            length = np.linalg.norm(delta)
            if length < 1e-10:
                return
            options = [(points[a] + delta / length, 0)]
        else:
            options = [(seed[v], 0)]
        for p, s in options:
            if any((abs(float((p - points[w]) @ (p - points[w])) - 1) > 1e-08 for w in near)):
                continue
            points[v] = p
            signs.append(s)
            rec(k + 1)
            signs.pop()
    rec(0)
    out.sort(key=lambda r: -r[0])
    return (out, nodes, steps)

def branch_exact(code, p, frame, signs, steps, directory, seconds, bound=64):
    """GP10 radical field machinery; exact edge/collision checks in frozen checker."""
    n, edges = graph6(code)
    p = normalize(p, frame)
    ids = {}
    ops = []
    serial = 0

    def push(expr):
        nonlocal serial
        serial += 1
        ops.append('push(' + expr + ');')
        return serial

    def ref(i):
        return 'R[' + str(i) + ']'
    ids[frame[0]] = [push('0'), push('0')]
    ids[frame[1]] = [push('1'), push('0')]
    for (v, near), sgn in zip(steps, signs):
        if len(near) >= 2:
            a, b = near[:2]
            ax, ay = map(ref, ids[a])
            bx, by = map(ref, ids[b])
            dx = push(bx + '-' + ax)
            dy = push(by + '-' + ay)
            mx = push('(' + ax + '+' + bx + ')/2')
            my = push('(' + ay + '+' + by + ')/2')
            rt = push('rootfield(1/(' + ref(dx) + '^2+' + ref(dy) + '^2)-1/4)')
            x = push(ref(mx) + '-(' + str(sgn) + ')*' + ref(dy) + '*' + ref(rt))
            y = push(ref(my) + '+(' + str(sgn) + ')*' + ref(dx) + '*' + ref(rt))
            ids[v] = [x, y]
        elif near:
            a = near[0]
            d = p[v] - p[a]
            d = d / np.linalg.norm(d)
            t = None if abs(1 + d[0]) < 1e-10 else Fraction(float(d[1] / (1 + d[0]))).limit_denominator(bound)
            c, s = (Fraction(-1), Fraction(0)) if t is None else ((1 - t * t) / (1 + t * t), 2 * t / (1 + t * t))
            ids[v] = [push(ref(ids[a][0]) + '+(' + str(c) + ')'), push(ref(ids[a][1]) + '+(' + str(s) + ')')]
        else:
            ids[v] = [push(str(Fraction(float(z)).limit_denominator(bound))) for z in p[v]]
        # Fast exact rejection of incompatible rational-angle proposals.
        for w in near:
            x, y = map(ref, ids[v])
            u, z = map(ref, ids[w])
            ops.append('if((' + x + '-' + u + ')^2+(' + y + '-' + z + ')^2!=1,error("branch:edge"));')
    directory.mkdir(parents=True, exist_ok=True)
    source = PRELUDE + '\nmain()={\n' + '\n'.join(ops) + '\nfinish(' + str([x for v in range(n) for x in ids[v]]) + ');\n};\nmain();\nquit;\n'
    f = directory / ('branch-' + str(bound) + '.gp')
    f.write_text(source)
    child = subprocess.Popen(['gp', '-fq', '-s', '64000000', str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = child.communicate(timeout=seconds)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    f.with_suffix('.stdout').write_text(stdout)
    f.with_suffix('.stderr').write_text(stderr)
    if not stdout.splitlines() or stdout.splitlines()[-1] != 'GP_FIELD_OK':
        raise ValueError(stderr[-300:])
    return verify(code, gp_output(code, stdout, n))

def search(code, seconds, directory):
    start = time.monotonic()
    deadline = start + seconds
    numeric_deadline = start + max(1, seconds * 0.7)
    n, edges = graph6(code)
    frame = edges[0]
    a, b = frame
    free = [v for v in range(n) if v not in frame]
    ed = np.array([e for e in edges if e != frame])
    B = np.zeros((len(ed), len(free)))
    cols = {v: i for i, v in enumerate(free)}
    for i, (u, v) in enumerate(ed):
        if u in cols:
            B[i, cols[u]] = 1
        if v in cols:
            B[i, cols[v]] = -1

    def unpack(z):
        p = np.zeros((n, 2))
        p[b, 0] = 1
        p[free] = z.reshape(-1, 2)
        return p

    def fun(z):
        p = unpack(z)
        d = p[ed[:, 0]] - p[ed[:, 1]]
        return np.einsum('ij,ij->i', d, d) - 1

    def jac(z):
        p = unpack(z)
        d = p[ed[:, 0]] - p[ed[:, 1]]
        j = np.empty((len(ed), len(z)))
        j[:, ::2] = 2 * d[:, 0, None] * B
        j[:, 1::2] = 2 * d[:, 1, None] * B
        return j
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(code.encode()).digest()[:8], 'big'))
    stats = {'method': 'analytic_Jacobian_multistart_plus_both_circle_branches', 'cap_seconds': seconds, 'starts': 0, 'converged': 0, 'converged_separated_1e-4': 0, 'branch_nodes': 0, 'branch_configurations': 0, 'branch_separated_1e-4': 0, 'best_gap': 0.0, 'minimum_gap': None, 'best_residual': None, 'collision_pairs': {}, 'exact_attempts': []}
    collision = Counter()
    best = None
    branch_witness = None
    attempted = 0
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'numeric-trials.jsonl').open('w', buffering=1) as stream:
        while time.monotonic() < numeric_deadline and stats['starts'] < 3000:
            z = rng.normal(size=2 * len(free)) * rng.uniform(0.6, 1.8)
            fit = least_squares(fun, z, jac=jac, method='lm' if len(ed) >= len(z) else 'trf', max_nfev=600, ftol=1e-13, xtol=1e-13, gtol=1e-13)
            p = unpack(fit.x)
            error, gap, pair = diagnostics(p, edges)
            stats['starts'] += 1
            stats['best_residual'] = error if stats['best_residual'] is None else min(error, stats['best_residual'])
            stream.write(json.dumps({'start': stats['starts'], 'edge_error': error, 'gap': gap, 'closest_pair': pair, 'nfev': fit.nfev}) + '\n')
            if error > 1e-10:
                continue
            stats['converged'] += 1
            stats['minimum_gap'] = gap if stats['minimum_gap'] is None else min(gap, stats['minimum_gap'])
            if gap > 0.0001:
                stats['converged_separated_1e-4'] += 1
            else:
                collision[str(pair)] += 1
            if gap > stats['best_gap']:
                stats['best_gap'] = gap
                best = p.copy()
            if attempted < 60 or gap > 0.0001:
                variants, nodes, steps = enumerate_branches(p, edges, frame, numeric_deadline)
                attempted += 1
                stats['branch_nodes'] += nodes
                stats['branch_configurations'] += len(variants)
                for bg, q, signs in variants:
                    stats['branch_separated_1e-4'] += int(bg > 0.0001)
                    if bg > stats['best_gap']:
                        stats['best_gap'] = bg
                        best = q.copy()
                    if bg > 0.001 and (branch_witness is None or bg > branch_witness[0]):
                        branch_witness = (bg, q, signs, steps)
            if stats['converged_separated_1e-4'] >= 10 and stats['starts'] >= 30:
                break
    stats['numeric_seconds'] = time.monotonic() - start
    stats['collision_pairs'] = dict(collision)
    stats['coords'] = None if best is None else best.tolist()
    stats['frame'] = list(frame)
    stats['all_converged_within_1e-4'] = stats['converged'] > 0 and stats['converged_separated_1e-4'] == 0
    cert = None
    if branch_witness is not None:
        bg, p, signs, steps = branch_witness
        stats['branch_witness'] = {'gap': bg, 'points': p.tolist(), 'signs': signs, 'steps': steps}
        for bound in (16, 64, 256):
            if time.monotonic() >= deadline:
                break
            t = time.monotonic()
            row = {'denominator_bound': bound}
            try:
                cert = branch_exact(code, p, frame, signs, steps, directory, max(0.01, min(10, deadline - t)), bound)
                row['result'] = 'exact'
            except (Exception, Deadline) as exc:
                row['result'] = type(exc).__name__ + ':' + str(exc)[-300:]
            row['seconds'] = time.monotonic() - t
            stats['exact_attempts'].append(row)
            if cert:
                break
    stats['seconds'] = time.monotonic() - start
    (directory / 'numeric.json').write_text(json.dumps(stats, indent=2))
    return (cert, stats)
