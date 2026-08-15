# Topswops: total steps over all decks, and the Garden of Eden

Conway's **Topswops**: read the top card k of a shuffled deck of 1..n and, unless k = 1, reverse the top k cards; repeat. It always terminates, and why is not obvious. Staged here: the **total** number of steps summed over all n! decks, and the count of decks that no move can produce.

Documented on the Artificial Wasteland at [/strata/topswops-machine/](https://artwaste.land/strata/topswops-machine/).

## What is verified, and how far


Coverage for `topswops-total-flips` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

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

- `oversight/oeis/topswops-total-flips/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/topswops/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
