# Is the hereditary rhombus/triangle pruning known? (literature check, 2026-09-26)

A research agent's sourced answer, condensed by the u(23) supervisor. READ = read in the source; INFERRED = our
reasoning or measurement; 2ND-HAND = someone else's description. Scratch copies of the fetched papers were kept in the
session scratchpad (`lit/`).

## Bottom line

Both rules are Alexeev-Mixon-Parshall's own proof moves on Globus-Parshall's lemma. AMP apply their TU test and their
embedder only to FINAL candidates (n vertices, u(n) edges); their enumeration prunes intermediate graphs only by
F-freeness and degree. No published work or public code was found that runs 4-cycle-row or triangle-split reasoning
on every intermediate graph of an enumeration. The nearest analogue is Kurz's pruning of matchstick-graph generation
by triangle and rhombus angle criteria (a different problem).

## AMP (arXiv:2412.11914; local `research/unit-distance-22/sources/amp/`, byte-identical to arXiv v2)

- Pruning of intermediate graphs (READ, Section 2, tex lines 236-293): level-by-level extension with Schade's edge
  window, F-freeness via (minimal) bad neighbourhoods, minimum-degree skips for u(21); nauty with an S-free hook for
  n <= 15. Nothing else.
- Refutation machinery on final candidates only (READ): the TU test (line 492, "given a graph on n vertices and u(n)
  edges"), the embedder (line 798, "on each of the graphs that survived the filters"); Table 1 (lines 168-210) has
  F-free / TU-free / embeddable columns at (n, u(n)) only.
- Their counts are full censuses (INFERRED): our unpruned run reproduces AMP's 149 F-free graphs at (21,57)
  (`research/unit-distance-22/results/calib-unpruned/21-57/`), while the same pipeline with the six gadgets applied
  hereditarily from level 12 generates 24 there (19 after TU); at (17,43), 15 unpruned against 9 pruned
  (PRUNING.md 4.7a). A hereditarily pruned tree could not have produced their published counts.
- Discussion (READ, lines 807-809): extend the forbidden list to 10 vertices (what GP-10 did) and "it would be
  valuable to find more examples of such [TU] graphs". Their route to more pruning was more patterns.
- Our rules in their terms (READ, lines 560-685): rhombus rule = (L0) 4-cycle rows with (L1a) collision or (L2) with
  omega = +-1 at the root; triangle rule = (L3) Heron split on triangles (their K3 example gives exactly +-60 degrees),
  leaves closed by (L1a) or (L2) with a sixth root of unity. We omit (L1b) and general (L3); a "tu" verdict stops at
  the first (L2) and uses M >= u(N) where AMP add the edge and continue.
- The six TU gadgets (READ, lines 304-489): five from Globus-Parshall's Figure 1, the sixth AMP's; proofs use "rhombi
  and equilateral triangles"; neither paper says how they were found. `check/PROOFS.md` and our 2026-09-26 check: all
  six are forced by 4-cycle rows alone.
- No public AMP code (Boris Alexeev's paper page links only to arXiv; nothing relevant on the authors' GitHub).

## Globus-Parshall (arXiv:1905.07829; BICA 90 (2020) 107-138; `sources/gp/smallUD.tex`), READ

The lemma is theirs: an embedding is an injection (line 202); "every 3-cycle forms an equilateral triangle and every
4-cycle forms a rhombus" (line 204); Lemma 2 (lines 206-212). Their search is flat (geng over all biconnected graphs on
8 and 9 vertices, then Sage containment tests). The only automation of the TU idea is `verboseUnfaithful` (notebook
`anc/smallUDsage.ipynb`): adding edges forced by the five fixed gadgets, then testing for a forbidden 8-vertex
subgraph, used to prove specific 9-vertex graphs forbidden. No linear algebra, no search pruning.

## Others

- Schade 1993 (not online; 2ND-HAND via Agoston's 2019 thesis): case analysis with density monotonicity and a
  minimum-degree estimate; no sign of rhombus pruning, cannot exclude it.
- Agoston-Palvolgyi (arXiv:2006.06285), READ: u(15) = 37 by hand; their Observation 1 (every unit pair of an extremal
  configuration is an edge) is the TU logic at the final level.
- Kurz (Geombinatorics 21 (2011); arXiv:1401.4375, 1401.4377), READ: matchstick graphs; an angle linear program
  (triangle angles pi/3, rhombus faces) prunes a face-by-face generation. The closest precedent: angles over a fixed
  planar face structure, a non-embeddability verdict only, no forced distances.
- Not relevant or not read: Hochberg-O'Donnell 1996 (not read); Maehara 1991 (2ND-HAND: distances in rigid
  unit-distance graphs); Engel et al. (arXiv:2406.15317, constructive); Pach-Raz-Solymosi, Aloisio, Rodis, Polymath16.
- State of the field (READ): Guth's survey (arXiv:2609.10791, 2026-09-09) calls u(21) the state of the art; OEIS
  A186705 (revision 100) ends at a(21); AMP's only citer found is Guth.

## Points for the credit line

- "Extremal implies faithful" (the logic of every TU verdict) is old: Globus-Parshall line 314, AMP line 165,
  Agoston-Palvolgyi Observation 1. Hereditary pruning as such is standard (nauty's S-free pruning, used by AMP); what
  is new is the predicate.
- A collision is hereditary outright; a forced unit distance only relative to a target with M >= u(N) proved (for
  (23,65) that rests on our u(22) = 60), pruning ancestors because they are induced subgraphs.
- Boris already knows we applied the six gadgets hereditarily for u(22) (our letter and the 2026-09-25 draft). The new
  part is replacing that fixed list by the per-graph linear moves, which turns "find more TU graphs" into a search,
  per graph, over every linearly forced TU subgraph.
- Caveats: Schade's and Chilakamarri-Mahoney's theses were not read; AMP's code is not public (their Table 1 counts
  argue strongly against intermediate pruning).
