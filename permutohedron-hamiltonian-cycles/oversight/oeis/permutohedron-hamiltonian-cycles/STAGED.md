# Hamiltonian cycles of the n-permutohedron (bubble-sort graph of S_n)

`a(n)` = number of **undirected Hamiltonian cycles** in the Cayley graph of S_n on
the adjacent transpositions s_1..s_{n-1} = the 1-skeleton of the n-permutohedron =
the bubble-sort graph. Equivalently, the number of change-ringing *extents* on n
bells under the single-adjacent-swap rule.

**Known terms:** a(1)=0, a(2)=0, a(3)=1, a(4)=44 (the truncated octahedron; OEIS
A343433). The sequence indexed by n is **absent from OEIS** (staged in `draft.txt`
+ `b-file.txt`). This directory is its reproducible workshop.

## The five-bell term a(5) — state of the art (2026-06-02)

a(5) is the count for the 120-vertex, 4-regular five-bell graph. Established this night
(stratum 021, *A Sextillion Ways Home*):

- **Enumeration is impossible** — the answer is ~10²¹ (too large to list) and the
  backtracking tree is ~5×10²³ nodes.
- **Estimate:** `a(5) ≈ 1.11 × 10²¹` (95% CI 1.07–1.15; 288M-dive campaign 2026-06-26)
  by validated sequential importance sampling.
- **Exact value: OPEN — and NOT a 64 GB job (corrected 2026-07-02).** The disk-backed
  counter (`count_frontier5_ext.cpp`, RAM-light, resumable) ran a third of the sweep
  and *measured* 2.55×10⁹ frontier states, still growing, widest stretch ahead:
  projected peak 2×10¹⁰–10¹³ states/level, i.e. TB-scale NVMe + days-to-weeks at
  best. The old "≥64 GB box" plan would OOM ~level 165. See
  `../../../research/permutohedron-a5/WALL.md` and
  `../../requests/007-finish-the-extent-enumeration.md`.

## Programs (all in C/C++/Node; build lines at the top of each file)

| file | what it does | validated against |
|---|---|---|
| `count.mjs` / `count.c` | exact Hamiltonian-cycle count by **backtracking** (degree + connectivity pruning) | a(3)=1, a(4)=44 |
| `count_par.c` | the same, OpenMP-parallel (task prefixes at depth CUT) | a(4)=44 |
| `estimate.c` | **Knuth random-dive** estimate of the *search-tree* size (→ ~5×10²³ for n=5) | n=4 tree |
| `sis.c` | **sequential importance sampling** estimate of a(n) (uniform child choice) | a(4)=44 → 43.9 |
| `sis_w.c` | SIS with a Warnsdorff bias (variance-reduction experiment) | a(4)=44 |
| `count_frontier.cpp` … `4.cpp` | **exact frontier sweep** (reuses TdZdd `HamiltonCycleZdd` transitions; counts level-by-level without building the full ZDD). v2 compact map; v3 lookahead-off; **v4 packed 1-byte keys, the most memory-frugal** | a(3)=1, a(4)=44, + brute force on dozens of random graphs |
| `gen_adj.mjs` | emit the bubble-sort graph as a TdZdd adjacency list (`lex`/`bfs`/`cm`/`rcm`/`spectral` orders) | — |
| `min_frontier.c` | simulated-annealing minimiser of the **cut-frontier** (vertex separation); best order found for S_5 achieves **23**, an upper bound, see the note below | matches `vfront.mjs` |
| `vfront.mjs` | independent cut-frontier checker | — |
| `brute_hc.mjs` / `rand_graph.mjs` | brute-force HC counter + random-graph generator, for cross-validating the frontier counter | — |
| `run_sis5.sh` / `run_final.sh` | multi-seed SIS drivers | — |

## Reproduce

```sh
# exact small cases (instant)
node count.mjs 4               # 44
gcc -O3 -o count count.c && ./count 3   # 1

# the estimate (a few minutes/seed)
gcc -O3 -march=native -o sis sis.c -lm && ./sis 5 8000000 101

# the tree-size wall
gcc -O3 -march=native -o estimate estimate.c && ./estimate 5 300000   # ~5e23 nodes

# the exact engine (validated; needs >15 GB for n=5 — fits for n<=4 and random graphs)
git clone https://github.com/kunisura/TdZdd /tmp/TdZdd
g++ -O3 -march=native -I/tmp/TdZdd/include -o count_frontier4 count_frontier4.cpp
node gen_adj.mjs 4 lex > bs4.dat && ./count_frontier4 bs4.dat   # 44
# a(5) exact: use the DISK-BACKED engine + runbook — research/permutohedron-a5/
# run-exact-on-disk.sh (count_frontier4 on bs5 OOMs even a 128 GB box; see WALL.md)
```

Compiled binaries are git-ignored; rebuild from source.

## The artifact gate, and one claim corrected (2026-07-27)

**The staged file is now checked as a file.** `node verify-staged.mjs` reads
`b-file.txt` and recomputes all four staged terms: a(1)=a(2)=0 by inspection of a
graph with no cycle, a(3) and a(4) by the brute-force Hamiltonian-cycle counter.
Nothing here rests on a literal. `node verify-all.mjs` now also asserts its numbers
and exits nonzero on a mismatch; until 2026-07-27 it printed them and exited 0
whatever they were, so a mutation probe that rewrote every staged term left every
committed check in this directory byte-identical and green.

**The vertex-separation claim was wrong, and it is corrected here, in `draft.txt`
and in `research/permutohedron-a5/README.md`.** Three places said the cut-frontier
width 23 was *proved* or *verified optimal*. It is neither. What exists is:

- an ordering that **achieves** width 23, produced by `min_frontier.c` and
  independently re-checked by `vfront.mjs` on `bs5_bfs.dat`. That is an **upper
  bound** on the graph's vertex separation.
- 85 million simulated-annealing iterations that **failed to find** anything better.
  A search failing to improve is evidence, not a proof; it cannot rule out an
  ordering the search never visited.

No lower-bound certificate exists in this repository, so the honest statement is
**23 is the best width known, not a proven minimum**, and the cost projections that
rest on it inherit that status. `research/permutohedron-a5/WALL.md` already used the
careful phrasing ("confirmed optimal-in-practice"); the other three sites did not,
and now do.
