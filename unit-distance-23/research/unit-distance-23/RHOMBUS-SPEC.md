# The rhombus rule: lemma, certificate schema and tool contracts

Binding on the prover builder (`filter/udrhombus`, its `prune.py` and `run-dag2.py` integration) and on the checker
builder (`check/udcheck_rhombus.py`). Written 2026-09-26 by the u(23) supervisor after the measurement in
`LABNOTES.md` (2026-09-26 entries). Amend it here, never in a brief. Paths are relative to
`research/unit-distance-22/` unless they start with `research/`.

## 1. Mathematics

**Lemma R (rhombus).** Let f: V(G) -> R^2 be injective with |f(s) - f(t)| = 1 for every edge st of G. If u, v, w, x
are four distinct vertices with uv, vw, wx, xu all edges of G (a 4-cycle, not necessarily induced), then
f(u) + f(w) = f(v) + f(x).

*Proof.* Put a = f(u) - f(v), b = f(v) - f(w), c = f(w) - f(x), d = f(x) - f(u), four unit vectors with
a + b + c + d = 0. If a + b = 0 then f(u) = f(w), against injectivity. Otherwise s = a + b is nonzero, and the unit
vectors y with |s - y| = 1 are the points common to the unit circles about 0 and about s: at most two, and when there
are two they sum to s. Both a and b = s - a are such points, and so are -c and -d (their sum is -c - d = s). Hence
{a, b} = {-c, -d} as multisets. If a = -d then f(v) = f(x), against injectivity. So a = -c, that is
f(u) - f(v) = f(x) - f(w). QED.

For a 4-cycle C = [u, v, w, x] write r(C) = e_u - e_v + e_w - e_x in Z^n (e_i the standard unit vectors). Lemma R
says sum_i r(C)_i f(i) = 0.

**Corollary R1 (collision).** If 4-cycles C_1..C_k of G, integers l_1..l_k and a nonzero integer s satisfy
sum_j l_j r(C_j) = s (e_a - e_b) with a != b, then G is not a unit-distance graph. (Apply the identity to f:
s (f(a) - f(b)) = 0, so f(a) = f(b), against injectivity.) The certificate refutes G; by PRUNING.md L1 no DAG
descendant of G is a unit-distance graph.

**Corollary R2 (forced unit distance).** If sum_j l_j r(C_j) = s (e_a - e_b - e_p + e_q) with s != 0 and pq an
edge of G, then every unit-distance embedding of G has f(a) - f(b) = f(p) - f(q), so |f(a) - f(b)| = 1. If ab is NOT
an edge of G, this is PRUNING.md L2 with the linear certificate in place of a gadget: for a target (N, M) with
M >= u(N) proved, no graph on N vertices with M edges containing G as an induced subgraph is a unit-distance graph
(it would give M + 1 unit distances on N points). DAG ancestors are induced subgraphs, so the rule is hereditary
exactly as L2 is.

**Relation to the six TU gadgets.** Each gadget's distinguished pair is forced by R2 inside the gadget (checked
mod 2^61-1 on 2026-09-26: gadget i's pair difference equals plus or minus an edge difference modulo its 4-cycle
rows, for all six). So R2 subsumes the gadget rule wherever the gadget sits with its pair non-adjacent. The gadget
verdicts of `udfilter` stay as they are; the rhombus rule runs on udfilter's survivors.

## 2. Certificate schema

The certificate file is the u(22) one (`<n>-<m>.certs.jsonl`, one JSON object per stage-input graph, in input order;
`check/udcheck.py` documents it). Two new witness forms:

    {"g6": G, "verdict": "refuted", "witness": {"rhombus": {"cycles": [[u,v,w,x], ...], "coefficients": [l1, ...],
                                                              "scale": s, "pair": [a, b]}}}
    {"g6": G, "verdict": "tu",      "witness": {"rhombus": {"cycles": [[u,v,w,x], ...], "coefficients": [l1, ...],
                                                              "scale": s, "pair": [a, b], "edge": [p, q]}}}

A checker accepts a rhombus record only if ALL of the following hold, in exact integer arithmetic:

1. `witness` has exactly the key `rhombus`; `rhombus` has exactly the keys shown for its verdict (no others);
2. `cycles` is a non-empty list of at most 4096 entries; each entry is a list of 4 JSON integers in [0, n), pairwise
   distinct, and uv, vw, wx, xu are all edges of G;
3. `coefficients` is a list of JSON integers (never booleans or floats) of the same length as `cycles`, each nonzero
   and of absolute value below 2^62; `scale` is a JSON integer, nonzero, of absolute value below 2^62;
4. `pair` is two distinct JSON integers in [0, n); for verdict `tu`, ab is NOT an edge of G;
5. (`tu` only) `edge` is two distinct JSON integers in [0, n), and pq IS an edge of G;
6. sum_j l_j r(C_j) equals s (e_a - e_b) (verdict `refuted`) or s (e_a - e_b - e_p + e_q) (verdict `tu`), as
   integer vectors of length n.

Every other record is udcheck.py's schema and is checked by `check/udcheck.py` (set 74) or `check/udcheck398.py`
(set 398), both unchanged and hash-pinned. A rhombus record's verdict is only ever `refuted` or `tu`; `unknown`,
`embedded` and `forbidden` records never carry a rhombus witness.

## 3. Tool contracts

**Prover `filter/udrhombus` (C).** Reads graph6 lines (one graph per line) on stdin; writes exactly one JSON line
per input line, in order, to stdout: `{"verdict":"pass"}` or `{"verdict":"refuted","witness":{"rhombus":...}}` or
`{"verdict":"tu","witness":{"rhombus":...}}`. Priority: a collision if one exists (the lexicographically first pair
a < b), else a forced unit distance on a non-adjacent pair (the lexicographically first such pair a < b, and for it
the lexicographically first ordered edge (p, q) that forces it), else pass. Detection may be modular; every emitted
certificate must satisfy Section 2 exactly, and the prover checks its own identity in exact integer arithmetic
before emitting (on failure it emits pass and counts the event in a stats line on stderr). Deterministic: the same
input bytes give the same output bytes. Nothing it does can remove a graph without a certificate.

**Checker `check/udcheck_rhombus.py` (Python).** Same command line as udcheck.py (at least `--expect-n`,
`--expect-m`, `--graphs`, `--unknown-file`, `--data-dir`, `--labelg`, the certificate path) plus
`--forbidden-set {74,398}` (default 74). It verifies the file's structure itself (JSON, exact top-level keys, graph6
decoding and the expected order and size, no duplicate record, and, with `--graphs`, that the records' g6 sequence
equals the list exactly), verifies every rhombus record per Section 2, and hands every other record to the pinned
kernel as a subprocess (`udcheck.py` for set 74, `udcheck398.py` for set 398) on a derived certificate file and
graph list holding exactly those records in order, with the same `--unknown-file`. It prints one line
`ACCEPT certificates records=R forbidden=F tu=T embedded=E refuted=X unknown=U proof_nodes=P rhombus_tu=RT
rhombus_refuted=RX` (tu and refuted INCLUDE the rhombus ones) and exits 0, or prints `REJECT: <reason>` on stderr and
exits nonzero. Canonical form is checked for every record (the kernel does it for its records; the rhombus records'
graph6 strings go through the kernel's `check_canonical_g6_list` or an equivalent `nauty-labelg` call).

**Integration.** `enum/prune.py --rhombus` and `enum/run-dag2.py --rhombus` (default off: without the flag every
output byte and every manifest is unchanged); with it, the prune step runs udrhombus on udfilter's survivors, writes
rhombus certificates, and replays the whole certificate file with `check/udcheck_rhombus.py`. The flag is recorded
in run-config.json, run-summary.json and every prune manifest. The cloud runbook takes `U23_RHOMBUS=1` and keys its
run directories by it, so a prefix built without the rule is never hard-linked into a run with it.

## 4. The triangle extension (phase B)

Measured 2026-09-26 (`LABNOTES.md`): on graphs the rhombus rule leaves, splitting on triangle orientations closes a
further 33 / 50 / 71 / 91 % at levels 15 / 16 / 17 / 18 of the (23,65) tree.

**Lemma T (triangle orientation).** Identify R^2 with C and let w = e^(i pi / 3), so w^2 = w - 1 and
w^(-1) = 1 - w. If f is a unit-distance embedding of G and {a, b, c} is a triangle of G with a < b < c, then
f(c) - f(a) = w^s (f(b) - f(a)) for s = +1 or s = -1. (The three points form an equilateral triangle of side 1; the
rotation about f(a) taking f(b) to f(c) is by +60 or -60 degrees.)

For a sorted triangle T = (a, b, c) and a sign s write t(T, s) = e_c - e_a - w^s (e_b - e_a) in Z[w]^n. Lemma T says
t(T, s) . f = 0 for the sign s that f realises. Lemma R's rows r(C) hold for f as complex equations too.

**Certificate: a case tree.** Elements of Z[w] are JSON pairs [x, y] of integers meaning x + y w.

    {"g6": G, "verdict": "refuted" | "tu", "witness": {"tri": {"tree": NODE}}}
    NODE := {"split": [a, b, c], "plus": NODE, "minus": NODE}
          | {"leaf": {"cycles": [[u,v,w,x], ...], "cycle_coefficients": [Zw, ...],
                      "triangles": [[a,b,c], ...], "triangle_coefficients": [Zw, ...],
                      "scale": Zw, "pair": [a, b], "edge": [p, q], "zeta": k}}      ("edge" and "zeta" together or neither)

A checker accepts only if, in exact integer arithmetic:

1. every `split` is a sorted triple a < b < c of vertices in [0, n) whose three pairs are edges of G, and no triangle
   is split twice on one root-to-leaf path; `plus` assigns it s = +1 and `minus` s = -1; the tree has at most 100,000
   nodes and depth at most 64;
2. every entry of a leaf's `triangles` is a sorted triple [a, b, c], a < b < c, EQUAL (as that sorted list) to a
   triple split on the path to that leaf, and it is used with that path's sign (a checker must not accept an
   unsorted entry by set lookup: swapping a and b reverses the orientation, so e_c - e_b - w^s (e_a - e_b) with the
   path's s would be a false relation); every entry of `cycles` is a 4-cycle of G as in Section 2 rule 2 (at most
   4096 entries); either list may be EMPTY (a leaf may close on rhombus rows alone or, in principle, on triangle rows
   alone), but not both; the coefficient lists match their lists in length; every coefficient and the scale are Z[w]
   pairs of JSON integers of absolute value below 2^62; no coefficient is [0, 0]; the scale is not [0, 0];
3. `pair` is two distinct vertices; with `edge`: pq is an edge of G, ab is NOT an edge of G, `zeta` is an integer
   0..5, and the target is e_a - e_b - w^k (e_p - e_q); without `edge`: the target is e_a - e_b;
4. sum_j l_j r(C_j) + sum_T m_T t(T, s_T) equals scale * target as vectors in Z[w]^n (multiply with w^2 = w - 1);
5. verdict `refuted` only if no leaf has an `edge`; verdict `tu` otherwise.

*Soundness.* An injective unit-distance embedding f follows one root-to-leaf path (Lemma T at every split). At its
leaf every listed relation holds for f, so scale * (f(a) - f(b) - w^k (f(p) - f(q))) = 0, and a nonzero scale (1 and
w are independent over R) gives f(a) - f(b) = w^k (f(p) - f(q)): a unit distance on the non-edge ab, or, without an
edge, f(a) = f(b), against injectivity. So `refuted` proves G is not a unit-distance graph (L1), and `tu` proves that
every unit-distance embedding of G realises a unit distance on some non-edge, which prunes exactly as L2 does at a
target with M >= u(N). Heredity is as for Section 1.

**Prover `filter/udtriangle` (C).** Same I/O contract as udrhombus (Section 3), witness key `tri`. Suggested method
(the prototype `research/unit-distance-23/tools/triangle_probe.py`, mod p = 2^61 - 1 with w a root of x^2 - x + 1):
depth-first over triangle splits, closing a node as soon as its relations force a collision or a sixth-root-of-unity
multiple of an edge on a non-edge, splitting the first triangle whose orientation the node's rows do not already
decide (amendment 2026-09-26: a triangle sharing an edge with a split one is never undecided, because the rhombus row
of the 4-cycle through both apexes fixes it, so the earlier suggestion to prefer such triangles was vacuous); a node
budget, beyond which the graph passes. Exact leaf coefficients over Z[w] (fraction-free elimination on an independent
subset of the rows, re-verified exactly before emitting; any failure passes the graph). The rhombus rule is the
case with no split, so udtriangle's verdict set contains udrhombus's.

## 5. Amendments

1. (2026-09-26, from the triangle prover builder's report) Section 4 rule 2: leaf triangles must be the exact sorted
   triples split on the path (the unsorted-lookup trap); either leaf list may be empty but not both; coefficients
   are nonzero, as in Section 2. The split-order suggestion corrected. No verdict of the prover changes.
2. (2026-09-26, from the adversarial referee's report; no fatal objection was found, these close enforcement gaps)
   - **Structure (Section 4 rule 1 and Section 2 rule 1).** A checker parses JSON with a duplicate-key-rejecting
     hook (udcheck.py's `no_duplicate_object`) and enforces EXACT keys everywhere: `witness` has exactly `rhombus` or
     exactly `tri`; a split node has exactly `split`, `plus`, `minus`, and BOTH children are present and are nodes; a
     leaf node has exactly `leaf`; the leaf object has exactly `cycles`, `cycle_coefficients`, `triangles`,
     `triangle_coefficients`, `scale`, `pair`, and optionally `edge` and `zeta` (both or neither). A tree with a
     missing child is rejected (a half tree could "refute" an embeddable graph).
   - **Arithmetic.** "Exact integer arithmetic" means arbitrary precision: Python int, never numpy or any fixed-width
     type (with 4096 terms of size 2^62 a fixed-width sum wraps). A prover may self-verify in fixed width only if an
     overflow can only make it fail closed (emit pass).
   - **Targets** are computed as vector sums: entries accumulate and may cancel or double when pair and edge share a
     vertex (a = p or b = q is a collision in disguise; both still prune). In Section 4 rule 3, p != q.
   - **Verdicts** (Section 4 rule 5): the verdict is `refuted` if and only if no leaf has an `edge`, and `tu` if and
     only if at least one does.
   - **Silent passes are counted.** A prover's self-verification failures, lift failures and budget passes are
     counted in its stats line and copied into the prune manifest, so a prover that quietly stops certifying is
     visible.
   - **Checker for `tri` records.** Section 3's checker contract covers `tri` records exactly as `rhombus` records:
     the same wrapper verifies them (through a tree verifier implementing Section 4), and hands every other record to
     the pinned kernel. Integration flags: `enum/prune.py --triangles` and `enum/run-dag2.py --triangles` (default
     off; they imply the rhombus rule, since udtriangle's verdicts contain udrhombus's), recorded in run-config.json,
     run-summary.json and every prune manifest; runbook `U23_TRIANGLES=1`, keyed into the run directory names.
   - **The chain checker.** `enum/verify-chain.py --check` replays every certificate file with
     `check/udcheck_rhombus.py` when the run's manifests record `--rhombus` or `--triangles`, and REFUSES a run whose
     certificate files contain a `rhombus` or `tri` witness while its manifests do not record the flag.
   - **Binding controls** (each must be run through the CHECKER, not only the prover's own counts): zero `refuted`
     among GP-10's 32,653 embedded B10 graphs and AMP's 56 known graphs, with no graph of the 56 flagged at all;
     every `tu` certificate on an embedded B10 graph followed through its exact embedding to a true unit leaf; and
     red mutants that the checker must reject: the wrong ring (w^2 = -w - 1), a sign flip in t(T, s), a repeated
     vertex in a cycle, a dropped tree child, an int64 checker (a certificate whose intermediate sums exceed 2^63),
     and an unsorted leaf triangle.
   - **CONTRACT.** When the tools land, CONTRACT Section 0 lists Lemma R and Lemma T among the dependencies, Section 3
     names `check/udcheck_rhombus.py` among the acceptors, and PRUNING.md gains Section L5.
   - Lemma R's proof covers the tangent case |s| = 2: then a = b = -c = -d = s/2, so a = -d and f(v) = f(x), excluded.
