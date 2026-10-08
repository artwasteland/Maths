#!/usr/bin/env python3
"""GP-11 check 2: paired green originals and named failures on mutated copies.

Adapted from GP-10 independent_audit_redteam.py. Uses a small deletion/pointer
closure, rather than copying 3.39 GB for each control. No frozen checker runs.
"""
import argparse
from collections import Counter
import copy
from fractions import Fraction
import json
from pathlib import Path
import random
import sys
import time

from independent_core import (biconnected, decode_g6, encode_g6, iso_key,
    lines, record, require, write_json, guard_outputs)
from independent_audit import audit


def control_sample(b11, records, outdir):
    out = Path(outdir)
    guard_outputs([b11, records], [out / name for name in ("baseline.g6", "baseline.jsonl", "selection.json")])
    out.mkdir(parents=True, exist_ok=True)
    population = [raw[:-1].decode("ascii") for _, raw in lines(b11)]
    canonical = {iso_key(*decode_g6(g)): g for g in population}
    metadata, offset, exact, supers, refs = {}, 0, [], [], []
    for _, raw in lines(records):
        rec = record(raw)
        c, g = rec["cert"], rec["g6"]
        t = c.get("type")
        deps = [c["g6"]] if t in {"sub", "super"} and "index" not in c else []
        if t == "tu" and "refuted" in c.get("end", {}):
            deps.append(c["end"]["refuted"])
        metadata[g] = (offset, len(raw), rec["verdict"], t, deps)
        offset += len(raw)
        if t == "exact":
            exact.append((len(c["field"]["minpoly"]), len(raw), g))
        elif t == "super":
            supers.append(g)
        if rec["verdict"] == "refuted":
            refs.append((len(raw), g))
    require(exact and supers and refs, "control_sample", "need an embedding, pointer and refutation")
    seeds = [min(exact)[2], supers[0]] + [g for _, g in sorted(refs)[:3]]
    selected, todo = set(), seeds[:]
    while todo:
        g = todo.pop()
        if g in selected:
            continue
        require(g in metadata, "control_sample", f"missing dependency {g}")
        selected.add(g)
        todo.extend(metadata[g][4])
        if metadata[g][2] == "refuted":
            n, edges = decode_g6(g)
            for e in edges:
                deletion = edges - {e}
                if biconnected(n, deletion):
                    h = canonical.get(iso_key(n, deletion))
                    require(h is not None, "control_sample", f"missing edge deletion for {g}")
                    todo.append(h)
    selected = sorted(selected)
    bp, rp = out / "baseline.g6", out / "baseline.jsonl"
    bp.write_text("".join(g + "\n" for g in selected))
    with open(records, "rb") as f, rp.open("wb") as o:
        for g in selected:
            pos, size, _, _, _ = metadata[g]
            f.seek(pos)
            o.write(f.read(size))
    write_json(out / "selection.json", {"seeds": seeds, "records": len(selected),
        "bytes": sum(metadata[g][1] for g in selected), "sources": [str(b11), str(records)],
        "types": dict(Counter(metadata[g][3] for g in selected))})
    return bp, rp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("b11", help="a deletion-closed sample or B11")
    p.add_argument("records")
    p.add_argument("outdir")
    p.add_argument("--keep-copies", action="store_true")
    a = p.parse_args()
    started = time.monotonic()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    bp, rp = control_sample(a.b11, a.records, out)
    positive = audit(bp, rp, out / "green-before", sample=True, quiet=True)
    require(positive["status"] == "PASS", "positive_control", "untouched sampled closure must pass first")
    original = [record(raw) for _, raw in lines(rp)]
    by_g = {r["g6"]: r for r in original}
    population = sorted(by_g)
    canonical = {iso_key(*decode_g6(g)): g for g in population}
    minimal = (out / "green-before" / "L11.g6").read_text().splitlines()
    require(minimal, "positive_control", "sample must include an independently minimal refutation")
    refuted = minimal[0]
    exact = next(r["g6"] for r in original if r["cert"].get("type") == "exact")
    pointer = next(r["g6"] for r in original if r["cert"].get("type") == "super")
    results = []

    def run(name, expected, named, mutate=None, pop=None, claim=None, stages="1234"):
        changed = copy.deepcopy(original)
        if mutate:
            mutate(changed)
        require(changed != original or pop is not None or claim is not None,
                "control", "control must alter the input")
        cp = out / (name + ".records.jsonl")
        with cp.open("w") as f:
            for r in changed:
                f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
        bpath = bp
        if pop is not None:
            bpath = out / (name + ".g6")
            bpath.write_text("".join(g + "\n" for g in sorted(pop)))
        lpath = out / "green-before" / "L11.g6"
        if claim is not None:
            lpath = out / (name + ".L11.g6")
            lpath.write_text("".join(g + "\n" for g in claim))
        report = audit(bpath, cp, out / name, sample=True, compare_l11=lpath if "2" in stages else None,
                       stages=stages, quiet=True)
        alarms = [x for x in report["alarms"] if x["code"] == expected
                  and (x["g6"] == named or x.get("other") == named)]
        ok = report["status"] == "FAIL" and bool(alarms)
        results.append({"control": name, "g6": named, "red": ok, "expected_code": expected,
                        "named_alarms": alarms, "seconds": report["seconds"]})
        print(("RED " if ok else "FAILED CONTROL ") + name + " " + named, flush=True)
        if not a.keep_copies:
            cp.unlink()

    def update(rows, g, fn):
        fn(next(r for r in rows if r["g6"] == g))

    def coordinate(r):
        arr = r["cert"]["coords"][0][0]
        arr[0] = str(Fraction(arr[0]) + Fraction(1, 10 ** 40))
    run("coordinate-plus-1e-40", "edge_not_unit", exact, lambda rs: update(rs, exact, coordinate), stages="13")

    def fake_embedding(r):
        n, _ = decode_g6(r["g6"])
        r["verdict"] = "embedded"
        r["cert"] = {"type": "exact", "field": {"minpoly": [-2, 0, 1], "interval": ["1", "2"]},
                     "coords": [[["0", "0"], ["0", "0"]] for _ in range(n)]}
    run("refuted-flipped-to-fake-embedding", "edge_not_unit", refuted,
        lambda rs: update(rs, refuted, fake_embedding))
    run("record-dropped", "missing_record", refuted,
        lambda rs: rs.__setitem__(slice(None), [r for r in rs if r["g6"] != refuted]), stages="13")
    run("record-duplicated", "duplicate_record", exact,
        lambda rs: rs.append(copy.deepcopy(next(r for r in rs if r["g6"] == exact))), stages="13")

    def corrupt_map(r):
        r["cert"]["map"][0] = r["cert"]["map"][1]
    run("pointer-noninjective", "pointer", pointer, lambda rs: update(rs, pointer, corrupt_map), stages="13")

    subgraph = None
    for parent in minimal:
        n, edges = decode_g6(parent)
        for e in sorted(edges):
            deletion = edges - {e}
            if biconnected(n, deletion):
                h = canonical.get(iso_key(n, deletion))
                if h and by_g[h]["verdict"] == "embedded":
                    subgraph = parent, h, e
                    break
        if subgraph:
            break
    require(subgraph is not None, "control", "need a biconnected deletion of a minimal graph")
    parent, child, edge = subgraph
    run("minimal-subgraph-status-changed", "minimality_mismatch", parent,
        lambda rs: update(rs, child, lambda r: r.__setitem__("verdict", "refuted")), stages="12")
    results[-1].update(changed_record=child, deleted_edge=list(edge))
    run("minimal-member-dropped-from-claim", "minimality_mismatch", refuted,
        claim=[g for g in minimal if g != refuted], stages="12")

    rng = random.Random(20261007)
    base = population[1]
    n, edges = decode_g6(base)
    perm = list(range(n))
    for _ in range(100):
        rng.shuffle(perm)
        relabelled = encode_g6(n, {(min(perm[u], perm[v]), max(perm[u], perm[v])) for u, v in edges})
        if relabelled != base and relabelled not in by_g:
            break
    else:
        raise ValueError("could not construct a distinct labelled copy")
    run("population-duplicate-isomorphism", "duplicate_isomorphism", relabelled,
        pop=[relabelled] + population[1:], stages="1")

    # Separate after-run green guards against accidentally mutating shared state.
    after = audit(bp, rp, out / "green-after", sample=True, compare_l11=out / "green-before" / "L11.g6", quiet=True)
    behaved = all(r["red"] for r in results) and after["status"] == "PASS"
    rep = {"status": "PASS" if behaved else "FAIL", "scope": "paired controls on a deletion/pointer-closed sample",
           "green_before": positive["status"], "green_after": after["status"], "controls": results,
           "all_controls_behaved": behaved, "seconds": round(time.monotonic() - started, 3)}
    write_json(out / "redteam.json", rep)
    print(json.dumps({"status": rep["status"], "controls": len(results), "seconds": rep["seconds"]}), flush=True)
    return 0 if behaved else 1


if __name__ == "__main__":
    sys.exit(main())
