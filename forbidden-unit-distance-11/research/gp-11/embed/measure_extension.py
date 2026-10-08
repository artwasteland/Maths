#!/usr/bin/env python3
"""Derive job D's sample comparison and cost projection from checked artifacts."""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results/extension"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sample(name):
    directory = RESULTS / name
    summary = json.loads((directory / "summary.json").read_text())
    report = json.loads((directory / "checker-report.json").read_text())
    assert summary["completed"] and report["status"] == "ACCEPT"
    for file, receipt in summary["artifacts"].items():
        assert digest(directory / file) == receipt["sha256"], file
    counts = Counter()
    reasons = Counter()
    unknown_attempts = Counter()
    unknown_with_blocks = 0
    max_record_bytes = 0
    uncompressed_bytes = 0
    codes = []
    raw_hash = hashlib.sha256()
    with gzip.open(directory / "records.jsonl.gz", "rb") as records:
        with gzip.open(directory / "timings.jsonl.gz", "rt") as timings:
            for raw in records:
                raw_hash.update(raw)
                max_record_bytes = max(max_record_bytes, len(raw))
                uncompressed_bytes += len(raw)
                record = json.loads(raw)
                stats = json.loads(next(timings))
                assert record["g6"] == stats["g6"]
                assert record["verdict"] == stats["verdict"]
                codes.append(record["g6"])
                counts[record["verdict"]] += 1
                if record["verdict"] == "unknown":
                    reasons[record["cert"]["reason"]] += 1
                    rows = stats["attempts"]
                    unknown_attempts.update(row.get("reason", "interrupted_attempt") for row in rows)
                    unknown_with_blocks += any(row.get("reason") == "base_not_biconnected" for row in rows)
            assert next(timings, None) is None
    assert codes == (directory / "input.g6").read_text().splitlines()
    assert raw_hash.hexdigest() == report["files"][0]["sha256"]
    assert report["input_sha256"] == digest(directory / "input.g6")
    assert all(counts[key] == value for key, value in report["counts"].items())
    assert dict(reasons) == summary["unknown_reasons"]
    return {**summary, "checker_counts": report["counts"], "unknown_attempt_reasons": dict(unknown_attempts),
            "unknown_with_any_nonbiconnected_base": unknown_with_blocks,
            "max_record_bytes": max_record_bytes, "uncompressed_record_bytes": uncompressed_bytes,
            "embedded_percent": 100 * counts["embedded"] / len(codes),
            "seconds_per_graph_including_replay": (summary["graph_seconds"] + summary["replay_seconds"]) / len(codes),
            "cpu_seconds_per_graph_including_replay": (summary["graph_cpu_seconds"] + summary["replay_cpu_seconds"]) / len(codes)}


def main():
    samples = {name: sample(name) for name in ("architect-500", "seeded-5000")}
    larger = samples["seeded-5000"]
    population = 448708
    shards = 256
    cpu_ideal = population * larger["cpu_seconds_per_graph_including_replay"] / 14400
    wall_ideal = population * larger["seconds_per_graph_including_replay"] / 14400
    # Startup was not assigned per-graph CPU counters; charge all its wall time
    # as core time on every shard for a conservative explicit allowance.
    startup = shards * larger["setup_seconds"] / 14400
    overlap = {}
    for name in samples:
        directory = RESULTS / name
        with gzip.open(directory / "records.jsonl.gz", "rt") as records:
            with gzip.open(directory / "timings.jsonl.gz", "rt") as timings:
                for raw, timing in zip(records, timings):
                    record, stats = json.loads(raw), json.loads(timing)
                    code = record["g6"]
                    route = [(a["vertex"], a.get("reason")) for a in stats["attempts"]]
                    if name == "architect-500":
                        overlap[code] = {"record": record, "route": route}
                    elif code in overlap:
                        previous = overlap[code]
                        if (record["verdict"] == previous["record"]["verdict"] == "embedded"
                                and route == previous["route"]):
                            assert record == previous["record"], "same graph/route changed across sample positions"
                            previous["identical_embedding"] = True
                        previous["also_in_larger_sample"] = True
    result = {"samples": samples,
              "cross_sample_determinism": {
                  "shared_graphs": sum(bool(v.get("also_in_larger_sample")) for v in overlap.values()),
                  "identical_embeddings_with_same_attempt_route":
                      sum(bool(v.get("identical_embedding")) for v in overlap.values())},
              "prototype_comparison": {"prototype_embedded": 445, "prototype_count": 500,
                  "new_embedded": samples["architect-500"]["counts"]["embedded"],
                  "delta": samples["architect-500"]["counts"]["embedded"] - 445,
                  "prototype_search_seconds": 60.029, "prototype_checker_seconds": 25.304},
              "projection": {"population": population, "shards": shards,
                  "four_core_cpu_ideal_hours": cpu_ideal,
                  "four_core_observed_wall_ideal_hours": wall_ideal,
                  "startup_four_core_hour_allowance": startup,
                  "planning_hours_at_80_percent_utilization": math.ceil(wall_ideal / 0.8 + startup),
                  "planning_hours_at_50_percent_utilization": math.ceil(wall_ideal / 0.5 + startup),
                  "formula": "448708 * (graph seconds + full replay seconds) / 5000 / 14400; divide by utilization and add 256 * setup seconds / 14400",
                  "mean_projected_compressed_record_bytes_per_shard":
                      larger["artifacts"]["records.jsonl.gz"]["bytes"] * population / larger["count"] / shards}}
    (RESULTS / "measurements.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"prototype_comparison": result["prototype_comparison"], "projection": result["projection"]}, indent=2))


if __name__ == "__main__":
    main()
