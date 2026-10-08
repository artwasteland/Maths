#!/usr/bin/env python3
"""Resolve the frozen GP-10 embedding stream to direct exact embeddings.

The public ``EmbeddingIndex`` is deliberately an in-memory index: the compressed
input is only 45 MiB and loading it avoids introducing another generated artifact.
Coordinates are not copied until a result is requested.  An E-ptr map maps the
current graph's vertices into its target, so resolving a chain is just map
composition followed by one restriction of the terminal coordinate list.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time
from typing import Iterator


HERE = Path(__file__).resolve().parent
GP10 = HERE.parent.parent / "gp-10"
DEFAULT_RECORDS = GP10 / "cloud/lean3/records.jsonl.gz"
DEFAULT_B10 = GP10 / "data/B10.g6"


class IndexError(ValueError):
    """The frozen record graph or a requested key is invalid."""


class EmbeddingIndex:
    """Random-access and streaming view of GP-10's resolved E-exact records."""

    def __init__(self, records: Path = DEFAULT_RECORDS, b10: Path = DEFAULT_B10):
        self.records_path, self.b10_path = Path(records), Path(b10)
        self._records: dict[str, dict] = {}
        self._b10 = frozenset(self.b10_path.read_text(encoding="ascii").splitlines())
        with gzip.open(self.records_path, "rt", encoding="utf-8") as source:
            for line_no, line in enumerate(source, 1):
                record = json.loads(line)
                code = record.get("g6")
                if not isinstance(code, str) or code in self._records:
                    raise IndexError(f"bad or duplicate graph6 at line {line_no}")
                if code not in self._b10:
                    raise IndexError(f"record outside B10 at line {line_no}: {code}")
                # The frozen stream covers all B10; this index intentionally
                # exposes only its embedded portion.
                if record.get("verdict") == "embedded":
                    self._records[code] = record["cert"]
        self._cache: dict[str, tuple[str, tuple[int, ...], int]] = {}

    def __len__(self) -> int:
        return len(self._records)

    def _route(self, code: str) -> tuple[str, tuple[int, ...], int]:
        """Return terminal key, source-to-terminal map, and pointer count."""
        if code in self._cache:
            return self._cache[code]
        if code not in self._records:
            raise KeyError(code)
        path: list[tuple[str, tuple[int, ...]]] = []
        current, composed = code, tuple(range(10))
        seen: set[str] = set()
        while True:
            if current in seen:
                raise IndexError(f"pointer cycle from {code}: {current}")
            seen.add(current)
            cert = self._records.get(current)
            if cert is None:
                raise IndexError(f"missing pointer target from {code}: {current}")
            kind = cert.get("type")
            if kind == "exact":
                result = (current, composed, len(path))
                self._cache[code] = result
                return result
            if kind != "super":
                raise IndexError(f"unexpected certificate type for {current}: {kind!r}")
            raw = cert.get("map")
            if (not isinstance(raw, list) or len(raw) != 10 or
                    any(type(v) is not int or not 0 <= v < 10 for v in raw)):
                raise IndexError(f"invalid pointer map for {current}")
            if len(set(raw)) != 10:
                raise IndexError(f"non-injective pointer map for {current}")
            step = tuple(raw)
            path.append((current, composed))
            composed = tuple(step[v] for v in composed)
            current = cert.get("g6")
            if not isinstance(current, str):
                raise IndexError(f"invalid pointer target for {path[-1][0]}")

    def resolve(self, code: str) -> dict:
        """Return an ordinary E-exact certificate in ``code``'s own labels."""
        terminal, mapping, _ = self._route(code)
        exact = self._records[terminal]
        coords = exact.get("coords")
        if not isinstance(coords, list) or len(coords) != 10:
            raise IndexError(f"invalid terminal coordinates for {terminal}")
        return {"type": "exact", "field": exact["field"],
                "coords": [coords[v] for v in mapping]}

    def record(self, code: str) -> dict:
        return {"g6": code, "verdict": "embedded", "cert": self.resolve(code)}

    def stream(self) -> Iterator[dict]:
        """Yield all embedded B10 records in canonical graph6 byte order."""
        for code in sorted(self._records):
            yield self.record(code)

    def chain_lengths(self) -> Counter[int]:
        return Counter(self._route(code)[2] for code in self._records)


def compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--b10", type=Path, default=DEFAULT_B10)
    sub = parser.add_subparsers(dest="command", required=True)
    lookup = sub.add_parser("lookup", help="write one direct embedded record")
    lookup.add_argument("g6")
    sub.add_parser("stream", help="write all direct records as JSONL")
    sub.add_parser("stats", help="resolve all records and report chain lengths")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    index = EmbeddingIndex(args.records, args.b10)
    if args.command == "lookup":
        print(compact_json(index.record(args.g6)))
    elif args.command == "stream":
        for record in index.stream():
            print(compact_json(record))
    else:
        lengths = index.chain_lengths()
        print(compact_json({"resolved": len(index),
                            "pointer_chain_lengths": {str(k): lengths[k] for k in sorted(lengths)},
                            "seconds": time.perf_counter() - started}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
