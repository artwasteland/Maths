# WHAT WORKS

`chirosat.py --batch PTS_FILE --out JSONL` now validates the Section 8.2
completion marker, builds one v-dependent base, and solves every line with a
persistent python-sat `Cadical153` solver under instance assumptions. The base
has one nonzero selector for each triple and six auxiliary product-sign
variables per Grassmann-Pluecker relation. The selectors make both zero and
nonzero support expressible by assumptions. SAT models are converted to the
same chirotope witness format as standalone mode and pass the same direct
`verify_witness` check. Batch UNSAT records do not contain an ordinary DRAT
proof. A seeded 1 percent sample, configurable for testing, calls the existing
standalone CaDiCaL proof path and verifies drat-trim. `--second-solver kissat`
writes one temporary base-plus-units CNF per UNSAT result, runs Kissat, records
the verdict and agreement, then removes the temporary file.

The universal v=15 base contains exactly 91,455 variables and 632,450 clauses,
with 15,015 GP relations. This is larger than the predecessor's specialized
194,022-clause v=15 instance encoding because it handles every possible zero
pattern in one cached formula. It is built once per batch and is not rewritten
for ordinary CaDiCaL solves.

The existing standalone controls and deliberate mutations still pass:

```
make check
<repo>/pyenv-maths/bin/python -m py_compile chirosat.py controls.py run_controls.py batch_bench.py run_batch_controls.py
nice -n 10 <repo>/pyenv-maths/bin/python run_controls.py --mutations fano pappus
CONTROL fano v=7 b=7 verdict=no-pseudoline expected=no-pseudoline vars=70 clauses=918 encode_s=0.006903 write_s=0.005436 solve_s=0.008968 check_s=0.395883 total_s=0.417953 PASS
CONTROL pappus v=9 b=9 verdict=pseudoline expected=pseudoline vars=168 clauses=7234 encode_s=0.057863 write_s=0.056734 solve_s=0.037017 check_s=- total_s=0.196943 PASS
MUTATION drop-positive-gp fano verdict=pseudoline clauses=498 PASS
MUTATION truncate-drat fano checker_exit=1 not_verified=true PASS
MUTATION witness-zero pappus rejected='witness zero set differs from the prescribed blocks' PASS
MUTATION repeated-pair parser rejected='pair (0, 1) occurs in more than one block' PASS
MUTATION expected-verdict rejected='inverted-fano-expectation: got no-pseudoline, expected pseudoline' PASS
```

Every fixed control from the predecessor report also passed through the real
batch CLI. The controls were grouped by v so each group could have one base:

```
/usr/bin/time -f 'BATCH_CONTROLS_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python run_batch_controls.py
BATCH CONTROL fano v=7 verdict=no-pseudoline expected=no-pseudoline proof_sampled=True second_solver=True PASS
BATCH CONTROL pappus v=9 verdict=pseudoline expected=pseudoline proof_sampled=False second_solver=- PASS
BATCH CONTROL desargues v=10 verdict=pseudoline expected=pseudoline proof_sampled=False second_solver=- PASS
BATCH CONTROL kantor10 v=10 verdict=pseudoline expected=pseudoline proof_sampled=False second_solver=- PASS
BATCH CONTROL sts13-a v=13 verdict=no-pseudoline expected=no-pseudoline proof_sampled=True second_solver=True PASS
BATCH CONTROL sts13-b v=13 verdict=no-pseudoline expected=no-pseudoline proof_sampled=True second_solver=True PASS
BATCH CONTROL pegg15 v=15 verdict=pseudoline expected=pseudoline proof_sampled=False second_solver=- PASS
BATCH CONTROL kuhne16 v=16 verdict=pseudoline expected=pseudoline proof_sampled=False second_solver=- PASS
MUTATION batch-missing-done rejected=true PASS
MUTATION batch-expected-verdict rejected='inverted-batch-fano: got no-pseudoline, expected pseudoline' PASS
BATCH_CONTROLS_FINAL_WALL_SECONDS=76.27 EXIT=0 MAXRSS=322440
```

The two-instance repeated v=15 control batch was SAT in both cases:

```
/usr/bin/time -f 'WALL_SECONDS=%e' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/batch-controls/controls-v15.txt --out scratch/batch-one.jsonl --proof-sample-rate 0 --second-solver kissat --artifacts scratch/batch-one-artifacts
WALL_SECONDS=2.90
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/batch-one.jsonl
{"count": 2, "instances_per_second": 2.142348, "sum_instance_seconds": 0.933555, "verdicts": {"no-pseudoline": 0, "pseudoline": 2}}
```

The random generator uses PG(3,2)'s 35-line STS(15), removes three lines,
then applies a random point permutation. The resulting 32 triples are a PTS
with a nine-edge even leave. Generation was measured as:

```
/usr/bin/time -f 'GEN_WALL_SECONDS=%e EXIT=%x' nice -n 10 <repo>/pyenv-maths/bin/python batch_bench.py random --out scratch/random-1000.txt --count 1000 --seed 20260905
scratch/random-1000.txt 1000
GEN_WALL_SECONDS=0.34 EXIT=0
```

The requested 1,000-instance v=15 batch was run as follows. The summary uses
the exact per-record `total_seconds` values emitted by the batch path, so its
throughput includes per-instance model handling but not a separately assigned
base-build interval:

```
/usr/bin/time -f 'BATCH_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/random-1000.txt --out scratch/random-1000.jsonl --proof-sample-rate 0 --artifacts scratch/random-1000-artifacts
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/random-1000.jsonl
{"count": 1000, "instances_per_second": 2.210678, "sum_instance_seconds": 452.349918, "verdicts": {"no-pseudoline": 1000, "pseudoline": 0}}
```

The sample was all UNSAT because it is drawn from the one STS(15) isomorphism
class and removes three blocks. It is a valid shaped stress sample, not a
claim about the distribution of arbitrary PTS(15,32) instances.

Persistent learned clauses helped in the measured sample. For 100 records, the
persistent run and a reset every ten records were:

```
/usr/bin/time -f 'WALL=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/random-fast-100.txt --out scratch/random-fast-100.jsonl --proof-sample-rate 0 --artifacts scratch/random-fast-100-artifacts
WALL=38.20 EXIT=0 MAXRSS=289328
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/random-fast-100.jsonl
{"count": 100, "instances_per_second": 2.966035, "sum_instance_seconds": 33.715046, "verdicts": {"no-pseudoline": 100, "pseudoline": 0}}

/usr/bin/time -f 'RESET10_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/random-fast-100.txt --out scratch/random-fast-100-reset10.jsonl --proof-sample-rate 0 --reset-every 10 --artifacts scratch/random-fast-100-reset10-artifacts
RESET10_WALL_SECONDS=41.98 EXIT=0 MAXRSS=299684
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/random-fast-100-reset10.jsonl
{"count": 100, "instances_per_second": 3.638234, "sum_instance_seconds": 27.485864, "verdicts": {"no-pseudoline": 100, "pseudoline": 0}}
```

The wall comparison is the relevant reset comparison because reset rebuild
time is outside individual result records: 38.20 s persistent versus 41.98 s
with nine resets. Thus resetting every ten hurt end-to-end throughput by about
9.9 percent on this sample.

Kissat overhead was measured on the two v=13 UNSAT controls, first without and
then with the cross-check:

```
/usr/bin/time -f 'V13_BASE_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/batch-controls-final/controls-v13.txt --out scratch/v13-base.jsonl --proof-sample-rate 0 --artifacts scratch/v13-base-artifacts
V13_BASE_WALL_SECONDS=27.04 EXIT=0 MAXRSS=134680
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/v13-base.jsonl
{"count": 2, "instances_per_second": 0.082304, "sum_instance_seconds": 24.300085, "verdicts": {"no-pseudoline": 2, "pseudoline": 0}}

/usr/bin/time -f 'V13_KISSAT_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/batch-controls-final/controls-v13.txt --out scratch/v13-kissat.jsonl --proof-sample-rate 0 --second-solver kissat --artifacts scratch/v13-kissat-artifacts
V13_KISSAT_WALL_SECONDS=53.31 EXIT=0 MAXRSS=139212
<repo>/pyenv-maths/bin/python batch_bench.py summary scratch/v13-kissat.jsonl
{"count": 2, "instances_per_second": 0.040367, "sum_instance_seconds": 49.545423, "verdicts": {"no-pseudoline": 2, "pseudoline": 0}}
```

The v=13 cross-check had Kissat agreement `True` on both records, with
`cadical_sum=23.169935` seconds and `kissat_sum=21.551546` seconds. A sampled
proof on an actual random v=15 PTS also passed:

```
/usr/bin/time -f 'RANDOM_SAMPLE_WALL_SECONDS=%e EXIT=%x MAXRSS=%M' nice -n 10 <repo>/pyenv-maths/bin/python chirosat.py --batch scratch/random-one.txt --out scratch/random-one.jsonl --proof-sample-rate 1 --seed 20260905 --artifacts scratch/random-one-artifacts
RANDOM_SAMPLE_WALL_SECONDS=13.76 EXIT=0 MAXRSS=280132
no-pseudoline True True 91455 632450
```

The encoding is the rank-3 chirotope system (B0) nonzero support, (B1)
alternation, and (B2) the three-term Grassmann-Pluecker relations from
Björner, Las Vergnas, Sturmfels, White and Ziegler, *Oriented Matroids*,
second edition, Section 3.5. The direct checker uses the same relation form.

All deliberate checks were made to fail once. The predecessor controls omitted
the positive GP family and changed Fano from UNSAT to SAT, truncated the actual
Fano DRAT and got checker exit 1 with `s NOT VERIFIED`, changed a Pappus model
sign to zero and got a zero-set rejection, supplied a repeated PTS pair and
got a parser rejection, and inverted an expected verdict and got an assertion.
The new batch control copied a marked input without its `.DONE` file and the
real CLI rejected it. It also inverted the actual batch Fano expectation and
the batch result checker rejected `got no-pseudoline, expected pseudoline`.

# WHAT DOES NOT

The generated 1,000-instance sample has no SAT cases. It therefore measures a
hard UNSAT workload and does not measure a balanced SAT/UNSAT workload.

The attempted 100-instance random Kissat overhead run was stopped before JSONL
completion because a hard random UNSAT instance did not finish in the allowed
foreground window. Its temporary CNF was removed after the process stopped. The
fixed v=13 measurement above is the completed Kissat overhead measurement.

Batch UNSAT records only get DRAT on sampled instances, as required by Section
8.3. The implementation does not independently prove every batch UNSAT result.
The fixed controls and one v=15 random instance have sampled proof verification,
and all fixed UNSAT controls have Kissat agreement.

No PTS(14,27), PTS(14,28), or PTS(15,32) enumeration dataset was delivered in
the workspace, so no census result is claimed. The standalone and batch work
does not decide the orchard problem.

# UNCERTAIN

The default one percent proof sample was not run over the full 1,000-record
file. A rate-one sample was run on a v=15 random record and rate-one sampling
was run on every fixed UNSAT control. The default seeded sampling logic remains
to be exercised on the full file.

Only `Cadical153` was measured. `Cadical195` is accepted by the batch CLI but
was not exercised. No `propagate` call or phase-saving option was added because
the persistent solve measurements were sufficient for the requested comparison.

The random generator varies labels and the three removed STS blocks, but it
does not sample the full space of nonisomorphic PTS(15,32) structures. Its
validity checks only establish the PTS property and even leave, not canonical
coverage.

The reported batch summary throughput is based on summed JSONL per-instance
timings. The exact wall commands are recorded above, but the long 1,000-record
wall timer output was not retained by the command wrapper. The per-instance
summary is reproducible from `scratch/random-1000.jsonl`.

# PROPOSED CONTRACT AMENDMENTS

Clarify Section 8.4 that a cached base CNF may use Tseitin auxiliary variables
for product signs and support selectors, while the two sign variables per
triple remain the witness variables. Otherwise a correct universal zero-aware
base cannot express nonzero assumptions using literals alone.

Clarify whether the required instances-per-second figure is wall-clock batch
throughput including base construction and output, or the sum of per-instance
solver timings. This report gives the latter for the 1,000 run and both values
where the wrapper retained wall output.

Retain the existing amendment that either permits the checker installation path
or designates `chiro/scratch/drat-trim`, since the common brief requires an
external checker while the module-only write rule forbids installing it there.
