# Blind checker builder report

The original sections below retain the historical Round 1 record. Current
changes, results, and every changed line range are under [Round 2](#round-2).

The requested checker, self-test, fixtures, and format definition are delivered.
The final local tests pass. This is a checker implementation result, not a
classification of the frozen input or an assertion that the publication gates
are complete. No producer certificates existed or were read in this task.

`gp10check.py` implements strict record parsing, exact embeddings, both pointer
directions, the trusted refutation tree bridge, TU replay on the augmented graph,
regenerated algebraic systems, cofactor expansion, rational Sturm counting, SOS
expansion, coverage, consistency, unknown listings, edge-deletion minimality,
and control profiles. `FORMAT.md` specifies the complete producer interface.
`PROOFS.md` records the local soundness invariants. The only imported project
verification code is the allowed trusted checker. No embedder or refuter code
was read, and no packages were installed.

The mathematical controls are deliberately distinct from implementation tests.
The self-test exercises the canonical expected-member comparisons and small
genuine minimality examples. It does not run the full withheld control
pipelines. A B10 profile with missing controls is rejected even when its same
input and records were accepted as an explicitly synthetic sample.

## Reproduction commands

All paths below are relative to the repository root. These are the final
commands actually run. Standard output and standard error were saved as shown.
The negative CLI command intentionally exits unsuccessfully.

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/kernel_selftest.py > research/gp-10/check/kernel-selftest.log 2>&1'

nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/make_fixtures.py > research/gp-10/check/fixture-build.log 2>&1'

nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/selftest.py > research/gp-10/check/selftest.log 2>&1'

nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/benchmark.py > research/gp-10/check/benchmark.log 2>&1'

nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/gp10check.py research/gp-10/check/fixtures/pointers --output /tmp/gp10-check/cli-positive > research/gp-10/check/cli-positive.log 2>&1'

nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/gp10check.py research/gp-10/check/fixtures/pointer-cycle --output /tmp/gp10-check/cli-negative > research/gp-10/check/cli-negative.log 2>&1'
```

The benchmark environment below is measured, including the actual niceness,
which is affected by inherited priority. SymPy's ground setting is assigned
before imports in every local entry point. SQLite and Python temporary storage
are directed to the allowed scratch directory. The local runners execute
external tools sequentially, with the checker itself as the only parent.
The earlier execution exceptions are disclosed separately below.

## Fixtures and independent algebra

The positive fixtures include a rational square, an equilateral triangle, a
Moser spindle built from rotated rhombi, collision refutations for complete and
bipartite graphs, polynomial refutations, both real-obstruction branches,
pointers, and a TU chain whose later gadget needs an earlier added edge.

`make_fixtures.py` obtains the null cofactors with Singular `lift` from expanded
polynomials. The checker verifies the resulting identities only with flint
expansion. The fixture builder requires an exact positive output line and has
a changed-coefficient control that prints an exact negative line. Its output is:

```text
PASS Singular wrapper positive: LIFT_IDENTITY_OK
PASS Singular wrapper one-coefficient red control: LIFT_IDENTITY_NO
PASS Singular wrapper positive: LIFT_IDENTITY_OK
FIXTURES 30 record cases
```

An exploratory saturation choice for the bipartite fixture omitted separation
of its two centers. Singular answered `2nd module does not lie in the first`
and emitted no required positive line. That attempt was rejected. Including
the missing center pair produces the final verified saturated certificate.
The final construction command above reproduces the corrected fixture.

Each stored certificate mutation identifies its positive fixture and changed
JSON path in `fixtures/cases.json`. Run mutations identify their positive run
and the sole changed file in `fixtures/run-cases.json`. Coverage mutations
remove or add a single record; certificate mutations change a specified field.
The self-test checks those relationships and asserts rejection reason codes,
including the trusted tree's specific invalid-pair diagnostic. Utility tests
also cover shared-root selection, exact tiny separations, genuine interval
refinement, repeated Sturm roots, strict JSON, and protection against output
paths that would overwrite input files.

## Final GP-10 self-test output, verbatim

```text
PASS c4
PASS triangle
PASS moser
PASS coordinate-perturbed: edge_equation: (0, 1)
PASS collision-edges-fine: exact_collision: (0, 3)
PASS interval-no-sign: interval_sign_change
PASS unknown-record-field: schema: record: missing=[] extra=['unexpected']
PASS verdict-tu: verdict_allowlist
PASS verdict-pass: verdict_allowlist
PASS verdict-forbidden: verdict_allowlist
PASS k4-tree
PASS tree-collision-pair: tree: R-tree.tree.move.pair: invalid distinct vertices
PASS k23-tree
PASS k4-isolate-null
PASS frame-nonedge: frame_not_edge
PASS extra-nonedge-generator: system_mismatch: generator keys
PASS cofactor-coefficient: cofactor_identity
PASS k4-real-sos
PASS sos-zero-constant: sos_constant_positive
PASS sos-negative-weight: sos_weight_positive
PASS sos-wrong-square: sos_identity
PASS k4-real-sturm
PASS sturm-wrong-variable: sturm_multivariate
PASS k23-saturated-null
PASS saturation-cofactor: cofactor_identity
PASS tu-chain
PASS tu-final-edge: map_not_edge_preserving: TU forbidden end: (0, 2) -> (0, 2)
PASS tu-future-edge: map_not_edge_preserving: TU step 0: (0, 1) -> (10, 11)
PASS tu-already-edge: tu_pair_already_edge
PASS tu-wrong-pair: tu_distinguished_pair
PASS run pointers: ACCEPT
PASS run mixed: ACCEPT
PASS run unknown: ACCEPT
PASS run refutation-pointer: ACCEPT
PASS run frozen-pointer: ACCEPT
PASS run tu-refuted-pointer: ACCEPT
PASS run minimality: ACCEPT
PASS run conditional-minimality: ACCEPT
PASS run pointer-noninjective: records_rejected / map_not_injective
PASS run pointer-cycle: records_rejected / pointer_cycle
PASS run pointer-missing: records_rejected / pointer_target_missing
PASS run coverage-missing: coverage
PASS run coverage-extra: coverage
PASS run coverage-duplicate: duplicate_record
PASS run verdict-conflict: embedded_refuted_conflict
PASS run unknown-missing: unknown_exactness
PASS run unknown-extra: unknown_exactness
PASS run minimality-false-claim: minimality_claim_refuted_deletion
PASS run withheld-index: records_rejected / forbidden_not_in_force
PASS run cross-check-wrong-verdict: cross_check_records
PASS run conditional-unknown-missing: unknown_exactness
PASS pointer to unknown target: pointer_target_not_accepted_refuted
PASS Sturm quadratic positive
PASS Sturm quadratic coefficient mutation: real roots=2
PASS Sturm repeated positive
PASS Sturm repeated coefficient mutation: real roots=2
PASS Sturm constant positive
PASS Sturm zero polynomial: sturm_zero_polynomial
PASS Sturm repeated real root: real roots=1
PASS reducible minpoly exact embedding
PASS rational midpoint collision: exact_collision: (0, 1)
PASS tiny exact separation
PASS tiny separation zero mutation: exact_collision: (0, 1)
PASS whole interval bisection: 3
PASS bisection positive collision mutation: exact_collision: (0, 1)
PASS shared-root positive
PASS all roots collide with different pairs: exact_collision: (0, 2)
PASS B8p expected canonical minimal members: 13
PASS B8p missing minimal member: control_minimal_list: missing=['GqGTYw'] extra=[]
PASS B9p expected canonical minimal members: 55
PASS B9p missing minimal member: control_minimal_list: missing=['H``Axih'] extra=[]
PASS strict JSON positive
PASS duplicate JSON key: duplicate_json_key: v
PASS JSON NaN: json_constant: NaN
PASS JSON overflowing exponent: json_constant: 1e9999
PASS output argument input collision: output_input_collision
SELFTEST PASS checks=76 positive=28 rejected_mutations=48
```

## Trusted kernel self-test output, verbatim

The original trusted self-test's test logic is retained. The adapter changes
its execution harness: it selects the required interpreter, redirects scratch,
and invokes checker calls in-process so that a canonicalizer does not create
an additional nested checker process. It does not change any certificate,
assertion, mathematical branch, or fixture in the trusted directory.

```text
HARNESS Python=<repo>/pyenv-gp10/bin/python SYMPY_GROUND_TYPES=python
HARNESS checker calls in-process; scratch=/tmp/gp10-check/kernel-selftest
PASS K4 L1a refutation: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS K4 one-byte pair corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/k4-refuted-corrupt.jsonl:1.witness.tree.move.pair: invalid distinct vertices
PASS default (22,61) gate on K4: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/k4-refuted.jsonl:1: expected 22 vertices, got 4
PASS L0 root row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/root-a-bad.jsonl:1.witness.tree.A: row space is inconsistent with the claimed constraints
PASS Moser exact embedding: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=1 refuted=0 unknown=0 proof_nodes=0
PASS Moser one-byte coordinate corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/moser-embedded-corrupt.jsonl:1.witness: edge (0,1) does not have squared distance 1
PASS exact embedding collision mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/embedding-collision.jsonl:1.witness: points 0 and 6 collide
PASS planted forbidden witness: exit=0: ACCEPT certificates records=1 forbidden=1 tu=0 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS forbidden one-byte map corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/planted-forbidden-corrupt.jsonl:1.witness.map: map is not injective
PASS forbidden edge-preservation mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/forbidden-absent-edge.jsonl:1.witness: pattern edge 0 maps to absent edge (0, 1)
PASS L1b exact forced ratio: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS L1b unit-modulus mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l1b-bad.jsonl:1.witness.tree: L1b omega has unit modulus
PASS L2 forced edge and child contradiction: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=2
PASS L2 modulus mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l2-bad.jsonl:1.witness.tree: L2 ratio is not a consequence of A
PASS L2 child graph mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l2-child-bad.jsonl:1.witness.tree.children[0].edges: inconsistent with the parent move
PASS L3 two-branch Lemma 4 split: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=3
PASS L3 discriminant mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l3-bad.jsonl:1.witness.tree: L3 d does not square to the recomputed discriminant
PASS L3 branch row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l3-branch-bad.jsonl:1.witness.tree.children[1].A: row space is inconsistent with the claimed constraints
PASS L1c nonnegative discriminant from genuine L3 node: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l1c-nonnegative.jsonl:1.witness.tree: L1c discriminant is not negative at the selected real root
PASS L1c n=17 negative-Heron refutation: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15
PASS L1c row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l1c-relation-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c three-edge relation is not a consequence of A
PASS L1c zero-coefficient mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l1c-zero-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c coefficients a,b,c must each be nonzero
PASS L1c child mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/l1c-child-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c contradiction must be a leaf
PASS TU gadget index 0: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 1: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 2: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 3: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 4: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 5: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU distinguished-pair mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/tu-bad.jsonl:1.witness.pair: is not the mapped distinguished gadget pair
PASS noncanonical graph6 mutation: exit=1: REJECT: g6: graph6 record 1 is not nauty-labelg canonical
PASS unknown exact listing: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=0 unknown=1 proof_nodes=0
PASS unknown one-byte listing corruption: exit=1: REJECT: UNKNOWN.g6 does not exactly list unknown certificate records in order
PASS default (22,61) positive gate and graph-list match: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=0 unknown=1 proof_nodes=0
PASS graph-list mismatch: exit=1: REJECT: certificate graph6 records do not exactly equal the supplied graph list in order
PASS manifest hashes and exact range tiling: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS compressed manifest record counting: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS manifest overlap mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/parent.g6: shard ranges have a gap or overlap before /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/manifests-bad/s1.json, expected 1, got 0
PASS manifest one-byte input-hash mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-e55kzj7l/manifests-hash-bad/s0.json.inputs_sha256: parent file hash mismatch
PASS PROOFS.md identities and exact coordinate models
PASS PROOFS.md coefficient mutation: rejected: proof gadget 0 rhombus identity is false
SELFTEST PASS checks=41 positive=18 rejected_mutations=23
```

## Streaming benchmark

The command above generated a synthetic record for every graph in the frozen
B10 input. Every verdict was deliberately unknown, with an explicit synthetic
budget and an exact UNKNOWN list. Thus this measures streaming, parsing,
canonicalization, indexing, coverage, unknown output, and report production.
It is not a benchmark of difficult exact certificates or geometric search.
No mathematical verdict about a B10 graph was obtained from this benchmark.

Historical Round 1 measured values (the current `benchmark.json` is reported
in Round 2 below):

| Quantity | Value |
| --- | --- |
| Records | 33162 |
| Record stream bytes | 4577589 |
| Elapsed seconds | 17.845728686079383 |
| Records per second | 1858.2597877254586 |
| Peak checker RSS, KiB | 77716 |
| Largest child RSS, KiB | 54144 |

The complete measured benchmark output and its one-field control-profile
mutation are preserved verbatim:

```text
{"emitted": {"ACCEPT record": 33162, "ACCEPT run": 1, "REJECT record": 0, "REJECT run": 0}, "environment": {"SYMPY_GROUND_TYPES": "python", "executable": "<repo>/pyenv-gp10/bin/python", "flint": "0.9.0", "max_rss_kib": 77716, "nice": 19, "python": "3.12.3", "sympy": "1.14.0"}, "peak_child_rss_kib": 54144, "peak_self_rss_kib": 77716, "record_bytes": 4577589, "records": 33162, "records_per_second": 1858.2597877254586, "run_report": "/tmp/gp10-check/benchmark/checked/report.json", "scope": "synthetic all-unknown records, no geometric search or proof workload", "seconds": 17.845728686079383}
PASS one-field B10 profile mutation: REJECT controls_required
```

The checker keeps only a decoded chunk of certificates in memory. Its disk
index stores graph identifiers, verdicts, dependencies, and small check details.
The measured resident memory is well below the contract ceiling. Certificate
sizes and proof complexity in a future production stream can differ greatly
from this synthetic workload; no runtime extrapolation is claimed.

## CLI output, verbatim

Accepted pointer run:

```text
ACCEPT record Bw verified
ACCEPT record A_ verified
ACCEPT run verified
```

Its changed-target cycle:

```text
ACCEPT record Bw verified
REJECT record A_ pointer_cycle
REJECT run records_rejected
```

Machine-readable counterparts are in the named scratch output directories.
The benchmark report is at the `run_report` path printed above. Control
acceptance is bound to actual control replays, not supplied ACCEPT flags.

## Contract ambiguity and scope

The prose in CONTRACT's minimality subsection says "minimal unless ... embeds"
for an unknown deletion. That reverses its own L-min criterion. The checker
implements the criterion and reports "minimal if all listed deletions embed".
The derived list includes provisional candidates under the contract's global
hypothesis that unknowns embed, and records their dependencies separately.
This is an explicit correction to contradictory prose, not an unreported
reinterpretation. A known refuted deletion always excludes a candidate.

The module supplies an additional local proof note, but it does not change the
contract, shared proofs, frozen inputs, or producer interfaces outside this
module. Input-freeze replay, independent recount, external review, historical
commit checks, and publication authorization remain outside this builder's
completed work. All reports retain `claim_authorized: false`.

## Execution deviations and corrections

I cannot honestly claim perfect compliance with the execution restrictions.
The first COMMON.md read used the following niced command, before its stricter
priority and memory wrapper were known:

```sh
nice -n 10 cat research/gp-10/briefs/COMMON.md
```

The initial direct trusted-kernel self-test was invoked as follows:

```sh
nice -n 15 bash -c 'ulimit -v 1500000; export SYMPY_GROUND_TYPES=python; exec <repo>/pyenv-gp10/bin/python research/unit-distance-22/check/selftest.py'
```

Although the top-level interpreter was correct, the script hard-coded a
pyenv-maths child interpreter, created temporary files beneath the trusted
checker's `scratch` directory, and nested a checker child beneath its own
process before launching external tools. That broke the intended interpreter,
write-boundary, and process constraints. Its temporary subdirectory was managed
by the script's cleanup. I did not modify trusted source files or attempt
cleanup outside the permitted module afterward. The adapter and its complete
passing output above are the corrected run under the required environment.

A later fixture regeneration returned a running session before I started its
self-test consumer. I did not first establish that the generator had exited,
so I cannot certify the instantaneous process count during that exploratory
handoff. Both finished, and the final validation and benchmark commands were
run sequentially after their dependencies completed.

Local proof notes were written after exploratory fixture checks and before
final validation. A strict interpretation requiring those local notes before
any exploratory use was therefore not met. These historical deviations cannot
be repaired by claiming they did not happen.

No git command, package installation, npm command, or oversight operation was
run. All intentional implementation writes and corrected scratch writes are
inside the allowed module and scratch directory. The original trusted harness
write described above is the exception. The report and module are checked for
the prohibited punctuation by the audit command below.

## Final artifact audit

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/audit.py > research/gp-10/check/audit.log 2>&1'
```

This checks the requested deliverables, Python syntax without bytecode writes,
required mutation coverage, verbatim log inclusion, benchmark/checker hash
agreement, the final UNCERTAIN section, and prohibited punctuation. Its
machine-readable result is `audit.json`.

## Round 2

Implemented A2-CHECKER-ROUND2.md and read all amendments in CONTRACT Section 10.
The baseline checker hash matches the exact version identified by the supplied
soundness audit. The audit's missing-profile finding is addressed. Amendments
concerning conditional minimality, rational spelling, and nonzero constant
real obstructions confirm the existing mathematical behavior; those branches
were not changed.

The checker now accepts B4p, B5p, B6p, and B7p as control profile names, pins
their frozen hashes, enforces the expected order and biconnectivity, uses the
F9 members of order at most n - 1, requires no unknowns, and compares the derived
minimal list with the F9 members of order n. Each produces its corresponding
`L<n>.g6`. The existing output collision guard and stale-file cleanup cover
these new filenames.

B10 requires the exact control key set B4p through B9p, named, and regressions.
The existing accepted-report checks and full replays apply to every required
entry. An old control manifest that omits a new profile cannot pass that gate.
The geometric kernels, polynomial generators and arithmetic, pointer resolution,
TU replay, block verification, and deletion logic remain unchanged. The only
change inside the minimality method is its output filename selection.

`audit_regression.py` imports the checker, not auditor or producer code. It
uses the retained `check-audit/cases/` data read-only, fingerprints that entire
source before and after execution, verifies each mutation against its accepted
parent, then replays the exact run or Sturm expectation. JSON comparisons are
type-sensitive. Checker calls run in-process, so external canonicalization
never nests a second checker child. Outputs are confined to the permitted
module and scratch directories.

Only the audit expectations named `unsupported-B4p` through `unsupported-B7p`
change: they now reject for `control_unknown`, since their profiles exist but
their records remain unknown. The original `profile` reasons are retained in
the regression result. Every other retained expectation is unchanged.

The four new wrong-derived-list tests each start with a genuine accepted
minimal-list comparison, then remove one required member. These are explicitly
helper tests, not fabricated complete control runs. Separately, genuine exact
embeddings for the square and diamond and a checked K4 tree certify a complete
frozen B4p run. Changing only its claimed list to empty rejects that run.

### Commands actually run

Each block was executed separately and completed before another test command
started. No git command or write outside the allowed module and scratch was
used during Round 2. External tools inherit the niced parent's resource ceiling.
The retained cases are a bounded deterministic sample, not an exhaustive attack
on all possible certificates. All timed commands finished below the common
long-run threshold.

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/audit_regression.py --all > research/gp-10/check/round2-regression.log 2>&1'
```

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/selftest.py > research/gp-10/check/round2-selftest.log 2>&1'
```

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -u research/gp-10/check/benchmark.py > research/gp-10/check/round2-benchmark.log 2>&1'
```

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/audit.py > research/gp-10/check/audit.log 2>&1'
```

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/round2_review.py --update-ranges'
```

The final command verifies the unchanged mathematical functions against the
saved audited baseline, checks current test/checker hashes, and generates the
line ranges below without invoking git. Its evidence is `round2-review.json`
and `round2-review.log`. Its baseline is `/tmp/gp10-check/round2/baseline/`.

### Results

The original self-test output is byte-for-byte identical to the complete output
already quoted above. The Round 2 command's last line is:

```text
SELFTEST PASS checks=76 positive=28 rejected_mutations=48
```

Measured regression results from `round2-regression.json`:

| Quantity | Result |
| --- | --- |
| Retained audit cases | 304 |
| Full audit run cases | 257 |
| Direct Sturm cases | 47 |
| Retained accepted expectations | 67 |
| Retained rejected expectations | 237 |
| Validated mutation links | 237 |
| New profile checks | 10 |
| Total regression expectations | 314 |
| Regression elapsed seconds | 15.397455086000264 |
| Regression peak RSS, KiB | 87796 |

The rejected-expectation count includes direct Sturm helpers that return a
positive real-root count; those are not full-run REJECT lines. Every full-run
case checks its exact final decision and required reason, including any
specified per-record reason.

The complete new regression output is retained verbatim:

```text
PASS audit existing-c4: ACCEPT verified
PASS audit existing-triangle: ACCEPT verified
PASS audit existing-moser: ACCEPT verified
PASS audit existing-k4-tree: ACCEPT verified
PASS audit existing-k23-tree: ACCEPT verified
PASS audit existing-k4-isolate-null: ACCEPT verified
PASS audit existing-k4-real-sos: ACCEPT verified
PASS audit existing-k4-real-sturm: ACCEPT verified
PASS audit existing-k23-saturated-null: ACCEPT verified
PASS audit existing-tu-chain: ACCEPT verified
PASS audit run-pointers: ACCEPT verified
PASS audit run-mixed: ACCEPT verified
PASS audit run-unknown: ACCEPT verified
PASS audit run-refutation-pointer: ACCEPT verified
PASS audit run-frozen-pointer: ACCEPT verified
PASS audit run-tu-refuted-pointer: ACCEPT verified
PASS audit run-minimality: ACCEPT verified
PASS audit run-conditional-minimality: ACCEPT verified
PASS audit rational-plus: ACCEPT verified
PASS audit rational-negative-zero: ACCEPT verified
PASS audit rational-leading-zeroes: ACCEPT verified
PASS audit large-rational: ACCEPT verified
PASS audit multiple-roots: ACCEPT verified
PASS audit repeated-root-odd: ACCEPT verified
PASS audit repeated-root-mixed: ACCEPT verified
PASS audit shared-root: ACCEPT verified
PASS audit interval-refinement: ACCEPT verified
PASS audit edgeless-4: ACCEPT verified
PASS audit edgeless-5: ACCEPT verified
PASS audit edgeless-6: ACCEPT verified
PASS audit edgeless-7: ACCEPT verified
PASS audit edgeless-8: ACCEPT verified
PASS audit edgeless-9: ACCEPT verified
PASS audit tree-k4-isolates-4: ACCEPT verified
PASS audit tree-k4-isolates-7: ACCEPT verified
PASS audit tree-k4-isolates-10: ACCEPT verified
PASS audit saturation-adjacent: ACCEPT verified
PASS audit real-saturation-variable: ACCEPT verified
PASS audit pointer-chain: ACCEPT verified
PASS audit refutation-chain: ACCEPT verified
PASS audit control-sample-B4p: ACCEPT verified
PASS audit control-sample-B5p: ACCEPT verified
PASS audit control-sample-B6p: ACCEPT verified
PASS audit control-sample-B7p: ACCEPT verified
PASS audit frozen-canonical-labels: ACCEPT verified
PASS audit tu-frozen-stored-labels: ACCEPT verified
PASS audit tu-pointer-with-unknown: ACCEPT verified
PASS audit derive-k4-disabled: ACCEPT verified
PASS audit derive-k4-complete: ACCEPT verified
PASS audit block-forbidden-baseline: ACCEPT verified
PASS audit real-constant: ACCEPT verified
PASS audit sturm-positive--3-1: ACCEPT returned
PASS audit sturm-positive--3-2: ACCEPT returned
PASS audit sturm-positive--2-1: ACCEPT returned
PASS audit sturm-positive--2-2: ACCEPT returned
PASS audit sturm-positive--1-1: ACCEPT returned
PASS audit sturm-positive--1-2: ACCEPT returned
PASS audit sturm-positive-0-1: ACCEPT returned
PASS audit sturm-positive-0-2: ACCEPT returned
PASS audit sturm-positive-1-1: ACCEPT returned
PASS audit sturm-positive-1-2: ACCEPT returned
PASS audit sturm-positive-2-1: ACCEPT returned
PASS audit sturm-positive-2-2: ACCEPT returned
PASS audit sturm-positive-3-1: ACCEPT returned
PASS audit sturm-positive-3-2: ACCEPT returned
PASS audit sturm-repeated-complex: ACCEPT returned
PASS audit sturm-constant: ACCEPT returned
PASS audit existing-coordinate-perturbed: REJECT records_rejected
PASS audit existing-collision-edges-fine: REJECT records_rejected
PASS audit existing-interval-no-sign: REJECT records_rejected
PASS audit existing-unknown-record-field: REJECT records_rejected
PASS audit existing-verdict-tu: REJECT records_rejected
PASS audit existing-verdict-pass: REJECT records_rejected
PASS audit existing-verdict-forbidden: REJECT records_rejected
PASS audit existing-tree-collision-pair: REJECT records_rejected
PASS audit existing-frame-nonedge: REJECT records_rejected
PASS audit existing-extra-nonedge-generator: REJECT records_rejected
PASS audit existing-cofactor-coefficient: REJECT records_rejected
PASS audit existing-sos-zero-constant: REJECT records_rejected
PASS audit existing-sos-negative-weight: REJECT records_rejected
PASS audit existing-sos-wrong-square: REJECT records_rejected
PASS audit existing-sturm-wrong-variable: REJECT records_rejected
PASS audit existing-saturation-cofactor: REJECT records_rejected
PASS audit existing-tu-final-edge: REJECT records_rejected
PASS audit existing-tu-future-edge: REJECT records_rejected
PASS audit existing-tu-already-edge: REJECT records_rejected
PASS audit existing-tu-wrong-pair: REJECT records_rejected
PASS audit run-pointer-noninjective: REJECT records_rejected
PASS audit run-pointer-cycle: REJECT records_rejected
PASS audit run-pointer-missing: REJECT records_rejected
PASS audit run-coverage-missing: REJECT coverage
PASS audit run-coverage-extra: REJECT coverage
PASS audit run-coverage-duplicate: REJECT duplicate_record
PASS audit run-verdict-conflict: REJECT embedded_refuted_conflict
PASS audit run-unknown-missing: REJECT unknown_exactness
PASS audit run-unknown-extra: REJECT unknown_exactness
PASS audit run-minimality-false-claim: REJECT minimality_claim_refuted_deletion
PASS audit run-withheld-index: REJECT records_rejected
PASS audit run-cross-check-wrong-verdict: REJECT cross_check_records
PASS audit run-conditional-unknown-missing: REJECT unknown_exactness
PASS audit zero-denominator: REJECT records_rejected
PASS audit signed-denominator: REJECT records_rejected
PASS audit rational-space: REJECT records_rejected
PASS audit rational-decimal: REJECT records_rejected
PASS audit rational-float: REJECT records_rejected
PASS audit rational-bool: REJECT records_rejected
PASS audit rational-plus-red: REJECT records_rejected
PASS audit rational-negative-zero-red: REJECT records_rejected
PASS audit rational-leading-zeroes-red: REJECT records_rejected
PASS audit minpoly-constant: REJECT records_rejected
PASS audit minpoly-zero: REJECT records_rejected
PASS audit minpoly-leading-zero: REJECT records_rejected
PASS audit minpoly-boolean: REJECT records_rejected
PASS audit endpoint-root: REJECT records_rejected
PASS audit interval-reversed: REJECT records_rejected
PASS audit coordinate-missing-vertex: REJECT records_rejected
PASS audit coordinate-extra-vertex: REJECT records_rejected
PASS audit coordinate-not-reduced: REJECT records_rejected
PASS audit coordinate-not-pair: REJECT records_rejected
PASS audit coordinate-wrong-labels: REJECT records_rejected
PASS audit large-rational-collision: REJECT records_rejected
PASS audit multiple-roots-collision: REJECT records_rejected
PASS audit repeated-root-odd-collision: REJECT records_rejected
PASS audit repeated-root-mixed-collision: REJECT records_rejected
PASS audit shared-root-trap: REJECT records_rejected
PASS audit interval-refinement-red: REJECT records_rejected
PASS audit embed-K4: REJECT records_rejected
PASS audit embed-forbidden-00: REJECT records_rejected
PASS audit embed-forbidden-01: REJECT records_rejected
PASS audit embed-forbidden-02: REJECT records_rejected
PASS audit embed-forbidden-03: REJECT records_rejected
PASS audit embed-forbidden-04: REJECT records_rejected
PASS audit embed-forbidden-05: REJECT records_rejected
PASS audit embed-forbidden-06: REJECT records_rejected
PASS audit embed-forbidden-07: REJECT records_rejected
PASS audit embed-forbidden-08: REJECT records_rejected
PASS audit embed-forbidden-09: REJECT records_rejected
PASS audit embed-forbidden-10: REJECT records_rejected
PASS audit embed-forbidden-11: REJECT records_rejected
PASS audit embed-forbidden-12: REJECT records_rejected
PASS audit embed-forbidden-13: REJECT records_rejected
PASS audit embed-forbidden-14: REJECT records_rejected
PASS audit embed-forbidden-15: REJECT records_rejected
PASS audit embed-forbidden-16: REJECT records_rejected
PASS audit embed-forbidden-17: REJECT records_rejected
PASS audit embed-forbidden-18: REJECT records_rejected
PASS audit embed-forbidden-19: REJECT records_rejected
PASS audit embed-forbidden-20: REJECT records_rejected
PASS audit embed-forbidden-21: REJECT records_rejected
PASS audit embed-forbidden-22: REJECT records_rejected
PASS audit embed-forbidden-23: REJECT records_rejected
PASS audit embed-forbidden-24: REJECT records_rejected
PASS audit embed-forbidden-25: REJECT records_rejected
PASS audit embed-forbidden-26: REJECT records_rejected
PASS audit embed-forbidden-27: REJECT records_rejected
PASS audit embed-forbidden-28: REJECT records_rejected
PASS audit embed-forbidden-29: REJECT records_rejected
PASS audit embed-forbidden-30: REJECT records_rejected
PASS audit embed-forbidden-31: REJECT records_rejected
PASS audit embed-forbidden-32: REJECT records_rejected
PASS audit embed-forbidden-33: REJECT records_rejected
PASS audit embed-forbidden-34: REJECT records_rejected
PASS audit embed-forbidden-35: REJECT records_rejected
PASS audit embed-forbidden-36: REJECT records_rejected
PASS audit embed-forbidden-37: REJECT records_rejected
PASS audit embed-forbidden-38: REJECT records_rejected
PASS audit embed-forbidden-39: REJECT records_rejected
PASS audit embed-forbidden-40: REJECT records_rejected
PASS audit embed-forbidden-41: REJECT records_rejected
PASS audit embed-forbidden-42: REJECT records_rejected
PASS audit embed-forbidden-43: REJECT records_rejected
PASS audit embed-forbidden-44: REJECT records_rejected
PASS audit embed-forbidden-45: REJECT records_rejected
PASS audit embed-forbidden-46: REJECT records_rejected
PASS audit embed-forbidden-47: REJECT records_rejected
PASS audit embed-forbidden-48: REJECT records_rejected
PASS audit embed-forbidden-49: REJECT records_rejected
PASS audit embed-forbidden-50: REJECT records_rejected
PASS audit embed-forbidden-51: REJECT records_rejected
PASS audit embed-forbidden-52: REJECT records_rejected
PASS audit embed-forbidden-53: REJECT records_rejected
PASS audit embed-forbidden-54: REJECT records_rejected
PASS audit embed-forbidden-55: REJECT records_rejected
PASS audit embed-forbidden-56: REJECT records_rejected
PASS audit embed-forbidden-57: REJECT records_rejected
PASS audit embed-forbidden-58: REJECT records_rejected
PASS audit embed-forbidden-59: REJECT records_rejected
PASS audit embed-forbidden-60: REJECT records_rejected
PASS audit embed-forbidden-61: REJECT records_rejected
PASS audit embed-forbidden-62: REJECT records_rejected
PASS audit embed-forbidden-63: REJECT records_rejected
PASS audit embed-forbidden-64: REJECT records_rejected
PASS audit embed-forbidden-65: REJECT records_rejected
PASS audit embed-forbidden-66: REJECT records_rejected
PASS audit embed-forbidden-67: REJECT records_rejected
PASS audit embed-forbidden-68: REJECT records_rejected
PASS audit embed-forbidden-69: REJECT records_rejected
PASS audit embed-forbidden-70: REJECT records_rejected
PASS audit embed-forbidden-71: REJECT records_rejected
PASS audit embed-forbidden-72: REJECT records_rejected
PASS audit embed-forbidden-73: REJECT records_rejected
PASS audit refute-UDG-C4: REJECT records_rejected
PASS audit refute-UDG-Moser: REJECT records_rejected
PASS audit refute-UDG-Petersen: REJECT records_rejected
PASS audit refute-UDG-pentagonal_prism: REJECT records_rejected
PASS audit refute-UDG-extremal: REJECT records_rejected
PASS audit tree-root-edges: REJECT records_rejected
PASS audit tree-root-rowspace: REJECT records_rejected
PASS audit tree-reducible-field: REJECT records_rejected
PASS audit tree-endpoint-root: REJECT records_rejected
PASS audit tree-leaf-children: REJECT records_rejected
PASS audit tree-forged-move: REJECT records_rejected
PASS audit cofactor-unexpected-key: REJECT records_rejected
PASS audit system-renamed-generator: REJECT records_rejected
PASS audit system-pinned-third-point: REJECT records_rejected
PASS audit system-changed-polynomial: REJECT records_rejected
PASS audit sparse-duplicate-monomial: REJECT records_rejected
PASS audit sparse-negative-exponent: REJECT records_rejected
PASS audit sparse-boolean-exponent: REJECT records_rejected
PASS audit sparse-extra-variable: REJECT records_rejected
PASS audit saturation-repeated: REJECT records_rejected
PASS audit saturation-reversed: REJECT records_rejected
PASS audit saturation-self-pair: REJECT records_rejected
PASS audit saturation-out-of-range: REJECT records_rejected
PASS audit saturation-variable-order: REJECT records_rejected
PASS audit saturation-adjacent-red: REJECT records_rejected
PASS audit real-saturation-variable-red: REJECT records_rejected
PASS audit real-nonexistent-variable: REJECT records_rejected
PASS audit sos-zero-weight: REJECT records_rejected
PASS audit sos-negative-constant: REJECT records_rejected
PASS audit real-both-proof-types: REJECT records_rejected
PASS audit pointer-negative: REJECT records_rejected
PASS audit pointer-too-large: REJECT records_rejected
PASS audit pointer-boolean: REJECT records_rejected
PASS audit pointer-direction: REJECT records_rejected
PASS audit refutation-pointer-direction: REJECT records_rejected
PASS audit frozen-index-mismatch: REJECT records_rejected
PASS audit frozen-index-negative: REJECT records_rejected
PASS audit frozen-index-out-of-range: REJECT records_rejected
PASS audit frozen-index-boolean: REJECT records_rejected
PASS audit pointer-chain-through-unknown: REJECT records_rejected
PASS audit refutation-chain-through-unknown: REJECT records_rejected
PASS audit tu-map-repeated: REJECT records_rejected
PASS audit tu-map-outside: REJECT records_rejected
PASS audit tu-gadget-negative: REJECT records_rejected
PASS audit tu-no-steps: REJECT records_rejected
PASS audit tu-no-terminal-proof: REJECT records_rejected
PASS audit tu-terminal-index: REJECT records_rejected
PASS audit minimality-omitted-minimal: REJECT minimality_claim_mismatch
PASS audit conditional-minimality-omitted: REJECT minimality_claim_mismatch
PASS audit input-wrong-hash: REJECT input_hash
PASS audit empty-record-stream: REJECT coverage
PASS audit records-no-final-newline: REJECT line_format
PASS audit records-blank-line: REJECT line_format
PASS audit unknown-file-absent: REJECT unknown_file_missing
PASS audit duplicate-json-key: REJECT records_rejected
PASS audit duplicate-generator-key: REJECT records_rejected
PASS audit json-nan: REJECT records_rejected
PASS audit coverage-noncanonical-record: REJECT records_rejected
PASS audit unsupported-B4p: REJECT control_unknown (amended from profile)
PASS audit unsupported-B5p: REJECT control_unknown (amended from profile)
PASS audit unsupported-B6p: REJECT control_unknown (amended from profile)
PASS audit unsupported-B7p: REJECT control_unknown (amended from profile)
PASS audit frozen-stored-labels-confused: REJECT records_rejected
PASS audit tu-frozen-canonical-labels-confused: REJECT records_rejected
PASS audit tu-target-unknown: REJECT records_rejected
PASS audit derive-requires-deletion: REJECT minimality_deletion_missing
PASS audit derive-k4-omitted: REJECT minimality_claim_mismatch
PASS audit block-forbidden-shortcut: REJECT block_forbidden
PASS audit real-constant-zero-target: REJECT records_rejected
PASS audit sturm-positive--3-1-two-roots: REJECT returned
PASS audit sturm-positive--3-1-repeated-root: REJECT returned
PASS audit sturm-positive--3-2-two-roots: REJECT returned
PASS audit sturm-positive--3-2-repeated-root: REJECT returned
PASS audit sturm-positive--2-1-two-roots: REJECT returned
PASS audit sturm-positive--2-1-repeated-root: REJECT returned
PASS audit sturm-positive--2-2-two-roots: REJECT returned
PASS audit sturm-positive--2-2-repeated-root: REJECT returned
PASS audit sturm-positive--1-1-two-roots: REJECT returned
PASS audit sturm-positive--1-1-repeated-root: REJECT returned
PASS audit sturm-positive--1-2-two-roots: REJECT returned
PASS audit sturm-positive--1-2-repeated-root: REJECT returned
PASS audit sturm-positive-0-1-two-roots: REJECT returned
PASS audit sturm-positive-0-1-repeated-root: REJECT returned
PASS audit sturm-positive-0-2-two-roots: REJECT returned
PASS audit sturm-positive-0-2-repeated-root: REJECT returned
PASS audit sturm-positive-1-1-two-roots: REJECT returned
PASS audit sturm-positive-1-1-repeated-root: REJECT returned
PASS audit sturm-positive-1-2-two-roots: REJECT returned
PASS audit sturm-positive-1-2-repeated-root: REJECT returned
PASS audit sturm-positive-2-1-two-roots: REJECT returned
PASS audit sturm-positive-2-1-repeated-root: REJECT returned
PASS audit sturm-positive-2-2-two-roots: REJECT returned
PASS audit sturm-positive-2-2-repeated-root: REJECT returned
PASS audit sturm-positive-3-1-two-roots: REJECT returned
PASS audit sturm-positive-3-1-repeated-root: REJECT returned
PASS audit sturm-positive-3-2-two-roots: REJECT returned
PASS audit sturm-positive-3-2-repeated-root: REJECT returned
PASS audit sturm-quartic-real: REJECT returned
PASS audit sturm-quartic-repeated-real: REJECT returned
PASS audit sturm-zero: REJECT sturm_zero_polynomial
PASS audit moser-coordinate-red: REJECT records_rejected
PASS audit k23-tree-collision-red: REJECT records_rejected
PASS audit tu-refuted-pointer-map-red: REJECT records_rejected
PASS new B4p minimal comparison: ACCEPT members=1
PASS new B4p wrong derived list: REJECT control_minimal_list
PASS new B5p minimal comparison: ACCEPT members=1
PASS new B5p wrong derived list: REJECT control_minimal_list
PASS new B6p minimal comparison: ACCEPT members=1
PASS new B6p wrong derived list: REJECT control_minimal_list
PASS new B7p minimal comparison: ACCEPT members=3
PASS new B7p wrong derived list: REJECT control_minimal_list
PASS new B4p complete frozen run: ACCEPT embedded=2 refuted=1 unknown=0
PASS new B4p wrong claimed list: REJECT minimality_claim_mismatch
REGRESSION PASS audit=304 new=10 total=314 mutation_links=237
```

The current streaming benchmark still uses declared-unknown synthetic records,
not geometric proofs or a complete B10 classification. Its measured output is:

```text
{"emitted": {"ACCEPT record": 33162, "ACCEPT run": 1, "REJECT record": 0, "REJECT run": 0}, "environment": {"SYMPY_GROUND_TYPES": "python", "executable": "<repo>/pyenv-gp10/bin/python", "flint": "0.9.0", "max_rss_kib": 77896, "nice": 19, "python": "3.12.3", "sympy": "1.14.0"}, "peak_child_rss_kib": 54336, "peak_self_rss_kib": 77896, "record_bytes": 4577589, "records": 33162, "records_per_second": 3696.659108588221, "run_report": "/tmp/gp10-check/benchmark/checked/report.json", "scope": "synthetic all-unknown records, no geometric search or proof workload", "seconds": 8.970802831929177}
PASS one-field B10 profile mutation: REJECT controls_required
```

### Every changed line range

Old ranges refer to the audited baseline snapshot. New ranges refer to the
current module. Insertions and empty new files are identified explicitly.
Generated fixture and evidence files are included alongside source and docs.
The inventory is computed from actual file contents by the review command.

<!-- ROUND2_RANGES_BEGIN -->
| File | Old lines | New lines |
| --- | --- | --- |
| `FORMAT.md` | 36 | 36-38 |
| `FORMAT.md` | 174 | 176 |
| `FORMAT.md` | 178-180 | 180-183 |
| `FORMAT.md` | 195-196 | 198-199 |
| `FORMAT.md` | 203-204 | 206-209 |
| `FORMAT.md` | 220-221 | 225-227 |
| `FORMAT.md` | 249-250 | 255-257 |
| `FORMAT.md` | after 266 (insertion) | 274-302 |
| `PROOFS.md` | 78-79 | 78-79 |
| `REPORT.md` | after 1 (insertion) | 2-4 |
| `REPORT.md` | 231 | 234-235 |
| `REPORT.md` | after 346 (insertion) | 351-850 |
| `REPORT.md` | 349-352 | 853-857 |
| `REPORT.md` | 363-364 | 868-869 |
| `REPORT.md` | 377-378 | 882-884 |
| `audit.json` | 3 | 3 |
| `audit.json` | 8 | 8 |
| `audit.log` | 1 | 1 |
| `audit_regression.py` | absent | 1-212 |
| `benchmark.json` | 12 | 12 |
| `benchmark.json` | 17-18 | 17-18 |
| `benchmark.json` | 21 | 21 |
| `benchmark.json` | 24 | 24 |
| `fixtures/round2/B4p-accepted/UNKNOWN.g6` | absent | empty new file |
| `fixtures/round2/B4p-accepted/claim.g6` | absent | 1 |
| `fixtures/round2/B4p-accepted/input.g6` | absent | 1-3 |
| `fixtures/round2/B4p-accepted/records.jsonl` | absent | 1-3 |
| `fixtures/round2/B4p-accepted/run.json` | absent | 1-9 |
| `fixtures/round2/B4p-wrong-claim/UNKNOWN.g6` | absent | empty new file |
| `fixtures/round2/B4p-wrong-claim/claim.g6` | absent | empty new file |
| `fixtures/round2/B4p-wrong-claim/input.g6` | absent | 1-3 |
| `fixtures/round2/B4p-wrong-claim/records.jsonl` | absent | 1-3 |
| `fixtures/round2/B4p-wrong-claim/run.json` | absent | 1-9 |
| `fixtures/round2/minimal-comparisons.json` | absent | 1-67 |
| `gp10check.py` | after 42 (insertion) | 43-44 |
| `gp10check.py` | 599 | 601 |
| `gp10check.py` | 630 | 632 |
| `gp10check.py` | 652 | 654 |
| `gp10check.py` | 661 | 663 |
| `gp10check.py` | 668 | 670-671 |
| `gp10check.py` | 677 | 680 |
| `gp10check.py` | 700 | 703 |
| `gp10check.py` | 723 | 726 |
| `gp10check.py` | 753 | 756 |
| `gp10check.py` | 755 | 758 |
| `gp10check.py` | 887 | 890 |
| `gp10check.py` | 929 | 932 |
| `gp10check.py` | 931 | 934 |
| `round2-benchmark.log` | absent | 1-2 |
| `round2-regression.json` | absent | 1-2792 |
| `round2-regression.log` | absent | 1-315 |
| `round2-review.json` | absent | 1-595 |
| `round2-review.log` | absent | 1 |
| `round2-selftest.log` | absent | 1-77 |
| `round2_review.py` | absent | 1-154 |
<!-- ROUND2_RANGES_END -->

## Round 3

Implemented A3-CHECKER-ROUND3.md from CONTRACT Section 10 amendment 5 and
shared PROOFS.md Section 6, with no producer code read. The earlier report,
Round 2 range table, logs, and review JSON describe their historical versions.
The baseline for this round is the complete module snapshot in
`/tmp/gp10-check/round3/baseline/`, taken before edits. Its checker SHA256 is
`ca643575c793c20ed716ef696cfef84b39b47e9d4a64a3e1790089074c88de8f`.

`null-dag` and `real-dag` now regenerate exactly the existing framed edge and
saturation system, verify each row by rational polynomial expansion using
only original generators or strictly earlier rows, and verify the last target.
A row is registered as an auxiliary source only after its identity passes.
The checker enforces required and extra fields, nonempty rows, the row bound,
source spelling and reference order, and canonical sparse terms. It does not
flatten auxiliary rows into a global cofactor identity or use a Groebner basis.
The induction justifying these checks is recorded in local PROOFS.md as well
as in the shared proof the brief required us to read.

The sparse term rule for DAG certificates is increasing lexicographic
exponent vectors, distinct monomials, and nonzero coefficients. FORMAT.md
makes this explicit for row polynomials, cofactors, f, and SOS squares.
Equivalent rational spellings are still permitted by amendment 3. Ordinary
null/real term parsing retains its original order and zero-term behavior.
DAG certificates do not accept a supplied system or top-level cofactors.

The old R-real proof statements were extracted verbatim into `real_no_zero`.
The old algebra branch passes its original parser; DAG passes the canonical
wrapper. `round3_review.py` compares parsed source against the Round 2
snapshot: 57 of the 59 original functions are identical. The only changed
original functions are `algebra`, whose tail was moved without changing any
statement, and `Checker.verify`, which gained the DAG dispatch. Removing that
new dispatch gives the identical old method. The globals are identical. The
review also verifies all original selftest statements and output remain
unchanged, and preserves the original fixtures and Round 2 evidence.
This is a source comparison in addition to replaying the regression data,
not a new independent soundness audit.

### Genuine positives and mutation coverage

`make_dag_fixtures.py` reads only our own old K4-with-isolate and saturated
K2,3 null fixtures. Those identities were obtained independently using
Singular in Round 1, and are reverified before splitting. The K2,3 null DAG
has three rows: two partial cofactor sums and their sum 1. The K4-with-isolate
DAG has two rows, with the second combining the remainder and the first row.
The isolate permits a non-edge frame mutation without relabelling the graph.
The real DAGs multiply the established 1 by `x_i^2 + 1`, using a Sturm proof
on K2,3 and an SOS proof on K4. Both are explicit univariate obstructions.
Additional positives cover nonzero constant f, a zero intermediate row,
equivalent rational spelling, and exactly 256 rows.

There are 8 genuine positive record fixtures and 66 red record fixtures.
`dag_selftest.py` loads the saved JSON afresh, checks that each red changes
exactly its declared field (including field insertion/deletion and bool versus
int), requires an accepted parent, and asserts the exact rejection reason.
Every positive has a paired red. Both DAG types exercise the common rules.
The extra CLI checks use the actual command entry point in-process on accepted
null/real records and rejected row-identity/final-target mutations, then check
both stdout and the serialized record report.

| Requirement | Retained fixture names | Expected reason |
| --- | --- | --- |
| Forward reference | `null-forward`, `real-forward` | `dag_reference_order` |
| Self reference | `null-self`, `real-self` | `dag_reference_order` |
| Unknown source | `null-unknown-source`, `real-unknown-source` | `dag_source` |
| Missing cofactors | `null-missing-cofactors`, `real-missing-cofactors` | `schema` |
| Missing poly | `null-missing-poly`, `real-missing-poly` | `schema` |
| Extra row or certificate field | `null-extra-row-field`, `real-extra-row-field`, `null-extra-cert-field`, `real-extra-cert-field` | `schema` |
| Noncanonical row/cofactor order | `null-noncanonical-poly`, `real-noncanonical-poly`, `null-noncanonical-cofactor`, `real-noncanonical-cofactor` | `sparse_noncanonical` |
| Zero or duplicate sparse term | `null-zero-term`, `real-zero-term`, `null-duplicate-term`, `real-duplicate-term` | `sparse_noncanonical` or `sparse_duplicate_monomial` |
| One coefficient breaks a row identity | `null-failed-identity`, `real-failed-identity` | `dag_row_identity` |
| Last null row is not 1, though its identity is valid | `null-last-not-one` | `dag_last_null` |
| Last real row differs from f, though its identity is valid | `real-last-not-f` | `dag_last_real` |
| More than 256 rows | `dag-257-rows`, paired with `dag-256-rows` | `dag_row_limit` |
| Empty rows | `null-empty-rows`, `real-empty-rows` | `dag_rows` |
| Frame is a non-edge | `null-frame-nonedge`, `real-frame-nonedge`, `k4-frame-nonedge` | `frame_not_edge` |

Other paired reds cover malformed auxiliary indices, a very long forward
index, a non-dictionary cofactor field, non-list rows, invalid rational
spelling and denominators, boolean exponents, noncanonical f and SOS terms,
proof-choice errors, wrong Sturm variable, and SOS positivity/identity errors.
Even an illegal source with a zero cofactor is rejected.

### Commands and observed results

These commands were run sequentially from the repository root. Each Python
runner executes checker calls in-process and waits for its single child, if
needed, before continuing. No git command, producer read, package installation,
or write outside the module and `/tmp/gp10-check/` was used in this round.
The environment records niceness 19, from the inherited priority plus the
requested `nice -n 15`, and the explicit virtual-memory limit is 1000000 KiB.

```sh
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/make_dag_fixtures.py > research/gp-10/check/round3-fixture-build.log 2>&1'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/selftest.py > research/gp-10/check/round3-selftest.log 2>&1'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/round3_regression.py > research/gp-10/check/round3-regression.log 2>&1'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/kernel_selftest.py > research/gp-10/check/round3-kernel-selftest.log 2>&1'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/benchmark.py > research/gp-10/check/round3-benchmark.log 2>&1'
```

`round3_regression.py` calls the unchanged `audit_regression.py` in-process,
sets its scratch output to `/tmp/gp10-check/round3/regression/`, saves its new
summary as `round3-regression.json`, and restores the historical Round 2 summary
in a finally block. All original audit cases and all Round 2 profile tests
are rerun. The external audit case data are fingerprinted before and after.
The final lines from the required commands are exactly:

```text
SELFTEST PASS checks=154 positive=38 rejected_mutations=116
REGRESSION PASS audit=304 new=10 total=314 mutation_links=237
SELFTEST PASS checks=41 positive=18 rejected_mutations=23
```

The expanded selftest includes the 76 original checks, 74 DAG record checks,
and 4 DAG CLI checks. Its full output is reproduced below. The regression
suite and trusted kernel are separate from that total.

The regression replay measured 20.42786197923124 seconds with peak self RSS
87228 KiB, as recorded in `round3-regression.json`. The refreshed
synthetic streaming sample checked 33162 unknown records in
14.302764233667403 seconds with peak self RSS 77908 KiB
and peak child RSS 54232 KiB. This is an all-unknown
streaming measurement, not a measurement of DAG expansion or a B10 control
acceptance. The one-field B10 profile mutation still rejects without controls.
`benchmark.json` now describes this current checker; historical Round 2 timing
remains in its log and report section.

### Fixture builder output

```text
DAG FIXTURES PASS positive=8 rejected_mutations=66 total=74
```

### Selftest output, verbatim

```text
PASS c4
PASS triangle
PASS moser
PASS coordinate-perturbed: edge_equation: (0, 1)
PASS collision-edges-fine: exact_collision: (0, 3)
PASS interval-no-sign: interval_sign_change
PASS unknown-record-field: schema: record: missing=[] extra=['unexpected']
PASS verdict-tu: verdict_allowlist
PASS verdict-pass: verdict_allowlist
PASS verdict-forbidden: verdict_allowlist
PASS k4-tree
PASS tree-collision-pair: tree: R-tree.tree.move.pair: invalid distinct vertices
PASS k23-tree
PASS k4-isolate-null
PASS frame-nonedge: frame_not_edge
PASS extra-nonedge-generator: system_mismatch: generator keys
PASS cofactor-coefficient: cofactor_identity
PASS k4-real-sos
PASS sos-zero-constant: sos_constant_positive
PASS sos-negative-weight: sos_weight_positive
PASS sos-wrong-square: sos_identity
PASS k4-real-sturm
PASS sturm-wrong-variable: sturm_multivariate
PASS k23-saturated-null
PASS saturation-cofactor: cofactor_identity
PASS tu-chain
PASS tu-final-edge: map_not_edge_preserving: TU forbidden end: (0, 2) -> (0, 2)
PASS tu-future-edge: map_not_edge_preserving: TU step 0: (0, 1) -> (10, 11)
PASS tu-already-edge: tu_pair_already_edge
PASS tu-wrong-pair: tu_distinguished_pair
PASS run pointers: ACCEPT
PASS run mixed: ACCEPT
PASS run unknown: ACCEPT
PASS run refutation-pointer: ACCEPT
PASS run frozen-pointer: ACCEPT
PASS run tu-refuted-pointer: ACCEPT
PASS run minimality: ACCEPT
PASS run conditional-minimality: ACCEPT
PASS run pointer-noninjective: records_rejected / map_not_injective
PASS run pointer-cycle: records_rejected / pointer_cycle
PASS run pointer-missing: records_rejected / pointer_target_missing
PASS run coverage-missing: coverage
PASS run coverage-extra: coverage
PASS run coverage-duplicate: duplicate_record
PASS run verdict-conflict: embedded_refuted_conflict
PASS run unknown-missing: unknown_exactness
PASS run unknown-extra: unknown_exactness
PASS run minimality-false-claim: minimality_claim_refuted_deletion
PASS run withheld-index: records_rejected / forbidden_not_in_force
PASS run cross-check-wrong-verdict: cross_check_records
PASS run conditional-unknown-missing: unknown_exactness
PASS pointer to unknown target: pointer_target_not_accepted_refuted
PASS Sturm quadratic positive
PASS Sturm quadratic coefficient mutation: real roots=2
PASS Sturm repeated positive
PASS Sturm repeated coefficient mutation: real roots=2
PASS Sturm constant positive
PASS Sturm zero polynomial: sturm_zero_polynomial
PASS Sturm repeated real root: real roots=1
PASS reducible minpoly exact embedding
PASS rational midpoint collision: exact_collision: (0, 1)
PASS tiny exact separation
PASS tiny separation zero mutation: exact_collision: (0, 1)
PASS whole interval bisection: 3
PASS bisection positive collision mutation: exact_collision: (0, 1)
PASS shared-root positive
PASS all roots collide with different pairs: exact_collision: (0, 2)
PASS B8p expected canonical minimal members: 13
PASS B8p missing minimal member: control_minimal_list: missing=['GqGTYw'] extra=[]
PASS B9p expected canonical minimal members: 55
PASS B9p missing minimal member: control_minimal_list: missing=['H``Axih'] extra=[]
PASS strict JSON positive
PASS duplicate JSON key: duplicate_json_key: v
PASS JSON NaN: json_constant: NaN
PASS JSON overflowing exponent: json_constant: 1e9999
PASS output argument input collision: output_input_collision
PASS DAG k23-null-dag: rows=3
PASS DAG k4-isolate-null-dag: rows=2
PASS DAG k23-real-dag-sturm: rows=4
PASS DAG k4-real-dag-sos: rows=3
PASS DAG real-dag-constant: rows=3
PASS DAG dag-rational-spelling: rows=3
PASS DAG dag-zero-row: rows=4
PASS DAG dag-256-rows: rows=256
PASS DAG null-forward: dag_reference_order: row 2: aux:3
PASS DAG null-self: dag_reference_order: row 2: aux:2
PASS DAG null-unknown-source: dag_source: row 2: e:99,100
PASS DAG null-negative-index: dag_source: row 2: aux:-1
PASS DAG null-leading-zero-index: dag_source: row 2: aux:00
PASS DAG null-huge-index: dag_reference_order: row 2: aux:99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
PASS DAG null-missing-cofactors: schema: DAG row 0: missing=['cofactors'] extra=[]
PASS DAG null-missing-poly: schema: DAG row 0: missing=['poly'] extra=[]
PASS DAG null-extra-row-field: schema: DAG row 0: missing=[] extra=['extra']
PASS DAG null-extra-cert-field: schema: R-algebra-dag: missing=[] extra=['system']
PASS DAG null-cofactors-list: dag_source: expected cofactor dictionary
PASS DAG null-rows-object: dag_rows: expected nonempty row list
PASS DAG null-empty-rows: dag_rows: expected nonempty row list
PASS DAG null-noncanonical-poly: sparse_noncanonical: terms must be in increasing exponent order
PASS DAG null-noncanonical-cofactor: sparse_noncanonical: terms must be in increasing exponent order
PASS DAG null-zero-term: sparse_noncanonical: zero coefficient
PASS DAG null-duplicate-term: sparse_duplicate_monomial
PASS DAG null-failed-identity: dag_row_identity: row 0
PASS DAG null-wrong-row-poly: dag_row_identity: row 0
PASS DAG null-frame-nonedge: frame_not_edge
PASS DAG null-float-coefficient: rational: expected an exact rational string
PASS DAG null-spaced-rational: rational: expected an exact rational string
PASS DAG null-negative-denominator: rational: expected an exact rational string
PASS DAG null-zero-denominator: rational: invalid denominator or numerator
PASS DAG null-boolean-exponent: sparse_exponents
PASS DAG real-forward: dag_reference_order: row 2: aux:3
PASS DAG real-self: dag_reference_order: row 2: aux:2
PASS DAG real-unknown-source: dag_source: row 2: e:99,100
PASS DAG real-negative-index: dag_source: row 2: aux:-1
PASS DAG real-leading-zero-index: dag_source: row 2: aux:00
PASS DAG real-huge-index: dag_reference_order: row 2: aux:99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
PASS DAG real-missing-cofactors: schema: DAG row 0: missing=['cofactors'] extra=[]
PASS DAG real-missing-poly: schema: DAG row 0: missing=['poly'] extra=[]
PASS DAG real-extra-row-field: schema: DAG row 0: missing=[] extra=['extra']
PASS DAG real-extra-cert-field: schema: R-algebra-dag: missing=[] extra=['system']
PASS DAG real-cofactors-list: dag_source: expected cofactor dictionary
PASS DAG real-rows-object: dag_rows: expected nonempty row list
PASS DAG real-empty-rows: dag_rows: expected nonempty row list
PASS DAG real-noncanonical-poly: sparse_noncanonical: terms must be in increasing exponent order
PASS DAG real-noncanonical-cofactor: sparse_noncanonical: terms must be in increasing exponent order
PASS DAG real-zero-term: sparse_noncanonical: zero coefficient
PASS DAG real-duplicate-term: sparse_duplicate_monomial
PASS DAG real-failed-identity: dag_row_identity: row 0
PASS DAG real-wrong-row-poly: dag_row_identity: row 0
PASS DAG real-frame-nonedge: frame_not_edge
PASS DAG real-float-coefficient: rational: expected an exact rational string
PASS DAG real-spaced-rational: rational: expected an exact rational string
PASS DAG real-negative-denominator: rational: expected an exact rational string
PASS DAG real-zero-denominator: rational: invalid denominator or numerator
PASS DAG real-boolean-exponent: sparse_exponents
PASS DAG null-last-not-one: dag_last_null
PASS DAG real-last-not-f: dag_last_real
PASS DAG dag-257-rows: dag_row_limit
PASS DAG real-noncanonical-f: sparse_noncanonical: terms must be in increasing exponent order
PASS DAG real-wrong-sturm-variable: sturm_multivariate
PASS DAG real-missing-proof: real_proof_choice
PASS DAG real-both-proofs: real_proof_choice
PASS DAG real-missing-f: schema: R-algebra-dag: missing=['f'] extra=[]
PASS DAG sos-zero-constant: sos_constant_positive
PASS DAG sos-negative-weight: sos_weight_positive
PASS DAG sos-wrong-square: sos_identity
PASS DAG sos-zero-term: sparse_noncanonical: zero coefficient
PASS DAG zero-row-nonzero-poly: dag_row_identity: row 0
PASS DAG k4-frame-nonedge: frame_not_edge
PASS DAG constant-last-not-f: dag_last_real
PASS DAG rational-spelling-invalid: rational: invalid denominator or numerator
PASS DAG CLI k23-null-dag: ACCEPT run verified
PASS DAG CLI k23-real-dag-sturm: ACCEPT run verified
PASS DAG CLI null-failed-identity: REJECT run records_rejected
PASS DAG CLI real-last-not-f: REJECT run records_rejected
SELFTEST PASS checks=154 positive=38 rejected_mutations=116
```

### Trusted kernel output, verbatim

```text
HARNESS Python=<repo>/pyenv-gp10/bin/python SYMPY_GROUND_TYPES=python
HARNESS checker calls in-process; scratch=/tmp/gp10-check/kernel-selftest
PASS K4 L1a refutation: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS K4 one-byte pair corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/k4-refuted-corrupt.jsonl:1.witness.tree.move.pair: invalid distinct vertices
PASS default (22,61) gate on K4: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/k4-refuted.jsonl:1: expected 22 vertices, got 4
PASS L0 root row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/root-a-bad.jsonl:1.witness.tree.A: row space is inconsistent with the claimed constraints
PASS Moser exact embedding: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=1 refuted=0 unknown=0 proof_nodes=0
PASS Moser one-byte coordinate corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/moser-embedded-corrupt.jsonl:1.witness: edge (0,1) does not have squared distance 1
PASS exact embedding collision mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/embedding-collision.jsonl:1.witness: points 0 and 6 collide
PASS planted forbidden witness: exit=0: ACCEPT certificates records=1 forbidden=1 tu=0 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS forbidden one-byte map corruption: exit=1: REJECT: <repo>/research/unit-distance-22/check/fixtures/planted-forbidden-corrupt.jsonl:1.witness.map: map is not injective
PASS forbidden edge-preservation mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/forbidden-absent-edge.jsonl:1.witness: pattern edge 0 maps to absent edge (0, 1)
PASS L1b exact forced ratio: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS L1b unit-modulus mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l1b-bad.jsonl:1.witness.tree: L1b omega has unit modulus
PASS L2 forced edge and child contradiction: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=2
PASS L2 modulus mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l2-bad.jsonl:1.witness.tree: L2 ratio is not a consequence of A
PASS L2 child graph mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l2-child-bad.jsonl:1.witness.tree.children[0].edges: inconsistent with the parent move
PASS L3 two-branch Lemma 4 split: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=3
PASS L3 discriminant mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l3-bad.jsonl:1.witness.tree: L3 d does not square to the recomputed discriminant
PASS L3 branch row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l3-branch-bad.jsonl:1.witness.tree.children[1].A: row space is inconsistent with the claimed constraints
PASS L1c nonnegative discriminant from genuine L3 node: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l1c-nonnegative.jsonl:1.witness.tree: L1c discriminant is not negative at the selected real root
PASS L1c n=17 negative-Heron refutation: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15
PASS L1c row-space mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l1c-relation-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c three-edge relation is not a consequence of A
PASS L1c zero-coefficient mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l1c-zero-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c coefficients a,b,c must each be nonzero
PASS L1c child mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/l1c-child-bad.jsonl:1.witness.tree.children[0].children[0].children[0]: L1c contradiction must be a leaf
PASS TU gadget index 0: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 1: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 2: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 3: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 4: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU gadget index 5: exit=0: ACCEPT certificates records=1 forbidden=0 tu=1 embedded=0 refuted=0 unknown=0 proof_nodes=0
PASS TU distinguished-pair mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/tu-bad.jsonl:1.witness.pair: is not the mapped distinguished gadget pair
PASS noncanonical graph6 mutation: exit=1: REJECT: g6: graph6 record 1 is not nauty-labelg canonical
PASS unknown exact listing: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=0 unknown=1 proof_nodes=0
PASS unknown one-byte listing corruption: exit=1: REJECT: UNKNOWN.g6 does not exactly list unknown certificate records in order
PASS default (22,61) positive gate and graph-list match: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=0 unknown=1 proof_nodes=0
PASS graph-list mismatch: exit=1: REJECT: certificate graph6 records do not exactly equal the supplied graph list in order
PASS manifest hashes and exact range tiling: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS compressed manifest record counting: exit=0: ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
PASS manifest overlap mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/parent.g6: shard ranges have a gap or overlap before /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/manifests-bad/s1.json, expected 1, got 0
PASS manifest one-byte input-hash mutation: exit=1: REJECT: /tmp/gp10-check/kernel-selftest/selftest-_pm0r3hh/manifests-hash-bad/s0.json.inputs_sha256: parent file hash mismatch
PASS PROOFS.md identities and exact coordinate models
PASS PROOFS.md coefficient mutation: rejected: proof gadget 0 rhombus identity is false
SELFTEST PASS checks=41 positive=18 rejected_mutations=23
```

### Streaming benchmark output, verbatim

```text
{"emitted": {"ACCEPT record": 33162, "ACCEPT run": 1, "REJECT record": 0, "REJECT run": 0}, "environment": {"SYMPY_GROUND_TYPES": "python", "executable": "<repo>/pyenv-gp10/bin/python", "flint": "0.9.0", "max_rss_kib": 77908, "nice": 19, "python": "3.12.3", "sympy": "1.14.0"}, "peak_child_rss_kib": 54232, "peak_self_rss_kib": 77908, "record_bytes": 4577589, "records": 33162, "records_per_second": 2318.5727918201765, "run_report": "/tmp/gp10-check/benchmark/checked/report.json", "scope": "synthetic all-unknown records, no geometric search or proof workload", "seconds": 14.302764233667403}
PASS one-field B10 profile mutation: REJECT controls_required
```

### Development failures and review scope

An initial editing command had a shell quoting error and made no changes.
During fixture development, FLINT exponent objects needed explicit conversion
to JSON integers. A trial row-coefficient mutation created zero and correctly
hit the canonical-term check before the intended identity check. A supposed
f-only mutation was initially accepted because Python object sharing also
changed its final row and cofactor. Positive fixtures are now JSON-round-tripped
before mutation, and the independent saved-file mutation audit catches any
multi-field change. Finally, the first CLI negative check expected
`record_invalid`; the checker correctly returned `records_rejected`, and the
harness now asserts that actual run-level reason along with the precise
record-level reason. These were fixture or harness defects, not checker fixes.
The failed outputs are retained under `/tmp/gp10-check/round3/` as
`fixture-first-attempt.log`, `fixture-second-attempt.log`,
`fixture-third-attempt.log`, and `selftest-first-attempt.log`.

The final artifact audit and source/range comparison use these commands:

```sh
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/audit.py > research/gp-10/check/audit.log 2>&1'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/round3_review.py --update-ranges'
exec nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/round3_review.py'
```

`audit.json` is the artifact audit result; `round3-review.json` contains the
source comparison, checker hashes, exact test final lines, and the complete
changed-line inventory. The review asserts the final UNCERTAIN heading,
verbatim logs, current regression and benchmark checker hashes, Python syntax,
and absence of the prohibited punctuation. The source review final line is:

```text
ROUND3 REVIEW PASS original_functions=59 identical=57 moved_real_proof=identical existing_branches=identical
```

### Every changed line range

Old lines refer to the Round 2 snapshot; new lines refer to this delivery.
Insertions have no old span. New fixture JSON files each occupy one line.
Unchanged historical artifacts are omitted. The review computes these ranges
with a text comparison and verifies the table and its JSON inventory agree.

<!-- ROUND3_RANGES_BEGIN -->
| File | Old lines | New lines |
| --- | --- | --- |
| `FORMAT.md` | after 150 (insertion) | 151-189 |
| `PROOFS.md` | after 87 (insertion) | 88-106 |
| `REPORT.md` | after 850 (insertion) | 851-1348 |
| `REPORT.md` | after 851 (insertion) | 1350-1368 |
| `audit.json` | 3 | 3 |
| `audit.json` | 8 | 8 |
| `audit.log` | 1 | 1 |
| `benchmark.json` | 12 | 12 |
| `benchmark.json` | 17-18 | 17-18 |
| `benchmark.json` | 21 | 21 |
| `benchmark.json` | 24 | 24 |
| `dag_selftest.py` | absent | 1-86 |
| `fixtures/round3/cases.json` | absent | 1-999 |
| `fixtures/round3/constant-last-not-f.json` | absent | 1 |
| `fixtures/round3/dag-256-rows.json` | absent | 1 |
| `fixtures/round3/dag-257-rows.json` | absent | 1 |
| `fixtures/round3/dag-rational-spelling.json` | absent | 1 |
| `fixtures/round3/dag-zero-row.json` | absent | 1 |
| `fixtures/round3/k23-null-dag.json` | absent | 1 |
| `fixtures/round3/k23-real-dag-sturm.json` | absent | 1 |
| `fixtures/round3/k4-frame-nonedge.json` | absent | 1 |
| `fixtures/round3/k4-isolate-null-dag.json` | absent | 1 |
| `fixtures/round3/k4-real-dag-sos.json` | absent | 1 |
| `fixtures/round3/null-boolean-exponent.json` | absent | 1 |
| `fixtures/round3/null-cofactors-list.json` | absent | 1 |
| `fixtures/round3/null-duplicate-term.json` | absent | 1 |
| `fixtures/round3/null-empty-rows.json` | absent | 1 |
| `fixtures/round3/null-extra-cert-field.json` | absent | 1 |
| `fixtures/round3/null-extra-row-field.json` | absent | 1 |
| `fixtures/round3/null-failed-identity.json` | absent | 1 |
| `fixtures/round3/null-float-coefficient.json` | absent | 1 |
| `fixtures/round3/null-forward.json` | absent | 1 |
| `fixtures/round3/null-frame-nonedge.json` | absent | 1 |
| `fixtures/round3/null-huge-index.json` | absent | 1 |
| `fixtures/round3/null-last-not-one.json` | absent | 1 |
| `fixtures/round3/null-leading-zero-index.json` | absent | 1 |
| `fixtures/round3/null-missing-cofactors.json` | absent | 1 |
| `fixtures/round3/null-missing-poly.json` | absent | 1 |
| `fixtures/round3/null-negative-denominator.json` | absent | 1 |
| `fixtures/round3/null-negative-index.json` | absent | 1 |
| `fixtures/round3/null-noncanonical-cofactor.json` | absent | 1 |
| `fixtures/round3/null-noncanonical-poly.json` | absent | 1 |
| `fixtures/round3/null-rows-object.json` | absent | 1 |
| `fixtures/round3/null-self.json` | absent | 1 |
| `fixtures/round3/null-spaced-rational.json` | absent | 1 |
| `fixtures/round3/null-unknown-source.json` | absent | 1 |
| `fixtures/round3/null-wrong-row-poly.json` | absent | 1 |
| `fixtures/round3/null-zero-denominator.json` | absent | 1 |
| `fixtures/round3/null-zero-term.json` | absent | 1 |
| `fixtures/round3/rational-spelling-invalid.json` | absent | 1 |
| `fixtures/round3/real-boolean-exponent.json` | absent | 1 |
| `fixtures/round3/real-both-proofs.json` | absent | 1 |
| `fixtures/round3/real-cofactors-list.json` | absent | 1 |
| `fixtures/round3/real-dag-constant.json` | absent | 1 |
| `fixtures/round3/real-duplicate-term.json` | absent | 1 |
| `fixtures/round3/real-empty-rows.json` | absent | 1 |
| `fixtures/round3/real-extra-cert-field.json` | absent | 1 |
| `fixtures/round3/real-extra-row-field.json` | absent | 1 |
| `fixtures/round3/real-failed-identity.json` | absent | 1 |
| `fixtures/round3/real-float-coefficient.json` | absent | 1 |
| `fixtures/round3/real-forward.json` | absent | 1 |
| `fixtures/round3/real-frame-nonedge.json` | absent | 1 |
| `fixtures/round3/real-huge-index.json` | absent | 1 |
| `fixtures/round3/real-last-not-f.json` | absent | 1 |
| `fixtures/round3/real-leading-zero-index.json` | absent | 1 |
| `fixtures/round3/real-missing-cofactors.json` | absent | 1 |
| `fixtures/round3/real-missing-f.json` | absent | 1 |
| `fixtures/round3/real-missing-poly.json` | absent | 1 |
| `fixtures/round3/real-missing-proof.json` | absent | 1 |
| `fixtures/round3/real-negative-denominator.json` | absent | 1 |
| `fixtures/round3/real-negative-index.json` | absent | 1 |
| `fixtures/round3/real-noncanonical-cofactor.json` | absent | 1 |
| `fixtures/round3/real-noncanonical-f.json` | absent | 1 |
| `fixtures/round3/real-noncanonical-poly.json` | absent | 1 |
| `fixtures/round3/real-rows-object.json` | absent | 1 |
| `fixtures/round3/real-self.json` | absent | 1 |
| `fixtures/round3/real-spaced-rational.json` | absent | 1 |
| `fixtures/round3/real-unknown-source.json` | absent | 1 |
| `fixtures/round3/real-wrong-row-poly.json` | absent | 1 |
| `fixtures/round3/real-wrong-sturm-variable.json` | absent | 1 |
| `fixtures/round3/real-zero-denominator.json` | absent | 1 |
| `fixtures/round3/real-zero-term.json` | absent | 1 |
| `fixtures/round3/sos-negative-weight.json` | absent | 1 |
| `fixtures/round3/sos-wrong-square.json` | absent | 1 |
| `fixtures/round3/sos-zero-constant.json` | absent | 1 |
| `fixtures/round3/sos-zero-term.json` | absent | 1 |
| `fixtures/round3/zero-row-nonzero-poly.json` | absent | 1 |
| `gp10check.py` | after 418 (insertion) | 419-422 |
| `gp10check.py` | after 444 (insertion) | 449-491 |
| `gp10check.py` | after 507 (insertion) | 555-556 |
| `make_dag_fixtures.py` | absent | 1-183 |
| `round3-benchmark.log` | absent | 1-2 |
| `round3-fixture-build.log` | absent | 1 |
| `round3-kernel-selftest.log` | absent | 1-44 |
| `round3-regression.json` | absent | 1-2792 |
| `round3-regression.log` | absent | 1-315 |
| `round3-review.json` | absent | 1-1507 |
| `round3-review.log` | absent | 1 |
| `round3-selftest.log` | absent | 1-155 |
| `round3_regression.py` | absent | 1-24 |
| `round3_review.py` | absent | 1-127 |
| `selftest.py` | after 159 (insertion) | 160-161 |
<!-- ROUND3_RANGES_END -->

## UNCERTAIN

- Round 3 was built without reading the refuter prototype. Its producer
  interoperability and the large motivating F9 index 39 certificate were not
  exercised. The 256-row positive uses small rows; it is not a stress test of
  high-degree or very large expanded intermediates. The row limit alone does
  not bound polynomial expansion memory or runtime.
- Amendment 5 requires canonical sparse terms but does not name an ordering.
  This checker defines increasing lexicographic exponent order, consistent
  with its existing serializer, and preserves amendment 3's rational spelling.
  That is the least certain new integration assumption. Producers must use
  the documented DAG spelling; unsorted or zero terms that ordinary algebra
  still accepts now reject in DAG certificates.
- The new real DAG fixtures are built on already complex-inconsistent systems
  and multiply 1 by a univariate polynomial with no real roots. They test the
  no-real-zero proof path but do not establish the intended large-DAG speedup
  or supply a DAG for a complex-solvable, real-unsolvable example. The most
  likely new bug would concern sparse-format interoperability or resource
  behavior on large rows. The source comparison and regression replay were
  performed by this builder, not a fresh independent reviewer.

- Round 2 accepts a genuine complete frozen B4p checker run. Complete accepted
  B5p through B9p, named, and regression control runs were not executed. The
  expected-member helper comparisons and rejected unknown profiles do not
  replace those pipelines. A full accepted B10 control tree remains unexercised
  and no complete accepted B10 classification report is available.
- The real-obstruction fixtures multiply a genuine null identity by a polynomial
  with no real roots. They exercise expansion, SOS positivity, and Sturm logic,
  but do not demonstrate a complex-solvable, real-unsolvable graph through this
  new algebra branch. The delegated kernel's negative-discriminant fixture does
  exercise a distinct real obstruction in the trusted tests.
- The streaming measurement uses small unknown records. Large cofactors, large
  hosts, deep trusted proof trees, long pointer chains, and full production
  minimality throughput were not stress-tested. Resource exhaustion rejects or
  interrupts a check; it never proves an embedding or refutation.
- The least certain integration assumption is agreement by future producers
  and the supervisor on the run manifest and complete control-tree layout.
  The minimality wording is now settled by the contract amendment. The named
  Golomb topology is explicitly constructed there, rather than inferred from
  a supplied graph6 value in the brief.
- A bug would most likely hide in control-profile integration, canonical label
  maps across external data, a future large sparse identity, or conditional
  minimality/report consumption. Small certificates and adversarial mutations
  cannot replace the required independent review of these branches.
- Named-control search provenance and predictions chronology are not proved by
  certificate arithmetic. The checker can reject declared library pointers,
  validate the required declarations, hash predictions, and replay controls;
  it cannot establish search origin or past commit order from these files.
- Frozen input membership, the published smaller-order theorem, the trusted
  gadget file, nauty, flint, and the imported tree verifier remain assumptions.
  The supplied independent soundness audit was read and its cases replayed.
  No new independent input-freeze recount or cross-model mathematical review
  was performed here.
- The historical write, interpreter, and process-limit deviations above remain
  part of this task's record. The exact concurrent process count during the
  exploratory handoff was not measured. A passing final audit cannot certify
  that those earlier restrictions were always observed.
