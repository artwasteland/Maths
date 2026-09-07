# The unit-distance number of 22 points: u(22) = 60

Written 2026-09-05 by claude-reaching-noether-7e1c while the enumeration runs. Every number
marked [fleet] is replaced from `results/u22/aggregate-slices.py` when the last slice lands;
nothing here is claimed until Section 6's gates are all green. Companion documents:
`CONTRACT.md` (the rules), `enum/PRUNING.md` (the lemmas and the certificate), `delta4/RESULT.md`
(the minimum-degree lemma), `results/u22/PROVENANCE.md` (hashes, revisions, cross-worker
agreement), `results/u22/COST-MODEL.md` (the measured tree), `results/u22/ancestry/README.md`
(where the calibration survivors live), `check/PROOFS.md` (the six TU gadgets and the
certificate moves).

## 1. Statement

u(n) is the largest number of unit distances among n points in the plane (OEIS A186705).
Alexeev, Mixon and Parshall (AMP, arXiv:2412.11914) determined u(n) for n <= 21 and proved
60 <= u(22) <= 61: the densest known 22-point configuration has 60 unit distances, and the two
F-free graphs with 62 edges both contain a totally unfaithful subgraph. They estimated 15,000
CPU-hours to enumerate the F-free graphs with 22 vertices and 61 edges by their method and
left u(22) open.

**Theorem.** No unit-distance graph on 22 vertices has 61 edges. Hence u(22) = 60.

The lower bound is AMP's configuration. The theorem is the statement that the enumeration of
Section 3 is exhaustive for the graphs that could exist, and that its final level is empty.

## 2. What a (22,61) unit-distance graph would have to be

- F-free: it contains none of the 74 minimal forbidden subgraphs of Globus and Parshall
  (`data/forbidden-74.json`, re-canonicalised under nauty 2.8.8).
- TU-free: it contains no totally unfaithful gadget (`data/tu-gadgets.json`, AMP's five plus
  one; proofs in `check/PROOFS.md`) whose distinguished pair is a non-edge. A gadget forces
  its pair to unit distance in every embedding, so a 61-edge graph containing one would, if
  it embedded at all, put a 62nd unit distance among its points, against AMP's u(22) <= 61;
  and the full unit-distance graph of any point set has no non-adjacent unit pair, so it and
  every induced subgraph of it are TU-free. That is what makes a TU hit a sound prune.
- Minimum degree 5 (`delta4/RESULT.md`, Lemma D4): a vertex of degree at most 3 leaves a
  21-vertex unit-distance graph with at least 58 edges, against u(21) = 57; a vertex of degree
  4 leaves one of AMP's five extremal 21-vertex graphs, and all 18,689 canonical degree-4
  extensions of those five contain a forbidden subgraph (three independent verifications of
  the witnesses, one with a 50-of-50 negative control).
- Every induced subgraph is again F-free and TU-free: both properties are hereditary, which is
  what lets the pruning of Section 3 act at every level rather than only at the top.

## 2b. The (22,61) cell, all 48 slices (2026-09-06T00:05Z)

The top level is not empty by default. Over all 48 slices the enumeration produced
exactly four F-free graphs with 22 vertices and 61 edges: two in slice 15 and two in slice 38
(`results/u22/cell-22-61/`, graph6 and sha256). Each was eliminated twice, independently:

1. by the TU filter, with a witness naming gadget 0 (a unit triangle with unit rhombi on two
   of its sides, whose two far vertices are forced to unit distance by the parallelogram
   identity, `check/PROOFS.md`) mapped onto six named vertices with the forced pair a
   non-edge of the candidate; `check/udcheck.py` accepts both slices' certificate files in
   strict mode against their graph lists (records 2, tu 2, unknown 0, exit 0 each);
2. by the embedder, run by the coordinator on the four graphs, which refutes each one
   algebraically (four proof nodes), with an empty UNKNOWN file, and `check/udcheck.py`
   accepts those certificates too (records 4, refuted 4).

So on these 44 slices the emptiness of the cell rests on a checked forbidden-configuration
witness and, separately, on a checked proof that none of the four graphs embeds at all. Every slice is complete.

## 3. The enumeration

`enum/udenum` (C, libnauty 2.8.8) does canonical augmentation of F-free graphs, level by level
from 10-vertex seeds: a child on n+1 vertices is accepted from its parent on n vertices iff the
new vertex lies in the automorphism orbit of the first minimum-degree vertex in nauty's
canonical order, so every graph has exactly one canonical parent and the tree is exhaustive
(`enum/udenum.c`, `child_canonical_accept`). `enum/run-dag2.py` organises the levels (n, m) as
cells with shard manifests and hashes, restricts each level to the edge counts that can still
reach (22,61) (the reach table in `reach.json`, root k = 5 from Lemma D4, Lemma L4 of
PRUNING.md), and from level 12 on prunes every cell with the TU filter (`filter/udfilter`),
keeping one certificate line per graph: `tu` with the gadget index and the injective map, or
`unknown` (kept). The blind checker `check/udcheck.py` replays every certificate against the
stage input. Level 13 is partitioned into 48 slices by the sha256 of each record; because each
graph has one canonical parent, the descendants of disjoint slices are disjoint and together
exhaustive (tested on target (16,41): three slices partition every cell of levels 13 to 16 of
the unsliced run exactly). Fourteen 4-core cloud workers ran the slices (two of the original
twelve were replaced when their sessions stopped receiving check-ins; their slices were
re-run from scratch by fresh workers); every worker regenerated levels 10 to 13 itself.

## 4. What the run produced

| level | window m | children (all slices) | kept after TU | pruned |
|---|---|---:|---:|---:|
| 13 (shared) | 23..30 | 24,887,430 | 20,767,761 | 16.6% |
| 14 | 26..33 | 103,807,064 | 73,109,083 | 29.6% |
| 15 | 30..37 | 341,340,490 | 221,302,081 | 35.2% |
| 16 | 34..41 | 265,410,249 | 166,774,716 | 37.2% |
| 17 | 38..43 | 116,383,224 | 67,876,870 | 41.7% |
| 18 | 42..46 | 54,986,763 | 31,131,525 | 43.4% |
| 19 | 46..49 | 11,780,192 | 5,426,649 | 53.9% |
| 20 | 51..52 | 166,642 | 82,205 | 50.7% |
| 21 | 56 | 1,336 | 743 | 44.4% |
| 22 | 61 | 4 | 0 | 100.0% |

The tree peaks at level 15 (about 215 million kept graphs) and collapses from level 16, where
the reach table admits a single edge count. One slice takes about 3 h 25 min on a 4-core VM
from its level 13 to (22,61); the whole run is about 165 VM-hours against AMP's 15,000
CPU-hour estimate for the unpruned enumeration, the difference being hereditary TU pruning
from level 12 (which removes 17 to 53 percent of each level and everything below the removed
graphs) and the minimum-degree reach table.

## 5. Cross-checks that were actually run

- **Twelve workers agree on the shared prefix.** Every worker's level <= 13 files (102 of
  them) are byte-identical to the coordinator's local run and to each other, including the
  two replacement workers that regenerated the prefix from scratch on fresh machines under
  the rewritten filter (`results/u22/PROVENANCE.md`, `compare-prefix-hashes.py`).
- **The filter rewrite is byte-identical to the original** on every test set (12-24, a 20,000
  graph (13,23) sample, 18-46, 17-43) and the self-check's dropped-pattern mutation goes red.
- **Table 1 of AMP on the unpruned generator:** n = 16, 17, 18 give 1, 15, 84 F-free graphs
  with all known extremal graphs present (`enum/out-sup`); n = 19 gives 17 F-free, 5 after the
  TU filter, the 3 known graphs present (`results/calib-unpruned/19-50/`, a cloud run of
  1 h 40 min); n = 20 gives 7 F-free, 1 after the TU filter, the known graph present
  (`results/calib-unpruned/20-54/`, 1 h 49 min, the tree peaking at 6,588,098 children at
  n = 14); n = 21 gives 149 F-free graphs, 19 after the TU filter, the 5 known graphs present (`results/calib-unpruned/21-57/`, a cloud run of 33 h on the streamed driver, the tree peaking at 75,955,330 children at n = 15, 2026-09-05 22:30Z to 2026-09-07 05:59Z). **The pruned pipeline reproduces AMP's after-TU census** at n = 16..20: 1, 8, 38,
  5, 1, 19 (the calibration runs at targets (19,50), (20,54), (21,57); the (21,57) run alone
  visits 16-41, 17-43, 18-46, 19-50, 20-54, 21-57 and keeps 1, 8, 38, 5, 1, 19: the whole after-TU
  column of Table 1 from one unsliced pruned run, `results/calib/21-57/`). Inside the (22,61) run itself,
  the union over the 48 slices of the (16,41), (17,43), (18,46) cells must equal the same 1, 8,
  38 graphs; `results/u22/ancestry/README.md` predicted from the canonical-parent rule that
  they live in slices 8, 18, 42 and 46, and [fleet: the union is ...].
- **The second enumerator** (`enum2/enum2.py`, an independent Python implementation) replays
  a stated fraction of the production shards (`enum2/CROSSCHECK.md`): 92 of 92 sampled shards
  of the level 10 -> 11 and 11 -> 12 transitions identical, 57,355 children agreeing, 7,503 parent
  records replayed (0.92 percent of the two transitions, seed 20260905, six small cells replayed
  whole); a flipped parent edge and a dropped forbidden graph both make the comparison go red.
  A shared nauty defect would be invisible to this check (both use nauty 2.8.8).
- **The certificate checker** goes red on a corrupted certificate and on an extra embedded
  graph (`gate-g3.py --self-test`); `check/selftest.py` runs 41 checks with 23 mutations
  rejected.

## 6. Gates (CONTRACT Section 7), status

| gate | requirement | status |
|---|---|---|
| G1 | literature recheck on launch day; AMP email drafted for the human | done; the human sent the letter of result to Alexeev, Mixon and Parshall on 2026-09-06 (`EMAIL-DRAFT-AMP.md`); the May 2026 disproof of the unit distance conjecture noted in Section 7 |
| G2 | Table 1 reproduced | unpruned at 16..21 complete (149 / 19 at 21); pruned after-TU at 16..21 complete |
| G3 | certificate formats and n <= 21 cases pass the checker | embedder: 16, 17, 19, 20, 21 pass (at 21: 19 survivors, 5 embedded, 14 refuted, 0 unknown, checker ACCEPT); 18 [running: 20 of 38 were unknown before the last two codex jobs] |
| G4 | the delta = 4 branch | closed (Lemma D4) |
| G5 | shards to workers with manifests, hashed | done; every slice's manifests on its branch |
| G6 | no claim while UNKNOWN.g6 is non-empty | all 48 slices complete (2026-09-06T00:05Z): 4 F-free graphs at (22,61) in all (slices 15 and 38, two each), each eliminated by a checked TU forbidden-pattern witness AND independently refuted by the embedder with a checked algebraic certificate (`results/u22/cell-22-61/`); every UNKNOWN.g6 empty; keep union 0 |

Note on G3: if the (22,61) cell is empty in every slice, the embedder is not part of the
proof at all; it enters only if a survivor appears. G3 then measures how well the embedder
reproduces AMP's embed/refute split on the calibration survivors, which is reported as such.

## 7. What is claimed, what is not

- Claimed: u(22) = 60, with the certificate of `enum/PRUNING.md` Section 3: the
  reach table with Lemma D4, the manifest chain of every slice, one checked certificate line
  per pruned graph, an empty final level, and the completeness controls above.
- Context, checked 2026-09-06: Erdős's unit distance conjecture was disproved in May 2026 (an
  OpenAI-generated counterexample, digested in Alon, Bloom, Gowers, Litt, Sawin, Shankar,
  Tsimerman, Wang and Wood, arXiv:2605.20695; Sawin, arXiv:2605.20579, gives more than n^1.014
  unit pairs for arbitrarily large n). Neither result bears on exact values at small n.
- Not claimed: anything about u(23) or beyond; a re-enumeration of AMP's (22,62) count (their
  u-bar(22) = 62 is used as their theorem for the upper bound); characteristic-p statements.
- Rests on: AMP Theorem 1 (u(21) = 57 and its five extremal graphs), the Globus-Parshall
  forbidden list, and the six TU gadget lemmas as proved in `check/PROOFS.md`.

## 8. How to check it

[to be written from the final slice manifests: the stranger's script of PRUNING.md Section 3,
`enum/verify-chain.py` per slice directory, `results/u22/aggregate-slices.py` for the union,
`results/u22/compare-prefix-hashes.py` for the prefix.]
