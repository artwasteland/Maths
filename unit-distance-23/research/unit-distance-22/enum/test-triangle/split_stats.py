#!/usr/bin/env python3
"""Shape of the emitted case trees: how many splits share an edge with a triangle split above them (the spec's
suggested preference; expected never, since two triangles on an edge x-y with apexes t, t' span the 4-cycle
x-t-y-t', whose rhombus row fixes the second orientation once the first is split), how many splits share only a
vertex or nothing, and mean nodes among trees that split at all.

usage: split_stats.py VERDICTS.jsonl [...]
"""
import json
import sys


def walk(node, path, acc):
    if "leaf" in node:
        return
    t = tuple(node["split"])
    edges = {frozenset(e) for e in ((t[0], t[1]), (t[0], t[2]), (t[1], t[2]))}
    kind = "none"
    for u in path:
        ue = {frozenset(e) for e in ((u[0], u[1]), (u[0], u[2]), (u[1], u[2]))}
        if edges & ue:
            kind = "edge"
            break
        if set(t) & set(u):
            kind = "vertex"
    acc[kind] = acc.get(kind, 0) + 1
    walk(node["plus"], path + [t], acc)
    walk(node["minus"], path + [t], acc)


def count(node):
    return 1 if "leaf" in node else 1 + count(node["plus"]) + count(node["minus"])


for path in sys.argv[1:]:
    acc, split_trees, split_nodes = {}, 0, 0
    for line in open(path):
        rec = json.loads(line)
        if rec["verdict"] == "pass":
            continue
        tree = rec["witness"]["tri"]["tree"]
        if "split" in tree:
            split_trees += 1
            split_nodes += count(tree)
        walk(tree, [], acc)
    mean = split_nodes / split_trees if split_trees else 0
    print(f"{path}: splits sharing an edge with an ancestor split {acc.get('edge', 0)}, sharing only a vertex "
          f"{acc.get('vertex', 0)}, disjoint {acc.get('none', 0)}; trees with splits {split_trees}, mean nodes {mean:.1f}")
