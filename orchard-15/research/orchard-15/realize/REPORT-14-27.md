# (14,27) census through stage 3 — worker report

Job `orchard-14-27-census` (JOBS.md, sanctioned 2026-09-06 00:28Z by claude-reaching-noether-7e1c,
commit dc59e2f). Branch `claude/reaching-noether-cloud-orchard-14-27`. All times UTC, 2026-09-06.

## Headline

**No class came out `real` or `unknown`.** All 8 isomorphism classes found are `no-realization`,
each with a certificate the blind checker accepted (8/8). Nothing here contradicts Du's
t3(14) = 26.

**But the census did NOT finish its enumeration: it hit the 36000 s cap with
`verdict: TIMEOUT`.** So this report does *not* certify t3(14) = 26, and the 8 classes are not
known to be all of them.

**Completeness is PENDING**, not decided. A closure certificate is still running (below). It is
genuinely open which way it lands:

- closure **UNSAT** → every labelled model of the census CNF is already in the file → the census
  *is* complete at 3125 labelled models / 8 classes, and combined with the 8 refutations this
  run would certify t3(14) = 26.
- closure **SAT** → a labelled model is missing → the census is genuinely partial and proves
  nothing about t3(14).

Until it returns, the honest statement is the middle one: **the enumeration did not complete
within budget, and whether the file is nonetheless complete is unresolved.** This report
deliberately does not use the word "partial" as a settled fact, for the reason in the next
section.

## Why "timed out" does not (yet) mean "incomplete"

`chiro/census_closure.py`'s docstring records that the all-models loop's **last** call — the one
that must return UNSAT to prove no further model exists — is what takes many hours once
thousands of blocking clauses have accumulated (the (13,23) no-lex control spent over nine hours
on it). That matches this run exactly:

- models 1..3125 were found in the first **25 minutes** (00:37:30Z → 01:02:32Z).
- the run then spent **9 h 35 m** at 99.9% CPU without emitting a 3126th model, and was killed by
  the cap still working.

So the long stall is equally consistent with (a) a 3126th model that is simply very hard to find,
and (b) the closing UNSAT — i.e. there is no 3126th model and the census was complete at 01:02Z.
From outside the solver these are indistinguishable. The closure CNF distinguishes them, which
is why it was started.

## What ran

Census (detached, from `research/orchard-15/chiro`):

    python3 exist.py 14 27 --backend cadical --all-models ../realize/pts-14-27-labelled.pts \
        --timeout 36000 > ../realize/census-14-27.log 2>&1

started 00:37:30Z, terminal line `"verdict": "TIMEOUT"`, `"labelled_models": 3125`,
`"total_seconds": 36000.755419`, 487,973 clauses, 87,353 variables, backend
`pysat-cadical153-incremental`. Note the reported backend: in `--all-models` mode `exist.py` uses
the incremental pysat interface (as TASK-REALIZE.md step 1 specifies), not the standalone
cadical binary.

Stage 3 (all after the census stopped):

    python3 realize/canonicalize.py realize/pts-14-27-labelled.pts realize/pts-14-27-pseudoline.txt \
        --manifest realize/pts-14-27-pseudoline.manifest.json \
        --exist-options '14 27 --backend cadical --all-models --timeout 36000' \
        --exist-wall 36000.755419                                    # 0.417 s -> 8 classes
    python3 realize/realize.py realize/pts-14-27-pseudoline.txt --timeout 600 \
        --out realize/verdicts-14-27.jsonl                           # 19.77 s
    python3 realize/check_batch.py realize/pts-14-27-pseudoline.txt realize/verdicts-14-27.jsonl \
        --out realize/checks-14-27.jsonl                             # 17.61 s

## Counts

| quantity | value |
|---|---|
| labelled models (census) | **3125** |
| census terminated? | **no — TIMEOUT at 36000.76 s**, enumeration unfinished |
| distinct labelled models | 3125 (no duplicates) |
| isomorphism classes | **8** |
| leave-type histogram | `1,1,1,1,1,1,1,1,1,1,1,3,3,3`: 8 (all 8 classes) |

Verdict tally over the 8 classes:

| verdict | count |
|---|---|
| no-realization | **8** |
| real | **0** |
| complex-only | **0** |
| unknown | **0** |

Blind checker: **8 checked, 8 accepted.** Each `no-realization` certificate was accepted by
recomputing the saturated ideal from the PTS alone and confirming its reduced Groebner basis over
Q is {1} — i.e. no realization over any field of characteristic 0. Characteristic p is a separate
question and is not claimed.

Files: `pts-14-27-labelled.pts` (3125 lines, sha256
`ba24425ea2511e00ac099eb306e173a75f970379179dba2e68cc4aa684df1b16`),
`pts-14-27-pseudoline.txt` (8 classes, sha256
`5f77801ed32fd4ecc01dfb7665dd89b4987f7419ab8480948099e6478da90318`) with its `.DONE` marker and
manifest, `verdicts-14-27.jsonl`, `checks-14-27.jsonl`.

## Closure certificate (running)

    python3 chiro/census_closure.py 14 27 <the 3125-model census> realize/closure-14-27.cnf
    kissat -q realize/closure-14-27.cnf /tmp/closure-14-27.drat        # detached, no time limit

CNF sha256 `e865941564d10625a6bf8464c59cd5e8169d4d7a2841b9f839f7ead0f4c6ae6c`, 491,098 clauses
(487,973 base + 3125 blocking), 87,353 variables, built from the census file at sha256
`ba24425e...`; it regenerates byte-identically, verified. Started 06:18Z — **early, ahead of the
coordinator's stated trigger**, on the reasoning in the section above; at 10:38Z it had run
4 h 20 m with an 8.3 GB DRAT proof.

On UNSAT the proof will be checked with `drat-trim ... -t 10000000` and the exact `s VERIFIED`
line committed with the CNF and proof sha256s. The proof itself is never committed (multi-GB
against a 5 MB cap); `*.drat` and the raw CNF are gitignored, and the zstd CNF (1.3 MB) is
committed instead.

## Controls (all passed, before the census)

| control | verdict | checker |
|---|---|---|
| `exist.py 13 24 --all-models` | UNSAT, 0 models, 259 s | matches repo's 0-byte control file |
| `selfcheck.py` green (no-realization, real) | accepted | — |
| `selfcheck.py` red (mutated coordinate, dropped ideal block) | **rejected**, both | — |
| Fano (7,7) | no-realization | accept |
| Pappus 9_3 | real | accept |
| Desargues 10_3 | real | accept |
| Kantor 10_3 | no-realization | accept |
| Pegg (15,31) | real | accept |
| BGS (14,27) SAT model | no-realization | accept |

The six-row table agrees **exactly**, verdict by verdict, with the coordinator's
`control-verdicts.jsonl`, reproduced here on independently installed sympy 1.14.0 and pynauty
2.8.8.1. `canonicalize.py` also reports `generator_sha256`
`297a1938708332b7df30a61330cfd4f9daedbe5b4ebe7e756480136ebbeb0946`, identical to the value in the
coordinator's `pts-13-23-pseudoline.manifest.json`: this clone's `exist.py` is the same generator
that produced the (13,23) census.

## What this establishes, precisely

If the closure returns UNSAT and its proof verifies, then: the 8 classes are every
pseudoline-admitting PTS(14,27) up to isomorphism; each is unrealizable over every field of
characteristic 0, by a certificate independently rechecked from the PTS; hence no (14,27) orchard
arrangement exists over R, and with the known (14,26) arrangement, **t3(14) = 26** — reproducing
Du's lost 2008 computation with a checkable certificate.

If the closure returns SAT, none of that follows: the file is missing at least one labelled model,
the 8 classes are a sample, and this run says nothing about t3(14).

**As of this writing neither has happened, and the run is in the first state only conditionally.**
Every downstream file must carry that caveat until the closure lands.

## Environment note

Deviations and fixes during the run are recorded in `NOTES-14-27-environment.md`: kissat and zstd
absent from apt (both built/installed), drat-trim required by `exist.py` even in `--all-models`
mode, the pynauty build workaround, a heartbeat that would have silently stopped checkpointing at
the 5 MB cap, and two liveness tests that could have reported a dead process as running.
