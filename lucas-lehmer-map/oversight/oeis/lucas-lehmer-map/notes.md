# The Lucas–Lehmer map x²−2 (mod n) — staged computation

*Surfaced by the immersive stratum **Square Minus Two**
(`/strata/square-minus-two/`, `public/strata/square-minus-two/index.html`).
Ledger program **P2** (small true discoveries, computational & citable).*

> **Read `../README.md` first — the AI-authorship line.** OEIS forbids
> AI-authored submissions, so nothing here is paste-ready. What is staged is the
> *computation* (exact, calibrated against catalogued sequences, absence-checked);
> the *footprint* routes through a Zenodo DOI of the bundle and/or a human who
> independently verifies and authors a submission as themselves.

## The object

Fix a modulus `n`. The map `f(x) = x² − 2 (mod n)` sends `Z_n = {0,…,n−1}` to
itself, so iterating it makes `Z_n` a **functional graph**: every node has
out-degree 1, so each connected component is one directed cycle with trees
flowing into it. This is the iteration of the **Lucas–Lehmer Mersenne primality
test** — `s₀ = 4`, `s_{k+1} = s_k² − 2 (mod M_p)`, and `M_p = 2^p − 1` is prime
iff `s_{p−2} ≡ 0`. (Verified here against true primality for exponents 3..61, and
shown as orbit-of-4-reaches-0 inside `G(M_p)` for `p ≤ 19`.) The same `x²−2` is
the **Chebyshev / angle-doubling** map: with `x = y + y⁻¹` one has
`x² − 2 = y² + y⁻²`, i.e. `f` squares `y` — verified over the units of every
modulus the verifier touches.

The squaring map `x²` and the cubing map `x³` have their cycle counts
catalogued (**A023153**, **A023154**) and `x²`'s periodic-point count is
**A277847**. The `x²−2` map — the one that actually runs the Mersenne hunt — does
not. These four natural counts are **confirmed absent from OEIS** (June 2026;
numeric search, several windows). Offset `n = 1` throughout.

| key | statistic | first terms (n = 1..) | b-file |
|-----|-----------|------------------------|--------|
| **C** | number of cycles of `f` | 1,2,1,2,2,2,2,2,3,4,3,2,3,4,2,2,3,6,4,4,… | `b-file-C.txt` |
| **P** | number of periodic points (`x` with `fᵏ(x)=x`) | 1,2,1,2,2,2,2,2,3,4,4,2,5,4,2,2,5,6,7,4,… | `b-file-P.txt` |
| **F** | number of fixed points (`f(x)=x`) | 1,2,1,2,2,2,2,2,3,4,2,2,2,4,2,2,2,6,2,4,… | `b-file-F.txt` |
| **L** | length of the longest cycle | 1,1,1,1,1,1,1,1,1,1,2,1,3,1,1,1,3,1,3,1,… | `b-file-L.txt` |

Each b-file carries **120 verified terms**.

## The method (reproducible, exact, calibrated)

`engine.mjs` builds the graph by a single linear sweep (Floyd-free: a 3-colour
walk that marks each newly-closed cycle once). `verify.mjs` asserts every claim
below; `node verify.mjs` → **19/19, 0 failures**. No floating point, no
estimation. `node verify.mjs 120 --bfile C` (or P/F/L) regenerates a b-file.

The engine is **calibrated against the catalogue**: the *same* cycle/periodic-point
algorithm, run on `x²` and `x³`, reproduces **A023153**, **A023154** and
**A277847** exactly through n = 24. So the algorithm is correct; only the map is new.

## What the computation also establishes (asserted in the verifier)

By CRT, for coprime `m, n` the graph factors as a tensor product
`G(mn) ≅ G(m) ⊗ G(n)`. The periodic part is the product of the periodic parts, so:

1. **P and F are multiplicative** — `P(mn)=P(m)P(n)`, `F(mn)=F(m)F(n)` (0 failures
   over all coprime pairs `m,n ≤ 70`). `F` also counts the roots of
   `(x−2)(x+1) ≡ 0 (mod n)` directly (independent second count), giving the
   **prime law** `F(p) = 2` for primes `p > 3`, `F(2)=2`, `F(3)=1`.
2. **C and L are *not* multiplicative.** They obey the permutation-product rule on
   the periodic part — verified to hold *exactly* over all coprime pairs `m,n ≤ 70`:
   - `C(mn) = Σ_{i,j} gcd(rᵢ, sⱼ)` over the two cycle-length spectra;
   - `L(mn) = max_{i,j} lcm(rᵢ, sⱼ)`.
   Both are positively witnessed to differ from the naive `C(m)C(n)` /
   `lcm(L(m),L(n))`. This irregularity is exactly *why* C and L need cataloguing:
   they are not reconstructable from a multiplicative formula — you need the full
   cycle spectrum, which is governed by the multiplicative orders Vasiga & Shallit
   (2004) analysed over prime fields.

## Honest scope

Ours and checked: the four exact sequences (120 terms each), their OEIS absence as
of June 2026, the multiplicativity of P and F, the tensor formulas for C and L
(verified, not proved here for all n), the prime law for F, and the Lucas–Lehmer /
Chebyshev identities (verified to the stated bounds). **Not** claimed: that no one
has ever computed these privately (only that they are uncatalogued); a closed form
for C, P, or L over all n; that the prime-field cycle theory is new (it is Vasiga &
Shallit's, here applied to all of `Z_n` and tabulated). If a reader finds any of
these published, that correction belongs in the deposition door.

## References

- D. H. Lehmer, "An extended theory of Lucas' functions," *Ann. of Math.* 31
  (1930), 419–448. (The s₀=4, x²−2 test.)
- T. Vasiga & J. Shallit, "On the iteration of certain quadratic maps over GF(p),"
  *Discrete Math.* 277 (2004), 219–240. (Cycle/tail structure of `x²` and `x²−2`
  over prime fields — the structural backbone.)
- L. Somer & M. Křížek, "On a connection of number theory with graph theory,"
  *Czechoslovak Math. J.* 54 (2004), 465–485. (The digraph `x²` over `Z_n`;
  OEIS A023153 / A277847 sit here.)
- OEIS A023153, A023154 (cycle counts of `x²`, `x³` mod n), A277847 (periodic
  points of `x²` mod n) — the catalogued siblings this calibrates against.

## Open edges

- A **closed form** (or clean asymptotic) for `C(n)` and `P(n)` from the
  prime-power cycle spectrum — the tensor rule reduces it to understanding
  `G(p^k)`, where Vasiga–Shallit give the prime case.
- **Prove** the prime-field cycle-length law lifts to the b-file values for
  composite `n` via the tensor rule (the verifier checks it; a proof would close it).
- Push the b-files past 120 (the sweep is `O(n)` per modulus, trivially extendable).
