#!/usr/bin/env python3
"""cube_census.py: the census of PTS(v, b) inside exist.py's cube frames, with a closure
certificate per cube.

Why this exists (2026-09-06). The (14,27) census (`exist.py 14 27 --all-models`, lex-leader
symmetry breaking) found 3,125 labelled models in 25 minutes and then could not finish its
closing UNSAT call inside 36,000 s; the standalone closure CNF (`census_closure.py`) ran for more
than twelve hours in kissat with a DRAT proof past 20 GB and no verdict, a proof no checker here
could hold in memory even if it finished. The lex-leader breaking is sound but weak: about 390
labellings of each of the 8 classes survive it, and the solver has to refute all of that
symmetric space at once.

The cube frames of exist.py are a much stronger breaking. The row of point 0 is normalised by the
reduction, the row of point 1 (depth 1) or of points 1 and 2 (depth 2) is fixed to one orbit
representative per cube, and the lex-leader is taken under the stabiliser of the cubed rows
(`build_existence_encoding(..., cube=, cube_group=)`). exist.py's cube set is a cover: every
PTS(v, b) with the degree bounds has a labelling in some cube (`enumerate_cubes` /
`refine_cube` assert the orbit partition of every row configuration), which is the lemma the
(15,32) proof rests on.

What this script does, per cube:
  1. build the cube encoding exactly as `exist.py --cubes` does;
  2. enumerate ALL its models with one incremental cadical (the loop of
     `enumerate_all_models`, without the orbit expansion, which assumes the global row frame and
     would trip on cube units): after each model, verify it with `verify_model`, write its PTS
     line, and add the exact-b blocking clause of its block vector;
  3. when the loop returns UNSAT, write the closure CNF (cube clauses + every blocking clause)
     and hand it to kissat with a DRAT proof, checked by drat-trim (`solve_standalone`, the same
     audited path the (15,32) cubes went through). UNSAT VERIFIED certifies that the models
     written are all the models of that cube.

Soundness of the whole: if every cube's closure is UNSAT VERIFIED and the union of the models'
isomorphism classes is K, then every PTS(v, b) with the degree bounds is isomorphic to a member
of K. Completeness of the cube set is exist.py's lemma; the per-cube claim is a checked DRAT
proof of a CNF whose clauses a reader can regenerate from (v, b, cube name) and the model lines.

Controls: `--mutate-drop-model` drops the last blocking clause of every cube that had a model
(the closure must then be SAT; the record says whether it was); exist.py's `--mutate-drop-cube`
is honoured (the aggregate's coverage audit must then fail); (13,23) must yield exactly one class
and (13,24) none.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import multiprocessing
import os
import sys
import time
from pathlib import Path

from pysat.solvers import Cadical153

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chirosat import file_sha256, find_executable  # noqa: E402
from exist import (  # noqa: E402
    ExistenceError,
    apply_to_config,
    build_existence_encoding,
    derive_reduction,
    enumerate_cubes,
    group_closure,
    parse_half_open_range,
    refine_cube,
    solve_standalone,
    verify_model,
)


def cube_rows(cube) -> list[dict[str, object]]:
    return [
        {"point": point, "blocks": [sorted((point, a, b)) for a, b in config[0]], "leave": list(config[1])}
        for point, config in enumerate(cube, start=1)
    ]


def _loop_child(connection, encoding, cap: int) -> None:
    """Enumerate every model of the cube encoding; send ('UNSAT'|'CAP', models)."""
    solver = Cadical153(bootstrap_with=encoding.clauses)
    models: list[tuple[str, list[int]]] = []
    try:
        while True:
            if len(models) >= cap:
                connection.send(("CAP", models))
                return
            if not solver.solve():
                break
            true_vars = {literal for literal in (solver.get_model() or []) if literal > 0}
            pts, _witness, _leave = verify_model(encoding, true_vars)
            blocks = set(pts.blocks)
            clause = [-var if triple in blocks else var for triple, var in encoding.block_variables.items()]
            if any(line == pts.line for line, _ in models):
                raise RuntimeError("the solver returned a block vector that is already blocked")
            models.append((pts.line, clause))
            solver.add_clause(clause)
        connection.send(("UNSAT", models))
    finally:
        solver.delete()
        connection.close()


def enumerate_cube_models(encoding, timeout: float, cap: int) -> tuple[str, list[tuple[str, list[int]]], float]:
    started = time.perf_counter()
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_loop_child, args=(child, encoding, cap))
    process.start()
    child.close()
    if not parent.poll(timeout if timeout > 0 else None):
        process.kill()
        process.join()
        return "LOOP_TIMEOUT", [], time.perf_counter() - started
    try:
        verdict, models = parent.recv()
    except EOFError as exc:
        process.join()
        raise RuntimeError(f"cube loop worker exited with code {process.exitcode}") from exc
    process.join()
    return verdict, models, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("v", type=int)
    p.add_argument("b", type=int)
    p.add_argument("--cube-depth", type=int, choices=(1, 2), default=1)
    p.add_argument("--cube-index", type=int, help="one depth-1 cube (required with --cube-children)")
    p.add_argument("--cube-children", type=parse_half_open_range, help="A:B, a half-open range of the depth-2 children of --cube-index")
    p.add_argument("--artifacts", default="scratch/cube-census")
    p.add_argument("--timeout", type=float, default=0.0, help="seconds per phase (loop; kissat), 0 = none")
    p.add_argument("--model-cap", type=int, default=100000, help="stop a cube's loop after this many models (recorded as CAP)")
    p.add_argument("--no-degree", action="store_true")
    p.add_argument("--no-cube-lex", action="store_true")
    p.add_argument("--drat-trim")
    p.add_argument("--keep-cnf", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--keep-proof", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--mutate-drop-model", action="store_true", help="control: drop the last blocking clause in every cube with a model; the closure must be SAT")
    p.add_argument("--mutate-drop-cube", action="store_true", help="control: exist.py's dropped-orbit cube set; the coverage audit must fail")
    p.add_argument("--skip-recorded", action="store_true", help="resume: skip cubes already recorded UNSAT_VERIFIED in the JSONL")
    args = p.parse_args(argv)
    if args.cube_children is not None and args.cube_index is None:
        raise ExistenceError("--cube-children requires --cube-index")

    checker = find_executable(
        args.drat_trim,
        ("~/tools/sat/drat-trim/drat-trim", str(Path(__file__).resolve().parent / "scratch" / "drat-trim"), "drat-trim"),
    )
    reduction = derive_reduction(args.v, args.b)
    cube_set = enumerate_cubes(reduction, drop_one=args.mutate_drop_cube and args.cube_depth == 1)
    group_one = group_closure(cube_set.generators, reduction.v)
    level1 = list(range(len(cube_set.representatives)))
    if args.cube_index is not None:
        if not 0 <= args.cube_index < len(cube_set.representatives):
            raise ExistenceError(f"--cube-index must be between 0 and {len(cube_set.representatives) - 1}")
        level1 = [args.cube_index]
    cubes: list[tuple[str, object, int]] = []
    if args.cube_depth == 1:
        cubes = [(f"cube{i:03d}", (cube_set.representatives[i],), len(group_one) // cube_set.orbit_sizes[i]) for i in level1]
    else:
        for i in level1:
            children, sizes, order = refine_cube(reduction, cube_set.representatives[i], group_one, drop_one=args.mutate_drop_cube)
            named = [(f"cube{i:03d}-{j:03d}", child, order // sizes[j]) for j, child in enumerate(children)]
            if args.cube_children is not None:
                start, stop = args.cube_children
                if stop > len(named):
                    raise ExistenceError(f"--cube-children stop {stop} exceeds child count {len(named)} of cube {i}")
                named = named[start:stop]
            cubes.extend(named)

    artifact_dir = Path(args.artifacts)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    jsonl = artifact_dir / f"cube-census-{args.v}-{args.b}-depth{args.cube_depth}.jsonl"
    mode = "a" if (args.cube_index is not None or args.cube_children is not None) else "w"
    if args.skip_recorded and jsonl.exists():
        done = set()
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("verdict") == "UNSAT_VERIFIED":
                    done.add(r["cube_name"])
        before = len(cubes)
        cubes = [c for c in cubes if c[0] not in done]
        print(f"skip-recorded: {before - len(cubes)} of {before} cubes already UNSAT_VERIFIED in {jsonl}", file=sys.stderr, flush=True)
        mode = "a"
    totals = {"cubes": 0, "models": 0, "unsat_verified": 0, "other": 0}
    started = time.perf_counter()
    with jsonl.open(mode, encoding="utf-8") as handle:
        for name, cube, stabiliser_order in cubes:
            encode_started = time.perf_counter()
            cube_group = None
            if not args.no_cube_lex:
                cube_group = [g for g in group_one if all(apply_to_config(g, config) == config for config in cube)]
            encoding = build_existence_encoding(
                args.v, args.b, drop_exact_b=False, lex=False, degree=not args.no_degree, cube=cube, cube_group=cube_group
            )
            encode_seconds = time.perf_counter() - encode_started
            loop_verdict, models, loop_seconds = enumerate_cube_models(encoding, args.timeout, args.model_cap)
            record: dict[str, object] = {
                "v": args.v, "b": args.b, "depth": args.cube_depth, "cube_name": name,
                "rows": cube_rows(cube), "stabiliser_order": stabiliser_order,
                "cube_group_order": None if cube_group is None else len(cube_group),
                "cube_clauses": len(encoding.clauses), "nvars": encoding.nvars,
                "encode_seconds": round(encode_seconds, 6),
                "loop_backend": "pysat-cadical153-incremental", "loop_verdict": loop_verdict,
                "loop_seconds": round(loop_seconds, 6),
                "models": [line for line, _ in models], "models_count": len(models),
                "pid": os.getpid(),
            }
            if loop_verdict == "UNSAT":
                blocking = [clause for _, clause in models]
                mutated = False
                if args.mutate_drop_model and blocking:
                    blocking = blocking[:-1]
                    mutated = True
                closure = dataclasses.replace(encoding, clauses=encoding.clauses + blocking)
                closure_record = solve_standalone(
                    closure, encode_seconds, artifact_dir, "kissat", checker, args.timeout, False,
                    stem=f"closure-{args.v}-{args.b}-{name}",
                )
                keep = {k: closure_record.get(k) for k in (
                    "verdict", "backend", "cnf_sha256", "solve_seconds", "proof_bytes", "proof_sha256", "proof_verified",
                    "check_seconds", "checker_tail", "checker_sha256", "timeout_seconds", "partial_proof_bytes",
                ) if k in closure_record}
                keep["clauses"] = len(closure.clauses)
                keep["blocking_clauses"] = len(blocking)
                record["closure"] = keep
                record["mutation"] = "drop-model" if mutated else None
                if mutated:
                    record["mutation_ok"] = closure_record["verdict"] == "SAT"
                cnf_path = Path(closure_record["cnf"])
                proof_path = Path(closure_record["proof"]) if closure_record.get("proof") else None
                if closure_record["verdict"] == "UNSAT" and closure_record.get("proof_verified") and not mutated:
                    record["verdict"] = "UNSAT_VERIFIED"
                    if not args.keep_proof and proof_path is not None and proof_path.exists():
                        proof_path.unlink()
                        record["proof_deleted_after_verification"] = True
                    if not args.keep_cnf:
                        cnf_path.unlink(missing_ok=True)
                        record["cnf_deleted_after_verification"] = True
                elif closure_record["verdict"] == "SAT" and not mutated:
                    record["verdict"] = "INCONSISTENT"
                    record["closure_model_line"] = closure_record.get("pts_line") or closure_record.get("line")
                else:
                    record["verdict"] = "MUTATION_" + closure_record["verdict"] if mutated else closure_record["verdict"]
                    if mutated and not args.keep_cnf:
                        cnf_path.unlink(missing_ok=True)
                        if proof_path is not None and proof_path.exists():
                            proof_path.unlink()
                # any remaining model file from a SAT kissat run
                model_file = artifact_dir / f"closure-{args.v}-{args.b}-{name}.kissat.model"
                model_file.unlink(missing_ok=True)
            else:
                record["verdict"] = loop_verdict
            record["total_seconds"] = round(time.perf_counter() - encode_started, 6)
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            totals["cubes"] += 1
            totals["models"] += len(models)
            if record["verdict"] == "UNSAT_VERIFIED":
                totals["unsat_verified"] += 1
            else:
                totals["other"] += 1
            print(
                f"{name} ({totals['cubes']}/{len(cubes)}) models={len(models)} loop={loop_seconds:.1f}s "
                f"verdict={record['verdict']} closure_solve={record.get('closure', {}).get('solve_seconds')} "
                f"check={record.get('closure', {}).get('check_seconds')} proof={record.get('closure', {}).get('proof_bytes')}",
                file=sys.stderr, flush=True,
            )
            if record["verdict"] == "INCONSISTENT":
                print("INCONSISTENT: the loop said UNSAT but kissat found a model; stopping", file=sys.stderr)
                return 3
    summary = totals | {
        "v": args.v, "b": args.b, "depth": args.cube_depth, "cube_index": args.cube_index,
        "cube_children": list(args.cube_children) if args.cube_children else None,
        "wall_seconds": round(time.perf_counter() - started, 6), "jsonl": str(jsonl.resolve()),
        "mutation": "drop-model" if args.mutate_drop_model else ("drop-cube" if args.mutate_drop_cube else None),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if totals["other"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
