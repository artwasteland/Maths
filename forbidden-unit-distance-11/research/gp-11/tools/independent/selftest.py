#!/usr/bin/env python3
"""Small specification cases and diverse-method controls, without checkers.

Networkx is a graph oracle only in these tests. Production check 6 still runs
under Python -S with integer arithmetic and no external arithmetic packages.
"""
import argparse
import ast
from collections import Counter
import copy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import time

import networkx as nx

from independent_core import (Failure, biconnected, blocks, bounded_map, check_exact,
    decode_g6, encode_g6, iso_key, lines, loads, record, require, source_hashes, write_json)
from forbidden_catalogue import ForbiddenCatalogue, monomorphism
import modp_identities as modp


def make_system(rec):
    """Literal expansion of FORMAT's squared-distance generators for a control."""
    n, edges = decode_g6(rec["g6"])
    a, b = rec["cert"]["frame"]
    sat = rec["cert"]["sat"]
    names = [f"{z}_{i}" for i in range(n) if i not in (a, b) for z in ("x", "y")]
    names += [f"t_{k}" for k in range(len(sat))]
    zero = (0,) * len(names)

    def coordinate(i, axis):
        if i in (a, b):
            return {zero: Fraction(int(i == b and axis == "x"))}
        ex = list(zero)
        ex[names.index(f"{axis}_{i}")] = 1
        return {tuple(ex): Fraction(1)}

    def distance(u, v):
        result = Counter()
        for axis in ("x", "y"):
            terms = coordinate(u, axis)
            for e, coefficient in coordinate(v, axis).items():
                terms[e] = terms.get(e, Fraction(0)) - coefficient
            for x, c in terms.items():
                for y, d in terms.items():
                    result[tuple(i + j for i, j in zip(x, y))] += c * d
        return dict(result)

    def sparse(poly):
        return [[str(c), list(e)] for e, c in sorted(poly.items()) if c]

    result = {}
    for u, v in sorted(edges):
        if (u, v) != tuple(sorted((a, b))):
            poly = distance(u, v)
            poly[zero] = poly.get(zero, Fraction(0)) - 1
            result[f"e:{u},{v}"] = sparse(poly)
    for k, (u, v) in enumerate(sat):
        poly = {}
        for ex, coef in distance(u, v).items():
            ex = list(ex)
            ex[names.index(f"t_{k}")] += 1
            poly[tuple(ex)] = coef
        poly[zero] = -1
        result[f"s:{u},{v}"] = sparse(poly)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("samples")
    p.add_argument("forbidden_json")
    p.add_argument("out")
    a = p.parse_args()
    t0, done = time.monotonic(), []

    def case(name, fn):
        fn()
        done.append({"name": name, "status": "PASS"})

    def fails(fn, code):
        try:
            fn()
        except Failure as exc:
            require(exc.code == code, "selftest", f"expected {code}, got {exc.code}")
            return
        raise Failure("selftest", f"expected failure {code}")

    rng = random.Random(20261007)

    def codecs_and_blocks():
        require(decode_g6("Bw") == (3, {(0, 1), (0, 2), (1, 2)}), "selftest", "triangle graph6 anchor")
        for n in range(1, 12):
            for _ in range(8):
                es = {(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < .25}
                s = encode_g6(n, es)
                g = nx.Graph()
                g.add_nodes_from(range(n))
                g.add_edges_from(es)
                require(s == nx.to_graph6_bytes(g, header=False).decode().strip(), "selftest", "graph6 writer disagrees with networkx")
                require(set(nx.from_graph6_bytes(s.encode()).edges()) == es, "selftest", "graph6 reader disagrees with networkx")
                actual, isolated = blocks(n, es)
                expected = [set(tuple(sorted(e)) for e in b) for b in nx.biconnected_component_edges(g)]
                require({frozenset(b) for b in actual} == {frozenset(b) for b in expected}, "selftest", "block partition disagrees with networkx")
                require(biconnected(n, es) == (n >= 3 and nx.is_biconnected(g)), "selftest", "biconnectivity disagrees")
        fails(lambda: decode_g6("Bx"), "graph6")  # nonzero padding, despite same first three edge bits
    case("88 graph6/block comparisons against networkx; padding red", codecs_and_blocks)

    triangle = {"type": "exact", "field": {"minpoly": [-3, 0, 1], "interval": ["1", "2"]},
                "coords": [[["0", "0"], ["0", "0"]], [["1", "0"], ["0", "0"]],
                           [["1/2", "0"], ["0", "1/2"]]]}

    def exact_controls():
        check_exact("Bw", triangle)
        mutant = copy.deepcopy(triangle)
        mutant["coords"][0][0][0] = "1/" + str(10 ** 40)
        fails(lambda: check_exact("Bw", mutant), "edge_not_unit")
        check_exact("Bw", triangle)
        reducible = {"type": "exact", "field": {"minpoly": [6, 0, -5, 0, 1], "interval": ["1", "3/2"]},
                     "coords": [[["0"] * 4, ["0"] * 4], [["1", "0", "0", "0"], ["0"] * 4]]}
        check_exact("A_", reducible)
        collision = {"type": "exact", "field": {"minpoly": [-1, 1, -1, 1], "interval": ["-1", "3"]},
                     "coords": [[["0"] * 3, ["0"] * 3], [["1", "0", "0"], ["0"] * 3],
                                [["0", "0", "1"], ["0"] * 3]]}
        fails(lambda: check_exact(encode_g6(3, {(0, 1)}), collision), "collision")
        big = copy.deepcopy(triangle)
        huge = "1" + "0" * 5000
        big["coords"][1][0][0] = huge + "/" + huge
        check_exact("Bw", big)
    case("exact triangle; 1e-40 red; reducible polynomial; midpoint collision; 5001-digit rational", exact_controls)

    catalogue = ForbiddenCatalogue(a.forbidden_json)

    def matching():
        counts = Counter()
        for index, n, es in catalogue.patterns:
            counts[n] += 1
            require(monomorphism(n, es, n, es), "selftest", f"F10 self-containment fails at {index}")
        require(counts[10] == 324 and sum(v for n, v in counts.items() if n <= 9) == 74,
                "selftest", "F10 composition disagrees with the contract")
        for index, pn, pe in catalogue.patterns[:6]:
            for _ in range(3):
                hn = 8
                he = {(u, v) for u in range(hn) for v in range(u + 1, hn) if rng.random() < .35}
                host, pattern = nx.Graph(), nx.Graph()
                host.add_nodes_from(range(hn)); host.add_edges_from(he)
                pattern.add_nodes_from(range(pn)); pattern.add_edges_from(pe)
                expected = nx.algorithms.isomorphism.GraphMatcher(host, pattern).subgraph_is_monomorphic()
                require(monomorphism(hn, he, pn, pe) == expected, "selftest", "non-induced matcher disagrees with VF2")
        # Added nonedges must be allowed; an induced matcher would fail this.
        require(monomorphism(3, {(0, 1), (1, 2), (0, 2)}, 3, {(0, 1), (1, 2)}),
                "selftest", "matcher incorrectly requires induced containment")
    case("398 F10 positive controls; 18 VF2 comparisons; non-induced triangle control", matching)

    representatives = [record(raw) for _, raw in lines(Path(a.samples) / "by-type.jsonl")]
    null = next(r for r in representatives if r["cert"]["type"] == "null")

    def systems():
        positive = copy.deepcopy(null)
        positive["cert"]["system"] = make_system(positive)
        modp.check(positive)
        mutant = copy.deepcopy(positive)
        modp.bump(next(iter(mutant["cert"]["system"].values())))
        fails(lambda: modp.check(mutant), "system_identity")
        missing = copy.deepcopy(positive)
        missing["cert"]["system"].pop(next(iter(missing["cert"]["system"])))
        fails(lambda: modp.check(missing), "system_keys")
        modp.check(positive)
    case("supplied system: positive before/after, perturbed coefficient and missing generator red", systems)

    def sturm_zero_terms():
        positive = copy.deepcopy(null)
        n, _ = decode_g6(positive["g6"])
        frame, sat = positive["cert"]["frame"], positive["cert"]["sat"]
        labels = [i for i in range(n) if i not in frame]
        nv = 2 * (n - 2) + len(sat)
        foreign = [0] * nv
        foreign[1] = 1
        positive["cert"].update(type="real", sturm=f"x_{labels[0]}",
            f=[["1", [0] * nv], ["0", foreign]])
        modp.check(positive)
        mutant = copy.deepcopy(positive)
        mutant["cert"]["f"][1][0] = "1"
        fails(lambda: modp.check(mutant), "cofactor_identity")
        modp.check(positive)
    case("constant Sturm target with permitted zero foreign-variable term; coefficient mutation red", sturm_zero_terms)

    def field_controls():
        for prime in modp.PRIMES:
            f = modp.ModularField([Fraction(-3), Fraction(0), Fraction(1)], prime)
            root = f.element([0, 1])
            require(f.mul(root, root) == f.scalar(3), "selftest", "extension-field root^2 != 3")
            require(f.mul(root, f.inverse(root)) == f.one, "selftest", "extension-field inverse")
        fails(lambda: modp.ModularField([Fraction(-3), Fraction(0), Fraction(1)], modp.PRIMES[0]).rat(Fraction(1, modp.PRIMES[0])),
              "modular_denominator")
    case("modular extension fields and denominator red", field_controls)

    def parallel():
        raw_trees = list(lines(Path(a.samples) / "trees.jsonl"))
        results = list(bounded_map(modp.worker, [(number, raw, 3, 20261007) for number, raw in raw_trees], jobs=2))
        require(len(results) == len(raw_trees) and all(r["status"] == "PASS" for r in results),
                "selftest", "two-worker tree processing did not accept the actual positive samples")
        require(len({r["line"] for r in results}) == len(raw_trees), "selftest", "parallel worker duplicated a task")
    case("two-worker processing of actual trees covering all five moves and three field degrees", parallel)

    def l2_control():
        original = next(record(raw) for _, raw in lines(Path(a.samples) / "trees.jsonl")
                        if record(raw)["g6"] == "J??EPgKphr?")
        modp.check(original)
        mutant = copy.deepcopy(original)
        todo = [mutant["cert"]["witness"]["tree"]]
        while todo:
            node = todo.pop()
            if node["move"]["kind"] == "L2":
                actual = {tuple(sorted(e)) for e in node["edges"]}
                forced = next(e for e in node["move"]["edges"] if tuple(sorted(e)) not in actual)
                node["move"]["edges"] = [forced[:], forced[:]]
                node["move"]["omega"] = 1
                break
            todo.extend(node["children"])
        else:
            raise Failure("selftest", "L2 sample has no L2 node")
        fails(lambda: modp.check(mutant), "tree_move")
        modp.check(original)
    case("L2 duplicated nonedge red, with genuine original before/after", l2_control)

    def collisions():
        folder = Path(a.out).resolve().parent / "collision-evidence"
        folder.mkdir(exist_ok=True)
        evidence = folder / "report.json"
        contents = '{"retained":"input evidence"}\n'
        evidence.write_text(contents)
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).parent / "independent_audit.py"),
            str(Path(a.samples) / "first2000-closed.g6"), str(Path(a.samples) / "first2000-closed.jsonl"),
            "--sample", "--outdir", str(folder), "--compare-report", str(evidence)],
            capture_output=True, text=True, check=False)
        require(result.returncode != 0 and "overwrite" in result.stderr and evidence.read_text() == contents,
                "selftest", "CLI collision rejection overwrote supplied evidence")
    case("audit CLI output collision is red and preserves supplied input bytes", collisions)

    def import_guard():
        for path in Path(__file__).parent.glob("*.py"):
            module = ast.parse(path.read_text())
            for node in ast.walk(module):
                if isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                elif isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                else:
                    continue
                require(not any("gp10check" in s or "gp11check" in s or "udcheck" in s or s.startswith("flint") for s in modules),
                        "selftest", f"forbidden import in {path.name}")
        require("flint" not in sys.modules and "sympy" not in sys.modules, "selftest", "external arithmetic module was loaded")
    case("static checker/FLINT import guard; no flint or sympy loaded", import_guard)
    rep = {"status": "PASS", "cases": done, "seconds": round(time.monotonic() - t0, 3),
           "source_hashes": source_hashes("selftest.py", "independent_core.py", "modp_identities.py", "forbidden_catalogue.py")}
    write_json(a.out, rep)
    print(json.dumps({"status": "PASS", "cases": len(done), "seconds": rep["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
