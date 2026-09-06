# Task B1: the enumerator (module enum/)

Build `enum/` per CONTRACT Section 3: a C program (`enum/udenum.c`, single binary `udenum`,
linked against libnauty) that, given a parent file (canonical graph6, n-1 vertices, m' edges)
and a target (n, m), emits every F-free child on n vertices with m edges obtained by adding a
vertex of degree d = m - m' whose neighbourhood avoids every minimal bad set, accepting a
child only if the new vertex is in the Aut(child)-orbit of the canonically first minimum-degree
vertex (canonical augmentation by minimum-degree deletion; use densenauty to get the
canonical labelling and the orbits). Output: canonical graph6, one per line, plus a JSON shard
manifest exactly as in CONTRACT Section 2.

Also deliver `enum/run-dag.sh` (or python) that builds the whole DAG for a target (n, m) from
geng seeds: for each level n' and each m' in the edge window (CONTRACT 3.2 and 3.4), run the
shards and keep every intermediate `<n'>-<m'>.g6` with manifests, so that a later cloud run can
take any parent file and a parent range.

Required behaviour and self-checks (all must be run and reported):
1. Bad-neighbourhood patterns: precompute from data/forbidden-74.json the 635 (F - v, N(v))
   patterns; for each parent H find all monomorphic copies and the minimal family T'. Verify the
   pattern count (635) and the size distribution (|S| = 2: 61, 3: 413, 4: 130, 5: 26, 6: 4, 7: 1).
2. Reproduce the paper's Table 1 F-free column EXACTLY: for n = 16..21 with m = u(n)
   (41, 43, 46, 50, 54, 57) the counts must be 1, 15, 84, 17, 7, 149. Then u-bar(22) = 62 with
   EXACTLY two graphs, and none at (22, 63). Report wall time and CPU time per level. If the
   full run to 21 is too slow for the ten-minute test rule, run it in the background under nice
   with logging and report how far it got, plus the exact counts you did reproduce (n <= 18
   at least). Small-n sanity: for n <= 10, brute force with nauty-geng plus the F filter must
   give the same U-bar(n, m) sets as your generator for every m (compare sorted canonical files).
3. Completeness controls: every one of the 56 graphs in sources/amp/anc/graph6.txt must appear
   in your `<n>-<m>.g6` for its (n, m). Mutation tests per CONTRACT 3.6(d), each shown to go
   red.
4. Determinism: the same parent range gives byte-identical output on two runs.
5. Performance notes for sharding: graphs per second per level, memory, and your estimate of
   the (22, 61) cost given the measured (21, 56) and (21, 57) sizes.

Read the paper's Section 2 carefully (the min-degree rule on p. 5 is subtle: a parent with
delta(H) <= d - 2 can be skipped; with delta(H) = d - 1 the new vertex must be adjacent to all
minimum-degree vertices). Under canonical augmentation by minimum-degree deletion that rule is
automatic; state precisely why in REPORT.md, or state why it is not, with a counterexample.
