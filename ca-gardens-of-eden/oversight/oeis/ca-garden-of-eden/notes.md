# Verification log (dated)

## 2026-07-20: honesty pass on the verification claims

An audit found the trust prose overclaimed: it said all four methods "agree on
every term", but for n above the brute-force horizon only the Node transfer
matrix (the same code that generated the b-files) had ever evaluated the staged
terms. Fixed by closing the gap, not by softening the claim:

- `verify.py` now re-derives every term of every staged b-file (all 8 files,
  n = 1..64) with its independently written Python transfer matrix and compares
  term by term against the committed files. Every staged term is now confirmed
  by two implementations that share no code, in two languages. Python check
  count went from 15 to 23.
- `verify.mjs`: the subset-DFS cross-check now also covers rules 126, 54, 146
  (previously only 30, 110, 184, 22, 90, 45), so all seven featured GoE rules
  get the third method at n <= 13. The b-file block now FAILS when a b-file is
  missing instead of silently skipping. Check count unchanged at 19.
- README.md and .zenodo.json trust sections rewritten to state per-method
  coverage precisely (which n-ranges each method reaches).

Both verifiers run fresh after the edits, on this tree:

- `node research/ca-garden-of-eden/verify.mjs` -> 19/19 checks passed
- `python3 research/ca-garden-of-eden/verify.py` -> 23/23 checks passed

(Exact tails recorded in the honesty-pass session. Runtime: about 80 s for the
Node verifier, dominated by the 2^24 brute-force enumeration; about 3 min for
the Python verifier, dominated by the n <= 18 brute force.)

## 2026-07-20: OEIS absence re-confirmed

Queried the OEIS search API (`https://oeis.org/search?q=<terms>&fmt=json`) with
the literal digit string of terms n = 5..14 of each staged b-file. All 8 heads
returned 0 hits. Positive control: the Fibonacci window `1,1,2,3,5,8,13,21,34,55`
returned 10 hits (A000045 first), so the empty results are genuine absences,
not a broken query.

| file | query window (n = 5..14) | hits |
|---|---|---|
| b-rule30-goe.txt | 6,12,22,33,57,101,166,280,482,813 | 0 |
| b-rule30-image.txt | 26,52,106,223,455,923,1882,3816,7710,15571 | 0 |
| b-rule110-goe.txt | 10,23,49,102,210,442,935,1971,4134,8647 | 0 |
| b-rule184-goe.txt | 10,24,56,124,270,580,1232,2596,5434,11312 | 0 |
| b-rule22-goe.txt | 6,30,50,89,249,466,870,2046,4109,8079 | 0 |
| b-rule126-goe.txt | 20,41,91,190,393,807,1661,3403,6955,14177 | 0 |
| b-rule54-goe.txt | 10,23,49,106,237,512,1089,2303,4849,10145 | 0 |
| b-rule146-goe.txt | 15,30,49,116,237,480,1056,2146,4524,9401 | 0 |

This repeats and logs the 2026-07-19 pre-staging check (multiple contiguous
windows plus keyword search) with a committed, reproducible record.
