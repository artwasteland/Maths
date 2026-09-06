# Measured: `drat-trim -L` buffers the whole LRAT in RAM (affects all four LRAT jobs)

Worker orchard-15-32-lrat-c3, 2026-09-05.

The brief and JOBS.md expect drat-trim on the 3.7 GB cube-3 proof to peak "near 5 GB"
of RAM, which is what AUDIT-15-32.md records (~4.8 GB) for the earlier kissat-proof
check. That figure is for a run WITHOUT `-L`. It does not hold when emitting LRAT.

In `drat-trim.c`, `lratAdd()` appends every LRAT element to an in-memory table:

    void lratAdd (struct solver *S, int elem) {
      if (S->lratSize == S->lratAlloc) {
        S->lratAlloc = S->lratAlloc * 3 >> 1;      // grow 1.5x, realloc
        ...

and nothing is written to the LRAT file until `printProof()` runs at the end of
verification (`printLRATline()`, then `fclose (S->lratFile)`). So the LRAT file stays
0 bytes for the whole check and the accumulated proof lives in RSS.

Measured on this run (3.7 GB DRAT, single drat-trim process):

| wall clock into check | RSS |
|---|---|
| 212 s | 4.49 GB |
| 1981 s | 5.66 GB |
| 3037 s | 6.30 GB |
| 3308 s | 6.48 GB |
| 5081 s | 7.63 GB (VSZ 9.46 GB) |

i.e. roughly the ~4.8 GB baseline plus a steadily growing LRAT table. Two consequences
for the fleet:

1. **Sizing.** An LRAT job needs materially more RAM than the same check without `-L`,
   and the growth is in the checker, not the solver. The 1.5x `realloc` also means a
   transient of up to ~2.5x the table size at each growth step, when the old and new
   buffers can both be live.
2. **Disk and RAM peaks are sequential, not simultaneous.** RAM peaks at the end of
   backward checking; the LRAT file is written only afterwards. So a swapfile bought
   with disk trades against the space the LRAT write will need, and the two needs do
   not overlap in time.

This worker chose a 6 GB swapfile rather than the briefed 12 GB, because disk here is
25 GB total and a 12 GB swapfile would have left ~13 GB for a 3.7 GB DRAT plus a
multi-GB LRAT. On the numbers above that now looks like the right side of the trade:
RAM+swap is 22 GB against a current 8.4 GB used, and 16 GB of disk remains for the
LRAT write. Swap has not been touched at any point so far.

Cubes 0-2 have smaller proofs and should be well inside limits; cube 3 is the one to
watch. If an LRAT job is OOM-killed, this is the first thing to check.
