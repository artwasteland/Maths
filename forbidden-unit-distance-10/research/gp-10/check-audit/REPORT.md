# CHECKAUDIT report

## VERDICT

BLOCKER: 0. MAJOR: 1. MINOR: 2.

No invalid full-run fixture was accepted. This is a bounded soundness audit, not a proof that the checker is sound. The required smaller control profiles are missing, so the amended control gate is not fully implemented. The minor findings are sound differences in accepted syntax.

The final audit matched all 304 expectations: 257 full run checks (51 accepted baselines and 206 rejected mutations), plus 47 direct Sturm checks (16 polynomials with no real zero and 31 red companions). Every accepted baseline has a direct red companion. All 237 mutation links were checked against the retained positive fixture.

These counts, findings, environment values and exact outputs come from the commands below and [cases/results.json](cases/results.json), [cases/index.json](cases/index.json), and [findings.json](findings.json). Finding counts are computed from the reviewed finding inventory by the report command.

Executed from the repository root, with each block a separate command:

```sh
ulimit -v 1000000
exec nice -n 15 env PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/build_cases.py
```

```sh
ulimit -v 1000000
exec nice -n 15 env PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/audit.py --all
```

```sh
ulimit -v 1000000
exec nice -n 15 env PYTHONDONTWRITEBYTECODE=1 SYMPY_GROUND_TYPES=python <repo>/pyenv-gp10/bin/python research/gp-10/check-audit/make_report.py
```

Observed audit wall time: 16.448262 seconds; maximum resident memory reported by the audit process: 85572 KiB; inherited niceness: 19; address-space ceiling: 1024000000 bytes. The suite is a stated deterministic sample of certificates and run directories. No full production classification was attempted, and the suite completed below the common time threshold.

Environment: Python 3.12.3 from `<repo>/pyenv-gp10/bin/python`, SymPy 1.14.0, python-flint 0.9.0, `SYMPY_GROUND_TYPES=python`.

Checker SHA256: `9064ccc64ae900aee07672f14d4e3fec4f4cb6a09ec0042bb2db7e6e8df3ce6f`. Trusted kernel SHA256: `63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de`. The audit asserted that the checker hash did not change during replay.

The original checker is imported through the pre-existing [runner.py](runner.py). The adapter changes only scratch paths and bytecode settings. Each full case calls the original `main(argv)` in the audit process; nauty is its only child. This keeps the workload within the process limit without changing verification branches. All outputs and fixtures are within this module or `/tmp/gp10-checkaudit/`. No git commands were used, and no producer, checker or trusted data files were edited.

Process deviation: the initial read of COMMON.md used `nice -n 10 cat research/gp-10/briefs/COMMON.md` without a virtual-memory limit. After reading that rule, commands used `nice -n 15`; the brief and contract reads used `ulimit -v 1500000`, and remaining commands used the stricter `ulimit -v 1000000` required by the contract's machine limit. The contract takes precedence over the common file's looser memory allowance.

The fixture builder initially needed a type-sensitive comparison for boolean mutations. Early audit passes also exposed an incorrectly regenerated input for the noncanonical-record test and literal newline escapes in a new TU fixture. These were audit-fixture mistakes, corrected before the final replay. No checker changes were made to obtain passing results.

## TEST CASES

Every test input and its observed output is retained under [cases/](cases/). The case index records the positive parent and the mutation path. A record mutation changes exactly its declared JSON field; the run envelope is rebuilt when the graph identity changes. A run mutation changes one input file, such as one JSONL record, a pointer field, a coverage line or a proposed minimal list. Helper mutations change one polynomial coefficient. These scopes are distinguished below instead of treating a whole changed stream as a single scalar field.

Every invocation below was actually executed inside the `audit.py --all` command above. `gp10check.main` lines give its exact argument vector. The following fenced output is its captured stdout, including the final run decision; it is not reconstructed from an expected result. For helper cases the output is explicitly an adapter rendering of the helper's return value or rejection exception, not a CLI ACCEPT line. The stored checker report and record logs provide additional structured evidence.

To replay one case and its genuine positive parent, use the same command wrapper with `audit.py --case CASE_NAME`. The audit exits successfully only if the expected acceptance or exact rejection reason is observed. Full checker exit codes are recorded separately in results.json.

Coverage notes: all frozen forbidden members were targeted by changing the g6 of an accepted distinct rational embedding. These are graph-binding attacks, not evidence that difficult near-solutions were exhausted. The named UDG tree attacks use an accepted same-order K4-with-isolates refutation and change only the record's g6. They must fail at the trusted kernel's comparison with the current graph.

A declared-unknown sample may correctly print ACCEPT while its report remains conditional. A missing record, a missing unknown-list entry or a pointer to an unknown graph must reject. A sample profile never establishes production completeness. The smaller-family sample baselines deliberately contain declared unknowns and are not successful classification controls.

### 1. existing-c4

File: [cases/existing-c4/records.jsonl](cases/existing-c4/records.jsonl). Run manifest: [run.json](cases/existing-c4/run.json). Exact saved output: [observed.stdout](cases/existing-c4/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-c4', '--output', '/tmp/gp10-checkaudit/results/existing-c4'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 2. existing-triangle

File: [cases/existing-triangle/records.jsonl](cases/existing-triangle/records.jsonl). Run manifest: [run.json](cases/existing-triangle/run.json). Exact saved output: [observed.stdout](cases/existing-triangle/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-triangle', '--output', '/tmp/gp10-checkaudit/results/existing-triangle'])
```

```text
ACCEPT record Bw verified
ACCEPT run verified
```

### 3. existing-moser

File: [cases/existing-moser/records.jsonl](cases/existing-moser/records.jsonl). Run manifest: [run.json](cases/existing-moser/run.json). Exact saved output: [observed.stdout](cases/existing-moser/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-moser', '--output', '/tmp/gp10-checkaudit/results/existing-moser'])
```

```text
ACCEPT record F`o~_ verified
ACCEPT run verified
```

### 4. existing-coordinate-perturbed

File: [cases/existing-coordinate-perturbed/records.jsonl](cases/existing-coordinate-perturbed/records.jsonl). Run manifest: [run.json](cases/existing-coordinate-perturbed/run.json). Exact saved output: [observed.stdout](cases/existing-coordinate-perturbed/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-coordinate-perturbed', '--output', '/tmp/gp10-checkaudit/results/existing-coordinate-perturbed'])
```

```text
REJECT record Cr edge_equation: (0, 1)
REJECT run records_rejected
```

### 5. existing-collision-edges-fine

File: [cases/existing-collision-edges-fine/records.jsonl](cases/existing-collision-edges-fine/records.jsonl). Run manifest: [run.json](cases/existing-collision-edges-fine/run.json). Exact saved output: [observed.stdout](cases/existing-collision-edges-fine/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 3], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-collision-edges-fine', '--output', '/tmp/gp10-checkaudit/results/existing-collision-edges-fine'])
```

```text
REJECT record Cr exact_collision: (0, 3)
REJECT run records_rejected
```

### 6. existing-interval-no-sign

File: [cases/existing-interval-no-sign/records.jsonl](cases/existing-interval-no-sign/records.jsonl). Run manifest: [run.json](cases/existing-interval-no-sign/run.json). Exact saved output: [observed.stdout](cases/existing-interval-no-sign/observed.stdout).

Positive parent: [existing-triangle](cases/existing-triangle/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "interval"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-interval-no-sign', '--output', '/tmp/gp10-checkaudit/results/existing-interval-no-sign'])
```

```text
REJECT record Bw interval_sign_change
REJECT run records_rejected
```

### 7. existing-unknown-record-field

File: [cases/existing-unknown-record-field/records.jsonl](cases/existing-unknown-record-field/records.jsonl). Run manifest: [run.json](cases/existing-unknown-record-field/run.json). Exact saved output: [observed.stdout](cases/existing-unknown-record-field/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["unexpected"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-unknown-record-field', '--output', '/tmp/gp10-checkaudit/results/existing-unknown-record-field'])
```

```text
REJECT record records.jsonl:1 schema: record: missing=[] extra=['unexpected']
REJECT run records_rejected
```

### 8. existing-verdict-tu

File: [cases/existing-verdict-tu/records.jsonl](cases/existing-verdict-tu/records.jsonl). Run manifest: [run.json](cases/existing-verdict-tu/run.json). Exact saved output: [observed.stdout](cases/existing-verdict-tu/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["verdict"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-verdict-tu', '--output', '/tmp/gp10-checkaudit/results/existing-verdict-tu'])
```

```text
REJECT record Cr verdict_allowlist
REJECT run records_rejected
```

### 9. existing-verdict-pass

File: [cases/existing-verdict-pass/records.jsonl](cases/existing-verdict-pass/records.jsonl). Run manifest: [run.json](cases/existing-verdict-pass/run.json). Exact saved output: [observed.stdout](cases/existing-verdict-pass/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["verdict"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-verdict-pass', '--output', '/tmp/gp10-checkaudit/results/existing-verdict-pass'])
```

```text
REJECT record Cr verdict_allowlist
REJECT run records_rejected
```

### 10. existing-verdict-forbidden

File: [cases/existing-verdict-forbidden/records.jsonl](cases/existing-verdict-forbidden/records.jsonl). Run manifest: [run.json](cases/existing-verdict-forbidden/run.json). Exact saved output: [observed.stdout](cases/existing-verdict-forbidden/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["verdict"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-verdict-forbidden', '--output', '/tmp/gp10-checkaudit/results/existing-verdict-forbidden'])
```

```text
REJECT record Cr verdict_allowlist
REJECT run records_rejected
```

### 11. existing-k4-tree

File: [cases/existing-k4-tree/records.jsonl](cases/existing-k4-tree/records.jsonl). Run manifest: [run.json](cases/existing-k4-tree/run.json). Exact saved output: [observed.stdout](cases/existing-k4-tree/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k4-tree', '--output', '/tmp/gp10-checkaudit/results/existing-k4-tree'])
```

```text
ACCEPT record C~ verified
ACCEPT run verified
```

### 12. existing-tree-collision-pair

File: [cases/existing-tree-collision-pair/records.jsonl](cases/existing-tree-collision-pair/records.jsonl). Run manifest: [run.json](cases/existing-tree-collision-pair/run.json). Exact saved output: [observed.stdout](cases/existing-tree-collision-pair/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "move", "pair"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tree-collision-pair', '--output', '/tmp/gp10-checkaudit/results/existing-tree-collision-pair'])
```

```text
REJECT record C~ tree: R-tree.tree.move.pair: invalid distinct vertices
REJECT run records_rejected
```

### 13. existing-k23-tree

File: [cases/existing-k23-tree/records.jsonl](cases/existing-k23-tree/records.jsonl). Run manifest: [run.json](cases/existing-k23-tree/run.json). Exact saved output: [observed.stdout](cases/existing-k23-tree/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k23-tree', '--output', '/tmp/gp10-checkaudit/results/existing-k23-tree'])
```

```text
ACCEPT record DFw verified
ACCEPT run verified
```

### 14. existing-k4-isolate-null

File: [cases/existing-k4-isolate-null/records.jsonl](cases/existing-k4-isolate-null/records.jsonl). Run manifest: [run.json](cases/existing-k4-isolate-null/run.json). Exact saved output: [observed.stdout](cases/existing-k4-isolate-null/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k4-isolate-null', '--output', '/tmp/gp10-checkaudit/results/existing-k4-isolate-null'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 15. existing-frame-nonedge

File: [cases/existing-frame-nonedge/records.jsonl](cases/existing-frame-nonedge/records.jsonl). Run manifest: [run.json](cases/existing-frame-nonedge/run.json). Exact saved output: [observed.stdout](cases/existing-frame-nonedge/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "frame"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-frame-nonedge', '--output', '/tmp/gp10-checkaudit/results/existing-frame-nonedge'])
```

```text
REJECT record DJ[ frame_not_edge
REJECT run records_rejected
```

### 16. existing-extra-nonedge-generator

File: [cases/existing-extra-nonedge-generator/records.jsonl](cases/existing-extra-nonedge-generator/records.jsonl). Run manifest: [run.json](cases/existing-extra-nonedge-generator/run.json). Exact saved output: [observed.stdout](cases/existing-extra-nonedge-generator/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "system"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-extra-nonedge-generator', '--output', '/tmp/gp10-checkaudit/results/existing-extra-nonedge-generator'])
```

```text
REJECT record DJ[ system_mismatch: generator keys
REJECT run records_rejected
```

### 17. existing-cofactor-coefficient

File: [cases/existing-cofactor-coefficient/records.jsonl](cases/existing-cofactor-coefficient/records.jsonl). Run manifest: [run.json](cases/existing-cofactor-coefficient/run.json). Exact saved output: [observed.stdout](cases/existing-cofactor-coefficient/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "e:1,3", 0, 0], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-cofactor-coefficient', '--output', '/tmp/gp10-checkaudit/results/existing-cofactor-coefficient'])
```

```text
REJECT record DJ[ cofactor_identity
REJECT run records_rejected
```

### 18. existing-k4-real-sos

File: [cases/existing-k4-real-sos/records.jsonl](cases/existing-k4-real-sos/records.jsonl). Run manifest: [run.json](cases/existing-k4-real-sos/run.json). Exact saved output: [observed.stdout](cases/existing-k4-real-sos/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k4-real-sos', '--output', '/tmp/gp10-checkaudit/results/existing-k4-real-sos'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 19. existing-sos-zero-constant

File: [cases/existing-sos-zero-constant/records.jsonl](cases/existing-sos-zero-constant/records.jsonl). Run manifest: [run.json](cases/existing-sos-zero-constant/run.json). Exact saved output: [observed.stdout](cases/existing-sos-zero-constant/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sos", "c"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-sos-zero-constant', '--output', '/tmp/gp10-checkaudit/results/existing-sos-zero-constant'])
```

```text
REJECT record DJ[ sos_constant_positive
REJECT run records_rejected
```

### 20. existing-sos-negative-weight

File: [cases/existing-sos-negative-weight/records.jsonl](cases/existing-sos-negative-weight/records.jsonl). Run manifest: [run.json](cases/existing-sos-negative-weight/run.json). Exact saved output: [observed.stdout](cases/existing-sos-negative-weight/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sos", "squares", 0, 0], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-sos-negative-weight', '--output', '/tmp/gp10-checkaudit/results/existing-sos-negative-weight'])
```

```text
REJECT record DJ[ sos_weight_positive
REJECT run records_rejected
```

### 21. existing-sos-wrong-square

File: [cases/existing-sos-wrong-square/records.jsonl](cases/existing-sos-wrong-square/records.jsonl). Run manifest: [run.json](cases/existing-sos-wrong-square/run.json). Exact saved output: [observed.stdout](cases/existing-sos-wrong-square/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sos", "squares", 0, 1], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-sos-wrong-square', '--output', '/tmp/gp10-checkaudit/results/existing-sos-wrong-square'])
```

```text
REJECT record DJ[ sos_identity
REJECT run records_rejected
```

### 22. existing-k4-real-sturm

File: [cases/existing-k4-real-sturm/records.jsonl](cases/existing-k4-real-sturm/records.jsonl). Run manifest: [run.json](cases/existing-k4-real-sturm/run.json). Exact saved output: [observed.stdout](cases/existing-k4-real-sturm/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k4-real-sturm', '--output', '/tmp/gp10-checkaudit/results/existing-k4-real-sturm'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 23. existing-sturm-wrong-variable

File: [cases/existing-sturm-wrong-variable/records.jsonl](cases/existing-sturm-wrong-variable/records.jsonl). Run manifest: [run.json](cases/existing-sturm-wrong-variable/run.json). Exact saved output: [observed.stdout](cases/existing-sturm-wrong-variable/observed.stdout).

Positive parent: [existing-k4-real-sturm](cases/existing-k4-real-sturm/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sturm"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-sturm-wrong-variable', '--output', '/tmp/gp10-checkaudit/results/existing-sturm-wrong-variable'])
```

```text
REJECT record DJ[ sturm_multivariate
REJECT run records_rejected
```

### 24. existing-k23-saturated-null

File: [cases/existing-k23-saturated-null/records.jsonl](cases/existing-k23-saturated-null/records.jsonl). Run manifest: [run.json](cases/existing-k23-saturated-null/run.json). Exact saved output: [observed.stdout](cases/existing-k23-saturated-null/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-k23-saturated-null', '--output', '/tmp/gp10-checkaudit/results/existing-k23-saturated-null'])
```

```text
ACCEPT record DFw verified
ACCEPT run verified
```

### 25. existing-saturation-cofactor

File: [cases/existing-saturation-cofactor/records.jsonl](cases/existing-saturation-cofactor/records.jsonl). Run manifest: [run.json](cases/existing-saturation-cofactor/run.json). Exact saved output: [observed.stdout](cases/existing-saturation-cofactor/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "s:3,4"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-saturation-cofactor', '--output', '/tmp/gp10-checkaudit/results/existing-saturation-cofactor'])
```

```text
REJECT record DFw cofactor_identity
REJECT run records_rejected
```

### 26. existing-tu-chain

File: [cases/existing-tu-chain/records.jsonl](cases/existing-tu-chain/records.jsonl). Run manifest: [run.json](cases/existing-tu-chain/run.json). Exact saved output: [observed.stdout](cases/existing-tu-chain/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Copied checker fixture, replayed independently through the full run path.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tu-chain', '--output', '/tmp/gp10-checkaudit/results/existing-tu-chain'])
```

```text
ACCEPT record K_?G?cks`M^? verified
ACCEPT run verified
```

### 27. existing-tu-final-edge

File: [cases/existing-tu-final-edge/records.jsonl](cases/existing-tu-final-edge/records.jsonl). Run manifest: [run.json](cases/existing-tu-final-edge/run.json). Exact saved output: [observed.stdout](cases/existing-tu-final-edge/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "end", "map"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tu-final-edge', '--output', '/tmp/gp10-checkaudit/results/existing-tu-final-edge'])
```

```text
REJECT record K_?G?cks`M^? map_not_edge_preserving: TU forbidden end: (0, 2) -> (0, 2)
REJECT run records_rejected
```

### 28. existing-tu-future-edge

File: [cases/existing-tu-future-edge/records.jsonl](cases/existing-tu-future-edge/records.jsonl). Run manifest: [run.json](cases/existing-tu-future-edge/run.json). Exact saved output: [observed.stdout](cases/existing-tu-future-edge/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tu-future-edge', '--output', '/tmp/gp10-checkaudit/results/existing-tu-future-edge'])
```

```text
REJECT record K_?G?cks`M^? map_not_edge_preserving: TU step 0: (0, 1) -> (10, 11)
REJECT run records_rejected
```

### 29. existing-tu-already-edge

File: [cases/existing-tu-already-edge/records.jsonl](cases/existing-tu-already-edge/records.jsonl). Run manifest: [run.json](cases/existing-tu-already-edge/run.json). Exact saved output: [observed.stdout](cases/existing-tu-already-edge/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tu-already-edge', '--output', '/tmp/gp10-checkaudit/results/existing-tu-already-edge'])
```

```text
REJECT record K_?G?cks`M^? tu_pair_already_edge
REJECT run records_rejected
```

### 30. existing-tu-wrong-pair

File: [cases/existing-tu-wrong-pair/records.jsonl](cases/existing-tu-wrong-pair/records.jsonl). Run manifest: [run.json](cases/existing-tu-wrong-pair/run.json). Exact saved output: [observed.stdout](cases/existing-tu-wrong-pair/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps", 0, "pair"], "scope": "record"}`.

Copied checker mutation with its declared positive and single changed field.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/existing-tu-wrong-pair', '--output', '/tmp/gp10-checkaudit/results/existing-tu-wrong-pair'])
```

```text
REJECT record K_?G?cks`M^? tu_distinguished_pair
REJECT run records_rejected
```

### 31. run-pointers

File: [cases/run-pointers/records.jsonl](cases/run-pointers/records.jsonl). Run manifest: [run.json](cases/run-pointers/run.json). Exact saved output: [observed.stdout](cases/run-pointers/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-pointers', '--output', '/tmp/gp10-checkaudit/results/run-pointers'])
```

```text
ACCEPT record Bw verified
ACCEPT record A_ verified
ACCEPT run verified
```

### 32. run-mixed

File: [cases/run-mixed/records.jsonl](cases/run-mixed/records.jsonl). Run manifest: [run.json](cases/run-mixed/run.json). Exact saved output: [observed.stdout](cases/run-mixed/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-mixed', '--output', '/tmp/gp10-checkaudit/results/run-mixed'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
ACCEPT run verified
```

### 33. run-unknown

File: [cases/run-unknown/records.jsonl](cases/run-unknown/records.jsonl). Run manifest: [run.json](cases/run-unknown/run.json). Exact saved output: [observed.stdout](cases/run-unknown/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-unknown', '--output', '/tmp/gp10-checkaudit/results/run-unknown'])
```

```text
ACCEPT record A_ verified
ACCEPT run verified
```

### 34. run-refutation-pointer

File: [cases/run-refutation-pointer/records.jsonl](cases/run-refutation-pointer/records.jsonl). Run manifest: [run.json](cases/run-refutation-pointer/run.json). Exact saved output: [observed.stdout](cases/run-refutation-pointer/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-refutation-pointer', '--output', '/tmp/gp10-checkaudit/results/run-refutation-pointer'])
```

```text
ACCEPT record C~ verified
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 35. run-frozen-pointer

File: [cases/run-frozen-pointer/records.jsonl](cases/run-frozen-pointer/records.jsonl). Run manifest: [run.json](cases/run-frozen-pointer/run.json). Exact saved output: [observed.stdout](cases/run-frozen-pointer/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-frozen-pointer', '--output', '/tmp/gp10-checkaudit/results/run-frozen-pointer'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 36. run-tu-refuted-pointer

File: [cases/run-tu-refuted-pointer/records.jsonl](cases/run-tu-refuted-pointer/records.jsonl). Run manifest: [run.json](cases/run-tu-refuted-pointer/run.json). Exact saved output: [observed.stdout](cases/run-tu-refuted-pointer/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-tu-refuted-pointer', '--output', '/tmp/gp10-checkaudit/results/run-tu-refuted-pointer'])
```

```text
ACCEPT record C~ verified
ACCEPT record K_?G?cks`M^? verified
ACCEPT run verified
```

### 37. run-minimality

File: [cases/run-minimality/records.jsonl](cases/run-minimality/records.jsonl). Run manifest: [run.json](cases/run-minimality/run.json). Exact saved output: [observed.stdout](cases/run-minimality/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-minimality', '--output', '/tmp/gp10-checkaudit/results/run-minimality'])
```

```text
ACCEPT record DFw verified
ACCEPT record DF{ verified
ACCEPT run verified
```

### 38. run-conditional-minimality

File: [cases/run-conditional-minimality/records.jsonl](cases/run-conditional-minimality/records.jsonl). Run manifest: [run.json](cases/run-conditional-minimality/run.json). Exact saved output: [observed.stdout](cases/run-conditional-minimality/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-conditional-minimality', '--output', '/tmp/gp10-checkaudit/results/run-conditional-minimality'])
```

```text
ACCEPT record DF{ verified
ACCEPT record DFw verified
ACCEPT run verified
```

### 39. run-pointer-noninjective

File: [cases/run-pointer-noninjective/records.jsonl](cases/run-pointer-noninjective/records.jsonl). Run manifest: [run.json](cases/run-pointer-noninjective/run.json). Exact saved output: [observed.stdout](cases/run-pointer-noninjective/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-pointer-noninjective', '--output', '/tmp/gp10-checkaudit/results/run-pointer-noninjective'])
```

```text
ACCEPT record Bw verified
REJECT record A_ map_not_injective: E-ptr
REJECT run records_rejected
```

### 40. run-pointer-cycle

File: [cases/run-pointer-cycle/records.jsonl](cases/run-pointer-cycle/records.jsonl). Run manifest: [run.json](cases/run-pointer-cycle/run.json). Exact saved output: [observed.stdout](cases/run-pointer-cycle/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-pointer-cycle', '--output', '/tmp/gp10-checkaudit/results/run-pointer-cycle'])
```

```text
ACCEPT record Bw verified
REJECT record A_ pointer_cycle
REJECT run records_rejected
```

### 41. run-pointer-missing

File: [cases/run-pointer-missing/records.jsonl](cases/run-pointer-missing/records.jsonl). Run manifest: [run.json](cases/run-pointer-missing/run.json). Exact saved output: [observed.stdout](cases/run-pointer-missing/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "hosts.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-pointer-missing', '--output', '/tmp/gp10-checkaudit/results/run-pointer-missing'])
```

```text
REJECT record A_ pointer_target_missing
REJECT run records_rejected
```

### 42. run-coverage-missing

File: [cases/run-coverage-missing/records.jsonl](cases/run-coverage-missing/records.jsonl). Run manifest: [run.json](cases/run-coverage-missing/run.json). Exact saved output: [observed.stdout](cases/run-coverage-missing/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-coverage-missing', '--output', '/tmp/gp10-checkaudit/results/run-coverage-missing'])
```

```text
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
REJECT run coverage
```

### 43. run-coverage-extra

File: [cases/run-coverage-extra/records.jsonl](cases/run-coverage-extra/records.jsonl). Run manifest: [run.json](cases/run-coverage-extra/run.json). Exact saved output: [observed.stdout](cases/run-coverage-extra/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-coverage-extra', '--output', '/tmp/gp10-checkaudit/results/run-coverage-extra'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
ACCEPT record A_ verified
REJECT run coverage
```

### 44. run-coverage-duplicate

File: [cases/run-coverage-duplicate/records.jsonl](cases/run-coverage-duplicate/records.jsonl). Run manifest: [run.json](cases/run-coverage-duplicate/run.json). Exact saved output: [observed.stdout](cases/run-coverage-duplicate/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-coverage-duplicate', '--output', '/tmp/gp10-checkaudit/results/run-coverage-duplicate'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
REJECT record Cr duplicate_record
REJECT run duplicate_record
```

### 45. run-verdict-conflict

File: [cases/run-verdict-conflict/records.jsonl](cases/run-verdict-conflict/records.jsonl). Run manifest: [run.json](cases/run-verdict-conflict/run.json). Exact saved output: [observed.stdout](cases/run-verdict-conflict/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-verdict-conflict', '--output', '/tmp/gp10-checkaudit/results/run-verdict-conflict'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
REJECT record Cr embedded_refuted_conflict
REJECT run embedded_refuted_conflict
```

### 46. run-unknown-missing

File: [cases/run-unknown-missing/records.jsonl](cases/run-unknown-missing/records.jsonl). Run manifest: [run.json](cases/run-unknown-missing/run.json). Exact saved output: [observed.stdout](cases/run-unknown-missing/observed.stdout).

Positive parent: [run-unknown](cases/run-unknown/). Mutation: `{"file": "UNKNOWN.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-unknown-missing', '--output', '/tmp/gp10-checkaudit/results/run-unknown-missing'])
```

```text
ACCEPT record A_ verified
REJECT run unknown_exactness
```

### 47. run-unknown-extra

File: [cases/run-unknown-extra/records.jsonl](cases/run-unknown-extra/records.jsonl). Run manifest: [run.json](cases/run-unknown-extra/run.json). Exact saved output: [observed.stdout](cases/run-unknown-extra/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "UNKNOWN.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-unknown-extra', '--output', '/tmp/gp10-checkaudit/results/run-unknown-extra'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
REJECT run unknown_exactness
```

### 48. run-minimality-false-claim

File: [cases/run-minimality-false-claim/records.jsonl](cases/run-minimality-false-claim/records.jsonl). Run manifest: [run.json](cases/run-minimality-false-claim/run.json). Exact saved output: [observed.stdout](cases/run-minimality-false-claim/observed.stdout).

Positive parent: [run-minimality](cases/run-minimality/). Mutation: `{"file": "claim.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-minimality-false-claim', '--output', '/tmp/gp10-checkaudit/results/run-minimality-false-claim'])
```

```text
ACCEPT record DFw verified
ACCEPT record DF{ verified
REJECT run minimality_claim_refuted_deletion
```

### 49. run-withheld-index

File: [cases/run-withheld-index/records.jsonl](cases/run-withheld-index/records.jsonl). Run manifest: [run.json](cases/run-withheld-index/run.json). Exact saved output: [observed.stdout](cases/run-withheld-index/observed.stdout).

Positive parent: [run-frozen-pointer](cases/run-frozen-pointer/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-withheld-index', '--output', '/tmp/gp10-checkaudit/results/run-withheld-index'])
```

```text
REJECT record DJ[ forbidden_not_in_force: 0
REJECT run records_rejected
```

### 50. run-cross-check-wrong-verdict

File: [cases/run-cross-check-wrong-verdict/records.jsonl](cases/run-cross-check-wrong-verdict/records.jsonl). Run manifest: [run.json](cases/run-cross-check-wrong-verdict/run.json). Exact saved output: [observed.stdout](cases/run-cross-check-wrong-verdict/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "cross.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-cross-check-wrong-verdict', '--output', '/tmp/gp10-checkaudit/results/run-cross-check-wrong-verdict'])
```

```text
ACCEPT record Cr verified
ACCEPT record F`o~_ verified
ACCEPT record C~ verified
REJECT run cross_check_records
```

### 51. run-conditional-unknown-missing

File: [cases/run-conditional-unknown-missing/records.jsonl](cases/run-conditional-unknown-missing/records.jsonl). Run manifest: [run.json](cases/run-conditional-unknown-missing/run.json). Exact saved output: [observed.stdout](cases/run-conditional-unknown-missing/observed.stdout).

Positive parent: [run-conditional-minimality](cases/run-conditional-minimality/). Mutation: `{"file": "UNKNOWN.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/run-conditional-unknown-missing', '--output', '/tmp/gp10-checkaudit/results/run-conditional-unknown-missing'])
```

```text
ACCEPT record DF{ verified
ACCEPT record DFw verified
REJECT run unknown_exactness
```

### 52. zero-denominator

File: [cases/zero-denominator/records.jsonl](cases/zero-denominator/records.jsonl). Run manifest: [run.json](cases/zero-denominator/run.json). Exact saved output: [observed.stdout](cases/zero-denominator/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/zero-denominator', '--output', '/tmp/gp10-checkaudit/results/zero-denominator'])
```

```text
REJECT record Cr rational: invalid denominator or numerator
REJECT run records_rejected
```

### 53. signed-denominator

File: [cases/signed-denominator/records.jsonl](cases/signed-denominator/records.jsonl). Run manifest: [run.json](cases/signed-denominator/run.json). Exact saved output: [observed.stdout](cases/signed-denominator/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/signed-denominator', '--output', '/tmp/gp10-checkaudit/results/signed-denominator'])
```

```text
REJECT record Cr rational: expected an exact rational string
REJECT run records_rejected
```

### 54. rational-space

File: [cases/rational-space/records.jsonl](cases/rational-space/records.jsonl). Run manifest: [run.json](cases/rational-space/run.json). Exact saved output: [observed.stdout](cases/rational-space/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-space', '--output', '/tmp/gp10-checkaudit/results/rational-space'])
```

```text
REJECT record Cr rational: expected an exact rational string
REJECT run records_rejected
```

### 55. rational-decimal

File: [cases/rational-decimal/records.jsonl](cases/rational-decimal/records.jsonl). Run manifest: [run.json](cases/rational-decimal/run.json). Exact saved output: [observed.stdout](cases/rational-decimal/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-decimal', '--output', '/tmp/gp10-checkaudit/results/rational-decimal'])
```

```text
REJECT record Cr rational: expected an exact rational string
REJECT run records_rejected
```

### 56. rational-float

File: [cases/rational-float/records.jsonl](cases/rational-float/records.jsonl). Run manifest: [run.json](cases/rational-float/run.json). Exact saved output: [observed.stdout](cases/rational-float/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-float', '--output', '/tmp/gp10-checkaudit/results/rational-float'])
```

```text
REJECT record Cr rational: expected an exact rational string
REJECT run records_rejected
```

### 57. rational-bool

File: [cases/rational-bool/records.jsonl](cases/rational-bool/records.jsonl). Run manifest: [run.json](cases/rational-bool/run.json). Exact saved output: [observed.stdout](cases/rational-bool/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-bool', '--output', '/tmp/gp10-checkaudit/results/rational-bool'])
```

```text
REJECT record Cr rational: expected an exact rational string
REJECT run records_rejected
```

### 58. rational-plus

File: [cases/rational-plus/records.jsonl](cases/rational-plus/records.jsonl). Run manifest: [run.json](cases/rational-plus/run.json). Exact saved output: [observed.stdout](cases/rational-plus/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Alternate exact spelling of zero is valid.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-plus', '--output', '/tmp/gp10-checkaudit/results/rational-plus'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 59. rational-plus-red

File: [cases/rational-plus-red/records.jsonl](cases/rational-plus-red/records.jsonl). Run manifest: [run.json](cases/rational-plus-red/run.json). Exact saved output: [observed.stdout](cases/rational-plus-red/observed.stdout).

Positive parent: [rational-plus](cases/rational-plus/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-plus-red', '--output', '/tmp/gp10-checkaudit/results/rational-plus-red'])
```

```text
REJECT record Cr rational: invalid denominator or numerator
REJECT run records_rejected
```

### 60. rational-negative-zero

File: [cases/rational-negative-zero/records.jsonl](cases/rational-negative-zero/records.jsonl). Run manifest: [run.json](cases/rational-negative-zero/run.json). Exact saved output: [observed.stdout](cases/rational-negative-zero/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Alternate exact spelling of zero is valid.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-negative-zero', '--output', '/tmp/gp10-checkaudit/results/rational-negative-zero'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 61. rational-negative-zero-red

File: [cases/rational-negative-zero-red/records.jsonl](cases/rational-negative-zero-red/records.jsonl). Run manifest: [run.json](cases/rational-negative-zero-red/run.json). Exact saved output: [observed.stdout](cases/rational-negative-zero-red/observed.stdout).

Positive parent: [rational-negative-zero](cases/rational-negative-zero/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-negative-zero-red', '--output', '/tmp/gp10-checkaudit/results/rational-negative-zero-red'])
```

```text
REJECT record Cr rational: invalid denominator or numerator
REJECT run records_rejected
```

### 62. rational-leading-zeroes

File: [cases/rational-leading-zeroes/records.jsonl](cases/rational-leading-zeroes/records.jsonl). Run manifest: [run.json](cases/rational-leading-zeroes/run.json). Exact saved output: [observed.stdout](cases/rational-leading-zeroes/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Alternate exact spelling of zero is valid.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-leading-zeroes', '--output', '/tmp/gp10-checkaudit/results/rational-leading-zeroes'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 63. rational-leading-zeroes-red

File: [cases/rational-leading-zeroes-red/records.jsonl](cases/rational-leading-zeroes-red/records.jsonl). Run manifest: [run.json](cases/rational-leading-zeroes-red/run.json). Exact saved output: [observed.stdout](cases/rational-leading-zeroes-red/observed.stdout).

Positive parent: [rational-leading-zeroes](cases/rational-leading-zeroes/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/rational-leading-zeroes-red', '--output', '/tmp/gp10-checkaudit/results/rational-leading-zeroes-red'])
```

```text
REJECT record Cr rational: invalid denominator or numerator
REJECT run records_rejected
```

### 64. minpoly-constant

File: [cases/minpoly-constant/records.jsonl](cases/minpoly-constant/records.jsonl). Run manifest: [run.json](cases/minpoly-constant/run.json). Exact saved output: [observed.stdout](cases/minpoly-constant/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "minpoly"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/minpoly-constant', '--output', '/tmp/gp10-checkaudit/results/minpoly-constant'])
```

```text
REJECT record Cr minpoly: expected positive degree integer polynomial
REJECT run records_rejected
```

### 65. minpoly-zero

File: [cases/minpoly-zero/records.jsonl](cases/minpoly-zero/records.jsonl). Run manifest: [run.json](cases/minpoly-zero/run.json). Exact saved output: [observed.stdout](cases/minpoly-zero/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "minpoly"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/minpoly-zero', '--output', '/tmp/gp10-checkaudit/results/minpoly-zero'])
```

```text
REJECT record Cr minpoly: expected positive degree integer polynomial
REJECT run records_rejected
```

### 66. minpoly-leading-zero

File: [cases/minpoly-leading-zero/records.jsonl](cases/minpoly-leading-zero/records.jsonl). Run manifest: [run.json](cases/minpoly-leading-zero/run.json). Exact saved output: [observed.stdout](cases/minpoly-leading-zero/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "minpoly"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/minpoly-leading-zero', '--output', '/tmp/gp10-checkaudit/results/minpoly-leading-zero'])
```

```text
REJECT record Cr minpoly: expected positive degree integer polynomial
REJECT run records_rejected
```

### 67. minpoly-boolean

File: [cases/minpoly-boolean/records.jsonl](cases/minpoly-boolean/records.jsonl). Run manifest: [run.json](cases/minpoly-boolean/run.json). Exact saved output: [observed.stdout](cases/minpoly-boolean/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "minpoly"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/minpoly-boolean', '--output', '/tmp/gp10-checkaudit/results/minpoly-boolean'])
```

```text
REJECT record Cr minpoly: expected positive degree integer polynomial
REJECT run records_rejected
```

### 68. endpoint-root

File: [cases/endpoint-root/records.jsonl](cases/endpoint-root/records.jsonl). Run manifest: [run.json](cases/endpoint-root/run.json). Exact saved output: [observed.stdout](cases/endpoint-root/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "interval"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/endpoint-root', '--output', '/tmp/gp10-checkaudit/results/endpoint-root'])
```

```text
REJECT record Cr interval_sign_change
REJECT run records_rejected
```

### 69. interval-reversed

File: [cases/interval-reversed/records.jsonl](cases/interval-reversed/records.jsonl). Run manifest: [run.json](cases/interval-reversed/run.json). Exact saved output: [observed.stdout](cases/interval-reversed/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "field", "interval"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/interval-reversed', '--output', '/tmp/gp10-checkaudit/results/interval-reversed'])
```

```text
REJECT record Cr interval_sign_change
REJECT run records_rejected
```

### 70. coordinate-missing-vertex

File: [cases/coordinate-missing-vertex/records.jsonl](cases/coordinate-missing-vertex/records.jsonl). Run manifest: [run.json](cases/coordinate-missing-vertex/run.json). Exact saved output: [observed.stdout](cases/coordinate-missing-vertex/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coordinate-missing-vertex', '--output', '/tmp/gp10-checkaudit/results/coordinate-missing-vertex'])
```

```text
REJECT record Cr coordinate_count
REJECT run records_rejected
```

### 71. coordinate-extra-vertex

File: [cases/coordinate-extra-vertex/records.jsonl](cases/coordinate-extra-vertex/records.jsonl). Run manifest: [run.json](cases/coordinate-extra-vertex/run.json). Exact saved output: [observed.stdout](cases/coordinate-extra-vertex/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coordinate-extra-vertex', '--output', '/tmp/gp10-checkaudit/results/coordinate-extra-vertex'])
```

```text
REJECT record Cr coordinate_count
REJECT run records_rejected
```

### 72. coordinate-not-reduced

File: [cases/coordinate-not-reduced/records.jsonl](cases/coordinate-not-reduced/records.jsonl). Run manifest: [run.json](cases/coordinate-not-reduced/run.json). Exact saved output: [observed.stdout](cases/coordinate-not-reduced/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coordinate-not-reduced', '--output', '/tmp/gp10-checkaudit/results/coordinate-not-reduced'])
```

```text
REJECT record Cr coordinate_degree
REJECT run records_rejected
```

### 73. coordinate-not-pair

File: [cases/coordinate-not-pair/records.jsonl](cases/coordinate-not-pair/records.jsonl). Run manifest: [run.json](cases/coordinate-not-pair/run.json). Exact saved output: [observed.stdout](cases/coordinate-not-pair/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coordinate-not-pair', '--output', '/tmp/gp10-checkaudit/results/coordinate-not-pair'])
```

```text
REJECT record Cr coordinate_shape
REJECT run records_rejected
```

### 74. coordinate-wrong-labels

File: [cases/coordinate-wrong-labels/records.jsonl](cases/coordinate-wrong-labels/records.jsonl). Run manifest: [run.json](cases/coordinate-wrong-labels/run.json). Exact saved output: [observed.stdout](cases/coordinate-wrong-labels/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coordinate-wrong-labels', '--output', '/tmp/gp10-checkaudit/results/coordinate-wrong-labels'])
```

```text
REJECT record Cr edge_equation: (0, 1)
REJECT run records_rejected
```

### 75. large-rational

File: [cases/large-rational/records.jsonl](cases/large-rational/records.jsonl). Run manifest: [run.json](cases/large-rational/run.json). Exact saved output: [observed.stdout](cases/large-rational/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/large-rational', '--output', '/tmp/gp10-checkaudit/results/large-rational'])
```

```text
ACCEPT record A? verified
ACCEPT run verified
```

### 76. large-rational-collision

File: [cases/large-rational-collision/records.jsonl](cases/large-rational-collision/records.jsonl). Run manifest: [run.json](cases/large-rational-collision/run.json). Exact saved output: [observed.stdout](cases/large-rational-collision/observed.stdout).

Positive parent: [large-rational](cases/large-rational/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 1, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/large-rational-collision', '--output', '/tmp/gp10-checkaudit/results/large-rational-collision'])
```

```text
REJECT record A? exact_collision: (0, 1)
REJECT run records_rejected
```

### 77. multiple-roots

File: [cases/multiple-roots/records.jsonl](cases/multiple-roots/records.jsonl). Run manifest: [run.json](cases/multiple-roots/run.json). Exact saved output: [observed.stdout](cases/multiple-roots/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Sign change and common certified distinctness suffice; irreducibility and root uniqueness are not required.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/multiple-roots', '--output', '/tmp/gp10-checkaudit/results/multiple-roots'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 78. multiple-roots-collision

File: [cases/multiple-roots-collision/records.jsonl](cases/multiple-roots-collision/records.jsonl). Run manifest: [run.json](cases/multiple-roots-collision/run.json). Exact saved output: [observed.stdout](cases/multiple-roots-collision/observed.stdout).

Positive parent: [multiple-roots](cases/multiple-roots/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 3], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/multiple-roots-collision', '--output', '/tmp/gp10-checkaudit/results/multiple-roots-collision'])
```

```text
REJECT record Cr exact_collision: (0, 3)
REJECT run records_rejected
```

### 79. repeated-root-odd

File: [cases/repeated-root-odd/records.jsonl](cases/repeated-root-odd/records.jsonl). Run manifest: [run.json](cases/repeated-root-odd/run.json). Exact saved output: [observed.stdout](cases/repeated-root-odd/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Sign change and common certified distinctness suffice; irreducibility and root uniqueness are not required.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/repeated-root-odd', '--output', '/tmp/gp10-checkaudit/results/repeated-root-odd'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 80. repeated-root-odd-collision

File: [cases/repeated-root-odd-collision/records.jsonl](cases/repeated-root-odd-collision/records.jsonl). Run manifest: [run.json](cases/repeated-root-odd-collision/run.json). Exact saved output: [observed.stdout](cases/repeated-root-odd-collision/observed.stdout).

Positive parent: [repeated-root-odd](cases/repeated-root-odd/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 3], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/repeated-root-odd-collision', '--output', '/tmp/gp10-checkaudit/results/repeated-root-odd-collision'])
```

```text
REJECT record Cr exact_collision: (0, 3)
REJECT run records_rejected
```

### 81. repeated-root-mixed

File: [cases/repeated-root-mixed/records.jsonl](cases/repeated-root-mixed/records.jsonl). Run manifest: [run.json](cases/repeated-root-mixed/run.json). Exact saved output: [observed.stdout](cases/repeated-root-mixed/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Sign change and common certified distinctness suffice; irreducibility and root uniqueness are not required.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/repeated-root-mixed', '--output', '/tmp/gp10-checkaudit/results/repeated-root-mixed'])
```

```text
ACCEPT record Cr verified
ACCEPT run verified
```

### 82. repeated-root-mixed-collision

File: [cases/repeated-root-mixed-collision/records.jsonl](cases/repeated-root-mixed-collision/records.jsonl). Run manifest: [run.json](cases/repeated-root-mixed-collision/run.json). Exact saved output: [observed.stdout](cases/repeated-root-mixed-collision/observed.stdout).

Positive parent: [repeated-root-mixed](cases/repeated-root-mixed/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 3], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/repeated-root-mixed-collision', '--output', '/tmp/gp10-checkaudit/results/repeated-root-mixed-collision'])
```

```text
REJECT record Cr exact_collision: (0, 3)
REJECT run records_rejected
```

### 83. shared-root

File: [cases/shared-root/records.jsonl](cases/shared-root/records.jsonl). Run manifest: [run.json](cases/shared-root/run.json). Exact saved output: [observed.stdout](cases/shared-root/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/shared-root', '--output', '/tmp/gp10-checkaudit/results/shared-root'])
```

```text
ACCEPT record C? verified
ACCEPT run verified
```

### 84. shared-root-trap

File: [cases/shared-root-trap/records.jsonl](cases/shared-root-trap/records.jsonl). Run manifest: [run.json](cases/shared-root-trap/run.json). Exact saved output: [observed.stdout](cases/shared-root-trap/observed.stdout).

Positive parent: [shared-root](cases/shared-root/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/shared-root-trap', '--output', '/tmp/gp10-checkaudit/results/shared-root-trap'])
```

```text
REJECT record C? exact_collision: (0, 2)
REJECT run records_rejected
```

### 85. interval-refinement

File: [cases/interval-refinement/records.jsonl](cases/interval-refinement/records.jsonl). Run manifest: [run.json](cases/interval-refinement/run.json). Exact saved output: [observed.stdout](cases/interval-refinement/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/interval-refinement', '--output', '/tmp/gp10-checkaudit/results/interval-refinement'])
```

```text
ACCEPT record A? verified
ACCEPT run verified
```

### 86. interval-refinement-red

File: [cases/interval-refinement-red/records.jsonl](cases/interval-refinement-red/records.jsonl). Run manifest: [run.json](cases/interval-refinement-red/run.json). Exact saved output: [observed.stdout](cases/interval-refinement-red/observed.stdout).

Positive parent: [interval-refinement](cases/interval-refinement/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 1, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/interval-refinement-red', '--output', '/tmp/gp10-checkaudit/results/interval-refinement-red'])
```

```text
REJECT record A? exact_collision: (0, 1)
REJECT run records_rejected
```

### 87. embed-K4

File: [cases/embed-K4/records.jsonl](cases/embed-K4/records.jsonl). Run manifest: [run.json](cases/embed-K4/run.json). Exact saved output: [observed.stdout](cases/embed-K4/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-K4', '--output', '/tmp/gp10-checkaudit/results/embed-K4'])
```

```text
REJECT record C~ edge_equation: (0, 3)
REJECT run records_rejected
```

### 88. edgeless-4

File: [cases/edgeless-4/records.jsonl](cases/edgeless-4/records.jsonl). Run manifest: [run.json](cases/edgeless-4/run.json). Exact saved output: [observed.stdout](cases/edgeless-4/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-4', '--output', '/tmp/gp10-checkaudit/results/edgeless-4'])
```

```text
ACCEPT record C? verified
ACCEPT run verified
```

### 89. edgeless-5

File: [cases/edgeless-5/records.jsonl](cases/edgeless-5/records.jsonl). Run manifest: [run.json](cases/edgeless-5/run.json). Exact saved output: [observed.stdout](cases/edgeless-5/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-5', '--output', '/tmp/gp10-checkaudit/results/edgeless-5'])
```

```text
ACCEPT record D?? verified
ACCEPT run verified
```

### 90. edgeless-6

File: [cases/edgeless-6/records.jsonl](cases/edgeless-6/records.jsonl). Run manifest: [run.json](cases/edgeless-6/run.json). Exact saved output: [observed.stdout](cases/edgeless-6/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-6', '--output', '/tmp/gp10-checkaudit/results/edgeless-6'])
```

```text
ACCEPT record E??? verified
ACCEPT run verified
```

### 91. edgeless-7

File: [cases/edgeless-7/records.jsonl](cases/edgeless-7/records.jsonl). Run manifest: [run.json](cases/edgeless-7/run.json). Exact saved output: [observed.stdout](cases/edgeless-7/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-7', '--output', '/tmp/gp10-checkaudit/results/edgeless-7'])
```

```text
ACCEPT record F???? verified
ACCEPT run verified
```

### 92. edgeless-8

File: [cases/edgeless-8/records.jsonl](cases/edgeless-8/records.jsonl). Run manifest: [run.json](cases/edgeless-8/run.json). Exact saved output: [observed.stdout](cases/edgeless-8/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-8', '--output', '/tmp/gp10-checkaudit/results/edgeless-8'])
```

```text
ACCEPT record G????? verified
ACCEPT run verified
```

### 93. edgeless-9

File: [cases/edgeless-9/records.jsonl](cases/edgeless-9/records.jsonl). Run manifest: [run.json](cases/edgeless-9/run.json). Exact saved output: [observed.stdout](cases/edgeless-9/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/edgeless-9', '--output', '/tmp/gp10-checkaudit/results/edgeless-9'])
```

```text
ACCEPT record H?????? verified
ACCEPT run verified
```

### 94. embed-forbidden-00

File: [cases/embed-forbidden-00/records.jsonl](cases/embed-forbidden-00/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-00/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-00/observed.stdout).

Positive parent: [edgeless-4](cases/edgeless-4/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-00', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-00'])
```

```text
REJECT record C~ edge_equation: (0, 2)
REJECT run records_rejected
```

### 95. embed-forbidden-01

File: [cases/embed-forbidden-01/records.jsonl](cases/embed-forbidden-01/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-01/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-01/observed.stdout).

Positive parent: [edgeless-5](cases/edgeless-5/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-01', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-01'])
```

```text
REJECT record DFw edge_equation: (0, 3)
REJECT run records_rejected
```

### 96. embed-forbidden-02

File: [cases/embed-forbidden-02/records.jsonl](cases/embed-forbidden-02/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-02/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-02/observed.stdout).

Positive parent: [edgeless-6](cases/edgeless-6/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-02', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-02'])
```

```text
REJECT record EqLw edge_equation: (0, 2)
REJECT run records_rejected
```

### 97. embed-forbidden-03

File: [cases/embed-forbidden-03/records.jsonl](cases/embed-forbidden-03/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-03/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-03/observed.stdout).

Positive parent: [edgeless-7](cases/edgeless-7/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-03', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-03'])
```

```text
REJECT record F@h^_ edge_equation: (0, 4)
REJECT run records_rejected
```

### 98. embed-forbidden-04

File: [cases/embed-forbidden-04/records.jsonl](cases/embed-forbidden-04/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-04/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-04/observed.stdout).

Positive parent: [edgeless-7](cases/edgeless-7/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-04', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-04'])
```

```text
REJECT record FqHXw edge_equation: (0, 2)
REJECT run records_rejected
```

### 99. embed-forbidden-05

File: [cases/embed-forbidden-05/records.jsonl](cases/embed-forbidden-05/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-05/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-05/observed.stdout).

Positive parent: [edgeless-7](cases/edgeless-7/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-05', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-05'])
```

```text
REJECT record FoS~_ edge_equation: (0, 2)
REJECT run records_rejected
```

### 100. embed-forbidden-06

File: [cases/embed-forbidden-06/records.jsonl](cases/embed-forbidden-06/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-06/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-06/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-06', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-06'])
```

```text
REJECT record G?K]Nc edge_equation: (0, 6)
REJECT run records_rejected
```

### 101. embed-forbidden-07

File: [cases/embed-forbidden-07/records.jsonl](cases/embed-forbidden-07/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-07/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-07/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-07', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-07'])
```

```text
REJECT record Gp@Gzo edge_equation: (0, 2)
REJECT run records_rejected
```

### 102. embed-forbidden-08

File: [cases/embed-forbidden-08/records.jsonl](cases/embed-forbidden-08/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-08/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-08/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-08', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-08'])
```

```text
REJECT record GsOiho edge_equation: (0, 2)
REJECT run records_rejected
```

### 103. embed-forbidden-09

File: [cases/embed-forbidden-09/records.jsonl](cases/embed-forbidden-09/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-09/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-09/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-09', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-09'])
```

```text
REJECT record G@fBJs edge_equation: (0, 4)
REJECT run records_rejected
```

### 104. embed-forbidden-10

File: [cases/embed-forbidden-10/records.jsonl](cases/embed-forbidden-10/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-10/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-10/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-10', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-10'])
```

```text
REJECT record GqHPW{ edge_equation: (0, 2)
REJECT run records_rejected
```

### 105. embed-forbidden-11

File: [cases/embed-forbidden-11/records.jsonl](cases/embed-forbidden-11/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-11/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-11/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-11', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-11'])
```

```text
REJECT record G@IQV{ edge_equation: (0, 5)
REJECT run records_rejected
```

### 106. embed-forbidden-12

File: [cases/embed-forbidden-12/records.jsonl](cases/embed-forbidden-12/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-12/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-12/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-12', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-12'])
```

```text
REJECT record GHCML{ edge_equation: (0, 6)
REJECT run records_rejected
```

### 107. embed-forbidden-13

File: [cases/embed-forbidden-13/records.jsonl](cases/embed-forbidden-13/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-13/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-13/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-13', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-13'])
```

```text
REJECT record G?Nebs edge_equation: (0, 5)
REJECT run records_rejected
```

### 108. embed-forbidden-14

File: [cases/embed-forbidden-14/records.jsonl](cases/embed-forbidden-14/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-14/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-14/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-14', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-14'])
```

```text
REJECT record GAJcrs edge_equation: (0, 5)
REJECT run records_rejected
```

### 109. embed-forbidden-15

File: [cases/embed-forbidden-15/records.jsonl](cases/embed-forbidden-15/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-15/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-15/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-15', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-15'])
```

```text
REJECT record GdhAXk edge_equation: (0, 3)
REJECT run records_rejected
```

### 110. embed-forbidden-16

File: [cases/embed-forbidden-16/records.jsonl](cases/embed-forbidden-16/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-16/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-16/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-16', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-16'])
```

```text
REJECT record G[dBG{ edge_equation: (0, 2)
REJECT run records_rejected
```

### 111. embed-forbidden-17

File: [cases/embed-forbidden-17/records.jsonl](cases/embed-forbidden-17/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-17/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-17/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-17', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-17'])
```

```text
REJECT record Gm__x[ edge_equation: (0, 3)
REJECT run records_rejected
```

### 112. embed-forbidden-18

File: [cases/embed-forbidden-18/records.jsonl](cases/embed-forbidden-18/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-18/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-18/observed.stdout).

Positive parent: [edgeless-8](cases/edgeless-8/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-18', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-18'])
```

```text
REJECT record GqGTYw edge_equation: (0, 2)
REJECT run records_rejected
```

### 113. embed-forbidden-19

File: [cases/embed-forbidden-19/records.jsonl](cases/embed-forbidden-19/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-19/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-19/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-19', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-19'])
```

```text
REJECT record H?GXmRo edge_equation: (0, 7)
REJECT run records_rejected
```

### 114. embed-forbidden-20

File: [cases/embed-forbidden-20/records.jsonl](cases/embed-forbidden-20/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-20/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-20/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-20', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-20'])
```

```text
REJECT record H??|Qro edge_equation: (0, 6)
REJECT run records_rejected
```

### 115. embed-forbidden-21

File: [cases/embed-forbidden-21/records.jsonl](cases/embed-forbidden-21/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-21/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-21/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-21', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-21'])
```

```text
REJECT record HIGCkX{ edge_equation: (0, 6)
REJECT run records_rejected
```

### 116. embed-forbidden-22

File: [cases/embed-forbidden-22/records.jsonl](cases/embed-forbidden-22/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-22/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-22/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-22', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-22'])
```

```text
REJECT record H_hP`SV edge_equation: (0, 4)
REJECT run records_rejected
```

### 117. embed-forbidden-23

File: [cases/embed-forbidden-23/records.jsonl](cases/embed-forbidden-23/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-23/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-23/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-23', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-23'])
```

```text
REJECT record HCO_W~q edge_equation: (0, 3)
REJECT run records_rejected
```

### 118. embed-forbidden-24

File: [cases/embed-forbidden-24/records.jsonl](cases/embed-forbidden-24/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-24/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-24/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-24', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-24'])
```

```text
REJECT record HgCXSLp edge_equation: (0, 7)
REJECT run records_rejected
```

### 119. embed-forbidden-25

File: [cases/embed-forbidden-25/records.jsonl](cases/embed-forbidden-25/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-25/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-25/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-25', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-25'])
```

```text
REJECT record HAJ?Xfw edge_equation: (0, 5)
REJECT run records_rejected
```

### 120. embed-forbidden-26

File: [cases/embed-forbidden-26/records.jsonl](cases/embed-forbidden-26/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-26/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-26/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-26', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-26'])
```

```text
REJECT record HqL@?[V edge_equation: (0, 2)
REJECT run records_rejected
```

### 121. embed-forbidden-27

File: [cases/embed-forbidden-27/records.jsonl](cases/embed-forbidden-27/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-27/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-27/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-27', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-27'])
```

```text
REJECT record H?XPdeM edge_equation: (0, 7)
REJECT run records_rejected
```

### 122. embed-forbidden-28

File: [cases/embed-forbidden-28/records.jsonl](cases/embed-forbidden-28/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-28/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-28/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-28', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-28'])
```

```text
REJECT record H@EPQ^a edge_equation: (0, 5)
REJECT run records_rejected
```

### 123. embed-forbidden-29

File: [cases/embed-forbidden-29/records.jsonl](cases/embed-forbidden-29/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-29/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-29/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-29', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-29'])
```

```text
REJECT record Ho?gqd{ edge_equation: (0, 2)
REJECT run records_rejected
```

### 124. embed-forbidden-30

File: [cases/embed-forbidden-30/records.jsonl](cases/embed-forbidden-30/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-30/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-30/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-30', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-30'])
```

```text
REJECT record HoO_ol{ edge_equation: (0, 2)
REJECT run records_rejected
```

### 125. embed-forbidden-31

File: [cases/embed-forbidden-31/records.jsonl](cases/embed-forbidden-31/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-31/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-31/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-31', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-31'])
```

```text
REJECT record HAGW}Ed edge_equation: (0, 7)
REJECT run records_rejected
```

### 126. embed-forbidden-32

File: [cases/embed-forbidden-32/records.jsonl](cases/embed-forbidden-32/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-32/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-32/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-32', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-32'])
```

```text
REJECT record HoCYPLp edge_equation: (0, 2)
REJECT run records_rejected
```

### 127. embed-forbidden-33

File: [cases/embed-forbidden-33/records.jsonl](cases/embed-forbidden-33/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-33/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-33/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-33', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-33'])
```

```text
REJECT record H_SsPNo edge_equation: (0, 6)
REJECT run records_rejected
```

### 128. embed-forbidden-34

File: [cases/embed-forbidden-34/records.jsonl](cases/embed-forbidden-34/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-34/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-34/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-34', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-34'])
```

```text
REJECT record H?hPaue edge_equation: (0, 4)
REJECT run records_rejected
```

### 129. embed-forbidden-35

File: [cases/embed-forbidden-35/records.jsonl](cases/embed-forbidden-35/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-35/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-35/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-35', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-35'])
```

```text
REJECT record HoCy@TR edge_equation: (0, 2)
REJECT run records_rejected
```

### 130. embed-forbidden-36

File: [cases/embed-forbidden-36/records.jsonl](cases/embed-forbidden-36/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-36/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-36/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-36', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-36'])
```

```text
REJECT record HIA@Wzw edge_equation: (0, 5)
REJECT run records_rejected
```

### 131. embed-forbidden-37

File: [cases/embed-forbidden-37/records.jsonl](cases/embed-forbidden-37/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-37/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-37/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-37', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-37'])
```

```text
REJECT record H_hOpNo edge_equation: (0, 4)
REJECT run records_rejected
```

### 132. embed-forbidden-38

File: [cases/embed-forbidden-38/records.jsonl](cases/embed-forbidden-38/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-38/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-38/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-38', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-38'])
```

```text
REJECT record H?dPdLi edge_equation: (0, 4)
REJECT run records_rejected
```

### 133. embed-forbidden-39

File: [cases/embed-forbidden-39/records.jsonl](cases/embed-forbidden-39/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-39/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-39/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-39', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-39'])
```

```text
REJECT record HGEAXjw edge_equation: (0, 5)
REJECT run records_rejected
```

### 134. embed-forbidden-40

File: [cases/embed-forbidden-40/records.jsonl](cases/embed-forbidden-40/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-40/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-40/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-40', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-40'])
```

```text
REJECT record Ho@PQwz edge_equation: (0, 2)
REJECT run records_rejected
```

### 135. embed-forbidden-41

File: [cases/embed-forbidden-41/records.jsonl](cases/embed-forbidden-41/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-41/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-41/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-41', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-41'])
```

```text
REJECT record H?iRQhr edge_equation: (0, 4)
REJECT run records_rejected
```

### 136. embed-forbidden-42

File: [cases/embed-forbidden-42/records.jsonl](cases/embed-forbidden-42/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-42/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-42/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-42', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-42'])
```

```text
REJECT record Hh_EhW\ edge_equation: (0, 4)
REJECT run records_rejected
```

### 137. embed-forbidden-43

File: [cases/embed-forbidden-43/records.jsonl](cases/embed-forbidden-43/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-43/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-43/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-43', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-43'])
```

```text
REJECT record HSD_YVp edge_equation: (0, 2)
REJECT run records_rejected
```

### 138. embed-forbidden-44

File: [cases/embed-forbidden-44/records.jsonl](cases/embed-forbidden-44/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-44/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-44/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-44', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-44'])
```

```text
REJECT record HH_KiXr edge_equation: (0, 4)
REJECT run records_rejected
```

### 139. embed-forbidden-45

File: [cases/embed-forbidden-45/records.jsonl](cases/embed-forbidden-45/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-45/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-45/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-45', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-45'])
```

```text
REJECT record H_KQ\Jp edge_equation: (0, 7)
REJECT run records_rejected
```

### 140. embed-forbidden-46

File: [cases/embed-forbidden-46/records.jsonl](cases/embed-forbidden-46/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-46/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-46/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-46', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-46'])
```

```text
REJECT record H`QBWyp edge_equation: (0, 5)
REJECT run records_rejected
```

### 141. embed-forbidden-47

File: [cases/embed-forbidden-47/records.jsonl](cases/embed-forbidden-47/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-47/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-47/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-47', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-47'])
```

```text
REJECT record HkCeHoN edge_equation: (0, 3)
REJECT run records_rejected
```

### 142. embed-forbidden-48

File: [cases/embed-forbidden-48/records.jsonl](cases/embed-forbidden-48/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-48/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-48/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-48', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-48'])
```

```text
REJECT record H?HVCp| edge_equation: (0, 6)
REJECT run records_rejected
```

### 143. embed-forbidden-49

File: [cases/embed-forbidden-49/records.jsonl](cases/embed-forbidden-49/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-49/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-49/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-49', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-49'])
```

```text
REJECT record H@EMBD| edge_equation: (0, 5)
REJECT run records_rejected
```

### 144. embed-forbidden-50

File: [cases/embed-forbidden-50/records.jsonl](cases/embed-forbidden-50/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-50/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-50/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-50', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-50'])
```

```text
REJECT record HH`K_\r edge_equation: (0, 4)
REJECT run records_rejected
```

### 145. embed-forbidden-51

File: [cases/embed-forbidden-51/records.jsonl](cases/embed-forbidden-51/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-51/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-51/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-51', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-51'])
```

```text
REJECT record H@CNEK| edge_equation: (0, 6)
REJECT run records_rejected
```

### 146. embed-forbidden-52

File: [cases/embed-forbidden-52/records.jsonl](cases/embed-forbidden-52/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-52/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-52/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-52', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-52'])
```

```text
REJECT record H@_maXr edge_equation: (0, 4)
REJECT run records_rejected
```

### 147. embed-forbidden-53

File: [cases/embed-forbidden-53/records.jsonl](cases/embed-forbidden-53/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-53/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-53/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-53', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-53'])
```

```text
REJECT record HG_\aXr edge_equation: (0, 4)
REJECT run records_rejected
```

### 148. embed-forbidden-54

File: [cases/embed-forbidden-54/records.jsonl](cases/embed-forbidden-54/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-54/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-54/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-54', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-54'])
```

```text
REJECT record HGaqOtr edge_equation: (0, 4)
REJECT run records_rejected
```

### 149. embed-forbidden-55

File: [cases/embed-forbidden-55/records.jsonl](cases/embed-forbidden-55/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-55/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-55/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-55', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-55'])
```

```text
REJECT record HHEAG^x edge_equation: (0, 5)
REJECT run records_rejected
```

### 150. embed-forbidden-56

File: [cases/embed-forbidden-56/records.jsonl](cases/embed-forbidden-56/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-56/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-56/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-56', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-56'])
```

```text
REJECT record Hm__XKZ edge_equation: (0, 3)
REJECT run records_rejected
```

### 151. embed-forbidden-57

File: [cases/embed-forbidden-57/records.jsonl](cases/embed-forbidden-57/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-57/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-57/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-57', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-57'])
```

```text
REJECT record HOOo}Rp edge_equation: (0, 2)
REJECT run records_rejected
```

### 152. embed-forbidden-58

File: [cases/embed-forbidden-58/records.jsonl](cases/embed-forbidden-58/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-58/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-58/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-58', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-58'])
```

```text
REJECT record Hg?X[rp edge_equation: (0, 7)
REJECT run records_rejected
```

### 153. embed-forbidden-59

File: [cases/embed-forbidden-59/records.jsonl](cases/embed-forbidden-59/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-59/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-59/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-59', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-59'])
```

```text
REJECT record H`?NeW{ edge_equation: (0, 6)
REJECT run records_rejected
```

### 154. embed-forbidden-60

File: [cases/embed-forbidden-60/records.jsonl](cases/embed-forbidden-60/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-60/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-60/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-60', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-60'])
```

```text
REJECT record HqGRSgN edge_equation: (0, 2)
REJECT run records_rejected
```

### 155. embed-forbidden-61

File: [cases/embed-forbidden-61/records.jsonl](cases/embed-forbidden-61/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-61/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-61/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-61', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-61'])
```

```text
REJECT record Hp?Gi^w edge_equation: (0, 2)
REJECT run records_rejected
```

### 156. embed-forbidden-62

File: [cases/embed-forbidden-62/records.jsonl](cases/embed-forbidden-62/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-62/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-62/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-62', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-62'])
```

```text
REJECT record Hr?MPgN edge_equation: (0, 2)
REJECT run records_rejected
```

### 157. embed-forbidden-63

File: [cases/embed-forbidden-63/records.jsonl](cases/embed-forbidden-63/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-63/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-63/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-63', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-63'])
```

```text
REJECT record Hr_@iWN edge_equation: (0, 2)
REJECT run records_rejected
```

### 158. embed-forbidden-64

File: [cases/embed-forbidden-64/records.jsonl](cases/embed-forbidden-64/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-64/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-64/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-64', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-64'])
```

```text
REJECT record HkCe`WN edge_equation: (0, 3)
REJECT run records_rejected
```

### 159. embed-forbidden-65

File: [cases/embed-forbidden-65/records.jsonl](cases/embed-forbidden-65/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-65/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-65/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-65', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-65'])
```

```text
REJECT record HqGEhW\ edge_equation: (0, 2)
REJECT run records_rejected
```

### 160. embed-forbidden-66

File: [cases/embed-forbidden-66/records.jsonl](cases/embed-forbidden-66/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-66/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-66/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-66', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-66'])
```

```text
REJECT record H{O_okN edge_equation: (0, 2)
REJECT run records_rejected
```

### 161. embed-forbidden-67

File: [cases/embed-forbidden-67/records.jsonl](cases/embed-forbidden-67/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-67/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-67/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-67', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-67'])
```

```text
REJECT record Hp`@iWZ edge_equation: (0, 2)
REJECT run records_rejected
```

### 162. embed-forbidden-68

File: [cases/embed-forbidden-68/records.jsonl](cases/embed-forbidden-68/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-68/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-68/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-68', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-68'])
```

```text
REJECT record H`QBpiL edge_equation: (0, 5)
REJECT run records_rejected
```

### 163. embed-forbidden-69

File: [cases/embed-forbidden-69/records.jsonl](cases/embed-forbidden-69/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-69/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-69/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-69', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-69'])
```

```text
REJECT record H_CfKxw edge_equation: (0, 6)
REJECT run records_rejected
```

### 164. embed-forbidden-70

File: [cases/embed-forbidden-70/records.jsonl](cases/embed-forbidden-70/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-70/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-70/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-70', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-70'])
```

```text
REJECT record HpO]@cN edge_equation: (0, 2)
REJECT run records_rejected
```

### 165. embed-forbidden-71

File: [cases/embed-forbidden-71/records.jsonl](cases/embed-forbidden-71/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-71/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-71/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-71', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-71'])
```

```text
REJECT record HQ`F_wl edge_equation: (0, 2)
REJECT run records_rejected
```

### 166. embed-forbidden-72

File: [cases/embed-forbidden-72/records.jsonl](cases/embed-forbidden-72/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-72/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-72/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-72', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-72'])
```

```text
REJECT record Hr`?XKZ edge_equation: (0, 2)
REJECT run records_rejected
```

### 167. embed-forbidden-73

File: [cases/embed-forbidden-73/records.jsonl](cases/embed-forbidden-73/records.jsonl). Run manifest: [run.json](cases/embed-forbidden-73/run.json). Exact saved output: [observed.stdout](cases/embed-forbidden-73/observed.stdout).

Positive parent: [edgeless-9](cases/edgeless-9/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/embed-forbidden-73', '--output', '/tmp/gp10-checkaudit/results/embed-forbidden-73'])
```

```text
REJECT record H``Axih edge_equation: (0, 4)
REJECT run records_rejected
```

### 168. tree-k4-isolates-4

File: [cases/tree-k4-isolates-4/records.jsonl](cases/tree-k4-isolates-4/records.jsonl). Run manifest: [run.json](cases/tree-k4-isolates-4/run.json). Exact saved output: [observed.stdout](cases/tree-k4-isolates-4/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-k4-isolates-4', '--output', '/tmp/gp10-checkaudit/results/tree-k4-isolates-4'])
```

```text
ACCEPT record C~ verified
ACCEPT run verified
```

### 169. tree-k4-isolates-7

File: [cases/tree-k4-isolates-7/records.jsonl](cases/tree-k4-isolates-7/records.jsonl). Run manifest: [run.json](cases/tree-k4-isolates-7/run.json). Exact saved output: [observed.stdout](cases/tree-k4-isolates-7/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-k4-isolates-7', '--output', '/tmp/gp10-checkaudit/results/tree-k4-isolates-7'])
```

```text
ACCEPT record F?CWw verified
ACCEPT run verified
```

### 170. tree-k4-isolates-10

File: [cases/tree-k4-isolates-10/records.jsonl](cases/tree-k4-isolates-10/records.jsonl). Run manifest: [run.json](cases/tree-k4-isolates-10/run.json). Exact saved output: [observed.stdout](cases/tree-k4-isolates-10/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-k4-isolates-10', '--output', '/tmp/gp10-checkaudit/results/tree-k4-isolates-10'])
```

```text
ACCEPT record I????CB?w verified
ACCEPT run verified
```

### 171. refute-UDG-C4

File: [cases/refute-UDG-C4/records.jsonl](cases/refute-UDG-C4/records.jsonl). Run manifest: [run.json](cases/refute-UDG-C4/run.json). Exact saved output: [observed.stdout](cases/refute-UDG-C4/observed.stdout).

Positive parent: [tree-k4-isolates-4](cases/tree-k4-isolates-4/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refute-UDG-C4', '--output', '/tmp/gp10-checkaudit/results/refute-UDG-C4'])
```

```text
REJECT record Cr tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 172. refute-UDG-Moser

File: [cases/refute-UDG-Moser/records.jsonl](cases/refute-UDG-Moser/records.jsonl). Run manifest: [run.json](cases/refute-UDG-Moser/run.json). Exact saved output: [observed.stdout](cases/refute-UDG-Moser/observed.stdout).

Positive parent: [tree-k4-isolates-7](cases/tree-k4-isolates-7/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refute-UDG-Moser', '--output', '/tmp/gp10-checkaudit/results/refute-UDG-Moser'])
```

```text
REJECT record F`o~_ tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 173. refute-UDG-Petersen

File: [cases/refute-UDG-Petersen/records.jsonl](cases/refute-UDG-Petersen/records.jsonl). Run manifest: [run.json](cases/refute-UDG-Petersen/run.json). Exact saved output: [observed.stdout](cases/refute-UDG-Petersen/observed.stdout).

Positive parent: [tree-k4-isolates-10](cases/tree-k4-isolates-10/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refute-UDG-Petersen', '--output', '/tmp/gp10-checkaudit/results/refute-UDG-Petersen'])
```

```text
REJECT record IsP@OkWHG tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 174. refute-UDG-pentagonal_prism

File: [cases/refute-UDG-pentagonal_prism/records.jsonl](cases/refute-UDG-pentagonal_prism/records.jsonl). Run manifest: [run.json](cases/refute-UDG-pentagonal_prism/run.json). Exact saved output: [observed.stdout](cases/refute-UDG-pentagonal_prism/observed.stdout).

Positive parent: [tree-k4-isolates-10](cases/tree-k4-isolates-10/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refute-UDG-pentagonal_prism', '--output', '/tmp/gp10-checkaudit/results/refute-UDG-pentagonal_prism'])
```

```text
REJECT record Is?HGtcU? tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 175. refute-UDG-extremal

File: [cases/refute-UDG-extremal/records.jsonl](cases/refute-UDG-extremal/records.jsonl). Run manifest: [run.json](cases/refute-UDG-extremal/run.json). Exact saved output: [observed.stdout](cases/refute-UDG-extremal/observed.stdout).

Positive parent: [tree-k4-isolates-10](cases/tree-k4-isolates-10/). Mutation: `{"file": "records.jsonl", "path": ["g6"], "scope": "record"}`.

Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refute-UDG-extremal', '--output', '/tmp/gp10-checkaudit/results/refute-UDG-extremal'])
```

```text
REJECT record IISpZATaw tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 176. tree-root-edges

File: [cases/tree-root-edges/records.jsonl](cases/tree-root-edges/records.jsonl). Run manifest: [run.json](cases/tree-root-edges/run.json). Exact saved output: [observed.stdout](cases/tree-root-edges/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "edges"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-root-edges', '--output', '/tmp/gp10-checkaudit/results/tree-root-edges'])
```

```text
REJECT record C~ tree: R-tree.tree.edges: inconsistent with the parent move
REJECT run records_rejected
```

### 177. tree-root-rowspace

File: [cases/tree-root-rowspace/records.jsonl](cases/tree-root-rowspace/records.jsonl). Run manifest: [run.json](cases/tree-root-rowspace/run.json). Exact saved output: [observed.stdout](cases/tree-root-rowspace/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "A"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-root-rowspace', '--output', '/tmp/gp10-checkaudit/results/tree-root-rowspace'])
```

```text
REJECT record C~ tree: R-tree.tree.A: row space is inconsistent with the claimed constraints
REJECT run records_rejected
```

### 178. tree-reducible-field

File: [cases/tree-reducible-field/records.jsonl](cases/tree-reducible-field/records.jsonl). Run manifest: [run.json](cases/tree-reducible-field/run.json). Exact saved output: [observed.stdout](cases/tree-reducible-field/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "field", "minpoly"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-reducible-field', '--output', '/tmp/gp10-checkaudit/results/tree-reducible-field'])
```

```text
REJECT record C~ tree: R-tree.field.minpoly: polynomial is reducible over Q
REJECT run records_rejected
```

### 179. tree-endpoint-root

File: [cases/tree-endpoint-root/records.jsonl](cases/tree-endpoint-root/records.jsonl). Run manifest: [run.json](cases/tree-endpoint-root/run.json). Exact saved output: [observed.stdout](cases/tree-endpoint-root/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "field", "interval"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-endpoint-root', '--output', '/tmp/gp10-checkaudit/results/tree-endpoint-root'])
```

```text
REJECT record C~ tree: isolating interval endpoint is a root
REJECT run records_rejected
```

### 180. tree-leaf-children

File: [cases/tree-leaf-children/records.jsonl](cases/tree-leaf-children/records.jsonl). Run manifest: [run.json](cases/tree-leaf-children/run.json). Exact saved output: [observed.stdout](cases/tree-leaf-children/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "children"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-leaf-children', '--output', '/tmp/gp10-checkaudit/results/tree-leaf-children'])
```

```text
REJECT record C~ tree: R-tree.tree: L1a contradiction must be a leaf
REJECT run records_rejected
```

### 181. tree-forged-move

File: [cases/tree-forged-move/records.jsonl](cases/tree-forged-move/records.jsonl). Run manifest: [run.json](cases/tree-forged-move/run.json). Exact saved output: [observed.stdout](cases/tree-forged-move/observed.stdout).

Positive parent: [existing-k4-tree](cases/existing-k4-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "move", "kind"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tree-forged-move', '--output', '/tmp/gp10-checkaudit/results/tree-forged-move'])
```

```text
REJECT record C~ tree: R-tree.tree.move.kind: unsupported move 'accept'
REJECT run records_rejected
```

### 182. cofactor-unexpected-key

File: [cases/cofactor-unexpected-key/records.jsonl](cases/cofactor-unexpected-key/records.jsonl). Run manifest: [run.json](cases/cofactor-unexpected-key/run.json). Exact saved output: [observed.stdout](cases/cofactor-unexpected-key/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/cofactor-unexpected-key', '--output', '/tmp/gp10-checkaudit/results/cofactor-unexpected-key'])
```

```text
REJECT record DJ[ cofactor_generator: unknown generator
REJECT run records_rejected
```

### 183. system-renamed-generator

File: [cases/system-renamed-generator/records.jsonl](cases/system-renamed-generator/records.jsonl). Run manifest: [run.json](cases/system-renamed-generator/run.json). Exact saved output: [observed.stdout](cases/system-renamed-generator/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "system"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/system-renamed-generator', '--output', '/tmp/gp10-checkaudit/results/system-renamed-generator'])
```

```text
REJECT record DJ[ system_mismatch: generator keys
REJECT run records_rejected
```

### 184. system-pinned-third-point

File: [cases/system-pinned-third-point/records.jsonl](cases/system-pinned-third-point/records.jsonl). Run manifest: [run.json](cases/system-pinned-third-point/run.json). Exact saved output: [observed.stdout](cases/system-pinned-third-point/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "system"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/system-pinned-third-point', '--output', '/tmp/gp10-checkaudit/results/system-pinned-third-point'])
```

```text
REJECT record DJ[ system_mismatch: generator keys
REJECT run records_rejected
```

### 185. system-changed-polynomial

File: [cases/system-changed-polynomial/records.jsonl](cases/system-changed-polynomial/records.jsonl). Run manifest: [run.json](cases/system-changed-polynomial/run.json). Exact saved output: [observed.stdout](cases/system-changed-polynomial/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "system", "e:1,3"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/system-changed-polynomial', '--output', '/tmp/gp10-checkaudit/results/system-changed-polynomial'])
```

```text
REJECT record DJ[ system_mismatch: generator polynomials
REJECT run records_rejected
```

### 186. sparse-duplicate-monomial

File: [cases/sparse-duplicate-monomial/records.jsonl](cases/sparse-duplicate-monomial/records.jsonl). Run manifest: [run.json](cases/sparse-duplicate-monomial/run.json). Exact saved output: [observed.stdout](cases/sparse-duplicate-monomial/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "e:1,3"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sparse-duplicate-monomial', '--output', '/tmp/gp10-checkaudit/results/sparse-duplicate-monomial'])
```

```text
REJECT record DJ[ sparse_duplicate_monomial
REJECT run records_rejected
```

### 187. sparse-negative-exponent

File: [cases/sparse-negative-exponent/records.jsonl](cases/sparse-negative-exponent/records.jsonl). Run manifest: [run.json](cases/sparse-negative-exponent/run.json). Exact saved output: [observed.stdout](cases/sparse-negative-exponent/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "e:1,3", 0, 1, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sparse-negative-exponent', '--output', '/tmp/gp10-checkaudit/results/sparse-negative-exponent'])
```

```text
REJECT record DJ[ sparse_exponents
REJECT run records_rejected
```

### 188. sparse-boolean-exponent

File: [cases/sparse-boolean-exponent/records.jsonl](cases/sparse-boolean-exponent/records.jsonl). Run manifest: [run.json](cases/sparse-boolean-exponent/run.json). Exact saved output: [observed.stdout](cases/sparse-boolean-exponent/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "e:1,3", 0, 1, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sparse-boolean-exponent', '--output', '/tmp/gp10-checkaudit/results/sparse-boolean-exponent'])
```

```text
REJECT record DJ[ sparse_exponents
REJECT run records_rejected
```

### 189. sparse-extra-variable

File: [cases/sparse-extra-variable/records.jsonl](cases/sparse-extra-variable/records.jsonl). Run manifest: [run.json](cases/sparse-extra-variable/run.json). Exact saved output: [observed.stdout](cases/sparse-extra-variable/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "cofactors", "e:1,3", 0, 1], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sparse-extra-variable', '--output', '/tmp/gp10-checkaudit/results/sparse-extra-variable'])
```

```text
REJECT record DJ[ sparse_exponents
REJECT run records_rejected
```

### 190. saturation-repeated

File: [cases/saturation-repeated/records.jsonl](cases/saturation-repeated/records.jsonl). Run manifest: [run.json](cases/saturation-repeated/run.json). Exact saved output: [observed.stdout](cases/saturation-repeated/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-repeated', '--output', '/tmp/gp10-checkaudit/results/saturation-repeated'])
```

```text
REJECT record DFw sat_duplicate
REJECT run records_rejected
```

### 191. saturation-reversed

File: [cases/saturation-reversed/records.jsonl](cases/saturation-reversed/records.jsonl). Run manifest: [run.json](cases/saturation-reversed/run.json). Exact saved output: [observed.stdout](cases/saturation-reversed/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat", 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-reversed', '--output', '/tmp/gp10-checkaudit/results/saturation-reversed'])
```

```text
REJECT record DFw sat_pair_order: use u < v
REJECT run records_rejected
```

### 192. saturation-self-pair

File: [cases/saturation-self-pair/records.jsonl](cases/saturation-self-pair/records.jsonl). Run manifest: [run.json](cases/saturation-self-pair/run.json). Exact saved output: [observed.stdout](cases/saturation-self-pair/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat", 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-self-pair', '--output', '/tmp/gp10-checkaudit/results/saturation-self-pair'])
```

```text
REJECT record DFw pair: invalid vertices
REJECT run records_rejected
```

### 193. saturation-out-of-range

File: [cases/saturation-out-of-range/records.jsonl](cases/saturation-out-of-range/records.jsonl). Run manifest: [run.json](cases/saturation-out-of-range/run.json). Exact saved output: [observed.stdout](cases/saturation-out-of-range/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat", 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-out-of-range', '--output', '/tmp/gp10-checkaudit/results/saturation-out-of-range'])
```

```text
REJECT record DFw pair: invalid vertices
REJECT run records_rejected
```

### 194. saturation-variable-order

File: [cases/saturation-variable-order/records.jsonl](cases/saturation-variable-order/records.jsonl). Run manifest: [run.json](cases/saturation-variable-order/run.json). Exact saved output: [observed.stdout](cases/saturation-variable-order/observed.stdout).

Positive parent: [existing-k23-saturated-null](cases/existing-k23-saturated-null/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-variable-order', '--output', '/tmp/gp10-checkaudit/results/saturation-variable-order'])
```

```text
REJECT record DFw system_mismatch: generator polynomials
REJECT run records_rejected
```

### 195. saturation-adjacent

File: [cases/saturation-adjacent/records.jsonl](cases/saturation-adjacent/records.jsonl). Run manifest: [run.json](cases/saturation-adjacent/run.json). Exact saved output: [observed.stdout](cases/saturation-adjacent/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Saturating an edge is redundant and mathematically valid.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-adjacent', '--output', '/tmp/gp10-checkaudit/results/saturation-adjacent'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 196. saturation-adjacent-red

File: [cases/saturation-adjacent-red/records.jsonl](cases/saturation-adjacent-red/records.jsonl). Run manifest: [run.json](cases/saturation-adjacent-red/run.json). Exact saved output: [observed.stdout](cases/saturation-adjacent-red/observed.stdout).

Positive parent: [saturation-adjacent](cases/saturation-adjacent/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sat"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/saturation-adjacent-red', '--output', '/tmp/gp10-checkaudit/results/saturation-adjacent-red'])
```

```text
REJECT record DJ[ sat_duplicate
REJECT run records_rejected
```

### 197. real-saturation-variable

File: [cases/real-saturation-variable/records.jsonl](cases/real-saturation-variable/records.jsonl). Run manifest: [run.json](cases/real-saturation-variable/run.json). Exact saved output: [observed.stdout](cases/real-saturation-variable/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Multiply a verified null identity by t_0^2+1; every saturation variable is real.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-saturation-variable', '--output', '/tmp/gp10-checkaudit/results/real-saturation-variable'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 198. real-saturation-variable-red

File: [cases/real-saturation-variable-red/records.jsonl](cases/real-saturation-variable-red/records.jsonl). Run manifest: [run.json](cases/real-saturation-variable-red/run.json). Exact saved output: [observed.stdout](cases/real-saturation-variable-red/observed.stdout).

Positive parent: [real-saturation-variable](cases/real-saturation-variable/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sturm"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-saturation-variable-red', '--output', '/tmp/gp10-checkaudit/results/real-saturation-variable-red'])
```

```text
REJECT record DJ[ sturm_multivariate
REJECT run records_rejected
```

### 199. real-nonexistent-variable

File: [cases/real-nonexistent-variable/records.jsonl](cases/real-nonexistent-variable/records.jsonl). Run manifest: [run.json](cases/real-nonexistent-variable/run.json). Exact saved output: [observed.stdout](cases/real-nonexistent-variable/observed.stdout).

Positive parent: [real-saturation-variable](cases/real-saturation-variable/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sturm"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-nonexistent-variable', '--output', '/tmp/gp10-checkaudit/results/real-nonexistent-variable'])
```

```text
REJECT record DJ[ sturm_variable
REJECT run records_rejected
```

### 200. sos-zero-weight

File: [cases/sos-zero-weight/records.jsonl](cases/sos-zero-weight/records.jsonl). Run manifest: [run.json](cases/sos-zero-weight/run.json). Exact saved output: [observed.stdout](cases/sos-zero-weight/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sos", "squares", 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sos-zero-weight', '--output', '/tmp/gp10-checkaudit/results/sos-zero-weight'])
```

```text
REJECT record DJ[ sos_weight_positive
REJECT run records_rejected
```

### 201. sos-negative-constant

File: [cases/sos-negative-constant/records.jsonl](cases/sos-negative-constant/records.jsonl). Run manifest: [run.json](cases/sos-negative-constant/run.json). Exact saved output: [observed.stdout](cases/sos-negative-constant/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sos", "c"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/sos-negative-constant', '--output', '/tmp/gp10-checkaudit/results/sos-negative-constant'])
```

```text
REJECT record DJ[ sos_constant_positive
REJECT run records_rejected
```

### 202. real-both-proof-types

File: [cases/real-both-proof-types/records.jsonl](cases/real-both-proof-types/records.jsonl). Run manifest: [run.json](cases/real-both-proof-types/run.json). Exact saved output: [observed.stdout](cases/real-both-proof-types/observed.stdout).

Positive parent: [existing-k4-real-sos](cases/existing-k4-real-sos/). Mutation: `{"file": "records.jsonl", "path": ["cert", "sturm"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-both-proof-types', '--output', '/tmp/gp10-checkaudit/results/real-both-proof-types'])
```

```text
REJECT record DJ[ real_proof_choice
REJECT run records_rejected
```

### 203. pointer-negative

File: [cases/pointer-negative/records.jsonl](cases/pointer-negative/records.jsonl). Run manifest: [run.json](cases/pointer-negative/run.json). Exact saved output: [observed.stdout](cases/pointer-negative/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-negative', '--output', '/tmp/gp10-checkaudit/results/pointer-negative'])
```

```text
ACCEPT record Bw verified
REJECT record A_ map_range: E-ptr
REJECT run records_rejected
```

### 204. pointer-too-large

File: [cases/pointer-too-large/records.jsonl](cases/pointer-too-large/records.jsonl). Run manifest: [run.json](cases/pointer-too-large/run.json). Exact saved output: [observed.stdout](cases/pointer-too-large/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-too-large', '--output', '/tmp/gp10-checkaudit/results/pointer-too-large'])
```

```text
ACCEPT record Bw verified
REJECT record A_ map_range: E-ptr
REJECT run records_rejected
```

### 205. pointer-boolean

File: [cases/pointer-boolean/records.jsonl](cases/pointer-boolean/records.jsonl). Run manifest: [run.json](cases/pointer-boolean/run.json). Exact saved output: [observed.stdout](cases/pointer-boolean/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-boolean', '--output', '/tmp/gp10-checkaudit/results/pointer-boolean'])
```

```text
ACCEPT record Bw verified
REJECT record A_ map_range: E-ptr
REJECT run records_rejected
```

### 206. pointer-direction

File: [cases/pointer-direction/records.jsonl](cases/pointer-direction/records.jsonl). Run manifest: [run.json](cases/pointer-direction/run.json). Exact saved output: [observed.stdout](cases/pointer-direction/observed.stdout).

Positive parent: [run-pointers](cases/run-pointers/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-direction', '--output', '/tmp/gp10-checkaudit/results/pointer-direction'])
```

```text
ACCEPT record Bw verified
REJECT record A_ map_length: E-ptr
REJECT run records_rejected
```

### 207. refutation-pointer-direction

File: [cases/refutation-pointer-direction/records.jsonl](cases/refutation-pointer-direction/records.jsonl). Run manifest: [run.json](cases/refutation-pointer-direction/run.json). Exact saved output: [observed.stdout](cases/refutation-pointer-direction/observed.stdout).

Positive parent: [run-refutation-pointer](cases/run-refutation-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refutation-pointer-direction', '--output', '/tmp/gp10-checkaudit/results/refutation-pointer-direction'])
```

```text
REJECT record DJ[ map_length: R-ptr
ACCEPT record C~ verified
REJECT run records_rejected
```

### 208. frozen-index-mismatch

File: [cases/frozen-index-mismatch/records.jsonl](cases/frozen-index-mismatch/records.jsonl). Run manifest: [run.json](cases/frozen-index-mismatch/run.json). Exact saved output: [observed.stdout](cases/frozen-index-mismatch/observed.stdout).

Positive parent: [run-frozen-pointer](cases/run-frozen-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-index-mismatch', '--output', '/tmp/gp10-checkaudit/results/frozen-index-mismatch'])
```

```text
REJECT record DJ[ forbidden_index_graph
REJECT run records_rejected
```

### 209. frozen-index-negative

File: [cases/frozen-index-negative/records.jsonl](cases/frozen-index-negative/records.jsonl). Run manifest: [run.json](cases/frozen-index-negative/run.json). Exact saved output: [observed.stdout](cases/frozen-index-negative/observed.stdout).

Positive parent: [run-frozen-pointer](cases/run-frozen-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-index-negative', '--output', '/tmp/gp10-checkaudit/results/frozen-index-negative'])
```

```text
REJECT record DJ[ forbidden_not_in_force: -1
REJECT run records_rejected
```

### 210. frozen-index-out-of-range

File: [cases/frozen-index-out-of-range/records.jsonl](cases/frozen-index-out-of-range/records.jsonl). Run manifest: [run.json](cases/frozen-index-out-of-range/run.json). Exact saved output: [observed.stdout](cases/frozen-index-out-of-range/observed.stdout).

Positive parent: [run-frozen-pointer](cases/run-frozen-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-index-out-of-range', '--output', '/tmp/gp10-checkaudit/results/frozen-index-out-of-range'])
```

```text
REJECT record DJ[ forbidden_not_in_force: 74
REJECT run records_rejected
```

### 211. frozen-index-boolean

File: [cases/frozen-index-boolean/records.jsonl](cases/frozen-index-boolean/records.jsonl). Run manifest: [run.json](cases/frozen-index-boolean/run.json). Exact saved output: [observed.stdout](cases/frozen-index-boolean/observed.stdout).

Positive parent: [run-frozen-pointer](cases/run-frozen-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-index-boolean', '--output', '/tmp/gp10-checkaudit/results/frozen-index-boolean'])
```

```text
REJECT record DJ[ schema: integer must be an integer
REJECT run records_rejected
```

### 212. pointer-chain

File: [cases/pointer-chain/records.jsonl](cases/pointer-chain/records.jsonl). Run manifest: [run.json](cases/pointer-chain/run.json). Exact saved output: [observed.stdout](cases/pointer-chain/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-chain', '--output', '/tmp/gp10-checkaudit/results/pointer-chain'])
```

```text
ACCEPT record Bw verified
ACCEPT record C~ verified
ACCEPT record A_ verified
ACCEPT record A? verified
ACCEPT run verified
```

### 213. pointer-chain-through-unknown

File: [cases/pointer-chain-through-unknown/records.jsonl](cases/pointer-chain-through-unknown/records.jsonl). Run manifest: [run.json](cases/pointer-chain-through-unknown/run.json). Exact saved output: [observed.stdout](cases/pointer-chain-through-unknown/observed.stdout).

Positive parent: [pointer-chain](cases/pointer-chain/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

One pointer g6 field targets an already declared unknown. Both downstream pointers must reject.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/pointer-chain-through-unknown', '--output', '/tmp/gp10-checkaudit/results/pointer-chain-through-unknown'])
```

```text
ACCEPT record Bw verified
ACCEPT record C~ verified
REJECT record A_ pointer_target_not_accepted_embedded
REJECT record A? pointer_target_not_accepted_embedded
REJECT run records_rejected
```

### 214. refutation-chain

File: [cases/refutation-chain/records.jsonl](cases/refutation-chain/records.jsonl). Run manifest: [run.json](cases/refutation-chain/run.json). Exact saved output: [observed.stdout](cases/refutation-chain/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refutation-chain', '--output', '/tmp/gp10-checkaudit/results/refutation-chain'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 215. refutation-chain-through-unknown

File: [cases/refutation-chain-through-unknown/records.jsonl](cases/refutation-chain-through-unknown/records.jsonl). Run manifest: [run.json](cases/refutation-chain-through-unknown/run.json). Exact saved output: [observed.stdout](cases/refutation-chain-through-unknown/observed.stdout).

Positive parent: [refutation-chain](cases/refutation-chain/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/refutation-chain-through-unknown', '--output', '/tmp/gp10-checkaudit/results/refutation-chain-through-unknown'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
REJECT record DJ[ pointer_target_not_accepted_refuted
REJECT run records_rejected
```

### 216. tu-map-repeated

File: [cases/tu-map-repeated/records.jsonl](cases/tu-map-repeated/records.jsonl). Run manifest: [run.json](cases/tu-map-repeated/run.json). Exact saved output: [observed.stdout](cases/tu-map-repeated/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps", 0, "map"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-map-repeated', '--output', '/tmp/gp10-checkaudit/results/tu-map-repeated'])
```

```text
REJECT record K_?G?cks`M^? map_not_injective: TU step 0
REJECT run records_rejected
```

### 217. tu-map-outside

File: [cases/tu-map-outside/records.jsonl](cases/tu-map-outside/records.jsonl). Run manifest: [run.json](cases/tu-map-outside/run.json). Exact saved output: [observed.stdout](cases/tu-map-outside/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps", 0, "map"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-map-outside', '--output', '/tmp/gp10-checkaudit/results/tu-map-outside'])
```

```text
REJECT record K_?G?cks`M^? map_range: TU step 0
REJECT run records_rejected
```

### 218. tu-gadget-negative

File: [cases/tu-gadget-negative/records.jsonl](cases/tu-gadget-negative/records.jsonl). Run manifest: [run.json](cases/tu-gadget-negative/run.json). Exact saved output: [observed.stdout](cases/tu-gadget-negative/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps", 0, "gadget"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-gadget-negative', '--output', '/tmp/gp10-checkaudit/results/tu-gadget-negative'])
```

```text
REJECT record K_?G?cks`M^? gadget_index
REJECT run records_rejected
```

### 219. tu-no-steps

File: [cases/tu-no-steps/records.jsonl](cases/tu-no-steps/records.jsonl). Run manifest: [run.json](cases/tu-no-steps/run.json). Exact saved output: [observed.stdout](cases/tu-no-steps/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "steps"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-no-steps', '--output', '/tmp/gp10-checkaudit/results/tu-no-steps'])
```

```text
REJECT record K_?G?cks`M^? tu_steps
REJECT run records_rejected
```

### 220. tu-no-terminal-proof

File: [cases/tu-no-terminal-proof/records.jsonl](cases/tu-no-terminal-proof/records.jsonl). Run manifest: [run.json](cases/tu-no-terminal-proof/run.json). Exact saved output: [observed.stdout](cases/tu-no-terminal-proof/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "end"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-no-terminal-proof', '--output', '/tmp/gp10-checkaudit/results/tu-no-terminal-proof'])
```

```text
REJECT record K_?G?cks`M^? schema: TU end: missing=['map', 'refuted'] extra=[]
REJECT run records_rejected
```

### 221. tu-terminal-index

File: [cases/tu-terminal-index/records.jsonl](cases/tu-terminal-index/records.jsonl). Run manifest: [run.json](cases/tu-terminal-index/run.json). Exact saved output: [observed.stdout](cases/tu-terminal-index/observed.stdout).

Positive parent: [existing-tu-chain](cases/existing-tu-chain/). Mutation: `{"file": "records.jsonl", "path": ["cert", "end", "forbidden"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-terminal-index', '--output', '/tmp/gp10-checkaudit/results/tu-terminal-index'])
```

```text
REJECT record K_?G?cks`M^? forbidden_not_in_force: 74
REJECT run records_rejected
```

### 222. minimality-omitted-minimal

File: [cases/minimality-omitted-minimal/records.jsonl](cases/minimality-omitted-minimal/records.jsonl). Run manifest: [run.json](cases/minimality-omitted-minimal/run.json). Exact saved output: [observed.stdout](cases/minimality-omitted-minimal/observed.stdout).

Positive parent: [run-minimality](cases/run-minimality/). Mutation: `{"file": "claim.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/minimality-omitted-minimal', '--output', '/tmp/gp10-checkaudit/results/minimality-omitted-minimal'])
```

```text
ACCEPT record DFw verified
ACCEPT record DF{ verified
REJECT run minimality_claim_mismatch
```

### 223. conditional-minimality-omitted

File: [cases/conditional-minimality-omitted/records.jsonl](cases/conditional-minimality-omitted/records.jsonl). Run manifest: [run.json](cases/conditional-minimality-omitted/run.json). Exact saved output: [observed.stdout](cases/conditional-minimality-omitted/observed.stdout).

Positive parent: [run-conditional-minimality](cases/run-conditional-minimality/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/conditional-minimality-omitted', '--output', '/tmp/gp10-checkaudit/results/conditional-minimality-omitted'])
```

```text
ACCEPT record DF{ verified
ACCEPT record DFw verified
REJECT run minimality_claim_mismatch
```

### 224. input-wrong-hash

File: [cases/input-wrong-hash/records.jsonl](cases/input-wrong-hash/records.jsonl). Run manifest: [run.json](cases/input-wrong-hash/run.json). Exact saved output: [observed.stdout](cases/input-wrong-hash/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/input-wrong-hash', '--output', '/tmp/gp10-checkaudit/results/input-wrong-hash'])
```

```text
REJECT run input_hash
```

### 225. empty-record-stream

File: [cases/empty-record-stream/records.jsonl](cases/empty-record-stream/records.jsonl). Run manifest: [run.json](cases/empty-record-stream/run.json). Exact saved output: [observed.stdout](cases/empty-record-stream/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/empty-record-stream', '--output', '/tmp/gp10-checkaudit/results/empty-record-stream'])
```

```text
REJECT run coverage
```

### 226. records-no-final-newline

File: [cases/records-no-final-newline/records.jsonl](cases/records-no-final-newline/records.jsonl). Run manifest: [run.json](cases/records-no-final-newline/run.json). Exact saved output: [observed.stdout](cases/records-no-final-newline/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/records-no-final-newline', '--output', '/tmp/gp10-checkaudit/results/records-no-final-newline'])
```

```text
REJECT run line_format
```

### 227. records-blank-line

File: [cases/records-blank-line/records.jsonl](cases/records-blank-line/records.jsonl). Run manifest: [run.json](cases/records-blank-line/run.json). Exact saved output: [observed.stdout](cases/records-blank-line/observed.stdout).

Positive parent: [run-mixed](cases/run-mixed/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/records-blank-line', '--output', '/tmp/gp10-checkaudit/results/records-blank-line'])
```

```text
REJECT run line_format
```

### 228. unknown-file-absent

File: [cases/unknown-file-absent/records.jsonl](cases/unknown-file-absent/records.jsonl). Run manifest: [run.json](cases/unknown-file-absent/run.json). Exact saved output: [observed.stdout](cases/unknown-file-absent/observed.stdout).

Positive parent: [run-unknown](cases/run-unknown/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/unknown-file-absent', '--output', '/tmp/gp10-checkaudit/results/unknown-file-absent'])
```

```text
ACCEPT record A_ verified
REJECT run unknown_file_missing
```

### 229. duplicate-json-key

File: [cases/duplicate-json-key/records.jsonl](cases/duplicate-json-key/records.jsonl). Run manifest: [run.json](cases/duplicate-json-key/run.json). Exact saved output: [observed.stdout](cases/duplicate-json-key/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/duplicate-json-key', '--output', '/tmp/gp10-checkaudit/results/duplicate-json-key'])
```

```text
REJECT record records.jsonl:1 duplicate_json_key: verdict
REJECT run records_rejected
```

### 230. duplicate-generator-key

File: [cases/duplicate-generator-key/records.jsonl](cases/duplicate-generator-key/records.jsonl). Run manifest: [run.json](cases/duplicate-generator-key/run.json). Exact saved output: [observed.stdout](cases/duplicate-generator-key/observed.stdout).

Positive parent: [existing-k4-isolate-null](cases/existing-k4-isolate-null/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/duplicate-generator-key', '--output', '/tmp/gp10-checkaudit/results/duplicate-generator-key'])
```

```text
REJECT record records.jsonl:1 duplicate_json_key: duplicate
REJECT run records_rejected
```

### 231. json-nan

File: [cases/json-nan/records.jsonl](cases/json-nan/records.jsonl). Run manifest: [run.json](cases/json-nan/run.json). Exact saved output: [observed.stdout](cases/json-nan/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/json-nan', '--output', '/tmp/gp10-checkaudit/results/json-nan'])
```

```text
REJECT record records.jsonl:1 json_constant: NaN
REJECT run records_rejected
```

### 232. coverage-noncanonical-record

File: [cases/coverage-noncanonical-record/records.jsonl](cases/coverage-noncanonical-record/records.jsonl). Run manifest: [run.json](cases/coverage-noncanonical-record/run.json). Exact saved output: [observed.stdout](cases/coverage-noncanonical-record/observed.stdout).

Positive parent: [existing-c4](cases/existing-c4/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/coverage-noncanonical-record', '--output', '/tmp/gp10-checkaudit/results/coverage-noncanonical-record'])
```

```text
REJECT record Cl noncanonical_g6: Cl
REJECT run records_rejected
```

### 233. control-sample-B4p

File: [cases/control-sample-B4p/records.jsonl](cases/control-sample-B4p/records.jsonl). Run manifest: [run.json](cases/control-sample-B4p/run.json). Exact saved output: [observed.stdout](cases/control-sample-B4p/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Complete frozen input coverage, declared unknowns, sample only.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/control-sample-B4p', '--output', '/tmp/gp10-checkaudit/results/control-sample-B4p'])
```

```text
ACCEPT record C^ verified
ACCEPT record Cr verified
ACCEPT record C~ verified
ACCEPT run verified
```

### 234. unsupported-B4p

File: [cases/unsupported-B4p/records.jsonl](cases/unsupported-B4p/records.jsonl). Run manifest: [run.json](cases/unsupported-B4p/run.json). Exact saved output: [observed.stdout](cases/unsupported-B4p/observed.stdout).

Positive parent: [control-sample-B4p](cases/control-sample-B4p/). Mutation: `{"file": "run.json", "scope": "file"}`.

Contract amendment requires this profile. Rejection is a reproduced implementation gap, not a soundness exploit.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/unsupported-B4p', '--output', '/tmp/gp10-checkaudit/results/unsupported-B4p'])
```

```text
REJECT run profile
```

### 235. control-sample-B5p

File: [cases/control-sample-B5p/records.jsonl](cases/control-sample-B5p/records.jsonl). Run manifest: [run.json](cases/control-sample-B5p/run.json). Exact saved output: [observed.stdout](cases/control-sample-B5p/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Complete frozen input coverage, declared unknowns, sample only.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/control-sample-B5p', '--output', '/tmp/gp10-checkaudit/results/control-sample-B5p'])
```

```text
ACCEPT record DFw verified
ACCEPT record DF{ verified
ACCEPT record DR{ verified
ACCEPT record Dd[ verified
ACCEPT record DqK verified
ACCEPT record Dr[ verified
ACCEPT record Dr{ verified
ACCEPT run verified
```

### 236. unsupported-B5p

File: [cases/unsupported-B5p/records.jsonl](cases/unsupported-B5p/records.jsonl). Run manifest: [run.json](cases/unsupported-B5p/run.json). Exact saved output: [observed.stdout](cases/unsupported-B5p/observed.stdout).

Positive parent: [control-sample-B5p](cases/control-sample-B5p/). Mutation: `{"file": "run.json", "scope": "file"}`.

Contract amendment requires this profile. Rejection is a reproduced implementation gap, not a soundness exploit.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/unsupported-B5p', '--output', '/tmp/gp10-checkaudit/results/unsupported-B5p'])
```

```text
REJECT run profile
```

### 237. control-sample-B6p

File: [cases/control-sample-B6p/records.jsonl](cases/control-sample-B6p/records.jsonl). Run manifest: [run.json](cases/control-sample-B6p/run.json). Exact saved output: [observed.stdout](cases/control-sample-B6p/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Complete frozen input coverage, declared unknowns, sample only.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/control-sample-B6p', '--output', '/tmp/gp10-checkaudit/results/control-sample-B6p'])
```

```text
ACCEPT record EDZW verified
ACCEPT record EDZw verified
ACCEPT record ED^_ verified
ACCEPT record EElw verified
ACCEPT record EPVW verified
ACCEPT record EQlw verified
ACCEPT record ETXW verified
ACCEPT record E_lo verified
ACCEPT record E_lw verified
ACCEPT record E`dg verified
ACCEPT record E`lo verified
ACCEPT record EoSo verified
ACCEPT record EoSw verified
ACCEPT record EqLw verified
ACCEPT record EqNw verified
ACCEPT record E{Sw verified
ACCEPT run verified
```

### 238. unsupported-B6p

File: [cases/unsupported-B6p/records.jsonl](cases/unsupported-B6p/records.jsonl). Run manifest: [run.json](cases/unsupported-B6p/run.json). Exact saved output: [observed.stdout](cases/unsupported-B6p/observed.stdout).

Positive parent: [control-sample-B6p](cases/control-sample-B6p/). Mutation: `{"file": "run.json", "scope": "file"}`.

Contract amendment requires this profile. Rejection is a reproduced implementation gap, not a soundness exploit.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/unsupported-B6p', '--output', '/tmp/gp10-checkaudit/results/unsupported-B6p'])
```

```text
REJECT run profile
```

### 239. control-sample-B7p

File: [cases/control-sample-B7p/records.jsonl](cases/control-sample-B7p/records.jsonl). Run manifest: [run.json](cases/control-sample-B7p/run.json). Exact saved output: [observed.stdout](cases/control-sample-B7p/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Complete frozen input coverage, declared unknowns, sample only.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/control-sample-B7p', '--output', '/tmp/gp10-checkaudit/results/control-sample-B7p'])
```

```text
ACCEPT record F?NVO verified
ACCEPT record F?dn_ verified
ACCEPT record F?dvW verified
ACCEPT record F?ur_ verified
ACCEPT record F@NN_ verified
ACCEPT record F@NUW verified
ACCEPT record F@Vdo verified
ACCEPT record F@YUw verified
ACCEPT record F@hUW verified
ACCEPT record F@hVw verified
ACCEPT record F@h^_ verified
ACCEPT record F@pto verified
ACCEPT record FAI^O verified
ACCEPT record FAMn_ verified
ACCEPT record FANTW verified
ACCEPT record FANcw verified
ACCEPT record FAhto verified
ACCEPT record FBFLW verified
ACCEPT record FBJKw verified
ACCEPT record FB_mW verified
ACCEPT record FCLmw verified
ACCEPT record FCO~W verified
ACCEPT record FCS~? verified
ACCEPT record FCUj_ verified
ACCEPT record FCUrO verified
ACCEPT record FCXto verified
ACCEPT record FCdrO verified
ACCEPT record FDPkw verified
ACCEPT record FDZ@w verified
ACCEPT record FGM]_ verified
ACCEPT record FGcuW verified
ACCEPT record FGdtw verified
ACCEPT record FHFKw verified
ACCEPT record FINTW verified
ACCEPT record FJQkw verified
ACCEPT record FKdPW verified
ACCEPT record FPO]w verified
ACCEPT record FQG]W verified
ACCEPT record FQMiw verified
ACCEPT record FSXPw verified
ACCEPT record FWEYo verified
ACCEPT record F_hXw verified
ACCEPT record F`AZO verified
ACCEPT record F`AZW verified
ACCEPT record F`QXw verified
ACCEPT record F`dn_ verified
ACCEPT record F`hPw verified
ACCEPT record F`o~_ verified
ACCEPT record Fo@Xo verified
ACCEPT record Fo@Xw verified
ACCEPT record FoDPO verified
ACCEPT record FoDPW verified
ACCEPT record FoSrw verified
ACCEPT record FoSvw verified
ACCEPT record FoSz_ verified
ACCEPT record FoS~_ verified
ACCEPT record Fq?gw verified
ACCEPT record FqHXw verified
ACCEPT record FqSpW verified
ACCEPT record FwDXo verified
ACCEPT run verified
```

### 240. unsupported-B7p

File: [cases/unsupported-B7p/records.jsonl](cases/unsupported-B7p/records.jsonl). Run manifest: [run.json](cases/unsupported-B7p/run.json). Exact saved output: [observed.stdout](cases/unsupported-B7p/observed.stdout).

Positive parent: [control-sample-B7p](cases/control-sample-B7p/). Mutation: `{"file": "run.json", "scope": "file"}`.

Contract amendment requires this profile. Rejection is a reproduced implementation gap, not a soundness exploit.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/unsupported-B7p', '--output', '/tmp/gp10-checkaudit/results/unsupported-B7p'])
```

```text
REJECT run profile
```

### 241. frozen-canonical-labels

File: [cases/frozen-canonical-labels/records.jsonl](cases/frozen-canonical-labels/records.jsonl). Run manifest: [run.json](cases/frozen-canonical-labels/run.json). Exact saved output: [observed.stdout](cases/frozen-canonical-labels/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

F9 index 2; R-ptr maps use canonical graph labels.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-canonical-labels', '--output', '/tmp/gp10-checkaudit/results/frozen-canonical-labels'])
```

```text
ACCEPT record EqLw verified
ACCEPT run verified
```

### 242. frozen-stored-labels-confused

File: [cases/frozen-stored-labels-confused/records.jsonl](cases/frozen-stored-labels-confused/records.jsonl). Run manifest: [run.json](cases/frozen-stored-labels-confused/run.json). Exact saved output: [observed.stdout](cases/frozen-stored-labels-confused/observed.stdout).

Positive parent: [frozen-canonical-labels](cases/frozen-canonical-labels/). Mutation: `{"file": "records.jsonl", "path": ["cert", "map"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/frozen-stored-labels-confused', '--output', '/tmp/gp10-checkaudit/results/frozen-stored-labels-confused'])
```

```text
REJECT record EqLw map_not_edge_preserving: R-ptr: (1, 3) -> (1, 4)
REJECT run records_rejected
```

### 243. tu-frozen-stored-labels

File: [cases/tu-frozen-stored-labels/records.jsonl](cases/tu-frozen-stored-labels/records.jsonl). Run manifest: [run.json](cases/tu-frozen-stored-labels/run.json). Exact saved output: [observed.stdout](cases/tu-frozen-stored-labels/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

F9 index 2; TU end maps use stored JSON labels.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-frozen-stored-labels', '--output', '/tmp/gp10-checkaudit/results/tu-frozen-stored-labels'])
```

```text
ACCEPT record K?CpOA@O]ABo verified
ACCEPT run verified
```

### 244. tu-frozen-canonical-labels-confused

File: [cases/tu-frozen-canonical-labels-confused/records.jsonl](cases/tu-frozen-canonical-labels-confused/records.jsonl). Run manifest: [run.json](cases/tu-frozen-canonical-labels-confused/run.json). Exact saved output: [observed.stdout](cases/tu-frozen-canonical-labels-confused/observed.stdout).

Positive parent: [tu-frozen-stored-labels](cases/tu-frozen-stored-labels/). Mutation: `{"file": "records.jsonl", "path": ["cert", "end", "map"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-frozen-canonical-labels-confused', '--output', '/tmp/gp10-checkaudit/results/tu-frozen-canonical-labels-confused'])
```

```text
REJECT record K?CpOA@O]ABo map_not_edge_preserving: TU forbidden end: (0, 3) -> (2, 4)
REJECT run records_rejected
```

### 245. tu-pointer-with-unknown

File: [cases/tu-pointer-with-unknown/records.jsonl](cases/tu-pointer-with-unknown/records.jsonl). Run manifest: [run.json](cases/tu-pointer-with-unknown/run.json). Exact saved output: [observed.stdout](cases/tu-pointer-with-unknown/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-pointer-with-unknown', '--output', '/tmp/gp10-checkaudit/results/tu-pointer-with-unknown'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
ACCEPT record K_?G?cks`M^? verified
ACCEPT run verified
```

### 246. tu-target-unknown

File: [cases/tu-target-unknown/records.jsonl](cases/tu-target-unknown/records.jsonl). Run manifest: [run.json](cases/tu-target-unknown/run.json). Exact saved output: [observed.stdout](cases/tu-target-unknown/observed.stdout).

Positive parent: [tu-pointer-with-unknown](cases/tu-pointer-with-unknown/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-target-unknown', '--output', '/tmp/gp10-checkaudit/results/tu-target-unknown'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
REJECT record K_?G?cks`M^? pointer_target_not_accepted_refuted
REJECT run records_rejected
```

### 247. derive-k4-disabled

File: [cases/derive-k4-disabled/records.jsonl](cases/derive-k4-disabled/records.jsonl). Run manifest: [run.json](cases/derive-k4-disabled/run.json). Exact saved output: [observed.stdout](cases/derive-k4-disabled/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/derive-k4-disabled', '--output', '/tmp/gp10-checkaudit/results/derive-k4-disabled'])
```

```text
ACCEPT record C~ verified
ACCEPT run verified
```

### 248. derive-requires-deletion

File: [cases/derive-requires-deletion/records.jsonl](cases/derive-requires-deletion/records.jsonl). Run manifest: [run.json](cases/derive-requires-deletion/run.json). Exact saved output: [observed.stdout](cases/derive-requires-deletion/observed.stdout).

Positive parent: [derive-k4-disabled](cases/derive-k4-disabled/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/derive-requires-deletion', '--output', '/tmp/gp10-checkaudit/results/derive-requires-deletion'])
```

```text
ACCEPT record C~ verified
REJECT run minimality_deletion_missing
```

### 249. derive-k4-complete

File: [cases/derive-k4-complete/records.jsonl](cases/derive-k4-complete/records.jsonl). Run manifest: [run.json](cases/derive-k4-complete/run.json). Exact saved output: [observed.stdout](cases/derive-k4-complete/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/derive-k4-complete', '--output', '/tmp/gp10-checkaudit/results/derive-k4-complete'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
ACCEPT run verified
```

### 250. derive-k4-omitted

File: [cases/derive-k4-omitted/records.jsonl](cases/derive-k4-omitted/records.jsonl). Run manifest: [run.json](cases/derive-k4-omitted/run.json). Exact saved output: [observed.stdout](cases/derive-k4-omitted/observed.stdout).

Positive parent: [derive-k4-complete](cases/derive-k4-complete/). Mutation: `{"file": "claim.g6", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/derive-k4-omitted', '--output', '/tmp/gp10-checkaudit/results/derive-k4-omitted'])
```

```text
ACCEPT record C~ verified
ACCEPT record C^ verified
REJECT run minimality_claim_mismatch
```

### 251. block-forbidden-baseline

File: [cases/block-forbidden-baseline/records.jsonl](cases/block-forbidden-baseline/records.jsonl). Run manifest: [run.json](cases/block-forbidden-baseline/run.json). Exact saved output: [observed.stdout](cases/block-forbidden-baseline/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/block-forbidden-baseline', '--output', '/tmp/gp10-checkaudit/results/block-forbidden-baseline'])
```

```text
ACCEPT record DN{ verified
ACCEPT run verified
```

### 252. block-forbidden-shortcut

File: [cases/block-forbidden-shortcut/records.jsonl](cases/block-forbidden-shortcut/records.jsonl). Run manifest: [run.json](cases/block-forbidden-shortcut/run.json). Exact saved output: [observed.stdout](cases/block-forbidden-shortcut/observed.stdout).

Positive parent: [block-forbidden-baseline](cases/block-forbidden-baseline/). Mutation: `{"file": "run.json", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/block-forbidden-shortcut', '--output', '/tmp/gp10-checkaudit/results/block-forbidden-shortcut'])
```

```text
ACCEPT record DN{ verified
REJECT run block_forbidden
```

### 253. real-constant

File: [cases/real-constant/records.jsonl](cases/real-constant/records.jsonl). Run manifest: [run.json](cases/real-constant/run.json). Exact saved output: [observed.stdout](cases/real-constant/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

A nonzero constant has no real zero although it involves no variable.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-constant', '--output', '/tmp/gp10-checkaudit/results/real-constant'])
```

```text
ACCEPT record DJ[ verified
ACCEPT run verified
```

### 254. real-constant-zero-target

File: [cases/real-constant-zero-target/records.jsonl](cases/real-constant-zero-target/records.jsonl). Run manifest: [run.json](cases/real-constant-zero-target/run.json). Exact saved output: [observed.stdout](cases/real-constant-zero-target/observed.stdout).

Positive parent: [real-constant](cases/real-constant/). Mutation: `{"file": "records.jsonl", "path": ["cert", "f"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/real-constant-zero-target', '--output', '/tmp/gp10-checkaudit/results/real-constant-zero-target'])
```

```text
REJECT record DJ[ cofactor_identity
REJECT run records_rejected
```

### 255. sturm-positive--3-1

File: [cases/sturm-positive--3-1/polynomial.json](cases/sturm-positive--3-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([10, 6, 1])
```

```text
RETURN sturm_real_roots 0
```

### 256. sturm-positive--3-1-two-roots

File: [cases/sturm-positive--3-1-two-roots/polynomial.json](cases/sturm-positive--3-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-1-two-roots/observed.stdout).

Positive parent: [sturm-positive--3-1](cases/sturm-positive--3-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([8, 6, 1])
```

```text
RETURN sturm_real_roots 2
```

### 257. sturm-positive--3-1-repeated-root

File: [cases/sturm-positive--3-1-repeated-root/polynomial.json](cases/sturm-positive--3-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive--3-1](cases/sturm-positive--3-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([9, 6, 1])
```

```text
RETURN sturm_real_roots 1
```

### 258. sturm-positive--3-2

File: [cases/sturm-positive--3-2/polynomial.json](cases/sturm-positive--3-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([13, 6, 1])
```

```text
RETURN sturm_real_roots 0
```

### 259. sturm-positive--3-2-two-roots

File: [cases/sturm-positive--3-2-two-roots/polynomial.json](cases/sturm-positive--3-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-2-two-roots/observed.stdout).

Positive parent: [sturm-positive--3-2](cases/sturm-positive--3-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, 6, 1])
```

```text
RETURN sturm_real_roots 2
```

### 260. sturm-positive--3-2-repeated-root

File: [cases/sturm-positive--3-2-repeated-root/polynomial.json](cases/sturm-positive--3-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--3-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive--3-2](cases/sturm-positive--3-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([9, 6, 1])
```

```text
RETURN sturm_real_roots 1
```

### 261. sturm-positive--2-1

File: [cases/sturm-positive--2-1/polynomial.json](cases/sturm-positive--2-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, 4, 1])
```

```text
RETURN sturm_real_roots 0
```

### 262. sturm-positive--2-1-two-roots

File: [cases/sturm-positive--2-1-two-roots/polynomial.json](cases/sturm-positive--2-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-1-two-roots/observed.stdout).

Positive parent: [sturm-positive--2-1](cases/sturm-positive--2-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([3, 4, 1])
```

```text
RETURN sturm_real_roots 2
```

### 263. sturm-positive--2-1-repeated-root

File: [cases/sturm-positive--2-1-repeated-root/polynomial.json](cases/sturm-positive--2-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive--2-1](cases/sturm-positive--2-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([4, 4, 1])
```

```text
RETURN sturm_real_roots 1
```

### 264. sturm-positive--2-2

File: [cases/sturm-positive--2-2/polynomial.json](cases/sturm-positive--2-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([8, 4, 1])
```

```text
RETURN sturm_real_roots 0
```

### 265. sturm-positive--2-2-two-roots

File: [cases/sturm-positive--2-2-two-roots/polynomial.json](cases/sturm-positive--2-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-2-two-roots/observed.stdout).

Positive parent: [sturm-positive--2-2](cases/sturm-positive--2-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, 4, 1])
```

```text
RETURN sturm_real_roots 2
```

### 266. sturm-positive--2-2-repeated-root

File: [cases/sturm-positive--2-2-repeated-root/polynomial.json](cases/sturm-positive--2-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--2-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive--2-2](cases/sturm-positive--2-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([4, 4, 1])
```

```text
RETURN sturm_real_roots 1
```

### 267. sturm-positive--1-1

File: [cases/sturm-positive--1-1/polynomial.json](cases/sturm-positive--1-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([2, 2, 1])
```

```text
RETURN sturm_real_roots 0
```

### 268. sturm-positive--1-1-two-roots

File: [cases/sturm-positive--1-1-two-roots/polynomial.json](cases/sturm-positive--1-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-1-two-roots/observed.stdout).

Positive parent: [sturm-positive--1-1](cases/sturm-positive--1-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, 2, 1])
```

```text
RETURN sturm_real_roots 2
```

### 269. sturm-positive--1-1-repeated-root

File: [cases/sturm-positive--1-1-repeated-root/polynomial.json](cases/sturm-positive--1-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive--1-1](cases/sturm-positive--1-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, 2, 1])
```

```text
RETURN sturm_real_roots 1
```

### 270. sturm-positive--1-2

File: [cases/sturm-positive--1-2/polynomial.json](cases/sturm-positive--1-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, 2, 1])
```

```text
RETURN sturm_real_roots 0
```

### 271. sturm-positive--1-2-two-roots

File: [cases/sturm-positive--1-2-two-roots/polynomial.json](cases/sturm-positive--1-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-2-two-roots/observed.stdout).

Positive parent: [sturm-positive--1-2](cases/sturm-positive--1-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([-3, 2, 1])
```

```text
RETURN sturm_real_roots 2
```

### 272. sturm-positive--1-2-repeated-root

File: [cases/sturm-positive--1-2-repeated-root/polynomial.json](cases/sturm-positive--1-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive--1-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive--1-2](cases/sturm-positive--1-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, 2, 1])
```

```text
RETURN sturm_real_roots 1
```

### 273. sturm-positive-0-1

File: [cases/sturm-positive-0-1/polynomial.json](cases/sturm-positive-0-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, 0, 1])
```

```text
RETURN sturm_real_roots 0
```

### 274. sturm-positive-0-1-two-roots

File: [cases/sturm-positive-0-1-two-roots/polynomial.json](cases/sturm-positive-0-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-1-two-roots/observed.stdout).

Positive parent: [sturm-positive-0-1](cases/sturm-positive-0-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([-1, 0, 1])
```

```text
RETURN sturm_real_roots 2
```

### 275. sturm-positive-0-1-repeated-root

File: [cases/sturm-positive-0-1-repeated-root/polynomial.json](cases/sturm-positive-0-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive-0-1](cases/sturm-positive-0-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, 0, 1])
```

```text
RETURN sturm_real_roots 1
```

### 276. sturm-positive-0-2

File: [cases/sturm-positive-0-2/polynomial.json](cases/sturm-positive-0-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([4, 0, 1])
```

```text
RETURN sturm_real_roots 0
```

### 277. sturm-positive-0-2-two-roots

File: [cases/sturm-positive-0-2-two-roots/polynomial.json](cases/sturm-positive-0-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-2-two-roots/observed.stdout).

Positive parent: [sturm-positive-0-2](cases/sturm-positive-0-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([-4, 0, 1])
```

```text
RETURN sturm_real_roots 2
```

### 278. sturm-positive-0-2-repeated-root

File: [cases/sturm-positive-0-2-repeated-root/polynomial.json](cases/sturm-positive-0-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-0-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive-0-2](cases/sturm-positive-0-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, 0, 1])
```

```text
RETURN sturm_real_roots 1
```

### 279. sturm-positive-1-1

File: [cases/sturm-positive-1-1/polynomial.json](cases/sturm-positive-1-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([2, -2, 1])
```

```text
RETURN sturm_real_roots 0
```

### 280. sturm-positive-1-1-two-roots

File: [cases/sturm-positive-1-1-two-roots/polynomial.json](cases/sturm-positive-1-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-1-two-roots/observed.stdout).

Positive parent: [sturm-positive-1-1](cases/sturm-positive-1-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, -2, 1])
```

```text
RETURN sturm_real_roots 2
```

### 281. sturm-positive-1-1-repeated-root

File: [cases/sturm-positive-1-1-repeated-root/polynomial.json](cases/sturm-positive-1-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive-1-1](cases/sturm-positive-1-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, -2, 1])
```

```text
RETURN sturm_real_roots 1
```

### 282. sturm-positive-1-2

File: [cases/sturm-positive-1-2/polynomial.json](cases/sturm-positive-1-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, -2, 1])
```

```text
RETURN sturm_real_roots 0
```

### 283. sturm-positive-1-2-two-roots

File: [cases/sturm-positive-1-2-two-roots/polynomial.json](cases/sturm-positive-1-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-2-two-roots/observed.stdout).

Positive parent: [sturm-positive-1-2](cases/sturm-positive-1-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([-3, -2, 1])
```

```text
RETURN sturm_real_roots 2
```

### 284. sturm-positive-1-2-repeated-root

File: [cases/sturm-positive-1-2-repeated-root/polynomial.json](cases/sturm-positive-1-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-1-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive-1-2](cases/sturm-positive-1-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, -2, 1])
```

```text
RETURN sturm_real_roots 1
```

### 285. sturm-positive-2-1

File: [cases/sturm-positive-2-1/polynomial.json](cases/sturm-positive-2-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, -4, 1])
```

```text
RETURN sturm_real_roots 0
```

### 286. sturm-positive-2-1-two-roots

File: [cases/sturm-positive-2-1-two-roots/polynomial.json](cases/sturm-positive-2-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-1-two-roots/observed.stdout).

Positive parent: [sturm-positive-2-1](cases/sturm-positive-2-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([3, -4, 1])
```

```text
RETURN sturm_real_roots 2
```

### 287. sturm-positive-2-1-repeated-root

File: [cases/sturm-positive-2-1-repeated-root/polynomial.json](cases/sturm-positive-2-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive-2-1](cases/sturm-positive-2-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([4, -4, 1])
```

```text
RETURN sturm_real_roots 1
```

### 288. sturm-positive-2-2

File: [cases/sturm-positive-2-2/polynomial.json](cases/sturm-positive-2-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([8, -4, 1])
```

```text
RETURN sturm_real_roots 0
```

### 289. sturm-positive-2-2-two-roots

File: [cases/sturm-positive-2-2-two-roots/polynomial.json](cases/sturm-positive-2-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-2-two-roots/observed.stdout).

Positive parent: [sturm-positive-2-2](cases/sturm-positive-2-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, -4, 1])
```

```text
RETURN sturm_real_roots 2
```

### 290. sturm-positive-2-2-repeated-root

File: [cases/sturm-positive-2-2-repeated-root/polynomial.json](cases/sturm-positive-2-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-2-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive-2-2](cases/sturm-positive-2-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([4, -4, 1])
```

```text
RETURN sturm_real_roots 1
```

### 291. sturm-positive-3-1

File: [cases/sturm-positive-3-1/polynomial.json](cases/sturm-positive-3-1/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-1/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([10, -6, 1])
```

```text
RETURN sturm_real_roots 0
```

### 292. sturm-positive-3-1-two-roots

File: [cases/sturm-positive-3-1-two-roots/polynomial.json](cases/sturm-positive-3-1-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-1-two-roots/observed.stdout).

Positive parent: [sturm-positive-3-1](cases/sturm-positive-3-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([8, -6, 1])
```

```text
RETURN sturm_real_roots 2
```

### 293. sturm-positive-3-1-repeated-root

File: [cases/sturm-positive-3-1-repeated-root/polynomial.json](cases/sturm-positive-3-1-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-1-repeated-root/observed.stdout).

Positive parent: [sturm-positive-3-1](cases/sturm-positive-3-1/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([9, -6, 1])
```

```text
RETURN sturm_real_roots 1
```

### 294. sturm-positive-3-2

File: [cases/sturm-positive-3-2/polynomial.json](cases/sturm-positive-3-2/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-2/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([13, -6, 1])
```

```text
RETURN sturm_real_roots 0
```

### 295. sturm-positive-3-2-two-roots

File: [cases/sturm-positive-3-2-two-roots/polynomial.json](cases/sturm-positive-3-2-two-roots/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-2-two-roots/observed.stdout).

Positive parent: [sturm-positive-3-2](cases/sturm-positive-3-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([5, -6, 1])
```

```text
RETURN sturm_real_roots 2
```

### 296. sturm-positive-3-2-repeated-root

File: [cases/sturm-positive-3-2-repeated-root/polynomial.json](cases/sturm-positive-3-2-repeated-root/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-positive-3-2-repeated-root/observed.stdout).

Positive parent: [sturm-positive-3-2](cases/sturm-positive-3-2/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([9, -6, 1])
```

```text
RETURN sturm_real_roots 1
```

### 297. sturm-repeated-complex

File: [cases/sturm-repeated-complex/polynomial.json](cases/sturm-repeated-complex/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-repeated-complex/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1, 0, 2, 0, 1])
```

```text
RETURN sturm_real_roots 0
```

### 298. sturm-quartic-real

File: [cases/sturm-quartic-real/polynomial.json](cases/sturm-quartic-real/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-quartic-real/observed.stdout).

Positive parent: [sturm-repeated-complex](cases/sturm-repeated-complex/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([-1, 0, 2, 0, 1])
```

```text
RETURN sturm_real_roots 2
```

### 299. sturm-quartic-repeated-real

File: [cases/sturm-quartic-repeated-real/polynomial.json](cases/sturm-quartic-repeated-real/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-quartic-repeated-real/observed.stdout).

Positive parent: [sturm-repeated-complex](cases/sturm-repeated-complex/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0, 0, 2, 0, 1])
```

```text
RETURN sturm_real_roots 1
```

### 300. sturm-constant

File: [cases/sturm-constant/polynomial.json](cases/sturm-constant/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-constant/observed.stdout).

Genuine accepted baseline, with a rejected direct companion elsewhere in this section.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([1])
```

```text
RETURN sturm_real_roots 0
```

### 301. sturm-zero

File: [cases/sturm-zero/polynomial.json](cases/sturm-zero/polynomial.json). Exact saved output: [observed.stdout](cases/sturm-zero/observed.stdout).

Positive parent: [sturm-constant](cases/sturm-constant/). Mutation: `{"file": "polynomial.json", "path": [0], "scope": "polynomial"}`.

Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors.

Executed in-process command:

```python
gp10check.sturm_real_roots([0])
```

```text
REJECT helper sturm_zero_polynomial
```

### 302. moser-coordinate-red

File: [cases/moser-coordinate-red/records.jsonl](cases/moser-coordinate-red/records.jsonl). Run manifest: [run.json](cases/moser-coordinate-red/run.json). Exact saved output: [observed.stdout](cases/moser-coordinate-red/observed.stdout).

Positive parent: [existing-moser](cases/existing-moser/). Mutation: `{"file": "records.jsonl", "path": ["cert", "coords", 0, 0, 0], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/moser-coordinate-red', '--output', '/tmp/gp10-checkaudit/results/moser-coordinate-red'])
```

```text
REJECT record F`o~_ edge_equation: (0, 1)
REJECT run records_rejected
```

### 303. k23-tree-collision-red

File: [cases/k23-tree-collision-red/records.jsonl](cases/k23-tree-collision-red/records.jsonl). Run manifest: [run.json](cases/k23-tree-collision-red/run.json). Exact saved output: [observed.stdout](cases/k23-tree-collision-red/observed.stdout).

Positive parent: [existing-k23-tree](cases/existing-k23-tree/). Mutation: `{"file": "records.jsonl", "path": ["cert", "witness", "tree", "move", "pair"], "scope": "record"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/k23-tree-collision-red', '--output', '/tmp/gp10-checkaudit/results/k23-tree-collision-red'])
```

```text
REJECT record DFw tree: R-tree.tree.move.pair: invalid distinct vertices
REJECT run records_rejected
```

### 304. tu-refuted-pointer-map-red

File: [cases/tu-refuted-pointer-map-red/records.jsonl](cases/tu-refuted-pointer-map-red/records.jsonl). Run manifest: [run.json](cases/tu-refuted-pointer-map-red/run.json). Exact saved output: [observed.stdout](cases/tu-refuted-pointer-map-red/observed.stdout).

Positive parent: [run-tu-refuted-pointer](cases/run-tu-refuted-pointer/). Mutation: `{"file": "records.jsonl", "scope": "file"}`.

Executed in-process command:

```python
gp10check.main(['<repo>/research/gp-10/check-audit/cases/tu-refuted-pointer-map-red', '--output', '/tmp/gp10-checkaudit/results/tu-refuted-pointer-map-red'])
```

```text
REJECT record K_?G?cks`M^? map_not_injective: TU refuted end
ACCEPT record C~ verified
REJECT run records_rejected
```

## CODE REVIEW

Reviewed the complete gp10check.py against CONTRACT Sections 3 and 4 and both GP-10 proof documents. Also read the delegated kernel's field construction and complete verify_refutation implementation, plus its local gadget and Heron proofs. Locations below refer to the hashed checker version above.

### MAJOR-1: Required smaller control profiles and the B10 control gate are missing

Locations: `gp10check.py:598-603, 661-680, 700, 720-734, 753-755, 885-887, 924-937`.

CONTRACT Section 10 amendment 1 requires control 7.0 on B4p, B5p, B6p and B7p. Amendment 2 explicitly calls for these checker profiles to be extended.

Each complete frozen family is accepted as a declared-unknown sample, then changing only profile to its required control name yields REJECT run profile. The allowlist, frozen-family logic, minimal output logic and minimal-list comparison only support the older control profiles. B10 controls() requires exactly B8p, B9p, named and regressions, so it also fails to enforce the newly required smaller controls. This is one underlying amendment-coverage defect, not separate findings for each name. A full B10 acceptance without these controls was not constructed.

Evidence: [unsupported-B4p](cases/unsupported-B4p/observed.stdout), [unsupported-B5p](cases/unsupported-B5p/observed.stdout), [unsupported-B6p](cases/unsupported-B6p/observed.stdout), [unsupported-B7p](cases/unsupported-B7p/observed.stdout).

Suggested correction: Implement the smaller profiles, their frozen hashes, in-force lists, exact minimal comparisons and unknown prohibition. Require accepted replays of all smaller control runs before B10.

### MINOR-1: Rational spelling is narrower than the contract's rational-string description

Locations: `gp10check.py:67-73`.

CONTRACT Section 3.1 describes exact rational strings. FORMAT.md adds a more restrictive wire grammar.

The equivalent spelling 0/-1 is rejected as rational, as is surrounding whitespace, while a leading numerator sign and leading zeroes are allowed. Canonical rational strings remain usable. This is a harmless syntax restriction, not a mathematical false rejection for a normalized certificate and not a soundness defect.

Evidence: [signed-denominator](cases/signed-denominator/observed.stdout), [rational-space](cases/rational-space/observed.stdout), [rational-plus](cases/rational-plus/observed.stdout), [rational-negative-zero](cases/rational-negative-zero/observed.stdout), [rational-leading-zeroes](cases/rational-leading-zeroes/observed.stdout).

Suggested correction: Document denominator positivity and whitespace exclusion in the contract or require producers to normalize rational strings.

### MINOR-2: The Sturm branch accepts a nonzero constant as well as a univariate polynomial

Locations: `gp10check.py:280-285, 418-429`.

CONTRACT Section 3.2 R-real says f involves one variable; FORMAT.md explicitly permits a nonzero constant.

A constant identity with f=1 is accepted when an existing variable is named. It involves no variable, but cannot vanish at any real point, so the same contradiction proof is valid. The zero polynomial is rejected. This is a sound extension of the literal wording.

Evidence: [real-constant](cases/real-constant/observed.stdout), [real-constant-zero-target](cases/real-constant-zero-target/observed.stdout), [sturm-constant](cases/sturm-constant/observed.stdout), [sturm-zero](cases/sturm-zero/observed.stdout).

Suggested correction: Say that f is constant nonzero or univariate with no real root in the contract.

### Branch-by-branch assessment

| Area and checker locations | Proof obligation and audit result |
| --- | --- |

| Parsing and graph identity, 56-95, 156-217, 743-813 | Strict keys, finite JSON, integer vertices, canonical graph6, correct map length, injection and edge preservation are enforced. Duplicate keys and duplicate records reject. Noncanonical coverage does not merge aliases. Canonicalization trusts the installed nauty implementation. |

| E-exact, 303-350 | Strict sign change supplies a root. Edge equations are reduced exactly. Exact collisions reject before interval refinement. Every pair shares the same nested interval, and a rational midpoint root is tested against all pairs. No independent root choice per pair was found. Reducible and repeated-root polynomials are permitted when the proof obligations hold, as the contract allows. |

| E-ptr and R-ptr, 487-515, 815-842 | Maps use the correct source-to-target direction. Resolution requires an accepted target with the same required verdict. Missing targets, unknown targets and self-cycles reject. Frozen indices are range checked, checked against the in-force list and bound to the canonical graph. |

| R-tree, 496-503; trusted udcheck.py 585-710 | The exact current graph is passed to verify_refutation. The kernel checks root edges, root row space and subsequent move constraints, rather than trusting witness edges. The run fixtures demonstrate rejection of trees transplanted onto the named UDGs, fabricated row spaces, bad leaves, bad fields and invalid collision pairs. Deeper moves were read but not exhaustively mutation tested here. |

| R-tu, 516-542 | Each step checks its gadget map against the currently augmented graph, its distinguished pair and nonadjacency. The endpoint must contain the actual frozen forbidden member using stored labels, or an accepted refuted target using canonical labels. The asymmetric label tests distinguish these conventions. Earlier and later steps cannot be swapped to borrow future edges. |

| R-null, 353-416 | The checker constructs a frame on an edge and regenerates every generator. No extra pinned vertex or nonedge unit equation can be supplied. The sparse ring has fixed distinct variable names, strict exponent vectors and no duplicate monomials. Expansion checks the identity exactly. Repeated saturation pairs reject; adjacent pairs are allowed because they are redundant, sound equations. |

| R-real, 418-442 and 280-300 | The same regenerated identity must equal f. SOS requires a positive constant and positive weights, then separately checks expansion. Sturm checks the named variable, excludes other variables and handles zero and repeated-root polynomials. A saturation variable is valid because its value in a real embedding is real. No sign or complex-versus-real gap was found in these branches. |

| Coverage and consistency, 761-883 | All nonhost records must match the frozen input set exactly, with no duplicates or embedded/refuted conflicts. The exact unknown file is mandatory. Requested monotonicity comparisons are actually searched; no automatic nonempty sample is promised or required when none is requested. Records may print ACCEPT before a later coverage failure, but the final run decision rejects. |

| Blocks and minimality, 553-569, 885-922 | A nonbiconnected deletion is accepted structurally only after checking block order, forbidden freeness and edge coverage. A forbidden block is not waved through. Biconnected deletions require accepted records. A refuted deletion excludes the parent. Missing deletions, an included nonminimal parent and an omitted minimal graph are rejected. Unknown deletions produce the amended conditional wording and provisional list membership. |

| Control gate, 598-603, 661-680, 720-741, 924-963 | Existing control reports must lie within the run tree and are replayed; a supplied ACCEPT flag alone is not enough. The smaller-profile omission is MAJOR-1. Named search provenance and prediction chronology remain external assertions, clearly identified in the report. claim_authorized remains false. |

Sound implementation choices that are not additional findings: exact rational interval bounds satisfy the certified interval requirement; a strictly checked rational midpoint root proves the same existence conclusion; the field polynomial need not be irreducible for E-exact; ordered unique saturation pairs and nonempty TU chains restrict the wire format without weakening an accepted proof; omitted cofactors mean zero; dictionary keys cannot silently redefine generators. The amended minimality wording is correct and is not the earlier contract ambiguity.

No specific polynomial identity, graph map, proof-tree binding, coverage equality or minimality implication in the exercised paths verified less mathematics than its cited proof requires. This statement is limited by the sampling and trusted components below. The major finding concerns the amended control gate, not a demonstrated invalid geometric verdict.

## UNCERTAIN

The full B10 run and the full accepted B8p, B9p, named and regression control trees were not exercised. The missing smaller controls were demonstrated by rejected profile mutations and source review, not by constructing an accepted B10 run that bypasses them. Input-freeze completeness, forbidden-filter witness replay and independent enumeration were outside this module's job.

Only the copied C4, triangle and Moser embeddings, the generated elementary embeddings and the retained refutation certificates were verified positively here. Fresh embeddings of Petersen, the pentagonal prism and IISpZATaw were not produced. Their role as UDG targets comes from the supplied brief and contract. The forbidden-member sweep uses simple graph-identity mutations; it is not an exhaustive algebraic attack on each member.

The trusted tree kernel's deeper branching moves and all gadget proofs were not re-proved from scratch or exhaustively mutation tested. The direct tree positives mainly close by a rhombus collision. Gadget mutation fixtures primarily exercise the first gadget, although the source review checks the generic path. No CAS producer wrappers were run, so this report says nothing new about msolve or Singular production behavior.

Very large polynomials, extreme integer-string sizes beyond the retained rational fixture, long dependency chains, maximum-sized hosts, killed processes, concurrent file replacement, output-path races and disk exhaustion were not stress tested. The suite removes its own stale evidence before each replay; it does not establish all crash-recovery properties of the production checker.

The least independently checked assumption is the correctness of the trusted kernel and frozen mathematical data, including the external smaller-graph classification used by block_evidence. A hidden soundness defect would most plausibly lie in a deeper delegated proof-tree move, unusual exact-arithmetic boundary, or run/control interaction that needs a full production tree. Many initial certificates were copied from the checker author's fixture set, so agreement on those baselines is correlated; the new field, graph-binding, label-direction, unknown-pointer, block and arithmetic mutations provide additional but finite independence.

Accepted helper return values, accepted declared-unknown samples and the absence of observed false accepts do not authorize a GP-10 classification claim. The startup command deviation is disclosed in VERDICT. All required deliverables for this bounded CHECKAUDIT job are present; the mathematical and production gaps described here remain open.
