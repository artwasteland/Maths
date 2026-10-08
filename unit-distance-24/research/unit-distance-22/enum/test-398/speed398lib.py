"""Shared helpers for the Mode 398 speed work: the speed398-*.py scripts.

Nothing here decides a verdict.  It runs udenum binaries (always under `nice -n 15`), reads their
stats line, hashes outputs and builds test variants of the new source with the Makefile's flags.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENUM = HERE.parent
UD = ENUM.parent
REPO = UD.parent.parent
DATA = UD / "data"
F74 = DATA / "forbidden-74.json"
F398 = DATA / "forbidden-398.json"
F398_G6 = DATA / "forbidden-398.g6"

NEW_UDENUM = ENUM / "udenum"                      # the optimized source, built by enum/Makefile
NEW_SOURCE = ENUM / "udenum.c"
BASE398_UDENUM = HERE / "base398" / "udenum"      # the CURRENT Mode 398 (952ae252d), unmodified
BASE398_SOURCE = HERE / "base398" / "udenum.c"
OLD74_UDENUM = HERE / "old" / "enum" / "udenum"   # the u(22) production binary (Mode 74 only)

BASE398_SHA256 = "a99b130ab5ad0386265c429b78cf3c4a4c708e1d5dd6e222bec14a4596c16a84"
BASE398_SOURCE_SHA256 = "b509682789fbcab8250182d7ae8330559910d7c1322b84cf5d18c4f5961a5016"
PRODUCTION_UDENUM_SHA256 = "94a85d333d753ec2f518e62ef6d2f855d56b22dc6f3b890f53aa9575680f57b4"
F398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"

SCRATCH = Path(os.environ.get("T398_SCRATCH", "/tmp/t398-work"))

COUNTERS = ("parents_seen", "parents_processed", "parents_degree_skipped", "bad_sets",
            "neighbourhoods", "neighbourhood_orbit_reps", "neighbourhoods_bad",
            "child_orbit_rejected", "children_written")

CFLAGS = ["-O3", "-DNDEBUG", "-std=c17", "-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Wconversion",
          "-Wno-old-style-declaration", "-I/usr/include/x86_64-linux-gnu/nauty", "-I/usr/include/nauty"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def g6_lines(path: Path) -> list[bytes]:
    return [x for x in Path(path).read_bytes().split(b"\n") if x]


def write_lines(path: Path, lines) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"".join(x + b"\n" for x in lines))


def g6_order_size(line: bytes) -> tuple[int, int]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    return n, bits[: n * (n - 1) // 2].count("1")


def run_udenum(binary: Path, parents: Path, n: int, m: int, out: Path, forbidden_set: int = 398,
               extra=()) -> dict:
    """Run udenum; return {"returncode", "stderr_tail", "stats" (or None), "cpu", "output"}.

    A failing run is returned, not raised: some comparisons (--verify-parents on parents that
    contain a forbidden graph) expect both binaries to fail the same way."""
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = out.with_suffix(".manifest.json")
    forbidden = F398 if forbidden_set == 398 else F74
    cmd = ["nice", "-n", "15", str(binary), "--parents", str(parents), "--forbidden", str(forbidden),
           "--n", str(n), "--m", str(m), "--output", str(out), "--manifest", str(manifest),
           "--shard-id", out.stem, "--overwrite", *extra]
    if forbidden_set == 398:
        cmd += ["--forbidden-set", "398"]
    t0 = time.monotonic()
    p = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.monotonic() - t0
    lines = [x for x in p.stderr.strip().splitlines() if x.strip()]
    stats = None
    if p.returncode == 0 and lines and lines[-1].startswith("{"):
        stats = json.loads(lines[-1])
    return {"returncode": p.returncode, "stderr_tail": lines[-1] if lines else "", "stats": stats,
            "cpu": stats["cpu_seconds"] if stats else None, "wall": wall, "output": out}


def build_variant(source: Path, binary: Path, defines=(), extra_flags=(), allow_warnings: bool = False) -> Path:
    """Compile a udenum source with the Makefile's flags plus -D defines (test builds only).

    A clean build must be warning-free; a planted fault (speed398-red.py) may leave e.g. an
    unused parameter behind, so mutants pass allow_warnings=True."""
    binary.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["nice", "-n", "15", "cc", *CFLAGS, *[f"-D{d}" for d in defines], *extra_flags, str(source),
           "-o", str(binary), "-lnauty"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"build failed: {' '.join(cmd)}\n{p.stderr}")
    if p.stderr.strip() and not allow_warnings:
        raise RuntimeError(f"build produced warnings: {' '.join(cmd)}\n{p.stderr}")
    return binary


def compare_runs(ref: dict, got: dict) -> list[str]:
    """Byte-level comparison of two udenum runs: exit status, output bytes, all nine counters.

    Deliberately NOT a comparison of child counts or of child sets: two outputs can have the
    same count and the same set and still differ (order), and only the bytes are the output."""
    problems = []
    if ref["returncode"] != got["returncode"]:
        problems.append(f"exit status {ref['returncode']} vs {got['returncode']}")
        return problems
    ref_bytes = Path(ref["output"]).read_bytes() if Path(ref["output"]).exists() else None
    got_bytes = Path(got["output"]).read_bytes() if Path(got["output"]).exists() else None
    if ref_bytes != got_bytes:
        problems.append("output bytes differ")
    if ref["returncode"] != 0:
        # a refusal (e.g. --verify-parents): same message, and exit() flushed the same children
        if ref["stderr_tail"] != got["stderr_tail"]:
            problems.append(f"failure message differs: {ref['stderr_tail']!r} vs {got['stderr_tail']!r}")
        return problems
    for k in COUNTERS:
        if ref["stats"][k] != got["stats"][k]:
            problems.append(f"counter {k}: {ref['stats'][k]} vs {got['stats'][k]}")
    return problems
