# Penney's game as a tournament: nontransitivity over a fair q-sided die

Penney's game played with a fair *q*-sided die. At word length *k* the *q^k* words form a tournament with an edge A → B whenever A appears first with probability over one half. Staged here: the tied pairs, directed 3-cycles, transitive triples, maximum out-degree and distinct win-probabilities, for q = 2, 3, 4 and 5. **The headline is that the coin is the special case**: for a coin, nontransitivity starts at k=3 but the first directed *triangle* waits until k=4; for every die with three or more faces the two arrive together.

Documented on the Artificial Wasteland at [/strata/no-triangle-at-three/](https://artwaste.land/strata/no-triangle-at-three/), [/strata/penney-dice/](https://artwaste.land/strata/penney-dice/), [/strata/a-triangle-at-two/](https://artwaste.land/strata/a-triangle-at-two/).

## What is verified, and how far

Of the 128 staged terms here, **128 recomputed** (measured by `bind-staged.mjs --full`, not asserted).

| b-file | staged | recomputed | drift-guarded | unbound |
|---|---:|---:|---:|---:|
| `penney-tournament/b-cyc3.txt` | 10 | 10 | 0 | 0 |
| `penney-tournament/b-distinctp.txt` | 12 | 12 | 0 | 0 |
| `penney-tournament/b-maxout.txt` | 12 | 12 | 0 | 0 |
| `penney-tournament/b-ties.txt` | 12 | 12 | 0 | 0 |
| `penney-tournament/b-transtri.txt` | 10 | 10 | 0 | 0 |
| `penney-mary/b-m5-cyc3.txt` | 4 | 4 | 0 | 0 |
| `penney-mary/b-m5-maxout.txt` | 4 | 4 | 0 | 0 |
| `penney-mary/b-m5-ties.txt` | 4 | 4 | 0 | 0 |
| `many-symbol-penney/b-q3-cyc3.txt` | 7 | 7 | 0 | 0 |
| `many-symbol-penney/b-q3-distinctp.txt` | 7 | 7 | 0 | 0 |
| `many-symbol-penney/b-q3-maxout.txt` | 7 | 7 | 0 | 0 |
| `many-symbol-penney/b-q3-ties.txt` | 7 | 7 | 0 | 0 |
| `many-symbol-penney/b-q3-transtri.txt` | 7 | 7 | 0 | 0 |
| `many-symbol-penney/b-q4-cyc3.txt` | 5 | 5 | 0 | 0 |
| `many-symbol-penney/b-q4-distinctp.txt` | 5 | 5 | 0 | 0 |
| `many-symbol-penney/b-q4-maxout.txt` | 5 | 5 | 0 | 0 |
| `many-symbol-penney/b-q4-ties.txt` | 5 | 5 | 0 | 0 |
| `many-symbol-penney/b-q4-transtri.txt` | 5 | 5 | 0 | 0 |

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

## ⚠ Read before relying on this

Three of the source directories overlap. `penney-mary` (m = 3, 4, 5) and `many-symbol-penney` (q = 3, 4) independently computed **the same six sequences**, from two separately written engines, two weeks apart. They agree on every shared term, which is a genuine cross-engine confirmation, but they are duplicates. **Only one copy of each is published here**: the six `penney-mary/b-m3-*` and `b-m4-*` files are omitted, because the `many-symbol-penney` copies are longer or equal wherever the two meet. penney-mary's m = 5 family is unique to it and is published. Both engines ship, so you can rerun the comparison rather than take this on trust.

## What was withheld, and why

1 source note is deliberately not published here. It records this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

## What is in this directory

- `oversight/oeis/penney-tournament/` — the b-files, and `STAGED.md`, the notes written with them.
- `oversight/oeis/penney-mary/` — the b-files, and `STAGED.md`, the notes written with them.
- `oversight/oeis/many-symbol-penney/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/penney-tournament/` — the engine and its verifier.
- `research/penney-mary/` — the engine and its verifier.
- `research/many-symbol-penney/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943922](https://doi.org/10.5281/zenodo.21943922)**

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
