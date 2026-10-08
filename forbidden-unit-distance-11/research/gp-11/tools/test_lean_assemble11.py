#!/usr/bin/env python3
"""CLI controls, real frozen-checker replays, and a 448,708-graph structural scale test.

Run with the pinned interpreter through tools/guard.py, in a fresh --output.
--suite positive replays both priority orders of the actual 2,000-graph sample.
--suite red includes a real positive replay after EACH of the four red controls.
Scale certificates are deliberately incomplete and are NEVER given to the checker.
Every child command, output tail, wall time and peak RSS is retained in results.json.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
GP11 = HERE.parent
ROOT = GP11.parents[1]
PYTHON = Path.home() / "tools/pyenv-gp10/bin/python"
TOOL = HERE / "lean_assemble11.py"
GUARD = HERE / "guard.py"
CHECKER = GP11 / "check/gp11check.py"
SAMPLE = GP11 / "pipeline/results/escalation-2000.g6"
PROBES = [GP11 / "pipeline/cloud" / f"probe-{i:03d}" for i in range(4)]
DESKTOP = GP11 / "pipeline/results/escalation-2000"
MAX_LINE = 8 * 1024 * 1024

# Real TU/sub cycle from the pipeline's two-step forcing control. Both direct
# proofs and both pointers are replayed below. No producer or receipt is trusted.
G = "J??@gzGx@r?"
H = "J?GHe_MpHm?"
STEP = {"gadget": 0, "map": [7, 5, 6, 3, 10, 2], "pair": [2, 5]}
G_DIRECT = {"g6": G, "verdict": "refuted", "cert": {"type": "tu", "steps": [STEP,
    {"gadget": 5, "map": [2, 10, 6, 3, 7, 5, 9, 4], "pair": [4, 9]}],
    "end": {"forbidden": 1, "map": [1, 4, 0, 8, 9]}}}
H_DIRECT = {"g6": H, "verdict": "refuted", "cert": {"type": "tu", "steps": [
    {"gadget": 5, "map": [5, 10, 4, 2, 6, 8, 9, 3], "pair": [3, 9]}],
    "end": {"forbidden": 1, "map": [1, 3, 0, 7, 9]}}}
G_POINTER = {"g6": G, "verdict": "refuted", "cert": {"type": "tu", "steps": [STEP],
    "end": {"refuted": H, "map": [0, 1, 3, 4, 6, 2, 7, 8, 5, 9, 10]}}}
H_POINTER = {"g6": H, "verdict": "refuted", "cert": {"type": "sub", "g6": G,
    "map": [0, 1, 5, 2, 3, 8, 4, 6, 7, 9, 10]}}


def encode(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as stream:
        for line in stream:
            yield json.loads(line)


def write_rows(path, rows):
    with path.open("wb") as stream:
        for row in rows:
            stream.write(encode(row))
    return path


def write_input(path, codes):
    path.write_text("".join(code + "\n" for code in sorted(set(codes))))
    return path


def load_tool():
    spec = importlib.util.spec_from_file_location("lean11_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tests:
    def __init__(self, out, index):
        self.out, self.index = out, index
        self.commands = []
        (out / "logs").mkdir()

    def run(self, label, arguments, failure=None):
        log = self.out / "logs" / (label + ".log")
        timing = self.out / "logs" / (label + ".time")
        command = ["nice", "-n", "10", str(PYTHON), "-B", str(GUARD), "--", "/usr/bin/time",
                   "-f", "wall_seconds=%e peak_rss_kib=%M", "-o", str(timing), str(PYTHON), "-B",
                   *map(str, arguments)]
        print("COMMAND " + shlex.join(command), flush=True)
        start = time.monotonic()
        with log.open("w") as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT,
                                       env={**os.environ, "SYMPY_GROUND_TYPES": "python", "PYTHONDONTWRITEBYTECODE": "1"})
            while True:
                try:
                    code = process.wait(timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    print(f"TEST RUNNING {label} seconds={time.monotonic() - start:.0f}", flush=True)
        output = log.read_text()
        tail = "\n".join(output.splitlines()[-5:])
        measured = timing.read_text().strip() if timing.exists() else "timing unavailable"
        print(f"TAIL {label}\n{tail}\nTIME {measured}", flush=True)
        result = {"label": label, "command": shlex.join(command), "exit": code, "tail": tail,
                  "timing": measured, "log": str(log)}
        self.commands.append(result)
        (self.out / "results.json").write_text(json.dumps(self.commands, indent=2) + "\n")
        if failure:
            assert code != 0 and failure in output, (label, code, output[-4000:])
        else:
            assert code == 0, (label, code, output[-4000:])
        return output

    def audit(self, out, inp):
        # Independent file audit. Never add seed summary counts together.
        inputs = inp.read_text().splitlines()
        decisions = list(read_rows(out / "records.jsonl"))
        codes = [row["g6"] for row in decisions]
        code_set = set(codes)
        assert len(codes) == len(code_set)
        assert code_set <= set(inputs)
        assert codes == [code for code in inputs if code in code_set]
        counts = Counter(row["verdict"] for row in decisions)
        assert set(counts) <= {"embedded", "refuted"}
        unknown = (out / "UNKNOWN.g6").read_text().splitlines()
        assert unknown == [code for code in inputs if code not in code_set]
        unknown_rows = list(read_rows(out / "unknown-records.jsonl"))
        assert [row["g6"] for row in unknown_rows] == unknown
        assert all(row["verdict"] == "unknown" for row in unknown_rows)
        counts = {"embedded": counts["embedded"], "refuted": counts["refuted"], "unknown": len(unknown)}
        report = json.loads((out / "assembly.json").read_text())
        assert report["counts"] == counts
        assert report["hosts"] == sum(1 for _ in read_rows(out / "hosts.jsonl"))
        for name, receipt in report["outputs"].items():
            assert receipt["sha256"] == sha(out / name)
            assert receipt["bytes"] == (out / name).stat().st_size
        for seed in report["seeds"]:
            if seed.get("kind") == "pipeline_state":
                with Path(seed["path"]).open("rb") as stream:
                    consumed = hashlib.sha256()
                    left = seed["bytes"]
                    while left:
                        raw = stream.read(min(left, 1024 * 1024))
                        assert raw
                        consumed.update(raw)
                        left -= len(raw)
                assert seed["sha256"] == consumed.hexdigest()
                assert seed["snapshot_sha256"] == sha(out / seed["snapshot_file"])
            else:
                assert seed["sha256"] == sha(seed["path"])
        assert (out / "assembly.json.sha256").read_text() == sha(out / "assembly.json") + "  assembly.json\n"
        return counts

    def assemble(self, label, inp, seeds, extra=()):
        out = self.out / label
        self.run(label, [TOOL, "--input", inp, "--out", out, *extra, *seeds])
        self.run(label + "-structure", [TOOL, "--check", out, "--input", inp])
        self.audit(out, inp)
        return out

    def replay(self, label, out, inp, failure=None, profile="sample", limit=None, no_hosts=False):
        manifest = {"profile": profile, "derive": False, "forbidden_limit": limit if limit is not None else
                    (10 if profile == "fixture11" else 9),
                    "input": str(inp.resolve()), "input_sha256": sha(inp),
                    "records": ["records.jsonl", "unknown-records.jsonl"], "hosts": "hosts.jsonl",
                    "unknown": "UNKNOWN.g6"}
        if no_hosts:
            assert (out / "hosts.jsonl").stat().st_size == 0
            del manifest["hosts"]
        (out / "run.json").write_text(json.dumps(manifest) + "\n")
        output = self.run(label, [CHECKER, out], failure=failure)
        report = json.loads((out / "checked/report.json").read_text())
        if failure:
            assert report["status"] == "REJECT" and failure in output
            return report
        assert "ACCEPT run verified\n" in output
        counts = self.audit(out, inp)
        assert report["status"] == "ACCEPT" and report["reason"] == "verified"
        assert report["counts"] == counts and report["input_count"] == sum(counts.values())
        assert report["direct_rejections"] == 0
        assert report["hosts"] == sum(1 for _ in read_rows(out / "hosts.jsonl"))
        assert report["conditional"] == bool(counts["unknown"])
        if profile == "fixture11":
            assert report["scope"] == "fixture-only" and report["forbidden_limit"] == manifest["forbidden_limit"]
        print("CHECKER COUNTS " + label + " " + json.dumps(report["counts"], sort_keys=True), flush=True)
        return report

    def rewrite(self):
        four = {"J@?_iVGbF__", "J@CIHEDuFB?", "Jk?AkoLHHS_", "Jq?AXY`DGs_"}
        all_rows = {r["g6"]: r for r in read_rows(DESKTOP / "records.jsonl.gz")}
        endpoints = {all_rows[code]["cert"]["end"]["refuted"] for code in four}
        inp = write_input(self.out / "rewrite-four.g6", four)
        original = [all_rows[code] for code in sorted(four | endpoints)]
        seed = write_rows(self.out / "rewrite-four.jsonl", original)
        clean = self.assemble("rewrite-four", inp, [seed], ["--rewrite-outside-ends"])
        evidence = json.loads((clean / "assembly.json").read_text())
        assert self.audit(clean, inp) == {"embedded": 0, "refuted": 4, "unknown": 0}
        assert len(evidence["rewrites"]) == 4 and not evidence["rewrite_failures"]
        self.replay("rewrite-four-checker", clean, inp, profile="fixture11", no_hosts=True)

        # One changed map entry, leaving every TU step and forbidden index intact.
        bad = self.out / "rewrite-map-red"
        shutil.copytree(clean, bad, ignore=shutil.ignore_patterns("checked", "run.json"))
        changed = list(read_rows(bad / "records.jsonl"))
        changed[0]["cert"]["end"]["map"][0] = changed[0]["cert"]["end"]["map"][1]
        write_rows(bad / "records.jsonl", changed)
        rejected = self.replay("rewrite-map-red-checker", bad, inp, "map_not_injective: TU forbidden end",
                               profile="fixture11", no_hosts=True)
        assert rejected["direct_rejections"] == 1
        rejected_rows = list(read_rows(bad / "checked/records.jsonl"))
        assert any(r.get("reason") == "map_not_injective: TU forbidden end" for r in rejected_rows)
        self.replay("rewrite-map-real-after", clean, inp, profile="fixture11", no_hosts=True)

        # The tool must refuse an unavailable first F10 index before publishing.
        limited = self.out / "rewrite-limit-red"
        self.run("rewrite-limit-red", [TOOL, "--input", inp, "--out", limited,
                 "--rewrite-outside-ends", "--forbidden-limit", "9", seed], "rewrite_forbidden_not_in_force")
        assert not limited.exists()
        self.replay("rewrite-limit-real-after", clean, inp, profile="fixture11", no_hosts=True)

        # Ten isolated vertices are embeddable. The false refutation is only a
        # producer input. It cannot provide an F10 endpoint and never reaches the checker.
        empty = "I????????"
        fake = copy.deepcopy(all_rows[sorted(four)[0]])
        fake["cert"]["end"]["refuted"] = empty
        fake["cert"]["end"]["map"] = list(range(10))
        false_support = {"g6": empty, "verdict": "refuted", "cert": {"type": "tree"}}
        fake_input = write_input(self.out / "rewrite-empty.g6", [fake["g6"]])
        fake_seed = write_rows(self.out / "rewrite-empty.jsonl", [fake, false_support])
        dropped = self.assemble("rewrite-empty-red", fake_input, [fake_seed], ["--rewrite-outside-ends"])
        dropped_report = json.loads((dropped / "assembly.json").read_text())
        assert dropped_report["counts"] == {"embedded": 0, "refuted": 0, "unknown": 1}
        assert dropped_report["rewrite_failures"][0]["reason"] == "rewrite_no_F10_member"
        assert not dropped_report["rewrites"] and not (dropped / "records.jsonl").read_bytes()
        self.replay("rewrite-empty-unknown-checker", dropped, fake_input, profile="fixture11", no_hosts=True)
        self.replay("rewrite-empty-real-after", clean, inp, profile="fixture11", no_hosts=True)

        # A nontrivial stored-to-canonical conversion for the second allowed rule.
        tool = load_tool()
        rewriter = tool.OutsideEnds(10)
        ck = rewriter.ck
        # The four real ten-vertex endpoints happen to use canonical stored
        # labels. Select a frozen pattern whose stored labels really differ.
        index = next(i for i, p in enumerate(rewriter.checker.forbidden)
                     if ck.base.encode(p) != rewriter.checker.forbidden_codes[i])
        d = rewriter.checker.forbidden_codes[index]
        graph = ck.base.decode(d)
        larger = ck.base.Graph(11, set(graph.edges))
        code = ck.base.canonical_many([ck.base.encode(larger)])[0]
        # Labels from decoded D into this new canonical graph, using an exact
        # graph isomorphism to the same graph with its original eleven labels.
        iso = next(ck.base.nx.algorithms.isomorphism.GraphMatcher(
            larger.nx(), ck.base.decode(code).nx()).isomorphisms_iter())
        pointer = {"g6": code, "verdict": "refuted", "cert": {
            "type": "sub", "g6": d, "map": [iso[j] for j in range(graph.n)]}}
        sub_input = write_input(self.out / "rewrite-sub.g6", [code])
        support = {"g6": d, "verdict": "refuted", "cert": {
            "type": "sub", "g6": d, "index": index, "map": list(range(graph.n))}}
        sub_seed = write_rows(self.out / "rewrite-sub.jsonl", [pointer, support])
        sub = self.assemble("rewrite-sub", sub_input, [sub_seed], ["--rewrite-outside-ends"])
        sub_event = json.loads((sub / "assembly.json").read_text())["rewrites"][0]
        assert sub_event["rule"] == "sub_canonical"
        assert sub_event["canonical_to_stored"] != list(range(len(sub_event["phi"])))
        self.replay("rewrite-sub-checker", sub, sub_input, profile="fixture11", no_hosts=True)

        self.rewrite_state_fixture(inp, original)

        # Legacy sample cannot admit ten-vertex F10 entries. Exercise both the
        # index rule and the profile limit, without altering any frozen code.
        self.replay("rewrite-legacy-index-red", clean, inp, "forbidden_not_in_force", no_hosts=True)
        self.replay("rewrite-legacy-real-after", clean, inp, profile="fixture11", no_hosts=True)
        for label, seeds in (("rewrite-probe-first", [*PROBES, DESKTOP]),
                             ("rewrite-desktop-first", [DESKTOP, *PROBES])):
            assembled = self.assemble(label, SAMPLE, seeds, ["--rewrite-outside-ends", "--no-propagate"])
            actual = {r["g6"]: r for r in read_rows(assembled / "records.jsonl")}
            assert set(actual) <= set(SAMPLE.read_text().splitlines())
            assert all(actual[code]["verdict"] == "refuted" for code in four)
            assert self.audit(assembled, SAMPLE) == {"embedded": 1979, "refuted": 19, "unknown": 2}
            report = json.loads((assembled / "assembly.json").read_text())
            assert report["hosts"] == 0 and report["rewrite_outside_ends"]["selected_rewrites"] == 4
            assert report["rewrite_outside_ends"]["restored_by_verdict"] == {"refuted": 4}
            # Re-derive receipts and unchanged priority from actual seed bytes.
            first = {}
            for bundle in seeds:
                with gzip.open(bundle / "records.jsonl.gz", "rb") as stream:
                    for raw in stream:
                        row = json.loads(raw)
                        if row["verdict"] != "unknown":
                            first.setdefault(row["g6"], hashlib.sha256(raw).hexdigest())
            selected = {e["g6"]: e for e in report["rewrites"] if e["selected"]}
            with (assembled / "records.jsonl").open("rb") as stream:
                for raw in stream:
                    code = json.loads(raw)["g6"]
                    if code in selected:
                        assert selected[code]["original_record_sha256"] == first[code]
                        assert selected[code]["new_record_sha256"] == hashlib.sha256(raw).hexdigest()
                    else:
                        assert hashlib.sha256(raw).hexdigest() == first[code]
            if label == "rewrite-probe-first":
                self.replay("rewrite-2000-legacy-limit-red", assembled, SAMPLE, "forbidden_limit",
                            profile="sample", limit=10, no_hosts=True)
            # fixture11 uses the B11 Checker(10), load_records, resolve, coverage
            # and unknowns on precisely these 2,000 input codes, with no hosts.
            self.replay(label + "-checker", assembled, SAMPLE, profile="fixture11", no_hosts=True)
        print("PASS rewrite TU/sub, three own-rule red controls, immutable state snapshot, "
              "both 2000-graph priorities; B11-shaped frozen fixture11 coverage", flush=True)

    def rewrite_state_fixture(self, inp, original):
        tool = load_tool()
        state = self.out / "rewrite-state-seed"
        state.mkdir()
        db = sqlite3.connect(state / "state.sqlite")
        db.executescript("PRAGMA journal_mode=WAL; CREATE TABLE accepted(seq INTEGER PRIMARY KEY, "
                         "g6 TEXT UNIQUE,verdict TEXT,hash TEXT,dep TEXT,origin TEXT); "
                         "CREATE TABLE blobs(hash TEXT PRIMARY KEY,offset INTEGER,size INTEGER);")

        def append(record):
            raw = encode(record)
            hashed = hashlib.sha256(raw).hexdigest()
            with (state / "certificates.jsonl").open("ab") as stream:
                offset = stream.tell()
                stream.write(raw)
            db.execute("INSERT INTO blobs VALUES (?,?,?)", (hashed, offset, len(raw)))
            db.execute("INSERT INTO accepted(g6,verdict,hash,dep,origin) VALUES (?,?,?,?,?)",
                       (record["g6"], record["verdict"], hashed, tool.dependency(record), "fixture"))
            db.commit()

        for row in original:
            append(row)
        out = self.out / "rewrite-state-snapshot"
        out.mkdir()
        with tempfile.TemporaryDirectory(dir=self.out) as scratch:
            assembler = tool.Assembler(Path(scratch), inp)
            try:
                assembler.ingest([state])
                assert assembler.spool.seek(0, 2) == 0, "state certificates must never be copied to the spool"
                frozen_prefix = assembler.sources[0]["bytes"]
                # A live writer commits an unrelated record after our snapshot.
                append(G_DIRECT)
                assert (state / "certificates.jsonl").stat().st_size > frozen_prefix
                assembler.rewrite_outside(10)
                assembler.select()
                assembler.emit(out, {"enabled": False, "generated": 0})
            finally:
                assembler.close()
        db.close()
        assert G not in (out / "seed-0-snapshot.jsonl").read_text()
        self.run("rewrite-state-snapshot-structure", [TOOL, "--check", out, "--input", inp])
        self.replay("rewrite-state-snapshot-checker", out, inp, profile="fixture11", no_hosts=True)

    def population(self, state):
        inp = GP11 / "data/B11.g6"
        out = self.out / "population"
        self.run("population-assembly", [TOOL, "--input", inp, "--out", out, "--no-propagate",
                                        "--rewrite-outside-ends", state])
        self.run("population-structure", [TOOL, "--check", out, "--input", inp])
        # Stream actual verdicts and original dependencies. No certificate list
        # or own-map validation, and no proof checker at population scale.
        counts = Counter(row["verdict"] for row in read_rows(out / "records.jsonl"))
        with (out / "UNKNOWN.g6").open() as stream:
            counts["unknown"] = sum(1 for _ in stream)
        report = json.loads((out / "assembly.json").read_text())
        assert counts == report["counts"] and sum(counts.values()) == 448708
        assert not (out / "hosts.jsonl").read_bytes()
        inputs = set(inp.read_text().splitlines())
        claims, deps, outside, endpoint_set = {}, {}, 0, set()
        receipt = report["seeds"][0]
        metadata = out / receipt["snapshot_file"]
        assert sha(metadata) == receipt["snapshot_sha256"]
        for seq, code, verdict, hashed, dep, origin, offset, size in read_rows(metadata):
            claims[code] = verdict
            if code in inputs:
                deps[code] = dep
                if dep is not None and dep not in inputs:
                    outside += 1
                    endpoint_set.add(dep)
        # Independent propagation of the original missing-outside set, using
        # functional dependencies from the saved state, not producer summaries.
        lost = set(endpoint_set)
        while True:
            added = {code for code, dep in deps.items() if dep in lost} - lost
            if not added:
                break
            lost.update(added)
        lost &= inputs
        rewrites = report["rewrites"]
        assert len(rewrites) == outside and all(e["selected"] for e in rewrites)
        assert {e["D"] for e in rewrites} == endpoint_set and not report["rewrite_failures"]
        assert counts["refuted"] == sum(claims[code] == "refuted" for code in deps)
        assert report["rewrite_outside_ends"]["restored_by_verdict"] == {"refuted": len(lost)}
        for name, item in report["outputs"].items():
            assert sha(out / name) == item["sha256"]
        summary = {"snapshot_rows": receipt["snapshot_rows"], "snapshot_utc": receipt["snapshot_utc"],
                   "outside_dependencies": outside, "distinct_endpoints": len(endpoint_set),
                   "rewrites": len(rewrites), "restored_decisions": len(lost),
                   "restored_downstream": len(lost) - outside, "counts": dict(counts)}
        (self.out / "population-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("PASS population " + json.dumps(summary, sort_keys=True), flush=True)

    def raw_run(self, label, inp, rows):
        out = self.out / label
        out.mkdir()
        write_rows(out / "records.jsonl", rows)
        for name in ("unknown-records.jsonl", "UNKNOWN.g6", "hosts.jsonl"):
            (out / name).write_bytes(b"")
        return out

    def sample_priority(self, out, seeds):
        wanted = set(SAMPLE.read_text().splitlines())
        first = {}
        for seed, bundle in enumerate(seeds):
            with gzip.open(bundle / "records.jsonl.gz", "rb") as stream:
                for raw in stream:
                    row = json.loads(raw)
                    if row["g6"] in wanted and row["verdict"] != "unknown":
                        first.setdefault(row["g6"], (seed, hashlib.sha256(raw).hexdigest()))
        actual_sources = [Counter() for _ in seeds]
        with (out / "records.jsonl").open("rb") as stream:
            for raw in stream:
                row = json.loads(raw)
                seed, expected = first[row["g6"]]
                assert hashlib.sha256(raw).hexdigest() == expected, (row["g6"], seed)
                actual_sources[seed][row["verdict"]] += 1
        report = json.loads((out / "assembly.json").read_text())
        for declared, actual in zip(report["by_source_seed"], actual_sources):
            assert declared["embedded"] == actual["embedded"] and declared["refuted"] == actual["refuted"]
        print("PASS byte-for-byte first-decided priority " + out.name, flush=True)

    def positive(self):
        for label, seeds in (("probe-first", [*PROBES, DESKTOP]), ("desktop-first", [DESKTOP, *PROBES])):
            out = self.assemble(label, SAMPLE, seeds, ["--no-propagate"])
            self.sample_priority(out, seeds)
            report = self.replay(label + "-checker", out, SAMPLE)
            # Concrete assignment: four unsupported TU endpoints, two real unresolved inputs.
            # These are counts of the output records, also checked against the frozen report.
            assert report["counts"] == {"embedded": 1979, "refuted": 15, "unknown": 6}
            assert len(json.loads((out / "assembly.json").read_text())["unresolved"]) == 4
        print("PASS positive both priority orders, actual record counts and frozen replay", flush=True)

    def priority(self, replayed_root):
        assert replayed_root is not None, "priority suite requires --replayed-root"
        for label, seeds in (("probe-first", [*PROBES, DESKTOP]), ("desktop-first", [DESKTOP, *PROBES])):
            out = self.assemble(label, SAMPLE, seeds, ["--no-propagate"])
            self.sample_priority(out, seeds)
            previous = replayed_root / label
            report = json.loads((previous / "checked/report.json").read_text())
            assert report["status"] == "ACCEPT" and report["reason"] == "verified"
            assert report["counts"] == self.audit(out, SAMPLE)
            for name in ("records.jsonl", "unknown-records.jsonl", "UNKNOWN.g6", "hosts.jsonl"):
                assert sha(out / name) == sha(previous / name), name
            # Bind the streams to what the frozen runner actually consumed.
            for receipt in report["files"]:
                assert sha(Path(receipt["path"])) == receipt["sha256"]
            print("PASS identical payloads to frozen replay " + label, flush=True)

    def red(self):
        inp = write_input(self.out / "red-input.g6", [G, H])
        original = write_rows(self.out / "red-original.jsonl", [G_DIRECT, H_DIRECT])

        def positive_after(number):
            out = self.assemble(f"red{number}-positive-after", inp, [original])
            report = self.replay(f"red{number}-positive-after-checker", out, inp)
            assert report["counts"] == {"embedded": 0, "refuted": 2, "unknown": 0}

        before = self.assemble("red-positive-before", inp, [original])
        self.replay("red-positive-before-checker", before, inp)
        # One-field change. Detect it even though its certificate no longer matches its verdict.
        disagreeing = copy.deepcopy(G_DIRECT)
        disagreeing["verdict"] = "embedded"
        bad = write_rows(self.out / "disagreeing.jsonl", [disagreeing])
        failed_out = self.out / "red1-contradiction"
        output = self.run("red1-contradiction", [TOOL, "--input", inp, "--out", failed_out, original, bad], "contradiction")
        assert G in output and str(original) + ":1" in output and str(bad) + ":1" in output
        assert not failed_out.exists()
        positive_after(1)

        a = write_rows(self.out / "cycle-a.jsonl", [G_POINTER])
        b = write_rows(self.out / "cycle-b.jsonl", [H_POINTER])
        # Each pointer's actual map is first replayed with its real direct anchor.
        for label, rows in (("cycle-left", [G_POINTER, H_DIRECT]), ("cycle-right", [G_DIRECT, H_POINTER])):
            seed = write_rows(self.out / (label + ".jsonl"), rows)
            out = self.assemble(label, inp, [seed])
            self.replay(label + "-checker", out, inp)
        raw = self.raw_run("red2-raw-cycle", inp, [G_POINTER, H_POINTER])
        report = self.replay("red2-raw-cycle-checker", raw, inp, "pointer_cycle")
        assert report["direct_rejections"] == 0 and report["reason"] == "records_rejected"
        out = self.assemble("red2-cycle-omitted", inp, [a, b])
        report = json.loads((out / "assembly.json").read_text())
        assert report["broken_cycles"] == [{"action": "omitted", "graphs": [G, H]}]
        assert not (out / "records.jsonl").read_bytes()
        self.replay("red2-cycle-omitted-checker", out, inp)
        out = self.assemble("red2-cycle-replaced", inp, [a, b, original])
        report = json.loads((out / "assembly.json").read_text())
        assert report["event_counts"]["broken_cycles"] == 1
        assert report["event_counts"]["replacements"] == 1
        assert {r["g6"]: r for r in read_rows(out / "records.jsonl")} == {G: G_DIRECT, H: H_POINTER}
        self.replay("red2-cycle-replaced-checker", out, inp)
        positive_after(2)

        raw = self.raw_run("red3-raw-missing", inp, [G_POINTER])
        self.replay("red3-raw-missing-checker", raw, inp, "pointer_target_missing")
        out = self.assemble("red3-missing", inp, [a])
        report = json.loads((out / "assembly.json").read_text())
        assert report["unresolved"][0]["reason"] == "dependency_missing"
        assert not (out / "records.jsonl").read_bytes()
        self.replay("red3-missing-checker", out, inp)
        positive_after(3)

        oversized = self.out / "oversized.jsonl"
        base = encode(G_DIRECT).rstrip(b"\n")
        with oversized.open("wb") as stream:
            stream.write(base)
            stream.write(b" " * (MAX_LINE - len(base)))
            stream.write(b"\n")  # Exactly cap + 1, otherwise identical valid JSON.
            stream.write(encode(H_DIRECT))
        raw = self.raw_run("red4-raw-limit", inp, [])
        shutil.copyfile(oversized, raw / "records.jsonl")
        self.replay("red4-raw-limit-checker", raw, inp, "record_limit")
        out = self.assemble("red4-limit", inp, [oversized])
        report = json.loads((out / "assembly.json").read_text())
        assert report["skipped_lines"] == {"over_line_limit": 1}
        assert list(read_rows(out / "records.jsonl")) == [H_DIRECT]
        assert (out / "UNKNOWN.g6").read_text() == G + "\n"
        self.replay("red4-limit-checker", out, inp)
        positive_after(4)
        print("PASS red controls at contradiction, pointer_cycle, pointer_target_missing, record_limit; four real positives after", flush=True)

    def propagation(self):
        tool = load_tool()
        embedded = min((r for r in read_rows(PROBES[0] / "records.jsonl.gz")
                        if r["verdict"] == "embedded" and r["cert"]["type"] == "exact"), key=lambda r: len(encode(r)))
        with tool.Covers(self.index) as covers:
            child, child_map = next(covers.neighbours(embedded["g6"], 1))
            parent, parent_map = next(covers.neighbours(G, 2))
        inp = write_input(self.out / "propagation.g6", [embedded["g6"], child, G, parent])
        seed = write_rows(self.out / "propagation.jsonl", [embedded, G_DIRECT])
        off = self.assemble("propagation-off", inp, [seed], ["--no-propagate"])
        assert self.audit(off, inp) == {"embedded": 1, "refuted": 1, "unknown": 2}
        on = self.assemble("propagation-on", inp, [seed], ["--propagate", "--index", self.index])
        rows = {r["g6"]: r for r in read_rows(on / "records.jsonl")}
        assert rows[child]["cert"] == {"type": "super", "g6": embedded["g6"], "map": child_map}
        assert rows[parent]["cert"] == {"type": "sub", "g6": G, "map": parent_map}
        self.replay("propagation-on-checker", on, inp)

        host_input = write_input(self.out / "host.g6", [child])
        host_pointer = write_rows(self.out / "host-pointer.jsonl", [rows[child]])
        host_seed = write_rows(self.out / "host-seed.jsonl", [embedded])
        host = self.assemble("exact-host", host_input, [host_pointer, host_seed])
        assert list(read_rows(host / "hosts.jsonl")) == [embedded]
        self.replay("exact-host-checker", host, host_input)

        # A refuted support proof cannot be put in hosts even when mathematically sound.
        support_input = write_input(self.out / "refuted-support.g6", [parent])
        support_seed = write_rows(self.out / "refuted-support.jsonl", [rows[parent], G_DIRECT])
        support = self.assemble("refuted-support", support_input, [support_seed])
        assert not (support / "records.jsonl").read_bytes() and not (support / "hosts.jsonl").read_bytes()
        assert json.loads((support / "assembly.json").read_text())["unresolved"][0]["reason"] == "outside_refuted_support"
        self.replay("refuted-support-checker", support, support_input)
        print("PASS cover propagation both verdicts, exact host replay, outside refutation omitted", flush=True)

    def unit(self):
        tool = load_tool()
        assert tool.MAX_LINE == MAX_LINE
        # Check the complete dependency taxonomy, including graph-looking fields
        # inside direct witnesses which are not runner dependencies.
        for kind in ("tree", "null", "real", "null-dag", "real-dag"):
            assert tool.dependency({"verdict": "refuted", "cert": {"type": kind, "g6": H}}) is None
        assert tool.dependency(G_DIRECT) is None
        assert tool.dependency(G_POINTER) == H
        assert tool.dependency(H_POINTER) == G
        indexed = {"g6": "C~", "verdict": "refuted", "cert": {"type": "sub", "g6": "C~", "map": [0, 1, 2, 3], "index": 0}}
        assert tool.dependency(indexed) is None
        inp = write_input(self.out / "indexed.g6", ["C~"])
        seed = write_rows(self.out / "indexed.jsonl", [indexed])
        out = self.assemble("indexed", inp, [seed])
        self.replay("indexed-checker", out, inp)

        codes = (GP11 / "data/B11.g6").read_text().splitlines()[:4]
        a, b, c, d = codes
        inp = write_input(self.out / "unit.g6", codes)

        def ptr(source, target, verdict="embedded"):
            return {"g6": source, "verdict": verdict, "cert": {"type": "super" if verdict == "embedded" else "sub", "g6": target, "map": []}}

        def direct(code, verdict="embedded"):
            return {"g6": code, "verdict": verdict, "cert": {"type": "exact" if verdict == "embedded" else "tree"}}

        # Escape requires changing an alternative outside the original a-b cycle.
        seed = write_rows(self.out / "escape.jsonl", [ptr(a, b), ptr(b, a), ptr(c, a), direct(d), ptr(a, c), ptr(c, d)])
        out = self.assemble("escape", inp, [seed])
        rows = {r["g6"]: r for r in read_rows(out / "records.jsonl")}
        assert rows == {a: ptr(a, c), b: ptr(b, a), c: ptr(c, d), d: direct(d)}
        assert json.loads((out / "assembly.json").read_text())["event_counts"]["replacements"] == 2
        long_codes = (GP11 / "data/B11.g6").read_text().splitlines()[:4096]
        long_input = write_input(self.out / "long-escape.g6", long_codes)
        long_seed = write_rows(self.out / "long-escape.jsonl", [
            ptr(long_codes[0], long_codes[1]), ptr(long_codes[1], long_codes[0]),
            *(ptr(long_codes[i], long_codes[0]) for i in range(2, len(long_codes) - 1)),
            direct(long_codes[-1]), ptr(long_codes[0], long_codes[2]),
            *(ptr(long_codes[i], long_codes[i + 1]) for i in range(2, len(long_codes) - 1))])
        escaped = self.assemble("long-escape", long_input, [long_seed])
        assert self.audit(escaped, long_input)["embedded"] == len(long_codes)
        assert json.loads((escaped / "assembly.json").read_text())["event_counts"]["replacements"] == len(long_codes) - 2
        # An independent exhaustive simple-path oracle on small multigraphs checks
        # that cyclic alternatives do not lose any graph that can reach a root.
        rng = random.Random(11011)
        oracle_codes = long_codes[:8]
        oracle_input = write_input(self.out / "oracle.g6", oracle_codes)
        for case in range(64):
            options = [[None if rng.randrange(5) == 0 else rng.randrange(8)
                        for _ in range(rng.randrange(1, 4))] for _ in oracle_codes]

            def reaches_root(node, visited):
                return any(target is None or (target not in visited and reaches_root(target, visited | {target}))
                           for target in options[node])

            expected = {oracle_codes[i] for i in range(8) if reaches_root(i, {i})}
            oracle_seed = write_rows(self.out / "oracle-seed.jsonl", (
                direct(oracle_codes[i]) if target is None else ptr(oracle_codes[i], oracle_codes[target])
                for i, targets in enumerate(options) for target in targets))
            with tempfile.TemporaryDirectory(prefix="oracle-", dir=self.out) as temp:
                scratch = Path(temp)
                assembled = scratch / "out"
                assembled.mkdir()
                assembler = tool.Assembler(scratch, oracle_input)
                try:
                    assembler.ingest([oracle_seed])
                    assembler.select()
                    assembler.emit(assembled, {"enabled": False, "generated": 0})
                finally:
                    assembler.close()
                tool.structural_check(assembled, oracle_input)
                assert {r["g6"] for r in read_rows(assembled / "records.jsonl")} == expected, (case, options)
        print("PASS 64 deterministic alternative-graph cases against exhaustive simple-path reachability", flush=True)
        # Alternatives needing a wrong-verdict target are unusable. Later records
        # with the same verdict remain eligible, in exact file order.
        seed = write_rows(self.out / "alternatives.jsonl", [ptr(a, b), direct(b, "refuted"),
                          ptr(a, c), direct(c), direct(a), direct(d)])
        out = self.assemble("alternatives", inp, [seed])
        rows = {r["g6"]: r for r in read_rows(out / "records.jsonl")}
        assert rows[a] == ptr(a, c)
        assert json.loads((out / "assembly.json").read_text())["replacements"][0]["reason"] == "dependency_verdict"

        # Input-external conflicts are still fatal, before eligibility filtering.
        outside = write_rows(self.out / "outside-conflict.jsonl", [G_DIRECT, {**G_DIRECT, "verdict": "embedded"}])
        self.run("outside-conflict", [TOOL, "--input", inp, "--out", self.out / "outside-conflict", outside], "contradiction")
        # An outside pointer may fall back only to an exact host, and unused hosts vanish.
        host_input = write_input(self.out / "unit-host.g6", [a])
        seed = write_rows(self.out / "unit-host.jsonl", [ptr(a, b), ptr(b, c), direct(b), direct(c)])
        out = self.assemble("unit-host", host_input, [seed])
        assert list(read_rows(out / "hosts.jsonl")) == [direct(b)]
        assert json.loads((out / "assembly.json").read_text())["skipped_lines"] == {"outside_non_exact": 1}

        # Recovery after malformed and oversized physical lines, gzip receipts,
        # exact-cap boundary, unknown never winning, and a final unterminated line.
        malformed = self.out / "framing.jsonl.gz"
        exact = encode(direct(a)).rstrip(b"\n")
        with gzip.open(malformed, "wb") as stream:
            stream.write(b'{"g6":"x","g6":"y","verdict":"embedded","cert":{}}\n')
            stream.write(b'{"g6":"x","verdict":"embedded","cert":{"type":"exact","x":NaN}}\n')
            stream.write(b"{broken}\n\n")
            stream.write(encode({"g6": a, "verdict": "unknown", "cert": {"reason": "fixture", "budget": {}}}))
            stream.write(b" " * (MAX_LINE * 2) + b"\n")
            stream.write(exact + b" " * (MAX_LINE - len(exact) - 1) + b"\n")
            stream.write(encode(direct(b)))
            stream.write(encode(direct(c)).rstrip(b"\n"))
        out = self.assemble("framing", inp, [malformed])
        report = json.loads((out / "assembly.json").read_text())
        assert report["skipped_lines"] == {"duplicate_json_key": 1, "json_constant": 1, "invalid_json": 1,
                                           "line_format": 2, "not_decided": 1, "over_line_limit": 1}
        assert self.audit(out, inp) == {"embedded": 2, "refuted": 0, "unknown": 2}
        with (out / "records.jsonl").open("rb") as stream:
            assert len(stream.readline()) == MAX_LINE

        # Structural red mutations are judged from bytes, not assembly.json counts.
        clean_seed = write_rows(self.out / "structural.jsonl", [direct(a), ptr(b, a), direct(c), direct(d)])
        clean = self.assemble("structural", inp, [clean_seed])
        cases = {
            "duplicate": ([direct(a), direct(a), direct(c), direct(d)], "duplicate_record"),
            "missing": ([ptr(a, G), direct(b), direct(c), direct(d)], "dependency_missing"),
            "wrong-verdict": ([ptr(a, b), direct(b, "refuted"), direct(c), direct(d)], "dependency_verdict"),
            "cycle": ([ptr(a, b), ptr(b, a), direct(c), direct(d)], "dependency_cycle"),
            "order": ([direct(b), direct(a), direct(c), direct(d)], "record_input_order"),
        }
        for name, (rows, rule) in cases.items():
            mutated = self.out / ("structural-" + name)
            shutil.copytree(clean, mutated)
            write_rows(mutated / "records.jsonl", rows)
            self.run("structural-" + name, [TOOL, "--check", mutated, "--input", inp], rule)
            self.run("structural-" + name + "-after", [TOOL, "--check", clean, "--input", inp])
        for name in ("UNKNOWN.g6", "unknown-records.jsonl"):
            mutated = self.out / ("structural-" + name)
            shutil.copytree(clean, mutated)
            (mutated / name).write_bytes((a + "\n").encode() if name == "UNKNOWN.g6" else
                                        encode({"g6": a, "verdict": "unknown", "cert": {"reason": "extra", "budget": {}}}))
            self.run("structural-unknown-" + name, [TOOL, "--check", mutated, "--input", inp], "unknown_exactness")
        mutated = self.out / "structural-cap"
        shutil.copytree(clean, mutated)
        with (mutated / "records.jsonl").open("ab") as stream:
            stream.write(b" " * MAX_LINE + b"\n")
        self.run("structural-cap", [TOOL, "--check", mutated, "--input", inp], "over_line_limit")
        self.run("structural-final-after", [TOOL, "--check", clean, "--input", inp])
        print("PASS unit taxonomy, priority, escape path, outside support, framing, structural mutations", flush=True)

    def scale(self):
        # Real graph strings, synthetic verdicts/dependencies, no proof bodies.
        # Two long chains stress stack safety. A missing tail exercises UNKNOWN.
        inp = self.out / "scale-input.g6"
        shutil.copyfile(GP11 / "data/B11.g6", inp)
        seed = self.out / "scale-seed.jsonl"
        with inp.open() as source, seed.open("wb") as target:
            previous = None
            count = 0
            for i, line in enumerate(source):
                code = line.rstrip("\n")
                count += 1
                if i >= 448708 - 4487:
                    continue
                verdict = "embedded" if i < 224354 else "refuted"
                if i in (0, 224354):
                    cert = {"type": "exact" if verdict == "embedded" else "tree"}
                else:
                    cert = {"type": "super" if verdict == "embedded" else "sub", "g6": previous, "map": []}
                target.write(encode({"g6": code, "verdict": verdict, "cert": cert}))
                previous = code
        assert count == 448708
        out = self.out / "scale"
        self.run("scale-assembly", [TOOL, "--input", inp, "--out", out, "--no-propagate", seed])
        self.run("scale-check", [TOOL, "--check", out, "--input", inp])
        # Stream the independent scale audit too; no list of fake certificate objects.
        counts = Counter(row["verdict"] for row in read_rows(out / "records.jsonl"))
        with (out / "UNKNOWN.g6").open() as stream:
            counts["unknown"] = sum(1 for _ in stream)
        assert counts == {"embedded": 224354, "refuted": 219867, "unknown": 4487}
        report = json.loads((out / "assembly.json").read_text())
        assert report["counts"] == counts
        for name, receipt in report["outputs"].items():
            assert sha(out / name) == receipt["sha256"]
        print("PASS scale 448708 graphs; synthetic certificates were not sent to the checker", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=Path("/tmp/gp11-index"))
    parser.add_argument("--suite", choices=("unit", "positive", "red", "propagation", "scale", "priority", "rewrite", "population", "all"), default="all")
    parser.add_argument("--state", type=Path, default=Path("/tmp/gp11-population-cheap-state"))
    parser.add_argument("--replayed-root", type=Path, help="existing positive-suite directory for byte-equivalence tests")
    args = parser.parse_args()
    assert Path(sys.executable) == PYTHON, "use the pinned interpreter"
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    tests = Tests(args.output, args.index)
    for suite in ("unit", "red", "propagation", "positive", "scale", "rewrite") if args.suite == "all" else (args.suite,):
        if suite == "priority":
            tests.priority(args.replayed_root)
        elif suite == "population":
            tests.population(args.state)
        else:
            getattr(tests, suite)()
    print(f"PASS suite={args.suite} commands={len(tests.commands)} results={args.output / 'results.json'}", flush=True)


if __name__ == "__main__":
    main()
