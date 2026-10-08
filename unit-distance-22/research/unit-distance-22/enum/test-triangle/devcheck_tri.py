#!/usr/bin/env python3
"""DEV AID ONLY: a private checker for udtriangle's "tri" certificates, used by this test directory.

It is NOT the pipeline's checker.  The independent checker is to be written blind, from RHOMBUS-SPEC.md, by another
agent; this one was written by the prover's builder and shares its reading of the spec, so it can catch the prover's
arithmetic and bookkeeping mistakes but not a shared misreading.  It implements Section 4 rules 1 to 5 literally,
in exact Python integers, and nothing else.

usage: devcheck_tri.py GRAPHS.g6 VERDICTS.jsonl [--json] [--count]
    GRAPHS.g6       the prover's input, one graph6 per line
    VERDICTS.jsonl  the prover's output, one JSON line per input line: {"verdict":"pass"} or
                    {"verdict":"refuted"|"tu","witness":{"tri":{"tree":NODE}}}
Prints one summary line (ACCEPT ... or REJECT line N: reason) and exits 0 on ACCEPT, 1 on REJECT.

Readings of the spec that this checker adopts (each is a choice where the text is open; see REPORT.md):
  * A leaf's "cycles" list may be EMPTY (a leaf closed by triangle rows alone).  Section 4 rule 2 says the cycles
    are "4-cycles of G as in Section 2 rule 2"; this checker reads that as the per-entry condition plus Section 2's
    cap of 4096 entries, not Section 2's "non-empty" (Section 2 has no triangles, so there an empty list is useless).
  * Coefficients may be zero (Section 4, unlike Section 2 rule 3, does not require them nonzero).
  * A triangle may appear more than once in a leaf's list (the spec does not forbid it; the prover never does it).
  * "pair" is not required to be sorted, and "edge" is an ordered pair (p, q) as the target formula uses it.
  * Depth is counted in splits: the root has depth 0 and a leaf's depth is the number of splits above it.
"""
import collections
import json
import sys

LIMIT = 1 << 62
MAX_NODES = 100000
MAX_DEPTH = 64
MAX_CYCLES = 4096
WPOW = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]      # w^k as x + y w, w^2 = w - 1


class Reject(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Reject(msg)


def zmul(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0] + a[1] * b[1])


def decode_g6(s):
    need(s and not s.startswith(">>") and all(63 <= ord(c) <= 126 for c in s), "bad graph6")
    v = [ord(c) - 63 for c in s]
    need(v[0] <= 62, "graph order encoding unsupported")
    n = v[0]
    bits = n * (n - 1) // 2
    need(len(v) - 1 == (bits + 5) // 6, "wrong graph6 length")
    flat = [(x >> sh) & 1 for x in v[1:] for sh in range(5, -1, -1)]
    need(not any(flat[bits:]), "nonzero graph6 padding")
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if flat[k]:
                edges.add((i, j))
            k += 1
    return n, edges


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def keys_exact(obj, required, optional=(), where=""):
    need(isinstance(obj, dict), f"{where}: expected an object")
    ks = set(obj)
    need(set(required) <= ks and ks <= set(required) | set(optional), f"{where}: keys {sorted(ks)}")


def vertex(x, n, where):
    need(is_int(x) and 0 <= x < n, f"{where}: not a vertex in [0, {n})")
    return x


def zw_elem(x, where):
    need(isinstance(x, list) and len(x) == 2 and all(is_int(c) for c in x), f"{where}: not a Z[w] pair of integers")
    need(all(-LIMIT < c < LIMIT for c in x), f"{where}: |component| >= 2^62")
    return (x[0], x[1])


class Checker:
    def __init__(self, n, edges):
        self.n, self.edges = n, edges
        self.nodes = 0
        self.any_edge = False
        self.leaves = 0
        self.stats = {"leaves_no_cycles": 0, "leaves_no_triangles": 0, "max_depth": 0, "rows": 0}

    def edge(self, a, b):
        return (min(a, b), max(a, b)) in self.edges

    def node(self, node, path, depth):
        """path: list of ((a, b, c), sign) for the splits above this node."""
        self.nodes += 1
        need(self.nodes <= MAX_NODES, "more than 100000 nodes")                          # rule 1
        need(depth <= MAX_DEPTH, "depth above 64")                                        # rule 1
        need(isinstance(node, dict), "node: expected an object")
        if "split" in node:
            keys_exact(node, ("split", "plus", "minus"), where="split node")
            t = node["split"]
            need(isinstance(t, list) and len(t) == 3, "split: expected [a, b, c]")
            a, b, c = (vertex(x, self.n, "split") for x in t)
            need(a < b < c, "split: not a sorted triple a < b < c")                      # rule 1
            need(self.edge(a, b) and self.edge(a, c) and self.edge(b, c), "split: not a triangle of G")
            need(all(tri != (a, b, c) for tri, _ in path), "split: triangle split twice on one path")
            self.node(node["plus"], path + [((a, b, c), 1)], depth + 1)
            self.node(node["minus"], path + [((a, b, c), -1)], depth + 1)
            return
        keys_exact(node, ("leaf",), where="leaf node")
        self.leaf(node["leaf"], path, depth)

    def leaf(self, L, path, depth):
        self.leaves += 1
        self.stats["max_depth"] = max(self.stats["max_depth"], depth)
        keys_exact(L, ("cycles", "cycle_coefficients", "triangles", "triangle_coefficients", "scale", "pair"),
                   ("edge", "zeta"), where="leaf")
        need(("edge" in L) == ("zeta" in L), "leaf: edge and zeta must come together")
        n = self.n
        acc = [(0, 0)] * n

        def add(v, z):
            acc[v] = (acc[v][0] + z[0], acc[v][1] + z[1])

        cycles, ccoef = L["cycles"], L["cycle_coefficients"]
        need(isinstance(cycles, list) and isinstance(ccoef, list), "leaf: cycles / coefficients not lists")
        need(len(cycles) <= MAX_CYCLES, "leaf: more than 4096 cycles")
        need(len(ccoef) == len(cycles), "leaf: cycle coefficient list length")            # rule 2
        for i, (cyc, co) in enumerate(zip(cycles, ccoef)):
            need(isinstance(cyc, list) and len(cyc) == 4, f"cycle {i}: expected [u, v, w, x]")
            u, v, w, x = (vertex(y, n, f"cycle {i}") for y in cyc)
            need(len({u, v, w, x}) == 4, f"cycle {i}: vertices not distinct")
            need(self.edge(u, v) and self.edge(v, w) and self.edge(w, x) and self.edge(x, u), f"cycle {i}: not a 4-cycle of G")
            l = zw_elem(co, f"cycle coefficient {i}")
            add(u, l); add(w, l); add(v, (-l[0], -l[1])); add(x, (-l[0], -l[1]))       # l * (e_u - e_v + e_w - e_x)
        tris, tcoef = L["triangles"], L["triangle_coefficients"]
        need(isinstance(tris, list) and isinstance(tcoef, list), "leaf: triangles / coefficients not lists")
        need(len(tcoef) == len(tris), "leaf: triangle coefficient list length")           # rule 2
        signs = dict(path)
        for i, (t, co) in enumerate(zip(tris, tcoef)):
            need(isinstance(t, list) and len(t) == 3 and all(is_int(y) for y in t), f"triangle {i}: expected [a, b, c]")
            key = tuple(t)
            need(key in signs, f"triangle {i}: {key} is not split on the path to this leaf")
            s = signs[key]
            a, b, c = key
            m = zw_elem(co, f"triangle coefficient {i}")
            rho = WPOW[1] if s == 1 else WPOW[5]                                          # w^s
            # t(T, s) = e_c - e_a - rho (e_b - e_a): c gets 1, a gets rho - 1, b gets -rho
            add(c, m)
            add(a, zmul(m, (rho[0] - 1, rho[1])))
            add(b, zmul(m, (-rho[0], -rho[1])))
        scale = zw_elem(L["scale"], "scale")
        need(scale != (0, 0), "scale is zero")                                            # rule 2
        pair = L["pair"]
        need(isinstance(pair, list) and len(pair) == 2, "pair: expected [a, b]")
        a, b = (vertex(y, n, "pair") for y in pair)
        need(a != b, "pair: vertices not distinct")                                       # rule 3
        target = [(0, 0)] * n
        target[a] = (1, 0)
        target[b] = (-1, 0)
        if "edge" in L:
            e = L["edge"]
            need(isinstance(e, list) and len(e) == 2, "edge: expected [p, q]")
            p, q = (vertex(y, n, "edge") for y in e)
            need(p != q and self.edge(p, q), "edge: pq is not an edge of G")               # rule 3
            need(not self.edge(a, b), "pair: ab is an edge of G")                          # rule 3
            k = L["zeta"]
            need(is_int(k) and 0 <= k <= 5, "zeta: not an integer 0..5")                  # rule 3
            wk = WPOW[k]
            target[p] = (target[p][0] - wk[0], target[p][1] - wk[1])
            target[q] = (target[q][0] + wk[0], target[q][1] + wk[1])
            self.any_edge = True
        for v in range(n):                                                                # rule 4
            need(acc[v] == zmul(scale, target[v]), f"identity fails at vertex {v}")
        if not cycles:
            self.stats["leaves_no_cycles"] += 1
        if not tris:
            self.stats["leaves_no_triangles"] += 1
        self.stats["rows"] += len(cycles) + len(tris)


def no_dupes(pairs):
    d = {}
    for k, v in pairs:
        need(k not in d, f"duplicate key {k!r}")
        d[k] = v
    return d


def bad_constant(x):
    raise Reject(f"non-JSON constant {x}")


def check_line(g6, line):
    """Returns (verdict, tree nodes, Checker or None)."""
    rec = json.loads(line, object_pairs_hook=no_dupes, parse_constant=bad_constant,
                     parse_float=lambda x: bad_constant(x))
    keys_exact(rec, ("verdict",), ("witness",), where="record")
    verdict = rec["verdict"]
    if verdict == "pass":
        need("witness" not in rec, "pass carries a witness")
        return "pass", 0, None
    need(verdict in ("refuted", "tu"), f"unknown verdict {verdict!r}")
    keys_exact(rec, ("verdict", "witness"), where="record")
    keys_exact(rec["witness"], ("tri",), where="witness")
    keys_exact(rec["witness"]["tri"], ("tree",), where="tri")
    n, edges = decode_g6(g6)
    ck = Checker(n, edges)
    ck.node(rec["witness"]["tri"]["tree"], [], 0)
    need((verdict == "tu") == ck.any_edge, "verdict disagrees with the leaves (rule 5)")   # rule 5
    return verdict, ck.nodes, ck


def count_mode(graphs, lines):
    """--count: check every line and report how many certificates are rejected (for the red controls)."""
    rejected, reasons = 0, collections.Counter()
    certs = 0
    for i, (g, line) in enumerate(zip(graphs, lines), 1):
        try:
            verdict, _, _ = check_line(g, line)
            certs += verdict != "pass"
        except (Reject, ValueError, RecursionError) as exc:
            certs += 1
            rejected += 1
            reasons[str(exc).split(":")[0]] += 1
    print(f"COUNT certificates={certs} rejected={rejected} accepted={certs - rejected} reasons={dict(reasons)}")
    return 1 if rejected else 0


def main(argv):
    graphs = [l.strip() for l in open(argv[1]) if l.strip()]
    lines = open(argv[2]).read().splitlines()
    as_json = "--json" in argv
    if len(lines) != len(graphs):
        print(f"REJECT: {len(lines)} output lines for {len(graphs)} graphs")
        return 1
    if "--count" in argv:
        return count_mode(graphs, lines)
    counts = {"pass": 0, "refuted": 0, "tu": 0}
    nodes_total = nodes_max = leaves = no_cyc = no_tri = rows = depth_max = 0
    for i, (g, line) in enumerate(zip(graphs, lines), 1):
        try:
            verdict, nodes, ck = check_line(g, line)
        except (Reject, ValueError, RecursionError) as exc:
            print(f"REJECT line {i}: {exc}  graph {g}")
            return 1
        counts[verdict] += 1
        if ck:
            nodes_total += nodes
            nodes_max = max(nodes_max, nodes)
            leaves += ck.leaves
            no_cyc += ck.stats["leaves_no_cycles"]
            no_tri += ck.stats["leaves_no_triangles"]
            rows += ck.stats["rows"]
            depth_max = max(depth_max, ck.stats["max_depth"])
    certs = counts["refuted"] + counts["tu"]
    summary = {"records": len(graphs), **counts, "tree_nodes": nodes_total, "max_nodes": nodes_max, "leaves": leaves,
               "mean_nodes": round(nodes_total / certs, 2) if certs else 0, "max_depth": depth_max,
               "leaves_without_cycles": no_cyc, "leaves_without_triangles": no_tri,
               "mean_rows_per_leaf": round(rows / leaves, 2) if leaves else 0}
    print("ACCEPT " + (json.dumps(summary) if as_json else " ".join(f"{k}={v}" for k, v in summary.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
