# The GP-11 architect's prototypes (2026-10-01, codex gpt-6-astra, scratch /tmp/gp11-architect/)

Copied from the architect's scratch so builders and cloud tasks can read them. Untrusted producer code: nothing here
is a certificate or a checker. `../REPORT.txt` is the consultation, `../AUDIT.txt` the order-10 audit of GP-10's tools,
`../BUILD-JOBS.txt` the job specifications, `../MEASUREMENTS.json` the measured numbers, `../sample-manifest.json` the
seeded 500-graph sample (seed 20261001, indices into the sorted B11). Here: `extension.py` + `extension-current.gp`
(the degree-two extension prototype, 445 of 500), `tu.c` + `tu_bench.py` (TU closure; `tu-all-refuted.g6` is the
full-population closure's 3,323 refutation proposals, NOT checked beyond the sample), `poset.c` + `propagation.py`
(the B11 edge-deletion poset: 4,721,083 relations), `rigid_system_order11.py` (the rigid-system front end with the
order limit raised to 11, scratch only), `post-msolve-unknown.g6` (the sample's 13 unknowns), and the per-method
summaries.
