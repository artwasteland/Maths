# Independent check of the (13,23) non-realizability certificate

Hostile re-verification, written from scratch with sympy only (`check.py` in this
directory).  Nothing was imported or read from `realize/core.py`, `realize/realize.py`
or `realize/check_realization.py`; `realize/REPORT.md` was read only for the statement
of the claim.  All outputs are in `results/*.json` and `results/*.log`.

Object checked: the single line of `realize/pts-13-23-pseudoline.txt`
(sha256 `bd30d3d2b0a5...3848`, matching REPORT.md):

```
13 23 : 0 1 9 , 0 3 10 , 0 4 7 , 0 5 12 , 0 8 11 , 1 2 8 , 1 4 11 , 1 6 10 , 1 7 12 ,
        2 3 9 , 2 4 10 , 2 6 12 , 2 7 11 , 3 5 7 , 3 6 8 , 3 11 12 , 4 5 6 , 4 9 12 ,
        5 8 9 , 5 10 11 , 6 9 11 , 7 9 10 , 8 10 12 ;
```

Claim under test: there is no set of 13 points over any field of characteristic 0
whose collinear triples are exactly these 23 blocks; the builder's certificate is that
the reduced Groebner basis over Q of the collinearity ideal, frame fixed, saturated by
the product of all 263 non-block determinants, is `{1}`.

## Verdict

**The claim holds, and the certificate is reproduced independently.**  Moreover the
obstruction is much simpler than a general saturation: with a projective frame fixed,
the 23 collinearity equations alone force a non-block triple to be collinear.
Explicit polynomial identities (cofactors, verified by plain expansion, no Groebner
engine involved) are in `results/cofactors_frame1_034.json` and
`results/cofactors_frame2_012.json`.  Their integer forms have leading constants 4 and 9,
so, as a side result that goes beyond the builder's claim, the PTS has no realization
over any field of any characteristic (see "Beyond the claim").

## Method

### 1. Frame and affine chart

A projective frame is four points, no three in a block.  In any realization (exactly the
blocks collinear) such a quadruple is in general position, so a projective
transformation over the field sends it to `(1,0,0),(0,1,0),(0,0,1),(1,1,1)`.

The first two frame points `f0,f1` are chosen so that the pair `{f0,f1}` is covered by no
block.  Then no other point `p` can lie on the line `z=0` through `f0=(1,0,0)` and
`f1=(0,1,0)`: it would make `{f0,f1,p}` collinear, and that triple is not a block.  Hence
every non-frame point has `z != 0` and can be scaled to `(x,y,1)`.  This chart loses no
realization, over any field.  (If every pair is covered, as in the Fano plane, the one
point `p` with `{f0,f1,p}` a block must lie on `z=0` and is given the chart `(x,1,0)`;
`p != f0` forces its second coordinate nonzero.  `check.py` does this automatically and
reports the point as `point_on_infinity`.)

Frame used for the target: **(0,2,1,3)**, i.e. `0->(1,0,0)`, `2->(0,1,0)`, `1->(0,0,1)`,
`3->(1,1,1)`; pair `{0,2}` is uncovered, no three of `0,1,2,3` are in a block.  Second,
disjoint frame for the agreement check: **(4,8,5,7)**.

### 2. Ideal and Groebner basis

Variables: 18 (`x_i, y_i` for the nine non-frame points).  Generators: the 23 block
determinants `det[p_a; p_b; p_c]` with frame coordinates substituted (10 are linear, 13
quadratic).  The reduced Groebner basis was computed **directly** by
`sympy.groebner(..., order='grevlex', domain=QQ)`, no construction sequence, no
solved-for coordinates.  It finished in 0.33 s, so the reduced-variable fallback was
never needed.  Cross-check: the same ideal recomputed with `method='f5b'` and
`order='lex'` (a different algorithm and a different order) gives the same ideal
(mutual reduction to zero), 127 s.

### 3. Non-degeneracy and the radical test

The builder's certificate `I : g^oo = (1)` (g = product of the 263 non-block
determinants) is equivalent to `g in sqrt(I)`.  Since `sqrt(I)` is an ideal, it suffices
that **one** non-block determinant `det_T` lies in `sqrt(I)`; that is tested by
Rabinowitsch: `GB(I + <1 - t*det_T>) == {1}`.  `check.py` tests the 263 non-block
triples in turn and stops at the first success (`--all-forced` enumerates them all).
If none succeeds it falls back to incremental saturation `I : (d_1 d_2 ...)^oo`, one
determinant at a time, via a t-eliminating product order (`ProductOrder(lex(t),
grevlex(rest))`, with a hashable slicer because sympy 1.14's `build_product_order`
result is unhashable).  Saturating by a product equals saturating by the factors in
sequence, so this is exact; it stops as soon as the basis is `{1}`.

### 4. Explicit cofactor certificate (Groebner-free)

For a forced triple `T`, `check.py cofactors` finds polynomials `a_k` with
`det_T^p = sum_k a_k * det_k` (p = smallest power whose normal form is 0; p = 1 for
frame 1, p = 2 for frame 2).  Method: row-reduce the linear generators, substitute
them into the quadratic ones, solve a small Macaulay linear system over Q
(`DomainMatrix.rref`) for cofactors of bounded degree in the free variables, then lift
back to the full ring by exact division through the linear forms.  The final identity is
checked by `sympy.expand` only, and re-checked from the JSON by a separate script that
recomputes the determinants from the frame, multiplies through by the lcm N of the
cofactor denominators, and confirms integrality and `N*det_T^p - sum N*a_k*det_k == 0`.

## Results for the target

### Frame 1 = (0,2,1,3)

Reduced grevlex basis of I (0.33 s): **17 polynomials, all linear**, Krull dimension 1:

```
x4 = x6 = x7 = x10 = x11 = x12          (one free parameter s)
y4 = y5 = y6 = y7 = y8 = y10 = y11 = y12 = 1
x5 = 0,  x8 = 0,  x9 = 1,  y9 = 0
```

So with the frame fixed, every solution of the 23 collinearities (over the algebraic
closure of Q) is the line `L(s)`: points 4,6,7,10,11,12 all at `(s,1,1)`, points 5 and 8 at
`(0,1,1)`, point 9 at `(1,0,1)`.  All eight of 4,5,6,7,8,10,11,12 lie on the line
`y = z` through `0=(1,0,0)` and `3=(1,1,1)`.  `L(s)` was substituted into all 23 block
determinants: all vanish (`L subset V(I)`); the identity below gives the converse.

Single non-block triples: the **first forced triple is (0,3,4)**, found after 21
Rabinowitsch tests (0.22 s).  With `--all-forced`, **149 of the 263** non-block triples are
forced; this set coincides exactly with the set of non-block determinants that vanish
identically on `L(s)`.  Hence `g in sqrt(I)` and `I : g^oo = (1)`: the builder's
certificate is reproduced.

Explicit identity (`results/cofactors_frame1_034.json`, 2.6 s):
`1 - y4 = sum_k a_k * det_k` with all 23 cofactors nonzero, of degree <= 2, denominators'
lcm **N = 4**.  `1 - y4` is `det(0,3,4)`.  Verified by expansion.

### Frame 2 = (4,8,5,7)  (disjoint from frame 1)

Basis: 22 polynomials, max degree 2, dimension 1 (0.50 s).  The ideal is not radical in
this chart.  **92 of 263** non-block triples are forced; the first is **(0,1,2)**.  Same
verdict.  Explicit identity (`results/cofactors_frame2_012.json`, 18 s):
`det(0,1,2)^2 = sum_k a_k * det_k`, 20 of 23 cofactors nonzero, degree <= 3, denominators'
lcm **N = 9** (the degree-<=3 search for `det(0,1,2)^1` is inconsistent, which is why the
square is needed).  Verified by expansion.

### Beyond the claim: any characteristic

Multiplying through, `4*(1 - y4) = sum_k b_k det_k` and `9*det(0,1,2)^2 = sum_k c_k det_k`
with `b_k, c_k` in `Z[x,y]` (integrality confirmed).  These are identities in `Z[x,y]`
and therefore hold over every field.  In a realization over a field K, after moving the
frame to the standard one (possible over any K) and using the chart (valid over any K),
all `det_k` vanish, so `4*det(0,3,4) = 0` and `9*det(0,1,2)^2 = 0`.  If char K != 2 the
first gives `det(0,3,4) = 0`; if char K != 3 the second gives `det(0,1,2) = 0`.  Either
makes a non-block triple collinear.  So **there is no realization over any field**.  The
builder claimed only characteristic 0 and explicitly made no claim in characteristic p;
this is extra, not a correction.

## Controls (same code path, `check.py controls`)

| control | frame | chart note | dim I | single forced? | fallback | witness | got | expected |
|---|---|---|---:|---|---|---|---|---|
| Fano (7,7) | (0,1,3,6) | point 2 on `z=0`, block 012 absorbed by the chart | -1 | I itself = (1) | - | - | one | one |
| Pappus 9_3 | (0,3,1,4) | - | 2 | none of 75 | saturated by all 75: dim 2, not (1) | rational, passes | not_one | not_one |
| Desargues 10_3 | (0,7,1,3) | - | 3 | none of 110 | saturated by all 110: dim 3, not (1) | rational, passes | not_one | not_one |
| non-realizable 10_3 | (0,1,2,4) | - | 2 | none of 110 | saturation reaches (1) at step 13 | - | one | one |
| BGS (14,27) | (0,13,1,3) | - | 1 | (0,5,7) after 41 tests | - | - | one | one |

All five pass.  Notes:

- Fano: the six linear block conditions pin 2=(1,1,0), 4=(1,0,1), 5=(0,1,1) and then
  `det(2,4,5) = -2`, so `I = (1)` over Q before any non-degeneracy is imposed (the
  classical `2 = 0` obstruction; over F_2 this is a realization).  Checked by hand as well.
- Pappus witness: 0=(-3,0,1), 1=(-2,0,1), 2=(-1,0,1), 3=(-3,1,1), 4=(-2,1,1), 5=(0,1,1),
  6=(-5,1,2), 7=(-9,2,5), 8=(-4,1,3).  Desargues witness: 0=(0,0,1), 1=(1,0,1), 2=(0,1,1),
  3=(2,3,1), 4=(2,0,1), 5=(0,2,1), 6=(4,6,1), 7=(-2,2,0), 8=(6,18,0), 9=(-8,-8,0).  Each was
  checked directly on all triples and pairs (exactly the blocks vanish, points distinct),
  then moved into the frame chart and substituted into the ideal generators (all vanish)
  and into every non-block determinant (none vanishes).  A point of V(I) with g != 0
  proves `I : g^oo != (1)` independently of the saturation loop.
- The non-realizable 10_3 exercises the code path the target never needed: no single
  triple is forced, and the incremental product saturation is what reaches (1).
- Dimensions after saturation (Pappus 2, Desargues 3) match the expected dimensions of
  the realization spaces modulo PGL(3) (18-8-8 = 2 and 20-9-8 = 3).

## Worked wrong control (`check.py selftest`, `results/selftest.json`)

- **Frame that puts a point at infinity by mistake.**  Pappus with frame (0,1,3,4): the
  pair {0,1} IS covered (block 012), so point 2 must be on `z=0`.  Giving it the affine
  chart `(x,y,1)` anyway turns `det(0,1,2)` into the constant 1, `I = (1)`, and a naive
  check reports "non-realizable" for a realizable configuration.  With the correct
  `(x,1,0)` chart the same frame gives dim 2 and no forced triple.  In normal operation
  `check.py` refuses a constant generator outright and prefers uncovered first pairs;
  the target's second frame is the guard the brief asked for.
- A perturbed Pappus witness (point 8 moved) is rejected both by the direct triple check
  and by the ideal check.
- Sensitivity of the radical test in both directions on one configuration: Pappus'
  first non-block triple is reported NOT forced; dropping block 678 and asking whether
  678 is forced by the other eight blocks (Pappus' theorem) is reported forced, and stays
  forced after saturating by the other non-block determinants (dim 2).
- A check that only asserts "the Groebner computation finished" is never used: every
  verdict field is derived from `is_one` of a specific basis or from an explicit witness.

## Mutations

### Drop one block (23 cases, `results/mut_drop_*.json`)

Every PTS(13,22) obtained by removing one block **stays non-realizable**: a forced
non-block triple exists in each case (wall 0.3-17 s each).  Dropping (0,1,9) uncovers the
pair {0,1}, so that case automatically used frame (0,1,2,3); the basis grows to 30
polynomials of degree 3, dim 2, and (2,4,6) is forced.  The others keep frame (0,2,1,3);
in 15 of them the basis is unchanged (17 linear forms) and (0,3,4) is still forced; in
the rest the basis has degree 2 and (0,4,5), (0,3,6) or (0,3,4) is forced.

Why this is legitimate: the frame-1 basis shows the 23 collinearities collapse eight
points onto the line 03; removing one collinearity relaxes one equation but the
remaining 22 still pin the same degenerate line (or a slightly larger degenerate
variety).  The known realizable (13,22) arrangement is therefore not a sub-system of
this (13,23); nothing in the claim requires it to be.

The mutation nevertheless changes what the code reports (different bases, different
forced triples, different frames), so the check is not blind to the input; the
"verdict flips" red-on-purpose is instead supplied by the realizable controls (Pappus,
Desargues) and by the Pappus wrong-chart control, which flip the verdict in both
directions through the same code.

### Drop two blocks (253 cases, `results/chainD0b.log`, `results/chainD1b.log`)

See the section "Double-drop outcome" appended at the end of this file.

## Wall times (this machine, 4 cores, sympy 1.14, one process at a time per job)

| step | wall |
|---|---:|
| target frame 1: reduced grevlex basis, 18 vars, 23 generators | 0.33 s |
| target frame 1: Rabinowitsch tests to first forced triple (21 tests) | 0.22 s |
| target frame 1: all 263 tests | 5.1 s |
| target frame 1: lex + f5b recomputation (cross-check) | 127 s |
| target frame 1: explicit cofactors for det(0,3,4) | 2.6 s |
| target frame 2: basis / all 263 tests / cofactors for det(0,1,2)^2 | 0.50 s / 11.7 s / 18 s |
| controls: Fano / Pappus / Desargues / 10_3 / BGS(14,27) | 0.002 s / 2.2 s / 7.6 s / 4.7 s / 3.8 s |
| single-block mutations (23) | about 40 s total |

## What is not claimed

- Nothing about characteristic-p realizations beyond the two explicit identities (which
  together cover every characteristic; each alone misses one prime).
- Nothing about the census (uniqueness of the PTS) or the chirotope step; only the
  realizability verdict on the given line was checked.
- The double-drop mutation search is a sensitivity exercise, not part of the claim.

## Reproduce

```
PY=~/tools/pyenv-maths/bin/python
$PY check.py run --pts-file ../pts-13-23-pseudoline.txt --label target_frame1 --all-forced
$PY check.py run --pts-file ../pts-13-23-pseudoline.txt --label target_frame2 --avoid-frame 0,2,1,3 --all-forced
$PY check.py cofactors --pts-file ../pts-13-23-pseudoline.txt --frame 0,2,1,3 --triple 0,3,4 --label cofactors_frame1_034
$PY check.py cofactors --pts-file ../pts-13-23-pseudoline.txt --frame 4,8,5,7 --triple 0,1,2 --label cofactors_frame2_012 --max-degree 4
$PY check.py controls
$PY check.py selftest
for i in $(seq 0 22); do $PY check.py run --pts-file ../pts-13-23-pseudoline.txt --label mut_drop_$i --drop $i --no-product; done
```

## Double-drop outcome (PARTIAL at the time of writing, 2026-09-06 00:47 AEST)

Every PTS(13,21) obtained by removing two blocks is being run through the same
single-triple test (`--no-product`, 120 s cap per pair, two background workers,
`results/chainD.sh`, logs `results/chainD0b.log` and `results/chainD1b.log`; rerun
`results/summarize_double.py` to refresh the counts).  State when this file was written:

```
double drops finished: 30 of 253 pairs
  forced non-block triple found (non-realizable): 26
  timed out within the per-run cap: 2 -> [(0, 1), (0, 5)]
  no single triple forced (needs product/witness): 0 -> []
  other/errors: 2 -> [(1, 9), (5, 9)]
  forced triples seen: {'triple (2, 4, 6)': 12, 'triple (0, 4, 5)': 13, 'triple (0, 4, 8)': 1}
```

Reading: every pair that finished within the cap is still non-realizable, and only two
forced triples ever appear, (2,4,6) or (0,4,5).  The pairs that did not finish all involve
one of the two blocks through point 9 whose single removal most enlarged the variety,
(0,1,9) and (2,3,9); for (1,9) and (5,9) the basis itself finished (64 and 52 polynomials,
degree 3, in 100 s and 64 s) and only the triple loop was cut off.  The two pairs whose
basis did not finish in 120 s, {(0,1,9),(0,3,10)} and {(0,1,9),(1,2,8)}, are being rerun
with a 15 min basis budget and a 25 min triple budget (`results/chainE.sh`, log
`results/chainE.log`, outputs `results/mut2slow_*.json`).  **No double-drop mutation has
been shown to be realizable so far; none has been shown to be a green witness either.**
This section is a sensitivity exercise and does not bear on the verdict above.
