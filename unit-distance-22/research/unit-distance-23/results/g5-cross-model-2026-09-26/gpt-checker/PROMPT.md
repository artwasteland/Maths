You are building an INDEPENDENT certificate checker for a mathematical proof pipeline. Another team (a different AI
system) wrote the certificate producers and two checkers; your checker's value is that it shares nothing with theirs.
You MUST NOT read any file outside this directory (the current working directory). Everything you need is here:

- RHOMBUS-SPEC.md: the binding specification. Implement its Section 2 (rhombus certificates) and Section 4 (tri case
  trees) EXACTLY, including the amendments in Section 5 (amendment 1: leaf triangles must be exact sorted triples split
  on the path, never matched as sets; either leaf list may be empty but not both; no zero coefficients; amendment 2:
  exact keys everywhere with duplicate-key rejection, both tree children present, arbitrary-precision integers only,
  targets as vector sums, verdict = refuted iff no leaf has an edge, tu iff at least one does).
- data/*.certs.jsonl: real certificate files. One JSON object per line: {"g6": <graph6 string>, "verdict":
  "unknown"|"tu"|"refuted", "witness": {...}}. Records with verdict "unknown" carry no witness and need no check beyond
  well-formedness. Witnesses are {"rhombus": {...}} (Section 2) or {"tri": {"tree": ...}} (Section 4).

Deliverables, all in this directory:
1. gpt_check.py (Python 3, standard library only): `python3 gpt_check.py FILE.certs.jsonl` verifies every record and
   prints one line `ACCEPT records=N unknown=U rhombus_refuted=a rhombus_tu=b tri_refuted=c tri_tu=d` and exits 0, or
   prints `REJECT line L: <reason>` and exits 1 on the first invalid record. Decode graph6 yourself (the standard
   format: first byte n+63 for n <= 62, then the upper triangle column by column, 6 bits per byte, byte value = 6 bits +
   63). Use exact integer arithmetic only (Python int); Z[w] arithmetic with w^2 = w - 1.
2. selftest.py: at least 25 red controls (each a small hand-made certificate that must be REJECTED, with the reason),
   covering every rule of Sections 2 and 4 and the amendments (e.g. a repeated cycle vertex, a missing cycle edge, a
   zero scale, a tu pair that is an edge, an unsorted leaf triangle, a missing tree child, an int64-overflow fake whose
   identity holds only mod 2^64, a wrong rotation w^2 in place of w, a verdict/edge mismatch), plus at least 5 valid
   certificates that must be ACCEPTED (build them yourself: e.g. K_{2,3} refuted by two rhombus rows; K4 refuted; a
   gadget-like forced unit distance). Print PASS/FAIL per case and a final summary line.
3. Run gpt_check.py on every file in data/ and report each output line.
4. REPORT.md: how you implemented each rule, anything in the spec you found ambiguous and how you resolved it, and your
   soundness opinion of Lemma R, Corollaries R1/R2, Lemma T and the case-tree soundness argument (is anything a checker
   must enforce missing from the spec?).

Work carefully; correctness over speed. Your final message: the per-file results, the selftest summary, and the key
points of REPORT.md.
