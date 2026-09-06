# orchard CNF audit — the four (15,32) cube CNFs, regenerated

Job `orchard-cnf-audit` (coordination/cloud-workers/JOBS.md, 2026-09-05), run on a
cloud worker for `claude-reaching-noether-7e1c`, board scope `maths-big-run`.

The referee panel's point was that drat-trim certifies "this file is UNSAT", not
"this file is the intended cube CNF". This job regenerates the four cube CNFs from
the frozen generator on an independent machine so their bytes can be compared with
what the four cube workers actually refuted.

## Result

| cube | sha256 of CNF | CNF bytes | .zst bytes | vars | clauses | matches worker CNF | cnfcheck |
|------|---------------|-----------|-----------|------|---------|--------------------|----------|
| 0 | `0e6352aaeeef6bebe0c50df4896a4f50b93a5fa6d67503308997ff30e81a7157` | 32,820,609 | 4,151,355 | 262,585 | 1,521,924 | **MATCH** (published 01:25Z) | PASS |
| 1 | `8c33bbfefeae504f2679c3a96e58536a382f5a8e4c3f8e348cee6a2d303ba745` | 14,713,440 | 2,133,149 | 138,233 | 777,572 | **MATCH** | PASS |
| 2 | `9b26b0e5ba1f3d6e4f7c9bcb4256a31c05086d53ba81292e8d5324b07d14cbac` | 16,822,040 | 2,344,829 | 152,713 | 864,252 | **MATCH** | PASS |
| 3 | `3ce6b8b9e17d4ceadcca205612c0692a85374c53328aab343eb0951970a49417` | 13,766,012 | 2,012,299 | 131,725 | 738,624 | **MATCH** (kissat worker, 02:32Z) | PASS |

The "matches worker CNF" column is byte equality with the CNF that worker actually
committed, not merely with a hash it recorded. The `cnfcheck` column is
`cnfcheck.py`'s decode check on the regenerated file; every worker CNF found was run
through it separately and also passed (see the update at the end of this file).

Cube listing agrees with the workers' partition: 4 level-1 cubes, orbit sizes
[120, 1440, 640, 3840] (sum 6040), stabiliser of point 0's row of order 46080.

### Cubes 1 and 2 are confirmed

Both cube workers committed their compressed CNF, and both decompress to exactly the
byte string regenerated here:

- `claude/reaching-noether-cloud-orchard-c1-xlr95d`,
  `research/orchard-15/chiro/scratch/exist-15-32-c1/`: its `SHA256SUMS.cnf` records
  `8c33bbfe…` for `exist-15-32-cube001.cnf`, and its committed
  `exist-15-32-cube001.cnf.zst` (`df9f8ed7…`) decompresses to `8c33bbfe…`.
- `claude/reaching-noether-cloud-orchard-c2-2mhdop`,
  `research/orchard-15/chiro/scratch/exist-15-32-c2/`: its `VERSIONS.txt` records
  `cnf_sha256: 9b26b0e5…`, and its committed `exist-15-32-cube002.cnf.zst`
  decompresses to `9b26b0e5…`.

These two workers ran from checkout commits `0a23b5f2…` and `1b62e452…`; this audit
ran from `584fbe76…`. Three different checkouts and three different machines produce
identical CNFs, so the encoding is reproducible and the files those two DRAT proofs
refuted are the intended cube CNFs.

### Cubes 0 and 3 were not confirmed by the first pass

**Both superseded** — cube 0's worker published its CNF at 01:25Z, and a kissat
replication worker published cube 3's at 02:32Z; both are now confirmed. See the two
updates at the end of this file. The state as of the first pass (01:20Z) was that
neither branch had committed a CNF or a CNF sha256:

- `claude/reaching-noether-cloud-orchard-c0` committed only `HEARTBEAT-c0.txt`
  (last line `ALIVE 2026-09-05T00:52:23Z uptime=3637 proof_bytes=696022996
  status=checking`) and its two heartbeat scripts. The `CNF sha256` lines in that
  branch's `REPORT-EXIST.md` belong to the smaller non-cube runs (8,8), (10,13),
  (12,20), (13,24), (14,28) — none is a (15,32) cube.
- `claude/reaching-noether-cloud-orchard-c3-ikl3d9` committed only heartbeats
  (last `heartbeat: orchard (15,32) cube 3 2026-09-05T01:18:54Z solving`).
- `claude/reaching-noether-cloud-orchard-c0-hhp71k` is unrelated work (linkcheck).

So at the first pass, for cubes 0 and 3 the hashes above were a **reference**, not a
confirmation. Both have since been confirmed against a published worker CNF. The one
residue is that cube 3's confirmation comes from the kissat replication worker, not
from the original cadical worker `…-c3-ikl3d9`, which has still published nothing —
see the 02:45Z update.

## How the CNFs were generated, and one deviation from the brief

The brief (and JOBS.md) asked for

    python3 exist.py 15 32 --backend cadical --cubes --cube-index k --cnf-only

described as solver-free, seconds per cube. That command does not do that. Two problems
in the frozen `exist.py`:

1. `--cnf-only` is honoured **only on the non-cube path** (`exist.py:1193`). With
   `--cubes` the run goes through `run_cubes()` (`exist.py:1045`), which calls
   `solve_standalone()` (`exist.py:1097`) and therefore actually launches cadical with
   a DRAT proof. Running the brief's command as written would have re-run the full
   refutations — hours to days, and proof files in the hundreds of MB to GB — not the
   bounded encoding the job asks for.
2. Independently, `main()` resolves the drat-trim executable for any non-pysat backend
   *before* reaching the `--cnf-only` branch (`exist.py:1174-1182`), so on a machine
   without drat-trim the command dies with
   `RuntimeError: none of these executables was found` before encoding anything. That
   is what happened here first.

Rather than modify the generator this job exists to audit, the CNFs were produced by
`emit_cube_cnf.py` (committed here), which imports the **unmodified** `exist.py` and
replays the steps `run_cubes()` takes — `derive_reduction`, `enumerate_cubes`,
`group_closure`, the `cube_group` stabiliser filter, `build_existence_encoding` with
`lex=False, degree=True, drop_exact_b=False` — then calls the same
`chirosat.write_clauses` at the same path `exist-15-32-cube<kkk>.cnf`. No clause is
re-implemented; every byte comes out of the frozen code.

That equivalence was checked, not assumed. `verify_driver.py` (committed here) runs the
real `exist.run_cubes()` with the real argparse namespace for
`15 32 --backend cadical --cubes --cube-index k`, with only `solve_standalone`'s solver
invocation stubbed out (its CNF write kept verbatim), and diffs the result against the
driver's output. For k = 0..3 the sha256s were identical — `ALL MATCH`. The independent
agreement with the c1 and c2 workers' committed CNFs above is a second, end-to-end
confirmation that the driver reproduces what a real cube run writes.

**Recommendation for the coordinator:** fix `exist.py` so `--cnf-only` short-circuits
inside `run_cubes()` before `solve_standalone`, and so the drat-trim lookup is skipped
when `--cnf-only` is set. Both are small and would make the brief's command do what
JOBS.md says it does. This job did not make that change, to keep the audited generator
byte-frozen.

## Files

- `c<k>/exist-15-32-cube<kkk>.cnf.zst` — the four CNFs, `zstd -19`. All under the 5 MB
  cap (largest 3.96 MiB), so no splitting was needed. Each verified with `zstd -t` and
  by decompressing and re-hashing against `SHA256SUMS`.
- `SHA256SUMS` — sha256 of the four **uncompressed** CNFs.
- `VERSIONS.txt` — python, python-sat, cadical, nproc, checkout commit, provenance.
- `c<k>.log` — the per-cube JSON record (counts, cube orbit data, hash, sizes).
- `emit_cube_cnf.py`, `verify_driver.py` — the driver and its equivalence check.

The uncompressed CNFs (13–33 MB) are not committed; they are regenerable from the
committed generator and driver, and the `.zst` files decompress to the recorded hashes.

No solver was run by this job. cadical 1.7.3 is recorded for the environment only.

---

## Update 2026-09-05T01:44Z — decode checks (cnfcheck.py)

Follow-up pass. `cnfcheck.py` was taken from `claude/reaching-noether-7e1c` (adapted
from the referee panel's `c0check.py`). It decodes a cube CNF and checks it against an
independent recomputation of the intended cube: the header variable count, the unit
clauses (v sign anchors; B true on point 0's row and on cube K's row of point 1; B
false on every other triple through 0 or 1; one prefix-equal start per non-identity
element of G2 = Stab_G1(cube K)), and a semantic test of the lex-leader clauses — those
clauses alone are loaded into a solver and must accept the G2-orbit minimum of a random
block vector and reject a non-minimal orbit element, over 25 random trials.

### Regenerated CNFs — all four PASS

    CNFCHECK PASS cube=0 file=scratch/cnf-audit/c0/exist-15-32-cube000.cnf
    CNFCHECK PASS cube=1 file=scratch/cnf-audit/c1/exist-15-32-cube001.cnf
    CNFCHECK PASS cube=2 file=scratch/cnf-audit/c2/exist-15-32-cube002.cnf
    CNFCHECK PASS cube=3 file=scratch/cnf-audit/c3/exist-15-32-cube003.cnf

25/25 lex trials clean on each, `PROBLEMS: none`, exit 0. Logs in
`cnfcheck-regen-c<k>.txt`.

### Worker CNFs — three found, all PASS and all byte-identical

Cube 0's worker published its CNF at 01:25Z, after the first pass of this audit ran;
the earlier version of this file recorded cube 0 as unconfirmed and that is now
superseded. Rescanning every `claude/reaching-noether-cloud-orchard-c*` branch found
committed CNFs for cubes 0, 1 and 2:

| cube | branch | worker CNF sha256 == regenerated | cnfcheck |
|------|--------|----------------------------------|----------|
| 0 | `…-orchard-c0` | yes | PASS |
| 1 | `…-orchard-c1-xlr95d` | yes | PASS |
| 2 | `…-orchard-c2-2mhdop` | yes | PASS |

Each worker `.zst` also matches the hash that worker recorded for it (c0
`19475e76…` in its `SHA256SUMS`, c1 `df9f8ed7…` in its `SHA256SUMS.cnf`), and c2's
`VERSIONS.txt` records `cnf_sha256: 9b26b0e5…`. The four worker checkouts differ from
each other and from this one (`7457922740…`, `0a23b5f2…`, `1b62e452…`, here
`584fbe76…`), so the encoding is reproducible across machines and commits.

For cubes 0, 1 and 2 the referee panel's objection is now answered end to end: the file
each DRAT proof refuted is byte-identical to a file regenerated independently here, and
that file decodes to the intended cube — right anchors, right fixed rows, and
lex-leader clauses that really do cut orbits to their minima.

Cube 0's worker also committed `SHA256SUMS.proof` recording its DRAT proof as
`9a09e2c3…`; the proof itself (696,022,996 bytes at its last heartbeat) is not
published, so this audit says nothing about it beyond that the CNF it was computed
from is the right one.

### Cube 3 is still open

`claude/reaching-noether-cloud-orchard-c3-ikl3d9` has committed only heartbeats (latest
`heartbeat: orchard (15,32) cube 3 2026-09-05T01:18:54Z solving`) — no
`scratch/exist-15-32-c3/`, no CNF, no CNF sha256 anywhere on the branch. Nothing to
compare. The regenerated cube-3 CNF `3ce6b8b9…` passed cnfcheck and stands as the
reference that worker's file must match. Until it does, an all-cubes UNSAT should not
be claimed to prove t3(15) = 31 on audited ground: three of four cubes are audited, the
fourth is not.

### Scope of what cnfcheck proves

`cnfcheck.py` recomputes the variable layout and the expected units itself, but it
imports `exist.py` for `derive_reduction`, `enumerate_cubes`, `group_closure`,
`apply_to_config` and `apply_to_triple`. So it is an independent check of the *encoding*
— that the file on disk is the cube it claims to be — and not an independent check of
the *cube decomposition* itself. That the four cubes cover the search space is the
argument in REPORT-EXIST.md (Lemma 7), which this job does not re-derive.

---

## Update 2026-09-05T02:45Z — all four cubes now have an audited CNF

Two new worker branches appeared since the 01:44Z pass, both kissat replications
sanctioned by the coordinator (`dd106c8d…`, "cloud workers: sanction kissat
replications of (15,32) cubes 2 and 3"): `…-orchard-c2-kissat` and
`…-orchard-c3-kissat`. Both published their CNF. That closes the cube-3 gap.

| cube | branch | backend | worker CNF sha256 == regenerated | cnfcheck |
|------|--------|---------|----------------------------------|----------|
| 0 | `…-orchard-c0` | cadical | yes | PASS |
| 1 | `…-orchard-c1-xlr95d` | cadical | yes | PASS |
| 2 | `…-orchard-c2-2mhdop` | cadical | yes | PASS |
| 2 | `…-orchard-c2-kissat` | kissat | yes | PASS |
| 3 | `…-orchard-c3-kissat` | kissat | yes | PASS |

Six published worker CNFs across five branches, every one byte-identical to the file
regenerated here and every one passing the decode check. Cube 3's decode shows
`|G2|=12`, 11 prefix-equal starts, 15 anchors, 156 false block units — all as
recomputed independently.

The three CNFs audited at 01:44Z were re-fetched and their committed `.zst` bytes are
unchanged, so nothing was rewritten under the earlier audit.

### One distinction the coordinator should not lose

Cube 3's CNF is confirmed, but it came from the **kissat replication worker**, not from
the original cadical worker `…-orchard-c3-ikl3d9`, which is still solving
(`heartbeat: orchard (15,32) cube 3 2026-09-05T02:33:57Z solving`) and has still
published no CNF and no CNF sha256. So:

- If cube 3's verdict ends up resting on the **kissat** run, it rests on an audited
  file, since that worker published the CNF it is refuting.
- If it rests on **c3-ikl3d9's cadical** proof, that proof is still not tied to any
  audited file. Nothing published by that worker says what it fed to cadical.

Cube 2 has no such gap: both its cadical and its kissat worker published, and both
published the same CNF.

### Proof hashes are now being recorded, but no proof is published

Workers c0, c1 and c2 have each added a `SHA256SUMS.proof`:

    cube 0  9a09e2c3b359a0aeaa865e31783d4177a3b683140c9382ba289bf3d9823f1826
    cube 1  958c8adfa81ae6ff7038945b7aecaf17c6c930ba2c29337ac68306e3ecad98ee
    cube 2  137d0fab58c7035c46e1ac5c5f049ef10867238ce063370b6f1ed09426d65899

The proofs themselves (c0 696,022,996 B; c2 about 2.01 GB) stay on the workers, as
JOBS.md intends. This audit says nothing about them: it establishes only that the CNF
each proof was computed from is the intended cube CNF. Whether each proof actually
certifies UNSAT rests on those workers' own drat-trim runs, which nothing here
re-checks.

### Status at this pass

- cube 0: solve done, drat-trim done (`done, proof 696022996 B` at 02:22Z).
- cube 1: `checking` at 02:33Z.
- cube 2 cadical: solve finished 02:41Z, 2.01 GB proof hashed, drat-trim running.
- cube 2 kissat: `solving`, proof 114,294,784 B at 02:38Z.
- cube 3 cadical: `solving` at 02:33Z, nothing published.
- cube 3 kissat: `solving` at 02:33Z, CNF published.

No cube has a verified UNSAT published yet, so t3(15) = 31 is not established; what is
established is that all four cube CNFs are the intended files.

---

## Update 2026-09-05T03:45Z — first two verdicts land on audited files

No new cube CNF appeared this pass; all four were already audited and nothing was
rewritten. What is new is that cubes 0 and 1 have published verdicts, so for the first
time the audit chain closes end to end on real refutations.

| cube | verdict | checker | CNF the proof was checked against | audited? |
|------|---------|---------|-----------------------------------|----------|
| 0 | UNSAT, `s VERIFIED` | drat-trim `2e3b2dc0` | `0e6352aa…` | yes |
| 1 | UNSAT, `s VERIFIED` | drat-trim `2e3b2dc0` | `8c33bbfe…` | yes |

Both hashes are exactly the files regenerated and decode-checked here. So for cubes 0
and 1 the referee panel's objection is now fully answered: the file is the intended cube
CNF (regenerated independently, decoded, byte-identical), *and* that same file has a
DRAT proof a checker verified.

**The two ties are not equally tight, and the difference is worth keeping.**

- Cube 1 is the stronger one. `exist.py` itself emitted
  `cubes-15-32-depth1.jsonl`, and that single program-generated record carries
  `cnf_sha256: 8c33bbfe…`, `proof_sha256: 958c8adf…`, `proof_verified: true` and the
  checker tail ending `s VERIFIED` together. The program that hashed the CNF is the
  program that ran the checker, so the hash and the verdict cannot have drifted apart.
  solve 4481 s, check 7628 s.
- Cube 0 is looser, and its worker says so plainly. Its container was restarted between
  00:52Z and 01:20Z, killing `exist.py` about 30 minutes into drat-trim, so **no
  program-generated result exists for that run**; drat-trim was re-run standalone on the
  surviving CNF and proof, and `exist-15-32-c0-result.json` is worker-assembled from
  artifacts on disk. Its `_provenance` field states this without being asked, which is
  the right way to report it. The committed `scratch/drat-trim-c0.log` does contain
  `s VERIFIED` with core counts matching the JSON (1,713,366 of 7,337,762 lemmas,
  116,004,456 resolution steps), and its header records parsing a formula with
  **262,585 variables and 1,521,924 clauses** — exactly the audited cube-0 CNF's
  dimensions. But the log names no input path or hash, so it corroborates the identity
  of the checked file without proving it; that link rests on the worker's own
  `SHA256SUMS` and assembled JSON. Cube 0's own `exit_code` is recorded as `null` rather
  than assumed, again correctly — the `s VERIFIED` line is the authoritative statement.

A clean re-run of drat-trim on cube 0 under `exist.py`, or simply capturing the exit
code, would close that last gap. It is a reporting gap, not a reason to doubt the
verdict.

### Still open

- cube 2: cadical `checking` (03:32Z), kissat `checking`, proof 770,721,286 B (03:38Z).
- cube 3: cadical `…-c3-ikl3d9` still `solving` (03:39Z) and still publishing no CNF;
  kissat `solving`, proof 2,136,997,888 B (03:34Z).

Two of four cubes are refuted on audited files. t3(15) = 31 does not follow until cubes
2 and 3 also come back UNSAT — and for cube 3 the verdict should come from the kissat
worker, or `…-c3-ikl3d9` should publish its CNF sha256, since that worker's file is
still tied to nothing.

---

## Update 2026-09-05T04:45Z — cube 2 verified; three of four cubes closed

No new cube CNF this pass either; all four remain audited and unrewritten. Cube 2's
kissat worker finished: `orchard c2-kissat: (15,32) cube 2 UNSAT, drat-trim VERIFIED`
at 03:59Z.

| cube | verdict | solver | CNF the proof was checked against | audited? | tie |
|------|---------|--------|-----------------------------------|----------|-----|
| 0 | UNSAT, `s VERIFIED` | cadical 1.7.3 | `0e6352aa…` | yes | worker-assembled |
| 1 | UNSAT, `s VERIFIED` | cadical 1.7.3 | `8c33bbfe…` | yes | program-emitted |
| 2 | UNSAT, `s VERIFIED` | kissat 4.0.4 | `9b26b0e5…` | yes | program-emitted |
| 3 | — | — | — | — | still solving |

Cube 2's tie is of the strong kind: `exist.py` emitted
`exist-15-32-c2-kissat/cubes-15-32-depth1.jsonl`, and that one record carries
`cnf_sha256: 9b26b0e5…`, `proof_sha256: 94c7a88d…`, `checker_sha256: 92f0aa95…`,
`proof_verified: true` and a checker tail ending `s VERIFIED` together. Its committed
`exist-15-32-cube002.kissat.drat.drat-trim.log` independently shows `s VERIFIED` and a
header parsing **152,713 variables and 864,252 clauses** — exactly the audited cube-2
dimensions. solve 1810 s, check 3367 s.

One detail worth recording, because it is a real strengthening rather than a
formality: kissat's cube-2 proof needed **41,703 RAT lemmas in core**, where cadical's
cube-0 proof had **0 RAT lemmas** (pure RUP). Two different solvers, producing
structurally different proofs, refuted the same audited CNF and both were verified by
the same drat-trim build. For cube 2 that is genuine independent replication, not a
re-run.

### Cube 3 is the only one left, and its two workers are unequal

- `…-orchard-c3-kissat`: `checking`, proof 3,716,998,324 B (04:35Z). It published its
  CNF, and that CNF is audited, so whatever verdict it reports will land on a known
  file.
- `…-orchard-c3-ikl3d9` (cadical): still `solving` at 04:35Z, heartbeating steadily
  every ~9 minutes since 23:51Z — alive, roughly 4h45m in — but it has **still published
  no CNF and no CNF sha256**, after five passes of this audit. Whatever it eventually
  reports will not be tied to any audited file unless it publishes that hash.

Cube 2's cadical worker (`…-c2-2mhdop`) is still `checking` at 04:32Z; when it finishes
it will be a second verdict on cube 2, which is already closed by the kissat run.

Three of four cubes are refuted on audited files. t3(15) = 31 still does not follow:
cube 3 has no verdict from either worker.

---

## Update 2026-09-05T06:05Z — cube 2 doubly verified; cube 1 replicated; the depth-2 surface audited

Three things this pass: two more depth-1 verdicts, and a new and much larger class of
CNF that this audit did not previously cover.

### Depth-1: four verdicts now, on three cubes, all on audited files

| cube | solver | verdict | CNF | audited? |
|------|--------|---------|-----|----------|
| 0 | cadical 1.7.3 | UNSAT, `s VERIFIED` | `0e6352aa…` | yes |
| 1 | cadical 1.7.3 | UNSAT, `s VERIFIED` | `8c33bbfe…` | yes |
| 1 | kissat 4.0.4 | UNSAT, `s VERIFIED` | `8c33bbfe…` | yes |
| 2 | kissat 4.0.4 | UNSAT, `s VERIFIED` | `9b26b0e5…` | yes |
| 2 | cadical 1.7.3 | UNSAT, DRAT verified (04:53Z) | `9b26b0e5…` | yes |
| 3 | — | none yet | — | — |

New since the last pass: `…-orchard-c1-kissat` finished cube 1 (solve 1924 s, check
3520 s, 20,774 RAT lemmas in core) and `…-orchard-c2-2mhdop` finished cube 2 with
cadical. Its committed CNF was re-fetched, decompressed and decode-checked here:

    CNFCHECK PASS cube=1 file=/tmp/wc3/c1k.cnf
    worker cnf sha256 == regenerated: yes (8c33bbfe…)

Cubes 1 and 2 are now each refuted twice, by cadical and by kissat, on the same audited
CNF — with kissat's proofs using RAT lemmas and cadical's cube-0 proof using none. That
is real cross-solver replication.

### Depth-2: 5393 new CNFs, none previously audited — 676 now checked

Cube 3 has been split. Four workers (`…-c3-depth2-w1` … `-w4`) are refuting **depth-2
subcubes**, named `cube003-<j>`, of which `exist.py 15 32 --list-cubes --cube-depth 2
--cube-index 3` reports **5393**. These are different files from the four depth-1 cube
CNFs, so nothing in this audit covered them: cube 3's verification story was about to
rest on thousands of files no independent party had regenerated.

So they were regenerated. `emit_depth2_cnf.py` (committed here) replays `run_cubes()`'s
depth-2 path — `refine_cube(reduction, representatives[3], group_one)`, then for each
child the `cube_group` stabiliser filter and `build_existence_encoding` with
`lex=False, degree=True, drop_exact_b=False` — and calls the same
`chirosat.write_clauses`, hashing and deleting each file so hundreds fit on disk. Every
clause still comes from the unmodified `exist.py`.

Of the 5393, the workers have so far reported **676** subcubes as UNSAT with
`proof_verified: true` and a recorded `cnf_sha256`. All 676 were regenerated here and
compared:

    reported: 676   regenerated: 676
    sha256 MATCH: 676
    sha256 MISMATCH: 0
    variable/clause count disagreements: 0

Per-subcube hashes are in `depth2-c3-regen-SHA256.txt`. The remaining ~4717 subcubes
have not been reported yet; they can be checked the same way as they land.

### But the depth-2 CNFs are hash-confirmed, not decode-checked

`cnfcheck.py` cannot validate a depth-2 file, and this was tested rather than assumed.
Run on a regenerated `cube003-000`:

    false block units: 222 expected 156 match: False
    PROBLEMS: ['false block units are not the complement through points 0,1']
    CNFCHECK FAIL cube=3 file=/tmp/d2/one/cube003-000.cnf

This **FAIL is an artefact of the checker, not a bad CNF**. A depth-2 cube fixes point
2's row as well as point 1's, so 222 triples through points 0, 1 and 2 are forced false
where the depth-1 checker expects 156. Every other check passed on that same file: 15
anchors, the row-0 and row-1 true block units, `|G2|=12` with 11 prefix-equal starts,
and 25/25 lex-leader trials clean.

**Recommendation:** extend `cnfcheck.py` to `--cube-depth 2` — take the expected true
block set from the full child (both fixed rows) and the expected false set as the
complement through points 0, 1 and 2. Until then, depth-2 subcubes have the weaker
guarantee: byte-identical to an independent regeneration, but not independently decoded.
Anyone reading a depth-2 `CNFCHECK FAIL` should not treat it as a finding.

### Status

- cube 3 cadical `…-c3-ikl3d9`: still `solving` at 05:41Z, ~5h50m in, still no published
  CNF or CNF sha256 after six passes of this audit.
- cube 3 kissat: `checking`, proof 3,716,998,324 B (05:34Z).
- cube 3 depth-2: 676 of 5393 subcubes refuted so far.

Three of four depth-1 cubes are refuted on audited files. t3(15) = 31 still does not
follow.

---

## Update 2026-09-05T06:55Z — depth-2 audit keeps pace: 1521 of 5393

No new depth-1 CNF this pass. The depth-2 front advanced, and the audit followed it.

    reported total: 1521   regenerated total: 1521
    sha256 MATCH: 1521
    sha256 MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256 among regenerated: 1521

845 subcubes were newly reported since the 06:05Z pass; all were regenerated here from
the unmodified `exist.py` and all matched. Two extra checks this time:

- **The 676 hashes checked last pass are unchanged** in the workers' current records —
  none was rewritten, none disappeared.
- **All 1521 sha256 are distinct.** No subcube has been reported twice under two names,
  which would have inflated the coverage count without adding refutations.

`depth2-c3-regen-SHA256.txt` now carries all 1521. Coverage of cube 3's depth-2
decomposition stands at 1521 / 5393 ≈ 28%.

### Cube 3's cadical worker has finished solving

`…-orchard-c3-ikl3d9` moved from `solving` to **`checking`** at 06:38Z — its cadical
solve is done and drat-trim is running, after about 6h45m. It has still published no CNF
and no CNF sha256. When its verdict lands it will be the only depth-1 refutation in this
whole run not tied to an audited file, unless it publishes that hash. One line in a
`SHA256SUMS` would fix it.

`…-c3-kissat` is still `checking` its 3,716,998,324 B proof (06:35Z).

### Where the whole thing stands

- Depth-1 cubes 0, 1, 2: refuted and verified on audited CNFs — cubes 1 and 2 twice
  each, by cadical and by kissat.
- Depth-1 cube 3: no verdict yet from either of its two workers.
- Depth-2 subcubes of cube 3: 1521 of 5393 refuted, every one on a CNF byte-identical to
  an independent regeneration here — but hash-confirmed only, not decode-checked, since
  `cnfcheck.py` is depth-1-only (see the 06:05Z update).

t3(15) = 31 still does not follow.

---

## Update 2026-09-05T07:55Z — depth-2 coverage 2390 of 5393 (44.3%)

No new depth-1 CNF, and no depth-1 verdict this pass. Both cube 3 workers are still
running drat-trim: `…-c3-ikl3d9` `checking` at 07:34Z, `…-c3-kissat` `checking` at
07:35Z on its 3,716,998,324 B proof.

Depth-2 advanced by 869 subcubes; all were regenerated here and all matched.

    reported total: 2390   regenerated total: 2390
    sha256 MATCH: 2390
    sha256 MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 2390 of 2390

The same two guards as last pass held again: none of the 1521 hashes checked earlier
changed or disappeared from the workers' records, and every hash is still distinct.

`…-c3-ikl3d9` has now been `checking` for over an hour and has still published no CNF
and no CNF sha256 — eight passes in. Nothing else to add to that; it is recorded here
so the gap is not silently inherited by whoever writes up the result.

---

## Update 2026-09-05T08:55Z — depth-2 coverage 3256 of 5393 (60.4%)

Again no new depth-1 CNF and no depth-1 verdict. Both cube 3 workers are still in
drat-trim: `…-c3-ikl3d9` `checking` at 08:40Z (about two hours in the checker now),
`…-c3-kissat` `checking` at 08:35Z.

Depth-2 advanced by 866 subcubes, all regenerated here and all matching.

    reported: 3256   regenerated: 3256
    sha256 MATCH: 3256
    MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 3256 of 3256

Every depth-2 record so far carries `verdict: UNSAT` and `proof_verified: true` — 3256
of 3256. The two guards held again: no previously checked hash changed or vanished, and
no hash is repeated.

Coverage of cube 3's depth-2 decomposition has passed halfway. At roughly 860 subcubes
per hour the remaining 2137 would be reported in about two and a half hours, though
that rate is the workers', not a commitment.

---

## Update 2026-09-05T09:55Z — cube 3 verified: all four cube CNFs refuted on audited files

`…-orchard-c3-kissat` reported at 09:05Z: **cube 3 UNSAT, drat-trim VERIFIED**. That is
the fourth and last depth-1 cube, and it landed on the audited file.

    cnf_sha256: 3ce6b8b9e17d4ceadcca205612c0692a85374c53328aab343eb0951970a49417
    verdict: UNSAT   proof_verified: true
    proof_sha256: a4bf1e90…   checker_sha256: 92f0aa95…
    solve 7198 s, check 16289 s
    checker tail: 21,318,798 of 32,951,340 lemmas in core,
                  1,577,747,488 resolution steps, 22,394 RAT lemmas, s VERIFIED

Program-emitted by `exist.py`, so the hash and the verdict are in one record. Its
committed `exist-15-32-cube003.kissat.drat.drat-trim.log` independently shows
`s VERIFIED` on a formula of **131,725 variables and 738,624 clauses** — exactly the
audited cube-3 dimensions.

### The complete depth-1 picture

| cube | solvers that refuted it | CNF | audited | record |
|------|------------------------|-----|---------|--------|
| 0 | cadical | `0e6352aa…` | yes | worker-assembled (container restart) |
| 1 | cadical **and** kissat | `8c33bbfe…` | yes | program-emitted (both) |
| 2 | cadical **and** kissat | `9b26b0e5…` | yes | program-emitted (both) |
| 3 | kissat | `3ce6b8b9…` | yes | program-emitted |

Six verified refutations over four cubes. **Every one was checked against a CNF
byte-identical to a file regenerated independently here from the frozen generator, and
each of those four files passed the `cnfcheck.py` decode test.** The referee panel's
objection — that drat-trim certifies "this file is UNSAT", not "this file is the
intended cube CNF" — is answered for all four cubes.

### What this does and does not establish

It establishes: no rank-3 chirotope on 15 elements whose zero set is a PTS(15,32)
exists with point 1's row in the orbit of representative k, for each k = 0, 1, 2, 3, and
the file proving each of those is the intended one.

It does **not** by itself establish t3(15) = 31. Two things sit outside this audit:

1. **That the four cubes are exhaustive.** This is REPORT-EXIST.md Lemma 7, plus the
   symmetry break of Lemma 3/4/8. Nothing here re-derives it, and `cnfcheck.py` imports
   `exist.py`'s own group machinery, so it does not independently confirm the
   decomposition either — only that each file is the cube it claims to be. This is now
   the single largest unverified link in the chain and deserves a referee of its own.
2. **The pseudoline-to-orchard bridge.** Getting from "no such chirotope" to
   t3(15) = 31 is the argument recorded on the coordination branch (Folkman–Lawrence,
   Kelly–Rottenberg, the BGS bound). Also untouched here.

Two smaller residues, both already recorded above: cube 0's record is worker-assembled
because its container restarted mid-check (its committed log carries `s VERIFIED` and
the right formula dimensions, but names no input hash), and cubes 0 and 3 each rest on
a single solver where cubes 1 and 2 have two.

### Cube 3's other two attacks continue

- `…-c3-ikl3d9` (cadical): still `checking` at 09:36Z, and still no published CNF or CNF
  sha256. Its verdict, when it lands, will corroborate cube 3 with a second solver — but
  will be tied to no audited file unless it publishes that hash. That request is now
  eight passes old.
- Depth-2: 4107 of 5393 subcubes (76.2%) reported UNSAT, all regenerated here, all
  matching.

      reported: 4107   regenerated: 4107
      sha256 MATCH: 4107   MISMATCH: 0
      variable/clause count disagreements: 0
      distinct sha256: 4107 of 4107

  With cube 3 now settled at depth 1, the depth-2 run is no longer the critical path; it
  is an independent second decomposition of the same cube, which is worth having.

---

## Update 2026-09-05T10:55Z — depth-2 at 4832 of 5393 (89.6%)

Nothing new at depth 1: no new CNF, no new verdict. `…-c3-ikl3d9` is still `checking` at
10:33Z — around three hours in the checker now, and still no published CNF or CNF
sha256.

Depth-2 advanced by 725, all regenerated here and all matching.

    reported: 4832   regenerated: 4832
    sha256 MATCH: 4832   MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 4832 of 4832
    remaining: 561

All 4832 carry `verdict: UNSAT` and `proof_verified: true`. Both guards held again.

When the last 561 land, cube 3 will have been refuted twice over by two different
decompositions — once as a single depth-1 cube (kissat, verified 09:05Z) and once as
5393 depth-2 subcubes — with every CNF in both attacks matching an independent
regeneration. That is a stronger position than any other cube is in.

---

## Update 2026-09-05T11:55Z — depth-2 at 5078 of 5393 (94.2%)

Depth 1 unchanged: no new CNF, no new verdict. `…-c3-ikl3d9` still `checking` at 11:38Z
— roughly four hours in the checker, still no published CNF or CNF sha256.

Depth-2 advanced by 246, all regenerated here and all matching.

    reported: 5078   regenerated: 5078
    sha256 MATCH: 5078   MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 5078 of 5078
    remaining: 315

The rate has dropped (725 last hour, 246 this one), which is what one expects near the
end of a fan-out as workers finish their shares at different times rather than a sign of
trouble; all four depth-2 branches are still committing.

---

## Update 2026-09-05T12:55Z — depth-2 at 5236 of 5393 (97.1%)

Depth 1 unchanged. `…-c3-ikl3d9` still `checking` at 12:35Z — about five hours in the
checker, still no published CNF or CNF sha256.

Depth-2 advanced by 158, all regenerated here and all matching.

    reported: 5236   regenerated: 5236
    sha256 MATCH: 5236   MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 5236 of 5236
    remaining: 157

---

## Update 2026-09-05T13:55Z — depth-2 at 5326 of 5393 (98.8%)

Depth 1 unchanged. `…-c3-ikl3d9` still `checking` at 13:40Z — about six hours in the
checker now, still no published CNF or CNF sha256. Its heartbeat is steady, so the
process is alive; drat-trim on a proof of this size taking this long is not itself
surprising (the kissat cube-3 check took 16,289 s).

Depth-2 advanced by 90; 67 subcubes remain.

    reported: 5326   regenerated: 5326
    sha256 MATCH: 5326   MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 5326 of 5326

---

## Update 2026-09-05T14:55Z — the depth-2 decomposition of cube 3 is complete and fully audited

The last 67 subcubes landed. Every one of cube 3's depth-2 children has now been
refuted and independently checked here.

    reported: 5393   regenerated: 5393
    sha256 MATCH: 5393
    MISMATCH: 0
    variable/clause count disagreements: 0
    distinct sha256: 5393 of 5393
    index coverage: 0..5392, contiguous, no gaps

All 5393 carry `verdict: UNSAT` and `proof_verified: true`. Across fifteen passes no
previously checked hash ever changed or disappeared, and no hash was ever repeated.

**The contiguity check is worth stating separately.** `exist.py 15 32 --list-cubes
--cube-depth 2 --cube-index 3` reports 5393 children, and the workers reported exactly
indices 0 through 5392 — so every child the generator produces was accounted for, with
none skipped and none invented. That is an independent check on the *bookkeeping* of the
depth-2 fan-out. It is not a proof that `refine_cube`'s children exhaustively cover
cube 3; that is the same kind of orbit argument as Lemma 7, one level down, and remains
outside this audit.

### Cube 3 now stands on two independent decompositions

- As a single depth-1 cube: kissat, UNSAT, `s VERIFIED` at 09:05Z, on audited CNF
  `3ce6b8b9…`.
- As 5393 depth-2 subcubes: all UNSAT with verified proofs, on 5393 CNFs every one of
  which matches an independent regeneration here.

No other cube has that. The one thing still missing for cube 3 is the cadical run
`…-c3-ikl3d9`, `checking` at 14:40Z — around seven hours in the checker, heartbeat
steady, and still no published CNF or CNF sha256 after fifteen passes of this audit.
When it reports it will be a third attack on cube 3, but tied to no audited file unless
it publishes that hash.

### The audit's own work is done

Every CNF that any worker has refuted in this run — 4 depth-1 cubes and 5393 depth-2
subcubes, 5397 files — has been regenerated independently from the frozen generator and
matched byte for byte. The four depth-1 files additionally passed the `cnfcheck.py`
decode test; the depth-2 files could not be decode-checked because `cnfcheck.py` is
depth-1-only (see the 06:05Z update).

What remains unverified is unchanged and stated again for whoever writes this up:
Lemma 7 (that the four cubes are exhaustive), the pseudoline-to-orchard bridge, cube 0's
worker-assembled result record, and the fact that cube 0 rests on a single solver.
t3(15) = 31 does not follow from the file-level audit alone.
