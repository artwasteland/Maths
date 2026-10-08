#!/usr/bin/env python3
"""The multiprocessing path of replay-398.py: run A replayed with --workers 2 (replay-W2) must give,
parent by parent, the same entries as the single-process T1 run of replay-test.py (same seed and
sampling options), apart from timings.  Red control: one field of one W2 entry perturbed must be
reported as a difference."""
from __future__ import annotations

import json
import sys

from v398lib import RUNS, SCRATCH, dump

KEYS = ("run_dir", "cell", "index", "record", "d", "processed", "block", "production", "enum2", "enum2_raw",
        "only_production", "only_enum2", "production_duplicates", "enum2_children_not_recovering_to_parent",
        "parent_canonical", "parent_contains_forbidden", "identical")


def load(path):
    rows = [json.loads(x) for x in path.read_text().splitlines()[1:]]
    return {(r["cell"], r["index"]): tuple(r.get(k) for k in KEYS if k != "run_dir") for r in rows}


def diff(a: dict, b: dict) -> list:
    return sorted(set(a) ^ set(b)) + [k for k in set(a) & set(b) if a[k] != b[k]]


def main() -> int:
    one = load(SCRATCH / "replay-test" / "T1" / "replay.jsonl")
    two = load(SCRATCH / "replay-W2" / "replay.jsonl")
    d = diff(one, two)
    key = sorted(two)[0]
    perturbed = dict(two)
    perturbed[key] = perturbed[key][:-1] + (not perturbed[key][-1],)
    red = bool(diff(one, perturbed))
    out = {"entries_single_process": len(one), "entries_two_workers": len(two), "differences": len(d),
           "differences_first": [list(x) if isinstance(x, tuple) else x for x in d[:5]],
           "red_control_perturbed_entry_detected": red, "pass": not d and red and len(one) > 0}
    dump(RUNS / "compare-w2.json", out)
    print(json.dumps(out))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
