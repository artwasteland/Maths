# Gardens of Eden of elementary cellular automata on a ring

*Computed inside the Artificial Wasteland, verified by four structurally
independent methods (every staged term confirmed by at least two of them, in two
languages) plus textbook positive controls, checked absent from OEIS on
2026-07-19 (re-confirmed 2026-07-20), and staged here for deposit. Surfaced by the immersive stratum **The Patterns With No
Yesterday** (`/strata/gardens-of-eden/`). Engine + verifiers: `research/ca-garden-of-eden/`.*

## The object

An elementary cellular automaton (ECA) is fixed by a rule number `R ∈ {0,…,255}`:
a local map `f(a,b,c)` reading a cell's left neighbour, itself, and its right
neighbour, where `f` is the base-2 digits of `R` (standard Wolfram numbering). On
a **ring of `n` cells** (periodic boundary) the rule induces a global map

```
F_R : {0,1}^n → {0,1}^n,     F_R(x)_i = f(x_{i-1}, x_i, x_{i+1})   (indices mod n).
```

A configuration `y` is a **Garden of Eden** (an *orphan*) iff it has **no
predecessor**: no `x` with `F_R(x) = y`. It is a pattern the rule can *display*
but could never have *produced* one step earlier. The quantity computed is

```
GoE_R(n) = 2^n − |image(F_R on the ring of length n)|.
```

The term is from the Moore–Myhill Garden-of-Eden theorem (E. F. Moore 1962, J.
Myhill 1963): on the infinite lattice a CA has an orphan iff it is not surjective.
On a **finite ring** the count `GoE_R(n)` is what we compute exactly, per `n`.

## What is new

The Garden-of-Eden counts, on the ring, of these rules are **absent from OEIS**
(checked 2026-07-19 by the literal digit strings on multiple contiguous windows,
and by keyword search; each staged sequence's definition — cyclic boundary,
image/orphan count — was confirmed distinct from the existing "rule N" OEIS
entries, which are one-cell-period or infinite-line objects; absence of all 8
heads re-confirmed 2026-07-20 via the OEIS search API during the pre-deposit
audit, with a Fibonacci query as positive control):

| file | rule | what it counts |
|---|---|---|
| `b-rule30-goe.txt`  | 30  | orphans on a ring of length n — the chaotic rule (Mathematica's default RNG) |
| `b-rule30-image.txt`| 30  | configurations *with* a predecessor (= 2^n − GoE); the co-sequence |
| `b-rule110-goe.txt` | 110 | orphans — the Turing-complete rule |
| `b-rule184-goe.txt` | 184 | orphans — the traffic / particle-hopping rule |
| `b-rule22-goe.txt`  | 22  | orphans — a complex rule whose count *dips* at n=4 (6→5) |
| `b-rule126-goe.txt` | 126 | orphans — complex |
| `b-rule54-goe.txt`  | 54  | orphans — class-4 complex |
| `b-rule146-goe.txt` | 146 | orphans — complex |

Each b-file gives `n = 1..64` (exact big-integers). Rule 30's head, `n = 1..`:

```
1, 1, 3, 5, 6, 12, 22, 33, 57, 101, 166, 280, 482, 813, 1373, 2337, 3962, 6708, …
```

**A finding beyond the numbers.** Rule 30 is *almost* surjective: its orphan
**density** `GoE(n)/2^n` falls monotonically toward 0 (≈ 0.099 at n=10, ≈ 0.018 at
n=20, ≈ 0.00068 at n=40), yet the orphan **count** grows without bound (≈ 1.7^n).
The rule can eventually produce *almost every* pattern, but never *quite* all of
them: on every ring, some configurations have no yesterday.

## What is *not* claimed as new (the controls, stated honestly)

- **The six reversible ECAs `{15, 51, 85, 170, 204, 240}`** (shifts, identity,
  negations) are bijective on every ring, so `GoE(n) = 0` for all n — *no orphans,
  ever*. Used as a control, not staged.
- **Constant rules 0 and 255** map everything to one fixed configuration, so
  `GoE(n) = 2^n − 1` (a trivial closed form) — a control.
- **Linear rules 90 (Sierpiński/XOR) and 150** are surjective on the *infinite*
  line, yet have orphans on *finite* rings following a number-theoretic pattern
  (rule 150 & 105: orphans exactly when `3 | n`; rule 90 & 60: a doubling
  structure tied to the GF(2) ring-map nullity). These finite-ring nullity
  sequences are classical linear algebra and likely catalogued in other forms; we
  show them as *illustration* of the finite-vs-infinite distinction, not as new.
- **Rule 45** gives `0,2,0,4,0,8,…` (= 2^(n/2) at even n, else 0), which OEIS
  already holds; excluded.

## Trust — never one path

Four structurally independent methods, atop textbook positive controls. They
agree on every term of their pairwise overlaps, and **every staged term
(all 8 b-files, n = 1..64) is confirmed by at least two implementations that
share no code, in two languages**:

1. **Brute force** (`engine.mjs` `bruteImageGoE`): enumerate all 2^n configs, apply
   F_R, count distinct images. Exact ground truth; run to **n = 20** for every
   featured rule and to **n = 24** for rule 30.
2. **Transfer matrix over the de Bruijn transition monoid** (`imageSizes`): a
   config `y` is in the image iff `trace(M_{y_0}⋯M_{y_{n-1}}) ≠ 0` (boolean), where
   `M_b` is the 4×4 de Bruijn pair-state matrix emitting symbol `b`; the boolean
   products form a finite monoid, and counting length-n strings by their product
   gives the image size as an exact big-integer for every n. Matches (1) on the
   whole overlap; generated the b-files to n = 64.
3. **Subset-DFS predecessor finder** (`findPredecessor`): for a specific `y`, search
   for a preimage by propagating the local constraints around the ring. Its
   orphan/non-orphan verdict matches (1) on **every one** of the 2^n configs for
   all seven featured GoE rules 30, 110, 184, 22, 126, 54, 146 plus controls 90
   and 45 (n ≤ 13), and every non-orphan witness `x` it returns satisfies
   `F_R(x) = y` under a fresh forward step.
4. **An independent Python reimplementation** (`verify.py`), separate language and
   separate code (plain nested-list boolean matrices, Python big-ints): checks
   brute == transfer within Python (n ≤ 18, all featured rules), reproduces the
   recorded heads, and re-derives **every term of every staged b-file
   (n = 1..64)**, comparing term by term against the committed files.

Coverage per term, stated plainly: for n ≤ 13 a staged GoE term is confirmed by
all four methods; for n ≤ 18 by both languages' brute force and both transfer
implementations; for n ≤ 20 (n ≤ 24 for rule 30) by Node brute force and both
transfer implementations; for every n up to 64 by the two independently written
transfer implementations (Node and Python), which agree exactly on all 8 × 64
staged values. No staged term rests on a single implementation.
(`b-rule30-image.txt` is the co-sequence 2^n − GoE; the DFS confirms it via the
orphan count it cross-checks at n ≤ 13, and both transfer implementations check
it directly at every n.)

Positive controls (the machinery reproduces known facts before any new value is
trusted): the six reversible ECAs → 0; constant rules → 2^n − 1; standard Wolfram
numbering round-trips (rule 110 truth table; rule 90 = `x_{i-1} XOR x_{i+1}`).

`node research/ca-garden-of-eden/verify.mjs` → **19/19**;
`python3 research/ca-garden-of-eden/verify.py` → **23/23**.

## Provenance (honest, not laundered)

The computation and prose here were produced by an AI instance (Claude) inside the
open *Artificial Wasteland* project, under a strict never-lie / show-the-check
rule; everything is verified by the reproducible code in `research/ca-garden-of-eden/`.
Per OEIS policy (AI-authored and automated submissions are **forbidden**), **none
of this has been submitted to the OEIS by the project.** The footprint routes to a
**Zenodo** deposit (DOI) for the reproducible artifact; any of these sequences
should be authored on OEIS only by a human who has independently verified it.

The machinery is classical: elementary cellular automata (Wolfram, *A New Kind of
Science*, 2002; and the numbering therein), the Garden-of-Eden theorem (Moore
1962; Myhill 1963), and the de Bruijn / transition-monoid method for CA image
counting (standard symbolic-dynamics practice; see e.g. Lind & Marcus, *Symbolic
Dynamics and Coding*, 1995, for sofic-shift image counting). What is uncatalogued
is the specific ring Garden-of-Eden count of each rule above.

## Reproduce

```
node research/ca-garden-of-eden/verify.mjs      # 19/19
python3 research/ca-garden-of-eden/verify.py     # 23/23
node research/ca-garden-of-eden/gen-data.mjs      # regenerate the b-files
```
