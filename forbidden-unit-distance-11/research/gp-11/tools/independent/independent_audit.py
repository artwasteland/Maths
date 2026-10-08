#!/usr/bin/env python3
"""GP-11 checks 1: independent coverage, exact embeddings, pointers and L11.

Adapted in purpose and four stages from GP-10 independent_audit.py; no imports
from its checker or producers. Refutation verdicts are premises of this audit.
Their identities are independently examined by modp_identities.py (check 6).
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys
import time

from independent_core import (Failure, biconnected, blocks, bounded_map, check_exact,
    decode_g6, digest, encode_g6, iso_key, keys, lines, loads, maps_into,
    record, require, write_json, source_hashes, guard_outputs)

FROZEN_B11_SHA256 = "ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f"
REFUTATIONS = {"tree", "tu", "sub", "null", "real", "null-dag", "real-dag"}


def inspect_record(task):
    number, raw, check_embeddings = task
    g6 = f"line:{number}"
    try:
        r = record(raw)
        g6, verdict, cert = r["g6"], r["verdict"], r["cert"]
        t = cert.get("type")
        require(verdict == "unknown" or isinstance(t, str), "certificate_type", "certificate type must be a string")
        require((verdict == "embedded" and t in {"exact", "super"})
                or (verdict == "refuted" and t in REFUTATIONS)
                or verdict == "unknown", "certificate_verdict",
                f"certificate type {t!r} cannot support verdict {verdict!r}")
        meta = {"verdict": verdict, "type": t}
        if t in {"super", "sub"}:
            keys(cert, {"type", "g6", "map"}, {"index"} if t == "sub" else ())
            decode_g6(cert["g6"])
            meta.update({k: v for k, v in cert.items() if k != "type"})
        detail = check_exact(g6, cert) if check_embeddings and verdict == "embedded" and t == "exact" else None
        return number, g6, meta, detail, None
    except Failure as exc:
        # Keep the declared status for coverage/minimality diagnostics even when
        # its certificate fails. It can NEVER yield an overall PASS.
        if "r" in locals():
            typ = (r.get("cert") or {}).get("type")
            meta = {"verdict": r.get("verdict"), "type": typ if isinstance(typ, str) else None}
        else:
            meta = {}
        return number, g6, meta, None, {"code": exc.code, "reason": exc.reason, **exc.details}
    except (KeyError, TypeError, IndexError, ArithmeticError) as exc:
        return number, g6, {}, None, {"code": "schema", "reason": str(exc)}


def derive_minimal(population, metadata, canonical, alarm, evidence=None, catalogue=None):
    """L-min at order eleven, with no driver poset or checker lookup.

    F10-freeness is hereditary. Vertex deletions have order 10, so GP-10's
    theorem decides them. Edge deletions retain F10-freeness: a biconnected
    one is IN B11; every block of any other one has order <=10 and embeds by
    that same theorem. L-block glues the latter together without collisions.
    """
    result, tally = [], Counter()
    for g in population:
        if metadata.get(g, {}).get("verdict") != "refuted":
            continue
        n, edges = decode_g6(g)
        minimal, bad = True, []
        for vertex in range(n):
            remap = {u: k for k, u in enumerate(v for v in range(n) if v != vertex)}
            deletion = {(remap[u], remap[v]) for u, v in edges if vertex not in (u, v)}
            require(len(remap) == 10 and all(0 <= u < v < 10 for u, v in deletion),
                    "vertex_deletion", f"{g}: invalid reconstructed vertex deletion")
            tally["vertex_deletions_embedded_by_lower_order_theorem"] += 1
        for e in sorted(edges):
            deletion = edges - {e}
            detail = {"parent": g, "edge": list(e)}
            if biconnected(n, deletion):
                h = canonical.get(iso_key(n, deletion))
                status = metadata.get(h, {}).get("verdict") if h else None
                detail.update(kind="B11", target=h, verdict=status)
                tally["biconnected_deletions"] += 1
                if status is None:
                    minimal = False
                    alarm("missing_deletion", g, "biconnected edge deletion lacks a B11 record", edge=list(e), target=h)
                elif status != "embedded":
                    minimal = False
                    bad.append({"edge": list(e), "target": h, "verdict": status})
                    tally[f"deletions_{status}"] += 1
                    if status == "unknown":
                        alarm("unknown_deletion", g, "minimality cannot be unconditional", target=h)
            else:
                bs, isolated = blocks(n, deletion)
                union = set().union(*bs) if bs else set()
                sizes = [len({v for edge in b for v in edge}) for b in bs]
                require(union == deletion and sum(map(len, bs)) == len(deletion)
                        and all(size <= 10 for size in sizes), "block_partition",
                        f"{g}: invalid partition into proper smaller blocks")
                if catalogue is not None:
                    for block in bs:
                        vertices = sorted({v for e in block for v in e})
                        labels = {v: k for k, v in enumerate(vertices)}
                        relabelled = {(min(labels[u], labels[v]), max(labels[u], labels[v])) for u, v in block}
                        forbidden = catalogue.witness(len(vertices), relabelled)
                        if forbidden is not None:
                            minimal = False
                            alarm("block_contains_F10", g, "proper block contains an F10 member",
                                  edge=list(e), forbidden_index=forbidden, block_order=len(vertices))
                detail.update(kind="blocks", verdict="embedded", block_orders=sizes,
                              isolated_vertices=isolated, reason="F10-free; lower-order theorem and L-block")
                tally["non_biconnected_deletions_embedded_by_blocks"] += 1
                tally["blocks_of_order_10"] += sizes.count(10)
            if evidence is not None:
                evidence.write(__import__("json").dumps(detail, sort_keys=True) + "\n")
        if minimal:
            result.append(g)
        else:
            tally["refuted_not_minimal"] += 1
            if evidence is not None:
                evidence.write(__import__("json").dumps({"parent": g, "nonminimal_witnesses": bad}, sort_keys=True) + "\n")
    return sorted(result), dict(tally)


def check_pointers(metadata, alarm):
    states, bad = {}, 0
    for start, sm in metadata.items():
        if sm.get("type") not in {"super", "sub"} or start in states:
            continue
        chain, visiting, g, valid, reason = [], set(), start, True, ""
        while g not in states:
            if g in visiting:
                valid, reason = False, "cycle"
                break
            visiting.add(g)
            chain.append(g)
            m = metadata.get(g)
            if m is None:
                valid, reason = False, f"missing target {g}"
                break
            t, want = m.get("type"), sm["verdict"]
            if m.get("verdict") != want:
                valid, reason = False, f"wrong target verdict at {g}"
                break
            if t not in {"super", "sub"}:
                valid = (want == "embedded" and t == "exact") or (want == "refuted" and t in REFUTATIONS)
                reason = "invalid terminal type"
                break
            if "index" in m:
                valid, reason = False, "indexed F10 pointer inside an F10-free B11 graph"
                break
            target = m.get("g6")
            if target is None:
                valid, reason = False, "missing pointer target"
                break
            source_graph, target_graph = decode_g6(g), decode_g6(target)
            small, big = (source_graph, target_graph) if t == "super" else (target_graph, source_graph)
            if not maps_into(small, big, m.get("map")):
                valid, reason = False, f"noninjective or non-edge-preserving map at {g}"
                break
            g = target
        if g in states:
            valid, reason = states[g]
        for member in chain:
            states[member] = valid, reason
    for g, m in metadata.items():
        if m.get("type") in {"super", "sub"} and not states.get(g, (False, "unresolved"))[0]:
            bad += 1
            alarm("pointer", g, "pointer chain does not resolve: " + states.get(g, (False, "unresolved"))[1])
    return {"pointers": sum(m.get("type") in {"super", "sub"} for m in metadata.values()),
            "bad_pointer_chains": bad}


def grow_upset(minimal, population, metadata, canonical, alarm):
    up, frontier = set(minimal), list(minimal)
    while frontier:
        g = frontier.pop()
        n, edges = decode_g6(g)
        for u in range(n):
            for v in range(u + 1, n):
                if (u, v) not in edges:
                    h = canonical.get(iso_key(n, edges | {(u, v)}))
                    if h is not None and h not in up:
                        up.add(h)
                        frontier.append(h)
    refuted = {g for g in population if metadata.get(g, {}).get("verdict") == "refuted"}
    for g in sorted(up - refuted):
        alarm("upset_embedded", g, "embedded graph contains an independently derived L11 member")
    for g in sorted(refuted - up):
        alarm("upset_missing", g, "refuted graph is outside the independently derived minimal up-set")
    return {"upset": len(up), "refuted": len(refuted), "equal": up == refuted}


def audit(b11, records, outdir, *, jobs=1, stages="1234", sample=False,
          compare_l11=None, compare_report=None, predictions=None,
          sha256=FROZEN_B11_SHA256, quiet=False, forbidden_json=None):
    started = time.monotonic()
    out = Path(outdir)
    guard_outputs((b11, records, compare_l11, compare_report, predictions, forbidden_json),
                  [out / name for name in ("L11.g6", "report.json", "minimality.jsonl", "verdicts.tsv")])
    out.mkdir(parents=True, exist_ok=True)
    (out / "L11.g6").unlink(missing_ok=True)
    report = {"scope": "sample-only" if sample else "B11", "alarms": [], "stages": stages,
              "refutation_verdicts_are_premises": True,
              "lower_order_premise": "GP-10 theorem and B11 F10-freeness; not re-derived here"}
    own_sources = ["independent_core.py", "independent_audit.py", "forbidden_catalogue.py"]
    report["source_hashes"] = source_hashes(*own_sources)

    def alarm(code, g6, reason, **details):
        item = {"code": code, "g6": g6, "reason": reason, **details}
        report["alarms"].append(item)
        if not quiet:
            print("ALARM", __import__("json").dumps(item), flush=True)

    population, canonical = [], {}
    bh = hashlib.sha256()
    for number, raw in lines(b11):
        bh.update(raw)
        try:
            g = raw[:-1].decode("ascii")
            n, edges = decode_g6(g)
            require(n == 11 and biconnected(n, edges), "B11_structure", "expected a biconnected graph of order 11")
            key = iso_key(n, edges)
            if key in canonical:
                alarm("duplicate_isomorphism", g, "B11 duplicate isomorphism class", other=canonical[key])
            canonical[key] = g
            population.append(g)
        except (Failure, UnicodeError) as exc:
            alarm(getattr(exc, "code", "graph6"), f"B11-line:{number}", str(exc))
    if population != sorted(set(population)):
        alarm("B11_order", "B11", "graph list must be bytewise sorted and unique")
    if not sample and (bh.hexdigest() != sha256 or len(population) != 448708):
        alarm("B11_freeze", "B11", "input does not match frozen B11 count and hash",
              actual_sha256=bh.hexdigest(), count=len(population))
    metadata, exact_stats, types, rh = {}, Counter(), Counter(), hashlib.sha256()

    def tasks():
        for number, raw in lines(records):
            rh.update(raw)
            yield number, raw, "3" in stages

    for number, g, meta, detail, failure in bounded_map(inspect_record, tasks(), jobs):
        if g in metadata:
            alarm("duplicate_record", g, "duplicate record", line=number)
        metadata[g] = meta
        types[f"{meta.get('verdict')}/{meta.get('type')}"] += 1
        if failure:
            alarm(failure.pop("code"), g, failure.pop("reason"), line=number, **failure)
        if detail:
            exact_stats["verified"] += 1
            exact_stats[f"degree_{detail['degree']}"] += 1
            exact_stats["total_subdivisions"] += detail["subdivisions"]
            exact_stats["max_subdivisions"] = max(exact_stats["max_subdivisions"], detail["subdivisions"])
        if not quiet and (len(metadata) % 10000 == 0):
            print(f"records {len(metadata)}; exact embeddings {exact_stats['verified']}; {time.monotonic()-started:.1f}s", flush=True)
    pset, rset = set(population), set(metadata)
    for g in sorted(pset - rset):
        alarm("missing_record", g, "B11 graph has no record")
    for g in sorted(rset - pset):
        alarm("extra_record", g, "record is outside B11 input")
    counts = dict(Counter(m.get("verdict") if m.get("verdict") in ("embedded", "refuted", "unknown")
                          else "invalid" for m in metadata.values()))
    if counts.get("unknown", 0):
        alarm("unknown", "assembly", "this post-result audit requires zero unknowns", count=counts["unknown"])
    report["input"] = {"B11": len(population), "distinct_iso_classes": len(canonical),
                       "records": len(metadata), "counts": counts, "types": dict(types),
                       "B11_sha256": bh.hexdigest(), "records_sha256": rh.hexdigest()}
    with (out / "verdicts.tsv").open("w") as f:
        f.write("g6\tverdict\ttype\n")
        for g in sorted(metadata):
            f.write(f"{g}\t{metadata[g].get('verdict')}\t{metadata[g].get('type')}\n")
    if "3" in stages:
        report["embeddings"] = {"method": "exact fraction-free integer polynomial reduction and rational interval separation", **exact_stats}
        report["pointers"] = check_pointers(metadata, alarm)
    minimal = []
    if "2" in stages:
        catalogue = None
        if forbidden_json:
            from forbidden_catalogue import ForbiddenCatalogue
            catalogue = ForbiddenCatalogue(forbidden_json)
        with (out / "minimality.jsonl").open("w") as f:
            minimal, tally = derive_minimal(population, metadata, canonical, alarm, f, catalogue)
        (out / "L11.g6").write_text("".join(g + "\n" for g in minimal))
        report["minimality"] = {"L11": len(minimal), **tally}
        if catalogue is not None:
            report["minimality"]["explicit_F10_block_search"] = {"sha256": catalogue.sha256, **catalogue.stats}
        if compare_l11:
            claimed = [raw[:-1].decode("ascii") for _, raw in lines(compare_l11)]
            require(claimed == sorted(set(claimed)), "comparison_list", "claimed L11 must be sorted and unique")
            for g in sorted(set(minimal) ^ set(claimed)):
                alarm("minimality_mismatch", g, "independent L11 differs from comparison list",
                      independent=g in minimal, comparison=g in claimed)
            report["minimality"]["equals_comparison_L11"] = minimal == claimed
        if "4" in stages:
            report["cross_consistency"] = grow_upset(minimal, population, metadata, canonical, alarm)
    if compare_report:
        ref = loads(Path(compare_report).read_bytes())
        require(isinstance(ref.get("counts"), dict), "comparison_report", "comparison report has no counts")
        equal = all(ref["counts"].get(k, 0) == counts.get(k, 0) for k in ("embedded", "refuted", "unknown"))
        if not equal:
            alarm("count_mismatch", "assembly", "independent counts differ from checker report", comparison=ref["counts"])
        report["equals_comparison_counts"] = equal
    if predictions:
        text = Path(predictions).read_text()
        # Retain the forecast verbatim as input evidence, never rewrite it.
        forecast_lines = [line for line in text.splitlines() if line.startswith("| ")]
        report["predictions"] = {"sha256": digest(predictions), "forecast_rows": forecast_lines,
            "refuted_in_forecast_95pct_range": 3600 <= counts.get("refuted", -1) <= 7300,
            "L11_in_forecast_95pct_range": 1500 <= len(minimal) <= 6000 if "2" in stages else None,
            "automated_residue": "not reconstructible from final records; requires stage history"}
    if digest(b11) != bh.hexdigest():
        alarm("input_changed", "B11", "input changed during audit")
    if source_hashes(*own_sources) != report["source_hashes"]:
        alarm("source_changed", "tool", "tool source changed during audit")
    report["seconds"] = round(time.monotonic() - started, 3)
    report["status"] = "FAIL" if report["alarms"] else "PASS"
    report["classification_authorized"] = False
    report["derived_list_valid"] = "2" in stages and not report["alarms"]
    write_json(out / "report.json", report)
    if not quiet:
        print(__import__("json").dumps({"status": report["status"], "scope": report["scope"],
            "counts": counts, "L11": len(minimal) if "2" in stages else None, "seconds": report["seconds"]}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("b11")
    p.add_argument("records")
    p.add_argument("--outdir", required=True)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--stages", default="1234", help="1 coverage; 2 minimality; 3 embeddings/pointers; 4 up-set (requires 2)")
    p.add_argument("--sample", action="store_true", help="explicitly waive population hash/count; report is sample-only")
    p.add_argument("--sha256", default=FROZEN_B11_SHA256)
    p.add_argument("--compare-l11")
    p.add_argument("--compare-report")
    p.add_argument("--predictions")
    p.add_argument("--forbidden-json", help="redundant explicit non-induced F10 search of every proper block, through order 10")
    a = p.parse_args()
    require(a.jobs >= 1 and all(x in "1234" for x in a.stages) and ("4" not in a.stages or "2" in a.stages),
            "arguments", "invalid jobs or stages")
    try:
        rep = audit(a.b11, a.records, a.outdir, jobs=a.jobs, stages=a.stages, sample=a.sample,
                    sha256=a.sha256, compare_l11=a.compare_l11, compare_report=a.compare_report, predictions=a.predictions,
                    forbidden_json=a.forbidden_json)
        return 0 if rep["status"] == "PASS" else 1
    except (Failure, OSError) as exc:
        if getattr(exc, "code", None) != "output_collision":
            write_json(Path(a.outdir) / "report.json", {"status": "FAIL", "alarms": [{"code": getattr(exc, "code", "io"),
                "g6": "input", "reason": str(exc)}], "scope": "sample-only" if a.sample else "B11"})
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
