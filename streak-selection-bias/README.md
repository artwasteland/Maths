# Streak-selection bias (Miller and Sanjurjo), as exact rationals

The expected proportion of heads on the flip immediately following a heads, averaged over all fair-coin sequences of length n that contain such a flip. It is **not one half**, which is the Miller and Sanjurjo finding that reopened the hot-hand debate. Staged as exact numerators and denominators, 21 terms each.

This result has no companion page on the Artificial Wasteland yet.

## What is verified, and how far


Coverage for `streak-selection-bias` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

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

- `oversight/oeis/streak-selection-bias/` — the b-files, and `STAGED.md`, the notes written with them.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943932](https://doi.org/10.5281/zenodo.21943932)**

Assigned by Zenodo for this deposit. If that link does not resolve, the deposit is
still a draft awaiting publication; the number is fixed either way and does not
change when it is published.

<!-- Worded to be true before AND after publication on purpose. This file is
     frozen into the deposit, so a sentence that is only true while the deposit
     is a draft would become a false statement in a permanent record the moment
     somebody pressed publish. -->

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
