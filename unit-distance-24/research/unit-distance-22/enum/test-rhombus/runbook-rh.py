#!/usr/bin/env python3
"""Local test of coordination/cloud-workers/u23-slice.sh with U23_RHOMBUS=1 and U23_TRIANGLES=1 (no cloud worker).

The rules' checker is the real check/udcheck_rhombus.py (U23_RHOMBUS_CHECKER unset, so the runbook unsets
PRUNE_UDCHECK_RHOMBUS; U23_RHOMBUS_CHECKER is used only by K6's red control, to name a missing checker).

As test-u23/runbook.py, with the documented overrides: target (16,41), root k 4 (Schade), prune from 12, sliced
at level 12 into 2 slices, JOBS=2, no toolchain step (the binaries as built), no push, scratch directories,
U23_CLEANUP=0 (the checks below read the run directories; enum/test-u23/runbook-g4.py tests the cleanup) and
U23_MIN_FREE_GB=0 (a local disk); production forbidden set 398 and stage verification.

PASS iff
  K1 U23_RHOMBUS=1 on slices 0 and 1, and U23_TRIANGLES=1 on slices 0 and 1, exit 0 after every self-check
     (make check-rhombus check-triangle among them); slice 1 hard-links its prefix from the prefix directory OF
     THE SAME RULE (prefix-16-41-L12-rh or -tri, made from that rule's slice 0); the directories carry -rh and -tri;
  K2 no rule, slice 0, into the SAME U23_OUT afterwards: exit 0, builds its own prefix (no hard link from a
     -rh or -tri directory) and writes no suffixed directory;
  K3 run-config.json and every prune manifest say rhombus: true in the -rh slices and triangles: true in the
     -tri slices, with the real checker not from the environment; the plain slice records neither; the
     pins file of every run pins filter/udrhombus, udrhombus.c, udtriangle, udtriangle.c,
     check/udcheck_rhombus.py and check/tri_verify.py;
  K4 the union of each rule's two slices' 16-41.keep.g6 contains AMP's known (16,41) graph;
  K5 verify-chain.py --check (replaying with check/udcheck_rhombus.py) accepts every rule slice: slice 0 whole with
     CHAIN OK, slice 1 from level 13 with CHAIN PARTIAL (exit 3), its levels <= 12 being hard links of slice 0's;
  K6 red: U23_RHOMBUS=2 exits 2 before writing anything; U23_RHOMBUS=1 with U23_TRIANGLES=1 exits 2; a
     missing checker (U23_RHOMBUS_CHECKER=/nonexistent/...) exits 3 before any run directory is made.

usage: runbook-rh.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from rhlib import REPO, SCRATCH, UD, canonical, decode_g6, g6_lines, known_graphs, log

RUNBOOK = REPO / "coordination" / "cloud-workers" / "u23-slice.sh"
CHECKER = UD / "check" / "udcheck_rhombus.py"
MATHS_PY = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"
WORK = SCRATCH / "runbook-rh"
PINNED = {"filter/udrhombus", "filter/udrhombus.c", "filter/udtriangle", "filter/udtriangle.c",
          "check/udcheck_rhombus.py", "check/tri_verify.py"}
SUFFIX = {"rhombus": "rh", "triangles": "tri"}
problems: list[str] = []


def env(res: Path, rhombus: str = "0", triangles: str = "0", checker: str | None = None) -> dict:
    e = dict(os.environ)
    e.update({"U23_TARGET_N": "16", "U23_TARGET_M": "41", "U23_ROOT_K": "4", "U23_PRUNE_FROM": "12",
              "U23_SLICE_LEVEL": "12", "U23_OUT": str(WORK / "out"), "U23_RES": str(res), "U23_PUSH": "0",
              "U23_TOOLCHAIN": "0", "JOBS": "2", "PY": str(MATHS_PY), "U23_RHOMBUS": rhombus,
              "U23_TRIANGLES": triangles, "U23_CLEANUP": "0", "U23_MIN_FREE_GB": "0"})
    for k in ("PRUNE_UDCHECK_RHOMBUS", "U23_RHOMBUS_CHECKER", "U23_PRUNE_FILTER_SET"):
        e.pop(k, None)
    if checker is not None:
        e["U23_RHOMBUS_CHECKER"] = checker
    return e


def runbook(args: list[str], e: dict, logname: str) -> tuple[int, str]:
    logf = WORK / f"{logname}.log"
    with logf.open("w") as stream:
        p = subprocess.run(["nice", "-n", "10", "bash", str(RUNBOOK), *args], env=e, stdout=stream,
                           stderr=subprocess.STDOUT, cwd=REPO)
    return p.returncode, logf.read_text()


def pins_ok(label: str) -> None:
    pins = json.loads((WORK / "res" / f"pins-{os.uname().nodename}.json").read_text())["sha256"]
    missing = PINNED - set(pins)
    log(f"K3 pins after the {label} run: the linear rules' files pinned: {sorted(PINNED & set(pins))}; missing {sorted(missing)}")
    if missing:
        problems.append(f"K3: the {label} run's pins lack {sorted(missing)}")


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    # K6 first: refusals before anything is written
    for label, e, want in (("U23_RHOMBUS=2", env(WORK / "red-res", rhombus="2"), 2),
                           ("U23_RHOMBUS=1 with U23_TRIANGLES=1", env(WORK / "red-res", "1", "1"), 2)):
        code, text = runbook(["2", "0"], e, "red")
        made = (WORK / "out").exists() or (WORK / "red-res").exists()
        log(f"K6 {label}: exit {code}: {text.strip()[-100:]}; anything written: {made}")
        if code != want or made:
            problems.append(f"K6: {label} was not refused before writing")
    code, text = runbook(["2", "0"], env(WORK / "red-res", "1", checker="/nonexistent/udcheck_rhombus.py"), "red-missing")
    dirs = list((WORK / "out").glob("dag-*")) if (WORK / "out").exists() else []
    log(f"K6 U23_RHOMBUS=1 with a missing checker: exit {code}: {text.strip().splitlines()[-1][-120:]}; "
        f"run directories made: {len(dirs)}")
    if code != 3 or dirs:
        problems.append("K6: a missing checker was not refused before any run")
    shutil.rmtree(WORK / "red-res", ignore_errors=True)
    shutil.rmtree(WORK / "out", ignore_errors=True)

    # K1, then K3's pins, for each rule
    rule_dirs = {}
    for rule in ("rhombus", "triangles"):
        code, text = runbook(["2", "0", "1"], env(WORK / "res", rhombus="1" if rule == "rhombus" else "0",
                                                  triangles="1" if rule == "triangles" else "0"), rule)
        log(f"K1 {rule} rule, slices 0 and 1 of 2: exit {code}\n" + "\n".join("    " + x for x in text.splitlines()))
        dirs = {s: WORK / "out" / f"dag-16-41-L12-{SUFFIX[rule]}-s{s}of2" for s in (0, 1)}
        rule_dirs[rule] = dirs
        if code != 0 or "pins and self-checks passed" not in text:
            problems.append(f"K1 {rule}: runbook exit {code}")
        prefix = WORK / "out" / f"prefix-16-41-L12-{SUFFIX[rule]}"
        made = json.loads((prefix / "prefix.json").read_text()).get("made_from") if (prefix / "prefix.json").is_file() else None
        if "slice s1of2: levels <= 12 hard-linked from " + str(prefix) + " " not in text or made != str(dirs[0]):
            problems.append(f"K1 {rule}: slice 1 did not hard-link its prefix from the same rule's prefix directory "
                            f"(made from that rule's slice 0: {made})")
        if not (WORK / "res" / f"linear-rules-selfcheck-{os.uname().nodename}.txt").is_file():
            problems.append(f"K1 {rule}: the linear rules' self-checks did not run")
        pins_ok(rule)

    # K2
    code, text = runbook(["2", "0"], env(WORK / "res"), "plain")
    plain = WORK / "out" / "dag-16-41-L12-s0of2"
    log(f"K2 no rule, slice 0, same U23_OUT: exit {code}\n" + "\n".join("    " + x for x in text.splitlines()))
    if code != 0 or "hard-linked" in text or not plain.is_dir():
        problems.append("K2: the plain run did not build its own prefix")
    pins_ok("plain")

    # K3
    for rule, dirs in rule_dirs.items():
        other = "triangles" if rule == "rhombus" else "rhombus"
        for s, d in dirs.items():
            cfg = json.loads((d / "run-config.json").read_text())
            pms = sorted(d.glob("*.prune.manifest.json"))
            bad = []
            for p in pms:
                v = json.loads(p.read_text())
                c = v.get(f"{rule}_checker", {})
                if v.get(rule) is not True or other in v or c.get("from_environment") is not False or c.get("path") != str(CHECKER):
                    bad.append(p.name)
            log(f"K3 {rule} slice {s}: run-config {rule} {cfg.get(rule)}, {other} {cfg.get(other)}; {len(pms)} prune "
                f"manifests, {len(bad)} not naming the rule and the real checker")
            if cfg.get(rule) is not True or other in cfg or bad or not pms:
                problems.append(f"K3: {rule} slice {s} does not record its rule everywhere")
    cfg = json.loads((plain / "run-config.json").read_text())
    mention = [p.name for p in plain.glob("*.prune.manifest.json")
               if any(k in json.loads(p.read_text()) for k in ("rhombus", "triangles"))]
    log(f"K3 plain slice 0: run-config rule keys {[k for k in ('rhombus', 'triangles') if k in cfg]}; prune manifests "
        f"naming a rule: {mention}")
    if any(k in cfg for k in ("rhombus", "triangles")) or mention:
        problems.append("K3: the plain run records a rule")

    # K4, K5
    known = canonical([g for g in known_graphs() if decode_g6(g)[0] == 16 and len(decode_g6(g)[1]) == 41])
    for rule, dirs in rule_dirs.items():
        union = set()
        for d in dirs.values():
            keep = d / "16-41.keep.g6"
            union |= set(g6_lines(keep)) if keep.is_file() else set()
        present = sum(1 for g in known if g in union)
        log(f"K4 {rule}: union of the two slices' 16-41.keep.g6: {len(union)} graphs; known (16,41) graphs present "
            f"{present}/{len(known)}")
        if present != len(known) or not known:
            problems.append(f"K4 {rule}: the known graph is missing")
        for s, d in dirs.items():
            cmd = ["nice", "-n", "10", sys.executable, str(UD / "enum" / "verify-chain.py"), str(d), "--check"] + \
                (["--from-n", "13"] if s else [])
            p = subprocess.run(cmd, capture_output=True, text=True)
            lines = p.stdout.strip().splitlines()
            log(f"K5 verify-chain {rule} slice {s}{' --from-n 13' if s else ''}: exit {p.returncode}: "
                f"{lines[-1] if lines else p.stderr.strip()[-200:]}; {lines[0][:220] if lines else ''}")
            # slice 0 whole is exhaustive (CHAIN OK); slice 1 from level 13 is an explicit PARTIAL (exit 3), its
            # levels <= 12 being hard links of slice 0's, checked there
            ok = (p.returncode == 0 and lines and lines[-1] == "CHAIN OK") if not s else \
                (p.returncode == 3 and lines and lines[-1].startswith("CHAIN PARTIAL") and "levels below 13" in lines[-1])
            if not ok:
                problems.append(f"K5 {rule} slice {s}: {[x for x in lines if x.startswith('PROBLEM')][:3]} "
                                f"{lines[-1] if lines else ''}")
    for p in problems:
        log("PROBLEM:", p)
    log("RUNBOOK-RULES", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
