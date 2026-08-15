# Verification notes: bulgarian-solitaire-settling

Honesty pass, 2026-07-20. What the words in `README.md` and `.zenodo.json` are backed by, precisely.

## What is checked, and over what range

`research/bulgarian-solitaire/verify.mjs` (12/12, ~2.5 min on plain `node verify.mjs`):

- Five catalogued anchors (recurrent = A135278, fixed = triangular indicator, goe = A123975,
  numCycles = A037306, longest = A183110) and the Igusa/Etienne `k^2 - k` bound: checked to
  **n=40** (the calibration range; the anchor literals reach that far).
- `maxTail(n)` reverse-BFS vs forward iteration: **n=40**.
- **`S(n)`, the one staged sequence: n=1..55**, computed two ways on one functional graph
  (reverse-BFS distance-to-cycle vs forward memoised iteration) AND read back against this
  deposit's `b-file.txt` term by term. The verifier now reads the staged `b-file.txt`; before
  this pass no script did, and the two-way check stopped at n=40, leaving the top 15 staged
  terms (n=41..55, up to 33802475) checked by a single path only.
- **A188160 relation `maxTail = A188160 - A183110 + 1`: n=1..61**, with the OEIS A188160
  b-file to n=61 embedded in the check. Before this pass the check ran only to n=40 and a
  comment misstated that bound as 44; the "n<=61 in the notes" was not backed anywhere.

## The "two ways" claim, stated exactly

The two `S(n)` methods in `verify.mjs` share the partition enumeration, the move, and the
cycle detection (one graph is built; both methods walk it). They differ only in how
distance-to-cycle is computed. So they catch distance-computation bugs, not a shared graph bug.

The independent guard against a shared graph bug is `research/bulgarian-solitaire/s_explore.py`:
a separate-language engine with its own partitioner, move, cycle detection, and forward-memo
tails. On 2026-07-20 it reproduced all 55 staged `S(n)` terms
(`python3 research/bulgarian-solitaire/s_explore.py 55 1`, ~120 s). It is committed code; anyone
can re-run it. `engine-s.mjs` at s=1 also computes the same numbers but uses the same
reverse-BFS algorithm as `engine.mjs`, so it is a different-authorship, same-algorithm path, not
an independent-algorithm one.

## Absence from OEIS

The "absent from OEIS, 2026-06-26" statement is a report from the computing session. No search
transcript, query log, or OEIS snapshot is committed in this repo, and the date is stale
relative to this pass. The human depositor must re-run the absence search (multiple windows +
name search) at actual deposit time and commit the query log. Do not treat 2026-06-26 as a live
check.

## Runs on 2026-07-20 (this pass)

- `node verify.mjs` -> `Bulgarian solitaire verifier: 12/12 passed.` (exit 0, ~150 s plain node)
- `python3 s_explore.py` cross-check: agrees with staged b-file on all 55 S(n) terms.
- A188160 relation independently recomputed and confirmed for n=41..55 and n=56..61 (both hold),
  matching the OEIS A188160 b-file.
- `derive.mjs` was NOT run (it rewrites `b-file.txt`); its default NMAX is 55, matching the
  committed b-file, so this directory has no truncation trap. The depositor should run
  `derive.mjs` and `verify.mjs` themselves to confirm before deposit.
