# Smoke test of the LRAT / cake_lpr chain (worker orchard-15-32-lrat-c3)

Machine: fresh cloud sandbox, 4 cores, 15 GB RAM, 25 GB free disk. None of the earlier
(15,32) proofs were produced here. Date 2026-09-05, ~10:10Z.

## Toolchain

- kissat 4.0.4, built from source (arminbiere/kissat, --depth 1 clone), `/tmp/kissat/build/kissat`,
  symlinked to `/usr/local/bin/kissat` because `exist.py` locates the solver by name
  (`find_executable`) and has no `--kissat` flag. The symlink target is the built binary, so the
  recorded sha256 is the binary that ran.
- drat-trim, built from source (marijnheule/drat-trim), `/tmp/drat-trim/drat-trim`.
- cake_lpr, built from source (tanyongkiam/cake_lpr) with the shipped `make`
  (`gcc -O2 basis_ffi.c cake_lpr.S -o cake_lpr -std=c99`), `/tmp/cake_lpr/cake_lpr`.
  Its self-test on the shipped `example.cnf` / `example.lpr` prints `s VERIFIED UNSAT`, exit 0.

## The drat-trim wrapper

`chirosat.py:424 run_drat_trim` invokes the checker as

    <checker> <cnf> <proof> -t <time_limit>

so `/tmp/dtl/drat-trim` passes every argument through unchanged and appends `-L <proof>.lrat`:

    #!/bin/sh
    proof="$2"
    exec /tmp/drat-trim/drat-trim "$@" -L "${proof}.lrat"

The LRAT is therefore emitted by the SAME checking pass that produces the `s VERIFIED` line
that `exist.py` accepts; it is not a second, separate run over the proof.

## GREEN: (8,8) end to end

    python3 exist.py 8 8 --backend kissat --artifacts scratch/smoke --drat-trim /tmp/dtl/drat-trim

verdict UNSAT, proof_verified true, 0.25 s total. drat-trim log:

    c 539 of 16566 clauses in core
    c 632 of 18453 lemmas in core using 2637 resolution steps
    c 10 RAT lemmas in core; 0 redundant literals in core lemmas
    s VERIFIED
    c verification time: 0.189 seconds
    [exit 0, 0.193 s]

LRAT emitted: `scratch/smoke/exist-8-8.kissat.drat.lrat`, 125,346 bytes, 1230 lines. Then

    /tmp/cake_lpr/cake_lpr scratch/smoke/exist-8-8.cnf scratch/smoke/exist-8-8.kissat.drat.lrat
    s VERIFIED UNSAT
    [exit 0]

## RED controls, and a finding about cake_lpr's exit code

Four mutations of the verified LRAT, each re-checked by cake_lpr:

| control | mutation | cake_lpr output | exit |
|---|---|---|---|
| RED-1 (briefed) | delete hint line 615 of 1230 (`21965 -607 102 0 21217 0`) | `c Checking failed at line: 893. Reason: clause index unavailable: 21965` | 0 |
| RED-2 | delete the last line (empty-clause derivation) | `c empty clause not derived at end of proof` | 0 |
| RED-3 | truncate to the first half | `c empty clause not derived at end of proof` | 0 |
| RED-4 | LRAT file does not exist | `c Input file: ... no such file or directory` | 0 |
| RED-5 | corrupt one hint value (`21217` -> `21218`) on line 615 | `c Checking failed at line: 614. Reason: clause not empty or singleton after reduction` | 0 |

All five are correctly REJECTED: none prints `s VERIFIED UNSAT`.

**Finding: this build of cake_lpr exits 0 on every one of them, including a missing input
file.** The brief expected a nonzero exit. It does not affect soundness here -- the checker
distinguishes the cases perfectly on stdout -- but it means the acceptance test for a cake_lpr
run must be the exact line `s VERIFIED UNSAT`, and an exit-status test would accept a proof
that cake_lpr rejected, and would even accept a run whose LRAT file was missing entirely.
This is the same shape as hazard 3 in AUDIT-15-32.md (the substring-`VERIFIED` parser for
drat-trim), and the ledger should record cake_lpr verdicts by their line, not their status.
This worker reports both for every run.

## CNF identity gate

The cube-3 CNF regenerated on this machine by `exist.py 15 32 --cubes --cube-index 3`:

    3ce6b8b9e17d4ceadcca205612c0692a85374c53328aab343eb0951970a49417  exist-15-32-cube003.cnf

equal to the audited value in JOBS.md and AUDIT-15-32.md. Pushed zstd-compressed
(2,012,299 bytes; `zstd -dc` round-trips to the same sha256).
