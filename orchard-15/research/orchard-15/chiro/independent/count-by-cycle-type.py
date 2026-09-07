#!/usr/bin/env python3
"""The (15,32) orbit sizes by hand: perfect matchings of {3..14} avoiding the row-0 pairs,
classified by the cycle type of M ∪ M0. Expected: 6040 total; (4,4,4): 120, (8,4): 1440,
(6,6): 640, (12,): 3840. No group theory, no imports from exist.py."""
import collections
pts = list(range(3, 15))
M0 = {frozenset(p) for p in ((3,4),(5,6),(7,8),(9,10),(11,12),(13,14))}
def matchings(v):
    if not v:
        yield frozenset(); return
    a = v[0]
    for b in v[1:]:
        e = frozenset((a, b))
        if e in M0: continue
        rest = [x for x in v if x not in (a, b)]
        for m in matchings(rest): yield m | {e}
def cycle_type(M):
    adj = collections.defaultdict(list)
    for e in M | M0:
        a, b = tuple(e); adj[a].append(b); adj[b].append(a)
    seen, lens = set(), []
    for s in pts:
        if s in seen: continue
        n, x, prev = 0, s, None
        while x not in seen:
            seen.add(x); n += 1; nxt = [y for y in adj[x] if y != prev]; prev, x = x, nxt[0]
        lens.append(n)
    return tuple(sorted(lens, reverse=True))
cnt = collections.Counter(cycle_type(M) for M in matchings(pts))
print('total', sum(cnt.values()), dict(cnt))
assert sum(cnt.values()) == 6040 and cnt[(4,4,4)] == 120 and cnt[(8,4)] == 1440 and cnt[(6,6)] == 640 and cnt[(12,)] == 3840
print('OK: 120, 1440, 640, 3840')
