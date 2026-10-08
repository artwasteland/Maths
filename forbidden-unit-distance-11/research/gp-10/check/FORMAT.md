# GP-10 checker format

`gp10check.py` checks certificates independently of producers. It imports only the
trusted `research/unit-distance-22/check/udcheck.py` for R-tree. It does not import
an embedder, refuter, or fixture generator. Its command is:

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/gp10check.py RUN_DIRECTORY --output /tmp/gp10-check/result'
```

Use the same wrapper for `selftest.py`, `make_fixtures.py`, `kernel_selftest.py`,
and `benchmark.py`. It provides a stricter memory ceiling than COMMON.md and
respects CONTRACT Section 9. Each runner launches at most one child at a time.
The trusted self-test adapter runs checker calls in-process, so that nauty or
zstd is the only child. The unadapted trusted self-test does not have that property.

## JSON and graph conventions

Each certificate line is exactly an object with `g6`, `verdict`, and `cert`.
The verdict allowlist is `embedded`, `refuted`, `unknown`. A nonempty line ends
with a newline. Duplicate JSON keys, NaN, Infinity, boolean vertex numbers, and
extra keys are rejected. Budget objects are application-defined JSON objects.
An invalid record rejects the run. Malformed records get a line-location label
when there is no usable graph6 value. Fatal framing, duplicate, conflict, and
external-tool failures stop further processing.

Graph6 values have no header or surrounding whitespace, zero padding bits, and
minimal order encoding. Short and medium graph6 order encodings are accepted.
Every record, pointer target, host, and frozen input is checked against
`nauty-labelg -q` canonical form. Maps and coordinates always use the labelling
specified below. The canonicalizer is the installed nauty utility, not a second
canonical form invented by this module.

Exact rationals in the GP-10 branches are **strings**, for example `"0"`, `"1"`,
`"-7/12"`, or `"1/1"`. Decimal and floating values are rejected. Reduction of
rational strings to a canonical spelling is not required. Under CONTRACT
Section 10 amendment 3, the spelling is `[+-]?digits(/digits)?`, with a positive
denominator and no whitespace. The delegated tree
witness retains its own documented integer-or-rational grammar.

## Embedding certificates

`exact` has precisely `type`, `field`, and `coords`. The field has precisely
`minpoly` and `interval`. The polynomial is a positive-degree integer coefficient
array in ascending powers, with nonzero leading coefficient. Each coordinate
is an array of exactly `degree(minpoly)` rational strings. Zero coefficients
must therefore be padded explicitly.

```json
{"g6":"Bw","verdict":"embedded","cert":{"type":"exact","field":{"minpoly":[-3,0,1],"interval":["1","2"]},"coords":[[["0","0"],["0","0"]],[["1","0"],["0","0"]],[["1/2","0"],["0","1/2"]]]}}
```

The interval must have a strict sign change. Irreducibility and unique-root
isolation are not required by this branch. Edge equations reduce to zero over
Q modulo the polynomial. Distinctness uses outward exact rational intervals,
which are certified interval balls with no rounding error. All pairs share a
single interval and thus select the same real root. Bisection keeps a sign
change; if a midpoint is an exact root, all distances are checked at that root.
Failure to separate within the documented bisection budget is a rejection of
the certificate, never a fabricated embedding or an automatic unknown record.

An E-ptr is exactly:

```json
{"type":"super","g6":"Bw","map":[0,1]}
```

It maps **the current graph into the target**. Every target must be an accepted
embedded record or an E-exact host. All pointers, including TU terminal
references, are resolved in topological order with an on-disk queue. Missing
and rejected targets, targets of the wrong verdict, and cycles reject.

## Refutation certificates

* `tree`: exactly `type` and `witness`. The witness is passed to the trusted
  `verify_refutation(Graph(n,edges), witness, where)` without mathematical
  reinterpretation. Its own strict field and proof-tree parsing applies.
* `sub`: exactly `type`, `g6`, `map`, optionally `index`. It maps **the target H
  into the current graph G**. Without `index`, H must have an accepted refuted
  record. With `index`, H must equal the canonical form of that F9 member and
  the member must belong to the list currently in force. This map uses H's
  **canonical** labels. An index cannot bypass the withheld control list.
* `tu`: exactly `type`, nonempty `steps`, and `end`. Each step has exactly
  `gadget`, `map`, `pair`. Gadget indices are zero-based indices in the trusted
  gadget JSON. Maps use the **stored gadget labels** and must embed into the
  graph after all earlier additions. The unordered pair must equal the image
  of the stored distinguished pair and must still be a non-edge. No bare TU
  hit is an accepted verdict.

TU ends have exactly `forbidden` plus `map`, or `refuted` plus `map`.
`forbidden` is a zero-based F9 JSON index that is in force, and its map uses
**stored F9 JSON labels**. `refuted` is a canonical graph6 target whose map uses
**canonical labels** and whose refuted record is accepted in the same run.
Both kinds map into the final augmented graph.

### Sparse polynomials and regenerated systems

R-null has `type`, `frame`, `sat`, and `cofactors`, with optional `system`.
The frame is an ordered pair `[a,b]` of distinct vertices forming an edge.
The checker substitutes p(a)=(0,0), p(b)=(1,0). No third vertex may be pinned.
Each saturation pair is stored `[u,v]` with u < v; duplicates are rejected.
The **order of the saturation list is significant** for naming its variables.

The polynomial variable order is:

1. `x_i,y_i` in increasing vertex order, omitting a and b;
2. `t_0,t_1,...` in saturation-list order.

A polynomial is a list of `[coefficient, exponents]` terms. A coefficient is an
exact rational string. An exponent vector has one nonnegative integer per
variable in that fixed order. Terms may appear in any order; duplicate exponent
vectors are rejected. The zero polynomial is `[]`. Zero coefficients are
permitted. No string expression parser or implicit variable is used.
For frame `[0,1]` on four vertices and no saturation, the order is
`x_2,y_2,x_3,y_3`; `x_2^2 + y_2^2 - 1` is:

```json
[["1",[2,0,0,0]],["1",[0,2,0,0]],["-1",[0,0,0,0]]]
```

Generator keys are `e:u,v` for every actual edge u < v other than the frame,
and `s:u,v` for each saturation pair. The checker generates, respectively,
`d2(u,v)-1` and `t_k*d2(u,v)-1`. `cofactors` is a dictionary keyed by these
names; omitted cofactors mean zero, and unknown names reject. `system`, when
present, must contain exactly all regenerated keys and agree polynomial by
polynomial. A non-edge unit equation, extra pinned coordinate, substituted
system, omitted generator, or invented saturation variable cannot be accepted.

The checker expands the sum using python-flint `fmpq_mpoly`. It does not call
Singular, msolve, or any Groebner algorithm. In R-null the sum must equal 1.

R-real has those same fields plus `f` and exactly one of:

```json
{"sturm":"x_2"}
```

or

```json
{"sos":{"c":"1","squares":[["1",[["1",[1,0,0,0]]]]]}}
```

These are extra fields in the certificate object, not separate records.
The cofactor sum must equal `f`. For Sturm, `f` must involve only the named
existing variable. A nonzero constant is permitted; the zero polynomial is
rejected. The checker's rational Sturm implementation counts distinct real
roots using signs at both infinities, including repeated roots, and accepts
only zero roots. For SOS, c and every weight must be strictly positive and the
checker separately expands `c + sum(w*q*q)` and compares it with `f`.

### Derivations in rows (amendment 5)

`null-dag` has exactly `type`, `frame`, `sat`, and `rows`. `real-dag` has
those fields plus `f` and exactly one of `sturm` or `sos`, with the same
no-real-zero checks as R-real. Neither DAG form permits `system` or top-level
`cofactors`. Frames, saturation, variable order, original generator keys, and
rational strings use the rules above.

`rows` is a nonempty list of at most 256 objects. Row k has exactly `poly`
and `cofactors`. Its cofactor dictionary may name an original generator or
`aux:j`, where j is a zero-based row index strictly smaller than k. The index
uses decimal digits without a sign or leading zeros (except `aux:0`). Omitted
cofactors are zero; an empty dictionary is permitted for a zero row. Each row
must satisfy `poly = sum(cofactor * source)` exactly by expansion. The checker
registers `aux:k` only after that identity passes. The last polynomial must
be 1 for `null-dag`, or equal `f` for `real-dag`.

All sparse polynomials in DAG certificates, including `f` and SOS squares,
use **strictly increasing lexicographic exponent-vector order**, contain no
zero coefficients, and contain no duplicate monomials. This is the order of
`serialize_polynomial`. The zero polynomial is `[]`. Equivalent rational
spellings such as `"1/1"` remain permitted. These canonical term requirements
apply only to the DAG types; ordinary R-null and R-real retain their original
term-order and zero-coefficient rules. For example, the canonical DAG spelling
of `x_2^2 + y_2^2 - 1` from the example above is:

```json
[["-1",[0,0,0,0]],["1",[0,2,0,0]],["1",[2,0,0,0]]]
```

Malformed row schemas reject with `schema`; invalid source names with
`dag_source`; self or forward references with `dag_reference_order`;
noncanonical term order or zero terms with `sparse_noncanonical`; duplicate
monomials with `sparse_duplicate_monomial`; failed expansion with
`dag_row_identity`; and wrong final targets with `dag_last_null` or
`dag_last_real`. Empty or non-list rows reject with `dag_rows`, and the row
limit with `dag_row_limit`. Existing rational, exponent, frame, Sturm, and SOS
reason strings remain in use.

## Run directory

A minimal `run.json` is:

```json
{"profile":"sample","input":"input.g6","input_sha256":"<lowercase sha256>","records":["records.jsonl"]}
```

Paths are relative to this manifest unless absolute. Input graph lists are
bytewise sorted, canonical, unique, and newline terminated. Record files need
not be sorted. Records must cover exactly the input set, and may not duplicate
each other. Hosts have a separate exact-only stream and are not input records;
input/host overlap is rejected to keep graph identity unambiguous.

Optional manifest fields:

| Field | Meaning |
| --- | --- |
| `hosts` | Path to E-exact host JSONL records. Each is checked once. |
| `unknown` | Path to the exact sorted unknown graph list, default `UNKNOWN.g6`. This file must exist even when empty. |
| `minimal_claim` | Sorted proposed minimal list to compare with the derived result. Requires derivation. |
| `cross_checks` | JSONL pairs `{"refuted":"...","embedded":"..."}`. Both records must be accepted with these verdicts. The checker searches for non-induced containment itself. |
| `forbidden_limit` | Sample-only integer from 0 through 9. Zero means the list is empty. Default 9. |
| `derive` | Sample-only boolean requesting minimality derivation. |
| `controls` | B10-only object with control run directories keyed `B4p`, `B5p`, `B6p`, `B7p`, `B8p`, `B9p`, `named`, `regressions`. |
| `provenance` | Named-control JSON file described below. |
| `predictions` | B10 object with `path` and `sha256` for the predictions document. |

Profiles `B4p` through `B9p`, and `B10`, require the corresponding frozen
SHA256SUMS entry and the expected order and biconnectivity. A control profile
`B<n>p` fixes the list in force to F9 members on at most n - 1 vertices; B4p
therefore has an empty list. B10 fixes the list to F9. The input digest is also checked against the actual bytes
consumed by the stream, and reports hash the consumed certificate streams.
A sample report is explicitly not a control or a B10 classification.

Minimality uses canonical edge deletions. Non-biconnected deletions must have
an edge partition into actual blocks and bridges, with every block of smaller
order at most nine and containing no F9 graph. Isolated vertices are recorded.
Biconnected deletions must have accepted records. Any refuted deletion excludes
the parent, even if another deletion is unknown. Missing deletions reject.

When only unknown deletions obstruct minimality, the candidate is listed with
`requires_embedded`. The derived file contains both proved minimal graphs and
these provisional graphs under the assumption that all unknowns embed. This
is the list needed for the contract's conditional claim, rather than silently
omitting potential minimal graphs. The report's `conditional_minimal` separates
the provisional entries. CONTRACT Section 10 amendment 2 corrects the earlier reversed wording
in Section 4.3 and adopts the existing status
`minimal_if_all_listed_deletions_embed`, as required by L-min. No classification
claim is authorized by this module: `claim_authorized` always remains false,
since the other publication gates are outside its scope.

### Control profiles

* B4p through B9p require no unknowns and exact equality of derived canonical
  minimal lists with the F9 members of the corresponding order. The expected
  counts for orders four through nine are 1, 1, 1, 3, 13, and 55. B4p through
  B7p implement control 7.0 from CONTRACT Section 10 amendment 1.
  B9p also searches each input for every applicable F9 member and requires
  `embedded` if and only if the graph is F9-free.
* `named` has exactly Petersen, Golomb, the pentagonal prism, the named
  extremal graph, and the Moebius ladder. Their canonical strings are generated
  by `named_graphs()` from explicit graphs, with the extremal input taken from
  CONTRACT. Golomb is a hexagonal wheel plus a disjoint triangle joined to
  alternate rim vertices. The first four must embed and the ladder must be
  refuted. The embedded records must be direct E-exact certificates, and
  `provenance` must map their g6 values to objects with
  `{"method":"general-search","evidence":"nonempty account of search origin"}`.
  The method is a producer assertion, not something coordinate checking can
  prove. Pointer/library hits cannot satisfy this named control.
* `regressions` uses an empty forbidden list and exactly K4, K2,3, F9 indices
  4, 9, 10, 17, 18, and the Moser spindle. The first seven must be refuted and
  the spindle embedded.
* B10 first requires accepted `checked/report.json` files in all eight control
  directories strictly inside the B10 run tree: B4p through B9p, named, and
  regressions. It then **rechecks each entire
  control run**; a supplied ACCEPT flag is never enough. A predictions file is
  required and hashed. File contents alone cannot establish that predictions
  or tests were committed before production, so that historical gate remains
  external. No git command is used or required by this module.

For control directories with custom output paths, copy/recreate the accepted
report at the documented default location before using them in a B10 run.
Rechecking always creates a fresh default report from their actual inputs.

## Outputs and resource behavior

The command prints exact lines of the form `ACCEPT record <g6> verified`,
`REJECT record <g6> <reason>`, and finally `ACCEPT run verified` or
`REJECT run <reason>`. The exit status is zero only on run acceptance.
An accepted unknown record means its declared unknown status was recorded and
covered correctly, not that the graph's geometry was decided.

The output directory defaults to `RUN_DIRECTORY/checked`. An output location
that would overwrite a supplied input file is rejected before any write. If
initial manifest parsing or this path guard fails, only the rejection line is
emitted, since no safe output location has been established. Otherwise it contains:

* `report.json`: status, counts, profile, consumed hashes, conditional entries,
  versions of SymPy and flint, ground-type setting, time and resident memory;
* `records.jsonl`: machine-readable per-record outcomes and reasons;
* `unknown-budgets.jsonl`: every unknown's reason and complete budget;
* `minimality.jsonl` when deriving: every deletion's verdict or block evidence;
* `L<n>.g6` for the corresponding order (four through ten), or `minimal.g6`
  for a sample derivation. The output collision guard and stale-output cleanup
  include every control filename.

Always consult the final report status. A rejection may leave partial evidence
from that attempted check. Starting a new check invalidates its previous report
and removes its old derived output files. Reports are atomically replaced.

Records are decoded one chunk at a time, bounded by 128 lines and 8 MiB of raw
JSON, with an 8 MiB per-line ceiling. Decoded certificates are released before
reading the next chunk. The SQLite index retains verdicts, dependencies and
small check details on disk; its cache is bounded to 8 MiB. It never stores all
certificate bodies in a Python list. Graph identifiers and final minimal lists
are smaller metadata and may be collected. Scratch SQLite files use
`/tmp/gp10-check/` and are removed on normal exit. Exact embedding bisection has
a budget of 2048 subdivisions. External canonicalization has a per-call timeout
of 60 seconds. R-tree also has the trusted kernel's own resource limits.
These limits can reject a difficult or oversized certificate but cannot turn a
failed check into an accepted mathematical conclusion.

## Independent audit regressions

The retained audit case data are replayed without importing auditor or producer
code. Every mutation is checked against its positive parent, including type
differences such as a boolean replacing an integer. Full cases invoke the
checker CLI in-process and assert its exact final status, reason, and any
required per-record reason. Helper cases assert the retained exact Sturm count.

```sh
nice -n 15 bash -c 'ulimit -v 1000000; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python research/gp-10/check/audit_regression.py --all'
```

Use `--case CASE_NAME` instead of `--all` to replay an audit case together with
its accepted parent. The source is `../check-audit/cases/`; it is read-only and
fingerprinted before and after replay. Outputs stay in `/tmp/gp10-check/round2/`
and the full summary is written to `round2-regression.json` in this module.

Only four audit expectations change: `unsupported-B4p` through
`unsupported-B7p` now reject for `control_unknown`, because the profiles are
recognized but those case records remain declared unknowns. Their original
audit reasons are retained in the regression result. All other audit
expectations are unchanged.

The same command runs the new wrong-minimal-list comparisons for B4p through
B7p, plus an actual complete frozen B4p run and its changed claimed list. The
comparison-helper positives for B5p through B7p do not certify full frozen
control runs. Their full accepted control trees, and an accepted B10 gate
replay, still require complete producer certificates.
