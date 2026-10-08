#!/usr/bin/env python3
"""run-dag2.py --prune-filter-set 74 (prune.py --filter-set 74) in a set-398 run: PRUNING.md 5.6.

Runs from e2e.py's scratch tree (the current scripts, the tree's binaries and the real checker).
PASS iff
  F1 on the (16,41) target in Mode 398 with --reach, --prune --prune-from 12 --prune-filter-only and
     --verify-stages, the default run and the run with --prune-filter-set 74 write the same level files
     byte for byte (every <n>-<m>.g6, .reach.g6, .keep.g6, .UNKNOWN.g6, .certs.jsonl, and every prune
     step's filter.jsonl), every prune manifest of the second says filter_set 74 and hashes both
     forbidden files, run-config.json and run-summary.json say prune_filter_set 74, and
     verify-chain.py --check accepts both directories;
  F2 a planted superset graph is still caught: a TEST-ONLY wrapper around udenum (passed with
     run-dag2.py --udenum; nothing in the production code knows about it) appends to a level-12 cell
     (12,m) one graph that contains one of GP-10's 324: it is taken from the level-12 keep files of a
     Mode 74 run of the same target (so it is canonical, 74-free, has no TU gadget and meets the reach
     bound: exactly what Mode 398 must never generate), and each of those facts is re-checked with
     udfilter and labelg before use. With --prune-filter-set 74 --verify-stages the run must stop at
     (12,m) in the stage verification; with the default filter set it must stop earlier, in the prune
     step, as a GENERATOR BUG. Either way no level above 12 is written;
  F3 refusals: --prune-filter-set 74 without --verify-stages, --prune-filter-set 398 in a set-74 run,
     and --prune-filter-set without --prune are refused before any work; prune.py --filter-set 398
     with --forbidden-set 74 is refused; verify-chain refuses a run-config.json recording
     prune_filter_set 74 without verify_stages;
  F4 the runbook's keys: U23_PRUNE_FILTER_SET=74 names the directories -pf74 (traced from the script's
     own KEY lines) and U23_PRUNE_FILTER_SET=398 with U23_FORBIDDEN_SET=74 exits 2.

usage: filterset.py [--jobs 2]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import e2e
from rhlib import DATA, REPO, decode_g6, encode_g6, log

LEVEL_RE = re.compile(r"^\d+-\d+(\.reach|\.keep|\.UNKNOWN)?\.g6$|^\d+-\d+\.certs\.jsonl$")
L10 = REPO / "research" / "gp-10" / "runs" / "B10-final-2026-09-25" / "L10.g6"
problems: list[str] = []


def udfilter(codes: list[str], fset: int) -> list[dict]:
    cmd = [str(e2e.TREE / "filter" / "udfilter"), *([] if fset == 74 else ["-s", "398"]),
           "-f", str(DATA / f"forbidden-{fset}.json"), "-t", str(DATA / "tu-gadgets.json")]
    p = subprocess.run(cmd, input="".join(c + "\n" for c in codes), text=True, capture_output=True, check=True)
    return [json.loads(x) for x in p.stdout.splitlines()]


def plant_graph(mode74_run: Path) -> tuple[int, str]:
    """A graph of a level-12 keep file of the Mode 74 (16,41) run that contains one of GP-10's 324: it
    is canonical, 74-free, has no TU gadget, meets the reach bound, and is exactly what Mode 398 must
    never generate (Mode 398 = Mode 74 minus containment, REPORT-398.md). Re-checked here with udfilter
    and labelg. Returns (m, graph6)."""
    table = json.loads((mode74_run / "reach.json").read_text())["table"]["12"]
    for m in sorted(table, key=int):
        keep = mode74_run / f"12-{m}.keep.g6"
        codes = [x for x in keep.read_text().split("\n") if x] if keep.is_file() else []
        for code, v398 in zip(codes, udfilter(codes, 398)):
            if v398["verdict"] == "forbidden" and v398["witness"]["index"] >= 74:
                v74 = udfilter([code], 74)[0]
                n, edges = decode_g6(code)
                degree = min(sum(1 for e in edges if v in e) for v in range(n))
                canon = e2e.canonical([code])[0] == code
                log(f"planted graph {code} (from the Mode 74 run's 12-{m}.keep.g6): 12 vertices, {len(edges)} edges, "
                    f"minimum degree {degree} (reach bound {table[m]}); set 74 {v74['verdict']}; set 398 forbidden "
                    f"member {v398['witness']['index']}; canonical {canon}")
                if v74["verdict"] == "pass" and degree >= table[m] and canon and len(edges) == int(m):
                    return int(m), code
    raise SystemExit("no level-12 graph of the Mode 74 run contains one of the 324")


WRAPPER = '''#!{python}
"""TEST ONLY (enum/test-rhombus/filterset.py): udenum, then one planted graph appended to the first shard of
the level ({n},{m}). Never used by any production path."""
import subprocess, sys
args = sys.argv[1:]
p = subprocess.run([{udenum!r}, *args])
def arg(name):
    return args[args.index(name) + 1] if name in args else None
if p.returncode == 0 and arg("--n") == "{n}" and arg("--m") == "{m}" and arg("--start") == "0" and "--parents" in args \\
        and "--filter" not in args and "--verify-parents" not in args:
    with open(arg("--output"), "a") as out:
        out.write({code!r} + "\\n")
sys.exit(p.returncode)
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    e2e.build_tree()
    shutil.copy2(e2e.UD / "enum" / "verify-chain.py", e2e.TREE / "enum" / "verify-chain.py")
    runs = e2e.RUNS
    runs.mkdir(parents=True, exist_ok=True)

    # F1
    base, pf = runs / "fs-16-41-default", runs / "fs-16-41-pf74"
    for out, extra in ((base, ()), (pf, ("--prune-filter-set", "74"))):
        shutil.rmtree(out, ignore_errors=True)
        code, wall, last = e2e.run_dag(out, (16, 41), 398, False, a.jobs, extra)
        log(f"F1 {out.name}: exit {code} after {wall:.0f} s")
        if code != 0:
            problems.append(f"F1 {out.name}: exit {code}: {last}")
    files = sorted(p.name for p in base.iterdir() if LEVEL_RE.match(p.name))
    same = [f for f in files if (pf / f).is_file() and (pf / f).read_bytes() == (base / f).read_bytes()]
    filters = sorted(p.relative_to(base) for p in base.glob("_prune/*/filter.jsonl"))
    fsame = [f for f in filters if (pf / f).read_bytes() == (base / f).read_bytes()]
    extra_files = sorted(p.name for p in pf.iterdir() if LEVEL_RE.match(p.name) and not (base / p.name).exists())
    log(f"F1 level files: {len(same)} of {len(files)} byte-identical (extra in the -pf74 run: {extra_files}); "
        f"filter.jsonl: {len(fsame)} of {len(filters)} identical")
    if len(same) != len(files) or extra_files or len(fsame) != len(filters) or not files:
        problems.append("F1: --prune-filter-set 74 changed a level file")
    manifests = sorted(pf.glob("*.prune.manifest.json"))
    bad = []
    for mpath in manifests:
        v = json.loads(mpath.read_text())
        hashes = set(v["inputs_sha256"].values())
        if v.get("filter_set") != 74 or e2e.sha256(DATA / "forbidden-74.json") not in hashes or \
                e2e.sha256(DATA / "forbidden-398.json") not in hashes or v.get("forbidden_set") != 398:
            bad.append(mpath.name)
    cfg = json.loads((pf / "run-config.json").read_text())
    summ = json.loads((pf / "run-summary.json").read_text())
    base_manifests = [p.name for p in base.glob("*.prune.manifest.json") if "filter_set" in json.loads(p.read_text())]
    log(f"F1 -pf74 prune manifests: {len(manifests)}, without filter_set 74 and both forbidden hashes: {bad}; "
        f"run-config prune_filter_set {cfg.get('prune_filter_set')}, run-summary {summ.get('prune_filter_set')}; "
        f"default run's manifests naming a filter_set: {base_manifests}")
    if bad or cfg.get("prune_filter_set") != 74 or summ.get("prune_filter_set") != 74 or base_manifests or not manifests:
        problems.append("F1: the filter set is not recorded as specified")
    for out in (base, pf):
        p = subprocess.run(["nice", "-n", "10", sys.executable, str(e2e.TREE / "enum" / "verify-chain.py"), str(out),
                            "--check"], capture_output=True, text=True, env=e2e.clean_env())
        lines = p.stdout.strip().splitlines()
        log(f"F1 verify-chain --check {out.name}: exit {p.returncode}: {lines[-1] if lines else p.stderr[-200:]}")
        if p.returncode != 0:
            problems.append(f"F1: verify-chain refused {out.name}: {[x for x in lines if x.startswith('PROBLEM')][:3]}")

    # F2
    mode74 = runs / "fs-16-41-mode74"
    shutil.rmtree(mode74, ignore_errors=True)
    rc, wall, last = e2e.run_dag(mode74, (16, 41), 74, False, a.jobs)
    log(f"F2 the Mode 74 (16,41) run the planted graph is taken from: exit {rc} after {wall:.0f} s")
    m12, code = plant_graph(mode74)
    wrapper = runs / f"udenum-plant-12-{m12}.py"
    wrapper.write_text(WRAPPER.format(python=sys.executable, udenum=str(e2e.TREE / "enum" / "udenum"), n=12, m=m12,
                                      code=code))
    wrapper.chmod(0o755)
    for label, extra, expect in (("-pf74", ("--prune-filter-set", "74"), f"STAGE VERIFICATION FAILED at (12,{m12})"),
                                 ("default", (), "GENERATOR BUG")):
        out = runs / f"fs-plant-{label.strip('-')}"
        shutil.rmtree(out, ignore_errors=True)
        rc, wall, last = e2e.run_dag(out, (16, 41), 398, False, a.jobs, (*extra, "--udenum", str(wrapper)),
                                     expect_ok=False)
        text = (out.parent / f"{out.name}.log").read_text()
        planted = code in (out / f"12-{m12}.g6").read_text() if (out / f"12-{m12}.g6").is_file() else False
        above = sorted(p.name for p in out.glob("1[3-6]-*.g6"))
        log(f"F2 planted run {label}: exit {rc} after {wall:.0f} s; the planted graph in 12-{m12}.g6: {planted}; "
            f"'{expect}' reported: {expect in text}; level files above 12: {above}; last line: {last[-160:]}")
        if rc != 2 or expect not in text or not planted or above:
            problems.append(f"F2 {label}: the planted graph was not caught as expected")

    # F3
    red = runs / "fs-red"
    tree_rd = str(e2e.TREE / "enum" / "run-dag2.py")
    for label, argv, expect in (
            ("--prune-filter-set 74 without --verify-stages",
             ["--forbidden-set", "398", "--reach", "--prune", "--prune-filter-set", "74"], "needs --verify-stages"),
            ("--prune-filter-set 398 in a set-74 run",
             ["--reach", "--prune", "--prune-filter-set", "398", "--verify-stages"], "generator bug"),
            ("--prune-filter-set without --prune",
             ["--forbidden-set", "398", "--reach", "--prune-filter-set", "74", "--verify-stages"], "needs --prune")):
        shutil.rmtree(red, ignore_errors=True)
        p = subprocess.run([sys.executable, tree_rd, "--target-n", "16", "--target-m", "41", "--output-dir", str(red),
                            *argv], capture_output=True, text=True, env=e2e.clean_env())
        log(f"F3 {label}: exit {p.returncode}: {p.stderr.strip()[-120:]}; directory made {red.exists()}")
        if p.returncode != 2 or expect not in p.stderr or red.exists():
            problems.append(f"F3: {label} was not refused before any work")
    level = runs / "fs-red-prune" / "16-41.reach.g6"
    level.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base / "16-41.reach.g6", level)
    p = subprocess.run([sys.executable, str(e2e.TREE / "enum" / "prune.py"), "--level", str(level), "--target-n", "16",
                        "--target-m", "41", "--filter-only", "--filter-set", "398"], capture_output=True, text=True,
                       env=e2e.clean_env())
    log(f"F3 prune.py --filter-set 398 --forbidden-set 74: exit {p.returncode}: {p.stderr.strip()[-120:]}")
    if p.returncode != 2 or "filter set" not in p.stderr:
        problems.append("F3: prune.py --filter-set 398 in a set-74 step was not refused")
    cfg_path = pf / "run-config.json"
    original = cfg_path.read_bytes()
    try:
        v = json.loads(original)
        v.pop("verify_stages", None)
        cfg_path.write_text(json.dumps(v, indent=2) + "\n")
        p = subprocess.run([sys.executable, str(e2e.TREE / "enum" / "verify-chain.py"), str(pf)], capture_output=True,
                           text=True, env=e2e.clean_env())
        lines = p.stdout.strip().splitlines()
        hit = [x for x in lines if "prune_filter_set 74 without verify_stages" in x]
        log(f"F3 verify-chain on -pf74 with verify_stages removed from run-config.json: exit {p.returncode}; "
            f"{(hit or lines[-1:] or [''])[0][:150]}")
        if p.returncode == 0 or not hit:
            problems.append("F3: verify-chain accepted prune_filter_set 74 without verify_stages")
    finally:
        cfg_path.write_bytes(original)

    # F4
    runbook = REPO / "coordination" / "cloud-workers" / "u23-slice.sh"
    text = runbook.read_text()
    key_lines = [x for x in text.splitlines() if x.startswith(("RHOMBUS=", "PFSET=", "KEY=", "[ \"$RHOMBUS\" = 1 ] && KEY",
                                                              "[ \"$PFSET\" = \"$FSET\" ] || KEY", "case \"$PFSET\"",
                                                              "[ \"$FSET\" = 74 ] && [ \"$PFSET\""))]
    trace = runs / "keytrace.sh"
    trace.write_text("#!/usr/bin/env bash\nset -euo pipefail\nFSET=$1; SLICE_LEVEL=$2\n" + "\n".join(key_lines) +
                     "\necho \"dag-23-65${KEY}-s0of1920\"\n")
    results = {}
    for fset, pfs in (("398", ""), ("398", "74"), ("398", "398"), ("74", "74"), ("74", "398")):
        env = e2e.clean_env()
        env.pop("U23_PRUNE_FILTER_SET", None)
        env.pop("U23_RHOMBUS", None)
        if pfs:
            env["U23_PRUNE_FILTER_SET"] = pfs
        p = subprocess.run(["bash", str(trace), fset, "13"], capture_output=True, text=True, env=env)
        results[(fset, pfs)] = (p.returncode, p.stdout.strip() or p.stderr.strip())
    log(f"F4 runbook directory keys (set, U23_PRUNE_FILTER_SET) -> (exit, name): {results}")
    if results[("398", "")] != (0, "dag-23-65-s0of1920") or results[("398", "74")] != (0, "dag-23-65-pf74-s0of1920") \
            or results[("398", "398")] != (0, "dag-23-65-s0of1920") or results[("74", "398")][0] != 2:
        problems.append("F4: the runbook's directory keys for the filter set are wrong")

    for p in problems:
        log("PROBLEM:", p)
    log("FILTERSET", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
