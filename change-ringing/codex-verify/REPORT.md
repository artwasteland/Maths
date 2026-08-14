# Independent re-aggregation of n5-L21

## Method and checkpoint format

`reaggregate.py` independently constructs all 120 permutations of `0..4` in
lexicographic order.  For every permutation it applies each nonempty subset of
adjacent swaps whose selected positions do not touch.  There are seven such
moves for five bells, so the resulting undirected graph is 7-regular.  Vertex
0, `(0,1,2,3,4)`, is rounds.

Simple depth-6 prefixes are enumerated by DFS, using ascending neighbour ranks.
For the symmetry

`phi(p)[i] = 4 - p[4-i]`,

only the lexicographically smaller of a prefix and its phi-image is retained.
Its weight is 2; a phi-fixed prefix would instead have weight 1.

The checkpoint header is:

```text
H n=5 graph=fd678c690f6416b5 maxL=21 K=6 sym=1 jobs=3388
```

Each subsequent line has this format:

```text
J <job-id> <weight> <path-7>,<cyclic-7> ... <path-21>,<cyclic-21>
```

Thus each job line contains 15 path/cyclic pairs.  These are continuations of
one retained length-6 prefix, and are multiplied by the stored symmetry weight.
They do not supply levels 1 through 6.  Those levels were independently counted
by a complete, unsymmetrised simple-path DFS, with the stated convention
`path(1) = cyclic(1) = 1`.

The C resume scan marks the first complete line for a job ID as done.  Its final
aggregation likewise accepts the first parseable complete line for that ID and
ignores later duplicates.  The Python parser implements that first-valid-line
rule.  There were no duplicate lines in this checkpoint.

## Job-set audit

The independent enumeration expected 3,388 job IDs.  It produced 0 weight-1
representatives and 3,388 weight-2 representatives.  The checkpoint declared
3,388 jobs and contained 3,388 physical job lines representing exactly 3,388
unique in-range IDs.

- Missing expected IDs: 0
- Out-of-range/extra IDs: 0
- Duplicate valid IDs: 0
- Malformed/incomplete lines: 0
- Stored weights disagreeing with independent enumeration: 0

Job-set completeness: **PASS**.

## Totals and comparison

| L | path | cyclic | noncappable | vs n5-L21.out |
|---:|---:|---:|---:|:---:|
| 1 | 1 | 1 | 0 | PASS |
| 2 | 7 | 7 | 0 | PASS |
| 3 | 42 | 18 | 24 | PASS |
| 4 | 234 | 50 | 184 | PASS |
| 5 | 1,264 | 120 | 1,144 | PASS |
| 6 | 6,776 | 418 | 6,358 | PASS |
| 7 | 36,094 | 2,114 | 33,980 | PASS |
| 8 | 190,560 | 10,140 | 180,420 | PASS |
| 9 | 997,774 | 41,544 | 956,230 | PASS |
| 10 | 5,199,588 | 164,022 | 5,035,566 | PASS |
| 11 | 27,025,854 | 730,136 | 26,295,718 | PASS |
| 12 | 140,092,710 | 3,770,982 | 136,321,728 | PASS |
| 13 | 723,510,594 | 20,541,820 | 702,968,774 | PASS |
| 14 | 3,720,320,512 | 110,476,618 | 3,609,843,894 | PASS |
| 15 | 19,044,051,770 | 580,834,748 | 18,463,217,022 | PASS |
| 16 | 97,051,434,120 | 3,013,771,544 | 94,037,662,576 | PASS |
| 17 | 492,383,872,912 | 15,539,996,378 | 476,843,876,534 | PASS |
| 18 | 2,486,705,768,206 | 79,715,421,726 | 2,406,990,346,480 | PASS |
| 19 | 12,500,104,398,912 | 406,436,091,978 | 12,093,668,306,934 | PASS |
| 20 | 62,535,460,933,312 | 2,059,526,455,302 | 60,475,934,478,010 | PASS |
| 21 | 311,327,372,361,512 | 10,379,809,487,334 | 300,947,562,874,178 | PASS |

All 21 rows matched programmatically, including `noncappable = path - cyclic`
(with the explicit level-1 convention).  Overall comparison: **PASS**.

The only mildly surprising observation is that none of the 3,388 canonical
depth-6 prefixes is phi-invariant; consequently every checkpoint job has
weight 2.  No discrepancy was found.
