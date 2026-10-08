#!/usr/bin/env python3
"""Mode 74 unchanged: CROSSCHECK.md's three replays, re-run with the new enum2.

crosscheck/replay.py (unmodified, sha256 c1cada1d...) is imported as a module and run on
the original u(22) run directory with CROSSCHECK's own plan (plan-main.json, seed
20260905: 92 shards, 7,503 parent records) and its two controls, then every per-shard
record is compared with the committed results-main.json / results-control-*.json.

One thing is patched, not edited: replay.DEFAULT_FORBIDDEN is set to the forbidden-74.json
of the original checkout, because the shard manifests key the forbidden list by that
absolute path (same bytes as data/forbidden-74.json here: sha256 ff1badd6...).  enum2 still
loads its own pinned copy.

PASS iff, shard by shard, the new run reproduces the committed record exactly in:
identical, parents_replayed, udenum_children, udenum_block, enum2_children (distinct),
enum2_children_raw (raw constructions: the fast engine enumerates the same neighbourhoods
in the same order), only_udenum and only_enum2 (and their first-20 lists); and both
controls are red again with the same differences.
Red control of this script's own comparison: the committed record with one field
perturbed (enum2_children + 1) must be reported as not reproduced.

Also, the whole u(22) final cell in Mode 74: enum2 on the 743 real level-21 parents of the
48 slices (from the worker branches) must give exactly the 4 production (22,61) graphs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from v398lib import ENUM2_DIR, ORIG_DAG_F12, RUNS, SCRATCH, compare, dump, enum2, read_records, sha256, software

CROSS = ENUM2_DIR / "crosscheck"
sys.path.insert(0, str(CROSS))
import replay  # noqa: E402

ORIG_FORBIDDEN = Path("<repo>/research/unit-distance-22/data/forbidden-74.json")
FIELDS = ("identical", "parents_replayed", "udenum_children", "udenum_block", "enum2_children",
          "enum2_children_raw", "only_udenum", "only_enum2", "only_udenum_first20", "only_enum2_first20",
          "range", "whole_shard", "children_file_sha256_matches_manifest")


def namespace(**kw) -> argparse.Namespace:
    base = {"dag": str(ORIG_DAG_F12), "cells": replay.ALL_CELLS, "plan_file": "", "ranges": "",
            "workers": 1, "workdir": "", "tag": ""}
    base.update(kw)
    return argparse.Namespace(**base)


def reproduce(old: dict, new: dict) -> dict:
    old_by = {e["shard_id"]: e for e in old["per_shard"]}
    new_by = {e["shard_id"]: e for e in new["per_shard"]}
    mismatches = []
    for sid, e in old_by.items():
        f = new_by.get(sid)
        if f is None:
            mismatches.append({"shard": sid, "missing": True})
            continue
        for key in FIELDS:
            if e.get(key) != f.get(key):
                mismatches.append({"shard": sid, "field": key, "old": e.get(key), "new": f.get(key)})
    extra = sorted(set(new_by) - set(old_by))
    return {"shards_old": len(old_by), "shards_new": len(new_by), "mismatches": mismatches[:50],
            "mismatch_count": len(mismatches), "extra_shards": extra,
            "reproduced": not mismatches and not extra}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=SCRATCH / "mode74")
    ap.add_argument("--summary", type=Path, default=RUNS / "mode74.json")
    ap.add_argument("--skip-main", action="store_true")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    if sha256(ORIG_FORBIDDEN) != sha256(ENUM2_DIR.parent / "data" / "forbidden-74.json"):
        raise SystemExit("the original checkout's forbidden-74.json differs from data/forbidden-74.json")
    replay.DEFAULT_FORBIDDEN = ORIG_FORBIDDEN
    summary = {"software": software(), "replay.py": sha256(CROSS / "replay.py"),
               "engine": os.environ.get("ENUM2_ENGINE", "fast"), "runs": {}}
    t0 = time.monotonic()
    if not a.skip_main:
        new = replay.cmd_replay(namespace(plan_file=str(CROSS / "plan-main.json"), workdir=str(a.work),
                                          tag="main-new"))
        old = json.loads((CROSS / "results-main.json").read_text())
        rep = reproduce(old, new)
        rep.update({"all_identical_new": new["all_identical"], "parents_replayed": new["parents_replayed"],
                    "udenum_children": new["udenum_children"], "enum2_children": new["enum2_children"],
                    "enum2_cpu_seconds": round(sum(e["enum2_cpu_seconds"] for e in new["per_shard"]), 1),
                    "enum2_cpu_seconds_2026_09_05": round(sum(e["enum2_cpu_seconds"] for e in old["per_shard"]), 1),
                    "input_mismatches_reported_by_replay": new["inputs"]["mismatches"][:3],
                    "input_mismatch_count": len(new["inputs"]["mismatches"])})
        summary["runs"]["main"] = rep
        # red control of the reproduction check itself
        perturbed = json.loads(json.dumps(old))
        perturbed["per_shard"][5]["enum2_children"] += 1
        summary["runs"]["main_red_perturbed_record"] = {"reproduced": reproduce(perturbed, new)["reproduced"],
                                                        "went_red": not reproduce(perturbed, new)["reproduced"]}
        print(f"main: {json.dumps({k: v for k, v in rep.items() if k != 'mismatches'})}", flush=True)
    # control a: one flipped edge in parent record 200010 of 12-20
    new_a = replay.cmd_replay(namespace(ranges="12-20-200000-210000:200000:200030", workdir=str(a.work),
                                        tag="control-a-new"),
                              mutation={"shard_id": "12-20-200000-210000", "record": 200010, "i": 0, "j": 1},
                              tag="control-a-new")
    old_a = json.loads((CROSS / "results-control-a.json").read_text())
    rep_a = reproduce(old_a, new_a)
    rep_a["red"] = not new_a["all_identical"]
    summary["runs"]["control_a"] = rep_a
    print(f"control a: {json.dumps({k: v for k, v in rep_a.items() if k != 'mismatches'})}", flush=True)
    # control b: K_{2,3} (index 1) dropped from a copy of the list
    raw = json.loads(ORIG_FORBIDDEN.read_text())
    copy = a.work / "forbidden-73-drop1.json"
    copy.write_text(json.dumps([g for k, g in enumerate(raw) if k != 1]))
    new_b = replay.cmd_replay(namespace(ranges="12-20-200000-210000:200000:200030,11-17-20000-30000:25000:25030",
                                        workdir=str(a.work), tag="control-b-new"),
                              forbidden=copy, tag="control-b-new")
    old_b = json.loads((CROSS / "results-control-b.json").read_text())
    rep_b = reproduce(old_b, new_b)
    rep_b["red"] = not new_b["all_identical"]
    rep_b["copy_sha256"] = sha256(copy)
    summary["runs"]["control_b"] = rep_b
    print(f"control b: {json.dumps({k: v for k, v in rep_b.items() if k != 'mismatches'})}", flush=True)
    # the u(22) final cell, whole: 743 real level-21 parents (48 slices) -> the 4 (22,61) graphs
    slices = SCRATCH.parent / "u22-slices"
    parents, children = [], []
    for s in range(48):
        parents += read_records(slices / f"s{s}of48" / "21-56.keep.g6")
        children += read_records(slices / f"s{s}of48" / "22-61.g6")
    fs74 = enum2.load_forbidden_set("74")
    t1 = time.process_time()
    raw = []
    for code in parents:
        raw.extend(enum2.extend_parent(enum2.graph6_decode(code), 61, fs74))
    final = compare(children, raw)
    final.update({"parents": len(parents), "enum2_cpu_seconds": round(time.process_time() - t1, 1)})
    summary["runs"]["final_cell_22_61"] = final
    print(f"final cell (22,61), Mode 74: {json.dumps(final)}", flush=True)
    summary["wall_seconds"] = round(time.monotonic() - t0, 1)
    ok = (rep_a["reproduced"] and rep_a["red"] and rep_b["reproduced"] and rep_b["red"] and
          final["identical"] and final["production"] == 4 and len(parents) == 743 and
          (a.skip_main or (summary["runs"]["main"]["reproduced"] and
                           summary["runs"]["main_red_perturbed_record"]["went_red"])))
    summary["pass"] = ok
    dump(a.summary, summary)
    print("RESULT:", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
