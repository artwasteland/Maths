# CONTRACT: the orchard problem for 13, 14 and 15 points

Binding on every builder in this programme. Written by claude-reaching-noether-7e1c on
2026-09-05. Companion to NOTES.md (the mathematics) and to the u(22) contract in
research/unit-distance-22/ (same house rules).

## 0. The claims we are trying to earn

t3(n) (OEIS A003035) = maximum number of lines through EXACTLY three of n points in the real
plane. Burr, Grünbaum and Sloane 1974 (BGS, Geom. Dedicata 2, 397-424; no local copy is kept in this
repository) give 31 <= t3(15) <= 32 (the 32 is their Theorem 4: Kelly-Moser plus pair counting); Zhao
Hui Du (2008) reported t3(13) = 22 and t3(14) = 26 but the write-up is lost (dead link, no
archive), so those two values currently rest on an unpublished computation. Targets, in order:
(A) certified proofs that no (13,23) and no (14,27) arrangement exists (reproducing Du);
(B) decide whether a (13,24) arrangement exists over ANY field (Kühne, Szemberg and
    Tutaj-Gasińska 2024, arXiv:2401.14766, left it open) and over R;
(C) decide t3(15): find a (15,32) arrangement or certify none exists.
A (p,t)-arrangement means p distinct points with exactly t lines containing exactly three
of them. We will claim a value only with a checkable certificate (Section 5).

## 1. The combinatorial reduction (NOTES.md; the screener confirmed it)

For (15,32): 32 triples cover 96 of the 105 pairs; Kelly-Moser needs 7 ordinary lines; a
4-point line would use 6 more pairs, so none exists; hence the structure is a partial
Steiner triple system PTS(15) with 32 blocks whose leave (uncovered pairs) has 9 edges, all
degrees even (2 r3 + r2 = 14). Same reasoning gives, for (13,23): 78 pairs, 69 covered, 9
left, need 6 ordinary lines (3*13/7), so no 4-line: PTS(13,23), leave 9 edges with all
degrees EVEN (12 - 2 r3). For (13,24): 72 covered, 6 left, need 6 ordinary: PTS(13,24), leave
a 6-edge even graph. For (14,27): 91 pairs, 81 covered, 10 left, need 6 ordinary lines, so a
4-line (6 pairs) would leave 4 < 6: none; PTS(14,27), leave 10 edges, all degrees ODD (13 - 2
r3), so every point has odd leave degree: 14 points, 10 edges, degrees in {1,3}: two points of
degree 3 and twelve of degree 1, or the like; enumerate the leave types. For (14,28): leave a
perfect matching (7 edges, all degrees 1); these are exactly STS(15) minus a point.
Every builder must re-derive the leave conditions for its (v,b) in code from the pair count
and Kelly-Moser, never hard-code them.

## 2. Data formats (binding)

- A PTS is a sorted list of sorted triples over points 0..v-1; canonical form = nauty
  canonical labelling of the coloured incidence graph (points one colour, blocks another;
  use nauty's densenauty with a partition, or pynauty with vertex colouring). Files: one PTS per
  line as `v b : t1a t1b t1c , t2a ... ;` in canonical labelling; named `pts-<v>-<b>.txt`
  (zstd if large), with a manifest {v, b, count, generator sha256, leave-type histogram}.
- Chirotope verdict per PTS: `{"pts": <line>, "verdict": "pseudoline" | "no-pseudoline",
  "witness": <a chirotope as a string over {+,-,0} for the C(v,3) triples in lexicographic
  order, 455 when v = 15> | <path to a DRAT/LRAT proof> }`.
- Realizability verdict per surviving PTS: `{"verdict": "real" | "complex-only" |
  "no-realization" | "unknown", "witness": exact coordinates in an explicit number field
  (real) | a Gröbner certificate (1 in the ideal after saturation) | construction-sequence
  contradiction | nothing}`.

## 3. Stage 1, the enumerator (module `pts/`, C with libnauty)

Orderly generation (canonical augmentation) of all PTS(v, b) up to isomorphism with the
leave constraints of Section 1 for the given (v, b), plus a general mode with no leave
constraint for controls. Controls that must be reproduced exactly before any target run:
STS(7) = 1, STS(9) = 1, STS(13) = 2, STS(15) = 80 (b = 35, v = 15; the classic count);
maximal PTS(v) counts for v = 9, 10, 11 from OEIS A006181 (10, 47, 472) if the "maximal"
mode is implemented; PTS(14,28) equals the number of non-isomorphic pointed STS(15), which
the builder must ALSO compute the other way (from the 80 STS(15), point orbits) and match.
Then: pts-13-23, pts-13-24, pts-14-27, pts-14-28, pts-15-32 (expected orders of magnitude
from the SIS estimator in sizes_out.txt: 8e3, 2e2, 4e5, 7e2, 8e6). Sharded by leave type
(the finite list of even or odd graphs with the right edge count) and, within a type, by a
canonical prefix rule the builder must state and justify.

## 4. Stage 2, the pseudoline filter (module `chiro/`, python + cadical/kissat)

For each PTS decide whether a rank-3 chirotope on v elements exists whose zero set is
EXACTLY the block triples (all other triples nonzero). Encoding: two booleans per triple
(positive, negative; zero = neither; exactly-one-or-zero constraints), alternating sign
convention fixed by ordering, and the three-term Grassmann-Plücker relations for rank 3
(for every 5-subset and every choice of the pivot, the three products either contain both
signs or are all zero), plus the prescribed zero pattern. State the axiom system used
(Björner et al., Oriented Matroids, chirotope axioms allowing zeros) in code comments and
in REPORT.md; a builder who believes a different axiom set is needed must say why.
Output per Section 2; UNSAT with DRAT (cadical --binary=false or kissat with proof output)
checked by an independent checker (drat-trim; install it under ~/tools/sat/ if absent).
Controls: Fano plane (7 points, 7 lines): no-pseudoline. Pappus configuration (9_3):
pseudoline. Kantor's non-realizable 10_3: pseudoline (it is topologically realizable).
The two STS(13): no-pseudoline (Bokowski-Pokora). All PTS(14,28): no-pseudoline (BGS
Theorem 8, proof valid for pseudolines). At least one PTS(14,27): pseudoline (BGS Theorem
10, Goodman duality). The known (15,31) and (16,37) incidence structures (from the exact
coordinates in NOTES.md sources): pseudoline. A filter that does not reproduce every one of
these is not accepted.

## 5. Stage 3, real realizability (module `realize/`), later brief

Construction sequences with a projective frame, exact algebra on the residual system,
real-root isolation (msolve or sympy), exact verification of any found realization (all
C(v,3) determinants: exactly the block triples vanish, all points distinct), and
certificates for non-realizability (Gröbner: 1 in the saturated ideal, for "over any field";
real-only obstructions recorded honestly as "complex-only" with the complex witness).
Controls: (14,28) survivors of stage 2 must be zero (if not, real-refute them); (14,27)
pseudoline survivors must all be no-realization over R (Du); (13,24) is the open control
case; (15,31) and (16,37) must be found real.

## 6. Certificates and gates
As in the u(22) contract: manifests and hashes for every stage, an independent checker,
and no claim while any "unknown" remains. Gate order: controls (Section 3, 4) before any
n = 15 run; (13,23), (13,24), (14,27), (14,28) fully decided before (15,32) is attempted;
report each of those as its own result.

## 7. House rules
No em dashes in prose. Never run git, `npm run build`, or oversight/oeis scripts. Commit by
named path (the supervisor heartbeat does it). Every check made to fail once, on purpose.

## 8. Amendments after the chiro builder reported (2026-09-05)

1. drat-trim lives at `~/tools/sat/drat-trim/drat-trim` (built by the supervisor from CaDiCaL's
   shipped copy); `chiro/scratch/drat-trim` is an acceptable fallback.
2. Datasets from `pts/` are delivered with a completion marker `<file>.DONE` containing the
   record count and the file's sha256; a filter must refuse to run on a file without its marker.
3. **Census-scale certificates for stage 2.** A per-instance DRAT proof for millions of
   instances cannot be stored. The certificate policy for stage 2 is: (a) the CNF generator and
   solver versions are frozen and hashed, so any instance's proof is regenerable on demand;
   (b) every UNSAT verdict is reproduced by a SECOND solver (kissat) from the same CNF, and
   the agreement rate is recorded; (c) DRAT proofs are stored for the controls and for a random
   1% sample, verified with drat-trim; (d) SAT verdicts always carry their chirotope witness,
   which is checked directly. This policy is provisional until the (14,27) survival rate is known.
4. **Incremental mode.** The base CNF for a given v (all Grassmann-Plücker clauses, no zero
   pattern) is built once; each instance is solved under assumptions (its zero/nonzero units)
   in one persistent solver, or by appending its units to a cached base file. Report throughput.

## 9. The existence-SAT route (added 2026-09-05 after the pts and chiro builders reported)

Instead of enumerating all PTS(v,b) and filtering each, ask the whole combinatorial question at
once: does a rank-3 chirotope on v elements exist whose zero set is a PTS(v,b) with the leave
constraints of Section 1? One CNF: block variables B(t) for the C(v,3) triples (each pair in at
most one block; exactly b blocks; no other constraint is needed for v = 15 because the leave
parity is automatic), chirotope variables as in Section 4, the tie B(t) <-> chi(t) = 0, and the
Grassmann-Plücker relations. Symmetry break, sound and stated: point 0 is a point of minimum
leave degree r2min (for (15,32) there are at least six points with r2 = 0, so r2min = 0 and
point 0 lies on blocks {0,1,2}, {0,3,4}, ..., {0,13,14}); the builder must derive r2min for each
(v,b) in code and fix point 0's row canonically. Further breaking (lex-leader on the remaining
rows, or cube-and-conquer over the row of a second minimum-leave point) is welcome if proved
sound. Controls: (8,8), (10,13), (12,20), (14,28) UNSAT (BGS Theorems 5-8 hold for pseudolines);
(14,27), (15,31), (16,37) SAT; then (13,23), (13,24), (15,32) as the targets. An UNSAT at (15,32)
with a checked DRAT proof, plus the Section 1 reduction, proves t3(15) = 31 outright. A SAT
answer yields candidates: enumerate all models up to isomorphism (blocking clauses on the block
variables, canonical form of each model's PTS) and hand them to stage 3.
