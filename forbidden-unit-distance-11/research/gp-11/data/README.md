# Frozen B11 input

`B11.g6` contains 448,708 biconnected F10-free graphs on 11 vertices.
Each graph is canonical under nauty-labelg 2.8.8 default options.
Lines are strictly sorted by bytes, with one graph per line and a trailing newline.
The file's SHA-256 is recorded in `SHA256SUMS`.

`GENERATION-DOMAIN.md` proves that `nauty-geng -Ckq 11 11:24` loses no member of B11.
The initial bytes came from `/tmp/gp11-architect/B11.g6`.
The recount regenerates them with udfilter and with the independent GP-10 matcher extended to 11 vertices and 398 patterns.
Both regenerated lists must agree with the frozen bytes, including their SHA-256.

See `../recount/REPORT.md` for measured anchors, replay totals and controls.
See `../recount/receipt.json` and `../recount/chunks.jsonl` for the machine-readable evidence.
The reproduction command, run from the repository root, is:

```sh
python3 -B research/gp-11/recount/run_recount.py
```

This checks the frozen input; it makes no classification claim about the graphs in B11.
