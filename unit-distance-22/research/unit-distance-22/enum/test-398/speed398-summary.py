#!/usr/bin/env python3
"""Arithmetic for the Mode 398 speed work, as speed-summary.py does it for REPORT-398 5.

Reads runs/speed398-speed.json (medians per level) and runs/production-profile.json (u(22)'s
per-slice udenum wall by parent level) and prints, per level, the ms per parent and the ratios,
then the production-weighted generator estimate sum_L W_L R_L / sum_L W_L with the old and the new
R_L = CPU(398 on the 398-free parents) / CPU(new binary, set 74, all parents).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed", type=Path, default=HERE / "runs" / "speed398-speed.json")
    ap.add_argument("--profile", type=Path, default=HERE / "runs" / "production-profile.json")
    a = ap.parse_args()
    sp = json.loads(a.speed.read_text())
    prof = json.loads(a.profile.read_text())
    print("L  parents free | ms/parent: old74 new74 | base398 new398 (same) | base398f new398f (free) | "
          "speedup same free | R_L old new | children 74 398f")
    R_old, R_new = {}, {}
    for r in sp["levels"]:
        L, N, Nf, ms = r["level"], r["parents_all"], r["parents_free"], r["ms_per_parent"]
        R_old[L], R_new[L] = r["R_old"], r["R_new"]
        f = lambda v: f"{v:7.3f}" if v is not None else "    n/a"
        print(f"{L:2d} {N:5d} {Nf:4d} | {f(ms.get('old74'))} {f(ms.get('new74'))} | {f(ms.get('base398'))} "
              f"{f(ms.get('new398'))} | {f(ms.get('base398f'))} {f(ms.get('new398f'))} | "
              f"{f(r['speedup_same'])} {f(r['speedup_free'])} | {f(r['R_old'])} {f(r['R_new'])} | "
              f"{r['children']['new74']:6d} {r['children']['new398f']:5d}")
    for name, per in prof.items():
        levels = [int(L) for L in per if int(L) in R_new and R_new[int(L)] is not None and per[L]["udenum_shard_wall"] > 0]
        W = {L: per[str(L)]["udenum_shard_wall"] for L in levels}
        tot = sum(W.values())
        old = sum(W[L] * R_old[L] for L in levels) / tot
        new = sum(W[L] * R_new[L] for L in levels) / tot
        print(f"{name}: generator time of the 398 tree relative to the 74 tree, weighted over parent levels "
              f"{levels}: old {old:.3f}, new {new:.3f} (x{old / new:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
