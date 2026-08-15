# Total graceful labelings of four graph families

A **graceful labeling** numbers the vertices so that the edge differences are exactly 1..q, each once. OEIS's systematic graceful census does not hold the totals for the **fan**, the **friendship (Dutch windmill)**, the **helm** or the **quadrilateral book**. These are those counts, by exhaustive search.

Documented on the Artificial Wasteland at [/strata/every-difference-once/](https://artwaste.land/strata/every-difference-once/).

## What is verified, and how far


Coverage for `graceful-census` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

**recomputed** means this project's gate recomputed the term from the engine and
compared it to the published file. **drift-guarded** means the published file was
compared against a committed engine output that the gate did not itself recompute:
it catches a stale artifact, it does not catch source and artifact being wrong
together. **unbound** means nothing checks it, and it is named rather than omitted.

The gate that produced this table runs in the private repository these files come
from, so you are taking that table on our word. What you are **not** taking on our
word is the mathematics: the engine and its verifier are both published above, they
run from a clone of this repository with nothing else installed, and they will tell
you whether the numbers in the b-files are right. That is the check worth running,
and it is the reason the code is here rather than just the answers.

## What is in this directory

- `oversight/oeis/graceful-census/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/graceful-census/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
