#!/usr/bin/env python3
"""Build the F-free canonical augmentation DAG with frozen parent shards."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone


UBAR = {
    0: 0,
    1: 0,
    2: 1,
    3: 3,
    4: 5,
    5: 7,
    6: 9,
    7: 12,
    8: 14,
    9: 18,
    10: 20,
    11: 23,
    12: 27,
    13: 30,
    14: 33,
    15: 37,
    16: 41,
    17: 43,
    18: 46,
    19: 50,
    20: 54,
    21: 57,
    22: 62,
    23: 66,
}


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-n", type=int, required=True)
    parser.add_argument("--target-m", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-n", type=int, default=10)
    parser.add_argument("--shard-size", type=int, default=10000)
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=1)
    parser.add_argument("--udenum", type=Path, default=here / "udenum")
    parser.add_argument("--forbidden", type=Path,
                        default=here.parent / "data" / "forbidden-74.json")
    parser.add_argument("--geng", type=Path, default=Path("/usr/bin/nauty-geng"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-parents", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_count(path: Path) -> int:
    with path.open("rb") as stream:
        return sum(1 for line in stream
                   if line.strip() and not line.startswith(b">>graph6<<"))


def windows_for(target_n: int, target_m: int, seed_n: int) -> dict[int, tuple[int, int]]:
    if target_n not in UBAR or seed_n < 1 or seed_n >= target_n:
        raise ValueError("target and seed orders must lie in the known u-bar table")
    windows = {target_n: (target_m, target_m)}
    for n in range(target_n, seed_n, -1):
        child_low, child_high = windows[n]
        lower = math.ceil(child_low * (n - 2) / n)
        upper = min(UBAR[n - 1], child_high)
        if lower > upper:
            raise ValueError(f"empty induced-parent window at order {n - 1}")
        windows[n - 1] = (lower, upper)
    return windows


def checked_run(command: list[str], *, stdout: Path | None = None,
                stderr: Path | None = None) -> float:
    start = time.monotonic()
    out_stream = stdout.open("wb") if stdout else None
    err_stream = stderr.open("wb") if stderr else None
    try:
        subprocess.run(command, check=True, stdout=out_stream, stderr=err_stream)
    finally:
        if out_stream:
            out_stream.close()
        if err_stream:
            err_stream.close()
    return time.monotonic() - start


def valid_completed(path: Path, manifest: Path) -> bool:
    if not path.is_file() or not manifest.is_file():
        return False
    try:
        info = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return (info.get("exit_status") == 0 and
            info.get("children_file_sha256") == sha256(path))


def software_args(udenum: Path, runner: Path, geng: Path | None = None) -> list[str]:
    args = ["--software", f"run-dag.py={runner}"]
    if geng is not None:
        args += ["--software", f"nauty-geng={geng}"]
    return args


def run_seed(args: argparse.Namespace, outdir: Path, n: int, m: int,
             summary: list[dict[str, object]]) -> None:
    output = outdir / f"{n}-{m}.g6"
    manifest = outdir / f"{n}-{m}.manifest.json"
    if args.resume and valid_completed(output, manifest):
        summary.append({"n": n, "m": m, "kind": "seed", "resumed": True,
                        "children": record_count(output)})
        return
    raw_dir = outdir / "_geng"
    raw_dir.mkdir(exist_ok=True)
    raw = raw_dir / f"{n}-{m}.g6"
    geng_command = ["nice", "-n", "10", str(args.geng), "-q", str(n), f"{m}:{m}"]
    if n == 0:
        raw.write_bytes(b"?\n")
        geng_wall = 0.0
    else:
        geng_wall = checked_run(geng_command, stdout=raw)
    command = [
        "nice", "-n", "10", str(args.udenum), "--filter",
        "--parents", str(raw), "--forbidden", str(args.forbidden),
        "--n", str(n), "--m", str(m), "--output", str(output),
        "--manifest", str(manifest), "--shard-id", f"seed-{n}-{m}",
        *software_args(args.udenum, Path(__file__).resolve(), args.geng),
    ]
    if args.resume:
        command.append("--overwrite")
    stats_path = outdir / f"{n}-{m}.stats.json"
    filter_wall = checked_run(command, stderr=stats_path)
    summary.append({"n": n, "m": m, "kind": "seed", "resumed": False,
                    "geng_wall_seconds": geng_wall,
                    "filter_wall_seconds": filter_wall,
                    "children": record_count(output), "stats": str(stats_path)})


def concatenate(paths: list[Path], output: Path) -> None:
    with output.open("wb") as destination:
        for path in paths:
            with path.open("rb") as source:
                shutil.copyfileobj(source, destination, 1024 * 1024)


def write_aggregate_manifest(args: argparse.Namespace, manifest: Path,
                             parent_file: Path, parent_count: int,
                             parts: list[Path], output: Path,
                             started: str, finished: str) -> None:
    software = {
        "udenum": sha256(args.udenum),
        "run-dag.py": sha256(Path(__file__).resolve()),
    }
    inputs = {str(parent_file): sha256(parent_file),
              str(args.forbidden): sha256(args.forbidden)}
    for part in parts:
        inputs[str(part)] = sha256(part)
        part_manifest = part.with_suffix(".manifest.json")
        inputs[str(part_manifest)] = sha256(part_manifest)
    value = {
        "shard_id": f"aggregate-{output.stem}",
        "parent_file": str(parent_file),
        "parent_range": [0, parent_count],
        "software_sha256": software,
        "inputs_sha256": inputs,
        "started": started,
        "finished": finished,
        "children_written": record_count(output),
        "children_file_sha256": sha256(output),
        "host": socket.gethostname(),
        "exit_status": 0,
    }
    manifest.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n")


def run_level_file(args: argparse.Namespace, outdir: Path,
                   windows: dict[int, tuple[int, int]], n: int, m: int,
                   summary: list[dict[str, object]]) -> None:
    output = outdir / f"{n}-{m}.g6"
    aggregate_manifest = outdir / f"{n}-{m}.manifest.json"
    if args.resume and valid_completed(output, aggregate_manifest):
        summary.append({"n": n, "m": m, "kind": "augmentation",
                        "resumed": True, "children": record_count(output)})
        return
    lower = math.ceil(m * (n - 2) / n)
    upper = min(UBAR[n - 1], m)
    previous_low, previous_high = windows[n - 1]
    lower = max(lower, previous_low)
    upper = min(upper, previous_high)
    source_files = [outdir / f"{n - 1}-{parent_m}.g6"
                    for parent_m in range(lower, upper + 1)]
    missing = [str(path) for path in source_files if not path.is_file()]
    if missing:
        raise RuntimeError("missing parent files: " + ", ".join(missing))
    parents_dir = outdir / "_parents"
    parents_dir.mkdir(exist_ok=True)
    parent_file = parents_dir / f"{n}-{m}.g6"
    concatenate(source_files, parent_file)
    count = record_count(parent_file)
    shard_dir = outdir / "shards" / f"{n}-{m}"
    shard_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    shard_stats: list[dict[str, object]] = []
    started = utc_now()
    pending: list[tuple[int, int, str, Path, Path, Path, list[str]]] = []
    for start in range(0, max(count, 1), args.shard_size):
        end = min(start + args.shard_size, count)
        if count == 0 and start > 0:
            break
        shard_id = f"{n}-{m}-{start}-{end}"
        part = shard_dir / f"{shard_id}.g6"
        manifest = shard_dir / f"{shard_id}.manifest.json"
        stats_path = shard_dir / f"{shard_id}.stats.json"
        if args.resume and valid_completed(part, manifest):
            parts.append(part)
            shard_stats.append({"range": [start, end], "resumed": True,
                                "children": record_count(part)})
            if count == 0:
                break
            continue
        command = [
            "nice", "-n", "10", str(args.udenum),
            "--parents", str(parent_file), "--forbidden", str(args.forbidden),
            "--n", str(n), "--m", str(m), "--start", str(start),
            "--end", str(end), "--output", str(part),
            "--manifest", str(manifest), "--shard-id", shard_id,
            *software_args(args.udenum, Path(__file__).resolve()),
        ]
        if args.verify_parents:
            command.append("--verify-parents")
        if args.resume:
            command.append("--overwrite")
        parts.append(part)
        pending.append((start, end, shard_id, part, manifest, stats_path, command))
        if count == 0:
            break
    def run_one(spec: tuple[int, int, str, Path, Path, Path, list[str]]) -> dict[str, object]:
        start, end, shard_id, part, manifest, stats_path, command = spec
        del shard_id, manifest
        wall = checked_run(command, stderr=stats_path)
        return {"range": [start, end], "resumed": False,
                "wall_seconds": wall, "children": record_count(part),
                "stats": str(stats_path)}

    if pending:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            shard_stats.extend(executor.map(run_one, pending))
    parts.sort(key=lambda path: int(path.stem.split("-")[-2]))
    shard_stats.sort(key=lambda value: int(value["range"][0]))
    concatenate(parts, output)
    finished = utc_now()
    write_aggregate_manifest(args, aggregate_manifest, parent_file, count,
                             parts, output, started, finished)
    summary.append({"n": n, "m": m, "kind": "augmentation",
                    "resumed": False, "parent_range": [lower, upper],
                    "parents": count, "children": record_count(output),
                    "shards": shard_stats})


def main() -> int:
    args = parse_args()
    args.udenum = args.udenum.resolve()
    args.forbidden = args.forbidden.resolve()
    args.geng = args.geng.resolve()
    outdir = args.output_dir.resolve()
    if args.shard_size < 1:
        raise ValueError("--shard-size must be positive")
    if outdir.exists() and not args.resume:
        raise RuntimeError("output directory exists, use --resume to continue it")
    outdir.mkdir(parents=True, exist_ok=True)
    immediate_parent_lower = math.ceil(args.target_m * (args.target_n - 2) / args.target_n)
    if (args.target_n - 1 in UBAR and
            immediate_parent_lower > UBAR[args.target_n - 1]):
        parents_dir = outdir / "_parents"
        parents_dir.mkdir(exist_ok=True)
        parent_file = parents_dir / f"{args.target_n}-{args.target_m}.g6"
        parent_file.write_bytes(b"")
        output = outdir / f"{args.target_n}-{args.target_m}.g6"
        output.write_bytes(b"")
        manifest = outdir / f"{args.target_n}-{args.target_m}.manifest.json"
        now = utc_now()
        write_aggregate_manifest(args, manifest, parent_file, 0, [], output, now, now)
        value = {
            "target": [args.target_n, args.target_m],
            "empty_by_schade": {
                "required_parent_edges": immediate_parent_lower,
                "parent_ubar": UBAR[args.target_n - 1],
            },
            "completed_through_n": args.target_n,
            "levels": [{"n": args.target_n, "m": args.target_m,
                        "parents": 0, "children": 0}],
        }
        (outdir / "run-summary.json").write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps(value["empty_by_schade"]))
        return 0
    windows = windows_for(args.target_n, args.target_m, args.seed_n)
    summary: list[dict[str, object]] = []
    for n in range(0, args.seed_n):
        run_seed(args, outdir, n, UBAR[n], summary)
    low, high = windows[args.seed_n]
    for m in range(low, high + 1):
        run_seed(args, outdir, args.seed_n, m, summary)
    for n in range(args.seed_n + 1, args.target_n + 1):
        low, high = windows[n]
        for m in range(low, high + 1):
            run_level_file(args, outdir, windows, n, m, summary)
        summary_path = outdir / "run-summary.json"
        summary_path.write_text(json.dumps({
            "target": [args.target_n, args.target_m],
            "seed_n": args.seed_n,
            "windows": {str(k): list(v) for k, v in sorted(windows.items())},
            "completed_through_n": n,
            "levels": summary,
        }, indent=2) + "\n")
    print(json.dumps({"target": [args.target_n, args.target_m],
                      "windows": windows, "files": len(summary)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"run-dag.py: {error}", file=sys.stderr)
        raise SystemExit(2)
