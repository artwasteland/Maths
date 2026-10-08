#!/usr/bin/env python3
"""Exact rational cross-check of udrhombus's verdicts: no modulus anywhere.

The prover detects modulo P = 2^61 - 1 and argues (Hadamard) that this decides the rational question;
the prototype rhombus_probe.py also works modulo P, so agreement.py cannot see an error in that
argument. Here every 4-cycle row (from both diagonals, as the prototype lists them) goes into a
reduced row echelon form over Q (fractions.Fraction); each e_i is reduced exactly; then
  refuted  iff some pair a < b has red(e_a) = red(e_b),
  tu       iff not refuted and some NON-adjacent a < b has red(e_a) - red(e_b) = red(e_p) - red(e_q)
           for an edge pq (either orientation),
and for the first such pair (lexicographic) and its first ordered edge (lexicographic) the pair and
edge must be exactly the ones in the prover's certificate. PASS iff verdict, pair and edge agree on
every graph. Standard library only.

usage: exact-crosscheck.py [FILE.g6 ...] [--udrhombus PATH]   (default: every samples/*.g6)
Red control: --udrhombus bin/udrhombus-mutant-4 (built by mutants.py) must FAIL.
"""
from __future__ import annotations

import collections
import sys
from fractions import Fraction
from pathlib import Path

from rhlib import HERE, decode_g6, g6_lines, log, run_prover


def rref(rows: list[list[Fraction]], n: int) -> list[tuple[int, list[Fraction]]]:
    piv: list[tuple[int, list[Fraction]]] = []
    for r in rows:
        r = list(r)
        for c, pr in piv:
            if r[c]:
                f = r[c]
                r = [a - f * b for a, b in zip(r, pr)]
        lead = next((i for i, x in enumerate(r) if x), None)
        if lead is None:
            continue
        inv = 1 / r[lead]
        r = [x * inv for x in r]
        piv = [(c, [a - pr[lead] * b for a, b in zip(pr, r)] if pr[lead] else pr) for c, pr in piv]
        piv.append((lead, r))
    return piv


def exact_verdict(code: str):
    n, edges = decode_g6(code)
    adj = [set() for _ in range(n)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    rows = []
    for u in range(n):
        for w in range(u + 1, n):
            common = sorted(adj[u] & adj[w])
            for i in range(len(common)):
                for j in range(i + 1, len(common)):
                    v, x = common[i], common[j]
                    r = [Fraction(0)] * n
                    r[u] += 1; r[w] += 1; r[v] -= 1; r[x] -= 1
                    rows.append(r)
    piv = rref(rows, n)

    def red(i: int) -> tuple:
        v = [Fraction(0)] * n
        v[i] = Fraction(1)
        for c, pr in piv:
            if v[c]:
                f = v[c]
                v = [a - f * b for a, b in zip(v, pr)]
        return tuple(v)
    reds = [red(i) for i in range(n)]
    for a in range(n):
        for b in range(a + 1, n):
            if reds[a] == reds[b]:
                return "refuted", (a, b), None
    diff = lambda a, b: tuple(x - y for x, y in zip(reds[a], reds[b]))
    by_diff = collections.defaultdict(list)
    for p in range(n):
        for q in sorted(adj[p]):
            by_diff[diff(p, q)].append((p, q))
    for a in range(n):
        for b in range(a + 1, n):
            if b in adj[a]:
                continue
            hits = by_diff.get(diff(a, b))
            if hits:
                return "tu", (a, b), hits[0]
    return "pass", None, None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--udrhombus", type=Path, default=None, help="another build (a red control: a mutant)")
    a = ap.parse_args()
    files = a.files or sorted((HERE / "samples").glob("*.g6"))
    problems = []
    total = collections.Counter()
    for f in files:
        lines = g6_lines(f)
        recs, _, _ = run_prover(lines, a.udrhombus) if a.udrhombus else run_prover(lines)
        bad = 0
        for code, r in zip(lines, recs):
            v, pair, edge = exact_verdict(code)
            ok = v == r["verdict"]
            if ok and v != "pass":
                rh = r["witness"]["rhombus"]
                ok = tuple(rh["pair"]) == pair and (v == "refuted" or tuple(rh["edge"]) == edge)
            if not ok:
                bad += 1
                if bad <= 5:
                    log(f"  DIFFER {code}: prover {r['verdict']} {r.get('witness', {}).get('rhombus', {}).get('pair')} "
                        f"{r.get('witness', {}).get('rhombus', {}).get('edge')}; exact {v} {pair} {edge}")
            total[v] += 1
        total["graphs"] += len(lines)
        total["differences"] += bad
        log(f"{f.name}: {len(lines)} graphs; exact rational verdict, pair and edge = the prover's on {len(lines) - bad}")
        if bad:
            problems.append(f"{f.name}: {bad} differences")
    log(f"TOTAL {dict(total)}")
    log("EXACT", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
