# Negative-path stress test (supervisor, 2026-09-05)

Sample: 120 canonical graphs drawn from `delta4/children-22-61.g6` (22 vertices, 61 edges,
every one contains a forbidden subgraph, so none is a unit-distance graph). The binding-schema
file was regenerated with:
`nice -n 10 ~/tools/pyenv-maths/bin/python -u udembed.py stress/sample-120.g6 --tries 0
--max-states 100 --unknown-file stress/UNKNOWN.g6 > stress/verdicts-120.jsonl`.
Outcome over the 120 distinct graphs: 119 refuted, 1 unknown (`UNKNOWN.g6`). The run took
303.28 seconds, or 2.527333 seconds per graph. So the bounded L0-L3 procedure decides about 99%
of dense 22-vertex
non-embeddable inputs of this kind without any forbidden-subgraph knowledge. The graphs that
matter most, TU-survivors at (22,61), have no forbidden subgraph by construction and may be
harder; the n <= 21 AMP-rejected set (39 graphs) is the calibration for that, after gate G2.
