# u(22) slice cost model, from the workers' interim counts

Kept up to date by the coordinator as levels land. Source: `results/u22/interim/w<N>-<run
dir>-counts.json`, copied from each worker's run-summary.json at every check-in. Every number
below is for ONE slice (1/48 of the level-13 keep set, hash-partitioned; w1's slice 0 drew
432,604 of the expected 432,661 parents) on a 4-core cloud VM with the F2 udfilter.

## Slice 0 (w1), 07:22Z: levels 14 and 15 complete

| level | window m | children | kept after TU | TU-pruned | prune wall | growth of kept |
|---|---|---:|---:|---:|---:|---:|
| 13 (shared, all slices) | 23..30 | 24,887,430 | 20,767,761 | 16.6% | (F1 era) | |
| 13 slice share | | | 432,604 | | | |
| 14 | 26..33 | 2,156,374 | 1,519,760 | 29.5% | 3.6 min | 3.5x |
| 15 | 30..37 | 7,120,046 | 4,614,723 | 35.2% | 14.6 min | 3.0x |

Children per parent: 5.0 at level 14, 4.7 at level 15. The mass sits in the lowest cell of
each window: 14-26 holds 59% of level 14's children, 15-30 holds 93% of level 15's. TU pruning
is rising with the level (16.6% -> 29.5% -> 35.2%) but nowhere near a collapse. Wall per level
(enumeration plus prune) on w1: level 14 about 10 min, level 15 about 20 min, of which the
prune step is 70% (the filter is half of the prune step; the certificate checker is the rest).

## Slice 2 (w3), 07:27Z: the slices are uniform

| level | children | kept | prune wall |
|---|---:|---:|---:|
| 14 | 2,168,958 | 1,528,376 | 4.4 min |
| 15 | 6,714,725 | 4,353,479 | 16.4 min |

Within 6% of slice 0 at both levels, so one slice's profile stands for all 48: the whole tree
holds about 73M kept graphs at level 14 and about 215M at level 15.

## Level 16 (08:13Z): the turnover, measured

Slice 1 (w2), with slices 0, 4 and 5 at the same point by 07:53Z:

| level | window m | children | kept after TU | TU-pruned | growth of kept |
|---|---|---:|---:|---:|---:|
| 14 | 26..33 | 2,160,649 | 1,521,179 | 29.6% | 3.5x |
| 15 | 30..37 | 7,139,035 | 4,629,007 | 35.2% | 3.0x |
| 16 | 34 only | 5,508,061 | 3,482,032 | 36.8% | **0.75x** |

Level 16 produced FEWER kept graphs than level 15. The reach table admits only m = 34 at
level 16 (a 16-vertex graph needs 34 edges to still reach (22,61) with the min-degree lemma),
so level 15's mass at m = 30 can only extend by a degree-4 vertex and every child must be
canonical; the wide-window growth of levels 14-15 is over. Level 16 took about 30 minutes per
slice against the hour the 3x model predicted. From here the windows are 17: 38..43, 18: 42..46,
19: 46..49, 20: 51..52, 21: 56, 22: 61, and every level from 16 on is a single dominant cell.

The tree therefore peaks at level 15 with about 215M kept graphs across the 48 slices, and the
projection above is withdrawn: no extra VMs are needed. w2's own projection for level 17 is
~4.1M children / ~2.6M kept per slice. Expect a slice to finish within a few hours of its
level 15 and the four slices of a worker within the day; the exact level 17-22 profile is
recorded here as it lands.

## Slice 0 (w1) through level 17 (08:22Z)

| level | cells with mass | children | kept after TU | TU-pruned | growth of kept | wall (enum + prune) |
|---|---|---:|---:|---:|---:|---:|
| 16 | 34 (99%), 35, 36, 37, 38 | 5,701,083 | 3,568,177 | 37.4% | 0.77x | ~30 min |
| 17 | 38 (96%), 39, 40, 41 | 2,281,688 | 1,317,923 | 42.2% | 0.37x | ~30 min |

Cells 16-39..41 and 17-42..43 are empty in this slice, as expected: the (16,41), (17,43) and
(18,46) survivors (AMP after-TU counts 1, 8, 38) each live in exactly one slice, so those
cells are checked on the UNION of the 48 slices (gate G3), not per slice. The reach step
itself drops nothing at these levels (reach_kept = children everywhere): the windows are
enforced by the generator, and the pruning is all TU. A slice therefore costs roughly 10, 20,
30, 30 minutes for levels 14..17 and less per level after, about 2.5 h from its level 13 to
(22,61); four slices per worker is about 10 h, so the first-fired workers should finish
around 18:00Z and w13 (fired 07:46Z) around 21:00Z. (11:10Z correction from w12's own
measurement: end-to-end a slice is about 3 h 23 min including the cells the 142-minute figure
left out, so four slices per worker is about 13.5 h: first workers around 20:30Z, w13 and w14
nearer midnight.)

## Slice 0 complete (w1, 09:20Z): the full profile of one slice

| level | children | kept after TU | TU-pruned | cells |
|---|---:|---:|---:|---:|
| 14 | 2,156,374 | 1,519,760 | 29.5% | 8 |
| 15 | 7,120,046 | 4,614,723 | 35.2% | 8 |
| 16 | 5,701,083 | 3,568,177 | 37.4% | 8 |
| 17 | 2,281,688 | 1,317,923 | 42.2% | 6 |
| 18 | 1,567,653 | 980,027 | 37.5% | 5 |
| 19 | 287,082 | 134,849 | 53.0% | 4 |
| 20 | 9,453 | 4,881 | 48.4% | 2 |
| 21 | 90 | 52 | 42.2% | 1 |
| 22 | 0 | 0 | | 1 |

Levels 14..22 took about 142 minutes of wall on the 4-core VM (prune step plus shards
divided by four jobs), from 06:49Z (level 13 complete) to 09:18Z (slice pushed). Slice 0's
(22,61) cell is EMPTY: no F-free, TU-free, minimum-degree-5 graph on 22 vertices with 61 edges
descends from this forty-eighth of the level-13 keep set. The (22,61) answer is the union of
all 48 slices' 22-61.keep.g6 (shipped by the runbook), and the G3 gate is the union of the
(16,41), (17,43), (18,46) cells (slice 0 holds none of them). w2 reports the same shape on
slice 1 (level 17: 2,453,175 / 1,444,839).

## Projection of 07:27Z (withdrawn at 08:13Z, kept for the record)


If kept grows 3.0x per level and the wall 2.5x per level with no collapse, one slice costs
roughly: level 16 ~1 h, 17 ~2.5 h, 18 ~6 h, 19 ~15 h, and levels 20-21 more still, i.e. tens of
hours per slice and 4 slices per worker. The reach windows narrow from level 17 (38..43), 18
(42..46), 19 (46..49), 20 (51..52), 21 (56): from level 19 on, every child must add a vertex of
degree 4 or 5 and be canonical, which is where the tree is expected to collapse, but that is an
expectation, not a measurement. The decision point is w1's level-16 count (due about 08:30Z):
if kept at level 16 is under ~10M the 3x model holds and the fleet needs either more workers
(one per slice, 48 VMs) or a tighter reach table; if it is far below, the collapse has begun.

Levers, in order of cost: (1) more VMs via the routine trigger (Liam's call); (2) skip the
certificate checker on interior levels and re-check only the final keep set's ancestry (loses
the per-level blind check, keeps the final certificates); (3) a root_k > 5 reach table if the
lemmas allow; (4) a stronger hereditary prune (forbidden subgraph list beyond TU).
