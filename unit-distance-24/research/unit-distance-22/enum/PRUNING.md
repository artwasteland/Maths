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
degree is at most the average degree; and 0 <= m_j <= u(j) <= u-bar(j) because G_j is a
unit-distance graph on j vertices (an induced subgraph of one, L1). So (m_j, max(0, d-1)) is
contributed to R(j), hence m_j is a key of R(j) with k(j, m_j) <= max(0, d - 1). Finally deleting
one vertex lowers every other degree by at most one, and no degree is negative, so
delta(G_j) >= max(0, delta(G_{j+1}) - 1) = max(0, d - 1) >= k(j, m_j). The last sentence of the
statement is the pair (m_{j+1}, k') itself.

*Erratum (2026-09-28, found by gpt-6-astra in the u(23) finishing review).* The proof above
first said m_j <= u-bar(j) "because G_j is F-free", but the bound needs G_j to be a unit-distance
graph (F-freeness alone does not bound the edges by u(j)); and it concluded k(j, m_j) <= d - 1,
which fails when d = 0, where the contributed bound is max(0, d - 1) = 0. Both are corrected
above. The code (`run-dag2.py`'s reach table) already used max(0, d - 1), and every graph on a
construction path is a unit-distance graph, so no computation changes.

*Consequences used by `run-dag2.py --reach`.* (i) A level file (n, m) with m not a key of R(n)
is never on a useful path and is not generated. (ii) For the level (n+1, M') only parents
(n, m) with d = M' - m >= k(n+1, M') are used (the parent file is the concatenation of exactly
those level files, listed in the aggregate manifest as `parent_sources`). (iii) A graph at
(n, m) with minimum degree below k(n, m) is on no useful path; `<n>-<m>.reach.g6` is the level
file with those graphs removed, and only it is used as a parent (and as the input to
hereditary pruning, which saves the embedder's time). The removed graphs need no certificate:
the stranger recomputes the minimum degree from the graph6 string.

*The root bound.* For a target (N, M) with M = u(N) the default is k_N = M - u-bar(N-1), which
is Schade's bound (deleting a minimum-degree vertex leaves a unit-distance graph with M - delta
edges, so delta >= M - u(N-1) >= M - u-bar(N-1)); nothing is lost. For (22, 61) that gives k = 4, and
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

(k) Coverage comes first and from the target alone: the stranger derives the u-bar table
(AMP's, or a recorded and justified lowering), Schade's windows, and the L4 table from a
JUSTIFIED root k (Schade's bound M - u-bar(N - 1), or a recorded lemma such as D4), hence
the REQUIRED cells (every (n, m) of the table, from the seed level to the target) and every
cell's allowed parent edge counts (L4(ii)). Every required cell must be present and pass
(a)-(e), with exactly those parents; the run's own summary, which lists the cells it made
and the windows it used, is checked against the derivation and never trusted for it. Without
(k), (a)-(e) check only the cells the run says it made: a run with (15,37) omitted and its
level-15 window narrowed, or with its pruned levels' entries deleted from its summary, passed
them while losing AMP's (16,41) graph (G5 objection 1, 2026-09-26; `enum/verify-chain.py`
now does (k), and says CHAIN OK only when the check was exhaustive: Section 5.9).

## 4. Controls run, with their numbers

All on <host> on 2026-09-05 while the supervisor's unpruned (19,50) run (two `udenum`
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

## 5. L5: the rhombus rule (u(23) programme, 2026-09-26)

Binding source: `research/unit-distance-23/RHOMBUS-SPEC.md` (lemma, certificate schema, tool
contracts). Code: `filter/udrhombus.c` (the prover), `prune.py --rhombus` and `run-dag2.py
--rhombus` (default off), `check/udcheck_rhombus.py` (the checker, written blind from the spec by
another agent). Tests and measurements: `enum/test-rhombus/REPORT.md`.

### 5.1 The lemma and its two corollaries

Throughout, f: V(G) -> R^2 is injective with |f(s) - f(t)| = 1 for every edge st (a unit-distance
embedding; non-edges are unconstrained, CONTRACT Section 1). A 4-cycle C = [u, v, w, x] of G is four
PAIRWISE DISTINCT vertices with uv, vw, wx and xu edges (not necessarily induced). Write
r(C) = e_u - e_v + e_w - e_x in Z^n.

**Lemma R (every unit 4-cycle is a rhombus).** f(u) + f(w) = f(v) + f(x), that is
sum_i r(C)_i f(i) = 0.

*Proof.* The four vectors a = f(u) - f(v), b = f(v) - f(w), c = f(w) - f(x), d = f(x) - f(u) are unit
vectors (the four edges) and a + b + c + d = 0 (the sum telescopes). Put s = a + b = f(u) - f(w).
Since u != w and f is injective, s != 0. The unit vectors y with |s - y| = 1 are the points common to
the unit circles centred at 0 and at s; the centres differ, so there are at most two such points, and
the two circles have equal radii, so the points are mirror images in the line through 0 and s and
their midpoint is s/2: they sum to s (when there is only one point, it is s/2, and "they" are that
point twice). Now a is such a point (|a| = 1, |s - a| = |b| = 1), and so is b = s - a; so {a, b} is
exactly that set (as a multiset: {y1, y2}, or {s/2, s/2}). Likewise -c and -d are such points
(|s + c| = |-d| = 1 and |s + d| = |-c| = 1) and -c - d = a + b = s, so {-c, -d} is the same multiset.
Hence a = -c or a = -d. If a = -d, then f(u) - f(v) = f(u) - f(x), so f(v) = f(x) with v != x, against
injectivity. So a = -c: f(u) - f(v) = f(x) - f(w), which is the claim. QED.

(Only u != w, v != x, the four edges and injectivity are used; the tangent case |s| = 2, where v is
the midpoint of u and w, is covered. The rule's own tests confirm the lemma numerically on the
9,712 forced pairs of GP-10's embedded graphs, Section 5.5.)

**Corollary R1 (collision; verdict refuted).** If 4-cycles C_1..C_k of G, integers l_1..l_k and an
integer s != 0 satisfy sum_j l_j r(C_j) = s (e_a - e_b) with a != b, then G is not a unit-distance
graph.

*Proof.* If f were a unit-distance embedding, apply the linear map z -> sum_i z_i f(i) to both sides:
the left side is sum_j l_j (f(u_j) - f(v_j) + f(w_j) - f(x_j)) = 0 by Lemma R, the right side is
s (f(a) - f(b)). So f(a) = f(b) with a != b, against injectivity. QED.

**Corollary R2 (forced unit distance; verdict tu).** If sum_j l_j r(C_j) = s (e_a - e_b - e_p + e_q)
with s != 0 and pq an edge of G, then every unit-distance embedding of G has f(a) - f(b) = f(p) - f(q),
hence |f(a) - f(b)| = 1.

*Proof.* The same linear map gives s (f(a) - f(b) - f(p) + f(q)) = 0; divide by s; |f(p) - f(q)| = 1
because pq is an edge. QED. (The pair may share a vertex with the edge: a = q gives
2 f(a) = f(b) + f(p), a midpoint relation, and the conclusion is the same. If a = p, or b = q, the
identity is a collision of the other two vertices and R1 applies instead.)

### 5.2 Heredity: why a certificate prunes every DAG descendant

*Refuted (R1).* By L1 every subgraph of a unit-distance graph is one, so a graph with an R1
certificate has no unit-distance supergraph at all: no DAG descendant of it, at any target, is a
unit-distance graph. This is L1 with a linear certificate in place of the embedder's proof tree, and
it needs no bound on u(N).

*TU (R2), with ab NOT an edge of H.* This is L2 with the linear certificate in place of a gadget.
Let (N, M) be a target with u(N) <= M proved (prune.py refuses any other target; `UPPER` holds the
bounds and their sources). Let H satisfy R2 with ab a non-edge of H, and let G be a graph on N vertices
with M edges containing H as an INDUCED subgraph. If G had a unit-distance embedding f, its restriction
to V(H) would be one of H (the 4-cycles of H are 4-cycles of G, and injectivity restricts), so
|f(a) - f(b)| = 1 by R2; ab is not an edge of G because H is induced in G and ab is not an edge of H;
so G + ab would be a unit-distance graph on N vertices with M + 1 > u(N) edges, a contradiction.
DAG ancestors are induced subgraphs (vertex deletion, Section 0), so the rule applies at every level,
exactly as L2 does, and it consumes only the inequality M + 1 > u(N), nothing about H's edge count.

*Where the target is checked.* A certificate proves only that H has a forced unit distance on a
non-edge; the checker (`check/udcheck_rhombus.py`, like `udcheck.py` for the gadgets) never sees the
target, so a tu record prunes soundly only because prune.py refuses every target without a proved
bound: before any work, with or without `--rhombus`, it requires target_n in `UPPER` and
target_m >= UPPER[target_n] (`UPPER_SOURCE` and every prune manifest's `tu_rule_bound` say why;
UPPER[23] = 65 rests on u(22) = 60 and Schade's lemma). `verify-chain.py` re-checks this from the
files: every prune manifest must name the run's target, and the target must meet its own copy of the
proved bounds. The refuted records (R1, and the embedder's proof trees) need no target at all.

*Section 2's claim with L5.* Every graph G_j on the construction path of a unit-distance (N, M) graph
G is itself a unit-distance graph (L1), so it has no R1 certificate (R1 would prove the opposite), and
it has no R2 certificate with a non-adjacent pair (the paragraph above, applied to H = G_j and G). So
the rhombus step never removes G_j, the induction of Section 2 goes through unchanged, and the
certificate of Section 3 gains one record type: for a pruned graph, item 3 now allows a rhombus
witness (tu or refuted) beside the gadget and the proof tree, and the stranger's check (a) replays
the whole file with `check/udcheck_rhombus.py --forbidden-set {74,398}` (which hands every
non-rhombus record to the pinned `udcheck.py` or `udcheck398.py`). `verify-chain.py --check` does
this for a run whose run-config.json says `"rhombus": true`.

*Relation to the six TU gadgets.* Each gadget's distinguished pair is forced by R2 inside the gadget
(the certificates of Section 5.4, generated by udrhombus and checked by hand). If a gadget T maps into
a host H by an injective edge-preserving map, the images of T's 4-cycles are 4-cycles of H, so T's
certificate, relabelled, is an R2 certificate in H; hence the rhombus rule subsumes the gadget rule
wherever the mapped pair is non-adjacent. udfilter's gadget verdicts stay as they are (checked by the
pinned kernel), and udrhombus runs only on udfilter's survivors.

### 5.3 The prover and the certificate

`filter/udrhombus` reads graph6 lines and writes one JSON line per graph: `{"verdict":"pass"}`, or
`refuted` / `tu` with the witness `{"rhombus": {"cycles": [[u,v,w,x], ...], "coefficients": [...],
"scale": s, "pair": [a, b]}}` (plus `"edge": [p, q]` for tu), RHOMBUS-SPEC.md Section 2. Priority:
the lexicographically first colliding pair; else the lexicographically first non-adjacent forced
pair with the lexicographically first ordered edge forcing it; else pass. Method, and why each step
is exact:

1. Every 4-cycle is listed once, as [u, v, w, x] with u its smallest vertex (u < w, v < x common
   neighbours of u and w, u < v; the other diagonal would give -r(C)).
2. Detection is modulo P = 2^61 - 1, and it decides the rational question exactly: the rows involved
   (cycle rows and one target vector) have Euclidean norm at most sqrt 6 and at most 32 of them are
   independent, so by Hadamard's inequality every minor is below 6^16 < 2^42 < P in absolute value. A
   minor therefore vanishes mod P iff it vanishes over Z: ranks mod P equal ranks over Q, and a target
   vector lies in the rational row space iff it lies in the row space mod P.
3. A null-space fingerprint y (mod P) proposes candidates: a true collision forces y_a = y_b and a
   true forced pair forces y_a - y_b = y_p - y_q, so no instance is missed; each candidate, in
   lexicographic order, is then decided exactly by reducing its target vector against the basis.
4. The certificate uses a maximal independent set of ORIGINAL cycle rows (greedy, in listing order).
   On their pivot columns the k x k system is nonsingular; fraction-free elimination (Bareiss, row
   interchanges, every division checked exact, 128-bit products, every value checked below 2^62)
   gives Cramer numerators x_i = D l_i with D = +-det; dividing by g = gcd(D, x) gives the scale
   s = |D| / g and the coefficients; zero coefficients are dropped.
5. Before writing, the prover re-checks every rule of the spec's Section 2 from the certificate
   alone, including the identity coordinate by coordinate in 128-bit integers; any failure writes
   pass (the graph is kept) and is counted in the statistics line on stderr, which prune.py copies
   into the manifest (`rhombus_stats`, `certificate_failures`).

prune.py refuses a red-control build of the prover (its statistics line names the mutant) before
doing any work, and cross-checks three counts of the rhombus records: the prover's, the certificate
file's and the checker's ACCEPT line (`rhombus_tu=`, `rhombus_refuted=`).

### 5.4 The six TU gadgets as integer R2 certificates

Generated by `udrhombus --pair a b` on each gadget of `data/tu-gadgets.json`, in the gadget's own
vertex labels (graph6 in those labels, not canonical), and checked by hand and by the dev replay
(`enum/test-rhombus/units.py`, U2). In every case s = 1. The default priority search finds each
gadget's own pair first except gadget 4 (the graph of gadget 3, whose pair (3,7) is forced as well
and comes first).

    gadget 0  Elcg    pair (1,5)  edge (0,4)
      -[0,1,2,3] + [2,3,4,5]                         = e1 - e5 - e0 + e4
    gadget 1  F^gbG   pair (4,5)  edge (0,2)
      -[0,3,2,4] + [1,3,2,6] - [1,2,5,6]             = e4 - e5 - e0 + e2
    gadget 2  F^_jG   pair (2,4)  edge (1,2)
      -[0,2,1,3] + [0,2,5,4] + [1,3,2,6] - [1,2,5,6] = e2 - e4 - e1 + e2   (a = q: 2 f(2) = f(4) + f(1))
    gadget 3  GrClIO  pair (3,7)  edge (2,6)
      [0,1,3,2] - [0,2,5,6] + [1,3,4,7] - [2,3,4,5]  = e3 - e7 - e2 + e6
    gadget 4  GrClIO  pair (6,7)  edge (0,1)
      -[0,2,5,6] + [1,3,4,7] - [2,3,4,5]             = e6 - e7 - e0 + e1
    gadget 5  GrCkIO  pair (6,7)  edge (0,1)
      -[0,2,5,6] + [1,3,4,7] - [2,3,4,5]             = e6 - e7 - e0 + e1

([u,v,w,x] stands for r = e_u - e_v + e_w - e_x.) Gadget 0 read as geometry: the rhombus 0-1-2-3
gives f(1) - f(0) = f(2) - f(3) and the rhombus 2-3-4-5 gives f(2) - f(3) = f(5) - f(4), so
f(1) - f(5) = f(0) - f(4), a unit vector: the pair is carried across two rhombi by translation.
Gadget 5 is gadget 4 without the edge 26, which none of its three cycles uses.

### 5.5 Controls run (details and numbers: `enum/test-rhombus/REPORT.md`, runner `run-all.sh`)

Units (K2,3 refuted; the six gadgets tu; Moser spindle, unit rhombus, W6 pass; AMP's 56 known densest
graphs all pass); the B10 positive control (GP-10's 32,653 embedded 10-vertex graphs: none refuted,
9,712 tu, and in every one the forced pair is at unit distance in GP-10's exact embedding, evaluated
at 80 digits, with f(a) - f(b) = f(p) - f(q)); verdict-class agreement with the supervisor's
prototype `research/unit-distance-23/tools/rhombus_probe.py` on every graph of the (23,65) descent
samples, and verdict, pair and edge equal to an exact rational computation (no modulus) on the same
graphs; five compile-time mutants caught (four by the positive controls and the checker, the fifth
showing that a failed self-verification is a counted pass); the binding controls of RHOMBUS-SPEC
amendment 2 run through `check/udcheck_rhombus.py` itself (`through-checker.py`); end to end on
(16,41), (17,43) and (18,46), replayed by the checker, with every known extremal graph kept, and
byte-identical outputs without the flag.

### 5.6 The prune step's forbidden re-check, and `--prune-filter-set 74`

The prune step runs `udfilter` on every stage-input graph, and udfilter does two things in order: it
looks for a member of its forbidden list (a hit is a GENERATOR BUG: prune.py aborts, it never
certifies one), and only then for the six TU gadgets. The gadget search does not depend on the
forbidden list. So on graphs containing none of the run's forbidden graphs, `udfilter -s 74` and
`udfilter -s 398` give the same verdicts and the same witnesses, and the certificate, keep and UNKNOWN
files are byte-identical. In a set-398 run the two differ only on a stage-input graph that contains
one of GP-10's 324 (and none of the 74), which the generator should never produce.

Such a graph is not a unit-distance graph (L1), so it can only make the tree a SUPERSET: Section 2's
claim is that every F-free unit-distance graph on the path is generated, and "nothing is claimed about
F-free non-unit-distance graphs at the target". The re-check therefore guards cost, never soundness.
With `--prune-filter-set 74` (prune.py `--filter-set 74`) such a graph is TU-pruned if it holds a gadget
(a valid certificate) or kept as unknown, and a kept one lands in the level's stage file, where
`--verify-stages` (udenum `--verify-parents` in set 398 over every stage file, fast since the Mode 398
speed-up) finds it and stops the run at that level. So in a set-398 run with `--verify-stages`, the
prune step's 398 re-check is redundant with the stage verification: run-dag2.py accepts
`--prune-filter-set 74` only together with `--verify-stages`, and verify-chain.py refuses a run that
records one without the other. The certificate replay does not change: its kernel stays the run's
(`udcheck398.py`, or `udcheck_rhombus.py --forbidden-set 398`), and the prune manifests record
`filter_set: 74` and hash both forbidden files. The measured reason (pilot 2, slice 240 of (23,65),
fast udenum): the prune step's `udfilter -s 398` took 1,431 s of about 2,250 s, and udfilter's per-graph
cost is 4 to 7 times larger in set 398 than in set 74. Tests: `enum/test-rhombus/filterset.py`.

### 5.7 The triangle rule (`--triangles`)

RHOMBUS-SPEC.md Section 4 (Lemma T and the case-tree certificate, with its soundness argument) extends
the rule: in a unit-distance embedding every triangle is equilateral with one of two orientations, and
a certificate is a tree of such splits whose every leaf closes by the linear algebra of Section 5.1
(over Z[w], w a primitive sixth root of unity). `filter/udtriangle` is its prover, witness key `tri`,
checked by `check/udcheck_rhombus.py` through its pinned `check/tri_verify.py`. Heredity is as in
5.2: the triangles and 4-cycles of H are those of every graph containing H, and a non-edge of H stays
a non-edge in any graph containing H as an induced subgraph, so a tree for H is a tree for every DAG
descendant; a `refuted` tree needs no target and a `tu` tree prunes only at a target with a proved
bound (the same guard). The rhombus rule is the tree with no split, so udtriangle's verdicts contain
udrhombus's, and `--triangles` (prune.py, run-dag2.py; runbook `U23_TRIANGLES=1`, suffix `-tri`)
runs udtriangle IN PLACE of udrhombus on udfilter's survivors; the two flags exclude each other. The
prune manifests record `triangles: true`, the counts `tri_tu`, `tri_refuted` and `tri_silent_passes`
(its budget, verify_fail, lift_fail and internal passes), and the prover's whole statistics line
(`triangles_stats`); verify-chain.py replays such a run with the same checker and refuses a `rhombus`
witness in it (and a `tri` witness in any run that does not record `--triangles`). udtriangle's
statistics line names its build (`mutant=N`, 0 in production, since cd88d2efa), so prune.py's preflight
refuses a red-control build of it as it does udrhombus's; were one to run anyway, its wrong certificates
would be rejected by the checker (prune.py goes red), or, for a search-only mutant, turned into counted
passes by its own self-verification (`verify_fail`).
Controls: `enum/test-rhombus/e2e.py` (C, R10, R11), `runbook-rh.py`, and
`make check-triangle` (its 13 unit graphs); the prover's own suite is `enum/test-triangle/`.

### 5.8 The prune step's replay in parallel chunks

Step 4 of prune.py (the run's checker replaying the cell's certificate file) ran as one process per
cell, about 15 percent of a pilot-3 slice. With `--jobs` > 1, a cell of more than
`$PRUNE_CHECK_PARALLEL_ABOVE` records (default 20,000) is now replayed in up to `--jobs` contiguous
chunks at once, each at most `$PRUNE_CHECK_CHUNK` records: chunk i is the level's graphs lo..hi-1,
the same lines of the certificate file byte for byte, and the entries of the written UNKNOWN file
that fall in it (so the checker still compares that file with the verdicts). The split loses
nothing: the certificate contract's checks (one record per graph in the list's order, each witness
proving its verdict, the unknown list equal to the unknown records in order) are per record or per
position, so they hold for the cell exactly when they hold for every chunk of a contiguous
partition; the one property across records, no duplicate graph, prune.py checks itself before step
1. Every chunk must ACCEPT with its own record and unknown counts; the counts are summed (rhombus_*
and tri_* too, so 5.3's three-way count check is unchanged); one REJECT fails the step with that
chunk's range and reason, and its files are kept. The manifest records the chunks
(`checker_chunking`), and the ACCEPT line ends `(parallel: K chunks of at most S, J at a time)`. At
or below the threshold, and with `--jobs 1`, the step is byte for byte what it was; verify-chain.py
still replays whole cells. Controls: `enum/test-rhombus/checkpar.py`.

### 5.9 The stranger's coverage check, and what a resumed run may reuse (G5, 2026-09-26)

A cross-model soundness read (`research/unit-distance-23/results/g5-cross-model-2026-09-26/`) found
the lemmas and both checkers sound, and two gaps in the tooling around them, both fixed here.

*Coverage (objection 1, FATAL for the audit).* `enum/verify-chain.py` took the cells to inspect,
and the windows that decide each cell's allowed parents, from the run's own `run-summary.json`. It
now derives both from the target alone (Section 3 (k)): the u-bar table (`check_ubar`), Schade's
windows, and the L4 table recomputed from reach.json's root k, which must be justified (at most
Schade's bound M - u-bar(N - 1), or a recorded lemma: D4's 5 at (22,61)); a stored table that
differs is refused. run-config.json, run-summary.json and reach.json must name the same target,
seed level, root and slice; the summary must list every required cell exactly once and no other,
with the derived windows and reach levels, and say `completed_through_n` = N; every required cell's
files must be present and pass the old checks, its parent sources being exactly the derived ones.
The verdict is `CHAIN OK` (exit 0), preceded by "COVERAGE exhaustive", only when every required cell
was inspected and, with pruning, every pruned cell's certificates were replayed (`--check`); a check
restricted by `--from-n` or run without `--check` says `CHAIN PARTIAL (reasons)` (exit 3), never
CHAIN OK. A sliced run is exhaustive for its slice only: the fleet needs every slice (below).
`--summary-only RUN ...` is the audit of runs whose directories are gone: it reads only their
run-config.json, run-summary.json and reach.json (and the earlier pushed versions of the summary,
for the parents of cells the final summary lists as resumed, used only when their counts agree),
checks the derivation, each recorded cell's parent edge counts, parent sources and counts, and for
a fleet of slices that every slice index is present, that their shared prefix agrees, and that
their records of each slice-level parent add up to that parent cell; its verdict is "COVERAGE
(summary only) OK" and then `CHAIN PARTIAL (summary only ...)`, never CHAIN OK. Controls:
`enum/test-rhombus/vchain.py` (the reviewer's two tamperings and two more, each accepted by the
landed tool and refused by the new one; the explicit PARTIAL verdicts; a sliced fleet with a slice
missing and with a slice record that does not add up). The u(22) slices' summary-only audit
(`results/u22/summary-coverage-audit.py`, output `summary-coverage-audit.txt`, 2026-09-26): 72 pushed
copies of the 48 slice summaries (all 48 indices), every copy listing every required cell of (22,61)
exactly once with the derived windows and reach levels (root k 5, Lemma D4) and completed through 22,
no problem; with their pushed histories (235 resumed cells recovered) the parents of all 23 prefix
cells and of every cell above level 13 are recorded, except slice 37's 24 cells at levels 14 to 16,
resumed in every version its worker pushed. So 47 of the 48 slices record their share of each
level-13 cell, and slice 37's share is recorded nowhere: the remainder it would have to hold (347,431
of the 16,609,368 records of (13,23); the mean share is 346,028.5) is unchecked by the summaries. The
target (22,61) had 4 children (slices 15 and 38), all pruned.

*Resume (objection 2, MAJOR).* `run-dag2.py --resume` reused a finished prune step whose manifest
had a clean status, the run's flags and matching file hashes, without looking at its target, its
checker or its ACCEPT line. It now reuses one only if the manifest names the run's target; hashes
the checkers prune.py would use now (udcheck.py always, udcheck398.py for set 398,
udcheck_rhombus.py with a rule) with their current sha256, and with a rule names the current
checker's path, not chosen by `$PRUNE_UDCHECK_RHOMBUS` (`from_environment` false; while that
variable is set nothing is reused); has an ACCEPT line whose counts agree with its counts and
verified counts (records, tu, refuted, embedded, unknown, the rule's own tu and refuted); and its
stage input, keep and UNKNOWN files hold as many records as those counts say. Anything else reruns
the step (with the same outputs, the run is otherwise unchanged). Controls: `vchain.py` phase P.

*Round 2 (the closure read, `G5-closure-read-gpt-6-astra.md`, of 4120dd63c).* Five gaps, closed as
follows, each of the reader's reproductions kept as a red control (`enum/test-rhombus/g5close.py`:
the landed tool accepts it, the fixed one refuses it, and an untouched run of each still passes).
(1, FATAL) Resume accepted a keep file with an unknown graph swapped for a tu graph when the keep
hash in the manifest was edited too (the removed graph, of (13,29), is the canonical ancestor of
AMP's (16,41) graph): resume now re-runs prune.py's own `verify_outputs`, which rebuilds the keep
and UNKNOWN files from the certificate verdicts, and every count must agree with what the files give
(4 CPU seconds per million records). (2, FATAL) A seed level outside 1..N-1 gave no required cell and
CHAIN OK: the seed range is checked, the target cell is always required, and `--expect-target`,
`--expect-seed` and `--expect-slices` pin what the caller expects. (3) Summary-only let a resumed
cell without recoverable parents, and a present slice without a share record, pass as notes, and
accepted shares of 75 of 74 records, or 80 and -6: every count must be a nonnegative integer, every
share at most its cell, and anything coverage needs that the summaries do not record is UNRESOLVED
(exit 4), never OK. (4) Fleet completeness trusted declared slice counts and compared prefixes by
counts: slice declarations are validated ([12,0,0] fails), the fleet can be pinned, each slice is
bound to its hashes.json (its slice, its files' record counts) and to its G4 replay (PASS or EMPTY,
of this slice, its re-derived slice files the sizes the summary records), and the prefix files must
hash identically in every slice and copy. (5) Resume did not reconcile the native counts (counts.tu
alone changed, or tu 999 on a 25-record cell in the ACCEPT line and the verified counts, passed) and
compared the target with the run's only (a consistent (16,40) passed): both now fail. The reader's
sixth point stands: for the running fleet's already-deleted intermediate stages no summary check
recovers the certificate-to-keep relation; that needs the full chain audit before deletion or the
stages restored. The summary-only audit of the running (23,65) fleet
(`enum/test-rhombus/fleet-audit.py`, 2026-09-26, pinned to (23,65), seed 10, level 12, 1920 slices,
hashes and G4 required; `runs/u23-fleet-audit.txt`): 383 slices from 44 workers, and nothing fails
but the 1,537 missing slices. The 70 prefix files hash identically in all 383 (every worker computed
the prefix itself), all 383 G4 replays PASS with their re-derived slice files the sizes the summaries
record, and the target cell (23,65) has no children in any of them. Two slices, 579 and 606, are
UNRESOLVED: their final summaries list 42 and 26 cells above level 12 as resumed (a restart), so they
record neither those cells' parents nor their shares of the eight level-12 parent cells; the
workers' earlier pushed summaries (not in the extracted results) may record them, as they did for
u(22). The u(22) audit now reports slice 37 as UNRESOLVED (exit 4), no longer OK.

*Round 3 (`G5-round3-read-gpt-6-astra.md`, of 4d2b1490b): findings 1-3 closed, three narrower gaps.*
(1) Copies of one slice were compared by file hashes and cell counts, and the partition took the shares
of the copy with the most of them: a duplicate of slice 0 claiming 35 of (12,24) instead of 34 passed or
failed with the argument order, and complementary copies left a recorded share unresolved. Each slice's
shares are now merged over all its copies, and two different values of one share fail. (2) The G4 check
accepted a PASS label over a seed level that differs (all_identical false), and an EMPTY label, with
exit 1 and nothing sampled, for a slice holding 734 graphs of (12,20): the verdict is now derived from
the replay's own evidence by the runbook's rule (every seed identical, all_identical, no mismatch or
unreplayable cell, every stage re-derived, red controls red in full mode, the fingerprint's numbers the
summary's; PASS only with exit 0 and parents sampled; EMPTY only for a slice-mode replay of a slice with
no parent above the slice level and every share 0), and a label that is not that verdict fails; the real
fleet record f01-jjpzl7/s0of1920 is the untouched control. (3) Resume compared the rule's counts only in
totals (counts.tu 11 -> 12 with tri_tu 1 -> 0 and survivors 14 -> 13 passed): the rule's tu and refuted
must now each be the records carrying its witness. Controls: `g5close.py` C6-C8, the landed tool
(4d2b1490b) against the fixed one. The fleet audit rerun with these checks (`runs/u23-fleet-audit.txt`,
577 slices from 44 workers): again nothing fails but the 1,343 missing slices; all 577 G4 labels are
the verdicts their own evidence gives, no two copies disagree on a share, the 70 prefix files hash
identically everywhere, and slices 579 and 606 remain the only UNRESOLVED ones.

*Round 4 (`G5-round4-read-gpt-6-astra.md`, of 768cc0930): duplicate shares and rule counts closed; two
gaps in the G4 verdict.* (1) It trusted the aggregates mismatching_parents and red_all: on the real
f01-jjpzl7/s0of1920 record, only per_cell[0].mismatches set to 1, or only red_controls[0].went_red set to
false, still passed. Every aggregate the verdict reads is now recomputed from the records it summarises
(enum2/replay-398.py's summarize() and main(): sampled, processed, children and mismatches summed over
per_cell; per_level the per-cell sums of its level; stages_checked and stages_ok from stages; red_all from
red_controls; all_identical from those), and an aggregate that disagrees with its details fails. (2) It
required all_identical before EMPTY, but the producer defines all_identical as bool(entries), false when
nothing is sampled, so a genuine empty slice was refused: EMPTY is now decided first, from verified
emptiness (a slice-mode replay that exited nonzero, no parent sampled and no per-cell record, stage checks
passed, every cell of the slice above the slice level without a parent, every share 0), and all_identical
is required for PASS only. Controls: `g5close.py` C9 (both detail-only mutations on a copy of the real
record: the landed tool (768cc0930) accepts them, the fixed one refuses them) and C10 (a genuine EMPTY
slice made by the runbook itself, on (16,41) sliced 128 ways, and one built with the producer's own
summarize([], ...): the landed tool refuses them, the fixed one accepts them; the same evidence with a
share of one graph is refused). The fleet audit rerun (`runs/u23-fleet-audit.txt`, 663 slices from 45
workers): nothing fails but the 1,257 missing slices; all 663 G4 labels are what their evidence gives with
every aggregate recomputed from its details; slices 579 and 606 remain the only UNRESOLVED ones.

*Round 5 (`G5-round5-read-gpt-6-astra.md`, of 7b3edd5c0): the aggregates closed; one gap, failing
closed.* The EMPTY decision read the final summary entries, so a genuine empty slice whose (13,28) the
driver had resumed (its parent fields removed) was refused as "unconfirmed" although summary_audit had
recovered that cell's parent record from the pushed history. The EMPTY decision now reads the parent
records summary_audit accepted (the final entry, or the recovered earlier version): a resumed cell with no
recoverable history is still unconfirmed, and a recovered record with parents still makes the slice not
empty. Controls: `g5close.py` C11 (the reader's reproduction on C10's empty slice: refused by the landed
tool (7b3edd5c0), accepted by the fixed one; with no history, and with a history record showing parents
in (13,28): refused by both). The fleet audit refreshed (`runs/u23-fleet-audit.txt`, 744 result
directories from 46 workers, 743 slice indices, one slice pushed twice with agreeing copies): nothing
fails but the 1,177 missing slices; all 744 G4 labels are what their evidence gives; four slices are now
UNRESOLVED, the same way as 579 and 606: 1354 (worker f11-bqjl8k, 9 resumed cells) and 1773 (worker
f46-s4mdou, 26 resumed cells) were restarted too, and their final summaries record neither those cells'
parents nor their level-12 shares.

*Round 6 (`G5-round6-read-gpt-6-astra.md`, of cca1769c8): round 5 closed; one more fail-closed case, and
its family.* EMPTY was decided per copy, before the copies of a slice were merged, so two complementary
copies of an empty slice (each resuming cells the other records fresh) were refused, each for the other's
cells. A copy whose only obstacle to EMPTY is unconfirmed cells is now PENDING, decided with the fleet
from the parent records every copy accepted. Hunting the rest of the family (copies, recovered history,
shares, resumed cells, labels) found three ways to accept a wrong run, now refused: copies of one slice
whose accepted parent records for a cell differ (only their counts, files and shares had been compared);
copies with different G4 results, or replayed in the same mode from different manifests (their
fingerprints); and a G4 replay whose per-cell parent counts are not the summary's (each per_cell row's
parents_in_cell must be the parent count the summary accepted for that cell, it samples no more, and a
slice-mode replay replays no prefix cell; on the fleet's 780 result directories, 23,178 rows agree and
none differs). Controls: `g5close.py` C12 (the reader's reproduction in both argument orders: refused by
the landed tool, accepted by the fixed one; neither copy recording (13,28), complementary copies with one
recording parents in (13,29), and copies whose shares disagree: refused by both in both orders; a fleet
record's per_cell parents raised by one: accepted by the landed tool, refused by the fixed one).

*Round 7 (`G5-round7-read-gpt-6-astra.md`, of 57daa7c14): round 6 closed; one fail-open gap, fixed
structurally.* The per-cell binding compared a replay's rows with the copy's own parent records only,
so a copy that had resumed the cell escaped it although another copy recorded it (the reader's (11,17)
replayed with 31,128 parents instead of 31,127 passed in both argument orders). Now every binding that
uses parent evidence runs in the fleet pass against the MERGED records: for a cell above the slice level,
the accepted records of every copy of its slice; for a prefix cell, those of every slice (the prefix is
the same in all of them); disagreeing records fail, and a binding with no record anywhere stays
UNRESOLVED. That covers the per-cell rows, the G4 records of the slice files (bound to the slice's merged
shares, so a copy that records no share no longer escapes either) and the EMPTY confirmation. The reads
that stay per copy are local by design and marked so in the code: a record's own validation before it
becomes evidence, the replay summary's own consistency, facts of a replay row itself, and a local record
that REFUTES emptiness. On the fleet's 887 result directories (57 workers) the merged bindings raise no
problem (the one problem is the 1,039 slices not yet run); the replay rows of the four restarted slices
(579, 606, 1354, 1773: 61 rows) are now UNRESOLVED, since no copy records their cells, which brings the
fleet's unresolved lines to 73, all from those four slices. Controls: `g5close.py` C13 (the reader's reproduction in both orders, accepted by the
landed tool and refused by the fixed one; the same copy alone, UNRESOLVED; the prefix path, another
worker's full-mode slice mutated the same way and audited with f01's slice, refused; a copy recording no
share whose G4 slice record is one larger, refused against the other copy's share).

*Round 8 (`G5-round8-read-gpt-6-astra.md`, of a3a38e37f): round 7 closed; one fail-open gap, and its
family.* The sampling bound on a G4 replay row ran only when its parents_in_cell and sampled were both
nonnegative integers, and the binding then compared parents_in_cell with the accepted record by Python's
numeric equality, so a float or boolean parent count skipped the bound and still matched (31127.0 == 31127,
True == 1): the reader's (11,17) row with parents_in_cell 31127.0 and 31,128 samples of its 31,127 parents,
the sampled totals moved to agree, passed with no problem, where the integer 31127 is refused. A row whose
parents_in_cell or sampled is not a nonnegative integer is now a problem naming the cell and both values,
and is neither bounded nor bound, so the bound and the binding compare integers only. Hunting the family
(every count read from a summary, replay summary, fingerprint, manifest, hashes.json, per_level, share or
stage record that is compared, summed or used as a bound: each is checked first, or compared only with a
value that was) found two more places where a check that skips a non-integer let an equality accept it: a
summary level entry written (23, 65.0) counted as listed (65.0 == 65) but was never audited, since only
entries with integer cells are read (the target entry with one child passed, and the fleet report counted
no child at the target); and a parent source's level [12, 20.0] equalled [12, 20], and the float became the
share's key and so the slice file's name, so the G4 record of that file was never compared (UNRESOLVED
only). A level entry's n and m, and a source's level and the recorded parent edge counts, must now be
nonnegative integers. Controls: `g5close.py` C14 (on copies of the fleet record f01-jjpzl7/s0of1920: the
reader's (11,17) with parents_in_cell 31127.0 and 31,128 samples, and (16,36) with parents_in_cell true, and
1.0, and 2 samples of its one parent, each accepted by the landed tool (a3a38e37f) and refused by the fixed
one; an untouched copy clean; the two family cases, where the landed tool raises no problem (the second only
an UNRESOLVED line) and the fixed one refuses both). The fleet audit refreshed
(`runs/u23-fleet-audit.txt`, 932 result directories from 62 workers, 926 slice indices): nothing fails but
the 994 missing slices, all 932 G4 labels are PASS, and the 73 UNRESOLVED lines all come from slices 579,
606, 1354 and 1773; on these 932 directories the landed and the fixed tool print identical output (their
28,052 replay rows, 86,676 level entries and 167,255 parent sources are all integers). The target cell
(23,65) has one child, in slice 50, which the filter-only prune kept as unknown (so in the round-7 log too).
