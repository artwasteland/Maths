# Order-eleven fixtures

`lattice11.json`, `tree11.json` and `tu11.json` are retained ordinary records
from the architect's measured general-search pilot, `/tmp/gp11-architect/`.
They are self-contained; tests do not require that scratch directory.
Their proofs are independently replayed, never inferred from the pilot report.
The tree and TU files intentionally give different certificate types for the
same graph; they are checked in separate runs to respect duplicate coverage.

`selftest.py` also constructs an exact rational eleven-vertex path and lifts
the frozen GP-10 K4 polynomial identity by isolated vertices, mapping every
variable and graph label. It feeds the resulting ordinary certificates to the
unmodified arithmetic routines through the new profile.

The ten-vertex block red has all of the forbidden block's edges in its host.
An injective identity map is explicitly checked before testing block evidence.
Its positive deletes one edge of that block, keeping it biconnected; the red
restores just that edge and must reject at `block_forbidden`.
Another positive is an edge deletion of a biconnected eleven-vertex graph,
leaving a ten-cycle and a bridge.

Every red asserts its exact rule name. Real positive evidence is rechecked
after mutation, with original counts, lists or partitions required to return.

`minimality11.jsonl` retains the tree-refuted parent and sixteen exact embeddings
from `tools/make_minimality_fixture.py`, four seconds and 200000 nodes per deletion,
using lattice18/lattice36/lattice30/constructive only.
The checker reconstructs every edge deletion and verifies this bundle independently.
The test also creates an UNKNOWN variant and a real refuted supergraph pointer;
neither changes the retained evidence.

`named11/` retains the local general-search records, input, provenance and stats.
Both graphs were found by lattice18; coordinates were not read from AMP.
