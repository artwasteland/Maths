# Task B4: the independent checker (module check/)

You are the adversary of the other builders and you must NOT read their code: do not open
research/unit-distance-22/enum/, filter/, embed/ or enum2/. Read only CONTRACT.md, the paper,
and the data files. Build `check/udcheck.py` (python, ~/tools/pyenv-maths/bin/python) that
replays a certificate file (CONTRACT Section 2 JSON lines) for a (22, 61) list, trusting nothing
but the graph6 strings and the witness objects:
- "forbidden": re-verify the injective edge-preserving map against data/forbidden-74.json;
- "tu": re-verify the map, that the pair is non-adjacent in the graph, and that the gadget index
  is one of the six in data/tu-gadgets.json;
- "embedded": re-verify exact coordinates (minimal polynomial, isolating interval, all squared
  distances exactly 1, all points distinct) with your OWN exact arithmetic;
- "refuted": re-verify every node of the proof tree: the constraint systems are consistent with
  the moves claimed, each L1a/L1b/L2 witness is a genuine consequence of the exact linear
  algebra at that node, each L3 node's two children cover the case split per the paper's
  Lemma 4 (state the lemma in your code comments in your own words and verify its algebraic
  content on the node), and every leaf is a contradiction;
- "unknown": counted and listed.
Also verify the enumeration manifest chain (CONTRACT Section 6.2(a)): every shard's inputs hash
matches a parent file, the ranges tile each parent file exactly, and the software hashes are
consistent.

Deliver also `check/PROOFS.md`: explicit written proofs, in your own words with the geometric
reasoning (rhombi and equilateral triangles), that each of the six TU gadgets forces its pair to
unit distance in every unit-distance embedding. Where you cannot complete a proof, say so; a
gap here is a gap in the whole programme and must be visible.

Self-checks: construct small synthetic certificates by hand for K4 (refuted), the Moser spindle
(embedded, exact coordinates in Q(sqrt 3, sqrt 11) or another explicit field), and a planted
forbidden witness; then corrupt each in one byte and confirm rejection. Report every check and
how it was made to fail.
