# Task B5: the second, independent enumerator (module enum2/)

You must NOT read research/unit-distance-22/enum/ (the first enumerator); read only
CONTRACT.md, the paper and the data files. Build an independent implementation of the F-free
enumeration in a DIFFERENT language and style: python with pynauty (~/tools/pyenv-maths/bin/
python) or Rust (cargo is available at ~/.cargo/bin if present; otherwise python). Same
semantics as CONTRACT Section 3 (canonical augmentation by minimum-degree deletion, edge
windows, bad-neighbourhood patterns from data/forbidden-74.json), same output format
(canonical graph6 via nauty canonical labelling), so that a shard run by both enumerators must
produce byte-identical sorted output.

Self-checks (run and report): (1) for n <= 12 and every m, your U-bar(n, m) equals brute force
(nauty-geng all graphs with n vertices and m edges, then filter with a straightforward
subgraph-monomorphism test against the 74 forbidden graphs); (2) reproduce Table 1 for as many
n as fit in the ten-minute test rule (at least n = 16, 17: counts 1 and 15), running larger n in
the background under nice with logs; (3) all 56 known extremal graphs appear in their (n, m)
files; (4) mutation tests that go red (CONTRACT 3.6(d)); (5) determinism.

Speed matters less than independence and correctness: this enumerator's job is to re-run a
fraction of the first enumerator's shards and agree byte for byte.
