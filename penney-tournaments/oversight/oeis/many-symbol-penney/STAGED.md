# oversight/oeis/many-symbol-penney

The **many-symbol Penney's-game dominance tournament**: Penney's game played with a
fair *q*-sided die instead of a coin. Over a *q*-letter alphabet, the tournament at
word length *k* is the digraph on the *q^k* words with an edge **A → B** whenever *A*
appears before *B* (in i.i.d. rolls of the fair die) with probability over ½. This
directory stages the genuinely-new invariant sequences of that tournament for the
three- and four-sided dice, each **confirmed absent from the OEIS on 2026-07-05**.

Backs the stratum **A Triangle at Two** (`/strata/a-triangle-at-two/`) and the
notebook `research/many-symbol-penney/`. Sequel to the binary (q=2) bundle in
`oversight/oeis/penney-tournament/`.

> ## ⚠ SIX OF THESE TEN FILES ARE ALSO STAGED IN `../penney-mary/`
>
> **This was already known and had been sitting unactioned.** It is finding 1 of
> `../CENSUS-2026-07-26.md`, which checked the byte-identity directly and named the
> same resolution (keep these, the longer copies). Three weeks later nothing had
> changed and neither README carried a warning. `../bind-staged.mjs` re-derived it
> independently on 2026-08-15 and now **fails** on it, which is the actual repair: the
> fact moves out of a document nobody has to open and into a gate that blocks.
>
> `../penney-mary/` was staged 2026-06-21, two weeks before this directory, by a
> different session. They stage the same object: the Penney dominance tournament over
> a fair *q*-letter (there *m*-symbol) alphabet, indexed by word length.
>
> | this directory | same sequence as | overlap |
> |---|---|---|
> | `b-q3-cyc3.txt` (7 terms) | `../penney-mary/b-m3-cyc3.txt` (6 terms) | all 6 agree |
> | `b-q3-maxout.txt` (7) | `../penney-mary/b-m3-maxout.txt` (6) | all 6 agree |
> | `b-q3-ties.txt` (7) | `../penney-mary/b-m3-ties.txt` (6) | all 6 agree |
> | `b-q4-cyc3.txt` (5) | `../penney-mary/b-m4-cyc3.txt` (5) | identical |
> | `b-q4-maxout.txt` (5) | `../penney-mary/b-m4-maxout.txt` (5) | identical |
> | `b-q4-ties.txt` (5) | `../penney-mary/b-m4-ties.txt` (5) | identical |
>
> **DO NOT DEPOSIT BOTH DIRECTORIES.** Six duplicate OEIS submissions of one
> sequence each, under two separately dated absence claims, is what this note exists
> to prevent.
>
> This directory is the longer file everywhere the two meet, and `b-q3-transtri.txt`
> / `b-q3-distinctp.txt` / `b-q4-transtri.txt` / `b-q4-distinctp.txt` have no
> counterpart there. What `../penney-mary/` has that this does not is the **m = 5**
> family, three files, unaffected by any of the above.
>
> The good half: the two directories were computed by two independently written
> engines, and they agree on every shared term. That is real cross-engine
> confirmation, which neither could claim on its own.
>
> **Resolution is a human call and has not been made.** Until it is,
> `bind-staged.mjs` reports the overlap as a failure so that it cannot ship quietly.

## What is staged (all confirmed absent from OEIS, 2026-07-05)

Indexed by word length *k* (offset 1). b-files regenerate via
`node oversight/oeis/many-symbol-penney/derive.mjs`.

### Three-sided die (q = 3), k = 1…7

| quantity | terms | b-file |
|---|---|---|
| nontransitive (directed-3-cycle) triples | 0, 2, 60, 2144, 71484, 2019058, 55930476 | `b-q3-cyc3.txt` |
| transitive triples | 0, 6, 654, 21300, 633840, 17796978, 496096782 | `b-q3-transtri.txt` |
| tied pairs (probability exactly ½) | 3, 18, 129, 1134, 9825, 87030, 769827 | `b-q3-ties.txt` |
| max out-degree (words the strongest beats) | 0, 3, 12, 42, 130, 402, 1214 | `b-q3-maxout.txt` |
| distinct win-probabilities | 1, 7, 29, 95, 275, 695, 1507 | `b-q3-distinctp.txt` |

### Four-sided die (q = 4), k = 1…5

| quantity | terms | b-file |
|---|---|---|
| nontransitive triples | 0, 8, 716, 55004, 3813064 | `b-q4-cyc3.txt` |
| transitive triples | 0, 48, 7020, 515772, 35117328 | `b-q4-transtri.txt` |
| tied pairs | 6, 60, 864, 13332, 209868 | `b-q4-ties.txt` |
| max out-degree | 0, 5, 24, 108, 438 | `b-q4-maxout.txt` |
| distinct win-probabilities | 1, 7, 29, 97, 275 | `b-q4-distinctp.txt` |

The q=4 sequences are shorter (computed to k=5) and are the weaker absence claims of
the two families; a future session can lengthen them (k=6 is q^k = 4096 words — the
cheap invariants are easy; cyc3/transtri need the O(n³) triple census, ~hours).

## Why these are believed exact

- **Two independent exact methods** compute every win-probability as a BigInt
  rational: Conway's leading-number closed form (base-*q*), and an independent
  first-principles absorbing-Markov linear solver. `research/many-symbol-penney/verify.mjs`
  (**48/48**) asserts they agree on every ordered pair (q=3,4; k≤3 full, k=4 sampled).
- **Calibration against known ground truth.** The same engine reproduces the *published*
  binary (q=2) sequences exactly — the nontransitive-triple count `0,0,0,14,182,…`, the
  tied-pair count `1,4,10,32,120,…`, the max-out-degree `0,1,4,10,22,…`, etc. — which
  are the staged sequences of the sibling bundle. An engine that reproduces the known
  case is trusted on the new one.
- **Absence checked** term-by-term at `https://oeis.org/search?q=<terms>` on 2026-07-05;
  every sequence returned "No results."

## The honest frame — what is and isn't new

Penney's game, its nontransitivity over any alphabet, and Conway's leading-number
method for the odds are **classical** — the generalization to larger alphabets and to
biased/asymmetric dice is Guibas & Odlyzko, *String overlaps, pattern matching, and
nontransitive games* (J. Combin. Theory A 30, 1981); the martingale proof is Li (1980).
The Penney game under a group action on words is studied by Khovanova & Li (2020),
theoretically, **without** tabulating the tournament invariants counted here. So the
qualitative story is not claimed as new; **only the specific integer sequences carry
the OEIS-absence claim.**

## Outward path (unchanged house policy)

OEIS forbids AI-authored and automated submissions, so this directory contains **no
paste-ready draft prose** — that would break OEIS policy and the project's never-lie
rule. The math is staged reproducibly (exact, two-way verified, absence-checked); the
*footprint* routes through **(A)** a Zenodo deposit for a citable DOI (`.zenodo.json`
here) and/or **(B)** a real mathematician who independently checks and, if convinced,
authors and submits to OEIS *as themselves*. Only the human can open the Zenodo account
or send outreach — see `oversight/requests/`. A-numbers get added here once assigned.
