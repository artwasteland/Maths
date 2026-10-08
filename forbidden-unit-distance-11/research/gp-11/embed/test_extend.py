#!/usr/bin/env python3
"""Exact arithmetic controls and production-path regressions for job D."""
from __future__ import annotations

import copy
from fractions import Fraction
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import extend
from extend_run import recover_journal


def canonical_record(points, edges, field):
    n = len(points)
    mask = sum(1 << extend.graphs.pair_index(n, u, v) for u, v in edges)
    canonical = extend.graphs.canonicalize(n, mask)
    return {"g6": canonical.g6, "verdict": "embedded", "cert": {
        "type": "exact", "field": field,
        "coords": [points[old] for old in canonical.new_to_old]}}


class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        extend.limits()
        cls.guard = extend.Guard()
        with cls.guard.watch():
            cls.index = extend.EmbeddingIndex()
            cls.checker = extend.load_checker()
        cls.directory = tempfile.TemporaryDirectory(prefix="gp11-extend-tests-", dir="/tmp")
        cls.scratch = Path(cls.directory.name)
        cls.red_messages = []

    @classmethod
    def tearDownClass(cls):
        print("RED_CONTROLS " + json.dumps(cls.red_messages, sort_keys=True), flush=True)
        cls.directory.cleanup()

    def accept(self, record):
        # Round-trip the wire syntax too. A red control must reach the
        # arithmetic rule through the frozen JSON and rational parsers.
        wire = self.checker.loads(extend.compact(record))
        return self.checker.exact_embedding(self.checker.decode(wire["g6"]), wire["cert"])

    def reject(self, record, reason, name):
        with self.assertRaises(self.checker.Rejection) as caught:
            self.accept(record)
        self.assertEqual(caught.exception.reason, reason)
        self.red_messages.append({"control": name, "reason": caught.exception.reason,
                                  "message": str(caught.exception)})

    def extension(self, base, neighbours=(0, 1), cap=256):
        n = len(base["coords"])
        with self.guard.watch(30):
            return extend.extend_exact("test", base, n, list(range(n)), list(neighbours), self.scratch, cap)

    def rational_base(self, points):
        return {"type": "exact", "field": {"minpoly": [0, 1], "interval": ["-1", "1"]},
                "coords": [[[str(x)], [str(y)]] for x, y in points]}

    def test_tangent_and_two_intersections(self):
        for x, tangent in ((2, True), (1, False)):
            candidate, diagnostics = self.extension(self.rational_base([(0, 0), (x, 0)]))
            record = canonical_record(candidate["coords"], [(0, 2), (1, 2)], candidate["field"])
            self.accept(record)
            self.assertEqual(diagnostics["tangent"], tangent)
            self.assertEqual(diagnostics["branches"], [[1, 0]])

    def square(self):
        base = self.rational_base([(0, 0), (1, 0), (1, 1)])
        candidate, diagnostics = self.extension(base, (0, 2))
        self.assertEqual(diagnostics["branches"], [[1, 2], [-1, 0]])
        edges = [(0, 1), (1, 2), (2, 3), (0, 3)]
        mask = sum(1 << extend.graphs.pair_index(4, u, v) for u, v in edges)
        self.square_new_vertex = extend.graphs.canonicalize(4, mask).old_to_new[3]
        return canonical_record(candidate["coords"], edges, candidate["field"])

    def test_red_controls_and_recheck_originals(self):
        original = self.square()
        initial = self.accept(original)
        perturbed = copy.deepcopy(original)
        perturbed["cert"]["coords"][0][0][0] = str(
            Fraction(perturbed["cert"]["coords"][0][0][0]) + Fraction(1, 7))
        # This mutation must pass distinctness if edge equations are absent.
        # Otherwise a second defect could hide a deleted edge check.
        self.checker.exact_embedding(self.checker.Graph(4, set()), perturbed["cert"])
        self.reject(perturbed, "edge_equation", "coordinate_perturbed")
        self.assertEqual(self.accept(original), initial)

        # In C4, opposite vertices share both neighbours. Coinciding them
        # preserves every edge equation and isolates the collision rule.
        graph = self.checker.decode(original["g6"])
        v = self.square_new_vertex
        u = next(u for u in range(4) if u != v and tuple(sorted((u, v))) not in graph.edges)
        collided = copy.deepcopy(original)
        collided["cert"]["coords"][v] = copy.deepcopy(collided["cert"]["coords"][u])
        self.reject(collided, "exact_collision", "new_point_on_non_neighbour")
        self.assertEqual(self.accept(original), initial)

        u, v = min(graph.edges)
        wrong = copy.deepcopy(original)
        coords = wrong["cert"]["coords"]
        coords[u], coords[v] = coords[v], coords[u]
        self.checker.exact_embedding(self.checker.Graph(4, set()), wrong["cert"])
        self.reject(wrong, "edge_equation", "wrong_relabelling")
        self.assertEqual(self.accept(original), initial)

    def test_nonmonic_reducible_and_selected_root(self):
        # theta = +/- sqrt(3)/2; the extraneous factor and repeated factor
        # are legal E-exact inputs, but cannot be handed to nfinit unchanged.
        variants = [([-3, 0, 4], ["0", "1"]),
                    ([36, 0, -51, 0, 4], ["0", "21/20", "0", "-1/15"]),
                    ([-27, 0, 108, 0, -144, 0, 64], ["0", "15/8", "0", "-5/3", "0", "2/3"])]
        for polynomial, theta in variants:
            degree = len(polynomial) - 1
            for interval in (["4/5", "9/10"], ["-9/10", "-4/5"]):
                zero = ["0"] * degree
                one = ["1"] + ["0"] * (degree - 1)
                half = ["1/2"] + ["0"] * (degree - 1)
                base = {"type": "exact", "field": {"minpoly": polynomial, "interval": interval},
                        "coords": [[zero, zero], [one, zero], [half, theta]]}
                self.accept(canonical_record(base["coords"], [(0, 1), (0, 2), (1, 2)], base["field"]))
                candidate, diagnostics = self.extension(base)
                record = canonical_record(candidate["coords"], [(0, 2), (1, 2), (0, 3), (1, 3)], candidate["field"])
                self.accept(record)
                self.assertEqual(len(diagnostics["branches"]), 2 if interval[0].startswith("-") else 1)

    def test_higher_degree_primitive_conversion(self):
        degree = 8
        zero = ["0"] * degree
        base = {"type": "exact", "field": {"minpoly": [-2] + [0] * 7 + [1], "interval": ["1", "2"]},
                "coords": [[zero, zero], [["1"] + zero[1:], zero],
                           [["0", "1"] + zero[2:], ["2"] + zero[1:]]]}
        candidate, _ = self.extension(base)
        self.assertEqual(len(candidate["field"]["minpoly"]) - 1, 16)
        self.accept(canonical_record(candidate["coords"], [(0, 3), (1, 3)], candidate["field"]))

    def test_only_colliding_extensions_stay_unknown(self):
        # Add a third common neighbour where both intersections are already
        # occupied. All base vertices have degree >= 3, so only the added
        # vertex is eligible. This deliberately lies outside F10-free B11.
        fixture = None
        for code in sorted(self.index._records):
            n, mask = extend.graphs.decode_graph6(code)
            adjacency = extend.graphs.adjacency_dict(n, mask)
            if min(map(len, adjacency.values())) < 3:
                continue
            pair = next(((u, v) for u in range(n) for v in range(u + 1, n)
                         if len(set(adjacency[u]) & set(adjacency[v])) == 2), None)
            if pair is not None:
                newmask = mask | (1 << extend.graphs.pair_index(11, 10, pair[0]))
                newmask |= 1 << extend.graphs.pair_index(11, 10, pair[1])
                fixture = extend.graphs.canonicalize(11, newmask).g6
                break
        self.assertIsNotNone(fixture)
        extender = extend.Extender(self.index, self.checker, self.scratch, self.guard, seconds=10)
        record, stats = extender.run(fixture)
        self.assertEqual(record["verdict"], "unknown")
        self.assertEqual(record["cert"]["reason"], "extension:collision")
        self.assertEqual(stats["degree2_vertices"], 1)
        branches = stats["attempts"][0]["branches"]
        self.assertEqual([row[0] for row in branches], [1, -1])
        self.assertTrue(all(row[1] > 0 for row in branches))
        print("COLLISION_UNKNOWN " + extend.compact({"record": record, "stats": stats}), flush=True)

    def test_real_deletion_map_and_determinism(self):
        code = (extend.HERE.parent / "design/prototypes/sample.g6").read_text().splitlines()[0]
        extender = extend.Extender(self.index, self.checker, self.scratch, self.guard, seconds=10)
        first, stats = extender.run(code)
        second, _ = extender.run(code)
        self.assertEqual(first["verdict"], "embedded")
        self.assertEqual(first, second)
        self.assertEqual(stats["seed"], extend.seed_for(code))
        self.accept(first)

    def test_nonbiconnected_missing_base_and_no_degree_two(self):
        # Every vertex deletion of a cycle is a path, hence absent from B10.
        mask = sum(1 << extend.graphs.pair_index(11, i, (i + 1) % 11) for i in range(11))
        code = extend.graphs.canonicalize(11, mask).g6
        extender = extend.Extender(self.index, self.checker, self.scratch, self.guard)
        record, stats = extender.run(code)
        self.assertEqual(record["cert"]["reason"], "base_not_biconnected")
        self.assertEqual(len(stats["attempts"]), 11)
        # A triangle with isolated vertices also exercises disconnected bases.
        mask = sum(1 << extend.graphs.pair_index(11, u, v) for u, v in [(0, 1), (0, 2), (1, 2)])
        code = extend.graphs.canonicalize(11, mask).g6
        record, stats = extender.run(code)
        self.assertEqual(record["cert"]["reason"], "base_not_biconnected")
        self.assertEqual(len(stats["attempts"]), 3)
        code = extend.graphs.canonicalize(11, (1 << 55) - 1).g6
        record, _ = extender.run(code)
        self.assertEqual(record["cert"]["reason"], "no_degree_two_vertex")

    def test_failure_paths(self):
        with self.assertRaisesRegex(extend.ExtensionFailure, "extension:far"):
            self.extension(self.rational_base([(0, 0), (3, 0)]))
        with self.assertRaisesRegex(extend.ExtensionFailure, "field:degree_cap"):
            self.extension(self.rational_base([(0, 0), (1, 0)]), cap=1)
        with patch("extend.subprocess.Popen") as mocked:
            child = mocked.return_value
            child.returncode = 0
            child.communicate.return_value = ("", "")
            with self.assertRaisesRegex(extend.ExtensionFailure, "pari:missing_exact_success"):
                self.extension(self.rational_base([(0, 0), (1, 0)]))
        code = (extend.HERE.parent / "design/prototypes/sample.g6").read_text().splitlines()[0]
        extender = extend.Extender(self.index, self.checker, self.scratch, self.guard)
        with patch.object(self.index, "resolve", side_effect=KeyError("missing")):
            record, stats = extender.run(code)
            self.assertEqual(record["verdict"], "unknown")
            self.assertIn("base_not_indexed", {row["reason"] for row in stats["attempts"]})
        for error, reason in ((extend.Deadline(), "graph_timeout"), (MemoryError(), "producer_exception:MemoryError"),
                              (extend.MemoryFloor(), "memory_floor"), (extend.Interrupted(), "interrupted")):
            with patch("extend.extend_exact", side_effect=error):
                record, _ = extender.run(code)
                self.assertEqual(record["verdict"], "unknown")
                self.assertEqual(record["cert"]["reason"], reason)

    def test_journal_partial_write_recovery(self):
        path = self.scratch / "partial.jsonl"
        line = extend.compact({"record": {"g6": "Bw"}, "stats": {"g6": "Bw"}}) + "\n"
        path.write_text(line + '{"record":')
        self.assertEqual(recover_journal(path), 1)
        self.assertEqual(path.read_text(), line)
        path.write_text(line + "invalid\n")
        with self.assertRaises(json.JSONDecodeError):
            recover_journal(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
