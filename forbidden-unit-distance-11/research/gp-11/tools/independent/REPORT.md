# GP-11 independent checks 1, 2, 3 and 6

Built in `<repo>` for landing at
`research/gp-11/tools/independent/`. The full population has **not** been audited,
checked modulo primes, or searched numerically on this desktop. The VM run is
the coordinator's. All retained desktop arithmetic results are samples.

Land the Python/shell sources, this report, `.gitignore` and `SHA256SUMS`.
`gp11-independent-tools.tar.gz` contains only those deliverables; the 346 MB
`samples/` directory and small `runs/` reports are retained local evidence.
The supplied Python environment has pynauty, numpy, mpmath and networkx.
Production identity checks need only Python 3.12's standard library and run
under `/usr/bin/python3 -S`; neither FLINT nor SymPy is loaded.

`independent_audit.py` verifies coverage, recomputes verdict/type counts, checks
every direct embedding exactly, resolves every super/sub pointer, derives L11
from actual edge deletions, and checks the upward closure of that list against
the refuted set. It writes `report.json`, `L11.g6`, `minimality.jsonl` and
`verdicts.tsv`. `--compare-l11`, `--compare-report` and `--predictions` compare
the derived list, counts and registered forecasts after the official outputs
arrive. A nonzero exit and named `alarms` mean failure. An alarm-bearing list
has `derived_list_valid: false` and must not be used as a result.

Direct refutation verdicts are premises of check 1, just as in GP-10. It does
not claim to be a second complete refutation verifier. Check 6 examines their
identities; the separately assigned blind verifier covers their remaining
mathematical obligations. No overall classification is authorized by these
tools; their reports explicitly say so.

For a refuted G in B11, every vertex deletion has ten vertices and is F10-free
by heredity, so GP-10's theorem decides it as embedded. The tool reconstructs
all eleven vertex deletions and records this reliance on the lower-order
theorem. Every proper subgraph either omits a vertex, or omits an edge while
retaining all vertices, so it lies in one of these deletions. Monotonicity
therefore reduces minimality to **all actual one-edge deletions embedding**.

An edge deletion retains eleven vertices and F10-freeness. If biconnected, it
is in B11 by definition. The tool reconstructs it, computes its own nauty
isomorphism key, and looks up the accepted/declarative status in the input
records. Missing deletions are alarms, never presumed embedded. A refuted
deletion excludes its parent from L11. Unknowns fail this post-result audit;
it deliberately does not issue conditional lists.

If that deletion is not biconnected, its edge-stack blocks, including bridges,
are reconstructed independently by Tarjan's algorithm. Their edge sets must
partition the deletion exactly, and every block must have at most **ten**
vertices. Each inherits F10-freeness from G, embeds by GP-10, and L-block's
finite-rotation argument glues the embeddings without collisions. Isolated
vertices are placed separately. No B10/B10' record lookup is needed: B10'
contains F9-free graphs, including the 324 forbidden ten-vertex graphs, while
these particular blocks are F10-free. The VM command additionally uses
`--forbidden-json` to search every reconstructed block explicitly for all
applicable F10 members through order ten. This redundant check has an
independent bitset matcher and an isomorphism cache. Without that option, the
audit still works from B11 and records alone, under B11's defining F10-free
premise and GP-10's theorem.

The upward-closure check starts from the independently derived minimal list,
adds one edge at a time, and looks up results in B11. Any B11 supergraph of a
minimal member can be reached this way: intermediate graphs retain its
biconnected spanning subgraph and inherit F10-freeness from the final host.
Thus the upward closure must equal the refuted set. This catches mutually
inconsistent positive/negative statuses as well as errors in the recount.

Every direct embedding uses exact rational parsing, common-denominator integer
polynomials, fraction-free pseudo-division by the supplied integer polynomial,
and exact rational interval separation of all vertex pairs. Edge equations
must have identically zero remainder. Bisection preserves a strict sign
change, selecting a common real root; midpoint roots are checked directly.
Outward integer interval Horner bounds separate a coordinate difference from
zero for each pair. No floating tolerance, irreducibility assumption or unique
root assumption is used. This strengthens GP-10's high-precision numerical
embedding audit. The 2,048-subdivision budget can reject a certificate but
cannot produce an unsupported acceptance.

`modp_identities.py` streams every record, examines every refuted certificate,
and evaluates each sparse cofactor identity, each DAG derivation row and final
target, each optional supplied-system polynomial, and each SOS decomposition
at three points modulo each of `2^61-1` and `2^127-1`. Systems, ordered frames,
variable names and ordered saturation variables are regenerated from its local
graph6 decoder. Optional systems are compared with the regenerated system,
never installed as substitute generators. All arithmetic here is Python
integers; standard-library Fraction only parses rational coefficients.

Tree certificates additionally regenerate every four-cycle rhombus relation,
check root/child row spaces and move relations, L2 unit-ratio equalities, and
L3 discriminant/ordered-branch equalities. Since field identities hold modulo
the minimal polynomial, evaluating them at an arbitrary unreduced primitive
element would be wrong. These use integer quotient rings modulo each prime,
complex pairs, and independently implemented elimination. Reduced differences
are evaluated at random points and also checked coefficient by coefficient.
All five move kinds are supported. TU and sub certificates contain no supplied
polynomial identities; they are enumerated as such, never silently counted as
polynomial proofs. Unsupported refutation types fail.

Sturm root counts, real-root isolation/irreducibility, selected-root signs at
L1b/L1c/L3, and TU gadget lemmas are not polynomial identities and remain the
exact verifiers' obligations. A vanishing modular denominator or nonunit
pivot is an explicit failure, not a skipped prime. Random-point evidence is
not an exact proof over Q: the Schwartz-Zippel bound is `(d/p)^3` at a prime
only when the discrepancy remains a nonzero polynomial there and test points
are independent of it. Fixed public seeds/primes are reproducible controls,
not a security guarantee against deliberately crafted prime multiples.

`--jobs` uses a bounded process queue, at most twice the job count for audit
and identity records; decoded certificate bodies are not accumulated. Raw
lines have an 8 MiB ceiling. `--shard i/n` is zero-based, by physical JSONL line
for identities and by sorted L11 index for numerical searches. Record seeds
are hashes of seed, graph6 and type, so worker completion order and shard
assignment do not change the arithmetic points. `merge_shards.py` requires
complete, disjoint shard numbering, common inputs/configuration/source hashes
and passing controls; it rejects missing/duplicate shards.

`embed_redteam.py` uses spanning-tree edge angles, batched Levenberg-Marquardt
and damped 60-digit refinement. All actual edges must have squared-length
residue below `1e-45`, and every pair must remain farther apart than `1e-6`.
Each member gets both an edge-deletion control and an embedded B11 control,
preferably with the same degrees/edge count. The same search and acceptance
rule is used, with the same budget ceiling, and no certificate coordinates
seed the search. A member hit is a `COUNTEREXAMPLE_CANDIDATE` with coordinates
retained for review. Missed controls produce `INCONCLUSIVE_CONTROLS`, exit 2.
A negative search is evidence, not proof.

The adaptations are traceable to these GP-10 templates:

| GP-10 template | GP-11 adaptation |
|---|---|
| `independent_audit.py` | Coverage/isomorphism keys, edge-deletion recount and up-set; exact integer/rational arithmetic replaces mpmath; own decoding/blocks, order-ten premise, bounded workers and explicit block search added. |
| `independent_audit_redteam.py` | Paired originals/mutants and specific alarms; uses a 54-record deletion/pointer closure instead of eight copies of the full stream. |
| `embed_redteam.py` | Tree-angle parameterization, batched LM, high-precision refinement and two controls; local BFS/decoder, damped polishing, jobs, shards and retained candidate coordinates added. |
| `modp_identities.py` | Two specified primes, three points, sparse evaluation and paired mutants; optional systems, final-target counts, all tree moves, bounded workers, shards and stable per-record seeds added. |
| `write_independent_checks.py` | Its refusal to summarize incomplete/failed checks is adapted in `summarize_run.py`; counts and coverage are read from artifacts. |

Specification decisions and source accesses were as follows:

1. GP-11's definition, not a literal global replacement in GP-10, fixes the
   lower-order cutoff at F10/order ten. Every biconnected deletion is looked
   up; every other deletion uses proper blocks. Indexed F10 pointers inside
   B11 would contradict F10-freeness and are rejected. GP-11 FORMAT's separate
   stored/canonical label conventions do not need guessing for these pointers.
2. GP-10's numerical audit calls its certificates exact, but FORMAT explicitly
   specifies polynomial reduction and rational intervals. The new audit uses
   those exact obligations, including reducible minimal-polynomial arrays,
   rather than inferring exactness from shrinking numerical residue.
3. GP-10 FORMAT delegates the inner tree schema without reproducing it.
   `research/unit-distance-22/CONTRACT.md` amendment 9.1 makes the schema in
   `research/unit-distance-22/check/udcheck.py`'s module docstring binding.
   To resolve that gap I read its schema/Lemma-4 docstring, lines 2–52.
   The command was `sed -n '1,155p'`, so it also displayed lines 53–155:
   imports, simple schema/rational parsers and rational polynomial/Sturm
   helpers. Those helpers were not used as implementation templates. No
   proof-verification implementation was read. No other checker/kernel source
   was read, and none was imported or executed. This is the only source-code
   access exception to the written-specification workflow.
4. Tree field vectors in actual sealed witnesses omit trailing zeros (for
   example `[1]` in a quadratic field), whereas E-exact FORMAT explicitly
   requires padding. Tree vectors of length at most the field degree are
   padded locally; E-exact vectors must have exactly that degree. This was
   resolved from the documented coefficient convention and actual witnesses,
   without reading further kernel code.
5. L2's two directed pairs are interpreted by the actual parent graph: exactly
   one must be an existing edge and the other the forced nonedge. Child edges
   must equal the augmented graph, and child A must equal inherited constraints
   plus its new rhombi. L3 children follow the documented +i*d, then -i*d order.
6. Python 3.12's default 4,300-digit conversion ceiling would reject legitimate
   coordinates with 7,820-digit rational strings. The tools remove that digit
   ceiling while retaining the 8 MiB line and per-process memory bounds.
7. PREDICTIONS's final refuted/embedded counts and L11 size can be compared here;
   the residue immediately after automated stages and its eventual embedding
   share cannot be recovered from final records alone. The report retains the
   forecast rows/hash and marks the stage-history quantities unavailable.
8. Ordinary sparse forms explicitly permit zero coefficients. Such terms do
   not add variables to a Sturm target's mathematical support; DAG forms still
   reject zero terms. A converted genuine null identity with a constant Sturm
   target and a zero foreign-variable term passes, and changing that zero to
   one fails with its named cofactor-identity alarm.

Desktop measurements are retained under `runs/final-samples/`, with input
selection/provenance in `samples/manifest.json` and `samples/trees-manifest.json`.
All commands ran at nice 15 with a 1,800-second timeout and 4 GB address-space
limit. Normal sample checks use one worker; the small parallel test uses two.
The judge was active, so timings varied between repetitions.

| Test | Result | Measured wall time |
|---|---|---:|
| Metadata-only stream/offset scan | 448,708 offsets; 443,444 embedded and 5,264 refuted declarations; no population arithmetic verification | 94.602 s; 115.964 s including B11 lookup index, sample closure/extraction |
| First 2,000 records, pointer-closed | 2,401 records: 448 exact embeddings and 1,953 pointers, no alarms | 2.029 s |
| Twenty largest refutations plus representatives and deletion/pointer closure | 756 records: 369 exact embeddings, 359 pointers, 29 refuted; 27 minimal in this closed sample, 2 nonminimal; up-set equal | 30.130 s including explicit F10 block search |
| Block boundary in that sample | 56 non-biconnected edge deletions; 52 order-ten block occurrences; 112 block searches, 23 distinct blocks, 18 distinct order-ten blocks; zero F10 hits | included above |
| Audit red controls | 8/8 named mutations red; untouched sample green before and after | 11.392 s |
| Polynomial/type representatives | All 7 refuted record types covered; polynomial/tree identities pass, TU/sub enumerated; 120 identities per point; 20/20 paired mutation controls red | 37.598 s |
| Six additional actual trees | Every move kind; fields of degrees 1, 2 and 4; 343 identities per point; 2/2 paired mutations red | 4.709 s after L2 guard regression |
| Twenty largest refutations alone | 160,906,726 bytes; 18 real-dag and 2 null-dag; 2,718 identities per point, zero failures | 93.410 s; red controls deliberately NOT RUN in this timing-only pass |
| Numerical pilot | Two independently minimal sample graphs, zero hits at 1,024 starts each; 2/2 minus-edge and 2/2 embedded B11 controls found | 11.146 s including control indexing/hashing; search tasks sum to about 2.3 s |
| Small specification/oracle tests | 10 cases: graph6/blocks against networkx, all 398 positive matcher controls plus VF2 comparisons, exact embeddings/mutations, optional-system and Sturm controls, quotient fields, two-worker trees, L2 and output-collision controls | 8.851 s |

The audit also passed its actual 2,401-record closure with `--jobs 2` in
1.850 s. Two identity shards accepted all six tree samples and merged to 343
identities per point; omitted/duplicated shard controls both failed, while the
unchanged pair passed. These checks are in `runs/audit-jobs2/`,
`runs/tree-shard*.json`, `runs/trees-merged.json` and `runs/shard-controls.json`.
Each report records the source hashes at its own execution; later parser/guard
regressions did not alter the arithmetic paths used for the large-DAG timing.

The first 2,000 raw records contain only 47 direct embeddings; the other 401
direct embeddings above are their required pointer targets. The 27-member
sample file is **not** the complete L11. There are 815 polynomial certificates,
1,099 tree certificates and 3,350 non-polynomial TU/sub certificates in the
metadata census; these are declarations until the VM checks them.

For planning on a 16-core, 62 GB VM with 12 workers, allow roughly **5–20
minutes for the audit**, including its serial metadata/canonical/minimality
work and block cache. The two embedding samples bracket about 170–3,100
serial work-seconds for 37,904 direct certificates before parsing and pointer
overheads; this is an extrapolation, not a measured full replay.

For identities, the largest sample cost about 0.58 wall seconds/MB including
parsing (about 0.51 in arithmetic tasks). Applying that pessimistic byte rate
to the 3.39 GB stream, then dividing independent work over 12 workers while
allowing serial parsing, tree checks and controls, suggests **4–10 minutes**.
The sample's large DAGs bias this estimate upward. All times depend on actual
VM per-core speed and how strongly the desktop judge competed for CPU.

For numerical search, the pilot cost 1.15 task seconds/member for 1,024 member
starts and two 512-start controls. Scaling its member work to 16,384 starts
gives a rough 18-second ceiling/member under similar convergence behavior,
or about **40–160 minutes** for the registered 1,500–6,000-member forecast at
12 workers. More near-misses/polishing and harder controls can increase this;
reserve several hours and first run a 20-member VM pilot at the full budget.

The exact full VM command, after the official files have arrived, is:

```bash
cd <repo>/research/gp-11/tools/independent
bash run_vm.sh \
  <repo> \
  <repo>/b11-endgame/assembly-1 \
  <repo>/b11-endgame/final-outputs \
  "$PWD/runs/vm-20261007" 12
```

`run_vm.sh` requires a new output directory. It runs audit with `--jobs 12`,
explicit order-ten block searches and both official comparisons, then the
paired audit controls, identities with `--jobs 12 --points 3`, numerical
search with `--jobs 12 --starts 2048 --rounds 8 --iters 120`, and the summary
coverage checks. It fixes BLAS threads to one. The 4 GB bound is per process,
compatible with twelve workers on the 62 GB VM. Its VM timeout defaults to
86,400 seconds (`GP11_VM_TIMEOUT`), rather than the desktop's 1,800 seconds.
Interpreter paths can be changed with `GP11_PY` and `GP11_INTEGER_PY`.

For a numerical VM pilot before that last long stage:

```bash
nice -n 15 timeout 1800 prlimit --as=4000000000 \
  <repo>/pyenv-gp10/bin/python -B embed_redteam.py \
  runs/vm-20261007/audit/L11.g6 \
  <repo>/research/gp-11/data/B11.g6 \
  <repo>/b11-endgame/assembly-1/records.jsonl \
  runs/vm-pilot20.json --jobs 12 --limit 20 --starts 2048 --rounds 8
```

For independent identity shards, invoke each `i` in `0..11` with its own
output/detail file (or use two shards with six jobs each to use twelve cores):

```bash
nice -n 15 timeout 86400 prlimit --as=4000000000 \
  /usr/bin/python3 -S -B modp_identities.py \
  <repo>/b11-endgame/assembly-1/records.jsonl \
  runs/modp-0-of-12.json --jobs 1 --shard 0/12 --points 3 \
  --details runs/modp-0-of-12.jsonl
/usr/bin/python3 -S -B merge_shards.py modp runs/modp-merged.json \
  runs/modp-*-of-12.json
```

Every identity shard streams the input to select physical lines, so twelve
separate shards repeat I/O; one `--jobs 12` invocation is preferable on one VM.
Concatenate the completed shard detail JSONLs for the summary's set-coverage
check. Numerical shards use the same syntax; `merge_shards.py embed` verifies
complete L11 coverage and shared byte hashes before merging their rows.

To reproduce desktop samples, use `prepare_samples.py B11.g6 records.jsonl
SAMPLES` and `select_tree_samples.py records.jsonl SAMPLES`, followed by
`bash benchmark_samples.sh SAMPLES forbidden-398.json NEW_OUTDIR`. These
helpers perform metadata scans, not full certificate checks. The metadata
scan is needed to choose the largest twenty and close pointer/deletion
dependencies; it does not import producers or checkers.

The independence boundary is explicit: graph6 decoding, block reconstruction,
matching, integer/rational/quotient arithmetic and numerical search are local.
Nauty remains a shared dependency for isomorphism keys; its canonical labelling
does not constitute an independently reimplemented nauty algorithm. These
checks do not re-enumerate B11, re-prove GP-10, or validate the written geometric
lemmas themselves. Those remain the programme's G0/lower-order/review premises.
