**u(24) third-review fixes — 2026-10-01**

Base: detached worktree at `bd1e5bcc1a`. All three requested findings are addressed.
The reproductions, earlier reports and retained evidence were read before editing.
No Git command changed state. The three chain checkers, u(23) judge, runbook and
launcher (including its checker pin) are unchanged. No enumeration or independent
enumerator replay was started, and `tools/red_controls.py` was not run.

Logs and scratch controls are in `/tmp/u24-review3-fixes-8vhfvm4v/`.
[review3_controls.py](tools/review3_controls.py) copies the third review's actual
mutations from `/tmp/u24-review3-bd1e5bcc1a/extra/`. It independently checks their
receipt envelope hashes, retained-file hashes, summary binding and the retained
files' inventory records before asserting the semantic refusal. Additional
mutations refresh those bindings too. The original receipts, replay evidence
(including manifest fingerprints) and restart markers must pass after every red.
Graph and certificate bytes remain unchanged.

1. **G4 scope follows the whole/prefix check.**
   [evidence.py:468](tools/evidence.py#L468) requires full mode for a whole check,
   and slice mode for a partial check with an accepted full-mode prefix replay.
   The latter must have the same prefix fingerprint. The existing call to the
   u(23) judge still derives the complete cell scope, samples, seed recomputations,
   stage parameters and red outcomes. [evidence.py:550](tools/evidence.py#L550)
   derives the check scope from the worker's check start and audits the supplied
   prefix bundle before using it. [receipt_audit.py:268](tools/receipt_audit.py#L268)
   derives whole/partial from the accepted checker output and recursively audits
   the bound prefix; [line 366](tools/receipt_audit.py#L366) passes that context to G4.

   The reviewer's whole receipt with an internally consistent slice-mode replay
   now fails at both worker G4 validation and receipt audit. Exact control output:

   ```text
   REVIEW3 red: G4: whole check requires a full-mode replay
   ```

   Additional controls preserve full-mode labels while removing a seed's full
   recomputation or making R1's recorded outcome non-red. Their exact refusals are:

   ```text
   REVIEW3 red: G4 SCOPE: a full G4 replay whose seed cell 10-14 is not recomputed in full over its 24862 audited graphs: records 24862, enum2 24862
   REVIEW3 red: G4 SCOPE: a full G4 replay whose red controls ['R1'] are not red by their own recorded outcome
   REVIEW3 red: G4: slice-mode prefix fingerprint differs from passed full replay
   REVIEW3 red: G4: slice-mode replay requires a passed full-mode prefix replay
   ```

2. **Stage parameters follow the configuration-derived table.**
   [evidence.py:31](tools/evidence.py#L31) applies the common requirements check to
   every required cell. [Lines 60–89](tools/evidence.py#L60) compare every reach
   record's `k`, augmentation `reach_k` and parent levels/kinds with the derivation.
   Prune sources must name that cell's configured input file; verification must
   read the configured output stage. JSON comparison preserves integer types.
   Producer paths may relocate, but their input filenames cannot change.
   The worker invokes this before reconciliation; [receipt_audit.py:298](tools/receipt_audit.py#L298)
   applies it independently to both raw and exported summaries. Replay stage
   sources, inputs, slice identities and consumers remain checked by the reused
   judge's `stage_fields()`.

   The reviewer's `(20,49)` reach `k = 99` summary, with refreshed summary,
   inventory and receipt hashes, fails at both worker reconciliation and receipt
   audit. Exact control output:

   ```text
   REVIEW3 red: PARAMETERS: 20-49 reach k: metadata 99 != derived 4
   ```

   Independent controls cover seed, resumed-prefix, resumed-upper and target
   reach records, plus prune source, augmentation threshold and verification stage.

3. **Markers bind the implementation that accepted them.**
   [worker.py:264](tools/worker.py#L264) records the loaded worker and evidence
   source hashes. [Lines 294–308](tools/worker.py#L294) require the current receipt
   audit when either hash is absent or differs. Both same-slice restart and prefix
   reuse use this path. The worker supplies the configured result root, so a
   custom receipt directory does not determine which result is audited.
   [Lines 497–505](tools/worker.py#L497) write both hashes and the result path into
   each new marker, refusing marker creation/deletion if either source changed
   during the check. Honest older bundles are audited without rewriting them.

   The third review's older marker, whose four receipt hashes are valid but whose
   structure claims 777 records for an empty target keep file, now fails. Exact control output:

   ```text
   REVIEW3 red: MARKER: worker/evidence hashes differ; current receipt audit rejected bound bundle: COUNTS: structure 24-69.keep.g6 records: metadata 777 != checked files 0
   ```

   The controls cover missing hashes, a changed worker hash, a changed evidence
   hash, and the actual restart entry point. Restart refuses before starting a
   child or deleting anything. A marker with both current hashes retains its
   existing fast path after its receipt bindings and accepted verdicts validate.

The 19-control third-review suite passed in 29.349 seconds, peak RSS 38,224 KiB.
Every red was followed by acceptance of the unmodified evidence and original
marker. `controls.log` and `controls/review3-controls.json` record every exact output.

`rereview_controls.py --worker` passed all 26 exact semantic refusals, with the
original receipts passing after each. Its real worker integration rejected the
omitted prune record with exit 7 and no marker, then accepted the restored slice
with exit 0. The fresh partial receipt passes receipt audit, and its actual marker
contains both current code hashes and passes restart verification. Both runs kept
their evidence. The combined suite took 434.332 seconds, peak RSS 155,692 KiB.

Compatibility was checked without rewriting the original bundles:

| Worker version | Honest receipts | Result |
| --- | --- | --- |
| `ccfce9dc5f` | `worker/res/check/s1907of1920-fixcheck.*` and `s1444of1920-fixcheck.*` under `/tmp/u24-fixes-yE1TRr/` | Receipt audits and old-marker verification pass; target survivors measured as 0 |
| `bd1e5bcc1a` | `real-worker/res/check/s1444of1920-rereview.*` under `/tmp/u24-rereview-fixes-xJ9521/` | Receipt audit and old-marker verification pass; target survivors measured as 0 |

Read-only `git show` comparisons confirm that the text receipts' worker hashes
identify those exact historical versions. After all regression suites finished,
`compatibility.py` repeated the receipt audits and the actual `worker.main()`
restart path for all three old bundles and the new worker bundle. All passed with
zero survivors measured, without starting a child or deleting anything. See
`compatibility.log`; `suites.log` also records the fresh marker and receipt checks.

| Check | Result | Seconds | Peak RSS KiB |
| --- | --- | ---: | ---: |
| `review3_controls.py` | 19 exact refusals; original evidence and markers pass after every red | 29.349 | 38,224 |
| `rereview_controls.py --worker` | 26 exact refusals; real worker omission/restoration and fresh marker checks pass | 434.332 | 155,692 |
| `review_controls.py` | 28 exact refusals; original evidence passes after each; all 97,912 eligible known graphs placed | 457.330 | 374,692 |
| `known_graphs.py --self-test` | Seven red controls; complete synthetic fleet passes | 9.549 | 62,696 |
| `test_worker.py` | Acceptance, comparison, committed-byte binding, simulated push and memory controls pass | 1.008 | 42,016 |
| Final receipt/restart compatibility | Both historical workers' honest bundles and the newly written bundle pass | 6.021 | 35,276 |

Exact suite completion output:

```text
REVIEW3 CONTROLS OK: 19 exact refusals; original evidence passed after every red
REREVIEW CONTROLS OK: 26 exact semantic refusals; original evidence passed after every red
REVIEW CONTROLS OK: 28 exact refusals; unmutated evidence passed after every control
KNOWN-SLICES OK: 97912 eligible, 97912 placed, every level-12 ancestor in the prefix
KNOWN-GRAPHS SELF-TEST OK: 7 rule-specific red controls; clean evidence restored after each
WORKER SELF-TEST OK: acceptance, comparison errors and three-attempt push guards
ALL REQUIRED SUITES OK
```

All substantive tests ran sequentially with `U24_MIN_AVAILABLE_MB=1536`, monitored
by `worker.measured()`. No real memory cutoff occurred; the worker self-test's
memory refusal is deliberately simulated. `suites.json`, `controls.measurement.json`
and `compatibility.measurement.json` preserve the measurements. The only change to
the old review suite is supplying the newly required, already-checked prefix
context to its partial G4 call; none of its assertions or controls was removed.
All 12 Python tools parse successfully. `git diff --check` is clean. Read-only
comparisons confirm the protected files and the original detached HEAD are unchanged.
