# The 2,833 minimal forbidden unit-distance graphs on 11 vertices, with checked certificates

There are 2,833 minimal forbidden unit-distance graphs on 11 vertices. The frozen checker accepts all 448,708 candidates: 443,444 embedded and 5,264 refuted, with no unknown or conditional result. It derives the minimal list by checking every one-edge deletion.

Documented on the Artificial Wasteland at [/strata/every-edge-but-one-at-eleven/](https://artwaste.land/strata/every-edge-but-one-at-eleven/).

## What is verified, and how far

`research/gp-11/RESULT.md` lists the 2,833 graphs and the proof structure. `final-check-2026-10-08/checked/report.json` records the 448,708 accepted inputs and the derived list; `checked/minimality.jsonl.gz` retains every deletion decision and `checked/L11.g6` the published list. `independent-checks-2026-10-07/` retains separate algebraic, numerical and minimality audits. `RECHECK.sh --quick` checks the minimal-list summary, gate copies and a bounded deterministic refutation sample; --audit checks all refutations and re-derives minimality against separate verdict receipts, then compares the derived list byte for byte. The complete input accompanies the zip on Zenodo; `RECHECK.sh --full --evidence ARCHIVE --records FILE` streams it through the frozen checker and prerequisite controls.

## Re-check tiers

- `--quick`: The published minimal list against all 5,264 status summaries, all 34 normalized gate files and the bounded-size direct minimal-member refutations named in QUICK-SCOPE.json, selected in frozen input order.
- `--audit`: Quick checks plus all 5,264 refutations, independent reconstruction of every deletion against separate verdict receipts, exact L11 comparison and small-order, named and regression controls; embedding verdicts and the accepted census remain historical receipts.
- `--full`: The frozen checker over all 448,708 candidates and prerequisite controls, using the separate compressed records file.

## ⚠ Read before relying on this

This result is computer-assisted and not yet refereed outside the project. It rests on GP-10’s checker, classification and lemmas, AMP’s calculus and named controls, the Globus and Parshall list, and nauty. The audit check replays all refutations and minimality, using the accepted frozen-census class receipt, not all 443,444 embedding records; full mode supplies that coverage. These exact small classifications are not progress on the asymptotic unit-distance problem.

## Research source

The tracked research files were taken from commit `0ff57d1f2f14baf8177e34b8bb54fd4c18d09618`.
Machine paths and contact details are redacted in the public copy. `PUBLICATION-TRANSFORMS.json`, when present, records the affected file hashes.

## What is in this directory

- `research/gp-11`: the GP-11 contract, frozen checker, candidate and minimal lists, final receipts and independent checks; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/data`: the 4-through-10 candidate lists and the 324-graph minimal forbidden list; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/runs`: the frozen GP-10 run records and independent-check outputs; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/cloud/lean3`: the compressed certificates for all 33,162 GP-10 candidates (in the evidence archive).
- `research/gp-10/CONTRACT.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/PROOFS.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/RESULT.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/data`: the trusted 74- and 398-pattern forbidden lists and totally unfaithful gadget tables; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/sources/amp/anc/graph6.txt`: AMP ancillary graph6 data used by the degree and named-graph controls; see NOTICE.md; large run inputs accompany the zip in the evidence archive.
- `RECHECK.sh` and `recheck.py`: the quick check, receipt audit and full replay.
- `NOTICE.md`: environment, provenance, licences and the limits of the checks.

## Files accompanying the deposit zip

These files accompany the zip on Zenodo and are omitted from the GitHub directory.

- `gp11-b11-records.jsonl.zst`: 550269076 bytes; SHA-256 `aee1dec28195bac1254adad74fef548260061ff16c31651544929bb36be49506`. The zstd-compressed 448,708-record B11 input to the full frozen checker; decompressed size 3,391,468,870 bytes. Full mode streams it without making a raw copy. The decompressed content has SHA-256 `41731c987fade25c26b205fb02c809a2b75461ddeae852869ad61aab2804e114`.
- `forbidden-unit-distance-11-evidence.tar.zst`: 253682211 bytes; SHA-256 `6d1f0fc52b37de89d1a470efa7954865b86c69e90b98ea5c5d9f3ec4cd80828d`. Immutable run receipts and bulk verification inputs for --audit and --full; quick mode uses the GitHub directory alone.

Every research-module import stays within this directory. Audit and full modes
additionally read the separately deposited files named above; see NOTICE.md for commands.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
