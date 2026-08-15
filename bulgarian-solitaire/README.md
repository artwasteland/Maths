# Settling times of Bulgarian solitaire and its s-generalisation

Bulgarian solitaire: a hand is a partition of *n*; one move takes a card from every pile and makes them into one new pile. It always becomes periodic. The staged sequence is the **total settling time**, the sum over all p(n) partitions of the number of moves each needs to first become periodic, plus the same statistic for Brian Hopkins's *s*-generalisation.

Documented on the Artificial Wasteland at [/strata/the-longest-way-home/](https://artwaste.land/strata/the-longest-way-home/), [/strata/the-longer-way-home/](https://artwaste.land/strata/the-longer-way-home/).

## What is verified, and how far

Of the 55 staged terms here, **55 recomputed** (measured by `bind-staged.mjs --full`, not asserted).

| b-file | staged | recomputed | drift-guarded | unbound |
|---|---:|---:|---:|---:|
| `bulgarian-solitaire-settling/b-file.txt` | 55 | 55 | 0 | 0 |

Coverage for `generalized-bulgarian-solitaire` is stated in that directory's own `STAGED.md` and enforced by its own `verify-staged.mjs`; it is not part of the table above and does not borrow its authority.

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

- `oversight/oeis/bulgarian-solitaire-settling/` — the b-files, and `STAGED.md`, the notes written with them.
- `oversight/oeis/generalized-bulgarian-solitaire/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/bulgarian-solitaire/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
