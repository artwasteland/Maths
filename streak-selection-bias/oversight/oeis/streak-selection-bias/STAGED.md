# Streak-selection bias (Miller-Sanjurjo), exact rationals

Two companion sequences: the numerators and denominators of `E(n)`, the expected
within-sequence proportion of heads on the flip immediately following a heads,
averaged over all fair-coin sequences of length `n` in which at least one such
flip exists. Staged as `b-file-numerators.txt` and `b-file-denominators.txt`,
21 terms each, `n = 2..22`. The point of the sequence is that `E(n) < 1/2` for
every finite `n >= 3` even though the *pooled* proportion is exactly `1/2`: the
finite-sample selection bias of Miller & Sanjurjo, *Econometrica* 86(6) (2018),
2019-2047.

## How far the checking actually reaches

Stated by index. This directory used to ship a generator and nothing else, so
the honest statement is short and it is worth being exact about what changed.

| staged index | how it is bound | by what |
| --- | --- | --- |
| `n = 2..22`, both files, all 42 terms | **recomputed, two paths** | `verify-staged.mjs` |
| `n = 2..3` | additionally matched to a **published** value | Miller & Sanjurjo 2018, Table 1 |
| `n = 4..22` | no external source exists in this repository | |

Nothing is drift-guarded against a stored table here, and no staged term is
unbound.

**The gate was mutation-tested, not trusted** (2026-07-27). Against an isolated
copy of this directory, each of the 42 staged terms across the two files was
incremented by 1 in turn and `verify-staged.mjs` re-run: all 42 went red, zero
silent. Compare the pre-existing check set, which caught 13 of 21 per file.

**What the two paths differ in.** The previous "checked two ways" claim in this
project did not survive the 2026-07-20 audit, which found it was one enumeration
compared against a hardcoded constant, covering the single term `n=4`. So the
difference is named:

- **(A) instance enumeration.** Iterate all `2^n` bitmasks and accumulate each
  individual sequence's `(o, h)`. This is `compute.mjs`'s algorithm. Cost
  `O(n * 2^n)`.
- **(B) class counting.** Never build a sequence. Carry a DP over the state
  (value of the current flip, `o` so far, `h` so far) and weight each `(o, h)`
  class by how many sequences fall in it. Cost `O(n^3)`.

They differ in what they iterate over, in asymptotic cost, and in whether a
sequence object is ever materialized. What they do **not** differ in: both are
JavaScript, both live in one file, and both encode the same reading of the
definition. A convention error in that reading is a shared assumption, which is
why the gate also checks two **closed-form structural identities** with no
enumeration at all: that the number of sequences with at least one opportunity
is `2^n - 2`, and that summed over all sequences `sum(h) = (n-1)2^(n-2)` and
`sum(o) = (n-1)2^(n-1)`, so the pooled proportion is exactly `1/2`. That last
one is the Miller-Sanjurjo framing itself, and it is what would catch an
off-by-one in which flip positions count toward which statistic.

**Why this directory needed a gate.** The 2026-07-20 audit
(`research/oeis-coverage-audit/findings-2026-07-20.json`) found the parent
README's "21 verified terms each" resting on nothing in this directory:
`compute.mjs` prints values, never reads a b-file, and has no pass/fail exit
status. A mutation prober then measured the true reach
(`research/oeis-term-coverage/coverage-before.json`): 13 of 21 terms per file,
frontier at `n=14`, which is exactly `research/made-not-retold/verify.mjs`
reading both files and recomputing `n=2..14`. Terms `n=15..22` of both files
were bound to nothing. They are bound now.

## Absence from OEIS is asserted, not evidenced

`draft.txt` records a direct search on 2026-06-02 finding both sequences absent.
No transcript, query URL, or result snapshot was committed, and the 2026-07-20
re-check could not be completed from the sandbox (oeis.org returns HTTP 403 to
automated fetches). A human must redo this search and record it before any
deposit or submission. The values are checked; the *novelty* is not.

## Reproduce

```sh
# reads both b-files, recomputes all 42 staged terms two ways, exits nonzero on mismatch
node oversight/oeis/streak-selection-bias/verify-staged.mjs

# compute.mjs is the GENERATOR: it prints values and checks nothing.
# Running it verifies nothing and it does not write the b-files.
```

Measured cost of the gate: about 2 s wall on Node v22.22.2, dominated by path A
at `n=22` (roughly 4.2 million masks). Each run prints its own timing.
