# u22-unpruned-19: AMP Table 1 at (19,50) on the unpruned generator

Gate G2 of `research/unit-distance-22/CONTRACT.md` asks for AMP's Table 1 reproduced by the
UNPRUNED generator. It was done for n = 16, 17, 18 (`enum/out-sup`); this is n = 19.

Job `u22-unpruned-<n>` in `coordination/cloud-workers/JOBS.md`, worker session
`claude-reaching-noether-cloud-u22-unpruned-19`, branch
`claude/reaching-noether-cloud-u22-unpruned-19`.

## Result

| quantity | this run | AMP Table 1 |
| --- | --- | --- |
| F-free graphs at (19,50) | **17** | 17 |
| after the TU filter | **5** | 5 |
| AMP's known extremal graphs at n = 19 present | **3 of 3**, byte for byte | 3 |

All three known graphs are among the five TU survivors; the other two survivors are
`R??I?cRWdOS`QOPGpoC_@K?{HYOHig` and `Rw?G?CbJ?_aBAa@a`GoIJSGiO`]}??`. Whether those two
embed is the embedder's question (gate G3), not this job's.

## The run

    enum/run-dag2.py --target-n 19 --target-m 50 --output-dir out-cloud/dag-19-50-unpruned \
        --jobs 4 --reach --resume

No `--prune`: `run-summary.json` records `prune.enabled: false` and `slice: null`, so this is
the full F-free tree under the reach table only. The reach root is `root_k = 4`
(`reach.json`: "Schade: d >= target_m - u-bar(target_n - 1)"). `19-50.g6` and
`19-50.reach.g6` are the same 17 records with the same sha256
`c0dabc0a5ba9cdab668e9f70967b6beb70e7073e97facdf3f0b5adc2f5489884`, confirming the brief's
expectation that the reach step loses nothing at the target.

Started 13:10Z, finished 14:22Z: about 72 minutes on 4 cores, 1.2 GB of working files.

## Cross-checks that landed on the way

The run passes through the extremal cells of the three completed unpruned runs, so it
re-derives them independently (different target, so a different reach table):

| cell | this run | AMP | agreement with `enum/out-sup` |
| --- | --- | --- | --- |
| (16,41) | 1 | 1 | byte-identical to `dag-17-43` and `dag-18-46` |
| (17,43) | 15 | 15 | sha256 `fc095f90…` equals `dag-17-43/17-43.g6` |
| (18,46) | 84 | 84 | count agrees (the `dag-18-46` control is the same cell) |

## Level profile

The tree peaks at level 14 and contracts after it, which is why an unpruned (19,50) run is
about an hour rather than the days the level-13 growth rate alone would suggest.

| n | F-free children | shard CPU s | ~elapsed min (4 jobs) |
| --- | --- | --- | --- |
| 12 | 1,658,636 | 138.9 | 0.6 |
| 13 | 4,694,852 | 2,162.4 | 9.0 |
| 14 | 6,588,098 | 2,565.2 | 10.7 |
| 15 | 2,755,058 | 2,982.3 | 12.4 |
| 16 | 1,175,241 | — | — |
| 17 | 80,235 | — | — |
| 18 | 1,320 | — | — |
| 19 | 17 | — | — |

Exact per-cell counts and timings are in `counts.json`; `hashes.json` has the sha256 and
record count of all 112 `<n>-<m>.g6` and `<n>-<m>.reach.g6` files of the run directory, so
another worker's levels can be compared against these.

## Self-checks

Both were run on this worker before the enumeration and both exit 0
(`verify-quick.json`, `filter-selfcheck.txt`, toolchain in `VERSIONS.txt`):

- `enum/verify.py quick`: all five red controls went red (pattern validator, forbidden-child
  rejection, child-orbit uniqueness, byte determinism, manifest hash).
- `filter/selfcheck.py`: `known_56_pass=56`, `forbidden_planted_verified=74`,
  `tu_pair_removed_verified=6`, `corrupt_witness_rejected=1`.

## What is not claimed

`run-dag2.py` ran detached under `setsid`, so its exit status was not captured by a waiting
parent; "finished" here means the process left the process table having written its final
completion record (`completed_through_n = 19`, `files: 61`) and all 61 level files. The 17
graphs are an F-free count from this generator, not an embedding result: u(19) = 50 is AMP's,
and nothing here re-proves it.
