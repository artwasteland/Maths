# Labeled chip-firing that sorts itself — and the count of the endings it can't decide

**The process.** Put `N` labeled chips — numbered `1..N` — in a single pile at the
origin `0` of the integer line. Whenever some site holds **two or more** chips it is
*unstable* and may **fire**: pick any two chips there, send the **lesser-labeled one
one step left** and the **greater-labeled one one step right** (Hopkins–McConville–Propp's
rule, verbatim: *"we choose any two chips at that vertex and move the lesser-labeled chip
to the left and the greater-labeled chip to the right"*). Keep firing until every site
holds at most one chip. The `N` chips then sit on `N` consecutive sites and, read
left→right, spell a **permutation of `1..N`**.

**The wonder (their Theorem 13).** If `N` is **even**, the pile *sorts itself*: **every**
sequence of firings, however you choose the pairs, ends in the **same** sorted order
`1,2,…,N` — a global order falling out of a blind local rule, a phenomenon they call
*confluence*. For `N = 2m` the terminal chips land on sites `−m..−1` and `1..m` (the
origin left empty), label `i` at the `i`-th site.

**Where it breaks — and what we count.** If `N` is **odd** (`N = 2n+1`), confluence
**fails**: a lone chip can be kept at the origin, and different firing choices reach
different terminal permutations. The number of **distinct terminal permutations
reachable** is **OEIS [A282901](https://oeis.org/A282901)**:

```
n:      0   1    2    3    4     5      6
a(n):   1   3   12   54  232   819   2555
      └──── on record ─────┘   └── new here ──┘
```

A282901 stood at **five terms** (`a(0..4)`, keyword `more`, no formula, no b-file, no
program) since 2017. This folder computes **`a(5) = 819`** — the number of terminal
permutations reachable with **11 labeled chips** — exactly, and three independent ways,
and **`a(6) = 2555`** at `N = 13` (the compute wall on one box; two independent C++
enumerators, the JS methods can't reach it).

## What is new, precisely

- **`a(5) = 819`**, reached over **6 520 201** distinct reachable configurations.
  Absent from OEIS (the sequence had only `a(0..4)`); staged for the catalogue in
  `oversight/oeis/labeled-chip-firing/`.
- **`a(6) = 2555`**, reached over **705 592 802** configurations at `N = 13`.
- The reachable terminal permutations are a *vanishingly small, structured* slice of
  all `N!`: `819` of `11! = 39 916 800` (≈ 0.002 %). The sorted identity is always
  among them (you can always choose to finish the sort); most orders are unreachable.

## How the number is trusted (never a single code path)

Three independent enumerators, all doing an exhaustive search of the reachable-config
graph from the single starting pile, agree on **every** odd `N ≤ 9` — reproducing the
five published terms `1, 3, 12, 54, 232` **and** the reachable-config counts
`1, 4, 56, 1699, 84793` — and then agree on the new `a(5) = 819` (6 520 201 configs):

1. **`enumMap`** (`enum.mjs`) — the reference. A configuration is a `Map` from a *real*
   integer position (negatives allowed) to its sorted labels. Handles even and odd `N`;
   used to reproduce Theorem 13's even-`N` sorting directly.
2. **`enumFast`** (`enum.mjs`) — odd `N` only. A configuration is packed into `N`
   nibbles of a JS `Number` (each label's position `0..N-1`); the visited set is a
   `Set<number>`. Different data structure, same answers.
3. **`cf.cpp`** — a third implementation in C++: the same nibble idea in a `uint64_t`
   with a hand-rolled flat open-addressing hash set (~8 bytes/state), for scale.

`node research/labeled-chip-firing/verify.mjs` → **29/29**, including: the five known
terms from both JS enumerators; the C++ leg built and cross-checked; `a(5) = 819`
confirmed by C++ **and** by `enumFast`; Theorem 13's even-`N` confluence (exactly one
reachable terminal, and it is sorted) with the terminal sites matching their closed
form; and the odd-`N` boundary invariant below.

**`a(6) = 2555`** (at `N = 13`, 705 592 802 configs) is past the reach of the JS methods
(their visited set exceeds JS memory), so it rests on the C++ path — but on **two
independent C++ builds**: `cf.cpp` (MurmurHash mix, linear probing) and a second build
(FNV-1a hash, quadratic probing), which agree on the count *and* on the configuration
total. Both share the firing rule that the three enumerators triple-check on every lower
term through `a(5)`, and both assert the odd-`N` boundary invariant (which never fires),
so the only `N = 13`-specific failure modes are ruled out.

### The boundary invariant that makes the fast encoding sound

For **odd** `N`, the pile's support never reaches its two end sites `±n`, so those sites
never fire and no chip is ever pushed to position `−1` or `N`. That is exactly what lets
`enumFast` and `cf.cpp` represent every position in a single `0..N-1` nibble. Both
enumerators **assert** this invariant on every firing; it never triggers. (For **even**
`N` the origin *does* fire, so the nibble window would underflow — `enumFast` refuses
even `N` on purpose, and `enumMap`, with real positions, is used there instead.)

## Reproduce

```sh
node research/labeled-chip-firing/verify.mjs          # the full check, ~50 s
g++ -O3 -march=native -o cf research/labeled-chip-firing/cf.cpp
./cf 9                                                # a(4) = 232, an anchor
./cf 11                                               # a(5) = 819  (the new term, ~5 s)
./cf 13 30                                            # a(6) = 2555, the wall (~13 min, 2^30 table ≈ 8.6 GB)
```

## The wall

The reachable-config count grows steeply per odd step
(`4 → 56 → 1699 → 84793 → 6 520 201 → 705 592 802`). `a(6)` at `N = 13` searched those
**705 592 802** `uint64_t` states — feasible only with the flat-hash `cf.cpp` and a
multi-GB table (a 2^30-slot table sits at load 0.66), and it is the **last term reachable
on a single commodity box**; `a(7)` (`N = 15`) is out of range here — its config count is
another ~100× larger — and `N ≤ 15` is the nibble ceiling anyway.

## Provenance / honesty notes

- The *process*, its *firing rule*, **Theorem 13**, and the sequence **A282901** are all
  Hopkins–McConville–Propp's (EJC 24 (2017) #P3.13; arXiv:1612.06816). What is original
  here is the **computation of the next terms** `a(5) = 819` (verified three ways) and
  `a(6) = 2555` (two independent C++ builds), plus the reachable-config counts, and their
  staging for the catalogue.
- A282901 counts terminal permutations *up to nothing* — the pile is fixed at the origin
  and orientation is fixed (left = smaller); there is no symmetry quotient to argue.
- `data.json` holds the terms, the reachable-config counts, and the full list of
  reachable terminal permutations for `n = 1, 2` (used by the page's live check).
