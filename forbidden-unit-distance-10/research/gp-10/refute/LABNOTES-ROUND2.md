# Round 2 exploration notes

Accepted claims are restricted to official checker runs listed in REPORT.md.
Raw exploration output is not an accepted proof library. In particular, the
following records exceed the official 8 MiB line limit and are not selected:

- `evidence/gp74-real-extra.jsonl`, line 1, 9559729 bytes.
- `evidence/gp74-real-focused.jsonl`, line 4, 9436447 bytes.
- `evidence/round2/stalls-66-centroid-factored-homogeneous.jsonl`, line 1, 39690648 bytes.
- `evidence/round2/stalls-66-centroid.jsonl`, line 1, 22521082 bytes.

The factored centroid experiment recorded a native FLINT abort under the
address-space cap in `stalls-66-factored-crash.json`. Several exploratory
index 39 expansions similarly exhausted memory or exceeded the certificate
term budget. These are unknown attempts. Exact local expansion of an
oversized identity is not official certificate acceptance.

The index 39 direct, homogeneous, quotient-ring, saturation and elimination
experiments remain in `evidence/round2/`. Empty JSONL output means no
certificate was emitted; consult the neighboring attempt or summary file.
The final compact derivation is a proposal document, not a record stream.
The final full expansion has 446203 terms; the earlier triangle reduction
had 434887. Both exceed the current term guard and remain unknown.

The first Round 2 test run selected a direct-containment fixture from B8p,
but that sweep contained only nonempty TU proofs. The fixture was corrected
to explicit in-force K4 containment. A subsequent quotient-wrapper test
exposed a Singular loop-variable redeclaration warning between its exact
markers. Separate loop variable names fixed parsing; the full positive
and negative wrapper controls then passed. Neither issue emitted a false
refutation. FGLM now recreates the actual source variable order before
marking a saved basis as a standard basis; its changed-order positive and
positive-dimensional red control both pass.

Recorded edge-frame sweeps and focused trials:

| Attempt log | Frames | Observed seconds | Per-frame limits |
|---|---:|---:|---|
| stalls-22-d2-frames.attempts.jsonl | 14 | 4.214 | [15.0] |
| stalls-38-d2-frames.attempts.jsonl | 14 | 210.096 | [15.0] |
| stalls-39-allframes-d2.attempts.jsonl | 14 | 168.085 | [12.0] |
| stalls-39-circles-slim.attempts.jsonl | 1 | 55.064 | [55.0] |
| stalls-39-critical.attempts.jsonl | 1 | 45.020 | [45.0] |
| stalls-39-d2-frame18.attempts.jsonl | 1 | 40.032 | [40.0] |
| stalls-66-all-frame36.attempts.jsonl | 1 | 6.648 | [45.0] |
| stalls-66-all-lex-x0.attempts.jsonl | 1 | 60.071 | [60.0] |
| stalls-66-critical-fglm.attempts.jsonl | 1 | 37.049 | [90.0] |
| stalls-66-d2-fglm.attempts.jsonl | 1 | 41.977 | [120.0] |
| stalls-66-d2-frame36.attempts.jsonl | 1 | 1.340 | [45.0] |
| stalls-66-default-fglm.attempts.jsonl | 1 | 0.547 | [90.0] |
| stalls-66-minimal-fglm.attempts.jsonl | 1 | 31.628 | [60.0] |
| stalls-66-preprocessed-dedup.attempts.jsonl | 1 | 60.087 | [60.0] |
| stalls-66-preprocessed-fglm.attempts.jsonl | 1 | 60.093 | [60.0] |
| stalls-66-small-fglm.attempts.jsonl | 1 | 23.017 | [60.0] |

The source GP picture for the intended index 22 graph differs from the
frozen edge list: replacing the drawn 1--4 edge by 3--4 gives an exact
isomorphism. `appendix-maps.json` preserves the proposed correction and the
checked map. The source itself was not changed. The generated certificates
use the frozen graph and are checked independently of that identification.
The other three Appendix maps match without a correction.
