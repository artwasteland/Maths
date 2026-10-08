#!/usr/bin/env python3
"""enum2 (the 398) against udenum --forbidden-set 398 on real cells.

For each cell of enum/REPORT-398.md section 4.2 (the (22,61) DAG's 11-19..12-27, the
unpruned (18,46) DAG's 15-34..18-46, and the real (22,61) final cell, 743 level-21
parents from the 48 slices of the u(22) run):

  P74   the cell's production parent file (Mode 74), and C74 its production output;
  P398  P74 minus the records that contain one of the 398, decided by enum2's own
        ContainmentTester (no matcher32, no udfilter);
  PROD  udenum --forbidden-set 398 run on P398 (the production enumerator);
  ENUM2 enum2's children of every record of P398 with the 398;
  E     C74 minus the records that contain one of the 398 (enum2's decider): the
        builder's semantic identity, re-derived independently.

PASS for the cell iff set(ENUM2) == set(PROD), PROD has no duplicate line, every PROD
child's recovered canonical parent is a record of P398 and the children of every parent
agree parent by parent, the parent indices are non-decreasing along PROD, and
set(PROD) == set(E).  Equal counts or ENUM2 <= PROD are reported but never decide: --red
shows them passing on broken outputs while the set comparison fails.

--red (after the cells):
  R1  enum2 with ONE member of the 324 removed from its list, on the parents of the
      Mode-74 children that contain exactly that member and no other of the 398: must
      emit extra children (and each extra must contain exactly that member);
  R2  one record dropped from PROD: must be detected;
  R3a one PROD record replaced by another graph of the same cell: the WRONG equal-count
      check passes, the set comparison fails;
  R3b one record dropped from ENUM2: the WRONG enum2 <= production check passes, the set
      comparison fails;
  R4  enum2 with the 74 only on P398 (a generator without the 324): must differ.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from v398lib import (ORIG_DAG_F12, REPO_DAG22, REPO_SUP, RUNS, SCRATCH, compare, dump, enum2,
                     read_records, recover_parent, run_udenum, sha256, software, write_records)

U22_SLICES = SCRATCH.parent / "u22-slices"   # s<i>of48/{21-56.keep.g6,22-61.g6}, from the worker branches

CELLS = ([(REPO_DAG22, c) for c in ("11-19", "11-20", "11-21", "11-22", "11-23",
                                    "12-23", "12-24", "12-25", "12-26", "12-27")] +
         [(REPO_SUP, c) for c in ("15-34", "15-35", "15-36", "15-37", "16-38", "16-39", "16-40",
                                  "16-41", "17-42", "17-43", "18-46")] +
         [(None, "22-61")])


def cell_inputs(dag: Path | None, cell: str, work: Path) -> dict:
    n, m = map(int, cell.split("-"))
    if dag is None:
        parents, children = [], []
        for s in range(48):
            parents += read_records(U22_SLICES / f"s{s}of48" / "21-56.keep.g6")
            children += read_records(U22_SLICES / f"s{s}of48" / "22-61.g6")
        return {"name": "u22-final/22-61", "n": n, "m": m, "P74": parents, "C74": children,
                "c74_manifest_check": "48 slice files from the worker branches (743 parents, 4 children)"}
    manifest = json.loads((dag / f"{cell}.manifest.json").read_text())
    c74_path = dag / f"{cell}.g6"
    ok = (sha256(c74_path) == manifest["children_file_sha256"])
    if not ok:
        raise SystemExit(f"{c74_path} does not match its manifest")
    return {"name": f"{dag.name}/{cell}", "n": n, "m": m,
            "P74": read_records(dag / "_parents" / f"{cell}.g6"), "C74": read_records(c74_path),
            "c74_manifest_check": "sha256 equal to the aggregate manifest"}


def run_cell(dag: Path | None, cell: str, fs: enum2.ForbiddenSet, work: Path, log) -> dict:
    t_start = time.monotonic()
    c = cell_inputs(dag, cell, work)
    n, m = c["n"], c["m"]
    tag = c["name"].replace("/", "_")
    tester = fs.tester
    t0 = time.process_time()
    p74_hits = {}
    p398 = []
    for code in c["P74"]:
        hit = tester.first(enum2.graph6_decode(code))
        if hit is None:
            p398.append(code)
        else:
            p74_hits[code] = hit
    c74_hits = {}
    expected = []
    for code in c["C74"]:
        hit = tester.first(enum2.graph6_decode(code))
        if hit is None:
            expected.append(code)
        else:
            c74_hits[code] = hit
    decider_seconds = time.process_time() - t0
    p398_file = work / f"{tag}.p398.g6"
    write_records(p398_file, p398)
    prod_file = work / f"{tag}.prod398.g6"
    stats = run_udenum(p398_file, n, m, prod_file, "398")
    prod = read_records(prod_file)
    # enum2, parent by parent
    t1 = time.process_time()
    per_parent: dict[str, set[str]] = {}
    raw_all: list[str] = []
    e2stats: dict = {}
    for code in p398:
        kids = list(enum2.extend_parent(enum2.graph6_decode(code), m, fs, stats=e2stats))
        raw_all.extend(kids)
        if kids:
            per_parent[code] = set(kids)
    enum2_seconds = time.process_time() - t1
    result = compare(prod, raw_all)
    # parent by parent: recover every production child's parent
    index = {code: i for i, code in enumerate(p398)}
    prod_by_parent: dict[str, set[str]] = {}
    unknown_parent = 0
    order_ok = True
    last = -1
    for child in prod:
        parent = recover_parent(child)
        if parent not in index:
            unknown_parent += 1
            continue
        if index[parent] < last:
            order_ok = False
        last = index[parent]
        prod_by_parent.setdefault(parent, set()).add(child)
    parents_differing = sorted(set(prod_by_parent) ^ set(per_parent) |
                               {p for p in set(prod_by_parent) & set(per_parent)
                                if prod_by_parent[p] != per_parent[p]})
    sem = compare(expected, prod)   # E against PROD
    record = {
        "cell": c["name"], "n": n, "m": m, "c74_input_check": c["c74_manifest_check"],
        "P74": len(c["P74"]), "P74_containing_398": len(p74_hits), "P398": len(p398),
        "C74": len(c["C74"]), "C74_containing_398": len(c74_hits), "E": len(expected),
        "PROD": len(prod), "ENUM2": result["enum2"], "ENUM2_raw": result["enum2_raw"],
        "only_production": result["only_production"], "only_enum2": result["only_enum2"],
        "only_production_first": result["only_production_first"],
        "only_enum2_first": result["only_enum2_first"],
        "prod_duplicates": len(prod) - result["production_distinct"],
        "prod_children_with_unknown_parent": unknown_parent,
        "prod_parent_order_nondecreasing": order_ok,
        "parents_differing": len(parents_differing), "parents_differing_first": parents_differing[:5],
        "parents_with_children": len(per_parent),
        "E_equals_PROD": sem["identical"],
        "set_equal": result["identical"], "equal_counts": result["equal_counts"],
        "enum2_subset_of_production": result["enum2_subset_of_production"],
        "hits_on_first_74": sum(1 for h in list(p74_hits.values()) + list(c74_hits.values()) if h < 74),
        "enum2_stats": e2stats, "udenum_stats": {k: stats.get(k) for k in
                                                 ("parents_processed", "children_written", "cpu_seconds")},
        "enum2_cpu_seconds": round(enum2_seconds, 2),
        "enum2_ms_per_parent": round(1000 * enum2_seconds / max(1, len(p398)), 2),
        "enum2_ms_per_processed_parent": round(1000 * enum2_seconds / max(1, e2stats.get("parents_processed", 0)), 2),
        "decider_cpu_seconds": round(decider_seconds, 2),
        "wall_seconds": round(time.monotonic() - t_start, 1),
        "p398_sha256": sha256(p398_file), "prod_sha256": sha256(prod_file),
    }
    record["pass"] = (record["set_equal"] and record["prod_duplicates"] == 0 and unknown_parent == 0
                      and order_ok and not parents_differing and record["E_equals_PROD"]
                      and record["hits_on_first_74"] == 0)
    print(f"{c['name']:22s} P74 {len(c['P74']):6d} (398-hits {len(p74_hits):6d}) P398 {len(p398):6d} | "
          f"C74 {len(c['C74']):6d} E {len(expected):6d} PROD {len(prod):6d} ENUM2 {result['enum2']:6d} "
          f"(raw {result['enum2_raw']}) only_prod {result['only_production']} only_enum2 {result['only_enum2']} "
          f"| per-parent diffs {len(parents_differing)} | {'PASS' if record['pass'] else 'FAIL'} "
          f"| enum2 {enum2_seconds:.1f}s ({record['enum2_ms_per_processed_parent']} ms/processed parent)",
          file=log, flush=True)
    return record


def red_controls(fs: enum2.ForbiddenSet, work: Path, member_cell: str, log) -> list[dict]:
    reds = []
    # -------- R1: one member of the 324 removed from enum2's list
    dag = REPO_DAG22 if member_cell.startswith(("11-", "12-")) else REPO_SUP
    c = cell_inputs(dag, member_cell, work)
    n, m = c["n"], c["m"]
    tester = fs.tester
    p398 = [p for p in c["P74"] if tester.first(enum2.graph6_decode(p)) is None]
    p398_set = set(p398)
    prod = read_records(work / f"{c['name'].replace('/', '_')}.prod398.g6")
    single: dict[int, list[str]] = {}
    for child in c["C74"]:
        members = tester.all(enum2.graph6_decode(child))
        if len(members) == 1 and members[0] >= 74 and recover_parent(child) in p398_set:
            single.setdefault(members[0], []).append(child)
    if not single:
        raise SystemExit(f"R1: no Mode-74 child of {member_cell} contains exactly one of the 324")
    member = max(single, key=lambda k: (len(single[k]), -k))
    targets = single[member]
    position = {code: i for i, code in enumerate(p398)}
    parents = sorted({recover_parent(ch) for ch in targets}, key=position.__getitem__)
    parent_set = set(parents)
    dropped = enum2.load_forbidden_set("398", drop_members=[member])
    raw = []
    for code in parents:
        raw.extend(enum2.extend_parent(enum2.graph6_decode(code), m, dropped))
    prod_of_parents = [ch for ch in prod if recover_parent(ch) in parent_set]
    res = compare(prod_of_parents, raw)
    extras = sorted(set(raw) - set(prod_of_parents))
    extras_exactly_member = all(tester.all(enum2.graph6_decode(x)) == [member] for x in extras)
    reds.append({"control": f"R1 enum2 without member {member} of the 398 (one of the 324), "
                            f"on the {len(parents)} parents in {c['name']} of the {len(targets)} Mode-74 "
                            f"children containing exactly that member",
                 "member": member, "member_edges": json.loads(fs.path.read_text())[member],
                 "production_children": res["production"], "enum2_children": res["enum2"],
                 "extra_children": len(extras), "missing_children": res["only_production"],
                 "extras_contain_exactly_that_member": extras_exactly_member,
                 "extras_are_the_mode74_children": set(extras) == set(targets),
                 "went_red": not res["identical"] and len(extras) > 0 and extras_exactly_member})
    # -------- R2, R3a, R3b on the same cell's full comparison
    raw_full = []
    for code in p398:
        raw_full.extend(enum2.extend_parent(enum2.graph6_decode(code), m, fs))
    base = compare(prod, raw_full)
    r2 = compare(prod[:-1], raw_full)
    reds.append({"control": f"R2 one record dropped from production ({c['name']})",
                 "baseline_identical": base["identical"], "identical": r2["identical"],
                 "only_enum2": r2["only_enum2"], "went_red": base["identical"] and not r2["identical"]})
    replacement = next(x for x in c["C74"] if x not in set(prod))
    swapped = prod[:-1] + [replacement]
    r3a = compare(swapped, raw_full)
    reds.append({"control": f"R3a one production record replaced by another ({c['name']}) graph",
                 "wrong_equal_count_check": "PASS" if r3a["equal_counts"] else "FAIL",
                 "set_comparison": "PASS" if r3a["identical"] else "FAIL",
                 "went_red": r3a["equal_counts"] and not r3a["identical"]})
    distinct = sorted(set(raw_full))
    r3b = compare(prod, distinct[1:])
    reds.append({"control": f"R3b one record dropped from enum2's output ({c['name']})",
                 "wrong_subset_check": "PASS" if r3b["enum2_subset_of_production"] else "FAIL",
                 "set_comparison": "PASS" if r3b["identical"] else "FAIL",
                 "went_red": r3b["enum2_subset_of_production"] and not r3b["identical"]})
    # -------- R4: the 74 only (a generator without the 324) on P398
    fs74 = enum2.load_forbidden_set("74")
    raw74 = []
    for code in p398:
        raw74.extend(enum2.extend_parent(enum2.graph6_decode(code), m, fs74))
    r4 = compare(prod, raw74)
    reds.append({"control": f"R4 enum2 with the 74 only on P398 ({c['name']})",
                 "enum2_children": r4["enum2"], "production_children": r4["production"],
                 "only_enum2": r4["only_enum2"], "wrong_subset_check_production_in_enum2":
                     set(prod) <= set(raw74), "went_red": not r4["identical"]})
    for r in reds:
        print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: "
              f"{json.dumps({k: v for k, v in r.items() if k != 'member_edges'})}", file=log, flush=True)
    return reds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default="", help="comma-separated cells (e.g. 11-21,22-61); default all")
    ap.add_argument("--work", type=Path, default=SCRATCH / "cells398")
    ap.add_argument("--summary", type=Path, default=RUNS / "cells398.json")
    ap.add_argument("--red", action="store_true")
    ap.add_argument("--red-cell", default="11-20", help="cell for the red controls")
    ap.add_argument("--red-only", action="store_true", help="skip the cells (their outputs must exist)")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    fs = enum2.load_forbidden_set("398")
    log = sys.stdout
    print(f"software {json.dumps(software())}", file=log, flush=True)
    wanted = set(x for x in a.only.split(",") if x)
    previous = json.loads(a.summary.read_text()) if a.summary.exists() else {}
    results = {r["cell"]: r for r in previous.get("cells", [])}
    if not a.red_only:
        for dag, cell in CELLS:
            if wanted and cell not in wanted:
                continue
            rec = run_cell(dag, cell, fs, a.work, log)
            results[rec["cell"]] = rec
            dump(a.summary, {"software": software(), "cells": list(results.values()),
                             "red_controls": previous.get("red_controls", [])})
    reds = red_controls(fs, a.work, a.red_cell, log) if a.red else previous.get("red_controls", [])
    cells = list(results.values())
    totals = {k: sum(r[k] for r in cells) for k in ("P74", "P74_containing_398", "P398", "C74",
                                                     "C74_containing_398", "E", "PROD", "ENUM2")}
    ok = all(r["pass"] for r in cells) and all(r["went_red"] for r in reds)
    summary = {"software": software(), "cells": cells, "red_controls": reds, "totals": totals,
               "cells_pass": sum(r["pass"] for r in cells), "cells_total": len(cells), "pass": ok}
    dump(a.summary, summary)
    print(f"cells pass: {summary['cells_pass']} of {len(cells)}; totals {totals}; red controls "
          f"{sum(r['went_red'] for r in reds)} of {len(reds)} went red", file=log)
    print("RESULT:", "PASS" if ok else "FAIL", file=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
