#!/usr/bin/env python3
"""AddressSanitizer + UBSan runs of the new set-398 code paths, with a red control.

Builds the new enum/udenum.c with -fsanitize=address,undefined (as asan.py does), plus the two
switch-forcing variants of speed398-identity.py and the one tracking uncovered sets on every order
(UNCOVERED_MIN_ORDER=1), and runs each on inputs that drive every new path:
the pattern path and the restricted path in both oracles (child containment, anchored family T),
--verify-parents (the parent containment), --filter (containment on 10-vertex hosts, where the
10-vertex members are searched), and parents that contain a forbidden graph.  Every run must be
sanitizer-clean and write output byte-identical to the optimized (non-sanitized) build.

Red control: SearchContext.map shrunk to SG_MAX - 1 entries (a 10-vertex forbidden graph writes
map[9]) must produce a sanitizer report.  (asan.py's own red control plants old sizes into
ExistsContext, which set 398 no longer uses; this is its counterpart for the new code.)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from speed398lib import F398, F398_G6, NEW_SOURCE, NEW_UDENUM, SCRATCH, g6_lines, g6_order_size, run_udenum, write_lines

FLAGS = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-std=c17",
         "-I/usr/include/x86_64-linux-gnu/nauty", "-I/usr/include/nauty"]


def build(source: Path, binary: Path, defines=()) -> Path:
    binary.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["nice", "-n", "15", "cc", *FLAGS, *[f"-D{d}" for d in defines], str(source), "-o", str(binary),
                    "-lnauty"], check=True, capture_output=True)
    return binary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speed-work", type=Path, required=True)
    ap.add_argument("--slices", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=SCRATCH / "speed398-asan")
    a = ap.parse_args()
    w = a.work
    w.mkdir(parents=True, exist_ok=True)
    builds = {"asan": build(NEW_SOURCE, w / "udenum-asan"),
              "asan-K1": build(NEW_SOURCE, w / "udenum-asan-K1", ["RESTRICTED_SWITCH_CANDIDATES=1"]),
              "asan-Kinf": build(NEW_SOURCE, w / "udenum-asan-Kinf", ["RESTRICTED_SWITCH_CANDIDATES=4000000000"]),
              "asan-U1": build(NEW_SOURCE, w / "udenum-asan-U1", ["UNCOVERED_MIN_ORDER=1"])}
    l21 = w / "l21-all.g6"
    write_lines(l21, [g for s in range(48) for g in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
    sw = a.speed_work
    inputs = [("L12 (13,23) free", sw / "measure-12-23.free.g6", 13, 23, []),
              ("L16 (17,38) free", sw / "measure-16-38.free.g6", 17, 38, []),
              ("L16 (17,38) free --verify-parents", sw / "measure-16-38.free.g6", 17, 38, ["--verify-parents"]),
              ("L17 (18,42) all", sw / "measure-17-42.all.g6", 18, 42, []),
              ("L18 (19,47) all", sw / "measure-18-47.all.g6", 19, 47, []),
              ("L21 (22,61) the 743 real parents", l21, 22, 61, []),
              ("L21 (22,61) --verify-parents (must refuse)", l21, 22, 61, ["--verify-parents"])]
    by_nm: dict[tuple[int, int], list[bytes]] = {}
    for g in g6_lines(F398_G6):
        by_nm.setdefault(g6_order_size(g), []).append(g)
    for (n, m), gs in sorted(by_nm.items()):
        if n == 10:
            f = w / f"members-{m}.g6"
            write_lines(f, gs)
            inputs.append((f"--filter the 10-vertex members with {m} edges", f, 10, m, ["--filter"]))
    bad = 0
    (w / "out").mkdir(parents=True, exist_ok=True)
    for label, parents, n, m, extra in inputs:
        ref = run_udenum(NEW_UDENUM, parents, n, m, w / "ref" / f"{abs(hash(label))}.g6", extra=extra)
        for bname, b in builds.items():
            out = w / "out" / f"{bname}-{abs(hash(label))}.g6"
            cmd = ["nice", "-n", "15", str(b), "--parents", str(parents), "--forbidden",
                   str(F398), "--forbidden-set", "398",
                   "--n", str(n), "--m", str(m), "--output", str(out), "--manifest", f"{out}.json", "--shard-id", "a",
                   "--overwrite", *extra]
            p = subprocess.run(cmd, capture_output=True, text=True)
            san = [x for x in p.stderr.splitlines() if "Sanitizer" in x or "runtime error" in x]
            tail = [x for x in p.stderr.strip().splitlines() if x.strip()]
            tail = tail[-1] if tail else ""
            # same exit status, same output bytes, and for a refusal the same message
            same = (p.returncode == ref["returncode"] and out.exists() and Path(ref["output"]).exists()
                    and out.read_bytes() == Path(ref["output"]).read_bytes()
                    and (p.returncode == 0 or tail == ref["stderr_tail"]))
            ok = not san and same
            bad += not ok
            print(f"{bname:10s} {label}: exit {p.returncode} (optimized build {ref['returncode']}), sanitizer lines "
                  f"{len(san)}, output identical {same}: {'ok' if ok else 'BAD'}"
                  + ("" if ok else f" [{tail[:120]}]"), flush=True)
            for x in san[:3]:
                print("    ", x)
    # red control
    src = NEW_SOURCE.read_text()
    old = "    uint32_t vertex_mask[SG_MAX];   /* host vertices passing the per-vertex filters, per position */\n    int map[SG_MAX];\n"
    if src.count(old) != 1:
        print("cannot locate SearchContext in udenum.c")
        return 2
    redsrc = w / "udenum-smallmap.c"
    redsrc.write_text(src.replace(old, old.replace("int map[SG_MAX];", "int map[SG_MAX - 1];")))
    red = build(redsrc, w / "udenum-smallmap-asan")
    f = w / "members-16.g6"
    out = w / "red.g6"
    p = subprocess.run(["nice", "-n", "15", str(red), "--parents", str(f), "--forbidden",
                        str(F398), "--forbidden-set", "398",
                        "--n", "10", "--m", "16", "--filter", "--output", str(out), "--manifest", f"{out}.json",
                        "--shard-id", "red", "--overwrite"], capture_output=True, text=True)
    san = [x for x in p.stderr.splitlines() if "Sanitizer" in x or "runtime error" in x]
    went_red = bool(san)
    print(f"RED CONTROL {'went red' if went_red else 'DID NOT GO RED'}: SearchContext.map[SG_MAX - 1], --filter the "
          f"16-edge members: exit {p.returncode}, sanitizer lines {len(san)}", flush=True)
    for x in san[:2]:
        print("    ", x)
    ok = not bad and went_red
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
