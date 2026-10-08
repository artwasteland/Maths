#!/usr/bin/env python3
"""Check that the JSON edge lists and frozen graph6 pattern order agree."""

import argparse
import json
from collections import Counter


def graph6(value):
    pos = 10 if value.startswith(">>graph6<<") else 0
    if pos >= len(value) or not 63 <= ord(value[pos]) <= 125:
        raise ValueError("unsupported graph6 order")
    n = ord(value[pos]) - 63
    pos += 1
    edges = set()
    bit = 0
    total = n * (n - 1) // 2
    for _ in range((total + 5) // 6):
        chunk = ord(value[pos]) - 63
        pos += 1
        for shift in range(5, -1, -1):
            if bit == total:
                break
            if chunk & (1 << shift):
                seen = 0
                for v in range(1, n):
                    width = v
                    if bit < seen + width:
                        edges.add((bit - seen, v))
                        break
                    seen += width
            bit += 1
    return n, edges


def same_graph(json_edges, graph6_edges, n):
    json_adj = [0] * n
    g6_adj = [0] * n
    for u, v in json_edges:
        json_adj[u] |= 1 << v
        json_adj[v] |= 1 << u
    for u, v in graph6_edges:
        g6_adj[u] |= 1 << v
        g6_adj[v] |= 1 << u
    json_degree = [row.bit_count() for row in json_adj]
    g6_degree = [row.bit_count() for row in g6_adj]
    if sorted(json_degree) != sorted(g6_degree):
        return False
    mapping = [-1] * n
    used = 0

    def search(done, used_hosts):
        if done == n:
            return True
        best = None
        best_candidates = []
        for u in range(n):
            if mapping[u] >= 0:
                continue
            candidates = [v for v in range(n) if not used_hosts & (1 << v)
                          and g6_degree[v] == json_degree[u]
                          and all(mapping[w] < 0 or
                                  bool(json_adj[u] & (1 << w)) ==
                                  bool(g6_adj[v] & (1 << mapping[w]))
                                  for w in range(n) if mapping[w] >= 0)]
            if best is None or len(candidates) < len(best_candidates):
                best = u
                best_candidates = candidates
        for v in best_candidates:
            mapping[best] = v
            if search(done + 1, used_hosts | (1 << v)):
                return True
            mapping[best] = -1
        return False

    return search(0, used)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    parser.add_argument("g6_path")
    args = parser.parse_args()
    with open(args.json_path, encoding="utf-8") as source:
        edge_lists = json.load(source)
    g6_values = []
    with open(args.g6_path, encoding="ascii") as source:
        for raw in source:
            value = raw.strip()
            if value and not value.startswith(">>graph6<<"):
                g6_values.append(value)
    if len(edge_lists) != len(g6_values):
        raise SystemExit(f"REJECT: JSON count {len(edge_lists)} != graph6 count {len(g6_values)}")
    sizes = Counter()
    for index, (edges, value) in enumerate(zip(edge_lists, g6_values)):
        json_edges = {tuple(sorted(edge)) for edge in edges}
        vertices = {vertex for edge in json_edges for vertex in edge}
        n, g6_edges = graph6(value)
        if vertices and max(vertices) >= n:
            raise SystemExit(f"REJECT: vertex outside graph6 order at member {index}")
        if not same_graph(json_edges, g6_edges, n):
            raise SystemExit(f"REJECT: edge mismatch at member {index}")
        sizes[n] += 1
    print(f"patterns={len(g6_values)}")
    for n in sorted(sizes):
        print(f"vertices_{n}={sizes[n]}")
    print("MATCH JSON_graph6_order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
