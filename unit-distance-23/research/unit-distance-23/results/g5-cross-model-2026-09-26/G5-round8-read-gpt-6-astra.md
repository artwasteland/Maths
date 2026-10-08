**Round-7 finding: CLOSED.** At `a3a38e37f6`, `research/unit-distance-22/enum/verify-chain.py:1131–1158` merges the evidence, and **1177–1184** checks every replay row against it. Independent tests confirm rejection in both argument orders and UNRESOLVED when no supporting copy exists.

1. **SERIOUS — Float/boolean parent counts bypass the sampling bound.**  
   At `verify-chain.py:1012–1015`, an invalid parent-count type skips the oversampling check rather than causing rejection. The merged comparison at **1182** then accepts Python’s numeric equality: `31127.0 == 31127` and `False == 0`.

   **Reproduction:** In the real `f01-jjpzl7/s0of1920` replay, change `(11,17)` to:
   ```json
   {"parents_in_cell": 31127.0, "sampled": 31128}
   ```
   Update the corresponding sampled totals in `per_level`, the replay summary and fingerprint; leave production evidence unchanged.

   I reproduced **zero additional problems and zero unresolved items**. Using integer `31127` instead correctly reports oversampling. Thus an encoding change permits an impossible sample exceeding its population.

   The same hole also accepted a fabricated single sample from the real target cell’s zero parents when `parents_in_cell` was `false` or `0.0`; integer `0` was rejected. These tests retain only the fixture’s expected missing-slice failure.

   Require a nonnegative integer parent count, excluding booleans, before applying either comparison.

Minor issues: none reported.

**G5: OPEN — malformed count types allow mathematically impossible G4 sampling evidence to pass.**
