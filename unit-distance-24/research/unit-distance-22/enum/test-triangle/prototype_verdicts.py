#!/usr/bin/env python3
"""Per-graph verdicts of the prototypes (research/unit-distance-23/tools/rhombus_probe.py and triangle_probe.py),
unchanged, for the agreement test: one line per input graph, "<rhombus verdict> <triangle verdict>" where the
triangle verdict is "-" when the rhombus rule already flags the graph (as in the prototype's own driver).

usage: prototype_verdicts.py IN.g6 OUT.txt
"""
import sys
from pathlib import Path

import networkx as nx

TOOLS = Path(__file__).resolve().parents[3] / "unit-distance-23" / "tools"
sys.path.insert(0, str(TOOLS))
from rhombus_probe import probe            # noqa: E402
from triangle_probe import triangle_verdict  # noqa: E402

with open(sys.argv[1]) as fin, open(sys.argv[2], "w") as fout:
    for line in fin:
        g6 = line.strip()
        if not g6:
            continue
        G = nx.from_graph6_bytes(g6.encode())
        r = probe(G)[0]
        t = triangle_verdict(G) if r == "none" else "-"
        fout.write(f"{r} {t}\n")
        fout.flush()
