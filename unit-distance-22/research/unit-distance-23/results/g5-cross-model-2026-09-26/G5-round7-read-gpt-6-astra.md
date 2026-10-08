**Round-6 finding: CLOSED.** At `57daa7c14`, `research/unit-distance-22/enum/verify-chain.py:763–768` defers incomplete EMPTY evidence, and lines **1120–1149** resolve it across copies. C12 confirms acceptance in both orders and rejection of missing or contradictory evidence.

1. **SERIOUS — Resumption bypasses the new G4 parent-count check.**  
   `verify-chain.py:1004–1009` compares replay rows only with **local** parent evidence. The fleet merge never rechecks those rows against evidence supplied by another copy.

   **Reproduction:** Take two copies, A and B, of the real `f01-jjpzl7/s0of1920` record. In A:
   - Apply C12’s mutation: change `(11,17)`’s `parents_in_cell` from **31,127 to 31,128**, adjusting `per_level.parents` accordingly.
   - Mark that summary cell resumed and remove its parent fields, exactly as the driver does. Leave B untouched.

   With the fleet pins and required hashes/G4, I reproduced **zero additional problems and zero unresolved items**, in both argument orders. Both G4 labels remain PASS. The only reported failure is the fixture’s expected 1,919 missing slices.

   Without the resumed marker, the same mutation is correctly rejected. With it, the audit overlooks explicit contradictory evidence already supplied by B. This uses the fleet’s real data and supported resume/copy workflow.

   Reconcile replay rows against merged parent evidence, including shared-prefix evidence; unresolved bindings must remain unresolved.

Minor issues: none reported.

**G5: OPEN — resumed cells can bypass G4 parent-count reconciliation despite contradictory evidence in another copy.**
