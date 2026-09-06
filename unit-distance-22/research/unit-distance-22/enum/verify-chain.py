#!/usr/bin/env python3
"""The stranger's check of a pruned DAG directory (enum/PRUNING.md, Section 3).

Trusting nothing but the files, it verifies, for a run-dag2.py output directory:
  (c) reach.json's table follows from its root by the L4 recursion, and every
      <n>-<m>.reach.g6 equals <n>-<m>.g6 minus the graphs of minimum degree below k(n, m);
  (b) every <n>-<m>.keep.g6 equals, in order, the records of <n>-<m>.certs.jsonl with verdict
      embedded or unknown, the certs list equals the stage input, and every pruned graph has a
      tu or refuted witness object;
  (d) every _parents/<n>-<m>.g6 is the byte concatenation of the parent sources listed in the
      aggregate manifest, with the listed hashes, and those sources are exactly the stage files
      of the parents L4 allows (or Schade's window without --reach);
  (e) every shard manifest hashes the parent file it names and the shard ranges tile it;
  (a) with --check, check/udcheck.py replays every certs file against its stage input.
It does not verify the generator itself (CONTRACT 3.6 controls do that).
usage: verify-chain.py RUN_DIR [--check] [--from-n N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PYTHON = Path("~/tools/pyenv-maths/bin/python").expanduser()


class Bad(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise Bad(f"{path}: missing final newline")
    return raw.decode("ascii").split("\n")[:-1] if raw else []


def graph6(code: str) -> tuple[int, int, int]:
    n = ord(code[0]) - 63
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    deg = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                deg[i] += 1
                deg[j] += 1
            k += 1
    return n, sum(deg) // 2, (min(deg) if n else 0)


def recompute_reach(reach: dict) -> dict[int, dict[int, int]]:
    tn, tm = reach["target"]
    ubar = {int(k): v for k, v in reach["ubar"].items()}
    table = {tn: {tm: reach["root_k"]}}
    for n in range(tn - 1, reach["seed_n"] - 1, -1):
        level: dict[int, int] = {}
        for cm, k in table[n + 1].items():
            for d in range(k, min(n, (2 * cm) // (n + 1)) + 1):
                m = cm - d
                if 0 <= m <= ubar[n]:
                    level[m] = min(level.get(m, d), max(0, d - 1))
        table[n] = level
    return table


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--check", action="store_true", help="replay every certs file with udcheck.py")
    ap.add_argument("--from-n", type=int, default=0, help="only inspect levels with n >= this")
    a = ap.parse_args()
    run = a.run.resolve()
    summary = json.loads((run / "run-summary.json").read_text())
    tn, tm = summary["target"]
    seed_n = summary["seed_n"]
    config = json.loads((run / "run-config.json").read_text())
    reach = json.loads((run / "reach.json").read_text()) if config["reach"] else None
    table = None
    problems: list[str] = []
    checked = {"reach_files": 0, "keep_files": 0, "parent_files": 0, "shards": 0, "certs_replayed": 0}
    if reach is not None:
        table = recompute_reach(reach)
        stored = {int(n): {int(m): k for m, k in lv.items()} for n, lv in reach["table"].items()}
        if stored != table:
            problems.append("reach.json table does not follow from its root by the L4 recursion")
        if (tn, tm) == (22, 61) and reach["root_k"] != 5 and "D4" in reach["root_k_source"]:
            problems.append("reach.json claims D4 but root_k is not 5")
    ubar = {int(k): v for k, v in reach["ubar"].items()} if reach else None
    windows = {int(k): tuple(v) for k, v in summary["windows"].items()}
    prune_from = config["prune_from"] if config["prune"] else None

    def stage(n: int, m: int) -> tuple[Path, str]:
        if prune_from is not None and n >= prune_from:
            return run / f"{n}-{m}.keep.g6", "keep"
        if table is not None:
            return run / f"{n}-{m}.reach.g6", "reach"
        return run / f"{n}-{m}.g6", "full"

    levels = [(l["n"], l["m"]) for l in summary["levels"] if l["n"] >= max(a.from_n, seed_n)]
    for n, m in levels:
        full = run / f"{n}-{m}.g6"
        codes = lines(full)
        for code in codes:
            vn, vm, _ = graph6(code)
            if (vn, vm) != (n, m):
                problems.append(f"{full.name}: graph {code} is ({vn},{vm})")
                break
        # (c) reach file
        if table is not None:
            k = table[n][m]
            reach_file = run / f"{n}-{m}.reach.g6"
            expected = [c for c in codes if graph6(c)[2] >= k]
            if lines(reach_file) != expected:
                problems.append(f"{reach_file.name}: is not the level file minus minimum degree < {k}")
            rm = json.loads((run / f"{n}-{m}.reach.manifest.json").read_text())
            if rm.get("k") != k or rm.get("output_sha256") != sha256(reach_file) or rm.get("input_sha256") != sha256(full):
                problems.append(f"{reach_file.name}: reach manifest hashes or k do not match")
            checked["reach_files"] += 1
        # (b) keep file
        if prune_from is not None and n >= prune_from:
            source = run / (f"{n}-{m}.reach.g6" if table is not None else f"{n}-{m}.g6")
            certs = run / f"{n}-{m}.certs.jsonl"
            keep = run / f"{n}-{m}.keep.g6"
            unknown = run / f"{n}-{m}.UNKNOWN.g6"
            records = [json.loads(l) for l in lines(certs)]
            if [r["g6"] for r in records] != lines(source):
                problems.append(f"{certs.name}: record list is not the stage input {source.name}")
            if lines(keep) != [r["g6"] for r in records if r["verdict"] in ("embedded", "unknown")]:
                problems.append(f"{keep.name}: is not the embedded and unknown records in order")
            if lines(unknown) != [r["g6"] for r in records if r["verdict"] == "unknown"]:
                problems.append(f"{unknown.name}: is not the unknown records in order")
            for r in records:
                if r["verdict"] in ("tu", "refuted") and not isinstance(r.get("witness"), dict):
                    problems.append(f"{certs.name}: pruned graph {r['g6']} has no witness")
                    break
                if r["verdict"] not in ("tu", "refuted", "embedded", "unknown"):
                    problems.append(f"{certs.name}: verdict {r['verdict']} for {r['g6']}")
                    break
            pm = json.loads((run / f"{n}-{m}.prune.manifest.json").read_text())
            if pm.get("exit_status") != 0 or any(pm.get("mutation", {}).values()):
                problems.append(f"{n}-{m}: prune manifest is not a clean success")
            for path in (certs, keep, unknown):
                if pm.get("outputs_sha256", {}).get(str(path)) != sha256(path):
                    problems.append(f"{path.name}: hash differs from the prune manifest")
            if pm.get("inputs_sha256", {}).get(str(source)) != sha256(source):
                problems.append(f"{source.name}: hash differs from the prune manifest input")
            checked["keep_files"] += 1
            if a.check:
                cmd = [str(PYTHON), str(ROOT / "check" / "udcheck.py"), "--expect-n", str(n), "--expect-m", str(m),
                       "--graphs", str(source), "--unknown-file", str(unknown), str(certs)]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0 or not res.stdout.startswith("ACCEPT certificates"):
                    problems.append(f"{certs.name}: udcheck did not accept: {res.stderr.strip()[:200]}")
                checked["certs_replayed"] += 1
        # (d) parent file of this level and (e) shards
        if n > seed_n:
            am = json.loads((run / f"{n}-{m}.manifest.json").read_text())
            parent_file = Path(am["parent_file"])
            lower = max(math.ceil(m * (n - 2) / n), windows[n - 1][0])
            upper = min(ubar[n - 1] if ubar else windows[n - 1][1], m, windows[n - 1][1])
            allowed = [pm_ for pm_ in range(lower, upper + 1)
                       if table is None or m - pm_ >= table[n][m]]
            listed = am.get("parent_sources")
            if listed is None:
                problems.append(f"{n}-{m}: aggregate manifest lists no parent_sources")
                continue
            if [s["level"][1] for s in listed] != allowed or any(s["level"][0] != n - 1 for s in listed):
                problems.append(f"{n}-{m}: listed parent levels {[s['level'] for s in listed]} are not the allowed {allowed}")
            blob = b""
            for s in listed:
                path, kind = stage(n - 1, s["level"][1])
                if Path(s["file"]) != path or s["kind"] != kind:
                    problems.append(f"{n}-{m}: parent source {s['file']} ({s['kind']}) is not the stage file {path} ({kind})")
                if not path.is_file() or sha256(path) != s["sha256"]:
                    problems.append(f"{n}-{m}: parent source {path.name} hash differs from the manifest")
                    continue
                blob += path.read_bytes()
            if not parent_file.is_file() or hashlib.sha256(blob).hexdigest() != sha256(parent_file):
                problems.append(f"{n}-{m}: {parent_file.name} is not the concatenation of the listed sources")
            if am["inputs_sha256"].get(str(parent_file)) != sha256(parent_file):
                problems.append(f"{n}-{m}: aggregate manifest does not hash its parent file")
            if am.get("children_file_sha256") != sha256(full):
                problems.append(f"{n}-{m}: aggregate manifest does not hash its level file")
            if table is not None and am.get("reach", {}).get("reach_json_sha256") != sha256(run / "reach.json"):
                problems.append(f"{n}-{m}: aggregate manifest does not hash reach.json")
            count = len(lines(parent_file))
            ranges = []
            for sm in sorted((run / "shards" / f"{n}-{m}").glob("*.manifest.json")):
                info = json.loads(sm.read_text())
                if info.get("exit_status") != 0 or Path(info["parent_file"]) != parent_file:
                    problems.append(f"{sm.name}: bad status or parent file")
                if info["inputs_sha256"].get(str(parent_file)) != sha256(parent_file):
                    problems.append(f"{sm.name}: does not hash the parent file")
                if table is not None and info["software_sha256"].get("reach.json") != sha256(run / "reach.json"):
                    problems.append(f"{sm.name}: does not hash reach.json")
                ranges.append(tuple(info["parent_range"]))
                checked["shards"] += 1
            ranges.sort()
            if count and (not ranges or ranges[0][0] != 0 or ranges[-1][1] != count or
                          any(ranges[i][1] != ranges[i + 1][0] for i in range(len(ranges) - 1))):
                problems.append(f"{n}-{m}: shard ranges {ranges} do not tile the parent file of {count} records")
            checked["parent_files"] += 1
    print(json.dumps({"run": str(run), "target": [tn, tm], "levels_inspected": len(levels), **checked}))
    for p in problems:
        print("PROBLEM:", p)
    print("CHAIN", "OK" if not problems else f"FAIL ({len(problems)} problems)")
    return 0 if not problems else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Bad, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"verify-chain.py: {error!r}", file=sys.stderr)
        sys.exit(2)
