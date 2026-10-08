# udtriangle: the triangle-orientation prover (RHOMBUS-SPEC.md Section 4), tests and results

Built 2026-09-26 by the triangle-prover builder for the u(23) supervisor, against RHOMBUS-SPEC.md at 9c61e32a8
(Section 4 binding, Section 3's I/O contract). The builder's report was delivered as text (a subagent may not write
report files); the supervisor wrote this file from it. Every number comes from one run of `run.sh --speed`, log
`runs/suite-2026-09-26.txt`; the whole suite passed. Paths are relative to `research/unit-distance-22/`.

## What was built

- `filter/udtriangle.c`: standalone C17, no code shared with udfilter; `make udtriangle` in `filter/` (not in `all`,
  because `u23-slice.sh` runs a bare `make` there; the supervisor decides at integration).
- I/O exactly as Section 3: graph6 lines in, one line out per input line, `{"verdict":"pass"}` or
  `{"verdict":"refuted"|"tu","witness":{"tri":{"tree":NODE}}}`, no `g6` key, deterministic bytes; an invalid line
  (bad graph6, blank, header, more than 24 vertices) is an error (stderr, exit 2).
- Flags: `-b N` / `--budget N` (nodes per graph, default 4096, at most 100,000; a graph needing more passes, counted
  as `budget`); `--no-mirror` (test aid, identical output). Stats line on stderr: graphs, refuted, tu, pass (open,
  budget, verify_fail, lift_fail, internal), root_leaf, tree_nodes, leaves, leaves_without_cycles, max_nodes.
- Rows: every 4-cycle's rhombus row plus the rows t(T, s) of the triangles split on the path. Depth-first: a node
  closes on a collision (first pair a < b), else a forced unit distance on a non-edge (first non-edge a < b, first
  edge p < q, smallest zeta), else splits the first triangle whose orientation its rows do not decide.
- Arithmetic: linear algebra mod p = 2^61 - 1 with w a root of x^2 - x + 1. For n <= 24 this is exact: every minor
  involved has modulus below 2^24.3 and a nonzero element of the kernel ideal of Z[w] -> F_p has norm at least p, so
  every rank equals the rank over Q(w). Leaf coefficients are Cramer minors of the leaf's basis rows, recovered from
  their residues as the unique element of norm < 2^58 in the class; only nonzero coefficients are listed; integer
  content divided out. The root's minus half is the mirror of the plus half (conjugate coefficients, zeta -> -zeta),
  byte-identical to searching it (tested).
- Self-verification before every emission: the serialised line is re-parsed strictly and checked against Section 4
  rules 1-5 in exact Z[w] arithmetic (int64 bounded by 2^62, __int128 accumulators); any failure emits pass and
  counts `verify_fail`. Peak RSS 1.9 MB.

## Results

**a. Units** (`units.py`, `units.tsv`): K4 refuted; K_{1,1,3} refuted; Moser spindle, W6 wheel, triangular-lattice
hexagon of radius 2 (19 points, 42 edges), 3x3 rhombic block, two triangles on an edge: pass; the six TU gadgets: tu
(single root leaves, zeta 0 or 3). K4 and K_{1,1,3} close on rhombus rows alone (single leaves, no triangles).

**b. Positive controls.** AMP's 56 known graphs: 56 pass. GP-10's 32,653 embedded B10 graphs: 0 refuted, 10,432 tu,
22,221 pass (tu = 9,712 single root leaves + 720 split trees, exactly the prototype's hidden-edge and closed counts).
Strong form (`b10_embed_check.py`): the 28,774 `super` pointers of `research/gp-10/cloud/lean3/records.jsonl.gz`
resolve to 858 exact embeddings in 81 number fields, evaluated to 100 digits; each of the 10,432 tu graphs was followed
down its tree by its embedding and by the mirror image (every ratio (f(c)-f(a))/(f(b)-f(a)) within 1e-30 of w or
w^-1): 20,864 leaf checks, every reached leaf a unit leaf whose relation holds with |f(a)-f(b)| = 1, worst residual
2.7e-94, 0 failures (depths 0: 19,424, 2: 998, 3: 428, 4: 14). Known-embedding fuzz (`fuzz_ud.py`, 6,000 graphs with
coordinates, n 6..24): 0 refuted, 826 tu (35 split trees, up to 143 nodes, depth 7), all 1,652 leaf checks true.

**c. Agreement with the prototype** (`prototype_verdicts.py`, `agree.py`): on the w1 samples of levels 13-18 (9,000
graphs), 0 disagreements; flagged 375 / 622 / 794 / 1,114 / 1,318 / 1,464. Cross-tab: prototype collision <->
refuted root leaf; hidden-edge <-> tu root leaf; closed -> tu with splits; open and no-triangles -> pass; the
prototype's closed-collision came out refuted with splits (93) or tu with splits (649), since a node closes at the
first relation it forces; both prune at (23,65). 3,000 random graphs (`fuzz_random.py`): 0 disagreements.

**d. Red controls** (`red-controls.sh`): `-DMUT_ROTATION` (w^2 for w) flags 49 / 26,677 / 1,500 of AMP 56 / B10 /
level 18, the dev checker rejects 49/49, 16,965/26,677 and 397/1,500 on rule 4 (the accepted ones are triangle-free
root leaves the mutation does not touch); `-DMUT_EDGE_CLOSE` (closes on a unit distance to an EDGE) flags 53 / 32,613
/ 1,500, rejected 53/53, 29,224/32,613, 1,018/1,500 on rule 3 (the accepted ones closed on a genuine non-edge); with
`-DMUT_SEARCH_ONLY` the true self-verifier caught every bad certificate (verify_fail equal to the counts above).

**e. Dev checker** (`devcheck_tri.py`, DEV AID ONLY, not independent): accepts every certificate emitted in the
suite. The blind checker is separate.

Other: `mirror-equiv.sh` byte-identical on 10 files at budgets 4,096 and 7; `robustness.sh` 28 checks (malformed input
exits 2; budgets 1-12 give valid output within budget and monotone flag counts; a budget only turns verdicts into
pass; deterministic).

## Throughput (graphs per CPU-second, median of 3 runs of ~40,000 graphs)

| level | sample | graphs/s/core | output bytes/graph |
|---|---|---|---|
| 15 | measure-15 | 22,375 | 690 |
| 17 | measure-17 | 15,340 | 1,232 |
| 17 | w1 reach-kept level-17 graphs (17,652) | 16,047 | 1,244 |
| 18 | measure-18 | 16,666 | 1,118 |
| 19 | level-19 children (1,354) | 21,156 | 518 |

The Python dev checker verifies about 1,050-1,250 certificates per CPU-second: replaying certificates in Python costs
~15x the prover's CPU, so the blind checker's replay cost matters for production.

## Tree sizes (nodes per certificate)

| level | certificates | mean | max | max depth | with splits (count, mean nodes) | rows per leaf |
|---|---|---|---|---|---|---|
| 13 | 375 | 8.64 | 95 | 6 | 224, 13.8 | 5.5 |
| 14 | 622 | 9.29 | 79 | 6 | 329, 16.7 | 5.8 |
| 15 | 794 | 8.28 | 63 | 6 | 344, 17.8 | 6.2 |
| 16 | 1,114 | 8.17 | 127 | 7 | 389, 21.5 | 7.3 |
| 17 | 1,318 | 7.94 | 111 | 7 | 437, 21.9 | 8.1 |
| 18 | 1,464 | 5.92 | 71 | 7 | 361, 20.9 | 8.9 |
| 19 (children) | 1,336 | 2.22 | 55 | 6 | 96, 18.0 | 8.5 |
| B10 | 10,432 | 1.60 | 31 | 4 | 720, 9.7 | 3.2 |

## Spec readings (none changes a verdict on the tested data; amendment 1 of RHOMBUS-SPEC.md adopts 1, 2 and 5)

1. Empty `cycles` in a leaf: read as allowed (never occurred in ~36,000 certificates).
2. Zero coefficients: never emitted.
3. Priority inside the tree: Section 3's order at every leaf, smallest zeta; `pair` a < b, edges p < q.
4. Refuted versus tu: a node closes at the first relation it forces, so a tree may be tu where deeper splitting would
   refute (649 graphs in c); both prune at (23,65).
5. The suggested split preference is vacuous: two triangles on an edge x-y with apexes t, t' span the 4-cycle
   x-t-y-t', whose rhombus row fixes the second orientation once the first is split; 0 of 23,440 splits shared an edge
   with an ancestor split (`split_stats.py`).
6. Coefficients by lifting Cramer minors (not fraction-free elimination); same exact re-verification; lift_fail 0.
7. Depth counted in splits; the budget counts all nodes; with the mirror the plus half is capped at (budget-1)/2.
8. Host limit 24, as udfilter's; the exactness bound is proved for n <= 24.

## Soundness read (the builder's)

Correct as argued: Lemma T (an equilateral unit triangle's rotation is +-60 degrees); an injective embedding realises
one sign at every split, so follows exactly one root-to-leaf path; at the leaf every rhombus row holds (Lemma R, needs
injectivity) and every path triangle row holds (Lemma T); the Z[w] identity maps to C by a ring homomorphism, so
scale * target(f) = 0, and scale != 0 in C (1 and w independent over R). tu heredity is L2's (G induced in every
descendant, u(N) <= M at the target). Soundness never depends on the modular arithmetic, only completeness does;
it rests on the exact self-verification and on the checker. Checker trap (now spec rule 2): a leaf triangle must be
the exact sorted split triple, never matched as a set. Certificate volume ~0.5-1.2 KB per graph at levels 15-19.

## Files and how to run

`run.sh` runs everything (`--speed` adds throughput; ~10 minutes, niced, one heavy process at a time); it calls
`units.py`, `run-samples.sh`, `devcheck_tri.py`, `prototype_verdicts.py`, `agree.py`, `run-b10-embed.sh` /
`b10_embed_check.py`, `mirror-equiv.sh`, `red-controls.sh`, `robustness.sh`, `fuzz.sh` / `fuzz_ud.py` /
`fuzz_random.py`, `throughput.sh`. Separately: `memory.sh`, `checker-speed.sh`, `split_stats.py`,
`run-prototype.sh`. `data/` holds copies of every input (w1 samples 13-18, `level19-children.g6`,
`level17-parents-w1.g6`, `B10-embedded.g6`, `amp-known56.g6`); outputs go to `out/`, mutants to `bin/`
(git-ignored). Python: `~/tools/pyenv-gp10/bin/python` (networkx 3.7, mpmath 1.3.0).
