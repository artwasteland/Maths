# Round 2 integration notes

The D2 brief records the supervisor's failed B8p control. The original driver
kept failed maxima in the active embedding set. That scheduling error is
confirmed directly in the old maximal-set expression. The replacement removes
already-attempted graphs separately at each budget, exposing their subgraphs.

Repeated layer requests also reused output filenames. The embedder skips any
graph already present in its output, and the refuter rejects changes to input,
known-file hashes, budgets or source metadata at a reused path. Every request
now has an immutable input, known-record snapshot and fresh output directory.

The v1 refuter dispatches only tree and TU certificates explicitly and sends
all other types to its algebra verifier. Driver-generated sub pointers must
therefore be excluded from its known file. The export retains supported direct
certificates and a closed subset of their TU dependencies. Full output keeps
the pointers for the official checker.

An exit status of 2 is not evidence of argparse failure: the refuter also uses
it for ValueError and OSError. Captured logs include traceback and return status.
The supervisor's empty logs were not available here for retrospective replay.
Concrete reproductions and outcomes are recorded in the Round 2 report.

The controls are rerun after these explanations. A failed control authorizes
only diagnosis and retries of that control, not a B10 classification run.

The first real B9 pass exposed the dual scheduling problem. Refutation was
gated on all biconnected children already being embedded. Twenty-four further
refutations were found after removing failed minima from the current frontier
and giving tree search the full 40 seconds with 2,000 allowed states. The
control then had 97 refuted, 2,959 embedded and 29 unknown. A two-graph test
first failed because no refuter calls occurred, then passed in both frontier
directions at each configured budget. Minimality remains separately derived.

The real status-2 reproductions are in `round2/reproductions-asserted/` under
scratch. The first mutation attempt used the same path for its known file and
its output and hit the path guard. That was not the intended red fixture.
The corrected attempt uses distinct paths and asserts `algebra: invalid type`
for both the genuine pointer stream and the one-field tree type mutation.

A three-graph host-only sample at 60 seconds embedded H?QX`va but timed out
on H?DLHrp and H?DTJQx. The successful sample motivates a normal host-only
control retry. Probe outputs are diagnostic and do not silently modify the
control state; new records enter through the control runner and its checker.

The completed host-only retry added six embeddings. Final B9 counts are
2,965 embedded, 97 refuted and 23 unknown. Its checker line remains
`REJECT run control_unknown`, with zero direct certificate rejections.
B8 remains `ACCEPT run verified`, with 366 embedded and 17 refuted.

There is an additional embedder coverage blocker, not only four refuter
stalls. In a fresh six-method, 40-second probe, H`GO]Nw and H`QEpgl completed
in 0.883 and 0.400 seconds. All lattice sets exhausted, constructive search
reported no degree-two elimination, and every available host search completed
without a match. Numeric search failed to converge on the first graph; the
second candidate was correctly refused for exact coincident points 0 and 4.
These are unchanged producer choices, not integration failures or proofs of
non-embeddability. The other seventeen F9-free unknowns timed out in host-only
search at 60 seconds. No host stack-level diagnosis was performed.

The four refuter stalls remain unknown with tree-only 40 seconds / 2,000
states, enlarged-known-set TU at 60 seconds, and a stated all-saturation
null/real probe at 20 seconds total. The tree leaves are completed no-move
leaves. All-saturation algebra found no certifiable target for H_hP`SV and
hit both method deadlines for the other three graphs. Details and exact
reproduction commands are in REPORT.md and the scratch probe directories.

The requested state with everything except the four refuter stalls decided
was not achieved. Fixing the extra completed embedding failures needs new
search choices in the embedder, outside this builder's write authority.
No sibling module was changed, and the failed B9 gate does not authorize B10.

## Round 3 seeded assembly

The preceding notes describe the historical Round 2 snapshot, not the later
producer improvements described by D3. D3 expressly requests a full-B10
sample-profile assembly and check without a B10-profile control claim.

First-choice seed bytes are retained separately from parsed records. The
official checker validates selected certificates and their selected
dependencies before either propagation or producer scheduling. Only external
E-exact hosts are admitted; external R records are not legal hosts. Validation
failure does not cause an undocumented fallback to a later duplicate proof.

Two aggregator assumptions needed alignment with the checker: an external
E-exact host may have more vertices but the same number of edges, and an
indexed forbidden-list R pointer is a terminal witness even when its graph6
equals the input graph. Tests exercise both cases with genuine certificates.

Initial new-test failures were test-harness issues: three rejection assertions
omitted the checker's reason detail suffix, and one framing fixture mixed
vertex orders in a same-order poset. These were corrected without changing
the checker. The final suite has 23 passing tests, with retained genuine
positive checks and coordinate, pointer-map, DAG-coefficient and schema
mutations that are required to go red. A separate gate test requires
`REJECT run controls_required` for a B10 draft without controls.

The optional embedder round4 directory appeared after initial discovery work
and before the assembly's recorded discovery. The assembly consumed 328
JSONL files, selected 2,518 records and accepted all of them in 20 serial
samples. Four oversized source lines were counted and skipped before parsing,
not called checker-accepted records. All consumed source prefixes rehashed
identically in the final audit. There were no source changes during reading.

The full-input sample check ended `ACCEPT run verified`, with 31,159 embedded,
238 refuted, 1,765 unknown, 99 derived minimal and zero conditional-minimal
entries. The report's whole-run `conditional` flag is still true because of
the unknowns, and `claim_authorized` is false. The assembly-only work took
366.690 seconds; the final checker took 784.524 seconds. The full B10 draft
was not submitted as a classification claim. No producer search ran.

The final audit passed exact-set coverage, UNKNOWN equality, byte-for-byte
preservation of all accepted seeds, source-prefix hashes, and consistency of
the checker/kernel identities across seed validation and the final check.
Full evidence is under `/tmp/gp10-drive/round3-b10/`; seed regression evidence
is under `/tmp/gp10-drive/round3-regressions/`.
