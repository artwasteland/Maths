#!/usr/bin/env python3
"""What set 398 costs in the prune step and in the stage verification, per graph, by order.

For real cells of the u(22) runs, restricted to their 398-free graphs (a set-398 run only ever
filters 398-free graphs), one process at a time, CPU seconds from the child's rusage:
  udfilter -s 74     the u(22) prune step's filter
  udfilter -s 398    the set-398 prune step's filter (prune.py --forbidden-set 398)
  udenum --verify-parents --forbidden-set 398   run-dag2.py --verify-stages on the same graphs
Informational: nothing here passes or fails. usage: timing.py --slices <dir of s0of48..s47of48>
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import time
from pathlib import Path

from u23lib import DATA, ENUM, SCRATCH, UD, UDENUM, UDFILTER, decode_g6, g6_lines, log, write_lines

WORK = SCRATCH / "timing"


def cpu_run(cmd: list[str], stdin: Path) -> tuple[float, float, int]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    with stdin.open("rb") as f:
        p = subprocess.run(cmd, stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    wall = time.monotonic() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return after.ru_utime - before.ru_utime + after.ru_stime - before.ru_stime, wall, p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slices", type=Path, required=True)
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    cells = [("12-23 (u22 DAG)", ENUM / "out-22" / "dag-22-61" / "12-23.g6"),
             ("13-23 sample", UD / "results" / "u22" / "sample-13-23-unpruned.g6"),
             ("15-34 (18,46) DAG", ENUM / "out-sup" / "dag-18-46" / "15-34.g6"),
             ("16-38 (18,46) DAG", ENUM / "out-sup" / "dag-18-46" / "16-38.g6"),
             ("17-42 (18,46) DAG", ENUM / "out-sup" / "dag-18-46" / "17-42.g6")]
    top = WORK / "21-56.keep.g6"
    write_lines(top, [x for s in range(48) for x in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
    cells.append(("21-56 keep (48 slices)", top))
    rows = []
    for label, path in cells:
        lines = g6_lines(path)
        n, edges = decode_g6(lines[0])
        m = len(edges)
        # the 398-free graphs of the cell, by udfilter -s 398 itself (its verdicts were compared
        # with an independent matcher on these cells in REPORT-398.md 4.2)
        p = subprocess.run([str(UDFILTER), "-s", "398", "-f", str(DATA / "forbidden-398.json"),
                            "-t", str(DATA / "tu-gadgets.json")], input=b"".join(x + b"\n" for x in lines),
                           capture_output=True, check=True)
        free = [json.loads(r)["g6"].encode() for r in p.stdout.split(b"\n") if r and
                json.loads(r)["verdict"] != "forbidden"]
        hosts = WORK / f"{n}-{m}.free.g6"
        write_lines(hosts, free)
        t74 = cpu_run(["nice", "-n", "15", str(UDFILTER), "-f", str(DATA / "forbidden-74.json"),
                       "-t", str(DATA / "tu-gadgets.json")], hosts)
        t398 = cpu_run(["nice", "-n", "15", str(UDFILTER), "-s", "398", "-f", str(DATA / "forbidden-398.json"),
                        "-t", str(DATA / "tu-gadgets.json")], hosts)
        out = WORK / f"{n}-{m}.verify.g6"
        tv = cpu_run(["nice", "-n", "15", str(UDENUM), "--verify-parents", "--forbidden-set", "398",
                      "--forbidden", str(DATA / "forbidden-398.json"), "--parents", str(hosts),
                      "--n", str(n + 1), "--m", str(m + n), "--output", str(out),
                      "--manifest", str(out.with_suffix(".manifest.json")), "--shard-id", "timing",
                      "--overwrite"], Path(os.devnull))
        k = max(len(free), 1)
        rows.append((label, n, m, len(lines), len(free), 1e3 * t74[0] / k, 1e3 * t398[0] / k, 1e3 * tv[0] / k,
                     t74[2], t398[2], tv[2]))
    log("cell | order | edges | graphs | 398-free | ms/graph udfilter -s 74 | -s 398 | ratio | "
        "udenum --verify-parents 398 | exits")
    for r in rows:
        log(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]:.3f} | {r[6]:.3f} | {r[6] / max(r[5], 1e-9):.1f}x | "
            f"{r[7]:.3f} | {r[8]},{r[9]},{r[10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
