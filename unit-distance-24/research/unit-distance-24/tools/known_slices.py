#!/usr/bin/env python3
"""Where the known graphs must be: the slice of the (24,69) fleet that holds each eligible Engel graph.

usage: python known_slices.py --reach REACH_JSON [--prefix RUN_DIR] [--out FILE] [--self-test]
       (needs pynauty: ~/tools/pyenv-maths/bin/python)

Engel et al.'s configurations (research/unit-distance-22/sources/engel-dataset/engel-<n>-<m>.g6, canonical graph6 from
nauty-labelg) are each the unit-distance graph of its own points, so no sound rule prunes one or any of its
induced subgraphs. A graph G at a reach-table cell (n, m) with minimum degree d >= k(n, m) is ELIGIBLE. Its canonical parent
(udenum and enum2 delete the first vertex of minimum degree in nauty's canonical order) lies at (n-1, m-d), which the
L4 recursion admits with k <= max(0, d-1), and the parent's minimum degree is at least d-1: so it is eligible too, and
by induction every eligible graph is in the tree. Its slice is its level-12 ancestor's: run-dag2.py's slice_of, the
first 8 bytes of the sha256 of the ancestor's graph6, mod 1920.

This computes every eligible graph's chain of canonical ancestors down to the seed level, CHECKS the induction at every
step (each ancestor at a table cell with minimum degree >= its k; a failure is printed as a VIOLATION and the tool exits
1), and writes, per slice, the Engel graphs it must hold. With --prefix (a (24,69) run directory holding levels <= 12),
every level-12 ancestor must be in that run's 12-<m>.keep.g6: a completeness test of the shared prefix on the known
graphs. The slice function and the canonical deletion are this file's own code, so agreement with the fleet's receipts
is evidence for both.

--self-test first shows the checks can fail: a table whose k at one ancestor's cell is raised above that ancestor's
minimum degree must give a VIOLATION there, and a prefix with one ancestor removed must report it missing; then the
real run is repeated unchanged.
"""
import argparse, glob, hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

import pynauty
import known_graphs as known

def decode(g6: str) -> list[int]:
    """graph6 (n <= 62) to adjacency bitmasks."""
    n = ord(g6[0]) - 63
    bits = "".join(format(ord(c) - 63, "06b") for c in g6[1:])
    adj, k = [0] * n, 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                adj[i] |= 1 << j
                adj[j] |= 1 << i
            k += 1
    return adj


def encode(adj: list[int]) -> str:
    n = len(adj)
    bits = "".join("1" if adj[j] >> i & 1 else "0" for j in range(1, n) for i in range(j))
    bits += "0" * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(int(bits[k:k + 6], 2) + 63) for k in range(0, len(bits), 6))


def canon(adj: list[int]) -> tuple[list[int], list[int]]:
    """nauty's canonical order (old vertex at each canonical position) and the canonical adjacency."""
    n = len(adj)
    order = list(pynauty.canon_label(pynauty.Graph(n, adjacency_dict={
        v: [u for u in range(n) if adj[v] >> u & 1] for v in range(n)})))
    rank = [0] * n
    for pos, old in enumerate(order):
        rank[old] = pos
    out = [0] * n
    for old in range(n):
        for u in range(n):
            if adj[old] >> u & 1:
                out[rank[old]] |= 1 << rank[u]
    return order, out


def degrees(adj: list[int]) -> list[int]:
    return [a.bit_count() for a in adj]


def canonical_parent(adj: list[int]) -> tuple[list[int], int]:
    """The canonical parent (canonical adjacency) and the deleted vertex's degree: the first vertex of minimum
    degree in nauty's canonical order is deleted (udenum child_canonical_accept, enum2 canonical_child)."""
    order, _ = canon(adj)
    deg = degrees(adj)
    d = min(deg)
    v = next(x for x in order if deg[x] == d)
    keep = [u for u in range(len(adj)) if u != v]
    idx = {u: i for i, u in enumerate(keep)}
    sub = [0] * len(keep)
    for u in keep:
        for w in keep:
            if adj[u] >> w & 1:
                sub[idx[u]] |= 1 << idx[w]
    return canon(sub)[1], d


def slice_of(code: str, count: int) -> int:
    """run-dag2.py's slice_of, restated."""
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big") % count


def run(table: dict, seed_n: int, slice_level: int, count: int, prefix: dict | None, files: list) -> dict:
    eligible, by_slice, violations, missing = defaultdict(int), defaultdict(list), [], []
    for path in files:
        n, m = map(int, re.findall(r"engel-(\d+)-(\d+)\.g6$", path)[0])
        if m not in table.get(n, {}):
            continue
        for idx, line in enumerate(l.strip() for l in open(path) if l.strip()):
            adj = decode(line)
            if min(degrees(adj)) < table[n][m]:
                continue
            eligible[f"{n}-{m}"] += 1
            cur, cn, cm, anc = canon(adj)[1], n, m, None
            while cn > seed_n:
                par, d = canonical_parent(cur)
                cn, cm = cn - 1, cm - d
                k = table.get(cn, {}).get(cm)
                if k is None or min(degrees(par)) < k:
                    violations.append(f"Engel ({n},{m}) #{idx}: ancestor at ({cn},{cm}) has minimum degree "
                                      f"{min(degrees(par))}, the table's k is {k}")
                    break
                cur = par
                if cn == slice_level:
                    anc = encode(cur)
                    if prefix is not None and anc not in prefix.get(cm, ()):
                        missing.append(f"Engel ({n},{m}) #{idx}: level-{slice_level} ancestor {anc} not in the "
                                       f"prefix's {slice_level}-{cm}.keep.g6")
            if anc is not None:
                by_slice[slice_of(anc, count)].append([n, m, idx])
    return {"eligible": dict(eligible), "by_slice": {str(s): v for s, v in sorted(by_slice.items())},
            "violations": violations, "missing_from_prefix": missing}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reach", type=Path, required=True, help="a (24,69) reach.json")
    ap.add_argument("--prefix", type=Path, help="a (24,69) run directory holding levels <= the slice level")
    ap.add_argument("--slice-level", type=int, default=12)
    ap.add_argument("--count", type=int, default=1920)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    try:
        reach = json.loads(a.reach.read_text())
        known.production_reach(reach)
        if a.slice_level != 12 or a.count != 1920:
            raise ValueError("CONFIG: not a slice of 1920 at level 12")
        cells = known.catalogue()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"KNOWN-SLICES FAIL: {error}")
        return 1
    table = {int(n): {int(m): k for m, k in lv.items()} for n, lv in reach["table"].items()}
    seed_n = reach["seed_n"]
    files = [str(known.DATA / c["dataset"]["file"]) for c in cells.values()]
    prefix = None
    if a.prefix:
        prefix = {}
        for p in glob.glob(str(a.prefix / f"{a.slice_level}-*.keep.g6")):
            m = int(re.findall(rf"{a.slice_level}-(\d+)\.keep\.g6$", p)[0])
            prefix[m] = {l.strip() for l in open(p) if l.strip()}
        if not prefix:
            raise SystemExit(f"no {a.slice_level}-*.keep.g6 in {a.prefix}")
    problems = []
    if a.self_test:
        small = [f for f in files if f.endswith("engel-22-60.g6")]
        base = run(table, seed_n, a.slice_level, a.count, prefix, small)
        # a table with k raised above one ancestor's minimum degree: its first eligible graph's parent cell
        adj = canon(decode(open(small[0]).readline().strip()))[1]
        par, d = canonical_parent(adj)
        cell = (21, 60 - d)
        bad = {n: dict(lv) for n, lv in table.items()}
        bad[cell[0]][cell[1]] = min(degrees(par)) + 1
        r = run(bad, seed_n, a.slice_level, a.count, None, small)
        hit = any(f"ancestor at ({cell[0]},{cell[1]})" in v for v in r["violations"])
        print(f"self-test: k({cell[0]},{cell[1]}) raised to {bad[cell[0]][cell[1]]}: "
              f"{'VIOLATION reported' if hit else 'NOT reported'} ({len(r['violations'])} violations)")
        if not hit:
            problems.append("self-test: a raised k did not give a violation at its cell")
        if prefix is not None:
            # an empty prefix: every eligible (22,60) graph's level-12 ancestor must be reported missing
            r2 = run(table, seed_n, a.slice_level, a.count, {m: set() for m in prefix}, small)
            print(f"self-test: an empty prefix reports {len(r2['missing_from_prefix'])} missing "
                  f"(of {sum(base['eligible'].values())} eligible (22,60) graphs)")
            if len(r2["missing_from_prefix"]) != sum(base["eligible"].values()):
                problems.append("self-test: an empty prefix did not report every ancestor missing")
        if base["violations"] or base["missing_from_prefix"]:
            problems.append("self-test: the unmutated (22,60) run is not clean")
    res = run(table, seed_n, a.slice_level, a.count, prefix, files)
    res["reach_sha256"] = hashlib.sha256(a.reach.read_bytes()).hexdigest()
    res["engel_sha256"] = {Path(f).name: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
    res["slice_level"], res["count"] = a.slice_level, a.count
    if a.out:
        a.out.write_text(json.dumps(res, indent=0) + "\n")
    total = sum(res["eligible"].values())
    placed = sum(len(v) for v in res["by_slice"].values())
    print(f"eligible Engel graphs: {total} in {len(res['eligible'])} cells; placed in {len(res['by_slice'])} of "
          f"{a.count} slices: {placed}")
    for v in res["violations"][:20]:
        print("VIOLATION:", v)
    for v in res["missing_from_prefix"][:20]:
        print("MISSING:", v)
    problems += [f"{len(res['violations'])} violations"] * bool(res["violations"])
    problems += [f"{len(res['missing_from_prefix'])} ancestors missing from the prefix"] * bool(res["missing_from_prefix"])
    problems += [f"placed {placed} of {total}"] * (placed != total)
    for p in problems:
        print("PROBLEM:", p)
    print(f"KNOWN-SLICES {'OK' if not problems else 'FAIL'}: {total} eligible, {placed} placed"
          + (f", every level-{a.slice_level} ancestor in the prefix" if prefix is not None and not problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
