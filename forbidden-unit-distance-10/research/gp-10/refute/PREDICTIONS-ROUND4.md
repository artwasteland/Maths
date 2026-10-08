# Round 4 schedule, recorded before frontier production

The supplied residue has 702 graphs. Previous 5-second algebra searches
found no new refutations. I predict that most remain unknown at these
budgets, without assigning a defensible numerical success probability.
A 40-second tree retry may resolve some earlier deadline/state-limit cases.

The primary queue is increasing edge count. Newly available likely-forbidden
hints take precedence, with hinted graphs ordered by edge count. This is
the explicit priority exception requested in the brief. Hints arriving
after an unknown result trigger a separate targeted algebra retry.

Each candidate receives TU at 0.5 seconds, tree at 40 seconds with 10000
states and both L3 children, null at 10 seconds with distance-two non-edge
saturation, then real at 10 seconds with four-cycle and hinted collision
saturation, stopping when a verified certificate is found. The real pass
includes an exact-reconstructed quadratic SOS search with at most 600 rows
and at most 1 second of single-threaded LP time inside its total budget.
Hinted collision pairs receive saturation; hinted algebra retries use
30 seconds for null and 30 for real. DAG output is selected automatically
when expansion is large. A hint is not trusted by any proof check.

Each invocation reserves at most 270 seconds of method budgets on a stated
sample, normally four graphs. All batches receive independent official
checking with F9 in force. Only the producer and at most one child run at
a time, each niced and capped at approximately 1 GB address space.
