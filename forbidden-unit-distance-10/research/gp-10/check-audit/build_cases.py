#!/usr/bin/env python3
"""Generate bounded paired audit fixtures without modifying the checker."""
import copy
from fractions import Fraction
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
from runner import load_checker
ck = load_checker()
HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
FIX = HERE.parent / "check/fixtures"
INDEX = []


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def jsonl(path, records):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def read(name):
    return json.loads((FIX / (name + ".json")).read_text())


def add(name, records, *, status="ACCEPT", reason="verified", record_reason=None,
        parent=None, mutation=None, note="", hosts=None, options=None, source=None):
    path = CASES / name
    path.mkdir(parents=True, exist_ok=True)
    if source is not None:
        for src in source.iterdir():
            if src.is_file() and src.suffix in (".g6", ".json", ".jsonl") and not src.name.startswith("observed"):
                shutil.copyfile(src, path / src.name)
    else:
        data = "".join(c + "\n" for c in sorted({r["g6"] for r in records}))
        (path / "input.g6").write_text(data)
        (path / "UNKNOWN.g6").write_text("".join(sorted(r["g6"] + "\n" for r in records if r["verdict"] == "unknown")))
        jsonl(path / "records.jsonl", records)
        manifest = {"profile": "sample", "input": "input.g6", "input_sha256": hashlib.sha256(data.encode()).hexdigest(), "records": ["records.jsonl"]}
        manifest.update(options or {})
        if hosts is not None:
            manifest["hosts"] = "hosts.jsonl"
            jsonl(path / "hosts.jsonl", hosts)
        write(path / "run.json", manifest)
    INDEX.append({"name": name, "status": status, "reason": reason, "record_reason": record_reason,
                  "parent": parent, "mutation": mutation, "note": note, "kind": "run"})
    return path


def positive(name, record, note=""):
    return add(name, [record], note=note)


def alter(obj, path, value):
    result = copy.deepcopy(obj)
    node = result
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = copy.deepcopy(value)
    return result


def red(name, parent, path, value, reason, note=""):
    base = json.loads((CASES / parent / "records.jsonl").read_text())
    record = alter(base, path, value)
    assert json.dumps(record, sort_keys=True) != json.dumps(base, sort_keys=True)
    return add(name, [record], status="REJECT", reason="records_rejected", record_reason=reason,
               parent=parent, mutation={"file": "records.jsonl", "path": path, "scope": "record"}, note=note)


def run_change(name, parent, filename, transform, reason, record_reason=None, note=""):
    path = add(name, [], source=CASES / parent, status="REJECT", reason=reason,
               record_reason=record_reason, parent=parent,
               mutation={"file": filename, "scope": "file"}, note=note)
    old = (path / filename).read_text()
    new = transform(old)
    assert old != new
    (path / filename).write_text(new)
    return path


def unknown(code):
    return {"g6": code, "verdict": "unknown", "cert": {"reason": "audit fixture, no geometry search", "budget": {"seconds": 0}}}


def canon(n, edges):
    graph = ck.Graph(n, {tuple(sorted(e)) for e in edges})
    code = ck.canonical(graph)
    iso = next(ck.nx.algorithms.isomorphism.GraphMatcher(graph.nx(), ck.decode(code).nx()).isomorphisms_iter())
    return code, iso


def exact(n, edges, points, poly=None, interval=None):
    poly = [0, 1] if poly is None else poly
    interval = ["-1", "1"] if interval is None else interval
    code, iso = canon(n, edges)
    d = len(poly) - 1
    coords = [None] * n
    for i, xy in enumerate(points):
        coords[iso[i]] = [[str(Fraction(v)) for v in list(axis) + [0] * (d - len(axis))] for axis in xy]
    return {"g6": code, "verdict": "embedded", "cert": {"type": "exact", "field": {"minpoly": poly, "interval": interval}, "coords": coords}}


def tree_k4_isolates(n):
    code, iso = canon(n, itertools.combinations(range(4), 2))
    base = read("k4-tree")
    tree = base["cert"]["witness"]["tree"]
    rows = []
    for row in tree["A"]:
        new = [0] * n
        for i, x in enumerate(row):
            new[iso[i]] = x
        rows.append(new)
    tree["A"] = rows
    tree["edges"] = [list(e) for e in sorted(ck.decode(code).edges)]
    tree["move"]["pair"] = [iso[v] for v in tree["move"]["pair"]]
    base["g6"] = code
    return base


def main():
    CASES.mkdir(exist_ok=True)
    # Reuse certificates, never run the producer fixture generator.
    for spec in json.loads((FIX / "cases.json").read_text()):
        name = "existing-" + spec["name"]
        record = read(spec["name"])
        if spec["status"] == "ACCEPT":
            positive(name, record, "Copied checker fixture, replayed independently through the full run path.")
        else:
            add(name, [record], status="REJECT", reason="records_rejected", record_reason=spec["reason"],
                parent="existing-" + Path(spec["positive"]).stem,
                mutation={"file": "records.jsonl", "path": spec["mutation_path"], "scope": "record"},
                note="Copied checker mutation with its declared positive and single changed field.")
    positives = ("pointers", "mixed", "unknown", "refutation-pointer", "frozen-pointer", "tu-refuted-pointer", "minimality", "conditional-minimality")
    for name in positives:
        add("run-" + name, [], source=FIX / name)
    for spec in json.loads((FIX / "run-cases.json").read_text()):
        add("run-" + spec["name"], [], source=FIX / spec["name"], status="REJECT", reason=spec["reason"], record_reason=spec["record_reason"],
            parent="run-" + spec["positive"], mutation={"file": spec["changed_file"], "scope": "file"})

    c4 = read("c4")
    for name, value, reason in (
        ("zero-denominator", "1/0", "rational"), ("signed-denominator", "0/-1", "rational"),
        ("rational-space", " 0", "rational"), ("rational-decimal", "0.0", "rational"),
        ("rational-float", 0.0, "rational"), ("rational-bool", False, "rational")):
        red(name, "existing-c4", ["cert", "coords", 0, 0, 0], value, reason)
    for name, value in (("rational-plus", "+0/1"), ("rational-negative-zero", "-0/1"), ("rational-leading-zeroes", "000/001")):
        p = alter(c4, ["cert", "coords", 0, 0, 0], value)
        positive(name, p, "Alternate exact spelling of zero is valid.")
        red(name + "-red", name, ["cert", "coords", 0, 0, 0], "1/0", "rational")
    for name, value, reason in (
        ("minpoly-constant", [1], "minpoly"), ("minpoly-zero", [0], "minpoly"),
        ("minpoly-leading-zero", [0, 1, 0], "minpoly"), ("minpoly-boolean", [False, 1], "minpoly"),
        ("endpoint-root", ["0", "1"], "interval_sign_change"), ("interval-reversed", ["1", "-1"], "interval_sign_change")):
        path = ["cert", "field", "interval" if name.startswith(("endpoint", "interval")) else "minpoly"]
        red(name, "existing-c4", path, value, reason)
    red("coordinate-missing-vertex", "existing-c4", ["cert", "coords"], c4["cert"]["coords"][:-1], "coordinate_count")
    red("coordinate-extra-vertex", "existing-c4", ["cert", "coords"], c4["cert"]["coords"] + [c4["cert"]["coords"][0]], "coordinate_count")
    red("coordinate-not-reduced", "existing-c4", ["cert", "coords", 0, 0], ["0", "1"], "coordinate_degree")
    red("coordinate-not-pair", "existing-c4", ["cert", "coords", 0], [["0"]], "coordinate_shape")
    red("coordinate-wrong-labels", "existing-c4", ["cert", "coords"], list(reversed(c4["cert"]["coords"][:3])) + c4["cert"]["coords"][3:], "edge_equation")
    positive("large-rational", exact(2, [], [([0], [0]), ([Fraction(1, 10**1000)], [0])]))
    red("large-rational-collision", "large-rational", ["cert", "coords", 1, 0, 0], "0", "exact_collision")
    for name, poly, iv in (("multiple-roots", [0, -4, 0, 1], ["-3", "3"]),
                           ("repeated-root-odd", [0, 0, 0, 1], ["-1", "1"]),
                           ("repeated-root-mixed", [2, -3, 0, 1], ["-3", "2"])):
        record = exact(4, ck.decode(c4["g6"]).edges,
                       [([int(x[0])], [int(y[0])]) for x, y in c4["cert"]["coords"]], poly, iv)
        positive(name, record, "Sign change and common certified distinctness suffice; irreducibility and root uniqueness are not required.")
        red(name + "-collision", name, ["cert", "coords", 3], record["cert"]["coords"][0], "exact_collision")
    shared = exact(4, [], [([i], [0]) for i in range(4)], [0, -4, 0, 1], ["-3", "3"])
    positive("shared-root", shared)
    red("shared-root-trap", "shared-root", ["cert", "coords"],
        [[["0", "0", "0"], ["0", "0", "0"]]] + [[[str(a), "1", "0"], ["0", "0", "0"]] for a in (-2, 0, 2)], "exact_collision")
    refine = exact(2, [], [([0], [0]), ([-1, 1], [0])], [-2, 0, 1], ["1", "2"])
    positive("interval-refinement", refine)
    red("interval-refinement-red", "interval-refinement", ["cert", "coords", 1, 0], ["0", "0"], "exact_collision")

    # Strong graph-identity attacks plus a bounded sweep of the frozen forbidden set.
    red("embed-K4", "existing-c4", ["g6"], "C~", "edge_equation")
    checker = ck.Checker()
    for n in sorted({g.n for g in checker.forbidden}):
        positive(f"edgeless-{n}", exact(n, [], [([i], [0]) for i in range(n)]))
    for i, (code, graph) in enumerate(zip(checker.forbidden_codes, checker.forbidden)):
        red(f"embed-forbidden-{i:02d}", f"edgeless-{graph.n}", ["g6"], code, "edge_equation",
            "Retarget a genuine distinct rational embedding by changing only g6. This checks graph binding, not a search for embeddings.")
    targets = {"C4": c4["g6"], "Moser": read("moser")["g6"], **{k: v for k, v in ck.named_graphs().items() if k in ("Petersen", "pentagonal_prism", "extremal")}}
    for n in sorted({ck.decode(code).n for code in targets.values()}):
        positive(f"tree-k4-isolates-{n}", tree_k4_isolates(n))
    for name, code in targets.items():
        n = ck.decode(code).n
        red("refute-UDG-" + name, f"tree-k4-isolates-{n}", ["g6"], code, "tree",
            "Known UDG named in the brief; a same-order forbidden graph tree must not certify this graph.")
    kt = read("k4-tree")
    red("tree-root-edges", "existing-k4-tree", ["cert", "witness", "tree", "edges"], kt["cert"]["witness"]["tree"]["edges"][:-1], "tree")
    red("tree-root-rowspace", "existing-k4-tree", ["cert", "witness", "tree", "A"], [], "tree")
    red("tree-reducible-field", "existing-k4-tree", ["cert", "witness", "field", "minpoly"], [0, 0, 0, 1], "tree")
    red("tree-endpoint-root", "existing-k4-tree", ["cert", "witness", "field", "interval"], [0, 1], "tree")
    red("tree-leaf-children", "existing-k4-tree", ["cert", "witness", "tree", "children"], [{}], "tree")
    red("tree-forged-move", "existing-k4-tree", ["cert", "witness", "tree", "move", "kind"], "accept", "tree")

    # Sparse algebra parsing and regeneration attacks.
    null = read("k4-isolate-null")
    cert = null["cert"]
    key = next(k for k, p in cert["cofactors"].items() if p)
    red("cofactor-unexpected-key", "existing-k4-isolate-null", ["cert", "cofactors"], {**cert["cofactors"], "e:0,1": []}, "cofactor_generator")
    renamed = dict(cert["system"])
    renamed["invented"] = renamed.pop(next(iter(renamed)))
    red("system-renamed-generator", "existing-k4-isolate-null", ["cert", "system"], renamed, "system_mismatch")
    red("system-pinned-third-point", "existing-k4-isolate-null", ["cert", "system"], {**cert["system"], "pin:x_0": [["1", [1, 0, 0, 0, 0, 0]]]}, "system_mismatch")
    red("system-changed-polynomial", "existing-k4-isolate-null", ["cert", "system", next(iter(cert["system"]))], [], "system_mismatch")
    term = cert["cofactors"][key][0]
    red("sparse-duplicate-monomial", "existing-k4-isolate-null", ["cert", "cofactors", key], cert["cofactors"][key] + [term], "sparse_duplicate_monomial")
    red("sparse-negative-exponent", "existing-k4-isolate-null", ["cert", "cofactors", key, 0, 1, 0], -1, "sparse_exponents")
    red("sparse-boolean-exponent", "existing-k4-isolate-null", ["cert", "cofactors", key, 0, 1, 0], True, "sparse_exponents")
    red("sparse-extra-variable", "existing-k4-isolate-null", ["cert", "cofactors", key, 0, 1], term[1] + [0], "sparse_exponents")
    sat = read("k23-saturated-null")["cert"]["sat"]
    red("saturation-repeated", "existing-k23-saturated-null", ["cert", "sat"], sat + [sat[0]], "sat_duplicate")
    red("saturation-reversed", "existing-k23-saturated-null", ["cert", "sat", 0], list(reversed(sat[0])), "sat_pair_order")
    red("saturation-self-pair", "existing-k23-saturated-null", ["cert", "sat", 0], [sat[0][0], sat[0][0]], "pair")
    red("saturation-out-of-range", "existing-k23-saturated-null", ["cert", "sat", 0], [0, 5], "pair")
    red("saturation-variable-order", "existing-k23-saturated-null", ["cert", "sat"], list(reversed(sat)), "system_mismatch")
    adjacent = copy.deepcopy(null)
    ac = adjacent["cert"]
    ac.pop("system")
    ac["sat"] = [sorted(ac["frame"])]
    ac["cofactors"] = {k: [[c, e + [0]] for c, e in p] for k, p in ac["cofactors"].items()}
    positive("saturation-adjacent", adjacent, "Saturating an edge is redundant and mathematically valid.")
    red("saturation-adjacent-red", "saturation-adjacent", ["cert", "sat"], ac["sat"] * 2, "sat_duplicate")
    real = copy.deepcopy(adjacent)
    rc = real["cert"]
    rc["type"] = "real"
    rc["cofactors"] = {k: [[c, e] for c, e in p] + [[c, e[:-1] + [2]] for c, e in p] for k, p in ac["cofactors"].items()}
    nv = len(term[1]) + 1
    rc["f"] = [["1", [0] * nv], ["1", [0] * (nv - 1) + [2]]]
    rc["sturm"] = "t_0"
    positive("real-saturation-variable", real, "Multiply a verified null identity by t_0^2+1; every saturation variable is real.")
    red("real-saturation-variable-red", "real-saturation-variable", ["cert", "sturm"], "x_0", "sturm_multivariate")
    red("real-nonexistent-variable", "real-saturation-variable", ["cert", "sturm"], "t_1", "sturm_variable")
    red("sos-zero-weight", "existing-k4-real-sos", ["cert", "sos", "squares", 0, 0], "0", "sos_weight_positive")
    red("sos-negative-constant", "existing-k4-real-sos", ["cert", "sos", "c"], "-1", "sos_constant_positive")
    red("real-both-proof-types", "existing-k4-real-sos", ["cert", "sturm"], "x_0", "real_proof_choice")

    # Pointer checks run through the actual dependency resolver.
    def rec_change(path, value):
        def change(raw):
            rows = [json.loads(s) for s in raw.splitlines()]
            rows[0] = alter(rows[0], path, value)
            return "".join(json.dumps(r) + "\n" for r in rows)
        return change
    for name, value, reason in (("pointer-negative", [-1, 1], "map_range"),
                                ("pointer-too-large", [0, 3], "map_range"),
                                ("pointer-boolean", [False, 1], "map_range"),
                                ("pointer-direction", [0, 1, 2], "map_length")):
        run_change(name, "run-pointers", "records.jsonl", rec_change(["cert", "map"], value), "records_rejected", reason)
    run_change("refutation-pointer-direction", "run-refutation-pointer", "records.jsonl", rec_change(["cert", "map"], list(range(5))), "records_rejected", "map_length")
    run_change("frozen-index-mismatch", "run-frozen-pointer", "records.jsonl", rec_change(["cert", "index"], 1), "records_rejected", "forbidden_index_graph")
    run_change("frozen-index-negative", "run-frozen-pointer", "records.jsonl", rec_change(["cert", "index"], -1), "records_rejected", "forbidden_not_in_force")
    run_change("frozen-index-out-of-range", "run-frozen-pointer", "records.jsonl", rec_change(["cert", "index"], 74), "records_rejected", "forbidden_not_in_force")
    run_change("frozen-index-boolean", "run-frozen-pointer", "records.jsonl", rec_change(["cert", "index"], True), "records_rejected", "schema")
    edge = exact(2, [(0, 1)], [([0], [0]), ([1], [0])])
    tri = read("triangle")
    iso2 = exact(2, [], [([0], [0]), ([1], [0])])
    eptr = {"g6": edge["g6"], "verdict": "embedded", "cert": {"type": "super", "g6": tri["g6"], "map": [0, 1]}}
    iptr = {"g6": iso2["g6"], "verdict": "embedded", "cert": {"type": "super", "g6": edge["g6"], "map": [0, 1]}}
    add("pointer-chain", [iptr, eptr, tri, unknown("C~")])
    def at_row(raw, row_number, path, value):
        rows = [json.loads(line) for line in raw.splitlines()]
        rows[row_number] = alter(rows[row_number], path, value)
        return "".join(json.dumps(row) + "\n" for row in rows)
    run_change("pointer-chain-through-unknown", "pointer-chain", "records.jsonl",
               lambda raw: at_row(raw, 1, ["cert", "g6"], "C~"),
               "records_rejected", "pointer_target_not_accepted_embedded",
               "One pointer g6 field targets an already declared unknown. Both downstream pointers must reject.")
    diamond_edges = set(itertools.combinations(range(4), 2)) - {(2, 3)}
    diamond = exact(4, diamond_edges, [([0], [0]), ([1], [0]), ([Fraction(1,2)], [0, Fraction(1,2)]), ([Fraction(1,2)], [0, Fraction(-1,2)])], [-3, 0, 1], ["1", "2"])
    unknown_code = diamond["g6"]
    rrecords = list(map(json.loads, (CASES / "run-refutation-pointer/records.jsonl").read_text().splitlines()))
    add("refutation-chain", rrecords + [unknown(unknown_code)])
    run_change("refutation-chain-through-unknown", "refutation-chain", "records.jsonl",
               lambda raw: at_row(raw, 0, ["cert", "g6"], unknown_code),
               "records_rejected", "pointer_target_not_accepted_refuted")
    for name, path, value, reason in (
        ("tu-map-repeated", ["cert", "steps", 0, "map"], [0] * 6, "map_not_injective"),
        ("tu-map-outside", ["cert", "steps", 0, "map"], [99] * 6, "map_range"),
        ("tu-gadget-negative", ["cert", "steps", 0, "gadget"], -1, "gadget_index"),
        ("tu-no-steps", ["cert", "steps"], [], "tu_steps"),
        ("tu-no-terminal-proof", ["cert", "end"], {}, "schema"),
        ("tu-terminal-index", ["cert", "end", "forbidden"], 74, "forbidden_not_in_force")):
        red(name, "existing-tu-chain", path, value, reason)

    # Freeze, minimality, syntax, and profile controls.
    run_change("minimality-omitted-minimal", "run-minimality", "claim.g6", lambda _: "", "minimality_claim_mismatch")
    run_change("conditional-minimality-omitted", "run-conditional-minimality", "run.json", lambda raw: json.dumps({**json.loads(raw), "minimal_claim": "UNKNOWN.g6"}) + "\n", "minimality_claim_mismatch")
    run_change("input-wrong-hash", "run-mixed", "run.json", lambda raw: json.dumps({**json.loads(raw), "input_sha256": "0" * 64}) + "\n", "input_hash")
    run_change("empty-record-stream", "run-mixed", "records.jsonl", lambda _: "", "coverage")
    run_change("records-no-final-newline", "run-mixed", "records.jsonl", lambda raw: raw.rstrip("\n"), "line_format")
    run_change("records-blank-line", "run-mixed", "records.jsonl", lambda raw: raw + "\n", "line_format")
    run_change("unknown-file-absent", "run-unknown", "run.json", lambda raw: json.dumps({**json.loads(raw), "unknown": "absent.g6"}) + "\n", "unknown_file_missing")
    run_change("duplicate-json-key", "existing-c4", "records.jsonl", lambda raw: raw.replace('"verdict": "embedded"', '"verdict": "embedded", "verdict": "embedded"'), "records_rejected", "duplicate_json_key")
    run_change("duplicate-generator-key", "existing-k4-isolate-null", "records.jsonl", lambda raw: raw.replace('"cofactors": {', '"cofactors": {"duplicate": [], "duplicate": [], '), "records_rejected", "duplicate_json_key")
    run_change("json-nan", "existing-c4", "records.jsonl", lambda raw: raw.replace('"0"', 'NaN', 1), "records_rejected", "json_constant")
    graph = ck.decode(c4["g6"])
    alias = None
    for permutation in itertools.permutations(range(graph.n)):
        code = ck.encode(ck.Graph(graph.n, {tuple(sorted((permutation[u], permutation[v]))) for u, v in graph.edges}))
        if code != c4["g6"]:
            alias = code
            break
    run_change("coverage-noncanonical-record", "existing-c4", "records.jsonl", rec_change(["g6"], alias), "records_rejected", "noncanonical_g6")
    for n in range(4, 8):
        codes = (HERE.parent / f"data/B{n}p.g6").read_text().splitlines()
        add(f"control-sample-B{n}p", [unknown(code) for code in codes], note="Complete frozen input coverage, declared unknowns, sample only.")
        run_change(f"unsupported-B{n}p", f"control-sample-B{n}p", "run.json",
                   lambda raw, n=n: json.dumps({**json.loads(raw), "profile": f"B{n}p"}) + "\n", "profile",
                   note="Contract amendment requires this profile. Rejection is a reproduced implementation gap, not a soundness exploit.")
    # Frozen-list labels are deliberately asymmetric in these tests.
    index = next(i for i, g in enumerate(checker.forbidden) if ck.encode(g) != checker.forbidden_codes[i] and g.n >= 6)
    source = checker.forbidden[index]
    code = checker.forbidden_codes[index]
    indexed = {"g6": code, "verdict": "refuted", "cert": {"type": "sub", "g6": code, "index": index, "map": list(range(source.n))}}
    positive("frozen-canonical-labels", indexed, "F9 index " + str(index) + "; R-ptr maps use canonical graph labels.")
    iso = next(ck.nx.algorithms.isomorphism.GraphMatcher(source.nx(), ck.decode(code).nx()).isomorphisms_iter())
    red("frozen-stored-labels-confused", "frozen-canonical-labels", ["cert", "map"], [iso[i] for i in range(source.n)], "map_not_edge_preserving")
    gadget = checker.gadgets[0]
    offset = gadget["n"]
    edges = {tuple(e) for e in gadget["edges"]} | {(u + offset, v + offset) for u, v in source.edges}
    code, iso = canon(offset + source.n, edges)
    tu = {"g6": code, "verdict": "refuted", "cert": {"type": "tu", "steps": [{"gadget": 0, "map": [iso[i] for i in range(offset)], "pair": [iso[i] for i in gadget["pair"]]}], "end": {"forbidden": index, "map": [iso[i + offset] for i in range(source.n)]}}}
    positive("tu-frozen-stored-labels", tu, "F9 index " + str(index) + "; TU end maps use stored JSON labels.")
    canon_iso = next(ck.nx.algorithms.isomorphism.GraphMatcher(ck.decode(checker.forbidden_codes[index]).nx(), source.nx()).isomorphisms_iter())
    red("tu-frozen-canonical-labels-confused", "tu-frozen-stored-labels", ["cert", "end", "map"], [iso[canon_iso[i] + offset] for i in range(source.n)], "map_not_edge_preserving")
    trecords = list(map(json.loads, (CASES / "run-tu-refuted-pointer/records.jsonl").read_text().splitlines()))
    add("tu-pointer-with-unknown", trecords + [unknown(unknown_code)])
    run_change("tu-target-unknown", "tu-pointer-with-unknown", "records.jsonl",
               lambda raw: at_row(raw, 0, ["cert", "end", "refuted"], unknown_code),
               "records_rejected", "pointer_target_not_accepted_refuted")

    add("derive-k4-disabled", [kt], options={"forbidden_limit": 0})
    run_change("derive-requires-deletion", "derive-k4-disabled", "run.json",
               lambda raw: json.dumps({**json.loads(raw), "derive": True}) + "\n", "minimality_deletion_missing")
    path = add("derive-k4-complete", [kt, diamond], options={"forbidden_limit": 0, "derive": True, "minimal_claim": "claim.g6"})
    (path / "claim.g6").write_text("C~\n")
    run_change("derive-k4-omitted", "derive-k4-complete", "claim.g6", lambda _: "", "minimality_claim_mismatch")
    raw_edges = set(itertools.combinations(range(4), 2)) | {(0, 4), (1, 4)}
    code, iso = canon(5, raw_edges)
    graph = ck.decode(code)
    rows, seen = [], set()
    for vertices in itertools.combinations(range(graph.n), 4):
        for tail in itertools.permutations(vertices[1:]):
            cycle = (vertices[0],) + tail
            if cycle[1] > cycle[-1] or not all(tuple(sorted((cycle[j], cycle[(j+1)%4]))) in graph.edges for j in range(4)):
                continue
            row = [0] * graph.n
            for j, vertex in enumerate(cycle):
                row[vertex] = (-1)**j
            key_row = min(tuple(row), tuple(-x for x in row))
            if key_row not in seen:
                seen.add(key_row)
                rows.append(row)
    obstructed = {"g6": code, "verdict": "refuted", "cert": {"type": "tree", "witness": {"field": {"minpoly": [0, 1], "interval": [-1, 1]}, "tree": {"edges": [list(e) for e in sorted(graph.edges)], "A": rows, "move": {"kind": "L1a", "pair": [iso[0], iso[1]]}, "children": []}}}}
    add("block-forbidden-baseline", [obstructed], options={"forbidden_limit": 0})
    run_change("block-forbidden-shortcut", "block-forbidden-baseline", "run.json",
               lambda raw: json.dumps({**json.loads(raw), "derive": True}) + "\n", "block_forbidden")

    # A nonzero constant is a sound, slightly broader R-real Sturm case.
    constant = copy.deepcopy(null)
    constant["cert"]["type"] = "real"
    constant["cert"]["f"] = [["1", [0] * len(term[1])]]
    constant["cert"]["sturm"] = "x_0"
    positive("real-constant", constant, "A nonzero constant has no real zero although it involves no variable.")
    red("real-constant-zero-target", "real-constant", ["cert", "f"], [], "cofactor_identity")

    # Bounded direct tests reach the root-count rejection boundary without invalidating an identity first.
    def sturm_case(name, poly, count, parent=None, coefficient=None, reason="returned"):
        path = CASES / name
        path.mkdir(exist_ok=True)
        write(path / "polynomial.json", poly)
        INDEX.append({"name": name, "kind": "sturm", "status": "ACCEPT" if count == 0 else "REJECT",
                      "reason": reason, "record_reason": None, "count": count, "parent": parent,
                      "mutation": None if parent is None else {"scope": "polynomial", "file": "polynomial.json", "path": [coefficient]},
                      "note": "Helper return value, not a full run ACCEPT. Root count is known from explicit quadratic factors."})
    for a in range(-3, 4):
        for b in (1, 2):
            name = f"sturm-positive-{a}-{b}"
            sturm_case(name, [a*a + b*b, -2*a, 1], 0)
            sturm_case(name + "-two-roots", [a*a - b*b, -2*a, 1], 2, name, 0)
            sturm_case(name + "-repeated-root", [a*a, -2*a, 1], 1, name, 0)
    sturm_case("sturm-repeated-complex", [1, 0, 2, 0, 1], 0)
    sturm_case("sturm-quartic-real", [-1, 0, 2, 0, 1], 2, "sturm-repeated-complex", 0)
    sturm_case("sturm-quartic-repeated-real", [0, 0, 2, 0, 1], 1, "sturm-repeated-complex", 0)
    sturm_case("sturm-constant", [1], 0)
    sturm_case("sturm-zero", [0], None, "sturm-constant", 0, "sturm_zero_polynomial")
    red("moser-coordinate-red", "existing-moser", ["cert", "coords", 0, 0, 0], "100", "edge_equation")
    red("k23-tree-collision-red", "existing-k23-tree", ["cert", "witness", "tree", "move", "pair"], [0, 0], "tree")
    run_change("tu-refuted-pointer-map-red", "run-tu-refuted-pointer", "records.jsonl",
               lambda raw: at_row(raw, 0, ["cert", "end", "map"], [0] * 4), "records_rejected", "map_not_injective")
    tree_details = {
        "k23-tree-collision-red": "tree: R-tree.tree.move.pair: invalid distinct vertices",
        "existing-tree-collision-pair": "tree: R-tree.tree.move.pair: invalid distinct vertices",
        "tree-root-edges": "tree: R-tree.tree.edges: inconsistent with the parent move",
        "tree-root-rowspace": "tree: R-tree.tree.A: row space is inconsistent with the claimed constraints",
        "tree-reducible-field": "tree: R-tree.field.minpoly: polynomial is reducible over Q",
        "tree-endpoint-root": "tree: isolating interval endpoint is a root",
        "tree-leaf-children": "tree: R-tree.tree: L1a contradiction must be a leaf",
        "tree-forged-move": "tree: R-tree.tree.move.kind: unsupported move 'accept'",
    }
    for spec in INDEX:
        if spec["name"].startswith("refute-UDG-"):
            spec["record_detail"] = "tree: R-tree.tree.edges: inconsistent with the parent move"
        elif spec["name"] in tree_details:
            spec["record_detail"] = tree_details[spec["name"]]
    write(CASES / "index.json", INDEX)
    print("BUILD_CASES", len(INDEX))


if __name__ == "__main__":
    main()
