#!/usr/bin/env python3
"""Own-rule reds, with original evidence rechecked after mutation.

Report/gate unit fixtures use retained GP-10 receipts; they do NOT stand in for
the heavy B10 replay or an outside review. No fixture can publish a B11 result.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
import gp11check as ck

FIX = Path(__file__).resolve().parent / "fixtures"
OLD = ck.GP10 / "check/fixtures"
PASSED = 0
REDS = 0


def passed(name, detail=""):  # B11 test helper.
    global PASSED
    PASSED += 1
    print("PASS " + name + (": " + detail if detail else ""), flush=True)


def red(name, operation, reason):  # B11 test helper: never accept exit status as evidence.
    global REDS
    try:
        operation()
    except ck.Rejection as exc:
        assert exc.reason == reason, (name, reason, str(exc))
        REDS += 1
        passed(name, "REJECT " + str(exc))
    else:
        raise AssertionError(name + " accepted")


def run_ok(path):  # B11 test helper.
    result = ck.Run(path, emit=lambda _: None).execute()
    assert result["status"] == "ACCEPT", result
    return result


def run_red(path, reason, record_reason=None):  # B11 test helper.
    result = ck.Run(path, emit=lambda _: None).execute()
    assert result["status"] == "REJECT" and result["reason"] == reason, result
    if record_reason:
        rows = [ck.loads(line) for line in (path / "checked/records.jsonl").read_text().splitlines()]
        assert any(row["reason"].split(":", 1)[0] == record_reason for row in rows), rows
    raise ck.Rejection(record_reason or reason)


def write_run(path, records, **options):  # B11 test helper.
    path.mkdir(parents=True, exist_ok=True)
    (path / "input.g6").write_text("".join(c + "\n" for c in sorted(r["g6"] for r in records)))
    (path / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (path / "UNKNOWN.g6").write_text("".join(c + "\n" for c in sorted(r["g6"] for r in records if r["verdict"] == "unknown")))
    ck.json_write(path / "run.json", {"profile": "fixture11", "input": "input.g6",
        "input_sha256": ck.digest(path / "input.g6"), "records": ["records.jsonl"], **options})
    return path


def mapped_graph(graph):  # B11 fixture builder: nauty labels determine the coordinate permutation.
    code = ck.canonical(graph)
    mapping = next(ck.nx.algorithms.isomorphism.GraphMatcher(graph.nx(), ck.decode(code).nx()).isomorphisms_iter())
    return code, mapping


def path_record():  # B11 fixture builder: an exact eleven-vertex tree.
    graph = ck.Graph(11, {(i, i + 1) for i in range(10)})
    code, mapping = mapped_graph(graph)
    coords = [None] * 11
    for i, j in mapping.items():
        coords[j] = [[str(i)], ["0"]]
    return {"g6": code, "verdict": "embedded", "cert": {"type": "exact",
        "field": {"minpoly": [0, 1], "interval": ["-1", "1"]}, "coords": coords}}


def polynomial11():  # B11 fixture builder: lift a real GP-10 identity by six isolated vertices.
    original = ck.read_json(OLD / "k4-isolate-null.json")
    old = ck.decode(original["g6"])
    code, mapping = mapped_graph(ck.Graph(11, old.edges))
    cert = copy.deepcopy(original["cert"])
    old_names = ck.regenerate(old, cert["frame"], cert["sat"])[1]
    cert["frame"] = [mapping[v] for v in cert["frame"]]
    cert["sat"] = [sorted(mapping[v] for v in pair) for pair in cert["sat"]]
    names = ck.regenerate(ck.decode(code), cert["frame"], cert["sat"])[1]
    indices = [names.index(name if name.startswith("t_") else name[:2] + str(mapping[int(name[2:])])) for name in old_names]
    for key in ("cofactors", "system"):
        if key not in cert:
            continue
        converted = {}
        for generator, terms in cert[key].items():
            u, v = sorted(mapping[int(v)] for v in generator[2:].split(","))
            lifted = []
            for coefficient, exponents in terms:
                powers = [0] * len(names)
                for i, power in zip(indices, exponents):
                    powers[i] = power
                lifted.append([coefficient, powers])
            converted[f"{generator[:2]}{u},{v}"] = lifted
        cert[key] = converted
    return {"g6": code, "verdict": "refuted", "cert": cert}


def certificate_tests(root, checker):  # B11 rules 2 and inherited order-generic proof routines.
    records = {name: ck.read_json(FIX / filename) for name, filename in
               (("exact11", "lattice11.json"), ("tree11", "tree11.json"), ("tu11", "tu11.json"))}
    records["polynomial11"] = polynomial11()
    records["path11"] = path_record()
    for name, record in records.items():
        assert ck.decode(record["g6"]).n == 11
        checker.verify(record)
        result = run_ok(write_run(root / name, [record]))
        passed(name, result["status"] + " " + record["cert"]["type"])
    bad = copy.deepcopy(records["exact11"])
    u = min(ck.decode(bad["g6"]).edges)[0]
    bad["cert"]["coords"][u][0][0] = str(ck.rational(bad["cert"]["coords"][u][0][0]) + 1)
    red("exact11 coordinate", lambda: checker.verify(bad), "edge_equation")
    bad = copy.deepcopy(records["tree11"])
    bad["cert"]["witness"]["tree"]["move"]["pair"] = [0, 0]
    red("tree11 collision pair", lambda: checker.verify(bad), "tree")
    bad = copy.deepcopy(records["tu11"])
    bad["cert"]["steps"][0]["pair"] = [0, 1]
    red("tu11 distinguished pair", lambda: checker.verify(bad), "tu_distinguished_pair")
    bad = copy.deepcopy(records["polynomial11"])
    first = next(iter(bad["cert"]["cofactors"].values()))
    first[0][0] = str(ck.rational(first[0][0]) + 1)
    red("polynomial11 coefficient", lambda: checker.verify(bad), "cofactor_identity")
    pattern = checker.forbidden[74]
    source = checker.forbidden_codes[74]
    host = ck.Graph(11, ck.decode(source).edges)
    code, mapping = mapped_graph(host)
    pointer = {"g6": code, "verdict": "refuted", "cert": {"type": "sub", "g6": source,
        "map": [mapping[i] for i in range(10)], "index": 74}}
    assert ck.Checker(10).verify(pointer)[0] is None
    red("withheld B10 answer", lambda: ck.Checker(9).verify(pointer), "forbidden_not_in_force")
    assert ck.Checker(10).verify(pointer)[0] is None
    for record in records.values():
        checker.verify(record)
    passed("certificate originals restored", "all order-11 originals ACCEPT")
    return records


def block_tests(checker):  # B11 3: intact forbidden host reaches block_forbidden itself.
    cycle = ck.Graph(11, {(i, i + 1) for i in range(9)} | {(0, 9), (0, 10), (1, 10)})
    assert ck.nx.is_biconnected(cycle.nx())
    deletion = ck.Graph(11, cycle.edges - {(1, 10)})
    evidence = checker.block_evidence(deletion, 10)
    assert max(len(row["vertices"]) for row in evidence["blocks"]) == 10
    passed("eleven-vertex deletion with ten-vertex block", "embedded_by_blocks")
    red("block order ceiling", lambda: checker.block_evidence(deletion, 9), "block_order")
    red("block must be non-biconnected", lambda: checker.block_evidence(cycle, 10), "block_is_biconnected")
    pattern = checker.forbidden[74]
    edge = next(e for e in sorted(pattern.edges) if ck.nx.is_biconnected(ck.Graph(10, pattern.edges - {e}).nx()))
    positive = ck.Graph(11, pattern.edges - {edge} | {(0, 10)})
    original = checker.block_evidence(positive, 10)
    mutated = copy.deepcopy(positive)
    mutated.edges.add(edge)
    # This is the exact map check that an invalid host would fail prematurely.
    ck.mapping(pattern, mutated, list(range(10)), "intact forbidden block")
    assert checker.contains_forbidden(pattern, limit=9) is None
    red("intact ten-vertex forbidden block", lambda: checker.block_evidence(mutated, 10), "block_forbidden")
    assert checker.block_evidence(positive, 10) == original
    assert checker.block_evidence(deletion, 10) == evidence
    passed("block originals restored", "same block partitions")


def coverage_tests(root, records):  # B11 4,8: consumed fixtures, not unused side files.
    directory = write_run(root / "coverage", [records["exact11"], records["path11"]])
    result = run_ok(directory)
    path = directory / "records.jsonl"
    original = path.read_text()
    path.write_text(original.splitlines(keepends=True)[0])
    red("omitted candidate record", lambda: run_red(directory, "coverage"), "coverage")
    path.write_text(original)
    assert run_ok(directory)["counts"] == result["counts"]
    path.write_text(original + original.splitlines(keepends=True)[0])
    red("duplicated candidate record", lambda: run_red(directory, "duplicate_record"), "duplicate_record")
    path.write_text(original)
    manifest = ck.read_json(directory / "run.json")
    bad = {**manifest, "input_sha256": "0" * 64}
    ck.json_write(directory / "run.json", bad)
    red("wrong input bytes hash", lambda: run_red(directory, "input_hash"), "input_hash")
    ck.json_write(directory / "run.json", manifest)
    ck.json_write(directory / "run.json", {**manifest, "controls": []})
    red("malformed controls object", lambda: run_red(directory, "controls_required"), "controls_required")
    ck.json_write(directory / "run.json", manifest)
    with patch.object(ck, "GP11", root / "freeze"):
        frozen = ck.GP11 / "data"
        frozen.mkdir(parents=True)
        shutil.copy(directory / "input.g6", frozen / "B11.g6")
        sha = ck.digest(frozen / "B11.g6")
        (frozen / "SHA256SUMS").write_text(sha + "  B11.g6\n")
        run = ck.Run(directory, b11_sha256=sha)
        run.manifest = {**manifest, "profile": "B11"}
        run.frozen_input()
        run.b11_sha256 = "0" * 64
        red("B11 independent frozen hash", run.frozen_input, "frozen_input_hash")
        run.b11_sha256 = None
        red("B11 missing external hash", run.frozen_input, "b11_hash_required")
        run.b11_sha256 = sha
        original_input = (frozen / "B11.g6").read_bytes()
        (frozen / "B11.g6").write_bytes(original_input.splitlines(keepends=True)[0])
        red("B11 omitted frozen candidate", run.frozen_input, "frozen_input_hash")
        (frozen / "B11.g6").write_bytes(original_input)
        run.frozen_input()
        passed("frozen fixture restored", "same external digest accepted")
    # L11 is a product too: never erase a certificate stream with that name.
    shutil.copy(path, directory / "L11.g6")
    ck.json_write(directory / "run.json", {**manifest, "records": ["L11.g6"]})
    guarded = ck.Run(directory, directory, emit=lambda _: None).execute()
    assert guarded["reason"] == "output_input_collision", guarded
    passed("L11 output collision", "REJECT output_input_collision")
    ck.json_write(directory / "run.json", manifest)
    assert run_ok(directory)["counts"] == result["counts"]
    passed("coverage originals restored", "same counts and ACCEPT")

    # All earlier input rules pass: this graph is canonical and biconnected on eleven vertices.
    count_dir = write_run(root / "census-count", [records["exact11"]])
    count_run = ck.Run(count_dir)
    count_run.input = count_dir / "input.g6"
    count_run.manifest = ck.read_json(count_dir / "run.json")
    count_run.profile = "fixture11"
    count_run.db = ck.sqlite3.connect(":memory:")
    count_run.db.execute("CREATE TABLE inputs(g6 TEXT PRIMARY KEY)")
    count_run.load_input()
    count_run.db.execute("DELETE FROM inputs")
    count_run.profile = "B11"
    red("B11 incomplete census", count_run.load_input, "b11_input_count")
    count_run.db.execute("DELETE FROM inputs")
    count_run.profile = "fixture11"
    count_run.load_input()
    count_run.db.close()
    passed("census fixture restored", "one canonical fixture accepted only as fixture11")

    original_loader = ck.Run.load_records
    def change_consumed(run):  # B11 test hook: change only bytes already consumed by the checker.
        original_loader(run)
        with path.open("a") as stream:
            stream.write(" ")
    with patch.object(ck.Run, "load_records", change_consumed):
        red("record changed during check", lambda: run_red(directory, "inputs_changed_during_check"),
            "inputs_changed_during_check")
    path.write_text(original)
    assert run_ok(directory)["counts"] == result["counts"]
    passed("consumed record restored", "same counts and ACCEPT")
    receipt = ck.read_json(directory / "checked/report.json")
    ck.consumed_receipts(directory, receipt, receipt["artifacts"])
    bad = copy.deepcopy(receipt)
    bad["files"][0]["sha256"] = "0" * 64
    red("streamed certificate hash", lambda: ck.consumed_receipts(directory, bad, receipt["artifacts"]),
        "consumed_record_hash")
    ck.consumed_receipts(directory, receipt, receipt["artifacts"])
    passed("streamed receipt restored")


def control_tests(root, checker):  # B11 5: real retained reports, preflight only.
    directory = root / "control-gate"
    directory.mkdir()
    controls = {name: "controls/" + name for name in ck.CONTROL_NAMES}
    with tarfile.open(ck.GP10 / "cloud/final/tree-public.tar.gz") as archive:
        for name in (*ck.base.CONTROL_ORDERS, "regressions"):
            target = directory / controls[name] / "checked"
            target.mkdir(parents=True)
            raw = archive.extractfile(f"tree/controls/{name}/checked/report.json").read()
            (target / "report.json").write_bytes(raw)
    output = directory / controls["B10"] / "checked"
    output.mkdir(parents=True)
    for name in ("report.json", "L10.g6"):
        shutil.copy(ck.GP10 / "runs/B10-final-2026-09-25" / name, output / name)
    named = directory / controls["named11"] / "checked"
    named.mkdir(parents=True)
    # Only the report-presence branch is tested here; real named11 replay is in small_controls.py.
    ck.json_write(named / "report.json", {"profile": "named11", "status": "ACCEPT"})
    run = ck.Run(directory)
    run.manifest = {"controls": controls}
    run.checker = checker
    expected = run.control_reports()
    report = ck.read_json(output / "report.json")
    assert ck.complete_b10(report, output, checker)["members"] == 324
    for field, value in (("counts", {**report["counts"], "unknown": 1}), ("conditional", True),
                         ("conditional_minimal", [{"g6": report["minimal"][0]}]), ("direct_rejections", 1)):
        ck.json_write(output / "report.json", {**report, field: value})
        red("partial ACCEPT B10 " + field, run.control_reports, "b10_incomplete")
        ck.json_write(output / "report.json", report)
        assert run.control_reports() == expected
    ck.json_write(output / "report.json", {**report, "forbidden_limit": 10})
    red("B10 seeded with F10 answers", run.control_reports, "b10_control_input")
    ck.json_write(output / "report.json", report)
    original = (output / "L10.g6").read_bytes()
    (output / "L10.g6").write_bytes(b"".join(original.splitlines(keepends=True)[:-1]))
    red("B10 derived list missing one", run.control_reports, "b10_derived_list")
    (output / "L10.g6").write_bytes(original)
    saved = (named / "report.json").read_bytes()
    (named / "report.json").unlink()
    red("missing named11 report", run.control_reports, "control_report_missing")
    (named / "report.json").write_bytes(saved)
    ck.json_write(named / "report.json", [])
    red("malformed control report", run.control_reports, "control_report_not_accepted")
    (named / "report.json").write_bytes(saved)
    ck.json_write(named / "report.json", {"profile": "named11", "status": "REJECT"})
    red("unaccepted named11 report", run.control_reports, "control_report_not_accepted")
    (named / "report.json").write_bytes(saved)
    run.manifest["controls"] = {k: v for k, v in controls.items() if k != "B9p"}
    red("omitted control", run.control_reports, "controls_required")
    run.manifest["controls"] = {**controls, "B4p": str(root / "outside")}
    red("control outside run tree", run.control_reports, "control_outside_run_tree")
    run.manifest["controls"] = controls
    # Retarget only the symlink; the intact accepted report is byte-identical.
    target = directory / controls["B4p"] / "checked/report.json"
    saved_report = target.read_bytes()
    inside = directory / "positive-report.json"
    outside = root / "outside-report.json"
    inside.write_bytes(saved_report)
    outside.write_bytes(saved_report)
    target.unlink()
    target.symlink_to(inside)
    assert run.control_reports() == expected
    ck.json_write(directory / "run.json", {"controls": {"B4p": controls["B4p"]}})
    ck.json_write(directory / controls["B4p"] / "run.json", {"controls": {}})
    paths = ck.control_report_paths(directory)
    target.unlink()
    target.symlink_to(outside)
    red("control report symlink outside run tree", run.control_reports, "control_outside_run_tree")
    red("receipt traversal symlink outside run tree", lambda: ck.control_report_paths(directory), "control_outside_run_tree")
    target.unlink()
    target.write_bytes(saved_report)
    assert ck.control_report_paths(directory) == paths
    assert run.control_reports() == expected
    passed("control reports restored", "original 324; preflight only, heavy replay still required")


def named_tests(root):  # B11 7: paired provenance and direct-certificate rules.
    directory = root / "named11"
    shutil.copytree(FIX / "named11", directory)
    original = run_ok(directory)
    passed("named11 retained general-search positives", "ACCEPT two exact embeddings")
    provenance = ck.read_json(directory / "provenance.json")
    bad = copy.deepcopy(provenance)
    bad[next(iter(bad))]["method"] = "coordinate-lookup"
    ck.json_write(directory / "provenance.json", bad)
    red("named11 lookup provenance", lambda: run_red(directory, "control_not_general_search"), "control_not_general_search")
    ck.json_write(directory / "provenance.json", provenance)
    assert run_ok(directory)["counts"] == original["counts"]
    records = [ck.loads(line) for line in (directory / "records.jsonl").read_text().splitlines()]
    record = records[0]
    graph = ck.decode(record["g6"])
    code, mapping = mapped_graph(ck.Graph(12, graph.edges))
    cert = copy.deepcopy(record["cert"])
    degree = len(cert["field"]["minpoly"]) - 1
    points = cert["coords"] + [[["10000"] + ["0"] * (degree - 1), ["0"] * degree]]
    coords = [None] * 12
    for i, j in mapping.items():
        coords[j] = points[i]
    cert["coords"] = coords
    host = {"g6": code, "verdict": "embedded", "cert": cert}
    (directory / "hosts.jsonl").write_text(json.dumps(host) + "\n")
    manifest = ck.read_json(directory / "run.json")
    ck.json_write(directory / "run.json", {**manifest, "hosts": "hosts.jsonl"})
    assert run_ok(directory)["counts"] == original["counts"]
    modified = copy.deepcopy(records)
    modified[0]["cert"] = {"type": "super", "g6": code, "map": [mapping[i] for i in range(11)]}
    (directory / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in modified))
    red("named11 library pointer", lambda: run_red(directory, "control_library_pointer"), "control_library_pointer")
    (directory / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    assert run_ok(directory)["counts"] == original["counts"]
    passed("named11 originals restored", "same two embeddings")


def minimality_tests(root, checker):  # B11 6: genuine proofs and one unknown deletion.
    records = [ck.loads(line) for line in (FIX / "minimality11.jsonl").read_text().splitlines()]
    parent = records[0]
    assert parent["verdict"] == "refuted" and all(r["verdict"] == "embedded" for r in records[1:])
    directory = write_run(root / "minimality11", records, derive=True)
    positive = run_ok(directory)
    assert positive["minimal"] == [parent["g6"]] and positive["conditional"] is False
    passed("eleven-vertex minimality", "ACCEPT minimal=1 conditional=false")
    unknown = copy.deepcopy(records)
    child = unknown[1]["g6"]
    unknown[1] = {"g6": child, "verdict": "unknown", "cert": {"reason": "own-rule fixture budget", "budget": {"seconds": 0}}}
    write_run(directory, unknown, derive=True)
    result = run_ok(directory)
    assert result["counts"]["unknown"] == 1 and result["conditional"] is True
    assert result["conditional_minimal"] == [{"g6": parent["g6"], "requires_embedded": [child]}]
    evidence = ck.loads((directory / "checked/minimality.jsonl").read_text().strip())
    assert evidence["status"] == "minimal_if_all_listed_deletions_embed"
    passed("one unknown deletion cannot certify unconditional minimality", "ACCEPT conditional=true minimal_if_all_listed_deletions_embed")
    write_run(directory, records, derive=True)
    assert run_ok(directory)["minimal"] == positive["minimal"]

    # Missing host evidence reaches the deletion rule, with input coverage still exact.
    host_dir = write_run(root / "minimality-hosts", [parent], derive=True, hosts="hosts.jsonl")
    hosts = "".join(json.dumps(r) + "\n" for r in records[1:])
    (host_dir / "hosts.jsonl").write_text(hosts)
    assert run_ok(host_dir)["minimal"] == positive["minimal"]
    (host_dir / "hosts.jsonl").write_text("".join(hosts.splitlines(keepends=True)[1:]))
    red("eleven-vertex missing deletion evidence", lambda: run_red(host_dir, "minimality_deletion_missing"),
        "minimality_deletion_missing")
    (host_dir / "hosts.jsonl").write_text(hosts)
    assert run_ok(host_dir)["minimal"] == positive["minimal"]

    # Exercise the L11 output branch on the same verified records, without a B11 claim.
    original_minimality = ck.Run.minimality
    def list_branch(run):  # B11 test hook: only the output filename branch changes.
        profile = run.profile
        run.profile = "B11"
        try:
            original_minimality(run)
        finally:
            run.profile = profile
    with patch.object(ck.Run, "minimality", list_branch):
        listed = run_ok(directory)
        assert listed["profile"] == "fixture11" and listed["minimal_file"] == "L11.g6"
        assert ck.graph_list(directory / "checked/L11.g6") == positive["minimal"]
    passed("L11 output branch", "same derived member, fixture-only report")

    graph = ck.decode(parent["g6"])
    bigger = None
    for u in range(11):
        for v in range(u + 1, 11):
            if (u, v) in graph.edges:
                continue
            candidate = ck.Graph(11, graph.edges | {(u, v)})
            if checker.contains_forbidden(candidate, limit=10) is None:
                bigger = candidate
                break
        if bigger is not None:
            break
    assert bigger is not None, "fixture needs an F10-free supergraph"
    code, mapping = mapped_graph(bigger)
    super_record = {"g6": code, "verdict": "refuted", "cert": {"type": "sub", "g6": parent["g6"],
                    "map": [mapping[i] for i in range(11)]}}
    all_records = {r["g6"]: r for r in records + [super_record]}
    for edge in bigger.edges:
        deletion = ck.Graph(11, bigger.edges - {edge})
        if ck.nx.is_biconnected(deletion.nx()):
            child = ck.canonical(deletion)
            all_records.setdefault(child, {"g6": child, "verdict": "unknown", "cert":
                {"reason": "nonminimal control needs no proof of this deletion", "budget": {}}})
    nonminimal = write_run(root / "nonminimal11", list(all_records.values()), derive=True, minimal_claim="claim.g6")
    (nonminimal / "claim.g6").write_text(parent["g6"] + "\n")
    result = run_ok(nonminimal)
    assert result["nonminimal_count"] == 1 and result["minimal"] == [parent["g6"]]
    (nonminimal / "claim.g6").write_text("".join(c + "\n" for c in sorted([parent["g6"], code])))
    red("eleven-vertex claimed minimal with refuted deletion", lambda: run_red(nonminimal, "minimality_claim_refuted_deletion"),
        "minimality_claim_refuted_deletion")
    (nonminimal / "claim.g6").write_text(parent["g6"] + "\n")
    assert run_ok(nonminimal)["minimal"] == result["minimal"]
    assert run_ok(directory)["conditional"] is False
    passed("minimality originals restored", "same minimal list; known refuted deletion defeats unknowns")


def writer_tests(root):  # B11 W1,W2: mutate exactly the report/review field actually consumed.
    spec = importlib.util.spec_from_file_location("gp11_writer", ck.GP11 / "tools/write_result.py")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    checked = root / "writer/checked"
    checked.mkdir(parents=True)
    (checked / "L11.g6").write_text("")
    evidence = root / "writer/evidence.txt"
    evidence.write_text("SYNTHETIC receipt unit fixture; no classification or outside review is claimed.\n")
    sources = ck.source_hashes()
    sha = ck.digest(evidence)
    report = {"status": "ACCEPT", "reason": "verified", "profile": "B11", "counts":
              {"embedded": 448708, "refuted": 0, "unknown": 0}, "input_count": 448708,
              "conditional": False, "conditional_minimal": [], "direct_rejections": 0,
              "profile_sources": sources, "minimal_file": "L11.g6", "minimal": [], "minimal_count": 0,
              "nonminimal_count": 0, "input_sha256": sha, "frozen_B11_sha256": sha,
              "predictions": {"sha256": sha}}
    fake = root / "writer/freeze/data"
    fake.mkdir(parents=True)
    shutil.copy(evidence, fake / "B11.g6")
    with patch.object(ck, "GP11", fake.parent), patch.object(ck, "source_hashes", return_value=sources):
        assert writer.validate_report(report, checked, sha) == []
        bad = {**report, "conditional": True}
        red("writer otherwise-ACCEPT conditional report", lambda: writer.validate_report(bad, checked, sha), "writer_conditional")
        bad = {**report, "profile": "fixture11"}
        red("writer fixture cannot publish", lambda: writer.validate_report(bad, checked, sha), "writer_profile")
        bad = {**report, "counts": {**report["counts"], "embedded": 448707}}
        red("writer count mismatch", lambda: writer.validate_report(bad, checked, sha), "writer_counts")
        assert writer.validate_report(report, checked, sha) == []
    ck.json_write(checked / "report.json", report)
    gates = {f"G{i}": {"status": "PASS", "evidence": [{"path": "evidence.txt", "sha256": sha}]} for i in range(6)}
    gates["G0"]["input_sha256"] = sha
    gates["G1"].update(sources=sources, selftest_committed=True)
    gates["G2"].update(predictions_sha256=sha, predictions_committed_before_run=True)
    gates["G3"]["report_sha256"] = ck.digest(checked / "report.json")
    gates["G4"]["L11_sha256"] = ck.digest(checked / "L11.g6")
    gates["G5"].update(sources=sources, findings_answered=True, outside_reviewer="fixture only")
    path = root / "writer/gates.json"
    ck.json_write(path, gates)
    check = lambda: writer.validate_gates(ck.read_json(path), path.parent, checked, report)
    original = check()
    for label, gate, field, value, reason in (
        ("stale G5 review", "G5", "sources", {**sources, "research/gp-11/check/gp11check.py": "0" * 64}, "writer_stale_review"),
        ("open G0", "G0", "status", "OPEN", "writer_gate_open"),
        ("uncommitted selftest", "G1", "selftest_committed", False, "writer_g1_sources"),
        ("late predictions", "G2", "predictions_committed_before_run", False, "writer_prediction_chronology"),
        ("stale report", "G3", "report_sha256", "0" * 64, "writer_report_hash"),
        ("stale derived list", "G4", "L11_sha256", "0" * 64, "writer_g4_list"),
        ("unanswered findings", "G5", "findings_answered", False, "writer_review_open"),
        ("stale evidence", "G0", "evidence", [{"path": "evidence.txt", "sha256": "0" * 64}], "writer_evidence_hash"),
    ):
        bad = copy.deepcopy(gates)
        bad[gate][field] = value
        ck.json_write(path, bad)
        red("writer " + label, check, reason)
        ck.json_write(path, gates)
        assert check() == original
    passed("writer receipt originals restored", "unit receipts only; no B11 publication")


def main():  # B11 own-rule suite.
    checker = ck.Checker()
    with tempfile.TemporaryDirectory(prefix="gp11-selftest-") as tmp:
        root = Path(tmp)
        records = certificate_tests(root, checker)
        block_tests(checker)
        coverage_tests(root, records)
        control_tests(root, checker)
        named_tests(root)
        minimality_tests(root, checker)
        writer_tests(root)
    ck.verify_frozen()
    path = ck.GP10 / "check/gp10check.py"
    with patch.dict(ck.PINS, {path: "0" * 64}):
        red("frozen verifier hash", ck.verify_frozen, "frozen_source_hash")
    ck.verify_frozen()
    named_source = ck.U22 / "sources/amp/anc/graph6.txt"
    assert ck.PINS[named_source] == ck.digest(named_source)
    with patch.dict(ck.PINS, {named_source: "0" * 64}):
        red("named problem source hash", ck.verify_frozen, "frozen_source_hash")
    ck.verify_frozen()
    with patch.object(ck, "PROFILE_AT_IMPORT", "0" * 64):
        red("profile replaced after import", ck.source_hashes, "profile_changed_since_import")
    ck.source_hashes()
    passed("frozen verifier originals restored")
    print(f"GP11 SELFTEST PASS checks={PASSED} rejected_mutations={REDS}")


if __name__ == "__main__":
    main()
