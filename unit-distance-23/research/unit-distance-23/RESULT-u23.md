# u(23): the (23,65) enumeration (DRAFT for the human)

**A DRAFT for the human, not a result.** Generated 2026-09-28T23:53:17Z by `research/unit-distance-23/tools/write_result.py`, for gate G6 (the write-up generated from checker and manifest output only). Every number and status word below is read from a file: the outputs of the tools in Section 8, the records they rest on (the top-level records, the G5 reads, `JOBS.md`), and `CONTRACT.md`, whose sentences are quoted verbatim. The one exception is a parameter of the options put to the human in Section 6 (the sample's size), which is the supervisor's. `results/u23/result-values.json` names each value's source. Writing to Alexeev, Mixon and Parshall, and any OEIS, arXiv or Zenodo publication, are the human's (CONTRACT Section 7).

**Headline: COMPLETE.** The enumeration finds no (23,65) unit-distance graph. All 1,920 of 1,920 slices have a complete copy; the coverage audit says `COVERAGE (summary only) OK: every run's required cells are listed and recorded with the parents L4 allows, every count is consistent, and every fleet's slices are all present with their shares`; the 1 graph(s) the fleet's filter-only prune kept at (23,65) each carry a refutation that both checkers accept (`TOP-LEVEL OK: 1 slice(s) with kept graphs, 1 cop(ies), 0 problem(s)`) and a blind second verifier accepts (`BLIND-CHECK OK: 1 of 1 top-level certificates accepted by the blind verifier (verify_tree.py sha256 1bafc054ee736f4c); 7 of 7 tampered inputs rejected`); the G4 replays give PASS 1,920. If the gates of Section 6 are all green, u(23) = 64.

## 1. Statement and dependencies

CONTRACT Section 0, verbatim:

> u(n) is the maximum number of edges of a unit-distance graph on n vertices (OEIS A186705). Known before this programme: u(23) >= 64 (AMP, arXiv:2412.11914, Theorem 1(b): configurations found by Engel et al. and AMP), and u(22) = 60 (our u(22) result). AMP's Lemma (Schade): a graph with n vertices and m edges has an induced subgraph on n - 1 vertices with at least ceil(m(n-2)/n) edges. With m = 66 that subgraph would have 61 > u(22) edges, so **u(23) <= 65, and u(23) is 64 or 65.**

**Statement (DRAFT, for the human).** The enumeration of Section 3 finds no (23,65) unit-distance graph. If the gates of Section 6 are all green, u(23) = 64. The CONTRACT's own sentence on when that claim is allowed (Section 0):

> We claim u(23) = 64 only when the enumeration of Section 2 is complete for the graphs that could exist, every graph at its top level carries a checker-accepted refutation (or a TU witness), and gates G0 to G6 are green.

The dependencies, CONTRACT Section 0 and amendment 2, verbatim:

> Never "u(23) = 64" on an empty level whose emptiness was not produced by the certified pipeline, on numerics, or on an unchecked certificate. Never hide a dependency: the claim rests on u(22) = 60, on AMP's u(n) for n <= 21, on the 398 minimal forbidden graphs (Globus-Parshall and GP-10), and on the six TU gadgets.
>
> Section 0's dependencies gain Lemma R (every unit 4-cycle of an injective embedding is a rhombus; Globus-Parshall's Lemma 2) and Lemma T (every unit triangle is rotated by +-60 degrees).

Where each lives:
- u(22) = 60: `research/unit-distance-22/RESULT-u22.md`; every slice ran with u-bar(22) = 60 in place of AMP's 62, its justification recorded in the run options;
- AMP's values of u(n): Alexeev, Mixon and Parshall, `arXiv:2412.11914`, Theorem 1 (with Schade's lemma, which gives the upper bound above);
- the 398 minimal forbidden graphs: Globus and Parshall's list and GP-10's ten-vertex list (`research/gp-10/RESULT.md`), as `research/unit-distance-22/data/forbidden-398.json`, sha256 `8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c` in every slice copy's manifests and G4 replays;
- the six TU gadgets: `research/unit-distance-22/check/PROOFS.md` (`tu-gadgets.json`, sha256 `a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629` in every prune manifest);
- Lemma R and Lemma T: `research/unit-distance-23/RHOMBUS-SPEC.md` Sections 1 and 4, `research/unit-distance-22/enum/PRUNING.md` Section 5; their certificates are checked by `check/udcheck_rhombus.py` and `check/tri_verify.py`, which hand every other record to the hash-pinned `check/udcheck.py` or `check/udcheck398.py`.

## 2. What a (23,65) unit-distance graph would have to be

CONTRACT Section 1, verbatim:

> - **Minimum degree exactly 5.** Deleting a vertex of degree d leaves a unit-distance graph with 65 - d <= u(22) = 60 edges, so d >= 5; and 2 x 65 / 23 < 6, so some vertex has degree <= 5. (Schade's bound; no extra lemma needed.)
> - **Free of all 398.** It contains none of the 398 minimal forbidden graphs on at most 10 vertices (`research/unit-distance-22/data/forbidden-398.json`, sha256 pinned in Section 5): each is not a unit-distance graph, and subgraphs of unit-distance graphs are unit-distance graphs.
> - **TU-free, hereditarily.** PRUNING.md's Lemma L2 with (N, M) = (23, 65): a TU gadget with its pair non-adjacent in an induced subgraph would force a 66th unit distance, and u(23) <= 65.
> - **Every canonical ancestor is a unit-distance graph** (L1), so the ancestor on j vertices has at most u(j) edges: u(j) from AMP for j <= 21, and u(22) = 60.

And, by amendment 2, hereditarily like the gadgets: no 4-cycle rows (Lemma R) or triangle orientations (Lemma T) of the graph, or of any induced subgraph, force a collision or a unit distance on a non-edge (`RHOMBUS-SPEC.md`, `PRUNING.md` Section 5).

## 3. The enumeration

Method (CONTRACT Section 2 and amendments 1 to 3). The run options below are the same in every slice copy (identical: yes).
- `research/unit-distance-22/enum/udenum` in Mode 398 (the fast binary of amendment 3, `84adaddf` in every copy): canonical augmentation by minimum-degree deletion, from the seeds at level 10 to level 23.
- The reach table from (23,65) with root k = 5 and u-bar(22) = 60: the windows in Section 4.1.
- Hereditary pruning from level 12: `udfilter` (the six gadgets, its containment re-check on set 74) and `udtriangle` (Lemmas R and T). Every graph gets one certificate line; the prune step replays the whole certificate file with `check/udcheck_rhombus.py` and re-reads its outputs (`prune.py`'s `verify_outputs`: the keep file is exactly the kept records, kept plus pruned the input); every stage file is re-checked against all 398 (stage verification: yes).
- The prune is filter-only (filter-only: yes; embedder tries 0): a graph that survives every rule is kept, and at the top level CONTRACT Section 3 decides it (Section 4.2).
- Level 12 is split into 1,920 slices by record hash. Each worker regenerates the prefix, levels 10 to 12, itself (Section 5 compares the copies), and runs its slices to level 23.

The fleet (`coordination/cloud-workers/JOBS.md`, entry `u23-fleet`): 96 planned workers of 20 interleaved slices each, run as cloud sessions in waves, since the cloud cap was about 48 concurrent sandboxes. Tags re-fired after a lost or stuck session started fresh sandboxes and re-ran slices already pushed (9 tags with several result directories). A container restart makes the runbook resume from its own files, and a resumed cell's summary keeps neither its parents nor its share, so the summary audit cannot bind it (JOBS.md): 16 slices (94, 253, 263, 282, 453, 472, 534, 579, 600, 606, 835, 1227, 1354, 1405, 1735, 1773) have such a copy and a fresh one, and the fresh copy is the one counted; the rerun workers, outside the plan's owners, made f100-b704du 4, f97-t4t9v7 4, f98-lqpsag 4, f99-wsyxyj 3 of the copies. Slices whose every copy has resumed cells: none. 35 slices hold several complete copies (Section 5).

## 4. What the run produced

### 4.1 The tree above level 12

Over all 1,920 slices, one copy each (`aggregate_fleet.py`):

| level | window m (reach table) | cells | children | kept | pruned | tu | tri_tu | tri_refuted | refuted | % pruned |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 13 | 23..30 | 8 | 17,770,330 | 14,227,296 | 3,543,034 | 2,649,736 | 877,724 | 15,574 | 0 | 19.9 |
| 14 | 26..33 | 8 | 149,368,305 | 111,094,819 | 38,273,486 | 26,673,717 | 11,240,806 | 358,963 | 0 | 25.6 |
| 15 | 29..37 | 9 | 842,594,946 | 492,690,622 | 349,904,324 | 214,552,374 | 127,976,366 | 7,375,584 | 0 | 41.5 |
| 16 | 33..41 | 9 | 1,058,712,809 | 580,930,642 | 477,782,167 | 251,563,636 | 211,707,116 | 14,511,415 | 0 | 45.1 |
| 17 | 37..43 | 7 | 430,213,696 | 213,648,700 | 216,564,996 | 106,789,432 | 101,641,378 | 8,134,186 | 0 | 50.3 |
| 18 | 41..46 | 6 | 148,671,082 | 69,977,653 | 78,693,429 | 40,355,890 | 35,233,396 | 3,104,143 | 0 | 52.9 |
| 19 | 45..50 | 6 | 11,975,593 | 4,368,436 | 7,607,157 | 3,456,001 | 3,738,733 | 412,423 | 0 | 63.5 |
| 20 | 50..53 | 4 | 154,347 | 75,745 | 78,602 | 38,816 | 35,515 | 4,271 | 0 | 50.9 |
| 21 | 55..56 | 2 | 2,026 | 1,320 | 706 | 360 | 308 | 38 | 0 | 34.8 |
| 22 | 60 | 1 | 30 | 29 | 1 | 0 | 0 | 1 | 0 | 3.3 |
| 23 | 65 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0 |

The other count keys, summed over these cells: input 2,659,463,165, survivors 2,013,383,203, tri_silent_passes 0, tri_survivors 1,487,015,263, embedded 0, unknown 1,487,015,263. Children minus prune input (the reach filter's drops): 0. At level 23, kept means kept by the filter-only prune; Section 4.2 decides those graphs.

### 4.2 The top level (23,65) and its certificate

Over all 1,920 slices: children at (23,65) 1; kept by the filter-only prune 1, in slice(s) 50.

- Slice 50: `V?_QPIGD@AGOoHKE_o?Q??HK?WqH@PO_m@CWCaHN_?F_`. Its record `research/unit-distance-23/results/u23/top-level/s50of1920/` (graph, certificate, prune manifest, CHECK.txt): the full prune with the embedder on gives `{"input": 1, "tu": 0, "survivors": 1, "embedded": 0, "refuted": 1, "unknown": 0, "kept": 0, "pruned": 1}` and `ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15`; its red control (a proof-tree entry changed): `REJECT: tampered.certs.jsonl:1.witness.tree.A: row space is inconsistent with the claimed constraints`.

CONTRACT Section 3, verbatim:

> Every graph written at (23, 65) and not TU-pruned is either embedded exactly (then u(23) = 65 and the programme stops to verify it three ways) or refuted by a certificate that `research/gp-10/check/gp10check.py`'s sample profile (or `research/unit-distance-22/check/udcheck.py`) accepts. Unknown is never absorbed into a claim.

`top_level_check.py` with its self-test, which replays each record with both checkers and a tampered copy of each certificate (exit 0):

```
s50: 1 kept graph(s) in 1 copy; udcheck.py: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15
s50: 1 kept graph(s) in 1 copy; udcheck398.py: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15
s50: self-test: udcheck.py rejects a tampered certificate: REJECT: /tmp/tmpwv2mw5uf/23-65.certs.jsonl:1.witness.tree.A: row space is inconsistent with the claimed constraints
s50: self-test: udcheck398.py rejects a tampered certificate: REJECT: /tmp/tmpwv2mw5uf/23-65.certs.jsonl:1.witness.tree.A: row space is inconsistent with the claimed constraints
TOP-LEVEL OK: 1 slice(s) with kept graphs, 1 cop(ies), 0 problem(s)
```

`blind_check.py`: the blind second verifier (`research/unit-distance-23/blind-verifier/`, its README says how it was made: from the format and the mathematics alone, sharing no code with `check/udcheck.py`, which `check/udcheck398.py` executes) on each record, and seven tampered copies of each certificate made afresh (exit 0):

```
verifier: research/unit-distance-23/blind-verifier/verify_tree.py sha256 1bafc054ee736f4c7275a7ccb0a747bd2839ce7fefc3b5e04858265d1b015f67
s50of1920/23-65.g6 graph 0 V?_QPIGD@AGOoHKE_o?Q??HK?WqH@PO_m@CWCaHN_?F_ certs 46f2d3de06f72e37110daf656a5a7a98fd79554049882fa23160232c0617a145: ACCEPT (exit 0)
  (a) one entry of the root's A changed: REJECT root.A: row space does not equal all graph 4-cycle rhombus rows (exit 1)
  (b) one child subtree of the root removed: REJECT root: L3 requires 2 children; found 1 (exit 1)
  (c) the root move's first coefficient changed: REJECT root.move: ax+by+cz is not in A row space (exit 1)
  (d) the graph with the root move's first edge removed: REJECT root.edges: does not equal input graph (missing=[], extra=[(0, 4)]) (exit 1)
  (e) the field's interval moved off its root: REJECT field.interval: expected exactly one real root, found 0 (exit 1)
  (f) the last L3 split's d changed: REJECT root.children[1].children[1].move: L3 d squared does not equal the Heron discriminant (exit 1)
  (g) the first L1b leaf's omega changed: REJECT root.children[0].children[0].children[0].move: L1b x-omega*y is not in A row space (exit 1)
BLIND-CHECK OK: 1 of 1 top-level certificates accepted by the blind verifier (verify_tree.py sha256 1bafc054ee736f4c); 7 of 7 tampered inputs rejected
```

Graphs kept with no record: none.

### 4.3 Coverage and reruns

- Slices with a complete copy: 1,920 of 1,920. Copies read 1,955 from 101 worker directories; skipped as incomplete 0, misfiled 0, unfinished 0.
- The coverage audit (`verify-chain.py --summary-only`, pinned to target (23, 65), seed level 10 and slices (12, 1920) (level, count), requiring g4, hashes; branch `claude/answering-alexeev-u22-g5` at `34f0dcb9ba`): 1955 slice result directories from 101 workers under <scratch>/scratchpad/fleet/results. Summaries 1,955, slice indices 1,920, missing 0; prefix cells 15, with their parents recorded 15; cells recovered from pushed history 0; problems 0, unresolved 0. Its verdict: `COVERAGE (summary only) OK: every run's required cells are listed and recorded with the parents L4 allows, every count is consistent, and every fleet's slices are all present with their shares`, `CHAIN PARTIAL (summary only: no level, keep, parent or certificate file was read)` (exit 3). A summary-only audit never says more than that: it reads no level, keep, parent or certificate file.
- The slices partition every level-12 parent cell: each slice records its share, and the audit requires the shares to add up to the stage file once every slice is present.

| parent cell | records in the stage file | sum of the recorded shares | slices recording | slices present without a share |
|---|---:|---:|---:|---|
| (12,20) | 1,384,579 | 1,384,579 | 1,920 | none |
| (12,21) | 476,585 | 476,585 | 1,920 | none |
| (12,22) | 51,819 | 51,819 | 1,920 | none |
| (12,23) | 3,011 | 3,011 | 1,920 | none |
| (12,24) | 198 | 198 | 1,920 | none |
| (12,25) | 25 | 25 | 1,920 | none |
| (12,26) | 2 | 2 | 1,920 | none |
| (12,27) | 1 | 1 | 1,920 | none |

### 4.4 Cost

By `fleet_status.py`'s rule (step timings of the cells above level 12; a resumed cell's time is unknown, so a slice with one is not timed): 1,920 slices timed, 0 excluded, **1,304,030.4 s** (362.23 h). Per slice: median 556.8 s, p90 987.4 s, max 13,270.6 s; the heaviest s344 13,270.6 s (f57-w2xriy), s1535 11,289.4 s (f96-fi9jlf), s50 9,734.2 s (f51-2h4ksy), s1082 9,594.1 s (f27-ldx6e0), s1651 8,559.4 s (f20-bvpkkh). The runbook's own clocks over 1,920 copies: `run-dag2.py` 1,468,404 s, the G4 replay 89,973 s.

## 5. Cross-checks that were actually run

- **G4, the independent replay** (`enum2/replay-398.py` with `enum2.py`, sharing no code with `udenum` but using the same nauty release for canonical labelling and automorphism orbits, so a defect there would reach both; `2c81ae65` and `d967fc90` in every copy): verdicts PASS 1,920 over the chosen copies; modes full 99, slice 1,821; full-mode replays with every red control red 99. Parents sampled 2,237,909, processed 1,374,989; production children compared 3,576,629; mismatching parents 0; stage files re-derived 131,946. The audit derives each replay's verdict again from its evidence and binds its rows to the summaries: PASS 1,955.
- **The prefix is the same on every worker**: 70 files of levels up to 12 (`hashes.json`) with identical sha256 in all 1,955 copies: yes; the audit: 70 prefix files hashed, identical in 1,955 summaries. Every worker computed the prefix itself.
- **Duplicate copies agree**: 35 slices hold several complete copies; their counts rows, shipped level files and kept graphs are identical: yes.
- **The top-level certificates**: each record replayed by `check/udcheck.py` and `check/udcheck398.py` (2 checker lines above), each tampered copy not accepted (2 of 2; accepted 0). The two are one implementation (`check/udcheck398.py` executes `check/udcheck.py`'s pinned bytes), so a blind second verifier, written from the format and the mathematics alone (`blind_check.py`, accepts), accepts 1 of 1 and rejects 7 of 7 tampered inputs.
- **Known graphs survive** (CONTRACT Section 4.3 at level 22; `level22_control.py`, kept): of Engel et al.'s 35 known (22,60) configurations (`research/unit-distance-22/sources/engel-dataset/engel-22-60.g6`, sha256 `c85de7632fbf2513`), each the unit-distance graph of its own points, the 14 with minimum degree at least 4 must be kept at level 22; kept: 14, Engel 1 in s50of1920, Engel 8 in s50of1920, Engel 9 in s50of1920, Engel 10 in s50of1920, Engel 11 in s344of1920, Engel 12 in s1647of1920, Engel 13 in s344of1920, Engel 14 in s1647of1920, Engel 15 in s50of1920, Engel 16 in s50of1920, Engel 18 in s50of1920, Engel 21 in s344of1920, Engel 24 in s50of1920, Engel 34 in s50of1920. The fleet's keep files at level 22 hold 29 distinct (22,60) graphs over 1,955 slice copies, 15 of them not Engel's (the filter-only prune keeps what it cannot decide), and 0 of them in more than one slice. Its self-test: with Engel 1's form removed it reports missing [1]; an edge-flipped Engel graph found: no; a graph placed in a second slice reported: yes. `LEVEL-22 CONTROL OK: 14 of 14 required graphs found` (exit 0).
- **The certification sample** (G5's point 6, the human's choice; `verify_sample.py`, all verified): 63 of 63 sampled slices re-run with nothing deleted, each run directory checked in full by the G5-closed `verify-chain.py --check` (9 checked whole from the seed level, the rest from level 13 with the prefix compared), and each re-run's result files identical to the fleet's copy of the slice; the random part drawn by a published seed (20260927), which the tool re-draws. Section 6 has the details.
- **The full re-run** (beyond point 6's sample; `u23-verify-all-claude` on Claude cloud, judged by `verify_sample.py --all`, all verified): every one of the 1,920 slices re-run with nothing deleted and checked the same way, each check bound to its slice's copy (the checker's own record and a digest of the files checked), every prefix the prefix of a whole check: `VERIFY-ALL OK: 1920 of 1920 slices re-run and verified (48 tasks; 48 first slices checked whole, the rest from level 13 with the prefix compared; every prefix the prefix of a whole check; 6 by the memory-bounded verify-chain-lean.py after the G5 check was killed for memory), 0 problem(s)`.
- **The tree control at full strength** (CONTRACT Section 4.1; `u23-control22`, judged by `target_check.py`, empty): the whole (22,61) tree through the final pipeline, with no u-bar override below it and root minimum degree 5 (Lemma D4), must keep nothing at its top, consistently with the u(22) result: `TARGET-CHECK OK: (22,61): 1920 of 1920 slices complete, G4 PASS 1920; 0 failing, 0 missing; kept at (22,61): 0 distinct graph(s)`.
- **The calibration** (CONTRACT Section 4.3; `u23-calib2157`, judged by `target_check.py`, all kept): the whole (21,57) tree through the final pipeline, root minimum degree 3 (Schade's bound), must keep all five of Alexeev, Mixon and Parshall's extremal graphs (`engel-21-57.g6`): `TARGET-CHECK OK: (21,57): 1920 of 1920 slices complete, G4 PASS 1920; 0 failing, 0 missing; kept at (21,57): 10 distinct graph(s); known: 5 of 5 kept`.
- **The aggregate's self-check**, each identity recomputed by a second path: 8 of 8 hold (coverage holds, cell_partition holds, pruned_by_kind holds, counts_vs_summary holds, counts_vs_files holds, totals holds, copies_agree holds, fleet_status holds); its red control, `--perturb`, is in Section 8 (this generator does not run it).
- **One software and data hash each in every copy**: yes (enum2.py `d967fc90`, exact_verify.py `ab55ce77`, prune.py `b4858cab`, python `/usr/local/bin/python3 3.11.15`, replay-398.py `2c81ae65`, run-dag2.py `0c6fb312`, udcheck.py `63b7f1b5`, udcheck398.py `783d368c`, udcheck_rhombus.py `06db27ec`, udembed.py `75886c63`, udenum `84adaddf`, udfilter `6e0771bb`, udtriangle `0ca59908`; 162,265 verify manifests read).
- **The reach windows against CONTRACT Section 2**: level 19: the CONTRACT 45..50, the run 45..50, level 20: the CONTRACT 50..53, the run 50..53, level 21: the CONTRACT 55..56, the run 55..56, level 22: the CONTRACT 60..60, the run 60..60.
- **G5, the cross-model soundness read**: `G5: CLOSED`, the round-9 read `research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round9-read-gpt-6-astra.md` on branch `claude/answering-alexeev-u22-g5` (`34f0dcb9ba`); the latest read since, `G5 round 26: CLOSED` (`research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round26-read-gpt-6-astra.md`).

## 6. Gates

| gate | requirement (CONTRACT Section 6) | status here |
|---|---|---|
| G0 | inputs pinned (Section 5); literature recheck that u(23) is still open | not re-derived by this generator. Inputs: one software and data hash each in every copy: yes (Section 5). The literature: the last record is `research/unit-distance-23/LITERATURE-CHECK-2026-09-28.md`, made by the session at the human's request; to be redone on the day anything is public. |
| G1 | Mode 398 built and validated (`enum/REPORT-398.md`: regression, semantics, filter on B10) | not re-derived by this generator: `research/unit-distance-22/enum/REPORT-398.md` and `REPORT-398-SPEED.md`. |
| G2 | controls of Section 4 green; the pilot's measured cost model written before the fleet launches | met: re-derived here (Section 5): CONTRACT Section 4.3 at level 22, kept; Section 4.1, the whole (22,61) tree, empty; Section 4.3's (21,57) calibration, all kept. Sections 4.2 and 4.4: `research/unit-distance-22/enum/REPORT-398.md` and G4 below; the earlier pilot and control records are in `LABNOTES.md` and `JOBS.md` (`u23-pilot`, `u23-control`, `u23-pilot2`, `u23-pilot3`). |
| G3 | every slice complete; the top level decided by checker-accepted certificates | met: coverage complete, the audit OK, the top level decided, the blind verifier accepts, one snapshot. |
| G4 | the independent replay of Section 4.4 | met: verdicts over the chosen copies PASS 1,920; the audit's G4 results PASS 1,955; every replay in its mode's scope: `G4-SCOPE OK: 101 of 101 full-mode replays and 1854 of 1854 slice-mode replays in their mode's scope; 0 problem(s)`. |
| G5 | a cross-model soundness read of anything new in the trust chain, every finding answered in writing | met: `G5: CLOSED` (`research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round9-read-gpt-6-astra.md`, branch `claude/answering-alexeev-u22-g5`, `34f0dcb9ba`); since the fleet, `G5 round 26: CLOSED` (`research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round26-read-gpt-6-astra.md`, answered in writing); point 6 by the human's choice, the certification sample: all verified, 63 of 63 slices verified (below); beyond it, the full re-run of every slice: all verified, 1,920 of 1,920 verified. |
| G6 | the write-up generated from checker and manifest output only | met by this generator: the lint sees no numeral, status word or state assertion in the fixed text around the 563 values, and each of the 7 occurrences of u(23) = n sits in a conditional sentence |

GPT's point 6 (item 6 of `research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-closure-read-gpt-6-astra.md`: "FATAL for the proposed final certification — The retained artifacts cannot close the intermediate keep-file gap."): once intermediate files are deleted, no summary-level audit can re-prove the certificate-to-keep-file relation, so correctness rests on the workers' in-process checks, `prune.py`'s `verify_outputs` at production and the G4 replay. Of the three options put to the human (a re-run of the restarted slices plus a ~2.5% random sample with nothing deleted, each run directory checked by the full `verify-chain.py --check`; keeping the files until an on-worker full audit; a full second run) the human chose the first (`JOBS.md`, entry `u23-verify`). Its result, `verify_sample.py`: `VERIFY-SAMPLE OK: 63 of 63 planned slices verified (15 restarted, 48 random, seed 20260927; 9 of 10 workers' first slices checked whole, the rest from level 13 with the prefix compared), 0 problem(s)`. Verified: the restarted slices 94, 253, 263, 282, 453, 472, 534, 579, 606, 835, 1227, 1354, 1405, 1735, 1773 (15 of 15), and 48 of the 48 random ones (seed 20260927): each re-run by the fleet's unchanged runbook with nothing deleted, its run directory checked by the G5-closed `verify-chain.py --check` (9 of 10 workers' first slices whole; every other slice from level 13, its prefix compared byte for byte with its worker's first slice, or, for a first slice checked from that level on a machine too small for the whole check, by hash with the fleet's copies), every inspected pruned cell's certificates replayed, and its result files identical to the fleet's copy.

## 7. What is claimed, and what is not

- Claimed, as a DRAFT for the human: the enumeration of Section 3 finds no (23,65) unit-distance graph (Sections 4 and 5).
- If the gates of Section 6 are all green, u(23) = 64; the CONTRACT allows that claim only as Section 1 quotes.
- Not claimed: u(23) = 64 as an established result. G0 and G1 are not re-derived here; G2's whole-tree controls are empty and all kept, the full re-run is all verified.
- Not claimed: that the summary audit re-proves the certificate-to-keep relation of the deleted intermediate files (it reads no level, keep, parent or certificate file); that relation rests on the workers' in-process checks, and the certification sample re-proved it on 63 of the 1,920 slices (Section 6), the full re-run on 1,920 of them (Section 5).
- Not claimed: anything about u(n) for n > 23.
- Rests on: the dependencies in Section 1.

## 8. How to check it

ROOT is the extraction of every fleet worker's pushed results, VROOT the verification workers'; G5DIR a checkout of branch `claude/answering-alexeev-u22-g5`, where the audit ran (merged into this branch once the fleet and the certification sample were done, so a checkout of this branch serves as well).

```
python3 research/unit-distance-23/tools/fleet_status.py --fetch --workdir ROOT
python3 research/unit-distance-23/tools/aggregate_fleet.py --root ROOT --self-check --out aggregate.json
python3 research/unit-distance-23/tools/aggregate_fleet.py --root ROOT --self-check --perturb 0   # must fail
python3 research/unit-distance-23/tools/top_level_check.py ROOT --self-test
python3 research/unit-distance-23/tools/level22_control.py ROOT --self-test
python3 research/unit-distance-23/tools/verify_sample.py --fetch --verify-root VROOT --root ROOT --self-test
git worktree add G5DIR origin/claude/answering-alexeev-u22-g5
python3 G5DIR/research/unit-distance-22/enum/test-rhombus/fleet-audit.py --root ROOT
python3 research/unit-distance-23/tools/write_result.py --root ROOT --audit-worktree G5DIR
python3 research/unit-distance-23/tools/write_result.py --self-test
```

What this draft ran (the outputs' sha256 are in `result-values.json`, under `sources`):

- aggregate: `/usr/bin/python3 <repo>/research/unit-distance-23/tools/aggregate_fleet.py --root <scratch>/scratchpad/fleet/results --self-check --out <repo>/research/unit-distance-23/results/u23/result-inputs/aggregate.json` in `.` (exit 0; output sha256 `c3db272baa6582c8`)
- top level: `/usr/bin/python3 <repo>/research/unit-distance-23/tools/top_level_check.py <scratch>/scratchpad/fleet/results --self-test` in `.` (exit 0; output sha256 `be53a38ea98187d0`)
- blind verifier: `/usr/bin/python3 <repo>/research/unit-distance-23/tools/blind_check.py` in `.` (exit 0; output sha256 `6c18f4243ccd85a5`)
- known graphs: `/usr/bin/python3 <repo>/research/unit-distance-23/tools/level22_control.py <scratch>/scratchpad/fleet/results --self-test` in `.` (exit 0; output sha256 `a772dbdd7dc41ce6`)
- certification sample: `/usr/bin/python3 <repo>/research/unit-distance-23/tools/verify_sample.py --verify-root <scratch>/scratchpad/fleet/verify-results --root <scratch>/scratchpad/fleet/results` in `.` (exit 0; output sha256 `f4f15a63d569537e`)
- coverage audit: `/usr/bin/python3 <repo>/.claude/worktrees/agent-a3c9dc31ac1640180/research/unit-distance-22/enum/test-rhombus/fleet-audit.py --root <scratch>/scratchpad/fleet/results` in `<repo>/.claude/worktrees/agent-a3c9dc31ac1640180` (exit 3; output sha256 `14603299d8c127d4`)

The fleet root's fingerprint before and after: `81e046a9d3efda0c` and `81e046a9d3efda0c` over 7,820 files.
