# GP-11 build job A notes

2026-10-01, local checker/profile build in the detached job-A worktree.
No state-changing git commands were run.
The frozen GP-10 checker and u(22) kernel were read and left unchanged.
The new structural proof notes were written before implementing the profile.

The first unchanged GP-10 regression harness invocation reached the DAG tests
and stopped because the adapter exposed GP-11's HERE directory to the old
fixture loader. It sought `gp-11/check/fixtures/round3/cases.json` instead of
the original GP-10 fixture. This was an adapter path error, not a certificate
rejection. The adapter now preserves all original module paths and substitutes
Checker, Run and the CLI. The unchanged corpus was rerun successfully after this correction.
Its 154 checks passed, including 116 mutations with exact rejection reasons.
The adapter also rechecked all original DAG positives after their mutations.

The small control replay uses a fresh extraction of GP-10's retained public
tree and its final record stream, SHA-256
`577c1f8de771dc80832c4cddce39f7efc2fad5dee3363480805b379e7e87f20e`.
No ten-vertex forbidden answers are seeded into B10.
One guarded heavy process runs at a time; other test/checker invocations wait.

The full B10 replay is left for the dedicated cloud command in
`check/CLOUD-RUNBOOK.md`. Local tests of complete-control report validation use
GP-10's real retained complete report and list, with one-field mutations.
They test rejection rules, not a substitute for the full certificate replay.
The writer's receipt fixtures are explicitly synthetic and create no B11 claim.
Neither G2 nor G5 is closed by those unit fixtures.

Input freeze and independent recount are another build job.
Until its B11 file and SHA256SUMS land, the B11 freeze rules are tested against
temporary fixture files through the same checker methods.
Fixture runs cannot authorize publication.

The small controls all passed locally: B4p through B9p, GP-10's named graphs,
regressions with an empty list, and the two new named11 instances.
Both new named embeddings were found by lattice18 in twelve search nodes.
No coordinate lookup or host method was enabled.
Their exact records, invocation and search statistics are retained under check/fixtures/named11/.

The eleven-vertex minimality fixture was built by bounded general search on
each biconnected deletion of the pilot tree-refuted graph.
All sixteen deletion classes produced exact embeddings.
The fixture checker derived one unconditional minimal member and kept the
single-UNKNOWN variant conditional, as required.

The kernel's unchanged selftest passed all 41 checks, including 23 mutations.
During final code review, malformed control objects/reports were found to need
explicit type guards before receipt traversal. These guards and their own-rule
reds were added; the full GP-11 selftest was rerun after the change.

The final named-graph input is hash-pinned to AMP's graph6 source so the
control problems cannot drift while leaving the wrapper unchanged.
The full own-rule suite was rerun after this pin was added.
A separate integration test exercises B11's actual execute path with the
temporary freeze and confirms `controls_required` precedes the census check.

The unchanged kernel harness originally checked exit status and an ACCEPT/REJECT
marker. The new adapter additionally compares all 23 refusal messages exactly,
normalising only temporary/repository path prefixes, and restores every positive
input and the original result after the reds. One legacy label says "L2 modulus"
although the fixture reaches the L2 ratio guard first; the expectation names its
actual rule and claims no independent modulus-guard coverage.

The final containment review also covers the control report file itself,
including symlinks, as well as the control directory. A byte-identical accepted
B4p report is retargeted from inside to outside the run tree and must fail at
`control_outside_run_tree` in both control preflight and receipt traversal.
The original report is restored and rechecked. The full own-rule suite was
rerun after this change.

Final GP-11 own-rule verdict: `GP11 SELFTEST PASS checks=72 rejected_mutations=49`.
The output-collision red is also asserted separately in that suite.
The guard observed at least 3968396 KiB MemAvailable and exited zero.
