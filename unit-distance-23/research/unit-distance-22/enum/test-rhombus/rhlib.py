"""Shared helpers for the rhombus prover's tests (enum/test-rhombus). Standard library only.

Nothing here decides a verdict: it locates files, runs the prover and parses its output. Each
test script states its own pass condition and its own red controls. The certificate replay used
by the tests is dev_replay_rhombus.py (a DEV AID, not the checker)."""
from __future__ import annotations

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
FILTER = UD / "filter"
UDRHOMBUS = FILTER / "udrhombus"
UDFILTER = FILTER / "udfilter"
TU_GADGETS = DATA / "tu-gadgets.json"
KNOWN = UD / "sources" / "amp" / "anc" / "graph6.txt"
LABELG = "/usr/bin/nauty-labelg"
SCRATCH = Path(os.environ.get("RHOMBUS_SCRATCH", str(HERE / "scratch")))
RUNS = HERE / "runs"

sys.path.insert(0, str(HERE))
from dev_replay_rhombus import Reject, check_rhombus_witness, decode_g6  # noqa: E402


def encode_g6(n: int, edges) -> str:
    es = {tuple(sorted(e)) for e in edges}
    bits = [1 if (i, j) in es else 0 for j in range(1, n) for i in range(j)]
    while len(bits) % 6:
        bits.append(0)
    return chr(n + 63) + "".join(chr(63 + int("".join(map(str, bits[k:k + 6])), 2))
                                 for k in range(0, len(bits), 6))


def g6_lines(path: Path) -> list[str]:
    return [x for x in Path(path).read_text(encoding="ascii").split("\n") if x]


def write_lines(path: Path, lines) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(x + "\n" for x in lines), encoding="ascii")


def run_prover(lines: list[str], binary: Path = UDRHOMBUS, args: list[str] | None = None,
               nice: bool = True) -> tuple[list[dict], dict, bytes]:
    """Run udrhombus on the given graph6 lines. Returns (records, stats, raw stdout)."""
    cmd = (["nice", "-n", "10"] if nice else []) + [str(binary), *(args or [])]
    p = subprocess.run(cmd, input="".join(x + "\n" for x in lines).encode("ascii"), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"udrhombus exited {p.returncode}: {p.stderr.decode()[-500:]}")
    out = p.stdout.split(b"\n")
    if out[-1] != b"":
        raise RuntimeError("udrhombus output does not end with a newline")
    records = [json.loads(x) for x in out[:-1]]
    if len(records) != len(lines):
        raise RuntimeError(f"udrhombus wrote {len(records)} records for {len(lines)} graphs")
    err = p.stderr.decode().strip().splitlines()
    stats = json.loads(err[-1])["udrhombus_stats"] if err else {}
    return records, stats, p.stdout


def replay(code: str, record: dict) -> tuple[bool, str]:
    """(True, verdict) if the dev replay accepts a prover record for graph `code`, else (False, reason)."""
    try:
        n, edges = decode_g6(code)
        return True, check_rhombus_witness(n, edges, record.get("verdict"), record.get("witness"), code)
    except Reject as exc:
        return False, str(exc)


def canonical(lines: list[str]) -> list[str]:
    if not lines:
        return []
    p = subprocess.run([LABELG, "-q"], input="".join(x + "\n" for x in lines), text=True,
                       capture_output=True, check=True)
    out = [x for x in p.stdout.split("\n") if x]
    if len(out) != len(lines):
        raise RuntimeError("labelg returned a different number of graphs")
    return out


def known_graphs() -> list[str]:
    return g6_lines(KNOWN)


def gadgets() -> list[dict]:
    return json.loads(TU_GADGETS.read_text())


def log(*parts) -> None:
    print(*parts, flush=True)
