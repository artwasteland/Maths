# CONTRACT: a certificate-first determination of u(22)

Binding on every builder, checker and worker in this programme. Written by
claude-reaching-noether-7e1c on 2026-09-05 after four scouts and nine adversarial screeners.
Amend it here, never in a brief; every builder inherits the amended version.

## 0. The claim we are trying to earn, and what we will never say

u(n) = the maximum number of edges of a unit-distance graph on n vertices in the plane
(OEIS A186705). Alexeev, Mixon and Parshall (AMP, arXiv:2412.11914, v2 Feb 2025; "the
paper") determined u(n) for n <= 21 and proved 60 <= u(22) <= 61. They estimate 15,000
CPU-hours to enumerate all F-free graphs on 22 vertices with 61 edges by their method, after
which each candidate must be embedded (u(22) = 61) or refuted (u(22) = 60).

We will claim u(22) = 61 only with an exact embedding of a 22-vertex, 61-edge graph (Section
6.1). We will claim u(22) = 60 only when EVERY (22,61) F-free isomorphism class is accounted
for by a checkable certificate (Section 6.2) and an independent checker has replayed all of
them. Completing the enumeration is not completing u(22). A graph the embedder cannot decide
leaves the question open, and we will say so.

## 1. Definitions (AMP, Section 1; Globus-Parshall = GP, arXiv:1905.07829)

- Unit-distance graph (UDG): a simple graph G with an injection f: V -> R^2 such that every
  edge has |f(u) - f(v)| = 1. Non-edges MAY be at unit distance (the definition is not faithful).
- F: the 74 minimal forbidden subgraphs on <= 9 vertices (GP Appendix A; machine-readable
  in `data/forbidden-74.json` and `.g6`, extracted from GP's own Sage notebook and checked:
  composition (4,6)x1 (5,6)x1 (6,9)x1 (7,10)x1 (7,11)x2 (8,12)x3 (8,13)x10 (9,13)x2 (9,14)x19
  (9,15)x34; pairwise non-isomorphic; no member is a subgraph of another).
- F-free: contains no member of F as a (not necessarily induced) subgraph. U-bar(n,m) = the
  set of F-free graphs with n vertices and m edges up to isomorphism; u-bar(n) its max m.
- Totally unfaithful (TU) gadget: a UDG H with a distinguished NON-adjacent pair {a,b} such
  that every unit-distance embedding of H has |f(a) - f(b)| = 1. Data: `data/tu-gadgets.json`
  (GP's five, AMP's sixth). Filter rule (AMP Section 3): if a candidate G on n vertices with
  u(n)-many edges contains a TU gadget as a (not necessarily induced) subgraph with the
  gadget's pair non-adjacent in G, then G is not a UDG (else G + ab is a UDG with more edges).
  For (22,61) this applies because u(22) <= 61 is proved. Semantics, found by the filter
  builder: a TU hit says "G is not an EXTREMAL unit-distance graph"; at the proved maximum
  edge count that means "G is not a unit-distance graph", but below the maximum it says
  nothing (a gadget plus its own pair is itself a UDG and can contain another gadget with a
  non-adjacent pair, as happens for gadgets 4 and 5). Apply the filter only where the
  edge-count argument holds. HEREDITARY use (our extension):
  any graph at any level whose induced structure forces a non-edge to unit length while a
  61-edge supergraph exists is equally dead; a builder using this must state the exact
  lemma and its proof in the checker, not merely in a comment.
- The paper's checkpoints (Table 1, p. 3), which our enumeration must reproduce EXACTLY
  before any (22,61) run is believed: F-free graphs with u(n) edges: n=16: 1; 17: 15; 18: 84;
  19: 17; 20: 7; 21: 149. After TU filtering: 1, 8, 38, 5, 1, 19. Embeddable: 1, 7, 16, 3, 1, 5
  (the 56 graphs in `sources/amp/anc/graph6.txt`). Also u-bar(22) = 62 with EXACTLY two F-free
  graphs, both containing TU subgraphs; u-bar(23) = 66.

## 2. Data formats (binding)

- Graphs: graph6, one per line, canonically labelled with nauty (`labelg` or densenauty
  with the default options), vertex count first. Files named `<n>-<m>.g6`.
- Shard manifests: JSON, one per shard: {shard_id, parent_file, parent_range [i, j), software
  sha256 (every binary and script), inputs sha256, started, finished, children_written,
  children_file sha256, host, exit_status}. A shard without a manifest does not exist.
- Certificates: JSON lines, one per graph, `{"g6": ..., "verdict": "forbidden" | "tu" |
  "embedded" | "refuted" | "unknown" | "pass", "witness": ...}` (the standalone filter CLI
  emits the same shape with verdict "pass" and no witness) where witness is (for forbidden) the
  index of the F member and the injective vertex map; (for tu) the gadget index, the vertex
  map and the non-adjacent pair; (for embedded) exact coordinates per Section 6.1; (for
  refuted) the proof tree per Section 6.2; (for unknown) nothing, and the graph is listed in
  `UNKNOWN.g6` for a separate attack.

## 3. The enumeration (module `enum/`, C, links libnauty)

Reimplementation of AMP Section 2, with these binding choices:

1. **Canonical augmentation by minimum-degree vertex deletion.** A child G (n vertices, m
   edges) is accepted from parent H = G - v only if v lies in the Aut(G)-orbit of the
   canonically-first minimum-degree vertex of G. Every isomorphism class then has exactly one
   accepted construction path, so shards need no global deduplication. (McKay's canonical
   construction path; the orbit computation is nauty's.)
2. **Edge window (AMP Lemma 2, Schade).** A child (n,m) has a parent (n-1, m') with
   ceil(m(n-2)/n) <= m' <= min(u-bar(n-1), m) and the new vertex has degree d = m - m'.
   With rule 1 the parent is G minus a minimum-degree vertex, so d = delta(G) and the parent
   must satisfy delta(H) >= d - 1 with every degree-(d-1) vertex of H adjacent to v (AMP p. 5).
3. **Bad neighbourhoods (AMP p. 5).** For each parent H compute the minimal family T' of
   vertex sets T such that any new vertex whose neighbourhood contains T creates a member of
   F; the 635 (F - v, N_F(v)) patterns are precomputed once from `data/forbidden-74.json`.
   Enumerate neighbourhoods N of size d containing no T in T'.
4. **Order of work.** Build the DAG bottom-up: U-bar(n', m') for all n' <= 21 and m' in the
   windows implied by the target (22,61): 21: 56-57; 20: 51-54; 19: 46-50; 18: 42-46; 17:
   38-43; 16: 34-41; 15: 30-37; 14: 26-33; 13: 23-30; 12: 20-27; 11: 17-23 (and smaller n from
   geng). Every intermediate file is kept with its manifest.
5. **Sharding.** Shard by parent-record ranges of a frozen, hashed parent file. A shard's
   output is its children in canonical graph6 with a manifest. Parents are immutable inputs,
   so shards are independent and restartable. Sizes: no single committed file over 5 MB;
   bulk lists travel as zstd-compressed blobs with recorded hashes.
6. **Self-checks that can fail.** (a) Reproduce Table 1 counts exactly. (b) u-bar(22) = 62 with
   exactly two graphs. (c) Every one of the 56 known extremal graphs must appear in our list
   for its (n,m); the same for every graph in Engel et al.'s database that falls inside a
   window IF that dataset can be obtained (the code is at codeberg.org/zsamboki/dbs-udg but
   the data sit behind a figshare private link that answers 202 to non-browser clients as of
   2026-09-05; the supervisor is chasing it, builders should not). (d) Mutation tests: inject a forbidden subgraph and
   confirm rejection; delete a bad-neighbourhood pattern from T' and confirm a forbidden
   child appears; break the orbit test and confirm duplicates appear. A generator whose
   mutation tests do not go red is not accepted.

## 4. The filters (module `filter/`, python + C)

F-freeness and TU containment with witnesses (Section 2 format). Subgraph monomorphism
against 74 + 6 patterns on graphs of <= 22 vertices, bitset-based, deterministic. Self-check:
every witness must be re-verifiable by a 30-line independent script that only checks that
the map is injective and edge-preserving and that the TU pair is non-adjacent.

## 5. The embedder (module `embed/`), proof-producing

Reimplementation of AMP Section 4 (moves L0-L3, Lemma 4) with EXACT arithmetic: number
fields (sympy/flint) or interval arithmetic with certified separation, never bare floats in
any step whose output is trusted. Output per graph: "embedded" with exact coordinates, or
"refuted" with a finite proof tree (each node: the current graph G_i, the exact linear
constraint system A_s, the move applied and its exact witness: an L1a collision, an L1b
forced ratio with |w| != 1, an L2 forced edge, or an L3 branch with both children), or
"unknown". Randomised search may PROPOSE embeddings; the trusted checker only verifies.
Self-checks: the 56 known extremal graphs embed; the 39 graphs AMP refuted for n <= 21 (the
TU-survivors minus the embeddable ones: 1, 22, 2, 0, 14 at n = 17, 18, 19, 20, 21) are refuted
with proof trees; K4 and K_{2,3} are refuted; Moser spindle embeds.

## 6. Certificates

### 6.1 If u(22) = 61
A graph in graph6 and 22 points with coordinates in an explicit real number field
(minimal polynomial, isolating interval for the primitive element, coordinates as rational
polynomials in it). Checker: exact arithmetic, all points distinct, all 61 squared distances
equal to 1. Nothing else is needed: u(22) <= 61 is AMP's theorem.

### 6.2 If u(22) = 60
(a) The enumeration manifest chain from geng seeds to `22-61.g6`, every shard hashed;
(b) a second, independently written enumerator run on a stated fraction of shards with
    identical output (the fraction and the agreement recorded);
(c) one certificate line per (22,61) graph, verdict in {tu, refuted}, none unknown;
(d) the independent checker `check/` that replays (c) trusting nothing but the graph6
    strings and the witness objects, plus the TU lemmas for the six gadgets, each with a
    written proof in `PROOFS.md` (GP's Lemma 11 reasoning, made explicit).
If (c) contains any "unknown", the result is "u(22) is 60 unless one of these k graphs is
unit-distance", published as such, and the k graphs get their own attack.

## 7. Gates, in order (the screener's, adopted)

G1 priority: recheck arXiv, OEIS A186705, MathWorld, SciNet and GitHub on launch day; the
   email to the AMP and Engel groups is drafted for the human, who alone sends it.
G2 reproduction: Table 1 exactly, u-bar(22) = 62 with two graphs. No cloud spend before G2.
G3 certificate: formats above implemented and the n <= 21 cases pass the checker.
G4 positive branch first: the delta = 4 case (5 known (21,57) UDGs x C(21,4) neighbourhoods,
   filtered then embedded) and a bounded search for a 61-edge realisation beyond the Moser
   lattice; a success ends the programme with a 6.1 certificate.
G5 exhaustive branch: shards to cloud workers with manifests; streaming, hashed outputs.
G6 unknown gate: no claim while UNKNOWN.g6 is non-empty.

## 8. House rules that bind here too
No em dashes in prose. Never run oversight/oeis derive scripts. Never `npm run build`.
Commit by named path. Every check must have been made to fail on purpose once.

## 9. Amendments adopted from the independent checker (2026-09-05, after B4 reported)

1. **Witness schema.** The inner JSON schema for "embedded" and "refuted" witnesses is the one
   documented in the module docstring of `check/udcheck.py` (coefficient order, rational
   encoding, interval endpoints, complex encoding, graph state per node, child order, row-space
   comparison). It is binding on the embedder; a producer using another shape must ship a
   converter and the checker is not changed to accommodate it.
2. **Merge manifests.** Every concatenation, canonical sort, deduplication and freeze of shard
   outputs into the next parent file gets its own merge record: ordered shard inputs with
   hashes, the software hashes used, output path and hash, input and output record counts,
   duplicates removed. Seed files from geng get explicit seed records (geng version, its
   arguments, output hash). The terminal target `22-61.g6` gets an explicit target record.
3. **Hashes of compressed files** cover the stored bytes AND the decompressed content; both are
   recorded.
4. **nauty is pinned** to 2.8.8 (Debian 2.8.8+ds-5) with `labelg` default options as the
   canonical form; `data/forbidden-74.g6` was re-canonicalised under it on 2026-09-05 (only 1 of
   the 74 GP-notebook labellings had been canonical) and is position-wise isomorphic to the JSON.
5. **L3 requires all three coefficients nonzero.** A three-edge relation with a zero coefficient
   is a two-edge proportionality and must be handled as L1b or L2, never as a case split. A
   negative discriminant at an L3 node is certified by exact sign at the isolated real root.
6. **Semantics note carried from B2:** the standalone filter emits "pass" records; a TU hit means
   "not extremal" and is a UDG refutation only at the proved maximum edge count.

7. **The 39 AMP-rejected graphs** (Section 5's calibration set) are not published by AMP; they
   are produced by this programme: `integrate.py` writes `survivors-<n>-<m>.g6` (F-free and
   TU-free) for n = 16..21, and the rejected set is those survivors minus the 56 known
   embeddable graphs (expected 0, 1, 22, 2, 0, 14). Gate G3 runs the embedder on the survivors
   and requires exactly the known graphs embedded and every other survivor refuted (unknowns
   are reported, and block the gate).
