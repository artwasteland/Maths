# Penney-tournament sequences for an *m*-sided die — staged for OEIS

The binary Penney tournament (the digraph on the 2ⁿ coin-flip strings, A → B iff
*A* appears before *B* with probability > ½) is already staged in
`../penney-tournament/`. This folder generalises it to a **fair *m*-symbol
alphabet — an *m*-sided die**: the digraph on the *mⁿ* length-*n* words, same
edge rule. Surfaced by the stratum **"A Triangle on Three Sides"**
(`/strata/penney-dice/`).

> ## ⚠ SIX OF THESE NINE FILES ARE ALSO STAGED IN `../many-symbol-penney/`
>
> **This was already known and had been sitting unactioned.** It is finding 1 of
> `../CENSUS-2026-07-26.md`, which checked the byte-identity directly and named the
> same resolution. Three weeks later nothing had changed and neither README carried a
> warning. `../bind-staged.mjs` re-derived it independently on 2026-08-15 and now
> **fails** on it, which is the actual repair: the fact moves out of a document nobody
> has to open and into a gate that blocks.
>
> This directory was staged 2026-06-21 and `../many-symbol-penney/` on 2026-07-05, by
> different sessions. They stage the same object: the Penney dominance tournament over
> a fair *q*-letter (here *m*-symbol) alphabet, indexed by word length.
>
> | this directory | same sequence as | overlap |
> |---|---|---|
> | `b-m3-cyc3.txt` (6 terms) | `../many-symbol-penney/b-q3-cyc3.txt` (7 terms) | all 6 agree |
> | `b-m3-maxout.txt` (6) | `../many-symbol-penney/b-q3-maxout.txt` (7) | all 6 agree |
> | `b-m3-ties.txt` (6) | `../many-symbol-penney/b-q3-ties.txt` (7) | all 6 agree |
> | `b-m4-cyc3.txt` (5) | `../many-symbol-penney/b-q4-cyc3.txt` (5) | identical |
> | `b-m4-maxout.txt` (5) | `../many-symbol-penney/b-q4-maxout.txt` (5) | identical |
> | `b-m4-ties.txt` (5) | `../many-symbol-penney/b-q4-ties.txt` (5) | identical |
>
> **DO NOT DEPOSIT BOTH DIRECTORIES.** Six duplicate OEIS submissions of one
> sequence each, under two separately dated absence claims, is what this note exists
> to prevent.
>
> The three `b-m5-*.txt` files are unique to this directory and are unaffected.
> `../many-symbol-penney/` is the longer file everywhere the two meet: it carries one
> further term at q = 3 and stages two families this directory does not (transitive
> triples, distinct win-probabilities).
>
> The good half: the two directories were computed by two independently written
> engines, and they agree on every shared term. That is real cross-engine
> confirmation, which neither could claim on its own.
>
> **Resolution is a human call and has not been made.** Until it is,
> `bind-staged.mjs` reports the overlap as a failure so that it cannot ship quietly.

All nine sequences below were **confirmed absent from OEIS** at staging
(2026-06-21; numeric search of the live database, each prefix returning *No
results*).

## The headline fact — the coin is the special case

For a **coin** (m=2) Penney's game is nontransitive from n=3, but the smallest
cycle is a **4-square**: there is *no directed triangle until n=4* (cyc3 =
0,0,0,**14**,…). That "no triangle at three" is the reason the sibling sequence
exists — and it turns out to be a **peculiarity of having only two symbols.**

For **any die with m ≥ 3 symbols, nontransitivity and the first directed triangle
arrive together at n = 2.** On a fair 3-sided die the length-2 words already make
a clean rock-paper-scissors triangle:

```
01 ▸ 12 ▸ 20 ▸ 01     each beats the next with probability exactly 3/5
```

(and its mirror `02 ▸ 21 ▸ 10`). Two symbols are simply too few to close a
triangle at the onset length; three are exactly enough. The onset gap
(triangle − nontransitivity) is **1 for the coin and 0 for every larger die.**

| m (die) | nontransitivity onset | first triangle | gap |
|---|---|---|---|
| 2 (coin) | n=3 | n=4 | **1** |
| 3 | n=2 | n=2 | 0 |
| 4 | n=2 | n=2 | 0 |
| 5 | n=2 | n=2 | 0 |

## The staged sequences (offset k = 1, the word length n)

| family | m=3 | m=4 | m=5 |
|---|---|---|---|
| **cyc3** — directed (nontransitive) triangles | 0, 2, 60, 2144, 71484, 2019058 | 0, 8, 716, 55004, 3813064 | 0, 20, 3720, 535440 |
| **ties** — tied pairs (p = ½) | 3, 18, 129, 1134, 9825, 87030 | 6, 60, 864, 13332, 209868 | 10, 160, 3770, 90900 |
| **maxout** — max out-degree | 0, 3, 12, 42, 130, 402 | 0, 5, 24, 108, 438 | 0, 7, 40, 220 |

(The m=2 row — the published anchor — is reproduced exactly by the same code:
cyc3 = 0,0,0,14,182,…; ties = 1,4,10,32,…; maxout = 0,1,4,10,…. See the
honesty-anchor check below.) `%K` for every new sequence: `nonn,more`.

## How the terms were computed and checked

`research/penney-mary/verify.mjs` — **18/18 checks**:

1. **Two independent exact engines for every win-probability.** A generalised
   Conway / Guibas–Odlyzko leading-number closed form (alphabet size = the base)
   and a first-principles absorbing-Markov linear solver, both in exact BigInt
   rationals. They agree on **every** ordered pair for (m,k) ∈
   {(2,4),(2,5),(3,2),(3,3),(4,2),(5,2)} (full) and on random samples at
   (3,4),(4,3),(5,3). Markov is first-principles, so the agreement *validates the
   generalised Conway formula empirically* for m up to 5.
2. **Honesty anchor.** The m=2 invariants reproduce the **published binary
   sequences exactly** (ties / cyc3 / maxout from `../penney-tournament/`). If the
   coin numbers were wrong, none of the die numbers would be trusted.
3. **Monte-Carlo.** A third, independent method (simulated races) agrees in sign
   with the exact p(A,B) on a sample of pairs — the edge *directions* are real.
4. **Structure.** Antisymmetry; invariance under all m! symbol relabellings (the
   die is fair); girth and the two onset thresholds.

Reproduce the b-files: `node oversight/oeis/penney-mary/derive.mjs`.

## ⚠ The outward path — read `../README.md` first

OEIS **forbids AI-authored and automated submissions**, so there are
**deliberately no paste-ready `draft.txt` files here.** The *math* is the
contribution (exact, two-way verified, absence-checked); the *authoring* must be
done by a human who independently checks it and stands behind it. The footprint
routes the same way as the rest of `/oversight/oeis/`:

1. **Zenodo** — deposit the reproducible bundle (engine + verifier + b-files) for
   a citable DOI; no authorship problem.
2. **OEIS only via a real human author** who verifies it themselves (SeqFan /
   maths students). The pitch invites scrutiny — *including that we might be
   wrong* — never applause.

If a reader finds any of these already catalogued, that correction belongs at the
deposition door — the claim is only "absent from OEIS as of 2026-06-21."

## References

- W. Penney, *Problem 95: Penney-Ante*, J. Recreational Math. 2 (1969), 241.
- L. J. Guibas & A. M. Odlyzko, *String overlaps, pattern matching, and
  nontransitive games*, J. Combin. Theory Ser. A 30 (1981), 183–208.
- S.-Y. R. Li, *A martingale approach…*, Ann. Probab. 8 (1980), 1171–1176.
- M. Gardner, *On the paradoxical situations that arise from nontransitive
  relations*, Scientific American 231 (Oct. 1974), 120–125.
