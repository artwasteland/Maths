# oversight/oeis/nonorientable-kings

Non-attacking **kings** on `n×n` boards whose edges are glued into different
surfaces — the flat board, the **torus**, the **Möbius strip**, and the **Klein
bottle**. A non-attacking king placement is exactly an *independent set in the king
graph* of the surface. The two **orientable** boards are already in the OEIS; the
two **non-orientable** boards are not. This directory stages the two new sequences,
each **confirmed absent from the OEIS on 2026-07-12**.

Backs the stratum **The King That Doesn't Spiral**
(`/strata/kings-on-a-klein-bottle/`) and the notebook
`research/nonorientable-queens/` (shared engine; kings-specific counter and gate).

## Why kings, and why this is the *clean* extension

The companion queen study
(`/strata/chess-on-a-mobius-strip/`, `oversight/oeis/nonorientable-queens/`) had to
flag its Klein-bottle numbers as **convention-dependent**: a queen's *diagonal* is
not canonical on a non-orientable surface — traced across the twisted seam it does
not close after a short loop, it spirals, and the count depends on how you decide a
diagonal continues past the flip. It left the honest fix explicit: *"The clean way
to extend the family to the Klein bottle is with **kings** (whose one-square reach
is unambiguous under any gluing) — left as the open next step."* This directory is
that step. A king reaches only the eight squares around it; that reach is fully
determined by the gluing on **every** surface. So the Klein-bottle king counts are
**canonical**, not a curiosity — the first fully unambiguous non-orientable member
of the family.

## Why these are trustworthy (never one code path)

Two structurally unrelated exact counters must agree on every overlapping term:

- **(A) ray-trace + DFS** — `research/nonorientable-queens/engine.mjs` traces each
  king's 8 neighbours through an explicit seam rule and DFS-enumerates every
  independent set. This is the same engine already validated against three
  *published queen* sequences (A000170, A007705, A137279).
- **(B) transfer matrix** — `research/nonorientable-queens/kings-transfer.mjs` sweeps
  the board one line at a time over valid line-states, with an explicit bit-reversal
  at each flip seam. Completely different machinery.

They agree for **all n = 1..7** on all four surfaces. And (B) reproduces **two
published king sequences exactly**:

- flat kings → **A063443** ("binary arrangements without adjacent 1's on n×n board")
  — matched for n = 1..13;
- toroidal kings → **A067958** ("… on n×n torus connected e-w ne-sw n-s nw-se")
  — matched for n = 2..13.

Only after clearing both published grounds are the two non-orientable sequences
believed. Full gate: `node research/nonorientable-queens/verify-kings.mjs`
(**23/23**).

### What the 23/23 did and did not pin (2026-08-15)

An audit asked what covers **this** directory's staged files, since it has no
verifier under its own name. Reading `verify-kings.mjs`: it computes `kingTotal`
for `n = 1..13` on both boards, then asserts `.slice(0, 6)` against literal values
and checks the whole array is strictly increasing. So **6 of the 26 staged terms
were pinned to a value; the other 20 were guarded by "the sequence goes up"**,
which almost nothing can fail. Not wrong, just much weaker than 23/23 sounds.

`verify-staged.mjs` here (a shim into `../bind-staged.mjs`) closes that:
**all 26 staged terms are recomputed from the transfer matrix and compared to the
file, in about 63 s.** What that does *not* do is make them two-path at the top:
counter **(A)** and counter **(B)** still agree only to `n = 7`, because the
ray-tracing enumerator cannot reach further. For `n = 8..13` these numbers rest on
the transfer matrix alone, and the reason to trust it there is external: the same
machinery reproduces **A063443** and **A067958** at `n = 13`, which is ground truth
for the method at the right magnitude but not for the non-orientable counts
themselves.

`../CENSUS-2026-07-26.md` had already put this on its *"do not publish without
re-verifying first"* list, as **"non-orientable kings n=8 to 13 (single path despite
the label)"**. That flag stands. The gate closes the artifact half of it (the staged
file now matches a live recomputation of every term) and does not close the
independence half (above `n = 7` there is still one path).

## Convention

Board coordinates and the Möbius/Klein gluings are those of the shared engine:
rows `0…n−1` top→bottom, columns `0…n−1` left→right.
- **Möbius** — left/right edges joined with a half-twist (row `i` carries over to
  row `n−1−i`); top/bottom free. (Same board as Bell & Stevens 2008 for queens.)
- **Klein bottle** — left/right joined straight, top/bottom joined with a
  horizontal flip (column `c` carries over to column `n−1−c`).

**Offset & the `n=1` degeneracy.** Offset `1`; `a(1)=2` on every surface under the
convention *a king never attacks its own square*. Note that **A067958 uses `a(1)=1`**
for the torus: on a `1×1` torus every direction wraps back to the single cell, and
A067958 counts that as a self-attack (only the empty arrangement survives). The two
conventions differ **only at n=1**; they agree for all n ≥ 2. We keep the
no-self-attack convention (a piece does not attack the square it stands on) and note
the discrepancy here rather than silently re-indexing.

## What is staged (both confirmed absent from OEIS, 2026-07-12)

"Total placements" = number of independent sets in the king graph **including the
empty placement** — the convention A063443/A067958 use. Regenerate the b-files with
`node oversight/oeis/nonorientable-kings/derive.mjs` (a few seconds).

| quantity | board | terms (n=1…13) | b-file | orientable sibling in OEIS |
|---|---|---|---|---|
| total non-attacking king placements | Möbius | 2, 5, 21, 191, 3125, 90917, 4821373, 456381347, 78532374321, 24216949807317, 13514204184370867, 13562258690209832541, 24571944238751976479381 | `b-mobius-total.txt` | A063443 (flat), A067958 (torus) |
| total non-attacking king placements | Klein | 2, 5, 10, 129, 1433, 42502, 1809099, 157128897, 22966349906, 6282135540891, 3035036314128983, 2672749503556098950, 4217585699195883821109 | `b-klein-total.txt` | A063443 (flat), A067958 (torus) |

### Structural facts recorded from the same computation

These are exact byproducts, offered as `%C` comment material — not staged as
separate sequences.

1. **The twin paradox.** The torus and Klein-bottle king graphs have the **same
   number of edges** (both are 8-regular for `n≥3`, `4n²` edges), so their
   *non-attacking-pair* counts are identical. Yet the graphs are not isomorphic. The
   total-placement counts are equal for `n = 1, 2, 3` (`2, 5, 10`) and **first
   diverge at `n = 4`** (torus `133`, Klein `129`).
2. **The divergence is a densest-packing effect.** At `n = 4` the two surfaces admit
   the *same* number of placements of `0, 1, 2, 3` kings (`1, 16, 56, 48`); they
   differ **only** at the maximum, `4` kings — the torus packs `12` ways, the Klein
   bottle only `8`. The twist removes exactly the four densest packings.
3. **Parity of the winner.** For `n ≥ 4`, `sign(torus − Klein)` alternates with the
   parity of `n`: the **torus** admits more placements on **even** boards, the
   **Klein bottle** more on **odd** boards (verified n = 4..13). The plausible
   mechanism is the flip seam's fixed column — the map `c ↦ n−1−c` has a fixed
   column iff `n` is odd — but this is an *observed, exactly-computed pattern*, not a
   theorem, and is stated as such.

## The AI-authorship line (why nothing here is auto-submitted)

OEIS forbids AI-authored and automated submissions, and rightly. These files are
**not** paste-ready OEIS drafts. The *mathematics* is sound (exact, two-method,
validated against two published king sequences, absence-checked on two windows); the
*authoring* must be done by a human who has independently verified it and stands
behind it. Two honest routes: **(1)** deposit the reproducible bundle on Zenodo for a
citable DOI (`.zenodo.json` is ready — no authorship problem); **(2)** offer the
verified computation to a mathematician to check and submit to OEIS as themselves.
See `oversight/oeis/README.md` and the hand-off request.

If you find either already published, that correction belongs at the deposition
door — the claim is only "absent from the catalogue as of 2026-07-12."
