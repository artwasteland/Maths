# REPORT: stage 3 for (13,23)

Date: 2026-09-06 AEST.  Python: `~/tools/pyenv-maths/bin/python`, SymPy 1.14.0,
pynauty 2.8.8.1, python-sat 1.9.dev15.

## Result

The `(13,23)` census is complete.  The existence SAT produced 441 labelled block assignments
in its sound canonical-row and generator-lex slice, then returned UNSAT.  Nauty identifies
exactly one coloured point-block incidence class.  `chiro/chirosat.py` independently returned
`pseudoline` on that canonical class.  The exact realizer returned `no-realization`, and the
blind checker independently reconstructed its characteristic-zero saturated ideal and obtained
the reduced Groebner basis `{1}`.

Therefore this establishes `t3(13) <= 22` with a checkable certificate, hence `t3(13) = 22`
using the known `(13,22)` arrangement.  The upper bound rests on CONTRACT Section 1's PTS
reduction, the exhaustive incremental SAT census, nauty canonical incidence labelling, the
independent chirotope recheck, and the independently recomputed exact saturation certificate.

## Step 1: all pseudoline-admitting PTS(13,23)

| Case | Terminal result | Labelled models | Nauty classes | `chirosat.py` pseudoline checks | Wall (s) |
|---|---:|---:|---:|---:|---:|
| (13,23) | UNSAT after enumeration | 441 | 1 | 1 of 1 | 2933.493624 |
| (13,24) control | UNSAT on first call | 0 | 0 | not applicable | 589.799140 |
| (14,28) control | UNSAT on first call | 0 | 0 | not applicable | 1125.706361 |

The command options for the target were
`13 23 --all-models realize/pts-13-23-labelled.pts --timeout 14400`.  The backend was one
persistent PySAT `Cadical153` instance and no proof was logged.  Every reported labelled model
was obtained by a SAT call, checked by `verify_model`, appended in CONTRACT PTS format, and
blocked on its complete block-variable assignment.  After a model was found, its canonical-row
relabelled copies were supplied as full assumptions to accelerate the same incremental solver;
each copy was separately SAT-checked and separately blocked.  The final unassumed call returned
UNSAT.  This preserves discovery of a new isomorphism class and does not infer copies from the
first witness.

The canonicalizer used pynauty's canonical labelling and certificate of the bipartite incidence
graph with the point and block vertices in different colour cells.  A 50-random-relabel control
returned the identical canonical PTS each time.  The previously saved
`chiro/scratch/exist-13-23.pts` has the same nauty certificate and is present among the classes.
The sole leave type is `0,0,0,0,2,2,2,2,2,2,2,2,2`.

Artifacts and hashes:

- `pts-13-23-labelled.pts`: 441 lines, sha256
  `eeee42ba83f9f09db12aba8737f8906b4048788b8b30088ffc0a2d6be76c5cbf`.
- `pts-13-23-pseudoline.txt`: 1 line, sha256
  `bd30d3d2b0a501715bebb94b82cd47d4bac0360c46409f0e157df68393673848`.
- `exist.py` used for the completed target run: sha256
  `297a1938708332b7df30a61330cfd4f9daedbe5b4ebe7e756480136ebbeb0946`.
- `chiro-verifications-13-23.jsonl`: 1 `pseudoline` result.  Its instance record took
  0.234202 s after 0.400817 s base encoding and 0.279189 s solver initialization.
- `pts-13-23-pseudoline.manifest.json` records the count, hashes, options, wall time, leave
  histogram, pynauty version, and known-model membership.

## Step 2: exact realizer controls

| Configuration | Verdict | Certificate kind | Checker accept | Prover / checker wall (s) |
|---|---|---|---:|---:|
| Fano (7,7) | no-realization | saturated basis `{1}` over Q | yes | 0.021398 / 0.016488 |
| Pappus 9_3 | real | exact rational projective coordinates | yes | 0.298841 / 0.043938 |
| Desargues 10_3 | real | exact rational projective coordinates | yes | 0.503080 / 0.053330 |
| Kantor 10_3 | no-realization | saturated basis `{1}` over Q | yes | 1.536287 / 1.153398 |
| Pegg (15,31) | real | exact coordinates in Q(alpha) | yes | 17.156005 / 13.176412 |
| BGS (14,27) SAT model | no-realization | saturated basis `{1}` over Q | yes | 1.806715 / 1.531931 |

For Pegg, `alpha = cot(pi/15)` is represented by
`alpha^8 - 28 alpha^6 + 134 alpha^4 - 92 alpha^2 + 1`, with real isolating interval
`(47/10,24/5)`.  The checker reduces every determinant modulo that polynomial.  All real
certificates were checked on every triple and every point pair.  The BGS control is stronger
than merely non-real: its certificate excludes a realization over every characteristic-zero
field.  It makes no claim in characteristic `p`.

The construction engine fixes four PTS-independent points to the standard projective frame,
uses exact line intersections whenever two known block lines determine a point, and introduces
one parameter on one known line.  A free point uses two parameters, but a negative certificate
is withheld unless all necessary projective charts have been covered; this did not arise in any
completed control or target.  The remaining block determinants generate the ideal.  Every
non-block determinant is a non-degeneracy polynomial.  For these PTS sizes this also enforces
nonzero and pairwise distinct projective points because every pair belongs to many non-block
triples.  The full non-degeneracy product is normalized, deduplicated up to rational units, and
reduced incrementally modulo the block Groebner basis before the Rabinowitsch equation is added.
This is algebraically the same localization and avoids expanding an enormous product.

`selfcheck.py` passed both green cases and both required red cases.  Changing a valid rational
coordinate was rejected at determinant `(2,4,8)`.  Dropping one PTS block from the stated ideal
was rejected before the algebra was trusted.

## Step 3: (13,23) through stage 3

| Verdict | Count |
|---|---:|
| real | 0 |
| no-realization | 1 |
| complex-only | 0 |
| unknown | 0 |

The prover took 1.753268 s on the canonical class.  The blind checker took 1.698845 s and
accepted.  The certificate has one construction parameter, six residual block equations,
263 non-degeneracy determinants, full-product remainder zero modulo the block ideal, and reduced
saturated basis `{1}`.  `verdicts-13-23.jsonl` has sha256
`6e7e3b650b85644759b4c99461861af206902538112a3ff6525cc032e627cd1b`.

## Exact `chiro/exist.py` diff

```diff
--- /tmp/orchard-exist.py.before	2026-09-05 22:47:44.251281876 +1000
+++ chiro/exist.py	2026-09-05 23:18:34.853579209 +1000
@@ -955,6 +955,139 @@
     }
 
 
+def row_orbit_block_vectors(encoding: ExistenceEncoding, pts: PTS) -> list[tuple[bool, ...]]:
+    """All canonical-row relabellings of one PTS that obey the encoded lex leaders."""
+    reduction = encoding.reduction
+    triples = encoding.chiro.triples
+    triple_index = encoding.chiro.index
+    highest_bit = len(triples) - 1
+    blocks = set(pts.blocks)
+    covered = {pair for block in blocks for pair in itertools.combinations(block, 2)}
+    degrees = [
+        sum(tuple(sorted((point, other))) not in covered for other in range(pts.v) if other != point)
+        for point in range(pts.v)
+    ]
+    generators = row_stabiliser_generators(reduction, fix_point_one=False)
+    if not encoding.counts["lex_generators"]:
+        generators = []
+    generator_image_bits = [
+        [1 << (highest_bit - triple_index[apply_to_triple(permutation, triple)]) for triple in triples]
+        for permutation in generators
+    ]
+    vectors: set[int] = set()
+    target_pairs = [(block[1], block[2]) for block in reduction.row_blocks]
+    for root, degree in enumerate(degrees):
+        if degree != reduction.min_leave_degree:
+            continue
+        source_pairs = [tuple(point for point in block if point != root) for block in pts.blocks if root in block]
+        source_leave = [
+            point for point in range(pts.v)
+            if point != root and tuple(sorted((root, point))) not in covered
+        ]
+        for ordered_pairs in itertools.permutations(source_pairs):
+            for flips in itertools.product((False, True), repeat=len(source_pairs)):
+                for ordered_leave in itertools.permutations(source_leave):
+                    relabel = {root: 0}
+                    for source, target, flip in zip(ordered_pairs, target_pairs, flips):
+                        left, right = source[::-1] if flip else source
+                        relabel[left], relabel[right] = target
+                    relabel.update(zip(ordered_leave, reduction.row_leave_neighbours))
+                    image = {tuple(sorted(relabel[point] for point in block)) for block in blocks}
+                    indices = [triple_index[triple] for triple in image]
+                    vector = sum(1 << (highest_bit - index) for index in indices)
+                    if all(vector <= sum(bits[index] for index in indices) for bits in generator_image_bits):
+                        vectors.add(vector)
+    return [
+        tuple(bool(vector & (1 << (highest_bit - index))) for index in range(len(triples)))
+        for vector in sorted(vectors)
+    ]
+
+
+def _all_models_child(connection, encoding: ExistenceEncoding, output: Path) -> None:
+    """Persistent incremental enumeration worker, isolated for hard timeout."""
+    models = 0
+    solver = Cadical153(bootstrap_with=encoding.clauses)
+    try:
+        with output.open("w", encoding="ascii") as handle:
+            seen: set[tuple[bool, ...]] = set()
+            while solver.solve():
+                true_vars = {literal for literal in (solver.get_model() or []) if literal > 0}
+                pts, _witness, _leave = verify_model(encoding, true_vars)
+                for vector in row_orbit_block_vectors(encoding, pts):
+                    if vector in seen:
+                        continue
+                    assumptions = [
+                        variable if value else -variable
+                        for variable, value in zip(encoding.block_variables.values(), vector)
+                    ]
+                    if not solver.solve(assumptions=assumptions):
+                        raise RuntimeError("an isomorphic canonical-row copy unexpectedly failed SAT")
+                    model_vars = {literal for literal in (solver.get_model() or []) if literal > 0}
+                    copy, _copy_witness, _copy_leave = verify_model(encoding, model_vars)
+                    if tuple(triple in set(copy.blocks) for triple in encoding.chiro.triples) != vector:
+                        raise RuntimeError("assumption solve returned the wrong block assignment")
+                    handle.write(copy.line + "\n")
+                    handle.flush()
+                    models += 1
+                    seen.add(vector)
+                    solver.add_clause([-literal for literal in assumptions])
+                    if models % 500 == 0:
+                        print(f"all-models: {models} block assignments", file=sys.stderr, flush=True)
+        connection.send((models, solver.accum_stats()))
+    finally:
+        solver.delete()
+        connection.close()
+
+
+def enumerate_all_models(
+    encoding: ExistenceEncoding,
+    encode_seconds: float,
+    output: Path,
+    timeout: float,
+) -> dict[str, object]:
+    """Enumerate distinct labelled block vectors with one incremental solver.
+
+    Chirotope signs are deliberately absent from the blocking clause: a PTS is
+    written once even when it supports several chirotopes.  The existing row
+    and lex constraints are sound but incomplete symmetry breaking, so the
+    output can still contain isomorphic labelled PTSs; stage 3 canonicalises
+    their coloured incidence graphs with nauty.
+    """
+    import multiprocessing
+
+    total_started = time.perf_counter()
+    output.parent.mkdir(parents=True, exist_ok=True)
+    context = multiprocessing.get_context("fork")
+    parent, child = context.Pipe(duplex=False)
+    process = context.Process(target=_all_models_child, args=(child, encoding, output))
+    process.start()
+    child.close()
+    if not parent.poll(timeout if timeout > 0 else None):
+        process.kill()
+        process.join()
+        models = sum(1 for line in output.read_text(encoding="ascii").splitlines() if line.strip())
+        stats: dict[str, int] | None = None
+        verdict = "TIMEOUT"
+    else:
+        try:
+            models, stats = parent.recv()
+        except EOFError as exc:
+            process.join()
+            raise RuntimeError(f"all-models worker exited with code {process.exitcode}") from exc
+        process.join()
+        verdict = "UNSAT"
+    return common_result(encoding, encode_seconds) | {
+        "backend": "pysat-cadical153-incremental",
+        "verdict": verdict,
+        "labelled_models": models,
+        "output": str(output.resolve()),
+        "proof_logged": False,
+        "timeout_seconds": timeout,
+        "solver_stats": stats,
+        "total_seconds": round(time.perf_counter() - total_started + encode_seconds, 6),
+    }
+
+
 def parse_text_model(text: str, nvars: int) -> set[int]:
     values: list[int] = []
     status = None
@@ -1249,6 +1382,11 @@
     parser.add_argument("--cnf-only", action="store_true")
     parser.add_argument("--phase-hint", action="store_true", help="pysat: known control PTS as initial phases")
     parser.add_argument("--hint-cube", action="store_true", help="pysat: assume the known control PTS first (encoding consistency check, not a search control)")
+    parser.add_argument(
+        "--all-models",
+        metavar="OUT_PTS",
+        help="incrementally enumerate every distinct labelled block assignment; no proof logging",
+    )
     parser.add_argument("--cubes", action="store_true", help="cube-and-conquer over the row of point 1")
     parser.add_argument("--list-cubes", action="store_true")
     parser.add_argument("--cube-index", type=int)
@@ -1276,6 +1414,13 @@
             raise ExistenceError("--corrupt-proof requires a standalone backend")
         if (args.phase_hint or args.hint_cube) and args.backend != "pysat":
             raise ExistenceError("--phase-hint and --hint-cube need --backend pysat")
+        if args.all_models is not None and (
+            args.cubes or args.list_cubes or args.cnf_only or args.corrupt_proof or args.drop_exact_b
+            or args.phase_hint or args.hint_cube
+        ):
+            raise ExistenceError(
+                "--all-models cannot be combined with cubes, CNF/proof controls, or hints"
+            )
         if args.cube_children is not None and (args.cube_depth != 2 or args.cube_index is None):
             raise ExistenceError("--cube-children requires --cube-depth 2 and one --cube-index")
         if args.mutate_drop_cube and args.cube_depth == 2 and args.cube_index is None:
@@ -1300,6 +1445,12 @@
             args.v, args.b, drop_exact_b=args.drop_exact_b, lex=not args.no_lex, degree=not args.no_degree
         )
         encode_seconds = time.perf_counter() - encode_started
+        if args.all_models is not None:
+            result = enumerate_all_models(
+                encoding, encode_seconds, Path(args.all_models), args.timeout
+            )
+            print(json.dumps(result, sort_keys=True), flush=True)
+            return 0
         if args.cnf_only:
             destination = Path(args.artifacts) / f"exist-{args.v}-{args.b}.cnf"
             destination.parent.mkdir(parents=True, exist_ok=True)
```

## What I was unsure about

The generic realizer is deliberately incomplete outside this completed census: a construction
requiring a genuinely free point can need several projective charts, and a positive-dimensional
or multivariate nontrivial saturated ideal can need stronger exact real algebra than the current
univariate isolation path.  Those cases return `unknown`, as required.  The `(13,23)` class and
all mandatory controls avoided that gap, so there are no hidden unknowns in the result above.
I did not start the optional `(14,27)` census stretch because its many-model enumeration could
not be completed within this run; only the mandated BGS `(14,27)` model was exactly certified
no-realization.  The final equality also uses the programme's cited known `(13,22)` lower-bound
arrangement rather than regenerating it here.
