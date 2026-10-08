#!/usr/bin/env python3
"""Throughput of filter/udrhombus on real (23,65) samples, in graphs per CPU-second of one core.

Each sample file is repeated until at least --min-graphs graphs are fed to one udrhombus process
(the prover has no state between graphs, so repetition measures the same work); CPU time is the
child's user + system time from getrusage, which a loaded box inflates less than wall time.
Reports the verdict mix of the sample (one copy) as well.

usage: bench.py FILE.g6 [FILE.g6 ...] [--udrhombus PATH] [--min-graphs N]
"""
from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

from rhlib import UDRHOMBUS, g6_lines, log


def cpu_of_children() -> float:
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--udrhombus", type=Path, default=UDRHOMBUS)
    ap.add_argument("--min-graphs", type=int, default=200000)
    a = ap.parse_args()
    rows = []
    for f in a.files:
        lines = g6_lines(f)
        reps = max(1, -(-a.min_graphs // len(lines)))
        data = ("".join(x + "\n" for x in lines) * reps).encode("ascii")
        c0, w0 = cpu_of_children(), time.monotonic()
        p = subprocess.run(["nice", "-n", "10", str(a.udrhombus)], input=data, capture_output=True)
        cpu, wall = cpu_of_children() - c0, time.monotonic() - w0
        if p.returncode != 0:
            raise SystemExit(f"udrhombus failed on {f}: {p.stderr.decode()[-300:]}")
        stats = json.loads(p.stderr.decode().strip().splitlines()[-1])["udrhombus_stats"]
        n = len(lines) * reps
        verdicts = [json.loads(x)["verdict"] for x in p.stdout.split(b"\n")[:len(lines)]]
        mix = {v: verdicts.count(v) for v in ("pass", "refuted", "tu")}
        row = {"file": f.name, "graphs": n, "cpu_seconds": round(cpu, 3), "wall_seconds": round(wall, 3),
               "graphs_per_cpu_second": round(n / cpu) if cpu else None,
               "sample_verdicts": mix, "flagged_percent": round(100 * (mix["refuted"] + mix["tu"]) / len(lines), 1),
               "mean_cycles": round(stats["cycles"] / n, 1), "max_rank": stats["max_rank"],
               "certificate_failures": stats["certificate_failures"]}
        rows.append(row)
        log(json.dumps(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
