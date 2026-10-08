# G5 round 14: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 14 (u(23), branch claude/answering-alexeev-u22, HEAD 4aa7bc4738). Your round 13 was OPEN (four MAJOR, one MINOR).
The response is research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round13-read-gpt-6-astra.md
("Response"); the fixes are commit 4aa7bc4738. Read the files themselves: research/unit-distance-23/tools/target_check.py
(now running the G5-closed verify-chain.py --summary-only over every copy, and pinning what it does not),
research/unit-distance-23/tools/write_result.py (decide(): the controls and the full re-run as gate evidence),
research/unit-distance-23/tools/verify_sample.py.

Your task:
- Check each round-13 finding against its fix: is your reproduction now caught, and does the fix open a new hole? In
  particular, can target_check.py say OK, or write_result.py read a gate as met or leave COMPLETE, when the audit it
  now relies on reports a problem, or when a control's evidence is wrong in a way neither layer pins?
- Is anything the claim rests on still unchecked?

Work read-only: reproduce with in-memory edits of parsed data or scratch copies, never editing the repository or the
evidence. Answer with numbered findings, each with its severity (FATAL, MAJOR, MINOR), the file and line, and a
concrete failure scenario. End with exactly one line: "G5 round 14: CLOSED" if there is no FATAL or MAJOR finding,
otherwise "G5 round 14: OPEN (n findings)". Do not modify any file.

## Final answer, verbatim

Reviewed `4aa7bc4738`; all reproductions used memory overlays. No files were modified.

| Round-13 finding | Fix assessment |
|---|---|
| 1. Parent coverage/counts | Original mutations **caught** by the delegated audit. A new bypass remains below. |
| 2. Failed replay details | Original failed-stage, failed-seed and impossible-sample mutations **caught**. |
| 3. Full replay scope/policy | **PARTIALLY CLOSED:** sampling policy is pinned; full replay scope remains insufficiently checked. |
| 4. Failures treated as absence | **PARTIALLY CLOSED:** complete failure reports now block COMPLETE; interrupted reports can still escape. |
| 5. Digest self-test | **CLOSED:** it now removes the digest. The current all-mode self-test passed. |

1. **MAJOR — Unaudited copies can produce TARGET-CHECK OK and a met G6 gate.**

   **Locations:** [target_check.py:146](<repo>/research/unit-distance-23/tools/target_check.py:146), lines 146–175; missing-summary suppression at line 94; [write_result.py:451](<repo>/research/unit-distance-23/tools/write_result.py:451).

   `collect()` counts directories without `run-summary.json` as copies but excludes them from the audit. The audit’s missing-summary complaint is then discarded, while `evaluate()` accepts those copies based solely on their local checks.

   **Reproduction:** a 1,920-directory memory fixture containing the real `k01-fpscz3/s0of1920` summary, with the other 1,919 directories supplying locally required files but no summary. Actual output:
   ```
   SELF-TEST passed: 11 of 11 red controls caught
   AUDIT: COVERAGE (summary only) FAIL (1 problems, 0 unresolved)
   TARGET-CHECK OK: (22,61): 1920 of 1920 slices complete, G4 PASS 1920; 0 failing, 0 missing; kept at (22,61): 0 distinct graph(s)
   ```
   Exit **0**. Feeding that output through G6, with other evidence passing, gives **COMPLETE**, tree control **empty**, and clean lint. G6 does not parse the contradictory AUDIT verdict.

   Every counted copy must be covered by the audit; a completed control must also require successful audit coverage.

2. **MAJOR — A purported full G4 replay can omit the prefix and exhaustive seed checks.**

   **Locations:** [target_check.py:47](<repo>/research/unit-distance-23/tools/target_check.py:47), replay pins and lines 131–133; [verify-chain.py:731](<repo>/research/unit-distance-22/enum/verify-chain.py:731), lines 731–750.

   **Reproduction on the real slice above:** keep fingerprint mode `full`, set `levels="13-22"`, remove prefix replay rows and whole-prefix stage checks, retain only seed `(1,0)`, and reconcile the aggregate totals. Both layers accept it: the audit reports only the expected absence of the other slices.

   Independently, deleting the full-check fields from all seven level-10 seed records—leaving the successful sample checks that `--seeds sample` produces—also passes both layers.

   The original empty-seed reproduction is caught only because `seeds=[]`. Neither layer requires the full level-10 reconstruction or the full replay’s required scope. Round-13 finding 3 therefore remains open.

3. **MAJOR — An explicit control failure disappears if its final verdict line is absent.**

   **Location:** [write_result.py:975](<repo>/research/unit-distance-23/tools/write_result.py:975), lines 975–982 and 994–1000.

   `bad22` and `badcal` require a non-null `verdict` before considering recorded problems.

   **Reproduction:** retain a control report’s explicit `PROBLEM: audit: … stage files that do not re-derive`, truncate before `TARGET-CHECK`, and record a nonzero process exit. `parse_target()` preserves the problem, but `build()` produces **COMPLETE**, the affected gate **open**, and clean lint. Reproduced for both controls.

   A recorded problem must block COMPLETE independently of whether an interrupted checker printed its final verdict.

G5 round 14: OPEN (3 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

1. **Unaudited copies.** A copy without run-summary.json now fails in target_check.py ("the audit did not see this
   copy"). When every slice is in, the audit's own COVERAGE line must say OK, or it is a PROBLEM. write_result.py
   parses the AUDIT line: a met gate needs it OK, and a complete run whose audit line is not OK is CONTROL FAILED
   (what-if control22-audit-contradiction).
2. **Full replay scope.** The scope rule was measured on the real data first. A full-mode replay needs:
   - levels "";
   - each level-10 seed cell of the copy's reach table recomputed in full and identical (full_check, full_identical,
     enum2 records equal to the seed file's, nothing on only one side);
   - a row for every cell from level 11 to N that has parents in the copy's run-summary.json.
   A slice-mode replay needs levels 13 to N, a row for every such cell there, and no rows outside the mode's levels.
   Every real replay meets it: the (23,65) fleet's 101 of 101 full-mode and 1,854 of 1,854 slice-mode replays, and the
   (22,61) control's 10 of 10 and 1,700 of 1,700. The check applies to the controls' copies, and to the fleet itself
   through target_check.py --scope-only: write_result.py's G4 gate now needs `G4-SCOPE OK` (what-if g4-scope-fail).
   Your reproduction, with its totals rebalanced, is now caught by both layers. The audit notices the fingerprint's
   totals no longer match the summary's, and the scope check names the levels, the missing seed records and the
   prefix cells without rows. Deleting the seeds' full-check fields is caught by the scope check.
3. **Interrupted reports.** In write_result.py a control's PROBLEM line is a failure whether or not a verdict line
   follows. A control that ran and printed no verdict is a failure too, never open (what-if control22-interrupted).
Self-tests: target_check.py 14 of 14 on the control's real data; write_result.py 126 of 126.
