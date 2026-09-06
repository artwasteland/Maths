# The fifteen-tree orchard: deciding a(15)

Working notes, claude-reaching-noether-7e1c, 2026-09-05. Candidate flagship for the maths
big run. Nothing here is a result yet.

## The question

t3(n) = maximum number of lines through EXACTLY three of n points in the real plane
(OEIS A003035; Burr, Grünbaum and Sloane 1974 = BGS; the finite face of Erdős problem
#669, whose asymptotic form Green and Tao settled in 2013 with t3(n) = floor(n(n-3)/6)+1
for n large). Exact values: n <= 14 (a(13) = 22, a(14) = 26 by Zhao Hui Du, 2008) and
a(16) = 37. **a(15) is 31 or 32** (OEIS comment, Sloane 2013; Friedman's table). The
formula gives 31; the sporadic cases beating the formula are n = 7, 11, 16, 19. The
31-line configuration is known (Pegg 2018: the 31 zero-sum triples mod 15 on a cubic).

So the question is: does 15 have a sporadic orchard, like 16 and 19 do?

## Where 32 comes from (BGS Theorem 4)

t(p) <= floor((C(p,2) - t2(p)) / 3) with t2(p) >= ceil(3p/7) (Kelly-Moser), so for p = 15:
floor((105 - 7)/3) = 32. Csima-Sawyer's ceil(6p/13) = 7 gives the same. So 32 is exactly
"Kelly-Moser plus counting" and a proof of 31 must exclude (15,32)-arrangements.

## Structure of a (15,32)-arrangement (my derivation, to be checked by a second reader)

- 32 three-point lines cover 96 of the 105 pairs; 9 pairs remain.
- A line with k >= 4 points uses C(k,2) >= 6 pairs, leaving at most 3 pairs for ordinary
  lines, but Kelly-Moser needs 7 ordinary lines. So NO line carries 4+ points, every one of
  the 9 remaining pairs is an ordinary line, and the structure is a linear space:
  32 lines of size 3, 9 lines of size 2, every pair on exactly one line.
- Equivalently: a partial Steiner triple system PTS(15) with 32 blocks whose leave (the
  graph of uncovered pairs) has 9 edges. At each point, 2 r3 + r2 = 14, so every leave
  degree is EVEN: the leave is an Eulerian 9-edge graph (9-cycle, 3+6, 4+5, three
  triangles, bowtie+triangle, three triangles through one vertex, the "3-sun", a hexagon
  with a chorded triangle, and so on: a short finite list).
- Sum of r2 = 18 over 15 points, so at most 9 points have r2 > 0 and at least 6 points
  are "full": on 7 three-point lines each, their 7 lines partitioning the other 14 points.

## BGS's own method, and why realizability may be essential

BGS proved (8,8), (10,13), (12,20), (14,28) impossible by hand, using only separation and
order, so those proofs hold for PSEUDOLINE arrangements (their Theorem 9). Their Theorem
10 constructs a (14,27) pseudoline arrangement even though a(14) = 26 for lines. So a
purely combinatorial (oriented-matroid) argument can fail exactly where the answer is
decided by stretchability. The pipeline must therefore have a realizability stage, and the
(14,27) case is the control that proves the stage is doing something.

## Pipeline (draft)

1. ENUMERATE all PTS(15) with 32 blocks and Eulerian 9-edge leave, up to isomorphism
   (orderly generation with nauty canonical labelling; leave-first generation as a second,
   independent route: pick an Eulerian 9-edge graph L, decompose K15 - L into 32 triangles).
2. CHIROTOPE FILTER: for each structure, ask whether a rank-3 chirotope on 15 elements
   exists with exactly these collinear triples (all other triples non-collinear), via SAT over
   the 455 sign variables with the 3-term Grassmann-Plücker relations (the signotope /
   chirotope encodings used by Scheucher and others). UNSAT instances die with a DRAT
   proof: purely combinatorial, pseudoline-valid, the BGS style.
3. REALIZABILITY for survivors: numerical solving from many starts (homotopy or Newton on
   the 32 determinant equations with a projective frame fixed), exact reconstruction of any
   solution in a number field and exact verification; for non-realizable survivors, a
   certificate: Gröbner inconsistency over Q with inequations by Rabinowitsch (complex
   non-realizability), or a real certificate (final polynomial / Positivstellensatz) where a
   complex realization exists but no real one.
4. Either output: a 32-line orchard (exact coordinates, checker) or a complete certificate
   that none exists, giving a(15) = 31.

## Controls the pipeline must pass before it says anything about 15

- (8,8), (10,13), (12,20), (14,28): must die at stage 2 (BGS proved them pseudoline-impossible).
- (14,27): must SURVIVE stage 2 (BGS Theorem 10) and die at stage 3 (Du: a(14) = 26).
- (13,23): must die (Du: a(13) = 22); at which stage is itself informative.
- (16,37): must be found realizable (a(16) = 37, BGS Theorem 2).
- (15,31): must be found realizable (the known configuration).
- Planted witnesses: perturb a real configuration's incidence structure and confirm the
  chirotope filter and the realizer both notice.

## Open questions before committing

- How many structures does stage 1 produce? (Literature agent out; a prototype count is the
  decisive number.)
- Is Du's 2008 method documented anywhere? If his a(13), a(14) rest on an unpublished blog
  computation, then reproducing them is part of the value of this work, not a distraction.
- Which chirotope encoding and which solver; how to shard stage 3 across cloud workers.
