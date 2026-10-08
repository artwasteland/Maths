#!/usr/bin/env python3
"""Stage times and level counts of the e2e.py control runs, from their own manifests (no recomputation).

For each run directory under scratch/e2e/c-*: udenum seconds (the shard wall times in run-summary.json,
summed; they run --jobs at a time, so this is core time, not elapsed), the prune step's filter,
rhombus and check seconds (prune manifests), and per level the generated count and the kept count.

usage: summarize-e2e.py
"""
from __future__ import annotations

import json
import sys

from rhlib import SCRATCH, log


def main() -> int:
    rows = {}
    for d in sorted((SCRATCH / "e2e").glob("c-*")):
        if not d.is_dir():
            continue
        summary = json.loads((d / "run-summary.json").read_text())

        def gen_seconds(select) -> float:
            return (sum(s.get("wall_seconds", 0) for l in summary["levels"] if select(l["n"]) for s in l.get("shards", [])) +
                    sum(l.get("geng_wall_seconds", 0) + l.get("filter_wall_seconds", 0) for l in summary["levels"]
                        if select(l["n"])))
        gen = gen_seconds(lambda n: True)
        gen_above = gen_seconds(lambda n: n > 12)
        stages = {"filter": 0.0, "rule": 0.0, "check": 0.0}
        kept = pruned = rh_tu = rh_ref = 0
        for pm in d.glob("*.prune.manifest.json"):
            v = json.loads(pm.read_text())
            w = v["wall_seconds"]
            stages["filter"] += w.get("filter", 0.0)
            stages["check"] += w.get("check", 0.0)
            stages["rule"] += w.get("rhombus", 0.0) + w.get("triangles", 0.0)
            kept += v["counts"]["kept"]
            pruned += v["counts"]["pruned"]
            rh_tu += v["counts"].get("rhombus_tu", 0) + v["counts"].get("tri_tu", 0)
            rh_ref += v["counts"].get("rhombus_refuted", 0) + v["counts"].get("tri_refuted", 0)
        children = {f"{l['n']}-{l['m']}": l["children"] for l in summary["levels"]}
        rows[d.name] = {"udenum_core_seconds": round(gen, 1), "udenum_core_seconds_above_12": round(gen_above, 1),
                        **{k + "_seconds": round(v, 1) for k, v in stages.items()},
                        "generated_above_12": sum(c for k, c in children.items() if int(k.split("-")[0]) > 12),
                        "kept_total": kept, "pruned_total": pruned, "rule_tu": rh_tu, "rule_refuted": rh_ref}
        log(f"{d.name}: {json.dumps(rows[d.name])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
