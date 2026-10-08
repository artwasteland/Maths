Deliverable 1 completed on 2026-10-03. Added
`research/gp-11/pipeline/coordinator/round_from_rounds.py` and its stdlib unittest
file. The allocator uses `rounds.bundle`, `rounds.codes`, and the existing shard
function. It checks all artifact hashes, assignments, counts, UNKNOWN records,
overlay input coverage, and decision conflicts (including displaced copies and
support records). It writes sorted input, verbatim UNKNOWN lines in deterministic
gzip, and a schema-1 `frontier_allocation_only` manifest. Existing files and the
read-only bundle collections were not modified.

Tests:

```bash
python3 -B -m unittest discover -s research/gp-11/pipeline/coordinator -p test_round_from_rounds.py -v
python3 -B research/gp-11/pipeline/coordinator/test_round_from_rounds.py --mutation-checks
```

All 17 tests pass. Expected residues are handwritten; replacement records are
compared byte-for-byte. The mutation command confirmed that all nine fatal test
methods go red across seven independently disabled guards, using in-memory
copies only. This covers missing shards, duplicate assignments, non-UNKNOWN
overlay bases, conflicting overlay/displaced decisions, missing/extra input
graphs, wrong shard assignment, and incomplete overlay coverage. With the
duplicate guard disabled, the independent shard-map guard still rejects the
fixture, but the test fails its required duplicate diagnostic. The ordinary
suite passed again after the red runs.

Real allocation command (completed successfully):

```bash
python3 -B research/gp-11/pipeline/coordinator/round_from_rounds.py \
  research/gp-11/pipeline/cloud/f3-input \
  --f1 <repo>/f1-bundles \
  --f1b <repo>/f1b-bundles \
  --f2 <repo>/f2-bundles \
  --p2 <repo>/p2-bundles
```

The selected base is 75 f1 plus 117 f1b bundles: all 192 shards, pairwise
disjoint, exactly the original 17,505 graphs. The five displaced f1b shards are
017, 018, 153, 154, 191, with respectively 3, 2, 1, 0, 4 UNKNOWNs (10 total).
These are separate from the 12 g29 copies already resolved in COLLECTION-f1b.json.

| Source | Assigned | Embedded | Refuted | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| Selected base | 17,505 | 15,291 | 1,606 | 608 |
| f2 overlay | 244 | 15 | 65 | 164 |
| p2 overlay | 8 | 3 | 0 | 5 |
| Final combined status | 17,505 | 15,309 | 1,671 | **525** |

f2 drops 80 and replaces 164 records, leaving 528. p2 drops 3 and replaces 4
surviving records, leaving **525**, below the brief's rough estimate:
`259 + 359 - 10 - 80 - 3 = 525`. All eight p2 graphs are base UNKNOWNs and f2
assignments. One p2 UNKNOWN, `JIGOSED@~o?`, was already refuted by f2; that decision
persists and the later UNKNOWN does not restore it. No conflicting decisions
were found. The 525 final records come from f1 / f1b / f2 / p2 in counts
15 / 349 / 157 / 4.

An independent check of the g6 sets, manifest counts/hashes, sorted records, and
every final record's exact source bytes passed. The existing `rounds.coverage`
also passed on a synthetic return with a handwritten expected allocation.
Real f3 return coverage is not yet applicable: `rounds.py coverage` requires
completed f3 bundles, which do not exist yet.

`round.json` records 200 selected/overlay bundle receipts plus five displaced
receipts, their summary counts and compressed-record SHA-256s, all shard indices,
the selection/decision rules, overlay effects, counts, and these hashes:

| Artifact | SHA-256 |
| --- | --- |
| input.g6 | `35cc3cbea37d98c66e60612a1aec86c4d4281c60bd959c31416e56d5e8bf0d2d` |
| unknown-records.jsonl.gz | `e91ecef62a414fddad81d35ca0aca8070f2bfd76d565a8d184fbfad7032beb07` |
| helper | `32570ebd4509df859d2df04aee5217d4bca621cfe6b8f5f8813e28551d6dde81` |
| round.json | `4f4b94f3e43daea1ee1c8b2bd0b71f5af7d8143bb59edd1ccfffdb4405c4597a` |

Data details: source records have the usual `g6`, `verdict`, `cert` keys. There
are 27 additional refuted support-record occurrences (25 selected, two displaced),
excluded from assigned counts. The largest source line is 8,379,422 bytes, only
9,186 below the existing 8 MiB cap. The output files occupy 223,652 bytes total.

Deliverable 2 proposal (prepared after recording deliverable 1; not launched):
use **80 shards**, indices 0–79, with the existing SHA-256 rule and four concurrent
workers. The actual input gives 2–13 graphs per shard, no empty shards, mean
6.5625. At the supplied p2 rate of approximately 970 seconds per graph, that is
0.54–3.50 hours per shard (mean 1.77), plus startup/export/replay. The ideal
four-worker search total is 35.4 hours; the eight-graph probe is an estimate,
not a runtime bound. For comparison, 64 shards has an 18-graph bucket (4.85 hours
at that rate); 96 shards introduces an empty bucket without reducing the maximum.

Proposed commands, from this desktop's existing environment/index:

```bash
cd <repo>
<repo>/pyenv-gp10/bin/python -B research/gp-11/pipeline/drive.py \
  preflight --scratch /tmp/gp11-f3-preflight
TAG=g25 GP11_PUSH=0 bash coordination/cloud-workers/gp11-frontier.sh \
  f3 research/gp-11/pipeline/cloud/f3-input/input.g6 \
  research/gp-11/pipeline/cloud/f3-input/unknown-records.jsonl.gz \
  80 {0..79}
```

`TAG=g25` selects the existing plan entry's `long` policy; this launcher reads
only the policy from that entry. The positional arguments set the f3 input,
round, and shards. Its existing `xargs -P 4` maintains the requested concurrency;
single-threaded solver settings and memory guards remain active. `GP11_PUSH=0`
disables commits/pushes. Results go to `cloud/f3-000` through `cloud/f3-079`,
states/logs to `/tmp/gp11-f3-*`. No plan or launcher edit is needed.

After all 80 checked bundles return, proposed coverage command:

```bash
python3 -B research/gp-11/pipeline/coordinator/rounds.py coverage \
  research/gp-11/pipeline/cloud/f3-input \
  research/gp-11/pipeline/cloud/f3-[0-9][0-9][0-9]
```
