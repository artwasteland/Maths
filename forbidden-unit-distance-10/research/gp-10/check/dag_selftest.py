#!/usr/bin/env python3
"""Replay the independent amendment 5 fixtures and their exact mutations."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
os.environ["SYMPY_GROUND_TYPES"] = "python"
sys.dont_write_bytecode = True
import gp10check as ck

FIX = ck.HERE / "fixtures/round3"


def encoded(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def one_field(base, changed, path):
    assert path and encoded(base) != encoded(changed), "empty or inert mutation"
    clone = copy.deepcopy(base)
    a, b = clone, changed
    for key in path[:-1]:
        a, b = a[key], b[key]
    key = path[-1]
    if isinstance(b, dict) and key not in b:
        del a[key]
    else:
        a[key] = copy.deepcopy(b[key])
    assert encoded(clone) == encoded(changed), "mutation changed more than the stated field"


def run(checker, passed, expect_error):
    cases = ck.read_json(FIX / "cases.json")
    by_name = {c["name"]: c for c in cases}
    assert len(by_name) == len(cases)
    positives = {c["file"] for c in cases if c["status"] == "ACCEPT"}
    assert positives == {c["positive"] for c in cases if c["status"] == "REJECT"}
    required = {"forward", "self", "unknown-source", "missing-cofactors", "missing-poly",
                "extra-row-field", "extra-cert-field", "noncanonical-poly", "noncanonical-cofactor",
                "zero-term", "duplicate-term", "failed-identity", "empty-rows", "frame-nonedge"}
    assert {prefix + "-" + suffix for prefix in ("null", "real") for suffix in required} <= by_name.keys()
    assert {"null-last-not-one", "real-last-not-f", "dag-257-rows"} <= by_name.keys()
    accepted = {}
    for case in cases:
        record = ck.read_json(FIX / case["file"])
        ck.check_canonical([record["g6"]])
        if case["status"] == "ACCEPT":
            dep, details = checker.verify(record)
            assert dep is None and details["rows"] == len(record["cert"]["rows"])
            accepted[case["file"]] = record
            passed("DAG " + case["name"], detail="rows=" + str(details["rows"]))
        else:
            base = accepted[case["positive"]]
            one_field(base, record, case["mutation_path"])
            # Record parsing starts from independent JSON values, including bool versus int.
            detail = case.get("detail")
            expect_error("DAG " + case["name"], lambda: checker.verify(record), case["reason"], detail)
    # Exercise record dispatch, serialized reports, and the actual CLI in-process.
    with tempfile.TemporaryDirectory(prefix="dag-selftest-", dir=ck.SCRATCH) as temp:
        for name in ("k23-null-dag", "k23-real-dag-sturm", "null-failed-identity", "real-last-not-f"):
            case = by_name[name]
            record = ck.read_json(FIX / case["file"])
            directory = Path(temp) / name
            directory.mkdir()
            (directory / "input.g6").write_text(record["g6"] + "\n")
            (directory / "records.jsonl").write_text(encoded(record) + "\n")
            (directory / "UNKNOWN.g6").write_text("")
            ck.json_write(directory / "run.json", {"profile": "sample", "input": "input.g6",
                          "input_sha256": ck.digest(directory / "input.g6"), "records": ["records.jsonl"],
                          "forbidden_limit": 0})
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                code = ck.main([str(directory), "--output", str(directory / "checked")])
            lines = captured.getvalue().splitlines()
            good = case["status"] == "ACCEPT"
            assert code == (0 if good else 1), (name, code, lines)
            assert lines[-1] == ("ACCEPT run verified" if good else "REJECT run records_rejected"), (name, lines)
            rows = [ck.loads(line) for line in (directory / "checked/records.jsonl").read_text().splitlines()]
            assert len(rows) == 1 and rows[0]["status"] == case["status"], rows
            if not good:
                assert rows[0]["reason"].split(":", 1)[0] == case["reason"], rows
            passed("DAG CLI " + name, good, lines[-1])
