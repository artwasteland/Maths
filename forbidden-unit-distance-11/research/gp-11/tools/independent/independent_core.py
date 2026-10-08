"""Shared independent infrastructure. No checker, kernel, or producer imports.

Graph6 and rational polynomial arithmetic below are local implementations.
Only isomorphism keys use pynauty; this is disclosed in REPORT.md.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from fractions import Fraction
from pathlib import Path

# Sealed coordinates include rational numerators with >7,800 decimal digits.
# Input lines retain the 8 MiB resource bound; Python's 4,300-digit default
# would reject legitimate exact data before doing any mathematics.
sys.set_int_max_str_digits(0)


class Failure(ValueError):
    def __init__(self, code, reason, **details):
        super().__init__(reason)
        self.code, self.reason, self.details = code, reason, details


def require(ok, code, reason, **details):
    if not ok:
        raise Failure(code, reason, **details)


def keys(obj, required, optional=()):
    require(isinstance(obj, dict) and set(required) <= set(obj)
            and set(obj) <= set(required) | set(optional), "schema",
            f"expected keys {sorted(required)}; optional {sorted(optional)}")


def integer(v):
    return type(v) is int


def rational(v, tree=False):
    require((tree and integer(v)) or (isinstance(v, str)
            and re.fullmatch(r"[+-]?[0-9]+(?:/[0-9]+)?", v)),
            "rational", "expected an exact rational string")
    try:
        return Fraction(v)
    except (ValueError, ZeroDivisionError) as exc:
        raise Failure("rational", f"invalid rational: {exc}") from exc


def loads(raw):
    def object_pairs(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, "json_duplicate_key", f"duplicate JSON key {k}")
            out[k] = v
        return out

    def bad_constant(v):
        raise Failure("json_constant", f"non-finite JSON value {v}")

    try:
        return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, Failure):
            raise
        raise Failure("json", str(exc)) from exc


def record(raw):
    r = loads(raw)
    keys(r, {"g6", "verdict", "cert"})
    decode_g6(r["g6"])
    require(r["verdict"] in ("embedded", "refuted", "unknown"), "verdict", "unknown verdict")
    require(isinstance(r["cert"], dict), "schema", "certificate must be an object")
    return r


def lines(path, limit=None):
    """Bound individual raw lines to the specification's 8 MiB ceiling."""
    with open(path, "rb") as f:
        i = 0
        while limit is None or i < limit:
            raw = f.readline(8 * 1024 * 1024 + 1)
            if not raw:
                break
            i += 1
            require(len(raw) <= 8 * 1024 * 1024, "line_size", f"line {i} exceeds 8 MiB")
            require(raw.endswith(b"\n"), "newline", f"line {i} lacks trailing newline")
            require(raw.strip(), "empty_line", f"line {i} is empty")
            yield i, raw


def decode_g6(s):
    require(isinstance(s, str) and s and all(63 <= ord(c) <= 126 for c in s),
            "graph6", "invalid graph6 characters or header")
    nums = [ord(c) - 63 for c in s]
    if nums[0] != 63:
        n, offset = nums[0], 1
    else:
        require(len(nums) >= 4 and nums[1] != 63, "graph6", "unsupported or truncated order encoding")
        n, offset = (nums[1] << 12) | (nums[2] << 6) | nums[3], 4
        require(n >= 63, "graph6", "nonminimal order encoding")
    needed = n * (n - 1) // 2
    require(len(nums) == offset + (needed + 5) // 6, "graph6", "wrong graph6 length")
    if needed % 6:
        require(nums[-1] & ((1 << (6 - needed % 6)) - 1) == 0, "graph6", "nonzero padding bits")
    edges, k = set(), 0
    for v in range(1, n):
        for u in range(v):
            if nums[offset + k // 6] & (1 << (5 - k % 6)):
                edges.add((u, v))
            k += 1
    return n, edges


def encode_g6(n, edges):
    require(n < 63, "graph6", "encoder is intentionally restricted to these small graphs")
    edges = {tuple(sorted(e)) for e in edges}
    bits = [int((u, v) in edges) for v in range(1, n) for u in range(v)]
    bits.extend([0] * (-len(bits) % 6))
    return chr(n + 63) + "".join(chr(63 + sum(bits[k + i] << (5 - i) for i in range(6)))
                                for k in range(0, len(bits), 6))


def adjacency(n, edges):
    adj = [set() for _ in range(n)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def iso_key(n, edges):
    import pynauty
    adj = adjacency(n, edges)
    return n.to_bytes(2, "big") + pynauty.certificate(
        pynauty.Graph(n, adjacency_dict={i: sorted(a) for i, a in enumerate(adj)}))


def blocks(n, edges):
    """Tarjan edge-stack blocks, including bridges; isolated vertices separate."""
    adj = adjacency(n, edges)
    seen, low, stack, out = {}, {}, [], []
    clock = 0

    def visit(v, parent):
        nonlocal clock
        clock += 1
        seen[v] = low[v] = clock
        for w in sorted(adj[v]):
            e = tuple(sorted((v, w)))
            if w not in seen:
                stack.append(e)
                visit(w, v)
                low[v] = min(low[v], low[w])
                if low[w] >= seen[v]:
                    block = set()
                    while True:
                        z = stack.pop()
                        block.add(z)
                        if z == e:
                            break
                    out.append(block)
            elif w != parent and seen[w] < seen[v]:
                low[v] = min(low[v], seen[w])
                stack.append(e)

    for v in range(n):
        if v not in seen:
            visit(v, -1)
    return out, [v for v in range(n) if not adj[v]]


def biconnected(n, edges):
    bs, isolated = blocks(n, edges)
    return n >= 3 and not isolated and len(bs) == 1 and len(set(sum((list(e) for e in edges), []))) == n


def maps_into(small, big, mapping):
    ns, es = small
    nb, eb = big
    return (isinstance(mapping, list) and len(mapping) == ns
            and all(integer(v) and 0 <= v < nb for v in mapping)
            and len(set(mapping)) == ns
            and all(tuple(sorted((mapping[u], mapping[v]))) in eb for u, v in es))


def bounded_map(fn, iterable, jobs=1, pending_per_job=2):
    """Unordered, bounded process map: never enqueue the whole JSONL."""
    if jobs == 1:
        for item in iterable:
            yield fn(item)
        return
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        it, pending, exhausted = iter(iterable), set(), False
        while pending or not exhausted:
            while not exhausted and len(pending) < pending_per_job * jobs:
                try:
                    pending.add(pool.submit(fn, next(it)))
                except StopIteration:
                    exhausted = True
            if pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for fut in done:
                    yield fut.result()


def shard(text):
    try:
        i, n = map(int, text.split("/"))
        require(0 <= i < n, "shard", "shard must satisfy 0 <= i < n")
        return i, n
    except (ValueError, AttributeError) as exc:
        raise Failure("shard", "use zero-based i/n") from exc


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def source_hashes(*names):
    root = Path(__file__).resolve().parent
    return {name: digest(root / name) for name in names}


def guard_outputs(inputs, outputs):
    evidence = {Path(p).resolve() for p in inputs if p is not None}
    require(not any(Path(p).resolve() in evidence for p in outputs),
            "output_collision", "an output would overwrite supplied input evidence")


def trim(a):
    a = list(a)
    while a and not a[-1]:
        a.pop()
    return a


def padd(a, b):
    out = [Fraction(0)] * max(len(a), len(b))
    for i, x in enumerate(a):
        out[i] += x
    for i, x in enumerate(b):
        out[i] += x
    return trim(out)


def psub(a, b):
    return padd(a, [-v for v in b])


def pmul(a, b):
    out = [Fraction(0)] * max(0, len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    out[i + j] += x * y
    return trim(out)


def premainder(a, modulus):
    out = trim(a)
    while len(out) >= len(modulus):
        shift = len(out) - len(modulus)
        coef = out[-1] / modulus[-1]
        for i, x in enumerate(modulus):
            if x:
                out[shift + i] -= coef * x
        out = trim(out)
    return out


def peval(poly, value):
    result = Fraction(0)
    for c in reversed(poly):
        result = result * value + c
    return result


def interval_mul(a, b):
    products = [x * y for x in a for y in b]
    return min(products), max(products)


def interval_eval(poly, interval):
    acc = (Fraction(0), Fraction(0))
    for c in reversed(poly):
        lo, hi = interval_mul(acc, interval)
        acc = lo + c, hi + c
    return acc


def check_exact(g6, cert, max_bisections=2048):
    """Exact Q[t]/(minpoly) edge equations and common rational interval separation.

    This does not assume irreducibility or a uniquely isolated root, as FORMAT
    expressly allows reducible polynomials. A sign change selects a common root.
    """
    n, edges = decode_g6(g6)
    keys(cert, {"type", "field", "coords"})
    require(cert["type"] == "exact", "certificate_type", "expected an exact embedding certificate")
    keys(cert["field"], {"minpoly", "interval"})
    raw_m = cert["field"]["minpoly"]
    require(isinstance(raw_m, list) and len(raw_m) >= 2 and all(integer(x) for x in raw_m)
            and raw_m[-1] != 0, "minpoly", "invalid integer polynomial")
    modulus = raw_m
    d = len(modulus) - 1
    iv = cert["field"]["interval"]
    require(isinstance(iv, list) and len(iv) == 2, "interval", "expected two interval endpoints")
    lo, hi = map(rational, iv)
    def sign_value(poly, q):
        # Homogenized integer Horner evaluation: only the sign is needed.
        acc, denominator_power = 0, 1
        for c in reversed(poly):
            acc = acc * q.numerator + c * denominator_power
            denominator_power *= q.denominator
        return acc

    flo, fhi = sign_value(modulus, lo), sign_value(modulus, hi)
    require(lo < hi and flo * fhi < 0, "interval", "interval has no strict sign change")
    raw_coords = cert["coords"]
    require(isinstance(raw_coords, list) and len(raw_coords) == n,
            "coordinate_count", f"expected {n} coordinate pairs")
    coords, cache = [], {}
    for pair in raw_coords:
        require(isinstance(pair, list) and len(pair) == 2, "coordinate_schema", "expected [x,y]")
        require(all(isinstance(v, list) and len(v) == d for v in pair),
                "coordinate_degree", "coordinate arrays must have degree(minpoly) entries")
        parsed = []
        for poly in pair:
            values = []
            for value in poly:
                if value not in cache:
                    cache[value] = rational(value)
                values.append(cache[value])
            parsed.append(values)
        coords.append(parsed)
    # One common denominator makes edge reduction fraction-free. This matters
    # for coordinates containing thousands of digits: repeated Fraction gcds
    # in every convolution otherwise dominate the verification.
    denominators = {q.denominator for pair in coords for poly in pair for q in poly}
    common_den = math.lcm(*denominators)
    icoords = [[[q.numerator * (common_den // q.denominator) for q in poly]
                for poly in pair] for pair in coords]

    def isquare(poly):
        result = [0] * (2 * len(poly) - 1)
        for i, x in enumerate(poly):
            if x:
                result[2 * i] += x * x
                for j in range(i + 1, len(poly)):
                    if poly[j]:
                        result[i + j] += 2 * x * poly[j]
        return result

    def divisible(poly):
        # Pseudo-division scales the remainder by powers of the nonzero leading
        # coefficient, preserving precisely whether the Q-remainder is zero.
        rem, lead = trim(poly), modulus[-1]
        while len(rem) >= len(modulus):
            shift, top = len(rem) - len(modulus), rem[-1]
            if lead != 1:
                rem = [x * lead for x in rem]
            for k, value in enumerate(modulus):
                rem[shift + k] -= top * value
            rem = trim(rem)
        return not rem

    def bounds(poly, left, right):
        # Integer interval Horner, with a common positive denominator. No
        # rounding and no gcd inside the Horner loop.
        q = math.lcm(left.denominator, right.denominator)
        l, h = left.numerator * (q // left.denominator), right.numerator * (q // right.denominator)
        low, high, den = 0, 0, 1
        for coefficient in reversed(poly):
            products = (low * l, low * h, high * l, high * h)
            den *= q
            low, high = min(products) + coefficient * den, max(products) + coefficient * den
        return low, high, den * common_den

    deltas = {}
    for u in range(n):
        for v in range(u + 1, n):
            dx, dy = (trim([x - y for x, y in zip(icoords[u][j], icoords[v][j])]) for j in (0, 1))
            if (u, v) in edges:
                squares = [isquare(poly) if poly else [] for poly in (dx, dy)]
                distance = [sum(poly[k] if k < len(poly) else 0 for poly in squares)
                            for k in range(max(map(len, squares), default=0))]
                if not distance:
                    distance = [0]
                distance[0] -= common_den * common_den
                require(divisible(distance),
                        "edge_not_unit", f"edge {u},{v} is off unit length exactly", edge=[u, v])
            deltas[u, v] = (dx, dy)
    unresolved = list(deltas)
    subdivisions, lower = 0, None
    while unresolved:
        next_unresolved = []
        for pair in unresolved:
            dx, dy = deltas[pair]
            enclosures = [bounds(poly, lo, hi) for poly in (dx, dy)]
            if all(l <= 0 <= h for l, h, den in enclosures):
                if lo == hi:
                    raise Failure("collision", f"vertices {pair} coincide", pair=list(pair))
                else:
                    next_unresolved.append(pair)
                    continue
            for l, h, den in enclosures:
                if not l <= 0 <= h:
                    numerator = min(abs(l), abs(h))
                    k = numerator.bit_length() - den.bit_length()
                    below_power = numerator < den << k if k >= 0 else numerator << (-k) < den
                    if below_power:
                        k -= 1
                    lower = k if lower is None else min(lower, k)
        unresolved = next_unresolved
        if not unresolved:
            break
        require(subdivisions < max_bisections, "separation_budget",
                f"failed to separate pair {unresolved[0]} in {max_bisections} exact subdivisions")
        mid = (lo + hi) / 2
        fm = sign_value(modulus, mid)
        if fm == 0:
            lo = hi = mid
        elif (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
        subdivisions += 1
    return {"degree": d, "subdivisions": subdivisions,
            "gap_component_lower_bound_power_of_two": lower}
