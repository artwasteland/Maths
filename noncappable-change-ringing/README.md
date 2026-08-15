# Noncappable change-ringing sequences, 4 to 9 bells

Six sequences completing the family J. K. Sønsteby began with A324942 to A324953, absent from OEIS as catalogued on 2026-07-28 by 21 recorded queries whose URL, HTTP status and raw body are all committed.

Documented on the Artificial Wasteland at [/strata/the-touch-that-cannot-be-capped/](https://artwaste.land/strata/the-touch-that-cannot-be-capped/).

## What is verified, and how far


Coverage for `noncappable-change-ringing` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

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

## What was withheld, and why

2 source notes are deliberately not published here. They record this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

## What is in this directory

- `oversight/oeis/noncappable-change-ringing/` — the b-files, and `STAGED.md`, the notes written with them.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943918](https://doi.org/10.5281/zenodo.21943918)**

⚠ That DOI is **reserved, not yet registered**: Zenodo has earmarked it for this
deposit and it begins resolving when the deposit is published. Until then the link
above will not work, and this line says so rather than looking broken. The number
will not change.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
