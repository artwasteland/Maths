**Current G1 verdict: CLOSED — Round 3 verified commit `8a10df49b0d`.**

The Round-3 verification below supersedes the remaining findings from earlier rounds, preserved here as history.

## Round 1 — 2026-10-07

**Round-1 G1: NOT CLOSED — all nine prior findings are CLOSED; a reproduced retained level-23 count gap remains.**

Verified 2026-10-07 against `e857daef1c3e35b20777ce6b6bb1f1dccf727c02`. The requested `git diff --stat 2b3c4d9dd0 HEAD -- <files>` is empty. SHA256 comparisons also establish that the live files equal both commits: receipt audit, evidence, worker, known-graph control, U24 checker, both control suites, and worker/certificate tests. See [provenance.json](provenance.json). No network, enumeration, repository writes, or Git state changes were used; all generated files and temporary directories are here.

For the table, run from this directory; `H R1` means:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B verify_history.py R1
```

Every H command runs the same mutation against the relevant archived pre-fix code and current code, then accepts both original whole/partial receipts after each version. Locations are relative to `research/unit-distance-24/tools/` in the reviewed repository.

| ID | Original finding and current fix | Verdict | Command |
| --- | --- | --- | --- |
| R1 | Empty target keep file reported as 777 records. `receipt_audit.py:91,115,325` measures target bytes/counts independently. | CLOSED | `H R1` |
| R2 | Missing `(20,49)` prune record bypasses reconciliation. `evidence.py:31,49,54` derives mandatory stage records. | CLOSED | `H R2` |
| R3 | G4 replay covers only 1 of 41 populated cells. `evidence.py:417,430,456` derives exact scope and prescribed sampling. | CLOSED | `H R3` |
| R4 | Resumed shard counts change 819/638 to 818/639 without corresponding manifests. `receipt_audit.py:176,198,203`; `evidence.py:236` reconstructs structure. | CLOSED | `H R4` |
| R5 | Receipt omits its obligation to retain the target certificate. `receipt_audit.py:74,318,322` derives the copy policy. | CLOSED | `H R5` |
| R6 | Relabelled marker borrows slice 1907 receipts to skip unrun 1445. `worker.py:268,279,284,290` binds identity and accepted verdicts. | CLOSED | `H R6` |
| T1 | Whole-check replay downgraded to slice mode, omitting seeds/prefix. `evidence.py:468,475,511`; `receipt_audit.py:268,294,366` binds replay scope to the check. | CLOSED | `H T1` |
| T2 | Reach threshold 99 accepted instead of derived 4. `evidence.py:61,86`; `receipt_audit.py:298` checks parameters in both summaries. | CLOSED | `H T2` |
| T3 | Earlier worker marker bypasses current evidence rules. `worker.py:264,294,304` re-audits absent/different implementation hashes. | CLOSED | `H T3` |

[history.log](history.log) records acceptance before each fix (`ccfce9dc5f` for R1–R6, `bd1e5bcc1a` for T1–T3), exact semantic rejection now, and honest receipt acceptance throughout. Thus the corresponding red assertions demonstrably fail without the fixes.

I read and ran the unmodified control suites through:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B run_controls.py rereview
nice -n 15 timeout 1800 /usr/bin/python3 -B run_controls.py review3
```

They assert exact error messages and green originals after every red: 26 and 19 controls passed, respectively ([logs](rereview.log), [third-round log](review3.log)). These also exercise missing cells/reach/verification, undersampling, altered parent counts/ranges, failed marker verdicts, seed/red replay details, prefix fingerprints, and restart refusal.

The default `/tmp/u24-fixes-yE1TRr/worker` fixture is absent. [prepare.py](prepare.py) reconstructs unchanged honest receipt bytes from preserved control copies and relocates marker paths; all four original whole-receipt hashes match the preserved prefix marker. G4 run views contain preserved aggregate manifests, including seeds, and reproduce both stored fingerprints. They are not raw enumeration reruns. The separate worker integration uses a private full raw copy.

`nice -n 15 timeout 1800 /usr/bin/python3 -B worker_integration.py` also passed the original real-worker omission/restoration assertions: missing prune returned **7**, retained the run, and created no marker; restoration returned **0** and its new receipt passed the current audit. See [worker-integration.log](worker-integration.log). The checker and known-graph control actually ran; neither was mocked.

The answer to question 2 is **yes**. Run:

```sh
nice -n 15 timeout 1800 /usr/bin/python3 -B probe_retained.py
```

The reproduction adds one JSON record to the originally empty `23-64.certs.jsonl`. It refreshes that file's SHA256/byte metadata and the receipt envelopes, while retaining inventory `newlines=0`, file-count `records=0`, and unchanged summary/checker output. Actual records are **1**, declared records **0**. Its unchanged retained prune manifest still binds the original empty certificate hash. Current `receipt_audit.prepare()` and `judge.accepted_copy()` accept it. The staged summary checker reports only the expected 1,919 missing slices, with no mutation diagnostic. See [retained-probe.log](retained-probe.log) and [accepted mutated bundle](retained-probe/res/check/s1907of1920-fixcheck.txt).

`receipt_audit.py:115,325` remeasures only target files. Level-23 certificate counts at line 163 come from inventory; lines 358–363 compare hashes without counting those retained records. Changing this same inventory count to the actual **1** produces the exact rejection `COUNTS: 23-64 certificates: metadata 1 != checked files 0`. Untouched originals still pass.

This proves an acceptance gap, not corruption of the completed fleet or a false mathematical result. Closure requires independent measurements of retained level-23 outputs and this regression to reject, followed by verification.

## Round 2 — 2026-10-07

The Round 1 certificate-count gap is **CLOSED**. All nine original findings remain **CLOSED**. One additional producer-binding gap is reproduced below, so G1 remains **NOT CLOSED**. This section supplies the current verdict; the preceding section records Round 1.

Verified HEAD `6a6dda8e3558fd185a1dd6ebe1c710bc45ead9c2`. The live audit and G1 controls are byte-identical to fix commit `2aba1ff128f` and the builder's packaged files. Its pristine audit equals `e857daef1c3` exactly. I read both the builder's patch and the committed diff. [Provenance](round2/provenance.json) and [diff](round2/fix.diff) are retained here. Repository and historical fixtures remained unchanged; all new writes and temporary directories stayed here.

Run from this directory; each command starts with `nice -n 15 timeout 1800`:

| Command after that prefix | Verified result |
| --- | --- |
| `/usr/bin/python3 -B probe_retained.py --expect-rejected --out round2/probe` | Original mutation rejected; untouched whole and partial receipts accepted. |
| `/usr/bin/python3 -B verify_history.py` | R1, R2, R3, R4, R5, R6, T1, T2, T3 all CLOSED: pre-fix accepted, current exact rejection, both honest receipts green. |
| `/usr/bin/python3 -B round2/run_g1.py` | Current: 15 exact refusals. Pristine: all 15 accepted by `prepare()` and `judge.accepted_copy()`. Honest receipts pass after every case. |
| `/usr/bin/python3 -B round2/probe_full_producer.py` | Three contradictory producer-metadata copies accepted; expanded-format countercheck rejects while its export remains present. |

The original probe's exact refusal is:

```text
COUNTS: inventory 23-64.certs.jsonl records: metadata 0 != checked files 1
```

`receipt_audit.py:146–199,380–382` now measures all retained level outputs, reconciles inventory/file-count/retained rows, checks every naming `outputs_sha256`, and reconciles prune counts. The G1 controls test both certificate variants, four output kinds, shortened keep content, producer hashes/counts, and missing prune bindings. Their red assertions demonstrably fail against pristine code. Logs: [original probe](round2/probe.log), [nine findings](round2/history-console.log), [patched controls](round2/g1-patched.log), [pristine controls](round2/g1-pristine.log). Round 1 logs were preserved as `round2/round1-*.log`.

**Remaining finding: retained full `.g6` producer metadata can escape validation.** The enumeration aggregate manifest uses `children_written` and `children_file_sha256`, not `outputs_sha256`. The new producer loop at `receipt_audit.py:168` reads only the latter; full `.g6` files then take the `continue` at lines 182–184. Structural reconstruction at lines 252–258 occurs only for resumed cells or aggregate manifests present in the receipt's export.

The new reproduction uses actual preserved receipts and leaves graph/certificate bytes and checker output unchanged. It refreshes affected manifest/inventory/receipt envelope hashes using the reviewed control helper:

| Retained-copy mutation | Measured output | Current result |
| --- | --- | --- |
| Legacy whole receipt: `23-64.manifest.json` claims `children_written=777`. | `23-64.g6` has 0 records. | `prepare()` and `judge.accepted_copy()` accept. |
| Legacy whole receipt: `children_file_sha256` becomes 64 zeroes. | Empty file has SHA256 beginning `e3b0c44298fc`. | Both accept. |
| Expanded receipt: omit only exported `23-64.manifest.json` for its non-resumed cell, then change the retained manifest's child count to 777. | Full file still has 0 records. | Both accept. |

Keeping that export present instead produces the exact refusal `COUNTS: 23-64 manifest children: metadata 777 != checked files 0`. This establishes that acceptance depends on the receipt's export declaration. All untouched originals still pass.

For each accepted mutation, the staged summary checker reports only the expected 1,919 missing slices. `retained_scan.scan_dir()` also measures eight files and reports no problem. [Full reproduction log](round2/full-producer.log) and [expanded mutated receipt](round2/full-producer/expanded-aggregate-omitted/res/check/s1907of1920-fixcheck.txt) preserve the evidence. These cases are outside the fifteen new controls.

I inspected the published re-judged reports: all four plans are OK and the stated outcome fields match their predecessors; fleet audit is OK. The published scan records 1,936 copies and 15,488 files with zero problems. I did not rerun the fleet or establish corruption of its copies. Those clean reports do not exercise this producer-field gap.

Closure requires comparing each retained full `.g6` file directly with its aggregate producer's child count/hash, including when the exported aggregate is absent, and adding these refusals while preserving honest compatibility.

G1 verdict: NOT CLOSED: retained full .g6 producer counts/hashes can bypass validation when its exported aggregate manifest is absent.

## Round 3 — 2026-10-07

**CLOSED.** Verified current commit `8a10df49b0db6e6bdaa6e4c32ffa01a778d55bd8`, including the builder's report and `PATCH-2.diff`. Audit/control bytes match the landed commit and builder package; `pristine-r1` matches commit `2aba1ff128f`. Worker, evidence, known-graph control and U24 checker remain byte-identical to the pilot. [Provenance](round3/provenance.json) records hashes. Repository and historical fixtures stayed read-only; all writes/temporary directories are here; no network or Git state changes.

Commands below run from this directory. `H` means `nice -n 15 timeout 1800 /usr/bin/python3 -B`. RA, E and W mean current [receipt_audit.py](<repo>/research/unit-distance-24/tools/receipt_audit.py:243), [evidence.py](<repo>/research/unit-distance-24/tools/evidence.py:31) and [worker.py](<repo>/research/unit-distance-24/tools/worker.py:268).

| Finding | Current fix | Verdict | Command after H |
| --- | --- | --- | --- |
| R1: target keep count falsely 777 | RA:69,118 | CLOSED | `verify_history.py R1` |
| R2: required `(20,49)` prune record omitted | E:53–55 | CLOSED | `verify_history.py R2` |
| R3: replay covers one of 41 populated cells | E:429–431 | CLOSED | `verify_history.py R3` |
| R4: compensating resumed shard counts | E:288–289; RA:515 | CLOSED | `verify_history.py R4` |
| R5: receipt omits obligatory target certificate file | RA:75–89,630–636 | CLOSED | `verify_history.py R5` |
| R6: slice-1907 marker skips slice 1445 | W:277–287 | CLOSED | `verify_history.py R6` |
| T1: whole-check replay downgraded to slice mode | E:474–476 | CLOSED | `verify_history.py T1` |
| T2: reach k claims 99 instead of derived 4 | E:60–61,86–89 | CLOSED | `verify_history.py T2` |
| T3: older implementation marker bypasses current audit | W:294–307 | CLOSED | `verify_history.py T3` |

I ran `H verify_history.py` for all nine. Every mutation was accepted by its archived pre-fix code and rejected with the exact expected message by current code; untouched whole/partial receipts passed after each. Thus each red assertion fails without its fix. [Log](round3/history.log).

The Round-2 probes now reject both producer fields, in legacy receipts and expanded receipts with the non-resumed aggregate export removed:

```text
COUNTS: 23-64.manifest.json children_written: metadata 777 != checked files 0
RECEIPT: 23-64.manifest.json children_file_sha256 differs from checked files
```

The fix is RA:271–281: retained full files require stage manifests, and their counts/hashes are measured independently of exports. Command: `H round2/probe_full_producer.py --expect-rejected --out round3/full-producer`. All four refusals and audit/judge greens are in [full-producer.log](round3/full-producer.log).

The Round-1 certificate probe also rejects exactly:

```text
COUNTS: inventory 23-64.certs.jsonl records: metadata 0 != checked files 1
```

Command: `H probe_retained.py --expect-rejected --out round3/cert-probe`; [log and honest greens](round3/cert-probe.log).

I read the unmodified control suite's mutations and exact-message assertions. `H round3/run_g1.py patched` confirms **188 exact refusals**. `H round3/run_g1.py pristine-r1` runs `--round2-only --audit-code .../pristine-r1/.../receipt_audit.py --expect-unpatched`: **all 173 new mutations accepted by prepare and judge**. Honest whole/partial receipts passed after every case; expanded and synthetic baselines passed too. [Current log](round3/g1-patched.log), [baseline log](round3/g1-pristine-r1.log).

Published seed **2026100703** selected **30 of 386 B rows**, without replacement or substitutions. Each field was mutated in a private fixture and envelopes resealed; exported retained producers and their matching duplicates changed together. Every refusal's traceback contains a cited audit line. [Selection](round3/sample-selection.json), [30 field mutations, messages and cited frames](round3/sample-results.json). Commands: `H round3/sample_bindings.py`, then `H round3/sample_bindings.py --start 24`. The harness initially lacked the raw-summary handler; I added it and resumed the same sample. All honest baselines and whole/partial originals passed.

`H round3/review_enumeration.py` confirms all 602 raw JSON families have annotations, with 54 additional payload/text families. I read **every H row**, all **152**, and checked its referent against producer/worker code and retained fixture paths: 95 replay comparisons, 16 prover diagnostics, 12 checker-history fields, 11 text-history fields, six directory/prefix totals, five shard fields, three known-control fields, two fingerprint descriptors and two verifier-part references. **No H row should be B.** [Individual assessments](round3/historical-review.json). Their subjects were deleted or describe pre-deletion processing; surviving metadata does not remeasure those subjects. This follows CONTRACT:35–45's checker-before-deletion standard.

**Question 2:** no reproduced retained-content claim remains unbound in the targeted paths. Sampling supports closure; it is not an exhaustive proof against every possible mutation. Historical-field limitations remain explicitly documented and are not G1 defects under the requested standard. The supplied fleet-rejudge log currently records its pilot start, without completed reports; I did not wait or claim its outcome.

G1 verdict: CLOSED
