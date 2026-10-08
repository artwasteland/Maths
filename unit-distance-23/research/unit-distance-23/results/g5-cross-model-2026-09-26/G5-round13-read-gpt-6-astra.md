# G5 round 13: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 13 (u(23), branch claude/answering-alexeev-u22, HEAD 4651b73022). Your round 12 was OPEN (four MAJOR, one MINOR),
all in the new gate evidence. The fixes are commit 228be7e3d8; read the files themselves:
research/unit-distance-23/tools/target_check.py (rewritten), research/unit-distance-23/tools/write_result.py (decide():
the tree control, the calibration and the full re-run as gate evidence, bound to the contract's parameters, failures
apart from absence), research/unit-distance-23/tools/verify_sample.py (--all).

Also new since round 12, and running now: the full re-run moved from codex cloud to Claude cloud (codex tasks stop at
about an hour and return results only as a size-limited diff). coordination/cloud-workers/u23-verify-local.sh now
takes U23_PUSH and U23_TOOLCHAIN from the environment and, after a restart, skips a slice whose check output already
says pass (the first slice only while its run directory exists); coordination/cloud-workers/BRIEF-u23-verify-all.md
is the workers' brief, coordination/cloud-workers/u23-verify-all-claude-plan.json their plan (48 workers, every slice
once), JOBS.md entry u23-verify-all-claude. verify_sample.py --all judges their branches (cloud-u23-a*).

Your task:
- Check each round-12 finding against its fix: is your reproduction now caught, and does the fix open a new hole?
- Attack target_check.py again: can it say OK when a slice is missing, failing, run with other options, or not
  replayed as the runbook replays it (full mode on a worker's first slice, slice mode after), or when the top level
  keeps a graph (the control) or loses a known graph (the calibration)?
- Attack the new driver path: can a restart's skip, or the one-slice-at-a-time deletion, let a slice pass that was
  never checked, or check a slice's prefix against a directory that is not the first slice's?
- Can write_result.py reach COMPLETE, or read a gate as met, when any of its evidence is wrong?

Work read-only: reproduce with in-memory edits of parsed data or scratch copies, never editing the repository or the
evidence. Answer with numbered findings, each with its severity (FATAL, MAJOR, MINOR), the file and line, and a
concrete failure scenario. End with exactly one line: "G5 round 13: CLOSED" if there is no FATAL or MAJOR finding,
otherwise "G5 round 13: OPEN (n findings)". Do not modify any file.

## Final answer, verbatim

Four MAJOR findings remain at `4651b73022`. No files were modified.

| Round-12 finding | Assessment |
|---|---|
| 1. Slice identity/completeness | **PARTIALLY CLOSED.** Original relabelling and removed-level reproductions are rejected at `target_check.py:142–170`; coverage gaps remain below. |
| 2. Unsupported G4 PASS | **PARTIALLY CLOSED.** Minimal summaries, mismatching cells and inconsistent aggregate totals are rejected at `:101–123`; other failed evidence still passes. |
| 3. Wrong control requirements | **CLOSED.** Degree-six and four-graph reproductions now produce `CONTROL FAILED`, through `write_result.py:973–998`. |
| 4. Failures classified as absence | **PARTIALLY CLOSED.** Recorded failing slices and full-rerun problems now block COMPLETE; global control failures still do not. |
| 5. Ineffective task-removal control | **CLOSED.** `verify_sample.py:394–395` removes an entire task and detects the incomplete plan. |

1. **MAJOR — Required-cell presence still does not establish coverage.**  
   **Location:** [target_check.py:162](<repo>/research/unit-distance-23/tools/target_check.py:162), lines 162–185.

   On the real `k01-fpscz3/s0of1920` record, I changed cell `(13,23)` to:
   ```
   parent_edge_counts=[]
   parent_sources=[]
   parents=0
   ```
   Its required parents were previously edge counts 20 and 21. `read_copy()` reports no problem; an otherwise passing 1,920-entry fixture produces **TARGET-CHECK OK**.

   Separately, `children=-1` passes, as does a top-cell prune count declaring one kept graph while the shipped keep file is empty. Parent coverage and count/file consistency remain unchecked.

2. **MAJOR — Explicitly failed replay details are accepted.**  
   **Location:** [target_check.py:105](<repo>/research/unit-distance-23/tools/target_check.py:105), lines 105–124.

   **Reproductions:** independently change the real replay’s `stages[0].ok` to `false`, or `seeds[0].identical` to `false`. Both pass `read_copy()`; the failed-stage fixture produces **TARGET-CHECK OK**.

   The checker trusts `stages_ok` and `all_identical` without reconciling those flags with the detailed evidence. It also accepts a row reporting 32 sampled parents from `parents_in_cell=0`.

3. **MAJOR — A “full” replay need not cover the prefix or use the runbook’s sampling policy.**  
   **Locations:** [target_check.py:88](<repo>/research/unit-distance-23/tools/target_check.py:88), lines 88–124 and 221–222.

   **Reproduction:** retain fingerprint mode `full`, restrict the summary to `levels="13-22"`, remove its seed records and prefix `per_cell` rows, and recompute the aggregate totals. It still passes and produces **TARGET-CHECK OK** in the complete fixture.

   Independently, changing the sampling settings to `fraction=0`, `min_per_shard=1`, `whole_max=0`, `max_per_shard=1` is accepted. Full-mode scope and the sampling policy are not enforced. Merely finding one record labelled `full` does not establish the required prefix replay.

4. **MAJOR — A genuine global control failure still leaves COMPLETE.**  
   **Location:** [write_result.py:975](<repo>/research/unit-distance-23/tools/write_result.py:975), lines 975–1017.

   Give `target_check.evaluate()` 1,920 otherwise passing slice-mode copies, with no full-mode copy. Its genuine output includes:
   ```
   PROBLEM: no counted copy has a full-mode G4 replay...
   TARGET-CHECK FAIL: ...1920...; 0 failing, 0 missing...
   ```
   Feeding that failure through `parse_target()` and `build()` produces **COMPLETE**, control status **open**, and clean lint.

   `bad22` and `badcal` omit global problem lines. The original reproduction—an explicit control problem beside otherwise successful aggregate fields—also still yields COMPLETE. This is affirmative failure, not absent evidence.

5. **MINOR — All-mode self-test fails on the new workers’ valid digest-bearing outputs.**  
   **Location:** [verify_sample.py:375](<repo>/research/unit-distance-23/tools/verify_sample.py:375).

   The “files digest required” control removes exemptions without removing any digest. When every tested output already has its valid digest, this changes nothing. Reproduced: **“not caught,” SELF-TEST FAILED: 13 of 14**, exit 1. The control must actually remove a digest.

I found no final-audit bypass through the new restart/deletion path. A truncated output containing the pass header can be skipped locally, but the judge rejects its missing checker body. Wrong prefix identity and file-digest mismatches are rejected; failed checks retain their directories. The Claude plan contains all 1,920 slices exactly once.

G5 round 13: OPEN (5 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

Findings 1 to 3 (parent coverage, replay details, full-mode scope) are what the fleet audit's checker already does, so
target_check.py no longer re-implements them. It runs the G5-closed verify-chain.py --summary-only, the checker
fleet-audit.py wraps, over every copy, pinned by sha256 to the target, seed level and slicing, with hashes.json and
the G4 replays required. Each of your reproductions was put to that audit on a scratch copy of a real (22,61) slice.
It caught 7 of the 8: emptied parents, children -1, a failed stage, a failed seed, a shrunken full replay, impossible
sampled counts, and a kept count beside an empty keep file. It missed the sampling policy (fraction 0), which
target_check.py now pins itself, with the replay's tool, enum2, forbidden list and seed.
Absence has its own MISSING line; every PROBLEM line, a global one included, is a failure. Finding 4:
write_result.py now treats any PROBLEM line of a control as CONTROL FAILED, with the what-if
control22-global-problem. Finding 5: the judge's digest control now removes a digest.
Self-tests:
- target_check.py: 11 of 11 red controls on the control's real data, each of your reproductions among them;
- verify_sample.py: 15 of 15;
- write_result.py: 114 of 114.
The control now reads 1,625 of 1,920 slices, 0 failing, nothing kept at (22,61).
