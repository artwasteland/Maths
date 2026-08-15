# research/nonorientable-leapers — leapers on boards with only one side

A P2 *deepen / small-true-discovery* result (ledger P2: small true, citable
discoveries). It counts **non-attacking (a,b)-leaper placements, one piece per row
and per column** — the permutation / "semiqueen" convention — on boards glued into
four topologies (flat, torus, Möbius band, Klein bottle), for the knight (1,2),
camel (1,3), zebra (2,3) and giraffe (1,4), and finds **eight integer sequences
absent from the OEIS** (the Möbius and Klein rows), completing a family the
catalogue already holds for the orientable boards.

Backs the immersive stratum **Leapers on a Möbius Strip**
(`/strata/leapers-on-a-mobius-strip/`) and stages a deposition bundle in
`oversight/oeis/nonorientable-leapers/`. It is the crossing of two earlier
programs: the leapers of `research/leapers-on-a-torus/` (orientable glue) meet the
twisted boards of `research/nonorientable-queens/` (which flagged a bounded-move
piece as "the clean twisted extension" — exactly what a leaper is).

## The object, precisely

A placement is a permutation `π` of `{0,…,n−1}`: the piece in row `i` sits in
column `π(i)` (so one-per-row-and-column holds by construction). Two pieces attack
iff, under the surface's gluing, one sits a leaper's jump from the other.

## Why a leaper is canonical here (and a queen is not)

On a non-orientable board a *slider*'s diagonal spirals around the twist and its
"attack set" depends on a convention (this is why `nonorientable-queens` flagged
the Klein queen as convention-dependent). A **leaper makes a single fixed-vector
jump**, so its landing square is defined by the standard **universal-cover rule**:
lift the board to its cover (the infinite plane; the infinite strip for the Möbius
band), read the leaper's vector `(dr,dc)` there, and fold the target back through
the surface's deck group. This is **trajectory-independent** — it does not depend
on "which way round the L" — precisely *because* the move is one jump, not a swept
ray. `engine.mjs :: foldCell` implements the fold for each surface:

- **torus** — both axes wrap straight.
- **mobius** — an open *band*: columns glued with a vertical flip (`g:(R,C) →
  (n−1−R, C+n)`), rows a free boundary that a jump can fall off. Row `i` carries
  over to row `n−1−i` across the seam (the Bell–Stevens 2008 carry-over).
- **klein** — closed: columns wrap straight, rows glued with a horizontal flip
  (`t_R:(R,C) → (R+n, n−1−C)`).

## Correctness — `node verify.mjs` → **25/25 PASS** (~1–2 min)

The fold is pinned to FOUR independent published grounds before any new term is
believed:

1. **flat = OEIS.** Flat leaper permutation counts reproduce **A137774** (knight /
   "non-attacking empresses"; the rook part of the empress *is* the one-per-row-and-
   column rule) and Kimberling's **A189358 / A189565 / A189563** (camel / zebra /
   giraffe), including `A137774(13) = 197 708 058` computed from scratch.
2. **torus = the previous stratum.** Torus counts reproduce
   `research/leapers-on-a-torus/` bit-for-bit (knight `1,2,0,8,10,72,210,1408,…`),
   whose queen case is A007705 and whose C code independently reaches n=13.
3. **king cross-check certifies the twisted geometry.** A king is the eight *unit*
   leapers; fed those, the model reproduces the already-validated
   `nonorientable-queens` king attack graph **cell-for-cell on all four topologies**
   — the one move where universal-cover and single-step must agree (816 cells).
4. **two enumerators + C.** A bitmask backtracker and a column-DFS agree, and
   `leap.c` (an independent re-implementation of the fold) agrees again to n=13.

verify.mjs also asserts the structural finding: the torus unit-scaling collapse
(all four leapers → 210 at n=7) is **broken** by the twist.

## The new sequences (Möbius + Klein; absent from OEIS, 2026-07-13)

`n = 1..13`, one piece per row and column. Full table: `terms-1-13.tsv`.

| board | piece | terms |
|---|---|---|
| Möbius | knight  | 1, 2, 0, 0, 6, 22, 200, 1266, 11048, 93510, 956498, 10439562, 128784794 |
| Möbius | camel   | 1, 0, 6, 2, 2, 64, 150, 1454, 9114, 97966, 848378, 11091230, 125667676 |
| Möbius | zebra   | 1, 2, 6, 4, 6, 32, 270, 1226, 12102, 108926, 1129588, 12690196, 160440958 |
| Möbius | giraffe | 1, 2, 0, 24, 6, 24, 184, 1008, 12072, 113896, 1145510, 13237632, 159144390 |
| Klein  | knight  | 1, 0, 0, 0, 4, 4, 136, 628, 6740, 53280, 576360, 6374092, 80979240 |
| Klein  | camel   | 1, 0, 4, 0, 2, 64, 54, 612, 4100, 45992, 403342, 5605200, 66375330 |
| Klein  | zebra   | 1, 0, 2, 0, 0, 8, 28, 248, 3588, 31508, 409334, 4946760, 68113432 |
| Klein  | giraffe | 1, 0, 0, 16, 0, 0, 56, 864, 4348, 34872, 414950, 5183944, 68196002 |

The unit-scaling collapse and its breakage: at n=7 the torus welds all four leapers
to **210**; the Möbius band splits them (200 / 150 / 270 / 184) and the Klein bottle
splits them again (136 / 54 / 28 / 56). The twist removes the symmetry that welded
them.

## Files

- `engine.mjs` — the four-surface fold, the universal-cover leaper attack model,
  two independent permutation enumerators, and the free-placement stats.
  `node engine.mjs <topo> <leaper|a b> <nlo> [nhi]`.
- `leap.c` — independent C backtracker (the third code path), reaches n=13.
  `gcc -O3 -o leap leap.c -lm && ./leap mobius 1 2 13`.
- `verify.mjs` — the 25-check correctness gate.
- `xcheck-king.mjs` — the king cross-check against `nonorientable-queens` alone.
- `oeis-check.mjs` — live OEIS search per sequence (with a positive control).
- `terms-1-13.tsv` — the full computed table.
- `../../oversight/oeis/nonorientable-leapers/` — the staged deposition bundle.

## Why it counts (P2 criteria)

*Verifiable* — exact integer enumeration; the model reproduced five published
sequences (four OEIS + the torus stratum) and one validated in-repo king graph
before it was believed. *Record-completing* — not an error but a hole: the twisted
members of a family the catalogue holds for the flat and toroidal boards. *A finding
beyond the numbers* — the torus scaling symmetry, and exactly where and why the
non-orientable glue destroys it.

## The honest limit

An absent OEIS search is evidence of absence, not proof: these counts could be
defined in a paper under a name that never became a catalogue entry. The claim is
exactly *"uncatalogued as far as we found, 2026-07-13."* The gluing conventions are
the standard ones and are stated in the code, so a reader can adopt a different one
and recompute.
