#!/usr/bin/env python3
"""Independent F-free graph enumerator for the u(22) programme.

The implementation deliberately keeps graph operations small and explicit.  It
uses pynauty only for canonical labelling and automorphism orbits.  Forbidden
subgraphs are checked by an independent injective edge-preserving backtracker.
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
from dataclasses import dataclass
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


def load_forbidden() -> list[Graph]:
    raw = json.loads(FORBIDDEN_JSON.read_text())
    graphs: list[Graph] = []
    for edges in raw:
        n = 1 + max(max(e) for e in edges)
        adj = [0] * n
        for x, y in edges:
            adj[x] |= 1 << y
            adj[y] |= 1 << x
        graphs.append(Graph(tuple(adj)))
    return graphs


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


def extend_parent(host: Graph, target_edges: int, patterns: Sequence[Pattern],
                  break_orbit: bool = False, verify: bool = False) -> Iterator[str]:
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
        if verify and not f_free(child, LOAD_FORBIDDEN):
            raise AssertionError("bad-neighborhood filter emitted a forbidden child")
        yield canonical_g6(child)


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
                           break_orbit: bool = False, verify: bool = False) -> int:
    parents = read_graph6(parent_path)
    patterns = list(PATTERNS)
    if drop_pattern is not None:
        dropped = {drop_pattern} if isinstance(drop_pattern, int) else set(drop_pattern)
        patterns = [p for i, p in enumerate(patterns) if i not in dropped]
    records: list[str] = []
    for parent in parents:
        if parent.n != target_n - 1:
            raise ValueError(f"parent {canonical_g6(parent)} has wrong order")
        records.extend(extend_parent(parent, target_m, patterns, break_orbit, verify))
    return write_graph6(output, records)


def geng(n: int, m: int) -> list[Graph]:
    """Read all unlabeled n-vertex m-edge graphs from the local nauty geng."""
    command = ["/usr/bin/nauty-geng", "-q", str(n), f"{m}:{m}"]
    proc = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
    return [graph6_decode(x) for x in proc.stdout.splitlines() if x]


def brute_force_records(n: int, m: int) -> set[str]:
    return {canonical_g6(g) for g in geng(n, m) if f_free(g, LOAD_FORBIDDEN)}


def enumerate_recursive(n: int, m: int, cache: dict[tuple[int, int], list[str]],
                       work: Path, verify: bool = False) -> list[str]:
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
        parent_records.extend(enumerate_recursive(n - 1, mp, cache, work, verify))
    parent_path = work / f"parents-{n}-{m}.g6"
    write_graph6(parent_path, parent_records)
    output = work / f"{n}-{m}.g6"
    enumerate_from_parents(parent_path, n, m, output, verify=verify)
    cache[key] = output.read_text().splitlines()
    return cache[key]


def run_mutations() -> dict[str, int]:
    """Exercise real extension paths with deliberately broken controls."""
    triangle = Graph((0b110, 0b101, 0b011))
    with tempfile.TemporaryDirectory(prefix="enum2-mutation-", dir=ROOT) as name:
        work = Path(name)
        parent = work / "parent.g6"
        parent.write_text(canonical_g6(triangle) + "\n")
        normal = work / "normal.g6"
        dropped = work / "dropped.g6"
        broken_orbit = work / "broken-orbit.g6"
        normal_count = enumerate_from_parents(parent, 4, 6, normal)
        dropped_count = enumerate_from_parents(parent, 4, 6, dropped,
                                               drop_pattern=list(range(4)))
        # The deleted K4 pattern is also the first pattern, so this path emits
        # the K4 when that real bad-neighborhood control is removed.
        two_edge_parent = Graph((0b10, 0b1))
        two_edge_parent_file = work / "two-edge-parent.g6"
        two_edge_parent_file.write_text(canonical_g6(two_edge_parent) + "\n")
        broken_raw = list(extend_parent(two_edge_parent, 2, PATTERNS,
                                         break_orbit=True))
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


def check_determinism(n: int, m: int, work: Path) -> tuple[int, bool]:
    cache: dict[tuple[int, int], list[str]] = {}
    first = enumerate_recursive(n, m, cache, work)
    second = enumerate_recursive(n, m, {}, work / "second")
    return len(first), first == second


LOAD_FORBIDDEN = load_forbidden()
PATTERNS = make_patterns(LOAD_FORBIDDEN)


def command_enumerate(args: argparse.Namespace) -> None:
    count = enumerate_from_parents(Path(args.parents), args.n, args.m,
                                    Path(args.output), args.drop_pattern,
                                    args.break_orbit, args.verify)
    print(f"children={count}")


def command_bruteforce(args: argparse.Namespace) -> None:
    records = brute_force_records(args.n, args.m)
    print(f"brute_force_f_free={len(records)}")


def command_mutations(_: argparse.Namespace) -> None:
    print(json.dumps(run_mutations(), sort_keys=True))


def command_check(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="enum2-check-", dir=ROOT) as name:
        work = Path(name)
        ours = set(enumerate_recursive(args.n, args.m, {}, work))
        brute = brute_force_records(args.n, args.m)
        print(f"n={args.n} m={args.m} ours={len(ours)} brute={len(brute)} equal={ours == brute}")
        if ours != brute:
            raise SystemExit(1)


def command_determinism(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="enum2-determinism-", dir=ROOT) as name:
        count, equal = check_determinism(args.n, args.m, Path(name))
        print(f"n={args.n} m={args.m} records={count} byte_identical={equal}")
        if not equal:
            raise SystemExit(1)


def command_table(args: argparse.Namespace) -> None:
    # The dense checkpoints are intentionally requested one at a time, so a
    # caller can enforce the programme's resource policy around this command.
    targets = [(16, 41), (17, 43), (18, 46), (19, 50), (20, 54), (21, 57)]
    with tempfile.TemporaryDirectory(prefix="enum2-table-", dir=ROOT) as name:
        work = Path(name)
        for n, m in targets[:args.limit]:
            records = enumerate_recursive(n, m, {}, work)
            print(f"n={n} m={m} f_free={len(records)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("enumerate")
    p.add_argument("--parents", required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--drop-pattern", type=int, action="append")
    p.add_argument("--break-orbit", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.set_defaults(function=command_enumerate)
    p = sub.add_parser("bruteforce")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.set_defaults(function=command_bruteforce)
    p = sub.add_parser("check")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.set_defaults(function=command_check)
    p = sub.add_parser("mutations")
    p.set_defaults(function=command_mutations)
    p = sub.add_parser("determinism")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.set_defaults(function=command_determinism)
    p = sub.add_parser("table")
    p.add_argument("--limit", type=int, default=2)
    p.set_defaults(function=command_table)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
