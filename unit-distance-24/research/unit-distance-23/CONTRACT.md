# CONTRACT: a certificate-first determination of u(23)

Binding on every builder, checker and worker in this programme. Written 2026-09-25 by the supervisor of GP-10
(claude-answering-alexeev-u22), after Boris Alexeev suggested using the 398 minimal forbidden graphs to push the
computation of u(n). Amend it here, never in a brief. It extends `research/unit-distance-22/CONTRACT.md`,
`enum/PRUNING.md` and `RESULT-u22.md`, whose definitions, formats and lemmas apply unless this file says otherwise.

## 0. The claim, and what we will never say

u(n) is the maximum number of edges of a unit-distance graph on n vertices (OEIS A186705). Known before this
programme: u(23) >= 64 (AMP, arXiv:2412.11914, Theorem 1(b): configurations found by Engel et al. and AMP), and
u(22) = 60 (our u(22) result). AMP's Lemma (Schade): a graph with n vertices and m edges has an induced subgraph on
n - 1 vertices with at least ceil(m(n-2)/n) edges. With m = 66 that subgraph would have 61 > u(22) edges, so
**u(23) <= 65, and u(23) is 64 or 65.**

- We claim u(23) = 65 only with an exact embedding of a 23-vertex, 65-edge graph accepted by the checker.
- We claim u(23) = 64 only when the enumeration of Section 2 is complete for the graphs that could exist, every graph
  at its top level carries a checker-accepted refutation (or a TU witness), and gates G0 to G6 are green.
- Never "u(23) = 64" on an empty level whose emptiness was not produced by the certified pipeline, on numerics, or on
  an unchecked certificate. Never hide a dependency: the claim rests on u(22) = 60, on AMP's u(n) for n <= 21, on the
  398 minimal forbidden graphs (Globus-Parshall and GP-10), and on the six TU gadgets.

## 1. What a (23,65) unit-distance graph would have to be

- **Minimum degree exactly 5.** Deleting a vertex of degree d leaves a unit-distance graph with 65 - d <= u(22) = 60
  edges, so d >= 5; and 2 x 65 / 23 < 6, so some vertex has degree <= 5. (Schade's bound; no extra lemma needed.)
- **Free of all 398.** It contains none of the 398 minimal forbidden graphs on at most 10 vertices
  (`research/unit-distance-22/data/forbidden-398.json`, sha256 pinned in Section 5): each is not a unit-distance
  graph, and subgraphs of unit-distance graphs are unit-distance graphs.
- **TU-free, hereditarily.** PRUNING.md's Lemma L2 with (N, M) = (23, 65): a TU gadget with its pair non-adjacent in
  an induced subgraph would force a 66th unit distance, and u(23) <= 65.
- **Every canonical ancestor is a unit-distance graph** (L1), so the ancestor on j vertices has at most u(j) edges:
  u(j) from AMP for j <= 21, and u(22) = 60.

## 2. The enumeration

- `enum/udenum` in **Mode 398** (the 398 as deletion patterns; Mode 74 stays byte-identical to the u(22) run),
  canonical augmentation by minimum-degree deletion, levels 10 to 23, seeds = every graph on 10 vertices (connected or
  not) in the level-10 window that contains none of the 398 (for 10 vertices this is exactly the unit-distance
  graphs), from `nauty-geng` and the Mode-398 filter.
- **Reach table** from (23, 65) with root k = 5 (Section 1), PRUNING.md's L4 with u-bar(22) = 60 and u-bar(j) = u(j)
  for j <= 21. It admits m = 60 only at level 22 (k = 4), 55..56 at 21, 50..53 at 20 and 45..50 at 19; windows are
  one edge wider at the sparse end than the (22,61) run's from level 15 up, and at levels 19 (45..50 against 46..49) and 20 (50..53 against 51..52) one edge wider at the dense end too (amendment 1, 2026-09-26, from the integration builder's check of the computed table).
- **Hereditary TU pruning** from level 12, one certificate per graph (`tu` with gadget and map, or `unknown`, kept).
- **Slicing** at level 13 by record hash, as in u(22); each slice's descendants are disjoint and together exhaustive.
- Every stage writes manifests with input and output hashes and counts, as in u(22).

## 3. The top level

Every graph written at (23, 65) and not TU-pruned is either embedded exactly (then u(23) = 65 and the programme stops
to verify it three ways) or refuted by a certificate that `research/gp-10/check/gp10check.py`'s sample profile (or
`research/unit-distance-22/check/udcheck.py`) accepts. Unknown is never absorbed into a claim.

## 4. Controls (gate G2; each must be shown able to fail)

1. **(22,61) again, in Mode 398:** its top level must be empty after TU (consistency with u(22) = 60); its level
   counts, set against the u(22) run's, measure what the 398 buy.
2. **Mode 398 = Mode 74 minus containment**, on real cells: equality of sets with an independent matcher (the
   builder's report `enum/REPORT-398.md`).
3. **Known graphs survive:** AMP's five extremal 21-vertex graphs in a (21,57) calibration; the densest known
   22-point configuration's graph (60 edges, a unit-distance graph) at level 22 of the (23,65) run whenever its
   minimum degree is at least 4 (as the unit-distance graph of its own points it is faithful, so no TU pruning can
   remove its ancestors).
4. **Independent replay:** a stated fraction of shards replayed by an enumerator sharing no code with `udenum`
   (u(22)'s `enum2`, extended to the 398), with a red control.

## 5. Inputs to pin (gate G0)

- `forbidden-398.json` / `.g6`: sha256 recorded by the Mode-398 builder; the 74 in their existing order, then
  `research/gp-10/runs/B10-final-2026-09-25/L10.g6`.
- The Mode-398 binaries' sha256, and the u(n) table used by the reach computation.

## 6. Gates

| gate | requirement |
|---|---|
| G0 | inputs pinned (Section 5); literature recheck that u(23) is still open |
| G1 | Mode 398 built and validated (`enum/REPORT-398.md`: regression, semantics, filter on B10) |
| G2 | controls of Section 4 green; the pilot's measured cost model written before the fleet launches |
| G3 | every slice complete; the top level decided by checker-accepted certificates |
| G4 | the independent replay of Section 4.4 |
| G5 | a cross-model soundness read of anything new in the trust chain, every finding answered in writing |
| G6 | the write-up generated from checker and manifest output only |

## 7. What is the human's

Emailing Alexeev, Mixon and Parshall; any OEIS, arXiv or Zenodo publication; the timing of anything public.

## 8. Amendments

1. (2026-09-26) Section 2's window sentence completed: levels 19 and 20 are also one edge wider at the dense end.
   The pruning step (`enum/prune.py`) now carries u-bar(23) = UPPER[23] = 65 for the TU rule, with its source
   (u(22) = 60 and Schade's lemma) recorded in every prune manifest; this is Section 1's third bullet, made explicit.
2. (2026-09-26) The rhombus and triangle rules (`RHOMBUS-SPEC.md`, `enum/PRUNING.md` Section 5). Section 0's
   dependencies gain Lemma R (every unit 4-cycle of an injective embedding is a rhombus; Globus-Parshall's Lemma 2)
   and Lemma T (every unit triangle is rotated by +-60 degrees). Section 2's hereditary pruning may use, besides the
   six gadgets, a rhombus certificate (`--rhombus`) or a triangle case tree (`--triangles`), each prune carrying an
   exact certificate; TU-type verdicts need the target bound as before (prune.py's UPPER, now also checked by
   verify-chain.py). Section 3's acceptors gain `check/udcheck_rhombus.py`, which verifies rhombus and tri records
   itself (with the hash-pinned `check/tri_verify.py`) and hands every other record to the hash-pinned udcheck.py or
   udcheck398.py. With `--prune-filter-set 74` the prune step re-checks containment against the 74 only; the 398
   re-check stays in `--verify-stages`, which that option requires (a missed containment could only make the tree a
   superset). Gate G5 covers all of this: an adversarial referee (a Fable model) found no fatal objection
   (RHOMBUS-SPEC amendment 2); a cross-model read by a GPT model is still owed when codex is available.
3. (2026-09-26) Section 2's enumerator is the fast Mode-398 `udenum` (84adaddf, `enum/REPORT-398-SPEED.md`),
   byte-identical to the pilot's; pilot 2 reproduced six pilot slices level by level.
4. (2026-09-26) Section 2's slicing: the pilots and the fleet slice at level 12, not 13 (`U23_SLICE_LEVEL=12`, 1920
   slices by record hash; every worker regenerates levels 10 to 12 itself). The pilot's cost model of gate G2 was
   measured this way, and the property Section 2 relies on is the same: each slice's descendants are disjoint and
   together exhaustive. The coverage audit checks it (each slice records its share of every level-12 parent cell, and
   the shares add up to the stage file), and the prefix files are byte-identical in every copy. A container restart
   makes a worker resume from its own files, and a resumed cell's summary keeps neither its parents nor its share, so
   the slices whose every copy had resumed cells were run again fresh, by the rerun workers f97 to f100 (`JOBS.md`,
   u23-fleet, Reruns); the fresh copy is the one counted.
