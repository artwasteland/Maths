# Task B3: the proof-producing embedder (module embed/)

Build `embed/` per CONTRACT Section 5: a python program (`embed/udembed.py`, using
~/tools/pyenv-maths/bin/python; exact arithmetic via sympy number fields or python-flint if you
install it into the venv; you may also use mpmath intervals for DISCOVERY only) implementing
the paper's Section 4 algorithm: identify R^2 with C, rhombus constraints from every 4-cycle
(L0), vertex collision (L1a), forced proportional edges with |w| != 1 (L1b), forced unit-modulus
non-edge (L2, adds the edge), three linearly dependent edges (L3, Lemma 4 branch into two
linear constraints), greedy priority L1 > L2 > L3, and, when no move applies, a randomised
search for an embedding in some ker A_s (random unit-circle constraints on independent edge
pairs until the kernel is 2-dimensional), retried a bounded number of times.

Output per graph, exactly per CONTRACT Sections 2, 5 and 6: "embedded" with exact coordinates
in an explicit real number field (minimal polynomial of the primitive element, isolating
interval, coordinates as rational polynomials), or "refuted" with a finite proof tree (every node
records the graph, the exact linear constraint system, the move and its exact witness; L3 nodes
have two children), or "unknown". The trusted verification of an "embedded" verdict must be a
separate function that only checks distinctness and the 61 (or m) squared distances exactly.

Self-checks (run and report): (1) all 56 graphs in sources/amp/anc/graph6.txt embed, with exact
coordinates verified exactly; (2) K4, K_{2,3} and the other 72 forbidden graphs are refuted (or
report which are "unknown": the paper says some small graphs come back unknown, so be honest);
(3) the Moser spindle and the 6-vertex gadget-1 host embed; (4) each of the six TU gadgets: the
algorithm, run on the gadget with its pair as a NON-edge, must fire L2 and add the pair (this is
the mechanised half of the TU lemma; report for each gadget whether L2 fires and after which
moves); (5) plant a false "embedded" certificate (one coordinate perturbed) and confirm the
exact verifier rejects it; (6) timing per graph on 21-vertex inputs.

State clearly in REPORT.md which arithmetic every trusted step uses. A float anywhere in a
trusted step is a defect, not a shortcut.
