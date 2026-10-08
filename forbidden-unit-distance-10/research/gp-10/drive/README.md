# GP-10 driver module

The module is intentionally independent of the embedder and refuter.  The
producer interfaces are:

```text
python embed/gp10embed.py IN.g6 --out OUT.jsonl --unknown U.g6 --time-limit S
python refute/gp10refute.py IN.g6 --out OUT.jsonl --unknown U.g6 --time-limit S --forbidden LIST.json [--refuted KNOWN.jsonl]
```

Build a poset with:

```text
python research/gp-10/drive/poset.py INPUT.g6 --out RUN/poset.json --stats RUN/poset-stats.json
```

Run a resumable pipeline with one producer job:

```text
python research/gp-10/drive/driver.py --input INPUT.g6 --run-dir RUN \
  --embedder research/gp-10/embed/gp10embed.py \
  --refuter research/gp-10/refute/gp10refute.py \
  --forbidden LIST.json --processes 1 --resume
```

At each budget, failed maxima are removed from that budget's embedding
frontier. The next maximal layer is attempted until every remaining graph has
had its attempt. Refutation similarly removes failed minima from its frontier
and ascends to the remaining supergraphs at every budget. A refutation does
not require its graph to be minimal. Minimality is derived separately.
`--exhaustive-fallback` is retained for CLI
compatibility; ordinary layer descent already covers that work.

The B10 wrapper writes `PREDICTIONS.md` before producer work and keeps the
poset, state, request files, logs, aggregate records, `UNKNOWN.g6`, and the
driver minimality comparison in one run directory.

The control runner creates separate `B8p-F7` and `B9p-F8` directories:

```text
nice -n 15 bash -c 'ulimit -v 976562; export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1; exec <repo>/pyenv-gp10/bin/python -B research/gp-10/drive/controls.py --control b8 --root /tmp/gp10-drive/round2 --processes 1 --time-limits 1,5,40'
```

Repeat with `--control b9`, or use `--control both`. A real control writes
`run.json`, invokes the official checker, saves `checker.log` and the default
`checked/` report, and sets PASS only when the checker accepts. Failed controls
write `LABNOTES.md` and do not authorize a B10 run.

The real producer CLIs each launch a worker. `integration.py` calls their
unmodified `main(argv)` in the driver process, so `--processes 1` means one
producer job and at most two processes including its worker. Only scratch-path
globals are redirected into `/tmp/gp10-drive/integration`; no sibling file is
edited. The same adapter invokes the checker. Every request has a fresh
directory, a supported known-refutation snapshot, command metadata and a log
containing stdout, stderr and return status. Request samples have no more than
240 seconds of nominal search budget. Unknowns retain the producer's detailed
attempt budgets across rounds.

`reproduce_integration.py` replays the known-pointer and stale-output failure
cases from a real run. `audit_round2.py` summarizes counts, checker outcomes,
request exit statuses and remaining unknowns.
`probe_remaining.py` runs a stated sample of unresolved graphs with at most
240 seconds of nominal search budget. It preserves full producer output but
does not modify the control state or claim a control PASS.

`stub_producers.py --mode control` is a deterministic orchestration stub.  Its
certificates are not official checker certificates and are used only by the
module tests and control-runner smoke tests.

## Seeded runs and assembly only

`driver.py --seed FILE` is repeatable. In command-line file order and then
line order, the first parsed embedded/refuted record for each input graph
wins. Unknowns and non-record diagnostics do not claim a graph. Selected
records retain their original JSONL bytes. Later duplicates do not replace a
selection, including when validation rejects that first selection.

Use `--validate-seeds` for untrusted producer output. It invokes the unchanged
official checker on dependency-closed samples before propagation. Only an
explicit record ACCEPT survives; rejected and unconfirmed records are dropped.
The default is 128 roots per sample, configurable downward with
`--seed-sample-size`. A sample includes any selected pointer/TU dependencies,
which can make its total larger than its root count. There is no certificate
type whitelist: the checker decides, including for `null-dag` and `real-dag`.

Outside-input records are ignored except for directly referenced E-exact
hosts, the only external records allowed by the checker's host stream.
External R records do not become pointer targets. Bad hosts reject their
dependent seeds. Accepted seeds propagate down for E and up for R before
either producer is scheduled. `--no-producers` skips scheduling entirely and
assigns an explicit assembly-only unknown reason to everything left over.

Seed provenance, consumed source-prefix hashes, ignored-line counters,
first-choice origins, acceptance/rejection counts and checker logs are under
`RUN/seeds/`. Source reads are bounded to the file size observed on opening;
later appends are not silently consumed. Lines over the official 8 MiB limit
are counted and skipped before parsing. Malformed JSON is likewise counted
separately from selected-record checker rejections. Without
`--validate-seeds`, seed certificates have not been mathematically validated.

Seeded and assembly-only runs write `run.json` and `sample/run.json`.
`--profile B10` writes a gated draft, not a fabricated controls bundle, and
requires the frozen B10 input and full F9 list. The sample manifest always
sets `derive: true` on the full frozen B10 input. `--derive` enables derivation
for other sample inputs. Pass the intended forbidden JSON prefix explicitly;
the original generic driver's default remains an empty forbidden list.

The Round 3 reproduction performs the brief's ordered seed discovery, writes
predictions before assembly, uses these driver CLI flags, and invokes the
official checker on the sample run:

```sh
nice -n 15 bash -c 'ulimit -v 976562; export PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; exec <repo>/pyenv-gp10/bin/python -B research/gp-10/drive/assemble_b10.py --run-dir /tmp/gp10-drive/round3-b10-replay --poset /tmp/gp10-drive/b10-poset-final.json'
```

Choose a fresh output directory. Omit `--poset` to build one in that directory.
The current source directories are rediscovered, so later producer work can
change a new assembly. To replay the saved certificate stream without such
rediscovery, invoke the checker on the existing `sample/` directory through
`integration.py`, using the same resource wrapper. `ASSEMBLY.json` records
the exact final checker line, counts, timings and resource measurements.
`audit_round3.py --run-dir RUN` checks saved coverage, seed byte preservation,
source-prefix hashes and checker identities. The optional test environment
variable `GP10_DRIVE_TEST_ARTIFACTS` retains seed regression runs in a fresh
directory; otherwise their temporary files are cleaned up.
