# Incident: the disk guard unlinked the DRAT proof and exist.py then failed

Worker orchard-15-32-lrat-c3, 2026-09-05 15:36-15:37Z. Written by the worker that caused it.

## What happened

drat-trim buffers the whole LRAT in RAM and writes it in one burst at the end
(NOTE-lrat-memory.md). The burst here wrote 16.06 GB at roughly 130 MB/s, i.e. it could
consume the machine's entire remaining disk between two 60 s monitor polls. Free disk was
16 GB. To stop the write dying of ENOSPC after a 5.5 hour run, this worker armed
`/tmp/disk-guard.sh`, polling every 5 s, to unlink the 3.7 GB DRAT proof if free disk fell
below 6 GB.

It fired, correctly and as designed:

    2026-09-05T15:36:51Z disk 6133176kB < 6291456kB; unlinking DRAT proof to protect the LRAT write
    2026-09-05T15:36:51Z freed; disk now 9760916kB

The LRAT write then completed: 16,063,366,058 bytes, with 3.9 GB of disk to spare. Without
the guard it would have hit ENOSPC at about 15:36:55Z.

## The mistake

The guard's justification checked that drat-trim had closed the proof (`/proc/13622/fd`
held only /dev/null, the .lrat and two pipes) and that cake_lpr never reads the DRAT. Both
are true. What it did NOT account for is that **exist.py itself touches the proof again
after `run_drat_trim` returns**, at exist.py:1063-1065:

    "proof_bytes": proof.stat().st_size,
    "proof_sha256": file_sha256(proof),

So exist.py died with

    exist: FileNotFoundError: [Errno 2] No such file or directory:
    'scratch/exist-15-32-lrat-c3/exist-15-32-cube003.kissat.drat'

and wrote no JSONL record. That code was read by this worker at the start of the job, to
learn run_drat_trim's argument order, and the post-check `stat`/`file_sha256` two lines
below it was missed. The guard should have been written to unlink only after exist.py had
exited, or to move the proof aside and restore it, or simply to hard-link it first.

## What was and was not lost

Not lost -- the certificate itself is complete and self-contained:

- **drat-trim's verdict, in full**, from the log it writes itself next to the proof
  (`exist-15-32-cube003.kissat.drat.drat-trim.log`, committed). Crucially, exist.py's
  failure happened strictly AFTER `run_drat_trim` returned normally, and `run_drat_trim`
  returns only when the checker exited 0 AND printed an exact `s VERIFIED` line AND printed
  no `s NOT VERIFIED` / `s TIMEOUT` (chirosat.py:424-454). So drat-trim's acceptance is
  established by the program's own acceptance test having passed, not merely by reading
  the log afterwards.
- The proof's **sha256 and byte count**, computed and pushed at 11:54Z, before the guard was
  ever armed: 3,716,998,324 bytes,
  a4bf1e902a73134bfdd2bc75b84d00549b9a1fab2c3f84588317f814ba721983.
- The **CNF** (hash-checked against the audited value, pushed compressed) and the **LRAT**,
  which are the only two inputs cake_lpr needs.

Lost:

- exist.py's own result JSONL line for this run (`cubes-15-32-depth1.jsonl` is 0 bytes).
  The brief's step 7 is conditioned on "exist.py exits with UNSAT and proof_verified true",
  and that record does not exist. Everything it would have contained is available from the
  files above, but it is assembled by this worker rather than emitted by the program, and
  the ledger should say so.
- The DRAT proof file. It is regenerable: kissat 4.0.4 is deterministic on this input (the
  proof produced here was bit-identical to the one the earlier cube-3 kissat worker
  produced on a different machine), so `exist.py 15 32 --cubes --cube-index 3` reproduces
  it in ~100 min. The fleet also already holds a copy with the same sha256.

## Honest assessment

The guard saved the run's expensive artefact and cost a bookkeeping record that can be
reconstructed. That is the better side of the trade, but it was a trade this worker did not
know it was making: the FileNotFoundError was a surprise, not a priced-in cost. A worker
repeating this should hard-link the proof to a second name before unlinking, which costs
nothing and keeps exist.py's `stat`/`sha256` working.

Recommendation for the other LRAT jobs: give the machine enough disk that no guard is
needed. On these measurements an LRAT job on cube 3 wants ~40 GB of free disk (3.7 GB DRAT
+ 16.1 GB LRAT + headroom) and ~14 GB of RAM, against the 26 GB and "up to 5 GB" the brief
assumed.
