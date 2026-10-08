# A blind second verifier for the (23,65) top-level certificate

`verify_tree.py` is an independent checker of one refutation certificate: it reads a graph (graph6) and one
certificate record, and prints `ACCEPT` (exit 0) or `REJECT <reason>` (exit 1). It was written on 2026-09-27 by a
different model (OpenAI codex, `gpt-6-astra` at reasoning effort `max`) from `BRIEF.md` alone. The brief forbade it to
read anything outside its own directory, in particular the reference checker `research/unit-distance-22/check/udcheck.py`
and every prover. What it had:

- `spec/FORMAT.md`: the certificate wire format (the reference checker's module docstring, copied verbatim; the code
  was withheld);
- `spec/PROOFS.md`: the mathematics (`research/unit-distance-22/check/PROOFS.md`);
- the graph and certificate of the one graph the fleet's filter-only prune kept at (23,65): slice 50's
  `research/unit-distance-23/results/u23/top-level/s50of1920/23-65.g6` (sha256 `c90a07cd8b44…`) and `23-65.certs.jsonl`
  (sha256 `46f2d3de06f7…`).

Why it exists: the two checkers that accepted this certificate before, `udcheck.py` and `udcheck398.py`, are one
implementation (`udcheck398.py` executes `udcheck.py`'s pinned bytes). This one shares no code with them. It uses the
standard library only, with exact arithmetic throughout (integers, `Fraction`, exact polynomials); no floating point
enters any decision.

Its verdict and its own report are in `REPORT.md`, which ends `BLIND VERDICT: ACCEPT`. In summary, it found:

- The root's rows are exactly the row space of the rhombus equations of all 57 four-cycles of the graph (dimension 18).
  It derived these itself.
- The field's minimal polynomial `81t^4 - 684t^2 + 256` is irreducible (an exhaustive Kronecker search), and the
  interval isolates one real root (Sturm).
- The tree has 15 nodes. Its 7 Heron splits (L3) were checked exactly, discriminants 3 and 11/9, each child's row
  space being exactly its parent's plus the stated row. Its 8 leaves (L1b) each force two unit edges into a ratio
  `omega` with `|omega|^2 != 1`.

Where the specification was silent, it chose the strictest reading and says so in `REPORT.md`: the root's rows, the
meaning of L1b, and L1a and L2, which it does not support.

Its four red controls are in `controls/`, and each is rejected for its own reason (`verification_results.json`):
- (a) one entry of the root's A changed;
- (b) one child subtree removed;
- (c) the root move's coefficients changed;
- (d) the certificate against the graph with the edge {0,4} removed.

Three more tampered inputs were then made by the coordinator, and each was rejected for its own reason:
- the field's interval moved off its root: "expected exactly one real root, found 0";
- one L3's `d` changed: "L3 d squared does not equal the Heron discriminant";
- one L1b's `omega` changed: "L1b x-omega*y is not in A row space".

`research/unit-distance-23/tools/blind_check.py` runs this verifier over every top-level record and makes all seven
tampered inputs afresh for each certificate. `write_result.py` requires all of that to pass before a draft can be
COMPLETE.

Run it on the real certificate:

```sh
python3 research/unit-distance-23/blind-verifier/verify_tree.py \
  research/unit-distance-23/results/u23/top-level/s50of1920/23-65.g6 \
  research/unit-distance-23/results/u23/top-level/s50of1920/23-65.certs.jsonl
```

`REPORT.md` and `verification_results.json` name the inputs by their paths in the verifier's own directory
(`data/23-65.g6`, `data/23-65.certs.jsonl`). Those are the two slice-50 files above, byte for byte.

Its scope is this certificate. It does not certify L2 moves, gadgets, or anything else a future certificate might use.
