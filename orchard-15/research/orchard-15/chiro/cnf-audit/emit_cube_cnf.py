#!/usr/bin/env python3
"""Emit one (v, b) cube CNF from the frozen generator, without solving.

Why this exists.  The audit job asks for

    exist.py 15 32 --backend cadical --cubes --cube-index k --cnf-only

but exist.py honours --cnf-only only on the non-cube path (exist.py:1193).
With --cubes the run goes through run_cubes(), which calls solve_standalone()
and therefore actually launches cadical with a DRAT proof -- the full
refutation, not the solver-free encoding the job description asks for.

So this driver imports the frozen exist.py and replays exactly the steps
run_cubes() takes to build cube k, then calls the same chirosat.write_clauses
that solve_standalone() would call, at the same path
(<artifacts>/exist-<v>-<b>-cube<kkk>.cnf).  Nothing here re-implements the
encoding: every clause comes out of build_existence_encoding in the
unmodified generator, so the bytes are the bytes the cube workers refuted.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
CHIRO = HERE.parent.parent.parent
sys.path.insert(0, str(CHIRO))

import exist  # noqa: E402
from chirosat import write_clauses  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("v", type=int)
    parser.add_argument("b", type=int)
    parser.add_argument("--cube-index", type=int, required=True)
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args(argv)

    # --- run_cubes() prologue, verbatim (exist.py:1045-1071, depth 1) ---
    reduction = exist.derive_reduction(args.v, args.b)
    cube_set = exist.enumerate_cubes(reduction, drop_one=False)
    group_one = exist.group_closure(cube_set.generators, reduction.v)

    k = args.cube_index
    if not 0 <= k < len(cube_set.representatives):
        raise SystemExit(f"cube index {k} out of range (0..{len(cube_set.representatives) - 1})")

    name = f"cube{k:03d}"
    cube = (cube_set.representatives[k],)

    # --- run_cubes() body for one cube (exist.py:1085-1093) ---
    encode_started = time.perf_counter()
    # default --no-cube-lex is False, so the stabiliser lex-leader is used
    cube_group = [
        g for g in group_one if all(exist.apply_to_config(g, config) == config for config in cube)
    ]
    encoding = exist.build_existence_encoding(
        args.v,
        args.b,
        drop_exact_b=False,
        lex=False,
        degree=True,
        cube=cube,
        cube_group=cube_group,
    )
    encode_seconds = time.perf_counter() - encode_started

    # --- solve_standalone()'s CNF write (exist.py:971-977), same stem ---
    artifact_dir = Path(args.artifacts)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    destination = artifact_dir / f"exist-{args.v}-{args.b}-{name}.cnf"
    write_started = time.perf_counter()
    write_clauses(encoding.nvars, encoding.clauses, destination)
    write_seconds = time.perf_counter() - write_started

    record = exist.common_result(encoding, encode_seconds) | {
        "verdict": "CNF_ONLY",
        "cube_name": name,
        "cube_index": k,
        "level1_cubes": len(cube_set.representatives),
        "level1_orbit_sizes": cube_set.orbit_sizes,
        "group_one_order": len(group_one),
        "cube_group_order": len(cube_group),
        "cnf": str(destination.resolve()),
        "cnf_sha256": exist.file_sha256(destination),
        "cnf_bytes": destination.stat().st_size,
        "write_seconds": round(write_seconds, 6),
        "generator": "exist.py (unmodified) via scratch/cnf-audit/emit_cube_cnf.py",
    }
    print(json.dumps(record, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
