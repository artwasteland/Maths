# Verification tiers and licensed data

Quick mode compares L11 with all 5,264 minimality status summaries, checks the 34 normalized gate-evidence copies, and replays the bounded-size direct minimal-member refutations listed in QUICK-SCOPE.json, selected in frozen input order.

`RECHECK.sh --quick` uses this GitHub directory alone. `RECHECK.sh --audit --evidence FILE` verifies the separately deposited evidence archive by bytes and SHA-256, then repeats the quick checks and the complete receipt audits. `RECHECK.sh --full --evidence FILE` supplies the original complete replay or named-slice reproduction; GP-11 additionally needs `--records gp11-b11-records.jsonl.zst`.

The archive is streamed into a read-only memory view. It stores uncompressed logical data under sorted tar members, with fixed owners and mtimes, compressed with zstd level 12 and two threads. The index binds every logical file and its deterministic gzip representation. This keeps the audit from expanding hundreds of megabytes onto disk. Source hashes and publication transformations retain the distinction between original and normalized bytes.

Audit mode reconstructs every edge deletion against the separate candidate-verdict receipts, derives the minimal list independently, compares it byte for byte, replays every refutation and runs the archived small-order, named and regression controls. Embedding verdicts are historical receipts here; full mode replays their certificates.

The audit uses the accepted, hash-pinned complete B11 census for exclusion of earlier forbidden subgraphs, and subgraph monotonicity for deletion blocks. Full mode repeats those searches and all 448,708 certificates. The complete replay took about 29 hours and was not repeated by this builder. All 34 original gate files are checked against the pinned original gates before path redaction. GATES-SOURCE.json retains those original hashes; gates.json binds the normalized public copies and the retained source verifier checks them.

The only redistributed third-party source file is AMP ancillary `graph6.txt`, SHA-256 `4f7da8729d4818712e8718daabce29fb7f423cd7abec07eb195f0a04d6601a49`. Credit: Boris Alexeev, Dustin G. Mixon and Hans Parshall, The Erdős unit distance problem for small point sets (2024), https://arxiv.org/abs/2412.11914, licensed CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. Globus and Parshall source material and the Engel dataset are not redistributed.

Environment: Python 3.12, python-flint 0.9.0, sympy 1.14.0, networkx, nauty-labelg and zstd. Full enumeration also needs nauty-geng, nauty development files, make and a C compiler. Expected runtimes are printed from the original run records; archive audits can take tens of minutes on this host; each prints its elapsed time. All results are computer-assisted and not yet refereed outside the project, with the prerequisites stated in the README. These exact small values do not claim progress on the asymptotic problem.

Quick selection retains every direct minimal-member record of at most 1,000,000 raw bytes that fits the cumulative 64,000,000-byte budget in input order, with a 16,000,000-byte compressed limit. The manifest states the count and selected graphs. Refutation pointers and larger certificates are covered by audit mode.
