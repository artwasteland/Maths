# Frozen inputs (CONTRACT Sections 1 and 6)

Each file: canonical graph6 (nauty labelg 2.8.8 defaults), sorted bytewise (`LC_ALL=C sort`), one per
line. Regenerate from `research/unit-distance-22/` with nauty-geng 2.8.8 and `filter/udfilter`:

| file | graphs | recipe |
|---|---:|---|
| B10.g6 | 33,162 | `nauty-geng -Cq 10` then keep every record whose udfilter verdict is not `forbidden` (F9, `data/forbidden-74.json`) |
| B9p.g6 | 3,085 | `nauty-geng -Cq 9`, F8 in force |
| B8p.g6 | 383 | `nauty-geng -Cq 8`, F7 in force |

udfilter requires exactly 74 patterns, so F7 and F8 are applied by replacing every member with more
than 7 (resp. 8) vertices by a 10-vertex path, which cannot occur in an 8- or 9-vertex graph.
A `tu` verdict counts as F-free here (gadgets are not a filter at these edge counts).

Checks run 2026-09-24: geng counts 7,123 / 194,066 / 9,743,542 equal OEIS A002218; with F9 in
force the 8- and 9-vertex counts are 366 and 2,984 (GP's printed numbers); an independent
networkx (VF2 monomorphism) pass finds no member of the list in force inside any kept graph of
B8p and B9p, and finds exactly 101 = 3,085 - 2,984 graphs of B9p containing a member of F9 (the
red control).

Added 2026-09-24 (contract amendment 1): `B4p.g6` (3), `B5p.g6` (7), `B6p.g6` (16), `B7p.g6` (60),
the biconnected n-vertex graphs free of the F9 members on at most n - 1 vertices, same recipe; the
geng totals are 3, 10, 56, 468 biconnected graphs, and the networkx pass finds no member in force
inside any kept graph.
