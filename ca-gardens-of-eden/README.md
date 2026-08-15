# Gardens of Eden for elementary cellular automata on a ring

A **Garden of Eden** is a configuration with no predecessor. For seven elementary cellular automata (rules 22, 30, 54, 110, 126, 146, 184) on a ring of n cells, the count of Gardens of Eden for n = 1..64, plus the image size for rule 30. Computed by a monoid transfer construction, which is linear in n and so exact all the way out.

Documented on the Artificial Wasteland at [/strata/gardens-of-eden/](https://artwaste.land/strata/gardens-of-eden/).

## What is verified, and how far

Of the 512 staged terms here, **512 recomputed** (measured by `bind-staged.mjs --full`, not asserted).

| b-file | staged | recomputed | drift-guarded | unbound |
|---|---:|---:|---:|---:|
| `ca-garden-of-eden/b-rule110-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule126-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule146-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule184-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule22-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule30-goe.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule30-image.txt` | 64 | 64 | 0 | 0 |
| `ca-garden-of-eden/b-rule54-goe.txt` | 64 | 64 | 0 | 0 |

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

- `oversight/oeis/ca-garden-of-eden/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/ca-garden-of-eden/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943899](https://doi.org/10.5281/zenodo.21943899)**

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
