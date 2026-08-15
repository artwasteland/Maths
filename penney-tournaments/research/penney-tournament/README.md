# research/penney-tournament

The **Penney's-game dominance tournament** at string length *k*: the digraph on
the 2^k binary patterns where A → B iff *P(A appears before B in fair coin
flipping) > ½*. This notebook computes its structural invariants exactly and
stages the genuinely-new ones for OEIS. Backs the stratum **No Triangle at
Three** and `oversight/oeis/penney-tournament/`.

## Files

- `engine.mjs` — the shared engine. Exact BigInt rationals; **two independent**
  win-probability methods (Conway's leading-number closed form; an
  absorbing-Markov linear solver); the tournament builder and its invariants.
- `verify.mjs` — the gate (**49/49**). Conway vs Markov on *every* ordered pair
  for k ≤ 6 (full) + k = 7 (sampled); each invariant recomputed from both
  engines; structural sanity (antisymmetry, the H↔T complement automorphism, the
  published k=3 odds, the canonical 4-cycle, count identities); prints the term
  lists. Run: `node research/penney-tournament/verify.mjs` (~2 min, the k=6
  Markov sweep).
- `explore.mjs` — the original scan (k = 1..9) that surfaced the candidates.
- `girth.mjs` — shortest directed cycle (BFS from each source).
- `structure.mjs` — the coarse structure: Tarjan SCC decomposition, sources/sinks,
  and (for small k) the exact set of directed-cycle lengths present by a Held–Karp
  subset DP.
- `pancyclic.mjs` — searches for and edge-verifies a directed cycle of *every*
  length in the giant SCC (a witness proves existence; a miss proves nothing).
  Also emits `pancyclic-k5-witnesses.json`, the length-3…30 witnesses embedded in
  the stratum for live re-checking.
- `verify-structure.mjs` — the structural gate (**39/39**): the 3-SCC
  decomposition for k ≤ 10, sink identities, girth, exact k=3/k=4 cycle spectra,
  pancyclicity witnesses k = 5..7, and the transTri/distinctP terms.
- `verify-page.mjs` — drives the built immersive page headless (both viewports),
  exercising all six instruments and asserting the self-checks and no overflow.

## What was found (all absent from OEIS; re-checked 2026-07-03)

| invariant | k = 1 … | staged? |
|---|---|---|
| nontransitive (cyclic) triples | 0,0,0,14,182,1790,16792,146894,1208544,9820040 | ✓ `b-cyc3` |
| tied pairs (p = ½) | 1,4,10,32,120,478,1860,7192,28490,112328,445752,1769174 | ✓ `b-ties` |
| max out-degree (strongest pattern) | 0,1,4,10,22,47,97,197,398,802,1609,3226 | ✓ `b-maxout` |
| transitive triples | 0,0,8,198,1964,16652,139570,1163520,9456630,76907320 | ✓ `b-transtri` |
| distinct win-probabilities | 1,3,15,31,87,191,415,871,1781,3395,6177,10373 | ✓ `b-distinctp` |

## The two points

**A square before a triangle.** Penney's game is nontransitive **from k = 3** —
but only as a directed *4-cycle* (HHT→HTT→TTH→THH→HHT, odds 2/3, 3/4, 2/3, 3/4).
At k = 3 **every decided triple is transitive**: no rock-paper-scissors *triangle*
until k = 4. `cyc3` measures that onset.

**One whirlpool, two drains.** From k = 4 the whole tournament is exactly three
strongly-connected components: one **pancyclic** whirlpool of size 2^k − 2 (girth
3, up to a Hamiltonian tour), plus the two constant runs H…H / T…T as isolated
**sinks** that beat no one. No sources. So there is no best pattern (the top is a
current that eats its own tail) and no worst but the two constants. Exact for
k ≤ 10 (`verify-structure.mjs`); pancyclicity proven exactly for k ≤ 4 and by
edge-verified witnesses for k = 5, 6, 7.

## Provenance

The win-probabilities reuse the engine validated three ways (Conway / Markov /
brute force, 152 checks) in `research/penneys-game` for the stratum *Always Bet
Second*; this notebook lifts it to the whole tournament and to longer strings,
re-proving Conway≡Markov on every pair it reads an invariant off of.
