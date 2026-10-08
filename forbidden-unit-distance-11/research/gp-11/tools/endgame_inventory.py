#!/usr/bin/env python3
"""Measure endgame payloads and model SQLite footprint; never verify proofs.

Only reads the supplied sources and writes --out plus temporary files below its
parent. The SQLite model uses the frozen schema with a conservative 256-byte
details value for decided rows. It is NOT a complete checker benchmark.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(paths):
    sizes, verdicts, types, degrees, large = Counter(), Counter(), Counter(), Counter(), []
    for path in paths:
        sizes["stored_bytes"] += path.stat().st_size
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rb") as stream:
            for line_number, raw in enumerate(stream, 1):
                row = json.loads(raw)
                sizes["uncompressed_bytes"] += len(raw)
                sizes["records"] += 1
                sizes["max_record_bytes"] = max(sizes["max_record_bytes"], len(raw))
                verdicts[row["verdict"]] += 1
                kind = row["cert"].get("type", "unknown")
                types[kind] += 1
                degree = len(row["cert"].get("field", {}).get("minpoly", [])) - 1
                if degree > 0:
                    degrees[degree] += 1
                if degree >= 20 or len(raw) >= 500000:
                    large.append({"source": str(path), "line": line_number, "g6": row["g6"],
                                  "type": kind, "degree": degree, "bytes": len(raw),
                                  "sha256": hashlib.sha256(raw).hexdigest()})
    return {**dict(sizes), "verdicts_including_support": dict(verdicts), "types": dict(types),
            "field_degrees": dict(sorted(degrees.items())), "expensive_candidates": sorted(large, key=lambda x: (-x["degree"], -x["bytes"], x["g6"]))}


def sqlite_model(assembly, parent):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".sqlite-model-", dir=parent) as temp:
        os.environ.update(TMPDIR=temp, SQLITE_TMPDIR=temp)
        path = Path(temp) / "index.sqlite"
        db = sqlite3.connect(path)
        db.executescript("""
          PRAGMA cache_size=-8192; PRAGMA temp_store=FILE;
          CREATE TABLE inputs(g6 TEXT PRIMARY KEY);
          CREATE TABLE records(g6 TEXT PRIMARY KEY, verdict TEXT, host INTEGER, dep TEXT,
            status TEXT, reason TEXT, details TEXT);
          CREATE INDEX dependency ON records(dep);
        """)
        count, log_bytes, details_bytes, peak = 0, 0, 0, 0
        for name in ("records.jsonl", "unknown-records.jsonl"):
            with (assembly / name).open("rb") as stream:
                for raw in stream:
                    row = json.loads(raw)
                    code, verdict, cert = row["g6"], row["verdict"], row["cert"]
                    dep = None
                    if cert.get("type") == "super" or cert.get("type") == "sub" and "index" not in cert:
                        dep = cert["g6"]
                    elif cert.get("type") == "tu":
                        dep = cert["end"].get("refuted")
                    details = json.dumps(cert) if verdict == "unknown" else '{"modeled_details":"' + "x" * 234 + '"}'
                    details_bytes += len(details)
                    db.execute("INSERT INTO inputs VALUES (?)", (code,))
                    db.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?)", (code, verdict, 0, dep, "ACCEPT", "verified", details))
                    log_bytes += len((json.dumps({"status": "ACCEPT", "g6": code, "reason": "verified"}) + "\n").encode())
                    count += 1
                    if count % 128 == 0:
                        peak = max(peak, sum(p.stat().st_size for p in Path(temp).iterdir()))
                        db.commit()
        db.commit()
        # Queue holds every graph after resolution; all rows inserted here to
        # measure the end-state footprint, without claiming resolved proofs.
        db.executescript("CREATE TABLE queue(id INTEGER PRIMARY KEY,g6 TEXT UNIQUE); INSERT INTO queue(g6) SELECT g6 FROM records ORDER BY g6;")
        peak = max(peak, sum(p.stat().st_size for p in Path(temp).iterdir()))
        db.commit()
        size = path.stat().st_size
        db.close()
    return {"scope": "synthetic metadata footprint only; no certificate verification", "records": count,
            "sqlite_bytes": size, "sampled_peak_with_journal_bytes": peak,
            "modeled_details_bytes": details_bytes, "one_accept_json_log_bytes": log_bytes,
            "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--bundles", required=True, action="append", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = {"assembly": inventory([args.assembly / "records.jsonl", args.assembly / "unknown-records.jsonl"]), "bundles": {}}
    for root in args.bundles:
        paths = sorted(root.glob("*/records.jsonl.gz"))
        result["bundles"][root.name] = {"shards": len(paths), **inventory(paths)}
    result["sqlite_model"] = sqlite_model(args.assembly, args.out.parent)
    result["source_assembly_sha256"] = sha(args.assembly / "assembly.json")
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.out), "sqlite_model": result["sqlite_model"]}, sort_keys=True))


if __name__ == "__main__":
    main()
