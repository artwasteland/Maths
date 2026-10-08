Implemented retained-file hash/count checks and producer-manifest reconciliation.

All 15 new controls reject with exact errors after the fix and are accepted by the original code. Honest receipts pass throughout. Six existing suites passed; `review_controls.py` could not complete because its original raw fixtures are missing.

[REPORT.md](<repo>/REPORT.md) includes commands and results. [PATCH.diff](<repo>/PATCH.diff) contains the two-file unified diff; dry-run application passed.