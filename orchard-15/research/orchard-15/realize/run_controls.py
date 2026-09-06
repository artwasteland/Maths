#!/usr/bin/env python3
"""Run and independently check the mandatory exact-realizability controls."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "chiro"))
sys.path.insert(0, str(HERE))
from chirosat import parse_pts_line  # noqa: E402
from controls import DESARGUES, FANO, KANTOR_10, PAPPUS, PEGG_15_31  # noqa: E402
from check_realization import check_record  # noqa: E402
from realize import decide_with_timeout  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--out", type=Path, default=HERE / "control-verdicts.jsonl")
    args = parser.parse_args()
    bgs = parse_pts_line((ROOT / "chiro" / "scratch" / "exist-14-27.pts").read_text().strip())
    controls = [
        ("Fano (7,7)", FANO),
        ("Pappus 9_3", PAPPUS),
        ("Desargues 10_3", DESARGUES),
        ("Kantor 10_3", KANTOR_10),
        ("Pegg (15,31)", PEGG_15_31),
        ("BGS (14,27) SAT model", bgs),
    ]
    records = []
    for name, pts in controls:
        record = decide_with_timeout(pts, args.timeout)
        check_started = time.perf_counter()
        accepted, detail = check_record(pts, record)
        record["control"] = name
        record["checker_accept"] = accepted
        record["checker_detail"] = detail
        record["checker_wall_seconds"] = round(time.perf_counter() - check_started, 6)
        records.append(record)
        print(f"{name}: {record['verdict']}, checker={accepted}", file=sys.stderr, flush=True)
    args.out.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
                        encoding="utf-8")
    print(json.dumps({"controls": len(records), "checker_accepted": sum(r["checker_accept"] for r in records),
                      "output": str(args.out.resolve())}, sort_keys=True))
    return 0 if all(record["checker_accept"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
