#!/usr/bin/env python3
"""Cross-check a pruned level against the unpruned enumeration of the same cell.

    check-prune-sample.py --unpruned 13-23.g6 --keep 13-23.keep.g6 [--sample 20000] [--mutate]

Two facts are checked. (1) Every graph of the pruned keep set occurs in the unpruned cell
(the pruned DAG never invents a graph). (2) On a strided sample of the unpruned cell, the C
filter's verdict agrees with membership in the keep set: 'pass' graphs are kept, 'tu' graphs
are not. Because pruning is hereditary, a 'pass' graph whose canonical parent was pruned
would be missing from the keep set, so (2) also tests that no TU-free graph lost its parent.
--mutate flips one verdict and must make the check fail (a control on the control).
Exit 0 only if every assertion holds; the JSON summary goes to stdout.
"""
import argparse, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def records(path):
    with open(path, encoding="ascii") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith(">>")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unpruned", type=Path, required=True)
    ap.add_argument("--keep", type=Path, required=True)
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--udfilter", type=Path, default=ROOT / "filter" / "udfilter")
    ap.add_argument("--mutate", action="store_true", help="control: flip one verdict, expect failure")
    ap.add_argument("--unpruned-is-sample", action="store_true",
                    help="--unpruned holds only a sample of the cell: skip the keep-subset check")
    a = ap.parse_args()
    full = records(a.unpruned); keep = records(a.keep)
    full_set = set(full); keep_set = set(keep)
    problems = []
    not_in_full = [] if a.unpruned_is_sample else [g for g in keep if g not in full_set]
    if not_in_full:
        problems.append(f"{len(not_in_full)} keep graphs absent from the unpruned cell, e.g. {not_in_full[0]}")
    if len(keep_set) != len(keep):
        problems.append("duplicate records in keep file")
    stride = 1 if a.unpruned_is_sample else max(1, len(full) // max(1, a.sample))
    sample = full if a.unpruned_is_sample else full[::stride][:a.sample]
    proc = subprocess.run([str(a.udfilter), "-t", str(ROOT / "data" / "tu-gadgets.json")],
                          input="".join(g + "\n" for g in sample), capture_output=True, text=True, check=True)
    verdicts = {}
    for line in proc.stdout.splitlines():
        d = json.loads(line); verdicts[d["g6"]] = d["verdict"]
    if set(verdicts) != set(sample):
        problems.append("filter did not answer for every sampled graph")
    if a.mutate and sample:
        g0 = sample[0]; verdicts[g0] = "tu" if verdicts.get(g0) == "pass" else "pass"
    counts = {"pass_kept": 0, "pass_missing": 0, "tu_absent": 0, "tu_kept": 0}
    for g in sample:
        v = verdicts.get(g); kept = g in keep_set
        if v == "pass" and kept: counts["pass_kept"] += 1
        elif v == "pass": counts["pass_missing"] += 1
        elif v == "tu" and not kept: counts["tu_absent"] += 1
        elif v == "tu": counts["tu_kept"] += 1
    if counts["pass_missing"] or counts["tu_kept"]:
        problems.append(f"filter/keep disagreement: {counts}")
    if counts["pass_kept"] == 0 or counts["tu_absent"] == 0:
        problems.append(f"sample is one-sided, the check has no power: {counts}")
    out = {"unpruned": str(a.unpruned), "keep": str(a.keep), "unpruned_records": len(full),
           "keep_records": len(keep), "sample": len(sample), "counts": counts,
           "mutated": a.mutate, "problems": problems, "ok": not problems}
    print(json.dumps(out))
    return 0 if not problems else 1

if __name__ == "__main__":
    sys.exit(main())
