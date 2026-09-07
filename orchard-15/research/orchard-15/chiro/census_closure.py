#!/usr/bin/env python3
"""census_closure.py: a checkable certificate that an --all-models census is complete.

The all-models loop (exist.py, _all_models_child) finds labelled block assignments one at a time
with one incremental solver and blocks each one; its LAST call, the one that must return UNSAT to
say "there is no other model", can take many hours once thousands of blocking clauses have piled
up (the (13,23) no-lex control spent more than nine hours on it on 2026-09-05/06, and the (14,27)
census stalled on one call for hours). This tool asks the same question of a standalone solver
with proof logging, so the answer is a DRAT proof drat-trim can check rather than a process that
eventually exits:

    base CNF (the same flags as the census: lex or --no-lex, degree bounds, exact b)
    + for every line of the census file, the clause  OR_{t in blocks(line)} NOT B(t)

UNSAT  => every labelled model of the base CNF is a line of the file: the census is complete.
SAT    => the solver's model is a labelled model missing from the file: append it and repeat.

The blocking clause here has b literals rather than the loop's full-vector form; under the base
encoding's exactly-b cardinality constraint the two exclude precisely the same assignment (an
assignment whose true block set equals the line's is that line), so the closure CNF is
equisatisfiable with the loop's final call.

Usage:
  python3 census_closure.py V B CENSUS.pts OUT.cnf [--no-lex] [--no-degree]
Then, for example:
  kissat -q OUT.cnf OUT.drat ; drat-trim OUT.cnf OUT.drat -t 10000000
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exist  # noqa: E402


def parse_line(line: str, v: int, b: int) -> list[tuple[int, int, int]]:
    head, rest = line.split(":", 1)
    hv, hb = map(int, head.split())
    if (hv, hb) != (v, b):
        raise SystemExit(f"census line is for ({hv},{hb}), not ({v},{b})")
    blocks = [tuple(sorted(map(int, t.split()))) for t in rest.strip().rstrip(";").split(",") if t.strip()]
    if len(blocks) != b:
        raise SystemExit(f"census line has {len(blocks)} blocks, not {b}")
    return blocks  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("v", type=int)
    p.add_argument("b", type=int)
    p.add_argument("census", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--no-lex", action="store_true", help="the census was run with --no-lex")
    p.add_argument("--no-degree", action="store_true", help="the census was run with --no-degree")
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    enc = exist.build_existence_encoding(a.v, a.b, drop_exact_b=False, lex=not a.no_lex, degree=not a.no_degree)
    base = enc.clauses
    lines = [l.strip() for l in a.census.read_text().splitlines() if l.strip()]
    seen: set[tuple[tuple[int, int, int], ...]] = set()
    blocking: list[list[int]] = []
    for line in lines:
        blocks = tuple(parse_line(line, a.v, a.b))
        if blocks in seen:
            continue
        seen.add(blocks)
        try:
            blocking.append([-enc.block_variables[t] for t in blocks])
        except KeyError as e:
            raise SystemExit(f"triple {e} is not a block variable of the encoding") from None
    with a.out.open("w", encoding="ascii") as fh:
        fh.write(f"p cnf {enc.nvars} {len(base) + len(blocking)}\n")
        for c in base:
            fh.write(" ".join(map(str, c)) + " 0\n")
        for c in blocking:
            fh.write(" ".join(map(str, c)) + " 0\n")
    sha = hashlib.sha256(a.out.read_bytes()).hexdigest()
    rec = {"v": a.v, "b": a.b, "census": str(a.census), "census_lines": len(lines), "distinct_models": len(seen),
           "lex": not a.no_lex, "degree": not a.no_degree, "base_clauses": len(base), "blocking_clauses": len(blocking),
           "variables": enc.nvars, "cnf": str(a.out), "cnf_sha256": sha, "seconds": round(time.perf_counter() - t0, 3)}
    print(json.dumps(rec, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
