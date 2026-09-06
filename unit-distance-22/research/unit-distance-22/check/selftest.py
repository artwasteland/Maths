#!/usr/bin/env python3
"""Adversarial end-to-end self-checks for udcheck.py."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import networkx as nx


HERE = Path(__file__).resolve().parent
PYTHON = Path.home() / "tools/pyenv-maths/bin/python"
CHECKER = HERE / "udcheck.py"
DATA = HERE.parent / "data"
LABELG = "/usr/bin/nauty-labelg"


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in records),
                    encoding="utf-8")


def invoke(name: str, cert: Path, accept: bool, *extra: str) -> str:
    proc = subprocess.run(
        [str(PYTHON), str(CHECKER), "--allow-any-size", str(cert), *extra],
        cwd=HERE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=60, check=False,
    )
    ok = proc.returncode == 0
    if ok != accept:
        raise AssertionError(f"{name}: unexpected exit {proc.returncode}\n{proc.stdout}")
    marker = "ACCEPT" if accept else "REJECT"
    if marker not in proc.stdout:
        raise AssertionError(f"{name}: output lacks {marker}\n{proc.stdout}")
    first = proc.stdout.strip().splitlines()[0]
    print(f"PASS {name}: exit={proc.returncode}: {first}")
    return proc.stdout


def invoke_default(name: str, cert: Path, accept: bool, *extra: str) -> str:
    proc = subprocess.run(
        [str(PYTHON), str(CHECKER), str(cert), *extra],
        cwd=HERE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=60, check=False,
    )
    if (proc.returncode == 0) != accept:
        raise AssertionError(f"{name}: unexpected exit {proc.returncode}\n{proc.stdout}")
    marker = "ACCEPT" if accept else "REJECT"
    if marker not in proc.stdout:
        raise AssertionError(f"{name}: output lacks {marker}\n{proc.stdout}")
    print(f"PASS {name}: exit={proc.returncode}: {proc.stdout.strip().splitlines()[0]}")
    return proc.stdout


def canonical_graph(n: int, edges: list[tuple[int, int]]) -> tuple[str, dict[int, int], list[tuple[int, int]]]:
    source = nx.Graph()
    source.add_nodes_from(range(n))
    source.add_edges_from(edges)
    raw = nx.to_graph6_bytes(source, header=False).decode("ascii").strip()
    proc = subprocess.run([LABELG, "-q"], input=raw + "\n", text=True,
                          stdout=subprocess.PIPE, check=True)
    code = proc.stdout.strip()
    target = nx.from_graph6_bytes(code.encode("ascii"))
    mapping = next(nx.algorithms.isomorphism.GraphMatcher(source, target).isomorphisms_iter())
    mapped_edges = sorted(tuple(sorted((mapping[u], mapping[v]))) for u, v in edges)
    return code, mapping, mapped_edges


def cycle_rows(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    eset = {tuple(sorted(e)) for e in edges}
    seen: set[tuple[int, ...]] = set()
    rows: list[list[int]] = []
    import itertools
    for vertices in itertools.combinations(range(n), 4):
        first = vertices[0]
        for tail in itertools.permutations(vertices[1:]):
            cycle = (first,) + tail
            if cycle[1] > cycle[-1]:
                continue
            if not all(tuple(sorted((cycle[i], cycle[(i + 1) % 4]))) in eset for i in range(4)):
                continue
            row = [0] * n
            for i, v in enumerate(cycle):
                row[v] += 1 if i % 2 == 0 else -1
            key = min(tuple(row), tuple(-x for x in row))
            if key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def q_field() -> dict:
    return {"minpoly": [0, 1], "interval": [-1, 1]}


def k4_node(move: dict, children: list[dict] | None = None) -> dict:
    return {
        "edges": [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]],
        "A": [[1, -1, 1, -1], [1, -1, -1, 1], [1, 1, -1, -1]],
        "move": move,
        "children": [] if children is None else children,
    }


def refuted_record(code: str, field: dict, tree: dict) -> dict:
    return {"g6": code, "verdict": "refuted", "witness": {"field": field, "tree": tree}}


def first_move_node(node: dict, kind: str) -> dict:
    if node["move"]["kind"] == kind:
        return node
    for child in node["children"]:
        found = first_move_node(child, kind)
        if found is not None:
            return found
    return None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class QS3:
    def __init__(self, a: int | Fraction, b: int | Fraction = 0):
        self.a, self.b = Fraction(a), Fraction(b)

    def __add__(self, other: "QS3") -> "QS3":
        return QS3(self.a + other.a, self.b + other.b)

    def __sub__(self, other: "QS3") -> "QS3":
        return QS3(self.a - other.a, self.b - other.b)

    def __mul__(self, other: "QS3") -> "QS3":
        return QS3(self.a * other.a + 3 * self.b * other.b,
                   self.a * other.b + self.b * other.a)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QS3) and (self.a, self.b) == (other.a, other.b)


def validate_written_tu_proofs(gadgets: list[dict], bad_combo: bool = False) -> None:
    cycles = [
        [(0, 1, 2, 3), (2, 3, 4, 5)],
        [(0, 2, 1, 3), (0, 3, 2, 4), (1, 3, 2, 6), (1, 2, 5, 6)],
        [(0, 2, 1, 3), (0, 2, 5, 4), (1, 3, 2, 6), (1, 2, 5, 6)],
        [(0, 1, 3, 2), (0, 2, 5, 6), (1, 3, 4, 7), (2, 3, 4, 5)],
        [(0, 1, 3, 2), (0, 2, 5, 6), (1, 3, 4, 7), (2, 3, 4, 5)],
        [(0, 1, 3, 2), (0, 2, 5, 6), (1, 3, 4, 7), (2, 3, 4, 5)],
    ]
    weights = [[-1, 1], [0, -1, 1, -1], [-1, 1, 1, -1],
               [1, -1, 1, -1], [0, -1, 1, -1], [0, -1, 1, -1]]
    comparison_edges = [(0, 4), (0, 2), (1, 2), (2, 6), (0, 1), (0, 1)]
    if bad_combo:
        weights[0][0] = 1
    for k, gadget in enumerate(gadgets):
        eset = {tuple(sorted(e)) for e in gadget["edges"]}
        total = [0] * gadget["n"]
        for weight, cycle in zip(weights[k], cycles[k]):
            if not all(tuple(sorted((cycle[i], cycle[(i + 1) % 4]))) in eset for i in range(4)):
                raise AssertionError(f"proof gadget {k} uses absent cycle edge")
            for i, v in enumerate(cycle):
                total[v] += weight * (1 if i % 2 == 0 else -1)
        u, v = gadget["pair"]
        total[u] -= 1
        total[v] += 1
        a, b = comparison_edges[k]
        if tuple(sorted((a, b))) not in eset:
            raise AssertionError(f"proof gadget {k} comparison is not an edge")
        total[a] += 1
        total[b] -= 1
        if any(total):
            raise AssertionError(f"proof gadget {k} rhombus identity is false")

    half = Fraction(1, 2)
    zero, one, s2 = QS3(0), QS3(1), QS3(0, half)
    d0 = [(zero, zero), (one, zero), (QS3(half), s2), (zero, one),
          (one, one), (QS3(half), one + s2)]
    d1 = [(zero, zero), (one, zero), (QS3(half), s2), (QS3(Fraction(3, 2)), s2),
          (QS3(Fraction(-1, 2)), s2), (zero, QS3(0, 1)), (one, QS3(0, 1))]
    d2 = [(zero, zero), (one, zero), (QS3(half), s2), (QS3(Fraction(3, 2)), s2),
          (zero, one), (one, one), (QS3(half), one + s2),
          (QS3(Fraction(3, 2)), one + s2)]
    diagrams = [d0, d1, d1, d2, d2, d2]
    maps = [
        [0, 3, 5, 2, 1, 4],
        [5, 0, 2, 4, 6, 3, 1],
        [1, 4, 2, 0, 3, 6, 5],
        [0, 4, 2, 6, 7, 3, 1, 5],
        [0, 4, 2, 6, 7, 3, 1, 5],
        [0, 4, 2, 6, 7, 3, 1, 5],
    ]
    for k, gadget in enumerate(gadgets):
        points = [diagrams[k][i] for i in maps[k]]
        for u, v in gadget["edges"]:
            dx, dy = points[u][0] - points[v][0], points[u][1] - points[v][1]
            if dx * dx + dy * dy != one:
                raise AssertionError(f"proof gadget {k} coordinate edge is not unit")
        u, v = gadget["pair"]
        dx, dy = points[u][0] - points[v][0], points[u][1] - points[v][1]
        if dx * dx + dy * dy != one or tuple(sorted((u, v))) in {
            tuple(sorted(e)) for e in gadget["edges"]
        }:
            raise AssertionError(f"proof gadget {k} distinguished pair check failed")


def main() -> int:
    gadgets = json.loads((DATA / "tu-gadgets.json").read_text())
    scratch_root = HERE / "scratch"
    scratch_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="selftest-", dir=scratch_root) as temp_name:
        temp = Path(temp_name)

        invoke("K4 L1a refutation", HERE / "fixtures/k4-refuted.jsonl", True)
        invoke("K4 one-byte pair corruption", HERE / "fixtures/k4-refuted-corrupt.jsonl", False)
        invoke_default("default (22,61) gate on K4", HERE / "fixtures/k4-refuted.jsonl", False)
        broken = json.loads((HERE / "fixtures/k4-refuted.jsonl").read_text())
        broken["witness"]["tree"]["A"][0][0] = 2
        root_a_bad = temp / "root-a-bad.jsonl"
        write_jsonl(root_a_bad, [broken])
        invoke("L0 root row-space mutation", root_a_bad, False)
        invoke("Moser exact embedding", HERE / "fixtures/moser-embedded.jsonl", True)
        invoke("Moser one-byte coordinate corruption", HERE / "fixtures/moser-embedded-corrupt.jsonl", False)
        broken = json.loads((HERE / "fixtures/moser-embedded.jsonl").read_text())
        broken["witness"]["coordinates"][6] = broken["witness"]["coordinates"][0]
        collision_bad = temp / "embedding-collision.jsonl"
        write_jsonl(collision_bad, [broken])
        invoke("exact embedding collision mutation", collision_bad, False)
        invoke("planted forbidden witness", HERE / "fixtures/planted-forbidden.jsonl", True)
        invoke("forbidden one-byte map corruption", HERE / "fixtures/planted-forbidden-corrupt.jsonl", False)
        absent_edge = temp / "forbidden-absent-edge.jsonl"
        write_jsonl(absent_edge, [{"g6": "C^", "verdict": "forbidden",
                                  "witness": {"index": 0, "map": [0, 1, 2, 3]}}])
        invoke("forbidden edge-preservation mutation", absent_edge, False)

        l1b = temp / "l1b.jsonl"
        write_jsonl(l1b, [refuted_record(
            "C~", q_field(), k4_node({"kind": "L1b", "edges": [[0, 1], [0, 2]], "omega": 0})
        )])
        invoke("L1b exact forced ratio", l1b, True)
        broken = json.loads(l1b.read_text())
        broken["witness"]["tree"]["move"]["omega"] = 1
        l1b_bad = temp / "l1b-bad.jsonl"
        write_jsonl(l1b_bad, [broken])
        invoke("L1b unit-modulus mutation", l1b_bad, False)

        base_edges = [tuple(e) for e in gadgets[0]["edges"]] + [(1, 6), (2, 6), (5, 6)]
        code, mapping, mapped = canonical_graph(7, base_edges)
        root_rows = cycle_rows(7, mapped)
        forced = (mapping[1], mapping[5])
        reference = (mapping[0], mapping[4])
        child_edges = sorted(mapped + [tuple(sorted(forced))])
        child_rows = root_rows + cycle_rows(7, child_edges)
        leaf = {
            "edges": [list(e) for e in child_edges],
            "A": child_rows,
            "move": {"kind": "L1a", "pair": [mapping[1], mapping[2]]},
            "children": [],
        }
        l2_tree = {
            "edges": [list(e) for e in mapped],
            "A": root_rows,
            "move": {"kind": "L2", "edges": [list(reference), list(forced)], "omega": 1},
            "children": [leaf],
        }
        l2 = temp / "l2.jsonl"
        write_jsonl(l2, [refuted_record(code, q_field(), l2_tree)])
        invoke("L2 forced edge and child contradiction", l2, True)
        broken = json.loads(l2.read_text())
        broken["witness"]["tree"]["move"]["omega"] = 0
        l2_bad = temp / "l2-bad.jsonl"
        write_jsonl(l2_bad, [broken])
        invoke("L2 modulus mutation", l2_bad, False)
        broken = json.loads(l2.read_text())
        broken["witness"]["tree"]["children"][0]["edges"].pop()
        l2_child_bad = temp / "l2-child-bad.jsonl"
        write_jsonl(l2_child_bad, [broken])
        invoke("L2 child graph mutation", l2_child_bad, False)

        leaf3 = k4_node({"kind": "L1a", "pair": [0, 1]})
        l3_tree = k4_node(
            {"kind": "L3", "edges": [[0, 1], [0, 2], [0, 3]],
             "coefficients": [1, 1, 1], "d": [0, 1]},
            [leaf3, leaf3],
        )
        l3 = temp / "l3.jsonl"
        write_jsonl(l3, [refuted_record(
            "C~", {"minpoly": [-3, 0, 1], "interval": [1, 2]}, l3_tree
        )])
        invoke("L3 two-branch Lemma 4 split", l3, True)
        broken = json.loads(l3.read_text())
        broken["witness"]["tree"]["move"]["d"] = [1]
        l3_bad = temp / "l3-bad.jsonl"
        write_jsonl(l3_bad, [broken])
        invoke("L3 discriminant mutation", l3_bad, False)
        broken = json.loads(l3.read_text())
        broken["witness"]["tree"]["children"][1]["A"][0][0] = 2
        l3_branch_bad = temp / "l3-branch-bad.jsonl"
        write_jsonl(l3_branch_bad, [broken])
        invoke("L3 branch row-space mutation", l3_branch_bad, False)

        broken = json.loads(l3.read_text())
        broken["witness"]["tree"]["move"] = {
            "kind": "L1c", "edges": [[0, 1], [0, 2], [0, 3]],
            "coefficients": [1, 1, 1],
        }
        broken["witness"]["tree"]["children"] = []
        l1c_nonnegative = temp / "l1c-nonnegative.jsonl"
        write_jsonl(l1c_nonnegative, [broken])
        invoke("L1c nonnegative discriminant from genuine L3 node", l1c_nonnegative, False)

        l1c_fixture = HERE / "fixtures/n17-negative-heron.jsonl"
        invoke("L1c n=17 negative-Heron refutation", l1c_fixture, True)
        l1c_record = json.loads(l1c_fixture.read_text())

        # Each mutation below changes exactly one JSON location in the accepted fixture.
        broken = json.loads(json.dumps(l1c_record))
        first_move_node(broken["witness"]["tree"], "L1c")["move"]["coefficients"][0] = [2]
        l1c_relation_bad = temp / "l1c-relation-bad.jsonl"
        write_jsonl(l1c_relation_bad, [broken])
        invoke("L1c row-space mutation", l1c_relation_bad, False)

        broken = json.loads(json.dumps(l1c_record))
        first_move_node(broken["witness"]["tree"], "L1c")["move"]["coefficients"][0] = [0]
        l1c_zero_bad = temp / "l1c-zero-bad.jsonl"
        write_jsonl(l1c_zero_bad, [broken])
        invoke("L1c zero-coefficient mutation", l1c_zero_bad, False)

        broken = json.loads(json.dumps(l1c_record))
        first_move_node(broken["witness"]["tree"], "L1c")["children"] = [{}]
        l1c_child_bad = temp / "l1c-child-bad.jsonl"
        write_jsonl(l1c_child_bad, [broken])
        invoke("L1c child mutation", l1c_child_bad, False)

        for i, gadget in enumerate(gadgets):
            gedges = [tuple(e) for e in gadget["edges"]]
            gcode, gmapping, _ = canonical_graph(gadget["n"], gedges)
            record = {
                "g6": gcode,
                "verdict": "tu",
                "witness": {
                    "index": i,
                    "map": [gmapping[j] for j in range(gadget["n"])],
                    "pair": [gmapping[j] for j in gadget["pair"]],
                },
            }
            path = temp / f"tu-{i}.jsonl"
            write_jsonl(path, [record])
            invoke(f"TU gadget index {i}", path, True)
        tu_bad = json.loads((temp / "tu-0.jsonl").read_text())
        tu_bad["witness"]["pair"][1] = tu_bad["witness"]["map"][0]
        tu_bad_path = temp / "tu-bad.jsonl"
        write_jsonl(tu_bad_path, [tu_bad])
        invoke("TU distinguished-pair mutation", tu_bad_path, False)
        raw_graph = nx.Graph()
        raw_graph.add_nodes_from(range(gadgets[0]["n"]))
        raw_graph.add_edges_from(gadgets[0]["edges"])
        raw_code = nx.to_graph6_bytes(raw_graph, header=False).decode("ascii").strip()
        raw_tu = {
            "g6": raw_code, "verdict": "tu",
            "witness": {"index": 0, "map": list(range(gadgets[0]["n"])),
                        "pair": gadgets[0]["pair"]},
        }
        raw_tu_path = temp / "tu-noncanonical.jsonl"
        write_jsonl(raw_tu_path, [raw_tu])
        invoke("noncanonical graph6 mutation", raw_tu_path, False)

        unknown_dir = temp / "unknown"
        unknown_dir.mkdir()
        unknown_cert = unknown_dir / "cert.jsonl"
        write_jsonl(unknown_cert, [{"g6": "C~", "verdict": "unknown"}])
        (unknown_dir / "UNKNOWN.g6").write_text("C~\n", encoding="ascii")
        invoke("unknown exact listing", unknown_cert, True)
        (unknown_dir / "UNKNOWN.g6").write_text("C?\n", encoding="ascii")
        invoke("unknown one-byte listing corruption", unknown_cert, False)

        target_dir = temp / "target-22-61"
        target_dir.mkdir()
        target_edges = [(u, v) for v in range(1, 22) for u in range(v)][:61]
        target_code, _, _ = canonical_graph(22, target_edges)
        target_cert = target_dir / "cert.jsonl"
        target_graphs = target_dir / "22-61.g6"
        write_jsonl(target_cert, [{"g6": target_code, "verdict": "unknown"}])
        (target_dir / "UNKNOWN.g6").write_text(target_code + "\n", encoding="ascii")
        target_graphs.write_text(target_code + "\n", encoding="ascii")
        invoke_default("default (22,61) positive gate and graph-list match", target_cert, True,
                       "--graphs", str(target_graphs))
        target_graphs.write_text("C~\n", encoding="ascii")
        invoke_default("graph-list mismatch", target_cert, False,
                       "--graphs", str(target_graphs))

        manifest_dir = temp / "manifests"
        manifest_dir.mkdir()
        parent = temp / "parent.g6"
        parent.write_text("C~\nC^\n", encoding="ascii")
        software = temp / "software.bin"
        software.write_bytes(b"independent test program\n")
        children = []
        for i, line in enumerate(("C~\n", "C^\n")):
            child = temp / f"child-{i}.g6"
            child.write_text(line, encoding="ascii")
            children.append(child)
            manifest = {
                "shard_id": f"s{i}",
                "parent_file": "../parent.g6",
                "parent_range": [i, i + 1],
                "software_sha256": {"../software.bin": sha(software)},
                "inputs_sha256": sha(parent),
                "started": "2026-09-05T00:00:00Z",
                "finished": "2026-09-05T00:00:01Z",
                "children_written": 1,
                "children_file": f"../child-{i}.g6",
                "children_sha256": sha(child),
                "host": "selftest",
                "exit_status": 0,
            }
            (manifest_dir / f"s{i}.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        invoke("manifest hashes and exact range tiling", HERE / "fixtures/k4-refuted.jsonl",
               True, "--manifest-dir", str(manifest_dir))
        compressed_dir = temp / "manifests-compressed"
        compressed_dir.mkdir()
        compressed_parent = temp / "parent.g6.zst"
        subprocess.run(["/usr/bin/zstd", "-q", "-f", str(parent), "-o", str(compressed_parent)],
                       check=True)
        for i, child in enumerate(children):
            compressed_child = temp / f"child-{i}.g6.zst"
            subprocess.run(["/usr/bin/zstd", "-q", "-f", str(child), "-o", str(compressed_child)],
                           check=True)
            manifest = json.loads((manifest_dir / f"s{i}.json").read_text())
            manifest["parent_file"] = "../parent.g6.zst"
            manifest["inputs_sha256"] = sha(compressed_parent)
            manifest["children_file"] = f"../child-{i}.g6.zst"
            manifest["children_sha256"] = sha(compressed_child)
            (compressed_dir / f"s{i}.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        invoke("compressed manifest record counting", HERE / "fixtures/k4-refuted.jsonl",
               True, "--manifest-dir", str(compressed_dir))
        bad_manifest_dir = temp / "manifests-bad"
        shutil.copytree(manifest_dir, bad_manifest_dir)
        bad_path = bad_manifest_dir / "s1.json"
        bad = json.loads(bad_path.read_text())
        bad["parent_range"] = [0, 1]
        bad_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
        invoke("manifest overlap mutation", HERE / "fixtures/k4-refuted.jsonl",
               False, "--manifest-dir", str(bad_manifest_dir))
        hash_bad_dir = temp / "manifests-hash-bad"
        shutil.copytree(manifest_dir, hash_bad_dir)
        hash_bad_path = hash_bad_dir / "s0.json"
        hash_bad = json.loads(hash_bad_path.read_text())
        digest = hash_bad["inputs_sha256"]
        hash_bad["inputs_sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
        hash_bad_path.write_text(json.dumps(hash_bad) + "\n", encoding="utf-8")
        invoke("manifest one-byte input-hash mutation", HERE / "fixtures/k4-refuted.jsonl",
               False, "--manifest-dir", str(hash_bad_dir))

        validate_written_tu_proofs(gadgets)
        print("PASS PROOFS.md identities and exact coordinate models")
        try:
            validate_written_tu_proofs(gadgets, bad_combo=True)
        except AssertionError as exc:
            print(f"PASS PROOFS.md coefficient mutation: rejected: {exc}")
        else:
            raise AssertionError("mutated TU proof unexpectedly passed")

    print("SELFTEST PASS checks=41 positive=18 rejected_mutations=23")
    return 0


if __name__ == "__main__":
    sys.exit(main())
