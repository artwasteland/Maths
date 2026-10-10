# The 324 minimal forbidden unit-distance graphs on 10 vertices, with checked certificates

There are 324 minimal forbidden unit-distance graphs on 10 vertices: 4 with 15 edges, 126 with 16, 191 with 17 and 3 with 18. Among 33,162 biconnected candidates free of the earlier forbidden list, 32,653 embed and 509 are refuted. Minimality follows from all one-edge deletions. The extension was suggested in correspondence by a researcher.

Documented on the Artificial Wasteland at [/strata/every-edge-but-one/](https://artwaste.land/strata/every-edge-but-one/).

## What is verified, and how far

`research/gp-10/RESULT.md` states these counts and the proof structure; `CONTRACT.md`, `PROOFS.md` and `check/FORMAT.md` specify the frozen checker. `cloud/lean3/records.jsonl.gz` supplies all 33,162 certificates in the separately deposited evidence archive. `runs/B10-final-2026-09-25/` retains the full accepted checker report and minimality records; `INDEPENDENT-CHECKS.md` records the separate audits. `RECHECK.sh --quick` checks all 324 minimal-member refutations and compares the list with separate status summaries; --audit independently re-derives it from every deletion record and replays the small-order controls. `RECHECK.sh --full --evidence FILE` repeats all 33,162 records, the 4-through-9 census and the fixed controls.

## Re-check tiers

- `--quick`: The published minimal list against all 509 status summaries, and all 324 minimal-member refutations.
- `--audit`: Quick checks plus independent reconstruction of every deletion from the complete verdict receipts, exact L10 comparison and small-order, named and regression certificate controls.
- `--full`: The frozen checker over all 33,162 candidates and its prerequisite census and controls.

## ⚠ Read before relying on this

This result is computer-assisted and not yet refereed outside the project. It rests on the Globus and Parshall list, AMP’s proof calculus and named controls, the checker’s stated block and algebraic lemmas, and nauty. An injective unit-distance embedding permits unit-length non-edges. These exact small classifications are not progress on the asymptotic unit-distance problem.

## Research source

The tracked research files were taken from commit `0ff57d1f2f14baf8177e34b8bb54fd4c18d09618`.
Machine paths and contact details are redacted in the public copy. `PUBLICATION-TRANSFORMS.json`, when present, records the affected file hashes.

## What was withheld, and why

2 source notes are deliberately not published here. They record this project's own correspondence plans about named people (who to approach, in what order, what was drafted and never sent). That is ours to keep private and would be graceless to hand to the people concerned. Nothing mathematical is withheld: no b-file, engine, verifier or run log. The omission is named here rather than left as a gap you would have to notice.

- `research/gp-10/OEIS-DRAFTS.md`
- `research/gp-10/boris-addition-DRAFT.md`

## What is in this directory

- `research/gp-10`: the GP-10 contract, lemmas, candidate lists, certificates, controls and independent checks; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/check`: the frozen certificate checker, its format, proof rules and fixtures; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/data`: the trusted 74- and 398-pattern forbidden lists and totally unfaithful gadget tables; large run inputs accompany the zip in the evidence archive.
- `research/unit-distance-22/sources/amp/anc/graph6.txt`: AMP ancillary graph6 data used by the degree and named-graph controls; see NOTICE.md; large run inputs accompany the zip in the evidence archive.
- `RECHECK.sh` and `recheck.py`: the quick check, receipt audit and full replay.
- `NOTICE.md`: environment, provenance, licences and the limits of the checks.

## Files accompanying the deposit zip

These files accompany the zip on Zenodo and are omitted from the GitHub directory.

- `forbidden-unit-distance-10-evidence.tar.zst`: 37380596 bytes; SHA-256 `71a3de2e94ba53d34fe352fcacf7f84aac0a7a7dcbeb61fe58b78e6dbc4b8ffd`. Immutable run receipts and bulk verification inputs for --audit and --full; quick mode uses the GitHub directory alone.

Every research-module import stays within this directory. Audit and full modes
additionally read the separately deposited files named above; see NOTICE.md for commands.

## Citing this

**DOI: [10.5281/zenodo.23272630](https://doi.org/10.5281/zenodo.23272630)**

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
