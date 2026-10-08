# The judged u(24) fleet, re-judged with the G1 round-2 receipt audit (2026-10-07)

The same snapshot as `../judge-final-2026-10-06/` (2026-10-06T19:40:25Z; the 286 branches of `sources.tsv`), judged
again at commit 8a10df49b0d. This is the audit as it stands after G1's two fix rounds: every retained level output
measured, and every retained content claim bound (656 field families enumerated;
`../../g1-verification-2026-10-07/`). `judge.py` sha256 1fa97e93b0d240d2bb4fdc2325905612cece12293e21db2798d9b5e2c5ac1101; `receipt_audit.py` sha256 411258b1c09589716eb2acff98f3a3dceb04e8be6e623fc88bd6c8980be9e9ad.

| step | started (UTC) | finished (UTC) | result |
|---|---|---|---|
| pilot | 2026-10-07T08:26:47Z | 2026-10-07T08:48:23Z | JUDGE OK, 42/42 slices, 44 copies |
| full | 2026-10-07T08:48:23Z | 2026-10-07T10:55:49Z | JUDGE OK, 1,841/1,841 slices, 1,842 copies |
| phase B | 2026-10-07T10:55:49Z | 2026-10-07T11:12:45Z | JUDGE OK, 37/37 slices, 37 copies |
| repro | 2026-10-07T11:12:45Z | 2026-10-07T11:36:03Z | JUDGE OK, 50/50 slices, 100 copies |
| fleet audit | 2026-10-07T11:36:03Z | 2026-10-07T14:13:06Z | OK: 1,923 copies, 1,920 slices, COVERAGE OK, status complete |

These fields are identical to the 2026-10-06 reports in all four plans: verdict, accepted slices and copies, missing,
duplicates, rejected, G4, survivors, resumed slices and rerun disagreements. So the stricter audit accepts every copy
the first audit accepted. These are the judge reports the write-up reads.
