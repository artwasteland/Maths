All references are to **7b3edd5c0**; paths below are relative to `research/unit-distance-22/`. Reproductions ran in memory.

- **Aggregates reconciled with details: CLOSED.** `enum/verify-chain.py:697–746` recomputes and reconciles the aggregates. I independently reproduced C9: both mutations fail; the untouched real slice passes.
- **Genuine EMPTY slices accepted: NOT CLOSED.** The original `all_identical` problem is fixed, and C10’s fresh EMPTY cases pass. A supported resume/history case still fails.

1. **SERIOUS — EMPTY validation ignores successfully recovered parent records.**  
   `summary_audit` recovers a resumed cell’s original parent evidence at `enum/verify-chain.py:855–862`, but replaces only local variable `e`. At line **961**, it passes the original `entries` to `g4_verdict`, whose line **755** treats every resumed entry as unconfirmed.

   **Reproduction:** Take C10’s valid empty `s4of128`. Preserve its fresh summary as `history/original.json`, listed in `history/INDEX.json`. In the current summary, mark `(13,28)` resumed and remove its parent fields, exactly as the driver does on resume. Keep all graph counts and G4 evidence unchanged.

   The fresh version passes. The resumed version reports `recovered: {"original": 1}`, zero unresolved items, and every share zero—but rejects G4 with:
   ```
   ... slice that is not shown empty ...
   unconfirmed [[13, 28]]
   ```
   I reproduced this using the actual 102-record prefix, confirming slice 4 contains zero graphs.

   The EMPTY decision must use the validated, recovered parent evidence.

Minor issues: none reported.

**G5: OPEN — valid EMPTY slices with complete resume history are rejected.**
