# G5 round 12: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 12 (u(23), branch claude/answering-alexeev-u22, HEAD 843ba9e80f). Your round 11 was OPEN (three MAJOR, one
MINOR). The response is research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round11-read-gpt-6-astra.md
("Response"); the fixes are in 843ba9e80f. Read the files themselves: research/unit-distance-23/tools/verify_sample.py,
research/unit-distance-23/tools/blind_check.py, research/unit-distance-23/tools/write_result.py (its decide(), the
new gate evidence: target_check.py for CONTRACT 4.1 and 4.3, verify_sample.py --all for the full re-run),
research/unit-distance-23/tools/target_check.py and research/unit-distance-23/results/u23/verify-sample-outputs.json.

Your task:
- Check each round-11 finding against its fix: is your reproduction now caught, and does the fix open a new hole?
- Attack target_check.py (it will judge the (22,61) control and the (21,57) calibration over all 1,920 slices each):
  can it say OK when a slice is missing, was run with other options, failed its G4 replay, or when the top level
  keeps a graph (the control) or loses a known graph (the calibration)?
- Attack the way write_result.py uses the three new pieces of evidence: can a failed control, calibration or full
  re-run leave the state COMPLETE, or can an open one read as met?
- Anything the claim still rests on that is unchecked.

Work read-only: reproduce with in-memory edits of parsed data, as before. Answer with numbered findings, each with its
severity (FATAL, MAJOR, MINOR), the file and line, and a concrete failure scenario. End with exactly one line:
"G5 round 12: CLOSED" if there is no FATAL or MAJOR finding, otherwise "G5 round 12: OPEN (n findings)". Do not
modify any file.

## Final answer, verbatim

Reviewed `843ba9e80f`; no files modified. All reproductions used memory only.

The round-11 reproductions are resolved:

| Finding | Closure evidence |
|---|---|
| Legacy digest failure | **CLOSED:** `verify_sample.py:139–148` rejects altered sample outputs, failed digest calculations and wrapper FAIL. |
| Blind verification of another graph | **CLOSED:** `blind_check.py:142` records identities; `write_result.py:868–872` requires exact graph/certificate matches. Substitutions now give `TOP LEVEL NOT DECIDED`. |
| Approved driver rejected | **CLOSED:** `verify_sample.py:178–186`. The real pilot now passes in all-slices mode. |
| All-mode seed crash | **CLOSED:** `verify_sample.py:391–396` avoids the seed access. Its replacement control has the MINOR defect below. |

The genuine sample passes 63/63; existing self-tests pass 15/15 and 86/86. Nevertheless:

1. **MAJOR — One slice can masquerade as the entire control fleet.**  
   **Locations:** [target_check.py:72](<repo>/research/unit-distance-23/tools/target_check.py:72), lines 108–137.

   The checker validates the summary’s slice label but ignores the config’s target/slice and the required-cell coverage.

   **Reproduction:** I presented the real `k01-fpscz3/s0of1920` files under 1,920 virtual directory names, changing only each `run-summary.json` slice label. Every config still named slice zero. The result was:

   `TARGET-CHECK OK: (22,61): 1920 of 1920 slices complete, G4 PASS 1920`

   Separately, deleting all `levels`, `windows` and reach information from one summary still passes, including the five red controls. Required-cell and slice-partition validation must accompany the labels.

2. **MAJOR — G4 PASS does not require valid replay evidence.**  
   **Location:** [target_check.py:77](<repo>/research/unit-distance-23/tools/target_check.py:77), lines 77–84.

   **Reproduction:** replacing one replay summary with just `{"processed_parents":1}` yields PASS. Changing a real replay’s `per_cell[0].mismatches` to `1`, or making aggregate production and replay child counts disagree, also yields PASS.

   In an otherwise passing 1,920-entry fixture, the minimal bogus replay produces `TARGET-CHECK OK`, passes all five red controls, and makes G6 mark the tree control satisfied. Replay details, identities and aggregates need reconciliation.

3. **MAJOR — G6 accepts evidence for different control requirements.**  
   **Locations:** [write_result.py:450](<repo>/research/unit-distance-23/tools/write_result.py:450), lines 963–978; `target_check.py:154–161`.

   **Reproductions using successful outputs from the actual target-check functions:**

   - A control evaluated with root minimum degree **6** is accepted by G6 as the required degree-**5** control.
   - A calibration containing only four required graphs, checked against a four-graph `known` list, reports **4/4**. G6 marks it **“all kept”**, despite the fifth contractual graph being absent. Checking the same fixture against the genuine five-graph list correctly fails.

   Both leave `COMPLETE`, with clean lint. G6 ignores the parsed target and does not bind the evidence to the required options or known-file identity.

4. **MAJOR — Actual failures can remain COMPLETE or even read as satisfied.**  
   **Location:** [write_result.py:963](<repo>/research/unit-distance-23/tools/write_result.py:963), lines 963–989.

   **Reproduction:** change one otherwise complete control copy’s replay to FAILED. The genuine target-check output reports the failure and **1919/1920** passing slices. G6 nevertheless produces **COMPLETE**, classifying the failed control as merely **open**. Failed control self-tests likewise leave COMPLETE.

   Additionally, adding an explicit mismatch to otherwise successful parsed `VERIFY-ALL` evidence still produces **COMPLETE / all verified**: `okva` ignores `failed_problems`. The target-control success predicates similarly ignore their problem lists.

   Missing evidence and affirmative failure need distinct treatment; a success summary must not override recorded problems.

5. **MINOR — The replacement all-mode red control does not remove a singleton slice.**  
   **Location:** [verify_sample.py:392](<repo>/research/unit-distance-23/tools/verify_sample.py:392).

   The actual first task is `c001: [344]`. Applying `wk[t0][:-1] or wk[t0]` leaves `[344]` unchanged. Reproduced: **“a slice dropped from the plan: not caught.”** The seed crash is fixed, but this replacement test is ineffective.

G5 round 12: OPEN (5 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

Fixed in 228be7e3d8 (target_check.py rewritten to bind every copy and rebuild G4 from its evidence; write_result.py
binding each control to the contract's parameters and treating a recorded failure as failure). Round 13 read those
fixes; see its record.
