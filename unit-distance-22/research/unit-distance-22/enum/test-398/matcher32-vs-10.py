#!/usr/bin/env python3
"""The widened matcher (matcher32.c) against GP-10's unmodified matcher on 10-vertex hosts.

On a host file of graphs with at most 10 vertices, both are run chained over the same pattern file
in the same chunks.  The search is untouched by the widening, so the removed sets, the survivor
lists (in order) and every witness (pattern index and map) must be identical.  Default hosts: B10
and the 398 patterns; --hosts may name any 10-vertex file (brute10.py's brute74.raw.g6, for all
74-free graphs on 10 vertices).  Red: the widened matcher with member 74 dropped must differ.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from t398lib import F398_G6, HERE, MATCHER10, MATCHER32, REPO, SCRATCH, g6_lines, run_matcher, write_lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hosts", type=Path, default=REPO / "research/gp-10/data/B10.g6")
    ap.add_argument("--work", type=Path, default=SCRATCH / "matcher32-vs-10")
    a = ap.parse_args()
    m10 = run_matcher(MATCHER10, F398_G6, a.hosts, a.work / "m10")
    m32 = run_matcher(MATCHER32, F398_G6, a.hosts, a.work / "m32")
    same = m10["removed"] == m32["removed"] and m10["survivors"] == m32["survivors"]
    print(f"hosts {a.hosts.name}: matcher10 removed {len(m10['removed'])}, matcher32 removed {len(m32['removed'])}; "
          f"survivors {len(m10['survivors'])} / {len(m32['survivors'])}; removed sets, witnesses and survivor "
          f"order identical: {same}")
    pats = g6_lines(F398_G6)
    reduced = a.work / "drop74.g6"
    write_lines(reduced, pats[:74] + pats[75:])
    red = run_matcher(MATCHER32, reduced, a.hosts, a.work / "m32-drop")
    went_red = red["survivors"] != m10["survivors"]
    print(f"RED CONTROL {'went red' if went_red else 'DID NOT GO RED'}: matcher32 without member 74 removed "
          f"{len(red['removed'])}")
    ok = same and went_red
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
