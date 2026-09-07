# Certificate ledger for the (15,32) existence SAT (t3(15) decision)

Kept by the coordinator claude-reaching-noether-7e1c. One row per cube; a cube counts as
refuted only when every column is filled and consistent. The mathematics behind the chain
(Lemma 1 reduction, Lemmas 3, 4, 7, 8 symmetry break, encoding soundness) was attacked by a
five-referee panel on 2026-09-05 and held; the panel's serious findings were all about this
ledger, which did not exist before it.

## What each column means

- **CNF sha256**: the sha256 of the file the solver refuted, as pushed by the worker
  (`scratch/exist-15-32-c<k>/SHA256SUMS.cnf`, plus the file itself zstd-compressed), compared
  with the sha256 of the same cube regenerated from the frozen generator by an unrelated cloud
  worker (`claude/reaching-noether-cloud-cnf-audit`, commit 584fbe761, python 3.11.15,
  python-sat 1.9.dev15) and, for cube 0, by this box (python 3.12, same pysat).
- **decode**: `cnfcheck.py <cnf> --cube k` on the refuted file: unit clauses are exactly the 15
  anchors, B true on the row of point 0 and on cube k's row of point 1, B false on the other
  triples through 0 or 1, one prefix-equal start per non-identity element of G2, and the
  lex-leader clauses accept G2-orbit minima and reject non-minima (25 random trials).
- **solver / checker**: cadical 1.7.3 (Ubuntu package 1.7.4-1, binary sha256 7b73df0a...) and
  drat-trim built from marijnheule/drat-trim at commit 2e3b2dc0 (binary sha256 92f0aa95...),
  as recorded in each worker's VERSIONS.txt. The coordinator's LOCAL check of cube 0 (3432 s)
  used a different build: ~/tools/sat/drat-trim/drat-trim, sha256 993de410..., compiled from the
  December 2017 drat-trim.c shipped in CaDiCaL's test directory (TIMEOUT 20000), so cube 0's two
  checks are by two different checker builds (referee panel, certificate lens, 10:00Z).
- **verdict / proof**: the JSONL line with verdict UNSAT and proof_verified true, the sha256
  of the DRAT proof, and the checker's `s VERIFIED` line. The proofs (0.7 to several GB) stay
  on the workers' disks; they are regenerable from the CNF and solver version.

## Ledger (2026-09-05, updated as results land)

| cube | orbit | stabiliser | CNF sha256 (refuted = regenerated?) | decode | verdict | proof | checked |
|---|---|---|---|---|---|---|---|
| 0 | 120 | 384 | 0e6352aa... local original = local regen = cloud regen = worker file: yes | PASS (referee c0check.py; cnfcheck on regen and on the worker file, 01:45Z) | UNSAT twice: local (cadical, 3494 s) and cloud (cadical, 26 min) | 696,022,996 B; cloud proof sha256 9a09e2c3...; 7,337,762 lemmas, 1,713,366 in core | drat-trim `s VERIFIED` locally (3432 s) and in the cloud (2353 s, log scratch/drat-trim-c0.log on the c0 branch; the cloud JSON is worker-assembled after the sandbox restart killed exist.py mid-check, and says so) |
| 1 | 1440 | 32 | 8c33bbfe... worker = cloud regen = kissat worker file: yes | PASS (regen, worker file, kissat worker file) | UNSAT twice, both proofs verified: cadical 1.7.3 (solve 4481 s; `scratch/exist-15-32-c1/cubes-15-32-depth1.jsonl` on `...-orchard-c1-xlr95d`, checkout 0a23b5f2) and kissat 4.0.4 (solve 1924 s; `scratch/exist-15-32-c1-kissat/` on `...-orchard-c1-kissat`) | cadical proof 2,455,730,413 B sha256 958c8adf... (6,101,031 of 10,713,561 lemmas in core, 453,778,782 resolution steps); kissat proof 933,086,904 B sha256 6c4239bf... | drat-trim 2e3b2dc0 (binary 92f0aa95...) `s VERIFIED` on both: 7628 s (cadical proof) and 3520 s (kissat proof, -t 10000000, exact-line parser, log committed) |
| 2 | 640 | 72 | 9b26b0e5... worker = cloud regen = kissat worker file: yes | PASS (regen, worker file, kissat worker file) | UNSAT twice, both proofs verified: cadical 1.7.3 run 2 (solve 5065 s; JSONL `scratch/exist-15-32-c2/cubes-15-32-depth1.jsonl` on `...-orchard-c2-2mhdop`) and kissat 4.0.4 (solve 1810 s; `scratch/exist-15-32-c2-kissat/` on `...-orchard-c2-kissat`) | cadical proof 2,010,793,854 B sha256 137d0fab... (5,896,422 of 9,708,465 lemmas in core, 422,228,499 resolution steps); kissat proof 770,721,286 B sha256 94c7a88d... (5,438,780 of 8,997,293 lemmas in core, 41,703 RAT lemmas) | drat-trim 2e3b2dc0 (binary 92f0aa95...) `s VERIFIED` on both: 7766 s (cadical proof) and 3366 s (kissat proof, with -t 10000000 and the exact-line parser) |
| 3 | 3840 | 12 | 3ce6b8b9... cloud regen = kissat worker file: yes (02:32Z); the kissat worker's result record carries cnf_sha256 3ce6b8b9e17d4ceadcca205612c0692a85374c53328aab343eb0951970a49417, the audited value; the cadical worker c3-ikl3d9 has pushed no CNF hash yet | PASS (regen and kissat worker file) | solved by BOTH solvers: kissat 4.0.4 UNSAT in 7198 s (proof 3,716,998,324 B, sha256 a4bf1e902a73134bfdd2bc75b84d00549b9a1fab2c3f84588317f814ba721983); cadical 1.7.3 run 2 UNSAT in ~5 h (proof 8,980,523,963 B, drat-trim since ~06:25Z) | **VERIFIED (kissat proof)**: drat-trim 2e3b2dc0 `s VERIFIED`, exit 0, 16289.1 s, 32,951,340 lemmas / 21,318,798 in core, peak RSS ~4.8 GB, on the cloud worker claude/reaching-noether-cloud-orchard-c3-kissat (commit 111a7884a, 09:05Z; SHA256SUMS and VERSIONS.txt in chiro/scratch/exist-15-32-c3-kissat/) | **depth-2 certification COMPLETE (14:45Z)**: Lemma 7' splits cube 3 into 5393 children by the row of point 2 (G2-orbits, stabiliser orders {1: 4638, 2: 674, 3: 2, 4: 64, 6: 9, 12: 6}, recounted without the generator's code in controls/orbits_independent.py); four cloud workers solved each child with cadical and checked each DRAT with drat-trim; `aggregate-depth2.py` COVERAGE PASS: every child exactly once, all UNSAT, all verified (chiro/results/depth2-c3-aggregate.txt; a dropped child and a duplicated child both make it FAIL). The cadical proof of the undivided cube is still in drat-trim; the LRAT+cake_lpr certificate is in progress. |

Decode checks were run by the audit worker (`claude/reaching-noether-cloud-cnf-audit`, commits
"orchard CNF audit: decode checks" 01:45Z and "cube 3 closed, all four cube CNFs audited"
02:44Z): cnfcheck.py on each regenerated CNF and on each worker-pushed CNF (six worker files
across five branches), all PASS with |G2| = 384, 32, 72, 12 and 25/25 lex trials each, and every
worker file byte-identical to the regenerated one. Cube 3's audited file is the one the kissat
replication refutes; if cube 3's verdict is to rest on the cadical worker's proof instead, that
worker must first push its CNF hash. The audit says nothing about UNSAT itself: cubes 0, 1 and 2
have two verified proofs each at 06:50Z, and at 09:05Z cube 3's kissat proof was verified by
drat-trim on the audited CNF (the worker's result record carries the audited cnf_sha256). Every
cube of the sound depth-1 split therefore has at least one verified refutation: the existence
CNF for (15,32) is UNSAT with checked certificates, and with Section 1 of CONTRACT.md that is
t3(15) = 31. Cube 3's second certification (the cadical proof, still in drat-trim) and the
depth-2 fleet (5393 children, a third, structurally different certification) are in progress.

## Controls added after the 10:00Z referee panel

- `controls/pegg_e2e.py` (PASS, log committed): the chirotope of Pegg's real (15,31)
  configuration, computed from exact coordinates, pushed through the identical Lemma 3/4/7/8
  machinery, falsifies no clause of the monolithic (15,31) CNF or of its cube-2 CNF; one flipped
  sign falsifies 370. This is the control that tests the direction the real theorem needs (an
  over-constrained encoder would fail it and pass every solver-found-model control).
- `controls/orbits_independent.py` (PASS, 28 of 28 checks, 5 s; log committed): without importing
  exist.py, chirosat.py or cnfcheck.py, rebuilds G1 as (pair permutation, within-pair swaps) and
  recomputes 6040 row-1 configurations (brute force and inclusion-exclusion), exactly 4 orbits of
  sizes 120/1440/640/3840 with stabilisers 384/32/72/12 (cycle types 2+2+2, 4+2, 3+3, 6),
  lex-min representatives IDENTICAL to exist.py's four cube representatives, and for cube 3 the
  5393 Lemma 7' children with stabiliser orders {1: 4638, 2: 674, 3: 2, 4: 64, 6: 9, 12: 6},
  confirmed by Burnside (sum of fixed points 64716 = 12 x 5393). Negative controls inside the
  script (wrong group, missing exclusion, proper subgroup, wrong stabiliser) all go red, and two
  mutated copies of the script exit 1. This answers the panel's note that cnfcheck.py's
  "independent recomputation" imported the generator's own group code.

## Verified-checker certificates (LRAT + cake_lpr), added after the 10:00Z panel

Fresh cloud workers (branches claude/reaching-noether-cloud-orchard-lrat-c<k>) regenerate each
cube CNF, solve with kissat 4.0.4, run drat-trim 2e3b2dc0 with -L through a committed wrapper
(so exist.py's own verification pass emits the LRAT), then check the LRAT with cake_lpr (CakeML,
git a36874a8, binary sha256 1822ca1e..., verified core cake_lpr.S sha256 2f3af32d... equal to the
repo's checked-in value). Each worker also runs a red control: a copy of the LRAT with one hint
line removed, which cake_lpr rejects (log committed).

| cube | CNF sha256 = audited | kissat | DRAT bytes, sha256 | drat-trim -L | LRAT bytes, sha256 | cake_lpr |
|---|---|---|---|---|---|---|
| 0 | 0e6352aa... yes | UNSAT, 803 s | 278,912,545, 13f20d43... | `s VERIFIED`, exit 0, 1530 s | 1,074,689,995, 454b29cd... | **`s VERIFIED UNSAT`, exit 0, 63 s** (commit 456944608, 10:50Z) |
| 1 | 8c33bbfe... yes | UNSAT, 2628 s | 933,086,904, 6c4239bf... (byte-identical to the c1-kissat worker's proof of 06:55Z) | `s VERIFIED`, exit 0, 4374 s | 4,097,460,135, 2cccfcd7... | **`s VERIFIED UNSAT`, exit 0** (commit c9a9b1b2b, 12:20Z; artefacts in chiro/results-lrat-c1/) |
| 2 | 9b26b0e5... yes | UNSAT, 2362 s | 770,721,286, 94c7a88d... (byte-identical to the c2-kissat worker's proof) | `s VERIFIED`, exit 0, 4408 s | c3345127... | **`s VERIFIED UNSAT`, exit 0** (commit de5e2cfd1, 12:22Z; six red controls in chiro/scratch/smoke/) |
| 3 | 3ce6b8b9... yes | UNSAT, solved 11:5xZ; the fresh DRAT proof's sha256 is a4bf1e90..., byte-identical to the c3-kissat worker's proof of 04:25Z (kissat 4.0.4 is bit-deterministic across these VMs) | 3,716,998,324, a4bf1e90... | `s VERIFIED`, exit 0, 13,462 s (log in chiro/lrat-c3/) | 16,063,366,058, fc433d15... | **`s VERIFIED UNSAT`, exit 0** (commit 3ecafc327, 15:54Z; record mirrored in chiro/lrat-c3/; the worker's disk guard unlinked the DRAT after the check, see INCIDENT-proof-unlinked.md: the JSONL there is worker-assembled) |

## Known hazards (from the referee panel) and their status

1. drat-trim's compiled limit (TIMEOUT 40000 s at 2e3b2dc0; 20000 s in the 2017 CaDiCaL-shipped copy) prints `s TIMEOUT` with exit 0 and exist.py (pre-2815b1e5d)
   then exits 2 with no record: the check-in routines carry a `-t 10000000` rerun instruction;
   run_drat_trim now passes `-t` and rejects TIMEOUT / NOT VERIFIED explicitly (commit 2815b1e5d).
2. The cloud sandbox kills background processes about five minutes after a session idles
   (observed on cubes 2 and 3 at ~01:00Z after the five-hour rate limit blocked their keep-alive
   turns). cadical has no checkpointing, so a killed cube restarts from zero. Hourly check-in
   routines restart dead runs; a depth-2 cube split (8922 short cubes) is the fallback design if
   the depth-1 cubes cannot be kept alive for their full solve plus check.
3. The verdict parser accepted the substring VERIFIED: fixed (exact line) in 2815b1e5d; the
   workers run the earlier parser, which is sound against the real drat-trim binary (exit 1 on
   NOT VERIFIED) whose sha256 they record.
4. The depth-2 cube code landed at 04:50Z (codex, brief `chiro/TASK-DEPTH2.md`; Lemma 7' and the
   controls in REPORT-EXIST.md). Regression guard run by the coordinator afterwards: all four
   (15,32) depth-1 cube CNFs regenerated with the edited exist.py hash exactly to the audited
   values 0e6352aa..., 8c33bbfe..., 9b26b0e5..., 3ce6b8b9..., so the certificate is untouched.

## Cube 3, cadical proof: verified (2026-09-06 06:01Z)

The 8.98 GB cadical proof of cube 3 (solve 18,004 s) hit drat-trim's compiled 40,000 s limit on the first pass (hazard 1); the recheck with `-t 10000000` returned `s VERIFIED` after 45,331.519 s (19,612,400 of 35,470,012 lemmas in core, 1,451,495,880 resolution steps, 0 RAT). Log and status record mirrored in `chiro/c3-cadical/`. Every redundancy item in this ledger is now complete: each cube has two solver-independent DRAT refutations checked by drat-trim, an LRAT accepted by cake_lpr, and cube 3 additionally its 5393-child depth-2 certification.

## Independent check of the orbit decomposition (2026-09-06)

GAP 4.12.1, from the definition, no input from exist.py: (15,32) four orbits 120/1440/640/3840 with the fixed representatives a transversal and every cube lex-leader group equal to the orbit stabiliser element for element; (14,27) likewise with seven orbits. Scripts, logs and a hand count in `independent/`.
