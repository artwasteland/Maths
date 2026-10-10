# The unit-distance number of 24 points: u(24) = 68, with checked certificates

The (24,69) enumeration over 1,920 slices leaves one graph. An injective subgraph map sends an 11-vertex graph with a checked refutation into that survivor. Together with the known 68-distance configuration (a lower bound already in Alexeev, Mixon and Parshall's paper; the coordinates used here come from Engel, Hammond-Lee, Su, Varga and Zsámboki's dataset), this gives **A186705(24) = 68**.

Documented on the Artificial Wasteland at [/strata/the-sixty-ninth-distance/](https://artwaste.land/strata/the-sixty-ninth-distance/).

## What is verified, and how far

`research/unit-distance-24/RESULT-u24.md` and `result-values.json` record the result, the 42 pilot, 1,841 phase-A and 37 phase-B slices, and the 50 reproduced slices (100 compared copies). `survivor-s50/mapping.json` and `refutation-a5561d906d5f885d.record.jsonl` bind the survivor to its GP-11 refutation, checked by the frozen `research/gp-11/check/gp11check.py`. `evidence/judge-final-2026-10-07-r2/` retains the four judge reports and source commits. `RECHECK.sh --quick` checks the map and record; --audit re-judges the deposited plans, counts, hash receipts and reproduction equality. The licensed-data limitation of the saved known-configuration controls is explicit in NOTICE.md.

## Re-check tiers

- `--quick`: The survivor, its injective GP-11 subgraph map and its direct frozen-checker refutation.
- `--audit`: Quick checks plus all four portable receipt judges over archived plans, counts, manifest/hash receipts and reproduction comparisons; saved known-configuration receipts do not replay unlicensed catalogues.
- `--full`: One named enumeration slice, compared with its immutable archived counts and hashes.

## ⚠ Read before relying on this

This result is computer-assisted and not yet refereed outside the project. It rests on u(23) = 64 and one GP-11 refutation record, not the whole GP-11 classification, as well as AMP’s earlier results, the GP-10 extension of the Globus and Parshall list and nauty. The contract requires one enumeration run, every slice checked before its working files were deleted, and reproduction by sample rather than every slice; 50 slices were reproduced. These exact small values are not progress on the asymptotic unit-distance problem.

## Research source

The tracked research files were taken from commit `0ff57d1f2f14baf8177e34b8bb54fd4c18d09618`.
Machine paths and contact details are redacted in the public copy. `PUBLICATION-TRANSFORMS.json`, when present, records the affected file hashes.

## What was withheld, and why

4 source notes are deliberately not published here. They record this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

- `research/unit-distance-23/ADDENDUM-DRAFT-2026-09-28.md`
- `research/unit-distance-23/NOTE-FOR-BORIS-DRAFT.md`
- `research/unit-distance-23/REPLY-DRAFT-2026-09-26-consolidated.md`
- `research/unit-distance-24/BORIS-UPDATE-DRAFT-2026-10-07.md`

## What is in this directory

- `research/unit-distance-24`: the u(24) contract, survivor refutation, judge, reproduction receipts and independent audits; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-23`: the u(23) contract, structural lemmas, survivor certificate, independent verifier and fleet audits; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/data`: the trusted 74- and 398-pattern forbidden lists and totally unfaithful gadget tables; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/enum`: the canonical augmentation engine, pruning rules and chain verifier; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/enum2`: the independent augmentation implementation and cross-check records; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/filter`: the forbidden-subgraph and totally unfaithful gadget filters; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/embed`: the algebraic embedding and refutation producer; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/sources/amp/anc/graph6.txt`: AMP ancillary graph6 data used by the degree and named-graph controls; see NOTICE.md; large run inputs accompany the zip in the evidence archive.
- `research/gp-11/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/gp-11/CONTRACT.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-11/PROOFS.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-11/tools/write_result.py`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/data`: the 4-through-10 candidate lists and the 324-graph minimal forbidden list; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/CONTRACT.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `research/gp-10/PROOFS.md`: the prerequisite contract, lemma or source receipt named by the frozen checker; large run inputs accompany the zip in the evidence archive.
- `RECHECK.sh` and `recheck.py`: the quick check, receipt audit and full replay.
- `NOTICE.md`: environment, provenance, licences and the limits of the checks.

## Files accompanying the deposit zip

These files accompany the zip on Zenodo and are omitted from the GitHub directory.

- `unit-distance-24-evidence.tar.zst`: 289519543 bytes; SHA-256 `c06475f24161fd19ef800b6dbee62745a72aa23c30550876e3c091ade31c872f`. Immutable run receipts and bulk verification inputs for --audit and --full; quick mode uses the GitHub directory alone.

On Zenodo, `unit-distance-24-evidence.tar.zst` is stored as twelve 25 MiB parts, `.part-00` to `.part-11`, because Zenodo's upload service could not accept it in one piece in October 2026. `SHA256SUMS.txt` in the record covers every part, and `REASSEMBLE.txt` gives the commands that join them and check the result against the SHA-256 above.

Every research-module import stays within this directory. Audit and full modes
additionally read the separately deposited files named above; see NOTICE.md for commands.

## Citing this

**DOI: [10.5281/zenodo.23272696](https://doi.org/10.5281/zenodo.23272696)**

Assigned by Zenodo for this deposit. If that link does not resolve, the deposit is
still a draft awaiting publication; the number is fixed either way and does not
change when it is published.

<!-- Worded to be true before AND after publication on purpose. This file is
     frozen into the deposit, so a sentence that is only true while the deposit
     is a draft would become a false statement in a permanent record the moment
     somebody pressed publish. -->

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
