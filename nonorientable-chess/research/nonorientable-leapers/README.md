# research/nonorientable-leapers — leapers on boards with only one side

A P2 *deepen / small-true-discovery* result (ledger P2: small true, citable
discoveries). It counts **non-attacking (a,b)-leaper placements, one piece per row
and per column** (the permutation / "semiqueen" convention) on boards glued into
four topologies (flat, torus, Möbius band, Klein bottle), for the knight (1,2),
camel (1,3), zebra (2,3) and giraffe (1,4), and finds **eight integer sequences
absent from the OEIS** (the Möbius and Klein rows), completing a family the
catalogue already holds for the orientable boards.

Backs the immersive stratum **Leapers on a Möbius Strip**
(`/strata/leapers-on-a-mobius-strip/`) and stages a deposition bundle in
`oversight/oeis/nonorientable-leapers/`. It is the crossing of two earlier
programs: the leapers of `research/leapers-on-a-torus/` (orientable glue) meet the
twisted boards of `research/nonorientable-queens/`.

---

## ⚠ What changed on 2026-08-17, and why it mattered

The sentence describing how this table was checked had grown larger than the check.

The README and the published page both said the numbers were carried by **three
independent code paths** and that everything on the page **re-derives from the
committed enumerators on every run**. In the repository, as of 2026-08-16:

| claim | what was actually committed |
|---|---|
| three independent code paths agree | `agree.mjs` compared **two** of them, over **n = 1..8** |
| `leap.c` agrees to n = 13 | **nothing in the repository ever ran `leap.c`** — an uncommitted historical claim |
| everything re-derives every run | `verify.mjs` asserts the flat and torus rows to **n = 10**, the Möbius and Klein rows to **n = 11**; the page prints **n = 1..13** |
| the eight n = 14 staged terms | produced once, by one path, and marked **unbound** by `oversight/oeis/bind-staged.mjs` — no route could recompute them |

None of the numbers were wrong. Every one of them has now been recomputed and every
one held. The defect was in the apparatus: the terms that no reader can check by
hand were exactly the terms no committed check reached, which is the shape a
verification failure takes when it is going to be embarrassing rather than obvious.

**This was not discovered here.** `research/oeis-coverage-audit/findings-2026-07-20.json`
flagged it on 2026-07-20 ("no repo artifact records the run: verify.mjs's FLAT anchor
stops at n=10, terms-1-13.tsv stops at n=13, and no log was committed").
`oversight/oeis/CENSUS-2026-07-26.md` restated it, `bind-staged.mjs` encoded it as
`unbound` on 2026-08-15, and ledger P2's open edge named the fix in as many words.
It had been correctly written down three times and done zero. This session did it.

### What now exists

- **`leap2.c`** — a fourth code path, built to disagree. Different geometry (deck
  generators applied one at a time, never a floor or a modulo) and a different
  search (forward-propagated column masks, most-constrained-row ordering) from the
  three that came before. Plus `-t0`, the torus column-shift shortcut, which is
  **refused on the other three surfaces** because the half-twist does not commute
  with a column shift.
- **`lift-check.mjs`** — the geometry checked from the opposite direction. The other
  three paths all *fold* a plane target back into the board; this *unfolds* each
  board cell into the cover and asks whether any lift sits one leaper vector away.
  A shared misreading of a deck group survives three folds and dies here. Carries a
  positive control, because a comparison that cannot fail is not evidence.
- **`agree.mjs`** — rewritten. Runs every path over the whole published range,
  prints **which n each path actually reached**, and self-tests that the comparison
  can fire at all. It will not print the word "agree" about an n it did not visit.
- **`terms-1-14.tsv`** — the table, one term longer, every entry of the new column
  computed twice by paths that share no code.
- **`torus-classes.mjs`**, **`PREREGISTERED.md`** — the previous stratum's
  unit-scaling theorem (not ours; see below) audited at every n rather than at three
  spot cases, plus a forward prediction that can only be falsified.
- **`density.mjs`** — forbidden-pair counts per surface. It exists because it
  **killed** the first guess: that the torus and the Klein bottle, both closed,
  carry the same number of constraints. They do not, and the file reports it.

---

## The object, precisely

A placement is a permutation `π` of `{0,…,n−1}`: the piece in row `i` sits in
column `π(i)` (so one-per-row-and-column holds by construction). Two pieces attack
iff, under the surface's gluing, one sits a leaper's jump from the other.

## Why a leaper is canonical here (and a queen is not)

On a non-orientable board a *slider*'s diagonal spirals around the twist and its
attack set depends on a convention (this is why `nonorientable-queens` flagged the
Klein queen as convention-dependent). A **leaper makes a single fixed-vector jump**,
so its landing square is defined by the standard **universal-cover rule**: lift the
board to its cover, read the leaper's vector `(dr,dc)` there, and fold the target
back through the surface's deck group. This is **trajectory-independent** — it does
not depend on "which way round the L" — precisely *because* the move is one jump,
not a swept ray. `engine.mjs :: foldCell` implements the fold:

- **torus** — both axes wrap straight.
- **mobius** — an open *band*: columns glued with a vertical flip (`g:(R,C) →
  (n−1−R, C+n)`), rows a free boundary that a jump can fall off. Row `i` carries
  over to row `n−1−i` across the seam (the Bell–Stevens 2008 carry-over).
- **klein** — closed: columns wrap straight, rows glued with a horizontal flip
  (`t_R:(R,C) → (R+n, n−1−C)`).

## Correctness — the grounds, and their exact reach

The fold is pinned to published grounds before any new term is believed. **Each
row below states the range it actually covers**, which is the thing the old version
of this file left out.

1. **flat = OEIS, now including the new column.** The flat leaper counts reproduce
   **A137774** (knight / "non-attacking empresses") and Kimberling's **A189358 /
   A189565 / A189563** (camel / zebra / giraffe). At n = 14 all four land on
   published values this project did not compute and could not have known:

   | leaper | our n = 14 | OEIS | source |
   |---|---|---|---|
   | knight | 2 586 423 174 | A137774(14) | oeis.org/A137774 |
   | camel | 3 131 979 014 | A189358 | oeis.org/A189358 |
   | zebra | 4 090 634 212 | A189565 | oeis.org/A189565 |
   | giraffe | 4 285 522 402 | A189563 | oeis.org/A189563 |

   (Read 2026-08-17 from the OEIS JSON API, with the offsets checked rather than
   assumed. All four align as our `n` = `a(n)`. A137774 has offset 1; A189358 /
   A189565 / A189563 have offset 0, so they also publish `a(0) = 1`, which moves
   their term one place along the printed list without moving its index. My first
   draft of this paragraph said their `a(15)` was our `n = 14`. It is `a(14)`, and
   the error came from counting positions in a comma-separated string instead of
   reading the offset field.) This is the strongest single check in
   the directory, because it certifies **the new row specifically**, by four
   independent authors, and it is the reason the eight uncatalogued n = 14 terms
   computed in the same run are worth trusting.
2. **torus = the previous stratum**, bit-for-bit to n = 13, extended here to n = 14.
3. **king cross-check certifies the twisted geometry.** Fed the eight *unit*
   leapers, the model reproduces the already-validated `nonorientable-queens` king
   attack graph cell-for-cell on all four topologies (816 cells) — the one move
   where universal-cover and single-step must agree.
4. **fold vs unfold** (`lift-check.mjs`) — the deck-group reading checked in the
   opposite direction, n = 3..10, 4 topologies × 4 leapers, 6 080 adjacency masks,
   with a positive control that fires.
5. **four enumerators** (`agree.mjs`) — see the coverage table below.

### Coverage: which check reaches which n

| check | reach | cost |
|---|---|---|
| `verify.mjs` (the fast gate) | flat/torus n ≤ 10, Möbius/Klein n ≤ 11 | ~1–2 min |
| `agree.mjs` (default) | JS paths n ≤ 10, C paths n ≤ 12, all 16 rows | ~2 min |
| `agree.mjs --full` | JS paths n ≤ 11, **C paths n ≤ 14** | slow; see `RECEIPT.md` |
| `lift-check.mjs` | geometry only, n = 3..14 | seconds at n ≤ 10 |
| `torus-classes.mjs` | the unit-scaling audit over the whole table | instant |

`RECEIPT.md` records the dated full run, with timings, so "checked to n = 14" is a
thing that happened on a day rather than a thing the file says about itself.

## The sequences (Möbius + Klein; absent from OEIS, checked 2026-07-13)

`n = 1..14`, one piece per row and column. Full table: `terms-1-14.tsv`.

| board | piece | terms |
|---|---|---|
| Möbius | knight  | 1, 2, 0, 0, 6, 22, 200, 1266, 11048, 93510, 956498, 10439562, 128784794, 1724594758 |
| Möbius | camel   | 1, 0, 6, 2, 2, 64, 150, 1454, 9114, 97966, 848378, 11091230, 125667676, 1860322066 |
| Möbius | zebra   | 1, 2, 6, 4, 6, 32, 270, 1226, 12102, 108926, 1129588, 12690196, 160440958, 2127637150 |
| Möbius | giraffe | 1, 2, 0, 24, 6, 24, 184, 1008, 12072, 113896, 1145510, 13237632, 159144390, 2173250724 |
| Klein  | knight  | 1, 0, 0, 0, 4, 4, 136, 628, 6740, 53280, 576360, 6374092, 80979240, 1111966112 |
| Klein  | camel   | 1, 0, 4, 0, 2, 64, 54, 612, 4100, 45992, 403342, 5605200, 66375330, 1023820044 |
| Klein  | zebra   | 1, 0, 2, 0, 0, 8, 28, 248, 3588, 31508, 409334, 4946760, 68113432, 963035384 |
| Klein  | giraffe | 1, 0, 0, 16, 0, 0, 56, 864, 4348, 34872, 414950, 5183944, 68196002, 993649808 |

The n = 14 column was staged in the b-files on 2026-07-20 by a single path and was
never recomputable by anything. All eight terms were recomputed here by `leap.c` and
again by `leap2.c`, and all eight held.

## The unit-scaling law — whose it is, and it is not ours

The torus row is full of coincidences (all four leapers give 10 at n = 5 and 210 at
n = 7; camel = giraffe at n = 13; zebra = giraffe at n = 14). They are explained by
the **unit-scaling theorem**. An adversarial prior-art scout was sent to kill that
claim and killed it, twice:

- **Externally.** W. D. Weakley, *"Toroidal queens graphs over finite fields"*,
  Australasian J. Combinatorics **57** (2013) 21–38, states it on p. 24 for the full
  `GL_2` in exactly this setting, with `Z_n` and the toroidal queens graph as his own
  worked example: for `M` in `GL_2(F)`, left multiplication by `M` "is a graph
  isomorphism from `G(F, D)` to `G(F, μ_M(D))`". His own word for the proof is that
  it is "easy to verify". Unit scaling is the case `M = uI`. More generally this is
  the *trivial direction* of Ádám's conjecture and the CI-group literature —
  multiplication by a unit is a group automorphism of `(Z/n)²`, the attack relation
  is a Cayley graph on that group, and "automorphism ⟹ isomorphic Cayley graph" is
  the direction nobody bothers proving.
- **In-house.** This project also proved and published it on 2026-07-03, in
  `research/leapers-on-a-torus/`, whose README already names three of the
  coincidences it forces. It was re-derived here from scratch before either was
  read. That is a rediscovery, and `torus-classes.mjs` says so at the top.

Two further corrections the scout forced, both deflationary and both now in the code:

- The theorem is stated too narrowly as scalars. `diag(u,v)` and the transpose swap
  work too, so the natural group is the **monomial subgroup** of `GL_2(Z/n)`.
  Verified here over n = 3..24: for these four leapers the larger group gives the
  identical partition, so the strengthening is free and moves no number.
- **Some of the coincidences are not coincidences.** Reduced mod n the vector sets
  can collide outright: mod 7, `4 ≡ −3` and `V` is closed under sign change, so the
  **camel and the giraffe are literally the same piece** and their equal counts need
  no theorem at all; mod 5 the knight and camel likewise coincide, and the zebra and
  giraffe both degenerate from 8 vectors to 4. The famous n = 7 four-way collapse is
  really *three* distinct move sets in one orbit plus a duplicate.
  `torus-classes.mjs` now prints the number of distinct move sets at each n so this
  cannot hide inside a claim about orbits.

And the phenomenon of different leapers sharing a toroidal count is itself published:
V. Kotěšovec, *Non-attacking chess pieces* (6th ed., 2013), ch. 10.4–10.9 — "Two
leapers [r,s] on a toroidal chessboard n × n … **Independent on r, s!**" His is a
*different mechanism*: his coincidences are a large-n phenomenon (he marks n ≤ 2s in
red as the range where leapers may still differ) under the k-pieces convention, while
every coincidence here is a small-n effect of vector sets colliding mod n. Adjacent
enough that not naming it would be a misrepresentation by omission.

What is left that is genuinely added is narrow, and worth exactly what it is: the
orbit partition computed at **every** n with every forced equality mechanically
checked (**17 of 17 independent merges, 21 of 21 unordered pairs** over n = 3..14 —
both tallies printed, because quoting one while meaning the other is what a miscount
looks like), a negative control that applies the same predictions to the Möbius band
and watches them collapse (**3 of 17**), and the forward claim in `PREREGISTERED.md`
— that the orbits are all singletons from n = 15 on, so the coincidences stop
permanently — filed in a commit that deliberately contains no n = 15 count.

**An unclosed hole in the search, stated as one.** Pólya's 1918 paper on the
doubly-periodic solutions of the n-queens problem could **not** be obtained
first-hand; every route reached it only through Ahrens' 1921 secondary account. Since
Pólya's method is explicitly about solutions generated by a repeated modular step,
the risk that the general argument is already there is real and unresolved. Nobody
here should make a priority claim about the modular-scaling argument until that paper
has actually been read.

## Files

- `engine.mjs` — the four-surface fold and two enumerators. `node engine.mjs <topo> <leaper|a b> <nlo> [nhi]`.
- `leap.c` — C backtracker, closed-form fold. `gcc -O3 -o leap leap.c -lm`.
- `leap2.c` — the fourth path: iterated deck generators, mask propagation, MRV. `gcc -O3 -o leap2 leap2.c`.
- `agree.mjs` — the cross-check, with coverage reporting and a self-test.
- `lift-check.mjs` — geometry by unfolding, with a positive control.
- `torus-classes.mjs` — the unit-scaling audit and its negative control.
- `density.mjs` — forbidden-pair counts per surface (and the guess it killed).
- `verify.mjs` — the fast 25-check correctness gate.
- `xcheck-king.mjs` — the king cross-check against `nonorientable-queens`.
- `oeis-check.mjs` — live OEIS search per sequence, with a positive control.
- `terms-1-14.tsv` — the full computed table.
- `PREREGISTERED.md`, `RECEIPT.md` — the forward prediction, and the dated full run.

## Why it counts (P2 criteria)

*Verifiable* — exact integer enumeration, now by four code paths that share no
geometry implementation and no search order. *Record-completing* — not an error but
a hole: the twisted members of a family the catalogue holds for the flat and
toroidal boards. *A finding beyond the numbers* — the torus scaling law, and exactly
where and why the non-orientable glue destroys it.

The same scout confirmed where the real contribution sits, and it is the counts, not
the law: direct OEIS sequence lookups on all four torus rows (full and windowed) and
full-text searches return nothing; the ten OEIS hits for "toroidal leaper" are all
wazirs. The two flanks of the hole exist — the flat permutation convention is
A137774 / A189358 / A189563 / A189565, and the toroidal k-pieces convention is
A172529–A173436 (knights) and A201236+ (wazirs) — and the toroidal *permutation*
convention is catalogued only for the non-skew leaper [1,1], which Kotěšovec (p. 626)
identifies with **A089222**, an entry whose OEIS name is the dinner-table problem and
carries no chess name at all. That near-neighbour is worth citing precisely because
it shows the convention is an established object rather than a local idiosyncrasy.

One trap for a future reader: **A370672** is titled "Number of ways of arranging
2n+1 nonattacking queens on a 2n+1 × 2n+1 toroidal board *using knight moves*"
(Vatutin, 2024). It is not this. It counts toroidal *queens* solutions generated by a
repeated step, not knight-leaper placements.

## The honest limit

An absent OEIS search is evidence of absence, not proof: these counts could be
defined in a paper under a name that never became a catalogue entry. The claim is
exactly *"uncatalogued as far as we found, 2026-07-13."* The gluing conventions are
the standard ones and are stated in the code, so a reader can adopt a different one
and recompute.

And the limit this session added, which is the honest reading of everything above:
four agreeing paths are four chances to catch a mistake, not a proof. They share the
**convention** — the vector set, the permutation constraint, the deck groups written
down in `engine.mjs` — and no amount of agreement between implementations can
certify the definition they all implement. What guards the definition is the king
cross-check against independently-authored code, the fold-versus-unfold check, and
the flat row landing on four sequences other people published. Those are the checks
that could have caught a wrong convention. The four-path agreement could not.
