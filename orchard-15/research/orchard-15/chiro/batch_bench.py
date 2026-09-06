#!/usr/bin/env python3
"""Create marked batch inputs and summarize chirosat JSONL results."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
from typing import Iterable, Sequence

from chirosat import PTS
from controls import CONTROLS


def write_marked(path: Path, instances: Iterable[PTS]) -> int:
    """Write a PTS file and its Section 8.2 completion marker."""
    lines = [instance.line for instance in instances]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = ("\n".join(lines) + "\n").encode("ascii")
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    path.with_name(path.name + ".DONE").write_text(
        f"count={len(lines)}\nsha256={digest}\n", encoding="ascii"
    )
    return len(lines)


def random_pts15(rng: random.Random) -> PTS:
    """Make a quick noncanonical PTS(15,32) from PG(3,2).

    The 35 lines of the binary projective 3-space form an STS(15). Removing
    any three lines leaves 32 edge-disjoint triples and an even nine-edge
    leave. Random relabelling and line removal provide varied input orderings
    and leave types without a fragile late-stage greedy search.
    """
    sts_set: set[tuple[int, int, int]] = set()
    for first, second in itertools.combinations(range(1, 16), 2):
        third = first ^ second
        if third not in (first, second):
            sts_set.add(tuple(sorted((first - 1, second - 1, third - 1))))
    sts = sorted(sts_set)
    assert len(sts) == 35
    removed = set(rng.sample(sts, 3))
    permutation = list(range(15))
    rng.shuffle(permutation)
    blocks = [
        tuple(sorted(permutation[point] for point in block))
        for block in sts
        if block not in removed
    ]
    result = PTS(15, tuple(sorted(blocks)))
    leave_degrees = [14] * 15
    for block in result.blocks:
        for point in block:
            leave_degrees[point] -= 2
    assert all(degree >= 0 and degree % 2 == 0 for degree in leave_degrees)
    assert sum(leave_degrees) == 18
    return result


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    controls = subparsers.add_parser("controls")
    controls.add_argument("--outdir", type=Path, required=True)
    controls.add_argument("--repeat", type=int, default=1)

    random_batch = subparsers.add_parser("random")
    random_batch.add_argument("--out", type=Path, required=True)
    random_batch.add_argument("--count", type=int, default=1000)
    random_batch.add_argument("--seed", type=int, default=20260905)

    summary = subparsers.add_parser("summary")
    summary.add_argument("jsonl", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.command == "controls":
        if args.repeat < 1:
            raise SystemExit("repeat must be positive")
        grouped: dict[int, list[PTS]] = {}
        for instance, _expected in CONTROLS.values():
            grouped.setdefault(instance.v, []).extend([instance] * args.repeat)
        for v, instances in sorted(grouped.items()):
            path = args.outdir / f"controls-v{v}.txt"
            print(path, write_marked(path, instances))
        return 0
    if args.command == "random":
        if args.count < 1:
            raise SystemExit("count must be positive")
        rng = random.Random(args.seed)
        print(args.out, write_marked(args.out, (random_pts15(rng) for _ in range(args.count))))
        return 0
    records = [json.loads(line) for line in args.jsonl.read_text(encoding="utf-8").splitlines()]
    verdicts = {verdict: sum(record["verdict"] == verdict for record in records) for verdict in ("pseudoline", "no-pseudoline")}
    total = sum(float(record["total_seconds"]) for record in records)
    print(json.dumps({"count": len(records), "verdicts": verdicts, "sum_instance_seconds": round(total, 6), "instances_per_second": round(len(records) / total, 6) if total else None}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
