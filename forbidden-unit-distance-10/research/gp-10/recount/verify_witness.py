#!/usr/bin/env python3
"""Replay every streamed subgraph witness without importing matcher code."""

import argparse
import gzip
import sys


def graph6(value):
    pos = 10 if value.startswith(">>graph6<<") else 0
    if pos >= len(value) or not 63 <= ord(value[pos]) <= 125:
        raise ValueError("unsupported graph6 order")
    n = ord(value[pos]) - 63
    pos += 1
    adj = [0] * n
    bit = 0
    for _ in range((n * (n - 1) // 2 + 5) // 6):
        if pos >= len(value):
            raise ValueError("truncated graph6")
        chunk = ord(value[pos]) - 63
        pos += 1
        for shift in range(5, -1, -1):
            if bit == n * (n - 1) // 2:
                break
            if chunk & (1 << shift):
                seen = 0
                for v in range(1, n):
                    width = v
                    if bit < seen + width:
                        u = bit - seen
                        adj[u] |= 1 << v
                        adj[v] |= 1 << u
                        break
                    seen += width
            bit += 1
    return n, adj


def load_patterns(path):
    patterns = []
    with open(path, encoding="ascii") as source:
        for raw in source:
            value = raw.strip()
            if value and not value.startswith(">>graph6<<"):
                patterns.append(graph6(value))
    return patterns


def fail(line_no, reason):
    raise ValueError(f"line {line_no}: {reason}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patterns", required=True)
    parser.add_argument("--witness", required=True)
    args = parser.parse_args()
    patterns = load_patterns(args.patterns)
    replayed = 0
    try:
        with gzip.open(args.witness, "rt", encoding="ascii") as source:
            for line_no, raw in enumerate(source, 1):
                fields = raw.rstrip("\n").split("\t")
                if len(fields) != 3:
                    fail(line_no, "expected host, member index, map")
                host, index_text, map_text = fields
                try:
                    index = int(index_text)
                except ValueError:
                    fail(line_no, "member index is not an integer")
                if not 0 <= index < len(patterns):
                    fail(line_no, "member index is outside the pattern list")
                try:
                    mapping = [int(item) for item in map_text.split(",")]
                    host_n, host_adj = graph6(host)
                except ValueError as error:
                    fail(line_no, str(error))
                pattern_n, pattern_adj = patterns[index]
                if len(mapping) != pattern_n:
                    fail(line_no, "map length does not match the pattern")
                if len(set(mapping)) != len(mapping):
                    fail(line_no, "map is not injective")
                if any(vertex < 0 or vertex >= host_n for vertex in mapping):
                    fail(line_no, "map leaves the host vertex range")
                for u in range(pattern_n):
                    for v in range(u + 1, pattern_n):
                        if pattern_adj[u] & (1 << v):
                            if not (host_adj[mapping[u]] & (1 << mapping[v])):
                                fail(line_no, f"pattern edge {u},{v} is absent in the host")
                replayed += 1
    except (OSError, EOFError, ValueError) as error:
        print(f"REJECT: {error}", file=sys.stderr)
        return 1
    print(f"replayed={replayed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
