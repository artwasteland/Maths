# Round 2 exact solver

`round2.py` is the standalone batch entry point. It keeps one parent and at
most one child active. Preparation and conversion use isolated children,
which finish before the msolve child starts. Do not invoke this backend from
the round-one CLI's existing worker, since that would introduce a third
process. All results are in `results/round2/`; the original union and the
module-level UNKNOWN.g6 are historical round-one outputs.

Use the frozen Python with `-B`, `nice -n 15`, and `ulimit -v 1000000`.
The scripts set the SymPy ground type and numerical thread environment
before library imports. `round2.py prepare` creates the exact requested
cohorts. Build `msolve_seed.c` with the separate compile and link commands
in COMMANDS.md, then run `round2_selftest.py`.

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2.py batch --sample maximal --start 0 --stop 10 --cap 20
```

Replace the sample and index bounds to continue. The other samples are
`B9p` and `uniform500`. Batch bounds are zero-based and stop is exclusive.
Existing completed records are skipped; existing embeddings are rechecked
when resuming. Graph identifiers and seeds do not depend on batch indices.
Per graph, preparation has an 8-second hard cap, msolve has a 20-second
first-pass cap, and conversion has a 15-second hard cap. Failed preparation
is unknown without inventing a pin or launching an unpinned flexible system.

`round2_quiet.py` checks shared-box conditions before each optional 120-second
retry of an msolve timeout. It stops on a busy observation and records why.
`round2_reconvert.py --sample maximal` can convert saved complete output
without rerunning msolve; it preserves earlier records and charges the retry.
`round2.py collect` merges the new certificates with the original union,
writes the triage and timeout files, and creates `results/round2/run/`.

Every system frames an actual edge. Generic rigidity rank is evaluated
exactly at three deterministic random integer placements. The attained rank
must match either the elementary edge/motion upper bound or the exhaustive
(2,3)-sparsity matroid rank. For k positive, directions are chosen at a
numerical configuration with no near coincidence and full numerical rank.
Each rational unit direction is imposed by two linear equations replacing
the edge's unit equation, a net addition of one local constraint. These
are positive-certificate search restrictions, never refutation premises.
A certified implicit-function neighborhood is not constructed, so persistence
after rational pinning is a stated limitation.

msolve receives expanded polynomials only. Its variable permutations,
additional separating variable, rational coordinate denominators, and
ideal multiplicities are parsed explicitly. Coordinate boxes follow the
printed variable order. Denominators are inverted with python-flint separately
modulo each irreducible eliminant factor. The selected factor describes the
same separating element. Exact input-equation checks and the local E-exact
checker precede every emitted embedding. The output eliminant cap is 1024;
the E-exact factor-degree cap is 256. Native crashes and hard timeouts become
unknown records.

`rigid-no-embedding.g6` is solver-dependent triage only. A graph enters it
only with k=0 and no pins, when msolve gives an empty solution set or its
finite parametrization has no injective real solution. The finite branch
checks real-root counts with exact Sturm sequences and proves coincident
pairs modulo every real factor. Completeness of the CAS result is not a
refutation certificate. All listed graphs retain unknown verdicts.

The installed CLI allocates a 1 GiB input buffer and crashes under the
contract's memory cap. `msolve_exact.prepare_binary` creates a scratch copy
with five guarded header-buffer constants reduced to 1 MiB. Input size is
checked against that bound. No solver arithmetic or installed binary is
modified. Source and copied-binary hashes and offsets are recorded. The
srand interposer supplies a graph-hash seed to keep random separators
reproducible; it changes no arithmetic.

The official checker uses a forbidden hardcoded scratch path.
`official_check.py RUN --output RUN/out` imports its unchanged source,
redirects only SCRATCH, TMPDIR and SQLITE_TMPDIR into `/tmp/gp10-embed/`,
then calls its normal main. It also checks that the source hash stays
unchanged. The final checker log and report are retained in the run directory.
