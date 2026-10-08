Each completed sample directory is a portable checker bundle.
Run `drive.py replay` as described in the runbook; reading its summary alone
does not recheck the certificates.

`architect-500-release` uses the architect's exact 500-graph input file.
`architect-500-final` repeats that input from empty state after fault-path hardening.
`escalation-2000.g6` and its selection manifest preserve the second sample
from the escalation experiment; the 500 graphs are excluded from that draw.
Counts in `summary.json` refer only to assigned graphs.
The frozen checker report also counts supporting proof records.

`controls.json`, `resume.json`, `reuse.json`, `merge.json`, `merge-cycles.json`,
`failures.json`, `history.json`, and `rounds.json` record the
rule mutations, actual crash recovery, TU endpoint reuse, transaction
rollback, cross-shard import, grounded proof alternatives, and failure recovery.
`hardening-validation.json` binds the earlier receipts in `hardening-controls/`
to the sources used before the imported-history fix.
`final-validation.json` binds all final control receipts, including the repeat-round
and history regressions, to the final runtime and test files.
`tu-population.json` compares the 3,323 certified TU decisions with the architect's
complete hit set; it never treats that hit list as a certificate.
`measurements.json` records elapsed times, resources and explicit cost formulas.
`escalation-round2-input/` demonstrates the small allocation of the four remaining
graphs, preserving all 23 prior stage outcomes for each graph.
`poset-build.json` and `poset-validation.json` bind the deletion index and
the independent checks of its maps and both adjacency directions.
`environment.json` records the measured GP-10 toolchain and exact preflight.

`measured-sources.tar.gz` preserves the pipeline sources used in the long,
source-pinned measurements before subsequent fault-path hardening.
`measured-sources.json` lists every member hash and the archive hash.
Each job manifest independently binds those producer source bytes.
`hardened-sample-sources.tar.gz` and its hash manifest preserve the subsequent
fresh 500-graph run and its associated controls.
All sources outside the pipeline remain the repository's unchanged files.
The frozen checker and mathematical certificate formats are unchanged.
REPORT.txt describes any later changes and their separate validation.
