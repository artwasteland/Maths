#!/usr/bin/env python3
"""Compare two sorted canonical graph6 lists and print a full difference."""

import argparse
import hashlib
import sys


def read_bytes(path):
    with open(path, "rb") as source:
        return source.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("expected")
    parser.add_argument("actual")
    args = parser.parse_args()
    expected_bytes = read_bytes(args.expected)
    actual_bytes = read_bytes(args.actual)
    expected = set(expected_bytes.splitlines())
    actual = set(actual_bytes.splitlines())
    print(f"expected_count={len(expected_bytes.splitlines())}")
    print(f"actual_count={len(actual_bytes.splitlines())}")
    print(f"expected_sha256={hashlib.sha256(expected_bytes).hexdigest()}")
    print(f"actual_sha256={hashlib.sha256(actual_bytes).hexdigest()}")
    if expected_bytes == actual_bytes:
        print("MATCH exact_bytes")
        return 0
    print("MISMATCH symmetric_difference_begin")
    for line in sorted(actual - expected):
        print("only_actual\t" + line.decode("ascii"))
    for line in sorted(expected - actual):
        print("only_expected\t" + line.decode("ascii"))
    print("MISMATCH symmetric_difference_end")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
