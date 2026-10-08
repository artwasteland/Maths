# Round 2: verify the fix (2026-10-07)

The gap you reproduced is fixed in the repository at commit 2aba1ff128f (pushed; working tree at
<repo>, read-only for you as before):
- `research/unit-distance-24/tools/receipt_audit.py`: new `measure_retained` (built by a separate Codex builder in
  <repo>; its REPORT.md and PATCH.diff are there; the pre-fix file is under its `pristine/`);
- `research/unit-distance-24/tools/g1_controls.py`: 15 controls.
The whole judged fleet was re-judged with the fixed audit: `research/unit-distance-24/evidence/judge-final-2026-10-07/`
(all four plans JUDGE OK, fleet audit OK, accepted copies identical to the pre-fix judge). A separate measurement of
every retained level file of every judged copy, outside the audit, is
`research/unit-distance-24/evidence/retained-scan-2026-10-07.txt` (tools/retained_scan.py).

Same constraints as BRIEF.md. Please:
1. Run your `probe_retained.py` against the current repository code: it must now be rejected (give the exact message),
   and the untouched receipts accepted.
2. Re-run `verify_history.py` for all nine findings against the current code (still CLOSED?).
3. Run `g1_controls.py` (patched: 15 exact refusals; against the pristine receipt_audit.py: each accepted).
4. Read the diff. Is there still a way the audit accepts a retained level output (or its metadata) that does not
   match what the enumeration produced? Reproduce anything real.
5. Write your verdict into REPORT.md (append a "Round 2" section), and end the final message with one line:
   `G1 verdict: CLOSED` or `G1 verdict: NOT CLOSED: <what remains>`.
