#!/usr/bin/env python3
"""Check JSON-labelled witnesses, exact ordered coverage, and frozen list bytes.

This verifier imports neither C matcher nor udfilter code.
Only required edges are checked, so extra host edges remain allowed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time


def graph6(value):
    if not value or not 63 <= value[0] <= 74:
        raise ValueError('invalid graph6 order')
    n = value[0] - 63
    bits = n * (n - 1) // 2
    if len(value) != 1 + (bits + 5) // 6:
        raise ValueError('invalid graph6 length')
    if any(not 63 <= c <= 126 for c in value[1:]):
        raise ValueError('invalid graph6 character')
    if bits % 6 and (value[-1] - 63) & ((1 << (6 - bits % 6)) - 1):
        raise ValueError('invalid graph6 padding')
    edges = []
    bit = 0
    for v in range(1, n):
        for u in range(v):
            if (value[1 + bit // 6] - 63) & (1 << (5 - bit % 6)):
                edges.append((u, v))
            bit += 1
    return n, edges


def encode(n, edges):
    payload = [0] * ((n * (n - 1) // 2 + 5) // 6)
    for u, v in edges:
        u, v = sorted((u, v))
        bit = v * (v - 1) // 2 + u
        payload[bit // 6] |= 1 << (5 - bit % 6)
    return bytes([n + 63] + [c + 63 for c in payload])


def load_patterns(path):
    rows = json.loads(Path(path).read_bytes())
    patterns = []
    for edges in rows:
        if not edges or any(len(e) != 2 or any(type(v) is not int for v in e) for e in edges):
            raise ValueError('invalid pattern edge list')
        n = 1 + max(max(e) for e in edges)
        normal = {tuple(sorted(e)) for e in edges}
        if n > 10 or any(u < 0 or u >= v for u, v in normal) or len(normal) != len(edges):
            raise ValueError('invalid pattern graph')
        patterns.append((n, sorted(normal)))
    return patterns


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def replay(pattern_path, inputs, survivors, witnesses, order=11):
    patterns = load_patterns(pattern_path)
    # Precompute graph6 bit addresses; replay only reads edges named by each certificate.
    addresses = {}
    for u in range(order):
        for v in range(order):
            a, b = sorted((u, v))
            bit = b * (b - 1) // 2 + a
            addresses[u, v] = (1 + bit // 6, 1 << (5 - bit % 6))
    bits = order * (order - 1) // 2
    width = (bits + 5) // 6
    padding = (6 - bits % 6) % 6
    last = bytes(v + 63 for v in range(0, 64, 1 << padding))
    host_rule = re.compile(re.escape(bytes([order + 63])) +
                           rb'[\x3f-\x7e]{' + str(width - 1).encode() + b'}[' +
                           re.escape(last) + rb']\n')
    count = kept = removed = 0
    input_hash = hashlib.sha256()
    union_hash = hashlib.sha256()
    survivor_hash = hashlib.sha256()
    witness_hash = hashlib.sha256()
    start = time.monotonic()
    with Path(inputs).open('rb') as hosts, Path(survivors).open('rb') as accepted, \
            Path(witnesses).open('rb') as rejected:
        survivor = accepted.readline()
        witness = rejected.readline()
        witness_host = witness.split(b'\t', 1)[0] + b'\n' if witness else b''
        for count, host in enumerate(hosts, 1):
            if not host_rule.fullmatch(host):
                raise ValueError(f'input {count}: invalid graph6')
            input_hash.update(host)
            is_survivor = survivor == host
            is_removed = witness_host == host
            if is_survivor == is_removed:
                reason = 'both output classes' if is_survivor else 'neither output class'
                raise ValueError(f'coverage: input {count} occurs in {reason}')
            if is_survivor:
                survivor_hash.update(survivor)
                union_hash.update(survivor)
                survivor = accepted.readline()
                kept += 1
                continue
            fields = witness.rstrip(b'\n').split(b'\t')
            line_no = removed + 1
            if len(fields) != 3 or not witness.endswith(b'\n'):
                raise ValueError(f'line {line_no}: expected host, member index, map')
            try:
                index = int(fields[1])
                mapping = tuple(map(int, fields[2].split(b',')))
            except ValueError:
                raise ValueError(f'line {line_no}: member index or map is not an integer') from None
            if not 0 <= index < len(patterns):
                raise ValueError(f'line {line_no}: member index is outside the pattern list')
            n, edges = patterns[index]
            if len(mapping) != n:
                raise ValueError(f'line {line_no}: map length does not match the pattern')
            if len(set(mapping)) != n:
                raise ValueError(f'line {line_no}: map is not injective')
            if any(v < 0 or v >= order for v in mapping):
                raise ValueError(f'line {line_no}: map leaves the host vertex range')
            for u, v in edges:
                byte, mask = addresses[mapping[u], mapping[v]]
                if not (host[byte] - 63) & mask:
                    raise ValueError(f'line {line_no}: pattern edge {u},{v} is absent in the host')
            witness_hash.update(witness)
            union_hash.update(witness_host)
            removed += 1
            witness = rejected.readline()
            witness_host = witness.split(b'\t', 1)[0] + b'\n' if witness else b''
        if survivor or witness:
            raise ValueError('coverage: output contains a host beyond the input stream')
    return {'status': 'ACCEPT', 'input': count, 'survivors': kept, 'replayed': removed,
            'input_sha256': input_hash.hexdigest(), 'union_sha256': union_hash.hexdigest(),
            'survivors_sha256': survivor_hash.hexdigest(),
            'witness_sha256': witness_hash.hexdigest(),
            'wall_seconds': round(time.monotonic() - start, 6)}


def compare(expected, actual):
    paths = [Path(expected), Path(actual)]
    counts = []
    for path in paths:
        previous = b''
        count = 0
        with path.open('rb') as source:
            for count, line in enumerate(source, 1):
                if not line.endswith(b'\n'):
                    raise ValueError('list format: missing trailing newline')
                graph6(line[:-1])
                if line <= previous:
                    raise ValueError('list format: entries are not strictly bytewise sorted')
                previous = line
        counts.append(count)
    # Bytes, not counts or set cardinalities, decide acceptance.
    with paths[0].open('rb') as left, paths[1].open('rb') as right:
        while True:
            a, b = left.read(1 << 20), right.read(1 << 20)
            if a != b:
                raise ValueError('list equality: canonical survivor bytes differ')
            if not a:
                break
    return {'status': 'ACCEPT', 'expected_count': counts[0], 'actual_count': counts[1],
            'expected_sha256': sha256(expected), 'actual_sha256': sha256(actual)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='kind', required=True)
    witness = subparsers.add_parser('replay')
    witness.add_argument('--patterns', required=True)
    witness.add_argument('--inputs', required=True)
    witness.add_argument('--survivors', required=True)
    witness.add_argument('--witnesses', required=True)
    witness.add_argument('--order', type=int, default=11)
    lists = subparsers.add_parser('compare')
    lists.add_argument('expected')
    lists.add_argument('actual')
    args = parser.parse_args()
    try:
        if args.kind == 'replay':
            result = replay(args.patterns, args.inputs, args.survivors, args.witnesses, args.order)
        else:
            result = compare(args.expected, args.actual)
    except (OSError, ValueError) as error:
        print(f'REJECT: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
