#!/usr/bin/env python3
"""Local test of gate G4 in coordination/cloud-workers/u23-slice.sh (U23_REPLAY: enum2/replay-398.py after every
slice, CONTRACT.md 4.4), and of the runbook's disk handling (U23_CLEANUP, U23_MIN_FREE_GB), on the fleet's pipeline,
without a cloud worker.

The runbook runs as on a worker except for the overrides of enum/test-rhombus/runbook-rh.py: target (16,41), root k 4,
prune from 12, sliced at level 12, JOBS=2, no toolchain step, scratch directories. The rules are the fleet's
(U23_TRIANGLES=1, U23_PRUNE_FILTER_SET=74) and the G4 settings the runbook's defaults (fraction 0.001, whole-max 100,
seed 20260926; the replay's python is PY, the maths venv, which has pynauty). U23_MIN_FREE_GB=0 (a local disk) except
in G9. U23_PUSH=1, with a stand-in for git first on PATH: it passes rev-parse to the real git, records add, commit and
push, answers "changes are staged" to diff, refuses to add a path that does not exist, and with GIT_STUB_PUSH_FAIL=1
fails every push; so the commit steps run as on a worker and nothing is committed or pushed. G1-G7 run in one area
(slice count 2) with U23_CLEANUP=0, since they read the run directories; G8 and G9 in a second area (slice count 5)
with the default U23_CLEANUP=1.

PASS iff
  G1 the runbook exits 0 on slices 0 and 1. Slice 0's replay is mode "full": every level, every seed level identical
     and the level-10 seed files equal, as sets, to enum2's own augmentation of nauty-geng's 9-vertex graphs; stage
     files of the kinds reach, keep+slice and keep all re-derived; all six red controls red. Slice 1's is mode
     "slice": levels 13-16 only, no seeds, no red controls. Both find 0 mismatching parents and write replay/summary.json
     and replay/fingerprint.json (slice 0 also red.json) into their result directories, every file under 4 MB; the
     prefix marker names slice 0; the prefix directory is made from slice 0 and slice 1 hard-links from it; the pins
     file pins enum2/enum2.py and enum2/replay-398.py and names pynauty; the replay's self-check (canonical form =
     nauty-labelg's, K4, augmentation = brute force) says ok.
  G1b R3's parent outside the sample is used only when identical to production: when G1's R3 came from outside the
     sample (the fleet's small per-cell sample has no parent R3 can use here), a copy of slice 0's run directory in
     which that parent's production block lost one child (manifests rewritten to match) must make replay-398.py report
     R3 as a discrepancy, not red, and exit 1, while its sampled parents all stay identical.
  G2 a restart: the runbook again on the same directories exits 0 and replays neither slice ("already passed").
  G3 the planted fault stops the worker, and U23_CLEANUP=1 deletes nothing: in slice 0's run directory one child of a
     sampled parent above the slice level (the deepest such cell) is corrupted IN ITS SHARD FILE so that it is lost,
     the shard manifest is rewritten as udenum would write it for what it wrote, and the cell file, its aggregate
     manifest and every file of the levels above are deleted, so that run-dag2.py --resume rebuilds them from the
     shards (and redoes the reach, prune and stage-verification steps), as after a faulty udenum shard: a consistent
     run that lost one graph. The runbook on slices 0 and 1, with U23_CLEANUP=1, exits 5 with a "G4 REPLAY FAILED for
     slice s0of2" line naming a mismatch; replay/FAILED says MISMATCH and replay/mismatches.jsonl holds the victim
     parent with exactly the lost child missing; slice 1 is never started; slice 0's run directory and its replay
     directory (replay.jsonl) are still there. (A lost child is the fault only the replay can see: a repeated record
     is refused by prune.py, and a record that is not canonical or holds one of the 398 by the stage verification,
     once kept. Corrupting a shard file alone, the cell file left as it was, changes nothing the next level is built
     from: the replay reads the cell file, checked against the aggregate manifest.)
  G4 the same corrupted directories with U23_REPLAY=0: exit 0. Every other step of the runbook accepts the planted
     fault; the replay is what stops it.
  G5 refusals before anything is written (exit 2): U23_REPLAY=2, U23_REPLAY_FRACTION=0 and =x, U23_REPLAY_WHOLE_MAX=-1,
     U23_REPLAY_SEED='a b', U23_CLEANUP=2, U23_MIN_FREE_GB=x. Fail closed before any run directory (exit 3): a replay
     python without pynauty, and one whose pynauty labels in another canonical order (a sitecustomize reversing
     canon_label: an isomorphism invariant still, but not nauty-labelg's, so every record enum2 writes would differ
     from udenum's).
  G6 an empty slice (no level-12 graph hashes to it, slice count 1920) passes as EMPTY: exit 0, nothing sampled, its
     empty slice files re-derived from the level-12 keep files; its prefix hard-linked from the prefix directory.
  G7 the commit steps: after G1 two commits, "u23 slice s0of2 done: through n 16; G4 replay PASS (full, ...)" and
     "... s1of2 ...; G4 replay PASS (slice, ...)", each adding the slice's result directory and the per-worker files
     with the replay's self-check, and each pushed; after G2 the same with "G4 replay passed before"; after G3 exactly
     one commit, "u23 slice s0of2 G4 REPLAY FAILED (slice): MISMATCH ...", adding slice 0's result directory (its
     replay/FAILED and mismatches.jsonl), pushed; after G4 two commits "...; no G4 replay (U23_REPLAY=0)" without the
     self-check file; after G6 "...; G4 replay EMPTY (slice, 0 parents)". Every path added exists.
  G8 U23_CLEANUP=1 (second area, slice count 5):
     A1 slice 0: exit 0; the prefix directory is made from slice 0; in the log its replay's PASS comes before
        "run directory deleted", and its commit was pushed; its run directory and replay directory are gone; its
        results (the replay's summary, red controls and fingerprint, hashes, counts, run summary, the top cells)
        and its two logs stay; the done marker names the commit (the worktree's HEAD, through the stand-in).
     A2 a restart on slices 0 and 1, the G4 marker deleted first (so slice 1 gets a FULL replay over a prefix it
        hard-linked from the prefix directory, slice 0's directory being gone): slice 0 is skipped as done before
        (not recomputed, nothing committed for it); slice 1 hard-links from the prefix directory, its run and its
        full replay pass (seeds identical, red controls red), its levels <= 12 in hashes.json equal slice 0's, and
        its run directory is deleted after its push.
     A3 the same restart again: both slices skipped, nothing started or committed, exit 0.
     A4 slice 2 with every push failing: exit 0 after three tries, "its results are not pushed, so its run directory
        is kept", the directory there, no done marker. A5 slice 2 again, pushes working: its replay is not repeated
        ("already passed"), its commit is pushed, and only then is its run directory deleted.
  G9 the disk guard: every slice that starts logs "disk" (df -h of the output filesystem). a: slice 3 with
     U23_MIN_FREE_GB=1000000 exits 6 with "STOPPING this worker before slice s3of5", nothing started or committed.
     b: slices 3 and 4 with a stand-in df reporting 10 GB free and then 1 GB (U23_MIN_FREE_GB=5): slice 3 runs,
     is pushed and deleted; the worker then exits 6 before slice 4 starts (no s4of5 directory).

usage: runbook-g4.py      (about 8 minutes on 2 cores; work directory <U23_SCRATCH>/runbook-g4)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from u23lib import MATHS_PY, REPO, SCRATCH, UD, log, sha256

RUNBOOK = REPO / "coordination" / "cloud-workers" / "u23-slice.sh"
REPLAY = UD / "enum2" / "replay-398.py"
WORK = SCRATCH / "runbook-g4"
KEY = "16-41-L12-tri-pf74"
FRACTION = "0.001"             # the runbook's default U23_REPLAY_FRACTION
HOST = os.uname().nodename
STUB, STUB_LOG, DF_STUB = WORK / "gitstub", WORK / "gitstub.log", WORK / "dfstub"
STUB_SCRIPT = """#!/usr/bin/env bash
# runbook-g4.py's stand-in for git: rev-parse to the real git; add (refusing a missing path), commit, push recorded;
# diff answers "changes are staged"; GIT_STUB_PUSH_FAIL=1 fails every push
case "$1" in
  rev-parse) exec /usr/bin/git "$@" ;;
  add)
    shift
    for a in "$@"; do
      case "$a" in -*) ;; *) [ -e "$a" ] || { echo "add REFUSED $a" >> "$GIT_STUB_LOG"; exit 128; } ;; esac
    done
    echo "add $*" >> "$GIT_STUB_LOG" ;;
  diff) echo "$*" >> "$GIT_STUB_LOG"; exit 1 ;;
  push)
    if [ "${GIT_STUB_PUSH_FAIL:-0}" = 1 ]; then echo "push-failed" >> "$GIT_STUB_LOG"; exit 1; fi
    echo "$*" >> "$GIT_STUB_LOG" ;;
  *) echo "$*" >> "$GIT_STUB_LOG" ;;
esac
exit 0
"""
DF_SCRIPT = """#!/usr/bin/env bash
# runbook-g4.py's stand-in for df: the free space (KB) is the next value of $DF_STUB_SEQ at each -Pk call (the last
# one repeated); -hP shows the value the next -Pk call will return
seq=($DF_STUB_SEQ)
i=$(cat "$DF_STUB_STATE" 2>/dev/null || echo 0)
j=$i; [ "$j" -lt "${#seq[@]}" ] || j=$(( ${#seq[@]} - 1 ))
kb=${seq[$j]}
case "$1" in
  -Pk) echo $(( i + 1 )) > "$DF_STUB_STATE"
       echo "Filesystem 1024-blocks Used Available Capacity Mounted on"; echo "stub 104857600 0 $kb 1% /stub" ;;
  *)   echo "Filesystem Size Used Avail Use% Mounted on"; echo "stub 100G 0 $(( kb / 1048576 ))G 1% /stub" ;;
esac
"""
problems: list[str] = []


def env(**over: str) -> dict:
    e = dict(os.environ)
    e.update({"U23_TARGET_N": "16", "U23_TARGET_M": "41", "U23_ROOT_K": "4", "U23_PRUNE_FROM": "12",
              "U23_SLICE_LEVEL": "12", "U23_OUT": str(WORK / "out"), "U23_RES": str(WORK / "res"), "U23_PUSH": "1",
              "U23_TOOLCHAIN": "0", "JOBS": "2", "PY": str(MATHS_PY), "U23_RHOMBUS": "0", "U23_TRIANGLES": "1",
              "U23_PRUNE_FILTER_SET": "74", "PATH": f"{STUB}:{os.environ['PATH']}", "GIT_STUB_LOG": str(STUB_LOG),
              "U23_CLEANUP": "0", "U23_MIN_FREE_GB": "0"})
    for k in ("PRUNE_UDCHECK_RHOMBUS", "U23_RHOMBUS_CHECKER", "U23_REPLAY", "U23_REPLAY_FRACTION", "U23_REPLAY_SEED",
              "U23_REPLAY_WHOLE_MAX", "U23_REPLAY_PY", "U23_REPLAY_VENV", "ENUM2_ENGINE", "GIT_STUB_PUSH_FAIL",
              "DF_STUB_SEQ", "DF_STUB_STATE"):
        e.pop(k, None)
    e.update(over)
    return e


def runbook(args: list[str], e: dict, name: str) -> tuple[int, str]:
    logf = WORK / f"{name}.log"
    with logf.open("w") as stream:
        p = subprocess.run(["nice", "-n", "10", "bash", str(RUNBOOK), *args], env=e, stdout=stream,
                           stderr=subprocess.STDOUT, cwd=REPO)
    return p.returncode, logf.read_text()


def run_dir(s: int) -> Path:
    return WORK / "out" / f"dag-{KEY}-s{s}of2"


def res_dir(s: int) -> Path:
    return WORK / "res" / KEY / f"s{s}of2"


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def lines_of(path: Path) -> list[str]:
    return [x for x in Path(path).read_text().split("\n") if x]


def write_lines(path: Path, lines: list[str]) -> None:
    Path(path).write_text("".join(x + "\n" for x in lines))


def need(ok: bool, label: str) -> None:
    if not ok:
        problems.append(label)


def show(text: str, keep: str = "") -> str:
    return "\n".join("    " + x[:260] for x in text.splitlines() if not keep or keep in x)


def git_record() -> tuple[list[str], list[str], int, list[str], int]:
    """What the runbook asked git to do since the last call: adds, commit messages, pushes, refused adds, failed pushes."""
    entries = lines_of(STUB_LOG) if STUB_LOG.exists() else []
    STUB_LOG.unlink(missing_ok=True)
    return ([x for x in entries if x.startswith("add -f ")], [x[len("commit -q -m "):] for x in entries if x.startswith("commit ")],
            sum(1 for x in entries if x == "push -q origin HEAD"), [x for x in entries if "REFUSED" in x],
            sum(1 for x in entries if x == "push-failed"))


def g7(after: str, want: list[str], selfcheck: bool, key_dir: Path | None = None) -> None:
    adds, msgs, pushes, refused, failed = git_record()
    log(f"G7 after {after}: commits {msgs}; {len(adds)} adds, {pushes} pushes, {failed} failed pushes, refused {refused}")
    ok = not refused and not failed and len(msgs) == len(want) == len(adds) == pushes and \
        all(m.startswith(w) for m, w in zip(msgs, want))
    for a, m in zip(adds, msgs):
        tag = m.split()[2]                           # "u23 slice <tag> done: ..." / "u23 slice <tag> G4 REPLAY FAILED ..."
        ok = ok and str((key_dir or WORK / "res" / KEY) / tag) in a.split()
        ok = ok and ((f"replay-selfcheck-{HOST}.json" in a) == selfcheck) and (("pins-" in a) == ("REPLAY FAILED" not in m))
    need(ok, f"G7 after {after}: the commit steps are not as expected")


def refusals() -> None:
    for label, over in (("U23_REPLAY=2", {"U23_REPLAY": "2"}), ("U23_REPLAY_FRACTION=0", {"U23_REPLAY_FRACTION": "0"}),
                        ("U23_REPLAY_FRACTION=x", {"U23_REPLAY_FRACTION": "x"}),
                        ("U23_REPLAY_WHOLE_MAX=-1", {"U23_REPLAY_WHOLE_MAX": "-1"}),
                        ("U23_REPLAY_SEED='a b'", {"U23_REPLAY_SEED": "a b"}),
                        ("U23_CLEANUP=2", {"U23_CLEANUP": "2"}), ("U23_MIN_FREE_GB=x", {"U23_MIN_FREE_GB": "x"})):
        code, text = runbook(["2", "0"], env(**over), "refusal")
        made = (WORK / "out").exists() or (WORK / "res").exists()
        log(f"G5 {label}: exit {code}: {text.strip()[-110:]}; anything written: {made}")
        need(code == 2 and not made, f"G5 {label} was not refused before writing (exit {code}, wrote {made})")
    # fail closed before any run directory: no pynauty; a pynauty with another canonical order
    mutant = WORK / "mutant-pynauty"
    mutant.mkdir(parents=True)
    (mutant / "sitecustomize.py").write_text(
        "import pynauty\n_canon = pynauty.canon_label\n"
        "def canon_label(g):   # an isomorphism invariant still, but not nauty-labelg's labelling\n"
        "    return list(reversed(_canon(g)))\n"
        "pynauty.canon_label = canon_label\n")
    fakepy = WORK / "mutant-python"
    fakepy.write_text(f"#!/usr/bin/env bash\nPYTHONPATH={mutant} exec {MATHS_PY} \"$@\"\n")
    fakepy.chmod(0o755)
    probe = subprocess.run([str(fakepy), "-c", "import pynauty; print(pynauty.canon_label.__name__, "
                            "pynauty.canon_label.__module__)"], capture_output=True, text=True)
    log(f"G5 the mutant python's canon_label: {probe.stdout.strip()} {probe.stderr.strip()[-200:]}")
    need(probe.stdout.split()[-1:] == ["sitecustomize"], "G5: the mutant pynauty was not installed")
    for label, py in (("a replay python without pynauty (/usr/bin/python3)", "/usr/bin/python3"),
                      ("a pynauty with another canonical order", str(fakepy))):
        code, text = runbook(["2", "0"], env(U23_REPLAY_PY=py), "refusal-selfcheck")
        dirs = list((WORK / "out").glob("dag-*")) if (WORK / "out").exists() else []
        log(f"G5 {label}: exit {code}: {text.strip().splitlines()[-1][-170:]}; run directories made: {len(dirs)}")
        need(code == 3 and not dirs, f"G5 {label} did not fail closed (exit {code}, {len(dirs)} run directories)")
    sc = WORK / "res" / f"replay-selfcheck-{HOST}.json"
    if sc.is_file():
        v = load(sc)
        log(f"G5 the mutant's self-check record: canonical {v.get('canonical')}, ok {v.get('ok')}")
        need(v.get("ok") is False and v["canonical"]["enum2_eq_labelg_eq_original"] < 56,
             "G5: the mutant's self-check did not fail on the canonical form")
    else:
        problems.append("G5: the mutant's self-check wrote no record")
    shutil.rmtree(WORK / "out", ignore_errors=True)
    shutil.rmtree(WORK / "res", ignore_errors=True)


def g1(code: int, text: str) -> dict:
    need(code == 0 and "pins and self-checks passed" in text, f"G1: runbook exit {code}")
    need("G4 replay of slice s0of2 (full): PASS" in text, "G1: slice 0 was not replayed in full mode with a PASS")
    need("G4 replay of slice s1of2 (slice): PASS" in text, "G1: slice 1 was not replayed in slice mode with a PASS")
    prefix = WORK / "out" / f"prefix-{KEY}"
    made = load(prefix / "prefix.json").get("made_from") if (prefix / "prefix.json").is_file() else None
    log(f"G1 prefix directory: made from {made}; slice 1 linked from it: "
        f"{('slice s1of2: levels <= 12 hard-linked from ' + str(prefix) + ' ') in text}")
    need(made == str(run_dir(0)) and ("slice s1of2: levels <= 12 hard-linked from " + str(prefix) + " ") in text,
         "G1: the prefix directory is not made from slice 0, or slice 1 did not hard-link from it")
    s0, s1 = (load(res_dir(s) / "replay" / "summary.json") for s in (0, 1))
    red = load(res_dir(0) / "replay" / "red.json")
    fp0, fp1 = (load(res_dir(s) / "replay" / "fingerprint.json") for s in (0, 1))
    for s, summ, fp in ((0, s0, fp0), (1, s1, fp1)):
        kinds = sorted({st["kind"] for st in summ["stages"]})
        log(f"G1 slice {s}: mode {fp['mode']}, levels '{summ['levels']}', sampled {summ['sampled_parents']} "
            f"({summ['processed_parents']} processed), {summ['production_children_compared']} production children "
            f"compared, {summ['mismatching_parents']} mismatching, {len(summ['unreplayable_cells'])} unreplayable, "
            f"stages {summ['stages_checked']} ({kinds}) ok {summ['stages_ok']}, seeds {len(summ['seeds'])}, "
            f"red_all {summ.get('red_all')}; wall {fp['replay_wall_seconds']} s against the run's "
            f"{fp['run_dag2_wall_seconds']} s")
        need(summ["all_identical"] and summ["mismatching_parents"] == 0 and summ["sampled_parents"] > 0
             and not summ["unreplayable_cells"] and summ["stages_ok"], f"G1: slice {s}'s replay is not clean")
        need(summ["fraction"] == float(FRACTION) and summ["whole_max"] == 100 and summ["min_per_shard"] == 2
             and summ["seed"] == "20260926", f"G1: slice {s}'s replay did not use the runbook's default settings")
    need(fp0["mode"] == "full" and s0["levels"] == "" and {"reach", "keep+slice", "keep"} <= {st["kind"] for st in s0["stages"]},
         "G1: slice 0's replay is not a full one with every stage kind")
    full10 = [x for x in s0["seeds"] if x.get("full_check")]
    log(f"G1 slice 0 seeds: {len(s0['seeds'])} seed levels, all identical {all(x['identical'] for x in s0['seeds'])}; "
        f"level-10 full recomputations {[(x['cell'], x['records'], x['enum2_records'], x['full_identical']) for x in full10]}")
    need(bool(full10) and all(x["identical"] for x in s0["seeds"]) and all(x["full_identical"] for x in full10),
         "G1: slice 0's seeds were not all recomputed identical")
    need(fp1["mode"] == "slice" and s1["levels"] == "13-16" and not s1["seeds"] and "red_all" not in s1
         and not (res_dir(1) / "replay" / "red.json").exists(), "G1: slice 1's replay is not a slice-mode one")
    log("G1 slice 0 red controls: " + "; ".join(f"{r['id']} {'red' if r['went_red'] else 'NOT RED'}" for r in red))
    need(len(red) == 6 and all(r["went_red"] for r in red), "G1: not every red control went red")
    r3 = next((r for r in red if r["id"] == "R3"), {})
    log(f"G1 R3: {json.dumps(r3)}")
    marker = WORK / "out" / f"g4-prefix-{KEY}.json"
    need(marker.is_file() and load(marker).get("slice") == "s0of2", "G1: the prefix marker does not name slice 0")
    pins = load(WORK / "res" / f"pins-{HOST}.json")
    need({"enum2/enum2.py", "enum2/replay-398.py"} <= set(pins["sha256"]) and pins.get("replay", {}).get("pynauty"),
         "G1: the pins file does not pin the replay")
    sc = load(WORK / "res" / f"replay-selfcheck-{HOST}.json")
    log(f"G1 replay self-check: {json.dumps(sc)}")
    need(sc.get("ok") is True, "G1: the replay self-check did not pass")
    files = [p for p in (WORK / "res").rglob("*") if p.is_file()]
    big = [str(p) for p in files if p.stat().st_size >= 4_000_000]
    log(f"G1 result files: {len(files)}, largest {max(p.stat().st_size for p in files) / 1e3:.0f} kB; replay files "
        f"slice 0 {sorted(p.name for p in (res_dir(0) / 'replay').iterdir())}, slice 1 "
        f"{sorted(p.name for p in (res_dir(1) / 'replay').iterdir())}")
    need(not big, f"G1: result files over 4 MB: {big}")
    return r3


def g1b(r3: dict) -> None:
    """R3's extension beyond the sample has teeth: the parent it used, with one child dropped from its block."""
    if r3.get("from_sample") is not False:
        log("G1b skipped: R3's parent came from the sample (the extension was not needed)")
        return
    copy = WORK / "g1b" / run_dir(0).name    # the same base name, so the same sample and the same R3 order
    shutil.rmtree(copy.parent, ignore_errors=True)
    shutil.copytree(run_dir(0), copy, symlinks=True)
    cell, index = r3["cell"], r3["index"]
    manifest = load(copy / f"{cell}.manifest.json")
    parents = []
    for src in manifest["parent_sources"]:     # the recorded paths: the original directory's files, unchanged
        parents += lines_of(Path(src["file"]))
    sys.path.insert(0, str(REPLAY.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("replay398", REPLAY)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    lines = replay.LineFile(copy / f"{cell}.g6")
    start, end = replay.BlockFinder(lines, parents, 0, len(parents)).block(index)
    lines.close()
    cell_lines = lines_of(copy / f"{cell}.g6")
    if end > start:      # the block loses its first child
        changed, what = cell_lines[:start] + cell_lines[start + 1:], f"lost {cell_lines[start]}"
    else:                # an empty block gains a child of this parent that the 398 reject
        g, m = replay.enum2.graph6_decode(parents[index]), int(cell.split("-")[1])
        spurious = sorted(set(replay.enum2.extend_parent(g, m, replay.forbidden("74")))
                          - set(replay.enum2.extend_parent(g, m, replay.forbidden("398"))))[0]
        changed, what = cell_lines[:start] + [spurious] + cell_lines[start:], f"gained {spurious}"
    write_lines(copy / f"{cell}.g6", changed)
    manifest["children_file_sha256"] = sha256(copy / f"{cell}.g6")
    manifest["children_written"] = len(changed)
    (copy / f"{cell}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    out = WORK / "g1b" / "replay"
    cmd = ["nice", "-n", "10", str(MATHS_PY), str(REPLAY), "--run-dir", str(copy), "--forbidden-set", "398",
           "--fraction", FRACTION, "--seed", "20260926", "--min-per-shard", "2", "--whole-max", "100", "--seeds", "off",
           "--red", "--red-budget", "2000", "--workers", "2", "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    summ = load(out / "summary.json")
    red3 = next(r for r in summ["red_controls"] if r["id"] == "R3")
    others = [r["went_red"] for r in summ["red_controls"] if r["id"] != "R3"]
    log(f"G1b parent {index} of {cell} (block of {end - start}) {what}: replay exit {p.returncode}; sampled "
        f"parents all identical {summ['all_identical']}; R3: {json.dumps(red3)[:400]}; other controls red {others}")
    need(p.returncode == 1 and summ["all_identical"] and red3["went_red"] is False and "discrepancy" in red3["control"]
         and red3.get("index") == index and all(others), "G1b: R3 used a parent that differs from production")


def g3() -> dict:
    """Corrupt one child in one shard file of slice 0 so that it is lost, as a faulty udenum shard would, and let
    run-dag2.py --resume rebuild the cell and every level above it from the shards; U23_CLEANUP=1 must delete nothing."""
    entries = [json.loads(x) for x in lines_of(run_dir(0).with_name(run_dir(0).name + ".replay") / "replay.jsonl")[1:]]
    cands = [e for e in entries if e["n"] > 12 and e["production"] >= 1 and e["identical"] and e["where"] == "cell file"]
    if not cands:
        problems.append("G3: no sampled parent above the slice level with a child")
        return {}
    e = max(cands, key=lambda x: (x["n"], -x["index"]))
    cell, i, (start, end) = e["cell"], e["index"], e["block"]
    n = int(cell.split("-")[0])
    d = run_dir(0)
    block = lines_of(d / f"{cell}.g6")[start:end]
    shards = []
    for mf in (d / "shards" / cell).glob(f"{cell}-*.manifest.json"):
        info = load(mf)
        shards.append((int(info["parent_range"][0]), int(info["parent_range"][1]), mf,
                       d / "shards" / cell / f"{info['shard_id']}.g6"))
    shards.sort()
    offset = 0
    for a, b, mf, sf in shards:
        records = lines_of(sf)
        if a <= i < b:
            k = start - offset
            if records[k] != block[0]:
                problems.append(f"G3: shard {sf.name} line {k} is not the block's first child")
                return {}
            del records[k]                              # the corrupted shard: that child is gone
            write_lines(sf, records)
            info = load(mf)                             # its manifest, as udenum writes it for what it wrote
            info["children_file_sha256"] = sha256(sf)
            info["children_written"] = len(records)
            mf.write_text(json.dumps(info, indent=2) + "\n")
            break
        offset += len(records)
    else:
        problems.append("G3: no shard covers the victim parent")
        return {}
    # run-dag2.py --resume rebuilds the cell from its shards (a duplicate record would instead be refused by prune.py,
    # a record that is not canonical or contains one of the 398 by the stage verification: a LOST child is the fault
    # only the replay can see), then that level's reach, prune and verification steps; everything above the level
    # is deleted too, so that it is regenerated from the corrupted level as it would have been in production
    (d / f"{cell}.g6").unlink()
    (d / f"{cell}.manifest.json").unlink()
    removed = 0
    for p in list(d.rglob("*")):
        head = p.name.split(".")[0].split("-")
        if p.is_file() and len(head) >= 2 and head[0].isdigit() and int(head[0]) > n:
            p.unlink()
            removed += 1
    victim = {"cell": cell, "index": i, "record": e["record"], "lost": block[0], "shard": sf.name, "block": [start, end]}
    log(f"G3 planted: parent {i} of {cell} ({e['record']}), block {block}: the child {block[0]} deleted from "
        f"{sf.name} (its manifest rewritten to match); the cell file, its aggregate manifest and the {removed} files of "
        f"levels above {n} deleted for run-dag2.py --resume to rebuild")
    code, text = runbook(["2", "0", "1"], env(U23_CLEANUP="1"), "g3-planted")
    log(f"G3 runbook (U23_CLEANUP=1) exit {code}; log:\n" + show(text))
    fail_line = [x for x in text.splitlines() if "G4 REPLAY FAILED for slice s0of2" in x]
    need(code == 5 and bool(fail_line) and "MISMATCH" in fail_line[0], "G3: the runbook did not stop with a G4 mismatch")
    need("slice s1of2 starting" not in text, "G3: the worker went on to slice 1 after the failed replay")
    replay_dir = d.with_name(d.name + ".replay")
    log(f"G3 after the failed replay: run directory kept {d.is_dir()}, replay directory kept "
        f"{(replay_dir / 'replay.jsonl').is_file()}, 'deleted' in the log {'run directory deleted' in text}")
    need(d.is_dir() and (replay_dir / "replay.jsonl").is_file() and "run directory deleted" not in text,
         "G3: U23_CLEANUP deleted something after a failed replay")
    rebuilt = d / f"{cell}.g6"
    need(rebuilt.is_file() and block[0] not in set(lines_of(rebuilt)) and
         load(d / f"{cell}.manifest.json")["children_file_sha256"] == sha256(rebuilt),
         "G3: run-dag2.py did not rebuild the cell from the corrupted shard")
    failed = res_dir(0) / "replay" / "FAILED"
    mism = [json.loads(x) for x in lines_of(res_dir(0) / "replay" / "mismatches.jsonl")] if \
        (res_dir(0) / "replay" / "mismatches.jsonl").is_file() else []
    hit = [m for m in mism if m["cell"] == cell and m["index"] == i]
    log(f"G3 FAILED: {failed.read_text().strip() if failed.is_file() else None}; mismatches.jsonl: {len(mism)} "
        f"entries; the victim's: {json.dumps(hit[0])[:500] if hit else None}")
    need(failed.is_file() and "MISMATCH" in failed.read_text(), "G3: replay/FAILED does not name the mismatch")
    need(bool(hit) and hit[0]["only_enum2"] == 1 and hit[0]["only_enum2_first"] == [block[0]]
         and hit[0]["only_production"] == 0 and hit[0]["production"] == len(block) - 1,
         "G3: mismatches.jsonl does not show exactly the lost child")
    return victim


def g6() -> str:
    """An empty slice (no level-12 graph hashes to it) is not a failure: the replay reads its empty slice files,
    re-derives them from the level-12 keep files, and the run itself generated from no parent above level 12."""
    sys.path.insert(0, str(REPLAY.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("replay398", REPLAY)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    used = set()
    for keep in run_dir(1).glob("12-*.keep.g6"):
        used |= {replay.slice_number(x, 1920) for x in lines_of(keep)}
    idx = min(set(range(1920)) - used)
    code, text = runbook(["1920", str(idx)], env(), "g6-empty")
    tag = f"s{idx}of1920"
    fp = WORK / "res" / KEY / tag / "replay" / "fingerprint.json"
    info = load(fp) if fp.is_file() else {}
    linked = f"slice {tag}: levels <= 12 hard-linked from {WORK / 'out' / ('prefix-' + KEY)} " in text
    log(f"G6 slice {tag} (no level-12 graph hashes to it; {len(used)} indices of 1920 do): exit {code}; prefix "
        f"hard-linked from the prefix directory {linked}; {[x[22:250] for x in text.splitlines() if 'G4' in x]}; "
        f"fingerprint: result {info.get('result')}, sampled {info.get('sampled_parents')}, stage files "
        f"{info.get('stages_checked')}")
    need(code == 0 and linked and info.get("result") == "EMPTY" and info.get("sampled_parents") == 0
         and (info.get("stages_checked") or 0) > 0, "G6: an empty slice was not passed as EMPTY")
    return tag


# ------------------------------------------------------------------ G8, G9: the second area, U23_CLEANUP=1
C_OUT, C_RES = WORK / "c-out", WORK / "c-res"
C_PREFIX, C_MARKER = C_OUT / f"prefix-{KEY}", C_OUT / f"g4-prefix-{KEY}.json"


def c_env(**over: str) -> dict:
    return env(U23_OUT=str(C_OUT), U23_RES=str(C_RES), U23_CLEANUP="1", **over)


def c_dir(s: int) -> Path:
    return C_OUT / f"dag-{KEY}-s{s}of5"


def c_res(s: int) -> Path:
    return C_RES / KEY / f"s{s}of5"


def c_done(s: int) -> Path:
    return C_OUT / f"done-{KEY}-s{s}of5.json"


def gone(s: int) -> bool:
    return not c_dir(s).exists() and not Path(f"{c_dir(s)}.replay").exists()


def prefix_hashes(s: int) -> dict:
    return {k: v for k, v in load(c_res(s) / "hashes.json")["files"].items() if int(k.split("-")[0]) <= 12}


def g8() -> None:
    head = subprocess.run(["/usr/bin/git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    git_record()
    # A1: slice 0 builds the prefix, is replayed in full, pushed, then deleted
    code, text = runbook(["5", "0"], c_env(), "g8-a1")
    lines = text.splitlines()
    at = lambda s: next((k for k, x in enumerate(lines) if s in x), -1)
    i_pass, i_del = at("G4 replay of slice s0of5 (full): PASS"), at("slice s0of5: run directory deleted")
    adds, msgs, pushes, refused, failed = git_record()
    kept = {str(p.relative_to(c_res(0))) for p in c_res(0).rglob("*") if p.is_file()}
    want = {"replay/summary.json", "replay/red.json", "replay/fingerprint.json", "hashes.json", "counts.json",
            "run-summary.json", "run-config.json", "reach.json", "16-41.g6", "16-41.keep.g6", "16-41.manifest.json"}
    done = load(c_done(0)) if c_done(0).is_file() else {}
    made = load(C_PREFIX / "prefix.json") if (C_PREFIX / "prefix.json").is_file() else {}
    log(f"G8 A1 slice 0: exit {code}; replay PASS at log line {i_pass}, deletion at {i_del}; commits {msgs}, pushes "
        f"{pushes}; run and replay directories gone {gone(0)}; logs kept {Path(f'{c_dir(0)}.log').is_file()} "
        f"{Path(f'{c_dir(0)}.replay.log').is_file()}; results kept {len(kept)} files, missing {sorted(want - kept)}; "
        f"done marker {done}; prefix directory made from {made.get('made_from')} ({len(made.get('files', {}))} files)")
    need(code == 0 and 0 <= i_pass < i_del and len(msgs) == 1 and pushes == 1 and not failed and not refused
         and gone(0) and Path(f"{c_dir(0)}.log").is_file() and Path(f"{c_dir(0)}.replay.log").is_file()
         and want <= kept and done.get("commit") == head and done.get("results") == str(c_res(0))
         and made.get("made_from") == str(c_dir(0)), "G8 A1: slice 0 was not replayed, pushed and only then deleted")
    # A2: a restart on slices 0 and 1, the G4 marker gone: slice 1 is replayed in full over a hard-linked prefix
    C_MARKER.unlink(missing_ok=True)
    code, text = runbook(["5", "0", "1"], c_env(), "g8-a2")
    adds, msgs, pushes, refused, failed = git_record()
    linked = f"slice s1of5: levels <= 12 hard-linked from {C_PREFIX} " in text
    summ = load(c_res(1) / "replay" / "summary.json") if (c_res(1) / "replay" / "summary.json").is_file() else {}
    same = prefix_hashes(1) == prefix_hashes(0) if (c_res(1) / "hashes.json").is_file() else False
    log(f"G8 A2 restart on 0 and 1: exit {code}; slice 0 skipped {'slice s0of5: done before' in text}, started "
        f"{'slice s0of5 starting' in text}; slice 1 hard-linked from the prefix directory {linked}, replayed in full "
        f"{'G4 replay of slice s1of5 (full): PASS' in text} (seeds identical "
        f"{all(x.get('identical') for x in summ.get('seeds', [])) and bool(summ.get('seeds'))}, red {summ.get('red_all')}); "
        f"levels <= 12 equal slice 0's: {same} ({len(prefix_hashes(1)) if same else '?'} files); commits {msgs}; "
        f"slice 1 deleted {gone(1)}, done marker {c_done(1).is_file()}")
    need(code == 0 and "slice s0of5: done before" in text and "slice s0of5 starting" not in text and linked
         and "G4 replay of slice s1of5 (full): PASS" in text and summ.get("red_all") is True and same
         and len(msgs) == 1 and msgs[0].startswith("u23 slice s1of5 done:") and pushes == 1 and gone(1)
         and c_done(1).is_file(), "G8 A2: the restart did not skip slice 0 and run slice 1 from the prefix directory")
    # A3: the same restart again
    code, text = runbook(["5", "0", "1"], c_env(), "g8-a3")
    adds, msgs, pushes, refused, failed = git_record()
    log(f"G8 A3 restart again: exit {code}; skipped {text.count('done before')}; started {text.count(' starting ')}; "
        f"commits {msgs}")
    need(code == 0 and text.count("done before") == 2 and " starting " not in text and not msgs,
         "G8 A3: a second restart did not skip both slices")
    # A4, A5: a failed push keeps the run directory; the next attempt pushes and only then deletes
    code, text = runbook(["5", "2"], c_env(GIT_STUB_PUSH_FAIL="1"), "g8-a4")
    adds, msgs, pushes, refused, failed = git_record()
    log(f"G8 A4 slice 2, pushes failing: exit {code}; commits {msgs}, pushes {pushes}, failed pushes {failed}; "
        f"{[x[22:200] for x in text.splitlines() if 'not pushed' in x or 'push' in x]}; run directory kept "
        f"{c_dir(2).is_dir()}, done marker {c_done(2).is_file()}")
    need(code == 0 and len(msgs) == 1 and pushes == 0 and failed == 3 and "its results are not pushed" in text
         and c_dir(2).is_dir() and not c_done(2).is_file() and "run directory deleted" not in text,
         "G8 A4: a failed push did not keep the run directory")
    code, text = runbook(["5", "2"], c_env(), "g8-a5")
    adds, msgs, pushes, refused, failed = git_record()
    log(f"G8 A5 slice 2 again: exit {code}; replay repeated {'(slice:' in text}, 'already passed' "
        f"{'already passed on this content' in text}; commits {msgs}, pushes {pushes}; deleted {gone(2)}, done marker "
        f"{c_done(2).is_file()}")
    need(code == 0 and "already passed on this content" in text and "(slice:" not in text and len(msgs) == 1
         and pushes == 1 and gone(2) and c_done(2).is_file(), "G8 A5: the retried slice was not pushed and deleted")


def g9() -> None:
    code, text = runbook(["5", "3"], c_env(U23_MIN_FREE_GB="1000000"), "g9-a")
    adds, msgs, pushes, refused, failed = git_record()
    stop = [x for x in text.splitlines() if "STOPPING this worker before slice s3of5" in x]
    disk = [x for x in text.splitlines() if "slice s3of5: disk " in x]
    log(f"G9 a U23_MIN_FREE_GB=1000000: exit {code}; {disk[0][22:] if disk else 'no disk line'}; "
        f"{stop[0][22:] if stop else 'no stop line'}; started {'slice s3of5 starting' in text}; commits {msgs}")
    need(code == 6 and bool(stop) and bool(disk) and "slice s3of5 starting" not in text and not c_dir(3).exists()
         and not msgs, "G9 a: the disk guard did not stop the worker before the slice")
    DF_STUB.mkdir(exist_ok=True)
    (DF_STUB / "df").write_text(DF_SCRIPT)
    (DF_STUB / "df").chmod(0o755)
    state = WORK / "dfstub.state"
    state.unlink(missing_ok=True)
    e = c_env(U23_MIN_FREE_GB="5", DF_STUB_SEQ=f"{10 * 1048576} {1048576}", DF_STUB_STATE=str(state))
    e["PATH"] = f"{DF_STUB}:{e['PATH']}"
    code, text = runbook(["5", "3", "4"], e, "g9-b")
    adds, msgs, pushes, refused, failed = git_record()
    disk = [x[22:] for x in text.splitlines() if ": disk " in x]
    stop = [x for x in text.splitlines() if "STOPPING this worker before slice s4of5" in x]
    log(f"G9 b stand-in df (10 GB, then 1 GB free), U23_MIN_FREE_GB=5: exit {code}; disk lines {disk}; slice 3 done "
        f"{'slice s3of5 done' in text}, deleted {gone(3)}; {stop[0][22:] if stop else 'no stop line'}; slice 4 started "
        f"{'slice s4of5 starting' in text}; commits {msgs}")
    need(code == 6 and "slice s3of5 done" in text and gone(3) and bool(stop) and "slice s4of5 starting" not in text
         and not c_dir(4).exists() and len(msgs) == 1 and msgs[0].startswith("u23 slice s3of5 done:") and len(disk) == 2,
         "G9 b: the disk guard did not stop the worker between slices")


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    STUB.mkdir(parents=True)
    (STUB / "git").write_text(STUB_SCRIPT)
    (STUB / "git").chmod(0o755)
    refusals()
    git_record()
    code, text = runbook(["2", "0", "1"], env(), "g1")
    log(f"G1 runbook exit {code}; log:\n" + show(text))
    r3 = g1(code, text)
    g7("G1", ["u23 slice s0of2 done: through n 16; G4 replay PASS (full, ",
              "u23 slice s1of2 done: through n 16; G4 replay PASS (slice, "], True)
    g1b(r3)
    code, text = runbook(["2", "0", "1"], env(), "g2-restart")
    log(f"G2 restart: exit {code}; log:\n" + show(text, "G4"))
    need(code == 0 and text.count("already passed on this content") == 2 and "(full:" not in text and "(slice:" not in text,
         "G2: a restart replayed a slice whose replay had passed on the same content")
    g7("G2", ["u23 slice s0of2 done: through n 16; G4 replay passed before",
              "u23 slice s1of2 done: through n 16; G4 replay passed before"], True)
    victim = g3()
    g7("G3", ["u23 slice s0of2 G4 REPLAY FAILED (slice): MISMATCH"], False)
    if victim:
        code, text = runbook(["2", "0", "1"], env(U23_REPLAY="0"), "g4-no-replay")
        log(f"G4 the corrupted directories with U23_REPLAY=0: exit {code}; G4 lines: "
            f"{[x for x in text.splitlines() if 'G4' in x]}; all slices done: {'all slices done' in text}")
        need(code == 0 and "all slices done: 0 1" in text and "G4" not in text,
             "G4: without the replay the planted fault was stopped by something else")
        g7("G4", ["u23 slice s0of2 done: through n 16; no G4 replay (U23_REPLAY=0)",
                  "u23 slice s1of2 done: through n 16; no G4 replay (U23_REPLAY=0)"], False)
    tag = g6()
    g7("G6", [f"u23 slice {tag} done: through n 16; G4 replay EMPTY (slice, 0 parents)"], True)
    g8()
    g9()
    for p in problems:
        log("PROBLEM:", p)
    log("RUNBOOK-G4", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
