#!/usr/bin/env python3
"""enum2's fast engine against enum2's reference engine (the original code), on real hosts.

The fast engine is new code (rooted-pattern classes, a shared search trie, pruning by known
smaller bad sets and by surviving candidate neighbourhoods); the reference engine is the
u(22) enum2 code, unchanged, that replayed 92 of 92 production shards.  For hosts sampled
(seed 20260925) from real parent files of the u(22) run (10- and 11-vertex hosts) and of
the unpruned (18,46) DAG (12- to 16-vertex hosts), with the 74 and with the 398:

  F1  bad family: fast (shared) == fast (per plan) == the reference's minimal family
      restricted to the sets T with |T u required| <= d, for the cell's own (d, required)
      and for random variants (random d, random required set);
  F2  good neighbourhoods: fast good_candidates == the reference's child_neighborhoods, as
      LISTS (same order);
  F3  children: extend_parent fast == reference, as lists (same order, same multiplicity),
      for the cell's own target;
  F4  deciders: ContainmentTester == straightforward_contains on every host and child seen,
      on each host plus a random edge, and on structured cases that must come out one way:
      every member F_i contains exactly itself (tester.all(F_i) == [i]: the list is an
      antichain) and so do F_i plus a pendant vertex and F_i plus an isolated vertex; every
      F_i - x (vertex deleted) and F_i - e (edge deleted) contains NO member (each member is
      minimal); the reference backtracker re-decides a seeded sample of these.

Red controls (each must make its check fail on this data):
  X1  a fast engine with one rooted class removed (the class with the most images on the
      first hosts) -> F1/F2 mismatch;
  X2  the reference family with one set removed -> F1 mismatch;
  X3  a ContainmentTester without member j, on F_j itself, for j = K4, K_{2,3}, the first and
      the last of the 324 -> must call F_j free while the reference finds F_j.
      (The first version of X3, "without K4, on the hosts plus a random edge", could not go
      red: no such graph contained K4 alone.  It was replaced by this one.)
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

from v398lib import ORIG_DAG_F12, REPO_SUP, RUNS, dump, enum2, software

SOURCES = ([(ORIG_DAG_F12 / "_parents" / f"{c}.g6", c) for c in
            ("11-17", "11-18", "11-20", "11-21", "11-22", "11-23", "12-20", "12-21", "12-22", "12-24",
             "12-25")] +
           [(REPO_SUP / "_parents" / f"{c}.g6", c) for c in
            ("13-28", "13-29", "14-31", "14-32", "15-35", "16-39", "17-43")])


def guard(h: enum2.Graph, m: int) -> tuple[int, int] | None:
    d = m - h.m
    degs = [h.degree(v) for v in range(h.n)]
    md = min(degs)
    if d < 0 or d > h.n or md < d - 1:
        return None
    req = 0
    if md == d - 1:
        for v in range(h.n):
            if degs[v] == md:
                req |= 1 << v
    if req.bit_count() > d:
        return None
    return d, req


def affordable(name: str, n: int, d: int) -> bool:
    """The reference engine assigns roots first over all host vertices (about n^|S| tuples
    per pattern), so its cost explodes with d; these limits keep one case under a minute."""
    if name == "74":
        return d <= (4 if n <= 11 else 3 if n <= 13 else 2)
    return d <= (3 if n <= 11 else 2)


def reference_family(h, patterns, d, req) -> list[int]:
    fam = enum2.bad_neighborhoods(h, patterns, d)
    return sorted((t for t in fam if (t | req).bit_count() <= d), key=lambda x: (x.bit_count(), x))


def reference_good(h, patterns, d, req) -> list[int]:
    return list(enum2.child_neighborhoods(h, d, patterns, req))


def _with(adj: list[int], extra: list[tuple[int, int]], order: int) -> enum2.Graph:
    a = list(adj) + [0] * (order - len(adj))
    for u, v in extra:
        a[u] |= 1 << v
        a[v] |= 1 << u
    return enum2.Graph(tuple(a))


def _minus_vertex(g: enum2.Graph, x: int) -> enum2.Graph:
    keep = [v for v in range(g.n) if v != x]
    return enum2.Graph(tuple(sum(1 << j for j, u in enumerate(keep) if g.adj[v] >> u & 1) for v in keep))


def decider_structure(fs: enum2.ForbiddenSet, rng: random.Random, reference_sample: int) -> dict:
    """Cases whose answer is known from the list's own structure (antichain of minimal graphs)."""
    tester = fs.tester
    positives, negatives, wrong = 0, 0, []
    ref_cases = []
    for i, f in enumerate(fs.graphs):
        k = f.n
        cases = [("member", f, [i])]
        cases.append(("member+pendant", _with(list(f.adj), [(0, k)], k + 1), [i]))
        cases.append(("member+isolated", _with(list(f.adj), [], k + 1), [i]))
        for x in range(k):
            cases.append(("member-vertex", _minus_vertex(f, x), []))
        for u in range(k):
            for v in range(u + 1, k):
                if f.adj[u] >> v & 1:
                    a = list(f.adj)
                    a[u] &= ~(1 << v)
                    a[v] &= ~(1 << u)
                    cases.append(("member-edge", enum2.Graph(tuple(a)), []))
        for kind, g, want in cases:
            got = tester.all(g)
            if got != want:
                wrong.append({"member": i, "case": kind, "graph": enum2.graph6_encode(g), "tester_all": got,
                              "expected": want})
            if want:
                positives += 1
            else:
                negatives += 1
            ref_cases.append((i, kind, g, bool(want)))
    # the reference backtracker on a seeded sample of the same cases
    sample = rng.sample(ref_cases, min(reference_sample, len(ref_cases)))
    ref_wrong = []
    t0 = time.process_time()
    for i, kind, g, contains in sample:
        if enum2.f_free(g, fs.graphs) == contains:
            ref_wrong.append({"member": i, "case": kind, "graph": enum2.graph6_encode(g)})
    ref_seconds = time.process_time() - t0
    # X3: a tester without member j must call F_j free, while the reference finds it
    x3 = []
    picks = [j for j in (0, 1, 74, len(fs.graphs) - 1) if j < len(fs.graphs)]
    for j in picks:
        without = enum2.ContainmentTester([g for i, g in enumerate(fs.graphs) if i != j])
        f = fs.graphs[j]
        x3.append({"member": j, "order": f.n, "tester_without_j_calls_it_free": without.first(f) is None,
                   "reference_finds_it": not enum2.f_free(f, fs.graphs),
                   "went_red": without.first(f) is None and not enum2.f_free(f, fs.graphs)})
    return {"positives": positives, "negatives": negatives, "tester_wrong": wrong[:20],
            "tester_wrong_count": len(wrong), "reference_sample": len(sample), "reference_wrong": ref_wrong[:20],
            "reference_seconds": round(ref_seconds, 1), "X3": x3, "ok": not wrong and not ref_wrong}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference-sample", type=int, default=1500,
                    help="structured decider cases re-decided by the reference backtracker")
    ap.add_argument("--per-source", type=int, default=6)
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--budget", type=float, default=5400.0, help="seconds of reference-engine work per set")
    ap.add_argument("--summary", type=Path, default=RUNS / "engines.json")
    ap.add_argument("--sets", default="74,398")
    a = ap.parse_args()
    rng = random.Random(20260925)
    hosts = []
    for path, cell in SOURCES:
        codes = [x for x in path.read_text().split() if x]
        n, m = map(int, cell.split("-"))
        picked = rng.sample(codes, min(a.per_source, len(codes)))
        for code in picked:
            hosts.append((cell, m, code))
    rng.shuffle(hosts)
    out = {"software": software(), "hosts": len(hosts), "sets": {}}
    ok = True
    for name in a.sets.split(","):
        fs = enum2.load_forbidden_set(name)
        shared = fs.engine
        per_plan = enum2.PatternEngine(fs.patterns, share=False)
        stats = {"hosts": 0, "family_checks": 0, "family_mismatch": [], "good_checks": 0, "good_mismatch": [],
                 "children_checks": 0, "children_mismatch": [], "decider_checks": 0, "decider_mismatch": [],
                 "bad_sets_compared": 0, "good_neighbourhoods_compared": 0, "children_compared": 0,
                 "reference_seconds": 0.0, "fast_seconds": 0.0, "d_required_cases": {}}
        # X1: a fast engine without one rooted class (chosen below, after the first hosts)
        spent = 0.0
        x1_engine = None
        x1_red = False
        x2_red = False
        x3_red = False
        class_hits: dict[int, int] = {}
        for cell, m, code in hosts:
            if spent > a.budget:
                break
            h = enum2.graph6_decode(code)
            stats["hosts"] += 1
            cases = []
            g = guard(h, m)
            if g is not None:
                cases.append(("cell", g[0], g[1]))
            for _ in range(a.variants):
                d = rng.choice([2, 3, 4])
                size = rng.randrange(0, d)
                req = sum(1 << v for v in rng.sample(range(h.n), size))
                cases.append(("variant", d, req))
            for kind, d, req in cases:
                if not affordable(name, h.n, d):
                    stats["skipped_cases_cost"] = stats.get("skipped_cases_cost", 0) + 1
                    continue
                key = f"n={h.n},d={d},|req|={req.bit_count()}"
                stats["d_required_cases"][key] = stats["d_required_cases"].get(key, 0) + 1
                t0 = time.process_time()
                ref_f = reference_family(h, fs.patterns, d, req)
                ref_g = [x for x in reference_good(h, fs.patterns, d, req)]
                t1 = time.process_time()
                fast_f = shared.bad_family(h, d, req)
                fast_pp = per_plan.bad_family(h, d, req)
                fast_g = shared.good_candidates(h, d, req)
                t2 = time.process_time()
                spent += t1 - t0
                stats["reference_seconds"] += t1 - t0
                stats["fast_seconds"] += t2 - t1
                stats["family_checks"] += 1
                stats["good_checks"] += 1
                stats["bad_sets_compared"] += len(ref_f)
                stats["good_neighbourhoods_compared"] += len(ref_g)
                if not (fast_f == fast_pp == ref_f):
                    stats["family_mismatch"].append({"cell": cell, "host": code, "d": d, "required": req,
                                                     "ref": len(ref_f), "fast": len(fast_f), "per_plan": len(fast_pp)})
                if fast_g != ref_g:
                    stats["good_mismatch"].append({"cell": cell, "host": code, "d": d, "required": req,
                                                   "ref": len(ref_g), "fast": len(fast_g)})
                # X2 on the first non-empty reference family
                if not x2_red and ref_f:
                    x2_red = (ref_f[1:] != fast_f)
                # X1: choose the class with images on the first hosts, then test it
                if x1_engine is None and ref_f:
                    for plan in shared.plans:
                        if plan.s > d:
                            continue
                        probe = enum2.PatternEngine([fs.patterns[plan.members[0]]])
                        if probe.bad_family(h, d, req):
                            class_hits[plan.members[0]] = class_hits.get(plan.members[0], 0) + 1
                    if class_hits:
                        drop_first = max(class_hits, key=lambda k: (class_hits[k], -k))
                        drop = next(p for p in shared.plans if p.members[0] == drop_first)
                        x1_engine = enum2.PatternEngine([fs.patterns[i] for i in range(len(fs.patterns))
                                                         if i not in set(drop.members)])
                        stats["x1_dropped_class_members"] = list(drop.members)
                if x1_engine is not None and not x1_red:
                    x1_red = (x1_engine.good_candidates(h, d, req) != ref_g or
                              x1_engine.bad_family(h, d, req) != ref_f)
            if g is not None and affordable(name, h.n, g[0]):
                d, req = g
                t0 = time.process_time()
                ref_c = list(enum2.extend_parent(h, m, fs, engine="reference"))
                t1 = time.process_time()
                fast_c = list(enum2.extend_parent(h, m, fs, engine="fast"))
                spent += t1 - t0
                stats["children_checks"] += 1
                stats["children_compared"] += len(ref_c)
                if ref_c != fast_c:
                    stats["children_mismatch"].append({"cell": cell, "host": code, "ref": len(ref_c),
                                                       "fast": len(fast_c)})
                graphs_to_decide = [h] + [enum2.graph6_decode(x) for x in set(ref_c)]
            else:
                graphs_to_decide = [h]
            # F4 deciders, on the host, its children, and the host plus a random extra edge
            extra = list(h.adj)
            u, v = rng.sample(range(h.n), 2)
            extra[u] |= 1 << v
            extra[v] |= 1 << u
            graphs_to_decide.append(enum2.Graph(tuple(extra)))
            for gr in graphs_to_decide:
                stats["decider_checks"] += 1
                a1 = fs.tester.first(gr) is None
                a2 = enum2.f_free(gr, fs.graphs)
                if a1 != a2:
                    stats["decider_mismatch"].append({"graph": enum2.graph6_encode(gr), "tester_free": a1,
                                                      "reference_free": a2})
        # F4 structured cases (members, members + a vertex, members - a vertex, members - an edge)
        structured = decider_structure(fs, rng, a.reference_sample)
        stats["decider_structured"] = structured
        x3 = structured["X3"]
        x3_red = bool(x3) and all(r["went_red"] for r in x3)
        stats["reference_seconds"] = round(stats["reference_seconds"], 1)
        stats["fast_seconds"] = round(stats["fast_seconds"], 1)
        stats["red_controls"] = {"X1_fast_engine_missing_one_rooted_class": x1_red,
                                 "X2_reference_family_minus_one_set": x2_red,
                                 "X3_tester_without_member_j_on_F_j": x3_red}
        if not structured["ok"]:
            stats["decider_mismatch"].append({"structured": "failed"})
        set_ok = (not stats["family_mismatch"] and not stats["good_mismatch"] and not stats["children_mismatch"]
                  and not stats["decider_mismatch"] and x1_red and x2_red and x3_red)
        stats["pass"] = set_ok
        ok = ok and set_ok
        out["sets"][name] = stats
        print(f"set {name}: {json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in stats.items()})}",
              flush=True)
        dump(a.summary, out)
    out["pass"] = ok
    dump(a.summary, out)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
