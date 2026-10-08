Independent rhombus and triangle certificate checker
===================================================

All seven supplied files were accepted, comprising 57,659 records. The CLI
self-test passed all 195 cases: 156 red controls and 39 positive cases.

`gpt_check.py` was written from the specification in this directory. No producer,
other checker, external reference, or source material outside this directory was
consulted. It imports only `json` and `sys` from the Python standard library.
`selftest.py` constructs its own fixtures, never reads `data/`, never imports the
checker, and submits every case to a fresh invocation of the checker's actual
command-line interface. Temporary test files are created inside this directory.

Run with `python3 gpt_check.py FILE.certs.jsonl` and `python3 selftest.py`.
The recorded outputs are in `data-results.txt` and `selftest-results.txt`.

Rule implementation
-------------------

| Specification requirement | Implementation |
| --- | --- |
| Record well-formedness and exact keys | A record is an object with exactly `g6`, `verdict`, and, for a non-unknown verdict, `witness`. Only `unknown`, `refuted`, and `tu` are supported. Unknown records have no witness, including no null witness. |
| Duplicate-key rejection | `json.loads` uses `object_pairs_hook=no_duplicates`, at every nesting level. Keys are compared after JSON escape decoding. Nonstandard `NaN` and infinity tokens are rejected. |
| Graph decoding | `decode_graph6` decodes the order and the upper triangle by columns, taking the most significant bit first. It checks the character range, exact payload length, and zero padding. Adjacency is undirected and has no loops. No graph library is used. |
| Section 2.1: witness and rhombus keys | The witness contains exactly one of `rhombus` and `tri`. A rhombus has exactly the four required fields, plus `edge` exactly when its verdict is `tu`. |
| Section 2.2: cycles | The rhombus list has 1 through 4096 cycles. Every cycle is a list of four distinct, in-range JSON integers; all four edges, including the closing edge, must exist. Chords are allowed. |
| Section 2.3: coefficients and scale | The coefficient list has the same length as the cycle list. Every coefficient and the scale has type exactly `int`, is nonzero, and has absolute value strictly below `2^62`. Thus booleans, floats, and boundary values are rejected. |
| Section 2.4–5: pair and edge | Every pair has two distinct, in-range integer vertices. For `tu`, the pair is a non-edge and the specified edge is an edge. Refuted pairs may be edges. |
| Section 2.6: identity | Each signed cycle row is accumulated into an integer vector of length `n`. The target is accumulated independently, with scaled positive and negative contributions, and every coordinate is compared exactly. |
| Section 4.1: tree structure | An explicit depth-first stack visits every node. Split nodes have exactly `split`, `plus`, `minus`; both children must be objects. Leaf nodes have exactly `leaf`. The `tri` wrapper has exactly `tree`. |
| Section 4.1: splits and budgets | Split triples must already satisfy `a < b < c`, be in range, and have all three graph edges. Each child gets its own path map, with sign `+1` or `-1`. A repeated split on one path is rejected. The total node count is at most 100,000 and depth at most 64. |
| Section 4.2: leaf rows | A leaf has exactly the six required fields, with `edge` and `zeta` both present or both absent. Cycle lists have at most 4096 entries. Either row list may be empty, but not both. Both coefficient lists must match their respective row lists. |
| Section 4.2 and amendment 1: triangles | Each leaf triangle is validated as an already sorted triple before its exact ordered tuple is looked up in that leaf's path map. It is never sorted by the checker or matched as a vertex set. Its row uses the sign from that path. |
| Section 4.2: ring coefficients and scale | Every value is a two-element JSON list of bounded integer components, each with absolute value below `2^62`. No coefficient or scale can be `[0,0]`. A nonzero value need not be a unit of the ring. |
| Section 4.3: target | Both pair and edge endpoints are validated, including `p != q`. An edge leaf requires a graph edge, a graph non-edge as its pair, and an integer `zeta` in `0..5`. The target is built by adding all contributions, then multiplied by the scale. Shared vertices can cancel or double. |
| Section 4.4: identity | Rhombus and path-signed triangle rows are accumulated in `Z[w]^n`, then compared coordinate by coordinate to the scaled target. |
| Section 4.5 and amendment 2: verdict | All leaves are checked, including those visited after a unit leaf. Only after verification does the checker require `tu` iff at least one leaf has an edge, and `refuted` iff none does. |
| Arbitrary precision and first failure | All arithmetic uses Python `int`; no floating-point or modular arithmetic participates in verification. Records are processed in physical line order. The first failure prints one `REJECT line L: ...` line and exits 1; success prints the requested counters and exits 0. |

The multiplication formula is

```
(x + y*w)(u + v*w) = (x*u - y*v) + (x*v + y*u + y*v)*w.
```

The six rotations, in order, are `(1,0)`, `(0,1)`, `(-1,1)`, `(-1,0)`,
`(0,-1)`, `(1,-1)`. The row for a path sign is formed as
`e_c + (w^s - 1)e_a - w^s e_b`, with `w^(-1) = 1 - w`.
Bounds apply to input components; intermediate results have no fixed-width bound.
Where available, Python's decimal integer digit limit is disabled so that even
very long JSON integers are parsed exactly before the certificate bounds are
applied. A 5000-digit scale is a tested rejection.

Interpretations and scope
-------------------------

The specification leaves a few representational conventions implicit. These are
the choices made here:

- Depth counts edges from a root at depth zero. A path may therefore contain 64
  splits followed by a leaf. Total nodes include both internal nodes and leaves.
  Because a full binary tree has an odd number of nodes, 99,999 is the largest
  attainable size within the 100,000-node limit; 100,001 is rejected.
- Section 4's 4096-row cap applies to cycles. No triangle-row cap is stated, so
  none is added. Repeated leaf triangles and repeated cycle rows are allowed;
  coefficients still must be nonzero. A triangle cannot be split twice on one
  path, but it may be split on separate branches. Leaves need not use every
  split on their path. Positive controls exercise all these distinctions.
- Pair and edge lists are ordered as supplied, with no sorting requirement and
  no requirement that their four endpoints all differ. Cycle vertices likewise
  need not be sorted. Sortedness is required specifically for triangle triples.
- In addition to the short graph6 order format used by the supplied data, the
  decoder supports standard 18-bit and 36-bit order encodings, with their
  minimal ranges, and the optional `>>graph6<<` header. Whitespace inside `g6`,
  extra payload, and nonzero padding are rejected. Payload length is checked
  before allocating adjacency from a claimed order. Tests include orders 62
  and 63 and malformed extended encodings; constructing a valid 36-bit-order
  graph would require an impractically large fixture and was not tested.
- Empty files are accepted with zero counters; blank lines are invalid records.
  CRLF line endings and an unterminated final line are accepted. UTF-8 is checked
  per physical line. Argument and file-open errors use line zero because no
  input record has yet been read.

This is the requested Section 2/4 per-record verifier and custom CLI, rather than
the Section 3 pipeline wrapper. It does not call a pinned kernel or `nauty`,
check graph canonical labeling, enforce distinct graphs across records, compare
an expected input sequence, verify expected graph order/size, or implement the
other witness types. Repetition of a graph does not change the validity of an
individual certificate. Pipeline completeness and graph-list reconciliation
remain separate obligations, as do manifest flags and prover pass statistics.

Independent controls and their algebra
-------------------------------------

The complete PASS/FAIL log includes each red control's actual rejection reason.
The tests also assert the exit status, a single stdout line, empty stderr, exact
success counters, and the line number for a failure after a valid record.

The main positive fixtures have short, explicit derivations:

- **K2,3.** Hubs are 0 and 1; the other vertices are 2, 3, 4. The cycles
  `[0,2,1,3]` and `[0,2,1,4]`, with coefficients `1,-1`, sum to `e_4-e_3`.
- **K4.** The cycles `[0,1,2,3]` and `[0,2,1,3]`, with coefficients `1,-1`,
  sum to `2(e_2-e_1)`. This also checks that a cycle need not be induced.
- **An embeddable forced-distance gadget.** The cycles `[2,3,0,1]` and
  `[4,5,0,1]` sum with coefficients `1,-1` to
  `e_2-e_4-e_3+e_5`; `35` is an edge and `24` is a non-edge. A concrete
  injective embedding is `f(0)=0`, `f(1)=-i`, `f(2)=1-i`, `f(3)=1`,
  `f(4)=w-i`, `f(5)=w`. Every listed edge has length one, and `24` also has
  length one. Thus the positive TU fixture does not rely on nonembeddability.
- **K4 using only triangles.** Split 012 and 013. Equal signs give
  `t(012)-t(013)=e_2-e_3`. For opposite signs, split 023 as well. If their
  rotations are `r,t,u`, respectively, then
  `u*t(012)-t(013)+t(023)=(u*r-t)(e_0-e_1)`.
  The four hand-computed scales are `(-2,2)`, `(0,1)`, `(1,-1)`, `(0,-2)`.
- **Rotated TU leaves.** Add triangle 356 to the gadget. With `R` its cycle
  difference and `r=w^s`,
  `R+r^(-1)*t(356,s)=e_2-e_4-r^(-1)*(e_3-e_6)`.
  Reversing the edge and using other root-leaf fixtures exercises all six zeta
  values. Other positive controls cover mixed collision/unit leaves, nonreal
  scales, and all four possible single-vertex overlaps of pair and edge.

Red controls cover exact schemas, duplicate keys (including escaped duplicates),
integer types and strict bounds, every graph/row membership condition, both
children, path-local triangle lookup, empty rows, zero coefficients and scales,
verdict mismatches, ring arithmetic, and each size/depth limit. In particular:

- A counterfeit identity adds eight copies of a cycle with coefficient `2^61`.
  Its error is exactly `2^64*r(C)`, so it vanishes modulo `2^64`. Both witness
  forms reject it. Positive controls then cancel that error after intermediate
  sums exceed `2^64`, and must still be accepted.
- Wrong-ring scales make the K4 identities hold under `w^2=-w-1`, and fail
  under the required ring. They are rejected. Swapped branch signs and a
  triangle coefficient sign error are also rejected.
- An embeddable diamond, with triangles 012 and 013, is falsely "refuted" by a
  tree built for rotations `w^2` and `w^(-2)` instead of `w` and `w^(-1)`.
  Its opposite-sign leaves claim
  `r(0,2,1,3)+t(012)+t(013)=-2(e_0-e_1)`. The true left side is zero.
- A separate diamond counterexample swaps the first two vertices of leaf
  triangle 013 on opposite-sign branches. Set-based path lookup would permit
  the false relation. The checker rejects the unsorted triple before lookup.

Most cases are small certificates. Tests of 4096 cycles, more than 4096 triangle
rows, 64/65 depth, and 99,999/100,001 nodes expand the same hand-made fixtures to
exercise the stated limits. They use no proof producer or linear-system solver.

Soundness assessment
--------------------

**Lemma R is sound for injective planar unit-distance embeddings.** An independent
way to see it is to take the opposite vertices `u,w` as the centers of two unit
circles. Both `v,x` are intersection points. Injectivity makes the centers
distinct and makes these two intersection points distinct. They are therefore
the two symmetric intersections, whose midpoint is the midpoint of the centers.
Consequently `f(u)+f(w)=f(v)+f(x)`. A tangent intersection would force `v=x` and
is excluded; coincident centers would force `u=w` and are excluded. Chords do
not affect the argument. The specification's vector proof, with its tangent-case
amendment, reaches the same conclusion. This argument is specific to the plane.

**Corollary R1 is sound.** Apply a verified vector identity to `f`. All cycle
rows vanish; the nonzero integer scale forces `f(a)=f(b)`. The checked distinct
vertices contradict injectivity. Any graph containing this graph as a subgraph
is likewise impossible, provided vertex inclusion is injective.

**Corollary R2 is sound, with its stated pruning hypotheses.** The exact identity
forces `f(a)-f(b)=f(p)-f(q)`, so an actual edge gives a unit distance on the
checked non-edge. This alone does not prove the graph nonembeddable: the gadget
above is a positive example. For pruning an `N`-vertex, `M`-edge descendant,
there must separately be a proof of `u(N) <= M` and induced containment of the
certified graph. Induced containment preserves the certified non-edge, giving
at least `M+1` unit-distance pairs, a contradiction. Arbitrary supergraph
containment would not suffice for this TU argument because the pair might
already be an edge of the descendant.

**Lemma T is sound.** Three mutually unit-separated planar points form an
equilateral triangle. The displacement from `a` to `c` is the displacement from
`a` to `b` rotated by exactly +60 or -60 degrees. The specified ordering fixes
which displacement is the base. Swapping vertices while retaining a stored sign
is not legitimate; the sorted, exact path matching is essential.

**The amended case-tree argument is sound.** Any embedding selects a sign at
each split and hence a root-to-leaf path in the finite, complete binary tree.
Every listed row at that leaf vanishes on that embedding. The ring evaluation
has no problematic nonzero scale: for integer `x,y`,
`|x+y*w|^2 = x^2+x*y+y^2`, which is positive unless both components are zero.
Thus cancellation of the verified scale is valid in the complex numbers; the
scale need not be invertible within `Z[w]` itself. A collision leaf excludes
that path. Any embedding that survives must reach a unit leaf, which forces a
unit distance on a graph non-edge. Different unit leaves may force different
pairs; the extremal counting contradiction requires only some extra pair in
each embedding. A common pair across all leaves is unnecessary. Mixed trees
are correctly labeled `tu`, and a tree with unit leaves may still describe a
nonembeddable graph.

I find no additional local mathematical acceptance condition missing after the
two amendments. Distinct/in-range integer vertices, actual graph edges and
non-edges, exact sorted path triangles, both children, nonzero scales, the
specified rotations, and full exact vector identities suffice. Some mandated
format restrictions, such as nonzero individual coefficients and budgets, are
stricter than mathematics requires and are nevertheless enforced.

Acceptance here is not a verification of an entire extremal-proof pipeline.
Injective planar embeddings, the bound on `u(N)`, induced descendant mappings,
and complete input/manifest accounting must be justified by that pipeline.
The B10 file has zero refuted records, satisfying the supplied part of that
control. No exact B10 embedding coordinates or identified AMP-56 suite were
provided, so this work does not claim the separate coordinate-follow-through
or AMP binding controls in Section 5. The algebraic certificates themselves
were all checked.

Recorded results
----------------

Every command below exited zero:

```
data/B10-embedded.certs.jsonl: ACCEPT records=32653 unknown=22221 rhombus_refuted=0 rhombus_tu=0 tri_refuted=0 tri_tu=10432
data/level17-parents-w1.certs.jsonl: ACCEPT records=17652 unknown=2103 rhombus_refuted=0 rhombus_tu=0 tri_refuted=3108 tri_tu=12441
data/level19-children.certs.jsonl: ACCEPT records=1354 unknown=18 rhombus_refuted=0 rhombus_tu=0 tri_refuted=641 tri_tu=695
data/measure-15-rhombus.certs.jsonl: ACCEPT records=1500 unknown=1050 rhombus_refuted=102 rhombus_tu=348 tri_refuted=0 tri_tu=0
data/measure-16.certs.jsonl: ACCEPT records=1500 unknown=386 rhombus_refuted=0 rhombus_tu=0 tri_refuted=208 tri_tu=906
data/measure-17-rhombus.certs.jsonl: ACCEPT records=1500 unknown=619 rhombus_refuted=228 rhombus_tu=653 tri_refuted=0 tri_tu=0
data/measure-18.certs.jsonl: ACCEPT records=1500 unknown=36 rhombus_refuted=0 rhombus_tu=0 tri_refuted=375 tri_tu=1089
```

Aggregate counts: `records=57659 unknown=26433 rhombus_refuted=330
rhombus_tu=1001 tri_refuted=4332 tri_tu=25563`.

```
SUMMARY PASS cases=195 red=156 valid=39 passed=195 failed=0
```
