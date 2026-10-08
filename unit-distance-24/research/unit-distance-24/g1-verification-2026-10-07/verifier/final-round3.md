Round 3 is complete at commit `8a10df49b0d`. [REPORT.md](<repo>/REPORT.md:101) records current fix locations, commands and evidence.

Each command below follows `nice -n 15 timeout 1800 /usr/bin/python3 -B`:

| Finding | Verdict | Command |
| --- | --- | --- |
| R1: false target count | CLOSED | `verify_history.py R1` |
| R2: missing prune record | CLOSED | `verify_history.py R2` |
| R3: incomplete replay coverage | CLOSED | `verify_history.py R3` |
| R4: compensating shard counts | CLOSED | `verify_history.py R4` |
| R5: omitted retained certificate | CLOSED | `verify_history.py R5` |
| R6: marker borrows another slice’s receipts | CLOSED | `verify_history.py R6` |
| T1: whole replay downgraded | CLOSED | `verify_history.py T1` |
| T2: incorrect reach threshold | CLOSED | `verify_history.py T2` |
| T3: old marker bypasses current audit | CLOSED | `verify_history.py T3` |

Both producer mutations reject with and without the aggregate export:

```text
COUNTS: 23-64.manifest.json children_written: metadata 777 != checked files 0
RECEIPT: 23-64.manifest.json children_file_sha256 differs from checked files
```

The original certificate probe still rejects:

```text
COUNTS: inventory 23-64.certs.jsonl records: metadata 0 != checked files 1
```

All **188 current controls** produced exact refusals; all **173 new mutations** were accepted by the pristine baseline. Honest receipts remained accepted.

Seed **2026100703** selected **30 B rows**; every mutation rejected at a cited audit line. All **152 H rows** were reviewed; none should be B. No reproduced retained-content gap remains within the targeted scope. Sampling is not exhaustive.

The fleet rejudge remains unfinished; I did not wait. The repository stayed read-only.

G1 verdict: CLOSED