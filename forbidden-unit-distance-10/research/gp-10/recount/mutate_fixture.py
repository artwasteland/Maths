#!/usr/bin/env python3
"""Make small one-field negative fixtures for the independent controls."""

import argparse
import gzip


def mutate_witness(source_path, target_path):
    with gzip.open(source_path, "rt", encoding="ascii") as source:
        first = source.readline()
        rest = source.read()
    fields = first.rstrip("\n").split("\t")
    mapping = fields[2].split(",")
    if len(mapping) < 2:
        raise ValueError("witness map has fewer than two vertices")
    mapping[1] = mapping[0]
    fields[2] = ",".join(mapping)
    with gzip.open(target_path, "wt", encoding="ascii", newline="") as target:
        target.write("\t".join(fields) + "\n")
        target.write(rest)


def mutate_list(source_path, target_path):
    with open(source_path, "rb") as source:
        data = source.read()
    lines = data.splitlines(keepends=True)
    if not lines:
        raise ValueError("graph list is empty")
    lines[0] = lines[0].replace(b"?", b"@", 1)
    with open(target_path, "wb") as target:
        target.write(b"".join(lines))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="kind", required=True)
    witness = subparsers.add_parser("witness")
    witness.add_argument("source")
    witness.add_argument("target")
    graph_list = subparsers.add_parser("list")
    graph_list.add_argument("source")
    graph_list.add_argument("target")
    args = parser.parse_args()
    if args.kind == "witness":
        mutate_witness(args.source, args.target)
    else:
        mutate_list(args.source, args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
