# GP-10 embedder report

The producer and all requested development artifacts are present. Accepted records contain ordinary E-exact coordinates, checked locally before emission. The blind checker has not been run, and the global pipeline gates remain open. The unresolved inputs are retained explicitly.

Entry point: [gp10embed.py](gp10embed.py). Usage and resume behaviour: [README.md](README.md). Exact commands: [COMMANDS.md](COMMANDS.md). Raw records, per-method statistics and audits: [results/](results/). The cross-sample union is [union-records.jsonl](results/union-records.jsonl), with [UNKNOWN.g6](UNKNOWN.g6) containing exactly those measured graph codes that no measured method embedded. Each input set also has its own records and UNKNOWN.g6.

## Scope and coverage

Counts below come from `measure.py prepare`, the method commands linked in the next table, and [the audit command](COMMANDS.md#audit). The maximal file and the prescribed random sample were used in full for the first lattice pass. Every line of B9p was exercised. Later circle and numeric stages used deterministic samples of unresolved inputs. This is a development measurement, with no full B10 classification claim.

| Input | Graphs | Embedded | Unknown | Unknown rate |
|---|---:|---:|---:|---:|
| maximal | 2526 | 1324 | 1202 | 47.59% |
| uniform500 | 500 | 453 | 47 | 9.40% |
| B9p | 3085 | 2896 | 189 | 6.13% |
| named | 13 | 5 | 8 | 61.54% |
| B9p: F9_free | 2984 | 2896 | 88 | 2.95% |
| B9p: forbidden | 101 | 0 | 101 | 100.00% |

The deduplicated measured union contains 6078 graph codes: 4656 embedded and 1422 unknown. Its unknown rate is 23.40%. Success in another overlapping sample can settle a graph that remains unknown in an individual sample's historical results.

## Coverage and time by method

These are incremental hits on inputs still unresolved at that stage, not independent success rates on the whole set. `Attempted` is the denominator. A sample cap is shown where only a deterministic subset was exercised. Wall time includes workers and output writes; import and host-loading time is recorded separately in each meta file. The graph limit is a watchdog deadline, with process cleanup included in reported wall time. Unknown rates above use the exact combination of budgets below.

| Input | Stage | Attempted | New embedded | Unknown | Wall s | Limit s/graph | Node cap | Sample cap | Command |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| maximal | lattice18 | 2526 | 1062 | 1464 | 98.843 | 0.1 | 1500 | all remaining | [max-lattice](COMMANDS.md#max-lattice) |
| maximal | lattice36 | 1464 | 0 | 1464 | 92.353 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| maximal | lattice30 | 1464 | 0 | 1464 | 93.724 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| maximal | constructive | 32 | 3 | 29 | 38.629 | 2 | 1500 | 32 | [circles](COMMANDS.md#circles) |
| maximal | host | 1461 | 239 | 1222 | 158.613 | 0.15 | 1500 | all remaining | [host-pass](COMMANDS.md#host-pass) |
| maximal | host_g118_subset | 1222 | 20 | 1202 | 141.058 | 0.15 | 1500 | all remaining | [host-subset-pass](COMMANDS.md#host-subset-pass) |
| maximal | numeric | 32 | 0 | 32 | 39.447 | 2 | 1500 | 32 | [numeric](COMMANDS.md#numeric) |
| uniform500 | lattice18 | 500 | 436 | 64 | 13.646 | 0.1 | 1500 | all remaining | [baseline](COMMANDS.md#baseline) |
| uniform500 | lattice36 | 64 | 2 | 62 | 4.009 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| uniform500 | lattice30 | 62 | 0 | 62 | 3.905 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| uniform500 | constructive | 32 | 3 | 29 | 41.645 | 2 | 1500 | 32 | [circles](COMMANDS.md#circles) |
| uniform500 | host | 59 | 11 | 48 | 6.501 | 0.15 | 1500 | all remaining | [host-pass](COMMANDS.md#host-pass) |
| uniform500 | host_g118_subset | 48 | 1 | 47 | 6.451 | 0.15 | 1500 | all remaining | [host-subset-pass](COMMANDS.md#host-subset-pass) |
| uniform500 | numeric | 32 | 0 | 32 | 39.562 | 2 | 1500 | 32 | [numeric](COMMANDS.md#numeric) |
| B9p | lattice18 | 3085 | 2710 | 375 | 88.055 | 0.08 | 1500 | all remaining | [baseline](COMMANDS.md#baseline) |
| B9p | lattice36 | 375 | 19 | 356 | 22.972 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| B9p | lattice30 | 356 | 5 | 351 | 22.242 | 0.06 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| B9p | constructive | 32 | 5 | 27 | 40.290 | 2 | 1500 | 32 | [circles](COMMANDS.md#circles) |
| B9p | host | 346 | 153 | 193 | 27.243 | 0.15 | 1500 | all remaining | [host-pass](COMMANDS.md#host-pass) |
| B9p | host_g118_subset | 193 | 4 | 189 | 23.716 | 0.15 | 1500 | all remaining | [host-subset-pass](COMMANDS.md#host-subset-pass) |
| B9p | numeric | 32 | 0 | 32 | 34.281 | 2 | 1500 | 32 | [numeric](COMMANDS.md#numeric) |
| named | lattice18 | 13 | 4 | 9 | 2.193 | 1 | 20000 | all remaining | [named-lattice](COMMANDS.md#named-lattice) |
| named | constructive | 9 | 1 | 8 | 4.678 | 15 | 2000 | all remaining | [named-construct](COMMANDS.md#named-construct) |
| named | lattice36 | 8 | 0 | 8 | 0.939 | 0.5 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| named | lattice30 | 8 | 0 | 8 | 1.101 | 0.5 | 1500 | all remaining | [wide](COMMANDS.md#wide) |
| named | host | 8 | 0 | 8 | 0.398 | 0.15 | 1500 | all remaining | [host-pass](COMMANDS.md#host-pass) |
| named | numeric | 8 | 0 | 8 | 5.204 | 2 | 1500 | 32 | [numeric](COMMANDS.md#numeric) |

`host_g118_subset` repeats the host stage after the new G118 subhost was compiled. Its hits are attributed to their actual source in the saved statistics. The host matcher node cap is the displayed base cap multiplied by the factor in the implementation. All graph time limits still apply.

## Methods and exact acceptance

- The lattice DFS stores integer coefficients in a fixed real algebraic basis. It uses the spindle rotation, wider roots of unity, and a rational Pythagorean rotation. Each new point is reached from a placed neighbour by a chosen direction; other incident edges are checked exactly. Trying every placed neighbour fixed the initial spindle miss. Closing-edge directions are allowed outside the finite proposal set.
- Constructive placement peels low-degree vertices, embeds the remaining core, then uses exact unit-circle intersections and rational free directions. A structural search for two regular polygon layers derives unit spokes algebraically and supplies the Petersen control. It contains no named graph-code or coordinate lookup.
- Host search uses an injective, non-induced bitset matcher. Numeric host adjacency only proposes maps. Selected coordinates are flattened and verified as ordinary E-exact certificates against the input graph. Library hits are separate from general search.
- Numeric search uses seeded least squares with a coincidence penalty, then rational free directions and exact circle reconstruction. Every reconstructed candidate must pass the same exact check. No msolve, Singular, z3 or integer-relation wrapper was used.
- The local verifier checks the strict rational endpoint sign change, reduces every required squared edge distance exactly modulo the supplied polynomial, and proves all pair distances positive using rational interval arithmetic. Interval refinement retains a strict sign change. It does not assume irreducibility or use float separation to accept.
- Search seeds are SHA256 of graph6. Coordinate order is the input graph6 order. One worker is alive at a time. The parent turns timeouts and abrupt worker exits into unknown records, flushes records, and resumes by streaming and rechecking prior exact records. Existing unknown records are skipped on resume too.

## Host preparation

Preparation commands: [hosts](COMMANDS.md#hosts) and [subset](COMMANDS.md#subset). The full G118 edge count below is numeric proposal adjacency; its entire coordinate field was not certified.

| Host | Vertices | Proposed edges | Exact degree | Status | Wall s | Limit s |
|---|---:|---:|---:|---|---:|---:|
| G27 | 27 | 57 | 8 | certified | 22.560 | 60 |
| AMP33 | 33 | 95 | 8 | certified | 31.710 | 60 |
| G118 | 118 | 299 |  | timeout | 60.001 | 60 |
| G118 simple subset | 47 | 102 | 4 | certified | 2.709 | 60 |

The subset's one-coordinate mutation failed with `edge:0,1`. The audit counted these library hits across the per-sample method records, including repeated graph codes across samples: AMP33: 73, G118: 8, G118_simple: 21, G27: 326.

## Named controls and regressions

The named positive records were obtained through general search before the host pass. The embedder cannot produce the refutations required by the whole pipeline. Its negative controls therefore remain unknown.

| Graph | Canonical graph6 | Verdict | First successful general method |
|---|---|---|---|
| Golomb | ``I?C]dPcww`` | embedded | lattice18 |
| K2_3 | ``DFw`` | unknown |  |
| K4 | ``C~`` | unknown |  |
| Moebius_ladder | ``Is?@WxcU?`` | unknown |  |
| Moser_spindle | ``F`o~_`` | embedded | lattice18 |
| Petersen | ``IsP@OkWHG`` | embedded | constructive |
| complex_only_10 | ``GqHPW{`` | unknown |  |
| complex_only_17 | ``Gm__x[`` | unknown |  |
| complex_only_18 | ``GqGTYw`` | unknown |  |
| complex_only_4 | ``FqHXw`` | unknown |  |
| complex_only_9 | ``G@fBJs`` | unknown |  |
| extremal_10 | ``IISpZATaw`` | embedded | lattice18 |
| pentagonal_prism | ``Is?HGtcU?`` | embedded | lattice18 |

The Golomb input code was taken from the existing scratch brief cited by this job, then canonicalised. Named graphs, including the extremal input, are searched in the canonical labelling. No AMP or GP coordinate lookup contributed to these successful controls.

## Validation and numeric refusal

[selftest.py](selftest.py) passed 18 controls. [selftest-results.json](selftest-results.json) gives the actual positive and rejection results. The [controls command](COMMANDS.md#controls) exercises coordinate, sign-change, coincident-point, reducible-polynomial and nonreal-field mutations; host-map injectivity and edge preservation; deterministic certificates; worker exceptions, hard exits and hard timeouts; continuation after a crash; and resume repair.

The deliberately permissive numeric diagnostic disables the repulsion term to exhibit the residual-only failure mode. It solves the edge equations for K2,3 near collapsed circle intersections. This is a diagnostic mode of the same fitting routine, not a claim that the production penalised solve accepted that configuration.
Its maximum squared-edge residual was 0, while the minimum numeric point separation was 1e-08. The exact collapsed candidate failed with `distinctness:2,3:zero`. A genuine exact positive and a single-coordinate coincidence mutation separately exercise that rejection branch.
No production sample retained both a residual at most 1e-12 and a completed exact-refusal result. Watchdog interruptions can omit these diagnostics. The explicit diagnostic above supplies the required example.

[final-audit.json](results/final-audit.json) verifies every saved stage certificate, input/certificate label agreement, primary coverage and unknown projections, canonical input codes, negative controls, valid finite JSON numbers, and source syntax. These are local checks, not the blind checker.

## Environment and procedural notes

Measured by the [audit command](COMMANDS.md#audit): `SYMPY_GROUND_TYPES=python`, `executable=<repo>/pyenv-gp10/bin/python`, `flint=0.9.0`, `networkx=3.7`, `niceness=19`, `numpy=2.5.3`, `python=3.12.3`, `scipy=1.18.1`, `sympy=1.14.0`, `virtual_memory_limit_bytes=1024000000`.

All work products are inside this module or the permitted scratch directory. No git commands, package installs, npm, oversight execution, or edits to the earlier unit-distance module were used. The common brief gives a looser memory ceiling than the contract; the stricter contract ceiling was used. The initial read-only COMMON.md bootstrap used `nice -n 10` without an explicit ulimit before its detailed rules were known. All later shell commands used `nice -n 15` and `ulimit -v 1000000`; this bootstrap is the procedural exception.

The shared PROOFS.md and PREDICTIONS.md were absent. The module [PREDICTIONS.md](PREDICTIONS.md) records predictions before coverage measurements. [LABNOTES.md](LABNOTES.md) explains the initial named-control misses and the incomplete B9 control coverage. No shared proof file, global gate, independent checker acceptance or commit is claimed.

## Round 1 limitations (historical)

The following limitations describe the round-one run. Round-two results follow.

- The official blind checker was not available in this module run. Local arithmetic, mutations and audits do not substitute for that gate.
- The unresolved F9-free B9 graphs show that search coverage is incomplete. The numeric and circle methods were sampled on unresolved graphs, and wider lattice searches often reached their time limits. Unknown never means forbidden.
- Full G118 flattening timed out. The certified subhost is usable; difficult matches in the full host still require per-map conversion and can time out or exceed the field-degree cap. The matcher tries one map per host, so a difficult first map can hide an easier alternative.
- Search decisions are deterministic from each graph code, but wall-time cutoffs and recorded durations vary with scheduling. Literal record equality is therefore expected for completed successful searches, not for elapsed-time fields or borderline timeouts.
- Actual operating-system OOM killing and a native-library segmentation fault were not injected. Abrupt worker exit, Python exceptions and an uncooperative timeout were exercised. Parent I/O failure and concurrent writers are outside the tested recovery case.
- The likeliest implementation errors are in algebraic field conversion, source-coordinate parsing and labelling at graph/coordinate boundaries. Exact checks protect each emitted result, but a shared arithmetic or parser mistake still needs an independent checker. Golomb identity was inherited from the supplied scratch definition, rather than independently looked up.
- The union covers only the measured input sets. No completeness claim for B10, minimal forbidden list, or full control-pipeline PASS follows from this report.

## Round 2

Processed all 1,337 requested input memberships (1,314 distinct graphs), in the requested cohort order. The new union has 4,900 embedded records and 1,178 unknown records, with 244 new unique embeddings. No refuted record is emitted.

The official checker accepted the merged sample run. Its exact final line is:

```text
ACCEPT run verified
```

Measured coverage on the round-one unknown lists follows. Embedded and unknown are this producer's per-cohort outcomes; overlaps are deduplicated in the union.

| Cohort | Inputs processed | Embedded | Unknown | msolve calls | First-pass timeouts | Rigid triage |
|---|---:|---:|---:|---:|---:|---:|
| maximal | 1202 | 212 | 990 | 785 | 68 | 10 |
| B9p | 88 | 28 | 60 | 41 | 0 | 0 |
| uniform500 | 47 | 6 | 41 | 21 | 5 | 0 |

Every input has a record. A failed numerical preparation is unknown without an msolve call. The stated cohorts are the requested research samples; no additional full-B10 solve was run. Long work was divided into recorded index batches.

The triage file has 10 unique graphs, all unpinned with k=0 and all still unknown. It is a lead for the refuter, not a refutation certificate. The audit found no triage/embedding conflict.

| Cohort | Pinned msolve calls | Pinned embeddings | Sum of graph wall time (s) | msolve time (s) |
|---|---:|---:|---:|---:|
| maximal | 94 | 44 | 4893.927 | 4361.823 |
| B9p | 31 | 19 | 77.156 | 50.173 |
| uniform500 | 5 | 3 | 173.031 | 155.530 |

The sums include saved-output conversion retries and any second-pass attempts. They exclude development, imports before batch timing, and preliminary experiments. The final official checker took 265.158 s.

The first msolve cap was 20 s per graph; preparation and conversion had separate hard caps of 8 s and 15 s. There were 18 attempts at the conditional second-pass cap of 120 s. These recovered 10 embeddings; 3 retried entries reached the longer cap. 55 first-pass timeout memberships were not retried.

The second pass stopped before the next pending timeout because the shared-box check was not quiet: one-minute load 2.078, CPU idle fraction 0.690, available memory 3,070,156 KiB. The previously recorded thresholds were load at most 2.0, idle fraction at least 0.5, and available memory at least 1,572,864 KiB. The observations and any attempted retries are in `second-pass-decision.json`.

Completed-output eliminant degrees, including rejected parametrizations, are counted per solver attempt:

| Eliminant degree | Outputs |
|---:|---:|
| 8 | 2 |
| 16 | 7 |
| 32 | 9 |
| 56 | 3 |
| 64 | 139 |
| 72 | 1 |
| 80 | 5 |
| 88 | 2 |
| 90 | 1 |
| 92 | 2 |
| 94 | 1 |
| 96 | 1 |
| 104 | 1 |
| 112 | 2 |
| 120 | 2 |
| 122 | 1 |
| 124 | 2 |
| 128 | 49 |
| 152 | 3 |
| 160 | 1 |
| 176 | 1 |
| 180 | 2 |
| 184 | 1 |
| 186 | 1 |
| 190 | 1 |
| 192 | 2 |
| 194 | 1 |
| 196 | 2 |
| 208 | 4 |
| 211 | 1 |
| 216 | 1 |
| 226 | 1 |
| 244 | 4 |
| 248 | 1 |
| 256 | 1 |

New unique certificates use these irreducible-factor degrees: 2: 1, 4: 101, 8: 104, 10: 7, 12: 24, 16: 5, 24: 2.

The primitive element remains the printed separating variable. Factoring its eliminant permits smaller exact certificates. The parser handles reordered coordinate boxes, an added separator, rational coordinate denominators, exact rational roots, and ideal multiplicities. It inverts denominators modulo each factor and checks input equations before the local E-exact checks.

457 unpinned k=0 attempts returned a positive-dimensional complex solution set. Thus generic rigidity did not guarantee a finite unit-length system. Such outputs never entered triage. No distinctness saturation or component decomposition was added.

The final local suite passed 25 controls in 0.645 s. It includes a triangle, a rationally pinned unit rhombus, repeated-root multiplicity, reordered variables, reproducible added separators, coincident points with exact edge lengths, one-coordinate and one-interval mutations, malformed output, and native child exit/timeout handling. The independent pilot checker accepted its saved new certificates and rejected a one-coordinate mutation with `edge_equation`.

The stock msolve CLI segfaulted under the contract memory cap because it allocated a 1 GiB header buffer. The scratch copy changes five guarded input-buffer immediates to 1 MiB. Input size is checked against that bound. Solver arithmetic and the installed binary are unchanged. A small srand interposer seeds random separators from the graph hash. Exact offsets, binary hashes, inputs, outputs and logs are retained.

The checker hardcodes `/tmp/gp10-check`, outside the allowed write paths. `official_check.py` redirects only its scratch globals and environment to `/tmp/gp10-embed/official-check`, then invokes the unchanged checker's main. This is the necessary deviation from the brief's literal checker command. The checker source hash is recorded and checked for stability.

Commands supplying these measurements are `round2.py batch` with the bounds recorded in `results/round2/batches/`, `round2_reconvert.py --sample maximal`, `round2_quiet.py`, `round2.py collect`, `round2_selftest.py`, `official_check.py results/round2/run --output results/round2/run/out` (with module-prefixed paths), and `round2_finish.py`. Every Python command was launched with the frozen interpreter, `-B`, niceness 15 and the address-space cap shown in [COMMANDS.md](COMMANDS.md). The official checker further increased its own niceness to 19, as recorded in its report.

Deliverables: [summary](results/round2/summary.json), [new union](results/round2/union-records.jsonl), [unknowns](results/round2/UNKNOWN.g6), [rigid triage](results/round2/rigid-no-embedding.g6), [triage summaries](results/round2/rigid-no-embedding.jsonl), [first-pass timeouts](results/round2/timeouts-pass1.g6), [second-pass timeouts](results/round2/timeouts-pass2.g6), [checker log](results/round2/run/checker.log), [checker report](results/round2/run/out/report.json), [audit](results/round2/final-audit.json), and [usage and design](ROUND2.md).

## Round 2 limitations (historical)

The following limitations describe round two. Round-three results follow.

- Rational direction pins are proposals near a numerical solution. No certified implicit-function neighborhood or persistence radius was constructed. Successful pins have exact embeddings; a failed pinned system cannot exclude another embedding.

- Generic rank is bounded and checked exactly, but special unit-length components can still be positive-dimensional. The current solver does not saturate coincidences or decompose those components.

- 4 completed solver outputs were rejected by parametrization/schema checks. Details are in `final-audit.json` and the original outputs are retained. Three fail the printed separator relation under the current interpretation; one fails original input equations on some factors. Diagnostic factor checks found valid original equations throughout the three separator failures, but did not resolve the separator mismatch. The msolve output parser, especially unusual nonradical cases, remains the most likely integration failure point.

- Triage relies on the completeness of msolve's result and is not independently certified as a refutation. The official sample checker validates the embedded records and accepts unknown records as unknown.

- The memory workaround is specific to the guarded installed binary. A different msolve build requires a reviewed replacement. Actual large-solver OOM was not deliberately forced; child exit and hard timeout were exercised, as was the stock CLI allocation crash.

- This run does not close the classification gates. Remaining unknowns, full small-order pipeline controls, and refutation/minimality work remain outside this embedder result.

## Round 3

All 13 supplied nine-vertex gaps now have exact embeddings. Each closed by a map into G118 followed by conversion of only its image coordinates. No gap required H1 or H2. No refutation is emitted.

The new union contains 4,913 embedded and 1,165 unknown records out of 6,078, with 13 new unique embeddings. The official checker took 385.475 seconds and ended with exactly:

```text
ACCEPT run verified
```

| Input g6 | Closing method | Real field degree | Graph wall time (s) |
|---|---|---:|---:|
| `H?DLHrp` | G118 image field | 8 | 0.147 |
| `H?DTJQx` | G118 image field | 16 | 1.595 |
| `H?QXbei` | G118 image field | 8 | 0.205 |
| `H?hXcdb` | G118 image field | 16 | 1.750 |
| `H@@LIqx` | G118 image field | 8 | 0.063 |
| `H@gIGnR` | G118 image field | 8 | 0.113 |
| `H_DJDc{` | G118 image field | 8 | 0.153 |
| `H_SsHVo` | G118 image field | 8 | 0.223 |
| `H_hPOno` | G118 image field | 8 | 0.160 |
| `Hg@G\|_x` | G118 image field | 8 | 0.149 |
| `HgDHKcx` | G118 image field | 8 | 0.576 |
| `Ho?rOxX` | G118 image field | 8 | 0.107 |
| `HoKQG^o` | G118 image field | 8 | 0.174 |

The stated 13-graph production sample took 5.429 seconds as a batch. Summed graph time was 5.416 seconds, including 4.262 seconds in PARI. These exclude development, the preserved pilot pass and the independent checker. Mapping has a 60-second watchdog and a 10,000,000-node cap; PARI has 180 seconds per image.

Numerical adjacency proposes injective maps. PARI evaluates only the mapped radical expressions, adjoining square roots when necessary and reducing the field. It then chooses a linear combination of image coordinates and solves exact rational linear systems to express every coordinate in its powers. Because that primitive element is itself a combination of the coordinates, these two inclusions establish equality with the field generated by the image coordinates. Root selection is numerical; acceptance still requires exact edge reduction, sign change and certified distinctness in the existing verifier.

The first PARI probe reached degree 8 but timed out at 180 seconds during matrix conversion, with thread-stack allocation warnings under the address-space cap. Setting `default(nbthreads,1)` resolved this in the repeat. Both attempts are retained. The final implementation seeds PARI from the canonical graph hash, and its degree-16 production image repeated byte-for-byte.

| Exceptional host | Canonical g6 | Real field degree | Construction time (s) | Printed polynomials checked |
|---|---|---:|---:|---:|
| H1 | ``H`QEpgl`` | 10 | 0.749 | 9 |
| H2 | ``H`GO]Nw`` | 12 | 0.143 | 9 |

H1 and H2 were reconstructed from the paper's fixed coordinates and equilateral-triangle relations in `uglyFigure`, with the remaining equations solved by msolve. Every printed polynomial in z=x+iy was then checked exactly in the resulting real field. Their canonical graphs were already embedded in round two; the new union replaces those two certificates with these table-validated ones so the official checker checks them too. All 26 graph-host pairs were searched for a subgraph map, with no hits.

To match H2's figure, the last two table rows are interpreted as displacement coordinates from (sqrt(3),0). Adding sqrt(3) to their x coordinates agrees with the figure and is necessary for its edge set. The implementation validates their printed polynomials before that translation. Rounded coordinates only select branches; they are not proof data. The source file and notebook hashes, printed coefficients, formulas, solver inputs and exact certificates are retained. No network fetch was needed.

The optional pass on 990 maximal and 41 uniform unknowns was deferred: one-minute load was 2.467, two-second CPU idle fraction 0.420, and available memory 2,428,756 KiB. The pre-existing quiet criteria require load at most 2.0, idle fraction at least 0.5, and available memory at least 1,572,864 KiB. Both load and idle failed. Zero optional inputs were attempted; their round-two records remain in the union.

Validation passed 15 paired positive/one-coordinate mutation checks on the 13 gaps and two exceptional hosts. Each mutation failed on the expected edge. Two PARI fixtures also passed positive, mutation and deterministic-repeat checks; H1 and H2 each rejected a one-coefficient printed-polynomial mutation with `table:minpoly:0`. The official checker accepted the 15-record control and rejected its one-coordinate mutation with `edge_equation`, then accepted the complete merged union.

Commands and limits are recorded in [ROUND3.md](ROUND3.md). Computational commands used the frozen Python, `-B`, niceness 15 and `ulimit -v 1000000`, with at most one child. PARI and msolve use one thread. The unchanged official checker increases its niceness to 19. The existing wrapper redirects its scratch directory into `/tmp/gp10-embed/`, as in round two.

Deliverables: [new records](results/round3/records.jsonl), [merged union](results/round3/union-records.jsonl), [unknown projection](results/round3/UNKNOWN.g6), [summary](results/round3/summary.json), [checker log](results/round3/run/checker.log), [checker report](results/round3/run/out/report.json), [final audit](results/round3/final-audit.json), and [optional-pass decision](results/round3/optional-decision.json).

## Round 3 uncertainties (historical)

- The optional 990-plus-41 host pass was not exercised because the shared box failed the recorded quiet check. The new converter may close more of those inputs, but no coverage claim is made for them.

- This module did not rerun the complete nine-vertex control pipeline. It supplies accepted certificates for all 13 supplied gaps; the supervisor must merge them with the other producers and rerun that control. The module's own union still has unknown records.

- Numerical host adjacency and approximate real-root selection remain proposal steps. Incorrect proposals can waste time or select a different conjugate, but cannot bypass the exact certificate checks. The most likely future integration defects are unsupported notebook expression forms or a wrong source-coordinate ordering.

- H2's two translated table rows require the figure to interpret them. The maximum discrepancy from a printed rounded coordinate was about 5.13e-6, so rounded decimals should not be treated as certified intervals. The complex polynomials and all required graph edges were checked exactly.

- General PARI OOM recovery was not forced deliberately. The preserved initial probe exercised the timeout under thread-stack pressure. High-degree image fields beyond this sample, and host conversion above the degree cap of 256, remain unmeasured.

- H1/H2 use source-specific positive construction constraints, and the G118 method is a library method. These are not the general-search named controls and do not authorize a classification claim.

## Round 4

The mandatory pass on the supplied 1,515 candidates is complete. The official sample checker accepted the merged candidate records with the exact final line:

```text
ACCEPT run verified
```

Round 4 produced 922 exact embedding certificates, of which 912 are additional to the completed external embedding pass. The merged candidate sample has 1,202 embedded, 98 externally refuted, and 215 unknown graphs. [UNDECIDED.g6](results/round4/UNDECIDED.g6) contains exactly those 215 graphs. [rigid-no-embedding.g6](results/round4/rigid-no-embedding.g6) exists and is empty: no rigid candidate supplied a complete finite no-distinct-real-solution result. No new refuted verdict was emitted.

### Scope, source snapshots and reconciliation

The source is the read-only `scratchpad/cand/` directory named in B4. This is the selected 1,515-candidate research sample, not all B10. The launch snapshot was frozen at `2026-09-24T00:37:51.494256+00:00`; the final snapshot was frozen after the external embedding file completed, at `2026-09-24T01:13:41.405859+00:00`. Source bytes, complete-record counts, hashes and timestamps are retained under [snapshots/](results/round4/snapshots/). The candidate file and tree file were unchanged between snapshots. The launch embedding prefix contained 1,460 complete records; the final file contained all 1,515.

| Candidate scope | Embedded | Refuted | Unresolved | Total |
|---|---:|---:|---:|---:|
| External results at launch | 280 | 98 | 1,137 | 1,515 |
| External results after completion | 290 | 98 | 1,127 | 1,515 |
| Final merged candidate sample | 1,202 | 98 | 215 | 1,515 |

The recomputed external unresolved sets are [input-start.g6](results/round4/input-start.g6) and [input-end.g6](results/round4/input-end.g6). All 1,137 launch-unresolved graphs were attempted. Ten of our successful certificates overlap embeddings added by the external pass after launch; all ten are excluded from the 912 additional-embedding count. The merger prefers our explicit certificates on those overlaps so the official check includes every new embedding. It checks for conflicting embedded/refuted verdicts. The earlier rounds remain historical outputs; the Round 4 merge covers the supplied candidate sample.

### Coverage and budgets

`generic_exact.py` provides resumable arbitrary graph6-list input to both methods. The established entry points are `round2.py input` for msolve and `round3.py input` for G118. Input hashes and all search settings must agree on resume. Completed per-graph records are durable, and resumed embedded records are checked locally again. [ROUND4.md](ROUND4.md) gives usage, supported graph sizes and output layout.

Graphs were ordered by increasing generic degrees of freedom, with graph6 as the tie-breaker. Exact rigidity-rank evidence and the complete order are in [search/order.json](results/round4/search/order.json). Coverage below counts produced certificates before removing the ten external overlaps.

| Generic k | Attempted | G118 embedded | Msolve embedded | Total embedded | Unknown | Rigid triage |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 17 | 7 | 1 | 8 | 9 | 0 |
| 1 | 1,080 | 843 | 35 | 878 | 202 | 0 |
| 2 | 40 | 33 | 3 | 36 | 4 | 0 |
| Total | 1,137 | 883 | 39 | 922 | 215 | 0 |

| Method, in execution order | Graphs attempted | Embedded | No certificate | Method cap per graph (s) | Sum wall time (s) | Maximum observed (s) |
|---|---:|---:|---:|---:|---:|---:|
| G118_image | 1,137 | 883 | 254 | 10 | 349.772 | 9.015 |
| framed_pinned_msolve | 254 | 39 | 215 | 20 | 1510.079 | 18.918 |

The sum of complete per-graph wall times was 1860.764 seconds. Shared setup, rank ordering, pauses between batches and the checker are excluded from that sum. The official checker took 156.485 seconds. Certificate degrees were 4 for 183 graphs, 6 for one, 8 for 666, 16 for 71, and 20 for one. The largest compact new JSON record measured 756,922 bytes.

G118 was tried first and stopped after an exact certificate. It found no map for 244 inputs; ten mapped-image PARI conversions timed out. All 254 cases then reached msolve. Each method cap includes proposal work, solver execution and exact conversion. G118 mapping has an additional three-second and 2,000,000-node cap. GP explicitly uses one thread, a graph-derived seed and the exact success marker before local E-exact verification.

Msolve tried up to three actual edge frames. Flexible graphs had two independently seeded pin proposals per frame, with varied pin ordering and rational direction bounds. Preparation was capped at 2.5 seconds per attempt. Remaining solver time was divided across remaining attempts, with a conversion reserve, so these are total per-method budgets rather than 20 seconds for each frame. Success stops further attempts. There were 1,445 msolve-stage attempts: 39 exact embeddings, 146 solver timeouts, 156 positive-dimensional solver outputs, and 1,104 numeric proposal failures. Of the 254 msolve-stage graphs, 241 reached three frames and 220 reached all six flexible variants. The 313 attempts with prepared pins are recorded individually. No positive-dimensional or pinned negative result enters the rigid triage file.

The saved `I??GvHqf_` first pin proposal, frame [4,5], had residual about 1.085e-10 but minimum point separation about 2.215e-12 after its numerical restarts. The proposal guard rejected the near-collapse. A later attempt embedded that graph exactly. This illustrates why a failed proposal says nothing about non-embeddability; the guard itself is numerical and is not a proof. The exact certificate checks remain the sole acceptance gate.

### Validation and implementation notes

All 25 legacy msolve controls passed after the frame/pin extension. The 27 Round 4 checks exercised three edge frames on a rigid triangle, two pin variants on each of three frames on a flexible cycle, a degree-16 G118 image, marker rejection, budget exhaustion, unchanged resume output, and changed-input/configuration rejection. Every tested genuine embedding had a one-field mutation rejected for the expected reason. Six additional paired entry/trivial-graph cases exercised both actual CLI aliases, byte-identical resume, changed-budget rejection, and rational embeddings for graphs on zero through two vertices.

The official positive control accepted one newly produced certificate from each method. Its one-coordinate mutation was rejected with `edge_equation`; the exact final line was `REJECT run records_rejected`. The subsequent official sample run checked all 1,515 merged candidate records, including all 922 new embedding certificates and the 98 external tree refutations. Its verification code was unchanged. The existing wrapper redirected only scratch paths into `/tmp/gp10-embed/`.

Two implementation issues were corrected before the candidate pass. An initial control passed a Python Fraction directly to python-flint, which requires an explicit conversion here; the control now converts through a rational string. The resume control then exposed a JSON key-order mismatch between fresh and rebuilt record streams. Both paths now serialize with sorted keys. The mathematical records had been equivalent, but byte stability was required by the control. Fresh CLI runs and resumes subsequently passed. These initial failed controls are recorded as development failures, not hidden as production unknowns.

The audit measured Python 3.12.3, SymPy 1.14.0, python-flint 0.9.0, NumPy 2.5.3, SciPy 1.18.1 and pynauty 2.8.8.1. `SYMPY_GROUND_TYPES=python` and numerical thread counts of one were set before imports. The existing msolve allocation-size workaround and seeded runtime from Round 2 were reused; their provenance is retained with the rerun legacy controls. The installed msolve executable was unchanged.

The old quiet thresholds were not consulted. Search, control, merge and checker commands were niced and explicitly limited to 1,000,000 KiB of address space, following the stricter contract limit rather than COMMON.md's larger limit. There was at most one child process alongside the parent. Some early read-only inspection commands were niced but omitted an explicit `ulimit`; they did no solver work. All writes stayed in this module and its designated scratch tree. No git commands were run.

### Executed commands and artifacts

The following command prefix was used for computational steps, each as a separate command:

```sh
ulimit -v 1000000
exec nice -n 15 <repo>/pyenv-gp10/bin/python -B SCRIPT ARGUMENTS
```

The script/argument combinations were:

```text
research/gp-10/embed/round4_selftest.py
research/gp-10/embed/round4.py prepare
research/gp-10/embed/round4.py batch --start 0 --stop 10
research/gp-10/embed/round4.py batch --start 10 --stop 110
research/gp-10/embed/round4.py batch --start 110 --stop 310
research/gp-10/embed/round4.py batch --start 310 --stop 510
research/gp-10/embed/round4.py batch --start 510 --stop 710
research/gp-10/embed/round4_entry_controls.py
research/gp-10/embed/round4.py batch --start 710 --stop 910
research/gp-10/embed/round4.py batch --start 910 --stop 1137
research/gp-10/embed/round4_finish.py controls
research/gp-10/embed/official_check.py research/gp-10/embed/results/round4/run --output research/gp-10/embed/results/round4/run/out
research/gp-10/embed/round4_finish.py audit
```

Collection was invoked in a niced, limited frozen-Python here-document using `sys.path.insert(0,"research/gp-10/embed"); from round4 import collect,limits; limits(); s=collect()`, followed by printing the summary fields. It is reproducible with the same prefix and `research/gp-10/embed/round4.py collect`. All reported counts, versions, degree distributions, failure causes and timings come from that collection command or `round4_finish.py audit`. Batch timing records are in [search/batches/](results/round4/search/batches/). The selftest log is [round4-selftest.log](results/round4-selftest.log).

Deliverables: [new records](results/round4/new-records.jsonl), [merged candidate records](results/round4/merged-records.jsonl), [additional embeddings](results/round4/new-unique-embedded.g6), [UNDECIDED.g6](results/round4/UNDECIDED.g6), [rigid triage](results/round4/rigid-no-embedding.g6), [summary and coverage](results/round4/summary.json), [per-graph statistics](results/round4/stats.jsonl), [official checker log](results/round4/run/checker.log), [checker report](results/round4/run/out/report.json), [local controls](results/round4/controls/results.json), [entry controls](results/round4/controls/entry/results.json), [official controls](results/round4/controls/official-results.json), and [artifact audit](results/round4/audit.json). Every graph directory retains its proposals, expanded systems, raw solver output and attempt statistics where those phases ran.

Merged record SHA256: `c91ae95aeb33834d424d06ef5f723adf4ce7519e02cd6e4e2e182c640afadd6c`. New record SHA256: `1e9dcd9bfc44402a21e8e1f5eabc4a5541f68dbc0b78a0363638a0c1ef5fa8d0`. The checker report and final audit bind these artifacts to the frozen sample and unchanged checker source.

## UNCERTAIN

- The 215 graphs in Round 4 UNDECIDED.g6 remain undecided at the stated first-pass budgets. There was no longer-budget second pass. The empty rigid triage file is not evidence that the nine unresolved rigid graphs embed; their solver runs were incomplete or positive-dimensional.

- Flexible pin selection is heuristic. Regular-looking numerical points and nearby rational directions have no certified persistence radius. Most failed attempts could not find separated numerical points. Different pins, frames or longer budgets may work. Pinned failure never supports a refutation.

- G118 matching uses numerical adjacency only to propose an image, and tries one selected map. Incorrect numerical edges, missed maps, the node/time caps, or a costly field conversion can lose coverage. The final coordinates still require exact checks. Alternative maps and image fields above the exercised degrees were not explored systematically.

- Generic rigidity is not the dimension of every special unit-length component. This is why positive-dimensional results for nominally rigid graphs were left unknown. The least certain search assumption is that the chosen small-height direction pins are useful for the difficult flexible cases, not that they preserve every embedding.

- The most likely future implementation defects are frame-to-variable bookkeeping, parser behavior on new msolve output forms, and resume files produced by a different code version. Input/configuration hashes are enforced, while source hashes are recorded by the final audit rather than used as a resume compatibility gate. Concurrent writers to one output directory are unsupported. Native out-of-memory recovery was not deliberately forced in Round 4; timeout and native-exit paths were exercised by controls.

- The sample checker accepted the supplied candidate records. This module did not independently verify the candidate-selection deletion premise, derive a minimal forbidden list, rerun the full B10 pipeline, or merge other builders' wider result sets. The earlier rounds' historical limitations, including the interpretation of H2 table displacements, remain as recorded above. No classification or minimality claim follows from this sample run.
