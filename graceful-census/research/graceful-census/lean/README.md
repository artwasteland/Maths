# Graceful labelling, machine-checked — Rosa's parity condition

`Graceful.lean` proves — for **every** `k` and **every** `n`, with no search — the
*necessity* half of two graceful-labelling impossibility results:

- **Windmill (friendship graph) `F_k`** — `k` triangles sharing one hub. A graceful
  labelling forces **`k ≡ 0 or 1 (mod 4)`**, so `F_2`, `F_3`, `F_6`, `F_7`, … are never
  graceful. This is Bermond–Kotzig's necessity — the stratum's "provably cannot be
  graceful" headline.
- **Cycle `C_n`** — a graceful labelling forces **`n ≡ 0 or 3 (mod 4)`** (the classic
  condition; the OEIS cycle census A333720 is 0 exactly at `n ≡ 1, 2 mod 4`).

Both fall to **one** law, `rosa_residue`: in a graph where every vertex has even degree,
the sum of the edge labels is even, but a graceful labelling makes that sum
`1 + 2 + … + m = m(m+1)/2`, so `m(m+1)/2` must be even — i.e. `m ≡ 0 or 3 (mod 4)`. This
is Rosa's parity condition (A. Rosa, 1967). The windmill has `m = 3k` edges, and
`3k ≡ 0,3 (mod 4) ⇔ k ≡ 0,1 (mod 4)`.

This closes the gap the browser stratum `/strata/every-difference-once/` and
`research/graceful-census/` leave open. The census confirms the impossibility by
*enumeration* — it counts **0** graceful labellings at `k = 2, 3` — but a count, however
far it runs, only ever settles finitely many `k`. The kernel proof settles all of them at
once.

## The idea in one line

An edge label `|f(u) − f(v)|` has the same parity as `f(u) + f(v)`. Sum over all edges:
each vertex `v` contributes `f(v)` once per incident edge, i.e. `deg(v)·f(v)`. If every
degree is even, the total is `≡ 0 (mod 2)` — the edge-label sum is even. A graceful
labelling makes that sum the triangular number `tri m`; and `tri m` is even iff
`m ≡ 0 or 3 (mod 4)` (proved here by a period-four induction on the parity of `tri`, no
closed form, no division). It is the same parity-invariant move that defeats Langford's
problem (`research/langford/lean/`) and the mutilated chessboard.

## What is and isn't proved

- **Proved (kernel):** *necessity* — the existence of a graceful labelling ⟹ the residue
  condition, for all `k` / `n`. `windmill_necessity`, `cycle_necessity`, sharing the engine
  `rosa_residue`. `windmill2_impossible` spends the theorem to show `F_2` has no graceful
  labelling at all.
- **Kept honestly apart:** *sufficiency* — that a graceful labelling exists **for** every
  allowed residue — is a construction, exhibited by the census (`graceful.mjs`,
  `graceful.cpp`) and the stratum's playground, not claimed here.
- **The hypothesis is if anything weaker than gracefulness:** it asks only that the edge
  *differences* realise `{1,…,m}` once each (the edge-label half of a graceful labelling).
  The vertex constraints (distinct labels in `{0,…,m}`) are what make achieving it hard;
  they are not needed for the parity obstruction, so omitting them only strengthens the
  necessity claim.

## Footprint

Zero imports (no Mathlib, no Std). `#print axioms` on every theorem →
`[propext, Quot.sound]` (`Quot.sound` enters only through `List.Perm`); no `sorry`, no
`Classical.choice`, no `native_decide` — the kernel evaluates every `decide` itself.
Typechecks in ~1 s.

## Run it

```sh
bash research/graceful-census/lean/install-lean-nix.sh   # github-free install (~2 min)
bash research/graceful-census/lean/verify.sh             # typecheck + print axioms
```

`node research/graceful-census/verify.mjs` (§7) also live-typechecks this file when `lean`
is on PATH and asserts the axiom footprint, alongside the JS/C++ census enumeration.
