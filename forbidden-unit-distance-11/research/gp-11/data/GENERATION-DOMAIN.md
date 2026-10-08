# Generation domain

`B11` means biconnected, F10-free graphs on 11 vertices.
F10 is the ordered list in `research/unit-distance-22/data/forbidden-398.json`.
Its SHA-256 is `8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c`.

Use `nauty-geng -Ckq 11 11:24`.
`-C` restricts to biconnected graphs, exactly as in the definition of B11.
A biconnected graph on 11 vertices has minimum degree at least 2, hence at least 11 edges.
`-k` restricts to K4-free graphs.
K4 is F10 member 0, so every F10-free graph satisfies this restriction.

Let G be an F10-free graph on 11 vertices with m edges.
Each of its 11 vertex deletions is an F10-free graph on 10 vertices.
By GP-10's classification, each deletion is a unit-distance graph.
The established bound u(10) = 20 gives at most 20 edges in each deletion.
Every edge of G is counted in exactly 9 of the deletions.
Thus 9m <= 11 * 20 = 220, and the integer m is at most 24.
The edge cap therefore excludes no F10-free graph.
The dependency is one-sided: the cap is safe because 20 is at least the true maximum u(10); a value of
u(10) above 20 would make B11 incomplete (G5 NOTE-4). u(10) = 20 is exact and established.

These restrictions together lose no member of B11.
The proof uses GP-10's theorem and its underlying GP classification through 9 vertices.
It does not claim that every graph in the restricted stream is F10-free.
The subsequent filter removes a graph exactly when a member of F10 is a non-induced subgraph.
Both `pass` and `tu` outputs of udfilter are retained, because a bare TU hit is not a refutation.

Canonicalize the survivors with nauty-labelg 2.8.8 default labelling (`-q` only suppresses messages).
Sort with `LC_ALL=C sort --parallel=1`, without deduplication.
Strictly increasing lines are checked independently, so duplicates cannot disappear silently.
Write graph6 without a header, one graph per line, with a final newline.
