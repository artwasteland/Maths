# Where the G3 survivors live: canonical ancestry of the 47 known after-TU graphs

`ancestry.c` replays udenum's canonical-parent rule (delete the first minimum-degree vertex in
nauty's canonical order, densenauty with defaultptn, the same libnauty udenum links) from a
graph6 record down to a given order. Validation: for 240 generated level-12 records of the
local control run, every computed parent and grandparent (322 records) is a generated level-11
or level-10 record of that run, 0 missing.

Applied to the 1 + 8 + 38 after-TU survivors at (16,41), (17,43), (18,46) (the calibration
DAGs' keep sets, `embed/scratch/g3/survivors-*.g6`), the level-13 ancestors fall into only
four cells and, by `run-dag2.py`'s `slice_of` (sha256 of the record, first 8 bytes, mod 48),
only four slices. Every one of the 47 has its level-12 ancestor generated AND kept by the
local run, so no survivor is lost below level 13.

| slice | (16,41) | (17,43) | (18,46) | total |
|---|---:|---:|---:|---:|
| 8 | 0 | 0 | 1 | 1 |
| 18 | 0 | 0 | 2 | 2 |
| 42 | 0 | 1 | 10 | 11 |
| 46 | 1 | 7 | 25 | 33 |

Prediction for the G3 gate (`aggregate-slices.py`): the union stays at 0 / 0 / 1 until slices
18, 42 and 46 finish, and then must reach exactly 1 / 8 / 38. Slice 8 is finished and holds
exactly the one (18,46) survivor it should. The chains are in `survivors-chains.txt`.

**14:40Z, first live test.** Slice 18 finished level 18 with exactly 2 kept graphs at (18,46),
the two the table predicted for it (both present in the union, which now holds 3 of 38);
slices 42 and 46 remain.
