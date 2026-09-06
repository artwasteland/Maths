# The (22,61) cell: the only four F-free candidates, and how each was eliminated twice

As of 2026-09-05 21:00Z, 44 of the 48 slices of the (22,61) enumeration are complete and the
(22,61) level has produced exactly four F-free graphs in total: two in slice 15 (worker w13)
and two in slice 38 (worker w3); every other completed slice produced none. Neither slice kept
any of them: `s*.22-61.certs.jsonl` are the workers' certificate files, each graph carrying a
`tu` verdict citing TU gadget 0 of the checker's trusted table `data/tu-gadgets.json` (six vertices,
eight edges: a unit triangle 0-3-4 with unit rhombi 0-1-2-3 and 2-3-4-5 on two of its sides; by
the parallelogram identity p1 - p5 = p0 - p4, so vertices 1 and 5 are at unit distance in every
embedding, `check/PROOFS.md`), mapped onto six named vertices of the candidate with the forced
pair a NON-edge of the candidate. A 61-edge graph with such a pair would carry a 62nd unit
distance if it embedded, against AMP's u(22) <= 61. `check/udcheck.py` accepts both files in
strict mode against each slice's `22-61.g6` (records=2, tu=2, unknown=0, exit 0).

`all4.embedder.certs.jsonl` is the second, independent elimination: `embed/udembed.py` run by
the coordinator on the four graphs (`all4.g6`, `--tries 4 --max-states 200`) refutes all four
algebraically (verdict `refuted`, four proof nodes), with `all4.UNKNOWN.g6` empty, and
`check/udcheck.py all4.embedder.certs.jsonl --graphs all4.g6` accepts (records=4, refuted=4).

So the emptiness of the (22,61) cell in these 44 slices does not rest on the TU filter's word:
each candidate is killed by a checked forbidden-subgraph witness AND by a checked algebraic
refutation. The four remaining slices (37, 39, 42, 45) were still enumerating when this was
written; this file is updated when they finish.

Reproduce: from research/unit-distance-22,
  python3 check/udcheck.py results/u22/cell-22-61/s15of48.22-61.certs.jsonl --graphs results/u22/cell-22-61/s15of48.22-61.g6 --unknown-file results/u22/cell-22-61/all4.UNKNOWN.g6
  python3 embed/udembed.py results/u22/cell-22-61/all4.g6 --tries 4 --max-states 200 --unknown-file /tmp/u.g6 > /tmp/certs.jsonl
  python3 check/udcheck.py /tmp/certs.jsonl --graphs results/u22/cell-22-61/all4.g6 --unknown-file /tmp/u.g6
