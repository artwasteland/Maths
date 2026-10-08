Both new producers are implemented and wired after the existing escalation portfolio in the `full` policy.
Every decision below is backed by the unchanged GP-10 sample-profile checker.
The complete 74-graph replay ended with `ACCEPT run verified`.

The production files are:

| File | Purpose |
| --- | --- |
| [branch_refute.py](branch_refute.py) | Choose frames from rhombi and triangles, enumerate apex choices, discover collision covers or root-free projections, and assemble a bounded real-DAG proof. |
| [subfield_exact.py](subfield_exact.py) | Refine retained numerical points, recognize and factor coordinate fields, exploit reflection subfields, and construct E-exact coordinates with an isolating interval. |
| [late_stage.py](late_stage.py) | Enforce worker/tool wall caps, monitor memory, terminate descendants, and retain search diagnostics. |
| [stages.py](stages.py) | Add 120-second branch and 180-second subfield searches, each with a separate 120-second checker budget. |
| [store.py](store.py), [export.py](export.py) | Preserve frames, saturation pairs, branches and field candidates in analyst packets and imported UNKNOWN history. |
| [test_late_stages.py](test_late_stages.py) | Exercise the actual pipeline adapters, measure independent stage coverage, run mutations and recheck unchanged positives. |
| [LATE-STAGES.md](LATE-STAGES.md) | Explain the algorithms, limits and standalone/reproduction commands. |

No checker, contract, proof rule, dependency, or git metadata was changed.
These are ordinary R-real-DAG and E-exact records under the existing GP-10 proofs.
The producers contain no graph-specific target polynomials or analyst-certificate lookup.

The final reproduction measurements were:

| Graph | Decision | Search seconds | Checker seconds | Total seconds | Certificate |
| --- | --- | ---: | ---: | ---: | --- |
| ``JaICZOo@Wd_`` | refuted | 16.086 | 6.109 | 22.619 | 209 rows; 6,480,258 bytes; [receipt](results/late-stages/receipts/5e088a918b09f0b2/checker.log) |
| ``JSO@]OSDjB?`` | refuted | 23.112 | 7.613 | 31.430 | 152 rows; 7,011,203 bytes; [receipt](results/late-stages/receipts/9e3d38680a6c33a3/checker.log) |
| ``JoCBkhGIGJ_`` | embedded | 102.928 | 70.442 | 173.403 | degree 40; 162,995 bytes; [receipt](results/late-stages/receipts/b0d8975366ef9ea4/checker.log) |
| ``J`C@KHIB^a?`` | embedded | 69.509 | 21.570 | 91.158 | degree 36; 33,874 bytes; [receipt](results/late-stages/receipts/77bf242bb4948d9f/checker.log) |

These are wall times from the final sequential measurement on the shared host.
They include refinement, recognition or algebra, proof construction and checking, but exclude the earlier generation of retained numerical seeds and producer development.
The self-contained numeric inputs are in [inputs.json](results/late-stages/inputs.json).

For `JaICZOo@Wd_`, the selected frame is (8,10).
All four apex branches are retained; three give zero products of squared distances on selected saturation pairs, and the fourth gives the root-free octic in y0.
The combined selectors derive that octic in the original framed system.
For `JSO@]OSDjB?`, frame (8,9) gives the root-free degree-18 polynomial in x0 without an additional apex split.
The two embedding searches choose their fields from the numerical coordinates and factor the recognition polynomials before fitting coordinates.
The reported degree-40 and degree-36 certificates are newly generated ordinary field records.

Independent coverage on the pre-escalation cohorts follows.
Each stage was run on every member, even when the other stage had already decided it.
No propagation decisions are included.

| Cohort | Graphs | Branch R | Branch search/check seconds | Subfield E | Subfield search/check seconds | Union decided |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| report_sample1 | 13 | 1 | 177.804 / 6.109 | 4 | 244.353 / 84.845 | 5 |
| report_sample2 | 59 | 5 | 635.037 / 17.085 | 12 | 517.360 / 56.473 | 17 |
| report_pooled | 72 | 6 | 812.840 / 23.195 | 16 | 761.712 / 141.318 | 22 |
| pipeline_sample2 | 41 | 5 | 496.525 / 17.085 | 11 | 464.867 / 51.035 | 16 |
| union | 74 | 6 | 835.958 / 23.195 | 16 | 762.196 / 141.318 | 22 |

The report's cohorts contain 13 + 59 = 72 graphs.
The newer pipeline bundle has 41 pre-escalation unknowns; 39 overlap those 72, so their union has 74 graphs.
The extra two are `J?dGH_bo_f_` and ``JGCG_Kb`]o?``.
Numerical inputs come from retained escalation outputs, not from analyst exact certificates.
This measures the new stages on those cohorts; it does not charge them for the earlier portfolio's numerical searches.

Of the six hard survivors in ESCALATION-REPORT.txt, four are decided automatically by these stages.
The remaining cases are `J_?gkpAYHb?` and `JqM??CNGqg_`.
Thus the reported post-escalation tail falls from six to two before analysts; the newer 2,000-sample bundle's tail falls from four to two.
This is measured sample coverage, with no new census or minimality claim.

The controls use valid JSON serialized from the real generated records.
For the missing-branch control, one complete selector contribution is deleted and now-unused rows are pruned and renumbered.
The selector control changes one nonzero rational coefficient in the final combination.
The coordinate control adds 1/17 to one coordinate coefficient.
The checker output is:

```text
missing-branch
REJECT record JaICZOo@Wd_ dag_row_identity: row 160
REJECT run records_rejected
selector-coefficient
REJECT record JaICZOo@Wd_ dag_row_identity: row 208
REJECT run records_rejected
perturbed-coordinate
REJECT record JoCBkhGIGJ_ edge_equation: (0, 1)
REJECT run records_rejected
```

Branch coverage is enforced by the existing polynomial identity rule, so the first two controls correctly fail at `dag_row_identity`; there is no new branch-trust rule in the checker.
All four original records were then rechecked unchanged, with their before/after SHA-256 hashes asserted equal.
Their logs all end with `ACCEPT run verified`.
[controls.json](results/late-stages/controls.json) contains exact outputs and hashes; the mutations and receipts are retained in [controls/](results/late-stages/controls/).

The final complete replay counts are {'embedded': 16, 'refuted': 6, 'unknown': 52}.
The complete replay took 85.997 wall seconds.
Minimum recorded MemAvailable was 2.718 GiB during the measurement and 2.343 GiB during the final replay, above the 1.5 GiB floor.
Only one heavy process ran at a time; native solver threads were set to one.
The frozen checker hash is `d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04`.
The complete replay receipt, source hashes and compressed records are under [results/late-stages/](results/late-stages/).
Every attempt has a row in [measurements.csv](results/late-stages/measurements.csv); [measurements.json](results/late-stages/measurements.json) retains the full diagnostics.

Validation also exercised a constant-target refutation and the reader for the original large unverified coordinate proposal.
The latter produced a fresh degree-40 E-exact record from the saved proposal in 93.187 seconds, followed by frozen-checker ACCEPT in 27.386 seconds.
During development, the wider cohort exposed two bounded-search issues: products growing in positive-dimensional quotients, and a triangle coordinate equation that was already zero.
The final code detects the unsupported dimension before forming large products and skips zero polynomial divisors in reduction.
It also handles PARI stack setup on a separate input line and rounds long decimal seeds before mpmath's integer parser without changing the interpreter's digit limit.

The new local/imported analyst-hint assertions passed.
The existing `test_history.py` regression fails at `history_duplicate_ancestor` in round 2.
It fails identically after substituting the unmodified HEAD `Store.unknown_record` method; `drive.py` and `test_history.py` are unchanged.
The existing importer retains ancestor attempts twice on repeated merged rounds.
This pre-existing issue is outside the new stages; exact logs, the baseline method source, and the substitution harness are retained in [extra-validation/](results/late-stages/extra-validation/).

The next additions I would make are rational pins for flexible numerical configurations, followed by balanced rational-function recognition over Q(sqrt(3)), as the A34 analyst's results suggest.
That targets the two remaining hard sample cases.
For refutations, I would reuse each branch basis across more elimination coordinates and frames, and use least common multiples of branch targets to reduce proof size.
Adaptive recognition precision would reduce the cost of the lower-degree successes.

Replay the measurement with:

```bash
~/tools/pyenv-gp10/bin/python research/gp-11/pipeline/test_late_stages.py \
  --cohort --output /tmp/gp11-late-reproduction
```

For a quick reproduction plus all three controls, omit `--cohort`.
To replay the retained complete record bundle, copy `input.g6`, `UNKNOWN.g6` and `run.json` to a writable run directory, decompress `records.jsonl.gz` there as `records.jsonl`, then use the frozen sample checker with its scratch directory redirected as in the test runner.
