#!/usr/bin/env python3
"""How many parent records of each (b) cell take udenum's RESTRICTED bad-family path (delta(H) = d-1:
brute contains_forbidden over every candidate) and how many the PATTERN path (delta(H) >= d:
deletion-pattern embedding), so that (b)'s equality is known to cover both code paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from t398lib import ENUM, HERE, g6_lines, g6_order_size


def degrees(line: bytes) -> list[int]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    deg = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                deg[i] += 1
                deg[j] += 1
            k += 1
    return deg


def classify(parents: list[bytes], M: int) -> dict:
    out = {"skipped": 0, "restricted": 0, "pattern": 0, "d_out_of_range": 0}
    for g in parents:
        n, m = g6_order_size(g)
        d = M - m
        if d < 0 or d > n:
            out["d_out_of_range"] += 1
            continue
        deg = degrees(g)
        delta = min(deg)
        if delta <= d - 2 or (delta == d - 1 and deg.count(delta) > d):
            out["skipped"] += 1
        elif delta == d - 1:
            out["restricted"] += 1
        else:
            out["pattern"] += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=HERE / "runs" / "paths-in-cells.json")
    a = ap.parse_args()
    res = {}
    for d, names in ((ENUM / "out-22/dag-22-61", ["11-19", "11-20", "11-21", "11-22", "11-23", "12-23", "12-24",
                                                  "12-25", "12-26", "12-27"]),
                     (ENUM / "out-sup/dag-18-46", ["15-34", "15-35", "15-36", "15-37", "16-38", "16-39", "16-40",
                                                   "16-41", "17-42", "17-43", "18-46"])):
        for name in names:
            M = int(name.split("-")[1])
            res[f"{d.name}/{name}"] = classify(g6_lines(d / "_parents" / f"{name}.g6"), M)
    if a.slices:
        parents = [g for s in range(48) for g in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")]
        res["u22-final/22-61"] = classify(parents, 61)
    tot = {k: sum(v[k] for v in res.values()) for k in ("skipped", "restricted", "pattern", "d_out_of_range")}
    for k, v in res.items():
        print(f"{k:28s} {v}")
    print("total", tot)
    a.out.write_text(json.dumps({"cells": res, "total": tot}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
