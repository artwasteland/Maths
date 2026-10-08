# Lab notes: u(24)

The programme's running record, newest last. CONTRACT.md is binding; this is what happened.

## 2026-10-01 (AEST, ~00:00-01:00): the standard, the pipeline, the known graphs

**The standard.** Liam accepted the codex strategist's plan (research/unit-distance-23/NEXT-ESTIMATES-2026-09-29.md,
"The standard for u(24)"): one run, every run directory checked before it is deleted, G4 at twice u(23)'s fraction,
reproduction by sample. CONTRACT.md Section 3.

**The pipeline's tables** (commit 6d75df7130, codex builder, reviewed): run-dag2.py u-bar(24) = 72 and u(24) >= 68
(AMP Theorem 1(b)), prune.py UPPER[24] = 69, the runbook taking two overrides. Reach tables of (23,65), (22,61), (21,57)
and (17,43) byte-identical before and after; RUNBOOK PASS and DEFAULTS PASS before and after. The (24,69) table:

    10: 14:2 15:1 16:1 17:0 18:0 19:0 20:0
    11: 17:2 18:1 19:1 20:0 21:0 22:0 23:0
    12: 20:2 21:1 22:1 23:0 24:0 25:0 26:0 27:0
    13: 23:2 24:1 25:1 26:1 27:0 28:0 29:0 30:0
    14: 26:2 27:2 28:1 29:1 30:1 31:0 32:0 33:0
    15: 29:3 30:2 31:2 32:1 33:1 34:1 35:0 36:0 37:0
    16: 33:3 34:2 35:2 36:1 37:1 38:1 39:0 40:0 41:0
    17: 37:3 38:2 39:2 40:1 41:1 42:1 43:1
    18: 41:3 42:2 43:2 44:2 45:1 46:1
    19: 45:3 46:3 47:2 48:2 49:2 50:1
    20: 49:4 50:3 51:3 52:2 53:2 54:2
    21: 54:4 55:3 56:3 57:2
    22: 59:4 60:3
    23: 64:4
    24: 69:5

A real (24,69) prefix (levels 10 to 12, slice 0, JOBS=2 on the desktop) took 739.1 s against (23,65)'s 739.6 s, peak
1.1 GB; all 86 prefix graph and certificate files are byte-identical to (23,65)'s; both G4 replays PASS.

**The known graphs, placed in advance** (`tools/known_slices.py`, 2 minutes). In the (24,69) table, 97,912 of Engel et
al.'s 137,011 configurations are ELIGIBLE (at a table cell, minimum degree at least its k): (22,60) all 35 (k = 3),
(17,40) 4,855 and (18,42) 1,792 (two of the new routes' cells), (19,46) 16,196, (16,36) 12,058, and so on over 29
cells. The tool follows each one's chain of canonical ancestors (the first minimum-degree vertex in nauty's canonical
order deleted, as udenum and enum2 do) down to the seed level: every step admissible (0 violations of the induction
CONTRACT 3 states), and every level-12 ancestor present in the real (24,69) prefix's keep files. So each eligible
graph's slice is known before the run: they lie in 123 of the 1,920 slices, s344 alone holding 60,367 and s50 13,209.
The pilot's 42 slices hold 82,582 of them, so the pilot's known-graph control is a completeness test (found = predicted,
slice by slice), not only a soundness one. Self-test: a k raised above an ancestor's minimum degree gives violations
at that cell; an empty prefix reports all 35 (22,60) ancestors missing.

## 2026-10-01 (AEST, ~01:40): the checker, the worker, the first real slices

**Landed** (71ef545b4a, codex builder, reviewed here): `verify-chain-u24.py` (lean + four marked U24 table edits;
sha256 a231bfc38470...), the check-before-delete worker (`coordination/cloud-workers/u24-worker.sh` execs
`tools/worker.py`), and the known-graph control (`tools/known_graphs.py`). The review here read every path to the
deletion: a failed or missing check, a failed control, a failed push of the result copy or of the receipt, and a later
slice without the prefix maker's passing receipt all keep the run directory. One bug was in the supervisor's own pilot
brief, not the code: the launcher execs into Python, so the brief's `pgrep '^bash ...u24-worker.sh'` would never match
and a worker could start a second copy; fixed before any firing.

**The builder's tests:** 120 of 120 checker comparisons identical to lean on older run directories (stdout, stderr,
status, with and without --check and --from-n); every red control refused at its own rule's exact text, then the clean
evidence re-checked unchanged. Two real (24,69) slices end to end on the desktop at JOBS=2 (pushes disabled):

| slice | runbook s | G4 s | check s | control s | checker peak | receipts |
|---|---:|---:|---:|---:|---:|---:|
| 1907 (made the prefix; whole check, CHAIN OK) | 1,846 | 270 | 476 | 4.5 | 801 MiB | 82 KB |
| 1444 (from level 13, prefix compared) | 444 | 51 | 85 | 4.3 | 152 MiB | 65 KB |

1907's runbook time includes the shared prefix (about 739 s of it at JOBS=2). Neither slice holds an Engel graph,
which is what `known_slices.py` predicts for both (a first agreement between the control and the prediction, on the
empty case).

## 2026-10-01 (AEST, ~02:05): the adversarial review says NOT CLEAR; the pilot waits

A fresh codex reviewer (read-only, `gpt-6-astra` at max) read 71ef545b4a and ran reproductions under /tmp: **NOT CLEAR,
1 FATAL, 4 MAJOR, 2 MINOR**. (1, FATAL) The checker validates graph-certificate relations but no count the summary or
`hashes.json` states is bound to the files: with counts zeroed in a copy of the three-slice (17,43) control, the whole
check passed and the fleet audit reported zero target survivors while the keep files held eight graphs. The worker
must reconcile every count with the checked files before deletion. (2) `U24_SKIP_RUNBOOK=1` could reach deletion
without the result copy pushed or G4 read from its own evidence. (3) The retained result files were never compared
with the checked run directory. (4) A slice resumed before its first push loses the structural records the fleet
audit needs, and the worker then deletes the manifests that hold them. (5) Both known-graph tools could pass having
read nothing (`known_slices.py` is the supervisor's own). Minor: no nonempty order-24 certificate fixture; "induced"
missing in a docstring. The U24 table edits, the 97,912-graph placement and every ordinary deletion path checked out.
Its deepest objection is the one u(23)'s reader's guide already states: checking every exclusion does not certify
that generation missed nothing (G4's sample and the known graphs are partial defences). A codex builder is fixing all
seven with the reviewer's reproductions as red controls; the fixes go back to review before any worker is fired.

**The fatal finding is inherited, so u(23) was checked for it the same night.** u(23)'s empty target does not rest on
counts: in all 1,955 fleet result copies (1,920 slices), the `hashes.json` sha256 of `23-65.keep.g6` is the empty
file's (e3b0c442...) for every slice but s50 (one graph, refuted at the top level); copies agree; every shipped copy
of the file hashes to its recorded value; and the full re-run bound each slice's `hashes.json` hashes to the directory
the G5 checker read. So u(23)'s claim holds under its stated assumptions.

## 2026-10-01 (AEST, ~04:30): the re-review, and a classifier refusal

**The fixes** (ccfce9dc5f): all seven findings of the first review fixed with the reviewer's reproductions as red
controls; the receipt gained a fourth file (.structure.json). **The re-review** (a fresh codex reviewer, reproducing
rather than trusting): all seven CLOSED at the worker; six new defects, all verified by running: (FATAL) the
coordinator's receipt audit compares reported counts with each other (and null with null) instead of measuring the
retained files; (MAJOR) a summary cell missing its prune record skips reconciliation; G4 accepted a replay covering 1
of 41 cells; the exported resume structure is trusted without re-derivation; the audit lets the receipt choose the
mandatory retained files; a copied marker can skip an unrun slice. A builder is fixing all six under one principle:
fail closed, derive what must exist from the configuration and the checked files, measure one side of every
comparison.

**The decision to fire the pilot before those fixes land:** each remaining hole needs an upstream bug to produce its
bad input (a truncated replay, a summary missing a record, a copied marker), the runbook and replay are the code that
ran all 1,920 u(23) slices with G4 PASS, and the fixed coordinator audit re-derives everything from the receipts, so
the worst case is re-running a slice, never a wrong result accepted; the checker and pipeline are unchanged, so pilot
slices still count. The full run waits for the fixed worker.

**The auto-mode classifier refused the first worker's RemoteTrigger create** ("Data Exfiltration"), where the same
payload shape fired the u(23) fleet, refine and repro workers. Not worked around, not reworded to probe (standing rule);
Liam decides.

## 2026-10-01 (AEST, ~05:10): round-2 fixes landed; round 3 cut short by a content filter

**bd1e5bcc1a:** the second review's six findings fixed on one principle (fail closed: derive what must exist from the
configuration and the checked files; measure one side of every comparison), 26 new exact controls, the honest
ccfce9dc5f receipts still accepted. **Round 3** (a fresh codex reviewer) was stopped mid-session by OpenAI's content
filter ("possible cybersecurity risk": the adversarial wording of a maths-verification brief, the same false positive
GP-10's first audit brief hit), so it wrote no report; its notes found three more cases of recorded metadata accepted
without derivation: (1) the prefix maker's receipt passed with its G4 replay in slice mode (levels 13 to 24), so the
seeds and the prefix would never be replayed; (2) a summary's reach k (99 against a derived 4) passed the receipt audit
(the fleet audit caught it); (3) a marker from an earlier worker version was honoured although the current rules reject
its evidence (the coordinator rejects it; fresh cloud sandboxes carry no old markers). A builder is fixing all three,
briefed as soundness testing. The trend across rounds (5, 6, 3 findings, each in the previous round's new code) is the
known one: the checker of the checker becomes the defect source; after this round a targeted verification, not another
open-ended review, before the full run.

## 2026-10-01, ~11:30 AEST: the pilot so far, the whole run fired, and the reproduction sample pre-registered

**Pilot (judge.py over the four pushed branches, 00:45Z):** 14 of 42 slices accepted, 0 rejected, 0 duplicated; G4 PASS
on all 14; known-graph control per slice OK (247 predicted in the accepted slices); target: 0 distinct (24,69) graph6
survivors. Cost: on the 14 random slices the (24,69) run time equals the (23,65) time within noise (deltas from -66 s to
+102 s a slice), and (run + G4 + check + control) / run = 1.37. The ten heavy slices (u01..u10) are still running.

**The whole run** (Liam: "Absolutely, fire whatever is needed cloud agent wise"): `coordination/cloud-workers/
u24-full-plan.json`, on the pilot's worker, unchanged since 2b3c4d9dd0 (checked), so the pilot's slices count. Phase A:
the 1,841 non-pilot slices whose (23,65) wall time was at most 1,800 s, over v01..v40, about 478 worker-hours at the
pilot's 1.37 (about 12 hours a worker); v01..v10 fired 01:21Z, the rest as sandboxes free. Phase B: the 37 heavier
slices (28.6 (23,65) hours), held until the pilot's heavy slices report.

**Reproduction sample (gate G5), pre-registered:** seed 20261003, `sorted(random.Random(20261003).sample(range(1920),
48))`, plus s344 and s1535 (`u24-repro-plan.json`), committed before any reproduction copy exists. Restarted slices
of the main run will be added by dated amendment.

