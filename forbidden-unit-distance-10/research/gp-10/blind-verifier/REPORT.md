# A second verifier for the GP-10 refutations, written blind

Built 2026-09-25 by a Claude agent (the official checker, `check/gp10check.py`, and its kernel were built by codex, so
the two verifiers come from different model families). The agent worked in a directory holding only the written
specification (GP-10 CONTRACT, FORMAT and PROOFS; the u(22) CONTRACT and gadget proofs; AMP's paper) and the data (the
324 L10 records, the forbidden-74 list, the TU gadgets). It was told not to open, list or run any checker, kernel or
producer code; a scan of everything it wrote finds no reference to one. The agent could not write this file itself, so
the supervisor wrote it from the agent's final report, and checked every claim below against the artifacts.

## Result

| type | ACCEPT | REJECT | UNSUPPORTED |
|---|---:|---:|---:|
| tu | 13 | 0 | 0 |
| null | 22 | 0 | 0 |
| null-dag | 65 | 0 | 0 |
| real (17 Sturm, 7 SOS) | 24 | 0 | 0 |
| real-dag (86 Sturm, 11 SOS) | 97 | 0 | 0 |
| tree | 103 | 0 | 0 |
| **total** | **324** | **0** | **0** |

All 342 proof-tree nodes, 2,007 derivation rows and 14 TU steps were checked (each count matches an independent count
of the file). 3 min 51 s, peak 145 MB. `verify_refutations.py` sha256 `3af7b336fc5ae730...`, `verdicts.jsonl`
`e9daec41172f644d...` (runs/independent-checks-2026-09-25/blind/).

## Checked by the supervisor afterwards

- Re-ran the verifier over all 324 records: identical verdicts, 324 ACCEPT (1 min 47 s, 143 MB;
  `verdicts-rerun-by-supervisor.jsonl`).
- Five mutations of the supervisor's own design, which the agent never saw: a proof-tree matrix entry changed, a
  Nullstellensatz cofactor coefficient changed, a derivation's last row dropped, a TU gadget index shifted, and a valid
  certificate transplanted onto a different L10 graph. All five REJECTED (`supervisor-mutations-verdicts.jsonl`). An
  unmutated TU record run alone was also REJECTED, correctly: its chain ends at another L10 member whose record was not
  in that run; with the target added, both ACCEPT.
- **The premise it trusts, closed.** The TU certificates may end at a Globus-Parshall graph (12 of the 13 do,
  directly or through another member), and the verifier treats the 74 as non-unit-distance. The GP-10 controls re-derived
  all 74 from an empty list (runs B4p-F3 to B9p-F8); the blind verifier ACCEPTS all 74 of those certificates (tree 33,
  tu 34, real 6, null-dag 1; `gp74-verdicts.jsonl`), and every TU certificate among them cites only a strictly smaller
  forbidden graph, so the induction on the number of vertices is not circular.

## What was implemented (from the agent's report, condensed)

All arithmetic exact; strict JSON with exact key sets; its own graph6 decoder.

- **Trusted data re-checked.** The forbidden-74 composition matches the contract; the TU property of all six gadgets
  is re-proved mechanically (the pair's displacement equals plus or minus an edge displacement modulo the rhombus
  relations of the gadget's 4-cycles).
- **tu.** A nonempty chain; each step an injective edge-preserving map into the graph augmented so far, the pair the
  image of the gadget's distinguished pair and a current non-edge; the end a forbidden-74 member (JSON labels) or a g6
  whose record in the same run is accepted; pointers resolved after all records, with cycle detection.
- **null, real, null-dag, real-dag.** The system is regenerated from the g6 alone: the frame must be an edge with
  p(a) = (0,0) and p(b) = (1,0); variables x_i, y_i for the other vertices in increasing order, then t_k in `sat` order;
  generators `e:u,v` = d2 - 1 (frame edge excluded) and `s:u,v` = t_k d2 - 1, sat pairs u < v without duplicates.
  Cofactor sums are expanded in FLINT's fmpq_mpoly and must equal 1 or f. The derivation types follow amendment 5 (at
  most 256 rows, `aux:j` only for j < k, canonical term order, each row's identity checked before use). Sturm: the
  variable exists, f is nonzero and univariate in it, its own Sturm count is 0 (and sympy's `count_roots` agrees). SOS:
  c > 0, every w_i > 0, and c + sum w_i q_i^2 = f.
- **tree.** At each node it tracks its own graph and its own proved constraint space over K(i), K = Q(theta) with theta
  the isolated real root of the witness's minimal polynomial: the root space is the rhombus rows of all 4-cycles; an
  L2 child adds the 4-cycle rows of the augmented graph; an L3 child adds its branch row. Moves: L1a (collision forced),
  L1b (both pairs edges, |omega|^2 != 1), L2 (second pair a non-edge, |omega|^2 = 1, one child), L3 (nonzero
  coefficients, d^2 equal to the discriminant, two children carrying (s +- i d) a x + 2|a|^2 b y), L1c (discriminant
  strictly negative at theta, by exact interval bisection). Each node's A must have exactly the row space of its own
  regeneration and the graph state must equal the one it derives, so a misreading of the format can only cause a false
  REJECT.

## Red controls (the agent's)

207 of 207 negative controls REJECTED (tu 22, null 27, null-dag 39, real 26, real-dag 49, tree 41, gadget data 3),
every mutation asserted to change its record; the 18 unmutated sources ACCEPTED in the same run; one positive control
(omega = -1 re-spelled as a complex number) ACCEPTED. Seven attack certificates (self-consistent certificates for false
claims about graphs that are unit-distance graphs, each with exactly one check between it and an ACCEPT) were each
stopped at the intended check. `redteam.json`, `redteam.py`, `redteam_attacks.py`.

## Ambiguities and doubts it recorded

1. The tree witness format is defined in the kernel's docstring, which the agent was not allowed to read; it was
   reconstructed from the data and AMP Section 4, strictly (above). Only two fields occur: Q (85 trees) and Q(sqrt 3)
   (18 trees).
2. The polynomial branch trusts FLINT's fmpq_mpoly arithmetic, spot-checked by re-expanding 11 identities in sympy.
3. Readings chosen: GP-10 rationals must be strings, tree rationals may be integers or strings; the forbidden-74
   vertex count is max label + 1, with contiguity checked; graph6 canonicity is not checked (pointers match by exact
   string); R-ptr (`sub`) is not implemented, since no L10 record uses one.

Also noted: 12 of the 13 L10 TU chains are a single application of gadget 0, one uses gadgets 0 then 5; F9[17] is one
of the five forbidden-74 graphs that embed over C but not over R; 35 frames have a > b (legitimate, the frame is
ordered).
