#!/usr/bin/env python3
"""Extract a few actual trees covering move kinds and field degrees.

Byte-filtered metadata scan only; no full-population identity verification.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

from independent_core import lines, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("records")
    p.add_argument("outdir")
    a = p.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    moves, degrees, selected, checked = Counter(), Counter(), [], 0
    with (out / "trees.jsonl").open("wb") as f:
        for number, raw in lines(a.records):
            if b'"tree"' not in raw:
                continue
            r = json.loads(raw)
            if r["cert"].get("type") != "tree":
                continue
            kinds, todo = Counter(), [r["cert"]["witness"]["tree"]]
            while todo:
                node = todo.pop()
                kinds[node["move"]["kind"]] += 1
                todo.extend(node["children"])
            degree = len(r["cert"]["witness"]["field"]["minpoly"]) - 1
            new = set(kinds) - set(moves)
            if new or degree not in degrees:
                f.write(raw)
                selected.append({"g6": r["g6"], "new_moves": sorted(new), "field_degree": degree,
                                 "line": number, "bytes": len(raw)})
            moves.update(kinds)
            degrees[degree] += 1
            checked += 1
    write_json(out / "trees-manifest.json", {"scope": "tree metadata only", "tree_records_seen": checked,
        "moves_seen": dict(moves), "degrees_seen": dict(degrees), "selected": selected,
        "seconds": round(time.monotonic() - t0, 3)})
    print(json.dumps({"trees_seen": checked, "selected": len(selected), "moves": dict(moves)}), flush=True)


if __name__ == "__main__":
    main()
