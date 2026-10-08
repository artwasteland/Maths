#!/usr/bin/env python3
"""CONTRACT Section 4.3's known-graph control for the (23,65) fleet: the densest known 22-point configurations survive.

usage: python level22_control.py [<extraction root>] [--engel FILE] [--labelg PATH] [--self-test]

Engel's 35 known 22-point configurations with 60 unit distances (sources/engel-dataset/engel-22-60.g6 of the u(22)
programme) are unit-distance graphs of their own points, hence faithful: no TU gadget, rhombus or triangle rule can
prune them or their ancestors. So each one whose minimum degree is at least 4 must appear at level 22, in the (22,60)
cell, of the (23,65) enumeration. This checks it on the fleet's pushed keep files: the union of every slice copy's
22-60.keep.g6 must contain the canonical form (nauty-labelg, the form check/udcheck.py enforces) of every such graph.
It also reports the kept (22,60) graphs that are not Engel's (the filter-only prune keeps what it cannot decide), and
requires every kept (22,60) graph to lie in one slice only: canonical augmentation gives each graph one ancestor chain,
so two slices holding the same graph would mean the slices are not the partition the coverage argument assumes.

Exit 0 only when no required graph is missing and no graph is in two slices. --self-test first shows the checks can
fail: with one required graph's form removed from the union it must report that graph missing, a copy of an Engel
graph with one edge flipped must not be found, and a required graph also placed in a second slice must be reported.
"""
import argparse, glob, hashlib, subprocess, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
ROOT = Path("<scratch>/scratchpad/fleet/results")
KIND = "23-65-L12-tri-pf74"


def decode(g6: str) -> tuple[int, set]:
    """graph6 for n <= 62: the vertex count, and the edge set {(i, j), i < j}."""
    n = ord(g6[0]) - 63
    bits = "".join(format(ord(c) - 63, "06b") for c in g6[1:])
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                edges.add((i, j))
            k += 1
    return n, edges


def encode(n: int, edges: set) -> str:
    bits = "".join("1" if (i, j) in edges else "0" for j in range(1, n) for i in range(j))
    bits += "0" * (-len(bits) % 6)
    return chr(n + 63) + "".join(chr(int(bits[k:k + 6], 2) + 63) for k in range(0, len(bits), 6))


def min_degree(n: int, edges: set) -> int:
    deg = [0] * n
    for i, j in edges:
        deg[i] += 1
        deg[j] += 1
    return min(deg)


def canonical(codes: list[str], labelg: str) -> list[str]:
    r = subprocess.run([labelg, "-q"], input="".join(c + "\n" for c in codes), capture_output=True, text=True,
                       check=True)
    out = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    if len(out) != len(codes):
        raise SystemExit(f"labelg returned {len(out)} graphs for {len(codes)}")
    return out


def duplicates(kept: dict) -> dict:
    """The kept forms found in more than one slice (copies of one slice share its directory name)."""
    return {f: sorted(s) for f, s in kept.items() if len(s) > 1}


def evaluate(engel: list[str], kept: dict, labelg: str) -> tuple[list, list, list]:
    """(required, missing, extra): required = [(index, canonical form, min degree)] of the Engel graphs with minimum
    degree >= 4; missing = the required ones not in kept; extra = kept forms that are no Engel graph's."""
    forms = canonical(engel, labelg)
    required = []
    for k, (code, form) in enumerate(zip(engel, forms)):
        n, e = decode(code)
        if n != 22 or len(e) != 60:
            raise SystemExit(f"Engel graph {k} is ({n},{len(e)}), not (22,60)")
        d = min_degree(n, e)
        if d >= 4:
            required.append((k, form, d))
    missing = [r for r in required if r[1] not in kept]
    extra = sorted(set(kept) - set(forms))
    return required, missing, extra


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, nargs="?", default=ROOT)
    ap.add_argument("--engel", type=Path, default=REPO / "research/unit-distance-22/sources/engel-dataset/engel-22-60.g6")
    ap.add_argument("--labelg", default="nauty-labelg")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    engel = [l.strip() for l in a.engel.read_text().splitlines() if l.strip()]
    kept: dict = defaultdict(set)
    copies = 0
    for p in glob.glob(str(a.root / f"*/research/unit-distance-23/results/u23/{KIND}/s*of1920/22-60.keep.g6")):
        copies += 1
        sl = Path(p).parent.name
        for line in Path(p).read_text().splitlines():
            if line.strip():
                kept[line.strip()].add(sl)
    problems = []
    if a.self_test:
        req, _, _ = evaluate(engel, kept, a.labelg)
        if not req:
            problems.append("self-test: no required graph to remove")
        else:
            k, form, _ = req[0]
            _, miss, _ = evaluate(engel, {f: s for f, s in kept.items() if f != form}, a.labelg)
            print(f"self-test: with Engel graph {k}'s form removed from the union, missing = {[m[0] for m in miss]}")
            if [m[0] for m in miss] != [k]:
                problems.append("self-test: removing one required form did not report exactly that graph missing")
        n, e = decode(engel[0])
        flip = (0, 1)
        e2 = (e - {flip}) if flip in e else (e | {flip})
        form2 = canonical([encode(n, e2)], a.labelg)[0]
        print(f"self-test: Engel graph 0 with the pair (0,1) flipped is {'FOUND (wrong)' if form2 in kept else 'not found'}")
        if form2 in kept:
            problems.append("self-test: an edge-flipped Engel graph was found")
        if req and kept.get(req[0][1]):
            k, form, _ = req[0]
            twice = {**kept, form: kept[form] | {"s-1of1920"}}
            flagged = form in duplicates(twice)
            print(f"self-test: Engel graph {k} also placed in a second slice is {'reported' if flagged else 'NOT reported'}")
            if not flagged:
                problems.append("self-test: a graph in two slices was not reported")
    required, missing, extra = evaluate(engel, kept, a.labelg)
    print(f"Engel file: {a.engel.resolve().relative_to(REPO) if a.engel.resolve().is_relative_to(REPO) else a.engel} "
          f"sha256 {hashlib.sha256(a.engel.read_bytes()).hexdigest()}")
    print(f"Engel (22,60) graphs: {len(engel)}; required (minimum degree >= 4): {len(required)}; "
          f"kept (22,60) graphs in the fleet: {len(kept)} distinct, from {copies} slice copies")
    for k, form, d in required:
        where = sorted(kept.get(form, ()))
        print(f"  Engel {k:2d} (min degree {d}): {'found in ' + ', '.join(where) if where else 'MISSING'}")
    print(f"kept (22,60) graphs that are not Engel's: {len(extra)} (undecided by the filter-only prune)")
    dup = duplicates(kept)
    print(f"kept (22,60) graphs in more than one slice: {len(dup)}")
    for m in missing:
        problems.append(f"Engel graph {m[0]} (minimum degree {m[2]}) is missing from level 22")
    for f, s in sorted(dup.items()):
        problems.append(f"{f} is kept in {len(s)} slices: {', '.join(s)}")
    for p in problems:
        print("PROBLEM:", p)
    print(f"LEVEL-22 CONTROL {'OK' if not problems else 'FAIL'}: {len(required) - len(missing)} of {len(required)} "
          f"required graphs found")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
