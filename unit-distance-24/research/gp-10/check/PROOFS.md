# Soundness notes for the blind checker

These notes record the mathematical invariants used by this module. The
trusted tree moves and gadget forcing identities remain the independently
written arguments in `../../unit-distance-22/check/PROOFS.md`.

## Exact embeddings

A sign change at rational endpoints gives a real root by continuity. Reduction
of every edge equation to zero modulo the integer polynomial makes those
identities hold at every root, without an irreducibility assumption. Horner
interval arithmetic with exact rational bounds contains every value on the
interval. Positive lower bounds on squared distances imply injectivity at
every root in that interval. Nested sign-changing intervals continue to
contain a root. Already separated pairs remain separated on subsets. One
shared interval for all pairs is essential: selecting different roots for
different pairs would not certify a single embedding. An exact midpoint root
can instead be evaluated rationally for every pair.

## Monotonicity, pointers, and TU

Restricting an injective unit-distance map to a subgraph proves L-mono.
Conversely, a graph containing a forbidden subgraph cannot embed. Each pointer
map is injective and preserves every source edge in the documented direction.
A topological resolution accepts a pointer only after its target has the
required accepted verdict, so no circular assumption can establish a verdict.

A gadget step preserves every original embedding as an embedding of the graph
with the distinguished pair added, by the trusted universal TU identity. This
argument applies to the current augmented graph, not just the initial graph.
Induction over the finite sequence transports any supposed original embedding
to the final graph. Containment of an accepted forbidden graph at the end is
then a contradiction. The gadget alone supplies no contradiction.

## Polynomial refutations

A rigid motion sends either orientation of an actual frame edge to the stated
points. A non-edge is insufficient to justify unit separation, and no third
vertex can be fixed without an additional argument. The regenerated edge
equations are necessary conditions for that normalized embedding.

For distinct real points, squared distance is positive. Each selected
saturation equation has the solution t=1/d2, so the added variables remove no
real injective embedding. No assertion about complex isotropic differences is
needed. Evaluating a verified identity sum(h_i*g_i)=1 at a supposed solution
would give 0=1. Evaluating a verified identity with right side f would give
f=0. A strictly positive constant plus positive multiples of real squares
cannot vanish. A univariate real polynomial with zero real roots cannot vanish
either, even when evaluated in a larger real coordinate system.

The rational Sturm chain uses the polynomial, its derivative, then negatives
of nonzero Euclidean remainders. At each end of the real line the sign of a
nonzero polynomial is determined by its leading coefficient and parity of its
degree. The difference of sign variations counts distinct real roots.
Stopping at a nonconstant gcd handles repeated roots without discarding them.
The zero polynomial has no finite root count and is rejected explicitly.

## Blocks and minimality

Every embedding restricts to each block. Conversely, glue embedded blocks one
at a time along cut vertices. Translate their attachment points to the shared
cut vertex and rotate the new block. Each unintended collision with an already
placed vertex forbids at most finitely many rotation angles, so a rotation
avoiding all collisions exists. Bridges and isolated vertices present the
same finite avoidance problem. Separate connected components by translation.
This proves L-block for finite graphs without imposing conditions on non-edges.

The checker verifies the block edge partition, that each block is of smaller
order, and that no trusted forbidden graph is contained in a block. GP's
classification through nine vertices then embeds each such block.

For a forbidden graph in the specified F-free biconnected input family,
deleting a vertex leaves a smaller F-free graph and hence a unit-distance
graph. Every other proper subgraph omits some edge and is contained in that
edge deletion. Thus all edge deletions embedding is equivalent to minimality.
A known refuted deletion disproves minimality immediately. With unknown
deletions, minimality is provisional exactly under the assumption that all
of those deletions embed. CONTRACT Section 10 amendment 2 adopts this
provisional status and corrects the earlier reversed use of "unless".

Once all input graphs are decided, L-block and the smaller-order classification
reduce any forbidden graph through ten vertices to a biconnected member of the
input family or a graph already containing F9. Inclusion-minimal forbidden
members of the family give the remaining obstructions. Under the hypothesis
that every unknown is embedded, the same argument gives the contract's
conditional form. Publication still needs the independent input-freeze and
review gates; this checker never independently authorizes that claim.

## Round 3: derivation rows

This branch implements CONTRACT Section 10 amendment 5 and the shared
`research/gp-10/PROOFS.md` Section 6. Let I be the ideal of the regenerated
edge and saturation equations. Each original source lies in I. At row k the
checker accepts only original sources and verified rows j < k, then expands
the claimed equality over Q. Induction gives P_k in I. A real injective
embedding, rigidly moved to the edge frame and extended with the reciprocal
squared-distance saturation variables, annihilates I and every accepted row.
A final row equal to 1 is therefore impossible. A final row equal to f is
impossible when the existing exact Sturm or positive SOS proof shows that f
has no real zero. No auxiliary row is registered before its identity passes.

The DAG term order and nonzero-coefficient rules provide a deterministic
sparse representation; rational spelling remains governed by amendment 3.
The row bound limits certificate length, not degree or expanded polynomial
size. The implementation shares the original no-real-zero proof statements
without changing their arithmetic or acceptance conditions.
