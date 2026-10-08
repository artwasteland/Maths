# GP-10 soundness: why each thing the checker accepts is true

Written 2026-09-24 by claude-answering-alexeev-u22 for `CONTRACT.md` Section 2. Every certificate type
and every step of the checker's derivation of L10 is justified here, or by a named proof elsewhere
(`research/unit-distance-22/check/PROOFS.md` for the gadgets and the proof-tree moves; AMP Section 4).
Notation: p is a unit-distance embedding of G, meaning an injective map V(G) -> R^2 with
|p(u) - p(v)| = 1 on every edge. d2(u, v) = |p(u) - p(v)|^2.

## 1. Structural lemmas

**L-mono.** If G is a subgraph of H via an injective edge-preserving map m and p embeds H, then
p o m embeds G: it is injective as a composition of injections, and every edge uv of G goes to an
edge m(u)m(v) of H, so |p(m(u)) - p(m(v))| = 1. Contrapositive: if G is forbidden, so is every H
containing it. This is the whole justification of E-ptr (pointer to a larger embedded graph) and
R-ptr (pointer to a smaller refuted one).

**L-block.** G is a UDG iff every block of G is. Only-if is L-mono. If: order the blocks B_1, B_2, ...
so that each B_k (k > 1) meets the union U of the earlier ones in exactly one cut vertex c (a
breadth-first order of the block tree does this; components are handled by translating them far
apart). Suppose U is embedded injectively and B_k has an embedding q with q(c) = p(c) (translate).
For an angle t let q_t be q rotated by t about p(c). A collision q_t(x) = p(y) with x in B_k - c and
y in U - c requires |q(x) - p(c)| = |p(y) - p(c)| > 0 (both points differ from p(c) by injectivity
within each part), and then happens for exactly one t in [0, 2 pi). There are finitely many pairs
(x, y), so some t avoids them all, and p extended by q_t is injective; its edges are unit because
every edge lies inside one block. A bridge is a block K2, trivially a UDG.

**Minimal forbidden graphs live in B10.** A minimal forbidden graph M on 10 vertices is biconnected
(otherwise its blocks are proper subgraphs, hence UDGs, hence M is a UDG by L-block) and F9-free
(a member of F9 inside M would be a proper forbidden subgraph; no member of F9 has 10 vertices).

**L-min.** For G in B10: G is minimal forbidden iff G is forbidden and G - e is a UDG for every edge
e. A proper subgraph S of G either has all 10 vertices, and then S is a subgraph of G - e for some
edge e missing from S; or misses a vertex v, and then S is a subgraph of G - v, which has 9 vertices
and is F9-free (being inside G), hence a UDG by GP's theorem (or, independently, by our control 7.2,
Section 5 below). So all proper subgraphs are UDGs iff all G - e are (L-mono). When G - e is not
biconnected, it is a UDG by L-block, since each of its blocks has at most 9 vertices and is F9-free.

**L-complete.** Suppose every graph of B10 has an accepted verdict, and let L10 be the set of
refuted G in B10 all of whose G - e are UDGs (L-min). Then a graph K on at most 10 vertices is a UDG
iff K contains no member of F9 and no member of L10.
- Only if: members of F9 and L10 are forbidden, and subgraphs of UDGs are UDGs (L-mono).
- If: let K be forbidden. Choose a forbidden subgraph M of K with as few vertices plus edges as
  possible; every proper subgraph of M is then a UDG, so M is minimal forbidden. If M has at most 9
  vertices, GP's theorem says M contains a member of F9, and minimality forces M to be that member.
  If M has 10 vertices, M is in B10 (previous paragraph) and is forbidden with every M - e a UDG, so
  M is in L10. Either way K contains a member of F9 or L10.

## 2. Embedding certificates

**E-exact.** From minpoly(lo) * minpoly(hi) < 0 and continuity there is a real root theta in
[lo, hi]. Each coordinate X_i(theta), Y_i(theta) is then a real number. For an edge uv the polynomial
E_uv(t) = (X_u - X_v)^2 + (Y_u - Y_v)^2 - 1 reduces to 0 modulo minpoly, so E_uv = minpoly * Q for a
rational polynomial Q, and E_uv(theta) = 0: the edge has length 1. Irreducibility of minpoly is not
needed for this. For distinctness, the checker bounds D_uv(t) = (X_u - X_v)^2 + (Y_u - Y_v)^2 over the
whole interval [lo, hi] by ball arithmetic (a rigorous enclosure of the range of a polynomial over an
interval) and finds the enclosure excludes 0; hence D_uv(theta) is nonzero and p(u) != p(v). So
t |-> (X_i(theta), Y_i(theta)) is a unit-distance embedding. The checker may shrink [lo, hi] by
bisection, keeping a sign change, before bounding; any subinterval with a sign change also contains a
real root, and the argument is unchanged.

## 3. Refutation certificates

**R-tu (chains of forced pairs).** Let the gadget H have distinguished non-adjacent pair {a, b} with
|q(a) - q(b)| = 1 in every embedding q of H (proved per gadget in
`research/unit-distance-22/check/PROOFS.md`). If phi maps H into G injectively and edge-preservingly
and phi(a)phi(b) is not an edge of G, then for any embedding p of G, p o phi embeds H (L-mono), so
|p(phi(a)) - p(phi(b))| = 1, and p also embeds G + phi(a)phi(b). By induction along the chain, if G
is a UDG then so is the final augmented graph G*. The end condition exhibits a forbidden graph inside
G* (a member of the list in force, or a graph with an accepted refutation), so G* is forbidden by
L-mono, and therefore G is forbidden. No edge-count hypothesis is used; that is why a single gadget
hit without the chain's end proves nothing here.

**L-frame.** Let (a, b) be an EDGE and p an embedding. The rigid motion x |-> R(x - p(a)), with R the
rotation taking p(b) - p(a) (a unit vector) to (1, 0), preserves all distances and injectivity, and
sends p(a) to (0, 0) and p(b) to (1, 0). So if G embeds at all, it embeds with that frame. A non-edge
cannot be framed this way (its length is unknown), and pinning any third coordinate loses embeddings.

**R-null.** Suppose p embeds G with the frame of L-frame. Put x_i = p(i)_x, y_i = p(i)_y for the other
vertices, and for each pair (u, v) in the sat list put t_uv = 1 / d2(u, v), which is a real number
because p is injective, so d2(u, v) > 0. At this real point every generator vanishes: the edge
equations because edges are unit, and t_uv * d2(u, v) - 1 by construction. If the certificate's
identity sum_k c_k g_k = 1 holds as polynomials, evaluating at the point gives 0 = 1. So G has no
embedding. The identity is checked by expansion; it is a statement about polynomials, so no
Groebner computation is being trusted. (It proves "no real injective embedding". It says nothing
about complex points whose differences are isotropic, and needs to.)

**R-real.** As R-null, with the identity sum_k c_k g_k = f: at the real point above f vanishes. If f
involves a single variable and has no real root (exact Sturm count 0 on the real line), or if
f = c + sum_i w_i q_i^2 with c > 0 and w_i > 0 rational (so f >= c > 0 at every real point), this is
a contradiction. Every variable, including each t_uv, is real at that point, which is what makes the
univariate case valid whichever variable f uses.

**R-tree.** The proof-tree calculus L0, L1a, L1b, L1c, L2, L3 of AMP Section 4 (B. Alexeev, D. G. Mixon and H. Parshall, arXiv:2412.11914, Section 4: the source of the soundness argument for L0, L1a, L1b and L2, which the kernel's PROOFS.md cites rather than proves in place; G5 MINOR-5) as implemented and
proved in `research/unit-distance-22/check/PROOFS.md` (L0: every 4-cycle is a rhombus, so its sides
are opposite in pairs; L1c and L3: the Heron-esque lemma). The checker delegates these nodes to the
u(22) kernel, which was built blind against the u(22) contract and mutation-tested (41 checks, 23
mutations rejected, `research/unit-distance-22/check/REPORT.md`).

## 4. What the result rests on

1. Every accepted certificate, by Sections 2 and 3.
2. The gadget proofs and the proof-tree moves (`research/unit-distance-22/check/PROOFS.md`).
3. The completeness of B10: every biconnected 10-vertex graph is produced by `nauty-geng -C` (count
   anchored to OEIS A002218) and every removed graph carries a replayed forbidden witness
   (CONTRACT Section 6).
4. GP's theorem for 9-vertex (and smaller) graphs, used in L-min, L-block and L-complete, OR the
   independent re-derivation of Section 5.

## 5. Re-deriving the smaller cases instead of trusting them

The withheld-answer controls do more than test the pipeline. If control 7.2 decides every graph of
B9' (biconnected, 9 vertices, F8-free) with accepted certificates and derives exactly GP's 55, then
L-complete one level down re-proves GP's 9-vertex theorem from our own certificates, given the same
statement at 8 vertices; control 7.1 gives that from 7 vertices, and so on. Running the controls
down to n = 4 (Section 10 amendment 1 of the contract) re-derives the whole classification up to 9
vertices from scratch, so the 10-vertex result would then rest on items 1 to 3 above alone, with GP
and Chilakamarri and Mahoney as independent agreement rather than as premises. This matters here:
the problem has a published history of errors (Purdy and Purdy's 1988 classification at 7 vertices
was wrong; GP's own v3 corrected a graph and a lemma).

## 6. Amendment 5: derivations in rows (R-null-dag, R-real-dag)

Let I be the ideal of Q[x, y, t] generated by the regenerated system (the edge equations other than the
frame edge and the Rabinowitsch polynomials). Row k states P_k = sum over sources of c * source, where each
source is a generator of I or an earlier row P_j (j < k). By induction on k, every P_k lies in I: a
generator is in I, and a polynomial combination of elements of I is in I. So the last row's P lies in I and
vanishes at the real point of the R-null argument (Section 3). If it is 1, that gives 0 = 1; if it is f
with a no-real-zero proof, the R-real argument applies. The chain only shares intermediate work that a
single cofactor identity would expand in full; it proves nothing more and nothing less.
