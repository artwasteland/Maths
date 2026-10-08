**Round-5 finding: CLOSED.** At `cca1769c8`, `research/unit-distance-22/enum/verify-chain.py:888` retains recovered parent evidence, line **971** passes it to G4, and lines **760–763** use it for EMPTY. Independent in-memory tests confirm C11’s positive case passes and both reds fail.

1. **SERIOUS — EMPTY is decided before complementary copies’ evidence is combined.**  
   `verify-chain.py:971–974` permanently records a G4 failure for each incomplete copy. Later, lines **1087–1124** successfully reconcile those copies’ parent coverage and shares, without reconsidering EMPTY.

   **Reproduction:** Make two copies of C10’s valid `s4of128`, preserving identical hashes, counts and replay evidence. Using the driver’s resumed representation:
   - Copy A resumes `(13,29)` and `(13,30)`.
   - Copy B resumes `(13,28)`.
   - Neither has history; every required parent record remains fresh in the other copy.

   Audit both together. I reproduced **zero unresolved parent/share items**, but two additional G4 failures: A reports `unconfirmed [[13,29],[13,30]]`; B reports `unconfirmed [[13,28]]`. Both argument orders fail. These errors are additional to the partial fixture’s expected missing-slice error.

   This defeats the supported complementary-copy reconciliation for EMPTY slices. Finalize EMPTY after validated evidence from matching copies has been merged.

Minor issues: none reported.

**G5: OPEN — complementary copies of a valid EMPTY slice are rejected despite collectively complete evidence.**
