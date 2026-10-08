# GP-10 independent recount report

Status: complete for the recount brief. This module checks the frozen forbidden-pattern filter and
does not decide unit-distance embeddability.

## Delivered

- `matcher.c`: an independent C graph6 decoder and bitset backtracking matcher for injective,
  non-induced subgraph maps. It reads hosts from standard input and never stores the host stream.
- `verify_witness.py`: a separate Python verifier. Witness records are
  `host_g6<TAB>zero-based-member-index<TAB>pattern-vertex-to-host-map`.
- `check_inputs.py`: checks the 74 JSON members against the same-order graph6 list up to graph
  isomorphism. The JSON labels are not assumed to be the graph6 labels.
- `compare_lists.py`: compares sorted canonical files by exact bytes and SHA-256, and prints the
  full symmetric difference on mismatch.
- `mutate_fixture.py`: makes one-field negative fixtures for the witness and list controls.
- `run_recount.sh`: a niced, sequential reproduction driver writing generated artifacts to
  `/tmp/gp10-recount/`.

The matcher was compiled with the system `cc` and zlib. No packages were installed. The final
compile command was:

```text
nice -n 15 sh -c 'ulimit -v 1500000; cc -O3 -std=c11 -Wall -Wextra -pedantic research/gp-10/recount/matcher.c -lz -o /tmp/gp10-recount/matcher'
```

The input check command was:

```text
nice -n 15 ~/tools/pyenv-gp10/bin/python research/gp-10/recount/check_inputs.py research/unit-distance-22/data/forbidden-74.json research/unit-distance-22/data/forbidden-74.g6
```

It reported `patterns=74`, with vertex counts 1, 1, 1, 3, 13, 55 for orders 4, 5, 6, 7, 8,
9, followed by `MATCH JSON_graph6_order`.

## Primary recounts

All recount pipelines were run with `nice -n 15`, `ulimit -v 1500000`, and at most the `geng`
producer plus the matcher at the same time. B10 was streamed directly from `nauty-geng -Cq 10`.
The final matcher summaries and timings were:

| stream | patterns in force | input graphs | removed | survivors | matcher elapsed |
|---|---:|---:|---:|---:|---:|
| B8p | orders at most 7 | 7,123 | 6,740 | 383 | 0.085 s |
| B9p | orders at most 8 | 194,066 | 190,981 | 3,085 | 2.380 s |
| B10 | all 74 | 9,743,542 | 9,710,380 | 33,162 | 96.338 s |

The final B8p and B9p commands used the same form with `nauty-geng -Cq 8` and
`--max-pattern-n 7`, then `nauty-geng -Cq 9` and `--max-pattern-n 8`. The B10 row came from the
final command:

```text
nice -n 15 bash -c 'ulimit -v 1500000; TIMEFORMAT="elapsed=%3R user=%3U sys=%3S"; { time nauty-geng -Cq 10 | /tmp/gp10-recount/matcher --patterns research/unit-distance-22/data/forbidden-74.g6 --survivors /tmp/gp10-recount/B10.raw.g6 --witness /tmp/gp10-recount/B10.witness.tsv.gz --summary /tmp/gp10-recount/B10.summary; } 2> /tmp/gp10-recount/B10-final.run.log'
```

Each survivor stream was canonicalized with `nauty-labelg -q`, sorted with `LC_ALL=C sort`, and
compared using `compare_lists.py`. The comparisons were exact byte matches:

| file | count | expected SHA-256 | actual SHA-256 |
|---|---:|---|---|
| B8p.g6 | 383 | `3a93e6dc1de6b8ac84494982a9e1bb7966c086505d59b08bd281ad0f30ba13bd` | same |
| B9p.g6 | 3,085 | `7dc5ec4dd9ecc339cc39d38fb3b567b0e9a2b97a52c9408c79eb1b54d8801b3c` | same |
| B10.g6 | 33,162 | `3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f` | same |

The final B10 canonicalization took 0.095 s for `labelg` and 0.015 s for sorting. Earlier measured
stage timings were 0.003 s and 0.003 s for B8p, and 0.012 s and 0.004 s for B9p. The comparison
command used for B10 was:

```text
nice -n 15 ~/tools/pyenv-gp10/bin/python research/gp-10/recount/compare_lists.py research/gp-10/data/B10.g6 /tmp/gp10-recount/B10.sorted.g6
```

## Required controls

Running all 74 members, rather than the order-limited B8p and B9p lists, gave the registered counts:

| order | input graphs | survivors with all 74 | removed | elapsed |
|---|---:|---:|---:|---:|
| 8 | 7,123 | 366 | 6,757 | 0.051 s |
| 9 | 194,066 | 2,984 | 191,082 | 1.614 s |

The mutation run dropped member index 0, the K4 member, from the active list. It still read all
9,743,542 B10 hosts and produced 35,957 survivors, versus 33,162 with all 74. Its elapsed time was
40.967 s. This is a changed count, not a count-only acceptance of the primary result.

The 100,000-host timing sample used before the full B10 run reported 4,606 survivors and 95,394
removed in 1.08 s, with measured maximum resident memory 2,072 KB. The full B10 run was then
performed, so the sample was not substituted for the required recount.

The list comparator's negative control changed `G?AZV_` to `G@AZV_`. It rejected the file and
printed exactly one `only_actual` and one `only_expected` line. The witness negative control made
the second map entry equal to the first. The verifier rejected it with:

```text
REJECT: line 1: map is not injective
```

## Witness replay

The independent verifier command was:

```text
nice -n 15 ~/tools/pyenv-gp10/bin/python research/gp-10/recount/verify_witness.py --patterns research/unit-distance-22/data/forbidden-74.g6 --witness /tmp/gp10-recount/B10.witness.tsv.gz
```

It replayed all `9,710,380` B10 records and completed in 332.182 s. The B8p and B9p replays
reported `replayed=6740` and `replayed=190981`. The compressed witness artifacts are in scratch:

| witness | bytes | SHA-256 |
|---|---:|---|
| B8p.witness.tsv.gz | 21,342 | `8f47960e4d77903dfedc4991641fdc4c609acd534b376b72e776ade8493ce5a7` |
| B9p.witness.tsv.gz | 573,833 | `1d5858b162fd78066c0873057ade191206bf6a1883f95367b58a7a04b10fd6ad` |
| B10.witness.tsv.gz | 28,711,632 | `f3cc3afe8296a0bdfef95669cacd8179e9316587f658fff8cda95dc11a6f2ea0` |

B10 exceeds the 20 MB module limit, so it was not copied into `recount/`. All three witness
files remain in `/tmp/gp10-recount/`. The B10 hash was unchanged after the final-source recount.

## UNCERTAIN

- The C decoder intentionally accepts only the one-byte graph6 order encoding. That covers every
  graph used here, since the largest order is 10, but the extended graph6 forms were not exercised.
- The C matcher and Python verifier each implement graph6 bit ordering independently, but both
  are small local decoders rather than calls to a third graph6 library. The JSON to graph6 input
  check passed up to isomorphism, all witness records replayed, and all three canonical survivor
  lists matched frozen bytes. A decoder convention error is therefore the residual place I would
  inspect first if an external graph6 implementation disagreed.
- I did not run a separate non-biconnected enumeration, since this brief only recounts the three
  `nauty-geng -Cq` biconnected streams.

## Supervisor addendum (claude-answering-alexeev-u22, 2026-09-24)

Reviewed. The witness replay proves each witness valid but not coverage, so I added the set-equality
check the report does not make: the B10 witness hosts (`zcat B10.witness.tsv.gz | cut -f1`) together
with the raw survivors (`B10.raw.g6`, geng labelling), sorted with `LC_ALL=C`, are byte-identical to
the sorted `nauty-geng -Cq 10` stream: 9,743,542 lines on both sides, 9,743,542 distinct. So no graph
was dropped from both files. With the exact sha256 match of the survivors against the frozen
`data/B10.g6`, gate G0's "independent recount agrees" and "witness replay complete" hold.
