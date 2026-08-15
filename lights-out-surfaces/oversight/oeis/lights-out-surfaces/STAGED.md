# Lights Out on surfaces: solution-space dimension, three sequences absent from OEIS

*Computed inside the Artificial Wasteland, cross-checked by two structurally
independent code paths over part of the range (see the coverage table below for
exactly which part), checked absent from OEIS on 2026-07-18, and staged here for
deposit. Surfaced by the immersive stratum **The Lights That Hide**
(`/strata/the-lights-that-hide/`).*

> **Revised 2026-07-27.** An audit on 2026-07-20
> (`research/oeis-coverage-audit/findings-2026-07-20.json`) and a mutation probe on
> 2026-07-27 (`research/oeis-term-coverage/coverage-before.json`) found that this
> directory claimed more verification than its code delivered. `.zenodo.json` said
> the sequences were given "each to n=64" and that trust rested on "four
> structurally independent computations that agree on every term", when the only
> structurally independent cross-check reached n=30, the brute-force one reached
> n=4, the browser one reached n=24 and was a transcription of the first, and no
> committed script read the staged b-files at all.
> Section [Trust](#trust-what-checked-n-ways-actually-means-here)
> now states the ranges the code reaches. What changed in the code, rather than in
> the prose, is listed at the end.

## The object

*Lights Out* is played on an `n × n` grid of lights that are also buttons. Pressing a
button toggles every light in its **closed neighbourhood** (itself and its four
orthogonal neighbours). Over the two-element field GF(2), pressing is a linear map
`M = A + I`, where `A` is the adjacency of the board's cell graph and `I` the
identity (the `+I` is each button's toggle of its own light). The single integer
that governs the whole puzzle is the **rank deficiency** (nullity) of `M` over GF(2):

```
d(n) = n² − rank_GF(2)(M)
```

* `d = 0` ⟺ every starting pattern is solvable, with a **unique** solution.
* in general the solvable patterns number `2^(n²−d)`, each with `2^d` solutions.
* the `d`-dimensional kernel of `M` is spanned by the **quiet patterns**: sets of
  buttons whose presses cancel and change nothing.

We compute `d(n)` for the `n × n` board on six surfaces, defined by how the grid's
edges are glued:

| surface | column edge | row edge | in OEIS? |
|---|---|---|---|
| flat grid | free | free | **A159257** |
| torus | joined plainly | joined plainly | **A165738** |
| cylinder | joined plainly | free | **absent** |
| Möbius band | joined with a flip | free | **absent** |
| Klein bottle | joined with a flip | joined plainly | **absent** |
| projective plane | joined with a flip | joined with a flip | flagged (convention-dependent) |

## The three staged sequences (n = 1..64 in the b-files)

```
cylinder     b-cylinder.txt    0, 0, 2, 0, 1, 0, 0, 4, 2, 0, 1, 0, 0, 2, 2, 0, 1, 0, 0, 4, ...
Möbius band  b-mobius.txt      0, 3, 2, 0, 1, 0, 0, 2, 2, 0, 1, 0, 0, 3, 2, 0, 1, 0, 0, 2, ...
Klein bottle b-klein.txt       0, 3, 4, 0, 4, 6, 0, 0, 4, 8, 0, 12, 0, 0, 8, 0, 8, 6, 0, 16, ...
```

`b-projective.txt` is included for completeness but is **flagged exploration, not a
claimed catalogue entry** (see the convention note).

## Trust: what "checked N ways" actually means here

Two commands have to be green, and they check different things:

```
node research/lights-out-surfaces/verify.mjs                  # the mathematics
node oversight/oeis/lights-out-surfaces/verify-staged.mjs     # these four b-files
```

They took 44 s and 17 s respectively. Every wall time in this file was measured on
2026-07-27 on a busy four-core box, so treat them as orders of magnitude rather than
benchmarks.

`verify.mjs` checks live recomputations and **never opens a b-file**. Until
2026-07-27 that was the whole gate, so all 256 staged terms could have been replaced
with wrong numbers and it would have stayed green; the mutation probe did exactly
that and measured no change in output or exit code. `verify-staged.mjs` is the
missing half: it reads these four files and reproduces them.

### The code paths, and what actually differs between them

There are not four independent computations. There are two, plus one partial and one
port:

| path | what it re-derives for itself | what it shares |
|---|---|---|
| **A** `research/lights-out-surfaces/engine.mjs` | gluing geometry (`step`, `closedNeighbourhood`) and Gauss-Jordan over GF(2) on BigInt rows | nothing; this is the reference, and it is the path that wrote the b-files |
| **B** `research/lights-out-surfaces/verify.py` | a separately written neighbourhood function **and** a separately written elimination, in Python 3 stdlib | nothing but the problem statement. **The only fully independent path.** |
| **C** `research/lights-out-surfaces/brute.mjs` | the counting method: Gray-code enumeration of all `2^(n²)` button subsets, counting the quiet ones. No matrix, no elimination. | it `import`s `closedNeighbourhood` from A (`brute.mjs:13`), so it shares A's **gluing geometry**, which is the part most at risk. It checks the algebra, not the topology. |
| **D** the live recount on the stratum page | nothing | `public/strata/the-lights-that-hide/index.html:318` says the neighbourhood code "matches engine.mjs step-by-step", and the elimination below it reproduces A's. It is A ported to a browser: a portability check, not an independent computation. **No longer counted as a verification path.** |

### Coverage, by index range

Every row names the range it reaches and the range it misses. The staged range is
n = 1..64.

| check | independent of | reaches | misses |
|---|---|---|---|
| `plane == A159257` (published) | everything; external ground truth | n = 1..40 | n = 41..64, and it is the **flat** board, not a staged surface |
| `torus == A165738` (published) | everything; external ground truth | n = 1..40 | n = 41..64, and it is the **torus**, not a staged surface |
| B vs A, all six surfaces | geometry and elimination both rewritten | n = 1..40 | **n = 41..64** |
| C vs A, all six surfaces | linear algebra only (shares A's geometry) | n = 1..4 | n = 5..64 |
| D (browser recount) | runtime only | n = 1..24 (slider max, `index.html:252`; embedded arrays hold 24 terms) | n = 25..64 |
| `verify-staged.mjs`: staged term recomputed from A | binds the b-file to a live computation | n = 1..48 in all four files (192 of 256 terms) | n = 49..64 |
| `verify-staged.mjs`: staged term vs `expected-tail.mjs` | detects any change since 2026-07-27 | n = 49..64 in all four files (64 of 256 terms) | it is **drift protection, not a recomputation** |
| parity law, cylinder and Möbius | property of the computed values | n = 3..48 | n = 49..64 |

**Said plainly: terms n = 41..64 of every staged sequence, 24 of 64, rest on one
engine.** No committed check recomputes them by a second path, because the cost of
the elimination grows about as `n⁵`: path B to n=64 takes 3 m 55 s and path A to
n=64 takes 133 s, against 15 s and 18 s for the ranges the gates do run.

One thing is known about that tail beyond the single engine, and it is deliberately
downgraded here because no gate re-runs it. On 2026-07-27 both paths were run once
to n=64 by hand, and A, B and all 256 staged terms agreed exactly. Those two runs,
their wall times and the commands that reproduce them are recorded in
`expected-tail.mjs`, which is where the drift table came from. That is a dated
one-off, not a standing check. To turn it back into a live check, run
`node oversight/oeis/lights-out-surfaces/verify-staged.mjs --to 64`, which ignores
the drift table and recomputes the whole staged range from A (several minutes).

### The rest of what `verify.mjs` checks

* **Calibration.** The same engine, fed the flat and torus gluings, reproduces the
  two **published** OEIS sequences bit-for-bit for n = 1..40. This is strong evidence
  that the conventions are the standard ones. It says nothing directly about the
  cylinder, Möbius or Klein values, which are different gluings.
* **Topology confirms the labels.** `chi.mjs` computes the Euler characteristic and
  boundary of each identified grid: torus χ=0 closed, Klein χ=0 closed, projective
  χ=1 closed, cylinder and Möbius χ=0 with boundary, flat χ=1. The surface names are
  earned, not decorative.
* **Sanity.** `M` is symmetric on every surface for n = 1..8; the torus obeys `d ≤ 2n`
  for n = 1..30; flat and torus `d` is even for n = 1..48; the cylinder and Möbius
  parity rules hold for n = 3..48.

## The convention (stated so it can be checked)

A button toggles each **distinct** cell of its closed neighbourhood **once** (the
board is a **simple graph**, exactly as the physical game is and as the published
A159257/A165738 are, being nullities of `GridGraph` adjacency matrices). At the
degenerate sizes n = 1, 2, where a wrap can fold a neighbour onto a cell already
counted, a different (multigraph, cancel-mod-2) convention would give different
values for the cylinder and Klein bottle; we use the simple-graph one throughout,
consistent with the calibration boards.

An earlier version of this file added that for n ≥ 3 the two conventions agree on the
cylinder, Möbius band and Klein bottle, "independently re-derived". **That claim is
withdrawn.** No implementation of the multigraph convention exists anywhere in
`research/lights-out-surfaces/`, so nothing in this repository supports it. It may
well be true; it is not checked here.

The **projective plane** is the one surface whose antipodal (both-axes-flipped)
gluing stays genuinely convention-dependent at every size, so `b-projective.txt` is
**not** claimed as an absent catalogue entry; it is shown on the stratum for
interest and included here only as reproducible exploration.

## A finding beyond the numbers

On the flat grid and the torus, `d(n)` is always even (quiet patterns pair off under
complementation). Gluing the board into a **cylinder** or **Möbius band** breaks that
pairing: the cylinder's `d(n)` is **odd exactly at n ≡ 5 (mod 6)**, and the Möbius
band's is odd at n ≡ 5 (mod 6) together with n ≡ 2 (mod 12). The parity of the answer
detects the twist.

Both rules are checked by `verify.mjs` for n = 3..48, and both hold through n = 64 in
the staged data. Stated as an observation on the computed range, not as a proved
theorem.

## Absence check

Searched OEIS on **2026-07-18** by surface name (cylinder / Möbius / Klein / sigma
game / all-ones problem) and by the computed digit strings themselves; each returned
no matching sequence. The only Lights Out rank-deficiency sequences in OEIS are
A159257 (flat) and A165738 (torus).

**No transcript, query log or archived result is committed in this directory**, so a
reader cannot confirm from here that the search happened as described. Treat it as a
dated assertion by the author, not as a checked claim, and re-run it before deposit.
The claim is in any case only "absent from the catalogue as of the date above." If a
reader finds any already published, that correction belongs in the deposition door.

The linear-algebra machinery is classical (Anderson & Feil, *Turning Lights Out with
Linear Algebra*, Math. Mag. 71 (1998) 300–303); what appears uncatalogued is the
**integer sequence** of `d(n)` for these surfaces.

## Provenance and the OEIS policy line

The computation and prose were produced by an AI instance (Claude) within the open
Artificial Wasteland project under a strict never-lie, show-the-check rule.
**Per OEIS policy (AI-authored and automated submissions are forbidden), this has NOT
been submitted to OEIS by the project.** It is deposited as a citable, independently
checkable artifact (Zenodo) and explicitly offered for independent human
verification; any of these sequences should be authored in OEIS only by a human who
has verified it themselves.

## Files

* `b-cylinder.txt`, `b-mobius.txt`, `b-klein.txt`: the three claimed sequences, n=1..64.
* `b-projective.txt`: flagged exploration (convention-dependent), n=1..64.
* `verify-staged.mjs`: the artifact gate. Reads the four b-files above and nothing
  else. Recomputes n=1..48 from `engine.mjs`, compares n=49..64 to `expected-tail.mjs`,
  exits nonzero on any mismatch.
* `expected-tail.mjs`: the drift table for n=49..64, with the provenance of every
  value in it.
* `.zenodo.json`: deposit metadata.
* Engine, mathematics gate and cross-check paths: `research/lights-out-surfaces/`.

**Never run `research/lights-out-surfaces/gen-data.mjs`** to "fix" a failing gate. It
rewrites all four b-files from scratch, which would erase the disagreement instead of
recording it.

## What changed in the code on 2026-07-27

* Added `verify-staged.mjs` and `expected-tail.mjs`. Before this, 0 of 256 staged
  terms were bound to any committed check; now 192 are recomputed live and the other
  64 are drift-guarded.
* `verify.mjs`: the Python cross-check (path B, the only independent one) was raised
  from n = 1..30 to n = 1..40, at a cost of about 10 s. It was not raised further
  because n = 1..64 costs 3 m 55 s in Python alone.
* `verify.mjs`: added the Möbius parity check, which this README and the stratum page
  both asserted while nothing verified it.
* `verify.mjs`: the brute-force check's label now says that it shares `engine.mjs`'s
  geometry, and the header now says the file reads no b-file and names the gate that
  does.
* The stratum page `public/strata/the-lights-that-hide/index.html` is outside this
  directory and still says "Four independent counts agree." and, of those four,
  "All agree on every term." That wording has the same defect this file just fixed
  and needs the same correction.
