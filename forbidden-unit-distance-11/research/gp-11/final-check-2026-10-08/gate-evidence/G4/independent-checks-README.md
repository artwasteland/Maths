# GP-11: independent checks after the result (2026-10-07)

GP-10's independent checks (`research/gp-10/INDEPENDENT-CHECKS.md`), rebuilt for B11 and run on the sealed complete
assembly (`<repo>/b11-endgame/assembly-1/records.jsonl`, sha256 41731c98...). None imports or runs the
frozen checkers. Tools: `research/gp-11/tools/independent/` (built by a Codex builder from the written specification;
its REPORT.md names the one place it read schema documentation) and `research/gp-11/blind-verifier/` (built by a Claude
agent, written blind). A generated summary, with the comparison against the frozen checker's own L11, follows when the
final check finishes.

| check | what it does | result |
|---|---|---|
| 1. independent audit (`audit/`) | coverage, verdict counts, every exact embedding checked in exact arithmetic, every pointer resolved, L11 derived from actual edge deletions (vertex deletions and non-biconnected deletions by GP-10's theorem and block gluing), upward closure checked against the refuted set | PASS, no alarms: embedded 443,444, refuted 5,264, **L11 = 2,833** (`audit/L11.g6`, sha256 498ac6bf...); inside PREDICTIONS.md's registered ranges |
| 2. red on purpose (`redteam/`) | 8 mutations of the records and the claim | 8 of 8 caught (coordinate + 1e-40, refuted flipped to a fake embedding, record dropped, record duplicated, non-injective pointer, a minimal graph's subgraph status changed, a minimal member dropped, a duplicate isomorph) |
| 3. trying to embed L11 anyway (`embed/`) | 16,384 numerical attempts per L11 graph (2,048 starts x 8 rounds, seed 20261007, 60-digit refinement) | NO_COUNTEREXAMPLE_FOUND for all 2,833; controls: every member minus an edge, and a matched embedded B11 graph per member, all embedded (2,833 and 2,833). A search is not a proof; it is a check that nothing slipped through |
| 5. a second verifier, written blind (`../blind-verifier/`) | every refutation certificate re-verified from the spec by another model family | ALL 5,264 ACCEPT, coverage complete |
| 6. polynomial identities without FLINT (`modp/`) | every identity of every refuted certificate at 3 random points modulo 2^61-1 and 2^127-1, in Python integers | PASS: 86,987 identities per point, every red control red |

Check 4 (a second certificate of a different type) is outside this round.
