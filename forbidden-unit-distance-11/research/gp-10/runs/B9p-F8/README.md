# Control 7.2: B9p with F8 in force, PASS

All 3,085 biconnected 9-vertex F8-free graphs decided with certificates accepted by the blind checker:
2,984 embedded (every F9-free one), 101 refuted, 0 unknown, 0 rejections. The checker's derived minimal list
(`L9.g6`) is exactly GP's 55 nine-vertex minimal forbidden graphs (also confirmed by an independent canonical
comparison). With controls 7.0 and 7.1 this re-derives the classification of unit-distance graphs on at
most 9 vertices from our own certificates.

`records.jsonl.gz` is gzip-compressed (the raw file exceeds the repository's 2 MB guideline; the largest
single record is GP's F(9,14,19) as a 14-row null-dag, 1.7 MB). To re-check: `gunzip -k records.jsonl.gz`, then
`SYMPY_GROUND_TYPES=python ~/tools/pyenv-gp10/bin/python research/gp-10/check/gp10check.py research/gp-10/runs/B9p-F8 --output /tmp/b9-out`.
