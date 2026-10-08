#!/usr/bin/env python3
"""Build the F-free canonical augmentation DAG with frozen parent shards, optionally pruned.

This is enum/run-dag.py plus two pruning stages (enum/PRUNING.md); run-dag.py itself is left
untouched because running shards hash the script on disk.

--reach            reach-table pruning (L4): only level files (n, m) that can still reach the
                   target are generated, only parents whose new-vertex degree d = M - m can
                   still reach it are used, and every level file is reduced to the graphs with
                   minimum degree >= k(n, m) before it is used as a parent (<n>-<m>.reach.g6).
--prune            hereditary pruning (L1 to L3): after each level file at n >= --prune-from is
                   complete, enum/prune.py certifies every graph (tu, refuted, embedded or
                   unknown) and the next level is built from <n>-<m>.keep.g6 only.

Every aggregate manifest records which file served as each parent source (full, reach or
keep), the reach entries used, and the hash of reach.json.

--forbidden-set 398 runs the whole DAG with the 398 minimal forbidden graphs (REPORT-398.md):
                   udenum gets --forbidden-set 398 at every level, the level-10 seed filter
                   included, and prune.py filters with udfilter -s 398. Recorded in
                   run-config.json, run-summary.json and every manifest this script writes.
--ubar N=M         lowers u-bar(N) for this run (Schade windows, reach table, default root
                   bound), only below the built-in value and never below a known lower bound on
                   u(N); needs --reach and --ubar-justification, both recorded in reach.json.
--verify-stages    after each level from the seeds to the target, udenum --verify-parents in the
                   run's forbidden set reads the level's stage file (<n>-<m>.verify.manifest.json):
                   every record must be canonical and contain none of the set, so a tree grown
                   from wrongly filtered seeds stops at its first level instead of silently
                   becoming a superset.
--rhombus          (needs --prune) every prune step also runs the rhombus rule (prune.py --rhombus,
                   enum/PRUNING.md L5, research/unit-distance-23/RHOMBUS-SPEC.md): udfilter's
                   survivors that filter/udrhombus refutes or finds a forced unit distance in are
                   pruned with linear certificates, replayed by check/udcheck_rhombus.py. Recorded
                   in run-config.json, run-summary.json, every aggregate and prune manifest; --resume
                   accepts only prune manifests made with the same setting.
--triangles        (needs --prune; not with --rhombus, which it implies) the same with filter/udtriangle, the
                   triangle-orientation case trees of RHOMBUS-SPEC.md Section 4 (witness "tri").
--prune-filter-set 74  (a set-398 run with --prune and --verify-stages) the prune step's udfilter
                   re-checks only the 74 (prune.py --filter-set 74): the level files are the same, and
                   the 324 are re-checked by the stage verification alone (PRUNING.md 5.6). Recorded
                   as prune_filter_set / filter_set in run-config.json, run-summary.json, the aggregate
                   and prune manifests; --resume accepts only prune manifests with the same filter set.
--resume           reuses a finished prune step only if its manifest names the run's target, a target with a
                   proved bound, the checkers prune.py would use now (by sha256; with a rule by path too,
                   never one chosen by $PRUNE_UDCHECK_RHOMBUS), and its files pass prune.py's structural
                   check again (verify_outputs: the keep and UNKNOWN files rebuilt from the certificate
                   verdicts) with the counts of its ACCEPT line, verified counts and native counts
                   (valid_prune); anything else reruns the step.
The defaults (set 74, the built-in u-bar, no stage verification, no rhombus rule) reproduce the
u(22) run: its commands, run-config.json, reach.json and manifests are unchanged.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
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
    24: 72,   # AMP, arXiv:2412.11914, Theorem 1(b)
}

# Best known LOWER bounds on u(n), each realised by a known unit-distance graph: u-bar(n) = u(n)
# for n <= 21 (AMP Theorem 1(a)), u(22) >= 60, u(23) >= 64 and u(24) >= 68 (AMP Theorem 1(b)). A --ubar
# override below one of these would contradict a known graph, so it is refused: for n <= 21 no
# override is possible at all.
UBAR_LOWER = {**{n: v for n, v in UBAR.items() if n <= 21}, 22: 60, 23: 64, 24: 68}

# The linear-certificate rules prune.py can run on udfilter's survivors (prune.py RULES), each with its prover binary
# in filter/: the rule's name is its flag (--rhombus, --triangles), passed on to prune.py and recorded in
# run-config.json, run-summary.json and every aggregate and prune manifest as "<rule>": true. At most one per run
# (udtriangle's verdicts contain udrhombus's, so --triangles implies the rhombus rule).
PRUNE_RULES = {"rhombus": "udrhombus", "triangles": "udtriangle"}
# the prefix of a rule's counts in prune manifests and the checker's ACCEPT line (prune.py RULES count_prefix)
RULE_COUNT_PREFIX = {"rhombus": "rhombus", "triangles": "tri"}

# Root minimum-degree bounds established by a lemma outside Schade's window (PRUNING.md L4).
ROOT_K_LEMMAS = {
    (22, 61): (5, "delta4/RESULT.md Lemma D4: every (22,61) unit-distance graph has minimum degree 5"),
}

# The forbidden lists udenum and udfilter accept. Set 398 is pinned by sha256 in both programs
# (REPORT-398.md); it is checked here too so that a wrong file fails before any work starts.
FORBIDDEN_FILES = {74: "forbidden-74.json", 398: "forbidden-398.json"}
FORBIDDEN_398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target-n", type=int, required=True)
    parser.add_argument("--target-m", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-n", type=int, default=10)
    parser.add_argument("--shard-size", type=int, default=10000)
    parser.add_argument("--jobs", type=int, choices=tuple(range(1, 17)), default=1)
    parser.add_argument("--slice-level", type=int, default=None,
                        help="partition this level's stage files by hash before they serve as parents "
                             "(descendants of disjoint slices are disjoint: each graph has one canonical parent)")
    parser.add_argument("--slice-index", type=int, default=None, help="which slice, 0 <= index < count")
    parser.add_argument("--slice-count", type=int, default=None, help="number of slices")
    parser.add_argument("--udenum", type=Path, default=here / "udenum")
    parser.add_argument("--forbidden-set", type=int, choices=(74, 398), default=74,
                        help="74: Globus and Parshall's list, as in the u(22) run (default); 398: the 74 "
                             "plus GP-10's 324 graphs on 10 vertices (data/forbidden-398.json, pinned by "
                             "sha256), passed to udenum at every level and to prune.py")
    parser.add_argument("--forbidden", type=Path, default=None,
                        help="forbidden JSON (default data/forbidden-74.json or data/forbidden-398.json, "
                             "by --forbidden-set)")
    parser.add_argument("--geng", type=Path, default=Path("/usr/bin/nauty-geng"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-parents", action="store_true")
    parser.add_argument("--reach", action="store_true", help="reach-table pruning (L4)")
    parser.add_argument("--reach-root-k", type=int, default=None,
                        help="minimum degree bound at the target; default: Schade's bound, or a lemma")
    parser.add_argument("--ubar", dest="ubar_items", action="append", default=[], metavar="N=M",
                        help="lower u-bar(N) to M for this run (Schade windows, reach table and default "
                             "root bound): only below the built-in value and not below the best known "
                             "lower bound on u(N); needs --reach and --ubar-justification; recorded in "
                             "reach.json and run-config.json")
    parser.add_argument("--ubar-justification", default=None,
                        help="the theorem that makes every --ubar value an upper bound on u(N)")
    parser.add_argument("--verify-stages", action="store_true",
                        help="after every level from the seeds to the target, run udenum --verify-parents "
                             "in the run's forbidden set over the level's stage file")
    parser.add_argument("--mutation-seeds-74", action="store_true",
                        help="TEST ONLY: filter the seeds with set 74 in a set-398 run (must be caught)")
    parser.add_argument("--prune", action="store_true", help="hereditary pruning (L1 to L3)")
    parser.add_argument("--prune-from", type=int, default=18,
                        help="prune level files with n >= this (default 18)")
    parser.add_argument("--prune-python", type=Path,
                        default=Path(os.path.expanduser("~/tools/pyenv-maths/bin/python")))
    parser.add_argument("--prune-tries", type=int, default=0,
                        help="udembed --tries; 0 disables the random search, which can run for minutes")
    parser.add_argument("--prune-max-states", type=int, default=400, help="udembed --max-states")
    parser.add_argument("--prune-chunk", type=int, default=25)
    parser.add_argument("--prune-filter-only", action="store_true",
                        help="hereditary TU pruning without the embedder (prune.py --filter-only)")
    parser.add_argument("--prune-graph-timeout", type=float, default=120.0)
    parser.add_argument("--rhombus", action="store_true",
                        help="with --prune: the rhombus rule in every prune step (prune.py --rhombus)")
    parser.add_argument("--triangles", action="store_true",
                        help="with --prune: the triangle-orientation rule in every prune step (prune.py --triangles, "
                             "udtriangle in place of udrhombus; it implies the rhombus rule)")
    parser.add_argument("--prune-filter-set", type=int, choices=(74, 398), default=None,
                        help="with --prune: the forbidden set of the prune step's udfilter re-check (prune.py "
                             "--filter-set; default the run's set). 74 in a set-398 run needs --verify-stages, "
                             "which re-checks every stage record against all 398 (PRUNING.md 5.6)")
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


def graph6_min_degree(code: str) -> int:
    n = ord(code[0]) - 63
    if n <= 0:
        return 0
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    degree = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                degree[i] += 1
                degree[j] += 1
            k += 1
    return min(degree)


def windows_for(target_n: int, target_m: int, seed_n: int,
                ubar: dict[int, int] = UBAR) -> dict[int, tuple[int, int]]:
    if target_n not in ubar or seed_n < 1 or seed_n >= target_n:
        raise ValueError("target and seed orders must lie in the known u-bar table")
    windows = {target_n: (target_m, target_m)}
    for n in range(target_n, seed_n, -1):
        child_low, child_high = windows[n]
        lower = math.ceil(child_low * (n - 2) / n)
        upper = min(ubar[n - 1], child_high)
        if lower > upper:
            raise ValueError(f"empty induced-parent window at order {n - 1}")
        windows[n - 1] = (lower, upper)
    return windows


def reach_table(target_n: int, target_m: int, root_k: int, seed_n: int,
                ubar: dict[int, int] = UBAR) -> dict[int, dict[int, int]]:
    """R(n) = {m: k}: graphs at level n with m edges can still reach the target only if their
    minimum degree is at least k (PRUNING.md L4).  Built backward from the target."""
    table: dict[int, dict[int, int]] = {target_n: {target_m: root_k}}
    for n in range(target_n - 1, seed_n - 1, -1):
        level: dict[int, int] = {}
        for child_m, k in table[n + 1].items():
            for d in range(k, min(n, (2 * child_m) // (n + 1)) + 1):
                m = child_m - d
                if m < 0 or m > ubar[n]:
                    continue
                level[m] = min(level.get(m, d), max(0, d - 1))
        if not level:
            raise ValueError(f"reach table is empty at order {n}")
        table[n] = level
    return table


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


def valid_completed(path: Path, manifest: Path, forbidden_sha256: str | None = None) -> bool:
    """--resume accepts a finished file. With forbidden_sha256 (set 398 runs) its manifest must
    also hash that forbidden file among its inputs, so a file made with another list (a set-74
    prefix hard-linked into a set-398 directory, say) is regenerated, never reused."""
    if not path.is_file() or not manifest.is_file():
        return False
    try:
        info = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if forbidden_sha256 is not None:
        inputs = info.get("inputs_sha256")
        if not isinstance(inputs, dict) or forbidden_sha256 not in inputs.values():
            return False
    return (info.get("exit_status") == 0 and
            info.get("children_file_sha256") == sha256(path))


def resume_forbidden(args: argparse.Namespace) -> str | None:
    """The forbidden-file hash a resumed manifest must name: none for set 74 (the u(22) rule,
    unchanged), the pinned file for set 398."""
    return FORBIDDEN_398_SHA256 if args.forbidden_set == 398 else None


def forbidden_set_args(forbidden_set: int) -> list[str]:
    """udenum's set option: none for set 74 (the u(22) commands, unchanged), else --forbidden-set."""
    return [] if forbidden_set == 74 else ["--forbidden-set", str(forbidden_set)]


def software_args(args: argparse.Namespace, runner: Path, geng: Path | None = None) -> list[str]:
    result = ["--software", f"run-dag2.py={runner}"]
    if geng is not None:
        result += ["--software", f"nauty-geng={geng}"]
    if args.reach:
        result += ["--software", f"reach.json={args.reach_json}"]
    return result


def run_seed(args: argparse.Namespace, outdir: Path, n: int, m: int,
             summary: list[dict[str, object]]) -> dict[str, object]:
    output = outdir / f"{n}-{m}.g6"
    manifest = outdir / f"{n}-{m}.manifest.json"
    if args.resume and valid_completed(output, manifest, resume_forbidden(args)):
        entry: dict[str, object] = {"n": n, "m": m, "kind": "seed", "resumed": True,
                                    "children": record_count(output)}
        summary.append(entry)
        return entry
    raw_dir = outdir / "_geng"
    raw_dir.mkdir(exist_ok=True)
    raw = raw_dir / f"{n}-{m}.g6"
    geng_command = ["nice", "-n", "10", str(args.geng), "-q", str(n), f"{m}:{m}"]
    if n == 0:
        raw.write_bytes(b"?\n")
        geng_wall = 0.0
    else:
        geng_wall = checked_run(geng_command, stdout=raw)
    # the seed filter uses the run's forbidden set (the test-only mutation swaps in set 74)
    seed_set, seed_forbidden = args.forbidden_set, args.forbidden
    if args.mutation_seeds_74:
        seed_set, seed_forbidden = 74, args.forbidden.parent / FORBIDDEN_FILES[74]
    command = [
        "nice", "-n", "10", str(args.udenum), "--filter",
        "--parents", str(raw), "--forbidden", str(seed_forbidden),
        *forbidden_set_args(seed_set),
        "--n", str(n), "--m", str(m), "--output", str(output),
        "--manifest", str(manifest), "--shard-id", f"seed-{n}-{m}",
        *software_args(args, Path(__file__).resolve(), args.geng),
    ]
    if args.resume:
        command.append("--overwrite")
    stats_path = outdir / f"{n}-{m}.stats.json"
    filter_wall = checked_run(command, stderr=stats_path)
    entry = {"n": n, "m": m, "kind": "seed", "resumed": False,
             "geng_wall_seconds": geng_wall,
             "filter_wall_seconds": filter_wall,
             "children": record_count(output), "stats": str(stats_path)}
    summary.append(entry)
    return entry


def concatenate(paths: list[Path], output: Path) -> None:
    with output.open("wb") as destination:
        for path in paths:
            with path.open("rb") as source:
                shutil.copyfileobj(source, destination, 1024 * 1024)


def write_aggregate_manifest(args: argparse.Namespace, manifest: Path,
                             parent_file: Path, parent_count: int,
                             parts: list[Path], output: Path,
                             started: str, finished: str,
                             extra: dict[str, object] | None = None) -> None:
    software = {
        "udenum": sha256(args.udenum),
        "run-dag2.py": sha256(Path(__file__).resolve()),
    }
    inputs = {str(parent_file): sha256(parent_file),
              str(args.forbidden): sha256(args.forbidden)}
    if args.reach:
        inputs[str(args.reach_json)] = sha256(args.reach_json)
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
    if args.forbidden_set != 74:
        value["forbidden_set"] = args.forbidden_set
    if extra:
        value.update(extra)
    manifest.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n")


def slice_of(code: str, count: int) -> int:
    """Deterministic, machine-independent slice number of a graph6 record."""
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big") % count


def slice_file(args: argparse.Namespace, outdir: Path, n: int, m: int,
               source: Path, kind: str) -> tuple[Path, str]:
    """Restrict a stage file to the records of slice --slice-index of --slice-count."""
    i, count = args.slice_index, args.slice_count
    out = outdir / f"{n}-{m}.slice-{i}-of-{count}.g6"
    manifest = outdir / f"{n}-{m}.slice-{i}-of-{count}.manifest.json"
    source_hash = sha256(source)
    if out.is_file() and manifest.is_file():
        try:
            info = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            info = {}
        if (info.get("input_sha256") == source_hash and info.get("output_sha256") == sha256(out)
                and info.get("slice") == [i, count]):
            return out, f"{kind}+slice"
    started = utc_now()
    codes = [line.strip() for line in source.read_text(encoding="ascii").splitlines()
             if line.strip() and not line.startswith(">>")]
    kept = [code for code in codes if slice_of(code, count) == i]
    out.write_text("".join(code + "\n" for code in kept), encoding="ascii")
    manifest.write_text(json.dumps({
        "kind": "slice", "level": [n, m], "slice": [i, count], "stage_kind": kind,
        "rule": "sha256(graph6 record) first 8 bytes big-endian mod count == index",
        "software_sha256": {"run-dag2.py": sha256(Path(__file__).resolve())},
        "input_file": str(source), "input_sha256": source_hash, "input_records": len(codes),
        "output_file": str(out), "output_sha256": sha256(out), "output_records": len(kept),
        "started": started, "finished": utc_now(), "host": socket.gethostname(), "exit_status": 0,
        **({"forbidden_set": args.forbidden_set} if args.forbidden_set != 74 else {}),
    }, indent=2) + "\n")
    return out, f"{kind}+slice"


def stage_file(args: argparse.Namespace, outdir: Path, n: int, m: int) -> tuple[Path, str]:
    """The file that represents level (n, m) when it serves as a parent: the last stage applied."""
    path, kind = stage_file_unsliced(args, outdir, n, m)
    if args.slice_level is not None and n == args.slice_level and path.is_file():
        return slice_file(args, outdir, n, m, path, kind)
    return path, kind


def stage_file_unsliced(args: argparse.Namespace, outdir: Path, n: int, m: int) -> tuple[Path, str]:
    if args.prune and n >= args.prune_from:
        return outdir / f"{n}-{m}.keep.g6", "keep"
    if args.reach:
        return outdir / f"{n}-{m}.reach.g6", "reach"
    return outdir / f"{n}-{m}.g6", "full"


def parent_edge_counts(args: argparse.Namespace, windows: dict[int, tuple[int, int]],
                       table: dict[int, dict[int, int]] | None, n: int, m: int) -> tuple[list[int], int]:
    """Parent edge counts m' for level (n, m), and the reach bound k applied (0 without reach)."""
    lower = math.ceil(m * (n - 2) / n)
    upper = min(args.ubar[n - 1], m)
    previous_low, previous_high = windows[n - 1]
    lower = max(lower, previous_low)
    upper = min(upper, previous_high)
    if table is None:
        return list(range(lower, upper + 1)), 0
    k = table[n][m]
    chosen = [parent_m for parent_m in range(lower, upper + 1) if m - parent_m >= k]
    for parent_m in chosen:
        if parent_m not in table[n - 1]:
            raise RuntimeError(f"reach table inconsistency: ({n - 1},{parent_m}) is a parent of "
                               f"({n},{m}) but not a reach level")
    return chosen, k


def run_level_file(args: argparse.Namespace, outdir: Path,
                   windows: dict[int, tuple[int, int]],
                   table: dict[int, dict[int, int]] | None, n: int, m: int,
                   summary: list[dict[str, object]]) -> dict[str, object]:
    output = outdir / f"{n}-{m}.g6"
    aggregate_manifest = outdir / f"{n}-{m}.manifest.json"
    if args.resume and valid_completed(output, aggregate_manifest, resume_forbidden(args)):
        entry: dict[str, object] = {"n": n, "m": m, "kind": "augmentation",
                                    "resumed": True, "children": record_count(output)}
        summary.append(entry)
        return entry
    parent_ms, k = parent_edge_counts(args, windows, table, n, m)
    sources = [(parent_m, *stage_file(args, outdir, n - 1, parent_m)) for parent_m in parent_ms]
    missing = [str(path) for _, path, _ in sources if not path.is_file()]
    if missing:
        raise RuntimeError("missing parent files: " + ", ".join(missing))
    parents_dir = outdir / "_parents"
    parents_dir.mkdir(exist_ok=True)
    parent_file = parents_dir / f"{n}-{m}.g6"
    concatenate([path for _, path, _ in sources], parent_file)
    count = record_count(parent_file)
    parent_sources = [{"level": [n - 1, parent_m], "d": m - parent_m, "kind": kind,
                       "file": str(path), "sha256": sha256(path), "records": record_count(path)}
                      for parent_m, path, kind in sources]
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
        if args.resume and valid_completed(part, manifest, resume_forbidden(args)):
            parts.append(part)
            shard_stats.append({"range": [start, end], "resumed": True,
                                "children": record_count(part)})
            if count == 0:
                break
            continue
        command = [
            "nice", "-n", "10", str(args.udenum),
            "--parents", str(parent_file), "--forbidden", str(args.forbidden),
            *forbidden_set_args(args.forbidden_set),
            "--n", str(n), "--m", str(m), "--start", str(start),
            "--end", str(end), "--output", str(part),
            "--manifest", str(manifest), "--shard-id", shard_id,
            *software_args(args, Path(__file__).resolve()),
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
    extra: dict[str, object] = {
        "parent_sources": parent_sources,
        "reach": ({"enabled": True, "k": k, "reach_json_sha256": sha256(args.reach_json),
                   "table_level": table[n], "table_parent_level": table[n - 1]}
                  if table is not None else {"enabled": False}),
        "pruning": {"enabled": bool(args.prune), "prune_from": args.prune_from if args.prune else None, "prune_filter_only": bool(args.prune and args.prune_filter_only),
                    **({args.rule: True} if args.rule else {}),
                    **({"filter_set": args.prune_filter_set} if args.prune_filter_set is not None else {})},
    }
    write_aggregate_manifest(args, aggregate_manifest, parent_file, count,
                             parts, output, started, finished, extra)
    entry = {"n": n, "m": m, "kind": "augmentation",
             "resumed": False, "parent_edge_counts": parent_ms, "reach_k": k,
             "parent_sources": [{"level": s["level"], "kind": s["kind"], "records": s["records"]}
                                for s in parent_sources],
             "parents": count, "children": record_count(output),
             "shards": shard_stats}
    summary.append(entry)
    return entry


def valid_reach(out: Path, manifest: Path, full: Path, k: int) -> bool:
    if not out.is_file() or not manifest.is_file():
        return False
    try:
        info = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return (info.get("exit_status") == 0 and info.get("k") == k and
            info.get("input_sha256") == sha256(full) and
            info.get("output_sha256") == sha256(out))


def reach_filter(args: argparse.Namespace, outdir: Path, table: dict[int, dict[int, int]],
                 n: int, m: int, entry: dict[str, object]) -> None:
    """Drop the graphs whose minimum degree is below k(n, m) (L4) before the level is a parent."""
    full = outdir / f"{n}-{m}.g6"
    out = outdir / f"{n}-{m}.reach.g6"
    manifest = outdir / f"{n}-{m}.reach.manifest.json"
    k = table[n][m]
    if args.resume and valid_reach(out, manifest, full, k):
        entry["reach"] = {"k": k, "resumed": True, "kept": record_count(out)}
        return
    started = utc_now()
    # Streamed (NEW4, 2026-09-05): the list-of-strings version held every record of the cell
    # in RAM and was OOM-killed on the unpruned (21,57) run's 72.4-million-record cell (15,31)
    # on a 15 GB worker. Reading and writing line by line gives the same bytes in the same
    # order (checked on a real cell against the old code: identical output sha256 and counts).
    n_in = 0
    n_kept = 0
    with full.open("r", encoding="ascii") as src, out.open("w", encoding="ascii") as dst:
        for line in src:
            code = line.strip()
            if not code or code.startswith(">>"):
                continue
            n_in += 1
            if graph6_min_degree(code) >= k:
                dst.write(code + "\n")
                n_kept += 1
    codes = range(n_in)
    kept = range(n_kept)
    manifest.write_text(json.dumps({
        "kind": "reach",
        "level": [n, m],
        "k": k,
        "reach_json_sha256": sha256(args.reach_json),
        "software_sha256": {"run-dag2.py": sha256(Path(__file__).resolve())},
        "input_file": str(full),
        "input_sha256": sha256(full),
        "input_records": len(codes),
        "output_file": str(out),
        "output_sha256": sha256(out),
        "output_records": len(kept),
        "dropped": len(codes) - len(kept),
        "started": started,
        "finished": utc_now(),
        "host": socket.gethostname(),
        "exit_status": 0,
        **({"forbidden_set": args.forbidden_set} if args.forbidden_set != 74 else {}),
    }, indent=2) + "\n")
    entry["reach"] = {"k": k, "resumed": False, "input": len(codes), "kept": len(kept),
                      "dropped": len(codes) - len(kept)}


def prune_checkers(args: argparse.Namespace) -> dict[str, Path]:
    """The checker files prune.py replays this run's certificates with, by the key its manifest hashes them
    under (software_sha256): run-dag2.py passes prune.py no checker option, so they are prune.py's defaults,
    check/udcheck.py always (udcheck398.py and udcheck_rhombus.py hand their kernel records to it),
    check/udcheck398.py for set 398, and check/udcheck_rhombus.py with a linear rule ($PRUNE_UDCHECK_RHOMBUS
    names another copy, a test aid a production run never sets)."""
    ud = Path(__file__).resolve().parent.parent
    checkers = {"udcheck.py": ud / "check" / "udcheck.py"}
    if args.forbidden_set != 74:
        checkers["udcheck398.py"] = ud / "check" / "udcheck398.py"
    if args.rule:
        checkers["udcheck_rhombus.py"] = Path(os.environ.get("PRUNE_UDCHECK_RHOMBUS") or
                                              ud / "check" / "udcheck_rhombus.py")
    return checkers


_PRUNE_MODULE = None


def prune_module():
    """enum/prune.py itself, imported once: resume re-runs ITS structural check of a prune step's files
    (verify_outputs) and reads ITS table of proved bounds (UPPER), so the two scripts cannot drift apart."""
    global _PRUNE_MODULE
    if _PRUNE_MODULE is None:
        spec = importlib.util.spec_from_file_location("prune_for_resume", Path(__file__).resolve().parent / "prune.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _PRUNE_MODULE = module
    return _PRUNE_MODULE


def count_value(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def valid_prune(args: argparse.Namespace, manifest: Path, source: Path, outdir: Path, n: int, m: int) -> bool:
    """--resume accepts a finished prune step only if nothing in it needs the step run again. A set-398
    run also needs the manifest's own forbidden_set to be 398 (prune.py writes it); set 74 keeps the
    u(22) rule unchanged. The manifest's linear rule must be the run's (prune.py writes "<rule>": true
    only with it), so a step made with a rule is never reused without it, or with another, or the other
    way round; and its filter_set (written only when it is not the run's set) must be the run's
    --prune-filter-set. Its target must be the run's, and a target with a proved bound (prune.py's UPPER:
    a tu record prunes only there, and the checker never sees the target). Its checkers must be the ones
    prune.py would use now, by sha256, and with a rule by path, never one chosen by $PRUNE_UDCHECK_RHOMBUS
    (from_environment). The files must pass prune.py's own structural check again (verify_outputs: the
    certificate records are the stage input in order, the keep file is exactly its embedded and unknown
    records in order, the UNKNOWN file exactly its unknown records, every pruned record has a witness, no
    other rule's witness), with the hashes the manifest records; and the counts the files give must be
    the ACCEPT line's, the verified counts, and the native counts (input, tu, survivors, the rule's tu,
    refuted and survivors, embedded, refuted, unknown, kept, pruned), all nonnegative integers. Anything
    else reruns the step."""
    if not manifest.is_file():
        return False
    try:
        info = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(info, dict):
        return False
    forbidden_set, rule, filter_set = args.forbidden_set, args.rule, args.prune_filter_set
    pr = prune_module()
    if args.target_n not in pr.UPPER or args.target_m < pr.UPPER[args.target_n]:
        return False
    if info.get("exit_status") != 0 or any((info.get("mutation") or {}).values()):
        return False
    if forbidden_set != 74 and info.get("forbidden_set") != forbidden_set:
        return False
    if any((info.get(name) is True) != (name == rule) for name in PRUNE_RULES):
        return False
    if info.get("filter_set") != filter_set:
        return False
    if info.get("target") != [args.target_n, args.target_m] or info.get("level") != [n, m]:
        return False
    software = info.get("software_sha256") or {}
    for key, path in prune_checkers(args).items():
        if not path.is_file() or software.get(key) != sha256(path):
            return False
    if rule:
        recorded = info.get(f"{rule}_checker") or {}
        if (recorded.get("from_environment") is not False or os.environ.get("PRUNE_UDCHECK_RHOMBUS") or
                recorded.get("path") != str(prune_checkers(args)["udcheck_rhombus.py"])):
            return False
    def by_name(table: dict, path: Path) -> str | None:
        # manifests key files by absolute path; a level copied (hard-linked) into another run
        # directory keeps the file names, so fall back to matching on the base name
        if str(path) in table:
            return table[str(path)]
        matches = [v for k, v in table.items() if Path(k).name == path.name]
        return matches[0] if len(matches) == 1 else None
    certs, keep, unknown = (outdir / f"{n}-{m}.certs.jsonl", outdir / f"{n}-{m}.keep.g6",
                            outdir / f"{n}-{m}.UNKNOWN.g6")
    if not source.is_file() or by_name(info.get("inputs_sha256", {}), source) != sha256(source):
        return False
    for path in (certs, keep, unknown):
        if not path.is_file() or by_name(info.get("outputs_sha256", {}), path) != sha256(path):
            return False
    # the files themselves: prune.py's structural check, which rebuilds the keep and UNKNOWN files from the
    # certificate verdicts (an accepted certificate file does not certify a keep file edited after it)
    try:
        files = pr.verify_outputs(source, certs, keep, unknown, rule=rule)
    except (pr.PruneError, OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
    accept = info.get("checker")
    counts = info.get("counts")
    verified = info.get("verified_counts")
    if not isinstance(accept, str) or not accept.startswith("ACCEPT certificates ") or \
            not isinstance(counts, dict) or not isinstance(verified, dict):
        return False
    said = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", accept)}
    if verified != files:
        return False
    keys = ["records", "tu", "refuted", "embedded", "unknown"]
    prefix = RULE_COUNT_PREFIX[rule] if rule else None
    if rule:
        keys += [f"{prefix}_tu", f"{prefix}_refuted"]
    if any(said.get(key) != files[key] for key in keys) or said.get("forbidden", 0) != 0:
        return False
    native = ["input", "tu", "survivors", "embedded", "refuted", "unknown", "kept", "pruned"]
    if rule:
        native += [f"{prefix}_tu", f"{prefix}_refuted", f"{prefix}_survivors"]
    if any(not count_value(counts.get(key)) for key in native):
        return False
    rule_tu = counts[f"{prefix}_tu"] if rule else 0
    rule_refuted = counts[f"{prefix}_refuted"] if rule else 0
    to_embed = counts[f"{prefix}_survivors"] if rule else counts["survivors"]
    # each count on its own, not only the totals: the rule's tu and refuted are the records carrying its witness
    # (G5 round 3: counts.tu 11 -> 12 with tri_tu 1 -> 0 kept every total)
    if rule and (rule_tu != files[f"{prefix}_tu"] or rule_refuted != files[f"{prefix}_refuted"]):
        return False
    return (counts["input"] == files["records"] and counts["kept"] == files["kept"] and
            counts["pruned"] == files["records"] - files["kept"] and
            counts["embedded"] == files["embedded"] and counts["unknown"] == files["unknown"] and
            counts["tu"] + rule_tu == files["tu"] and counts["refuted"] + rule_refuted == files["refuted"] and
            counts["survivors"] == counts["input"] - counts["tu"] and
            (not rule or to_embed == counts["survivors"] - rule_tu - rule_refuted) and
            counts["embedded"] + counts["refuted"] + counts["unknown"] == to_embed)


def prune_level(args: argparse.Namespace, outdir: Path, n: int, m: int,
                entry: dict[str, object]) -> None:
    source = outdir / (f"{n}-{m}.reach.g6" if args.reach else f"{n}-{m}.g6")
    manifest = outdir / f"{n}-{m}.prune.manifest.json"
    if args.resume and valid_prune(args, manifest, source, outdir, n, m):
        info = json.loads(manifest.read_text())
        entry["prune"] = {"resumed": True, "source": str(source), "counts": info["counts"]}
        return
    here = Path(__file__).resolve().parent
    command = [
        sys.executable, str(here / "prune.py"), "--level", str(source),
        "--target-n", str(args.target_n), "--target-m", str(args.target_m),
        "--jobs", str(args.jobs), "--tries", str(args.prune_tries),
        "--max-states", str(args.prune_max_states), "--chunk", str(args.prune_chunk),
        "--graph-timeout", str(args.prune_graph_timeout), "--python", str(args.prune_python),
        "--overwrite", *forbidden_set_args(args.forbidden_set),
    ]
    if args.prune_filter_only:
        command += ["--filter-only"]
    if args.rule:
        command += [f"--{args.rule}"]
    if args.prune_filter_set is not None:
        command += ["--filter-set", str(args.prune_filter_set)]
    if args.reach:
        command += ["--record", f"reach.json={args.reach_json}"]
    log = outdir / "_prune" / f"{n}-{m}.log"
    log.parent.mkdir(exist_ok=True)
    wall = checked_run(command, stdout=log)
    info = json.loads(manifest.read_text())
    if info.get("exit_status") != 0:
        raise RuntimeError(f"prune.py reported problems for ({n},{m}): {info.get('problems')}")
    if args.forbidden_set != 74 and info.get("forbidden_set") != args.forbidden_set:
        raise RuntimeError(f"prune.py manifest for ({n},{m}) does not record forbidden set "
                           f"{args.forbidden_set}")
    if any((info.get(name) is True) != (name == args.rule) for name in PRUNE_RULES):
        raise RuntimeError(f"prune.py manifest for ({n},{m}) does not record the run's linear rule "
                           f"{args.rule}")
    if info.get("filter_set") != args.prune_filter_set:
        raise RuntimeError(f"prune.py manifest for ({n},{m}) does not record the run's filter set "
                           f"{args.prune_filter_set}")
    entry["prune"] = {"resumed": False, "source": str(source), "counts": info["counts"],
                      "wall_seconds": info["wall_seconds"], "checker": info["checker"],
                      "step_wall_seconds": wall}


def valid_verify(manifest: Path, stage_sha256: str, forbidden_set: int, forbidden_sha256: str) -> bool:
    if not manifest.is_file():
        return False
    try:
        info = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return (info.get("exit_status") == 0 and info.get("stage_sha256") == stage_sha256 and
            info.get("forbidden_set") == forbidden_set and
            info.get("forbidden_sha256") == forbidden_sha256)


def verify_stage(args: argparse.Namespace, outdir: Path, n: int, m: int,
                 entry: dict[str, object]) -> None:
    """udenum --verify-parents over the stage file of level (n, m): every record must be a
    canonical graph6 string containing none of the run's forbidden graphs, else udenum exits 2
    and the run stops here. udenum checks each parent before anything else and is given the
    target (n + 1, m + n), so the new vertex would need degree n: every record with minimum
    degree below n - 1 is then skipped by udenum's degree rule and no child is generated (a
    complete graph on n >= 4 vertices contains K4 and has already failed the check). The
    unsliced stage file is read, so on a sliced level every slice is covered. The file is
    split into --jobs contiguous record ranges (udenum --start/--end), run in parallel; the
    ranges must tile the file and every record must have been read."""
    path, kind = stage_file_unsliced(args, outdir, n, m)
    manifest = outdir / f"{n}-{m}.verify.manifest.json"
    if not path.is_file():
        raise RuntimeError(f"stage file to verify is missing: {path}")
    stage_hash = sha256(path)
    forbidden_hash = sha256(args.forbidden)
    if args.resume and valid_verify(manifest, stage_hash, args.forbidden_set, forbidden_hash):
        info = json.loads(manifest.read_text())
        entry["verify"] = {"resumed": True, "stage_kind": kind, "records": info.get("records")}
        return
    records = record_count(path)
    vdir = outdir / "_verify"
    vdir.mkdir(exist_ok=True)
    count = max(1, min(args.jobs, records))
    bounds = [records * i // count for i in range(count + 1)]
    ranges = [(bounds[i], bounds[i + 1]) for i in range(count)]

    def run_range(spec: tuple[int, int]) -> dict[str, object]:
        lo, hi = spec
        stem = f"{n}-{m}.{lo}-{hi}"
        children, shard_manifest, stats_path = (vdir / f"{stem}.g6", vdir / f"{stem}.manifest.json",
                                                vdir / f"{stem}.stats.json")
        command = [
            "nice", "-n", "10", str(args.udenum), "--verify-parents",
            "--forbidden-set", str(args.forbidden_set), "--forbidden", str(args.forbidden),
            "--parents", str(path), "--n", str(n + 1), "--m", str(m + n),
            "--start", str(lo), "--end", str(hi),
            "--output", str(children), "--manifest", str(shard_manifest),
            "--shard-id", f"verify-{stem}", "--overwrite",
            *software_args(args, Path(__file__).resolve()),
        ]
        with stats_path.open("wb") as err:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=err)
        message = stats_path.read_text(encoding="utf-8", errors="replace").strip()
        return {"range": [lo, hi], "exit": result.returncode, "message": message,
                "children": children, "manifest": shard_manifest}

    started = utc_now()
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        results = list(executor.map(run_range, ranges))
    wall = time.monotonic() - start
    parts = []
    for r in results:
        lo, hi = r["range"]
        if r["exit"] != 0:
            raise RuntimeError(f"STAGE VERIFICATION FAILED at ({n},{m}): udenum --verify-parents "
                               f"--forbidden-set {args.forbidden_set} rejected {path.name} records "
                               f"[{lo},{hi}) (exit {r['exit']}): {str(r['message'])[-300:]}")
        try:
            stats = json.loads(str(r["message"]).splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as error:
            raise RuntimeError(f"stage verification of ({n},{m}) [{lo},{hi}) wrote no statistics: {error}")
        if (stats.get("parents_seen") != hi - lo or stats.get("parents_processed") != 0 or
                stats.get("children_written") != 0 or record_count(r["children"]) != 0):
            raise RuntimeError(f"stage verification of ({n},{m}) did not read exactly the records "
                               f"[{lo},{hi}) without generating: {stats}")
        parts.append({"range": [lo, hi], "udenum_manifest": str(r["manifest"]),
                      "udenum_manifest_sha256": sha256(r["manifest"]), "udenum_stats": stats})
    if [p["range"] for p in parts] != [[bounds[i], bounds[i + 1]] for i in range(count)] or \
            sum(p["udenum_stats"]["parents_seen"] for p in parts) != records:
        raise RuntimeError(f"stage verification of ({n},{m}): the ranges do not cover the {records} records")
    if sha256(path) != stage_hash:
        raise RuntimeError(f"stage file {path} changed during its verification")
    manifest.write_text(json.dumps({
        "kind": "verify",
        "level": [n, m],
        "check": "udenum --verify-parents: every record canonical and free of the forbidden set",
        "forbidden_set": args.forbidden_set,
        "forbidden_file": str(args.forbidden),
        "forbidden_sha256": forbidden_hash,
        "stage_kind": kind,
        "stage_file": str(path),
        "stage_sha256": stage_hash,
        "records": records,
        "parents_seen": sum(p["udenum_stats"]["parents_seen"] for p in parts),
        "udenum_target": [n + 1, m + n],
        "parts": parts,
        "software_sha256": {"udenum": sha256(args.udenum),
                            "run-dag2.py": sha256(Path(__file__).resolve())},
        "started": started,
        "finished": utc_now(),
        "wall_seconds": wall,
        "host": socket.gethostname(),
        "exit_status": 0,
    }, indent=2) + "\n")
    entry["verify"] = {"resumed": False, "stage_kind": kind, "records": records,
                       "wall_seconds": wall, "parts": len(parts)}


def after_level(args: argparse.Namespace, outdir: Path, table: dict[int, dict[int, int]] | None,
                n: int, m: int, entry: dict[str, object]) -> None:
    if table is not None:
        reach_filter(args, outdir, table, n, m, entry)
    if args.prune and n >= args.prune_from:
        prune_level(args, outdir, n, m, entry)
    if args.verify_stages:
        verify_stage(args, outdir, n, m, entry)


def write_summary(outdir: Path, args: argparse.Namespace, windows: dict[int, tuple[int, int]],
                  table: dict[int, dict[int, int]] | None, n: int,
                  summary: list[dict[str, object]]) -> None:
    (outdir / "run-summary.json").write_text(json.dumps({
        "target": [args.target_n, args.target_m],
        "seed_n": args.seed_n,
        "windows": {str(k): list(v) for k, v in sorted(windows.items())},
        "reach": ({"enabled": True, "root_k": args.reach_root_k,
                   "levels": {str(k): sorted(v) for k, v in sorted(table.items())}}
                  if table is not None else {"enabled": False}),
        "prune": {"enabled": bool(args.prune), "prune_from": args.prune_from if args.prune else None, "prune_filter_only": bool(args.prune and args.prune_filter_only)},
        "slice": ([args.slice_level, args.slice_index, args.slice_count] if args.slice_level is not None else None),
        **non_default_options(args),
        "completed_through_n": n,
        "levels": summary,
    }, indent=2) + "\n")


def non_default_options(args: argparse.Namespace) -> dict[str, object]:
    """The options the u(22) run did not have, only when they differ from its defaults, so that
    a default run writes exactly the u(22) run-config.json and run-summary.json."""
    extra: dict[str, object] = {}
    if args.forbidden_set != 74:
        extra["forbidden_set"] = args.forbidden_set
    if args.ubar_override:
        extra["ubar_override"] = args.ubar_override
        extra["ubar_justification"] = args.ubar_justification
    if args.verify_stages:
        extra["verify_stages"] = True
    if args.rule:
        extra[args.rule] = True
    if args.prune_filter_set is not None:
        extra["prune_filter_set"] = args.prune_filter_set
    if args.mutation_seeds_74:
        extra["mutation"] = {"seeds_74": True}
    return extra


def run_config(args: argparse.Namespace) -> dict[str, object]:
    return {"target": [args.target_n, args.target_m], "seed_n": args.seed_n,
            "reach": bool(args.reach), "reach_root_k": args.reach_root_k,
            "prune": bool(args.prune), "prune_from": args.prune_from if args.prune else None, "prune_filter_only": bool(args.prune and args.prune_filter_only),
            "prune_tries": args.prune_tries if args.prune else None,
            "prune_max_states": args.prune_max_states if args.prune else None,
            "slice": ([args.slice_level, args.slice_index, args.slice_count]
                      if args.slice_level is not None else None),
            **non_default_options(args)}


def effective_ubar(args: argparse.Namespace) -> tuple[dict[int, int], dict[str, dict[str, int]]]:
    """This run's u-bar table: the built-in UBAR with every --ubar N=M applied, and the overrides
    as recorded in reach.json. An override may only lower u-bar(N), never below UBAR_LOWER[N]
    (a known unit-distance graph has that many edges), and needs --reach and a justification."""
    ubar = dict(UBAR)
    overrides: dict[str, dict[str, int]] = {}
    for item in args.ubar_items:
        n_text, _, m_text = item.partition("=")
        try:
            n, m = int(n_text), int(m_text)
        except ValueError:
            raise ValueError(f"--ubar {item!r}: expected N=M with integers N and M") from None
        if n not in UBAR:
            raise ValueError(f"--ubar {item}: there is no built-in u-bar({n})")
        if str(n) in overrides:
            raise ValueError(f"--ubar gives u-bar({n}) twice")
        if m >= UBAR[n]:
            raise ValueError(f"--ubar {item}: may only lower the built-in u-bar({n}) = {UBAR[n]}")
        if m < UBAR_LOWER[n]:
            raise ValueError(f"--ubar {item}: below the best known lower bound u({n}) >= "
                             f"{UBAR_LOWER[n]}, which a known unit-distance graph attains")
        ubar[n] = m
        overrides[str(n)] = {"builtin": UBAR[n], "value": m}
    if overrides:
        if not args.reach:
            raise ValueError("--ubar needs --reach (the override is recorded in reach.json)")
        if not (args.ubar_justification or "").strip():
            raise ValueError("--ubar needs a non-empty --ubar-justification")
    elif args.ubar_justification is not None:
        raise ValueError("--ubar-justification was given without --ubar")
    return ubar, overrides


def main() -> int:
    args = parse_args()
    args.udenum = args.udenum.resolve()
    if args.forbidden is None:
        args.forbidden = (Path(__file__).resolve().parent.parent / "data" /
                          FORBIDDEN_FILES[args.forbidden_set])
    args.forbidden = args.forbidden.resolve()
    args.geng = args.geng.resolve()
    outdir = args.output_dir.resolve()
    args.reach_json = outdir / "reach.json"
    if args.forbidden_set == 398 and sha256(args.forbidden) != FORBIDDEN_398_SHA256:
        raise ValueError(f"--forbidden-set 398 needs the pinned forbidden-398.json "
                         f"(sha256 {FORBIDDEN_398_SHA256}); {args.forbidden} has {sha256(args.forbidden)}")
    if args.mutation_seeds_74 and args.forbidden_set != 398:
        raise ValueError("--mutation-seeds-74 is a control for --forbidden-set 398 runs")
    chosen = [name for name in PRUNE_RULES if getattr(args, name)]
    if len(chosen) > 1:
        raise ValueError(f"at most one linear rule per run, not {chosen} (--triangles implies the rhombus rule)")
    args.rule = chosen[0] if chosen else None
    if args.rule and not args.prune:
        raise ValueError(f"--{args.rule} runs inside the prune step and needs --prune")
    if args.prune_filter_set == args.forbidden_set:
        args.prune_filter_set = None   # the default: the run's own set
    if args.prune_filter_set is not None:
        if not args.prune:
            raise ValueError("--prune-filter-set applies to the prune step and needs --prune")
        if args.prune_filter_set == 398:
            raise ValueError("--prune-filter-set 398 in a set-74 run would call the tree's graphs containing one of "
                             "GP-10's 324 a generator bug")
        if not args.verify_stages:
            raise ValueError("--prune-filter-set 74 in a set-398 run needs --verify-stages: the stage verification "
                             "is then the only re-check of the 324 (PRUNING.md 5.6)")
    args.ubar, args.ubar_override = effective_ubar(args)
    if args.shard_size < 1:
        raise ValueError("--shard-size must be positive")
    if args.slice_level is not None:
        if args.slice_index is None or args.slice_count is None:
            raise ValueError("--slice-level needs --slice-index and --slice-count")
        if not (args.slice_count >= 1 and 0 <= args.slice_index < args.slice_count):
            raise ValueError("need 0 <= --slice-index < --slice-count")
        if not (args.seed_n <= args.slice_level < args.target_n):
            raise ValueError("--slice-level must lie between the seed level and the target")
    elif args.slice_index is not None or args.slice_count is not None:
        raise ValueError("--slice-index/--slice-count need --slice-level")
    if outdir.exists() and not args.resume:
        raise RuntimeError("output directory exists, use --resume to continue it")
    outdir.mkdir(parents=True, exist_ok=True)
    immediate_parent_lower = math.ceil(args.target_m * (args.target_n - 2) / args.target_n)
    if (args.target_n - 1 in args.ubar and
            immediate_parent_lower > args.ubar[args.target_n - 1]):
        parents_dir = outdir / "_parents"
        parents_dir.mkdir(exist_ok=True)
        parent_file = parents_dir / f"{args.target_n}-{args.target_m}.g6"
        parent_file.write_bytes(b"")
        output = outdir / f"{args.target_n}-{args.target_m}.g6"
        output.write_bytes(b"")
        manifest = outdir / f"{args.target_n}-{args.target_m}.manifest.json"
        now = utc_now()
        args.reach = False
        write_aggregate_manifest(args, manifest, parent_file, 0, [], output, now, now)
        value = {
            "target": [args.target_n, args.target_m],
            "empty_by_schade": {
                "required_parent_edges": immediate_parent_lower,
                "parent_ubar": args.ubar[args.target_n - 1],
            },
            **non_default_options(args),
            "completed_through_n": args.target_n,
            "levels": [{"n": args.target_n, "m": args.target_m,
                        "parents": 0, "children": 0}],
        }
        (outdir / "run-summary.json").write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps(value["empty_by_schade"]))
        return 0
    windows = windows_for(args.target_n, args.target_m, args.seed_n, args.ubar)
    table: dict[int, dict[int, int]] | None = None
    if args.reach:
        source = "Schade: d >= target_m - u-bar(target_n - 1)"
        if args.reach_root_k is None:
            args.reach_root_k = max(0, args.target_m - args.ubar[args.target_n - 1])
            if (args.target_n, args.target_m) in ROOT_K_LEMMAS:
                args.reach_root_k, source = ROOT_K_LEMMAS[(args.target_n, args.target_m)]
        else:
            source = "command line --reach-root-k"
        table = reach_table(args.target_n, args.target_m, args.reach_root_k, args.seed_n, args.ubar)
        for n, level in table.items():
            low, high = windows[n]
            for m in level:
                if not low <= m <= high:
                    raise RuntimeError(f"reach level ({n},{m}) lies outside Schade's window {windows[n]}")
        reach_value = {
            "target": [args.target_n, args.target_m],
            "seed_n": args.seed_n,
            "root_k": args.reach_root_k,
            "root_k_source": source,
            # Keep historical reach.json bytes and hashes for targets through 23; later bounds
            # are recorded only when the target uses them or an explicit override names them.
            "ubar": {str(k): v for k, v in sorted(args.ubar.items())
                     if k <= max(23, args.target_n) or str(k) in args.ubar_override},
            "table": {str(n): {str(m): k for m, k in sorted(level.items())}
                      for n, level in sorted(table.items())},
            "schade_windows": {str(k): list(v) for k, v in sorted(windows.items())},
        }
        if args.ubar_override:
            reach_value["ubar_override"] = args.ubar_override
            reach_value["ubar_justification"] = args.ubar_justification
        if args.reach_json.exists():
            previous = json.loads(args.reach_json.read_text())
            if previous != reach_value:
                raise RuntimeError("existing reach.json differs from this run's reach table; "
                                   "a resumed run must use the same table")
        else:
            args.reach_json.write_text(json.dumps(reach_value, indent=2) + "\n")
    elif args.reach_json.exists():
        raise RuntimeError("output directory has a reach.json but --reach was not given")
    config_path = outdir / "run-config.json"
    config = run_config(args)
    if config_path.exists():
        if json.loads(config_path.read_text()) != config:
            raise RuntimeError("run-config.json differs from this run's options; refusing to resume")
    else:
        config_path.write_text(json.dumps(config, indent=2) + "\n")
    if args.prune:
        tools = [args.prune_python, Path(__file__).resolve().parent / "prune.py"]
        if args.rule:   # prune.py's defaults (its checker path may come from PRUNE_UDCHECK_RHOMBUS)
            ud = Path(__file__).resolve().parent.parent
            tools += [ud / "filter" / PRUNE_RULES[args.rule],
                      Path(os.environ.get("PRUNE_UDCHECK_RHOMBUS") or ud / "check" / "udcheck_rhombus.py")]
        for tool in tools:
            if not tool.is_file():
                raise RuntimeError(f"missing pruning tool: {tool}")
    summary: list[dict[str, object]] = []
    for n in range(0, args.seed_n):
        run_seed(args, outdir, n, args.ubar[n], summary)
    seed_levels = sorted(table[args.seed_n]) if table is not None else list(
        range(windows[args.seed_n][0], windows[args.seed_n][1] + 1))
    for m in seed_levels:
        entry = run_seed(args, outdir, args.seed_n, m, summary)
        after_level(args, outdir, table, args.seed_n, m, entry)
    write_summary(outdir, args, windows, table, args.seed_n, summary)
    for n in range(args.seed_n + 1, args.target_n + 1):
        levels = sorted(table[n]) if table is not None else list(range(windows[n][0], windows[n][1] + 1))
        for m in levels:
            entry = run_level_file(args, outdir, windows, table, n, m, summary)
            after_level(args, outdir, table, n, m, entry)
            write_summary(outdir, args, windows, table, n, summary)
    print(json.dumps({"target": [args.target_n, args.target_m],
                      "windows": windows,
                      "reach_levels": ({str(n): sorted(v) for n, v in sorted(table.items())}
                                       if table is not None else None),
                      "files": len(summary)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"run-dag2.py: {error}", file=sys.stderr)
        raise SystemExit(2)
