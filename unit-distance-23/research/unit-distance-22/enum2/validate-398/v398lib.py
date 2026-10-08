"""Shared helpers for enum2's Mode-398 validation (enum2/validate-398).

Nothing here decides a verdict: it locates files, hashes them, runs the production
binary, reads graph6 and compares sets.  Each script states its own pass condition
and its own red controls.  Nothing here reads or ports udenum.c or udfilter code:
udenum is only RUN, as the production enumerator under test.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENUM2_DIR = HERE.parent
UD = ENUM2_DIR.parent
DATA = UD / "data"
sys.path.insert(0, str(ENUM2_DIR))
import enum2  # noqa: E402

UDENUM = UD / "enum" / "udenum"                  # the Mode-398 production binary
UDENUM_SHA256 = "a99b130ab5ad0386265c429b78cf3c4a4c708e1d5dd6e222bec14a4596c16a84"
F74 = DATA / "forbidden-74.json"
F398 = DATA / "forbidden-398.json"
REPO_DAG22 = UD / "enum" / "out-22" / "dag-22-61"
REPO_SUP = UD / "enum" / "out-sup" / "dag-18-46"
# the original u(22) run directory on this machine (read only): every shard and parent file
ORIG_DAG_F12 = Path("<repo>/research/unit-distance-22/enum/out-22/dag-22-61-f12")
SCRATCH = Path(os.environ.get("ENUM2_SCRATCH",
                              "<scratch>/scratchpad/v398"))
RUNS = HERE / "runs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_records(path: Path) -> list[str]:
    """udenum's record model: skip blank lines and '>>graph6<<' headers."""
    out = []
    with Path(path).open("r", encoding="ascii") as stream:
        for line in stream:
            s = line.rstrip("\r\n")
            if not s or s.startswith(">>graph6<<"):
                continue
            out.append(s)
    return out


def write_records(path: Path, records) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(r + "\n" for r in records), encoding="ascii")


def run_udenum(parents: Path, n: int, m: int, out: Path, forbidden_set: str = "398",
               extra: tuple[str, ...] = (), expect_ok: bool = True) -> dict:
    """Run the production udenum on a whole parent file; return its stderr stats plus times."""
    if sha256(UDENUM) != UDENUM_SHA256:
        raise SystemExit(f"{UDENUM} is not the pinned Mode-398 binary")
    forbidden = F398 if forbidden_set == "398" else F74
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["nice", "-n", "15", str(UDENUM), "--parents", str(parents), "--forbidden", str(forbidden),
           "--n", str(n), "--m", str(m), "--output", str(out),
           "--manifest", str(out.with_suffix(".manifest.json")), "--shard-id", out.stem,
           "--overwrite", "--forbidden-set", forbidden_set, *extra]
    t0 = time.monotonic()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    wall = time.monotonic() - t0
    if expect_ok and p.returncode != 0:
        raise SystemExit(f"udenum failed ({p.returncode}): {p.stderr.strip()}")
    stats: dict = {"returncode": p.returncode, "wall_seconds": round(wall, 3)}
    for line in p.stderr.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                stats.update(json.loads(line))
            except json.JSONDecodeError:
                pass
    if p.returncode != 0:
        stats["stderr"] = p.stderr.strip()
    return stats


def recover_parent(code: str) -> str:
    """Canonical graph6 of a canonical child minus its first minimum-degree vertex.

    The child record is canonical, so the canonical labelling of it is an
    automorphism and the first minimum-degree vertex in canonical order is an
    automorphic image of the smallest-index minimum-degree vertex; deleting
    either gives isomorphic graphs (the CROSSCHECK.md rule)."""
    g = enum2.graph6_decode(code)
    degrees = [g.degree(v) for v in range(g.n)]
    w = degrees.index(min(degrees))
    keep = [v for v in range(g.n) if v != w]
    adj = []
    for v in keep:
        row = 0
        for j, u in enumerate(keep):
            if (g.adj[v] >> u) & 1:
                row |= 1 << j
        adj.append(row)
    return enum2.canonical_g6(enum2.Graph(tuple(adj)))


def compare(production: list[str], enum2_records: list[str]) -> dict:
    """The comparison of record lists.  identical means: equal SETS, and no
    duplicate line in the production list.  (Counts and one-sided inclusion
    are reported too, but they are the WRONG test and never decide.)"""
    ps, es = set(production), set(enum2_records)
    only_p = sorted(ps - es)
    only_e = sorted(es - ps)
    return {"production": len(production), "production_distinct": len(ps),
            "enum2_raw": len(enum2_records), "enum2": len(es),
            "only_production": len(only_p), "only_enum2": len(only_e),
            "only_production_first": only_p[:10], "only_enum2_first": only_e[:10],
            "equal_counts": len(production) == len(es),
            "enum2_subset_of_production": es <= ps,
            "identical": not only_p and not only_e and len(production) == len(ps)}


def dump(path: Path, value) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=1, sort_keys=False) + "\n")


def software() -> dict:
    return {"enum2.py": sha256(ENUM2_DIR / "enum2.py"), "udenum": sha256(UDENUM),
            "forbidden-74.json": sha256(F74), "forbidden-398.json": sha256(F398),
            "python": sys.version.split()[0], "pynauty": getattr(enum2.pynauty, "__version__", "?")}
