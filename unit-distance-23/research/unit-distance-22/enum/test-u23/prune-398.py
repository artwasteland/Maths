#!/usr/bin/env python3
"""prune.py --forbidden-set 398: the set reaches the filter, and filter parts never cross sets.

Input: a Mode 74 level file X that contains graphs with one of GP-10's 324 (e2e.py's new74
12-m.reach.g6) and the Mode 398 file of the same level (new398), copied into scratch.

  P1 set 398 on X: exit 2, "GENERATOR BUG" naming a witness index >= 74 (udfilter -s 398 is
     really used: the graph is 74-free, so set 74 could not see it)
  P2 set 74 on X: exit 0 (X is 74-free), manifest without forbidden_set, inputs hash
     forbidden-74.json, udcheck.py only
  P3 set 398 on the Mode 398 file: exit 0; manifest says forbidden_set 398, hashes the pinned
     forbidden-398.json, names udcheck398.py; its certificates are P2's for the 398-free graphs
  P4 red, parts across sets: set 74 on X, then set 398 on X in the SAME directory. Reusing the
     set-74 filter parts would hide the 324 and exit 0; the set marker must discard them (exit 2)
  P5 red, the other way: set 398 on X (fails, leaving parts with "forbidden" verdicts), then set
     74 on X in the same directory must discard them and exit 0
  P6 the bound: target (23,64) refused (below u(23) <= 65), (23,65) accepted by the bound check,
     its manifest naming the source of the bound

usage: prune-398.py --e2e-dir <U23_SCRATCH>/e2e-17-43 [--level 12-22]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from u23lib import ENUM, F398_SHA256, MATHS_PY, SCRATCH, F74_SHA256, log

PRUNE = ENUM / "prune.py"
problems: list[str] = []


def prune(level: Path, forbidden_set: int, n: int = 17, m: int = 43) -> tuple[int, str, dict | None]:
    cmd = ["nice", "-n", "15", sys.executable, str(PRUNE), "--level", str(level), "--target-n", str(n),
           "--target-m", str(m), "--filter-only", "--jobs", "1", "--python", str(MATHS_PY), "--overwrite"]
    if forbidden_set != 74:
        cmd += ["--forbidden-set", str(forbidden_set)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    manifest = level.parent / f"{level.name.split('.')[0]}.prune.manifest.json"
    info = json.loads(manifest.read_text()) if manifest.is_file() and p.returncode == 0 else None
    return p.returncode, (p.stderr.strip().splitlines() or [""])[-1], info


def fresh(name: str, source: Path, level: str) -> Path:
    d = SCRATCH / "prune-398" / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    shutil.copy2(source, d / f"{level}.reach.g6")
    return d / f"{level}.reach.g6"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e2e-dir", type=Path, required=True)
    ap.add_argument("--level", default="12-22")
    a = ap.parse_args()
    x74 = a.e2e_dir / "new74" / f"{a.level}.reach.g6"
    x398 = a.e2e_dir / "new398" / f"{a.level}.reach.g6"
    # P1
    code, msg, _ = prune(fresh("p1", x74, a.level), 398)
    idx = None
    if "GENERATOR BUG" in msg and "'index': " in msg:
        idx = int(msg.split("'index': ")[1].split(",")[0])
    log(f"P1 set 398 on the Mode 74 file: exit {code}: {msg[:160]}")
    if code != 2 or idx is None or idx < 74:
        problems.append(f"P1: expected a GENERATOR BUG with a member >= 74, got exit {code}: {msg[:200]}")
    # P2
    level74 = fresh("p2", x74, a.level)
    code, msg, info = prune(level74, 74)
    ok = (code == 0 and info is not None and "forbidden_set" not in info and
          F74_SHA256 in info["inputs_sha256"].values() and "udcheck398.py" not in info["software_sha256"])
    log(f"P2 set 74 on the Mode 74 file: exit {code}; counts {info and info['counts']}; manifest as in u(22): {ok}")
    if not ok:
        problems.append(f"P2: exit {code}: {msg[:200]}")
    # P3
    level398 = fresh("p3", x398, a.level)
    code, msg, info = prune(level398, 398)
    ok = (code == 0 and info is not None and info.get("forbidden_set") == 398 and
          F398_SHA256 in info["inputs_sha256"].values() and "udcheck398.py" in info["software_sha256"])
    certs74 = (level74.parent / f"{a.level}.certs.jsonl").read_text().splitlines()
    certs398 = (level398.parent / f"{a.level}.certs.jsonl").read_text().splitlines()
    free = {line.strip() for line in x398.read_text().splitlines()}
    expected = [c for c in certs74 if json.loads(c)["g6"] in free]
    same = certs398 == expected
    log(f"P3 set 398 on the Mode 398 file: exit {code}; counts {info and info['counts']}; manifest says set 398, "
        f"pinned file, udcheck398.py: {ok}; certificates = Mode 74's for the 398-free graphs: {same} "
        f"({len(certs398)} of {len(certs74)})")
    if not ok or not same:
        problems.append(f"P3: exit {code}, manifest ok {ok}, certificates equal {same}: {msg[:200]}")
    # P4
    level = fresh("p4", x74, a.level)
    code1, _, _ = prune(level, 74)
    parts = sorted(p.name for p in (level.parent / "_prune" / a.level).glob("filter-*.jsonl"))
    code2, msg2, _ = prune(level, 398)
    log(f"P4 set 74 then set 398 in one directory: first exit {code1} (left {len(parts)} filter parts), "
        f"second exit {code2}: {msg2[:120]}")
    if code1 != 0 or not parts or code2 != 2 or "GENERATOR BUG" not in msg2:
        problems.append(f"P4: set-74 filter parts were reused by set 398 (exit {code2})")
    # P5
    level = fresh("p5", x74, a.level)
    code1, _, _ = prune(level, 398)
    marker = (level.parent / "_prune" / a.level / "forbidden-set.txt").read_text().strip()
    code2, msg2, _ = prune(level, 74)
    log(f"P5 set 398 then set 74 in one directory: first exit {code1} (marker {marker!r}), second exit {code2}")
    if code1 != 2 or marker != "398" or code2 != 0:
        problems.append(f"P5: set-398 filter parts were reused by set 74 (exit {code2}: {msg2[:160]})")
    # P6
    code, msg, _ = prune(fresh("p6a", x398, a.level), 398, 23, 64)
    log(f"P6 target (23,64): exit {code}: {msg[:150]}")
    if code != 2 or "below the proved bound" not in msg:
        problems.append(f"P6: (23,64) not refused: {msg}")
    code, msg, info = prune(fresh("p6b", x398, a.level), 398, 23, 65)
    bound = info and info.get("tu_rule_bound")
    log(f"P6 target (23,65): exit {code}; tu_rule_bound {bound}")
    if code != 0 or not bound or bound.get("proved_upper_bound") != 65 or "RESULT-u22.md" not in bound.get("source", ""):
        problems.append(f"P6: (23,65) not accepted with its bound's source: exit {code} {msg[:160]}")
    for p in problems:
        log("PROBLEM:", p)
    log("PRUNE-398", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
