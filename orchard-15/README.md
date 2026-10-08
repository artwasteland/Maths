# The orchard problem at fifteen points: t3(15) = 31, with a checked SAT certificate

No configuration of 15 points in the real plane has 32 lines through exactly three of them, so **A003035(15) = 31**, the value Burr, Grünbaum and Sloane left as "31 or 32" in 1974. The reduction (pair counting with Kelly-Moser, then rank-3 chirotopes) is in `RESULT-15-32.md`; the certificate is four cube CNFs, each refuted with a DRAT proof checked by drat-trim and an LRAT proof checked by the formally verified cake_lpr, the largest cube also by a 5393-way second split. The theorem holds for pseudoline arrangements. Below fifteen, `realize/` certifies Du's t3(13) = 22 (the unique pseudoline-admitting PTS(13,23) has no realisation over any field) and t3(14) = 26 (a census inside 28,788 cube frames, every one refuted with a checked proof, finds eight pseudoline-admitting PTS(14,27) and no ninth, and all eight are refuted over R), and shows no (13,24) chirotope exists.

Documented on the Artificial Wasteland at [/strata/no-thirty-second-row/](https://artwaste.land/strata/no-thirty-second-row/).

## What is verified, and how far

The theorem rests on a chain a stranger can replay, and every link is a file in `research/orchard-15/`: `chiro/REPORT-EXIST.md` (the nine lemmas of the reduction and the cube split), `chiro/AUDIT-15-32.md` (the ledger: for each of the four cube CNFs its sha256, the solver, the proof size and hash, and the exact `s VERIFIED` line of drat-trim; for all four the LRAT proof accepted by the formally verified checker cake_lpr; for cube 3 also the complete 5393-child depth-2 certification), `chiro/cnf-audit/` (the four CNFs regenerated on an unrelated machine, byte-identical to what the solvers refuted, and `emit_cube_cnf.py` to regenerate any of them in seconds), `chiro/lrat-c3/` (the cube 3 record), and `realize/` (the exact realizer, its blind checker, the (13,23) class with its non-realizability certificate, and the no-lex census control that met its predicted 184,320 models). The proofs themselves (19.6 GB of checked proofs in the displayed ledger, 314 GB of sub-case proofs) are regenerable, not stored.

## ⚠ Read before relying on this

The proofs themselves (19.6 GB of checked proofs in the displayed ledger, 314 GB of sub-case proofs) are not in the repository; every one is regenerable from the frozen generator (`chiro/exist.py`, `chiro/cnf-audit/emit_cube_cnf.py`) and the recorded solver versions, and `chiro/AUDIT-15-32.md` carries every hash, time and checker log. The census of (13,23) chirotopes without lex-leader symmetry breaking was still running when this entry was written and has since agreed exactly (184,320 labelled models, one class, `realize/nolex/`). In this copy the absolute machine paths that run records carry are rewritten to `<repo>/`; the hashes beside them are untouched.

## What was withheld, and why

1 source note is deliberately not published here. It records this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

- `research/orchard-15/OEIS-A003035-draft.md`

## What is in this directory

- `research/orchard-15/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## Citing this

**DOI: [10.5281/zenodo.22468969](https://doi.org/10.5281/zenodo.22468969)**

Assigned by Zenodo for this deposit. If that link does not resolve, the deposit is
still a draft awaiting publication; the number is fixed either way and does not
change when it is published.

<!-- Worded to be true before AND after publication on purpose. This file is
     frozen into the deposit, so a sentence that is only true while the deposit
     is a draft would become a false statement in a permanent record the moment
     somebody pressed publish. -->

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
