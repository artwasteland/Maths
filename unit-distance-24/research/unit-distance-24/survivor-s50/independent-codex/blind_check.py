#!/usr/bin/env python3
"""Independent graph6 decoding and exhaustive non-induced subgraph search."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import networkx as nx

ROOT = Path(__file__).resolve().parent
KERNEL = Path('<repo>/research/unit-distance-22/check/udcheck.py')
sys.dont_write_bytecode = True


def decode(code):
    data = code.encode('ascii')
    assert all(63 <= c <= 126 for c in data)
    if data[0] != 126:
        n, offset = data[0] - 63, 1
    elif data[1] != 126:
        n, offset = 0, 4
        for c in data[1:4]:
            n = n * 64 + c - 63
    else:
        n, offset = 0, 8
        for c in data[2:8]:
            n = n * 64 + c - 63
    bit_count = n * (n - 1) // 2
    assert len(data) == offset + (bit_count + 5) // 6
    payload = 0
    for c in data[offset:]:
        payload = payload * 64 + c - 63
    padding = 6 * (len(data) - offset) - bit_count
    assert payload & ((1 << padding) - 1) == 0
    edges = set()
    for v in range(n):
        for u in range(v):
            index = v * (v - 1) // 2 + u
            if (payload >> (bit_count + padding - index - 1)) & 1:
                edges.add((u, v))
    return n, edges


def neighbors(n, edges):
    result = [0] * n
    for u, v in edges:
        result[u] |= 1 << v
        result[v] |= 1 << u
    return result


def bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def find_subgraph(hn, he, gn, ge):
    """Enumerates injective maps, with safe degree/edge-support pruning.

    A domain only loses candidates that violate an edge, injectivity against an
    already assigned vertex, or the necessary host-degree bound. At each branch
    every remaining candidate is visited. Nonedges impose no restrictions.
    """
    ha, ga = neighbors(hn, he), neighbors(gn, ge)
    domains = [sum(1 << v for v in range(gn)
                   if ga[v].bit_count() >= ha[u].bit_count()) for u in range(hn)]
    mapping = [-1] * hn
    calls = 0

    def visit(dom, used):
        nonlocal calls
        calls += 1
        if all(v >= 0 for v in mapping):
            return mapping.copy()
        remaining = [u for u in range(hn) if mapping[u] < 0]
        dom = dom.copy()
        for u in remaining:
            dom[u] &= ~used
            for w in bits(ha[u]):
                if mapping[w] >= 0:
                    dom[u] &= ga[mapping[w]]
            if not dom[u]:
                return None
        # Arc consistency on required edges among unassigned vertices.
        changed = True
        while changed:
            changed = False
            for u in remaining:
                for w in bits(ha[u]):
                    if mapping[w] >= 0:
                        continue
                    supported = sum(1 << v for v in bits(dom[u]) if ga[v] & dom[w])
                    if supported != dom[u]:
                        dom[u] = supported
                        changed = True
                        if not supported:
                            return None
        # The union must have enough vertices for an injection.
        union = 0
        for u in remaining:
            union |= dom[u]
        if union.bit_count() < len(remaining):
            return None
        u = min(remaining, key=lambda u: (dom[u].bit_count(), -ha[u].bit_count(), u))
        for v in bits(dom[u]):
            mapping[u] = v
            result = visit(dom, used | (1 << v))
            if result is not None:
                return result
            mapping[u] = -1
        return None

    return visit(domains, 0), calls


def nx_graph(code):
    return nx.from_graph6_bytes(code.encode('ascii'))


def main():
    spec = importlib.util.spec_from_file_location('blind_frozen_kernel', KERNEL)
    kernel = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = kernel
    spec.loader.exec_module(kernel)
    codes = (ROOT / 'survivor.g6').read_text().splitlines()
    assert len(codes) == 1
    gcode = codes[0]
    gn, ge = decode(gcode)
    gnx = nx_graph(gcode)

    def agree(code):
        n, edges = decode(code)
        graph = nx_graph(code)
        frozen = kernel.decode_graph6(code)
        assert set(graph.nodes) == set(range(n))
        assert {tuple(sorted(e)) for e in graph.edges} == edges == frozen.edges
        assert frozen.n == n
        assert nx.to_graph6_bytes(graph, header=False).decode().strip() == code
        return n, edges

    agree(gcode)
    out = ROOT / 'mappings'
    out.mkdir(exist_ok=True)
    summary = {
        'host_g6': gcode, 'host_vertices': gn, 'host_edges': len(ge),
        'host_degree_sequence_descending': sorted((d for _, d in gnx.degree), reverse=True),
        'host_degrees_vertex_order': [gnx.degree[v] for v in range(gn)],
        'host_sha256': hashlib.sha256((ROOT / 'survivor.g6').read_bytes()).hexdigest(),
        'kernel_sha256': hashlib.sha256(KERNEL.read_bytes()).hexdigest(),
        'decoder_agreement': 'own decoder = NetworkX = frozen udcheck, exact labelled edges',
        'records': [],
    }
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}), flush=True)
    for path in sorted((ROOT / 'records').glob('*')):
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert set(record) == {'g6', 'verdict', 'cert'}
        hn, he = agree(record['g6'])
        assert hn == 11 and record['verdict'] == 'refuted'
        started = time.monotonic()
        mapping, calls = find_subgraph(hn, he, gn, ge)
        hnx = nx_graph(record['g6'])
        # Distinct implementation and decoder independently check the verdict.
        vf2 = nx.algorithms.isomorphism.GraphMatcher(gnx, hnx).subgraph_is_monomorphic()
        assert vf2 == (mapping is not None)
        row = {'file': path.name, 'g6': record['g6'], 'vertices': hn, 'edges': len(he),
               'embeds': mapping is not None, 'mapping': mapping, 'search_calls': calls,
               'seconds': time.monotonic() - started, 'networkx_monomorphism_agrees': True,
               'record_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if mapping is not None:
            saved = out / (path.name + '.json')
            saved.write_text(json.dumps({'record': path.name, 'source_g6': record['g6'],
                                        'target_g6': gcode, 'indexing': 'zero-based',
                                        'map_H_to_G': mapping}, indent=2) + '\n')
            # Read back the artifact and test injection and every labelled edge.
            witness = json.loads(saved.read_text())['map_H_to_G']
            assert len(witness) == hn and len(set(witness)) == hn
            assert all(type(v) is int and v in gnx for v in witness)
            assert all(gnx.has_edge(witness[u], witness[v]) for u, v in hnx.edges)
            row['mapping_independently_verified'] = True
        summary['records'].append(row)
        (ROOT / 'search-results.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
