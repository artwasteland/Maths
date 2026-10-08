# A second verifier for the GP-11 refutations, written blind

Built 2026-10-07 by a Claude agent as the GP-11 extension of the GP-10 blind verifier (gp10-blind-verifier/). The
official GP-11 checker and its kernel were built by Codex, so the two verifiers come from different model families.

The agent worked only in <repo>/. Its inputs were:
- the written spec (spec/gp-11, spec/gp-10, spec/u22, spec/amp);
- the data (data/forbidden-398.json, data/tu-gadgets.json);
- its predecessor's code;
- the one records file, read as data.

It opened, listed, read and ran no checker, kernel, producer or pipeline code. That means nothing under
research/gp-10/check/, research/gp-11/check/, research/gp-11/tools/, research/gp-11/pipeline/ or
research/unit-distance-22/check/, no *kernel*, and nothing in <repo>/ except
b11-endgame/assembly-1/records.jsonl. It did not search the repository for implementations. The only external program
it ran is the system nauty-labelg, for audits and one red-control construction, never inside a verdict.

The harness would not let the agent write this file ("subagents should return findings as text"). The supervisor wrote
it from the agent's final report, as was done for GP-10, and added the "Checked by the supervisor afterwards" section.

## Result (desktop sample)

A stratified sample of 429 of the 5,264 refuted records. It includes:
- every certificate type, every null and every real record;
- all 20 largest records;
- every TU chain ending at a record;
- random draws (seed 20261007) from every type and tree degree;
- every pointer target.

| type | sample | ACCEPT | REJECT | UNSUPPORTED |
|---|---:|---:|---:|---:|
| tu | 131 | 131 | 0 | 0 |
| sub (R-ptr) | 62 | 62 | 0 | 0 |
| tree | 96 (degree 1/2/4: 21/54/21) | 96 | 0 | 0 |
| null | 41 (all) | 41 | 0 | 0 |
| null-dag | 32 | 32 | 0 | 0 |
| real | 11 (all) | 11 | 0 | 0 |
| real-dag | 56 | 56 | 0 | 0 |
| total | 429 | 429 | 0 | 0 |

No honest record was rejected or unsupported. Timing:
- 97 s wall with 2 workers on the shared 4-core desktop, 171.7 CPU-seconds in total.
- Slowest record: 13.6 s (Jh_@wZ?@Wb_, real-dag, 8.0 MB). Its CPU time matched its wall time, so the cost is
  intrinsic, not load.
- Peak resident memory: 279 MB at most (JoCAhoKH]D?, real-dag, 8.3 MB).

Hashes:
- records sha256 41731c987fade25c26b205fb02c809a2b75461ddeae852869ad61aab2804e114
- verify_refutations11.py 3291138c73f23b2d...
- runs/sample/verdicts.jsonl 587d2589c3743ac0...

## Survey (survey11.py, runs/survey.json)

The file has 448,708 lines and no duplicate graph6: 443,444 embedded (405,540 super, 37,904 exact) and 5,264 refuted.

| refuted type | records | bytes | notes |
|---|---:|---:|---|
| tu | 1,760 | 0.3 MB | 1,626 one-step, 132 two-step and 2 three-step chains. 1,735 end at an F10 member (928 at j < 74, GP's list; 807 at j >= 74, GP-10's 324). 25 end at a refuted record. |
| sub (R-ptr) | 1,590 | 0.2 MB | None has an index. 1,588 point at a tu record, 2 at a tree. |
| tree | 1,099 | 11.8 MB | Field degree 1 (250), 2 (801) and 4 (48, new at GP-11). Up to 75 nodes. Moves: L3 5,500, L1a 4,198, L2 3,951, L1c 1,611, L1b 790. |
| real-dag | 482 | 1,326.8 MB | 412 Sturm, 70 SOS. Up to 256 rows; largest line 8.38 MB. |
| null-dag | 281 | 646.6 MB | |
| null | 41 | 65.3 MB | |
| real | 11 | 34.7 MB | 6 Sturm, 5 SOS. |

Every pointer lands on a refuted record of the file: the 1,590 sub records and the 25 tu chains ending at a record. No
chain is longer than one hop. The targets are 1,588 tu, 23 tree and 4 null-dag records. 204 refuted lines order their
keys g6, verdict, cert; the rest use cert, g6, verdict. 146 refuted graph6 strings contain a JSON-escaped backslash.
All 5,264 refuted graph6 strings are nauty-labelg canonical.

## What was implemented

verify_refutations11.py is the predecessor with every change marked "GP-11:". The tu, tree, null, real, null-dag and
real-dag mathematics is unchanged. New:

- **F10.** forbidden-398.json is used in file order with its stored labels. It is checked three ways:
  - against the contract's sha256 prefix 8e8a81a145f75a65;
  - against the prefix lengths 1, 2, 3, 6, 19, 74, 398 for graphs of at most 4 to 10 vertices;
  - against GP's (vertices, edges) composition for the first 74 entries.

  A TU end at F10[j] accepts j in 0..397. Its ACCEPT reason names the premise: GP's theorem for j < 74, GP-10's result
  for j >= 74.
- **Order.** Every refuted record must have exactly 11 vertices.
- **R-ptr (sub), new.** The keys are exactly type, g6 and map, plus an optional index. The map must send the target H
  (in the labels of its own g6) injectively and edge-preservingly into the record's graph. Without an index, H must be
  an accepted refuted record of the same run. With an index, H must be isomorphic to that F10 member, checked by exact
  backtracking.
- **Pointer resolution across shards.** A sub target, or a TU end at a record, must be an accepted refuted record of
  the run. A missing target, a rejected target, a duplicate record or a cycle rejects. Each record's F10 premises are
  collected through its pointers.
- **scan / check / resolve / run.**
  - scan streams the file once and indexes the refuted lines.
  - check seeks to its own records and verifies each one in a forked process. wait4 measures each record's wall time,
    CPU time and peak memory. Per-record time and memory limits can only produce UNSUPPORTED.
  - --shard i/n deals records to shards by size; --jobs N sets the worker processes. Rerunning check resumes.
  - resolve checks coverage, resolves pointers and writes verdicts and a summary.
  - check refuses a records file whose size differs from the indexed one, and rejects a line that does not hold the
    graph its index entry names.
- **Speed only.** A memo of parsed rational strings; exponent checks with C-level builtins (same rules as before);
  each derivation row's JSON released once its identity has passed.

## Readings of the specification

1. GP-11 keeps GP-10's certificate format and amendments, with 10 read as 11. At B11 the list in force is all 398 F10
   members, indexed in JSON order with stored labels.
2. A pointer target must be a refuted record of the same run. A pointer to an embedded record, or to a graph with no
   record, rejects.
3. **sub with index.** FORMAT asks that H equal the member's canonical form. The verifier checks isomorphism, which is
   what soundness needs. No record uses an index (B11 is F10-free), so this branch is covered by synthetic controls.
4. graph6 canonicity is not part of a verdict; pointers match by exact string. Canonicity is audited separately.
5. **Tree witnesses.** The format is described in a kernel docstring the agent may not read, so the predecessor's
   strict reconstruction is kept unchanged:
   - at every node, the row space of A must equal the regenerated constraint space;
   - the minimal polynomial must be irreducible over Q, with an interval isolating exactly one real root;
   - elements are lists of at most deg coefficients, or {re, im}.

   Degree-4 fields verify under this reading: all 21 sampled, plus the 2 degree-4 red-team source records.
6. Rational strings follow amendment 3. Tree rationals may be integers or strings. JSON key order is not significant.
7. GP-11 PROOFS asks that the first 74 F10 entries equal GP-10's forbidden-74.json byte for byte. That file is not in
   the workspace, so GP's composition was checked instead (see Premises).
8. Out of scope: embedded records, coverage of B11, and the minimality (L11) derivation.

## Red controls (redteam11.py, runs/redteam/redteam11.json): 341 of 341 as expected

Each control mutates a copy of a real record, or builds a synthetic certificate, and asserts the mutant differs from its
source. It then requires REJECT with a reason matching the rule it was aimed at. The 23 source records are ACCEPTED in
the same run, before and after the mutations. 316 controls expect REJECT, 24 expect ACCEPT, and 1 is a recorded
non-rejection.

The five required kinds (40 controls) are all rejected by the intended rule:
- **Matrix entry or cofactor coefficient changed (12):** tree A entries at the root, a leaf, the deepest node and a
  degree-4 L3 child; cofactor coefficients in null, real, null-dag and real-dag records.
- **Derivation row dropped (8):** the last row, and an intermediate row that later rows use.
- **SOS weight changed (2).**
- **Forbidden index shifted (4):** TU ends 3 to 4, 3 to 2 and 84 to 85, and an indexed R-ptr 84 to 85.
- **Transplant (14):** for each of the seven types, onto another refuted record's graph, and onto the record's own
  graph minus an edge the certificate uses.

The rest:
- The predecessor's mutation set, ported to 11 vertices, and its attacks on unit-distance graphs.
- New for GP-11:
  - R-ptr mutations: non-injective or non-edge-preserving maps, missing or broken targets, a self-loop, an index
    mismatch;
  - a genuine two-record cycle (A tu to B, B sub to A, both maps valid);
  - F10 index 398;
  - the order check;
  - degree-4 field and coefficient mutations;
  - a duplicate record;
  - mutations of the F10 data file.
- Positive controls:
  - an indexed R-ptr with labelg-canonical labels, built from a real TU chain;
  - certificates moved onto their own graph plus one edge (null, real-dag, tu, sub). These genuinely refute the larger
    graph and are ACCEPTED.
- End to end through the real command line (scan, check in 2 shards with forked workers, resolve), 45 controls:
  24 mutants, 18 unmutated records, 2 stale-index rejections and 1 refused records file. The one-shot run gives verdicts
  and reasons identical to the sharded path.
- Recorded on purpose: with the digest check switched off, deleting an edge from a 10-vertex F10 member still loads.
  The contract digest is the only guard against that corruption, and it is on in every run.

## Cross-checks (crosscheck11.py, runs/crosscheck/crosscheck11.json): all agree

- graph6 decoding agrees with networkx on all 5,264 graphs.
- The 4-cycle lists agree with an independent count on 300 graphs.
- 8 polynomial certificates (2 per type, covering both SOS and Sturm) were re-expanded in SymPy's pure-Python sparse
  ring. Every identity, SOS expansion and root count holds, and each fails when one coefficient is bumped.
- labelg: every refuted graph6 string is canonical, and a relabelled copy is flagged. The 398 F10 members are
  pairwise non-isomorphic.

## Premises

An ACCEPT rests on two premises besides the certificate itself:
- the gadgets' TU property, which the verifier re-proves on load;
- for a TU chain ending at F10[j], that F10[j] is forbidden: GP's theorem for j < 74, GP-10's result for j >= 74.

In the sample, 263 accepted records are self-contained, 120 rest on GP's 74 only, and 46 use GP-10's 324.

The agent left one link open: whether forbidden-398.json[74:] are exactly GP-10's 324 L10 graphs. Their sorted
labelg-canonical forms hash to a899e36cec0f135f253e0c9942d2fecd29280da44189a01d00752e8a5af971b8
(runs/crosscheck/F10-74-398-canonical.g6). Entries 0..73 hash to
59e7da3d016278b43a1e9f1ac667ec2cdb70e2f7b1c8b12612423d4caec29e81.

## Checked by the supervisor afterwards

- **The open premise link is closed.** GP-10's final L10 list (the B10 control campaign's
  `B10-final/checked/L10.g6`, which is already sorted) has sha256
  a899e36cec0f135f253e0c9942d2fecd29280da44189a01d00752e8a5af971b8. That equals the agent's hash of F10[74:], and it is
  also the `L10_SHA` pinned in research/gp-11/tools/b11_final.py. So entries 74..397 of the 398 list are exactly
  GP-10's 324 minimal forbidden graphs.
- **The full run over all 5,264 refuted records.** The supervisor ran it on the desktop with --jobs 2 (runs/full/):
  5,263 ACCEPT, 1 REJECT, 0 UNSUPPORTED, coverage complete. The one REJECT was JQ`@HKYE]W? (line 409,411, a tree):
  "minpoly must be a list of integers". Its witness writes the field x^2 - 3 with decimal-string coefficients
  (`["-3","0","1"]`, interval `["1","3"]`) where the other 1,098 trees use JSON integers. It also writes the zero
  element as a bare `"0"`, 3,182 times, where every other tree writes `["0"]`.
- **The encoding, resolved from the spec by the agent** (the supervisor sent it the record and nothing else). GP-10's
  FORMAT says the delegated tree witness keeps "its own documented integer-or-rational grammar", so an
  amendment-3 rational string with an integer value is legal where an integer is required. The JSON-integer-only rule
  had been inferred from GP-10's data. The agent read a bare integer-or-rational field element as the element of Q it
  names; the spec does not settle that one. Neither change can produce a false ACCEPT: every A matrix is still compared
  exactly with the regenerated constraint space.
  - Diff: verify_refutations11.py lines 166-175 (`parse_int_tree`), 764-766 (minpoly) and 718-719, 726 (bare
    elements).
  - 16 new controls; the red team is now 357 of 357. Rejected: minpoly "3/2", "x", "1.0", true, "-3/2", and "-2"
    (another field); interval "1.0"; bare elements "x", "1.0", true, "1". Accepted: "-6/2" and "0/5", the record
    re-encoded with JSON integers, and its zeros written as ["0"].
  - New verify_refutations11.py sha256 bdb7051f48463586e1b3d65938b3fe101fb5e7b9f956c037724c7c46def1f41f.
- **The full re-run (runs/full2/): ALL 5,264 ACCEPT, 0 REJECT, 0 UNSUPPORTED, coverage complete.** By type: tu 1,760,
  sub 1,590, tree 1,099, real-dag 482, null-dag 281, null 41, real 11. 1,941 accepted records are self-contained,
  2,205 rest on GP's theorem only, and 1,118 use GP-10's result. 693 CPU-seconds; slowest record 13.2 s; peak 355 MB.
- **Two mutations of the supervisor's design, never seen by the agent** (runs/supervisor-mutations/), both on that
  record:
  - its interval moved to ["2","3"], which does not contain sqrt(3): REJECT, "field: minpoly has no strict sign
    change on the interval";
  - its minpoly changed to x^2 + x - 3, another quadratic field with a root in (1,3): REJECT at the root node,
    "L3 d^2 != 4|a|^2|b|^2 - (|a|^2+|b|^2-|c|^2)^2".

  The unmutated record, run alone, is ACCEPTED.

## Commands

Copy verify_refutations11.py with data/forbidden-398.json and data/tu-gadgets.json, and the records file. The script
reads data/ next to itself, or `--data DIR`. It needs Python 3 with python-flint (0.9.0) and SymPy (1.14.0);
redteam11.py and crosscheck11.py also need networkx and nauty-labelg.

    export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1
    R=/path/to/records.jsonl   # sha256 41731c987fade25c26b205fb02c809a2b75461ddeae852869ad61aab2804e114
    mkdir -p full
    python3 verify_refutations11.py run "$R" --out full/verdicts.jsonl --summary full/summary.json \
        --jobs 12 --mem-gb 8 --timeout 7200
    # sharded: scan once, then check --shard i/n per worker, then resolve
    python3 verify_refutations11.py scan "$R" --index full/index.jsonl
    python3 verify_refutations11.py check "$R" --index full/index.jsonl --out full/part-0.jsonl --shard 0/3 --jobs 4 --mem-gb 8 --timeout 7200
    python3 verify_refutations11.py resolve --index full/index.jsonl --out full/verdicts.jsonl --summary full/summary.json full/part-*.jsonl
    python3 redteam11.py "$R" full/index.jsonl full/redteam11.json --workdir full/redteam-e2e
    python3 crosscheck11.py full/index.jsonl full/crosscheck11.json

`full/summary.json` gives the status, totals, coverage_complete, and not_accepted (the g6 and reason of anything not
ACCEPTED). `run` exits 0 only if all 5,264 records are ACCEPT with full coverage.

## Files (sha256 prefix)

| file | sha256 |
|---|---|
| verify_refutations11.py | 3291138c73f23b2d |
| redteam11.py | a67efd0e3dd224d4 |
| redteam_attacks11.py | 768dd1084f3f0e17 |
| survey11.py | 2d223f44aae7f3ea |
| make_sample11.py | bd5cdffe9c6dce96 |
| crosscheck11.py | 41cdd6a38ea9ef9e |
| runs/index.jsonl | 7440f00ddc1d964d |
| runs/sample/verdicts.jsonl | 587d2589c3743ac0 |
| runs/redteam/redteam11.json | 471a13d94674cefb |
| runs/crosscheck/crosscheck11.json | 2efeb2d10b1498d5 |
