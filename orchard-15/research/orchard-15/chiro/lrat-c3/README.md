# lrat-c3: the record of job orchard-15-32-lrat-3 (cube 3, kissat, drat-trim -L, cake_lpr)

Copied byte for byte from branch `claude/reaching-noether-cloud-orchard-lrat-c3`, directory
`chiro/scratch/exist-15-32-lrat-c3/` (scratch is ignored in the main tree). The 2 MB compressed
CNF stays on the branch (regenerable, hash 3ce6b8b9...). Read INCIDENT-proof-unlinked.md first:
the worker's disk guard unlinked the 3.7 GB DRAT after drat-trim had accepted it and written the
16.06 GB LRAT, so exist.py crashed at its post-check stat and the JSONL record here was assembled
by the worker from the logs, not emitted by exist.py. cake_lpr: `s VERIFIED UNSAT`, exit 0.
