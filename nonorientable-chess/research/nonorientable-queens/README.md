# research/nonorientable-queens — chess on surfaces that have only one side

A P2 *reach / Deepen* result (ledger P2: small true, citable discoveries). It counts
non-attacking **queens** on boards glued into four topologies — flat, torus, Möbius
strip, Klein bottle — and finds **three integer sequences absent from the OEIS**,
completing a family the catalogue already holds for the orientable boards.

Backs the immersive stratum **The Queen That Comes Back Upside Down**
(`/strata/chess-on-a-mobius-strip/`) and stages a submission bundle in
`oversight/oeis/nonorientable-queens/`.

## The idea, and why it is trustworthy

Bell & Stevens (2008) put the n-queens problem on the **Möbius board** — the ordinary
board with its left and right edges glued by a half-twist, so a queen sliding off the
right returns on the left *upside down* (row *i* carries over to row *n−1−i*). They
submitted **one** count to the OEIS: A137279, the number of ways to place ⌈n/2⌉
queens. The natural companions — the *total* number of non-attacking placements, the
number of non-attacking *pairs*, and everything on the torus and Klein bottle — were
never tabulated. Those are the gap.

The whole correctness argument is: **don't transcribe each surface's board-shape-
dependent diagonal algebra — ray-trace the attacks and prove the tracer right by
reproducing published counts.** `engine.mjs` steps each piece's lines of attack one
square at a time under an explicit seam rule, and it reproduces, exactly:

- flat n-queens → **A000170**,
- toroidal n-queens → **A007705**,
- Möbius ⌈n/2⌉-queens → **A137279**,

with both enumerators additionally calibrated against **A287227** (flat total),
**A036464** (flat pairs) and **A172517** (torus pairs). One ray-tracer, three
independent published grounds. The Klein-bottle numbers are the identical traced code
with the Klein identification (columns straight, rows flipped).

## What's verified — `node verify.mjs` → **85/85 pass** (~3–4 min)

1. attack model vs A000170 / A007705 / A137279;
2. both enumerators vs A287227 / A036464 / A172517;
3. internal consistency — the two counters agree (total = Σ_k C(k)), the attack
   graph is symmetric on every topology and piece, and a Möbius queen's E–W line
   lands exactly on rows {i, n−1−i} (the Bell–Stevens carry-over);
4. the new sequence values, asserted so a regression is caught, including the unique
   n=3 dip in the Möbius maximum.

## The new sequences (all confirmed absent from OEIS, 2026-07-06)

| sequence | terms |
|---|---|
| Möbius, total non-attacking placements | 2, 5, 10, 33, 146, 445, 2346, 8193, 49222, 175541, 1193094, 4593217, 34531602 |
| Möbius, two non-attacking queens | 0, 0, 0, 16, 80, 216, 504, 960, 1728, 2800, 4400, 6480, 9360, 12936, 17640, 23296, 30464, 38880 |
| torus, total non-attacking placements | 2, 5, 10, 49, 286, 1189, 6350, 41153, 217810, 1623941, 9326890, 87306481 |

A Klein-bottle total sequence is computed too but flagged **convention-dependent**
(on a non-orientable surface a queen's diagonal spirals and is not canonical) — staged
as exploration, not a catalogue claim. The clean Klein extension is **kings**, whose
one-square reach is unambiguous; left as the open next step.

## Files

- `engine.mjs` — the four-topology seam rule, ray-traced queen/king attacks, and exact
  enumerators (`countExactK`, `independenceStats`). `node engine.mjs <topo> <piece> <n> [k]`.
- `verify.mjs` — the 85-check correctness gate.
- `verify-page.mjs` — drives the built immersive page headless (desktop + mobile),
  asserting no errors, no overflow, and that the live counts match the engine.
- `../../oversight/oeis/nonorientable-queens/derive.mjs` — regenerates the staged b-files.

## Why it counts (P2 criteria)

*Verifiable* — exact integer enumeration, the counter reproduced three published
sequences before it was believed. *Adopted* — staged for a Zenodo DOI / human OEIS
authorship (`.zenodo.json` ready; the AI-authorship line means the project does not
submit to OEIS itself). *Record-completing* — not an error, but a hole: the twisted
members of a family the catalogue already holds for the flat and toroidal boards.
