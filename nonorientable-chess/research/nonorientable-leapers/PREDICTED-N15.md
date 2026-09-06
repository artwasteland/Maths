# Twelve numbers guessed before they were counted

*Filed 2026-08-20T23:20Z by claude-relaxed-allen-amj0kh (the Artificial Wasteland), on
branch `claude/relaxed-allen-amj0kh`. At the moment of writing, the exhaustive n = 15
enumeration had been running for 10 minutes and **had returned no count**: precisely, its
output directory held four zero-byte stderr files for the four jobs then running and zero
result files, which is recorded in the commit message of this file. The commit that adds
this document contains no n = 15 Mobius or Klein count, because none existed anywhere, in
this repository or outside it. The commit that adds them comes after. As with `PREREGISTERED.md` next door, the git history is the receipt and it is the
only reason this is worth more than a paragraph written afterwards.*

## What is being predicted, and by what

Every count in this directory is an exact enumeration. This file asks whether they have
to be, or whether a one-line model gets close enough to be interesting.

The model is old and is not ours. Under the permutation convention only one kind of pair
of cells can both be occupied: two cells in different rows and different columns. Call
the number of *attacking* such pairs `P`. A uniform random permutation seats both cells
of a given pair with probability `1/(n(n-1))`, so a random permutation carries
`E = P/(n(n-1))` attacking pairs on average, and if those pairs were independent the
count would be `n! exp(-E)`. `density.mjs` computes exactly this and says, correctly, that
it is a heuristic and not a theorem. OEIS **A137774** already carries the limiting form
of it, `a(n)/n! -> e^-4`.

Two things are new here, and both are in `pairs-model.mjs`.

**One. `P` has an exact closed form on all four surfaces, and the forms say something.**

| surface | `P` | free boundaries |
|---|---|---|
| torus | `4n²` | 0 |
| Klein | `4n² - k`, `k` in {6,8,10,16} by leaper and parity | 0 |
| Mobius | `4n² - 2(a+b)n - k'` | 1 |
| flat | `4(n-a)(n-b) = 4n² - 4(a+b)n + 4ab` | 2 |

The linear coefficient runs `0, 0, -2(a+b), -4(a+b)` as the number of free boundaries
runs `0, 0, 1, 2`. Every difference in constraint count between these four surfaces is a
boundary effect; the half-twist itself moves only a constant. That is the reason the
Mobius counts sit far above the torus counts while the Klein counts sit almost on top of
them: the Mobius band is the only one of the four that is open in a direction, so it is
the only one that loses a term of order `n`. `pairs-model.mjs` fits each form on three
points, tests it on the rest of n = 6..25, and fails loudly if one breaks. It also checks
the boundary law and the flat form `4(n-a)(n-b)` as assertions rather than printing them
as prose.

**Two. The residual is smooth, so it predicts.** Write

    a(n) = n! · exp(-P/(n(n-1))) · R(n)

so `R` is exactly what the independence heuristic misses. `R` is not 1 and is in no hurry
to become 1: at n = 14 it runs from 0.775 to 0.933 across the sixteen rows. But it moves
slowly. So the rule, which has **no free parameters and nothing to tune**:

> **Predict `a(n)` by carrying `R(n-1)` forward one step unchanged.**

## The rule was scored before it was used, on 39 integers nobody here computed

The four **flat** rows are published: A137774 (knight), A189358 (camel), A189565 (zebra),
A189563 (giraffe), read from the OEIS JSON API on 2026-08-20 and carried in
`pairs-model.mjs` with an alignment control that must fire (it checks that the neighbouring
index *fails* to match, because an off-by-one here is the mistake this directory has
already made once). They reach n = 24, n = 24, n = 24 and n = 23, far past anything this
project has enumerated.

Carrying `R` forward one step across n = 15..24 scores the rule against **39 published
values**:

- median absolute error **0.357 %**
- worst **1.569 %** (knight at n = 15, the first step and the one with least history)
- and the errors are *systematic*, drifting from about +1.6 % down through zero to about
  -0.4 %, which means a better rule certainly exists. It is not used here, because a rule
  tuned on the test set is not a prediction.

## The negative control, added before any result came back

*Added 2026-08-20T23:38Z, with the enumeration still returning nothing (`ls out/*.done`
still empty). It belongs above the predictions rather than below them, because it makes them
riskier, not safer.*

A median error of 0.357 % means nothing on its own. So the identical rule, unadjusted, was
pointed at the nearest neighbouring family using the same convention: the **n-queens** counts,
**A000170**, published to n = 27. A queens placement is a permutation with no two on a
diagonal, which is one-per-row-and-column exactly as here.

**It is wrong by about 32 %**, at every n from 15 to 27, and it never recovers.

The failure is structured, and it names the rule's precondition. A queen is a *slider*, so
`P = 2(2C(n,3) + C(n,2)) ~ (2/3)n³` and `E = P/(n(n-1)) ~ (2/3)n` grows without bound. A
leaper's `P` is `4n² + O(n)`, so its `E` settles on **4**. The residual can only stop moving
once `E` does; for the queens it shrinks by a near-constant factor of **0.764** per step, and
`1/0.764 - 1 = 31 %` is exactly the amount the rule is wrong by.

So the claim is bounded in advance: **this rule is for fixed-jump pieces, where P is
quadratic.** `pairs-model.mjs` runs the control on every invocation, checks the queens `P`
formula against brute force over n = 3..9, and **fails if the control does not fail**.

## The predictions

`node pairs-model.mjs --predict`, from the committed n = 14 terms.

### Blind: the eight Mobius and Klein values

**Nothing has ever computed these, here or anywhere.** They are being enumerated as this
file is written, by `leap.c` and `leap2.c` independently, and neither had returned when
this was committed.

| surface | leaper | R(14) | predicted a(15) |
|---|---|---|---|
| Mobius | knight | 0.90594 | 25,269,523,823 |
| Mobius | camel | 0.81967 | 26,124,295,977 |
| Mobius | zebra | 0.82163 | 31,083,857,079 |
| Mobius | giraffe | 0.82101 | 30,474,035,008 |
| Klein | knight | 0.90657 | 16,789,829,702 |
| Klein | camel | 0.79881 | 14,935,667,527 |
| Klein | zebra | 0.78515 | 14,820,718,528 |
| Klein | giraffe | 0.77527 | 14,634,251,035 |

### Not blind, and said so plainly: the four torus values

The four torus counts at n = 15 **were already in this repository** when this file was
written, in `PREREGISTERED.md`, produced on 2026-08-17 by the column-shift shortcut. I had
read that file before building the model. So these four are a check on a number I had
already seen, not a blind test, and they are listed separately for that reason and given
no weight in the headline.

| surface | leaper | predicted a(15) | known (shortcut, 2026-08-17) | error |
|---|---|---|---|---|
| torus | knight | 16,789,255,770 | 16,252,787,010 | +3.30 % |
| torus | camel | 13,987,890,878 | 14,152,444,950 | -1.16 % |
| torus | zebra | 14,315,868,625 | 14,294,528,550 | +0.15 % |
| torus | giraffe | 14,315,868,625 | 14,128,849,140 | +1.32 % |

## Where this model is guaranteed to be wrong, stated in advance

The zebra and the giraffe have **equal** torus counts at n = 14 (933,644,432 each) and
identical `P`. The model therefore has no mechanism whatever to separate them and predicts
the *same* number for both at n = 15. The truth, already known above, is that they differ
by about 1.2 %. So the model is blind to precisely the effect the unit-scaling law in
`PREREGISTERED.md` exists to explain: the orbit split at n = 15 that makes the coincidences
stop for good. Two files in one directory, one predicting a split and one unable to see it,
is not a contradiction. It is the difference between a symmetry argument and a density
argument, and it is worth having both.


## Result — the whole Mobius row, scored 2026-08-23

*by `claude-relaxed-allen-rzbv6r`, cloud, from the same background run that took the
n = 15 torus row to full enumeration. See `RECEIPT.md`.*

**All eight are bound.** Every value below was computed twice, by `leap2.c` and by
`leap.c`, which share no code, both full enumerations with no shortcut, and the two agreed
every time. Sixteen runs, about 21 core-hours, on four cores in one ephemeral container.

| surface | leaper | predicted, 2026-08-20 | counted, 2026-08-23 | error |
|---|---|---|---|---|
| Mobius | knight | 25,269,523,823 | **25,064,458,638** | **+0.818 %** |
| Mobius | camel | 26,124,295,977 | **25,670,090,508** | **+1.769 %** |
| Mobius | zebra | 31,083,857,079 | **31,389,175,160** | **-0.973 %** |
| Mobius | giraffe | 30,474,035,008 | **31,121,021,962** | **-2.079 %** |
| Klein | knight | 16,789,829,702 | **16,567,600,600** | **+1.341 %** |
| Klein | camel | 14,935,667,527 | **14,725,592,660** | **+1.427 %** |
| Klein | zebra | 14,820,718,528 | **15,076,395,068** | **-1.696 %** |
| Klein | giraffe | 14,634,251,035 | **15,010,150,442** | **-2.504 %** |

Both by `leap2` and by `leap.c`, both full enumerations, no shortcut anywhere: 49 and 84
minutes for the knight, 47 and 86 for the camel, on contended cores. **Two programs that
share no code returned the same integer in each case**, which is this directory's condition
for calling a term bound.

### The sign observation, and its death forty minutes later

When only those two rows existed, both errors had the **same sign** and both were
overestimates, and this section said so: *"With two points that is an observation and not a
pattern, and it is written down here so that the remaining six can confirm or kill it
rather than be read through it afterwards. If all eight come in high the residual `R` is
drifting down faster than the rule's carry-forward assumes, which would be a real finding
about the model; if they scatter, this sentence was noise."*

**It was noise.** The next row to arrive was the Möbius zebra, and it went the other way:

    mobius zebra n = 15   predicted 31,083,857,079   counted 31,389,175,160   -0.973 %

The sentence is kept rather than deleted because a guess that was written down before the
data and then refuted by the data is worth more on the page than a guess quietly removed.
Three rows, errors +0.818, +1.769 and -0.973 per cent, all well inside the model's stated
3 per cent threshold and **scattered in sign**. The rule is doing what its author claimed
for it and nothing more.

The zebra figure went in as one path, with a note saying that if `leap.c` disagreed then the
enumeration would be wrong rather than this paragraph. `leap.c` finished at 102 minutes and
returned the same integer, so the refutation above is **bound**, not provisional.

**Read that against the model's own stated failure condition**, which is above and was
written before the number existed: anything off by more than about 3 % means the rule does
not transfer to the twisted boards. It transferred. And the comparison worth making is not
against the flat rows the rule was scored on, but against the four **torus** rows in this
same file, which were not blind because they were already in the repository when the model
was built: those errors run -1.16 % to +3.30 %. The one row nobody had seen came in tighter
than three of the four the author had.

**This section was written provisional and is no longer.** It first went in with the
`leap2` value alone and a warning that `leap.c` had not finished and that a disagreement
would make the section wrong rather than the enumeration. `leap.c` then finished and
returned the same integer. The warning is left described here rather than deleted, because
the order in which a claim firmed up is part of the claim.

The term is **still not staged**, and that is not the same thing as unbound. The staged
b-files in `oversight/oeis/nonorientable-leapers/` are regenerated from a complete
`terms-1-N.tsv`, and a complete n = 15 column needs all sixteen values including the flat
row that nothing here computed. `n15-progress.tsv` in this directory records which five of
the sixteen are bound, so the next session starts from there rather than from scratch.

**All eight blind rows now have a count.** Mean absolute error **1.576 per cent**, worst
**2.504**, every one inside the 3 per cent this file set for itself before the numbers
existed. The rule has no free parameters and nothing was tuned to make that happen.

### The sign is a property of the leaper, not the surface

This is the thing the completed table shows and no partial one could, and it is written
here as **post-hoc**, because I found it by looking at eight rows rather than by predicting
it:

| leaper | a+b | Mobius | Klein |
|---|---|---|---|
| knight (1,2) | 3 | +0.818 % | +1.341 % |
| camel (1,3) | 4 | +1.769 % | +1.427 % |
| zebra (2,3) | 5 | -0.973 % | -1.696 % |
| giraffe (1,4) | 5 | -2.079 % | -2.504 % |

Eight rows, two surfaces, and the sign agrees across the surfaces every time. The model
overestimates the two short leapers and underestimates the two long ones, on both twisted
boards, and the split falls exactly where `a+b` crosses from 4 to 5. That is not obviously
an accident: the closed form for `P` on the Möbius band in the table further up carries a
`-2(a+b)n` term, so `a+b` is already the parameter the constraint count turns on, and a
residual that drifts with it is the shape you would expect if the independence heuristic
degrades with leaper reach.

**But eight points found after the fact are a hypothesis, not a result**, and the honest
move is the same one this file made before: say what would kill it. So, in advance:

> At n = 16 the same rule, carried forward from the n = 15 terms above, should overestimate
> the knight and the camel and underestimate the zebra and the giraffe, on both the Möbius
> band and the Klein bottle. Eight signs, predicted. Any one of them wrong and this section
> is a coincidence in eight rows rather than a property of the model.

Nothing has computed n = 16. The cost, measured on this machine, is a factor of about 13 a
rung, so about eight hours a case for `leap2` and seventeen for `leap.c`, which is a very
different order of job from this one and wants the box rather than a container.

## How this dies

- Any Mobius or Klein prediction off by more than about 3 %, which is roughly twice the
  worst error the rule made on the whole published flat range, means the rule does not
  transfer to the twisted boards and the flat score was luck of the domain.
- The closed forms are exact claims, not approximations. A single `P` in n = 6..25 that
  misses its form kills that row outright, and `pairs-model.mjs` exits non-zero if one does.

## Scoring it

    node pairs-model.mjs --score

reads `terms-1-15.tsv` once it exists and prints predicted against actual for all twelve.
