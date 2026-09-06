#!/usr/bin/env python3
"""Replay udenum shards with the independent enumerator enum2.py and compare per shard.

Reads the shard manifests of a finished run-dag2 DAG directory, slices the SAME frozen parent
file over a [a, b) sub-range of the shard's parent range, runs enum2.extend_parent on every
parent with the SAME target (n, m), and compares the set of canonical children with the udenum
shard output restricted to the children of those parents.

Restriction of udenum's output to a sub-range (when [a, b) is not the whole shard): for a
child G in canonical graph6, its generating parent is G minus the first minimum-degree vertex
in canonical order (that is the deletion rule both enumerators accept on), canonicalised, and
looked up in the shard's parent records to get its index. udenum writes children in parent
order, so the children of parents [a, b) are a contiguous block of lines; the block edges are
located by binary search on the recovered parent index and every line in the block is
verified to have its recovered parent in [a, b) (the lines just outside the block are verified
to lie outside). A whole-shard replay compares against the whole file.

Nothing is written outside --workdir (default: this directory). enum2.py is imported unmodified.

Subcommands:
  bench      time enum2 on a parent-file slice (no comparison)
  plan       build the seeded sample plan (which sub-range of which shard) with a cost estimate
  replay     run a plan (or all/listed shards) and compare; per-shard results stream to a JSONL
  summarize  per-cell table and summary JSON from a JSONL
  control-a  replay ONE sub-range with one parent record mutated (one edge flipped, re-canonicalised)
  control-b  replay sub-ranges with one forbidden graph removed from a COPY of the list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENUM2_DIR = HERE.parent
sys.path.insert(0, str(ENUM2_DIR))
import enum2  # noqa: E402  (unmodified, imported as a module)

ROOT = ENUM2_DIR.parent
DEFAULT_DAG = ROOT / "enum" / "out-22" / "dag-22-61-f12"
DEFAULT_FORBIDDEN = ROOT / "data" / "forbidden-74.json"
ALL_CELLS = "11-17,11-18,11-19,11-20,11-21,11-22,11-23,12-20,12-21,12-22,12-23,12-24,12-25,12-26,12-27"

# measured 2026-09-05 on liam-desktop (nice 10, 4 concurrent): seconds per PROCESSED parent
RATE = {(3, 11): 5.4, (3, 10): 3.0, (2, 11): 0.40, (2, 10): 0.19, (4, 11): 1.3, (4, 10): 1.3,
        (1, 11): 0.01, (1, 10): 0.01, (0, 10): 0.01, (0, 11): 0.01}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_records(path: Path) -> list[str]:
    """Exactly udenum's record model: skip blank lines and '>>graph6<<' headers."""
    out = []
    with path.open("r", encoding="ascii") as stream:
        for line in stream:
            s = line.rstrip("\r\n")
            if not s or s.startswith(">>graph6<<"):
                continue
            out.append(s)
    return out


def load_shards(dag: Path, cells: list[str]) -> list[dict]:
    shards = []
    for cell in cells:
        n, m = (int(x) for x in cell.split("-"))
        shard_dir = dag / "shards" / cell
        agg = json.loads((dag / f"{cell}.manifest.json").read_text())
        regions = []
        pos = 0
        for src in agg["parent_sources"]:
            regions.append({"a": pos, "b": pos + src["records"], "d": src["d"], "level": src["level"]})
            pos += src["records"]
        for manifest_path in sorted(shard_dir.glob(f"{cell}-*.manifest.json")):
            info = json.loads(manifest_path.read_text())
            shard_id = info["shard_id"]
            stats = json.loads(manifest_path.with_name(f"{shard_id}.stats.json").read_text())
            shards.append({
                "cell": cell, "n": n, "m": m, "shard_id": shard_id,
                "parent_file": info["parent_file"],
                "start": int(info["parent_range"][0]), "end": int(info["parent_range"][1]),
                "children_file": str(shard_dir / f"{shard_id}.g6"),
                "children_written": int(info["children_written"]),
                "children_file_sha256": info["children_file_sha256"],
                "parent_sha256_in_manifest": info["inputs_sha256"][info["parent_file"]],
                "forbidden_sha256_in_manifest": info["inputs_sha256"][str(DEFAULT_FORBIDDEN)],
                "udenum_sha256_in_manifest": info["software_sha256"]["udenum"],
                "manifest": str(manifest_path),
                "udenum_parents_processed": int(stats["parents_processed"]),
                "regions": regions,
            })
    shards.sort(key=lambda s: (s["n"], s["m"], s["start"]))
    return shards


def region_d(shard: dict, index: int) -> int:
    for r in shard["regions"]:
        if r["a"] <= index < r["b"]:
            return r["d"]
    raise ValueError("index outside parent file")


# ---------------------------------------------------------------- worker side
_PATTERN_CACHE: dict[str, list] = {}
_PARENT_CACHE: dict[str, list[str]] = {}


def patterns_for(forbidden_path: str) -> list:
    if forbidden_path not in _PATTERN_CACHE:
        if Path(forbidden_path) == DEFAULT_FORBIDDEN:
            _PATTERN_CACHE[forbidden_path] = list(enum2.PATTERNS)
        else:
            raw = json.loads(Path(forbidden_path).read_text())
            graphs = []
            for edges in raw:
                order = 1 + max(max(e) for e in edges)
                adj = [0] * order
                for x, y in edges:
                    adj[x] |= 1 << y
                    adj[y] |= 1 << x
                graphs.append(enum2.Graph(tuple(adj)))
            _PATTERN_CACHE[forbidden_path] = enum2.make_patterns(graphs)
    return _PATTERN_CACHE[forbidden_path]


def parents_for(parent_file: str) -> list[str]:
    if parent_file not in _PARENT_CACHE:
        _PARENT_CACHE.clear()
        _PARENT_CACHE[parent_file] = read_records(Path(parent_file))
    return _PARENT_CACHE[parent_file]


def flip_edge(code: str, i: int, j: int) -> tuple[str, str]:
    """Flip edge {i, j} of a graph6 record; return (raw mutated g6, canonical mutated g6)."""
    g = enum2.graph6_decode(code)
    adj = list(g.adj)
    adj[i] ^= 1 << j
    adj[j] ^= 1 << i
    mutated = enum2.Graph(tuple(adj))
    return enum2.graph6_encode(mutated), enum2.canonical_g6(mutated)


def recover_parent(code: str) -> str:
    """Canonical graph6 of G minus its first minimum-degree vertex in canonical order.

    The record is canonical, so canonical position i is vertex i and the first minimum-degree
    vertex in canonical order is the smallest-index one (any other choice nauty could make is
    an automorphic image, which gives an isomorphic parent).
    """
    g = enum2.graph6_decode(code)
    degrees = [g.degree(v) for v in range(g.n)]
    w = degrees.index(min(degrees))
    keep = [v for v in range(g.n) if v != w]
    adj = []
    for v in keep:
        row = 0
        for j, u in enumerate(keep):
            if (g.adj[v] >> u) & 1:
                row |= 1 << j
        adj.append(row)
    return enum2.canonical_g6(enum2.Graph(tuple(adj)))


def work(unit: dict) -> dict:
    """One chunk of one shard: replay parents [a, b) of the shard's parent file."""
    t0 = time.perf_counter()
    patterns = patterns_for(unit["forbidden"])
    records = parents_for(unit["parent_file"])
    a, b = unit["a"], unit["b"]
    codes = list(records[a:b])
    mutation = unit.get("mutation")
    mutated_info = None
    if mutation is not None and a <= mutation["record"] < b:
        raw, canonical = flip_edge(codes[mutation["record"] - a], mutation["i"], mutation["j"])
        mutated_info = {"record": mutation["record"], "original": codes[mutation["record"] - a],
                        "flipped_raw": raw, "flipped_canonical": canonical}
        codes[mutation["record"] - a] = canonical
    children: list[str] = []
    processed = 0
    for code in codes:
        parent = enum2.graph6_decode(code)
        if parent.n != unit["n"] - 1:
            raise ValueError(f"parent order {parent.n} != {unit['n'] - 1}")
        processed += 1
        children.extend(enum2.extend_parent(parent, unit["m"], patterns))
    return {"shard_id": unit["shard_id"], "a": a, "b": b, "parents": processed,
            "children_raw": children, "seconds": time.perf_counter() - t0,
            "mutated": mutated_info}


# ---------------------------------------------------------------- restriction of udenum output
def restrict_udenum(shard: dict, a: int, b: int, lines: list[str]) -> dict:
    """Lines of the udenum shard file generated by parents [a, b) (see module docstring)."""
    records = parents_for(shard["parent_file"])
    index_of = {records[i]: i for i in range(shard["start"], shard["end"])}
    cache: dict[int, int] = {}

    def parent_index(line_no: int) -> int:
        if line_no not in cache:
            parent = recover_parent(lines[line_no])
            if parent not in index_of:
                raise RuntimeError(f"{shard['shard_id']} line {line_no}: recovered parent {parent} "
                                   f"is not a parent record of this shard")
            cache[line_no] = index_of[parent]
        return cache[line_no]

    whole = (a == shard["start"] and b == shard["end"])
    if whole:
        block_lo, block_hi = 0, len(lines)
        recovered = 0
        if lines:  # cheap boundary sanity check
            parent_index(0)
            parent_index(len(lines) - 1)
            recovered = 2
    else:
        # first line with parent >= a  (parent index is non-decreasing in line order)
        lo, hi = 0, len(lines)
        while lo < hi:
            mid = (lo + hi) // 2
            if parent_index(mid) < a:
                lo = mid + 1
            else:
                hi = mid
        block_lo = lo
        block_hi = block_lo
        while block_hi < len(lines) and parent_index(block_hi) < b:
            block_hi += 1
        recovered = len(cache)
        # verify every block line's parent is in [a, b), and the neighbours are outside
        previous = -1
        for i in range(block_lo, block_hi):
            p = parent_index(i)
            if not (a <= p < b):
                raise RuntimeError(f"{shard['shard_id']} line {i}: parent {p} outside [{a},{b})")
            if p < previous:
                raise RuntimeError(f"{shard['shard_id']} line {i}: parent order not monotone")
            previous = p
        if block_lo > 0 and parent_index(block_lo - 1) >= a:
            raise RuntimeError("block start is wrong")
        if block_hi < len(lines) and parent_index(block_hi) < b:
            raise RuntimeError("block end is wrong")
        recovered = len(cache)
    return {"lines": lines[block_lo:block_hi], "block": [block_lo, block_hi],
            "recovered_parents": recovered, "whole": whole}


# ---------------------------------------------------------------- driver side
def make_units(plan: list[dict], forbidden: str, mutation: dict | None = None) -> list[dict]:
    units = []
    for p in plan:
        for a in range(p["a"], p["b"], p["chunk"]):
            units.append({"shard_id": p["shard_id"], "parent_file": p["parent_file"],
                          "a": a, "b": min(a + p["chunk"], p["b"]), "n": p["n"], "m": p["m"],
                          "forbidden": forbidden,
                          "mutation": mutation if (mutation and mutation["shard_id"] == p["shard_id"]) else None})
    return units


def compare_range(s: dict, a: int, b: int, chunk_results: list[dict]) -> dict:
    parents = sum(r["parents"] for r in chunk_results)
    raw = [c for r in chunk_results for c in r["children_raw"]]
    enum2_set = set(raw)
    seconds = sum(r["seconds"] for r in chunk_results)
    lines = read_records(Path(s["children_file"]))
    restricted = restrict_udenum(s, a, b, lines)
    udenum_lines = restricted["lines"]
    udenum_set = set(udenum_lines)
    only_udenum = sorted(udenum_set - enum2_set)
    only_enum2 = sorted(enum2_set - udenum_set)
    identical = (not only_udenum and not only_enum2 and len(udenum_lines) == len(udenum_set)
                 and parents == b - a and len(lines) == s["children_written"])
    return {
        "shard_id": s["shard_id"], "cell": s["cell"], "n": s["n"], "m": s["m"],
        "shard_range": [s["start"], s["end"]], "range": [a, b], "whole_shard": restricted["whole"],
        "d_values": sorted({region_d(s, i) for i in (a, b - 1)}),
        "parents_replayed": parents,
        "udenum_children": len(udenum_lines), "udenum_distinct": len(udenum_set),
        "udenum_block": restricted["block"], "udenum_shard_lines": len(lines),
        "udenum_manifest_children_written": s["children_written"],
        "udenum_recovered_parents": restricted["recovered_parents"],
        "enum2_children_raw": len(raw), "enum2_children": len(enum2_set),
        "only_udenum": len(only_udenum), "only_enum2": len(only_enum2),
        "identical": identical,
        "only_udenum_first20": only_udenum[:20], "only_enum2_first20": only_enum2[:20],
        "enum2_cpu_seconds": round(seconds, 3),
        "children_file_sha256": sha256(Path(s["children_file"])),
        "children_file_sha256_matches_manifest": sha256(Path(s["children_file"])) == s["children_file_sha256"],
        "mutated": [r["mutated"] for r in chunk_results if r.get("mutated")],
    }


def per_cell_table(entries: list[dict]) -> list[dict]:
    cells: dict[str, dict] = {}
    for e in entries:
        c = cells.setdefault(e["cell"], {"cell": e["cell"], "shards": 0, "shards_in_cell": 0,
                                         "parents_replayed": 0, "parents_in_cell": 0,
                                         "udenum_children": 0, "enum2_children": 0,
                                         "only_udenum": 0, "only_enum2": 0, "identical": True,
                                         "enum2_cpu_seconds": 0.0, "d_values": set()})
        c["shards"] += 1
        c["parents_replayed"] += e["parents_replayed"]
        c["udenum_children"] += e["udenum_children"]
        c["enum2_children"] += e["enum2_children"]
        c["only_udenum"] += e["only_udenum"]
        c["only_enum2"] += e["only_enum2"]
        c["identical"] = c["identical"] and e["identical"]
        c["enum2_cpu_seconds"] += e["enum2_cpu_seconds"]
        c["d_values"].update(e["d_values"])
    rows = [cells[k] for k in sorted(cells, key=lambda x: tuple(int(v) for v in x.split("-")))]
    for r in rows:
        r["d_values"] = sorted(r["d_values"])
    return rows


def print_table(rows: list[dict]) -> None:
    print("| cell | shards replayed / in cell | parents replayed / in cell | d | udenum children | enum2 children | only udenum | only enum2 | identical | enum2 cpu s |")
    print("|---|---:|---:|---|---:|---:|---:|---:|---|---:|")
    for c in rows:
        print(f"| {c['cell']} | {c['shards']} / {c['shards_in_cell']} | {c['parents_replayed']} / {c['parents_in_cell']} | "
              f"{','.join(map(str, c['d_values']))} | {c['udenum_children']} | "
              f"{c['enum2_children']} | {c['only_udenum']} | {c['only_enum2']} | "
              f"{'yes' if c['identical'] else 'NO'} | {c['enum2_cpu_seconds']:.0f} |")


def verify_inputs(shards: list[dict], forbidden: Path) -> dict:
    """Hash every parent file and the forbidden list once; compare with the manifests."""
    report = {"parent_files": {}, "forbidden": {"path": str(forbidden), "sha256": sha256(forbidden)},
              "udenum": {"path": str(ROOT / "enum" / "udenum"), "sha256": sha256(ROOT / "enum" / "udenum")},
              "enum2.py": {"path": str(ENUM2_DIR / "enum2.py"), "sha256": sha256(ENUM2_DIR / "enum2.py")},
              "replay.py": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
              "mismatches": []}
    for s in shards:
        pf = s["parent_file"]
        if pf not in report["parent_files"]:
            report["parent_files"][pf] = {"sha256": sha256(Path(pf)), "records": len(read_records(Path(pf)))}
        if report["parent_files"][pf]["sha256"] != s["parent_sha256_in_manifest"]:
            report["mismatches"].append(f"parent hash mismatch for {s['shard_id']}")
        if report["forbidden"]["sha256"] != s["forbidden_sha256_in_manifest"]:
            report["mismatches"].append(f"forbidden hash mismatch for {s['shard_id']}")
        if report["udenum"]["sha256"] != s["udenum_sha256_in_manifest"]:
            report["mismatches"].append(f"udenum hash mismatch for {s['shard_id']}")
    return report


def build_plan(shards: list[dict], seed: int, lengths: dict[int, int], whole_max: int) -> list[dict]:
    """Seeded sample: every shard gets one random sub-range whose length depends on the d of
    its start region; shards with at most whole_max parents are replayed whole."""
    rng = random.Random(seed)
    plan = []
    for s in shards:
        size = s["end"] - s["start"]
        d = region_d(s, s["start"])
        if size <= whole_max:
            a, b = s["start"], s["end"]
        else:
            L = min(lengths[d], size)
            a = rng.randrange(s["start"], s["end"] - L + 1)
            b = a + L
        d_at_a = region_d(s, a)
        rate = RATE[(d_at_a, s["n"] - 1)]
        frac = s["udenum_parents_processed"] / size
        est = (b - a) * frac * rate
        plan.append({"shard_id": s["shard_id"], "cell": s["cell"], "n": s["n"], "m": s["m"],
                     "parent_file": s["parent_file"], "a": a, "b": b, "d": d_at_a,
                     "chunk": max(5, (b - a) // 4), "estimated_cpu_seconds": round(est, 1)})
    return plan


def order_plan(plan: list[dict]) -> list[dict]:
    """Whole tiny shards first, then round-robin across cells so coverage arrives early."""
    by_cell: dict[str, list[dict]] = {}
    for p in plan:
        by_cell.setdefault(p["cell"], []).append(p)
    ordered = []
    while any(by_cell.values()):
        for cell in list(by_cell):
            if by_cell[cell]:
                ordered.append(by_cell[cell].pop(0))
    return ordered


def cmd_bench(args: argparse.Namespace) -> None:
    unit = {"shard_id": "bench", "parent_file": args.parent_file, "a": args.start, "b": args.end,
            "n": args.n, "m": args.m, "forbidden": str(DEFAULT_FORBIDDEN)}
    r = work(unit)
    raw = r["children_raw"]
    print(json.dumps({"parents": r["parents"], "children_raw": len(raw), "children": len(set(raw)),
                      "seconds": round(r["seconds"], 3),
                      "parents_per_second": round(r["parents"] / r["seconds"], 2)}))


def lengths_from(args: argparse.Namespace) -> dict[int, int]:
    return {int(k): int(v) for k, v in (kv.split("=") for kv in args.lengths.split(","))}


def cmd_plan(args: argparse.Namespace) -> None:
    shards = load_shards(Path(args.dag), args.cells.split(","))
    plan = order_plan(build_plan(shards, args.seed, lengths_from(args), args.whole_max))
    total = sum(p["estimated_cpu_seconds"] for p in plan)
    out = Path(args.workdir) / f"plan-{args.tag}.json"
    out.write_text(json.dumps({"seed": args.seed, "lengths": lengths_from(args), "whole_max": args.whole_max,
                               "cells": args.cells.split(","), "shards": len(plan),
                               "parents": sum(p["b"] - p["a"] for p in plan),
                               "estimated_cpu_seconds": round(total), "plan": plan}, indent=1) + "\n")
    print(f"plan: {len(plan)} shards, {sum(p['b'] - p['a'] for p in plan)} parents, "
          f"estimated {total:.0f} cpu-seconds (~{total / 4 / 60:.0f} min on 4 workers); wrote {out}")


def run_plan(args: argparse.Namespace, plan: list[dict], shards_by_id: dict[str, dict],
             forbidden: Path, mutation: dict | None, tag: str) -> list[dict]:
    units = make_units(plan, str(forbidden), mutation)
    pending = {p["shard_id"]: sum(1 for u in units if u["shard_id"] == p["shard_id"]) for p in plan}
    got: dict[str, list[dict]] = {}
    ranges = {p["shard_id"]: (p["a"], p["b"]) for p in plan}
    jsonl = Path(args.workdir) / f"shards-{tag}.jsonl"
    jsonl.write_text("")
    entries: list[dict] = []
    t0 = time.time()
    print(f"[{tag}] {len(plan)} shards, {sum(p['b'] - p['a'] for p in plan)} parents, {len(units)} units, "
          f"{args.workers} workers", flush=True)

    def finish(shard_id: str) -> None:
        a, b = ranges[shard_id]
        entry = compare_range(shards_by_id[shard_id], a, b, got.pop(shard_id))
        entries.append(entry)
        with jsonl.open("a") as stream:
            stream.write(json.dumps(entry) + "\n")
        print(f"[{tag} {time.time() - t0:6.0f}s] {shard_id} [{a},{b}) parents={entry['parents_replayed']} "
              f"udenum={entry['udenum_children']} enum2={entry['enum2_children']} "
              f"identical={entry['identical']} ({len(entries)}/{len(plan)})", flush=True)

    if args.workers <= 1:
        iterator = map(work, units)
    else:
        pool = Pool(processes=args.workers)
        iterator = pool.imap_unordered(work, units)
    try:
        for r in iterator:
            got.setdefault(r["shard_id"], []).append(r)
            pending[r["shard_id"]] -= 1
            if pending[r["shard_id"]] == 0:
                finish(r["shard_id"])
    finally:
        if args.workers > 1:
            pool.terminate()
            pool.join()
    return entries


def write_summary(args: argparse.Namespace, tag: str, entries: list[dict], shards: list[dict],
                  extra: dict) -> dict:
    table = per_cell_table(entries)
    all_shards = load_shards(Path(args.dag), ALL_CELLS.split(","))
    for row in table:
        row["shards_in_cell"] = sum(1 for s in all_shards if s["cell"] == row["cell"])
        row["parents_in_cell"] = sum(s["end"] - s["start"] for s in all_shards if s["cell"] == row["cell"])
    print_table(table)
    summary = {
        "tag": tag, "dag": str(args.dag), "host": os.uname().nodename,
        "shards_total": len(entries), "shards_identical": sum(1 for e in entries if e["identical"]),
        "parents_replayed": sum(e["parents_replayed"] for e in entries),
        "udenum_children": sum(e["udenum_children"] for e in entries),
        "enum2_children": sum(e["enum2_children"] for e in entries),
        "all_identical": all(e["identical"] for e in entries) and bool(entries),
        "per_cell": table, "per_shard": entries, **extra,
    }
    out = Path(args.workdir) / f"results-{tag}.json"
    out.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"all_identical={summary['all_identical']}; wrote {out} ({out.stat().st_size} bytes)")
    return summary


def plan_and_shards(args: argparse.Namespace) -> tuple[list[dict], dict[str, dict], dict]:
    shards = load_shards(Path(args.dag), args.cells.split(","))
    shards_by_id = {s["shard_id"]: s for s in shards}
    if args.plan_file:
        plan_doc = json.loads(Path(args.plan_file).read_text())
        plan = plan_doc["plan"]
        selection = {"mode": "plan", "plan_file": args.plan_file, "seed": plan_doc.get("seed"),
                     "lengths": plan_doc.get("lengths"), "whole_max": plan_doc.get("whole_max")}
    elif args.ranges:
        plan = []
        for spec in args.ranges.split(","):
            shard_id, a, b = spec.split(":")
            s = shards_by_id[shard_id]
            plan.append({"shard_id": shard_id, "cell": s["cell"], "n": s["n"], "m": s["m"],
                         "parent_file": s["parent_file"], "a": int(a), "b": int(b),
                         "d": region_d(s, int(a)), "chunk": max(5, (int(b) - int(a)) // 4)})
        selection = {"mode": "ranges", "ranges": args.ranges}
    else:
        plan = [{"shard_id": s["shard_id"], "cell": s["cell"], "n": s["n"], "m": s["m"],
                 "parent_file": s["parent_file"], "a": s["start"], "b": s["end"],
                 "d": region_d(s, s["start"]), "chunk": 500} for s in shards]
        selection = {"mode": "all"}
    selection["shards"] = [(p["shard_id"], p["a"], p["b"]) for p in plan]
    return plan, shards_by_id, selection


def cmd_replay(args: argparse.Namespace, forbidden: Path | None = None, mutation: dict | None = None,
               tag: str | None = None) -> dict:
    forbidden = forbidden or DEFAULT_FORBIDDEN
    tag = tag or args.tag
    plan, shards_by_id, selection = plan_and_shards(args)
    used = [shards_by_id[p["shard_id"]] for p in plan]
    t0 = time.time()
    inputs = verify_inputs(used, DEFAULT_FORBIDDEN)
    if forbidden != DEFAULT_FORBIDDEN:
        inputs["forbidden_used"] = {"path": str(forbidden), "sha256": sha256(forbidden)}
    entries = run_plan(args, plan, shards_by_id, forbidden, mutation, tag)
    wall = time.time() - t0
    extra = {"selection": selection, "inputs": inputs, "workers": args.workers,
             "wall_seconds": round(wall, 1), "mutation": mutation,
             "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
             "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return write_summary(args, tag, entries, used, extra)


def cmd_summarize(args: argparse.Namespace) -> None:
    entries = [json.loads(line) for line in Path(args.jsonl).read_text().splitlines() if line.strip()]
    shards = load_shards(Path(args.dag), args.cells.split(","))
    write_summary(args, args.tag, entries, shards, {"selection": {"mode": "summarize", "jsonl": args.jsonl}})


def cmd_control_a(args: argparse.Namespace) -> None:
    shard_id, a, b = args.ranges.split(":")
    i, j = (int(x) for x in args.edge.split(","))
    mutation = {"shard_id": shard_id, "record": args.record, "i": i, "j": j}
    summary = cmd_replay(args, mutation=mutation, tag=args.tag)
    e = summary["per_shard"][0]
    print(json.dumps({"control": "a", "shard": e["shard_id"], "range": e["range"], "mutated": e["mutated"],
                      "identical": e["identical"], "only_udenum": e["only_udenum"],
                      "only_enum2": e["only_enum2"], "red": not e["identical"]}))


def cmd_control_b(args: argparse.Namespace) -> None:
    raw = json.loads(DEFAULT_FORBIDDEN.read_text())
    dropped = raw[args.drop_index]
    kept = [g for k, g in enumerate(raw) if k != args.drop_index]
    copy = Path(args.workdir) / f"forbidden-73-drop{args.drop_index}.json"
    copy.write_text(json.dumps(kept))
    summary = cmd_replay(args, forbidden=copy, tag=args.tag)
    extra = sum(e["only_enum2"] for e in summary["per_shard"])
    missing = sum(e["only_udenum"] for e in summary["per_shard"])
    print(json.dumps({"control": "b", "dropped_index": args.drop_index,
                      "dropped_graph": {"vertices": 1 + max(max(e) for e in dropped), "edges": len(dropped)},
                      "forbidden_copy": str(copy), "forbidden_copy_sha256": sha256(copy),
                      "shards": summary["shards_total"], "extra_enum2_children": extra,
                      "missing_from_enum2": missing, "red": extra > 0}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--dag", default=str(DEFAULT_DAG))
        p.add_argument("--cells", default=ALL_CELLS)
        p.add_argument("--plan-file", default="")
        p.add_argument("--ranges", default="", help="shard_id:a:b[,...] explicit sub-ranges")
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--workdir", default=str(HERE))
        p.add_argument("--tag", default="replay")

    p = sub.add_parser("bench")
    p.add_argument("--parent-file", required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--m", type=int, required=True)
    p.set_defaults(function=cmd_bench)

    p = sub.add_parser("plan")
    common(p)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--lengths", default="0=500,1=500,2=120,3=40,4=150", help="sub-range length per d")
    p.add_argument("--whole-max", type=int, default=400, help="shards with at most this many parents are replayed whole")
    p.set_defaults(function=cmd_plan)

    p = sub.add_parser("replay")
    common(p)
    p.set_defaults(function=cmd_replay)

    p = sub.add_parser("summarize")
    common(p)
    p.add_argument("--jsonl", required=True)
    p.set_defaults(function=cmd_summarize)

    p = sub.add_parser("control-a")
    common(p)
    p.add_argument("--record", type=int, required=True, help="absolute record index in the parent file")
    p.add_argument("--edge", required=True, help="i,j edge to flip in that record")
    p.set_defaults(function=cmd_control_a)

    p = sub.add_parser("control-b")
    common(p)
    p.add_argument("--drop-index", type=int, required=True, help="index into forbidden-74.json to remove")
    p.set_defaults(function=cmd_control_b)

    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
