The real certificate is **ACCEPTED**, with exit status 0. The checked tree proves that the supplied labelled graph has no injective unit-distance embedding in the plane, using the geometric facts and Heron rule in the supplied specifications and the explicit contradiction rule below for the otherwise undefined L1b label.

The only pre-existing project files consulted were `spec/FORMAT.md`, `spec/PROOFS.md`, `data/23-65.g6`, and `data/23-65.certs.jsonl`. No reference checker, prover, external project file, website, or third-party Python package was consulted. The verifier uses only Python's standard library. All mathematical decisions use integers, `Fraction`, and exact polynomial arithmetic.

Run the verifier with:

```sh
python3 verify_tree.py data/23-65.g6 data/23-65.certs.jsonl
```

Its complete successful stdout is `ACCEPT`. Rejections print `REJECT <reason>` and exit 1. The command takes exactly one graph file and one certificate record; extra JSON records are rejected.

The five recorded subprocess runs gave these results. Times use `perf_counter_ns`, include Python startup and input parsing, and are expressed below as exact decimal seconds. Their summed wall time is **0.763872663 seconds**; the real verification took **0.383986908 seconds**. The machine-readable observations, including exit status and empty stderr, are in `verification_results.json`.

| Case | Graph input | Certificate input | Exit | Wall seconds |
| --- | --- | --- | ---: | ---: |
| Real | `data/23-65.g6` | `data/23-65.certs.jsonl` | 0 | 0.383986908 |
| (a) Root matrix changed | `data/23-65.g6` | `controls/a_root_A.jsonl` | 1 | 0.095581497 |
| (b) Child subtree removed | `data/23-65.g6` | `controls/b_missing_child.jsonl` | 1 | 0.098269149 |
| (c) Root coefficient changed | `data/23-65.g6` | `controls/c_root_coefficients.jsonl` | 1 | 0.100474360 |
| (d) Graph edge removed | `controls/d_edge_removed.g6` | `data/23-65.certs.jsonl` | 1 | 0.085560749 |

The four controls are valid inputs with these precise semantic changes and outputs:

1. **(a)** Changed `witness.tree.A[0][0]` from `[1]` to `[2]`. Output:

   ```text
   REJECT root.A: row space does not equal all graph 4-cycle rhombus rows
   ```

2. **(b)** Removed `witness.tree.children[1]`, including its entire subtree. Output:

   ```text
   REJECT root: L3 requires 2 children; found 1
   ```

3. **(c)** Changed `witness.tree.move.coefficients[0]` from `[1]` to `[2]`. Output:

   ```text
   REJECT root.move: ax+by+cz is not in A row space
   ```

4. **(d)** Removed the undirected edge `{0,4}` from the graph, retaining all 23 vertices and using the unmodified certificate. I wrote the graph6 encoder directly, packing the upper triangle by columns into six-bit characters. The resulting graph has 64 edges and is:

   ```text
   V??QPIGD@AGOoHKE_o?Q??HK?WqH@PO_m@CWCaHN_?F_
   ```

   Output:

   ```text
   REJECT root.edges: does not equal input graph (missing=[], extra=[(0, 4)])
   ```

Thus none of the required controls relies on a crash, syntax error, metadata-only mismatch, or unrelated rejection.

The real graph decodes to 23 vertices and 65 edges. Enumerating all distinct four-vertex cycles, including cycles with chords, gives **57 cycles**. Their midpoint equations span a space of dimension **18**, exactly the root's row space. Every node has precisely the original 65 graph edges. The checked tree has **15 nodes**, comprising **7 L3 splits** and **8 L1b contradiction leaves**, at maximum depth 3. Matrix ranks and node counts are 18:1, 19:2, 20:4, and 21:8. All 304 supplied matrix rows, each with 23 entries, were parsed and included in the row-space checks.

The field polynomial is `81*t^4 - 684*t^2 + 256`, with the supplied open interval `(13436/4735, 62183/21914)`. The verifier proves irreducibility over Q by an exhaustive Kronecker factor search. For this quartic, any proper factorization would have an integer factor of degree at most two, by Gauss's lemma. At `0, 1, -1`, the primitive polynomial has values `256, -347, -347`. The search interpolates all **288** combinations of signed divisors of these values and finds no nonconstant integer polynomial dividing the quartic. This is an exhaustive proof, not a numerical or probabilistic test. Independently, the exact Sturm variation counts at the interval endpoints are **1 and 0**, and neither endpoint is a root, proving that the interval contains exactly one real root.

Every L3 checks that its three directed edges exist, that all coefficients are nonzero, and that `a*x+b*y+c*z` belongs to the node's row space. It recomputes all squared moduli, `q`, and the Heron discriminant, verifies `d*d` exactly, and checks nonnegativity at the selected real root. The first three splits in the tree have discriminant 3; the four final splits have discriminant 11/9. Each ordered child is checked against the entire parent row space plus exactly its specified `+i*d` or `-i*d` row. Equality is checked in both directions through canonical reduced row bases.

At each L1b leaf, the verifier explicitly proves that the first displacement equals `omega` times the second. Both displacements are graph edges and hence must have length one. It computes `|omega|^2 - 1` exactly and verifies that it is nonzero; exact sign evaluation additionally found it **negative at all eight leaves**. Consequently every leaf contradicts the unit edge requirements. Combining these leaves with the exhaustive L3 alternatives and the valid root constraints proves the claimed nonexistence.

The supplied texts have the following omissions or representation ambiguities. These are the interpretations used; no unchecked equation, edge, or child is accepted because of an inferred intention.

1. **Root initialization is not specified.** I construct every rhombus equation `p_a-p_b+p_c-p_d=0` for every graph 4-cycle, as justified in `PROOFS.md`, and require exact equality with their full row space. I add no chosen triangle orientation, coordinate normalization, or gadget constraint. This supplies an independently proved foundation for the actual root.

2. **“Exactly” for matrix rows versus their representation.** Homogeneous constraints are compared as row spaces, consistent with the explicit child requirement in `FORMAT.md`. All rows must have exactly the graph's vertex count in columns. I compute reduced row bases independently, so changes in basis or harmless dependent rows do not change the mathematical constraint, while missing or additional independent constraints reject. I do not assume that a supplied matrix is already reduced.

3. **L1b has a wire shape but no mathematical definition.** I use the explicit sufficient contradiction criterion `x-omega*y` in the row space and `|omega|^2 != 1`, where `x` and `y` follow the listed edge order. Both conditions are proved from the node data. This is independently sound: taking squared moduli would otherwise give `1=|omega|^2`. The verifier does not try alternative orientations or accept the move label as evidence. Acceptance does not depend on guessing how another checker interprets this undefined label.

4. **L1a and L2 likewise lack mathematical definitions.** L1a is implemented only as the explicit injectivity contradiction that two distinct vertices are forced to coincide. L2 is rejected as unsupported because the supplied texts give no rule for its child edges or rows. Neither occurs in this certificate. This verifier does not claim complete support for every possible record suggested by the move-name list.

5. **Directed-edge sign and undirected graph storage.** I consistently use `x_(u,v)=p_v-p_u`. Graph edges are undirected sets of distinct, in-range labelled vertices, so edge-list ordering and endpoint reversal in graph storage are immaterial. Duplicated graph edges and loops reject. Move edge order and direction are retained in the equations; every cited edge must actually be present. No graph isomorphism or relabelling is allowed.

6. **Graph transitions are not described for all moves.** For L3, the only specified new condition is its orientation equation, so each child's edges must equal its parent's edges exactly. Every visited node is checked; there is no implicit inheritance of omitted data. The unsupported L2 rule is not used to infer or silently add any edge.

7. **Field arrays appear truncated despite the displayed degree-sized notation.** The actual certificate uses arrays such as `[1]`. I allow nonempty arrays of at most the field degree and fill only omitted trailing coefficients with zero, which preserves their exact meaning. Longer and empty arrays reject. Rational scalar shorthand is accepted for a complex element as explicitly allowed; `d`, `re`, and `im` use real-element arrays. Complex objects must include both `re` and `im`.

8. **Irreducibility versus isolation.** I require both irreducibility over Q and exactly one real root in the open rational interval. Rational leading coefficients are normalized algebraically; the polynomial need not arrive monic. Reversed intervals, endpoint roots, and intervals containing zero or multiple roots reject. All inverses use polynomial Euclid, and each computed real-field inverse is checked by multiplication.

9. **The sign of d and degenerate L3 splits.** The text requires real `d`, not positive `d`. Both signs are permissible, but child 0 must use the actual supplied `+i*d`, and child 1 its `-i*d`. If `d=0`, two children would still be required by the stated arity. A complex object in the `d` slot rejects. L1c, although absent here, requires a strictly negative discriminant; zero does not suffice.

10. **Outer JSON record and graph6 details are not fully specified.** I require `verdict: "refuted"` and `witness`, allow the supplied optional `g6` metadata only after verifying it denotes the same labelled graph, and reject other record keys. Field, node, and move objects require their stated keys and reject unknown ones. Duplicate JSON keys, floating-point numbers, nonfinite values, booleans in numeric positions, malformed rationals, malformed graph6 lengths or padding, and multiple graph/certificate records reject. Standard graph6 count encodings and an optional graph6 header are decoded without external packages.

11. **Repeated move edges are not explicitly forbidden.** No distinctness condition is assumed beyond valid edge endpoints. The implemented contradiction and Heron implications remain valid if a displacement is reused; all the same arithmetic and row checks still apply. The supplied L3 and L1b moves use distinct edges. Requiring unsupported additional distinctness would not strengthen the proof of this certificate.

Beyond the four saved controls, **35 additional assertions passed**. These exercised irreducible and reducible polynomials, repeated factors, exact real and complex inverses, interval refinement for close rational comparisons, invalid root intervals, the two actual discriminants, an independent enumeration of the 57 cycles by vertex permutations, swapped L3 branches, added/deleted child constraints, wrong `d`, nonreal `d`, zero Heron coefficients, changed child edges, changed leaf ratios, duplicate graph edges, and rejection of a unit-modulus L1b ratio even when its linear relation holds. These are supplementary checks, not a claim of formal verification of the Python implementation.

Input SHA-256 digests identify the exact graph and certificate checked:

```text
data/23-65.g6
c90a07cd8b4495d5bca46687e8d2c19d43e81ea5dd6b17f7f98eb1a7f3355f0e
data/23-65.certs.jsonl
46f2d3de06f72e37110daf656a5a7a98fd79554049882fa23160232c0617a145
```

Scope is this certificate and its required controls. No embedded witness, gadget claim, reference-checker behavior, or unsupported L2 transition has been certified. The exhaustive irreducibility algorithm is suitable here but is not claimed efficient for arbitrary large-degree fields.

BLIND VERDICT: ACCEPT
