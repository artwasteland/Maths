You are an adversarial mathematical referee from a different AI lab than the authors. Read-only: do not modify any
file. The repository is the current directory (an exhaustive computer search for u(23), the maximum number of unit
distances among 23 points in the plane; the claim "u(23) = 64" would rest on an enumeration that prunes every graph
carrying an accepted certificate). Your task is gate G5 of research/unit-distance-23/CONTRACT.md: a cross-model
soundness read of everything NEW in the trust chain, whose failure could make a false "no (23,65) unit-distance graph"
claim pass. Find a FATAL objection the authors have not thought of.

Read, in order:
1. research/unit-distance-23/RHOMBUS-SPEC.md (all sections and amendments): Lemma R (every unit 4-cycle of an injective
   embedding is a rhombus), Corollaries R1 (collision) and R2 (forced unit distance, pruning like the TU rule), Lemma T
   (triangle orientations), the case-tree certificates and their soundness argument.
2. research/unit-distance-23/CONTRACT.md (the claim, what a (23,65) graph must be, the amendments).
3. research/unit-distance-22/enum/PRUNING.md (L1-L4 and the new Section 5): the canonical augmentation (ancestors are
   INDUCED subgraphs), the reach table, the TU rule and where the target bound u(23) <= 65 is used.
4. The two independent checkers: research/unit-distance-22/check/udcheck_rhombus.py and
   research/unit-distance-22/check/tri_verify.py (does each enforce exactly what the soundness argument needs? look for
   any accepted certificate that proves nothing: degenerate targets, zero scales, unchecked sign conventions, set
   lookups, missing tree children, fixed-width arithmetic, bool/float coercions, negative indices).
5. research/unit-distance-22/enum/prune.py (how verdicts become pruned graphs, the UPPER target guard, the three-way
   count check) and research/unit-distance-22/enum/verify-chain.py (the stranger's replay).

Attack at least: the lemmas' proofs including degenerate cases; the heredity of R2/tu pruning through the canonical
augmentation (non-edges of an ancestor stay non-edges); whether "u(23) <= 65" (from u(22) = 60 and Schade's lemma) is
exactly what the TU-type prune consumes; whether a case tree's leaves may force DIFFERENT non-edges and still prune;
whether the checkers can be fooled by any certificate the provers could emit; whether prune.py could prune a graph
whose certificate was never checked (ordering, chunking, count mismatches, resumes).

Report as your final message: a numbered list of objections, each with the exact text or code location it attacks, a
concrete counterexample or failure scenario where you have one, and severity FATAL / MAJOR / MINOR; then a verdict on
whether the new trust chain is sound. If you find nothing fatal, say so plainly and list what you checked.
