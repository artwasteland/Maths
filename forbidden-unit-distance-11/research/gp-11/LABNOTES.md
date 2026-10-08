# GP-11 lab notes (supervisor: claude-answering-alexeev-u22)

Chronological, times AEST (Z = UTC). What happened, including what went wrong. CONTRACT.md is binding.

## 2026-10-01, ~00:30-03:30: the contract, the architect, G0

- Liam (00:25): "the whole 11 vertex mission, within the week. we're going for it. full throttle"; later, "we can make it
  realistic regardless, we just might need to spend quite a bit of our subscription shuffle credits" (codex credits).
- CONTRACT.md written before any producer (ea0139b70b).
- **The architect** (codex, read-only, measurements under /tmp/gp11-architect/; copied to design/): GP-10's embedding
  tools and E-exact already take n = 11; the rigid-system front end, the driver, the checker profile and the lean
  assembler have order-10 limits. On a seeded sample of 500 B11 graphs (seed 20261001): 479 embedded, 8 refuted, 13
  unknown, every decision accepted by the frozen GP-10 checker. Cheap automated pass: about 27 ideal four-core
  machine-hours over B11. Residue before propagation and longer searches: 2.6%, about 11,700 graphs (95% range 6,800
  to 19,700). Its first objection: forbidden graphs rarely settle each other (8 refuted seeds settled 28 graphs,
  against a mean of 394 per embedded seed), so the analyst stage is the critical path.
- **G0 met** (f78aabb3fd, codex builder B): B11.g6 frozen (448,708, sha256 ec9a7109...), geng's biconnected count
  900,969,091 = OEIS A002218(11), the restricted stream 68,232,100 of which 67,783,392 removed; the independent
  matcher reproduces the list byte for byte; all 67,783,392 removal witnesses replayed; red controls at their own rules.
- Running: the escalation measurement (the 13 unknowns at minutes-scale budgets; a second sample of 2,000, seed
  20261002); builder A (the checker's B11 profile); a codex audit of unbound metadata in the u(22), u(23) and GP-10
  results. Submitted to codex cloud as probes of its reliability today: job E (TU closure producer) and job D1 (the
  GP-10 embedding index). The desktop is also carrying other sessions' work (six OCR jobs, a git repack: load 10 on 4
  cores), so new local builders wait.

## 2026-10-01, ~04:35: the escalation measurement (design/ESCALATION-REPORT.txt)

Codex (174 minutes, two processes at most): minutes-scale budgets on the cheap pass's unknowns. **66 of 72 decided (62
embedded, 4 refuted), all accepted by the frozen GP-10 checker.** After escalation: 2 of 500 (0.40%) and 4 of 2,000
(0.20%, seed 20261002) unknown; projected over B11, **about 900 hard cases (95% range 349 to 2,302)** from the larger
sample, not the 11,700 the cheap pass alone suggested. The six survivors look like four embeddable graphs (separation
held under 70-digit refinement; numerical evidence only) and two forbidden ones; propagation settles none of them
(distinct TU closures, no subgraph relations), so each is its own certificate obligation (design/ANALYST-PACKETS.json:
four packets, six obligations). Projected cost of the automated pass: about 100 ideal four-core machine-hours plus 17
hours of serial replay. Surprise: re-basing the degree-2 extension on a different exact B10 embedding gave 10 more
embeddings in 28 seconds, so alternative bases belong in the extender. A week is conditional on analyst throughput,
which is unmeasured; the first packets measure it.

## 2026-10-01, ~05:00: G2's controls pass; predictions committed; the extender landed

- **The B10 control** (CONTRACT 5.1; check/CLOUD-RUNBOOK.md run on the desktop at nice 10, about 70 minutes under
  load): the GP-11 profile, replaying GP-10's whole record stream, printed `ACCEPT run verified` and `PASS B10
  COMPLETE derived=324` (embedded 32,653, refuted 509, unknown 0, conditional false, no rejections), the 324
  re-derived from the 74 and never supplied as axioms (check/results/control-replay-2026-10-01/). Controls 5.2 to 5.4
  (B4p to B9p, named, regressions, named11: AMP's two (11,23) graphs embedded by general search) all ACCEPT.
- **PREDICTIONS.md** committed before any B11 run exists: refuted about 5,200, |L11| about 3,000 (1,500 to 6,000),
  analyst residue about 900.
- **Gates:** G0 met; G1 built and self-tested, its outside review posted to Arturo (waste-drop task 0019, issue #9);
  G2's controls pass with the predictions committed first.
- **The degree-two extender** (e0e706df29): 448 of 500 and 4,534 of 5,000, frozen-checker ACCEPT, about 0.2 s a graph;
  the whole of B11 in an estimated 11 to 17 four-core machine-hours.
- **Blocked:** Claude cloud workers (for the automated pass, about 100 machine-hours) need Liam's OK after the
  classifier refused the u(24) pilot's RemoteTrigger create. Job C (the pipeline and its cloud runbook) is building.

## 2026-10-01, ~08:40: a correction to control 5.1, and the pipeline

**Correction.** The entry at ~05:00 (and commit 601258c057) said controls 5.1 to 5.4 pass. Control 5.1 as the contract
words it is "the full pipeline on B10' ... PASS iff every graph is decided": producers and checker. What ran was the
checker half: the GP-11 profile re-checking GP-10's own certificates and deriving the 324 (never as axioms). The
producer half, the GP-11 pipeline deciding B10' from scratch without reading GP-10's ten-vertex answers (bases restricted
to order at most nine), has not run. 5.2 to 5.4 stand. G2 is not met until 5.1's producer half runs, or the contract is
amended (dated, in Section 7) to say what a withheld-answer control at n = 10 can reasonably require, given that GP-10's
own hard residue needed 35 analyst sessions.

**The pipeline (job C, codex, timed out at 4 hours before its final report; its REPORT.txt stands):** research/gp-11/
pipeline/ (store, scheduler, poset, stages in the architect's order, propagation, export, shard merge, repeat rounds, a
cloud runbook). From empty state it reproduces the references: the architect's 500 (490 E, 8 R, 2 U) and the
escalation's 2,000 (1,977 E, 19 R, 4 U), complete replays ACCEPT; resume after SIGKILL byte-identical; controls at their
own rules. Cost: about 106 four-core machine-hours for the first cloud wave plus about 60 serial hours of coordinator
merge (repeated exact arithmetic), budget about 200; about 315 with one repeat wave. The serial merge is worth
parallelising before the run. The builder's own notes (development failures and fixes) are in pipeline/BUILD-NOTES.md;
its forecasts, written before its population pass and agreeing with PREDICTIONS.md, in pipeline/BUILDER-FORECASTS.md.

## 2026-10-01, ~11:15: the probe, frontier wave 1, the late stages, and the endgame without the serial merge

**Probe g00** (a Claude cloud worker, the escalation's 2,000-graph sample, full policy): all four shards replayed ACCEPT
and pushed. Graph by graph against the desktop reference: same assigned set, 1,977 embedded and 19 refuted in both (the
same 19), zero embedded/refuted flips; of the reference's 4 UNKNOWN, the cloud embedded 2. Over the 76 graphs that
survived the cheap stages, the later stages cost about 61 lane-seconds each.

**Wave 1** (coordination/cloud-workers/JOBS.md, `## gp11-frontier`): the 17,505 B11 graphs the desktop's cheap pass had
not decided at 00:57Z (pipeline/cloud/f1-input/, a superset of that pass's eventual frontier: the pass is still running
and decides about 86% of what its extension stage reaches), 192 shards, eight per worker; 19 workers running, 5 held
after two classifier refusals until Liam's OK. gp11-frontier.sh now pushes each shard as soon as its replay passes.

**Late stages landed** (the toolsmith, codex, in <repo>): branch_refute.py (R-real-DAG from branch
covers) and subfield_exact.py (E-exact from recognised coordinate fields) decide 4 of the 6 hard survivors and 22 of 74
pre-escalation unknowns, every decision frozen-checker ACCEPT (LATE-STAGES-REPORT.md). Landed as the policies `late`
(a fresh esc-numeric, then the two stages, for a residue that had `full`) and `full-late`; `full` is unchanged, so wave 1
runs one stage list whenever its workers start. Rechecked here: JaICZOo@Wd_ refuted again in 10 s, the same 6,480,258
record bytes. Their certificates run to 6.5 to 7 MB, near the checker's 8 MiB record cap.

**The endgame no longer needs the 60-hour coordinator.** The frozen checker streams records in chunks into SQLite
(gp10check.py load_records/resolve), so one B11 profile run over all 448,708 records fits its 1 GB guard; at GP-10's
measured cloud rate (33,162 certificates in 3,156 s) it is about 12 to 14 hours on one cloud worker. The coordinator's
merge re-verifies every record twice to produce what that run verifies anyway; GP-10 replaced the same step with a
memory-lean assembler (research/gp-10/tools/lean_assemble.py: first decided record per graph wins, propagation over
covers, certificates never held in memory). Two codex builders started 01:10Z: a GP-11 lean assembler (with cross-bundle
pointer-cycle repair and a structural precheck that is not a proof check; the positive control is the frozen checker's
ACCEPT) in <repo>, and control 5.1's producer half (an order-parameterized driver over B10' with F9
in force and bases of order at most nine, a leak guard with its own red control, a sample measurement and a cloud
runbook) in <repo> Running 5.1 rather than amending it: it is also the dress rehearsal of the
assembly and the single final check, at a twelfth of the size.

## 2026-10-01, ~02:30Z: control 5.1's producer half built (not yet run), and the outside-endpoint finding

**Control 5.1 tooling landed** (codex, <repo>, new files only, 443 originals unchanged):
pipeline/control_b10*.py, control51-worker.sh, CONTROL51-RUNBOOK.txt and CONTROL51-REPORT.txt. F9 is the pinned
forbidden-74.json; extension bases are fresh order-nine searches on the graph's own vertex deletions; a leak guard
refuses GP-10's B10 records, the 398-list, any B11 index and any ten-vertex base before search (12 controls PASS,
rerun here from the landed tree). Seeded 200-graph full sample: 196 embedded, 3 refuted, 1 UNKNOWN (IkLPC?FAw) in
2,006 s, sample replay ACCEPT. Cloud plan: 128 shards, about 23 ideal worker-hours (budget about 40), then the residue
(projected about 166 graphs at 1 in 200) through the late stages (`--policy full-late` is now available to it). PASS
is only the checker's `PASS B10 COMPLETE derived=324` with its report; nothing is claimed yet.

**Outside-endpoint finding (blocks the final B11 run as written; fix verified feasible).** The B11 profile admits
non-host records for exactly the B11 graphs. In the desktop pass, 807 TU refutations end in {"refuted": E} with E one
of 179 ten-vertex graphs outside B11 (their certificates imported from GP-10); a B11 run would reject all 807 and
everything propagated from them. Each E contains a ten-vertex F10 member (checked for all 179), so each end rewrites
to {"forbidden": idx, "map": end_map o phi}, which the frozen checker verifies with no outside record. The assembler
builder (round 1: lean_assemble11.py, 448,708 graphs in 88 s and 120 MiB, priority orders both ACCEPT on the 2,000
sample, finding the same four sample cases independently) is building that rewrite as an opt-in, recorded step.

## 2026-10-01, ~02:50Z: the assembler (with the outside-end rewrite) landed; the desktop pass finished its stages

**tools/lean_assemble11.py** (codex, two rounds; unit and red suites rerun here from the landed tree: PASS). First
decided record per graph by seed priority; agreeing duplicates collapse, disagreeing ones abort; cross-seed pointer
cycles repaired from alternatives; outputs records.jsonl + unknown-records.jsonl + UNKNOWN.g6 + hosts.jsonl for a
checker manifest; reads a live pipeline state read-only. `--rewrite-outside-ends` turns every refuted TU end (or
unindexed sub pointer) at a graph outside the input into the first F10 member that embeds in it, with the composed
map in the checker's label convention (stored for TU ends, canonical for indexed sub), each rewrite recorded with
both line hashes. Under the B11 checker's fixture11 profile (same Checker(10), coverage and resolve as B11, exactly
the 2,000 sample graphs, no hosts) both priority orders give 1,979 E / 19 R / 2 U, matching the cloud probe; a
corrupted rewritten map is rejected by the frozen checker (map_not_injective); limit 9 is refused; a support with no
F10 member stays UNKNOWN. Population (structural): embedded 431,476, refuted 3,323, UNKNOWN 13,909, hosts 0; all 807
outside ends rewritten (indices 82 to 396), restoring 1,118 decisions; 517 s, 167 MiB. The sample profile cannot
judge these rewrites (it delegates to GP-10 with F9 only); fixture11 and B11 can.

**The desktop population pass** completed tu, extension and rebase (435,026 accepted rows incl. 179 supports; 13,861
B11 graphs UNKNOWN), then refused to export: `source_changed_during_run`. My landing of the late stages (2076ea8c26)
changed pipeline sources in the worktree the run executed from, and the driver's end-of-run source check failed closed,
as it should. Nothing was lost: the stages and certificates are in the state, now copied out of /tmp to
~/gp11-data/population-cheap-state (certificates.jsonl sha256 ece7653e..., job.json 10f22dba...), and the assembler
reads the state directly. Lesson: never land pipeline source into the tree a live run executes from; run from a
pinned copy.

## 2026-10-01 ~04:25Z: the f1 residue, and a probe of longer clocks (p2, worker g25)

The 228 UNKNOWN graphs of the first 64 f1 shards (3.9%) split two ways by their attempt records. 123 have no
separated numerical seed (esc-branch `no_separated_seed`): refutation candidates, on which every algebraic refuter
(null, real, portfolio, targeted, components) ended in `producer_error:TimeoutExpired` at 60-180 s. The rest have a
seed but no exact certificate; 28 of them had a certificate PROPOSED that the frozen checker could not finish in its
60-180 s (`checker:Deadline` in esc-saturated, esc-saved or esc-pins). Both are clocks, not methods, so `stages.py` gains
an additive policy `long` (fresh esc-numeric, then saturated/saved/pins at 600 s with 900 s checks, then
targeted/null/real at 600 s and components at 900 s; worst case 2.1 h a graph). `full`, `late` and `full-late` are
unchanged. Probe p2: 4 deadline-class and 4 no-seed graphs (deterministic choice in p2-input/probe.json), one worker.
Decision rule, fixed before any result: if at least 2 of the 4 deadline-class graphs are decided, `long` runs over the
whole deadline class of the full f1 residue; if at least 1 of the 4 no-seed graphs is decided, over the no-seed class
too (after round f2's late stages, on what they leave); otherwise the classes go to the late stages and analysts only.
Round f2 (policy `late`) proceeds regardless once wave 1 is in.

## 2026-10-01 ~05:00Z: wave 1 cut short by a 2-hour cap; round f1b

Cloud sessions now stop any background task at 2 hours, and the workers then declined to restart it (JOBS.md,
"2026-10-01 ~04:55Z"). 18 of the 24 wave-1 workers stopped during their second shard batch; f1 holds 70 of 192 shards
(all checked, ACCEPT). Round f1b re-runs the 122 missing shards over the same f1 input and 192-way rule with policy
`full-late` (the late stages in the same pass, since this is a new pass anyway), workers g26..g35, under the
time-sliced brief. The f1 residue rate on the 70 shards back is the same 3.9%; round f2 (`late`) is now subsumed by
f1b for its shards and runs only on the 70 f1 shards' residue.

Round f2 (05:14Z): the 244 UNKNOWN graphs of the 71 f1 shards back by then (round_from_shards.py, the cheap-pass
state excluding none of them), policy `late`, one worker g36 (4 shards). f1b's shards carry their own late stages.

## 2026-10-02: control 5.1 PASSES: `PASS B10 COMPLETE derived=324`

The pre-registered withheld-answer control (CONTRACT.md 5.1): GP-11's producers, given F9 and the graph-only B10 input
but not GP-10's answer, re-derived the complete ten-vertex classification. All 128 shards of round r1 ran on Claude
cloud workers (c01..c04; c05's shards carried by c04); the frozen checker assembled them (sample/F9 intake, B10
profile): 33,130 decided, **32 UNKNOWN** (20 without a separated numerical seed, 12 seeded without an exact
certificate; codex builder C had projected ~33). The 32 went to a blinded analyst campaign
(`research/gp-11/tools/control51_campaign.sh`): one fresh codex context per graph (gpt-6-astra, max effort), in a
bubblewrap workspace holding only a 14-file allowlist (packet, F9, gadgets, the frozen GP-10 checker; no GP-10 B10
records, answers, coordinates or F10/B11 material; a pre-launch scan refuses anything else), two at a time. **All 32
returned a certificate that the frozen checker ACCEPTED independently (profile sample, forbidden_limit 9)**, in about
4.6 hours. The certificates replaced exactly those 32 UNKNOWN lines in a new copy of the assembled run (B10-final), and
`gp11check.py B10-final --require-complete-b10` printed **PASS B10 COMPLETE derived=324** (exit 0, 3,665 s): L10.g6
equals the 324 ten-vertex members of F10, checker-side, after fresh proofs. Evidence: `research/gp-11/control51/`
(final-status.json with artifact hashes, ledger.jsonl, campaign.json pins, final-check.log, checked/{report.json,
L10.g6, F10-provenance.json}, analyst-results.tar.zst = the 32 certificates and provenance). The full working tree
(B10-final, workspaces, runtime) is archived outside the repository.

## 2026-10-03: f1b complete; the frontier residue is 525 graphs; round f3 (policy long) runs locally

f1b returned all 122 shards, every one complete and ACCEPT by the frozen checker's replay (9,736 embedded, 1,089
refuted, 359 UNKNOWN). g29's twelve shards came back twice (its cloud session before the move to the desktop, then the
local re-run), both copies ACCEPT; the cloud copies were used (committed first, never more UNKNOWNs), recorded in
<repo>/f1b-bundles/COLLECTION-f1b.json. With the plan's rule "the f1 copy first" (f1b shards 17, 18,
153, 154, 191 displaced; 10 UNKNOWNs), the 192 shards cover the 17,505 f1 graphs exactly once: 15,291 embedded, 1,606
refuted, 608 UNKNOWN. The f2 (late) and p2 (long) overlays decide 80 and 3 more, leaving **525 UNKNOWN**, every one of
which has been through the full and late stages (records: 15 f1, 349 f1b, 157 f2, 4 p2). Built by
pipeline/coordinator/round_from_rounds.py (codex builder; 17 tests with hand-written expectations, nine fatal paths red
with their guards disabled); input and records in pipeline/cloud/f3-input/ (input.g6 35cc3cbe..., records e91ecef6...,
round.json 4f4b94f3...). Round f3 runs the `long` policy (p2: ~970 s a graph, 3 of 8 decided) over 80 shards, four at a
time on <host> as tag L3 (plan entry), each checked shard pushed to claude/answering-alexeev-u22-local-gp11-f3.
What f3 leaves goes to the analyst campaign, then the final B11 check.

## 2026-10-03: the B11 endgame tools (analyst campaign, residue assembly, final launcher)

A codex builder implemented sections 2-3 of REPORT-gp11-endgame-2026-10-01.md as new files only (no frozen checker,
F9/F10 list, pipeline stage or existing tool changed): tools/b11_campaign.py (the B11 analyst campaign: packets from the
assembled UNKNOWN set, isolated fresh-context analysts, independent admission by the frozen fixture11/F10 checker,
hash-chained resumable ledger, configurable concurrency), b11_check.py, b11_heavy.py, b11_selfcheck.py,
B11-ANALYST-BRIEF.md, b11_residue.py (audited lean assembly over the recorded f1-first selection, the f2/p2 overlays,
all 80 f3 returns and admitted analyst exports, with --rewrite-outside-ends; the final UNKNOWN set must equal 525 minus
f3 decisions minus admitted targets) and b11_final.py (sealed immutable run directory, the nine B11 controls with the
completed control 5.1 tree as B10, the hardcoded B11 digest, the step-5 acceptance conditions; refuses to launch while
UNKNOWN is non-empty except as an explicit <=100-input dry rehearsal). 176 tests pass, 129 guard-disable runs go red;
re-run here: 104 workflow + 38 record tests pass. Report and runbook: research/gp-11/REPORT-gp11-final-2026-10-03.md.
Open before the final run: root has ~14 GB free (the final run needs its payload plus ~12.5 GiB); the launcher requires
a reviewed prediction-chronology attestation (predictions file introduced at 601258c057e, 2026-10-01 04:57 +10, before
the first frontier input 2dcaf813459, 10:58 +10).

## 2026-10-04: stopping f3 early, and analysts on codex cloud

Round f3 (policy long) decided 2 of its first 33 graphs; with Liam's agreement it is stopped early (its remaining
shards may run on Claude cloud after the 2026-10-05 reset) and the analysts start now. Codex builders added, as audited
options of the endgame tools: (1) the stopped-f3 path, tools/b11_stopped.py and `b11_residue.py --not-run`: an f3 shard
with no checked return is NOT RUN and its f3-input records carry forward byte for byte; returned shards must equal
their driver shards exactly; make_packets.py `--round-input/--assembly` builds the carried packets from the round input,
marked NOT RUN; b11_final.py seals the provenance (45 new tests, 37 rejection paths red with their guards disabled;
report research/gp-11/REPORT-gp11-partial-f3-2026-10-04.md). Its dry run with 25 f3 returns assembled all 448,708
B11 inputs: 443,209 embedded, 4,994 refuted, **505 UNKNOWN**, structure OK (~30 min). (2) the codex-cloud analyst
route (Liam 2026-10-04: "yeah let's go codex cloud"): coordination/cloud-workers/codex-gp11.py stages packets into a
minimal standalone base, Cairn launches one codex cloud task per packet (BRIEF-codex-gp11.md, B11-CLOUD-ANALYST-
BRIEF.md: ~45 minutes of search inside the ~60-minute turn), each task returns a verified git bundle, and the desktop
extracts it without running returned code and admits it ONLY through the unchanged `b11_campaign.py admit` (the frozen
fixture11/F10 checker). 196 tests, 123 rejection controls red, a real fixture11 rehearsal (report
coordination/cloud-workers/REPORT-gp11-cloud-analysts-2026-10-04.md).
