# Refuter interface and sparse polynomial certificates

Run with the frozen Python, with a niced process and the contract memory cap:

```sh
ulimit -v 976562
nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/refute/gp10refute.py IN.g6 --out OUT.jsonl --unknown U.g6 --time-limit 10 --forbidden LIST.json
```

Optional arguments: `--refuted KNOWN.jsonl`, `--methods tu,tree,null,real`,
`--max-states 200`, `--all-sat`, and repeatable `--extra-sat U V`. Extra
pairs refer to canonical input vertex labels and must be sorted nonedges. Methods run in the supplied order;
the default order is TU, tree, null, real. Each remaining method receives
an equal share of the remaining graph budget. A method is independently
selectable for measurement. The internal tree worker receives the state
limit and no embedding trials. The default saturation set contains the
non-adjacent diagonals of all four-cycles. `--all-sat` uses all nonedges.

Input is canonicalized with default nauty-labelg options. Duplicate
isomorphism classes are rejected before output. The input must be valid
graph6. Empty inputs are accepted. The forbidden JSON list can be empty.
Known records are checked locally and their TU dependencies are resolved
acyclically. Only the explicit known file supplies search dependencies, so
input order does not change graph seeds or mathematical search inputs.

Every finished record is flushed and fsynced. Resume is automatic when the
same output path is used. Metadata binds input, forbidden and known files,
budget options, and producer source hashes. Resume rejects mismatches,
checks completed refutations, repairs an incomplete last JSON line, and
rebuilds the unknown file from durable records. An fsynced pending-graph
journal turns a graph interrupted by a main-process crash into unknown on
resume, so a repeatedly crashing graph does not prevent later inputs. Completed unknown records
are retained; use a new output path for a larger budget. Timing observations
in unknown records are not byte deterministic. Decisions close to a wall
clock deadline can depend on machine load. A lock rejects concurrent writers.

Scratch is exclusively `/tmp/gp10-refute/`. TU and tree searches use one
child and no grandchildren. Polynomial searches run Singular as the sole
child of the producer. All inherit niceness and address-space limits.
Python exceptions, child crashes, memory errors, CAS timeouts and rejected
certificates become unknown attempts. A native crash in the main process
requires resume; see REPORT.md for the remaining limitation.

## Certificate encoding

The trusted GP-10 checker format file was absent when implementation began.
It appeared during final review. New R-real output now uses its string Sturm
field and underscore variable names. Historical object-form Sturm records
remain readable locally; `export_checker.py` converts copies for review.
This module uses the contract's generator keys and the following encoding.
Tree witnesses use the existing udcheck schema without changes. TU steps
and terminal witnesses use CONTRACT 3.2 without changes. Amendment 4 requires every TU chain to have at least one step. Direct
containment uses `sub`, with a global F9 `index` or an accepted-record `g6`
target. The forbidden list must match a prefix of the frozen F9 JSON;
indices retain the original global numbering. Stored F9 labels are used
for TU terminal maps; `sub` maps use the canonical target graph labels.

For frame `[a,b]`, variables are ordered `x_i,y_i` for vertices in ascending
order other than a and b, followed by `t0,t1,...` in saturation-list order.
Coordinates of a and b are `(0,0)` and `(1,0)`. Frame orientation matters.
Each saturation pair is sorted, distinct, non-adjacent and not repeated.
The frame must be an edge. No third vertex is pinned.

A sparse polynomial is a list of `[rational_string, exponent_vector]`
terms. Exponents are nonnegative integers in the variable order above;
coefficients are exact strings such as `"-3/2"`. Zero is `[]`. For example,
in variables `(x2,y2,t0)`, `[["2",[2,0,0]],["-1/3",[0,1,1]]]`
means `2*x2^2-y2*t0/3`. Duplicate monomials are rejected.

`cofactors` maps `e:u,v` or `s:u,v` to sparse polynomials. Missing entries
mean zero. Edges are sorted; the framed edge has no generator. There is no
certificate-supplied generator list, so an extra edge or non-edge equation
cannot be smuggled into the system. The checker regenerates the system and
expands the identity with python-flint, independently of Singular.

An R-null certificate has exactly `type`, `frame`, `sat`, `cofactors`.
The target is the constant one. An R-real certificate adds `f`, a sparse
polynomial, and exactly one of:

- `"sturm":"y_2"`: f is nonconstant, involves only this
  variable, and has no real roots. Root counting is recomputed exactly.
- `"sos":{"c":"1/2","squares":[["3",Q],...]}`: c and every weight are
  positive rationals; f equals c plus the weighted polynomial squares.
  The empty squares list is allowed, so a positive constant also qualifies.

The checker document agrees with the sparse coefficient encoding. Its Python
implementation was still absent at final review, so no independent checker
acceptance is claimed. Its document requires nonempty TU steps and interprets
forbidden indices globally in F9. The contract describes indices in the list
in force and does not explicitly forbid an empty chain with a valid endpoint.
The producer retains the contract semantics. The measured known-endpoint CLI
chain is nonempty, and the exported GP sample has no TU records. Arbitrary
short forbidden lists and zero-step TU records need supervisor reconciliation.

## Round 2 replay and targeted proofs

`--methods reuse,tu` first replays the exact certificate for a matching
canonical graph from `--refuted`, then searches containment/TU closure.
The known file is verified before any replay. Reuse is optional and is not
part of the default search order. A copied certificate is verified again
within the graph budget. This is proof replay, not a fresh discovery budget.
The known file must be checked under the current forbidden prefix.

The Round 2 accepted library is `evidence/round2/GP73.refuted.jsonl`.
Specialized discovery commands are `real_radical.py --index 22` or
`--index 38`, and `centroid66.py --frame 6 7 --reduce --scale
--homogeneous --padding 6`. Each also takes `--seconds` and a fresh `--tag`.
See REPORT.md for measured budgets and the unresolved index 39.

`round2.py check --path RUN_DIRECTORY` invokes the official checker
in-process after relocating only its scratch directory to
`/tmp/gp10-refute/official-checker`. It does not alter proof checking,
parsing, limits, profiles, or acceptance logic.

The proposed intermediate-identity encoding is documented in PROOFS.md.
`ideal_derivation.py` is an experimental local verifier. Its JSON document
is not a producer record and is excluded from all checker run manifests.
It does not authorize an additional certificate type.

## Round 3 and amendment 5

The proposal status above is historical. The official checker now accepts
`null-dag` and `real-dag` with `frame`, `sat`, and a nonempty `rows` list
(up to 256). Each row has exactly `poly` and `cofactors`, whose sources are
original generators or strictly earlier `aux:j` rows. Every sparse
polynomial, including real targets and SOS squares, is sorted by strictly
increasing lexicographic exponent vector and omits zero coefficients.
`real-dag` also has `f` and exactly one of `sturm` or `sos`.

The optional `dag` search emits these shared identities. The optional
`portfolio` method shares one Groebner basis computation between constant
unit-ideal and real-obstruction targets. It emits ordinary null/real when
compact, or a DAG when a conservative expansion estimate exceeds 60000
monomial products. The estimate affects encoding only; every final identity
and positivity proof is checked exactly. The default method sequence is
unchanged. Explicit known files may now contain DAG certificates.

`candidate_batches.py` reads the live streams named in the Round 3 brief,
records complete-line snapshot hashes, and writes only to
`/tmp/gp10-refute/cand/`. It processes increasing edge counts, waiting for
lower-edge pending tree records before starting the next level. Completed
tree fixed-point searches are retained; time/state failures get a 12-second
retry. A 0.5-second TU pass uses F9 and independently checked prior
refutations. A 5-second algebra portfolio uses an edge frame chosen first
by common-neighbor count, then endpoint degrees, then lexicographic order.
Every batch reserves at most 240 seconds of method budgets. A native crash
is recovered from the pending record on the next identical invocation.
Every emitted refutation is checked in its batch with all referenced proof
dependencies. Unknowns remain explicit. This is a sampled candidate search,
not an authorized B10 classification or a minimality derivation.
