[REPORT.md](<repo>/REPORT.md) contains fix locations, reproductions, and logs. The repository remained unchanged.

All nine original findings are closed. Each mutation passed before its fix, fails now, and leaves honest receipts accepted. The control suites passed 45 red controls.

Below, `H ID` means `nice -n 15 timeout 1800 /usr/bin/python3 -B verify_history.py ID`, run in this workspace.

| Finding | Verdict | Command |
|---|---|---|
| False target counts | CLOSED | `H R1` |
| Missing prune record | CLOSED | `H R2` |
| Incomplete G4 replay | CLOSED | `H R3` |
| False resumed structure | CLOSED | `H R4` |
| Receipt-selected retention | CLOSED | `H R5` |
| Borrowed slice marker | CLOSED | `H R6` |
| Whole replay downgraded | CLOSED | `H T1` |
| Wrong reach threshold | CLOSED | `H T2` |
| Old marker bypass | CLOSED | `H T3` |

Question 2: **yes**. The current audit and per-copy judge accept an altered `23-64.certs.jsonl` containing **one actual record but zero declared records**, despite its producer manifest binding the original empty file. Reproduce with:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B probe_retained.py
```

This establishes an acceptance gap; completed-fleet corruption has not been established.

**G1: NOT CLOSED — retained level-23 outputs need independent measurement and a passing regression for this reproduced gap.**