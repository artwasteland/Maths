# G5 round 15: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 15 (u(23), branch claude/answering-alexeev-u22, HEAD fc65a372b9). Your round 14 was OPEN (three MAJOR).
The response is research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round14-read-gpt-6-astra.md
("Response"); the fixes are commit fc65a372b9 (and the fleet's G4 gate now also needs every replay in its mode's scope, target_check.py --scope-only). Read the files themselves: research/unit-distance-23/tools/target_check.py
(now running the G5-closed verify-chain.py --summary-only over every copy, and pinning what it does not),
research/unit-distance-23/tools/write_result.py (decide(): the controls and the full re-run as gate evidence),
research/unit-distance-23/tools/verify_sample.py.

Your task:
- Check each round-14 finding against its fix: is your reproduction now caught, and does the fix open a new hole? In
  particular, can target_check.py say OK, or write_result.py read a gate as met or leave COMPLETE, when the audit it
  now relies on reports a problem, or when a control's evidence is wrong in a way neither layer pins?
- Is anything the claim rests on still unchecked?

Work read-only: reproduce with in-memory edits of parsed data or scratch copies, never editing the repository or the
evidence. Answer with numbered findings, each with its severity (FATAL, MAJOR, MINOR), the file and line, and a
concrete failure scenario. End with exactly one line: "G5 round 15: CLOSED" if there is no FATAL or MAJOR finding,
otherwise "G5 round 15: OPEN (n findings)". Do not modify any file.

## Final answer, verbatim

Reviewed `fc65a372b9`, read-only. Three MAJOR findings remain.

| Round-14 finding | Assessment |
|---|---|
| 1. Unaudited copies | **CLOSED.** `target_check.py:146–148,218–219` rejects the original fixture: 1 complete, 1,919 failing. G6 also rejects contradictory audit coverage. |
| 2. Full replay scope | **PARTIALLY CLOSED.** Both original mutations are rejected at `target_check.py:115–129`; the scope checks still accept the cases below. |
| 3. Interrupted failure reports | **CLOSED.** `write_result.py:996–1000,1017–1022` produces CONTROL FAILED for both interrupted-control reproductions. |

For **each** new mutation below, I checked the complete 1,955-copy fleet using memory overlays. Results were:

- Pinned summary audit: **COVERAGE OK**, exit 3.
- Scope gate: **G4-SCOPE OK**, 101/101 full and 1,854/1,854 slice replays, exit 0.
- G6 with otherwise passing evidence: **COMPLETE**, G4 met, clean lint.

1. **MAJOR — Seed recomputation counts are not bound to the actual seed-file counts.**

   **Location:** [target_check.py:118](<repo>/research/unit-distance-23/tools/target_check.py:118), lines 118–125.

   On `f01-jjpzl7/s0of1920`, change the replay’s `(10,14)` seed record to:
   ```
   records = 0
   enum2_records = 0
   sampled = 0
   ```
   Leave its successful full-check flags unchanged. The run summary still records **24,862** seed graphs.

   Both layers accept this contradiction. The new check compares the replay’s two counts only with each other; it never requires either to equal the run’s seed count. Thus evidence claiming a successful comparison of empty seed files satisfies the exhaustive seed-check requirement.

   Bind the seed record to the audited cell’s file count and validate its count domains.

2. **MAJOR — An unsampled cell satisfies the “sampled row” requirement.**

   **Location:** [target_check.py:126](<repo>/research/unit-distance-23/tools/target_check.py:126), lines 126–129.

   On the same slice, keep the `(11,17)` replay row and its **31,127** `parents_in_cell`, but set:
   ```
   sampled = processed = production_children = enum2_children = mismatches = 0
   ```
   Recompute the per-level totals, summary totals and matching fingerprint totals.

   Everything passes. `have` tests only the cell’s name, so a row explicitly reporting **no replayed parents** satisfies the requirement. Other cells supply the positive aggregate sample required by the underlying checker.

   Require actual sampling for every required nonempty cell, consistent with the pinned sampling policy.

3. **MAJOR — Resumed cells bypass the new scope requirement.**

   **Location:** [target_check.py:127](<repo>/research/unit-distance-23/tools/target_check.py:127); callers at lines 155–175 and 374–375.

   Mark `(11,17)` resumed in the final summary and remove its parent fields, retaining its original record in an in-memory `history/INDEX.json` and history summary. Remove its G4 replay row and reconcile the replay totals.

   The pinned audit recovers and accepts the historical record containing **31,127 parents**. The new scope check reads only the final entry, treats its missing `parents` as zero, and requires no replay row. Both gates pass.

   Scope must use the parent evidence accepted by the audit—including recovered history and complementary copies—not the final summary’s optional parent field.

G5 round 15: OPEN (3 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

1. **Seed counts.** A full replay's level-10 seed record now needs all five counts (records, enum2_records, sampled,
   only_seed_file, only_enum2) to be ints, not bools or floats. records and enum2_records must equal the audited
   cell's children, which is the count the audit binds to the seed file through hashes.json. Nothing may be on only
   one side, and sampled must be between 1 and records. Your reproduction (all three counts 0, the flags kept) is
   caught: "seed cell 10-14 is not recomputed in full over its 24862 audited graphs: records 0, enum2 0".
2. **Unsampled rows.** A required row needs parents_in_cell equal to the audited parents, and sampled between the
   policy's share (at least 1) and the parents. The share is all of them up to whole_max (100), else at least
   ceil(0.001 x parents). Measured first: every row of the fleet and of the control meets it. Your reproduction, its
   totals rebalanced, is caught: "row of 11-17 has parents 31127 and sampled 0 ... (at least 32 to sample)".
3. **Resumed cells.** The scope check no longer reads the final summary's parent field. It imports the pinned
   verify-chain.py (the bytes the audit runs, sha256-checked) and takes the accepted parent evidence from its
   summary_audit(), pooled over the slice's copies. That evidence includes a resumed cell's parents recovered from
   history. Your reproduction (the cell resumed, its parents only in history, its row removed, totals rebalanced) is
   caught: "no row for cell 11-17 (31127 audited parents)".

Tightened while fixing these, each with a red control:
- A copy the audit cannot read in-process now fails. Before, its reading was empty and required nothing.
- Copies of one slice must agree on every audited parent count. Measured: the fleet's 35 slices with several copies
  all do.
- Every copy of a slice must pass, not just one of them. Measured: no slice of the fleet or of the control has a
  failing copy beside a passing one.
- A replay row naming a malformed or repeated cell fails. Before, a malformed name crashed the tool.
- An audited parent count that is not an int fails. Before, it was skipped.

The known-graph red control also caught its fault for the wrong reason. With slices missing, the coverage rule caught
it, not the known rule. It now drops a known graph that is actually kept, gives the audit a complete run's coverage,
and counts only the known rule's line. It reports "known graph(s) [0, 4] of 5 not kept at (21,57)"; graph 4 is not
yet kept by the running calibration.

Self-tests: target_check.py passes 24 of 24 on the control's real data and 24 of 24 on the calibration's. The
fleet's G4 scope: 101 of 101 full-mode and 1,854 of 1,854 slice-mode replays.
