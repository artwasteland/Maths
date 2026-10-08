# u(24) fleet judge — 2026-10-01

Implemented in the detached worktree at `bd1e5bcc1a`. No git command changed
state. No enumeration, cloud worker, certificate replay, or G4 enumeration was
started. The protected checkers, receipt audit, worker and u(23) tools are
unchanged.

## Files and decisions

- `tools/judge.py`: reads extracted worker branches; validates every receipt
  copy; checks fleet agreement, same-worker whole-prefix bindings, G4 scope,
  target survivors, independently predicted Engel membership, summary coverage,
  timings and available resource measurements; writes text and JSON reports.
- `tools/test_judge.py`: builds fleets from both retained receipt formats,
  reseals synthetic mutations, asserts exact semantic failures, and reruns the
  honest fleet after each control. It runs sequentially under the worker's
  1,536 MiB process-group memory guard.
- `WORKER.md`: coordinator invocation and link to this report.
- `REPORT-judge-2026-10-01.md`: fetch/run procedure, exact controls, measured
  validation results and the full honest output.

`receipt_audit.prepare()` checks each copy and supplies the checker's
`history/INDEX.json` interface. Its existing G4 checks call the reviewed u(23)
`target_check.replay_scope()` and pinned sampling policy. The judge uses
u(23)'s `aggregate_fleet.compare_copies()` for count/hash/target disagreement,
and `fleet_status.slice_record()` for the plan's timing definition. Count keys
are normalized before comparison, so JSON key order is immaterial.

Every text receipt is audited, even when another copy of its slice passes.
A rejected receipt makes the verdict FAIL. Result-only pushes and incomplete
bundles without a text receipt are pending. All accepted copies participate in
comparison and the summary audit; one copy per slice goes to the existing
`known_graphs.fleet_control()`. The locally computed `known_slices.run()` map
checks every accepted copy, so a missing predicted graph fails even in a pilot.
No worker-supplied prediction file or cached pass label is used.

For summary auditing, the only suppressed problem is the precisely matched
absence of the other `1920 - accepted_slice_count` slices. The checker exit,
JSON totals, number of fleets and coverage output are reconciled; all other
problems fail, and every unresolved record makes the judge PARTIAL. When all
1,920 are present, nothing is suppressed and `COVERAGE (summary only) OK` is
required. The raw checker output and exit status remain in the JSON report.

Targets are read directly from `24-69.keep.g6`, including pending or rejected
copies. Reports distinguish their acceptance status. A survivor needs its own
refutation; its existence does not make the run fail. Contradictory zero counts
do fail, without concealing the graph. `JUDGE OK` concerns the declared plan's
evidence, not all the mathematical gates for u(24).

## Fetch and run on the pilot

These are commands for the coordinator to execute in its repository, **not
commands run during this build**. Each branch has its own local ref, and the
archive uses a resolved commit. No command reads or writes `FETCH_HEAD`.
The new extraction root is an immutable snapshot while the judge runs; use a
new root for the next fetch rather than updating a tree under a running judge.

```bash
set -euo pipefail
fleet_root=$(mktemp -d /tmp/u24-fleet.XXXXXX)
printf 'Fleet snapshot: %s\n' "$fleet_root"
sub=research/unit-distance-24/results/u24
branch_prefix=claude/answering-alexeev-u22-cloud-u24-
git ls-remote --heads origin \
  'refs/heads/claude/answering-alexeev-u22-cloud-u24-u[0-9][0-9]*' \
  > "$fleet_root.remote-heads"
while read -r advertised remote_ref; do
  branch=${remote_ref#refs/heads/}
  suffix=${branch#"$branch_prefix"}
  local_ref="refs/u24judge/$suffix"
  git fetch --no-write-fetch-head -q origin "+$remote_ref:$local_ref"
  commit=$(git rev-parse "$local_ref")
  mkdir -p "$fleet_root/$suffix"
  if git cat-file -e "$commit:$sub" 2>/dev/null; then
    git archive "$commit" "$sub" | tar -x -C "$fleet_root/$suffix"
  fi
  printf '%s\t%s\t%s\n' "$branch" "$commit" "$advertised" >> "$fleet_root.sources.tsv"
done < "$fleet_root.remote-heads"

~/tools/pyenv-maths/bin/python -B research/unit-distance-24/tools/judge.py \
  "$fleet_root" --plan coordination/cloud-workers/u24-pilot-plan.json \
  --out "$fleet_root.judge.json" > "$fleet_root.judge.txt"
```

Under `set -e`, a partial verdict exits the shell with status 3; its text/JSON
reports are still written. The judge needs the repository's pinned Engel data
and Python with pynauty. It computes the prediction once per invocation. All
substantive work runs sequentially; the CLI also uses the 1,536 MiB memory guard.

The pilot's supplied plan is used unchanged. A whole-fleet plan must declare
`"all": true`, `"target": [24,69]`, `"slice_level": 12`, `"count": 1920`, and a
`"tasks"` object assigning every index 0..1919 once. A smaller control plan uses
`"slices": [1907,1444]` and matching tasks instead. Coverage is declared
separately from assignment, so deleting an assignment cannot silently shrink
the intended plan. All branch suffixes/reruns are collected, not just one branch
per tag. The whole fleet and subset plans use the published pilot cost sample;
a plan declaring its own ten-heavy/32-random sample uses that sample after
validation of its random draw.

## Cost and resource interpretation

The primary estimate follows the plan exactly:

```
T24 = T23 + sum_heavy(t24 - t23) + (1910/32) * sum_random(t24 - t23)
```

Both sides use the unchanged `fleet_status.slice_record` rule: above level 12,
for every non-resumed cell and prune step, sum
`max(longest shard, sum(shards)/4) + prune step + stage verification`.
The divisor remains four on both sides, including a pilot worker using JOBS=2.
The (23,65) baseline is the committed `result-inputs/aggregate.json`:
1,304,030.4 seconds by this rule.

A second, explicitly labelled wall-clock estimate applies the same formula to
the run-dag2 receipt/fingerprint wall clocks on both sides. Its T23 is
1,468,404 seconds. These clocks include startup/prefix work, and after a restart
cover only the last session. They are summed slice wall seconds, not a fleet's
elapsed makespan or CPU seconds.

Unfinished and resumed timings are lower bounds. An absent sample contributes
`t24 = 0` but still subtracts its entire `t23`; the denominator stays 32. Thus
the partial figures bound the stated estimator, not the cost of the unsampled
fleet. They are not completed pilot estimates. G4, checker, control and evidence
audit seconds are projected separately with weights 1 and 1910/32. The report
shows `(run + G4 + checker + control) / run` on paired observations and, when
complete, on the projected totals. Evidence-audit cost is additional and shown
separately. A ratio of lower bounds is never labelled a multiplier bound.

Duplicate timing copies are not summed. Selection prefers an accepted complete
timing, then the strongest recorded step lower bound, with the receipt path as
the deterministic tie-breaker. Every copy's timing and provenance remains in
JSON. The output ranks slices by recorded run-dag2 wall time.

The existing receipts measure **checker peak RSS**, and an inventory of logical
file bytes at checking time. They do **not** record a run-wide memory peak or a
disk peak. The judge reports these as unavailable, and labels the inventory
sum `disk-at-check`, a lower bound on peak logical file bytes. It does not
invent the missing measurements. Checker/control/evidence RSS measurements
that actually exist are preserved per copy in JSON.

## Validation

The honest fleet combines `/tmp/u24-fixes-yE1TRr/worker/res` (legacy receipts)
and `/tmp/u24-rereview-fixes-xJ9521/fresh-whole/res` (expanded receipts), as two
branch trees with a two-slice plan. Both contain slices 1907 and 1444, hence
four accepted copies and two duplicates. The real summary checker is used.
Neither slice has an eligible Engel graph predicted for it. The independent
map also checks the pilot total of 82,582 and the complete total of 97,912,
with every eligible graph placed exactly once.

Run the repeatable controls with:

```sh
~/tools/pyenv-maths/bin/python -B research/unit-distance-24/tools/test_judge.py \
  --out /tmp/u24-judge-controls-new
```

## Exact controls

The plan-coverage control removes an assignment while retaining the declared
slice set. This is a contradiction. Removing fetched evidence instead gives
PARTIAL, as required by the verdict definition. An additional pending copy also
remains unresolved when another copy of that slice is already accepted.

```text
PLAN: tasks do not cover the declared slices exactly once; missing [1444], extra []
COVERAGE: slice 1444: no accepted copy
PENDING: slice 1444: result pushed without receipts (legacy/research/unit-distance-24/results/u24/24-69-L12-tri-pf74/s1444of1920)
```

The disagreeing-copy control changes an upper cell's `tri_silent_passes` count
consistently in the raw summary, exported summary and counts table, and updates
their inventory/retained/envelope bindings. Both copies are accepted by the real
receipt audit. The fleet comparison alone rejects their disagreement:

```text
COPIES: slice 1444: accepted copies disagree on counts (expanded/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt, legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)
```

The binding control supplies a valid whole receipt under worker `borrowed` and
binds `fixcheck`'s later slice to it. Recursive receipt auditing succeeds; the
additional same-worker rule fails:

```text
REJECTED: slice 1444: PREFIX: slice 1444: later slice is not bound to a whole check of worker fixcheck (legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)
```

The predicted-membership control relabels the whole 1907 evidence as slice 261,
including the configuration, checker identity, manifests, replay records and
their bindings. Its synthetic G4 red-control indices are drawn under the new
run identity, so the G4 scope remains valid. The actual receipt audit accepts
it. The local, unmodified predictor assigns precisely one eligible form to 261;
this synthetic slice contains none. Its sole fleet problem is:

```text
KNOWN: slice 261: missing predicted Engel graph (16,35) #84
```

The reused fleet-control partition boundary is tested separately from the
predicted-location rule, using two typed synthetic known receipts made from the
retained ones. Its exact refusal is:

```text
PARTITION 16-35: eligible Engel index 84 kept in slices 1907 and 1444
```

The false-zero control puts the nonempty order-24 fixture in the retained keep
file, refreshes the content hashes and all receipt envelopes, and leaves the
record count zero. The rejection is the semantic count check, not a broken
hash envelope. The test independently asserts that the graph itself appears in
the survivor report; merely returning failure would not pass this control.

```text
REJECTED: slice 1444: COUNTS: inventory 24-69.keep.g6 records: metadata 0 != checked files 1 (legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)
SURVIVOR: slices [1444]: W`Uw?C??G@_E?J?F_Xw@wGKABBAE?HO?oo?Xoo?eE?Cb_@K (needs refutation; unaccepted evidence)
```

After every control the complete honest judgement is rerun and required to
equal its original report, including verdict, accepted copies, summary results
and costs. Further checks verify the lower-bound estimator arithmetic, the
1910/32 overhead weight, and the actual CLI parser/JSON writer/final verdict for
exits 0, 3 and 1. The full 1,920-slice mathematical fleet is not available on
this machine; the real summary integration is tested on all four honest copies.

## Final run and honest output

The final controls and JSON reports are retained under
`/tmp/u24-judge-controls-final/`. The suite passed eight exact controls,
rechecked the honest fleet after each, and verified CLI returns 0, 3 and 1.
It took 317.280 seconds and peaked at 197,276 KiB RSS;
no memory stop occurred. Substantive processes ran sequentially. Syntax checks
and `git diff --check` passed.

A final standalone guarded CLI run from `/tmp/u24-judge-controls-final`, using
relative `honest`, `plan.json` and output paths, also returned `JUDGE OK`. Its
JSON and text matched the honest report. This exercises the guarded launcher's
path normalization when the caller is outside the repository. A standalone
bad-plan check also verified exit 1 and replacement of an older OK JSON report
with a FAIL report, so a failed refresh cannot leave a stale success behind.

The honest output is reproduced below. These two slices are outside the
published ten-heavy/32-random pilot sample: their observed costs are real,
but the pilot projections remain lower bounds with **no pilot timings yet**.

```text
FLEET: 2/2 planned slices accepted; 4 accepted copies; 2 duplicated slices; 0 rejected copies
PREFIX: 70 prefix files compared; whole-check bindings checked per worker
G4: PASS 4
KNOWN: predicted 0 for plan, 0 for accepted slices; 97912 eligible in whole fleet
SUMMARY: per-slice OK; 1918 of 1920 slices absent
TARGET: 0 distinct graph6 survivors measured from retained 24-69.keep.g6 files
DUPLICATE: slice 1444: expanded/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt, legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt
DUPLICATE: slice 1907: expanded/research/unit-distance-24/results/u24/check/s1907of1920-fixcheck.txt, legacy/research/unit-distance-24/results/u24/check/s1907of1920-fixcheck.txt
COST definition: fleet_status.py slice_record: per cell above the slice level not resumed (neither the cell nor its prune step), max(longest shard, shards summed / 4) + prune step + stage verification
COST wall definition: run-dag2 wall clocks on both targets; last session only after restart
COST sample: 0/10 heavy, 0/32 random; random weight 1910/32 = 59.6875
COST step LOWER BOUND: T23 1304030.400 + heavy delta -84052.700 + weighted random delta -1072363.531 = T24 147614.169 s (41.004 h)
COST wall LOWER BOUND: T23 1468404.000 + heavy delta -88923.000 + weighted random delta -1190288.125 = T24 189192.875 s (52.554 h)
COST observed: step 832.200 s, run_dag2 1950.000 s, g4 321.000 s, check 889.618 s, control 17.024 s, evidence 123.402 s
COST projected overhead LOWER BOUNDS: g4 0.000 s, check 0.000 s, control 0.000 s, evidence 0.000 s
COST (run+G4+check+control)/run: observed 1.629560x over 2 paired slices
COST projected total wall: 189192.875 s; multiplier pending (a ratio of lower bounds is not a bound)
COST slice 1444: step 281.200 s lower-bound; run 385.000 s; G4 51.000 s; check 122.327 s; control 8.262 s; checker RSS 155656.000 KiB; disk-at-check 1552618021.000 bytes; run RSS/disk peaks unavailable
COST baseline slice 1444: t23 step 209.400 s, wall 228.000 s; deltas step 71.800 s, wall 157.000 s; outside sample
COST slice 1907: step 551.000 s; run 1565.000 s; G4 270.000 s; check 767.291 s; control 8.762 s; checker RSS 820612.000 KiB; disk-at-check 3225350433.000 bytes; run RSS/disk peaks unavailable
COST baseline slice 1907: t23 step 204.500 s, wall 218.000 s; deltas step 346.500 s, wall 1347.000 s; outside sample
COST longest by recorded run wall: s1907 1565 s, s1444 385 s
COST note: Unfinished/resumed slices are lower bounds; missing t24 is zero, with its full t23 still subtracted. These bound the estimator, not the actual unsampled fleet cost.
COST note: Overheads use weight 1 for heavy and 1910/32 for random; evidence audit is shown separately from G4+check+control.
COST note: Receipts do not measure run-wide RSS or disk peaks. Disk-at-check is a lower bound on peak logical file bytes, not allocated blocks.
JUDGE OK
```
