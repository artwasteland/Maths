# The cycle structure of the Pollard-rho map x² + c (mod n)

Pollard's **rho** method (1975) factors an integer `N` by iterating
`f(x) = x² + c (mod N)` and watching for a collision. Iterating `f` turns `Z_n`
into a **functional graph** (out-degree 1 at every node), so every orbit is a tail
draining into a loop: the shape of the Greek letter **ρ**, which is where the
method gets its name.

## What is staged here

Three b-files, 1,800 staged terms in total. Each is recomputed from the
mathematics, line by line, by `verify-staged.mjs`.

| b-file | terms | staged index range | recomputed by a committed check | range not recomputed |
|---|---|---|---|---|
| `b-periodic-x2plus1.txt` | 1000 | n = 1..1000 | n = 1..1000, two ways | none |
| `b-sum-periodic.txt` | 400 | n = 1..400 | n = 1..400, two ways | none |
| `b-sum-cycles.txt` | 400 | n = 1..400 | n = 1..400, two ways | none |

1. **`b-periodic-x2plus1.txt`**: the number of **periodic points** of `x²+1 mod n`
   (n = 1..1000): `1,2,1,2,3,2,2,2,3,6,2,2,6,4,3,2,6,6,2,6,…`
   This is the natural **sibling of the catalogued cycle count
   [A352635](https://oeis.org/A352635)** (Chai Wah Wu), which counts the *cycles*
   of the very same map but not its *periodic points*. Completing that pair is the
   cleanest contribution here.
2. **`b-sum-periodic.txt`**: `Σ_{c=0}^{n−1}` (periodic points of `x²+c mod n`),
   a c-independent invariant of the modulus (n = 1..400):
   `1,4,5,8,12,20,16,16,27,48,…`
3. **`b-sum-cycles.txt`**: `Σ_{c=0}^{n−1}` (cycles of `x²+c mod n`)
   (n = 1..400): `1,3,4,6,8,13,11,12,17,26,…`

## What "checked two ways" means here, exactly

An earlier version of this file said the staged math was "cross-checked two
independent ways". That was an overclaim, and the 2026-07-20 audit caught it: the
two-way check in `research/pollard-rho/verify.mjs` stops at n = 200, so 800 of the
1000 terms in `b-periodic-x2plus1.txt` had only ever been touched by one engine.
Worse, a mutation probe on 2026-07-27 rewrote **all 1,800 staged terms at once**
and both committed checks stayed green with byte-identical output: no script in
the repository had ever opened these b-files at all
(`research/oeis-term-coverage/coverage-before.json`, `dirs["pollard-rho-x2plus1"]`).

`verify-staged.mjs` is the fix. It reads the staged bytes and recomputes them.
The two ways that cover every staged term differ as follows.

| | **Way A** | **Way B** |
|---|---|---|
| where | `analyze()` in `research/pollard-rho/engine.mjs` | `peelPeriodic()` in `verify-staged.mjs` |
| algorithm | depth-first path walk with three-colour marking; a cycle is discovered when a walk re-enters itself | in-degree census, then repeatedly delete every node with in-degree 0; what survives the peeling is exactly the cyclic set |
| the map f | the shared `mapFn(n,c)` closure | recomputed inline, `(x*x + cc) % n`, no shared code |
| coverage | all 1,800 staged terms | all 1,800 staged terms |
| what it is worth alone | this is the engine `derive.mjs` writes the files with, so on its own it is drift protection, not independence | shares no line of code with A, so agreement is a genuine second witness |

Two further checks in the same script, neither of which is a third full-coverage
witness and neither of which is counted as one:

- **`orbit()` census** (`verify-staged.mjs` section C): works from the *definition*,
  counting seeds whose orbit has tail length 0. Sampled at 17 moduli spanning
  n = 1..1000, not the whole range, and it shares `mapFn` with way A.
- **External calibration against A352635** (section D): both A and B must reproduce
  Chai Wah Wu's catalogued cycle count for **all n = 1..1000**, against terms
  downloaded from the OEIS b-file and committed here as `a352635-reference.mjs`.
  This is the only externally authored number in the directory. It certifies the
  machinery over the full staged range. It does **not** certify a single staged
  value, because A352635 counts cycles and the staged sequence counts periodic
  points: different statistics of the same graph. Calibration, not coverage.

Honest limit on all of the above: A and B are two algorithms, but they run in one
process, in one language, on one machine, in one run. They rule out an
implementation mistake in either walk and any drift or corruption in the staged
bytes. They do not rule out a shared misreading of the definition, which is what
the A352635 calibration and a human reader are for.

## Second engines elsewhere in the repository, described accurately

- `research/pollard-rho/verify.mjs` cross-checks `analyze()` against a
  from-scratch brute force (a `Map`-based cycle finder) for **all n ≤ 200** and
  c ∈ {0,1,2,3,5}, on all four graph statistics. Genuinely a different
  implementation, but it never opens the staged b-files, and n ≤ 200 is one fifth
  of the staged range of `b-periodic-x2plus1.txt`.
- `research/nowhere-new-to-go/verify.mjs` recomputes the `x²+1` functional graph
  with a wholly separate generic engine (`fgraph.mjs`, which works from an explicit
  `next[]` array) and asserts agreement with `analyze()` on cycles, periodic
  points, fixed points, longest cycle, tail sum and the full cycle spectrum. That
  is a real second witness, but at **one modulus, n = 2003**, which is *outside*
  every staged range here (the staged files stop at n = 1000 and n = 400). It
  supports the engine. It gives this directory no term coverage, and it is not
  counted above.

## Absence from the OEIS

Checked **2026-07-27** and recorded in `absence-2026-07-27.json`: each staged
sequence's own prefix was submitted to `oeis.org/search` (one window per sequence,
20 terms for the periodic sequence and 16 for each Σ_c sequence) and all three
returned no catalogued match. The record holds the exact URLs and the exact
answers, so it can be re-run and disagreed with. Two controls ran alongside,
because a quietly broken query harness returns "no match" for everything: the
positive control (factorials) returned A000142 as it must, and the negative
control (a contrived sequence) returned nothing. Both behaved.

An earlier absence claim in this file was dated 2026-06-25 and cited "numeric
searches, multiple windows". No log, transcript or snapshot of that run was ever
committed, so it is withdrawn and replaced by the dated record above.

## Context the same work establishes

Verified in `research/pollard-rho/verify.mjs` (**26/26**), but *not* staged as
sequences: these are facts about the method, not new OEIS data.

- Pollard's rho with `f = x²+c` (c bumped on failure, though c = 1 sufficed for
  every case) factors a battery of five semiprimes plus one mixed composite, the
  largest being the balanced 10-digit semiprime
  `3037000493 × 3037000507 ≈ 9.2 × 10¹⁸`, in about 7 × 10⁴ iterations.
- Reduced mod a prime factor `p`, the iteration collides in **O(√p)** steps (the
  "hidden small rho"), **≥ 100×** sooner than the `√(πN/2)` scale of a rho mod `N`.
  That early collision mod `p`, invisible in `Z_N`, is exactly what `gcd(xᵢ−x₂ᵢ, N)`
  detects.
- Averaged over all generic `c`, the mean rho length of `x²+c mod p` matches the
  **Flajolet-Odlyzko (1990)** random-mapping prediction `√(πp/2)`. The committed
  assertion is a 6% bound; the worst deviation actually measured over
  p ∈ {401, 809, 1601, 3209, 6421} is 3.2%. This one is empirical, not proved:
  `x²+c` is conjectured to be random-like, not known to be.
- The two textbook "never use these" values are exactly the **non-random** ones.
  **c = 0** (`x→x²`) has periodic-point count **exactly `1 + oddpart(p−1)`**, derived
  in `research/pollard-rho/special-c.md` and checked against every prime `p < 2000`;
  **c = −2** (the Chebyshev / Lucas-Lehmer map, the subject of the stratum
  *[Square Minus Two](https://artwaste.land/strata/square-minus-two/)*) deviates
  from `√(πp/2)` by far more than generic `c`.

A correction belonging to this section, made 2026-07-27: the battery used to be
described as reaching a "balanced 10-digit" semiprime `3037000499 × 3037000493`.
`3037000499` is not prime (it is `13 × 233615423`), so that number was not a
semiprime, and rho "solved" it in 4 iterations by finding the factor 13, which
demonstrates nothing about the balanced case. The battery now uses the genuine
balanced semiprime quoted above.

## Reproduce everything

```sh
node oversight/oeis/pollard-rho-x2plus1/verify-staged.mjs  # the artifact gate: reads the three
                                                           # staged b-files and recomputes all
                                                           # 1,800 terms two ways (2.4 s measured)
node research/pollard-rho/verify.mjs                       # 26/26: the engine and every claim
                                                           # above, from scratch (8.6 s measured)
```

`verify-staged.mjs` exits nonzero on any mismatch and prints, per b-file, how many
terms it recomputed and by which paths. Both scripts are verify-only.

**Do not run `derive.mjs` to resolve a disagreement.** It rewrites all three
b-files. If a recomputation ever disagrees with a staged term, that is a finding to
report, not a file to regenerate.

## Submitting: the corrected path

See `../README.md`. Do **not** paste a machine-authored draft into OEIS
(AI-authorship policy, plus our own never-lie bar). The mathematics is exact, every
staged term is recomputed two ways over its full index range, and the absence check
is dated and logged; only the *authoring* is the constraint. Deposit the
reproducible bundle on **Zenodo** for a DOI (`.zenodo.json`), and hand the verified
computation to a human mathematician (SeqFan, or a student) who will independently
check it and, if convinced, author the OEIS entries as themselves, including the
missing periodic-points sibling of A352635. Surfaced by the stratum
[*The Shape of the Rho*](https://artwaste.land/strata/the-shape-of-the-rho/).
