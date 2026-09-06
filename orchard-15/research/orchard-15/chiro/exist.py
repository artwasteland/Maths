#!/usr/bin/env python3
"""Existence SAT for orchard partial Steiner triple systems (CONTRACT Section 9).

One CNF asks: is there a rank-3 chirotope on v elements whose zero set is a
PTS(v, b)?  Variables, for every increasing triple T:

    B(T)             T is a block
    pos(T), neg(T)   chi(T) = +1, chi(T) = -1 (neither means chi(T) = 0)

together with the auxiliary variables of ``chirosat.build_base_encoding``
(one nonzero selector per triple and six product-sign variables per
Grassmann-Pluecker relation).  Clauses:

  1. the chirotope base of chirosat.py: at most one sign per triple, the
     nonzero selector, and the rank-3 three-term Grassmann-Pluecker relations
     for every 5-subset and every pivot (axioms B0-B2 of Bjoerner, Las Vergnas,
     Sturmfels, White and Ziegler, Oriented Matroids, Section 3.5; see the
     docstring of chirosat.py);
  2. the tie B(T) <-> (not pos(T) and not neg(T)), and not B(T) -> pos xor neg;
  3. pair-disjointness: every pair lies in at most one block;
  4. exactly b blocks (pysat sequential counter);
  5. implied per-point degree bounds: at most floor((v-1)/2) blocks through
     every point, and exactly that many when the leave degrees are forced
     equal (2 e = v * parity);
  6. the symmetry break of REPORT-EXIST.md: point 0 has the minimum leave
     degree r2min (derived from v and b), its row is {0,1,2}, {0,3,4}, ...
     followed by the leave pairs {0, x}; v sign anchors kill the whole
     reorientation group; optionally a lex-leader constraint for each
     generator of the stabiliser of point 0's row (sound, not complete);
  7. cube-and-conquer mode: the row of point 1 (a second minimum-leave point)
     is fixed to one representative of each orbit under the stabiliser of
     point 0's row that fixes point 1. At depth 2 the row of point 2 is then
     fixed up to the stabiliser of the first row. The item-6 lex-leader is
     replaced inside each cube by one under the stabiliser of its fixed rows.

SAT models are checked directly (exact zero set, every GP relation, pair
disjointness, block count, the canonical row, the leave) and printed as a
contract PTS line plus a chirotope string.  UNSAT answers from the standalone
solvers carry a DRAT proof that is accepted only after drat-trim verifies it.
The pysat backend gives no proof and says so in its output.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pysat.card import CardEnc, EncType
from pysat.solvers import Cadical153

from chirosat import (
    BatchEncoding,
    Encoding,
    PTS,
    build_base_encoding,
    file_sha256,
    find_executable,
    parse_solver_model,
    run_drat_trim,
    verify_witness,
    witness_from_model,
    write_clauses,
)


Triple = tuple[int, int, int]
Pair = tuple[int, int]
Clause = list[int]
Permutation = tuple[int, ...]


class ExistenceError(ValueError):
    """The requested parameters do not support the contracted reduction."""


# ---------------------------------------------------------------------------
# The combinatorial reduction (CONTRACT Section 1), derived from v and b.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reduction:
    v: int
    b: int
    pairs: int
    leave_edges: int
    kelly_moser: int
    leave_parity: int
    min_leave_degree: int
    min_leave_points: int
    row_blocks: tuple[Triple, ...]
    row_leave_neighbours: tuple[int, ...]
    max_blocks_per_point: int
    all_degrees_minimum: bool


def derive_reduction(v: int, b: int) -> Reduction:
    """Derive the leave facts and the canonical row of point 0 from v and b.

    e = C(v,2) - 3b pairs are not covered by blocks.  Kelly-Moser gives at
    least ceil(3v/7) ordinary lines.  A line on four or more points would
    consume at least six uncovered pairs and leave fewer than ceil(3v/7) for
    ordinary lines, so no such line exists and the structure is a PTS whose
    leave has exactly e edges (Lemma 1 of REPORT-EXIST.md).

    At each point x, 2 r3(x) + r2(x) = v - 1, so every leave degree has the
    parity of v - 1.  If every degree exceeded that parity it would be at
    least parity + 2 and the degree sum 2e would be at least v (parity + 2);
    in every contracted case 2e is smaller, so the minimum leave degree is
    exactly the parity (Lemma 2).  The number of points of minimum degree is
    at least v - (e - v parity / 2) (Lemma 5).
    """
    if v < 5:
        raise ExistenceError("v must be at least 5")
    if b < 0:
        raise ExistenceError("b must be nonnegative")
    pairs = math.comb(v, 2)
    leave_edges = pairs - 3 * b
    if leave_edges < 0:
        raise ExistenceError("three times b exceeds the number of pairs")
    kelly_moser = -(-3 * v // 7)
    if leave_edges < kelly_moser:
        raise ExistenceError(
            f"leave has {leave_edges} pairs, below Kelly-Moser {kelly_moser}: "
            "no arrangement at all, nothing to encode"
        )
    if leave_edges - math.comb(4, 2) >= kelly_moser:
        raise ExistenceError(
            "Kelly-Moser does not exclude a line on four or more points; "
            "the PTS reduction of CONTRACT Section 1 does not apply"
        )
    parity = (v - 1) % 2
    degree_sum = 2 * leave_edges
    if degree_sum >= v * (parity + 2):
        raise ExistenceError(
            "degree average does not force the minimum leave degree"
        )
    minimum = parity
    row_size = (v - 1 - minimum) // 2
    row_blocks = tuple((0, 2 * i + 1, 2 * i + 2) for i in range(row_size))
    row_leave_neighbours = tuple(range(1 + 2 * row_size, v))
    if len(row_leave_neighbours) != minimum:
        raise AssertionError("internal canonical-row arithmetic failed")
    excess_points = (degree_sum - v * parity) // 2
    return Reduction(
        v=v,
        b=b,
        pairs=pairs,
        leave_edges=leave_edges,
        kelly_moser=kelly_moser,
        leave_parity=parity,
        min_leave_degree=minimum,
        min_leave_points=v - excess_points,
        row_blocks=row_blocks,
        row_leave_neighbours=row_leave_neighbours,
        max_blocks_per_point=row_size,
        all_degrees_minimum=(degree_sum == v * parity),
    )


# ---------------------------------------------------------------------------
# Permutation helpers for the symmetry break.
# ---------------------------------------------------------------------------


def apply_to_triple(permutation: Permutation, triple: Triple) -> Triple:
    return tuple(sorted(permutation[point] for point in triple))  # type: ignore[return-value]


def transposition(v: int, left: int, right: int) -> Permutation:
    permutation = list(range(v))
    permutation[left], permutation[right] = right, left
    return tuple(permutation)


def pair_exchange(v: int, first: Pair, second: Pair) -> Permutation:
    permutation = list(range(v))
    permutation[first[0]], permutation[second[0]] = second[0], first[0]
    permutation[first[1]], permutation[second[1]] = second[1], first[1]
    return tuple(permutation)


def row_stabiliser_generators(reduction: Reduction, fix_point_one: bool) -> list[Permutation]:
    """Generators of the stabiliser of point 0's canonical row.

    The stabiliser is (Z2 wr S_k) x S_r: swap the two points inside any row
    pair, permute the row pairs, permute the leave neighbours of point 0.
    With ``fix_point_one`` the pair {1,2} is fixed pointwise (Lemma 6).
    """
    v = reduction.v
    row_pairs = [(block[1], block[2]) for block in reduction.row_blocks]
    if fix_point_one:
        row_pairs = row_pairs[1:]
    generators: list[Permutation] = []
    for left, right in row_pairs:
        generators.append(transposition(v, left, right))
    for index in range(len(row_pairs) - 1):
        generators.append(pair_exchange(v, row_pairs[index], row_pairs[index + 1]))
    leave = reduction.row_leave_neighbours
    for index in range(len(leave) - 1):
        generators.append(transposition(v, leave[index], leave[index + 1]))
    for permutation in generators:
        if permutation[0] != 0:
            raise AssertionError("row stabiliser generator moves point 0")
        if fix_point_one and (permutation[1] != 1 or permutation[2] != 2):
            raise AssertionError("row stabiliser generator moves point 1 or 2")
        image = {apply_to_triple(permutation, block) for block in reduction.row_blocks}
        if image != set(reduction.row_blocks):
            raise AssertionError("row stabiliser generator does not preserve the row")
        image_leave = {permutation[x] for x in reduction.row_leave_neighbours}
        if image_leave != set(reduction.row_leave_neighbours):
            raise AssertionError("row stabiliser generator does not preserve the leave of 0")
    return generators


# ---------------------------------------------------------------------------
# Cubes: the row of point 1 up to the stabiliser of point 0's row.
# ---------------------------------------------------------------------------


Config = tuple[tuple[Pair, ...], tuple[int, ...]]


def enumerate_row1_configurations(reduction: Reduction) -> list[Config]:
    """All possible rows of point 1, given the canonical row of point 0.

    Point 1 lies on {0,1,2}.  Its other blocks {1,a,b} use pairs {a,b} of
    points 3..v-1 that are not row-0 pairs (those are already covered), and
    its leave partners are the r2min remaining points.  Nothing else is
    assumed here; impossible rows are left for the solver to refute.
    """
    v = reduction.v
    others = list(range(3, v))
    forbidden = {(block[1], block[2]) for block in reduction.row_blocks}
    need_blocks = reduction.max_blocks_per_point - 1
    need_leave = reduction.min_leave_degree
    if len(others) != 2 * need_blocks + need_leave:
        raise AssertionError("row-1 arithmetic does not add up")
    results: list[Config] = []

    def extend(remaining: list[int], pairs: list[Pair], leaves: list[int]) -> None:
        if not remaining:
            if len(pairs) == need_blocks and len(leaves) == need_leave:
                results.append((tuple(sorted(pairs)), tuple(sorted(leaves))))
            return
        first, rest = remaining[0], remaining[1:]
        if len(leaves) < need_leave:
            extend(rest, pairs, leaves + [first])
        if len(pairs) < need_blocks:
            for index, other in enumerate(rest):
                if (first, other) in forbidden:
                    continue
                extend(rest[:index] + rest[index + 1 :], pairs + [(first, other)], leaves)

    extend(others, [], [])
    return sorted(set(results))


def apply_to_config(permutation: Permutation, config: Config) -> Config:
    pairs, leaves = config
    image_pairs = tuple(sorted(tuple(sorted((permutation[a], permutation[b]))) for a, b in pairs))
    image_leaves = tuple(sorted(permutation[x] for x in leaves))
    return image_pairs, image_leaves  # type: ignore[return-value]


@dataclass(frozen=True)
class CubeSet:
    configurations: list[Config]
    representatives: list[Config]
    orbit_sizes: list[int]
    generators: list[Permutation]


def enumerate_cubes(reduction: Reduction, drop_one: bool = False) -> CubeSet:
    """Orbit representatives of point 1's rows, with a coverage self-check.

    Orbits are computed by union-find under the generators of Lemma 6.  The
    self-check re-expands every representative under the generators and
    requires that the expansions are disjoint, that each generator maps every
    configuration to a configuration (so the group preserves the constraints),
    and that the union is the whole configuration set.  ``drop_one`` is the
    mutation control: it removes one representative so the check must fail.
    """
    # Lemma 5 gives at least min_leave_points points of minimum leave degree;
    # besides point 0 and its r2min leave neighbours, at least one must lie
    # among the row points 1..2k, and the stabiliser moves it to point 1.
    if reduction.min_leave_points < 2 + reduction.min_leave_degree:
        raise ExistenceError("no second minimum-leave point is forced among the row points")
    configurations = enumerate_row1_configurations(reduction)
    index = {config: i for i, config in enumerate(configurations)}
    generators = row_stabiliser_generators(reduction, fix_point_one=True)
    parent = list(range(len(configurations)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, config in enumerate(configurations):
        for permutation in generators:
            image = apply_to_config(permutation, config)
            if image not in index:
                raise AssertionError("a generator maps a row-1 configuration outside the set")
            a, b = find(i), find(index[image])
            if a != b:
                parent[max(a, b)] = min(a, b)
    orbits: dict[int, list[Config]] = {}
    for i, config in enumerate(configurations):
        orbits.setdefault(find(i), []).append(config)
    representatives = sorted(min(members) for members in orbits.values())
    if drop_one:
        representatives = representatives[1:]

    # Coverage self-check, independent of the union-find above.
    covered: set[Config] = set()
    orbit_sizes: list[int] = []
    for representative in representatives:
        seen = {representative}
        frontier = [representative]
        while frontier:
            config = frontier.pop()
            for permutation in generators:
                image = apply_to_config(permutation, config)
                if image not in seen:
                    seen.add(image)
                    frontier.append(image)
        if covered & seen:
            raise AssertionError("cube orbits overlap")
        covered |= seen
        orbit_sizes.append(len(seen))
    if covered != set(configurations):
        raise AssertionError(
            f"cube set does not cover every row-1 configuration: "
            f"{len(covered)} of {len(configurations)} covered"
        )
    return CubeSet(configurations, representatives, orbit_sizes, generators)


Cube = tuple[Config, ...]  # row configurations of points 1, 2, ... in order


def cube_units(reduction: Reduction, cube: Cube) -> dict[Triple, bool]:
    """Block values for every triple containing a cubed point (1, 2, ...)."""
    values: dict[Triple, bool] = {}
    for depth, config in enumerate(cube):
        point = depth + 1
        blocks = {tuple(sorted((point, a, b))) for a, b in config[0]}
        for triple in itertools.combinations(range(reduction.v), 3):
            if point in triple and triple not in values:
                values[triple] = triple in blocks or triple == (0, 1, 2)  # type: ignore[assignment]
    return values


def group_closure(generators: list[Permutation], v: int) -> list[Permutation]:
    """All elements of the group generated (BFS; the groups here are small)."""
    identity = tuple(range(v))
    seen = {identity}
    frontier = [identity]
    while frontier:
        element = frontier.pop()
        for generator in generators:
            product = tuple(generator[element[i]] for i in range(v))
            if product not in seen:
                seen.add(product)
                frontier.append(product)
    return sorted(seen)


def enumerate_row2_configurations(reduction: Reduction, first: Config) -> list[Config]:
    """All possible rows of point 2 given the rows of points 0 and 1.

    Point 2 lies on {0,1,2}.  Its further blocks {2,a,b} use pairs of 3..v-1
    not covered by a row-0 or row-1 block.  Its leave degree d is any value
    with the parity p, d >= p, and d <= 2e - (v-1) p (the others are at
    least p); when all degrees are forced to p only d = p occurs.
    """
    v = reduction.v
    others = list(range(3, v))
    covered = {(block[1], block[2]) for block in reduction.row_blocks}
    covered |= set(first[0])
    p = reduction.min_leave_degree
    if reduction.all_degrees_minimum:
        degrees = [p]
    else:
        top = min(v - 3, 2 * reduction.leave_edges - (v - 1) * p)
        degrees = list(range(p, top + 1, 2))
    results: set[Config] = set()
    for d in degrees:
        need_blocks = (v - 1 - d) // 2 - 1
        need_leave = d
        if need_blocks < 0 or len(others) != 2 * need_blocks + need_leave:
            continue

        def extend(remaining: list[int], pairs: list[Pair], leaves: list[int]) -> None:
            if not remaining:
                if len(pairs) == need_blocks and len(leaves) == need_leave:
                    results.add((tuple(sorted(pairs)), tuple(sorted(leaves))))
                return
            head, rest = remaining[0], remaining[1:]
            if len(leaves) < need_leave:
                extend(rest, pairs, leaves + [head])
            if len(pairs) < need_blocks:
                for index, other in enumerate(rest):
                    if (head, other) in covered:
                        continue
                    extend(rest[:index] + rest[index + 1 :], pairs + [(head, other)], leaves)

        extend(others, [], [])
    return sorted(results)


def orbit_representatives(
    configurations: list[Config],
    group: list[Permutation],
    *,
    drop_one: bool = False,
) -> tuple[list[Config], list[int]]:
    """Orbit minima under an explicit group, with the coverage self-check.

    ``drop_one`` is the depth-2 mutation control.  It removes the first orbit
    minimum before the independent coverage pass, which must then fail.
    """
    index = set(configurations)
    representatives: list[Config] = []
    sizes: list[int] = []
    scanned: set[Config] = set()
    for config in configurations:
        if config in scanned:
            continue
        orbit = set()
        for permutation in group:
            image = apply_to_config(permutation, config)
            if image not in index:
                raise AssertionError("a group element maps a configuration outside the set")
            orbit.add(image)
        if config != min(orbit):
            raise AssertionError("orbit scan reached a non-minimal element first")
        if scanned & orbit:
            raise AssertionError("orbits overlap")
        scanned |= orbit
        representatives.append(config)
        sizes.append(len(orbit))
    if scanned != index:
        raise AssertionError("orbit scan does not cover the configuration set")
    if drop_one:
        representatives = representatives[1:]
        sizes = sizes[1:]

    # Re-expand the retained representatives independently of the scan above.
    covered: set[Config] = set()
    for representative in representatives:
        orbit = set()
        for permutation in group:
            image = apply_to_config(permutation, representative)
            if image not in index:
                raise AssertionError("a group element maps a configuration outside the set")
            orbit.add(image)
        if covered & orbit:
            raise AssertionError("depth-2 cube orbits overlap")
        covered |= orbit
    if covered != index:
        raise AssertionError(
            f"depth-2 cube set does not cover every row-2 configuration: "
            f"{len(covered)} of {len(configurations)} covered"
        )
    return representatives, sizes


def refine_cube(
    reduction: Reduction,
    first: Config,
    group_one: list[Permutation],
    *,
    drop_one: bool = False,
) -> tuple[list[Cube], list[int], int]:
    """Depth-2 cubes under a level-1 cube: rows of point 2 up to G2 = Stab_G1(row 1).

    Completeness (Lemma 7'): point 2's row is one of the
    enumerated configurations; G2 preserves rows 0 and 1 and the covered
    pairs, so it acts on those configurations, and relabelling by the group
    element that sends the row to its orbit minimum keeps rows 0 and 1.
    """
    group_two = [g for g in group_one if apply_to_config(g, first) == first]
    configurations = enumerate_row2_configurations(reduction, first)
    representatives, sizes = orbit_representatives(configurations, group_two, drop_one=drop_one)
    return [(first, second) for second in representatives], sizes, len(group_two)


# ---------------------------------------------------------------------------
# The CNF.
# ---------------------------------------------------------------------------


@dataclass
class ExistenceEncoding:
    reduction: Reduction
    chiro: BatchEncoding
    block_variables: dict[Triple, int]
    clauses: list[Clause]
    nvars: int
    exact_b: bool
    cube: Cube | None
    counts: dict[str, int]


def gf2_rank(vectors: list[int]) -> int:
    """Rank over GF(2) of bit-mask vectors by elimination on the highest bit."""
    basis: dict[int, int] = {}
    for vector in vectors:
        while vector:
            high = vector.bit_length() - 1
            if high not in basis:
                basis[high] = vector
                break
            vector ^= basis[high]
    return len(basis)


def sign_anchors(reduction: Reduction) -> list[Triple]:
    """v triples, never blocks under the canonical row, independent over GF(2).

    Reorienting a set S of elements multiplies chi(T) by (-1)^|S and T| and
    preserves zeros and every GP relation; global negation is S = everything.
    The incidence vectors of these v triples are independent, so exactly one
    of the 2^v reorientations makes them all positive (Lemma 4).
    """
    v = reduction.v
    # The first v-1 of these span exactly the vectors whose coefficient on
    # point 0 equals the sum of those on points 1 and 2; (0,3,5) breaks that
    # relation and completes a basis.  Every anchor contains a pair covered by
    # a row block ({0,1},{0,2},{1,2} or {0,3}), so none can be a block.
    anchors = [(0, 1, 3), (0, 2, 3), (1, 2, 3), (0, 3, 5)] + [(0, 1, e) for e in range(4, v)]
    covered_by_row = {pair for block in reduction.row_blocks for pair in itertools.combinations(block, 2)}
    if (0, 3, 4) not in reduction.row_blocks or v < 6:
        raise ExistenceError("sign anchors need v >= 6 and the row block {0,3,4}")
    for triple in anchors:
        if not any(pair in covered_by_row for pair in itertools.combinations(triple, 2)):
            raise AssertionError(f"anchor {triple} could be a block")
        if triple in reduction.row_blocks:
            raise AssertionError(f"anchor {triple} is a row block")
    vectors = [sum(1 << point for point in triple) for triple in anchors]
    if len(anchors) != v or gf2_rank(vectors) != v:
        raise AssertionError("sign anchors are not a basis of the reorientation group")
    return anchors


def build_existence_encoding(
    v: int,
    b: int,
    *,
    drop_exact_b: bool = False,
    lex: bool = True,
    degree: bool = True,
    cube: Cube | None = None,
    cube_group: list[Permutation] | None = None,
) -> ExistenceEncoding:
    reduction = derive_reduction(v, b)
    chiro = build_base_encoding(v)
    clauses = [list(clause) for clause in chiro.clauses]
    counts: dict[str, int] = {"base_clauses": len(clauses)}
    top = chiro.nvars

    block_variables: dict[Triple, int] = {}
    for triple in chiro.triples:
        top += 1
        block_variables[triple] = top

    start = len(clauses)
    for triple in chiro.triples:
        block = block_variables[triple]
        positive = chiro.var(triple, 1)
        negative = chiro.var(triple, -1)
        clauses.extend(([-block, -positive], [-block, -negative], [block, positive, negative]))
    counts["tie_clauses"] = len(clauses) - start

    def through_pair(pair: Pair) -> list[int]:
        return [
            block_variables[tuple(sorted((*pair, other)))]  # type: ignore[index]
            for other in range(v)
            if other not in pair
        ]

    start = len(clauses)
    for pair in itertools.combinations(range(v), 2):
        for left, right in itertools.combinations(through_pair(pair), 2):
            clauses.append([-left, -right])
    counts["pair_clauses"] = len(clauses) - start

    start, start_top = len(clauses), top
    if not drop_exact_b:
        cardinality = CardEnc.equals(
            lits=list(block_variables.values()), bound=b, top_id=top, encoding=EncType.seqcounter
        )
        clauses.extend(cardinality.clauses)
        top = max(top, cardinality.nv)
    counts["cardinality_clauses"] = len(clauses) - start
    counts["cardinality_variables"] = top - start_top

    start, start_top = len(clauses), top
    if degree:
        bound = reduction.max_blocks_per_point
        for point in range(v):
            lits = [block_variables[t] for t in chiro.triples if point in t]
            if reduction.all_degrees_minimum and not drop_exact_b:
                card = CardEnc.equals(lits=lits, bound=bound, top_id=top, encoding=EncType.seqcounter)
            else:
                card = CardEnc.atmost(lits=lits, bound=bound, top_id=top, encoding=EncType.seqcounter)
            clauses.extend(card.clauses)
            top = max(top, card.nv)
    counts["degree_clauses"] = len(clauses) - start
    counts["degree_variables"] = top - start_top

    start = len(clauses)
    fixed_blocks = set(reduction.row_blocks)
    for triple in chiro.triples:
        if 0 in triple:
            literal = block_variables[triple]
            clauses.append([literal if triple in fixed_blocks else -literal])
    counts["row_units"] = len(clauses) - start
    start = len(clauses)
    for triple in sign_anchors(reduction):
        clauses.append([chiro.var(triple, 1)])
    counts["anchor_units"] = len(clauses) - start

    start = len(clauses)
    if cube is not None:
        for triple, value in cube_units(reduction, cube).items():
            literal = block_variables[triple]
            clauses.append([literal if value else -literal])
    counts["cube_units"] = len(clauses) - start

    start, start_top = len(clauses), top
    generators: list[Permutation] = []
    if lex and cube is None:
        generators = row_stabiliser_generators(reduction, fix_point_one=False)
    if cube is not None and cube_group:
        # Lex-leader under the stabiliser G2 of the cubed rows (every element
        # of it, since these groups are tiny).  G2 maps cube models to cube
        # models, so the orbit minimum argument of Lemma 8 applies inside the
        # cube. Each element is checked to fix the cube before use.
        identity = tuple(range(v))
        for permutation in cube_group:
            if permutation == identity:
                continue
            if any(apply_to_config(permutation, config) != config for config in cube):
                raise AssertionError("cube group element does not fix the cube")
            generators.append(permutation)
    for permutation in generators:
        # Lex-leader: block vector x (triples in lexicographic order) satisfies
        # x <= x composed with the permutation.  Positions where the two
        # variables coincide, or where both triples contain 0 (fixed by the
        # row units and permuted among themselves), are always equal and are
        # skipped. Sound by Lemma 7 or 7' (the orbit minimum satisfies it).
        top += 1
        prefix_equal = top
        clauses.append([prefix_equal])
        for triple in chiro.triples:
            image = apply_to_triple(permutation, triple)
            if image == triple or (0 in triple and 0 in image):
                continue
            left, right = block_variables[triple], block_variables[image]
            clauses.append([-prefix_equal, -left, right])
            top += 1
            next_equal = top
            clauses.extend(
                (
                    [-next_equal, prefix_equal],
                    [-next_equal, -left, right],
                    [-next_equal, left, -right],
                    [-prefix_equal, -left, -right, next_equal],
                    [-prefix_equal, left, right, next_equal],
                )
            )
            prefix_equal = next_equal
    counts["lex_generators"] = len(generators)
    counts["lex_clauses"] = len(clauses) - start
    counts["lex_variables"] = top - start_top

    return ExistenceEncoding(
        reduction=reduction,
        chiro=chiro,
        block_variables=block_variables,
        clauses=clauses,
        nvars=top,
        exact_b=not drop_exact_b,
        cube=cube,
        counts=counts,
    )


# ---------------------------------------------------------------------------
# Model checking.
# ---------------------------------------------------------------------------


def leave_summary(pts: PTS) -> dict[str, object]:
    covered = {pair for block in pts.blocks for pair in itertools.combinations(block, 2)}
    leave = [pair for pair in itertools.combinations(range(pts.v), 2) if pair not in covered]
    degrees = [0] * pts.v
    for a, b in leave:
        degrees[a] += 1
        degrees[b] += 1
    return {"edges": len(leave), "pairs": leave, "degrees": degrees}


def verify_model(encoding: ExistenceEncoding, true_vars: set[int]) -> tuple[PTS, str, dict[str, object]]:
    """Direct check of a SAT model: PTS shape, symmetry break, chirotope."""
    reduction = encoding.reduction
    blocks = tuple(t for t in encoding.chiro.triples if encoding.block_variables[t] in true_vars)
    pts = PTS(reduction.v, blocks)
    if encoding.exact_b and len(blocks) != reduction.b:
        raise RuntimeError(f"model has {len(blocks)} blocks, not {reduction.b}")
    seen: set[Pair] = set()
    for block in blocks:
        for pair in itertools.combinations(block, 2):
            if pair in seen:
                raise RuntimeError(f"model repeats pair {pair}")
            seen.add(pair)
    if {block for block in blocks if 0 in block} != set(reduction.row_blocks):
        raise RuntimeError("model violates the canonical row of point 0")
    if encoding.cube is not None:
        expected = cube_units(reduction, encoding.cube)
        actual = {t: t in set(blocks) for t in expected}
        if actual != expected:
            raise RuntimeError("model violates a row fixed by the cube")
    leave = leave_summary(pts)
    if encoding.exact_b:
        if leave["edges"] != reduction.leave_edges:
            raise RuntimeError("model leave has the wrong number of edges")
        degrees: list[int] = leave["degrees"]  # type: ignore[assignment]
        if any(d % 2 != reduction.leave_parity for d in degrees):
            raise RuntimeError("model leave has a degree of the wrong parity")
        if degrees[0] != reduction.min_leave_degree or min(degrees) != reduction.min_leave_degree:
            raise RuntimeError("point 0 does not have the minimum leave degree")
    lightweight = Encoding(
        pts=pts,
        triples=encoding.chiro.triples,
        index=encoding.chiro.index,
        clauses=[],
        gp_relations=encoding.chiro.gp_relations,
        gp_active_histogram=(0, 0, 0, 0),
    )
    witness = witness_from_model(lightweight, true_vars)
    verify_witness(lightweight, witness)
    return pts, witness, leave


# ---------------------------------------------------------------------------
# Known controls as phase hints (pysat backend only).
# ---------------------------------------------------------------------------


def canonical_row_copy(pts: PTS, reduction: Reduction, lex: bool) -> PTS:
    """Relabel a known PTS so a minimum-leave point is 0 with the canonical row.

    With ``lex`` the block vector is then descended under the stabiliser
    generators until it satisfies every generator lex-leader constraint.
    """
    covered = {pair for block in pts.blocks for pair in itertools.combinations(block, 2)}
    degrees = [
        sum(tuple(sorted((p, q))) not in covered for q in range(pts.v) if q != p)
        for p in range(pts.v)
    ]
    root = degrees.index(min(degrees))
    if degrees[root] != reduction.min_leave_degree:
        raise RuntimeError("known control has the wrong minimum leave degree")
    incident = sorted(block for block in pts.blocks if root in block)
    old_pairs = [tuple(p for p in block if p != root) for block in incident]
    old_leave = sorted(
        q for q in range(pts.v) if q != root and tuple(sorted((root, q))) not in covered
    )
    relabel = {root: 0}
    for old_pair, new_block in zip(old_pairs, reduction.row_blocks):
        relabel[old_pair[0]], relabel[old_pair[1]] = new_block[1], new_block[2]
    for old, new in zip(old_leave, reduction.row_leave_neighbours):
        relabel[old] = new
    if len(relabel) != pts.v:
        raise RuntimeError("known control row relabelling is incomplete")
    blocks = {tuple(sorted(relabel[p] for p in block)) for block in pts.blocks}
    if lex:
        triples = tuple(itertools.combinations(range(pts.v), 3))
        generators = row_stabiliser_generators(reduction, fix_point_one=False)
        while True:
            vector = tuple(t in blocks for t in triples)
            replacement = None
            for permutation in generators:
                image = {apply_to_triple(permutation, block) for block in blocks}
                if tuple(t in image for t in triples) < vector:
                    replacement = image
                    break
            if replacement is None:
                break
            blocks = replacement
    return PTS(pts.v, tuple(sorted(blocks)))  # type: ignore[arg-type]


def known_control(v: int, b: int) -> tuple[str, PTS] | None:
    if (v, b) == (14, 27):
        # BGS Theorem 10 incidence structure as reconstructed by the previous
        # builder (codex-3.log): 21 lines of the affine-like part plus 6.
        blocks: list[Triple] = []
        for left, right in itertools.combinations(range(7), 2):
            axis = (4 * (left + right + 1)) % 7
            blocks.append(tuple(sorted((left, right, 7 + axis))))  # type: ignore[arg-type]
        blocks.extend(((7, 8, 9), (7, 10, 11), (7, 12, 13), (8, 10, 12), (8, 11, 13), (9, 11, 12)))
        return "BGS-Theorem-10", PTS(14, tuple(sorted(blocks)))
    if (v, b) == (15, 31):
        from controls import PEGG_15_31

        return "Pegg-zero-sum-mod-15", PEGG_15_31
    if (v, b) == (16, 37):
        from controls import KUHNE_16_37

        return "Kuhne-et-al-16-37", KUHNE_16_37
    return None


# ---------------------------------------------------------------------------
# Solving.
# ---------------------------------------------------------------------------


def common_result(encoding: ExistenceEncoding, encode_seconds: float) -> dict[str, object]:
    reduction = encoding.reduction
    return {
        "v": reduction.v,
        "b": reduction.b,
        "leave_edges": reduction.leave_edges,
        "kelly_moser": reduction.kelly_moser,
        "min_leave_degree": reduction.min_leave_degree,
        "min_leave_points_at_least": reduction.min_leave_points,
        "row_blocks": [list(block) for block in reduction.row_blocks],
        "row_leave_neighbours": list(reduction.row_leave_neighbours),
        "max_blocks_per_point": reduction.max_blocks_per_point,
        "all_degrees_minimum": reduction.all_degrees_minimum,
        "variables": encoding.nvars,
        "clauses": len(encoding.clauses),
        "chiro_gp_relations": encoding.chiro.gp_relations,
        "counts": encoding.counts,
        "exact_b": encoding.exact_b,
        "cube_stabiliser_lex_elements": encoding.counts.get("lex_generators") if encoding.cube is not None else None,
        "cube": None if encoding.cube is None else [
            {"point": depth + 1, "blocks": [sorted((depth + 1, a, b)) for a, b in config[0]], "leave": list(config[1])}
            for depth, config in enumerate(encoding.cube)
        ],
        "encode_seconds": round(encode_seconds, 6),
    }


def sat_fields(encoding: ExistenceEncoding, true_vars: set[int]) -> dict[str, object]:
    started = time.perf_counter()
    pts, witness, leave = verify_model(encoding, true_vars)
    return {
        "verdict": "SAT",
        "pts": pts.line,
        "chirotope": witness,
        "leave_edges_found": leave["edges"],
        "leave_degrees": leave["degrees"],
        "leave_pairs": leave["pairs"],
        "check_seconds": round(time.perf_counter() - started, 6),
        "model_checked": True,
    }


def _pysat_child(connection, clauses: list[Clause], phases: list[int], assumptions: list[int]) -> None:
    """Child process: solve and send back (cube_answer, answer, model, stats)."""
    solver = Cadical153(bootstrap_with=clauses)
    try:
        if phases:
            solver.set_phases(phases)
        answer = solver.solve(assumptions=assumptions)
        cube_answer = answer if assumptions else None
        if assumptions and not answer:
            answer = solver.solve()
        model = solver.get_model() if answer else None
        connection.send((cube_answer, answer, model, solver.accum_stats()))
    finally:
        solver.delete()
        connection.close()


def solve_pysat(
    encoding: ExistenceEncoding,
    encode_seconds: float,
    timeout: float,
    phase_hint: bool,
    hint_cube: bool,
) -> dict[str, object]:
    """python-sat Cadical153 in a forked child, killed on timeout (Cadical153 has
    no interrupt in python-sat, so a timer thread cannot stop it).  No proof."""
    import multiprocessing

    total_started = time.perf_counter()
    hint_name = None
    phases: list[int] = []
    assumptions: list[int] = []
    if phase_hint or hint_cube:
        known = known_control(encoding.reduction.v, encoding.reduction.b)
        if known is None:
            raise ExistenceError("no known control PTS for this (v, b)")
        hint_name, source = known
        copy = canonical_row_copy(source, encoding.reduction, lex=encoding.counts["lex_generators"] > 0)
        hint_blocks = set(copy.blocks)
        literals = [var if triple in hint_blocks else -var for triple, var in encoding.block_variables.items()]
        if phase_hint:
            phases = literals
        if hint_cube:
            assumptions = literals
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_pysat_child, args=(child, encoding.clauses, phases, assumptions))
    solve_started = time.perf_counter()
    process.start()
    child.close()
    result = common_result(encoding, encode_seconds) | {
        "backend": "pysat-cadical153",
        "phase_hint": hint_name if phase_hint else None,
        "hint_cube": hint_name if hint_cube else None,
        "timeout_seconds": timeout,
    }
    if not parent.poll(timeout if timeout > 0 else None):
        process.kill()
        process.join()
        return result | {
            "verdict": "TIMEOUT",
            "solve_seconds": round(time.perf_counter() - solve_started, 6),
            "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
        }
    cube_answer, answer, model, stats = parent.recv()
    process.join()
    result |= {
        "hint_cube_satisfied": cube_answer,
        "solve_seconds": round(time.perf_counter() - solve_started, 6),
        "solver_stats": stats,
    }
    if answer:
        true_vars = {lit for lit in (model or []) if lit > 0}
        return result | sat_fields(encoding, true_vars) | {
            "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6)
        }
    return result | {
        "verdict": "UNSAT",
        "proof_verified": False,
        "note": "pysat backend gives no proof; rerun with --backend cadical for a DRAT certificate",
        "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
    }


def row_orbit_block_vectors(encoding: ExistenceEncoding, pts: PTS) -> list[tuple[bool, ...]]:
    """All canonical-row relabellings of one PTS that obey the encoded lex leaders."""
    reduction = encoding.reduction
    triples = encoding.chiro.triples
    triple_index = encoding.chiro.index
    highest_bit = len(triples) - 1
    blocks = set(pts.blocks)
    covered = {pair for block in blocks for pair in itertools.combinations(block, 2)}
    degrees = [
        sum(tuple(sorted((point, other))) not in covered for other in range(pts.v) if other != point)
        for point in range(pts.v)
    ]
    generators = row_stabiliser_generators(reduction, fix_point_one=False)
    if not encoding.counts["lex_generators"]:
        generators = []
    generator_image_bits = [
        [1 << (highest_bit - triple_index[apply_to_triple(permutation, triple)]) for triple in triples]
        for permutation in generators
    ]
    vectors: set[int] = set()
    target_pairs = [(block[1], block[2]) for block in reduction.row_blocks]
    for root, degree in enumerate(degrees):
        if degree != reduction.min_leave_degree:
            continue
        source_pairs = [tuple(point for point in block if point != root) for block in pts.blocks if root in block]
        source_leave = [
            point for point in range(pts.v)
            if point != root and tuple(sorted((root, point))) not in covered
        ]
        for ordered_pairs in itertools.permutations(source_pairs):
            for flips in itertools.product((False, True), repeat=len(source_pairs)):
                for ordered_leave in itertools.permutations(source_leave):
                    relabel = {root: 0}
                    for source, target, flip in zip(ordered_pairs, target_pairs, flips):
                        left, right = source[::-1] if flip else source
                        relabel[left], relabel[right] = target
                    relabel.update(zip(ordered_leave, reduction.row_leave_neighbours))
                    image = {tuple(sorted(relabel[point] for point in block)) for block in blocks}
                    indices = [triple_index[triple] for triple in image]
                    vector = sum(1 << (highest_bit - index) for index in indices)
                    if all(vector <= sum(bits[index] for index in indices) for bits in generator_image_bits):
                        vectors.add(vector)
    return [
        tuple(bool(vector & (1 << (highest_bit - index))) for index in range(len(triples)))
        for vector in sorted(vectors)
    ]


def _all_models_child(connection, encoding: ExistenceEncoding, output: Path) -> None:
    """Persistent incremental enumeration worker, isolated for hard timeout."""
    models = 0
    solver = Cadical153(bootstrap_with=encoding.clauses)
    try:
        with output.open("w", encoding="ascii") as handle:
            seen: set[tuple[bool, ...]] = set()
            while solver.solve():
                true_vars = {literal for literal in (solver.get_model() or []) if literal > 0}
                pts, _witness, _leave = verify_model(encoding, true_vars)
                for vector in row_orbit_block_vectors(encoding, pts):
                    if vector in seen:
                        continue
                    assumptions = [
                        variable if value else -variable
                        for variable, value in zip(encoding.block_variables.values(), vector)
                    ]
                    if not solver.solve(assumptions=assumptions):
                        raise RuntimeError("an isomorphic canonical-row copy unexpectedly failed SAT")
                    model_vars = {literal for literal in (solver.get_model() or []) if literal > 0}
                    copy, _copy_witness, _copy_leave = verify_model(encoding, model_vars)
                    if tuple(triple in set(copy.blocks) for triple in encoding.chiro.triples) != vector:
                        raise RuntimeError("assumption solve returned the wrong block assignment")
                    handle.write(copy.line + "\n")
                    handle.flush()
                    models += 1
                    seen.add(vector)
                    solver.add_clause([-literal for literal in assumptions])
                    if models % 500 == 0:
                        print(f"all-models: {models} block assignments", file=sys.stderr, flush=True)
        connection.send((models, solver.accum_stats()))
    finally:
        solver.delete()
        connection.close()


def enumerate_all_models(
    encoding: ExistenceEncoding,
    encode_seconds: float,
    output: Path,
    timeout: float,
) -> dict[str, object]:
    """Enumerate distinct labelled block vectors with one incremental solver.

    Chirotope signs are deliberately absent from the blocking clause: a PTS is
    written once even when it supports several chirotopes.  The existing row
    and lex constraints are sound but incomplete symmetry breaking, so the
    output can still contain isomorphic labelled PTSs; stage 3 canonicalises
    their coloured incidence graphs with nauty.
    """
    import multiprocessing

    total_started = time.perf_counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_all_models_child, args=(child, encoding, output))
    process.start()
    child.close()
    if not parent.poll(timeout if timeout > 0 else None):
        process.kill()
        process.join()
        models = sum(1 for line in output.read_text(encoding="ascii").splitlines() if line.strip())
        stats: dict[str, int] | None = None
        verdict = "TIMEOUT"
    else:
        try:
            models, stats = parent.recv()
        except EOFError as exc:
            process.join()
            raise RuntimeError(f"all-models worker exited with code {process.exitcode}") from exc
        process.join()
        verdict = "UNSAT"
    return common_result(encoding, encode_seconds) | {
        "backend": "pysat-cadical153-incremental",
        "verdict": verdict,
        "labelled_models": models,
        "output": str(output.resolve()),
        "proof_logged": False,
        "timeout_seconds": timeout,
        "solver_stats": stats,
        "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
    }


def parse_text_model(text: str, nvars: int) -> set[int]:
    values: list[int] = []
    status = None
    for line in text.splitlines():
        if line.startswith("s "):
            status = line[2:].strip()
        elif line.startswith("v "):
            values.extend(int(item) for item in line[2:].split() if item != "0")
    if status != "SATISFIABLE":
        raise RuntimeError(f"solver output has unexpected status {status!r}")
    assignment = {abs(value): value > 0 for value in values}
    missing = [var for var in range(1, nvars + 1) if var not in assignment]
    if missing:
        raise RuntimeError(f"solver model omits {len(missing)} variables")
    return {var for var, truth in assignment.items() if truth}


def corrupt_and_reject(checker: str, cnf: Path, proof: Path) -> dict[str, object]:
    """Mutation control: a truncated proof must be rejected by drat-trim."""
    corrupt = proof.with_suffix(proof.suffix + ".corrupt")
    data = proof.read_bytes()
    corrupt.write_bytes(data[: max(1, len(data) // 2)])
    started = time.perf_counter()
    process = subprocess.run(
        [checker, str(cnf), str(corrupt)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    seconds = time.perf_counter() - started
    rejected = process.returncode != 0 and "NOT VERIFIED" in process.stdout
    if not rejected:
        raise RuntimeError("corrupted DRAT proof was NOT rejected by drat-trim")
    return {
        "path": str(corrupt.resolve()),
        "checker_exit": process.returncode,
        "rejected": True,
        "check_seconds": round(seconds, 6),
    }


def solve_standalone(
    encoding: ExistenceEncoding,
    encode_seconds: float,
    artifact_dir: Path,
    backend: str,
    checker: str,
    timeout: float,
    corrupt_proof: bool,
    stem: str | None = None,
) -> dict[str, object]:
    total_started = time.perf_counter()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or f"exist-{encoding.reduction.v}-{encoding.reduction.b}"
    cnf = artifact_dir / f"{stem}.cnf"
    proof = artifact_dir / f"{stem}.{backend}.drat"
    model = artifact_dir / f"{stem}.{backend}.model"
    write_started = time.perf_counter()
    write_clauses(encoding.nvars, encoding.clauses, cnf)
    write_seconds = time.perf_counter() - write_started

    if backend == "cadical":
        executable = find_executable(None, ("/usr/bin/cadical", "cadical"))
        command = [executable, "--binary=false", "-q", "-w", str(model), str(cnf), str(proof)]
    elif backend == "kissat":
        executable = find_executable(None, ("~/tools/sat/kissat/build/kissat", "kissat"))
        command = [executable, "-q", str(cnf), str(proof)]
    else:
        raise ExistenceError(f"unsupported standalone backend {backend!r}")

    result = common_result(encoding, encode_seconds) | {
        "backend": backend,
        "command": " ".join(command),
        "cnf": str(cnf.resolve()),
        "cnf_sha256": file_sha256(cnf),
        "timeout_seconds": timeout,
        "write_seconds": round(write_seconds, 6),
    }
    solve_started = time.perf_counter()
    try:
        process = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout if timeout > 0 else None,
        )
    except subprocess.TimeoutExpired:
        return result | {
            "verdict": "TIMEOUT",
            "solve_seconds": round(time.perf_counter() - solve_started, 6),
            "partial_proof_bytes": proof.stat().st_size if proof.exists() else 0,
            "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
        }
    result["solve_seconds"] = round(time.perf_counter() - solve_started, 6)
    if process.returncode == 10:
        true_vars = (
            parse_solver_model(model, encoding.nvars)
            if backend == "cadical"
            else parse_text_model(process.stdout, encoding.nvars)
        )
        return result | sat_fields(encoding, true_vars) | {
            "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6)
        }
    if process.returncode == 20:
        check_seconds, checker_tail = run_drat_trim(checker, cnf, proof)
        answer = result | {
            "verdict": "UNSAT",
            "proof": str(proof.resolve()),
            "proof_bytes": proof.stat().st_size,
            "proof_sha256": file_sha256(proof),
            "proof_verified": True,
            "checker": checker,
            "checker_sha256": file_sha256(Path(checker)),
            "checker_log": str(proof.resolve()) + ".drat-trim.log",
            "check_seconds": round(check_seconds, 6),
            "checker_tail": checker_tail,
            "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
        }
        if corrupt_proof:
            answer["corrupt_proof_control"] = corrupt_and_reject(checker, cnf, proof)
        return answer
    tail = "\n".join(process.stdout.strip().splitlines()[-12:])
    raise RuntimeError(f"{backend} failed with exit {process.returncode}:\n{tail}")


def run_cubes(args: argparse.Namespace, checker: str | None) -> dict[str, object]:
    reduction = derive_reduction(args.v, args.b)
    cube_set = enumerate_cubes(
        reduction,
        drop_one=args.mutate_drop_cube and args.cube_depth == 1,
    )
    listing = {
        "v": args.v,
        "b": args.b,
        "second_point": 1,
        "row1_configurations": len(cube_set.configurations),
        "stabiliser_generators": len(cube_set.generators),
        "level1_cubes": len(cube_set.representatives),
        "level1_orbit_sizes": cube_set.orbit_sizes,
        "level1_representatives": [
            {"blocks": [[1, a, b] for a, b in pairs], "leave": list(leaves)}
            for pairs, leaves in cube_set.representatives
        ],
        "depth": args.cube_depth,
    }
    level1 = list(range(len(cube_set.representatives)))
    if args.cube_index is not None:
        if not 0 <= args.cube_index < len(cube_set.representatives):
            raise ExistenceError(
                f"--cube-index must be between 0 and {len(cube_set.representatives) - 1}"
            )
        level1 = [args.cube_index]
    cubes: list[tuple[str, Cube]] = []
    group_one = group_closure(cube_set.generators, reduction.v)
    listing["group_one_order"] = len(group_one)
    if args.cube_depth == 1:
        cubes = [(f"cube{i:03d}", (cube_set.representatives[i],)) for i in level1]
    else:
        listing["level2"] = {}
        for i in level1:
            children, sizes, order = refine_cube(
                reduction,
                cube_set.representatives[i],
                group_one,
                drop_one=args.mutate_drop_cube,
            )
            details: dict[str, object] = {
                "cubes": len(children),
                "orbit_sizes": sizes,
                "stabiliser_order": order,
                "child_stabiliser_orders": [order // size for size in sizes],
            }
            named_children = [(f"cube{i:03d}-{j:03d}", child) for j, child in enumerate(children)]
            if args.list_cubes and args.cube_index is not None:
                details["children"] = [
                    {
                        "name": name,
                        "orbit_size": sizes[j],
                        "stabiliser_order": order // sizes[j],
                        "rows": [
                            {
                                "point": point,
                                "blocks": [sorted((point, a, b)) for a, b in config[0]],
                                "leave": list(config[1]),
                            }
                            for point, config in enumerate(child, start=1)
                        ],
                    }
                    for j, (name, child) in enumerate(named_children)
                ]
            if args.cube_children is not None:
                start, stop = args.cube_children
                if stop > len(named_children):
                    raise ExistenceError(
                        f"--cube-children stop {stop} exceeds child count {len(named_children)} "
                        f"of cube {i}"
                    )
                named_children = named_children[start:stop]
                listing["cube_children"] = [start, stop]
            listing["level2"][str(i)] = details
            cubes.extend(named_children)
    listing["cubes"] = len(cubes)
    if args.list_cubes:
        return listing | {"verdict": "CUBES_LISTED"}
    artifact_dir = Path(args.artifacts)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    jsonl = artifact_dir / f"cubes-{args.v}-{args.b}-depth{args.cube_depth}.jsonl"
    mode = "a" if args.cube_index is not None or args.cube_children is not None else "w"
    per_cube: list[dict[str, object]] = []
    started = time.perf_counter()
    with jsonl.open(mode, encoding="utf-8") as handle:
        for name, cube in cubes:
            encode_started = time.perf_counter()
            cube_group = None
            if not args.no_cube_lex:
                cube_group = [g for g in group_one if all(apply_to_config(g, config) == config for config in cube)]
            encoding = build_existence_encoding(
                args.v, args.b, drop_exact_b=args.drop_exact_b, lex=False, degree=not args.no_degree, cube=cube, cube_group=cube_group
            )
            encode_seconds = time.perf_counter() - encode_started
            if args.backend == "pysat":
                record = solve_pysat(encoding, encode_seconds, args.timeout, False, False)
            else:
                record = solve_standalone(
                    encoding,
                    encode_seconds,
                    artifact_dir,
                    args.backend,
                    checker or "",
                    args.timeout,
                    False,
                    stem=f"exist-{args.v}-{args.b}-{name}",
                )
            record = record | {"cube_name": name}
            if args.keep_cnf is False and record["verdict"] == "UNSAT" and record.get("proof_verified"):
                Path(record["cnf"]).unlink()
                record["cnf_deleted_after_verification"] = True
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            per_cube.append(record)
            print(
                f"{name} ({len(per_cube)}/{len(cubes)}) verdict={record['verdict']} "
                f"solve={record.get('solve_seconds')} check={record.get('check_seconds')} "
                f"total={record.get('total_seconds')}",
                file=sys.stderr,
                flush=True,
            )
    verdicts = [record["verdict"] for record in per_cube]
    if any(v == "SAT" for v in verdicts):
        overall = "SAT"
    elif all(v == "UNSAT" for v in verdicts) and len(per_cube) == len(cubes) and args.cube_index is None:
        overall = "UNSAT"
    else:
        overall = "INCOMPLETE"
    return listing | {
        "verdict": overall,
        "cubes_solved": len(per_cube),
        "cube_verdicts": verdicts,
        "all_proofs_verified": all(r.get("proof_verified") for r in per_cube if r["verdict"] == "UNSAT"),
        "per_cube_solve_seconds": [r.get("solve_seconds") for r in per_cube],
        "per_cube_check_seconds": [r.get("check_seconds") for r in per_cube],
        "wall_seconds": round(time.perf_counter() - started, 6),
        "jsonl": str(jsonl.resolve()),
    }


def parse_half_open_range(value: str) -> tuple[int, int]:
    """Argparse converter for a nonnegative half-open range A:B."""
    try:
        fields = value.split(":")
        if len(fields) != 2:
            raise ValueError
        start, stop = (int(field) for field in fields)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected A:B with integer endpoints") from exc
    if start < 0 or stop < start:
        raise argparse.ArgumentTypeError("expected 0 <= A <= B")
    return start, stop


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("v", type=int)
    parser.add_argument("b", type=int)
    parser.add_argument("--backend", choices=("cadical", "kissat", "pysat"), default="cadical")
    parser.add_argument("--artifacts", default="scratch/exist-artifacts")
    parser.add_argument("--drat-trim")
    parser.add_argument("--timeout", type=float, default=0.0, help="seconds per solver call, 0 = none")
    parser.add_argument("--no-lex", action="store_true", help="omit the generator lex-leader constraints")
    parser.add_argument("--no-degree", action="store_true", help="omit the implied per-point degree bounds")
    parser.add_argument("--drop-exact-b", action="store_true", help="mutation control only")
    parser.add_argument("--corrupt-proof", action="store_true", help="mutation control: truncate the proof and require rejection")
    parser.add_argument("--cnf-only", action="store_true")
    parser.add_argument("--phase-hint", action="store_true", help="pysat: known control PTS as initial phases")
    parser.add_argument("--hint-cube", action="store_true", help="pysat: assume the known control PTS first (encoding consistency check, not a search control)")
    parser.add_argument(
        "--all-models",
        metavar="OUT_PTS",
        help="incrementally enumerate every distinct labelled block assignment; no proof logging",
    )
    parser.add_argument("--cubes", action="store_true", help="cube-and-conquer over the row of point 1")
    parser.add_argument("--list-cubes", action="store_true")
    parser.add_argument("--cube-index", type=int)
    parser.add_argument(
        "--cube-children",
        type=parse_half_open_range,
        metavar="A:B",
        help="depth 2 with one --cube-index: select global child indices A <= j < B",
    )
    parser.add_argument(
        "--mutate-drop-cube",
        action="store_true",
        help="mutation control: drop one representative at the selected depth",
    )
    parser.add_argument("--cube-depth", type=int, choices=(1, 2), default=1, help="1: row of point 1; 2: rows of points 1 and 2")
    parser.add_argument("--no-cube-lex", action="store_true", help="omit the lex-leader under the stabiliser of the cubed rows")
    parser.add_argument("--keep-cnf", action=argparse.BooleanOptionalAction, default=True, help="keep per-cube CNF files after a verified UNSAT (they are regenerable)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if (args.corrupt_proof or args.cubes) and args.backend == "pysat" and args.corrupt_proof:
            raise ExistenceError("--corrupt-proof requires a standalone backend")
        if (args.phase_hint or args.hint_cube) and args.backend != "pysat":
            raise ExistenceError("--phase-hint and --hint-cube need --backend pysat")
        if args.all_models is not None and (
            args.cubes or args.list_cubes or args.cnf_only or args.corrupt_proof or args.drop_exact_b
            or args.phase_hint or args.hint_cube
        ):
            raise ExistenceError(
                "--all-models cannot be combined with cubes, CNF/proof controls, or hints"
            )
        if args.cube_children is not None and (args.cube_depth != 2 or args.cube_index is None):
            raise ExistenceError("--cube-children requires --cube-depth 2 and one --cube-index")
        if args.mutate_drop_cube and args.cube_depth == 2 and args.cube_index is None:
            raise ExistenceError("depth-2 --mutate-drop-cube requires one --cube-index")
        checker = None
        if args.backend != "pysat":
            checker = find_executable(
                args.drat_trim,
                (
                    "~/tools/sat/drat-trim/drat-trim",
                    str(Path(__file__).resolve().parent / "scratch" / "drat-trim"),
                    "drat-trim",
                ),
            )
        if args.cubes or args.list_cubes:
            if args.mutate_drop_cube and not args.list_cubes:
                raise ExistenceError("--mutate-drop-cube is a listing-time control; add --list-cubes")
            print(json.dumps(run_cubes(args, checker), sort_keys=True), flush=True)
            return 0
        encode_started = time.perf_counter()
        encoding = build_existence_encoding(
            args.v, args.b, drop_exact_b=args.drop_exact_b, lex=not args.no_lex, degree=not args.no_degree
        )
        encode_seconds = time.perf_counter() - encode_started
        if args.all_models is not None:
            result = enumerate_all_models(
                encoding, encode_seconds, Path(args.all_models), args.timeout
            )
            print(json.dumps(result, sort_keys=True), flush=True)
            return 0
        if args.cnf_only:
            destination = Path(args.artifacts) / f"exist-{args.v}-{args.b}.cnf"
            destination.parent.mkdir(parents=True, exist_ok=True)
            write_clauses(encoding.nvars, encoding.clauses, destination)
            print(
                json.dumps(
                    common_result(encoding, encode_seconds)
                    | {"verdict": "CNF_ONLY", "cnf": str(destination.resolve()), "cnf_sha256": file_sha256(destination)},
                    sort_keys=True,
                )
            )
            return 0
        if args.backend == "pysat":
            result = solve_pysat(encoding, encode_seconds, args.timeout, args.phase_hint, args.hint_cube)
        else:
            result = solve_standalone(
                encoding, encode_seconds, Path(args.artifacts), args.backend, checker or "", args.timeout, args.corrupt_proof
            )
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (ExistenceError, OSError, RuntimeError, ValueError, AssertionError) as exc:
        print(f"exist: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
