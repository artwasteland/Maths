# u(24) worker review fixes — 2026-10-01

Base: detached worktree at `71ef545b4a4e7e4bf99854c37f65e70458125cf8`.
All seven findings in the review's final message are addressed.
No Git command changed state.
No enumeration or cloud worker was started.
Tests use retained evidence, scratch copies, and a tiny synthetic certificate fixture.
The protected chain checkers and `u23-slice.sh` are unchanged.
The launcher's checker pin remains `a231bfc384702231f57fc21461b4c700ec8eed842bceb981076963c79d2cc86a`.

The retained test output is under `/tmp/u24-fixes-yE1TRr/`.
`review-final.log` contains 28 exact refusals and the passing real-evidence recheck after each.
`review-final/review-controls.json` records those rules in machine-readable form.

## 1. Counts not bound to files

`tools/evidence.py:59` checks every `hashes.json` record count and SHA256 against its run file.
`tools/evidence.py:110` derives prune counts from the certificate verdicts and the stage, keep and UNKNOWN files.
Native TU and refutation counts are distinguished from triangle/rhombus counts.
Silent-pass counters are reconciled with the prover's per-part diagnostics, which the inventory preserves by hash.
`tools/evidence.py:251` checks every summary cell's children, reach counts, prune counts and verification counts.
`tools/evidence.py:163` reconciles parent-source counts, aggregate parents and shard children with their files.
`counts.json` must reproduce the reconciled summary's counts, including their JSON types.

The worker runs this audit before acceptance (`tools/worker.py:393`).
A failure produces failed receipts and retains the directory.
The text and structure receipts record the target's full, reach, keep, certificate and UNKNOWN record counts measured from files (`tools/worker.py:438`).
Survivors are the target keep file's measured record count.

The false-zero controls preserve valid JSON, graph bytes, certificates and graph hashes.
The hashes control and the summary control are separate so one cannot mask the other.
Exact refusal text:

```text
COUNTS: hashes.json 17-43.UNKNOWN.g6 records: metadata 0 != checked files 1
COUNTS: 17-43 children: metadata 0 != checked files 1
COUNTS: hashes.json 24-69.keep.g6 records: metadata 777 != checked files 0
```

Twelve additional controls independently change each prune count on real `(17,37)` evidence.
For example:

```text
COUNTS: 17-37 prune input: metadata 40216 != checked files 40215
COUNTS: 17-37 prune tu: metadata 9341 != checked files 9340
COUNTS: 17-37 prune survivors: metadata 30876 != checked files 30875
COUNTS: 17-37 prune embedded: metadata 1 != checked files 0
COUNTS: 17-37 prune refuted: metadata 1 != checked files 0
COUNTS: 17-37 prune unknown: metadata 18996 != checked files 18995
COUNTS: 17-37 prune kept: metadata 18996 != checked files 18995
COUNTS: 17-37 prune pruned: metadata 21221 != checked files 21220
COUNTS: 17-37 prune tri_tu: metadata 11021 != checked files 11020
COUNTS: 17-37 prune tri_refuted: metadata 861 != checked files 860
COUNTS: 17-37 prune tri_survivors: metadata 18996 != checked files 18995
COUNTS: 17-37 prune tri_silent_passes: metadata 1 != checked files 0
```

## 2. Skipping the runbook and accepting only a G4 label

`tools/worker.py:296` refuses skipping the runbook unless retaining the run is explicit.
The refusal occurs before a child process, Git write or deletion can start.
A retained-evidence receipt says the result push was skipped.
Its marker cannot replace a production runbook pass.

`tools/evidence.py:321` requires the replay summary, fraction 0.002, zero mismatches, and positive samples except for a verified EMPTY replay.
It uses the unchanged checker's detail-derived G4 verdict routine.
It recomputes both fingerprints from the checked aggregate manifests, tool hashes and settings.
Replay parent counts must match the checked structural records.

Exact refusal text:

```text
RUNBOOK: U24_SKIP_RUNBOOK=1 requires U24_KEEP_RUNS=1
G4: replay/summary.json is required
G4: replay summary fraction must be 0.002
G4: replay summary mismatching_parents must be 0
G4: PASS requires sampled_parents above 0
G4: fingerprint differs from checked manifests, tools or settings
```

The deletion probe simulates forbidden side effects and asserts they are never reached.
No test performs a real Git write or push.

## 3. Retained result bytes unvalidated

`tools/evidence.py:81` reproduces the runbook's exact copy selection.
It requires the three source JSON files, generated `hashes.json` and `counts.json`, and all copied verification manifests.
For the target and every cell one level below, it requires each existing file smaller than 4,000,000 bytes with one of the runbook's six suffixes: `.g6`, `.keep.g6`, `.certs.jsonl`, `.UNKNOWN.g6`, `.manifest.json`, `.prune.manifest.json`.
Missing and unexpected retained files fail.
Every copied file is compared by SHA256 with its checked source.
Generated metadata is reconciled with its sources instead of being trusted.

`tools/worker.py:275` also compares the committed result blobs with the validated bytes when pushing is enabled.
The comparison runs before acceptance and again before deletion.

Exact refusal text:

```text
RESULT BINDING: retained 24-69.g6 differs from checked file
RESULT BINDING: retained 24-69.certs.jsonl differs from checked file
RESULT BINDING: retained file set differs: missing ['24-69.certs.jsonl'], extra []
RESULT BINDING: committed 24-69.certs.jsonl differs from checked result
```

The committed-blob control is simulated in `tools/test_worker.py`.
It checks that correct working-tree bytes cannot hide different committed bytes.

## 4. Resumed cells lose structural records

`tools/evidence.py:163` exports the missing fields from the verified aggregate and shard manifests.
The fourth receipt preserves parent sources, parent counts, shard ranges/counts, and original manifest text with its SHA256.
Each count is checked against its file before export.
Prefix records come from the bound whole-check receipt.
Missing export evidence prevents acceptance.

`tools/receipt_audit.py:20` validates the four receipts and retained result bytes.
`tools/receipt_audit.py:97` stages the exported summary through the existing `history/INDEX.json` interface.
It does not change the source result or the reviewed checker.

The review's resumed `(17,37)` entry in slice 1444 is used unchanged.
Presenting it without its export fails at the new rule:

```text
STRUCTURE: 17-37: resumed cell has no exported parent sources, parent count and shards
```

Removing the source manifest also fails before a receipt can authorize deletion:

```text
STRUCTURE: 17-37: cannot export resumed parent sources, parent count and shards: [Errno 2] No such file or directory: '/tmp/u24-fixes-yE1TRr/review-final/resumed-1444/17-37.manifest.json'
```

Restoring that manifest exports `(17,37)` successfully.
The unchanged summary checker recovers 16 records from the staged history: 15 prefix cells and `(17,37)`.
It reports zero unresolved records.
Its sole remaining problem on this single-slice input is the expected absence of 1,919 other slice summaries.
See `review-final/resumed-summary.log`.

## 5. Vacuous known-graph success

`tools/known_graphs.py:164` requires all 87 full/reach/keep files across the 29 production catalogue cells.
Empty files remain valid.
Every file's measured record count appears in the JSON and CLI output.
Fleet receipts can no longer omit a stage-file record (`tools/known_graphs.py:198`).

`tools/known_slices.py:139` validates the production table and obtains the files from `known_graphs.py`'s pinned catalogue.
The empty-run control reports 87 missing files; its first exact rule is:

```text
FILE 16-35.g6: required production stage file is missing
```

The valid empty-table JSON fails with:

```text
KNOWN-SLICES FAIL: CONFIG: not the production (24,69) reach table with seed 10 and root k 5
```

The real known-graph control passes again after the missing-file control.
After the empty-table control, the complete real calculation and its induction controls pass:

```text
eligible Engel graphs: 97912 in 29 cells; placed in 123 of 1920 slices: 97912
KNOWN-SLICES OK: 97912 eligible, 97912 placed, every level-12 ancestor in the prefix
```

## 6. Nonempty order-24 certificates

`fixtures/nonempty24/` contains canonical order-24 graphs and genuine TU witnesses for the chain fixture.
`tools/test_certificate24.py:91` builds a tiny synthetic seed-23 chain around the stored nonempty `24-69.certs.jsonl`.
It requires `CHAIN OK` with one certificate file replayed.
This is a chain-wiring fixture, not an enumerated production slice.
No enumeration is run to construct it.

Removing the witness gives:

```text
PROBLEM: 24-69.certs.jsonl: pruned graph W`Uw?C??G@_E?J?F_Xw@wGKABBAE?HO?oo?Xoo?eE?Cb_@K has no witness
```

The `(24,68)` chain must produce exactly this one PROBLEM line:

```text
PROBLEM: 24-68.prune.manifest.json: tu records prune only at a target (N, M) with M >= u(N) proved; (24,68) is below the proved bound 69
```

The unmodified `(24,69)` chain passes again after each refusal.

## 7. Faithfulness wording

`tools/known_slices.py:9` now says “induced subgraphs.”
This corrects the statement without changing the ancestor computation.
There is no behavioral red rule for this prose correction.
The real induction and missing-ancestor controls still pass, as recorded above.

## Receipt layout and bindings

For `s<i>of1920-<TAG>`:

| File | Contents and binding |
| --- | --- |
| `.txt` | Checker/control/audit output, tool hashes, timings, worker verdict, actual target counts, committed-result identity, SHA256 of each of the other three receipts |
| `.known.json` | Pinned catalogue, slice identity, all required file counts, matched zero-based Engel indices; SHA256 bound by `.txt` |
| `.inventory.jsonl.gz` | File bytes, SHA256 and newline counts above the shared prefix, including parent/shard files; prefix digest summary; SHA256 bound by `.txt` |
| `.structure.json` | Reconciled file counts, target records, retained-result hashes including replay evidence, original summary SHA256, normalized summary, exported resumed manifests, G4 result, whole-prefix receipt SHA256; its own SHA256 bound by `.txt` |

The v2 checked marker hashes all four receipts.
Old three-receipt markers do not authorize skipping a fresh check.
The text receipt and structure receipt both give the target keep file's actual record count.
The receipt audit checks that target records agree with the bound inventory.
It verifies a later slice's prefix binding back to a whole-check receipt.
`WORKER.md` documents the staging command for the unchanged fleet summary audit.

## Validation results

The new review controls passed: 28 exact refusals, with the unmodified evidence passing after each.
The complete known-slice calculation passed for all 97,912 eligible graphs.
The nonempty certificate fixture and its two refusals passed.
The real worker integration passed on retained copies of 1907 and resumed 1444.
It checked 1907 exhaustively and bound 1444's partial check to that whole-check receipt.
Both runs remain on disk.
Both receipt audits and both restart checks passed.
Appending JSON whitespace to either fourth receipt failed at exactly `RECEIPT: structure sha256 is not bound by text receipt`.
Restoring its bytes restored the passing receipt audit.

| Slice | Checker verdict | Checker seconds | Checker peak KiB | Text bytes | Known bytes | Inventory gzip bytes | Structure bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1907 | `CHAIN OK`, 89 cells, 75 certificate files replayed | 767.291 | 820612 | 5993 | 10062 | 68933 | 282573 |
| 1444 | Expected partial from level 13; `(17,37)` exported | 122.327 | 155656 | 5868 | 10062 | 51548 | 273056 |

The four-file bundles are in `/tmp/u24-fixes-yE1TRr/worker/res/check/`.
The staged summary-audit inputs are `worker/audit-1907/` and `worker/audit-1444/` under that scratch directory.
The command-line receipt audit also passed using only the retained result and receipt bundles:

```text
RECEIPT OK: slice 1444, target survivors 0, 1 resumed cells exported; summary input /tmp/u24-fixes-yE1TRr/receipt-cli-1444
```

`tools/test_worker.py` passed, including the simulated committed-result mismatch and three-attempt push controls.
`known_graphs.py --self-test` passed its seven exact red controls and complete synthetic fleet control.
`tools/checker_diff.py` passed plain diagnostics on three legacy runs, a full `--check`, partial checks from level 14 with 21 of 21 faults rejected identically, and summary-only comparisons.
The plain and individual summary comparisons include expected rejection diagnostics for incomplete inputs; equality is their assertion.
The complete real three-slice `(17,43)` summary audit separately reports zero problems, zero unresolved and eight target survivors (`legacy-fleet.log`).
`tools/red_controls.py` passed on retained slice 1907, including all 12 original controls and an unchanged-evidence recheck after each:

```text
U24 RED-CONTROLS OK: 12 exact rules asserted; real evidence rechecked after each
ALL SUITES OK
```

That suite took 4,605.741 seconds and peaked at 155,744 KiB.
`suites.log` and `suites.json` record every required suite's successful exit and measurements.
The separate 28-control review suite took 453.470 seconds and peaked at 374,460 KiB.
All substantial tests run sequentially with `U24_MIN_AVAILABLE_MB=1536`.
No real memory cutoff occurred; the worker self-test separately exercises a simulated cutoff and a passing restored command.
All ten Python tools pass AST parsing; the launcher passes `bash -n`; `git diff --check` is clean.
Read-only checks confirm the original HEAD and no changes to the protected checkers or `u23-slice.sh`.

## Review agreement and limits

I disagree with none of the seven findings.
The exports repair the resumed-summary evidence gap through the checker's existing history interface.
They do not alter its mathematics or diagnostics.
The full fleet's coverage verdict still requires all 1,920 slices.
Certificate replay, G4 sampling and Engel coverage do not independently certify generation completeness.
The review's stated trust in the enumerator remains a dependency of the research standard.
These changes are for coordinating review and another adversarial review before deployment.
