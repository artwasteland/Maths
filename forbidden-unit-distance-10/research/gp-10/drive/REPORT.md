# GP-10 driver report

The sections before Round 2 preserve the original orchestration-only report.
Their stub PASS results are not independent certificate acceptance.
Round 2 likewise records its historical producer snapshot. Round 3 below is
the current seeded B10 assembly result, not a new claim about those controls.

## Delivered

`drive/` now contains:

- graph6 decoding, nauty canonicalisation, non-induced subgraph matching, and
  biconnectivity helpers;
- the canonical edge-addition poset with child-to-parent maps;
- a resumable producer driver with one or two bounded child processes;
- exact-set aggregation, pointer validation, acyclicity checks, `UNKNOWN.g6`,
  and a checker-comparison minimality report;
- B10 and control entry points, separate control run directories, deterministic
  stub producers, and regression tests.

The relation builder uses edge deletion of each parent as the exact dual of
trying every edge addition of each child.  It records the added edge in child
labels and the map from child canonical labels to parent canonical labels.
This is the map direction required by both E-pointers and R-pointers.

## B10 poset statistics

Command run:

```text
nice -n 15 bash -c 'ulimit -v 1500000; PYTHONPATH=research/gp-10/drive ~/tools/pyenv-gp10/bin/python research/gp-10/drive/poset.py research/gp-10/data/B10.g6 --out /tmp/gp10-drive/b10-poset-final.json --stats /tmp/gp10-drive/b10-poset-final-stats.json --progress-every 10000'
```

The command reported:

| quantity | measured value |
| --- | ---: |
| input graphs | 33,162 |
| edge-maximal graphs | 2,526 |
| edge-minimal graphs | 43 |
| possible non-edge additions | 981,549 |
| parent edge-deletion attempts | 510,741 |
| canonical hits before relation deduplication | 293,572 |
| canonical edge-addition graph vertices | 33,162 |
| canonical edge-addition graph edges | 274,194 |
| build time in this run | 86.72264685016125 seconds |

The graph size reported here means vertices plus unique parent-child cover
relations.  The relation map is deduplicated when automorphisms give the same
parent and child.

The frozen B10 lines were also checked against nauty-labelg:

```text
nice -n 15 bash -c 'ulimit -v 1500000; nauty-labelg -q research/gp-10/data/B10.g6 /tmp/gp10-drive/labelg-B10.g6'
nice -n 15 bash -c 'ulimit -v 1500000; cmp research/gp-10/data/B10.g6 /tmp/gp10-drive/labelg-B10.g6 && sha256sum /tmp/gp10-drive/labelg-B10.g6'
```

`cmp` succeeded and the output hash was
`3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f`.

## Tests and controls

Command run:

```text
nice -n 15 bash -c 'ulimit -v 1500000; PYTHONPATH=research/gp-10/drive ~/tools/pyenv-gp10/bin/python -m unittest -v research.gp-10.drive.test_drive'
```

All 7 tests passed.  They cover exact-set coverage, E-pointer and R-pointer
direction, a deliberately failing identity map, pointer cycles, unknown
aggregation, and resume.

The control runners were exercised with the deterministic control stub and
the optional exhaustive fallback:

```text
nice -n 15 bash -c 'ulimit -v 1500000; PYTHONPATH=research/gp-10/drive ~/tools/pyenv-gp10/bin/python research/gp-10/drive/controls.py --control both --root /tmp/gp10-drive/control-test-fallback --embedder research/gp-10/drive/stub_producers.py --refuter research/gp-10/drive/stub_producers.py --time-limits 0.1 --processes 2 --exhaustive-fallback --embedder-arg=--mode --embedder-arg=control --refuter-arg=--mode --refuter-arg=control'
```

The B8' control produced 383 records, 0 unknowns, 13 derived minimal graphs,
and passed.  The B9' control produced 3,085 records, 0 unknowns, 55 derived
minimal graphs, and passed.  The stub certificates are orchestration fixtures,
not official E-exact or refutation certificates.  The run directories were
created separately as `B8p-F7` and `B9p-F8`.

The aggregate CLI was separately exercised on the B8' control output:

```text
nice -n 15 bash -c 'ulimit -v 1500000; PYTHONPATH=research/gp-10/drive ~/tools/pyenv-gp10/bin/python research/gp-10/drive/aggregator.py research/gp-10/data/B8p.g6 --records /tmp/gp10-drive/control-test-fallback/B8p-F7/records.jsonl --poset /tmp/gp10-drive/control-test-fallback/B8p-F7/poset.json --out-dir /tmp/gp10-drive/reaggregate-b8'
```

It reported 383 covered records, 366 embedded, 17 refuted, 0 unknown, and 13
minimal graphs.

## Round 2

Real embedder, refuter, and independent checker integration is implemented.
B8p-F7 passes the official checker. B9p-F8 does not pass. Its latest completed
control has 23 unknowns, including embedding gaps as well as refuter stalls.
The requested outcome with only four refuter stalls was not achieved: the real
embedder has additional coverage limits, reproduced below without editing it.

### Diagnosis and fixes

Failed embedding maxima now leave the current budget's frontier, allowing all
remaining layers to be tried. B9 also exposed the dual problem: requiring
every biconnected child to be embedded before trying refutation hid forbidden
supergraphs behind unknown children. Failed refutation minima now leave that
frontier too. Minimality is derived separately and is not assumed by search.
The two-graph scheduling regression failed with no refuter attempts before
the latter fix, then passed for both directions at budgets 1 and 5.

Every producer request now has a fresh directory and an immutable known-file
snapshot. Both producers treat prior unknown records as completed output;
the refuter also binds resume metadata to budgets, inputs, known records and
source hashes. Reusing an output path is not a valid budget escalation.
Known-refutation exports include only tree, TU, null and real certificates,
with a closed dependency subset. Driver `sub` pointers remain in the final
record stream but are not passed to the v1 known-record loader.

The actual default refuter methods are `tu,tree,null,real`. Their allocations
divide the remaining total time among remaining methods, not the full limit
per method. Both producers receive the configured escalating total budgets.
Producer stdout, stderr, status and per-method unknown diagnostics are saved.
Final log capture includes native stdout/stderr descriptors as well as Python
streams. Repeated unknown records are explicitly diagnosed as duplicates.

`reproduce_integration.py` used genuine B8 records. Supported known records and
a genuine tree record passed. Adding driver pointers failed with
`algebra: invalid type`. A one-field tree type mutation to `sub` failed for
the same asserted reason. Changing the time budget on a completed output
failed with `resume configuration or source changed; choose a new output`.
All three negatives returned status 2. Thus status 2 alone did not establish
an argparse error in the supervisor's old run. Its original stderr was not
available, so these are demonstrated failure mechanisms, not a claim to have
recovered that run's exact exception. The first mutation reproduction used
colliding paths and failed the path guard; the corrected reproduction asserts
the intended exception. Both evidence directories are retained.

### Real control measurements

| Run | Embedded | Refuted | Unknown | Derived minimal | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Supervisor B8 before, as supplied in brief | 347 | 8 | 28 | 4 | FAIL |
| B8 after integration fixes | 366 | 17 | 0 | 13 | PASS |
| B9 first real pass | 2959 | 73 | 53 | 29 | FAIL |
| B9 after refutation ascent and focused tree retry | 2959 | 97 | 29 | 32 | FAIL |
| B9 after host-only 60-second retry | 2965 | 97 | 23 | 34 | FAIL |

B8 final checker line: `ACCEPT run verified`.
B9 first-pass checker line: `REJECT run control_unknown`.
B9 latest checker line: `REJECT run control_unknown`.
The initial B9 audit is preserved in
`/tmp/gp10-drive/round2/audit-initial.json`; it includes all initial unknown
histories, request counts, return statuses and the checker report. The first
pass had 48 B9 producer samples and 8 B8 samples, all returning status 0.
The focused tree retry added 18 B9 samples, also all returning status 0, and
24 tree refutations. A further 15 samples with host-only embedding and TU-only
refutation at 60 seconds added six embeddings and no refutations. B9 has 81
control samples in total, all with status 0. The latest driver minimality
report lists 34 established and 19 conditional candidates. The checker lists
53 candidates, of which those same 19 are conditional. Its report has zero
direct certificate rejections, but the control cannot accept unknowns.

The remaining unknowns divide into 19 F9-free graphs and exactly the four
named forbidden stalls. F9 is used for this diagnostic comparison only, not
to assign a proof verdict. The control passes only when actual certificates
and the official checker establish the result. It would be false to report
that the four refuter stalls are the only remaining obstacle.

The focused tree run reproduced the four stalls without exhausting its
40-second allocation or 2,000-state allowance:

| Graph6 | States | Moves | Stops | Seconds |
| --- | ---: | --- | --- | ---: |
| ``H_hP`SV`` | 3 | L3: 1 | no_move_no_embedding: 2 | 1.278 |
| ``H?dPdLi`` | 3 | L3: 1 | no_move_no_embedding: 2 | 0.895 |
| ``HGEAXjw`` | 7 | L3: 3 | no_move_no_embedding: 4 | 2.115 |
| ``H{O_okN`` | 15 | L1a: 4, L1b: 2, L3: 7 | contradiction: 6, no_move_no_embedding: 2 | 7.117 |

These are fixed points of this actual deterministic search, not evidence that
every AMP move order fails. More time alone did not change these tree leaves.
The all-method first pass also failed to emit a polynomial certificate for
them. Its per-method reasons are retained, including CAS deadlines on HGEAXjw.

A further stated four-graph probe used `null,real`, all-pair saturation, and
20 seconds total per graph. It resolved none. On ``H_hP`SV``, both methods
completed with `no certifiable target in Groebner basis` (257 basis members,
22 saturated pairs). On each other graph, both methods reached their roughly
10-second deadlines. TU with the enlarged known-refutation set and a
60-second total allocation also left all four unknown.

### Additional embedding blocker

Nineteen F9-free graphs still lack E-exact certificates. Two are completed
search failures rather than timeouts. The stated two-graph, six-method,
40-second probe reproduced:

| Graph6 | Lattice nodes, 18 / 36 / 30 | Constructive | Host | Numeric | Total wall seconds |
| --- | --- | --- | --- | --- | ---: |
| ``H`GO]Nw`` | 525 / 1065 / 1431, exhausted | no_degree_two_elimination | no_host_match | numeric_not_converged | 0.883 |
| ``H`QEpgl`` | 193 / 301 / 387, exhausted | no_degree_two_elimination | no_host_match | exact_refused:distinctness:0,4:zero | 0.400 |

Both host searches completed without hitting the node cap on G27, AMP33,
G118_simple or G118. Both numeric searches completed three seeded restarts.
The second graph's small numerical residual was correctly refused because
two exact points coincide. Raising only these completed attempts' time or
node ceilings does not supply a new candidate. Changed search choices or
stronger embedding machinery are needed; that work belongs in `embed/`, which
this brief forbids editing. This is not a claim that either graph is forbidden.

The other seventeen F9-free graphs reached the full 60-second host watchdog:

```text
H?DLHrp
H?DTJQx
H?QXbei
H?hXcdb
H@@LIqx
H@AHqvc
H@`XbEJ
H@gIGnR
H_DJDc{
H_EZBSu
H_SsHVo
H_hPOno
Hg@G|_x
HgDHKcx
Ho?rOxX
HoCbOxT
HoKQG^o
```

For each, the interrupted method is explicitly `host`; their earlier lattice,
constructive, numeric and refutation diagnostics remain in the audit and
STATE history. The host timeout alone does not identify which internal
operation consumed its budget. Some could yield to more time, unlike the
completed search failures above. No stronger impossibility claim is made.
The host-only sample and control retry demonstrate that a larger allocation
can help other graphs: the sample found one embedding, and the complete retry
found six. Probe certificates never silently enter the control; its six
embeddings were regenerated through the normal control runner.

The exact final run directories are `/tmp/gp10-drive/round2/B8p-F7` and
`/tmp/gp10-drive/round2/B9p-F8`. Each contains `run.json`, `records.jsonl`,
`UNKNOWN.g6`, `checker.log`, and `checked/report.json`. The final audit gives
every unresolved graph's expected control class, full attempt history and
latest method diagnostics. `done: true` in the aggregate means exact input
coverage, not that unknowns were decided or that the control passed.

### Commands and retained evidence

Every Python invocation in Round 2 uses this shell wrapper, replacing
`SCRIPT_AND_ARGUMENTS` with a line below:

```sh
nice -n 15 bash -c 'ulimit -v 976562; export PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1; exec <repo>/pyenv-gp10/bin/python -B SCRIPT_AND_ARGUMENTS'
```

```text
research/gp-10/drive/controls.py --control b8 --root /tmp/gp10-drive/round2 --processes 1 --time-limits 1,5,40 --refuter-arg=--methods --refuter-arg=tu,tree,null,real
research/gp-10/drive/controls.py --control b9 --root /tmp/gp10-drive/round2 --processes 1 --time-limits 1,5,40 --refuter-arg=--methods --refuter-arg=tu,tree,null,real
research/gp-10/drive/controls.py --control b9 --root /tmp/gp10-drive/round2 --processes 1 --resume --time-limits 40 --embedder-arg=--methods --embedder-arg=lattice18 --refuter-arg=--methods --refuter-arg=tree --refuter-arg=--max-states --refuter-arg=2000
research/gp-10/drive/controls.py --control b9 --root /tmp/gp10-drive/round2 --processes 1 --resume --time-limits 60 --embedder-arg=--methods --embedder-arg=host --refuter-arg=--methods --refuter-arg=tu
research/gp-10/drive/reproduce_integration.py --run /tmp/gp10-drive/round2/B8p-F7 --out /tmp/gp10-drive/round2/reproductions-asserted
-m unittest -v research.gp-10.drive.test_drive
research/gp-10/drive/audit_round2.py --root /tmp/gp10-drive/round2 --out /tmp/gp10-drive/round2/audit-tree.json
research/gp-10/drive/audit_round2.py --root /tmp/gp10-drive/round2 --out /tmp/gp10-drive/round2/audit-host.json
research/gp-10/drive/probe_remaining.py --run /tmp/gp10-drive/round2/B9p-F8 --out /tmp/gp10-drive/round2/probe-host60 --kind embed --methods host --seconds 60 --count 3
research/gp-10/drive/probe_remaining.py --run /tmp/gp10-drive/round2/B9p-F8 --out /tmp/gp10-drive/round2/probe-all-sat20 --kind refute --methods null,real --seconds 20 --count 4 --from-g6 /tmp/gp10-drive/round2/stalls.g6 --extra=--all-sat
research/gp-10/drive/probe_remaining.py --run /tmp/gp10-drive/round2/B9p-F8 --out /tmp/gp10-drive/round2/probe-embedding-stalls40 --kind embed --methods lattice18,lattice36,lattice30,constructive,host,numeric --seconds 40 --count 2 --from-g6 /tmp/gp10-drive/round2/embedding-stalls.g6
research/gp-10/drive/reproduce_integration.py --run /tmp/gp10-drive/round2/B8p-F7 --out /tmp/gp10-drive/round2/reproductions-final
research/gp-10/drive/audit_round2.py --root /tmp/gp10-drive/round2 --out /tmp/gp10-drive/round2/audit-final.json
```

The 13 driver tests passed. In addition to the historical red fixtures, they
cover both frontier directions, escalating budgets, immutable request paths,
closed known-record exports, native stderr capture, duplicate unknowns and
retained per-method attempt histories.
The real CLI reproduction has two genuine positives and three reason-asserted
negatives. It passed again with the final logger; its latest logs are in
`round2/reproductions-final/` under scratch. The graph6 probe inputs were
written explicitly from the four brief-named stalls and the two observed
embedding failures, respectively; they are not substitute certificates.

### Resource and scope boundaries

All Round 2 commands use niceness at least 15, the frozen Python with `-B`,
`SYMPY_GROUND_TYPES=python`, and `ulimit -v 976562`. Real CLI `main(argv)`
functions run in the driver process through `integration.py`, with at most
their one worker or CAS subprocess. This avoids adding a third process.
Only scratch-path globals are redirected to `/tmp/gp10-drive/integration`;
no mathematical producer or checker function is replaced. Samples have at
most 240 seconds of nominal search budget. Longer controls consist of many
explicit sequential samples. Actual certificate replay adds overhead.
The embedder's budget JSON prints its static 1,024,000,000-byte constant, but
its limit-setting function takes the minimum with the inherited hard limit.
The actual shell limit here is 999,999,488 bytes, not that printed constant.

No git command, install, B10 production run, or edit outside `drive/` and
`/tmp/gp10-drive/` was performed in Round 2. The stricter contract memory cap
is used here; the preserved Round 1 commands above used its older larger cap.

## Round 3

The D3 seeded driver and assembly-only workflow are implemented. The official
checker accepted the requested sample-profile run over all 33,162 frozen B10
inputs, with F9 in force and `derive: true`. Its exact final line is:

```text
ACCEPT run verified
```

| Quantity | Official result |
| --- | ---: |
| Input graphs | 33,162 |
| Embedded | 31,159 |
| Refuted | 238 |
| Unknown | 1,765 |
| Derived minimal | 99 |
| Conditional-minimal entries | 0 |
| Established minimal entries in this run | 99 |
| Nonminimal refuted | 139 |
| Direct certificate rejections | 0 |

The distinction between zero conditional-minimal entries and an incomplete
run matters: the official report has `conditional: true` because unknowns
remain. It also has `claim_authorized: false`, `control: not_a_control` and
`cross_checks: 0`. This is sample-profile acceptance, not B10-profile control
acceptance or a complete classification theorem. The root B10 manifest is a
gated draft with no fabricated controls and was not checked by the assembly.

### Implementation and seed policy

`driver.py` accepts repeated `--seed FILE`, `--validate-seeds`,
`--no-producers`, `--seed-sample-size`, `--profile` and `--derive` flags.
`seeds.py` selects the first parsed decided record for each input graph in
file/line order. Unknowns, diagnostics and outside-input records do not claim
input graphs. Selected JSONL bytes survive aggregation unchanged, including
whitespace, and survive ordinary resume. Later duplicate records do not
replace a first selection, including after checker rejection.

With validation enabled, the unchanged official checker verifies
dependency-closed samples before any propagation or producer scheduling.
Only explicit record ACCEPTs survive; rejected or unconfirmed records are
dropped with their reasons. Dependencies dropped in another sample also
invalidate their dependents. The default sample has at most 128 roots, plus
their selected dependencies. Only directly referenced E-exact records outside
the input are retained as checker-permitted hosts. External R records are
ignored. Any checker-supported certificate type is eligible, with genuine
`null-dag` and `real-dag` coverage in the regression tests.

Accepted E seeds propagate downward and R seeds upward through the existing
poset before search. In assembly-only mode no producer is called; every
remaining graph receives an explicit unknown record and is included in the
exact `UNKNOWN.g6` set. Both ordinary and sample manifests are emitted, with
derivation automatically enabled for the full frozen B10 input. An explicit
B10 profile requires the frozen input and F9, and still needs real controls.

The aggregator now accepts checker-legal hosts with extra vertices but equal
edge counts, and treats indexed forbidden-list pointers as terminal witnesses
rather than self-cycles. Neither change alters the mathematical verifier.

### Actual seed inputs and preservation audit

`assemble_b10.py` reads the D3 locations in the listed order, with sorted
recursive JSONL discovery within directories. The optional embedder round4
directory became available before the run's discovery and was included.
`DISCOVERY.json` saves all 328 paths; `COMMAND.json` saves the exact repeated
driver CLI arguments. The three explicit embedding unions, round4 records,
the two candidate streams, refuter evidence and candidate directories, and
M10-minimal records were all read without writing to those sources.

| Seed measurement | Count |
| --- | ---: |
| Source files | 328 |
| Source lines consumed | 34,505 |
| Selected input seeds | 2,518 |
| Officially accepted selected seeds | 2,518 |
| Rejected selected seeds | 0 |
| Validation samples | 20 |
| Retained external hosts | 0 |
| Later input records ignored | 4,389 |
| Unknown/diagnostic/non-record lines ignored | 16,838 |
| Other outside-input records ignored | 1,995 |
| Outside-input E-exact candidate lines, none needed as hosts | 8,761 |
| Overlong lines skipped before JSON parsing | 4 |

The four overlong lines occur in `gp74-real-extra.jsonl`,
`gp74-real-focused.jsonl`, `round2/stalls-66-centroid-factored-homogeneous.jsonl`
and `round2/stalls-66-centroid.jsonl` under the refuter evidence directory.
They exceed the official 8 MiB line limit. They are separate framing skips,
not selected records and not part of the zero checker-rejection count.

The 2,518 accepted seeds comprise 2,419 E-exact, 98 tree and one TU record.
Propagation added 28,740 E-super and 139 R-sub records. The output certificate
types are thus exact 2,419, super 28,740, tree 98, TU 1, sub 139, unknown 1,765.

`audit_round3.py` passed. It compared the aggregate input set, exact UNKNOWN
set, official counts and minimal list; checked every accepted seed's output
bytes against its retained bytes and original per-record hash; and confirmed
one consistent checker/kernel identity across all validation samples and the
final check. It rehashed 432,721,266 source-prefix bytes. No consumed prefix
had changed, and no source had changed during its initial read.

Input SHA256:
`3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f`.
Aggregate records SHA256:
`e8e0b43e344a888ef65049c669fb0aa4aa6f51391b16362ff6c160fbda7d8b74`.
Derived minimal file SHA256:
`08775a54275f06dc29858e585f3e0e151c7303ab5e9fe3948dfd5baa9c8d3417`.

### Tests, commands and evidence

The final suite passed all 23 tests in 6.904 seconds. Ten new tests cover
first-decided selection, verbatim bytes and resume, dependency closure,
rejection before propagation, allowed external E hosts, forbidden external R
targets, both DAG types, indexed F9 terminals, no fallback after rejection,
bad framing, producers receiving only the unresolved remainder, and the B10
control gate. Several tests cover multiple cases. Genuine positives and
one-field coordinate, map, DAG-coefficient and schema mutations are checked
by the official kernel. Their checker runs are retained, not merely asserted
against driver stubs. The producer-scheduling test uses a mock only to record
which unresolved graph would be scheduled and makes no producer-success claim.

The initial eight-test run had three assertions that omitted checker reason
detail suffixes and one invalid mixed-order test input. These harness issues
were corrected. The first complete 21-test suite then passed; adding retained
evidence, normal scheduling and the explicit gate test gave the final 23.
The B10 gate test's exact final line is `REJECT run controls_required`.

All Round 3 Python commands use this wrapper:

```sh
nice -n 15 bash -c 'ulimit -v 976562; export PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; exec <repo>/pyenv-gp10/bin/python -B SCRIPT_AND_ARGUMENTS'
```

The executed assembly and audit arguments were:

```text
research/gp-10/drive/assemble_b10.py --run-dir /tmp/gp10-drive/round3-b10 --poset /tmp/gp10-drive/b10-poset-final.json
research/gp-10/drive/audit_round3.py --run-dir /tmp/gp10-drive/round3-b10
```

The final test arguments were
`-m unittest discover -s research/gp-10/drive -p "test_*.py" -v`, additionally
exporting `GP10_DRIVE_TEST_ARTIFACTS=/tmp/gp10-drive/round3-regressions` and
redirecting output to `/tmp/gp10-drive/round3-tests-final.log`. Reproduction
requires fresh assembly and retained-test directories. Current source
directories can gain new records; the saved assembly is a fixed snapshot.

The wrapper called the driver with `--processes 1 --validate-seeds
--no-producers --profile B10 --derive`, full forbidden-74 JSON and graph6 files,
the cached full B10 poset, and the recorded ordered `--seed` arguments. It
then invoked the unchanged `check/gp10check.py` main on the `sample/` directory
through `integration.py`, capturing stdout, stderr and status. Only scratch
paths were redirected. The optional cached poset can be omitted on a fresh
reproduction to rebuild it inside the chosen run directory.

Evidence under `/tmp/gp10-drive/round3-b10/`:

- `ASSEMBLY.json`: final line, official report, counts, timings and resources.
- `AUDIT.json`: exact-set, seed-byte, source-prefix and checker-identity audit.
- `seeds/SEEDS.json`, `seeds/accepted.jsonl`, and `seeds/validation-*/`:
  source order/hashes, first-choice origins, outcomes and all seed checks.
- `records.jsonl`, `UNKNOWN.g6`, `STATE.json`, `SUMMARY.json`, `MINIMALITY.json`:
  the aggregate and its driver state/comparison outputs.
- `sample/run.json`, `sample/checker.log`, `sample/checked/report.json`,
  `sample/checked/minimal.g6`, `sample/checked/minimality.jsonl`: official
  sample manifest, exact checker output and derived minimality evidence.
- `run.json`, `PREDICTIONS.md`, `DISCOVERY.json`, `COMMAND.json`: gated B10
  draft, preregistered estimates and reproducible input ordering/arguments.

### Timing, resources and scope

Predictions were written before reading seed contents: 30,000 embedded,
1,000 refuted and 2,162 unknown. These rough estimates were not measurements
and differ from the actual counts above. No search was launched.

Seed discovery, validation, propagation and aggregation took 366.690 seconds.
The official full-input check took 784.524 seconds. Total wrapper time was
1,151.701 seconds. Peak process RSS was 478,792 KiB, with the inherited address
space limit 999,999,488 bytes. The checker recorded niceness 19, the frozen
Python 3.12.3 executable, SymPy 1.14.0, python-flint 0.9.0 and
`SYMPY_GROUND_TYPES=python`.

There was one active Python compute job at a time, no producer searches and
no concurrent check jobs. The unchanged checker may synchronously launch its
short-lived nauty child, preserving the common two-process ceiling. Other
shell/compute commands waited for the active job to finish. No git command,
install, mathematical verifier edit, sibling-module edit, or write outside
`drive/` and `/tmp/gp10-drive/` was performed in Round 3.

## UNCERTAIN

- The 1,765 unknown B10 graphs remain undecided by this assembly. Zero
  conditional-minimal entries does not make the whole run unconditional or
  complete. No global classification claim is authorized by the sample check.
- The root B10-profile manifest still needs genuine replayable controls and
  has not passed that profile. The separately retained gate regression
  demonstrates that omitting controls is rejected, not bypassed.
- Sources are live producer directories. This result applies to the recorded
  consumed prefixes and retained certificates, not later additions. A new
  discovery can produce different counts. First-wins selection intentionally
  does not optimize across later proofs or replace rejected first choices.
- Four oversized source lines were skipped before parsing under the checker's
  framing limit. More generally, malformed/unparseable rows are counted
  separately from selected-seed rejections. Unconfirmed checker outcomes are
  conservatively dropped rather than promoted to proofs.
- Round 2's B9 failures are historical and were not rerun in Round 3; the D3
  brief describes subsequent producer improvements. The old supervisor's
  missing stderr still prevents identifying its exact historical status-2
  cause. Neither historical uncertainty changes the measured sample result.
- Search completion depends on wall-clock budgets and box load. No claim is
  made that another search order cannot solve an unknown. The seventeen host
  timeouts and all-saturation CAS timeouts on three graphs were not retried beyond their
  stated limits. No stack-level diagnosis of the host timeouts was performed.
- The least-tested integration assumption is that sibling imports remain
  compatible in one interpreter. The observed producer and checker runs
  worked, but future module-name collisions or import-time side effects could
  break the adapter. It must not be treated as a general plugin sandbox.
- Actual parent-process native crashes and operating-system OOM kills were
  not injected in Round 2. The adapter catches Python exceptions, not fatal
  native signals. The producer's own worker boundaries still apply.
- No B10 classification or global GP-10 gate acceptance is claimed.
