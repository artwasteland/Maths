#!/usr/bin/env python3
"""Mode 398 identity: the optimized udenum against the CURRENT Mode 398 binary, byte for byte.

Reference: test-398/base398/udenum, built from the unmodified source of 952ae252d (sha256 pinned
below; it must rebuild to a99b130a..., the binary REPORT-398 validated).  Candidates: the new
enum/udenum, and two test builds of the new source that force each oracle of the restricted path
(RESTRICTED_SWITCH_CANDIDATES=1: switch to the anchored family as soon as the parent is known free;
=4000000000: never switch, test every candidate child), and one that runs the pattern path's
uncovered-set tracking and direct tests on parents of every order (UNCOVERED_MIN_ORDER=1; the
production build does so from 15 vertices).  Each run is compared with the reference
on the exit status, the output BYTES and all nine counters (speed398lib.compare_runs).  Comparing
child counts or child sets instead would be the wrong check: it passes outputs that differ in
order, or that differ in which graphs have a given count (speed398-red.py shows it passing a
broken output).

Inputs, per cell (n, m):
  p398   the 398-free parents (what a Mode 398 tree feeds udenum): P74 minus the records that contain
         one of the 398, in order.  From semantics-398's work directory when given (--p398-dir,
         the exact files REPORT-398 4.2 used), otherwise computed with the REFERENCE binary's
         --filter per edge count.
  p74    the unfiltered parents, which include parents containing one of the 324: this drives the
         restricted path through its "parent not free" branch.
each with and without --verify-parents (on p74, both binaries must refuse identically), and with
--mutations the p398 inputs also under the two test-only mutation flags: --mutation-drop-first-badset
removes the first set of each bad family, so identical outputs (or identical aborts, usually at the
first parent where that set matters) show that the family's FIRST set is the same.  That is all of
the order the output can show; speed398-family.py compares every family in order.

Cells:
  dag    the 21 cells of REPORT-398 4.2 (out-22/dag-22-61 11-19..12-27, out-sup/dag-18-46 15-34..18-46)
  final  the (21,56) -> (22,61) cell of every one of the 48 u(22) slices, separately
  deep   (with --speed-work) the sampled parents of speed.py at levels 12..21, all and 398-free
  extra  (with --extra) the other parent files of the two DAGs (out-22 11-17, 11-18, 12-22; out-sup
         11-19..14-33)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from speed398lib import (BASE398_SHA256, BASE398_UDENUM, ENUM, NEW_SOURCE, NEW_UDENUM, SCRATCH, build_variant,
                         compare_runs, g6_lines, g6_order_size, run_udenum, sha256, write_lines)

OUT22 = ENUM / "out-22" / "dag-22-61"
SUP = ENUM / "out-sup" / "dag-18-46"
DAG_CELLS = ((OUT22, ["11-19", "11-20", "11-21", "11-22", "11-23", "12-23", "12-24", "12-25", "12-26", "12-27"]),
             (SUP, ["15-34", "15-35", "15-36", "15-37", "16-38", "16-39", "16-40", "16-41", "17-42", "17-43", "18-46"]))
EXTRA_CELLS = ((OUT22, ["11-17", "11-18", "12-22"]),
               (SUP, ["11-19", "11-20", "11-21", "11-22", "11-23", "12-22", "12-23", "12-24", "12-25", "12-26",
                      "12-27", "13-27", "13-28", "13-29", "13-30", "14-31", "14-32", "14-33"]))


def filter_398(parents: list[bytes], n: int, work: Path, tag: str) -> list[bytes]:
    """The 398-free records of `parents`, in order, decided by the REFERENCE binary's --filter."""
    by_m: dict[int, list[bytes]] = {}
    for g in parents:
        by_m.setdefault(g6_order_size(g)[1], []).append(g)
    keep: set[bytes] = set()
    for m, gs in sorted(by_m.items()):
        src = work / f"{tag}-filter-in-{m}.g6"
        write_lines(src, gs)
        r = run_udenum(BASE398_UDENUM, src, n, m, work / f"{tag}-filter-out-{m}.g6", extra=["--filter"])
        if r["returncode"] != 0:
            raise SystemExit(f"reference --filter failed: {r['stderr_tail']}")
        kept = g6_lines(r["output"])
        if not set(kept) <= set(gs):
            raise SystemExit("reference --filter rewrote a parent: the parents are not canonical")
        keep |= set(kept)
    return [g for g in parents if g in keep]


def cells(args, work: Path, wanted: set[str]) -> list[dict]:
    out = []
    groups = [("dag", DAG_CELLS)] + ([("extra", EXTRA_CELLS)] if args.extra else [])
    for group, dirs in groups:
        if group not in wanted:
            continue
        for d, names in dirs:
            for name in names:
                n, m = map(int, name.split("-"))
                tag = f"{d.name}_{name}"
                p74 = d / "_parents" / f"{name}.g6"
                p398 = args.p398_dir / f"{tag}.p398.g6" if args.p398_dir else None
                if p398 is None or not p398.exists():
                    p398 = work / f"{tag}.p398.g6"
                    write_lines(p398, filter_398(g6_lines(p74), n - 1, work, tag))
                out.append({"group": group, "cell": tag, "n": n, "m": m, "inputs": {"p398": p398, "p74": p74}})
    if "dag" in wanted and args.p398_dir and (args.p398_dir / "u22-all-48-slices_22-61.p398.g6").exists():
        # 4.2's final cell exactly as it was run there: the union of the 48 slices as one cell
        out.append({"group": "dag", "cell": "u22-all-48-slices/22-61", "n": 22, "m": 61,
                    "inputs": {"p398": args.p398_dir / "u22-all-48-slices_22-61.p398.g6",
                               "p74": args.p398_dir / "u22-final.parents.g6"}})
    if "final" in wanted and args.slices:
        for s in range(48):
            sd = args.slices / f"s{s}of48"
            raw = sd / "21-56.keep.g6"
            free = work / f"final-s{s}.p398.g6"
            write_lines(free, filter_398(g6_lines(raw), 21, work, f"final-s{s}"))
            out.append({"group": "final", "cell": f"u22-s{s}of48/22-61", "n": 22, "m": 61,
                        "inputs": {"p398": free, "p74": raw}})
    if "deep" in wanted and args.speed_work:
        for L in range(12, 22):
            for f in sorted(args.speed_work.glob(f"measure-{L}-*.all.g6"), key=lambda p: int(p.name.split("-")[2].split(".")[0])):
                M = int(f.name.split("-")[2].split(".")[0])
                out.append({"group": "deep", "cell": f"speed-L{L}/{L + 1}-{M}", "n": L + 1, "m": M,
                            "inputs": {"p398": f.with_name(f"measure-{L}-{M}.free.g6"), "p74": f}})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, default=None, help="results/u22 of the worker branches (s0of48..)")
    ap.add_argument("--p398-dir", type=Path, default=None, help="semantics-398.py's work directory (the 4.2 P398 files)")
    ap.add_argument("--speed-work", type=Path, default=None, help="speed.py's work directory (measure-L-M.{all,free}.g6)")
    ap.add_argument("--extra", action="store_true", help="also the other parent files of the two DAGs")
    ap.add_argument("--no-variants", action="store_true", help="compare only the enum/udenum binary")
    ap.add_argument("--mutations", action="store_true",
                    help="also run the p398 inputs with the test-only --mutation-drop-first-badset (it drops "
                         "the FIRST set of the bad family, so it exposes the family's order) and "
                         "--mutation-no-child-orbit")
    ap.add_argument("--groups", default="dag,final,deep,extra")
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-identity")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-identity.json")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    log = sys.stdout
    if sha256(BASE398_UDENUM) != BASE398_SHA256:
        print(f"reference {BASE398_UDENUM} is not the pinned Mode 398 binary {BASE398_SHA256}")
        return 2
    binaries = {"new": NEW_UDENUM}
    if not a.no_variants:
        binaries["new-K1"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-K1", ["RESTRICTED_SWITCH_CANDIDATES=1"])
        binaries["new-Kinf"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-Kinf",
                                             ["RESTRICTED_SWITCH_CANDIDATES=4000000000"])
        binaries["new-U1"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-U1", ["UNCOVERED_MIN_ORDER=1"])
    print(f"reference {BASE398_UDENUM} {BASE398_SHA256}", file=log)
    for k, b in binaries.items():
        print(f"candidate {k}: {b} {sha256(b)}", file=log)
    groups = set(a.groups.split(","))
    results = []
    t0 = time.monotonic()
    modes = [("", []), ("verify", ["--verify-parents"])]
    if a.mutations:
        modes += [("drop-first", ["--mutation-drop-first-badset"]), ("no-orbit", ["--mutation-no-child-orbit"])]
    for c in cells(a, w, groups):
        for inp, parents in c["inputs"].items():
            for mode, extra in modes:
                if mode in ("drop-first", "no-orbit") and inp != "p398":
                    continue
                verify = mode == "verify"
                tag = f"{c['cell'].replace('/', '_')}.{inp}{'.' + mode if mode else ''}"
                ref = run_udenum(BASE398_UDENUM, parents, c["n"], c["m"], w / "out" / f"{tag}.base.g6", extra=extra)
                rec = {"group": c["group"], "cell": c["cell"], "input": inp, "mode": mode or "plain",
                       "verify_parents": verify,
                       "parents_file": str(parents), "parents": len(g6_lines(parents)),
                       "reference": {"returncode": ref["returncode"], "cpu": ref["cpu"],
                                     "stats": ref["stats"], "stderr": ref["stderr_tail"] if ref["returncode"] else "",
                                     "output_sha256": sha256(ref["output"]) if Path(ref["output"]).exists() else None,
                                     "children": len(g6_lines(ref["output"])) if Path(ref["output"]).exists() else None},
                       "candidates": {}}
                ok = True
                for k, b in binaries.items():
                    got = run_udenum(b, parents, c["n"], c["m"], w / "out" / f"{tag}.{k}.g6", extra=extra)
                    problems = compare_runs(ref, got)
                    rec["candidates"][k] = {"identical": not problems, "problems": problems, "cpu": got["cpu"]}
                    ok = ok and not problems
                rec["identical"] = ok
                results.append(rec)
                r = rec["reference"]
                status = "IDENTICAL" if ok else "DIFFERENT: " + "; ".join(
                    f"{k}: {', '.join(v['problems'])}" for k, v in rec["candidates"].items() if v["problems"])
                what = (f"children {r['children']:6d} bad_sets {r['stats']['bad_sets']:7d}" if r["returncode"] == 0
                        else f"refused ({r['stderr'][:48]}), {r['children']} children before it")
                print(f"{c['group']:5s} {c['cell']:26s} {inp:4s} {mode or 'plain':10s} parents "
                      f"{rec['parents']:6d} {what} | cpu ref {r['cpu'] if r['cpu'] is not None else float('nan'):8.3f} "
                      f"new {rec['candidates']['new']['cpu'] if rec['candidates']['new']['cpu'] is not None else float('nan'):7.3f} | {status}",
                      file=log, flush=True)
    ok = all(r["identical"] for r in results)
    by_group = {}
    for r in results:
        g = by_group.setdefault(r["group"], {"runs": 0, "identical": 0, "parents": 0, "children": 0, "refusals": 0})
        g["runs"] += 1
        g["identical"] += r["identical"]
        g["parents"] += r["parents"]
        g["children"] += r["reference"]["children"] or 0
        g["refusals"] += r["reference"]["returncode"] != 0
    summary = {"reference": {"path": str(BASE398_UDENUM), "sha256": BASE398_SHA256},
               "candidates": {k: {"path": str(b), "sha256": sha256(b)} for k, b in binaries.items()},
               "by_group": by_group, "runs": results, "pass": ok, "seconds": round(time.monotonic() - t0, 1)}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    for g, v in by_group.items():
        print(f"{g}: {v['identical']} of {v['runs']} runs identical ({v['parents']} parent records, "
              f"{v['children']} reference children, {v['refusals']} identical-refusal runs expected)", file=log)
    print("RESULT:", "PASS" if ok else "FAIL", file=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
