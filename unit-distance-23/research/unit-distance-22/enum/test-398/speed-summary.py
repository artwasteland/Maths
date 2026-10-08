#!/usr/bin/env python3
"""Arithmetic for (d): per-level table from speed.json, and the production-weighted estimate.

Per level L (sampled level-L parents of the (22,61) tree, every target cell of level L+1):
  per-parent ms          = 1000 * median CPU / parents (398f: / 398-free parents)
  slowdown, same parents = CPU(new398) / CPU(new74)
  level cost ratio R_L   = CPU(new398f) / CPU(new74)
      The 398 tree's level L is exactly the 398-free part of the 74 tree's level L (398-freeness
      is hereditary and a canonical parent is an induced subgraph), so the 398-free part of a
      uniform sample of the 74 tree's level L is a uniform sample of the 398 tree's level L at the
      same rate: R_L is the ratio of the two trees' generator work at level L.
  children ratio         = children(new398f) / children(new74): the relative size of the next
      level before its stage filters.
Weighted estimate: sum_L W_L R_L / sum_L W_L, where W_L is the production udenum shard wall at
parent level L in one slice (production-profile.json), for the levels both files cover.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed", type=Path, default=HERE / "runs" / "speed.json")
    ap.add_argument("--profile", type=Path, default=HERE / "runs" / "production-profile.json")
    a = ap.parse_args()
    sp = json.loads(a.speed.read_text())
    prof = json.loads(a.profile.read_text())
    rows = {}
    print("L  parents free  f      cpu_s old74 new74  new398 new398f | ms/parent 74  398same 398free | "
          "slowdown R_L    | children 74 398same 398free")
    for r in sp["levels"]:
        L, N, Nf = r["level"], r["parents"], r["parents_398_free"]
        c = r["cpu_seconds_median"]
        ch = r["children_written"]
        R = c["new398f"] / c["new74"] if c["new74"] else float("nan")
        slow = c["new398"] / c["new74"] if c["new74"] else float("nan")
        rows[L] = R
        print(f"{L:2d} {N:7d} {Nf:5d} {Nf / N:6.3f}  {c['old74']:7.3f} {c['new74']:7.3f} {c['new398']:7.3f} "
              f"{c['new398f']:7.3f} | {1000 * c['new74'] / N:8.3f} {1000 * c['new398'] / N:8.3f} "
              f"{(1000 * c['new398f'] / Nf) if Nf else float('nan'):8.3f} | {slow:6.2f} {R:6.3f} | "
              f"{ch['new74']:7d} {ch['new398']:7d} {ch['new398f']:7d}")
    kids = {r["level"]: (r["children_written"]["new398f"] / r["children_written"]["new74"]
                         if r["children_written"]["new74"] else 0.0) for r in sp["levels"]}
    for name, per in prof.items():
        levels = [int(L) for L in per if int(L) in rows and per[L]["udenum_shard_wall"] > 0]
        W = {L: per[str(L)]["udenum_shard_wall"] for L in levels}
        tot = sum(W.values())
        est = sum(W[L] * rows[L] for L in levels) / tot if tot else float("nan")
        terms = " + ".join(f"{W[L]:.0f}x{rows[L]:.3f}" for L in levels)
        print(f"{name}: generator time weighted over parent levels {levels}: ({terms}) / {tot:.0f} = {est:.3f}")
        P = {L: per[str(L)]["prune_wall"] for L in levels if per[str(L)]["prune_wall"] > 0}
        ptot = sum(P.values())
        pest = sum(P[L] * kids[L] for L in P) / ptot if ptot else float("nan")
        pterms = " + ".join(f"{P[L]:.0f}x{kids[L]:.3f}" for L in P)
        print(f"{name}: prune (TU filter + checker) time, weighted by children(398f)/children(74): "
              f"({pterms}) / {ptot:.0f} = {pest:.3f}")
        print(f"{name}: generator + prune: ({est * tot:.0f} + {pest * ptot:.0f}) / ({tot:.0f} + {ptot:.0f}) = "
              f"{(est * tot + pest * ptot) / (tot + ptot):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
