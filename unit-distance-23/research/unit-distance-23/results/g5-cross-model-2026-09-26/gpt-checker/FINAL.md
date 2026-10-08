Created [gpt_check.py](<scratch>/scratchpad/codex/checker3/gpt_check.py), [selftest.py](<scratch>/scratchpad/codex/checker3/selftest.py), and [REPORT.md](<scratch>/scratchpad/codex/checker3/REPORT.md).

All seven files passed, totaling **57,659 records**:

```text
data/B10-embedded.certs.jsonl: ACCEPT records=32653 unknown=22221 rhombus_refuted=0 rhombus_tu=0 tri_refuted=0 tri_tu=10432
data/level17-parents-w1.certs.jsonl: ACCEPT records=17652 unknown=2103 rhombus_refuted=0 rhombus_tu=0 tri_refuted=3108 tri_tu=12441
data/level19-children.certs.jsonl: ACCEPT records=1354 unknown=18 rhombus_refuted=0 rhombus_tu=0 tri_refuted=641 tri_tu=695
data/measure-15-rhombus.certs.jsonl: ACCEPT records=1500 unknown=1050 rhombus_refuted=102 rhombus_tu=348 tri_refuted=0 tri_tu=0
data/measure-16.certs.jsonl: ACCEPT records=1500 unknown=386 rhombus_refuted=0 rhombus_tu=0 tri_refuted=208 tri_tu=906
data/measure-17-rhombus.certs.jsonl: ACCEPT records=1500 unknown=619 rhombus_refuted=228 rhombus_tu=653 tri_refuted=0 tri_tu=0
data/measure-18.certs.jsonl: ACCEPT records=1500 unknown=36 rhombus_refuted=0 rhombus_tu=0 tri_refuted=375 tri_tu=1089
```

```text
SUMMARY PASS cases=195 red=156 valid=39 passed=195 failed=0
```

The report documents every enforcement rule and interpretation, including root depth zero and permitted repeated leaf rows. Tests cover overflow fakes, wrong rotations, unsorted triangles, missing children, overlapping targets, and budget boundaries.

Lemma R, R1/R2, Lemma T, and the amended case-tree argument are sound under their stated hypotheses; I found no additional local enforcement gap. Using `tu` for pruning still requires induced containment and a separately proved bound \(u(N)\le M\).

B10 has zero refutations. Pipeline coverage, canonical labeling, exact embedding replay, and the unavailable AMP controls are outside this verification.