# Certified embedding producer

Run from the repository root with the frozen interpreter:

```sh
ulimit -v 1000000
nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/gp10embed.py \
  research/gp-10/embed/results/named/input.g6 \
  --out /tmp/gp10-embed/demo.jsonl \
  --unknown /tmp/gp10-embed/demo-unknown.g6 \
  --stats /tmp/gp10-embed/demo-stats.jsonl --time-limit 30
```

Input lines must already have the intended canonical graph6 labelling. The
producer preserves that labelling. Every new input graph gets an E-exact
record or an unknown record. It never emits a refutation. Blank lines and
a separate graph6 file header are ignored. Repeated graph codes are skipped.

The default order is lattice18, lattice36, lattice30, constructive, host,
numeric. Use `--methods` with a comma-separated subset to isolate methods.
Exclude `host` for general-search controls. `--node-cap` bounds lattice
recursion and the constructive core search; the host matcher uses a multiple
of that cap. Per-method allocations carry unused time forward. A parent
watchdog enforces the total wall budget with only one child alive at a time.
Initialization of shared libraries and host data precedes graph timing.
The program also sets its niceness, memory ceiling, SymPy backend, and
numerical-library thread limits. It is intended for the supplied Linux
fork environment.

Exact acceptance uses rational polynomial reduction and rational interval
arithmetic. No floating point residual or separation threshold can accept
an embedding. Numerical routines may only propose candidates or discard
search branches. The producer implements its own check and does not import
the official checker.

Records and optional statistics are flushed per graph. Resume rechecks
existing exact records, skips all existing verdicts including unknowns,
repairs a malformed final fragment, and rebuilds the unknown projection.
Use a fresh output file when retrying unknowns with different budgets.
Use the same input set when resuming. Concurrent writers to one output file
are not supported.

`host_sources.json` snapshots GP notebook expressions and the AMP coordinate
expressions read from the earlier producer. `host_certificates.json` holds
reusable fields for exact hosts and a simple-coordinate subset of G118.
The full G118 expressions remain available for bounded per-map conversion.
The emitted certificate always contains coordinates for the input graph,
so it does not require a host pointer or an external host certificate file.

`selftest.py` runs positive, mutation, crash, timeout and resume controls.
`prepare_hosts.py` and `prepare_g118_subset.py` rebuild the library caches.
`measure.py` prepares the prescribed input samples, measures individual
methods on unresolved graphs, and audits the combined outputs. Re-running
a stage replaces only its named measurement artifacts. See REPORT.md for
the actual commands, budgets, timings, coverage and unresolved limitations.

Round 2 adds the standalone rigid and pinned msolve producer. See
[ROUND2.md](ROUND2.md) for usage and limitations, and [REPORT.md](REPORT.md)
for measured coverage and official checker results. The current merged
union is [results/round2/union-records.jsonl](results/round2/union-records.jsonl).

Round 3 completes the supplied nine-vertex gaps using G118 image fields and
reconstructs H1/H2 from the paper's tables. See [ROUND3.md](ROUND3.md) and the
Round 3 report. Its current union is
[results/round3/union-records.jsonl](results/round3/union-records.jsonl).

Round 4 adds generic graph6 input and resume to the msolve and G118 methods.
See [ROUND4.md](ROUND4.md) and the Round 4 section of [REPORT.md](REPORT.md).
The checked candidate sample is
[results/round4/merged-records.jsonl](results/round4/merged-records.jsonl), with
[results/round4/UNDECIDED.g6](results/round4/UNDECIDED.g6) listing its remaining unknowns.
