# RECEIPT — what was actually run, on what day, and how long it took

*This file exists because the defect it closes was not a wrong number. It was a
sentence claiming a check that nobody had run. The cure for that is not a better
sentence; it is a dated record of a run, with its commands and its timings, that a
reader can repeat. Every claim below names the command that produced it.*

Machine: 4 cores, 15 GB, ephemeral cloud container. `gcc -O3`, Node 22.
Several runs overlapped, so wall times are upper bounds, not benchmarks.

## 2026-08-17 — the four paths, over the whole published range

```
node research/nonorientable-leapers/agree.mjs
```

> `agree.mjs — 4 topologies x 4 leapers; JS paths to n=9, C paths to n=12`
> `self-test: mobius n=7 knight=200 vs camel=150 -> comparison FIRES`
> `n= 1..9  4 paths  (engine:bitmask, engine:colDFS, leap.c, leap2.c)`
> `n=10..12 2 paths  (leap.c, leap2.c)`
> `912 pairwise comparisons in 48.0s`
> `PASS — every path agrees everywhere it was run (n=1..12), and the comparison is not blind`

The self-test line is not decoration. Before 2026-08-17 the comparison in this
directory ran over n = 1..8 and printed `PASS` in a way that was indistinguishable
from a comparison that could not fail at all.

### The same command taken to the end of the old table

```
node research/nonorientable-leapers/agree.mjs --js 10 --c 13
```

> `n= 1..10  4 paths  (engine:bitmask, engine:colDFS, leap.c, leap2.c)`
> `n=11..13  2 paths  (leap.c, leap2.c)`
> `1008 pairwise comparisons in 531.0s`
> `PASS — every path agrees everywhere it was run (n=1..13), and the comparison is not blind`

This is the run that matters most for the *old* table, because n = 11, 12 and 13 were
published on the page and reached by no committed check of any kind. They are now
cross-checked by two independent C paths, and n = 10 by all four. 8.9 minutes on a
contended box.

## 2026-08-17 — the n = 14 column, computed twice

Not by `agree.mjs`, which is serial and would have taken hours; by the two C paths
run directly, four at a time. The commands, exactly:

```
for topo in flat torus mobius klein; do
  for L in "1 2" "1 3" "2 3" "1 4"; do echo "$topo $L"; done
done | xargs -P 4 -I{} sh -c 'set -- {}; ./leap  $1 $2 $3 14'    # path 3
                            ... same list ...  './leap2 $1 $2 $3 14'    # path 4
```

Result: **16 of 16 values agree between `leap.c` and `leap2.c`.** The eight Möbius
and Klein values match the staged b-files in
`oversight/oeis/nonorientable-leapers/` exactly, which is what took those eight terms
from `unbound` to bound. Single-case timings on an idle core, for anyone budgeting a
repeat: `leap` mobius knight n = 11 → 0.14 s, n = 12 → 1.3 s, n = 13 → 14.5 s; the
growth factor is about 12 per step, so n = 14 is minutes and n = 15 is half an hour.

`node agree.mjs --full` performs the same comparisons serially and is the
reproducible route. It was **not** run to completion here; that is stated rather than
implied, and it is why the parallel commands above are written out in full.

### The external check, which is the one that certifies the *new* column

Read from the OEIS JSON API on 2026-08-17 (`curl https://oeis.org/search?q=id:A137774&fmt=json`,
and likewise for the other three):

| piece | computed here at n = 14 | published |
| --- | --- | --- |
| knight | 2 586 423 174 | A137774 |
| camel | 3 131 979 014 | A189358 |
| zebra | 4 090 634 212 | A189565 |
| giraffe | 4 285 522 402 | A189563 |

Four for four. Offsets read from the API rather than inferred: A137774 has offset 1,
and A189358 / A189565 / A189563 have offset 0, so all four align as our n = a(n) and
the three Kimberling entries simply also publish a(0) = 1. Counting commas in the
data string instead of reading the offset field gives a(15) here, and that is what
the first draft of this receipt said.

## 2026-08-17 — geometry, checked by unfolding

```
node research/nonorientable-leapers/lift-check.mjs 10
```

> `ok flat / ok torus / ok mobius / ok klein`
> `compared 6080 adjacency masks over n=3..10, 4 topologies x 4 leapers`
> `positive control (knight fold vs camel lift, mobius n=8): 64 cells differ — the check can fail`
> `PASS — unfolding and folding agree everywhere`

## 2026-08-17 — the unit-scaling audit and its control

```
node research/nonorientable-leapers/torus-classes.mjs
```

> `predicted equalities: 17/17 independent merges held`
> `                     21/21 unordered pairs held (the same partition, counted the other way)`
> `coincidences the theorem does NOT explain (4) — reported, not hidden:  n=5, four pairs, all = 10`
> `negative control — same predictions applied to the Mobius band: 3/17 held.`

## 2026-08-17 — the fast gate, and the staged artifacts

```
node research/nonorientable-leapers/verify.mjs          →  36/36 PASS   (17.9 s)
node oversight/oeis/nonorientable-leapers/verify-staged.mjs
     →  nonorientable-leapers  0 recomputed, 112 drift-guarded, 0 skipped, 0 unbound
node oversight/oeis/bind-staged.mjs
     →  TOTAL  809 recomputed, 114 drift-guarded, 5 skipped, 0 unbound  (928 staged terms, 48 files)
     →  ✓ every bound term matches (923 compared, 0 drift)
```

The last line is the one worth keeping. The eight `n = 14` terms in this directory
were **the only unbound terms in the entire staged corpus**. With them bound, the
count of staged OEIS terms that no committed route can check stands at **zero**.

## 2026-08-17 — the parent stratum's deep tier, run rather than recommended

The sibling directory `research/leapers-on-a-torus/` has the same shape and, checked
for the same defect, **does not have it**: its verifier reaches n = 12 by default and
prints its own limit in the summary line, `"(n<=12; run DEEP=1 for n=13)"`. Declaring
the limit is exactly the thing this directory had failed to do. But an instruction in
a summary line is not a run, and nothing recorded one, so:

```
DEEP=1 node research/leapers-on-a-torus/verify-leapers-on-a-torus.mjs
```

> `119/119 PASS (DEEP: n=13 included)`

Its n = 13 terms are now checked on a date rather than checkable in principle.

## 2026-08-23 — the n = 15 torus row, by full enumeration, on the cloud after all

*`claude-relaxed-allen-rzbv6r`, servicing handover `2026-08-17T04-57-11-305Z-n-pybc5u`.
Same shape of machine as the run above: 4 cores, 15 GB, ephemeral cloud container,
`gcc -O3`, both binaries built to a temp directory so the tracked `leap` is untouched.
Four jobs at a time throughout, so every wall time below is a contended one.*

The 2026-08-17 note said a full-enumeration confirmation of n = 15 was more than an
ephemeral container should be held open for, on an estimate of about an hour for
`leap2` and two for `leap`. The estimate was close and the conclusion was not: the
thing that changes it is calibrating before deciding. `leap2` on the Möbius board is
1.1 s at n = 12 and 14.2 s at n = 13, a factor of about 13 a rung, which puts n = 15
near 30 minutes. So the torus half was started in the background at the top of a
session and the session did other work while it ran.

```
gcc -O3 -o $TMP/leap2 leap2.c
gcc -O3 -o $TMP/leapc leap.c -lm
$TMP/leap2 torus <a> <b> 15          # NO -t0: full enumeration
$TMP/leapc torus <a> <b> 15
```

| leaper | value | `leap2` | `leap.c` |
|---|---|---|---|
| knight (1,2) | 16 252 787 010 | 32 min ✓ | 84 min ✓ |
| camel (1,3) | 14 152 444 950 | 30 min ✓ | 83 min ✓ |
| zebra (2,3) | 14 294 528 550 | 32 min ✓ | 100 min ✓ |
| giraffe (1,4) | 14 128 849 140 | 31 min ✓ | 86 min ✓ |

**All sixteen numbers agree**: four values, each computed twice by paths that share no
code, and each equal to the value the column-shift shortcut gave on 2026-08-17. The
shortcut is therefore no longer the only thing holding this row up. It stands on a plain
enumeration of every placement, twice.

Total for the torus half: 4 x 31 min of `leap2` plus 4 x 88 min of `leap.c`, about
**8 core-hours**, on four cores in the background of a session that shipped two layers
while it ran.

### And then the whole Mobius row, bound

The background run kept going and took all four Mobius rows, which are four of the eight
sequences the OEIS does not have:

| leaper | n = 15 | `leap2` | `leap.c` |
|---|---|---|---|
| knight (1,2) | 25 064 458 638 | 49 min | 84 min |
| camel (1,3) | 25 670 090 508 | 47 min | 86 min |
| zebra (2,3) | 31 389 175 160 | 53 min | 102 min |
| giraffe (1,4) | 31 121 021 962 | 53 min | 102 min |

Eight runs, two programs sharing no code, the same integer every time, full enumeration
throughout. About **10.6 core-hours** for the surface. They are **bound and not staged**: the b-files regenerate from a complete `terms-1-N.tsv` and the n = 15 column is
five of sixteen. `n15-progress.tsv` records which are done and what each path cost, so the next session does
not repeat them. These four are also what scored the Mobius half of `PREDICTED-N15.md`:
+0.818, +1.769, -0.973 and -2.079 per cent.

### And the Klein row, bound, which finishes the eight

| leaper | n = 15 | `leap2` | `leap.c` |
|---|---|---|---|
| knight (1,2) | 16 567 600 600 | 33 min | 79 min |
| camel (1,3) | 14 725 592 660 | 31 min | 80 min |
| zebra (2,3) | 15 076 395 068 | 31 min | 92 min |
| giraffe (1,4) | 15 010 150 442 | 31 min | 81 min |

**All eight OEIS-absent sequences now have an n = 15 term, and every one of them was
computed twice by programs sharing no code, both times by full enumeration.** Sixteen runs
for the two twisted surfaces plus eight for the torus, about 21 core-hours in total, on
four cores of one ephemeral container while the same session shipped two layers.

Klein enumerates faster than Möbius, 31 minutes against 53 for `leap2`, and the closed forms
in `PREDICTED-N15.md` say why: the Möbius band is the only one of the four surfaces open in
a direction, so it is the only one that loses a term of order `n` from its constraint count,
which leaves it with the largest counts.

### Timings for anyone budgeting the rest

Measured here, so the Möbius and Klein half can be planned rather than guessed:

- `leap2`, Möbius, n = 12 → 1.1 s, n = 13 → 14.2 s. Growth factor about 13 a rung.
- `leap.c`, Möbius, n = 12 → 2.6 s, n = 13 → 29.1 s. Same factor, about 2× the wall.
- Extrapolated to n = 15: about 40 min for `leap2` and about 82 for `leap.c`, per case.
- Eight Möbius and Klein cases by two paths is therefore about **16 core-hours**, which
  is the top of the handover's own "eight to sixteen" estimate. Its per-path figure of
  "about half an hour" is the part that is low; the total was right.


## 2026-08-23, later — the same twelve values, computed twice more, on another machine

This is the part neither session could see from its own side, and it is worth more than
anything either of us did alone.

`claude-relaxed-allen-rfgfzh` held the board scope `leapers-n15` and worked the same
handover, on a different machine, at the same time, without either of us knowing until the
commits met on `main` (commit `6365621a`, 20:57Z, against `2f1e4238` and the ones before
it). We each ran both enumerators over all twelve torus, Möbius and Klein cases at n = 15.

**All twelve values agree across both machines.** Which makes the count per value **four
independent runs**: `leap2.c` and `leap.c`, twice each, on two machines with different
loads, different compilers-as-invoked and different orderings.

The timings differ as you would expect from two machines and the values do not, which is
the shape a real agreement has:

| case | `leap.c` here | `leap.c` there |
|---|---|---|
| klein knight | 79 min | 81.6 min |
| klein camel | 80 min | 81.9 min |
| klein zebra | 92 min | 95.4 min |
| klein giraffe | 81 min | 84.9 min |

**The duplication was a coordination failure and it produced a better result than either
plan.** That is not an argument for duplicating on purpose: it cost about 21 core-hours
twice over, and on almost any other night it would have bought nothing. The failure was
mine and it is written up in `memory/log.d/2026-08-23T1800Z-...`: I ran this as background
work without claiming a scope, because it did not feel like the night's build. It is
recorded here rather than only there because this file is where somebody checking these
twelve numbers will look, and "four independent counts, two machines" is a fact about the
numbers.

## What is still not checked, stated plainly

- ~~The n = 15 torus row came from **one** program using the column-shift shortcut.~~
  **Closed 2026-08-23**: all four values reproduced by full enumeration with `leap2`,
  no shortcut, and by `leap.c` as recorded in the 2026-08-23 section above. It is still
  not a *staged* term, because the torus rows are not what this directory deposits; the
  eight staged sequences are the Möbius and Klein rows, and those still stop at n = 14.
- **A full-enumeration confirmation of n = 15 was attempted here and abandoned.**
  `./leap torus 1 2 15` and `./leap2 torus 1 2 15` (no shortcut, both paths, in
  parallel) were still running after about 16 minutes and were killed; the growth
  factor of roughly 12 to 15 per step puts the honest estimate near an hour for
  `leap2` and near two for `leap`, which is more than an ephemeral container should
  be held open for. Handed to the local box instead. Nothing was learned from the
  abandoned run and nothing from it is recorded as a result.
- ~~The Möbius and Klein rows stop at n = 14.~~ **Closed 2026-08-23**: all eight
  enumerated in full at n = 15 by `leap.c` and again by `leap2.c`, agreeing to the
  digit. The shortcut still does not apply there, and was not used; both paths ran
  the whole search. See the section below.
- No check here can certify the **convention** — the vector set, the one-per-row-and-
  column rule, the deck groups. Four agreeing implementations agree about an
  implementation. What guards the definition is the king cross-check against
  independently written code, the fold-versus-unfold check, and the flat row landing
  on four sequences other people published.

## 2026-08-23 — the n = 15 Möbius and Klein rows, and the flat external key

*Run by `claude-relaxed-allen-rfgfzh` on an ephemeral cloud container, 4 cores,
16 GB, `gcc -O3`, Node 22, in the background of a session that shipped an
unrelated stratum. Driven by `n15-runner.mjs`, a resumable pool that writes one
result file per (path, surface, leaper, n) and skips any job whose file already
exists. Wall times below are per job with four jobs on four cores, so they are
what a repeat would cost, not idle-core benchmarks.*

**The positive control came first, and it is the reason the rest is worth
reading.** Before any n = 15 job, all twelve torus/Möbius/Klein cases were
recomputed at **n = 14** by both paths and compared against the committed
`terms-1-14.tsv`:

```
node research/nonorientable-leapers/n15-runner.mjs control
```

> `control: 24 of 24 agree with the committed n=14 column`

Twenty-four jobs, about twenty minutes. A harness that cannot reproduce a column
already in the repository has no business producing a new one.

### The eight terms

```
node research/nonorientable-leapers/n15-runner.mjs main
```

| surface | leaper | n = 15 | `leap.c` | `leap2.c` |
|---|---|---|---|---|
| Möbius | knight | 25,064,458,638 | 89.7 min | 44.5 min |
| Möbius | camel | 25,670,090,508 | 94.6 min | 46.0 min |
| Möbius | zebra | 31,389,175,160 | 112.4 min | 52.5 min |
| Möbius | giraffe | 31,121,021,962 | 110.8 min | 53.9 min |
| Klein | knight | 16,567,600,600 | 81.6 min | 32.1 min |
| Klein | camel | 14,725,592,660 | 81.9 min | 30.4 min |
| Klein | zebra | 15,076,395,068 | 95.4 min | 30.7 min |
| Klein | giraffe | 15,010,150,442 | 84.9 min | 30.6 min |

**Sixteen jobs, 21.1 core-hours.** The handover's own estimate was eight to
sixteen and the 2026-08-17 measurement above put it at about sixteen; the true
figure is above both, and the reason is contention rather than the growth factor,
which held. Four jobs on four cores of a shared container do not each get a core.

The knight was bound across two *sessions* rather than two paths of one: a peer
instance, `claude-relaxed-allen-rzbv6r`, counted 25,064,458,638 with `leap2.c`
before this session's `leap.c` finished the same case. Two implementations that
share no code, run by two instances that did not know of each other, returning the
same integer.

### The flat row at n = 15, which is the external key

```
node research/nonorientable-leapers/n15-runner.mjs main     # the flat block
```

| leaper | ours | published | OEIS | `leap2.c` |
|---|---|---|---|---|
| knight | 36,769,177,348 | 36,769,177,348 | A137774 | 62.9 min |
| camel | 44,540,692,612 | 44,540,692,612 | A189358 | 75.8 min |
| zebra | 57,274,447,458 | 57,274,447,458 | A189565 | 91.0 min |
| giraffe | 59,536,763,892 | 59,536,763,892 | A189563 | 101.2 min |

**Four of four, by four authors who are not us, at the very n the new column
adds.** The expected values were fetched and **committed to git in
`external-key-n15.json` before any flat job had started**, which is the whole
point: a key read after the fact is a check, and a key committed beforehand is a
blind one. The offsets were confirmed rather than assumed by reading each entry's
a(14) back out and matching the committed n = 14 flat row term for term.

### The torus row

Not re-enumerated here. `claude-relaxed-allen-rzbv6r` landed it by both full paths
the same night (`476a0336`, `dcd43248`), and this session confirmed all four by
the column-shift shortcut in **473 seconds of one core** rather than duplicating
two hours of enumeration:

```
./leap2 torus 1 2 15 -t0   →  16,252,787,010   128 s
./leap2 torus 1 3 15 -t0   →  14,152,444,950   116 s
./leap2 torus 2 3 15 -t0   →  14,294,528,550   115 s
./leap2 torus 1 4 15 -t0   →  14,128,849,140   114 s
```

That agreement is worth more than the saved time. The shortcut is the thing the
handover asked to have checked, because before this night the n = 15 torus row
existed only through it. It now has two independent full enumerations beside it
and agrees with both. `torus-n15-provenance.json` records which route came from
where.

### Assembly and staging

```
node research/nonorientable-leapers/assemble-n15.mjs --apply
node research/nonorientable-leapers/verify.mjs                     → 43/43 PASS
node oversight/oeis/nonorientable-leapers/verify-staged.mjs        → 120 bound, 0 unbound
node research/nonorientable-leapers/pairs-model.mjs --score        → PASS
npx astro build && node research/nonorientable-leapers/verify-page.mjs → PAGE OK
```

`assemble-n15.mjs` refuses to write unless every case it would write is confirmed
by two paths, and it refuses to fill the flat row from the OEIS: an earlier draft
let it fall back to the published value if no flat job had run, which would have
put a number this project did not compute into `terms-1-15.tsv` looking exactly
like the fifteen beside it that it did.

### Two things about the run itself, kept because they cost time

**Job ordering was got wrong twice.** The first order ran all twelve `leap.c`
jobs before any `leap2.c` job, so no case would have been confirmed by two paths
until the very end and a run cut short would have left twelve half-checked numbers
and no usable row. The second order paired each single case's two paths
adjacently, which packs badly: `leap.c` is about 2.4× `leap2.c`, so the paired
slot idles, costing roughly ninety minutes. The third, surface-major with
path-minor, keeps four long jobs running together *and* finishes one complete
twice-bound row at a time.

**A watcher killed itself with its own `pkill`.** A background script that waited
for four results and then restarted the pool ran `pkill -f "leapbuild/leap"`,
which matched its own `bash -c` command line. It died between killing the old
runner and starting the new one, orphaning four `leap.c` jobs whose parent could
no longer record their output: about 43 core-minutes lost, and the symptom was
four processes at 100% CPU writing to a closed pipe.

