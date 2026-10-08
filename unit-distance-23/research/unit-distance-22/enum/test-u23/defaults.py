#!/usr/bin/env python3
"""run-dag2.py: the defaults reproduce the u(22) run, and the u(23) options do what they claim.

A. For every recorded run directory below, the NEW run-dag2.py is started with that run's
   options and stopped the moment it would generate the first seed file. PASS iff the
   reach.json and run-config.json it wrote are byte-identical to the recorded ones (Mode 74,
   the built-in u-bar, no stage verification).
     out-22/dag-22-61-f12                 (22,61) reach, root k 5, prune from 12 filter-only
     results/u22/s0of48 (worker w1)       the same, sliced at 13 (index 0 of 48): the production
                                          invocation of coordination/cloud-workers/u22-slice.sh
     out-prune/dag-17-43-prune16          (17,43) reach, prune from 16 with the embedder
     out-prune/dag-18-46-reach            (18,46) reach only
     out-prune/dag-18-46-k4               (18,46) reach, root k 4 (the red control of PRUNING.md 4.7d)
B. The u(23) invocation (Mode 398, --ubar 22=60) writes a reach table that follows from its root
   by the L4 recursion with u-bar(22) = 60, and the contract's statements about it (CONTRACT.md
   Section 2) are tested against the numbers rather than assumed.
C. Refusals: every malformed or unjustified option must stop run-dag2.py before any work.
D. The u(24) pilot composes two overrides, derives root k 5, and admits the new L4 routes
   while retaining the u(23) table through level 15.

usage: defaults.py [--u22-slice-dir DIR]   (DIR holds results/u22/s0of48 from worker w1)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from u23lib import ENUM, F74, RUN_DAG2, SCRATCH, load_run_dag2, log

WORK = SCRATCH / "defaults"
JUSTIFY = ("u(22) = 60: research/unit-distance-22/RESULT-u22.md (no unit-distance graph on 22 "
           "vertices has 61 edges)")


class Stop(Exception):
    pass


def start_and_stop(argv: list[str], script: Path | None = None) -> tuple[bool, str]:
    """Run run-dag2.py's main() (or another copy's) in-process until the first seed."""
    if script is None:
        rd = load_run_dag2()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_dag2_baseline", script)
        rd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rd)

    def stop(*_args, **_kwargs):
        raise Stop()

    rd.run_seed = stop
    saved = sys.argv
    sys.argv = ["run-dag2.py", *argv]
    try:
        rd.main()
        return True, "ran to completion"
    except Stop:
        return True, "stopped at the first seed"
    except (OSError, ValueError, RuntimeError) as error:
        return False, f"{type(error).__name__}: {error}"
    finally:
        sys.argv = saved


def part_a(slice_dir: Path | None) -> list[str]:
    problems = []
    runs = [
        ("out-22/dag-22-61-f12", ENUM / "out-22" / "dag-22-61-f12",
         ["--target-n", "22", "--target-m", "61", "--reach", "--reach-root-k", "5", "--prune",
          "--prune-from", "12", "--prune-filter-only", "--prune-python", sys.executable]),
        ("out-prune/dag-17-43-prune16", ENUM / "out-prune" / "dag-17-43-prune16",
         ["--target-n", "17", "--target-m", "43", "--reach", "--prune", "--prune-from", "16",
          "--prune-python", sys.executable]),
        ("out-prune/dag-18-46-reach", ENUM / "out-prune" / "dag-18-46-reach",
         ["--target-n", "18", "--target-m", "46", "--reach"]),
        ("out-prune/dag-18-46-k4", ENUM / "out-prune" / "dag-18-46-k4",
         ["--target-n", "18", "--target-m", "46", "--reach", "--reach-root-k", "4"]),
    ]
    if slice_dir is not None:
        runs.append(("results/u22/s0of48 (w1)", slice_dir,
                     ["--target-n", "22", "--target-m", "61", "--jobs", "4", "--reach", "--reach-root-k", "5",
                      "--prune", "--prune-from", "12", "--prune-filter-only", "--prune-python", sys.executable,
                      "--slice-level", "13", "--slice-index", "0", "--slice-count", "48", "--resume"]))
    for name, recorded, argv in runs:
        out = WORK / "a" / name.replace("/", "_").replace(" ", "_")
        base = WORK / "a-baseline" / name.replace("/", "_").replace(" ", "_")
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(base, ignore_errors=True)
        ok, message = start_and_stop([*argv, "--output-dir", str(out)])
        if not ok:
            problems.append(f"A {name}: run-dag2.py refused: {message}")
            continue
        if BASELINE is not None:
            ok_b, message_b = start_and_stop([*argv, "--output-dir", str(base)], BASELINE)
            if not ok_b:
                problems.append(f"A {name}: the baseline run-dag2.py refused: {message_b}")
                continue
        report = []
        for f in ("reach.json", "run-config.json"):
            new = (out / f).read_bytes()
            same_recorded = new == (recorded / f).read_bytes()
            same_baseline = None if BASELINE is None else new == (base / f).read_bytes()
            base_recorded = None if BASELINE is None else (base / f).read_bytes() == (recorded / f).read_bytes()
            report.append(f"{f}: = recorded {same_recorded}, = baseline {same_baseline}")
            if same_baseline is False:
                problems.append(f"A {name}: {f} differs from the baseline run-dag2.py's")
            if not same_recorded and base_recorded is not False:
                problems.append(f"A {name}: {f} differs from the recorded run" + (" (and the baseline does not)" if base_recorded else " (no --baseline given, so an older recorder cannot be ruled out)"))
            if not same_recorded and base_recorded is False:
                report.append(f"({f} recorded by an older run-dag2.py: the baseline differs from it too)")
        log(f"A {name}: {message}; " + "; ".join(report))
    return problems


def u23_argv(out: Path, *extra: str) -> list[str]:
    return ["--target-n", "23", "--target-m", "65", "--forbidden-set", "398", "--reach",
            "--reach-root-k", "5", "--ubar", "22=60", "--ubar-justification", JUSTIFY, "--prune",
            "--prune-from", "12", "--prune-filter-only", "--prune-python", sys.executable,
            "--verify-stages", "--slice-level", "13", "--slice-index", "0", "--slice-count", "64",
            "--output-dir", str(out), *extra]


def part_b() -> list[str]:
    problems = []
    out = WORK / "b" / "u23"
    shutil.rmtree(out, ignore_errors=True)
    ok, message = start_and_stop(u23_argv(out))
    if not ok:
        return [f"B: the u(23) invocation was refused: {message}"]
    reach = json.loads((out / "reach.json").read_text())
    config = json.loads((out / "run-config.json").read_text())
    rd = load_run_dag2()
    ubar = {int(k): v for k, v in reach["ubar"].items()}
    # Later built-in bounds must not change the historical reach.json bytes or their hashes.
    expected_ubar = {n: v for n, v in rd.UBAR.items() if n <= 23}
    expected_ubar[22] = 60
    if ubar != expected_ubar:
        problems.append(f"B: reach.json ubar is not the built-in table with u-bar(22) = 60: {ubar}")
    if reach.get("ubar_override") != {"22": {"builtin": 62, "value": 60}}:
        problems.append(f"B: reach.json ubar_override is {reach.get('ubar_override')}")
    if reach.get("ubar_justification") != JUSTIFY:
        problems.append("B: reach.json does not record the justification")
    if (config.get("forbidden_set"), config.get("verify_stages"), config.get("ubar_override")) != \
            (398, True, {"22": {"builtin": 62, "value": 60}}):
        problems.append(f"B: run-config.json does not record set 398, stage verification and the override: {config}")
    # the table must follow from its root by L4 with this ubar (an independent recomputation)
    table = {23: {65: 5}}
    for n in range(22, 9, -1):
        level: dict[int, int] = {}
        for cm, k in table[n + 1].items():
            for d in range(k, min(n, (2 * cm) // (n + 1)) + 1):
                m = cm - d
                if 0 <= m <= ubar[n]:
                    level[m] = min(level.get(m, d), max(0, d - 1))
        table[n] = level
    stored = {int(n): {int(m): k for m, k in lv.items()} for n, lv in reach["table"].items()}
    if stored != table:
        problems.append("B: reach.json table does not follow from its root by L4")
    # CONTRACT.md Section 2: "It admits m = 60 only at level 22 (k = 4), 55..56 at 21, 50..53 at 20
    # and 45..50 at 19; windows are one edge wider at the sparse end than the (22,61) run's from
    # level 15 up."
    claims = {22: [60], 21: [55, 56], 20: [50, 51, 52, 53], 19: [45, 46, 47, 48, 49, 50]}
    for n, ms in claims.items():
        if sorted(stored[n]) != ms:
            problems.append(f"B: contract says level {n} admits {ms}, reach table has {sorted(stored[n])}")
    if stored[22] != {60: 4}:
        problems.append(f"B: contract says k = 4 at (22,60); table has {stored[22]}")
    u22 = json.loads((ENUM / "out-22" / "dag-22-61-f12" / "reach.json").read_text())
    u22t = {int(n): {int(m): k for m, k in lv.items()} for n, lv in u22["table"].items()}
    lines = []
    for n in range(10, 24):
        a = sorted(stored[n])
        b = sorted(u22t.get(n, {}))
        lines.append(f"  n={n:2d} u23 {a[0]}..{a[-1]} ({len(a)} cells)" +
                     (f"   u22 {b[0]}..{b[-1]} ({len(b)} cells)" if b else ""))
        # the contract's sentence is about the sparse end; the dense end is reported, not assumed
        if 15 <= n <= 21 and b and a[0] != b[0] - 1:
            problems.append(f"B: at level {n} the u23 window {a[0]}..{a[-1]} is not one edge wider at "
                            f"the sparse end than the u22 window {b[0]}..{b[-1]}")
        if 10 <= n <= 14 and b and a != b:
            problems.append(f"B: below level 15 the windows should agree; level {n}: {a} vs {b}")
        if 15 <= n <= 21 and b and a[-1] != b[-1]:
            lines[-1] += f"   <- also {a[-1] - b[-1]} edge wider at the dense end"
    log("B: u(23) reach table (Mode 398, root k 5, u-bar(22) = 60) against the (22,61) run's:")
    for line in lines:
        log(line)
    log("B: table by level: " + json.dumps({str(n): stored[n] for n in range(19, 24)}))
    windows = json.loads((out / "reach.json").read_text())["schade_windows"]
    log(f"B: Schade windows 19..23: {[windows[str(n)] for n in range(19, 24)]}")
    return problems


def part_c() -> list[str]:
    problems = []
    base = ["--target-n", "23", "--target-m", "65", "--reach", "--reach-root-k", "5"]
    cases = [
        ("u-bar not lowered", [*base, "--ubar", "22=62", "--ubar-justification", JUSTIFY], "may only lower"),
        ("u-bar raised", [*base, "--ubar", "22=63", "--ubar-justification", JUSTIFY], "may only lower"),
        ("below the known lower bound u(22) >= 60", [*base, "--ubar", "22=59", "--ubar-justification", JUSTIFY],
         "below the best known lower bound"),
        ("n <= 21 is exact (AMP)", [*base, "--ubar", "21=56", "--ubar-justification", JUSTIFY],
         "below the best known lower bound"),
        ("below the known lower bound u(24) >= 68", [*base, "--ubar", "24=67", "--ubar-justification", JUSTIFY],
         "below the best known lower bound"),
        ("no built-in u-bar(25)", [*base, "--ubar", "25=70", "--ubar-justification", JUSTIFY], "no built-in"),
        ("malformed", [*base, "--ubar", "22", "--ubar-justification", JUSTIFY], "expected N=M"),
        ("twice", [*base, "--ubar", "22=60", "--ubar", "22=61", "--ubar-justification", JUSTIFY], "twice"),
        ("no justification", [*base, "--ubar", "22=60"], "justification"),
        ("blank justification", [*base, "--ubar", "22=60", "--ubar-justification", "  "], "justification"),
        ("justification without --ubar", [*base, "--ubar-justification", JUSTIFY], "without --ubar"),
        ("--ubar without --reach", ["--target-n", "23", "--target-m", "65", "--ubar", "22=60",
                                    "--ubar-justification", JUSTIFY], "needs --reach"),
        ("set 398 with the 74 file", [*base, "--forbidden-set", "398", "--forbidden", str(F74)], "pinned"),
        ("seed mutation outside set 398", [*base, "--mutation-seeds-74"], "control for --forbidden-set 398"),
    ]
    for name, argv, needle in cases:
        out = WORK / "c" / name.replace(" ", "_").replace("/", "_")
        shutil.rmtree(out, ignore_errors=True)
        ok, message = start_and_stop([*argv, "--output-dir", str(out)])
        good = (not ok) and needle in message
        log(f"C {name}: {'refused' if not ok else 'ACCEPTED'}: {message[:150]}")
        if not good:
            problems.append(f"C {name}: expected a refusal mentioning {needle!r}, got {message!r}")
        if out.exists() and any(out.iterdir()):
            problems.append(f"C {name}: files were written before the refusal: {sorted(p.name for p in out.iterdir())}")
    # --forbidden-set 75 is refused by argparse (exit 2)
    p = subprocess.run([sys.executable, str(RUN_DAG2), "--target-n", "17", "--target-m", "43",
                        "--forbidden-set", "75", "--output-dir", str(WORK / "c" / "set75")],
                       capture_output=True, text=True)
    log(f"C set 75: exit {p.returncode}: {p.stderr.strip().splitlines()[-1][:120]}")
    if p.returncode != 2 or "invalid choice" not in p.stderr:
        problems.append("C set 75: not refused by argparse")
    # a directory started in one set cannot be resumed in the other
    out = WORK / "c" / "resume-across-sets"
    shutil.rmtree(out, ignore_errors=True)
    ok1, _ = start_and_stop(["--target-n", "17", "--target-m", "43", "--reach", "--output-dir", str(out)])
    ok2, message = start_and_stop(["--target-n", "17", "--target-m", "43", "--reach", "--forbidden-set",
                                   "398", "--resume", "--output-dir", str(out)])
    log(f"C resume a set-74 directory in set 398: {'refused' if not ok2 else 'ACCEPTED'}: {message[:120]}")
    if not ok1 or ok2 or "run-config.json differs" not in message:
        problems.append("C resume across sets: not refused")
    return problems


def part_d() -> list[str]:
    problems = []
    out = WORK / "d" / "u24"
    shutil.rmtree(out, ignore_errors=True)
    justification = (JUSTIFY + "; u(23) = 64: research/unit-distance-23/RESULT-u23.md "
                     "(COMPLETE, gates G2 to G6 met)")
    argv = ["--target-n", "24", "--target-m", "69", "--reach", "--ubar", "22=60", "--ubar", "23=64",
            "--ubar-justification", justification, "--output-dir", str(out)]
    ok, message = start_and_stop(argv)
    if not ok:
        return [f"D: the u(24) invocation was refused: {message}"]
    reach = json.loads((out / "reach.json").read_text())
    config = json.loads((out / "run-config.json").read_text())
    overrides = {"22": {"builtin": 62, "value": 60}, "23": {"builtin": 66, "value": 64}}
    for name, value in (("reach.json", reach), ("run-config.json", config)):
        if value.get("ubar_override") != overrides or value.get("ubar_justification") != justification:
            problems.append(f"D: {name} does not record both overrides and their justification")
    if reach["root_k"] != 5 or reach["root_k_source"] != "Schade: d >= target_m - u-bar(target_n - 1)":
        problems.append("D: u(24)'s default root bound is not 69 - 64 = 5")
    if [reach["ubar"][str(n)] for n in (22, 23, 24)] != [60, 64, 72]:
        problems.append("D: u(24)'s effective bounds are not 60, 64, 72")
    old = json.loads((WORK / "b" / "u23" / "reach.json").read_text())
    if any(reach["table"][str(n)] != old["table"][str(n)] for n in range(10, 16)):
        problems.append("D: u(24) and u(23) reach tables differ before level 16")
    # These routes add vertices of degrees 1, 2, 3, 4; the u(23) tree excludes each one.
    rd = load_run_dag2()

    def parents(value, n, m):
        ubar = {int(k): v for k, v in value["ubar"].items()}
        windows = {int(k): v for k, v in value["schade_windows"].items()}
        table = {int(k): {int(e): d for e, d in v.items()} for k, v in value["table"].items()}
        if m not in table[n]:
            return []
        return rd.parent_edge_counts(argparse.Namespace(ubar=ubar), windows, table, n, m)[0]

    for n, pm, m in ((17, 39, 40), (18, 40, 42), (19, 42, 45), (20, 45, 49)):
        if pm not in parents(reach, n, m) or pm in parents(old, n, m):
            problems.append(f"D: ({n - 1},{pm})->({n},{m}) is not a newly admitted route")
    log("D: u(24) reach table (m:k), two overrides, default root k 5:")
    for n, cells in reach["table"].items():
        log(f"  {n}: " + " ".join(f"{m}:{k}" for m, k in cells.items()))
    return problems


BASELINE: Path | None = None


def main() -> int:
    global BASELINE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--u22-slice-dir", type=Path, default=None)
    ap.add_argument("--baseline", type=Path, default=None,
                    help="the landed run-dag2.py (git show 952ae252d:...) placed next to copies of prune.py "
                         "and udenum; its outputs must equal the new script's byte for byte")
    a = ap.parse_args()
    BASELINE = a.baseline
    WORK.mkdir(parents=True, exist_ok=True)
    problems = part_a(a.u22_slice_dir) + part_b() + part_c() + part_d()
    for p in problems:
        log("PROBLEM:", p)
    log("DEFAULTS", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
