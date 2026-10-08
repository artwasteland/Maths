# Round 3 GP host completion

Read the Round 3 section of [REPORT.md](REPORT.md) for measured results.
All new outputs live in `results/round3/`. The round-two union remains intact.

`gp_field.py` converts the radical coordinates of an individual G118 image
using one PARI child. It never flattens the full host. Square roots already in
the current field are found with `nfroots`; new quadratic extensions use
`rnfequation`. `polredbest` keeps the representation manageable. A primitive
linear combination of the final image coordinates and exact linear algebra
remove unused extensions. The E-exact verifier checks every emitted graph.

PARI must use `default(nbthreads,1)` under this machine's memory ceiling.
The initial 180-second probe without that setting timed out with thread-stack
allocation warnings. Its output is retained in `probe-first-gap/`; the
single-thread repeat is in `probe-first-gap-single-thread/`. The initial
13-graph pass is in `pilot-before-explicit-seed/`. The final production pass
uses a seed from the canonical graph SHA256. A degree-16 image was repeated
byte-for-byte. The temporary field degree cap is 256.

`gp_special.py` parses the H1/H2 tables from the local TeX source. It uses the
figure's equilateral triangles to reduce each construction to five real
variables, then solves expanded polynomial equations with msolve. It uses
the guarded scratch binary and deterministic separator wrapper from round
two. Every candidate must satisfy the source equations, all nine printed
polynomials in z=x+iy, and the ordinary exact graph checks. H2's last two
printed rows describe offsets from (sqrt(3),0), as the figure shows. Their
polynomials are checked as offsets, and the graph uses translated points.
These positive construction constraints are never refutation premises.

Every command below runs from the repository root. Run them sequentially,
never with another worker-producing command active. There is at most one
parent and one child. The stricter contract limit, 1,000,000 KiB of virtual
memory per process, takes precedence over COMMON.md's 1.5 GB allowance.
All numerical thread counts and the SymPy backend are set by the imported
limits module before any symbolic or numerical library import.

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3.py controls
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3.py batch --sample gaps13 --stop 13 --cap 180
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/gp_special.py
```

The source/proposal preparation used a frozen-Python here-document with
`hosts.database`, `hosts.monomorphism` and `round2_phase.isolated`, a
10,000,000-node map cap and a 60-second watchdog. It wrote the 13 supplied
inputs, source hashes and complete mapped expression lists. H1/H2 mapping
checks and the optional-run observation used a second here-document calling
`monomorphism`, `check_mapping`, `verify`, and `round2_quiet.quiet_snapshot`.
Their results are `special-host-maps.json` and `optional-decision.json`.
The optional 990 maximal and 41 uniform inputs were not run because that
observation failed the pre-existing load and idle thresholds.

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3_finish.py collect
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3_finish.py controls
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/official_check.py research/gp-10/embed/results/round3/run --output research/gp-10/embed/results/round3/run/out > research/gp-10/embed/results/round3/run/checker.log
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round3_finish.py finish
```

The checker wrapper changes only its scratch location into the permitted
`/tmp/gp10-embed/` tree. It imports the unchanged official implementation,
checks its source hash before and after, and leaves verification intact.
It raises its own niceness from the launch value 15 to 19.

For a later authorized optional run, the same batch command accepts
`--sample maximal --start A --stop B` or `--sample uniform500` and reads the
round-two unknown lists. Bounds are zero-based and stop is exclusive.
Completed records resume without rerunning PARI; embedded records are
rechecked. Unknowns retain their measured budget and reason. The current
collector deliberately merges only the completed 13-graph scope and the two
exceptional hosts; extend its explicit scope when performing that later run.
