# GP-10 contract: the minimal forbidden unit-distance graphs on 10 vertices

Binding for every builder, checker and run in `research/gp-10/`. Written 2026-09-24 by
claude-answering-alexeev-u22 before any producer exists. Amendments go in Section 10 of this file,
dated, never in a brief. A brief that disagrees with this file is wrong.

The question is printed in Alexeev, Mixon and Parshall, arXiv:2412.11914, Section 6: extend Globus
and Parshall (GP, "Small unit-distance graphs in the plane", Bull. Inst. Combin. Appl. 90 (2020)
107-138, arXiv:1905.07829) from 9 to 10 vertices. OEIS A308349 (the number of minimal forbidden
graphs on n vertices) currently ends 1, 1, 1, 3, 13, 55 at n = 4..9.

## 0. The claim, and the only two forms it may take

- **Full claim** (only when every gate in Section 8 is green): "A graph on at most 10 vertices is a
  unit-distance graph if and only if it contains none of the 74 GP graphs and none of the N graphs
  in `L10.g6`." N and the file are produced by the checker, never typed by hand.
- **Conditional claim** (when UNKNOWN is non-empty): the same sentence prefixed by "Unless one of
  the k graphs in `UNKNOWN.g6` is not unit-distance," with L10 the checker's list and k stated.
  Nothing else may be claimed, in any document, page, email or commit message.

## 1. Definitions

- Graphs are simple, undirected, finite. Isomorphism classes are represented by graph6 strings
  canonically labelled by nauty `labelg` 2.8.8 with default options. "Subgraph" means NOT
  necessarily induced: delete any vertices and any edges. A map H -> G witnessing a subgraph is an
  injective vertex map sending every edge of H to an edge of G.
- A **unit-distance graph (UDG)** is a graph G with an injective map p: V(G) -> R^2 such that
  |p(u) - p(v)| = 1 for every edge uv. Non-edges MAY be at distance 1. A graph that is not a UDG is
  **forbidden**. A forbidden graph is **minimal** if every proper subgraph is a UDG.
- **F9** is the 74 graphs of `research/unit-distance-22/data/forbidden-74.json` (same order as
  `forbidden-74.g6`; GP's Appendix A: 1, 1, 1, 3, 13, 55 graphs on 4..9 vertices). **F7** and
  **F8** are its members on at most 7 and at most 8 vertices (6 and 19 graphs). "F-free" always
  names which list is in force.
- **B10** is the set of biconnected 10-vertex graphs that are F9-free. It is frozen in
  `data/B10.g6` (sorted bytewise, canonical, one per line, trailing newline) with its sha256 in
  `data/SHA256SUMS`. Measured 2026-09-24: 33,162 graphs, out of 9,743,542 biconnected 10-vertex
  graphs (`nauty-geng -Cq 10`; OEIS A002218(10) = 9,743,542).
- **Control sets** (Section 7): **B8'** = biconnected 8-vertex F7-free graphs; **B9'** =
  biconnected 9-vertex F8-free graphs. Frozen the same way in `data/`.

## 2. The lemmas everything rests on (proofs in `PROOFS.md`, each must be written before use)

- **L-block.** A graph is a UDG iff each of its blocks (biconnected components and bridges) is.
  (Chilakamarri and Mahoney 1995; GP.) Consequence: a 10-vertex F9-free graph that is not
  biconnected is a UDG, by GP's theorem applied to its blocks, all of which have at most 9 vertices.
- **L-mono.** A subgraph of a UDG is a UDG (restrict p). A graph containing a forbidden subgraph
  is forbidden.
- **L-min.** A graph G in B10 is minimal forbidden iff G is forbidden and G - e is a UDG for every
  edge e. (Deleting a vertex gives a 9-vertex F9-free graph, a UDG by GP; any proper subgraph is
  contained in some G - e or some G - v.)
- **L-complete.** If every graph in B10 is decided, the minimal forbidden 10-vertex graphs are
  exactly the minimal ones among the forbidden graphs of B10, and a graph on at most 10 vertices is
  a UDG iff it contains no member of F9 or L10. (Proof via L-block, L-mono and GP.)
- **L-TU.** For each gadget in `research/unit-distance-22/data/tu-gadgets.json` with its
  distinguished non-adjacent pair {a,b}: every unit-distance embedding has |p(a) - p(b)| = 1
  (`research/unit-distance-22/check/PROOFS.md`). Hence if G contains the gadget via a map with
  {a,b} non-adjacent in G, then G is a UDG only if G + ab is. **A bare gadget hit is never a
  refutation** (at u(22) it was, because 61 edges was the proved maximum; here there is no
  edge-count argument). Only a chain ending in a refutation of the augmented graph is.
- **L-frame.** Any real embedding can be moved by a rigid motion so a chosen EDGE (a,b) lands on
  p(a) = (0,0), p(b) = (1,0). A non-edge may never be the frame, and no third point may be pinned.
- **L-sat.** Distinct real points have squared distance > 0. So adjoining t * d2(u,v) - 1 (t a
  fresh variable, d2 the squared distance polynomial) for any set S of pairs loses no real
  injective embedding. A Nullstellensatz identity in the resulting ring proves "no real injective
  embedding"; it is NOT a statement about complex points with isotropic differences.

## 3. Record format (JSON lines, one record per graph, canonical g6)

```
{"g6": "<canonical graph6>", "verdict": "embedded" | "refuted" | "unknown", "cert": {...}}
```

Every record is exactly one of these. There is no `tu`, `pass` or `forbidden` verdict in a GP-10
certificate file (forbidden-list witnesses live only in the input-freeze replay, Section 6).

### 3.1 `embedded` certificates

- **E-exact**: `{"type": "exact", "field": {"minpoly": [c0, c1, ..., cd], "interval": [lo, hi]},
  "coords": [[X_0, Y_0], ..., [X_{n-1}, Y_{n-1}]]}`. `ci` are integers (ascending powers, cd != 0),
  `lo < hi` are rationals as strings `"p/q"`, each X_i, Y_i is a list of d rationals (ascending
  powers of theta, reduced mod minpoly). theta is any real root of minpoly in [lo, hi].
  Checker: (1) minpoly(lo) * minpoly(hi) < 0 exactly (a real root exists in the interval);
  (2) for every edge uv, (X_u - X_v)^2 + (Y_u - Y_v)^2 - 1 reduces to the zero polynomial mod
  minpoly (so it vanishes at every root, whether or not minpoly is irreducible); (3) for every
  pair u != v, (X_u - X_v)^2 + (Y_u - Y_v)^2 evaluated by certified interval (ball) arithmetic
  over the whole of [lo, hi] (refine the interval by bisection, keeping a sign change, as needed)
  is bounded away from 0. The labelling of coords is the labelling of the canonical g6.
- **E-ptr**: `{"type": "super", "g6": "<H canonical g6>", "map": [m_0..m_{n-1}]}`: G is a
  subgraph of H via v -> m_v, and H has an accepted `embedded` record in the same run, or H is a
  host in `hosts.jsonl` (each host is itself an E-exact record on any number of vertices, checked
  once). Pointer chains must be acyclic.

### 3.2 `refuted` certificates

- **R-tree**: `{"type": "tree", "witness": <udembed/udcheck refutation witness>}`, the exact
  format of `research/unit-distance-22` (field + proof tree of L0/L1a/L1b/L1c/L2/L3 nodes),
  verified by the trusted kernel `research/unit-distance-22/check/udcheck.py` verify_refutation
  (blind-built and mutation-tested for u(22)). Its moves are proved in
  `research/unit-distance-22/check/PROOFS.md` and AMP Section 4.
- **R-tu**: `{"type": "tu", "steps": [{"gadget": k, "map": [...], "pair": [a, b]}, ...],
  "end": <end>}`. Step i applies gadget k by an injective edge-preserving map into the graph as
  augmented by steps < i; `pair` is the image of the gadget's distinguished pair, non-adjacent at
  that moment; the step adds it as an edge. `end` is `{"forbidden": j, "map": [...]}` (member j
  of the list in force embeds into the final augmented graph) or `{"refuted": "<H g6>", "map":
  [...]}` (a graph with an accepted refuted record embeds into the final augmented graph).
- **R-null**: `{"type": "null", "frame": [a, b], "sat": [[u, v], ...], "cofactors": {...}}`.
  The CHECKER builds the polynomial system itself from the g6: variables x_i, y_i for vertices
  other than a, b (p(a) = (0,0), p(b) = (1,0), (a,b) must be an edge); one equation per edge other
  than ab; one Rabinowitsch polynomial t_k * d2(u_k, v_k) - 1 per pair in `sat`. The certificate
  gives, for each generator (keyed `"e:u,v"` or `"s:u,v"`), a cofactor polynomial with rational
  coefficients in a documented sparse encoding, and the checker verifies by plain expansion in a
  system independent of whatever produced it that sum(cofactor * generator) = 1 exactly. Any
  stated system that differs from the regenerated one is a rejection.
- **R-real**: as R-null, but the identity proves sum(cofactor * generator) = f, and the record
  also proves f has no real zero, by one of: (a) f involves one variable and the checker's own
  Sturm count on R is 0; (b) `{"sos": {"c": "p/q", "squares": [[w_i, q_i], ...]}}` with c > 0,
  w_i > 0 rationals, and f = c + sum w_i q_i^2 verified by expansion.
- **R-ptr**: `{"type": "sub", "g6": "<H canonical g6>", "map": [...]}`: H is a subgraph of G via
  the map, and H is in F9 (by index, for the frozen lists only) or has an accepted `refuted`
  record in the same run. Acyclic.
- New certificate types (for example parametric or interval-existence ones) are added only by an
  amendment in Section 10 that gives the lemma, its proof, the checker branch and its red
  fixtures.

### 3.3 `unknown`

`{"g6": ..., "verdict": "unknown", "cert": {"reason": "...", "budget": {...}}}`. A timeout, crash,
OOM or exhausted search is `unknown`, never a dropped line. Every unknown g6 is listed in
`UNKNOWN.g6`, and the unknown rate is always reported with the budget that produced it.

## 4. The checker (`check/`)

Built blind from this file (and the trusted u(22) kernel it names), importing no producer code.
It takes a run directory and emits ACCEPT or REJECT with a reason per record, plus:

1. **Coverage**: the set of g6 strings with records equals the frozen input set exactly (no
   missing, no extra, no duplicates); totals embedded + refuted + unknown = |input|.
2. **Consistency**: no graph is both embedded and refuted (fatal); no refuted graph is a
   subgraph of an embedded graph among those it is asked to cross-check (a sampled L-mono check).
3. **L10 derivation**: for every refuted G, and every edge e, decide G - e: if not biconnected,
   it is a UDG by L-block (verify the block structure); else canonicalise it (labelg) and look up
   its verdict. G is minimal iff all G - e are embedded or non-biconnected. The checker writes
   `L10.g6` and the count. If any needed G - e is unknown, G is reported as "minimal unless
   <g6> embeds" and the claim is conditional.
4. **Controls first**: refuses to report on B10 unless the control reports (Section 7) are
   present and accepted in the same run tree.

Red fixtures, each one field away from a real positive, all must be rejected: a `tu` verdict; an
R-tu whose final forbidden map is not edge-preserving; an E-exact with one coordinate perturbed;
an E-exact with two coincident points (edges fine); an interval without a sign change; an R-null
whose frame is a non-edge; an R-null with an extra non-edge-equals-1 generator; an R-null with a
cofactor changed in one coefficient; an R-real with c = 0; an E-ptr whose map is not injective; a
pointer cycle; a coverage file with one graph missing; one duplicated; a minimality claim where
one G - e is refuted.

## 5. Producers (`embed/`, `refute/`, `drive/`)

Producers may use any heuristic, floats, random search, CAS output or LLM guesswork. Nothing they
say is trusted; only the checker's ACCEPT counts. Rules: deterministic per graph (seed from
sha256 of the canonical g6, never a line number); one record per graph, flushed as written;
per-graph time and memory limits; resumable; a crash on one graph is an `unknown` record for
that graph. External tools (msolve, Singular, z3) are consulted only through wrappers that
pre-expand every polynomial (msolve misparses parenthesised powers and silently returns [1]),
accept only an exact positive line, never an exit code, and ship a red control proving the
wrapper can say "no".

## 6. Input freeze

`data/B10.g6`, `data/B8p.g6`, `data/B9p.g6`, with sha256, and a replay record: every graph removed
by the F-filter carries a forbidden witness (member index + map) that an independent script
verifies (streamed, chunked). Anchors: geng counts equal OEIS A002218 (7,123; 194,066;
9,743,542); B8 with F9 gives 366 and B9 with F9 gives 2,984 (GP's printed numbers). At least one
independent recount of B10 by code sharing nothing with `udfilter` must agree by sorted-list
sha256, not only by count.

## 7. Controls (pre-registered 2026-09-24, before any producer runs)

1. **n = 8, answer withheld.** Run the full pipeline on B8' with F7 in force. PASS iff every graph
   is decided and the checker's derived minimal list equals, up to isomorphism, exactly the 13
   eight-vertex members of F9 (indices by vertex count in forbidden-74.json).
2. **n = 9, answer withheld.** Same on B9' with F8 in force. PASS iff the derived list is exactly
   the 55 nine-vertex members of F9, and every graph of B9' that is F9-free is embedded (both
   directions).
3. **n = 10, named graphs.** Petersen, Golomb, the pentagonal prism C5 x K2 and the unique
   20-edge graph of B10 (`IISpZATaw`, identical to AMP's extremal 10-vertex graph in
   `sources/amp/anc/graph6.txt`) must be embedded, by the producers' general search and not by a
   lookup of AMP's or GP's coordinates (library hits are allowed in production but are reported
   separately and do not count for this control); the Moebius ladder on 10 vertices (15 edges, cubic;
   stated non-unit-distance on MathWorld's "Unit-Distance Graph" page, pers. comm. B. Alexeev,
   2025-08-09) must be refuted, directly or by pointer.
4. **Regressions**: K4, K_{2,3} and the five forbidden-74 graphs with complex but no real
   embeddings (json indices 4, 9, 10, 17, 18) are refuted when fed in as inputs with an empty list
   in force; the Moser spindle embeds.
5. **Timing model and predicted counts** are written to `PREDICTIONS.md` before the B10 run
   starts, so the run can surprise us.

A control that fails stops the run until the failure is explained in LABNOTES.md.

## 8. Gates

| gate | requirement |
|---|---|
| G0 | inputs frozen, anchors match, witness replay complete, independent recount agrees |
| G1 | checker built blind, every red fixture rejected, self-test committed |
| G2 | controls 7.1 to 7.4 PASS on the checker, with PREDICTIONS.md committed first |
| G3 | every B10 graph has a record; checker ACCEPT on all; UNKNOWN listed exactly |
| G4 | L10 derived by the checker; each member also refuted by a second, differently-typed certificate where one can be found (reported as a count, not required) |
| G5 | a cross-model read of PROOFS.md and of the checker's soundness branches (Kimi, via waste-drop, maths-only bundle) with every finding answered in writing |
| G6 | write-up generated from checker output only; refuses to run while G0-G5 are open |

## 9. Environment

Python from `~/tools/pyenv-gp10` only (frozen: `FREEZE.txt` in this directory; SymPy's ground
types change when python-flint is present, so the checker records `sympy.__version__`, the flint
version and `SYMPY_GROUND_TYPES` in every report). nauty 2.8.8. Heavy runs never on <host>
beyond two niced processes and 1 GB each. Scratch outside the repository.

## 10. Amendments

1. **2026-09-24, controls down to n = 4** (claude-answering-alexeev-u22, before any producer ran).
   Control 7.0: for n = 4, 5, 6, 7, run the full pipeline on `data/B<n>p.g6` (biconnected n-vertex
   graphs free of the F9 members on at most n - 1 vertices; 3, 7, 16 and 60 graphs) with those
   members in force. PASS iff every graph is decided and the derived minimal list equals exactly the
   F9 members on n vertices (1, 1, 1, 3 graphs). Together with 7.1 and 7.2 this re-derives the whole
   classification up to 9 vertices from our own certificates (`PROOFS.md` Section 5), so GP's theorem
   becomes an independent agreement rather than a premise. G2 now requires 7.0 as well.

2. **2026-09-24, correction found by the blind checker** (reported in `check/REPORT.md`, "Contract
   ambiguity"). Section 4.3 said a refuted G with an unknown G - e is "minimal unless <g6> embeds".
   That is backwards: by L-min such a G is minimal if every unknown deletion embeds, i.e. unless one of
   them is forbidden. The checker implements L-min and reports these as
   `minimal_if_all_listed_deletions_embed`; that wording is now the contract's. Also: the checker's
   control profiles predate amendment 1 and must be extended to B4p to B7p before control 7.0 runs.
3. **2026-09-24, clarifications from the checker's soundness audit** (`check-audit/REPORT.md`: 0 BLOCKER,
   1 MAJOR = amendment 1's missing profiles, 2 MINOR). Rational strings are `[+-]?digits(/digits)?` with a
   positive denominator and no whitespace (FORMAT.md is binding on spelling). R-real's f may be a nonzero
   constant as well as univariate with no real root; both give the same contradiction.
4. **2026-09-24, forbidden-list indices** (a mismatch between `check/FORMAT.md`, global F9 indices, and
   `refute/FORMAT.md`, indices within the list passed). Binding: an index is the zero-based index in
   `forbidden-74.json`. Every list in force is a prefix of that file (it is sorted by vertex count: prefixes
   of length 1, 2, 3, 6, 19, 74 for n <= 4, 5, 6, 7, 8, 9), and producers are only ever given such a
   prefix, so the two readings coincide; a producer given anything else is misconfigured. A TU chain has at
   least one step; direct containment of a list member is an R-ptr, not a zero-step chain.
5. **2026-09-24, R-null-dag and R-real-dag** (proposed by the refuter, `refute/PROOFS.md`, for F9 index 39 =
   GP's F(9,14,19), whose single cofactor identity expands to 446,203 terms; accepted by the lead). A
   certificate `{"type": "null-dag" | "real-dag", "frame", "sat", "rows": [...], + for real-dag the same
   f/sturm/sos fields as R-real}`. The checker regenerates the generators exactly as for R-null. Each row is
   `{"poly": P_k, "cofactors": {key: c}}` where each key is an original generator key (`e:u,v`, `s:u,v`) or
   `aux:j` for a strictly earlier row j < k; the checker verifies by plain expansion that
   P_k = sum(c * source). By induction every P_k lies in the ideal generated by the regenerated system (the
   same ideal R-null uses), so: null-dag requires the last row's P to equal 1 (then 0 = 1 at any real
   embedding, exactly as R-null); real-dag requires the last row's P to equal f and proves f has no real
   zero exactly as R-real. Reject forward or self references, unknown keys, extra fields, non-canonical
   sparse terms, more than 256 rows, and any failed identity. Soundness is PROOFS.md's R-null / R-real
   argument plus this induction; nothing about Groebner bases or normal forms is trusted.
6. **2026-09-25, wording from the G5 cross-model read** (waste-drop task 0018, Arturo / Kimi k3: checker sound,
   0 BLOCKER, 0 MAJOR, 5 MINOR; every finding answered in `G5-RESPONSE.md`). No acceptance behaviour changes; the
   checker stays at sha256 `d717816bde784fae…` for the B10 result. (a) Section 3.1 E-exact step (3): "over the
   whole of [lo, hi]" means on a subinterval of [lo, hi] that still contains the certified root, reached by
   bisection that keeps a sign change; the checker rejects if its bisection budget runs out first. (b) Section 9:
   a run's environment is its report's `environment` field (interpreter, SymPy and python-flint versions,
   executable); `FREEZE.txt` is the producers' record, not a checker input. (c) Producer note: K_{2,3}-type
   obstructions are real, not complex (the complex variety is non-empty), so they go through R-real, real-dag
   or R-tree, never R-null.
