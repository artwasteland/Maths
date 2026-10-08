# G5: the cross-model read, and every finding answered

CONTRACT gate G5 asks for "a cross-model read of PROOFS.md and of the checker's soundness branches (Kimi, via
waste-drop, maths-only bundle) with every finding answered in writing". The read is waste-drop task 0018 (hostile
referee of the GP-10 proof checker), answered by Arturo (Kimi k3, a non-Claude model family) on 2026-09-24 as
waste-drop PR #8, branch `result/0018-proofs-gp10-soundness-v2` (REPORT.md plus four strand papers A-D).

**Verdict received:** the checker is sound; no BLOCKER, no MAJOR; five MINORs, none exploitable, each with a stated
fix. The seven points the authors flagged as least sure were each adjudicated sound; all sixteen contract red
fixtures reject; a hand-derived K4 R-null witness (28 terms) is accepted, so the refutation branches are live, not
merely fail-closed; 79 adversarial checker invocations found no false accept.

**Checker freeze.** The B10 gate (G3) runs on checker sha256 `d717816bde784fae…`, the version Arturo read. None of
the findings changes what the checker accepts, so the result is certified under that version and no code change is
made before G3. Code fixes below are queued for a v2 checker; they would require re-running every control and the B10
run under the new hash before any claim cites v2.

## The five MINORs

**MINOR-1. E-exact distinctness: contract wording vs implementation.** Agreed. CONTRACT 3.1 step (3) says each
distinctness polynomial must be bounded away from 0 "over the whole of [lo, hi]"; the checker bisects and accepts
once the enclosure on the current subinterval, which still contains the certified root, excludes 0. As the referee
shows, this is sound for acceptance (the exhibited root lies in the final subinterval, edges vanish at every root of
the minimal polynomial, and a genuine collision at an in-interval root exhausts the bisection budget and rejects).
Action: the contract sentence is amended to describe the implemented semantics (Amendment 6, wording only, below).
No certificate's status changes.

**MINOR-2. `block_evidence` checks against the full F9 list even when a run's forbidden limit is lower.** Agreed,
and conservative: it can only reject more. It cannot affect the B10 run, which uses limit 9. Queued for v2 (thread
the run's limit through); documented here meanwhile.

**MINOR-3. `minimality_claim_refuted_deletion` appears unreachable.** Agreed that no construction the referee tried
reaches it (the earlier `block_forbidden` / `minimality_not_free` checks preempt it). It is a defensive assertion,
not an acceptance path. Queued for v2: either delete it or add the fault-injection fixture that reaches it.

**MINOR-4. `serialize_polynomial` emits flint integers that the strict parser rejects.** Agreed (check/gp10check.py
line 370). The serializer is not on any acceptance path; it only matters to a producer echoing the checker's own
canonical output back. Queued for v2 (coerce exponents to `int`).

**MINOR-5. The R-tree moves L0, L1a, L1b, L2 rest on a citation (AMP, Section 4) rather than in-bundle proofs.**
Agreed. L1c and L3 are proved in the kernel's PROOFS.md and the referee re-derived L3 independently; the other four
moves were validated behaviourally (valid trees accepted; tampered discriminants and swapped children rejected; the
L0 rhombus initialisation checked over every cyclic order, crossed 4-cycles included). Action: PROOFS.md now pins
the citation (Alexeev, Mixon, Parshall, arXiv:2412.11914, Section 4) at the point of use. Inlining the four short
proofs is queued with the v2 work. We do not re-host the paper (arXiv's licence is the authors' to grant).

## The NOTEs

- **Python's 4,300-digit integer limit.** A certificate with a larger integer would make the checker exit with
  `checker_error`: fail-closed, but a false negative. Checked before G3: no record in the final assembly (lean3)
  contains a run of even 4,000 digits, so this cannot affect the B10 run. Queued for v2
  (`sys.set_int_max_str_digits(0)` at start-up, with a control that exercises it).
- **`FREEZE.txt` is named in CONTRACT Section 9 but never checked by the code.** Agreed; the environment is recorded
  in each report's `environment` field (python, sympy, flint versions, executable) instead. Amendment 6 says so.
- **K_{2,3} cannot be refuted by R-null** (its complex variety is non-empty; the obstruction is real). Agreed and
  consistent with our runs: the regression control refutes K_{2,3} by R-tree. Added to the producer notes in
  Amendment 6.
- **Lenient accepts** (leading-zero rationals, zero coefficients in non-canonical sparse encodings, unused sat pairs):
  the referee judged them contract-conformant and sound; we agree and change nothing.
- **Uncaught arithmetic exceptions escape without writing ACCEPT.** Fail-closed; queued for v2 as a tidy-up (catch,
  report as `checker_error` with the record named).
- **Bundle layout** (kernel directory name, missing `forbidden-74.json`). A packaging gap in our task bundle, not a
  checker defect; the referee rebuilt the layout and verified `forbidden-74.json` independently (74 graphs,
  distribution 1/1/1/3/13/55 on n = 4..9, matching GP's Appendix A). Future bundles will ship the research-tree
  layout.
- **The u(22) kernel's own build REPORT was not in the bundle.** The referee substituted an independent battery
  (15 of 15 mutations rejected, 6 of 6 valid witnesses accepted). Noted; future bundles will include it.

## Amendment 6 (wording only; no acceptance behaviour changes)

1. CONTRACT 3.1 step (3), E-exact distinctness: "bounded away from 0 over the whole of [lo, hi]" is replaced by
   "bounded away from 0 on a subinterval of [lo, hi] that still contains the certified root, reached by bisection
   that keeps a sign change; the checker rejects if its bisection budget is exhausted first".
2. CONTRACT Section 9: the environment of a run is the `environment` field of its report (interpreter, SymPy and
   python-flint versions, executable path); `FREEZE.txt` is the producers' record, not a checker input.
3. Producer note: K_{2,3}-type obstructions are real, not complex; route them through R-real, real-dag or R-tree.
