# Bulgarian solitaire — the settling time (ledger P2)

**Bulgarian solitaire.** Take `n` cards split into piles (a partition of `n`). One *move*:
remove a card from **every** pile (piles that hit zero vanish), then gather those removed
cards into **one new pile**. Repeat. The map is deterministic on the finite set of
partitions of `n`, so every starting arrangement runs down a **transient tail** into an
eventual **cycle** and stays there forever.

The classical facts are settled and beautiful:

- **Brandt (1982):** when `n = T_k = k(k+1)/2` is *triangular*, there is a **unique fixed
  point** — the staircase `k, k-1, …, 2, 1` — and **every** arrangement reaches it.
- **Igusa (1985) / Etienne (1991):** for triangular `n = T_k`, the worst starting hand
  reaches the staircase in **exactly `k² − k` moves**, and that bound is tight.
- The number of **recurrent** (cyclic) arrangements is **Pascal's triangle** (Etienne); the
  number of **cycles** is OEIS **A037306**; the **Garden-of-Eden** count (arrangements with
  no predecessor) is **A123975**; the **longest cycle length** is **A183110**.

## What this program adds

The natural question Brandt/Igusa answer for *triangular* `n` — *how long until it settles?* —
has no published answer for **all** `n`. We compute the full functional graph exactly
(BigInt-free: every count is an integer reachable by exhaustive enumeration of partitions)
and read off the **settling time**:

- **`maxTail(n)`** — the **worst-case** number of moves before any arrangement of `n` first
  becomes periodic (first reaches its cycle). At triangular `n` this is `k² − k` (the proven
  bound, reproduced); off-triangular it is uncharted.
- **`totalSettle(n) = S(n)`** — the **total** settling work: the sum, over all `p(n)`
  arrangements, of each one's transient length. *(= mean settling time × p(n).)*
- **`maxTailCount(n)`** — how many arrangements are tied for slowest.

### Honest status of each, against OEIS (session reported this 2026-06-26 with multiple windows + name search; no search log is committed, so the human depositor re-runs and logs it at deposit time)

| sequence | first terms (n=1…) | OEIS | note |
|---|---|---|---|
| recurrent | 1,2,1,3,3,1,4,6,4,1,… | **A135278/A007318** | Pascal — Etienne 1991 |
| fixed | 1,0,1,0,0,1,0,… | support of **A010054** | triangular indicator — Brandt |
| numCycles | 1,1,1,1,1,1,1,2,1,… | **A037306** | cycle bijection |
| goe | 0,0,1,1,2,3,5,7,… | **A123975** | Garden of Eden |
| longest | 1,2,1,3,3,1,4,4,4,… | **A183110** | period of orbit of [1ⁿ] |
| **totalSettle S(n)** | 0,0,3,3,8,33,26,41,86,267,… | **absent** | **new — staged** |
| **maxTail(n)** | 0,0,2,2,3,6,4,5,7,12,8,… | absent, but **derivable** | see relation below |
| **maxTailCount(n)** | 1,2,1,1,1,1,1,1,1,3,… | absent | companion |

### The one thing we will not over-claim: maxTail is *derivable*

`maxTail` is absent from OEIS, but it is **not independent**. OEIS **A188160** ("max steps
until a partition repeats") equals `max_s(tail(s) + period(s)) − 1` — it bundles **one full
cycle** into the count. We verified (n ≤ 61):

```
maxTail(n) = A188160(n) − A183110(n) + 1
```

So `maxTail` follows from two catalogued sequences and we do **not** stage it as a new
sequence. But the relation is *not* a triviality: cycle lengths within a single `n` genuinely
differ (n=8 → {2,4}; n=17 → {3,6,6}; n=32 → {2,4,8,…}), so the identity asserts a real
structural fact — **the worst-case transient always flows into a *longest* cycle.** `verify.mjs`
checks this executably for n ≤ 61 (with the OEIS A188160 b-file to n=61 embedded in the check);
it is offered as a conjecture, not a theorem.

`totalSettle` (S) is a *global* statistic with no such reduction to catalogued sequences, and
is the genuinely new sequence we stage (`/oversight/oeis/bulgarian-solitaire-settling/`).

## Reproduce

```sh
node research/bulgarian-solitaire/verify.mjs      # 12/12 — anchors + S to n=55 vs staged b-file + relation to n=61 (~2.5 min)
python3 research/bulgarian-solitaire/s_explore.py 55 1  # independent engine reproduces all 55 S(n) terms
node research/bulgarian-solitaire/generate.mjs 55 # regenerates data.json + b-files (n≤55)
```

`verify.mjs` reproduces five catalogued sequences exactly (n≤40, the calibration range) and the
Igusa/Etienne `k²−k` bound; computes `S(n)` to n=55 two ways on one functional graph (reverse-BFS
distance-to-cycle vs forward memoised iteration) and holds every term to the staged deposit
`b-file.txt`; and checks the A188160 relation to n=61. The two `S(n)` methods share the partition
enumeration, the move, and the cycle detection, differing only in the distance computation, so
they catch distance bugs but not a shared graph bug; the independent guard against that is
`s_explore.py` (separate language, own partitioner/move/cycle-detection/forward-memo tails), which
reproduces all 55 terms. The engine is calibrated *before* any new number is trusted.

## Files
- `engine.mjs` — the map, the functional-graph analysis, two transient methods.
- `generate.mjs` — full dataset (`data.json`) + b-files to n=55.
- `verify.mjs` — 12 assertions (anchors n≤40, theorem, S(n) to n=55 vs staged b-file, relation to n=61).
- `b-total-settle.txt`, `b-max-tail.txt`, `b-max-tail-count.txt` — b-files.

## Open
- **Prove** `maxTail = A188160 − longest + 1` (worst transient → longest cycle) for all n.
- Asymptotics of `S(n)/p(n)` (mean settling time): does it grow like √n · const?
- Exact `maxTail` past n=55 (cheap — p(n) enumeration only).

## The generalization: s-Bulgarian solitaire (take s cards; 2026-07-19)

Take `s` cards from every pile instead of one (well-behaved sigma-Bulgarian, `sigma(h)=min(h,s)`;
Hopkins's operation `H_s`; `s=1` is the game above). New files:
- `engine-s.mjs` — the `H_s` map + functional-graph analysis for any `s` (reverse-BFS tails).
- `s_explore.py`: an independent Python engine (own partitioner, own move, own cycle detection,
  `lru_cache` forward tails). Two modes: `python3 s_explore.py [N] [s ...]` prints tables, and
  `python3 s_explore.py --check [N=40]` **asserts** against the staged b-files of
  `oversight/oeis/generalized-bulgarian-solitaire/` and exits nonzero on any mismatch.
- `laws.py` — probes the emergent laws.
- `generate-s.mjs`: `data-s.json` (s=1..5) + staged b-files. A producer, not a check.
- `verify-s.mjs`: **15/15**, ~8s, move checked three ways; s=1 anchors to six catalogued facts;
  Hopkins's recurrent closed form reproduced for s=1..5 at n<=40; the laws below. **It opens no
  b-file**, so a green run here says nothing about the staged deposit.
- `oversight/oeis/generalized-bulgarian-solitaire/verify-staged.mjs`: **17/17**, 30-45s, the gate
  that binds the staged artifact. Reads all ten b-files and reproduces every one of their 550
  terms, with a per-file coverage table naming what each term rests on. Run it too.

What is **already proven** (Hopkins, INTEGERS 24A 2024 #A9), reproduced here: recurrent count =
generalized binomial coefficient (trinomial A027907 for s=2; central trinomial A002426 at square
n), plus closed forms for loops and Garden of Eden. What is **new / open**: the *settling time*.
- **The k² law (conjecture):** `maxTail(s·T_k) = k²` for `s≥2`, `k²−k` for `s=1`. A `+k` jump at
  the first step, generalizing Igusa's bound. The whole space converges to the single steeper
  staircase `(sk, …, s)` at `n=s·T_k` (generalized Brandt). Checked over exactly `s=1..7`,
  `k=1..7`, `n=s·T_k ≤ 56` (`verify-s.mjs` section 3), which is 33 `(s,k)` cases, not a proof.
  For `s≥2` the largest `k` reached is `k=7`, and only at `s=2`.
- **Ten sequences staged** (settling, GoE, loops, recurrent for s=2,3), `n=1..55`, in
  `oversight/oeis/generalized-bulgarian-solitaire/`. Reported absent from OEIS by the computing
  session on 2026-07-19, but **no query log is committed**, so that is what a session reported
  and not a checkable fact; the human depositor re-runs and logs the search at deposit time.
- **The Python cross-check is now a check.** Until 2026-07-27, `s_explore.py` printed a table and
  nothing compared it to anything, so the "never one path" claim depended on a human diffing two
  screens by eye, and no committed script ever ran it. `s_explore.py --check` now reads the
  staged b-files itself and `verify-staged.mjs` invokes it, so it is a real path (n≤40) or it
  says out loud that it was skipped.

Live showing: `/strata/the-longer-way-home/` (verifier `verify-the-longer-way-home.mjs`).

### Open next
- **Prove** the k² law (the worst hand at `n=s·T_k` and why the s=1→2 step adds exactly k).
- Extend the settling b-files past n=55; check whether `s≥3` shares the `s=2` recurrent-at-square
  pattern under the right indexing.
- A `p(n−3T_j)`-style closed form for `ge_s(n)`, `s≥2` — flagged open by Hopkins himself.
