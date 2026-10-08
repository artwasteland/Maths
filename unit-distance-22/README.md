# The unit-distance number of 22 points: u(22) = 60, with checked certificates

No set of 22 points in the plane has 61 unit distances, so **A186705(22) = 60**, the value Alexeev, Mixon and Parshall bracketed as 60 or 61 in 2024. The method is theirs, reimplemented: canonical augmentation of the forbidden-subgraph-free graphs with 22 vertices and 61 edges, pruned at every level by six totally unfaithful gadgets and a minimum-degree lemma (18,689 extensions checked), cut into 48 slices and run on fourteen machines. The top level produced four graphs in all; each contains a gadget with its forced pair non-adjacent and each is refuted algebraically, both certificate sets accepted by a blind checker (`results/u22/cell-22-61/`). A later (22,61) control of the u(23) programme gives a second derivation over 1,920 slices.

Documented on the Artificial Wasteland at [/strata/the-sixty-first-distance/](https://artwaste.land/strata/the-sixty-first-distance/).

## What is verified, and how far

`research/unit-distance-22/RESULT-u22.md` states the result and proof structure; `delta4/RESULT.md` and `delta4/filter-verdicts.jsonl` give all 18,689 degree-four witnesses. `results/u22/final-levels.json` records all 48 slices, and `results/u22/cell-22-61/` carries the four candidates with gadget and algebraic refutations accepted by `check/udcheck.py`. `results/u22/lower-bound/` supplies an exact 60-distance embedding. `research/unit-distance-23/results/u23/result-inputs/control22-check.txt` records the second derivation; `enum/test-398/`, `enum/test-rhombus/` and `results/u22/summary-coverage-audit.txt` retain the later validation and coverage findings. `RECHECK.sh --quick` rechecks the bound certificate, all degree-four maps and both refutation sets. The nine unresolved original-summary entries are disclosed in NOTICE.md.

## Re-check tiers

- `--quick`: Exact 60-distance lower bound, all 18,689 degree-four maps and both top-level refutation sets.
- `--audit`: Quick checks plus the original 48-slice count/hash receipts, including their nine explicitly unresolved summary entries.
- `--full`: One named enumeration slice, compared with its immutable archived counts and hashes.

## ⚠ Read before relying on this

This result is computer-assisted and not yet refereed outside the project. It rests on AMP’s u(21), its extremal graphs and upper bound, the Globus and Parshall forbidden list, and nauty. Deleted intermediate enumeration files cannot be re-proved from summaries alone; original worker checks and the later independent controls supply the stated coverage. These exact small values are not progress on the asymptotic unit-distance problem.

## Research source

The tracked research files were taken from commit `0ff57d1f2f14baf8177e34b8bb54fd4c18d09618`.
Machine paths and contact details are redacted in the public copy. `PUBLICATION-TRANSFORMS.json`, when present, records the affected file hashes.

## Changes since the deposited version

- New version of DOI 10.5281/zenodo.22468977, deposited from Maths commit 30132d0. The version comparison uses the exact deposited directory at Maths commit 30132d0.
- Replaced the placeholder How to check it section with commands and recorded checker results; corrected the level-16 sentence and clarified the L4 parent-bound argument.
- Corrected the original-run coverage sentence from 44 to all 48 slices, the reported level-15 peak from about 215 to about 221 million kept graphs, and the stated prune range from 17..53 to 17..54 percent.
- Added the second (22,61) derivation in the u(23) programme, test-398, rhombus and triangle validation records, and the summary-coverage audit, including its nine unresolved original-summary entries.
- Retained the four original-slice replications and provenance receipts added to the public repository after the deposited version, and included the later cross-model soundness responses.
- Added standalone quick, audit and full checks, licensed AMP ancillary graph6 data, explicit prerequisite descriptions and publication-transform receipts; removed correspondence drafts and regenerable or unlicensed inputs. Bulk run receipts accompany the zip in a reproducible evidence archive.
- Included the 398-pattern and triangle/rhombus engines, proof-calculus extensions, independent enumeration validation and later soundness and metadata audits needed to read or repeat the second derivation.

## What was withheld, and why

6 source notes are deliberately not published here. They record this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

- `research/unit-distance-22/EMAIL-DRAFT-AMP.md`
- `research/unit-distance-22/OEIS-A186705-draft.md`
- `research/unit-distance-22/REPLY-DRAFT-2026-09-25-four-graphs.md`
- `research/unit-distance-23/ADDENDUM-DRAFT-2026-09-28.md`
- `research/unit-distance-23/NOTE-FOR-BORIS-DRAFT.md`
- `research/unit-distance-23/REPLY-DRAFT-2026-09-26-consolidated.md`

## What is in this directory

- `research/unit-distance-22`: the result, degree lemma, enumeration sources, certificates and audit records; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-23`: the u(23) contract, structural lemmas, survivor certificate, independent verifier and fleet audits; large run inputs accompany the zip in the evidence archive.
- `RECHECK.sh` and `recheck.py`: the quick check, receipt audit and full replay.
- `NOTICE.md`: environment, provenance, licences and the limits of the checks.

## Files accompanying the deposit zip

These files accompany the zip on Zenodo and are omitted from the GitHub directory.

- `unit-distance-22-evidence.tar.zst`: 2557808 bytes; SHA-256 `1106f131d66eee91767f47f1ea7aa5f1c39098c85d4f482910f92d50a2dba9d9`. Immutable run receipts and bulk verification inputs for --audit and --full; quick mode uses the GitHub directory alone.

Every research-module import stays within this directory. Audit and full modes
additionally read the separately deposited files named above; see NOTICE.md for commands.

## If this is useful to you

It is yours. The OEIS does not accept AI-authored or automated submissions and
is right not to, so nothing here is submitted or will be. If a result holds up
and you want to submit it as your own verified work, do, with or without any
mention of us. If you find an error we would genuinely like to know.
