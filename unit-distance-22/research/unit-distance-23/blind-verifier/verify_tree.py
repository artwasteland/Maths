#!/usr/bin/env python3
"""Independent, exact verifier for the supplied refutation-tree format.

Usage: python3 verify_tree.py GRAPH.g6 CERTIFICATE.jsonl

Only the standard library is used.  No certificate-supplied linear constraint
is trusted.  See REPORT.md for the conservative interpretations necessitated
by omissions in spec/FORMAT.md and spec/PROOFS.md.  In particular, L2 is
unsupported and fails closed.
"""

import itertools
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path


class Reject(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise Reject(reason)


def keys(value, required, where, optional=()):
    need(type(value) is dict, where + ": expected an object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    need(not missing, where + ": missing keys " + str(sorted(missing)))
    need(not extra, where + ": unknown keys " + str(sorted(extra)))


def rational(value, where):
    if type(value) is int:
        return Fraction(value)
    if type(value) is str and re.fullmatch(r"[+-]?[0-9]+(?:/[+-]?[0-9]+)?", value):
        parts = value.split("/")
        numerator = int(parts[0])
        denominator = int(parts[1]) if len(parts) == 2 else 1
        need(denominator != 0, where + ": zero rational denominator")
        return Fraction(numerator, denominator)
    raise Reject(where + ": expected an integer or rational string")


# Polynomials over Q, in ascending order; the zero polynomial is ().
def trim(a):
    a = list(a)
    while a and a[-1] == 0:
        a.pop()
    return tuple(a)


def padd(a, b):
    return trim((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
                for i in range(max(len(a), len(b))))


def pscale(a, c):
    return trim(x * c for x in a)


def psub(a, b):
    return padd(a, pscale(b, -1))


def pmul(a, b):
    if not a or not b:
        return ()
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return trim(out)


def pdivmod(a, b):
    need(bool(b), "internal arithmetic: polynomial division by zero")
    a = list(trim(a))
    q = [Fraction(0)] * max(0, len(a) - len(b) + 1)
    while a and len(a) >= len(b):
        k = len(a) - len(b)
        c = Fraction(a[-1]) / b[-1]
        q[k] = c
        for j, x in enumerate(b):
            a[k + j] -= c * x
        while a and a[-1] == 0:
            a.pop()
    return trim(q), tuple(a)


def peval(a, x):
    value = Fraction(0)
    for c in reversed(a):
        value = value * x + c
    return value


def primitive(a):
    denominator = math.lcm(*(c.denominator for c in a))
    ints = [int(c * denominator) for c in a]
    divisor = math.gcd(*ints)
    if ints[-1] < 0:
        divisor = -divisor
    return tuple(x // divisor for x in ints)


def signed_divisors(n):
    n = abs(n)
    small, large = [], []
    for d in range(1, math.isqrt(n) + 1):
        if n % d == 0:
            small.append(d)
            if d * d != n:
                large.append(n // d)
    positive = small + large[::-1]
    return tuple(positive + [-d for d in positive])


def irreducible_over_q(poly):
    """Exact Kronecker factor search, not a probabilistic prime test.

    Gauss's lemma gives an integer factor of degree <= floor(deg(f)/2)
    whenever the primitive integer polynomial f is reducible.  At m+1
    distinct integer points every value of that factor divides f's value.
    Exhaustive interpolation of these divisor choices therefore finds a
    factor if one exists.  This is intended for small certificate fields.
    """
    f = primitive(poly)
    degree = len(f) - 1
    if degree == 1:
        return True
    m = degree // 2
    xs = [0]
    for j in range(1, m + 1):
        xs.extend((j, -j))
    xs = xs[:m + 1]
    values = [int(peval(f, x)) for x in xs]
    if any(v == 0 for v in values):
        return False  # An integer root is a proper linear factor.
    lagrange = []
    for i, x in enumerate(xs):
        basis, denominator = (Fraction(1),), 1
        for j, y in enumerate(xs):
            if i != j:
                basis = pmul(basis, (Fraction(-y), Fraction(1)))
                denominator *= x - y
        lagrange.append(pscale(basis, Fraction(1, denominator)))
    for ys in itertools.product(*(signed_divisors(v) for v in values)):
        candidate = ()
        for y, basis in zip(ys, lagrange):
            candidate = padd(candidate, pscale(basis, y))
        if len(candidate) < 2 or any(c.denominator != 1 for c in candidate):
            continue
        if not pdivmod(f, candidate)[1]:
            return False
    return True


def sturm_sequence(p):
    derivative = trim(i * p[i] for i in range(1, len(p)))
    seq = [p, derivative]
    while seq[-1]:
        remainder = pdivmod(seq[-2], seq[-1])[1]
        if not remainder:
            break
        seq.append(pscale(remainder, -1))
    return tuple(seq)


def variations(seq, x):
    signs = []
    for p in seq:
        v = peval(p, x)
        if v:
            signs.append(1 if v > 0 else -1)
    return sum(a != b for a, b in zip(signs, signs[1:]))


class Field:
    """Q(alpha), embedded using a certified rational isolating interval."""

    def __init__(self, wire):
        keys(wire, ("minpoly", "interval"), "field")
        raw = wire["minpoly"]
        need(type(raw) is list and len(raw) >= 2,
             "field.minpoly: expected a nonconstant polynomial")
        p = tuple(rational(c, "field.minpoly[" + str(i) + "]")
                  for i, c in enumerate(raw))
        need(p[-1] != 0, "field.minpoly: zero leading coefficient")
        need(irreducible_over_q(p), "field.minpoly: reducible over Q")
        self.degree = len(p) - 1
        self.p = pscale(p, 1 / p[-1])
        interval = wire["interval"]
        need(type(interval) is list and len(interval) == 2,
             "field.interval: expected two rational endpoints")
        self.left, self.right = (rational(x, "field.interval") for x in interval)
        need(self.left < self.right, "field.interval: endpoints are not increasing")
        need(peval(self.p, self.left) != 0 and peval(self.p, self.right) != 0,
             "field.interval: a root lies on an endpoint")
        self.sturm = sturm_sequence(self.p)
        count = variations(self.sturm, self.left) - variations(self.sturm, self.right)
        need(count == 1, "field.interval: expected exactly one real root, found " + str(count))
        self.zero = (Fraction(0),) * self.degree
        self.one = (Fraction(1),) + self.zero[1:]
        self._inverses = {self.one: self.one}
        self._signs = {self.zero: 0, self.one: 1}
        self.cz = Complex(self, self.zero, self.zero)
        self.co = Complex(self, self.one, self.zero)

    def real(self, wire, where):
        need(type(wire) is list and 1 <= len(wire) <= self.degree,
             where + ": expected a nonempty real element array of length <= field degree")
        values = tuple(rational(c, where + "[" + str(i) + "]") for i, c in enumerate(wire))
        return values + (Fraction(0),) * (self.degree - len(values))

    def complex(self, wire, where):
        if type(wire) is dict:
            keys(wire, ("re", "im"), where)
            return Complex(self, self.real(wire["re"], where + ".re"),
                           self.real(wire["im"], where + ".im"))
        if type(wire) is list:
            return Complex(self, self.real(wire, where), self.zero)
        return Complex(self, self.scalar(rational(wire, where)), self.zero)

    def scalar(self, q):
        return (Fraction(q),) + self.zero[1:]

    def add(self, a, b):
        return tuple(x + y for x, y in zip(a, b))

    def sub(self, a, b):
        return tuple(x - y for x, y in zip(a, b))

    def neg(self, a):
        return tuple(-x for x in a)

    def scale(self, a, q):
        return tuple(x * q for x in a)

    def mul(self, a, b):
        if a == self.zero or b == self.zero:
            return self.zero
        if a == self.one:
            return b
        if b == self.one:
            return a
        product = list(pmul(trim(a), trim(b)))
        for i in range(len(product) - 1, self.degree - 1, -1):
            c = product[i]
            if c:
                for j in range(self.degree):
                    product[i - self.degree + j] -= c * self.p[j]
        product = product[:self.degree]
        return tuple(product) + (Fraction(0),) * (self.degree - len(product))

    def inv(self, a):
        need(a != self.zero, "internal arithmetic: inverse of zero")
        cached = self._inverses.get(a)
        if cached is not None:
            return cached
        r0, r1 = self.p, trim(a)
        t0, t1 = (), (Fraction(1),)
        while r1:
            q, r2 = pdivmod(r0, r1)
            r0, r1 = r1, r2
            t0, t1 = t1, psub(t0, pmul(q, t1))
        need(len(r0) == 1, "internal arithmetic: element is not invertible")
        reduced = pdivmod(pscale(t0, 1 / r0[0]), self.p)[1]
        result = reduced + (Fraction(0),) * (self.degree - len(reduced))
        need(self.mul(a, result) == self.one, "internal arithmetic: inverse identity failed")
        self._inverses[a] = result
        return result

    def sign(self, a):
        """Exact sign at alpha; irreducibility guarantees termination for a != 0."""
        if a in self._signs:
            return self._signs[a]
        left, right = self.left, self.right
        while True:
            low = high = Fraction(0)
            for c in reversed(a):
                products = (low * left, low * right, high * left, high * right)
                low, high = min(products) + c, max(products) + c
            if low > 0 or high < 0:
                result = 1 if low > 0 else -1
                self._signs[a] = result
                return result
            middle = (left + right) / 2
            if peval(self.p, middle) == 0:
                value = peval(a, middle)
                result = (value > 0) - (value < 0)
                self._signs[a] = result
                return result
            if variations(self.sturm, left) - variations(self.sturm, middle) == 1:
                right = middle
            else:
                left = middle


class Complex:
    __slots__ = ("f", "re", "im")

    def __init__(self, field, real, imaginary):
        self.f, self.re, self.im = field, real, imaginary

    def __bool__(self):
        return self.re != self.f.zero or self.im != self.f.zero

    def __eq__(self, other):
        return (isinstance(other, Complex) and self.f is other.f
                and self.re == other.re and self.im == other.im)

    def __neg__(self):
        return Complex(self.f, self.f.neg(self.re), self.f.neg(self.im))

    def __add__(self, other):
        if not other:
            return self
        if not self:
            return other
        return Complex(self.f, self.f.add(self.re, other.re), self.f.add(self.im, other.im))

    def __sub__(self, other):
        if not other:
            return self
        return Complex(self.f, self.f.sub(self.re, other.re), self.f.sub(self.im, other.im))

    def __mul__(self, other):
        f = self.f
        if not self or not other:
            return f.cz
        return Complex(f, f.sub(f.mul(self.re, other.re), f.mul(self.im, other.im)),
                       f.add(f.mul(self.re, other.im), f.mul(self.im, other.re)))

    def norm2(self):
        return self.f.add(self.f.mul(self.re, self.re), self.f.mul(self.im, self.im))

    def inv(self):
        f = self.f
        denominator = f.inv(self.norm2())
        return Complex(f, f.mul(self.re, denominator), f.neg(f.mul(self.im, denominator)))


def rref(rows, n):
    """The unique reduced basis, with zero rows omitted."""
    out = [list(row) for row in rows]
    rank = 0
    for col in range(n):
        pivot = next((i for i in range(rank, len(out)) if out[i][col]), None)
        if pivot is None:
            continue
        out[rank], out[pivot] = out[pivot], out[rank]
        inverse = out[rank][col].inv()
        out[rank] = [x * inverse for x in out[rank]]
        for i in range(len(out)):
            if i != rank and out[i][col]:
                coefficient = out[i][col]
                out[i] = [x - coefficient * y for x, y in zip(out[i], out[rank])]
        rank += 1
        if rank == len(out):
            break
    return tuple(tuple(row) for row in out[:rank])


def residual(row, basis):
    row = list(row)
    for b in basis:
        pivot = next(i for i, x in enumerate(b) if x)
        if row[pivot]:
            c = row[pivot]
            row = [x - c * y for x, y in zip(row, b)]
    return tuple(row)


def contains(basis, row):
    return not any(residual(row, basis))


def decode_graph6(text, where):
    need(type(text) is str, where + ": expected graph6 text")
    text = text.strip("\r\n")
    if text.startswith(">>graph6<<"):
        text = text[len(">>graph6<<"):].lstrip("\r\n")
    need(bool(text) and "\n" not in text and "\r" not in text,
         where + ": expected exactly one graph6 graph")
    data = [ord(c) - 63 for c in text]
    need(all(0 <= x <= 63 for x in data), where + ": invalid graph6 character")
    if data[0] < 63:
        n, offset = data[0], 1
    elif len(data) >= 2 and data[1] < 63:
        need(len(data) >= 4, where + ": truncated graph6 vertex count")
        n, offset = (data[1] << 12) | (data[2] << 6) | data[3], 4
        need(63 <= n <= 258047, where + ": noncanonical graph6 vertex count")
    else:
        need(len(data) >= 8, where + ": truncated graph6 vertex count")
        n, offset = 0, 8
        for x in data[2:8]:
            n = (n << 6) | x
        need(n >= 258048, where + ": noncanonical graph6 vertex count")
    bit_count = n * (n - 1) // 2
    need(len(data) - offset == (bit_count + 5) // 6,
         where + ": wrong graph6 payload length")
    padding = (-bit_count) % 6
    if padding:
        need(data[-1] & ((1 << padding) - 1) == 0, where + ": nonzero graph6 padding")
    edges, k = set(), 0
    for v in range(1, n):
        for u in range(v):
            if data[offset + k // 6] & (1 << (5 - k % 6)):
                edges.add((u, v))
            k += 1
    return n, frozenset(edges)


def vertex_pair(wire, n, where):
    need(type(wire) is list and len(wire) == 2, where + ": expected a vertex pair")
    u, v = wire
    need(type(u) is int and type(v) is int and 0 <= u < n and 0 <= v < n,
         where + ": vertex outside graph")
    need(u != v, where + ": repeated vertex")
    return u, v


def read_edges(wire, n, where):
    need(type(wire) is list, where + ": expected an edge list")
    edges = set()
    for i, entry in enumerate(wire):
        u, v = vertex_pair(entry, n, where + "[" + str(i) + "]")
        edge = tuple(sorted((u, v)))
        need(edge not in edges, where + ": duplicate undirected edge " + str(edge))
        edges.add(edge)
    return frozenset(edges)


def rhombus_rows(n, edges, f):
    adjacent = [set() for _ in range(n)]
    for u, v in edges:
        adjacent[u].add(v)
        adjacent[v].add(u)
    cycles = set()
    for a, c in itertools.combinations(range(n), 2):
        for b, d in itertools.combinations(sorted(adjacent[a] & adjacent[c]), 2):
            cycles.add(tuple(sorted(((a, c), (b, d)))))
    rows = []
    for (a, c), (b, d) in sorted(cycles):
        row = [f.cz] * n
        row[a] = row[c] = f.co
        row[b] = row[d] = -f.co
        rows.append(tuple(row))
    return rows, len(cycles)


class Verifier:
    def __init__(self, n, edges, record):
        keys(record, ("verdict", "witness"), "record", optional=("g6",))
        need(record["verdict"] == "refuted", "record.verdict: expected refuted")
        witness = record["witness"]
        keys(witness, ("field", "tree"), "witness")
        self.n, self.edges, self.record = n, edges, record
        self.f = Field(witness["field"])
        self.tree = witness["tree"]
        self.stats = {"nodes": 0, "moves": {}, "ranks": {}, "leaf_norm_signs": []}

    def matrix(self, wire, where):
        need(type(wire) is list, where + ": expected a matrix")
        rows = []
        for i, row in enumerate(wire):
            position = where + "[" + str(i) + "]"
            need(type(row) is list and len(row) == self.n,
                 position + ": matrix row must have " + str(self.n) + " columns")
            rows.append(tuple(self.f.complex(x, position + "[" + str(j) + "]")
                              for j, x in enumerate(row)))
        return rows

    def displacement(self, pair):
        # One global directed-edge convention: x_(u,v) = p_v - p_u.
        row = [self.f.cz] * self.n
        u, v = pair
        row[u], row[v] = -self.f.co, self.f.co
        return tuple(row)

    def relation(self, pairs, coefficients):
        row = [self.f.cz] * self.n
        for (u, v), coefficient in zip(pairs, coefficients):
            row[u] = row[u] - coefficient
            row[v] = row[v] + coefficient
        return tuple(row)

    def move_edges(self, move, count, edges, where):
        raw = move["edges"]
        need(type(raw) is list and len(raw) == count,
             where + ".edges: expected " + str(count) + " directed edges")
        pairs = [vertex_pair(e, self.n, where + ".edges[" + str(i) + "]")
                 for i, e in enumerate(raw)]
        for pair in pairs:
            need(tuple(sorted(pair)) in edges,
                 where + ".edges: directed edge is absent from node graph: " + str(pair))
        return pairs

    def heron(self, move, edges, basis, where):
        pairs = self.move_edges(move, 3, edges, where)
        raw = move["coefficients"]
        need(type(raw) is list and len(raw) == 3,
             where + ".coefficients: expected three complex coefficients")
        coefficients = [self.f.complex(x, where + ".coefficients[" + str(i) + "]")
                        for i, x in enumerate(raw)]
        need(all(coefficients), where + ": all three Heron coefficients must be nonzero")
        relation = self.relation(pairs, coefficients)
        need(contains(basis, relation), where + ": ax+by+cz is not in A row space")
        aa, bb, cc = [x.norm2() for x in coefficients]
        f = self.f
        q = f.sub(f.add(aa, bb), cc)
        delta = f.sub(f.scale(f.mul(aa, bb), 4), f.mul(q, q))
        return pairs, coefficients, aa, q, delta

    def node(self, node, expected_edges, expected_basis, path):
        keys(node, ("edges", "A", "move", "children"), path)
        edges = read_edges(node["edges"], self.n, path + ".edges")
        if edges != expected_edges:
            missing, extra = sorted(expected_edges - edges), sorted(edges - expected_edges)
            source = "input graph" if path == "root" else "parent move"
            raise Reject(path + ".edges: does not equal " + source
                         + " (missing=" + str(missing) + ", extra=" + str(extra) + ")")
        basis = rref(self.matrix(node["A"], path + ".A"), self.n)
        source = "all graph 4-cycle rhombus rows" if path == "root" else "parent's specified orientation row space"
        need(basis == expected_basis, path + ".A: row space does not equal " + source)
        move, children = node["move"], node["children"]
        need(type(move) is dict and type(move.get("kind")) is str,
             path + ".move: missing or invalid kind")
        kind = move["kind"]
        forms = {"L1a": ("kind", "pair"), "L1b": ("kind", "edges", "omega"),
                 "L1c": ("kind", "edges", "coefficients"),
                 "L2": ("kind", "edges", "omega"),
                 "L3": ("kind", "edges", "coefficients", "d")}
        need(kind in forms, path + ".move: unknown kind " + kind)
        keys(move, forms[kind], path + ".move")
        need(type(children) is list, path + ".children: expected an array")
        arity = {"L1a": 0, "L1b": 0, "L1c": 0, "L2": 1, "L3": 2}[kind]
        need(len(children) == arity, path + ": " + kind + " requires " + str(arity)
             + " children; found " + str(len(children)))
        self.stats["nodes"] += 1
        self.stats["moves"][kind] = self.stats["moves"].get(kind, 0) + 1
        rank = len(basis)
        self.stats["ranks"][rank] = self.stats["ranks"].get(rank, 0) + 1
        where, f = path + ".move", self.f
        if kind == "L1a":
            pair = vertex_pair(move["pair"], self.n, where + ".pair")
            need(contains(basis, self.displacement(pair)),
                 where + ": L1a does not force the two distinct vertices to coincide")
        elif kind == "L1b":
            pairs = self.move_edges(move, 2, edges, where)
            omega = f.complex(move["omega"], where + ".omega")
            # x = omega*y, so two unit displacements require |omega|^2 = 1.
            need(contains(basis, self.relation(pairs, (f.co, -omega))),
                 where + ": L1b x-omega*y is not in A row space")
            norm_difference = f.sub(omega.norm2(), f.one)
            need(norm_difference != f.zero, where + ": L1b omega has unit squared modulus")
            self.stats["leaf_norm_signs"].append(f.sign(norm_difference))
        elif kind == "L1c":
            _, _, _, _, delta = self.heron(move, edges, basis, where)
            need(f.sign(delta) < 0, where + ": L1c discriminant is not strictly negative")
        elif kind == "L2":
            raise Reject(where + ": L2 is unsupported: supplied specs give no transition rule")
        elif kind == "L3":
            pairs, coefficients, aa, q, delta = self.heron(move, edges, basis, where)
            d = f.real(move["d"], where + ".d")
            need(f.mul(d, d) == delta, where + ": L3 d squared does not equal the Heron discriminant")
            need(f.sign(delta) >= 0, where + ": L3 discriminant is negative at the selected root")
            a, b, _ = coefficients
            second = Complex(f, f.scale(aa, 2), f.zero) * b
            for i, sign in enumerate((1, -1)):
                first = Complex(f, q, f.scale(d, sign)) * a
                extra = self.relation(pairs[:2], (first, second))
                expected = rref(list(basis) + [extra], self.n)
                self.node(children[i], edges, expected, path + ".children[" + str(i) + "]")

    def verify(self):
        rows, cycles = rhombus_rows(self.n, self.edges, self.f)
        self.stats["four_cycles"] = cycles
        expected = rref(rows, self.n)
        self.node(self.tree, self.edges, expected, "root")
        if "g6" in self.record:
            n, edges = decode_graph6(self.record["g6"], "record.g6")
            need((n, edges) == (self.n, self.edges), "record.g6: does not equal input graph")
        return self.stats


def load_record(path):
    def no_duplicates(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, "JSON: duplicate object key " + key)
            out[key] = value
        return out

    def no_float(value):
        raise Reject("JSON: floating-point or nonfinite number is forbidden: " + value)

    # json.loads also rejects a second record or non-whitespace trailing text.
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=no_duplicates,
                      parse_float=no_float, parse_constant=no_float)


def verify_files(graph_path, record_path):
    n, edges = decode_graph6(Path(graph_path).read_text(encoding="ascii"), "graph")
    return Verifier(n, edges, load_record(record_path)).verify()


def main(argv):
    try:
        need(len(argv) == 3, "usage: python3 verify_tree.py GRAPH.g6 CERTIFICATE.jsonl")
        verify_files(argv[1], argv[2])
    except Reject as error:
        print("REJECT " + str(error))
        return 1
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError,
            ZeroDivisionError, RecursionError, OverflowError) as error:
        print("REJECT input/arithmetic failure: " + type(error).__name__ + ": " + str(error))
        return 1
    print("ACCEPT")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
