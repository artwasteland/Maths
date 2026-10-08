#!/usr/bin/env python3
"""Print the validation tables from runs/*.json (no computation)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs"


def cells() -> None:
    d = json.loads((RUNS / "cells398.json").read_text())
    print("| cell | P74 | P74 with a 398 | P398 | C74 | E | udenum | enum2 | only udenum | only enum2 | "
          "per-parent diffs | processed udenum/enum2 | pass | enum2 ms/processed parent | udenum cpu s | enum2 cpu s |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|")
    order = lambda r: (0 if r["cell"].startswith("dag-22") else 1 if r["cell"].startswith("dag-18") else 2,
                       tuple(int(x) for x in r["cell"].split("/")[1].split("-")))
    for r in sorted(d["cells"], key=order):
        print(f"| {r['cell']} | {r['P74']} | {r['P74_containing_398']} | {r['P398']} | {r['C74']} | {r['E']} | "
              f"{r['PROD']} | {r['ENUM2']} | {r['only_production']} | {r['only_enum2']} | "
              f"{r['parents_differing']} | {r['udenum_stats'].get('parents_processed')}/"
              f"{r['enum2_stats'].get('parents_processed', 0)} | {'yes' if r['pass'] else 'NO'} | "
              f"{r['enum2_ms_per_processed_parent']} | "
              f"{r['udenum_stats'].get('cpu_seconds')} | {r['enum2_cpu_seconds']} |")
    print("totals", json.dumps(d.get("totals")), "pass", d.get("pass"))
    for rc in d.get("red_controls", []):
        print("RED", json.dumps({k: v for k, v in rc.items() if k != "member_edges"}))


if __name__ == "__main__":
    {"cells": cells}[sys.argv[1] if len(sys.argv) > 1 else "cells"]()
