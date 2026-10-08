Delivered [PATCH-2.diff](<repo>/PATCH-2.diff) and [REPORT.md](<repo>/REPORT.md).

Retained stage manifests now bind child counts and hashes directly to measured files, regardless of exports. Missing stage/output pairs fail. Additional checks reconcile retained metadata, prune counters, verification records and receipt duplicates.

- **188 G1 controls pass.** All **173 new controls** are accepted by round-1 code and rejected with exact errors by the patch; honest receipts pass after every red.
- All six runnable existing suites and the updated `retained_scan.py --self-test` pass.
- The table enumerates **656 field families**: 386 checked bindings, 152 historical fields with stated deletion limits, and 118 provenance fields.
- `review_controls.py` remains unavailable because its original raw fixtures are missing.
- The four-file patch applies cleanly to `pristine-r1/` in a dry run.