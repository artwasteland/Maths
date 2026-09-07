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

## (13,23), no-lex census (184,320 labelled models) and (14,27)

Running at the time of writing; recorded here when they return.
