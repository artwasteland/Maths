# Brief: blind from-definition enumeration

Read DEFINITION.md in this directory: verbatim definitions of two integer
sequences about change-ringing on 5 bells.

Write a from-scratch, single-file C program `enum.c` that computes BOTH
sequences for lengths L = 1..13 by direct enumeration (a simple DFS over
sequences of permutations is fine). You have deliberately NOT been given any
published values, and you must not try to look any up (no network access
anyway). Your output will be compared externally by someone else.

Read the definitions carefully and record in `NOTES.md` every interpretation
choice you had to make. In particular: for the cyclic variant, does the
repeated starting permutation at the end count toward the length? Justify your
reading from the definition text itself, e.g. by working out what each reading
implies for tiny lengths like n=1 and n=2, and state which reading you
implemented (implementing both and printing both columns is even better).

Also derive carefully what moves are allowed between consecutive permutations
by criterion 1 (each bell stays or moves by at most one place, and the result
must again be a permutation).

Compile with `gcc -O2 -o enum enum.c`, run with `nice -n 19 ./enum` (single
thread). Print a table: L, path_count, cyclic_count (one or two cyclic columns
per your NOTES.md) for L = 1..13. Keep total runtime under ~3 minutes; if
L=13 would exceed that, stop at the largest feasible L and say so in NOTES.md.
Write the final table to `RESULTS.txt` and your reasoning to `NOTES.md`.
