"""Prototype: how much would a general "rhombus-linear" filter prune beyond the six TU gadgets?

In an injective unit-distance embedding, every 4-cycle u-v-w-x of unit edges is a rhombus: p_u + p_w = p_v + p_x
(four unit vectors summing to zero pair into opposite pairs; the other two pairings put u on w or v on x). So the
4-cycles of a graph give linear relations on the positions. Consequences checked here:
  collision   e_a - e_b in rowspace        -> p_a = p_b, impossible: the graph is not unit-distance (L1-type prune)
  hidden edge e_a - e_b = +-(e_u - e_v) mod rowspace, uv an edge, ab a NON-edge -> |p_a - p_b| = 1 forced: a TU-type
              prune at a target (N, M) with M >= u(N) (PRUNING.md L2, generalised from the six gadgets)
Linear algebra mod p = 2^61 - 1 (a measurement; production would carry exact rational certificates).

usage: python rhombus_probe.py FILE.g6 [FILE.g6 ...]
"""
import sys, itertools
import networkx as nx

P = (1 << 61) - 1


def rref_mod(rows, n):
    """Row-reduce integer rows mod P; return list of (pivot_col, row) in reduced echelon form."""
    piv = []  # list of (col, row) with row[col] == 1
    for r in rows:
        r = [x % P for x in r]
        for c, pr in piv:
            if r[c]:
                f = r[c]
                r = [(a - f * b) % P for a, b in zip(r, pr)]
        lead = next((i for i, x in enumerate(r) if x), None)
        if lead is None:
            continue
        inv = pow(r[lead], P - 2, P)
        r = [(x * inv) % P for x in r]
        # keep fully reduced: eliminate this column from earlier pivots
        new = []
        for c, pr in piv:
            if pr[lead]:
                f = pr[lead]
                pr = [(a - f * b) % P for a, b in zip(pr, r)]
            new.append((c, pr))
        piv = new + [(lead, r)]
    return piv


def reduce_vec(v, piv):
    v = list(v)
    for c, pr in piv:
        if v[c]:
            f = v[c]
            v = [(a - f * b) % P for a, b in zip(v, pr)]
    return tuple(v)


def probe(G):
    n = G.number_of_nodes()
    adj = [set(G[v]) for v in range(n)]
    rows = []
    for u, w in itertools.combinations(range(n), 2):
        common = sorted(adj[u] & adj[w])
        for v, x in itertools.combinations(common, 2):
            r = [0] * n
            r[u] += 1; r[w] += 1; r[v] -= 1; r[x] -= 1
            rows.append(r)
    if not rows:
        return "none", len(rows)
    piv = rref_mod(rows, n)
    red = [reduce_vec([1 if i == v else 0 for i in range(n)], piv) for v in range(n)]
    diff = lambda a, b: tuple((x - y) % P for x, y in zip(red[a], red[b]))
    for a, b in itertools.combinations(range(n), 2):
        if red[a] == red[b]:
            return "collision", len(rows)
    edge_diffs = set()
    for u, v in G.edges():
        edge_diffs.add(diff(u, v)); edge_diffs.add(diff(v, u))
    for a, b in itertools.combinations(range(n), 2):
        if not G.has_edge(a, b) and diff(a, b) in edge_diffs:
            return "hidden-edge", len(rows)
    return "none", len(rows)


if __name__ == "__main__":
    from collections import Counter
    for path in sys.argv[1:]:
        c = Counter(); rels = 0; total = 0
        for line in open(path):
            g6 = line.strip()
            if not g6:
                continue
            verdict, k = probe(nx.from_graph6_bytes(g6.encode()))
            c[verdict] += 1; rels += k; total += 1
        pruned = c["collision"] + c["hidden-edge"]
        print(f"{path.rsplit('/', 1)[-1]:32s} graphs {total:6d}  pruned {pruned:6d} ({100 * pruned / max(total, 1):5.1f}%)"
              f"  collision {c['collision']:5d}  hidden-edge {c['hidden-edge']:5d}  mean 4-cycle relations {rels / max(total, 1):6.1f}",
              flush=True)
