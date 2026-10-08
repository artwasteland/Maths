# Estimates for what comes next: u(24) and the 11-vertex classification (2026-09-29)

Boris Alexeev asked for time estimates for u(24) and for the 11-vertex version of Globus-Parshall (his reply is not
quoted here). These are the estimates behind Liam's answer, worked out with codex (`gpt-6-astra`, the collaborative
dialogue, scratchpad `dialogue-6-out.txt`) from this repository's measured runs. Estimates, not measurements, except
where marked measured.

## u(24)

- **The one case.** AMP's Table 1 gives 68 <= u(24) <= 72. With u(23) = 64, Schade's lemma gives u(24) <= 69: a
  (24,70) graph would have an induced 23-vertex subgraph with ceil(70 x 22/24) = 65 > 64 edges. So u(24) is 68 or 69,
  and deciding it means excluding (24,69), whose minimum degree is exactly 5 (69 - 64 = 5, and 2 x 69/24 < 6): the
  same shape as (23,65).
- **Measured costs so far** (run-dag2.py wall time summed over 1,920 slices; four-core cloud machines):
  - (21,57), root degree 3: 19 h;
  - (22,61), root degree 5: 54 h;
  - (23,65), root degree 5: 407 h.

  From (22,61) to (23,65) the time grew 7.5x and the tree about 12x.
- **Why the naive extrapolation (x 7.5 to x 12, so 3,000 to 5,000 h) is too high** (codex): the reach tables of
  (24,69) and (23,65) agree through level 15, (18,41) is unchanged, and the new routes enter at (17,40), (18,42),
  (19,45) and (20,49). About 317 of the 362 phase-accounted worker-hours of (23,65) lie in cells that do not change.
  So T(24) is about 317 + 45 r hours, r the growth of the affected part: 500 h at r = 3, 800 at 10, 1,700 at 30.
- **Working estimate: 500 to 2,000 four-core machine-hours for the search**, 3,000 to 5,000 as a bad-case
  contingency, and about 2.5 to 3 times the search for re-running, checking and the G4 replay. That is one to five
  days on 48 machines.
- **The pilot that would measure it:** level 12, count 1,920. It takes 32 random slices (a published seed) plus ten
  predetermined heavy ones: 50, 344, 1082, 1209, 1474, 1535, 1639, 1651, 1721 and 1814. s344 holds 35.5% of the
  (18,42) parents the new routes use. The estimator takes the ten exactly and expands the random 32 by 1910/32.
  Needed first: the driver's and checker's tables extended to 24, prune.py's bounds, and the runbook passing both
  u-bar values.

## The 11-vertex classification (GP-11)

- **Candidates, measured:** 448,708 biconnected 11-vertex graphs contain none of the 398 minimal forbidden graphs as a
  subgraph (13.53 times GP-10's 33,162). Counted by codex (read-only) and again here, identically, in about five
  minutes:

      nauty-geng -Ckq 11 11:24 | research/unit-distance-22/filter/udfilter -s 398 \
          -f research/unit-distance-22/data/forbidden-398.json -t research/unit-distance-22/data/tu-gadgets.json

  Of 68,232,100 biconnected K4-free inputs, 67,783,392 contain a member of the 398; of the 448,708 left, 294,516
  pass every rule and 154,192 carry a TU witness. The edge cap 24 is rigorous: every 10-vertex deletion is a
  unit-distance graph, so 9m <= 11 x u(10) = 220. The same pipeline at 10 vertices gives 32,653, GP-10's certified
  count of unit-distance graphs.
- **The uncertainty is the hard residue.** GP-10's 33,162 decisions were 4,203 direct certificates and 28,959
  propagated ones; its hard finish took 35 analyst sessions. Reductions that may shrink the residue at 11 vertices
  are forced-edge closure of the TU witnesses, and extending an exact 10-vertex embedding by one vertex (97.6% of the
  candidates have a degree-2 vertex). The GP-10 tools need order-11 extensions (the rigidity front end stops at 10;
  the checker needs a new profile; the lean assembler for memory).
- **Estimate:** a few days for the extensions and the automated pass, then one to four weeks to finish. A pilot runs
  the automated stages over all of B11, then samples 256 unresolved frontier graphs (stratified) and 32 hard
  representatives under escalating budgets.
- **A link between the two:** even a partial set of certified 11-vertex forbidden graphs could prune the u(24) search.

## The standard for u(24), decided with Liam (2026-09-30)

A fresh codex strategist (scratchpad `efficiency-out.txt`), asked to cut the cost without weakening the claim,
recommended running u(24) once. Liam agreed after asking what the normal standard is:
- the field's norms are two independently written programs agreeing on the full count, or certificates checked by
  an independent checker;
- re-running the same program on other machines proves reproducibility, not correctness;
- u(23)'s full re-run existed because the fleet deleted run directories before the reviewed checker saw them.

So for u(24):
- **Check before delete.** Each worker enumerates a slice, runs its G4 replay and the reviewed checker on its own run
  directory, and pushes a receipt bound to the checker's output. Only then does it delete; a failed check or push
  keeps the directory.
- **The savings buy better evidence**, not a second identical run: a wider G4 sample, and about 10% of slices
  (random, plus chosen heavy and restarted ones) reproduced on fresh machines. What is given up is u(23)'s extra claim
  that every slice was reproduced on another machine; the write-up says so.
- **The streaming checker by default**, in a new file with the tables extended to 24. `verify-chain.py` stays
  byte-identical, so every u(23) pin holds.
- **Controls carried forward** where the core is unchanged ((22,61) and (21,57) stand), plus short deployment
  controls. A new positive control: the u(24) reach table admits (22,60) at minimum degree 3, so all 35 known (22,60)
  configurations must survive, and the known (23,64) graphs too.
- **Pilot slices count toward the final run** if the pipeline is frozen at the pilot's version.
- Planning multiplier about 1.4 to 1.6 times the search, not 2.5 to 3.
