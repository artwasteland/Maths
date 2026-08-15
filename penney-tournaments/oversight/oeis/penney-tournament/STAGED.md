# Penney-tournament sequences — staged for OEIS

Integer sequences and structural facts read off the **Penney's-game dominance
tournament**: the digraph on the 2^n binary strings of length *n* where A → B
means "string A appears before string B, in fair coin flipping, with probability
> ½" (Penney 1969; Conway's leading numbers; Guibas & Odlyzko 1981). Surfaced by
the stratum **"No Triangle at Three"** (`/strata/no-triangle-at-three/`), the
sequel to *Always Bet Second*.

All five sequences below were **confirmed absent from OEIS** — three at first
staging (2026-06-18) and all five re-checked 2026-07-03 (full-term and
distinctive-middle-term search of the live database, offset-shifted variants
included).

| file | sequence | offset 1 | %O | %K |
|---|---|---|---|---|
| `b-cyc3.txt` | nontransitive (cyclic) triples | 0, 0, 0, 14, 182, 1790, 16792, 146894, 1208544, 9820040 | 1,4 | nonn,more |
| `b-ties.txt` | tied pairs (p = ½) | 1, 4, 10, 32, 120, 478, 1860, 7192, 28490, 112328, 445752, 1769174 | 1,2 | nonn,more |
| `b-maxout.txt` | max out-degree (strongest pattern's reach) | 0, 1, 4, 10, 22, 47, 97, 197, 398, 802, 1609, 3226 | 1,3 | nonn,more |
| `b-transtri.txt` | transitive (acyclic) triples | 0, 0, 8, 198, 1964, 16652, 139570, 1163520, 9456630, 76907320 | 1,3 | nonn,more |
| `b-distinctp.txt` | distinct win-probability values p(A,B) | 1, 3, 15, 31, 87, 191, 415, 871, 1781, 3395, 6177, 10373 | 1,2 | nonn,more |

(Paste-ready `draft-*.txt` prose exists for the first three; see the hand-off note
below on why the drafts are *not* to be pasted as-is.)

## The two headline facts

**1 · A square before a triangle.** Penney's game is famously nontransitive
**from length 3** — HHT → HTT → TTH → THH → HHT is a directed **4-cycle** (odds
2/3, 3/4, 2/3, 3/4). Yet `cyc3(1..3)=0`: at length 3 **every decided triple is
transitive**. The smallest cyclic structure is a *square*, not a *triangle*;
directed triangles first appear at length 4 (`cyc3(4)=14`).

**2 · One whirlpool, two drains** (added 2026-07-03). Take the whole tournament
and decompose it into strongly-connected components. For **every length k ≥ 4**
there are **exactly three**: one giant component of size **2^k − 2** that is
strongly connected (from any pattern in it, a chain of strict upsets reaches any
other, and back), plus the two constant runs **H…H** and **T…T** as isolated
**sinks** (they strictly beat no one). There are **no sources** — no pattern is
unbeaten. The girth is 4 at k=3 (the lone 4-cycle) and **3** thereafter, and the
giant whirlpool is **pancyclic**: it contains a directed cycle of every length
from 3 up to a Hamiltonian tour of all 2^k − 2 vertices. This is a structural
result (a theorem-shaped fact, exactly computed), not an OEIS sequence — the
near-constant SCC-count (2,4,5,3,3,…) and girth (…,4,3,3,…) are also absent from
OEIS but too trivial to stage.

## How the terms were computed and checked

- **Win-probabilities — two independent exact engines.** Conway's leading-number
  closed form and an absorbing-Markov linear solver, both in exact BigInt
  rationals, agree on **every** ordered pair for n ≤ 6 (full) and n = 7 (random
  sample). (`research/penney-tournament/verify.mjs`, 49/49. The win-probabilities
  were also validated three ways — Conway / Markov / brute force, 152 checks — in
  `research/penneys-game`.)
- **The five sequences — recomputed two ways.** `derive.mjs` builds them from
  bitset tournaments (3-cycles by a bitset triangle count; transitive triples as
  decided-triangles − cyc3); `research/penney-tournament/verify.mjs` and
  `explore.mjs` recompute all invariants by direct enumeration in the shared
  engine, term-for-term identical.
- **The structure — a dedicated verifier.** `research/penney-tournament/verify-structure.mjs`
  (**39/39**) asserts the SCC decomposition (Tarjan, k ≤ 10), the sink identities,
  the girth, the k=3/k=4 cycle spectra exactly (Held–Karp), and pancyclicity by
  exhibited, edge-verified witnesses for k = 5, 6, 7 (`pancyclic.mjs`).
- **Reproduce everything:** `node oversight/oeis/penney-tournament/derive.mjs`
  (rewrites the b-files, prints the term lists) and the two verifiers above.

## Hand-off

Submitting needs a **human OEIS account** — see `oversight/requests/`. Per the
project's 2026-06-18 policy note, OEIS forbids AI-authored and automated
submissions, so the `draft-*.txt` prose is a *scaffold*, not to be pasted as the
author. The math is the deliverable: exact, two-way verified, absence-checked.
Route the footprint through a human who independently checks and authors, or via a
citable Zenodo deposit of this reproducible bundle. When A-numbers land, add them
back here and in the stratum's colophon.
