#!/usr/bin/env python3
"""Small deterministic checks for the C filter and its certificate verifier."""
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable
FILTER = HERE / "udfilter"
VERIFY = HERE / "verify-witness.py"
F = json.loads((HERE.parent / "data/forbidden-74.json").read_text())
T = json.loads((HERE.parent / "data/tu-gadgets.json").read_text())

def g6(n, edges):
    bits = []
    es = {tuple(sorted(e)) for e in edges}
    for j in range(1, n):
        for i in range(j): bits.append(int((i, j) in es))
    while len(bits) % 6: bits.append(0)
    return chr(n + 63) + ''.join(chr(63 + int(''.join(map(str, bits[k:k+6])), 2))
                                   for k in range(0, len(bits), 6))

def run(s):
    p = subprocess.run([str(FILTER)], input=s + "\n", text=True, capture_output=True, check=True)
    return json.loads(p.stdout)

def verify(g, cert, expect=True):
    p = subprocess.run([PYTHON, str(VERIFY), g, json.dumps(cert)], capture_output=True)
    assert (p.returncode == 0) == expect, p.stderr.decode()

def host_with(edges, n=22, extra=False, omit=None):
    es = {tuple(sorted(e)) for e in edges}
    omit = tuple(sorted(omit)) if omit is not None else None
    if extra:
        rng = random.Random(20260905 + len(edges))
        for x in range(9, n):
            if x + 1 < n and rng.randrange(3) == 0:
                es.add((x, x + 1))
    if omit is not None: es.discard(omit)
    return g6(n, es)

def main():
    known = (HERE.parent / "sources/amp/anc/graph6.txt").read_text().splitlines()
    out = [run(x) for x in known]
    assert len(out) == 56 and all(x["verdict"] == "pass" for x in out)
    print("known_56_pass=56")

    checked = 0
    for edges in F:
        n = max(max(e) for e in edges) + 1
        cert = run(host_with(edges, extra=True))
        assert cert["verdict"] == "forbidden"
        verify(cert["g6"], cert)
        checked += 1
    print(f"forbidden_planted_verified={checked}")

    removed = 0
    present = []
    for i, item in enumerate(T):
        edges = item["edges"]
        g_removed = host_with(edges, omit=item["pair"])
        cert = run(g_removed)
        assert cert["verdict"] == "tu"
        verify(cert["g6"], cert)
        removed += 1
        g_present = host_with(edges + [item["pair"]])
        present_cert = run(g_present)
        if present_cert["verdict"] == "tu": verify(present_cert["g6"], present_cert)
        present.append((i, present_cert["verdict"], present_cert.get("witness", {}).get("index")))
    print(f"tu_pair_removed_verified={removed}")
    print("tu_pair_present_results=" + json.dumps(present, separators=(",", ":")))
    assert all(v != "tu" or j != i for i, v, j in present)

    tu_line = next(run(host_with(T[0]["edges"], omit=T[0]["pair"]))
                   for _ in [0])
    bad = json.loads(json.dumps(tu_line))
    bad["witness"]["map"][0] = bad["witness"]["map"][1]
    verify(bad["g6"], bad, expect=False)
    print("corrupt_witness_rejected=1")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
