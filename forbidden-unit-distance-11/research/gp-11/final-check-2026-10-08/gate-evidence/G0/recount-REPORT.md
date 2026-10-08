# GP-11 G0 input freeze and independent recount

Completed 2026-10-01.
Status: G0 PASS for the input freeze only.
No claim about unit-distance embeddability of the B11 graphs is made here.
No git state-changing command was run.
No dependency was installed.

## Files and purpose

- `../data/B11.g6`: the frozen 448,708 canonical graphs.
- `../data/SHA256SUMS`: the frozen file's SHA-256.
- `../data/GENERATION-DOMAIN.md`: the justification for every generation restriction.
- `../data/README.md`: the input definition and reproduction entry point.
- `matcher.c`: GP-10's independent matcher extended to 11 host vertices and 398 patterns.
- `filter.c`: output plumbing around the existing udfilter implementation, retaining TU hits.
- `verify.py`: independent Python witness verification, ordered coverage and exact list comparison.
- `guard.py`: sequential child execution, memory monitoring and scratch limits.
- `run_recount.py`: reproducible compilation, provenance checks, enumerations and recounts.
- `controls.py`: own-rule mutations, restored-output checks and final G0 receipt assembly.
- `chunks.jsonl`: counts, digests and timings for every replayed chunk.
- `receipt.json`: the complete machine-readable result, source hashes, binary hashes and timings.
- `SHA256SUMS`: hashes for the recount sources and evidence files.

## Generation domain and provenance

The generation command is `nauty-geng -Ckq 11 11:24`.
The measured run omitted `-q` to preserve geng's status and count messages; this changes no graph bytes.
`-C` selects the biconnected graphs in the definition of B11.
Their minimum degree is at least 2, so the lower edge limit 11 loses none.
`-k` selects K4-free graphs, and K4 is F10 index 0.
Every 10-vertex deletion of an F10-free 11-vertex graph is F10-free, hence a unit-distance graph by GP-10.
Each such deletion has at most u(10) = 20 edges.
Each edge occurs in 9 of the 11 deletions, so 9m <= 220 and m <= 24.
Thus the restrictions lose no F10-free member of B11.
This argument rests on GP-10's theorem and GP's classification through 9 vertices.

F10 JSON SHA-256: `8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c`.
The first 74 JSON entries agree exactly with `forbidden-74.json`, including vertex labels.
All 398 JSON entries agree, in order up to isomorphism, with `forbidden-398.g6` after default labelg canonicalization.
The canonical 324-entry suffix agrees byte for byte with GP-10's checker-derived `runs/B10-final-2026-09-25/L10.g6`.
It also agrees with that accepted report's minimal list, whose unknown count is zero and conditional flag is false.
The order histogram is 1, 1, 1, 3, 13, 55, 324 for orders 4 through 10.
The independent matcher reads a graph6 encoding generated directly from the JSON labels, preserving the meaning of every F10 index and witness map.

## Anchors and primary census

`nauty-geng -Cu 11` counted **900,969,091** biconnected 11-vertex graphs.
This equals [OEIS A002218(11)](https://oeis.org/A002218/b002218.txt), checked 2026-10-01.
The unrestricted anchor took **365.524299 s wall time**, with **363.86 s** reported by geng.
No unrestricted graph stream was written because `-u` counts only.

| Restricted census | Graphs | Wall time |
|---|---:|---:|
| geng input stream | 68,232,100 | 77.756851 s |
| udfilter, including witness emission | 67,783,392 removed; 448,708 retained | 440.012217 s |
| independent Python witness and coverage replay | 67,783,392 witnesses | 569.823719 s |

The restricted geng status reported 68,232,100 graphs in 74.99 s of CPU time.
The retained class splits into 294,516 `pass` and 154,192 `tu` results.
Every census count matches `research/unit-distance-23/NEXT-ESTIMATES-2026-09-29.md`.
The independent verifier's total including process startup and guard polling was 577.101702 s.
Filter emission plus that guarded replay took 1017.113919 s in serial chunk stages, excluding generation, splitting and canonicalization.

## Independent recount and frozen bytes

The independent matcher contains no udfilter code and does not link to udfilter.
Its search logic is unchanged from GP-10's independent `recount/matcher.c`.
Changes are the bounds MAXN = 11 and MAXPAT = 398, strict graph6 length/character/padding validation, and detection of input read errors.
The search constructs injective maps and requires every pattern edge, while allowing extra host edges.
The reference GP-10 matcher SHA-256 is `fdf6a4d9455bf764718649c4e0f4ccf4bca9031d6b773ad3a7ae2dc705f1ea2a`.

The independent pass read **68,232,100** hosts, removed **67,783,392**, and retained **448,708**.
Its matching wall time was **1587.491871 s**.
It used all 398 patterns, with no dropped index.
Both independently produced raw survivor files were labelled using nauty-labelg 2.8.8 defaults and sorted bytewise without deduplication.
The comparator validates graph6, final newlines and strictly increasing byte order before exact file comparison.
Both producer lists equal the frozen list by exact bytes, not merely by cardinality.
A second default labelg pass over the independent sorted list also returned exactly the original bytes.

| List | Graphs | SHA-256 |
|---|---:|---|
| frozen `../data/B11.g6` | 448,708 | `ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f` |
| primary `primary.sorted.g6` | 448,708 | `ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f` |
| independent `independent.sorted.g6` | 448,708 | `ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f` |

The regenerated lists remain under `/tmp/gp11-freeze/`; their identical bytes are stored only once in the repository.
The original architect list had the same hash, with its earlier generation timed at 363.707452 s.
The present run freshly reproduced the primary list while emitting and checking all removal witnesses.
Primary labelg and sort took 1.047159 s and 0.270927 s.
Independent labelg and sort took 1.096059 s and 0.273702 s.

## Witness replay and coverage

The replay covered **69 chunks**, comprising 68 full million-host chunks and a final 232,100-host chunk.
Every chunk was accepted before its temporary witness data was deleted.
Only the first real chunk was retained for the red controls, alongside the current working chunk.
The program never stored all 67.8 million witnesses.
The raw generator stream was retained separately, using 818,785,200 bytes.

A witness is `host_graph6<TAB>zero_based_F10_index<TAB>comma_separated_map<NEWLINE>`.
Map position i names the host vertex assigned to JSON pattern vertex i.
`verify.py` imports neither producer's code and checks every map's length, injectivity, range and required edges.
It checks graph6 validity for every input host.
It walks the two output subsequences against the generator stream and requires each input to occur in exactly one class.
It rejects missing, duplicate, reordered or extra output hosts, including an input dropped from both classes.
The reconstructed ordered union agrees exactly with the input in each chunk.
Each chunk records input, survivor, witness and union SHA-256 digests, all counts, its global input interval, and its timings.
Witness digests cover the uncompressed TSV bytes.
Timing fields may vary on reproduction; the counts and four data digests must reproduce.

Full input stream SHA-256: `a3450c81997ff983f25902026b2967f3d451a8ff46a87e856f908504882fe791`.
Chunk manifest SHA-256: `2732d1c37aee1477343c87302df63b9a9769f467008f11d113ff55bf69553756`.
Total input coverage: **68,232,100 = 448,708 + 67,783,392**.
Total independently verified witnesses: **67,783,392**.

## Lower-order and non-induced controls

Every B4p through B9p list, and B10 with F9 in force, matched GP-10's frozen canonical bytes and SHA-256.
The input counts also agree with the corresponding A002218 anchors.
The all-F9 controls reproduced GP's printed counts 366 and 2,984.

| Control | Inputs | Survivors | Matcher wall time |
|---|---:|---:|---:|
| B4p | 3 | 3 | 0.005 |
| B5p | 10 | 7 | 0.005 |
| B6p | 56 | 16 | 0.005 |
| B7p | 468 | 60 | 0.005 |
| B8p | 7,123 | 383 | 0.037 |
| B8-F9 | 7,123 | 366 | 0.068 |
| B9p | 194,066 | 3,085 | 0.822 |
| B9-F9 | 194,066 | 2,984 | 1.224 |
| B10 | 9,743,542 | 33,162 | 37.586 |

The positive non-induced control was K2,3 with one additional edge, graph6 `Dfw`.
The matcher returned member index 1, and the independent Python verifier accepted its map.
Because the host and pattern both have five vertices but different edge counts, induced matching would miss this witness.

## Own-rule red controls

Each red control was required to return exit status 1 and its exact stderr message, with empty stdout.
The duplicate map entry kept a parseable integer list of the correct length and failed injectivity.
The coverage control omitted the first real input from its output class, leaving it absent from both classes.
The list control added one edge to a real survivor, canonically relabelled it, and re-sorted while preserving the number of distinct valid graph6 entries.
Its original graph was `J????Kwrfa?` and its replacement was `J?@g?_BenE?`.
It therefore reached list equality, rather than failing graph6 decoding or sorting.

- `REJECT: line 1: map is not injective`
- `REJECT: coverage: input 1 occurs in neither output class`
- `REJECT: list equality: canonical survivor bytes differ`

After **each** red control, the verifier replayed the entire original million-host control chunk and compared the full independent survivor list with the frozen file again.
Each restoration returned exactly the original counts and data digests, and the original full-list comparison result.
This does not mean that all 67.8 million witnesses were redundantly regenerated after every mutation.
The complete replay is recorded in the chunk manifest; the restored real control chunk and full list results are recorded separately for each red.
No required control failed unexpectedly.

## Reproduction and resource limits

Run from the repository root:

```sh
python3 -B research/gp-11/recount/run_recount.py
```

The driver writes generated work to `/tmp/gp11-freeze/` and leaves the frozen repository data unchanged.
It supports `--stage prepare`, `anchor`, `census`, `independent`, `lower`, `controls`, and `finalize` for separately inspecting phases.
Every phase after prepare checks the source and executable hashes recorded by prepare.
The full driver runs every phase in sequence.
The first measured anchor here was launched separately with `guard.py`, with the same command and limits.
The lower-order controls were measured before the main census; the full reproduction driver can run them afterward without affecting any data digest.

Toolchain: nauty	2.8.8+ds-5; cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0; Python 3.12.3.
The C matcher uses the already installed zlib dependency inherited from GP-10.
All heavy commands ran serially, with nice level 15, a 1,500,000,000-byte address-space limit, and single-threaded sorting.
The guard samples available memory every 0.5 s and stops the child process group below 1,572,864 KiB (1.5 GiB).
It also stops if observed scratch use reaches 10,000,000,000 bytes.
Minimum recorded available memory: **3,915,352 KiB**.
Peak recorded scratch use: **918,522,861 bytes**.
No resource stop was triggered.

Disagreements: **none** in the anchors, pattern provenance, census counts, canonical lists, witness replay, coverage, lower-order controls, or expected red-control messages.
