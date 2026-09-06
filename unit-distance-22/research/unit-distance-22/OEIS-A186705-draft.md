# Proposed edit to OEIS A186705 (unit distances among n points), for a mathematician's review

Drafted 2026-09-06 by claude-reaching-noether-7e1c. Not submitted. House rule: an OEIS edit goes
out only after a mathematician has read it and the certificate, and after AMP have had the
chance to reply to Liam's letter; Liam decides when.

## The entry today (fetched 2026-09-06, fmt=json)

- Name: The Erdős unit distance problem: the maximum number of occurrences of the same distance
  among n points in the plane. Author Michael Somos, Feb 25 2011. Offset 1.
- Data: 0, 1, 3, 5, 7, 9, 12, 14, 18, 20, 23, 27, 30, 33, 37, 41, 43, 46, 50, 54, 57
  (a(1) to a(21); a(15) to a(21) from Alexeev, Mixon and Parshall).
- Comments include Peter Munn (May 24 2026) on AMP's upper bounds for a(22..30), and links to
  AMP (arXiv:2412.11914), Sawin (arXiv:2605.20579) and Alon et al. (arXiv:2605.20695) on the
  May 2026 disproof of the unit distance conjecture.

## What we can add

**a(22) = 60.** No set of 22 points in the plane has 61 unit distances
(research/unit-distance-22/RESULT-u22.md). AMP proved 60 <= a(22) <= 61. The 61-edge case is
excluded by an exhaustive canonical-augmentation enumeration of the forbidden-subgraph-free
graphs (Globus-Parshall list) with 22 vertices and 61 edges, pruned by six totally unfaithful
gadgets and a minimum-degree lemma; the enumeration produced four such graphs, each of which
contains a gadget with its forced pair non-adjacent (so it is not the unit-distance graph of
any point set, given a(22) <= 61) and each of which is also refuted algebraically; both
certificate sets are accepted by a blind checker.

## Proposed edit text

DATA: 0, 1, 3, 5, 7, 9, 12, 14, 18, 20, 23, 27, 30, 33, 37, 41, 43, 46, 50, 54, 57, 60

COMMENTS (add):
  a(22) = 60: no 22-point set has 61 unit distances. Exhaustive enumeration of the candidate
  graphs by the method of Alexeev, Mixon and Parshall, with checkable certificates (see the
  Artificial Wasteland link). - [submitter], [date]

LINKS (add):
  Artificial Wasteland, <a href="https://artwaste.land/strata/the-sixty-first-distance/">The
  Sixty-First Distance</a>: a(22) = 60, with the certificate ledger, 2026.
  Artificial Wasteland, <a href="https://doi.org/10.5281/zenodo.XXXXXXX">The unit-distance
  number of 22 points: u(22) = 60 (certificates)</a>, Zenodo, 2026. [DOI to be minted]

EXTENSIONS:
  a(22) from [submitter], [date].

## What the reviewer should check before this goes out

- Section 2 of RESULT-u22.md: the four properties and why each is hereditary or sound (in
  particular why a gadget hit is a sound prune at the top level, which uses AMP's a(22) <= 61).
- Lemma D4 (delta4/RESULT.md) and the reach table (enum/PRUNING.md).
- results/u22/cell-22-61/: run check/udcheck.py on both certificate files as the README says.
- results/u22/final-levels.json against a fresh run of results/u22/aggregate-slices.py.
- Whether the comment should cite AMP's bound explicitly in the entry's own words.

## Related

- A003035 (orchard): the a(15) = 31 draft is research/orchard-15/OEIS-A003035-draft.md.
