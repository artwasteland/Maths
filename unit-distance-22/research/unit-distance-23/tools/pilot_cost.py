"""The u(23) pilot's cost model (gate G2), from the run summaries the pilot and control workers push.

usage: python pilot_cost.py RESULTS_ROOT [--slices 1920] [--jobs 4] [--out cost-model.json]

RESULTS_ROOT holds one directory per run kind (`23-65-L12`, `22-61-L12`, `22-61-f74-L12`), each with one
`s<i>of<C>/run-summary.json` per sampled slice (the layout `coordination/cloud-workers/u23-slice.sh` writes). For
every slice it splits the wall time into the shared prefix (levels <= the slice level, which every worker rebuilds)
and the slice's own levels, per level and per phase (generation shards, prune step, stage verification), and counts
children and kept graphs per level. The whole tree above the slice level is estimated as the mean slice times C
(with the spread of the per-slice values reported, since the tree is heavy-tailed). The Mode 398 against Mode 74
comparison is made per slice index, where both kinds sampled the same slice.
"""
import sys, json, os, glob, statistics, collections

ROOT = sys.argv[1]
C = int(sys.argv[sys.argv.index("--slices") + 1]) if "--slices" in sys.argv else 1920
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None


JOBS = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4


def phases(level):
    # Generation shards run JOBS at a time, so their summed wall time is core time, not elapsed time: a cell's
    # elapsed generation is at least the longest shard and at least the sum spread over JOBS workers. The prune and
    # verify steps report their own elapsed wall.
    walls = [s.get("wall_seconds", 0) or 0 for s in level.get("shards") or []]
    gen = max(max(walls, default=0), sum(walls) / JOBS)
    pr = (level.get("prune") or {}).get("step_wall_seconds", 0) or 0
    ve = (level.get("verify") or {}).get("wall_seconds", 0) or 0
    return gen, pr, ve


def read(path):
    d = json.load(open(path))
    slice_level = d["slice"][0] if d.get("slice") else 12
    per = collections.defaultdict(lambda: {"gen": 0.0, "prune": 0.0, "verify": 0.0, "children": 0, "kept": 0})
    for l in d["levels"]:
        g, p, v = phases(l)
        row = per[l["n"]]
        row["gen"] += g; row["prune"] += p; row["verify"] += v
        row["children"] += l.get("children") or 0
        row["kept"] += ((l.get("prune") or {}).get("counts") or {}).get("kept", l.get("children") or 0)
    total = lambda rows: sum(r["gen"] + r["prune"] + r["verify"] for r in rows)
    return {"slice": d.get("slice"), "completed_through_n": d.get("completed_through_n"),
            "prefix_seconds": total(r for n, r in per.items() if n <= slice_level),
            "slice_seconds": total(r for n, r in per.items() if n > slice_level),
            "levels": {n: dict(r) for n, r in sorted(per.items()) if n > slice_level}}


report = {"slices_total": C, "kinds": {}}
for kind_dir in sorted(glob.glob(os.path.join(ROOT, "*"))):
    runs = {}
    for p in sorted(glob.glob(os.path.join(kind_dir, "s*of*", "run-summary.json"))):
        runs[os.path.basename(os.path.dirname(p))] = read(p)
    if not runs:
        continue
    secs = [r["slice_seconds"] for r in runs.values()]
    mean = statistics.mean(secs)
    kind = os.path.basename(kind_dir)
    top = {}
    for tag, r in runs.items():
        last = max(r["levels"]) if r["levels"] else None
        top[tag] = r["levels"][last]["kept"] if last is not None else None
    report["kinds"][kind] = {
        "sampled_slices": sorted(runs),
        "slice_seconds": {t: round(r["slice_seconds"], 1) for t, r in runs.items()},
        "slice_seconds_mean": round(mean, 1),
        "slice_seconds_spread": [round(min(secs), 1), round(max(secs), 1)],
        "prefix_seconds": {t: round(r["prefix_seconds"]) for t, r in runs.items()},
        "estimated_tree_machine_hours": round(mean * C / 3600, 1),   # elapsed hours on JOBS-core machines
        "top_level_kept": top,
        "per_level_mean": {n: {k: round(statistics.mean(r["levels"].get(n, {}).get(k, 0) for r in runs.values()), 1)
                               for k in ("gen", "prune", "verify", "children", "kept")}
                           for n in sorted({n for r in runs.values() for n in r["levels"]})},
    }
k398, k74 = report["kinds"].get("22-61-L12"), report["kinds"].get("22-61-f74-L12")
if k398 and k74:
    both = sorted(set(k398["slice_seconds"]) & set(k74["slice_seconds"]))
    report["mode398_vs_mode74_on_22_61"] = {
        t: {"seconds_398": k398["slice_seconds"][t], "seconds_74": k74["slice_seconds"][t],
            "ratio": round(k398["slice_seconds"][t] / k74["slice_seconds"][t], 3) if k74["slice_seconds"][t] else None}
        for t in both}
print(json.dumps(report, indent=1, default=str))
if OUT:
    json.dump(report, open(OUT, "w"), indent=1, default=str)
