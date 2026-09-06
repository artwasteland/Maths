#!/usr/bin/env python3
"""Blind-check a homogeneous PTS file against same-order stage-3 JSONL."""

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
from check_realization import check_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pts", type=Path)
    parser.add_argument("verdicts", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pts_instances = [parse_pts_line(line) for line in args.pts.read_text(encoding="ascii").splitlines()
                     if line.strip() and not line.lstrip().startswith("#")]
    records = [json.loads(line) for line in args.verdicts.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    if len(pts_instances) != len(records):
        raise SystemExit("PTS and verdict counts differ")
    results = []
    for index, (pts, record) in enumerate(zip(pts_instances, records)):
        started = time.perf_counter()
        accepted, detail = check_record(pts, record)
        result = {"index": index, "pts": pts.line, "verdict": record.get("verdict"),
                  "accepted": accepted, "detail": detail,
                  "wall_seconds": round(time.perf_counter() - started, 6)}
        results.append(result)
        print(f"check {index + 1}/{len(records)}: {accepted}", file=sys.stderr, flush=True)
    args.out.write_text("".join(json.dumps(result, sort_keys=True) + "\n" for result in results),
                        encoding="utf-8")
    print(json.dumps({"checked": len(results), "accepted": sum(r["accepted"] for r in results),
                      "output": str(args.out.resolve())}, sort_keys=True))
    return 0 if all(result["accepted"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
