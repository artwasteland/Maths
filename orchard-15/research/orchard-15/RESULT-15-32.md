# The fifteen-tree orchard: t3(15) = 31

Status line, kept current by the coordinator claude-reaching-noether-7e1c: **A RESULT.** Every row
of `chiro/AUDIT-15-32.md` reads UNSAT with a drat-trim-verified proof (cube 3's since 09:05Z on
2026-09-05), so the theorem in Section 1 is proved. What remains in progress is redundancy, not
proof: all four cubes carry LRAT certificates accepted by the formally verified checker cake_lpr
(cube 3's since 15:54Z), cube 3 is additionally covered by its complete 5393-child depth-2
certification, and cube 3's cadical proof was verified by drat-trim on 2026-09-06 at 06:01Z
(45,331 s), so every redundancy item in Section 3 is complete. Section
6 says what would have happened had any cube been SAT; none was.

## 1. The claim

Let t3(n) be the maximum number of lines containing exactly three of n points in the real
plane (OEIS A003035; the orchard problem). Burr, Grünbaum and Sloane (1974) proved
31 <= t3(15) <= 32 and the value has stood open since: Sloane's 2013 comment on A003035 reads
"31 or 32", Friedman's table says the same, and the sporadic cases where the formula
floor(n(n-3)/6) + 1 is beaten are n = 7, 11, 16 and 19 only. The Green-Tao theorem (2013)
settles the orchard problem for all sufficiently large n and says nothing about n = 15.

**Theorem.** No configuration of 15 points in the real plane has 32 lines
through exactly three points. Hence t3(15) = 31, the value of the formula; 15 is not sporadic.

The lower bound is the known 31-line configuration (the 31 zero-sum triples of Z/15 on a
cubic; Pegg 2018), which is realised exactly by `chiro/exist.py 15 31` (SAT, model checked)
and by the classical construction; it is not part of what is new here.

What is actually proved is stronger than the theorem: **no rank-3 chirotope on 15 elements
has a partial Steiner triple system with 32 blocks as its set of collinear triples.** That is
the pseudoline statement: no arrangement of 15 points and pseudolines has 32 three-point
pseudolines either. Real lines are a special case of pseudolines, so the theorem follows.

## 2. The reduction to a finite SAT question

1. **Counting (Lemma 1 in `chiro/REPORT-EXIST.md`, from BGS Theorem 4).** A (15,32)
   arrangement's 32 three-point lines cover 96 of the 105 point pairs. Kelly-Moser gives at
   least ceil(3*15/7) = 7 ordinary (two-point) lines. A line through four or more points
   would use at least six pairs, leaving at most three for ordinary lines, contradiction. So
   every uncovered pair is an ordinary line and the incidence structure is a partial Steiner
   triple system PTS(15) with 32 blocks whose leave (uncovered pairs) has 9 edges and all
   degrees even (2 r3 + r2 = 14 at every point). The Kelly-Moser theorem holds for
   pseudoline arrangements (Kelly and Rottenberg 1972), so the reduction is pseudoline-valid.
2. **Chirotopes.** A configuration of 15 points in general or special position in the real
   plane determines a rank-3 chirotope on 15 elements (the signs of the 455 orientation
   determinants), and the collinear triples are exactly its zero set. Every rank-3 chirotope
   corresponds to an arrangement of pseudolines (Folkman-Lawrence). So if no rank-3 chirotope
   has a PTS(15,32) zero set, no such point configuration exists, real or pseudoline.
3. **The CNF (`chiro/exist.py`, CONTRACT Section 9).** Variables: one sign variable per
   triple and one block variable per triple (block = collinear), with the three-term
   Grassmann-Plücker relations on every 5-subset, the tie clauses (zero exactly on blocks),
   the pair clauses (every pair in at most one block), exact-b cardinality, the degree
   clauses from Lemma 9, and the symmetry break: point 0's row is fixed to its canonical
   form (Lemma 3), sign anchors kill the reorientation group (Lemma 4), and, in the monolithic
   CNF only, lex-leader clauses for the 13 generators of G0 = Z2 wr S7 (order 645120; Lemma 8,
   sound but not complete). The four cube CNFs that constitute the certificate carry NO G0 or
   G1 lex-leader (Lemma 8 shows that combination would be unsound with a cube split); each
   carries instead a lex-leader for every non-identity element of G2 = Stab_G1(row 1), as
   item 4 says.
4. **Cube-and-conquer (Lemma 7).** The row of a second minimum-leave point, point 1, is
   split into its 4 orbits under G1 (orbit sizes 120, 1440, 640, 3840; stabilisers of order
   384, 32, 72, 12). Lemma 7 proves the four cubes exhaust the search space; each cube's CNF
   carries its own lex-leader clauses for its stabiliser G2. All four cubes UNSAT, together
   with Lemmas 1 to 9, is the statement in Section 1.

The lemmas were attacked by a five-referee panel on 2026-09-05 (workflow `wf_2467b810-260`)
and held; the panel's findings were about the certificate protocol, which is Section 3.

## 3. The certificate (what a sceptic can check)

Every row below must be filled from `chiro/AUDIT-15-32.md` before this file is a result.

| cube | orbit | |G2| | CNF sha256 | vars / clauses | solver | proof bytes | proof sha256 | checker |
|---|---|---|---|---|---|---|---|---|
| 0 | 120 | 384 | 0e6352aa... | 262,585 / 1,521,924 | cadical 1.7.3 (local and cloud) | 696,022,996 | 9a09e2c3... | drat-trim `s VERIFIED` twice (3432 s local, 2353 s cloud) |
| 1 | 1440 | 32 | 8c33bbfe... | 138,233 / 777,572 | cadical 1.7.3 (cloud), 4481 s; kissat 4.0.4 (cloud), 1924 s | 2,455,730,413 (cadical); 933,086,904 (kissat) | 958c8adf... (cadical); 6c4239bf... (kissat) | drat-trim `s VERIFIED` on both: 7628 s and 3520 s |
| 2 | 640 | 72 | 9b26b0e5... | 152,713 / 864,252 | cadical 1.7.3 (cloud), 5065 s; kissat 4.0.4 (cloud), 1810 s | 2,010,793,854 (cadical); 770,721,286 (kissat) | 137d0fab... (cadical); 94c7a88d... (kissat) | drat-trim `s VERIFIED` on both: 7766 s and 3366 s |
| 3 | 3840 | 12 | 3ce6b8b9... | 131,725 / 738,624 | kissat 4.0.4 (cloud), 7198 s; cadical 1.7.3 (cloud), ~5 h | 3,716,998,324 (kissat); 8,980,523,963 (cadical) | a4bf1e90... (kissat); cadical proof verified 2026-09-06 | drat-trim `s VERIFIED` on the kissat proof (16,289 s, 09:05Z) and on the cadical proof (45,332 s on the second pass with the compiled limit lifted, 06:01Z 2026-09-06) |

How the columns were earned:

- **The CNF is the intended cube CNF, not merely "a file drat-trim refuted".** Each cube CNF
  was regenerated from the frozen generator on an unrelated cloud worker
  (`claude/reaching-noether-cloud-cnf-audit`) and on this machine; the sha256 of the file
  each solver actually refuted equals the regenerated one, byte for byte, for all four cubes
  (six worker files across five branches). `chiro/cnfcheck.py` decodes each file and checks
  the anchors, block units, the prefix-equal starts (one per non-identity element of G2)
  and, by 25 random trials per cube, that the lex-leader clauses accept G2-orbit minima and
  reject non-minima.
- **The proof certifies the CNF.** drat-trim (marijnheule/drat-trim at commit 2e3b2dc0, binary
  sha256 recorded) was run with `-t 10000000` so its compiled 40000 s limit (TIMEOUT in drat-trim.c at that commit) cannot produce a
  silent `s TIMEOUT`; only an exact `s VERIFIED` line with exit 0 is accepted; the checker's
  log is committed next to the verdict. The proofs themselves (0.7 to 3.4 GB) stay on the
  workers' disks and are regenerable from the CNF and the solver version.
- **Independence, exactly.** Cube 0: one cadical proof, byte-identical on the coordinator's box
  and on a cloud worker, checked twice by two different drat-trim builds (the 2017 CaDiCaL-shipped
  copy, binary sha256 993de410..., locally; commit 2e3b2dc0, binary 92f0aa95..., on the cloud).
  Cubes 1 and 2: a cadical proof and a kissat proof each, from different cloud workers, each
  checked once by drat-trim 2e3b2dc0. Cube 3: a kissat proof checked once by drat-trim 2e3b2dc0,
  self-reported by the worker that produced it; its cadical proof (a second worker) is still in
  drat-trim; the depth-2 split (5393 children, each with its own cadical proof checked by
  drat-trim, coverage verified exactly once each, 14:45Z) is a complete third certification of
  cube 3 by a structurally different case split; and four fresh workers are re-solving every cube with kissat, emitting
  LRAT with drat-trim -L and checking it with the formally verified checker cake_lpr (the referee
  panel of 10:00Z asked for both; the ledger records their outcome). First result: cube 0's
  fresh kissat proof, checked by drat-trim (1530 s) and its 1.07 GB LRAT checked by cake_lpr
  (`s VERIFIED UNSAT`, exit 0, 63 s), on a machine that produced none of the earlier proofs.
  Cubes 1 and 2 followed at 12:20Z and 12:22Z, each `s VERIFIED UNSAT` with exit 0, and in
  both cases the fresh kissat proof was byte-identical to the proof the earlier worker had
  produced, so the verified checker certified the very bytes drat-trim had already accepted.
  Cube 3's fresh proof is likewise byte-identical to the earlier one; its 16.06 GB LRAT was
  accepted by cake_lpr (`s VERIFIED UNSAT`, exit 0) at 15:54Z, after drat-trim -L had taken 13,462 s;
  the worker's disk guard unlinked the DRAT file after that check completed, so the run's JSONL
  record was assembled by the worker rather than emitted by exist.py (its INCIDENT file says
  exactly what was and was not lost: nothing that the certificate rests on).
- **Reproduction.** `python3 chiro/exist.py 15 32 --backend cadical --cubes --cube-index k
  --drat-trim <path>` regenerates and solves cube k (26 min for cube 0 on a 4-core cloud
  worker; cube 3 is the largest). `chiro/cnfcheck.py <cnf> --v 15 --b 32 --cube k` audits
  the file.

**Independent check of the cube split (2026-09-06, GAP 4.12.1, `chiro/independent/`).** A reader
objected, correctly, that a wrong orbit decomposition would make every downstream checker say
VERIFIED of the wrong formula. Built from the definition alone, GAP finds the stabiliser of the
row-0 partition to have order 46,080, the row-1 configurations to number 6,040, their orbits to
be exactly four, of sizes 120, 1440, 640 and 3840, the four fixed representatives to be a
transversal (stabilisers of order 384, 32, 72, 12), and each cube's lex-leader group, dumped from
the generator element by element, to be identical to GAP's stabiliser. The same holds for the
(14,27) frame (seven orbits, 120, 160, 960, 640, 480, 384, 3840). The check does not cover the
encoding of the lex-leader clauses themselves or the sign-anchor part of Lemma 8; see the README.

## 3b. Below fifteen: t3(13) = 22 certified (stage 3, 2026-09-05 14:55Z; the no-lex census control
agreed at 19:35Z: `realize/nolex/PREDICTION.md`)

Du's t3(13) = 22 (2008, write-up lost) rests on showing that no 13-point configuration has 23
three-point lines. Section 1's reduction puts any such configuration's collinear triples in a
PTS(13,23) with a 9-edge even leave; a real configuration gives a rank-3 chirotope with that
zero set, so the candidates are the pseudoline-admitting PTS(13,23). `chiro/exist.py
--all-models` (blocking clauses on the block variables over the canonical-row relabellings
that obey the lex leaders, pysat incremental) enumerated 441 labelled models in 2933 s, which
nauty (`realize/canonicalize.py`) collapses to ONE isomorphism class
(`realize/pts-13-23-pseudoline.txt`, sha256 bd30d3d2...); chirosat.py re-verifies it as
pseudoline; the same loop at (13,24) and (14,28) returns 0 models at once (both UNSAT), and the
class contains the model found on 2026-09-05 03:xxZ. Stage 3 (`realize/realize.py`,
`realize/check_realization.py`, blind, recomputing from the PTS alone): the class is NOT
realizable in characteristic 0, the ideal of its 23 collinearity conditions after a projective
frame and Rabinowitsch saturation by all 263 non-block determinants having reduced Groebner
basis {1}; controls Fano (no realization), Pappus and Desargues (real, rational coordinates),
the non-realizable 10_3 (no realization), Pegg's (15,31) (real, coordinates in Q(alpha),
455 determinants checked) and the Burr-Grünbaum-Sloane (14,27) arrangement (no realization
in characteristic 0, their Theorem 10 by machine) all as required; a changed coordinate and a
dropped ideal block are rejected. An independent re-implementation (`realize/independent/`,
sympy only, no shared code, two disjoint frames) reproduces the verdict and sharpens the
certificate: the block ideal alone has a reduced basis of 17 linear forms (every solution puts
eight points on one line with six coincident), the non-block triple (0,3,4) is forced collinear,
and explicit cofactor identities 1 - y4 = sum a_k det_k (integer form with constant 4) and, in
the second frame, det(0,1,2)^2 = sum a_k det_k (constant 9) are verified by plain expansion;
since gcd(4, 9) = 1 the structure has no realization over any field of any characteristic.
The control predicted in `realize/nolex/PREDICTION.md` before the run ended was met exactly: the
census without symmetry breaking (`exist.py 13 23 --no-lex --all-models`) found 184,320 labelled
models, all distinct, every one canonicalising to the single class (4 leave-free points times
|Z2 wr S6| = 46,080, divided by a trivial automorphism group). Hence no real (13,23) arrangement exists, and with the known (13,22) construction,
**t3(13) = 22**. What remains before this is stated unconditionally: the census re-run
without the lex-leader (`realize/nolex/`) must canonicalise to the same single class.
(14,27), the same route to t3(14) = 26, is the next brief.

## 3c. Fourteen: t3(14) = 26, pending one certificate (2026-09-06 10:40Z)

The same route at (14,27), the last orchard value that rested on Du's lost computation. The lex
census `exist.py 14 27 --all-models --timeout 36000` (worker branch
`claude/reaching-noether-cloud-orchard-14-27`, `realize/REPORT-14-27.md`) found 3,125 labelled
models in its first 25 minutes and then spent 9 h 35 min on one solver call before its cap killed
it, exactly the shape of the closing call that the (13,23) censuses showed. nauty collapses the
3,125 to **8 isomorphism classes** (`realize/pts-14-27-pseudoline.txt`, all with leave type
1^11 3^3), and `realize/realize.py` refutes **all 8 over R**, Groebner basis {1} after saturation,
with `check_batch.py` accepting all 8 certificates (`realize/verdicts-14-27.jsonl`,
`realize/checks-14-27.jsonl`). Nothing came out `real` or `unknown`.

What is NOT yet established is that the 8 classes are all of them. The closure certificate of
`chiro/census_closure.py` (the census CNF plus one blocking clause per found model, sha256
e8659415..., 487,973 + 3,125 clauses) is being refuted by kissat on the worker and on the
coordinator's box; `s UNSATISFIABLE` checked by drat-trim would certify the census complete and
hence **t3(14) = 26** by machine; `s SATISFIABLE` would hand back a missing model and the census
would continue from it. Until that returns, t3(14) = 26 remains Du's value with eight of its
cases certified and its completeness open.

## 4. Controls (all in `chiro/REPORT-EXIST.md`, same encoder, same lemmas)

| (v,b) | expected | got | why it matters |
|---|---|---|---|
| (8,8), (10,13), (12,20) | UNSAT (BGS Theorems 5-7, pseudoline proofs) | UNSAT, proofs verified | the encoder reproduces BGS by machine |
| (14,28) | UNSAT (BGS Theorem 8, proof never printed) | UNSAT, 280 MB proof verified; again by 7 cubes | the first checkable proof of Theorem 8 |
| (14,27) | SAT as pseudolines (BGS Theorem 10) but t3(14) = 26 | SAT, model checked | the pipeline does not over-prove: it finds the pseudoline arrangement that is not stretchable |
| (15,31) | SAT (the known orchard) | SAT, model checked | the target's neighbour is found |
| (16,37) | SAT (BGS Theorem 2) | SAT with a hint cube; search alone times out | honest limit of unhinted search |
| (13,24) | open over R (KST 2024) | UNSAT, proofs by cadical and kissat verified | new: no (13,24) pseudoline arrangement, hence none over R |

A SAT verdict at (14,27) shows only that the encoding's model set is non-empty; it cannot detect
an encoder that rejects every REAL chirotope while admitting some spurious sign vector, which is
the one failure that would make the four (15,32) UNSATs vacuous (every other control here is a
solver-found model checked by a verifier that shares the encoder's sign convention). The control
that tests that direction is `chiro/controls/pegg_e2e.py`, written by the referee panel of
10:00Z and adopted: the chirotope of Pegg's real (15,31) configuration, computed from exact
coordinates on the acnodal cubic, is pushed through the identical Lemma 3/4/7/8 machinery into
its depth-1 cube and evaluated against every clause of the monolithic (15,31) CNF (727,103
clauses) and of its cube CNF (862,684 clauses, cube 2, |G2| = 72): zero clauses falsified in
both, and flipping one sign falsifies 370. So the encoding is a relaxation of reality, not an
over-approximation, and an UNSAT refutes the real configurations too.

## 5. What is and is not claimed

- Claimed (Section 3 now has a verified refutation for every cube; cube 3's second proof and the depth-2 certification are still running): t3(15) = 31 over the reals, and the pseudoline
  statement of Section 1.
- Also new, unconditional now: no (13,24) pseudoline arrangement exists, so t3(13) <= 23 by a
  checkable certificate; Kühne, Szemberg and Tutaj-Gasińska's question over other fields
  (complex, finite) stays open, because chirotopes see only ordered fields.
- Not claimed: Zhao Hui Du's values t3(13) = 22 and t3(14) = 26 (2008, write-up lost) are not
  reproduced here. (13,23) is SAT at the chirotope level (a pseudoline (13,23) arrangement
  exists), so deciding it needs the realizability stage, exactly as (14,27) does.
- Not claimed: anything about Erdős problem #669 beyond its n = 15 instance, and nothing about
  the formula's sporadic exceptions beyond "15 is not one".

## 6. If a cube is SAT

A satisfying assignment is a rank-3 chirotope with a PTS(15,32) zero set, i.e. a pseudoline
(15,32) arrangement. That alone would already contradict nothing known (BGS's bound is for
pseudolines too, so it would be a new pseudoline orchard), and t3(15) = 32 would then need a
real realisation: the `realize/` stage (numerical solving, exact reconstruction, checker), with
non-realizability certified by a final polynomial. The model is checked by chirosat.py and
committed as the witness before anything else is done.

## 7. Provenance

Coordinator: claude-reaching-noether-7e1c (Claude Fable 5.1), 2026-09-04/05, with cloud
workers (Opus 5) for the cube solves, a five-referee pre-validation panel, and codex builders
for `chiro/` and `pts/`. Sources: BGS 1974 (Geom. Dedicata 2, 397-424); Kelly and Rottenberg
1972; Folkman and Lawrence 1978; Green and Tao 2013; Kühne, Szemberg and Tutaj-Gasińska
arXiv:2401.14766; OEIS A003035. The DRAT proofs are not in git; the CNF hashes, decode
audits, solver and checker binaries' hashes, and checker logs are.
