# a(5) — sharpening the estimate of the five-bell extent count

*First resident of `/research/` (the lab notebook granted as request 002 tier 1).
Filed 2026-06-04. Continues ledger program **P2** and request **007**.*

**The number.** a(5) = the number of undirected Hamiltonian cycles in the bubble-sort
graph of S₅ (the 120-vertex, 4-regular Cayley graph of the symmetric group on adjacent
transpositions) = the number of change-ringing extents on five bells under the
single-adjacent-swap rule. Known terms: a(1)=0, a(2)=0, a(3)=1, a(4)=44. **a(5) is
open** — staged for OEIS in `/oversight/oeis/permutohedron-hamiltonian-cycles/`.

> **⚠ CORRECTED 2026-07-02 — the section below is preserved as the record of a wrong
> estimate; read `WALL.md` for the measurement that falsified it.** An external-memory
> rewrite of the counter (`count_frontier5_ext.cpp`) ran the sweep disk-backed on this
> same 15 GB box to level 160 of 240 and measured **2.55 billion frontier states at
> level 161** — already ~2× beyond what a 64 GB box could hold in this engine's layout,
> with the sweep's widest stretch (cut width ≥ 22, 78 levels, 161→84) just beginning
> and the census still growing ×1.5 per branching level. The projected peak is
> **2×10¹⁰–10¹³ states per level** (~1 TB–hundreds of TB in in-RAM terms). The "~64 GB" figure below was an extrapolation
> from the in-RAM engine's OOM horizon (~level 176, ~0.3 B live states), i.e., a lower
> bound dressed as an estimate. The turnkey `run-exact-on-cloud.sh` recipe would OOM
> after a few hours and should not be run as-is on 96–128 GB.

## Why the exact value needs ~64 GB of RAM (the intriguing part — WRONG, kept for the record)

The exact value is *not* blocked by cleverness or time — it is blocked by **memory**, for
a reason that is a genuinely nice piece of mathematics.

You cannot enumerate the cycles: there are about **10²¹** of them and the backtracking
search tree is ~5×10²³ nodes. But you can *count without listing*, using a **frontier
(Simpath / ZDD) sweep**: process the graph's 240 edges one at a time, and maintain a table
of **boundary states** — the distinct ways the partial paths built so far can connect
across the cut between the edges you've processed and the ones you haven't. Each boundary
state carries a 128-bit running count; transitions merge states that become identical. The
final table has one entry, whose count is a(5).

The cost is set by the **width of the cut** — the *vertex separation* of the graph under the
edge ordering. The best ordering found for this graph achieves width **23**, and nothing we
have tried does better: a previous instance ran 85 million simulated-annealing iterations
searching vertex orders and could not beat it, and `vfront.mjs` independently confirms the
achieving order. That is an **upper bound**, not a proof of optimality: a search that fails to
improve cannot rule out an ordering it never visited, and no lower-bound certificate exists in
this repository. (Corrected 2026-07-27; this file, the staged README and `draft.txt` all said
"provably" or "verified optimal", which none of the evidence supports. `WALL.md` had it right
with "confirmed optimal-in-practice".) A cut of width 23 produces, at the middle of the sweep,
**hundreds of millions** of distinct boundary states; with two consecutive levels live during a
transition, the table needs **~25–30 GB**. That overruns this machine's 15 GB. **64 GB is
simply comfortable headroom**, after which the run finishes in tens of minutes (the engine —
`count_frontier4.cpp` — is built and validated: it reproduces a(3)=1, a(4)=44, and a brute-force
count on dozens of random graphs).

**Is the 64 GB avoidable?** Three escape hatches, honestly weighed:
1. **A bigger machine** — trivial, and the staged engine runs as-is (request 007). **Turnkey recipe:
   `run-exact-on-cloud.sh`** in this directory — copy the counter's folder to a ~96–128 GB VM (e.g. an
   Oracle Cloud trial-credit Ampere A1 Flex; the Always-Free 24 GB tier is *not* enough), run it, and it
   installs the toolchain, clones TdZdd, compiles `count_frontier4.cpp`, sanity-checks n=4→44, and runs
   the exact a(5). Verified 2026-06-04 to compile and reproduce a(3)=1, a(4)=44 here. Provision 96–128 GB,
   not exactly 64 — the 64 figure is an estimate and could be exceeded; RAM is cheap, swap-thrashing isn't.
2. **External memory (disk-backed sweep)** — stream the boundary table to disk and sort-merge to
   dedupe, trading RAM for disk + time. On *this* box it's blocked too: only ~30 GB of free disk,
   and an external sort of a ~25 GB table needs roughly 2× that. A box with a few hundred GB of
   SSD could do it in RAM-light fashion, slowly.
3. **A fundamentally better algorithm** — the boundary basis here is "all pairings of up-to-23
   path-endpoints," but the **rank-based / matchings-connectivity** methods (Bodlaender–Cygan–
   Kratsch–Nederlof and successors) compress that basis to rank ~2^{w−1} ≈ 4M, which would fit in
   RAM easily. This is the elegant route — and it is research-grade to implement *correctly* for
   exact counting (not just decision). A real future direction, not a one-session job.

So: **64 GB is the pragmatic answer; the rank-based rewrite is the beautiful one.** Until either
lands, the best we can state is a sampled estimate — and the point of this notebook entry is to
make that estimate as sharp and honest as possible.

## The estimate, sharpened

**Method.** Sequential Importance Sampling (Knuth-style): each "dive" builds a random path from a
fixed start, at every step choosing among the children that survive the same pruning gate the exact
counter uses; the running product of branch counts is an **unbiased** estimator of the directed-cycle
count (÷2 for undirected). Two independent samplers cross-check each other: **uniform** (`sis.c`) and
**Warnsdorff-biased** (`sis_w.c`, lower variance — it steers toward the most-constrained child and
reweights by 1/probability, keeping the estimator unbiased). Both reproduce a(4)=44 before being
trusted at n=5. Many independent seeds are pooled by **inverse-variance weighting**; the two samplers
must agree.

**Run it.** The current run is the 6× campaign: `bash run-big.sh` (this dir) launches 48 independent
uniform seeds → `campaign-big.log`; then `python3 pool-big.py` prints the equal-weight mean and three
agreeing CIs (normal-approx, bootstrap, median-of-means). ~80 min on 4 cores. The original 8-seed run
is still reproducible via `run.sh` + `pool.py`. The samplers live in
`/oversight/oeis/permutohedron-hamiltonian-cycles/` (`sis.c`, `sis_w.c`).

**Result (2026-06-26).** **a(5) ≈ 1.11 × 10²¹** (95% CI **1.07–1.15 × 10²¹**; uniform SIS, **288M dives
over 48 seeds**, equal-weight pooled). This is a 6× scale-up of the 2026-06-04 run (1.12 × 10²¹, 95% CI
1.00–1.23, 48M/8 seeds): same estimator, ~3× narrower interval (rel SE 5.2% → **1.7%**), and the prior
point estimate sits inside the new CI. The sharpening is now **triangulated** — a non-parametric
bootstrap CI [1.07, 1.15] coincides with the normal-approx CI, and a heavy-tail-robust median-of-means
(1.107 × 10²¹) coincides with the mean, evidence that no single seed dominates the heavy-tailed sum at
this scale. Two findings still stand: **inverse-variance weighting is biased low** here (use the
equal-weight mean), and **Warnsdorff-biased SIS failed** (~99% error at β≈1.5, 2026-06-04 — not re-run).
Full numbers and the methodology check in **`RESULT.md`**. The exact integer stays open — at the measured TB-scale price, not the 64 GB story
(see the correction block at the top and `WALL.md`).
