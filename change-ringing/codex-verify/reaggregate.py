#!/usr/bin/env python3
"""Independently re-aggregate the n=5, L=21 distributed checkpoint."""

from __future__ import annotations

import argparse
import itertools
import re
from pathlib import Path


N_BELLS = 5
MAX_L = 21
PREFIX_K = 6
HEADER_RE = re.compile(
    r"^H n=(\d+) graph=([0-9a-f]+) maxL=(\d+) K=(\d+) sym=(\d+) jobs=(\d+)$"
)
JOB_HEAD_RE = re.compile(r"^J\s+(-?\d+)\s+(-?\d+)(.*)$")
PAIR_RE = re.compile(r"\s+(\d+),(\d+)")


def build_graph(n: int) -> tuple[list[tuple[int, ...]], list[list[int]]]:
    """Build the graph directly from permutations and legal swap masks."""
    perms = list(itertools.permutations(range(n)))
    rank = {p: i for i, p in enumerate(perms)}
    masks = [
        mask
        for mask in range(1, 1 << (n - 1))
        if not (mask & (mask << 1))
    ]
    graph: list[list[int]] = []
    for p in perms:
        neighbours = []
        for mask in masks:
            q = list(p)
            for i in range(n - 1):
                if mask & (1 << i):
                    q[i], q[i + 1] = q[i + 1], q[i]
            neighbours.append(rank[tuple(q)])
        graph.append(sorted(neighbours))
    return perms, graph


def phi_map(perms: list[tuple[int, ...]]) -> list[int]:
    n = len(perms[0])
    rank = {p: i for i, p in enumerate(perms)}
    return [rank[tuple(n - 1 - p[n - 1 - i] for i in range(n))] for p in perms]


def enumerate_prefixes(
    graph: list[list[int]], phi: list[int], k: int
) -> list[tuple[tuple[int, ...], int]]:
    """Enumerate canonical simple prefixes in deterministic graph DFS order."""
    result: list[tuple[tuple[int, ...], int]] = []
    current = [0]
    visited = {0}

    def visit(v: int) -> None:
        if len(current) == k:
            image = tuple(phi[x] for x in current)
            prefix = tuple(current)
            if prefix <= image:
                result.append((prefix, 1 if prefix == image else 2))
            return
        for u in graph[v]:
            if u not in visited:
                visited.add(u)
                current.append(u)
                visit(u)
                current.pop()
                visited.remove(u)

    visit(0)
    return result


def count_short_levels(graph: list[list[int]], max_l: int) -> tuple[list[int], list[int]]:
    """Count all simple paths through max_l without symmetry reduction."""
    paths = [0] * (max_l + 1)
    cyclic = [0] * (max_l + 1)
    paths[1] = cyclic[1] = 1
    rounds_neighbours = set(graph[0])
    visited = {0}

    def walk(v: int, length: int) -> None:
        if length == max_l:
            return
        for u in graph[v]:
            if u in visited:
                continue
            next_length = length + 1
            paths[next_length] += 1
            cyclic[next_length] += u in rounds_neighbours
            visited.add(u)
            walk(u, next_length)
            visited.remove(u)

    walk(0, 1)
    return paths, cyclic


def parse_job_line(line: str, pair_count: int) -> tuple[int, int, list[tuple[int, int]]] | None:
    """Match count.c aggregation: accept a line if its first pair_count pairs parse."""
    head = JOB_HEAD_RE.match(line.rstrip("\n"))
    if not head:
        return None
    job_id, weight = int(head.group(1)), int(head.group(2))
    rest = head.group(3)
    pairs: list[tuple[int, int]] = []
    pos = 0
    for _ in range(pair_count):
        match = PAIR_RE.match(rest, pos)
        if not match:
            return None
        pairs.append((int(match.group(1)), int(match.group(2))))
        pos = match.end()
    return job_id, weight, pairs


def read_checkpoint(
    path: Path, expected_weights: list[int]
) -> tuple[list[int], list[int], dict[str, int | str]]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines:
        raise ValueError("empty checkpoint")
    header_match = HEADER_RE.fullmatch(lines[0])
    if not header_match:
        raise ValueError(f"invalid checkpoint header: {lines[0]!r}")
    n, graph_hash, max_l, k, sym, declared_jobs = header_match.groups()
    metadata: dict[str, int | str] = {
        "n": int(n), "graph_hash": graph_hash, "max_l": int(max_l),
        "k": int(k), "sym": int(sym), "declared_jobs": int(declared_jobs),
        "physical_job_lines": len(lines) - 1,
    }
    wanted = (N_BELLS, MAX_L, PREFIX_K, 1, len(expected_weights))
    got = (int(n), int(max_l), int(k), int(sym), int(declared_jobs))
    if got != wanted:
        raise ValueError(f"checkpoint metadata mismatch: got {got}, expected {wanted}")

    seen: dict[int, tuple[int, list[tuple[int, int]]]] = {}
    duplicate_lines = malformed_lines = out_of_range_lines = 0
    weight_mismatches: list[tuple[int, int, int]] = []
    for line in lines[1:]:
        parsed = parse_job_line(line, MAX_L - PREFIX_K)
        if parsed is None:
            malformed_lines += 1
            continue
        job_id, weight, pairs = parsed
        if not 0 <= job_id < len(expected_weights):
            out_of_range_lines += 1
            continue
        if job_id in seen:
            duplicate_lines += 1
            continue
        if weight != expected_weights[job_id]:
            weight_mismatches.append((job_id, weight, expected_weights[job_id]))
        seen[job_id] = (weight, pairs)

    missing = sorted(set(range(len(expected_weights))) - seen.keys())
    metadata.update(
        unique_jobs=len(seen), duplicate_lines=duplicate_lines,
        malformed_lines=malformed_lines, out_of_range_lines=out_of_range_lines,
        missing_jobs=len(missing), weight_mismatches=len(weight_mismatches),
    )
    if missing or out_of_range_lines or malformed_lines or weight_mismatches:
        raise ValueError(
            "checkpoint job-set failure: "
            f"missing={missing[:20]}, out_of_range={out_of_range_lines}, "
            f"malformed={malformed_lines}, weight_mismatches={weight_mismatches[:20]}"
        )

    paths = [0] * (MAX_L + 1)
    cyclic = [0] * (MAX_L + 1)
    for job_id in range(len(expected_weights)):
        stored_weight, pairs = seen[job_id]
        for level, (path_count, cyclic_count) in enumerate(pairs, PREFIX_K + 1):
            paths[level] += stored_weight * path_count
            cyclic[level] += stored_weight * cyclic_count
    return paths, cyclic, metadata


def read_claimed_totals(path: Path) -> dict[int, tuple[int, int, int]]:
    result = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("#"):
            continue
        level, paths, cyclic, noncappable = map(int, line.split())
        result[level] = (paths, cyclic, noncappable)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=Path("../runs/n5-L21.ck"))
    parser.add_argument("--claimed", type=Path, default=Path("../runs/n5-L21.out"))
    args = parser.parse_args()

    perms, graph = build_graph(N_BELLS)
    phi = phi_map(perms)
    prefixes = enumerate_prefixes(graph, phi, PREFIX_K)
    expected_weights = [weight for _, weight in prefixes]
    short_paths, short_cyclic = count_short_levels(graph, PREFIX_K)
    deep_paths, deep_cyclic, metadata = read_checkpoint(args.checkpoint, expected_weights)
    paths = [0] * (MAX_L + 1)
    cyclic = [0] * (MAX_L + 1)
    for level in range(1, PREFIX_K + 1):
        paths[level], cyclic[level] = short_paths[level], short_cyclic[level]
    for level in range(PREFIX_K + 1, MAX_L + 1):
        paths[level], cyclic[level] = deep_paths[level], deep_cyclic[level]

    claimed = read_claimed_totals(args.claimed)
    print(
        f"graph_vertices={len(graph)} degree={len(graph[0])} "
        f"expected_jobs={len(prefixes)} weight1={expected_weights.count(1)} "
        f"weight2={expected_weights.count(2)}"
    )
    print(" ".join(f"{key}={value}" for key, value in metadata.items()))
    print("L path cyclic noncappable result")
    failures = 0
    for level in range(1, MAX_L + 1):
        row = (paths[level], cyclic[level], paths[level] - cyclic[level] if level > 1 else 0)
        status = "PASS" if claimed.get(level) == row else "FAIL"
        failures += status == "FAIL"
        print(level, *row, status)
    print(f"comparison={'PASS' if failures == 0 else 'FAIL'} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
