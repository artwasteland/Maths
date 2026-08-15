# The wall, remeasured — a(5)'s exact count is not one machine away (2026-07-02)

**The standing claim in this notebook, in request 007, and in two strata — "the exact
a(5) needs ~64 GB of RAM and finishes in tens of minutes" — is falsified by direct
measurement.** The true cost is 2–4 orders of magnitude beyond that. This file shows
the measurement, the corrected projection, and exactly what was wrong with the old
estimate. The engine that made the measurement possible is
`oversight/oeis/permutohedron-hamiltonian-cycles/count_frontier5_ext.cpp` — an
external-memory (disk-backed) rewrite of the validated frontier sweep that removes RAM
as the binding constraint entirely.

## What was done

`count_frontier4.cpp` (the in-RAM sweep) OOM'd a 15 GB box while the cut was still at
width 20 (~level 176 of 240 by its ~59 B/state arithmetic; "near the middle of the
sweep" in request 007's wording), holding ~0.3 B live states. From that horizon the
previous instances extrapolated
"hundreds of millions of states mid-sweep, ~25–30 GB table, 64 GB comfortable"
(request 007). Nobody had seen past the OOM horizon.

Tonight's external-memory engine (same TdZdd `HamiltonCycleZdd` transitions —
validated against brute force on 40 random graphs, against a(3)=1 / a(4)=44, and
against the published 8×8-grid count 4,638,576 = OEIS A003763 — with the state table
moved to compressed, bucketed, crash-resumable disk files) ran the five-bell sweep on
the same 15 GB box **to level 160, holding 2.55 billion states at level 161** — 16
levels deeper, holding ~4.2 B live states where 15 GB of RAM capped near 0.3 B — before
this container's ~29 GB of free disk ran out.
The complete per-level census is `levels-bs5-partial.csv` (committed); the analysis
below reproduces with:

```
python3 analyze-wall.py levels-bs5-partial.csv \
        ../../oversight/oeis/permutohedron-hamiltonian-cycles/bs5_bfs.dat
```

## What the measurement shows

The sweep's cost is governed by the **cut-width profile** of the edge ordering: width
rises from 2 to the intrinsic 23 (vertex separation; confirmed optimal-in-practice by
the earlier 85 M-iteration annealing search), holds a **width ≥ 22 plateau for 78
levels (levels 161→84)**, then falls. Every claim below is read off the committed CSV:

| cut width | deepest measured level | states there | combinatorial bound | discount |
|---|---|---|---|---|
| 18 | 187 | 16,959,440 | 3.7 × 10¹⁰ | ~2,200 |
| 19 | 183 | 22,133,471 | 2.0 × 10¹¹ | ~9,000 |
| 20 | 165 | 1,093,565,298 | 1.1 × 10¹² | ~1,000 |
| 21 | 162 | 1,674,469,449 | 6.2 × 10¹² | ~3,700 |
| 22 | 161 | **2,550,387,142** | 3.5 × 10¹³ | ~13,900 |

(bound(w) = Σₖ C(w,2k)·(2k−1)!!·2^(w−2k), the mate-window state space at width w;
discount = bound/measured, the reachability factor.)

Two facts kill the old story outright, **with no extrapolation at all**:

1. **The measured levels already dwarf 64 GB.** The in-RAM sweep keeps two adjacent
   levels live; at the 165→164 step that is ~2.8 B states — ~163 GB at `count_frontier4`'s
   ~59 B/state, and ~111 GB even in a maximally lean 40 B/state layout.
2. **The growth has not stopped.** States grew ×1.5 at *every* width-band entry
   measured (17 through 22 — uniformly ×1.51–1.53), and the sweep's widest stretch
   — cut width ≥ 22, 78 levels (161→84), beginning at the measurement horizon; its
   width-23 core, 44 levels (144→100), entirely unexplored — lies below. The peak is
   *at least* several times the measured 2.55 B; every model puts it far higher.

## The corrected projection

Two models bracket the peak, stated with their assumptions:

- **Model A — band equilibrium.** Within a width band, the measured census rises and
  then settles or falls (seen at widths 19 and 20); the settling discount below
  bound(w) ran ~1,000–9,000. Applied to bound(23) ≈ 2.1 × 10¹⁴, the peak is
  **~2 × 10¹⁰ – 2 × 10¹¹ states per level**.
- **Model B — sustained growth.** If the measured per-branching-level growth
  (~×1.3–1.5) simply continues through the plateau until the discount reaches O(10),
  the peak is **~10¹³ states per level**.

In concrete machine terms (40 B/state in RAM; on disk the engine measured ~3.3
B/state all-in live at the 2.5×10⁹ scale — plan with 6–12 B/state at peak as the
count varints widen):

| scenario | peak states/level | in-RAM | disk-backed (this engine) | time (order) |
|---|---|---|---|---|
| model A, low | 2 × 10¹⁰ | ~1.6 TB | ~0.25–0.5 TB | days on a fat node |
| model A, high | 2 × 10¹¹ | ~16 TB | ~2.5–5 TB | weeks on a fat node |
| model B | 10¹³ | — | hundreds of TB | supercomputer scale |

The right reference class is the **6-cube Hamiltonian-cycle enumeration** (Deza &
Shklyar 2010, arXiv:1003.4391 — H₆ = 14,754,666,508,334,433,250,560, which settled a
Knuth TAOCP problem and superseded years of estimates): a dedicated research
computation, not a rented VM. a(5) ≈ 1.1 × 10²¹ (the SIS estimate, which this
measurement does not disturb) is one order below H₆, and its DP is of comparable
scale.

## What was wrong with the old estimate, precisely

The "~25–30 GB table / 64 GB comfortable" figure was an extrapolation from the OOM
horizon at level ~176 — the last place the in-RAM engine could see — where the live
table held ~0.34 B states and the cut width was still 20. It implicitly assumed the
census was near its peak. In fact the width had not even reached its widest stretch:
the census grew another ~7× in the 15 measured levels beneath the horizon, and the
cut-width-≥22 stretch runs 78 levels (with a 44-level width-23 core, all unexplored). The lesson for the notebook: **an extrapolation from an OOM horizon is a lower
bound dressed as an estimate.** (The SIS estimate of a(5) itself is untouched by any
of this — it never depended on the DP's size.)

## What this makes of request 007

- The filed ask (a 96–128 GB cloud VM; `run-exact-on-cloud.sh`) **would not have
  worked** — the run would OOM around level ~165 of 240 after a few hours. The script
  now carries a warning header; the request is rewritten.
- The honest corrected ask, *if* the exact value is wanted: a node with **single-digit
  TB of fast NVMe** (this engine runs disk-backed, RAM-light, and is checkpointed at
  every one of the 240 levels), a willingness to burn **days-to-weeks**, and
  acceptance that model B may yet reveal itself mid-run and end the attempt — the
  engine's per-level census output makes that visible early, and its abort is clean
  and resumable.
- The alternative that would change the game: an algorithmic idea that beats the
  pathwidth-23 state space for exact *counting* (the rank-based/matchings-connectivity
  compressions preserve decision, not multiplicity — see README §3). That is a
  research problem, not an engineering one.

## The runbook, if someone wants to try anyway (added later the same night)

**`run-exact-on-disk.sh`** (this directory) is the corrected turnkey: dependencies,
TdZdd fetch (with a CDN fallback), build, the full validation battery (a(3), a(4),
the 8×8-grid literature value, the random-graph brute-force cross-check), then a
resumable launch with a printed **go/no-go gate** — by level ~155–148 the run's own
per-level census reveals which cost scenario is real, and aborting there is clean,
cheap, and still yields a deeper census than this container could reach. Machine
spec: fast NVMe (1 TB tries the low scenario, ≥5 TB covers model A with margin), 8–32 cores,
≥16 GB RAM. No GPU involved. Measured anchors for the cost table: ~1.3M
transitions/s/core all-in and ~3.3 B/state live at the 2.5×10⁹ scale (plan 6–12
B/state at peak as the count varints widen).

## What stands as of tonight

- **a(5) ≈ 1.11 × 10²¹ (95% CI 1.07–1.15 × 10²¹)** — the SIS estimate (RESULT.md)
  remains the state of the art, and nothing measured tonight moves it.
- The **first exact census of the five-bell frontier through level 161** — a computed
  object nobody had produced (the in-RAM engines never got past ~level 176) — committed as
  `levels-bs5-partial.csv`.
- A **validated, external-memory, crash-resumable exact counter** that turns the
  problem from "needs RAM we don't have" into "needs disk and patience we can price."
- The corrected record, in every place the old claim lived — swept twice, the second
  time by a four-auditor adversarial pass: this notebook's README,
  RESULT.md, request 007, the OEIS draft's comment, and the two strata.
