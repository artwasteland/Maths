#!/usr/bin/env python3
"""Merge complete, disjoint mod-p or embedding shard reports; reject omissions.

Prefer --jobs 12 in a single process. --shard i/n is for separate VM runs.
"""
import argparse
from collections import Counter
from pathlib import Path
import sys

from independent_core import guard_outputs, loads, require, shard, write_json


def merge(kind, files, output):
    guard_outputs(files, [output])
    reps = [loads(Path(f).read_bytes()) for f in files]
    slots = [shard(r["shard"]) for r in reps]
    n = slots[0][1]
    require(all(size == n for i, size in slots) and sorted(i for i, size in slots) == list(range(n)),
            "shards", "need each shard 0/n through (n-1)/n exactly once")
    first = reps[0]
    require(all(r["source_hashes"] == first["source_hashes"] for r in reps), "sources", "shard source hashes disagree")
    out = dict(first)
    out["shard"], out["merged_shards"] = "0/1", [str(f) for f in files]
    if kind == "modp":
        require(all(r["status"] == "PASS" and r["all_red"] and not r["failures"] for r in reps),
                "shards", "an identity shard or its red controls failed")
        common = ("consumed_sha256", "scanned_records", "seed", "points_per_prime", "primes")
        require(all(all(r[k] == first[k] for k in common) for r in reps), "shards", "identity shard inputs/configurations disagree")
        selected = sum(r["selected_records"] for r in reps)
        require(selected == first["scanned_records"], "shards", "identity shard coverage is incomplete")
        for k in ("counts", "identities"):
            combined = Counter()
            for r in reps:
                combined.update(r[k])
            out[k] = dict(combined)
        out["selected_records"] = selected
        out["identities_per_point"] = sum(out["identities"].values()) // (2 * first["points_per_prime"])
        out["red_controls"] = [control for r in reps for control in r["red_controls"]]
        out["max_input_polynomial_degree"] = max(r["max_input_polynomial_degree"] for r in reps)
        out["polynomial_identity_degree_bound"] = max(r["polynomial_identity_degree_bound"] for r in reps)
        out["selected_sha256"] = None  # Ordered stream hashes cannot be combined by concatenating digests.
    else:
        require(all(r["status"] == "NO_COUNTEREXAMPLE_FOUND" and r["controls_all_found"]
                    and r["config"] == first["config"] and r["total_L11"] == first["total_L11"] for r in reps),
                "shards", "embedding shard result/configuration disagrees")
        require(all(r["input_hashes"] == first["input_hashes"] for r in reps),
                "shards", "embedding shard inputs differ")
        rows = [row for r in reps for row in r["rows"]]
        require(len(rows) == len({r["g6"] for r in rows}) == first["total_L11"],
                "shards", "embedding shards omit or duplicate a member")
        out["rows"], out["members"] = sorted(rows, key=lambda r: r["g6"]), len(rows)
        out["controls_minus_edge_found"] = sum(r["controls_minus_edge_found"] for r in reps)
        out["controls_embedded_B11_found"] = sum(r["controls_embedded_B11_found"] for r in reps)
    out["scope"] = "merged complete stream"
    out["seconds"] = max(r["seconds"] for r in reps)
    out["worker_seconds"] = sum(r["worker_seconds"] for r in reps)
    write_json(output, out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=("modp", "embed"))
    p.add_argument("out")
    p.add_argument("parts", nargs="+")
    a = p.parse_args()
    try:
        merge(a.kind, a.parts, a.out)
    except (ValueError, OSError, KeyError) as exc:
        print(f"REFUSE MERGE: {exc}", file=sys.stderr)
        sys.exit(1)
