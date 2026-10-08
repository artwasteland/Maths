#!/usr/bin/env python3
"""Every m at n = 3..8: enum2's recursive enumeration against geng + the reference backtracker.

For the 74 and the 398 (identical below order 10, where the 324 cannot occur), with the fast
engine (and, for n <= 7, the reference engine too), every (n, m) must give exactly the
brute-force set (nauty-geng, then straightforward_contains against every forbidden graph),
and the count vectors must equal the ones enum2/REPORT.md recorded on 2026-09-05.
Red control: the fast engine with K4's four rooted patterns removed must differ at (4, 6).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from v398lib import ENUM2_DIR, RUNS, dump, enum2, software

REPORTED = {  # enum2/REPORT.md, "The exact F-free count vectors, indexed by m"
    4: [1, 1, 2, 3, 2, 1, 0],
    5: [1, 1, 2, 4, 6, 6, 4, 1, 0, 0, 0],
    6: [1, 1, 2, 5, 9, 15, 19, 18, 11, 4, 0, 0, 0, 0, 0, 0],
    7: [1, 1, 2, 5, 10, 21, 39, 58, 73, 72, 41, 8, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    8: [1, 1, 2, 5, 11, 24, 54, 108, 193, 307, 397, 381, 221, 38, 3] + [0] * 14,
}


def main() -> int:
    out = {"software": software(), "sets": {}}
    ok = True
    for name in ("74", "398"):
        fs = enum2.load_forbidden_set(name)
        rec = {"vectors": {}, "mismatches": [], "reference_engine_checked": 0}
        for n in range(3, 9):
            vec = []
            for m in range(0, n * (n - 1) // 2 + 1):
                with tempfile.TemporaryDirectory(prefix="enum2-small-") as tmp:
                    ours = set(enum2.enumerate_recursive(n, m, {}, Path(tmp), forbidden_set=fs, engine="fast"))
                    if n <= 7:
                        ref = set(enum2.enumerate_recursive(n, m, {}, Path(tmp) / "ref", forbidden_set=fs,
                                                            engine="reference"))
                        rec["reference_engine_checked"] += 1
                    else:
                        ref = ours
                brute = enum2.brute_force_records(n, m, fs.graphs)
                if not (ours == brute == ref):
                    rec["mismatches"].append({"n": n, "m": m, "fast": len(ours), "reference": len(ref),
                                              "brute": len(brute)})
                vec.append(len(brute))
            rec["vectors"][n] = vec
            if n in REPORTED and vec != REPORTED[n]:
                rec["mismatches"].append({"n": n, "vector": vec, "reported_2026_09_05": REPORTED[n]})
            print(f"set {name} n={n}: {vec}", flush=True)
        out["sets"][name] = rec
        ok = ok and not rec["mismatches"]
    # red control: K4's rooted patterns removed from the fast engine
    fs = enum2.load_forbidden_set("74")
    with tempfile.TemporaryDirectory(prefix="enum2-small-") as tmp:
        parent = Path(tmp) / "p.g6"
        parent.write_text(enum2.canonical_g6(enum2.Graph((0b110, 0b101, 0b011))) + "\n")
        normal = enum2.enumerate_from_parents(parent, 4, 6, Path(tmp) / "a.g6", forbidden_set=fs)
        broken = enum2.enumerate_from_parents(parent, 4, 6, Path(tmp) / "b.g6", drop_pattern=[0, 1, 2, 3],
                                              forbidden_set=fs)
    out["red_control_K4_patterns_dropped"] = {"normal_children": normal, "broken_children": broken,
                                              "went_red": normal == 0 and broken == 1}
    out["pass"] = ok and out["red_control_K4_patterns_dropped"]["went_red"]
    dump(RUNS / "small-n.json", out)
    print("RESULT:", "PASS" if out["pass"] else "FAIL")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
