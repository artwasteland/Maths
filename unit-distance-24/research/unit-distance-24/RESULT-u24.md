# u(24): the (24,69) enumeration (draft for the human)

Generated 2026-10-07T18:48:22Z by `research/unit-distance-24/tools/write_result.py`.

Every displayed number and status is extracted from the hashed evidence or derived from it. The generation time is metadata. The accompanying `result-values.json` records each value, its source file and digest, and every derivation. The counted-copy source manifest is `result-sources.json.gz`, SHA digest `7263b5f061850f43b0ddbf1207f2ee2185d4ba79aa3b7b982b78ef87cf5e2441`. This draft is for human review.

**Headline: COMPLETE.** If the gates of Section 6 are all green, u(24) = 68.

## 1. Statement and dependencies

A TU gadget is a totally unfaithful graph: a distinguished non-edge has unit length in every unit-distance embedding. At an induced ancestor this forces an extra edge at the target; the proved upper bound rules out that target. See `research/unit-distance-22/enum/PRUNING.md`.

The receipt label `G4 replay` means the independent augmentation replay, which samples 0.2% of the augmentation work. Replay, sampling and replay verdict references in the quoted historical material use that receipt meaning. Gate G4 means the known-graph control: eligible graphs from known point configurations must be generated once and must never be pruned. The two checks have different scopes.

The contract's claim and dependencies, verbatim:

> u(24) >= 68 (AMP, arXiv:2412.11914, Theorem 1(b)). With u(23) = 64 (`research/unit-distance-23/RESULT-u23.md`), AMP's
> Lemma (Schade) gives u(24) <= 69: a (24,70) graph would have an induced 23-vertex subgraph with
> ceil(70 x 22/24) = 65 > 64 edges. **So u(24) is 68 or 69, and the one case is (24,69).**
> 
> - We claim u(24) = 69 only with an exact embedding of a 24-vertex, 69-edge graph accepted by the checker.
> - We claim u(24) = 68 only when the enumeration of Section 2 is complete, every graph at its top level carries a
>   checker-accepted refutation (or a TU witness), and the gates of Section 4 are green.
> - The claim rests on u(23) = 64 and u(22) = 60 (our results), on AMP's u(n) for n <= 21, on the 398 minimal forbidden
>   graphs, and on the six TU gadgets. Say so wherever the result is stated.

If the gates of Section 6 are all green, u(24) = 68. The claim depends on the inputs below.

Both preceding results are this programme's own results, neither yet independently published: `research/unit-distance-23/RESULT-u23.md`; `research/unit-distance-22/RESULT-u22.md`. Their values used by the contract are respectively 64 and 60.

The following dependencies are quoted from the preceding result:

> - AMP's values of u(n): Alexeev, Mixon and Parshall, `arXiv:2412.11914`, Theorem 1 (with Schade's lemma, which gives the upper bound above);
> - the 398 minimal forbidden graphs: Globus and Parshall's list and GP-10's ten-vertex list (`research/gp-10/RESULT.md`), as `research/unit-distance-22/data/forbidden-398.json`, sha256 `8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c` in every slice copy's manifests and G4 replays;
> - the six TU gadgets: `research/unit-distance-22/check/PROOFS.md` (`tu-gadgets.json`, sha256 `a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629` in every prune manifest);
> - Lemma R and Lemma T: `research/unit-distance-23/RHOMBUS-SPEC.md` Sections 1 and 4, `research/unit-distance-22/enum/PRUNING.md` Section 5; their certificates are checked by `check/udcheck_rhombus.py` and `check/tri_verify.py`, which hand every other record to the hash-pinned `check/udcheck.py` or `check/udcheck398.py`.

The forbidden-graph file read here is `research/unit-distance-22/data/forbidden-398.json`, SHA digest `8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c`. The TU gadget file is `research/unit-distance-22/data/tu-gadgets.json`, SHA digest `a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629`.

For the survivor, the dependency is the individual refutation record and the frozen checker, `research/gp-11/check/gp11check.py`, SHA digest `ac1e3d94571fcabfd3f99d083ffd54cddb78ccff2138111913e67513b4560baa`. The survivor argument requires neither the GP-11 classification (the census of minimal non-unit-distance graphs on eleven vertices) nor its full final census check. The certificate establishes a refuted subgraph; a unit-distance embedding of the survivor would restrict to an embedding of that subgraph.

## 2. What the candidate graph would have to be

The reach table records the ancestor vertex-and-edge cells and minimum-degree bounds that can still lead to the target, using the known extremal values u(j).

The contract's structural requirements, verbatim:

> - **Minimum degree exactly 5.** Deleting a vertex of degree d leaves 69 - d <= u(23) = 64 edges, so d >= 5; and
>   2 x 69/24 < 6. Schade's bound, no extra lemma.
> - **Free of all 398, TU-free hereditarily** (L2 with (N, M) = (24, 69), valid since u(24) <= 69 is proved).
> - **Every canonical ancestor is a unit-distance graph**, so the one on j vertices has at most u(j) edges: AMP for
>   j <= 21, u(22) = 60 and u(23) = 64 (the run's u-bar overrides 22=60 and 23=64, recorded and justified in reach.json).

## 3. The enumeration

Canonical augmentation by minimum-degree deletion gives each candidate a unique construction path from its canonical parent. Record-hash slicing at the slice level partitions that tree. The reach table bounds every ancestor cell that can lead to the target using the known u(j). Forbidden-subgraph exclusions, certificate refutations and the rules justified by Lemmas R and T apply hereditarily, because every subgraph of a unit-distance graph is unit-distance. A TU gadget in an induced ancestor forces an extra unit distance on a non-edge of the target, contradicting its proved upper bound, so that rule also excludes descendants soundly. Details are in `research/unit-distance-22/enum/PRUNING.md` and `research/unit-distance-23/RESULT-u23.md`.

The contract's enumeration parameters, verbatim:

> The u(23) pipeline unchanged except for its tables: `run-dag2.py` and `prune.py` extended to n = 24, the runbook
> `coordination/cloud-workers/u23-slice.sh` taking two u-bar overrides. Target (24,69), seed level 10, root k 5, slice
> level 12, count 1,920, Mode 398, triangles, the set-74 prune re-check, stage verification. The reach tables of (24,69)
> and (23,65) agree through level 15; the new routes enter at (17,40), (18,42), (19,45) and (20,49). The prefix (levels
> 10 to 12) is byte-identical to (23,65)'s (86 files compared, 2026-10-01).

The contract's standard, including the limits of reproduction, verbatim:

> Decided with Liam on 2026-09-30 (`research/unit-distance-23/NEXT-ESTIMATES-2026-09-29.md`, "The standard for u(24)").
> The field's norm is two independently written programs agreeing, or certificates checked by an independent checker;
> re-running the same program proves reproducibility, not correctness. u(23) ran twice only because its fleet deleted
> run directories before the reviewed checker saw them. So:
> 
> - **Check before delete.** Each worker (`coordination/cloud-workers/u24-worker.sh`) runs a slice, its G4 replay,
>   the reviewed checker `research/unit-distance-22/enum/verify-chain-u24.py --check` on the run directory, and the
>   known-graph control; pushes a receipt bound to that output; and only then deletes the directory. A failed check or
>   push keeps it.
> - **The checker** is the G5-closed `verify-chain.py` with its memory bounded (`verify-chain-lean.py`, four LEAN edits)
>   and its tables extended to 24 (the U24 edits), nothing else changed. On every run of a target with n <= 23 it
>   prints exactly what `verify-chain-lean.py` prints.
> - **G4 at twice u(23)'s fraction** (0.002): part of the saving buys a larger sample for the independent enumerator.
> - **The known-graph control, at every level with data.** Engel et al.'s configurations (16 to 22 points, 137,011
>   graphs, each the unit-distance graph of its own points) are faithful, so no sound rule prunes one or any ancestor,
>   and each one at a reach-table cell with minimum degree at least k(n,m) is in the tree, in exactly one slice. Per
>   slice: none generated is pruned. Over the whole run: every such graph found, once.
> - **Reproduction by sample**, not in full: 48 random slices (a published seed) and a few chosen ones (heavy,
>   restarted) re-run on fresh machines, their result copies compared with the first run's. What is given up is
>   u(23)'s extra claim that every slice was reproduced on another machine; the write-up says so.
> - **Controls carried forward** where the pipeline's core is unchanged: the (22,61) tree control and the (21,57)
>   calibration of u(23) stand. New: the known-graph control above, and the pilot's deployment checks.
> - **Pilot slices count** toward the final run when the pipeline and checker are frozen at the pilot's version.

Reproduction is by sample, not of every slice. The in-process checks before deletion and the independent replay are the contract's standard. Re-running the same program establishes reproducibility; it does not establish the program's correctness.

The pilot deployment record is `coordination/cloud-workers/JOBS.md`, entry `u24-pilot`. The judged snapshot has 286 branch/commit rows in `research/unit-distance-24/evidence/judge-final-2026-10-07-r2/sources.tsv`; `research/unit-distance-24/evidence/judge-final-2026-10-06/README.md` records the snapshot procedure and frozen checker, and `research/unit-distance-24/evidence/judge-final-2026-10-07-r2/README.md` records the final re-judge and receipt audit. The generator reads those saved reports.

## 4. What the run produced

The filter-only prune applies the sound forbidden-subgraph, gadget and structural filters and keeps every graph they leave undecided. Surviving that filter does not certify a unit-distance embedding.

| plan | verdict | exit | planned slices | accepted slices | accepted copies | duplicate slices | prefix files | independent augmentation replay |
|---|---|---|---|---|---|---|---|---|
| u24-pilot | OK | 0 | 42 | 42 | 44 | 2 | 70 | PASS 44 |
| u24-full | OK | 0 | 1,841 | 1,841 | 1,842 | 1 | 70 | PASS 1,842 |
| u24-phaseb | OK | 0 | 37 | 37 | 37 | 0 | 70 | PASS 37 |
| u24-repro | OK | 0 | 50 | 50 | 100 | 50 | 70 | PASS 100 |

The coverage partition uses the coverage plans only; the reproduction copies add no new slices. Duplicate and validation copies do not multiply the count. The partition check and each headline predicate are recorded in the values file.

### The tree above the slice level

Over 1,920 counted copies, using each coverage plan's `cost.chosen` source. Counts are summed by cell and level, and checked against each chosen summary and the prune accounting identities. The snapshot path and every selected file hash are in the compressed source manifest named above.

| level | window | cells | children | kept | pruned | tu | tri_tu | tri_refuted | refuted | % pruned |
|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 23..30 | 8 | 17,770,330 | 14,227,296 | 3,543,034 | 2,649,736 | 877,724 | 15,574 | 0 | 19.9 |
| 14 | 26..33 | 8 | 149,368,305 | 111,094,819 | 38,273,486 | 26,673,717 | 11,240,806 | 358,963 | 0 | 25.6 |
| 15 | 29..37 | 9 | 842,594,946 | 492,690,622 | 349,904,324 | 214,552,374 | 127,976,366 | 7,375,584 | 0 | 41.5 |
| 16 | 33..41 | 9 | 1,058,712,809 | 580,930,642 | 477,782,167 | 251,563,636 | 211,707,116 | 14,511,415 | 0 | 45.1 |
| 17 | 37..43 | 7 | 430,213,864 | 213,648,868 | 216,564,996 | 106,789,432 | 101,641,378 | 8,134,186 | 0 | 50.3 |
| 18 | 41..46 | 6 | 149,651,568 | 70,700,498 | 78,951,070 | 40,556,720 | 35,290,108 | 3,104,242 | 0 | 52.8 |
| 19 | 45..50 | 6 | 71,309,140 | 35,311,814 | 35,997,326 | 18,782,289 | 15,774,555 | 1,440,482 | 0 | 50.5 |
| 20 | 49..54 | 6 | 7,827,502 | 2,997,565 | 4,829,937 | 2,282,351 | 2,296,875 | 250,711 | 0 | 61.7 |
| 21 | 54..57 | 4 | 93,259 | 46,801 | 46,458 | 23,953 | 19,795 | 2,710 | 0 | 49.8 |
| 22 | 59..60 | 2 | 1,356 | 892 | 464 | 270 | 158 | 36 | 0 | 34.2 |
| 23 | 64 | 1 | 48 | 31 | 17 | 13 | 2 | 2 | 0 | 35.4 |
| 24 | 69 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.0 |

Kept at the target means kept by the filter-only prune. The survivor record below decides those graphs. This aggregation reads retained counts and summaries; it does not replay certificates or prove enumeration completeness independently.

### The survivor and its refutation

Distinct survivor identities across the judge reports: 1. `research/unit-distance-24/SURVIVOR-s50-2026-10-06.md` is the narrative note; the final judge reports decide coverage here.

- Slice(s) [50]: ``W@iiac_CA?O?GICD@C_HH?U?AWM@SE?i?GAh@?dWABT?OIr``.

Bundle `research/unit-distance-24/survivor-s50/mapping.json`; check output `research/unit-distance-24/survivor-s50/check_survivor.out`.

Pattern ``J?iP?dHPb`_`` has 11 vertices and 18 edges. Packet `packet-a5561d906d5f885d`; record `research/unit-distance-24/survivor-s50/refutation-a5561d906d5f885d.record.jsonl`, SHA digest `1b3bece53fd57eb407641afd210eca1fdcb27f12544b910ed71e079c8ca882a3`. The generator checks injectivity and every pattern edge against the survivor, and checks the record's graph identity and hash. It reads the saved frozen-checker acceptance below.

Its `real-dag` certificate uses 14 exact rational polynomial identities to derive a polynomial equal to a positive constant plus 4 positively weighted squares, which cannot vanish at a real embedding; see `research/gp-10/check/FORMAT.md`, inherited by `research/gp-11/check/FORMAT.md`, and `research/gp-10/check/gp10check.py` (`regenerate`, `algebra_dag` and `real_no_zero`).

```text
# 2026-10-06T22:10:22Z <host>: <repo>/pyenv-gp10/bin/python -B research/unit-distance-24/survivor-s50/check_survivor.py (exit 0), at commit 644cc4f488b
ACCEPT record J?iP?dHPb`_ verified
ACCEPT run verified
SURVIVOR REFUTATION OK: W@iiac_CA?O?GICD@C_HH?U?AWM@SE?i?GAh@?dWABT?OIr contains J?iP?dHPb`_ (refuted, frozen checker ACCEPT)

```

The blind search, `research/unit-distance-24/survivor-s50/independent-codex/search-results.json`, found 12 GP-11-refuted graphs on eleven vertices embedded in the survivor, out of 12 supplied records; any one suffices. The blind second check, `research/unit-distance-24/survivor-s50/independent-codex/FINAL.md` and `research/unit-distance-24/survivor-s50/independent-codex/checker-results.json`, reports that the frozen checker accepts 12 of 12 original records, and rejects 1 of 1 damaged records. It used the same frozen checker. The independent work was the subgraph search and the mapping checks, rather than another certificate-checker implementation.

### Coverage, histories and cost

| plan | per-plan summary | slices outside plan | resumed accepted copies | resumed slices | validation requested | validation accepted |
|---|---|---|---|---|---|---|
| u24-pilot | per-slice OK | 1,878 | 9 | [344, 1209, 1474, 1639, 1651, 1721, 1814] | 0 | 0 |
| u24-full | per-slice OK | 79 | 5 | [239, 830, 1069, 1352, 1641] | 1 | 1 |
| u24-phaseb | per-slice OK | 1,883 | 9 | [272, 276, 406, 466, 997, 1183, 1260, 1270, 1371] | 0 | 0 |

Each per-plan summary intentionally lacks the other plans' slices. Its per-slice status does not substitute for the fleet-wide summary audit. A summary-only audit reads structural records and counts; it cannot re-prove the certificate-to-keep relation after intermediate files have been deleted. That relation rests on the worker's in-process checks before deletion.

Fleet-wide report `research/unit-distance-24/evidence/judge-final-2026-10-07-r2/fleet-audit.json`: verdict OK, status complete, exit 0.

```text
COVERAGE (summary only) OK: every run's required cells are listed and recorded with the parents L4 allows, every count is consistent, and every fleet's slices are all present with their shares
```

The judge records 245 requested rerun slice/tag pairs and 238 retired rerun copies. These are histories, distinct from the fresh comparisons below. Superseded and validation decisions are retained in each JSON report.

Rerun requests grouped by the reason's leading clause, before its first parenthesis or semicolon:

| reason leading clause | requested slice/tag pairs | lead seconds range |
|---|---|---|
| suspect: its only PASS copies were resumed under the legacy timeout-6600 supervisor | 191 | not recorded |
| suspect: the legacy timeout-6600 run of this slice was resumed | 26 | -1..647 |
| suspect: the legacy timeout-6600 run of this slice was two runbook pushes after a relaunch in the same container | 28 | not recorded |

The full verbatim reason list and each reason's count are retained in `result-values.json` under `history.reasons`.

The grouped counts sum to 245; the judge's requested pairs are 245. Their equality is a headline predicate.

At slice 247, the earlier copy is `v26-ysvydx/research/unit-distance-24/results/u24/check/s247of1920-v26.txt` and the rerun is `w28-l7lhe0/research/unit-distance-24/results/u24/check/s247of1920-w28.txt`. The earlier copy was resumed under the legacy supervisor and disagrees on counts with the from-scratch rerun. The disagreement record does not name the differing cells. The counted copy is the rerun. This is why every legacy-resumed copy was rerun before judging.

The judge's differences, verbatim:

> ['COPIES: slice 247: accepted copies disagree on counts (w28-l7lhe0/research/unit-distance-24/results/u24/check/s247of1920-w28.txt, v26-ysvydx/research/unit-distance-24/results/u24/check/s247of1920-v26.txt)']

The plan's reason:

> suspect: its only PASS copies were resumed under the legacy timeout-6600 supervisor; re-run from scratch in the 2026-10-05 Claude wave (Sonnet, time-sliced brief BRIEF-u24-wave.md)

| plan | step seconds | run clock seconds | replay seconds | check seconds | control seconds | evidence seconds |
|---|---|---|---|---|---|---|
| u24-pilot | 94,954.5 | 109,184 | 15,199 | 35,488.894 | 163.713 | 3,305.33 |
| u24-full | 1,234,143.5 | 1,525,187 | 153,788 | 410,884.09 | 6,825.028 | 75,598.476 |
| u24-phaseb | 73,800.5 | 110,481 | 11,249 | 27,550.754 | 143.669 | 2,386.493 |

These are the judge's observed sums over its selected copies. They are not an elapsed fleet duration or a total including failed attempts. The rule is:

> fleet_status.py slice_record: per cell above the slice level not resumed (neither the cell nor its prune step), max(longest shard, shards summed / 4) + prune step + stage verification

The judge's cost limits:

> Step estimate applies the identical fleet_status.slice_record rule on both targets (four-shard normalization).
> Wall estimate uses run-dag2 clocks on both targets; includes prefix/startup, and after restart only the last session.
> Unfinished/resumed slices are lower bounds; missing t24 is zero, with its full t23 still subtracted. These bound the estimator, not the actual unsampled fleet cost.
> Overheads use weight 1 for heavy and 1910/32 for random; evidence audit is shown separately from G4+check+control.
> Receipts do not measure run-wide RSS or disk peaks. Disk-at-check is a lower bound on peak logical file bytes, not allocated blocks.

## 5. Cross-checks that were actually run

### Independently measured retained files

The independent scans measured retained level files against their recorded hashes and manifests. The saved summaries and coverage of enumeration stage manifests follow. This generator reads the reports; it does not rerun the scans.

Saved scan `research/unit-distance-24/evidence/retained-scan-2026-10-07.txt`:

```text
RETAINED SCAN OK: 1936 copies, 15488 retained level files measured, 0 problem(s)
```

Saved scan `research/unit-distance-24/evidence/retained-scan-2026-10-07b.txt`:

```text
RETAINED SCAN OK: 1936 copies, 15488 retained level files measured, 0 problem(s)
# coverage of rule 5: 3872 retained level files (n-m.g6), each bound to a stage manifest carrying children_written and children_file_sha256 (0 without)
```

The fleet audit's slice-share sums and unsliced stage totals:

| slice-level edge cell | slice-share sum | unsliced stage total |
|---|---|---|
| 20 | 1,384,579 | 1,384,579 |
| 21 | 476,585 | 476,585 |
| 22 | 51,819 | 51,819 |
| 23 | 3,011 | 3,011 |
| 24 | 198 | 198 |
| 25 | 25 | 25 |
| 26 | 2 | 2 |
| 27 | 1 | 1 |

| plan | plan prediction | accepted prediction | fleet total | per-plan control |
|---|---|---|---|---|
| u24-pilot | 82,582 | 82,582 | 97,912 | OK |
| u24-full | 5,293 | 5,293 | 97,912 | OK |
| u24-phaseb | 10,037 | 10,037 | 97,912 | OK |

The accepted predictions sum explicitly, in pilot, full, phase B order: 82,582 + 5,293 + 10,037 = 97,912; the fleet total is 97,912. Every eligible known configuration lies in the slice predicted for it and was found there, unpruned.

The known-graph headline predicate requires each accepted prediction to equal its plan prediction, and the coverage plans' accepted predictions to sum to the common fleet total. Individual per-plan controls cover subsets; their completion flags do not certify the union by themselves.

The reproduction sample has 50 accepted slices and 100 accepted copies. The published draw is:

> sorted(random.Random(20261003).sample(range(1920), 48)) (Python 3), committed before any of these copies exists

Chosen heavy slices: [344, 1535]. The judge compares accepted production and reproduction copies. Reproduction is by sample, not of every slice.

### Resumed copies and their from-scratch twins

The legacy supervisor relaunched workers in the same container. It could leave simultaneous writers and reuse an interrupted partial line. The tree-kill time-slice supervisor kills the process tree, quarantines partial files, and resumes valid checkpoints. The full plan's resumed copies use the legacy mechanism; the pilot and phase B resumed copies use the tree-kill mechanism. The source describes the holes and their repair:

> **time-slice supervisor landed; every resumed u24 slice is treated as suspect.** Codex audit
> (REPORT-timeslice-2026-10-01.md): the frozen worker starts every stage with `start_new_session=True`, so `timeout`
> kills the worker but not the running runbook; the relaunched worker resumes the same run directory while the orphan
> still writes (two writers). A separate single-writer hole: an interrupted filter part ending in a partial JSON line
> is reused by line count (the exact v05 error, reproduced on the frozen prune code). Two writers can also leave a
> shard whose child file is complete-looking but short (C reads parents to EOF after a concurrent truncation) and that
> passes chain, evidence and the 0.2% G4 sample, so a PASS of an overlapped slice is not sound. Fix, outside the frozen
> worker: `timeslice.sh` (tree-kill supervisor with a persistent PID/start-time snapshot and lock: kills recorded and
> current descendants before returning 124, and an orphaned previous tree before relaunching) and `u24-slices.py`
> (one whole slice per launch in phase A; for heavies, quarantine only partial files after a kill and resume the
> valid checkpoints). Tests + nine mutation controls pass here (`test_timeslice.sh --mutations`). All five briefs now
> run under it; check-ins every 360 minutes (each is a model turn; every 124 already wakes the worker).

The policy sentences, verbatim, at `coordination/cloud-workers/JOBS.md:1515 (the 10:40Z paragraph)`:

> Policy: every slice whose final runbook started more than ~20 s after the previous receipt on its branch (resumed
> after a relaunch in the same container), or that has two runbook pushes, is re-run from scratch under the
> supervisor by a new tag before the judge (scan: scratchpad overlap_scan.py, 481 receipts at 10:30Z: 337 clean,
> ~60 suspect, 84 first-on-branch to classify against fire times). The legacy pilot/repro heavies (u01..u10, r01, r02)
> cross many boundaries and accumulate writer sets: they are switched in place to the supervisor from a fresh run.

A rerun counts as a twin only when its saved row explicitly says it ran from scratch and reports no fresh recovered cells. A reproduction comparison counts only when the chosen copy's resumed-cell count is recorded as zero. A resumed candidate is shown below and does not count.

Every resumed accepted copy and its comparison:

| plan | slice | accepted copy | resume mechanism | from-scratch twin |
|---|---|---|---|---|
| u24-pilot | 344 | vm01/research/unit-distance-24/results/u24/check/s344of1920-vm01.txt | tree-kill time-slice supervisor | reproduction comparison: r01/research/unit-distance-24/results/u24/check/s344of1920-r01.txt; judge verdict OK |
| u24-pilot | 1,209 | u09-sgz9zi/research/unit-distance-24/results/u24/check/s1209of1920-u09.txt | tree-kill time-slice supervisor | vmr3 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:2; via the counted copy and the judge's duplicate-copy agreement |
| u24-pilot | 1,209 | u09-x7dha8/research/unit-distance-24/results/u24/check/s1209of1920-u09.txt | tree-kill time-slice supervisor | vmr3 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:2; direct comparison |
| u24-pilot | 1,474 | u07-aa336b/research/unit-distance-24/results/u24/check/s1474of1920-u07.txt | tree-kill time-slice supervisor | vmr3 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:1; direct comparison |
| u24-pilot | 1,639 | u10-c2xaqf/research/unit-distance-24/results/u24/check/s1639of1920-u10.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:10; direct comparison |
| u24-pilot | 1,639 | u10-vhb8bq/research/unit-distance-24/results/u24/check/s1639of1920-u10.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:10; via the counted copy and the judge's duplicate-copy agreement |
| u24-pilot | 1,651 | u05-umq7r7/research/unit-distance-24/results/u24/check/s1651of1920-u05.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:9; direct comparison |
| u24-pilot | 1,721 | u06-srvteg/research/unit-distance-24/results/u24/check/s1721of1920-u06.txt | tree-kill time-slice supervisor | vmr4 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:5; direct comparison |
| u24-pilot | 1,814 | u08-8w6cq5/research/unit-distance-24/results/u24/check/s1814of1920-u08.txt | tree-kill time-slice supervisor | vmr4 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:6; direct comparison |
| u24-full | 239 | v29-fxyv1b/research/unit-distance-24/results/u24/check/s239of1920-v29.txt | legacy same-container relaunch | vmr1 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl:1; direct comparison |
| u24-full | 830 | v29-fxyv1b/research/unit-distance-24/results/u24/check/s830of1920-v29.txt | legacy same-container relaunch | vmr1 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl:2; direct comparison |
| u24-full | 1,069 | v19-qayfjq/research/unit-distance-24/results/u24/check/s1069of1920-v19.txt | legacy same-container relaunch | vmr1 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl:3; direct comparison |
| u24-full | 1,352 | v06-hyf31m/research/unit-distance-24/results/u24/check/s1352of1920-v06.txt | legacy same-container relaunch | vmr2 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl:4; direct comparison |
| u24-full | 1,641 | v20-5iutaj/research/unit-distance-24/results/u24/check/s1641of1920-v20.txt | legacy same-container relaunch | vmr2 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl:5; direct comparison |
| u24-phaseb | 272 | w07-s86zer/research/unit-distance-24/results/u24/check/s272of1920-w07.txt | tree-kill time-slice supervisor | vmr3 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:3; direct comparison |
| u24-phaseb | 276 | w08-9did6s/research/unit-distance-24/results/u24/check/s276of1920-w08.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:12; direct comparison |
| u24-phaseb | 406 | w11-suxmrc/research/unit-distance-24/results/u24/check/s406of1920-w11.txt | tree-kill time-slice supervisor | vmr3 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:4; direct comparison |
| u24-phaseb | 466 | w12-4fkktd/research/unit-distance-24/results/u24/check/s466of1920-w12.txt | tree-kill time-slice supervisor | vmr4 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:7; direct comparison |
| u24-phaseb | 997 | w17/research/unit-distance-24/results/u24/check/s997of1920-w17.txt | tree-kill time-slice supervisor | vmr4 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:8; direct comparison |
| u24-phaseb | 1,183 | w21-7drrhb/research/unit-distance-24/results/u24/check/s1183of1920-w21.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:11; direct comparison |
| u24-phaseb | 1,260 | w23-lw7rks/research/unit-distance-24/results/u24/check/s1260of1920-w23.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:13; direct comparison |
| u24-phaseb | 1,270 | w24-dex65e/research/unit-distance-24/results/u24/check/s1270of1920-w24.txt | tree-kill time-slice supervisor | vmr6 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:15; direct comparison |
| u24-phaseb | 1,371 | w27-a4sf5r/research/unit-distance-24/results/u24/check/s1371of1920-w27.txt | tree-kill time-slice supervisor | vmr5 (IDENTICAL); research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl:14; direct comparison |

Resumed accepted copies with no recorded from-scratch twin:

None: every resumed accepted copy has a recorded twin.

A missing twin is listed here and does not fail a gate. Every saved rerun row must show identical file comparisons, a passing fresh receipt and explicit from-scratch freshness. Fresh comparisons are read from:

- research/unit-distance-24/evidence/rerun-resumed-2026-10-06.jsonl.
- research/unit-distance-24/evidence/rerun-resumed-supervisor-2026-10-07.jsonl.

| slice | counted tag | fresh tag | verdict | cells | hashed files | kept recovered cells | fresh recovered cells | fresh from scratch |
|---|---|---|---|---|---|---|---|---|
| 239 | v29 | vmr1 | IDENTICAL | 99 | 86 | 34 | 0 | yes |
| 830 | v29 | vmr1 | IDENTICAL | 99 | 86 | 35 | 0 | yes |
| 1,069 | v19 | vmr1 | IDENTICAL | 99 | 86 | 34 | 0 | yes |
| 1,352 | v06 | vmr2 | IDENTICAL | 99 | 86 | 9 | 0 | yes |
| 1,641 | v20 | vmr2 | IDENTICAL | 99 | 86 | 8 | 0 | yes |
| 1,474 | u07 | vmr3 | IDENTICAL | 99 | 86 | 82 | 0 | yes |
| 1,209 | u09 | vmr3 | IDENTICAL | 99 | 86 | 62 | 0 | yes |
| 272 | w07 | vmr3 | IDENTICAL | 99 | 86 | 8 | 0 | yes |
| 406 | w11 | vmr3 | IDENTICAL | 99 | 86 | 68 | 0 | yes |
| 1,721 | u06 | vmr4 | IDENTICAL | 99 | 86 | 62 | 0 | yes |
| 1,814 | u08 | vmr4 | IDENTICAL | 99 | 86 | 62 | 0 | yes |
| 466 | w12 | vmr4 | IDENTICAL | 99 | 86 | 82 | 0 | yes |
| 997 | w17 | vmr4 | IDENTICAL | 99 | 86 | 68 | 0 | yes |
| 1,651 | u05 | vmr5 | IDENTICAL | 99 | 86 | 68 | 0 | yes |
| 1,639 | u10 | vmr5 | IDENTICAL | 99 | 86 | 82 | 0 | yes |
| 1,183 | w21 | vmr5 | IDENTICAL | 99 | 86 | 82 | 0 | yes |
| 276 | w08 | vmr5 | IDENTICAL | 99 | 86 | 62 | 0 | yes |
| 1,260 | w23 | vmr5 | IDENTICAL | 99 | 86 | 69 | 0 | yes |
| 1,371 | w27 | vmr5 | IDENTICAL | 99 | 86 | 68 | 0 | yes |
| 1,270 | w24 | vmr6 | IDENTICAL | 99 | 86 | 82 | 0 | yes |

These comparisons cover every cell's `counts.json`, the retained-file hashes, `reach.json`, `run-config.json`, and the known-graph record with its machine-local `run` field removed. They require the fresh receipt's passing verdict and zero recovered cells in its structure. Deleted intermediate files cannot be compared byte for byte. Structure and inventory records are excluded because their retained-file lists differ by runbook version. The comparison procedure is described in `tools/rerun_compare.py`.

## 6. Gates

The contract's gate requirements, verbatim:

> - **G0** Literature: nothing published decides u(24) or contradicts the inputs (recheck at the end).
> - **G1** The extensions reviewed: the table extensions (`run-dag2.py`, `prune.py`, the runbook) and the new checker
>   and worker, each with its tests, and an independent review of the checker's U24 edits and the worker (codex,
>   read-only), closed.
> - **G2** The pilot (`## u24-pilot` in `coordination/cloud-workers/JOBS.md`): 42 slices, measured.
> - **G3** The whole run: every one of the 1,920 slices with a receipt that the coordinator's judge accepts, derived
>   from the recorded output (not the worker's label), every prefix the prefix of a whole check, G4 PASS on every
>   slice, and the fleet's summary audit (`verify-chain-u24.py --summary-only`) complete.
> - **G4** The known-graph control complete over the whole run.
> - **G5** The reproduction sample: every sampled slice's result copy identical to the first run's.
> - **G6** The write-up generated from the evidence, with its dependencies stated.

| gate | status here | evidence or remaining item |
|---|---|---|
| G0 | met | literature |
| G1 | met | closure record research/unit-distance-24/G1-verification-2026-10-07.md: first G1 verdict CLOSED; basis reported by the closure note: Targeted verification rounds 1, 2, 3 end with verifier verdict CLOSED; 656 field families: 386 measured or derived, 152 historical, 118 provenance; independent retained scan: 1,936 copies, 15,488 files, 0 problems; four-plan re-judge JUDGE OK, fleet audit OK. The final verification sampled 30 bound fields. Sampling is not exhaustive. |
| G2 | met | pilot |
| G3 | met | rejudge-equality; rerun-reason-accounting; plan-pilot; plan-full; plan-phaseb; partition; fleet-audit; resumed-reruns; survivor-refutations |
| G4 | met | known-control |
| G5 | met | reproduction |
| G6 | met | generated from the hashed inputs; fixed-text and conditional-claim lint checked before writing |

The literature verdict recorded in `research/unit-distance-24/G0-literature-2026-10-06.md`: nothing published decides u(24) or contradicts the inputs. This generator reads the literature note; it does not repeat its searches.

The closure input is `research/unit-distance-24/G1-verification-2026-10-07.md`; its first matching verdict is CLOSED. The basis stated by that file is:

Targeted verification rounds 1, 2, 3 end with verifier verdict CLOSED; 656 field families: 386 measured or derived, 152 historical, 118 provenance; independent retained scan: 1,936 copies, 15,488 files, 0 problems; four-plan re-judge JUDGE OK, fleet audit OK. The final verification sampled 30 bound fields. Sampling is not exhaustive.

The generator reads the closure record and does not repeat its targeted verification. Historical (deleted-content) fields rest on the worker's check before deletion. The saved audit cannot re-measure deleted files; the field enumeration states those limits row by row. Without an explicit final closure record, closure is not re-derived by this generator. The historical review files are:

- research/unit-distance-24/REPORT-review-fixes-2026-10-01.md.
- research/unit-distance-24/REPORT-review3-fixes-2026-10-01.md.
- research/unit-distance-24/REPORT-rereview-fixes-2026-10-01.md.

## 7. What is claimed, and what is not

If the gates of Section 6 are all green, u(24) = 68. This condition includes the mathematical and software dependencies stated above, including our own preceding results and the review gate. The generated headline summarizes the saved evidence predicates; it does not independently discharge those dependencies.

The individual survivor certificate does not establish a complete classification of graphs of its order. The summary audit does not reconstruct deleted intermediate certificate files. Enumeration correctness continues to depend on the reviewed augmentation and pruning programs, their checkers, the common canonical-labelling software, and the stated mathematical lemmas.

## 8. How to check it

The 2026-10-06 reports in `research/unit-distance-24/evidence/judge-final-2026-10-06/README.md` are the original judge of this snapshot. The r2 reports in `research/unit-distance-24/evidence/judge-final-2026-10-07-r2/README.md` are the re-judge with the final receipt audit. They use the same branch/commit snapshot and are identical in every key field.

The compared JSON keys are ['verdict', 'accepted_slices', 'accepted_copies', 'missing', 'duplicates', 'rejected', 'g4', 'survivors', 'resumed_slices', 'rerun_disagreements']; equality is a headline predicate. Read both READMEs for the snapshot's branch commits, audit history and judge commands. Read the contract, the source JSON reports and the saved survivor check. Recompute the file digests listed in `result-values.json` and its compressed source manifest. These commands are reproduction instructions; this generator reads saved reports and does not run the judge or the enumeration. Use a disposable repository checkout and writable output directories.

Build ROOT from `research/unit-distance-24/evidence/judge-final-2026-10-07-r2/sources.tsv` by the procedure in `research/unit-distance-24/evidence/judge-final-2026-10-06/README.md`: fetch each recorded commit and extract its result directory under the branch suffix. This command template assumes ROOT is an empty directory whose absolute path the caller supplies:

```sh
mkdir -p "$ROOT"
while IFS="$(printf '\t')" read -r branch fetched advertised; do
  git fetch origin "$fetched"
  case "$branch" in
    *cloud-u24-*) suffix=${branch##*cloud-u24-} ;;
    *codex-u24-*) suffix=codex-${branch##*codex-u24-} ;;
    *) exit 1 ;;
  esac
  mkdir -p "$ROOT/$suffix"
  git archive "$fetched" research/unit-distance-24/results/u24 | tar -x -C "$ROOT/$suffix"
done < research/unit-distance-24/evidence/judge-final-2026-10-07-r2/sources.tsv
```

Judge each published plan, then audit the union and run the audit's mutation tests:

```sh
nice -n 15 /usr/bin/python3 -B research/unit-distance-24/tools/judge.py "$ROOT" --plan coordination/cloud-workers/u24-pilot-plan.json --out judge-pilot.json
nice -n 15 /usr/bin/python3 -B research/unit-distance-24/tools/judge.py "$ROOT" --plan coordination/cloud-workers/u24-full-plan.json --out judge-full.json
nice -n 15 /usr/bin/python3 -B research/unit-distance-24/tools/judge.py "$ROOT" --plan coordination/cloud-workers/u24-phaseb-plan.json --out judge-phaseb.json
nice -n 15 /usr/bin/python3 -B research/unit-distance-24/tools/judge.py "$ROOT" --plan coordination/cloud-workers/u24-repro-plan.json --out judge-repro.json
nice -n 15 /usr/bin/python3 -B research/unit-distance-24/tools/fleet_audit.py "$ROOT" --out fleet-audit.json
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/test_fleet_audit.py -v
```

Fresh-copy source addresses are in `research/unit-distance-24/evidence/fresh-copies-2026-10-07.json`, SHA digest `306ddc43211dd984cb91c8414853a312a03acad636ab917b3d94af50aa5cee4d`. The values file binds each comparison's tag and slice to the manifest's branch, commit, receipt path, receipt digest and structure digest:

| fresh tag | branch | commit |
|---|---|---|
| vmr1 | claude/answering-alexeev-u22-cloud-u24-vmr1 | 758e066266554fea6644fd37e0107dafdba11d26 |
| vmr2 | claude/answering-alexeev-u22-cloud-u24-vmr2 | f7b54f4c012ec3e6bc32fd0a592989a27696c547 |
| vmr3 | claude/answering-alexeev-u22-cloud-u24-vmr3 | 13c7e29e3c58a16ec7c2622e7f977a5c85b792f9 |
| vmr4 | claude/answering-alexeev-u22-cloud-u24-vmr4 | eadbcd67104fd06af5665cef29e9877dd1483aca |
| vmr5 | claude/answering-alexeev-u22-cloud-u24-vmr5 | a231a1c8f4053fffe197917d530aa17bf15dc7b2 |
| vmr6 | claude/answering-alexeev-u22-cloud-u24-vmr6 | 65435e38a27144b1792a118aa56a83ea7f03bb59 |

Extract the immutable fresh commits in a disposable checkout, then verify their saved receipt and structure digests. The template sets the FRESH tag variables used by the comparisons:

```sh
export FRESH_WORK="$PWD/fresh-copies"
mkdir -p "$FRESH_WORK"
nice -n 15 timeout 1800 /usr/bin/python3 -B - <<'PY' > "$FRESH_WORK/sources.tsv"
import json
from pathlib import Path
manifest = json.loads(Path('research/unit-distance-24/evidence/fresh-copies-2026-10-07.json').read_text())
for tag, address in sorted(manifest["tags"].items()):
    print(tag, address["branch"], address["commit"], sep="\t")
PY
while IFS=$'\t' read -r fresh_tag fresh_branch fresh_commit; do
  git fetch origin "$fresh_branch"
  mkdir -p "$FRESH_WORK/$fresh_tag"
  git archive "$fresh_commit" research/unit-distance-24/results/u24 | tar -x -C "$FRESH_WORK/$fresh_tag"
  export "FRESH_${fresh_tag}_ROOT=$FRESH_WORK/$fresh_tag/research/unit-distance-24/results/u24"
done < "$FRESH_WORK/sources.tsv"
nice -n 15 timeout 1800 /usr/bin/python3 -B - <<'PY'
import hashlib, json, os
from pathlib import Path
manifest = json.loads(Path('research/unit-distance-24/evidence/fresh-copies-2026-10-07.json').read_text())
for tag, address in manifest["tags"].items():
    base = Path(os.environ["FRESH_WORK"]) / tag
    for record in address["slices"].values():
        receipt = base / record["receipt"]
        assert hashlib.sha256(receipt.read_bytes()).hexdigest() == record["receipt_sha256"]
        structure = receipt.with_suffix(".structure.json")
        assert hashlib.sha256(structure.read_bytes()).hexdigest() == record["structure_sha256"]
PY
```

Compare every saved rerun row and run its mutation control. Each FRESH tag variable below names that rerun's extracted result directory, as distinct from the whole snapshot ROOT. Use the source addresses above:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 239 "$ROOT/v29-fxyv1b/research/unit-distance-24/results/u24" v29 "${FRESH_vmr1_ROOT}" vmr1
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 239 "$ROOT/v29-fxyv1b/research/unit-distance-24/results/u24" v29
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 830 "$ROOT/v29-fxyv1b/research/unit-distance-24/results/u24" v29 "${FRESH_vmr1_ROOT}" vmr1
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 830 "$ROOT/v29-fxyv1b/research/unit-distance-24/results/u24" v29
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1069 "$ROOT/v19-qayfjq/research/unit-distance-24/results/u24" v19 "${FRESH_vmr1_ROOT}" vmr1
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1069 "$ROOT/v19-qayfjq/research/unit-distance-24/results/u24" v19
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1352 "$ROOT/v06-hyf31m/research/unit-distance-24/results/u24" v06 "${FRESH_vmr2_ROOT}" vmr2
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1352 "$ROOT/v06-hyf31m/research/unit-distance-24/results/u24" v06
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1641 "$ROOT/v20-5iutaj/research/unit-distance-24/results/u24" v20 "${FRESH_vmr2_ROOT}" vmr2
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1641 "$ROOT/v20-5iutaj/research/unit-distance-24/results/u24" v20
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1474 "$ROOT/u07-aa336b/research/unit-distance-24/results/u24" u07 "${FRESH_vmr3_ROOT}" vmr3
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1474 "$ROOT/u07-aa336b/research/unit-distance-24/results/u24" u07
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1209 "$ROOT/u09-sgz9zi/research/unit-distance-24/results/u24" u09 "${FRESH_vmr3_ROOT}" vmr3
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1209 "$ROOT/u09-sgz9zi/research/unit-distance-24/results/u24" u09
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 272 "$ROOT/w07-s86zer/research/unit-distance-24/results/u24" w07 "${FRESH_vmr3_ROOT}" vmr3
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 272 "$ROOT/w07-s86zer/research/unit-distance-24/results/u24" w07
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 406 "$ROOT/w11-suxmrc/research/unit-distance-24/results/u24" w11 "${FRESH_vmr3_ROOT}" vmr3
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 406 "$ROOT/w11-suxmrc/research/unit-distance-24/results/u24" w11
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1721 "$ROOT/u06-srvteg/research/unit-distance-24/results/u24" u06 "${FRESH_vmr4_ROOT}" vmr4
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1721 "$ROOT/u06-srvteg/research/unit-distance-24/results/u24" u06
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1814 "$ROOT/u08-8w6cq5/research/unit-distance-24/results/u24" u08 "${FRESH_vmr4_ROOT}" vmr4
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1814 "$ROOT/u08-8w6cq5/research/unit-distance-24/results/u24" u08
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 466 "$ROOT/w12-4fkktd/research/unit-distance-24/results/u24" w12 "${FRESH_vmr4_ROOT}" vmr4
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 466 "$ROOT/w12-4fkktd/research/unit-distance-24/results/u24" w12
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 997 "$ROOT/w17/research/unit-distance-24/results/u24" w17 "${FRESH_vmr4_ROOT}" vmr4
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 997 "$ROOT/w17/research/unit-distance-24/results/u24" w17
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1651 "$ROOT/u05-umq7r7/research/unit-distance-24/results/u24" u05 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1651 "$ROOT/u05-umq7r7/research/unit-distance-24/results/u24" u05
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1639 "$ROOT/u10-c2xaqf/research/unit-distance-24/results/u24" u10 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1639 "$ROOT/u10-c2xaqf/research/unit-distance-24/results/u24" u10
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1183 "$ROOT/w21-7drrhb/research/unit-distance-24/results/u24" w21 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1183 "$ROOT/w21-7drrhb/research/unit-distance-24/results/u24" w21
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 276 "$ROOT/w08-9did6s/research/unit-distance-24/results/u24" w08 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 276 "$ROOT/w08-9did6s/research/unit-distance-24/results/u24" w08
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1260 "$ROOT/w23-lw7rks/research/unit-distance-24/results/u24" w23 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1260 "$ROOT/w23-lw7rks/research/unit-distance-24/results/u24" w23
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1371 "$ROOT/w27-a4sf5r/research/unit-distance-24/results/u24" w27 "${FRESH_vmr5_ROOT}" vmr5
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1371 "$ROOT/w27-a4sf5r/research/unit-distance-24/results/u24" w27
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py 1270 "$ROOT/w24-dex65e/research/unit-distance-24/results/u24" w24 "${FRESH_vmr6_ROOT}" vmr6
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/rerun_compare.py --self-test 1270 "$ROOT/w24-dex65e/research/unit-distance-24/results/u24" w24
```

Check the survivor with the frozen checker's Python environment, named CHECKER_PYTHON:

```sh
nice -n 15 timeout 1800 "$CHECKER_PYTHON" -B research/unit-distance-24/survivor-s50/check_survivor.py
```

For the blind check, copy the complete supplied bundle named in its report into BLIND_WORK, including the supplied records and survivor graph file. Its scripts resolve inputs beside themselves and write outputs there. Use its Python environment with NetworkX; the certificate script uses the frozen checker environment and filesystem isolation recorded in the bundle:

```sh
nice -n 15 timeout 1800 "$CHECKER_PYTHON" -B "$BLIND_WORK/blind_check.py"
nice -n 15 timeout 1800 "$CHECKER_PYTHON" -B "$BLIND_WORK/run_certificates.py"
```

Generate the write-up and run its evidence-mutation suite. The last test regenerates from the untouched real inputs and compares the document, compact values and deterministic source sidecar with the first generation, apart from the generation timestamp:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/write_result.py --repo . --root "$ROOT"
U24_TEST_REPO="$PWD" U24_TEST_ROOT="$ROOT" nice -n 15 timeout 1800 /usr/bin/python3 -B research/unit-distance-24/tools/test_write_result.py -v
```

The default reads the saved survivor output. `--live-survivor --checker-python PYTHON` runs the existing checker script in a read-only filesystem with writable scratch under the output directory. Use the frozen checker's Python environment for that external command.
