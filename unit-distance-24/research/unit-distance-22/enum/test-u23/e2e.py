#!/usr/bin/env python3
"""End to end: run-dag2.py in Mode 398 against Mode 74 on a small target, with the full reach and
prune path of the u(23) runbook (--reach, --prune --prune-from 12 --prune-filter-only,
--verify-stages).

Runs (all --jobs 1, nice 15):
  base74   the LANDED pipeline (git HEAD 952ae252d: run-dag2.py, prune.py, udcheck.py, udenum
           a99b130a, udfilter b0947a10), from a scratch tree (--baseline-tree), Mode 74
  new74    this tree, Mode 74, with --verify-stages
  new398   this tree, --forbidden-set 398, with --verify-stages

A  Mode 74 is unchanged: every level file of base74 (<n>-<m>.g6, .reach.g6, .keep.g6,
   .UNKNOWN.g6, .certs.jsonl) exists in new74 with the same bytes, and no other exists.
B  Mode 398 = Mode 74 minus containment, at every level and every stage: for each file X of
   new74, R = the records of X that contain one of the 398, decided by GP-10's matcher widened
   to 31-vertex hosts (enum/test-398/matcher32.c) chained over chunks of <= 128 patterns of
   data/forbidden-398.g6; E = X minus R, in order. PASS iff the new398 file equals E byte for byte
   (for certs: the new74 certificate lines of the graphs in E). Every matcher witness is
   re-verified in Python; the matcher must never hit one of the first 74 (the files are 74-free).
   The WRONG check, set(new398) <= set(new74), is shown passing on an emptied and on a one-short
   Mode 398 file (W1, W2) while equality fails on both; and E computed with the 74 only must
   differ from new398 wherever R is non-empty (W3: the expected side is sensitive too).
C  AMP's known extremal graphs at the target (sources/amp/anc/graph6.txt) are all in the target's
   keep file in both modes (L1, L2 and L4 of PRUNING.md say they must be).
D  verify-chain.py --check accepts new74 (udcheck.py) and new398 (udcheck398.py), and the landed
   base74 directory too. Red: a copy of new398 with one line dropped from a keep file, and one
   with a tu witness in a certs file made non-injective, must both fail.
E  The failure mode of REPORT-398.md 7.1: a Mode 398 run whose seeds were filtered with set 74
   (--mutation-seeds-74, TEST ONLY) must stop at level 10 in its stage verification (E1), and
   without --verify-stages must still stop at the first pruned level with a GENERATOR BUG (E2).
F  --resume in Mode 398 does not accept set-74 files: new74's levels <= 11 are COPIED into a fresh
   directory (never hard-linked: a regenerated file would be written through the link) and a
   Mode 398 run with --resume regenerates them; its files must equal new398's byte for byte.
G  The stage verification split over --jobs ranges: a copy of new398 without its verification
   manifests, resumed with --jobs 2, re-verifies every level in min(2, records) ranges that tile
   each stage file, regenerating nothing. Red: a stage file whose last record contains one of the
   324 fails, naming the range [records/2, records).
(D's red controls tamper with new398 in place and restore it byte for byte: its manifests hold
absolute paths, so a copied directory would fail verify-chain for the wrong reason.)

usage: e2e.py --target-n N --target-m M --baseline-tree DIR [--reuse-base] [--skip-runs] [--skip-e] [--skip-f]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from u23lib import (F398, F398_G6, KNOWN, MATHS_PY, RUN_DAG2, SCRATCH, UD, canonical, decode_g6,
                    g6_lines, load_run_dag2, log, run_matcher, sha256, witness_ok, write_lines)

problems: list[str] = []
LEVEL_RE = re.compile(r"^(\d+)-(\d+)(\.reach|\.keep|\.UNKNOWN)?\.g6$|^(\d+)-(\d+)\.certs\.jsonl$")
PATTERNS = [decode_g6(x) for x in g6_lines(F398_G6)]


def run_dag(script: Path, out: Path, n: int, m: int, *extra: str, expect_ok: bool = True,
            log_name: str = "run", jobs: int = 1) -> tuple[int, str, float]:
    cmd = ["nice", "-n", "15", sys.executable, str(script), "--target-n", str(n), "--target-m", str(m),
           "--output-dir", str(out), "--jobs", str(jobs), "--reach", "--prune", "--prune-from", "12",
           "--prune-filter-only", "--prune-python", str(MATHS_PY), *extra]
    start = time.monotonic()
    with (out.parent / f"{log_name}.log").open("w") as logf:
        p = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT)
    wall = time.monotonic() - start
    tail = (out.parent / f"{log_name}.log").read_text().strip().splitlines()
    msg = tail[-1] if tail else ""
    if expect_ok and p.returncode != 0:
        problems.append(f"run {out.name}: exit {p.returncode}: {msg}")
    return p.returncode, msg, wall


def level_files(d: Path) -> dict[str, Path]:
    return {p.name: p for p in d.iterdir() if p.is_file() and LEVEL_RE.match(p.name)}


def part_a(base: Path, new: Path) -> None:
    fb, fn = level_files(base), level_files(new)
    missing = sorted(set(fb) - set(fn))
    extra = sorted(set(fn) - set(fb))
    differ = sorted(name for name in set(fb) & set(fn) if fb[name].read_bytes() != fn[name].read_bytes())
    if missing or extra or differ:
        problems.append(f"A: new74 vs base74: missing {missing[:5]}, extra {extra[:5]}, differ {differ[:5]}")
    log(f"A Mode 74 unchanged: {len(fb)} level files of the landed pipeline, {len(set(fb) & set(fn)) - len(differ)} "
        f"byte-identical in new74; missing {len(missing)}, extra {len(extra)}, different {len(differ)}")


def matcher_removed(path: Path, work: Path) -> dict[bytes, tuple[int, list[int]]]:
    removed = run_matcher(F398_G6, path, work)["removed"]
    for host, (idx, mp) in removed.items():
        _, pedges = PATTERNS[idx]
        if not witness_ok(host, sorted(pedges), mp):
            problems.append(f"B: matcher witness does not verify: {host.decode()} member {idx}")
        if idx < 74:
            problems.append(f"B: matcher found one of the 74 in a 74-free file: {host.decode()} member {idx}")
    return removed


def part_b(new74: Path, new398: Path, work: Path) -> dict:
    f74 = level_files(new74)
    f398 = level_files(new398)
    table = {}
    wrong_demo_done = False
    only398 = sorted(set(f398) - set(f74))
    if only398:
        problems.append(f"B: Mode 398 wrote level files Mode 74 did not: {only398[:5]}")
    levels = sorted({(int(LEVEL_RE.match(k).group(1) or LEVEL_RE.match(k).group(4)),
                      int(LEVEL_RE.match(k).group(2) or LEVEL_RE.match(k).group(5))) for k in f74})
    for n, m in levels:
        full = new74 / f"{n}-{m}.g6"
        removed = matcher_removed(full, work / f"match-{n}-{m}")
        row = {}
        for suffix in (".g6", ".reach.g6", ".keep.g6", ".UNKNOWN.g6", ".certs.jsonl"):
            name = f"{n}-{m}{suffix}"
            if name not in f74:
                continue
            p398 = new398 / name
            if suffix == ".certs.jsonl":
                lines74 = [x for x in f74[name].read_bytes().split(b"\n") if x]
                codes = [json.loads(x)["g6"].encode() for x in lines74]
                expected = [line for line, code in zip(lines74, codes) if code not in removed]
                r = len(lines74) - len(expected)
            else:
                lines74 = g6_lines(f74[name])
                expected = [x for x in lines74 if x not in removed]
                r = len(lines74) - len(expected)
            got = [x for x in p398.read_bytes().split(b"\n") if x] if p398.is_file() else None
            ok = got is not None and got == expected
            if got is not None and not p398.read_bytes().endswith(b"\n") and got:
                ok = False
            if not ok:
                problems.append(f"B: {name}: Mode 398 is not Mode 74 minus containment "
                                f"({len(lines74)} - {r} = {len(expected)} expected, "
                                f"{'missing file' if got is None else len(got)} written)")
            row[suffix] = (len(lines74), r, len(expected), None if got is None else len(got), ok)
            # the WRONG check, demonstrated once on the largest non-empty full file with R non-empty
            if suffix == ".g6" and ok and r and not wrong_demo_done and len(expected) >= 2:
                wrong_demo_done = True
                s74 = set(lines74)
                w1 = []
                w2 = expected[:-1]
                w1_subset, w2_subset = set(w1) <= s74, set(w2) <= s74
                w1_equal, w2_equal = w1 == expected, w2 == expected
                e74only = [x for x in lines74]      # the expected side computed with the 74 only
                log(f"B WRONG-check demo on {name}: W1 empty output: subset check "
                    f"{'PASSES' if w1_subset else 'fails'}, equality {'passes' if w1_equal else 'FAILS'}; "
                    f"W2 one record dropped: subset {'PASSES' if w2_subset else 'fails'}, equality "
                    f"{'passes' if w2_equal else 'FAILS'}; W3 expected side with the 74 only: "
                    f"{len(e74only)} records vs {len(expected)} written, equality "
                    f"{'passes' if e74only == got else 'FAILS'}")
                if not (w1_subset and w2_subset and not w1_equal and not w2_equal and e74only != got):
                    problems.append("B: the WRONG-check demonstration did not behave as stated")
        table[(n, m)] = row
    for (n, m), row in table.items():
        cells = []
        for suffix, (a, r, e, g, ok) in row.items():
            cells.append(f"{suffix} {a}-{r}={e}:{g}{'' if ok else ' FAIL'}")
        log(f"B {n}-{m}: " + "; ".join(cells))
    if not wrong_demo_done:
        problems.append("B: no level had graphs containing one of the 324, so the WRONG-check demo did not run")
    return table


def part_c(new74: Path, new398: Path, n: int, m: int) -> None:
    known = []
    for line in g6_lines(KNOWN):
        vn, edges = decode_g6(line)
        if (vn, len(edges)) == (n, m):
            known.append(line)
    known = canonical(known)
    for d, label in ((new74, "new74"), (new398, "new398")):
        keep = set(g6_lines(d / f"{n}-{m}.keep.g6"))
        present = sum(1 for x in known if x in keep)
        log(f"C {label}: {present} of AMP's {len(known)} known ({n},{m}) graphs in {n}-{m}.keep.g6 "
            f"({len(keep)} graphs kept)")
        if present != len(known) or not known:
            problems.append(f"C {label}: {present} of {len(known)} known graphs present")


def verify_chain(d: Path, expect_ok: bool, label: str, needle: str | None = None) -> None:
    p = subprocess.run(["nice", "-n", "15", sys.executable, str(UD / "enum" / "verify-chain.py"), str(d), "--check"],
                       capture_output=True, text=True)
    out = p.stdout.strip().splitlines()
    summary = out[0] if out else ""
    verdict = out[-1] if out else p.stderr.strip()
    found = [x for x in out if x.startswith("PROBLEM") and (needle is None or needle in x)]
    ok = (p.returncode == 0 and verdict == "CHAIN OK") if expect_ok else \
        (p.returncode != 0 and "FAIL" in verdict and bool(found))
    log(f"D verify-chain {label}: exit {p.returncode}: {verdict}; " +
        (summary[:260] if expect_ok else (found[0][:200] if found else "the expected problem was NOT reported")))
    if not ok:
        problems.append(f"D verify-chain {label}: exit {p.returncode}: {verdict} "
                        f"{[x for x in out if x.startswith('PROBLEM')][:3]}")


def tampered(path: Path, new_bytes: bytes, label: str, run: Path, needle: str) -> None:
    """Replace a file of the run directory in place (manifests hold absolute paths, so a copied
    directory would fail for the wrong reason), run verify-chain, which must report a problem
    containing `needle`, restore, and check the bytes."""
    original = path.read_bytes()
    digest = sha256(path)
    try:
        path.write_bytes(new_bytes)
        verify_chain(run, False, label, needle)
    finally:
        path.write_bytes(original)
    if sha256(path) != digest:
        problems.append(f"D: {path} was not restored")


def part_d(base74: Path, new74: Path, new398: Path, work: Path, n: int, m: int) -> None:
    verify_chain(base74, True, "base74 (landed directory, new verify-chain)")
    verify_chain(new74, True, "new74")
    verify_chain(new398, True, "new398")
    # red 1: a keep file one line short
    victim = next(p for p in sorted(new398.glob("*.keep.g6")) if len(g6_lines(p)) >= 2)
    tampered(victim, b"".join(x + b"\n" for x in g6_lines(victim)[:-1]), f"red: {victim.name} one line short",
             new398, "is not the embedded and unknown records in order")
    # red 2: a tu witness made non-injective
    for certs in sorted(new398.glob("*.certs.jsonl")):
        lines = certs.read_text().splitlines()
        hit = next((i for i, line in enumerate(lines) if json.loads(line)["verdict"] == "tu"), None)
        if hit is None:
            continue
        rec = json.loads(lines[hit])
        rec["witness"]["map"][1] = rec["witness"]["map"][0]
        lines[hit] = json.dumps(rec, separators=(",", ":"), sort_keys=True)
        tampered(certs, "".join(x + "\n" for x in lines).encode(),
                 f"red: a tu witness in {certs.name} made non-injective", new398, "udcheck did not accept")
        break
    # red 3: reach.json with u-bar(16) lowered by one and the table left as it was
    reach = new398 / "reach.json"
    value = json.loads(reach.read_text())
    value["ubar"]["16"] -= 1
    tampered(reach, (json.dumps(value, indent=2) + "\n").encode(), "red: reach.json u-bar(16) lowered without "
             "a recorded override", new398, "is not the built-in")
    # red 4: a stage file changed after its verification (its verify manifest no longer covers it)
    stage = next(p for p in sorted(new398.glob("10-*.reach.g6")) if len(g6_lines(p)) >= 2)
    tampered(stage, b"".join(x + b"\n" for x in g6_lines(stage)[1:]), f"red: {stage.name} changed after its "
             "stage verification", new398, "stage verification manifest does not cover")


def part_e(work: Path, n: int, m: int, table: dict) -> None:
    # With set-74 seeds the level-10 stage files are exactly new74's, so the verification must stop
    # at the first level-10 cell (in run order) whose new74 stage file has a graph with one of the
    # 324 (part B counted them with the independent matcher).
    stage_suffix = ".reach.g6"
    first = next(((ln, lm) for (ln, lm), row in sorted(table.items())
                  if ln == 10 and row.get(stage_suffix, (0, 0))[1] > 0), None)
    e1 = work / "mut-seeds-verify"
    shutil.rmtree(e1, ignore_errors=True)
    code, msg, wall = run_dag(RUN_DAG2, e1, n, m, "--forbidden-set", "398", "--verify-stages",
                              "--mutation-seeds-74", expect_ok=False, log_name="mut-seeds-verify")
    want = f"STAGE VERIFICATION FAILED at ({first[0]},{first[1]})" if first else "STAGE VERIFICATION FAILED at ("
    ok = code == 2 and want in msg
    log(f"E1 Mode 398 with set-74 seeds and --verify-stages: exit {code} after {wall:.0f} s (expected to stop at "
        f"{first}, the first level-10 stage file holding one of the 324): {msg[:230]}")
    if not ok:
        problems.append(f"E1: the stage verification did not stop the set-74 seeds at {first}: {msg}")
    e2 = work / "mut-seeds-noverify"
    shutil.rmtree(e2, ignore_errors=True)
    code, msg, wall = run_dag(RUN_DAG2, e2, n, m, "--forbidden-set", "398", "--mutation-seeds-74",
                              expect_ok=False, log_name="mut-seeds-noverify")
    text = (work / "mut-seeds-noverify.log").read_text()
    ok = code == 2 and "GENERATOR BUG" in text
    levels = sorted({p.name.split(".")[0] for p in e2.glob("*.prune.manifest.json")})
    log(f"E2 the same without --verify-stages: exit {code} after {wall:.0f} s; GENERATOR BUG reported: "
        f"{'GENERATOR BUG' in text}; prune manifests written before it stopped: {levels}")
    if not ok:
        problems.append(f"E2: the prune step did not stop the set-74-seeded tree: {msg}")


def part_f(new74: Path, new398: Path, work: Path, n: int, m: int) -> None:
    f = work / "resume-over-74"
    shutil.rmtree(f, ignore_errors=True)
    f.mkdir(parents=True)
    copied = 0
    for p in new74.iterdir():
        mm = re.match(r"^(\d+)-\d+\.", p.name)
        if p.is_file() and (p.name == "reach.json" or (mm and int(mm.group(1)) <= 11)):
            shutil.copy2(p, f / p.name)
            copied += 1
    code, msg, wall = run_dag(RUN_DAG2, f, n, m, "--forbidden-set", "398", "--verify-stages", "--resume",
                              log_name="resume-over-74")
    summary = json.loads((f / "run-summary.json").read_text()) if (f / "run-summary.json").is_file() else {}
    resumed = [(l["n"], l["m"]) for l in summary.get("levels", []) if l.get("resumed")]
    same = sorted(name for name, p in level_files(new398).items()
                  if (f / name).is_file() and (f / name).read_bytes() == p.read_bytes())
    differ = sorted(set(level_files(new398)) ^ set(level_files(f)) |
                    {name for name in level_files(new398) if name not in same})
    log(f"F Mode 398 --resume over {copied} copied set-74 files (levels <= 11): exit {code} after {wall:.0f} s; "
        f"levels accepted as resumed: {resumed}; files equal to new398: {len(same)}, different: {len(differ)}")
    if code != 0 or resumed or differ:
        problems.append(f"F: resume over set-74 files: exit {code}, resumed {resumed[:5]}, differ {differ[:5]}")


def part_g(new398: Path, work: Path, n: int, m: int) -> None:
    """The stage verification split over --jobs ranges: on a copy of new398 without its
    verification manifests, --resume --jobs 2 re-verifies every level (and nothing else); each
    manifest must hold min(2, records) ranges tiling the stage file. Red: a stage file whose LAST
    record contains one of the 324 fails in the range that holds it."""
    g = work / "verify-jobs2"
    shutil.rmtree(g, ignore_errors=True)
    shutil.copytree(new398, g, symlinks=True)
    shutil.rmtree(g / "_verify", ignore_errors=True)
    for p in g.glob("*.verify.manifest.json"):
        p.unlink()
    code, msg, wall = run_dag(RUN_DAG2, g, n, m, "--forbidden-set", "398", "--verify-stages", "--resume",
                              log_name="verify-jobs2", jobs=2)
    summary = json.loads((g / "run-summary.json").read_text())
    not_resumed = [(l["n"], l["m"]) for l in summary["levels"]
                   if l["n"] >= 10 and not l.get("resumed")]
    bad = []
    verified = 0
    for l in summary["levels"]:
        if l["n"] < 10:
            continue
        vm = json.loads((g / f"{l['n']}-{l['m']}.verify.manifest.json").read_text())
        ranges = [tuple(p["range"]) for p in vm["parts"]]
        want = min(2, vm["records"]) or 1
        if (len(ranges) != want or ranges[0][0] != 0 or ranges[-1][1] != vm["records"] or
                any(ranges[i][1] != ranges[i + 1][0] for i in range(len(ranges) - 1)) or
                vm["parents_seen"] != vm["records"]):
            bad.append((l["n"], l["m"], ranges, vm["records"]))
        verified += 1
    same = all((g / name).read_bytes() == p.read_bytes() for name, p in level_files(new398).items())
    log(f"G --resume --jobs 2 re-verification: exit {code} after {wall:.0f} s; levels regenerated instead of resumed: "
        f"{not_resumed}; {verified} verification manifests, {len(bad)} not tiled by min(2, records) ranges; "
        f"level files unchanged: {same}")
    if code != 0 or not_resumed or bad or not same:
        problems.append(f"G: exit {code}, regenerated {not_resumed[:5]}, bad ranges {bad[:3]}, same {same}")
    # red: the last record of a stage file contains one of the 324
    rd = load_run_dag2()
    red = work / "verify-red"
    shutil.rmtree(red, ignore_errors=True)
    red.mkdir(parents=True)
    source = new398 / "12-22.keep.g6"
    bad_graph = next(x for x in g6_lines(work / "new74" / "12-22.keep.g6")
                     if x not in set(g6_lines(source)))
    write_lines(red / "12-22.g6", g6_lines(source) + [bad_graph])
    args = argparse.Namespace(prune=False, reach=False, slice_level=None, resume=False, jobs=2,
                              forbidden_set=398, forbidden=F398, udenum=UD / "enum" / "udenum")
    entry: dict = {}
    try:
        rd.verify_stage(args, red, 12, 22, entry)
        outcome = "ACCEPTED"
    except RuntimeError as error:
        outcome = str(error)
    total = len(g6_lines(red / "12-22.g6"))
    ok = "STAGE VERIFICATION FAILED at (12,22)" in outcome and f"[{total // 2},{total})" in outcome
    log(f"G red: {total} records, the last one with a 324-member, verified in 2 ranges: {outcome[:200]}")
    if not ok:
        problems.append(f"G red: the failing range was not reported: {outcome[:200]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-n", type=int, required=True)
    ap.add_argument("--target-m", type=int, required=True)
    ap.add_argument("--baseline-tree", type=Path, required=True,
                    help="a scratch copy of research/unit-distance-22 at the landed commit")
    ap.add_argument("--skip-runs", action="store_true", help="reuse finished base74/new74/new398 directories")
    ap.add_argument("--reuse-base", action="store_true", help="reuse a finished base74 directory (the landed code)")
    ap.add_argument("--skip-e", action="store_true")
    ap.add_argument("--skip-f", action="store_true")
    a = ap.parse_args()
    n, m = a.target_n, a.target_m
    work = SCRATCH / f"e2e-{n}-{m}"
    work.mkdir(parents=True, exist_ok=True)
    base74, new74, new398 = work / "base74", work / "new74", work / "new398"
    base_script = a.baseline_tree / "research" / "unit-distance-22" / "enum" / "run-dag2.py"
    log(f"e2e target ({n},{m}); baseline {base_script} ({sha256(base_script)[:8]}); new run-dag2.py "
        f"{sha256(RUN_DAG2)[:8]}")
    if not a.skip_runs:
        for d, script, extra, label in ((base74, base_script, (), "base74"),
                                        (new74, RUN_DAG2, ("--verify-stages",), "new74"),
                                        (new398, RUN_DAG2, ("--forbidden-set", "398", "--verify-stages"), "new398")):
            if label == "base74" and a.reuse_base and (d / "run-summary.json").is_file():
                log(f"run {label}: reused (completed_through_n "
                    f"{json.loads((d / 'run-summary.json').read_text())['completed_through_n']})")
                continue
            shutil.rmtree(d, ignore_errors=True)
            code, msg, wall = run_dag(script, d, n, m, *extra, log_name=label)
            log(f"run {label}: exit {code} after {wall:.0f} s")
    part_a(base74, new74)
    table = part_b(new74, new398, work)
    part_c(new74, new398, n, m)
    part_d(base74, new74, new398, work, n, m)
    if not a.skip_e:
        part_e(work, n, m, table)
    if not a.skip_f:
        part_f(new74, new398, work, n, m)
    part_g(new398, work, n, m)
    for p in problems:
        log("PROBLEM:", p)
    log("E2E", f"({n},{m})", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
