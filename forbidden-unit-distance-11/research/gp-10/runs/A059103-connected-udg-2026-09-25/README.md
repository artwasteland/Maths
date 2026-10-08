# Connected unit-distance graphs on 10 vertices (OEIS A059103): a(10) = 91,658

Produced 2026-09-25 by `tools/count_connected_udg.sh` (the recipe and its justification are in its header).

| n | connected graphs | F(n-1)-free | refuted in run Bn | a(n) = difference | direct count | OEIS A059103 |
|---|---:|---:|---:|---:|---:|---:|
| 4 | 6 | 6 | 1 | 5 | 5 | 5 |
| 5 | 21 | 17 | 4 | 13 | 13 | 13 |
| 6 | 112 | 53 | 2 | 51 | 51 | 51 |
| 7 | 853 | 226 | 4 | 222 | 222 | 222 |
| 8 | 11,117 | 1,330 | 17 | 1,313 | 1,313 | 1,313 |
| 9 | 261,080 | 9,740 | 101 | 9,639 | 9,639 | 9,639 |
| 10 | 11,716,571 | 92,167 | 509 | **91,658** | **91,658** (all 398 as patterns) | (new) |

At n = 10 the F9-free count is made by two matchers that share no code (`recount/matcher.c`: 92,167 survivors;
`unit-distance-22/filter/udfilter`: 70,974 pass + 21,193 tu = 92,167 not forbidden). The connected-graph counts equal
OEIS A001349. `connected-udg-10.g6.gz` lists the 91,658 graphs (geng labelling, not canonical; sha256 of the
uncompressed file in `connected-udg-10.sha256`). The summaries of every run are in this directory.

OEIS A308349 (minimal forbidden graphs on n vertices; 0,0,0,1,1,1,3,13,55) gets a(10) = 324 from `RESULT.md` directly.
Submissions to OEIS are the human's to author.
