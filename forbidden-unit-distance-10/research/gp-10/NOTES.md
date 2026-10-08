# Minimal forbidden unit-distance graphs on 10 vertices: scoping (2026-09-24)

The open question is printed in AMP (arXiv:2412.11914), Section 6: "it would be interesting to
use the custom embeddability solver ... to reproduce the forbidden subgraphs established by
Globus and Parshall, and perhaps even extend their result to unit-distance graphs on 10
vertices." Globus and Parshall (GP, arXiv:1905.07829) classified every graph on at most 9
vertices: a graph is unit-distance iff it contains none of 74 minimal forbidden graphs.
The target here is the list of minimal forbidden graphs on exactly 10 vertices.

## Measured today (nauty-geng 2.8.8, `unit-distance-22/filter/udfilter` with forbidden-74.json)

GP reduce to biconnected graphs (a graph is unit-distance iff each biconnected block is) and
print two counts, which reproduce exactly:

| n | biconnected graphs | F<=9-free | GP's printed count |
|---|---:|---:|---|
| 8 | 7,123 | 366 | 7,123 and 366 |
| 9 | 194,066 | 2,984 | 194,066 and 2,984 |
| 10 | 9,743,542 | **33,162** | (new) |

(Connected, minimum degree >= 2, for comparison: n = 10 gives 37,654 F-free.)

Reproduce: `nauty-geng -Cq 10 | ./filter/udfilter -f data/forbidden-74.json -t data/tu-gadgets.json`
and count every verdict that is not `forbidden` (a `tu` verdict is F-free; TU is not a
forbidden-subgraph test below the extremal edge count). 24 s on four cores.

So the whole job is to decide 33,162 graphs: each embeds (exhibit it) or does not (refute it).
The minimal forbidden 10-vertex graphs are then the refuted ones whose every one-edge deletion
embeds (vertex deletions are 9-vertex F-free graphs, unit-distance by GP).

## The existing embedder is the wrong tool as it stands

`unit-distance-22/embed/udembed.py --tries 4 --max-states 200` on a fixed 200-graph sample
(`shuf --random-source=<(yes)`): 35 embedded, 22 refuted, **143 unknown** (71.5%), in 16.5 min
of wall clock (about 5 s per graph). At that rate the full 33,162 is about 46 hours on one
process, and would still leave roughly 23,700 undecided. It was built for dense rigid 22-vertex candidates;
most F-free 10-vertex graphs are flexible, so a search for an exact rigid realisation stalls.

## The shape of the pipeline this wants

1. **Containment** in a library of known unit-distance graphs (GP's G_27 and the Appendix B
   embeddings, AMP's 56 extremal graphs, Engel et al.'s database): GP settled all but 275 of
   2,984 at n = 9 this way. Cheap, certificate = subgraph map + the host's exact coordinates.
2. **Flexible embedding**: numerical realisation with free parameters, then an exact
   certificate (pick rational or quadratic-surd values for the free angles and solve the rest
   exactly, or an interval-arithmetic existence proof).
3. **Refutation** of what is left: rigid-component case analysis and the TU/rhombus lemmas as
   in GP Sections 3-4, then the algebraic refutation side of `udembed.py`; anything neither
   side decides stays UNKNOWN and the list is not claimed.
4. **Independent checker** replaying every certificate, and the controls: the pipeline must
   rediscover GP's 13 eight-vertex and 55 nine-vertex minimal forbidden graphs from scratch.

Note: `udembed.py` reads `sources/amp/tikz.tex`, which is not committed (arXiv source), so the
embedder cannot run from a fresh checkout. Copied locally for this measurement.
