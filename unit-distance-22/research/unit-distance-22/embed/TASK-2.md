# Task B3b: conform the embedder's certificates to the binding checker schema (module embed/)

Read REPORT.md and udembed.py here (your predecessor's embedder: 56/56 known graphs embedded
with exact certificates, 41 of 74 forbidden graphs refuted, six gadgets fire L2), then read the
module docstring of ../check/udcheck.py, which CONTRACT Section 9.1 makes the binding witness
schema (you may read that file; the checker's author was blind to this module and stays so).
Today the checker rejects our output: for "embedded" it wants `field: {minpoly, interval}` and
`coordinates` as [x, y] pairs of field elements (ascending-order coefficient arrays, rationals
as integers or "p/q" strings); for "refuted" it wants `field` and `tree`, each node with
`edges`, `A` (the exact complex constraint matrix as complex field elements), `move`
(`{"kind":"L1a","pair":[u,v]}`, `{"kind":"L1b","edges":[[u,v],[x,y]],"omega":complex}`,
`{"kind":"L2",...}`, `{"kind":"L3","edges":[...3...],"coefficients":[a,b,c],"d":element}`) and
`children` (L1: none; L2: one; L3: two, first child +i*d). It also requires all three L3
coefficients nonzero (CONTRACT 9.5) and verifies each L3 node's d^2 and realness exactly.

Change udembed.py so that its emitted certificates are accepted by
`~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null
<file>` with NO change to udcheck.py. Keep the mathematics; restructure the serialisation, and
where the checker's tree semantics differ from the current internal tree (for instance the L0
root and how constraint rows are represented), adapt the producer, not the checker. Run and
report, each with the exact command and the checker's final line: (1) K4 refuted; (2) all 56
catalog graphs embedded, accepted by udcheck; (3) all 41 refuted forbidden graphs accepted by
udcheck; (4) the file stress/verdicts-120.jsonl regenerated with the new schema for the 120
graphs in stress/sample-120.g6 (dense 22-vertex non-UDGs; report refuted/unknown counts and
the time per graph) and every refuted record accepted by udcheck; (5) one mutation: corrupt one
L3 `d` value and confirm udcheck rejects it. Do not touch ../check/.
