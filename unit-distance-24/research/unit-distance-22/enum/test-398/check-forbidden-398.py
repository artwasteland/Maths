#!/usr/bin/env python3
"""Independent check of data/forbidden-398.json and .g6 (networkx; shares no code with the builder).

Checks, each reported by name (all run; failures are collected, not short-circuited):
  C1 json-shape      398 entries, each a duplicate-free edge list on vertices 0..n-1, no isolated vertex
  C2 g6-shape        398 newline-terminated graph6 lines, each parsed by networkx
  C3 first-74        entries 0..73 equal forbidden-74.json verbatim, lines 0..73 equal forbidden-74.g6,
                     and each JSON graph is isomorphic to its graph6 line (the 74 JSON labellings are
                     GP's notebook labellings, the .g6 lines are nauty-canonical, CONTRACT 9.4)
  C4 last-324        line 74+j equals L10.g6 line j, and JSON entry 74+j has EXACTLY the labelled edge
                     set of that graph6 string (same labelling, not merely isomorphic)
  C5 composition     (order, size) counts: CONTRACT Section 1 for the 74; 4/126/191/3 at 15..18 edges
                     for the 324 (GP-10 RESULT.md)
  C6 non-isomorphic  the 398 are pairwise non-isomorphic
  C7 antichain       no member is a (not necessarily induced) subgraph of another
  C8 patterns        min degree >= 2, 2-connected, and the deletion-pattern size distribution computed
                     from vertex degrees is {2: 251, 3: 2474, 4: 920, 5: 192, 6: 34, 7: 4}, total 3875
  C9 hashes          sha256 of both files equal the pinned values

--self-test builds mutated copies and requires each targeted check to go red.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import networkx as nx
from networkx.algorithms import isomorphism as iso

HERE = Path(__file__).resolve().parent
UD = HERE.parent.parent
REPO = UD.parent.parent
DATA = UD / "data"

PIN_JSON = "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"
PIN_G6 = "91d5810c4d7b02d97afec7dfe2a2a5629f2075439100aa8eae6b60dca4ff4381"
COMPOSITION_74 = {(4, 6): 1, (5, 6): 1, (6, 9): 1, (7, 10): 1, (7, 11): 2, (8, 12): 3, (8, 13): 10,
                  (9, 13): 2, (9, 14): 19, (9, 15): 34}
COMPOSITION_324 = {(10, 15): 4, (10, 16): 126, (10, 17): 191, (10, 18): 3}
DISTRIBUTION = {2: 251, 3: 2474, 4: 920, 5: 192, 6: 34, 7: 4}


def graph_from_edges(edges) -> nx.Graph:
    g = nx.Graph()
    n = max(max(e) for e in edges) + 1
    g.add_nodes_from(range(n))
    g.add_edges_from((a, b) for a, b in edges)
    return g


_MONO_CACHE: dict[tuple, bool] = {}


def _key(g: nx.Graph) -> tuple:
    return (g.number_of_nodes(), tuple(sorted(tuple(sorted(e)) for e in g.edges())))


def is_subgraph(pattern: nx.Graph, host: nx.Graph) -> bool:
    """True iff pattern is a (not necessarily induced) subgraph of host (networkx VF2).

    Prefilter (sound): an injective edge-preserving map sends the k highest-degree pattern
    vertices to k distinct host vertices of at least that degree, so the descending degree
    sequences must dominate position by position.  Results are memoised on the labelled edge
    lists, so the self-test re-pays only for pairs that a mutation changed."""
    if pattern.number_of_nodes() > host.number_of_nodes() or pattern.number_of_edges() > host.number_of_edges():
        return False
    dp = sorted((d for _, d in pattern.degree()), reverse=True)
    dh = sorted((d for _, d in host.degree()), reverse=True)
    if any(a > b for a, b in zip(dp, dh)):
        return False
    key = (_key(pattern), _key(host))
    if key not in _MONO_CACHE:
        _MONO_CACHE[key] = iso.GraphMatcher(host, pattern).subgraph_is_monomorphic()
    return _MONO_CACHE[key]


def check(json_bytes: bytes, g6_bytes: bytes, f74_json: bytes, f74_g6: bytes, l10: bytes,
          pin: bool = True) -> list[str]:
    fails: list[str] = []

    def fail(name: str, msg: str) -> None:
        fails.append(f"{name}: {msg}")

    # C1
    try:
        entries = json.loads(json_bytes)
    except ValueError as e:
        return [f"C1 json-shape: not JSON ({e})"]
    graphs = []
    if not isinstance(entries, list) or len(entries) != 398:
        fail("C1 json-shape", f"expected 398 entries, got {len(entries) if isinstance(entries, list) else type(entries)}")
    for i, edges in enumerate(entries if isinstance(entries, list) else []):
        ok = isinstance(edges, list) and edges and all(
            isinstance(e, list) and len(e) == 2 and all(isinstance(x, int) and x >= 0 for x in e)
            and e[0] != e[1] for e in edges)
        if not ok:
            fail("C1 json-shape", f"entry {i} is not a list of vertex pairs")
            graphs.append(None)
            continue
        pairs = [frozenset(e) for e in edges]
        if len(set(pairs)) != len(pairs):
            fail("C1 json-shape", f"entry {i} repeats an edge")
        g = graph_from_edges(edges)
        if any(d == 0 for _, d in g.degree()):
            fail("C1 json-shape", f"entry {i} has an isolated vertex")
        graphs.append(g)

    # C2
    lines = g6_bytes.split(b"\n")
    if not g6_bytes.endswith(b"\n"):
        fail("C2 g6-shape", "file does not end with a newline")
    lines = lines[:-1] if lines and lines[-1] == b"" else lines
    g6graphs = []
    if len(lines) != 398:
        fail("C2 g6-shape", f"expected 398 lines, got {len(lines)}")
    for i, line in enumerate(lines):
        try:
            g6graphs.append(nx.from_graph6_bytes(line))
        except Exception as e:  # noqa: BLE001 - any parse failure is a failure
            fail("C2 g6-shape", f"line {i} does not parse: {e}")
            g6graphs.append(None)

    # C3
    old = json.loads(f74_json)
    old_lines = f74_g6.split(b"\n")[:-1]
    for i in range(74):
        if i >= len(entries) or entries[i] != old[i]:
            fail("C3 first-74", f"JSON entry {i} differs from forbidden-74.json entry {i}")
        if i >= len(lines) or lines[i] != old_lines[i]:
            fail("C3 first-74", f"g6 line {i} differs from forbidden-74.g6 line {i}")
        if i < len(graphs) and i < len(g6graphs) and graphs[i] is not None and g6graphs[i] is not None:
            if not nx.is_isomorphic(graphs[i], g6graphs[i]):
                fail("C3 first-74", f"JSON entry {i} is not isomorphic to g6 line {i}")

    # C4
    l10_lines = l10.split(b"\n")[:-1]
    if len(l10_lines) != 324:
        fail("C4 last-324", f"L10.g6 has {len(l10_lines)} lines")
    for j, want in enumerate(l10_lines):
        i = 74 + j
        if i >= len(lines) or lines[i] != want:
            fail("C4 last-324", f"g6 line {i} is not L10 line {j}")
        if i >= len(graphs) or graphs[i] is None:
            continue
        ref = nx.from_graph6_bytes(want)
        same_nodes = set(graphs[i].nodes()) == set(ref.nodes()) == set(range(10))
        same_edges = {frozenset(e) for e in graphs[i].edges()} == {frozenset(e) for e in ref.edges()}
        if not (same_nodes and same_edges):
            fail("C4 last-324", f"JSON entry {i} is not the graph6 labelling of L10 line {j} ({want.decode()})")

    valid = [g for g in graphs if g is not None]
    # C5
    comp74 = Counter((g.number_of_nodes(), g.number_of_edges()) for g in graphs[:74] if g is not None)
    comp324 = Counter((g.number_of_nodes(), g.number_of_edges()) for g in graphs[74:] if g is not None)
    if dict(comp74) != COMPOSITION_74:
        fail("C5 composition", f"74-part composition {dict(comp74)}")
    if dict(comp324) != COMPOSITION_324:
        fail("C5 composition", f"324-part composition {dict(comp324)}")

    # C6
    buckets: dict[tuple, list[int]] = {}
    for i, g in enumerate(graphs):
        if g is None:
            continue
        key = (g.number_of_nodes(), g.number_of_edges(), nx.weisfeiler_lehman_graph_hash(g, iterations=4))
        buckets.setdefault(key, []).append(i)
    for members in buckets.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                if nx.is_isomorphic(graphs[members[x]], graphs[members[y]]):
                    fail("C6 non-isomorphic", f"entries {members[x]} and {members[y]} are isomorphic")

    # C7: GraphMatcher(host, pattern).subgraph_is_monomorphic() is True iff pattern is a
    # (not necessarily induced) subgraph of host.  Sanity of the direction first.
    k4, k3, c4 = nx.complete_graph(4), nx.complete_graph(3), nx.cycle_graph(4)
    if not iso.GraphMatcher(k4, k3).subgraph_is_monomorphic() or iso.GraphMatcher(c4, k3).subgraph_is_monomorphic():
        fail("C7 antichain", "networkx monomorphism direction is not what this check assumes")
    if not is_subgraph(k3, k4) or is_subgraph(k3, c4) or not is_subgraph(nx.path_graph(4), c4):
        fail("C7 antichain", "is_subgraph (prefilter + VF2) gives a wrong answer on K3/K4/C4/P4")
    idx = [i for i, g in enumerate(graphs) if g is not None]
    for a in idx:
        ga = graphs[a]
        for b in idx:
            if a == b:
                continue
            gb = graphs[b]
            if ga.number_of_nodes() > gb.number_of_nodes() or ga.number_of_edges() > gb.number_of_edges():
                continue
            if ga.number_of_nodes() == gb.number_of_nodes() and ga.number_of_edges() == gb.number_of_edges():
                continue   # a same-size subgraph is an isomorphic copy: C6's job
            if is_subgraph(ga, gb):
                fail("C7 antichain", f"entry {a} is a subgraph of entry {b}")

    # C8
    dist: Counter = Counter()
    for i, g in enumerate(graphs):
        if g is None:
            continue
        if min(d for _, d in g.degree()) < 2:
            fail("C8 patterns", f"entry {i} has a vertex of degree < 2")
        if not nx.is_biconnected(g):
            fail("C8 patterns", f"entry {i} is not 2-connected")
        dist.update(d for _, d in g.degree())
    if dict(dist) != DISTRIBUTION or sum(dist.values()) != 3875:
        fail("C8 patterns", f"size distribution {dict(sorted(dist.items()))} total {sum(dist.values())}")

    # C9
    if pin:
        hj, hg = hashlib.sha256(json_bytes).hexdigest(), hashlib.sha256(g6_bytes).hexdigest()
        if hj != PIN_JSON:
            fail("C9 hashes", f"forbidden-398.json sha256 {hj} != pinned {PIN_JSON}")
        if hg != PIN_G6:
            fail("C9 hashes", f"forbidden-398.g6 sha256 {hg} != pinned {PIN_G6}")
    return fails


def mutate_edge(entries: list, i: int) -> list:
    """Move one endpoint of the first edge of entry i to a vertex not yet adjacent (a new graph)."""
    out = json.loads(json.dumps(entries))
    edges = out[i]
    a, b = edges[0]
    n = max(max(e) for e in edges) + 1
    present = {frozenset(e) for e in edges}
    for c in range(n):
        if c not in (a, b) and frozenset((a, c)) not in present:
            edges[0] = [a, c]
            return out
    raise RuntimeError("no mutation available")


def self_test(json_bytes, g6_bytes, f74_json, f74_g6, l10) -> int:
    entries = json.loads(json_bytes)
    lines = g6_bytes.split(b"\n")[:-1]
    base = check(json_bytes, g6_bytes, f74_json, f74_g6, l10)   # also fills the VF2 memo
    print(f"unmutated input: {len(base)} failures (must be 0)")
    if base:
        return 1
    cases = []

    m = mutate_edge(entries, 200)
    cases.append(("one edge of entry 200 moved", json.dumps(m).encode(), g6_bytes, {"C4 last-324", "C9 hashes"}))
    m = json.loads(json_bytes); m[100], m[101] = m[101], m[100]
    cases.append(("entries 100 and 101 swapped", json.dumps(m).encode(), g6_bytes, {"C4 last-324", "C9 hashes"}))
    m = json.loads(json_bytes); m[5] = m[5][1:]
    cases.append(("an edge dropped from entry 5 (of the 74)", json.dumps(m).encode(), g6_bytes,
                  {"C3 first-74", "C5 composition", "C9 hashes"}))
    ls = list(lines); ls[80], ls[81] = ls[81], ls[80]
    cases.append(("g6 lines 80 and 81 swapped", json_bytes, b"\n".join(ls) + b"\n", {"C4 last-324", "C9 hashes"}))
    m = json.loads(json_bytes)
    perm = [3, 7, 1, 9, 0, 2, 8, 4, 6, 5]
    m[301] = sorted([sorted([perm[a], perm[b]]) for a, b in m[300]])
    cases.append(("entry 301 replaced by a relabelled copy of entry 300", json.dumps(m).encode(), g6_bytes,
                  {"C4 last-324", "C6 non-isomorphic", "C9 hashes"}))
    # entry 74+j (a 15-edge graph) plus one edge replaces a 16-edge member: now 74+j is a subgraph of it
    m = json.loads(json_bytes)
    small = next(i for i in range(74, 398) if len(m[i]) == 15)
    big = next(i for i in range(74, 398) if len(m[i]) == 16)
    present = {frozenset(e) for e in m[small]}
    extra = next([a, b] for a in range(10) for b in range(a + 1, 10) if frozenset((a, b)) not in present)
    m[big] = sorted(m[small] + [extra])
    cases.append((f"entry {big} replaced by entry {small} plus one edge", json.dumps(m).encode(), g6_bytes,
                  {"C4 last-324", "C7 antichain", "C9 hashes"}))
    m = json.loads(json_bytes); m[250] = sorted(m[250] + [[0, 9]] if [0, 9] not in m[250] else m[250] + [[1, 8]])
    cases.append(("an edge added to entry 250", json.dumps(m).encode(), g6_bytes,
                  {"C4 last-324", "C5 composition", "C8 patterns", "C9 hashes"}))
    cases.append(("trailing newline appended to the JSON", json_bytes + b"\n", g6_bytes, {"C9 hashes"}))

    bad = 0
    for name, jb, gb, expected in cases:
        fails = check(jb, gb, f74_json, f74_g6, l10)
        names = {f.split(":")[0] for f in fails}
        missing = expected - names
        status = "RED as required" if not missing else f"NOT RED for {sorted(missing)}"
        if missing:
            bad += 1
        print(f"mutation [{name}]: {status}; failing checks {sorted(names)}")
        for f in fails[:3]:
            print(f"    {f}")
    print(f"self-test: {len(cases) - bad} of {len(cases)} mutations turned the targeted checks red")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=DATA / "forbidden-398.json")
    ap.add_argument("--g6", type=Path, default=DATA / "forbidden-398.g6")
    ap.add_argument("--l10", type=Path, default=REPO / "research/gp-10/runs/B10-final-2026-09-25/L10.g6")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    jb, gb = a.json.read_bytes(), a.g6.read_bytes()
    f74_json, f74_g6 = (DATA / "forbidden-74.json").read_bytes(), (DATA / "forbidden-74.g6").read_bytes()
    l10 = a.l10.read_bytes()
    print(f"networkx {nx.__version__}; L10.g6 sha256 {hashlib.sha256(l10).hexdigest()}")
    if a.self_test:
        return self_test(jb, gb, f74_json, f74_g6, l10)
    fails = check(jb, gb, f74_json, f74_g6, l10)
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"RESULT: FAIL ({len(fails)} problems)")
        return 1
    print(f"forbidden-398.json sha256 {hashlib.sha256(jb).hexdigest()}")
    print(f"forbidden-398.g6   sha256 {hashlib.sha256(gb).hexdigest()}")
    print("C1..C9 all pass: 398 entries; 74 verbatim and isomorphic to their graph6; 324 identical to "
          "their L10 graph6 labelling; pairwise non-isomorphic; an antichain under the subgraph order; "
          "pattern sizes {2: 251, 3: 2474, 4: 920, 5: 192, 6: 34, 7: 4} = 3875")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
