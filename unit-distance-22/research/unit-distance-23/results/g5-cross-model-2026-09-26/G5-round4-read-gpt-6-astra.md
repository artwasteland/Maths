All locations refer to **768cc0930**, with `enum/` and `enum2/` under `research/unit-distance-22/`. Reproductions ran entirely in memory.

- **Duplicate-share reconciliation: CLOSED.** `enum/verify-chain.py:1058–1081` merges every copy’s shares and rejects conflicts. C6 records rejection in both argument orders and acceptance of complementary copies.
- **G4 evidence vs label: NOT CLOSED.** The original C7 attacks are rejected, but contradictory detailed evidence still passes, as reproduced below.
- **Rule-specific counts: CLOSED.** `enum/run-dag2.py:757–765` independently reconciles both rule-specific counts with certificate records. C8 records the untouched case passing and the reassignment failing.

New findings:

1. **SERIOUS — G4 still accepts explicit failures hidden beneath successful aggregate fields.**  
   `enum/verify-chain.py:675`, `:692`, and `:705` trust `mismatching_parents` and `red_all` without reconciling the detailed evidence.

   Reproduction using the real `f01-jjpzl7/s0of1920` record: change only `replay/summary.json`’s `per_cell[0]["mismatches"]` to `1`. Alternatively, change only `red_controls[0]["went_red"]` to `false`. Leave the aggregates and fingerprint unchanged. **Each mutation passes `summary_audit` with zero problems and zero unresolved items**, retaining G4 `PASS`.

   Derive and reconcile the aggregates from the detailed records before accepting the verdict.

2. **SERIOUS — Genuine empty slices are rejected.**  
   `enum/verify-chain.py:687–703` requires `all_identical == true` before reaching its `EMPTY` branch. But `enum2/replay-398.py:724` defines that field using `bool(entries)`: zero sampled parents necessarily produce `false`.

   Reproduction: generate a summary with the producer’s `summarize([], …)`, successful stage checks, zero parents in every required cell above the slice level, zero shares, and fingerprint `{mode: "slice", result: "EMPTY", replay_exit: 1}`. `g4_verdict` returns **`FAIL: all_identical False`**. This is precisely the legitimate empty case supported by `coordination/cloud-workers/u23-slice.sh:480–487`.

   Handle verified emptiness separately from the positive-sample requirement; add a positive EMPTY control.

Minor issues: none reported.

**G5: OPEN — contradictory G4 evidence remains accepted, and valid empty slices are rejected.**
