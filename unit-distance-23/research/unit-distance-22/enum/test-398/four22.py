#!/usr/bin/env python3
"""The four F-free (22,61) graphs of the u(22) run against the 398 list.

Each was eliminated twice in the u(22) result (a TU witness, and an embedder refutation).  Here:
does each contain one of GP-10's 324 minimal forbidden graphs?  Decided by the new udfilter in
set 398 AND by the widened GP-10 matcher over data/forbidden-398.g6; every witness of both is
re-verified in pure Python (injective, in range, edge-preserving).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from t398lib import (F398, F398_G6, HERE, MATCHER32, NEW_UDFILTER, SCRATCH, TU, UD, decode_g6, g6_lines,
                     run_matcher, sha256, witness_ok)

ALL4 = UD / "results/u22/cell-22-61/all4.g6"


def main() -> int:
    hosts = g6_lines(ALL4)
    print(f"all4.g6 sha256 {sha256(ALL4)}; {len(hosts)} graphs")
    p = subprocess.run(["nice", "-n", "10", str(NEW_UDFILTER), "-s", "398", "-f", str(F398), "-t", str(TU)],
                       input=ALL4.read_bytes(), capture_output=True, check=True)
    recs = [json.loads(x) for x in p.stdout.split(b"\n") if x]
    f398 = json.loads(F398.read_text())
    pats = g6_lines(F398_G6)
    m = run_matcher(MATCHER32, F398_G6, ALL4, SCRATCH / "four22")
    ok = True
    for h, r in zip(hosts, recs):
        idx, mp = r["witness"]["index"], r["witness"]["map"]
        u_ok = r["verdict"] == "forbidden" and idx >= 74 and witness_ok(h, f398[idx], mp)
        mi, mm = m["removed"].get(h, (None, None))
        m_ok = mi is not None and witness_ok(h, [tuple(sorted(e)) for e in decode_g6(pats[mi])[1]], mm)
        ok = ok and u_ok and m_ok
        print(f"{h.decode()}: udfilter member {idx} (L10 line {idx - 74}, {pats[idx].decode()}) witness "
              f"{'verified' if u_ok else 'BAD'}; matcher member {mi} (L10 line {mi - 74 if mi is not None else '-'}) "
              f"witness {'verified' if m_ok else 'BAD'}")
    print("RESULT:", "each of the four contains one of the 324" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
