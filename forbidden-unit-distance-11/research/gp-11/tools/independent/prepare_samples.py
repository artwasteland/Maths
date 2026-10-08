#!/usr/bin/env python3
"""Read-only metadata pass; extract bounded samples and their dependency closure.

This is NOT a population certificate check. It reads the stream once to find
offsets, the first N records, representatives, and the K largest refutations.
The canonical index of B11 is used only to close sampled edge deletions.
"""
import argparse
from collections import Counter
import heapq
import json
from pathlib import Path
import time

from independent_core import biconnected, decode_g6, iso_key, lines, require, write_json, guard_outputs


def prepare(b11, records, outdir, first=2000, largest=20):
    t0 = time.monotonic()
    out = Path(outdir)
    names = ("first2000", "largest20", "by-type", "first2000-closed", "largest20-closed")
    guard_outputs([b11, records], [out / (name + suffix) for name in names for suffix in (".g6", ".jsonl")]
                  + [out / "manifest.json"])
    out.mkdir(parents=True, exist_ok=True)
    index, firsts, representatives, sizes, types = {}, [], {}, [], Counter()
    offset = 0
    for number, raw in lines(records):
        r = json.loads(raw)
        g, c = r["g6"], r["cert"]
        t = c.get("type")
        deps = []
        if t in {"sub", "super"} and "index" not in c:
            deps.append(c["g6"])
        if t == "tu" and "refuted" in c.get("end", {}):
            deps.append(c["end"]["refuted"])
        require(g not in index, "duplicate_record", f"duplicate record while sampling {g}")
        index[g] = (offset, len(raw), r["verdict"], t, tuple(deps))
        if number <= first:
            firsts.append(g)
        representatives.setdefault(t, g)
        if "sos" in c:
            representatives.setdefault(t + "+sos", g)
        if r["verdict"] == "refuted":
            heapq.heappush(sizes, (len(raw), g))
            if len(sizes) > largest:
                heapq.heappop(sizes)
        types[f"{r['verdict']}/{t}"] += 1
        offset += len(raw)
        if number % 50000 == 0:
            print(f"metadata {number}; {offset/1e9:.2f} GB; {time.monotonic()-t0:.1f}s", flush=True)
    scan_seconds = time.monotonic() - t0
    biggest = [g for size, g in sorted(sizes, reverse=True)]
    population, canonical = [], {}
    for number, raw in lines(b11):
        g = raw[:-1].decode("ascii")
        population.append(g)
        canonical[iso_key(*decode_g6(g))] = g
        if number % 100000 == 0:
            print(f"sample lookup index {number}; {time.monotonic()-t0:.1f}s", flush=True)

    def closure(seeds, deletions):
        seen, todo = set(), list(seeds)
        while todo:
            g = todo.pop()
            if g in seen:
                continue
            require(g in index, "sample_dependency", f"sample dependency has no record: {g}")
            seen.add(g)
            todo.extend(index[g][4])
            if deletions and index[g][2] == "refuted":
                n, edges = decode_g6(g)
                for edge in edges:
                    deletion = edges - {edge}
                    if biconnected(n, deletion):
                        h = canonical.get(iso_key(n, deletion))
                        require(h is not None, "sample_deletion", f"sample biconnected deletion missing for {g}")
                        todo.append(h)
        return sorted(seen)

    groups = {"first2000": firsts, "largest20": biggest,
              "by-type": sorted(set(representatives.values())),
              "first2000-closed": closure(firsts, False),
              "largest20-closed": closure(biggest + list(representatives.values()), True)}
    summary = {}
    with open(records, "rb") as stream:
        for name, selected in groups.items():
            with (out / (name + ".jsonl")).open("wb") as f:
                for g in selected:
                    pos, length, _, _, _ = index[g]
                    stream.seek(pos)
                    f.write(stream.read(length))
            (out / (name + ".g6")).write_text("".join(g + "\n" for g in sorted(selected)))
            summary[name] = {"records": len(selected), "bytes": sum(index[g][1] for g in selected),
                             "types": dict(Counter(index[g][3] for g in selected))}
    rep = {"scope": "metadata indexing and sampled closure only; no full-population verification",
           "records_source": str(records), "B11_source": str(b11), "source_records": len(index),
           "source_bytes": offset, "metadata_types": dict(types), "representatives": representatives,
           "largest": [{"g6": g, "bytes": size} for size, g in sorted(sizes, reverse=True)],
           "samples": summary, "metadata_scan_seconds": round(scan_seconds, 3),
           "seconds": round(time.monotonic() - t0, 3)}
    write_json(out / "manifest.json", rep)
    print(json.dumps(rep["samples"], sort_keys=True), flush=True)
    return rep


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("b11")
    p.add_argument("records")
    p.add_argument("outdir")
    p.add_argument("--first", type=int, default=2000)
    p.add_argument("--largest", type=int, default=20)
    a = p.parse_args()
    require(a.first > 0 and a.largest > 0, "arguments", "sample sizes must be positive")
    prepare(a.b11, a.records, a.outdir, a.first, a.largest)
