#!/usr/bin/env python3
"""prune.py's parallel certificate replay (check_in_parallel) against the landed prune.py of BEFORE_COMMIT.

Every run executes from e2e.py's scratch tree (the tree's binaries, the REAL check/udcheck_rhombus.py, e2e.py's
build_tree) with --triangles and --jobs 2 (this box allows two busy cores; the cloud workers use 4). A cell of more
than PRUNE_CHECK_PARALLEL_ABOVE records (default 20,000) is replayed in min(--jobs, ...) contiguous chunks of
ceil(N / jobs) records, at most PRUNE_CHECK_CHUNK each, --jobs at a time.

U  Units, in process (prune.py imported): line_cuts and unknown_cuts on synthetic files (the chunks are the file's
   own bytes; unknown entries fall in the right chunk, empty chunks included; an UNKNOWN file with a swapped pair,
   a duplicate, a foreign line, a blank line or no final newline is refused), and check_in_parallel's orchestration
   with a stand-in checker (the plan, the sums, and five red controls: a rejected chunk names itself and keeps its
   files, an under-counting ACCEPT line, a missing ACCEPT line, a missing unknown entry, a chunk that cannot run).
A  (16,41) Mode 398 and Mode 74, --triangles, default threshold (no cell reaches 20,000 records): the new prune.py's
   run directory equals the landed one's file for file (bytes, or JSON after removing timestamps and timings and
   prune.py's own hash), with no parallel check anywhere: below the threshold nothing changed. CHAIN OK.
B  (16,41) Mode 398 --triangles with PRUNE_CHECK_PARALLEL_ABOVE=20 and PRUNE_CHECK_CHUNK=50, so every cell above 20
   records is replayed in parallel chunks (up to 10 per cell, 2 at a time): every file equals A's landed run except
   the replay's own traces (the checker line's "(parallel: ...)" suffix, the manifest's checker_chunking, the
   parallel cells' udcheck.log), so the summed ACCEPT counts equal the single call's key by key. CHAIN OK.
C  (18,46) Mode 74 --triangles, landed and new, default threshold: its cells above 20,000 records (12-22, 13-25,
   14-29) are replayed in 2 parallel chunks each; the comparison of B; the 16 known (18,46) graphs kept; CHAIN OK.
P  A planted bad certificate: prune.py --triangles on C's 14-29 cell (41,871 records) with PRUNE_CHECK_CHUNK=15000,
   so 3 chunks, 2 at a time, and a udtriangle wrapper that doubles the scale of ONE graph's tri certificate. In the
   middle chunk, and also the first and the last: prune.py must exit 1 with the manifest's problems naming that
   chunk (and no other) and the checker's reason, checker_chunking marking it rejected, its files kept holding the
   corrupted record. Control: the wrapper with nothing to corrupt exits 0 with C's certs, keep and UNKNOWN files.
   --mutation-unknown-as-pruned (UNKNOWN emptied) must go red through the parallel replay: the checker itself
   rejects, since each chunk's unknown list is cut from the UNKNOWN file prune.py wrote.
T  Timing: prune.py alone on C's three cells above the threshold, landed and new alternately, 2 repetitions: the
   check seconds (and the new run's per-chunk seconds) from the manifests; the outputs must be identical.

usage: checkpar.py [--phases U,A,B,C,P,T] [--jobs 2]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import e2e
from e2e import MATHS_PY, TREE, VOLATILE, build_tree, load_json_or_lines, sha256
from rhlib import REPO, SCRATCH, UD, log

BEFORE_COMMIT = "cfea96c54"   # origin/claude/answering-alexeev-u22 under this work: the landed prune.py
RUNS = SCRATCH / "checkpar"
PARALLEL = " (parallel: "
problems: list[str] = []


def install(which: str) -> str:
    rel = "research/unit-distance-22/enum/prune.py"
    data = (subprocess.run(["git", "show", f"{BEFORE_COMMIT}:{rel}"], cwd=REPO, capture_output=True, check=True).stdout
            if which == "landed" else (UD / "enum" / "prune.py").read_bytes())
    (TREE / "enum" / "prune.py").write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class Env:
    """Temporarily set (or with None, remove) environment variables for the runs made inside."""
    def __init__(self, **values):
        self.values = values
        self.saved = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.saved[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)

    def __exit__(self, *exc):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def load_prune():
    spec = importlib.util.spec_from_file_location("prune_under_test", UD / "enum" / "prune.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- U
def phase_units() -> None:
    pr = load_prune()
    work = RUNS / "units"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    codes = [f"c{i:03d}" for i in range(100)]
    ranges = [(0, 30), (30, 60), (60, 90), (90, 100)]
    lines = [json.dumps({"g6": c, "verdict": "unknown", "i": i}) for i, c in enumerate(codes)]
    certs = work / "certs.jsonl"
    certs.write_text("".join(x + "\n" for x in lines))
    cuts = pr.line_cuts(certs, ranges, 100)
    data = certs.read_bytes()
    pieces = [data[cuts[i]:cuts[i + 1]].decode().split("\n")[:-1] for i in range(len(ranges))]
    ok = pieces == [lines[lo:hi] for lo, hi in ranges] and cuts[-1] == len(data)
    log(f"U line_cuts: 4 chunks of the 100-line file are its lines 0-29, 30-59, 60-89, 90-99 byte for byte: {ok}")
    if not ok:
        problems.append("U line_cuts")
    for label, text in (("99 lines", "".join(x + "\n" for x in lines[:99])),
                        ("101 lines", "".join(x + "\n" for x in lines + lines[:1]))):
        bad = work / "bad.jsonl"
        bad.write_text(text)
        try:
            pr.line_cuts(bad, ranges, 100)
            refused = ""
        except pr.PruneError as error:
            refused = str(error)
        log(f"U line_cuts refuses a certificate file of {label}: {bool(refused)} ({refused})")
        if not refused:
            problems.append(f"U line_cuts accepted {label}")
    unknown = work / "UNKNOWN.g6"
    for entries, expect in (
            (["c005", "c010", "c095"], [["c005", "c010"], [], [], ["c095"]]),
            ([], [[], [], [], []]),
            (["c000", "c029", "c030", "c059", "c060", "c089", "c090", "c099"],
             [["c000", "c029"], ["c030", "c059"], ["c060", "c089"], ["c090", "c099"]]),
            (["c050"], [[], ["c050"], [], []]),
            (["c099"], [[], [], [], ["c099"]])):
        unknown.write_text("".join(x + "\n" for x in entries))
        offsets, sizes = pr.unknown_cuts(unknown, codes, ranges)
        raw = unknown.read_bytes()
        got = [raw[offsets[i]:offsets[i + 1]].decode().split("\n")[:-1] for i in range(len(ranges))]
        ok = got == expect and sizes == [len(x) for x in expect] and offsets[-1] == len(raw)
        log(f"U unknown_cuts {entries}: {got} sizes {sizes}: {ok}")
        if not ok:
            problems.append(f"U unknown_cuts {entries}")
    for label, text in (("a swapped pair", "c010\nc005\n"), ("a duplicate", "c005\nc005\n"),
                        ("a foreign line", "c005\nzzz\n"), ("a blank line", "c005\n\nc010\n"),
                        ("no final newline", "c005\nc010")):
        unknown.write_bytes(text.encode())
        try:
            pr.unknown_cuts(unknown, codes, ranges)
            refused = ""
        except pr.PruneError as error:
            refused = str(error)
        log(f"U unknown_cuts refuses {label}: {bool(refused)} ({refused})")
        if not refused:
            problems.append(f"U unknown_cuts accepted {label}")
    orchestration(pr, work, codes, lines)


def orchestration(pr, work: Path, codes: list[str], lines: list[str]) -> None:
    """check_in_parallel with a stand-in checker (it reads the chunk's files, so it sees exactly what the
    real checker would be given), N = 100, --jobs 2, CHECK_CHUNK 30: chunks of min(50, 30) = 30, so 4 chunks."""
    level = work / "level.g6"
    level.write_text("".join(c + "\n" for c in codes))
    unknown_codes = [c for i, c in enumerate(codes) if i % 3 == 0]   # every record says unknown; see below
    real_process = pr.udcheck_process
    pr.CHECK_CHUNK, pr.CHECK_PARALLEL_ABOVE = 30, 20
    args = argparse.Namespace(jobs=2, rhombus=False, triangles=False)
    calls: list[tuple[int, int]] = []

    def fake(mode: str):
        def run(args_, n, m, graphs, certs, unknown, work_dir):
            del args_, n, m, work_dir
            g = graphs.read_text().split("\n")[:-1]
            recs = [json.loads(x) for x in certs.read_text().split("\n")[:-1]]
            unk = unknown.read_text().split("\n")[:-1]
            lo = codes.index(g[0])
            calls.append((lo, lo + len(g)))
            unknown_verdicts = [r["g6"] for r in recs if r["verdict"] == "unknown"]
            if [r["g6"] for r in recs] != g or unk != unknown_verdicts:
                return subprocess.CompletedProcess([], 1, "", "REJECT: graph list or unknown list mismatch")
            if mode == "reject-60" and lo == 60:
                return subprocess.CompletedProcess([], 1, "", "REJECT record 7: planted")
            if mode == "no-accept":
                return subprocess.CompletedProcess([], 0, "all good\n", "")
            if mode == "raise" and lo == 30:
                raise OSError("cannot start the checker")
            records = len(recs) - (1 if mode == "undercount" and lo == 30 else 0)
            return subprocess.CompletedProcess([], 0, f"ACCEPT certificates records={records} forbidden=0 "
                                               f"tu={len(recs) - len(unk)} embedded=0 refuted=0 unknown={len(unk)} "
                                               f"proof_nodes=0 rhombus_tu=0 rhombus_refuted=0 tri_tu={len(unk)} "
                                               f"tri_refuted=1\n", "")
        return run

    certs = work / "certs.jsonl"
    certs.write_text("".join(json.dumps({"g6": c, "verdict": "unknown" if c in unknown_codes else "tu"}) + "\n"
                             for c in codes))
    unknown = work / "UNKNOWN.g6"
    try:
        for mode in ("accept", "reject-60", "undercount", "no-accept", "raise", "unknown-short"):
            calls.clear()
            unknown.write_text("".join(c + "\n" for c in (unknown_codes[:-1] if mode == "unknown-short"
                                                          else unknown_codes)))
            shutil.rmtree(work / "check-chunks", ignore_errors=True)
            pr.udcheck_process = fake(mode)
            chunking: dict = {}
            try:
                accept, _ = pr.run_checker(args, 13, 25, level, certs, unknown, work / "udcheck.log", codes, chunking)
                error = ""
            except pr.PruneError as exc:
                accept, error = "", str(exc)
            plan = [c["range"] for c in chunking.get("chunks", [])]
            if mode == "accept":
                want = ("ACCEPT certificates records=100 forbidden=0 tu=66 embedded=0 refuted=0 unknown=34 "
                        "proof_nodes=0 rhombus_tu=0 rhombus_refuted=0 tri_tu=34 tri_refuted=4 "
                        "(parallel: 4 chunks of at most 30, 2 at a time)")
                ok = (accept == want and plan == [[0, 30], [30, 60], [60, 90], [90, 100]]
                      and chunking.get("jobs") == 2 and sorted(calls) == [(0, 30), (30, 60), (60, 90), (90, 100)]
                      and [c.get("unknown") for c in chunking["chunks"]] == [10, 10, 10, 4]
                      and not (work / "check-chunks").exists())
                log(f"U orchestration, all ACCEPT: {accept}; plan {plan}; unknown per chunk "
                    f"{[c.get('unknown') for c in chunking['chunks']]}; chunk files removed "
                    f"{not (work / 'check-chunks').exists()}: {ok}")
            elif mode == "reject-60":
                kept = sorted(p.name for p in (work / "check-chunks").iterdir()) if (work / "check-chunks").exists() else []
                ok = (not accept and "chunk 3 of 4 (records 60..89 of the cell, lines 61..90" in error
                      and "REJECT record 7: planted" in error and "chunk 1 of" not in error and "chunk 2 of" not in error
                      and "chunk-000000060.certs.jsonl" in kept and chunking["chunks"][2].get("rejected") is True
                      and all(not c.get("rejected") for i, c in enumerate(chunking["chunks"]) if i != 2)
                      and "# chunk 60:90" in (work / "udcheck.log").read_text())
                log(f"U orchestration, chunk 3 of 4 REJECTS: {error}; files kept {kept}; chunks "
                    f"{[{k: v for k, v in c.items() if k != 'wall_seconds'} for c in chunking['chunks']]}: {ok}")
            else:
                expect = {"undercount": "its ACCEPT line counts records=29 unknown=10, the chunk holds 30 and 10",
                          "no-accept": "udcheck exited 0 without an ACCEPT line",
                          "raise": "OSError: cannot start the checker",
                          "unknown-short": "REJECT: graph list or unknown list mismatch"}[mode]
                ok = not accept and expect in error and "udcheck REJECTED the certificates: chunk" in error
                log(f"U orchestration red control '{mode}': step fails: {not accept}; {error[:260]}: {ok}")
            if not ok:
                problems.append(f"U orchestration {mode}")
    finally:
        pr.udcheck_process = real_process


# ---------------------------------------------------------------- A, B, C
def parallel_cells(run: Path) -> dict[str, dict]:
    out = {}
    for p in run.glob("*.prune.manifest.json"):
        v = json.loads(p.read_text())
        if "checker_chunking" in v:
            out[p.name.split(".")[0]] = v
    return out


def norm(obj, hashes: dict, counter: dict):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in VOLATILE or k == "checker_chunking":
                counter[k] = counter.get(k, 0) + 1
                continue
            out[k] = norm(v, hashes, counter)
        return out
    if isinstance(obj, list):
        return [norm(v, hashes, counter) for v in obj]
    if isinstance(obj, str):
        if obj in hashes:
            counter[hashes[obj]] = counter.get(hashes[obj], 0) + 1
            return hashes[obj]
        if obj.startswith("ACCEPT certificates ") and PARALLEL in obj:
            counter["checker line (parallel: ...) suffix"] = counter.get("checker line (parallel: ...) suffix", 0) + 1
            return obj[:obj.index(PARALLEL)]
    return obj


def compare(base: Path, new: Path, hashes: dict) -> dict:
    """e2e.py's compare_dirs (bytes, then JSON modulo VOLATILE and the renaming of hashes of files already
    proved equivalent, to a fixed point), with the parallel replay's own traces removed: checker_chunking, the
    checker line's "(parallel: ...)" suffix, and the udcheck.log of the cells replayed in parallel."""
    par = parallel_cells(new)
    skip = {Path("_prune") / stem / "udcheck.log" for stem in par}
    files_b = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
    files_n = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
    only_b, only_n = sorted(files_b - files_n), sorted(files_n - files_b)
    renaming = dict(hashes)
    status: dict = {}
    counter: dict = {}
    pending = sorted((files_b & files_n) - skip)
    changed = True
    while changed:
        changed = False
        for rel in pending:
            if rel in status:
                continue
            b, n = (base / rel).read_bytes(), (new / rel).read_bytes()
            kind = None
            if b == n:
                kind = "bytes"
            else:
                try:
                    local: dict = {}
                    if norm(load_json_or_lines(base / rel), renaming, local) == \
                            norm(load_json_or_lines(new / rel), renaming, local):
                        kind = "json"
                        for k, v in local.items():
                            counter[k] = counter.get(k, 0) + v
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            if kind:
                status[rel] = kind
                name = f"<sha256 of {rel}>"
                renaming[hashlib.sha256(b).hexdigest()] = name
                renaming[hashlib.sha256(n).hexdigest()] = name
                changed = True
    differ = [str(rel) for rel in pending if rel not in status]
    return {"files": len(files_b), "only_base": [str(x) for x in only_b[:10]], "only_new": [str(x) for x in only_n[:10]],
            "byte_identical": sum(1 for v in status.values() if v == "bytes"),
            "json_equal_after_normalising": sum(1 for v in status.values() if v == "json"),
            "different": differ[:20], "parallel_cells": sorted(par), "udcheck_logs_skipped": len(skip & files_n),
            "normalised": {k: v for k, v in counter.items() if not k.startswith("<sha256 of")}}


def check_parallel_cells(base: Path, new: Path, label: str) -> list[str]:
    """Every cell the new run replayed in parallel: the plan covers the cell in contiguous chunks of at most
    max_chunk, every chunk ran and was accepted, the unknown entries add up, the log holds one ACCEPT per chunk,
    and the checker line's counts are the landed run's single call's, key by key."""
    rows = []
    for stem, v in sorted(parallel_cells(new).items(), key=lambda kv: tuple(map(int, kv[0].split("-")))):
        c = v["checker_chunking"]
        ranges = [x["range"] for x in c["chunks"]]
        contiguous = ranges[0][0] == 0 and ranges[-1][1] == c["records"] == v["counts"]["input"] and \
            all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])) and all(hi - lo <= c["max_chunk"] for lo, hi in ranges)
        clean = all(not x.get("rejected") and not x.get("not_run") for x in c["chunks"])
        unknown_sum = sum(x["unknown"] for x in c["chunks"]) == v["counts"]["unknown"]
        text = (new / "_prune" / stem / "udcheck.log").read_text()
        log_ok = text.count("# chunk ") == len(ranges) and \
            sum(1 for x in text.splitlines() if x.startswith("ACCEPT certificates")) == len(ranges)
        landed = json.loads((base / f"{stem}.prune.manifest.json").read_text())["checker"]
        same_counts = v["checker"].split(PARALLEL)[0] == landed and PARALLEL not in landed
        rows.append(f"{stem}: {c['records']} records in {len(ranges)} chunks of at most {c['chunk_size']} "
                    f"({c['jobs']} at a time), chunk seconds {[x['wall_seconds'] for x in c['chunks']]}; contiguous "
                    f"{contiguous}, all accepted {clean}, unknown adds up {unknown_sum}, log {log_ok}, counts = landed "
                    f"single call {same_counts}")
        if not (contiguous and clean and unknown_sum and log_ok and same_counts and len(ranges) >= 2):
            problems.append(f"{label} {stem}: parallel replay record {c} / counts {v['checker']} vs {landed}")
    return rows


def run_pair(target: tuple[int, int], mode: int, label: str, jobs: int, envs: dict[str, dict],
             hashes: dict, chain_for: tuple = ("new",)) -> dict[str, Path]:
    """Run the landed and/or new scripts (as named in envs: which -> environment) into the same output path,
    one after the other, each renamed to RUNS/<label>-<which> afterwards (the files hold absolute paths, so
    verify-chain.py --check runs on the runs named in chain_for before the renaming)."""
    out = RUNS / f"out-{target[0]}-{target[1]}-f{mode}"
    dirs = {}
    for which, env in envs.items():
        hashes[install(which.split("-")[0])] = "<prune.py sha256>"
        shutil.rmtree(out, ignore_errors=True)
        with Env(**env):
            code, wall, last = e2e.run_dag(out, target, mode, "triangles", jobs)
        log(f"{label} {which}: exit {code} after {wall:.0f} s (environment {env or 'default'})")
        if which in chain_for:
            chain_ok(out, f"{label} {which}")
        dest = RUNS / f"{label}-{which}"
        shutil.rmtree(dest, ignore_errors=True)
        out.rename(dest)
        (RUNS / f"{out.name}.log").rename(RUNS / f"{dest.name}.log")
        dirs[which] = dest
    return dirs


def chain_ok(run: Path, label: str) -> None:
    before = len(e2e.problems)
    e2e.chain(run, label)
    problems.extend(e2e.problems[before:])


def phase_a(jobs: int, hashes: dict) -> None:
    for mode in (398, 74):
        dirs = run_pair((16, 41), mode, f"a-16-41-f{mode}", jobs, {"landed": {}, "new": {}}, hashes)
        result = compare(dirs["landed"], dirs["new"], hashes)
        log(f"A (16,41) mode {mode}, default threshold: {json.dumps(result)}")
        if result["only_base"] or result["only_new"] or result["different"] or not result["files"] or \
                result["parallel_cells"] or any(k in result["normalised"] for k in
                                                ("checker_chunking", "checker line (parallel: ...) suffix")):
            problems.append(f"A mode {mode}: below the threshold the new prune.py changed something: {result}")


def phase_b(jobs: int, hashes: dict) -> None:
    dirs = run_pair((16, 41), 398, "b-16-41-f398", jobs,
                    {"new": {"PRUNE_CHECK_PARALLEL_ABOVE": 20, "PRUNE_CHECK_CHUNK": 50}}, hashes)
    base = RUNS / "a-16-41-f398-landed"
    result = compare(base, dirs["new"], hashes)
    log(f"B (16,41) mode 398, PRUNE_CHECK_PARALLEL_ABOVE=20 PRUNE_CHECK_CHUNK=50, against A's landed run: "
        f"{json.dumps(result)}")
    if result["only_base"] or result["only_new"] or result["different"] or not result["parallel_cells"]:
        problems.append(f"B: the parallel replay changed an output: {result}")
    for row in check_parallel_cells(base, dirs["new"], "B"):
        log("   ", row)
    if not any(len(v["checker_chunking"]["chunks"]) > jobs for v in parallel_cells(dirs["new"]).values()):
        problems.append("B: no cell had more chunks than --jobs (CHECK_CHUNK as the maximum chunk size untested)")


def phase_c(jobs: int, hashes: dict) -> dict:
    dirs = run_pair((18, 46), 74, "c-18-46-f74", jobs, {"landed": {}, "new": {}}, hashes, ("landed", "new"))
    result = compare(dirs["landed"], dirs["new"], hashes)
    log(f"C (18,46) mode 74, default threshold: {json.dumps(result)}")
    if result["only_base"] or result["only_new"] or result["different"] or \
            result["parallel_cells"] != ["12-22", "13-25", "14-29"]:
        problems.append(f"C: {result}")
    for row in check_parallel_cells(dirs["landed"], dirs["new"], "C"):
        log("   ", row)
    for which, run in dirs.items():
        before = len(e2e.problems)
        e2e.top_keep_check(run, 18, 46, f"C {which}")
        problems.extend(e2e.problems[before:])
    keep_same = all((dirs["landed"] / k.name).read_bytes() == k.read_bytes() for k in dirs["new"].glob("*.keep.g6"))
    log(f"C keep files identical, landed and new: {keep_same} ({len(list(dirs['new'].glob('*.keep.g6')))} files)")
    if not keep_same:
        problems.append("C: keep files differ")
    timing = {}
    for stem in ("12-22", "13-25", "14-29"):
        row = {}
        for which, run in dirs.items():
            v = json.loads((run / f"{stem}.prune.manifest.json").read_text())
            row[which] = round(v["wall_seconds"]["check"], 2)
        timing[stem] = row
    total = {which: round(sum(json.loads(p.read_text())["wall_seconds"]["check"] for p in run.glob("*.prune.manifest.json")), 1)
             for which, run in dirs.items()}
    log(f"C check seconds in the run, biggest cells: {json.dumps(timing)}; all cells: {json.dumps(total)}")
    return timing


# ---------------------------------------------------------------- P
WRAPPER = r'''#!{python}
"""TEST ONLY (checkpar.py P): udtriangle, but the tri certificate of the graph named by $CHECKPAR_CORRUPT gets its
first "scale" doubled; each corruption is appended to $CHECKPAR_MARK."""
import json, os, subprocess, sys
target = os.environ.get("CHECKPAR_CORRUPT", "")
data = sys.stdin.buffer.read()
codes = data.decode("ascii").split("\n")[:-1] if data else []
p = subprocess.run([{prover!r}], input=data, capture_output=True)
lines = p.stdout.decode().split("\n")[:-1]

def double(node):
    if isinstance(node, dict):
        if "scale" in node:
            node["scale"] = [2 * x for x in node["scale"]]
            return True
        return any(double(v) for v in node.values())
    if isinstance(node, list):
        return any(double(v) for v in node)
    return False

out = []
for code, line in zip(codes, lines):
    if target and code == target:
        record = json.loads(line)
        if record.get("verdict") in ("tu", "refuted") and double(record.get("witness")):
            line = json.dumps(record, separators=(",", ":"))
            with open(os.environ["CHECKPAR_MARK"], "a") as mark:
                mark.write(code + "\n")
    out.append(line)
out += lines[len(codes):]
sys.stdout.write("".join(x + "\n" for x in out))
sys.stderr.write(p.stderr.decode())
sys.exit(p.returncode)
'''


def prune_cell(level_src: Path, work: Path, jobs: int, env: dict, extra=()) -> tuple[int, dict, str, float]:
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    level = work / level_src.name
    shutil.copy2(level_src, level)
    n, m = map(int, level_src.name.split(".")[0].split("-"))
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "prune.py"), "--level", str(level),
           "--target-n", "18", "--target-m", "46", "--jobs", str(jobs), "--filter-only", "--triangles",
           "--python", str(MATHS_PY), *extra]
    t0 = time.monotonic()
    with Env(PRUNE_UDCHECK_RHOMBUS=None, **env):
        p = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.monotonic() - t0
    mpath = work / f"{n}-{m}.prune.manifest.json"
    man = json.loads(mpath.read_text()) if mpath.is_file() else {}
    return p.returncode, man, p.stderr, wall


def phase_p(jobs: int) -> None:
    install("new")
    source_run = RUNS / "c-18-46-f74-new"
    stem = "14-29"
    certs = (source_run / f"{stem}.certs.jsonl").read_text().split("\n")[:-1]
    wrapper = RUNS / "udtriangle-corrupt.py"
    wrapper.write_text(WRAPPER.replace("{python}", sys.executable).replace("{prover!r}", repr(str(TREE / "filter" / "udtriangle"))))
    wrapper.chmod(0o755)
    size = 15000
    total = len(certs)
    ranges = [(lo, min(lo + size, total)) for lo in range(0, total, size)]
    log(f"P cell {stem}: {total} records; with PRUNE_CHECK_CHUNK={size} and --jobs {jobs}: chunks {ranges}")
    targets = {}
    for position, (lo, hi), start in (("middle", ranges[1], ranges[1][0] + size // 2),
                                      ("first", ranges[0], size // 2), ("last", ranges[-1], ranges[-1][0] + 6000)):
        index = next(i for i in range(start, hi) if '"tri"' in certs[i])
        targets[position] = (index, json.loads(certs[index])["g6"], ranges.index((lo, hi)) + 1)
    level_src = source_run / f"{stem}.reach.g6"
    for position in ("control", "middle", "first", "last"):
        mark = RUNS / f"p-{position}.mark"
        mark.unlink(missing_ok=True)
        index, code, chunk = targets.get(position, (None, "", None))
        work = RUNS / f"p-{position}"
        code_rc, man, err, wall = prune_cell(level_src, work, jobs, {"PRUNE_CHECK_CHUNK": size, "CHECKPAR_CORRUPT": code,
                                                                     "CHECKPAR_MARK": mark},
                                             ["--udtriangle", str(wrapper)])
        marks = mark.read_text().split() if mark.is_file() else []
        chunking = man.get("checker_chunking", {})
        states = [("REJECTED" if c.get("rejected") else "not run" if c.get("not_run") else "accepted")
                  for c in chunking.get("chunks", [])]
        probs = man.get("problems", [])
        if position == "control":
            same = all((work / f"{stem}.{kind}").read_bytes() == (source_run / f"{stem}.{kind}").read_bytes()
                       for kind in ("certs.jsonl", "keep.g6", "UNKNOWN.g6"))
            ok = code_rc == 0 and man.get("exit_status") == 0 and not marks and same and states == ["accepted"] * 3
            log(f"P control (wrapper, nothing to corrupt): exit {code_rc} after {wall:.0f} s; chunks {states}; "
                f"certs, keep and UNKNOWN = the run's {same}; checker {man.get('checker')}: {ok}")
        else:
            lo, hi = ranges[chunk - 1]
            chunk_dir = work / "_prune" / stem / "check-chunks"
            kept = chunk_dir / f"chunk-{lo:09d}.certs.jsonl"
            corrupted_kept = kept.is_file() and any(json.loads(x)["g6"] == code for x in kept.read_text().split("\n")[:-1])
            names = re.findall(r"chunk (\d+) of 3", " ".join(probs))
            ok = (code_rc == 1 and man.get("exit_status") == 1 and marks == [code] and len(probs) == 1
                  and f"chunk {chunk} of 3 (records {lo}..{hi - 1} of the cell, lines {lo + 1}..{hi}" in probs[0]
                  and "udcheck REJECTED the certificates" in probs[0] and names == [str(chunk)]
                  and states[chunk - 1] == "REJECTED" and states.count("REJECTED") == 1 and corrupted_kept)
            log(f"P {position}: record {index} ({code}) in chunk {chunk} of 3 corrupted {marks == [code]}; exit {code_rc} "
                f"after {wall:.0f} s; chunks {states}; its files kept with the record {corrupted_kept}; "
                f"problems {probs}: {ok}")
        if not ok:
            problems.append(f"P {position}")
    # the unknown-as-pruned mutation through the parallel replay, and (for contrast, not a pass condition) through
    # the landed sequential chunked path (--jobs 1), whose chunk unknown lists are cut from the verdicts
    for label, run_jobs in (("parallel", jobs), ("sequential chunks, --jobs 1", 1)):
        work = RUNS / f"p-mutation-{run_jobs}"
        code_rc, man, err, wall = prune_cell(level_src, work, run_jobs, {"PRUNE_CHECK_CHUNK": size},
                                             ["--mutation-unknown-as-pruned"])
        probs = man.get("problems", [])
        checker_rejects = any("udcheck REJECTED" in x for x in probs)
        verification = any("UNKNOWN file" in x for x in probs)
        log(f"P --mutation-unknown-as-pruned, {label}: exit {code_rc}; the checker rejects {checker_rejects}; the "
            f"output verification fails {verification}; problems {[x[:200] for x in probs]}")
        if run_jobs > 1 and not (code_rc == 1 and checker_rejects and verification):
            problems.append(f"P mutation through the {label} replay")


# ---------------------------------------------------------------- T
def phase_t(jobs: int) -> None:
    source_run = RUNS / "c-18-46-f74-new"
    rows = {}
    for stem in ("12-22", "13-25", "14-29"):
        level_src = source_run / f"{stem}.reach.g6"
        samples: dict[str, list] = {"landed": [], "new": []}
        chunks = []
        outputs = {}
        for rep in (1, 2):
            for which in ("landed", "new"):
                install(which)
                work = RUNS / f"t-{stem}-{which}"
                code_rc, man, err, wall = prune_cell(level_src, work, jobs, {})
                if code_rc != 0:
                    problems.append(f"T {stem} {which}: exit {code_rc}: {err[-300:]}")
                    continue
                samples[which].append(round(man["wall_seconds"]["check"], 2))
                if which == "new":
                    chunks.append([x["wall_seconds"] for x in man["checker_chunking"]["chunks"]])
                outputs[which] = [sha256(work / f"{stem}.{k}") for k in ("certs.jsonl", "keep.g6", "UNKNOWN.g6")]
        same = outputs.get("landed") == outputs.get("new")
        rows[stem] = {"landed": samples["landed"], "new": samples["new"], "new_chunks": chunks}
        log(f"T {stem}: check seconds landed {samples['landed']}, new {samples['new']} (chunks {chunks}); outputs "
            f"identical {same}")
        if not same:
            problems.append(f"T {stem}: outputs differ")
    log(f"T summary: {json.dumps(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phases", default="U,A,B,C,P,T")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    phases = a.phases.split(",")
    for key in ("PRUNE_CHECK_CHUNK", "PRUNE_CHECK_PARALLEL_ABOVE", "PRUNE_UDCHECK_RHOMBUS"):
        os.environ.pop(key, None)
    RUNS.mkdir(parents=True, exist_ok=True)
    build_tree()
    shutil.copy2(UD / "enum" / "verify-chain.py", TREE / "enum" / "verify-chain.py")
    hashes: dict = {}
    for which in ("landed", "new"):
        hashes[install(which)] = "<prune.py sha256>"
    log(f"scratch tree {TREE}; landed prune.py ({BEFORE_COMMIT}) and new prune.py sha256: "
        f"{', '.join(h[:12] for h in hashes)}; the rules' checker is the real check/udcheck_rhombus.py "
        f"(sha256 {sha256(UD / 'check' / 'udcheck_rhombus.py')[:12]})")
    if "U" in phases:
        phase_units()
    if "A" in phases:
        phase_a(a.jobs, hashes)
    if "B" in phases:
        phase_b(a.jobs, hashes)
    if "C" in phases:
        phase_c(a.jobs, hashes)
    if "P" in phases:
        phase_p(a.jobs)
    if "T" in phases:
        phase_t(a.jobs)
    install("new")
    for p in problems:
        log("PROBLEM:", p)
    log("CHECKPAR", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
