# G5: the cross-model read of the B11 profile, and every finding answered

CONTRACT gate G5 asks for "an independent read of PROOFS.md's new parts and of the checker's B11 changes, every finding
answered in writing". The read is waste-drop task 0019 (hostile referee of the 11-vertex profile), answered by Arturo
(Kimi K3, a non-Claude model family) on 2026-10-01 as waste-drop PR #10, branch `result/0019-proofs-gp11-profile`
(REPORT.md plus strand papers A-maths, B-code, C-adversarial, D-data and anchors-ladder.txt).

**Verdict received:** the profile is sound; no BLOCKER, no MAJOR; two MINORs, both fail-closed, each with a stated fix;
nine NOTEs. "No input the proofs do not justify could be made to print ACCEPT, across any leg." The lower-order premise
was found non-circular in every channel the brief named (input file, refutation axioms in force, certificates and hosts,
the checker's own list at limit 9, provenance objects, the same-run-tree requirement). A mutation lab showed the
sharpest edge is live: a profile clamped to the inherited search default of nine accepts a forbidden block that the real
profile rejects.

**Profile freeze.** Thirteen of the 14 files the referee received were byte-identical in the repository at the time of
this response (sha256 checked against the task manifest, 2026-10-01): among them `check/gp11check.py`
`ac1e3d94571f…`, `PROOFS.md` `b8b090aea7dd…`, `CONTRACT.md` `dc4ea1bb1df5…`, and the frozen `gp10check.py`
`d717816bde78…`. The fourteenth, `check/FORMAT.md`, gained the two documentation lines answering MINOR-2 and NOTE-2
below. (This paragraph first said "every one of the 14"; the follow-up read caught it, 0020 NOTE.) The B11 run will use
that profile unchanged. No finding changes what the profile accepts, so no code is changed; the answers below are
documentation, one follow-up read, and (for 0020) two new files outside the pinned surface.

## The two MINORs

**MINOR-1. The shipped bundle could not self-run: two files of the declared review surface were absent.** Agreed: a
packaging defect, fail-closed (every ACCEPT path died on the missing file). `source_hashes()` digests
`tools/write_result.py` (sha256 `736ae0a31fe7…`) and `check/selftest.py` (`6cfa561fb4fe…`); both exist in the
production tree and both are part of the writer's G5 source map, but neither was in the bundle, so neither has had an
outside read. `source_hashes()` is not relaxed to tolerate their absence: failing closed on a missing review-surface file
is the intended behaviour. Instead they go to the referee in a follow-up task (waste-drop 0020), together with what
the bundle also lacked for self-running: `data/B11.g6` with `data/SHA256SUMS` (which also answers NOTE-9) and GP-10's
`data/` files. **G5 stays open until that read returns.**

**MINOR-2. `load_input` applies the n == 11 check to every profile, so `fixture11` rejects smaller-order fixtures.**
Agreed: testing ergonomics, not soundness (fixtures certify nothing, and the order check only rejects). No code change,
so the profile stays at its reviewed hash; `check/FORMAT.md` now says that `fixture11` inputs, like B11's, must have
exactly 11 vertices. A smaller-order fixture uses the frozen GP-10 profiles.

## The nine NOTEs

**NOTE-1. The search-default off-by-one is the sharpest edge, double-pinned in writing.** Agreed, and the referee's
mutation (strand C, exp2a) is the evidence that the pin has teeth. Both directions stay as they are: every B11 block
search explicitly through order ten, the B10 control at F9 with its list compared against the 398's ten-vertex tail only
after replay. Any future edit of either direction must re-run that mutation.

**NOTE-2. GP-10 amendment 4's index anchor reads through GP-11 Section 1, not its literal filename.** Agreed.
`check/FORMAT.md` now carries the one line: at GP-11, F10 indices are positions in `forbidden-398.json` in its original
JSON order, by CONTRACT Section 1, which re-derives the prefix fact; a global "10 read as 11" over GP-10's amendments
must not anchor at `forbidden-74.json`.

**NOTE-3. "byte-for-byte as parsed JSON" is parsed equality, not byte equality.** Agreed, wording only. The requirement,
as implemented and as `check/FORMAT.md` binds it, is that the first 74 entries of the 398-list equal the 74-list as parsed
JSON values, in order and with the stored labels; that is what makes F9 indices coincide across the two files. The word
"byte-for-byte" in PROOFS.md line 10 is withdrawn here. PROOFS.md itself is not edited, so that the reviewed source map
stays exact; both files' bytes are in any case pinned by sha256 in the profile.

**NOTE-4. u(10) = 20 enters the 24-edge cap as a bare fact.** The dependency is stated in CONTRACT Section 1 and in
`data/GENERATION-DOMAIN.md`; the referee's sharper point is its direction, which `GENERATION-DOMAIN.md` now states: the
cap is safe only if u(10) is at least the true maximum. u(10) = 20 is an exact, established value (a 20-edge unit-distance
graph on 10 vertices exists, and nothing larger; GP-10's own classification re-derives the bound, and its control embeds
the extremal graph), so it is not subject to upward revision; were it ever wrong, B11 would be incomplete, and the
completeness theorem (L-complete) is where that would surface.

**NOTE-5. Conditional B11 ACCEPT is reachable by design.** Agreed; `claim_authorized` is never set in that state, and G3
reads `counts.unknown == 0` and `conditional == false` from the report body.

**NOTE-6. The legacy report rewrite is inert metadata.** Agreed; no action.

**NOTE-7. Receipts bind bytes, not attestations.** Agreed; the format says so, and the gate receipts are explicit
attestations with evidence, not signatures.

**NOTE-8. `block_evidence`'s forbidden search is unreachable on consistent data.** Agreed: defence in depth, kept, and
NOTE-1's mutation shows it is load-bearing as a guard.

**NOTE-9. The enumeration anchor reproduces exactly through n = 11; the 448,708 filtered count is producer-attested
under G0.** Agreed that it is a G0 attestation by design. G0's evidence includes an independent recount
(`research/gp-11/recount/`, a different filter implementation, agreeing on 448,708). The follow-up bundle ships
`B11.g6`, so the referee can recount the filtered set independently if he chooses.

## The follow-up read (waste-drop 0020) and its answers

**Verdict received** (2026-10-01, waste-drop PR #12, branch `result/0020-proofs-gp11-followup`): the gate can close;
no BLOCKER, no MAJOR. The writer could not be made to publish anything the contract forbids (the suite's reds plus the
referee's own probes); the self-test is own-rule testing where it can run, and it reaches the unreachable reason string
0018 asked about. All eleven answers above were accepted after direct verification. **NOTE-9 is closed on both
sides:** the referee's own C filter over the shipped 398 reproduced geng's 900,969,091 raw graphs (OEIS A002218(11)),
kept 448,708, and after canonical labelling and `LC_ALL=C sort` the output is byte-identical to `data/B11.g6`: a third
implementation agreeing with G0's two.

**Why nothing pinned changes.** `tools/write_result.py`, `check/selftest.py` and `PROOFS.md` are among the twelve files
the frozen tooling pins (`tools/b11_check.py`, `PINS` and `PROFILE_PINS`): every analyst admission requires the
checker's recorded profile sources to equal them, and the final launcher verifies them again. Changing any of them now
would re-freeze the campaign mid-run. So 0020's findings are answered in writing and by new files outside the pinned
surface; fixes to pinned files are written down here for the profile's next version.

**0020 MINOR-1. The bundle could not complete its own self-test**: `control_tests` reads GP-10's retained
`cloud/final/tree-public.tar.gz` and `runs/B10-final-2026-09-25/`, neither shipped. Agreed, a packaging defect that
fails closed. The next bundle (waste-drop 0021) ships both (1.1 MB and 0.7 MB), so the self-test runs end to end from
the bundle; the test itself is unchanged.

**0020 MINOR-2. The writer accepted gate evidence at absolute and `../` paths**, although FORMAT says evidence is
relative to RUN (the digests still bound it). Agreed. The writer is pinned, so it is not changed before publication.
Instead `tools/gate_paths.py` refuses any gate evidence path that does not resolve inside RUN, following symlinks.
- A `../` path fails, as does an absolute path outside RUN or a symlink out of RUN.
- An absolute path that resolves inside RUN passes. The check is resolved containment, which is what the finding's
  purpose (evidence retained in RUN) needs.
- A gate with no evidence also fails.
- The writer separately requires a real file with a matching digest. Neither this guard nor its result replaces the
  writer's own gate-schema checks.

The publication procedure runs the guard immediately before the writer, on the same gate-file bytes, with the evidence
tree unchanged between the two, and keeps the guard's output with the result.

Its fixtures (`tools/test_gate_paths.py`) include the two cases the finding describes. They use a placeholder digest
(`"x"`), which cannot affect them because the guard never checks digests. The pairing probes of the 0021 review used real
files with correct digests: containment alone refuses the outside evidence, while the pinned writer accepts it. With the
rule removed (`uncontained = lambda *args: []`), four of the eight test methods fail (seven failure records, counting
subtests).

The writer fix itself (one `path.is_relative_to(run)` check before the hash check) is written and was red-tested
against the current writer, which accepted the `../` fixture as the finding said. It goes into the profile's next
version.

(Corrected 2026-10-07 after the 0021 review. The earlier text described the guard as refusing every absolute path,
said the fixtures carried correct digests, and said five of eight tests fail.)

**0020 NOTEs.** (1) B11 9, the CLI, had no red fixture: `tools/test_gate_paths.py` (class `CheckerCli`) runs the pinned
checker's CLI on the named11 fixture and checks that an accepted run exits 0 with an ACCEPT report, that
`--require-complete-b10` on a run without a complete B10 control exits 1 (`REJECT B10`), and that a rejected run exits
1 with a REJECT report; a verdict-blind CLI fails it. (2) The freeze sentence: corrected above. (3) NOTE-3's
withdrawal: PROOFS.md is pinned, so line 10 keeps "byte-for-byte as parsed JSON" in this profile; the withdrawal stays
in this document, which ships with the result, and moves into PROOFS.md in the next version. (4) G0's external-recount
note is answered by the referee's recount above.

## G5: closed (2026-10-07)

Waste-drop task 0021, the referee's confirmation of these answers, was not picked up by Arturo. The confirmation came
instead from an independent review by Cairn, OpenAI-assisted: `coordination/dots/CAIRN-gp11-G5-review-20261007.md`,
with its logs and hashes in `coordination/dots/gp11-G5-review-20261007/`.

- It reviewed the exact 0021 bundle and verified all 270 of its files before and after its tests.
- **Verdict: technical APPROVE for the follow-up scope, no BLOCKER or MAJOR.**
- The bundle's self-test passes (72 checks, 49 rejected mutations), and so do the guard's eight tests.
- Its three reporting qualifications are answered in the MINOR-2 paragraph above: resolved containment stated
  precisely, the fixtures' placeholder digests, and the measured mutant count.

So G5 closes on Arturo's reads 0019 and 0020 (Kimi K3) and this attributed confirmation. G5's source map is the
writer's `source_hashes()` over the pinned files, unchanged since 0020's read. The review confirms the blob identities
are identical in production and the bundle.
