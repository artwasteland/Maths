#!/usr/bin/env python3
"""Status of the u(23) fleet from the workers' pushed results (coordination/cloud-workers/JOBS.md, u23-fleet).

usage: python fleet_status.py [--fetch] [--out status.json] [--workdir DIR]

With --fetch it fetches every branch claude/answering-alexeev-u22-cloud-u23-fNN into refs/u23fleet/fNN and extracts
research/unit-distance-23/results/u23 from each into <workdir>/<tag>/. It then reads every slice's run-summary.json and
replay files and reports, over the 1,920 slices of the plan (worker fNN owns NN-1, NN-1+96, ...):
  - slices done through level 23, per worker and in total, and the slices never reported;
  - any slice whose top level (23,65) kept anything (must be empty, else it needs certificates: CONTRACT Section 3);
  - the G4 replay verdict of every slice (replay/summary.json; a replay/FAILED marker is a failure);
  - timing: the slice wall time summed over cells that were NOT resumed (a resumed cell's time is unknown, not zero),
    and how many slices had resumed cells;
It never infers success from silence: a slice counts as done only with completed_through_n = 23 in its own summary.
"""
import argparse, collections, glob, json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
W, C = 96, 1920
KIND = "23-65-L12-tri-pf74"


def sh(*cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, **kw)


def fetch(workdir: Path) -> dict:
    heads = {}
    out = sh("git", "ls-remote", "origin", "refs/heads/claude/answering-alexeev-u22-cloud-u23-f*").stdout.split("\n")
    for line in out:
        if not line.strip():
            continue
        sha, ref = line.split()
        branch = ref.split("refs/heads/", 1)[1]
        tag = branch.split("cloud-u23-", 1)[1].split("-")[0]
        heads.setdefault(tag, []).append((branch, sha))
    for tag, lst in sorted(heads.items()):
        for branch, sha in lst:
            local = f"refs/u23fleet/{branch.split('cloud-u23-', 1)[1]}"
            sh("git", "fetch", "-q", "origin", f"+refs/heads/{branch}:{local}")
            dst = workdir / branch.split("cloud-u23-", 1)[1]
            dst.mkdir(parents=True, exist_ok=True)
            arch = subprocess.run(["git", "archive", local, "research/unit-distance-23/results/u23"], cwd=REPO,
                                  capture_output=True)
            if arch.returncode == 0 and arch.stdout:
                subprocess.run(["tar", "-x", "-C", str(dst)], input=arch.stdout, check=True)
    return heads


def slice_record(d: Path) -> dict:
    rs = json.load(open(d / "run-summary.json"))
    known = unknown_cells = 0.0
    resumed = 0
    top_kept = None
    for l in rs.get("levels", []):
        if l.get("n", 0) <= 12:
            continue
        p = l.get("prune") or {}
        if l.get("resumed") or p.get("resumed"):
            resumed += 1
            continue
        walls = [x.get("wall_seconds", 0) or 0 for x in l.get("shards") or []]
        known += max(max(walls, default=0), sum(walls) / 4) + (p.get("step_wall_seconds") or 0) \
            + ((l.get("verify") or {}).get("wall_seconds") or 0)
        if l.get("n") == 23:
            top_kept = ((p.get("counts") or {}).get("kept"))
    for l in rs.get("levels", []):
        if l.get("n") == 23:
            top_kept = ((l.get("prune") or {}).get("counts") or {}).get("kept", l.get("children"))
    rep = {"verdict": "missing"}
    if (d / "replay" / "FAILED").exists():
        rep = {"verdict": "FAILED"}
    elif (d / "replay" / "summary.json").exists():
        s = json.load(open(d / "replay" / "summary.json"))
        mism, proc = s.get("mismatching_parents", 0) or 0, s.get("processed_parents", 0) or 0
        bad_cells = s.get("unreplayable_cells") or []
        verdict = "MISMATCH" if mism else ("UNREPLAYABLE" if bad_cells else ("EMPTY" if proc == 0 else "PASS"))
        rep = {"verdict": verdict, "parents": proc, "children": s.get("production_children_compared")}
    return {"completed_through_n": rs.get("completed_through_n"), "top_kept": top_kept,
            "seconds_known": round(known, 1), "resumed_cells": resumed, "replay": rep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--workdir", type=Path, default=Path("<scratch>/scratchpad/fleet/results"))
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    a.workdir.mkdir(parents=True, exist_ok=True)
    if a.fetch:
        fetch(a.workdir)
    plan = {f"f{k:02d}": [k - 1 + W * j for j in range(C // W)] for k in range(1, W + 1)}
    owner = {s: t for t, sl in plan.items() for s in sl}
    slices = {}
    for d in glob.glob(str(a.workdir / "*" / "research/unit-distance-23/results/u23" / KIND / "s*of1920")):
        d = Path(d)
        if not (d / "run-summary.json").exists():
            continue
        idx = int(d.name[1:].split("of")[0])
        rec = slice_record(d)
        rec["worker_dir"] = d.parts[len(a.workdir.parts)]
        prev = slices.get(idx)
        if prev is None or (rec["completed_through_n"] or 0) >= (prev["completed_through_n"] or 0):
            slices[idx] = rec
    done = {i for i, r in slices.items() if r["completed_through_n"] == 23}
    nonempty = {i: r["top_kept"] for i, r in slices.items() if r["top_kept"]}
    rep_bad = {i: r["replay"]["verdict"] for i, r in slices.items() if i in done and r["replay"]["verdict"] not in ("PASS", "EMPTY")}
    per_worker = collections.Counter(owner[i] for i in done)
    timed = [r["seconds_known"] for i, r in slices.items() if i in done and r["resumed_cells"] == 0]
    report = {"slices_done": len(done), "slices_total": C, "workers_reporting": len({owner[i] for i in slices}),
              "top_level_nonempty": nonempty, "replay_not_pass": rep_bad,
              "slices_with_resumed_cells": sum(1 for i in done if slices[i]["resumed_cells"]),
              "mean_seconds_unresumed": round(sum(timed) / len(timed), 1) if timed else None,
              "timed_slices": len(timed),
              "per_worker_done": dict(sorted(per_worker.items())),
              "missing": sorted(set(range(C)) - done) if len(done) > C - 50 else f"{C - len(done)} slices"}
    print(json.dumps({k: v for k, v in report.items() if k != "per_worker_done"}, indent=1))
    if a.out:
        json.dump({"report": report, "slices": slices}, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
