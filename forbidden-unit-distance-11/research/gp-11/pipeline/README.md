Run [RUNBOOK.txt](RUNBOOK.txt) for worker setup, sharding, resumption, replay,
git returns, coordinator intake, and subsequent rounds.
Read [REPORT.txt](REPORT.txt) for validation and measured cost.

The CLI is `drive.py`.
`poset.c` and `poset.py` build and map the complete deletion order.
The graph IDs are frozen B11 line numbers, starting at zero.
Relations retain child-to-parent label permutations.

`store.py` keeps accepted decisions, stage attempts, dependencies, and leases
in SQLite, with proof bytes in an append-only offset-and-hash store.
No decoded population-sized proof collection is retained in memory.
Global reach is a scheduling hint until a frozen-checker pointer passes.
Only accepted records create decisions.

`tu.c` and `tu.py` propose forced chains, replay GP-10 endpoints through F9,
and transport checked verdicts across known closure classes.
`extension.py` uses the landed extender and tries one-edge alternative B10 bases.
`stages.py` defines the ordered budgets and skips every graph already decided.
`rigid_system.py` raises the producer's order limit to eleven.
The other search modules port the measured escalation portfolio.
`branch_refute.py` and `subfield_exact.py` follow that portfolio in the `full-late` policy; `late` runs them
(after a fresh numerical search) on a residue that has had `full`, which itself is unchanged.
[LATE-STAGES.md](LATE-STAGES.md) describes their budgets, proof construction,
retained analyst hints, standalone commands and reproduction tests.
[LATE-STAGES-REPORT.md](LATE-STAGES-REPORT.md) records the measured coverage,
frozen-checker receipts and mutation controls.
[PORTS.json](PORTS.json) identifies their original sources and hashes.
The temporary original paths are provenance only; running needs no such paths.

`export.py` builds dependency-complete sample runs and replays the frozen checker.
It exports exact coverage, UNKNOWN records, structure, histories, and core packets.
It also independently rechecks incoming bundles and their declared assignments.
The certificates remain GP-10's ordinary formats.
The GP-11 profile validates frozen source/data pins before the sample checker loads.
`coordinator/rounds.py` allocates only the checked UNKNOWN frontier for a repeat
round and verifies its returned assignment union. The driver still independently
checks all returned certificates when it merges that round.

`test_pipeline.py` checks the five required red mutations and their positive parents,
plus expired/stale leases and changed certificate bytes.
`test_resume.py` kills a real worker mid-extension and introduces a torn write.
It compares the complete mathematical artifacts after recovery and another resume.
`test_reuse.py` checks TU transport only after a verified endpoint and injects
a transaction failure between the decision and attempt writes.
`test_merge.py` imports real seed and UNKNOWN shards, checks both propagation
directions, and rejects missing or duplicated shard assignments.
`test_merge_cycles.py` merges individually valid shards whose shortest proofs
would form a dependency cycle. Intake retains grounded alternatives and rejects
an unanchored cycle, then rechecks the original positive merge.
`test_failures.py` injects a producer failure after a verified endpoint, checks
bounded raw intake, preserves imported UNKNOWN budgets, and exercises a stop
at the initial memory check.
`test_rounds.py` allocates a real UNKNOWN frontier, returns two checked worker
bundles, rejects missing/extra/duplicate round assignments, and merges the
improvements with the prior bundle through a fresh frozen replay.
`test_history.py` merges three generations of UNKNOWN records, keeps their
distinct attempts, and checks that inherited history appears once after
repeated imports and resume.
`preflight.py` checks existing tools, versions, the msolve shim, and an exact control.

These outputs are certificate-workflow evidence.
They do not discharge the contract's full controls, minimality, or publication gates.
