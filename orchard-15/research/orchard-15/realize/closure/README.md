# Census closure certificates (census_closure.py + kissat + drat-trim)

A census by `exist.py --all-models` ends with one incremental solver call that must return UNSAT
to say "no other model exists"; on 2026-09-05/06 that call ran for more than sixteen hours on the
(13,23) no-lex control. `chiro/census_closure.py` writes the same question as a standalone CNF
(the census's base encoding plus one blocking clause per found model) so that kissat can answer it
with a DRAT proof and drat-trim can check the proof. UNSAT = the census is complete.

## (13,23), lex census (441 labelled models, one class)

- closure CNF: base (lex, degree) 318,590 clauses + 441 blocking clauses; sha256 f5af3d4854f5b8afc65f1a37b260dfa6b6cc668afa58316a80774bf288d76623
- kissat 4.0.4: `s UNSATISFIABLE`, exit 20, 2026-09-06 05:59Z (started 05:25Z, nice 10, one core
  shared with two other jobs); proof 524 MB, sha256 8226d19b7ed02e5cbfc42a4b4df4a5d592c1d8c8a35c2ce5ab6bb247bf08cc5d
- drat-trim (commit 2e3b2dc0, `-t 10000000`): `s VERIFIED`, exit 0, verification time 2590.729 s, finished 2026-09-06T07:45:46Z; log kept beside the proof on the coordinator's box (the proof is not committed: 524 MB, regenerable from the CNF)

This reproduces, as a checkable certificate, the "UNSAT after enumeration" with which the lex
census itself terminated (REPORT.md, 2933 s).

## (13,23), no-lex census (184,320 labelled models): abandoned

kissat ran 10 h on the standalone closure (7,4 GB of proof by then) and was killed on
2026-09-06 19:05Z with its paused pysat closing call, for disk: the control's prediction was
already met exactly, the lex closure above is certified, and a proof of that size could not have
been checked here. Not pursued.

## (14,27): the monolithic closure failed; the cube census replaced it

The same standalone closure (sha256 e8659415..., 487,973 + 3,125 clauses) ran 14 h 50 min in
kissat on the cloud worker until the proof (26,860,388,352 bytes) exhausted the sandbox disk
(`kissat: fatal error: flushing 1048576 bytes in proof write-buffer failed`, 2026-09-07 21:08Z
(sic: 2026-09-06)), no verdict; and 13 h on the coordinator's box (13 GB) before it was killed
for the same reason. The lex-leader breaking is too weak for the closing call at this size.
The completeness certificate came instead from the census inside cube frames,
`chiro/cube_census.py`, recorded in `../cube-census-14-27/` (28,788 children, every closure
UNSAT with a drat-trim-accepted proof, 2026-09-07 06:01Z).
