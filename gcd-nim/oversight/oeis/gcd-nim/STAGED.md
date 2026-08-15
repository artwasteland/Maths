# Coprime Nim and Common-factor Nim: Grundy sequences, one word apart

*Computed inside the Artificial Wasteland and staged here for deposit. Every
staged term is recomputed and matched by `verify-staged.mjs`, which ships in this
directory; the per-path coverage of every other check is stated exactly below.
Surfaced by the immersive stratum **One Word Apart** (`/strata/one-word-apart/`).
Engine + verifiers: `research/gcd-nim/`.*

## The object

Two one-pile subtraction games, differing in a single word. From a pile of `n`
tokens a player removes `d` tokens (`1 ≤ d ≤ n`); last to move wins (normal play):

| game | legal removal `d` |
|---|---|
| **Coprime Nim** | `gcd(d, n) = 1`, the bite shares **no** factor with the pile |
| **Common-factor Nim** | `gcd(d, n) > 1`, the bite **shares** a factor with the pile |

The quantity of interest is the **Sprague-Grundy value** (nimber) `G(n)` of a
single pile, the number that governs disjunctive (multi-pile) play, where the
value of several piles is the XOR of their `G`. (Single-pile *winning* is trivial
in both games; the depth is in the Grundy spectrum.)

## What is known, and what is new

**Coprime Nim is completely solved, and the solution is a number-theoretic law:**

```
G(0) = 0,   G(1) = 1,   G(even n ≥ 2) = 0,   G(odd n ≥ 3) = index of the least prime factor of n.
```

So an odd pile's value is `k` when its smallest prime factor is the `k`-th prime
(2→1, 3→2, 5→3, …). The odd-pile values therefore reproduce **OEIS A055396**
("Smallest prime dividing n is a(n)-th prime"), the sole boundary being `G(1)=1`
against `A055396(1)=0`. **This is not a new sequence.** It is a *theorem* tying a
Nim variant's Grundy values to the least-prime-factor index.

*What is actually checked here, precisely:* the law `G(odd n ≥ 3) = lpf-index(n)`
is verified for `n = 3..20000` against **our own** least-prime-factor sieve
(`verify.mjs`), and for `n = 3..6000` against a second, independent sieve in
Python (`verify.py`). Agreement with the **published** A055396 is checked only
against the 24 terms transcribed from OEIS into the source, `n = 1..24`, in both
verifiers. We do not hold a copy of A055396 beyond `n = 24`, so no claim of
agreement with the published sequence past `n = 24` is made.

**Common-factor Nim's Grundy sequence appears to be absent from OEIS, and is the
new datum.** Its structure splits cleanly:

- **P-positions are exactly `{0, 1}` (proved).** For every `n ≥ 2`, taking the
  whole pile (`d = n`, and `gcd(n,n)=n>1`) is legal and reaches 0, so every `n ≥ 2`
  is a first-player win. Hence the *interest* is the nimber, not the winner.
  (Also checked computationally for `n = 2..20000`.)
- **`G(even 2k) = k`** (verified `n = 2..20000` in JS, `n = 2..6000` in Python; the
  `≥ k` half is immediate, since every even `d` is legal from an even pile and
  reaches every smaller even value).
- **`G(odd prime) = 1`** (proved: the only legal move from a prime `p` is `d=p → 0`;
  also checked for every odd prime up to 20000).
- **`G(odd prime²) = 2`** (observed, not proved; all 33 odd primes `p` with
  `p² ≤ 20000`).
- **The general odd-pile values are erratic and, so far as we can tell,
  uncatalogued.** No period and no closed form is known. This is the honest open
  frontier.

Common-factor Nim Grundy, `n = 0..30`:
```
0,0,1,1,2,1,3,1,4,2,5,1,6,1,7,4,8,1,9,1,10,5,11,1,12,2,13,7,14,1,15
```
Odd-pile subsequence, `n = 1,3,5,…,59` (the wild part):
```
0,1,1,1,2,1,1,4,1,1,5,1,2,7,1,1,8,3,1,10,1,1,11,1,2,13,1,6,14,1
```

Both `b-common-factor-nim.txt` and `b-coprime-nim.txt` stage `n = 0..4096`
(4097 terms each, 8194 in total).

## Trust: how many ways, and how far each one reaches

The honest count is **two distinct algorithms, one of them implemented three
times**, not "four independent methods". Here is each one and the exact index
range it covers.

**Algorithm 1: one-pile mex recursion.** `G(n) = mex { G(n-d) : d legal }`.
Implemented three times. The three differ in how legality is decided and in what
language they run, but they are the same recursion, so they are three
implementations, not three algorithms.

| implementation | how legality is decided | what it is compared against | index range |
|---|---|---|---|
| `engine.mjs grundy` (JS) | Euclidean `gcd` | the staged b-files | `n = 0..4096`, every staged term (`verify-staged.mjs`) |
| | | the laws | `n = 0..20000` (`verify.mjs`) |
| `engine.mjs grundyByFactorSets` (JS) | intersecting distinct-prime-factor sets off a smallest-prime-factor sieve, never calling `gcd` | the staged b-files | `n = 0..4096`, every staged term (`verify-staged.mjs`) |
| | | implementation 1, term by term | `n = 0..4000` only (`verify.mjs`, `const M = 4000`) |
| `verify.py grundy` (Python) | `math.gcd`, with a standard-library smallest-prime-factor sieve for the number theory | **the structural laws only** | `n = 0..6000`; it makes **no** term-by-term comparison with the JS values and **never reads the b-files** |

**Algorithm 2: two-heap minimax.** A backward induction over pairs of piles that
computes P/N outcomes directly, with no mex and no nimbers anywhere in it. Its
outcome must equal `(G[a] XOR G[b]) == 0`, and it does, for both games. This is
the one genuinely unrelated validation of the nimbers, and it is also the
narrowest: **`a, b ≤ 60` only** (`verify.mjs`, `const M = 60`). It says nothing
about any pile above 60.

**Positive controls** (the mex harness reproduces known results before any new
value is trusted). In `verify.mjs`: subtraction game `S={1,2}` → `G(n)=n mod 3`;
`S={1,2,3}` → `n mod 4`; take-any → `n`; and the least-prime-factor sieve
reproduces the 24 transcribed terms of **A055396**. In `verify.py`: the
replacement standard-library sieve agrees with trial division on primality for
`n = 2..2000`, and reproduces the same 24 A055396 terms.

### Coverage of the staged terms, stated exactly

| | b-coprime-nim.txt | b-common-factor-nim.txt |
|---|---|---|
| staged terms | 4097 (`n = 0..4096`) | 4097 (`n = 0..4096`) |
| recomputed and matched, mex + `gcd` | all 4097 | all 4097 |
| recomputed and matched, factor-set path | all 4097 | all 4097 |
| checked only against a stored expected table (drift protection, not recomputation) | none | none |
| not covered by any check | none | none |
| reached by the two-heap minimax | `n ≤ 60` only | `n ≤ 60` only |
| reached by the Python path | none (it compares no terms) | none (it compares no terms) |

### What was not checked at all, until 2026-07-27

Until 2026-07-27, **nothing in this repository read these b-files.** `gen-data.mjs`
wrote them from one code path and `verify.mjs` never opened them, so the numbers
actually staged for deposit were confirmed by nothing. This was not inferred, it
was measured: a mutation prober rewrote all 8194 staged terms across both files at
once, and both committed checks (`node research/gcd-nim/verify.mjs` and
`python3 research/gcd-nim/verify.py`) still produced byte-identical output and
exit code 0. Single-term probes at indices 0, 2048 and 4096 of each file agree.
The record is `research/oeis-term-coverage/coverage-before.json` under
`dirs["gcd-nim"]`; the claim that failed is catalogued in
`research/oeis-coverage-audit/findings-2026-07-20.json`.

`verify-staged.mjs` in this directory is the fix. It reads these two files and
recomputes every one of the 8194 staged terms twice, and it exits nonzero on a
single mismatch. Corrupting any one term now turns it red.

## Reproduce

Run from the repository root. No third-party packages are needed for any of the
three; the Node scripts use only the standard library plus this repository's own
modules, and the Python script uses only the standard library.

| command | what it covers | measured |
|---|---|---|
| `node oversight/oeis/gcd-nim/verify-staged.mjs` | **the staged b-files themselves**, all 8194 terms, two paths each | `ALL PASS - 8/8 checks; 8194/8194 staged terms recomputed and matched`, 3.1 s |
| `node research/gcd-nim/verify.mjs` | the laws to `n = 20000`, the cross-path agreement to `n = 4000`, the minimax to 60, the positive controls | `ALL PASS — 17/17 checks`, 48.3 s |
| `python3 research/gcd-nim/verify.py` | the same laws recomputed in Python to `n = 6000`, plus two controls on its sieve | `ALL PASS — python 3.11.15` (9/9 checks), 9.2 s |

(Timings measured 2026-07-27 in this container, Node v22.22.2, Python 3.11.15.)

Do **not** run `node research/gcd-nim/gen-data.mjs` to check anything: it is the
producer, and it overwrites both staged b-files.

`verify.py` previously imported SymPy for `primefactors`, `isprime` and `primepi`.
SymPy is not present in a bare checkout of this repository and is declared in no
manifest here, so that "independent path" did not in fact run from a fresh clone.
The three calls are now a standard-library smallest-prime-factor sieve, checked by
the two positive controls named above. Verified 2026-07-27 by re-running the file
with SymPy shadowed by a module that raises on import: it still passes.

## OEIS absence: what we have, and what we do not

The Common-factor Nim Grundy sequence was checked against OEIS by hand on
2026-07-19, searching the literal digit strings of the full sequence and of the
odd subsequence, and again on 2026-07-20 during the coverage audit; both times the
result was no matches, with a working positive control. **No transcript of either
search is committed in this directory**, so that result is not reproducible from
this bundle and is recorded here as an uncommitted observation, not as a verified
claim. A depositor or a human OEIS author should redo the search rather than rely
on it. (Absence from OEIS is in any case a statement about a database at a moment
in time, never a theorem.)

## Provenance (honest, not laundered)

The computation and prose here were produced by an AI instance (Claude) inside the
open *Artificial Wasteland* project, under a strict never-lie / show-the-check
rule; everything above is verified by the reproducible code in this directory and
in `research/gcd-nim/`, at the coverage stated and no further.
Per OEIS policy (AI-authored and automated submissions are **forbidden**), **none
of this has been submitted to the OEIS by the project**. The footprint routes to
a **Zenodo** deposit (DOI) for the reproducible artifact; any of these sequences
should be authored on OEIS only by a human who has independently verified it.

The machinery (Sprague-Grundy theory) is classical (Berlekamp, Conway & Guy,
*Winning Ways*, 1982; Sprague 1935 / Grundy 1939). What appears to be
uncatalogued is the Grundy sequence of Common-factor Nim.
