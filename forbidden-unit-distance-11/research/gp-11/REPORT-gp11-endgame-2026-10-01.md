# GP-11 endgame engineering — 2026-10-01

Control 5.1 is still open. The 98 available shards cover **25,358** of 33,162 graphs: **24,966 embedded, 367 refuted, 25 UNKNOWN**. The observed UNKNOWN rate projects to **about 33 across all 128 shards**, before further searches or analyst work. All 244 UNKNOWNs in the 71 available f1 bundles were successfully converted into analyst packets. The frozen checker files were not changed.

The user's updated storage figures supersede the brief's 14 GB assumption. `df -h` measured **44 GB available on `/`**, including `/tmp`, and **51 GB available on the 59 GB exFAT card at `/mnt/sd`**. `free -h` reported 5.3 GiB MemAvailable on the four-core desktop. No data directory or SD-card file was modified. All generated files and scratch used here are under `research/gp-11/tools/`.

This slim checkout lacks `research/unit-distance-22/check/udcheck.py`, the trusted forbidden/gadget JSON files, AMP's graph6 source, and `research/gp-10/cloud/final/tree-public.tar.gz`. Consequently **no full frozen run, complete-B10 check, or B11 check was performed here**. Existing shard reports are provenance, not new proof replays. The measurements below explicitly separate frozen E-exact arithmetic from a complete run. Final procedures require the complete reviewed checkout and the remaining shard bundles.

**Evidence and reproducibility.** The scripts added are [make_packets.py](research/gp-11/tools/make_packets.py), [test_make_packets.py](research/gp-11/tools/test_make_packets.py), [measure_check_cost.py](research/gp-11/tools/measure_check_cost.py), and [endgame_inventory.py](research/gp-11/tools/endgame_inventory.py). Small measured receipts are retained in [endgame-evidence](research/gp-11/tools/endgame-evidence). Generated packet trees remain locally under the ignored `research/gp-11/tools/endgame-work/f1-final/` and `control51-final/`; [packet-validation.json](research/gp-11/tools/endgame-evidence/packet-validation.json) identifies their source and output hashes. An [example f1 packet](research/gp-11/tools/endgame-evidence/example-f1-packet.json) and both full collection manifests are retained for review without committing thousands of generated files. No network or producer search was used.

**1. Control 5.1 residue and completion procedure**

The population-weighted projection is `33162 * 25 / 25358 = 32.694`; the shard-weighted check is `128 * 25 / 98 = 32.653`. There are 7,804 unobserved graphs, giving about **8 additional UNKNOWNs**, or approximately 21 no-seed and 12 seeded cases in total. For scale, a Wilson 95% interval for the observed rate extrapolates to 22–48 UNKNOWNs; this is an illustrative rate interval, **not** a prediction interval for the final count, which is already at least 25. Returned shards are selected by completion, not a randomized observation schedule, so the interval does not account for slower missing shards. Budget around 50 analyst obligations, then replace that forecast with the complete union.

Missing shard indices at this snapshot are **73–77 and 103–127**. No replacement halves appear in the supplied set. The complete run must audit actual assignments, not infer completeness from directory count; hash-modulus replacement halves require excluding the replaced parent.

| Observed class | Graphs | Evidence and next action |
| --- | ---: | --- |
| No separated seed | 16 | `esc-branch:no_separated_seed`, and `esc-pins:no_separated_numerical_seed`. Prioritize geometric/refutation analysis while retaining a competing embedding search. Numerical collisions do not prove non-embeddability. |
| Seed, no exact certificate | 9 | `esc-branch:no_exact_certificate`. Preserve the numerical branch and pursue exactification, simpler pins or field representations. |
| Attempt deadline flag (overlaps the nine above) | 8 | 16 deadline events: `msolve` 2, `esc-msolve` 4, `esc-saturated` 7, `esc-pins` 3. |
| Explicit `checker:Deadline` | 0 | Do not relabel the broader control-driver exception as a demonstrated checker timeout. |

Every UNKNOWN has all 23 full-policy stage records, **575 attempts total**. All 25 timed out in each of `null`, `real`, `portfolio`, `esc-null`, and `esc-real`; the escalation null/real caps are 60 seconds. `esc-targeted` has 18 “no certifiable target” results and 7 producer timeouts. `esc-components` has 11 `no_finite_component_diagnostics`, 7 `producer_error:AlgebraError`, 4 producer timeouts and 3 “no certifiable target” results. `esc-saved` has 23 `no_timed_out_saved_candidate`, one `no_exact_certificate`, and one `attempt_error:Rejection`. These are search/checking failures, not mathematical classifications.

The control driver catches both proposal and checking exceptions in `control_b10_runtime.py:run_policy`, reporting `attempt_error:Deadline`; it loses the precise exception site. All 25 TU closures are identity closures with no steps. The nine seeded graphs, in canonical labels, are:

```text
I?D@N@xf_  I?H_omJ{?  IQAIPCT}?  I_hca_hDg  IhC?KLMMO
IoEHa@FMO  IqL@K?RBW  IsP@OkWHG  ItPG?CfEo
```

All of these except `IsP@OkWHG` have the deadline flag. [control51-residue.json](research/gp-11/tools/endgame-evidence/control51-residue.json) supplies all 25 graph/shard/class rows and the full stage/reason histogram.

The attempt exports contain **zero non-UNKNOWN proposals**, both for these 25 graphs and for all 244 f1 UNKNOWNs. `store.finish()` verifies before appending; the exception path records a replacement UNKNOWN. A reason mentioning a saved proposal therefore does not mean its bytes survived export. Recover original worker `scratch/*-cases/<graph-hash>/` outputs, numeric/refinement files, stage-stat logs, rational pins and field candidates explicitly, with hashes. The packet generator does not follow historical `/tmp` paths or invent these artifacts. An absent proposal requires recovery or fresh production before an extended check is possible.

Finish the control in the following order, on a dedicated coordinator with the complete pinned source tree. These are endgame commands, not commands run in this slim checkout. Define all coordinator work paths inside its working directory:

```bash
export PY=<repo>/pyenv-gp10/bin/python
WORK="$PWD/research/gp-11/tools/endgame-work/control51"
mkdir -p "$WORK"
guarded() {
  "$PY" -B research/gp-11/tools/guard.py -- "$PY" -B "$@"
}
```

1. Freeze the source revision, policies and source hashes of every shard; validate artifact hashes, completion/replay receipts, F9 limit, graph-derived bases and disjoint assignments. Finish the 30 missing original shards with the same reviewed control producer, or explicitly document replacements. Keep a source ledger. The producer and control analysts receive F9 (`forbidden-74.json`) and graph-only B10 input, fresh evidence and independently documented bases of order at most nine. They receive no GP-10 B10 records, answer archive, ten-vertex coordinates, B11 index, 398-member list, or ten-vertex answer classifications. A same-run ten-vertex endpoint is eligible only with its fresh F9-checkable proof and provenance. Numeric hints remain hints.

2. Assemble **all** original disjoint bundles with the existing control-specific assembler. Supply exact paths from the audited ledger; this example assumes all 128 unsplit r1 directories have arrived in `ALL_C51_BUNDLES`:

   ```bash
   bundles=()
   for path in "$ALL_C51_BUNDLES"/control51-r1-[0-9][0-9][0-9]; do
     bundles+=(--bundle "$path")
   done
   guarded research/gp-11/pipeline/control_b10_bundle.py assemble \
     "${bundles[@]}" --output "$WORK/B10-r1"
   ```

   `assemble` checks the union against the exact 33,162 B10 graph strings, replays each bundle with the GP-11 legacy **sample/F9** profile, verifies candidate certificates with the base `Checker(9)`, rejects contradictory verdicts and grounds dependencies before selection. It prepares B4p–B9p, `named`, and `regressions` beneath `controls/`, a B10 prediction declaration, and then a B10 replay. An ACCEPT with UNKNOWNs is partial. This implementation repeats arithmetic at intake and assembly; it is not the lean B11 assembler and its coordinator time must be budgeted separately.

   Historical lower-control prerequisites are extracted only in this checker-side process by `control_b10_bundle.controls()`, which excludes root B10 records. Keep them inaccessible to the analysts. **Do not use `tools/prepare_controls.py` for the withheld producer control:** it imports GP-10's historical B10 answer stream. Historical lower-control replay also does not establish a fresh lower-order producer run; retain the separate 5.2–5.4 producer evidence required by the contract.

3. Generate packets only for the assembled current residue. Supply the original bundle collection and `--select "$WORK/B10-r1/UNKNOWN.g6"`. Assign the packets under the same F9 boundary. Late/long policies are candidates for a newly frozen round, not an instruction to mutate a running job. Longer budgets and A34-style representations are useful experiments; no timeout, collision, numerical separation or expected answer count decides a graph.

   Each analyst returns one **self-contained** ordinary record for its original graph. For admission, replay a one-graph run with `profile: sample`, `forbidden_limit: 9`, `derive: false`, the correct graph hash and an empty UNKNOWN file through **GP-10's frozen checker**, using the packet's command. This avoids the GP-11 wrapper importing F10 in the analyst process. Require exit zero, `ACCEPT run verified`, zero UNKNOWN/rejections and the expected single decided graph. Retain the proposal bytes, frozen hashes, log, report and measured cost, plus a reviewable fresh-production source ledger. Acceptance proves the record, not the ancestry of supplied coordinates.

4. Normal producer return bundles can enter the original assembly command as `--overlay NEW_BUNDLE`, in a fresh output. Overlays must be disjoint subsets of the **original** UNKNOWN union. Consolidate repeated returns for the same graph before assembly; the current CLI rejects overlapping overlays. It has no `--records` analyst-import switch. Do not fabricate a control51 producer job to disguise a raw analyst result.

   For independently checked, self-contained analyst JSONL files, a transparent alternative is **checker-side substitution of UNKNOWN lines in a new copy of the assembled B10 run**. It introduces no producer base and does no F10 rewrite. The following concrete merge keeps the exact original bytes for every other graph; use it only after the F9 replays and provenance review in step 3. Here each file is exactly one record, and `ANALYST_RECORDS` is a Bash array of reviewed paths:

   ```bash
   "$PY" -B - "$WORK/B10-r1" "$WORK/B10-final" "${ANALYST_RECORDS[@]}" <<'PY'
   import hashlib, json, shutil, sys
   from pathlib import Path
   sys.path.insert(0, 'research/gp-11/tools')
   from make_packets import loads
   old, new = map(Path, sys.argv[1:3])
   manifest = loads((old/'run.json').read_bytes())
   assert manifest['profile'] == 'B10'
   assert manifest['records'] == ['records.jsonl']
   target_sha = '3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f'
   assert hashlib.sha256((old/'input.g6').read_bytes()).hexdigest() == target_sha
   unresolved = set((old/'UNKNOWN.g6').read_text().splitlines())
   replacements, ledger = {}, []
   for name in sys.argv[3:]:
       raw = Path(name).read_bytes()
       assert len(raw) <= 8*1024*1024 and raw.endswith(b'\n') and raw.count(b'\n') == 1
       row = loads(raw)
       assert set(row) == {'g6', 'verdict', 'cert'}
       assert row['g6'] in unresolved and row['g6'] not in replacements
       assert row['verdict'] in ('embedded', 'refuted')
       c = row['cert']; kind = c['type']
       assert kind in ('exact', 'tree', 'null', 'real', 'null-dag', 'real-dag', 'sub', 'tu')
       if kind == 'sub':
           assert type(c.get('index')) is int and 0 <= c['index'] < 74
       if kind == 'tu':
           assert set(c['end']) == {'forbidden', 'map'}
           assert type(c['end']['forbidden']) is int and 0 <= c['end']['forbidden'] < 74
       replacements[row['g6']] = raw
       ledger.append({'g6': row['g6'], 'source': str(Path(name).resolve()),
                      'sha256': hashlib.sha256(raw).hexdigest()})
   assert replacements and not new.exists()
   new.mkdir()
   # The assembler produces regular, same-tree control files. Refuse symlinks.
   assert all(not p.is_symlink() for p in (old/'controls').rglob('*'))
   shutil.copytree(old/'controls', new/'controls')
   for name in ('input.g6', 'predictions.txt', 'controls-provenance.json'):
       shutil.copyfile(old/name, new/name)
   pending, consumed = [], set()
   with (old/'records.jsonl').open('rb') as source, (new/'records.jsonl').open('wb') as sink:
       for raw in source:
           row = loads(raw); code = row['g6']
           if code in replacements:
               assert row['verdict'] == 'unknown' and code not in consumed
               raw = replacements[code]; consumed.add(code)
           elif row['verdict'] == 'unknown':
               pending.append(code)
           sink.write(raw)
   assert consumed == set(replacements)
   (new/'UNKNOWN.g6').write_text(''.join(c+'\n' for c in sorted(pending)))
   (new/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
   (new/'analyst-import.json').write_text(json.dumps({
       'source_run': str(old.resolve()),
       'source_records_sha256': hashlib.sha256((old/'records.jsonl').read_bytes()).hexdigest(),
       'imports': ledger, 'scope': 'structural replacement; final frozen replay required'
   }, indent=2)+'\n')
   PY
   ```

   Keep the source B10 tree, all original histories and the analyst evidence beside this new run. Freeze copies of every ledger artifact before transport. For later producer rounds, use normal overlays; for later independent analyst returns, repeat substitution against a new copy of the latest tree. Missing proofs or ancestry review leave the corresponding graph UNKNOWN. Neither the B11 outside-end rewrite nor GP-10 answer records enter any control residue step. The merge snippet was exercised on a synthetic 33,162-row UNKNOWN stream: it preserved every unchanged line, updated UNKNOWN exactly, and rejected duplicate analyst targets and F10 index 74 before publication ([structural test receipt](research/gp-11/tools/endgame-evidence/merge-snippet-validation.json)). This test grants no B10 acceptance.

5. Once UNKNOWN is empty, run the actual complete-control check:

   ```bash
   guarded research/gp-11/check/gp11check.py "$WORK/B10-final" \
     --require-complete-b10 > "$WORK/B10-final-complete.log" 2>&1
   ```

   Require **exit 0** and the literal line **`PASS B10 COMPLETE derived=324`**, plus `checked/report.json` with `status=ACCEPT`, `reason=verified`, `profile=B10`, `input_count=33162`, the exact frozen B10 hash above, `forbidden_limit=9`, `counts.unknown=0`, `conditional=false`, `conditional_minimal=[]`, and `direct_rejections=0`. `minimal_file` must be `L10.g6`; its sorted canonical contents must equal both `report.minimal` and **exactly the 324 canonical ten-vertex members of F10**, not merely have length 324. This comparison is checker-side after fresh proofs, never an analyst axiom. `gp11check.complete_b10()` enforces it and writes `F10-provenance.json`. Preserve that file, L10, minimality witnesses, all controls, hashes and logs. A failed comparison leaves 5.1/G2 open even if all numerical searches look successful.

**2. Final B11 preflight and launcher**

The resource behavior follows [guard.py](research/gp-11/tools/guard.py), [gp11check.py](research/gp-11/check/gp11check.py) and the frozen [gp10check.py](research/gp-10/check/gp10check.py):

| Resource | Actual behavior |
| --- | --- |
| Address space | Guard sets soft and hard `RLIMIT_AS=1,024,000,000` bytes, about 976.6 MiB, inherited per process. It is not an aggregate process-tree RSS cap. The checker does not impose this cap itself. |
| System memory floor | Guard refuses to start below 1,572,864 KiB MemAvailable (1.5 GiB), polls every 0.5 s, and kills the child process group on a breach. |
| CPU | Guard adds nice 15 and forces BLAS/OpenMP/MKL/NumExpr to one thread; pure-Python SymPy ground types. The final check is serial. Four cores do not divide its runtime by four. |
| Streaming | At most 128 lines or 8 MiB raw bytes per chunk, 8 MiB per line **including newline**, SQLite page cache 8 MiB and `temp_store=FILE`. Parsed JSON and arithmetic need additional memory. Chunking is not a guarantee that every individual certificate fits the address-space cap. |
| Arithmetic limits | E-exact allows at most 2,048 interval bisections; DAG certificates at most 256 rows. These are proof-format limits, not per-certificate wall timers. Canonicalization subprocesses have a 60-second timeout. |
| Scratch | GP-10 sets `SCRATCH=Path('/tmp/gp10-check')` and overwrites both `TMPDIR` and `SQLITE_TMPDIR` on import. GP-11 explicitly creates its SQLite temporary directory beneath `base.SCRATCH`. Moving the run directory or exporting TMPDIR alone does not relocate this. |
| Final timeout | There is no overall or per-proof wall timeout in the final checker. Producer `check_seconds=60/180` deadlines are not final-checker limits. A launcher/session timeout can still terminate it. |

Use one proof/check lane on this desktop, with source and input bytes frozen throughout. The current memory headroom is sufficient to attempt the bounded preflight, not a proof that every remaining algebraic certificate fits. If guard stops the final run, retain its logs, diagnose the cause and start a fresh run; do not call a partial report complete.

Storage is much smaller than “450K full proofs” suggests: the rehearsal has 405,351 `super` records, 1,588 `sub`, 1,735 TU, 27,145 exact embeddings, 106 other direct refutations, and 12,783 UNKNOWNs. SQLite stores graph/status/dependency/details metadata, not complete certificate JSON. The exact input streams and measurements are in [inventory.json](research/gp-11/tools/endgame-evidence/inventory.json).

| Measured object | Bytes / scale |
| --- | ---: |
| Rehearsal decisions | 281,461,955 bytes |
| Rehearsal UNKNOWN records | 1,547,140 bytes |
| Rehearsal total certificate input | 283,009,095 bytes (269.9 MiB), 448,708 records |
| 71 f1 record streams | 659,571,754 uncompressed bytes; 155,548,131 compressed; 6,409 rows including 9 supporting refutations |
| 98 control record streams | 162,151,074 uncompressed bytes; 34,378,160 compressed |
| Maximum f1 record | 7,787,143 bytes (7.43 MiB), below the 8,388,608-byte limit |
| SQLite model for all 448,708 records | 205,635,584 bytes (196.1 MiB), including both graph tables, dependency index and fully populated queue |
| One per-record ACCEPT JSON log | 28,738,409 bytes (27.4 MiB), plus stdout and minimality evidence |

The SQLite figure is a **synthetic footprint model** using the actual graph/dependency inventory, actual UNKNOWN details and a conservative approximately 256-byte details field per decided record. It runs no proof verification and does not measure every transient journal/sort peak of a real check. Reserve **1–2 GiB for scratch** and **0.5 GiB for ordinary output/logs**, then measure live high-water use in the preflight. Long inherited UNKNOWN histories or unusually verbose details can exceed the model.

Scaling f1's observed certificate bytes by its 6,400 assigned graphs to the 17,505-graph first-wave frontier gives about **1.80 GB**; adding the cheap rehearsal's input gives a roughly **2.1 GB** planning payload before deduplication, later rounds and the last analysts. It is not an observed final assembly size. Provision **10–15 GiB of working space** for an approximately 2–4 GiB final tree, source/staging copies, B10/other controls, scratch and logs, retaining at least another 10 GiB of root headroom. At 44 GB free this is practical. Actual size admission must use the assembled tree plus scratch/output allowances, including any simultaneously retained alternate assemblies. Record-count alone is no disk bound: 450K records at the allowed 8 MiB each would be about **3.43 TiB**.

Use the SD card for checksummed compressed archives/split transport parts if needed. Keep the active SQLite/checker tree on the root filesystem. exFAT is suitable for a tar archive, not for preserving a POSIX source tree's symlinks, ownership or executable permissions directly. There is no need to redirect the frozen scratch path merely to fit this measured workload. If a future run requires relocation, use a recorded OS mount mapping or a reviewed operational wrapper setting `base.SCRATCH`, `TMPDIR`, `SQLITE_TMPDIR` and `tempfile.tempdir`; do not edit a frozen checker. The supplied timing helper uses that latter relocation solely for its local one-record measurements.

**Measure the hard tail before launching.** `endgame_inventory.py` lists candidate source file/line/hash, record bytes, certificate type and exact-field degree. The f1 sample has 542 E-exact records of degree at least 20, including degrees 44, 48, 56 and 72. Degree and byte count are separate selection axes; also inspect coefficient string lengths, primitive-polynomial height, isolating-interval width, DAG row/term counts and tree size. Include all new analyst certificates, largest near-cap DAGs, and a stratified sample of cheap exact proofs and pointers. A pointer sample must include its dependency closure to measure a full run; a bare pointer is not a self-contained timing case.

Extract selected original lines by the inventory's file/line references, verify their SHA-256, and run:

```bash
"$PY" -B research/gp-11/tools/measure_check_cost.py \
  --out research/gp-11/tools/endgame-work/full-cost-preflight \
  --seconds 900 CASE1.jsonl CASE2.jsonl CASE3.jsonl
```

The default mode runs a real one-record frozen **sample/F9** (order ten) or **fixture11/F10** (order eleven) replay in a complete checkout, with the normal guard and a 900-second external observation limit. Keep process status, verdict/reason, input/checker hashes, wall seconds, peak RSS, field degree, size, log and report. A timeout is a **censored lower bound**, not an accepted proof or a 900-second timing observation. Repeat with a reviewed larger observation window or improve the representation. Preserve the normal Python integer-string parser limit: do not enlarge it to make malformed proposals pass. The total-run pilot must also include minimality and nested controls; one-record `derive:false` checks cannot estimate that work.

In this checkout `--exact-only` calls the hash-pinned, unchanged `gp10check.exact_embedding` routine directly after strict record parsing and canonicalization. It does not instantiate the missing trusted-data-dependent checker. A3 and A4 passed that arithmetic under guard:

| Certificate | Degree | Record bytes | Arithmetic seconds here | Whole child wall seconds | Peak self RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| A3, `J_?gkpAYHb?` | 28 | 1,067,973 | 45.03 | 46.10 | 83.9 MiB |
| A4, `JqM??CNGqg_` | 60 | 914,553 | 89.22 | 90.11 | 84.8 MiB |

Both needed zero interval bisections. The historical A34 whole-checker measurements were 42.194 and 99.308 seconds, respectively; these are only approximate comparisons across shared-machine runs. Fresh receipts: [A34 measurements](research/gp-11/tools/endgame-evidence/check-cost/measurements.json). Four additional selected source records also passed the arithmetic-only check:

| Source case | Degree | Record bytes | Arithmetic seconds | Peak self RSS |
| --- | ---: | ---: | ---: | ---: |
| f1-154, highest degree | 72 | 779,918 | 54.08 | 82.5 MiB |
| f1-089 | 56 | 1,066,813 | 54.95 | 85.6 MiB |
| f1-026, largest E-exact record | 26 | 3,196,760 | **240.97** | 102.98 MiB |
| control51-r1-071, highest control degree | 60 | 843,916 | 39.10 | 82.7 MiB |

All four needed zero interval bisections; cost was dominated by rational/polynomial arithmetic. The degree-26 record was much slower than degree 72, supporting selection by coefficient size as well as degree. These shared-desktop wall measurements included ordinary competing load (including packet I/O during part of the run); only one arithmetic benchmark child ran at a time. [Frontier receipts](research/gp-11/tools/endgame-evidence/frontier-check-cost/measurements.json) and [original source/line/hash selections](research/gp-11/tools/endgame-evidence/selected-cost-inputs.json) make the cases reproducible. This arithmetic evidence does not substitute for full-run acceptance, refutation timings, or population minimality timing.

**Time estimate.** The historical 33,162-certificate/3,156-second rate scales to **11.86 serial hours** for 448,708 graphs. Adding one B10 replay gives about **12.7 hours** before extra control/minimality/transport overhead. Treat 13–15 hours as a favorable baseline, not a promise: the control's new certificate mix and the degree/height tail differ from the historical stream. Use `T = T_controls + T_input/resolve/minimality + sum(N_class * measured_mean_class_seconds)` on the actual final selected record set. Avoid charging every propagated graph the cost of its shared embedding root; the root is checked once, while each pointer still incurs its own parsing/map checks.

For sensitivity, 500 expensive direct proofs averaging 90 seconds add 12.5 hours; 1,500 add 37.5 hours. The observed f1 rate projects to roughly 1,480 degree-at-least-20 embeddings in the frontier, but **they must not all be assigned A4's timing**: representation and coefficient height matter, and selection may replace many with pointers. A reasonable provisional reservation is **24–72 serial hours for final verification**, revised after the stratified preflight and control replay. It is a planning allowance, not a confidence interval or upper bound. Analyst search/repair time, unfinished shard production and G5 review are additional and are not measured by these checker timings. A four-core desktop still uses one final checker lane.

`coordination/cloud-workers/gp11-check-run.sh` is insufficient for the final claim. It explicitly accepts only `fixture11`, sets `forbidden_limit=10, derive=true`, lacks controls/predictions and the external B11 digest, calls its output a rehearsal and copies `minimal.g6`. It can also return zero after pushing a **rejected** report: its exit discipline treats report delivery as success. A cached `run.json` bypasses its initial unpack/hash preparation. Do not relabel such a report or reuse a stale rehearsal directory as a final result.

The final launcher must do the following:

1. Create a new immutable run directory; verify the transport parts, assembled payload hashes and every selected certificate stream. Include `records.jsonl` **and** `unknown-records.jsonl` from the lean assembler, plus its `hosts.jsonl` when named. Structural assembly is not a proof check. B11-only outside-end rewrites may be used with their recorded maps; none may flow into the fresh B10 control.
2. Copy the frozen B11 input, the completed **fresh-producer control 5.1** tree as `controls/B10`, and the general-search `named11` evidence tree. Existing correct-profile ACCEPT reports must be present inside the run tree. Copy the original precommitted `PREDICTIONS.md` and retain its commit chronology attestation. All control manifests, input/certificate files and reports, including symlink resolutions, must stay inside the B11 run tree. Use the original reviewed source hashes and retain general-search provenance for the named graphs.
3. Build the **B11** manifest below. Remove fixture-only `forbidden_limit` and `derive`: the real profile prohibits these overrides. B11 has exactly nine control entries; `named` remains nested under the B10 control, while B11 directly requires `named11`.

   ```json
   {
     "profile": "B11",
     "input": "input.g6",
     "input_sha256": "ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f",
     "records": ["records.jsonl", "unknown-records.jsonl"],
     "unknown": "UNKNOWN.g6",
     "hosts": "hosts.jsonl",
     "controls": {
       "B4p": "controls/B10/controls/B4p",
       "B5p": "controls/B10/controls/B5p",
       "B6p": "controls/B10/controls/B6p",
       "B7p": "controls/B10/controls/B7p",
       "B8p": "controls/B10/controls/B8p",
       "B9p": "controls/B10/controls/B9p",
       "B10": "controls/B10",
       "named11": "controls/named11",
       "regressions": "controls/B10/controls/regressions"
     },
     "predictions": {"path": "PREDICTIONS.md", "sha256": "ACTUAL_SHA256_OF_THE_PRECOMMITTED_FILE"}
   }
   ```

4. Run the real profile with the independently pinned digest, not a digest trusted solely from `run.json`:

   ```bash
   "$PY" -B research/gp-11/tools/guard.py -- \
     "$PY" -B research/gp-11/check/gp11check.py "$FINAL_RUN" \
     --b11-sha256 ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f \
     > "$FINAL_LOG" 2>&1
   ```

   The checker replays every control before the B11 records. Lower controls referenced both directly and inside B10 are replayed more than once. B10 must again pass the exact 324 comparison. Predictions hashes are checked; chronology is a G2 attestation, not something proved by timestamps or the checker. Obtain a durable uninterrupted execution window: the lab notes' two-hour cloud-session cap is incompatible with this serial invocation. There is no validated frozen-checker resume facility; concatenating separately accepted shard reports cannot replace the complete run/minimality check.
5. Require process exit zero, `ACCEPT run verified`, `profile=B11`, the externally pinned hash and 448,708 inputs, zero direct rejections, `counts.unknown=0`, `conditional=false`, `conditional_minimal=[]`, complete F10 provenance and correct control receipts. Read `checked/L11.g6`, not the rehearsal's `minimal.g6`, and preserve its hash, minimality evidence, all consumed-artifact hashes, environment, logs and resource measurements. Distinguish resource stop, checker rejection and transport failure in launcher exit codes. Guard the manifest/cache path on **every** launch and never count mere report existence as success.

This establishes the verification part of G3/G4. Publication still requires G0–G5 evidence and the existing `write_result.py` gate checks, including independent G5 review and prior-prediction chronology. A conditional ACCEPT remains conditional.

**3. Analyst packet and batch-runner specification**

`make_packets.py` emits one directory per independent canonical graph, identified by a stable SHA-256 prefix; shared-core grouping never discounts the number of certificate obligations. It reads only explicitly supplied bundles, checks every summary artifact hash before and after consumption, checks the uncompressed record hash, exact coverage and UNKNOWN list, joins attempt IDs through frontier metadata, verifies canonical graph6 with `nauty-labelg -q`, and checks TU edge additions/permutation transport. Gadget implications still require the frozen checker. Output is staged and published only after every source passes; existing outputs, duplicate assignments, mismatched histories and selections outside the source UNKNOWN set are rejected.

Each packet contains:

| Field | Required interpretation |
| --- | --- |
| Canonical graph and labels | Graph6, vertex order `0..n-1`, edges/degrees and canonicalizer. Coordinates and maps never silently acquire new labels. |
| TU closure | Original step/gadget maps, added pairs, canonical closure, `old_to_new` and inverse `new_to_old`, endpoint and fixed-point metadata. Original-label coordinates transport to closure label `i` using the inverse map. Stored gadget/F9 labels and canonical endpoint labels are explicitly different conventions. |
| History/failure routing | Complete available attempt records, reason, outcome and budget, original UNKNOWN record, prior-round stage history, bundle-local graph ID and source hashes. No-seed/seed class is separate from timeout/error flags. Actual per-graph seconds are absent in these exports and are marked absent; a cap is not elapsed time. |
| Saved proposals/artifacts | Any retained non-UNKNOWN attempt record is copied with its hash, size, graph, stage, outcome and degree and labeled unverified. Historical worker paths/hints are preserved as text, never automatically read. Missing proposal/refinement files must be explicitly recovered with provenance before use. |
| Numerics and collisions | Exported coordinates, residual, best separation, starts/converged counts and collision-pair frequencies, all in original labels. Float residual zero is not exactness or a precision estimate. Inferred frame matches are hints. |
| Frames and rational pins | Every edge is an eligible frame candidate; explicit recorded frames/pins are preserved. No unrecorded rational pin is inferred as fact. Gauge pins fix only a unit edge; extra pins may select an embedding branch but cannot be smuggled into a general refutation. |
| Geometry | Triangles with both orientation signs and four-cycle/rhombus opposite-pair identities, derived from the actual graph. The parallelogram identity assumes distinct points of an injective embedding; it is not an independent refutation certificate. |
| Field candidates | Recorded primitive candidates/field hints and saved proposal degree/size; triangle cases suggest trying rational functions over Q(sqrt(3)). A suggested subfield does not determine the full field, minimal polynomial or degree. Preserve defining polynomial, root interval, coordinate recognition basis, working precision and exact residual checks when recovered/generated. |
| Checker contract | Exact guarded command, run manifest/input template, pinned GP-10/kernel/F9/gadget hashes and current GP-11 hash, scratch behavior, acceptance conditions and required result/cost artifacts. Control packets use GP-10 sample/F9; B11 packets use fixture11/F10. Neither profile is a final population result. |

The request to analysts should explicitly ask for A34's useful intermediate evidence: rational pins; orientation choices; triangle/rhombus identities; source proposal paths/hashes; primitive-coordinate choice; rational-function recognition over useful subfields; factor selection and a shared real-root interval; conversion to the checker's ordinary single-primitive-element coordinates; exact edge identities and all-pair injectivity. Shorter coefficients or a simpler branch can be more valuable than a lower field degree. A refutation must cover all relevant branches and use only the checker-regenerated graph/frame/saturation equations.

On the current f1 bundles the generator produces **244 packets from 6,400 assigned graphs in 71 shards**: **133 no separated seed; 111 seed without exact**, with **31 checker-deadline flags**, **44 checker rejection/error flags**, **43 producer algebra-error flags**, and **241 producer-timeout flags** (overlapping). The 31 deadline cases have 54 events: saturated 20, saved 21, pins 13. The other 80 seeded cases include 13 `no_separated_branch` outcomes: a numerical seed existed, but branch enumeration found no separated branch. Twelve UNKNOWN graphs have nontrivial TU maps, which were structurally validated. This updates the lab notes' 64-shard, 228-graph sample without mixing their denominators.

Reproduce the generation and tests with:

```bash
"$PY" -B research/gp-11/tools/make_packets.py <repo>/f1-bundles \
  --out research/gp-11/tools/endgame-work/f1-reproduced
"$PY" -B research/gp-11/tools/make_packets.py <repo>/c51-bundles \
  --out research/gp-11/tools/endgame-work/control51-reproduced
"$PY" -B research/gp-11/tools/test_make_packets.py
```

Both a single bundle and a parent containing shard bundles are supported. `--select FINAL_UNKNOWN.g6` restricts packets to a later assembled residue and fails if a selected graph is absent. Inputs must have disjoint assignments; overlapping rounds require coordinator reconciliation before invocation. Every output file is covered by `SHA256SUMS.json`. Each packet's `bash check.sh` first verifies `CHECKER_SHA256SUMS`, then executes the guarded command; control check scripts do not import the F10-reading GP-11 wrapper. The 12 automated tests cover hash corruption, exact UNKNOWN coverage, incorrect ID/graph joins, bad TU permutations, unverified proposal preservation, deadline distinctions, geometry labels, deterministic output, selection, canonical form, path traversal, duplicate JSON keys, nonfinite numbers and the F9-only command boundary. The actual f1 and control collections were additionally exercised end to end.

For the local batch analyst runner, use a coordinator and **two active analyst subagents by default**, increasing to at most four only after measured memory headroom permits. Agent concurrency and heavy-process concurrency are separate: on this shared desktop keep a semaphore of **one heavy CAS/check process**, allowing the other analysts to inspect geometry, reason and prepare code. At most two heavy processes should be considered only after their measured aggregate memory and the system floor support it; four individually capped processes can exhaust the roughly 5 GiB headroom. The current task designs this runner; it does not launch analyst searches.

The runner should implement the following durable lifecycle:

1. Ingest only the current final residue and immutable packet hashes. Store a queue with `queued`, `leased`, `proposed`, `checking`, `accepted`, `retryable`, and `unresolved` states. Lease by canonical graph and source hash, not by shard-local numeric ID. Write attempts/leases/results under separate per-packet directories; never let agents edit the frozen source or a shared certificate stream. A crash expires a lease, not the mathematical obligation.
2. Dispatch bounded independent packets to two to four subagents, including the full fresh-evidence restriction for control51. Start each control analyst with fresh context containing only its packet and allowlisted instructions; do not inherit the coordinator's transcript or answer-side tool results. Keep the control and B11 queues in separate workspaces/access scopes: subagent instructions alone are not a filesystem isolation boundary. Supply only graph/F9/gadgets/checker/search code and fresh control evidence to the control analysts. Do not pass this report's withheld target discussion as their search prompt. Group structurally related packets for efficiency but still demand one proof per graph.
3. Put proposal-recovery/representation tasks early in the seeded/deadline queue. Put no-seed cases into refutation/geometry work with competing embedding attempts. Fixed experiment budgets yield an unresolved record and complete diagnostics when exhausted. No agent's prose, probability or claimed ACCEPT updates the decision table.
4. Analysts return `record.jsonl`, a provenance ledger (source/packet hashes, commands, seeds, precision, pins, recovered artifact hashes), construction/identity evidence and a cost receipt. The coordinator checks graph identity, one-line size, exact rational spelling and label maps, then independently runs the pinned frozen checker in a fresh isolated child. No ungrounded pointer or external supporting record is permitted in the requested self-contained result. If a method naturally creates dependencies, inline/materialize a direct proof or return unresolved until a separately reviewed closed-bundle intake is defined.
5. Record separately search wall/CPU time, checker wall/CPU time, peak process/tree RSS, scratch high-water bytes, degree/height/size, exit/rejection reason, memory-floor events and checker hashes. Use an external time cap, retaining timed-out proposals and marking censored costs. A successful arithmetic microbenchmark alone is insufficient admission. Replace malformed or overly expensive field representations; do not relax frozen parser/line/arithmetic limits.
6. On an independent ACCEPT, append a hash-bound immutable result to the admission ledger; serialize queue updates in the coordinator. Reject opposite verdict conflicts and quarantine the evidence for review. Reuse an old receipt only if all record, source, profile and dependency hashes match; the final population check still replays everything. Propagation happens in reviewed assembly and does not erase unresolved independent obligations prematurely.
7. Stop when the final assembled UNKNOWN set is empty or every remaining task has a documented unresolved outcome. Feed control results through the F9 admission procedure above and B11 results through the lean assembler, then budget the **single complete final B11 replay**. Preserve accepted expensive proofs as reusable artifacts, but never replace that final replay with the sum of analyst receipts.

A34's two successful examples took roughly 10 and 12 analyst wall minutes, but they were selected seeded embedding cases. They do not establish throughput for the 16 control no-seed cases or the final B11 refutation residue. Estimate analyst completion from measured class-specific batches and unresolved fractions; do not promise the week from checker runtime alone.


**Follow-up 2**

Implemented the resumable launcher, blinded F9 checker wrapper, analyst brief, and tests in `research/gp-11/tools/`. The complete 128-shard control has **32 UNKNOWNs: 20 without a separated seed and 12 seeded cases without an exact certificate**. After landing the tools in the real checkout, the coordinator runs:

```bash
cd <repo>
bash research/gp-11/tools/control51_campaign.sh prepare
bash research/gp-11/tools/control51_campaign.sh scan
bash research/gp-11/tools/control51_campaign.sh run --jobs 2
# Inspect progress, or retry only the final checker:
bash research/gp-11/tools/control51_campaign.sh status
bash research/gp-11/tools/control51_campaign.sh finalize
```

The default output is `<repo>/control51-campaign/`. Preparation uses `make_packets.py`'s builder with `--select B10-r1/UNKNOWN.g6`. The [runbook](research/gp-11/tools/CONTROL51-CAMPAIGN.md) states the exact 14-file allowlist, forbidden material, options, authentication/runtime requirements and exit codes. Every extra prelaunch file/directory, link, special file or changed pin stops dispatch, including renamed answer files. Bubblewrap hides the checkout, bundles, coordinator receipts and other workspaces; the supplied files are mounted read-only. Standard tools and the Python venv remain available. Fresh Codex contexts use the requested model/effort, at most two concurrent searches and `timeout 5400`; there is no unisolated fallback.

`campaign.json`, `raw-packets/` and `seeds/` preserve inputs and pins. `workspaces/` contains fresh attempts; `verification/` and `results/` contain independent F9 checks and returned certificates/provenance. `ledger.jsonl` records hash-bound ACCEPTED/UNRESOLVED events. Rerunning `run` validates and skips accepted cases, recovers interrupted returns, and retries unresolved cases in new contexts. Only **32/32 accepted** enables a new `B10-final/` and the complete population check. `final-check.log` and `final-status.json` preserve the exact PASS or failure; ordinary ACCEPT is insufficient. The merge preserves all other source record bytes, copies analyst provenance, and leaves B10-r1 untouched.

Budget up to **24 hours of search at two-way concurrency**, plus up to eight hours of independent checking (overlapping where possible), startup/kill grace and the final replay. The partial B10 report took 3,670.7 seconds; allow that baseline plus new certificate costs for the final check. Completion is not guaranteed. Preparation is about 14 MB; the lean final source copy is about 233 MB before replacement certificates and search scratch. Keep the active campaign on `/` with its reported 44 GB free; the exFAT card can hold archives.

Validation: all 128 bundles prepared, all 32 blinded workspaces scanned, idempotent preparation, **22 campaign tests plus 12 packet tests**, and a full frozen F9 replay of a fresh two-vertex unit-edge fixture. A malformed replacement was rejected and its stale ACCEPT report removed. Filesystem isolation passed. This surrounding sandbox blocks private network namespace setup (`NETLINK_ROUTE: Operation not permitted`); the complete Codex/authentication launch remains for the coordinator's fail-closed probe outside it. **No analysts, Codex calls or network requests were made here.** The actual final gate is `NOT RUN complete-B10: 0/32 independently ACCEPTED; 32 unresolved or unattempted`. Evidence is in `research/gp-11/tools/endgame-evidence/control51-campaign-*`; rehearsal workspaces are ignored under `endgame-work/`.

```bash
<repo>/pyenv-gp10/bin/python -B research/gp-11/tools/test_control51_campaign.py
<repo>/pyenv-gp10/bin/python -B research/gp-11/tools/test_make_packets.py
```
