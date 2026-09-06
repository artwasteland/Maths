# Task O1b: point-by-point augmentation (module pts/), follow-up

Read REPORT.md and ptsenum.c in this directory (your predecessor's generator; its canonical
augmentation and mutation controls are correct, but block-by-block levels explode: PTS(13,23)
reached 482,568 partial systems at level 10 of 23). Restructure the generation as
POINT-BY-POINT (row) canonical augmentation in the style of Kaski and Östergård,
Classification Algorithms for Codes and Designs (Springer 2006), Chapter 6: process points
in order; when point k is processed, add ALL blocks whose smallest point is k at once (a
partial matching of the points above k covering every pair {k, x}, x > k, that is not a leave
pair); the intermediate objects are "k-row-complete" partial systems, far fewer than
block-by-block prefixes; apply the canonical-parent test to each row-complete child. Keep the
leave constraints derived in code (the leave edge budget and per-point residuals), and add the
pruning that a point's remaining uncovered pairs must be decomposable given the remaining
block budget. Keep the same output and manifest formats, and add the generator's own sha256
to the manifest.

Controls, in this order, with wall time: STS(7)=1, STS(9)=1, STS(13)=2, STS(15)=80 (the classic
count; must complete), PTS(14,28) two ways (generator vs point deletion from the 80 STS(15) with
--delete-point; counts must agree), then pts-13-24 (expected ~2e2), pts-13-23 (~8e3), pts-14-27
(~4e5) as full runs if they fit in the ten-minute test rule, else in the background under nice
with logs and a projected total from the measured rate; and a timed one-leave-type shard of
pts-15-32 (the 9-cycle leave) with classes per second. Mutation tests must still go red. Write
`<file>.DONE` markers (record count + sha256) on completed datasets per CONTRACT Section 8.
