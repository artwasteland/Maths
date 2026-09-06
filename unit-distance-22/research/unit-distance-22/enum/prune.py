#!/usr/bin/env python3
"""Hereditary pruning of one level file of the F-free DAG (see enum/PRUNING.md, L1 to L3).

Input: a level file ``<n>-<m>.g6`` or ``<n>-<m>.reach.g6`` (canonical graph6, one graph per
line, every graph with n vertices and m edges).  Steps, all recorded in the manifest:

1. filter/udfilter on every graph.  Only the verdicts "tu" and "pass" are legal here; a
   "forbidden" verdict means the generator emitted a non-F-free graph and the step aborts.
2. embed/udembed.py on the survivors, in chunks, up to --jobs processes at a time, with a
   wall-clock budget per graph.  A graph whose chunk and individual reruns both time out is
   recorded as "unknown" (conservative: it is kept).
3. ``<n>-<m>.certs.jsonl``: one certificate per input graph, in input order, in the schema of
   check/udcheck.py; ``<n>-<m>.UNKNOWN.g6``: the unknown graphs in order (always written);
   ``<n>-<m>.keep.g6``: the embedded and unknown graphs in input order (the parents the next
   level is built from); ``<n>-<m>.prune.manifest.json``.
4. check/udcheck.py replays every certificate against the input list; a rejection aborts.
5. An independent re-read of the written files verifies that keep + pruned = input.

The TU verdict is a refutation only at or above the proved maximum edge count of the TARGET
(CONTRACT Section 1 and PRUNING.md L2), so --target-n and --target-m are required and the
step refuses to run when the target lies below the proved bound.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Proved upper bounds on u(n): AMP Theorem 1(a) gives u(n) exactly for n <= 21 and
# Theorem 1(b) gives u(22) <= 61.  The TU rule (L2) needs target_m >= UPPER[target_n].
UPPER = {16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57, 22: 61}

FILTER_VERDICTS = {"tu", "pass"}
EMBED_VERDICTS = {"embedded", "refuted", "unknown"}
KEEP_VERDICTS = {"embedded", "unknown"}


class PruneError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decode_graph6(code: str) -> tuple[int, int, int]:
    """Return (vertices, edges, minimum degree) of a short-form graph6 string."""
    if not code or ord(code[0]) < 63 or ord(code[0]) > 126:
        raise PruneError(f"invalid graph6 record {code!r}")
    n = ord(code[0]) - 63
    if n > 62:
        raise PruneError("long graph6 forms are not supported")
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    needed = n * (n - 1) // 2
    if len(bits) < needed or len(bits) - needed >= 6:
        raise PruneError(f"graph6 record of wrong length {code!r}")
    if any(ch != "0" for ch in bits[needed:]):
        raise PruneError(f"graph6 padding is not zero {code!r}")
    degree = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                degree[i] += 1
                degree[j] += 1
            k += 1
    return n, sum(degree) // 2, (min(degree) if n else 0)


def read_g6(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise PruneError(f"{path}: missing final newline")
    lines = raw.decode("ascii").split("\n")[:-1] if raw else []
    if any(not line or line.startswith(">>") for line in lines):
        raise PruneError(f"{path}: blank or header line in graph list")
    return lines


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(line + "\n" for line in lines), encoding="ascii")


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.endswith("\n") or not line.strip():
                raise PruneError(f"{path}:{lineno}: malformed JSON line")
            records.append(json.loads(line))
    return records


def iter_jsonl(path: Path):
    """Stream the records of a JSON-lines file; the (13,23) cell has 19.5 million of them and
    materialising them as dicts needs about 14 GB (a cloud worker was OOM-killed doing so)."""
    with path.open("r", encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.endswith("\n") or not line.strip():
                raise PruneError(f"{path}:{lineno}: malformed JSON line")
            yield json.loads(line)


def dump(record: dict) -> str:
    return json.dumps(record, separators=(",", ":"), sort_keys=True)


def level_from_name(path: Path) -> tuple[int, int]:
    match = re.match(r"^(\d+)-(\d+)(\.reach)?\.g6$", path.name)
    if not match:
        raise PruneError(f"level file name must be <n>-<m>.g6 or <n>-<m>.reach.g6: {path.name}")
    return int(match.group(1)), int(match.group(2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=Path, required=True, help="<n>-<m>.g6 or <n>-<m>.reach.g6")
    parser.add_argument("--target-n", type=int, required=True)
    parser.add_argument("--target-m", type=int, required=True)
    parser.add_argument("--jobs", type=int, choices=tuple(range(1, 17)), default=1)
    parser.add_argument("--tries", type=int, default=24, help="udembed --tries")
    parser.add_argument("--max-states", type=int, default=400, help="udembed --max-states")
    parser.add_argument("--chunk", type=int, default=25, help="graphs per embedder process")
    parser.add_argument("--graph-timeout", type=float, default=120.0,
                        help="wall-clock seconds allowed per graph before it is recorded unknown")
    parser.add_argument("--python", type=Path,
                        default=Path(os.path.expanduser("~/tools/pyenv-maths/bin/python")))
    parser.add_argument("--udfilter", type=Path, default=ROOT / "filter" / "udfilter")
    parser.add_argument("--udembed", type=Path, default=ROOT / "embed" / "udembed.py")
    parser.add_argument("--udcheck", type=Path, default=ROOT / "check" / "udcheck.py")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--record", action="append", default=[], metavar="NAME=PATH",
                        help="extra input file whose hash goes into the manifest (for example reach.json)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--filter-only", action="store_true",
                        help="hereditary TU pruning only: skip the embedder, survivors become unknown (kept)")
    parser.add_argument("--mutation-unknown-as-pruned", action="store_true",
                        help="TEST ONLY: drop unknown graphs from keep and UNKNOWN (must go red)")
    return parser.parse_args()


def nice(command: list[str]) -> list[str]:
    return ["nice", "-n", "10", *command]


FILTER_PART_MAX = 200_000   # graphs per udfilter process: a killed run loses at most one part


def run_filter_part(args: argparse.Namespace, codes: list[str], prefix: Path) -> Path:
    out = prefix.with_suffix(".jsonl")
    err = prefix.with_suffix(".stderr")
    source = prefix.with_suffix(".g6")
    # Resume: a part whose input is byte-identical to these codes and whose output has one
    # record per graph was completed by an earlier (killed) run of the same level; udfilter is
    # deterministic per graph, so the records are reused. Anything else is redone from scratch.
    if source.is_file() and out.is_file():
        expected = "".join(code + "\n" for code in codes).encode("ascii")
        try:
            if source.read_bytes() == expected and sum(1 for _ in out.open("rb")) == len(codes):
                return out
        except OSError:
            pass
        out.unlink(missing_ok=True)
    write_lines(source, codes)
    with prefix.with_suffix(".g6").open("rb") as stdin, out.open("wb") as stdout, err.open("wb") as stderr:
        result = subprocess.run(nice([str(args.udfilter), "-f", str(args.data_dir / "forbidden-74.json"),
                                      "-t", str(args.data_dir / "tu-gadgets.json")]),
                                stdin=stdin, stdout=stdout, stderr=stderr)
    if result.returncode != 0:
        raise PruneError(f"udfilter failed with status {result.returncode}: {err.read_text()}")
    return out


def run_filter(args: argparse.Namespace, codes: list[str], workdir: Path,
               gadgets: list) -> tuple[list[str], int, float]:
    """Filter every graph, in --jobs contiguous parts; the filter is deterministic per graph.
    Returns the survivors (verdict pass, in input order), the tu count and the wall time; the
    records themselves stay on disk in filter.jsonl and are streamed again when written out."""
    out = workdir / "filter.jsonl"
    start = time.monotonic()
    n = len(codes)
    # Reuse finished parts OF ANY SIZE from an earlier run of this level: an older prune.py wrote
    # parts of ceil(N/jobs) graphs, this one writes parts of at most FILTER_PART_MAX, and a
    # restart must not re-filter a cell whose output already exists (2.5 h at (13,23)). A part
    # is reused when its input file equals the codes at its offset and its output has one record
    # per graph; udfilter is deterministic per graph, so the concatenation is the same bytes.
    done: dict[int, tuple[int, Path]] = {}
    for src in sorted(workdir.glob("filter-*.g6")):
        match = re.fullmatch(r"filter-(\d+)\.g6", src.name)
        jsonl = src.with_suffix(".jsonl")
        if not match or not jsonl.is_file():
            continue
        offset = int(match.group(1))
        try:
            data = src.read_bytes()
        except OSError:
            continue
        length = data.count(b"\n")
        if length == 0 or offset + length > n:
            continue
        expected = "".join(code + "\n" for code in codes[offset:offset + length]).encode("ascii")
        if data == expected and sum(1 for _ in jsonl.open("rb")) == length:
            done[offset] = (length, jsonl)
    size = max(1, min(-(-n // args.jobs), FILTER_PART_MAX))
    parts: list[tuple[int, list[str]]] = []      # gaps still to filter
    plan: list[tuple[int, Path | None]] = []     # output order: (offset, reused jsonl or None)
    pos = 0
    for offset in sorted(done):
        length, jsonl = done[offset]
        if offset < pos:
            continue                              # overlaps a part already planned: ignore it
        while pos < offset:
            k = min(size, offset - pos)
            parts.append((pos, codes[pos:pos + k])); plan.append((pos, None)); pos += k
        plan.append((offset, jsonl)); pos = offset + length
    while pos < n:
        k = min(size, n - pos)
        parts.append((pos, codes[pos:pos + k])); plan.append((pos, None)); pos += k
    reused = sum(length for length, _ in done.values() if True)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        produced = dict(zip([offset for offset, _ in parts], executor.map(
            lambda spec: run_filter_part(args, spec[1], workdir / f"filter-{spec[0]:08d}"), parts)))
    with out.open("wb") as stream:
        for offset, jsonl in plan:
            stream.write((jsonl if jsonl is not None else produced[offset]).read_bytes())
    wall = time.monotonic() - start
    print(f"prune.py: filter reused {reused} of {n} records from finished parts", file=sys.stderr)
    survivors: list[str] = []
    n_tu = 0
    count = 0
    for index, record in enumerate(iter_jsonl(out)):
        if index >= len(codes):
            raise PruneError(f"udfilter wrote more than {len(codes)} records for {len(codes)} graphs")
        code = codes[index]
        if record.get("g6") != code:
            raise PruneError("udfilter records are out of order")
        verdict = record.get("verdict")
        if verdict == "forbidden":
            raise PruneError("GENERATOR BUG: the level file contains a non-F-free graph "
                             f"{code} (forbidden witness {record.get('witness')})")
        if verdict not in FILTER_VERDICTS:
            raise PruneError(f"unexpected filter verdict {verdict!r} for {code}")
        if verdict == "tu":
            convert_tu_witness(record.get("witness"), gadgets, code)   # validated here, converted when written
            n_tu += 1
        else:
            survivors.append(code)
        count = index + 1
    if count != len(codes):
        raise PruneError(f"udfilter wrote {count} records for {len(codes)} graphs")
    return survivors, n_tu, wall


def convert_tu_witness(witness: object, gadgets: list, code: str) -> dict:
    """The filter's "pair" is the gadget's own pair (gadget-local indices, checked by
    filter/verify-witness.py); the binding checker schema (check/udcheck.py) wants the two
    candidate vertices the pair maps to.  CONTRACT 9.1: the producer ships the converter."""
    if not isinstance(witness, dict) or set(witness) != {"index", "map", "pair"}:
        raise PruneError(f"malformed tu witness for {code}")
    index, mapping, pair = witness["index"], witness["map"], witness["pair"]
    if not isinstance(index, int) or not 0 <= index < len(gadgets):
        raise PruneError(f"tu witness gadget index out of range for {code}")
    gadget = gadgets[index]
    if (not isinstance(mapping, list) or len(mapping) != gadget["n"] or
            len(set(mapping)) != len(mapping)):
        raise PruneError(f"tu witness map is not an injection of the gadget for {code}")
    if list(pair) != list(gadget["pair"]):
        raise PruneError(f"tu witness pair {pair} is not gadget {index}'s pair {gadget['pair']} for {code}")
    return {"index": index, "map": mapping, "pair": [mapping[pair[0]], mapping[pair[1]]]}


def embed_command(args: argparse.Namespace, path: Path, seed: int) -> list[str]:
    return nice([str(args.python), "-u", str(args.udembed), str(path), "--seed", str(seed),
                 "--tries", str(args.tries), "--max-states", str(args.max_states),
                 "--unknown-file", ""])


def run_embed_process(args: argparse.Namespace, codes: list[str], seed: int, prefix: Path,
                      timeout: float) -> list[dict] | None:
    """Run one udembed process; None on timeout, else the records (validated)."""
    write_lines(prefix.with_suffix(".g6"), codes)
    out = prefix.with_suffix(".jsonl")
    err = prefix.with_suffix(".stderr")
    with out.open("wb") as stdout, err.open("wb") as stderr:
        try:
            result = subprocess.run(embed_command(args, prefix.with_suffix(".g6"), seed),
                                    stdout=stdout, stderr=stderr, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
    if result.returncode != 0:
        raise PruneError(f"udembed failed with status {result.returncode}: {err.read_text()}")
    records = read_jsonl(out)
    if len(records) != len(codes):
        raise PruneError(f"udembed wrote {len(records)} records for {len(codes)} graphs ({prefix})")
    for code, record in zip(codes, records):
        if record.get("g6") != code:
            raise PruneError(f"udembed records are out of order ({prefix})")
        if record.get("verdict") not in EMBED_VERDICTS:
            raise PruneError(f"unexpected embedder verdict {record.get('verdict')!r} for {code}")
    return records


def run_embedder(args: argparse.Namespace, survivors: list[str], workdir: Path
                 ) -> tuple[list[dict], dict, float]:
    """Embed the survivors in chunks; seeds equal 1 + global index, as one long run would use."""
    start = time.monotonic()
    chunks = [(k, survivors[k:k + args.chunk]) for k in range(0, len(survivors), args.chunk)]
    timeouts: list[str] = []
    chunk_timeouts = 0
    startup = 60.0

    def run_chunk(spec: tuple[int, list[str]]) -> tuple[int, list[dict]]:
        nonlocal chunk_timeouts
        offset, codes = spec
        prefix = workdir / f"part-{offset:08d}"
        records = run_embed_process(args, codes, 1 + offset, prefix,
                                    startup + args.graph_timeout * len(codes))
        if records is not None:
            return offset, records
        chunk_timeouts += 1
        records = []
        for i, code in enumerate(codes):
            single = workdir / f"single-{offset + i:08d}"
            got = run_embed_process(args, [code], 1 + offset + i, single, startup + args.graph_timeout)
            if got is None:
                timeouts.append(code)
                records.append({"g6": code, "verdict": "unknown"})
            else:
                records.extend(got)
        return offset, records

    results: list[tuple[int, list[dict]]] = []
    if chunks:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            results = list(executor.map(run_chunk, chunks))
    results.sort(key=lambda item: item[0])
    records = [record for _, chunk_records in results for record in chunk_records]
    if [r["g6"] for r in records] != survivors:
        raise PruneError("embedder records do not match the survivor list")
    stats = {"tries": args.tries, "max_states": args.max_states, "seed_base": 1,
             "chunk": args.chunk, "chunks": len(chunks), "graph_timeout_seconds": args.graph_timeout,
             "chunk_timeouts": chunk_timeouts, "graph_timeouts": timeouts}
    return records, stats, time.monotonic() - start


CHECK_CHUNK = int(os.environ.get("PRUNE_CHECK_CHUNK", "1000000"))   # certificates per udcheck process


def udcheck_once(args: argparse.Namespace, n: int, m: int, graphs: Path, certs: Path,
                 unknown: Path) -> tuple[str, str]:
    command = nice([str(args.python), str(args.udcheck), "--expect-n", str(n), "--expect-m", str(m),
                    "--graphs", str(graphs), "--unknown-file", str(unknown), str(certs)])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise PruneError(f"udcheck REJECTED the certificates: {result.stderr.strip()}")
    accept = [line for line in result.stdout.splitlines() if line.startswith("ACCEPT certificates")]
    if len(accept) != 1:
        raise PruneError("udcheck exited 0 without an ACCEPT line")
    return accept[0], result.stdout + result.stderr


def run_checker(args: argparse.Namespace, n: int, m: int, level: Path, certs: Path,
                unknown: Path, log: Path, codes: list[str]) -> tuple[str, float]:
    """Replay every certificate with the blind checker. A cell above CHECK_CHUNK records is
    checked in consecutive chunks (each with its own graph list and unknown list, cut from the
    same files in the same order) so the checker's memory stays bounded; the ACCEPT counts are
    summed. At or below CHECK_CHUNK it is the single call it always was."""
    start = time.monotonic()
    if len(codes) <= CHECK_CHUNK:
        accept, output = udcheck_once(args, n, m, level, certs, unknown)
        log.write_text(output)
        return accept, time.monotonic() - start
    totals: dict[str, int] = {}
    chunks = 0
    logs: list[str] = []
    chunk_dir = log.parent / "check-chunks"
    chunk_dir.mkdir(exist_ok=True)
    with certs.open("r", encoding="utf-8") as stream:
        for lo in range(0, len(codes), CHECK_CHUNK):
            hi = min(lo + CHECK_CHUNK, len(codes))
            c_certs = chunk_dir / f"chunk-{lo:09d}.certs.jsonl"
            c_graphs = chunk_dir / f"chunk-{lo:09d}.g6"
            c_unknown = chunk_dir / f"chunk-{lo:09d}.UNKNOWN.g6"
            unknown_here: list[str] = []
            with c_certs.open("w", encoding="utf-8") as out:
                for index in range(lo, hi):
                    line = stream.readline()
                    if not line:
                        raise PruneError("certificate file is shorter than the level file")
                    out.write(line)
                    if json.loads(line).get("verdict") == "unknown":
                        unknown_here.append(codes[index])
            write_lines(c_graphs, codes[lo:hi])
            write_lines(c_unknown, unknown_here)
            accept, output = udcheck_once(args, n, m, c_graphs, c_certs, c_unknown)
            logs.append(f"# chunk {lo}:{hi}\n{output}")
            for key, value in re.findall(r"(\w+)=(\d+)", accept):
                totals[key] = totals.get(key, 0) + int(value)
            chunks += 1
            for path in (c_certs, c_graphs, c_unknown):
                path.unlink()
        if stream.readline():
            raise PruneError("certificate file is longer than the level file")
    log.write_text("".join(logs))
    summary = " ".join(f"{key}={totals[key]}" for key in
                       ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes") if key in totals)
    return f"ACCEPT certificates {summary} (chunked: {chunks} chunks of at most {CHECK_CHUNK})", time.monotonic() - start


def verify_outputs(level: Path, certs: Path, keep: Path, unknown: Path) -> dict:
    """Independent re-read of the files on disk: keep + pruned must equal the input."""
    codes = read_g6(level)
    problems = []
    counts = {"records": 0, "tu": 0, "refuted": 0, "embedded": 0, "unknown": 0}
    expected_keep: list[str] = []
    expected_unknown: list[str] = []
    order_ok = True
    witness_problem: str | None = None
    partition_ok = True
    # One streamed pass: the graph list must equal the level file in order, every record is
    # either kept (embedded, unknown) or pruned (tu, refuted), which is the partition check.
    for index, r in enumerate(iter_jsonl(certs)):
        counts["records"] += 1
        code = r.get("g6")
        if index >= len(codes) or code != codes[index]:
            order_ok = False
        verdict = r.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
        if verdict in KEEP_VERDICTS:
            expected_keep.append(code)
        if verdict == "unknown":
            expected_unknown.append(code)
        if verdict in ("tu", "refuted", "embedded") and not isinstance(r.get("witness"), dict) and witness_problem is None:
            witness_problem = f"pruned or embedded record without witness: {code}"
        if verdict not in ("tu", "refuted", "embedded", "unknown"):
            partition_ok = False
    if counts["records"] != len(codes):
        order_ok = False
    if not order_ok:
        problems.append("certificate graph list differs from the level file")
    if read_g6(keep) != expected_keep:
        problems.append("keep file is not exactly the embedded and unknown records in order")
    if read_g6(unknown) != expected_unknown:
        problems.append("UNKNOWN file is not exactly the unknown records in order")
    if witness_problem:
        problems.append(witness_problem)
    if not partition_ok or not order_ok:
        problems.append("keep and pruned sets do not partition the level file")
    if problems:
        raise PruneError("output verification failed: " + "; ".join(problems))
    counts["kept"] = len(expected_keep)
    return counts


def main() -> int:
    args = parse_args()
    level = args.level.resolve()
    if not level.is_file():
        raise PruneError(f"level file not found: {level}")
    n, m = level_from_name(level)
    if args.target_n not in UPPER:
        raise PruneError(f"no proved upper bound on u({args.target_n}); TU pruning is not justified")
    if args.target_m < UPPER[args.target_n]:
        raise PruneError(f"target ({args.target_n},{args.target_m}) lies below the proved bound "
                         f"u({args.target_n}) <= {UPPER[args.target_n]}; TU pruning is not justified")
    if n > args.target_n or (n == args.target_n and m != args.target_m):
        raise PruneError(f"level ({n},{m}) is not an ancestor level of the target")
    for tool in (args.python, args.udfilter, args.udembed, args.udcheck):
        if not Path(tool).is_file():
            raise PruneError(f"missing tool: {tool}")
    outdir = level.parent
    stem = f"{n}-{m}"
    certs = outdir / f"{stem}.certs.jsonl"
    keep = outdir / f"{stem}.keep.g6"
    unknown = outdir / f"{stem}.UNKNOWN.g6"
    manifest = outdir / f"{stem}.prune.manifest.json"
    workdir = outdir / "_prune" / stem
    for path in (certs, keep, unknown, manifest):
        if path.exists() and not args.overwrite:
            raise PruneError(f"{path} exists, use --overwrite to replace it")
    # Keep completed filter parts (filter-<offset>.{g6,jsonl}) from an earlier killed run of the
    # same level: run_filter_part reuses a part only if its input is byte-identical to the codes
    # it is asked for. Everything else in the work directory is stale and removed.
    workdir.mkdir(parents=True, exist_ok=True)
    for stale in workdir.iterdir():
        if stale.name.startswith("filter-") and stale.suffix in (".g6", ".jsonl", ".stderr"):
            continue
        if stale.is_dir():
            shutil.rmtree(stale)
        else:
            stale.unlink()
    started = utc_now()
    total_start = time.monotonic()

    codes = read_g6(level)
    if len(set(codes)) != len(codes):
        raise PruneError("duplicate graph6 record in the level file")
    for code in codes:
        vertices, edges, _ = decode_graph6(code)
        if vertices != n or edges != m:
            raise PruneError(f"{code} has ({vertices},{edges}), expected ({n},{m})")

    gadgets = json.loads((args.data_dir / "tu-gadgets.json").read_text())
    if not isinstance(gadgets, list) or len(gadgets) != 6:
        raise PruneError("tu-gadgets.json must list the six gadgets")
    survivors, n_tu, filter_wall = run_filter(args, codes, workdir, gadgets)
    write_lines(workdir / "survivors.g6", survivors)
    if args.filter_only:
        by_code = None   # every survivor is recorded unknown; no per-record dict is kept in memory
        embed_counts = {"embedded": 0, "refuted": 0, "unknown": len(survivors)}
        embed_stats, embed_wall = {"skipped": True, "filter_only": True, "survivors": len(survivors)}, 0.0
    else:
        embed_records, embed_stats, embed_wall = run_embedder(args, survivors, workdir)
        by_code = {r["g6"]: r for r in embed_records}
        embed_counts = {v: sum(1 for r in embed_records if r["verdict"] == v)
                        for v in ("embedded", "refuted", "unknown")}

    # The certificate file is written in one streamed pass over filter.jsonl, in input order:
    # a tu record with its witness converted to the checker's schema, otherwise the embedder's
    # record (or {g6, unknown} in filter-only mode). Byte-identical to the former in-memory path.
    unknown_codes: list[str] = []
    keep_codes: list[str] = []
    embedded_codes: list[str] = []
    with certs.open("w", encoding="utf-8") as stream:
        for code, filtered in zip(codes, iter_jsonl(workdir / "filter.jsonl")):
            if filtered["verdict"] == "tu":
                record = {"g6": code, "verdict": "tu",
                          "witness": convert_tu_witness(filtered.get("witness"), gadgets, code)}
            elif by_code is None:
                record = {"g6": code, "verdict": "unknown"}
            else:
                record = by_code[code]
            verdict = record["verdict"]
            if verdict == "unknown":
                unknown_codes.append(code)
            if verdict == "embedded":
                embedded_codes.append(code)
            if verdict in KEEP_VERDICTS:
                keep_codes.append(code)
            stream.write(dump(record) + "\n")
    if args.mutation_unknown_as_pruned:
        unknown_codes = []
        keep_codes = embedded_codes
    write_lines(unknown, unknown_codes)
    write_lines(keep, keep_codes)

    problems: list[str] = []
    accept_line = ""
    check_wall = 0.0
    try:
        accept_line, check_wall = run_checker(args, n, m, level, certs, unknown, workdir / "udcheck.log", codes)
    except PruneError as error:
        problems.append(str(error))
    counts: dict = {}
    try:
        counts = verify_outputs(level, certs, keep, unknown)
    except PruneError as error:
        problems.append(str(error))
    finished = utc_now()

    software = {
        "prune.py": sha256(Path(__file__).resolve()),
        "udfilter": sha256(args.udfilter),
        "udembed.py": sha256(args.udembed),
        "exact_verify.py": sha256(args.udembed.parent / "exact_verify.py"),
        "udcheck.py": sha256(args.udcheck),
        "python": f"{args.python} {platform.python_version()}",
    }
    inputs = {str(level): sha256(level),
              str(args.data_dir / "forbidden-74.json"): sha256(args.data_dir / "forbidden-74.json"),
              str(args.data_dir / "tu-gadgets.json"): sha256(args.data_dir / "tu-gadgets.json")}
    for item in args.record:
        name, _, path = item.partition("=")
        inputs[name] = sha256(Path(path))
    value = {
        "kind": "prune",
        "level": [n, m],
        "level_file": str(level),
        "target": [args.target_n, args.target_m],
        "tu_rule_bound": {"n": args.target_n, "proved_upper_bound": UPPER[args.target_n]},
        "software_sha256": software,
        "inputs_sha256": inputs,
        "outputs_sha256": {str(certs): sha256(certs), str(keep): sha256(keep),
                           str(unknown): sha256(unknown),
                           str(workdir / "filter.jsonl"): sha256(workdir / "filter.jsonl"),
                           str(workdir / "survivors.g6"): sha256(workdir / "survivors.g6")},
        "counts": {"input": len(codes), "tu": n_tu,
                   "survivors": len(survivors),
                   "embedded": embed_counts["embedded"],
                   "refuted": embed_counts["refuted"],
                   "unknown": embed_counts["unknown"],
                   "kept": len(keep_codes), "pruned": len(codes) - len(keep_codes)},
        "embedder": embed_stats,
        "jobs": args.jobs,
        "wall_seconds": {"filter": filter_wall, "embed": embed_wall, "check": check_wall,
                         "total": time.monotonic() - total_start},
        "checker": accept_line,
        "verified_counts": counts,
        "mutation": {"unknown_as_pruned": bool(args.mutation_unknown_as_pruned)},
        "started": started,
        "finished": finished,
        "host": socket.gethostname(),
        "exit_status": 1 if problems else 0,
        "problems": problems,
    }
    manifest.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"level": [n, m], "counts": value["counts"], "wall_seconds": value["wall_seconds"],
                      "checker": accept_line, "problems": problems}))
    if problems:
        print("prune.py: RED: " + " | ".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PruneError, subprocess.CalledProcessError) as error:
        print(f"prune.py: {error}", file=sys.stderr)
        raise SystemExit(2)
