# Labeled chip-firing, machine-checked (Lean 4)

A machine-checked companion to the stratum
[`the-pile-that-sorts-itself`](../../../src/content/strata/the-pile-that-sorts-itself.md)
(ledger **P5**, deepening a **P2** discovery). The apex of the one rule ("never lie about
anything real"): a proof a *computer's kernel* certified, not one a reader is asked to trust.

## The subject

Hopkins, McConville & Propp, *Sorting via chip-firing*, EJC 24 (2017) #P3.13
(arXiv:1612.06816). Put `N` labeled chips (labels `1..N`) at the origin of the integer
line. A site holding `>= 2` chips may **fire**: choose any two chips there, send the
lesser-labeled one step left, the greater-labeled one step right. Fire until every site
holds `<= 1` chip; the chips then spell a permutation, read left to right.

The **wonder** (their Theorem 13): for **even** `N` the pile always sorts itself, whatever
pairs you choose (confluence). For **odd** `N` the spell breaks, and the number of distinct
reachable endings is **OEIS A282901** (`1, 3, 12, 54, 232, ...`).

## What is proved

`ChipFiring.lean` (Lean 4, **zero imports**) does not reprove the general theorem (that
stays HMP's, cited). It hands the kernel the finite object: it **builds** every
configuration reachable from the origin pile, over every choice, for concrete `N`, and the
kernel checks by counting:

| theorem | claim | meaning |
|---|---|---|
| `even2_sorts`, `even4_sorts`, `even6_sorts` | `perms N = [sorted]` | even N: the one ending is sorted |
| `even4_one_terminal` | `(terminals 4).length = 1` | exactly one terminal config (confluence, as a count) |
| `odd3_count`, `odd5_count` | `= 3`, `= 12` | odd N: exactly the OEIS A282901 terms `a(1)`, `a(2)` |
| `odd3_branches`, `odd5_branches` | `2 <= length` | confluence provably **fails** for odd N |
| `odd3_can_sort`, `odd5_can_sort` | `sorted in perms` | the sort is still reachable, you are just no longer forced |

Every theorem is `by decide` and closes with **`#print axioms -> does not depend on any
axioms at all`**: no `sorry`, no `Classical.choice`, no `native_decide`. The only trusted
component is the Lean kernel. (This is even tighter than the `[propext, Quot.sound]`
footprint the `omega`/`simp` results carry: pure `decide` over concrete `Nat`/`Bool`
computations needs nothing at all.)

## Why this matters here (the honest gap it closes)

The JS/C++ verifier `research/labeled-chip-firing/verify.mjs` reproduces the counts with
three independent enumerators, and they agree. That is strong evidence, but it is still
*code you are asked to trust*. The Lean file settles the same finite claims by logic
instead: the kernel builds the configurations itself and counts them, believing nothing it
cannot derive. It certifies both sides of the wonder at once, the even-N sort **and** the
odd-N branching with the exact catalogue counts, for the piles it runs.

## Faithfulness is machine-checked too

The Nat encoding shifts the origin to site `N` (so positions are non-negative). Two
theorems guard the encoding, in the kernel:

- **`boundary_safe`** — no reachable chip ever sits at site 0, so the truncated `Nat`
  subtraction `p - 1` can never fire at the boundary and corrupt a move. (The minimum site
  reached at `N = 6` is 3, a comfortable margin.)
- **`fuel_saturated_5`, `fuel_saturated_6`** — enlarging the fuel bound leaves the
  reachable set unchanged, so the enumeration is a fixed point, not a truncation.

## Reproduce

```sh
bash install-lean-nix.sh   # github-free route (Nix); or install-lean.sh (elan) if GitHub egress is open
bash verify.sh             # typechecks ChipFiring.lean and prints every axiom footprint (~2-4 min, all in the kernel)
```

`verify.mjs` section 7 also typechecks this file live when `lean` is on `PATH`, and
static-cross-checks the counts it commits to against the JS enumerator, so the browser
check and the kernel proof cannot silently drift.
