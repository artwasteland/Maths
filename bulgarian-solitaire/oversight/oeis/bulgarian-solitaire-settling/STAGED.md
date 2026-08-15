# Bulgarian solitaire — total settling time S(n) (staged for a DOI; OEIS via a human)

**New sequence (reported absent from OEIS by the computing session on 2026-06-26; the human
depositor re-runs the absence search at actual deposit time, see "Absence" below):**
`S(n)` = the **total settling time** = the sum, over all `p(n)` partitions of `n`, of the
number of Bulgarian-solitaire moves that arrangement needs to **first become periodic**.

```
S(n), n=1..55:
0, 0, 3, 3, 8, 33, 26, 41, 86, 267, 206, 242, 374, 831, 2133, 1629, 1517, 1919,
3353, 7209, 15973, 12744, 11000, 11597, 16506, 30317, 59275, 113710, 95497, 80965,
75363, 89663, 142164, 256749, 450157, 776353, 682835, 600700, 539057, 562086,
748806, 1214030, 2016947, 3248606, 5168531, 4701878, 4273283, 3762614, 3627949,
4205858, 6032340, 9676856, 14968242, 22571828, 33802475
```

`S(n) = p(n) · (mean settling time)`. It is a global statistic with no reduction to any
catalogued sequence.

**The honesty anchor.** The same engine reproduces five catalogued sequences of this exact
process (recurrent = Pascal/Etienne A135278; cycles A037306; Garden of Eden A123975; longest
cycle A183110; unique fixed point at triangular n — Brandt) **and** the proven Igusa/Etienne
tight bound `maxTail(T_k) = k² − k`. So the engine is trusted *before* `S(n)` is claimed new.
See `research/bulgarian-solitaire/verify.mjs` (12/12): the anchors and the `k²−k` theorem are
checked to n=40 (calibration range), `S(n)` itself is checked to n=55 against this deposit's
`b-file.txt` term by term, and the A188160 relation below to n=61.

**Not claimed new:** the worst-case settling time `maxTail(n)` is absent from OEIS but
**derivable**. `verify.mjs` checks, executably, for n ≤ 61 that `maxTail = A188160 − A183110 + 1`
(the A188160 b-file to n=61 is embedded in the check). We stage only `S(n)`; `maxTail` is
documented as a derived quantity plus a verified structural relation (worst-case transient flows
into a longest cycle), offered as a conjecture, not a theorem.

**How `S(n)` is verified (precisely).** `verify.mjs` computes each `S(n)` for n=1..55 two ways
on one functional graph: reverse-BFS distance-to-cycle and forward memoised iteration. These
two methods share the partition enumeration, the move, and the cycle detection; they differ
only in the distance computation, so they catch distance bugs but not a shared graph bug. The
independent guard against a shared bug is `research/bulgarian-solitaire/s_explore.py`: a
separate-language engine with its own partitioner, move, cycle detection, and forward-memo
tails, which reproduces all 55 staged `S(n)` terms (`python3 research/bulgarian-solitaire/s_explore.py 55 1`;
confirmed 2026-07-20). `verify.mjs` also reads this deposit's `b-file.txt` and holds every term
to the recomputed value.

**Absence.** The 2026-06-26 "absent from OEIS" claim is a report from the computing session; no
search transcript is bundled in this repo. The human depositor re-runs the absence search
(multiple windows + name search) at actual deposit time and commits the query log; do not treat
the 2026-06-26 date as a live check.

**Reproduce / why no paste-ready OEIS draft.** `node derive.mjs 55` rewrites `b-file.txt`.
Per the project's 2026-06-18 steer, OEIS forbids AI-authored/automated submissions, so there
is **no paste-ready `draft.txt`** here: the *math* is exact and verified as above, but the
*authoring* must be done by a human who has independently checked it. The path is **Zenodo for
a DOI** (`.zenodo.json`, depositor: the human) and an **offer to a mathematician** to author
the OEIS entry as themselves. Request 005 covers the human hand-off.
