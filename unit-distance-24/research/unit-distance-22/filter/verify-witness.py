#!/usr/bin/env python3
"""Independent syntactic verifier for one udfilter JSON certificate.

-s 398 (or --forbidden-set 398) reads "forbidden" witnesses against data/forbidden-398.json, which
must have its pinned sha256 (exit 2 otherwise); the default, set 74, reads data/forbidden-74.json
exactly as before. Exit 0: the witness is valid; 1: it is not; 2: usage or data error."""
import hashlib
import json
import sys
from pathlib import Path

FORBIDDEN_398_SHA256 = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"

def graph6(s):
    s = s.strip().removeprefix(">>graph6<<")
    n = ord(s[0]) - 63
    bits = ''.join(f'{ord(c)-63:06b}' for c in s[1:])
    a = [set() for _ in range(n)]
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == '1':
                a[i].add(j); a[j].add(i)
            k += 1
    return a

def main():
    argv = sys.argv[1:]
    forbidden_set = "74"
    for flag in ("-s", "--forbidden-set"):
        while flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                argv = []
                break
            forbidden_set = argv[i + 1]
            del argv[i:i + 2]
    if forbidden_set not in ("74", "398") or len(argv) not in (1, 2):
        print("usage: verify-witness.py [-s 74|398] GRAPH6 [WITNESS_JSON]", file=sys.stderr)
        return 2
    g6 = Path(argv[0]).read_text().splitlines()[0] if Path(argv[0]).is_file() else argv[0]
    line = sys.stdin.read() if len(argv) == 1 else argv[1]
    cert = json.loads(line)
    g = graph6(g6)
    w = cert.get("witness")
    if cert.get("verdict") not in ("forbidden", "tu") or not isinstance(w, dict): return 1
    name = ("tu-gadgets.json" if cert["verdict"] == "tu" else
            "forbidden-398.json" if forbidden_set == "398" else "forbidden-74.json")
    raw = (Path(__file__).parent.parent / "data" / name).read_bytes()
    if name == "forbidden-398.json" and hashlib.sha256(raw).hexdigest() != FORBIDDEN_398_SHA256:
        print("verify-witness.py: data/forbidden-398.json is not the pinned file", file=sys.stderr)
        return 2
    data = json.loads(raw)
    if not isinstance(w.get("index"), int) or w["index"] < 0 or w["index"] >= len(data): return 1
    pat = data[w["index"]]
    if cert["verdict"] == "forbidden":
        pat = {"n": max(max(e) for e in pat) + 1, "edges": pat}
    mp = w.get("map")
    if not isinstance(mp, list) or len(mp) != pat["n"] or len(set(mp)) != len(mp): return 1
    if any(not isinstance(v, int) or v < 0 or v >= len(g) for v in mp): return 1
    if any(b not in g[a] for a, b in ((mp[x], mp[y]) for x, y in pat["edges"])): return 1
    if cert["verdict"] == "tu":
        pair = w.get("pair")
        if pair != pat["pair"] or len(pair) != 2 or mp[pair[1]] in g[mp[pair[0]]]: return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
