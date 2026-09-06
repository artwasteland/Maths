#!/usr/bin/env python3
"""Independent exact verifier for embedded unit-distance certificates.

This module deliberately contains no embedding or search code.  Its public
function parses graph6, validates the stated real number field, and checks
point distinctness and every edge squared distance using Fraction arithmetic.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable

import sympy as sp


class CertificateError(ValueError):
    """Raised when an embedded certificate fails an exact check."""


def parse_graph6(code: str) -> tuple[int, list[tuple[int, int]]]:
    """Parse the graph6 subset used here, with at most 62 vertices."""
    if code.startswith(">>graph6<<"):
        code = code[10:]
    if not code:
        raise CertificateError("empty graph6 string")
    values = [ord(ch) - 63 for ch in code]
    if any(value < 0 or value > 63 for value in values):
        raise CertificateError("invalid graph6 character")
    n = values[0]
    if n > 62:
        raise CertificateError("only short graph6 order fields are supported")
    bits: list[int] = []
    for value in values[1:]:
        bits.extend((value >> shift) & 1 for shift in range(5, -1, -1))
    needed = n * (n - 1) // 2
    if len(bits) < needed:
        raise CertificateError("truncated graph6 string")
    edges: list[tuple[int, int]] = []
    cursor = 0
    for upper in range(1, n):
        for lower in range(upper):
            if bits[cursor]:
                edges.append((lower, upper))
            cursor += 1
    return n, edges


def _fraction(value: object) -> Fraction:
    if not isinstance(value, (str, int)):
        raise CertificateError("rational coefficients must be strings or integers")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise CertificateError("invalid rational coefficient") from exc


class NumberField:
    """The exact quotient Q[a]/(p), represented in the power basis."""

    def __init__(self, polynomial: Iterable[object]):
        self.polynomial = tuple(_fraction(value) for value in polynomial)
        if len(self.polynomial) < 2 or self.polynomial[-1] == 0:
            raise CertificateError("the field polynomial must have positive degree")
        self.degree = len(self.polynomial) - 1

    def element(self, coefficients: object) -> tuple[Fraction, ...]:
        if not isinstance(coefficients, list) or len(coefficients) > self.degree:
            raise CertificateError("coordinate is not a power-basis polynomial")
        result = [_fraction(value) for value in coefficients]
        result.extend(Fraction(0) for _ in range(self.degree - len(result)))
        return tuple(result)

    def add(self, left: tuple[Fraction, ...], right: tuple[Fraction, ...]):
        return tuple(a + b for a, b in zip(left, right))

    def sub(self, left: tuple[Fraction, ...], right: tuple[Fraction, ...]):
        return tuple(a - b for a, b in zip(left, right))

    def mul(self, left: tuple[Fraction, ...], right: tuple[Fraction, ...]):
        work = [Fraction(0) for _ in range(2 * self.degree - 1)]
        for i, a in enumerate(left):
            for j, b in enumerate(right):
                work[i + j] += a * b
        lead = self.polynomial[-1]
        for power in range(len(work) - 1, self.degree - 1, -1):
            factor = work[power] / lead
            if factor:
                offset = power - self.degree
                for j, coefficient in enumerate(self.polynomial):
                    work[offset + j] -= factor * coefficient
        return tuple(work[: self.degree])

    def is_zero(self, value: tuple[Fraction, ...]) -> bool:
        return all(coefficient == 0 for coefficient in value)

    @property
    def one(self) -> tuple[Fraction, ...]:
        return (Fraction(1),) + (Fraction(0),) * (self.degree - 1)


def _validate_real_field(field_data: object) -> NumberField:
    if not isinstance(field_data, dict):
        raise CertificateError("missing field object")
    if set(field_data) != {"minpoly", "interval"}:
        raise CertificateError("field must contain exactly minpoly and interval")
    field = NumberField(field_data.get("minpoly", []))
    x = sp.Symbol("x")
    coefficients = [sp.Rational(c.numerator, c.denominator) for c in field.polynomial]
    polynomial = sp.Poly(sum(c * x**i for i, c in enumerate(coefficients)), x, domain=sp.QQ)
    if not polynomial.is_irreducible:
        raise CertificateError("the stated polynomial is not irreducible over Q")
    interval = field_data.get("interval")
    if not isinstance(interval, list) or len(interval) != 2:
        raise CertificateError("missing isolating interval")
    lower, upper = (_fraction(value) for value in interval)
    if lower >= upper:
        raise CertificateError("invalid isolating interval")
    lo = sp.Rational(lower.numerator, lower.denominator)
    hi = sp.Rational(upper.numerator, upper.denominator)
    if polynomial.eval(lo) == 0 or polynomial.eval(hi) == 0:
        raise CertificateError("isolating interval has a root endpoint")
    if polynomial.count_roots(lo, hi) != 1:
        raise CertificateError("interval does not isolate one real root")
    return field


def verify_embedded_certificate(record: object) -> bool:
    """Check only the graph, field, distinctness, and edge distances exactly."""
    if not isinstance(record, dict) or record.get("verdict") != "embedded":
        raise CertificateError("record is not an embedded verdict")
    code = record.get("g6")
    if not isinstance(code, str):
        raise CertificateError("missing graph6 string")
    n, edges = parse_graph6(code)
    witness = record.get("witness")
    if not isinstance(witness, dict):
        raise CertificateError("missing embedded witness")
    field = _validate_real_field(witness.get("field"))
    raw_coordinates = witness.get("coordinates")
    if not isinstance(raw_coordinates, list) or len(raw_coordinates) != n:
        raise CertificateError("coordinate count does not equal graph order")
    coordinates = []
    for raw in raw_coordinates:
        if not isinstance(raw, list) or len(raw) != 2:
            raise CertificateError("each coordinate must be an [x,y] pair")
        coordinates.append((field.element(raw[0]), field.element(raw[1])))
    for i in range(n):
        for j in range(i):
            dx = field.sub(coordinates[i][0], coordinates[j][0])
            dy = field.sub(coordinates[i][1], coordinates[j][1])
            if field.is_zero(dx) and field.is_zero(dy):
                raise CertificateError(f"vertices {j} and {i} collide")
    for u, v in edges:
        dx = field.sub(coordinates[u][0], coordinates[v][0])
        dy = field.sub(coordinates[u][1], coordinates[v][1])
        squared = field.add(field.mul(dx, dx), field.mul(dy, dy))
        if squared != field.one:
            raise CertificateError(f"edge {(u, v)} does not have squared distance one")
    return True


__all__ = ["CertificateError", "NumberField", "parse_graph6", "verify_embedded_certificate"]
