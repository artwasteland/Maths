#!/usr/bin/env python3
"""Random inputs for the dev-checker and agreement fuzz: sparse G(n, p) graphs (n 5..24) and unit-distance graphs
of grown point sets (fuzz_ud.grown_set) with 1 to 4 random extra edges (mostly not unit-distance graphs any more, so
refutations and forced units through triangle splits are common).

usage: fuzz_random.py OUT.g6 COUNT SEED
"""
import random
import sys

import networkx as nx

from fuzz_ud import grown_set, unit_graph


def main(out, count, seed):
    rng = random.Random(seed)
    lines = []
    while len(lines) < count:
        if rng.random() < 0.4:
            n = rng.randint(5, 24)
            G = nx.gnp_random_graph(n, rng.choice([0.15, 0.2, 0.25, 0.3]), seed=rng.randrange(1 << 30))
        else:
            n = rng.randint(7, 22)
            G = unit_graph(grown_set(rng, n))
            non = [(u, v) for u in range(n) for v in range(u + 1, n) if not G.has_edge(u, v)]
            for e in rng.sample(non, min(len(non), rng.randint(1, 4))):
                G.add_edge(*e)
        lines.append(nx.to_graph6_bytes(G, header=False).decode().strip())
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
