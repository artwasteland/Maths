"""Shared helpers for the forbidden-398 validation scripts (enum/test-398).

Nothing here decides a verdict: it runs binaries, hashes files and reads graph6.  Each script
states its own pass condition and its own red controls.
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
TU = DATA / "tu-gadgets.json"

NEW_UDENUM = ENUM / "udenum"
OLD_UDENUM = HERE / "old" / "enum" / "udenum"
NEW_UDFILTER = UD / "filter" / "udfilter"
OLD_UDFILTER = HERE / "old" / "filter" / "udfilter"
MATCHER32 = HERE / "bin" / "matcher32"
MATCHER10 = HERE / "bin" / "matcher10"

# The production binary of the u(22) run, hashed in every shard manifest; the old sources in
# old/ rebuild to exactly this file.
PRODUCTION_UDENUM_SHA256 = "94a85d333d753ec2f518e62ef6d2f855d56b22dc6f3b890f53aa9575680f57b4"
PRODUCTION_UDFILTER_SHA256 = "d4ccae3ff45dcd2d45a64087bebb9519e901110c07fabd1661995b148cee600a"
F74_SHA256 = "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a"
F398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
F398_G6_SHA256 = "91d5810c4d7b02d97afec7dfe2a2a5629f2075439100aa8eae6b60dca4ff4381"

SCRATCH = Path(os.environ.get("T398_SCRATCH", "/tmp/t398-work"))

STAT_COUNTERS = ("parents_seen", "parents_processed", "parents_degree_skipped", "bad_sets",
                 "neighbourhoods", "neighbourhood_orbit_reps", "neighbourhoods_bad",
                 "child_orbit_rejected", "children_written")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def g6_lines(path: Path) -> list[bytes]:
    return [x for x in Path(path).read_bytes().split(b"\n") if x]


def write_lines(path: Path, lines) -> None:
    Path(path).write_bytes(b"".join(x + b"\n" for x in lines))


def g6_order_size(line: bytes) -> tuple[int, int]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    return n, bits[: n * (n - 1) // 2].count("1")


def run_udenum(binary: Path, parents: Path, n: int, m: int, out: Path, extra=(), forbidden=F74,
               expect_ok=True) -> dict:
    """Run udenum on a whole parent file; return its stderr stats JSON plus wall time."""
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = out.with_suffix(".manifest.json")
    cmd = ["nice", "-n", "10", str(binary), "--parents", str(parents), "--forbidden", str(forbidden),
           "--n", str(n), "--m", str(m), "--output", str(out), "--manifest", str(manifest),
           "--shard-id", out.stem, "--overwrite", *extra]
    t0 = time.monotonic()
    p = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.monotonic() - t0
    if not expect_ok:
        return {"returncode": p.returncode, "stderr": p.stderr.strip()}
    if p.returncode != 0:
        raise RuntimeError(f"udenum failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr}")
    stats = json.loads(p.stderr.strip().splitlines()[-1])
    stats["outer_wall_seconds"] = wall
    stats["manifest"] = json.loads(manifest.read_text())
    return stats


def run_matcher(binary: Path, patterns_g6: Path, hosts: Path, workdir: Path, chunk: int = 128,
                witnesses: bool = True) -> dict:
    """Chain GP-10's matcher over chunks of at most `chunk` patterns.

    Each chunk reads the previous chunk's survivors.  Returns the set of hosts removed (with the
    first witness found: global pattern index and map) and the final survivor list, in input
    order.  witnesses=False skips the witness file (for streams where millions of hosts are
    removed): "removed" is then None and only the survivors are returned."""
    import gzip
    workdir.mkdir(parents=True, exist_ok=True)
    patterns = g6_lines(patterns_g6)
    current = hosts
    removed: dict[bytes, tuple[int, list[int]]] | None = {} if witnesses else None
    for start in range(0, len(patterns), chunk):
        part = workdir / f"patterns-{start}.g6"
        write_lines(part, patterns[start:start + chunk])
        surv = workdir / f"survivors-{start}.g6"
        wit = workdir / f"witness-{start}.tsv.gz"
        cmd = ["nice", "-n", "10", str(binary), "--patterns", str(part), "--survivors", str(surv)]
        if witnesses:
            cmd += ["--witness", str(wit)]
        with open(current, "rb") as stdin:
            p = subprocess.run(cmd, stdin=stdin, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"matcher failed ({p.returncode}) on chunk {start}: {p.stderr}")
        if witnesses:
            with gzip.open(wit, "rb") as f:
                for row in f:
                    row = row.rstrip(b"\n")
                    if not row:
                        continue
                    host, idx, mp = row.split(b"\t")
                    removed[host] = (start + int(idx), [int(x) for x in mp.split(b",")])
        current = surv
    return {"removed": removed, "survivors": g6_lines(current)}


def decode_g6(line: bytes) -> tuple[int, set[frozenset]]:
    n = line[0] - 63
    bits = "".join(f"{c - 63:06b}" for c in line[1:])
    edges = set()
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                edges.add(frozenset((i, j)))
            k += 1
    return n, edges


def witness_ok(host_line: bytes, pattern_edges, mp: list[int]) -> bool:
    """Injective, in range, edge-preserving: the whole of an independent witness check."""
    n, host_edges = decode_g6(host_line)
    pn = max(max(e) for e in pattern_edges) + 1
    if len(mp) != pn or len(set(mp)) != pn or any(not (0 <= v < n) for v in mp):
        return False
    return all(frozenset((mp[a], mp[b])) in host_edges for a, b in pattern_edges)
