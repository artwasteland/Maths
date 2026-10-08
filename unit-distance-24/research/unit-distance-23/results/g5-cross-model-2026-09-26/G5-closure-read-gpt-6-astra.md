**Both objections are only partially closed. I reproduced two fatal acceptance failures.** The proposed archive-only audit is insufficient to certify nonexistence.

I loaded the new code directly from `4120dd63c` and tested it using in-memory file overlays. No files were modified. All code locations below refer to that commit; paths are relative to `research/unit-distance-22/`.

1. **FATAL — Resume can discard a graph whose unchanged, accepted certificate says `unknown`.**

   **Locations:** `enum/run-dag2.py:708`, `:714`, `:725`; compare `enum/prune.py:903` and `enum/verify-chain.py:456`.

   `valid_prune` checks hashes and record counts, but never reconstructs the required keep file from the certificate verdicts.

   Concrete reproduction using the existing `dag-16-41-L12-tri-s0of2` fixture’s `(13,29)` cell:

   - Remove `Lj??GPNHOetaeb` from its keep file.
   - Insert the input’s TU graph `L?Kw_fbaaKpIPR`, preserving input order.
   - Update only the keep file’s hash in the prune manifest.

   The input still has seven records and the keep file six. **Every certificate, the genuine ACCEPT line, UNKNOWN file, checker hash and count remain unchanged.** New `valid_prune` returns **True**.

   The removed graph is the canonical ancestor of AMP’s known `(16,41)` graph, along
   `(16,41) → (15,37) → (14,33) → (13,29)`. I verified that ancestry and matched the root against the repository’s AMP data.

   The committed G4 keep-stage check also returns `ok: True`: the replacement remains a subsequence of the input (`enum2/replay-398.py:583`). Conversely, the existing `prune.verify_outputs` immediately rejects it.

   **Closure:** run that structural verification before reusing a prune step. A genuine certificate ACCEPT does not certify the subsequently consumed keep file.

2. **FATAL — The full verifier can print CHAIN OK after checking zero cells.**

   **Locations:** `enum/verify-chain.py:186`, `:250`, `:405`, `:418`.

   `seed_n` is not range-checked. Set the target to `(23,65)` and the seed to `24`, consistently across the three metadata files. Use root `k=5`, the justified `ubar(22)=60`, singleton target windows/reach table, an empty `levels` list, and `completed_through_n=23`.

   The required-cell expression becomes `range(24,24)`. With pruning, triangles, stage verification and `--check` enabled, I obtained:

   ```text
   "required_cells": 0, "certs_replayed": 0, "coverage": "exhaustive"
   COVERAGE exhaustive: all 0 required cells of (23,65) present and checked ...
   CHAIN OK
   ```

   Exit status was **0**.

   The driver already rejects invalid seed ranges at `enum/run-dag2.py:222`; the independent verifier omitted that validation.

   **Closure:** validate the seed range, require the target cell in the required set, and pin the production seed independently of submitted metadata.

3. **SERIOUS — Summary-only accepts missing parent provenance and even impossible slice partitions.**

   **Locations:** `enum/verify-chain.py:658`, `:698`, `:769`, `:772`, `:775`.

   A resumed cell without recoverable history skips its parent/source/shard checks. Missing slice-share records produce notes rather than failure. A cell with no recorded shares is absent from the partition loop altogether.

   Reproduction on the two-slice `(16,41)` fixture:

   - Mark slice 1’s level-13 entries resumed, with no parent history.
   - Make slice 0 claim **75 records** from the `(12,24)` stage, whose complete file contains **74**.
   - Adjust its recorded parent total and shard endpoint accordingly.

   The tool printed:

   ```text
   ... the -1 records ... are theirs unchecked
   COVERAGE (summary only) OK ...
   CHAIN PARTIAL ...
   ```

   It also accepted fully recorded shares **80 and −6**, because their sum is 74. Source-record counts lack nonnegative-integer validation.

   The missing-history limitation is acknowledged at `enum/PRUNING.md:661`. The negative remainder demonstrates an additional failure: **even a contradiction visible in the retained records does not fail the audit.**

   **Closure:** unresolved required provenance must prevent coverage approval; validate count domains and require a share record for every required slice-level cell and slice.

4. **SERIOUS — Fleet completeness is based on unchecked declarations and cardinalities.**

   **Locations:** `enum/verify-chain.py:723`, `:732`, `:744`, `:753`, `:763`.

   There is no validation of slice-count/index bounds. I supplied only the fixture’s empty-target slice, declared its slice as `[12,0,0]`, and marked its first post-slice cells resumed. The audit reported **summary-only OK**, zero target children, and an empty partition report. The slice containing the known `(16,41)` graph was missing.

   With a valid count held fixed, ordinary missing indices and missing required-cell entries **do fail**; I reproduced both controls. Identical duplicate archive copies are also correctly deduplicated.

   However, shared prefixes and duplicate copies are compared only by counts. Summary-only never reads `hashes.json` or G4 reports. It cannot distinguish disjoint shares `{A,B}` and `{C,D}` from two shares both containing `{A,B}` when their recorded cardinalities agree.

   G4 does rederive slice files, but merely collecting its PASS verdicts does not bind those checked slice identities to the inventory being approved.

   **Closure:** independently pin `(23,65)`, level 12 and count 1,920; bind each index to its G4 slice records and common-prefix hashes. Cardinality sums alone cannot establish disjointness.

5. **SERIOUS — The new resume agreement checks remain incomplete.**

   **Locations:** `enum/run-dag2.py:671`, `:688`, `:699`; target guard at `enum/prune.py:923`.

   I reproduced these additional accepted cases:

   - Changing the manifest’s native `counts.tu` alone to an inconsistent value.
   - Changing both ACCEPT’s `tu` and `verified_counts.tu` to **999 for a 25-record certificate file**.
   - Setting both the requested and recorded target to `(16,40)`, below the proved bound 41.

   The first two pass because native TU/refuted counts and the complete verdict partition are not reconciled. The third passes because target equality substitutes for checking the TU bound; returning through resume bypasses `prune.py`’s guard.

   The advertised single-field target mismatch and missing-ACCEPT controls do reject, as intended. These remaining cases require stronger consistency checks. The below-bound case does not itself undermine the correctly configured `(23,65)` target.

6. **FATAL for the proposed final certification — The retained artifacts cannot close the intermediate keep-file gap.**

   **Locations:** summary inputs at `enum/verify-chain.py:592`; prune-summary checks at `:649`; G4 keep semantics at `enum2/replay-398.py:521`, `:583`.

   The proposed combination cannot establish that every intermediate keep file actually consumed by augmentation was exactly the set permitted by its checked certificates. Finding 1 demonstrates this **with genuine, unchanged certificate acceptance**, so the statement that workers checked the certificates does not resolve it.

   Top-cell rechecks cannot recover a counterexample lost at an intermediate ancestor. G4 samples generation from recorded parents and accepts arbitrary keep subsequences. The new resume guard is also not retroactive to the fleet’s old driver.

   **Cheapest closure while files survive:** perform the existing structural `verify_outputs` check on reused stages, enforce target/checker provenance, and run the corrected full chain audit before deletion. Retain a report binding the checked files, target, slice and checker versions.

   Recheck surviving shared prefixes once per distinct content hash. For already-deleted intermediate stages lacking equivalent evidence, **there is no metadata-only check that recovers the missing certificate-to-keep relationship**. Restore or regenerate the affected stages/slices, propagating any changed keep set through its descendants. The archive can support coverage crosschecks, but cannot independently establish the claimed nonexistence as presently proposed.

**Objection 1 — PARTIALLY CLOSED:** target-derived cells and parents are implemented (`verify-chain.py:216`, `:250`, `:254`, `:269`), but the empty-required-set acceptance and summary-only coverage gaps remain.

**Objection 2 — PARTIALLY CLOSED:** target/checker/ACCEPT checks are added (`run-dag2.py:671`, `:674`, `:685`), but a cached step can still discard a known counterexample ancestor despite its accepted `unknown` certificate; the existing fleet receives no retroactive protection.
