#!/usr/bin/env python3
"""Independent certificate checker for the u(22) programme.

Certificate witness schema
==========================

All polynomial coefficient arrays are in ascending order.  Exact rational
numbers are JSON integers or strings such as ``"-7/12"``.  A real field is
represented by::

    {"minpoly": [c0, c1, ..., cd], "interval": [left, right]}

It denotes the unique real root alpha of the irreducible polynomial in the
open rational interval.  A field element is an array ``[q0, ..., q_(d-1)]``
representing sum(q_i alpha^i).  A complex field element is either a real
field element, a rational scalar, or ``{"re": element, "im": element}``.

An embedded witness has keys ``field`` and ``coordinates``.  Coordinates are
``[x,y]`` pairs of real field elements.

A refuted witness has keys ``field`` and ``tree``.  Every tree node contains
``edges``, ``A``, ``move`` and ``children``.  A is a matrix of complex field
elements.  The move forms are::

    {"kind":"L1a", "pair":[u,v]}
    {"kind":"L1b", "edges":[[u,v],[x,y]], "omega": complex}
    {"kind":"L1c", "edges":[[u,v],[x,y],[p,q]], "coefficients":[a,b,c]}
    {"kind":"L2",  "edges":[[u,v],[x,y]], "omega": complex}
    {"kind":"L3",  "edges":[[u,v],[x,y],[p,q]],
                       "coefficients":[a,b,c], "d": element}

L1 nodes have no children, L2 has one child, and L3 has two ordered children.
The first L3 child gets the +i*d equation and the second gets the -i*d one.

Lemma 4, in our own words
-------------------------

Suppose three unit complex displacements x, y, z obey ax+by+cz=0.
The three complex vectors ax, by and cz form a possibly degenerate triangle.
Writing q=|a|^2+|b|^2-|c|^2 and
d^2=4|a|^2|b|^2-q^2, the law of cosines leaves exactly the two orientations
of that triangle.  Consequently either
    (q+i*d)*a*x + 2|a|^2*b*y = 0
or the same equation with -i*d holds.  These two equations cover all cases.
At every L3 node this checker independently verifies ax+by+cz is in the row
space of A, verifies d^2 exactly, checks d is real at the selected root, and
checks that the two child row spaces are precisely A plus the two equations.

No floating point arithmetic is used for a trusted decision.  Polynomial
reduction, field arithmetic, row reduction, and root isolation are performed
below with fractions.  SymPy is used only to test irreducibility over Q.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Sequence


class CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise CheckError(message)


def exact_keys(obj: Any, required: set[str], optional: set[str] = set(), where: str = "object") -> None:
    if not isinstance(obj, dict):
        fail(f"{where}: expected object")
    keys = set(obj)
    missing = required - keys
    extra = keys - required - optional
    if missing or extra:
        fail(f"{where}: missing keys {sorted(missing)}, extra keys {sorted(extra)}")


def as_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        fail(f"{where}: expected integer")
    return value


def as_fraction(value: Any, where: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        fail(f"{where}: expected an integer or rational string")
    try:
        q = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        fail(f"{where}: invalid rational: {exc}")
    if isinstance(value, str) and value != str(q):
        fail(f"{where}: rational string is not canonical, expected {q}")
    return q


def trim(poly: Sequence[Fraction]) -> tuple[Fraction, ...]:
    p = list(poly)
    while p and p[-1] == 0:
        p.pop()
    return tuple(p)


def poly_divmod(a: Sequence[Fraction], b: Sequence[Fraction]) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    aa = list(trim(a))
    bb = trim(b)
    if not bb:
        raise ZeroDivisionError
    q = [Fraction(0)] * max(0, len(aa) - len(bb) + 1)
    while len(aa) >= len(bb) and aa:
        c = aa[-1] / bb[-1]
        k = len(aa) - len(bb)
        q[k] = c
        for i, x in enumerate(bb):
            aa[k + i] -= c * x
        aa = list(trim(aa))
    return trim(q), trim(aa)


def poly_eval(p: Sequence[Fraction], x: Fraction) -> Fraction:
    ans = Fraction(0)
    for c in reversed(p):
        ans = ans * x + c
    return ans


def sturm_sequence(p: Sequence[Fraction]) -> list[tuple[Fraction, ...]]:
    p0 = trim(p)
    if len(p0) < 2:
        fail("minimal polynomial must have positive degree")
    p1 = trim([i * p0[i] for i in range(1, len(p0))])
    out = [p0, p1]
    while out[-1]:
        _, r = poly_divmod(out[-2], out[-1])
        if not r:
            break
        out.append(tuple(-x for x in r))
    return out


def variations_at(sturm: Sequence[Sequence[Fraction]], x: Fraction) -> int:
    signs: list[int] = []
    for p in sturm:
        y = poly_eval(p, x)
        if y:
            signs.append(1 if y > 0 else -1)
    return sum(a != b for a, b in zip(signs, signs[1:]))


def root_count(sturm: Sequence[Sequence[Fraction]], left: Fraction, right: Fraction) -> int:
    if any(poly_eval(p, left) == 0 or poly_eval(p, right) == 0 for p in sturm[:1]):
        fail("isolating interval endpoint is a root")
    return variations_at(sturm, left) - variations_at(sturm, right)


def interval_mul(x: tuple[Fraction, Fraction], y: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    products = (x[0] * y[0], x[0] * y[1], x[1] * y[0], x[1] * y[1])
    return min(products), max(products)


def interval_poly(p: Sequence[Fraction], interval: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    ans = (Fraction(0), Fraction(0))
    for c in reversed(p):
        ans = interval_mul(ans, interval)
        ans = (ans[0] + c, ans[1] + c)
    return ans


@dataclass(frozen=True)
class Elem:
    field: "RealField"
    coeffs: tuple[Fraction, ...]

    def __add__(self, other: Any) -> "Elem":
        b = self.field.coerce(other)
        return self.field.make([self[i] + b[i] for i in range(self.field.degree)])

    __radd__ = __add__

    def __neg__(self) -> "Elem":
        return self.field.make([-x for x in self.coeffs])

    def __sub__(self, other: Any) -> "Elem":
        return self + (-self.field.coerce(other))

    def __rsub__(self, other: Any) -> "Elem":
        return self.field.coerce(other) - self

    def __mul__(self, other: Any) -> "Elem":
        b = self.field.coerce(other)
        raw = [Fraction(0)] * (2 * self.field.degree - 1)
        for i, x in enumerate(self.coeffs):
            for j, y in enumerate(b.coeffs):
                raw[i + j] += x * y
        return self.field.make(raw)

    __rmul__ = __mul__

    def inverse(self) -> "Elem":
        if not self:
            raise ZeroDivisionError
        # Extended Euclid in Q[x], reduced modulo the minimal polynomial.
        r0, r1 = self.field.minpoly, trim(self.coeffs)
        s0, s1 = (Fraction(0),), (Fraction(1),)
        while r1:
            q, r2 = poly_divmod(r0, r1)
            prod = [Fraction(0)] * max(1, len(q) + len(s1) - 1)
            for i, x in enumerate(q):
                for j, y in enumerate(s1):
                    prod[i + j] += x * y
            size = max(len(s0), len(prod))
            s2 = [Fraction(0)] * size
            for i in range(size):
                s2[i] = (s0[i] if i < len(s0) else 0) - (prod[i] if i < len(prod) else 0)
            r0, r1, s0, s1 = r1, r2, trim(s1), trim(s2)
        if len(r0) != 1:
            raise ZeroDivisionError
        return self.field.make([x / r0[0] for x in s0])

    def __truediv__(self, other: Any) -> "Elem":
        return self * self.field.coerce(other).inverse()

    def __getitem__(self, i: int) -> Fraction:
        return self.coeffs[i] if i < len(self.coeffs) else Fraction(0)

    def __bool__(self) -> bool:
        return any(self.coeffs)


class RealField:
    def __init__(self, spec: Any, where: str):
        exact_keys(spec, {"minpoly", "interval"}, where=where)
        raw = spec["minpoly"]
        if not isinstance(raw, list) or len(raw) < 2:
            fail(f"{where}.minpoly: expected coefficient array of positive degree")
        p = trim([as_fraction(x, f"{where}.minpoly[{i}]") for i, x in enumerate(raw)])
        if len(p) != len(raw):
            fail(f"{where}.minpoly: leading coefficient must be nonzero")
        lead = p[-1]
        self.minpoly = tuple(x / lead for x in p)
        self.degree = len(p) - 1
        interval = spec["interval"]
        if not isinstance(interval, list) or len(interval) != 2:
            fail(f"{where}.interval: expected [left,right]")
        self.left = as_fraction(interval[0], f"{where}.interval[0]")
        self.right = as_fraction(interval[1], f"{where}.interval[1]")
        if self.left >= self.right:
            fail(f"{where}.interval: endpoints are not increasing")
        self.sturm = sturm_sequence(self.minpoly)
        if root_count(self.sturm, self.left, self.right) != 1:
            fail(f"{where}.interval: does not contain exactly one real root")
        try:
            import sympy
            x = sympy.Symbol("x")
            sp = sympy.Poly(sum(sympy.Rational(c.numerator, c.denominator) * x**i
                                for i, c in enumerate(self.minpoly)), x, domain=sympy.QQ)
            irreducible = bool(sp.is_irreducible)
        except ImportError:
            fail("SymPy is required for the exact irreducibility check")
        if not irreducible:
            fail(f"{where}.minpoly: polynomial is reducible over Q")
        self.zero = Elem(self, ())
        self.one = Elem(self, (Fraction(1),))

    def make(self, raw: Sequence[Fraction]) -> Elem:
        p = list(raw)
        d = self.degree
        while len(p) > d:
            c = p.pop()
            if c:
                k = len(p) - d
                for i in range(d):
                    p[k + i] -= c * self.minpoly[i]
        return Elem(self, trim(p))

    def coerce(self, value: Any) -> Elem:
        if isinstance(value, Elem):
            if value.field is not self:
                raise TypeError("different fields")
            return value
        return self.make([Fraction(value)])

    def parse(self, value: Any, where: str) -> Elem:
        if isinstance(value, list):
            if len(value) > self.degree:
                fail(f"{where}: polynomial degree is not reduced modulo minpoly")
            return self.make([as_fraction(x, f"{where}[{i}]") for i, x in enumerate(value)])
        return self.make([as_fraction(value, where)])

    def sign(self, value: Elem) -> int:
        value = self.coerce(value)
        if not value:
            return 0
        if self.degree == 1:
            return 1 if value.coeffs[0] > 0 else -1
        left, right = self.left, self.right
        for _ in range(2048):
            lo, hi = interval_poly(value.coeffs, (left, right))
            if lo > 0:
                return 1
            if hi < 0:
                return -1
            mid = (left + right) / 2
            if poly_eval(self.minpoly, mid) == 0:
                fail("internal error: irreducible polynomial of degree > 1 has rational root")
            if root_count(self.sturm, left, mid) == 1:
                right = mid
            else:
                left = mid
        fail("could not separate sign of a nonzero field element")


@dataclass(frozen=True)
class Cx:
    re: Elem
    im: Elem

    @property
    def field(self) -> RealField:
        return self.re.field

    def __add__(self, other: Any) -> "Cx":
        b = cx_coerce(self.field, other)
        return Cx(self.re + b.re, self.im + b.im)

    __radd__ = __add__

    def __neg__(self) -> "Cx":
        return Cx(-self.re, -self.im)

    def __sub__(self, other: Any) -> "Cx":
        return self + (-cx_coerce(self.field, other))

    def __rsub__(self, other: Any) -> "Cx":
        return cx_coerce(self.field, other) - self

    def __mul__(self, other: Any) -> "Cx":
        b = cx_coerce(self.field, other)
        return Cx(self.re * b.re - self.im * b.im,
                  self.re * b.im + self.im * b.re)

    __rmul__ = __mul__

    def conjugate(self) -> "Cx":
        return Cx(self.re, -self.im)

    def norm2(self) -> Elem:
        return self.re * self.re + self.im * self.im

    def inverse(self) -> "Cx":
        n = self.norm2()
        if not n:
            raise ZeroDivisionError
        return Cx(self.re / n, -self.im / n)

    def __truediv__(self, other: Any) -> "Cx":
        return self * cx_coerce(self.field, other).inverse()

    def __bool__(self) -> bool:
        return bool(self.re) or bool(self.im)


def cx_coerce(field: RealField, value: Any) -> Cx:
    if isinstance(value, Cx):
        if value.field is not field:
            raise TypeError("different fields")
        return value
    return Cx(field.coerce(value), field.zero)


def parse_cx(field: RealField, value: Any, where: str) -> Cx:
    if isinstance(value, dict):
        exact_keys(value, {"re", "im"}, where=where)
        return Cx(field.parse(value["re"], where + ".re"),
                  field.parse(value["im"], where + ".im"))
    return Cx(field.parse(value, where), field.zero)


def zero_row(field: RealField, n: int) -> list[Cx]:
    return [Cx(field.zero, field.zero) for _ in range(n)]


def matrix_rank(rows: Sequence[Sequence[Cx]], ncols: int) -> int:
    a = [list(row) for row in rows if any(row)]
    rank = 0
    for col in range(ncols):
        pivot = next((i for i in range(rank, len(a)) if a[i][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = a[rank][col].inverse()
        a[rank] = [x * inv for x in a[rank]]
        for i in range(len(a)):
            if i != rank and a[i][col]:
                c = a[i][col]
                a[i] = [x - c * y for x, y in zip(a[i], a[rank])]
        rank += 1
        if rank == len(a):
            break
    return rank


def in_rowspace(row: Sequence[Cx], rows: Sequence[Sequence[Cx]], ncols: int) -> bool:
    return matrix_rank(rows, ncols) == matrix_rank([*rows, row], ncols)


def same_rowspace(a: Sequence[Sequence[Cx]], b: Sequence[Sequence[Cx]], ncols: int) -> bool:
    ra = matrix_rank(a, ncols)
    rb = matrix_rank(b, ncols)
    return ra == rb and matrix_rank([*a, *b], ncols) == ra


@dataclass
class Graph:
    n: int
    edges: set[tuple[int, int]]


def decode_graph6(code: str, where: str = "g6") -> Graph:
    if not isinstance(code, str) or not code:
        fail(f"{where}: expected nonempty graph6 string")
    if code.startswith(">>") or any(ord(c) < 63 or ord(c) > 126 for c in code):
        fail(f"{where}: unsupported header or non-graph6 byte")
    vals = [ord(c) - 63 for c in code]
    pos = 0
    if vals[0] <= 62:
        n, pos = vals[0], 1
    elif len(vals) >= 4 and vals[0] == 63 and vals[1] != 63:
        n = (vals[1] << 12) | (vals[2] << 6) | vals[3]
        pos = 4
    else:
        fail(f"{where}: graph order encoding is unsupported")
    need_bits = n * (n - 1) // 2
    need_chars = (need_bits + 5) // 6
    if len(vals) - pos != need_chars:
        fail(f"{where}: wrong graph6 length for n={n}")
    bits: list[int] = []
    for v in vals[pos:]:
        bits.extend((v >> shift) & 1 for shift in range(5, -1, -1))
    if any(bits[need_bits:]):
        fail(f"{where}: nonzero graph6 padding bits")
    edges: set[tuple[int, int]] = set()
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                edges.add((i, j))
            k += 1
    return Graph(n, edges)


def check_canonical_g6(code: str, labelg: str) -> None:
    check_canonical_g6_list([code], labelg)


def check_canonical_g6_list(codes: Sequence[str], labelg: str) -> None:
    if not codes:
        return
    try:
        proc = subprocess.run([labelg, "-q"], input=("\n".join(codes) + "\n").encode("ascii"),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=540, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"canonical graph6 check could not run {labelg}: {exc}")
    if proc.returncode != 0:
        fail(f"canonical graph6 check failed: {proc.stderr.decode(errors='replace').strip()}")
    lines = proc.stdout.decode("ascii").splitlines()
    if lines != list(codes):
        mismatch = next((i for i, pair in enumerate(itertools.zip_longest(lines, codes), 1)
                         if pair[0] != pair[1]), 1)
        fail(f"g6: graph6 record {mismatch} is not nauty-labelg canonical")


def parse_edges(value: Any, n: int, where: str) -> set[tuple[int, int]]:
    if not isinstance(value, list):
        fail(f"{where}: expected edge list")
    result: set[tuple[int, int]] = set()
    previous: tuple[int, int] | None = None
    for i, edge in enumerate(value):
        if not isinstance(edge, list) or len(edge) != 2:
            fail(f"{where}[{i}]: expected [u,v]")
        u = as_int(edge[0], f"{where}[{i}][0]")
        v = as_int(edge[1], f"{where}[{i}][1]")
        if not 0 <= u < v < n:
            fail(f"{where}[{i}]: endpoints must satisfy 0 <= u < v < {n}")
        e = (u, v)
        if previous is not None and e <= previous:
            fail(f"{where}: edges must be unique and lexicographically sorted")
        result.add(e)
        previous = e
    return result


def edge_list(edges: Iterable[tuple[int, int]]) -> list[list[int]]:
    return [list(e) for e in sorted(edges)]


def directed_edge(value: Any, graph: Graph, where: str, require_edge: bool = True) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        fail(f"{where}: expected [u,v]")
    u = as_int(value[0], where + "[0]")
    v = as_int(value[1], where + "[1]")
    if not (0 <= u < graph.n and 0 <= v < graph.n and u != v):
        fail(f"{where}: invalid distinct vertices")
    present = tuple(sorted((u, v))) in graph.edges
    if require_edge and not present:
        fail(f"{where}: is not an edge in the node graph")
    if not require_edge and present:
        fail(f"{where}: must be a non-edge in the node graph")
    return u, v


def four_cycle_rows(graph: Graph, field: RealField) -> list[list[Cx]]:
    seen: set[tuple[int, ...]] = set()
    rows: list[list[Cx]] = []
    for vertices in itertools.combinations(range(graph.n), 4):
        first = vertices[0]
        for tail in itertools.permutations(vertices[1:]):
            cycle = (first,) + tail
            if cycle[1] > cycle[-1]:
                continue
            if not all(tuple(sorted((cycle[i], cycle[(i + 1) % 4]))) in graph.edges for i in range(4)):
                continue
            ints = [0] * graph.n
            for i, v in enumerate(cycle):
                ints[v] += 1 if i % 2 == 0 else -1
            neg = tuple(-x for x in ints)
            key = min(tuple(ints), neg)
            if key in seen:
                continue
            seen.add(key)
            rows.append([cx_coerce(field, x) for x in ints])
    return rows


def parse_matrix(field: RealField, value: Any, n: int, where: str) -> list[list[Cx]]:
    if not isinstance(value, list):
        fail(f"{where}: expected row array")
    rows: list[list[Cx]] = []
    for i, raw in enumerate(value):
        if not isinstance(raw, list) or len(raw) != n:
            fail(f"{where}[{i}]: expected row of length {n}")
        rows.append([parse_cx(field, x, f"{where}[{i}][{j}]") for j, x in enumerate(raw)])
    return rows


def relation_row(field: RealField, n: int, terms: Sequence[tuple[Cx, tuple[int, int]]]) -> list[Cx]:
    row = zero_row(field, n)
    for coefficient, (u, v) in terms:
        row[u] = row[u] + coefficient
        row[v] = row[v] - coefficient
    return row


def verify_embedding(graph: Graph, witness: Any, where: str) -> None:
    exact_keys(witness, {"field", "coordinates"}, where=where)
    field = RealField(witness["field"], where + ".field")
    coords_raw = witness["coordinates"]
    if not isinstance(coords_raw, list) or len(coords_raw) != graph.n:
        fail(f"{where}.coordinates: expected {graph.n} points")
    coords: list[tuple[Elem, Elem]] = []
    for i, point in enumerate(coords_raw):
        if not isinstance(point, list) or len(point) != 2:
            fail(f"{where}.coordinates[{i}]: expected [x,y]")
        coords.append((field.parse(point[0], f"{where}.coordinates[{i}][0]"),
                       field.parse(point[1], f"{where}.coordinates[{i}][1]")))
    for i in range(graph.n):
        for j in range(i):
            if coords[i][0] == coords[j][0] and coords[i][1] == coords[j][1]:
                fail(f"{where}: points {j} and {i} collide")
    for u, v in sorted(graph.edges):
        dx = coords[u][0] - coords[v][0]
        dy = coords[u][1] - coords[v][1]
        if dx * dx + dy * dy != field.one:
            fail(f"{where}: edge ({u},{v}) does not have squared distance 1")


def verify_refutation(graph: Graph, witness: Any, where: str) -> int:
    exact_keys(witness, {"field", "tree"}, where=where)
    field = RealField(witness["field"], where + ".field")
    nodes = 0

    def visit(node: Any, expected_graph: Graph, expected_rows: list[list[Cx]] | None,
              node_where: str, depth: int) -> tuple[list[list[Cx]], Graph]:
        nonlocal nodes
        nodes += 1
        if nodes > 100000 or depth > 1000:
            fail(f"{node_where}: proof tree exceeds safety limit")
        exact_keys(node, {"edges", "A", "move", "children"}, where=node_where)
        edges = parse_edges(node["edges"], graph.n, node_where + ".edges")
        current = Graph(graph.n, edges)
        if current.edges != expected_graph.edges:
            fail(f"{node_where}.edges: inconsistent with the parent move")
        rows = parse_matrix(field, node["A"], graph.n, node_where + ".A")
        target_rows = four_cycle_rows(current, field) if expected_rows is None else expected_rows
        if not same_rowspace(rows, target_rows, graph.n):
            fail(f"{node_where}.A: row space is inconsistent with the claimed constraints")
        move = node["move"]
        if not isinstance(move, dict) or "kind" not in move or not isinstance(move["kind"], str):
            fail(f"{node_where}.move: expected move object with string kind")
        children = node["children"]
        if not isinstance(children, list):
            fail(f"{node_where}.children: expected array")
        kind = move["kind"]
        if kind == "L1a":
            exact_keys(move, {"kind", "pair"}, where=node_where + ".move")
            if children:
                fail(f"{node_where}: L1a contradiction must be a leaf")
            pair = move["pair"]
            if not isinstance(pair, list) or len(pair) != 2:
                fail(f"{node_where}.move.pair: expected [u,v]")
            u = as_int(pair[0], node_where + ".move.pair[0]")
            v = as_int(pair[1], node_where + ".move.pair[1]")
            if not (0 <= u < graph.n and 0 <= v < graph.n and u != v):
                fail(f"{node_where}.move.pair: invalid distinct vertices")
            collision = relation_row(field, graph.n, [(cx_coerce(field, 1), (u, v))])
            if not in_rowspace(collision, rows, graph.n):
                fail(f"{node_where}: L1a collision is not a consequence of A")
        elif kind in ("L1b", "L2"):
            exact_keys(move, {"kind", "edges", "omega"}, where=node_where + ".move")
            es = move["edges"]
            if not isinstance(es, list) or len(es) != 2:
                fail(f"{node_where}.move.edges: expected two directed pairs")
            e1 = directed_edge(es[0], current, node_where + ".move.edges[0]")
            e2 = directed_edge(es[1], current, node_where + ".move.edges[1]", require_edge=(kind == "L1b"))
            omega = parse_cx(field, move["omega"], node_where + ".move.omega")
            relation = relation_row(field, graph.n,
                                    [(cx_coerce(field, 1), e1), (-omega, e2)])
            if not in_rowspace(relation, rows, graph.n):
                fail(f"{node_where}: {kind} ratio is not a consequence of A")
            unit = omega.norm2() == field.one
            if kind == "L1b":
                if unit:
                    fail(f"{node_where}: L1b omega has unit modulus")
                if children:
                    fail(f"{node_where}: L1b contradiction must be a leaf")
            else:
                if not unit:
                    fail(f"{node_where}: L2 omega does not have unit modulus")
                if len(children) != 1:
                    fail(f"{node_where}: L2 must have exactly one child")
                new_edges = set(current.edges)
                new_edges.add(tuple(sorted(e2)))
                child_graph = Graph(graph.n, new_edges)
                next_rows = [*rows, *four_cycle_rows(child_graph, field)]
                visit(children[0], child_graph, next_rows, node_where + ".children[0]", depth + 1)
        elif kind == "L1c":
            exact_keys(move, {"kind", "edges", "coefficients"}, where=node_where + ".move")
            if children:
                fail(f"{node_where}: L1c contradiction must be a leaf")
            es = move["edges"]
            cs = move["coefficients"]
            if not isinstance(es, list) or len(es) != 3 or not isinstance(cs, list) or len(cs) != 3:
                fail(f"{node_where}.move: L1c needs three edges and three coefficients")
            directed = [directed_edge(e, current, f"{node_where}.move.edges[{i}]") for i, e in enumerate(es)]
            coeff = [parse_cx(field, c, f"{node_where}.move.coefficients[{i}]") for i, c in enumerate(cs)]
            if not all(coeff):
                fail(f"{node_where}: L1c coefficients a,b,c must each be nonzero")
            base = relation_row(field, graph.n, list(zip(coeff, directed)))
            if not in_rowspace(base, rows, graph.n):
                fail(f"{node_where}: L1c three-edge relation is not a consequence of A")
            a, b, c = coeff
            aa, bb, cc = a.norm2(), b.norm2(), c.norm2()
            discriminant = 4 * aa * bb - (aa + bb - cc) * (aa + bb - cc)
            if field.sign(discriminant) >= 0:
                fail(f"{node_where}: L1c discriminant is not negative at the selected real root")
        elif kind == "L3":
            exact_keys(move, {"kind", "edges", "coefficients", "d"}, where=node_where + ".move")
            es = move["edges"]
            cs = move["coefficients"]
            if not isinstance(es, list) or len(es) != 3 or not isinstance(cs, list) or len(cs) != 3:
                fail(f"{node_where}.move: L3 needs three edges and three coefficients")
            directed = [directed_edge(e, current, f"{node_where}.move.edges[{i}]") for i, e in enumerate(es)]
            coeff = [parse_cx(field, c, f"{node_where}.move.coefficients[{i}]") for i, c in enumerate(cs)]
            if not all(coeff):
                fail(f"{node_where}: L3 coefficients a,b,c must each be nonzero")
            base = relation_row(field, graph.n, list(zip(coeff, directed)))
            if not in_rowspace(base, rows, graph.n):
                fail(f"{node_where}: L3 three-edge relation is not a consequence of A")
            a, b, c = coeff
            aa, bb, cc = a.norm2(), b.norm2(), c.norm2()
            q = aa + bb - cc
            discriminant = 4 * aa * bb - q * q
            d = field.parse(move["d"], node_where + ".move.d")
            if d * d != discriminant:
                fail(f"{node_where}: L3 d does not square to the recomputed discriminant")
            if field.sign(discriminant) < 0:
                fail(f"{node_where}: L3 discriminant is negative at the selected real root")
            if len(children) != 2:
                fail(f"{node_where}: L3 must have exactly two children")
            iad = Cx(field.zero, d)
            second = cx_coerce(field, 2 * aa) * b
            plus = relation_row(field, graph.n, [((cx_coerce(field, q) + iad) * a, directed[0]),
                                                  (second, directed[1])])
            minus = relation_row(field, graph.n, [((cx_coerce(field, q) - iad) * a, directed[0]),
                                                   (second, directed[1])])
            visit(children[0], current, [*rows, plus], node_where + ".children[0]", depth + 1)
            visit(children[1], current, [*rows, minus], node_where + ".children[1]", depth + 1)
        else:
            fail(f"{node_where}.move.kind: unsupported move {kind!r}")
        return rows, current

    visit(witness["tree"], graph, None, where + ".tree", 0)
    return nodes


def verify_map(raw: Any, pattern_n: int, target_n: int, where: str) -> list[int]:
    if not isinstance(raw, list) or len(raw) != pattern_n:
        fail(f"{where}: expected map array of length {pattern_n}")
    mapping = [as_int(x, f"{where}[{i}]") for i, x in enumerate(raw)]
    if any(x < 0 or x >= target_n for x in mapping):
        fail(f"{where}: image vertex out of range")
    if len(set(mapping)) != len(mapping):
        fail(f"{where}: map is not injective")
    return mapping


def pattern_order(edges: Sequence[Sequence[int]]) -> int:
    vertices = {x for e in edges for x in e}
    if not vertices or vertices != set(range(max(vertices) + 1)):
        fail("trusted pattern data has non-contiguous vertices")
    return max(vertices) + 1


def verify_pattern_edges(pattern_edges: Sequence[Sequence[int]], mapping: Sequence[int], graph: Graph, where: str) -> None:
    for i, e in enumerate(pattern_edges):
        if not isinstance(e, list) or len(e) != 2:
            fail(f"trusted pattern data edge {i} is malformed")
        image = tuple(sorted((mapping[e[0]], mapping[e[1]])))
        if image not in graph.edges:
            fail(f"{where}: pattern edge {i} maps to absent edge {image}")


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            fail(f"JSON object has duplicate key {key!r}")
        out[key] = value
    return out


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"{path}: cannot read JSON: {exc}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
    except OSError as exc:
        fail(f"cannot hash {path}: {exc}")
    return h.hexdigest()


def valid_hash(value: Any, where: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        fail(f"{where}: expected lowercase SHA-256 hex digest")
    return value


def resolve_record_path(manifest_path: Path, value: Any, where: str) -> Path:
    if not isinstance(value, str) or not value:
        fail(f"{where}: expected path string")
    p = Path(value)
    return (manifest_path.parent / p).resolve() if not p.is_absolute() else p.resolve()


def count_records(path: Path) -> int:
    if path.suffix in (".zst", ".zstd"):
        try:
            proc = subprocess.Popen(["/usr/bin/zstd", "-q", "-dc", str(path)],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as exc:
            fail(f"cannot start zstd for {path}: {exc}")
        assert proc.stdout is not None
        count = 0
        try:
            for i, line in enumerate(proc.stdout, 1):
                if not line.endswith(b"\n"):
                    proc.kill()
                    fail(f"{path}: decompressed record {i} lacks final newline")
                if not line.strip():
                    proc.kill()
                    fail(f"{path}: blank decompressed record {i}")
                count += 1
            returncode = proc.wait(timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            proc.kill()
            proc.wait()
            fail(f"cannot decompress {path}: {exc}")
        if returncode != 0:
            fail(f"zstd rejected compressed record file {path}")
        return count
    try:
        with path.open("rb") as stream:
            count = 0
            for i, line in enumerate(stream, 1):
                if not line.endswith(b"\n"):
                    fail(f"{path}: record {i} lacks final newline")
                if not line.strip():
                    fail(f"{path}: blank record {i}")
                count += 1
            return count
    except OSError as exc:
        fail(f"cannot count records in {path}: {exc}")


def verify_manifests(directory: Path) -> dict[str, int]:
    paths = sorted(directory.rglob("*.json"))
    if not paths:
        fail(f"manifest directory {directory} contains no JSON manifests")
    ranges: dict[Path, list[tuple[int, int, Path]]] = {}
    software_seen: dict[str, str] = {}
    shard_ids: set[str] = set()
    child_hashes: set[str] = set()
    parent_hashes: set[str] = set()
    for path in paths:
        obj = load_json(path)
        required = {"shard_id", "parent_file", "parent_range", "software_sha256",
                    "inputs_sha256", "started", "finished", "children_written",
                    "children_file", "children_sha256", "host", "exit_status"}
        exact_keys(obj, required, where=str(path))
        sid = obj["shard_id"]
        if not isinstance(sid, str) or not sid or sid in shard_ids:
            fail(f"{path}.shard_id: empty or duplicate")
        shard_ids.add(sid)
        parent = resolve_record_path(path, obj["parent_file"], str(path) + ".parent_file")
        pr = obj["parent_range"]
        if not isinstance(pr, list) or len(pr) != 2:
            fail(f"{path}.parent_range: expected [i,j]")
        i, j = as_int(pr[0], str(path) + ".parent_range[0]"), as_int(pr[1], str(path) + ".parent_range[1]")
        if i < 0 or j < i:
            fail(f"{path}.parent_range: invalid half-open range")
        ranges.setdefault(parent, []).append((i, j, path))
        parent_actual = sha256_file(parent)
        parent_hashes.add(parent_actual)
        inputs = obj["inputs_sha256"]
        if isinstance(inputs, str):
            supplied_parent_hash = valid_hash(inputs, str(path) + ".inputs_sha256")
        elif isinstance(inputs, dict):
            if not inputs:
                fail(f"{path}.inputs_sha256: mapping must not be empty")
            checked = {str(resolve_record_path(path, k, str(path) + ".inputs_sha256 key")):
                       valid_hash(v, str(path) + f".inputs_sha256[{k!r}]") for k, v in inputs.items()}
            key = str(parent)
            if key not in checked:
                fail(f"{path}.inputs_sha256: does not name parent_file")
            supplied_parent_hash = checked[key]
            for named, digest in checked.items():
                if sha256_file(Path(named)) != digest:
                    fail(f"{path}.inputs_sha256: hash mismatch for {named}")
        else:
            fail(f"{path}.inputs_sha256: expected digest or path-to-digest object")
        if supplied_parent_hash != parent_actual:
            fail(f"{path}.inputs_sha256: parent file hash mismatch")
        software = obj["software_sha256"]
        if not isinstance(software, dict) or not software:
            fail(f"{path}.software_sha256: expected nonempty path-to-digest object")
        for name, digest_raw in software.items():
            actual_path = resolve_record_path(path, name, str(path) + ".software_sha256 key")
            digest = valid_hash(digest_raw, str(path) + f".software_sha256[{name!r}]")
            if sha256_file(actual_path) != digest:
                fail(f"{path}.software_sha256: hash mismatch for {actual_path}")
            logical = actual_path.name
            if logical in software_seen and software_seen[logical] != digest:
                fail(f"{path}.software_sha256: inconsistent hash for software basename {logical}")
            software_seen[logical] = digest
        child = resolve_record_path(path, obj["children_file"], str(path) + ".children_file")
        child_digest = valid_hash(obj["children_sha256"], str(path) + ".children_sha256")
        if sha256_file(child) != child_digest:
            fail(f"{path}.children_sha256: child file hash mismatch")
        child_hashes.add(child_digest)
        written = as_int(obj["children_written"], str(path) + ".children_written")
        if written < 0 or count_records(child) != written:
            fail(f"{path}.children_written: does not equal child record count")
        if not isinstance(obj["started"], str) or not isinstance(obj["finished"], str):
            fail(f"{path}: started and finished must be strings")
        if not isinstance(obj["host"], str) or not obj["host"]:
            fail(f"{path}.host: expected nonempty string")
        if as_int(obj["exit_status"], str(path) + ".exit_status") != 0:
            fail(f"{path}.exit_status: shard did not finish successfully")
    for parent, pieces in ranges.items():
        pieces.sort()
        cursor = 0
        for i, j, path in pieces:
            if i != cursor:
                fail(f"{parent}: shard ranges have a gap or overlap before {path}, expected {cursor}, got {i}")
            cursor = j
        records = count_records(parent)
        if cursor != records:
            fail(f"{parent}: shard ranges end at {cursor}, parent has {records} records")
    # This establishes direct hash links when a shard consumes a previous shard file.
    # Merged/deduplicated frozen files need an additional merge manifest, which the
    # current contract does not specify.  Such roots are reported, not invented.
    roots = len(parent_hashes - child_hashes)
    return {"manifests": len(paths), "parents": len(ranges), "chain_roots": roots}


def load_trusted_data(data_dir: Path) -> tuple[list[Any], list[Any]]:
    forbidden = load_json(data_dir / "forbidden-74.json")
    gadgets = load_json(data_dir / "tu-gadgets.json")
    if not isinstance(forbidden, list) or len(forbidden) != 74:
        fail("forbidden-74.json does not contain 74 patterns")
    if not isinstance(gadgets, list) or len(gadgets) != 6:
        fail("tu-gadgets.json does not contain six gadgets")
    for index, pattern in enumerate(forbidden):
        if not isinstance(pattern, list):
            fail(f"forbidden pattern {index}: expected edge list")
        n = pattern_order(pattern)
        seen: set[tuple[int, int]] = set()
        for j, edge in enumerate(pattern):
            if (not isinstance(edge, list) or len(edge) != 2 or
                    any(isinstance(x, bool) or not isinstance(x, int) for x in edge)):
                fail(f"forbidden pattern {index} edge {j}: malformed")
            u, v = edge
            if not (0 <= u < n and 0 <= v < n and u != v):
                fail(f"forbidden pattern {index} edge {j}: invalid endpoints")
            e = tuple(sorted((u, v)))
            if e in seen:
                fail(f"forbidden pattern {index}: duplicate edge {e}")
            seen.add(e)
    for index, gadget in enumerate(gadgets):
        exact_keys(gadget, {"n", "m", "edges", "pair"}, where=f"TU gadget {index}")
        n = as_int(gadget["n"], f"TU gadget {index}.n")
        m = as_int(gadget["m"], f"TU gadget {index}.m")
        if n < 1 or not isinstance(gadget["edges"], list) or len(gadget["edges"]) != m:
            fail(f"TU gadget {index}: n or m is inconsistent with its edges")
        normalized: set[tuple[int, int]] = set()
        for j, edge in enumerate(gadget["edges"]):
            if (not isinstance(edge, list) or len(edge) != 2 or
                    any(isinstance(x, bool) or not isinstance(x, int) for x in edge)):
                fail(f"TU gadget {index} edge {j}: malformed")
            u, v = edge
            if not (0 <= u < v < n) or (u, v) in normalized:
                fail(f"TU gadget {index} edge {j}: invalid, unsorted, or duplicate")
            normalized.add((u, v))
        pair = gadget["pair"]
        if (not isinstance(pair, list) or len(pair) != 2 or
                any(isinstance(x, bool) or not isinstance(x, int) for x in pair) or
                not (0 <= pair[0] < pair[1] < n) or tuple(pair) in normalized):
            fail(f"TU gadget {index}.pair: must be a valid stored non-edge")
    return forbidden, gadgets


def read_graph_list(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read graph list {path}: {exc}")
    if raw and not raw.endswith(b"\n"):
        fail(f"{path}: missing final newline")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        fail(f"{path}: non-ASCII graph list: {exc}")
    if any(not line for line in lines):
        fail(f"{path}: blank graph6 record")
    return lines


def verify_certificates(cert_path: Path, forbidden: list[Any], gadgets: list[Any],
                        expect_n: int | None, expect_m: int | None, labelg: str,
                        graph_list: Path | None, unknown_path: Path | None) -> dict[str, Any]:
    counts = {k: 0 for k in ("forbidden", "tu", "embedded", "refuted", "unknown")}
    codes: list[str] = []
    seen_codes: set[str] = set()
    unknown: list[str] = []
    proof_nodes = 0
    try:
        stream = cert_path.open("r", encoding="utf-8")
    except OSError as exc:
        fail(f"cannot open certificate file {cert_path}: {exc}")
    with stream:
        for lineno, line in enumerate(stream, 1):
            if not line.endswith("\n"):
                fail(f"{cert_path}:{lineno}: missing final newline")
            if not line.strip():
                fail(f"{cert_path}:{lineno}: blank certificate record")
            try:
                record = json.loads(line, object_pairs_hook=no_duplicate_object)
            except (json.JSONDecodeError, CheckError) as exc:
                fail(f"{cert_path}:{lineno}: invalid JSON: {exc}")
            exact_keys(record, {"g6", "verdict"}, {"witness"}, f"{cert_path}:{lineno}")
            code = record["g6"]
            graph = decode_graph6(code, f"{cert_path}:{lineno}.g6")
            if expect_n is not None and graph.n != expect_n:
                fail(f"{cert_path}:{lineno}: expected {expect_n} vertices, got {graph.n}")
            if expect_m is not None and len(graph.edges) != expect_m:
                fail(f"{cert_path}:{lineno}: expected {expect_m} edges, got {len(graph.edges)}")
            if code in seen_codes:
                fail(f"{cert_path}:{lineno}: duplicate graph6 record")
            codes.append(code)
            seen_codes.add(code)
            verdict = record["verdict"]
            if not isinstance(verdict, str) or verdict not in counts:
                fail(f"{cert_path}:{lineno}.verdict: unsupported verdict {verdict!r}")
            counts[verdict] += 1
            witness = record.get("witness")
            where = f"{cert_path}:{lineno}.witness"
            if verdict == "unknown":
                if "witness" in record and witness is not None:
                    fail(f"{where}: unknown verdict must have no witness or null")
                unknown.append(code)
            elif "witness" not in record or not isinstance(witness, dict):
                fail(f"{where}: verdict requires witness object")
            elif verdict == "forbidden":
                exact_keys(witness, {"index", "map"}, where=where)
                index = as_int(witness["index"], where + ".index")
                if not 0 <= index < len(forbidden):
                    fail(f"{where}.index: out of range")
                pattern = forbidden[index]
                pn = pattern_order(pattern)
                mapping = verify_map(witness["map"], pn, graph.n, where + ".map")
                verify_pattern_edges(pattern, mapping, graph, where)
            elif verdict == "tu":
                exact_keys(witness, {"index", "map", "pair"}, where=where)
                index = as_int(witness["index"], where + ".index")
                if not 0 <= index < 6:
                    fail(f"{where}.index: must select one of the six TU gadgets")
                gadget = gadgets[index]
                exact_keys(gadget, {"n", "m", "edges", "pair"}, where=f"trusted TU gadget {index}")
                mapping = verify_map(witness["map"], gadget["n"], graph.n, where + ".map")
                verify_pattern_edges(gadget["edges"], mapping, graph, where)
                pair_raw = witness["pair"]
                if not isinstance(pair_raw, list) or len(pair_raw) != 2:
                    fail(f"{where}.pair: expected pair")
                pair = [as_int(x, f"{where}.pair[{i}]") for i, x in enumerate(pair_raw)]
                expected_pair = [mapping[x] for x in gadget["pair"]]
                if set(pair) != set(expected_pair) or len(set(pair)) != 2:
                    fail(f"{where}.pair: is not the mapped distinguished gadget pair")
                if tuple(sorted(pair)) in graph.edges:
                    fail(f"{where}.pair: distinguished pair is adjacent in the candidate")
            elif verdict == "embedded":
                verify_embedding(graph, witness, where)
            elif verdict == "refuted":
                proof_nodes += verify_refutation(graph, witness, where)
    if graph_list is not None:
        listed = read_graph_list(graph_list)
        if listed != codes:
            fail("certificate graph6 records do not exactly equal the supplied graph list in order")
    check_canonical_g6_list(codes, labelg)
    if unknown_path is None:
        unknown_path = cert_path.parent / "UNKNOWN.g6"
    if unknown or unknown_path.exists():
        listed_unknown = read_graph_list(unknown_path)
        if listed_unknown != unknown:
            fail("UNKNOWN.g6 does not exactly list unknown certificate records in order")
    return {"records": len(codes), **counts, "proof_nodes": proof_nodes, "unknown_codes": unknown}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("certificates", type=Path, help="Section 2 JSON-lines certificate file")
    parser.add_argument("--graphs", type=Path, help="graph6 list which certificates must match exactly")
    parser.add_argument("--unknown-file", type=Path, help="UNKNOWN.g6 path (default beside certificates)")
    parser.add_argument("--manifest-dir", type=Path, help="directory containing shard JSON manifests")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent / "data")
    parser.add_argument("--expect-n", type=int, default=22)
    parser.add_argument("--expect-m", type=int, default=61)
    parser.add_argument("--allow-any-size", action="store_true",
                        help="disable the default (22,61) order and size gate for self-checks")
    parser.add_argument("--labelg", default="/usr/bin/nauty-labelg")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        forbidden, gadgets = load_trusted_data(args.data_dir)
        summary = verify_certificates(
            args.certificates, forbidden, gadgets,
            None if args.allow_any_size else args.expect_n,
            None if args.allow_any_size else args.expect_m,
            args.labelg, args.graphs, args.unknown_file,
        )
        manifest_summary = verify_manifests(args.manifest_dir) if args.manifest_dir else None
    except CheckError as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 1
    print("ACCEPT certificates " + " ".join(f"{k}={summary[k]}" for k in
          ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes")))
    for code in summary["unknown_codes"]:
        print(f"UNKNOWN {code}")
    if manifest_summary:
        print("ACCEPT manifests " + " ".join(f"{k}={v}" for k, v in manifest_summary.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
