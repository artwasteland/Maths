#!/usr/bin/env python3
"""Brute force at order 10, where the 324 first act: enum2 against a naive closure.

  G9     every graph on 9 vertices (nauty-geng, 274,668), and G9F the 398-free ones,
         decided by enum2's ContainmentTester; G9F must equal udenum --filter
         --forbidden-set 398 over the same graphs, have 11,803 members, and agree with the
         reference backtracker straightforward_contains on a seeded sample (it is slow);
  NAIVE  every graph H + v(N), H in G9F and N any subset of V(H) (512 per H), in
         canonical graph6, then kept iff it contains none of the 398 (ContainmentTester):
         no canonical augmentation, no bad neighbourhoods, no parent guard.  Every
         398-free graph on 10 vertices is H + v for H = G - v (398-freeness is
         hereditary), so NAIVE is exactly the 398-free graphs on 10 vertices;
  ENUM2  enum2's canonical augmentation (fast engine, the 398) from G9F, every m = 0..45;
  UDF    udenum --filter --forbidden-set 398 over every graph of order 10 (nauty-geng,
         12,005,168), canonicalised by enum2: a third route, through production code.

PASS iff ENUM2 == NAIVE == UDF as sets of canonical graph6 (and |NAIVE| = 105,680, the
count GP-10 and the Mode-398 builder report), and the same with the 74 (106,189), and
NAIVE74 - NAIVE398 is exactly 509 graphs, each containing one of the 324 and none of the 74.

--red:
  R1  enum2 with one member of the 324 removed: extra graphs, each containing exactly
      that member of the 398;
  R2  one record dropped from ENUM2: detected;
  R3a one ENUM2 record replaced by a 74-free graph that contains a 324 member (the
      wrong equal-count check passes, the set comparison fails);
  R3b the wrong ENUM2 <= NAIVE check passes on R2's output, the set comparison fails;
  R4  ENUM2 with the 74 only, judged against NAIVE (398): must differ (by the 509).
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import pynauty

from v398lib import (DATA, RUNS, SCRATCH, UDENUM, UDENUM_SHA256, compare, dump, enum2, read_records,
                     sha256, software)

GENG = "/usr/bin/nauty-geng"


def geng(n: int, m: int | None = None) -> list[str]:
    cmd = [GENG, "-q", str(n)] + ([f"{m}:{m}"] if m is not None else [])
    return [x for x in subprocess.run(cmd, check=True, stdout=subprocess.PIPE, text=True).stdout.split()]


def canonical_of_adj(adj: list[int]) -> str:
    n = len(adj)
    g = pynauty.Graph(n, adjacency_dict={v: [u for u in range(n) if adj[v] >> u & 1] for v in range(n)})
    order = pynauty.canon_label(g)
    rank = [0] * n
    for pos, old in enumerate(order):
        rank[old] = pos
    new = [0] * n
    for old in range(n):
        row = 0
        a = adj[old]
        while a:
            low = a & -a
            a ^= low
            row |= 1 << rank[low.bit_length() - 1]
        new[rank[old]] = row
    return enum2.graph6_encode(enum2.Graph(tuple(new)))


def udenum_filter(path: Path, n: int, m: int, out: Path) -> list[str]:
    p = subprocess.run(["nice", "-n", "15", str(UDENUM), "--filter", "--parents", str(path),
                        "--forbidden", str(DATA / "forbidden-398.json"), "--forbidden-set", "398",
                        "--n", str(n), "--m", str(m), "--output", str(out),
                        "--manifest", str(out.with_suffix(".manifest.json")),
                        "--shard-id", f"udf-{n}-{m}", "--overwrite"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise SystemExit(f"udenum --filter failed at n={n} m={m}: {p.stderr}")
    return read_records(out)


def step_g9(fs398, fs74, work: Path, log, reference_sample: int) -> dict:
    """G9F by enum2's ContainmentTester; checked against udenum --filter (every graph) and
    against the reference backtracker straightforward_contains (a seeded sample: it is slow)."""
    if sha256(UDENUM) != UDENUM_SHA256:
        raise SystemExit("udenum is not the pinned Mode-398 binary")
    t0 = time.process_time()
    raw = geng(9)
    free_fast = []
    for code in raw:
        g = enum2.graph6_decode(code)
        if not fs398.tester.contains(g):
            free_fast.append(canonical_of_adj(list(g.adj)))
    free_fast = sorted(set(free_fast))
    # production decider, every graph, per edge count
    udf: set[str] = set()
    for m in range(0, 37):
        path = work / "geng9.g6"
        with path.open("w") as stream:
            subprocess.run([GENG, "-q", "9", f"{m}:{m}"], check=True, stdout=stream)
        for code in udenum_filter(path, 9, m, work / "udf9.g6"):
            udf.add(enum2.canonical_g6(enum2.graph6_decode(code)))
    # reference backtracker on a seeded sample, half from the free graphs
    rng = random.Random(20260925)
    free_set = set(free_fast)
    sample = rng.sample(raw, reference_sample // 2) + rng.sample(free_fast, reference_sample // 2)
    disagree = []
    for code in sample:
        g = enum2.graph6_decode(code)
        fast = not fs398.tester.contains(g)
        ref = enum2.f_free(g, fs74.graphs)   # at order 9 only the 74 can occur
        if fast != ref:
            disagree.append(code)
    (work / "g9free.g6").write_text("".join(x + "\n" for x in free_fast))
    rec = {"geng_9": len(raw), "g9_398_free": len(free_fast), "udenum_filter_free": len(udf),
           "tester_equals_udenum_filter": set(free_fast) == udf,
           "reference_backtracker_sample": len(sample), "deciders_disagree": len(disagree),
           "disagree_first": disagree[:5], "cpu_seconds": round(time.process_time() - t0, 1)}
    print(f"G9: {rec}", file=log, flush=True)
    return rec


def step_naive(g9free: list[str], fs398, fs74, work: Path, log) -> dict:
    t0 = time.process_time()
    children: set[str] = set()
    for code in g9free:
        h = enum2.graph6_decode(code)
        base = list(h.adj)
        for nb in range(1 << 9):
            child = list(base)
            child.append(nb)
            a = nb
            while a:
                low = a & -a
                a ^= low
                child[low.bit_length() - 1] |= 1 << 9
            children.add(canonical_of_adj(child))
    t1 = time.process_time()
    naive398, naive74 = [], []
    for code in children:
        g = enum2.graph6_decode(code)
        if not fs74.tester.contains(g):
            naive74.append(code)
            if not fs398.tester.contains(g):
                naive398.append(code)
    naive398.sort()
    naive74.sort()
    (work / "naive398.g6").write_text("".join(x + "\n" for x in naive398))
    (work / "naive74.g6").write_text("".join(x + "\n" for x in naive74))
    rec = {"distinct_one_vertex_extensions": len(children), "naive_398_free": len(naive398),
           "naive_74_free": len(naive74), "canonical_cpu_seconds": round(t1 - t0, 1),
           "containment_cpu_seconds": round(time.process_time() - t1, 1)}
    print(f"NAIVE: {rec}", file=log, flush=True)
    return rec


def enum2_all_m(g9free: list[str], fs, tag: str, work: Path, log) -> tuple[list[str], dict]:
    t0 = time.process_time()
    parents = [enum2.graph6_decode(c) for c in g9free]
    out: set[str] = set()
    raw = 0
    per_m = {}
    stats: dict = {}
    for m in range(0, 46):
        got: set[str] = set()
        for h in parents:
            for child in enum2.extend_parent(h, m, fs, stats=stats):
                got.add(child)
                raw += 1
        per_m[m] = len(got)
        out |= got
    records = sorted(out)
    (work / f"enum2-{tag}.g6").write_text("".join(x + "\n" for x in records))
    rec = {"records": len(records), "raw_constructions": raw, "per_m": per_m,
           "parents_processed": stats.get("parents_processed"),
           "cpu_seconds": round(time.process_time() - t0, 1)}
    print(f"ENUM2 {tag}: records {len(records)} raw {raw} cpu {rec['cpu_seconds']}s", file=log, flush=True)
    return records, rec


def step_udfilter(work: Path, log) -> tuple[list[str], dict]:
    """udenum --filter --forbidden-set 398 over every graph on 10 vertices, per edge count."""
    if sha256(UDENUM) != UDENUM_SHA256:
        raise SystemExit("udenum is not the pinned Mode-398 binary")
    t0 = time.monotonic()
    kept: set[str] = set()
    total_in = 0
    raw_path = work / "geng10.g6"
    out_path = work / "udfilter10.g6"
    for m in range(0, 46):
        with raw_path.open("w") as stream:
            subprocess.run(["nice", "-n", "15", GENG, "-q", "10", f"{m}:{m}"], check=True, stdout=stream)
        total_in += sum(1 for _ in raw_path.open())
        for code in udenum_filter(raw_path, 10, m, out_path):
            kept.add(enum2.canonical_g6(enum2.graph6_decode(code)))
    raw_path.unlink(missing_ok=True)
    records = sorted(kept)
    rec = {"graphs_in": total_in, "kept_canonical": len(records), "wall_seconds": round(time.monotonic() - t0, 1)}
    print(f"UDF: {rec}", file=log, flush=True)
    return records, rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=SCRATCH / "brute10")
    ap.add_argument("--summary", type=Path, default=RUNS / "brute10.json")
    ap.add_argument("--red", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="reuse g9free/naive files of an earlier run")
    ap.add_argument("--reference-sample", type=int, default=600,
                    help="9-vertex graphs re-decided by the slow reference backtracker")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    log = sys.stdout
    fs398 = enum2.load_forbidden_set("398")
    fs74 = enum2.load_forbidden_set("74")
    print(f"software {json.dumps(software())}", file=log, flush=True)
    summary: dict = {"software": software()}
    if a.reuse and (a.work / "g9free.g6").exists():
        g9free = read_records(a.work / "g9free.g6")
        summary["g9"] = {"reused": True, "g9_398_free": len(g9free)}
    else:
        summary["g9"] = step_g9(fs398, fs74, a.work, log, a.reference_sample)
        g9free = read_records(a.work / "g9free.g6")
    if a.reuse and (a.work / "naive398.g6").exists():
        naive398 = read_records(a.work / "naive398.g6")
        naive74 = read_records(a.work / "naive74.g6")
        summary["naive"] = {"reused": True, "naive_398_free": len(naive398), "naive_74_free": len(naive74)}
    else:
        summary["naive"] = step_naive(g9free, fs398, fs74, a.work, log)
        naive398 = read_records(a.work / "naive398.g6")
        naive74 = read_records(a.work / "naive74.g6")
    e398, summary["enum2_398"] = enum2_all_m(g9free, fs398, "398", a.work, log)
    e74, summary["enum2_74"] = enum2_all_m(g9free, fs74, "74", a.work, log)
    udf, summary["udfilter_398"] = step_udfilter(a.work, log)
    diff = sorted(set(naive74) - set(naive398))
    diff_ok = all((lambda g: fs74.tester.first(g) is None and
                   any(i >= 74 for i in fs398.tester.all(g)))(enum2.graph6_decode(x)) for x in diff)
    checks = {
        "enum2_398_vs_naive": compare(naive398, e398),
        "enum2_74_vs_naive74": compare(naive74, e74),
        "udfilter_vs_naive": compare(naive398, udf),
        "naive398_count_is_105680": len(naive398) == 105680,
        "naive74_count_is_106189": len(naive74) == 106189,
        "naive74_minus_naive398": len(diff), "naive398_subset_of_naive74": set(naive398) <= set(naive74),
        "difference_each_contains_a_324_member_and_no_74": diff_ok,
    }
    for k, v in checks.items():
        shown = {kk: vv for kk, vv in v.items() if not kk.endswith("_first")} if isinstance(v, dict) else v
        print(f"CHECK {k}: {shown}", file=log, flush=True)
    summary["checks"] = checks
    ok = (checks["enum2_398_vs_naive"]["identical"] and checks["enum2_74_vs_naive74"]["identical"]
          and checks["udfilter_vs_naive"]["identical"] and checks["naive398_count_is_105680"]
          and checks["naive74_count_is_106189"] and len(diff) == 509 and diff_ok
          and checks["naive398_subset_of_naive74"]
          and summary["g9"].get("deciders_disagree", 0) == 0
          and summary["g9"].get("tester_equals_udenum_filter", True)
          and len(g9free) == 11803)
    reds = []
    if a.red:
        # R1: one member of the 324 dropped
        member = 74 + 166   # entry 240, as in REPORT-398's W5b; any member works: each is 74-free on 10 vertices
        dropped = enum2.load_forbidden_set("398", drop_members=[member])
        e_drop, _ = enum2_all_m(g9free, dropped, f"398-drop{member}", a.work, log)
        r = compare(naive398, e_drop)
        extras = sorted(set(e_drop) - set(naive398))
        exact = all(fs398.tester.all(enum2.graph6_decode(x)) == [member] for x in extras)
        reds.append({"control": f"R1 enum2 without member {member}", "extra": len(extras),
                     "missing": r["only_production"], "extras_contain_exactly_that_member": exact,
                     "went_red": (not r["identical"]) and len(extras) > 0 and exact})
        # R2 / R3b: one record dropped from ENUM2
        r2 = compare(naive398, e398[1:])
        reds.append({"control": "R2 one record dropped from ENUM2", "identical": r2["identical"],
                     "only_naive": r2["only_production"], "went_red": not r2["identical"]})
        reds.append({"control": "R3b the WRONG check ENUM2 <= NAIVE on R2's output",
                     "wrong_subset_check": "PASS" if r2["enum2_subset_of_production"] else "FAIL",
                     "set_comparison": "PASS" if r2["identical"] else "FAIL",
                     "went_red": r2["enum2_subset_of_production"] and not r2["identical"]})
        # R3a: one ENUM2 record replaced by one of the 509
        r3 = compare(naive398, e398[1:] + [diff[0]])
        reds.append({"control": "R3a one ENUM2 record replaced by a graph containing a 324 member",
                     "wrong_equal_count_check": "PASS" if r3["equal_counts"] else "FAIL",
                     "set_comparison": "PASS" if r3["identical"] else "FAIL",
                     "went_red": r3["equal_counts"] and not r3["identical"]})
        # R4: the 74-only generator judged against the 398 ground truth
        r4 = compare(naive398, e74)
        reds.append({"control": "R4 ENUM2 with the 74 only, judged against NAIVE (398)",
                     "only_enum2": r4["only_enum2"], "went_red": not r4["identical"]})
        for r in reds:
            print(f"RED CONTROL {'went red' if r['went_red'] else 'DID NOT GO RED'}: {json.dumps(r)}",
                  file=log, flush=True)
    summary["red_controls"] = reds
    summary["pass"] = ok and all(r["went_red"] for r in reds)
    dump(a.summary, summary)
    print("RESULT:", "PASS" if summary["pass"] else "FAIL", file=log)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
