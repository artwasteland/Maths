#!/usr/bin/env python3
"""
Bulgarian solitaire — exact dynamics on integer partitions.

The classic move B on a partition of n (a multiset of positive pile sizes):
  remove one card from every pile (piles of size 1 vanish), then form ONE new
  pile whose size = the number of piles you had before removing.

B is a deterministic map on partitions(n) -> partitions(n). This script builds
the full functional graph for each n and extracts every dynamical statistic,
so we can search OEIS for whichever ones are absent.

Partition representation: a tuple of pile sizes sorted DESCENDING (canonical).
"""
import sys
from functools import lru_cache

def partitions(n, maxpart=None):
    """Yield all partitions of n as descending tuples."""
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for first in range(min(n, maxpart), 0, -1):
        for rest in partitions(n - first, first):
            yield (first,) + rest

def bulgarian(part):
    """One Bulgarian-solitaire move. part is a descending tuple summing to n."""
    k = len(part)                      # number of piles -> becomes the new pile
    new = [p - 1 for p in part if p - 1 > 0]
    if k > 0:
        new.append(k)
    new.sort(reverse=True)
    return tuple(new)

def functional_graph(n):
    """Return dict: partition -> B(partition) over all partitions of n."""
    return {p: bulgarian(p) for p in partitions(n)}

def analyze(n):
    """Compute dynamical statistics of B on partitions(n)."""
    G = functional_graph(n)
    nodes = list(G.keys())
    P = len(nodes)                     # = number of partitions of n = A000041

    # image / garden of eden
    image = set(G.values())
    goe = [p for p in nodes if p not in image]

    # Find recurrent nodes (on a cycle) via iterated-map cycle detection.
    # Every node eventually enters a unique cycle (functional graph).
    color = {}          # 0=unvisited,1=in progress,2=done
    on_cycle = set()
    cycles = []         # list of cycles (each a list of nodes)
    order = {}
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
            # found a new cycle: from pos[cur] to end of path
            idx = pos[cur]
            cyc = path[idx:]
            cycles.append(cyc)
            for x in cyc:
                on_cycle.add(x)
        # mark path done
        for x in path:
            color[x] = 2

    # tail length (steps to reach the cycle) for each node
    @lru_cache(maxsize=None)
    def tail(p):
        if p in on_cycle:
            return 0
        return 1 + tail(G[p])
    tails = {p: tail(p) for p in nodes}
    max_tail = max(tails.values()) if tails else 0

    cycle_lengths = sorted(len(c) for c in cycles)
    from collections import Counter
    clc = Counter(cycle_lengths)

    # triangular?
    k = 0
    tri = False
    while k*(k+1)//2 <= n:
        if k*(k+1)//2 == n:
            tri = True
        k += 1

    return {
        "n": n,
        "P": P,
        "num_goe": len(goe),
        "num_recurrent": len(on_cycle),
        "num_transient": P - len(on_cycle),
        "num_cycles": len(cycles),
        "num_fixed_points": sum(1 for c in cycles if len(c) == 1),
        "cycle_lengths": cycle_lengths,
        "distinct_cycle_lengths": len(set(cycle_lengths)),
        "max_cycle_length": max(cycle_lengths) if cycle_lengths else 0,
        "lcm_cycle_lengths": _lcm(cycle_lengths),
        "max_tail": max_tail,
        "triangular": tri,
        "goe_list": goe,
    }

def _lcm(xs):
    from math import gcd
    l = 1
    for x in xs:
        l = l * x // gcd(l, x)
    return l

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    seqs = {
        "P (A000041)": [],
        "num_goe": [],
        "num_recurrent": [],
        "num_transient": [],
        "num_cycles": [],
        "num_fixed_points": [],
        "distinct_cycle_lengths": [],
        "max_cycle_length": [],
        "lcm_cycle_lengths": [],
        "max_tail": [],
    }
    tri_marks = []
    for n in range(1, N + 1):
        a = analyze(n)
        seqs["P (A000041)"].append(a["P"])
        seqs["num_goe"].append(a["num_goe"])
        seqs["num_recurrent"].append(a["num_recurrent"])
        seqs["num_transient"].append(a["num_transient"])
        seqs["num_cycles"].append(a["num_cycles"])
        seqs["num_fixed_points"].append(a["num_fixed_points"])
        seqs["distinct_cycle_lengths"].append(a["distinct_cycle_lengths"])
        seqs["max_cycle_length"].append(a["max_cycle_length"])
        seqs["lcm_cycle_lengths"].append(a["lcm_cycle_lengths"])
        seqs["max_tail"].append(a["max_tail"])
        if a["triangular"]:
            tri_marks.append(n)
    print(f"# Bulgarian solitaire, standard map, n=1..{N}")
    print(f"# triangular n in range: {tri_marks}")
    for name, s in seqs.items():
        print(f"{name}:")
        print("  " + ", ".join(map(str, s)))
