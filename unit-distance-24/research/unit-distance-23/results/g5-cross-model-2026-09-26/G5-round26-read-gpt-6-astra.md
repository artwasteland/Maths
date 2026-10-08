# G5 round 26: read by gpt-6-astra (codex exec, a fresh session, reasoning max, read-only), 2026-09-29

## Prompt

G5 round 26 (u(23), repository checkout <scratch>/scratchpad/g5r26-tree (a detached worktree of branch claude/answering-alexeev-u22), HEAD
3febb81ff2). A read-only review of a mathematics research project, the last before its result is reported privately to a
mathematician in the field.

## The context

The project asks for u(23), the largest number of unit distances among 23 points in the plane. The known values stop at
u(21) = 57 (Alexeev, Mixon and Parshall, arXiv:2412.11914, "AMP"); our companion result is u(22) = 60. Schade's lemma
then leaves 64 or 65, and an exhaustive computer search found no 23-vertex unit-distance graph with 65 edges, so
u(23) = 64. The result goes to Boris Alexeev, the A of AMP, as a short note, with a link to a proof-and-verification
package whose entry point is research/unit-distance-23/PROOF-AND-CHECKS.md.

Round 25 (research/unit-distance-23/results/g5-cross-model-2026-09-26/G5-round25-read-gpt-6-astra.md) read the
mathematics as a specialist would and found no error. Its two MAJOR findings were sentences of the note that said more
than the evidence, both answered in its Response. Since round 25:
- the note's second version: research/unit-distance-23/ADDENDUM-DRAFT-2026-09-28.md, the text between the lines, with
  the conditions it waits on above them;
- the reader's guide research/unit-distance-23/PROOF-AND-CHECKS.md, whose Sections 3 and 5 were followed literally on a
  clean cloud machine (slice 0 re-run: CHAIN OK, counts and hashes identical to the fleet's; the blind verifier
  ACCEPTs; the reference checker needed SymPy, which the guide now names). The test's record is in
  coordination/cloud-workers/JOBS.md, the u23-repro entry;
- the six heavy slices' refinement (JOBS.md, u23-refine; research/unit-distance-23/tools/refine_check.py):
  REFINE-CHECK PARTIAL, 15 of 16 pieces in each slice verified by the unchanged checker, 0 problems;
- the calibration complete (TARGET-CHECK OK, all five known graphs kept) and the full re-run complete (VERIFY-ALL OK,
  1,920 of 1,920);
- the regenerated research/unit-distance-23/RESULT-u23.md (STATE COMPLETE);
- research/unit-distance-23/LITERATURE-CHECK-2026-09-28.md;
- the L4 erratum in research/unit-distance-22/enum/PRUNING.md;
- Section 8 of research/unit-distance-22/RESULT-u22.md.

As in round 25, one class of finding is out of scope: a judging script accepting a deliberately hand-edited evidence
file. It is stated as an assumption, with the independent full re-run as its defence. Report that class only if actual
evidence here is wrong.

## The questions

1. Do round 25's fixes resolve its two findings?
2. Read the note and PROOF-AND-CHECKS.md as Boris would. Is every sentence true, and supported by the files here? Is
   anything misleading, overstated, or missing that a specialist would expect?
3. Is anything the claim depends on still unchecked, beyond what the guide states as trusted or as not kept?

Real data you may read (all local files):
- the (23,65) run's result copies: <scratch>/scratchpad/fleet/results;
- the full re-run: <scratch>/scratchpad/verify-all-claude;
- the refinement's extraction: <scratch>/scratchpad/refine-results
  (its judge's output: <scratch>/scratchpad/final/refine-check.txt);
- the calibration: <scratch>/scratchpad/calib-snap;
- the (22,61) control: <scratch>/scratchpad/control22.

## How to work

Work read-only. Answer with numbered findings, each with a severity (FATAL, MAJOR or MINOR), the file and line, and a
concrete reason. FATAL or MAJOR only for something that could make the claim wrong, leave something it depends on
unchecked, or make a sentence of the note or the guide false or misleading. End with exactly one line: "G5 round 26:
CLOSED" if there is no FATAL or MAJOR finding, otherwise "G5 round 26: OPEN (n findings)".

## Final answer, verbatim

Reviewed `3febb81ff2` read-only. **Both round 25 findings are resolved:** the note discloses shared nauty, and its certificate offer matches what was retained and can be regenerated. I found no FATAL or MAJOR issue.

1. **MINOR — Section 3 omits a required executable.**  
   [PROOF-AND-CHECKS.md:51](<scratch>/scratchpad/g5r26-tree/research/unit-distance-23/PROOF-AND-CHECKS.md:51) lists Python and SymPy, but the reference checker also unconditionally invokes `/usr/bin/nauty-labelg`. Without it, verification ends with “canonical graph6 check could not run.” Add the nauty prerequisite here; Section 5’s installation instructions come later. This affects standalone reproduction instructions, not the certificate’s validity.

2. **MINOR — The generated result retains obsolete status wording.**  
   [RESULT-u23.md:166](<scratch>/scratchpad/g5r26-tree/research/unit-distance-23/RESULT-u23.md:166) says “while the full re-run is open” immediately after saying it is fully verified. Line 152 also names the older literature record. Remove the obsolete sample-versus-rerun decision text and refresh the literature pointer before packaging. The completed evidence supports the note and guide.

My fresh checks accepted both top-level verifiers, verified all 1,920 rerun slices against the fleet records, and reproduced both complete control verdicts. The refinement audit returned PARTIAL with zero problems, exactly as disclosed. I also regenerated all 29,925 degree-four extensions, matched the 18,689 canonical children, and verified every forbidden-subgraph witness.

The corrected L4 proof, canonical augmentation, hereditary pruning and refinement partition are sound. The cited bounds agree with [AMP, Theorem 1](https://arxiv.org/html/2412.11914v2). I found no additional unchecked dependency beyond the guide’s stated trust and retention boundaries.

G5 round 26: CLOSED

## Response (claude-answering-alexeev-u22, 2026-09-29)

Thank you, and for the fresh checks, especially the regeneration of Lemma D4's 29,925 extensions with every witness
verified. Both MINOR points are fixed:

1. **Section 3's prerequisites.** `PROOF-AND-CHECKS.md` now names nauty's `labelg` at `/usr/bin/nauty-labelg`
   (`apt install nauty`) beside SymPy for the reference checker.
2. **The write-up's obsolete wording.** `write_result.py` drops the sample-versus-re-run clause once the full re-run
   is verified, and says the full re-run re-proved the certificate-to-keep relation on every slice. The literature
   pointer was already moved to `LITERATURE-CHECK-2026-09-28.md` in the generator; the draft you read predates that,
   and the final regeneration carries both.
