# oversight/oeis/graceful-census

Four **total graceful-labeling counts** that OEIS's systematic graceful-labeling
census does not hold — for the **fan**, the **friendship (Dutch windmill)**, the
**helm**, and the **quadrilateral book** graphs. Every value was computed by an
exact, exhaustive method. How many *independent* ways each one is checked varies
by term and is set out per index in *Why these are trustworthy*, below; one term,
`fan(10)`, currently has no second check of any kind. The census was **confirmed absent from the
OEIS on 2026-07-13** (searched by the data and by keyword); the two largest terms,
added later, were absence-re-checked on 2026-07-20.

**The gate for the staged files is `verify-staged.mjs` in this directory**
(`node oversight/oeis/graceful-census/verify-staged.mjs`, about 34 s). It reads
all four b-files and recomputes **20 of the 26 staged terms** from the graph
definition; the other **6** it drift-guards against `expected-extension.mjs`,
which names the committed file and line every one of those values came from.
Exact ranges are in the table below. It is separate from
`research/graceful-census/verify.mjs` (about 342 s), which establishes that the
counters are correct in the first place but, as of 2026-07-27, still compares the
mathematics to its own hardcoded literals rather than to these files.

Backs the stratum **Every Difference, Once** (`/strata/every-difference-once/`)
and the notebook `research/graceful-census/` (`graceful.mjs`, `graceful.cpp`,
`verify.mjs`).

## What a graceful labeling is

A graph with `m` edges is **graceful** if its vertices can be labelled with
distinct integers from `{0, 1, …, m}` so that the `m` edge labels
`|f(u) − f(v)|` are exactly `{1, 2, …, m}` — each difference once. Whether every
*tree* is graceful is the **Graceful Tree Conjecture** (Ringel–Kotzig, 1964),
still open. We count the **total** number of graceful labelings (both members of
every complement pair `f, m−f`), which is the convention of the existing census
sequences.

## Why these four, and why the gap is real

OEIS holds a systematic run of "total number of graceful labelings of the
*n*-X graph": cycle **A333720**, ladder **A333719**, wheel **A333672**, prism
**A336677**, gear **A337795**, and the triangular book `K_{1,1,n}` **A334307**.
A 2025 wave added *fundamentally-different* (up-to-symmetry) counts for many
families, including the helm **A387800** and quadrilateral book **A387795**.
But four totals are missing:

| family | graph | staged file | status on 2026-07-13 |
|---|---|---|---|
| **fan** `F_n = K_1 + P_n` | hub joined to a path on `n` vertices | `b-fan.txt` | no total, no f.d. — **entirely absent** |
| **friendship / windmill** | `k` triangles sharing one hub | `b-friendship.txt` | no total, no f.d. — **entirely absent** |
| **helm** `H_n` | wheel `W_n` + a pendant on each rim vertex | `b-helm.txt` | f.d. exists (A387800); **total absent** |
| **quadrilateral book** | `n` 4-cycles sharing one edge | `b-book-quadrilateral.txt` | f.d. exists (A387795); **total absent** |

## The values

- **fan** (offset `n=2`, path length): `12, 32, 72, 292, 944, 3396, 18060, 112700, 709732, 4990632, 39745364`
- **friendship** (offset `k=1`, triangles): `12, 0, 0, 110592, 5529600` — the
  zeros are the **Bermond–Kotzig theorem**: the windmill is graceful iff
  `k ≡ 0 or 1 (mod 4)`, so `k = 2, 3, 6, 7, …` give 0; the next positive term is
  at `k = 8`.
- **helm** (offset `n=3`, rim length): `1308, 12432, 261540, 7445904, 359216956`
- **quadrilateral book** (offset `n=1`, pages): `16, 128, 0, 40032, 4671840` —
  the 0 at `n=3` reflects a gracefulness condition (`n ≡ 3 mod 4`).

## Why these are trustworthy (per term, with the gaps named)

### What backs each staged term

26 terms are staged. This is the whole picture, index by index. "Recomputed"
means a process enumerated the graph and produced the number; everything else is
weaker and is labelled as such.

| file | staged range | recomputed by `verify-staged.mjs` | **not** recomputed there | what backs the rest |
|---|---|---|---|---|
| `b-fan.txt` | `n=2..12` (11) | `n=2..9` (8) | **`n=10,11,12`** (3) | n=11,12: committed permuted recount. **n=10: nothing but a literal.** |
| `b-friendship.txt` | `k=1..5` (5) | `k=1..5` (**all 5**) | none | — |
| `b-helm.txt` | `n=3..7` (5) | `n=3..5` (3) | **`n=6,7`** (2) | both: `4n·A387800`. n=7 also: permuted recount. |
| `b-book-quadrilateral.txt` | `n=1..5` (5) | `n=1..4` (4) | **`n=5`** (1) | `4·5!·A387795`. |

**The weakest term in the directory is `fan(10) = 709732.`** It has no OEIS
cousin, no committed permuted-recount artifact, and no second engine committed
against it. It is recomputed on every 342 s run of
`research/graceful-census/verify.mjs` §3, but by the C++ engine alone (see the
`JS_MAX_V` note below) and against that file's own literal. If that one engine is
wrong about `fan(10)`, nothing in this repository would currently notice.

### The methods, and what actually differs between them

1. **Two JS counters, and they are genuinely different searches.**
   `countByVertices` walks **vertices** in a greedy most-constrained-first order
   and picks a label for each; `countByLabels` walks the **label values** `0..m`
   in order and decides which still-unlabelled vertex, if any, receives each. The
   recursion, the branching factor and the pruning order all differ, so the two
   search trees have different shapes and different sizes. What they **share** is
   one file, the `adjacency()` helper, the graph constructors in `FAMILIES`, and
   the idea of pruning on a used-difference bitset. **A wrong graph constructor,
   or a wrong definition of gracefulness, would be reproduced by both.** That is
   the limit of this cross-check. `countByLabels` is far slower (fan(8): 42.0 s
   against 0.7 s), so `verify-staged.mjs` runs it on fan `n=2..7`, friendship
   `k=1..3`, helm `n=3`, book `n=1..3` only.
2. **A third engine in a different language.** `graceful.cpp` is a separate
   bitmask implementation and agrees with the JS counters where they overlap
   (`research/graceful-census/verify.mjs` §6). It shares no code with them, but
   it is fed the same graph, built by the same constructor, so it does not
   escape the caveat above either.
3. **Six published sequences reproduced exactly** before any new value is trusted
   (A333720, A333719, A333672, A336677, A337795, A334307). This is the check that
   does test the constructors and the definition, because the reference values
   come from outside. It runs in `research/graceful-census/verify.mjs` §2, not in
   `verify-staged.mjs`.
4. **The friendship zeros reproduce the Bermond–Kotzig theorem** without being
   told it. `verify-staged.mjs` re-checks this against the **staged** values, and
   since `b-friendship.txt` is fully recomputed, that is a check on the staged
   zeros themselves rather than on a table.
5. **Helm and book totals reduce to an independently-authored OEIS sequence.**
   Canonicalising under `Aut(G) × {id, complement}` reproduces the published
   *fundamentally-different* counts (helm A387800, book A387795, gear A387798 as
   a control). Equivalently `helm = 4n·A387800` and `book = 4·n!·A387795`
   (`n ≥ 2`). `verify-staged.mjs` calibrates each relation against terms it
   enumerated itself (helm `n=3..5`, book `n=2..4`) **before** applying it to
   helm `n=6,7` and book `n=5`. Applying it is arithmetic on someone else's
   number, not an enumeration: strong outside evidence, and not a recomputation.
   No such relation exists for fan or friendship.

### Two things about `research/graceful-census/verify.mjs` a reader should know

Both were found on 2026-07-27 and neither is fixed here, because that file is a
different directory's and was left untouched.

- **`JS_MAX_V = 10` bites earlier than the prose suggested.** `verify.mjs` §3
  uses JS only when the graph has at most 10 vertices, so within that file
  `fan(10)`, `fan(11)`, `friendship(5)`, `helm(5)`, `helm(6)` and `book(5)` rest
  on the C++ engine **alone**, not just "the very largest terms". The version of
  this README before 2026-07-27 named only fan(12) and helm(7).
  `verify-staged.mjs` narrows that gap by two: it recomputes `friendship(5)` and
  `helm(5)` in JavaScript, which nothing committed did before.
- **§3 goes green while skipping terms when `g++` is absent.** At
  `verify.mjs:105` a term too large for JS with no compiler present is pushed as
  `(skip v=…)` and the pass flag is left true, so the section reports success
  having checked fewer terms. `verify-staged.mjs` has no conditional skip: its
  coverage is identical on every machine, which is why it uses pure JS even
  though `graceful.cpp` compiles in 0.72 s.

### The two largest terms — fan(12) and helm(7) — how each is actually checked

These two are the only staged terms that **no committed script recomputes at
all**: `verify.mjs` §3's literal arrays stop at fan `n=11` and helm `n=6`, one
term short of each staged file. (They are also the two furthest past `JS_MAX_V`,
at 13 and 15 vertices, but so are several smaller terms — see the `JS_MAX_V` note
above for the full list of terms that rest on the C++ engine alone.) Both were
first computed by `graceful.cpp` in two modes (root-label-sharded via `par.sh`,
and unsharded), but those are the *same* engine on the *same* graph and would
repeat any bug in either, so that pair alone is not an independent check. Each is
therefore confirmed a second, genuinely independent way (added 2026-07-20), and
`verify-staged.mjs` now binds both to the staged b-files:

- **helm(7) = 359216956** reduces to an **outside author's published number.**
  OEIS **A387800** ("fundamentally different graceful labelings of the n-helm",
  E. W. Weisstein, 2025) gives `A387800(7) = 12829177`, and `4·7·12829177 =
  359216956` exactly. That is independent code by an independent author, published
  before this computation. `verify.mjs` checks this relation arithmetically against
  the published data with no recomputation: §5(b) for n=3..6, §8(a) for n=7.
  `verify-staged.mjs` applies it to the staged n=6 and n=7 after calibrating it on
  n=3..5, which it enumerated itself.
- **fan(12) = 39745364** has **no cousin in OEIS** (searched 2026-07-20: the total
  and its fundamentally-different candidate both return no hits), so it is
  confirmed by **isomorphism-invariance.** `research/graceful-census/independence.mjs`
  rebuilds the fan graph from its definition (checked identical to the constructor
  in `graceful.mjs`), then applies a seeded vertex permutation before counting.
  The graceful-labeling total is invariant under relabelling, but the counter's
  greedy vertex order breaks ties by vertex id, so the permuted graph sends the
  search down a different tree, with different pruning and a different shard
  decomposition — a run that returns the same total exercises the recursion and
  the constructor, not just the shard arithmetic. Reproduce:
  `bash research/graceful-census/independence.sh fan 12` (and `fan 11`, `helm 7`
  as controls that must match the b-files). The permuted counts are staged in
  `research/graceful-census/runs/`.

Re-run the checks, cheapest first:

- `node oversight/oeis/graceful-census/verify-staged.mjs` — about 34 s, no
  compiler needed. Binds these four b-files: 20 of 26 staged terms recomputed,
  6 drift-guarded, 0 unbound. This is the one to run.
- `node research/graceful-census/verify.mjs` — about 342 s, builds a C++ binary.
  Establishes that the counters are correct (six published sequences, Burnside
  reduction, Lean kernel proof). It does **not** check these b-files term by
  term; see the two notes above.
- `node research/graceful-census/independence.mjs --selftest` — structural check
  that the permuted rebuild matches `graceful.mjs`.

Regenerating the b-files is `node oversight/oeis/graceful-census/derive.mjs
--write`. **Do not run it casually:** it rewrites all four files from scratch,
and a truncated or partial run silently shortens them. `verify-staged.mjs` checks
the index range of every file first for exactly this reason.

## The footprint — Zenodo first, OEIS only by a human author

Per `oversight/oeis/README.md` and OEIS's *Use of AI for OEIS Submissions is
Forbidden* policy, **nothing here is a paste-ready OEIS draft.** The *math* is
the contribution and it is sound as far as the checks reach: exact and exhaustive
throughout, absence-checked, and cross-checked by more than one method on every
term except `fan(10)`, which rests on a single engine. The *authoring* must be
done by a human who genuinely understands and stands behind it. Route:

1. **Citable footprint → Zenodo** (`.zenodo.json` here): deposit the notebook +
   verifier + b-files for a permanent DOI (request 005).
2. **OEIS only by a real human author** who independently verifies the four
   sequences and, if correct and interesting, submits them as themselves — with
   the natural cross-references (A333720/A333719/A333672/A336677/A337795/A334307
   for the census, A387800/A387795 for the reductions). The invitation is to
   scrutiny, including the possibility that we are wrong; the claim is only
   "absent from the catalogue as of 2026-07-13."
