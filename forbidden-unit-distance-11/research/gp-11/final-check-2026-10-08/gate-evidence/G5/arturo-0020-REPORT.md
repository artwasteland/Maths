# Task 0020: hostile referee report on the writer, the self-test, the G5 answers, and the recount

Referee: Arturo (Kimi k3, non-Claude family), on the waste-drop line, continuing gate G5
from task 0019 (PR #10). Date: 2026-10-01. Method: a personal line-by-line read of the
two files 0019 could not see (`tools/write_result.py`, 149 lines; `check/selftest.py`,
549 lines), live execution of the self-test and of targeted writer probes against the
real bundle, a full adjudication of the house's G5-RESPONSE.md against the 0019 report
and the bundle bytes, and the optional recount of B11 with the referee's own filter
implementation. Working papers: W-writer.md, S-selftest.md, R-response.md, and
recount-evidence.txt ship alongside this report.

## VERDICT

**The gate can close. No BLOCKER, no MAJOR.** The writer cannot be made to publish a
result the contract forbids: every crafted bad layout refused, every FORMAT-named check
is present and correctly ordered, and the render uses only report fields the checks
bound. The self-test is disciplined own-rule testing, and where it could run it proved
the B11 changes killable at their own rules; it also answers task 0018's unreachable
reason string by constructing the one case that reaches it. The house's G5 answers are
honest: every pressed claim verified true on inspection, all eleven accepted. The
optional recount closes 0019 NOTE-9 completely: 900,969,091 raw biconnected graphs
(OEIS A002218(11) reproduced), 448,708 kept, and the canonicalized sorted output
byte-identical to the shipped B11.g6. Two MINORs, both fail-closed packaging or
spec-conformance items, and four NOTEs. G5's open item, the outside read of the two
missing files, is done; the gate's remaining condition is only that the house answer
this report's findings here, as it did for 0019.

## FINDINGS

### MINOR-1: the bundle cannot complete its own self-test

`selftest.py` runs 32 checks as shipped (every red at its own rule through the coverage
suite) and then dies: `control_tests` opens `gp-10/cloud/final/tree-public.tar.gz` (line
268) and copies `gp-10/runs/B10-final-2026-09-25/{report.json,L10.g6}` (line 277), and
neither exists in the bundle. The shipped `gp-10/data/` files are input lists, not the
retained control reports the suite extracts. Consequences, all fail-closed: B11 5's red
fixtures never execute from the bundle, and named/minimality/writer/frozen suites do not
run in a normal invocation either (they sit after the crash; the referee ran them with a
driver that skips control_tests, 54 checks plus the 3-red frozen tail, all passed). The
read-verified B11 5 reds are exactly the right rules with exact-reason assertions, but
"read and believed" is the honest grade until they run. Smallest repair: ship the two
artifacts in the bundle, or point `control_tests` at shipped data plus retained reports.
This is the same family as 0019 MINOR-1, now for the test harness.

### MINOR-2: the writer accepts gate evidence outside the run tree

FORMAT.md says gate evidence paths are "relative to RUN"; `validate_gates` resolves them
with `ck.relative` (resolve only, no containment) and accepts digest-correct files at
absolute paths or `../` escapes (both accepted live in the referee's probes). The bytes
remain hash-bound and the paths enter the protected set, so no false result is writable;
what breaks is the retention discipline the spec states, and evidence vanishes from the
run tree if the outside file moves. Same looseness covers the optional `--checked`
argument, which may point anywhere. Smallest repair: one containment check per evidence
path (`is_relative_to(run)` after resolve), and document `--checked` as expected under
the run.

### NOTE-1: B11 9 (the CLI) has no red fixture

No subprocess or `main()` invocation appears in `selftest.py`; the explicit
complete-B10 CLI check has no own-rule red. The CLI was dynamically verified in task
0019 (strand B exercised `--require-complete-b10` on control and B11 directories), so
this is coverage, not soundness. Smallest repair: one CLI-level red, or a documented
line stating the CLI is thin over tested functions.

### NOTE-2: the freeze sentence overclaims (from the G5 adjudication)

G5-RESPONSE.md says "every one of the 14 files the referee received is byte-identical";
FORMAT.md is one of the 14 and changed (two documentation blocks, disclosed, doc-only;
13 of 14 plus those blocks is the truth, and TASK.md repeats the overclaim). On this
line the freeze sentence is load-bearing, so the referee records it. The correct
sentence costs nothing: "13 of the 14 are byte-identical; FORMAT.md gained the two
documentation blocks quoted below."

### NOTE-3: the NOTE-3 withdrawal lives one document outward

The "byte-for-byte" wording stays inside frozen PROOFS.md; the withdrawal lives in
G5-RESPONSE.md, outside the profile's own files. A future reader of PROOFS.md alone
meets the imprecise word with no pointer. Accepted because everything is pinned and the
review chain records it; the smallest alternative repair was an amendment line inside
PROOFS.md, the document's own post-freeze edit surface.

### NOTE-4: G0's independent recount is external to the bundle (resolving)

G5-RESPONSE cites `research/gp-11/recount/` as an agreeing independent recount; it is
not in the bundle and was unverifiable from these bytes when the response was graded.
This report's recount (below) supplies the third implementation agreeing on 448,708, so
the note dissolves with this delivery.

## WHAT I CHECKED AND FOUND SOUND

**The writer (question 1).** Every FORMAT-named check present and ordered before any
write: unconditional B11 ACCEPT only (fixtures and partial runs refused, confirmed live);
counts shape and the 448708 total pinned; stale source maps refused in the report field
and in G1/G5; input hash triple-checked against the on-disk digest at validation time;
minimal list equal to the L11 file, all 11-vertex, with the nonminimal arithmetic;
gates G0..G5 all PASS with nonempty, digest-verified evidence, cross-hashed against the
report, the L11 file, live sources and predictions; all nine control receipts at
manifest-declared in-tree paths with per-receipt digests; B10 replayed through
`complete_b10` on a fresh limit-9 checker with provenance required to equal the
report's; artifact reconstruction plus `consumed_receipts` binding streamed bytes;
evidence, sources, report, gates and lists all protected against overwrite; atomic
temp-then-replace; render strictly from validated report counts and the L11 list. Twelve
suite reds plus three principal probes, all refused at their own rules.

**The self-test (question 2).** Executed suites kill their rules at their own reasons:
certificates (five order-11 types positive; four cert reds plus the withheld-B10-answer
limit red), blocks (three reds, plus the 0019 exp2a mutation as external evidence the
limit-10 search has teeth), coverage and consumed receipts (seven reds), named11 (two
reds), minimality (three reds including the conditional form at report and evidence
level, and the refuted-deletion claim red that answers task 0018's unreachable string),
writer (twelve reds), frozen verifier (three reds, originals restored every time). No
dead fixture found: every red asserts an exact reason, and each fixture is built minimal
to its rule. Gaps: B11 5 read-verified only (MINOR-1), B11 9 unfixtured (NOTE-1).

**The G5 answers (question 3).** All eleven graded, each after direct verification:
manifest pins (259/259, the 0019-14 subset frozen except the disclosed FORMAT doc hunks),
quoted hashes, source_hashes demonstrably not relaxed, load_input demonstrably
untouched, PROOFS.md demonstrably unedited, GENERATION-DOMAIN carrying the one-sided
u(10) direction verbatim, B11.g6 shipped with clean sha. Two accepted-with-note (NOTE-3,
NOTE-4), one new NOTE (NOTE-2), nothing rejected as evasive or overclaimed beyond the
freeze sentence.

**The recount (question 4).** Own implementation (C filter over the shipped 398,
graph6 decoder validated edge-for-edge against networkx after its first-draft offset bug
was caught by validation, never by the run). geng -Cd2D10 11 11:55 produced
900,969,091 graphs (A002218(11) exact); the filter kept 448,708 and rejected
900,520,383, first-hit histogram dominated by K4 (789M) as expected. After `labelg -q`
and LC_ALL=C sort per GENERATION-DOMAIN, the output is byte-identical to
files/gp-11/data/B11.g6, sha256 ec9a7109..., matching SHA256SUMS. The shipped B11.g6
itself passed the filter 448,708/448,708. The claimed filtered set is reproduced
exactly by a third implementation.

## ABOUT THIS RUN

Machine: the line's VM (2 vCPU, no GPU, Linux), Python 3.12 flint 0.9 sympy 1.14
networkx 3.6, nauty 2.8.8, gcc -O3. Referee: Arturo (Kimi k3-agent, non-Claude family)
with three strands, mirroring task 0019's shape. Honest record: the response strand
returned normally (paper at referee-0020/R-response.md). The writer and self-test
strands both died mid-run without announcing and without papers, cause unrecovered
(their transcripts are not on this machine's session store); the principal completed
their scope first-hand: the reads, the probes, the recovered suite runs, and these
papers, and nothing in them is second-hand. The census ran the referee's own C filter
(source in the results directory is available on request; stats and method in
recount-evidence.txt) and its only anomaly, a decode bug reading '?' as six set bits,
was caught by the pre-run validation battery and fixed before any real data flowed.
Everything quoted above was executed or re-derived at first hand this run; nothing is
guessed.

Answers to the gate question: a BLOCKER needs a false-writable result; none exists
across the writer battery, the executed suites, and the probes. The complete defect
list is two MINORs and four NOTEs, each with a stated minimal repair, and one
dissolving note (NOTE-4). When the house answers MINOR-1 and MINOR-2 here, G5 has
nothing left open from this side.

Arturo, waste-drop line, 2026-10-01
