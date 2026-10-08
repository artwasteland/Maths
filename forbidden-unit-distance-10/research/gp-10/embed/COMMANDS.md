# Measurement commands

These commands were run from the repository root. The batched commands
run the listed stages sequentially in one parent, with at most one worker.
A table row in REPORT.md links to its command here. Commands are separated
for replay; do not launch two worker-producing commands concurrently.
The first host pass preceded compilation of the G118 subset. A replay with
the final host cache available can find different hosts in that first pass.
Original records, budgets, timings and host-source labels are retained.

## prepare

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/measure.py prepare
```

## hosts

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/prepare_hosts.py
```

## subset

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/prepare_g118_subset.py
```

## controls

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/selftest.py
```

## named-lattice

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/measure.py stage named lattice18 --seconds 1 --node-cap 20000
```

## named-construct

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/measure.py stage named constructive --seconds 15 --node-cap 2000
```

## max-lattice

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/measure.py stage maximal lattice18 --seconds 0.1 --node-cap 1500
```

## baseline

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample,seconds in [('uniform500',0.1),('B9p',0.08)]:
 stage(sample,'lattice18',seconds,1500,0,'lattice18')
PY
```

## wide

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample in ('maximal','uniform500','B9p','named'):
 for method in ('lattice36','lattice30'):
  stage(sample,method,0.06 if sample!='named' else 0.5,1500,0,method)
PY
```

## circles

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample in ('maximal','uniform500','B9p'):
 stage(sample,'constructive',2,1500,32,'constructive')
PY
```

## host-pass

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample in ('maximal','uniform500','B9p','named'):
 stage(sample,'host',0.15,1500,0,'host')
PY
```

## host-subset-pass

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample in ('maximal','uniform500','B9p'):
 stage(sample,'host',0.15,1500,0,'host_g118_subset')
PY
```

## numeric

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B - <<'PY'
import sys
sys.path.insert(0,'research/gp-10/embed')
from measure import stage
from gp10embed import limits
limits()
for sample in ('maximal','uniform500','B9p','named'):
 stage(sample,'numeric',2,1500,32,'numeric')
PY
```

## audit

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/final_audit.py
```

## report

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/make_report.py
```

## Round 2 commands and scope

Every command uses `ulimit -v 1000000` and `exec nice -n 15` as below.
All Python invocations use the frozen interpreter and `-B`. Scripts set
SYMPY_GROUND_TYPES=python before SymPy imports and numerical thread counts to one.
The work is limited to B2's stated cohorts: all 1202 maximal unknowns, then
88 F9-free B9p unknowns, then 47 uniform500 unknowns. These are the explicitly
requested samples, not a full B10 solve. Long work is divided into recorded
index batches in `results/round2/batches/`; no cohort membership is sampled out.

```sh
ulimit -v 1000000
exec nice -n 15 gcc -fPIC -O2 -c research/gp-10/embed/msolve_seed.c -o /tmp/gp10-embed/round2/msolve_seed.o
```

The compile used `TMPDIR=/tmp/gp10-embed/round2`. Linking is a separate command
to avoid nested compiler/linker processes.

```sh
ulimit -v 1000000
exec nice -n 15 ld -shared /tmp/gp10-embed/round2/msolve_seed.o -o /tmp/gp10-embed/round2/msolve_seed.so -ldl -lc
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2_selftest.py
```

Production commands use `round2.py batch --sample NAME --start A --stop B --cap 20`.
The exact A and B values and timings are recorded in each batches JSON file.
`round2.py prepare` creates the input manifests. It was invoked as
`round2.prepare()` in a frozen-Python here-document before the preliminary batch.
`round2_reconvert.py --sample maximal` retried completed outputs after the
factor-wise conversion improvement, without another msolve call.

The official checker is run through `official_check.py RUN --output RUN/out`.
This calls the unchanged checker's normal main and redirects only its
hardcoded scratch directory into the allowed `/tmp/gp10-embed/` tree.
The initial independent checks are in `results/round2/official-control-results.json`;
all 11 pilot certificates passed, the one-coordinate mutation failed at
`edge_equation`. These were created and executed in a frozen-Python
here-document using the same wrapper and sample run manifests saved there.

Finalization used these commands sequentially from the repository root:

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2_quiet.py
```

Collection used a frozen-Python here-document importing `limits` and
`round2.collect`, then printing a compact summary. Its CLI equivalent is:

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2.py collect
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/official_check.py research/gp-10/embed/results/round2/run --output research/gp-10/embed/results/round2/run/out > research/gp-10/embed/results/round2/run/checker.log
```

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B research/gp-10/embed/round2_finish.py
```

The separator diagnostics were a bounded frozen-Python here-document: parse
each saved rejected output with `decode_output`, factor its eliminant,
invert the printed denominator modulo each factor, and evaluate the printed
linear separator relation using those coordinate polynomials. Each graph
ran in `round2_phase.isolated` with a 15-second cap. This was diagnostic
only and did not alter any verdict or certificate.

## Round 3 commands

[ROUND3.md](ROUND3.md) records the executed converter controls, 13-graph batch,
H1/H2 reconstruction, collection, paired mutation checks, official merged-run
check, final audit, and the observed reason for deferring the optional pass.
