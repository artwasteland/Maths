# udrhombus and the rule integration: tests and results

Built 2026-09-26 by the prover/integration builder for the u(23) supervisor (RHOMBUS-SPEC.md with amendments 1 and
2). The builder's report was delivered as text (a subagent may not write report files); the supervisor wrote this
file from it. Every number comes from the committed `runs/*.txt` of the final run (`run-all.sh`: ALL RHOMBUS TESTS
PASSED on b26e7f12e). Paths are relative to `research/unit-distance-22/`.

## What was built

- `filter/udrhombus.c` and the committed binary `filter/udrhombus` (sha256 718394942c87..., rebuilds byte-identical):
  the rhombus prover (Section 3's contract); graphs up to 32 vertices, strict graph6 (exact length, zero padding, no
  header); `--pair A B` (only to document the gadget certificates); stats line `{"udrhombus_stats":{...}}` with a count
  per failure kind and a `mutant` field; compile-time mutants 1-5 (the production binary is byte-identical without).
- `filter/Makefile`: `udrhombus` target; udrhombus and udtriangle both in `all`; `check-rhombus` (units) and
  `check-triangle` (udtriangle's units, requiring no verify_fail, lift_fail or internal pass; both of udtriangle's
  red-control builds fail it).
- `enum/prune.py`: `--rhombus`, `--triangles` (a rule is one entry of `RULES`: prover option, witness key, count
  prefix, silent-pass fields, mutant field), `--udrhombus`, `--udtriangle`, `--udcheck-rhombus`, `--filter-set`; a
  preflight refusing mutant builds; a three-way count check (prover, certificate file, checker's `<prefix>_tu` /
  `<prefix>_refuted`); `PRUNE_UDCHECK_RHOMBUS` (test-only override, recorded in every manifest, unset by the runbook);
  manifest keys present only with a rule (`<rule>_prover`, `_checker`, `_stats`, `_silent_passes`, counts).
  `filter_set` is recorded only when it differs from the run's set, so default outputs stay byte-identical.
- `enum/run-dag2.py`: `--rhombus`, `--triangles` (from `PRUNE_RULES`), `--prune-filter-set` (74 only together with
  `--verify-stages`).
- `enum/verify-chain.py`: replays a rule run with `check/udcheck_rhombus.py`; refuses a `rhombus` or `tri` witness the
  run's manifests do not record (with or without `--check`); checks the target against its own table of proved
  bounds, and the filter set.
- `enum/PRUNING.md` Section 5 (5.1-5.4 L5: Lemma R, R1, R2, heredity, where the target is checked, the prover, the six
  gadget certificates; 5.5 the controls; 5.6 the filter set; 5.7 `--triangles`).
- `coordination/cloud-workers/u23-slice.sh`: `U23_RHOMBUS=1` (suffix `-rh`), `U23_TRIANGLES=1` (`-tri`, exclusive with
  `-rh`), `U23_PRUNE_FILTER_SET=74` (`-pf74`), `U23_RHOMBUS_CHECKER` (local tests only); every worker's pins include
  both provers and both checkers.

The checker call with a rule:

    nice -n 10 <python> check/udcheck_rhombus.py --expect-n N --expect-m M --graphs <stage input>
      --unknown-file N-M.UNKNOWN.g6 --data-dir data --forbidden-set {74|398} --work-dir <run>/_prune/N-M/check-work
      N-M.certs.jsonl

Chunked above `PRUNE_CHECK_CHUNK` (each chunk its own lists and work directory); the chunked ACCEPT summary carries
rhombus_tu, rhombus_refuted, tri_tu, tri_refuted; the work directory is deleted after ACCEPT, kept after REJECT.

## Results

**(a) Units** (`make check-rhombus`): K2,3 refuted with pair (2,3) (-[0,2,1,4] + [0,3,1,4] = e2 - e3, s = 1); the six
gadgets tu, `--pair` certifying each one's own distinguished pair (the default search finds gadget 4's sibling pair
(3,7), also forced); Moser spindle, unit rhombus, W6 pass; AMP's 56 all pass; deterministic output; 16 tampered
certificates rejected; bad input exits 2.

**(b) B10 positive control**: 32,653 embedded graphs (pinned records): 0 refuted, 9,712 tu, 22,941 pass; every one of
the 9,712 forced pairs is at unit distance in GP-10's exact embedding with f(a)-f(b) = f(p)-f(q) (807 exact
embeddings at 80 digits: worst |d^2-1| 9.7e-74, identity error 6.4e-75; all edges within 1.1e-73; closest pair of
points 0.090). The 509 refuted B10 graphs: 344 tu, 31 refuted, 134 pass.

**(c) Agreement** with `rhombus_probe.py` on 28,500 graphs (w1, w2, w3 at levels 13-18, w1 at 19): 0 disagreements
(17,768 pass, 2,876 refuted, 7,856 tu). `exact-crosscheck.py` (exact rationals, no modulus): verdict, first pair and
first forcing edge equal the prover's on all 28,500; its red controls fail as they should. `make-level19.py`
reproduces the descent log exactly (4,803 children, 2,333 TU-kept).

**(d) Mutants** (dev replay): 1 (3-edge paths as 4-cycles): 51 / 32,645 of known56 / B10 flagged, all false flags
rejected; 2 (distinct-vertex test dropped): 53 / 32,653; 3 (sign flip): 0 / 9,712; 4 (wrong pairing): 52 / 25,593.
The replay accepts only certificates of true statements (graphs the correct prover also flags). prune.py refuses every
mutant build before work. Mutant 5 (corrupting before the self-check) turns all 9,712 B10 detections into
`failure_self_check` passes.

**Binding controls through the REAL checker** (`through-checker.py`): AMP's 55 non-empty graphs accepted, none flagged;
all B10 accepted with rhombus_tu 9,712 = the prover's count, 0 refuted; every mutant's false-flag files rejected (25 of
25 single records per mutant); the int64-wrap certificate rejected (rule 6); a repeated vertex rejected (rule 2); all
28,500 sample graphs accepted with the prover's counts; K2,3 and the gadgets accepted; 16 tampered certificates
rejected, each for the right rule.

**Throughput** (graphs per CPU-second, one core, 201,000 graphs per level): L13 192k, L14 149k, L15 129k, L16 89k,
L17 71k, L18 49k, L19 38k (flagged 10.1 / 19.5 / 30.0 / 48.3 / 58.7 / 73.5 / 83.5 %).

**(e) End to end with the real checker** (`--reach --prune --prune-from 12 --prune-filter-only`, `--verify-stages` in
Mode 398):
- Default off unchanged: (16,41) Mode 398, 488 files (277 byte-identical, 211 JSON-equal after removing timestamps,
  timings, the two scripts' own hashes and hashes of files shown equivalent), Mode 74, 351 files (230 / 121), 0
  different; `test-u23/defaults.py --baseline` passes.
- Controls: (16,41) in both modes, (17,43), (18,46), each plain, `--rhombus`, `--triangles` (12 runs): every known
  graph kept (1, 7, 16); keep files nested tri <= rh <= plain on all 79 pruned levels; `verify-chain --check` CHAIN OK
  on all 12.
- (18,46), plain / rhombus / triangles: keep 13-25 202,186 / 155,781 / 114,587; 14-29 39,251 / 30,085 / 20,971;
  17-41 150 / 94 / 45; top 38 / 35 / 35. Generation above level 12 318.5 / 269.5 / 213.5 core-s; udfilter 100.2 /
  92.1 / 80.3 s; the prover 1.1 s (rhombus), 3.5 s (triangles); the check 30.4 / 34.3 / 40.2 s; wall 414 / 392 / 355 s.
- Red controls R1-R11 fire: tampered certificates and a corrupting prover fail verify-chain or prune.py; bad flag
  combinations and resumes refused; unrecorded witnesses refused (a rule flag stripped from 54 manifests, a `tri`
  witness in a rhombus run, a rhombus witness in a plain run); a prover silently passing 2 detections gives
  `rhombus_silent_passes` = 2 and a warning; targets (18,45) and (13,30) refused by prune.py, a lowered target refused
  by verify-chain; a rhombus witness in a triangles run refused; `--rhombus --triangles` together refused.

**Filter set** (`filterset.py`): (16,41) Mode 398, 86 of 86 level files and 12 of 12 filter outputs identical with
`--prune-filter-set 74`; manifests record `filter_set: 74` and hash both forbidden files; a planted superset
(KGCOYqedCSkJ, containing GP-10 member 363) is caught by the stage verification at (12,24) with -pf74, and by the prune
step as a GENERATOR BUG with the default set.

**Runbook** (`runbook-rh.py`, both rules): `-rh` and `-tri` directories hard-link prefixes only within the same rule;
every worker's pins include both provers and both checkers; every slice CHAIN OK; bad input exits 2 or 3 before work.

## Doubts and follow-ups (the builder's)

- udtriangle's stats line names no build, so prune.py's preflight cannot refuse a red-control udtriangle build (it can
  refuse udrhombus's); a `mutant=` field in udtriangle would close that.
- The udtriangle binary is not committed; workers build it with `make`.
- `check-prune-sample.py` does not know the rules: on a rule run it would report rule-pruned graphs as missing.
- CONTRACT.md needs the Lemma R and T dependencies and the new checker in Section 3 (the supervisor's).
- The builder read only the checker's `--help`, keeping it independent of the prover.
- The (23,65) saving is not measured here; only the (18,46) run shows one.
