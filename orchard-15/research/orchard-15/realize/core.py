"""Exact projective construction and certificate primitives for stage 3."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path
from typing import Any, Iterable

import sympy as sp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chiro"))
from chirosat import PTS  # noqa: E402


def determinant(left, middle, right):
    matrix = sp.Matrix.hstack(sp.Matrix(left), sp.Matrix(middle), sp.Matrix(right))
    return sp.factor(sp.expand(matrix.det()))


def cross(left, right):
    return tuple(sp.expand(value) for value in sp.Matrix(left).cross(sp.Matrix(right)))


def frame_is_valid(pts: PTS, frame: Iterable[int]) -> bool:
    frame_tuple = tuple(frame)
    blocks = set(pts.blocks)
    return len(frame_tuple) == 4 and len(set(frame_tuple)) == 4 and not any(
        tuple(sorted(triple)) in blocks for triple in itertools.combinations(frame_tuple, 3)
    )


def construction_cost(pts: PTS, frame: tuple[int, ...]):
    blocks = set(pts.blocks)
    placed = set(frame)
    steps = []
    parameters = 0
    while len(placed) < pts.v:
        candidates = []
        for point in set(range(pts.v)) - placed:
            lines = sorted(
                tuple(sorted(set(block) - {point}))
                for block in blocks
                if point in block and set(block) - {point} <= placed
            )
            candidates.append((-len(lines), point, lines))
        _negative_count, point, lines = min(candidates)
        if len(lines) >= 2:
            kind, used = "intersection", lines[:2]
        elif len(lines) == 1:
            kind, used = "line", lines
            parameters += 1
        else:
            kind, used = "free", []
            parameters += 2
        steps.append({"point": point, "kind": kind, "lines": [list(pair) for pair in used]})
        placed.add(point)
    return parameters, steps


def choose_construction(pts: PTS) -> dict[str, Any]:
    """Choose the lexicographically first lowest-parameter greedy construction."""
    best = None
    for frame in itertools.combinations(range(pts.v), 4):
        if not frame_is_valid(pts, frame):
            continue
        parameters, steps = construction_cost(pts, frame)
        item = (parameters, frame, steps)
        if best is None or (parameters, frame) < (best[0], best[1]):
            best = item
    if best is None:
        raise ValueError("PTS has no four-point projective frame")
    parameters, frame, steps = best
    return {"frame": list(frame), "steps": steps, "parameter_count": parameters}


def build_system(pts: PTS, construction: dict[str, Any]) -> dict[str, Any]:
    """Rebuild all equations and inequations from the PTS and a construction."""
    frame = tuple(construction.get("frame", []))
    if not frame_is_valid(pts, frame):
        raise ValueError("certificate frame is not four points in general position")
    coordinates: dict[int, tuple[sp.Expr, sp.Expr, sp.Expr]] = {
        frame[0]: (sp.Integer(1), sp.Integer(0), sp.Integer(0)),
        frame[1]: (sp.Integer(0), sp.Integer(1), sp.Integer(0)),
        frame[2]: (sp.Integer(0), sp.Integer(0), sp.Integer(1)),
        frame[3]: (sp.Integer(1), sp.Integer(1), sp.Integer(1)),
    }
    blocks = set(pts.blocks)
    parameters: list[sp.Symbol] = []
    normalized_steps = []
    for raw in construction.get("steps", []):
        point = raw.get("point")
        kind = raw.get("kind")
        lines = [tuple(pair) for pair in raw.get("lines", [])]
        if not isinstance(point, int) or not 0 <= point < pts.v or point in coordinates:
            raise ValueError("construction repeats or mislabels a point")
        for pair in lines:
            if len(pair) != 2 or pair[0] == pair[1] or any(p not in coordinates for p in pair):
                raise ValueError("construction line does not use two distinct known points")
            if tuple(sorted((point, *pair))) not in blocks:
                raise ValueError("construction line is not a PTS block")
        if kind == "intersection":
            if len(lines) != 2 or set(lines[0]) == set(lines[1]):
                raise ValueError("intersection step needs two distinct known block lines")
            first = cross(coordinates[lines[0][0]], coordinates[lines[0][1]])
            second = cross(coordinates[lines[1][0]], coordinates[lines[1][1]])
            coordinates[point] = cross(first, second)
        elif kind == "line":
            if len(lines) != 1:
                raise ValueError("line step needs one known block line")
            parameter = sp.Symbol(f"t{len(parameters)}")
            parameters.append(parameter)
            left, right = (coordinates[p] for p in lines[0])
            coordinates[point] = tuple(sp.expand(left[i] + parameter * right[i]) for i in range(3))
        elif kind == "free":
            if lines:
                raise ValueError("free step cannot name a line")
            first = sp.Symbol(f"t{len(parameters)}")
            second = sp.Symbol(f"t{len(parameters) + 1}")
            parameters.extend((first, second))
            coordinates[point] = (sp.Integer(1), first, second)
        else:
            raise ValueError("unknown construction step kind")
        normalized_steps.append({"point": point, "kind": kind, "lines": [list(p) for p in lines]})
    if set(coordinates) != set(range(pts.v)):
        raise ValueError("construction does not place every PTS point exactly once")

    block_equations = []
    for block in pts.blocks:
        value = determinant(*(coordinates[point] for point in block))
        if value != 0:
            block_equations.append(value)
    nondegeneracies = []
    for triple in itertools.combinations(range(pts.v), 3):
        if triple not in blocks:
            nondegeneracies.append(determinant(*(coordinates[point] for point in triple)))
    return {
        "construction": {
            "frame": list(frame),
            "steps": normalized_steps,
            "parameter_count": len(parameters),
        },
        "parameters": parameters,
        "coordinates": coordinates,
        "block_equations": block_equations,
        "nondegeneracies": nondegeneracies,
        "has_free_step": any(step["kind"] == "free" for step in normalized_steps),
    }


def normalized_polynomial(expression, variables):
    polynomial = sp.Poly(expression, *variables, domain=sp.QQ)
    if polynomial.is_zero:
        return sp.Integer(0)
    return polynomial.monic().as_expr()


def unique_nonconstant(expressions, variables):
    found: dict[str, sp.Expr] = {}
    for expression in expressions:
        polynomial = sp.Poly(expression, *variables, domain=sp.QQ)
        if polynomial.is_zero:
            return [sp.Integer(0)]
        if polynomial.total_degree() == 0:
            continue
        normalized = polynomial.monic().as_expr()
        found[sp.srepr(normalized)] = normalized
    return [found[key] for key in sorted(found)]


def saturated_groebner(system: dict[str, Any]) -> dict[str, Any]:
    """Compute I:(product g)^infinity exactly, reducing the product en route."""
    variables = system["parameters"]
    equations = unique_nonconstant(system["block_equations"], variables) if variables else []
    constant_contradiction = any(
        not expression.free_symbols and expression != 0 for expression in system["block_equations"]
    )
    nondegeneracies = unique_nonconstant(system["nondegeneracies"], variables) if variables else []
    if constant_contradiction or sp.Integer(0) in nondegeneracies:
        return {
            "is_unit": True,
            "basis": [sp.Integer(1)],
            "equations": equations,
            "nondegeneracies": nondegeneracies,
            "product_remainder": sp.Integer(0),
            "reason": "constant equation or identically zero required non-degeneracy",
        }
    if not variables:
        return {
            "is_unit": False,
            "basis": [],
            "equations": [],
            "nondegeneracies": [],
            "product_remainder": sp.Integer(1),
            "reason": "zero-dimensional parameter-free construction is consistent",
        }
    ideal_basis = sp.groebner(equations or [sp.Integer(0)], *variables, order="grevlex", domain=sp.QQ)
    if ideal_basis.is_zero_dimensional and list(ideal_basis) == [1] or list(ideal_basis) == [sp.Integer(1)]:
        return {
            "is_unit": True,
            "basis": [sp.Integer(1)],
            "equations": equations,
            "nondegeneracies": nondegeneracies,
            "product_remainder": sp.Integer(0),
            "reason": "block ideal is the unit ideal",
        }
    remainder = sp.Integer(1)
    for inequation in nondegeneracies:
        remainder = ideal_basis.reduce(sp.expand(remainder * inequation))[1]
        if remainder == 0:
            return {
                "is_unit": True,
                "basis": [sp.Integer(1)],
                "equations": equations,
                "nondegeneracies": nondegeneracies,
                "product_remainder": sp.Integer(0),
                "reason": "the full non-degeneracy product reduces to zero modulo the block ideal",
            }
    inverse = sp.Symbol("saturation_inverse")
    extended = sp.groebner(
        equations + [sp.expand(inverse * remainder - 1)],
        inverse,
        *variables,
        order="grevlex",
        domain=sp.QQ,
    )
    basis = list(extended)
    is_unit = basis == [1] or basis == [sp.Integer(1)]
    return {
        "is_unit": is_unit,
        "basis": basis,
        "equations": equations,
        "nondegeneracies": nondegeneracies,
        "product_remainder": remainder,
        "reason": "Rabinowitsch saturation Groebner basis",
    }


def rational_assignment(system: dict[str, Any]):
    variables = system["parameters"]
    values = [sp.Integer(2), sp.Integer(-1), sp.Integer(3), sp.Rational(1, 2),
              sp.Integer(-2), sp.Rational(2, 3), sp.Rational(-1, 2), sp.Integer(1), sp.Integer(0)]
    if len(variables) > 4:
        return None
    for candidate in itertools.product(values, repeat=len(variables)):
        substitution = dict(zip(variables, candidate))
        if any(sp.expand(eq.subs(substitution)) != 0 for eq in system["block_equations"]):
            continue
        if any(sp.expand(g.subs(substitution)) == 0 for g in system["nondegeneracies"]):
            continue
        return substitution
    return None


def rational_witness(system: dict[str, Any], assignment) -> dict[str, Any]:
    points = []
    for point in range(len(system["coordinates"])):
        points.append([str(sp.cancel(value.subs(assignment))) for value in system["coordinates"][point]])
    return {"field": {"type": "Q"}, "points": points}


def nf_reduce(expression, generator, modulus: sp.Poly):
    numerator, denominator = sp.cancel(expression).as_numer_denom()
    num = sp.Poly(numerator, generator, domain=sp.QQ)
    den = sp.Poly(denominator, generator, domain=sp.QQ)
    return (num * sp.invert(den, modulus)).rem(modulus).as_expr()


def pegg_witness(pts: PTS) -> dict[str, Any] | None:
    expected = tuple(triple for triple in itertools.combinations(range(15), 3) if sum(triple) % 15 == 0)
    if pts.v != 15 or pts.blocks != expected:
        return None
    alpha = sp.Symbol("alpha")
    modulus = sp.Poly(alpha**8 - 28 * alpha**6 + 134 * alpha**4 - 92 * alpha**2 + 1,
                      alpha, domain=sp.QQ)
    cotangents = [None, alpha]
    for _k in range(2, 15):
        previous = cotangents[-1]
        cotangents.append(nf_reduce((previous * alpha - 1) / (previous + alpha), alpha, modulus))
    coordinates = [(sp.Integer(0), sp.Integer(1), sp.Integer(0))]
    coordinates.extend(
        (nf_reduce(value**2 + 1, alpha, modulus),
         nf_reduce(value**3 + value, alpha, modulus), sp.Integer(1))
        for value in cotangents[1:]
    )
    return {
        "field": {
            "type": "number-field",
            "generator": "alpha",
            "minimal_polynomial": str(modulus.as_expr()),
            "isolating_interval": ["47/10", "24/5"],
        },
        "points": [[str(value) for value in point] for point in coordinates],
        "source": "15-torsion on y^2=x^2(x-1), alpha=cot(pi/15)",
    }


def verify_real_witness(pts: PTS, witness: dict[str, Any]) -> tuple[bool, str]:
    field = witness.get("field", {})
    raw_points = witness.get("points")
    if not isinstance(raw_points, list) or len(raw_points) != pts.v:
        return False, "wrong number of coordinate triples"
    if field.get("type") == "Q":
        try:
            points = [tuple(sp.Rational(value) for value in point) for point in raw_points]
        except (TypeError, ValueError, ZeroDivisionError):
            return False, "a purported rational coordinate is invalid"
        reduce = sp.cancel
    elif field.get("type") == "number-field":
        if field.get("generator") != "alpha":
            return False, "only the declared generator alpha is accepted"
        alpha = sp.Symbol("alpha")
        try:
            minimal = sp.Poly(sp.sympify(field["minimal_polynomial"], locals={"alpha": alpha}),
                              alpha, domain=sp.QQ)
            left, right = (sp.Rational(value) for value in field["isolating_interval"])
        except (KeyError, TypeError, ValueError, sp.SympifyError):
            return False, "invalid number-field declaration"
        if minimal.degree() < 1 or not minimal.is_irreducible or minimal.count_roots(left, right) != 1:
            return False, "minimal polynomial or real isolating interval is invalid"
        try:
            points = []
            for point in raw_points:
                if len(point) != 3:
                    raise ValueError
                parsed = tuple(sp.sympify(value, locals={"alpha": alpha}) for value in point)
                if any(value.free_symbols - {alpha} for value in parsed):
                    raise ValueError
                points.append(tuple(nf_reduce(value, alpha, minimal) for value in parsed))
        except (TypeError, ValueError, ZeroDivisionError, sp.SympifyError, sp.polys.polyerrors.NotInvertible):
            return False, "coordinate is not an element of the declared number field"
        reduce = lambda value: nf_reduce(value, alpha, minimal)
    else:
        return False, "unsupported or missing exact field"
    if any(len(point) != 3 or all(reduce(value) == 0 for value in point) for point in points):
        return False, "a projective point is the zero vector"
    for left, right in itertools.combinations(range(pts.v), 2):
        if all(reduce(value) == 0 for value in cross(points[left], points[right])):
            return False, f"points {left} and {right} coincide"
    blocks = set(pts.blocks)
    for triple in itertools.combinations(range(pts.v), 3):
        zero = reduce(determinant(*(points[point] for point in triple))) == 0
        if zero != (triple in blocks):
            return False, f"determinant classification is wrong at triple {triple}"
    return True, f"all {sp.binomial(pts.v, 3)} determinants and all point pairs verified exactly"
