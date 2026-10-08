#!/usr/bin/env python3
"""Reproduce analyst cases, measure both stages independently, mutate proofs."""
from common import *
import argparse
import copy
import gzip
import sqlite3
from types import SimpleNamespace
from fractions import Fraction
from late_stage import command
from stages import Producers, LATE
from exact import graph6


REPRODUCTIONS = {"JaICZOo@Wd_": "refuted", "JSO@]OSDjB?": "refuted",
                 "JoCBkhGIGJ_": "embedded", "J`C@KHIB^a?": "embedded"}


def check_record(path, directory):
    directory.mkdir(parents=True, exist_ok=True)
    limits(directory / "scratch")
    guard = Guard()
    guard.start()
    ck = checker(directory / "scratch")
    record = json.loads(path.read_text())
    raw = record["g6"] + "\n"
    atomic(directory / "input.g6", raw)
    atomic(directory / "UNKNOWN.g6", raw if record["verdict"] == "unknown" else "")
    atomic(directory / "records.jsonl", path.read_bytes())
    write_json(directory / "run.json", {"profile": "sample", "input": "input.g6",
        "input_sha256": hashlib.sha256(raw.encode()).hexdigest(), "records": ["records.jsonl"], "forbidden_limit": 9})
    lines = []
    report = ck.Run(directory, emit=lines.append).execute()
    atomic(directory / "checker.log", "\n".join(lines) + "\n")
    write_json(directory / "receipt.json", report)
    print(compact({"status": report["status"], "reason": report["reason"], "lines": lines[-3:]}), flush=True)


def checked(path, directory, seconds=120):
    started = time.monotonic()
    command([sys.executable, str(Path(__file__).resolve()), "--check", str(path), "--output", str(directory)],
            directory, "replay", seconds)
    report = json.loads((directory / "receipt.json").read_text())
    return report, time.monotonic()-started


def prune_rows(record):
    rows = record["cert"]["rows"]
    keep = set()
    def visit(i):
        if i in keep:
            return
        keep.add(i)
        for key in rows[i]["cofactors"]:
            if key.startswith("aux:"):
                visit(int(key[4:]))
    visit(len(rows)-1)
    indices = sorted(keep)
    mapping = {"aux:"+str(i): "aux:"+str(j) for j, i in enumerate(indices)}
    record["cert"]["rows"] = [{"poly": rows[i]["poly"],
        "cofactors": {mapping.get(k, k): q for k, q in rows[i]["cofactors"].items()}} for i in indices]


def controls(output, positives):
    first = json.loads(positives["JaICZOo@Wd_"].read_text())
    missing = copy.deepcopy(first)
    last = missing["cert"]["rows"][-1]
    if len(last["cofactors"]) != 4:
        raise AssertionError("four_branch_control_requires_four_contributions")
    removed = sorted(last["cofactors"])[0]
    del last["cofactors"][removed]
    prune_rows(missing)
    changed = copy.deepcopy(first)
    coefficient = next(iter(changed["cert"]["rows"][-1]["cofactors"].values()))[0]
    coefficient[0] = str(2*Fraction(coefficient[0]))
    perturbed = json.loads(positives["JoCBkhGIGJ_"].read_text())
    coordinate = perturbed["cert"]["coords"][0][0]
    coordinate[0] = str(Fraction(coordinate[0])+Fraction(1, 17))
    results = []
    hashes = {code: digest(path) for code, path in positives.items()}
    for name, record, rule in [("missing-branch", missing, "dag_row_identity"),
                               ("selector-coefficient", changed, "dag_row_identity"),
                               ("perturbed-coordinate", perturbed, "edge_equation")]:
        directory = output / "controls" / name
        write_json(directory / "mutation.jsonl", record)
        # Round-trip JSON first; a syntax failure is never a successful control.
        assert json.loads((directory / "mutation.jsonl").read_text()) == record
        report, seconds = checked(directory / "mutation.jsonl", directory / "check")
        rejected = [json.loads(line) for line in (directory / "check/checked/records.jsonl").read_text().splitlines()]
        assert report["status"] == "REJECT" and len(rejected) == 1, report
        assert rejected[0]["reason"].split(":", 1)[0] == rule, rejected
        results.append(dict(name=name, rule=rule, seconds=seconds,
                            output=(directory / "check/checker.log").read_text()))
    for code, path in positives.items():
        assert digest(path) == hashes[code]
        key = hashlib.sha256(code.encode()).hexdigest()[:16]
        report, seconds = checked(path, output / "controls" / ("unchanged-"+key))
        assert report["status"] == "ACCEPT", report
        assert digest(path) == hashes[code]
        results.append(dict(name="unchanged", g6=code, sha256=hashes[code], seconds=seconds,
                            output=(output / "controls" / ("unchanged-"+key) / "checker.log").read_text()))
    write_json(output / "controls.json", results)
    return results


def integration_hints(rows):
    from export import analyst_hints
    from store import Store
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE attempts(gid INTEGER,stage TEXT,outcome TEXT,reason TEXT,budget TEXT,detail TEXT)")
    db.execute("CREATE TABLE history(gid INTEGER,source TEXT,stages TEXT)")
    for row in rows:
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?)", (0, row["stage"], "unknown", "test", "{}", compact(row["detail"])))
    store = SimpleNamespace(db=db, config={"policy": "full"}, poset=SimpleNamespace(codes=[rows[0]["g6"]]))
    hints = analyst_hints(store, 0)
    assert any(h.get("triangle_choices") and h.get("saturation_pairs") for h in hints)
    assert any(h.get("primitive_candidates") and h.get("frame") for h in hints)
    unknown = Store.unknown_record(store, 0)
    db.execute("INSERT INTO history VALUES (?,?,?)", (0, "previous-run", compact(unknown["cert"]["budget"]["stages"])))
    db.execute("DELETE FROM attempts")
    inherited = analyst_hints(store, 0)
    assert [{k: v for k, v in h.items() if k != "prior_run"} for h in inherited] == hints
    db.close()


def benchmark(args):
    inputs = json.loads(args.inputs.read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    limits(output / "scratch")
    guard = Guard()
    guard.start()
    fingerprints = {str(p.relative_to(HERE)): digest(p) for p in
                    [HERE/name for name in ("branch_refute.py", "subfield_exact.py", "late_stage.py", "stages.py", "store.py", "export.py", "test_late_stages.py")]}
    specification = dict(inputs_sha256=digest(args.inputs), sources=fingerprints,
                         budgets=[stage.budget() for stage in LATE], checker_sha256=CHECKER_SHA)
    manifest = output / "manifest.json"
    if manifest.exists():
        assert json.loads(manifest.read_text()) == specification, "resume_sources_or_inputs_changed"
    write_json(manifest, specification)
    items = {row["g6"]: row for row in inputs["inputs"]}
    codes = list(REPRODUCTIONS) + (sorted(set(items)-set(REPRODUCTIONS)) if args.cohort else [])
    # These stages search the input graph; this identity closure exercises their
    # real pipeline adapter without building the unrelated population TU index.
    tu = SimpleNamespace(closure=lambda code: {"g6": code, "old_to_new": list(range(graph6(code)[0])), "steps": []})
    producer = Producers(SimpleNamespace(directory=output), tu)
    rows = []
    positives = {}
    for code in codes:
        if (output / "STOP").exists():
            print("STOP requested between graphs", flush=True)
            return
        key = hashlib.sha256(code.encode()).hexdigest()[:16]
        seed = items[code].get("evidence")
        if seed:
            write_json(output / "scratch/numeric" / key / "numeric.json", seed)
        for stage in LATE:
            directory = output / "cases" / key / stage.method
            result = directory / "result.json"
            if result.exists():
                row = json.loads(result.read_text())
            else:
                guard.check()
                started = time.monotonic()
                proposal, detail = producer.propose(code, stage)
                search_seconds = time.monotonic()-started
                record = directory / "record.jsonl"
                write_json(record, proposal)
                row = dict(g6=code, stage=stage.name, verdict=proposal["verdict"], search_seconds=search_seconds,
                           check_seconds=0, detail=detail, record_bytes=record.stat().st_size)
                if proposal["verdict"] != "unknown":
                    try:
                        report, elapsed = checked(record, directory / "check", stage.check_seconds)
                        row.update(check_seconds=elapsed, checker_status=report["status"], checker_reason=report["reason"])
                        if report["status"] != "ACCEPT":
                            row["verdict"] = "unknown"
                    except (Exception, Deadline) as exc:
                        row.update(verdict="unknown", checker_status="incomplete", checker_reason=type(exc).__name__+":"+str(exc))
                row["seconds"] = time.monotonic()-started
                row["record_sha256"] = digest(record)
                write_json(result, row)
            rows.append(row)
            if code in REPRODUCTIONS and row["verdict"] == REPRODUCTIONS[code]:
                positives[code] = directory / "record.jsonl"
            print(compact({k: row[k] for k in ("g6", "stage", "verdict", "search_seconds", "check_seconds")}), flush=True)
        write_json(output / "measurements.json", rows)
    assert set(positives) == set(REPRODUCTIONS), "analyst_reproduction_failed"
    integration_hints([row for row in rows if row["g6"] in REPRODUCTIONS])
    controls(output, positives)
    summary = {"cohorts": {}, "minimum_available_kib": guard.minimum_kib, "reproductions": []}
    for name, members in {**inputs["cohorts"], "union": list(items)}.items():
        subset = [row for row in rows if row["g6"] in members]
        summary["cohorts"][name] = {"graphs": len(members), "stages": {}}
        for stage in LATE:
            selected = [row for row in subset if row["stage"] == stage.name]
            summary["cohorts"][name]["stages"][stage.name] = dict(attempted=len(selected),
                decided=sum(row["verdict"] != "unknown" for row in selected),
                search_seconds=sum(row["search_seconds"] for row in selected),
                check_seconds=sum(row["check_seconds"] for row in selected))
        summary["cohorts"][name]["decided_union"] = len({row["g6"] for row in subset if row["verdict"] != "unknown"})
    for row in rows:
        if row["g6"] in REPRODUCTIONS and row["verdict"] == REPRODUCTIONS[row["g6"]]:
            summary["reproductions"].append(row)
    write_json(output / "summary.json", summary)
    with gzip.GzipFile(filename=str(output / "records.jsonl.gz"), mode="wb", mtime=0) as stream:
        for row in rows:
            if row["verdict"] != "unknown":
                key = hashlib.sha256(row["g6"].encode()).hexdigest()[:16]
                path = output / "cases" / key / next(stage.method for stage in LATE if stage.name == row["stage"]) / "record.jsonl"
                stream.write(path.read_bytes())
    print(compact(summary), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=HERE / "results/late-stages/inputs.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cohort", action="store_true")
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    if args.check:
        check_record(args.check, args.output)
    else:
        benchmark(args)


if __name__ == "__main__":
    main()
