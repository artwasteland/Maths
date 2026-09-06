# Task B2: the filters with witnesses (module filter/)

Build `filter/` per CONTRACT Section 4: a library and CLI (`filter/udfilter`, C, plus a thin
python wrapper) that, for each input graph (canonical graph6, <= 22 vertices), reports:
- "forbidden" with a witness (index into data/forbidden-74.json and the injective vertex map),
  if any of the 74 graphs is a (not necessarily induced) subgraph; else
- "tu" with a witness (index into data/tu-gadgets.json, the vertex map, the pair) if any gadget
  appears as a subgraph with its distinguished pair NON-adjacent in the input; else
- "pass".
Witness format exactly as CONTRACT Section 2. Bitset-based subgraph monomorphism with
degree/neighbourhood pruning; deterministic.

Also deliver `filter/verify-witness.py`: an INDEPENDENT 30-to-60-line script (no shared code
with the library) that, given a graph and a witness line, checks only that the map is injective,
edge-preserving from the pattern into the graph, and (for tu) that the pair is non-adjacent.

Self-checks (run and report): (1) on sources/amp/anc/graph6.txt every graph must be "pass";
(2) plant each forbidden graph into random host graphs and confirm "forbidden" with a witness
that verify-witness.py accepts; (3) plant each gadget with its pair removed and confirm "tu";
plant it with the pair PRESENT and confirm it is NOT reported as tu; (4) reproduce the paper's
Table 1 TU column (after-filter counts 1, 8, 38, 5, 1, 19 for n = 16..21) IF the enumerator's
files exist at research/unit-distance-22/enum/out/<n>-<m>.g6 by the time you finish; otherwise
say so; (5) corrupt one witness byte and confirm verify-witness.py rejects it; (6) throughput:
graphs per second on 21-vertex inputs.
