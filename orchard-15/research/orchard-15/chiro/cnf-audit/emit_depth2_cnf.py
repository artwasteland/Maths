#!/usr/bin/env python3
"""Regenerate depth-2 subcube CNFs of a (v,b) cube and print their sha256.

Same approach as emit_cube_cnf.py, one level deeper. run_cubes() with
--cube-depth 2 builds each child by

    children, sizes, order = refine_cube(reduction, representatives[i], group_one)
    cubes = [(f"cube{i:03d}-{j:03d}", child) for j, child in enumerate(children)]

and then encodes each child exactly as it encodes a depth-1 cube: the
cube_group is the subgroup of group_one fixing every config in the child, and
build_existence_encoding is called with lex=False, degree=True,
drop_exact_b=False.  solve_standalone then writes
<artifacts>/exist-<v>-<b>-<name>.cnf via chirosat.write_clauses.

This driver replays exactly that, writes each CNF to a scratch path, hashes it
and deletes it, so hundreds of subcubes can be checked without keeping tens of
GB.  Every clause still comes out of the unmodified exist.py.

    emit_depth2_cnf.py 15 32 --parent 3 --start 0 --stop 200 --tmp /tmp/d2/work0
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
CHIRO = HERE.parent.parent.parent
sys.path.insert(0, str(CHIRO))

import exist  # noqa: E402
from chirosat import write_clauses  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("v", type=int)
    ap.add_argument("b", type=int)
    ap.add_argument("--parent", type=int, required=True, help="depth-1 cube index")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--stop", type=int, default=None)
    ap.add_argument("--index-file", help="file of child indices, one per line; overrides --start/--stop")
    ap.add_argument("--tmp", required=True, help="scratch dir for the transient CNF")
    args = ap.parse_args(argv)

    reduction = exist.derive_reduction(args.v, args.b)
    cube_set = exist.enumerate_cubes(reduction, drop_one=False)
    group_one = exist.group_closure(cube_set.generators, reduction.v)
    rep = cube_set.representatives[args.parent]
    children, _sizes, _order = exist.refine_cube(reduction, rep, group_one)

    if args.index_file:
        wanted = [int(x) for x in Path(args.index_file).read_text().split()]
        bad = [j for j in wanted if not 0 <= j < len(children)]
        if bad:
            raise SystemExit(f"child index out of range (0..{len(children) - 1}): {bad[:5]}")
    else:
        stop = len(children) if args.stop is None else min(args.stop, len(children))
        wanted = list(range(args.start, stop))

    tmp = Path(args.tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    scratch = tmp / f"exist-{args.v}-{args.b}-work.cnf"

    for j in wanted:
        child = children[j]
        name = f"cube{args.parent:03d}-{j:03d}"
        cube_group = [
            g for g in group_one
            if all(exist.apply_to_config(g, config) == config for config in child)
        ]
        encoding = exist.build_existence_encoding(
            args.v, args.b,
            drop_exact_b=False, lex=False, degree=True,
            cube=child, cube_group=cube_group,
        )
        write_clauses(encoding.nvars, encoding.clauses, scratch)
        h = hashlib.sha256(scratch.read_bytes()).hexdigest()
        print(f"{name}\t{h}\t{encoding.nvars}\t{len(encoding.clauses)}", flush=True)
    scratch.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
