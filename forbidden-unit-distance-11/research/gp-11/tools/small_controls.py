#!/usr/bin/env python3
"""Replay B4p..B9p, GP-10 named/regressions, then search and check named11.

Run under guard.py. The B10 control remains a separate explicit cloud command.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "check"))
import gp11check as ck


def check(path):  # B11 harness addition.
    with (path / "gp11-check.txt").open("w") as log:
        run = ck.Run(path, emit=lambda text: log.write(text + "\n"))
        result = run.execute()
    print(f"{result['status']} {result.get('profile')} reason={result['reason']} "
          f"counts={result.get('counts')} minimal={result.get('minimal_count')} control={result.get('control')}", flush=True)
    if result["status"] != "ACCEPT":
        raise RuntimeError(result)


def main():  # B11 harness addition.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    args = parser.parse_args()
    tree = args.tree.resolve()
    for name in (*ck.base.CONTROL_ORDERS, "named", "regressions"):
        check(tree / "controls" / name)
    named = tree / "controls/named11"
    named.mkdir(exist_ok=True)
    codes = ck.canonical_many([c for c in (ck.U22 / "sources/amp/anc/graph6.txt").read_text().splitlines()
                              if ck.decode(c).n == 11])
    (named / "input.g6").write_text("".join(c + "\n" for c in sorted(codes)))
    # No host/library method: the graph6 source supplies only the problem instances.
    command = [sys.executable, str(ck.GP10 / "embed/gp10embed.py"), str(named / "input.g6"),
               "--out", str(named / "records.jsonl"), "--unknown", str(named / "UNKNOWN.g6"),
               "--stats", str(named / "search-stats.jsonl"), "--methods", "lattice18,lattice36,lattice30,constructive,numeric",
               "--time-limit", "20", "--node-cap", "200000"]
    with (named / "search.txt").open("w") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    ck.json_write(named / "provenance.json", {c: {"method": "general-search", "evidence":
        "gp10embed.py without host method; search.txt and search-stats.jsonl; command=" + repr(command)} for c in codes})
    ck.json_write(named / "run.json", {"profile": "named11", "input": "input.g6",
        "input_sha256": ck.digest(named / "input.g6"), "records": ["records.jsonl"], "provenance": "provenance.json"})
    check(named)
    print("SMALL CONTROLS PASS; B10 control not executed", flush=True)


if __name__ == "__main__":
    main()
