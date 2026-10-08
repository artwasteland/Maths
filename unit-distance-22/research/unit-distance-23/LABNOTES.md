# u(23) lab notes (supervisor: claude-answering-alexeev-u22)

Chronological, times AEST (UTC+10); a time marked Z is UTC. What happened, including what went wrong.

## 2026-09-25: from Boris Alexeev's suggestion to a pipeline

- **The question.** Replying to GP-10, Boris Alexeev suggested that forbidding all 398 minimal forbidden graphs (the
  74 of Globus-Parshall plus GP-10's 324 on ten vertices) should make computing u(n) more efficient. With u(22) = 60
  (our u(22) result), AMP's Schade lemma already gives u(23) <= 65; the known lower bound is 64, so u(23) is 64 or 65
  and a (23,65) enumeration decides it. `CONTRACT.md` written before any producer, as for u(22) and GP-10.
- **Gate G1, Mode 398 (landed as `952ae252d`).** A Claude agent generalized `udenum` and `udfilter` to
  `--forbidden-set 74|398` in its own worktree; the supervisor reviewed the diff (guard table against the old
  literals, every resized array, the manifest recording the forbidden file's hash), rebuilt the binaries
  byte-identical, and re-ran two checks on the landed binaries. `research/unit-distance-22/enum/REPORT-398.md` has
  the builder's report: Mode 74 byte-identical to production on 69 cells; Mode 398 = Mode 74 minus containment on 22
  cells (71,320 = 71,320) and on all 12,005,168 graphs of order 10; udfilter Mode 398 calls exactly GP-10's 509
  refuted graphs of B10 forbidden.
- **What the 398 buy, and what they cost.** They prune hard with depth: 703 of the 743 real level-21 parents of the
  (22,61) run contain one of the 398, and so do all four (22,61) candidates. But each parent costs 1.3 to 5x more
  (3,875 deletion patterns against 635), so as built, a (22,61) slice would only be about 15% cheaper. The two hot
  paths are named (a full containment scan per candidate at levels 12-13; the pattern path at 17-18).
- **Three agents launched in parallel, disjoint files:** integration (run-dag2 `--forbidden-set` and `--ubar 22=60`,
  prune, the 23-vertex limit in udfilter, the blind checker, a `u23-slice.sh` runbook, an end-to-end Mode 398 run
  checked level by level against Mode 74 minus containment); speed (anchored containment and cheaper patterns,
  shippable only if byte-identical to the current Mode 398); and `enum2` with the 398 plus a replay tool (gate G4).
- **By-products for OEIS** (in `research/gp-10/OEIS-DRAFTS.md`, the human's to submit): A308349(10) = 324,
  A059103(10) = 91,658, A350507(10) = 105,680, and the A186705 bound update.

## Supervisor notes

- The reach table for (23,65) with root k = 5 and u-bar(22) = 60: windows 14..20, 17..23, 20..27, 23..30, 26..33 at
  levels 10-14 (as for (22,61)), then 29..37, 33..41, 37..43, 41..46, 45..50, 50..53, 55..56, 60, 65 at 15-23: one
  edge wider at the sparse end than (22,61)'s from level 15, plus a level. Expect several times u(22)'s ~165
  machine-hours before the 398 give any back; the pilot measures it before any fleet launches (gate G2).

## 2026-09-26: integration landed

- The integration builder's work (run-dag2 `--forbidden-set` and guarded `--ubar`, prune with `udfilter -s 398`
  and `UPPER[23] = 65`, udfilter raised to 24 vertices, `check/udcheck398.py`, `--verify-stages`, verify-chain for
  sliced runs, `coordination/cloud-workers/u23-slice.sh`) was reviewed and landed. Its two deviations were right:
  `udcheck.py` is GP-10's pinned trusted kernel, so `udcheck398.py` hash-checks it and executes those exact bytes
  with only the loader replaced; and prune needed an explicit u-bar(23).
- Supervisor checks on the landed copy: udfilter rebuilt byte-identical (`6e0771bb`, `3dad0ca8`); `selftest-398.py`
  43/43; `defaults.py --baseline <the committed run-dag2.py>` DEFAULTS PASS (Mode 74 reach.json and run-config.json
  byte-identical to the landed driver's on all four recorded targets). Without `--baseline` the test fails closed,
  but its message wrongly said "the baseline does not" differ; corrected to say no baseline was given.
- Its end-to-end run at (17,43): every Mode 398 level file equals the Mode 74 file minus the graphs containing one
  of the 324, byte for byte (150 files); AMP's 7 known graphs kept. Cost notes for gate G2: udfilter -s 398 is 4 to 7
  times the per-graph cost of -s 74, so REPORT-398's prune estimate was low by that factor; stage verification adds
  0.9 to 10 ms per graph.

## 2026-09-26 ~02:00: the pilot (gate G2) launched

- `u23-slice.sh` now takes `U23_FORBIDDEN_SET` and keys run directories by set and slice level. Found while
  designing the pilot: its prefix sharing matched sibling directories on target and slice count only, so a run sliced
  at level 12 (whose level-13 files are partial) could have been hard-linked into a run sliced at 13, where `--resume`
  would accept the partial files because their own manifests describe them consistently. The production combination
  (398, level 13) keeps its tested name. Tested locally on (16,41) in both modes, two slices each: prefixes shared only
  within a mode, AMP's (16,41) graph kept by both. (A first test on (13,30) was refused by prune.py, correctly: there
  is no proved bound on u(13), so TU pruning there would be unjustified.)
- Six cloud workers fired 15:57Z (JOBS.md has the routine and session ids): p1..p4 run (23,65) in Mode 398 on eight
  hash-slices of level 12 (1920 slices; indices 0, 240, ..., 1680), about 1/240 of the tree above level 12; c1 and
  c2 run (22,61) on the same two slices, Mode 398 and Mode 74, to measure like for like what the 398 buy and to check
  that the Mode-398 (22,61) top level stays empty. Each worker also rebuilds the prefix (levels 10-12) itself.

## 2026-09-26 ~02:45: the first like-for-like measurement, and a surprise

- c2 (Mode 74) regenerated levels 10-12 byte-identical to the u(22) production run (49 of 49 comparable files), and
  its slice 0 of 1920 cost 356 s above level 12 (extrapolated ~190 machine-hours for the whole (22,61) tree, in line
  with u(22)'s ~165): the landed pipeline reproduces u(22) exactly and at the same cost.
- c1 (Mode 398) on the same slice: **691 s, 1.94 times Mode 74**, although its tree is 4 to 20 times smaller from
  level 16 down (level 17: 960 kept against 8,835). Generation is 84% of the time: per parent, Mode 398 costs 2.4 to
  5.7 times Mode 74 at levels 13-16 (3,875 deletion patterns against 635). Both top levels empty, as they must be.
- So Boris Alexeev's hypothesis (the 398 make u(n) cheaper) is true of the tree and, as implemented, false of the
  clock. The speed agent was sent the measured per-level profile; p5 was added to run (23,65) in Mode 74 on p1's
  slices, since for u(23) either mode is sound (Mode 74's tree is larger but its top level can be filtered by the
  398 afterwards) and the faster one should run the fleet.

## 2026-09-26 ~03:40: gate G4's tool landed (enum2 with the 398, replay-398.py)

- The enum2 agent extended the independent Python enumerator to the 398 (worktree review: only `enum2/` changed; the
  u(22) engine is kept verbatim as `--engine reference`; the new `fast` engine merges isomorphic rooted patterns,
  3,875 -> 3,387, and is checked against the reference engine, brute force and udenum). Its checks: Mode 74 still
  reproduces all 92 u(22) crosscheck shards field by field; 22 of 22 cells equal udenum Mode 398 (71,320 = 71,320);
  order 10 by naive closure gives exactly 105,680; every red control red. `replay-398.py` samples a stated,
  seeded fraction of every production shard and compares enum2's children with production's as full sets.
- The agent had tested the replay only on runs from a patched copy of the driver. Supervisor re-run on the LANDED
  pipeline's output (the (16,41) Mode 398 runbook test, two slices at level 12, fraction 0.2, seeds recomputed in
  full): 1,909 parents sampled, 885 production children compared, 0 mismatches, 0 unreplayable cells; all six red
  controls red (mutated parent, dropped record, wrong block, the two wrong checks, a member of the 324 dropped).
  `results/replay-landed-16-41/`.

## 2026-09-26 ~04:40: the first (23,65) slice, and the size of u(23)

- p5, (23,65) in Mode 74, slice 0 of 1920 at level 12: complete through level 23, top level empty. The tree is about
  35 times heavier than (22,61) on the same slice: level 16 has 3.17 million children (against 88 thousand), and
  generation at parent levels 16-18 is about 80% of the cost (the reach windows are one edge wider at the sparse end,
  and that compounds over several levels).
- A supervisor unit error, caught before any decision rested on it: `pilot_cost.py` summed shard wall times, which
  run four at a time, so its "machine-hours" were core time. Fixed to estimate elapsed time per cell. Corrected
  estimates for the whole tree above level 12, on 4-core machines: (22,61) Mode 74 about 220 hours (u(22) measured
  about 165); (22,61) Mode 398 about 490; (23,65) Mode 74, from this one slice, about 2,300 hours, probably an
  underestimate since slice 0 was the lighter of the two (22,61) slices.
- So u(23) is an order of magnitude beyond u(22). The fleet is not sized yet: the other seven (23,65) slices, the
  Mode 398 pair on p1's slices, and the speed agent's result come first.

## 2026-09-26 ~04:55: the like-for-like pair on (23,65)

- p1 (Mode 398) and p5 (Mode 74) on the same slice 0 of 1920: elapsed 6,230 s against 4,274 s (Mode 398 1.46 times
  slower; on (22,61) the same comparison was 2.2 times). Both top levels empty. Kept graphs, Mode 74 over Mode 398:
  1.2x at level 13, 1.5x at 15, 2.3x at 16, 4.6x at 17, 10.8x at 18, 21x at 19, 28x at 20. Mode 398 already costs
  less at level 19 (714 s against 999 s) and about the same at 18; it loses at levels 14-17, where the pruning is
  still modest but every parent pays for 3,875 deletion patterns.
- One-sample estimates for the whole (23,65) tree: Mode 74 about 2,300 machine-hours, Mode 398 about 3,300. The
  speed agent's per-parent work at 13-17-vertex hosts decides whether the 398 pay for themselves.

## 2026-09-26 ~05:30: p3 blocked by the permission classifier; three more (23,65) slices

- p3 never ran: the cloud session's auto-mode classifier denied the detached launch of `u23-slice.sh` ("Create
  Unsafe Agents"). The worker stopped without working around it, as it should. The supervisor has NOT re-fired it:
  the denial covers pursuing the same outcome from another session, and allowing that command is a permission
  decision for the human. The pilot does not need p3 (six other (23,65) Mode-398 slices and p5's two). For the fleet
  it matters: one launch in seven was blocked, so a fleet needs the runbook command allow-listed in the cloud
  environment's permissions first, which is the human's call.
- (23,65) Mode 398 so far: slices 0, 240, 720 at 6,230, 7,290 and 8,564 s elapsed (mean 7,362 s; about 3,900
  machine-hours for the whole tree on these three); every top level empty.

## 2026-09-26 ~07:00: a lever on the machine-hours: the six TU gadgets, generalised by linear algebra

Liam asked for ways to cut the machine-hour demand. The one measured so far is large.

- **The idea.** In an injective unit-distance embedding every 4-cycle of unit edges is a rhombus (four unit vectors
  summing to zero pair into opposite pairs; the other pairings put two vertices on one point), so each 4-cycle
  u-v-w-x gives p_u + p_w = p_v + p_x. Linear algebra over all of a graph's 4-cycles then forces (a) collisions,
  e_a - e_b in the row space, so the graph is not unit-distance, or (b) hidden edges, e_a - e_b = +-(e_u - e_v) with
  uv an edge and ab a non-edge, a forced unit distance, which prunes exactly as the TU gadgets do (PRUNING.md L2, at
  a target with M >= u(N)). The six gadgets are small instances of (b): the enum2 agent re-proved them this way.
  Both rules are hereditary, so they can act at every level like the gadgets.
- **Measured** with `tools/rhombus_probe.py` (a prototype, mod 2^61-1) on the enumerator agent's samples of KEPT
  graphs of the real (22,61) tree, i.e. graphs that already survived the six gadgets. Further pruned: level 13 6-12%,
  14 20-43%, 15 39%, 16 58%, 17 88%, 18 91% (main cells; 1,500 graphs each). Controls: K2,3 -> collision, gadget 0 ->
  hidden edge, Moser spindle and unit rhombus -> nothing, and none of AMP's 56 known densest graphs (0 to 21 points)
  flagged. On the 324 minimal forbidden graphs: 218 hidden edge, 3 collision, 103 neither.
- **Rough effect on (23,65)**, scaling slice 0's per-level generation by the survival of the parent level: about a
  third of the current cost, before any other saving. The (23,65) graphs are sparser than (22,61)'s at the same
  level, so the real rates must be re-measured on (23,65) samples.

## 2026-09-26 ~07:00: the rhombus rule measured on the (23,65) tree itself; two builders launched

- **Sampler** (`$S/rh65/descent65.py`, speed.py's sampled descent with the pilot's (23,65) reach table): level-12
  stage = the production keep files, every one hash-equal to the pilot's hashes.json (12-23 recomputed, its keep
  file hash-equal too); from a uniform level-12 sample each level keeps a uniform sample of its TU-kept graphs.
- **Mode 74 tree, 1,500 graphs per level** (seed 20260926): flagged 10.1 / 19.5 / 30.0 / 48.3 / 58.7 / 73.5 % at
  levels 13..18 (collisions about a quarter of them). By heredity (a flagged node's canonical descendants are all
  flagged: the parent is an induced subgraph), level L+1's generation from the unflagged level-L parents costs
  0.87 / 0.81 / 0.71 / 0.56 / 0.42 / 0.31 of the current (udenum CPU on the sample, flagged against unflagged).
  Lower than on (22,61) (39 to 91 %), as expected from the wider sparse windows.
- **Projected slice cost** (`$S/rh65/project.py`, pilot per-level costs times the retention; prover at 50 us/graph):
  Mode 74 4,274 s -> 2,111 s (x0.49, ~1,130 machine-hours for the tree); Mode 398 6,541 s -> 4,087 s (x0.63), from
  small 398-free subsamples at levels 17 and 18 (110 and 31 graphs), to be replaced by the Mode-398 descent (w3).
- **The six gadgets are special cases**: each gadget's own pair is forced by its 4-cycle rows (all six checked).
  And the 4-cycle rows are exactly the root matrix of AMP's refutation trees in `check/udcheck.py`
  (`four_cycle_rows`, moves L1a and L2 with omega = +-1): the rule is depth-0 AMP applied hereditarily.
- **Spec** `RHOMBUS-SPEC.md` (lemma, schema, contracts). Launched: a prover builder (C `filter/udrhombus`, prune.py /
  run-dag2.py `--rhombus`, runbook `U23_RHOMBUS`, PRUNING.md L5, tests incl. B10 and known56 positive controls, red
  mutants, (17,43)/(18,46) end-to-end) and a blind checker builder (`check/udcheck_rhombus.py`, kernel by subprocess,
  18+ red controls). The pilot: s1680 landed (5,470 s, empty top); Mode 398 mean now 6,541 s (~3,490 h).

## 2026-09-26 ~07:10: triangles on top of the rhombus rule; the B10 positive control; a heavy Mode-74 slice

- **Triangle orientations** (`tools/triangle_probe.py`): every triangle {a<b<c} has z_c - z_a = w^s (z_b - z_a),
  w = e^(i pi/3), s = +-1; triangles on a common edge have opposite sides (else their third vertices coincide), so
  each edge-connected triangle component carries one bit, the mirror fixes one. A graph is closed when every
  assignment forces a collision or a unit distance on a non-edge (z_a - z_b = zeta (z_p - z_q), zeta a sixth root of
  unity), over F_(2^61-1) as a stand-in for Q(w). This is AMP's L3 split on the (1,1,1) three-edge relation, then L1a
  and L2. On the w1 samples of the (23,65) Mode-74 tree, rhombus + triangles flag 52.9 / 74.3 / 87.9 / 97.6 % at
  levels 15 / 16 / 17 / 18 (the rhombus rule alone: 30.0 / 48.3 / 58.7 / 73.5 %).
- **Positive controls** (the sense that matters: a real unit-distance graph must never be refuted): AMP's 56 known
  graphs: none flagged by either rule. GP-10's 32,653 embedded B10 graphs: zero rhombus collisions, zero
  collision-only triangle closures, zero inconsistent triangle components (9,712 carry a forced unit distance under
  the rhombus rule and 720 more close only through forced unit distances, legitimate for non-faithful unit-distance
  graphs; the builder checks such pairs against the exact embeddings). On the 509 refuted B10 graphs the two rules
  refute 39 by collisions alone (31 + 8).
- **Mode 74, slice 960** (p5): 10,497 s against slice 0's 4,274 s, deep levels about five times bigger (level 18:
  4.7M children against 0.96M). The Mode 74 vs 398 comparison therefore rests on nothing yet; wait for p1's Mode-398
  slice 960, the like-for-like pair.

## 2026-09-26 ~07:20: rhombus + triangles, projected cost

`tools/combined.py` on the w1 samples, udenum timed side by side on all and open parents (the box is shared, so
cross-run timings are not comparable; the earlier rhombus-only retention figures were timed within one run too).
Generation retention of level L+1 with both rules: 0.75 / 0.60 / 0.49 / 0.20 / 0.12 / 0.028 for L = 13..18
(children 0.68 / 0.58 / 0.40 / 0.29 / 0.11 / 0.029). `tools/project2.py` with a prover at 0.5 ms per graph:

    Mode 74 slice 0     4,274 s -> 1,164 s  (x0.27)
    Mode 74 slice 960  10,497 s -> 1,721 s  (x0.16)

About x0.2 on the two-slice mean: ~3,900 machine-hours to ~800, and the prover itself is then a third of what is
left, so its speed matters. Results in `results/rhombus-2026-09-26/`. A third builder (triangle case-tree prover,
RHOMBUS-SPEC Section 4) is running beside the rhombus prover and the blind checker.

## 2026-09-26 ~07:30: fast Mode 398 landed (23b111659); the prune step's 398 re-check is now the bottleneck

- The speed builder's `udenum` (84adaddf, `enum/REPORT-398-SPEED.md`) is byte-identical to a99b130a on everything
  tested and 4.4x to 25x faster per parent (398-free parents: L15 5.9x, L16 9.4x, L17 8.8x, L18 6.4x). Supervisor
  re-ran guards, regress-74, brute10 and the identity final group from the landing worktree: all pass.
- **Projection for the (23,65) Mode-398 slice** (5-slice pilot mean 6,541 s): generation ~4,900 s -> ~580 s with the
  per-level speedups; the prune step's `udfilter -s 398` (1,242-1,310 s per slice, 0.65 ms per child against 0.078 ms
  with set 74) then dominates. That re-check can only catch a SUPERSET (a generated graph containing one of the 398),
  which costs time but never soundness; `--verify-stages` re-checks every stage record against all 398 anyway (now
  with the fast containment). Planned, after the rhombus integration lands: prune with udfilter's set 74 in Mode-398
  runs (TU verdicts and the 74 re-check), leave the 398 re-check to the stage verification, amend CONTRACT and
  PRUNING.md. Then a slice is ~1,000 s before the rhombus/triangle rules, which shrink the tree on top.
- The cost numbers are projections; pilot v2 (the new pipeline, four slices including the heavy 960) decides.

## 2026-09-26 ~07:55: the like-for-like slice-960 pair (first pilot, old binaries)

p1's Mode-398 slice 960: 12,157 s (generation ~9,026 s elapsed, udfilter -s 398 re-check 2,196 s, rest of prune
248 s, stage verification 686 s); p5's Mode-74 slice 960: 10,497 s. Mode 398 is 1.16x Mode 74 on the heavy slice
(1.46x on slice 0), but its tree is far smaller where it matters: level 18 has 584k children against 4.7M, level 19
70.5k against 1.31M. With the fast binary (5.9x to 9.4x per parent at levels 15..18) Mode 398's generation should
fall to roughly 1,300 s on this slice, and with the prune step's re-check on set 74 its filter to ~260 s: ~2,000 s
against 12,157 s, before the rhombus/triangle rules. So the fleet configuration is Mode 398 with the fast binary.
The first pilot's six Mode-398 slices average 7,477 s (~3,990 machine-hours); pilot 2 (q1..q3, the fast binary on
the same six slices) measures the binary alone; pilot 3 measures the full pipeline.

## 2026-09-26 ~08:20: triangle prover landed; literature; referee; Boris note drafted

- `filter/udtriangle` landed (625b59be0, 90121f009): the supervisor's re-run of `enum/test-triangle/run.sh` from the
  landing worktree passed every step (B10: 0 refuted, all 10,432 tu trees followed by exact embeddings to true unit
  leaves; AMP's 56 untouched; 0 disagreements with the prototype on 9,000 (23,65) graphs and 3,000 random ones;
  15,000-22,000 graphs/s/core at levels 15-19; a Python checker runs ~15x the prover's CPU, so replay cost matters).
- Literature (`LITERATURE-RHOMBUS.md`): AMP's moves on Globus-Parshall's Lemma 2, used in the literature only on final
  candidates; AMP's Table 1 counts are full censuses (our unpruned run reproduces their 149 at (21,57)); nearest
  precedent Kurz's matchstick-graph pruning.
- Adversarial referee (a Fable model, read-only): no FATAL objection; five MAJOR enforcement items (exact keys and
  both tree children, arbitrary-precision ints, the chain checker, the tri checker/flag contract, binding controls
  through the checker) adopted as RHOMBUS-SPEC amendment 2 (c39b71f6a) and relayed to the three builders concerned.
- `NOTE-FOR-BORIS-DRAFT.md`: a short note answering his second follow-up, for Liam; claims no u(23) result.

## 2026-09-26 ~08:45: rhombus + triangles on the Mode-398 tree (w3)

The Mode-398 descent (seed 11, 20,000 level-12 roots, the fast binary for the measurement) with both rules:
generation retention of level L+1 0.78 / 0.60 / 0.58 / 0.50 / 0.115 / 0.087 for L = 13..18 (children 0.73 / 0.76 /
0.50 / 0.25 / 0.096 / 0.087). On the first pilot's six-slice Mode-398 cost structure (old binary) the rules alone
give 7,477 s -> ~2,380 s per slice (x0.32). The fast binary and the set-74 prune re-check multiply on top; pilot 2's
per-level data (the fast binary on the same six slices) will replace these projections. The w2 Mode-74 sample gave
x0.42 / x0.36 on slices 0 / 960 (the first sample x0.27 / x0.16): deep-level rates vary by sample, so the fleet is
sized from measured slices only.

## 2026-09-26 ~09:00: the blind rhombus checker landed (81ff2c66e)

`check/udcheck_rhombus.py` + `check/selftest-rhombus.py` (written blind to both provers): Section 2 rules 1-6 in
Python ints, exact keys with duplicate-key refusal, kernel records handed to the hash-pinned udcheck.py/udcheck398.py
by subprocess on a derived file (their ACCEPT/UNKNOWN cross-checked against its own tally), `tri` records routed to a
pinned `tri_verify.py` when present (TRI_VERIFY_SHA256 to be set when the tree checker lands). Selftest 279 passed
(101 distinct red controls incl. the binding int64 wraparound, repeated cycle vertex, a real-4-cycle swap, zero-target
fakes on the Moser spindle, the six gadgets forced exactly over Q, GP-10's 324 at 218 tu / 3 collision / 103 neither).
Supervisor re-run from the landing worktree: 279 passed, 0 failed. Throughput 23-24k records/s quiet, 12-15k/s under
SMT contention. Notes for the integration (relayed to the prover builder): the chunked checker summary must carry the
rhombus/tri counts; R2's soundness rests on prune.py's UPPER guard, which the checker cannot see.

## 2026-09-26 ~09:10: pilot 2's first slice: the fast binary in production

q2's slice 240 ((23,65), Mode 398, the fast udenum, runbook unchanged): every level's children and kept counts are
IDENTICAL to pilot 1's slice 240 (a whole-slice identity check in production). Generation 4,904 s -> 540 s (x9.1),
stage verification 520 s -> 115 s, prune step 1,865 s -> 1,590 s (the udfilter -s 398 re-check 1,663 -> 1,431 s).
Slice total ~7,290 s -> ~2,250 s. The prune step's 398 re-check is now ~64% of the slice: asked the prune integration
builder to add `--prune-filter-set 74` (the re-check guards only a superset; the stage verification repeats it).

## 2026-09-26 ~09:40: the tree checker landed; the three independent pieces agree

`check/tri_verify.py` + `check/selftest-tri.py` (blind; 176 expectations, 57/57 mutants of the checker killed, the six
binding mutants of amendment 2 each rejected by it and accepted by a reference checker carrying exactly that bug;
supervisor re-run 176/0) landed as cecfe962a; its sha256 is now pinned in `udcheck_rhombus.py` (03f8b6684).
Cross-check: udtriangle's certificates on the w1 samples (levels 13-18), the 17,652 reach-kept level-17 graphs, the
level-19 children and GP-10's 32,653 embedded B10 graphs (32,004 certificates) are ACCEPTED by tri_verify.py's CLI and
by udcheck_rhombus.py (kernel for the unknown records, exact tri_tu / tri_refuted counts), every file. The prover and
the two checkers were written by three agents blind to one another's code. Throughput of tri_verify: ~4,200 records/s
end to end on the natural mix (slower on large trees); production replays in parallel chunks.
Pilot 2 so far: slices 0, 240, 720, 1200 identical to pilot 1 at every level, 2.6x to 3.9x faster per slice.

## 2026-09-26 ~10:15: pilot 2 complete; the integration landed; pilot 3 fired

- **Pilot 2** (the fast binary, runbook unchanged) on all six slices: every level's counts identical to pilot 1;
  slices 0 / 240 / 720 / 960 / 1200 / 1680 took 2,440 / 2,246 / 2,449 / 4,670 / 1,332 / 1,939 s (pilot 1: 6,230 /
  7,290 / 8,564 / 12,157 / 5,151 / 5,470). Mean 2,513 s, ~1,340 machine-hours for the tree (pilot 1: ~3,990). The
  prune step's 398 re-check is now the largest single cost (795-2,704 s per slice).
- **Integration landed** (fast-forward to 26323bdfa): udrhombus, prune.py/run-dag2.py `--rhombus`, `--triangles`,
  `--prune-filter-set 74`, verify-chain dispatch and refusals, PRUNING.md Section 5, runbook `U23_RHOMBUS`,
  `U23_TRIANGLES`, `U23_PRUNE_FILTER_SET`. The builder's end-to-end controls ((16,41) both modes, (17,43), (18,46);
  plain / rhombus / triangles; 12 runs) keep every known graph, keep files nested tri <= rh <= plain on all 79 pruned
  levels, CHAIN OK everywhere; (18,46) wall 414 / 392 / 355 s. Supervisor re-run (SKIP_LONG) of the suite: all pass.
  CONTRACT amendments 2 and 3 written.
- **Pilot 3** fired (r1..r3): `U23_TRIANGLES=1 U23_PRUNE_FILTER_SET=74`, Mode 398, the fast binary, the same six
  slices. It measures the fleet's pipeline; the top level must stay empty.
- Follow-ups noted by the builder: udtriangle's stats line should name a `mutant=` build (so prune.py's preflight can
  refuse a red-control udtriangle); `check-prune-sample.py` does not know the rules.

## 2026-09-26 ~12:30: pilot 3's first slices; the fleet plan

- **Pilot 3** (the full pipeline: fast Mode-398 udenum, `--triangles`, `--prune-filter-set 74`): slice 240 816 s
  (pilot 1 7,290 s, pilot 2 2,246 s: x8.9 and x2.8), slice 1200 432 s (5,151 / 1,332: x11.9 and x3.1). Top level
  empty; kept <= pilot 1 at every level (level 18 of slice 240: 65,015 -> 10,639). r1/r3 (slices 0, 960, 720, 1680)
  were refused at the detached launch by the cloud classifier and re-fired with the owner's authorization in the
  prompt (JOBS.md); both launched.
- Remaining cost per slice (slice 240): generation 336 s, prune 422 s (udfilter set 74 143 s, the certificate replay
  134 s single-process, the prover and bookkeeping ~145 s), stage verification 56 s. Projected tree: roughly
  400-450 machine-hours (pilot 1: ~3,990).
- **Before the fleet** (Liam, 2026-09-26: "boost concurrency"; "any other efficiency wins"): parallel certificate
  replay in prune.py (~10-15%), per-slice cleanup of run directories with a disk guard (required at 15-30 slices per
  worker), the G4 replay fraction 0.002 -> 0.001, interleaved slice assignment (worker k of W takes k, k+W, ...).
  Fleet shape: ~96 workers x 20 slices, fired in waves (the account's concurrency limit is unknown). Later, larger:
  drop the separate udfilter pass (the rules subsume the gadgets; the stage verification repeats the containment
  check) and fuse the prover into the generator. A second fleet on OpenAI's cloud (codex) needs a codex login.

## 2026-09-26 ~13:00: cross-model reads (gpt-6-astra via codex); pilot 3 at four slices

Liam suggested codex builders for load and redundancy; codex was logged in again (Pro, 22% of the week). Three jobs
(`results/g5-cross-model-2026-09-26/`):
- **A third checker, blind** (GPT, standard-library Python, from RHOMBUS-SPEC.md alone in an isolated directory):
  ACCEPTS all 57,659 records of seven certificate files (rhombus and tri, the samples, level-17 parents, level-19
  children, B10) with counts equal to the Claude checkers'; its selftest 195 cases (156 red, 39 valid) pass. Every
  certificate now has three independent acceptors from two model families.
- **The fast-udenum rewrite, reviewed**: no case where it loses a child or changes output; the reviewer independently
  reproduced 3,387 orbit representatives, 488 omitted patterns and 1,843 graph classes, ran 120 old/new comparisons
  and 385 ordered-family hash comparisons, and found no new undefined behaviour up to 23 vertices.
- **G5 soundness read**: Lemmas R and T, R1/R2, heredity, the exact use of 65 + 1 > u(23), trees with different
  forced non-edges: sound; neither checker accepts anything unsound; no prover refuted any of 1,200 exactly embedded
  lattice graphs. Two findings: (1) "FATAL" for the AUDIT, inherited from u(22): `verify-chain.py` takes the cells to
  inspect and the parent windows from the run's own summary, so a tampered run with a cell omitted (it lost the known
  (16,41) graph) or with pruned entries deleted still reports CHAIN OK; (2) MAJOR: run-dag2's resume reuses a cached
  prune result without checking its target, checker identity or ACCEPT line. Both sent to the prune builder: coverage
  derived independently from the recomputed reach table, "PARTIAL" never reported as OK, a summary-only coverage audit
  of the 48 u(22) slices; resume re-runs unless target, checker hash and ACCEPT line match. G5 stays open until the
  fixes land and the reviewer re-reads them. Neither finding touches the fleet's computation (run-dag2 builds every
  cell from the reach table itself); the coverage audit runs on the pushed summaries afterwards.
- Pilot 3 so far: slices 240 / 1200 / 720 / 1680 at 816 / 432 / 398 / 363 s (x8.9 / x11.9 / x21.5 / x15.1 against
  pilot 1), top levels empty, kept sets nested; slices 0 and 960 running.

## 2026-09-26 ~14:00: pilot 3 complete (and a resume artefact in its timings)

Slices 0 / 240 / 720 / 1200 / 1680: 743 / 816 / 398 / 432 / 363 s (pilot 1: 6,230 / 7,290 / 8,564 / 5,151 / 5,470;
x8.4 to x21.5). Slice 960 reports 61 s, but that is an ARTEFACT: r1's container restarted, and 47 of the slice's 61
cells above level 12 were resumed from files already on disk, so their recorded timings are ~0; only levels 19-21 were
timed (level 19 generation 46.9 s against pilot 2's 617.6 s). Its kept counts are real (level 18: 404,930 in pilot 1
-> 66,292; level 19: 45,659 -> 3,440) and its top level is empty. Scaling its pilot-2 time (4,670 s) by the other
slices' pilot-3/pilot-2 ratios (0.16-0.36) puts it near 1,000-1,600 s. Estimate for the tree: ~350-400
machine-hours with the G4 replay (pilot 1: ~3,990). The fleet collector must treat resumed cells' timings as unknown
(`resumed: true`), never as zero cost.

## 2026-09-26 ~14:05 (fired 03:06-04:05Z): the fleet (gate G3) is running

**Launched.** 96 routines `u23-fleet-fNN` (coordination/cloud-workers/JOBS.md, `## u23-fleet`), twenty interleaved
level-12 slices each, the pilot-3 pipeline (Mode 398, `U23_TRIANGLES=1`, `U23_PRUNE_FILTER_SET=74`, the G4 replay at
0.001, per-slice cleanup). Fired 03:06-03:22Z.

**The cloud cap is about 48 sandboxes.** 48 started (f01-f44, f46, f47, f49, f50); f45, f48, f51, f52 logged `Sandbox
allocation failed` and never ran. The remaining 48 tags (those four and f53-f96) are wave 2, fired as wave-1 workers
finish; every trigger is already made. Two waves of ~3.5-4 h: the whole tree about 10:30-11:30Z.

**One worker lost, re-fired.** f30 kept itself alive with ScheduleWakeup only; its sandbox was reclaimed ~5 min after
its turn ended, killing the runbook mid-slice, and the wakeup died with it (no event after 03:22:59Z, no push). Re-fired
03:55Z. The working keep-alive (f04's, found in its log) is a harness background Bash waiter with an anchored pgrep:
zero model turns while the runbook runs. The brief's step 5 now prescribes exactly that for wave 2 (and forbids
ScheduleWakeup alone and the unanchored `pgrep -f u23-slice.sh`, which matches its own waiter).

**First results.** 95 slices done by 04:00Z: every top level (23,65) empty, every G4 replay PASS (~1,100-1,300 sampled
parents each, children identical to enum2's). Slices run 8-10 min after a worker's first (17-30 min, which builds the
level-12 prefix). The summary-only coverage audit (the G5-fixed verify-chain.py, side branch
claude/answering-alexeev-u22-g5) already runs on the pushed files: all 69 slices it saw audited, every prefix cell's
parents recorded; its one PROBLEM was the slices not yet done.

**Load.** 44 polling workers cost ~6 % of the five-hour usage window per hour (measured from the usage endpoint).

**G5 fixes** (verify-chain coverage derived from the target; resume re-validates prune steps) are on the side branch,
kept OFF the fleet branch until the fleet is done so every slice runs one code version; GPT is re-reading them.

## 2026-09-27 ~07:50 (21:50Z on 09-26): the fleet complete; the DRAFT; point 6 under way

**The fleet.** All 1,920 slices have a complete copy (the last results pushed by 20:39Z; the collector saw 1,920 of
1,920 at 21:34Z). The generator (`tools/write_result.py`, gate G6) ran every tool on one snapshot (the root's
fingerprint unchanged while they ran) and wrote `RESULT-u23.md` (commit ac59e1ecc), state **COMPLETE**: coverage
1,920 of 1,920; the summary audit (the G5-closed verify-chain.py on the side branch) `COVERAGE (summary only) OK`
over 1,955 summaries; the only graph the filter-only prune kept at (23,65) is s50's, refuted by a certificate both
checkers accept; G4 PASS on all 1,920 chosen copies (1,955 with the duplicates); the aggregate's 8 identities hold and
its `--perturb` red control breaks three; 35 slices hold several copies and every pair agrees. By the slice-time
rule, ~362 machine-hours (median slice 557 s; s344 the heaviest at 13,271 s). The statement stays conditional: "If
the gates of Section 6 are all green, u(23) = 64". G0 (the literature recheck) and G1/G2 are only partly re-derived
by the generator, and everything public is Liam's.

**New checks landed today.** `tools/level22_control.py` (CONTRACT 4.3): Engel et al.'s 35 known (22,60)
configurations, the 14 with minimum degree >= 4 all kept at level 22 (s50, s344, s1647), none of the 29 kept (22,60)
graphs in two slices; red three ways. `tools/top_level_check.py` now requires a REJECT naming the proof tree
from its tamper control (it had counted any nonzero exit, and logged an empty reason). CONTRACT amendment 4: the
fleet sliced at level 12, not 13.

**Sixteen slices, not fifteen, have a restarted copy.** The draft counts 16 slices with a resumed copy and a fresh
one: the 15 that f97-f100 re-ran, and s600, whose counted copy is a fresh one from the re-fired f25 (so the audit
binds it). s600 was not in the "every copy resumed" set, so it is not in the certification sample either.

**G5 point 6: Liam chose option 1** ("happy for you to do that yes"). `u23-verify` (JOBS.md): the 15 restarted slices
plus `random.Random(20260927).sample(the other 1,905, 48)`, re-run by the fleet's unchanged runbook with
`U23_CLEANUP=0`, each run directory checked by the G5-closed `verify-chain.py --check` (the worker's first slice whole;
later slices from level 13, since their hard-linked prefix manifests name the first slice's directory, which
verify-chain refuses inside another run, with the prefix compared byte for byte instead). Tested locally on (17,43)
first, green 3 of 3 and red 3 of 3 for the reason planted (a forged tri witness with every hash rewritten: udcheck
REJECT; a top-level kept graph dropped with every hash rewritten: "is not the embedded and unknown records in order";
a changed prefix file: "prefix differs"). Found on the way: a runbook re-run REPAIRS a tampered file (its resume
recomputes what no longer matches its manifest), so a re-check skips the runbook (`U23_VERIFY_SKIP_RUNBOOK=1`).

**The cloud classifier refused 4 of the 10 workers** ("Create Unsafe Agents") on the brief it allowed for the other
six. With Liam's OK the four were re-fired with the brief's six-hour keep-alive-for-follow-up clause removed: v01, v06
and v10 went through; v04 was refused again, so the clause was not the cause. v04's seven slices (113 586 606 728 885
1006 1043) wait on Liam. `tools/verify_sample.py` judges the sample: it re-draws the random part from the seed,
re-derives every check's verdict from the output itself, and compares each re-run's result files with the fleet's
copy; its red controls catch 5 of 5 on real data. At 21:41Z: **41 of 63 verified, nothing failed** (13 of the 15
restarted, 28 random: every check passed, every re-run identical to the fleet's copy).

Open: v01, v06, v10 (21 slices, s276 the heaviest) finishing ~23:30Z-00:00Z, then the draft regenerated; v04 (Liam);
the G5 side branch merged once the verification is done (it changes code the workers run); the triggers' cleanup.

## 2026-09-27 ~14:10 (04:10Z): the certification sample 63 of 63; the final DRAFT; G5 merged

**G5 point 6, by the sample Liam chose: VERIFY-SAMPLE OK, 63 of 63, 0 problems** (`tools/verify_sample.py`). The 15
restarted slices and 48 drawn by seed 20260927 were each re-run by the fleet's unchanged runbook with nothing deleted,
their run directories checked by the G5-closed `verify-chain.py --check`, every inspected pruned cell's certificates
replayed (69 of 69 in each of the nine whole checks, 61 of 61 in each check from level 13), and every re-run's result
files identical to the fleet's copy of the slice. Nine workers ran in the cloud (v01's s276, the heaviest slice,
checked whole). v04, refused three times by the cloud classifier, ran on the desktop (Liam's call) after ~20 GB of stale
/tmp staging was cleared (each directory checked first: no process in it, every commit landed or pushed). The whole check
of its first slice outgrew the machine (3.9 GB and growing, swap full) and was stopped before anything else suffered;
its seven slices were therefore checked from level 13, with the prefix compared by hash (the prefix computed on the
desktop is byte-identical to the fleet's, which nine workers checked whole). s606, s1006 and s1043 (largest cells about
710,000 records) needed ~4 GB each and passed once Liam had closed sixteen idle Remote Control desks and COINS-AU.

**The final DRAFT** (`RESULT-u23.md`): state COMPLETE, the certification sample 63 of 63. On the way, the generator's
per-slice parser dropped s113 from the random count (a parenthesis after "from level 13": 47 of 48); fixed, and the
certification check now fails closed unless the per-slice lines add up to the verdict's own count (a what-if red control
for it; self-test 39 of 39).

**G5 merged** (32f04c6da): the side branch's verify-chain.py, run-dag2.py `--resume` and prune.py fixes are on the fleet
branch, now that no worker runs the old code.

Lessons. (1) On the desktop, memory, not CPU or disk, bounds a full chain check: verify-chain holds a cell's whole
certificate file in memory, about 5.4 KB per record, so the largest cell predicts the peak. (2) The harness reaps its own
background watchers under memory pressure; detach the work itself (setsid) so only the watcher dies, and cap the heavy
step (`ulimit -v`) so it fails alone. (3) A transcript's modification time is not activity: 261 automated artifact-ledger
records made a desk idle for 26 days look "active six minutes ago".

Open, the human's: G0's literature recheck before anything is public; the reply to Boris; OEIS, arXiv, Zenodo; the
u23 triggers (cron 29 February 2028) to disable by hand.

## 2026-09-27 ~17:45 (07:45Z): G5 round 10 answered; a blind second verifier; the no-doubt programme under way

Liam asked what stands between the DRAFT and "one hundred percent no doubt". The list: the (22,61) control at full
strength, the (21,57) calibration, a third independent check of the one top-level refutation (slice 50), a G5 read of
everything new, G0, and optionally the full re-run of all 1,920 slices. He chose all of it, with the heavy compute
offloaded to codex.

**G5 round 10** (gpt-6-astra, the round-9 session resumed) came back OPEN with four MAJOR findings, all in the checking
instruments: none says the enumeration is wrong. (1) `u23-verify.sh` read an exception in the prefix comparison as
equality. (2) The judge never bound a check output to its slice: a genuine check of s242 under s14's header passed.
(3) The sample could pass with no prefix checked whole. (4) `write_result.py` reached COMPLETE with 62 of 63 slices
missing, because missing counted as "not yet", not as failed. All four are fixed, each with a red control that fails on
purpose:
- `verify_sample.py --self-test`: 12 of 12;
- `write_result.py --self-test`: 51 of 51.
The fixes also bind each new check to its slice's result copy by a digest of the level files checked. It was checked
equal on a real run: 110 files, the same sha256 from the directory and from the copy's `hashes.json`. The sample still
verifies 63 of 63, and its prefixes are one prefix, checked whole nine times. The auditor also put the sample's reach in
numbers: a single faulty slice escapes a 48-slice draw from 1,905 with probability about 97%. That is the case for the
full re-run. Round 11 is reading the fixes.

**The blind verifier.** The two checkers that accepted slice 50's certificate are one implementation (`udcheck398.py`
executes `udcheck.py`'s pinned bytes). So codex wrote a third, blind: it was given the format (the reference checker's
docstring), `PROOFS.md` and the one graph and certificate, and forbidden to read anything else. It checks with exact
arithmetic, and it derived for itself:
- the root's rows, as the rhombus equations of all 57 four-cycles;
- a sufficient contradiction criterion for the L1b leaves.
It found the field's quartic irreducible (Kronecker) and the root isolated (Sturm). **BLIND VERDICT: ACCEPT.** Its
four red controls and three of mine are each rejected for their own reason. It is committed as
`research/unit-distance-23/blind-verifier/`, run by `tools/blind_check.py` with seven tampered copies of each
certificate made afresh, and required by `write_result.py` before COMPLETE. The regenerated DRAFT: COMPLETE, the
headline naming the blind check.

**The (21,57) calibration, first attempt.** It ran unsliced on the desktop and was stopped at level 15 at 06:57Z. Its
run directory was 20 GB and the disk had 7 GB left: whole, the tree does not fit here. It is now 48 codex cloud tasks
(q01..q48, 40 slices each, sliced 1,920 ways like the fleet, each slice's run directory deleted once written), with the
fleet's options and root minimum degree 3.

**Codex cloud as the full re-run's fleet** (`u23-verify-all`, 347 tasks):
- Wave 0 (12 tasks) is under way.
- Three tasks stopped at once: my task text said `git fetch origin`, and a codex container has no remote (the branch is
  checked out for it). The text is fixed and the three were resubmitted.
- Polling each task's status hit HTTP 429 at about 60 tasks, and my collector read the error as a failure. It now pages
  `codex cloud list --json` and treats an error as "retry".

**The (22,61) control** (Claude cloud, k01..k10, fired 05:06Z): at 07:35Z, 712 of 1,920 slices complete, all 712 G4
PASS, and nothing kept at (22,61). `tools/target_check.py` judges both controls: every slice complete, the fleet's
pipeline options, G4 PASS, every keep file equal to its hash, and at the top level nothing for (22,61) and all five of
AMP's graphs for (21,57). Its red controls: 5 of 5.

Lessons. (1) An auditor's reproduction is the best red control there is. All four findings came with a concrete
input that the old code passed, and each is now a what-if. (2) "Missing" is not "not yet". A gate that tolerates
absence can be passed by absence, so a certification needs every planned piece present. (3) Size a whole-tree run
before starting it on the desktop: level 15 of 21 already had 20 GB.

## 2026-09-27 ~21:10 (11:10Z): the full re-run on Claude cloud; G5 rounds 11 to 13; codex cloud's limits measured

**Codex cloud could not be the fleet.** Probes established three facts:
- About 48 tasks run at once: all 48 calibration tasks started within 8 minutes.
- A task stops at about an hour: the 9 long wave-0 tasks went to `error` near 60 minutes.
- A task's results come back only as its diff, which has a size limit. One (23,65) slice's result files are 444 KB,
  and all 48 forty-slice calibration tasks ended `diff_too_large` or empty.

A trivial task, a 32-minute sleep and a one-slice calibration each ran cleanly. (I first read the empty worklog of a
running task as "never started". Wrong: the worklog appears only when a task ends.) Liam was asked whether an easier
route kept the certainty, and there is none. The certificate-to-keep relation of levels 13 to 21 can only be re-proved
by regenerating those levels, about 400 machine-hours wherever it runs. So the full re-run moved to Claude cloud: 48
workers packed longest-first to about 9.6 hours each, with the one-slice driver made cloud-ready (it pushes each slice,
builds its toolchain, and skips already-verified slices after a restart).
- 33 workers were fired, a01 to a33.
- The local classifier refused the 34th trigger creation ("Shared Cluster Mutation"). Liam's call: fire a34 to a48 when
  a01 to a33 finish.
- First results: 7 slices whole-checked, CHAIN OK, identical to the fleet's copies, each check bound to its copy by
  the files digest. No failure.

**The (21,57) calibration** runs on the desktop, sliced, about 50 s a slice. From 190 of 1,920 slices, 4 of AMP's
five graphs are kept already. The **(22,61) control** stands at 1,625 of 1,920 slices, none failing, nothing kept.

**G5, rounds 11 to 13.**
- Round 11 closed three of round 10's findings and found four new ones, all fixed:
  - per-output exemptions, with the sample's 63 outputs pinned by sha256;
  - the blind check bound to the kept graph and its certificate file;
  - the G5-closed run-dag2.py hash accepted in the re-run;
  - a guarded self-test.
- Round 12 found my new control checker shallow: identity labels in one file only, and G4 read from its verdict line.
- Round 13 found it still shallow, on parent coverage, replay stage flags and a full replay's scope. The fix was to stop
  re-implementing a reviewed instrument. `target_check.py` now runs the fleet audit's own checker, the G5-closed
  `verify-chain.py --summary-only`, over every copy. On scratch copies of a real slice it caught 7 of round 13's 8
  reproductions; the eighth, the replay's sampling policy, is now pinned directly.
- Round 14 is reading.

Lessons.
1. When an auditor keeps finding holes in a new checker, the checker is the wrong layer. Reuse the reviewed one and
   pin only what it does not cover.
2. A platform's limits are facts to measure before a fleet is sized on it. Here they were a one-hour task, a diff as the
   only return channel, and a worklog visible only at the end. One probe per job shape costs minutes.
3. Firing 48 sessions through a tool that echoes each trigger in full costs real context; batch it, and record every id
   in a file as you go.

## 2026-09-27 ~21:55 (11:55Z): G5 rounds 14 and 15 answered; a race in my own poller; round 16 reading

**G5 round 14** (three MAJOR) was answered in fc65a372b9:
- A copy the audit never saw (no run-summary.json) now fails. A complete run's audit line must say OK.
- Each G4 replay must cover its mode's scope. That includes the fleet's own replays (`target_check.py --scope-only`, a
  new input to the G4 gate).
- A control that printed a PROBLEM, or no verdict at all, is a failure.

**G5 round 15** (three MAJOR, each reproduced on the real fleet with its totals rebalanced so every layer passed) was
answered in 41060c0184:
- the seed counts were not bound to the seed cell;
- a row that sampled nothing still counted as a row;
- a resumed cell's parents lived only in the history, which my scope check never read.

The fix stops reading the final summary. `target_check.py` imports the pinned `verify-chain.py`, the same bytes the
audit runs, and judges scope against that module's own accepted evidence (`summary_audit()`), pooled over each slice's
copies. Five more rules came from measuring the real data first, then enforcing it:
- every count is an int;
- copies of one slice agree on every audited parent count (the fleet's 35 slices with several copies all do);
- every copy passes, not just one of them (no slice of the fleet or the control has a failing copy beside a passing
  one);
- a copy the audit cannot read in-process fails;
- a malformed row fails.
One of my red controls was caught for the wrong reason: with slices missing, the known-graph control was caught by the
coverage rule. It now drops a graph that is actually kept and counts only the known rule's own line. Self-tests pass
24 of 24 on the control's data and 24 of 24 on the calibration's. The fleet's scope passes: 101 of 101 full-mode and
1,854 of 1,854 slice-mode replays. The DRAFT was regenerated (1b7bd1f9a6): 126 of 126, with three gates still open.

**A race in my poller.** An evaluation printed "136 failing" for the control. The cause was the control's poller
deleting and re-extracting the tree while the checker read it. Both pollers now fetch into a fresh snapshot directory
and swap a symlink atomically. `write_result.py` resolves the link once per tool, so every tool reads a single
snapshot. On a stable snapshot the control has 0 failing.

**Progress at 11:55Z:**
- The control: 1,813 of 1,920 slices, 0 failing, nothing kept.
- The calibration: 249 of 1,920 slices, 0 failing, 4 of AMP's five graphs kept.
- The full re-run: 34 of 1,920 slices verified, no failure.

**Round 16 is reading.** When I resumed codex, the session came back with a writable sandbox. `exec resume` takes the
config default, not the session's own sandbox. It was stopped at 28 seconds, with nothing written, and relaunched
with `-c sandbox_mode="read-only"`.

Lessons.
1. A red control proves the checker can go red, but not which rule turned it red. Aim each control at its own rule's
   line. Otherwise a new, stricter rule elsewhere quietly makes an old control vacuous.
2. A reader and a writer sharing one directory is a race, even when both are mine. Snapshot, then swap.

## 2026-09-27 ~22:15 (12:15Z): G5 round 16 stopped by the provider's classifier; its two leads fixed anyway; a leak in my evaluator

**Round 16 has no verdict.** After nine commands and 2.3M tokens, OpenAI's filter stopped the read ("This content was
flagged for possible cybersecurity risk"), probably because of the audit vocabulary: tampering, bypasses, red controls.
Before the stop, it had re-made round 15's three reproductions and found each one caught. It named two questions it
was about to test. Re-sending, as it stands or reworded, is Liam's decision, not mine (the classifier rule).

Both questions became rules, each measured on the real data first:
- **The exact sample.** A replay row was held only to a lower bound, while the policy draws at least 2 per shard and
  every record of a small shard. Each row must now sample exactly what the pinned tool's own `sample_indices()` draws
  from the audited shards. Measured: 58,458 fleet rows, 41,254 control rows and 3,575 calibration rows all do.
- **The prefix.** Only a worker's first slice replays levels up to 12, and nothing tied the other slices' prefix to
  it. Now every copy's prefix digest (hashes.json, levels 12 and below) must be one a passing full-mode replay has.
  Measured: each run has exactly one prefix, covered by 101 full-mode replays for the fleet, 10 for the control and 1
  for the calibration.

**The leak.** On the calibration, the new prefix rule turned 279 slices red. The cause was my own `evaluate()`,
which wrote each copy's verdict back into the evidence it was given. The self-test's "slice 0 removed" state removed
the calibration's only full-mode copy. The verdicts that state produced were left behind, and the real evaluation
that followed read them. `evaluate()` no longer changes its input. The self-test now ends by re-evaluating the real
evidence and fails on any difference. I proved the guard by putting the old bug back in a scratch copy of the tool:
it reports "0 failing before, 279 after".

**State.**
- Self-tests: 30 of 30 on the control and 30 of 30 on the calibration, each new control caught by its own rule.
- Fleet scope: 101 of 101 full-mode and 1,854 of 1,854 slice-mode replays.
- DRAFT: 126 of 126 (9008df5468).
- Progress: the control at 1,858 of 1,920, the calibration at 285, the full re-run at 51, all 0 failing.

Lesson. An evaluator that writes its conclusions into its inputs is safe only while every rule is local. The first
rule that looks across slices turns every hypothetical the self-test builds into a fact the next run reads.

## 2026-09-28 ~00:30 (27th 14:30Z): the control is complete; G5 round 17; the full re-run hits a memory ceiling

**The (22,61) control is complete.** All 1,920 slices, G4 PASS on every one, and nothing kept at (22,61). The whole
tree had no u-bar override at level 21 and root minimum degree 5 (Lemma D4). It passes every rule in
`target_check.py`, including round 17's (38 of 38 red controls). **The (21,57) calibration** is at 381 of 1,920 and
already keeps all five of AMP's extremal graphs.

**G5 round 16, sent again as round 17**, in a fresh session. Liam's call was softer wording and a fuller account of
the context, and the filter did not trip. The read was OPEN: six MAJOR and one MINOR, all in the checking tools:
- prefix evidence pooled per slice, while the audit pools it per run;
- G4 stage records not required or reconciled;
- replay rows not bound to their run;
- the controls' verify manifests and software unexamined;
- a whole check's PROBLEM lines ignored;
- a crashed re-run judge read as open;
- one red control that could pass for the wrong reason.
All seven are fixed (fd01053593). Each new rule was measured on the real data first, and every run meets it,
including 128,000 stage records and 320,000 verify manifests. Every red control is now aimed at its own rule's line.

**The memory ceiling.** Six slices of the full re-run (s50, s1082, s1535, s1651, s1721, s1814) had their G5 check
killed by the cloud worker's memory cgroup. The kernel log on a06 gave it: `anon-rss:13943008kB`, from the checker
itself, on a 15 GB machine.
- The cause is the checker's design: `lines()` holds a file's bytes, text and line list at once, and a pruned
  cell's certificates are all parsed before they are compared. Its peak is about 12 times the largest certificate
  file.
- Swap was not possible. The sandbox's disk allowance left 11 GB free, and the platform's classifier refused the
  attempt ("Modify Shared Resources"), so that route was dropped.
- PyPy runs the unchanged checker, but its peak was only 4% lower (2,137 MB against 2,052 MB on a (21,57) slice).
- Splitting across machines cannot help: the peak is one cell's certificate file, in one process.

So `verify-chain-lean.py` is the G5 checker with four marked streaming edits and nothing else changed. It runs only
after a G5 check dies of memory, into its own `.lean.txt` record. The judge accepts that record only beside G5
outputs that are all memory kills, with its sha256 pinned (4216d6a5a5).

`lean_diff.py` compares the two checkers byte for byte:
- On 10 older run directories the output was identical. Those directories fail anyway, so the planted faults proved
  nothing there. The faithful-copy baseline was added for exactly that reason.
- The test on real passing (21,57) slices, rebuilt with nothing deleted, is running.

Until the memory-bounded checks land, the DRAFT's state is VERIFICATION FAILED. That is by rule: a recorded failure is
never "open".

Lessons.
1. Size a checker's memory against the heaviest input before a fleet depends on it. The certification sample's
   largest slice (10.2 GB) happened to fit, and the full re-run's heaviest did not.
2. A test on inputs that already fail cannot show that faults are refused. Check that the unchanged copy passes
   first.

## 2026-09-28 ~08:15 (27th 22:15Z): G5 round 18; the memory-bounded checker cleared; the round-18 fixes; more workers

**The memory-bounded checker.** Its side-by-side test on real passing (21,57) slices, rebuilt with nothing deleted,
came back clean:
- identical output on the whole check of slice 0 (with `--check`) and the level-13 checks of slices 1 to 3;
- all 28 planted faults refused by both checkers, each in a cell the check inspects;
- peak memory 2,156 MB for the G5 checker, 302 MB for the lean one.
Five of the six memory-killed slices of the full re-run now pass through it. The sixth (a06's s1721) waits on a06's
disk (below).

**G5 round 18** read the lean checker first. For fixed regular files, the four edits preserve the acceptance
conditions, and it found no lean-only acceptance or bypass in the fallback. It found six MAJOR problems elsewhere, all
in the checking tools, each reproduced by editing the real evidence in memory:
1. the scope-only path skipped the replay pins, so a replay recording another seed passed;
2. a seed check that failed in its details passed, and so did a stage record with impossible parameters;
3. the controls' enumeration and pruning manifests were not checked for success;
4. a verify manifest's stage file was bound only by name, count and (where hashes.json lists it) digest;
5. the re-run judge ignored the re-run's own replay verdict;
6. the report parser let a malformed or self-contradicting report through as open or OK.
All six are fixed, with red controls. The scope-only path had no self-test at all, so the seed reproduction was run
through it as a red/green pair on one copy (G4-SCOPE FAIL with the seed changed, OK without).

One part of finding 4 cannot be fixed from the evidence, and is documented as a limit. For levels 13 to n-3 of the
two controls, no shipped file records the digest of the verified stage file: the runbook deletes those files, and
the verify manifest is their only record (47 of 73 manifests in k01's s0). Two things bind them instead:
- the pinned run-dag2.py hashes the file it verifies, in the same run, and refuses one that changed meanwhile;
- for the (23,65) run itself, the full re-run's G5 check binds every level's digest on a complete run directory.

**My own slip, caught by the self-test:** the new verify-run rule, once it added a reason, suppressed the prefix
rule's reason (43 of 44 controls). Second-pass rules now accumulate their reasons, and none can hide another's.

**More workers.** Liam's call: fire a34..a48 as slots free up, keeping 33 at once. A slot is freed by an a01..a33
worker that has verified all its slices. a34 to a37 went at 21:50Z (4 finished), a38 to a43 at 21:59Z (10 finished).

**a06's full disk was my leftover.** The swap attempt refused on the cloud workers had already begun a /swapfile on
a06, and that file is what filled its disk and blocked its re-check. With Liam's OK, a06 is told to delete it,
re-check s1721, and run `lean_diff.py --check` on its whole s845: the two checkers side by side on a (23,65) slice.

**Progress at 21:52Z:** the full re-run has 1,130 of 1,920 slices verified. The calibration has 957 of 1,920, with all
five known graphs kept. The (22,61) control is TARGET-CHECK OK, 1,920 of 1,920, under every round-18 rule.

Lessons.
1. When an attempt is refused or fails partway, remove what it left behind in the same step. A half-made swap file
   sat unnoticed until it blocked a worker hours later.
2. Aim every red control at its own rule's line, and let rules add reasons rather than replace them. Otherwise one
   rule's reason can hide another's, and the suite still looks green.

## 2026-09-28 ~11:30 (01:30Z): G5 round 19; a06 replaced; the weekly limit; the lean checker on a (23,65) slice

**a06 could not delete its own leftover.** Liam OK'd deleting the /swapfile my refused swap attempt had left, but a
built-in safety check refused `rm -f /swapfile`: a file directly under `/` needs a person at a live prompt, and a
routine-fired session cannot show one. I did not work around it. Liam's call was not to wait on it, so a fresh a06
(cse_017zWysb5UdhSnTmhd1r1W3n) started from scratch on a clean disk. Its s845 passed whole at 23:03Z.
Before firing it I checked, on a copy of the snapshot, that the judge reads two a06 branches correctly:
- s845 still verifies, now with two copies;
- the only change is that s1721's existing memory-kill problems are listed once per copy;
- the certification sample already held two v01 branches.

**The two checkers side by side on a whole (23,65) slice.** a01 had finished, and its first slice's run directory
(s955) was still on disk. `lean_diff.py --check` there gave identical output: exit 0 and 0, CHAIN OK, every
certificate of the 69 pruned cells replayed. Peak memory: 5,042 MB for the G5 checker, 800 MB for the lean one.

**The weekly limit.** Between 23:42Z and 01:00Z the account's weekly limit stopped every Claude turn: this session's,
and every worker's hourly check-in (a06's log: "You've hit your weekly limit · resets 1am (UTC)"). The workers' scripts
kept running as background tasks, and nothing stalled: every unfinished worker had pushed within the hour. A worker
whose container had restarted in that window would have stayed down, with no check-in left to restart it.

**G5 round 19: OPEN, seven MAJOR.** It confirmed the documented limit of round 18 ("substantially correct"; it does not
touch the full-directory checks of (23,65)), and found seven more places where edited evidence still passed:
1. the re-run's replays were judged from their aggregates only;
2. a checker record could claim less inspection than its check;
3. a red control whose baseline failed still counted red;
4. manifests could contradict their own success (a zeroed digest, a child beside an empty file, a REJECT);
5. a deleted software map passed;
6. a report's totals were trusted without its rows;
7. an unexplained FAIL read as open.
All seven are fixed, each with the reviewer's own reproduction as a red control.

Two of my first drafts were wrong, and measuring them first caught both:
- the pruning manifest's certificate TU count is the filter's and the triangle prover's together (checked on 14,002
  manifests);
- a level's reach table lists every cell of the level, which only the single-cell top levels of the fleet and the
  control had hidden.
Applying the replay audit to the sample surfaced something new: v04's s113, run by hand on this desktop and resumed,
has 61 resumed cells whose parents no pushed history records. The audit now pools the fleet's files-identical twin of
each judged slice, as it pools the fleet's reruns, and the sample verifies again.

Lessons.
1. Measure a relation before asserting it, even one that "must" hold. Two of my rules this round were wrong in ways
   the data showed at once.
2. A usage limit is a shared failure mode across the whole fleet: every worker's check-in chain breaks at once.
   Nothing broke this time, but the fleet's resilience rests on the background task, not on the check-ins.

## 2026-09-28 ~13:30 (03:30Z): G5 round 20; closing whole records instead of named fields

**Round 20: OPEN, seven MAJOR.** It caught every round-19 reproduction and found no gap in pooling the fleet's twin.
Its seven were all fields one layer further down:
- a verify manifest's `udenum_target` (an operation that verifies nothing);
- an enumeration manifest missing a parent source;
- pruning counts consistent internally but not tied to their files;
- the checker record's shard count and settings;
- the re-run judge not running the per-manifest software rule;
- a verified row whose text says CHAIN FAIL;
- a FAIL whose rows all say verified.

**The change of approach.** Twenty rounds in, the reviewer finds each round the next field nobody tied down. So this
round closes every field of each record a finding touched:
- the checker record is a closed set of 19 fields, each derived or pinned;
- a verify manifest's parts carry every counter udenum reports;
- a pruning manifest is bound to its reach, keep, UNKNOWN and certificate files, to its triangle statistics and to the
  audit;
- a verified row is read to its last note.
Every relation was measured on all the evidence first: 14,002 pruning manifests, every verify manifest, 1,444 checker
records, and the 171 full replays' red.json files.

**Two measurements changed the design.**
1. The checker's shard count cannot come from a copy's own run summary. A slice-mode copy's prefix is hard-linked, and
   a resumed copy lists none. It comes from the slice's pooled audited evidence, which the scope rules already build.
2. The fleet had the same software-pooling gap as the re-run judge. So the manifest rules now run in
   `scope_problems()`, for every copy of the fleet, the re-run and the sample.

Lesson. When a reviewer keeps finding the next unchecked field of the same record, stop binding fields one by one and
close the record: every field derived, pinned, or declared free with a reason.

**My own slip this round.** I inserted the red.json rule inside `if mode == "full":`, and its dedent pulled the
full-mode seed checks under the new branch, so they ran for every slice-mode replay. The smoke test passed because
its tree held one full-mode copy and nothing else. The sample judge caught it at once (57 false problems), and the
poller had already stopped on an unrelated false positive of the same change: a fleet twin's prefix run missing from
the pooled tree. Both are fixed. The smoke test is now two copies, one of each mode, from the same worker.

Lesson. A smoke test on one mode tests one mode. Make the smallest tree hold every case the change can reach.

## 2026-09-28 ~15:10 (05:10Z): G5 round 21; run identity; Liam: keep pushing

**Round 21: OPEN, seven MAJOR.** It found the checker record closed and round 20's FAIL rule clean, and seven more
fields one layer down. Three of them (verify parts, enumeration sources and the pruning checker's command) shared one
root: paths were checked by their basenames. One rule now closes all three. `run_names()` reads every string a
manifest records, keys and commands included, and requires this copy's run, or for a slice-mode copy's prefix cells
the run that computed the prefix. The other four:
- the shipped-manifest inventory (every top-level cell's two manifests);
- red controls bound to the replay's own cells, parents and the 324;
- the scope report's counts reconciled with the 1,955 copies;
- report identities: control footers, each row's fleet copy against the aggregate's chosen copy, and the sample's
  workers and first slices.
Everything was measured first. The run-identity rule was checked on 512,373 verify manifests and every enumeration and
pruning manifest of the five bodies of evidence.

**The stopping rule.** Rounds 17 to 21 each found 6 or 7 MAJOR findings, all of one kind: a hand-edited evidence file
some layer still accepts, never a defect in the evidence itself. I asked Liam whether to keep going, set a stopping
rule, or tighten the reviewer's rubric. His call: keep pushing through until CLOSED.

**Limits, stated.** Liam asked which limits are documented. There is one formal one: the controls' levels 13 to n-3
stage digests, with no shipped record. There are two boundaries covered another way: the G4 replay's sampled indices
are not recorded, and six slices were checked by the memory-bounded copy. I added one more to round 21's Response
before the reviewer could find it: the controls' certificates were checked when they were produced and are not
replayed afterwards (the (23,65) run's are all replayed by the full re-run).

## 2026-09-28 ~16:50 (06:50Z): G5 round 22; what only complete run directories can close

**Round 22: OPEN, eight MAJOR.** Five are closed in the judges:
- each path on its own, in its place;
- the pruning command's program is the recorded interpreter;
- the red controls' count invariants;
- a fully sampled cell compares every audited child;
- the scope report names its copies by digest (1,955, equal to the aggregate's), and the control report's outcome
  fields are read strictly.
The other three meet the same wall: evidence the shipped copies do not carry. The per-range verification logs are not
read even by the full-directory checkers, and parent-file digests cannot be recomputed where the sources are not
shipped. Those can only be closed on complete run directories.

**Liam: solutions, not limits.** Asked which limits were documented, he answered that he would rather sort out
solutions than deliver below our standard, and offered his laptop (16 GB, two NVMe drives, 6 GB of VRAM). Two plans are
now proposed and waiting on him:
1. A full re-run of both controls on Claude cloud (about 4 hours on 48 workers), every slice kept whole and checked by
   the reviewed checker with its certificates replayed, plus a supplementary check of every per-range log. This
   closes the documented limit, the controls' certificate boundary and round 22's finding 2 for the controls.
2. The six memory-heavy slices on the laptop: zram plus swap striped over both NVMe drives, and the original reviewed
   checker run in place of the memory-bounded copy.

## 2026-09-28 ~18:40 (08:40Z): G5 round 23

**Round 23: OPEN, seven MAJOR.** Five are closed in the judges:
- prefix coverage only by a copy that passes the audit too;
- the scope report's digest bound to target, mode and evidence (the writer recomputes it from the credited root);
- the one-nonempty-source parent digest checked exactly;
- no replay row with more children than its cell holds, and R4's next block a real block;
- the calibration's kept at least its found, and the sample's footer seed and counts the plan's.
The other two are stated as production-time boundaries of the pinned producer: the enumeration shard manifests and the
verification part logs, which the full-directory checkers do not read. The controls' re-run would close them for the
controls. For (23,65) it needs a second full re-run with a log-reading check, which is now an option put to Liam.

One of my rules had a hole the new what-if found at once. I added "kept at least found" only to the failure test, and
a calibration already read as met never reached it. It is now in the met condition too.

## 2026-09-28 ~20:50 (10:50Z): G5 round 24; a finer partition for the heavy slices; the last review round; the addition for Boris

**Round 24: OPEN, five MAJOR**, every one "a hand-edited evidence file some layer accepts". All five are fixed and
measured on every body of evidence first: the (22,61) control 1,920 of 1,920 (78 of 78 red controls), the sample 63
of 63 (36 of 36), the full re-run with no failing slice (34 of 34), the calibration with none failing (78 of 78), the
writer 249 of 249, G4-SCOPE OK on 1,955 copies. One slip of mine: the control for finding 2 looked for its case only in
each control's first full-mode slice, found none, and skipped itself without a word. It now searches every complete
copy, and a control that cannot run fails.

**The heavy slices, by a finer partition.** Liam ruled out renting and asked for a collaborative dialogue with codex
(`gpt-6-astra`, read-only; scratchpad `dialogue-1.md`, `dialogue-2.md` and their outputs). Its best idea: `run-dag2.py`
slices a level-12 record by `sha256(record)[:8] mod count`, and 1920 divides 30,720, so the sixteen slices
i + 1920 j of 30,720 partition slice i exactly, and with one canonical parent per graph, so do their trees. codex
checked that nothing above the slice level reads the slice's population in the production configuration. Each piece
is small enough, we expect, for the unchanged G5 checker.
- `coordination/cloud-workers/u23-refine.sh` runs each piece through the unchanged `u23-verify.sh`, with the memory
  fallback off, samples the checker's memory (`tools/refine_probe.py run`), and ships the evidence the result copies
  never kept (`refine_probe.py collect`: every file's sha256, the certificates' bytes by verdict, the metadata files,
  the level-12 roots, the G4 replay's records). Two local runs on (17,43) passed; the second fixed the sampler (the
  run's own descendants only) and the bundle (metadata, not payloads).
- The pilot h01 (s1535, the heaviest: 5,654,767 graphs at (18,41), 1,013 level-12 roots) was fired at 10:16Z.
- Measured on the way: the record count does not predict the memory kill. s1474 passed the original checker with
  3,298,473 records at (18,41), and s1814 died with 2,430,591; both were their worker's second slice. So the pieces'
  peaks are measured, not predicted.
- Liam on the standard: "I think so? you're the maths guy in the house here". It is sound, and not a workaround: the
  pieces cover the old slice exactly, the unchanged checker checks each, and their counts must add up to the fleet's
  record of the old slice. The judge, `tools/refine_check.py`, is a draft.

**The last review round.** Liam: "we are sort of trying to show off the very best we can do to Boris here, not just
pushing hard for the sake of hypothetical Reddit karma". Rounds 19 to 24 each found five to eight MAJOR findings of
one class, a hand-edited file that some judge accepts; none found an error in the mathematics or the computation, and
that class has no natural end. So round 25 is the last. It checks round 24's fixes, and then reads as Boris would: the
mathematics, the completeness argument, the partition, and each sentence of the addition below. The forgery class is
stated as an assumption: the judges take the files a worker pushed to be the files its run produced, and the
independent full re-run, which reproduced every slice's result files, is the defence.

**The addition for Boris.** He has not answered the consolidated reply, which said "we'll write when the search
finishes". Liam wants to send the result as a short addition to that thread, with a word on the long email's
formatting and on how his agents work. The draft is `ADDENDUM-DRAFT-2026-09-28.md`, with what must hold before it goes.
G0 pre-checked for Liam: OEIS A186705 still ends at a(21) = 57 with no edit since May 2026; AMP's paper is still v2
(February 2025); the 2026 papers found are on the asymptotic problem.

## 2026-09-29 ~09:00 (28th 23:00Z): everything in; the heavy pieces; the last read

**The evidence is complete.**
- The full re-run: `VERIFY-ALL OK: 1920 of 1920 slices re-run and verified, 0 problem(s)` (11:39Z).
- The (21,57) calibration: `TARGET-CHECK OK: (21,57): 1920 of 1920 slices complete, G4 PASS 1920; ... known: 5 of 5
  kept` (12:38Z). Its self-test first read 78 of 79: finding 2's control, which now fails when it finds no case, found
  none, and a survey of 400 copies showed why (the calibration's partly sampled cells are almost all one shard, and no
  shard drawn in full has children). The rule has nothing to check there, so that control now says "n/a" on its own
  line, uncounted; it is still caught on the (22,61) control.
- The write-up regenerated at 3febb81ff2: STATE COMPLETE, every check ok, G2 met; G5 waits only on the last read.
- The clean-machine test (p01) held, apart from the missing SymPy line, now in the guide.

**The heavy slices, split sixteen ways.** In each, 15 of 16 pieces passed the unchanged checker. The sixteenth was
killed for memory at about 13.7 GB, and it holds 93.1 to 99.9% of the slice's (18,41) cell: s1535's has 5,647,165 of
5,654,767 graphs, and the next-largest piece has 2,590. So one level-12 root dominates each slice. Splitting by level-12
hash can isolate a root, but it cannot divide one root's subtree. The judge (`tools/refine_check.py`, reworked for
memory kills, with two new rules: every prefix covered by a whole check, and a kept graph bound to its top-level record)
says REFINE-CHECK PARTIAL, 0 problems, self-test 19 of 19.

**The root shortcut, tried and closed.** If a dominant root were not a unit-distance graph, one certificate would
dismiss its whole subtree. The embedder on the seven dense roots of the killed pieces:

| slice | root | cell | verdict |
|---|---|---|---|
| s1535 | KwCW_cI@PRgu | (12,23) | embedded |
| s50 | Kw?Gc\|WIihCr | (12,26) | embedded |
| s1082 | KGA_gSOQHrW} | (12,23) | embedded |
| s1082 | Kw?G_SFV`qEd | (12,24) | unknown, even at 400 tries and 20,000 states |
| s1651 | KoCW_TFK`Qgf | (12,24) | unknown, likewise |
| s1721 | KWCGYHBLPdrK | (12,25) | unknown, likewise |
| s1814 | KwCWOKOcyTCl | (12,24) | embedded |

Four are genuine unit-distance graphs, so their subtrees are real. codex checked the embeddings exactly: s1535's and
s1814's have extra unit pairs (27 unit distances each), which leaves a narrow TU route open, a bounded experiment for
later, not a gate.

**Not tunnel vision (Liam: "worth continuing to work collaboratively with codex just to make sure we don't get tunnel
vision").** The second-level split (153 one-root sub-pieces, a root receipt from the unchanged checker with
`--from-n 24`, tested: 0.15 s, and red on a deleted root) would only narrow the stated exception from "one piece of
sixteen" to "the subtree of one named graph". The streaming checker already covers it, and a referee accepts that
(codex, dialogue 5). So it is off the finish line. The finish line is release work: the guide reconciled (done), the
write-up regenerated (done), a last read of the note as sent (running), then Liam's link and send. Optional after:
the seven dense roots run alone (to name the monsters), a complete enum2 regeneration of one heavy transition (the most
added independence, about 34 CPU-hours for s1814's), or the laptop with swap for the original checker's own verdict.

**G5 round 26: CLOSED** (22:37Z, at 3febb81ff2). Both of round 25's findings resolved, no FATAL or MAJOR. Its fresh
checks: both top-level verifiers accept; all 1,920 re-run slices against the fleet's records; both control verdicts
reproduced; the refinement PARTIAL with zero problems; Lemma D4 regenerated (all 29,925 degree-four extensions, the
18,689 canonical children, every forbidden-subgraph witness). The corrected L4, canonical augmentation, hereditary
pruning and the refinement partition are sound; no dependency unchecked beyond the guide's stated trust and retention.
Two MINOR, both fixed: the guide's Section 3 now names nauty's `labelg`, and the write-up drops its sample-versus-re-run
clause once the full re-run is verified. The note to Boris is ready; the link and the sending are Liam's.

## 2026-10-01 (AEST, ~02:05): the target's emptiness, derived from hashes rather than counts

The adversarial review of the u(24) worker found that no count in a run summary or `hashes.json` is bound to the files
(research/unit-distance-24/LABNOTES.md). Checked here for u(23): in all 1,955 fleet result copies of the 1,920 slices,
the `hashes.json` sha256 of `23-65.keep.g6` equals the empty file's for every slice except s50 (whose one kept graph is
refuted at the top level); duplicate copies agree; every shipped copy hashes to its recorded value; and the full
re-run (u23-verify-all-claude) bound every slice's `hashes.json` hashes to the run directory the G5 checker read. So
the empty target stands on hashes bound to checked files, not on recorded counts.
