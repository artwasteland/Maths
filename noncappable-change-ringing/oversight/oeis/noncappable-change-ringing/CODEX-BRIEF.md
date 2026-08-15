# Brief: close the verification-coverage gap (audit finding, 2026-07-20)

You are a careful implementation worker on a mathematics repo. A coverage audit
found that this directory's verifier never checks the staged b-file terms. Your
job is points 2 and 6 of the audit's work order, below. A supervisor will
review your diff; prose corrections elsewhere are being handled separately, so
do NOT edit README.md or the draft-bells*.txt files.

Working rules:
- Edit ONLY in this directory (oversight/oeis/noncappable-change-ringing/):
  verify.mjs, engine.mjs, and one new data file. Nothing else.
- You may READ ../../../research/change-ringing-sequences/extension/runs/*.out
  (finished run outputs; format: "# L path cyclic noncappable" then one line
  per level).
- NEVER run derive.mjs, stage.mjs, or anything in
  research/change-ringing-sequences/ (some of those scripts rewrite data
  files). Running `node verify.mjs` here is fine and expected.
- Do not use the em dash character in ANY text you write (code comments,
  data file headers, output strings). Use commas, colons, or parentheses.
- Match the existing code style (ESM .mjs, BigInt terms, small dependency-free
  scripts).

## Task 1 (audit point 2): make verify.mjs check every staged b-file term

Create `expected-extension.mjs` (or a similarly named small module): a
committed expected-values table for the extension terms beyond the published
OEIS range, sourced from the finished run outputs:
  runs/n5-L20.out and runs/n5-L21.out for n=5 (L=19..21),
  runs/n6-L14.out and runs/n6-L15.out for n=6 (L=14..15),
  runs/n7-L12.out and runs/n7-L13.out for n=7 (L=12..13).
Copy the noncappable values as literal strings/BigInts with a header comment
stating exactly which runs/*.out file and line each value came from, and the
date you copied them. Where a level appears in two run outputs (n=5 L=19,20 in
both the L20 and L21 runs; n=6 L=14 in both; n=7 L=12 in both), record BOTH
and have the table constructor assert they agree.

Then extend verify.mjs:
  a. Read every `b-bells{4,5,6,7}.txt` file, parse "index value" lines.
  b. Check the published-range prefix of each b-file equals DATA's
     path minus cyclic, term by term.
  c. Check every term beyond the published range equals the expected-values
     table, and that the b-file has no terms the table does not cover (and
     vice versa: flag table entries missing from the b-file).
  d. Keep all existing checks. Update the file's header comment to describe
     the new coverage honestly (and adjust the stated runtime if it changes).

## Task 2 (audit point 6): a genuinely direct noncappable counter

In engine.mjs's DFS, add a directly-counted noncappable tally: increment when
a path's endpoint is NOT adjacent to rounds (rather than deriving noncappable
as path minus cyclic). Keep the derived value too, and have verify.mjs assert
direct == derived at every level it computes. If engine.mjs already counts
directly, verify that claim by reading the code carefully and say so in your
final message.

## Task 3 (audit point 4, runtime side): the DFS floor

verify.mjs's REACH is {4:24, 5:12, 6:9, 7:7}. Time the current run. If raising
n=6 to 10 and n=7 to 8 keeps the TOTAL verify.mjs runtime under ~90 seconds on
this machine (test it with nice -n 19), do it. Do NOT raise n=5 to 13 (that is
minutes-to-hours in JS; an independent compiled check at L=13 exists elsewhere).
Report the measured runtime.

When done: run `node verify.mjs` one final time, confirm every check passes,
and summarize in your final message: files changed, checks added, measured
runtime, and anything that did not reconcile (report discrepancies honestly,
never paper over them).
