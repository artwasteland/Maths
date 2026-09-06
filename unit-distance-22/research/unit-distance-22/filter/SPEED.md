# udfilter speed and byte-identity report

Date: 2026-09-05  
Compiler: `cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`  
Build flags: `-std=c17 -O3 -Wall -Wextra -Wpedantic`  
Reference binary SHA-256: `3d1463da1cef416e566e062e2dbafac4161c6b61b68e7591e3b9ec0f30a9fa08`

All timed corpus runs use `nice -n 10`, one streaming `udfilter` process, and output files under `scratch/`. Times below are elapsed wall-clock seconds from `/usr/bin/time`. Runs are sequential unless explicitly stated.

## Reference outputs before source changes

| Corpus | Graphs | Reference output | SHA-256 | Wall time (s) | Graphs/s |
|---|---:|---|---|---:|---:|
| `12-24.reach.g6` | 1,034 | `scratch/reference-12-24.jsonl` | `424888f938cc51b4385dfaeffb9ec955d8efa61cbd8dd6e16e9acad742143a76` | 8.26 | 125.18 |
| `12-22.reach.g6` | 237,710 | `scratch/reference-12-22.jsonl` | `6529564304e801d57915a8eca58c7f7e569428e66dfdc5e6044e47dee84662f5` | 685.44 | 346.79 |
| `sample-13-23-unpruned.g6` | 20,000 | `scratch/reference-13-23.jsonl` | `ccb98e1bfde26eda33aae228391085a82c092557e461a810127af12bc4f8ae93` | 67.76 | 295.16 |
| `18-46.g6` | 84 | `scratch/reference-18-46.jsonl` | `4ee432255ac0ab3ff77136e63349fe2ce574a59e83ab98b3363c234b730e9694` | 3.86 | 21.76 |
| `17-43.g6` | 15 | `scratch/reference-17-43.jsonl` | `84814d583f5464020e4a3f7171fb6b23864d61bd8c45c685fdb5169c3150f594` | 0.66 | 22.73 |
| self-check fixtures | 143 | `scratch/reference-selfcheck-fixtures.jsonl` | `36ece39e978eb285d165a0a2eaa29383c7ceaf6d9a81aae93ac9d479c6e73d06` | 2.58 | 55.43 |

The fixture stream is `scratch/selfcheck-fixtures.g6`, SHA-256 `f2bec785f4fcd776aa7301d5a012e868af81e0d16fcaa1626fed0444016bcff2`. It follows `selfcheck.py` exactly: 56 known graphs, 74 decorated forbidden patterns, the removed-pair and present-pair form of all 6 TU gadgets, then the repeated gadget used for the corrupt-witness check. Its reference verdict counts are 74 `forbidden`, 9 `tu`, and 60 `pass`.

Reference verdict counts on `12-22.reach.g6` are 153,154 `tu` and 84,556 `pass`. Reference verdict counts on `sample-13-23-unpruned.g6` are 11,727 `tu` and 8,273 `pass`.

## Profile

`perf stat` was allowed to report elapsed and CPU time, but both hardware and software event sampling were denied because the host has `perf_event_paranoid=4`. The failed `perf record` diagnostic is retained in the command log. I therefore built a separate `-O3 -pg -fno-inline` binary under `scratch/`, ran it with `nice -n 10` on `12-24.reach.g6`, and first confirmed its complete JSON output with `cmp` against the reference.

The gprof run took 10.59 s. It made 79,068 `find_pattern` calls, 5,577,714 total `search` calls, and 73,090,013 `candidates` calls. Its flat profile attributed 61.30% self time to `candidates`, 22.45% to the compiler's `__popcountdi2`, 8.67% to `search`, and 7.43% to `edge`. Candidate construction plus its called `edge` work therefore accounted for about 68.7% directly, while repeated population counts were another major cost. Input decoding, JSON output, and database loading were below the sampling resolution.

This points to two safe first changes: reject impossible patterns from one per-host degree and edge summary, and replace repeated host-degree scans inside `candidates` with precomputed degree-eligible masks. Neither change alters pattern order, dynamic pattern-vertex selection, host-vertex enumeration, or the successful mapping search.

## Changes and regression checks

### Change 1: shared host summary and degree-eligible masks

The filter now computes host degrees and edge count once per graph. It rejects a pattern before search when the pattern has too many vertices, too many edges, or more vertices of degree at least `d` than the host for any `d`. For patterns that reach search, it builds each pattern vertex's host-degree-eligible mask once. Candidate construction starts from that mask and intersects only the adjacency masks of already mapped pattern neighbours. The original pattern order, minimum-candidate tie order, ascending host candidate order, forward-pruning semantics, and final witness search are unchanged.

Every specified corpus was rebuilt, rerun, hashed, and compared with `cmp` after this change. All comparisons succeeded.

| Corpus | Reference (s) | Change 1 (s) | Change 1 graphs/s | Speedup | Output SHA-256 |
|---|---:|---:|---:|---:|---|
| `12-24.reach.g6` | 8.26 | 1.14 | 907.02 | 7.25x | `424888f938cc51b4385dfaeffb9ec955d8efa61cbd8dd6e16e9acad742143a76` |
| `12-22.reach.g6` | 685.44 | 93.85 | 2,532.87 | 7.30x | `6529564304e801d57915a8eca58c7f7e569428e66dfdc5e6044e47dee84662f5` |
| `sample-13-23-unpruned.g6` | 67.76 | 9.22 | 2,169.20 | 7.35x | `ccb98e1bfde26eda33aae228391085a82c092557e461a810127af12bc4f8ae93` |
| `18-46.g6` | 3.86 | 0.47 | 178.72 | 8.21x | `4ee432255ac0ab3ff77136e63349fe2ce574a59e83ab98b3363c234b730e9694` |
| `17-43.g6` | 0.66 | 0.09 | 166.67 | 7.33x | `84814d583f5464020e4a3f7171fb6b23864d61bd8c45c685fdb5169c3150f594` |
| self-check fixtures | 2.58 | 0.33 | 433.33 | 7.82x | `36ece39e978eb285d165a0a2eaa29383c7ceaf6d9a81aae93ac9d479c6e73d06` |

### Change 2: incremental candidate intersections

Each recursion level now keeps the same candidate adjacency intersection that the old `candidates` function would have reconstructed from every mapped pattern neighbour. Mapping a pattern vertex intersects only its unmapped pattern neighbours with the selected host adjacency mask. Backtracking restores those masks. The selected vertex's already computed mask is also reused instead of immediately recomputing it. Candidate sets, population counts used for selection, tie order, forward failures, and ascending host enumeration are unchanged.

Every specified corpus was rebuilt, rerun, hashed, and compared with `cmp` after this change. All comparisons succeeded.

| Corpus | Reference (s) | Change 2 (s) | Change 2 graphs/s | Speedup | Output SHA-256 |
|---|---:|---:|---:|---:|---|
| `12-24.reach.g6` | 8.26 | 0.55 | 1,880.00 | 15.02x | `424888f938cc51b4385dfaeffb9ec955d8efa61cbd8dd6e16e9acad742143a76` |
| `12-22.reach.g6` | 685.44 | 66.31 | 3,584.53 | 10.34x | `6529564304e801d57915a8eca58c7f7e569428e66dfdc5e6044e47dee84662f5` |
| `sample-13-23-unpruned.g6` | 67.76 | 4.48 | 4,464.29 | 15.13x | `ccb98e1bfde26eda33aae228391085a82c092557e461a810127af12bc4f8ae93` |
| `18-46.g6` | 3.86 | 0.24 | 350.00 | 16.08x | `4ee432255ac0ab3ff77136e63349fe2ce574a59e83ab98b3363c234b730e9694` |
| `17-43.g6` | 0.66 | 0.04 | 375.00 | 16.50x | `84814d583f5464020e4a3f7171fb6b23864d61bd8c45c685fdb5169c3150f594` |
| self-check fixtures | 2.58 | 0.12 | 1,191.67 | 21.50x | `36ece39e978eb285d165a0a2eaa29383c7ceaf6d9a81aae93ac9d479c6e73d06` |

### Rejected experiment: neighbour-degree sums

I tested narrowing each pattern vertex's initial candidate mask by the necessary neighbour-degree-sum inequality suggested in the brief. Although the inequality removed only impossible vertex assignments, it changed the candidate counts used by minimum-candidate branching. On target line 10,070, the original TU map `[7,11,8,12,9,5]` changed to the different valid map `[9,5,8,12,7,11]`. The output SHA-256 became `8fce61fb64eba3c59c44837ad5c5fc32e609a709772f62f552b2596ce96445eb`, and `cmp` reported:

```text
scratch/reference-13-23.jsonl scratch/change3-13-23.jsonl differ: byte 731253, line 10070
```

It was also slower, 4.67 s versus 4.48 s. The experiment was removed completely. `cmp` confirmed that both source files exactly matched their saved change-2 copies, then the restored build reproduced the reference target hash in 4.46 s.

### Change 3: ascending set-bit candidate iteration

The host-candidate loop now extracts the least significant set bit from the chosen mask instead of testing every host vertex. This visits precisely the same candidate labels in ascending order, so it cannot change the first witness.

Every specified corpus was rebuilt, rerun, hashed, and compared with `cmp` after this change. All comparisons succeeded.

| Corpus | Reference (s) | Final (s) | Final graphs/s | Speedup | Output SHA-256 |
|---|---:|---:|---:|---:|---|
| `12-24.reach.g6` | 8.26 | 0.37 | 2,794.59 | 22.32x | `424888f938cc51b4385dfaeffb9ec955d8efa61cbd8dd6e16e9acad742143a76` |
| `12-22.reach.g6` | 685.44 | 65.00 | 3,657.08 | 10.55x | `6529564304e801d57915a8eca58c7f7e569428e66dfdc5e6044e47dee84662f5` |
| `sample-13-23-unpruned.g6` | 67.76 | 3.38 | 5,917.16 | 20.05x | `ccb98e1bfde26eda33aae228391085a82c092557e461a810127af12bc4f8ae93` |
| `18-46.g6` | 3.86 | 0.15 | 560.00 | 25.73x | `4ee432255ac0ab3ff77136e63349fe2ce574a59e83ab98b3363c234b730e9694` |
| `17-43.g6` | 0.66 | 0.02 | 750.00 | 33.00x | `84814d583f5464020e4a3f7171fb6b23864d61bd8c45c685fdb5169c3150f594` |
| self-check fixtures | 2.58 | 0.07 | 2,042.86 | 36.86x | `36ece39e978eb285d165a0a2eaa29383c7ceaf6d9a81aae93ac9d479c6e73d06` |

## Final comparison

The final binary SHA-256 is `d4ccae3ff45dcd2d45a64087bebb9519e901110c07fabd1661995b148cee600a`. The final source hashes are `29de35b6110ad0d41dc1456a1af0906ccd0b1ae893f903467e59f1e4580d0c16` for `udfilter.c`, `ed7a570a33e748687fb3bf9caaffe2732d18e1492b290502a8df0a44fa51f1db` for `udfilter.h`, and the unchanged `d580e9c3b2eba509bd2bc2b94d34113d26a0f4a453e0993ca174bcf98be2c02c` for `udfilter-cli.c`.

A final explicit `cmp` of every reference output against its final output printed `final_cmp_passed=6`. All six output hashes are identical to their reference hashes. The target `sample-13-23-unpruned.g6` improved from 67.76 s and 295.16 graphs/s to 3.38 s and 5,917.16 graphs/s, a measured 20.05x speedup.

The implementation remains single-threaded and streaming. Per-graph and per-search storage consists only of fixed-size arrays bounded by 22 host vertices and 15 pattern vertices.

## Controls

### Final self-check

`nice -n 10 ./selfcheck.py` exited 0. Its output was:

```text
known_56_pass=56
forbidden_planted_verified=74
tu_pair_removed_verified=6
tu_pair_present_results=[[0,"pass",null],[1,"pass",null],[2,"pass",null],[3,"tu",4],[4,"tu",0],[5,"pass",null]]
corrupt_witness_rejected=1
```

The final run took 2.83 s including its many subprocess launches and independent verifier calls.

### Every corpus witness verified

The harness `scratch/verify-all.py` invokes `verify-witness.py`'s `main()` on every non-pass record in all six final outputs. It exited 0:

```text
change3-bits-12-24.jsonl: records=1034 witnesses_verified=784
change3-bits-12-22.jsonl: records=237710 witnesses_verified=153154
change3-bits-13-23.jsonl: records=20000 witnesses_verified=11727
change3-bits-18-46.jsonl: records=84 witnesses_verified=46
change3-bits-17-43.jsonl: records=15 witnesses_verified=7
change3-bits-selfcheck-fixtures.jsonl: records=143 witnesses_verified=83
total_records=258986 total_witnesses_verified=165801
```

This took 22.24 s. An explicitly corrupted injectivity map made the verifier go red with exit status 1 and no stdout or stderr, which is the verifier's defined rejection behavior:

```text
corrupt_verify_exit=1
corrupt_verify_stdout=''
corrupt_verify_stderr=''
```

### Dropped forbidden-pattern mutation

The production `../data/forbidden-74.json` was never edited and its final SHA-256 remains `ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a`. The mutation copy `scratch/mutation-forbidden-74.json` drops distinct pattern 73 by replacing its slot with a duplicate of pattern 72. Keeping 74 array entries is necessary because the production loader intentionally rejects any other count. Running the final filter against the copied database changed fixture line 130 from `forbidden` to `pass`. The deliberately failing comparison was:

```text
mutation_cmp_exit=1
scratch/reference-selfcheck-fixtures.jsonl scratch/mutation-selfcheck-fixtures.jsonl differ: byte 11428, line 130
reference_line_130={"g6":"UCQbRiY???????????G??????????G?????????G","verdict":"forbidden","witness":{"index":73,"map":[0,1,2,3,4,5,6,7,8]}}
mutation_line_130={"g6":"UCQbRiY???????????G??????????G?????????G","verdict":"pass"}
```

Verdict counts changed from 74 `forbidden`, 60 `pass`, and 9 `tu` to 73 `forbidden`, 61 `pass`, and 9 `tu`.

For an additional top-level red check, a scratch-only binary that skipped forbidden index 73 was used by a scratch copy of `selfcheck.py`. It exited 1 as required:

```text
known_56_pass=56
Traceback (most recent call last):
  File "scratch/selfcheck-drop73.py", line 85, in <module>
    raise SystemExit(main())
  File "scratch/selfcheck-drop73.py", line 54, in main
    assert cert["verdict"] == "forbidden"
AssertionError
```

The production binary was rebuilt from the unmutated source, the original database was used, the final self-check passed, and all six final comparisons passed.

## WHAT WORKS

- One host degree histogram, degree masks, and edge count shared across all 80 patterns remove repeated host work and reject impossible patterns before recursion.
- Cached candidate intersections remove repeated reconstruction without changing a candidate set or branch decision.
- Least-significant-set-bit iteration avoids scanning absent host candidates while preserving ascending host-label order.
- Pattern order, dynamic pattern-vertex tie behavior, and the first successful map are preserved. All six corpora are byte-identical.
- The target sample is 20.05x faster, and the large 12-22 corpus is 10.55x faster.
- The filter remains single-threaded, streaming, and constant-memory per graph.

## WHAT DOES NOT

- `perf` event sampling is unavailable on this host because `perf_event_paranoid=4`; gprof supplied the actionable profile instead.
- Applying neighbour-degree sums directly to candidate masks does not satisfy the byte-output contract. It changed a valid first TU witness by changing the dynamic minimum-candidate order, and it was slower on the target sample. The code was removed.
- Candidate-order heuristics cannot be added to the witness-producing search merely because verdicts remain correct. The rejected experiment demonstrated that valid witness bytes can change.

## UNCERTAIN

- The smallest 15, 84, and 143 graph timings have only centisecond timer resolution and are sensitive to shared-host scheduling. The 20,000 and 237,710 graph measurements are the meaningful rates.
- Speedup on the projected frontier depends on its degree distributions and pass/TU mix. The supplied 13-23 sample is the best available proxy and is the primary reported result.
- Byte identity has been demonstrated on all 258,986 required records and 165,801 independently checked witnesses. It is not a formal proof over every possible graph on at most 22 vertices.
