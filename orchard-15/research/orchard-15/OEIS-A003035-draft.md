# Proposed edit to OEIS A003035 (orchard problem, 3-tree rows), for a mathematician's review

Drafted 2026-09-06 by claude-reaching-noether-7e1c. Not submitted. House rule: an OEIS edit goes
out only after a mathematician has read it and the certificate; Liam decides when.

## The entry today (fetched 2026-09-06, fmt=json)

- Name: Maximal number of 3-tree rows in n-tree orchard problem.
- Offset 1. Data: 0, 0, 1, 1, 2, 4, 6, 7, 10, 12, 16, 19, 22, 26 (that is a(1) to a(14)).
- Comment (N. J. A. Sloane, Feb 11 2013): "It is known that a(15) is 31 or 32, a(16)=37 and
  a(17) is 40, 41 or 42."
- Links include Burr-Grünbaum-Sloane 1974, Friedman's table, Green-Tao, Pegg's 2018 blog and four
  illustrations (one showing a(15) >= 31 with coordinates in Q(sqrt 3); one showing a(16) = 37),
  and Zhao Hui Du's 2008 blog (dead link).

## What we can now add

1. **a(15) = 31.** Proved 2026-09-05: no configuration of 15 points in the real plane has 32
   lines through exactly three of them (research/orchard-15/RESULT-15-32.md). Method: the
   pair-counting reduction of BGS Theorem 4 plus Kelly-Moser puts the 32 lines in a partial
   Steiner triple system with a 9-edge even leave; the chirotope axioms turn any real (or
   pseudoline) configuration into a rank-3 chirotope whose zero set is that PTS; the resulting
   CNF, split into four cubes by symmetry, is UNSAT, each cube's DRAT proof checked by drat-trim
   and each cube's LRAT proof by the formally verified checker cake_lpr. The theorem holds for
   pseudoline arrangements as well.
2. **The data can extend to a(16) = 37**, which the entry's own comment already states as known
   (BGS 1974, Table; the pair-count ceiling floor((120 - 7)/3) = 37 is achieved by the known
   16-point configuration, illustrated on the entry). It could not be listed while a(15) was open.
3. **a(13) = 22 now has a certificate.** Du's 2008 value rested on a lost computation. The
   pseudoline-admitting PTS(13,23) is unique up to isomorphism and is not realizable over any
   field (Gröbner certificate plus explicit cofactor identities; research/orchard-15/realize/).
   No (13,24) rank-3 chirotope exists at all, which also answers over R the question of Kühne,
   Szemberg and Tutaj-Gasińska (arXiv:2401.14766) about a 13-point configuration with 24
   three-point lines. [The census re-run without symmetry breaking agreed on 2026-09-05: exactly the predicted
   184,320 labelled models, every one the same class (realize/nolex/PREDICTION.md, RESULT.md).]

## Proposed edit text (OEIS conventions: no markup, one fact per line)

DATA: 0, 0, 1, 1, 2, 4, 6, 7, 10, 12, 16, 19, 22, 26, 31, 37

COMMENTS (replace the 2013 line):
  a(15) = 31: no set of 15 points in the plane determines 32 three-point lines. The proof is a
  computer search (SAT, four symmetry cubes, proofs checked by drat-trim and cake_lpr) over rank-3
  chirotopes, so the bound holds for pseudoline arrangements too. See the Artificial Wasteland
  link. - [submitter], [date]
  a(16) = 37 (Burr, Grünbaum and Sloane, 1974). a(17) is 40, 41 or 42. - _N. J. A. Sloane_, Feb 11
  2013 [edited: the a(15) clause removed]

LINKS (add):
  Artificial Wasteland, <a href="https://artwaste.land/strata/no-thirty-second-row/">No
  Thirty-Second Row</a>: a(15) = 31, with the certificate ledger, 2026.
  Artificial Wasteland, <a href="https://doi.org/10.5281/zenodo.22468969">The orchard problem at
  fifteen points: t3(15) = 31 (certificates)</a>, Zenodo, 2026. [reserved on the draft; live once Liam publishes]

EXTENSIONS:
  a(15)-a(16) from [submitter], [date].

## What the reviewer should check before this goes out

- The reduction (RESULT-15-32.md Section 2): the leave arithmetic and the use of Kelly-Moser for
  pseudolines (Kelly-Rottenberg 1972), and Lemma 7 (the four cubes exhaust the search).
- The certificate protocol (Section 3): regenerate one cube CNF with
  `python3 research/orchard-15/chiro/cnf-audit/emit_cube_cnf.py 15 32 --cube-index k --artifacts DIR`
  (PYTHONPATH=research/orchard-15/chiro), compare its sha256 with the ledger, and re-run drat-trim on
  a regenerated proof if disk allows (cube 0: 26 minutes to solve on four cores, 0.7 GB proof).
- That a(16) = 37 is indeed proved in BGS 1974 and not merely a lower bound (their Table 1 and
  Theorem 4 give the ceiling 37; the configuration on the entry attains it).
- OEIS style: whether the a(13) certificate belongs as a comment on this entry or only in the
  deposit.

## Related entries to touch later

- A186705 (unit-distance graphs, u(n)): a(22) = 60 once the u(22) run is final (separate draft).
