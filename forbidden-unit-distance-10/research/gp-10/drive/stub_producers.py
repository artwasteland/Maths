"""Deterministic producer stubs used by the driver tests.

These records are intentionally not checker certificates.  They exercise the
driver's batching, resume, unknown, propagation, and exact-coverage paths
while the real embedder and refuter are developed in their own modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

try:
    from .graph6 import contains_subgraph, decode_graph6, load_graph6, save_graph6
except ImportError:
    from graph6 import contains_subgraph, decode_graph6, load_graph6, save_graph6  # type: ignore


def _contains_pattern(pattern: str, host: str) -> bool:
    pattern_n, pattern_mask = decode_graph6(pattern)
    host_n, host_mask = decode_graph6(host)
    return contains_subgraph(pattern_n, pattern_mask, host_n, host_mask)


@lru_cache(maxsize=1)
def _f9_graphs() -> tuple[str, ...]:
    source = Path(__file__).resolve().parents[1] / ".." / "unit-distance-22" / "data" / "forbidden-74.g6"
    return tuple(load_graph6(source.resolve()))


def _choice(mode: str, kind: str, graph: str, index: int) -> str:
    if mode == "all-embedded":
        return "embedded"
    if mode == "all-refuted":
        return "refuted"
    if mode == "control":
        forbidden = _f9_graphs()
        contains = any(_contains_pattern(pattern, graph) for pattern in forbidden)
        if kind == "embed":
            return "unknown" if contains else "embedded"
        return "refuted" if contains else "unknown"
    if mode == "unknown":
        return "unknown"
    if mode == "alternate":
        return ("embedded" if index % 2 == 0 else "unknown") if kind == "embed" else (
            "refuted" if index % 2 == 0 else "unknown"
        )
    digest = hashlib.sha256(graph.encode("ascii")).digest()
    if kind == "embed":
        return "embedded" if digest[0] & 1 else "unknown"
    return "refuted" if digest[0] & 1 else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("embed", "refute"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--unknown", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, required=True)
    parser.add_argument("--forbidden", type=Path)
    parser.add_argument("--refuted", type=Path)
    parser.add_argument(
        "--mode",
        choices=("all-embedded", "all-refuted", "unknown", "alternate", "hash", "control"),
        default="all-embedded",
    )
    parser.add_argument("--crash-after", type=int)
    args = parser.parse_args()
    graphs = load_graph6(args.input)
    records: list[dict[str, object]] = []
    unknown_lines: list[str] = []
    for index, graph in enumerate(graphs):
        if args.crash_after is not None and index >= args.crash_after:
            break
        verdict = _choice(args.mode, args.kind, graph, index)
        if verdict == "unknown":
            records.append(
                {
                    "g6": graph,
                    "verdict": "unknown",
                    "cert": {
                        "reason": "stub budget exhausted",
                        "budget": {"time_limit": args.time_limit},
                    },
                }
            )
            unknown_lines.append(graph)
        else:
            records.append(
                {
                    "g6": graph,
                    "verdict": verdict,
                    "cert": {"type": "stub", "mode": args.mode},
                }
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    save_graph6(args.unknown, unknown_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
