# GP-11: the profile's soundness obligations

Written 2026-10-01 before implementing the B11 profile.
The certificate rules and their proofs are unchanged from GP-10.
This file applies CONTRACT Sections 1 and 2; it admits no new certificate type.

## The lower-order premise

F10 is the frozen 398-entry JSON, in its original order and labelling.
Its first 74 entries must equal the frozen GP-10 list byte-for-byte as parsed JSON.
Canonicalising its remaining entries must give exactly the 324 graphs derived by
a complete B10 control in the same run tree.
The B10 control uses only F9, never those 324 as refutation axioms.
Its smaller controls re-derive orders 4 through 9 with the answer at each order withheld.
Thus GP-10's theorem, independently agreeing with GP below order 10, supplies the
lower-order premise; the filename or cardinality 398 alone does not supply it.

## L-block at order 11

Use GP-10 PROOFS Section 1's finite-rotation argument without alteration.
Every block of a non-biconnected graph on 11 vertices has at most 10 vertices.
The checker reconstructs the blocks, including bridges, and checks that their
edge sets partition the graph's edges.
Isolated vertices impose no distance equations and can be placed separately.
Each block is searched for all F10 members through order 10.
Absence of every such member implies that the block embeds, by the lower-order
theorem just re-derived in the controls.
The order-ten search must be explicit: the old search default is nine.

## L-min at order 11

Let G be a forbidden member of B11.
Every vertex deletion is F10-free and has ten vertices, hence embeds by GP-10.
Every proper subgraph either omits a vertex or is contained in an edge deletion.
By L-mono, G is minimal forbidden exactly when every edge deletion embeds.
For each actual edge the profile reconstructs its deletion.
A biconnected deletion must have an accepted record in the same run.
A non-biconnected deletion uses the block argument above.
A refuted deletion rules out minimality even if other deletions are unknown.
An unknown deletion leaves the assertion conditional on all listed unknown
deletions embedding; it never certifies unconditional minimality.
The conditional list follows GP-10 amendment 2's wording.

## L-complete at order 11

Choose an inclusion-minimal forbidden subgraph M of any forbidden graph K on
at most 11 vertices.
M is biconnected, since otherwise each proper block embeds and L-block embeds M.
If M has at most ten vertices, the lower-order theorem places it in F10.
Otherwise M has eleven vertices and is F10-free, since any contained F10 member
would be a proper forbidden subgraph.
The frozen enumeration therefore contains M in B11.
When every B11 graph is decided, the edge-deletion test places M in L11.
Conversely every F10 or L11 member is forbidden and L-mono excludes every host
containing one.
Consequently a graph on at most eleven vertices embeds exactly when it avoids
F10 and L11, subject to the independent enumeration and review gates.

## Receipts and publication

Replay, coverage, and exact certificates establish mathematical decisions.
Hash-bound receipts only identify the bytes checked or reviewed.
They do not establish that an outside review occurred, that a prediction was
committed before a run, or that an enumeration was exhaustive.
Those are explicit human or independent-tool attestations at G0, G1, G2 and G5.
The writer requires their evidence and the current source hashes, and checks
the report and all retained input/output/control hashes before writing a claim.
Fixture runs and conditional ACCEPTs cannot authorize publication.
