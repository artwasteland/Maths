# Fault-free domino tilings of the rectangle — the whole array, not just the square

**Question.** Tile an `m × n` rectangle with `1 × 2` dominoes. A *fault line* is a
straight line — horizontal or vertical — that runs clear across the rectangle
without cutting through any domino. It is a plane of weakness: the reason a
bricklayer *staggers* courses instead of stacking them, and the reason a running
bond holds where a stack bond splits. A tiling is **fault-free** when it has no
such line. Let `FF(m,n)` be the number of fault-free domino tilings of the
`m × n` rectangle (rotations and reflections counted as distinct — the rectangle
sits fixed).

This folder computes the **whole `FF(m,n)` array**, exactly.

## What was already known — and what is new

The **square diagonal** `FF(2n, 2n)` is OEIS **[A124997](https://oeis.org/A124997)**
(Don Knuth, 2008; extended by Alois P. Heinz and Xu Mingkuan, whose b-file
reaches `n = 12`, i.e. the `24 × 24` square). We reproduce **ten** of its twelve
terms, through `FF(20,20)`, as our correctness anchor:

```
FF(8,8)   = 25506                                    recomputed live by verify.mjs
FF(10,10) = 1759280998                               recomputed live by verify.mjs
FF(12,12) = 854818404562894                          recomputed live by verify.mjs
FF(14,14) = 3588226034666378581610                   recomputed live by verify.mjs
FF(16,16) = 138311081613064367684548901556           recomputed live by verify.mjs
FF(18,18) = 50272239752141442901464758051467073726   recomputed by
            oversight/oeis/fault-free-tilings/verify-staged.mjs --full
FF(20,20) = 174927321882862834702052846250836696969014873138
            recomputed ONCE, out of band, 2026-07-27, in 342.8 s; it matched.
            Log: oversight/oeis/fault-free-tilings/ff-20x20-run-2026-07-27.txt
FF(22,22), FF(24,24)                                 NOT computed anywhere here
```

**The last two are quoted from the OEIS b-file, not reproduced.** An earlier
version of this file claimed all twelve, "up to the 70-digit `FF(24,24)`". That
was false, and it was false in a self-certifying way: `verify.mjs:97` recomputes
only `k = 1..8`, `verify.mjs:98-99` defers `k = 9..12` to "computed offline, see
data.json", and `data.json`'s diagonal is a hardcoded literal block in
`gen-data.mjs:9-15` whose comment sends the reader back to `verify.mjs`. The
70-digit number appears in this repository exactly three times, always as a string
literal. Agreement with terms 11 and 12 is not evidence about this engine, because
this engine has never produced them. (The printed lines `verify.mjs:98-99` still
carry the old claim and are a known outstanding defect.)

Term 10 was the one term the old claim could have earned, so it was earned: see
the log above. Terms 11 and 12 were not attempted, and on the measured growth rate
they are hours of compute away.

**What is new here:** the *off-diagonal* rectangle counts — the full array — are
**absent from OEIS** (every row and the antidiagonal reading checked 2026-07-11,
all return `null`). Only the square diagonal and two *weaker* cousins were on
record (A124997; A232621 = *vertically* fault-free `5×2n`; A334396 = a different
tile set). The rows we stage as new sequences:

| rectangle family | first fault-free terms | note |
|---|---|---|
| `FF(5, 2n)` | 6, 108, 1182, 10338, 79818, 570342, … | smallest live width is 5×6 |
| `FF(6, n)`, n≥5 | 6, **0**, 124, 62, 1646, 1630, 18120, … | the `0` is the 6×6 exception, sitting *inside* the row |
| `FF(7, 2n)` | 124, 13514, 765182, 32046702, … | |
| `FF(8, n)`, n≥5 | 108, 62, 13514, 25506, 991186, … | 25506 is the 8×8 = A124997(4) |

and the array itself, read by antidiagonals.

## The theorem the array reproduces (Graham–Kotzig)

R. L. Graham proved (and A. Kotzig had shown the square case): an `m × n`
rectangle with `mn` even has a fault-free domino tiling **for every size with
`m, n ≥ 5`, with exactly one exception — the `6 × 6` square.** Our array shows
this as ground truth, not as a quoted claim:

- every entry with `min(m,n) ≤ 4` is `0` (below `5×6` there is always a fault) —
  save the two degenerate strips `1×2` and `2×1`, which have no interior line at
  all and so are vacuously fault-free (`FF = 1`);
- `FF(6,6) = 0` — the lone hole in the otherwise-solid `≥5` region;
- every other `m,n ≥ 5` with `mn` even is `> 0`.

The smallest fault-free rectangle is therefore `5 × 6`, and `FF(5,6) = 6`.

## Method — inclusion–exclusion, collapsed onto partitions

`FF(m,n)` is sieved out of the count of *all* tilings by removing those with a
fault. Fix the horizontal fault lines `R ⊆ {1..m-1}`: they cut the board into
horizontal strips, each tiled freely, so the number of tilings with horizontal
faults `⊇ R` is a product of strip counts; a further 1-D deconvolution along the
width removes any *shared* vertical fault. Summing over `R` with the usual
`(−1)^|R|` sign gives `FF`.

The trick that makes large `m` fast: the deconvolution depends only on the
*multiset* of strip heights, so we group the `2^(m-1)` subsets `R` by the integer
**partitions of `m`** (627 of them at `m = 20`, not 500 000). All-tilings strip
counts `T(h,k)` come from a standard broken-profile transfer matrix. Everything
is `BigInt`-exact. See `ff.mjs`.

## How the numbers are trusted, and how far each reason reaches

1. **Two independent algorithms agree, below a stated horizon.** `ff.mjs`
   (inclusion–exclusion) and a from-scratch **brute force** that enumerates
   *every* tiling and detects fault lines directly agree on the 8 boards small
   enough to enumerate: `5×6`, `5×8`, `5×10`, `6×6`, `6×7`, `6×8`, `7×6`, `7×8`.
   The largest are `5×10`, `6×8` and `7×8`. **Above that horizon, every value
   rests on `ff.mjs` alone.** Most of the array, and most of the staged terms, are
   above it.
2. **`brute.cpp` is a port, not a third opinion.** It is the same brute-force
   algorithm in C++, so it varies the language and compiler, not the mathematics.
   No gate compiles or runs it and no run output is committed, so at present no
   claim here rests on it.
3. **The published record is reproduced in part:** ten of the twelve terms of
   A124997 (see above), and A232621 (`VFF(5,2n)` = 8, 31, 175, 1015, 5911, 34447).
4. **The classical theorem is reproduced** for `m,n ≤ 12`: the whole zero/nonzero
   map, including the `6×6` exception and the `5×6` smallest. This is a structural
   prediction, not a term-by-term value check.
5. **Internal symmetry** `FF(m,n) = FF(n,m)`, which is the same code path
   evaluated twice and so the weakest check here.

`node research/fault-free-tilings/verify.mjs` → **32/32**. That gate checks the
*engine*. It does not read the b-files staged for deposit; until 2026-07-27
nothing did, and all 470 staged terms could be rewritten without turning it red.
`node oversight/oeis/fault-free-tilings/verify-staged.mjs` is the check that binds
the staged files to this engine.

## Reproduce

```sh
node research/fault-free-tilings/verify.mjs        # the engine check, a few seconds
node oversight/oeis/fault-free-tilings/verify-staged.mjs   # the staged b-files, 10-15 s
node research/fault-free-tilings/gen-data.mjs      # REWRITES data.json (rows + array)
g++ -O2 -o brute research/fault-free-tilings/brute.cpp
./brute 8 8                                        # expects 12988816 tilings, 25506 fault-free
```

`data.json` holds the rows, the `16×16` array and the antidiagonal reading, all of
them engine output, plus a `diagonal` block that is **not**: all twelve of those
values are a literal constant in `gen-data.mjs:9-15`, so none of them is engine
output *as it stands in `data.json`*, whatever its comment says. Ten of the twelve
have since been reproduced elsewhere (see the table at the top of this file); the
largest two, `FF(22,22)` and `FF(24,24)`, are computed nowhere in this repository.
The rows in `data.json` also stop short of the
staged b-files (`rowspec` 6:38, 7:32, 8:26 against staged 6:40, 7:34, 8:28), so it
is not a second record of the staged tails. The b-files staged for OEIS, and the
check that binds them to this engine, are in `oversight/oeis/fault-free-tilings/`.

## The wall

The array is exact for every rectangle whose all-tilings transfer matrix fits in
memory. Time, not memory, is the limit: the height-`m` transfer matrix has `2^m`
states, so each step in the larger side roughly quadruples the work.

Measured on 2026-07-27, Node v22.22.2, `FF` called through `ff.mjs`:

| computation | wall time |
|---|---|
| every term of the staged rows (`FF(5,n)` to n=44, `FF(6,n)` to 40, `FF(7,n)` to 34, `FF(8,n)` to 28), 146 terms | 0.2 s |
| the whole `18 × 18` array up to `max(m,n) = 17` | 10 to 15 s |
| the `18`-edge of that array, 35 cells including `FF(18,18)` | 25 to 40 s |
| the whole `18 × 18` array, 324 cells | 36 to 50 s |
| `FF(20,20)` | **342.8 s** (5 min 43 s), not the "~20 s" this file used to claim |

An earlier version of this section put `FF(20,20)` at "~20 s" and `FF(22,22)` at
"~3 min". The first is wrong by about 17x, now measured. The second was never run
and should be read as unsupported: on the `2^m` growth of the transfer matrix,
`FF(22,22)` is well above `FF(20,20)`'s 5 min 43 s, not below it. Treat the
diagonal above `FF(20,20)` as unreached by this engine until somebody finishes a
run and commits the log, as was done for `FF(20,20)` in
`oversight/oeis/fault-free-tilings/ff-20x20-run-2026-07-27.txt`.

Any *fixed* small height (`FF(5,n)`, `FF(6,n)`, `FF(7,n)`, `FF(8,n)`) runs to
essentially unlimited width in fractions of a second, because the cost there is
`2^m` with `m` small. Those are the rows staged for deposit, and every one of
their terms is recomputed on each run of
`oversight/oeis/fault-free-tilings/verify-staged.mjs`.

## Definition notes

- Fault-free counts *labelled* tilings (the rectangle is fixed in the plane), as
  A124997 does. Counting up to the rectangle's symmetry group is a different,
  also-unrecorded sequence — a natural next computation (Burnside over the
  brute-force enumeration for small boards).
- "Fault-free" is about *straight* full-span lines only; a tiling can still have
  a staggered continuous mortar path and count as fault-free. That is exactly the
  bricklayer's distinction: a running bond has offset joints, not none.
