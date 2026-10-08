# Round 3: verify round 2's fix and its enumeration (2026-10-07)

The builder's round 2 is landed at repository commit 8a10df49b0d. Its report is
<repo>/REPORT.md, and its patch PATCH-2.diff. Its baseline, the round-1 audit, is in
<repo>/pristine-r1/. Its enumeration is
<repo>/outputs-r2/field-enumeration-complete.json and field-bindings.json. A fleet re-judge
with the new audit is running now. Its output will be in
<scratch>/scratchpad/u24-rejudge2.log and
u24-rejudge-g1fix2/, finishing about 10:00Z. Read them if they are there when you finish; do not wait.

Same constraints as before. This round is a targeted closure, not another open-ended search:
1. Your round-2 probes, `round2/probe_full_producer.py` (both fields, and the export-removed variant), against the
   current code: rejected? Give the exact messages. `probe_retained.py` (round 1): still rejected?
2. `verify_history.py`, all nine findings: still CLOSED?
3. `g1_controls.py`:
   - against the current code: 188 exact refusals;
   - with `--round2-only` against pristine-r1: the 173 new mutations are accepted.
4. **The enumeration.** Check its completeness claim by sampling, not trust. Take a random sample of at least 25 rows
   marked B, seeded with a published seed. For each, mutate that field in a copy of a fixture and confirm the cited
   audit line rejects it.
   Then read every row marked H, all 152, and confirm each describes content that is deleted after the check, not
   retained content the audit could measure. Name any H row that should be B.
5. **Verdict.** A gap in a historical (deleted-content) field is not a G1 defect. That relation rests on the
   worker's checker run before deletion, as the contract's standard says. Write this round into REPORT.md, and end
   with one line: `G1 verdict: CLOSED` or `G1 verdict: NOT CLOSED: <retained-content claim that is unbound>`.
