#!/usr/bin/env python3
"""Independent F-free graph enumerator for the u(22) and u(23) programmes.

The implementation deliberately keeps graph operations small and explicit.  It
uses pynauty only for canonical labelling and automorphism orbits.  Forbidden
subgraphs are checked by an independent injective edge-preserving backtracker.

Forbidden sets (2026-09-25).  The list of forbidden graphs is a parameter.  Two
lists are pinned by sha256 and by their structure (graph count, orders, number
of rooted deletion patterns and their root-size distribution), and nothing else
is accepted unless the caller says so explicitly (`allow_unpinned`, used only
by red controls):

  "74"   data/forbidden-74.json   the u(22) list; the default, as before
  "398"  data/forbidden-398.json  the 74 verbatim, then the 324 minimal
                                  forbidden graphs on 10 vertices (GP-10)

The module globals LOAD_FORBIDDEN and PATTERNS keep their old meaning (the 74).

Two engines compute the children of a parent.  Both implement the same
definition (CONTRACT 3.1 of u(22): canonical augmentation by minimum-degree
deletion, AMP's minimum-degree guard, bad neighbourhoods from the rooted
deletion patterns (F - x, N_F(x))):

  "reference"  the original code of this file, unchanged: rooted patterns are
               embedded roots-first and every pattern is searched separately.
  "fast"       (default) the same bad family, computed faster: isomorphic
               rooted patterns are searched once (rooted certificates), each
               pattern is searched along a connected vertex order that reaches
               every root as early as possible, a root image already known to
               be bad is not searched again, and a bad set that cannot fit into
               any candidate neighbourhood (|T u required| > d) is not
               collected.  Candidate neighbourhoods are enumerated in the same
               order as the reference engine and tested incrementally.

The fast engine is new code; it is checked against the reference engine, against
brute force, and against udenum (see CROSSCHECK-398 in the final report).
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import pynauty


ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data"
FORBIDDEN_JSON = DATA / "forbidden-74.json"

# These are the paper's exact dense bounds through n=21.  They are used only
# as the contract permits, as the upper end of the parent edge window.
KNOWN_UBAR = {
    0: 0, 1: 0, 2: 1, 3: 3, 4: 5, 5: 7, 6: 9, 7: 12,
    8: 14, 9: 18, 10: 20, 11: 23, 12: 27, 13: 30, 14: 33,
    15: 37, 16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57,
    22: 62, 23: 66,
}


@dataclass(frozen=True)
class Graph:
    """A simple graph represented by one integer neighbor mask per vertex."""

    adj: tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.adj)

    @property
    def m(self) -> int:
        return sum(x.bit_count() for x in self.adj) // 2

    def degree(self, v: int) -> int:
        return self.adj[v].bit_count()

    def add_vertex(self, neighborhood: int) -> "Graph":
        n = self.n
        a = list(self.adj) + [neighborhood]
        for v in range(n):
            if neighborhood & (1 << v):
                a[v] |= 1 << n
        return Graph(tuple(a))


def graph6_decode(line: str) -> Graph:
    """Decode one short graph6 record, including the n <= 62 format."""
    s = line.rstrip("\r\n")
    if not s:
        raise ValueError("empty graph6 record")
    vals = [ord(c) - 63 for c in s]
    if vals[0] < 63:
        n = vals[0]
        pos = 1
    elif vals[1] < 63:
        n = (vals[1] << 12) | (vals[2] << 6) | vals[3]
        pos = 4
    else:
        n = (vals[2] << 30) | (vals[3] << 24) | (vals[4] << 18)
        n |= (vals[5] << 12) | (vals[6] << 6) | vals[7]
        pos = 8
    bits: list[int] = []
    for value in vals[pos:]:
        bits.extend((value >> shift) & 1 for shift in (5, 4, 3, 2, 1, 0))
    adj = [0] * n
    k = 0
    # graph6 orders pairs by increasing larger endpoint: 01, 02, 12,
    # 03, 13, 23, and so on.
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                adj[i] |= 1 << j
                adj[j] |= 1 << i
            k += 1
    return Graph(tuple(adj))


def graph6_encode(g: Graph) -> str:
    """Encode a graph6 record for n <= 62."""
    if g.n >= 63:
        raise ValueError("this programme only handles graph6 n <= 62")
    out = [chr(g.n + 63)]
    bits: list[int] = []
    for j in range(1, g.n):
        for i in range(j):
            bits.append((g.adj[i] >> j) & 1)
    while len(bits) % 6:
        bits.append(0)
    for start in range(0, len(bits), 6):
        value = 0
        for bit in bits[start:start + 6]:
            value = (value << 1) | bit
        out.append(chr(value + 63))
    return "".join(out)


def pynauty_graph(g: Graph) -> pynauty.Graph:
    return pynauty.Graph(
        g.n,
        adjacency_dict={i: [j for j in range(g.n) if g.adj[i] & (1 << j)]
                        for i in range(g.n)},
    )


def canonical_graph(g: Graph) -> tuple[Graph, list[int]]:
    """Return the canonical graph and canonical-position to old-vertex map."""
    pg = pynauty_graph(g)
    order = list(pynauty.canon_label(pg))
    # pynauty returns the old vertex at each canonical position.
    rank = [0] * g.n
    for position, old in enumerate(order):
        rank[old] = position
    adj = [0] * g.n
    for old_i in range(g.n):
        for old_j in range(old_i + 1, g.n):
            if g.adj[old_i] & (1 << old_j):
                i, j = rank[old_i], rank[old_j]
                adj[i] |= 1 << j
                adj[j] |= 1 << i
    return Graph(tuple(adj)), order


def canonical_g6(g: Graph) -> str:
    return graph6_encode(canonical_graph(g)[0])


def canonical_augmentation_ok(child: Graph, added_vertex: int,
                              break_orbit: bool = False) -> bool:
    """Apply the minimum-degree deletion orbit rule from CONTRACT 3.1."""
    pg = pynauty_graph(child)
    order = list(pynauty.canon_label(pg))
    mindeg = min(child.degree(v) for v in range(child.n))
    first = next(v for v in order if child.degree(v) == mindeg)
    if break_orbit:
        # Mutation mode intentionally disables the orbit test.  This is a
        # deliberately weak control, useful because two different deletions
        # can then construct the same canonical child.
        return True
    orbits = pynauty.autgrp(pg)[3]
    return orbits[added_vertex] == orbits[first]


@dataclass(frozen=True)
class Pattern:
    adj: tuple[int, ...]
    neighborhood: int


def _graphs_from_edge_lists(raw: list) -> list[Graph]:
    graphs: list[Graph] = []
    for edges in raw:
        n = 1 + max(max(e) for e in edges)
        adj = [0] * n
        for x, y in edges:
            adj[x] |= 1 << y
            adj[y] |= 1 << x
        graphs.append(Graph(tuple(adj)))
    return graphs


def load_forbidden(path: Path | None = None) -> list[Graph]:
    """The forbidden graphs of a JSON edge-list file (default: the 74), unchecked.

    Use load_forbidden_set() for anything that needs the pin and the guards."""
    raw = json.loads((FORBIDDEN_JSON if path is None else Path(path)).read_text())
    return _graphs_from_edge_lists(raw)


def make_patterns(forbidden: Sequence[Graph]) -> list[Pattern]:
    patterns: list[Pattern] = []
    for f in forbidden:
        for deleted in range(f.n):
            keep = [v for v in range(f.n) if v != deleted]
            position = {v: i for i, v in enumerate(keep)}
            adj = [0] * len(keep)
            for i, old_i in enumerate(keep):
                for old_j in keep:
                    if old_i < old_j and f.adj[old_i] & (1 << old_j):
                        j = position[old_j]
                        adj[i] |= 1 << j
                        adj[j] |= 1 << i
            neighborhood = 0
            for old in keep:
                if f.adj[deleted] & (1 << old):
                    neighborhood |= 1 << position[old]
            patterns.append(Pattern(tuple(adj), neighborhood))
    return patterns


# ---------------------------------------------------------------------------
# The reference engine: the original implementation, unchanged.
# ---------------------------------------------------------------------------

def _pattern_embeddings(pattern: Pattern, host: Graph) -> Iterator[tuple[int, ...]]:
    """Yield all injective edge-preserving maps of pattern into host."""
    k = len(pattern.adj)
    if k > host.n:
        return
    order = sorted(range(k), key=lambda v: (-pattern.adj[v].bit_count(), v))
    mapping = [-1] * k
    used = 0

    def visit(depth: int, used_mask: int) -> Iterator[tuple[int, ...]]:
        if depth == k:
            yield tuple(mapping)
            return
        pv = order[depth]
        required = pattern.adj[pv]
        for hv in range(host.n):
            if used_mask & (1 << hv):
                continue
            if host.degree(hv) < required.bit_count():
                continue
            good = True
            for other in range(k):
                mapped = mapping[other]
                if mapped >= 0 and (required & (1 << other)):
                    if not (host.adj[hv] & (1 << mapped)):
                        good = False
                        break
            if not good:
                continue
            mapping[pv] = hv
            yield from visit(depth + 1, used_mask | (1 << hv))
            mapping[pv] = -1

    yield from visit(0, used)


def _candidate_mask(pattern: Pattern, host: Graph, pv: int,
                    mapping: Sequence[int], used_mask: int) -> int:
    candidates = (1 << host.n) - 1
    candidates &= ~used_mask
    candidates &= sum(1 << hv for hv in range(host.n)
                      if host.degree(hv) >= pattern.adj[pv].bit_count())
    for other, hv in enumerate(mapping):
        if hv >= 0 and (pattern.adj[pv] & (1 << other)):
            candidates &= host.adj[hv]
    return candidates


def _has_pattern_embedding(pattern: Pattern, host: Graph,
                           mapping: list[int], used_mask: int,
                           order: Sequence[int], depth: int) -> bool:
    if depth == len(order):
        return True
    pv = order[depth]
    candidates = _candidate_mask(pattern, host, pv, mapping, used_mask)
    while candidates:
        bit = candidates & -candidates
        candidates -= bit
        mapping[pv] = bit.bit_length() - 1
        if _has_pattern_embedding(pattern, host, mapping, used_mask | bit,
                                  order, depth + 1):
            mapping[pv] = -1
            return True
        mapping[pv] = -1
    return False


def _pattern_neighborhood_images(pattern: Pattern, host: Graph) -> Iterator[int]:
    """Yield each possible image of the rooted neighborhood once.

    Once the distinguished vertices have been assigned, the rest of the
    rooted forbidden graph needs only an existential match.  This avoids
    enumerating all completions that produce the same bad neighborhood.
    """
    if len(pattern.adj) > host.n:
        return
    roots = [p for p in range(len(pattern.adj))
             if pattern.neighborhood & (1 << p)]
    rest = [p for p in range(len(pattern.adj)) if p not in roots]
    root_order = sorted(roots, key=lambda p: (-pattern.adj[p].bit_count(), p))
    rest_order = sorted(rest, key=lambda p: (-pattern.adj[p].bit_count(), p))
    mapping = [-1] * len(pattern.adj)
    seen: set[int] = set()

    def assign_roots(depth: int, used_mask: int) -> Iterator[int]:
        if depth == len(root_order):
            if _has_pattern_embedding(pattern, host, mapping, used_mask,
                                      rest_order, 0):
                image = 0
                for p in roots:
                    image |= 1 << mapping[p]
                if image not in seen:
                    seen.add(image)
                    yield image
            return
        pv = root_order[depth]
        candidates = _candidate_mask(pattern, host, pv, mapping, used_mask)
        while candidates:
            bit = candidates & -candidates
            candidates -= bit
            mapping[pv] = bit.bit_length() - 1
            yield from assign_roots(depth + 1, used_mask | bit)
            mapping[pv] = -1

    yield from assign_roots(0, 0)


def bad_neighborhoods(host: Graph, patterns: Sequence[Pattern],
                      max_neighborhood_size: int | None = None) -> set[int]:
    """Compute the minimal T' family as host vertex masks."""
    masks: set[int] = set()
    for pattern in patterns:
        if (max_neighborhood_size is not None and
                pattern.neighborhood.bit_count() > max_neighborhood_size):
            continue
        masks.update(_pattern_neighborhood_images(pattern, host))
    # A neighborhood containing any nonminimal mask is already rejected by a
    # smaller one.  Sorting makes this deterministic and usually shortens it.
    minimal: set[int] = set()
    for mask in sorted(masks, key=lambda x: (x.bit_count(), x)):
        if not any((small & mask) == small for small in minimal):
            minimal.add(mask)
    return minimal


def straightforward_contains(host: Graph, forbidden: Graph) -> bool:
    """Independent full subgraph monomorphism test."""
    if forbidden.n > host.n:
        return False
    pattern = Pattern(forbidden.adj, 0)
    return next(_pattern_embeddings(pattern, host), None) is not None


def f_free(host: Graph, forbidden: Sequence[Graph]) -> bool:
    return not any(straightforward_contains(host, f) for f in forbidden)


def child_neighborhoods(host: Graph, degree: int, patterns: Sequence[Pattern],
                        mandatory: int = 0) -> Iterator[int]:
    if degree < 0 or degree > host.n:
        return
    if mandatory.bit_count() > degree:
        return
    bad = bad_neighborhoods(host, patterns, degree)
    optional = [v for v in range(host.n) if not (mandatory & (1 << v))]
    for vertices in itertools.combinations(optional, degree - mandatory.bit_count()):
        mask = sum(1 << v for v in vertices)
        mask |= mandatory
        if not any((t & mask) == t for t in bad):
            yield mask


def _extend_parent_reference(host: Graph, target_edges: int, patterns: Sequence[Pattern],
                             break_orbit: bool, verify: bool,
                             forbidden: Sequence[Graph]) -> Iterator[str]:
    degree = target_edges - host.m
    min_degree = min((host.degree(v) for v in range(host.n)), default=0)
    if min_degree < degree - 1:
        return
    mandatory = 0
    if min_degree == degree - 1:
        for v in range(host.n):
            if host.degree(v) == min_degree:
                mandatory |= 1 << v
        if mandatory.bit_count() > degree:
            return
    for neighborhood in child_neighborhoods(host, degree, patterns, mandatory):
        child = host.add_vertex(neighborhood)
        if not canonical_augmentation_ok(child, host.n, break_orbit):
            continue
        if verify and not f_free(child, forbidden):
            raise AssertionError("bad-neighborhood filter emitted a forbidden child")
        yield canonical_g6(child)


# ---------------------------------------------------------------------------
# Forbidden sets: pinned files, structural guards, explicit mutations.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ForbiddenSpec:
    name: str
    file: str
    sha256: str
    graphs: int
    orders: tuple[tuple[int, int], ...]       # (order, count), sorted
    patterns: int
    root_sizes: tuple[tuple[int, int], ...]   # (|N_F(x)|, count), sorted


# Structure computed from the files by this module (and, for the 398, equal to
# the numbers in enum/REPORT-398.md section 2, which were computed separately).
FORBIDDEN_SPECS = {
    "74": ForbiddenSpec(
        name="74", file="forbidden-74.json",
        sha256="ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
        graphs=74, orders=((4, 1), (5, 1), (6, 1), (7, 3), (8, 13), (9, 55)),
        patterns=635, root_sizes=((2, 61), (3, 413), (4, 130), (5, 26), (6, 4), (7, 1))),
    "398": ForbiddenSpec(
        name="398", file="forbidden-398.json",
        sha256="8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c",
        graphs=398, orders=((4, 1), (5, 1), (6, 1), (7, 3), (8, 13), (9, 55), (10, 324)),
        patterns=3875, root_sizes=((2, 251), (3, 2474), (4, 920), (5, 192), (6, 34), (7, 4))),
}
MAX_FORBIDDEN_ORDER = 10          # the 398 reach order 10; their deletion patterns order 9


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class ForbiddenSet:
    """A pinned list of forbidden graphs, its rooted deletion patterns and its engine."""

    name: str                       # "74", "398", or "unpinned"
    path: Path
    sha256: str
    graphs: list[Graph]
    patterns: list[Pattern]
    dropped: tuple[int, ...] = ()   # member indices removed on purpose (a red control)
    _engine: "PatternEngine | None" = field(default=None, repr=False)
    _tester: "ContainmentTester | None" = field(default=None, repr=False)

    @property
    def engine(self) -> "PatternEngine":
        if self._engine is None:
            self._engine = PatternEngine(self.patterns)
        return self._engine

    @property
    def tester(self) -> "ContainmentTester":
        """Containment decider over this set's graphs (indices are positions in
        self.graphs, which after drop_members are no longer file indices)."""
        if self._tester is None:
            self._tester = ContainmentTester(self.graphs)
        return self._tester

    def describe(self) -> dict:
        sizes: dict[int, int] = {}
        for p in self.patterns:
            s = p.neighborhood.bit_count()
            sizes[s] = sizes.get(s, 0) + 1
        orders: dict[int, int] = {}
        for g in self.graphs:
            orders[g.n] = orders.get(g.n, 0) + 1
        return {"name": self.name, "path": str(self.path), "sha256": self.sha256,
                "graphs": len(self.graphs), "patterns": len(self.patterns),
                "orders": sorted(orders.items()), "root_sizes": sorted(sizes.items()),
                "dropped_members": list(self.dropped)}


def _validate_edge_lists(raw: object, source: str) -> None:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{source}: not a non-empty JSON list of edge lists")
    for index, edges in enumerate(raw):
        if not isinstance(edges, list) or not edges:
            raise ValueError(f"{source}: member {index} is not a non-empty edge list")
        seen: set[tuple[int, int]] = set()
        for e in edges:
            if (not isinstance(e, list) or len(e) != 2 or
                    not all(isinstance(x, int) and not isinstance(x, bool) for x in e)):
                raise ValueError(f"{source}: member {index} has a malformed edge {e!r}")
            x, y = e
            if x < 0 or y < 0 or x == y:
                raise ValueError(f"{source}: member {index} has a bad edge {e!r}")
            key = (min(x, y), max(x, y))
            if key in seen:
                raise ValueError(f"{source}: member {index} repeats the edge {e!r}")
            seen.add(key)
        order = 1 + max(max(e) for e in edges)
        if order > MAX_FORBIDDEN_ORDER:
            raise ValueError(f"{source}: member {index} has order {order} > {MAX_FORBIDDEN_ORDER}")
        degree = [0] * order
        for x, y in edges:
            degree[x] += 1
            degree[y] += 1
        if min(degree) < 2:
            # a minimal forbidden graph has minimum degree >= 2; an isolated
            # top label would also make the order read from the edges wrong
            raise ValueError(f"{source}: member {index} has a vertex of degree {min(degree)}")


def resolve_forbidden_path(spec: str | Path) -> Path:
    key = str(spec)
    if key in FORBIDDEN_SPECS:
        return DATA / FORBIDDEN_SPECS[key].file
    return Path(spec)


def load_forbidden_set(spec: str | Path = "74", drop_members: Sequence[int] = (),
                       allow_unpinned: bool = False) -> ForbiddenSet:
    """Load a forbidden list by pinned name ("74", "398") or path, and check it.

    A file is accepted when its sha256 is one of the pins AND its structure
    equals that pin's (graph count, orders, pattern count, root sizes); any
    other file is refused unless allow_unpinned.  drop_members removes members
    AFTER the checks (a red control); the result is then named "<name>-drop...".
    """
    path = resolve_forbidden_path(spec).resolve()
    digest = file_sha256(path)
    pinned = [s for s in FORBIDDEN_SPECS.values() if s.sha256 == digest]
    if str(spec) in FORBIDDEN_SPECS and (not pinned or pinned[0].name != str(spec)):
        raise ValueError(f"{path}: sha256 {digest} is not the pin of forbidden set {spec}")
    if not pinned and not allow_unpinned:
        raise ValueError(f"{path}: sha256 {digest} matches no pinned forbidden set "
                         f"({', '.join(FORBIDDEN_SPECS)})")
    raw = json.loads(path.read_text())
    _validate_edge_lists(raw, str(path))
    graphs = _graphs_from_edge_lists(raw)
    patterns = make_patterns(graphs)
    name = pinned[0].name if pinned else "unpinned"
    fs = ForbiddenSet(name=name, path=path, sha256=digest, graphs=graphs, patterns=patterns)
    if pinned:
        spec_ = pinned[0]
        got = fs.describe()
        want = {"graphs": spec_.graphs, "patterns": spec_.patterns,
                "orders": [list(x) for x in spec_.orders],
                "root_sizes": [list(x) for x in spec_.root_sizes]}
        have = {"graphs": got["graphs"], "patterns": got["patterns"],
                "orders": [list(x) for x in got["orders"]],
                "root_sizes": [list(x) for x in got["root_sizes"]]}
        if have != want:
            raise ValueError(f"{path}: structure {have} differs from the pin of set {name}: {want}")
    if drop_members:
        drop = sorted(set(int(i) for i in drop_members))
        if any(i < 0 or i >= len(graphs) for i in drop):
            raise ValueError(f"drop index outside 0..{len(graphs) - 1}")
        kept = [g for i, g in enumerate(graphs) if i not in set(drop)]
        fs = ForbiddenSet(name=f"{name}-drop{'-'.join(map(str, drop))}", path=path, sha256=digest,
                          graphs=kept, patterns=make_patterns(kept), dropped=tuple(drop))
    return fs


# ---------------------------------------------------------------------------
# The fast engine.
# ---------------------------------------------------------------------------

def _bits(mask: int) -> list[int]:
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


def rooted_pattern_key(pattern: Pattern) -> tuple[int, bytes]:
    """Isomorphism invariant of the rooted pattern (F - x, N_F(x)).

    The graph F is rebuilt from the pattern (the deleted vertex x becomes
    vertex k, adjacent to the roots) and canonically labelled with x in a
    colour class of its own.  Two rooted patterns with equal keys are
    isomorphic as rooted graphs, so they have exactly the same root images in
    every host: searching one of them is enough."""
    k = len(pattern.adj)
    adjacency = {v: _bits(pattern.adj[v]) for v in range(k)}
    adjacency[k] = _bits(pattern.neighborhood)
    g = pynauty.Graph(k + 1, adjacency_dict=adjacency,
                      vertex_coloring=[set(range(k)), {k}])
    return k, pynauty.certificate(g)


def _connected(adj: Sequence[int], vertices: int) -> bool:
    if not vertices:
        return True
    start = vertices & -vertices
    reached = start
    frontier = start
    while frontier:
        low = frontier & -frontier
        frontier ^= low
        new = adj[low.bit_length() - 1] & vertices & ~reached
        reached |= new
        frontier |= new
    return reached == vertices


@dataclass(frozen=True)
class RootedPlan:
    """A search order for one rooted pattern: every position after the first is
    adjacent to an earlier one, and the roots come as early as a connected
    order allows (a smallest connected vertex set containing the roots first)."""

    k: int
    s: int
    edges: int
    degseq: tuple[int, ...]                 # pattern degrees, descending
    need: tuple[int, ...]                   # pattern degree at each position
    back: tuple[tuple[int, ...], ...]       # earlier adjacent positions
    isroot: tuple[bool, ...]
    last_root: int                          # position of the last root
    members: tuple[int, ...]                # indices of the input patterns it stands for


def make_plan(pattern: Pattern, members: tuple[int, ...]) -> RootedPlan:
    adj = pattern.adj
    k = len(adj)
    roots_mask = pattern.neighborhood
    everything = (1 << k) - 1
    if not _connected(adj, everything):
        raise ValueError("a deletion pattern is disconnected (its forbidden graph is not 2-connected)")
    deg = [adj[v].bit_count() for v in range(k)]
    others = [v for v in range(k) if not roots_mask >> v & 1]
    core = None
    for size in range(len(others) + 1):
        best_score = None
        for extra in itertools.combinations(others, size):
            candidate = roots_mask | sum(1 << v for v in extra)
            if _connected(adj, candidate):
                score = (sum(deg[v] for v in extra), [-v for v in extra])
                if best_score is None or score > best_score:
                    best_score, core = score, candidate
        if core is not None:
            break
    assert core is not None

    order: list[int] = []
    placed = 0

    def pick(pool: int, prefer_roots: bool) -> int:
        best = None
        best_key = None
        for v in _bits(pool):
            links = (adj[v] & placed).bit_count()
            if order and links == 0:
                continue
            key = (links, (roots_mask >> v & 1) if prefer_roots else 0, deg[v], -v)
            if best_key is None or key > best_key:
                best, best_key = v, key
        assert best is not None
        return best

    start = max(_bits(roots_mask), key=lambda v: (deg[v], -v))
    order.append(start)
    placed |= 1 << start
    while core & ~placed:
        v = pick(core & ~placed, True)
        order.append(v)
        placed |= 1 << v
    while everything & ~placed:
        v = pick(everything & ~placed, False)
        order.append(v)
        placed |= 1 << v
    position = {v: i for i, v in enumerate(order)}
    back = tuple(tuple(sorted(position[u] for u in _bits(adj[v]) if position[u] < i))
                 for i, v in enumerate(order))
    isroot = tuple(bool(roots_mask >> v & 1) for v in order)
    last_root = max(i for i, r in enumerate(isroot) if r)
    return RootedPlan(k=k, s=roots_mask.bit_count(), edges=sum(deg) // 2,
                      degseq=tuple(sorted(deg, reverse=True)),
                      need=tuple(deg[v] for v in order), back=back, isroot=isroot,
                      last_root=last_root, members=members)


class _TrieNode:
    """One position of the root phase, shared by every plan whose search order
    begins with the same (degree, earlier neighbours, root?) sequence."""

    __slots__ = ("need", "back", "isroot", "children", "tails", "index")

    def __init__(self, need: int, back: tuple[int, ...], isroot: bool):
        self.need = need
        self.back = back
        self.isroot = isroot
        self.children: list[_TrieNode] = []
        self.tails: list[tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]] = []
        self.index: dict[tuple, _TrieNode] = {}


def _build_trie(plans: Sequence[RootedPlan]) -> list[_TrieNode]:
    top = _TrieNode(0, (), False)
    for plan in plans:
        node = top
        for i in range(plan.last_root + 1):
            key = (plan.need[i], plan.back[i], plan.isroot[i])
            child = node.index.get(key)
            if child is None:
                child = _TrieNode(*key)
                node.index[key] = child
                node.children.append(child)
            node = child
        # the rest of the pattern: needs only an existential match
        node.tails.append((plan.need[plan.last_root + 1:], plan.back[plan.last_root + 1:]))
    return top.children


class PatternEngine:
    """Bad families and children for one list of rooted patterns."""

    def __init__(self, patterns: Sequence[Pattern], share: bool = True):
        self.source_count = len(patterns)
        self.share = share
        groups: dict[tuple[int, bytes], list[int]] = {}
        first: dict[tuple[int, bytes], Pattern] = {}
        for index, pattern in enumerate(patterns):
            key = rooted_pattern_key(pattern)
            if key not in groups:
                groups[key] = []
                first[key] = pattern
            groups[key].append(index)
        plans = [make_plan(first[key], tuple(members)) for key, members in groups.items()]
        # smaller root sets first (their images are the likely minimal ones),
        # then by input order, for determinism
        plans.sort(key=lambda p: (p.s, p.members[0]))
        self.plans = plans
        self.max_s = max((p.s for p in plans), default=0)
        self.max_k = max((p.k for p in plans), default=0)
        self.max_need = max((max(p.need) for p in plans), default=0)
        self.plans_upto = {d: [p for p in plans if p.s <= d] for d in range(self.max_s + 1)}
        self._tries: dict[tuple[int, int], list[_TrieNode]] = {}

    def describe(self) -> dict:
        return {"input_patterns": self.source_count, "rooted_classes": len(self.plans),
                "shared_search": self.share}

    def _trie(self, s: int, n: int) -> list[_TrieNode]:
        """The shared search tree of the plans with exactly s roots and at most n vertices."""
        key = (s, min(n, self.max_k))
        if key not in self._tries:
            self._tries[key] = _build_trie([p for p in self.plans
                                            if p.s == s and p.k <= key[1]])
        return self._tries[key]

    def _found_shared(self, host: Graph, d: int, required: int, deg_ok: list[int],
                      allowed_outside: int, to_candidates: bool = False
                      ) -> tuple[set[int], list[int] | None]:
        """Root images, by increasing root count s.

        (1) A partial root image that already contains a bad set of an earlier
        (smaller) s is abandoned: every image it could complete to is a proper
        superset of a bad set, hence not minimal, and only minimal bad sets are
        used.

        (2) Only with to_candidates: after each s, the candidate neighbourhoods
        (d-sets containing required) that contain no bad set found so far are
        the survivors, and a partial root image that lies inside no survivor is
        abandoned.  A bad set that lies inside no survivor cannot change which
        candidates are good (every candidate containing it is already bad), so
        the survivors after the last s are exactly the good neighbourhoods;
        the bad sets found are then only those that decide some candidate.
        Returns (bad images found, survivors or None)."""
        n = host.n
        hadj = host.adj
        found: set[int] = set()
        mapping = [0] * (self.max_k + 1)
        # known[v]: for each bad set T of a smaller root count containing v, T - v
        known: list[list[int]] = [[] for _ in range(n)]
        # within[v]: union of the surviving candidates that contain v (None: no pruning yet)
        within: list[int] | None = None
        survivors: list[int] | None = None

        def exists(need: tuple[int, ...], back: tuple[tuple[int, ...], ...], t: int,
                   base: int, used: int) -> bool:
            if t == len(need):
                return True
            cand = deg_ok[need[t]] & ~used
            for j in back[t]:
                cand &= hadj[mapping[j]]
                if not cand:
                    return False
            i = base + t
            while cand:
                bit = cand & -cand
                cand ^= bit
                mapping[i] = bit.bit_length() - 1
                if exists(need, back, t + 1, base, used | bit):
                    return True
            return False

        def walk(node: _TrieNode, i: int, cand: int, used: int, image: int, outside: int) -> None:
            # cand: the candidates of position i (computed by the caller, non-empty)
            root = node.isroot
            tails = node.tails
            children = node.children
            nxt = i + 1
            while cand:
                bit = cand & -cand
                cand ^= bit
                v = bit.bit_length() - 1
                mapping[i] = v
                if root:
                    new_image = image | bit
                    if within is not None and new_image & ~within[v]:
                        continue
                    superset = False
                    for rest in known[v]:
                        if rest & image == rest:
                            superset = True
                            break
                    if superset:
                        continue
                    new_outside = outside if bit & required else outside + 1
                else:
                    new_image = image
                    new_outside = outside
                new_used = used | bit
                for need, back in tails:
                    if new_image in found:
                        break
                    if exists(need, back, 0, nxt, new_used):
                        found.add(new_image)
                        break
                free = ~new_used
                for child in children:
                    c = deg_ok[child.need] & free
                    for j in child.back:
                        c &= hadj[mapping[j]]
                        if not c:
                            break
                    if c:
                        if child.isroot and new_outside >= allowed_outside:
                            c &= required
                            if not c:
                                continue
                        walk(child, nxt, c, new_used, new_image, new_outside)

        for s in range(2, min(d, self.max_s) + 1):
            before = set(found)
            for node in self._trie(s, n):
                c = deg_ok[node.need]
                if node.isroot and allowed_outside <= 0:
                    c &= required
                if c:
                    walk(node, 0, c, 0, 0, 0)
            for t in found - before:
                for v in _bits(t):
                    known[v].append(t & ~(1 << v))
            if to_candidates:
                survivors = good_neighbourhoods(n, d, required, sorted(found))
                if not survivors:
                    return found, survivors
                within = [0] * n
                for cand_set in survivors:
                    for v in _bits(cand_set):
                        within[v] |= cand_set
        if to_candidates and survivors is None:
            survivors = good_neighbourhoods(n, d, required, sorted(found))
        return found, survivors

    def _found_per_plan(self, host: Graph, d: int, required: int, deg_ok: list[int],
                        allowed_outside: int, stats: dict | None) -> set[int]:
        n = host.n
        hadj = host.adj
        plans = self.plans_upto.get(min(d, self.max_s), [])
        hdeg = [a.bit_count() for a in hadj]
        edges = sum(hdeg) // 2
        hdeg_sorted = sorted(hdeg, reverse=True)
        found: set[int] = set()
        mapping = [0] * (self.max_k + 1)
        searched = 0
        for plan in plans:
            k = plan.k
            if k > n or plan.edges > edges:
                continue
            dominated = True
            for a, b in zip(plan.degseq, hdeg_sorted):
                if a > b:
                    dominated = False
                    break
            if not dominated:
                continue
            searched += 1
            need = plan.need
            back = plan.back
            isroot = plan.isroot
            last = plan.last_root

            def exists(i: int, used: int) -> bool:
                if i == k:
                    return True
                cand = deg_ok[need[i]] & ~used
                for j in back[i]:
                    cand &= hadj[mapping[j]]
                    if not cand:
                        return False
                while cand:
                    bit = cand & -cand
                    cand ^= bit
                    mapping[i] = bit.bit_length() - 1
                    if exists(i + 1, used | bit):
                        return True
                return False

            def visit(i: int, used: int, image: int, outside: int) -> None:
                cand = deg_ok[need[i]] & ~used
                for j in back[i]:
                    cand &= hadj[mapping[j]]
                    if not cand:
                        return
                root = isroot[i]
                if root and outside >= allowed_outside:
                    cand &= required
                while cand:
                    bit = cand & -cand
                    cand ^= bit
                    mapping[i] = bit.bit_length() - 1
                    if root:
                        new_image = image | bit
                        new_outside = outside if bit & required else outside + 1
                    else:
                        new_image = image
                        new_outside = outside
                    if i == last:
                        if new_image not in found and exists(i + 1, used | bit):
                            found.add(new_image)
                    else:
                        visit(i + 1, used | bit, new_image, new_outside)

            visit(0, 0, 0, 0)
        if stats is not None:
            stats["plans_searched"] = stats.get("plans_searched", 0) + searched
        return found

    def _degree_masks(self, host: Graph) -> list[int]:
        n = host.n
        hdeg = [a.bit_count() for a in host.adj]
        deg_ok = []
        for t in range(self.max_need + 1):
            mask = 0
            for v in range(n):
                if hdeg[v] >= t:
                    mask |= 1 << v
            deg_ok.append(mask)
        return deg_ok

    @staticmethod
    def _minimal(found: Iterable[int]) -> list[int]:
        """The inclusion-minimal members (a set is kept unless a proper subset was kept)."""
        minimal: set[int] = set()
        for t in sorted(found, key=lambda x: (x.bit_count(), x)):
            sub = (t - 1) & t
            redundant = False
            while sub:
                if sub in minimal:
                    redundant = True
                    break
                sub = (sub - 1) & t
            if not redundant:
                minimal.add(t)
        return sorted(minimal, key=lambda x: (x.bit_count(), x))

    def bad_family(self, host: Graph, d: int, required: int,
                   stats: dict | None = None) -> list[int]:
        """Minimal bad sets T (host vertex masks) with |T u required| <= d.

        T is bad when some rooted pattern (P, S) has an injective
        edge-preserving map of P into the host sending S onto T.  A bad set
        with |T u required| > d cannot lie inside any candidate neighbourhood
        (every candidate has d vertices and contains required), so it is not
        collected.  (A test interface: children use good_candidates.)"""
        if d < 2 or not self.plans_upto.get(min(d, self.max_s)):
            return []
        allowed_outside = d - required.bit_count()
        if allowed_outside < 0:
            return []
        deg_ok = self._degree_masks(host)
        if self.share:
            found, _ = self._found_shared(host, d, required, deg_ok, allowed_outside)
        else:
            found = self._found_per_plan(host, d, required, deg_ok, allowed_outside, stats)
        minimal = self._minimal(found)
        if stats is not None:
            stats["bad_images"] = stats.get("bad_images", 0) + len(found)
            stats["bad_sets"] = stats.get("bad_sets", 0) + len(minimal)
        return minimal

    def good_candidates(self, host: Graph, d: int, required: int,
                        stats: dict | None = None) -> list[int]:
        """The good neighbourhoods: d-subsets of the host's vertices that contain
        required and no bad set, in the order of itertools.combinations over the
        optional vertices (the reference engine's order)."""
        n = host.n
        if d < 0 or d > n or required.bit_count() > d:
            return []
        if d < 2 or not self.plans_upto.get(min(d, self.max_s)):
            return good_neighbourhoods(n, d, required, [])
        allowed_outside = d - required.bit_count()
        deg_ok = self._degree_masks(host)
        if self.share:
            found, survivors = self._found_shared(host, d, required, deg_ok, allowed_outside,
                                                  to_candidates=True)
        else:
            found = self._found_per_plan(host, d, required, deg_ok, allowed_outside, stats)
            survivors = good_neighbourhoods(n, d, required, self._minimal(found))
        if stats is not None:
            stats["bad_images"] = stats.get("bad_images", 0) + len(found)
        return survivors


def good_neighbourhoods(n: int, d: int, required: int, bad: Sequence[int]) -> list[int]:
    """All d-subsets of range(n) that contain required and no bad set, in the
    order of itertools.combinations over the optional vertices."""
    free = d - required.bit_count()
    if free < 0 or d > n:
        return []
    by_last: dict[int, list[int]] = {}
    for t in bad:
        rest = t & ~required
        if not rest:
            return []            # T inside required: every candidate is bad
        by_last.setdefault(rest.bit_length() - 1, []).append(rest)
    optional = [v for v in range(n) if not required >> v & 1]
    out: list[int] = []
    count = len(optional)

    def visit(start: int, chosen: int, size: int) -> None:
        if size == free:
            out.append(chosen | required)
            return
        for idx in range(start, count - (free - size) + 1):
            v = optional[idx]
            new = chosen | (1 << v)
            ok = True
            for rest in by_last.get(v, ()):
                if rest & new == rest:
                    ok = False
                    break
            if ok:
                visit(idx + 1, new, size + 1)

    visit(0, 0, 0)
    return out


def canonical_child(child_adj: Sequence[int], new_vertex: int,
                    break_orbit: bool = False) -> str | None:
    """Canonical graph6 of the child if the canonical-deletion rule accepts
    new_vertex (it lies in the automorphism orbit of the first minimum-degree
    vertex in nauty's canonical order), else None.  One canon_label call gives
    both the rule's vertex and the output; autgrp is called only when that
    vertex is not new_vertex itself."""
    n = len(child_adj)
    g = pynauty.Graph(n, adjacency_dict={v: _bits(child_adj[v]) for v in range(n)})
    order = pynauty.canon_label(g)
    degs = [a.bit_count() for a in child_adj]
    mindeg = min(degs)
    first = next(v for v in order if degs[v] == mindeg)
    if not break_orbit and first != new_vertex:
        orbits = pynauty.autgrp(g)[3]
        if orbits[first] != orbits[new_vertex]:
            return None
    rank = [0] * n
    for position, old in enumerate(order):
        rank[old] = position
    adj = [0] * n
    for old in range(n):
        row = 0
        for u in _bits(child_adj[old]):
            row |= 1 << rank[u]
        adj[rank[old]] = row
    return graph6_encode(Graph(tuple(adj)))


def _extend_parent_fast(host: Graph, target_edges: int, engine: PatternEngine,
                        break_orbit: bool, verify: bool, forbidden: Sequence[Graph],
                        stats: dict | None) -> Iterator[str]:
    n = host.n
    degree = target_edges - host.m
    degs = [host.degree(v) for v in range(n)]
    min_degree = min(degs, default=0)
    if min_degree < degree - 1:
        return
    mandatory = 0
    if min_degree == degree - 1:
        for v in range(n):
            if degs[v] == min_degree:
                mandatory |= 1 << v
        if mandatory.bit_count() > degree:
            return
    if degree < 0 or degree > n:
        return
    if stats is not None:
        stats["parents_processed"] = stats.get("parents_processed", 0) + 1
    neighbourhoods = engine.good_candidates(host, degree, mandatory, stats)
    if stats is not None:
        stats["neighbourhoods_good"] = stats.get("neighbourhoods_good", 0) + len(neighbourhoods)
    base = list(host.adj)
    top = 1 << n
    for neighbourhood in neighbourhoods:
        child = list(base)
        child.append(neighbourhood)
        for v in _bits(neighbourhood):
            child[v] |= top
        code = canonical_child(child, n, break_orbit)
        if code is None:
            continue
        if verify and not f_free(Graph(tuple(child)), forbidden):
            raise AssertionError("bad-neighborhood filter emitted a forbidden child")
        if stats is not None:
            stats["children_raw"] = stats.get("children_raw", 0) + 1
        yield code


class ContainmentTester:
    """Decides whether a host contains one of a list of graphs as a (not
    necessarily induced) subgraph, and which one: a backtracker along a
    connected vertex order with bitmask candidates.  It is a second decider
    next to straightforward_contains (degree order, no bitmasks), and the two
    are compared in the validation."""

    def __init__(self, graphs: Sequence[Graph]):
        self.items = []
        for index, f in enumerate(graphs):
            k = f.n
            deg = [f.degree(v) for v in range(k)]
            start = max(range(k), key=lambda v: (deg[v], -v))
            order = [start]
            placed = 1 << start
            while len(order) < k:
                best = None
                best_key = None
                for v in range(k):
                    if placed >> v & 1:
                        continue
                    links = (f.adj[v] & placed).bit_count()
                    key = (links, deg[v], -v)
                    if best_key is None or key > best_key:
                        best, best_key = v, key
                order.append(best)
                placed |= 1 << best
            position = {v: i for i, v in enumerate(order)}
            back = tuple(tuple(position[u] for u in _bits(f.adj[v]) if position[u] < i)
                         for i, v in enumerate(order))
            self.items.append((index, k, f.m, tuple(sorted(deg, reverse=True)),
                               tuple(deg[v] for v in order), back))
        # small graphs first: most hosts that contain something contain a small one
        self.items.sort(key=lambda item: (item[1], item[2], item[0]))
        self.max_need = max((max(item[4]) for item in self.items), default=0)

    def first(self, host: Graph) -> int | None:
        """Index (in the input list) of the first contained graph in the test
        order, or None when the host contains none of them."""
        found = self._scan(host, stop_at_first=True)
        return found[0] if found else None

    def all(self, host: Graph) -> list[int]:
        """Indices (in the input list) of every contained graph, ascending."""
        return sorted(self._scan(host, stop_at_first=False))

    def _scan(self, host: Graph, stop_at_first: bool) -> list[int]:
        out: list[int] = []
        n = host.n
        hadj = host.adj
        hdeg = [a.bit_count() for a in hadj]
        edges = sum(hdeg) // 2
        hsorted = sorted(hdeg, reverse=True)
        deg_ok = []
        for t in range(self.max_need + 1):
            mask = 0
            for v in range(n):
                if hdeg[v] >= t:
                    mask |= 1 << v
            deg_ok.append(mask)
        mapping = [0] * 16
        for index, k, m, degseq, need, back in self.items:
            if k > n or m > edges:
                continue
            if any(a > b for a, b in zip(degseq, hsorted)):
                continue

            def search(i: int, used: int) -> bool:
                if i == k:
                    return True
                cand = deg_ok[need[i]] & ~used
                for j in back[i]:
                    cand &= hadj[mapping[j]]
                    if not cand:
                        return False
                while cand:
                    bit = cand & -cand
                    cand ^= bit
                    mapping[i] = bit.bit_length() - 1
                    if search(i + 1, used | bit):
                        return True
                return False

            if search(0, 0):
                out.append(index)
                if stop_at_first:
                    return out
        return out

    def contains(self, host: Graph) -> bool:
        return self.first(host) is not None


_ENGINES: dict[int, tuple[object, PatternEngine]] = {}


def engine_for(patterns: object) -> PatternEngine:
    """The fast engine of a pattern list (compiled once per list object)."""
    if isinstance(patterns, PatternEngine):
        return patterns
    if isinstance(patterns, ForbiddenSet):
        return patterns.engine
    key = id(patterns)
    hit = _ENGINES.get(key)
    if hit is not None and hit[0] is patterns and hit[1].source_count == len(patterns):
        return hit[1]
    engine = PatternEngine(list(patterns))
    _ENGINES[key] = (patterns, engine)   # keeps the list alive, so the id stays unique
    return engine


DEFAULT_ENGINE = os.environ.get("ENUM2_ENGINE", "fast")


def extend_parent(host: Graph, target_edges: int, patterns, break_orbit: bool = False,
                  verify: bool = False, *, engine: str | None = None,
                  forbidden: Sequence[Graph] | None = None,
                  stats: dict | None = None) -> Iterator[str]:
    """Canonical graph6 of every accepted child of host with target_edges edges.

    patterns: a list of Pattern (as before), a ForbiddenSet or a PatternEngine.
    The same child can be yielded more than once (Aut(host)-equivalent
    neighbourhoods); callers compare sets.  forbidden: the graphs --verify
    checks children against (default: those of a ForbiddenSet, else the 74)."""
    engine = engine or DEFAULT_ENGINE
    if forbidden is None:
        forbidden = patterns.graphs if isinstance(patterns, ForbiddenSet) else LOAD_FORBIDDEN
    if engine == "reference":
        plist = patterns.patterns if isinstance(patterns, ForbiddenSet) else patterns
        if isinstance(plist, PatternEngine):
            raise ValueError("the reference engine needs the pattern list")
        yield from _extend_parent_reference(host, target_edges, plist, break_orbit, verify,
                                            forbidden)
    elif engine == "fast":
        yield from _extend_parent_fast(host, target_edges, engine_for(patterns), break_orbit,
                                       verify, forbidden, stats)
    else:
        raise ValueError(f"unknown engine {engine!r}")


def edge_window(n: int, m: int) -> range:
    if n <= 1:
        return range(0, 0)
    lo = (m * (n - 2) + n - 1) // n
    hi = min(m, (n - 1) * (n - 2) // 2, KNOWN_UBAR.get(n - 1, m))
    return range(lo, hi + 1)


def read_graph6(path: Path) -> list[Graph]:
    if not path.exists():
        return []
    return [graph6_decode(line) for line in path.read_text().splitlines() if line]


def write_graph6(path: Path, records: Iterable[str]) -> int:
    values = sorted(set(records))
    path.write_text("".join(x + "\n" for x in values))
    return len(values)


def enumerate_from_parents(parent_path: Path, target_n: int, target_m: int,
                           output: Path, drop_pattern: int | Sequence[int] | None = None,
                           break_orbit: bool = False, verify: bool = False,
                           forbidden_set: ForbiddenSet | None = None,
                           engine: str | None = None, start: int | None = None,
                           end: int | None = None, stats: dict | None = None) -> int:
    parents = read_graph6(parent_path)
    if start is not None or end is not None:
        parents = parents[start or 0:end]
    fs = forbidden_set
    patterns = list(PATTERNS if fs is None else fs.patterns)
    graphs = LOAD_FORBIDDEN if fs is None else fs.graphs
    if drop_pattern is not None:
        dropped = {drop_pattern} if isinstance(drop_pattern, int) else set(drop_pattern)
        patterns = [p for i, p in enumerate(patterns) if i not in dropped]
        source: object = patterns
    else:
        source = fs if fs is not None else PATTERNS
    records: list[str] = []
    for parent in parents:
        if parent.n != target_n - 1:
            raise ValueError(f"parent {canonical_g6(parent)} has wrong order")
        records.extend(extend_parent(parent, target_m, source, break_orbit, verify,
                                     engine=engine, forbidden=graphs, stats=stats))
    if stats is not None:
        stats["parents_read"] = stats.get("parents_read", 0) + len(parents)
        stats["children_raw_total"] = stats.get("children_raw_total", 0) + len(records)
    return write_graph6(output, records)


def geng(n: int, m: int) -> list[Graph]:
    """Read all unlabeled n-vertex m-edge graphs from the local nauty geng."""
    command = ["/usr/bin/nauty-geng", "-q", str(n), f"{m}:{m}"]
    proc = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
    return [graph6_decode(x) for x in proc.stdout.splitlines() if x]


def brute_force_records(n: int, m: int, forbidden: Sequence[Graph] | None = None) -> set[str]:
    graphs = LOAD_FORBIDDEN if forbidden is None else forbidden
    return {canonical_g6(g) for g in geng(n, m) if f_free(g, graphs)}


def enumerate_recursive(n: int, m: int, cache: dict[tuple[int, int], list[str]],
                        work: Path, verify: bool = False,
                        forbidden_set: ForbiddenSet | None = None,
                        engine: str | None = None) -> list[str]:
    work.mkdir(parents=True, exist_ok=True)
    key = (n, m)
    if key in cache:
        return cache[key]
    if n == 0:
        if m != 0:
            cache[key] = []
        else:
            cache[key] = [graph6_encode(Graph(tuple()))]
        return cache[key]
    if n == 1:
        cache[key] = ["@"] if m == 0 else []
        return cache[key]
    parent_records: list[str] = []
    for mp in edge_window(n, m):
        parent_records.extend(enumerate_recursive(n - 1, mp, cache, work, verify,
                                                  forbidden_set, engine))
    parent_path = work / f"parents-{n}-{m}.g6"
    write_graph6(parent_path, parent_records)
    output = work / f"{n}-{m}.g6"
    enumerate_from_parents(parent_path, n, m, output, verify=verify,
                           forbidden_set=forbidden_set, engine=engine)
    cache[key] = output.read_text().splitlines()
    return cache[key]


def run_mutations(forbidden_set: ForbiddenSet | None = None,
                  engine: str | None = None) -> dict[str, int]:
    """Exercise real extension paths with deliberately broken controls."""
    fs = forbidden_set
    patterns = PATTERNS if fs is None else fs.patterns
    triangle = Graph((0b110, 0b101, 0b011))
    with tempfile.TemporaryDirectory(prefix="enum2-mutation-", dir=ROOT) as name:
        work = Path(name)
        parent = work / "parent.g6"
        parent.write_text(canonical_g6(triangle) + "\n")
        normal = work / "normal.g6"
        dropped = work / "dropped.g6"
        broken_orbit = work / "broken-orbit.g6"
        normal_count = enumerate_from_parents(parent, 4, 6, normal, forbidden_set=fs,
                                              engine=engine)
        dropped_count = enumerate_from_parents(parent, 4, 6, dropped,
                                               drop_pattern=list(range(4)), forbidden_set=fs,
                                               engine=engine)
        # The deleted K4 pattern is also the first pattern, so this path emits
        # the K4 when that real bad-neighborhood control is removed.
        two_edge_parent = Graph((0b10, 0b1))
        two_edge_parent_file = work / "two-edge-parent.g6"
        two_edge_parent_file.write_text(canonical_g6(two_edge_parent) + "\n")
        broken_raw = list(extend_parent(two_edge_parent, 2, patterns,
                                        break_orbit=True, engine=engine))
        broken_count = write_graph6(broken_orbit, broken_raw)
        if normal_count != 0:
            raise AssertionError("K4 was accepted by the normal path")
        if dropped_count == 0:
            raise AssertionError("deleted bad-neighborhood pattern did not fail")
        if len(broken_raw) <= broken_count:
            raise AssertionError("broken orbit control did not create a duplicate")
        return {"normal_k4": normal_count, "drop_pattern_k4": dropped_count,
                "break_orbit_raw": len(broken_raw),
                "break_orbit_unique": broken_count}


def check_determinism(n: int, m: int, work: Path,
                      forbidden_set: ForbiddenSet | None = None) -> tuple[int, bool]:
    cache: dict[tuple[int, int], list[str]] = {}
    first = enumerate_recursive(n, m, cache, work, forbidden_set=forbidden_set)
    second = enumerate_recursive(n, m, {}, work / "second", forbidden_set=forbidden_set)
    return len(first), first == second


LOAD_FORBIDDEN = load_forbidden()
PATTERNS = make_patterns(LOAD_FORBIDDEN)


def _forbidden_from_args(args: argparse.Namespace) -> ForbiddenSet | None:
    spec = getattr(args, "forbidden", None) or "74"
    drop = getattr(args, "drop_forbidden", None) or ()
    allow = getattr(args, "allow_unpinned", False)
    return load_forbidden_set(spec, drop_members=drop, allow_unpinned=allow)


def command_enumerate(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    stats: dict = {}
    t0 = time.process_time()
    count = enumerate_from_parents(Path(args.parents), args.n, args.m,
                                   Path(args.output), args.drop_pattern,
                                   args.break_orbit, args.verify, forbidden_set=fs,
                                   engine=args.engine, start=args.start, end=args.end,
                                   stats=stats)
    print(f"children={count}")
    if args.stats:
        stats["cpu_seconds"] = round(time.process_time() - t0, 3)
        stats["forbidden"] = fs.describe() if fs is not None else None
        stats["engine"] = args.engine or DEFAULT_ENGINE
        print(json.dumps(stats, sort_keys=True), file=sys.stderr)


def command_info(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    info = fs.describe()
    info["engine"] = fs.engine.describe()
    print(json.dumps(info, indent=1))


def command_bruteforce(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    records = brute_force_records(args.n, args.m, fs.graphs)
    print(f"brute_force_f_free={len(records)}")


def command_mutations(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    print(json.dumps(run_mutations(fs, args.engine), sort_keys=True))


def command_check(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    with tempfile.TemporaryDirectory(prefix="enum2-check-", dir=ROOT) as name:
        work = Path(name)
        ours = set(enumerate_recursive(args.n, args.m, {}, work, forbidden_set=fs,
                                       engine=args.engine))
        brute = brute_force_records(args.n, args.m, fs.graphs)
        print(f"n={args.n} m={args.m} ours={len(ours)} brute={len(brute)} equal={ours == brute}")
        if ours != brute:
            raise SystemExit(1)


def command_determinism(args: argparse.Namespace) -> None:
    fs = _forbidden_from_args(args)
    with tempfile.TemporaryDirectory(prefix="enum2-determinism-", dir=ROOT) as name:
        count, equal = check_determinism(args.n, args.m, Path(name), fs)
        print(f"n={args.n} m={args.m} records={count} byte_identical={equal}")
        if not equal:
            raise SystemExit(1)


def command_table(args: argparse.Namespace) -> None:
    # The dense checkpoints are intentionally requested one at a time, so a
    # caller can enforce the programme's resource policy around this command.
    fs = _forbidden_from_args(args)
    targets = [(16, 41), (17, 43), (18, 46), (19, 50), (20, 54), (21, 57)]
    with tempfile.TemporaryDirectory(prefix="enum2-table-", dir=ROOT) as name:
        work = Path(name)
        for n, m in targets[:args.limit]:
            records = enumerate_recursive(n, m, {}, work, forbidden_set=fs)
            print(f"n={n} m={m} f_free={len(records)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    def forbidden_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("--forbidden", default="74",
                       help="pinned set name (74, 398) or a JSON path whose sha256 is pinned")
        p.add_argument("--drop-forbidden", type=int, action="append",
                       help="RED CONTROL: remove this member (index into the list) after loading")
        p.add_argument("--allow-unpinned", action="store_true",
                       help="RED CONTROL: accept a list whose sha256 is not pinned")
        p.add_argument("--engine", choices=("fast", "reference"), default=None)

    p = sub.add_parser("enumerate")
    p.add_argument("--parents", required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--start", type=int, default=None, help="first parent record (0-based)")
    p.add_argument("--end", type=int, default=None, help="one past the last parent record")
    p.add_argument("--drop-pattern", type=int, action="append")
    p.add_argument("--break-orbit", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--stats", action="store_true", help="print a JSON stats line on stderr")
    forbidden_options(p)
    p.set_defaults(function=command_enumerate)
    p = sub.add_parser("info")
    forbidden_options(p)
    p.set_defaults(function=command_info)
    p = sub.add_parser("bruteforce")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    forbidden_options(p)
    p.set_defaults(function=command_bruteforce)
    p = sub.add_parser("check")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    forbidden_options(p)
    p.set_defaults(function=command_check)
    p = sub.add_parser("mutations")
    forbidden_options(p)
    p.set_defaults(function=command_mutations)
    p = sub.add_parser("determinism")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    forbidden_options(p)
    p.set_defaults(function=command_determinism)
    p = sub.add_parser("table")
    p.add_argument("--limit", type=int, default=2)
    forbidden_options(p)
    p.set_defaults(function=command_table)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
