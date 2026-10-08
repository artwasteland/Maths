"""The landed extender, plus deterministic one-edge alternative base placements."""
from common import *
from functools import lru_cache
from graph6 import canonicalize, decode_graph6, adjacency_dict, iter_edges, pair_index

# Load explicitly because GP-10 has modules with the same short names.
load("index", GP11 / "embed/index.py")
ext = load("pipeline_degree_two", GP11 / "embed/extend.py")
gp_poly = ext.gp_poly


@lru_cache(maxsize=1)
def index():
    return ext.EmbeddingIndex()


def gp_output(code, output, points):
    from generic_exact import gp_output as parse
    return parse(code, output, points)


def search(code, seconds, directory, ck, alternatives=False):
    directory.mkdir(parents=True, exist_ok=True)
    if not alternatives:
        runner = ext.Extender(index(), ck, directory, seconds=seconds,
                              attempt_seconds=seconds if seconds > 3 else 1)
        record, detail = runner.run(code)
        if detail.get("stop"):
            raise MemoryFloor(record["cert"]["reason"])
        return (record["cert"] if record["verdict"] == "embedded" else None), detail
    start = time.monotonic()
    n, mask = decode_graph6(code)
    adjacency = adjacency_dict(n, mask)
    detail = {"method": "one_edge_alternative_B10_bases", "attempts": [], "lookups": 0}
    for vertex in range(n):
        if len(adjacency[vertex]) != 2:
            continue
        keep = [u for u in range(n) if u != vertex]
        reverse = {old: new for new, old in enumerate(keep)}
        small = sum(1 << pair_index(10, reverse[a], reverse[b]) for a, b in iter_edges(n, mask) if vertex not in (a, b))
        degrees = [len(v) for v in adjacency_dict(10, small).values()]
        pairs = [(a, b) for b in range(10) for a in range(b) if not small >> pair_index(10, a, b) & 1]
        pairs.sort(key=lambda p: (min(degrees[a] for a in p), sum(degrees[a] for a in p), p))
        for a, b in pairs:
            left = seconds - (time.monotonic()-start)
            if left <= 0:
                return None, dict(detail, reason="alternative_base_budget")
            base = canonicalize(10, small | 1 << pair_index(10, a, b))
            detail["lookups"] += 1
            try:
                exact = index().resolve(base.g6)
            except KeyError:
                continue
            cert = {"type": "exact", "field": exact["field"],
                    "coords": [exact["coords"][base.old_to_new[v]] for v in range(10)]}
            attempt = {"vertex": vertex, "added_edge": [keep[a], keep[b]], "base": base.g6}
            try:
                candidate, diagnostics = ext.extend_exact(code, cert, vertex, keep, adjacency[vertex], directory,
                                                           seconds=min(6, left))
                attempt.update(diagnostics, reason="proposal")
                detail["attempts"].append(attempt)
                return candidate, detail
            except (ext.ExtensionFailure, ext.Deadline, Exception) as exc:
                attempt["reason"] = type(exc).__name__ + ":" + str(exc)[-250:]
            detail["attempts"].append(attempt)
    return None, dict(detail, reason="alternative_bases_exhausted")
