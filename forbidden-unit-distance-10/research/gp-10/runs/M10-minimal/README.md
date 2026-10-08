# The Moebius ladder on 10 vertices is a minimal forbidden unit-distance graph

`Is?@WxcU?` (canonical graph6) is the circulant C10(1,5), the Moebius ladder M10: 10 vertices, 15 edges.

- It contains none of GP's 74 minimal forbidden graphs on at most 9 vertices (checked by the checker's own
  containment test during minimality derivation, and by udfilter and the independent recount's matcher).
- It is refuted by an R-null certificate (a Nullstellensatz identity with the frame on an edge and
  Rabinowitsch terms for non-adjacent pairs), in `records.jsonl`. Two further independent refutations
  (R-tree, R-real) are accepted too: `research/gp-10/refute/` evidence, checked with an empty list in force.
- Its 15 one-edge deletions fall into two isomorphism classes, `I@ClAdCaG` and `I@GQtHG`G`, both
  biconnected, both embedded here with exact E-exact certificates.

The blind checker (`research/gp-10/check/gp10check.py`, profile `sample`, `derive: true`, F9 in force)
accepts all three records and derives `minimal.g6` = [`Is?@WxcU?`] (`checker-report.json`). By L-min
(`PROOFS.md`) M10 is therefore a minimal forbidden graph on 10 vertices. MathWorld's "Unit-Distance Graph"
page states that Moebius ladders are not unit-distance (pers. comm., B. Alexeev, 2025-08-09); this adds a
checked certificate and minimality.

Reproduce from the repository root:
`SYMPY_GROUND_TYPES=python ~/tools/pyenv-gp10/bin/python research/gp-10/check/gp10check.py research/gp-10/runs/M10-minimal --output /tmp/m10-out`
