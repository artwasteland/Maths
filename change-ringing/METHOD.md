# Extending the change-ringing family — new exact terms for A324944–A324949

**The move (P2, reach, 2026-07-03):** all six of J. K. Sønsteby's change-ringing
sequences for 5, 6 and 7 bells carry OEIS keyword **`more`** — the catalogue
explicitly asks for more terms, and none have been added since their 2019
submission. This directory computes those terms **exactly**, with a counter
fast enough to push each sequence past its published truncation point on a
4-core, 15 GB machine.

The object counted is precisely the one defined in `../engine.mjs` (the
faithful port of Sønsteby's definition, verified against every published term
of the family): simple paths of L distinct rows from rounds in the
change-ringing graph G_n, split into *cyclic* (last row adjacent to rounds —
cappable) and the rest (*noncappable*), with `path = cyclic + noncappable`.

## Why the published terms stopped where they did

A plain DFS visits one node per counted sequence, so its cost *is* the count —
the published families all stop where the totals reach ~10¹²–10¹³. Three
changes push the wall out (`count.c`):

1. **2-level lookahead.** The DFS stops two levels short of the target. At
   depth maxL−2 the two deepest (and overwhelmingly dominant) levels are
   counted in O(degree) per node:
   - *cnt engine* (any n): incrementally-maintained counters `cnt[v]` (visited
     neighbours of v) and `cnt2[v]` (visited members of N(v)∩N(rounds)) give
     `#extensions(u) = deg − cnt[u]` and `#cappable = d2(u) − cnt2(u)`; one
     further inlined level at maxL−3 uses a bare mark with exact corrections.
   - *mask engine* (N ≤ 128, i.e. n = 5): visited set and adjacency rows are
     two 64-bit words; the deepest level is AND + popcount, no counters at all.
2. **Symmetry.** φ(p)[i] = (n−1) − p[(n−1)−i] (conjugation by the reversal w₀)
   is an automorphism of G_n fixing rounds and preserving N(rounds) — asserted
   over every edge at startup. Prefixes come in φ-pairs with equal completion
   counts, so only lexicographic representatives are explored (weight 2, or 1
   if φ-invariant): ~2× fewer nodes.
3. **Parallel prefix jobs with checkpointing.** Deterministically-enumerated
   depth-K prefixes are distributed over threads; each finished job appends
   one line to a checkpoint file. A killed run resumes; `driver.sh` is
   re-runnable end to end. Final totals are aggregated from the checkpoint
   file alone, and only printed if every job is present.

## The validation chain (all of it must pass before any new term is believed)

- **All 132 published terms reproduced exactly** — the full runs print every
  level, so each extension run re-derives the published prefix of its own
  sequences (n=4: 24+24 `full`; n=5: 18+18; n=6: 13+13; n=7: 11+11);
  `check-oeis.mjs` compares against dated OEIS JSON snapshots stored here.
- **Independent implementation:** `../engine.mjs` (Sønsteby's rules via his
  recursion, JS/BigInt, no lookahead, no symmetry) agrees with `count.c`
  (rules derived independently as non-adjacent-bit subsets, count asserted
  = Fib(n+1)−1) on every overlapping depth.
- **Fuzz:** `fuzz.mjs` — 60 random graphs, a trivially-correct BigInt
  enumerator vs every count.c mode (`--simple`, cnt engine, mask engine,
  several prefix depths, checkpoint full/partial resume): bit-identical.
- **Internal:** symmetry on vs off identical (n=4 full, n=5 L=14); the two
  engines identical; job mode vs `--simple` identical; the automorphism and
  rule-count assertions run at every startup.

## The runs (`driver.sh` → `runs/`) — all completed 2026-07-03

| run | K | jobs | engine | wall (4 threads) | published terms reproduced |
|---|---|---|---|---|---|
| n6-L14 | 5 | 7,210 | cnt | 978 s | 26/26 |
| n7-L12 | 4 | 3,533 | cnt | ~1,900 s (incl. one resume) | 22/22 |
| n5-L20 | 6 | 3,388 | mask | 9,489 s | 36/36 |
| n6-L15 | 5 | 7,210 | cnt | 9,449 s | 26/26 |
| n7-L13 | 5 | 64,871 | cnt | ~35,700 s across 3 checkpoint resumes (2026-07-07; survived one container restart and one rebase-orphaned-inode recovery — see memory/log.d/2026-07-07T0315Z) | 22/22 |
| n5-L21 | 6 | 3,388 | mask | ≥96,300 s logged, 4 legs (2026-07-18..21: the log records checkpoint resumes at jobs 361, 1686 and 1698, one of them a mid-run reboot at 49.7%; every resume lost nothing; final leg 46,537 s under the systemd harness) | 36/36 |

(Job counts are the φ-deduplicated prefix counts; see each `runs/*.log`.
The n7-L12 run was killed mid-flight by a harness timeout and **resumed from
its checkpoint losing nothing** — the mechanism working as designed.)

## The new terms

| bells | L | cyclic | path | noncappable |
|---|---|---|---|---|
| 5 | 19 | A324944(19) = 406436091978 | A324945(19) = 12500104398912 | 12093668306934 |
| 5 | 20 | A324944(20) = 2059526455302 | A324945(20) = 62535460933312 | 60475934478010 |
| 5 | 21 | A324944(21) = 10379809487334 | A324945(21) = 311327372361512 | 300947562874178 |
| 6 | 14 | A324946(14) = 268627091334 | A324947(14) = 15581060125092 | 15312433033758 |
| 6 | 15 | A324946(15) = 2417188927944 | A324947(15) = 155784508130046 | 153367319202102 |
| 7 | 12 | A324948(12) = 1396188899504 | A324949(12) = 83655954433944 | 82259765534440 |
| 7 | 13 | A324948(13) = 21639187630450 | A324949(13) = 1509862407105164 | 1488223219474714 |

Fourteen new terms for Sønsteby's six published sequences, seven for the staged
noncappable family (`/oversight/oeis/noncappable-change-ringing/`, b-files
extended). The A324946/7 L=14 values were computed **twice** — in the L=14
and L=15 runs, whose different maxL puts them through different lookahead
code paths — and agree exactly; likewise the n=7 L=12 values were computed
twice (the L=12 and L=13 runs) and agree exactly. The n=5 L=19/L=20 values
were likewise computed twice (the L=20 run, and again through the different
lookahead paths of the 2026-07-21 L=21 run) and agree exactly. Growth ratios
continue smoothly (path: multiplied by 4.98 at the n=5 L=21 step vs 5.00 the
step before, by 10.0 at n=6, by 18.05 at n=7 vs 18.06 prior; cyclic: by 5.04
at n=5 vs 5.07 prior, by 9.0 at n=6, by 15.50 at n=7 vs 15.19 prior).

**The next rungs, priced:** n=7 L=13 — **DONE 2026-07-07** (~10 h across
checkpoint resumes, exactly as priced). n=5 L=21: **DONE 2026-07-21** (the
~13 h estimate was right about CPU cost but the box was shared with another
long compute and the run absorbed a harness kill plus a mid-run reboot, so
the logged wall came to ~27 h across 4 checkpoint-resumed legs; the systemd
harness in `systemd/` is what carried it home). Still open: n=7 L=14 is ~×18
again (~7.5 days: checkpoint-safe, but it wants a dedicated box). n=6 L=16 is
~×10 L=15 (~28 h: a bigger box or a smarter counter). n=5 L=22 is ~×5 the
L=21 run (~2.5 days at this box's shared throughput).

## The n5-L21 verification pass (2026-07-23)

Beyond the standing validation chain above, the L=21 landing got its own
independent checks (artifacts in `codex-verify/`, produced by an OpenAI
codex CLI agent working from written briefs, directed and audited by the
instance that landed the terms; the scripts are committed and re-runnable):

- **Fresh catalogue check:** new OEIS snapshots pulled 2026-07-23
  (`oeis-A32494{4,5}-2026-07-23.json`); all 36 published terms reproduced
  exactly against the live catalogue and L=19..21 confirmed still absent
  (`SNAP_DATE=2026-07-23 node check-oeis.mjs 5 runs/n5-L21.out`).
- **Independent re-aggregation** (`codex-verify/reaggregate.py`): a
  from-scratch Python rebuild of the 5-bell graph and the depth-6
  phi-deduplicated prefix enumeration, parsing `runs/n5-L21.ck` with its own
  parser (never count.c's aggregation path). Job-set audit: 3,388 expected
  representatives, 3,388 unique checkpoint lines, none missing, none extra,
  no duplicates, every stored weight agreeing with the independent
  enumeration. All 21 levels match `runs/n5-L21.out` exactly
  (`codex-verify/REPORT.md`).
- **Blind from-definition enumerator** (`codex-verify/blind/`): a C counter
  written from the verbatim OEIS definition text alone (the worker was never
  shown a single published or computed value; no network). Its cyclic counts
  match A324944 on all of L=1..13 and its path counts match A324945 on
  L=2..13. Its one divergence is the degenerate edge L=1, where it argues
  the single-row sequence trivially ends where it starts, so under the
  literal "does not satisfy criterion 4" wording path(1) should be 0 where
  OEIS has a(1)=1: a convention choice at the edge, not a counting
  discrepancy. It also noticed, blind, that the definition's length footnote
  is in tension with the stated maximum length 5!=120 (an explicit closing
  repeat would allow 121 written rows), and resolved it the way the
  published terms do.

## Files

- `count.c` — the counter (gcc -O3 -march=native -o count count.c -lpthread).
- `driver.sh` — the checkpointed run sequence.
- `fuzz.mjs` — random-graph validation vs a BigInt reference.
- `check-oeis.mjs` — output vs the dated OEIS snapshots.
- `oeis-A32494?-2026-07-03.json` — the six entries as they stood at
  extension time (all keyword `more`; the absence-of-newer-terms record).
- `runs/` — outputs, logs, checkpoints (the raw evidence).
