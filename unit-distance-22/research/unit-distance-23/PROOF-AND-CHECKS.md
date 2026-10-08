# u(23) = 64: the argument, the evidence, and how to check it

A reader's guide, written 2026-09-28 by the u(23) session (claude-answering-alexeev-u22) with codex (`gpt-6-astra`)
as reviewer and collaborator. It is the entry point to everything else in this directory. **Draft for Liam until the
gates of `RESULT-u23.md` Section 6 are green.** Every number here is from a tool's final run. Read it at one commit
of this repository (the link to this package names it), so that the u(22) documents and the forbidden-graph list it
depends on are exactly the ones cited.

## 1. The statement

u(n) is the largest number of pairs at distance exactly 1 among n points in the plane (OEIS A186705). Alexeev, Mixon
and Parshall (AMP, arXiv:2412.11914) determined u(n) for n <= 21, and their Theorem 1(b) gives configurations with
u(23) >= 64. Our companion result is u(22) = 60 (`research/unit-distance-22/RESULT-u22.md`).

**Theorem.** No unit-distance graph on 23 vertices has 65 edges. Hence u(23) = 64.

Why 65 is the only case: by Schade's lemma (AMP's Lemma), a graph with n vertices and m edges has an induced subgraph on
n - 1 vertices with at least ceil(m(n-2)/n) edges. For (23, 66) that is 61 > u(22) = 60, so u(23) <= 65. A graph with
more than 65 edges would contain one with exactly 65, so the theorem closes the gap.

## 2. The argument

A (23,65) unit-distance graph G would have to satisfy all of the following (`CONTRACT.md` Sections 0 to 3 and
amendments 1 to 4; `research/unit-distance-22/enum/PRUNING.md`; `RHOMBUS-SPEC.md`; `research/unit-distance-22/check/PROOFS.md`):

- **Minimum degree exactly 5.** Deleting a vertex of degree d leaves a unit-distance graph with 65 - d <= 60 edges,
  so d >= 5; and 2 x 65 / 23 < 6.
- **Every canonical ancestor is a unit-distance graph** (L1: deleting a minimum-degree vertex, repeatedly, gives
  induced subgraphs), so the ancestor on j vertices has at most u(j) edges, and its minimum degree is bounded below by
  the reach table (L4; its written proof was corrected on 2026-09-28, an exposition error with no effect on the code).
- **Free of the 398 minimal forbidden graphs** (Globus and Parshall's list and GP-10's ten-vertex list). Only one fact
  about them is used: none is a unit-distance graph, so no subgraph of G is one of them.
- **Hereditarily free of TU gadgets and of the rhombus and triangle contradictions.** If an induced subgraph of G forces
  a unit distance on a non-edge (a TU gadget, L2; or the 4-cycle rows of Lemma R and the triangle rotations of Lemma T),
  then G has a 66th unit distance; if it forces two vertices to coincide, G is not a unit-distance graph. Each such
  exclusion carries an exact algebraic certificate.

The search enumerates every graph that could be such an ancestor: canonical augmentation by minimum-degree deletion,
from the level-10 seeds to 23 vertices (`enum/udenum`, driven by `enum/run-dag2.py`), each graph excluded only by a
proved structural rule or by an exact certificate that a checker separate from the prover replays. Level 12 is split
into 1,920 slices by a hash of each graph, and each graph above level 12 has exactly one canonical parent, so the
slices partition the search.

**What the search found.** Exactly one graph reached (23,65), in slice 50, and it survived every pruning rule. An exact
refutation certificate (a proof tree of 15 nodes over an explicit algebraic number field) shows it is not a
unit-distance graph. Nothing else reached the top.

## 3. Check the last step yourself, in seconds

The graph and its certificate are in `results/u23/top-level/s50of1920/`:
`23-65.g6` (sha256 `c90a07cd8b44…`) and `23-65.certs.jsonl` (sha256 `46f2d3de06f7…`). The first checker needs Python 3
with SymPy (`pip install sympy`: its exact irreducibility check refuses to run without it) and nauty's `labelg` at
`/usr/bin/nauty-labelg` (Debian and Ubuntu: `apt install nauty`), which it uses to confirm the graph is canonical; the
second needs only the standard library. From the repository root:

    : > /tmp/empty.g6
    (cd research/unit-distance-22 && python3 check/udcheck.py --graphs ../unit-distance-23/results/u23/top-level/s50of1920/23-65.g6 \
        --unknown-file /tmp/empty.g6 --data-dir data --expect-n 23 --expect-m 65 \
        ../unit-distance-23/results/u23/top-level/s50of1920/23-65.certs.jsonl)
    # ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15   (about 6 s)

    python3 research/unit-distance-23/blind-verifier/verify_tree.py \
        research/unit-distance-23/results/u23/top-level/s50of1920/23-65.g6 \
        research/unit-distance-23/results/u23/top-level/s50of1920/23-65.certs.jsonl
    # ACCEPT   (under a second)

The second is a verifier written blind, by another model, from the certificate format and the mathematics alone, with
exact arithmetic throughout; `blind-verifier/README.md` and `REPORT.md` say how, and which tampered inputs it rejects.

## 4. The computation and its independent confirmations

- **The run.** 1,920 slices on cloud workers, about 362 machine-hours. Every slice's result copy (counts, hashes,
  manifests, the top two levels' files and certificates, its G4 summary) is on its worker's branch; the coverage audit
  of all of them is in `RESULT-u23.md` Section 5.
- **An independent enumerator on samples (G4).** `enum2/enum2.py`, written separately (it shares nauty for canonical
  labelling and automorphisms with the main enumerator, so a nauty defect would reach both), regenerated a seeded
  sample of the parents of every slice and compared their children with production's, parent by parent: PASS on all
  1,920 slices, over 2,237,909 sampled parents.
- **The full re-run.** Every one of the 1,920 slices was run again from scratch on 48 fresh cloud machines, with
  nothing deleted, and its whole run directory checked by the reviewed checker (`enum/verify-chain.py --check`): every
  level, keep, parent and certificate file read, every certificate replayed. Every re-run agrees with the original in
  its graph counts and in the hashes of its retained graph files: `VERIFY-ALL OK: 1920 of 1920 slices re-run and
  verified, 0 problem(s)` (2026-09-28T11:39Z).
- **The six heavy slices.** Six slices (s50, s1082, s1535, s1651, s1721, s1814) outgrew the machines' 15 GB in that
  check, so a memory-bounded copy of the checker checked them. It is the reviewed checker with four marked streaming
  edits, which change how files are read and held, not what is checked; on every directory both could run, whole
  (23,65) slices included, its output was byte-identical to the original's. Then each heavy slice was split exactly
  into sixteen finer slices of the same enumeration (slice i of 1,920 is the union of the slices i + 1920 j,
  j = 0..15, of 30,720), each regenerated and checked by the unchanged checker (`tools/refine_check.py`). In every
  slice, 15 of the 16 pieces pass. The sixteenth, which holds 93 to 99.9% of the slice's largest cell (a single dense
  level-12 graph dominates each slice), outgrew the machine again: the original checker gives it no verdict, and the
  streaming copy's check of the whole slice covers it. The pieces' roots, and all sixteen pieces' counts, cell by
  cell, reconcile exactly with the original slice (`REFINE-CHECK PARTIAL`, 0 problems).
- **Controls through the same pipeline.** The whole (22,61) tree finds nothing, as it must with u(22) = 60:
  `TARGET-CHECK OK: (22,61): 1920 of 1920 slices complete, G4 PASS 1920; 0 failing, 0 missing; kept at (22,61): 0`.
  The whole (21,57) tree keeps all five of AMP's extremal (21,57) graphs: `TARGET-CHECK OK: (21,57): 1920 of 1920
  slices complete, G4 PASS 1920; 0 failing, 0 missing; kept at (21,57): 10 distinct graph(s); known: 5 of 5 kept`.
- **Reviews.** Twenty-five cross-model review rounds (`results/g5-cross-model-2026-09-26/`), each finding answered in
  writing. The last read the mathematics as a specialist would and found no error.

## 5. Re-run any slice yourself

On a Debian or Ubuntu machine with 4 cores and 8 GB or more (the runbook installs nauty, its headers and a C toolchain
with apt, and pynauty 2.8.8.1 into a virtual environment for the G4 replay):

    env TAG=me U23_PUSH=0 U23_TOOLCHAIN=1 U23_OUT=$PWD/out U23_RES=$PWD/res U23_VERIFY_RES=$PWD/res/verify \
        bash coordination/cloud-workers/u23-verify-local.sh <i>

This builds the shared prefix (levels 10 to 12, about ten minutes), re-runs slice i to level 23 with the fleet's exact
options, replays its G4 sample, and checks the whole run directory with the reviewed checker, regenerating and
replaying every intermediate certificate. Compare `res/.../s<i>of1920/counts.json` and `hashes.json` with the fleet's
copy. A typical slice takes about ten minutes above the prefix (median 557 s); the heaviest took 3.7 hours. The whole
check of a typical slice needs about 5 GB. The six heavy slices need more than 15 GB for the unchanged checker (an
estimate from their certificate files: about 28 GB for the largest); on a smaller machine, set `U23_VERIFY_LEAN=1`
(the default) and the memory-bounded copy takes over when the check is killed for memory.

## 6. What is trusted

- The platform: the compilers and interpreters, and nauty 2.8.8's canonical labelling and automorphism groups (both
  enumerators use it).
- Our implementations of the enumerator (`udenum`), the driver (`run-dag2.py`) and the prune step. The checker reads the
  generated chain and replays every certificate, but it does not regenerate every child; completeness rests on the
  argument of Section 2, the independent G4 regeneration on samples, and the controls.
- The certificate checkers (`check/udcheck.py`, `check/udcheck_rhombus.py`, `check/tri_verify.py`); for the last step,
  also the blind verifier.
- That the files each cloud worker pushed are the files its run produced. The defence is the full re-run, on other
  machines, which reproduced every slice.

## 7. What is kept, and what is not

Kept: every slice's result copy, the re-run's check outputs, the top-level record and certificate, the refinement's
evidence bundles, and every review. Not kept: the intermediate level files and certificates, which were replayed and
then deleted to save space; re-running a slice (Section 5) regenerates them. The review records state three smaller
boundaries: the G4 sampled indices were not retained, the controls' certificates were checked only at production, and
some production logs are read by no checker.

## 8. Where things are

`CONTRACT.md` (the rules and gates), `RESULT-u23.md` (the generated write-up, every number from a tool),
`LABNOTES.md` (the history), `RHOMBUS-SPEC.md` (Lemmas R and T), `blind-verifier/`, `tools/` (every judge, each with
a self-test that plants faults and must catch them), `coordination/cloud-workers/JOBS.md` (every worker, trigger and
session), and for u(22): `research/unit-distance-22/RESULT-u22.md`, `enum/PRUNING.md`, `check/PROOFS.md`,
`delta4/RESULT.md`.
