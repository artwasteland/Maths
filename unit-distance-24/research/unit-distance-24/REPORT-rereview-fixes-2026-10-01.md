**u(24) rereview fixes — 2026-10-01**

Base: `ccfce9dc5f0eb83229f703bedb5fcd3b0ae98f4a`, detached worktree.
All six findings in the rereview's final report are addressed. I agree with all six.
No Git command changed state. The three protected chain checkers, their pins, the u(23) fleet judge and `u23-slice.sh` are unchanged.
No enumeration or G4 enumeration replay was started. `tools/red_controls.py` was not run.

Evidence and logs are in `/tmp/u24-rereview-fixes-xJ9521/`.
The new [rereview_controls.py](tools/rereview_controls.py) reproduces the reviewer's mutations, including refreshed structure/inventory envelope hashes. It also refreshes retained metadata hashes when the mutation changes those files. Checker output, graph bytes and graph hashes remain intact. Each rejection asserts the exact semantic error below and is followed by acceptance of the original receipts. `controls-final/rereview-controls.json` records all 26 controls; `controls-final.log` includes every red and green result.

1. **Incorrect survivor counts.** [receipt_audit.py](tools/receipt_audit.py), lines 25–71, 91–173 and 325–367, requires typed, unique inventory rows and independently measures the retained target files. The target reach input is reconstructed in order from certificate `g6` records because the copy policy does not retain `.reach.g6`. Certificate verdicts give prune counts and bind keep/UNKNOWN content. Raw and exported summaries, `hashes.json`, `counts.json`, target counts and file-count rows are reconciled with measured content. The returned target-file records, and therefore the CLI's survivor figure, are measurements.

   The three original mutations produce:

   ```text
   COUNTS: inventory 24-69.keep.g6 records: metadata 777 != checked files 0
   COUNTS: 24-69 children: metadata 777 != checked files 0
   RECEIPT: required inventory row missing: 24-69.keep.g6
   ```

   An independent hashes-only mutation also fails:

   ```text
   COUNTS: hashes.json 24-69.keep.g6 records: metadata 777 != checked files 0
   ```

2. **Missing required prune record.** [evidence.py](tools/evidence.py), lines 30–59 and 300–312, calls the unchanged checker's `derive()` to establish the required cells from the configuration and reach table. Each cell must have its prescribed kind and reach, prune and verification records. Both worker reconciliation and receipt auditing apply this requirement before examining counts. Missing reach/verification records and an omitted required cell have separate controls too.

   ```text
   RECORDS: 20-49: required prune record is missing
   ```

   The actual `worker_omission.py` scenario was repeated with real checker and known-graph execution, in a scratch hardlinked copy of slice 1444. The worker exited 7, retained the run and wrote no checked marker. Its checker still returned the expected passing partial verdict; the new evidence rule independently refused:

   ```text
   REREVIEW WORKER red: EVIDENCE FAIL: RECORDS: 20-49: required prune record is missing
   ```

   Restoring only the original summary record and its result metadata yielded worker exit 0 and a passing receipt audit. See `real-worker.log`; the new suite exposes this integration test through `--worker`.

3. **Incomplete G4 replay.** [evidence.py](tools/evidence.py), lines 378–435 and 438–481, requires exactly the populated cells in the replay's scope. It invokes the existing u(23) judge's `replay_scope()` and pinned `policy_sample()`/`sample_indices()` logic using the checked structural evidence and the recorded sampling settings at fraction 0.002. This also checks seed, stage and replay-control coverage. The coordinator reconstructs the structural inputs before invoking the same check.

   The reviewer's one-of-41 replay, with its aggregates recomputed, fails at both worker and receipt audit:

   ```text
   G4: replay cells differ: expected 41 populated cells, got 1; missing ['11-17', '11-18', '11-19'], extra []
   ```

   Retaining every cell but lowering a prescribed sample independently fails:

   ```text
   G4 SCOPE: a full G4 replay whose row of 11-17 has parents 31127, sampled 62 over 4 shards, for 31127 audited parents in 4 shards (the policy samples 63)
   ```

4. **Unverified resumed structure.** [receipt_audit.py](tools/receipt_audit.py), lines 176–241, hashes preserved manifest text against required inventory rows, requires every resumed aggregate/shard manifest, and uses [evidence.py](tools/evidence.py), lines 206–275, to reconstruct sources, parent counts, ranges and child counts. The exported fields must equal that reconstruction. Sources also must match the reach table's allowed parent cells and the measured stage files. Existing summary fields are reconciled too. New receipts preserve all checked augmentation manifests; honest old receipts still work with their resumed manifests and measured inventories.

   The original compensating 819/638 → 818/639 mutation fails:

   ```text
   COUNTS: 17-37 shard [0, 10000] children: metadata 818 != checked files 819
   ```

   Additional controls independently reject altered parent totals, compensating source counts and altered shard boundaries. None changes a preserved manifest or its inventory hash.

5. **Receipt-selected retained files.** [receipt_audit.py](tools/receipt_audit.py), lines 74–88, 307–324 and 358–363, derives the retained set from the copy policy, configuration, reach cells and inventory. Both the declaration and actual directory must equal that set, and retained bytes must match their checked source hashes. Replay mode determines the required replay files. [evidence.py](tools/evidence.py), lines 308–312, also prevents acceptance/deletion if the runbook's size cap omitted a target file needed for the coordinator's measurements.

   Deleting the target certificate and its declared obligation, while leaving its inventory record, fails:

   ```text
   RECEIPT: retained file set differs from copy policy: missing ['24-69.certs.jsonl'], extra []
   ```

6. **Marker borrowing another slice's receipts.** [worker.py](tools/worker.py), lines 263–289 and 340, binds the four paths as one receipt set, checks structure/known identities against the requested slice, and requires passing worker, checker, structure, known-graph and G4 verdicts. The checker output itself must satisfy `check_accept()` for that slice.

   The unchanged 1907 receipts attached to the reviewer's relabelled 1445 marker fail before any child starts:

   ```text
   MARKER: receipts do not name requested slice [12, 1445, 1920]
   ```

   A resealed marker whose text receipt records failure independently gives:

   ```text
   MARKER: receipts do not record an accepted verdict for slice [12, 1907, 1920]
   ```

**Validation results**

| Check | Result | Seconds | Peak RSS KiB |
| --- | --- | ---: | ---: |
| New rereview suite | 26 exact semantic refusals; original receipts pass after each | 14.799 | 36,188 |
| Original review-control suite | 28 exact refusals; original evidence passes after each | 265.203 | 374,640 |
| Known-graph self-test | 7 exact red controls; complete synthetic fleet passes | 5.770 | 62,720 |
| Worker self-test | Acceptance, committed-byte binding, push simulation and memory controls pass | 1.004 | 42,012 |
| Order-24 certificate fixture | Nonempty certificate replay passes; missing witness and (24,68) controls refuse | 1.508 | 22,772 |
| Actual worker omission/restoration | Exit 7 at the new rule, then exit 0 and receipt acceptance | 243.303 | 155,668 |
| Receipt compatibility and expanded-format checks | Original 1907/1444 plus new whole/partial exports accepted | 103.612 | 43,944 |
| Final worker evidence reconciliation | Original 1907 and 1444 both pass counts, retention, structure and G4 | 78.301 | 27,080 |

The original review suite also reran the real known-slice calculation and induction controls:

```text
KNOWN-SLICES OK: 97912 eligible, 97912 placed
```

`compatibility.log` confirms that the actual worker's restart path accepts both original `ccfce9dc5f` markers for their own slices. Both original four-receipt bundles under `/tmp/u24-fixes-yE1TRr/worker/` pass the current receipt audit, with zero survivors measured in each target keep file. A staged two-slice fleet audit reports target children 0, kept 0, two G4 passes and zero unresolved records. Its only problem is the expected 1,918 missing slices; this is not a complete-fleet pass.

Expanded-format validation generated fresh measured inventories and exports from the same preserved evidence, retaining the original real checker/control output: 275 manifests in the whole receipt, and 270 in the partial receipt including its inherited prefix. Both passed. Legacy prefix compaction is supported through the old whole-check measurements; new inventories retain explicit prefix rows as well as their digest.

All substantive test workloads ran sequentially with the 1,536 MiB memory guard. No memory stop occurred. Protected-file SHA256 comparisons and `git diff --check` passed. The final worker evidence reconciliation and G4 recheck are recorded in `final-evidence.log`:

```text
FINAL WORKER EVIDENCE OK: 1907 G4 PASS target survivors 0
FINAL WORKER EVIDENCE OK: 1444 G4 PASS target survivors 0
```
