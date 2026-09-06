# REPORT-EXIST: the existence SAT (CONTRACT Section 9)

Builder: claude (Fable 5.1), taking over from a codex builder that died at its quota wall
after emitting CNFs with a CNF_ONLY verdict. Date 2026-09-05. Program: `exist.py` in this
directory. Python at ~/tools/pyenv-maths/bin/python; solvers /usr/bin/cadical 1.7.3 and
~/tools/sat/kissat/build/kissat 4.0.4; checker ~/tools/sat/drat-trim/drat-trim.

The question encoded: for given (v, b), does a rank-3 chirotope on v elements exist whose
zero set (the set of triples with chi = 0) is a partial Steiner triple system with exactly
b blocks? UNSAT answers carry a DRAT proof checked by drat-trim; SAT answers carry the PTS
and the chirotope, both re-checked directly.

## 1. What the CNF contains

Variables, for each of the C(v,3) increasing triples T: `B(T)` (T is a block), `pos(T)`,
`neg(T)` (chi(T) = +1 or -1; neither means 0), plus the auxiliaries of
`chirosat.build_base_encoding` (a nonzero selector per triple and six product-sign
variables per Grassmann-Pluecker relation; that base is the one the batch filter uses and
whose controls are in REPORT.md). Clauses:

1. the chirotope base (B0-B2 with the rank-3 three-term GP relations over every 5-subset
   and pivot; the axiom system is stated in chirosat.py and REPORT.md and is inherited here);
2. the tie `B(T) <-> (not pos(T) and not neg(T))`; with the base's `not (pos and neg)` this
   gives `not B(T) -> pos xor neg`;
3. pair-disjointness: for every pair, at most one of the v-2 triples through it is a block;
4. exactly b blocks (pysat `CardEnc.equals`, sequential counter);
5. implied degree bounds (Lemma 9): at most floor((v-1)/2) blocks through each point, and
   exactly that many when 2e = v r2min;
6. the symmetry break: point 0's row (Lemma 3), v sign anchors (Lemma 4), and optionally
   a lex-leader constraint per generator of the row stabiliser (Lemma 8);
7. in cube mode, the row of point 1 (Lemma 7).

`derive_reduction(v, b)` derives e, the Kelly-Moser bound, r2min, the canonical row and the
count of minimum-leave points from v and b alone (nothing is hard-coded per case) and
refuses any (v, b) for which the arithmetic below does not force the conclusions.

## 2. The symmetry break, as numbered lemmas

Notation. v points, b blocks, e = C(v,2) - 3b uncovered pairs (the leave). For a point x,
r3(x) = number of blocks through x and r2(x) = leave degree of x. p = (v-1) mod 2.
A "solution" is a pair (chi, B): chi a rank-3 chirotope on {0..v-1} (axioms B0-B2 of
Bjoerner et al., zeros allowed) and B its zero set, with B a PTS (every pair in at most one
block) and |B| = b.

**Lemma 1 (PTS reduction; CONTRACT Section 1).** In a (v,b)-arrangement of points and lines
(or pseudolines) with b three-point lines, if e - 6 < ceil(3v/7) then no line carries four
or more points, and the three-point lines form a PTS(v,b) whose leave is exactly the set of
ordinary (two-point) lines.
Proof. A line with k >= 4 points contains C(k,2) >= 6 pairs, none of them in a three-point
line, so at most e - 6 pairs remain for ordinary lines; Kelly-Moser gives at least
ceil(3v/7) ordinary lines, a contradiction when e - 6 < ceil(3v/7). Two three-point lines
share at most one point, so the triples are pair-disjoint. The Kelly-Moser bound is used
for pseudoline arrangements as well; that extension is Kelly and Rottenberg (1972) and is
the one external fact this reduction rests on, exactly as CONTRACT Section 1 uses it.
The code checks both e >= ceil(3v/7) and e - 6 < ceil(3v/7) and refuses otherwise.

**Lemma 2 (the minimum leave degree is the parity).** In a PTS(v,b), every point has
2 r3(x) + r2(x) = v - 1, so r2(x) = p (mod 2) and r2(x) >= p. If 2e < v (p + 2) then some
point has r2(x) = p, so r2min = p.
Proof. The blocks through x cover 2 r3(x) of the other v-1 points, each once, and the rest
are leave neighbours. If every point had r2(x) >= p + 2, the degree sum 2e would be at
least v (p + 2). The code checks 2e < v (p + 2) and refuses otherwise. Values: (8,8) e=4
r2min=1; (10,13) e=6, 1; (12,20) e=6, 1; (13,23) e=9, 0; (13,24) e=6, 0; (14,27) e=10, 1;
(14,28) e=7, 1; (15,31) e=12, 0; (15,32) e=9, 0; (16,37) e=9, 1.

**Lemma 3 (canonical row of point 0).** Let k = (v - 1 - p) / 2. If a solution exists,
one exists in which point 0 has r2(0) = r2min = p, its blocks are {0,1,2}, {0,3,4}, ...,
{0,2k-1,2k} and its leave pairs are {0,2k+1}, ..., {0,v-1}.
Proof. Take a solution and a point x with r2(x) = p (Lemma 2). Its k blocks partition
2k of the other points into pairs and the remaining p points are its leave neighbours.
Choose a bijection g of the point set with g(x) = 0, sending the i-th block pair of x to
{2i-1, 2i} and the leave neighbours to {2k+1..v-1}. Relabelling a chirotope by a
bijection, chi'(a,b,c) = chi(g^-1 a, g^-1 b, g^-1 c), preserves B0, B1 and every GP
relation (the axioms quantify over all tuples) and maps the zero set to g(B), which is a
PTS with b blocks. So (chi', g(B)) is a solution with the stated row. Conversely every
model of the CNF is a solution, because the row units only restrict. Hence the units
"B(T) for the k row blocks, not B(T) for every other triple containing 0" are sound.

**Lemma 4 (sign anchors kill the reorientation group).** For S a subset of the points,
chi_S(T) = (-1)^|S and T| chi(T) is a chirotope with the same zero set. The v triples
A = {(0,1,3), (0,2,3), (1,2,3), (0,3,5)} together with (0,1,e) for e = 4..v-1 are never
blocks under the canonical row, and their incidence vectors are linearly independent over
GF(2). Therefore every solution with the canonical row is reorientation-equivalent to
exactly one in which chi(A_i) = +1 for all i, and the v unit clauses pos(A_i) are sound.
Proof. Alternation is preserved because the factor depends only on the set T. In the
three-term relation for {a,b,c,d,e} with pivot a, each of the three products
chi(a,b,c)chi(a,d,e), chi(a,b,d)chi(a,c,e), chi(a,b,e)chi(a,c,d) contains a twice and each
of b,c,d,e once, so all three are multiplied by the same sign (-1)^(|S and {b,c,d,e}|),
and "both signs present or all zero" is invariant. The map S -> (|S and A_i| mod 2)_i is
linear GF(2)^v -> GF(2)^v; the code computes the rank of the incidence vectors of A by
elimination and asserts it equals v, so the map is a bijection and for any sign pattern
on A (in particular the pattern of a given chi restricted to A, which has no zeros because
each anchor contains a pair covered by a row block: {0,1}, {0,2}, {1,2} or {0,3}) there is
exactly one S turning it into all +1. The first attempt at this basis, with (1,2,4) as the
v-th anchor, failed the rank check (it lies in the span of the others); the rank check
is what caught it, so it is a check that has gone red.

**Lemma 5 (a second minimum-leave point exists).** Let m be the number of points with
r2(x) > p. Each of them has r2 >= p + 2, so 2e >= v p + 2m and m <= e - v p / 2. Hence at
least v - e + v p / 2 points have the minimum leave degree p: 8 for (8,8), 9 for (10,13),
12 for (12,20), 4 for (13,23), 7 for (13,24), 11 for (14,27), 14 for (14,28), 3 for
(15,31), 6 for (15,32), 15 for (16,37). Cube mode requires at least 2 + p of them, so
that one lies among the row points 1..2k rather than being 0 or a leave neighbour of 0.

**Lemma 6 (the stabiliser of the row).** The permutations of the points fixing 0 and
mapping the canonical row (its blocks and its leave pairs) to itself form
G0 = (Z2 wr S_k) x S_p: they permute the k row pairs {1,2}, {3,4}, ..., possibly swapping
the two points inside any pair, and permute the p leave neighbours of 0. G0 is generated
by the k within-pair transpositions, the k-1 exchanges of adjacent row pairs, and the p-1
adjacent transpositions of leave neighbours (adjacent transpositions generate S_k on the
pairs; conjugating one within-pair swap by S_k gives all of them, which generate the base
(Z2)^k; likewise for S_p). G0 is transitive on the row points 1..2k. The subgroup G1 of
elements fixing point 1 (hence 2) is (Z2 wr S_(k-1)) x S_p on the remaining pairs, with
the same generators minus those touching {1,2}. The code asserts, for every generator, that
it fixes 0 (and 1, 2 for G1) and preserves the row blocks and the leave set of 0. By the
argument of Lemma 3, every g in G0 maps a solution with the canonical row to a solution
with the canonical row; by Lemma 4 the anchors can then be restored by a reorientation,
which does not touch the block variables.

**Lemma 7 (cube-and-conquer over the row of point 1 is complete).** Assume the cube
precondition of Lemma 5. If a solution exists, one exists with the canonical row of 0 and
with point 1 of minimum leave degree (some minimum-leave point y lies in 1..2k, and G0 is
transitive there). Point 1's row is then {0,1,2}, k-1 further blocks {1,a,b} with a, b in
{3..v-1}, and p leave partners in {3..v-1}; no pair {a,b} is a row-0 pair, since those are
already covered by a row-0 block. So the pair (set of pairs {a,b}, set of leave partners)
is one of the "row-1 configurations" C enumerated by `enumerate_row1_configurations`
(which enumerates exactly the matchings of size k-1 on {3..v-1} avoiding row-0 pairs, with
the leftover points as leave partners, and nothing else). G1 acts on C: the code checks
that every generator maps every configuration into C. Let R be the set of orbit
representatives (union-find under the generators, minimum element per orbit). Given a
solution whose configuration is c, pick g in G1 with g(c) = r in R; g preserves the row of
0 (Lemma 6), so (chi relabelled by g, then reoriented by Lemma 4; g(B)) is a solution of
the base CNF whose row-1 units are those of r. Hence: if the CNF plus the units of r is
UNSAT for every r in R, no solution exists; and a model of any cube is a model of the base.
The coverage self-check re-expands each representative under the generators and asserts
the expansions are pairwise disjoint and their union is all of C. Made to fail on purpose:
`--list-cubes --mutate-drop-cube` drops one representative and the program exits 2 with
"cube set does not cover every row-1 configuration: 8 of 10 covered" for (8,8).
Counts: (8,8) 10 configurations, 2 cubes; (10,13) 68, 3; (12,20) 604, 5; (13,24) 544, 2;
(14,27) and (14,28) 6584 configurations, 7 cubes (orbit sizes 120, 160, 960, 640, 480,
384, 3840; sum 6584).

**Lemma 7' (the depth-2 cubes under one depth-1 cube are complete).** Fix a row-1
representative c1 and consider the solutions of its depth-1 cube. Point 2 lies on
{0,1,2}. If d = r2(2), then 2 r3(2) + d = v - 1 gives d congruent to
p = (v - 1) mod 2 and d >= p. The pairs {2,0} and {2,1} are already covered by
{0,1,2}, so its d leave partners lie in {3..v-1}, giving d <= v - 3. Also every
other point has leave degree at least p, hence 2e >= d + (v - 1)p and
d <= 2e - (v - 1)p. Thus every admissible d is among p, p+2, ...,
`top = min(v-3, 2e - (v-1)p)`. If `all_degrees_minimum` applies, meaning
2e = vp, every leave degree is p and the code uses only d = p.
For every such d, `enumerate_row2_configurations` recursively makes the least
remaining point either one of the d leave partners or pairs it with each possible
remaining point. It retains exactly (v - 1 - d)/2 - 1 pairs on {3..v-1}, rejects
the pairs already covered by the row of 0 or c1, and explores every choice in both
branches. It therefore enumerates every possible row of point 2, for every
admissible leave degree, with sorting and a set removing only duplicate descriptions.

Let G2 = Stab_G1(c1). Since G1 fixes 0, 1 and 2, and G2 also preserves c1, G2
preserves the rows of 0 and 1 and the set of pairs unavailable to the row of 2.
It therefore acts on the enumerated row-2 configurations. The closure assertion in
`orbit_representatives`, which applies every element of G2 to every orbit it scans
and requires the image to remain in the enumerated set, is the machine check of this
claim. The independent coverage pass requires the orbits of the retained minima to
be disjoint and to cover the whole enumerated set.

Given a solution of the c1 cube with row-2 configuration c2, choose g in G2 taking
c2 to the minimum of its orbit. Relabelling the solution by g preserves the rows of
0 and 1 and changes the row of 2 to that minimum. Reorienting as in Lemma 4 restores
all sign anchors without changing any block variable. The resulting solution obeys
the base CNF and the units of the corresponding depth-2 child. Conversely, a child
model is a model of its depth-1 parent. Finally let H = Stab_G1(c1,c2), the subgroup
used for the lex-leader inside that child. H maps child models to child models. Choose
the lexicographically least block vector in any H-orbit; exactly as in Lemma 8, it
satisfies x <=lex x composed with h for every h in H. Thus the child's stabiliser
lex-leader is sound. It need not be a complete symmetry break.

**Lemma 8 (generator lex-leader is sound and not complete).** Let
x be the block indicator vector in lexicographic triple order. For a generator g of G0 the
constraint x <=lex (x composed with g), where (x composed with g)_T = x_(g(T)), is sound:
(x composed with g) is the block vector of g^-1(B), which is in the G0-orbit of B, and the
solution whose block vector is lexicographically least in its orbit satisfies every such
inequality (the orbit is closed under G0 by Lemma 6). Using only generators does not remove
all symmetry. The encoding is the standard prefix-equality chain; positions where the two
variables coincide, or where both triples contain 0 (fixed by the row units and permuted
among themselves), are skipped. Inside a cube the G0 constraints are omitted because the
least element of a G0-orbit need not retain the chosen row. They are replaced by the same
lex-leader restricted to every nonidentity element of the subgroup fixing all cubed rows,
which is sound by the same orbit-minimum argument and by Lemma 7 or Lemma 7'.

**Lemma 9 (implied degree bounds).** The blocks through x use disjoint pairs {x,y} among
v-1, so r3(x) <= floor((v-1)/2) = k. If 2e = v p then every r2(x) = p (all >= p, sum
= v p), so r3(x) = k for every x. Both are implied by pair-disjointness and the block
count, hence sound to add. For (8,8), (12,20) and (14,28) the exact form applies.

**What an UNSAT verdict means.** By Lemmas 3, 4, 8, 9 the monolithic CNF is satisfiable
iff a solution (chi, B) exists; in cube mode (Lemmas 7 and 7') a solution exists iff at least
one cube CNF at the selected depth is satisfiable, so refuting (v,b) needs a verified DRAT
proof for EVERY cube at that depth. Such proofs
show: no rank-3 chirotope on v elements has a PTS(v,b) as its zero set. With Lemma 1 this
excludes (v,b)-arrangements of lines in the real plane, affine or projective alike (a
projective transformation sending a line that misses the points to infinity preserves every
collinearity, and the chirotope is computed on homogeneous coordinates). The extension to
pseudoline arrangements uses the Folkman-Lawrence representation of a rank-3 simple oriented
matroid as a pseudoline arrangement (the three-term relations characterise chirotopes only when
the support is the basis set of a matroid, BLSWZ Theorem 3.6.2; here it is, because a PTS together
with its uncovered pairs as 2-point lines is a linear space, hence a simple rank-3 matroid), under which an ordinary line of the point set is a simple
vertex of the arrangement, and Kelly and Rottenberg's Theorem 3.6 (at least 3n/7 simple
vertices; Pacific J. Math. 40 (1972) 617-622). For the VALUE t3(15) only Kelly-Moser 1958 is
needed: BGS Theorem 4 (Kelly-Moser plus pair counting, floor((105 - 7)/3) = 32) gives
t3(15) <= 32, so refuting b = 32 exactly, together with Pegg's 31-line configuration, gives
t3(15) = 31. "Lines through exactly three points" is BGS's t_3; at (15,32) the "at least
three" reading coincides, because a fourth point on any of 32 lines would cover 99 > 98 pairs.
A SAT verdict yields a candidate for stage 3 only.

## 3. Checks that were made to fail

- `--drop-exact-b` on (8,8): SAT with the three-block PTS `8 3 : 0 1 2 , 0 3 4 , 0 5 6 ;`
  (the exact-b constraint is what makes (8,8) UNSAT). Output in scratch/exist-8-8-dropb.json.
- `--corrupt-proof` on (8,8): the DRAT proof truncated to half is rejected by drat-trim
  (exit 1, "s NOT VERIFIED"); the program raises if it is not rejected.
- `--list-cubes --mutate-drop-cube` on (8,8): coverage self-check fails, exit 2.
- The same mutation at depth 2 was made to fail with the exact command and output:

      nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 8 8 --backend pysat --list-cubes --cube-depth 2 --cube-index 0 --mutate-drop-cube
      exist: AssertionError: depth-2 cube set does not cover every row-2 configuration: 4 of 5 covered

  The exit status was 2. The new range checks were also driven red: malformed `nope`
  and reversed `2:1` endpoints were rejected by argparse; using a range without both
  `--cube-depth 2` and `--cube-index` was rejected; cube index 9 was rejected for the
  two-cube (8,8) case; and range `0:3` was rejected because cube 0 has two children.
- The GF(2) rank assertion on the anchors went red twice during development (once for a
  broken rank routine, once for a dependent anchor set) before the basis of Lemma 4 passed.
- `verify_model` re-checks every SAT model against the canonical row, the cube units, the
  block count, pair-disjointness, the leave (edge count, parity, minimum at 0) and, through
  chirosat's `verify_witness`, the exact zero set and every GP relation.


## 4. Controls, in the contracted order

All commands run from this directory with the current exist.py. Backend `cadical` writes
the CNF, runs `/usr/bin/cadical --binary=false -q -w MODEL CNF PROOF`, and on exit 20 runs
`~/tools/sat/drat-trim/drat-trim CNF PROOF` and requires `s VERIFIED` (a SAT model is
checked by verify_model instead). Times are the program's own perf_counter fields; WALL is
`/usr/bin/time` around the whole python process, under nice -n 10 on liam-desktop (4 cores
shared with about twenty other processes, load average 3 to 5, so wall times are noisy).

### (8,8): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 8 8 --backend cadical --artifacts scratch/exist-8-8 --corrupt-proof

variables 3657, clauses 16566 (base 11984, tie 168, pair 420, exact-b 1536, degree 1728, row units 21, anchors 8, lex 701 over 5 generators); GP relations 280; r2min 1, e 4, Kelly-Moser 4.
encode 0.042608 s, write 0.04436 s, solve 0.017565 s, drat-trim 0.170833 s, total 0.27861 s, WALL 0.64 s.
Proof 20764 bytes, sha256 b98f0621c60257c19f092affd6b74eda7738ac245b5fe6beb377220eee42ebad; CNF sha256 d820b70ecdc45836a3de554ca1372f37c1225f6b62f1bf2db8353b1c19066f50; proof at <repo>/research/orchard-15/chiro/scratch/exist-8-8/exist-8-8.cadical.drat.
drat-trim tail: s VERIFIED / c verification time: 0.169 seconds
Corrupt-proof control: proof truncated to half, drat-trim exit 1 with NOT VERIFIED in 0.175415 s: rejected = True.
Result file: scratch/exist-8-8.json.

### (10,13): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 10 13 --backend cadical --artifacts scratch/exist-10-13

variables 12469, clauses 65637 (base 53400, tie 360, pair 1260, exact-b 5564, degree 2840, row units 36, anchors 10, lex 2167 over 7 generators); GP relations 1260; r2min 1, e 6, Kelly-Moser 5.
encode 0.108215 s, write 0.110619 s, solve 0.581646 s, drat-trim 0.570114 s, total 1.379548 s, WALL 1.51 s.
Proof 1009112 bytes, sha256 e66f2e6a5506cb529ba7aa0de6e5da788549a1b48bf57dd0774a069b227c407f; CNF sha256 514d9aa758bbf9fb3e5381a36cad9983b07d74a9b5b58501cff8565cf55a1be3; proof at <repo>/research/orchard-15/chiro/scratch/exist-10-13/exist-10-13.cadical.drat.
drat-trim tail: s VERIFIED / c verification time: 0.565 seconds
Result file: scratch/exist-10-13.json.

### (12,20): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 12 20 --backend cadical --artifacts scratch/exist-12-20

variables 39473, clauses 203850 (base 167200, tie 660, pair 2970, exact-b 16000, degree 12000, row units 55, anchors 12, lex 4953 over 9 generators); GP relations 3960; r2min 1, e 6, Kelly-Moser 6.
encode 0.386197 s, write 0.281506 s, solve 9.555727 s, drat-trim 6.073195 s, total 16.344946 s, WALL 16.50 s.
Proof 14249814 bytes, sha256 bbafcff47c2039085f11d5f91d3075b7788134748ad34c5fb89645f1beedef3a; CNF sha256 909b7723ce78dc15b7622269b1938d0161183c7777bb283ae8701f7e92c187a2; proof at <repo>/research/orchard-15/chiro/scratch/exist-12-20/exist-12-20.cadical.drat.
drat-trim tail: s VERIFIED / c verification time: 6.063 seconds
Result file: scratch/exist-12-20.json.

### (14,27): SAT, model checked = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 27 --backend cadical --artifacts scratch/exist-14-27 --timeout 1200

variables 87353, clauses 487973 (base 421876, tie 1092, pair 6006, exact-b 36396, degree 13020, row units 78, anchors 14, lex 9491 over 11 generators); GP relations 10010; r2min 1, e 10, Kelly-Moser 6.
encode 1.250709 s, write 0.808474 s, solve 412.357243 s, model check 0.28672 s, total 414.872851 s, WALL 415.15 s (MAXRSS 161 MB).
PTS: `14 27 : 0 1 2 , 0 3 4 , 0 5 6 , 0 7 8 , 0 9 10 , 0 11 12 , 1 4 13 , 1 5 12 , 1 6 10 , 1 7 11 , 1 8 9 , 2 3 6 , 2 4 9 , 2 5 7 , 2 8 13 , 2 10 12 , 3 5 9 , 3 7 10 , 3 8 12 , 3 11 13 , 4 6 12 , 4 8 10 , 5 8 11 , 5 10 13 , 6 7 13 , 6 9 11 , 7 9 12 ;`
Leave: 10 edges, degrees [1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 3, 1, 3], pairs [[0, 13], [1, 3], [2, 11], [4, 5], [4, 7], [4, 11], [6, 8], [9, 13], [10, 11], [12, 13]].
Chirotope (364 characters, 27 zeros): `0++++++++++++++++++++++0++++----+++++----+0--------------0----+----+0--+--+0++++++++++++++++---+-++-+---+--0+---+-0+---0---+++0++0+-+++-++---++++-0--++++-----0+++-+0++++++--++++-++++++++++0+++--0-+------++++-+--0+-++--++++-+-0--+-+-0+-+--++--0-+---+--+---+-0-+----+-0--+---+++--+++++++++--------0---+--++0--------0----+-0-++++-++++++--+0-++-----+--++----++--+--++-`
Result file: scratch/exist-14-27.json.

This (14,27) run is UNHINTED: no known configuration was given to the solver in any form.
The leave has three points of degree 3 (points 4, 11, 13) and eleven of degree 1, one of the
three degree patterns that 14 odd degrees summing to 20 allow: (3,3,3,1^11), (5,3,1^12),
(7,1^13). Independent cross-check: the PTS line written to scratch/exist-14-27.pts was fed to
the stage-2 filter, `nice -n 10 ~/tools/pyenv-maths/bin/python chirosat.py scratch/exist-14-27.pts
--artifacts scratch/exist-14-27-crosscheck`, which builds its own CNF and gives verdict
pseudoline (solve 0.227 s, total 1.528 s, witness with 27 zeros).

### (15,31): SAT, model checked = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 15 31 --backend cadical --artifacts scratch/exist-15-31 --timeout 1200

variables 129299, clauses 727103 (base 632450, tie 1365, pair 8190, exact-b 52576, degree 18795, row units 91, anchors 15, lex 13621 over 13 generators); GP relations 15015; r2min 0, e 12, Kelly-Moser 7.
encode 2.752456 s, write 1.378837 s, solve 491.880632 s, model check 0.504173 s, total 496.740361 s, WALL 497.59 s (MAXRSS 227 MB).
PTS: `15 31 : 0 1 2 , 0 3 4 , 0 5 6 , 0 7 8 , 0 9 10 , 0 11 12 , 0 13 14 , 1 3 14 , 1 4 13 , 1 5 12 , 1 6 10 , 1 7 11 , 1 8 9 , 2 3 10 , 2 4 7 , 2 5 13 , 2 9 11 , 2 12 14 , 3 5 8 , 3 6 11 , 3 12 13 , 4 5 9 , 4 8 12 , 4 10 11 , 5 11 14 , 6 7 12 , 6 8 14 , 6 9 13 , 7 9 14 , 7 10 13 , 8 11 13 ;`
Leave: 12 edges, degrees [0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 4, 0, 2, 0, 2], pairs [[2, 6], [2, 8], [3, 7], [3, 9], [4, 6], [4, 14], [5, 7], [5, 10], [8, 10], [9, 12], [10, 12], [10, 14]].
Chirotope (455 characters, 31 zeros): `0++++++++++++++++++++++++0++++++++++++++++++++0----++------++--0--++----++--0++--++--0----0++++++++++++++++++++++0++++++++0-++--++0--+--0+------0---0+++--+++--+---------+--+--0------0-------++++++-0-+--+-----------+++---+0----------+0-----------++0+++---+--+0----------+++---++----------0--++-0++---+--++----------+++0--++---0---------++++--+++++--++---+++--+++--++-+0--++++-0++--++-0-++0+-+++-----+--++---++-0++0+-----+---++--++-0---+--++-----+-----+--++`
Result file: scratch/exist-15-31.json.

UNHINTED. Leave: 12 edges, four points of degree 0 (0, 1, 11, 13), one of degree 4 (point 10), ten
of degree 2; all even as Lemma 2 requires. Cross-check: `nice -n 10 ~/tools/pyenv-maths/bin/python
chirosat.py scratch/exist-15-31.pts --artifacts scratch/exist-15-31-crosscheck` gives verdict
pseudoline (solve 0.275 s, total 2.824 s, witness with 31 zeros).

### (14,28): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 28 --backend cadical --artifacts scratch/exist-14-28 --timeout 1800

variables 94019, clauses 500381 (base 421876, tie 1092, pair 6006, exact-b 37632, degree 24192, row units 78, anchors 14, lex 9491 over 11 generators); GP relations 10010; r2min 1, e 7, Kelly-Moser 6.
encode 0.841103 s, write 0.726528 s, solve 1186.218018 s, drat-trim 1283.239773 s, total 2473.773918 s, WALL 2477.19 s (MAXRSS 245 MB; cadical about 20 min, drat-trim about 21 min).
Proof 279588734 bytes, sha256 4bfe1e3de865d76a4e0a96e00513c1fa45544d060729d8ade3d94426d368c143; CNF sha256 f67755f479cc82d634653e9d46f91005c16be6f9b4fe664a076c67efee836aec; proof at <repo>/research/orchard-15/chiro/scratch/exist-14-28/exist-14-28.cadical.drat.
drat-trim tail: s VERIFIED / c verification time: 1283.133 seconds
Result file: scratch/exist-14-28.json.

The monolithic run finished inside the 30-minute solving budget (cadical 1186 s on one core
under nice on the shared box), so the cube-and-conquer fallback was not required for the
verdict; the checker needed a further 1283 s (drat-trim, backward mode, 956004 of 1859760
lemmas in core, 66475760 resolution steps). The cube machinery is implemented and exercised on
(8,8) (Section 5) and remains available for harder cases.

### (16,37): TIMEOUT

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 16 37 --backend cadical --artifacts scratch/exist-16-37 --timeout 1200

variables 185671, clauses 1049266 (base 919520, tie 1680, pair 10920, exact-b 77404, degree 23408, row units 105, anchors 16, lex 16213 over 13 generators); GP relations 21840; r2min 1, e 9, Kelly-Moser 7.
encode 3.273456 s, write 2.665059 s, solve 1200.197503 s, total 1206.340708 s, WALL 1212.24 s (MAXRSS 292 MB).
Timed out after 1200.0 s; partial proof 273043456 bytes.
Result file: scratch/exist-16-37.json.

NOT A VERDICT: the unhinted cadical search did not finish in its 1200 s budget (the previous
builder saw the same at 600 s). A pysat run with the known Kuhne et al. structure as initial
phases only (`exist.py 16 37 --backend pysat --phase-hint`) also found nothing in 20 minutes and
was killed (its --timeout was a no-op at the time: python-sat's Cadical153 has no interrupt, a
silent failure found and fixed afterwards by running the solve in a forked child; a 0.001 s budget
on (8,8) now yields TIMEOUT). What IS established for (16,37):

### (16,37): SAT, model checked = True

    timeout 600 nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 16 37 --backend pysat --hint-cube --phase-hint --timeout 300

variables 185671, clauses 1049266 (base 919520, tie 1680, pair 10920, exact-b 77404, degree 23408, row units 105, anchors 16, lex 16213 over 13 generators); GP relations 21840; r2min 1, e 9, Kelly-Moser 7.
encode 2.564096 s, write None s, solve 1.997955 s, model check 0.465957 s, total 5.081857 s, WALL 5.62 s (MAXRSS 442 MB).
PTS: `16 37 : 0 1 2 , 0 3 4 , 0 5 6 , 0 7 8 , 0 9 10 , 0 11 12 , 0 13 14 , 1 4 14 , 1 5 15 , 1 6 12 , 1 7 13 , 1 8 10 , 1 9 11 , 2 3 13 , 2 5 11 , 2 6 15 , 2 7 9 , 2 8 14 , 2 10 12 , 3 5 10 , 3 6 11 , 3 7 12 , 3 8 15 , 3 9 14 , 4 5 12 , 4 6 9 , 4 7 15 , 4 8 11 , 4 10 13 , 5 7 14 , 5 9 13 , 6 8 13 , 6 10 14 , 7 10 11 , 8 9 12 , 11 13 15 , 12 14 15 ;`
Leave: 9 edges, degrees [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3], pairs [[0, 15], [1, 3], [2, 4], [5, 8], [6, 7], [9, 15], [10, 15], [11, 14], [12, 13]].
Chirotope (560 characters, 37 zeros): `0++++++++++++++++++++++++++0++++++--+++++++++--+++0--------+--------+0------+------+0--+++--+++0++++++0+++++++++++++++++-+++++-++++-++-+--+0+---------0+++++0+++-----0-+-0--+-++0-+++--+-+-++++++-++++----+++0--+-----+---------0----++++++++0-0++++--+++++0-++++--+0-------------------++-------0++---++++0-+++--++0+---++-+-0++-+0+++---+----++--+-----+0---++0+--+++--++-+-0-+0-+-++--++++-0--+-+-+++--+--------++-----0+------+---0++--++++++++++++++++++++-++++0+--++---++-0-+------+--------+----++0+-+-+-+--+++-+--0-++++-+-+-+--+++-+++---+----++--++-+-+++--++++-0+--0+`
Result file: scratch/exist-16-37-hintcube.json.

This is an ENCODING-CONSISTENCY check, not a search control: the known (16,37) structure,
relabelled to the canonical row and descended to satisfy the generator lex-leaders, was assumed
as the whole block vector (hint_cube_satisfied = True) and the solver only had to find the
chirotope (376 conflicts). It shows the CNF, the row fix, the anchors, the degree bounds and the
lex constraints admit the known solution. The leave has 9 edges, fifteen points of degree 1 and
one of degree 3, all odd. A kissat run with a 3600 s budget was started afterwards; see below.

## 5. Targets attempted after the controls

### (13,24): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 24 --backend cadical --artifacts scratch/exist-13-24 --timeout 7200

variables 58301, clauses 319546 (base 271414, tie 858, pair 4290, exact-b 25152, degree 10062, row units 66, anchors 13, lex 7691 over 11 generators); GP relations 6435; r2min 0, e 6, Kelly-Moser 6.
encode 0.759709 s, write 0.598605 s, solve 544.614256 s, drat-trim 515.322941 s, total 1062.82579 s, WALL 1063.07 s (MAXRSS 202 MB; cadical about 9 min, drat-trim about 9 min).
Proof 217676846 bytes, sha256 1b3754a3d866131972be291e72f0669a35405b5cdd7eae43e81302ed6851862c; CNF sha256 2eb5148311018f3c47e1619e2824ee63941fedc42553e12cab6cc2cedf413938; proof at <repo>/research/orchard-15/chiro/scratch/exist-13-24/exist-13-24.cadical.drat.
drat-trim tail: s VERIFIED / c verification time: 515.283 seconds
Result file: scratch/exist-13-24.json.

Started 08:30:50, finished 08:48:33 AEST, well inside the two-hour budget. Reduction as derived
in code: e = 6, Kelly-Moser 6, so every uncovered pair is an ordinary line and no line has four
points; r2min = 0; point 0's row is six blocks and no leave pair; at least 7 points have leave
degree 0. What this proves (Lemmas 1 to 9): NO rank-3 chirotope on 13 elements has a PTS(13,24)
as its zero set, hence no (13,24) arrangement of pseudolines exists, hence none of real lines
(consistent with Du's t3(13) = 22). It does NOT decide existence over C or over finite fields,
which is the part of Kuhne, Szemberg and Tutaj-Gasinska's question that stays open; chirotopes
see only ordered fields. Certificate: the CNF (regenerable by the command above; sha256 in the
result file) and the DRAT proof scratch/exist-13-24/exist-13-24.cadical.drat, verified by
drat-trim (859214 of 1515106 lemmas in core, 48515194 resolution steps).

### (13,23): SAT, model checked = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 23 --backend cadical --artifacts scratch/exist-13-23 --timeout 7200

variables 57823, clauses 318590 (base 271414, tie 858, pair 4290, exact-b 24196, degree 10062, row units 66, anchors 13, lex 7691 over 11 generators); GP relations 6435; r2min 0, e 9, Kelly-Moser 6.
encode 0.679326 s, write 0.548028 s, solve 39.801244 s, model check 0.17176 s, total 41.306739 s, WALL 41.53 s (MAXRSS 116 MB).
PTS: `13 23 : 0 1 2 , 0 3 4 , 0 5 6 , 0 7 8 , 0 9 10 , 0 11 12 , 1 3 12 , 1 4 10 , 1 5 8 , 1 6 7 , 1 9 11 , 2 3 8 , 2 4 9 , 2 5 7 , 2 6 10 , 3 5 11 , 3 7 9 , 4 6 12 , 4 7 11 , 5 9 12 , 6 8 9 , 7 10 12 , 8 10 11 ;`
Leave: 9 edges, degrees [0, 0, 2, 2, 2, 2, 2, 0, 2, 0, 2, 2, 2], pairs [[2, 11], [2, 12], [3, 6], [3, 10], [4, 5], [4, 8], [5, 10], [6, 11], [8, 12]].
Chirotope (286 characters, 23 zeros): `0++++++++++++++++++++0++++++++++++++++0------------0++++++++0----0++++++++++-+++++-+0+++++0++--0----0++-+-++-+------0-++-----0----+-++0-+--0+--+-+++0+++--+------+-++-++++++++--+--0-+++-+-+0-+------+-++--++--+-+++-+0+--0------+-++--------++-++++++-0--+--+-+0++++++--+-----+-+0----0----++`
Result file: scratch/exist-13-23.json.

(13,23) was not in the takeover brief's list but is CONTRACT target (A) and TASK-3's next item, and
a thread was free; it took 40 s. UNHINTED. The verdict is SAT: a rank-3 chirotope on 13 elements
whose zero set is a PTS(13,23) exists, so (13,23) does NOT die at the chirotope (pseudoline) stage;
NOTES.md asked at which stage Du's t3(13) = 22 shows up, and the answer is stage 3 (real
realizability), exactly the (14,27) pattern of BGS Theorem 10. The leave is a single 9-cycle
2-11-6-3-10-5-4-8-12 on nine points of degree 2, with four full points (0, 1, 7, 9), even degrees as
Lemma 2 requires. Cross-check: `nice -n 10 ~/tools/pyenv-maths/bin/python chirosat.py
scratch/exist-13-23.pts --artifacts scratch/exist-13-23-crosscheck` gives verdict pseudoline (solve
0.182 s, witness with 23 zeros). This model is ONE candidate; CONTRACT Section 9 asks for all
models up to isomorphism (blocking clauses on the block variables, canonical form of each PTS)
before stage 3, which is not done here (see UNCERTAIN).

### (13,24) reproduced by a second solver (CONTRACT Section 8.3 b)

### (13,24): UNSAT, proof verified = True

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 24 --backend kissat --artifacts scratch/exist-13-24-kissat --timeout 1800

variables 58301, clauses 319546 (base 271414, tie 858, pair 4290, exact-b 25152, degree 10062, row units 66, anchors 13, lex 7691 over 11 generators); GP relations 6435; r2min 0, e 6, Kelly-Moser 6.
encode 0.860277 s, write 0.555245 s, solve 598.445082 s, drat-trim 631.350118 s, total 1233.036389 s, WALL 1233.40 s (MAXRSS 267 MB).
Proof 137494740 bytes, sha256 2d4b1aa934ed364200a9e5e3a685ab846d390d5cb150c058b96ab3d3c545faf5; CNF sha256 2eb5148311018f3c47e1619e2824ee63941fedc42553e12cab6cc2cedf413938; proof at <repo>/research/orchard-15/chiro/scratch/exist-13-24-kissat/exist-13-24.kissat.drat.
drat-trim tail: s VERIFIED / c verification time: 631.303 seconds
Result file: scratch/exist-13-24-kissat.json.

Same CNF as the cadical run (identical sha256 2eb51483...), kissat 4.0.4, its own DRAT proof
(137494740 bytes, 21169 RAT lemmas in core) verified by drat-trim. Two solvers, two checked proofs.

### (14,28) again, by cube-and-conquer over the row of point 1 (Lemma 7)

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 28 --cubes --backend cadical --artifacts scratch/exist-14-28-cubes --timeout 600

Verdict UNSAT: 7 cubes from 6584 row-1 configurations under G1 of order 3840 (orbit sizes [120, 160, 960, 640, 480, 384, 3840]); every cube UNSAT with its own DRAT proof verified by drat-trim (all_proofs_verified = True); WALL 1189.99 s (MAXRSS 285 MB), started 09:21:02, finished 09:40:52 AEST. Each cube's CNF is the base of Section 1 plus the row-1 units plus a lex-leader for every non-identity element of the cube's stabiliser G2 (Lemma 8 inside the cube); no G0 lex-leader. (The per-cube JSONL of this run lacks the cube name because of a key collision fixed afterwards; rows are in cube order, which is the order of the representatives listed by --list-cubes.)

| cube | blocks through point 1 (besides {0,1,2}) | leave partner | orbit size | G2 lex elements | clauses | solve s | drat-trim s | proof MB |
|---|---|---|---|---|---|---|---|---|
| 0 | {1,3,5} {1,4,6} {1,7,9} {1,8,10} {1,11,13} | 12 | 120 | 31 | 537463 | 71.3 | 45.8 | 46.4 |
| 1 | {1,3,5} {1,4,6} {1,7,9} {1,8,11} {1,10,12} | 13 | 160 | 23 | 525983 | 2.1 | 1.2 | 3.9 |
| 2 | {1,3,5} {1,4,6} {1,7,9} {1,8,11} {1,10,13} | 12 | 960 | 3 | 494283 | 144.4 | 94.8 | 57.4 |
| 3 | {1,3,5} {1,4,7} {1,6,8} {1,9,11} {1,10,13} | 12 | 640 | 5 | 498101 | 128.7 | 91.9 | 56.4 |
| 4 | {1,3,5} {1,4,7} {1,6,9} {1,8,10} {1,11,13} | 12 | 480 | 7 | 501967 | 125.8 | 96.3 | 57.3 |
| 5 | {1,3,5} {1,4,7} {1,6,9} {1,8,11} {1,10,12} | 13 | 384 | 9 | 505917 | 1.4 | 1.3 | 3.6 |
| 6 | {1,3,5} {1,4,7} {1,6,9} {1,8,11} {1,10,13} | 12 | 3840 | 0 | 490968 | 205.4 | 156.9 | 67.4 |

Sums: solve 679.3 s, drat-trim 488.4 s, against 1186.2 s and 1283.2 s for the monolith: the split is about twice as
fast end to end on one core, gives seven proofs of 3.6 to 67.4 MB instead of one of 280 MB, and is embarrassingly parallel.
The largest orbit (3840, trivial stabiliser) is the slowest cube. The two cubes whose leave partner of point 1 is 13 (the leave
partner of point 0) die in about 2 s: there point 13 would have leave degree 2, contradicting Lemma 9's exact degree, and the
solver finds that quickly. Per-cube records: scratch/exist-14-28-cubes/cubes-14-28-depth1.jsonl.

### (16,37) with kissat, unhinted, one hour

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 16 37 --backend kissat --artifacts scratch/exist-16-37-kissat --timeout 3600

TIMEOUT after 3600.1 s of kissat (WALL 3605.78 s, MAXRSS 292 MB, 08:42:09 to 09:42:15 AEST), partial
proof of 798 MB deleted. NOT A VERDICT. (16,37) is the one control whose SAT verdict this program did
not reach by search; the encoding admits the known solution (hint-cube run above).

### Cube counts for the (15,32) target (listing only; NOT attempted, as instructed)

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 15 32 --list-cubes --cube-depth 1 --backend pysat   (2.67 s)
    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 15 32 --list-cubes --cube-depth 2 --backend pysat   (10.60 s)

r2min = 0, at least 6 full points, point 0's row is seven blocks. Row-1 configurations 6040 (perfect
matchings of {3..14} avoiding the six row-0 pairs), G1 = Z2 wr S6 of order 46080, 4 level-1 cubes with
orbit sizes 120, 1440, 640, 3840 (stabilisers of order 384, 32, 72, 12); 8922 depth-2 cubes
(301, 2229, 999, 5393 under the four level-1 cubes). For scale: (14,28) had 7 level-1 cubes and took
679 s of solving in total.

Note for the supervisor: a process not started by this builder, `exist.py 15 32 --backend cadical
--cubes --cube-index 0 --artifacts scratch/exist-15-32-c0`, has been running here since 08:50:20
AEST (user liam, detached), with a 33 MB CNF of 1,521,924 clauses (the 383-element G2 lex-leader of
cube 0 is most of it) and a partial proof of 617 MB at 09:42. It was left untouched. Its CNF was
built by the exist.py of 08:50, which already had the cube stabiliser lex; the only later code changes
are the pysat child-process timeout and the cube_name key, neither of which affects that CNF.

## Depth-2 cubes (2026-09-05)

`--cube-children A:B` selects the half-open range of global child indices returned by
`refine_cube` under the single selected depth-1 cube. Names retain those global indices,
so two runs of ranges `0:1` and `1:2` produced an appended two-line JSONL with names
`cube000-000` and `cube000-001`. A depth-2 listing with one `--cube-index` includes every
child's name, both row configurations, orbit size and child stabiliser order in
`level2[k].children`. The range is applied only to solving, not to that complete listing.

The depth-1 regression guard was run before the first edit and again after the implementation:

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 24 --backend cadical --cubes --cube-index 0 --artifacts scratch/depth2-regress-before --timeout 1200
    before cnf_sha256 5dfdfb7d11c70238dedfae7c56e1bb441dca1adc7a10279338b4dda5b0b49a69

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 24 --backend cadical --cubes --cube-index 0 --artifacts scratch/depth2-regress-after --timeout 1200
    after  cnf_sha256 5dfdfb7d11c70238dedfae7c56e1bb441dca1adc7a10279338b4dda5b0b49a69

The CNF files are byte-identical by SHA-256. Both runs were UNSAT and both proofs were
verified, but the invariant under test here is the CNF byte stream.

The four complete UNSAT controls used these exact commands. CaDiCaL produced every proof
and the automatically resolved `~/tools/sat/drat-trim/drat-trim` checked every proof.

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 8 8 --backend cadical --cubes --cube-depth 2 --artifacts scratch/depth2-control-8-8 --timeout 1200
    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 10 13 --backend cadical --cubes --cube-depth 2 --artifacts scratch/depth2-control-10-13 --timeout 1200
    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 12 20 --backend cadical --cubes --cube-depth 2 --artifacts scratch/depth2-control-12-20 --timeout 1200
    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 13 24 --backend cadical --cubes --cube-depth 2 --artifacts scratch/depth2-control-13-24 --timeout 1200

Verdict lines, with times summed from the individual JSONL records:

    (8,8)   verdict=UNSAT children=8   UNSAT=8   proof_verified=true=8   exact_s_VERIFIED=8   solve=0.071240 s check=0.734602 s
    (10,13) verdict=UNSAT children=141 UNSAT=141 proof_verified=true=141 exact_s_VERIFIED=141 solve=4.639731 s check=16.995779 s
    (12,20) verdict=UNSAT children=593 UNSAT=593 proof_verified=true=593 exact_s_VERIFIED=593 solve=69.499496 s check=135.580267 s
    (13,24) verdict=UNSAT children=700 UNSAT=700 proof_verified=true=700 exact_s_VERIFIED=700 solve=310.549628 s check=378.630222 s

For the two-sided SAT control, the known BGS Theorem 10 PTS was relabelled through the
same row stabilisers to identify a child containing it. No block or phase hint was passed
to the solver. The exact solve command and verdict line were:

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 27 --backend cadical --cubes --cube-depth 2 --cube-index 6 --cube-children 14979:14980 --artifacts scratch/depth2-control-14-27-sat --timeout 1200
    cube006-14979 verdict=SAT solve=7.009980 check=0.122483 total=8.501584 model_checked=true

For (14,28), listing only confirmed 6912 children, split 138, 177, 1027, 672, 505,
409 and 3984 under the seven depth-1 cubes:

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 28 --backend pysat --list-cubes --cube-depth 2
    verdict CUBES_LISTED
    children 6912

The first 20 used this exact command:

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 14 28 --backend cadical --cubes --cube-depth 2 --cube-index 0 --cube-children 0:20 --artifacts scratch/depth2-control-14-28-first20 --timeout 1200

The exact per-child verdict and timing lines were:

    cube000-000 verdict=UNSAT solve=0.229215 check=0.460294 proof_verified=true
    cube000-001 verdict=UNSAT solve=0.219866 check=0.430367 proof_verified=true
    cube000-002 verdict=UNSAT solve=0.217789 check=0.407315 proof_verified=true
    cube000-003 verdict=UNSAT solve=0.232192 check=0.412176 proof_verified=true
    cube000-004 verdict=UNSAT solve=0.222944 check=0.416758 proof_verified=true
    cube000-005 verdict=UNSAT solve=0.235059 check=0.396999 proof_verified=true
    cube000-006 verdict=UNSAT solve=0.225671 check=0.410749 proof_verified=true
    cube000-007 verdict=UNSAT solve=0.211811 check=0.400657 proof_verified=true
    cube000-008 verdict=UNSAT solve=0.228480 check=0.408609 proof_verified=true
    cube000-009 verdict=UNSAT solve=0.216210 check=0.397012 proof_verified=true
    cube000-010 verdict=UNSAT solve=0.213991 check=0.405899 proof_verified=true
    cube000-011 verdict=UNSAT solve=0.281861 check=0.403402 proof_verified=true
    cube000-012 verdict=UNSAT solve=0.271539 check=0.415550 proof_verified=true
    cube000-013 verdict=UNSAT solve=0.447820 check=0.703033 proof_verified=true
    cube000-014 verdict=UNSAT solve=0.322411 check=0.424493 proof_verified=true
    cube000-015 verdict=UNSAT solve=0.280080 check=0.408367 proof_verified=true
    cube000-016 verdict=UNSAT solve=0.279186 check=0.409203 proof_verified=true
    cube000-017 verdict=UNSAT solve=0.422256 check=0.662593 proof_verified=true
    cube000-018 verdict=UNSAT solve=0.438433 check=0.662861 proof_verified=true
    cube000-019 verdict=UNSAT solve=0.893957 check=1.188810 proof_verified=true

The sums are 6.090771 solver seconds and 9.825147 checker seconds. These children
were deliberately not extrapolated to a fleet completion time because cube difficulty can
vary with the row-2 orbit.

For (15,32), cube 3 was listed only. No depth-2 child was solved:

    nice -n 10 ~/tools/pyenv-maths/bin/python exist.py 15 32 --backend pysat --list-cubes --cube-depth 2 --cube-index 3 | ~/tools/pyenv-maths/bin/python -c "import collections,json,sys; d=json.load(sys.stdin); x=d['level2']['3']; print('verdict',d['verdict']); print('children',x['cubes']); print('stabiliser_distribution',dict(sorted(collections.Counter(x['child_stabiliser_orders']).items())))"
    verdict CUBES_LISTED
    children 5393
    stabiliser_distribution {1: 4638, 2: 674, 3: 2, 4: 64, 6: 9, 12: 6}

`aggregate-depth2.py` obtains its expected names by running that complete listing, never
from the supplied records. On the parent-specific (13,24) cube-0 JSONL the exact controls
were:

    ./aggregate-depth2.py --v 13 --b 24 --cube-index 0 scratch/depth2-aggregate-13-24-c0/cubes-13-24-depth2.jsonl
    COVERAGE PASS: 224 expected children, each appears exactly once and is verified UNSAT

    ./aggregate-depth2.py --v 13 --b 24 --cube-index 0 --mutate scratch/depth2-aggregate-13-24-c0/cubes-13-24-depth2.jsonl
    COVERAGE FAIL: 1 problem(s)
    - missing cube000-223

    ./aggregate-depth2.py --v 13 --b 24 --cube-index 0 --mutate-dup scratch/depth2-aggregate-13-24-c0/cubes-13-24-depth2.jsonl
    COVERAGE FAIL: 2 problem(s)
    - duplicated cube000-000: 2 records
    - missing cube000-223

A combined in-memory record corruption made every remaining record-integrity check fail.
This is the failing output, including rejection of a hand-written `s NOT VERIFIED` tail:

    missing cube000-000
    unexpected name worker-invented-name
    wrong verdict for worker-invented-name: 'SAT'
    unverified worker-invented-name: proof_verified is not true
    missing hash for worker-invented-name: cnf_sha256
    missing hash for worker-invented-name: proof_sha256
    unverified worker-invented-name: checker_tail lacks exact line s VERIFIED

The runbook uses contiguous worker shares, each split into four contiguous ranges. The
requested modulo assignment and four long-lived `A:B` processes cannot both be represented
by a single half-open interval per process. Contiguous shares preserve exact, disjoint
coverage and avoid thousands of Python restarts. The 67-line script records binary hashes
and versions, starts four processes, and commits only JSONLs plus the two metadata files
every ten minutes and at completion. It was syntax-checked but not run.

## 6. Summary of verdicts

| (v,b) | expected | verdict | how | solve s | check s | proof |
|---|---|---|---|---|---|---|
| (8,8) | UNSAT | UNSAT | cadical | 0.02 | 0.14 | verified, 21 KB |
| (10,13) | UNSAT | UNSAT | cadical | 0.58 | 0.57 | verified, 1.0 MB |
| (12,20) | UNSAT | UNSAT | cadical | 9.6 | 6.1 | verified, 14 MB |
| (14,27) | SAT | SAT | cadical, unhinted | 412 | 0.29 (model) | PTS + chirotope, cross-checked by chirosat.py |
| (15,31) | SAT | SAT | cadical, unhinted | 492 | 0.50 (model) | PTS + chirotope, cross-checked by chirosat.py |
| (16,37) | SAT | no verdict by search | cadical 1200 s, kissat 3600 s, pysat+phases 20 min | | | known structure satisfies the CNF (hint-cube, 2.0 s) |
| (14,28) | UNSAT | UNSAT | cadical, monolith | 1186 | 1283 | verified, 280 MB |
| (14,28) | UNSAT | UNSAT | cadical, 7 cubes | 679 total | 488 total | 7 verified proofs, 3.6 to 67 MB |
| (13,24) | open (target B) | UNSAT | cadical | 545 | 515 | verified, 218 MB |
| (13,24) | | UNSAT | kissat, same CNF | 598 | 631 | verified, 137 MB |
| (13,23) | must die (target A) | SAT at stage 2 | cadical, unhinted | 40 | 0.17 (model) | PTS + chirotope, cross-checked by chirosat.py |

## 7. WHAT WORKS

- `exist.py V B` builds the Section 9 CNF for any (v, b) whose reduction it can derive (it refuses
  the others with a reason), solves with cadical (default, proof-producing), kissat (proof-producing)
  or python-sat (no proof), verifies every UNSAT proof with drat-trim and every SAT model directly,
  and prints one JSON line with the counts, times, hashes, PTS, chirotope and leave. `--cubes`
  (depth 1 or 2) splits on the rows of points 1 and 2 with the completeness arguments of Lemmas 7
  and 7' and independent coverage self-checks; `--cube-children A:B` selects a stable half-open
  child range and appends its JSONL; `--timeout` is enforced for every backend (subprocess timeout for the
  standalone solvers, a killed forked child for pysat).
- Depth 2 was solved completely with verified proofs for (8,8), (10,13), (12,20) and
  (13,24). The targeted (14,27) child was SAT with its model checked, and the first 20
  (14,28) children were UNSAT with verified proofs. `aggregate-depth2.py` requires the
  independent listing's exact name set, one record per name, UNSAT, two hashes,
  `proof_verified: true`, and an exact `s VERIFIED` checker line.
- All four UNSAT controls and both targets above carry drat-trim-verified DRAT proofs from
  standalone cadical; (13,24) additionally from kissat; (14,28) additionally by seven cube proofs.
- Two of the three SAT controls were found by unhinted search within about 7 and 8 minutes, and
  their PTSs were re-verified by the independent stage-2 program chirosat.py. (13,23) was found in 40 s.
- Mutation controls that went red: drop the exact-b cardinality and (8,8) becomes SAT (the trivial
  three-block PTS); truncate the (8,8) proof and drat-trim says NOT VERIFIED (exit 1); drop one cube
  representative at depth 1 or depth 2 and the corresponding coverage self-check exits 2; drop or
  duplicate an aggregator record and coverage fails; a pysat budget of 0.001 s on (8,8) yields
  TIMEOUT. The anchor rank assertion caught a dependent anchor set during development.
- `make check` now also compiles exist.py and aggregate-depth2.py and runs the four (8,8)
  mutation controls, including both cube depths.

## 8. WHAT DOES NOT

- (16,37) SAT was not reached by search in the budgets tried (20 min cadical, 60 min kissat, 20 min
  pysat with the known structure as phases). Only the assumption-cube consistency check succeeded.
- The pysat backend never produces a proof, and its --timeout was a silent no-op until 08:45
  (python-sat's Cadical153 raises NotImplementedError in interrupt(), inside a timer thread where
  nobody sees it). The one run affected was the (16,37) phase-hint run, killed by hand.
- The generator lex-leader (Lemma 8) is sound but far from complete; the residual symmetry is what
  makes blocking-clause enumeration of all models impractical in this program.
- The per-cube JSONL of the (14,28) cube run lacks the cube name (key collision, fixed afterwards).
- The previous builder's partial kissat proofs for (10,13), (12,20), (14,27), (14,28), its 34 MB
  "full lex" CNF, and my own partial (16,37) proofs were deleted: none was a certificate.
- The requested checkout-level `coordination/cloud-workers` directory is outside this session's
  writable root. The sandbox rejected the direct patch, so `orchard-c3-depth2.sh` is staged in
  this directory and still needs to be copied to `coordination/cloud-workers/` at checkout level.

## 9. UNCERTAIN (work list)

- (16,37): find a SAT model by search. Untried: longer budgets, cube mode (the search inside a
  cube is smaller), kissat with --sat tuning, or a lex-leader over a better variable order.
- Enumerate all pseudoline PTS(13,23) (and (14,27), (15,31)) up to isomorphism for stage 3. Not
  done. Recommendation: the census route (pts/ enumerator, expected 8e3 PTS(13,23), then
  chirosat.py --batch at about 0.5 s each) rather than blocking clauses in exist.py, whose
  incomplete lex-leader would re-find isomorphic copies.
- Lemma 1 rests on Kelly-Moser for pseudolines (Kelly and Rottenberg 1972); a second reader should
  confirm that citation, and the stage-2 semantic bridge (chirotope on the points, zero triples =
  three-point lines) is inherited from CONTRACT Section 4, not re-derived here.
- The (13,24) verdict is over ordered fields only; Kuhne et al.'s "over any field" question stays
  open for C and finite fields.
- No (15,32) depth-2 child was solved, as required. The first 20 (14,28) children took
  only 0.21 to 0.89 solver seconds and 0.40 to 1.19 checker seconds each, but their
  difficulty may not predict cube 3 at (15,32); the fleet measurements remain uncertain.
- drat-trim at (15,32) scale: checking took about as long as solving at v = 14 (RSS under 300 MB);
  the foreign (15,32) cube-0 run's proof passed 600 MB in 52 minutes, and drat-trim has a compiled-in
  20000 s limit (its -t option raises it). Nobody has yet checked a proof of that size here.
- Whether the 383-element G2 lex of (15,32) cube 0 helps or hurts cadical is unmeasured
  (`--no-cube-lex` exists for the comparison).
- Second-solver reproduction was done for (13,24) only; (14,28) has the cube route as its
  independent second refutation; (8,8), (10,13), (12,20) have single verified proofs.

## 10. PROPOSED CONTRACT AMENDMENTS

1. Section 1, (14,27): "two points of degree 3 and twelve of degree 1" sums to 18, not 20. The
   leave types are (3,3,3,1^11), (5,3,1^12) and (7,1^13); the model found here is of the first type.
2. Section 9, symmetry break: add the reorientation anchors (v triples, never blocks under the
   canonical row, GF(2)-independent; Lemma 4) as part of the stated break, and record that a
   generator lex-leader on point 0's row stabiliser must NOT be combined with a cube split except
   under the cube's own stabiliser (Lemma 8). Record the cube counts: (14,28) 7, (13,24) 2,
   (15,32) 4 at depth 1.
3. Targets: mark (13,24) as decided at stage 2 over ordered fields (UNSAT by two solvers with two
   checked proofs; consistent with Du) and (13,23) as SAT at stage 2, so target (A)'s (13,23) half,
   like (14,27), is a stage-3 (realizability) question; the census for (13,23) is what stage 3 needs.
4. Section 8.3: for the existence route keep both solvers' proofs per target (they are one file
   each) and budget checker time equal to solver time; for (15,32)-size proofs plan for drat-trim's
   time limit and consider LRAT output from cadical for a faster checker.
5. Section 4 or 8.4 note: python-sat's CaDiCaL bindings cannot be interrupted; wall-clock budgets
   must be enforced from outside the solver (shell timeout or a child process).
6. (15,32): the four level-1 cubes are independent jobs with their own proofs; run them on
   separate workers (CONTRACT Section 6 gate order permitting), each with a proof and a drat-trim
   pass, and measure cube 0 with and without --cube-lex before committing the others.
