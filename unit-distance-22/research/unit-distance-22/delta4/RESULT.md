# Lemma D4: a (22,61) unit-distance graph has minimum degree exactly 5

Established 2026-09-05 by claude-reaching-noether-7e1c. This is the first closed piece of the
u(22) programme (CONTRACT gate G4, the delta = 4 branch).

**Statement.** If G is a unit-distance graph on 22 vertices with 61 edges, then every vertex
of G has degree at least 5. Since 2 x 61 = 122 = 5 x 22 + 12, G then has at least ten vertices
of degree exactly 5 (if every degree were at least 6 the edge count would be at least 66).

**Proof.** Degree at most 3 is impossible: deleting such a vertex leaves a unit-distance graph
on 21 vertices with at least 58 edges, but u(21) = 57 (Alexeev, Mixon and Parshall, Theorem
1(a)). Suppose v has degree 4. Then G - v is a unit-distance graph on 21 vertices with 57 =
u(21) edges, so by AMP Theorem 1(c) it is isomorphic to one of the five densest graphs on 21
vertices listed in their ancillary file (`sources/amp/anc/graph6.txt`, the five 21-vertex
lines). Hence G is obtained from one of those five graphs by adding a vertex adjacent to
four of its vertices. There are 5 x C(21,4) = 29,925 such labelled graphs, and 18,689
non-isomorphic ones (nauty 2.8.8 canonical labelling). Every one of the 18,689 contains one
of the 74 minimal forbidden subgraphs of Globus and Parshall as a subgraph, hence is not a
unit-distance graph. Contradiction.

**Evidence, all in this directory.**
- `delta4.py`: the enumeration, canonicalisation and filtering script (networkx + nauty-labelg
  + the `filter/udfilter` module).
- `children-raw.g6` (29,925 labelled children), `children-22-61.g6` (18,689 canonical).
- `filter-verdicts.jsonl`: one certificate per canonical child, verdict "forbidden" for all
  18,689, each with the forbidden-graph index and the injective vertex map.
- `summary.json`: the counts.
- Verification of the witnesses, three ways: the filter's own check; the filter builder's
  independent `verify-witness.py` on a random sample of 300 (0 failures); and a third
  implementation written by the supervisor (in the session transcript, reproduced below) over
  all 18,689 records (18,689 verified, 0 bad), with a negative control in which one map entry
  was duplicated in 50 random records (50 of 50 rejected).

```python
F = json.load(open('../data/forbidden-74.json'))
for r in records:                       # each line of filter-verdicts.jsonl
    adj = graph6_to_adjacency(r['g6']); w = r['witness']; pat = F[w['index']]; m = w['map']
    assert len(m) == 1 + max(max(e) for e in pat) and len(set(m)) == len(m)
    assert all(m[b] in adj[m[a]] for a, b in pat)
```

**What this does not say.** Nothing about the delta = 5 case, which is the bulk of the
programme; and it relies on AMP Theorem 1(a),(c) and on the Globus-Parshall forbidden list
exactly as the rest of the programme does.
