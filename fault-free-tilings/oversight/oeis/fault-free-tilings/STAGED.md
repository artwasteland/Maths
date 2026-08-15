# oversight/oeis/fault-free-tilings

**Fault-free domino tilings of the rectangle**, the counts that were on record
nowhere. A *fault line* is a straight line running clear across an `m × n`
rectangle that misses every domino; a tiling with none is *fault-free* (a
bricklayer's running bond). Backs the stratum **The Wall That Won't Crack**
(`/strata/the-wall-that-wont-crack/`) and the notebook
`research/fault-free-tilings/`.

## What is already recorded, and what is new

- **Already in OEIS:** the *square diagonal* `FF(2n, 2n)` is
  [A124997](https://oeis.org/A124997) (Knuth 2008; b-file by A. P. Heinz & Xu
  Mingkuan to the 24×24). We use it as a correctness anchor, and we do **not**
  claim it as new. How much of it this repository actually recomputes is set out
  below, under "What this repository recomputes of A124997, and what it copies";
  the short version is ten of the twelve terms, not all twelve.
  Also recorded: [A232621](https://oeis.org/A232621) (*vertically* fault-free
  5×2n, a weaker notion, reproduced here via `VFF`).
- **New here (absent from OEIS, checked 2026-07-11, every one returns `null`):**
  the *off-diagonal / general rectangle* counts. Staged as b-files:
  - `b-ff-5xn.txt` (44 terms) fault-free `5 × n`: `…,6,0,108,0,1182,0,10338,…`
  - `b-ff-6xn.txt` (40 terms) fault-free `6 × n`: `…,6,0,124,62,1646,1630,18120,…`
    (the interior `0` at `6×6` is the Graham exception, *inside* the row)
  - `b-ff-7xn.txt` (34 terms) fault-free `7 × n`
  - `b-ff-8xn.txt` (28 terms) fault-free `8 × n` (contains `FF(8,8)=25506=A124997(4)`)
  - `b-ff-array-antidiagonals.txt` (324 terms) the array `T(m,n)` for
    `1 ≤ m,n ≤ 18`, read by antidiagonals; its `2n×2n` diagonal is A124997, and
    its last term is `FF(18,18) = A124997(9)`.

  470 staged terms in total.

## What this repository recomputes of A124997, and what it copies

This section replaces an earlier claim in this file, which read: "We **reproduce
all twelve of its recorded terms exactly** (to the 70-digit `FF(24,24)`) as our
correctness anchor". That was false for the four largest terms, and the way it
was false is worth recording, because it was self-certifying rather than merely
sloppy:

- `research/fault-free-tilings/verify.mjs:97` recomputes `FF(2k,2k)` live for
  `k = 1..8` only, against a literal table at lines 92 to 96.
- For `k = 9..12` the same file prints (lines 98 to 99) that they are "all
  reproduced by this engine … computed offline, see data.json / README."
- `data.json`'s `diagonal` block is not engine output. It is a hardcoded literal
  in `research/fault-free-tilings/gen-data.mjs:9-15`, whose own comment reads
  "validated constants (each independently reproduced by this engine; see
  verify.mjs)".

The two pointers point at each other. Grepping the 70-digit `FF(24,24)` across
the repository returns exactly three hits, all of them string literals:
`verify.mjs:96`, `gen-data.mjs:15`, and `data.json:816`, the last being a copy of
the second. At the time of the audit, `FF(20,20)`, `FF(22,22)` and `FF(24,24)` were computed
nowhere here. `FF(20,20)` has since been computed (below); the other two still are
not.

What is true, term by term:

| A124997 term | board | status in this repository |
|---|---|---|
| 1 to 8 | `FF(2,2)` … `FF(16,16)` | **recomputed live**, every run of `research/fault-free-tilings/verify.mjs` |
| 9 | `FF(18,18)` = `50272239752141442901464758051467073726` | **recomputed** by `verify-staged.mjs --full`. It is index 324, the last term of the staged array; recomputing it and the rest of the 18-edge is what makes `--full` roughly 25 to 40 s slower than the default run, in which it is drift-guarded against `expected-extension.mjs` instead |
| 10 | `FF(20,20)` = `174927321882862834702052846250836696969014873138` | **recomputed once, out of band, on 2026-07-27**, in 342.8 s, and it matched. Log: `ff-20x20-run-2026-07-27.txt` in this directory, with the script that reproduces it. Too slow for any gate, and not a staged term |
| 11, 12 | `FF(22,22)`, `FF(24,24)` | **transcribed from the OEIS b-file** of Heinz & Xu. Not computed anywhere in this repository, then or now. Agreement with them is not evidence about our engine, because our engine has never produced them |

So: **ten of the twelve recorded terms of A124997 are reproduced by this engine,
through `FF(20,20)`. The last two, including the 70-digit `FF(24,24)` that the old
claim was named after, are quoted, not reproduced.**

Of those ten, eight are recomputed by a gate you can run in seconds, the ninth by
`verify-staged.mjs --full`, and the tenth only by the committed one-off log above.
Those are three different strengths of evidence and this file does not blur them.

One defect remains that this directory cannot reach: the printed lines
`research/fault-free-tilings/verify.mjs:98-99` still assert that terms 9 to 12
are "all reproduced by this engine". That file is outside this directory's edit
scope. It is a known false line, recorded here rather than left for a reader to
discover.

## Why these are trustworthy, and exactly how far each reason reaches

The counter is checked more than one way, but the ways are not equally strong and
they do not all reach the same terms. Naming what differs between them:

| way | what actually differs | how far it reaches |
|---|---|---|
| inclusion–exclusion sieve over fault lines (`research/fault-free-tilings/ff.mjs`) | the engine itself | every staged term. This is the single source of all 470 |
| from-scratch brute force (`verify.mjs`, "Method B") | **a genuinely different algorithm**: lays out every tiling one domino at a time and detects fault lines directly, with no formula and no sieve | 8 boards, the largest being `5×10`, `6×8` and `7×8` |
| `brute.cpp` | **same algorithm** as Method B, different language and compiler. Not a third opinion about the mathematics | nothing, at present: no gate compiles or runs it, and no run output is committed |
| the published record | independent authors, independent code, decades apart | A124997 terms 1 to 10 and A232621 `VFF(5,2n)` for n = 1..6 |
| Graham–Kotzig zero/nonzero map | an independent *structural* prediction rather than a term-by-term value | which entries are 0 and which are positive, for `m,n ≤ 12` |
| symmetry `FF(m,n) = FF(n,m)` | same code path evaluated twice, so the weakest check here | internal consistency only |
| `verify-staged.mjs` (new) | not a second opinion on the mathematics at all: it checks that the **staged artifact is what the engine says** | all 470 staged terms |

The honest count, per staged term: **two independent algorithms below the
brute-force horizon (`5×10`, `6×8`, `7×8`), one above it.** Most staged terms are
above it. Beyond that horizon the guarantee is that the deposited number is
exactly what `ff.mjs` computes, plus agreement with OEIS wherever OEIS has the
value, and nothing stronger.

For completeness, the engine gate also pins staged row values against literals at
`verify.mjs:122-130`, reaching `5×16`, `6×12`, `7×12` and `8×10`. Those are
single-path pins, not a second algorithm.

## Are the staged numbers bound to any check?

Until 2026-07-27, no. A mutation prober rewrote all 470 staged terms across all
five b-files at once and ran the directory's whole committed check set;
`node research/fault-free-tilings/verify.mjs` produced byte-identical output and
exit code 0. Zero of 470 staged terms were bound to anything. The measurement is
`research/oeis-term-coverage/coverage-before.json`, under
`dirs["fault-free-tilings"]`. The engine was being checked; the file that would
actually be deposited was not.

`verify-staged.mjs` in this directory is the fix. It reads these five b-files and
reproduces them from `ff.mjs`, and it ships inside the deposit bundle so the
bundle carries its own check.

| run | staged terms recomputed live | drift-guarded only | bound to nothing | wall time |
|---|---|---|---|---|
| `node oversight/oeis/fault-free-tilings/verify-staged.mjs` | 435 of 470 | 35 | 0 | 10 to 15 s |
| `node oversight/oeis/fault-free-tilings/verify-staged.mjs --full` | 470 of 470 | 0 | 0 | 36 to 50 s |

The 35 terms the default run does not recompute are the array cells with `m = 18`
or `n = 18` (indices 154 to 324 of `b-ff-array-antidiagonals.txt`, scattered, not
contiguous; the script prints the exact ranges). They are still read and still
compared, against `expected-extension.mjs`. **That is drift protection, not an
independent recomputation:** same engine, recorded on 2026-07-27, not re-executed.
`full-array-run-2026-07-27.txt` is the committed output of the `--full` run that
earned those values live.

Timings above are ranges over 5 default and 3 `--full` runs on 2026-07-27, Node
v22.22.2. They are measured, not estimated, and they are given as ranges because
the run-to-run spread is large enough that a single number would misrepresent it.

The default run was confirmed to go red. Six staged terms were mutated by `+1`
(the last term of each of the four row files, one live array cell at index 163,
and one drift-guarded array cell at index 324); it printed six named failures,
reported `bound to nothing: 1`, and exited 1. The b-files were then restored and
checksum-verified byte-identical. The `--full` run was not separately
mutation-tested; it recomputes a strict superset of what the default run
recomputes, so this is an untested inference rather than a measurement.

Gates:

```sh
node oversight/oeis/fault-free-tilings/verify-staged.mjs   # 435/470 recomputed, 35 drift-guarded, 0 unbound
node research/fault-free-tilings/verify.mjs                # 32/32 checks
```

## Conventions

- Tilings are counted **labelled** (the rectangle fixed in the plane; a tiling and
  its mirror are two), exactly as A124997 does. The *up-to-symmetry* count is a
  different, also-unrecorded sequence, a natural next computation (Burnside over
  the brute-force enumeration for small boards).
- A "fault" is a **straight** full-span line only; a running bond has offset
  joints, not none, and still counts as fault-free.
- The degenerate strips `1×2` and `2×1` have no interior line and so are vacuously
  fault-free (`FF=1`); this is the one honest edge of the "min side ≥ 5" rule.

## Reproduce

```sh
node oversight/oeis/fault-free-tilings/verify-staged.mjs        # bind the b-files to the engine
node oversight/oeis/fault-free-tilings/verify-staged.mjs --full # slower, recomputes all 470
node research/fault-free-tilings/verify.mjs                     # check the engine itself
```

`derive.mjs` in this directory **rewrites** all five b-files from the engine. It is
a producer, not a check, and running it destroys the evidence that the staged file
matched. Use `verify-staged.mjs` to check; use `derive.mjs` only when deliberately
regenerating.

## The outward path (see request 016)

Per OEIS policy (no AI-authored/automated submissions) the footprint is routed
honestly: (a) a **Zenodo** deposit for a citable DOI (`.zenodo.json` here, no
authorship problem, provenance stated plainly), and (b) an **offer to a human**
(SeqFan or a combinatorialist) to independently check and, if convinced, author the
new array/rows to OEIS as themselves. The classical parts (Graham–Kotzig; the
A124997 diagonal) are cited, not claimed. Only the specific new rows and array
carry the absence claim.
