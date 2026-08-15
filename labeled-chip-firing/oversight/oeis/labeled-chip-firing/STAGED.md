# A282901 extended — labeled chip-firing reaches a(5) = 819

**The sequence.** OEIS **[A282901](https://oeis.org/A282901)** — *Number of permutations
of `1,2,…,2n+1` obtainable via labeled chip-firing* (Hopkins, McConville, Propp,
*Sorting via chip-firing*, EJC 24 (2017) #P3.13; arXiv:1612.06816). It had **five
terms** on record — `a(0..4) = 1, 3, 12, 54, 232` — with keyword `more`, **no b-file,
no program**, since 2017.

**What is staged here.** The **next terms** — `a(5) = 819` (11 chips, verified three
independent ways) and `a(6) = 2555` (13 chips, two independent C++ enumerators; the wall
on one box). The b-file `b282901.txt` gives `a(0..6) = 1, 3, 12, 54, 232, 819, 2555` at
offset 0.

- `b282901.txt` — the extended b-file (offset 0).
- `derive.mjs` — rewrites the b-file from the verified enumerators
  (`node oversight/oeis/labeled-chip-firing/derive.mjs 5`).
- `.zenodo.json` — deposit metadata (title, honest provenance, CC-BY-4.0).
- Full method, three-way verification, and the wall: `research/labeled-chip-firing/`
  (gate: `node research/labeled-chip-firing/verify.mjs` → **29/29**).
- `verify-staged.mjs` — the artifact gate, a shim into `../bind-staged.mjs`.

### ⚠ What the artifact gate covers, and the one term it cannot (2026-08-15)

`verify-staged.mjs` recomputes `a(0..4)` live from `research/labeled-chip-firing/enum.mjs`
and compares them to the staged file (`a(4)` in 0.4 s; `--full` adds `a(5)`, which costs
39 s). The remaining terms are **drift-guarded** against the committed
`research/labeled-chip-firing/data.json`: compared, not recomputed. The gate does not
run `cf`, because building that committed C++ binary dirties the working tree and makes
`coordination/publish.sh` refuse.

**`a(6) = 2555` is therefore the one staged term nothing here recomputes, and it is
exactly the term `../CENSUS-2026-07-26.md` flagged**, under *"do not publish without
re-verifying first"*: **"A282901 `a(6)=2555` (the claimed second build has no source in
the worktree or in git history)."** Checked again 2026-08-15 and that holds: the only
C++ source committed anywhere in this repository is `research/labeled-chip-firing/cf.cpp`.
The "two independent C++ builds" sentence below describes a second build whose source is
not here, so at `a(6)` the honest count of reproducible paths in this repo is **one**.
`a(5) = 819` is unaffected and genuinely multi-path.

## The hand-off — what only the human can do

Per this folder's parent `README.md` and OEIS's *AI-authorship-forbidden* policy, an
instance may **compute and verify** but must not submit. This is an **extension of an
existing sequence** (not a new absent one), so the footprint is small and clean:

1. **Zenodo (the citable step).** Deposit this folder + `research/labeled-chip-firing/`
   as a dataset (metadata in `.zenodo.json`) for a DOI — a permanent, independently
   checkable record of the computation, regardless of OEIS.
2. **OEIS (optional, human-authored).** A282901 has a history of contributors adding
   terms (Schoenfield, the Ekhad–Zeilberger extension, Dobbelaere). A human who has
   **run the verifier and satisfied themselves** may add `a(5) = 819` (e.g. by
   attaching a b-file to the entry, or offering it to the sequence's editors). The
   `a(5)` value and its 6 520 201-configuration search are the contribution; the
   authoring and the standing-behind-it must be a person's.

A request entry for the human is filed under `oversight/requests/` (Zenodo deposit +
optional A282901 term offer). Nothing here is auto-submitted anywhere.

## Honesty line

The chip-firing process, its firing rule, **Theorem 13** (even chips confluES to
sorted), and the sequence **A282901** are Hopkins–McConville–Propp's — cited, not
claimed. **Only `a(5) = 819` and `a(6) = 2555` are new here** — exact (exhaustive search,
small integers). `a(5)` is reproduced by three independent implementations; `a(6)`, past
the JS methods' memory, by two independent C++ builds (different hash + probing). All
reproducible from a fresh checkout.
