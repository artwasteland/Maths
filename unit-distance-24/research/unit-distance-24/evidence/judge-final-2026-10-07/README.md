# The judged u(24) fleet, re-judged with the G1-fixed receipt audit (2026-10-07)

The same snapshot as `../judge-final-2026-10-06/` (2026-10-06T19:40:25Z, the 286 branches of `sources.tsv`), judged
again after commit 2aba1ff128f, in which `receipt_audit.py` measures every retained level output itself (the gap the
G1 verification reproduced). `judge.py` sha256 1fa97e93b0d240d2bb4fdc2325905612cece12293e21db2798d9b5e2c5ac1101; `receipt_audit.py` sha256 cf891f8ae2325762f4bea4f5ec5004b336c23c578cae06f2ae2d363a78475a70.

| step | started (UTC) | finished (UTC) | result |
|---|---|---|---|
| pilot | 2026-10-06T23:43:17Z | 2026-10-06T23:50:59Z | JUDGE OK, 42/42 slices, 44 copies |
| full | 2026-10-06T23:50:59Z | 2026-10-07T00:33:29Z | JUDGE OK, 1,841/1,841 slices, 1,842 copies |
| phase B | 2026-10-07T00:33:29Z | 2026-10-07T00:40:27Z | JUDGE OK, 37/37 slices, 37 copies |
| repro | 2026-10-07T00:40:27Z | 2026-10-07T00:49:01Z | JUDGE OK, 50/50 slices, 100 copies |
| fleet audit | 2026-10-07T00:49:01Z | 2026-10-07T01:42:45Z | OK: 1,923 copies, 1,920 slices, COVERAGE OK, status complete |

Compared with the 2026-10-06 reports, these fields are identical in all four plans: verdict, accepted slices and
copies, missing, duplicates, rejected, G4, survivors, resumed slices, rerun disagreements. Commands: as in
`../judge-final-2026-10-06/README.md`, at commit 2aba1ff128f.
