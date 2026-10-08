#!/usr/bin/env python3
"""verify-chain.py's coverage derivation (G5 objection 1) and run-dag2.py's resume check (G5 objection 2).

Runs from e2e.py's scratch tree (the tree's scripts and binaries, the REAL checkers). The landed verify-chain.py
(LANDED_COMMIT) runs beside the new one on every tampered directory, so each red control shows both what the
old tool said and what the new one says. Every tampering is made in place (the files hold absolute paths) on a
snapshot that is restored byte for byte afterwards.

G  Green: (16,41) Mode 398 --triangles (the reviewer's c-16-41-f398-tri control, run here): the new tool with
   --check says COVERAGE exhaustive and CHAIN OK (exit 0); without --check, and with --from-n 13, it says CHAIN
   PARTIAL (exit 3) with the reason; --summary-only says COVERAGE (summary only) OK and CHAIN PARTIAL (exit 3).
R1 The reviewer's first tampering, made consistent file by file: (15,37) omitted (its files deleted, its
   summary entry removed), the level-15 window narrowed to [36,36] (and the summary's reach level 15), the
   target's parent list, parent file, shard, level, reach, prune and verify files rebuilt for the resulting
   EMPTY target (AMP's (16,41) graph lost). The landed tool must say CHAIN OK (the gap); the new one CHAIN FAIL
   naming the missing cell (15,37), the narrowed window and the target's parents.
R2 The reviewer's second: every pruned-level entry removed from run-summary.json. Landed: CHAIN OK with
   certs_replayed 0; new: CHAIN FAIL naming the missing required cells.
R3 Mine: one allowed parent level dropped, consistently: (13,30) removed from the parent lists (and parent
   files, shards) of the level-14 cells that read it, and the summary's level-13 window narrowed to exclude
   it. Landed: CHAIN OK; new: CHAIN FAIL naming the allowed parents.
R4 Mine: a consistent run with an unjustified root, run-dag2.py --reach-root-k 5 at (16,41) (Schade's bound is
   41 - u-bar(15) = 4; the run's own table follows from its root, and it loses AMP's (16,41) graph, of minimum
   degree 4). Landed: CHAIN OK; new: CHAIN FAIL (the root k, and the cells the justified root requires).
F  A sliced fleet, (16,41) Mode 398 --triangles sliced 2 ways at level 12: each slice CHAIN OK (exhaustive for
   its slice); --summary-only on both: COVERAGE (summary only) OK, the slices' records of each level-12 cell
   adding up to it; on slice 0 alone: FAIL (slice 1 missing); with a slice's record of a level-12 parent
   changed: FAIL.
P  Resume (objection 2), on G's directory: run-dag2.py --resume reuses every prune step (green); with one prune
   manifest's target changed, its udcheck_rhombus.py sha256 zeroed, its checker marked from_environment, its
   checker path changed, its ACCEPT line emptied, or its ACCEPT tu count changed, that step (and only that
   step) reruns, rewriting the same outputs; with $PRUNE_UDCHECK_RHOMBUS set every step reruns, and the next
   --resume without it reruns them all again (their manifests record the environment's checker), the one
   after reuses all. Every red control is followed by the directory's CHAIN OK.

usage: vchain.py [--phases G,R,F,P] [--jobs 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import e2e
from e2e import MATHS_PY, TREE, build_tree, known_at, sha256
from rhlib import REPO, SCRATCH, UD, g6_lines, log

LANDED_COMMIT = "b6494295b"   # origin/claude/answering-alexeev-u22 under this work: the landed verify-chain.py
RUNS = SCRATCH / "vchain"
problems: list[str] = []


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def h(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_dag2(out: Path, target, mode: int, jobs: int, extra=(), env_extra: dict | None = None,
             fresh: bool = True) -> tuple[int, float]:
    if fresh:
        shutil.rmtree(out, ignore_errors=True)
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "run-dag2.py"), "--target-n", str(target[0]),
           "--target-m", str(target[1]), "--output-dir", str(out), "--jobs", str(jobs), "--reach", "--prune",
           "--prune-from", "12", "--prune-filter-only", "--prune-python", str(MATHS_PY), "--triangles", *extra]
    if mode == 398:
        cmd += ["--forbidden-set", "398", "--verify-stages"]
    env = dict(os.environ)
    env.pop("PRUNE_UDCHECK_RHOMBUS", None)
    env.update(env_extra or {})
    t0 = time.monotonic()
    with (out.parent / f"{out.name}.log").open("a") as stream:
        p = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env)
    return p.returncode, time.monotonic() - t0


def chain(run: Path, *args: str, landed: bool = False) -> dict:
    """verify-chain.py (the new one, or the landed one) with the given arguments (default: the run alone)."""
    script = TREE / "enum" / ("verify-chain-landed.py" if landed else "verify-chain.py")
    p = subprocess.run(["nice", "-n", "10", sys.executable, str(script), *(args or (str(run),))],
                       capture_output=True, text=True)
    out = p.stdout.strip().splitlines()
    stats = {}
    for line in out:
        if line.startswith("{"):
            try:
                stats = json.loads(line)
            except json.JSONDecodeError:
                pass
    return {"exit": p.returncode, "last": out[-1] if out else p.stderr.strip()[-200:],
            "problems": [x[len("PROBLEM: "):] for x in out if x.startswith("PROBLEM: ")],
            "coverage": [x for x in out if x.startswith("COVERAGE")], "stats": stats,
            "notes": [x for x in out if x.startswith("NOT FROM")]}


class Snapshot:
    """Tamper a run directory in place and restore it byte for byte afterwards."""
    def __init__(self, run: Path):
        self.run = run
        self.backup = run.parent / f"{run.name}.pristine"

    def __enter__(self):
        shutil.rmtree(self.backup, ignore_errors=True)
        shutil.copytree(self.run, self.backup, symlinks=True)
        self.digest = tree_digest(self.run)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.run)
        self.backup.rename(self.run)
        if tree_digest(self.run) != self.digest:
            problems.append(f"{self.run.name}: not restored byte for byte")


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            digest.update(str(p.relative_to(root)).encode() + b"\0" + p.read_bytes() + b"\0")
    return digest.hexdigest()


def summary_edit(run: Path, fn) -> None:
    path = run / "run-summary.json"
    value = load(path)
    fn(value)
    dump(path, value)


def set_parents(run: Path, n: int, m: int, keep_pms: list[int]) -> int:
    """Rebuild cell (n,m)'s parent file from its listed sources with m' in keep_pms, consistently: the aggregate
    manifest's parent_sources and hashes, one shard manifest tiling the new parent file, the summary entry.
    The level file is left as it is (the tools do not recompute children). Returns the new parent count."""
    am_path = run / f"{n}-{m}.manifest.json"
    am = load(am_path)
    sources = [s for s in am["parent_sources"] if s["level"][1] in keep_pms]
    am["parent_sources"] = sources
    parent_file = Path(am["parent_file"])
    parent_file.write_bytes(b"".join(Path(s["file"]).read_bytes() for s in sources))
    count = len(g6_lines(parent_file))
    am["inputs_sha256"][str(parent_file)] = h(parent_file)
    am["parent_range"] = [0, count]
    manifests = sorted((run / "shards" / f"{n}-{m}").glob("*.manifest.json"))
    for other in manifests[1:]:
        am["inputs_sha256"].pop(str(other), None)
        other.unlink()
    info = load(manifests[0])
    info["parent_range"] = [0, count]
    info["inputs_sha256"][str(parent_file)] = h(parent_file)
    dump(manifests[0], info)
    am["inputs_sha256"][str(manifests[0])] = h(manifests[0])
    dump(am_path, am)

    def fix(s: dict) -> None:
        for e in s["levels"]:
            if (e["n"], e["m"]) == (n, m) and "parent_sources" in e:
                e["parent_sources"] = [x for x in e["parent_sources"] if x["level"][1] in keep_pms]
                e["parent_edge_counts"] = [pm for pm in e["parent_edge_counts"] if pm in keep_pms]
                e["parents"] = count
                e["shards"] = [{"range": [0, count], "resumed": False, "children": e.get("children", 0)}]
    summary_edit(run, fix)
    return count


def empty_cell(run: Path, n: int, m: int) -> None:
    """Make cell (n,m) consistently empty: level, shard part, reach, certs, keep and UNKNOWN files, with every
    hash, count and the verify manifest of its (empty) stage file (what the augmentation of a parent file
    without the lost graph's parent gives)."""
    full = run / f"{n}-{m}.g6"
    full.write_bytes(b"")
    am_path = run / f"{n}-{m}.manifest.json"
    am = load(am_path)
    for part in sorted((run / "shards" / f"{n}-{m}").glob("*.g6")):
        part.write_bytes(b"")
        am["inputs_sha256"][str(part)] = h(part)
    for sm in sorted((run / "shards" / f"{n}-{m}").glob("*.manifest.json")):
        info = load(sm)
        info["children_written"], info["children_file_sha256"] = 0, h(full)
        dump(sm, info)
        am["inputs_sha256"][str(sm)] = h(sm)
    am["children_written"], am["children_file_sha256"] = 0, h(full)
    dump(am_path, am)
    reach = run / f"{n}-{m}.reach.g6"
    reach.write_bytes(b"")
    rm_path = run / f"{n}-{m}.reach.manifest.json"
    rm = load(rm_path)
    rm.update({"input_sha256": h(full), "output_sha256": h(reach)})
    for key in ("input", "kept", "dropped", "records_in", "records_out"):
        if key in rm:
            rm[key] = 0
    dump(rm_path, rm)
    for name in ("certs.jsonl", "keep.g6", "UNKNOWN.g6"):
        (run / f"{n}-{m}.{name}").write_bytes(b"")
    pm_path = run / f"{n}-{m}.prune.manifest.json"
    pm = load(pm_path)
    pm["inputs_sha256"][str(reach)] = h(reach)
    for name in ("certs.jsonl", "keep.g6", "UNKNOWN.g6"):
        pm["outputs_sha256"][str(run / f"{n}-{m}.{name}")] = h(run / f"{n}-{m}.{name}")
    pm["counts"] = {k: 0 for k in pm["counts"]}
    pm["verified_counts"] = {k: 0 for k in pm["verified_counts"]}
    pm["checker"] = "ACCEPT certificates " + " ".join(f"{k}=0" for k in (
        "records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes", "rhombus_tu", "rhombus_refuted",
        "tri_tu", "tri_refuted"))
    dump(pm_path, pm)
    vm_path = run / f"{n}-{m}.verify.manifest.json"
    if vm_path.is_file():
        vm = load(vm_path)
        stage = run / f"{n}-{m}.keep.g6"
        vm.update({"stage_sha256": h(stage), "records": 0, "parents_seen": 0,
                   "parts": [{**(vm.get("parts") or [{}])[0], "range": [0, 0],
                              "udenum_stats": {**((vm.get("parts") or [{}])[0].get("udenum_stats") or {}),
                                               "parents_seen": 0, "children_written": 0}}]})
        dump(vm_path, vm)

    def fix(s: dict) -> None:
        for e in s["levels"]:
            if (e["n"], e["m"]) == (n, m):
                e["children"] = 0
                for key in ("reach",):
                    if isinstance(e.get(key), dict):
                        e[key].update({k: 0 for k in ("input", "kept", "dropped") if k in e[key]})
                if isinstance(e.get("prune"), dict):
                    e["prune"]["counts"] = {k: 0 for k in e["prune"]["counts"]}
    summary_edit(run, fix)


def delete_cell(run: Path, n: int, m: int) -> None:
    for p in run.glob(f"{n}-{m}.*"):
        p.unlink()
    for d in (run / "shards" / f"{n}-{m}", run / "_prune" / f"{n}-{m}"):
        shutil.rmtree(d, ignore_errors=True)
    for p in (run / "_parents" / f"{n}-{m}.g6", run / "_prune" / f"{n}-{m}.log"):
        p.unlink(missing_ok=True)
    summary_edit(run, lambda s: s.update(levels=[e for e in s["levels"] if (e["n"], e["m"]) != (n, m)]))


def both(run: Path, label: str, *args: str) -> tuple[dict, dict]:
    old = chain(run, str(run), *args, landed=True)
    new = chain(run, str(run), *args)
    log(f"{label}: LANDED verify-chain exit {old['exit']}: {old['last']} (certs_replayed "
        f"{old['stats'].get('certs_replayed')}, levels_inspected {old['stats'].get('levels_inspected')})")
    log(f"{label}: NEW verify-chain exit {new['exit']}: {new['last']}")
    for p in new["problems"][:8]:
        log(f"      PROBLEM: {p[:300]}")
    return old, new


def expect_gap(label: str, old: dict, new: dict, must_name: list[str]) -> None:
    named = all(any(word in p for p in new["problems"]) for word in must_name)
    if old["exit"] != 0 or old["last"] != "CHAIN OK":
        log(f"{label}: note: the landed tool did not accept it either ({old['last']})")
    if new["exit"] != 1 or not new["last"].startswith("CHAIN FAIL") or not named:
        problems.append(f"{label}: the new verify-chain did not refuse it naming {must_name}: {new['last']} "
                        f"{new['problems'][:4]}")


# ---------------------------------------------------------------- G, R
def phase_g(run: Path) -> None:
    new = chain(run, str(run), "--check")
    log(f"G --check: exit {new['exit']}: {new['coverage']} / {new['last']}; required cells "
        f"{new['stats'].get('required_cells')}, certs_replayed {new['stats'].get('certs_replayed')}")
    if new["exit"] != 0 or new["last"] != "CHAIN OK" or not new["coverage"] or "exhaustive" not in new["coverage"][0]:
        problems.append(f"G: the untampered run is not CHAIN OK (exhaustive): {new}")
    for args, reason in ((("--from-n", "13"), "levels below 13"), ((), "not replayed (no --check)")):
        r = chain(run, str(run), *args)
        log(f"G {' '.join(args) or 'no --check'}: exit {r['exit']}: {r['last']}")
        if r["exit"] != 3 or not r["last"].startswith("CHAIN PARTIAL") or reason not in r["last"]:
            problems.append(f"G {args}: not an explicit PARTIAL: {r['last']}")
    r = chain(run, "--summary-only", str(run))
    log(f"G --summary-only: exit {r['exit']}: {r['coverage']} / {r['last']}")
    if r["exit"] != 3 or not r["last"].startswith("CHAIN PARTIAL (summary only") or \
            not any("COVERAGE (summary only) OK" in x for x in r["coverage"]):
        problems.append(f"G --summary-only: {r}")


def phase_r(run: Path, root5: Path) -> None:
    known = known_at(16, 41)
    # R1: (15,37) omitted, the level-15 window narrowed, the target rebuilt empty
    with Snapshot(run):
        delete_cell(run, 15, 37)
        set_parents(run, 16, 41, [36])
        empty_cell(run, 16, 41)

        def narrow(s: dict) -> None:
            s["windows"]["15"] = [36, 36]
            s["reach"]["levels"]["15"] = [m for m in s["reach"]["levels"]["15"] if m != 37]
        summary_edit(run, narrow)
        top = set(g6_lines(run / "16-41.keep.g6"))
        log(f"R1 tampered: (15,37) omitted, window 15 = [36,36], (16,41) rebuilt from (15,36) alone: top keep "
            f"{len(top)} graphs, AMP's (16,41) graph present {sum(1 for g in known if g in top)}/{len(known)}")
        old, new = both(run, "R1", "--check")
        expect_gap("R1", old, new, ["[[15, 37]]", "windows", "16-41: listed parent levels"])
    # R2: every pruned-level entry removed from the summary
    with Snapshot(run):
        summary_edit(run, lambda s: s.update(levels=[e for e in s["levels"] if e["n"] < 12]))
        old, new = both(run, "R2", "--check")
        expect_gap("R2", old, new, ["required cell(s) of (16,41) not in run-summary.json"])
        if old["stats"].get("certs_replayed") != 0:
            log(f"R2: note: the landed tool replayed {old['stats'].get('certs_replayed')} certificate files")
    # R3: an allowed parent level dropped from the cells that read it, the window narrowed to match: the highest
    # parent level read at the first level (from 14 up) where every reader keeps another parent
    with Snapshot(run):
        summary = load(run / "run-summary.json")
        choice = None
        for n in (14, 15, 13):
            lists = {}
            for am_path in sorted(run.glob(f"{n}-*.manifest.json")):
                if am_path.name.count(".") == 2:
                    lists[int(am_path.name.split(".")[0].split("-")[1])] = \
                        [s["level"][1] for s in load(am_path)["parent_sources"]]
            if not lists or not any(lists.values()):
                continue
            top = max(pm for listed in lists.values() for pm in listed)
            readers = {m: listed for m, listed in lists.items() if top in listed}
            if all(len(listed) >= 2 for listed in readers.values()) and summary["windows"][str(n - 1)][0] <= top - 1:
                choice = (n, top, readers)
                break
        if choice is None:
            problems.append("R3: no level where a parent level can be dropped consistently")
        else:
            n, top, readers = choice
            for m, listed in readers.items():
                set_parents(run, n, m, [pm for pm in listed if pm != top])

            def narrow(s: dict) -> None:
                s["windows"][str(n - 1)] = [s["windows"][str(n - 1)][0], top - 1]
            summary_edit(run, narrow)
            log(f"R3 tampered: ({n - 1},{top}) dropped from the parents of {[(n, m) for m in readers]}, the "
                f"level-{n - 1} window narrowed to end at {top - 1}")
            old, new = both(run, "R3", "--check")
            expect_gap("R3", old, new, ["listed parent levels", "windows"])
    # R4: a consistent run with an unjustified root k
    top = set(g6_lines(root5 / "16-41.keep.g6")) if (root5 / "16-41.keep.g6").is_file() else set()
    log(f"R4 run-dag2.py --reach-root-k 5 at (16,41): top keep {len(top)} graphs, AMP's (16,41) graph present "
        f"{sum(1 for g in known if g in top)}/{len(known)}")
    old, new = both(root5, "R4", "--check")
    expect_gap("R4", old, new, ["root k 5", "not justified"])


# ---------------------------------------------------------------- F
def phase_f(jobs: int) -> None:
    dirs = []
    for i in (0, 1):
        out = RUNS / f"f-16-41-s{i}of2"
        code, wall = run_dag2(out, (16, 41), 398, jobs, ["--slice-level", "12", "--slice-index", str(i),
                                                         "--slice-count", "2"])
        log(f"F slice {i} of 2: run-dag2 exit {code} after {wall:.0f} s")
        r = chain(out, str(out), "--check")
        log(f"F slice {i} of 2: verify-chain --check exit {r['exit']}: {r['coverage']} / {r['last']}")
        if code != 0 or r["exit"] != 0 or r["last"] != "CHAIN OK" or "slice" not in " ".join(r["coverage"]):
            problems.append(f"F slice {i}: {r}")
        dirs.append(out)
    r = chain(dirs[0], "--summary-only", *map(str, dirs))
    fleet = (r["stats"].get("fleets") or [{}])[0]
    log(f"F --summary-only on both slices: exit {r['exit']}: {r['coverage']} / {r['last']}; slice partition "
        f"{fleet.get('slice_partition')}")
    if r["exit"] != 3 or not any("COVERAGE (summary only) OK" in x for x in r["coverage"]) or \
            not fleet.get("slice_partition") or any(v["sum"] != v["stage_file"] or v["slices_recording"] != 2
                                                    for v in fleet["slice_partition"].values()):
        problems.append(f"F summary-only fleet: {r}")
    r = chain(dirs[0], "--summary-only", str(dirs[0]))
    log(f"F --summary-only on slice 0 alone: exit {r['exit']}: {r['last']}; {r['problems'][:2]}")
    if r["exit"] != 1 or not any("have no summary ([1])" in p for p in r["problems"]):
        problems.append("F: a fleet missing slice 1 was not refused")
    with Snapshot(dirs[1]):
        def bump(s: dict) -> None:
            for e in s["levels"]:
                if e["n"] == 13 and not e.get("resumed") and e.get("parent_sources"):
                    for x in e["parent_sources"]:
                        x["records"] += 1
                    e["parents"] += len(e["parent_sources"])
                    e["shards"] = [{"range": [0, e["parents"]], "children": e["children"]}]
        summary_edit(dirs[1], bump)
        r = chain(dirs[0], "--summary-only", *map(str, dirs))
        log(f"F --summary-only with slice 1's records of its level-12 parents raised by one: exit {r['exit']}: "
            f"{r['last']}; {[p[:160] for p in r['problems'][:3]]}")
        if r["exit"] != 1 or not any("shares of (12," in p for p in r["problems"]):
            problems.append("F: a slice record that does not add up was not refused")


# ---------------------------------------------------------------- P
def prune_resumed(run: Path) -> dict[str, bool]:
    return {f"{e['n']}-{e['m']}": bool(e["prune"].get("resumed")) for e in load(run / "run-summary.json")["levels"]
            if isinstance(e.get("prune"), dict)}


def phase_p(run: Path, jobs: int) -> None:
    outputs = {p.name: h(p) for p in sorted(run.glob("*.keep.g6")) + sorted(run.glob("*.certs.jsonl"))}
    code, wall = run_dag2(run, (16, 41), 398, jobs, ["--resume"], fresh=False)
    states = prune_resumed(run)
    log(f"P green --resume: exit {code} after {wall:.0f} s; prune steps reused {sum(states.values())}/{len(states)}")
    if code != 0 or not states or not all(states.values()):
        problems.append(f"P green: not every prune step was reused: {states}")
    cell = "13-28"
    tamperings = {
        "target changed to (16,40)": lambda v: v.update(target=[16, 40]),
        "udcheck_rhombus.py sha256 zeroed": lambda v: v["software_sha256"].update({"udcheck_rhombus.py": "0" * 64}),
        "checker from the environment": lambda v: v["triangles_checker"].update(from_environment=True),
        "checker path changed": lambda v: v["triangles_checker"].update(path="/elsewhere/udcheck_rhombus.py"),
        "ACCEPT line emptied": lambda v: v.update(checker=""),
        "ACCEPT tu count changed": lambda v: v.update(checker=v["checker"].replace(" tu=", " tu=1", 1)),
        "verified counts emptied": lambda v: v.update(verified_counts={}),
    }
    for label, fn in tamperings.items():
        path = run / f"{cell}.prune.manifest.json"
        value = load(path)
        fn(value)
        dump(path, value)
        code, wall = run_dag2(run, (16, 41), 398, jobs, ["--resume"], fresh=False)
        states = prune_resumed(run)
        rerun = sorted(k for k, v in states.items() if not v)
        same = {p.name: h(p) for p in sorted(run.glob("*.keep.g6")) + sorted(run.glob("*.certs.jsonl"))} == outputs
        fresh = load(path)
        log(f"P {label}: --resume exit {code}; prune steps rerun {rerun}; outputs identical {same}; the manifest "
            f"rewritten clean {fresh.get('target') == [16, 41] and fresh.get('exit_status') == 0}")
        if code != 0 or rerun != [cell] or not same:
            problems.append(f"P {label}: rerun {rerun}, outputs identical {same}")
    env = {"PRUNE_UDCHECK_RHOMBUS": str(TREE / "check" / "udcheck_rhombus.py")}
    for label, extra_env, want_rerun in (("with $PRUNE_UDCHECK_RHOMBUS set", env, True),
                                         ("next, without it (the manifests record the environment's checker)", {}, True),
                                         ("once more", {}, False)):
        code, wall = run_dag2(run, (16, 41), 398, jobs, ["--resume"], env_extra=extra_env, fresh=False)
        states = prune_resumed(run)
        rerun = sum(1 for v in states.values() if not v)
        log(f"P --resume {label}: exit {code}; prune steps rerun {rerun}/{len(states)}")
        if code != 0 or (rerun == len(states)) != want_rerun or (not want_rerun and rerun):
            problems.append(f"P --resume {label}: {rerun} of {len(states)} rerun")
    r = chain(run, str(run), "--check")
    log(f"P after the resumes: verify-chain --check exit {r['exit']}: {r['last']}")
    if r["exit"] != 0 or r["last"] != "CHAIN OK":
        problems.append(f"P: the resumed directory is not CHAIN OK: {r['problems'][:3]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phases", default="G,R,F,P")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    phases = a.phases.split(",")
    for key in ("PRUNE_CHECK_CHUNK", "PRUNE_CHECK_PARALLEL_ABOVE", "PRUNE_UDCHECK_RHOMBUS"):
        os.environ.pop(key, None)
    RUNS.mkdir(parents=True, exist_ok=True)
    build_tree()
    shutil.copy2(UD / "enum" / "verify-chain.py", TREE / "enum" / "verify-chain.py")
    landed = subprocess.run(["git", "show", f"{LANDED_COMMIT}:research/unit-distance-22/enum/verify-chain.py"],
                            cwd=REPO, capture_output=True, check=True).stdout
    (TREE / "enum" / "verify-chain-landed.py").write_bytes(landed)
    log(f"scratch tree {TREE}; verify-chain.py new {sha256(TREE / 'enum' / 'verify-chain.py')[:12]}, landed "
        f"({LANDED_COMMIT}) {hashlib.sha256(landed).hexdigest()[:12]}; run-dag2.py {sha256(TREE / 'enum' / 'run-dag2.py')[:12]}")
    run = RUNS / "c-16-41-f398-tri"
    root5 = RUNS / "c-16-41-f398-tri-root5"
    if {"G", "R", "P"} & set(phases):
        code, wall = run_dag2(run, (16, 41), 398, a.jobs)
        log(f"run-dag2 (16,41) mode 398 --triangles: exit {code} after {wall:.0f} s")
        if code != 0:
            problems.append("the control run failed")
    if "G" in phases:
        phase_g(run)
    if "R" in phases:
        code, wall = run_dag2(root5, (16, 41), 398, a.jobs, ["--reach-root-k", "5"])
        log(f"run-dag2 (16,41) mode 398 --triangles --reach-root-k 5: exit {code} after {wall:.0f} s")
        phase_r(run, root5)
    if "F" in phases:
        phase_f(a.jobs)
    if "P" in phases:
        phase_p(run, a.jobs)
    for p in problems:
        log("PROBLEM:", p)
    log("VCHAIN", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
