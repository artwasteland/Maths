#!/usr/bin/env python3
"""Mode 398 identity at order 10, where the 324 first act: every graph on 9 and 10 vertices.

The optimized udenum (and its test builds: the two switch-forcing ones of speed398-identity.py, and
two that run the uncovered-set tracking on every order, with direct tests from 16 and from 64
uncovered sets) against
the CURRENT Mode 398 binary (test-398/base398/udenum), byte for byte and counter for counter:

  generator  for every m = 0..45, --n 10 --m m on (a) the 11,803 74-free (= 398-free) 9-vertex
             graphs of REPORT-398 4.3 and (b) ALL 274,668 graphs on 9 vertices (geng -q 9,
             canonically relabelled with nauty-labelg), most of which contain a forbidden graph
             (--parent-sets and --m-range select a part: (b) at m ~ 20..27 takes tens of minutes per
             edge count and binary, since it writes every graph on 10 vertices it reaches);
  filter     for every m = 0..45, --filter --n 10 --m m on geng -q 10 m:m: all 12,005,168 graphs on
             10 vertices (the seed path of the u(23) contract).
Also, as in brute10.py/seeds10.py: the new generator's output from (a) and the new filter's output,
each relabelled with nauty-labelg and sorted, must equal brute10.py's brute398 (105,680 graphs,
decided by GP-10's unmodified matcher), when --brute-work is given.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from speed398lib import (BASE398_SHA256, BASE398_UDENUM, NEW_SOURCE, NEW_UDENUM, SCRATCH, build_variant, compare_runs,
                         g6_lines, run_udenum, sha256, write_lines)


def labelg_sorted(src: Path, dst: Path) -> list[bytes]:
    tmp = dst.with_suffix(".labelg.g6")
    subprocess.run(["nice", "-n", "15", "nauty-labelg", "-q", str(src), str(tmp)], check=True)
    lines = sorted(g6_lines(tmp))
    write_lines(dst, lines)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brute-work", type=Path, default=None,
                    help="brute10.py's work directory (free9.g6, brute398.g6, geng-9.g6)")
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-brute10")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-brute10.json")
    ap.add_argument("--no-variants", action="store_true")
    ap.add_argument("--parent-sets", default="free9,all9", help="which 9-vertex parent sets drive the generator")
    ap.add_argument("--m-range", default="0:45", help="edge counts FROM:TO of the generator runs (inclusive)")
    ap.add_argument("--skip-filter", action="store_true", help="omit the --filter pass over all graphs on 10 vertices")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    if sha256(BASE398_UDENUM) != BASE398_SHA256:
        print("the reference binary is not the pinned Mode 398 binary")
        return 2
    binaries = {"new": NEW_UDENUM}
    if not a.no_variants:
        binaries["new-K1"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-K1", ["RESTRICTED_SWITCH_CANDIDATES=1"])
        binaries["new-Kinf"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-Kinf",
                                             ["RESTRICTED_SWITCH_CANDIDATES=4000000000"])
        # the pattern path's uncovered-set tracking and direct tests, which production runs from 15
        # vertices, on these 9-vertex parents; and with direct tests from 64 uncovered sets down
        binaries["new-U1"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-U1", ["UNCOVERED_MIN_ORDER=1"])
        binaries["new-U1D64"] = build_variant(NEW_SOURCE, w / "bin" / "udenum-U1D64",
                                              ["UNCOVERED_MIN_ORDER=1", "UNCOVERED_DIRECT=64"])
    t0 = time.monotonic()
    # parents on 9 vertices
    geng9 = a.brute_work / "geng-9.g6" if a.brute_work and (a.brute_work / "geng-9.g6").exists() else w / "geng-9.g6"
    if not geng9.exists():
        with open(geng9, "wb") as out:
            subprocess.run(["nice", "-n", "15", "nauty-geng", "-q", "9"], stdout=out, check=True)
    all9 = w / "all9.g6"
    subprocess.run(["nice", "-n", "15", "nauty-labelg", "-q", str(geng9), str(all9)], check=True)
    free9 = a.brute_work / "free9.g6" if a.brute_work else None
    if free9 is None or not free9.exists():
        # 74-free = 398-free on 9 vertices (the 324 have 10); decided by the reference --filter
        by_m: dict[int, list[bytes]] = {}
        from speed398lib import g6_order_size
        for g in g6_lines(all9):
            by_m.setdefault(g6_order_size(g)[1], []).append(g)
        kept = []
        for m, gs in sorted(by_m.items()):
            src = w / f"all9-{m}.g6"
            write_lines(src, gs)
            r = run_udenum(BASE398_UDENUM, src, 9, m, w / f"free9-{m}.g6", extra=["--filter"])
            kept += g6_lines(r["output"])
        free9 = w / "free9.g6"
        write_lines(free9, kept)
    sets = {k: v for k, v in (("free9", free9), ("all9", all9)) if k in a.parent_sets.split(",")}
    m_from, m_to = (int(x) for x in a.m_range.split(":"))
    print(f"parents: free9 {len(g6_lines(free9))} ({sha256(free9)[:16]}), all9 {len(g6_lines(all9))}", flush=True)
    rows = []
    ok = True
    gen_union: dict[str, list[bytes]] = {k: [] for k in binaries}
    for pname, pfile in sets.items():
        for m in range(m_from, m_to + 1):
            tag = f"gen-{pname}-{m}"
            ref = run_udenum(BASE398_UDENUM, pfile, 10, m, w / "out" / f"{tag}.base.g6")
            row = {"kind": "generator", "parents": pname, "m": m, "children": ref["stats"]["children_written"],
                   "bad_sets": ref["stats"]["bad_sets"], "cpu_ref": ref["cpu"], "output_sha256": sha256(ref["output"]),
                   "candidates": {}}
            for k, b in binaries.items():
                got = run_udenum(b, pfile, 10, m, w / "out" / f"{tag}.{k}.g6")
                p = compare_runs(ref, got)
                row["candidates"][k] = {"identical": not p, "problems": p, "cpu": got["cpu"]}
                ok = ok and not p
                if pname == "free9":
                    gen_union[k] += g6_lines(got["output"])
                if not p:
                    Path(got["output"]).unlink()
            if pname == "all9":
                Path(ref["output"]).unlink()
            rows.append(row)
        n_rows = [r for r in rows if r["parents"] == pname]
        print(f"generator on {pname}: {sum(all(v['identical'] for v in r['candidates'].values()) for r in n_rows)} of "
              f"{len(n_rows)} edge counts identical; {sum(r['children'] for r in n_rows)} children, "
              f"{sum(r['bad_sets'] for r in n_rows)} bad sets; cpu ref {sum(r['cpu_ref'] for r in n_rows):.1f} s, "
              f"new {sum(r['candidates']['new']['cpu'] or 0 for r in n_rows):.1f} s", flush=True)
    filter_union: list[bytes] = []
    total10 = 0
    for m in ([] if a.skip_filter else range(46)):
        src = w / f"geng-10-{m}.g6"
        with open(src, "wb") as out:
            subprocess.run(["nice", "-n", "15", "nauty-geng", "-q", "10", f"{m}:{m}"], stdout=out, check=True)
        count = sum(1 for _ in open(src, "rb"))
        total10 += count
        ref = run_udenum(BASE398_UDENUM, src, 10, m, w / "out" / f"filter-{m}.base.g6", extra=["--filter"])
        row = {"kind": "filter", "m": m, "graphs": count, "kept": ref["stats"]["children_written"],
               "cpu_ref": ref["cpu"], "candidates": {}}
        for k, b in binaries.items():
            got = run_udenum(b, src, 10, m, w / "out" / f"filter-{m}.{k}.g6", extra=["--filter"])
            p = compare_runs(ref, got)
            row["candidates"][k] = {"identical": not p, "problems": p, "cpu": got["cpu"]}
            ok = ok and not p
            if k == "new":
                filter_union += g6_lines(got["output"])
        rows.append(row)
        src.unlink()
    f_rows = [r for r in rows if r["kind"] == "filter"]
    print(f"filter: {sum(all(v['identical'] for v in r['candidates'].values()) for r in f_rows)} of {len(f_rows)} edge "
          f"counts identical over {total10} graphs; kept {sum(r['kept'] for r in f_rows)}; cpu ref "
          f"{sum(r['cpu_ref'] for r in f_rows):.1f} s, new {sum(r['candidates']['new']['cpu'] or 0 for r in f_rows):.1f} s",
          flush=True)
    checks = {"all_runs_identical": ok}
    if not a.skip_filter:
        checks["graphs_on_10_vertices"] = total10 == 12005168
    if a.brute_work and (a.brute_work / "brute398.g6").exists() and not a.skip_filter and "free9" in sets \
            and (m_from, m_to) == (0, 45):
        brute398 = g6_lines(a.brute_work / "brute398.g6")
        raw = w / "gen-new-free9.raw.g6"
        write_lines(raw, gen_union["new"])
        checks["new_generator_equals_brute398"] = labelg_sorted(raw, w / "gen-new-free9.sorted.g6") == brute398
        raw = w / "filter-new.raw.g6"
        write_lines(raw, filter_union)
        checks["new_filter_equals_brute398"] = labelg_sorted(raw, w / "filter-new.sorted.g6") == brute398
        checks["brute398_graphs"] = len(brute398)
    for k, v in checks.items():
        print(f"{k}: {v}", flush=True)
    passed = all(v for k, v in checks.items() if k != "brute398_graphs")
    summary = {"reference": str(BASE398_UDENUM), "candidates": {k: sha256(b) for k, b in binaries.items()},
               "checks": checks, "rows": rows, "pass": passed, "seconds": round(time.monotonic() - t0, 1)}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print("RESULT:", "PASS" if passed else "FAIL", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
