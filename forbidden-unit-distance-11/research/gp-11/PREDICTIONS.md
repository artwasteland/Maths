# GP-11 predictions (CONTRACT Section 5.5), committed before any B11 run

Written 2026-10-01 (AEST ~05:00) by claude-answering-alexeev-u22, after the controls and the sample measurements and
before any run over B11 exists (no pipeline has been built yet). The point is that the B11 run can surprise us: every
number below is a forecast with its basis, to be compared with the checker's output afterwards, never adjusted.

## The basis

- The architect's sample (500 graphs, seed 20261001) and the escalation's (2,000, seed 20261002), all certificates
  accepted by the frozen GP-10 checker (design/MEASUREMENTS.json, design/ESCALATION-REPORT.txt): of 2,500 sampled
  graphs, 2,467 embedded, 27 refuted, 6 undecided (numerical guesses: 4 embeddable, 2 forbidden).
- The degree-two extender alone (embed/EXTEND-REPORT.txt): 4,534 of a 5,000 sample (seed 20261003).
- GP-10: 509 refuted of 33,162 (1.53%), 324 of them minimal (64%); OEIS A308349 runs 1, 1, 1, 3, 13, 55, 324 for
  n = 4 to 10 (ratios 1, 1, 3, 4.3, 4.2, 5.9).

## The forecasts

| quantity | forecast | 95% range and basis |
|---|---:|---|
| refuted graphs in B11 | about 5,200 | 3,600 to 7,300: 27 to 29 refuted in 2,500 sampled (1.1 to 1.2%), sampling error only |
| embedded graphs in B11 | about 443,500 | the rest |
| minimal forbidden graphs on 11 vertices, \|L11\| | about 3,000 | 1,500 to 6,000: the refuted count times a minimal fraction of 40% to 70% (GP-10: 64%), and a growth ratio of 5 to 18 over 324 |
| undecided after the automated stages (the analyst residue) | about 900 | 349 to 2,302: 4 undecided of 2,000 after escalation (0.20%); the 500-sample gives 1,795 (493 to 6,491) |
| share of the residue that embeds | about two thirds | the six observed survivors guessed 4 embeddable, 2 forbidden (numerical, not certificates) |

## What would surprise us

- \|L11\| outside 1,500 to 6,000.
- A residue above 2,300 after the automated stages, or one dominated by forbidden graphs.
- Any disagreement between the B11 run and the samples' checked decisions (each sampled graph's verdict is fixed by
  its accepted certificate).
