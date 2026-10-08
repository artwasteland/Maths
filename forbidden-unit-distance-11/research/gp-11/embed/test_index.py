#!/usr/bin/env python3
"""Integration/regression tests for the GP-10 embedding index."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import random
import sys
import time
import types
import unittest

from index import EmbeddingIndex


HERE = Path(__file__).resolve().parent
CHECKER_PATH = HERE.parent.parent / "gp-10/check/gp10check.py"


def load_checker():
    # Exact embeddings and maps use only the checker's rational-polynomial
    # kernel.  Permit that frozen code to load on lean workers lacking the
    # optional algebraic-refutation and graph-isomorphism dependencies.
    try:
        import flint  # noqa: F401
    except ImportError:
        stub = types.ModuleType("flint")
        stub.fmpq = stub.fmpq_mpoly_ctx = object
        sys.modules["flint"] = stub
    try:
        import networkx  # noqa: F401
    except ImportError:
        sys.modules["networkx"] = types.ModuleType("networkx")
    spec = importlib.util.spec_from_file_location("frozen_gp10check", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = EmbeddingIndex()
        cls.checker_module = load_checker()

    def accepted(self, code, cert):
        self.checker_module.exact_embedding(self.checker_module.decode(code), cert)

    def rejection(self, operation, expected):
        with self.assertRaises(self.checker_module.Rejection) as caught:
            operation()
        self.assertEqual(caught.exception.reason, expected)

    def test_all_resolve(self):
        self.assertEqual(len(self.index), 32653)
        self.assertEqual(sum(self.index.chain_lengths().values()), 32653)
        for record in self.index.stream():
            self.assertEqual(record["cert"]["type"], "exact")
            self.assertEqual(len(record["cert"]["coords"]), 10)

    def test_seeded_sample_with_frozen_exact_checker(self):
        codes = sorted(self.index._records)
        sample = sorted(random.Random(20261001).sample(codes, 1000))
        for code in sample:
            self.accepted(code, self.index.resolve(code))

    def test_red_controls_and_unchanged_evidence(self):
        # Use a genuine pointer and let the frozen checker's map validator reject
        # a duplicate image.  The unmodified resolved evidence remains accepted.
        code = next(c for c, cert in self.index._records.items() if cert["type"] == "super")
        original = self.index.resolve(code)
        bad_pointer = copy.deepcopy(self.index._records[code])
        bad_pointer["map"][1] = bad_pointer["map"][0]
        self.rejection(lambda: self.checker_module.mapping(
            self.checker_module.decode(code),
            self.checker_module.decode(bad_pointer["g6"]), bad_pointer["map"], "E-ptr"),
            "map_not_injective")
        self.accepted(code, original)

        # A syntactically valid rational perturbation reaches exact arithmetic
        # (rather than merely breaking JSON) and fails an edge equation.
        perturbed = copy.deepcopy(original)
        perturbed["coords"][0][0][0] = str(
            self.checker_module.rational(perturbed["coords"][0][0][0]) + 1)
        self.rejection(lambda: self.accepted(code, perturbed), "edge_equation")
        self.accepted(code, original)

        # Simulate the classic composition-order bug: apply the first pointer's
        # inverse instead of its source-to-target map.  Select a case where this
        # demonstrably destroys an edge, and demand the exact checker reason.
        wrong = None
        for candidate, cert in self.index._records.items():
            if cert["type"] != "super" or cert["g6"] not in self.index._records:
                continue
            route = self.index.resolve(candidate)
            permutation = cert["map"]
            inverse = [0] * 10
            for i, image in enumerate(permutation):
                inverse[image] = i
            trial = copy.deepcopy(route)
            trial["coords"] = [route["coords"][inverse[i]] for i in range(10)]
            try:
                self.accepted(candidate, trial)
            except self.checker_module.Rejection as exc:
                if exc.reason == "edge_equation":
                    wrong = (candidate, trial, route)
                    break
        self.assertIsNotNone(wrong)
        self.rejection(lambda: self.accepted(wrong[0], wrong[1]), "edge_equation")
        self.accepted(wrong[0], wrong[2])


if __name__ == "__main__":
    started = time.perf_counter()
    unittest.main(verbosity=2)
