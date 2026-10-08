#!/usr/bin/env python3
"""Mode 398 bad families, set for set and IN ORDER: the new code against the CURRENT Mode 398.

udenum's output depends on a parent's bad family only as a set (the domain is the d-sets it does
not cover) and through its size (the bad_sets counter).  Its order reaches the output only through
the test-only --mutation-drop-first-badset, and there only its first set (the run then usually
aborts at the first parent where that set mattered).  So the output identity of
speed398-identity.py cannot see the order of a family.  The new code claims the order anyway
(udenum.c: anchored_images_398 makes build_bad_family's additions in the same order;
build_restricted_bad_family_398 runs the old loop), and this check tests that claim directly.

Both sources, test-398/base398/udenum.c (the current Mode 398, unmodified) and the new
enum/udenum.c, get the same instrumentation by text substitution after the line where
process_parent finishes the family: one stderr line per processed parent,
"FAMILY <count> <FNV-1a 64 of the sets, in order, 4 bytes each>".  The instrumented reference and
each instrumented candidate run on the same inputs; their FAMILY sequences must be equal, and so
must their exit status, output bytes and nine counters.  The instrumented reference must also
reproduce the pinned reference binary byte for byte on the first cells (the instrumentation only
writes to stderr).

Candidates: the new source as built by the Makefile, and test builds forcing the restricted
path's anchored family as early as allowed (RESTRICTED_SWITCH_CANDIDATES=1) and the pattern path's
uncovered-set tracking on every order (UNCOVERED_MIN_ORDER=1), all instrumented.

Red control (--red): the new source with one planted change of ORDER only: where the direct test
finds two or more uncovered images, it adds all of them in numeric order instead of letting the
search add them in its own order.  The family has the same sets, so the outputs and counters stay
identical to the reference (shown), and the FAMILY sequence must differ.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from speed398lib import (BASE398_SHA256, BASE398_SOURCE, BASE398_UDENUM, F398, NEW_SOURCE, SCRATCH, build_variant,
                         compare_runs, g6_lines, run_udenum, sha256, write_lines)

HOOK = "    if (cfg->mutation_drop_first_badset) bad_family_drop_first(bad);\n"
DUMP = HOOK + r"""    {
        uint64_t family_hash = UINT64_C(14695981039346656037);
        size_t family_q;
        int family_b;
        for (family_q = 0; family_q < bad->count; ++family_q) {
            for (family_b = 0; family_b < 4; ++family_b) {
                family_hash ^= (uint64_t)((bad->sets[family_q] >> (8 * family_b)) & 0xffu);
                family_hash *= UINT64_C(1099511628211);
            }
        }
        fprintf(stderr, "FAMILY %zu %016llx\n", bad->count, (unsigned long long)family_hash);
    }
"""

ORDER_ONLY_OLD = """            if (images == 1) {
                bad_family_add(family, found);
                continue;
            }"""
ORDER_ONLY_NEW = """            if (images >= 1) {
                for (u = 0; u < listed; ++u)
                    if (pattern_has_image(s, h, host_m, i, uncovered[u])) bad_family_add(family, uncovered[u]);
                continue;
            }"""


def instrumented(source: Path, work: Path, name: str, defines=(), patches=()) -> Path:
    src = source.read_text()
    for old, new in [(HOOK, DUMP), *patches]:
        if src.count(old) != 1:
            raise SystemExit(f"{name}: patch applies {src.count(old)} times, expected 1: {old[:60]!r}")
        src = src.replace(old, new)
    path = work / "src" / f"udenum-{name}.c"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return build_variant(path, work / "bin" / f"udenum-{name}", defines, allow_warnings=True)


def run_with_family(binary: Path, cell: dict, out: Path) -> tuple[dict, list[str]]:
    """run_udenum's record for one run, plus the FAMILY lines it wrote (in parent order)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["nice", "-n", "15", str(binary), "--parents", str(cell["parents"]), "--forbidden", str(F398),
           "--forbidden-set", "398", "--n", str(cell["n"]), "--m", str(cell["m"]), "--output", str(out),
           "--manifest", str(out.with_suffix(".manifest.json")), "--shard-id", out.stem, "--overwrite",
           *cell.get("extra", [])]
    p = subprocess.run(cmd, capture_output=True, text=True)
    lines = [x for x in p.stderr.strip().splitlines() if x.strip()]
    family = [x for x in lines if x.startswith("FAMILY ")]
    rest = [x for x in lines if not x.startswith("FAMILY ")]
    stats = json.loads(rest[-1]) if p.returncode == 0 and rest and rest[-1].startswith("{") else None
    return ({"returncode": p.returncode, "stderr_tail": rest[-1] if rest else "", "stats": stats,
             "cpu": stats["cpu_seconds"] if stats else None, "output": out}, family)


def cells(a) -> list[dict]:
    out = []
    if a.p398_dir:
        for f in sorted(a.p398_dir.glob("*.p398.g6")):
            if f.name.startswith("u22-all-48-slices"):
                continue
            name = f.name[: -len(".p398.g6")]                  # e.g. dag-22-61_11-19
            n, m = map(int, name.split("_")[-1].split("-"))
            out.append({"cell": f"dag {name} p398", "parents": f, "n": n, "m": m})
    if a.speed_work:
        for L in range(12, 22):
            for f in sorted(a.speed_work.glob(f"measure-{L}-*.all.g6"),
                            key=lambda p: int(p.name.split("-")[2].split(".")[0])):
                M = int(f.name.split("-")[2].split(".")[0])
                for kind in ("free", "all"):
                    out.append({"cell": f"deep L{L} ({L + 1},{M}) {kind}",
                                "parents": f.with_name(f"measure-{L}-{M}.{kind}.g6"), "n": L + 1, "m": M})
    if a.slices:
        l21 = a.work / "l21-all.g6"
        write_lines(l21, [g for s in range(48) for g in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
        out.append({"cell": "L21 (22,61) the 743 real parents", "parents": l21, "n": 22, "m": 61})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--p398-dir", type=Path, default=None, help="semantics-398.py's work directory (4.2 P398 files)")
    ap.add_argument("--speed-work", type=Path, default=None, help="speed.py's work directory (measure files)")
    ap.add_argument("--slices", type=Path, default=None, help="results/u22 of the worker branches (s0of48..)")
    ap.add_argument("--red", action="store_true", help="also the order-only red control")
    ap.add_argument("--only", default=None, help="run only the cells whose name contains this text (smoke tests)")
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-family")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-family.json")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    w = a.work
    if sha256(BASE398_UDENUM) != BASE398_SHA256:
        print("the reference binary is not the pinned Mode 398 binary")
        return 2
    t0 = time.monotonic()
    ref_bin = instrumented(BASE398_SOURCE, w, "base398")
    cands = {"new": instrumented(NEW_SOURCE, w, "new"),
             "new-K1": instrumented(NEW_SOURCE, w, "new-K1", ["RESTRICTED_SWITCH_CANDIDATES=1"]),
             "new-U1": instrumented(NEW_SOURCE, w, "new-U1", ["UNCOVERED_MIN_ORDER=1"])}
    # the order-only mutant tracks uncovered sets on every order, so its change can act on every cell
    red_bin = (instrumented(NEW_SOURCE, w, "order-only", ["UNCOVERED_MIN_ORDER=1"],
                            patches=[(ORDER_ONLY_OLD, ORDER_ONLY_NEW)]) if a.red else None)
    cs = [c for c in cells(a) if a.only is None or a.only in c["cell"]]
    rows = []
    ok = True
    sanity_ok = True
    red_family_differs = 0
    red_output_differs = 0
    for idx, c in enumerate(cs):
        tag = f"c{idx}"
        ref, ref_family = run_with_family(ref_bin, c, w / "out" / f"{tag}.ref.g6")
        row = {"cell": c["cell"], "parents": len(g6_lines(c["parents"])), "families": len(ref_family),
               "sets": sum(int(x.split()[1]) for x in ref_family), "candidates": {}}
        if idx < 3:
            pinned = run_udenum(BASE398_UDENUM, c["parents"], c["n"], c["m"], w / "out" / f"{tag}.pinned.g6")
            p = compare_runs(pinned, ref)
            row["instrumented_reference_equals_pinned"] = not p
            sanity_ok = sanity_ok and not p
        line_ok = True
        for k, b in cands.items():
            got, fam = run_with_family(b, c, w / "out" / f"{tag}.{k}.g6")
            problems = compare_runs(ref, got)
            if fam != ref_family:
                first = next((j for j, (x, y) in enumerate(zip(fam, ref_family)) if x != y), min(len(fam), len(ref_family)))
                problems.append(f"FAMILY sequence differs (lengths {len(ref_family)} vs {len(fam)}; first at parent "
                                f"record {first})")
            row["candidates"][k] = {"identical": not problems, "problems": problems, "cpu": got["cpu"]}
            line_ok = line_ok and not problems
        if red_bin is not None:
            got, fam = run_with_family(red_bin, c, w / "out" / f"{tag}.order-only.g6")
            out_problems = compare_runs(ref, got)
            fam_differs = fam != ref_family
            row["order_only_mutant"] = {"output_problems": out_problems, "family_differs": fam_differs}
            red_family_differs += fam_differs
            red_output_differs += bool(out_problems)
        ok = ok and line_ok
        rows.append(row)
        red_note = ""
        if red_bin is not None:
            red_note = (f" | order-only mutant: output {'DIFFERS' if row['order_only_mutant']['output_problems'] else 'identical'}"
                        f", family {'differs' if row['order_only_mutant']['family_differs'] else 'same'}")
        print(f"{c['cell']:40s} parents {row['parents']:6d} families {row['families']:6d} sets {row['sets']:9d} | "
              + ("IDENTICAL (families in order, outputs, counters)" if line_ok else "DIFFERENT: " + "; ".join(
                  f"{k}: {', '.join(v['problems'])}" for k, v in row["candidates"].items() if v["problems"]))
              + red_note, flush=True)
    print(f"families compared: {sum(r['families'] for r in rows)} per candidate "
          f"({sum(r['sets'] for r in rows)} sets) over {len(rows)} cells; all identical in order: {ok}", flush=True)
    print(f"instrumented reference equals the pinned reference on the first cells: {sanity_ok}", flush=True)
    passed = ok and sanity_ok
    red = None
    if red_bin is not None:
        red = {"cells_family_differs": red_family_differs, "cells_output_differs": red_output_differs}
        went_red = red_family_differs > 0
        print(f"RED CONTROL {'went red' if went_red else 'DID NOT GO RED'}: order-only mutant: the FAMILY sequence "
              f"differs on {red_family_differs} of {len(rows)} cells, while outputs and counters differ on "
              f"{red_output_differs} (the output check cannot see an order change)", flush=True)
        passed = passed and went_red
    summary = {"reference_source_sha256": sha256(BASE398_SOURCE), "new_source_sha256": sha256(NEW_SOURCE),
               "candidates": {k: sha256(b) for k, b in cands.items()}, "rows": rows, "red": red,
               "pass": passed, "seconds": round(time.monotonic() - t0, 1)}
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print("RESULT:", "PASS" if passed else "FAIL", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
