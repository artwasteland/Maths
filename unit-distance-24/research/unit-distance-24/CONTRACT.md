# CONTRACT: a certificate-first determination of u(24)

Binding on every builder, checker and worker in this programme. Written 2026-10-01 by claude-answering-alexeev-u22,
after Boris Alexeev asked how long u(24) would take. It extends `research/unit-distance-23/CONTRACT.md`, whose
definitions, formats, lemmas and rules apply unless this file says otherwise. Amend it here, never in a brief.

## 0. The claim, and what we will never say

u(24) >= 68 (AMP, arXiv:2412.11914, Theorem 1(b)). With u(23) = 64 (`research/unit-distance-23/RESULT-u23.md`), AMP's
Lemma (Schade) gives u(24) <= 69: a (24,70) graph would have an induced 23-vertex subgraph with
ceil(70 x 22/24) = 65 > 64 edges. **So u(24) is 68 or 69, and the one case is (24,69).**

- We claim u(24) = 69 only with an exact embedding of a 24-vertex, 69-edge graph accepted by the checker.
- We claim u(24) = 68 only when the enumeration of Section 2 is complete, every graph at its top level carries a
  checker-accepted refutation (or a TU witness), and the gates of Section 4 are green.
- The claim rests on u(23) = 64 and u(22) = 60 (our results), on AMP's u(n) for n <= 21, on the 398 minimal forbidden
  graphs, and on the six TU gadgets. Say so wherever the result is stated.

## 1. What a (24,69) unit-distance graph would have to be

- **Minimum degree exactly 5.** Deleting a vertex of degree d leaves 69 - d <= u(23) = 64 edges, so d >= 5; and
  2 x 69/24 < 6. Schade's bound, no extra lemma.
- **Free of all 398, TU-free hereditarily** (L2 with (N, M) = (24, 69), valid since u(24) <= 69 is proved).
- **Every canonical ancestor is a unit-distance graph**, so the one on j vertices has at most u(j) edges: AMP for
  j <= 21, u(22) = 60 and u(23) = 64 (the run's u-bar overrides 22=60 and 23=64, recorded and justified in reach.json).

## 2. The enumeration

The u(23) pipeline unchanged except for its tables: `run-dag2.py` and `prune.py` extended to n = 24, the runbook
`coordination/cloud-workers/u23-slice.sh` taking two u-bar overrides. Target (24,69), seed level 10, root k 5, slice
level 12, count 1,920, Mode 398, triangles, the set-74 prune re-check, stage verification. The reach tables of (24,69)
and (23,65) agree through level 15; the new routes enter at (17,40), (18,42), (19,45) and (20,49). The prefix (levels
10 to 12) is byte-identical to (23,65)'s (86 files compared, 2026-10-01).

## 3. The standard: one run, checked before deletion

Decided with Liam on 2026-09-30 (`research/unit-distance-23/NEXT-ESTIMATES-2026-09-29.md`, "The standard for u(24)").
The field's norm is two independently written programs agreeing, or certificates checked by an independent checker;
re-running the same program proves reproducibility, not correctness. u(23) ran twice only because its fleet deleted
run directories before the reviewed checker saw them. So:

- **Check before delete.** Each worker (`coordination/cloud-workers/u24-worker.sh`) runs a slice, its G4 replay,
  the reviewed checker `research/unit-distance-22/enum/verify-chain-u24.py --check` on the run directory, and the
  known-graph control; pushes a receipt bound to that output; and only then deletes the directory. A failed check or
  push keeps it.
- **The checker** is the G5-closed `verify-chain.py` with its memory bounded (`verify-chain-lean.py`, four LEAN edits)
  and its tables extended to 24 (the U24 edits), nothing else changed. On every run of a target with n <= 23 it
  prints exactly what `verify-chain-lean.py` prints.
- **G4 at twice u(23)'s fraction** (0.002): part of the saving buys a larger sample for the independent enumerator.
- **The known-graph control, at every level with data.** Engel et al.'s configurations (16 to 22 points, 137,011
  graphs, each the unit-distance graph of its own points) are faithful, so no sound rule prunes one or any ancestor,
  and each one at a reach-table cell with minimum degree at least k(n,m) is in the tree, in exactly one slice. Per
  slice: none generated is pruned. Over the whole run: every such graph found, once.
- **Reproduction by sample**, not in full: 48 random slices (a published seed) and a few chosen ones (heavy,
  restarted) re-run on fresh machines, their result copies compared with the first run's. What is given up is
  u(23)'s extra claim that every slice was reproduced on another machine; the write-up says so.
- **Controls carried forward** where the pipeline's core is unchanged: the (22,61) tree control and the (21,57)
  calibration of u(23) stand. New: the known-graph control above, and the pilot's deployment checks.
- **Pilot slices count** toward the final run when the pipeline and checker are frozen at the pilot's version.

## 4. Gates

- **G0** Literature: nothing published decides u(24) or contradicts the inputs (recheck at the end).
- **G1** The extensions reviewed: the table extensions (`run-dag2.py`, `prune.py`, the runbook) and the new checker
  and worker, each with its tests, and an independent review of the checker's U24 edits and the worker (codex,
  read-only), closed.
- **G2** The pilot (`## u24-pilot` in `coordination/cloud-workers/JOBS.md`): 42 slices, measured.
- **G3** The whole run: every one of the 1,920 slices with a receipt that the coordinator's judge accepts, derived
  from the recorded output (not the worker's label), every prefix the prefix of a whole check, G4 PASS on every
  slice, and the fleet's summary audit (`verify-chain-u24.py --summary-only`) complete.
- **G4** The known-graph control complete over the whole run.
- **G5** The reproduction sample: every sampled slice's result copy identical to the first run's.
- **G6** The write-up generated from the evidence, with its dependencies stated.
