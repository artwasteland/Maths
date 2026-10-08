#!/usr/bin/env python3
"""Per-level production profile of the u(22) run, from the slices' run-summary.json.

For each PARENT level L (the generator step L -> L+1): parents, children, the summed wall time of
the udenum shards, and the wall time of the prune step (TU filter + certificate check) on the
children.  Used by REPORT-398.md to weight the per-level set-398 cost ratios measured by speed.py.
"""
import argparse
import collections
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, required=True)
    ap.add_argument("--which", default="0,15,38")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "runs" / "production-profile.json")
    a = ap.parse_args()
    result = {}
    for s in (int(x) for x in a.which.split(",")):
        summary = json.loads((a.slices / f"s{s}of48" / "run-summary.json").read_text())
        per = collections.defaultdict(lambda: {"parents": 0, "children": 0, "udenum_shard_wall": 0.0,
                                               "prune_wall": 0.0})
        for lv in summary["levels"]:
            n = lv.get("n")
            if n is None or n < 13 or lv.get("kind") != "augmentation":
                continue
            p = per[n - 1]
            p["parents"] += lv.get("parents") or 0
            p["children"] += lv.get("children") or 0
            p["udenum_shard_wall"] += sum((x.get("wall_seconds") or 0) for x in lv.get("shards", []))
            p["prune_wall"] += ((lv.get("prune") or {}).get("wall_seconds") or {}).get("total", 0) or 0
        result[f"s{s}of48"] = {str(k): v for k, v in sorted(per.items())}
        print(f"slice {s}: parent level, parents, children, udenum shard wall s, prune wall s")
        for k, v in sorted(per.items()):
            print(f"  {k:2d} {v['parents']:10d} {v['children']:10d} {v['udenum_shard_wall']:10.0f} {v['prune_wall']:10.0f}")
        print(f"  total udenum {sum(v['udenum_shard_wall'] for v in per.values()):.0f} s, "
              f"prune {sum(v['prune_wall'] for v in per.values()):.0f} s")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
