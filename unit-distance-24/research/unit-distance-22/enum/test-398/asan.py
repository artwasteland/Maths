#!/usr/bin/env python3
"""AddressSanitizer + UBSan runs of the new udenum on the paths where 10-vertex forbidden graphs are
searched, and a red control that plants the OLD ExistsContext sizes (order[9], map[9]) back.

Checks (each sanitizer-clean, with the stated result):
  --filter on the L10 members, per edge count: set 398 keeps none of them, set 74 keeps all of them
  set 398 --verify-parents on the 743 real level-21 parents: refuses (some contain one of the 324)
  set 398 generation of (22,61) from the 743 level-21 parents
Red control: the same --filter run on a build with order[9]/map[9] must produce a sanitizer report.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from t398lib import F398, F74, HERE, REPO, SCRATCH, UD, g6_lines, g6_order_size, write_lines

FLAGS = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-std=c17",
         "-I/usr/include/x86_64-linux-gnu/nauty", "-I/usr/include/nauty"]


def run(binary: Path, args: list[str], label: str) -> tuple[int, list[str]]:
    p = subprocess.run(["nice", "-n", "10", str(binary), *args, "--overwrite"], capture_output=True, text=True)
    san = [x for x in p.stderr.splitlines() if "Sanitizer" in x or "runtime error" in x]
    print(f"{label}: exit {p.returncode}; sanitizer lines {len(san)}; {p.stderr.strip().splitlines()[-1][:120]}")
    for x in san[:3]:
        print("   ", x)
    return p.returncode, san


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--l10", type=Path, default=REPO / "research/gp-10/runs/B10-final-2026-09-25/L10.g6")
    ap.add_argument("--slices", type=Path, required=True, help="results/u22 of the worker branches (s0of48..)")
    ap.add_argument("--work", type=Path, default=SCRATCH / "asan")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    good = w / "udenum-asan"
    subprocess.run(["nice", "-n", "10", "cc", *FLAGS, str(UD / "enum/udenum.c"), "-o", str(good), "-lnauty"],
                   check=True, capture_output=True)
    bad = 0
    by_m: dict[int, list[bytes]] = {}
    for g in g6_lines(a.l10):
        by_m.setdefault(g6_order_size(g)[1], []).append(g)
    for m, lines in sorted(by_m.items()):
        src = w / f"l10-m{m}.g6"
        write_lines(src, lines)
        for label, extra, forb, expect in (("set 398", ["--forbidden-set", "398"], F398, 0),
                                           ("set 74", [], F74, len(lines))):
            out = w / f"filter-{m}-{label.replace(' ', '')}.g6"
            rc, san = run(good, ["--parents", str(src), "--forbidden", str(forb), "--n", "10", "--m", str(m),
                                 "--filter", "--output", str(out), "--manifest", f"{out}.json", "--shard-id", "asan",
                                 *extra], f"--filter the {len(lines)} L10 members with {m} edges, {label}")
            kept = len(g6_lines(out)) if out.exists() else -1
            ok = rc == 0 and not san and kept == expect
            print(f"    kept {kept}, expected {expect}: {'ok' if ok else 'BAD'}")
            bad += not ok
    l21 = w / "l21.g6"
    write_lines(l21, [g for s in range(48) for g in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
    out = w / "final-398v.g6"
    rc, san = run(good, ["--parents", str(l21), "--forbidden", str(F398), "--forbidden-set", "398", "--verify-parents",
                         "--n", "22", "--m", "61", "--output", str(out), "--manifest", f"{out}.json", "--shard-id", "asan"],
                  "set 398 --verify-parents on the 743 level-21 parents (must refuse)")
    bad += not (rc == 2 and not san)
    out = w / "final-398.g6"
    rc, san = run(good, ["--parents", str(l21), "--forbidden", str(F398), "--forbidden-set", "398",
                         "--n", "22", "--m", "61", "--output", str(out), "--manifest", f"{out}.json", "--shard-id", "asan"],
                  "set 398 on the 743 level-21 parents")
    bad += not (rc == 0 and not san)
    print("ASAN checks:", "PASS" if not bad else f"FAIL ({bad})")

    # red control: the old ExistsContext sizes
    src = (UD / "enum/udenum.c").read_text()
    new = "    unsigned char order[MAX_FORBIDDEN_ORDER];\n    int map[MAX_FORBIDDEN_ORDER];\n    uint32_t used;\n} ExistsContext;"
    old = "    unsigned char order[9];\n    int map[9];\n    uint32_t used;\n} ExistsContext;"
    if src.count(new) != 1:
        print("cannot locate ExistsContext in udenum.c")
        return 2
    (w / "udenum-oldexists.c").write_text(src.replace(new, old))
    red = w / "udenum-oldexists-asan"
    subprocess.run(["nice", "-n", "10", "cc", *FLAGS, str(w / "udenum-oldexists.c"), "-o", str(red), "-lnauty"],
                   check=True, capture_output=True)
    out = w / "red-filter.g6"
    rc, san = run(red, ["--parents", str(w / "l10-m16.g6"), "--forbidden", str(F398), "--forbidden-set", "398",
                        "--n", "10", "--m", "16", "--filter", "--output", str(out), "--manifest", f"{out}.json",
                        "--shard-id", "red"], "RED CONTROL: planted order[9]/map[9], --filter the 16-edge members")
    went_red = rc != 0 and bool(san)
    print("RED CONTROL", "went red" if went_red else "DID NOT GO RED")
    ok = not bad and went_red
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
