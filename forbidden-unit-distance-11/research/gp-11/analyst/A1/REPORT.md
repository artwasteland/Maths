Both packet A1 graphs are refuted-certified. Each individual sample run ended with `ACCEPT run verified`, with one refuted graph and zero unknowns. This establishes non-embeddability; no edge-deletion minimality claim is made.

| Graph | First ACCEPT, wall minutes | Certificate | Checker |
|---|---:|---|---|
| `JaICZOo@Wd_` | 22.291 | [A-real-dag.jsonl](records/A-real-dag.jsonl), 234 rows, 6,231,976 bytes | [receipt](check-A.log) |
| `JSO@]OSDjB?` | 13.612 | [B-real-dag.jsonl](records/B-real-dag.jsonl), 157 rows, 7,231,939 bytes | [receipt](check-B.log) |

Timing is measured from 2026-09-30 22:38:25 UTC to the end of each first accepting checker call. Both graphs were investigated together from the outset; shared setup and proof-method development overlap, so these figures are not additive. Both decisions were obtained within 22.291 minutes. The `*.meta.json` files retain individual attempt timestamps, durations, exit statuses, and minimum available memory.

For `JSO@]OSDjB?`, triangle pairs and rhombi reduce the coordinate equations to a finite system. Distinctness of (2,7) and (2,5), together with the rhombus assumptions, leaves a degree-18 equation for x0 with no real roots. Staged Groebner identities and a sequence of polynomial remainders turn that observation into the accepted DAG.

For `JaICZOo@Wd_`, the useful move was to split the two equilateral-triangle choices after framing edge (8,10). Two of the four cases force collisions. The other two force, respectively, a positive quartic and a root-free octic in y0. Exact polynomial selectors combine every case into one degree-12 Sturm contradiction. Both circle-intersection choices are retained throughout.

What failed: direct saturation on the unsplit first graph timed out at 120 seconds; direct high-degree reduction also timed out at 120 seconds. Unstaged or insufficiently split lift computations produced 100.9 MB and 216.5 MB text outputs, far too large for the checker's 8 MiB record ceiling. An initial saturation probe used the wrong Singular return convention and was corrected; none of these attempts supplied a verdict.

What would make this faster: a reusable producer for certified triangle-case splitting, staged low-degree ideal identities, and Horner remainder certificates. The most useful packet hints would have been frames (8,10) and (8,9), the first graph's two triangle choices and additional collision pairs (0,4) and (2,10), and x0 as the second graph's useful elimination coordinate. The shared nine-vertex core alone did not supply the decisive hint.

All files were written under `/tmp/gp11-analyst-A1/`. No git commands were run. The checker source hash is `d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04`; only its runtime scratch-directory constant was redirected into this directory. Checkers used the requested sample profile. Heavy jobs were bounded and monitored; all monitored available-memory readings stayed above 1.5 GB. See [ARGUMENTS.md](ARGUMENTS.md) for coordinates, factors, saturation lists, and replay commands.
