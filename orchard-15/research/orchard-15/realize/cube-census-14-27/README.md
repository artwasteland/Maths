# The (14,27) cube census: the completeness certificate behind t3(14) = 26

Produced 2026-09-06 20:00Z to 2026-09-07 06:01Z by 23 cloud workers (branches
`claude/reaching-noether-cloud-cube-census-w1..w23`) and the coordinator's box, job
`orchard-14-27-cube-census` in `coordination/cloud-workers/JOBS.md`, driver
`research/orchard-15/chiro/cube_census.py`, aggregator `cube_census_aggregate.py`.

## What it certifies

Every PTS(14,27) that admits a rank-3 chirotope (equivalently, a pseudoline arrangement with
27 three-point rows on 14 points) is isomorphic to one of the 8 classes in `classes.pts`,
which is byte-identical to `../pts-14-27-pseudoline.txt`, the classes the lex census found.
With `../verdicts-14-27.jsonl` (all 8 refuted over R, certificates accepted 8/8 by the blind
checker), this is t3(14) = 26.

## How

`exist.py`'s cube frames: point 0's row fixed to its canonical form, the rows of points 1 and 2
fixed to one orbit representative per cube (7 depth-1 cubes, 28,788 depth-2 children; the orbit
decomposition and each cube's stabiliser are checked independently in GAP,
`../../chiro/independent/`), the lex-leader in each child taken over its stabiliser. Per child:
every model enumerated with an incremental cadical and blocked by its exact-b block vector;
then the closure CNF (child clauses + blocking clauses) refuted by kissat 4.0.4 with a DRAT
proof, checked by drat-trim. UNSAT VERIFIED for a child means: the models recorded for it are
all of its models. The cube set is a cover (exist.py asserts it; GAP confirms it), so the union
over all children is every chirotope-admitting PTS(14,27) up to isomorphism.

## Files

- `records-all-sources.jsonl.zst`: every record every source produced (31,363 records for
  28,788 distinct children; children done by more than one source are present more than once
  and agree exactly). Each record: cube name, its rows, stabiliser order, the model lines,
  loop time, and the closure's CNF sha256, proof sha256 and size, kissat and drat-trim times
  and the checker's tail.
- `aggregate-manifest.json`: the aggregator's verdict COMPLETE with every count.
- `classes.pts`: the 8 canonical classes (nauty), sorted.
- `SHA256SUMS`.

## Numbers

28,788 children, all UNSAT_VERIFIED; 834 labelled models in 502 children (106, 106, 104, 104,
104, 104, 104, 102 per class); 2,575 agreeing duplicates; proofs 470,771,688,199 bytes in
total, deleted after acceptance; kissat 351,202 s, drat-trim 705,327 s, enumeration 373,895 s.

## Reproduce any child

    python3 research/orchard-15/chiro/cube_census.py 14 27 --cube-depth 2 --cube-index 6 --cube-children 1234:1235 --artifacts /tmp/x --keep-proof --keep-cnf

writes the child's record, its closure CNF and proof, and drat-trim's log; the CNF and proof
hashes should match the archived record's. The whole census is `--cube-index i --cube-children a:b`
over the seven cubes' children (599, 767, 4332, 2801, 2105, 1704, 16480), about 330 core-hours.

## Controls (before the run, on the box)

(13,23) through the same driver: exactly its one known class, 12 labelled models over 2
cubes, both closures UNSAT VERIFIED. (13,24): no models, both closures UNSAT VERIFIED. Dropping
one blocking clause per cube (`--mutate-drop-model`): every closure SAT. The aggregator fails on
a deleted record, on a record with `proof_verified` flipped, and on two records for one child
that disagree; exist.py's own cover assertion rejects a dropped cube.
