# Brief: independent re-aggregation of the n5-L21 checkpoint

You are an independent verification worker on a mathematics research repo. Your
job: re-derive the final totals of a finished distributed computation from its
raw checkpoint file, WITHOUT using the program's own aggregation code path.

Context: `../count.c` is a multithreaded change-ringing sequence counter. It was
run in job mode (n=5 bells, maxL=21, prefix depth K=6), writing
`../runs/n5-L21.ck`: one line per completed prefix job. `../runs/n5-L21.out`
claims final totals per level L=1..21 (path, cyclic, noncappable).

Do this:

1. Read `../count.c` carefully to learn: (a) the exact checkpoint line format,
   including any job weights; (b) how the graph and the depth-K prefix jobs are
   enumerated (the change-ringing graph on 5 bells; the phi-symmetry dedup;
   weight 1 or 2 per representative); (c) what the deep jobs count vs. what the
   prefix walk itself contributes for small L, so your aggregation covers every
   level 1..21.
2. Write a fresh Python 3 script `reaggregate.py` in THIS directory
   (codex-verify/) that: independently rebuilds the 5-bell change-ringing graph
   (permutations of {0..4}; a move swaps any non-empty set of disjoint adjacent
   pairs); re-enumerates the depth-6 phi-deduplicated prefix representatives
   with their weights; parses `../runs/n5-L21.ck`; verifies the checkpoint
   contains EXACTLY the expected job set (none missing, none extra; if
   duplicate lines exist, learn from count.c how its resuming aggregator
   handles them and do likewise, stating what you found); and aggregates
   per-level totals for L=1..21.
3. Run it (nice -n 19; it should need well under a minute). Then diff your
   totals against `../runs/n5-L21.out` programmatically.
4. Write `REPORT.md` in THIS directory: the checkpoint format as you understood
   it; the job-set completeness result (expected count vs found count); your
   full totals table; the per-level PASS/FAIL vs n5-L21.out; anything
   surprising.

Rules: do NOT modify anything outside codex-verify/. Do NOT run the count
binary or reuse count.c's aggregation code; the point is an independent parse
and an independent prefix enumeration. The box is busy: nice everything. Be
precise and honest — if something does not reconcile, report the discrepancy
exactly rather than papering over it.
