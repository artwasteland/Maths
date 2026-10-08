# Round 4 usage

Run from the repository root, using the frozen interpreter and the stricter 1 GB address-space cap:

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/generic_exact.py --input research/gp-10/embed/results/round4/input-start.g6 --out research/gp-10/embed/results/round4/search --start 0 --stop 10
```

The generic mode accepts canonical graph6 lists, removes duplicate lines, calculates generic rigidity rank, and orders graphs by increasing `k = 2*n - 3 - rank`, then graph6. Rank computation and framed msolve support graphs with at most 10 vertices; unsupported cases remain unknown unless the host method certifies them. Edgeless graphs and graphs on at most two vertices have direct rational certificates. An input hash and configuration manifest must match on resume. Completed per-graph records are skipped, and every resumed embedding is checked again locally. A new output directory is required for a different budget or input. Outputs are confined to this module or `/tmp/gp10-embed/`.

The existing method entry points also accept generic input:

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2.py input --input INPUT.g6 --out /tmp/gp10-embed/msolve-input --msolve-cap 20
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3.py input --input INPUT.g6 --out /tmp/gp10-embed/g118-input --host-cap 10
```

Run commands separately, never concurrently. The parent has at most one child. Phase watchdogs, msolve and GP run sequentially. All descendants inherit niceness, the address-space limit and single-thread environment variables. GP also explicitly selects one thread. `SYMPY_GROUND_TYPES=python` is set before importing SymPy.

The combined default tries G118 first, then msolve. The per-graph method budgets are 10 and 20 seconds respectively, including proposal preparation, solver execution and exact conversion. Watchdog cleanup and file writes can add small wall-clock overhead. Host matching is capped at 3 seconds and 2,000,000 nodes. A mapped image gets its own field; the full host field is not constructed. Each GP execution has a graph-derived seed and requires the exact final marker `GP_FIELD_OK`, followed by the local certificate checks.

Msolve tries up to three actual edge frames. Flexible graphs get two pin proposals per frame, with different graph-derived numeric seeds, pin ordering and rational direction bounds. Rigid graphs get one unpinned attempt per frame. Each preparation has a 2.5-second cap. The remaining solver budget is divided across remaining attempts, reserving time for exact conversion. Success stops the search. A complete finite unpinned rigid result without distinct real points is retained only as unknown triage. Positive-dimensional output, pin failure, malformed output, conversion failure and timeout remain unknown. Pins propose embeddings and never justify a refutation.

The mandatory research sample is the supplied 1,515 candidates, not all B10. `round4.py prepare` freezes the source candidate file, tree results and then-current external embedding prefix. It requires passing local controls. `round4.py batch --start A --stop B` processes the launch-unresolved set. `round4.py collect` refuses to finish until the external embedding file contains complete records for all candidates. It recomputes the external unresolved set, merges all candidates, checks for contradictions, and writes `new-records.jsonl`, `merged-records.jsonl`, `UNDECIDED.g6` and `rigid-no-embedding.g6`. Existing rounds remain historical outputs.

Use `round4_selftest.py` for the paired local controls, `round4_finish.py controls` for independent checker controls, and `round4_finish.py audit` after the official sample check. Each command must use the same niced, limited interpreter prefix above. The complete executed batch ranges and checker command are recorded in REPORT.md.
