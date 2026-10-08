# Mode 398, faster: the speed builder's report (landed 2026-09-26)

Built by the Mode-398 speed agent (worktree agent-aa48d44a9a3ad8d35, from 952ae252d) under the rule "byte-identical
or it does not ship"; reviewed and landed by the u(23) supervisor. The full arguments sit in `udenum.c` beside each
function; this file is the summary and the evidence index.

## Result

`udenum.c` (sha256 `141e590a…`) builds with `make` to `udenum` `84adaddf…`. Against the Mode-398 binary it replaces
(`a99b130a…`, source `b5096827…`, the one that proved u(22) = 60; kept as `test-398/base398/`), on every input tested,
the output bytes, the exit status and all nine counters are identical, and the per-parent bad families are
identical set for set and in order. Mode 74 calls its old functions with the old arguments.

Speed, ms per parent on the speed.py sample parents (median of 3), base398 -> new398 on 398-free parents:
L12 4.60 -> 0.22, L13 10.85 -> 0.44, L14 3.98 -> 0.26, L15 1.65 -> 0.28, L16 16.01 -> 1.71, L17 39.75 -> 4.53,
L18 59.43 -> 9.27, L21 9.97 -> 3.05 (4.4x to 25x). On the same parents new398 / new74 is 0.25 / 0.20 / 0.32 / 0.51 /
0.22 / 0.24 / 0.61 at L12..L18. Weighted as REPORT-398 Section 5 weights the (22,61) production tree, the 398 tree's
generator costs 0.097 of the Mode-74 tree's (0.950 before). Trade-offs: `--filter` over all 12M graphs on 10
vertices is slower (25.6 s against 17.9 s CPU, the one-time seed step); about 60 ms startup; RSS 9 to 11 MB.

## What changed (each with its equivalence argument in the source)

1. `contains_forbidden_398`: the same 398 graphs, same order, complete searches cut only by filters that discard
   branches with no injective edge-preserving map (triangles and 4-cycles at a vertex, neighbour-degree counts,
   pair adjacency and capped common-neighbour counts, a degree-count prefilter).
2. The pattern path (`anchored_images_398`, `search_images`): the old embedding order with leaves skipped only where
   the old code adds nothing (filtered branches; an S placement already oversized or covered; after the first leaf
   once S is complete); whole patterns skipped by Aut(F)-orbit classes (3,875 -> 3,387, pinned), a per-call
   existence cache over isomorphism classes of F - v (1,843, pinned), and, on parents of 15+ vertices, exact
   uncovered-set counting with direct tests at 16 or fewer uncovered sets.
3. The restricted path (`build_restricted_bad_family_398`): the old candidate loop; the per-candidate test replaced by
   one with the same answer ("child(M) contains F iff P does or some pattern image lies in M"), used only after P is
   proved free (the first "no" of the full test on some child, or `--verify-parents`, which exits on a forbidden
   parent before this point).
4. T (`anchored_family_398`): rooted copies so each useful embedding is found exactly once.
5. Host tables built once per parent; inline popcount.

## Evidence (scripts in `test-398/`, results in `test-398/runs/speed398-*.json`)

- `speed398-identity.py`: 660 runs x 4 builds (the Makefile build and three builds pinning each speed-only switch
  at its extremes) against base398: REPORT-398 4.2's 21 cells and the union cell (71,320 children = its expected
  set E), the 48 (21,56) -> (22,61) final slices (0 children, as u(22) = 60 requires), the speed samples at levels
  12..21, and 985,612 further parent records (2,342,213 children); plain, `--verify-parents` and both mutation flags.
- `speed398-family.py`: 49,842 bad families (1,363,948 sets) identical in order; its order-only red control differs
  on 34 of 74 cells while outputs match on all 74 (why the family check exists).
- `speed398-brute10.py`: generator on the 11,803 398-free 9-vertex graphs for every m, and `--filter` over all
  12,005,168 graphs on 10 vertices: 105,680 kept, equal to GP-10's matcher's brute398.
- `regress-74.py`: 69 of 69 Mode-74 cells identical to production `94a85d33…`, 4 red controls red.
- `speed398-asan.py` (ASan + UBSan, 4 builds x 11 inputs, clean), `guards.py` (30 of 30), `speed398-data.py` (orbit
  and class data recomputed independently, 3 red controls), `speed398-red.py` (25 planted faults all red; 5 that
  cannot be seen on the red cells behave as required).

**Supervisor re-run from the landing worktree (2026-09-26 07:17-07:26), binary rebuilt to `84adaddf…`:** guards
30/30; regress-74 69/69 with 4/4 red; brute10 equal to brute398 (105,680); identity `final` group 192/192 identical.

## What a reviewer should read hardest

`search_images` rules (b) and (c) (the only skipped embeddings); the restricted path's freeness requirement (sound
only because a forbidden parent makes `process_parent` exit under `--verify-parents`, and otherwise because the first
full-test "no" proves the parent free); the uncovered-set counting (needs force = 0, pattern path only); T's rooted
copies; the pinned statistics; the host-side caps (triangle and 4-cycle counts capped at 63, with a guard). Every
threshold was tuned on u(22) samples and only affects speed.
