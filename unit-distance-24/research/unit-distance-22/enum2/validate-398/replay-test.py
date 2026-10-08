#!/usr/bin/env python3
"""End-to-end tests of enum2/replay-398.py on real run directories.

  T0  Mode 74 on the original u(22) run directory (dag-22-61-f12, levels 11-12, shards
      present): the tool must PASS on production data it did not produce.
  T1  Mode 398 on a local run A (make-test-run.py: (16,41), reach, unsliced), --seeds full
      --red: PASS, every red control red.
  T2  Mode 398 on a local run B ((16,41), reach, sliced at level 12 as the u(22)/u(23) fleets
      slice, slice 1 of 3): PASS, stage files re-derived.
  Tampered copies of run A (each must make the replay FAIL, with the same seed and fraction):
  T3  one child line deleted from a sampled parent's block, in the cell file and its shard
      file, with every manifest hash and count rewritten to match (a consistent run that is
      missing one graph);
  T4  one spurious child added to a sampled parent's block: a Mode-74 child of that parent
      which the 398 reject (it recovers to that parent), manifests rewritten;
  T5  one parent source record changed without touching the manifests (stale input): the
      cell must be reported unreplayable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from v398lib import ENUM2_DIR, ORIG_DAG_F12, RUNS, SCRATCH, dump, enum2, recover_parent, sha256, software

PY = sys.executable
TOOL = ENUM2_DIR / "replay-398.py"
HERE = Path(__file__).resolve().parent


def run_tool(out: Path, run_dirs: list[Path], extra: list[str]) -> tuple[int, dict, str]:
    cmd = [PY, str(TOOL), "--out", str(out)]
    for d in run_dirs:
        cmd += ["--run-dir", str(d)]
    cmd += extra
    p = subprocess.run(["nice", "-n", "15", *cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    summary = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}
    return p.returncode, summary, p.stdout[-3000:]


def brief(summary: dict) -> dict:
    keys = ("sampled_parents", "processed_parents", "production_children_compared", "enum2_children_compared",
            "mismatching_parents", "all_identical", "red_all", "seconds_per_sampled_parent",
            "seconds_per_processed_parent", "wall_seconds")
    out = {k: summary.get(k) for k in keys}
    out["unreplayable_cells"] = [c.get("cell") for c in summary.get("unreplayable_cells", [])]
    out["seeds"] = [{k: s.get(k) for k in ("cell", "records", "sampled", "full_identical", "identical")}
                    for s in summary.get("seeds", [])]
    return out


def copy_run(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # manifests name absolute paths inside src: rewrite them to dst so the copy is a run of its own
    for mf in dst.rglob("*.json"):
        text = mf.read_text()
        if str(src) in text:
            mf.write_text(text.replace(str(src), str(dst)))


def rewrite_cell(run: Path, cell: str, new_lines: list[str], shard_file: Path | None,
                 shard_lines: list[str] | None) -> None:
    """Replace a cell file (and one shard file) and make every manifest agree with the new bytes."""
    cf = run / f"{cell}.g6"
    cf.write_text("".join(x + "\n" for x in new_lines))
    agg = run / f"{cell}.manifest.json"
    info = json.loads(agg.read_text())
    info["children_file_sha256"] = sha256(cf)
    info["children_written"] = len(new_lines)
    if shard_file is not None:
        shard_file.write_text("".join(x + "\n" for x in shard_lines))
        smf = shard_file.with_suffix(".manifest.json")
        sinfo = json.loads(smf.read_text())
        sinfo["children_file_sha256"] = sha256(shard_file)
        sinfo["children_written"] = len(shard_lines)
        smf.write_text(json.dumps(sinfo, indent=2) + "\n")
        info.setdefault("inputs_sha256", {})[str(shard_file)] = sha256(shard_file)
        info["inputs_sha256"][str(smf)] = sha256(smf)
    agg.write_text(json.dumps(info, indent=2) + "\n")


def pick_parent(replay_out: Path) -> tuple[dict, str | None]:
    """A sampled parent with >= 2 production children in a shard file, preferring one that
    has a Mode-74 child which the 398 reject (a graph that WOULD be its child without the
    324: the natural spurious record for T4)."""
    entries = [json.loads(x) for x in (replay_out / "replay.jsonl").read_text().splitlines()[1:]]
    fs398 = enum2.load_forbidden_set("398")
    fs74 = enum2.load_forbidden_set("74")
    fallback = None
    for e in entries:
        if not (e["production"] >= 2 and e["identical"] and e["where"] == "cell file"):
            continue
        fallback = fallback or e
        g = enum2.graph6_decode(e["record"])
        extra = sorted(set(enum2.extend_parent(g, e["m"], fs74)) - set(enum2.extend_parent(g, e["m"], fs398)))
        if extra:
            return e, extra[0]
    if fallback is None:
        raise SystemExit("no sampled parent with at least two production children")
    return fallback, None


def shard_containing(run: Path, cell: str, line: str) -> Path:
    for path in sorted((run / "shards" / cell).glob(f"{cell}-*.g6")):
        if line in set(x for x in path.read_text().split("\n") if x):
            return path
    raise SystemExit(f"no shard file of {cell} contains {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=SCRATCH / "replay-test")
    ap.add_argument("--run-a", type=Path, default=SCRATCH / "runs" / "A-16-41")
    ap.add_argument("--run-b", type=Path, default=SCRATCH / "runs" / "B-16-41-s1of3")
    ap.add_argument("--fraction", default="0.02")
    ap.add_argument("--seed", default="20260925")
    ap.add_argument("--summary", type=Path, default=RUNS / "replay-test.json")
    ap.add_argument("--skip", default="", help="comma-separated tests to skip (T0..T5)")
    a = ap.parse_args()
    skip = set(x for x in a.skip.split(",") if x)
    a.work.mkdir(parents=True, exist_ok=True)
    common = ["--fraction", a.fraction, "--seed", a.seed, "--min-per-shard", "3", "--whole-max", "20"]
    results: dict = {"software": software(), "replay-398.py": sha256(TOOL), "tests": {}}
    ok = True

    def record(name: str, code: int, summary: dict, tail: str, want_pass: bool) -> None:
        nonlocal ok
        passed = (code == 0) == want_pass
        results["tests"][name] = {"exit": code, "expected": "PASS" if want_pass else "FAIL",
                                  "as_expected": passed, **brief(summary), "tail": tail[-1500:]}
        ok = ok and passed
        print(f"{name}: exit {code}, expected {'PASS' if want_pass else 'FAIL'}: "
              f"{'as expected' if passed else 'NOT AS EXPECTED'} {json.dumps(brief(summary))[:600]}", flush=True)
        dump(a.summary, results)

    if "T0" not in skip:
        code, s, tail = run_tool(a.work / "T0", [ORIG_DAG_F12],
                                 ["--fraction", "0.0005", "--seed", a.seed, "--min-per-shard", "3",
                                  "--whole-max", "30", "--levels", "11-12", "--forbidden-set", "74",
                                  "--seeds", "sample", "--red"])
        record("T0 Mode 74, original u(22) run, levels 11-12", code, s, tail, True)
    if "T1" not in skip:
        code, s, tail = run_tool(a.work / "T1", [a.run_a], common + ["--seeds", "full", "--red",
                                                                     "--forbidden-set", "398"])
        record("T1 Mode 398, run A", code, s, tail, True)
    if "T2" not in skip and a.run_b.exists():
        code, s, tail = run_tool(a.work / "T2", [a.run_b], common + ["--seeds", "sample", "--red"])
        record("T2 Mode 398, run B (sliced)", code, s, tail, True)
    # tampered copies of run A
    base_out = a.work / "T1"
    if not (base_out / "replay.jsonl").exists():
        raise SystemExit("T3-T5 need T1's replay.jsonl")
    target, spurious = pick_parent(base_out)
    results["tamper_target"] = {"cell": target["cell"], "index": target["index"], "record": target["record"],
                                "block": target["block"], "where": target["where"], "spurious_child": spurious}
    cell = target["cell"]
    start, end = target["block"]          # cell-file line coordinates
    # the copies keep the run directory's base name, so the seeded sample is the same
    if "T3" not in skip:
        t3 = a.work / "T3-run" / a.run_a.name
        copy_run(a.run_a, t3)
        lines = [x for x in (t3 / f"{cell}.g6").read_text().split("\n") if x]
        victim = lines[start]             # the block's first child
        lines2 = lines[:start] + lines[start + 1:]
        shard_file = shard_containing(t3, cell, victim)
        slines = [x for x in shard_file.read_text().split("\n") if x]
        spos = slines.index(victim)
        slines2 = slines[:spos] + slines[spos + 1:]
        rewrite_cell(t3, cell, lines2, shard_file, slines2)
        code, s, tail = run_tool(a.work / "T3", [t3], common + ["--seeds", "off", "--cells", cell])
        record(f"T3 one child of parent {target['index']} deleted from {cell} (manifests rewritten)",
               code, s, tail, False)
        results["tests"][list(results["tests"])[-1]]["deleted_child"] = victim
    if "T4" not in skip:
        t4 = a.work / "T4-run" / a.run_a.name
        copy_run(a.run_a, t4)
        lines = [x for x in (t4 / f"{cell}.g6").read_text().split("\n") if x]
        # a Mode-74 child of this parent that the 398 reject (it recovers to this parent), else
        # a repeated line of the block; placed right after the block's last line
        last = lines[end - 1]
        added = spurious if spurious is not None else lines[start]
        lines2 = lines[:end] + [added] + lines[end:]
        shard_file = shard_containing(t4, cell, last)
        slines = [x for x in shard_file.read_text().split("\n") if x]
        spos = slines.index(last) + 1
        slines2 = slines[:spos] + [added] + slines[spos:]
        rewrite_cell(t4, cell, lines2, shard_file, slines2)
        code, s, tail = run_tool(a.work / "T4", [t4], common + ["--seeds", "off", "--cells", cell])
        what = "a Mode-74 child rejected by the 398" if spurious is not None else "a repeated child"
        record(f"T4 {what} added to the block of parent {target['index']} in {cell} (manifests rewritten)",
               code, s, tail, False)
    if "T5" not in skip:
        t5 = a.work / "T5-run" / a.run_a.name
        copy_run(a.run_a, t5)
        info = json.loads((t5 / f"{cell}.manifest.json").read_text())
        src = Path(info["parent_sources"][0]["file"])
        recs = [x for x in src.read_text().split("\n") if x]
        g = enum2.graph6_decode(recs[0])
        adj = list(g.adj)
        adj[0] ^= 1 << 1
        adj[1] ^= 1 << 0
        recs[0] = enum2.canonical_g6(enum2.Graph(tuple(adj)))
        src.write_text("".join(x + "\n" for x in recs))
        code, s, tail = run_tool(a.work / "T5", [t5], common + ["--seeds", "off", "--cells", cell])
        record(f"T5 one parent source record of {cell} changed, manifests untouched", code, s, tail, False)
    results["pass"] = ok
    dump(a.summary, results)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
