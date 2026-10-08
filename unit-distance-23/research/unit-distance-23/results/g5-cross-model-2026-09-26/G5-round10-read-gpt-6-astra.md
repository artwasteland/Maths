# G5 round 10: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 10 (u(23), branch claude/answering-alexeev-u22, HEAD 19a455beca; your round 9 closed G5 at 34f0dcb9ba).

Since round 9 the fleet finished and the human chose option 1 for your point 6: a certification sample. Everything
new in the trust chain since then is below; the working tree has it (the G5 side branch is merged). Read the files
themselves. The claim they support is research/unit-distance-23/RESULT-u23.md (a DRAFT, state COMPLETE): the (23,65)
enumeration finds no graph; "if the gates are all green, u(23) = 64".

New since round 9:
1. coordination/cloud-workers/u23-verify.sh: re-runs a sampled slice with the fleet's unchanged runbook and U23_CLEANUP=0,
   then checks its run directory with your round-9 verify-chain.py (pinned by commit and sha256, run as a copy
   verify-chain-g5.py beside the fleet's). A worker's first slice is checked whole (CHAIN OK); a later slice from level
   13 (CHAIN PARTIAL, --from-n 13 its only reason) with its prefix (levels <= 12) compared byte for byte with the first
   slice's run directory, because a later slice's prefix files are hard links whose manifests name the first slice's
   directory, which verify-chain refuses inside another run. U23_VERIFY_WHOLE=0 (used for one worker, v04, run on a
   7.8 GB desktop where the whole check ran out of memory): the first slice is also checked from level 13, and its prefix
   is compared only by hash with the fleet's copies (by verify_sample.py).
2. coordination/cloud-workers/u23-verify-local.sh: that worker's driver, one slice at a time (deleting each later
   slice's run directory after its check passed).
3. research/unit-distance-23/tools/verify_sample.py: the judge. Re-draws the random sample from the registered seed,
   re-derives each check's verdict from its output, compares each re-run's result files with the fleet's copy
   (aggregate_fleet.py's compare_copies, prefix/software/input hashes, the interpreter excepted). Result: 63 of 63.
4. research/unit-distance-23/tools/level22_control.py: CONTRACT 4.3's known-graph control at level 22 (14 of 14).
5. research/unit-distance-23/tools/top_level_check.py: the tamper control now requires a REJECT naming the proof tree.
6. research/unit-distance-23/tools/write_result.py: the G6 generator; its decide() and the states it can give.
7. CONTRACT.md amendment 4 (slicing at level 12) and the u23-verify entry of coordination/cloud-workers/JOBS.md.

Your task: find a fatal objection to the claim as these pieces now support it, one I have not thought of. In
particular: can the level-13 checks plus the prefix comparison leave any certificate-to-keep relation unchecked in a
sampled slice? Can verify_sample.py pass a slice whose re-run or check is wrong? Is a 63-slice sample (15 restarted +
48 random of 1,905) a sound answer to your point 6, and what exactly does it license? Can write_result.py reach
COMPLETE when something is wrong? Is anything the claim rests on still unchecked?

Answer with numbered findings, each with severity (FATAL, MAJOR, MINOR), the file and line, and a concrete failure
scenario. End with exactly one line: "G5 round 10: CLOSED" (no FATAL or MAJOR finding) or "G5 round 10: OPEN (n
findings)". Do not modify any file.

## Final answer, verbatim

I reproduced the recorded 63/63 sample and 14/14 known-graph results. Both top-level checkers accept the genuine certificate and reject its mutation. All reproductions below were read-only.

1. **MAJOR — A failed prefix comparison is recorded as equality.**  
   [u23-verify.sh:158](<repo>/coordination/cloud-workers/u23-verify.sh:158) ignores `prefix_diff`’s exit status and tests only whether stdout is empty. An exception occurs before the helper’s final `print`, leaving empty stdout.

   **Reproduction:** invoking the actual helper with an unavailable first directory produced `status=1 stdout='' accepted=1`. A directory disappearing after lookup, or an I/O error reading a prefix file, therefore becomes “identical, file for file.” The level-13 check cannot supply the omitted prefix certificate-to-keep verification. Require successful comparison execution as well as empty differences.

2. **MAJOR — A genuine check of another slice certifies the requested slice.**  
   [verify_sample.py:102](<repo>/research/unit-distance-23/tools/verify_sample.py:102) checks the wrapper’s identity, but ignores the checker JSON’s `slice`, `target`, `seed_n` and `pinned` fields. Its coverage test merely checks a string prefix.

   **Reproduction:** retain the `v02/s14` wrapper and result copy, but substitute the genuine checker body from `v03/s242`. `evaluate()` still reports **63/63, zero problems**, although that body explicitly says it checked slice 242. Bind the checker’s identity and checked-file fingerprint to the result copy being certified.

3. **MAJOR — The sample can pass without any fully checked prefix.**  
   [verify_sample.py:107](<repo>/research/unit-distance-23/tools/verify_sample.py:107) permits every worker’s first slice to declare “whole check skipped”; [line 192](<repo>/research/unit-distance-23/tools/verify_sample.py:192) counts whole checks without requiring one.

   **Reproduction:** make every first-slice output consistently describe the supported `U23_VERIFY_WHOLE=0` mode. The judge reports **63/63, zero problems, zero whole checks**, and G6 returns `COMPLETE`. Identical prefix hashes then establish agreement without establishing the prefix’s pruning correctness. Require a whole-checked reference for every shared prefix hash. The present nine whole checks avoid this particular scenario, assuming their evidence is correctly bound.

4. **MAJOR — G6 declares COMPLETE after the certification sample fails for missing evidence.**  
   [write_result.py:781](<repo>/research/unit-distance-23/tools/write_result.py:781) expressly exempts missing outputs/copies and does not require the sample’s successful exit or complete verification.

   **Reproduction:** leave only `v01/s276` available in the in-memory sample collection. The judge returns **exit 1, VERIFY-SAMPLE FAIL, 1/63 verified, 124 problems**. Passing that genuine output through `parse_vs()` and `decide()` nevertheless produces **COMPLETE**, no failing checks, and “The enumeration finds no (23,65) unit-distance graph.” Require every planned slice verified before treating this certification requirement as satisfied.

The level-13 boundary itself is sound **when comparison succeeds and reaches a correctly bound, whole-checked prefix**; the verifier also recomputes the level-12 slicing.

The sample provides corroboration, not exhaustive closure of point 6. A single faulty slice among the other 1,905 escapes the 48-slice draw with probability **1,857/1,905 ≈ 97.48%**, assuming uniform sampling independent of fault locations. It licenses findings about the checked reruns; the remaining slices still depend on trusted production checks. Exhaustive independent certification requires auditing or regenerating those remaining slices.

G5 round 10: OPEN (4 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

All four findings are about the checking instruments; none says the enumeration is wrong. Each is fixed, and each fix
has a red control that fails on purpose.

1. **Prefix comparison.** `coordination/cloud-workers/u23-verify.sh` (commit e29124767c). `prefix_diff` now prints a
   positive `identical, file for file (N files)` and exits 1 on any difference. The caller needs exit 0 and that line;
   the header prints what it got, or `NO RESULT` when empty. Red-tested on a (17,43) run: with one prefix file made
   unreadable, the check now fails (exit 7, `the comparison did not succeed (exit 1): Traceback ...`). With the file
   restored it passes again.
2. **Binding a check to its slice.** `research/unit-distance-23/tools/verify_sample.py` now requires the checker's
   own JSON record to be of this slice: `slice == [12, i, 1920]`, target, seed, the pinned block, and the run
   directory's name, both in the record and in the header. A whole check's COVERAGE line must name the slice.
   `u23-verify.sh` also records a digest of the run directory's level files, under the runbook's `hashes.json` rule.
   The judge recomputes that digest from the slice's result copy and requires equality. It was checked equal on a
   real run: 110 files, the same sha256 on both sides. Outputs made before the digest existed (the sample's, and
   codex wave 0's commit f197cd5867) are exempt only by that explicit list.
   Red controls: your substitution (s14's genuine check under s276's header) is caught; so are a changed digest and a
   missing one.
3. **Prefixes without a whole check.** The judge now keeps the prefix hashes of the slices that passed a whole check.
   Every verified slice's prefix, taken from its copy's hashes, must be one of them, and at least one whole check must
   pass. Red control: every first slice declaring its whole check skipped now gives `no slice passed a whole check`.
   The real sample still verifies 63 of 63, and its prefixes are all one prefix, checked whole 9 times.
4. **COMPLETE despite missing slices.** `write_result.py` now needs all of these for the certification sample: the
   judge's verdict OK, its exit status 0, every planned slice verified, no problem, and the per-slice lines adding up.
   A slice with only its output or copy missing now makes the draft INCOMPLETE. New what-ifs:
   - `sample-mostly-missing` (your reproduction, 1 of 63): INCOMPLETE;
   - `sample-no-exit`: INCOMPLETE;
   - `sample-partial`: now INCOMPLETE, where before it was COMPLETE.

Also since this read:
- the full re-run of all 1,920 slices is under way on codex cloud (`u23-verify-all`), because a 48-slice sample leaves a
  single faulty slice undetected with probability about 97%, as you say;
- a blind second verifier, written by a different model from the format and the mathematics alone, accepts slice 50's
  top-level certificate (`research/unit-distance-23/blind-verifier/`). `write_result.py` now requires it, with seven
  tampered copies of each certificate rejected, before a draft can be COMPLETE.

Self-tests: `verify_sample.py --self-test` 12 of 12 red controls caught; `write_result.py --self-test` 51 of 51.
