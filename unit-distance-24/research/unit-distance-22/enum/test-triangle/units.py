#!/usr/bin/env python3
"""Unit-test graphs for udtriangle (RHOMBUS-SPEC.md Section 4), as graph6 with their expected verdicts.

usage: units.py OUT.tsv      (lines: name <TAB> graph6 <TAB> expected verdict)
"""
import itertools
import json
import sys
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data"


def g6(G):
    G = nx.convert_node_labels_to_integers(G, ordering="sorted")
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def lattice_patch(radius):
    """The triangular lattice's points a + b w (w = e^(i pi/3)) with max(|a|, |b|, |a + b|) <= radius, adjacent
    exactly at distance 1: a faithful unit-distance graph (every unit distance is an edge)."""
    pts = [(a, b) for a in range(-radius, radius + 1) for b in range(-radius, radius + 1) if abs(a + b) <= radius]
    G = nx.Graph()
    G.add_nodes_from(range(len(pts)))
    steps = {(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)}
    for i, j in itertools.combinations(range(len(pts)), 2):
        if (pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]) in steps:
            G.add_edge(i, j)
    return G


def cases():
    out = [("K4", nx.complete_graph(4), "refuted"),
           ("K_{1,1,3}", nx.complete_multipartite_graph(1, 1, 3), "refuted")]
    moser = nx.Graph([(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (0, 4), (0, 5), (4, 5), (4, 6), (5, 6), (3, 6)])
    out.append(("Moser spindle", moser, "pass"))
    out.append(("W6 wheel", nx.wheel_graph(7), "pass"))
    out.append(("triangular lattice patch, hexagon of radius 2 (19 points, 42 edges)", lattice_patch(2), "pass"))
    out.append(("triangular lattice patch, 3x3 rhombic block", nx.convert_node_labels_to_integers(
        nx.Graph([((a, b), (a + da, b + db)) for a in range(3) for b in range(3) for da, db in ((1, 0), (0, 1), (-1, 1))
                  if 0 <= a + da < 3 and 0 <= b + db < 3])), "pass"))
    out.append(("two triangles on an edge (unit rhombus with its short diagonal)",
                nx.Graph([(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]), "pass"))
    for i, gd in enumerate(json.loads((DATA / "tu-gadgets.json").read_text())):
        G = nx.Graph()
        G.add_nodes_from(range(gd["n"]))
        G.add_edges_from(map(tuple, gd["edges"]))
        out.append((f"TU gadget {i} (pair {gd['pair'][0]},{gd['pair'][1]})", G, "tu"))
    return out


if __name__ == "__main__":
    with open(sys.argv[1], "w") as f:
        for name, G, want in cases():
            f.write(f"{name}\t{g6(G)}\t{want}\n")
