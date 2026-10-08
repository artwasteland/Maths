#!/usr/bin/env python3
"""Count connected graphs in a graph6 file (BFS on the decoded adjacency).  Used on brute10.py's
brute398.g6: the 398-free graphs on 10 vertices are exactly the unit-distance graphs on 10 vertices
(the 398 are all minimal non-unit-distance graphs on at most 10 vertices), so the connected ones
should number A059103(10), which the GP-10 branch reports as 91,658."""
import sys

from t398lib import decode_g6, g6_lines


def connected(line: bytes) -> bool:
    n, edges = decode_g6(line)
    adj = {v: set() for v in range(n)}
    for e in edges:
        a, b = tuple(e)
        adj[a].add(b)
        adj[b].add(a)
    seen, stack = {0}, [0]
    while stack:
        for w in adj[stack.pop()]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == n


lines = g6_lines(sys.argv[1])
c = sum(connected(x) for x in lines)
print(f"{sys.argv[1]}: {len(lines)} graphs, {c} connected")
