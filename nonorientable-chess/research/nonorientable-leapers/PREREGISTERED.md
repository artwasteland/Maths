# A prediction written down before the numbers existed

*Filed 2026-08-17 by claude-relaxed-allen-pybc5u, on branch `claude/relaxed-allen-pybc5u`,
**before** the n = 15 torus row had been computed by anything. The commit that adds this file
contains no n = 15 count; the commit that adds the counts comes after it. The git history is
the receipt, and it is the only reason this document is worth more than a paragraph written
afterwards.*

## Whose theorem this is — not mine, and not this project's either

The law being tested is the **unit-scaling theorem**, and it is published mathematics.
Externally: W. D. Weakley, "Toroidal queens graphs over finite fields", *Australasian J.
Combinatorics* 57 (2013) 21–38, p. 24, states it for the full `GL_2` in exactly this setting;
more generally it is the trivial direction of Ádám's conjecture in the CI-group literature.
In-house: this project proved and published it on 2026-07-03, a month before this file, in
`research/leapers-on-a-torus/`, whose README already names three of the coincidences it
forces (n = 7, n = 11, n = 13). I re-derived it from the torus row before reading either.
That is a rediscovery, not a discovery, and it is labelled as one here and in
`torus-classes.mjs`.

Note also that some of the coincidences the law "explains" are not coincidences: mod 7 the
camel and giraffe are the *same piece* (`4 ≡ −3`), and mod 5 so are the knight and camel. The
prediction below is about counts, and where two leapers share a move set it is trivially true.
From n = 15 on all four move sets are distinct, so the prediction is not trivial anywhere in
the range it covers.

## Why pre-register at all

`torus-classes.mjs` applies that theorem to every `n` in the committed table rather than to
the three spot cases the prior work names: if `u` is a unit mod `n` and `u * V(a,b) = V(a',b')`
as sets, the two leapers have equal toroidal counts at that `n`. It forces 16 equalities
across n = 3..13 and all 16 hold, and a negative control that applies the same predictions to
the Mobius band — where the scaling map is not a symmetry — holds only 3 of 16.

But 16 for 16 on a table that already existed is a **retrodiction**. The argument was written
while looking at the numbers it explains, which is exactly the situation where a wrong
explanation is hardest to notice. The cheap fix is to make it say something about numbers
nobody has computed yet, and to write that down first.

One honest note on the n = 14 torus row, because the order matters and it was not ideal: the
n = 14 computation was already running when the orbit partition for n = 14 was worked out, and
its `zebra = giraffe` equality had appeared in the partial results *before* the prediction for
that `n` was derived. So **n = 14 is not a clean advance prediction and is not claimed as one.**
That is precisely why this file exists.

## The predictions

Orbits of {knight (1,2), camel (1,3), zebra (2,3), giraffe (1,4)} under multiplication by
units mod n. Leapers grouped together are predicted to have **equal** toroidal counts.

| n | predicted orbits | predicted equalities |
|---|---|---|
| 15 | knight \| camel \| zebra \| giraffe | none — all four counts distinct |
| 16 | knight \| camel \| zebra \| giraffe | none |
| 17 | knight \| camel \| zebra \| giraffe | none |
| 18 | knight \| camel \| zebra \| giraffe | none |
| 19 | knight \| camel \| zebra \| giraffe | none |
| 20 | knight \| camel \| zebra \| giraffe | none |
| 21 | knight \| camel \| zebra \| giraffe | none |
| 22 | knight \| camel \| zebra \| giraffe | none |
| 23 | knight \| camel \| zebra \| giraffe | none |
| 24 | knight \| camel \| zebra \| giraffe | none |

Regenerate this table with the orbit code in `torus-classes.mjs`; it depends on nothing but
`n` and the four vector sets.

### What this predicts in words

**The coincidences stop, and they stop for good at n = 15.** Every collapse in the torus row
— all four leapers welded to 10 at n = 5 and to 210 at n = 7, the pairings at n = 4, 6, 8, 9,
10, 11, 13 and 14 — is a small-`n` accident of the vector sets colliding once they are read
modulo a small number. From n = 15 on, no unit carries any one of these four leapers onto any
other, so the theorem predicts **four distinct toroidal counts at every n from 15 upward.**

### How this prediction dies

- Any two of the four torus counts turning out **equal** at n = 15 (or at any n in the table
  above) falsifies it outright, unless a second mechanism is found and named.
- Any *predicted* equality failing would falsify it, but there are none left to fail above
  n = 14, which is what makes the prediction a real risk rather than a safe restatement: from
  here it can only be wrong, never trivially right.

### What it does NOT predict

Nothing about the flat, Mobius or Klein rows: the scaling map is not a symmetry of those
boards. Nothing about *inequality* being interesting — two counts can coincide by accident,
and one such accident is already on the record at n = 5, where knight and giraffe sit in
different orbits and both count 10. An unexplained coincidence at n = 15 would be a weaker
blow than a broken predicted equality, and this file says so in advance rather than after.

## Result — 2026-08-17, and it held

The n = 15 torus row, computed after the commit above and by a different commit:

| leaper | toroidal count, n = 15 |
|---|---|
| knight | 16 252 787 010 |
| camel | 14 152 444 950 |
| zebra | 14 294 528 550 |
| giraffe | 14 128 849 140 |

**Four distinct values, as predicted.** The sharpest part is the pair that had to
move: at n = 14 the zebra and the giraffe are in the same orbit and their counts are
*equal* (933 644 432 each). At n = 15 the orbits split, and so do the counts, by
about 1.2 per cent — a gap small enough that a wrong prediction would have been easy
to make and impossible to hide.

The prediction is confirmed at n = 15 and remains open for n = 16..24, where the
table above says the same thing and nothing has computed it.

### How these four numbers were obtained, including the part that is weaker

They come from `leap2 torus <a> <b> 15 -t0`, the column-shift shortcut: on the torus
a constant shift of every column is a free Z_n action on placements, so the count is
`n` times the number of placements whose row-0 piece sits in column 0. That is an
n-fold saving and it is what put n = 15 in reach at all.

Being honest about what that costs: the shortcut was validated against **full**
enumeration at n = 7, 9, 11 and 13, where it reproduces the committed table exactly,
and it is refused outright on the three surfaces where the argument does not hold.
But the four numbers above were each produced by **one** program using **one**
argument, which is a weaker footing than the n = 14 column, where every entry was
computed twice by paths sharing no code. Treat the n = 15 row as a confirmed
prediction rather than as a deposited term, and do not stage it until a second path
has reached it.

## The footing under those four numbers, 2026-08-23

*by `claude-relaxed-allen-rzbv6r`, cloud, servicing handover
`2026-08-17T04-57-11-305Z-n-pybc5u`, which had been open six days.*

The paragraph above asked for two things: full enumeration rather than the
column-shift shortcut, and a second path. Both were run here, in the background of an
ephemeral container, which the handover said could not do it. The calibration is why
it could: `leap2` on the Möbius board takes 1.1 s at n = 12 and 14.2 s at n = 13, a
factor of about 13 a rung, which puts n = 15 near half an hour rather than near a
night. Four cores, and the torus half is a couple of hours.

**Every one of the four values above has now been reproduced by full enumeration,
with no shortcut, by `leap2.c`:**

| leaper | `leap2 torus a b 15`, no `-t0` | agrees with the shortcut |
|---|---|---|
| knight (1,2) | 16 252 787 010 | yes |
| camel (1,3) | 14 152 444 950 | yes |
| zebra (2,3) | 14 294 528 550 | yes |
| giraffe (1,4) | 14 128 849 140 | yes |

**And every one of them has also been reproduced by `leap.c`**, which shares no code with
`leap2.c`: 84, 83, 100 and 86 minutes respectively. So the shortcut is no longer
load-bearing for this row. The four numbers stand on a plain enumeration of every
placement, carried out twice by independent programs, and both agree with the shortcut
that produced them in the first place. `RECEIPT.md` has the commands and the timings.

**The prediction is unchanged and still held**: four distinct values at n = 15, and the
zebra and giraffe, welded together at n = 14, apart here by about 1.2 per cent.

