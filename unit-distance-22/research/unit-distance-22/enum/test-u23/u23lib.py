"""Shared helpers for the u(23) integration checks (enum/test-u23).

Nothing here decides a verdict: it locates files, runs programs and hashes. Each script states
its own pass condition and its own red controls. Work directories live under U23_SCRATCH
(default /tmp/u23-work), never in the repository.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENUM = HERE.parent
UD = ENUM.parent
REPO = UD.parent.parent
DATA = UD / "data"
F74 = DATA / "forbidden-74.json"
F398 = DATA / "forbidden-398.json"
F398_G6 = DATA / "forbidden-398.g6"
TU = DATA / "tu-gadgets.json"
KNOWN = UD / "sources" / "amp" / "anc" / "graph6.txt"
UDENUM = ENUM / "udenum"
UDFILTER = UD / "filter" / "udfilter"
UDCHECK = UD / "check" / "udcheck.py"
UDCHECK398 = UD / "check" / "udcheck398.py"
VERIFY_WITNESS = UD / "filter" / "verify-witness.py"
RUN_DAG2 = ENUM / "run-dag2.py"
MATCHER32 = ENUM / "test-398" / "bin" / "matcher32"
LABELG = "/usr/bin/nauty-labelg"
MATHS_PY = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"

F74_SHA256 = "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a"
F398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
F398_G6_SHA256 = "91d5810c4d7b02d97afec7dfe2a2a5629f2075439100aa8eae6b60dca4ff4381"
UDCHECK_KERNEL_SHA256 = "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de"

SCRATCH = Path(os.environ.get("U23_SCRATCH", "/tmp/u23-work"))


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


def decode_g6(line: bytes) -> tuple[int, set[tuple[int, int]]]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    edges = set()
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                edges.add((i, j))
            k += 1
    return n, edges


def encode_g6(n: int, edges) -> bytes:
    es = {tuple(sorted(e)) for e in edges}
    bits = []
    for j in range(1, n):
        for i in range(j):
            bits.append(1 if (i, j) in es else 0)
    while len(bits) % 6:
        bits.append(0)
    return bytes([n + 63] + [63 + int("".join(map(str, bits[k:k + 6])), 2)
                             for k in range(0, len(bits), 6)])


def canonical(lines: list[bytes]) -> list[bytes]:
    """nauty-labelg canonical forms, in input order."""
    if not lines:
        return []
    p = subprocess.run([LABELG, "-q"], input=b"".join(x + b"\n" for x in lines),
                       capture_output=True, check=True)
    out = [x for x in p.stdout.split(b"\n") if x]
    if len(out) != len(lines):
        raise RuntimeError("labelg returned a different number of graphs")
    return out


def load_run_dag2():
    """run-dag2.py as a module (for its functions; nothing runs on import)."""
    spec = importlib.util.spec_from_file_location("run_dag2_under_test", RUN_DAG2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_matcher(patterns_g6: Path, hosts: Path, workdir: Path, chunk: int = 128) -> dict:
    """GP-10's matcher widened to 31-vertex hosts (enum/test-398/matcher32.c), chained over
    chunks of at most `chunk` patterns, each chunk reading the previous chunk's survivors
    (the method of REPORT-398.md 4.2). Returns {host: (global pattern index, map)} for the
    hosts that contain a pattern, and the survivors in input order."""
    import gzip
    workdir.mkdir(parents=True, exist_ok=True)
    patterns = g6_lines(patterns_g6)
    current = hosts
    removed: dict[bytes, tuple[int, list[int]]] = {}
    for start in range(0, len(patterns), chunk):
        part = workdir / f"patterns-{start}.g6"
        write_lines(part, patterns[start:start + chunk])
        surv = workdir / f"survivors-{start}.g6"
        wit = workdir / f"witness-{start}.tsv.gz"
        cmd = ["nice", "-n", "15", str(MATCHER32), "--patterns", str(part), "--survivors", str(surv),
               "--witness", str(wit)]
        with open(current, "rb") as stdin:
            p = subprocess.run(cmd, stdin=stdin, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"matcher32 failed ({p.returncode}) on chunk {start}: {p.stderr}")
        with gzip.open(wit, "rb") as f:
            for row in f:
                row = row.rstrip(b"\n")
                if row:
                    host, idx, mp = row.split(b"\t")
                    removed[host] = (start + int(idx), [int(x) for x in mp.split(b",")])
        current = surv
    return {"removed": removed, "survivors": g6_lines(current)}


def witness_ok(host: bytes, pattern_edges, mp: list[int]) -> bool:
    """Injective, in range, edge-preserving: the whole of an independent witness check."""
    n, host_edges = decode_g6(host)
    pn = max(max(e) for e in pattern_edges) + 1
    if len(mp) != pn or len(set(mp)) != pn or any(not (0 <= v < n) for v in mp):
        return False
    return all(tuple(sorted((mp[a], mp[b]))) in host_edges for a, b in pattern_edges)


def dump(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True)


def log(*parts) -> None:
    print(*parts, flush=True)
    sys.stdout.flush()
