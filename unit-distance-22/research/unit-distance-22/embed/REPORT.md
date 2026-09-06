# WHAT WORKS

`udembed.py` now emits the binding schema from `check/udcheck.py` for both positive and negative certificates. An embedded witness has exactly `field: {minpoly, interval}` and `coordinates`, where every point is an `[x,y]` pair and every field element is an ascending-order coefficient array. Integers are JSON integers and non-integral rationals are canonical `p/q` strings.

A refuted witness has exactly `field` and `tree`. One real number field is constructed for every proof and contains the real and imaginary parts of all matrix entries, move coefficients, ratios and L3 square roots in that proof. Every public node has exactly `edges`, `A`, `move` and `children`. The private L0 wrapper is removed during serialization because the checker initializes the public root from all four-cycle rows itself. Private canonical constraint matrices are serialized as exact complex field elements, and the checker compares their row spaces.

The public moves are:

- L1a: `pair`, with no children.
- L1b: two directed `edges` and `omega`, with no children.
- L2: the reference edge followed by the forced non-edge in `edges`, exact unit-modulus `omega`, and one child.
- L3: three directed `edges`, three nonzero `coefficients`, exact real `d`, and two children. The first private branch was already the `+i*d` branch and remains first publicly. The second is the `-i*d` branch.

Rational certificates use the degree-one field with `minpoly: [0,1]`, interval `[-1,1]`, and selected root 0. Algebraic certificates use an irreducible SymPy primitive element with an exact rational isolating interval. The independent checker redoes irreducibility, isolation, field arithmetic, graph state, row-space, modulus, L3 discriminant and branch checks.

The local `exact_verify.py` accepts the binding embedded schema. `proof_verify.py` retains its old private-tree replay function as `verify_private_refutation`, while its public `verify_refutation` delegates public-schema replay to the binding checker. `selfcheck.py` now mutates a public L3 `d` value.

## Requested checker runs

### 1. K4 refuted

Commands:

```text
printf 'C~\n' | nice -n 10 ~/tools/pyenv-maths/bin/python udembed.py --tries 0 --unknown-file /dev/null > scratch/k4.jsonl
~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null scratch/k4.jsonl
```

Checker final line:

```text
ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=1
```

### 2. All 56 AMP catalog graphs embedded

Commands:

```text
/usr/bin/time -f 'CATALOG_ELAPSED_SECONDS %e' nice -n 10 ~/tools/pyenv-maths/bin/python -u udembed.py ../sources/amp/anc/graph6.txt --unknown-file /dev/null > scratch/catalog-56.jsonl
~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null scratch/catalog-56.jsonl
```

Measured generation output and checker final line:

```text
CATALOG_ELAPSED_SECONDS 65.56
ACCEPT certificates records=56 forbidden=0 tu=0 embedded=56 refuted=0 unknown=0 proof_nodes=0
```

### 3. All 41 refuted forbidden graphs

Generation and extraction commands:

```text
nice -n 10 ~/tools/pyenv-maths/bin/python -u udembed.py ../data/forbidden-74.g6 --tries 0 --max-states 100 --unknown-file scratch/forbidden-unknown.g6 > scratch/forbidden-all.jsonl
~/tools/pyenv-maths/bin/python - <<'PY'
import json
with open('scratch/forbidden-refuted.jsonl', 'w') as out:
    for line in open('scratch/forbidden-all.jsonl'):
        record = json.loads(line)
        if record['verdict'] == 'refuted':
            print(json.dumps(record, separators=(',', ':'), sort_keys=True), file=out)
PY
~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null scratch/forbidden-refuted.jsonl
```

The generated verdict counts were `refuted=41`, `unknown=33`, `embedded=0`. Checker final line:

```text
ACCEPT certificates records=41 forbidden=0 tu=0 embedded=0 refuted=41 unknown=0 proof_nodes=92
```

These 92 nodes include 47 L1a, 5 L1b, 29 L2 and 11 L3 nodes. The proof fields have degree 1 for 38 records and degree 2 for 3 records.

### 4. Dense 22-vertex stress sample

The first attempt used the default 400-state bound. Graph 32 remained in a large deterministic reduction for more than six minutes, so I interrupted it before the ten-minute ceiling. Its partial output was not retained. The clean run used the same `--tries 0 --max-states 100` settings as the 74-forbidden regression and wrote to scratch before installation:

```text
timeout 540 /usr/bin/time -f 'STRESS_ELAPSED_SECONDS %e' nice -n 10 ~/tools/pyenv-maths/bin/python -u udembed.py stress/sample-120.g6 --tries 0 --max-states 100 --unknown-file scratch/stress-unknown.new.g6 > scratch/stress-verdicts.new.jsonl
mv -f scratch/stress-verdicts.new.jsonl stress/verdicts-120.jsonl
mv -f scratch/stress-unknown.new.g6 stress/UNKNOWN.g6
```

Exact measured output and counts:

```text
STRESS_ELAPSED_SECONDS 303.28
INPUTS 120 RECORDS 120 ORDER_MATCH True
COUNTS {'refuted': 119, 'unknown': 1}
```

This is 2.527333 seconds per input graph. The installed file has 120 newline-terminated JSON records and SHA-256 `cb13a74289c600f0d04b6bfaecf2322a021fc17ff25a74415326651111936b0b`. `stress/UNKNOWN.g6` has the one unknown and SHA-256 `97637736d22703c7b76e7d41b51a568a9a1042b2811ab75a7826bc1eb4e90e61`.

Full-file check, including exact graph-list order and the matching unknown file:

```text
timeout 540 ~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --graphs stress/sample-120.g6 --unknown-file stress/UNKNOWN.g6 stress/verdicts-120.jsonl
```

Checker acceptance line, followed by its informational unknown line:

```text
ACCEPT certificates records=120 forbidden=0 tu=0 embedded=0 refuted=119 unknown=1 proof_nodes=121
UNKNOWN U??OiO`PcoSK@AA@`CH?_K?\?Q[CTGGM_A_rUQ?W
```

I also extracted all 119 refuted records to `scratch/stress-refuted.jsonl` and used the requested `/dev/null` form:

```text
timeout 540 ~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null scratch/stress-refuted.jsonl
```

Checker final line:

```text
ACCEPT certificates records=119 forbidden=0 tu=0 embedded=0 refuted=119 unknown=0 proof_nodes=121
```

### 5. Corrupted L3 d mutation

I selected the refutation for `G[dBG{`. Its first L3 node had `d: [0,1]`. I copied that public record to `scratch/mutated-l3-d.jsonl`, changed only that value to `d: [0]`, and ran:

```text
~/tools/pyenv-maths/bin/python ../check/udcheck.py --allow-any-size --unknown-file /dev/null scratch/mutated-l3-d.jsonl
```

The checker exited 1 with:

```text
REJECT: scratch/mutated-l3-d.jsonl:1.witness.tree: L3 d does not square to the recomputed discriminant
```

This goes through the actual public serialization and the binding checker path used for every accepted refutation.

## Integrated regression

Command:

```text
timeout 540 nice -n 10 ~/tools/pyenv-maths/bin/python -u selfcheck.py --jobs 2
```

Key exact output:

```text
AMP_EMBEDDED 56 VERIFIED 56 SECONDS 30.293621
FORBIDDEN_REFUTED 41 UNKNOWN 33 EMBEDDED 0 SECONDS 81.241579
SPECIAL_MOSER EMBEDDED VERIFIED N 7 M 11
SPECIAL_GADGET1_HOST EMBEDDED VERIFIED N 6 M 9
TU_GADGET 1 TARGET 1-5 MOVES L0>L2 TARGET_L2_INDEX 1
TU_GADGET 2 TARGET 4-5 MOVES L0>L2 TARGET_L2_INDEX 1
TU_GADGET 3 TARGET 2-4 MOVES L0>L2 TARGET_L2_INDEX 1
TU_GADGET 4 TARGET 3-7 MOVES L0>L2 TARGET_L2_INDEX 1
TU_GADGET 5 TARGET 6-7 MOVES L0>L2>L2 TARGET_L2_INDEX 2
TU_GADGET 6 TARGET 6-7 MOVES L0>L2 TARGET_L2_INDEX 1
MUTATION_EMBEDDED REJECTED CertificateError
MUTATION_L3_D REJECTED ProofError: witness.tree: L3 d does not square to the recomputed discriminant
MUTATION_TU RED DELETE_EDGE_0-3 TARGET_L2_NOT_REACHED
SELF_CHECK PASS
```

Every check written in `selfcheck.py` was made red on purpose at least once:

1. The embedded-certificate check had 1 added to the first x-coordinate coefficient. The exact verifier rejected the collision or incorrect edge geometry.
2. The public proof check changed a real L3 `d` from `[0,1]` to `[0]`. The binding checker rejected the recomputed square mismatch, as shown above.
3. The TU trace check deleted data edge `[0,3]` from gadget 1 before calling the real greedy trace. The target L2 edge was no longer reached. Restoring the data made the same path pass.

Python compilation was also exercised:

```text
~/tools/pyenv-maths/bin/python -m py_compile udembed.py exact_verify.py proof_verify.py selfcheck.py
```

It exited 0 with no output.

# WHAT DOES NOT

The bounded algorithm still does not refute 33 of the 74 supplied minimal forbidden graphs. It emits these as `unknown`. No false embedding or unsupported refutation is substituted.

The 100-state stress run leaves one of the 120 dense graphs unknown. The default 400-state run was too slow on graph 32 for this task's ten-minute command limit and was stopped cleanly. No result from that interrupted run is claimed.

The 39 dense n at most 21 graphs that AMP rejected after TU filtering were not exercised because their graph6 records are not supplied in `sources/amp/anc/graph6.txt`, `data/`, or another identified programme input. The 41 refuted forbidden graphs are different small graphs and do not satisfy that contract checkpoint.

The 56 positive results remain exact verification of AMP's displayed coordinate set, not 56 independent rediscoveries by randomized search.

`proof_verify.py` is now an adapter to the binding checker for public certificates. It is intentionally not another independent public-schema checker.

# UNCERTAIN

No actual F-free 22-vertex, 61-edge candidate was supplied to this module. The stress graphs all contain a forbidden subgraph, although the embedder did not use that knowledge.

Proofs requiring number fields beyond the degree-2 fields encountered in the 41 forbidden refutations were not produced in this run. The general primitive-element serializer is exact, but high-degree and deeply nested L3 fields remain unmeasured.

The default 400-state behavior across all 120 stress graphs remains unmeasured because graph 32 exceeded the practical bound. The reported 119 to 1 result applies specifically to `--tries 0 --max-states 100`.

Only short graph6 order fields, up to 62 vertices, are implemented. This covers the u(22) programme.

The AMP proposal mapping still reads `sources/amp/anc/graph6.txt` and `sources/amp/tikz.tex` at runtime. Emitted certificates are standalone, but proposal generation depends on those source artifacts.

Wall-clock times were measured on the shared host and are not portable benchmarks.

# PROPOSED CONTRACT AMENDMENTS

Add the 39 AMP-rejected dense graph6 records as a named binding data file. CONTRACT Section 5 requires their replay, but the repository supplies only the 56 embeddable catalog records. Without the missing records, this module cannot distinguish that required set from unrelated generated candidates without reconstructing the complete enumeration and TU-filter pipeline.

# G3 refutation gap (2026-09-05)

## WHAT WORKS

A new `--trace` option writes deterministic search events and a per-graph summary to standard error only. JSONL on standard output is unchanged.

The pre-fix n=17 reproduction used the default `--tries 24 --max-states 400` settings:

```text
TRACE graph=PoDQhOoKIOH@IO@Y?igDU?dk start n=17 m=43 L0_cycles=33 L0_rank=11 max_states=400 tries=24
TRACE state=1 depth=0 stop=no_move_no_embedding
TRACE graph=PoDQhOoKIOH@IO@Y?igDU?dk verdict=unknown states=1 remaining_states=399 max_depth=0 moves={} stops={'no_move_no_embedding': 1} L3_calls=1 L3_triples_tested=80
BASELINE_N17_SECONDS 1036.66
```

The first applicable L3 relation is on edges `[1,5]`, `[1,6]`, `[5,6]`. It is triple 1697 in the old lexicographic order. The private 80-triple cutoff therefore made the solver incorrectly conclude that L3 was exhausted.

The pre-fix n=19 reproduction, with the old cap retained diagnostically, was:

```text
TRACE graph=R??I?cRWdOS`QOPGpoC_@K?{HYOHig start n=19 m=50 L0_cycles=39 L0_rank=14 max_states=400 tries=24 L3_max_triples=80
TRACE state=1 depth=0 move=L3 edges=[[0, 10], [0, 11], [4, 5]]
TRACE state=2 depth=1 stop=no_move_no_embedding
TRACE graph=R??I?cRWdOS`QOPGpoC_@K?{HYOHig verdict=unknown states=2 remaining_states=398 max_depth=1 moves={'L3': 1} stops={'no_move_no_embedding': 1} L3_calls=2 L3_triples_tested=95 embedding_trials=24 embedding_constraints=48
BASELINE_N19_SECONDS 303.63
```

The L3 cap is removed. L3 now classifies the full set of underlying edge triples using exact algebraic-number-field arithmetic. Raw exact minors decide dependence. Actual graph triangles are ordered first so their discriminant 3 reuses a small field. Numerical values order the remaining proposals, and every proposed move is reconstructed exactly. Triples whose three restrictions are already projectively equal are omitted because L1b has already established their pairwise unit-modulus ratios; their L3 split has one row-space-identical child and cannot strengthen that child. Direction reversal and triple permutation only rescale or permute the relation and exchange the two signs.

L0 was already complete: every 4-cycle is collected initially, new 4-cycles are collected after every L2, and the combined constraints determine the full row space. L1a already tests every vertex pair. L1b and L2 already test every underlying pair of edges, with directed reversals absorbed by the exact ratio. Move priority remains exhaustive L1, then L2, then L3.

The n=19 counterexample is now refuted in 36.44 seconds with 15 proof nodes:

```text
TRACE graph=R??I?cRWdOS`QOPGpoC_@K?{HYOHig verdict=refuted states=15 remaining_states=385 max_depth=3 moves={'L3': 7, 'L1b': 8} stops={'contradiction': 8} L3_calls=7 L3_triples_tested=305 L3_negative_discriminants=0
TRIANGLE_N19_SECONDS 36.44
ACCEPT certificates records=1 forbidden=0 tu=0 embedded=0 refuted=1 unknown=0 proof_nodes=15
```

This changes n=19 from an unknown after 303.63 seconds to a checker-accepted refutation after 36.44 seconds.

Current regression results are:

```text
CATALOG_SECONDS 15.10
56 embedded
ACCEPT certificates records=56 forbidden=0 tu=0 embedded=56 refuted=0 unknown=0 proof_nodes=0
TRIANGLE_FORBIDDEN41_SECONDS 22.35
41 refuted
ACCEPT certificates records=41 forbidden=0 tu=0 embedded=0 refuted=41 unknown=0 proof_nodes=108
SELF_CHECK PASS
```

The required deliberate failure was run before acceptance testing. It exited 1 with:

```text
REJECT: embed/scratch/mutated-l3-d.jsonl:1.witness.tree: L3 d does not square to the recomputed discriminant
```

The final self-check also rejected its embedded-coordinate mutation and its L3-d mutation.

## WHAT DOES NOT

The full exact L3 scan reaches the following n=17 leaf in 9.35 seconds, including with the default 24 embedding tries because the exact obstruction now suppresses the futile randomized fallback:

```text
TRACE state=1 depth=0 move=L3 edges=[[1, 5], [1, 6], [5, 6]] discriminant=3
TRACE state=2 depth=1 move=L3 edges=[[1, 10], [1, 11], [10, 11]] discriminant=3
TRACE state=3 depth=2 move=L3 edges=[[1, 5], [1, 10], [3, 4]] discriminant=11/9
TRACE L3_negative edges=[[0, 1], [0, 2], [1, 5]] relation=['1', '-1', '-sqrt(33)/12 + 11/4 + sqrt(11)*I/4 + 11*sqrt(3)*I/12'] discriminant=-77
TRACE state=4 depth=3 stop=negative_heron_unrepresentable
TRACE graph=PoDQhOoKIOH@IO@Y?igDU?dk verdict=unknown states=4 remaining_states=396 max_depth=3 moves={'L3': 3} stops={'negative_heron_unrepresentable': 1} L3_calls=4 L3_triples_tested=13164 L3_negative_discriminants=41
TRIANGLE_N17_SECONDS 9.35
```

This is a proof of non-embeddability mathematically, but it cannot be serialized in the binding schema. The blind checker requires an L3 witness to contain a real field element `d`, verifies `d^2 = discriminant`, and explicitly rejects a negative discriminant. L1a and L1b cannot encode this leaf because no vertex difference is zero and no two edge differences are forced proportional with unequal modulus.

The requested G3 PASS is therefore not attainable without changing the checker contract. The embedder continues to report n=17 as `unknown`; it does not emit an unverifiable proof node.

### Proposed negative-Heron contradiction leaf

Add a checker-supported L1 variant, for example `L1c`, with fields `edges` and `coefficients`. For forced edge displacements `x,y,z` and nonzero coefficients `a,b,c`, the checker would verify exactly that

```text
a*x + b*y + c*z is in rowspace(A)
Delta = 4*|a|^2*|b|^2 - (|a|^2 + |b|^2 - |c|^2)^2 < 0.
```

If a unit-distance embedding existed, `a*x`, `b*y`, and `c*z` would be the directed sides of a triangle of lengths `|a|`, `|b|`, and `|c|`. The Heron-like lemma gives `Delta = d^2 >= 0`, a contradiction. This is the negative-discriminant case adjacent to AMP's L3 rule. The n=17 leaf above has `Delta = -77`. No square root or new field extension is needed for this leaf, only exact sign separation already implemented by the checker for L3.

Per the brief, this move has not been added to emitted certificates because `check/udcheck.py` cannot verify it.

An earlier experiment that allowed row-space-identical rank-one L3 splits hit the old global 400-node budget after 817.66 seconds at depth 307. Those splits only recreate the surviving state and are not a finite substitute for the missing negative-Heron contradiction. The documented global state limit remains in force.

## UNCERTAIN

The requested default four-cell gate was run twice. Both runs completed n=16 and n=17, then the eighteenth n=18 survivor remained inside one exact state for more than sixteen minutes in the first ordering. A direct trace identified repeated primitive-field construction after unrelated-radical L3 proposals as the bottleneck. Triangle-first ordering removed that single-state stall and reached state 39 on the same graph, but the symmetric exact proof tree was still too slow for the available time. The task-owned diagnostic was stopped without a record, so no default n=18 gate line is claimed.

The completed default gate cells were:

```text
OK   n=16 m=41: survivors=1 (expect 1), embedded=1 (expect 1), refuted=0, unknown=0, dups=0, known-among-survivors=1/1, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
FAIL n=17 m=43: survivors=8 (expect 8), embedded=7 (expect 7), refuted=0, unknown=1, dups=0, known-among-survivors=7/7, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
OK   n=19 m=50: survivors=5 (expect 5), embedded=3 (expect 3), refuted=2, unknown=0, dups=0, known-among-survivors=3/3, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
GATE G3: FAIL
```

A separate n=18 diagnostic with `--max-states 1` checked survivor counts, the 16 catalog embeddings, two immediate refutations, and checker behavior:

```text
FAIL n=18 m=46: survivors=38 (expect 38), embedded=16 (expect 16), refuted=2, unknown=20, dups=0, known-among-survivors=16/16, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
GATE G3: FAIL
```

This diagnostic line is not a substitute for the requested default n=18 gate result.
