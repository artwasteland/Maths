# Pruning the F-free DAG: lemmas, certificate, and what a stranger checks

Written by the pruning builder on 2026-09-05 for CONTRACT Section 3 (hereditary use of the TU
rule, "a builder using this must state the exact lemma and its proof"). Code: `enum/prune.py`
(hereditary pruning of one level file) and `enum/run-dag2.py` (the DAG runner with `--reach`
and `--prune`). `enum/run-dag.py` is untouched.

## 0. Setting and notation

The generator builds the DAG of CONTRACT Section 3: a child G on n+1 vertices is accepted
from the parent H = G - v only if v lies in the Aut(G)-orbit of the canonically first
minimum-degree vertex of G (`udenum.c`, `child_canonical_accept`: it computes delta(G) over
all n+1 vertices, locates the first vertex of degree delta(G) in nauty's canonical order, and
rejects the child unless the new vertex is in that vertex's orbit). Consequently every F-free
graph G has exactly one accepted construction path G = G_n, G_{n-1}, ..., down to the seeds,
with G_{j-1} = G_j - v_j for a minimum-degree vertex v_j of G_j. Every G_j on the path is an
INDUCED subgraph of G (vertex deletion only).

Target: (N, M) with M at or above the proved upper bound on u(N). For (22, 61): u(22) <= 61 is
AMP Theorem 1(b). For the controls (17, 43) and (18, 46): u(17) = 43 and u(18) = 46 are AMP
Theorem 1(a). `prune.py` refuses to run for a target below the proved bound (table `UPPER`).

## 1. Lemmas

**L1 (heredity of unit-distance).** Every subgraph of a unit-distance graph, induced or not,
is a unit-distance graph.

*Proof.* Restrict the injection f: V -> R^2 to the subgraph's vertices; every retained edge
still has unit length. (Non-edges are unconstrained, CONTRACT Section 1.)

*Use.* If an intermediate graph H (any level) is refuted by the embedder, i.e. has a proof
tree accepted by `check/udcheck.py` that H has no unit-distance embedding, then no descendant
of H in the DAG is a unit-distance graph, because every descendant contains H as an induced
subgraph. So no child of H needs to be generated for the purpose of finding (N, M)
unit-distance graphs.

**L2 (hereditary TU rule).** Let (N, M) satisfy u(N) <= M (proved). Let H be a graph on
n <= N vertices that contains a totally unfaithful gadget T (CONTRACT Section 1, one of the
six in `data/tu-gadgets.json`) as a not necessarily induced subgraph, with T's distinguished
pair {a, b} NON-adjacent in H. Then no graph G on N vertices with M edges that contains H as an
induced subgraph is a unit-distance graph. In particular no DAG descendant of H at the target
is a unit-distance graph.

*Proof.* Suppose G is a unit-distance graph with embedding f. T is a subgraph of H, hence of
G, so f restricted to V(T) is a unit-distance embedding of T, and by total unfaithfulness
|f(a) - f(b)| = 1. Since H is an induced subgraph of G and ab is not an edge of H, ab is not an
edge of G. Then G + ab is a unit-distance graph (same f) on N vertices with M + 1 > u(N) edges,
a contradiction.

*Why induced matters.* The hypothesis "ab non-adjacent in H" transfers to G only because H is
induced in G. DAG ancestors are induced subgraphs (vertex deletion), so the rule applies to
every ancestor. The semantics note of CONTRACT Section 1 (a TU hit means "not extremal") is
exactly why the target edge count M must be at or above the proved bound: the argument
consumes the inequality M + 1 > u(N), nothing about H's own edge count.

**L3 (unknown is kept).** A graph the embedder cannot decide gets verdict "unknown", no
witness, is listed in `<n>-<m>.UNKNOWN.g6`, and is KEPT as a parent. Pruning only ever removes
graphs with a checkable "tu" or "refuted" certificate. Also, the embedder's per-graph
wall-clock budget in `prune.py` turns a timeout into "unknown" (kept), never into a pruning.

**L4 (reach table).** Fix the target (N, M) and a number k_N such that every (N, M) graph we
are looking for has minimum degree at least k_N. Define R(N) = {M: k_N} and, for n from N-1
down to the seed order, R(n) = {m: k(n, m)} where, for every (M', k') in R(n+1) and every
integer d with

    k' <= d <= min(n, floor(2 M' / (n+1)))    and    0 <= M' - d <= u-bar(n),

the pair (M' - d, max(0, d - 1)) is contributed to R(n), and k(n, m) is the MINIMUM contributed
bound for that m. Then for every graph G at the target that we are looking for, every graph
G_j on its construction path satisfies: G_j has m_j edges with m_j a key of R(j), and
delta(G_j) >= k(j, m_j). Moreover the step G_j -> G_{j+1} uses d = m_{j+1} - m_j with
(m_{j+1}, k') in R(j+1) and d >= k'.

*Proof.* Downward induction on j. For j = N the claim is the hypothesis on k_N. Suppose
(m_{j+1}, k') is in R(j+1) with delta(G_{j+1}) >= k'. Put d = delta(G_{j+1}) = deg(v_{j+1}),
the degree of the deleted minimum-degree vertex, so m_j = m_{j+1} - d. Then k' <= d; d <= j
because v_{j+1} has at most j neighbours; d <= floor(2 m_{j+1} / (j+1)) because the minimum
degree is at most the average degree; and 0 <= m_j <= u-bar(j) because G_j is F-free on j
vertices. So (m_j, max(0, d-1)) is contributed to R(j), hence m_j is a key of R(j) with
k(j, m_j) <= d - 1. Finally deleting one vertex lowers every other degree by at most one, so
delta(G_j) >= delta(G_{j+1}) - 1 = d - 1 >= k(j, m_j). The last sentence of the statement is the
pair (m_{j+1}, k') itself.

*Consequences used by `run-dag2.py --reach`.* (i) A level file (n, m) with m not a key of R(n)
is never on a useful path and is not generated. (ii) For the level (n+1, M') only parents
(n, m) with d = M' - m >= k(n+1, M') are used (the parent file is the concatenation of exactly
those level files, listed in the aggregate manifest as `parent_sources`). (iii) A graph at
(n, m) with minimum degree below k(n, m) is on no useful path; `<n>-<m>.reach.g6` is the level
file with those graphs removed, and only it is used as a parent (and as the input to
hereditary pruning, which saves the embedder's time). The removed graphs need no certificate:
the stranger recomputes the minimum degree from the graph6 string.

*The root bound.* For a target (N, M) with M = u(N) the default is k_N = M - u-bar(N-1), which
is Schade's bound (deleting a minimum-degree vertex leaves an F-free graph with M - delta
edges, so delta >= M - u-bar(N-1)); nothing is lost. For (22, 61) that gives k = 4, and
Lemma D4 (`delta4/RESULT.md`: every (22, 61) unit-distance graph has minimum degree exactly 5,
proved with 18,689 forbidden-subgraph certificates) raises it to k = 5, recorded in
`reach.json` as `root_k_source`. With k = 5 the pruned DAG looks only for (22, 61) graphs with
minimum degree 5; D4 covers the rest. u-bar(n) for n <= 21 equals u(n) (AMP Table 1 and the
sentence "these upper bounds match the best known lower bound when n <= 21"); the table `UBAR`
in `run-dag2.py` is the same one `run-dag.py` already uses for Schade's window, so L4
introduces no new input.

Reach tables (from `reach.json` of the runs; k in brackets):

    target (22,61), k_22 = 5 (D4)
      21: 56[4]                          (21-57 is not generated)
      20: 51[4] 52[3]                    (20-53, 20-54 are not generated)
      19: 46[4] 47[3] 48[3] 49[2]        (19-50 is not generated)
      18: 42[3] 43[3] 44[2] 45[2] 46[2]
      17: 38[3] 39[2] 40[2] 41[2] 42[1] 43[1]
      16: 34[3] 35[2] 36[2] 37[1] 38[1] 39[1] 40[1] 41[0]
    target (18,46), k_18 = 3 (Schade)
      17: 41[4] 42[3] 43[2]
      16: 37[3] 38[3] 39[2] 40[2] 41[1]
      15: 33[3] 34[2] 35[2] 36[2] 37[1]
    target (17,43), k_17 = 2 (Schade)
      16: 38[4] 39[3] 40[2] 41[1]

## 2. The pruned DAG and what is generated

With `--reach` and `--prune --prune-from P`, the level file `<n>-<m>.g6` is the generator's
output on the parent file `_parents/<n>-<m>.g6`, which is the concatenation, in increasing
m', of the STAGE file of each parent level (n-1, m') allowed by L4(ii). The stage file of a
level is the last of: `<n>-<m>.g6` (full), `<n>-<m>.reach.g6` (L4(iii), if `--reach`),
`<n>-<m>.keep.g6` (L1 to L3, if `--prune` and n >= P). Each stage has its own manifest
(`.manifest.json`, `.reach.manifest.json`, `.prune.manifest.json`) with input and output
hashes and counts, and the aggregate manifest of every level lists the stage file, its kind,
hash and record count for every parent source.

Claim: every F-free (N, M) unit-distance graph G with delta(G) >= k_N is written to
`<N>-<M>.g6` and, being a unit-distance graph, is not tu or refuted, so it is in
`<N>-<M>.keep.g6` (as embedded or unknown).

*Proof.* Let G_N = G, G_{N-1}, ... be G's construction path. By L1 every G_j is a unit-distance
graph, so the sound embedder never refutes it (a refutation certificate accepted by the checker
is a proof of non-embeddability). By L2 (contrapositive, using that G_j is induced in G and G
is a unit-distance graph with M >= u(N) edges) G_j contains no TU gadget with its pair
non-adjacent, so the filter never gives it verdict tu. By L4, m_j is a key of R(j),
delta(G_j) >= k(j, m_j), and the step to G_{j+1} uses an allowed d. Induction upward: the
seed G_s is in the seed file (geng is complete, the F filter is sound), passes the reach filter
and the prune filter, hence is in the stage file; it is placed in the parent file of
(j+1, m_{j+1}) by L4(ii); the generator writes G_{j+1} (completeness of canonical
augmentation, CONTRACT 3.6 controls); G_{j+1} passes the stages likewise.

Nothing is claimed about F-free non-unit-distance graphs at the target: they may or may not
be generated, which is the point.

## 3. The certificate of "no (22, 61) unit-distance graph" under pruning

It consists of

1. `reach.json` (target, k_22 = 5 with its source D4, the u-bar table, R(n) for every level)
   and `delta4/RESULT.md` with its 18,689 certificates (for k_22 = 5);
2. the enumeration manifests of the pruned DAG: seed records, every shard manifest, every
   aggregate manifest with its `parent_sources`, every reach manifest, every prune manifest
   (each names the software hashes, `reach.json`'s hash, input and output hashes, counts);
3. one certificate line per PRUNED node: for every level (n, m) with n >= P, the file
   `<n>-<m>.certs.jsonl` contains one record per graph of the stage input in order (verified by
   the checker with `--graphs`), and every graph absent from `<n>-<m>.keep.g6` has verdict tu
   (gadget index, injective map, non-adjacent mapped pair) or refuted (proof tree);
4. one certificate line per graph of `22-61.g6` (the final level's `22-61.certs.jsonl`), with
   verdict in {tu, refuted} and `22-61.UNKNOWN.g6` empty (else CONTRACT 6.2's conditional
   statement applies to the unknown graphs);
5. the generator's completeness controls (CONTRACT 3.6: Table 1 reproduced on the UNPRUNED
   generator, the 56 known graphs present, the three mutation tests red) and the second
   enumerator's agreement on a stated fraction of shards.

A stranger checks: (a) `udcheck.py --expect-n n --expect-m m --graphs <stage input>
--unknown-file <n>-<m>.UNKNOWN.g6 <n>-<m>.certs.jsonl` accepts for every pruned level and the
target; (b) `<n>-<m>.keep.g6` equals, in order, the certificate records with verdict embedded
or unknown (a 10-line script; `prune.py` `verify_outputs` does it too but the stranger should
not trust it); (c) `<n>-<m>.reach.g6` equals the level file minus graphs of minimum degree
below k(n, m) from `reach.json`, and `reach.json`'s table follows from its root by the L4
recursion; (d) every `_parents/<n>-<m>.g6` is the concatenation of the listed stage files with
the listed hashes, and the listed parent levels are exactly those allowed by L4(ii); (e) the
shard manifests cover every parent range and hash the parent file, the forbidden list and
the binaries; (f) the completeness controls of item 5. Then by Section 2 every (22, 61)
unit-distance graph with minimum degree 5 would be in `22-61.keep.g6`, which is empty by
item 4, and by D4 there is none with minimum degree 4 or less. The never-generated
descendants of pruned nodes are covered by L1 (refuted) and L2 (tu); the never-generated
level files and dropped low-degree graphs by L4.

## 4. Controls run, with their numbers

All on liam-desktop on 2026-09-05 while the supervisor's unpruned (19,50) run (two `udenum`
processes) shared the four cores; wall times are pessimistic and not portable. Commands were
run from `enum/`. `run-dag.py` was never edited (its on-disk sha256 is
`8546a6d7da38ddedf3e7cfc8f587d84a644ffba77d45b69bb8ff7af21982b35e`, mtime 07:22).

### 4.1 A schema mismatch found by the first smoke test (CONTRACT 9.1)

The filter's tu witness `pair` is the gadget's own pair (gadget-local indices; its
`verify-witness.py` checks `pair == pattern["pair"]`), while the binding checker expects the
two candidate vertices the pair maps to. Exact rejection on the first smoke test:

    prune.py: RED: udcheck REJECTED the certificates: REJECT: .../17-43.certs.jsonl:1.witness.pair: is not the mapped distinguished gadget pair

`prune.py` now converts (`convert_tu_witness`) after checking that the filter's pair equals
the gadget's pair in `data/tu-gadgets.json`. The abort-on-reject path was thereby exercised
for real before any control ran.

### 4.2 Embedder budget (why the pruning default is `--tries 0`)

Twelve random TU-survivors of the (16,38) level, one process:

    --tries 0 --max-states 100:   57.8 s for 12 graphs: 3 refuted, 9 unknown (4.8 s per graph)
    default --tries 24 --max-states 400: 2 refuted in 3 s, then one graph ran > 5 min (killed)

The AMP-rejected (17,43) survivor `PoDQhOoKIOH@IO@Y?igDU?dk`: `--tries 0` with 400 or 1000
states returns unknown in about 3 s; the default ran > 2.5 min without a verdict. The
deterministic reduction terminates quickly on it; the random search is what runs for
minutes. Hence `run-dag2.py` defaults to `--prune-tries 0 --prune-max-states 400` with a
120 s per-graph budget (a timeout is recorded as unknown, kept). The 56 known graphs are
embedded through the embedder's `known_coordinates` regardless of tries.

### 4.3 Filter cost and yield, and what L4(iii) removes

    filter 16-38 (2045 graphs): 57.4 s, 1757 tu / 288 pass
    filter 17-41 (19103):      604.4 s, 17036 tu / 2067 pass
    filter 16-37 first 3000:    68.0 s, 2799 tu / 201 pass
    minimum degree, 16-37: {0:1, 1:109, 2:9449, 3:36457, 4:4785}; k = 3 for (18,46) drops 9559 of 50801
    minimum degree, 17-41: {0:1, 1:59, 2:3663, 3:13211, 4:2169};  k = 4 drops 16934 of 19103
    minimum degree, 18-46: {3:55, 4:28, 5:1}; root k = 3 drops nothing, k = 4 would drop 55

### 4.4 prune.py smoke test and red controls (scratch copies of out-sup/dag-17-43/17-43.g6)

    python3 prune.py --level 17-43.g6 --target-n 17 --target-m 43 --jobs 2 --tries 0 --max-states 400 --graph-timeout 120
    counts {input 15, tu 7, survivors 8, embedded 7, refuted 0, unknown 1, kept 8, pruned 7}; wall filter 0.9 s, embed 23.0 s, check 1.5 s
    checker: ACCEPT certificates records=15 forbidden=0 tu=7 embedded=7 refuted=0 unknown=1 proof_nodes=0
    keep = the 7 known 17-vertex graphs plus the unknown PoDQhOoKIOH@IO@Y?igDU?dk

Red: (1) `--target-n 18 --target-m 45`: `target (18,45) lies below the proved bound u(18) <= 46;
TU pruning is not justified` (exit 2). (2) A random 17-vertex 43-edge graph containing K4,
canonicalised and appended: `GENERATOR BUG: the level file contains a non-F-free graph
P??@og?CSAAsak@EHCZXYG^[ (forbidden witness {'index': 0, 'map': [8, 11, 15, 16]})` (exit 2).
(3) `--mutation-unknown-as-pruned`: both defences fire, exit 1, manifest `exit_status 1` and
`mutation.unknown_as_pruned true`: `udcheck REJECTED ...: UNKNOWN.g6 does not exactly list
unknown certificate records in order` and `output verification failed: keep file is not
exactly the embedded and unknown records in order; UNKNOWN file is not exactly the unknown
records in order`.

### 4.5 run-dag2.py plumbing, target (16,41), `--reach --prune --prune-from 15 --jobs 2`

Fresh run 49.7 s, 30 files. 15-36: 6 generated from 14-32 only (d = 4 by L4; the unpruned
level has 11), prune 4 tu, 2 unknown, 2 kept; 15-37: 1, embedded; 16-41: 1 generated from
the 3 keep parents, embedded (the known graph). `--resume`: 0.24 s, every level, reach and
prune step `resumed: true`. Refused: a different `--prune-from` (`run-config.json differs`),
no `--reach` on the directory (`has a reach.json but --reach was not given`),
`--reach-root-k 5` (`existing reach.json differs from this run's reach table`).

### 4.6 verify-chain.py, clean and corrupted, on that directory

Clean: `levels_inspected 20, reach_files 20, keep_files 3, parent_files 16, shards 16, CHAIN OK`.
Corruptions (each restored, directory byte-identical to its backup afterwards): a line
dropped from 15-36.keep.g6 (4 problems); reach.json k(15,36) 4 to 3 (33 problems: the table
no longer follows from its root, and every manifest's reach.json hash); `_parents/16-41.g6`
truncated (4 problems: concatenation, aggregate and shard hashes, ranges do not tile); a tu
record turned into unknown without touching keep (3 problems).

### 4.7 Controls on the real targets (queue `out-prune/run-controls.sh`)

Each run: `nice -n 10 python3 run-dag2.py --target-n N --target-m M --output-dir DIR --jobs 2 <flags>`.

**(a) target (17,43), `--reach --prune --prune-from 16`, `out-prune/dag-17-43-prune16`: exit 0
after 601 s** (the supervisor's unpruned run: 162 s). Columns: unpruned count in
`out-sup/dag-17-43`, generated here, reach bound k, after the reach filter, then the prune
step's tu, refuted, embedded, unknown, kept, and its filter, embed and check seconds.

    level  unpruned generated  k  reach    tu refuted embedded unknown kept  filter  embed  check
    15-34      5886      4332  3   4332     -       -        -       -    -
    15-35       252       217  3    217     -       -        -       -    -
    15-36        11        11  2     11     -       -        -       -    -
    15-37         1         1  2      1     -       -        -       -    -
    16-38      2045       433  4    433   421       7        0       5    5    13.3   67.6    4.7
    16-39       108        97  3     97    89       0        0       8    8     3.6   47.0    0.4
    16-40         6         6  2      6     5       0        0       1    1     0.3   11.2    0.5
    16-41         1         1  1      1     0       0        1       0    1     0.0    5.0    1.3
    17-43        15         9  2      9     1       0        7       1    8     0.5   29.3    1.0

Top: 9 of the 15 F-free (17,43) graphs are generated (the other 6 have a tu or refuted
ancestor at level 16); all 7 known graphs are among the 9; keep = the 7 known + the unknown
`PoDQhOoKIOH@IO@Y?igDU?dk` (the AMP-rejected graph, Section 4.2), so "keep minus unknown ==
known set" holds and "keep == known set" does not, by the embedder's limit. The (16,41)
level keeps its one graph (embedded). No embedder timeouts. `verify-chain.py --check`:
`levels_inspected 34, reach_files 34, keep_files 5, parent_files 29, shards 51,
certs_replayed 5, CHAIN OK` (19 s).

Where the reach table bites: 16-38 is generated only from 15-34 with d = 4 (L4: (38,4) in
R(16)), so it holds the 433 graphs of minimum degree 4 instead of all 2045; 15-34 is built
from 14-30 and 14-31 only (4332 instead of 5886).

**(b1) target (18,46), `--reach` alone, `out-prune/dag-18-46-reach`: exit 0 after 1993 s**
(the supervisor's unpruned run `out-sup/dag-18-46`: 1196 s; but see the CPU comparison).
Top: 84 graphs, all 16 known present, identical to the unpruned top. Every reference level
is generated. `verify-chain.py`: `levels_inspected 36, reach_files 36, parent_files 36,
shards 220, CHAIN OK` (85 s). Generated counts (unpruned -> reach), reach k, parents of the
next big level, and udenum CPU seconds from the shard stats (`parents_processed` in brackets):

    level   unpruned -> reach     k   udenum cpu s unpruned [processed] -> reach [processed]
    13-25   1235062 -> 709053     3   655.5 [251189] -> 635.6 [233793]
    13-26     67140 ->  66448     2    28.7 [25519]  ->  44.0 [25432]
    14-29    394705 -> 266653     3   200.7 [390445] -> 289.3 [386288]
    14-30     19492 ->  19328     2    20.8 [36182]  ->  30.7 [36163]
    15-33    133102 ->  95293     3   274.9 [261773] -> 406.8 [260611]
    15-34      5886 ->   5873     2    17.3 [12473]  ->  24.8 [12471]
    16-37     50801 ->  41242     3   227.5 [99773]  -> 325.7 [99509]
    16-38      2045 ->   1727     3    13.9 [4586]   ->  14.3 [4574]
    17-41     19103 ->   2169     4   194.7 [43369]  -> 259.9 [41214]
    17-42       590 ->    433     3    10.6 [1842]   ->  14.0 [1835]
    17-43        15 ->     15     2     0.7 [210]    ->   1.1 [210]
    18-46        84 ->     84     3     4.6 [943]    ->   6.1 [943]
    parent files: 15-33 415359 -> 285981, 16-37 139252 -> 101166, 17-41 52961 -> 41242
    total udenum cpu: 1786 s unpruned, 2191 s reach (the box is 2 cores x 2 hyperthreads and
    carried the supervisor's two (19,50) processes plus mine: 1.05 vs 1.56 ms per parent at 15-33)

The honest reading. L4 is sound (top identical, chain verified) and shrinks the LEVEL FILES
by 40 to 90 percent at the low-m end, but it does NOT reduce the generator's work: the
number of parents actually processed per level is nearly unchanged, because `udenum` already
skips a parent with delta(H) <= d - 2 (AMP p. 5, `parents_degree_skipped`) in microseconds,
and those are exactly the parents L4(ii) and L4(iii) remove. The dropped children are the
cheap small-d ones (12-23/24/25 gave 13-25 half its graphs from 7 percent of its parents).
What L4 buys is proportional to level-file size: storage, the 30 ms per graph TU filter and
the seconds per survivor embedder of hereditary pruning, and the four never-generated level
files of the (22,61) DAG (19-50, 20-53, 20-54, 21-57, all small). The generator's
15,000 CPU-hours are in the d = 3 and d = 4 parents, which are all reachable. Hereditary
pruning is the lever on parent COUNT (Section 4.3: the TU rule removes 86 to 93 percent of
the graphs at levels 16 and 17); its cost is the filter, not the generator.

**(d) red control of the root bound: target (18,46), `--reach --reach-root-k 4`,
`out-prune/dag-18-46-k4`: completed through n = 18** (53 min on the loaded box). Predicted
from the minimum degrees of the known graphs beforehand (the 16 known 18-vertex graphs have
minimum degree 3 for 12 of them and 4 for 4; the 84 F-free top graphs split 55/28/1 by
minimum degree 3/4/5): top = 29 graphs, known present = 4. Measured: exactly that.

    16-37 41242, 16-38 1727, 16-39 108 (16-40, 16-41 not generated), 17-41 2169, 17-42 433 (17-43 not generated), 18-46: 29
    top 18-46: 29 graphs; known 16 present: 4  ->  compare.py RESULT FAIL

`reach.json` records `root_k 4, root_k_source: command line --reach-root-k`. This is how a
wrong D4 would show: a top level missing known graphs. With the default root bound (b1)
the same code gives 84 and 16 of 16.

**(b2) target (18,46), `--reach --prune --prune-from 16`: NOT completed.** The run
(`out-prune/dag-18-46-prune16`) was killed by the supervisor at 23:46Z, 117 s in, while
generating 12-23 (the shard died with SIGTERM), to free the box for the real (22,61) target
(`enum/out-22/`). It never reached a pruning step. The cost it would have paid, from the
measurements above: the level-16 stage input is 43,084 graphs after the reach filter
(41242 + 1727 + 108 + 6 + 1); the TU filter at 30 to 45 graphs per second per process is
about 10 to 12 minutes on two processes; the survivors (7 to 14 percent, about 3000 to
6000 graphs) at 3 to 5 s each on two processes are 1.5 to 4 hours (the supervisor's estimate
was about 40 hours on the box as loaded); the checker replay of 43k certificates adds
minutes. The gain it would have measured is the parent count of level 17: 2169 + 433 + 15
reach parents in (b1) against roughly 10 to 15 percent of that after TU pruning (the
embedder adds a further 20 to 60 percent of the survivors as refutations, Section 4.2 and
(a)).

**(19,50) with `--reach` into `out-sup2/dag-19-50`: NOT completed.** Started at 23:46:39Z
after (b2) failed, killed by me at 23:47Z on the supervisor's instruction; the directory
holds only partial low levels and no target file. What it would have shown is predicted by
(b1): 17 at the top with the 3 known present (all three have minimum degree 4, the root
bound), smaller level files where k >= 3, and no reduction of generator CPU (the (19,50)
13-24 parent file of the supervisor's run has 1,720,988 records, of which reach removes
the 255,059 from 12-22/23/24 that udenum's degree skip discards anyway).

### 4.8 Recommendation for the (22,61) run

Run the generator with `--reach` (root k = 5 from D4, the default) for the smaller files
and the four skipped levels, expecting no enumeration speed-up from it. Do not run the
embedder as a pruning step below level 21: at 3 to 5 s per survivor with `--tries 0` it
refutes 20 to 60 percent of the TU-survivors and leaves the rest unknown (kept), so it
removes at most a few percent of a level for hours of work, and its known failure mode is a
random search that runs for minutes on one graph (keep `--tries 0` and a per-graph budget
wherever it runs). The cheap lever is the TU filter alone (30 to 45 graphs per second per
process, 86 to 93 percent removed at levels 16 and 17): if `prune.py` is given a
`--filter-only` mode that records every survivor as "unknown" without invoking the embedder,
hereditary TU pruning from level 17 or 18 upward costs minutes per level and cuts the parent
count of every level above by an order of magnitude, which is where the generator's hours
are; the certificate stays valid as written (unknown is kept, tu is certified, L2 covers the
descendants). Reserve the embedder for the (21,56) keep set and the (22,61) candidates,
where each refutation is a certificate line the result needs anyway, and give the
AMP-rejected graphs the embedder cannot decide (Section 4.2) their own attack.
