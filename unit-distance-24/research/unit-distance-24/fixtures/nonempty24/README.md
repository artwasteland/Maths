# Nonempty order-24 certificate

`24-69.g6` has 24 vertices, 69 edges and minimum degree 5.
Its certificate maps trusted TU gadget zero into the graph.
The distinguished pair remains nonadjacent.
Extra edges fill out the graph without changing that witness.
Both stored graphs and their witness maps use nauty's canonical labels.
`24-68.g6` and its certificate remove one edge outside the gadget and relabel canonically.

`tools/test_certificate24.py` wraps this record in a small synthetic chain with seed level 23 and one augmentation.
It runs the unchanged `verify-chain-u24.py --check` and requires `CHAIN OK` with one certificate file replayed.
It removes the witness and requires the exact missing-witness refusal.
It also constructs the corresponding `(24,68)` chain and requires only the TU target-bound refusal.
It reruns the unmutated `(24,69)` chain after each refusal.

This is a test of certificate replay and chain wiring.
The fixture is not an enumerated production slice or evidence of enumeration completeness.
