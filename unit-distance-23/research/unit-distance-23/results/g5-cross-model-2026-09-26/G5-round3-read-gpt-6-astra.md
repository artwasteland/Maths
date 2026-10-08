The two fatal reproductions are fixed. Findings 4 and 5 remain incompletely closed. I read the committed code and controls and ran additional tests using in-memory mutations; no files changed.

References below are to **`4d2b1490b`**, under `research/unit-distance-22/`.

**Finding 1 — CLOSED.** `enum/run-dag2.py:729` now calls `prune.verify_outputs`. I confirmed the original keep substitution returns `False`, while the untouched step returns `True`; control C1 also records successful restoration.

**Finding 2 — CLOSED.** `enum/verify-chain.py:225` validates the seed range; `:300` requires the target cell. C2 rejects the zero-cell reproduction and tests the configuration pins.

**Finding 3 — CLOSED.** Count validation and share bounds are enforced at `enum/verify-chain.py:701` and `:783`; missing provenance/shares produce UNRESOLVED through `:959`, `:993` and `:1027`. C3 rejects both impossible partitions. The 383-slice audit correctly reports missing slices and unresolved provenance.

**Finding 4 — NOT CLOSED.** Slice validation, pins and prefix hashes address the original controls, but duplicate-share reconciliation and G4 validation still accept contradictory evidence; see new findings 1–2.

**Finding 5 — NOT CLOSED.** The bound check at `enum/run-dag2.py:691` and file-derived totals fix the reported reproductions. Native-versus-rule count agreement remains incomplete; see new finding 3.

1. **SERIOUS — Duplicate-share acceptance depends on argument order.**

   **Locations:** `enum/verify-chain.py:966`, `:987`.

   Copies are compared by file hashes and cell counts, but their share dictionaries are not reconciled. The partition check selects one copy using `max(..., len(shares))`.

   Reproduction, with all pins and both `--require-*` flags enabled: the normal two-slice fixture records shares **34 + 40 = 74**. Add a duplicate of slice 0 claiming **35**, adjusting its parent total, shard endpoint and matching G4 stage counts. Preserve its archived file hashes and cell counts.

   Original copy first: **coverage OK, exit 3**. Modified copy first: **FAIL, exit 1**. Both copies claim the same prefix, index and modulus, so their differing shares contradict deterministic slicing.

   The same selection also mishandles correct complementary copies: when one records shares `{24,25}` and another `{25,26,27}`, the audit reports share 24 unresolved despite possessing it.

   **Fix:** merge shares per parent cell across copies, rejecting conflicting values.

2. **SERIOUS — Required G4 evidence can explicitly contradict its accepted verdict.**

   **Location:** `enum/verify-chain.py:836` and `:844`.

   The check omits seed-verification results, `all_identical`, and consistency between PASS/EMPTY, replay exit status and whether the slice is empty.

   On the real worker-f01 `s0of1920` records, I set one `seeds[].identical=false` and `all_identical=false`, retaining the PASS label. With all pins and requirements enabled, `summary_audit` returned **no problems and no unresolved items**.

   It likewise accepted an EMPTY/exit-1/zero-sampled-parents claim for that slice, although its recorded `(12,20)` share contains **734 graphs**.

   **Fix:** validate the complete PASS/EMPTY conditions against the detailed replay evidence, including seed failures and emptiness.

3. **MINOR — Native and triangle TU counts can be reassigned without rejection.**

   **Location:** `enum/run-dag2.py:752` and `:758`.

   In slice 1’s 25-record `(13,28)` manifest, change:

   ```text
   counts.tu:        11 → 12
   counts.tri_tu:     1 → 0
   counts.survivors: 14 → 13
   ```

   Leave certificates, ACCEPT, verified counts and `tri_survivors=13` unchanged. **`valid_prune` returns True**, although the file and ACCEPT report one triangle TU.

   Only combined totals are compared. Require each rule-specific native count to equal its file-derived counterpart. This reproduction corrupts count attribution; it does not bypass the repaired keep-file check.
