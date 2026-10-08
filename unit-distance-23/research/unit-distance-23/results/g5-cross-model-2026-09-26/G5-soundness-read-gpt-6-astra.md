1. **FATAL — the stranger’s replay does not establish exhaustive coverage.**

   [verify-chain.py:236](<repo>/research/unit-distance-22/enum/verify-chain.py:236) obtains the levels to inspect directly from `summary["levels"]`. It never requires this list to equal the levels prescribed by the recomputed reach table. Furthermore, [line 348](<repo>/research/unit-distance-22/enum/verify-chain.py:348) restricts “allowed” parents using windows supplied by that same summary, without independently validating those windows.

   **Concrete counterexample:** I reconstructed, entirely in memory, the existing `c-16-41-f398-tri` control with `(15,37)` omitted and the level-15 window narrowed to `[36,36]`. I adjusted the affected descendant files and manifest hashes to describe the resulting empty target. The structural replay returned **`CHAIN OK`**. All **638 remaining certificates** independently verified using the actual checker functions: 19 triangle certificates and 619 legacy records.

   This loses the [known 16-point, 41-edge graph](<repo>/research/unit-distance-22/enum/test-triangle/data/amp-known56.g6:24). Its minimum degree is 4; I checked that every minimum-degree deletion gives the omitted `(15,37)` graph. Thus a genuine solution disappears without any invalid certificate being needed. Certificate replay cannot recover a missing construction branch.

   I also reproduced the simpler bypass: removing all 12 pruned-level entries from that run’s summary made **`verify-chain.py --check` return `CHAIN OK`, with `certs_replayed: 0`**, while `completed_through_n` still said 16. This contradicts [RHOMBUS-SPEC’s promise to replay “every certificate file”](<repo>/research/unit-distance-23/RHOMBUS-SPEC.md:178).

   **Required repair:** derive the required cells and parent choices independently from the validated target and reach table; require complete coverage. Partial replay must be explicitly distinguished from exhaustive validation. This is an inherited coverage defect that compromises the new replay guarantee.

2. **MAJOR — resume trusts cached success without validating checker provenance or target.**

   [run-dag2.py:620](<repo>/research/unit-distance-22/enum/run-dag2.py:620), `valid_prune`, checks status, flags and file hashes, but ignores the manifest’s target, checker identity, ACCEPT line and verified counts. [The resume branch](<repo>/research/unit-distance-22/enum/run-dag2.py:661) then returns without replaying certificates.

   **Reproduction:** in memory, I changed a successful manifest’s target to `[23,64]`, emptied its checker result and verified counts, and replaced its recorded checker hash with zeros. `valid_prune` still returned `True`.

   Consequently, results produced using the development checker override in [prune.py:233](<repo>/research/unit-distance-22/enum/prune.py:233), or an obsolete checker, can survive a production resume without current validation. A complete independent replay would catch invalid certificates or the target mismatch; objection 1 undermines that fallback. Resume should validate the target and approved checker provenance, or replay the cached certificates.

**Verdict:** I would withhold G5 approval for the end-to-end trust chain because of objection 1. I found **no unsound acceptance by either new mathematical checker**.

I checked Lemmas R and T, including degeneracies; R1/R2; induced-ancestor heredity; the exact consumption of \(65+1>u(23)\); and trees whose leaves force different non-edges. Those arguments hold. The reach-table values also recomputed correctly.

I inspected ordering, chunk boundaries, EOF/count checks and rejection handling in fresh pruning. Runtime attacks covered zero scales, degenerate targets, booleans/floats, negative indices, missing children, unsorted triangles and integer overflow. On 1,200 exactly embedded lattice graphs, neither prover refuted an embedding, and every TU result reached a genuine missing unit edge.

No files were modified.