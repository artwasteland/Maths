# Topswops — total steps over all decks (+ the Garden of Eden)

Conway's **Topswops**: a deck is a permutation of `1..n`; read the top card `k`, and
unless `k = 1` reverse the top `k` cards; repeat. It always terminates.

**What is staged here (computed exactly 2026-06-24; verification coverage stated by
index below, not blanket):**

1. **A new sequence — `draft.txt` + `b-file.txt`.** `a(n)` = the **total number of
   steps summed over all `n!` decks** of `n` cards:
   `0, 1, 6, 38, 265, 2115, 18508, 180260, 1911505, 22169434, 277931375, 3758940272, 54349566758`
   (n = 1..13). Equivalently `n!` × the mean steps for a random deck. Reported
   absent from OEIS by full and windowed numeric searches, with the caveat under
   "Absence from OEIS" below.

2. **A new interpretation of an existing sequence — `A000255-comment.txt`.** The
   number of **Garden-of-Eden** decks (permutations no single reversal can produce)
   is **A000255(n-1)**. A deck `q` is reachable iff some `k` in `2..n` has `q(k)=k`;
   so the unreachable decks are exactly the permutations with **no fixed point in
   positions 2..n**, counted by inclusion-exclusion as `A000255(n-1)`. This is a
   proposed **comment**, not a new sequence.

## How far the checking actually reaches

Stated by index, because it does not reach as far as the staging does. The
2026-07-20 coverage audit found this README claiming the staging was "verified,
9/9" while the two largest terms were checked by nothing; a mutation prober then
confirmed it, by flipping `a(13)` to `54349566758` + 1 and watching every
committed check stay green
(`research/oeis-term-coverage/coverage-before.json`, `dirs["topswops-total-flips"]`).

| staged index | how it is bound | by what |
| --- | --- | --- |
| `a(1)..a(9)` | **recomputed, two implementations** | the engine, plus a flip simulation written separately that shares no code with it |
| `a(10)..a(11)` | **recomputed, one implementation** | the engine only |
| `a(12)..a(13)` | **drift-guarded only, NOT recomputed** | compared against `expected-extension.mjs`, a table with per-value provenance comments |

**The gate was mutation-tested, not trusted** (2026-07-27). Against an isolated
copy of this directory, each of the 13 staged terms was incremented by 1 in turn
and `verify-staged.mjs` re-run: all 13 went red. A b-file truncated to `n=1..11`,
which is exactly what the old `derive.mjs 12` instruction would have produced,
also went red. Every staged index is bound. "Drift-guarded only" means `a(12)`
and `a(13)` are not independently recomputed, not that they are unchecked.

**What "drift-guarded only" means, exactly.** For `a(12) = 3758940272` and
`a(13) = 54349566758` the gate reads the b-file and compares it against a
committed table. That catches truncation of the b-file (the hazard `derive.mjs`
creates) and a transcription slip. It **cannot** catch a wrong original
computation: the table and the b-file descend from the same 2026-06-24 run, so
if that run was wrong they are wrong together and the gate goes green. The
originating 2026-06-24 run is **not committed** anywhere in this repository:
there is no stdout log and no `runs/*.out` file for it. `expected-extension.mjs`
says so per value. Recomputing `a(13)` means enumerating 13! ≈ 6.2 billion decks,
which is why it is out of a gate's reach rather than merely skipped.

Both values *were* re-derived out of band on 2026-07-27, from the committed
engine, and the results are recorded per value in `expected-extension.mjs`:
`a(12)` in 98.6 s and `a(13)` in 1348.1 s (22.5 min), both matching the staged
b-file exactly. That establishes the two terms are reproducible from committed
code and were transcribed without error. It does **not** make them independently
verified, because it is the same engine, and 22 minutes is far outside what a
gate can spend. One genuinely external fact did fall out of the `a(13)` run:
`M(13) = 80`, matching the catalogued **A000375(13)**. That is outside evidence
about the *engine* at `n=13`, not about the total-steps value.

**On "two methods".** The parent README's staging discipline asks for an
independent value or a second method. For the *total-steps* column that bar is
met only up to `a(9)`. The engine's `statsFull()` and `maxAndSum()` are **not**
two methods: they live in one file, share one `perms()` Heap's-algorithm
generator, and `maxAndSum`'s flip loop is an inline copy of `flips()`. The gate
cross-checks them anyway and labels that for what it is, a consistency check
between two copies of one algorithm. The genuine second witness is the
from-scratch flip simulation (recursive lexicographic permutation generation),
which reaches `n=9` inside a gate's budget. Terms `a(10)..a(13)` rest on one
algorithm.

**Calibration (what it does and does not cover).** The same engine reproduces the
*catalogued* Topswops sequences: the **maximum** steps **A000375** for `n=1..11`
(`…,30,38,51`) and the **count of maximizing decks A123398** for `n=1..10`. So
only the total-steps sequence is claimed new. A000375(12)=65 and A000375(13)=80
are catalogued values that **no committed check recomputes**; earlier drafts of
this README and `.zenodo.json` listed them as though the engine had reproduced
them, and that has been withdrawn. The Garden-of-Eden identity *is* checked
**three genuinely different ways** (flip-map preimages counted by enumeration,
the no-fixed-point characterization, and A000255's recurrence), and those three
differ in what they compute, not merely in where the code sits.

**Absence from OEIS** was checked on 2026-06-24 by full and windowed numeric
searches, and re-run by the auditor on 2026-07-20 with zero matches. No search
transcript or URL is committed, so this is a dated assertion, not evidence you
can re-read here.

**Reproduce:**
```sh
# binds the staged b-file to a check: recomputes a(1)..a(11), drift-guards a(12..13)
node oversight/oeis/topswops-total-flips/verify-staged.mjs

# the engine's own checks: calibration, the Garden-of-Eden identity, a(1)..a(11)
node research/topswops/verify.mjs

# rewrites b-file.txt for n=1..13 (about 20 min).  REFUSES to write fewer terms
# than the file already holds, so a smaller NMAX aborts instead of truncating.
node oversight/oeis/topswops-total-flips/derive.mjs 13
```

**Submitting — the corrected path (see `../README.md`).** Do **not** paste `draft.txt`
into OEIS (AI-authorship policy + our honesty bar). Deposit the reproducible bundle on
**Zenodo** for a DOI (`.zenodo.json`), and/or hand the computation to a human
mathematician who will independently check it and, if convinced, author the OEIS entry
and the A000255 comment as themselves. Surfaced by the stratum
[*The Topswops Machine*](https://artwaste.land/strata/topswops-machine/).
