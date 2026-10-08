# Checked worker for (24,69)

Run from the repository:

```sh
TAG=u01 JOBS=2 bash coordination/cloud-workers/u24-worker.sh 1907 1444
```

The launcher fixes the production settings, including both justified u-bar
overrides, triangle pruning, the set-74 prune filter, stage verification,
level-12 slicing into 1,920 parts and G4 fraction 0.002.
The runbook has cleanup disabled.
The launcher pins `verify-chain-u24.py` by its full SHA256.
The pin remains `a231bfc384702231f57fc21461b4c700ec8eed842bceb981076963c79d2cc86a`.
The review fixes do not change the checker or this pin.
It leaves the three older checkers and all u(23) runbooks unchanged.

Historical targets through 23 keep the reviewed checker's table view and diagnostics.
This includes its refusal of an explicit u-bar(24) override on an older target.
The producer can record that unused future override, so accepting it would conflict
with the requested byte-for-byte compatibility.
For target 24 the checker uses the producer's full recorded key set.

Local defaults are `U23_PUSH=0` and `U23_TOOLCHAIN=0`.
Cloud workers set both to 1.
`PY` defaults locally to `~/tools/pyenv-maths/bin/python`, which needs pynauty for G4.
The runbook performs its existing binary, data, checker and replay self-checks.

Paths may be changed with these environment variables:

| Variable | Default |
| --- | --- |
| `U23_OUT` | `research/unit-distance-24/enum/out-cloud` |
| `U23_RES` | `research/unit-distance-24/results/u24` |
| `U24_CHECK_RES` | `$U23_RES/check` |

Use an independent output directory per worker.
The first complete slice makes the runbook's `PREFIXDIR`.
That slice must pass the whole checker with `COVERAGE exhaustive` and `CHAIN OK`.
It must also pass G4 in full mode, including the shared prefix, every level-10 seed
recomputed in full and red controls whose recorded outcomes establish rejection.
Each later slice must have exactly the `--from-n 13` partial verdict and no `PROBLEM` line.
Every inspected pruned cell must have its certificates replayed.
The prefix comparison must finish successfully and report `identical`.
A digest saved after the whole check also binds the current prefix to that check.
This detects changes to a shared inode even when both comparison paths change together.

Each slice writes four receipts named `s<i>of1920-<TAG>`:

| Suffix | Contents |
| --- | --- |
| `.txt` | Pins, measured wall times and checker RSS, SHA256 of the other three receipts, file-derived target counts, result snapshot, checker output, control output, evidence audit output and worker verdict |
| `.known.json` | Pinned Engel files, eligible counts, all 87 required stage files with actual record counts and matched zero-based Engel line indices |
| `.inventory.jsonl.gz` | Every regular file: relative path, bytes, SHA256 and newline count; also a count/digest summary for prefix files |
| `.structure.json` | Count reconciliation, SHA256 and counts of the target files, hashes of every retained result file, normalized summary, checked augmentation and shard manifest text and SHA256, G4 evidence and the whole prefix receipt's binding |

The inventory visits subdirectories too, including parents and shards.
Its prefix digest hashes sorted `relative-path sha256\n` lines.
Level-12 files containing `.slice-` are specific to the slice and remain explicit.
Files without a level, including configuration and summary JSON, remain explicit.
The receipt also records a separate digest of the top-level files actually shared by `PREFIXDIR`.
The first slice can have additional prefix parents and shards that later slices do not need.
Those are included in its prefix inventory summary.
The runbook's result digest uses its own `hashes.json` selection.
The worker checks every selected hash and record count against the run's bytes.
The required cells come from the independently derived reach table. Their required reach, prune and verification records come from the configuration; an omitted record fails before reconciliation.
Every summary cell's children, reach, prune, parent, shard and stage-verification counts are reconciled with their files.
Each reach record's integer `k`, including seed and resumed records, must equal the
configuration-derived table. Augmentation thresholds and parent-stage identities,
prune input filenames and verification stage kinds must also match that derivation.
Certificate verdicts distinguish native TU/refutation counts from triangle or rhombus counts.
Silent-pass statistics come from the prover's per-part diagnostic files; the whole prefix receipt preserves those already checked for later slices.
The target's full, reach, keep, certificate and UNKNOWN file counts are measured from files and written into both the text and structure receipts.
The coordinator reads the retained target keep file to measure survivors. It reconstructs the target reach input from the certificates, since the runbook does not copy `.reach.g6`, and reconciles summary, hash, structure and inventory counts with those bytes.
An essential target file omitted by the runbook's size limit prevents worker acceptance and deletion, so the evidence remains available for recovery before the coordinator reports survivors.

The retained set follows the runbook exactly: `run-summary.json`, `run-config.json`, `reach.json`, `hashes.json`, `counts.json`, all `verify/*.verify.manifest.json`, and the target and preceding level's files with suffixes `.g6`, `.keep.g6`, `.certs.jsonl`, `.UNKNOWN.g6`, `.manifest.json`, `.prune.manifest.json` when smaller than 4,000,000 bytes.
Every copied file must exist and match its source SHA256, including certificates.
`hashes.json` and `counts.json` are validated against their source records.
Replay evidence is checked separately and its files are included in the structure receipt's retained-file hashes.
With pushes enabled, the worker reads the committed result blobs and verifies their hashes before accepting and again before deletion.

G4 requires `replay/summary.json` and derives PASS or EMPTY from its detail records using the reviewed checker's verdict routine.
There must be zero mismatching parents and a positive sampled-parent count unless the slice satisfies EMPTY's rules.
The fraction must be 0.002.
The worker recomputes the fingerprint from the checked manifests, replay tools and settings.
Both worker and receipt audit require exactly the populated cells prescribed by that mode and their prescribed sample sizes. They reuse the u(23) fleet judge's `replay_scope()` and pinned `sample_indices()` implementation, including its seed, stage and red-control checks, at fraction 0.002.
The whole or partial check determines the required mode, independently of the replay's
label. A later slice requires slice mode and the same prefix fingerprint as its bound,
accepted full-mode replay. The receipt audit recursively checks the whole bundle;
the standalone evidence command also audits that bundle before using it as an anchor.

For resumed cells the worker exports parent sources, parent counts and shard records from the checked manifests.
The export includes the original manifest text and its SHA256.
Later slices inherit their prefix structure only from a bound whole-check receipt.
Missing export evidence fails acceptance and retains the run.
The source `run-summary.json` stays unchanged.
To prepare a retained result for the existing fleet summary audit:

```sh
python3 research/unit-distance-24/tools/receipt_audit.py RESULT CHECK/s1444of1920-u01.txt --out NEW_AUDIT_DIRECTORY
python3 research/unit-distance-22/enum/verify-chain-u24.py --summary-only NEW_AUDIT_DIRECTORY --require-hashes --require-g4
```

`receipt_audit.py` validates the four receipts and retained bytes, then puts the exported summary into the staged copy's `history/INDEX.json` interface.
It derives the mandatory retained set from the copy policy and inventory, re-derives exported resume structure from the preserved manifests and file measurements, and refuses missing or untyped inventory rows.
Honest `ccfce9dc5f` receipts remain supported: their prefix measurements are in `file_counts` and the bound whole receipt, and their preserved manifest text covers resumed cells. New receipts keep prefix inventory rows and all checked augmentation manifests explicitly.
Pass every staged slice directory to the fleet audit for its complete-run verdict.

The coordinator can judge all fetched branch trees together, including duplicate
copies, with the maths Python (pynauty is needed for the independent Engel slice
prediction):

```sh
~/tools/pyenv-maths/bin/python tools/judge.py FLEET_ROOT \
  --plan ../../coordination/cloud-workers/u24-pilot-plan.json --out /tmp/u24-judge.json
```

Here the working directory is `research/unit-distance-24`. Each directory under
`FLEET_ROOT` contains an extracted branch's `research/unit-distance-24/results/u24`
tree. `JUDGE OK`, `JUDGE PARTIAL`, and `JUDGE FAIL` exit 0, 3, and 1. An OK verdict
is for the plan's evidence; retained target survivors are listed for separate
refutation. The judge stages receipts through the history interface itself and
runs the summary audit, retaining every diagnostic except the exact expected
absence of unjudged slices. It stops below 1,536 MiB available memory.
See [the judge report](REPORT-judge-2026-10-01.md) for safe fetch commands, the
full-plan schema, timing definitions and executable controls.

With pushes enabled, the runbook pushes the small result copy first.
The worker commits only its four receipt paths and tries the push three times, 30 seconds apart.
A failure to push either the result copy or receipt retains the run directory.
Only passing checks, a passing control and a successful push authorize a checked marker and deletion.
With pushes disabled, successfully writing the receipts replaces the push requirement.
The run and `.replay` directories are deleted; the shared prefix, markers, results and logs remain.
A v2 checked marker skips a slice on restart only after all four receipt hashes, the checker pin, the requested slice identity and the receipts' accepted verdicts validate.
New markers record the SHA256 of the running worker and evidence module, and the
retained result path. Both code hashes must match the running versions; absent or
different hashes require the current receipt audit to accept the bound bundle first.
This applies to both completed-slice and whole-prefix markers. Honest older bundles
remain accepted without rewriting their receipts or markers. A source change during
a running check prevents marker creation and deletion.
Old three-receipt markers require a fresh evidence check.
The runbook resumes incomplete slices itself.

Exit statuses are 0 for success, 7 for a failed check/control, 8 for a failed commit/push,
2 for a precondition or receipt-writing error, or the runbook's own status when it fails.
A killed checker is a failed check, with no fallback.
`/usr/bin/time -v` measures the checker when available.
Otherwise a 250 ms process-group RSS sampler supplies the peak measurement.

For deployment controls, `U24_KEEP_RUNS=1` retains passing evidence.
`U24_SKIP_RUNBOOK=1` checks existing evidence without letting resume repair a planted fault.
It requires `U24_KEEP_RUNS=1` and refuses otherwise before starting any child process.
Its receipt says the result push was skipped, and its marker cannot replace a production runbook pass.
Neither option relaxes the count, retention, structure, G4 or certificate checks.
`U24_MIN_AVAILABLE_MB=1536` stops the running process group if Linux `MemAvailable` falls below 1.5 GiB.
The pilot uses that guard and `JOBS=2`.

The known-graph control can also be run directly:

```sh
python3 research/unit-distance-24/tools/known_graphs.py slice RUN --out known.json
python3 research/unit-distance-24/tools/known_graphs.py fleet check/*.known.json
python3 research/unit-distance-24/tools/known_graphs.py fleet check/*.known.json --complete
python3 research/unit-distance-24/tools/known_graphs.py --self-test
```

Slice mode requires and streams every full, reach and keep file of every production Engel cell.
Empty files are legitimate; absent files fail.
Its output and JSON report how many records each file supplied.
It fails when an eligible form in full is absent from reach, or a form in reach is absent from keep.
Fleet mode rechecks the recorded soundness relations and dataset pins.
It rejects a repeated slice or an eligible kept form assigned to two slices.
Without `--complete`, missing forms are coverage information.
With `--complete`, all 1,920 slice identities and every eligible form are required.
The production table is derived independently inside the control; receipts cannot change eligibility.

The Engel induction is in `tools/known_graphs.py`'s docstring.
The bound is `max(0,d-1)`, as in `reach_table`, to cover isolated vertices too.
Eligibility guarantees membership in this search tree, not extension to a graph at the target.
The control is additional evidence alongside the chain checker and G4.

`known_slices.py` validates the production (24,69) reach table and uses `known_graphs.py`'s pinned catalogue.
Faithfulness is inherited by induced subgraphs.

The regression and deployment harnesses are `tools/checker_diff.py`,
`tools/test_worker.py`, `tools/red_controls.py`, `tools/review_controls.py`,
`tools/rereview_controls.py`, `tools/review3_controls.py` and `tools/test_certificate24.py`.
The first wraps the existing `lean_diff.py` without altering its pin.
Every planted fault asserts the exact rule text and rechecks unchanged evidence.
The push guard test simulates git calls; it performs no git mutation.
The order-24 fixture has a nonempty TU certificate and tests the chain-level refusal at target (24,68).
It constructs a tiny synthetic chain and starts no enumeration.
