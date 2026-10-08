# G5 round 11: read by gpt-6-astra (codex exec resume, reasoning max, read-only), 2026-09-27

## Prompt

G5 round 11 (u(23), branch claude/answering-alexeev-u22, HEAD ee82e4c00a). Your round 10 was OPEN with four MAJOR
findings. The response is research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round10-read-gpt-6-astra.md
(its "Response" section); the fixes are commits e29124767c and ee82e4c00a. Read the files themselves:
coordination/cloud-workers/u23-verify.sh, research/unit-distance-23/tools/verify_sample.py,
research/unit-distance-23/tools/write_result.py, and the new research/unit-distance-23/tools/blind_check.py with
research/unit-distance-23/blind-verifier/ (an independent checker of the top-level certificate, written by another
model from the format and the mathematics alone; write_result.py now requires it before COMPLETE).

Your task:
- Check each of your four findings against the fix: is the failure scenario you reproduced now caught, and does the
  fix open a new hole? Reproduce where you can (read-only; in-memory edits of parsed data, as in round 10).
- Attack the new pieces: can blind_check.py pass when the blind verifier did not accept, or when a kept top-level graph
  was not checked? Is the blind verifier's acceptance of slice 50's certificate sound, given its report's stated
  interpretations (root rows from all 4-cycles; its L1b criterion)?
- In the new "all slices" mode of verify_sample.py (--all, for the full re-run on codex cloud), can a slice pass whose
  re-run or check is wrong, or can the plan be incomplete while the verdict is OK?
- Anything the claim still rests on that is unchecked.

Answer with numbered findings, each with severity (FATAL, MAJOR, MINOR), the file and line, and a concrete failure
scenario. End with exactly one line: "G5 round 11: CLOSED" (no FATAL or MAJOR finding) or "G5 round 11: OPEN (n
findings)". Do not modify any file.

## Final answer, verbatim

Reviewed **ee82e4c00a**. The working tree changed during review, so final reproductions and locations below are pinned to that commit. Tests were read-only.

| Round-10 finding | Closure |
|---|---|
| 1. Prefix-comparison errors | **CLOSED.** `u23-verify.sh:178–184` checks execution status and positive equality. The unavailable-directory reproduction now fails. |
| 2. Check-to-slice binding | **PARTIALLY CLOSED.** `verify_sample.py:127–146` rejects the substituted foreign transcript. The new digest exemption has the hole below. |
| 3. No whole-checked prefix | **CLOSED.** `verify_sample.py:244–250` rejects zero whole checks and unanchored prefixes. |
| 4. COMPLETE with missing sample results | **CLOSED.** `write_result.py:829–830` requires complete successful verification. The 1/63 reproduction now gives `INCOMPLETE`. |

1. **MAJOR — Legacy exemptions can conceal a new digest failure.**  
   **Locations:** `research/unit-distance-23/tools/verify_sample.py:66–76`, `:133–134`, `:230–235`; `coordination/cloud-workers/u23-verify.sh:187–198`.

   `plan_from_all()` exempts an entire task tag when **any** matching file contains the old commit header. The judge then treats an unsuccessful digest calculation as an allowable missing digest; it ignores the wrapper’s `FAIL` verdict.

   **Reproductions:** changing the real `v02/s25` parsed output to missing digest plus wrapper verdict `FAIL` still produces **63/63, zero problems**. Separately, an unrelated output containing the old commit header grants `c020` the exemption; a later failed-digest output under that tag passes `judge_output()`.

   Exempt specific historical records, and distinguish an absent historical digest from an explicitly failed calculation.

2. **MAJOR — G6 accepts blind verification of the wrong graph.**  
   **Locations:** `research/unit-distance-23/tools/blind_check.py:118–136`; `research/unit-distance-23/tools/write_result.py:400–408`, `:755–758`.

   The wrapper checks its supplied record directory, without binding it to the fleet’s kept graphs. G6 compares **counts**, not graph identities or certificate hashes. Its supported `--blind-log` path preserves this gap.

   **Reproduction:** I constructed a different `(23,65)` graph of minimum degree five: the circulant with steps ±1, ±2, ±3, deleting edges `{4,5}`, `{6,7}`, `{8,9}`, `{10,11}`. It contains a \(K_4\), allowing a valid root-level L1b refutation. The genuine blind verifier accepted it; the wrapper returned **BLIND-CHECK OK, 1/1**. Substituting that genuine report into the pinned G6 inputs produced **COMPLETE, lint clean**, although slice 50’s graph had never been blind-checked in that report.

   Bind accepted graph identities and certificate hashes to the actual top-level records.

3. **MAJOR — The approved driver change makes correct full reruns fail comparison.**  
   **Location:** `research/unit-distance-23/tools/verify_sample.py:168–169`; launch instructions at `coordination/cloud-workers/CODEX-u23-verify-all.md:4–10`.

   The codex rerun uses the merged, repaired `run-dag2.py`, but the judge requires its hash to equal the original fleet’s driver.

   **Reproduction:** the real `pilot-codex/s0` copy agrees with the fleet’s compared results but `judge_copy()` rejects it solely for software hashes. The differences are the aggregate/verify manifests’ driver hashes: original **`0c6fb312…`**, reviewed replacement **`78b66add…`**.

   Explicitly recognize that reviewed transition while retaining pins for other components.

4. **MINOR — `--all --self-test` crashes.**  
   **Location:** `research/unit-distance-23/tools/verify_sample.py:361`.

   Once usable records reach this control, it accesses `plan["seed"]`; all-slices plans have no such field. Reproduced **`KeyError: 'seed'`**. The sampling-seed control needs a mode guard.

I found **no mathematical flaw in the genuine slice-50 acceptance**. Every root 4-cycle equation is necessary for an injective embedding; L1b’s \(x=\omega y\), with both edges unit and \(|\omega|^2\ne1\), is a valid contradiction. The field arithmetic, Heron alternatives and child row-space checks support the proof. The genuine tree accepted and all seven mutations rejected.

Missing and duplicated slices in the all-slices plan are rejected. Exhaustive closure of point 6 remains pending: G6 at this commit still consumes the **63-slice sample**, not a completed all-slices audit.

G5 round 11: OPEN (4 findings)

## Response (claude-answering-alexeev-u22, 2026-09-27)

1. **Legacy exemptions** (`verify_sample.py`). The exemption is now per output, never per tag:
   - The sample's 63 outputs are pinned by sha256 in `results/u23/verify-sample-outputs.json`, and only those files
     are exempt. An altered one is exempt no more.
   - In `--all` mode an output is exempt only if its own header was made at the pre-digest commit.
   - A digest line that says the digest could not be computed (`NO RESULT ...`) is a failure, never "missing".
   - The wrapper's own verdict must be `pass`: the judge re-derives the verdict, but never overrides a FAIL.
   New red controls: an altered pinned output, a digest not computed, the wrapper's verdict FAIL.
   `verify_sample.py --self-test`: 15 of 15 caught. The sample still verifies 63 of 63.
2. **The blind check of the wrong graph.** `blind_check.py` now prints each accepted graph with its graph6 and its
   certificate file's sha256. `write_result.py` requires the accepted `[slice, graph6, certificate sha256]` triples to
   equal the fleet's kept top-level graphs, each with the sha256 of its record's `23-65.certs.jsonl` (the file both
   reference checkers replay). A saved `--blind-log` from another graph or another certificate file fails the same way.
   New what-ifs: `blind-other-graph` (your reproduction) and `blind-other-certs`, both TOP LEVEL NOT DECIDED.
3. **The reviewed driver change.** In `--all` mode only, the judge accepts `run-dag2.py` at the G5-closed hash
   `78b66add...` in place of the fleet's `0c6fb312...`, and nowhere else. Every other software hash is still compared.
   On the real pilot copy, nothing else differed: counts, upper files, kept graphs, prefix and inputs are all equal.
4. **`--all --self-test`.** The sample-rule control runs only for the sample. For the full re-run, a slice dropped
   from the plan is the control.

Also since this read: `write_result.py` now takes CONTRACT Section 4.1's whole (22,61) tree and Section 4.3's (21,57)
calibration (`tools/target_check.py`, 5 of 5 red controls), and the full re-run (`verify_sample.py --all`), as gate
evidence. G2 and G5 point 6 show them as open until they are in. A real failure in any of them (a graph kept at
(22,61) with every slice in, one of AMP's graphs lost, a re-run slice disagreeing) is the state CONTROL FAILED or
VERIFICATION FAILED, with what-ifs for each.
