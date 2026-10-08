#!/usr/bin/env python3
"""Build amendment 5 fixtures from our own previously verified null identities."""
import copy
from fractions import Fraction
import itertools
import json
import os
from pathlib import Path
import sys
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import gp10check as ck

FIX = ck.HERE / "fixtures"
OUT = FIX / "round3"


def sparse(poly):
    return [[c, [int(x) for x in exps]] for c, exps in ck.serialize_polynomial(poly)]


def main():
    OUT.mkdir(exist_ok=True)
    checker = ck.Checker()
    cases, positives = [], {}

    def write(name, record, **meta):
        (OUT / (name + ".json")).write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        cases.append({"name": name, "file": name + ".json", **meta})

    def positive(name, record):
        assert checker.verify(record)[0] is None, name
        positives[name] = json.loads(json.dumps(record))
        write(name, record, status="ACCEPT")
        return record

    absent = object()

    def red(name, parent, path, value=absent, reason="schema", detail=None):
        record = copy.deepcopy(positives[parent])
        obj = record
        for key in path[:-1]:
            obj = obj[key]
        if value is absent:
            del obj[path[-1]]
        else:
            obj[path[-1]] = copy.deepcopy(value)
        try:
            checker.verify(record)
        except ck.Rejection as exc:
            assert exc.reason == reason, (name, reason, str(exc))
            if detail:
                assert detail in exc.detail, (name, detail, exc.detail)
        else:
            raise AssertionError(name + " accepted")
        write(name, record, status="REJECT", positive=parent + ".json", mutation_path=path,
              reason=reason, detail=detail)

    def split(source, separate):
        original = ck.read_json(FIX / source)
        assert checker.verify(original)[0] is None
        cert = original["cert"]
        ctx, names, gens = ck.regenerate(ck.decode(original["g6"]), cert["frame"], cert["sat"])
        parse = lambda p: ck.polynomial(p, ctx, len(names))
        cof = {key: sparse(parse(raw)) for key, raw in cert["cofactors"].items()}
        items = list(cof.items())
        cut = max(1, len(items) // 2)
        groups = [dict(items[:cut]), dict(items[cut:])]
        polys = [sum((parse(raw) * gens[key] for key, raw in group.items()), ctx.constant(0)) for group in groups]
        assert sum(polys, ctx.constant(0)) == ctx.constant(1)
        assert all(p != ctx.constant(1) for p in polys)
        one = sparse(ctx.constant(1))
        rows = [{"poly": sparse(polys[0]), "cofactors": groups[0]}]
        if separate:
            rows += [{"poly": sparse(polys[1]), "cofactors": groups[1]},
                     {"poly": one, "cofactors": {"aux:0": one, "aux:1": one}}]
        else:
            rows.append({"poly": one, "cofactors": {**groups[1], "aux:0": one}})
        record = {"g6": original["g6"], "verdict": "refuted", "cert": {
            "type": "null-dag", "frame": cert["frame"], "sat": cert["sat"], "rows": rows}}
        return record, ctx, names

    k23, ctx, names = split("k23-saturated-null.json", True)
    positive("k23-null-dag", k23)
    k4, ctx4, names4 = split("k4-isolate-null.json", False)
    positive("k4-isolate-null-dag", k4)
    real = copy.deepcopy(k23)
    f = sparse(ctx.gens()[0] ** 2 + 1)
    real["cert"].update(type="real-dag", f=f, sturm=names[0])
    real["cert"]["rows"].append({"poly": f, "cofactors": {"aux:2": f}})
    positive("k23-real-dag-sturm", real)
    sos = copy.deepcopy(k4)
    f4 = sparse(ctx4.gens()[0] ** 2 + 1)
    sos["cert"].update(type="real-dag", f=f4,
                       sos={"c": "1", "squares": [["1", sparse(ctx4.gens()[0])]]})
    sos["cert"]["rows"].append({"poly": f4, "cofactors": {"aux:1": f4}})
    positive("k4-real-dag-sos", sos)
    constant = copy.deepcopy(k23)
    constant["cert"].update(type="real-dag", f=sparse(ctx.constant(1)), sturm=names[0])
    positive("real-dag-constant", constant)
    alternate = copy.deepcopy(k23)
    alternate["cert"]["rows"][2]["cofactors"]["aux:0"][0][0] = "+02/02"
    positive("dag-rational-spelling", alternate)
    zero = copy.deepcopy(k23)
    zero["cert"]["rows"] = [{"poly": [], "cofactors": {}}, *zero["cert"]["rows"]]
    zero["cert"]["rows"][3]["cofactors"] = {"aux:1": sparse(ctx.constant(1)),
                                             "aux:2": sparse(ctx.constant(1)), "aux:0": []}
    positive("dag-zero-row", zero)
    maximum = copy.deepcopy(k23)
    one = sparse(ctx.constant(1))
    for k in range(len(maximum["cert"]["rows"]), 256):
        maximum["cert"]["rows"].append({"poly": one, "cofactors": {f"aux:{k-1}": one}})
    positive("dag-256-rows", maximum)

    for parent in ("k23-null-dag", "k23-real-dag-sturm"):
        record = positives[parent]
        rows = record["cert"]["rows"]
        prefix = "null" if record["cert"]["type"] == "null-dag" else "real"
        # Adding even a zero cofactor must not legalize a bad source reference.
        for label, key, reason in [("forward", "aux:3", "dag_reference_order"),
                                   ("self", "aux:2", "dag_reference_order"),
                                   ("unknown-source", "e:99,100", "dag_source"),
                                   ("negative-index", "aux:-1", "dag_source"),
                                   ("leading-zero-index", "aux:00", "dag_source"),
                                   ("huge-index", "aux:" + "9" * 5000, "dag_reference_order")]:
            red(prefix + "-" + label, parent, ["cert", "rows", 2, "cofactors", key], [], reason)
        for missing in ("cofactors", "poly"):
            red(prefix + "-missing-" + missing, parent, ["cert", "rows", 0, missing])
        red(prefix + "-extra-row-field", parent, ["cert", "rows", 0, "extra"], 1)
        red(prefix + "-extra-cert-field", parent, ["cert", "system"], {})
        red(prefix + "-cofactors-list", parent, ["cert", "rows", 0, "cofactors"], [], "dag_source")
        red(prefix + "-rows-object", parent, ["cert", "rows"], {}, "dag_rows")
        red(prefix + "-empty-rows", parent, ["cert", "rows"], [], "dag_rows")
        red(prefix + "-noncanonical-poly", parent, ["cert", "rows", 0, "poly"],
            list(reversed(rows[0]["poly"])), "sparse_noncanonical", "increasing exponent order")
        key = next(k for k, p in rows[0]["cofactors"].items() if len(p) > 1)
        poly = rows[0]["cofactors"][key]
        red(prefix + "-noncanonical-cofactor", parent, ["cert", "rows", 0, "cofactors", key],
            list(reversed(poly)), "sparse_noncanonical", "increasing exponent order")
        red(prefix + "-zero-term", parent, ["cert", "rows", 2, "cofactors", "aux:0"],
            one + [["0", [99] * len(names)]], "sparse_noncanonical", "zero coefficient")
        red(prefix + "-duplicate-term", parent, ["cert", "rows", 0, "poly"],
            rows[0]["poly"] + rows[0]["poly"][:1], "sparse_duplicate_monomial")
        red(prefix + "-failed-identity", parent, ["cert", "rows", 0, "cofactors", key, 0, 0],
            str(Fraction(poly[0][0]) + 1), "dag_row_identity", "row 0")
        red(prefix + "-wrong-row-poly", parent, ["cert", "rows", 0, "poly", 0, 0],
            str(2 * Fraction(rows[0]["poly"][0][0])), "dag_row_identity", "row 0")
        graph = ck.decode(record["g6"])
        nonedge = next([u, v] for u, v in itertools.combinations(range(graph.n), 2) if (u, v) not in graph.edges)
        red(prefix + "-frame-nonedge", parent, ["cert", "frame"], nonedge, "frame_not_edge")
        for label, value, reason in [("float-coefficient", 1.0, "rational"),
                                     ("spaced-rational", " 1", "rational"),
                                     ("negative-denominator", "1/-1", "rational"),
                                     ("zero-denominator", "1/0", "rational")]:
            red(prefix + "-" + label, parent, ["cert", "rows", 2, "cofactors", "aux:0", 0, 0], value, reason)
        red(prefix + "-boolean-exponent", parent, ["cert", "rows", 2, "poly", 0, 1, 0], False, "sparse_exponents")

    red("null-last-not-one", "k23-null-dag", ["cert", "rows"], k23["cert"]["rows"][:2], "dag_last_null")
    red("real-last-not-f", "k23-real-dag-sturm", ["cert", "f", 0, 0], "2", "dag_last_real")
    red("dag-257-rows", "dag-256-rows", ["cert", "rows"],
        maximum["cert"]["rows"] + [{"poly": one, "cofactors": {"aux:255": one}}], "dag_row_limit")
    red("real-noncanonical-f", "k23-real-dag-sturm", ["cert", "f"], list(reversed(f)), "sparse_noncanonical")
    red("real-wrong-sturm-variable", "k23-real-dag-sturm", ["cert", "sturm"], names[1], "sturm_multivariate")
    red("real-missing-proof", "k23-real-dag-sturm", ["cert", "sturm"], reason="real_proof_choice")
    red("real-both-proofs", "k23-real-dag-sturm", ["cert", "sos"], {}, "real_proof_choice")
    red("real-missing-f", "k23-real-dag-sturm", ["cert", "f"])
    red("sos-zero-constant", "k4-real-dag-sos", ["cert", "sos", "c"], "0", "sos_constant_positive")
    red("sos-negative-weight", "k4-real-dag-sos", ["cert", "sos", "squares", 0, 0], "-1", "sos_weight_positive")
    red("sos-wrong-square", "k4-real-dag-sos", ["cert", "sos", "squares", 0, 1, 0, 0], "2", "sos_identity")
    red("sos-zero-term", "k4-real-dag-sos", ["cert", "sos", "squares", 0, 1, 0, 0], "0", "sparse_noncanonical")
    red("zero-row-nonzero-poly", "dag-zero-row", ["cert", "rows", 0, "poly"], one, "dag_row_identity")
    red("k4-frame-nonedge", "k4-isolate-null-dag", ["cert", "frame"],
        ck.read_json(FIX / "frame-nonedge.json")["cert"]["frame"], "frame_not_edge")
    red("constant-last-not-f", "real-dag-constant", ["cert", "f", 0, 0], "2", "dag_last_real")
    red("rational-spelling-invalid", "dag-rational-spelling", ["cert", "rows", 2, "cofactors", "aux:0", 0, 0],
        "2/0", "rational")
    ck.json_write(OUT / "cases.json", cases)
    print(f'DAG FIXTURES PASS positive={len(positives)} rejected_mutations={len(cases)-len(positives)} total={len(cases)}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
