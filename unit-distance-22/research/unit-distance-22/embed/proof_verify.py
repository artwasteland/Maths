#!/usr/bin/env python3
"""Exact replay checker for refutation trees emitted by udembed.py."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

import sympy as sp
from sympy.polys.matrices import DomainMatrix

from udembed import (
    Graph,
    difference_row,
    exact_one,
    exact_zero,
    four_cycle_rows,
    modulus_squared,
    normalize_exact,
)


class ProofError(ValueError):
    """Raised when a refutation tree cannot be replayed."""


EXACT_NAMES = {"I": sp.I, "sqrt": sp.sqrt}


def parse_exact(value: object) -> sp.Expr:
    if not isinstance(value, str):
        raise ProofError("exact scalar is not a string")
    try:
        expression = sp.sympify(value, locals=EXACT_NAMES)
    except (SyntaxError, TypeError, ValueError) as exc:
        raise ProofError("invalid exact scalar") from exc
    if expression.has(sp.Float):
        raise ProofError("floating-point scalar in proof")
    return normalize_exact(expression)


def parse_matrix(value: object, n: int) -> sp.Matrix:
    if not isinstance(value, list):
        raise ProofError("constraint system is not a list")
    rows = []
    for raw_row in value:
        if not isinstance(raw_row, list) or len(raw_row) != n:
            raise ProofError("constraint row has the wrong width")
        rows.append([parse_exact(entry) for entry in raw_row])
    return sp.Matrix(rows) if rows else sp.zeros(0, n)


def parse_graph(value: object) -> Graph:
    if not isinstance(value, dict) or not isinstance(value.get("n"), int):
        raise ProofError("invalid graph object")
    try:
        graph = Graph.from_edges(value["n"], value.get("edges", []))
    except (TypeError, ValueError) as exc:
        raise ProofError("invalid graph edge list") from exc
    if any(u < 0 or v >= graph.n for u, v in graph.edges):
        raise ProofError("graph endpoint out of range")
    return graph


def exact_rank(matrix: sp.Matrix) -> int:
    if matrix.rows == 0 or matrix.cols == 0:
        return 0
    return DomainMatrix.from_Matrix(matrix, fmt="dense", extension=True).to_field().rank()


def same_rowspace(left: sp.Matrix, right: sp.Matrix) -> bool:
    if left.cols != right.cols:
        return False
    rank_left = exact_rank(left)
    rank_right = exact_rank(right)
    if rank_left != rank_right:
        return False
    joined = left.col_join(right)
    return exact_rank(joined) == rank_left


def row_is_forced(matrix: sp.Matrix, row: Sequence[sp.Expr]) -> bool:
    return exact_rank(matrix.col_join(sp.Matrix([list(row)]))) == exact_rank(matrix)


def parse_edge(value: object, graph: Graph) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, int) for v in value):
        raise ProofError("invalid edge witness")
    u, v = sorted(value)
    if u < 0 or u == v or v >= graph.n:
        raise ProofError("edge witness endpoint out of range")
    return u, v


def expect_state(node: object, graph: Graph, matrix: sp.Matrix) -> tuple[dict, dict, list]:
    if not isinstance(node, dict):
        raise ProofError("proof node is not an object")
    stated_graph = parse_graph(node.get("graph"))
    if stated_graph != graph:
        raise ProofError("proof node graph does not match its parent")
    stated_matrix = parse_matrix(node.get("constraints"), graph.n)
    if not same_rowspace(stated_matrix, matrix):
        raise ProofError("proof node constraints do not match its parent")
    move = node.get("move")
    if not isinstance(move, dict) or not isinstance(move.get("kind"), str):
        raise ProofError("proof node has no move")
    children = node.get("children", [])
    if not isinstance(children, list):
        raise ProofError("proof children are not a list")
    return move, node, children


def replay_node(node: object, graph: Graph, matrix: sp.Matrix) -> None:
    move, _, children = expect_state(node, graph, matrix)
    kind = move["kind"]
    if kind == "L1a":
        if children:
            raise ProofError("L1a leaf has children")
        pair = parse_edge(move.get("collision"), graph)
        if not row_is_forced(matrix, difference_row(graph.n, pair)):
            raise ProofError("L1a collision is not forced")
        return
    if kind == "L1b":
        if children:
            raise ProofError("L1b leaf has children")
        raw_edges = move.get("edges")
        if not isinstance(raw_edges, list) or len(raw_edges) != 2:
            raise ProofError("L1b must name two edges")
        first, second = (parse_edge(edge, graph) for edge in raw_edges)
        if first not in graph.edges or second not in graph.edges:
            raise ProofError("L1b witness uses a non-edge")
        ratio = parse_exact(move.get("ratio"))
        relation = [
            normalize_exact(a - ratio * b)
            for a, b in zip(difference_row(graph.n, first), difference_row(graph.n, second))
        ]
        if not row_is_forced(matrix, relation):
            raise ProofError("L1b proportionality is not forced")
        norm = modulus_squared(ratio)
        if exact_one(norm):
            raise ProofError("L1b ratio has unit modulus")
        if not exact_zero(parse_exact(move.get("modulus_squared")) - norm):
            raise ProofError("L1b modulus witness is wrong")
        return
    if kind == "L2":
        if len(children) != 1:
            raise ProofError("L2 must have one child")
        reference = parse_edge(move.get("reference_edge"), graph)
        forced = parse_edge(move.get("forced_edge"), graph)
        if reference not in graph.edges or forced in graph.edges:
            raise ProofError("L2 edge status is wrong")
        ratio = parse_exact(move.get("ratio"))
        relation = [
            normalize_exact(a - ratio * b)
            for a, b in zip(difference_row(graph.n, reference), difference_row(graph.n, forced))
        ]
        if not row_is_forced(matrix, relation) or not exact_one(modulus_squared(ratio)):
            raise ProofError("L2 forced unit edge witness is wrong")
        child_graph = graph.with_edge(forced)
        _, rhombus_rows = four_cycle_rows(child_graph)
        child_matrix = matrix
        for row in rhombus_rows:
            child_matrix = child_matrix.col_join(sp.Matrix([list(row)]))
        replay_node(children[0], child_graph, child_matrix)
        return
    if kind == "L3":
        if len(children) != 2:
            raise ProofError("L3 must have two children")
        raw_edges = move.get("edges")
        raw_relation = move.get("relation")
        raw_branches = move.get("branch_rows")
        if not isinstance(raw_edges, list) or len(raw_edges) != 3:
            raise ProofError("L3 must name three edges")
        if not isinstance(raw_relation, list) or len(raw_relation) != 3:
            raise ProofError("L3 must name three coefficients")
        if not isinstance(raw_branches, list) or len(raw_branches) != 2:
            raise ProofError("L3 must name two branch rows")
        edges = [parse_edge(edge, graph) for edge in raw_edges]
        if any(edge not in graph.edges for edge in edges):
            raise ProofError("L3 witness uses a non-edge")
        a, b, c = (parse_exact(value) for value in raw_relation)
        if any(exact_zero(value) for value in (a, b, c)):
            raise ProofError("L3 relation has a zero coefficient")
        relation = [
            normalize_exact(
                a * difference_row(graph.n, edges[0])[i]
                + b * difference_row(graph.n, edges[1])[i]
                + c * difference_row(graph.n, edges[2])[i]
            )
            for i in range(graph.n)
        ]
        if not row_is_forced(matrix, relation):
            raise ProofError("L3 dependence is not forced")
        aa, bb, cc = (modulus_squared(value) for value in (a, b, c))
        discriminant = normalize_exact(4 * aa * bb - (aa + bb - cc) ** 2)
        if discriminant.is_nonnegative is not True:
            raise ProofError("L3 discriminant is not certified nonnegative")
        if not exact_zero(parse_exact(move.get("discriminant")) - discriminant):
            raise ProofError("L3 discriminant witness is wrong")
        for branch_index, sign in enumerate((1, -1)):
            factor = normalize_exact((aa + bb - cc + sign * sp.I * sp.sqrt(discriminant)) * a)
            other = normalize_exact(2 * aa * b)
            expected = [
                normalize_exact(
                    factor * difference_row(graph.n, edges[0])[i]
                    + other * difference_row(graph.n, edges[1])[i]
                )
                for i in range(graph.n)
            ]
            stated = [parse_exact(value) for value in raw_branches[branch_index]]
            if len(stated) != graph.n or any(not exact_zero(x - y) for x, y in zip(stated, expected)):
                raise ProofError("L3 branch constraint is wrong")
            child_matrix = matrix.col_join(sp.Matrix([stated]))
            replay_node(children[branch_index], graph, child_matrix)
        return
    raise ProofError(f"unexpected move {kind}")


def verify_private_refutation(record: object) -> bool:
    if not isinstance(record, dict) or record.get("verdict") != "refuted":
        raise ProofError("record is not a refutation")
    graph = Graph.from_graph6(record.get("g6", ""))
    root = record.get("witness")
    move, _, children = expect_state(root, graph, sp.zeros(0, graph.n))
    if move.get("kind") != "L0" or len(children) != 1:
        raise ProofError("refutation root is not L0")
    cycles, rows = four_cycle_rows(graph)
    if move.get("four_cycles") != [list(cycle) for cycle in cycles]:
        raise ProofError("L0 four-cycle list is wrong")
    initial = sp.Matrix(rows) if rows else sp.zeros(0, graph.n)
    if move.get("result_rank") != exact_rank(initial):
        raise ProofError("L0 rank is wrong")
    replay_node(children[0], graph, initial)
    return True


def verify_refutation(record: object) -> bool:
    """Replay a public certificate through the binding independent checker."""
    if not isinstance(record, dict) or record.get("verdict") != "refuted":
        raise ProofError("record is not a refutation")
    checker_dir = Path(__file__).resolve().parents[1] / "check"
    if str(checker_dir) not in sys.path:
        sys.path.insert(0, str(checker_dir))
    from udcheck import CheckError, decode_graph6, verify_refutation as checker_verify

    try:
        graph = decode_graph6(record.get("g6", ""), "g6")
        checker_verify(graph, record.get("witness"), "witness")
    except CheckError as exc:
        raise ProofError(str(exc)) from exc
    return True


__all__ = ["ProofError", "verify_private_refutation", "verify_refutation"]
