# G1 for u(24): the extensions reviewed, closed (2026-10-07)

G1 verdict: CLOSED

The gate, CONTRACT section 4: "**G1** The extensions reviewed: the table extensions (`run-dag2.py`, `prune.py`, the
runbook) and the new checker and worker, each with its tests, and an independent review of the checker's U24 edits and
the worker (codex, read-only), closed."

## What closes it

1. **The reviews of 2026-10-01.** Three read-only Codex rounds covered the checker's U24 edits, the worker and the
   coordinator's receipt audit. They found 7, 6 and 3 defects, fixed in ccfce9dc5f, bd1e5bcc1a and 4e24509f2f
   (`LABNOTES.md`, 2026-10-01). A re-review confirmed the first round's seven closed. The notes planned "a targeted
   verification, not another open-ended review, before the full run" of the later rounds' fixes. That verification was
   not recorded then.
2. **The targeted verification, 2026-10-07.** Codex worked read-only on the code that judged the fleet, which is
   byte-identical to the pilot's base 2b3c4d9dd0. Its rounds and reports are in
   `g1-verification-2026-10-07/verifier/`.
   - **Round 1.** All nine findings of the second and third rounds are CLOSED. Each was shown accepted by the pre-fix
     code and refused now (`verify_history.py`, `history.log`). One new gap was reproduced: the retained level-23
     outputs were not measured independently (`probe_retained.py`).
   - **Fix 1** (a Codex builder, commit 2aba1ff128f): `receipt_audit.measure_retained`, with 15 controls in
     `g1_controls.py`.
   - **Round 2.** That gap is closed. A second was reproduced: a retained stage manifest's `children_written` and
     `children_file_sha256` were not bound when the aggregate export was absent (`round2/probe_full_producer.py`).
   - **Fix 2** (the builder's second round, commit 8a10df49b0d). Every retained stage manifest is now bound to its
     measured level file. The builder also enumerated every content-claiming field of every retained file:
     - 656 field families: 386 bound to a measurement or a derived value, 152 historical claims about deleted files
       with their limits stated, and 118 provenance fields;
     - the table is in `g1-verification-2026-10-07/builder/`;
     - 173 new controls (188 in `g1_controls.py`), each accepted by the round-1 audit and refused here with its exact
       message, with honest receipts accepted after every red.
   - **Round 3.** All findings are closed. 30 randomly sampled bound fields (seed 2026100703) were each refused when
     mutated, at the cited audit line. All 152 historical rows were reviewed, and none should be bound. The verifier's
     verdict is CLOSED, with the stated caveat that sampling is not exhaustive.
3. **The fleet itself, measured outside the audit** (`tools/retained_scan.py`;
   `evidence/retained-scan-2026-10-07.txt` and `-07b.txt`). Every retained level file of all 1,936 judged copies equals:
   - its `hashes.json` entry;
   - every manifest naming it;
   - its prune manifest's counts and its `counts.json` cell;
   - its enumeration stage manifest (rule 5).

   That is 15,488 files, of which 3,872 level files are bound to stage manifests, with 0 problems. So the gaps were
   real in the audit, but no judged copy has such a mismatch.
4. **The fleet re-judged with the final audit** (`evidence/judge-final-2026-10-07-r2/`). All four plans give JUDGE OK
   and the fleet audit is OK. Every key field is identical to the original judge: the stricter audit accepts every copy
   the first one accepted.

## What it does not claim

The historical fields describe intermediate files that are deleted after the check. They rest on the worker's checker
run before deletion, which is the contract's standard ("check before delete"). The audit cannot re-measure them, as the
enumeration table states row by row.
