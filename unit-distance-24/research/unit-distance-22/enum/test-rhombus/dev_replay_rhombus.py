#!/usr/bin/env python3
"""DEV AID ONLY. This is NOT the checker of the rhombus rule, and nothing may rest on it.

The prover builder's private replay of rhombus certificates, written from
research/unit-distance-23/RHOMBUS-SPEC.md (Sections 2 and 3) for the builder's own tests while
the real checker, check/udcheck_rhombus.py, is written blind by another agent. It lives in the
test directory on purpose and must never be copied to check/.

Where it runs:
  - the unit, B10, agreement and mutant tests of enum/test-rhombus import check_rhombus_witness;
  - the end-to-end tests substitute it for check/udcheck_rhombus.py through the environment
    variable PRUNE_UDCHECK_RHOMBUS, which prune.py reads as the default of --udcheck-rhombus;
    the prune manifest then records this file's path and sha256, so such a run is marked.

Command line (the checker contract of spec Section 3):
  dev_replay_rhombus.py [--expect-n N] [--expect-m M] [--allow-any-size] [--graphs LIST]
                        [--unknown-file UNKNOWN.g6] [--data-dir DIR] [--labelg PATH]
                        [--forbidden-set 74|398] CERTIFICATES.jsonl
It checks the file's structure (JSON lines, no duplicate object keys, exact top-level keys, strict
graph6, the expected order and size, no duplicate record, and with --graphs the exact g6 sequence),
checks every rhombus record against Section 2 in exact integers, checks the canonical form of the
rhombus records' graph6 strings with nauty-labelg, and hands every other record to the pinned
kernel (check/udcheck.py for set 74, check/udcheck398.py for set 398) as a subprocess, on a derived
certificate file and graph list holding exactly those records in order, with the same unknown
file. Prints one line
  ACCEPT certificates records=R forbidden=F tu=T embedded=E refuted=X unknown=U proof_nodes=P
         rhombus_tu=RT rhombus_refuted=RX
(tu and refuted include the rhombus ones) and exits 0, or prints REJECT: <reason> on stderr and
exits 1.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
UD = HERE.parent.parent                       # research/unit-distance-22
KERNELS = {74: UD / "check" / "udcheck.py", 398: UD / "check" / "udcheck398.py"}
LIMIT = 1 << 62
MAX_CYCLES = 4096


class Reject(Exception):
    pass


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Reject(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def decode_g6(code: object) -> tuple[int, set[tuple[int, int]]]:
    """Strict short-form graph6: order below 63, exact length, zero padding."""
    if not isinstance(code, str) or not code:
        raise Reject(f"g6 is not a non-empty string: {code!r}")
    vals = [ord(ch) - 63 for ch in code]
    if any(v < 0 or v > 63 for v in vals):
        raise Reject(f"g6 has a character outside the graph6 alphabet: {code!r}")
    n = vals[0]
    if n > 62:
        raise Reject(f"g6 long form is not supported: {code!r}")
    bits = n * (n - 1) // 2
    if len(vals) != 1 + (bits + 5) // 6:
        raise Reject(f"g6 has the wrong length: {code!r}")
    if bits % 6 and vals[-1] & ((1 << (6 - bits % 6)) - 1):
        raise Reject(f"g6 padding is not zero: {code!r}")
    edges = set()
    k = 0
    for w in range(1, n):
        for u in range(w):
            if vals[1 + k // 6] & (1 << (5 - k % 6)):
                edges.add((u, w))
            k += 1
    return n, edges


def is_int(x: object) -> bool:
    return type(x) is int                     # JSON integers only: never bool, never float


def vertex(x: object, n: int, where: str) -> int:
    if not is_int(x) or not 0 <= x < n:
        raise Reject(f"{where}: {x!r} is not a JSON integer in [0, {n})")
    return x


def check_rhombus_witness(n: int, edges: set[tuple[int, int]], verdict: object, witness: object,
                          where: str = "record") -> str:
    """Spec Section 2, rules 1 to 6. Returns the verdict; raises Reject."""
    def edge(a: int, b: int) -> bool:
        return (min(a, b), max(a, b)) in edges

    if verdict not in ("refuted", "tu"):
        raise Reject(f"{where}: a rhombus witness with verdict {verdict!r}")
    if not isinstance(witness, dict) or set(witness) != {"rhombus"}:
        raise Reject(f"{where}: witness must have exactly the key rhombus")
    rh = witness["rhombus"]
    want = {"cycles", "coefficients", "scale", "pair"} | ({"edge"} if verdict == "tu" else set())
    if not isinstance(rh, dict) or set(rh) != want:
        raise Reject(f"{where}: rhombus keys {sorted(rh) if isinstance(rh, dict) else rh!r} are not {sorted(want)}")
    cycles = rh["cycles"]
    if not isinstance(cycles, list) or not 1 <= len(cycles) <= MAX_CYCLES:
        raise Reject(f"{where}: cycles must be a list of 1 to {MAX_CYCLES} entries")
    parsed = []
    for j, c in enumerate(cycles):
        if not isinstance(c, list) or len(c) != 4:
            raise Reject(f"{where}: cycle {j} is not a list of 4 vertices")
        u, v, w, x = (vertex(y, n, f"{where}: cycle {j}") for y in c)
        if len({u, v, w, x}) != 4:
            raise Reject(f"{where}: cycle {j} {c} has a repeated vertex")
        for s, t in ((u, v), (v, w), (w, x), (x, u)):
            if not edge(s, t):
                raise Reject(f"{where}: cycle {j} {c}: {s}{t} is not an edge")
        parsed.append((u, v, w, x))
    coefficients = rh["coefficients"]
    if not isinstance(coefficients, list) or len(coefficients) != len(cycles):
        raise Reject(f"{where}: coefficients must be a list as long as cycles")
    for j, l in enumerate(coefficients):
        if not is_int(l) or l == 0 or abs(l) >= LIMIT:
            raise Reject(f"{where}: coefficient {j} = {l!r} is not a nonzero JSON integer below 2^62")
    s = rh["scale"]
    if not is_int(s) or s == 0 or abs(s) >= LIMIT:
        raise Reject(f"{where}: scale {s!r} is not a nonzero JSON integer below 2^62")
    pair = rh["pair"]
    if not isinstance(pair, list) or len(pair) != 2:
        raise Reject(f"{where}: pair is not two vertices")
    a, b = (vertex(y, n, f"{where}: pair") for y in pair)
    if a == b:
        raise Reject(f"{where}: pair {pair} is not two distinct vertices")
    target = [0] * n
    target[a] += s
    target[b] -= s
    if verdict == "tu":
        if edge(a, b):
            raise Reject(f"{where}: pair {pair} is an edge")
        e = rh["edge"]
        if not isinstance(e, list) or len(e) != 2:
            raise Reject(f"{where}: edge is not two vertices")
        p, q = (vertex(y, n, f"{where}: edge") for y in e)
        if p == q or not edge(p, q):
            raise Reject(f"{where}: edge {e} is not an edge of the graph")
        target[p] -= s
        target[q] += s
    total = [0] * n
    for (u, v, w, x), l in zip(parsed, coefficients):
        total[u] += l
        total[v] -= l
        total[w] += l
        total[x] -= l
    if total != target:
        raise Reject(f"{where}: sum of l_j r(C_j) is {total}, not s times the target {target}")
    return verdict


def check_rhombus_record(record: dict, where: str = "record") -> str:
    n, edges = decode_g6(record.get("g6"))
    return check_rhombus_witness(n, edges, record.get("verdict"), record.get("witness"), where)


def read_list(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise Reject(f"{path}: missing final newline")
    lines = raw.decode("ascii").split("\n")[:-1] if raw else []
    if any(not x for x in lines):
        raise Reject(f"{path}: blank graph6 record")
    return lines


def canonical_check(codes: list[str], labelg: str) -> None:
    for start in range(0, len(codes), 200000):
        chunk = codes[start:start + 200000]
        p = subprocess.run([labelg, "-q"], input="".join(c + "\n" for c in chunk), text=True,
                           capture_output=True)
        out = p.stdout.split("\n")[:-1] if p.stdout else []
        if p.returncode != 0 or len(out) != len(chunk):
            raise Reject(f"nauty-labelg failed: {p.stderr.strip()[:200]}")
        for c, d in zip(chunk, out):
            if c != d:
                raise Reject(f"graph6 record {c} is not in nauty canonical form ({d})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("certificates", type=Path)
    ap.add_argument("--graphs", type=Path)
    ap.add_argument("--unknown-file", type=Path)
    ap.add_argument("--data-dir", type=Path, default=UD / "data")
    ap.add_argument("--expect-n", type=int, default=22)
    ap.add_argument("--expect-m", type=int, default=61)
    ap.add_argument("--allow-any-size", action="store_true")
    ap.add_argument("--labelg", default="/usr/bin/nauty-labelg")
    ap.add_argument("--forbidden-set", type=int, choices=(74, 398), default=74)
    a = ap.parse_args(argv)
    try:
        counts = replay(a)
    except (Reject, OSError, UnicodeError) as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 1
    print("ACCEPT certificates " + " ".join(f"{k}={counts[k]}" for k in (
        "records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes",
        "rhombus_tu", "rhombus_refuted")))
    return 0


def replay(a) -> dict:
    expect_n = None if a.allow_any_size else a.expect_n
    expect_m = None if a.allow_any_size else a.expect_m
    unknown_file = a.unknown_file if a.unknown_file is not None else a.certificates.parent / "UNKNOWN.g6"
    codes: list[str] = []
    seen: set[str] = set()
    rhombus_codes: list[str] = []
    counts = {"rhombus_tu": 0, "rhombus_refuted": 0}
    with tempfile.TemporaryDirectory(prefix="dev-replay-") as tmp:
        derived_certs = Path(tmp) / "kernel.certs.jsonl"
        derived_list = Path(tmp) / "kernel.g6"
        kernel_records = 0
        with a.certificates.open("r", encoding="utf-8") as stream, \
                derived_certs.open("w", encoding="utf-8") as dc, derived_list.open("w", encoding="ascii") as dl:
            for lineno, line in enumerate(stream, 1):
                where = f"{a.certificates}:{lineno}"
                if not line.endswith("\n") or not line.strip():
                    raise Reject(f"{where}: missing newline or blank record")
                try:
                    record = json.loads(line, object_pairs_hook=no_duplicates)
                except json.JSONDecodeError as exc:
                    raise Reject(f"{where}: invalid JSON: {exc}")
                if not isinstance(record, dict) or not {"g6", "verdict"} <= set(record) <= {"g6", "verdict", "witness"}:
                    raise Reject(f"{where}: top-level keys must be g6, verdict and optionally witness")
                code = record["g6"]
                n, edges = decode_g6(code)
                if expect_n is not None and n != expect_n:
                    raise Reject(f"{where}: expected {expect_n} vertices, got {n}")
                if expect_m is not None and len(edges) != expect_m:
                    raise Reject(f"{where}: expected {expect_m} edges, got {len(edges)}")
                if code in seen:
                    raise Reject(f"{where}: duplicate graph6 record")
                seen.add(code)
                codes.append(code)
                witness = record.get("witness")
                if isinstance(witness, dict) and "rhombus" in witness:
                    verdict = check_rhombus_witness(n, edges, record["verdict"], witness, where)
                    counts["rhombus_" + verdict] += 1
                    rhombus_codes.append(code)
                else:
                    dc.write(line)
                    dl.write(code + "\n")
                    kernel_records += 1
        if a.graphs is not None and read_list(a.graphs) != codes:
            raise Reject("certificate graph6 records do not exactly equal the supplied graph list in order")
        canonical_check(rhombus_codes, a.labelg)
        kernel = {k: 0 for k in ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes")}
        if kernel_records:
            cmd = [sys.executable, str(KERNELS[a.forbidden_set]), "--data-dir", str(a.data_dir),
                   "--labelg", a.labelg, "--graphs", str(derived_list), "--unknown-file", str(unknown_file)]
            cmd += ["--allow-any-size"] if a.allow_any_size else ["--expect-n", str(a.expect_n), "--expect-m", str(a.expect_m)]
            p = subprocess.run(cmd + [str(derived_certs)], capture_output=True, text=True)
            accept = [x for x in p.stdout.splitlines() if x.startswith("ACCEPT certificates")]
            if p.returncode != 0 or len(accept) != 1:
                raise Reject(f"kernel {KERNELS[a.forbidden_set].name}: {p.stderr.strip()[:300]}")
            for key, value in re.findall(r"(\w+)=(\d+)", accept[0]):
                kernel[key] = int(value)
            if kernel["records"] != kernel_records:
                raise Reject("kernel record count differs from the derived file")
        elif unknown_file.exists() and read_list(unknown_file):
            raise Reject("UNKNOWN file lists graphs but no record is unknown")
    return {"records": len(codes), "forbidden": kernel["forbidden"],
            "tu": kernel["tu"] + counts["rhombus_tu"], "embedded": kernel["embedded"],
            "refuted": kernel["refuted"] + counts["rhombus_refuted"], "unknown": kernel["unknown"],
            "proof_nodes": kernel["proof_nodes"], **counts}


if __name__ == "__main__":
    sys.exit(main())
