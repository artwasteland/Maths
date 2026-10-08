"""Optional independent F10 search on proper blocks, through order TEN.

Bitset backtracking for non-induced containment; no networkx, checker or
producer matching routines. F10-freeness already follows from B11's freeze.
This optional redundant check makes the ten-vertex boundary explicit.
"""
from collections import Counter
from pathlib import Path

from independent_core import adjacency, decode_g6, digest, iso_key, loads, require


def monomorphism(host_n, host_edges, pattern_n, pattern_edges):
    if pattern_n > host_n or len(pattern_edges) > len(host_edges):
        return False
    ha, pa = adjacency(host_n, host_edges), adjacency(pattern_n, pattern_edges)
    hd, pd = list(map(len, ha)), list(map(len, pa))
    if any(x > y for x, y in zip(sorted(pd, reverse=True), sorted(hd, reverse=True))):
        return False
    hb = [sum(1 << u for u in neighbors) for neighbors in ha]
    domains = [sum(1 << j for j in range(host_n) if hd[j] >= pd[i]) for i in range(pattern_n)]
    if any(not d for d in domains):
        return False
    # Identical open/closed neighborhoods give interchangeable pattern
    # vertices. Ordering their images removes only automorphic duplicate maps.
    twins = {(i, j) for i in range(pattern_n) for j in range(i + 1, pattern_n)
             if pa[i] - {j} == pa[j] - {i}}

    def search(current, assigned, available):
        if len(assigned) == pattern_n:
            return True
        unassigned = [i for i in range(pattern_n) if i not in assigned]
        vertex = min(unassigned, key=lambda i: ((current[i] & available).bit_count(), -pd[i], i))
        choices = current[vertex] & available
        while choices:
            bit = choices & -choices
            choices -= bit
            image = bit.bit_length() - 1
            if any((min(vertex, u), max(vertex, u)) in twins
                   and ((vertex < u and image >= j) or (vertex > u and image <= j))
                   for u, j in assigned.items()):
                continue
            next_domains = current[:]
            remaining = available ^ bit
            valid = True
            for u in unassigned:
                if u == vertex:
                    continue
                next_domains[u] &= remaining
                if u in pa[vertex]:
                    next_domains[u] &= hb[image]
                if not next_domains[u]:
                    valid = False
                    break
            if valid:
                assigned[vertex] = image
                if search(next_domains, assigned, remaining):
                    return True
                del assigned[vertex]
        return False

    return search(domains, {}, (1 << host_n) - 1)


class ForbiddenCatalogue:
    def __init__(self, path):
        raw = loads(Path(path).read_bytes())
        require(isinstance(raw, list) and len(raw) == 398, "F10", "expected the 398-member catalogue")
        self.patterns, self.cache, self.stats = [], {}, Counter()
        self.sha256 = digest(path)
        require(self.sha256 == "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c",
                "F10_freeze", "catalogue bytes do not match frozen forbidden-398.json")
        for index, edges in enumerate(raw):
            require(isinstance(edges, list) and edges, "F10", "invalid forbidden graph")
            es = {tuple(sorted(e)) for e in edges}
            n = 1 + max(v for e in es for v in e)
            require(4 <= n <= 10 and all(0 <= u < v < n for u, v in es), "F10", "invalid F10 edge")
            self.patterns.append((index, n, es))

    def witness(self, n, edges):
        key = iso_key(n, edges)
        self.stats["blocks_requested"] += 1
        if key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[key]
        self.stats["distinct_blocks_checked"] += 1
        self.stats[f"distinct_blocks_order_{n}"] += 1
        found = None
        for index, order, pattern in self.patterns:
            if order <= n:
                self.stats["patterns_considered"] += 1
                if monomorphism(n, edges, order, pattern):
                    found = index
                    break
        self.cache[key] = found
        return found
