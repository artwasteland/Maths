The `full-late` policy finishes the existing escalation portfolio, then runs
`esc-branch-refute` (120 seconds) and `esc-subfield` (180 seconds).
(Integration note, 2026-10-01: the builder wired them into `full`; they were landed as `full-late`, and as `late`
= a fresh 60-second `esc-numeric` then the two stages, for a residue that already had `full`, so that `full` stays
the stage list frontier wave 1 ran.)
Each proposal has a separate 120-second frozen-checker budget.
The standard and cheap policies keep their existing stage lists.
An exhausted search or a rejected proposal remains UNKNOWN.

`branch_refute.py` ranks edge frames by the number of coordinates left after
the existing GP-10 rhombus identities and framed triangle equations.
It then finds triangles whose base direction is fixed in that frame.
For each remaining apex it retains both possible positions.
The current search permits up to three independent choices and two frames.

The branch discovery system omits saturation variables from its Groebner
computation.
It reduces squared distances modulo the branch ideal to find a collision
cover, or uses FGLM and factorization to find a univariate root-free factor.
Distance products remove the collision components.
The cover is minimized before producing a proof.
All this is proposal discovery: it establishes no verdict by itself.

The producer rebuilds the derivation using degree-bounded `liftstd` stages
and exact Horner remainder identities.
For an apex selector s, its two weights are s and 1-s.
Small exact lifts prove that each weight annihilates its branch equations.
Products of these weights lift the local proofs to the original edge and
injectivity system.
Their sum is identically one, so the final row derives the product of the
branch targets without assuming a branch.
The frozen checker verifies every row and applies its ordinary Sturm rule.
This uses GP-10's existing R-real-DAG rule, with no new lemma or checker rule.

Only rows needed by the final identity are serialized.
Unused saturation variables are removed from every exponent vector.
The producer enforces 256 rows and the 8 MiB record limit.
A Singular basis call has a 20-second cap inside the graph budget.
Positive-dimensional branches without an immediate forced collision return
UNKNOWN before distance products can grow without bound.
Failed attempts retain the frames, triangles, distances and discovered
targets in `hints.json`.

`subfield_exact.py` takes numerical points or locates the pipeline's saved
numeric/refinement files and unverified coordinate proposals.
It normalizes the framed edge and refines an isolated configuration using
a rank-selected square Newton system, checking every edge afterward.
Numerical rank only selects a search method; it proves no mathematical fact.
The current recognizer refines to 6,040 digits and uses PARI `algdep` and
`lindep`, with degree bounds 4, 8, 12, 20 and 28.
Recognized polynomials are factored before choosing a basis.
Coefficient height and numerical residual rank proposals only.

It first tries x coordinates, representing x_i and y_i/S in Q(X).
S may be 1, sqrt(3), or a nonzero y coordinate on the unit circle about the
frame origin.
Writing f(X)=E(X^2)+X O(X^2) recovers X from X^2 as -E/O when the inverse exists.
For the circle representation use t=S and X^2=1-t^2.
For the sqrt(3) representation use t=sqrt(3) X and X^2=t^2/3.
Both constructions yield an ordinary rational polynomial field description.
Fallback candidates include y coordinates, x+y and x+2y.
Exact modular checks of every edge reject spurious numerical relations.
A sign change and a Sturm variation difference certify the isolating interval.
The frozen E-exact checker separately proves the common-root embedding and
pairwise distinctness.

Flexible configurations and fields outside this bounded recognition search
can remain UNKNOWN.
In particular, an unproved numerical drawing never becomes a decision.
Analyst hints include the frame, field candidates, attempted representations,
numerical source and refinement diagnostics.

`late_stage.py` runs one worker at a time.
The parent waits while a native solver runs.
Solver threads are limited to one by the existing environment policy.
Workers use the existing address-space limit and memory guard.
The parent monitors MemAvailable while waiting and kills the worker and its
descendants at the graph deadline or the 1.5 GiB floor.
No analyst scratch directory is a production dependency.

Standalone proposal searches:

```bash
~/tools/pyenv-gp10/bin/python research/gp-11/pipeline/branch_refute.py \
  --g6 'JaICZOo@Wd_' --seconds 120 --output /tmp/branch-example
~/tools/pyenv-gp10/bin/python research/gp-11/pipeline/subfield_exact.py \
  --g6 'JoCBkhGIGJ_' --seconds 180 --work /path/to/pipeline/scratch \
  --output /tmp/subfield-example
```

The output is `record.jsonl` plus `detail.json`.
It is a proposal until checked.
For explicit points, `--numeric` accepts JSON containing `points` or `coords`
and an optional ordered `frame` edge.

Reproduce the four analyst cases, including all three valid-JSON mutations
and unchanged positive replays:

```bash
~/tools/pyenv-gp10/bin/python research/gp-11/pipeline/test_late_stages.py \
  --output /tmp/late-stage-test
```

Add `--cohort` to run both stages independently on every retained input.
The runner supports resuming completed cases only when its source hashes,
input hash and budgets match.
Creating `STOP` in its output directory stops it between graphs.
`results/late-stages/inputs.json` retains the numerical inputs, source hashes
and cohort membership, so the measurement needs no analyst files in `/tmp`.
The reported 72 pre-escalation unknowns and the newer pipeline bundle's 41
overlap in 39 graphs, giving a union of 74.
The two stages are measured independently; no propagation discount is used.
