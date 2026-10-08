The patch updates `research/unit-distance-24/tools/judge.py` and adds
`research/unit-distance-24/tools/test_judge_plans.py`. The plan files are unchanged.

`plan_owners()` reconstructs ownership from current tasks, every `pruned.removed`
table, and each move's receiving tag. A move already listed in the receiver's
tasks is counted once. Conflicting owners and duplicate task/pruning assignments
are rejected. Coverage is still checked against a separate declaration, so
removing an assignment cannot silently reduce the required coverage.

The published full-plan schema declares phase A as the complement of the pilot
and held phase B. Validation checks the 42/1,841/37 partition, compares the full
plan's pilot declaration with the reconstructed published pilot, and requires
phase A's reconstructed assignments to cover its complement exactly. The
current full plan therefore judges 1,841 assigned slices; phase B remains held.

The repro schema uses its integer `seed`, the reproducible 48-slice draw from
`range(1920)`, and disjoint `chosen.heavy` indices. It no longer enters the pilot's
ten-heavy/32-random estimator schema. Regrouped tasks r01 through r04 cover all
50 declared repro slices.

Receipts must belong to the reconstructed owner before entering acceptance or
the timing sample. Repro judging additionally admits the owners reconstructed
from the published pilot and full plans, and requires an accepted main copy and
an accepted repro copy for every sampled slice. Two receipts from the same role
cannot satisfy that requirement. The existing comparisons still check all
accepted copies; missing evidence remains PARTIAL (exit 3), and rejection or
disagreement remains FAIL (exit 1). Target survivors are still read before a
receipt can be rejected.

The cost estimator and its weights are unchanged. Its pilot validation now
recovers all 42 slices, including the 23 pruned slices. Imports of the unavailable
u(23) support modules were moved into the functions that use them, allowing plan
validation in this slim snapshot without weakening receipt checks.

Direct validation of the three actual JSON files, without mocks, passed:

```text
coordination/cloud-workers/u24-pilot-plan.json: PLAN OK (42 slices)
coordination/cloud-workers/u24-full-plan.json: PLAN OK (1841 slices)
coordination/cloud-workers/u24-repro-plan.json: PLAN OK (50 slices)
PARTITION OK: 42 pilot + 1841 phase A + 37 phase B = 1920, disjoint
```

Reproduce that validation from the repository root:

```bash
python3 -B - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('research/unit-distance-24/tools').resolve()))
import judge
coverage = {}
for name in ('pilot', 'full', 'repro'):
    path = Path(f'coordination/cloud-workers/u24-{name}-plan.json')
    coverage[name] = set(judge.plan_check(judge.evidence.load(path)))
    print(f'{path}: PLAN OK ({len(coverage[name])} slices)')
held = set(judge.evidence.load(judge.FULL)['phase_b']['slices'])
p, a = coverage['pilot'], coverage['full']
assert not (p & a or p & held or a & held)
assert p | a | held == set(range(1920))
print('PARTITION OK: 42 pilot + 1841 phase A + 37 phase B = 1920, disjoint')
PY
```

The regression command passed all 18 tests:

```bash
python3 -B -m unittest discover -s research/unit-distance-24/tools -p test_judge_plans.py -v
```

The required negative controls cover missing task/pruning assignments, duplicate
ownership, one-copy repro evidence (50 accepted copies still yields PARTIAL),
and receipts from a non-owning tag (FAIL, excluded from acceptance and cost).
Additional controls cover moved donors, invalid repro seeds/draws, overlapping
partitions, two copies from the same role, rejected second copies, and matching
versus disagreeing main/repro pairs. The complete pilot cost control measures
all ten heavy and 32 random slices with the existing estimator. `git diff
--check` also passed.

The judge-flow tests use synthetic audited copies, a synthetic baseline, and
mocked external receipt/graph audits, hashes, timings, and the absent u(23)
comparison dependency. They exercise the real plan checks, discovery, ownership
and repro gates, target-file comparison, and cost estimator. The original
retained-receipt integration suite could not run: this snapshot lacks the
u(23) support modules/baseline, retained fleet fixtures, and pynauty. No claim of
full receipt verification is made.

Repro slice 1270 belongs to held phase B and currently has no assigned main-run
owner. Its plan validates, but its evidence must remain pending until a main
assignment and accepted main copy exist; an arbitrary tag cannot fill that role.

## Follow-up 2

Implemented the additional copy-handling rules in `judge.py` and expanded
`test_judge_plans.py`. Coverage reconstruction, current ownership, repro's two
required roles, and the existing receipt audits remain in force.

`superseded` records are validated for slice, tag, SHA256/null and a nonempty
reason. At judgement, every record must match exactly one discovered copy by
slice, tag and the actual text receipt hash. Missing or ambiguous matches and
duplicate records raise a PLAN error. A matched text receipt must have exactly
one worker verdict, `FAIL`; a passing, missing or contradictory verdict cannot
be superseded. A copy without a text receipt can use a null hash. A bare result
directory has discovered tag `None`, so its record must use both `"tag": null`
and `"receipt_sha256": null`; null is an exact match, not a wildcard. An
incomplete named receipt bundle retains the tag from its filename.

Matched copies are listed under `superseded` with their reason, hash and source
path, and contribute neither rejection, pending evidence nor cost. They never
remove a coverage obligation: without an accepted current-owner replacement,
the slice is still missing and the verdict is PARTIAL.
Supersession records from the other published plans also apply to the mixed
ROOT and undergo the same exact-match checks. This prevents a full-plan copy
explicitly retired under v19 from becoming an unknown-owner failure when judging
the pilot or repro. The selected plan replaces the published version of its own
job, including its supersession records.

Bare result directories become informational `unreceipted` entries when the
selected plan has an accepted copy of the same slice. Otherwise they remain
pending for planned slices. Incomplete bundles with a known tag still require
a receipt unless explicitly superseded or foreign. Bare directories outside
the selected coverage retain their lack of a coverage obligation.

The three published plans supply foreign ownership by **slice and tag**.
Copies belonging to another plan appear under `foreign` and enter neither
acceptance nor cost; they cannot fill a missing current-owner copy. An amended
selected plan takes precedence over its published version, so a former owner
of that same plan does not acquire a foreign exemption. Unknown owners still
fail. Discovery now also retains copies outside the selected coverage, allowing
foreign copies and their target survivors to be reported across the full ROOT.

All copies still pass through the real target-record reader, including
superseded, foreign and unreceipted copies. If slice i has accepted evidence,
each graph in a non-accepted copy of i must occur in accepted evidence for i.
A survivor found only in a non-accepted copy causes
`TARGET: survivor in a non-accepted copy only` and FAIL. An accepted graph in
another slice does not satisfy this condition. Without an accepted replacement,
the survivor remains visible in both JSON and text while coverage stays pending.

The report now includes `resumed_copies` and the distinct sorted
`resumed_slices`, counted from nonempty `recovered_cells` in the structure
receipts of accepted copies. The text renderer prints this information and the
three copy classifications. The resumed count does not alter the verdict.

Validation after this follow-up:

```text
python3 -B -m unittest discover -s research/unit-distance-24/tools -p test_judge_plans.py -v
Ran 36 tests
OK

coordination/cloud-workers/u24-pilot-plan.json: PLAN OK (42 slices)
coordination/cloud-workers/u24-full-plan.json: PLAN OK (1841 slices)
coordination/cloud-workers/u24-repro-plan.json: PLAN OK (50 slices)
PARTITION OK: 42 pilot + 1841 phase A + 37 phase B = 1920, disjoint
```

The 18 additional tests cover supersession schema, exact matching and ambiguity,
passing receipts that must not be superseded, replacement coverage, missing
receipts, foreign ownership and cost exclusion, resumed counts, and survivor
preservation. Survivor controls read the real graph in
`research/unit-distance-24/fixtures/nonempty24/24-69.g6`, and supersession tests
hash real receipt bytes. The receipt/graph-audit integration limitations noted
above still apply; the full retained-receipt suite is unavailable in this snapshot.
The mixed-ROOT control amends phase A's ownership of slice 49 in memory and
verifies that its superseded v19 receipt and foreign replacement do not block
the pilot's accepted evidence.

Worked **WRONG** example: insert just `continue` immediately after the
superseded report entry:

```python
if number_ in supersessions:
    superseded.append(dict(supersessions[number_], copy=c["worker"]))
    continue  # WRONG: skips adding this copy's target records to survivors.
```

Although `target_records()` already read the graph, this one-line change bypasses
the later survivor collection. A superseded failed copy containing the fixture
graph, followed by an accepted empty replacement of the same slice, incorrectly
produces OK and hides the graph. I executed this mutation in memory only:
`JudgeFlowTests.test_superseded_only_survivor_is_fail` went red with
`AssertionError: ('OK', 0) != ('FAIL', 1)`. The correct implementation returns
FAIL, preserves the graph in the report, and passes once the replacement also
contains it. The mutation was not written to disk.

## Follow-up 3

Added `rerun` and `validation` handling in `judge.py`, with 16 new tests in
`test_judge_plans.py`. The supplied chained-move implementation and its three
regression tests are preserved. The test file's direct entry point now follows
all test classes, so direct execution also includes the chained-move tests.

`rerun` transfers ownership after tasks, pruning and all moves, including chained
moves. The source must be the current owner, the destination must be different,
and each slice may have only one rerun declaration. Slice indices, tags and
nonempty reasons are checked. This works whether the old ownership came from a
task, a pruned record or a move, without changing the declared coverage.

Every discovered copy with the rerun's old `(slice, tag)` is automatically listed
under `superseded`, with the reason, destination and receipt hash when present.
Both PASS and FAIL receipts are retired, and multiple old branches are allowed.
No old copy is required to exist before declaring a rerun. These copies cannot
fill coverage, repro roles or the cost sample. The exact-hash, FAIL-only rules
for the separate manual `superseded` field are unchanged.

Old receipts still undergo target-record reading. For comparisons, an old copy
is considered `accepted_looking` only if it passes receipt preparation and
`accepted_copy()`; a PASS label alone is insufficient. Its audit failure, if any,
is recorded on its superseded entry. An old copy that passes these checks is
compared with every accepted copy from the rerun's new owner using the existing
duplicate comparator, including prefix and configuration checks. Differences
are recorded in `rerun_disagreements` with both source paths and rendered as
informational findings. Old copies do not enter trusted summary or known-graph
audits. Neither their apparent success nor their agreement fills missing new-owner
coverage: that remains PARTIAL until the replacement is accepted.

Survivor contradictions remain hard failures. If a replacement exists, a graph
present in an old copy must also occur in accepted owner evidence for that slice.
A validation copy containing the graph cannot excuse its absence from the owner.
Without a replacement, coverage remains PARTIAL and the old survivor stays
visible. Thus informational rerun differences cannot suppress the survivor guard.

`validation` declarations authorize only the named `(slice, tag)`. Each copy must
pass the ordinary receipt, configuration, known-graph and summary checks, and
all accepted validation and owner copies enter the ordinary duplicate comparison.
Disagreement is FAIL. A missing declared validation copy or its owner copy is
pending; a failed receipt is rejected. Current and retired owners cannot be
relabelled as validation tags. Validation copies never fill owner coverage or
repro roles, and are excluded from cost selection.

An explicitly requested seed validation outside the selected coverage uses the
owner from the published main plans. Its owner's copy is audited for comparison,
without adding the seed to the selected coverage or cost sample. Validation
copies declared only in another published plan remain foreign to this judgement.
Published rerun declarations retire their old copies across the mixed ROOT,
following the existing cross-plan supersession policy.

The new report fields and text counts distinguish declarations from copies:

| JSON field | Meaning |
| --- | --- |
| `rerun_count` | Rerun declarations in the selected and other effective published plans |
| `rerun_copies` | Discovered copies automatically superseded by reruns |
| `rerun_disagreements` | Informational old/new comparison findings; their count is printed |
| `validation_count` | Validation declarations in the selected plan |
| `validation_copies` | Accepted validation copies |
| `validation` | Discovered validation copies, reasons and acceptance status |

`accepted_slices` and `missing` still measure owner coverage. `accepted_copies`
includes sound validation copies and any owner copies fetched specifically to
compare out-of-plan seed validations; those extra copies do not expand coverage.

The complete unittest file and the three actual snapshot plans passed:

```text
python3 -B -m unittest discover -s research/unit-distance-24/tools -p test_judge_plans.py -v
Ran 55 tests
OK

coordination/cloud-workers/u24-pilot-plan.json: PLAN OK (42 slices)
coordination/cloud-workers/u24-full-plan.json: PLAN OK (1841 slices)
coordination/cloud-workers/u24-repro-plan.json: PLAN OK (50 slices)
PARTITION OK: 42 pilot + 1841 phase A + 37 phase B = 1920, disjoint
```

The new controls cover transfers from each ownership source, invalid/duplicate
declarations, old PASS/FAIL/missing receipts, informational disagreement, lost
survivors, mixed published plans, validation audit failure/disagreement, missing
owner evidence, seed validation and repro-role enforcement. `git diff --check`
passed. These are the older plan files supplied in this snapshot; no live plans
were accessed. Receipt-audit and external comparison dependencies remain mocked
in the flow tests, while plan validation, discovery, target graph reading,
classification, comparison/report routing and cost selection run normally.
The earlier full receipt-integration limitations still apply.

Worked **WRONG** example for rule 2: add this single `continue` inside the
superseded-copy branch:

```python
superseded.append(row)
continue  # WRONG: bypasses the later survivor collection.
```

With an old PASS copy containing the real `(24,69)` fixture graph and an accepted
empty replacement, this hides the old survivor. Any ordinary old/new disagreement
is only informational, so the broken judge returns OK. I ran that exact mutation
in memory: `JudgeFlowTests.test_rerun_pass_survivor_cannot_be_hidden` went red with
`AssertionError: ('OK', 0) != ('FAIL', 1)`. The correct code returns FAIL, reports
the graph, and passes once the replacement also contains it. No mutated source
was written to disk.
