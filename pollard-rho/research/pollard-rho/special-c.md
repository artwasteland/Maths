# The two values Pollard's method must avoid, derived

*A proof note for P2 / "The Shape of the Rho". Every claim here is checked
constructively in `verify.mjs` (sections I–K); run `node research/pollard-rho/verify.mjs`.*

Every textbook on Pollard's rho says: pick the map `f(x) = x² + c (mod n)` with a
*random-ish* `c`, but **never `c = 0` and never `c = −2`**. The reason given is
usually a hand-wave — "those are degenerate." This note replaces the hand-wave with
theorems. Both maps are *rigid*: their cycle structure is fixed by the multiplicative
order theory of the field, not by chance, so the birthday law `√(πp/2)` that makes the
method fast simply does not apply to them. The earlier stratum **observed** the `c=0`
count and noted `c=−2` "deviates even more"; here both are derived, and the exact
`c=−2` count — absent from the page until now — is pinned down.

Throughout, `p` is an odd prime, `F_p` the field of `p` elements, and for a positive
integer `m` we write `oddpart(m)` for `m` with all factors of 2 removed (so
`m = 2^a · oddpart(m)`).

---

## The one lemma both proofs ride on: squaring **is** the doubling map

`F_p^*` is cyclic of order `p−1`. Fix a generator `g` and write each nonzero element
as `x = g^e`. Then squaring is

```
x ↦ x²   ⟺   e ↦ 2e   (mod p−1),
```

the **doubling map** on the exponent. So the dynamics of squaring on a cyclic group of
order `N` are exactly the dynamics of `e ↦ 2e` on `Z_N`.

> **Lemma (periodic points of doubling).** An element `e ∈ Z_N` is periodic under
> `e ↦ 2e` iff its order (additively) is **odd**, equivalently iff `e` lies in the
> unique subgroup of `Z_N` of order `oddpart(N)`. Hence doubling on `Z_N` has exactly
> `oddpart(N)` periodic points.

*Proof.* Write `N = 2^a · b` with `b = oddpart(N)` odd. By CRT,
`Z_N ≅ Z_{2^a} × Z_b`. On the `Z_{2^a}` factor doubling is nilpotent — `2^a · z = 0`
for every `z`, so the only periodic point is `0`. On the `Z_b` factor, `b` odd, `2` is
a unit, so doubling is a *bijection* and every element is periodic. An element is
therefore periodic iff its `Z_{2^a}`-component is `0`, i.e. iff it lies in the
`{0} × Z_b` subgroup, of which there are exactly `b = oddpart(N)`. ∎

Translating back through `x = g^e`: **the periodic points of `x ↦ x²` on a cyclic group
of order `N` are precisely the unique subgroup of odd order `oddpart(N)`** — the
elements of odd multiplicative order.

---

## Theorem 1 — the map `x ↦ x²` (the case `c = 0`)

> **Periodic points:** `1 + oddpart(p−1)`.
> **Fixed points:** `2` (namely `0` and `1`).
> **Longest cycle:** `ord_b(2)`, the multiplicative order of `2` modulo `b = oddpart(p−1)`
> (and `1` when `b = 1`).
> **Number of cycles:** `1 + Σ_{d | b} φ(d) / ord_d(2)`.

*Proof.* The point `0` is an isolated fixed point (`0² = 0`), hence periodic. On the
nonzero elements `F_p^*` (cyclic of order `p−1`) squaring is the doubling map, so by the
Lemma its periodic points are the odd-order subgroup, of size `oddpart(p−1)`. Total:
`1 + oddpart(p−1)`.

*Fixed points:* `x² = x ⟺ x(x−1) = 0 ⟺ x ∈ {0, 1}` — exactly two.

*Longest cycle / cycle count:* on the odd-order subgroup the doubling map `e ↦ 2e` acts
on `Z_b`. The orbit of `e` has length `ord_{b/gcd(b,e)}(2)`, maximized at `gcd(b,e)=1`
to give `ord_b(2)`. The `φ(d)` elements of additive order exactly `d` (for each `d | b`)
fall into orbits of common length `ord_d(2)`, contributing `φ(d)/ord_d(2)` cycles; the
isolated point `0` adds one more. ∎

Why this kills the birthday law: a random map on `p` points has
`≈ √(πp/2)` periodic points (Flajolet–Odlyzko 1990). Here the count is `oddpart(p−1)`,
which for a prime with `p−1` smooth-and-even (the common case) is *tiny* — often a
handful — so the rho closes almost immediately and discovers nothing. The map isn't
unlucky; it's algebraic.

---

## Theorem 2 — the Lucas–Lehmer map `x ↦ x² − 2` (the case `c = −2`)

> **Periodic points:** `( oddpart(p−1) + oddpart(p+1) ) / 2`   (for `p > 3`; the count is
> integral because exactly one of `p−1, p+1` is `≡ 2 (mod 4)`).
> **Fixed points:** `2` (namely `2` and `−1`), collapsing to `1` at `p = 3` where the two
> roots coincide.

This is the value the page never had. The headline: `c = −2` samples the order
structure of **two** groups, `p−1` *and* `p+1` — which is exactly why it "deviates even
more" than `c = 0`, which sees only `p−1`.

*Proof.* Use the Chebyshev / Lucas substitution. For `y` in `F_p` or its quadratic
extension, set `x = y + y^{−1}`. Then

```
x² − 2 = (y + y^{−1})² − 2 = y² + y^{−2},
```

so under `x = y + 1/y` the map `x ↦ x² − 2` becomes simply `y ↦ y²`. Given `x ∈ F_p`,
its `y` solves `t² − x t + 1 = 0` (product of roots `= 1`, so the two roots are `y` and
`1/y`):

- If `x² − 4` is a nonzero square in `F_p`, then `y, 1/y ∈ F_p^*` (order `p−1`).
- If `x² − 4` is a non-square, then `y, 1/y ∈ F_{p²} \ F_p` are Frobenius-conjugate, so
  `1/y = ȳ = y^p`, giving `y^{p+1} = y·y^p = y·ȳ = 1`: `y` lies in the **norm-one
  subgroup** of `F_{p²}^*`, which is cyclic of order `p+1`.
- `x = 2 ⇒ y = 1`; `x = −2 ⇒ y = −1`.

In every case `x ↦ x² − 2` is conjugate to `y ↦ y²` on a cyclic group (order `p−1` or
`p+1`), so by the Lemma **`x` is periodic iff `y` has odd order**. The periodic `y`'s
are therefore

```
P = { odd-order y in F_p^* }  ∪  { odd-order y in the order-(p+1) group },
```

of sizes `oddpart(p−1)` and `oddpart(p+1)`. The two groups meet in
`F_p^* ∩ (norm-1) = {y : y² = 1} = {±1}`; their only common *odd-order* element is `1`,
so `|P| = oddpart(p−1) + oddpart(p+1) − 1`.

Now `x = y + 1/y` identifies `y` with `1/y` (equal order), so the periodic `x`'s are the
inverse-pair classes inside `P`. The only self-paired element (`y = 1/y ⟺ y = ±1`) that
survives in `P` is `y = 1` (since `y = −1` has even order 2 and is excluded), giving
`x = 2`. Every other periodic `y` pairs with a distinct `1/y`. Hence

```
#periodic x = 1 + (|P| − 1)/2 = ( oddpart(p−1) + oddpart(p+1) ) / 2.
```

*Fixed points:* `x² − 2 = x ⟺ x² − x − 2 = 0 ⟺ (x − 2)(x + 1) = 0 ⟺ x ∈ {2, −1}` — two,
unless `2 ≡ −1`, i.e. `p = 3`, where the double root leaves one. ∎

The full **cycle spectrum** of `c = −2` is *not* a single clean formula: the inversion
`y ↔ 1/y` (negation on the exponent) merges some doubling-cycles and not others. A
doubling-cycle of `y` and the cycle of `1/y` coincide iff `−1` is a power of `2` modulo
the order of `y`; when they coincide the resulting `x`-cycle is *half* the length. So the
longest `c=−2` cycle is `ord_2(·)/2` or `ord_2(·)` according to that order-theoretic
condition — honestly a case split, not a closed form. The **periodic count and the fixed
count above are exact and proven**; the finer spectrum is where the clean theory stops,
and the note says so rather than papering over it.

---

## What is checked, and how (the honesty apparatus)

`verify.mjs` certifies all of the above **two independent ways** — once by the structural
formula, once by *constructing the periodic set from group theory and comparing it
element-for-element* to what the dynamical-graph walker `analyze()` actually finds:

| Claim | Range | How certified |
|---|---|---|
| `c=0` periodic `= 1 + oddpart(p−1)` | primes `p < 2000` | formula vs `analyze()` |
| `c=0` periodic set `= {0} ∪ odd-order subgroup` | primes `p < 500` | **set equality**, built from `x^oddpart(p−1)=1` |
| `c=0` fixed `= 2`, longest `= ord_b(2)`, cycles `= 1+Σφ(d)/ord_d(2)` | primes `p < 2000` | formula vs `analyze()` |
| `c=−2` periodic `= (oddpart(p−1)+oddpart(p+1))/2` | primes `p < 2000` | formula vs `analyze()` |
| `c=−2` periodic set built from `F_p^*` + norm-1 `F_{p²}` | primes `p < 200` | **set equality** vs `analyze()` |
| `c=−2` fixed `= 2` (`=1` at `p=3`) | primes `p < 2000` | roots of `x²−x−2` |
| Chebyshev identity `(y+1/y)²−2 = y²+1/y²` | exhaustive over `F_p`, several `p` | algebraic check |

The set-equality rows are the strong ones: they don't just match a count (a count can
coincide by accident), they show the *mechanism* — that the periodic points really are
the odd-order elements, reached through `x = y + 1/y`. The earlier verifier already
showed these two maps fall *far* from the random-map prediction; this note explains, and
exactly quantifies, *why*.
