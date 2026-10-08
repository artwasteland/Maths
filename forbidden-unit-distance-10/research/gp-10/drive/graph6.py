"""Small graph6 and graph-poset primitives used by the GP-10 driver.

The frozen GP-10 inputs use ordinary graph6, but the decoder also accepts the
two extended graph6 order encodings.  The edge bit order is the graph6 order:
columns ``j = 1 .. n-1``, with rows ``i = 0 .. j-1`` in each column.

The canonicalisation routine deliberately keeps both permutations returned by
pynauty.  ``canon_label`` returns ``new_vertex -> old_vertex``.  Its inverse is
therefore ``old_vertex -> new_vertex``.  Keeping the two names explicit avoids
the common pointer-direction error in the GP-10 poset.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import pynauty


class Graph6Error(ValueError):
    """Raised for malformed graph6 or an invalid graph operation."""


def _sixbit_values(raw: bytes) -> list[int]:
    values: list[int] = []
    for byte in raw:
        value = byte - 63
        if not 0 <= value < 64:
            raise Graph6Error("graph6 payload contains a non-graph6 byte")
        values.append(value)
    return values


def _read_order(raw: bytes) -> tuple[int, int]:
    if not raw:
        raise Graph6Error("empty graph6 string")
    first = raw[0] - 63
    if first < 0:
        raise Graph6Error("graph6 order byte is below 63")
    if first < 63:
        return first, 1
    if len(raw) >= 2 and raw[1] - 63 == 63:
        if len(raw) < 10:
            raise Graph6Error("truncated extended graph6 order")
        values = _sixbit_values(raw[2:10])
        order = 0
        for value in values:
            order = (order << 6) | value
        return order, 10
    if len(raw) < 5:
        raise Graph6Error("truncated graph6 order")
    values = _sixbit_values(raw[1:5])
    order = 0
    for value in values:
        order = (order << 6) | value
    return order, 5


def pair_index(n: int, u: int, v: int) -> int:
    """Return the bit index of the unordered pair ``{u, v}``."""

    if not 0 <= u < n or not 0 <= v < n or u == v:
        raise Graph6Error(f"invalid pair ({u}, {v}) for order {n}")
    if u > v:
        u, v = v, u
    return v * (v - 1) // 2 + u


def edge_count(n: int, mask: int) -> int:
    """Return the number of set edge bits."""

    if n < 0:
        raise Graph6Error("negative graph order")
    return int(mask).bit_count()


def iter_edges(n: int, mask: int) -> Iterator[tuple[int, int]]:
    """Yield edges in graph6 column order."""

    for v in range(1, n):
        for u in range(v):
            if mask & (1 << pair_index(n, u, v)):
                yield u, v


def iter_non_edges(n: int, mask: int) -> Iterator[tuple[int, int]]:
    """Yield non-edges in graph6 column order."""

    for v in range(1, n):
        for u in range(v):
            if not mask & (1 << pair_index(n, u, v)):
                yield u, v


def add_edge(n: int, mask: int, u: int, v: int) -> int:
    return mask | (1 << pair_index(n, u, v))


def remove_edge(n: int, mask: int, u: int, v: int) -> int:
    return mask & ~(1 << pair_index(n, u, v))


def _order_bytes(order: int) -> bytes:
    if not 0 <= order < 1 << 36:
        raise Graph6Error("graph6 order is outside the supported range")
    if order < 63:
        return bytes([order + 63])
    if order < 1 << 18:
        values = [(order >> shift) & 63 for shift in (18, 12, 6, 0)]
        return bytes([126, *[value + 63 for value in values]])
    values = [(order >> shift) & 63 for shift in range(30, -1, -6)]
    return bytes([126, 126, *[value + 63 for value in values]])


def encode_graph6(n: int, mask: int) -> str:
    """Encode an edge mask as a canonical-order graph6 string.

    This only encodes the graph with its current labels.  Use
    :func:`canonicalize` when an isomorphism-class representative is needed.
    """

    if n < 0:
        raise Graph6Error("negative graph order")
    bits: list[int] = []
    for v in range(1, n):
        for u in range(v):
            bits.append(1 if mask & (1 << pair_index(n, u, v)) else 0)
    while len(bits) % 6:
        bits.append(0)
    payload = bytearray(_order_bytes(n))
    for start in range(0, len(bits), 6):
        value = 0
        for bit in bits[start : start + 6]:
            value = (value << 1) | bit
        payload.append(value + 63)
    return payload.decode("ascii")


def decode_graph6(text: str | bytes) -> tuple[int, int]:
    """Decode one graph6 line and return ``(order, edge_mask)``."""

    if isinstance(text, str):
        line = text.strip()
        if line.startswith(">>graph6<<"):
            line = line[len(">>graph6<<") :]
        try:
            raw = line.encode("ascii")
        except UnicodeEncodeError as exc:
            raise Graph6Error("graph6 is not ASCII") from exc
    else:
        raw = bytes(text).strip()
        if raw.startswith(b">>graph6<<"):
            raw = raw[len(b">>graph6<<") :]
    n, offset = _read_order(raw)
    values = _sixbit_values(raw[offset:])
    needed = n * (n - 1) // 2
    if len(values) * 6 < needed:
        raise Graph6Error(
            f"truncated graph6 payload for order {n}: "
            f"need {needed} bits, got {len(values) * 6}"
        )
    mask = 0
    bit_number = 0
    for v in range(1, n):
        for u in range(v):
            value = (values[bit_number // 6] >> (5 - bit_number % 6)) & 1
            if value:
                mask |= 1 << pair_index(n, u, v)
            bit_number += 1
    # A graph6 line may have harmless zero padding only.  Rejecting nonzero
    # padding catches a surprisingly easy malformed-fixture mistake.
    for padding_index in range(needed, len(values) * 6):
        if (values[padding_index // 6] >> (5 - padding_index % 6)) & 1:
            raise Graph6Error("graph6 payload has nonzero padding bits")
    return n, mask


def load_graph6(path: str | Path) -> list[str]:
    """Load nonblank graph6 lines, retaining their file order."""

    lines: list[str] = []
    with Path(path).open("r", encoding="ascii") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith(">>graph6<<") and line == ">>graph6<<":
                continue
            try:
                decode_graph6(line)
            except Graph6Error as exc:
                raise Graph6Error(f"{path}:{line_number}: {exc}") from exc
            lines.append(line)
    return lines


def save_graph6(path: str | Path, lines: Iterable[str]) -> None:
    """Write graph6 lines with exactly one trailing newline."""

    with Path(path).open("w", encoding="ascii", newline="\n") as handle:
        for line in lines:
            handle.write(str(line).rstrip("\n") + "\n")


def adjacency_dict(n: int, mask: int) -> dict[int, list[int]]:
    adjacency = {vertex: [] for vertex in range(n)}
    for u, v in iter_edges(n, mask):
        adjacency[u].append(v)
        adjacency[v].append(u)
    return adjacency


@dataclass(frozen=True)
class CanonicalForm:
    """A graph and both directions of its canonical-label map."""

    g6: str
    n: int
    mask: int
    old_to_new: tuple[int, ...]
    new_to_old: tuple[int, ...]


@lru_cache(maxsize=250_000)
def _canonicalize_cached(n: int, mask: int) -> CanonicalForm:
    if n <= 1:
        identity = tuple(range(n))
        return CanonicalForm(encode_graph6(n, mask), n, mask, identity, identity)
    graph = pynauty.Graph(n, adjacency_dict=adjacency_dict(n, mask))
    # pynauty's documented list is the new-position to old-vertex map.
    new_to_old = tuple(int(value) for value in pynauty.canon_label(graph))
    if len(new_to_old) != n or set(new_to_old) != set(range(n)):
        raise Graph6Error("pynauty returned a non-permutation canonical label")
    old_to_new_list = [0] * n
    for new, old in enumerate(new_to_old):
        old_to_new_list[old] = new
    old_to_new = tuple(old_to_new_list)
    canonical_mask = 0
    for u, v in iter_edges(n, mask):
        canonical_mask |= 1 << pair_index(n, old_to_new[u], old_to_new[v])
    return CanonicalForm(
        encode_graph6(n, canonical_mask),
        n,
        canonical_mask,
        old_to_new,
        new_to_old,
    )


def canonicalize(n: int, mask: int) -> CanonicalForm:
    """Return the nauty-default canonical graph6 form and permutations."""

    return _canonicalize_cached(int(n), int(mask))


def canonical_g6(text: str | bytes) -> str:
    n, mask = decode_graph6(text)
    return canonicalize(n, mask).g6


def is_connected(n: int, mask: int) -> bool:
    if n == 0:
        return False
    adjacency = adjacency_dict(n, mask)
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbour in adjacency[vertex]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return len(seen) == n


def is_biconnected(n: int, mask: int) -> bool:
    """Return the standard connected, no-articulation-point predicate.

    The two-vertex edge is a valid bridge block for L-block purposes.  A
    one-vertex graph and a disconnected graph are not treated as biconnected.
    """

    if n < 2 or not is_connected(n, mask):
        return False
    if n == 2:
        return edge_count(n, mask) == 1
    adjacency = adjacency_dict(n, mask)
    discovery = [-1] * n
    low = [-1] * n
    parent = [-1] * n
    time = 0
    has_articulation = False

    def visit(vertex: int) -> None:
        nonlocal time, has_articulation
        discovery[vertex] = low[vertex] = time
        time += 1
        child_count = 0
        for neighbour in adjacency[vertex]:
            if discovery[neighbour] < 0:
                parent[neighbour] = vertex
                child_count += 1
                visit(neighbour)
                low[vertex] = min(low[vertex], low[neighbour])
                if parent[vertex] < 0 and child_count > 1:
                    has_articulation = True
                if parent[vertex] >= 0 and low[neighbour] >= discovery[vertex]:
                    has_articulation = True
            elif neighbour != parent[vertex]:
                low[vertex] = min(low[vertex], discovery[neighbour])

    visit(0)
    return time == n and not has_articulation


def map_is_injective(mapping: Sequence[int], target_n: int) -> bool:
    return len(set(mapping)) == len(mapping) and all(0 <= value < target_n for value in mapping)


def map_edges(source_n: int, source_mask: int, target_n: int, target_mask: int, mapping: Sequence[int]) -> bool:
    """Check that ``mapping`` sends every source edge to a target edge."""

    if len(mapping) != source_n or not map_is_injective(mapping, target_n):
        return False
    for u, v in iter_edges(source_n, source_mask):
        if not target_mask & (1 << pair_index(target_n, mapping[u], mapping[v])):
            return False
    return True


@lru_cache(maxsize=150_000)
def contains_subgraph(pattern_n: int, pattern_mask: int, host_n: int, host_mask: int) -> bool:
    """Return whether the host contains the pattern as a non-induced subgraph."""

    if pattern_n > host_n or edge_count(pattern_n, pattern_mask) > edge_count(host_n, host_mask):
        return False
    pattern_adjacency = [0] * pattern_n
    host_adjacency = [0] * host_n
    for u, v in iter_edges(pattern_n, pattern_mask):
        pattern_adjacency[u] |= 1 << v
        pattern_adjacency[v] |= 1 << u
    for u, v in iter_edges(host_n, host_mask):
        host_adjacency[u] |= 1 << v
        host_adjacency[v] |= 1 << u
    order = sorted(range(pattern_n), key=lambda vertex: (-pattern_adjacency[vertex].bit_count(), vertex))
    candidates = {
        vertex: [image for image in range(host_n) if host_adjacency[image].bit_count() >= pattern_adjacency[vertex].bit_count()]
        for vertex in range(pattern_n)
    }
    mapping = [-1] * pattern_n
    used = [False] * host_n

    def search(position: int) -> bool:
        if position == pattern_n:
            return True
        vertex = order[position]
        for image in candidates[vertex]:
            if used[image]:
                continue
            compatible = True
            for previous in range(pattern_n):
                previous_image = mapping[previous]
                if previous_image < 0:
                    continue
                if pattern_adjacency[vertex] & (1 << previous):
                    if not host_adjacency[image] & (1 << previous_image):
                        compatible = False
                        break
            if not compatible:
                continue
            mapping[vertex] = image
            used[image] = True
            if search(position + 1):
                return True
            used[image] = False
            mapping[vertex] = -1
        return False

    return search(0)


def graph6_mask(text: str | bytes) -> tuple[str, int, int]:
    """Return ``(canonical_g6, order, canonical_mask)`` for a graph6 line."""

    n, mask = decode_graph6(text)
    form = canonicalize(n, mask)
    return form.g6, form.n, form.mask
