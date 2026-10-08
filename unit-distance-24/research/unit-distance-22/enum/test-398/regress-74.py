#!/usr/bin/env python3
"""(a) Regression: the new udenum in forbidden set 74 is byte-identical to the u(22) production binary.

For every cell (a parent file and the tracked level file the production run wrote from it):
  1. the parent file and the tracked output have the sha256s recorded in the production manifest;
  2. the OLD binary (test-398/old/enum/udenum, rebuilt from the unmodified sources, which must
     hash to the production binary 94a85d33...) and the NEW binary, run once with no set flag and
     once with --forbidden-set 74, all write children files byte-identical to each other AND to
     the tracked production output;
  3. the old and new binaries report identical internal counters (bad sets, neighbourhoods,
     orbit representatives, orbit rejections, ...), not only identical outputs.

Red controls (--red): the comparison must report DIFFERENT for
  R1 the new binary with --mutation-no-child-orbit (duplicates admitted),
  R2 the new binary with --mutation-drop-first-badset (a forbidden child admitted; K3 -> (4,6)),
  R3 the new binary run with --forbidden-set 398 on a 74-list cell (a silent change of list),
  R4 a tracked output with its last record removed (a tampered reference).

Cells: the level-11 and level-12 cells of the (22,61) DAG (enum/out-22/dag-22-61), the level
15-18 cells of the unpruned (18,46) calibration DAG (enum/out-sup/dag-18-46), and the final
(21,56) -> (22,61) cell of all 48 u(22) slices (21-56.keep.g6 and 22-61.g6 from the worker
branches, passed with --slices DIR).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from t398lib import (ENUM, F398, NEW_UDENUM, OLD_UDENUM, PRODUCTION_UDENUM_SHA256, SCRATCH, STAT_COUNTERS,
                     g6_lines, run_udenum, sha256, write_lines)

OUT22 = ENUM / "out-22" / "dag-22-61"
SUP = ENUM / "out-sup" / "dag-18-46"


def manifest_hashes(manifest: Path) -> tuple[str, str]:
    m = json.loads(manifest.read_text())
    parent = [v for k, v in m["inputs_sha256"].items() if "/_parents/" in k]
    if len(parent) != 1:
        raise SystemExit(f"{manifest}: cannot identify the parent file hash")
    return parent[0], m["children_file_sha256"]


def cells(slices: Path | None) -> list[dict]:
    out = []
    for d, names in ((OUT22, ["11-19", "11-20", "11-21", "11-22", "11-23",
                              "12-23", "12-24", "12-25", "12-26", "12-27"]),
                     (SUP, ["15-34", "15-35", "15-36", "15-37", "16-38", "16-39", "16-40", "16-41",
                            "17-42", "17-43", "18-46"])):
        for name in names:
            n, m = map(int, name.split("-"))
            ph, oh = manifest_hashes(d / f"{name}.manifest.json")
            out.append({"cell": f"{d.name}/{name}", "parents": d / "_parents" / f"{name}.g6",
                        "tracked": d / f"{name}.g6", "n": n, "m": m, "parent_sha": ph, "out_sha": oh})
    if slices is not None:
        for s in range(48):
            sd = slices / f"s{s}of48"
            ph, oh = manifest_hashes(sd / "22-61.manifest.json")
            out.append({"cell": f"u22-s{s}of48/22-61", "parents": sd / "21-56.keep.g6",
                        "tracked": sd / "22-61.g6", "n": 22, "m": 61, "parent_sha": ph, "out_sha": oh})
    return out


def compare(c: dict, work: Path, log) -> dict:
    """Run the three configurations; return a result record (pass == everything identical)."""
    tag = c["cell"].replace("/", "_")
    problems = []
    if sha256(c["parents"]) != c["parent_sha"]:
        problems.append("parent file hash differs from the production manifest")
    if sha256(c["tracked"]) != c["out_sha"]:
        problems.append("tracked output hash differs from the production manifest")
    old = run_udenum(OLD_UDENUM, c["parents"], c["n"], c["m"], work / f"{tag}.old.g6")
    new = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / f"{tag}.new.g6")
    new74 = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / f"{tag}.new74.g6",
                       extra=["--forbidden-set", "74"])
    ref = c["tracked"].read_bytes()
    outs = {k: (work / f"{tag}.{k}.g6").read_bytes() for k in ("old", "new", "new74")}
    for k, v in outs.items():
        if v != ref:
            problems.append(f"{k} output differs from the tracked production output")
    for k in STAT_COUNTERS:
        if not (old[k] == new[k] == new74[k]):
            problems.append(f"counter {k}: old {old[k]} new {new[k]} new74 {new74[k]}")
    rec = {"cell": c["cell"], "parents": old["parents_seen"], "children": old["children_written"],
           "output_sha256": sha256(work / f"{tag}.new.g6"), "identical": not problems,
           "problems": problems,
           "counters_old": {k: old[k] for k in STAT_COUNTERS},
           "cpu_old": old["cpu_seconds"], "cpu_new": new["cpu_seconds"], "cpu_new74": new74["cpu_seconds"]}
    print(f"{c['cell']:32s} parents {rec['parents']:6d} children {rec['children']:6d} "
          f"{'IDENTICAL' if not problems else 'DIFFERENT: ' + '; '.join(problems)}", file=log, flush=True)
    return rec


def red_controls(cs: list[dict], work: Path, log) -> list[dict]:
    """Each must make the same byte comparison report DIFFERENT.

    (--mutation-drop-first-badset aborts on real cells with "automorphism left the neighbourhood
    domain": dropping one bad set breaks the Aut(H)-invariance of the candidate domain.  That
    mutation is therefore run where verify.py runs it, on the parent K3 at target (4,6).)"""
    reds = []

    def record(name, candidate: Path, reference_bytes: bytes, children: int):
        same = candidate.read_bytes() == reference_bytes
        reds.append({"control": name, "children": children,
                     "tracked_children": len([x for x in reference_bytes.split(b"\n") if x]),
                     "went_red": not same})

    c = next(x for x in cs if x["cell"].endswith("12-24"))
    mut = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / "red-no-orbit.g6",
                     extra=["--mutation-no-child-orbit"])
    record(f"R1 new binary --mutation-no-child-orbit on {c['cell']}", work / "red-no-orbit.g6",
           c["tracked"].read_bytes(), mut["children_written"])

    k3 = work / "k3.g6"
    k3.write_bytes(b"Bw\n")
    old = run_udenum(OLD_UDENUM, k3, 4, 6, work / "red-k3-old.g6")
    mut = run_udenum(NEW_UDENUM, k3, 4, 6, work / "red-k3-drop.g6", extra=["--mutation-drop-first-badset"])
    record("R2 new binary --mutation-drop-first-badset on parent K3, target (4,6), against the old binary",
           work / "red-k3-drop.g6", (work / "red-k3-old.g6").read_bytes(), mut["children_written"])

    d = next(x for x in cs if x["cell"].endswith("18-46") and "dag-18-46" in x["cell"])
    mut = run_udenum(NEW_UDENUM, d["parents"], d["n"], d["m"], work / "red-set398.g6",
                     extra=["--forbidden-set", "398"], forbidden=F398)
    record(f"R3 new binary with --forbidden-set 398 on {d['cell']} (the 74-list cell)",
           work / "red-set398.g6", d["tracked"].read_bytes(), mut["children_written"])

    tampered = work / "red-tampered-tracked.g6"
    write_lines(tampered, g6_lines(c["tracked"])[:-1])
    new = run_udenum(NEW_UDENUM, c["parents"], c["n"], c["m"], work / "red-new.g6")
    record(f"R4 tracked output of {c['cell']} with its last record removed", work / "red-new.g6",
           tampered.read_bytes(), new["children_written"])
    for r in reds:
        print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {r['control']} "
              f"(children {r['children']} vs reference {r['tracked_children']})", file=log, flush=True)
    return reds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, default=None,
                    help="directory holding s0of48 .. s47of48 (results/u22 of the worker branches)")
    ap.add_argument("--work", type=Path, default=SCRATCH / "regress-74")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "regress-74.json")
    ap.add_argument("--red", action="store_true", help="also run the red controls")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    log = sys.stdout
    old_sha, new_sha = sha256(OLD_UDENUM), sha256(NEW_UDENUM)
    print(f"old udenum {old_sha} (production {PRODUCTION_UDENUM_SHA256}: "
          f"{'same file' if old_sha == PRODUCTION_UDENUM_SHA256 else 'DIFFERENT'})", file=log)
    print(f"new udenum {new_sha}", file=log)
    if old_sha != PRODUCTION_UDENUM_SHA256:
        print("the old binary is not the production binary; refusing to call this a regression test")
        return 2
    cs = cells(a.slices)
    results = [compare(c, a.work, log) for c in cs]
    reds = red_controls(cs, a.work, log) if a.red else []
    ok = all(r["identical"] for r in results) and all(r["went_red"] for r in reds)
    summary = {"old_udenum": old_sha, "new_udenum": new_sha, "cells": results, "red_controls": reds,
               "cells_identical": sum(r["identical"] for r in results), "cells_total": len(results),
               "children_compared": sum(r["children"] for r in results),
               "parents_processed": sum(r["parents"] for r in results), "pass": ok}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"cells identical: {summary['cells_identical']} of {summary['cells_total']}; "
          f"children compared {summary['children_compared']}; parents {summary['parents_processed']}; "
          f"red controls {sum(r['went_red'] for r in reds)} of {len(reds)} went red", file=log)
    print("RESULT:", "PASS" if ok else "FAIL", file=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
