#!/usr/bin/env python3
"""Independent syntactic verifier for one udfilter JSON certificate."""
import json
import sys
from pathlib import Path

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
    if len(sys.argv) not in (2, 3):
        print("usage: verify-witness.py GRAPH6 [WITNESS_JSON]", file=sys.stderr)
        return 2
    g6 = Path(sys.argv[1]).read_text().splitlines()[0] if Path(sys.argv[1]).is_file() else sys.argv[1]
    line = sys.stdin.read() if len(sys.argv) == 2 else sys.argv[2]
    cert = json.loads(line)
    g = graph6(g6)
    w = cert.get("witness")
    if cert.get("verdict") not in ("forbidden", "tu") or not isinstance(w, dict): return 1
    data = json.loads((Path(__file__).parent.parent / "data" /
                       ("forbidden-74.json" if cert["verdict"] == "forbidden" else "tu-gadgets.json")).read_text())
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
