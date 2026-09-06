#!/usr/bin/env python3
"""Canonicalise contract PTS lines via coloured point-block incidence graphs."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import itertools
import sys
import time
from pathlib import Path

import pynauty

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chiro"))
from chirosat import PTS, parse_pts_line  # noqa: E402


def incidence_graph(pts: PTS) -> pynauty.Graph:
    size = pts.v + len(pts.blocks)
    adjacency = {vertex: [] for vertex in range(size)}
    for index, block in enumerate(pts.blocks):
        block_vertex = pts.v + index
        for point in block:
            adjacency[point].append(block_vertex)
            adjacency[block_vertex].append(point)
    return pynauty.Graph(
        size,
        directed=False,
        adjacency_dict=adjacency,
        vertex_coloring=[set(range(pts.v)), set(range(pts.v, size))],
    )


def canonical_pts(pts: PTS) -> tuple[bytes, PTS]:
    graph = incidence_graph(pts)
    # pynauty returns lab[new] = old.  Invert it before relabelling points.
    lab = pynauty.canon_label(graph)
    old_to_new = [0] * len(lab)
    for new, old in enumerate(lab):
        old_to_new[old] = new
    if set(old_to_new[: pts.v]) != set(range(pts.v)):
        raise RuntimeError("nauty canonical labelling did not preserve the point colour cell")
    blocks = tuple(
        sorted(tuple(sorted(old_to_new[point] for point in block)) for block in pts.blocks)
    )
    canonical = PTS(pts.v, blocks)
    return pynauty.certificate(graph), canonical


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def leave_type(pts: PTS) -> str:
    covered = {pair for block in pts.blocks for pair in itertools.combinations(block, 2)}
    degrees = sorted(
        sum(tuple(sorted((point, other))) not in covered for other in range(pts.v) if other != point)
        for point in range(pts.v)
    )
    return ",".join(map(str, degrees))


def iter_pts(path: Path):
    with path.open(encoding="ascii") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip() and not line.lstrip().startswith("#"):
                try:
                    yield parse_pts_line(line)
                except ValueError as exc:
                    raise ValueError(f"{path}:{number}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--exist-options", required=True)
    parser.add_argument("--exist-wall", type=float, required=True)
    parser.add_argument("--known", type=Path)
    args = parser.parse_args()

    started = time.perf_counter()
    classes: dict[bytes, PTS] = {}
    labelled = 0
    v = b = None
    for pts in iter_pts(args.input):
        labelled += 1
        if v is None:
            v, b = pts.v, len(pts.blocks)
        elif (pts.v, len(pts.blocks)) != (v, b):
            raise ValueError("input is not homogeneous")
        certificate, canonical = canonical_pts(pts)
        previous = classes.setdefault(certificate, canonical)
        if previous.line != canonical.line:
            raise RuntimeError("nauty certificate collision with unequal canonical forms")
    ordered = sorted((pts.line for pts in classes.values()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="ascii")

    known_present = None
    if args.known:
        known = list(iter_pts(args.known))
        if len(known) != 1:
            raise ValueError("--known must contain exactly one PTS")
        known_present = canonical_pts(known[0])[0] in classes
        if not known_present:
            raise RuntimeError("known PTS is absent up to isomorphism")
    manifest = {
        "v": v,
        "b": b,
        "labelled_models": labelled,
        "count": len(ordered),
        "sha256": file_sha256(args.output),
        "input_sha256": file_sha256(args.input),
        "generator": str((ROOT / "chiro" / "exist.py").resolve()),
        "generator_sha256": file_sha256(ROOT / "chiro" / "exist.py"),
        "exist_options": args.exist_options,
        "exist_wall_seconds": args.exist_wall,
        "canonicalizer": "pynauty coloured point-block incidence graph",
        "pynauty_version": pynauty.Version(),
        "leave_type_histogram": dict(sorted(collections.Counter(
            leave_type(pts) for pts in classes.values()
        ).items())),
        "known_pts_present": known_present,
        "canonicalize_wall_seconds": round(time.perf_counter() - started, 6),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
