# The unit-distance number of 22 points: u(22) = 60, with checked certificates

No set of 22 points in the plane has 61 unit distances, so **A186705(22) = 60**, the value Alexeev, Mixon and Parshall bracketed as 60 or 61 in 2024. The method is theirs, reimplemented: canonical augmentation of the forbidden-subgraph-free graphs with 22 vertices and 61 edges, pruned at every level by six totally unfaithful gadgets and a minimum-degree lemma (18,689 extensions checked), cut into 48 slices and run on fourteen machines. The top level produced four graphs in all; each contains a gadget with its forced pair non-adjacent and each is refuted algebraically, both certificate sets accepted by a blind checker (`results/u22/cell-22-61/`).

Documented on the Artificial Wasteland at [/strata/the-sixty-first-distance/](https://artwaste.land/strata/the-sixty-first-distance/).

## What is verified, and how far

Every link is a file in `research/unit-distance-22/`: `RESULT-u22.md` (the four properties a 61-edge graph would need and why each is sound, the gates, and what is and is not claimed), `delta4/RESULT.md` (Lemma D4 with its 18,689 witnesses), `check/PROOFS.md` (the six gadget lemmas) and `check/udcheck.py` (the blind checker that replays every certificate line against its stage input), `results/u22/` (`final-levels.json`, the funnel over all 48 slices; `cell-22-61/`, the four 61-edge candidates with their gadget witnesses AND the embedder's algebraic refutations, both accepted by the checker; `lower-bound/`, this project's own exact embedding of the 60-distance configuration; `PROVENANCE.md`, the code revisions attested by every manifest; `aggregate-slices.py`, which rebuilds the funnel from the workers' branches), `results/calib*/` (AMP's Table 1 reproduced, unpruned at 16 to 20 and after the gadget filter at 16 to 21, every known extremal graph present) and `enum2/CROSSCHECK.md` (an independent enumerator replaying 92 of 92 sampled shards identically).

## ⚠ Read before relying on this

The enumeration outputs (hundreds of millions of graphs) are not in the repository; each slice's manifests and hashes are, with one certificate line per pruned graph on the workers' branches, and `results/u22/aggregate-slices.py` rebuilds the funnel from them. Rests on AMP Theorem 1 (u(21) = 57 and its five extremal graphs), their u(22) <= 61, the Globus-Parshall forbidden list, and nauty 2.8.8, which both enumerators share. In this copy the absolute machine paths that run manifests record are rewritten to `<repo>/`; the hashes beside them are untouched.

## What is in this directory

- `research/unit-distance-22/` — the engine and its verifier.

The two trees mirror the layout of the private repository these came from, so
that every relative import inside them resolves unchanged. Nothing here reaches
outside its own directory.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
