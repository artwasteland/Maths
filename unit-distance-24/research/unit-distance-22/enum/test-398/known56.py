#!/usr/bin/env python3
"""The 56 known extremal unit-distance graphs of AMP (sources/amp/anc/graph6.txt) contain none of the
398: a unit-distance graph has no non-unit-distance subgraph.  Decided by the new udfilter in set
398 and by the widened GP-10 matcher over data/forbidden-398.g6.  Red: the first L10 graph appended
as a 57th host must be called forbidden by both."""
from __future__ import annotations

import json
import subprocess
import sys

from t398lib import F398, F398_G6, MATCHER32, NEW_UDFILTER, SCRATCH, TU, UD, g6_lines, run_matcher, write_lines

KNOWN = UD / "sources/amp/anc/graph6.txt"


def decide(hosts_file):
    p = subprocess.run(["nice", "-n", "10", str(NEW_UDFILTER), "-s", "398", "-f", str(F398), "-t", str(TU)],
                       input=hosts_file.read_bytes(), capture_output=True, check=True)
    forb = {json.loads(x)["g6"] for x in p.stdout.split(b"\n") if x and json.loads(x)["verdict"] == "forbidden"}
    m = run_matcher(MATCHER32, F398_G6, hosts_file, SCRATCH / f"known56-{hosts_file.stem}")
    return forb, {h.decode() for h in m["removed"]}


def main() -> int:
    known = g6_lines(KNOWN)
    u, m = decide(KNOWN)
    print(f"{len(known)} known graphs: udfilter set 398 forbidden {len(u)}, matcher removed {len(m)}")
    planted = SCRATCH / "known56-planted.g6"
    member = g6_lines(F398_G6)[74]
    write_lines(planted, known + [member])
    ru, rm = decide(planted)
    red = member.decode() in ru and member.decode() in rm and len(ru) == len(rm) == 1
    print(f"RED CONTROL {'went red' if red else 'DID NOT GO RED'}: L10 line 0 appended -> udfilter {len(ru)}, "
          f"matcher {len(rm)}")
    ok = not u and not m and red
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
