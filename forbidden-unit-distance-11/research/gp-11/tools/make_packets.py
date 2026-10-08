#!/usr/bin/env python3
"""Build auditable analyst packets from completed bundle UNKNOWN records.

Usage: make_packets.py BUNDLE_OR_PARENT [...] --out NEW_DIRECTORY
       [--select FINAL_UNKNOWN.g6] [--python FROZEN_PYTHON]

--round-input F3_INPUT --assembly ASSEMBLY adds the disjoint NOT RUN graphs
from an audited stopped-f3 assembly; these are explicitly not checked bundles.

Standard library plus nauty-labelg; imports no producer or checker and reads no
answer library. Hashes, canonical labels and TU relabellings are checked, but
packets and geometric hints are NOT certificates. Missing worker scratch is
reported explicitly, never reconstructed from an answer corpus. Output is
staged below its parent and published only after all checks succeed.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import gzip
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE_PIN = "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04"
KERNEL_PIN = "63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de"
F9_PIN = "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a"
GADGET_PIN = "a904487c6c327be215825bb129144445c16511495984cd5a3897012e906de629"
RECORD_LIMIT = 8 * 1024 * 1024
JSONL_LIMIT = 32 * 1024 * 1024  # Attempt wrapper/history can exceed record size.


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key:" + key)
        result[key] = value
    return result


def loads(raw):
    def constant(value):
        raise ValueError("nonfinite_json:" + value)

    def floating(value):
        answer = float(value)
        require(math.isfinite(answer), "nonfinite_json:" + value)
        return answer

    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant, parse_float=floating)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rows(path, limit=JSONL_LIMIT):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        number = 0
        while True:
            raw = stream.readline(limit + 1)
            if not raw:
                break
            number += 1
            require(len(raw) <= limit and raw.endswith(b"\n") and raw != b"\n", f"jsonl_framing:{path}:{number}")
            yield number, raw, loads(raw)


def decode(code):
    require(isinstance(code, str) and code and all(63 <= ord(c) <= 126 for c in code), "graph6_alphabet")
    n = ord(code[0]) - 63
    require(1 <= n <= 11, "packet_order_1_to_11_required")
    bits = n * (n - 1) // 2
    require(len(code) == 1 + (bits + 5) // 6, "graph6_length")
    if bits % 6:
        require((ord(code[-1]) - 63) & ((1 << (6 - bits % 6)) - 1) == 0, "graph6_padding")
    edges, bit = [], 0
    for b in range(1, n):
        for a in range(b):
            if (ord(code[1 + bit // 6]) - 63) & (1 << (5 - bit % 6)):
                edges.append((a, b))
            bit += 1
    return n, edges


def graph_list(path):
    raw = path.read_bytes()
    require(not raw or raw.endswith(b"\n"), "graph_list_newline:" + str(path))
    result = raw.decode("ascii").splitlines()
    require(result == sorted(set(result)), "graph_list_sorted_unique:" + str(path))
    for code in result:
        decode(code)
    return result


def canonical(codes, labelg):
    if not codes:
        return
    result = subprocess.run([str(labelg), "-q"], input="\n".join(codes) + "\n", text=True,
                            capture_output=True, timeout=60, check=True)
    require(result.stdout.splitlines() == codes, "noncanonical_graph6")


def safe_file(bundle, name):
    require(Path(name).name == name and name not in (".", ".."), "unsafe_artifact_name")
    path = bundle / name
    require(path.resolve().is_relative_to(bundle) and path.is_file(), "artifact_outside_or_missing:" + name)
    return path


def validate_bundle(bundle):
    summary = loads(safe_file(bundle, "summary.json").read_bytes())
    require(summary.get("completed") is True and summary.get("checker_status") == "ACCEPT", "incomplete_bundle")
    artifacts = summary["artifacts"]
    required = {"job.json", "run.json", "records.jsonl.gz", "UNKNOWN.g6", "input.g6", "assigned.g6",
                "frontier.jsonl.gz", "attempts.jsonl.gz", "packets.jsonl.gz", "checker-report.json"}
    require(required <= artifacts.keys(), "bundle_artifact_set")
    for name, expected in artifacts.items():
        require(sha(safe_file(bundle, name)) == expected, "bundle_hash:" + name)
    job = loads((bundle / "job.json").read_bytes())
    report = loads((bundle / "checker-report.json").read_bytes())
    require(report.get("status") == "ACCEPT", "bundle_report_not_accepted")
    mode = "control51" if job.get("schema") == "control51-v1" else "b11"
    if mode == "control51":
        require(job.get("forbidden_limit") == 9, "control51_F9_required")
    receipt = {"bundle": str(bundle), "summary_sha256": sha(bundle / "summary.json"),
               "artifact_hashes": artifacts, "mode": mode,
               "counts": summary["counts"], "job_sha256": sha(bundle / "job.json")}
    return summary, job, receipt


def classify(history):
    reasons = [a.get("reason", "") for a in history]
    no_seed = "no_separated_seed" in reasons or "no_separated_numerical_seed" in reasons
    seed = any(a.get("stage", "").endswith("branch") and a.get("reason") in
               ("no_exact_certificate", "no_separated_branch") for a in history)
    flags = []
    for name, present in (
        ("checker_deadline", any(r == "checker:Deadline" for r in reasons)),
        ("attempt_deadline_unspecified", any(r == "attempt_error:Deadline" for r in reasons)),
        ("producer_timeout", any(r == "producer_error:TimeoutExpired" for r in reasons)),
        ("checker_rejection_or_error", any(r.startswith("checker:") and r != "checker:Deadline" for r in reasons)),
        ("producer_algebra_error", "producer_error:AlgebraError" in reasons),
    ):
        if present:
            flags.append(name)
    primary = "no_separated_seed" if no_seed else ("seed_without_exact" if seed else "unclassified")
    # Historical attempts can conflict after a later stronger search; retain
    # both the raw reasons and flags instead of silently turning this into proof.
    return {"primary": primary, "flags": flags, "seed_evidence_mixed": no_seed and seed,
            "routing_only": True, "reason_counts": dict(sorted(Counter(reasons).items()))}


def closure_info(code, closure):
    if not closure:
        return {"available": False, "reason": "TU closure absent from bundle"}
    n, edges = decode(code)
    target_n, target_edges = decode(closure["g6"])
    mapping = closure["old_to_new"]
    require(target_n == n and all(type(v) is int for v in mapping) and sorted(mapping) == list(range(n)), "tu_permutation")
    augmented = set(edges)
    for step in closure["steps"]:
        pair = step["pair"]
        require(len(pair) == 2 and all(type(v) is int and 0 <= v < n for v in pair) and pair[0] != pair[1], "tu_pair")
        pair = tuple(sorted(pair))
        require(pair not in augmented, "tu_pair_already_edge")
        step_map = step["map"]
        require(all(type(v) is int and 0 <= v < n for v in step_map) and len(set(step_map)) == len(step_map), "tu_gadget_map")
        augmented.add(pair)
    transported = {tuple(sorted((mapping[a], mapping[b]))) for a, b in augmented}
    require(transported == set(target_edges), "tu_closure_label_mismatch")
    return {**closure, "available": True, "new_to_old": [mapping.index(i) for i in range(n)],
            "map_direction": "original canonical vertex -> canonical TU closure vertex",
            "steps_labels": "original canonical graph; gadget maps use stored gadget labels",
            "validation": "edge additions and permutation only; gadget implications require frozen replay"}


def geometry(n, edges):
    edge_set = set(edges)
    adjacent = [set() for _ in range(n)]
    for a, b in edges:
        adjacent[a].add(b)
        adjacent[b].add(a)
    triangles = [list(t) for t in combinations(range(n), 3) if all(e in edge_set for e in combinations(t, 2))]
    rhombi = set()
    for a, b in combinations(range(n), 2):
        for c, d in combinations(sorted(adjacent[a] & adjacent[b]), 2):
            rhombi.add(tuple(sorted(((a, b), (c, d)))))
    return {"triangles": triangles,
            "triangle_identity": "p_c=(p_a+p_b)/2 +/- sqrt(3)/2 * R90(p_b-p_a); retain both orientations",
            "rhombi": [{"opposite_pairs": [list(a), list(b)],
                        "identity": f"p{a[0]}+p{a[1]}=p{b[0]}+p{b[1]}"} for a, b in sorted(rhombi)],
            "status": "graph-derived necessary identities for injective unit-distance embeddings; not certificates"}


def numeric_info(n, edges, evidence):
    if not evidence or evidence.get("coords") is None:
        return {"available": False, "reason": "numerical coordinates absent from bundle"}, []
    coords = evidence["coords"]
    require(len(coords) == n and all(isinstance(xy, list) and len(xy) == 2 for xy in coords), "numeric_coordinate_shape")
    values = [[float(x), float(y)] for x, y in coords]
    require(all(math.isfinite(v) for xy in values for v in xy), "numeric_coordinate_nonfinite")
    frames = [[a, b] for a in range(n) for b in range(n) if a != b and tuple(sorted((a, b))) in set(edges)
              and math.hypot(*values[a]) < 1e-9 and math.hypot(values[b][0] - 1, values[b][1]) < 1e-9]
    collisions = []
    for pair, count in evidence.get("collision_pairs", {}).items():
        parsed = ast.literal_eval(pair)
        require(isinstance(parsed, (tuple, list)) and len(parsed) == 2 and
                all(type(v) is int and 0 <= v < n for v in parsed) and parsed[0] != parsed[1], "collision_pair")
        collisions.append({"pair": sorted(parsed), "occurrences": count})
    return {"available": True, "evidence_only": True, "labels": "original canonical graph vertex order",
            "raw": evidence, "collision_pairs": sorted(collisions, key=lambda x: x["pair"]),
            "precision": "as exported; do not infer high precision from float residual 0"}, frames


def make_packet(directory, code, frontier, unknown, attempts, groups, receipt, python, original_raw=None):
    n, edges = decode(code)
    mode = receipt["mode"]
    require(n == (10 if mode == "control51" else 11), "bundle_graph_order")
    if "edges" in frontier:
        require({tuple(sorted(e)) for e in frontier["edges"]} == set(edges), "frontier_edges_mismatch")
    prior = unknown["cert"].get("budget", {}).get("stages", [])
    history = [{k: v for k, v in a.items() if k != "record"} for a in attempts]
    # The complete original budget remains separately available, including prior
    # rounds. Classification combines reasons without fabricating lost timings.
    def history_key(attempt):
        return compact({k: attempt[k] for k in ("stage", "outcome", "reason", "budget", "prior_run") if k in attempt})
    known_history = {history_key(a) for a in history}
    classification = classify(history + [a for a in prior if history_key(a) not in known_history])
    directory.mkdir()
    (directory / "attempts.jsonl").write_text("".join(compact(a) + "\n" for a in attempts))
    (directory / "original-unknown.jsonl").write_bytes(original_raw if original_raw is not None else (compact(unknown) + "\n").encode())
    proposals = []
    for i, attempt in enumerate(attempts):
        record = attempt.get("record")
        if not record or record.get("verdict") == "unknown":
            continue
        raw = (compact(record) + "\n").encode()
        name = f"proposal-{i:03d}.jsonl"
        (directory / name).write_bytes(raw)
        cert = record.get("cert", {})
        proposals.append({"path": name, "sha256": sha(directory / name), "bytes": len(raw),
                          "within_record_limit": len(raw) <= RECORD_LIMIT, "g6": record["g6"],
                          "stage": attempt.get("stage"), "outcome": attempt.get("outcome"),
                          "reason": attempt.get("reason"), "status": "unverified proposal",
                          "field_degree": len(cert.get("field", {}).get("minpoly", [])) - 1})
    hints = list(frontier.get("analyst_hints", []))
    for attempt in prior:
        if attempt.get("analyst_hints"):
            hints.append({"stage": attempt.get("stage"), **attempt["analyst_hints"]})
    numeric, inferred_frames = numeric_info(n, edges, frontier.get("numeric_evidence_only"))
    geom = geometry(n, edges)
    closure = closure_info(code, frontier.get("tu_closure"))
    checker_path = "research/gp-10/check/gp10check.py" if mode == "control51" else "research/gp-11/check/gp11check.py"
    check = directory / "check"
    check.mkdir()
    (check / "input.g6").write_text(code + "\n")
    (check / "UNKNOWN.g6").write_text("")
    write(check / "run.json", {"profile": "sample" if mode == "control51" else "fixture11", "input": "input.g6",
                              "input_sha256": sha(check / "input.g6"), "records": ["records.jsonl"],
                              "unknown": "UNKNOWN.g6", "derive": False, "forbidden_limit": 9 if mode == "control51" else 10})
    pins = {"gp10check.py": BASE_PIN, "udcheck.py": KERNEL_PIN,
            "forbidden-74.json": F9_PIN, "tu-gadgets.json": GADGET_PIN,
            "gp11check.py": sha(ROOT / "research/gp-11/check/gp11check.py")}
    source_pins = {
        ROOT / "research/gp-10/check/gp10check.py": BASE_PIN,
        ROOT / "research/unit-distance-22/check/udcheck.py": KERNEL_PIN,
        ROOT / "research/unit-distance-22/data/forbidden-74.json": F9_PIN,
        ROOT / "research/unit-distance-22/data/tu-gadgets.json": GADGET_PIN,
        ROOT / "research/gp-11/tools/guard.py": sha(ROOT / "research/gp-11/tools/guard.py"),
    }
    if mode != "control51":
        source_pins[ROOT / checker_path] = pins["gp11check.py"]
    (directory / "CHECKER_SHA256SUMS").write_text("".join(f"{digest}  {path}\n" for path, digest in source_pins.items()))
    command = [python, "-B", str(ROOT / "research/gp-11/tools/guard.py"), "--", python, "-B", str(ROOT / checker_path), "check"]
    (directory / "check.sh").write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                                        'sha256sum --check --strict CHECKER_SHA256SUMS\nexec ' + shlex.join(command) + '\n')
    packet = {"schema": "gp11-analyst-packet-v1", "id": directory.name, "mode": mode,
              "graph": {"g6": code, "n": n, "labels": list(range(n)), "edges": [list(e) for e in edges],
                        "degrees": [sum(v in e for e in edges) for v in range(n)], "canonicalizer": "nauty-labelg -q",
                        "label_convention": "zero-based labels of this canonical graph6; never silently relabel coordinates"},
              "source": {"bundle": receipt["bundle"], "summary_sha256": receipt["summary_sha256"],
                         "graph_id_in_bundle": frontier["id"], "receipt": "../../sources/" + receipt["id"] + "/receipt.json"},
              "tu_closure": closure, "failure_class": classification,
              "attempt_history": {"path": "attempts.jsonl", "sha256": sha(directory / "attempts.jsonl"),
                                  "count": len(attempts), "prior_and_current_budget": unknown["cert"]["budget"],
                                  "timing_status": "per-stage caps retained; actual per-graph seconds not exported by these bundles"},
              "original_unknown": {"path": "original-unknown.jsonl", "sha256": sha(directory / "original-unknown.jsonl")},
              "saved_proposals": {"records": proposals, "availability": "retained in attempts" if proposals else
                                  "absent from exported attempts; recover explicitly from worker scratch before retrying saved-candidate checks"},
              "numerical": numeric, "frames": {"candidate_edges": [list(e) for e in edges],
                                                "inferred_from_numeric_only": inferred_frames,
                                                "recorded": [h for h in hints if "frame" in h or "candidate_frames" in h]},
              "rational_pins": {"recorded": [h for h in hints if "pins" in h or "rational_pins" in h],
                                "status": "only explicit hints retained; numerical near-rationals are not exact pins",
                                "restriction": "extra pins may select embedding candidates; no added pin is an axiom in a refutation"},
              "geometric_identities": geom,
              "field_candidates": {"recorded": [h for h in hints if any(k in h for k in ("primitive_candidates", "field", "field_candidates"))],
                                   "proposal_metadata": proposals,
                                   "suggestions": ["Try rational functions over Q(sqrt(3)); triangles justify considering this subfield, not a field degree"] if geom["triangles"] else [],
                                   "status": "candidate hints only; no minimal polynomial or degree invented"},
              "analyst_hints": hints, "related_graph_groups": groups,
              "independent_certificate_obligations": 1,
              "checker": {"cwd": "this packet directory", "pinned_command": ["bash", "check.sh"], "argv": command,
                          "pins": pins, "scratch": "/tmp/gp10-check (hard-coded; TMPDIR alone does not relocate it)",
                          "acceptance": "exit 0, literal ACCEPT run verified, status ACCEPT, zero unknown and direct_rejections, one decided graph",
                          "result_required": "write one self-contained frozen-format record to check/records.jsonl; return checker log/report, record hash and measured wall/RSS cost",
                          "control_policy": "F9 only, fresh evidence, no GP-10 answer records, no F10 rewrite, bases at most nine" if mode == "control51" else "F10 premise allowed; fixture11 is not a final B11 result"},
              "missing_evidence": [name for name, present in (("saved_proposals", proposals), ("numerical_coordinates", numeric["available"]),
                                                            ("explicit_rational_pins", any("pins" in h or "rational_pins" in h for h in hints)),
                                                            ("recorded_field_candidates", any("primitive_candidates" in h or "field" in h for h in hints))) if not present]}
    if receipt.get('kind') == 'round-input':
        packet['source'].update(kind='round-input', f3_status='NOT RUN', round_sha256=receipt['round_sha256'])
        packet['attempt_history']['timing_status'] = 'Prior round-input budgets only; no f3 attempt claimed.'
    write(directory / "packet.json", packet)
    return {"id": directory.name, "g6": code, "mode": mode, "path": "packets/" + directory.name + "/packet.json",
            "sha256": sha(directory / "packet.json"), "failure_class": classification,
            "attempts": len(attempts), "proposals": len(proposals), "missing_evidence": packet["missing_evidence"]}


def discover(paths):
    result = []
    for path in paths:
        path = path.resolve()
        found = [path] if (path / "summary.json").is_file() else sorted(p for p in path.iterdir() if p.is_dir() and (p / "summary.json").is_file())
        require(found, "no_bundles:" + str(path))
        result.extend(found)
    require(len(set(result)) == len(result), "duplicate_bundle")
    return sorted(result)


def build(paths, out, select=None, python=sys.executable, labelg=Path("/usr/bin/nauty-labelg"), round_input=None, assembly=None):
    out = out.resolve()
    bundles = discover(paths)
    carry = None
    if round_input is not None:
        import b11_stopped as stopped
        round_input = round_input.resolve()
        carry = stopped.packet_source(round_input, assembly, bundles, select)
        require(not out.is_relative_to(round_input) and not round_input.is_relative_to(out), "output_input_collision")
    require(not out.exists(), "output_exists")
    require(all(not out.is_relative_to(b) and not b.is_relative_to(out) for b in bundles), "output_input_collision")
    require(sha(ROOT / "research/gp-10/check/gp10check.py") == BASE_PIN, "frozen_checker_hash")
    chosen = set(graph_list(select)) if select else None
    all_unknown, published, assignments, receipts, modes = set(), [], set(), [], set()
    totals, stage_reasons = Counter(), Counter()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".packet-stage-", dir=out.parent) as temporary:
        stage = Path(temporary)
        (stage / "packets").mkdir()
        (stage / "sources").mkdir()
        for index, bundle in enumerate(bundles):
            summary, job, receipt = validate_bundle(bundle)
            if carry is not None:
                stopped.require(receipt['summary_sha256'] == carry[1]['returned_summaries'][str(bundle)],
                                'round_packets_returned_sources')
            modes.add(receipt["mode"])
            require(len(modes) == 1, "do_not_mix_control51_and_B11_packets")
            assigned = set(graph_list(bundle / "assigned.g6"))
            require(not assignments & assigned, "overlapping_bundle_assignments")
            assignments.update(assigned)
            codes = graph_list(bundle / "UNKNOWN.g6")
            require(not all_unknown & set(codes) and set(codes) <= assigned, "unknown_assignment")
            all_unknown.update(codes)
            want = set(codes) if chosen is None else set(codes) & chosen
            receipt["id"] = f"bundle-{index:04d}"
            receipts.append(receipt)
            totals.update(summary["counts"])
            source_dir = stage / "sources" / receipt["id"]
            source_dir.mkdir()
            for name in ("summary.json", "job.json", "run.json", "checker-report.json"):
                shutil.copyfile(bundle / name, source_dir / name)
            write(source_dir / "receipt.json", receipt)
            unknowns, seen, counts, digest = {}, set(), Counter(), hashlib.sha256()
            for _, raw, row in rows(bundle / "records.jsonl.gz", RECORD_LIMIT):
                digest.update(raw)
                code = row["g6"]
                require(code not in seen, "duplicate_record")
                seen.add(code)
                if code in assigned:
                    counts[row["verdict"]] += 1
                if row["verdict"] == "unknown":
                    unknowns[code] = row
            require(digest.hexdigest() == summary["records_sha256"], "records_uncompressed_hash")
            require(seen == set(graph_list(bundle / "input.g6")), "bundle_record_coverage")
            require(set(unknowns) == set(codes) and all(counts[k] == summary["counts"][k] for k in ("embedded", "refuted", "unknown")), "unknown_or_counts_mismatch")
            frontier, ids = {}, {}
            for _, _, row in rows(bundle / "frontier.jsonl.gz"):
                code = row["g6"]
                require(code in unknowns and code not in frontier and row["id"] not in ids, "frontier_coverage_or_id")
                frontier[code] = row
                ids[row["id"]] = code
            require(set(frontier) == set(codes), "frontier_unknown_coverage")
            canonical(sorted(set(codes) | {r["tu_closure"]["g6"] for r in frontier.values() if r.get("tu_closure")}), labelg)
            attempts, groups = defaultdict(list), defaultdict(list)
            for _, _, row in rows(bundle / "attempts.jsonl.gz"):
                code = ids.get(row["id"])
                if code is None:
                    continue
                require(row.get("record", {}).get("g6") == code, "attempt_graph_id_mismatch")
                stage_reasons[(row.get("stage", ""), row.get("reason", ""))] += 1
                if code in want:
                    attempts[code].append(row)
            for _, _, row in rows(bundle / "packets.jsonl.gz"):
                for code in set(row["graphs"]) & want:
                    groups[code].append(row)
            for code in sorted(want):
                name = "packet-" + hashlib.sha256(code.encode()).hexdigest()[:16]
                published.append(make_packet(stage / "packets" / name, code, frontier[code], unknowns[code],
                                             attempts[code], groups[code], receipt, python))
            # Refuse changed inputs, including a concurrently re-exported summary.
            require(sha(bundle / "summary.json") == receipt["summary_sha256"], "source_changed:summary")
            for name, expected in receipt["artifact_hashes"].items():
                require(sha(safe_file(bundle, name)) == expected, "source_changed:" + name)
        if carry is not None:
            records, info = carry
            extra, receipt = stopped.append_packets(stage, records, info, chosen, assignments, python, labelg)
            published.extend(extra)
            receipts.append(receipt)
            assignments.update(records)
            all_unknown.update(records)
            totals.update(unknown=len(records))
        if chosen is not None:
            require(chosen <= all_unknown, "selected_graph_not_unknown_in_sources")
        published.sort(key=lambda r: r["g6"])
        histogram = Counter(r["failure_class"]["primary"] for r in published)
        flags = Counter(flag for r in published for flag in r["failure_class"]["flags"])
        manifest = {"schema": "gp11-analyst-packets-v1", "scope": "routing and evidence preservation; no proof verdict",
                    "bundles": len(bundles), "assigned_graphs": len(assignments), "source_counts": dict(totals),
                    "source_unknowns": len(all_unknown), "packets": len(published), "selection": sorted(chosen) if chosen is not None else None,
                    "failure_classes": dict(histogram), "failure_flags": dict(flags),
                    "source_unknown_stage_reasons": [{"stage": s, "reason": r, "count": n} for (s, r), n in sorted(stage_reasons.items())],
                    "saved_proposals": sum(p["proposals"] for p in published), "packet_index": published,
                    "sources": receipts, "generator_sha256": sha(Path(__file__)), "labelg_sha256": sha(labelg)}
        write(stage / "manifest.json", manifest)
        (stage / "UNKNOWN.g6").write_text("".join(p["g6"] + "\n" for p in published))
        # Every generated file, not only packet.json, is covered by this receipt.
        hashes = {str(p.relative_to(stage)): sha(p) for p in sorted(stage.rglob("*")) if p.is_file()}
        write(stage / "SHA256SUMS.json", hashes)
        stage.rename(out)
    return {k: manifest[k] for k in ("bundles", "assigned_graphs", "source_counts", "packets", "failure_classes", "failure_flags", "saved_proposals")}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundles", nargs="*", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--select", type=Path, help="restrict packets to this final UNKNOWN set; every selected graph must be found")
    parser.add_argument("--round-input", type=Path, help="f3-input for NOT RUN shards recorded in --assembly; never a run bundle")
    parser.add_argument("--assembly", type=Path, help="audited stopped-f3 assembly, required with --round-input")
    parser.add_argument("--python", default=sys.executable, help="Python executable for analyst checker commands")
    parser.add_argument("--labelg", type=Path, default=Path("/usr/bin/nauty-labelg"))
    args = parser.parse_args()
    try:
        require(bool(args.bundles) or args.round_input is not None, 'packet_sources_required')
        require(args.assembly is None or args.round_input is not None, 'assembly_requires_round_input')
        result = build(args.bundles, args.out, args.select, args.python, args.labelg, args.round_input, args.assembly)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print("PACKET ERROR " + str(exc), file=sys.stderr)
        return 2
    print("PACKETS WRITTEN " + compact(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
