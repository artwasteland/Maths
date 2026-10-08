# Development predictions, before measurements

This is a module development sample, not the gated full B10 pipeline. The
shared PREDICTIONS.md and PROOFS.md are absent. No global gate is claimed.

The finite direction search should cover a substantial part of the uniform
sample but less of the edge-maximal set. Wider direction sets should add
some hits while spending more time. Constructive placement should mostly
help low-degree graphs. Host matching should add library hits, especially
on the smaller control set. Numeric recognition is expected to leave many
unknowns because a small residual is insufficient for exact acceptance.

Measurements will record per-graph budgets and method times. Long methods
will use a stated deterministic sample under the common five-minute rule.
Unknowns are expected and will remain explicitly unresolved.

## Measured pilot model before coverage stages

The command recorded in REPORT.md sampled each declared input, searched with the lattice node cap, and verified every success. Linear extrapolation ignores worker startup, scheduling and the difference between node and wall limits. These are predictions, not coverage claims.

| Input | Pilot successes | Pilot seconds | Predicted lattice successes | Predicted seconds |
|---|---:|---:|---:|---:|
| maximal | 9/20 | 1.418 | 1137 | 179.068 |
| uniform500 | 18/20 | 0.326 | 450 | 8.155 |
| B9p | 19/20 | 0.112 | 2931 | 17.342 |
