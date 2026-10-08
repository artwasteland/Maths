#!/usr/bin/env python3
"""Build data/forbidden-398.json and data/forbidden-398.g6.

The 398 = Globus and Parshall's 74 minimal forbidden graphs on at most 9 vertices, in the
order and labelling of data/forbidden-74.json (copied verbatim), followed by the 324 minimal
forbidden graphs on 10 vertices certified by GP-10, in the order of L10.g6, each written as the
edge list of its graph6 labelling (pairs [i, j] with i < j, sorted).

The .g6 file is data/forbidden-74.g6 followed by L10.g6, byte for byte.

The JSON is written with json.dumps defaults, which reproduces forbidden-74.json exactly
(checked below), so the new file has exactly the old file's format.

This script trusts nothing it does not check: it pins the sha256 of each input, refuses to
overwrite an output whose bytes differ, and prints the output hashes.  The independent check of
the result is check-forbidden-398.py (networkx), not this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent.parent                     # research/unit-distance-22
REPO = UD.parent.parent                     # repository root
DATA = UD / "data"

PINNED = {
    "forbidden-74.json": "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
    "forbidden-74.g6": "97c12af4b429004b602c1fc8a3bcc7110ab90a46b724bc0c892429812138720e",
    "L10.g6": "a899e36cec0f135f253e0c9942d2fecd29280da44189a01d00752e8a5af971b8",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def graph6_edges(line: str) -> tuple[int, list[list[int]]]:
    """Decode a graph6 string of order <= 62 into (n, sorted edge list)."""
    n = ord(line[0]) - 63
    if not 0 <= n <= 62:
        raise SystemExit(f"unsupported graph6 order in {line!r}")
    bits = "".join(f"{ord(c) - 63:06b}" for c in line[1:])
    need = n * (n - 1) // 2
    if len(bits) < need or len(line) - 1 != (need + 5) // 6:
        raise SystemExit(f"graph6 length mismatch in {line!r}")
    if any(b == "1" for b in bits[need:]):
        raise SystemExit(f"graph6 padding bits set in {line!r}")
    edges = []
    k = 0
    for j in range(1, n):          # graph6: upper triangle column by column
        for i in range(j):
            if bits[k] == "1":
                edges.append([i, j])
            k += 1
    edges.sort()
    return n, edges


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--l10", type=Path,
                    default=REPO / "research/gp-10/runs/B10-final-2026-09-25/L10.g6")
    ap.add_argument("--out-dir", type=Path, default=DATA)
    a = ap.parse_args()

    f74_json = (DATA / "forbidden-74.json").read_bytes()
    f74_g6 = (DATA / "forbidden-74.g6").read_bytes()
    l10 = a.l10.read_bytes()
    for name, data in (("forbidden-74.json", f74_json), ("forbidden-74.g6", f74_g6), ("L10.g6", l10)):
        got = sha256_bytes(data)
        if got != PINNED[name]:
            raise SystemExit(f"input {name} has sha256 {got}, pinned {PINNED[name]}")

    list74 = json.loads(f74_json)
    if json.dumps(list74).encode() != f74_json:
        raise SystemExit("json.dumps does not reproduce forbidden-74.json; format assumption broken")
    if len(list74) != 74:
        raise SystemExit("forbidden-74.json does not hold 74 graphs")
    if not f74_g6.endswith(b"\n") or len(f74_g6.splitlines()) != 74:
        raise SystemExit("forbidden-74.g6 is not 74 newline-terminated lines")
    if not l10.endswith(b"\n"):
        raise SystemExit("L10.g6 does not end with a newline")
    lines10 = l10.decode("ascii").splitlines()
    if len(lines10) != 324 or len(set(lines10)) != 324:
        raise SystemExit("L10.g6 is not 324 distinct lines")

    list324 = []
    for line in lines10:
        n, edges = graph6_edges(line)
        if n != 10:
            raise SystemExit(f"L10 member {line} has order {n}, not 10")
        if max(max(e) for e in edges) != 9:
            raise SystemExit(f"L10 member {line} has an isolated vertex 9")
        list324.append(edges)

    out_json = json.dumps(list74 + list324).encode()
    out_g6 = f74_g6 + l10
    # The first 74 entries are the old file's bytes up to its closing bracket.
    if not out_json.startswith(f74_json[:-1] + b", "):
        raise SystemExit("forbidden-398.json does not start with forbidden-74.json's entries")

    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("forbidden-398.json", out_json), ("forbidden-398.g6", out_g6)):
        path = a.out_dir / name
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f"{path} exists with different bytes; refusing to overwrite")
        if not path.exists():
            path.write_bytes(data)
        print(f"{sha256_bytes(data)}  {name}  ({len(data)} bytes)")
    print(f"inputs: forbidden-74.json {PINNED['forbidden-74.json']}, forbidden-74.g6 "
          f"{PINNED['forbidden-74.g6']}, L10.g6 {PINNED['L10.g6']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
