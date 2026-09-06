# cnf-audit: the record of job orchard-cnf-audit, moved out of scratch/

These files were committed by the cloud worker on branch
`claude/reaching-noether-cloud-cnf-audit` under `chiro/scratch/cnf-audit/` (scratch is
ignored in the main tree). They are copied here byte for byte so the main tree carries
the provenance that RESULT-15-32.md Section 3 cites: the four (15,32) cube CNFs
regenerated on an unrelated machine, their sha256 (`SHA256SUMS`), their `p cnf`
headers (`c*.log`, `AUDIT.md`), the cnfcheck decode logs for the regenerated and the
worker files, and the sha256 of every depth-2 child CNF (`depth2-c3-regen-SHA256.txt`).
The compressed CNFs themselves (about 10 MB) stay on the branch; they are regenerable
with `python3 chiro/exist.py 15 32 --backend cadical --cubes --cube-index k --cnf-only`.
