# Independent check of the cube split (GAP, 2026-09-06)

Prompted by a reader's objection relayed by the human on 2026-09-06: the DRAT chain proves the
cube CNFs unsatisfiable, but if the orbit decomposition behind the cube split were wrong, every
checker downstream would still say VERIFIED of the wrong formula. The two claims that carry the
split are therefore checked here in GAP 4.12.1, built from the definition alone (nothing is read
from `exist.py`; its own listing is used only to name the representatives it fixed and, in the
second check, to dump the group it used, so that GAP can compare).

## Claim 1: the orbit decomposition (`orbits.g`, log `orbits.log`)

Frame: point 0's row fixed to its canonical form (blocks {0,1,2}, {0,3,4}, ..., the remaining
points its leave); G1 = the stabiliser in Sym(points 3..n-1) of the row-0 partition
M0 = {{3,4},{5,6},...} as a set of sets; a row-1 configuration = point 1's blocks other than
{0,1,2}, i.e. a matching of the required size on the remaining points avoiding every M0 pair.

- **(15,32):** |G1| = 46,080; 6,040 configurations; exactly 4 orbits of sizes 120, 1440, 640,
  3840; the four representatives the cube CNFs fix lie one per orbit, with stabilisers of order
  384, 32, 72, 12. A transversal: every configuration lies in the orbit of exactly one cube.
- **(14,27):** |G1| = 3,840; 6,584 configurations; exactly 7 orbits of sizes 120, 160, 960, 640,
  480, 384, 3840; the seven representatives lie one per orbit, with stabilisers of order 32,
  24, 4, 6, 8, 10, 1.

By hand, for (15,32): M ∪ M0 is a 2-regular graph on 12 points, a disjoint union of even
cycles of length at least 4, and G1 acts on it by the cycle type: the four partitions of 12
into even parts of size at least 4 are {4,4,4}, {8,4}, {6,6}, {12}; k pairs of M0 close into a
single alternating 2k-cycle in (k-1)!·2^(k-1) ways, which gives 15·8 = 120, 15·2·48 = 1440,
10·8·8 = 640 and 3840, in that order. `count-by-cycle-type.py` is the same count in plain
Python, no group theory.

## Claim 2: each cube's lex-leader group is its orbit stabiliser (`lex-groups.g`, log `lex-groups.log`)

`exist.py` adds, in each cube CNF, a lex-leader clause set for every non-identity element of
the group it computes as the stabiliser of the cube's configuration inside its own G1. That
group was dumped element by element (`cube-groups.g`) and compared with GAP's independent
`Stabilizer(G1, representative, OnSetsSets)`: for all four (15,32) cubes and all seven
(14,27) cubes the two are identical as sets of permutations.

## What this does and does not cover

Covered: the exhaustiveness of the cube split (Lemma 7's combinatorial content) and the
identity of the symmetry group each cube's lex-leader is taken over. Not covered here: that the
lex-leader clauses in the CNF correctly encode "block vector <=_lex its image" for each element,
and the sign-anchor / reorientation part of Lemma 8; those remain the generator's proof
obligations, with the encoder's mutation controls and the found-configuration controls
((13,23), (14,27) and (16,37) are found by the same encoding) as the evidence.

Run: `gap -q -b orbits.g` and `gap -q -b lex-groups.g` from `research/orchard-15/chiro/`
(the second reads `independent/cube-groups.g`). Both finish in seconds.
