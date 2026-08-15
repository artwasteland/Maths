# Non-attacking chess pieces on the Möbius band and the Klein bottle

Independent sets in the attack graph of a chess piece on an n×n board whose edges are glued into a **Möbius band** or a **Klein bottle**. Queens, kings and four leapers (knight, camel, zebra, giraffe). **Kings are the clean case**: a one-square reach is unambiguous under any gluing, while a queen's diagonal traced across a twisted seam does not close and the count depends on a convention. A leaper is canonical for the same reason a king is, its move being a single fixed jump folded through the surface's deck group.

Documented on the Artificial Wasteland at [/strata/chess-on-a-mobius-strip/](https://artwaste.land/strata/chess-on-a-mobius-strip/), [/strata/kings-on-a-klein-bottle/](https://artwaste.land/strata/kings-on-a-klein-bottle/), [/strata/leapers-on-a-mobius-strip/](https://artwaste.land/strata/leapers-on-a-mobius-strip/).

## What is verified, and how far

Of the 193 staged terms here, **81 recomputed**, 104 drift-guarded, **8 unbound** (measured by `bind-staged.mjs --full`, not asserted).

| b-file | staged | recomputed | drift-guarded | unbound |
|---|---:|---:|---:|---:|
| `nonorientable-queens/b-klein-total.txt` | 12 | 12 | 0 | 0 |
| `nonorientable-queens/b-mobius-pairs.txt` | 18 | 18 | 0 | 0 |
| `nonorientable-queens/b-mobius-total.txt` | 13 | 13 | 0 | 0 |
| `nonorientable-queens/b-torus-total.txt` | 12 | 12 | 0 | 0 |
| `nonorientable-kings/b-klein-total.txt` | 13 | 13 | 0 | 0 |
| `nonorientable-kings/b-mobius-total.txt` | 13 | 13 | 0 | 0 |
| `nonorientable-leapers/b-klein-camel.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-klein-giraffe.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-klein-knight.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-klein-zebra.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-mobius-camel.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-mobius-giraffe.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-mobius-knight.txt` | 14 | 0 | 13 | 1 |
| `nonorientable-leapers/b-mobius-zebra.txt` | 14 | 0 | 13 | 1 |

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

Two items here are on the project's own **do not rely on this without re-verifying** list, and they are the largest terms in their files. (1) The leaper counts at **n = 14** are unbound: the three-way confirmation their notes describe is not backed by anything in the source repository, whose only committed cross-check between the two enumerators runs to n = 8. (2) The king counts for **n = 8..13** rest on the transfer matrix alone; the independent ray-tracing enumerator only reaches n = 7. The reason to trust the transfer matrix that high is external, that it reproduces A063443 and A067958 at n = 13, which is ground truth for the method at the right size but not for these counts.

## What is in this directory

- `oversight/oeis/nonorientable-queens/` — the b-files, and `STAGED.md`, the notes written with them.
- `oversight/oeis/nonorientable-kings/` — the b-files, and `STAGED.md`, the notes written with them.
- `oversight/oeis/nonorientable-leapers/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/nonorientable-queens/` — the engine and its verifier.
- `research/nonorientable-leapers/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943920](https://doi.org/10.5281/zenodo.21943920)**

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
