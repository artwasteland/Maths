#!/usr/bin/env python3
"""The seed path of the u(23) contract: `udenum --filter --forbidden-set 398` on every graph on 10 vertices.

research/unit-distance-23/CONTRACT.md takes as level-10 seeds "every graph on 10 vertices that contains none of
the 398, from nauty-geng and the Mode-398 filter".  For every m = 0..45: nauty-geng -q 10 m:m, then udenum
--filter (set 398, and set 74 as the control) with --n 10 --m m.  PASS iff the union, relabelled with
nauty-labelg and sorted, equals brute10.py's brute398 (resp. brute74), which the unmodified GP-10 matcher
decided.  Red: the set-74 filter's union judged against brute398 must differ by exactly the 509.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from t398lib import F398, F74, HERE, NEW_UDENUM, SCRATCH, g6_lines, run_udenum, write_lines


def labelg_sorted(src: Path, dst: Path) -> list[bytes]:
    tmp = dst.with_suffix(".labelg.g6")
    subprocess.run(["nice", "-n", "10", "nauty-labelg", "-q", str(src), str(tmp)], check=True)
    lines = sorted(g6_lines(tmp))
    write_lines(dst, lines)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brute", type=Path, default=SCRATCH / "brute10", help="brute10.py's work directory")
    ap.add_argument("--work", type=Path, default=SCRATCH / "seeds10")
    ap.add_argument("--summary", type=Path, default=HERE / "runs" / "seeds10.json")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    brute = {"398": g6_lines(a.brute / "brute398.g6"), "74": g6_lines(a.brute / "brute74.g6")}
    out = {"per_m": {}}
    unions = {"398": [], "74": []}
    total = 0
    for m in range(46):
        src = w / f"geng-10-{m}.g6"
        with open(src, "wb") as stdout:
            subprocess.run(["nice", "-n", "10", "nauty-geng", "-q", "10", f"{m}:{m}"], stdout=stdout, check=True)
        count = len(g6_lines(src))
        total += count
        row = {"graphs": count}
        for s, extra, forb in (("398", ["--forbidden-set", "398"], F398), ("74", [], F74)):
            o = w / f"seed-{s}-10-{m}.g6"
            st = run_udenum(NEW_UDENUM, src, 10, m, o, extra=["--filter", *extra], forbidden=forb)
            kept = g6_lines(o)
            unions[s] += kept
            row[f"kept_{s}"] = len(kept)
            row[f"cpu_{s}"] = st["cpu_seconds"]
        out["per_m"][m] = row
    print(f"geng: {total} graphs on 10 vertices over m = 0..45")
    checks = {}
    for s in ("398", "74"):
        raw = w / f"seeds-{s}.raw.g6"
        write_lines(raw, unions[s])
        got = labelg_sorted(raw, w / f"seeds-{s}.g6")
        checks[f"filter{s}_equals_brute{s}"] = got == brute[s]
        print(f"udenum --filter set {s}: {len(got)} graphs; equals brute force {got == brute[s]}")
    got74 = g6_lines(w / "seeds-74.g6")
    red = got74 != brute["398"] and len(set(got74) - set(brute["398"])) == 509
    print(f"RED CONTROL {'went red' if red else 'DID NOT GO RED'}: set-74 seeds judged against brute398 "
          f"(differ by {len(set(got74) - set(brute['398']))})")
    out.update({"geng_total": total, "checks": checks, "red_control_went_red": red,
                "cpu_seconds": {s: sum(r[f'cpu_{s}'] for r in out['per_m'].values()) for s in ("398", "74")}})
    print(f"filter cpu seconds: set 398 {out['cpu_seconds']['398']:.1f}, set 74 {out['cpu_seconds']['74']:.1f}")
    ok = all(checks.values()) and red
    out["pass"] = ok
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(out, indent=1) + "\n")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
