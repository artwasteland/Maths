# B10 final run (gate G3), 2026-09-25

The B10-profile run of the official checker (sha256 `d717816b…`) over every one of the 33,162 graphs in
`data/B10.g6`, with the eight controls (B4p..B9p, named, regressions) re-verified inside the same run. Executed on a
cloud worker by `coordination/cloud-workers/gp10-final.sh` (tag fin2); the records are the lean assembly
`research/gp-10/cloud/lean3/records.jsonl.gz` (sha256 in `inputs.sha256`), built by `tools/lean_assemble.py` from the
seed bundle `research/gp-10/cloud/assembly/asm3/`.

- `report.json`: the checker's report (status ACCEPT, reason verified, profile B10, 0 unknown, not conditional).
- `L10.g6`: the 324 certified minimal forbidden graphs on 10 vertices, as written by the checker.
- `minimality.jsonl`: the checker's minimality evidence for every refuted graph.
- `check.txt`: the checker's log without the per-record ACCEPT lines (full log on the fin2 worker branch).

Re-check: extract the records, rebuild the tree from `research/gp-10/cloud/final/tree.tar.gz`, and run
`python research/gp-10/check/gp10check.py <tree> --output <out>`; see `gp10-final.sh` for the exact steps.
`../../RESULT.md` is generated from this directory by `tools/write_result.py`.
