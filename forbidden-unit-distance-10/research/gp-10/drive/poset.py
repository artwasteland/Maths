"""The fixed-vertex edge-addition poset for a GP-10 input set.

The input is a set of canonical graph6 strings on one vertex order.  For every
edge deletion of every input graph, this module canonicalises the deletion and
keeps the relation when the child is also in the input.  Deletion is the
cheaper equivalent of trying every non-edge addition, and it gives the map in
the direction needed by both pointer types:

``child canonical vertex -> parent canonical vertex``.

The relation also records the added edge in child labels.  Thus the resulting
JSON is an auditable canonical edge-addition graph, not merely a reachability
table.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from .graph6 import (
        Graph6Error,
        canonicalize,
        decode_graph6,
        edge_count,
        encode_graph6,
        iter_edges,
        is_biconnected,
        map_edges,
        map_is_injective,
        pair_index,
        remove_edge,
        load_graph6,
        save_graph6,
    )
except ImportError:
    from graph6 import (  # type: ignore
        Graph6Error,
        canonicalize,
        decode_graph6,
        edge_count,
        encode_graph6,
        iter_edges,
        is_biconnected,
        map_edges,
        map_is_injective,
        pair_index,
        remove_edge,
        load_graph6,
        save_graph6,
    )


@dataclass(frozen=True)
class Relation:
    """One cover relation, with the child-to-parent vertex map."""

    parent: str
    child: str
    map: tuple[int, ...]
    edge: tuple[int, int]

    def as_json(self) -> dict[str, object]:
        return {
            "parent": self.parent,
            "child": self.child,
            "map": list(self.map),
            "edge": list(self.edge),
        }

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> "Relation":
        try:
            parent = str(value["parent"])
            child = str(value["child"])
            mapping = tuple(int(item) for item in value["map"])  # type: ignore[index]
            edge_values = tuple(int(item) for item in value["edge"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"malformed poset relation: {value!r}") from exc
        if len(edge_values) != 2:
            raise ValueError(f"relation edge is not a pair: {value!r}")
        return cls(parent, child, mapping, (min(edge_values), max(edge_values)))


@dataclass
class Poset:
    """An in-memory edge-addition poset."""

    vertices: tuple[str, ...]
    n: int
    masks: dict[str, int]
    children: dict[str, tuple[Relation, ...]]
    parents: dict[str, tuple[Relation, ...]]
    deletion_edges: dict[str, tuple[tuple[int, int], ...]]
    stats: dict[str, object]

    def relations(self) -> tuple[Relation, ...]:
        return tuple(
            relation
            for parent in self.vertices
            for relation in self.children.get(parent, ())
        )

    def edge_count(self, g6: str) -> int:
        return edge_count(self.n, self.masks[g6])

    def maximal(self, active: Iterable[str] | None = None) -> list[str]:
        """Return graphs with no edge-addition parent in ``active``."""

        active_set = set(self.vertices if active is None else active)
        return sorted(
            graph
            for graph in active_set
            if not any(relation.parent in active_set for relation in self.parents.get(graph, ()))
        )

    def minimal(self, active: Iterable[str] | None = None) -> list[str]:
        """Return graphs with no one-edge-deletion child in ``active``."""

        active_set = set(self.vertices if active is None else active)
        return sorted(
            graph
            for graph in active_set
            if not any(relation.child in active_set for relation in self.children.get(graph, ()))
        )

    def relation(self, parent: str, child: str) -> Relation | None:
        for item in self.children.get(parent, ()):
            if item.child == child:
                return item
        return None

    def verify_relation(self, relation: Relation) -> tuple[bool, str]:
        if relation.parent not in self.masks or relation.child not in self.masks:
            return False, "relation endpoint is outside the input set"
        parent_mask = self.masks[relation.parent]
        child_mask = self.masks[relation.child]
        if edge_count(self.n, parent_mask) <= edge_count(self.n, child_mask):
            return False, "parent does not have strictly more edges"
        if len(relation.map) != self.n:
            return False, "relation map has the wrong length"
        if (
            len(relation.edge) != 2
            or relation.edge[0] == relation.edge[1]
            or not all(0 <= value < self.n for value in relation.edge)
        ):
            return False, "relation added edge is not a valid pair"
        if not map_is_injective(relation.map, self.n):
            return False, "relation map is not injective"
        if not map_edges(self.n, child_mask, self.n, parent_mask, relation.map):
            return False, "relation map is not edge-preserving"
        mapped_edge = tuple(sorted((relation.map[relation.edge[0]], relation.map[relation.edge[1]])))
        if not (parent_mask & (1 << pair_index(self.n, *mapped_edge))):
            return False, "recorded added edge is absent from the parent"
        if child_mask & (1 << pair_index(self.n, *relation.edge)):
            return False, "recorded added edge is present in the child"
        return True, "ok"

    def as_json(self) -> dict[str, object]:
        return {
            "schema": 1,
            "n": self.n,
            "vertices": list(self.vertices),
            "relations": [relation.as_json() for relation in self.relations()],
            "deletion_edges": {
                graph: [list(edge) for edge in edges]
                for graph, edges in self.deletion_edges.items()
            },
            "stats": self.stats,
        }

    def write(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.as_json(), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )


def _normalise_input(lines: Iterable[str]) -> tuple[tuple[str, ...], int, dict[str, int]]:
    vertices = tuple(str(line).strip() for line in lines if str(line).strip())
    if not vertices:
        raise ValueError("the poset input is empty")
    masks: dict[str, int] = {}
    order: int | None = None
    for graph in vertices:
        n, mask = decode_graph6(graph)
        canonical = canonicalize(n, mask).g6
        if canonical != graph:
            raise ValueError(f"input graph is not nauty-canonical: {graph} -> {canonical}")
        if order is None:
            order = n
        elif n != order:
            raise ValueError("all poset graphs must have the same vertex count")
        if graph in masks:
            raise ValueError(f"duplicate input graph: {graph}")
        masks[graph] = mask
    assert order is not None
    return vertices, order, masks


def build_poset(lines: Iterable[str], progress_every: int = 0) -> Poset:
    """Build the canonical edge-addition graph and its statistics."""

    started = time.perf_counter()
    vertices, n, masks = _normalise_input(lines)
    vertex_set = set(vertices)
    children_lists: dict[str, list[Relation]] = {graph: [] for graph in vertices}
    parents_lists: dict[str, list[Relation]] = {graph: [] for graph in vertices}
    deletion_edges: dict[str, list[tuple[int, int]]] = {graph: [] for graph in vertices}
    deletion_attempts = 0
    hits = 0
    unique_pairs: set[tuple[str, str]] = set()

    for index, parent in enumerate(vertices, 1):
        parent_mask = masks[parent]
        for u, v in iter_edges(n, parent_mask):
            deletion_attempts += 1
            deletion_edges[parent].append((u, v))
            child_mask_raw = remove_edge(n, parent_mask, u, v)
            child_form = canonicalize(n, child_mask_raw)
            child = child_form.g6
            if child not in vertex_set:
                continue
            hits += 1
            # child_form.new_to_old maps child canonical labels to the raw
            # parent labels.  This is exactly the R-pointer map direction.
            child_to_parent = child_form.new_to_old
            parent_to_child = child_form.old_to_new
            child_edge = tuple(sorted((parent_to_child[u], parent_to_child[v])))
            relation = Relation(parent, child, child_to_parent, child_edge)
            key = (parent, child)
            if key in unique_pairs:
                # An automorphism can make two deleted parent edges produce
                # one cover pair.  Keep the lexicographically stable witness.
                for position, previous in enumerate(children_lists[parent]):
                    if previous.child == child and (
                        (relation.map, relation.edge) < (previous.map, previous.edge)
                    ):
                        children_lists[parent][position] = relation
                        parents_lists[child] = [
                            relation if item.parent == parent else item
                            for item in parents_lists[child]
                        ]
                        break
                continue
            unique_pairs.add(key)
            children_lists[parent].append(relation)
            parents_lists[child].append(relation)
        if progress_every and index % progress_every == 0:
            elapsed = time.perf_counter() - started
            print(
                json.dumps(
                    {
                        "event": "poset-progress",
                        "processed": index,
                        "total": len(vertices),
                        "relations": len(unique_pairs),
                        "seconds": round(elapsed, 3),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    for graph in vertices:
        children_lists[graph].sort(key=lambda item: (item.child, item.map, item.edge))
        parents_lists[graph].sort(key=lambda item: (item.parent, item.map, item.edge))
        deletion_edges[graph].sort()

    maximal_count = sum(not parents_lists[graph] for graph in vertices)
    minimal_count = sum(not children_lists[graph] for graph in vertices)
    relation_count = len(unique_pairs)
    elapsed = time.perf_counter() - started
    possible_additions = sum(
        n * (n - 1) // 2 - edge_count(n, masks[graph]) for graph in vertices
    )
    stats: dict[str, object] = {
        "n": n,
        "input_count": len(vertices),
        "deletion_attempts": deletion_attempts,
        "canonical_edge_addition_candidates": possible_additions,
        "canonical_edge_addition_hits": hits,
        "relation_count": relation_count,
        "canonical_edge_addition_graph_vertices": len(vertices),
        "canonical_edge_addition_graph_edges": relation_count,
        "maximal_count": maximal_count,
        "edge_maximal_count": maximal_count,
        "minimal_count_by_poset": minimal_count,
        "edge_minimal_count": minimal_count,
        "edge_count_min": min(edge_count(n, masks[graph]) for graph in vertices),
        "edge_count_max": max(edge_count(n, masks[graph]) for graph in vertices),
        "build_seconds": elapsed,
    }
    poset = Poset(
        vertices,
        n,
        masks,
        {graph: tuple(children_lists[graph]) for graph in vertices},
        {graph: tuple(parents_lists[graph]) for graph in vertices},
        {graph: tuple(deletion_edges[graph]) for graph in vertices},
        stats,
    )
    for relation in poset.relations():
        valid, reason = poset.verify_relation(relation)
        if not valid:
            raise AssertionError(f"internal poset relation failed: {reason}: {relation}")
    return poset


def load_poset(path: str | Path) -> Poset:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != 1:
        raise ValueError(f"unsupported poset schema: {value.get('schema')!r}")
    vertices, n, masks = _normalise_input(value["vertices"])
    if int(value["n"]) != n:
        raise ValueError("poset order does not match its vertex list")
    children_lists: dict[str, list[Relation]] = {graph: [] for graph in vertices}
    parents_lists: dict[str, list[Relation]] = {graph: [] for graph in vertices}
    for raw_relation in value.get("relations", []):
        relation = Relation.from_json(raw_relation)
        valid, reason = Poset(
            vertices,
            n,
            masks,
            children_lists,
            parents_lists,
            {},
            {},
        ).verify_relation(relation)
        if not valid:
            raise ValueError(f"invalid relation in {path}: {reason}")
        children_lists[relation.parent].append(relation)
        parents_lists[relation.child].append(relation)
    raw_deletions = value.get("deletion_edges", {})
    deletion_edges = {
        graph: tuple(tuple(int(item) for item in edge) for edge in raw_deletions.get(graph, []))
        for graph in vertices
    }
    for graph in vertices:
        children_lists[graph].sort(key=lambda item: (item.child, item.map, item.edge))
        parents_lists[graph].sort(key=lambda item: (item.parent, item.map, item.edge))
    stats = dict(value.get("stats", {}))
    stats.setdefault("relation_count", sum(len(items) for items in children_lists.values()))
    stats.setdefault("input_count", len(vertices))
    stats.setdefault("n", n)
    return Poset(
        vertices,
        n,
        masks,
        {graph: tuple(children_lists[graph]) for graph in vertices},
        {graph: tuple(parents_lists[graph]) for graph in vertices},
        deletion_edges,
        stats,
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="canonical graph6 input")
    parser.add_argument("--out", type=Path, required=True, help="poset JSON output")
    parser.add_argument("--stats", type=Path, help="optional statistics JSON")
    parser.add_argument("--progress-every", type=int, default=0)
    args = parser.parse_args()
    poset = build_poset(load_graph6(args.input), progress_every=args.progress_every)
    poset.write(args.out)
    if args.stats:
        args.stats.parent.mkdir(parents=True, exist_ok=True)
        args.stats.write_text(json.dumps(poset.stats, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(poset.stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
