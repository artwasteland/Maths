#!/usr/bin/env python3
"""
s-Bulgarian solitaire — well-behaved sigma-Bulgarian with sigma(h)=min(h,s).

Move B_s on a partition of n (piles, descending tuple):
  from every pile of size h remove min(h, s) cards; collect ALL removed cards
  into ONE new pile; drop emptied piles; re-sort descending.

s=1 is classic Bulgarian solitaire. Fixed points are step-s staircases
(a, a-s, a-2s, ..., r) with r in [1,s].

We build the full functional graph for each n and read off exact statistics,
then hunt for OEIS-absent sequences among the s>=2 dynamics.

Two modes:
  python3 s_explore.py [N=34] [s ...]      print the statistic tables
  python3 s_explore.py --check [N=40] [s]  ASSERT against the staged b-files of
                                           oversight/oeis/generalized-bulgarian-solitaire
                                           (s=2,3 by default); exit 1 on any mismatch
"""
import os
import sys
from functools import lru_cache
from collections import Counter
from math import gcd

def partitions(n, maxpart=None):
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for first in range(min(n, maxpart), 0, -1):
        for rest in partitions(n - first, first):
            yield (first,) + rest

def move(part, s):
    removed = 0
    new = []
    for p in part:
        take = p if p < s else s
        removed += take
        if p - take > 0:
            new.append(p - take)
    if removed > 0:
        new.append(removed)
    new.sort(reverse=True)
    return tuple(new)

def _lcm(xs):
    l = 1
    for x in xs:
        l = l * x // gcd(l, x)
    return l

def analyze(n, s):
    G = {p: move(p, s) for p in partitions(n)}
    nodes = list(G.keys())
    P = len(nodes)
    image = set(G.values())
    goe = [p for p in nodes if p not in image]

    color = {}
    on_cycle = set()
    cycles = []
    for start in nodes:
        if color.get(start, 0) != 0:
            continue
        path = []
        pos = {}
        cur = start
        while color.get(cur, 0) == 0:
            color[cur] = 1
            pos[cur] = len(path)
            path.append(cur)
            cur = G[cur]
        if color.get(cur, 0) == 1:
            idx = pos[cur]
            cyc = path[idx:]
            cycles.append(cyc)
            for x in cyc:
                on_cycle.add(x)
        for x in path:
            color[x] = 2

    import sys as _s
    _s.setrecursionlimit(1 << 20)
    @lru_cache(maxsize=None)
    def tail(p):
        if p in on_cycle:
            return 0
        return 1 + tail(G[p])
    tails = {p: tail(p) for p in nodes}
    max_tail = max(tails.values()) if tails else 0
    total_settle = sum(tails.values())
    max_tail_count = sum(1 for v in tails.values() if v == max_tail)

    cycle_lengths = sorted(len(c) for c in cycles)
    return {
        "n": n, "s": s, "P": P,
        "num_goe": len(goe),
        "num_recurrent": len(on_cycle),
        "num_transient": P - len(on_cycle),
        "num_cycles": len(cycles),
        "num_fixed_points": sum(1 for c in cycles if len(c) == 1),
        "cycle_lengths": cycle_lengths,
        "distinct_cycle_lengths": len(set(cycle_lengths)),
        "max_cycle_length": max(cycle_lengths) if cycle_lengths else 0,
        "lcm_cycle_lengths": _lcm(cycle_lengths) if cycle_lengths else 1,
        "max_tail": max_tail,
        "max_tail_count": max_tail_count,
        "total_settle": total_settle,
    }

def has_fixed_point(n, s):
    """True iff a step-s staircase sums to n. Returns the staircase or None."""
    # staircase (a, a-s, ..., r), r in [1,s], m terms; sum = m*a - s*m*(m-1)/2
    # a = r + (m-1)s, r in [1,s]. Enumerate m, r.
    for m in range(1, n + 1):
        for r in range(1, s + 1):
            a = r + (m - 1) * s
            total = m * r + s * m * (m - 1) // 2
            if total == n:
                return tuple(a - i * s for i in range(m))
            if total > n:
                break
    return None

STAGED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "oversight", "oeis", "generalized-bulgarian-solitaire",
)

# Field name in analyze() -> b-file stem in the staged directory.
STAGED_FILES = {
    "total_settle": "b-total-settle",
    "max_tail": "b-max-tail",
    "num_goe": "b-goe",
    "num_cycles": "b-num-cycles",
    "num_recurrent": "b-recurrent",
}


def read_bfile(path):
    """Parse an OEIS b-file into {index: value}, rejecting anything malformed."""
    terms = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"{path}: unparsable b-file line {raw!r}")
            terms[int(parts[0])] = int(parts[1])
    if not terms:
        raise ValueError(f"{path}: no terms")
    return terms


def check_staged(N, ss=(2, 3)):
    """Assertion mode: reproduce the staged b-files of
    oversight/oeis/generalized-bulgarian-solitaire and diff term by term.

    This exists so the Python engine is a CHECK and not a printout. Before
    2026-07-27 nothing in the repo ever compared this file's output against
    anything, so the "independent Python path" was a claim resting on a human
    doing the diff by eye. Now it exits nonzero on any mismatch.

    Only the s=2 and s=3 files of that one directory are read. The s=1 artifact
    lives elsewhere and is not this function's business.
    """
    staged = {}
    for s in ss:
        for field, stem in STAGED_FILES.items():
            path = os.path.join(STAGED_DIR, f"{stem}-s{s}.txt")
            staged[(s, field)] = (path, read_bfile(path))

    mismatches = []
    checked = {k: 0 for k in staged}
    for s in ss:
        for n in range(1, N + 1):
            a = analyze(n, s)
            for field in STAGED_FILES:
                path, terms = staged[(s, field)]
                if n not in terms:
                    continue
                checked[(s, field)] += 1
                if terms[n] != a[field]:
                    mismatches.append((path, n, terms[n], a[field]))

    for s in ss:
        for field, stem in STAGED_FILES.items():
            path, terms = staged[(s, field)]
            total = len(terms)
            got = checked[(s, field)]
            top = max(terms)
            gap = "" if got == total else f"; NOT recomputed here: indices {N + 1}..{top}"
            print(f"{stem}-s{s}.txt: {got}/{total} staged terms recomputed in Python and matched{gap}")

    for path, n, want, got in mismatches:
        print(f"!!! DISAGREEMENT {os.path.basename(path)} n={n}: staged {want}, Python {got}")
    if mismatches:
        print(f"{len(mismatches)} mismatch(es). A DISAGREEMENT IS A DISCOVERY, NOT A TYPO: do not edit a b-file.")
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
        SS = [int(x) for x in sys.argv[3:]] or [2, 3]
        sys.exit(check_staged(N, SS))

    N = int(sys.argv[1]) if len(sys.argv) > 1 else 34
    SS = [int(x) for x in sys.argv[2:]] or [1, 2, 3, 4]
    for s in SS:
        seqs = {k: [] for k in
                ["P", "num_goe", "num_recurrent", "num_transient", "num_cycles",
                 "num_fixed_points", "distinct_cycle_lengths", "max_cycle_length",
                 "lcm_cycle_lengths", "max_tail", "max_tail_count", "total_settle"]}
        fp_ns = []
        for n in range(1, N + 1):
            a = analyze(n, s)
            for k in seqs:
                seqs[k].append(a[k])
            if a["num_fixed_points"] > 0:
                fp_ns.append(n)
        print(f"\n===== s = {s} =====")
        print(f"# n with a fixed point (step-{s} staircase sums to n): {fp_ns}")
        for k, v in seqs.items():
            print(f"{k}:")
            print("  " + ", ".join(map(str, v)))
