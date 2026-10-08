#!/usr/bin/env python3
"""Independent checker for the "tri" certificates of RHOMBUS-SPEC.md Section 4 (triangle case trees).

Written blind, from research/unit-distance-23/RHOMBUS-SPEC.md Section 4 with amendments 1 and 2 (2026-09-26), as
the checking half of the trust chain for the u(23) triangle rule. It shares no code with any prover.

Record (one JSON object per line of a JSONL certificate file)::

    {"g6": G, "verdict": "refuted" | "tu", "witness": {"tri": {"tree": NODE}}}
    NODE := {"split": [a, b, c], "plus": NODE, "minus": NODE}
          | {"leaf": {"cycles": [[u,v,w,x], ...], "cycle_coefficients": [Zw, ...],
                      "triangles": [[a,b,c], ...], "triangle_coefficients": [Zw, ...],
                      "scale": Zw, "pair": [a, b], "edge": [p, q], "zeta": k}}
    ("edge" and "zeta" together or neither.)

A Z[w] element is a JSON pair [x, y] of integers meaning x + y w, where w = e^(i pi/3), so w^2 = w - 1 and
w^(-1) = 1 - w.  For a sorted triangle T = (a, b, c) and a sign s, t(T, s) = e_c - e_a - w^s (e_b - e_a); for a
4-cycle C = [u, v, w, x], r(C) = e_u - e_v + e_w - e_x.

The rules, checked literally and in exact integer arithmetic (Python integers, no modular or float step):

 1. every `split` is a list of three JSON integers a < b < c in [0, n) whose three pairs are edges of G; no triangle
    is split twice on one root-to-leaf path; `plus` gives it s = +1 and `minus` s = -1; the tree has at most
    100,000 nodes and depth at most 64 (the root has depth 0, so a leaf may lie below at most 64 splits);
 2. every entry of a leaf's `triangles` is a sorted triple [a, b, c], a < b < c, EQUAL as that list to a triple
    split on the path to the leaf, and it is used with that path's sign (never looked up as a set); every entry
    of `cycles` is a list of four pairwise distinct JSON integers in [0, n) with uv, vw, wx, xu edges of G; `cycles`
    has at most 4096 entries; either list may be empty but not both; the coefficient lists have the lengths of
    their lists; every coefficient and the scale is a Z[w] pair of JSON integers of absolute value below 2^62; no
    coefficient is [0, 0]; the scale is not [0, 0];
 3. `pair` is two distinct JSON integers in [0, n); with `edge`: `edge` is two distinct JSON integers [p, q] with
    pq an edge of G, ab is NOT an edge of G, `zeta` is a JSON integer 0..5 and the target is
    e_a - e_b - w^zeta (e_p - e_q); without `edge` the target is e_a - e_b.  The target is a vector SUM: when pair
    and edge share a vertex its entries accumulate (they may cancel or double);
 4. sum_j l_j r(C_j) + sum_T m_T t(T, s_T) equals scale * target in Z[w]^n, multiplying by
    (x1 + y1 w)(x2 + y2 w) = (x1 x2 - y1 y2) + (x1 y2 + x2 y1 + y1 y2) w, in arbitrary-precision Python integers
    (never a fixed-width type: 4096 terms of size 2^62 overflow 64 bits);
 5. the verdict is `refuted` if and only if no leaf has an `edge`, and `tu` if and only if some leaf has one.

Every object must have exactly the keys shown: a split node exactly `split`, `plus`, `minus` (so a missing child is
rejected), a leaf node exactly `leaf`, a leaf exactly its six keys or those and `edge` and `zeta`. JSON objects with
a duplicate key, and NaN or Infinity, are rejected.  Duplicate entries inside `cycles` or `triangles` are accepted:
the specification does not forbid them and they are mathematically harmless (they add up).

Library use: ``verify_tri_witness(n, edges, verdict, witness) -> (ok, reason, stats)``.
Command line: ``tri_verify.py CERTS.jsonl [--graphs G.g6] [--labelg PATH] [--expect-n N] [--expect-m M]`` prints
``ACCEPT tri records=N refuted=R tu=T nodes=K`` and exits 0, or prints ``REJECT: <reason>`` on stderr and exits 1.
Every record must carry a tri witness; with --graphs the records' g6 sequence must equal that list exactly;
every g6 string must be nauty-labelg canonical and appear once.
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["TriReject", "verify_tri_witness", "verify_tri_file", "decode_graph6", "zmul", "W_POW",
           "MAX_NODES", "MAX_DEPTH", "MAX_LEAF_CYCLES", "COEFF_BOUND"]

MAX_NODES = 100_000            # rule 1: at most 100,000 nodes (splits and leaves together)
MAX_DEPTH = 64                 # rule 1: depth at most 64, the root at depth 0
MAX_LEAF_CYCLES = 4096         # rule 2: a leaf's `cycles` has at most 4096 entries
COEFF_BOUND = 1 << 62          # rule 2: every integer of a coefficient or of the scale has |x| < 2^62


class TriReject(Exception):
    """A certificate violates Section 4; the message says which rule and where."""


# ---------------------------------------------------------------------------------------------------------------
# Z[w] with w^2 = w - 1.  An element x + y w is the tuple (x, y) of Python integers.

def zmul(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    """(x1 + y1 w)(x2 + y2 w) = (x1 x2 - y1 y2) + (x1 y2 + x2 y1 + y1 y2) w, using w^2 = w - 1."""
    x1, y1 = a
    x2, y2 = b
    return (x1 * x2 - y1 * y2, x1 * y2 + x2 * y1 + y1 * y2)


def zadd(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return (a[0] + b[0], a[1] + b[1])


def zneg(a: tuple[int, int]) -> tuple[int, int]:
    return (-a[0], -a[1])


Z_ZERO = (0, 0)
Z_ONE = (1, 0)
W_PLUS = (0, 1)                # w^(+1) = w
W_MINUS = (1, -1)              # w^(-1) = 1 - w
W_POW: list[tuple[int, int]] = [Z_ONE]
for _k in range(1, 6):         # w^k for k in 0..5 by repeated multiplication
    W_POW.append(zmul(W_POW[-1], W_PLUS))
del _k
# Self-checks of the arithmetic (they run at import; a failure stops the checker before it can accept anything).
if zmul(W_PLUS, W_PLUS) != zadd(W_PLUS, zneg(Z_ONE)):                   # w^2 = w - 1
    raise AssertionError("Z[w] multiplication does not satisfy w^2 = w - 1")
if zmul(W_PLUS, W_MINUS) != Z_ONE or W_POW[5] != W_MINUS:               # w * (1 - w) = 1 and w^5 = w^(-1)
    raise AssertionError("w^(-1) = 1 - w fails")
if zmul(W_POW[5], W_PLUS) != Z_ONE or W_POW[3] != zneg(Z_ONE):          # w^6 = 1 and w^3 = -1
    raise AssertionError("w is not a primitive sixth root of unity")

# t(T, s) = e_c - e_a - w^s (e_b - e_a): its entries at a, b and c, computed literally for s = +1 and s = -1.
_T_ENTRIES: dict[int, tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = {}
for _s, _ws in ((1, W_PLUS), (-1, W_MINUS)):
    _T_ENTRIES[_s] = (zadd(zneg(Z_ONE), _ws),   # at a: -1 + w^s
                      zneg(_ws),                # at b: -w^s
                      Z_ONE)                    # at c: +1
del _s, _ws
# The same entries flattened for the leaf loop, which writes zmul's formula out inline.
_T_FLAT = {s: (ea[0], ea[1], eb[0], eb[1], ec[0], ec[1]) for s, (ea, eb, ec) in _T_ENTRIES.items()}
if _T_ENTRIES[1] != ((-1, 1), (0, -1), (1, 0)) or _T_ENTRIES[-1] != ((0, -1), (-1, 1), (1, 0)):
    raise AssertionError("t(T, s) entries differ from e_c - e_a - w^s (e_b - e_a)")

_LEAF_KEYS = frozenset({"cycles", "cycle_coefficients", "triangles", "triangle_coefficients", "scale", "pair"})
_LEAF_KEYS_EDGE = _LEAF_KEYS | {"edge", "zeta"}
_SPLIT_KEYS = frozenset({"split", "plus", "minus"})
_RECORD_KEYS = frozenset({"g6", "verdict", "witness"})
_VERDICTS = ("refuted", "tu")


# ---------------------------------------------------------------------------------------------------------------
# Locations for messages are kept as a chain (parent, step) and only formatted when a check fails.

def _where(loc: Any) -> str:
    steps = []
    while loc is not None:
        loc, step = loc
        steps.append(step)
    return "tree" + "".join("." + s for s in reversed(steps))


def _keys_reason(obj: dict, required: Iterable[str], optional: Iterable[str], where: str) -> str:
    keys = set(obj)
    required = set(required)
    missing = sorted(required - keys)
    extra = sorted(keys - required - set(optional))
    return f"{where}: missing keys {missing}, extra keys {extra}"


def _zw(value: Any, where: Any, field: str) -> tuple[int, int]:
    """A Z[w] pair [x, y] of JSON integers with |x|, |y| < 2^62 (rule 2)."""
    if type(value) is not list or len(value) != 2:
        raise TriReject(f"{_where(where)}.leaf.{field}: expected a Z[w] pair [x, y] (rule 2)")
    x, y = value
    if type(x) is not int or type(y) is not int:
        raise TriReject(f"{_where(where)}.leaf.{field}: Z[w] entries must be JSON integers, got {value!r} (rule 2)")
    if not (-COEFF_BOUND < x < COEFF_BOUND and -COEFF_BOUND < y < COEFF_BOUND):
        raise TriReject(f"{_where(where)}.leaf.{field}: Z[w] entry of absolute value 2^62 or more (rule 2)")
    return x, y


def _vertex_pair(value: Any, n: int, loc: Any, field: str) -> tuple[int, int]:
    if type(value) is not list or len(value) != 2:
        raise TriReject(f"{_where(loc)}.leaf.{field}: expected [u, v] (rule 3)")
    u, v = value
    if type(u) is not int or type(v) is not int:
        raise TriReject(f"{_where(loc)}.leaf.{field}: vertices must be JSON integers, got {value!r} (rule 3)")
    if not (0 <= u < n and 0 <= v < n):
        raise TriReject(f"{_where(loc)}.leaf.{field}: vertex out of range [0, {n}) in {value!r} (rule 3)")
    if u == v:
        raise TriReject(f"{_where(loc)}.leaf.{field}: the two vertices must be distinct, got {value!r} (rule 3)")
    return u, v


def _check_split(split: Any, n: int, adj: Sequence[int], loc: Any) -> tuple[int, int, int]:
    if type(split) is not list or len(split) != 3:
        raise TriReject(f"{_where(loc)}.split: expected a triple [a, b, c] (rule 1)")
    a, b, c = split
    if type(a) is not int or type(b) is not int or type(c) is not int:
        raise TriReject(f"{_where(loc)}.split: vertices must be JSON integers, got {split!r} (rule 1)")
    if not (0 <= a < n and 0 <= b < n and 0 <= c < n):
        raise TriReject(f"{_where(loc)}.split: vertex out of range [0, {n}) in {split!r} (rule 1)")
    if not a < b < c:
        raise TriReject(f"{_where(loc)}.split: {split!r} is not a sorted triple a < b < c (rule 1)")
    for u, v in ((a, b), (a, c), (b, c)):
        if not (adj[u] >> v) & 1:
            raise TriReject(f"{_where(loc)}.split: {split!r} is not a triangle of G, {u}-{v} is not an edge (rule 1)")
    return (a, b, c)


def _check_leaf(leaf: Any, n: int, adj: Sequence[int], path: dict, loc: Any) -> bool:
    """Rules 2 to 4 for one leaf; returns whether the leaf has an edge."""
    if type(leaf) is not dict:
        raise TriReject(f"{_where(loc)}.leaf: expected an object")
    nkeys = len(leaf)
    if nkeys == 6 and leaf.keys() == _LEAF_KEYS:
        has_edge = False
    elif nkeys == 8 and leaf.keys() == _LEAF_KEYS_EDGE:
        has_edge = True
    else:
        if ("edge" in leaf) != ("zeta" in leaf):
            raise TriReject(f"{_where(loc)}.leaf: 'edge' and 'zeta' must appear together or not at all")
        raise TriReject(_keys_reason(leaf, _LEAF_KEYS, ("edge", "zeta"), _where(loc) + ".leaf"))

    cycles = leaf["cycles"]
    ccoef = leaf["cycle_coefficients"]
    tris = leaf["triangles"]
    tcoef = leaf["triangle_coefficients"]
    if type(cycles) is not list:
        raise TriReject(f"{_where(loc)}.leaf.cycles: expected a list (rule 2)")
    if type(tris) is not list:
        raise TriReject(f"{_where(loc)}.leaf.triangles: expected a list (rule 2)")
    if type(ccoef) is not list or len(ccoef) != len(cycles):
        raise TriReject(f"{_where(loc)}.leaf.cycle_coefficients: expected a list as long as cycles (rule 2)")
    if type(tcoef) is not list or len(tcoef) != len(tris):
        raise TriReject(f"{_where(loc)}.leaf.triangle_coefficients: expected a list as long as triangles (rule 2)")
    if len(cycles) > MAX_LEAF_CYCLES:
        raise TriReject(f"{_where(loc)}.leaf.cycles: more than {MAX_LEAF_CYCLES} entries (rule 2)")
    if not cycles and not tris:
        raise TriReject(f"{_where(loc)}.leaf: cycles and triangles are both empty (rule 2)")

    B = COEFF_BOUND
    X = [0] * n                 # the x parts of sum_j l_j r(C_j) + sum_T m_T t(T, s_T)
    Y = [0] * n                 # the y parts (coefficients of w)

    # sum_j l_j r(C_j), r(C) = e_u - e_v + e_w - e_x (an integer vector, so l_j r(C_j) is +-l_j entrywise)
    for j, (cyc, c) in enumerate(zip(cycles, ccoef)):
        if type(cyc) is not list or len(cyc) != 4:
            raise TriReject(f"{_where(loc)}.leaf.cycles[{j}]: expected four vertices [u, v, w, x] (rule 2)")
        u, v, w, x = cyc
        if type(u) is not int or type(v) is not int or type(w) is not int or type(x) is not int:
            raise TriReject(f"{_where(loc)}.leaf.cycles[{j}]: vertices must be JSON integers, got {cyc!r} (rule 2)")
        if not (0 <= u < n and 0 <= v < n and 0 <= w < n and 0 <= x < n):
            raise TriReject(f"{_where(loc)}.leaf.cycles[{j}]: vertex out of range [0, {n}) in {cyc!r} (rule 2)")
        if u == v or u == w or u == x or v == w or v == x or w == x:
            raise TriReject(f"{_where(loc)}.leaf.cycles[{j}]: {cyc!r} is not pairwise distinct (rule 2)")
        # uv, vw, wx and xu must all be edges: the lowest bit of the AND of the four shifted rows
        if not ((adj[u] >> v) & (adj[v] >> w) & (adj[w] >> x) & (adj[x] >> u) & 1):
            s, t = next((s, t) for s, t in ((u, v), (v, w), (w, x), (x, u)) if not (adj[s] >> t) & 1)
            raise TriReject(f"{_where(loc)}.leaf.cycles[{j}]: {cyc!r} is not a 4-cycle of G, "
                            f"{s}-{t} is not an edge (rule 2)")
        if type(c) is not list or len(c) != 2:
            raise TriReject(f"{_where(loc)}.leaf.cycle_coefficients[{j}]: expected a Z[w] pair [x, y] (rule 2)")
        lx, ly = c
        if type(lx) is not int or type(ly) is not int:
            raise TriReject(f"{_where(loc)}.leaf.cycle_coefficients[{j}]: Z[w] entries must be JSON integers, "
                            f"got {c!r} (rule 2)")
        if not (-B < lx < B and -B < ly < B):
            raise TriReject(f"{_where(loc)}.leaf.cycle_coefficients[{j}]: Z[w] entry of absolute value 2^62 "
                            f"or more (rule 2)")
        if lx == 0 and ly == 0:
            raise TriReject(f"{_where(loc)}.leaf.cycle_coefficients[{j}]: coefficient is [0, 0] (rule 2)")
        X[u] += lx
        Y[u] += ly
        X[v] -= lx
        Y[v] -= ly
        X[w] += lx
        Y[w] += ly
        X[x] -= lx
        Y[x] -= ly

    # sum_T m_T t(T, s_T), s_T the sign the path gives T
    for j, (tri, m) in enumerate(zip(tris, tcoef)):
        if type(tri) is not list or len(tri) != 3:
            raise TriReject(f"{_where(loc)}.leaf.triangles[{j}]: expected a triple [a, b, c] (rule 2)")
        a, b, c3 = tri
        if type(a) is not int or type(b) is not int or type(c3) is not int:
            raise TriReject(f"{_where(loc)}.leaf.triangles[{j}]: vertices must be JSON integers, got {tri!r} "
                            f"(rule 2)")
        if not a < b < c3:
            raise TriReject(f"{_where(loc)}.leaf.triangles[{j}]: {tri!r} is not a sorted triple a < b < c (rule 2)")
        s = path.get((a, b, c3))
        if s is None:
            raise TriReject(f"{_where(loc)}.leaf.triangles[{j}]: {tri!r} is not a triangle split on the path to "
                            f"this leaf (rule 2)")
        if type(m) is not list or len(m) != 2:
            raise TriReject(f"{_where(loc)}.leaf.triangle_coefficients[{j}]: expected a Z[w] pair [x, y] (rule 2)")
        mx, my = m
        if type(mx) is not int or type(my) is not int:
            raise TriReject(f"{_where(loc)}.leaf.triangle_coefficients[{j}]: Z[w] entries must be JSON integers, "
                            f"got {m!r} (rule 2)")
        if not (-B < mx < B and -B < my < B):
            raise TriReject(f"{_where(loc)}.leaf.triangle_coefficients[{j}]: Z[w] entry of absolute value 2^62 "
                            f"or more (rule 2)")
        if mx == 0 and my == 0:
            raise TriReject(f"{_where(loc)}.leaf.triangle_coefficients[{j}]: coefficient is [0, 0] (rule 2)")
        # m_T times the entries of t(T, s) at a, b, c, by zmul's formula written out:
        # (x1 + y1 w)(x2 + y2 w) = (x1 x2 - y1 y2) + (x1 y2 + x2 y1 + y1 y2) w
        a0, a1, b0, b1, c0, c1 = _T_FLAT[s]
        X[a] += mx * a0 - my * a1
        Y[a] += mx * a1 + a0 * my + my * a1
        X[b] += mx * b0 - my * b1
        Y[b] += mx * b1 + b0 * my + my * b1
        X[c3] += mx * c0 - my * c1
        Y[c3] += mx * c1 + c0 * my + my * c1

    scale = _zw(leaf["scale"], loc, "scale")
    if scale == Z_ZERO:
        raise TriReject(f"{_where(loc)}.leaf.scale: the scale is [0, 0] (rule 2)")

    a, b = _vertex_pair(leaf["pair"], n, loc, "pair")
    target = {a: Z_ONE}
    target[b] = zadd(target.get(b, Z_ZERO), zneg(Z_ONE))
    if has_edge:
        p, q = _vertex_pair(leaf["edge"], n, loc, "edge")
        if not (adj[p] >> q) & 1:
            raise TriReject(f"{_where(loc)}.leaf.edge: {[p, q]} is not an edge of G (rule 3)")
        if (adj[a] >> b) & 1:
            raise TriReject(f"{_where(loc)}.leaf.pair: {[a, b]} is an edge of G; with an edge the pair must be a "
                            f"non-edge (rule 3)")
        k = leaf["zeta"]
        if type(k) is not int or not 0 <= k <= 5:
            raise TriReject(f"{_where(loc)}.leaf.zeta: expected a JSON integer 0..5, got {k!r} (rule 3)")
        wk = W_POW[k]           # target e_a - e_b - w^k (e_p - e_q)
        target[p] = zadd(target.get(p, Z_ZERO), zneg(wk))
        target[q] = zadd(target.get(q, Z_ZERO), wk)

    RX = [0] * n
    RY = [0] * n
    for vtx, val in target.items():
        rx, ry = zmul(scale, val)
        RX[vtx] = rx
        RY[vtx] = ry
    if X != RX or Y != RY:      # rule 4
        bad = next(i for i in range(n) if X[i] != RX[i] or Y[i] != RY[i])
        raise TriReject(f"{_where(loc)}.leaf: identity fails at vertex {bad}: the relations sum to "
                        f"[{X[bad]}, {Y[bad]}] but scale * target is [{RX[bad]}, {RY[bad]}] (rule 4)")
    return has_edge


def _adjacency(n: Any, edges: Iterable[Any]) -> list[int]:
    if type(n) is not int or n < 0:
        raise TriReject("graph: the order n must be a non-negative integer")
    adj = [0] * n
    for e in edges:
        try:
            u, v = e
        except (TypeError, ValueError):
            raise TriReject(f"graph: invalid edge {e!r}")
        if type(u) is not int or type(v) is not int or not (0 <= u < n and 0 <= v < n) or u == v:
            raise TriReject(f"graph: invalid edge {e!r}")
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return adj


def _check_witness(n: int, adj: Sequence[int], verdict: Any, witness: Any, stats: dict) -> None:
    if type(verdict) is not str or verdict not in _VERDICTS:
        raise TriReject(f"verdict: a tri witness needs verdict 'refuted' or 'tu', got {verdict!r}")
    if type(witness) is not dict or witness.keys() != {"tri"}:
        if type(witness) is not dict:
            raise TriReject("witness: expected an object with exactly the key 'tri'")
        raise TriReject(_keys_reason(witness, ("tri",), (), "witness"))
    tri = witness["tri"]
    if type(tri) is not dict or tri.keys() != {"tree"}:
        if type(tri) is not dict:
            raise TriReject("witness.tri: expected an object with exactly the key 'tree'")
        raise TriReject(_keys_reason(tri, ("tree",), (), "witness.tri"))

    # Depth-first, plus before minus. `path` maps each split triangle on the current root-to-node path to its
    # sign; two-element stack items are markers that switch a triangle to -1 (after its plus subtree) and remove
    # it (after its minus subtree), so `path` always holds exactly the ancestors of the node being visited.
    path: dict[tuple[int, int, int], int] = {}
    stack: list[tuple] = [(tri["tree"], 0, None)]
    nodes = leaves = splits = units = depth_max = 0
    any_edge = False
    while stack:
        item = stack.pop()
        if len(item) == 2:
            key, sign = item
            if sign:
                path[key] = sign
            else:
                del path[key]
            continue
        node, depth, loc = item
        nodes += 1
        if nodes > MAX_NODES:
            raise TriReject(f"tree: more than {MAX_NODES} nodes (rule 1)")
        if depth > MAX_DEPTH:
            raise TriReject(f"{_where(loc)}: node at depth {depth}, deeper than {MAX_DEPTH} (rule 1)")
        if depth > depth_max:
            depth_max = depth
        if type(node) is not dict:
            raise TriReject(f"{_where(loc)}: expected a node object")
        if "leaf" in node:
            if len(node) != 1:
                raise TriReject(_keys_reason(node, ("leaf",), (), _where(loc)))
            leaves += 1
            if _check_leaf(node["leaf"], n, adj, path, loc):
                units += 1
                any_edge = True
                if verdict == "refuted":
                    raise TriReject(f"verdict refuted but the leaf at {_where(loc)} has an edge (rule 5)")
        elif "split" in node:
            if node.keys() != _SPLIT_KEYS:
                raise TriReject(_keys_reason(node, _SPLIT_KEYS, (), _where(loc)))
            key = _check_split(node["split"], n, adj, loc)
            if key in path:
                raise TriReject(f"{_where(loc)}.split: triangle {list(key)} is split twice on one root-to-leaf "
                                f"path (rule 1)")
            splits += 1
            path[key] = 1                                   # plus assigns s = +1
            stack.append((key, 0))                          # after the minus subtree: leave the path
            stack.append((node["minus"], depth + 1, (loc, "minus")))
            stack.append((key, -1))                         # after the plus subtree: minus assigns s = -1
            stack.append((node["plus"], depth + 1, (loc, "plus")))
        else:
            raise TriReject(f"{_where(loc)}: a node needs exactly the key 'leaf' or exactly the keys "
                            f"'split', 'plus', 'minus'; got {sorted(node)}")
        stats["nodes"] = nodes
    stats.update(nodes=nodes, leaves=leaves, splits=splits, depth=depth_max, unit_leaves=units,
                 collision_leaves=leaves - units)
    if verdict == "tu" and not any_edge:
        raise TriReject("verdict tu but no leaf has an edge (rule 5)")


def _new_stats() -> dict:
    return {"nodes": 0, "leaves": 0, "splits": 0, "depth": 0, "unit_leaves": 0, "collision_leaves": 0}


def verify_tri_witness(n: int, edges: Iterable[Any], verdict: Any, witness: Any) -> tuple[bool, str, dict]:
    """Check one tri witness against the graph (n, edges) under Section 4 rules 1 to 5.

    `edges` is an iterable of vertex pairs; `verdict` and `witness` are the record's parsed JSON values.
    Returns (ok, reason, stats): reason is "" when ok, and stats counts nodes, leaves, splits, depth,
    unit_leaves and collision_leaves (partial counts when the check fails).
    """
    stats = _new_stats()
    try:
        adj = _adjacency(n, edges)
        _check_witness(n, adj, verdict, witness, stats)
    except TriReject as exc:
        return False, str(exc), stats
    except Exception as exc:        # fail closed: anything unforeseen is a rejection, never an acceptance
        return False, f"internal error while checking (rejected): {type(exc).__name__}: {exc}", stats
    return True, "", stats


# ---------------------------------------------------------------------------------------------------------------
# File level: the conventions of check/udcheck.py (graph6 decoding, strict JSON, canonical form, --graphs).

def decode_graph6(code: Any) -> tuple[int, list[int], int]:
    """Decode a graph6 string exactly as check/udcheck.py does; returns (n, adjacency bitmasks, edge count)."""
    if type(code) is not str or not code:
        raise TriReject("g6: expected a nonempty graph6 string")
    if code.startswith(">>") or any(ord(ch) < 63 or ord(ch) > 126 for ch in code):
        raise TriReject("g6: unsupported header or non-graph6 byte")
    vals = [ord(ch) - 63 for ch in code]
    if vals[0] <= 62:
        n, pos = vals[0], 1
    elif len(vals) >= 4 and vals[0] == 63 and vals[1] != 63:
        n, pos = (vals[1] << 12) | (vals[2] << 6) | vals[3], 4
    else:
        raise TriReject("g6: graph order encoding is unsupported")
    need_bits = n * (n - 1) // 2
    if len(vals) - pos != (need_bits + 5) // 6:
        raise TriReject(f"g6: wrong graph6 length for n={n}")
    adj = [0] * n
    k = 0
    m = 0
    j, i = 1, 0
    for v in vals[pos:]:
        for shift in range(5, -1, -1):
            bit = (v >> shift) & 1
            if k < need_bits:
                if bit:
                    adj[i] |= 1 << j
                    adj[j] |= 1 << i
                    m += 1
                k += 1
                i += 1
                if i == j:
                    j += 1
                    i = 0
            elif bit:
                raise TriReject("g6: nonzero graph6 padding bits")
    return n, adj, m


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    d = dict(pairs)
    if len(d) != len(pairs):
        seen: set[str] = set()
        for key, _ in pairs:
            if key in seen:
                raise TriReject(f"JSON object has duplicate key {key!r}")
            seen.add(key)
    return d


def _no_constant(name: str) -> Any:
    raise TriReject(f"non-standard JSON constant {name}")


def _read_graph_list(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TriReject(f"cannot read graph list {path}: {exc}")
    if raw and not raw.endswith(b"\n"):
        raise TriReject(f"{path}: missing final newline")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise TriReject(f"{path}: non-ASCII graph list: {exc}")
    if any(not line for line in lines):
        raise TriReject(f"{path}: blank graph6 record")
    return lines


def _check_canonical(codes: Sequence[str], labelg: str) -> None:
    if not codes:
        return
    try:
        proc = subprocess.run([labelg, "-q"], input=("\n".join(codes) + "\n").encode("ascii"),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TriReject(f"canonical graph6 check could not run {labelg}: {exc}")
    if proc.returncode != 0:
        raise TriReject(f"canonical graph6 check failed: {proc.stderr.decode(errors='replace').strip()}")
    lines = proc.stdout.decode("ascii", errors="replace").splitlines()
    if lines != list(codes):
        bad = next((i for i, pair in enumerate(itertools.zip_longest(lines, codes), 1) if pair[0] != pair[1]), 1)
        raise TriReject(f"g6: graph6 record {bad} is not nauty-labelg canonical")


def verify_tri_file(path: Path, graphs: Path | None = None, labelg: str = "/usr/bin/nauty-labelg",
                    expect_n: int | None = None, expect_m: int | None = None) -> dict:
    """Verify a JSONL file of tri records; raises TriReject, else returns the counts."""
    counts = {"records": 0, "refuted": 0, "tu": 0, "nodes": 0}
    codes: list[str] = []
    seen: set[str] = set()
    try:
        stream = path.open("rb")
    except OSError as exc:
        raise TriReject(f"cannot open certificate file {path}: {exc}")
    with stream:
        for lineno, raw in enumerate(stream, 1):
            where = f"{path}:{lineno}"
            if not raw.endswith(b"\n"):
                raise TriReject(f"{where}: missing final newline")
            if not raw.strip():
                raise TriReject(f"{where}: blank certificate record")
            try:
                record = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
                                    parse_constant=_no_constant)
            except TriReject as exc:
                raise TriReject(f"{where}: invalid JSON: {exc}")
            except (ValueError, RecursionError) as exc:      # JSONDecodeError, UnicodeDecodeError, huge ints
                raise TriReject(f"{where}: invalid JSON: {type(exc).__name__}: {str(exc)[:200]}")
            if type(record) is not dict or record.keys() != _RECORD_KEYS:
                if type(record) is not dict:
                    raise TriReject(f"{where}: expected a JSON object")
                raise TriReject(_keys_reason(record, _RECORD_KEYS, (), where))
            code = record["g6"]
            try:
                n, adj, m = decode_graph6(code)
            except TriReject as exc:
                raise TriReject(f"{where}: {exc}")
            if expect_n is not None and n != expect_n:
                raise TriReject(f"{where}: expected {expect_n} vertices, got {n}")
            if expect_m is not None and m != expect_m:
                raise TriReject(f"{where}: expected {expect_m} edges, got {m}")
            if code in seen:
                raise TriReject(f"{where}: duplicate graph6 record")
            seen.add(code)
            codes.append(code)
            stats = _new_stats()
            try:
                _check_witness(n, adj, record["verdict"], record["witness"], stats)
            except TriReject as exc:
                raise TriReject(f"{where}: {exc}")
            except Exception as exc:    # fail closed
                raise TriReject(f"{where}: internal error while checking (rejected): {type(exc).__name__}: {exc}")
            counts["records"] += 1
            counts[record["verdict"]] += 1
            counts["nodes"] += stats["nodes"]
    if graphs is not None and _read_graph_list(graphs) != codes:
        raise TriReject("certificate graph6 records do not exactly equal the supplied graph list in order")
    _check_canonical(codes, labelg)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("certificates", type=Path, help="JSONL file of tri certificate records")
    parser.add_argument("--graphs", type=Path, help="graph6 list which the records' g6 sequence must equal")
    parser.add_argument("--labelg", default="/usr/bin/nauty-labelg")
    parser.add_argument("--expect-n", type=int, help="required order of every graph (default: any)")
    parser.add_argument("--expect-m", type=int, help="required size of every graph (default: any)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        c = verify_tri_file(args.certificates, args.graphs, args.labelg, args.expect_n, args.expect_m)
    except TriReject as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:        # fail closed on anything unforeseen
        print(f"REJECT: internal error while checking (rejected): {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"ACCEPT tri records={c['records']} refuted={c['refuted']} tu={c['tu']} nodes={c['nodes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
