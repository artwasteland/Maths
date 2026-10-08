"""Vendored AMP refutation core. See VENDOR.md for provenance and changes."""
from __future__ import annotations
import os
os.environ["SYMPY_GROUND_TYPES"] = "python"
import collections
import itertools
import random
import sys
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence
import networkx as nx
import sympy as sp
from sympy.polys.matrices import DomainMatrix
ROOT3 = sp.sqrt(3)

def parse_graph6(code):
    graph = nx.from_graph6_bytes(code.encode("ascii"))
    return len(graph), graph.edges()

@dataclass(frozen=True)
class Graph:
    n: int
    edges: frozenset[tuple[int, int]]

    @classmethod
    def from_graph6(cls, code: str) -> "Graph":
        n, edges = parse_graph6(code)
        return cls(n, frozenset(normal_edge(edge) for edge in edges))

    @classmethod
    def from_edges(cls, n: int, edges: Iterable[Sequence[int]]) -> "Graph":
        return cls(n, frozenset(normal_edge(edge) for edge in edges))

    def with_edge(self, edge: Sequence[int]) -> "Graph":
        return Graph(self.n, self.edges | {normal_edge(edge)})

    def nonedges(self) -> Iterable[tuple[int, int]]:
        for v in range(self.n):
            for u in range(v):
                if (u, v) not in self.edges:
                    yield (u, v)

    def record(self) -> dict:
        return {"n": self.n, "edges": [list(edge) for edge in sorted(self.edges)]}

    def networkx(self) -> nx.Graph:
        result = nx.Graph()
        result.add_nodes_from(range(self.n))
        result.add_edges_from(self.edges)
        return result


def normal_edge(edge: Sequence[int]) -> tuple[int, int]:
    if len(edge) != 2:
        raise ValueError("edge must have two endpoints")
    u, v = int(edge[0]), int(edge[1])
    if u == v:
        raise ValueError("loops are not supported")
    return (u, v) if u < v else (v, u)


def difference_row(n: int, edge: Sequence[int]) -> tuple[sp.Expr, ...]:
    u, v = edge
    row = [sp.Integer(0)] * n
    row[u] = sp.Integer(1)
    row[v] = sp.Integer(-1)
    return tuple(row)


def normalize_exact(value: sp.Expr) -> sp.Expr:
    return sp.cancel(sp.expand_complex(value))


@lru_cache(maxsize=200000)
def exact_zero(value: sp.Expr) -> bool:
    if value == 0 or value.is_zero is True:
        return True
    value = normalize_exact(value)
    return value == 0 or value.is_zero is True


def exact_one(value: sp.Expr) -> bool:
    return exact_zero(value - 1)


@lru_cache(maxsize=200000)
def modulus_squared(value: sp.Expr) -> sp.Expr:
    return normalize_exact(sp.conjugate(value) * value)


def canonical_matrix(rows: Iterable[Sequence[sp.Expr]], n: int) -> sp.Matrix:
    rows = [list(row) for row in rows]
    if not rows:
        return sp.zeros(0, n)
    reduced, _ = sp.Matrix(rows).rref(simplify=False)
    nonzero = []
    for i in range(reduced.rows):
        row = [normalize_exact(value) for value in reduced.row(i)]
        if any(not exact_zero(value) for value in row):
            nonzero.append(row)
    return sp.Matrix(nonzero) if nonzero else sp.zeros(0, n)


def exact_nullspace(matrix: sp.Matrix) -> list[sp.Matrix]:
    """Compute a column-basis kernel using exact algebraic-domain elimination."""
    if matrix.rows == 0:
        return [sp.eye(matrix.cols).col(i) for i in range(matrix.cols)]
    domain_matrix = DomainMatrix.from_Matrix(matrix, fmt="dense", extension=True)
    if not domain_matrix.domain.is_Field:
        domain_matrix = domain_matrix.to_field()
    rows = domain_matrix.nullspace().to_Matrix()
    return [rows.row(i).T for i in range(rows.rows)]


def four_cycle_rows(graph: Graph) -> tuple[list[tuple[int, int, int, int]], list[tuple[sp.Expr, ...]]]:
    cycles: list[tuple[int, int, int, int]] = []
    rows: list[tuple[sp.Expr, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for vertices in itertools.combinations(range(graph.n), 4):
        a, b, c, d = vertices
        for left, right in (((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))):
            u, v = left
            x, y = right
            required = {(min(p, q), max(p, q)) for p in left for q in right}
            if not required <= graph.edges:
                continue
            row = [0] * graph.n
            row[u] += 1
            row[v] += 1
            row[x] -= 1
            row[y] -= 1
            first = next(value for value in row if value)
            if first < 0:
                row = [-value for value in row]
            key = tuple(row)
            if key in seen:
                continue
            seen.add(key)
            cycles.append((u, x, v, y))
            rows.append(tuple(sp.Integer(value) for value in row))
    return cycles, rows


def serialize_internal_matrix(matrix: sp.Matrix) -> list[list[str]]:
    """Serialize a search matrix for the private, pre-certificate proof tree."""
    return [[sp.sstr(sp.simplify(matrix[i, j])) for j in range(matrix.cols)] for i in range(matrix.rows)]


def _rational_string(value: sp.Expr) -> str:
    value = sp.Rational(value)
    return str(value.p) if value.q == 1 else f"{value.p}/{value.q}"


def _rational_json(value: sp.Expr) -> int | str:
    """Use the checker's canonical integer-or-rational JSON representation."""
    value = sp.Rational(value)
    return int(value.p) if value.q == 1 else f"{value.p}/{value.q}"


def _power_coefficients(value: sp.Expr, theta: sp.AlgebraicNumber) -> list[int | str]:
    converted = sp.to_number_field(value, theta)
    degree = theta.minpoly.degree()
    descending = list(converted.coeffs())
    descending = [sp.Rational(0)] * (degree - len(descending)) + descending
    increasing = list(reversed(descending))
    while len(increasing) > 1 and increasing[-1] == 0:
        increasing.pop()
    return [_rational_json(coefficient) for coefficient in increasing]



def restricted(row: Sequence[sp.Expr], kernel: Sequence[sp.Matrix]) -> tuple[sp.Expr, ...]:
    return tuple(normalize_exact(sum(row[i] * vector[i] for i in range(len(row)))) for vector in kernel)


def proportional(left: Sequence[sp.Expr], right: Sequence[sp.Expr]) -> sp.Expr | None:
    pivot = next((i for i, value in enumerate(right) if not exact_zero(value)), None)
    if pivot is None:
        return None
    ratio = normalize_exact(left[pivot] / right[pivot])
    if all(exact_zero(a - ratio * b) for a, b in zip(left, right)):
        return ratio
    return None


def matrix_with_row(matrix: sp.Matrix, row: Sequence[sp.Expr]) -> sp.Matrix:
    if len(row) != matrix.cols:
        raise ValueError("constraint row has the wrong width")
    return matrix.col_join(sp.Matrix([list(row)]))


def state_node(graph: Graph, matrix: sp.Matrix, move: dict, children: list[dict] | None = None) -> dict:
    result = {"graph": graph.record(), "constraints": serialize_internal_matrix(matrix), "move": move}
    if children is not None:
        result["children"] = children
    return result


def _internal_exact(value: object) -> sp.Expr:
    """Parse a private-tree scalar without admitting floating-point values."""
    if isinstance(value, sp.Expr):
        result = value
    elif isinstance(value, str):
        result = sp.sympify(value, locals={"I": sp.I, "sqrt": sp.sqrt})
    else:
        result = sp.sympify(value)
    if result.has(sp.Float):
        raise ValueError("floating-point value in exact proof tree")
    return normalize_exact(result)


def _real_imag(value: object) -> tuple[sp.Expr, sp.Expr]:
    exact = _internal_exact(value)
    real = sp.simplify(sp.re(exact))
    imag = sp.simplify(sp.im(exact))
    if real.has(sp.re, sp.im) or imag.has(sp.re, sp.im):
        raise ValueError(f"could not prove proof scalar algebraic: {exact}")
    return real, imag


def _proof_scalars(node: dict) -> list[sp.Expr]:
    """Collect every real algebraic value needed by a checker proof."""
    result: list[sp.Expr] = []
    for row in node["constraints"]:
        for value in row:
            result.extend(_real_imag(value))
    move = node["move"]
    if move["kind"] in ("L1b", "L2"):
        result.extend(_real_imag(move["ratio"]))
    elif move["kind"] in ("L1c", "L3"):
        for value in move["relation"]:
            result.extend(_real_imag(value))
        if move["kind"] == "L3":
            discriminant = _internal_exact(move["discriminant"])
            d = sp.sqrt(discriminant)
            real, imag = _real_imag(d)
            if not exact_zero(imag):
                raise ValueError("L3 discriminant does not have a real square root")
            result.append(real)
    for child in node.get("children", []):
        result.extend(_proof_scalars(child))
    return result


@dataclass(frozen=True)
class CertificateField:
    """A checker-schema real field and power-basis element encoder."""

    theta: sp.AlgebraicNumber | None
    spec: dict

    @classmethod
    def containing(cls, values: Sequence[sp.Expr]) -> "CertificateField":
        algebraic = []
        for value in values:
            value = sp.simplify(value)
            if value.is_rational:
                continue
            if value.is_real is not True or value.is_algebraic is not True:
                raise ValueError(f"proof value is not certified real algebraic: {value}")
            algebraic.append(value)
        if not algebraic:
            return cls(None, {"minpoly": [0, 1], "interval": [-1, 1]})

        theta = sp.to_number_field(algebraic)
        intervals = sp.Poly(theta.minpoly).intervals(eps=sp.Rational(1, 10**8))
        approximate = sp.N(theta.root, 100)
        chosen = None
        for candidate, multiplicity in intervals:
            lower, upper = candidate
            if multiplicity == 1 and lower < approximate < upper:
                chosen = candidate
                break
        if chosen is None:
            raise ValueError("could not isolate the proof field primitive element")
        polynomial = list(reversed(theta.minpoly.all_coeffs()))
        spec = {
            "minpoly": [_rational_json(value) for value in polynomial],
            "interval": [_rational_json(chosen[0]), _rational_json(chosen[1])],
        }
        return cls(theta, spec)

    def real(self, value: object) -> list[int | str]:
        real, imag = _real_imag(value)
        if not exact_zero(imag):
            raise ValueError(f"expected a real field element, got {value}")
        if self.theta is None:
            if real.is_rational is not True:
                raise ValueError(f"non-rational value in rational proof field: {real}")
            return [_rational_json(real)]
        return _power_coefficients(real, self.theta)

    def complex(self, value: object) -> object:
        real, imag = _real_imag(value)
        encoded_real = self.real(real)
        if exact_zero(imag):
            return encoded_real
        return {"re": encoded_real, "im": self.real(imag)}


def _checker_tree(node: dict, field: CertificateField) -> dict:
    """Convert one private reduction node to the binding checker schema."""
    move = node["move"]
    kind = move["kind"]
    if kind == "L1a":
        checked_move = {"kind": kind, "pair": move["collision"]}
    elif kind == "L1b":
        checked_move = {
            "kind": kind,
            "edges": move["edges"],
            "omega": field.complex(move["ratio"]),
        }
    elif kind == "L2":
        checked_move = {
            "kind": kind,
            "edges": [move["reference_edge"], move["forced_edge"]],
            "omega": field.complex(move["ratio"]),
        }
    elif kind in ("L1c", "L3"):
        discriminant = _internal_exact(move["discriminant"])
        checked_move = {
            "kind": kind,
            "edges": move["edges"],
            "coefficients": [field.complex(value) for value in move["relation"]],
        }
        if kind == "L3":
            checked_move["d"] = field.real(sp.sqrt(discriminant))
    else:
        raise ValueError(f"cannot serialize private move {kind}")
    return {
        "edges": node["graph"]["edges"],
        "A": [[field.complex(value) for value in row] for row in node["constraints"]],
        "move": checked_move,
        "children": [_checker_tree(child, field) for child in node.get("children", [])],
    }


def refutation_certificate(private_root: dict) -> dict:
    """Drop private L0 and package its child in the binding witness schema."""
    if private_root["move"].get("kind") != "L0" or len(private_root.get("children", [])) != 1:
        raise ValueError("private refutation root is not L0 with one child")
    root = private_root["children"][0]
    field = CertificateField.containing(_proof_scalars(root))
    return {"field": field.spec, "tree": _checker_tree(root, field)}


@dataclass
class SearchTrace:
    enabled: bool = False
    states_visited: int = 0
    max_depth: int = 0
    moves: collections.Counter[str] | None = None
    stops: collections.Counter[str] | None = None
    l3_calls: int = 0
    l3_triples_tested: int = 0
    l3_dependent_triples: int = 0
    l3_negative_discriminants: int = 0
    l3_redundant_splits: int = 0
    l1a_pairs_tested: int = 0
    l1b_pairs_tested: int = 0
    l2_pairs_tested: int = 0
    embedding_trials: int = 0
    embedding_constraints: int = 0

    def __post_init__(self) -> None:
        self.moves = collections.Counter()
        self.stops = collections.Counter()

    def event(self, message: str) -> None:
        if self.enabled:
            print(f"TRACE {message}", file=sys.stderr)


@dataclass
class SearchBudget:
    remaining_states: int
    tries: int
    rng: random.Random
    trace: SearchTrace


def pair_restrictions(graph: Graph, kernel: Sequence[sp.Matrix]):
    return {
        pair: restricted(difference_row(graph.n, pair), kernel)
        for pair in itertools.combinations(range(graph.n), 2)
    }


@dataclass(frozen=True)
class RestrictionClasses:
    projections: dict[tuple[int, int], tuple[tuple[object, ...], sp.Expr] | None]
    domain_images: dict[tuple[int, int], tuple[object, ...]]
    domain: object


def classify_restrictions(
    restrictions: dict[tuple[int, int], tuple[sp.Expr, ...]],
) -> RestrictionClasses:
    """Canonicalize every nonzero displacement image up to exact scale."""
    pairs = list(restrictions)
    images = [restrictions[pair] for pair in pairs]
    width = len(images[0]) if images else 0
    if width == 0:
        return RestrictionClasses(
            {pair: None for pair in pairs},
            {pair: () for pair in pairs},
            sp.QQ,
        )
    conjugate_images = [
        [normalize_exact(sp.conjugate(value)) for value in image]
        for image in images
    ]
    matrix = DomainMatrix.from_Matrix(
        sp.Matrix([*images, *conjugate_images]),
        fmt="dense",
        extension=True,
    ).to_field()
    dense = matrix.to_list()
    zero = matrix.domain.zero
    projections: dict[tuple[int, int], tuple[tuple[object, ...], sp.Expr] | None] = {}
    domain_images: dict[tuple[int, int], tuple[object, ...]] = {}
    for row_index, (pair, image) in enumerate(zip(pairs, images)):
        domain_image = tuple(dense[row_index][column] for column in range(width))
        domain_images[pair] = domain_image
        pivot_index = next((i for i, value in enumerate(domain_image) if value != zero), None)
        if pivot_index is None:
            projections[pair] = None
            continue
        domain_pivot = domain_image[pivot_index]
        projections[pair] = (
            tuple(value / domain_pivot for value in domain_image),
            image[pivot_index],
        )
    return RestrictionClasses(projections, domain_images, matrix.domain)


def projective_restrictions(
    restrictions: dict[tuple[int, int], tuple[sp.Expr, ...]],
) -> dict[tuple[int, int], tuple[tuple[object, ...], sp.Expr] | None]:
    return classify_restrictions(restrictions).projections


def find_l1(
    graph: Graph,
    matrix: sp.Matrix,
    kernel: Sequence[sp.Matrix],
    restrictions: dict[tuple[int, int], tuple[sp.Expr, ...]] | None = None,
    projections: dict[tuple[int, int], tuple[tuple[object, ...], sp.Expr] | None] | None = None,
    trace: SearchTrace | None = None,
):
    if restrictions is None:
        restrictions = pair_restrictions(graph, kernel)
    if projections is None:
        projections = projective_restrictions(restrictions)
    for pair in itertools.combinations(range(graph.n), 2):
        if trace is not None:
            trace.l1a_pairs_tested += 1
        row = difference_row(graph.n, pair)
        if projections[pair] is None:
            return {
                "kind": "L1a",
                "collision": list(pair),
                "difference_row": [sp.sstr(value) for value in row],
            }
    edges = sorted(graph.edges)
    for first, second in itertools.combinations(edges, 2):
        if trace is not None:
            trace.l1b_pairs_tested += 1
        left = projections[first]
        right = projections[second]
        if left is None or right is None or left[0] != right[0]:
            continue
        left_norm = modulus_squared(left[1])
        right_norm = modulus_squared(right[1])
        if not exact_zero(left_norm - right_norm):
            ratio = normalize_exact(left[1] / right[1])
            norm = modulus_squared(ratio)
            return {
                "kind": "L1b",
                "edges": [list(first), list(second)],
                "ratio": sp.sstr(ratio),
                "modulus_squared": sp.sstr(norm),
            }
    return None


def find_l2(
    graph: Graph,
    kernel: Sequence[sp.Matrix],
    restrictions: dict[tuple[int, int], tuple[sp.Expr, ...]] | None = None,
    projections: dict[tuple[int, int], tuple[tuple[object, ...], sp.Expr] | None] | None = None,
    trace: SearchTrace | None = None,
):
    if restrictions is None:
        restrictions = pair_restrictions(graph, kernel)
    if projections is None:
        projections = projective_restrictions(restrictions)
    edge_images = [(edge, projections[edge]) for edge in sorted(graph.edges)]
    for nonedge in graph.nonedges():
        target = projections[nonedge]
        for edge, source in edge_images:
            if trace is not None:
                trace.l2_pairs_tested += 1
            if source is None or target is None or source[0] != target[0]:
                continue
            if exact_zero(modulus_squared(source[1]) - modulus_squared(target[1])):
                ratio = normalize_exact(source[1] / target[1])
                return {
                    "kind": "L2",
                    "reference_edge": list(edge),
                    "forced_edge": list(nonedge),
                    "ratio": sp.sstr(ratio),
                    "modulus_squared": "1",
                }
    return None


def _all_nonzero_relation(basis: Sequence[sp.Matrix]) -> sp.Matrix | None:
    for vector in basis:
        if all(not exact_zero(value) for value in vector):
            return vector
    for coefficients in itertools.product((-2, -1, 1, 2), repeat=len(basis)):
        vector = sum((coefficient * basis[i] for i, coefficient in enumerate(coefficients)), sp.zeros(3, 1))
        if all(not exact_zero(value) for value in vector):
            return vector
    return None


def dependent_edge_relation(images: Sequence[Sequence[sp.Expr]]) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Return an all-nonzero left-kernel vector for three edge images."""
    width = len(images[0])
    for p, q in itertools.combinations(range(width), 2):
        a = normalize_exact(images[1][p] * images[2][q] - images[2][p] * images[1][q])
        b = normalize_exact(images[2][p] * images[0][q] - images[0][p] * images[2][q])
        c = normalize_exact(images[0][p] * images[1][q] - images[1][p] * images[0][q])
        if all(exact_zero(value) for value in (a, b, c)):
            continue
        if any(exact_zero(value) for value in (a, b, c)):
            return None
        if all(exact_zero(a * images[0][j] + b * images[1][j] + c * images[2][j]) for j in range(width)):
            return a, b, c
        return None
    first = proportional(images[1], images[0])
    second = proportional(images[2], images[0])
    if first is None or second is None:
        return None
    b = sp.Integer(1)
    c = sp.Integer(1)
    a = normalize_exact(-first - second)
    if exact_zero(a):
        c = sp.Integer(2)
        a = normalize_exact(-first - 2 * second)
    return a, b, c


def rowspace_signature(rows: Sequence[Sequence[sp.Expr]]) -> tuple[int, tuple[tuple[sp.Expr, ...], ...]]:
    """Return an exact reduced-row-echelon signature for one or two rows."""
    reduced = [list(row) for row in rows]
    if not reduced:
        return 0, ()
    width = len(reduced[0])
    rank = 0
    for column in range(width):
        pivot = next(
            (index for index in range(rank, len(reduced)) if not exact_zero(reduced[index][column])),
            None,
        )
        if pivot is None:
            continue
        reduced[rank], reduced[pivot] = reduced[pivot], reduced[rank]
        pivot_value = reduced[rank][column]
        reduced[rank] = [normalize_exact(value / pivot_value) for value in reduced[rank]]
        for index in range(len(reduced)):
            if index == rank or exact_zero(reduced[index][column]):
                continue
            factor = reduced[index][column]
            reduced[index] = [
                normalize_exact(value - factor * base)
                for value, base in zip(reduced[index], reduced[rank])
            ]
        rank += 1
        if rank == len(reduced):
            break
    signature = tuple(tuple(normalize_exact(value) for value in reduced[index]) for index in range(rank))
    return rank, signature


def domain_dependent_relation(
    indices: tuple[int, int, int],
    domain_rows: Sequence[Sequence[object]],
    domain: object,
) -> tuple[object, object, object] | None:
    """Recover a canonical all-nonzero relation in one exact number field."""
    i, j, k = indices
    x, y, z = domain_rows[i], domain_rows[j], domain_rows[k]
    width = len(x)
    coefficients = None
    for p, q in itertools.combinations(range(width), 2):
        a = y[p] * z[q] - z[p] * y[q]
        b = z[p] * x[q] - x[p] * z[q]
        c = x[p] * y[q] - y[p] * x[q]
        if a == domain.zero and b == domain.zero and c == domain.zero:
            continue
        if a == domain.zero or b == domain.zero or c == domain.zero:
            return None
        coefficients = [a, b, c]
        break
    if coefficients is None:
        pivot = next((p for p, value in enumerate(x) if value != domain.zero), None)
        if pivot is None:
            return None
        first = y[pivot] / x[pivot]
        second = z[pivot] / x[pivot]
        a = -first - second
        b = domain.one
        c = domain.one
        if a == domain.zero:
            c = domain.convert(2)
            a = -first - c * second
        coefficients = [a, b, c]
    scale = coefficients[0]
    coefficients = [value / scale for value in coefficients]
    return tuple(coefficients)


def numeric_dependence_score(
    indices: tuple[int, int, int],
    rows: Sequence[Sequence[complex]],
) -> float:
    """Heuristic only: smaller means a triple should be exactly tested sooner."""
    x, y, z = (rows[index] for index in indices)
    width = len(x)
    score = 0.0
    for p, q, r in itertools.combinations(range(width), 3):
        determinant = (
            x[p] * (y[q] * z[r] - y[r] * z[q])
            - x[q] * (y[p] * z[r] - y[r] * z[p])
            + x[r] * (y[p] * z[q] - y[q] * z[p])
        )
        score = max(score, abs(determinant))
    return score


def find_l3(
    graph: Graph,
    matrix: sp.Matrix,
    kernel: Sequence[sp.Matrix],
    restrictions: dict[tuple[int, int], tuple[sp.Expr, ...]] | None = None,
    trace: SearchTrace | None = None,
    classes: RestrictionClasses | None = None,
    excluded: frozenset[tuple[tuple[int, int], ...]] = frozenset(),
):
    if restrictions is None:
        restrictions = pair_restrictions(graph, kernel)
    edge_data = [
        (edge, difference_row(graph.n, edge), restrictions[edge])
        for edge in sorted(graph.edges)
    ]
    if trace is not None:
        trace.l3_calls += 1

    # Pairwise projective classes handle the rank-one cases.  Otherwise a
    # triple is dependent precisely when all of its 3-by-3 minors vanish.
    # Cache raw pair wedges so the exhaustive O(m^3) scan uses exact domain
    # multiplication and equality, with no repeated symbolic row reduction.
    if classes is None:
        classes = classify_restrictions(restrictions)
    domain_rows = [classes.domain_images[item[0]] for item in edge_data]
    if not domain_rows:
        return None
    width = len(domain_rows[0])
    zero = classes.domain.zero
    pair_wedges: dict[tuple[int, int], dict[tuple[int, int], object]] = {}
    conjugates: dict[object, object] = {}
    reported_negative = False

    def pair_wedge(first: int, second: int):
        key = (first, second) if first < second else (second, first)
        if key not in pair_wedges:
            left, right = domain_rows[key[0]], domain_rows[key[1]]
            pair_wedges[key] = {
                (p, q): left[p] * right[q] - left[q] * right[p]
                for p, q in itertools.combinations(range(width), 2)
            }
        return pair_wedges[key]

    def domain_conjugate(value: object):
        if value not in conjugates:
            expression = normalize_exact(sp.conjugate(classes.domain.to_sympy(value)))
            conjugates[value] = classes.domain.from_sympy(expression)
        return conjugates[value]

    numeric_rows = []
    for item in edge_data:
        row = [complex(sp.N(value, 20)) for value in item[2]]
        scale = max((abs(value) for value in row), default=0.0) or 1.0
        numeric_rows.append(tuple(value / scale for value in row))
    ordered_triples = list(itertools.combinations(range(len(edge_data)), 3))

    def is_graph_triangle(indices: tuple[int, int, int]) -> bool:
        vertices = {
            vertex
            for index in indices
            for vertex in edge_data[index][0]
        }
        return len(vertices) == 3

    ordered_triples.sort(
        key=lambda indices: (
            0 if is_graph_triangle(indices) else 1,
            0 if numeric_dependence_score(indices, numeric_rows) < 1e-10 else 1,
            indices,
        )
    )
    for tested, indices in enumerate(ordered_triples):
        if trace is not None:
            trace.l3_triples_tested += 1
            if tested and tested % 2000 == 0:
                trace.event(
                    f"L3_progress local_triples={tested} total_triples={trace.l3_triples_tested} "
                    f"dependent={trace.l3_dependent_triples} redundant={trace.l3_redundant_splits}"
                )
        edge_key = tuple(edge_data[index][0] for index in indices)
        if edge_key in excluded:
            continue
        i, j, k = indices
        projective = [classes.projections[edge_data[index][0]] for index in indices]
        assert all(item is not None for item in projective)
        signatures = [item[0] for item in projective if item is not None]
        # If all three images are already projectively equal, L1b has proved
        # that their forced ratios have unit modulus.  L3 would then reproduce
        # the current state in one child and an impossible state in the other,
        # so it cannot strengthen the surviving branch.  If exactly two
        # images agree, no relation with all coefficients nonzero exists.
        if len(set(signatures)) != 3:
            continue
        wedge = pair_wedge(i, j)
        last = domain_rows[k]
        dependent = all(
            wedge[(p, q)] * last[r] - wedge[(p, r)] * last[q] + wedge[(q, r)] * last[p] == zero
            for p, q, r in itertools.combinations(range(width), 3)
        )
        if not dependent:
            continue
        if trace is not None:
            trace.l3_dependent_triples += 1
        triple = tuple(edge_data[index] for index in indices)
        images = [item[2] for item in triple]
        domain_relation = domain_dependent_relation(indices, domain_rows, classes.domain)
        if domain_relation is None:
            continue
        domain_a, domain_b, domain_c = domain_relation
        aa = domain_a * domain_conjugate(domain_a)
        bb = domain_b * domain_conjugate(domain_b)
        cc = domain_c * domain_conjugate(domain_c)
        q = aa + bb - cc
        domain_discriminant = classes.domain.convert(4) * aa * bb - q * q
        discriminant = normalize_exact(classes.domain.to_sympy(domain_discriminant))
        if discriminant.is_nonnegative is not True:
            if trace is not None:
                trace.l3_negative_discriminants += 1
                if not reported_negative:
                    trace.event(
                        f"L3_negative edges={[list(item[0]) for item in triple]} "
                        f"relation={[sp.sstr(classes.domain.to_sympy(value)) for value in domain_relation]} "
                        f"discriminant={sp.sstr(discriminant)}"
                    )
                    reported_negative = True
            if discriminant.is_negative is True:
                relation = tuple(
                    normalize_exact(classes.domain.to_sympy(value))
                    for value in domain_relation
                )
                candidate = ({
                    "kind": "L1c",
                    "edges": [list(item[0]) for item in triple],
                    "relation": [sp.sstr(value) for value in relation],
                    "discriminant": sp.sstr(discriminant),
                }, [])
                return candidate
            continue
        imaginary_root = sp.I * sp.sqrt(discriminant)
        relation = tuple(
            normalize_exact(classes.domain.to_sympy(value))
            for value in domain_relation
        )
        a, b, _ = relation
        aa_expr = normalize_exact(classes.domain.to_sympy(aa))
        bb_expr = normalize_exact(classes.domain.to_sympy(bb))
        cc_expr = normalize_exact(classes.domain.to_sympy(cc))
        branch_rows = []
        for sign in (1, -1):
            factor = sp.simplify((aa_expr + bb_expr - cc_expr + sign * imaginary_root) * a)
            other = sp.simplify(2 * aa_expr * b)
            row = tuple(
                sp.simplify(factor * triple[0][1][i] + other * triple[1][1][i])
                for i in range(graph.n)
            )
            branch_rows.append(row)
        if len(branch_rows) != 2:
            continue
        candidate = ({
            "kind": "L3",
            "edges": [list(item[0]) for item in triple],
            "relation": [sp.sstr(value) for value in relation],
            "discriminant": sp.sstr(discriminant),
            "branch_rows": [[sp.sstr(value) for value in row] for row in branch_rows],
        }, branch_rows)
        return candidate
    return None

def random_kernel_embedding(graph, matrix, budget):
    # This producer searches only for refutations and never uses coordinates.
    return None

def reduce_state(
    graph: Graph,
    matrix: sp.Matrix,
    budget: SearchBudget,
    depth: int = 0,
    used_l3: frozenset[tuple[tuple[int, int], ...]] = frozenset(),
):
    if budget.remaining_states <= 0:
        budget.trace.stops["state_limit"] += 1
        budget.trace.event(f"stop depth={depth} reason=state_limit")
        return "unknown", None
    budget.remaining_states -= 1
    budget.trace.states_visited += 1
    budget.trace.max_depth = max(budget.trace.max_depth, depth)
    state_number = budget.trace.states_visited
    kernel = exact_nullspace(matrix)
    restrictions = pair_restrictions(graph, kernel)
    classes = classify_restrictions(restrictions)
    projections = classes.projections
    budget.trace.event(f"state={state_number} depth={depth} phase=L1 start")
    l1 = find_l1(graph, matrix, kernel, restrictions, projections, budget.trace)
    if l1 is not None:
        budget.trace.moves[l1["kind"]] += 1
        budget.trace.stops["contradiction"] += 1
        budget.trace.event(f"state={state_number} depth={depth} move={l1['kind']}")
        return "refuted", state_node(graph, matrix, l1)
    budget.trace.event(f"state={state_number} depth={depth} phase=L1 exhausted")
    budget.trace.event(f"state={state_number} depth={depth} phase=L2 start")
    l2 = find_l2(graph, kernel, restrictions, projections, budget.trace)
    if l2 is not None:
        budget.trace.moves["L2"] += 1
        budget.trace.event(
            f"state={state_number} depth={depth} move=L2 forced={l2['forced_edge']} reference={l2['reference_edge']}"
        )
        child_graph = graph.with_edge(l2["forced_edge"])
        _, rhombus_rows = four_cycle_rows(child_graph)
        child_matrix = canonical_matrix([*matrix.tolist(), *rhombus_rows], graph.n)
        verdict, payload = reduce_state(child_graph, child_matrix, budget, depth + 1, used_l3)
        if verdict == "refuted":
            l2["new_rhombus_rank"] = child_matrix.rank() - matrix.rank()
            return "refuted", state_node(graph, matrix, l2, [payload])
        return verdict, payload
    budget.trace.event(f"state={state_number} depth={depth} phase=L2 exhausted")
    budget.trace.event(f"state={state_number} depth={depth} phase=L3 start")
    negative_before = budget.trace.l3_negative_discriminants
    l3 = find_l3(
        graph,
        matrix,
        kernel,
        restrictions,
        trace=budget.trace,
        classes=classes,
        excluded=used_l3,
    )
    if l3 is not None:
        move, rows = l3
        budget.trace.moves[move["kind"]] += 1
        budget.trace.event(
            f"state={state_number} depth={depth} move={move['kind']} edges={move['edges']} "
            f"discriminant={move['discriminant']}"
        )
        if move["kind"] == "L1c":
            budget.trace.stops["contradiction"] += 1
            return "refuted", state_node(graph, matrix, move)
        children = []
        move_key = tuple(normal_edge(edge) for edge in move["edges"])
        child_used_l3 = used_l3 | {move_key}
        for row in rows:
            verdict, payload = reduce_state(
                graph,
                matrix_with_row(matrix, row),
                budget,
                depth + 1,
                child_used_l3,
            )
            if verdict == "embedded":
                return verdict, payload
            children.append(payload if verdict == "refuted" else None)
        if any(child is None for child in children):
            return "unknown", None
        return "refuted", state_node(graph, matrix, move, children)
    budget.trace.event(f"state={state_number} depth={depth} phase=L3 exhausted")
    if budget.trace.l3_negative_discriminants > negative_before:
        budget.trace.stops["negative_heron_unrepresentable"] += 1
        budget.trace.event(
            f"state={state_number} depth={depth} stop=negative_heron_unrepresentable"
        )
        return "unknown", None
    budget.trace.event(f"state={state_number} depth={depth} phase=embedding start tries={budget.tries}")
    coordinates = random_kernel_embedding(graph, matrix, budget)
    if coordinates is not None:
        budget.trace.stops["embedding"] += 1
        budget.trace.event(f"state={state_number} depth={depth} stop=embedding")
        return "embedded", coordinates
    budget.trace.stops["no_move_no_embedding"] += 1
    budget.trace.event(f"state={state_number} depth={depth} stop=no_move_no_embedding")
    return "unknown", None
