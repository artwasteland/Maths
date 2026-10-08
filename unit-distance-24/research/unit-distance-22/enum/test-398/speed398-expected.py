#!/usr/bin/env python3
"""Tie the identity runs back to REPORT-398 4.2: the new binary's outputs equal E, byte for byte.

semantics-398.py computed, for every cell of 4.2, E = C74 minus the records containing one of the
398 (decided by GP-10's widened matcher, re-decided by udfilter), and checked that the Mode 398
binary writes exactly E from P398.  speed398-identity.py ran the new binary on the same P398 files.
This script compares the new binary's plain-mode output (and the reference's) with E, cell by cell,
so the chain "new == reference == E" is checked directly rather than by transitivity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from speed398lib import SCRATCH, g6_lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--p398-dir", type=Path, required=True, help="semantics-398.py's work directory")
    ap.add_argument("--identity-work", type=Path, default=SCRATCH / "speed398-identity")
    ap.add_argument("--summary", type=Path, default=Path(__file__).resolve().parent / "runs" / "speed398-expected.json")
    a = ap.parse_args()
    rows = []
    for e in sorted(a.p398_dir.glob("*.expected.g6")):
        tag = e.name[: -len(".expected.g6")]
        new = a.identity_work / "out" / f"{tag}.p398.new.g6"
        ref = a.identity_work / "out" / f"{tag}.p398.base.g6"
        if not new.exists():
            rows.append({"cell": tag, "missing": str(new)})
            print(f"{tag}: no identity output at {new}")
            continue
        eb = e.read_bytes()
        row = {"cell": tag, "expected_records": len(g6_lines(e)), "new_equals_E": new.read_bytes() == eb,
               "reference_equals_E": ref.read_bytes() == eb}
        rows.append(row)
        print(f"{tag:32s} E {row['expected_records']:6d} records: new == E {row['new_equals_E']}, "
              f"reference == E {row['reference_equals_E']}")
    ok = bool(rows) and all(r.get("new_equals_E") and r.get("reference_equals_E") for r in rows)
    total = sum(r.get("expected_records", 0) for r in rows)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps({"cells": rows, "expected_records": total, "pass": ok}, indent=1) + "\n")
    print(f"{sum(bool(r.get('new_equals_E')) for r in rows)} of {len(rows)} cells: new == E ({total} records)")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
