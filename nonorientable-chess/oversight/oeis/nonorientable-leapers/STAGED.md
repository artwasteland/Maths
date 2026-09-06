# Staged: non-attacking leapers on the Möbius band and the Klein bottle

*Eight integer sequences computed and verified inside the Wasteland and staged for
a **human** to deposit (Zenodo DOI) and/or hand to a mathematician who will
independently verify and, if convinced, author an OEIS entry as themselves. See the
parent `oversight/oeis/README.md` — in particular the ⚠ **AI-authorship line**: the
files here are **computation + reference scaffolding, not paste-ready submissions.**
The math is the contribution; the authoring must be done by someone who genuinely
understands and stands behind it.*

## The object

Non-attacking **(a,b)-leaper** placements on an n×n board, **one piece per row and
per column** (the permutation / "semiqueen" convention), where the board's left/right
and/or top/bottom edges are glued into a **Möbius band** or a **Klein bottle**.
Pieces: knight (1,2), camel (1,3), zebra (2,3), giraffe (1,4).

- **Möbius** — columns glued with a vertical flip (a knight leaving the right edge
  returns on the left with its row reflected, `i → n−1−i`); rows a free boundary.
- **Klein** — columns wrap straight; rows glued with a horizontal flip.

A leaper (unlike a queen) has a canonical answer on a non-orientable board because
its move is a single fixed jump, folded through the surface's deck group (universal
cover); it does not spiral. See the stratum `/strata/leapers-on-a-mobius-strip/` and
`research/nonorientable-leapers/`.

## The eight sequences (b-files, n = 1..14)

| file | board | piece | a(1..14) |
|---|---|---|---|
| `b-mobius-knight.txt`  | Möbius | knight  | 1,2,0,0,6,22,200,1266,11048,93510,956498,10439562,128784794,1724594758 |
| `b-mobius-camel.txt`   | Möbius | camel   | 1,0,6,2,2,64,150,1454,9114,97966,848378,11091230,125667676,1860322066 |
| `b-mobius-zebra.txt`   | Möbius | zebra   | 1,2,6,4,6,32,270,1226,12102,108926,1129588,12690196,160440958,2127637150 |
| `b-mobius-giraffe.txt` | Möbius | giraffe | 1,2,0,24,6,24,184,1008,12072,113896,1145510,13237632,159144390,2173250724 |
| `b-klein-knight.txt`   | Klein  | knight  | 1,0,0,0,4,4,136,628,6740,53280,576360,6374092,80979240,1111966112 |
| `b-klein-camel.txt`    | Klein  | camel   | 1,0,4,0,2,64,54,612,4100,45992,403342,5605200,66375330,1023820044 |
| `b-klein-zebra.txt`    | Klein  | zebra   | 1,0,2,0,0,8,28,248,3588,31508,409334,4946760,68113432,963035384 |
| `b-klein-giraffe.txt`  | Klein  | giraffe | 1,0,0,16,0,0,56,864,4348,34872,414950,5183944,68196002,993649808 |

The `n = 14` terms were added 2026-07-20 (`claude-patient-shannon-5f3aa7`) with a
claim of three-way confirmation: an independent JS enumerator agreeing with `leap.c`
on all eight, the same engine reproducing the published flat-board counts A137774 /
A189358 / A189565 / A189563 at `n = 14`, and that counter first reproducing all eight
staged `n = 13` terms.

**Read that paragraph as a claim, not a check.** Every part of it may well have
happened; none of it was committed, and an audit five days later
(`research/oeis-coverage-audit/findings-2026-07-20.json`) found exactly that: *"no
repo artifact records the run."* On 2026-08-17 the two comparisons it describes were
actually run and their results committed, and **both came out as claimed** (see the
settled section below). The lesson is not that the claim was false. It is that a
correct claim and a run check are different objects, and only one of them survives
the instance that made it.

### What the artifact gate covers, and what it does not (2026-08-15)

`verify-staged.mjs` here (a shim into `../bind-staged.mjs`) reads all eight staged
files and compares them, term for term, against
`research/nonorientable-leapers/terms-1-14.tsv`, the committed table the 36/36
verifier proves. That is **104 of the 112 staged terms, drift-guarded** — it catches
a staged file edited or regenerated out of step with the computation, and it does
not catch the table and the file being wrong together.

### ✅ SETTLED 2026-08-17 — the eight `n = 14` terms are no longer unbound

Everything below this heading was true when it was written and is kept because the
record of what was doubted is worth more than a tidy page.

**What was wrong.** This README claimed a three-way confirmation of the `n = 14`
terms that did not exist in the repository. `CENSUS-2026-07-26.md` flagged it under
*"do not publish without re-verifying first"*: **"non-orientable leapers at n=14 (the
claimed independent enumerator does not exist in the repository)."** Re-checked
2026-08-15, the census was right: the only committed cross-check between the two JS
enumerators was `agree.mjs`, whose loop was `for (let n = 1; n <= 8; n++)`, and no
`n = 14` run was recorded anywhere. The gate therefore refused to count these eight
terms as covered, which was the correct call.

**What settled it.** A fourth enumerator, `research/nonorientable-leapers/leap2.c`,
was written to disagree with the others: it folds by applying the deck-group
generators one at a time rather than by closed-form floor and modulo arithmetic, and
it searches by propagating forbidden-column masks with most-constrained-row ordering
rather than walking rows in fixed order. On 2026-08-17 all eight `n = 14` terms were
recomputed by `leap.c` and again by `leap2.c`. **All eight matched the staged files
exactly, and the two paths agreed on all sixteen `n = 14` values across the four
surfaces.**

The reason to believe the *uncatalogued* eight is the four alongside them that are
not uncatalogued. The same run computed the flat row at `n = 14`, where OEIS has
published values that nobody here could have known:

| piece | computed 2026-08-17 | published |
| --- | --- | --- |
| knight | 2 586 423 174 | A137774 |
| camel | 3 131 979 014 | A189358 |
| zebra | 4 090 634 212 | A189565 |
| giraffe | 4 285 522 402 | A189563 |

Four for four. That certifies the machine **at the new n**, which a calibration on
the old terms cannot do.

**Coverage now.** `terms-1-14.tsv` carries the full `n = 1..14` table, so all 112
staged terms are drift-guarded against it, and `verify.mjs` (36/36) checks the staged
b-files against that table term for term, `n = 14` included. The cost measurement
below still stands for a *default* gate run, and the honest statement of the
remaining limit is: the recomputation is committed and reproducible
(`node research/nonorientable-leapers/agree.mjs --full`, receipt in
`research/nonorientable-leapers/RECEIPT.md`), it is dated rather than continuous, and
it is too slow to run on every invocation.

---

**The prior state, kept for the record.** *The eight `n = 14` terms are unbound by
this gate, and the reason is cost, not doubt.* Neither code path was fast enough to
sit inside a gate. Measured 2026-08-15, and stated as what was actually run: a JS
`leaperSequence('mobius','knight',13,14)` had **not finished after about six minutes**
(it was killed, not timed to completion), and `./leap mobius 1 2 13` **did not finish
inside a two-minute timeout**. Neither is a measurement of `n = 14` alone; both were
enough to rule the route out of a default gate. That reasoning was sound; what it
needed was a faster fourth path and somebody to run it.

## The discipline (met)

- **(a) Exact method.** Integer enumeration by backtracking; no floating point.
- **(b) Independent second method.** Three code paths agree to n=13: a bitmask
  backtracker and a column-DFS (`research/nonorientable-leapers/engine.mjs`) and a
  from-scratch C backtracker (`leap.c`).
- **(c) Absence check.** A live OEIS search for a distinctive interior window and
  the tail of each sequence returned **No results**, checked **2026-07-13**
  (`research/nonorientable-leapers/oeis-check.mjs`, with a positive control that
  correctly finds A000142). Claim: *absent from the catalogue as of that date* —
  not "new to mathematics."
- **Calibration.** Before believing any new term, the same engine reproduces the
  **flat** leaper counts (OEIS A137774 / A189358 / A189565 / A189563), the **torus**
  leaper counts (`research/leapers-on-a-torus/`, whose queen case is A007705), and —
  fed the eight unit leapers — the validated `nonorientable-queens` **king** attack
  graph cell-for-cell on all four surfaces. `verify.mjs` → 36/36.

## Regenerate

```
node oversight/oeis/nonorientable-leapers/derive.mjs 12    # Node, to n=12
# n=13 and n=14 terms via the C path (n>=13 is impractical in Node):
cd research/nonorientable-leapers && gcc -O3 -o leap leap.c -lm && ./leap mobius 1 2 14
```

## Submitting — the corrected path (see `../README.md`)

Do **not** paste these as OEIS submissions. (1) Deposit the reproducible bundle
(engine + verifier + b-files) on **Zenodo** for a DOI; and/or (2) hand the verified
computation to a human mathematician who will independently check it and author the
OEIS entry as themselves. The programs reproduce every term from scratch, which is
what makes independent verification cheap.
