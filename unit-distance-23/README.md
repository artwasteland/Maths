# The unit-distance number of 23 points: u(23) = 64, with checked certificates

The (23,65) enumeration over 1,920 slices leaves one graph, refuted by an exact proof tree checked by the project checker and an independent verifier. Together with the known 64-distance configuration (a lower bound already in Alexeev, Mixon and Parshall's paper; the coordinates used here come from Engel, Hammond-Lee, Su, Varga and Zsámboki's dataset), this gives **A186705(23) = 64**.

Documented on the Artificial Wasteland at [/strata/the-sixty-fifth-distance/](https://artwaste.land/strata/the-sixty-fifth-distance/).

## What is verified, and how far

`research/unit-distance-23/RESULT-u23.md` gives the reduction and gate ledger. `results/u23/result-inputs/aggregate.json` records 1,920 complete slices and 1,955 checked copies; `results/u23/top-level/s50of1920/23-65.certs.jsonl` is the one surviving graph’s 15-node proof tree. `blind-verifier/verify_tree.py` checks it independently. `RECHECK.sh --quick` runs both project checkers and that verifier; --audit re-derives the published funnel from the separately deposited worker summaries. `RESULT-u23.md` also records the 63-slice certification sample and subsequent verification of all 1,920 slices.

## Re-check tiers

- `--quick`: One surviving certificate with both project checkers and the independent proof-tree verifier.
- `--audit`: Quick checks plus the 1,920-slice funnel from all 1,955 archived checked copies.
- `--full`: One named enumeration slice, compared with its immutable archived counts and hashes.

## ⚠ Read before relying on this

This result is computer-assisted and not yet refereed outside the project. It rests on u(22) = 60, AMP’s earlier results, the GP-10 extension of the Globus and Parshall list, and nauty. The contract requires one enumeration run, every slice checked before its working files were deleted, and reproduction by sample rather than every slice; the pinned write-up additionally records a later full 1,920-slice rerun. Summary audits do not replay deleted intermediates. These exact small values are not progress on the asymptotic unit-distance problem.

## Research source

The tracked research files were taken from commit `0ff57d1f2f14baf8177e34b8bb54fd4c18d09618`.
Machine paths and contact details are redacted in the public copy. `PUBLICATION-TRANSFORMS.json`, when present, records the affected file hashes.

## What was withheld, and why

3 source notes are deliberately not published here. They record this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

- `research/unit-distance-23/ADDENDUM-DRAFT-2026-09-28.md`
- `research/unit-distance-23/NOTE-FOR-BORIS-DRAFT.md`
- `research/unit-distance-23/REPLY-DRAFT-2026-09-26-consolidated.md`

## What is in this directory

- `research/unit-distance-23`: the u(23) contract, structural lemmas, survivor certificate, independent verifier and fleet audits; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/data`: the trusted 74- and 398-pattern forbidden lists and totally unfaithful gadget tables; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/enum`: the canonical augmentation engine, pruning rules and chain verifier; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/enum2`: the independent augmentation implementation and cross-check records; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/filter`: the forbidden-subgraph and totally unfaithful gadget filters; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/embed`: the algebraic embedding and refutation producer; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/sources/amp/anc/graph6.txt`: AMP ancillary graph6 data used by the degree and named-graph controls; see NOTICE.md; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/RESULT-u22.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/CONTRACT.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `RECHECK.sh` and `recheck.py`: the quick check, receipt audit and full replay.
- `NOTICE.md`: environment, provenance, licences and the limits of the checks.

## Files accompanying the deposit zip

These files accompany the zip on Zenodo and are omitted from the GitHub directory.

- `unit-distance-23-evidence.tar.zst`: 26310870 bytes; SHA-256 `45cd435ed8d388ea082683d249f881f588304889006167f1e0bd317535eeaaae`. Immutable run receipts and bulk verification inputs for --audit and --full; quick mode uses the GitHub directory alone.

Every research-module import stays within this directory. Audit and full modes
additionally read the separately deposited files named above; see NOTICE.md for commands.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
