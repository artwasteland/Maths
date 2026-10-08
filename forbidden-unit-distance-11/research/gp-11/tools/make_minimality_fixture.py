#!/usr/bin/env python3
"""Untrusted bounded fixture producer; retain ordinary certificates only.

The committed fixture is replayed by selftest.py without importing this producer.
No outcome of failed search is treated as a refutation.
"""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "check"))
import gp11check as ck
sys.path.insert(0, str(ck.GP10 / "embed"))
import gp10embed as producer


def main():  # B11 fixture producer addition.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path, default=ck.HERE / "fixtures/tree11.json")
    args = parser.parse_args()
    parent = ck.read_json(args.source)
    graph = ck.decode(parent["g6"])
    children = sorted({ck.canonical(ck.Graph(graph.n, graph.edges - {e})) for e in graph.edges
                       if ck.nx.is_biconnected(ck.Graph(graph.n, graph.edges - {e}).nx())})
    methods = ("lattice18", "lattice36", "lattice30", "constructive")
    producer.warm(methods)
    records = [parent]
    for child in children:
        record, stats = producer.run_one(child, time_limit=4, methods=methods, node_cap=200000)
        print(child, record["verdict"], flush=True)
        records.append(record)
    args.output.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records))
    print("FIXTURE SEARCH", {v: sum(r["verdict"] == v for r in records) for v in ("embedded", "refuted", "unknown")})


if __name__ == "__main__":
    main()
