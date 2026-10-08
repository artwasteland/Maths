"""Graph decoding, canonicalization, and non-induced subgraph maps."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import networkx as nx

MODULE = Path(__file__).resolve().parent
ROOT = MODULE.parents[2]
UD = ROOT / "research/unit-distance-22"
SCRATCH = Path("/tmp/gp10-refute")
sys.dont_write_bytecode = True

def seed(code):
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest(), "big")

def decode(code):
    g = nx.from_graph6_bytes(code.encode("ascii"))
    return len(g), frozenset(tuple(sorted(e)) for e in g.edges())

def encode(n, edges):
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(edges)
    return nx.to_graph6_bytes(g, header=False).decode().strip()

def canonical(codes):
    if not codes:
        return []
    for code in codes:
        decode(code)
    result = subprocess.run(["nauty-labelg", "-q"], input="\n".join(codes) + "\n",
                            text=True, capture_output=True, timeout=30)
    out = result.stdout.splitlines()
    if result.returncode or len(out) != len(codes):
        raise ValueError("canonicalization failed: " + result.stderr[:200])
    for code in out:
        decode(code)
    return out

def patterns(edge_lists):
    result = []
    for edges in edge_lists:
        if not isinstance(edges, list) or not edges:
            raise ValueError("forbidden pattern must have a nonempty edge list")
        es = set()
        for pair in edges:
            if (not isinstance(pair, list) or len(pair) != 2 or
                any(type(x) is not int or x < 0 for x in pair) or pair[0] == pair[1]):
                raise ValueError("invalid forbidden edge")
            es.add(tuple(sorted(pair)))
        result.append((max(max(e) for e in es) + 1, frozenset(es)))
    return result

def validate_forbidden(forbidden):
    full = patterns(json.loads((UD / "data/forbidden-74.json").read_text()))
    if list(forbidden) != full[:len(forbidden)] or len(forbidden) > len(full):
        raise ValueError("forbidden list must be a prefix of forbidden-74.json")

_F9_CANONICAL = None

def forbidden_canonical():
    # Call in the parent before entering an isolated worker.
    global _F9_CANONICAL
    if _F9_CANONICAL is None:
        _F9_CANONICAL = canonical((UD / "data/forbidden-74.g6").read_text().splitlines())
    return _F9_CANONICAL

def verify_sub(code, cert, forbidden, known):
    if set(cert) not in ({"type", "g6", "map"}, {"type", "g6", "map", "index"}):
        raise ValueError("sub: invalid fields")
    h = cert["g6"]
    if "index" in cert:
        j = cert["index"]
        if type(j) is not int or not 0 <= j < len(forbidden):
            raise ValueError("sub: forbidden index is not in force")
        if h != forbidden_canonical()[j]:
            raise ValueError("sub: target does not equal indexed forbidden graph")
    elif h == code or h not in known:
        raise ValueError("sub: unaccepted or self reference")
    check_map(decode(h), decode(code), cert["map"], "sub map")

def maps(pattern, target):
    pn, pe = pattern
    n, edges = target
    if pn > n or len(pe) > len(edges):
        return
    pa, ta = [set() for _ in range(pn)], [set() for _ in range(n)]
    for u, v in pe:
        pa[u].add(v); pa[v].add(u)
    for u, v in edges:
        ta[u].add(v); ta[v].add(u)
    domains = [set(v for v in range(n) if len(ta[v]) >= len(pa[u])) for u in range(pn)]
    mapping, used = {}, set()
    def search():
        if len(mapping) == pn:
            yield [mapping[u] for u in range(pn)]
            return
        choices = []
        for u in range(pn):
            if u in mapping:
                continue
            candidates = domains[u] - used
            for w in pa[u] & mapping.keys():
                candidates &= ta[mapping[w]]
            choices.append((len(candidates), -len(pa[u] & mapping.keys()), -len(pa[u]), u, candidates))
        _, _, _, u, candidates = min(choices, key=lambda x: x[:4])
        for v in sorted(candidates):
            mapping[u] = v; used.add(v)
            yield from search()
            used.remove(v); del mapping[u]
    yield from search()

def check_map(pattern, target, mapping, reason="map"):
    pn, pe = pattern
    n, edges = target
    if (not isinstance(mapping, list) or len(mapping) != pn or
        any(type(v) is not int or not 0 <= v < n for v in mapping) or len(set(mapping)) != pn):
        raise ValueError(reason + ": not injective")
    if any(tuple(sorted((mapping[u], mapping[v]))) not in edges for u, v in pe):
        raise ValueError(reason + ": not edge-preserving")

def gadgets():
    return json.loads((UD / "data/tu-gadgets.json").read_text())

_KERNEL = None

def kernel():
    global _KERNEL
    if _KERNEL is None:
        spec = importlib.util.spec_from_file_location("gp10_trusted_udcheck", UD / "check/udcheck.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _KERNEL = module
    return _KERNEL

def verify_tree(code, cert):
    if set(cert) != {"type", "witness"} or cert["type"] != "tree":
        raise ValueError("tree: invalid fields")
    k = kernel()
    return k.verify_refutation(k.decode_graph6(code), cert["witness"], "tree")

def verify_tu(code, cert, forbidden, known):
    if set(cert) != {"type", "steps", "end"} or cert["type"] != "tu":
        raise ValueError("tu: invalid fields")
    if not isinstance(cert["steps"], list) or not cert["steps"]:
        raise ValueError("tu: steps must be nonempty")
    n, initial = decode(code)
    edges = set(initial)
    gs = gadgets()
    for step in cert["steps"]:
        if set(step) != {"gadget", "map", "pair"}:
            raise ValueError("tu step: invalid fields")
        k = step["gadget"]
        if type(k) is not int or not 0 <= k < len(gs):
            raise ValueError("tu step: invalid gadget")
        g = gs[k]
        pattern = (g["n"], frozenset(tuple(e) for e in g["edges"]))
        check_map(pattern, (n, edges), step["map"], "tu step map")
        pair = sorted(step["map"][i] for i in g["pair"])
        if step["pair"] != pair or tuple(pair) in edges:
            raise ValueError("tu step: pair is not the missing distinguished pair")
        edges.add(tuple(pair))
    end = cert["end"]
    if set(end) == {"forbidden", "map"}:
        j = end["forbidden"]
        if type(j) is not int or not 0 <= j < len(forbidden):
            raise ValueError("tu end: forbidden index is not in force")
        pattern = forbidden[j]
    elif set(end) == {"refuted", "map"}:
        h = end["refuted"]
        if h == code or h not in known:
            raise ValueError("tu end: unaccepted or self reference")
        pattern = decode(h)
    else:
        raise ValueError("tu end: missing terminal refutation")
    check_map(pattern, (n, edges), end["map"], "tu end map")

def tu_search(code, forbidden, known):
    n, initial = decode(code)
    edges, steps = set(initial), []
    gs = gadgets()
    while True:
        for j, pattern in enumerate(forbidden):
            mapping = next(maps(pattern, (n, edges)), None)
            if mapping is not None:
                if not steps:
                    h = forbidden_canonical()[j]
                    return {"type": "sub", "g6": h, "index": j,
                            "map": next(maps(decode(h), (n, edges)))}
                return {"type": "tu", "steps": steps, "end": {"forbidden": j, "map": mapping}}
        for h in sorted(known):
            if h == code:
                continue
            mapping = next(maps(decode(h), (n, edges)), None)
            if mapping is not None:
                if not steps:
                    return {"type": "sub", "g6": h, "map": mapping}
                return {"type": "tu", "steps": steps, "end": {"refuted": h, "map": mapping}}
        added = False
        for k, g in enumerate(gs):
            pattern = (g["n"], frozenset(tuple(e) for e in g["edges"]))
            for mapping in maps(pattern, (n, edges)):
                pair = sorted(mapping[v] for v in g["pair"])
                if tuple(pair) in edges:
                    continue
                steps.append({"gadget": k, "map": mapping, "pair": pair})
                edges.add(tuple(pair)); added = True
                break
            if added:
                break
        if not added:
            return None
