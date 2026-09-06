# Software provenance of the u(22) slice runs: two revisions of the enumeration code

Every level manifest written by `enum/run-dag2.py` and every prune manifest written by
`enum/prune.py` records `software_sha256`, the sha256 of the script's own source AT THE
MOMENT THE MANIFEST WAS WRITTEN. During the 2026-09-05 cloud run exactly two revisions of these
two files existed, and some slice-0 run directories attest to both, because the hourly
check-in briefs used between 02:22Z and 02:46Z refreshed the files on disk while the run was
in flight (worker W=8 caught this; the briefs were replaced by `coordination/cloud-workers/u22-checkin.sh`
at 03:07Z, which refreshes code only when it is about to start a runbook).

| revision | commit | prune.py sha256 | run-dag2.py sha256 |
|---|---|---|---|
| OLD (every worker started on it, 00:30Z-01:00Z) | 27b1b2714^ (= 08f1f9281 for these files) | c27d1b616e63335eded6c7b43494c229c3fd9522e8bf017da18f29af42bcdd65 | 10b93761131718c200d0119ace598d2cf113f418d3108dfc7f8a79fbeafcbad3 |
| NEW (landed 02:17Z; run-dag2.py unchanged since) | 27b1b2714 | 972e3e46b32617e44bbfbc99191597498bdf5c47fad03c3eceb7f5730d4b362f | 768e1e65e07d1c236ae42abe1971aaa6fba749582714914066aaa823a9d0ea2c |

| NEW2 (landed 04:20Z, prune.py only) | the commit "prune.py: stream the certificate stages" | c86164caa9f5e5ab628b6e5afb36dea2b007b6d6919248aa9833a2c1e55809f6 | (same as NEW) |

| NEW3 (landed 05:25Z, prune.py only) | the commit "prune.py: reuse finished filter parts of any size" | d0f51c3d42c5f4cbef94f740377f2c1ea3bbf53e848ebb508602de52ea2da204 | (same as NEW) |

| NEW4 (landed 2026-09-05 21:30Z, run-dag2.py only) | the commit "run-dag2.py: stream the reach filter" | (prune.py unchanged: NEW3) | b6f0b7b3fc344c0d60ed077cf480b3f702b0040de24cefd2f327d5e98a9f7da4 |

**Why NEW4 exists.** `reach_filter` held every record of a cell in a Python list and was
OOM-killed on the unpruned (21,57) Table-1 run at the 72.4-million-record cell (15,31)
(worker unpruned-21, 21:1xZ; the pruned slices never have a cell that large). NEW4 reads and
writes the cell line by line. On the real cell `enum/scratch/dag-18-46/12-22.g6` (237,735
records) the old and new code give identical output sha256 and identical manifest counts at
thresholds k = 2 (234,373 kept) and k = 3 (92,923 kept). Every slice of the (22,61) run had
finished its reach filters before NEW4 existed, so no slice manifest attests it; only the
unpruned (21,57) run's level >= 15 reach manifests will.

**Why NEW3 exists.** NEW2 wrote filter parts of 200,000 graphs and reused only parts of that
shape, so a worker restarted on it could not reuse the 4.87-million-graph parts the OLD code
had finished, and re-filtered the whole (13,23) cell (2.5 h). NEW3 reuses finished parts of any
size (input bytes equal to the codes at the part's offset, one record per graph) and filters
only the gaps in 200,000-graph parts; the merged filter.jsonl is the same bytes in the same
order. Tested on (12,24): full reuse, partial reuse (one part deleted) and a corrupted part
(one record dropped, correctly not reused) all give byte-identical outputs to OLD.

**Why NEW2 exists.** Every worker's prune.py was OOM-killed at the (13,23) cell (19,494,068
records) in the post-filter stage, which materialised every certificate as a Python dict
(about 14 GB against the 15 GB cgroup limit; W=1 reported it at 04:01Z with the kernel line).
NEW2 streams those stages (certificate writing, the blind checker in chunks of 1,000,000
records, the output re-verification) and reuses the finished filter parts on disk. On the
1,034-graph cell (12,24) the OLD, NEW and NEW2 code produce byte-identical certs.jsonl,
keep.g6, UNKNOWN.g6, survivors.g6 and filter.jsonl (sha256 c67353a8..., 8696133...,
424888f9...), also equal to the coordinator's local control run; the chunked checker path
was exercised with 300-record chunks and agrees; the mutation control still goes red. So a
level-13 manifest attesting NEW2 was produced by a program with the same outputs as OLD.

**What differs between the revisions** (`git diff 27b1b2714^ 27b1b2714 -- research/unit-distance-22/enum/`):
resume and sharing logic only. run-dag2.py: slice manifests keyed by basename with a path
fallback, so a hard-linked prefix validates in a different directory. prune.py: filter parts
capped at 200,000 graphs, finished parts reused after a kill, selective workdir cleanup. No
change to what is enumerated, filtered or kept; the same inputs produce byte-identical
outputs under both revisions, and the cross-worker agreement of every level <= 13 hash
(`results/u22/s<i>of48/hashes.json`, twelve workers, against the coordinator's local control
run for levels <= 12) is the evidence that the outputs are unaffected.

**How to read a manifest.** A `software_sha256` equal to the OLD row means the level was
written by the code every worker started with; equal to the NEW row means the file on disk had
been refreshed by then (the running run-dag2.py process was still the OLD code in memory, and
prune.py is re-executed per level, so a NEW prune.py hash means that level's filter really ran
the NEW prune.py). Any other value is a defect and must be explained before the results count.

**Per-worker state (from their branches; updated as check-ins report):**
- W=1: refreshed at its 02:22Z check-in, then put both files back to the OLD revision on disk at
  03:2xZ, so its slice 0 attests OLD throughout (except any manifest written between 02:22Z and
  the revert, which would show NEW).
- W=2: refreshed at 02:24Z, files on disk are NEW; manifests written after 02:25Z attest NEW.
- W=12: refreshed at 02:5xZ, files on disk are NEW.
- W=8: did not apply the refresh (its provenance note); OLD throughout until its runbook restarts.
- Others: same brief, so assume NEW on disk from their 02:2xZ-02:4xZ check-in unless their
  heartbeat NOTE says otherwise.

Later slices (started by the fixed runbook) run the NEW revision throughout; their levels <= 13
are hard-links of the worker's slice-0 files and carry slice 0's manifests.

## The filter binary: two source revisions of udfilter (2026-09-05 06:45Z)

prune.py also records `software_sha256["udfilter"]`, the hash of the udfilter binary. The
binary hash is not reproducible across machines (compiler, flags), so the meaningful identity is
the SOURCE revision, and manifests from before and after 06:45Z will show different binary
hashes on the same worker:

| udfilter source | commit | what changed |
|---|---|---|
| F1 | 4fcf3002f and earlier (udfilter.c unchanged since the filter was built) | the original subgraph search |
| F2 | the heartbeat commits of 06:26Z and 06:37Z carrying codex's rewrite | per-host degree summary, degree-eligible masks, incremental candidate intersections, ascending set-bit iteration |

F2 produces byte-identical output to F1: the coordinator built both from source and compared
them on 12-24.reach.g6 (1,034), the 20,000-graph unpruned (13,23) sample, 18-46.g6 (84) and
17-43.g6 (15): identical bytes, 13 to 16 times faster; codex's own report (filter/SPEED.md) adds
12-22.reach.g6 (237,710) and the self-check fixtures, all identical, with every witness
re-verified by verify-witness.py and the dropped-pattern mutation going red. Local binary
hashes on the coordinator: F1 c0222fd9599b1c40641c9b40ea62cf825c1abc951dd748d5b21744a21085ea5b, F2 d4ccae3ff45dcd2d45a64087bebb9519e901110c07fabd1661995b148cee600a. Workers adopt F2 at the forced
restart (coordination/cloud-workers/u22-restart-epoch); a cell filtered partly under F1 and
partly under F2 has identical records either way.

## Cross-worker agreement on the shared prefix (2026-09-05 06:55Z)

Worker w1 published `results/u22/prefix-hashes-w1.json` (commit 7df533300): sha256 and record
count of every level <= 13 file in its DAG. The coordinator compared it against the local
control run (`enum/out-22/dag-22-61-f12`, the OLD revision) and worker w4's
`hashes-levels-10-12-u22-w4.json`:

- levels <= 12: 70 of 70 files identical to the local run; no disagreement with w4.
- level 13 (first record of these on any worker; every other slice worker must match):

| file | records | sha256 (prefix) |
|---|---:|---|
| 13-23.reach.g6 | 19,494,068 | eb09a149a5532bd2 |
| 13-23.keep.g6 | 16,609,368 | af429f91b05b46b3 |
| 13-24.reach.g6 | 4,910,465 | 45c4bcc9f0a36474 |
| 13-24.keep.g6 | 3,820,085 | 6e5d9e8c7de236e1 |
| 13-25.reach.g6 | 463,555 | 8ce46e72c78faaa7 |
| 13-25.keep.g6 | 324,822 | fe9732b14e10703f |
| 13-26.reach.g6 | 18,274 | 95514571d9268b08 |
| 13-26.keep.g6 | 12,746 | 6e0ef6136d781bee |
| 13-27.reach.g6 | 972 | 9a3f335d5684aec5 |
| 13-27.keep.g6 | 670 | 515802243cdd2ca1 |
| 13-28.reach.g6 | 88 | d206408cb0d1dd24 |
| 13-28.keep.g6 | 63 | 9350cab975e12f04 |
| 13-29.reach.g6 | 7 | 806b9bc4ffd1c462 |
| 13-29.keep.g6 | 6 | e8ee45f12344b0c4 |
| 13-30.reach.g6 | 1 | 50dbd9bab95cd6d4 |
| 13-30.keep.g6 | 1 | 50dbd9bab95cd6d4 |

The level-13 counts agree with w2's independently reported 13-23 (19,494,068 in / 16,609,368
kept) and 13-24 (4,910,465 / 3,820,085). Level 13 as a whole: 24,887,430 reach, 20,767,761 kept
(16.6% TU-pruned; level 12 pruned 51.0%). These are the prefix every slice shares; a slice
worker whose level-13 hashes differ from this table is running different code and its slice
is void until explained.

(07:05Z: the kept total above first read 20,767,676, a coordinator addition slip; the per-cell
numbers were right and w2's independent level-13 completion (commit 0dd5258c5) reports the same
per-cell counts and the correct total 20,767,761. w6 and w8 report the same 24,887,430 children.)

07:20Z: w11 published `prefix-hashes-w11.json` while its level 13 was still in flight (the check-in
script's first condition read run-dag2.py's `completed_through_n`, which becomes 13 after the FIRST
level-13 cell, not the last; fixed to require every level-13 cell's prune counts, and the partial
file is replaced at w11's next check-in). What it did publish agrees: 76 of 76 files identical
to w1, including all four 13-23 files (reach, keep, UNKNOWN, g6) and 13-24.g6/13-24.reach.g6.

07:50Z: `compare-prefix-hashes.py` (this directory) now does the comparison from the workers'
branches. Ten of twelve workers have published complete tables (w1 reference; w2, w3, w5, w6,
w7, w8, w9, w11, w12): every one is 102 of 102 shared level <= 13 files identical to w1 in
sha256 and record count. Each worker's own `<cell>.slice-<i>-of-48.g6` partition files hold
431,412 to 433,230 records for the 8 level-13 cells against the 432,661 an even split would
give. Outstanding: w4 (session stuck; replaced by w13 for slices 3, 15, 27, 39) and w10.

08:55Z: w13, the replacement fired at 07:46Z on a fresh VM, regenerated the whole prefix from
scratch under the F2 filter in 65 minutes and matches w1 on all 102 shared files. That is the
cleanest cross-machine statement available: w1 computed levels 12-13 partly under F1, w13
entirely under F2, on different machines, from the same source revisions, byte for byte.
Eleven workers now agree; only w10 has not published.

10:35Z: w14 (the replacement for w10, fired 09:06Z on a fresh VM) also regenerated the whole
prefix from scratch under F2 and matches w1 on all 102 shared files. Twelve workers now agree
(w1 as reference; w2, w3, w5, w6, w7, w8, w9, w11, w12, w13, w14); the two that never published
(w4, w10) are the two stuck sessions, replaced by w13 and w14.
