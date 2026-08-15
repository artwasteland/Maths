# The Lucas-Lehmer map x² − 2 (mod n)

The functional graph of x² − 2 (mod n), the map at the heart of the Lucas-Lehmer primality test for Mersenne numbers, described by the same cycle statistics as the rho map above.

Documented on the Artificial Wasteland at [/strata/square-minus-two/](https://artwaste.land/strata/square-minus-two/).

## What is verified, and how far


Coverage for `lucas-lehmer-map` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

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

- `oversight/oeis/lucas-lehmer-map/` — the b-files, and `STAGED.md`, the notes written with them.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943913](https://doi.org/10.5281/zenodo.21943913)**

⚠ That DOI is **reserved, not yet registered**: Zenodo has earmarked it for this
deposit and it begins resolving when the deposit is published. Until then the link
above will not work, and this line says so rather than looking broken. The number
will not change.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
