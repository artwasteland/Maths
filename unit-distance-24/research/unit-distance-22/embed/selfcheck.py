#!/usr/bin/env python3
"""Required exercised checks for the proof-producing embedder."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import time
from fractions import Fraction
from pathlib import Path

import networkx as nx

from exact_verify import CertificateError, verify_embedded_certificate
from proof_verify import ProofError, verify_refutation
from udembed import Graph, MOSER_EDGES, embed_graph, normal_edge, trace_to_first_l2


ROOT = Path(__file__).resolve().parents[1]


def graph6(graph: nx.Graph) -> str:
    return nx.to_graph6_bytes(graph, header=False).decode("ascii").strip()


def forbidden_worker(item: tuple[int, str]) -> tuple[int, str, str, dict]:
    index, code = item
    record = embed_graph(code, tries=0, seed=index + 1, max_states=100)
    if record["verdict"] == "refuted":
        verify_refutation(record)
    return index, code, record["verdict"], record


def first_l3(node: dict) -> dict | None:
    if node["move"]["kind"] == "L3":
        return node
    for child in node["children"]:
        found = first_l3(child)
        if found is not None:
            return found
    return None


def make_moser() -> nx.Graph:
    graph = nx.Graph()
    graph.add_edges_from(MOSER_EDGES)
    return nx.convert_node_labels_to_integers(graph, ordering="sorted")


def make_data_graph(item: dict, add_pair: bool = False) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(item["n"]))
    graph.add_edges_from(item["edges"])
    if add_pair:
        graph.add_edge(*item["pair"])
    return graph


def run(jobs: int) -> None:
    amp_codes = (ROOT / "sources/amp/anc/graph6.txt").read_text().splitlines()
    amp_records = []
    started = time.perf_counter()
    for code in amp_codes:
        record = embed_graph(code, tries=4)
        assert record["verdict"] == "embedded"
        assert verify_embedded_certificate(record)
        amp_records.append(record)
    print(f"AMP_EMBEDDED {len(amp_records)} VERIFIED {len(amp_records)} SECONDS {time.perf_counter() - started:.6f}")

    forbidden_codes = (ROOT / "data/forbidden-74.g6").read_text().splitlines()
    started = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
        forbidden_results = list(pool.map(forbidden_worker, enumerate(forbidden_codes), chunksize=1))
    counts = {
        verdict: sum(result[2] == verdict for result in forbidden_results)
        for verdict in ("refuted", "embedded", "unknown")
    }
    assert counts["embedded"] == 0
    assert counts["refuted"] + counts["unknown"] == 74
    unknown = [(index, code) for index, code, verdict, _ in forbidden_results if verdict == "unknown"]
    print(
        f"FORBIDDEN_REFUTED {counts['refuted']} UNKNOWN {counts['unknown']} "
        f"EMBEDDED {counts['embedded']} SECONDS {time.perf_counter() - started:.6f}"
    )
    print("FORBIDDEN_UNKNOWN_INDICES " + ",".join(str(index) for index, _ in unknown))
    print("FORBIDDEN_UNKNOWN_G6 " + ",".join(code for _, code in unknown))

    tu_data = json.loads((ROOT / "data/tu-gadgets.json").read_text())
    specials = (("MOSER", make_moser()), ("GADGET1_HOST", make_data_graph(tu_data[0], add_pair=True)))
    for name, graph in specials:
        record = embed_graph(graph6(graph))
        assert record["verdict"] == "embedded"
        assert verify_embedded_certificate(record)
        print(f"SPECIAL_{name} EMBEDDED VERIFIED N {graph.number_of_nodes()} M {graph.number_of_edges()}")

    for index, item in enumerate(tu_data, 1):
        graph = Graph.from_edges(item["n"], item["edges"])
        trace = trace_to_first_l2(graph, target_edge=item["pair"])
        hit = (
            trace[-1].get("kind") == "L2"
            and normal_edge(trace[-1]["forced_edge"]) == normal_edge(item["pair"])
        )
        assert hit
        print(
            f"TU_GADGET {index} TARGET {item['pair'][0]}-{item['pair'][1]} "
            f"MOVES {'>'.join(move['kind'] for move in trace)} TARGET_L2_INDEX {len(trace) - 1}"
        )

    false_certificate = copy.deepcopy(amp_records[2])
    old = Fraction(false_certificate["witness"]["coordinates"][0][0][0])
    false_certificate["witness"]["coordinates"][0][0][0] = str(old + 1)
    try:
        verify_embedded_certificate(false_certificate)
    except CertificateError as exc:
        print(f"MUTATION_EMBEDDED REJECTED {type(exc).__name__}")
    else:
        raise AssertionError("perturbed embedded certificate was accepted")

    k4 = nx.complete_graph(4)
    k4_record = embed_graph(graph6(k4), tries=0)
    assert k4_record["verdict"] == "refuted"
    assert verify_refutation(k4_record)
    l3_record = next(result[3] for result in forbidden_results if result[2] == "refuted" and first_l3(result[3]["witness"]["tree"]) is not None)
    false_proof = copy.deepcopy(l3_record)
    mutated_l3 = first_l3(false_proof["witness"]["tree"])
    assert mutated_l3 is not None
    mutated_l3["move"]["d"] = [0]
    try:
        verify_refutation(false_proof)
    except ProofError as exc:
        print(f"MUTATION_L3_D REJECTED {type(exc).__name__}: {exc}")
    else:
        raise AssertionError("corrupted L3 d was accepted")

    first = tu_data[0]
    doctored_edges = [edge for edge in first["edges"] if edge != [0, 3]]
    doctored = Graph.from_edges(first["n"], doctored_edges)
    doctored_trace = trace_to_first_l2(doctored, max_moves=10, target_edge=first["pair"])
    doctored_hit = (
        doctored_trace[-1].get("kind") == "L2"
        and normal_edge(doctored_trace[-1]["forced_edge"]) == normal_edge(first["pair"])
    )
    try:
        assert doctored_hit
    except AssertionError:
        print("MUTATION_TU RED DELETE_EDGE_0-3 TARGET_L2_NOT_REACHED")
    else:
        raise AssertionError("TU path mutation did not make the control red")

    codes_21 = [code for code in amp_codes if Graph.from_graph6(code).n == 21]
    for index, code in enumerate(codes_21, 1):
        started = time.perf_counter()
        record = embed_graph(code)
        assert verify_embedded_certificate(record)
        print(f"TIMING_21 {index} {code} SECONDS {time.perf_counter() - started:.6f}")
    print("SELF_CHECK PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    run(args.jobs)


if __name__ == "__main__":
    main()
