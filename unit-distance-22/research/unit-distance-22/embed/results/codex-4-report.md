# Brief 4 report

## gate-g3.py

```text
OK   n=16 m=41: survivors=1 (expect 1), embedded=1 (expect 1), refuted=0, unknown=0, dups=0, known-among-survivors=1/1, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
OK   n=17 m=43: survivors=8 (expect 8), embedded=7 (expect 7), refuted=1, unknown=0, dups=0, known-among-survivors=7/7, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
OK   n=19 m=50: survivors=5 (expect 5), embedded=3 (expect 3), refuted=2, unknown=0, dups=0, known-among-survivors=3/3, extra-embedded=0, missing-embedded=0, known-refuted=0, checker=ACCEPT
GATE G3: PASS
```

## Gate self-test

```text
FAIL (as required) n=17 m=43: survivors=7 (expect 8), embedded=7 (expect 7), refuted=0, unknown=0, dups=0, known-among-survivors=6/6, extra-embedded=1, missing-embedded=0, known-refuted=0, checker=ACCEPT
FAIL (as required) corrupted coordinate in the n=16 certificate: REJECT: <repo>/research/unit-distance-22/gate-g3-work/mutation-16.jsonl:1: invalid J
SELF-TEST PASS
```

## Checker self-test

The four new L1c mutations were all red: 4/4 rejected for a nonnegative discriminant, a relation outside the row space, a zero coefficient, and forbidden children. The positive n=17 graph-state certificate was accepted with 15 proof nodes, including eight L1c leaves. The complete checker summary was:

```text
SELFTEST PASS checks=41 positive=18 rejected_mutations=23
```

## Unified diff of check/udcheck.py

```diff
--- check/udcheck.py.before-task4
+++ check/udcheck.py
@@ -24,6 +24,7 @@
 
     {"kind":"L1a", "pair":[u,v]}
     {"kind":"L1b", "edges":[[u,v],[x,y]], "omega": complex}
+    {"kind":"L1c", "edges":[[u,v],[x,y],[p,q]], "coefficients":[a,b,c]}
     {"kind":"L2",  "edges":[[u,v],[x,y]], "omega": complex}
     {"kind":"L3",  "edges":[[u,v],[x,y],[p,q]],
                        "coefficients":[a,b,c], "d": element}
@@ -650,6 +651,26 @@
                 child_graph = Graph(graph.n, new_edges)
                 next_rows = [*rows, *four_cycle_rows(child_graph, field)]
                 visit(children[0], child_graph, next_rows, node_where + ".children[0]", depth + 1)
+        elif kind == "L1c":
+            exact_keys(move, {"kind", "edges", "coefficients"}, where=node_where + ".move")
+            if children:
+                fail(f"{node_where}: L1c contradiction must be a leaf")
+            es = move["edges"]
+            cs = move["coefficients"]
+            if not isinstance(es, list) or len(es) != 3 or not isinstance(cs, list) or len(cs) != 3:
+                fail(f"{node_where}.move: L1c needs three edges and three coefficients")
+            directed = [directed_edge(e, current, f"{node_where}.move.edges[{i}]") for i, e in enumerate(es)]
+            coeff = [parse_cx(field, c, f"{node_where}.move.coefficients[{i}]") for i, c in enumerate(cs)]
+            if not all(coeff):
+                fail(f"{node_where}: L1c coefficients a,b,c must each be nonzero")
+            base = relation_row(field, graph.n, list(zip(coeff, directed)))
+            if not in_rowspace(base, rows, graph.n):
+                fail(f"{node_where}: L1c three-edge relation is not a consequence of A")
+            a, b, c = coeff
+            aa, bb, cc = a.norm2(), b.norm2(), c.norm2()
+            discriminant = 4 * aa * bb - (aa + bb - cc) * (aa + bb - cc)
+            if field.sign(discriminant) >= 0:
+                fail(f"{node_where}: L1c discriminant is not negative at the selected real root")
         elif kind == "L3":
             exact_keys(move, {"kind", "edges", "coefficients", "d"}, where=node_where + ".move")
             es = move["edges"]
```

## Uncertainty

The only procedural uncertainty is that this checkout's `gate-g3.py` returns immediately after `--self-test`, so the supplied combined command cannot also print the normal n=16, n=17, and n=19 cells or write the JSON report. I ran the supplied command unchanged for the self-test lines, then ran the same command without `--self-test` to produce the three gate lines and `gate-g3-work/report-task4.json`. The supervisor's `gate-g3-work/run-18.txt` and the only matching n=18 unknown file were both empty, so there were no n=18 graphs to trace and I did not start another n=18 run.
