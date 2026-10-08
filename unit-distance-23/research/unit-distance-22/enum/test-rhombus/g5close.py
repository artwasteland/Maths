#!/usr/bin/env python3
"""G5 round 2: the closure read's reproductions (research/unit-distance-23/results/g5-cross-model-2026-09-26/
G5-closure-read-gpt-6-astra.md) as red controls, the landed tools (LANDED_COMMIT, the commit it read) against the
fixed ones, each with a valid control that must still pass.

Fixture: the runbook itself (coordination/cloud-workers/u23-slice.sh, as runbook-rh.py runs it: (16,41), root k 4,
prune from 12, set 398, stage verification, U23_TRIANGLES=1, sliced 2 ways at level 12, G4 replay on), so the run
directories are the reader's dag-16-41-L12-tri-s0of2 and -s1of2 and the result directories carry the runbook's
hashes.json and replay/. Every tampering is made on a copy or restored byte for byte.

C1 (finding 1, FATAL) valid_prune on (13,29) of slice 0: its keep file with the unknown graph Lj??GPNHOetaeb
   (the canonical ancestor of AMP's (16,41) graph) replaced by the input's tu graph L?Kw_fbaaKpIPR in input order,
   and only the keep hash in the prune manifest updated. Landed: reused (True); fixed: rerun (False). Valid control:
   the untouched step is reused by both. End to end: run-dag2.py --resume on the tampered directory reruns that step
   and restores the keep file, and the directory is CHAIN OK.
C5 (finding 5) valid_prune: counts.tu alone changed; the ACCEPT line's tu and verified_counts.tu both 999 on a
   25-record cell; the manifest's target and the run's both (16,40), below the proved bound 41. Landed: reused;
   fixed: rerun. Valid control: every untouched prune step of both slices is reused by the fixed code.
C2 (finding 2, FATAL) verify-chain.py on the reader's fixture: target (23,65), seed 24 in all three files, root
   k 5, u-bar(22) = 60 recorded and justified, singleton windows and reach table, no levels, completed through 23,
   pruning with triangles and stage verification, --check. Landed: CHAIN OK, exit 0; fixed: CHAIN FAIL. Valid
   control: slice 0 with --check is CHAIN OK, also with its target, seed and slicing pinned; a wrong pin fails.
C3 (finding 3) --summary-only on the two slices' summaries: (a) slice 1's level-13 entries resumed with no
   history, and slice 0 claiming 75 records of the 74-record (12,24) (its parents total and shard end adjusted);
   (b) shares 80 and -6 of (12,24). Landed: COVERAGE OK; fixed: FAIL (and, for (a), slice 1's missing shares
   unresolved). Valid control: the untouched summaries give COVERAGE (summary only) OK.
C4 (finding 4) --summary-only: (a) the reader's case, the empty-target slice alone, its slice declared [12,0,0]
   and its level-13 entries resumed. Landed: COVERAGE OK; fixed: FAIL, also with the fleet pinned. With the
   result directories (hashes.json, replay/) and the fleet pinned (--expect-target 16 41 --expect-seed 10
   --expect-slices 12 2 --require-hashes --require-g4): the valid control gives COVERAGE OK; each of these fails:
   (b) a prefix file's hash changed in one slice, (c) a copy of slice 0 from another "worker" with a prefix hash
   changed, (d) one slice's G4 result FAIL, (e) one slice's G4 stage record of its (12,24) slice not re-derived,
   (f) its G4 record of that slice's size changed, (g) one slice's replay/ missing, (h) hashes.json naming another
   slice, (i) the fleet pinned at 3 slices.
Round 3 (G5-round3-read-gpt-6-astra.md, of LANDED_R3), landed = LANDED_R3:
C6 (finding 1) a duplicate of slice 0 (another worker) claiming 35 of (12,24) instead of 34, its parent total,
   shard end and G4 stage record matched, its hashes.json and cell counts kept: the landed tool's verdict depends
   on the argument order (OK one way, FAIL the other); the fixed one fails in both orders. Valid controls: an exact
   duplicate is OK in both orders; complementary copies (one records the shares of one level-13 cell, the other
   those of the rest) are OK once merged (the landed tool left a recorded share unresolved).
C7 (finding 2) on a copy of the running fleet's f01-jjpzl7/s0of1920 result directory, pinned to (23,65), seed 10,
   level 12, 1920 slices, hashes and G4 required (its 1919 missing slices are the only expected problem): the
   untouched record raises no other problem with either tool; (a) a seed level not identical and all_identical
   false with PASS kept, (b) EMPTY with exit 1 and nothing sampled for a slice holding 734 graphs of (12,20): the
   landed tool accepts both, the fixed one says the label is not what the evidence gives.
C8 (finding 3) slice 1's 25-record (13,28): counts.tu 11 -> 12, counts.tri_tu 1 -> 0, counts.survivors 14 -> 13,
   tri_survivors kept: the landed valid_prune reuses it, the fixed one reruns it; untouched, both reuse it.
Round 4 (G5-round4-read-gpt-6-astra.md, of LANDED_R4), landed = LANDED_R4:
C9 (finding 1) on a copy of the fleet's f01-jjpzl7/s0of1920, pinned and with hashes and G4 required: ONLY
   replay/summary.json per_cell[0].mismatches set to 1, or ONLY red_controls[0].went_red set to false, every
   aggregate and the fingerprint kept: the landed tool raises no problem but the missing slices, the fixed one
   refuses the G4 label. Valid control: the untouched record raises none with either tool.
C10 (finding 2) a genuine EMPTY slice: the runbook itself on (16,41) sliced 128 ways (102 level-12 records, so some
   slices are empty), a non-empty slice first (its full G4 replay), then an empty one (its slice-mode replay, EMPTY,
   exit 1, nothing sampled); audited together, pinned: the landed tool refuses the EMPTY slice (all_identical
   false), the fixed one accepts it. The same with its replay/summary.json built by the producer's own
   summarize([], ...) as the reader did: accepted. Red: that EMPTY evidence with the slice's summary recording a
   share of one graph: refused.
Round 5 (G5-round5-read-gpt-6-astra.md, of LANDED_R5), landed = LANDED_R5:
C11 C10's genuine EMPTY slice with (13,28) resumed as the driver writes it (parent fields removed, every count and
   the G4 evidence kept) and its fresh summary kept as history/original.json: the landed tool refuses it
   ("unconfirmed [[13, 28]]", the recovered record ignored), the fixed one accepts it. Reds, refused by both: the
   same with no history; the same with a history record showing parents in (13,28).
Round 6 (G5-round6-read-gpt-6-astra.md, of LANDED_R6), landed = LANDED_R6:
C12 two copies of C10's genuine EMPTY slice, A resuming (13,29) and (13,30), B resuming (13,28), no history, each
   cell's parent record fresh in the other copy, in both argument orders: the landed tool refuses them (each copy
   "unconfirmed"), the fixed one accepts them. Reds, refused by both in both orders: neither copy recording (13,28);
   complementary copies with B recording parents in (13,29); copies whose shares of (12,24) disagree (0 and 1). And
   the G4 per-cell binding: on a copy of the fleet record, one per_cell row's parents_in_cell (and its per_level)
   raised by one: the landed tool accepts it, the fixed one refuses it.
Round 7 (G5-round7-read-gpt-6-astra.md, of LANDED_R7), landed = LANDED_R7:
C13 bindings made against the merged records, on copies of the fleet record f01-jjpzl7/s0of1920: (a) the reader's
   copy A with (11,17) replayed with one parent more and resumed, copy B untouched, both orders: the landed tool
   accepts it, the fixed one refuses it; (b) copy A alone: the fixed tool leaves the row UNRESOLVED; (c) through the
   shared prefix: another worker's full-mode slice with the same mutation, audited with f01's untouched slice: the
   fixed tool refuses it; (d) copy A recording no share (its level-13 cells resumed) with its G4 record of the (12,20)
   slice file one larger, copy B untouched: the fixed tool binds A's record to B's share and refuses it. Valid
   control: two untouched copies.
Round 8 (G5-round8-read-gpt-6-astra.md, of LANDED_R8), landed = LANDED_R8:
C14 a G4 per_cell row's parents_in_cell and sampled must both be nonnegative integers before the sampling bound and
   the binding compare them, on copies of the fleet record f01-jjpzl7/s0of1920, with the sampled totals (per_level,
   the replay summary's and the fingerprint's sampled_parents) moved with each change and the production evidence
   kept: (a) the reader's (11,17) with parents_in_cell 31127.0 and 31128 sampled; (b) (16,36) with parents_in_cell
   true and 2 sampled; (c) (16,36) with parents_in_cell 1.0 and 2 sampled: the landed tool accepts each, the fixed
   one refuses the row. (d) Valid control: an untouched copy. Found hunting the family: (e) the target entry written
   (23, 65.0) with one child: the landed tool never audits it (its report counts no child at the target), the fixed
   one refuses the entry; (f) the source level [12, 20] of (13,23) written [12, 20.0] and the G4 record of the (12,20)
   slice file one larger: the landed tool never compares that record (it looks for 12-20.0.slice-0-of-1920.g6 and
   leaves the share UNRESOLVED), the fixed one refuses the recorded parents.

usage: g5close.py [--jobs 2]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

from rhlib import REPO, SCRATCH, UD, known_graphs, canonical, decode_g6, g6_lines, log

LANDED_COMMIT = "4120dd63c"   # the commit the closure read tested
LANDED_R3 = "4d2b1490b"       # the commit the round-3 read tested (C6-C8)
LANDED_R4 = "768cc0930"       # the commit the round-4 read tested (C9, C10)
LANDED_R5 = "7b3edd5c0"       # the commit the round-5 read tested (C11)
LANDED_R6 = "cca1769c8"       # the commit the round-6 read tested (C12)
LANDED_R7 = "57daa7c14"       # the commit the round-7 read tested (C13)
LANDED_R8 = "a3a38e37f6"      # the commit the round-8 read tested (C14)
RUNS = SCRATCH / "g5close"
# a real slice of the running (23,65) fleet, read-only, the untouched control of C7
FLEET_SLICE = Path("<scratch>/scratchpad/fleet/results/"
                   "f01-jjpzl7/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s0of1920")
MATHS_PY = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"
RUNBOOK = REPO / "coordination" / "cloud-workers" / "u23-slice.sh"
REMOVED, INSERTED = "Lj??GPNHOetaeb", "L?Kw_fbaaKpIPR"   # the reader's two graphs of (13,29)
problems: list[str] = []


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def landed_source(rel: str, commit: str = LANDED_COMMIT) -> str:
    return subprocess.run(["git", "show", f"{commit}:research/unit-distance-22/{rel}"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout


def module_from_source(name: str, source: str, pretend_file: Path):
    """A module from source text, with __file__ set to a path beside the tree's own scripts (so that its
    checkers and prune.py are found where the landed code looks for them)."""
    module = types.ModuleType(name)
    module.__file__ = str(pretend_file)
    exec(compile(source, str(pretend_file), "exec"), module.__dict__)
    return module


def module_from_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def chain(*args: str, landed: bool | str = False) -> dict:
    """verify-chain.py: the fixed one, or landed=True (LANDED_COMMIT), or "r3" to "r8" (LANDED_R3 to LANDED_R8)."""
    script = (RUNS / f"verify-chain-landed-{landed}.py" if landed in ("r3", "r4", "r5", "r6", "r7", "r8") else
              RUNS / "verify-chain-landed.py" if landed else UD / "enum" / "verify-chain.py")
    p = subprocess.run(["nice", "-n", "10", sys.executable, str(script), *args], capture_output=True, text=True)
    out = p.stdout.strip().splitlines()
    return {"exit": p.returncode, "last": out[-1] if out else p.stderr.strip()[-300:],
            "problems": [x[len("PROBLEM: "):] for x in out if x.startswith("PROBLEM: ")],
            "unresolved": [x[len("UNRESOLVED: "):] for x in out if x.startswith("UNRESOLVED: ")],
            "coverage": [x for x in out if x.startswith("COVERAGE")], "report": report_line(out)}


def report_line(out: list[str]) -> dict:
    """verify-chain.py's JSON report line ({} when there is none)."""
    for x in out:
        if x.startswith("{"):
            try:
                return json.loads(x)
            except ValueError:
                return {}
    return {}


def show(label: str, r: dict) -> None:
    log(f"{label}: exit {r['exit']}: {(r['coverage'] or [''])[0][:110]} / {r['last'][:130]}")
    for p in r["problems"][:4]:
        log(f"      PROBLEM: {p[:260]}")
    for u in r["unresolved"][:3]:
        log(f"      UNRESOLVED: {u[:260]}")


class Restore:
    """Tamper files in place and restore them byte for byte afterwards."""
    def __init__(self, *paths: Path):
        self.saved = {p: p.read_bytes() for p in paths}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for p, data in self.saved.items():
            p.write_bytes(data)
        if any(p.read_bytes() != data for p, data in self.saved.items()):
            problems.append(f"files not restored: {list(self.saved)}")


# ---------------------------------------------------------------- the fixture
def runbook_fixture(jobs: int) -> tuple[dict, dict]:
    env = dict(os.environ)
    env.update({"U23_TARGET_N": "16", "U23_TARGET_M": "41", "U23_ROOT_K": "4", "U23_PRUNE_FROM": "12",
                "U23_SLICE_LEVEL": "12", "U23_OUT": str(RUNS / "out"), "U23_RES": str(RUNS / "res"), "U23_PUSH": "0",
                "U23_TOOLCHAIN": "0", "JOBS": str(jobs), "PY": str(MATHS_PY), "U23_RHOMBUS": "0", "U23_TRIANGLES": "1",
                "U23_CLEANUP": "0",    # keep the run directories (the runbook deletes them after the results by default)
                "U23_MIN_FREE_GB": "0"})   # the fixture needs under 100 MB; the production guard wants 5 GB free
    for key in ("PRUNE_UDCHECK_RHOMBUS", "U23_RHOMBUS_CHECKER", "U23_PRUNE_FILTER_SET"):
        env.pop(key, None)
    with (RUNS / "runbook.log").open("w") as stream:
        p = subprocess.run(["nice", "-n", "10", "bash", str(RUNBOOK), "2", "0", "1"], env=env, stdout=stream,
                           stderr=subprocess.STDOUT, cwd=REPO)
    text = (RUNS / "runbook.log").read_text()
    log(f"fixture: the runbook, (16,41) --triangles sliced 2 ways at level 12: exit {p.returncode}; "
        f"{[x for x in text.splitlines() if 'G4 replay of slice' in x]}")
    if p.returncode != 0:
        raise SystemExit(f"the runbook failed: {text[-2000:]}")
    out = {s: RUNS / "out" / f"dag-16-41-L12-tri-s{s}of2" for s in (0, 1)}
    res = {s: RUNS / "res" / "16-41-L12-tri" / f"s{s}of2" for s in (0, 1)}
    return out, res


# ---------------------------------------------------------------- C1, C5
def prune_args(target_m: int = 41) -> argparse.Namespace:
    return argparse.Namespace(target_n=16, target_m=target_m, forbidden_set=398, rule="triangles", prune_filter_set=None)


def valid(module, run: Path, n: int, m: int, args=None) -> bool:
    return bool(module.valid_prune(args or prune_args(), run / f"{n}-{m}.prune.manifest.json",
                                   run / f"{n}-{m}.reach.g6", run, n, m))


def resume(run: Path, jobs: int) -> int:
    cfg = load(run / "run-config.json")
    cmd = ["nice", "-n", "10", sys.executable, str(UD / "enum" / "run-dag2.py"), "--target-n", "16", "--target-m", "41",
           "--output-dir", str(run), "--jobs", str(jobs), "--forbidden-set", "398", "--reach", "--reach-root-k", "4",
           "--ubar", "22=60", "--ubar-justification", cfg["ubar_justification"], "--prune", "--prune-from", "12",
           "--prune-filter-only", "--prune-python", str(MATHS_PY), "--triangles", "--verify-stages",
           "--slice-level", "12", "--slice-index", str(cfg["slice"][1]), "--slice-count", "2", "--resume"]
    env = dict(os.environ)
    env.pop("PRUNE_UDCHECK_RHOMBUS", None)
    with (RUNS / "resume.log").open("a") as stream:
        return subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env).returncode


def phase_c1_c5(out: dict, jobs: int) -> None:
    fixed = module_from_file("run_dag2_fixed", UD / "enum" / "run-dag2.py")
    landed = module_from_source("run_dag2_landed", landed_source("enum/run-dag2.py"), UD / "enum" / "run-dag2-landed.py")
    run = out[0]
    source, keep, pm_path = run / "13-29.reach.g6", run / "13-29.keep.g6", run / "13-29.prune.manifest.json"
    records = {json.loads(x)["g6"]: json.loads(x)["verdict"] for x in (run / "13-29.certs.jsonl").read_text().splitlines()}
    kept = g6_lines(keep)
    log(f"C1 fixture (13,29) of slice 0: {len(records)} records, keep {len(kept)}; {REMOVED} {records.get(REMOVED)} and "
        f"kept {REMOVED in kept}; {INSERTED} {records.get(INSERTED)}")
    if records.get(REMOVED) != "unknown" or REMOVED not in kept or records.get(INSERTED) != "tu":
        problems.append("C1: the fixture is not the reader's ((13,29) does not hold the two graphs as described)")
        return
    both = (valid(landed, run, 13, 29), valid(fixed, run, 13, 29))
    log(f"C1 valid control, (13,29) untouched: landed reuses {both[0]}, fixed reuses {both[1]}")
    if both != (True, True):
        problems.append(f"C1 valid control: {both}")
    with Restore(keep, pm_path):
        order = g6_lines(source)
        new = [c for c in order if (c in kept and c != REMOVED) or c == INSERTED]
        keep.write_text("".join(c + "\n" for c in new))
        v = load(pm_path)
        v["outputs_sha256"][str(keep)] = sha(keep)
        dump(pm_path, v)
        both = (valid(landed, run, 13, 29), valid(fixed, run, 13, 29))
        log(f"C1 red: keep = input order with {REMOVED} out and {INSERTED} in ({len(new)} records), only the keep hash "
            f"updated: landed reuses {both[0]}, fixed reuses {both[1]}")
        if both != (True, False):
            problems.append(f"C1 red: landed/fixed {both}, expected (True, False)")
        code = resume(run, jobs)
        summary = load(run / "run-summary.json")
        entry = next(e for e in summary["levels"] if (e["n"], e["m"]) == (13, 29))
        restored = REMOVED in g6_lines(keep) and INSERTED not in g6_lines(keep)
        log(f"C1 end to end: run-dag2.py --resume exit {code}; (13,29) prune step rerun "
            f"{entry['prune'].get('resumed') is False}; the keep file holds {REMOVED} again and not {INSERTED}: {restored}")
        if code != 0 or entry["prune"].get("resumed") is not False or not restored:
            problems.append("C1 end to end: the resumed run did not rerun and restore the tampered step")
        r = chain(str(run), "--check")
        log(f"C1 end to end: verify-chain --check after the rerun: exit {r['exit']}: {r['last']}")
        if r["exit"] != 0:
            problems.append(f"C1 end to end: not CHAIN OK after the rerun: {r['problems'][:2]}")
    # C5
    sizes = {s: {p.name.split(".")[0]: len(p.read_text().splitlines()) for p in sorted(r.glob("*.certs.jsonl"))}
             for s, r in out.items()}
    found25 = [(s, stem) for s in (1, 0) for stem, k in sizes[s].items() if k == 25]
    log(f"C5 certificate files by size: {sizes}; 25-record cells: {found25}")
    if not found25:
        problems.append("C5: no 25-record cell (the reader's fixture differs)")
        return
    slice25, cell25 = found25[0]
    reds = []

    def counts_tu(v: dict) -> None:
        v["counts"]["tu"] += 1

    def accept_999(v: dict) -> None:
        v["checker"] = re.sub(r"( tu=)\d+", r"\g<1>999", v["checker"], count=1)
        v["verified_counts"]["tu"] = 999
    reds.append(("counts.tu alone changed, slice 0's (13,29)", 0, "13-29", counts_tu, None))
    reds.append((f"ACCEPT tu and verified tu both 999 on the 25-record cell, slice {slice25}'s {cell25}", slice25,
                 cell25, accept_999, None))
    reds.append(("target (16,40) in the manifest and the run, below u(16) <= 41, slice 0's (13,29)", 0, "13-29",
                 lambda v: v.update(target=[16, 40]), prune_args(40)))
    for label, s, stem, fn, args in reds:
        n, m = map(int, stem.split("-"))
        path = out[s] / f"{stem}.prune.manifest.json"
        with Restore(path):
            v = load(path)
            fn(v)
            dump(path, v)
            both = (valid(landed, out[s], n, m, args), valid(fixed, out[s], n, m, args))
        log(f"C5 red, {label}: landed reuses {both[0]}, fixed reuses {both[1]}")
        if both != (True, False):
            problems.append(f"C5 {label}: landed/fixed {both}, expected (True, False)")
    for s, r in out.items():
        cells = sorted(p.name.split(".")[0] for p in r.glob("*.prune.manifest.json"))
        reused = [c for c in cells if valid(fixed, r, *map(int, c.split("-")))]
        log(f"C5 valid control, slice {s}: the fixed code reuses {len(reused)} of {len(cells)} untouched prune steps")
        if len(reused) != len(cells):
            problems.append(f"C5 valid control slice {s}: not reused {sorted(set(cells) - set(reused))}")


# ---------------------------------------------------------------- C2
def phase_c2(out: dict) -> None:
    fixture = RUNS / "seed24"
    fixture.mkdir()
    ubar = {**{str(k): v for k, v in {0: 0, 1: 0, 2: 1, 3: 3, 4: 5, 5: 7, 6: 9, 7: 12, 8: 14, 9: 18, 10: 20, 11: 23,
                                    12: 27, 13: 30, 14: 33, 15: 37, 16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57,
                                    22: 60, 23: 66}.items()}}
    override = {"22": {"builtin": 62, "value": 60}}
    justification = "u(22) = 60 (research/unit-distance-22/RESULT-u22.md)"
    config = {"target": [23, 65], "seed_n": 24, "reach": True, "reach_root_k": 5, "prune": True, "prune_from": 12,
              "prune_filter_only": True, "prune_tries": 0, "prune_max_states": 400, "slice": None, "forbidden_set": 398,
              "ubar_override": override, "ubar_justification": justification, "verify_stages": True, "triangles": True}
    reach = {"target": [23, 65], "seed_n": 24, "root_k": 5, "root_k_source": "command line --reach-root-k",
             "ubar": ubar, "table": {"23": {"65": 5}}, "schade_windows": {"23": [65, 65]},
             "ubar_override": override, "ubar_justification": justification}
    summary = {"target": [23, 65], "seed_n": 24, "windows": {"23": [65, 65]},
               "reach": {"enabled": True, "root_k": 5, "levels": {"23": [65]}},
               "prune": {"enabled": True, "prune_from": 12, "prune_filter_only": True}, "slice": None,
               "forbidden_set": 398, "ubar_override": override, "ubar_justification": justification,
               "verify_stages": True, "triangles": True, "completed_through_n": 23, "levels": []}
    for name, value in (("run-config.json", config), ("reach.json", reach), ("run-summary.json", summary)):
        dump(fixture / name, value)
    old, new = chain(str(fixture), "--check", landed=True), chain(str(fixture), "--check")
    show("C2 red, the reader's seed-24 fixture, landed", old)
    show("C2 red, the reader's seed-24 fixture, fixed", new)
    if old["exit"] != 0 or old["last"] != "CHAIN OK":
        log("C2: note: the landed tool did not accept it")
    if new["exit"] != 1 or not any("seed level 24" in p for p in new["problems"]):
        problems.append(f"C2: the fixed tool did not refuse seed 24: {new['last']}")
    pins = ["--expect-target", "16", "41", "--expect-seed", "10", "--expect-slices", "12", "2"]
    for label, args, want in (("slice 0, --check", ["--check"], 0), ("slice 0, --check, pinned", ["--check", *pins], 0),
                              ("slice 0 pinned to seed 9", ["--check", *pins[:3], "--expect-seed", "9"], 1),
                              ("slice 0 pinned to target (16,40)", ["--expect-target", "16", "40"], 1),
                              ("slice 0 pinned to 3 slices", ["--expect-slices", "12", "3"], 1)):
        r = chain(str(out[0]), *args)
        show(f"C2 {'valid control' if want == 0 else 'red'}: {label}", r)
        if r["exit"] != want:
            problems.append(f"C2 {label}: exit {r['exit']}, expected {want}")


# ---------------------------------------------------------------- C3, C4
def summaries_copy(res: dict, dest: Path, with_evidence: bool = False, slices=(0, 1)) -> dict:
    dirs = {}
    for s in slices:
        d = dest / f"s{s}of2"
        if with_evidence:
            shutil.copytree(res[s], d)
        else:
            d.mkdir(parents=True)
            for name in ("run-config.json", "run-summary.json", "reach.json"):
                shutil.copy2(res[s] / name, d / name)
        dirs[s] = d
    return dirs


def set_share(summary: dict, level: int, pm: int, share: int) -> int:
    """Every level-(level+1) entry of this slice that reads (level, pm): its record of that slice set to `share`,
    its parents total and its last shard's end moved by the same amount. Returns how many entries changed."""
    changed = 0
    for e in summary["levels"]:
        if e["n"] != level + 1 or e.get("resumed"):
            continue
        for s in e.get("parent_sources", []):
            if s["level"] == [level, pm]:
                delta = share - s["records"]
                s["records"] = share
                e["parents"] += delta
                e["shards"][-1]["range"][1] += delta
                changed += 1
    return changed


def resume_level(summary: dict, n: int) -> None:
    for e in summary["levels"]:
        if e["n"] == n:
            for key in ("parent_edge_counts", "reach_k", "parent_sources", "parents", "shards"):
                e.pop(key, None)
            e["resumed"] = True


def phase_c3(res: dict) -> None:
    base = RUNS / "c3"
    dirs = summaries_copy(res, base / "valid")
    old, new = (chain("--summary-only", *map(str, dirs.values()), landed=True),
                chain("--summary-only", *map(str, dirs.values())))
    show("C3 valid control, the two untouched summaries, landed", old)
    show("C3 valid control, fixed", new)
    if new["exit"] != 3 or not any("COVERAGE (summary only) OK" in x for x in new["coverage"]):
        problems.append(f"C3 valid control: {new['last']}")
    # (a) slice 1's level-13 entries resumed with no history; slice 0 claims 75 of the 74-record (12,24)
    dirs = summaries_copy(res, base / "a")
    s0, s1 = load(dirs[0] / "run-summary.json"), load(dirs[1] / "run-summary.json")
    whole = next(e for e in s0["levels"] if (e["n"], e["m"]) == (12, 24))["prune"]["counts"]["kept"]
    changed = set_share(s0, 12, 24, 75)
    resume_level(s1, 13)
    dump(dirs[0] / "run-summary.json", s0)
    dump(dirs[1] / "run-summary.json", s1)
    old, new = (chain("--summary-only", *map(str, dirs.values()), landed=True),
                chain("--summary-only", *map(str, dirs.values())))
    log(f"C3 (a): (12,24) holds {whole}; slice 0 claims 75 in {changed} entries; slice 1's level 13 resumed")
    show("C3 red (a), landed", old)
    show("C3 red (a), fixed", new)
    if new["exit"] != 1 or not any("75" in p for p in new["problems"]):
        problems.append(f"C3 (a): the fixed tool did not refuse 75 of {whole}: {new['last']}")
    # (b) shares 80 and -6
    dirs = summaries_copy(res, base / "b")
    s0, s1 = load(dirs[0] / "run-summary.json"), load(dirs[1] / "run-summary.json")
    c0, c1 = set_share(s0, 12, 24, 80), set_share(s1, 12, 24, -6)
    dump(dirs[0] / "run-summary.json", s0)
    dump(dirs[1] / "run-summary.json", s1)
    old, new = (chain("--summary-only", *map(str, dirs.values()), landed=True),
                chain("--summary-only", *map(str, dirs.values())))
    log(f"C3 (b): shares 80 ({c0} entries) and -6 ({c1} entries) of (12,24)")
    show("C3 red (b), landed", old)
    show("C3 red (b), fixed", new)
    if new["exit"] != 1 or not any("-6" in p for p in new["problems"]):
        problems.append(f"C3 (b): the fixed tool did not refuse a share of -6: {new['last']}")


def phase_c4(res: dict, out: dict) -> None:
    base = RUNS / "c4"
    pins = ["--expect-target", "16", "41", "--expect-seed", "10", "--expect-slices", "12", "2"]
    # (a) the reader's case: the empty-target slice alone, declared [12,0,0], its level-13 entries resumed
    empty = next(s for s in (0, 1) if load(res[s] / "run-summary.json")["levels"][-1]["children"] == 0)
    kept_top = {s: len(g6_lines(out[s] / "16-41.keep.g6")) for s in (0, 1)}
    dirs = summaries_copy(res, base / "a", slices=(empty,))
    d = dirs[empty]
    for name in ("run-config.json", "run-summary.json"):
        v = load(d / name)
        v["slice"] = [12, 0, 0]
        if name == "run-summary.json":
            resume_level(v, 13)
        dump(d / name, v)
    log(f"C4 (a): slice {empty} has the empty target (top keep sizes {kept_top}); it alone, declared [12,0,0], "
        f"level 13 resumed")
    old, new, newp = (chain("--summary-only", str(d), landed=True), chain("--summary-only", str(d)),
                      chain("--summary-only", str(d), *pins))
    show("C4 red (a), landed", old)
    show("C4 red (a), fixed", new)
    show("C4 red (a), fixed, pinned", newp)
    if new["exit"] != 1 or newp["exit"] != 1 or not any("[12, 0, 0]" in p for p in new["problems"]):
        problems.append(f"C4 (a): the fixed tool did not refuse slice count 0: {new['last']} / {newp['last']}")
    # the result directories themselves, pinned, with hashes.json and the G4 replays required
    strict = ["--require-hashes", "--require-g4", *pins]
    valid_dirs = summaries_copy(res, base / "valid", with_evidence=True)
    new = chain("--summary-only", *map(str, valid_dirs.values()), *strict)
    show("C4 valid control, both result directories, pinned, hashes and G4 required", new)
    if new["exit"] != 3:
        problems.append(f"C4 valid control: {new['last']} {new['problems'][:3]} {new['unresolved'][:3]}")

    def red(label: str, edit, expect: str, extra_copy: bool = False) -> None:
        dirs = summaries_copy(res, base / label.split()[0].strip("()"), with_evidence=True)
        extra = []
        if extra_copy:
            twin = base / label.split()[0].strip("()") / "other-worker" / "s0of2"
            shutil.copytree(res[0], twin)
            extra = [twin]
            edit(twin)
        else:
            edit(dirs)
        old = chain("--summary-only", *map(str, dirs.values()), *map(str, extra), landed=True)
        new = chain("--summary-only", *map(str, dirs.values()), *map(str, extra), *strict)
        show(f"C4 red {label}, landed", old)
        show(f"C4 red {label}, fixed", new)
        if new["exit"] != 1 or not any(expect in p for p in new["problems"]):
            problems.append(f"C4 {label}: the fixed tool did not refuse it ({expect}): {new['last']} {new['problems'][:2]}")

    def prefix_hash(dirs) -> None:
        h = load(dirs[1] / "hashes.json")
        h["files"]["12-24.keep.g6"]["sha256"] = "0" * 64
        dump(dirs[1] / "hashes.json", h)

    def twin_hash(twin: Path) -> None:
        h = load(twin / "hashes.json")
        name = next(x for x in sorted(h["files"]) if x.startswith("11-") and x.endswith(".reach.g6"))
        h["files"][name]["sha256"] = "f" * 64
        dump(twin / "hashes.json", h)

    def g4_fail(dirs) -> None:
        f = load(dirs[1] / "replay" / "fingerprint.json")
        f["result"] = "FAIL"
        dump(dirs[1] / "replay" / "fingerprint.json", f)

    def g4_stage(key: str, value):
        def edit(dirs) -> None:
            s = load(dirs[0] / "replay" / "summary.json")
            for st in s["stages"]:
                if st.get("source") == "12-24.slice-0-of-2.g6":
                    st[key] = value
            dump(dirs[0] / "replay" / "summary.json", s)
        return edit

    def no_replay(dirs) -> None:
        shutil.rmtree(dirs[1] / "replay")

    def other_slice(dirs) -> None:
        h = load(dirs[1] / "hashes.json")
        h["slice"] = [12, 0, 2]
        dump(dirs[1] / "hashes.json", h)
    red("(b) a prefix file's hash changed in slice 1", prefix_hash, "prefix files differ")
    red("(c) a copy of slice 0 from another worker, one prefix hash changed", twin_hash, "prefix files differ",
        extra_copy=True)
    red("(d) slice 1's G4 result FAIL", g4_fail, "G4 replay says 'FAIL'")
    red("(e) slice 0's G4 record of its (12,24) slice not re-derived", g4_stage("status", "differs"),
        "12-24.slice-0-of-2.g6")
    red("(f) slice 0's G4 record of its (12,24) slice size changed", g4_stage("derived_records", 999),
        "12-24.slice-0-of-2.g6")
    red("(g) slice 1's replay/ missing", no_replay, "no G4 replay")
    red("(h) slice 1's hashes.json naming slice 0", other_slice, "hashes.json slice")
    dirs = summaries_copy(res, base / "i", with_evidence=True)
    new = chain("--summary-only", *map(str, dirs.values()), "--require-hashes", "--require-g4", "--expect-target", "16",
                "41", "--expect-seed", "10", "--expect-slices", "12", "3")
    show("C4 red (i) the fleet pinned at 3 slices, fixed", new)
    if new["exit"] != 1 or not any("pinned 3" in p for p in new["problems"]):
        problems.append(f"C4 (i): {new['last']}")


# ---------------------------------------------------------------- round 3: C6, C7, C8
def resume_cells(summary: dict, cells: set) -> None:
    for e in summary["levels"]:
        if (e["n"], e["m"]) in cells:
            for key in ("parent_edge_counts", "reach_k", "parent_sources", "parents", "shards"):
                e.pop(key, None)
            e["resumed"] = True


def phase_c6(res: dict) -> None:
    """Round 3, finding 1: copies of one slice with different shares, in both argument orders; and complementary
    copies whose shares only together cover the slice."""
    base = RUNS / "c6"
    strict = ["--require-hashes", "--require-g4", "--expect-target", "16", "41", "--expect-seed", "10",
              "--expect-slices", "12", "2"]
    for label, claim in (("an exact duplicate of slice 0", None), ("a duplicate of slice 0 claiming 35 of (12,24)", 35)):
        dirs = summaries_copy(res, base / ("same" if claim is None else "claim"), with_evidence=True)
        twin = base / ("same" if claim is None else "claim") / "other-worker" / "s0of2"
        shutil.copytree(res[0], twin)
        if claim is not None:
            s = load(twin / "run-summary.json")
            own = set_share(s, 12, 24, claim)
            dump(twin / "run-summary.json", s)
            r = load(twin / "replay" / "summary.json")
            for st in r["stages"]:
                if st.get("source") == "12-24.slice-0-of-2.g6":
                    st["records"] = st["derived_records"] = claim
            dump(twin / "replay" / "summary.json", r)
            log(f"C6 {label}: {own} entries changed; its hashes.json and cell counts kept, its G4 stage record matched")
        results = {}
        for order, runs in (("original first", [dirs[0], twin, dirs[1]]), ("duplicate first", [twin, dirs[0], dirs[1]])):
            old = chain("--summary-only", *map(str, runs), *strict, landed="r3")
            new = chain("--summary-only", *map(str, runs), *strict)
            show(f"C6 {label}, {order}, landed", old)
            show(f"C6 {label}, {order}, fixed", new)
            results[order] = (old["exit"], new["exit"])
        want_fixed = 3 if claim is None else 1
        if any(fixed != want_fixed for _, fixed in results.values()):
            problems.append(f"C6 {label}: fixed exits {results}, expected {want_fixed} in both orders")
        if claim is not None and len({landed for landed, _ in results.values()}) != 2:
            log(f"C6 {label}: note: the landed tool gave the same exit in both orders {results}")
    # complementary copies: copy A records the shares of one level-13 cell, copy B those of the others
    s0 = load(res[0] / "run-summary.json")
    fresh13 = {(e["n"], e["m"]): {x["level"][1] for x in e.get("parent_sources", [])}
               for e in s0["levels"] if e["n"] == 13 and not e.get("resumed")}
    first = min(fresh13)
    others = set(fresh13) - {first}
    a_shares, b_shares = fresh13[first], set().union(*(fresh13[c] for c in others)) if others else set()
    dirs = summaries_copy(res, base / "complementary", with_evidence=True, slices=(1,))
    copies = {}
    for name, resumed in (("copy-a", others), ("copy-b", {first})):
        d = base / "complementary" / name / "s0of2"
        shutil.copytree(res[0], d)
        s = load(d / "run-summary.json")
        resume_cells(s, resumed)
        dump(d / "run-summary.json", s)
        copies[name] = d
    log(f"C6 complementary copies of slice 0: copy A records the shares {sorted(a_shares)} (only {first} fresh), "
        f"copy B {sorted(b_shares)} ({sorted(others)} fresh); only A records {sorted(a_shares - b_shares)}")
    runs = [copies["copy-a"], copies["copy-b"], dirs[1]]
    old = chain("--summary-only", *map(str, runs), *strict, landed="r3")
    new = chain("--summary-only", *map(str, runs), *strict)
    show("C6 complementary copies, landed", old)
    show("C6 complementary copies, fixed", new)
    if new["exit"] != 3:
        problems.append(f"C6 complementary copies: the fixed tool exits {new['exit']}: {new['problems'][:2]} "
                        f"{new['unresolved'][:2]}")


def phase_c7() -> None:
    """Round 3, finding 2: G4 evidence contradicting its label, on a real slice of the running (23,65) fleet."""
    base = RUNS / "c7"
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "23", "65", "--expect-seed", "10",
            "--expect-slices", "12", "1920"]
    share = None
    for e in load(FLEET_SLICE / "run-summary.json")["levels"]:
        for x in (e.get("parent_sources") or []) if e["n"] == 13 else []:
            if x["level"] == [12, 20]:
                share = x["records"]
    log(f"C7 fixture: a copy of the fleet's f01-jjpzl7/s0of1920 result directory, whose share of (12,20) is {share}")

    def case(name: str, edit) -> tuple[dict, dict]:
        d = base / name / "s0of1920"
        shutil.copytree(FLEET_SLICE, d)
        edit(d)
        return chain(str(d), *pins, landed="r3"), chain(str(d), *pins)

    def g4_problems(r: dict) -> list[str]:
        return [p for p in r["problems"] if "have no summary" not in p]
    old, new = case("untouched", lambda d: None)
    show("C7 valid control, the untouched record, landed", old)
    show("C7 valid control, fixed", new)
    if g4_problems(new) or new["unresolved"]:
        problems.append(f"C7 valid control: {g4_problems(new)[:2]} {new['unresolved'][:2]}")

    def seeds(d: Path) -> None:
        s = load(d / "replay" / "summary.json")
        s["seeds"][0]["identical"] = False
        s["all_identical"] = False
        dump(d / "replay" / "summary.json", s)

    def empty(d: Path) -> None:
        f = load(d / "replay" / "fingerprint.json")
        f.update(result="EMPTY", replay_exit=1, sampled_parents=0, mode="slice")
        dump(d / "replay" / "fingerprint.json", f)
        s = load(d / "replay" / "summary.json")
        s.update(sampled_parents=0, processed_parents=0)
        dump(d / "replay" / "summary.json", s)
    for label, edit in (("a seed level not identical, all_identical false, PASS kept", seeds),
                        (f"EMPTY, exit 1, nothing sampled, for the slice holding {share} graphs of (12,20)", empty)):
        old, new = case(label.split(",")[0].replace(" ", "-"), edit)
        show(f"C7 red, {label}, landed", old)
        show(f"C7 red, {label}, fixed", new)
        if g4_problems(old):
            log(f"C7 {label}: note: the landed tool refused it too")
        if new["exit"] != 1 or not any("G4 replay says" in p for p in g4_problems(new)):
            problems.append(f"C7 {label}: the fixed tool did not refuse it: {g4_problems(new)[:2]}")


def phase_c8(out: dict) -> None:
    """Round 3, finding 3: the rule's own counts reassigned while every total is kept."""
    fixed = module_from_file("run_dag2_fixed_r3", UD / "enum" / "run-dag2.py")
    landed = module_from_source("run_dag2_landed_r3", landed_source("enum/run-dag2.py", LANDED_R3),
                                UD / "enum" / "run-dag2-landed.py")
    run, stem = out[1], "13-28"
    path = run / f"{stem}.prune.manifest.json"
    c = load(path)["counts"]
    log(f"C8 fixture: slice 1's {stem} ({len((run / f'{stem}.certs.jsonl').read_text().splitlines())} records): "
        f"counts tu {c['tu']}, tri_tu {c['tri_tu']}, survivors {c['survivors']}, tri_survivors {c['tri_survivors']}")
    both = (valid(landed, run, 13, 28), valid(fixed, run, 13, 28))
    log(f"C8 valid control, untouched: landed reuses {both[0]}, fixed reuses {both[1]}")
    if both != (True, True):
        problems.append(f"C8 valid control: {both}")
    with Restore(path):
        v = load(path)
        v["counts"].update(tu=v["counts"]["tu"] + 1, tri_tu=v["counts"]["tri_tu"] - 1,
                           survivors=v["counts"]["survivors"] - 1)
        dump(path, v)
        both = (valid(landed, run, 13, 28), valid(fixed, run, 13, 28))
    log(f"C8 red, counts.tu +1, counts.tri_tu -1, counts.survivors -1 (tri_survivors kept): landed reuses {both[0]}, "
        f"fixed reuses {both[1]}")
    if both != (True, False):
        problems.append(f"C8 red: landed/fixed {both}, expected (True, False)")


# ---------------------------------------------------------------- round 4: C9, C10
def g4_only(r: dict) -> list[str]:
    """The problems of a summary-only run other than the expected missing slices."""
    return [p for p in r["problems"] if "have no summary" not in p]


def phase_c9() -> None:
    """Round 4, finding 1: a failure in the replay's detailed records under clean aggregates, on a copy of the
    running fleet's f01-jjpzl7/s0of1920."""
    base = RUNS / "c9"
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "23", "65", "--expect-seed", "10",
            "--expect-slices", "12", "1920"]

    def case(name: str, edit) -> tuple[dict, dict]:
        d = base / name / "s0of1920"
        shutil.copytree(FLEET_SLICE, d)
        edit(d)
        return chain(str(d), *pins, landed="r4"), chain(str(d), *pins)

    def per_cell_mismatch(d: Path) -> None:
        s = load(d / "replay" / "summary.json")
        s["per_cell"][0]["mismatches"] = 1
        dump(d / "replay" / "summary.json", s)

    def red_not_red(d: Path) -> None:
        s = load(d / "replay" / "summary.json")
        s["red_controls"][0]["went_red"] = False
        dump(d / "replay" / "summary.json", s)
    old, new = case("untouched", lambda d: None)
    show("C9 valid control, the untouched fleet record, landed", old)
    show("C9 valid control, fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C9 valid control: {g4_only(new)[:2]}")
    for label, edit in (("only per_cell[0].mismatches set to 1", per_cell_mismatch),
                        ("only red_controls[0].went_red set to false", red_not_red)):
        old, new = case(label.split()[1].replace("[", "").replace("]", "").replace(".", "-"), edit)
        show(f"C9 red, {label}, landed", old)
        show(f"C9 red, {label}, fixed", new)
        if g4_only(old):
            log(f"C9 {label}: note: the landed tool refused it too")
        if new["exit"] != 1 or not any("G4 replay says" in p for p in g4_only(new)):
            problems.append(f"C9 {label}: the fixed tool did not refuse it: {g4_only(new)[:2]}")


def slice_of(code: str, count: int) -> int:
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big") % count


def phase_c10(jobs: int) -> tuple[str, Path] | None:
    """Round 4, finding 2: a genuine EMPTY slice, produced by the runbook itself, and one built with the producer's
    own summarize([], ...) as the reader did; both must be accepted; one of them with a share raised must not."""
    base = RUNS / "c10"
    count = 128
    env = dict(os.environ)
    env.update({"U23_TARGET_N": "16", "U23_TARGET_M": "41", "U23_ROOT_K": "4", "U23_PRUNE_FROM": "12",
                "U23_SLICE_LEVEL": "12", "U23_OUT": str(base / "out"), "U23_RES": str(base / "res"), "U23_PUSH": "0",
                "U23_TOOLCHAIN": "0", "JOBS": str(jobs), "PY": str(MATHS_PY), "U23_RHOMBUS": "0", "U23_TRIANGLES": "1",
                "U23_CLEANUP": "0", "U23_MIN_FREE_GB": "0"})
    for key in ("PRUNE_UDCHECK_RHOMBUS", "U23_RHOMBUS_CHECKER", "U23_PRUNE_FILTER_SET"):
        env.pop(key, None)
    # the prefix is the same however the fleet is sliced: find a non-empty and an empty slice of 128 from the
    # level-12 keep files of the round-2 fixture
    level12 = {int(p.name.split(".")[0].split("-")[1]): g6_lines(p) for p in (RUNS / "out" / "dag-16-41-L12-tri-s0of2").glob("12-*.keep.g6")}
    hit = {slice_of(c, count) for codes in level12.values() for c in codes}
    full, empty = min(hit), min(i for i in range(count) if i not in hit)
    log(f"C10 fixture: the level-12 keep files hold {sum(map(len, level12.values()))} records; of {count} slices, slice "
        f"{full} is not empty (run first: the full G4 replay) and slice {empty} is empty")
    with (base.parent / "c10-runbook.log").open("w") as stream:
        base.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(["nice", "-n", "10", "bash", str(RUNBOOK), str(count), str(full), str(empty)], env=env,
                           stdout=stream, stderr=subprocess.STDOUT, cwd=REPO)
    text = (base.parent / "c10-runbook.log").read_text()
    log(f"C10 runbook exit {p.returncode}: {[x for x in text.splitlines() if 'G4 replay of slice' in x and ':' in x[25:]]}")
    res = base / "res" / "16-41-L12-tri" / f"s{empty}of{count}"
    # audited together with the full slice, whose summary records the shared prefix fresh (a slice alone leaves
    # its hard-linked prefix unresolved)
    first = str(base / "res" / "16-41-L12-tri" / f"s{full}of{count}")
    fp = load(res / "replay" / "fingerprint.json") if (res / "replay" / "fingerprint.json").is_file() else {}
    log(f"C10 the empty slice's G4 fingerprint: result {fp.get('result')}, mode {fp.get('mode')}, exit "
        f"{fp.get('replay_exit')}, sampled {fp.get('sampled_parents')}, stages {fp.get('stages_checked')}")
    if p.returncode != 0 or fp.get("result") != "EMPTY":
        problems.append(f"C10: the runbook did not produce an EMPTY slice (exit {p.returncode}, {fp.get('result')})")
        return None
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "16", "41", "--expect-seed", "10",
            "--expect-slices", "12", str(count)]
    old, new = chain(first, str(res), *pins, landed="r4"), chain(first, str(res), *pins)
    show("C10 positive control, the runbook's own EMPTY slice, landed", old)
    show("C10 positive control, fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C10: the fixed tool refused the genuine EMPTY slice: {g4_only(new)[:2]} {new['unresolved'][:2]}")
    # the reader's way: the producer's summarize([], ...) with the genuine stage checks
    replay = module_from_file("replay_398", UD / "enum2" / "replay-398.py")
    genuine = load(res / "replay" / "summary.json")
    rargs = argparse.Namespace(run_dir=[Path(x) for x in genuine["run_dirs"]], seed=genuine["seed"],
                               fraction=genuine["fraction"], min_per_shard=genuine["min_per_shard"],
                               whole_max=genuine["whole_max"], max_per_shard=genuine["max_per_shard"],
                               levels=genuine["levels"], workers=genuine["workers"])
    built = replay.summarize([], [], [], rargs, 0.0, "398")
    built["stages"] = genuine["stages"]
    built["stages_checked"] = len(built["stages"])
    built["stages_ok"] = all(s["ok"] for s in built["stages"])
    built["all_identical"] = built["all_identical"] and built["stages_ok"]
    synth = base / "synthesized" / f"s{empty}of{count}"
    shutil.copytree(res, synth)
    dump(synth / "replay" / "summary.json", built)
    f = load(synth / "replay" / "fingerprint.json")
    f.update(mode="slice", result="EMPTY", replay_exit=1, sampled_parents=0, production_children_compared=0,
             mismatching_parents=0, stages_checked=built["stages_checked"])
    dump(synth / "replay" / "fingerprint.json", f)
    old, new = chain(first, str(synth), *pins, landed="r4"), chain(first, str(synth), *pins)
    log(f"C10 summarize([], ...): all_identical {built['all_identical']}, stages {built['stages_checked']} ok "
        f"{built['stages_ok']}, sampled {built['sampled_parents']}")
    show("C10 positive control, summarize([], ...) as the reader built it, landed", old)
    show("C10 positive control, summarize([], ...), fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C10 summarize([]): the fixed tool refused it: {g4_only(new)[:2]}")
    # red: the same EMPTY evidence, but the slice's summary records a share of one graph
    red = base / "red" / f"s{empty}of{count}"
    shutil.copytree(synth, red)
    s = load(red / "run-summary.json")
    changed = set_share(s, 12, min(level12), 1)
    dump(red / "run-summary.json", s)
    old, new = chain(first, str(red), *pins, landed="r4"), chain(first, str(red), *pins)
    show(f"C10 red, the empty slice's summary recording a share of 1 graph of (12,{min(level12)}) ({changed} entries), "
         f"landed", old)
    show("C10 red, fixed", new)
    if not any("G4 replay says 'EMPTY'" in p for p in g4_only(new)):
        problems.append(f"C10 red: the fixed tool did not refuse EMPTY for a slice with a share: {g4_only(new)[:2]}")
    return first, res


# ---------------------------------------------------------------- round 5: C11
def phase_c11(c10: tuple[str, Path] | None) -> None:
    """Round 5: the genuine EMPTY slice of C10 with (13,28) resumed as the driver writes it and its fresh summary
    kept as pushed history: the EMPTY decision must read the recovered parent record. Reds: no history; a history
    record showing parents in (13,28)."""
    if c10 is None:
        problems.append("C11: no C10 fixture")
        return
    first, res = c10
    base = RUNS / "c11"
    count = int(res.name.split("of")[1])
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "16", "41", "--expect-seed", "10",
            "--expect-slices", "12", str(count)]
    fresh = load(res / "run-summary.json")

    def build(name: str, history: dict | None) -> Path:
        d = base / name / res.name
        shutil.copytree(res, d)
        s = load(d / "run-summary.json")
        resume_cells(s, {(13, 28)})
        dump(d / "run-summary.json", s)
        if history is not None:
            (d / "history").mkdir()
            dump(d / "history" / "original.json", history)
            dump(d / "history" / "INDEX.json", {"commits": ["original"]})
        return d

    def recovered_of(r: dict) -> object:
        out = subprocess.run(["nice", "-n", "10", sys.executable, str(UD / "enum" / "verify-chain.py"), first,
                              str(r), *pins], capture_output=True, text=True).stdout
        line = next((x for x in out.splitlines() if x.startswith("{")), "{}")
        return (json.loads(line).get("fleets") or [{}])[0].get("cells_recovered_from_history")
    # GPT's reproduction: the fresh summary kept as history
    d = build("recovered", fresh)
    old, new = chain(first, str(d), *pins, landed="r5"), chain(first, str(d), *pins)
    log(f"C11 (13,28) of the empty slice resumed, its fresh summary kept as history/original.json: cells recovered "
        f"{recovered_of(d)}")
    show("C11 red at the landed code, accepted when fixed: landed", old)
    show("C11 fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C11: the fixed tool refused the recovered EMPTY slice: {g4_only(new)[:2]} {new['unresolved'][:2]}")
    if not any("unconfirmed [[13, 28]]" in p for p in g4_only(old)):
        log("C11: note: the landed tool did not refuse it as the reader found")
    # red: no history at all
    d = build("no-history", None)
    old, new = chain(first, str(d), *pins, landed="r5"), chain(first, str(d), *pins)
    show("C11 red, (13,28) resumed with no history, landed", old)
    show("C11 red, no history, fixed", new)
    if not any("G4 replay says 'EMPTY'" in p for p in g4_only(new)) or not any("G4 replay says 'EMPTY'" in p for p in g4_only(old)):
        problems.append(f"C11 no history: not refused by both: landed {g4_only(old)[:1]} fixed {g4_only(new)[:1]}")
    # red: a history record with parents in (13,28) (one record of (12,24), which only (13,28) reads here)
    history = json.loads(json.dumps(fresh))
    entry = next(e for e in history["levels"] if (e["n"], e["m"]) == (13, 28))
    source = next(x for x in entry["parent_sources"] if x["level"] == [12, 24])
    source["records"] = 1
    entry["parents"] = 1
    entry["shards"] = [{"range": [0, 1], "resumed": False, "children": entry.get("children", 0)}]
    d = build("history-with-parents", history)
    old, new = chain(first, str(d), *pins, landed="r5"), chain(first, str(d), *pins)
    show("C11 red, a history record with parents in (13,28), landed", old)
    show("C11 red, history with parents, fixed", new)
    if not any("cells with parents [[13, 28]]" in p for p in g4_only(new)) or not g4_only(old):
        problems.append(f"C11 history with parents: not refused by both: landed {g4_only(old)[:1]} fixed {g4_only(new)[:1]}")


# ---------------------------------------------------------------- round 6: C12
def phase_c12(c10: tuple[str, Path] | None) -> None:
    """Round 6: copies of C10's genuine EMPTY slice, each resuming cells the other records (the EMPTY decision must
    be taken with the records of every copy); reds refused before and after; and the G4 per-cell binding."""
    if c10 is None:
        problems.append("C12: no C10 fixture")
        return
    first, res = c10
    base = RUNS / "c12"
    count = int(res.name.split("of")[1])
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "16", "41", "--expect-seed", "10",
            "--expect-slices", "12", str(count)]

    def copies(case: str, a_resumed: set, b_resumed: set, edit_b=None) -> tuple[Path, Path]:
        made = []
        for name, resumed in (("copy-a", a_resumed), ("copy-b", b_resumed)):
            d = base / case / name / res.name
            shutil.copytree(res, d)
            s = load(d / "run-summary.json")
            resume_cells(s, resumed)
            if name == "copy-b" and edit_b is not None:
                edit_b(s)
            dump(d / "run-summary.json", s)
            made.append(d)
        return made[0], made[1]

    def run_both(label: str, a: Path, b: Path) -> list[tuple[dict, dict]]:
        out = []
        for order, pair in (("A, B", (a, b)), ("B, A", (b, a))):
            old = chain(first, *map(str, pair), *pins, landed="r6")
            new = chain(first, *map(str, pair), *pins)
            show(f"C12 {label}, order {order}, landed", old)
            show(f"C12 {label}, order {order}, fixed", new)
            out.append((old, new))
        return out
    # the reader's reproduction: A resumes (13,29) and (13,30), B resumes (13,28), no history
    a, b = copies("repro", {(13, 29), (13, 30)}, {(13, 28)})
    for old, new in run_both("the reader's complementary copies of the EMPTY slice", a, b):
        if g4_only(new) or new["unresolved"]:
            problems.append(f"C12 reproduction: the fixed tool refused it: {g4_only(new)[:2]} {new['unresolved'][:2]}")
        if not g4_only(old):
            log("C12 reproduction: note: the landed tool accepted it")

    def both_refuse(label: str, a: Path, b: Path) -> None:
        for old, new in run_both(label, a, b):
            if not g4_only(old) or not g4_only(new):
                problems.append(f"C12 {label}: not refused by both: landed {g4_only(old)[:1]} fixed {g4_only(new)[:1]}")
    a, b = copies("neither-28", {(13, 28), (13, 29)}, {(13, 28), (13, 30)})
    both_refuse("red, neither copy records (13,28)", a, b)

    def parents_in_29(s: dict) -> None:
        e = next(x for x in s["levels"] if (x["n"], x["m"]) == (13, 29))
        e["parent_sources"][-1]["records"] = 1
        e["parents"] = 1
        e["shards"] = [{"range": [0, 1], "resumed": False, "children": e.get("children", 0)}]
    a, b = copies("parents", {(13, 29), (13, 30)}, {(13, 28)}, parents_in_29)
    both_refuse("red, complementary copies, B recording parents in (13,29)", a, b)

    def share_24(s: dict) -> None:
        set_share(s, 12, 24, 1)
    a, b = copies("shares", {(13, 29), (13, 30)}, set(), share_24)
    both_refuse("red, copies whose shares of (12,24) disagree (0 and 1)", a, b)
    # the G4 per-cell binding (found hunting the family): a replayed cell's parents must be the summary's
    if FLEET_SLICE.is_dir():
        d = base / "per-cell" / "s0of1920"
        shutil.copytree(FLEET_SLICE, d)
        s = load(d / "replay" / "summary.json")
        row = s["per_cell"][0]
        row["parents_in_cell"] += 1
        for lv in s["per_level"]:
            if lv["n"] == row["n"]:
                lv["parents"] += 1
        dump(d / "replay" / "summary.json", s)
        fleet_pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "23", "65",
                      "--expect-seed", "10", "--expect-slices", "12", "1920"]
        old, new = chain(str(d), *fleet_pins, landed="r6"), chain(str(d), *fleet_pins)
        show(f"C12 red, the fleet record's G4 per_cell {row['cell']} parents_in_cell raised by one (per_level too), landed",
             old)
        show("C12 red, per_cell parents, fixed", new)
        if not any("G4 replayed" in p for p in g4_only(new)):
            problems.append(f"C12 per_cell binding: the fixed tool did not refuse it: {g4_only(new)[:2]}")


# ---------------------------------------------------------------- round 7: C13
def phase_c13() -> None:
    """Round 7: bindings of a replay to parent records made against the MERGED records of every copy (and, for the
    prefix, of every slice). On copies of the real fleet record f01-jjpzl7/s0of1920."""
    base = RUNS / "c13"
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "23", "65", "--expect-seed", "10",
            "--expect-slices", "12", "1920"]

    def mutate_row(d: Path, cell: str = "11-17") -> int:
        s = load(d / "replay" / "summary.json")
        row = next(r for r in s["per_cell"] if r["cell"] == cell)
        row["parents_in_cell"] += 1
        for lv in s["per_level"]:
            if lv["n"] == row["n"]:
                lv["parents"] += 1
        dump(d / "replay" / "summary.json", s)
        return row["parents_in_cell"]

    def resume_summary(d: Path, cells: set) -> None:
        s = load(d / "run-summary.json")
        resume_cells(s, cells)
        dump(d / "run-summary.json", s)

    def g4_problem(r: dict, text: str) -> bool:
        return any(text in p for p in g4_only(r))
    # (a) the reader's reproduction: copy A with (11,17)'s parents_in_cell raised and (11,17) resumed, copy B untouched
    a = base / "repro" / "copy-a" / "s0of1920"
    b = base / "repro" / "copy-b" / "s0of1920"
    shutil.copytree(FLEET_SLICE, a)
    shutil.copytree(FLEET_SLICE, b)
    raised = mutate_row(a)
    resume_summary(a, {(11, 17)})
    for order, pair in (("A, B", (a, b)), ("B, A", (b, a))):
        old, new = chain(*map(str, pair), *pins, landed="r7"), chain(*map(str, pair), *pins)
        show(f"C13 (a) copy A: (11,17) replayed with {raised} parents and resumed; copy B untouched; order {order}; landed",
             old)
        show(f"C13 (a) order {order}, fixed", new)
        if g4_only(old):
            log(f"C13 (a) order {order}: note: the landed tool refused it")
        if not g4_problem(new, "G4 replayed (11, 17)"):
            problems.append(f"C13 (a) order {order}: the fixed tool did not refuse it: {g4_only(new)[:2]}")
    # (b) the same mutation with no copy B: no evidence anywhere, so UNRESOLVED, never a silent pass
    alone = base / "alone" / "s0of1920"
    shutil.copytree(a, alone)
    old, new = chain(str(alone), *pins, landed="r7"), chain(str(alone), *pins)
    show("C13 (b) copy A alone, landed", old)
    show("C13 (b) copy A alone, fixed", new)
    if not any("G4 replayed (11, 17)" in u for u in new["unresolved"]):
        problems.append(f"C13 (b): the fixed tool did not leave the unbindable row UNRESOLVED: {new['unresolved'][:2]}")
    # (c) the prefix path: another worker's full-mode slice Y, (11,17) resumed and its row raised, audited with the
    # untouched f01 slice X (another slice): X's record of the shared prefix refutes Y's row
    root = FLEET_SLICE.parents[6]
    other = None
    for d in sorted(root.glob("*/research/unit-distance-23/results/u23/23-65-L12-tri-pf74/s*of1920")):
        if d.parents[5].name == FLEET_SLICE.parents[5].name:
            continue
        fp = load(d / "replay" / "fingerprint.json") if (d / "replay" / "fingerprint.json").is_file() else {}
        if fp.get("mode") == "full" and fp.get("result") == "PASS":
            rows = load(d / "replay" / "summary.json").get("per_cell", [])
            entries = {(e["n"], e["m"]): e for e in load(d / "run-summary.json")["levels"]}
            if any(r["cell"] == "11-17" for r in rows) and not entries.get((11, 17), {}).get("resumed"):
                other = d
                break
    if other is None:
        log("C13 (c): no other worker's full-mode slice with a fresh (11,17) in the extraction; the prefix path untested")
    else:
        y = base / "prefix" / other.parents[5].name / other.name
        shutil.copytree(other, y)
        raised_y = mutate_row(y)
        resume_summary(y, {(11, 17)})
        x = base / "prefix" / "f01-jjpzl7" / FLEET_SLICE.name
        shutil.copytree(FLEET_SLICE, x)
        old, new = chain(str(x), str(y), *pins, landed="r7"), chain(str(x), str(y), *pins)
        show(f"C13 (c) slice {other.name} of {other.parents[5].name}: (11,17) resumed and replayed with {raised_y} "
             f"parents, audited with f01's untouched {FLEET_SLICE.name}; landed", old)
        show("C13 (c) fixed", new)
        if not g4_problem(new, "G4 replayed (11, 17)"):
            problems.append(f"C13 (c): the fixed tool did not refuse it through the prefix: {g4_only(new)[:2]}")
    # (d) found hunting the family: copy A's level-13 cells resumed (it records no share) and its G4 record of the
    # (12,20) slice file changed; copy B untouched records the share
    a2 = base / "stage" / "copy-a" / "s0of1920"
    b2 = base / "stage" / "copy-b" / "s0of1920"
    shutil.copytree(FLEET_SLICE, a2)
    shutil.copytree(FLEET_SLICE, b2)
    s = load(a2 / "run-summary.json")
    resume_cells(s, {(e["n"], e["m"]) for e in s["levels"] if e["n"] == 13})
    dump(a2 / "run-summary.json", s)
    r = load(a2 / "replay" / "summary.json")
    for st in r["stages"]:
        if st.get("source") == "12-20.slice-0-of-1920.g6":
            st["records"] = st["derived_records"] = st["records"] + 1
    dump(a2 / "replay" / "summary.json", r)
    old, new = chain(str(a2), str(b2), *pins, landed="r7"), chain(str(a2), str(b2), *pins)
    show("C13 (d) copy A records no share and its G4 record of the (12,20) slice file is one larger; landed", old)
    show("C13 (d) fixed", new)
    if not g4_problem(new, "12-20.slice-0-of-1920.g6"):
        problems.append(f"C13 (d): the fixed tool did not bind copy A's slice record to copy B's share: {g4_only(new)[:2]}")
    # valid control: two untouched copies
    v1, v2 = base / "valid" / "copy-a" / "s0of1920", base / "valid" / "copy-b" / "s0of1920"
    shutil.copytree(FLEET_SLICE, v1)
    shutil.copytree(FLEET_SLICE, v2)
    new = chain(str(v1), str(v2), *pins)
    show("C13 valid control, two untouched copies, fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C13 valid control: {g4_only(new)[:2]} {new['unresolved'][:2]}")


# ---------------------------------------------------------------- round 8: C14
def phase_c14() -> None:
    """Round 8: a G4 per_cell row's parent and sample counts must be nonnegative integers before the sampling bound and
    the binding compare them (a float or boolean parent count skipped the bound, then equalled the accepted record);
    and the family found with it: a summary entry's cell and a parent source's level must be integers too. On copies
    of the real fleet record f01-jjpzl7/s0of1920."""
    base = RUNS / "c14"
    pins = ["--summary-only", "--require-hashes", "--require-g4", "--expect-target", "23", "65", "--expect-seed", "10",
            "--expect-slices", "12", "1920"]

    def set_row(d: Path, cell: str, parents_in_cell, sampled: int) -> dict:
        """The row's parents_in_cell and sampled set, the sampled totals moved with it (its level in per_level, the
        replay summary's and the fingerprint's sampled_parents), the production evidence kept. Returns the row as it
        was."""
        s = load(d / "replay" / "summary.json")
        f = load(d / "replay" / "fingerprint.json")
        row = next(r for r in s["per_cell"] if r["cell"] == cell)
        before = dict(row)
        delta = sampled - row["sampled"]
        row["parents_in_cell"], row["sampled"] = parents_in_cell, sampled
        for lv in s["per_level"]:
            if lv["n"] == row["n"]:
                lv["sampled"] += delta
        s["sampled_parents"] += delta
        f["sampled_parents"] += delta
        dump(d / "replay" / "summary.json", s)
        dump(d / "replay" / "fingerprint.json", f)
        return before

    def g4_problem(r: dict, text: str) -> bool:
        return any(text in p for p in g4_only(r))
    # (a) the reader's reproduction, (b) and (c) a boolean and a float parent count of one on the real (16,36)
    for key, cell, value, sampled in (("a", "11-17", 31127.0, 31128), ("b", "16-36", True, 2), ("c", "16-36", 1.0, 2)):
        d = base / key / "s0of1920"
        shutil.copytree(FLEET_SLICE, d)
        before = set_row(d, cell, value, sampled)
        old, new = chain(str(d), *pins, landed="r8"), chain(str(d), *pins)
        show(f"C14 ({key}) per_cell {cell} ({before['parents_in_cell']} parents, {before['sampled']} sampled) set to "
             f"parents_in_cell {value!r} and {sampled} sampled, the sampled totals moved with it; landed", old)
        show(f"C14 ({key}) fixed", new)
        if g4_only(old) or old["unresolved"]:
            log(f"C14 ({key}): note: the landed tool did not accept it")
        text = (f"G4 per_cell row of {tuple(map(int, cell.split('-')))}: parents_in_cell {value!r} and sampled "
                f"{sampled!r} are not both nonnegative integers")
        if not g4_problem(new, text):
            problems.append(f"C14 ({key}): the fixed tool did not refuse it: {g4_only(new)[:2]}")
    # (d) valid control: an untouched copy
    v = base / "valid" / "s0of1920"
    shutil.copytree(FLEET_SLICE, v)
    new = chain(str(v), *pins)
    show("C14 (d) valid control, an untouched copy, fixed", new)
    if g4_only(new) or new["unresolved"]:
        problems.append(f"C14 (d) valid control: {g4_only(new)[:2]} {new['unresolved'][:2]}")
    # (e) found hunting the family: the target entry written (23, 65.0), with one child. The landed tool counted it
    # as listed (65.0 == 65) but audited only entries with integer cells, so nothing read it
    d = base / "e" / "s0of1920"
    shutil.copytree(FLEET_SLICE, d)
    s = load(d / "run-summary.json")
    entry = next(e for e in s["levels"] if (e["n"], e["m"]) == (23, 65))
    entry["m"], entry["children"] = 65.0, entry["children"] + 1
    dump(d / "run-summary.json", s)
    old, new = chain(str(d), *pins, landed="r8"), chain(str(d), *pins)
    target = ((old["report"].get("fleets") or [{}])[0].get("target_cell") or {}).get("children")
    show(f"C14 (e) the target entry written (23, 65.0) with {entry['children']} child; landed (its report: {target} "
         f"children at the target)", old)
    show("C14 (e) fixed", new)
    if g4_only(old) or old["unresolved"]:
        log("C14 (e): note: the landed tool did not accept it")
    if not g4_problem(new, "level entries whose n and m are not nonnegative integers: [(23, 65.0)]"):
        problems.append(f"C14 (e): the fixed tool did not refuse the entry: {g4_only(new)[:2]}")
    # (f) found hunting the family: a source level [12, 20] written [12, 20.0], and the G4 record of the (12,20) slice
    # file one larger. The float became the share's key and so the file's name: the landed tool looked for
    # 12-20.0.slice-0-of-1920.g6 and never compared the real record
    d = base / "f" / "s0of1920"
    shutil.copytree(FLEET_SLICE, d)
    s = load(d / "run-summary.json")
    readers = []
    for e in s["levels"]:
        for x in (e.get("parent_sources") or []) if e["n"] == 13 else []:
            if x["level"] == [12, 20]:
                x["level"] = [12, 20.0]
                readers.append((e["n"], e["m"]))
    dump(d / "run-summary.json", s)
    r = load(d / "replay" / "summary.json")
    for st in r["stages"]:
        if st.get("source") == "12-20.slice-0-of-1920.g6":
            st["records"] = st["derived_records"] = st["records"] + 1
    dump(d / "replay" / "summary.json", r)
    if not readers:
        problems.append("C14 (f): no level-13 entry of the fleet record reads (12,20) (the fixture differs)")
        return
    old, new = chain(str(d), *pins, landed="r8"), chain(str(d), *pins)
    show(f"C14 (f) the source level [12, 20] of {readers} written [12, 20.0], the G4 record of the (12,20) slice file "
         f"one larger; landed", old)
    show("C14 (f) fixed", new)
    if g4_problem(old, "12-20.slice-0-of-1920.g6"):
        log("C14 (f): note: the landed tool compared the record")
    if not any("recorded parents" in p and "[12, 20.0]" in p for p in g4_only(new)):
        problems.append(f"C14 (f): the fixed tool did not refuse the recorded parents: {g4_only(new)[:2]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    shutil.rmtree(RUNS, ignore_errors=True)
    RUNS.mkdir(parents=True)
    (RUNS / "verify-chain-landed.py").write_text(landed_source("enum/verify-chain.py"))
    log(f"landed tools from {LANDED_COMMIT}: run-dag2.py {hashlib.sha256(landed_source('enum/run-dag2.py').encode()).hexdigest()[:12]}, "
        f"verify-chain.py {sha(RUNS / 'verify-chain-landed.py')[:12]}; fixed: run-dag2.py "
        f"{sha(UD / 'enum' / 'run-dag2.py')[:12]}, verify-chain.py {sha(UD / 'enum' / 'verify-chain.py')[:12]}")
    (RUNS / "verify-chain-landed-r3.py").write_text(landed_source("enum/verify-chain.py", LANDED_R3))
    (RUNS / "verify-chain-landed-r4.py").write_text(landed_source("enum/verify-chain.py", LANDED_R4))
    (RUNS / "verify-chain-landed-r5.py").write_text(landed_source("enum/verify-chain.py", LANDED_R5))
    (RUNS / "verify-chain-landed-r6.py").write_text(landed_source("enum/verify-chain.py", LANDED_R6))
    (RUNS / "verify-chain-landed-r7.py").write_text(landed_source("enum/verify-chain.py", LANDED_R7))
    (RUNS / "verify-chain-landed-r8.py").write_text(landed_source("enum/verify-chain.py", LANDED_R8))
    out, res = runbook_fixture(a.jobs)
    phase_c2(out)
    phase_c3(res)
    phase_c4(res, out)
    phase_c6(res)
    if FLEET_SLICE.is_dir():
        phase_c7()
        phase_c9()
    else:
        problems.append(f"C7, C9: the fleet record {FLEET_SLICE} is not there")
    phase_c8(out)
    c10 = phase_c10(a.jobs)
    phase_c11(c10)
    phase_c12(c10)
    if FLEET_SLICE.is_dir():
        phase_c13()
        phase_c14()
    phase_c1_c5(out, a.jobs)
    for p in problems:
        log("PROBLEM:", p)
    log("G5CLOSE", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
