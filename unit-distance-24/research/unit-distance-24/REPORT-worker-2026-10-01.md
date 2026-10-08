# u(24) worker deployment check — 2026-10-01

Implemented the checked worker, the table-only u(24) checker extension, and the streaming Engel control.
The worktree was edited without a git state change.
The original checker, lean checker and u(23) worker scripts are unchanged.

Files added:

- `coordination/cloud-workers/u24-worker.sh`: fixed production settings and the final checker pin.
- `research/unit-distance-22/enum/verify-chain-u24.py`: the reviewed lean checker with the four marked U24 edits.
- `research/unit-distance-24/tools/worker.py`: acceptance, prefix binding, measurements, receipts, push retries and guarded cleanup.
- `research/unit-distance-24/tools/known_graphs.py`: pinned dataset, streaming slice control, fleet coverage and self-tests.
- `research/unit-distance-24/tools/checker_diff.py`: the existing lean_diff harness with its pin redirected to lean; exact rule assertions and clean rechecks.
- `research/unit-distance-24/tools/red_controls.py`: deployment mutations in copies, with exact rule assertions and real evidence rechecked after each.
- `research/unit-distance-24/tools/test_worker.py`: acceptance, comparison-error, push-retry, memory-guard and RSS-sampler controls.
- `research/unit-distance-24/WORKER.md`: usage, receipt format, restart behavior and control semantics.
- `research/unit-distance-24/REPORT-worker-2026-10-01.md`: this report.

Checker edits, relative to the pinned lean checker:

| Lines | U24 change |
| --- | --- |
| 2, 3, 4, 5, 6, 7, 9 | Docstring lists the four edits and pins the source. |
| 128 | `UBAR_BUILTIN[24] = 72`, AMP Table 1. |
| 130 | `UBAR_LOWER[24] = 68`, AMP Theorem 1(b). |
| 138 | `PROVED_UPPER[24] = 69`; the value at 23 stays 65. |
| 242, 248, 249, 250, 251, 252, 254, 256, 303 | Scope recorded keys to the run target, preserve the legacy table view through 23, and use that same logic in summary-only mode. |

Final checker SHA256:

```text
a231bfc384702231f57fc21461b4c700ec8eed842bceb981076963c79d2cc86a
```

Compatibility boundary worth reviewing: the producer permits an explicit unused u-bar(24) override on an older target.
Accepting it conflicts with the hard requirement to reproduce lean’s output on every older target.
This implementation preserves lean’s refusal in that case.
Target 24 uses the producer’s complete recorded key set.
The explicit future-override regression is byte-identical to lean.

The Engel induction holds with `max(0,d-1)` in place of `d-1`, as in `reach_table`.
This also covers an isolated vertex.
The parent is an induced faithful unit-distance graph, its edge count obeys u-bar, and its minimum degree obeys the parent cell’s bound.
Canonical deletion therefore reaches a unique level-12 ancestor.
This proves membership in the search tree, without asserting extension to the target.

Tests:

- `DEFAULTS PASS` before and after.
- `RUNBOOK PASS` before and after.
- 749 graph/certificate files byte-identical across the three small-target slices (314, 219, 216).
- All three pairs of reach/config files byte-identical.
- 545 manifests agree after normalizing run paths, timestamps, timing/RSS measurements and dependent manifest hashes (211, 167, 167).
- 24 complete-summary directories compared in five modes: normal, `--check`, `--from-n 14`, both flags, and `--summary-only`.
- All 120 stdout/stderr/status comparisons were byte-identical. Archived/incomplete evidence and historical red fixtures preserve their refusals too.
- `LEAN-DIFF OK: 1 of 1 run directories identical, 7 of 7 planted faults refused by both (identical: 7)`.
- `U24 RED-CONTROLS OK: 12 exact rules asserted; real evidence rechecked after each`.
- `KNOWN-GRAPHS SELF-TEST OK: 7 rule-specific red controls; clean evidence restored after each`.
- A complete synthetic fleet also passes, with every eligible form represented exactly once.
- Worker guard tests pass, including comparison exceptions, incorrect partial verdicts, missing certificate replays, three simulated push attempts with 30-second retry intervals, and the memory cutoff.
- The fallback RSS sampler measured a live 32 MiB allocation; a clean command passed after the simulated low-memory refusal.
- The unchanged lean checker refuses the real n=24 run: `verify-chain.py: Bad('run-config.json target [24, 69] is not a target of the u-bar table')`, exit 2.
- Its `check_ubar` also gives the exact refusal for coverage 0..24 instead of 0..23.
- Summary-only mode with required hashes and G4 accepts the n=24 schema; its only refusal on the single result copy is the missing 1,919 fleet slices.
- Bash syntax and Python compilation checks pass.
- Both checked slice markers skip on restart, with receipt hashes and the checker pin validated.

Pilot measurements (`JOBS=2`, pushes and toolchain installation disabled, 1.5 GiB MemAvailable guard):

| Slice | Runbook wall s | Enumeration s | G4 s | Checker s | Control s | Checker peak MiB | Run directory apparent bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1907 | 1846.378 | 1565 | 270 | 475.888 | 4.506 | 801.12 | 3226087386 |
| 1444 | 444.450 | 385 | 51 | 84.789 | 4.255 | 151.84 | 1553241465 |

Slice 1907 includes 945 seconds to finish the shared prefix, then about 620 seconds above it.
Times are from a shared desktop; some small regression checks ran alongside the initial pilot.
Enumeration and G4 ran once per slice.
The preserved 1907 files were checked again after the final compatibility edit and re-pin.
The table uses that final checker/control measurement and the original runbook/enumeration/G4 measurement.
The initial check took 697.264 seconds, peaked at 820,428 KiB, and also passed.
Its superseded receipts remain in the scratch archive.
Run sizes count every regular-file path plus directory sizes.
They are apparent sizes, including hard-linked prefix files.
No pilot memory cutoff was triggered.

| Slice | Text bytes | Known JSON bytes | Inventory gzip bytes | Total bytes |
| --- | ---: | ---: | ---: | ---: |
| 1907 | 3100 | 10070 | 68899 | 82069 |
| 1444 | 3056 | 10070 | 51526 | 64652 |

Checker and control verdicts:

```text
slice 1907:
COVERAGE exhaustive: all 89 required cells of (24,69) from seed level 10 present and checked, their parent sources exactly as L4 allows, the certificates of all 75 pruned cells replayed (slice 1907 of 1920 at level 12: the fleet needs all 1920 slices)
CHAIN OK
KNOWN-GRAPHS OK: slice 1907 of 1920, 29 cells, 0 Engel forms kept
slice 1444:
COVERAGE partial: levels below 13 not inspected (--from-n 13)
CHAIN PARTIAL (levels below 13 not inspected (--from-n 13))
KNOWN-GRAPHS OK: slice 1444 of 1920, 29 cells, 0 Engel forms kept
```

Exact red-control rules (scratch path components in parser errors are retained in the full log):

- u-bar(24) changed without override: `PROBLEM: reach.json u-bar(24) = 71 is not the built-in 72 and no override is recorded`
- override below the known lower bound: `PROBLEM: reach.json override of u-bar(24) {'builtin': 72, 'value': 67} is not a lowering of 72 to at least the known lower bound 68`
- unjustified root k 6: `PROBLEM: reach.json root k 6 is not justified: Schade's bound is 69 - u-bar(23) = 5, and no lemma is recorded for (24,69)`
- a certificate's g6 changed: `PROBLEM: 20-49.certs.jsonl: record list is not the stage input 20-49.reach.g6`
- a verdict renamed: `PROBLEM: 20-49.certs.jsonl: verdict bogus for SC?@II?_G_@HBHKCI@iAoQg_eg@Oac}??`
- a refuted or tu record's witness removed: `PROBLEM: 20-49.certs.jsonl: pruned graph SC?@II?_G_@HBHKCI@iAoQg_eg@Oac}?? has no witness`
- the certificate file without its final newline: `PROBLEM: required cell (20,49) could not be checked: Bad('/tmp/u24-worker-check-oo1ip077/u24-deployment-red-nkjycc64/dag-24-69-L12-tri-pf74-s1907of1920/20-49.certs.jsonl: missing final newline')`

<details>
<summary>Non-ASCII parser refusal: complete exact line</summary>

- a non-ASCII byte in the certificate file: `PROBLEM: required cell (20,49) could not be checked: UnicodeDecodeError('ascii', b'{\xe9"g6":"SC?@II?_G_@HBHKCI@iAoQg_eg@Oac}??","verdict":"tu","witness":{"tri":{"tree":{"minus":{"minus":{"minus":{"minus":{"leaf":{"cycle_coefficients":[[-15,26],[1,8],[2,16],[-8,9],[1,8],[-19,-6],[10,7],[10,7],[9,-1],[-10,-7],[17,-10],[-8,9]],"cycles":[[0,3,13,9],[1,14,10,15],[2,6,5,17],[2,13,9,18],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"edge":[1,16],"pair":[0,1],"scale":[-9,1],"triangle_coefficients":[[18,-2],[1,8],[-7,17],[19,6]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":0}},"plus":{"leaf":{"cycle_coefficients":[[3,-8],[-8,5],[6,-16],[-11,13],[-3,8],[-5,-3],[5,3],[-11,13],[-5,-3],[3,-8],[8,-5],[-2,-11]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19]],"edge":[9,15],"pair":[5,13],"scale":[-8,5],"triangle_coefficients":[[-13,2],[8,-5],[-13,2],[-13,2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":1}},"split":[2,6,17]},"plus":{"leaf":{"cycle_coefficients":[[-1,1],[-1,0],[0,2],[0,-1],[-1,1],[0,-1],[0,-1],[0,1],[0,1],[0,1]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[5,17,6,19]],"edge":[0,3],"pair":[1,17],"scale":[0,1],"triangle_coefficients":[[-1,1],[-1,0]],"triangles":[[0,8,9],[1,7,15]],"zeta":3}},"split":[1,7,15]},"plus":{"minus":{"leaf":{"cycle_coefficients":[[0,-1],[-1,0],[2,-2],[-1,1],[0,-1],[-1,1],[-1,1],[1,-1],[1,-1],[1,-1]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[5,17,6,19]],"edge":[0,3],"pair":[1,17],"scale":[1,-1],"triangle_coefficients":[[0,-1],[-1,0]],"triangles":[[0,8,9],[1,7,15]],"zeta":3}},"plus":{"minus":{"leaf":{"cycle_coefficients":[[-5,8],[-5,8],[-11,-2],[-5,8],[16,-6],[-8,3],[-8,3],[-8,3],[8,-3],[-5,8]],"cycles":[[0,3,13,9],[1,14,10,15],[2,6,5,17],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19]],"edge":[1,16],"pair":[3,17],"scale":[-3,-5],"triangle_coefficients":[[-5,8],[-5,8],[-5,8],[-13,11]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":2}},"plus":{"minus":{"leaf":{"cycle_coefficients":[[-3,10],[-13,1],[20,-6],[-9,-11],[-1,11],[-10,3],[-3,-2],[-10,18],[-10,-12],[10,-18],[10,-3],[0,15],[19,-7],[-9,9]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[2,13,9,18],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"pair":[0,1],"scale":[-19,27],"triangle_coefficients":[[9,-19],[7,-10],[-22,10],[10,-18],[8,2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17],[2,13,18]]}},"plus":{"leaf":{"cycle_coefficients":[[2,-3],[9,-10],[-14,14],[11,-6],[5,-4],[7,-7],[2,-3],[-2,-4],[16,-10],[2,4],[-7,7],[-9,3],[-9,10],[-3,-6]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[2,13,9,18],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"pair":[0,1],"scale":[-5,-10],"triangle_coefficients":[[7,0],[0,7],[6,-16],[2,4],[8,2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17],[2,13,18]]}},"split":[2,13,18]},"split":[2,6,17]},"split":[1,7,15]},"split":[0,8,9]},"plus":{"minus":{"minus":{"minus":{"minus":{"leaf":{"cycle_coefficients":[[-1,3],[-1,10],[0,-14],[5,6],[1,4],[0,7],[-1,3],[-6,4],[6,10],[6,-4],[0,-7],[-6,-3],[1,-10],[-9,6]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[2,13,9,18],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"pair":[0,1],"scale":[-15,10],"triangle_coefficients":[[7,0],[7,-7],[-10,16],[6,-4],[10,-2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17],[2,13,18]]}},"plus":{"leaf":{"cycle_coefficients":[[7,-10],[-12,-1],[14,6],[-20,11],[10,-11],[-7,-3],[-5,2],[8,-18],[-22,12],[-8,18],[7,3],[15,-15],[12,7],[0,-9]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[2,13,9,18],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"pair":[0,1],"scale":[8,-27],"triangle_coefficients":[[-10,19],[-3,10],[-12,-10],[-8,18],[10,-2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17],[2,13,18]]}},"split":[2,13,18]},"plus":{"leaf":{"cycle_coefficients":[[3,-8],[3,-8],[-13,2],[3,-8],[10,6],[-5,-3],[-5,-3],[-5,-3],[5,3],[3,-8]],"cycles":[[0,3,13,9],[1,14,10,15],[2,6,5,17],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19]],"edge":[1,16],"pair":[3,17],"scale":[-8,5],"triangle_coefficients":[[3,-8],[3,-8],[3,-8],[-2,-11]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":4}},"split":[2,6,17]},"plus":{"leaf":{"cycle_coefficients":[[-1,1],[-1,0],[0,2],[0,-1],[-1,1],[0,-1],[0,-1],[0,1],[0,1],[0,1]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[5,17,6,19]],"edge":[0,3],"pair":[1,17],"scale":[0,1],"triangle_coefficients":[[-1,1],[-1,0]],"triangles":[[0,8,9],[1,7,15]],"zeta":3}},"split":[1,7,15]},"plus":{"minus":{"leaf":{"cycle_coefficients":[[0,-1],[-1,0],[2,-2],[-1,1],[0,-1],[-1,1],[-1,1],[1,-1],[1,-1],[1,-1]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[5,17,6,19]],"edge":[0,3],"pair":[1,17],"scale":[1,-1],"triangle_coefficients":[[0,-1],[-1,0]],"triangles":[[0,8,9],[1,7,15]],"zeta":3}},"plus":{"minus":{"leaf":{"cycle_coefficients":[[-5,8],[-3,-5],[-10,16],[2,-13],[5,-8],[-8,3],[8,-3],[2,-13],[-8,3],[-5,8],[3,5],[-13,11]],"cycles":[[0,3,13,9],[1,14,10,15],[1,7,11,14],[2,6,5,17],[3,10,11,14],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19]],"edge":[9,15],"pair":[5,13],"scale":[-3,-5],"triangle_coefficients":[[-11,-2],[3,5],[-11,-2],[-11,-2]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":5}},"plus":{"leaf":{"cycle_coefficients":[[11,-26],[9,-8],[18,-16],[1,-9],[9,-8],[-25,6],[17,-7],[17,-7],[8,1],[-17,7],[7,10],[1,-9]],"cycles":[[0,3,13,9],[1,14,10,15],[2,6,5,17],[2,13,9,18],[3,10,14,13],[4,12,5,19],[4,16,6,19],[4,11,7,19],[4,12,8,16],[4,11,12,16],[5,17,6,19],[9,13,18,15]],"edge":[1,16],"pair":[0,1],"scale":[-8,-1],"triangle_coefficients":[[16,2],[9,-8],[10,-17],[25,-6]],"triangles":[[0,3,19],[0,8,9],[1,7,15],[2,6,17]],"zeta":0}},"split":[2,6,17]},"split":[1,7,15]},"split":[0,8,9]},"split":[0,3,19]}}}}', 1, 2, 'ordinal not in range(128)')`

</details>

- a keep line dropped: `PROBLEM: 20-49.keep.g6: is not the embedded and unknown records in order`
- a parent source changed: `PROBLEM: 20-49: parent source 19-45.keep.g6 hash differs from the manifest`
- Engel form removed from keep and certificates: `FAIL: PRUNED 16-35: Engel indices in reach but not keep: [0]`
- Later slice prefix: `FAIL: PREFIX: differs: 12-20.g6`.

The later-prefix control changes one payload byte in the retained 1444 run, preserving every newline.
It asserts the exact comparison refusal, restores the byte, and requires the original checker stdout, stderr and status and the original control result.
The full transcript is [later-prefix-red.log](/tmp/u24-worker-check-oo1ip077/later-prefix-red.log).

The known-graph self-test asserts these exact rule texts:

```text
FAIL: REACH 16-35: eligible Engel indices in full but not reach: [0]
FAIL: PRUNED 16-35: Engel indices in reach but not keep: [0]
FAIL: PARTITION 16-35: eligible Engel index 0 kept in slices 0 and 1
FAIL: DUPLICATE SLICE: 0
FAIL: RECEIPT 16-35: dataset pin, count or eligibility differs
FAIL: COMPLETE: 1 of 1920 slices present
FAIL: MISSING 16-35: 124 eligible Engel forms not kept (first indices [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13])
```

The 1907 pilot keeps no Engel form, so the known-graph removal test seeds a declared positive fixture at (16,35), index 0.
The control first accepts it in full/reach/keep, then rejects its removal from keep and certificates at its own PRUNED rule.
The keep-versus-certificate list relation still holds.
The chain checker would additionally detect certificate-to-stage and manifest-hash inconsistencies; removing both files’ records does not evade those rules.
Both the fixture and all other mutations are confined to copies.

Engel coverage (zero-based indices are in each known.json receipt):

| Cell | k | Dataset forms | Eligible | Kept eligible: 1907 | Kept eligible: 1444 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16-35 | 2 | 172 | 124 | 0 | 0 |
| 16-36 | 1 | 12061 | 12058 | 0 | 0 |
| 16-37 | 1 | 1501 | 1500 | 0 | 0 |
| 16-38 | 1 | 119 | 119 | 0 | 0 |
| 16-39 | 0 | 13 | 13 | 0 | 0 |
| 16-40 | 0 | 1 | 1 | 0 | 0 |
| 16-41 | 0 | 1 | 1 | 0 | 0 |
| 17-39 | 2 | 28909 | 27487 | 0 | 0 |
| 17-40 | 1 | 4856 | 4855 | 0 | 0 |
| 17-41 | 1 | 482 | 481 | 0 | 0 |
| 17-42 | 1 | 39 | 39 | 0 | 0 |
| 17-43 | 1 | 6 | 6 | 0 | 0 |
| 18-42 | 2 | 2061 | 1792 | 0 | 0 |
| 18-43 | 2 | 19373 | 18906 | 0 | 0 |
| 18-44 | 2 | 1872 | 1798 | 0 | 0 |
| 18-45 | 1 | 204 | 204 | 0 | 0 |
| 18-46 | 1 | 16 | 16 | 0 | 0 |
| 19-46 | 3 | 51138 | 16196 | 0 | 0 |
| 19-47 | 2 | 8984 | 8779 | 0 | 0 |
| 19-48 | 2 | 823 | 823 | 0 | 0 |
| 19-49 | 2 | 44 | 44 | 0 | 0 |
| 19-50 | 1 | 3 | 3 | 0 | 0 |
| 20-51 | 3 | 3883 | 2248 | 0 | 0 |
| 20-52 | 2 | 296 | 296 | 0 | 0 |
| 20-53 | 2 | 11 | 11 | 0 | 0 |
| 20-54 | 2 | 1 | 1 | 0 | 0 |
| 21-56 | 3 | 102 | 71 | 0 | 0 |
| 21-57 | 2 | 5 | 5 | 0 | 0 |
| 22-60 | 3 | 35 | 35 | 0 | 0 |

Dataset total: 137,011 forms; eligible: 97,912.
Both slices also have zero Engel matches in every full and reach file.
These light slices are deployment checks; the incomplete fleet is not a completeness verdict on missing Engel forms.
Live pushes were not performed; retry and failure behavior was exercised with simulated git calls.

The real two-slice fleet test printed:

```text
KNOWN-GRAPHS OK: 2/1920 slices, 0/97912 eligible forms kept (coverage only; missing forms not judged)
```

Adding `--complete` produced `FAIL: COMPLETE: 2 of 1920 slices present`, plus each cell's missing-form rule.
The test asserted the exact COMPLETE line and then reproduced the original coverage stdout, stderr, status and JSON byte for byte.

Evidence and reruns:

All pilot results, receipts and logs are under `/tmp/u24-worker-check-oo1ip077`.
The retained 1907 run directory is `pilot/out/dag-24-69-L12-tri-pf74-s1907of1920`.
The retained copy of 1444 is `retained-1444`; its manifest paths were rebased for direct rechecking.
The worker deleted the original 1444 run and replay directories after writing passing receipts and a checked marker.
The shared prefix remains.
Both slice markers skip on restart.
The temporary `filter/udtriangle` binary built for the local tests was removed from the worktree.
Rebuild it with `make -C research/unit-distance-22/filter udtriangle` before a new local runbook test.
The retained-directory checker and known-graph controls do not need that prover binary.
The exact source pins, measured times, file digests and whole checker outputs are in `pilot/check/*.txt`.
The final receipts are [slice 1907](/tmp/u24-worker-check-oo1ip077/pilot/check/s1907of1920-u24pilot.txt) and [slice 1444](/tmp/u24-worker-check-oo1ip077/pilot/check/s1444of1920-u24pilot.txt).
The run inventory covers every regular file, including parents, shards, configuration and summary JSON.
Prefix files have the requested count/digest summary; a separate digest binds the files actually shared by PREFIXDIR.

Useful local commands:

```sh
python3 research/unit-distance-24/tools/known_graphs.py --self-test
python3 research/unit-distance-24/tools/test_worker.py
python3 research/unit-distance-24/tools/red_controls.py /tmp/u24-worker-check-oo1ip077/pilot/out/dag-24-69-L12-tri-pf74-s1907of1920 --from-n 20 --out /tmp/u24-worker-check-oo1ip077
python3 research/unit-distance-24/tools/known_graphs.py fleet /tmp/u24-worker-check-oo1ip077/pilot/check/*.known.json
```
