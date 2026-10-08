"""Local E-exact checks. No numeric tolerance participates in acceptance."""
from __future__ import annotations
import re
from flint import fmpq as Q, fmpq_poly as Poly

class CertificateError(ValueError):
    pass

def rational(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+/[1-9]\d*", value):
        raise CertificateError("format:rational")
    return Q(value)

def textq(q):
    q = Q(q)
    return f"{q.numerator}/{q.denominator}"

def graph6(code):
    """Decode graph6 without relabelling, including the two extended headers."""
    if not isinstance(code, str) or not code or code.startswith('>>'):
        raise ValueError('graph6:header')
    data = [ord(c) - 63 for c in code]
    if any(c < 0 or c > 63 for c in data):
        raise ValueError('graph6:character')
    if data[0] != 63:
        n, start = data[0], 1
    elif len(data) >= 4 and data[1] != 63:
        n, start = (data[1] << 12) + (data[2] << 6) + data[3], 4
    elif len(data) >= 8:
        n, start = 0, 8
        for c in data[2:8]:
            n = (n << 6) + c
    else:
        raise ValueError('graph6:header')
    if n > 4096:
        raise ValueError('graph6:vertex_cap')
    bits = n * (n - 1) // 2
    if len(data) != start + (bits + 5) // 6:
        raise ValueError('graph6:length')
    if bits % 6 and data[-1] & ((1 << (6 - bits % 6)) - 1):
        raise ValueError('graph6:padding')
    edges, k = [], 0
    for v in range(n):
        for u in range(v):
            if data[start + k // 6] & (1 << (5 - k % 6)):
                edges.append((u, v))
            k += 1
    return n, edges

def adjacency(n, edges):
    a = [0] * n
    for u, v in edges:
        a[u] |= 1 << v
        a[v] |= 1 << u
    return a

def interval_eval(p, lo, hi):
    a = b = Q(0)
    for c in reversed(list(p)):
        products = (a * lo, a * hi, b * lo, b * hi)
        a, b = min(products) + c, max(products) + c
    return a, b

def refine(p, lo, hi):
    mid = (lo + hi) / 2
    fm = p(mid)
    if fm == 0:
        # A rational root can be a midpoint. Keep strict sign change by
        # approaching it from both sides, instead of making it an endpoint.
        left, right = (lo + mid) / 2, (mid + hi) / 2
        for _ in range(256):
            if p(left) * p(right) < 0:
                return left, right
            left, right = (left + mid) / 2, (right + mid) / 2
        raise CertificateError('interval:refinement')
    if p(lo) * fm < 0:
        return lo, mid
    return mid, hi

def verify(code, cert, max_refinements=192):
    """Return a possibly tightened copy of a valid certificate, or raise."""
    n, edges = graph6(code)
    if not isinstance(cert, dict) or cert.get('type') != 'exact':
        raise CertificateError('format:type')
    field = cert.get('field', {})
    coefficients = field.get('minpoly')
    if (not isinstance(coefficients, list) or len(coefficients) < 2
            or len(coefficients) > 257 or not coefficients[-1]
            or any(type(c) is not int for c in coefficients)):
        raise CertificateError('format:minpoly')
    p = Poly(coefficients)
    d = len(coefficients) - 1
    interval = field.get('interval', [])
    if not isinstance(interval, list) or len(interval) != 2:
        raise CertificateError('format:interval')
    lo, hi = map(rational, interval)
    if lo >= hi or p(lo) * p(hi) >= 0:
        raise CertificateError('sign_change')
    raw = cert.get('coords')
    if not isinstance(raw, list) or len(raw) != n:
        raise CertificateError('format:coords')
    points = []
    for point in raw:
        if not isinstance(point, list) or len(point) != 2:
            raise CertificateError('format:point')
        if any(not isinstance(c, list) or len(c) != d for c in point):
            raise CertificateError('format:coordinate_degree')
        points.append(tuple(Poly(list(map(rational, c))) for c in point))
    distances = {}
    for v in range(n):
        for u in range(v):
            dx, dy = points[u][0] - points[v][0], points[u][1] - points[v][1]
            distances[u, v] = (dx * dx + dy * dy) % p
    for u, v in edges:
        if distances[u, v] != Poly([1]):
            raise CertificateError(f'edge:{u},{v}')
    for pair, dist in distances.items():
        if not dist:
            raise CertificateError(f'distinctness:{pair[0]},{pair[1]}:zero')
    pending = list(distances.items())
    for _ in range(max_refinements + 1):
        pending = [(pair, dist) for pair, dist in pending
                   if interval_eval(dist, lo, hi)[0] <= 0]
        if not pending:
            return {'type': 'exact', 'field': {'minpoly': coefficients[:],
                    'interval': [textq(lo), textq(hi)]}, 'coords': raw}
        lo, hi = refine(p, lo, hi)
    pair = pending[0][0]
    raise CertificateError(f'distinctness:{pair[0]},{pair[1]}:interval')

def rational_certificate(points):
    return {'type': 'exact', 'field': {'minpoly': [0, 1],
            'interval': ['-1/1', '1/1']},
            'coords': [[[textq(x)], [textq(y)]] for x, y in points]}
