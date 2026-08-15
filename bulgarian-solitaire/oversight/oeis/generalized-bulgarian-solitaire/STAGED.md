# Generalized (s-)Bulgarian solitaire: settling-time sequences (staged for a DOI; OEIS via a human)

**The game.** *s-Bulgarian solitaire* (well-behaved sigma-Bulgarian with `sigma(h)=min(h,s)`;
this is exactly Brian Hopkins's operation `H_s`, and `s=1` is classic Bulgarian solitaire). A
hand is a partition of `n`. One move: from every pile of size `h` remove `min(h, s)` cards,
collect ALL removed cards into ONE new pile, drop emptied piles, re-sort. Deterministic on the
finite set of partitions of `n`, so every hand runs a transient tail into an eventual cycle.

**What is already known (reproduced here, not claimed).** Hopkins (*INTEGERS* 24A, 2024, #A9)
proves closed forms for the *recurrent* structure of `H_s` for every `s`: the number of
recurrent (cyclic) hands is a generalized binomial coefficient (for `s=2`, the trinomial
triangle A027907; so at a *square* number of cards it is the central trinomial coefficient
A002426), and the number of loops and the Garden-of-Eden count also have closed forms. Our
engine reproduces Hopkins's recurrent formula exactly for `s=1..5` at `n<=40`
(`research/bulgarian-solitaire/verify-s.mjs`), and for `s=2,3` across the whole staged range
`n<=55` (`verify-staged.mjs`, next to this file). It also reproduces the `s=1` catalogued facts
before trusting any new value, each only as far as the reference terms embedded in the verifier
go: Pascal A007318 and cycles A037306 to `n=28`, longest cycle A183110 to `n=21`, Garden of Eden
A123975 to `n=20`.

**What is new (staged).** The *settling time* of `H_s` for `s>=2` has no theorem in the
literature and no OEIS entry we could find (Eriksson-Jonsson-Sjostrand study asymptotic limit
shapes; Olson bounds cycle length; Hopkins characterizes the recurrent set but not the
transient). Ten sequences, `n=1..55`, b-files alongside this README:

| sequence | s | b-file | first terms (n=1..) |
|---|---|---|---|
| total settling time `S(n)` | 2 | `b-total-settle-s2.txt` | 0, 1, 1, 2, 8, 23, 20, 26, 44, 89, 186, 414, 353, ... |
| total settling time `S(n)` | 3 | `b-total-settle-s3.txt` | 0, 1, 2, 3, 4, 7, 20, 45, 78, 87, 87, 114, 176, ... |
| worst-case settling `maxTail(n)` | 2 | `b-max-tail-s2.txt` | 0, 1, 1, 1, 2, 4, 2, 2, 3, 5, 6, 9, 6, 6, 6, ... |
| worst-case settling `maxTail(n)` | 3 | `b-max-tail-s3.txt` | 0, 1, 1, 1, 1, 1, 2, 4, 4, 4, 2, 2, 3, 5, 5, ... |
| Garden of Eden `ge_s(n)` | 2 | `b-goe-s2.txt` | 0, 1, 1, 2, 4, 6, 9, 13, 18, 26, 36, 50, 67, ... |
| Garden of Eden `ge_s(n)` | 3 | `b-goe-s3.txt` | 0, 1, 2, 3, 4, 7, 11, 16, 23, 32, 44, 60, 80, ... |
| number of loops | 2 | `b-num-cycles-s2.txt` | 1, 1, 1, 2, 1, 1, 1, 2, 3, 2, 1, 1, 1, 3, 4, ... |
| number of loops | 3 | `b-num-cycles-s3.txt` | 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 2, 4, 4, 4, 4, ... |
| recurrent hands | 2 | `b-recurrent-s2.txt` | 1, 1, 2, 3, 2, 1, 3, 6, 7, 6, 3, 1, 4, 10, 16, ... |
| recurrent hands | 3 | `b-recurrent-s3.txt` | 1, 1, 1, 2, 3, 4, 3, 2, 1, 3, 6, 10, 12, 12, 10, ... |

(The Garden-of-Eden, number-of-loops, and recurrent-count sequences have Hopkins's closed forms
but no OEIS entry as an `n`-indexed sequence for this map. They are staged with the A9
cross-reference so provenance is clear; the *settling* sequences are the ones with no theorem at
all.)

**On the OEIS-absence claim, downgraded.** The computing session reported all ten sequences
absent from OEIS on 2026-07-19, searched by their digit strings. **No query log for that search
is committed in this repository**, so there is nothing here a reader can check, and the claim is
recorded as *what a session reported*, not as an established fact. The human depositor re-runs
the search on the actual deposit date and commits the log with it. (A search log does exist for
other directories under `research/oeis-term-coverage/absence/`; it does not cover this one.)

**The clean law (a checked conjecture).** At `n = s*T_k` (an `s`-fold triangular number) every
hand converges to one steeper staircase `(sk, s(k-1), ..., s)`, and the worst-case settling time
is:

```
maxTail(s*T_k)  =  k^2 - k   if s = 1     (Igusa 1985 / Etienne 1991)
                =  k^2       if s >= 2     (NEW; verified s=1..7, k<=7, n<=56)
```

A `+k` jump at the first step, uniform across all heavier games. Offered as a conjecture from
exhaustive computation, not a proof. The exact range checked is the `s in 1..7`, `k in 1..7`,
`n = s*T_k <= 56` loop at `research/bulgarian-solitaire/verify-s.mjs` section 3, which is **33
`(s,k)` cases**, the largest being `s=2, k=7, n=56`. It is not checked beyond `k=7` at any `s`.

## Verify (do this before believing anything above)

```sh
node oversight/oeis/generalized-bulgarian-solitaire/verify-staged.mjs   # 17/17, 30-45s: checks THESE b-files
node research/bulgarian-solitaire/verify-s.mjs                          # 15/15, ~8s:  checks the mathematics
```

The two do different jobs and neither substitutes for the other. `verify-s.mjs` never opens a
b-file: it checks the map and the laws. `verify-staged.mjs` reads all ten b-files in this
directory and reproduces every term in them, so corrupting one digit of one file turns it red.

**Do not run `derive.mjs` to check a b-file.** `derive.mjs` is the producer: it *rewrites* the
files, and a producer can only ever agree with itself. It is here for reproduction from scratch
(`node derive.mjs 55 2`, `node derive.mjs 55 3`, self-contained, no imports), which is a
different thing from verification.

### Exactly what backs each staged term

"Checked N ways" is worth nothing unless the ways differ, so here is what differs. All four
paths share one thing and one thing only: the definition of the move, which is itself checked
three independent ways in `verify-s.mjs` (min-subtraction; Hopkins's multiplicity formula;
equality with the classic Bulgarian move at `s=1`).

| path | what it is | what it does NOT share | staged terms it reaches |
|---|---|---|---|
| **P1** reverse-BFS | `engine-s.mjs analyze()`: distance to the cyclic set by reverse breadth-first search | nothing structural: it is the *same algorithm* the producer `derive.mjs` uses, separately transcribed | all 550 (all 10 files, n=1..55) |
| **P2** forward memo | own functional graph, own cycle marking, tails by forward iteration with a memo | graph construction and the distance computation | 200 (`total-settle` and `max-tail`, s=2 and 3, n=1..50) |
| **P3** Hopkins Thm 5 | the published closed form, a coefficient of `(1+x+...+x^s)^(m+1)` | everything: it builds no graph, and it is an outside author's result | 110 (`recurrent`, s=2 and 3, n=1..55) |
| **P4** `s_explore.py` | separate-language implementation: own partitioner, own move, own cycle detection, `lru_cache` forward tails | everything but the definition of the game | 400 (all 10 files, n=1..40) |

Read honestly, that means:

- **Every one of the 550 staged terms is recomputed** by at least one path and held to the line
  on disk. Before 2026-07-27 the number was zero: a mutation prober rewrote all 550 terms at once
  and `verify-s.mjs` produced byte-identical output and exit code 0
  (`research/oeis-term-coverage/coverage-before.json`).
- **P1 alone is not a cross-check.** It shares its algorithm with the producer, so on its own it
  catches transcription and staging mistakes, not a mistake in the reverse BFS itself.
- **The gaps, named and counted. 470 of the 550 staged terms are reached by at least two
  structurally different paths. The other 80 rest on P1 alone**, and they are exactly these:
  `S(n)` and `maxTail(n)` at **n = 51..55** for both `s` (4 files x 5 terms = 20), and
  `ge_s(n)` and the loop count at **n = 41..55** for both `s` (4 files x 15 terms = 60).
  The first 20 close with a one-line change (`FWD_N = 55` in `verify-staged.mjs`) costing about
  15 more seconds, declined to keep the gate inside a minute.
- The 60 Garden-of-Eden and number-of-loops terms above `n=40` are the bigger hole, and the
  cheaper one to close: Hopkins gives closed forms for **both** statistics, and neither is
  implemented here. Adding them would extend P3 to those two families across the whole staged
  range at no measurable cost. That is the obvious next improvement to this gate.
- **P4 is skipped, loudly, if `python3` is not on PATH.** The gate still passes in that case, and
  says on its own output that it did. Run `python3 research/bulgarian-solitaire/s_explore.py
  --check 40` yourself if you want that path confirmed separately.

## Why no paste-ready OEIS draft

Per the project's 2026-06-18 steer, OEIS forbids AI-authored and automated submissions, so there
is no paste-ready `draft.txt` here: the math is exact and verified, but the *authoring* must be
done by a human who has independently checked it. The path is Zenodo for a DOI (`.zenodo.json`,
depositor: the human) and an offer to a mathematician (or to Hopkins, whose theorems these
extend) to author any OEIS entry as themselves.

## Files

- `b-*.txt`: the ten staged b-files, `n=1..55`. Never edit one. If a check disagrees with a
  term, that is a discovery to report, not a typo to correct.
- `verify-staged.mjs`: the gate that binds those files. 17 assertions, 30 to 45 seconds
  depending on machine load (31s measured on an idle box, 45s on a busy one).
- `derive.mjs`: the producer. Self-contained. Rewrites the b-files. Not a check.
- `.zenodo.json`: deposit metadata.

**Live showing.** `/strata/the-longer-way-home/` operates the game and checks every number in the
browser; `/strata/the-longest-way-home/` is the `s=1` original.
