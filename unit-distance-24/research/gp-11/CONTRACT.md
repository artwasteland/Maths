# GP-11 contract: the minimal forbidden unit-distance graphs on 11 vertices

Binding for every builder, checker and run in `research/gp-11/`. Written 2026-10-01 by claude-answering-alexeev-u22,
before any producer exists. It extends `research/gp-10/CONTRACT.md` (and its amendments 1 to 6), whose definitions,
lemmas, record formats, checker rules, producer rules and environment apply with 10 read as 11 unless this file says
otherwise. Amendments go in Section 7 of this file, dated, never in a brief. A brief that disagrees with this file is
wrong.

The question continues the one in Alexeev, Mixon and Parshall (arXiv:2412.11914, Section 6) that GP-10 answered for
10 vertices: 324 minimal forbidden graphs, 398 on at most 10 vertices (`research/gp-10/RESULT.md`). Boris Alexeev asked
how long 11 vertices would take; the owner asked for it within the week (2026-10-01).

## 0. The claim, and the only two forms it may take

- **Full claim** (only when every gate in Section 6 is green): "A graph on at most 11 vertices is a unit-distance
  graph if and only if it contains none of the 398 graphs of `forbidden-398.json` and none of the N graphs in
  `L11.g6`." N and the file are produced by the checker, never typed by hand.
- **Conditional claim** (when UNKNOWN is non-empty): the same sentence prefixed by "Unless one of the k graphs in
  `UNKNOWN.g6` is not unit-distance," with L11 the checker's list and k stated.

The claim rests on GP-10's result (the 324) and GP's (the 74); say so wherever it is stated.

## 1. Definitions (in addition to GP-10's Section 1)

- **F10** is the 398 graphs of `research/unit-distance-22/data/forbidden-398.json` (sha256 `8e8a81a145f75a65…`), in
  file order, which is sorted by vertex count: its prefixes of length 1, 2, 3, 6, 19, 74 and 398 are the members on
  at most 4, 5, 6, 7, 8, 9 and 10 vertices. An index is the zero-based index in that file.
- **B11** is the set of biconnected 11-vertex graphs that are F10-free, frozen in `data/B11.g6` (sorted bytewise,
  canonical by nauty `labelg` 2.8.8 with default options, one per line, trailing newline) with its sha256 in
  `data/SHA256SUMS`. Counted 2026-09-29 (twice, by codex and by the supervisor): 448,708.
- Generation may use two restrictions, each implied by F10-freeness: K4-free (K4 is F10 index 0), and at most 24
  edges (each 10-vertex subgraph of an F10-free 11-vertex graph is F10-free, so a unit-distance graph by GP-10's
  theorem, so has at most u(10) = 20 edges; each edge lies in 9 of the 11 vertex deletions, so 9m <= 220).
- **Control sets:** **B10'** = biconnected 10-vertex graphs free of the F10 members on at most 9 vertices (that is,
  GP-10's B10, 33,162 graphs); and GP-10's B4p to B9p.

## 2. The lemmas (GP-10's Section 2, at 11)

- **L-block, L-mono, L-TU, L-frame, L-sat** as in GP-10.
- **L-min.** A graph G in B11 is minimal forbidden iff G is forbidden and G - e is a UDG for every edge e. (Deleting a
  vertex gives a 10-vertex F10-free graph, a UDG by GP-10's theorem; any proper subgraph lies in some G - e or G - v.)
- **L-complete.** If every graph in B11 is decided, the minimal forbidden 11-vertex graphs are exactly the minimal ones
  among the forbidden graphs of B11, and a graph on at most 11 vertices is a UDG iff it contains no member of F10 or
  L11. (Proof via L-block, L-mono, GP-10's theorem and GP's; written in `PROOFS.md` before use.)
- Any new certificate type or lemma (for instance extending an exact embedding of G - v by a vertex of degree 2) is
  written in `PROOFS.md` and admitted by an amendment before a producer relies on it; the checker verifies the
  certificate it produces, never the lemma's application by trust.

## 3. The checker

GP-10's checker (sha256 `d717816bde784fae…`, G5 closed) extended by a B11 profile, with the kernel unchanged where it
can be and every change marked and listed, the way the u(24) checker marks its edits. Its red fixtures are GP-10's
plus one per new rule, each one field away from a real positive. It refuses to report on B11 unless the control
reports of Section 5 are present and accepted in the same run tree.

## 4. Input freeze

`data/B11.g6` with its sha256, and a replay record: every graph removed by the F10 filter carries a forbidden witness
(member index + map) that an independent script verifies, streamed. Anchors: geng's count of biconnected 11-vertex
graphs equals OEIS A002218(11); the census counts above reproduce; at least one independent recount of B11 by code
sharing nothing with `udfilter` agrees by sorted-list sha256, not only by count.

## 5. Controls (pre-registered 2026-10-01, before any producer runs)

1. **n = 10, answer withheld.** The full pipeline on B10' with the F10 members on at most 9 vertices in force. PASS
   iff every graph is decided and the checker's derived minimal list equals, up to isomorphism, exactly the 324
   ten-vertex members of F10. This re-derives GP-10 with the GP-11 tools.
2. **n = 4 to 9**, GP-10's controls 7.0 to 7.2, re-run with the GP-11 tools.
3. **n = 11, named graphs.** AMP's two extremal 11-vertex graphs (23 edges, `research/unit-distance-22/sources/amp/anc/
   graph6.txt`) must be embedded by the producers' general search, not by a lookup of AMP's coordinates.
4. **Regressions**: GP-10's control 7.4.
5. **Predicted counts** (the size of L11, the residue after the automated stages) written to `PREDICTIONS.md` before
   the B11 run starts.

A control that fails stops the run until the failure is explained in `LABNOTES.md`.

## 6. Gates

| gate | requirement |
|---|---|
| G0 | B11 frozen, anchors match, witness replay complete, independent recount agrees |
| G1 | the checker's B11 profile built, every red fixture rejected, self-test committed |
| G2 | controls 5.1 to 5.4 PASS on the checker, with PREDICTIONS.md committed first |
| G3 | every B11 graph has a record; checker ACCEPT with counts.unknown == 0, conditional == false (read from the report, not the last line) |
| G4 | L11 derived by the checker; second certificates of a different type counted where found (not required) |
| G5 | an independent read of PROOFS.md's new parts and of the checker's B11 changes, every finding answered in writing |
| G6 | write-up generated from checker output only; refuses to run while G0 to G5 are open |

## 7. Amendments

(none yet)
