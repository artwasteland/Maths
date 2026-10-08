# Development control notes

An initial lattice-only probe left Petersen and the Moser spindle unknown.
No full B10 run or control PASS was claimed. The lattice probe chose only
the first placed neighbour as an anchor. That loses placements when a
closing unit edge is outside the finite direction set. The implementation
now tries directions from each placed neighbour and checks all incident
placed edges exactly. This remains an incomplete finite search.

Petersen can require directions outside that lattice. A structural search
now enumerates pairs of regular polygon layers and derives their relative
rotation from the unit spoke equation. It uses graph structure, not named
graph codes or coordinates from a library. All resulting coordinates still
pass the ordinary exact verifier. Controls are rerun after these changes.

The embedder cannot refute the Moebius ladder or any other graph. Unknown
is the only permitted negative output of this module. The contract's full
control pipeline needs the separate refuter and blind checker.

The complete baseline B9 sample left some F9-free inputs unknown. This is
incomplete search coverage, so the global control gate is open. The method
measurements continue as development experiments, with unresolved records
retained. No full pipeline control PASS or classification is claimed.

The resource ceiling is interpreted conservatively for all searches. A
read-only bootstrap command read COMMON.md with nice increment ten before
its stricter increment and memory instructions were available. Subsequent
commands used the common increment and the stricter contract memory cap.

## Round 2 setup and preliminary failures

The installed msolve CLI crashed with SIGSEGV and empty output even on the
manual two-variable example under `ulimit -v 1000000`. A diagnostic allocation
interposer in `/tmp/gp10-embed/round2-probe/` reported a failed 1073741824-byte
allocation. Disassembly located two header allocations and three fgets limits.
`msolve_exact.prepare_binary` guards the installed binary by SHA256 and reduces
only these five immediates to 1048576 in a scratch copy. The installed binary
is untouched. Generated inputs must be smaller than this buffer. The initial
failures are explained by the stricter contract memory cap; no solver result
from those crashes is used.

The first ten maximal unknowns, tested with an explicit dense separating
variable in the input, gave eight unsuccessful numerical preparations and two
20-second solver timeouts. Their artifacts remain in
`results/round2/pilot-dense-separator/`. A rigid graph without the extra variable
solved in under a second. Production therefore lets msolve add its separator
after its first basis computation. A small srand interposer seeds its internal
randomness from the graph SHA256. No numerical or CAS status alone accepts a
certificate. Repeated-seed and one-field mutation controls cover the parser.

The allowed scratch paths exclude the checker's hardcoded `/tmp/gp10-check`.
The round-two wrapper imports the unchanged checker, redirects its SCRATCH,
TMPDIR and SQLITE_TMPDIR into `/tmp/gp10-embed/`, then calls its normal main.
The checker source and all verification functions remain unchanged.

The first scripted round-two control run stopped in the test harness because
python-flint polynomials do not implement deepcopy. The mutation fixtures now
copy dictionaries and replace a polynomial, leaving the positive untouched.
No producer or certificate acceptance failed in this harness exception.

The oriented-rhombus control then found a parser ordering defect: msolve
permuted its variables, and its coordinate boxes follow that printed order,
not the submitted order. The old parser returned no certificate. The parser
now uses the printed order for both coordinate functions and root boxes. A
reordered-variable positive test and a repeated added-separator test cover both
branches. Production was paused until those controls passed. The first
30 c2/cross-direction experiments remain in `pilot-c2-cross-directions/`;
production uses oriented unit vectors and hard child limits for preparation
and conversion. Two linear pin equations replace an edge's unit equation,
so each direction pin adds one local degree-of-freedom constraint.

The first 120 production graphs exposed slow full-eliminant denominator
inversion and two outputs whose ideal degree exceeds their square-free
eliminant degree (multiplicities). The parser had conservatively rejected
these. It now records both degrees and converts each irreducible factor
separately before inverting the denominator. This preserves the same
separating element, can reduce coefficient growth, and validates every
input equation on the selected factor. The 23 controls still pass.
Saved complete outputs can be reconverted with `round2_reconvert.py`,
which preserves the original record and stats and charges the retry time.

## Round 2 completion and unresolved parametrizations

All 1337 requested cohort memberships were processed in order. The quiet-box
pass performed 18 maximal retries at 120 seconds, recovered 10 embeddings,
added two triage candidates, and timed out on three graphs. It stopped when
one-minute load reached 2.078125, above the predeclared maximum of 2.0.
Fifty-five first-pass timeout memberships were not retried.

Four completed outputs remain conservatively rejected. H`HIKcx, IGC@kXL{_,
and IGCDGxL{_ fail the printed separator relation under the current parser
interpretation. Exact diagnostic substitution on every eliminant factor
satisfied the original input equations for all three, but the separator
residuals were nonzero and nonconstant. The residual evidence is retained
in `results/round2/separator-diagnostics.json`. This could be a metadata
interpretation defect; no cause is established and no check was bypassed.
The fourth graph, I@CGNBBNg, failed original input equations on a linear
factor and two quadratic factors, although other factors satisfied them.
No attempt was made to salvage a certificate from a partly invalid output.
All four remain unknown and none enters triage.

The final 25-control suite passes. The official merged-run check accepted
4900 embeddings and 1178 unknowns in 265.158 seconds, with final line
`ACCEPT run verified`. It records niceness 19 after its own additional
increment; all commands were launched at niceness 15.

## Round 3 conversion and source interpretation

All 13 supplied gaps mapped into G118 numerically. The first per-image PARI
attempt reached degree 8, then hit the 180-second cap with thread-stack
allocation warnings in matrix conversion. Explicitly setting PARI's thread
count to one removed that failure. The preserved single-thread repeat passed
exact verification. The final run uses graph-derived seeds and repeats both
small controls and an actual degree-16 image.

All 13 gaps closed through G118. H1 and H2 were independently reconstructed
using the fixed coordinates and triangle relations in the paper's figure,
then checked against every printed complex minimal polynomial. H2 requires
adding sqrt(3) to the last two printed x coordinates for the actual figure
positions. The polynomial check uses the displacements, matching those table
rows. The exact graph verifier checks the translated points. One-coordinate
and one-table-coefficient red controls reject for explicit expected reasons.

The optional shared-box observation failed both load and idle criteria, so
no maximal or uniform graph was attempted in round three. This is a deferred
optional extension, not a negative result for those graphs. The full n=9
control still belongs to the supervisor's merged pipeline; this module
supplies the 13 missing exact certificates without claiming the global gate.

## Round 4 development notes

The initial new control failed because python-flint did not accept a Python Fraction directly. The control was corrected to pass its exact rational spelling. A subsequent resume control failed because fresh JSON records retained insertion order but rebuilt streams inherited sorted keys from durable record.json files. Both stream-writing paths now use sorted keys. These failures occurred before the candidate snapshot and production launch. The final local control log replaces the earlier development log; the failure descriptions here and in REPORT.md preserve what happened.

The completed candidate pass used the requested 20-second msolve and 10-second G118 method budgets, with no quiet gate. All 1,137 launch-unresolved candidates were processed; the final external snapshot was complete. The final checker accepted 1,202 embedded, 98 refuted and 215 unknown candidate records. Round 4 added 912 unique embeddings beyond the completed external pass.
