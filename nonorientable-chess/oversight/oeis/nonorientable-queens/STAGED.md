# oversight/oeis/nonorientable-queens

Non-attacking **queens** on boards whose edges are glued into different surfaces —
the **torus**, the **Möbius strip**, and the **Klein bottle**. The orientable
members of this little family are catalogued in the OEIS; several twisted ones are
not. This directory stages the genuinely-new counts, each **confirmed absent from
the OEIS on 2026-07-06**.

Backs the stratum **The Queen That Comes Back Upside Down**
(`/strata/chess-on-a-mobius-strip/`) and the notebook
`research/nonorientable-queens/`.

## Why these are trustworthy

The one thing that makes a new count worth anything is that the counter is right.
The engine (`research/nonorientable-queens/engine.mjs`) ray-traces each piece's
lines of attack under an explicit seam rule, and it is validated by reproducing
**three independently-published sequences exactly** before it computes anything new:

- flat *n*-queens → **A000170** (1, 0, 0, 2, 10, 4, 40, 92, 352, …),
- toroidal *n*-queens → **A007705** (odd *n*: 1, 10, 28, 88, …),
- Möbius ⌈n/2⌉-queens → **A137279** (Bell & Stevens 2008: 1, 4, 0, 16, 40, 192, …).

Both enumerators are further calibrated against **A287227** (flat total independent
sets), **A036464** (flat non-attacking pairs) and **A172517** (toroidal pairs). The
full gate — `node research/nonorientable-queens/verify.mjs`, **85/85** — also checks
that the attack graph is symmetric and that a Möbius queen's east–west line lands
exactly on rows {i, n−1−i}. Only then are the new terms believed.

## Conventions

Board coordinates and the Möbius gluing are those of **Jordan Bell & Brett Stevens,
"Results for the n-queens problem on the Möbius board," *Australasian J. Combin.*
42 (2008) 21–34** (`ajc_v42_p021.pdf`): rows 0…n−1, columns 0…n−1, left/right edges
joined with a half-twist so row *i* carries over to row *n−1−i*. The torus is the
standard modular board. See the honest caveat on the Klein bottle below.

## What is staged (all confirmed absent from OEIS, 2026-07-06)

Indexed by board size *n* (offset 1). "Total placements" = number of independent
sets in the queen graph **including the empty placement** — the same convention
A287227 uses for the flat board. Regenerate every b-file with
`node oversight/oeis/nonorientable-queens/derive.mjs`.

### Validated-convention sequences (Möbius, torus) — the real additions

| quantity | board | terms | b-file | flat/torus sibling in OEIS |
|---|---|---|---|---|
| total non-attacking placements | Möbius | 2, 5, 10, 33, 146, 445, 2346, 8193, 49222, 175541, 1193094, 4593217, 34531602 | `b-mobius-total.txt` | A287227 (flat) |
| two non-attacking queens | Möbius | 0, 0, 0, 16, 80, 216, 504, 960, 1728, 2800, 4400, 6480, 9360, 12936, 17640, 23296, 30464, 38880 | `b-mobius-pairs.txt` | A036464 (flat), A172517 (torus) |
| total non-attacking placements | torus | 2, 5, 10, 49, 286, 1189, 6350, 41153, 217810, 1623941, 9326890, 87306481 | `b-torus-total.txt` | A287227 (flat) |

Structural note recorded from the same computation: the maximum non-attacking queens
on the *n×n* Möbius board is ⌈n/2⌉ for every *n* ≤ 13 **except n = 3**, where it is 1
(the 3×3 Möbius board cannot hold ⌈3/2⌉ = 2 non-attacking queens — consistent with
A137279's a(3) = 0). The count of maximum placements equals A137279 exactly for
n ≥ 4, so it is not staged as a separate sequence.

### Convention-dependent (Klein bottle) — staged as exploration, not a canonical claim

| quantity | board | terms | b-file |
|---|---|---|---|
| total non-attacking placements | Klein | 2, 5, 10, 17, 66, 133, 946, 1729, 10234, 26501, 148578, 339409 | `b-klein-total.txt` |

**Honest caveat.** On a non-orientable surface a queen's *diagonal* is not
canonical: traced across the twisted seam it does not close after a short loop the
way a torus diagonal does — it spirals, so a Klein-bottle queen attacks most of the
board, and the exact counts depend on how one decides a diagonal continues past the
flip. Unlike the Möbius board, no published convention anchors this. The Klein terms
are exact **for the gluing defined in the engine** (columns straight, rows flipped)
and are offered as a curiosity, not a submission-ready claim. The clean way to extend
the family to the Klein bottle is with **kings** (whose one-square reach is
unambiguous under any gluing) — left as the open next step.

## The AI-authorship line (why nothing here is auto-submitted)

OEIS forbids AI-authored and automated submissions, and the reason — that a language
model will tell you what you want to hear regardless of the truth — is exactly the
failure this project's never-lie rule exists to refuse. So these files are **not**
paste-ready OEIS drafts. The *mathematics* is sound (exact enumeration, three-way
validated against published ground truth, absence-checked); the *authoring* must be
done by a human who has independently verified it and stands behind it. The staged
artifact is offered two honest ways: **(1)** deposit the reproducible bundle (engine
+ verifier + b-files) on Zenodo for a citable DOI (no authorship problem —
`.zenodo.json` is ready); **(2)** offer the verified computation to a mathematician
who will check it and, if convinced, submit to OEIS as themselves. See
`oversight/oeis/README.md` and request 005.

If you find any of these already published, that correction belongs at the
deposition door — the claim is only "absent from the catalogue as of 2026-07-06."
