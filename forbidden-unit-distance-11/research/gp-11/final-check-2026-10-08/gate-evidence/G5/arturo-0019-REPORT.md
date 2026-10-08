# Task 0019: hostile referee report on the 11-vertex profile of the proof checker

Referee: Arturo (Kimi k3, non-Claude family), on the waste-drop line, under gate G5.
Date: 2026-10-01. Method: five legs, mirroring task 0018. (0) A personal line-by-line read
of `gp11check.py` (432 lines) against the frozen `gp10check.py` (1,028 lines, sha256 pin
verified) before any strand ran, plus a full read of the GP-11 CONTRACT, PROOFS and FORMAT
against their GP-10 counterparts. (A) Pure-mathematics adjudication of every argument in
GP-11 PROOFS.md, attacking each claim by trying to construct the counterexample first.
(B) Independent code-against-proof second pass with live execution. (C) Adversarial
empiricism: fixture runs, a mutation test, and a forged-certificate attempt through the
genuine profile CLI. (D) Data integrity and anchors: all sha256 pins, the 398-list structure,
minimality as an antichain, canonical forms via nauty, the gadgets and the AMP list, and the
geng census ladder. Strand working papers ship with this report as A-maths.md, B-code.md,
C-adversarial.md, D-data.md.

## VERDICT

**The profile is sound. No BLOCKER, no MAJOR.** I could not construct, and no strand could
construct, an input the profile accepts that the soundness proofs do not justify, nor any
rejection the proofs require that the code omits. The lower-order premise is not circular in
any channel; the order-10 block search, the limit-9 B10 control, and the verdict replay of
controls are all live and load-bearing, and the one mutation that would matter (the inherited
search default of 9 silently clamping the block search) is proven to flip a real rejection
into a false acceptance, which is exactly why the explicit limits as shipped are the whole
game and why they are correct. All five example failure modes in the task brief are refuted.
Two MINORs, both fail-closed, one a bundle packaging gap, each with a stated fix. The gate
question, in the contract's grading: could a false result be accepted? Not found, across four
audit legs and six live experiments.

## FINDINGS

### MINOR-1 (B and C converge): the shipped referee bundle cannot self-run; two declared review-surface files are absent

`source_hashes()` digests, beyond the six pins and the two documents, `gp-11/tools/write_result.py`
and `gp-11/check/selftest.py`. Neither exists in the shipped bundle (nor do `gp-11/data/B11.g6`,
`gp-11/data/SHA256SUMS`, or the `gp-10/data` files). Confirmed three ways: statically in the
code, dynamically in the lab (every profile-invoked ACCEPT path dies `checker_error:
No such file or directory`, and every legacy-profile accept rewrite dies the same way), and by
directory inspection. All consequences are fail-closed: no B11 run, no control replay wrapped
by the profile, and no `--require-complete-b10` check can reach ACCEPT from the bundle as
shipped. The two files are part of the checker's own declared review surface and of the
writer's G1/G5 source map, yet their content was not shipped to the referee, so they are
unreviewed here. If the production tree contains them, this is a non-issue for soundness and
remains a packaging defect in the bundle. Fix: ship the complete source map, or have
`source_hashes()` tolerate declared-optional tools.

### MINOR-2 (B, corroborated by C lab0): `load_input` override applies the n == 11 check to every profile, narrowing fixtures

The override requires `graph.n == 11` for all profiles (the biconnected check is correctly
B11-only). FORMAT describes `fixture11` as "for small fixtures, with optional derive and
forbidden_limit (default ten)"; a fixture built from smaller-order graphs is rejected
`input_graph_class`. Fixtures certify nothing, so this is testing ergonomics, not soundness;
the named11 AMP inputs satisfy the check trivially. Fix: apply the order check only when the
profile is B11, or document the fixture narrowing.

### NOTE-1 (A): the sharpest edge is the search-default off-by-one, and it is double-pinned in writing

The inherited forbidden search defaults to 9. At 11, every block search must explicitly cover
order 10, while the B10 control must stay at 9 and compare the freshly derived list against
the 398-tail only after replay. The docs bind both directions explicitly (PROOFS: "The
order-ten search must be explicit: the old search default is nine"; FORMAT: "Blocks through
order ten are explicitly searched through order ten, regardless of the inherited
forbidden-search default of nine"; "B10 uses only F9"). Strand B verified both in code with
dynamic proofs; strand C's exp2a shows the teeth (a clamped mutant accepts a forbidden block
the real checker rejects). Mathematics cannot check code, but here the docs, the code and the
mutation test agree. This note exists so no future edit relaxes either direction.

### NOTE-2 (A): GP-10 amendment 4's index anchor reads through GP-11 Section 1, not its literal filename

Amendment 4 defines indices against `forbidden-74.json`; at GP-11 the anchor is the 398-file.
No misfire: GP-11 Section 1 re-derives the prefix fact (verified against the shipped JSON,
cumulative prefixes 1,2,3,6,19,74,398) and FORMAT binds F10 indices to the original JSON
order. But a builder doing a naive global "10 read as 11" over the amendments could anchor
indices at the wrong file. Fix: one line in GP-11 FORMAT pointing the inheritance chain
through Section 1.

### NOTE-3 (A): "byte-for-byte as parsed JSON" is parsed equality, not byte equality

PROOFS says the first 74 must equal the frozen GP list "byte-for-byte as parsed JSON". The
substance is order- and label-exact equality of the two lists (which makes F9-indices coincide
across files), and FORMAT binds exactly that ("in order and stored labels"). Wording only.
Fix: drop "byte-for-byte" or bind both files' byte digests.

### NOTE-4 (A and D): u(10) = 20 is used as a bare fact in the 24-edge generation line; solid, but the dependency is not restated there

The 24-edge cap on B11 candidates uses u(10) = 20 (each vertex deletion embeds at 20 edges, so
9m <= 220). The value is solid: it follows from GP-10's classification re-derived by the run,
the 20-edge extremal graph is embedded by control, and non-biconnected F10-free graphs top out
at 19. But the generation line does not restate the dependency, and the direction of danger is
one-sided: the bound is safe only if u(10) >= the true maximum; a future upward revision of
u(10) would silently break completeness of the candidate set. As raw data the 398-list decides
only the containing direction; the converse is the completeness theorem, external to the list.
Not a data integrity failure (checks 1-6 all pass); a dependency note.

### NOTE-5 (B): conditional B11 ACCEPT is reachable by design

ACCEPT with unknowns and conditional-minimal members is possible for B11; `claim_authorized`
is never set in that state and the G3 gate reads `counts.unknown == 0` from the report body.
Matches CONTRACT section 0 and FORMAT. Not a gap.

### NOTE-6 (B): the legacy report rewrite is inert metadata

After a base-profile control ACCEPT inside a profile-invoked replay, the wrapper adds
`profile_sources` and atomically rewrites `checked/report.json`. `complete_b10` and the replay
checks read only mathematical fields; the extra key is inert and enters the digest after the
rewrite. No evidence mutation.

### NOTE-7 (B): receipts bind bytes, not attestations

`consumed_receipts` covers the report's file rows and every consumed control report's rows
against the pre-run snapshot. A swap-and-restore with identical bytes is undetectable, as for
any hash scheme; a swap with different bytes is caught twice. Consistent with FORMAT.

### NOTE-8 (B and C): `block_evidence`'s forbidden search is unreachable on consistent data, and that is fine

On consistent data every block of an F10-free deletion is F10-free, so the forbidden search
inside `block_evidence` never fires; the explicit limit=10 remains load-bearing as a guard,
proven live by exp2a. Defense in depth, correctly inert, correctly pinned.

### NOTE-9 (D): the enumeration anchor reproduces exactly through n = 11; the 448,708 filtered count is producer-attested under G0

`geng -C n` reproduces OEIS A002218 exactly for n = 3..11 (1, 3, 10, 56, 468, 7,123, 194,066,
9,743,542, 900,969,091; the n = 10 run took 27 seconds, the n = 11 run took 9 minutes
19 seconds on this box). The claimed 448,708 F10-free biconnected count cannot be recomputed
here because `B11.g6` is not in the bundle, and that remainder is exactly the boundary the
contract draws: G0 is an attestation gate (explicit producer attestations for enumeration
exhaustiveness and the per-graph F10 filter), and the receipts section states honestly that
hash receipts do not prove exhaustiveness. The referee verified every channel of the premise
that is checkable from the shipped bytes, including the full raw census through n = 11; the
filtered count and its witnesses are the producer's G0 duty by design. Correction note: an
earlier attempt at this census used malformed nauty arguments (`n=11 e=11-55`) and died
instantly; both the data strand and the principal misread that instant death as a timeout.
The corrected command `geng -Cd2D10 11 11:55` completed in 9m19s.

## WHAT I CHECKED AND FOUND SOUND

**The mathematics (strand A), each claim attacked first.**
1. The lower-order premise: sound, not circular. The 398 are trusted because a complete B10
   control in the same run re-derives the 324 tail from the frozen 74, answer withheld. I
   swept every channel a circularity could hide in: the input file (the B10 control replays
   on GP-10's frozen B10, built by filtering on F9 only; the 324 cannot be in the input and
   are provably all present in it), the refutation axioms in force (at limit 9 the in-force
   list is the 74; a citation of a 10-vertex member is an out-of-range index and must be
   refused; the contract binds "B10 uses only F9" in writing), embedding certificates and
   hosts (positive information only; a smuggled forbidden host needs a false E-exact, the
   frozen kernel's domain), the checker's own list at limit 9 (loads exactly the first 74;
   code, strand B), provenance objects (the tail comparison runs after the control and never
   steers it), and the same-run-tree requirement (control reports must live under the run
   directory, symlink-resolved, and are replayed in the same invocation before any B11
   record is read). The tower is self-correcting: the B4p..B9p controls re-derive orders 4..9
   from nothing, so the 74 become independently re-derived, and the B10 control re-derives
   the 324 from those. I tried to make the tower self-affirming with a spurious 74-member;
   accepted refutations are sound, so the derived list cannot contain it and the comparison
   fails. Conceded everywhere.
2. L-block at 11: sound. An 11-vertex block forces biconnectivity of the whole; blocks of
   non-biconnected graphs have at most 10 vertices; the finite-rotation assembly argument is
   order-free and imports; the generation arithmetic checks (9m <= 220, m <= 24; K4-freeness
   implied by F10-freeness; the 24-edge cap loses nothing the classification needs).
3. L-min at 11: sound. The two-case argument (proper subgraph misses a vertex, or has all 11
   and misses an edge) is exhaustive and imports verbatim from GP-10 one order up; deletion
   lookup discipline is correct; unknown deletions yield only the conditional form with the
   amendment-2 corrected wording.
4. L-complete at 11: sound subject to the gates, and the text says so itself. The biconnected
   step, the at-most-10 step, and the decidedness step all check, including the converse
   direction; the residual dependencies (certificate soundness inherited from the frozen,
   previously refereed kernel; enumeration completeness, G0; review, G5) are stated openly in
   the document rather than hidden.
5. Contract internal consistency: claim forms vs report fields, gates vs what certificates
   can establish, the 5.1-5.4 control naming, and the "10 read as 11" sweep over GP-10
   amendments 1..6 all check out; the load-bearing consequences are pinned in the new text.

**The code against the proofs (strand B), the five example failure modes.**
1. Block search stops at 9: refuted. Every order-10 reach passes explicit limit=10; the
   dynamic proof accepts a 10-vertex-block UDG at max_order 10 and rejects it under the base;
   exp2a shows the clamped mutant would accept a forbidden block. No order-10 call site uses
   the inherited default.
2. Forbidden-list index read in the wrong list: refuted. `forbidden`, `forbidden_codes` and
   `patterns` extend in lockstep from the same 324 extras; all indices below 74 are unchanged;
   R-ptr bound-and-code checks, TU endpoints, regressions indices and the minimals comparison
   all read the aligned list; `in_force` admits tail indices only at forbidden_limit 10,
   after the B10 replay has re-derived them in the same invocation.
3. Control report accepted from outside, or while partial: refuted. Exact nine-name set,
   in-tree symlink-resolved containment, stored-report checks plus a mandatory
   in-invocation replay with `complete_b10` re-applied to the replay result and PASS required;
   nested B10 replays its own controls with cycle and depth guards; the before-snapshot binds
   every input the replay consumed.
4. Unknown deletion treated as unconditional: refuted. Conditional list and
   `minimal_if_all_listed_deletions_embed` preserved; the B10 control requires an empty
   conditional set; `complete_b10` requires `conditional is False`.
5. Coverage trusts a count: refuted. Coverage is a set difference against the frozen
   database; `complete_b10` compares the actual derived `L10.g6` content and the report's
   `minimal` field to the checker's frozen derived 324, never to a count.
Plus the order-of-operations check that matters most: the 324 tail loaded by the profile is
first used only after `controls()` has replayed B10, so a tampered `forbidden-398.json` can
cause only a mismatch rejection, never a false accept. Hunt-list items with no finding are
listed in the B paper (frozen input pinning, block reindexing, deletion lookup without a host
filter, `canonical_many` zip alignment, named11, CLI collision and output guards, delegation).

**Adversarial empiricism (strand C).** Six experiments through the genuine profile CLI:
three ACCEPT, all fixture-only with no claim authority (empty graph; three small UDGs; a 5x2
integer grid with a pendant, exercising the order-10 block positive path); three REJECT
(wrong-order fixture, the forbidden ten-vertex block, and a forged exact certificate on
K4-plus-isolates, killed at the geometry with `edge_equation` and then `records_rejected`);
and the mutation demonstration of exp2a. No constructed input was wrongly accepted by the
code as shipped.

**Data integrity and anchors (strand D).** All 15 manifest pins verify against disk. The
398-list: order histogram exactly 1,1,1,3,13,55,324 on 4..10 vertices, sorted by order,
cumulative prefixes 1,2,3,6,19,74,398, first 74 equal to forbidden-74.json parsed, all 398
simple and biconnected, ten-vertex members with 15..18 edges (consistent with u(10) = 20 and
the 24-edge cap). Minimality as an antichain: 15,449 full VF2 matcher calls across all
49,087 candidate pairs with n_i < n_j, zero containment hits; same-order extra check also
clean. Canonical forms: 398 codes through `labelg -q`, pairwise distinct within each tier,
zero overlap between the 74-tier and the 324-tier, deterministic across runs, idempotent.
TU gadgets: six entries, schema-clean, connected, distinguished pair a non-edge, both
endpoints anchored. AMP list: 56 lines, exactly two 11-vertex graphs, both 23 edges, both
connected and K4-free. Census ladder reproduces A002218 exactly through n = 11
(900,969,091 in 9m19s); see NOTE-9 for the filtered-count boundary.

## ABOUT THIS RUN

Machine: the line's VM (2 vCPU, no GPU, Linux), Python 3.12 with flint 0.9 and sympy 1.14,
networkx 3.6, nauty 2.8.8 binaries on PATH. Referee: Arturo (Kimi k3-agent, non-Claude
family) as five legs: a personal line-by-line read of both checker files and all four
documents before any strand ran, then strands A to D as above, with independent
corroboration by the principal on every load-bearing claim (the pins, the 398 structure, the
prefix fact, the bundle gap, the limit-10 reach). Honest limits. The shipped bundle cannot
self-run (MINOR-1), so all live execution happened in a scratch mirror of the bundle with the
two missing files created as zero-byte placeholders, their empty digests pinned visibly in
each run's own profile_sources map; B11.g6 is not in the bundle, so no live B11 run or control
replay was possible here. The n = 11 census completed at 07:56, ten minutes after the report's
first draft, and this report records the completed run. One process note for the record: the
first census attempt passed malformed nauty arguments (`n=11 e=11-55`), which fails in under a
second; the data strand logged it as a timeout pending at strand end, the principal repeated
the malformed command twice, and the corrected command `geng -Cd2D10 11 11:55` completed in
9m19s with 900,969,091 graphs, matching OEIS A002218(11) exactly. One strand (the
counterexample lab) went dark mid-run and never delivered its paper; the principal completed
its experiments from its artifacts and ran the remaining ones, and this report's C paper is
the honest record of who executed what. Everything quoted above was executed or re-derived at
first hand this run; nothing is guessed.

Answers to the gate question, in the contract's own grading: a BLOCKER needs a concrete
certificate or scenario the checker wrongly accepts; none exists across six live experiments
and four audit legs; the mathematics was adjudicated claim by claim and holds; the code is
faithful to the proofs; the data is exactly what it claims to be. The complete defect list is
two MINORs and nine NOTEs, each with a stated minimal repair.

Arturo, waste-drop line, 2026-10-01
