# B11 profile interface

Read ../CONTRACT.md and ../PROOFS.md first.
`gp11check.py` lists and marks every change from the frozen verifier.
It imports no producer.
The individual certificate format remains GP-10 check/FORMAT.md, amendments included.
At GP-11, F10 indices are positions in `forbidden-398.json` in that original JSON order, by CONTRACT Section 1
(which re-derives the prefix fact); GP-10's amendment 4 anchors at `forbidden-74.json`, and a global
"10 read as 11" over GP-10's amendments must not keep that anchor (G5 NOTE-2).
F10 indices use the original JSON order; TU endpoint maps use stored labels and
indexed subgraph pointers use canonical labels, exactly as in GP-10.

## Entry points

Use the frozen Python environment and nauty 2.8.8.
All existing profiles (`sample`, B4p..B9p, B10, named, regressions) delegate to
the frozen runner, with identical mathematical verdicts and rejection reasons.
The wrapper additionally records its source hashes on accepted legacy reports.
Legacy B10 still accepts correctly reported partial runs.
`--require-complete-b10` performs the stronger control check after replay and
prints `PASS B10 COMPLETE derived=324` only on exact agreement.

```
python research/gp-11/check/gp11check.py RUN --b11-sha256 FROZEN_SHA256
python research/gp-11/check/gp11check.py B10_RUN --require-complete-b10
```

B11 requires an independent command-line SHA-256, equality with
`research/gp-11/data/B11.g6` and its `data/SHA256SUMS` entry, 448708 canonical,
sorted, distinct biconnected graphs of order eleven, and exact record coverage.
The file may be copied into a run; the bytes must agree with the frozen file.
The externally supplied digest is not taken from the run's own declaration.
G0 is still responsible for enumeration, F10 filtering, anchors and recount.

An example `run.json` (replace the hash and provide the actual files):

```json
{
  "profile": "B11",
  "input": "B11.g6",
  "input_sha256": "<frozen SHA-256>",
  "records": ["records.jsonl"],
  "unknown": "UNKNOWN.g6",
  "controls": {
    "B4p": "controls/B10/controls/B4p",
    "B5p": "controls/B10/controls/B5p",
    "B6p": "controls/B10/controls/B6p",
    "B7p": "controls/B10/controls/B7p",
    "B8p": "controls/B10/controls/B8p",
    "B9p": "controls/B10/controls/B9p",
    "B10": "controls/B10",
    "named11": "controls/named11",
    "regressions": "controls/B10/controls/regressions"
  },
  "predictions": {"path": "PREDICTIONS.md", "sha256": "<SHA-256>"}
}
```

Controls and their report files must resolve below the B11 run directory,
including through symlinks.
Each must already have an accepted `checked/report.json` of the correct profile.
All certificates are replayed in the same invocation before any B11 records are
accepted. A report alone is insufficient.
B10 uses only F9. Its own original eight controls remain mandatory.
Its report must be ACCEPT/verified, have zero unknowns and rejections, be
unconditional, have no conditional minimal members, and derive exactly the 324
ten-vertex canonical members of F10, both in its report and its L10 file.
The first 74 F10 entries are required to equal F9 in order and stored labels.
`F10_provenance` records this comparison; it is never an input axiom.

`named11` contains exactly the two AMP order-eleven extremal graphs, directly
embedded, with the same general-search provenance object as the old named
control. Source graph6 strings supply the instances, not coordinates.
The checker can verify coordinates and prohibit pointers; the assertion that
the search was general is a producer provenance assertion, as in GP-10.
The search command and stats must be retained for review.

`fixture11` is for small fixtures, with optional `derive` and `forbidden_limit`
(default ten) and no controls/predictions. It never certifies the F10 premise or
B11 completeness. Its report says `scope: fixture-only`; the writer refuses it.
Its list is `minimal.g6`, never `L11.g6`.
Direct `Checker(10)` calls likewise test individual certificates under the F10
premise, not the provenance of that premise.
`fixture11` inputs must have exactly 11 vertices, as B11's do (the order check in `load_input` applies to every
profile; G5 MINOR-2, documented rather than changed so the profile keeps its reviewed hash). Smaller
fixtures use the frozen GP-10 profiles.

## Outputs and minimality

B11 writes `checked/L11.g6`, `minimality.jsonl`, the counts, the conditional
minimal members, unknown budgets, and per-record verdicts as GP-10 does.
Every edge deletion is reconstructed from the actual graph.
Blocks through order ten are explicitly searched through order ten, regardless
of the inherited forbidden-search default of nine.
Refuted deletions rule out minimality.
Unknown deletions retain the exact status
`minimal_if_all_listed_deletions_embed` and the report remains conditional.
As in GP-10, the conditional list contains these provisional members.

`ACCEPT` with unknowns is a valid partial check, never G3 or permission to write
a full claim. No checker invocation sets `claim_authorized` to true.
Outputs are invalidated before replay, including L11.g6, and are checked for
collisions with supplied inputs and control outputs.

The B11 report's `artifacts` map hashes every consumed manifest, input,
certificate stream, UNKNOWN list, optional claim/cross-check/provenance file,
predictions file, and all control inputs, plus generated result files and
control reports/lists. Paths are relative to the run root and may use `..` for
external frozen inputs. Control directories and reports must be inside the tree.
Input hashes are checked again at the end of replay to detect concurrent edits.
The writer rehashes the files and reconstructs the required input set.
Receipts identify evidence; they are not signatures against maliciously
fabricated reports or human attestations.

## G6 writer and gate receipt

```
python research/gp-11/tools/write_result.py RUN GATES.json RESULT.md --b11-sha256 SHA256
```

The writer requires an unconditional B11 ACCEPT, all counts/list invariants,
the current profile source hashes and artifacts, complete B10 provenance,
and all nine control receipts. No partial or fixture result can be published.
It writes atomically after all checks and refuses to overwrite evidence.

GATES.json has exactly G0..G5 objects. Every object requires `status: "PASS"`
and a nonempty `evidence` array of `{ "path": ..., "sha256": ... }` referring
to retained evidence, relative to RUN. These are explicit attestations by the
coordinator/reviewer that the corresponding CONTRACT gate is met, supported by
the linked evidence; file existence alone is insufficient. Additional fields:

| Gate | Required fields |
|---|---|
| G0 | `input_sha256`: the frozen B11 digest; evidence covers anchors, replay, independent recount |
| G1 | `sources`: `gp11check.source_hashes()`; `selftest_committed: true` |
| G2 | `predictions_sha256`; `predictions_committed_before_run: true`; evidence includes commit chronology and control logs |
| G3 | `report_sha256`: the final report bytes |
| G4 | `L11_sha256`: the final list bytes; evidence records second certificate counts where found |
| G5 | `sources`: the exact reviewed source map; `outside_reviewer`: nonempty name; `findings_answered: true`; evidence includes review and responses |

The source map includes both frozen checkers, both forbidden JSON files,
gadgets, AMP's graph6 instances, GP-11's contract/proofs, the profile, writer and own-rule selftest.
The writer rejects a stale G5 map even if every gate says PASS.
There is deliberately no command that invents PASS attestations or claims to
prove prediction chronology from certificate timestamps.
