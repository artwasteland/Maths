# A282901 extended: labeled chip-firing on a line

OEIS **A282901**, the number of permutations of 1..2n+1 reachable by labeled chip-firing (Hopkins, McConville and Propp, *Sorting via chip-firing*, 2017). It had five terms and keyword `more` since 2017, with no b-file and no program. Staged here: **a(5) = 819** and **a(6) = 2555**.

Documented on the Artificial Wasteland at [/strata/the-pile-that-sorts-itself/](https://artwaste.land/strata/the-pile-that-sorts-itself/).

## What is verified, and how far

Of the 7 staged terms here, **6 recomputed**, 1 drift-guarded (measured by `bind-staged.mjs --full`, not asserted).

| b-file | staged | recomputed | drift-guarded | unbound |
|---|---:|---:|---:|---:|
| `labeled-chip-firing/b282901.txt` | 7 | 6 | 1 | 0 |

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

`a(6) = 2555` is on the project's **do not rely on this without re-verifying** list, and it is the one staged term the artifact gate cannot recompute. The notes describe two independent C++ builds; only one C++ source is committed anywhere in the source repository. So at a(6) the honest count of reproducible paths is **one**. `a(5) = 819` is unaffected and genuinely multi-path.

## What is in this directory

- `oversight/oeis/labeled-chip-firing/` — the b-files, and `STAGED.md`, the notes written with them.
- `research/labeled-chip-firing/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.21943838](https://doi.org/10.5281/zenodo.21943838)**

⚠ That DOI is **reserved, not yet registered**: Zenodo has earmarked it for this
deposit and it begins resolving when the deposit is published. Until then the link
above will not work, and this line says so rather than looking broken. The number
will not change.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
