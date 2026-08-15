# research/many-symbol-penney

Penney's game with a fair **q-sided die** instead of a coin — "the coin grows a third
face." Over a q-letter alphabet, the **dominance tournament** at word length *k* is the
digraph on the *q^k* words where **A → B iff P(A appears before B) > ½**. This notebook
computes its structural invariants exactly and stages the genuinely-new ones for OEIS.
Backs the stratum **A Triangle at Two** (`/strata/a-triangle-at-two/`) and
`oversight/oeis/many-symbol-penney/`. Sequel to `research/penney-tournament` (q=2).

## Files

- `engine.mjs` — the shared engine. Exact BigInt rationals; **two independent**
  win-probability methods (Conway's base-*q* leading-number closed form; an
  absorbing-Markov linear solver), a biased-die Markov variant, the tournament builder,
  its invariants, and an iterative Tarjan SCC decomposition.
- `verify.mjs` — the gate (**48/48**). (1) reproduces the *published* binary (q=2)
  sequences exactly — calibration against known ground truth; (2) Conway == Markov on
  every ordered pair (q=3,4; k≤3 full, k=4 sampled) with the complement identity
  p(A,B)+p(B,A)=1; (3) structural facts — antisymmetry, the q constant runs are exactly
  the singleton sinks, giant SCC size = q^k−q, joint-strongest multiplicity q(q−1),
  alphabet-permutation automorphism; (4) biased-Markov sanity. Run:
  `node research/many-symbol-penney/verify.mjs` (~12 s).
- `discover.mjs` — the exploration: invariants + SCC structure for q = 2, 3, 4, printing
  the sequences and the whirlpool/drain census.
- `details.mjs` — the explicit findings: the two ternary length-2 triangles (with exact
  odds), the full q=3 k=2 relation table, and the consolidation length by q.
- `extend.mjs` — lengthens the sequences (q=3 → k=7, q=4 → k=6 for the cheap invariants).

## What was found (all absent from OEIS; checked 2026-07-05)

**A triangle at two.** A fair coin's Penney game has no directed 3-cycle until length 4
(the smallest nontransitive loop at length 3 is a 4-word square — see the sibling
*No Triangle at Three*). A fair **three-sided die has a directed triangle at length 2**:
`AB → BC → CA → AB` and its mirror `AC → CB → BA → AC`, every edge at odds **3/5**, and
these are the only two among the nine two-letter words. A four-sided die has 8 such
triangles at length 2. `cyc3` (directed-3-cycle count) by k:

| die | cyc3 (k = 1, 2, 3, …) |
|---|---|
| q=2 coin | 0, 0, 0, 14, 182, 1790, 16792, 146894 |
| q=3 die | 0, 2, 60, 2144, 71484, 2019058, 55930476 |
| q=4 die | 0, 8, 716, 55004, 3813064 |

**One whirlpool, q drains — consolidating sooner the more faces.** Past a consolidation
length, the tournament is exactly one strongly-connected whirlpool of size **q^k − q**
plus **q** constant-run drains (all-A, all-B, …), one per face, each beating no one; the
whirlpool is the unique source. The consolidation length **falls as q rises**:

| q | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| smallest k with giant = q^k − q | 4 | 3 | 2 | 2 |

floored at 2 (a length-1 game has no decided contests). The strongest word comes in
**q(q−1)** symmetric copies (the two-distinct-letter openers).

**New integer sequences** (staged in `oversight/oeis/many-symbol-penney/`): for q=3 and
q=4, the counts of nontransitive triples, transitive triples, tied pairs, max out-degree,
and distinct win-probabilities — all confirmed absent from OEIS.

## The honest frame

Penney's game, its nontransitivity over any alphabet, and Conway's leading-number method
are **classical** (generalization to larger alphabets & biased dice: Guibas & Odlyzko
1981; martingale proof: Li 1980; group-action variant, theoretical: Khovanova & Li 2020).
The qualitative story is **not** claimed as new — only the specific tournament-invariant
integer sequences carry the OEIS-absence claim. The structural facts (whirlpool size,
consolidation length, drain count, strongest-word multiplicity) are established by exact
computation over the finite ranges above and stated for larger k, q as the pattern those
checks show — the natural generalization of the binary theorem, not a proof for all k, q.

## Provenance

The win-probability engine reuses the discipline validated three ways (Conway / Markov /
brute force, 152 checks) in `research/penneys-game`, generalized here to base q and
re-proven Conway ≡ Markov on the pairs it reads invariants off. The one external anchor is
the reproduction of the published q=2 sequences — an engine that recovers the known case
exactly is trusted on the new one.
