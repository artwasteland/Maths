# Build job A: GP-11 checker profile and gates

2026-10-01. New wrapper and publication logic, requiring outside review.
No state-changing git commands were run.
No existing GP-10 files were edited.
No dependencies were added.

## Read first

1. `../CONTRACT.md`, then `../PROOFS.md` for the order-eleven structural arguments.
2. The numbered delta header in `gp11check.py`, then its marked functions.
3. `../tools/write_result.py` and `FORMAT.md` for publication and receipt semantics.
4. `selftest.py` and `results/gp11-selftest.txt` for each own-rule red and restoration.
5. `CLOUD-RUNBOOK.md` for the remaining full B10 replay.

The original checker is still
`d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04`.
The original kernel is still
`63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de`.
The frozen forbidden-398 JSON is still
`8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c`.

## Files and reasons

| New file(s) | Purpose |
|---|---|
| `../PROOFS.md` | L-block, L-min, L-complete at eleven; provenance and receipt trust boundaries |
| `gp11check.py` | B11, named11 and fixture11; frozen verifier delegation; controls, minimality and receipts |
| `../tools/write_result.py` | G6 refusal and report-only rendering, with review and artifact hashes |
| `FORMAT.md` | Manifest, output, control and gate-receipt interfaces |
| `selftest.py` | Order-eleven positives, exact own-rule rejections and restoration checks |
| `regression.py` | Execute unchanged GP-10 tests/fixtures through Checker, Run and CLI adapters |
| `gate_integration.py` | Exercise actual B11 dispatch with a temporary freeze; assert the control gate is reached |
| `kernel_reasons.py`, `kernel-rejections.json` | Assert the unchanged kernel corpus's exact refusal text and restore every positive invocation |
| `fixtures/lattice11.json`, `tree11.json`, `tu11.json` | Retained self-contained architect pilot certificates |
| `fixtures/minimality11.jsonl` | A genuine refutation and sixteen checked exact deletion certificates |
| `fixtures/named11/*` | Both AMP graphs, newly searched exact certificates, command provenance and search stats |
| `fixtures/README.md` | Fixture provenance and the intact forbidden-block construction |
| `../tools/prepare_controls.py` | Fresh scratch extraction of the retained GP-10 evidence and record-hash check |
| `../tools/small_controls.py` | Sequential lower-control replay and new general search for named11 |
| `../tools/make_minimality_fixture.py` | Untrusted bounded search used to produce the retained deletion certificates |
| `../tools/guard.py` | One command at a time, one numerical thread, nice 15, address-space and available-memory limits |
| `CLOUD-RUNBOOK.md` | Exact B10 control command, expected complete result and same-tree deployment |
| `../LABNOTES.md` | Build history, harness corrections and remaining gates |
| `results/*` | Retained verdict/rejection logs and source/artifact hashes |

## Header's change list

The profile header labels nine changes; every added/overridden function has a B11 marker.

1. Pin/import the frozen checker, kernel, F9, F10, gadgets and AMP instances; record review source hashes.
2. Extend the pattern table through order ten, preserving indices and the default search ceiling nine.
3. Permit blocks through ten and explicitly search them through ten.
4. Add B11/named11/fixture11 orchestration, external freeze binding, census count, L11 cleanup and output guards.
5. Replay same-tree controls and require complete B10 with the exact 324-derived-list agreement.
6. Extend the unchanged edge-deletion minimality algorithm through eleven and emit L11.
7. Check the two named order-eleven graphs, direct embeddings and general-search provenance.
8. Bind consumed streams and other artifacts; preserve legacy profile decisions by delegation.
9. Expose the CLI and the stronger complete-B10 control command.

The writer separately marks W1 (complete report/artifacts), W2 (G0..G5/current review),
and W3 (rendering and output protection).
The only new mathematical decision code is the pattern-table/block extension and
the eleven-vertex minimality orchestration; individual proof routines remain frozen.
The profile and writer still need G5 review in their entirety.

## Local tests

The complete logs are retained under `results/`.
`results/control-reports/` retains the actual local small-control reports,
including each invocation's source hashes and environment.
`results/build-manifest.json` binds the final files and logs for handoff;
it is build metadata, not a G1 commit or G5 approval.
Their red verdicts assert exact rule names, including record-level reasons when
the enclosing run reports `records_rejected`.
The unchanged DAG CLI tests check their record reasons as well as the run status.
Real, unmutated evidence is replayed after the reds and must recover its original result.

GP-10 regression corpus, unchanged: `SELFTEST PASS checks=154 positive=38 rejected_mutations=116`.
Its original certificate/run verdicts are restored after mutation, including DAG positives.
The trusted kernel's unchanged corpus: `SELFTEST PASS checks=41 positive=18 rejected_mutations=23`.
The added harness asserts all 23 complete refusal texts and restores all seventeen
positive checker invocations, plus the written proof models, after the reds.
An original kernel fixture named "L2 modulus mutation" reaches the ratio guard;
its expected text explicitly asserts that rule, not modulus-guard coverage.
The GP-11 suite: `GP11 SELFTEST PASS checks=72 rejected_mutations=49`.
Its exact rejection text is in `results/gp11-selftest.txt`.
The separately asserted L11 output-collision red also passes.
The final GP-11 suite's lowest MemAvailable was 3968396 KiB, above the
1572864 KiB stop threshold; its resource guard exited zero.
The integration log records `B11 GATE INTEGRATION PASS`: declaring the positive
fixture as B11 reaches `controls_required`, not a later census failure.

Reproduce the local suites sequentially from the repository root:

```sh
GP11_PY=<repo>/pyenv-gp10/bin/python
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/check/regression.py
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/check/selftest.py
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/check/gate_integration.py
"$GP11_PY" research/gp-11/tools/guard.py -- "$GP11_PY" research/gp-11/check/kernel_reasons.py
```

| Control | Verdict | Embedded | Refuted | Unknown | Derived minimal |
|---|---|---:|---:|---:|---:|
| B4p | ACCEPT / PASS | 2 | 1 | 0 | 1 |
| B5p | ACCEPT / PASS | 3 | 4 | 0 | 1 |
| B6p | ACCEPT / PASS | 14 | 2 | 0 | 1 |
| B7p | ACCEPT / PASS | 56 | 4 | 0 | 3 |
| B8p | ACCEPT / PASS | 366 | 17 | 0 | 13 |
| B9p | ACCEPT / PASS | 2984 | 101 | 0 | 55 |
| GP-10 named | ACCEPT / PASS | 4 | 1 | 0 | — |
| regressions, empty list | ACCEPT / PASS | 1 | 7 | 0 | — |
| named11 | ACCEPT / PASS | 2 | 0 | 0 | — |

These local legacy controls use the exact frozen Run implementation.
Later wrapper receipt/schema hardening does not replace that implementation.
The final B11 gate nevertheless replays every control with the final profile.
The new named11 certificates are also replayed in the final own-rule suite.
Both were found by lattice18 in twelve search nodes, with the host/library method disabled.
Their producer budgets were twenty seconds per graph, 200000 nodes.
Search provenance is an assertion with retained command/stats; exactness is checked independently.

Order-eleven fixtures accept an exact lattice embedding, an exact rational path,
a tree refutation, a TU chain and a lifted polynomial refutation.
The minimality fixture accepts one derived minimal member with all sixteen
biconnected deletion classes embedded; other deletions use checked blocks.
Replacing one deletion class by UNKNOWN leaves `conditional: true` and
`minimal_if_all_listed_deletions_embed` with exactly that required deletion.
An additional real refutation pointer gives a nonminimal eleven-vertex graph;
its known refuted deletion defeats all the other UNKNOWN deletions.

The principal new own-rule rejection reasons are:

| Mutation | Exact reason |
|---|---|
| Wrong externally pinned B11 digest / omitted frozen candidate | `frozen_input_hash` |
| Missing candidate certificate | `coverage` |
| Partial B10 ACCEPT: unknown, conditional, conditional minimal or rejection | `b10_incomplete` |
| B10 using order-ten answers | `b10_control_input` |
| B10 derived list missing a member | `b10_derived_list` |
| Byte-identical accepted control report symlinked outside the run tree | `control_outside_run_tree` |
| Intact ten-vertex forbidden block | `block_forbidden` |
| Missing order-eleven deletion proof | `minimality_deletion_missing` |
| Claimed minimal with an accepted refuted deletion | `minimality_claim_refuted_deletion` |
| Otherwise-ACCEPT conditional publication report | `writer_conditional` |
| Review bound to a stale source hash | `writer_stale_review` |

Every additional red's exact text is retained in `results/gp11-selftest.txt`;
the unchanged corpus's reds are in `results/gp10-regression.txt` and `results/kernel-selftest.txt`.
The block red first verifies an injective, edge-preserving identity map from
the full ten-vertex forbidden pattern into its host. It reaches the block rule itself.
The report-path red preserves the accepted report bytes and changes only the
symlink target; both control preflight and receipt traversal enforce containment.

## What remains

The full B10 control was not replayed locally; use `CLOUD-RUNBOOK.md`.
GP-10's recorded full run took 3156 seconds on a cloud worker.
The local B10 gate tests compare the real retained complete report and list,
then mutate fields; they do not claim a new complete certificate replay.
The result writer's receipt tests are explicitly synthetic unit tests, not
evidence that an outside review or full B11 classification occurred.

B11 freeze/recount is another job and its digest remains an explicit parameter.
No B11 result, G2 closure, or G5 approval is asserted here.
The coordinator must commit the tests, complete the cloud control, freeze and
commit predictions before the B11 run, and obtain the outside review.
Only then can the final checker run and evidence-backed G0..G5 receipt authorize G6.
