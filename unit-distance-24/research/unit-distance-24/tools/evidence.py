#!/usr/bin/env python3
"""Bind worker metadata to checked bytes, without changing the reviewed chain checker."""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

from functools import lru_cache

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "research/unit-distance-22/enum/verify-chain-u24.py"
SCHEMA = "u24-structure-v1"
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RETAIN_SUFFIXES = (".g6", ".keep.g6", ".certs.jsonl", ".UNKNOWN.g6", ".manifest.json", ".prune.manifest.json")


@lru_cache(None)
def chain_checker():
    spec = importlib.util.spec_from_file_location("u24_chain_evidence", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def requirements(config, summary, reach):
    """Derive obligations before inspecting any optional summary fields."""
    for key in ("reach", "prune", "verify_stages"):
        if type(config.get(key)) is not bool:
            raise ValueError(f"RECORDS: configuration {key} must be a boolean")
    if config["prune"] and (type(config.get("prune_from")) is not int or config["prune_from"] < 0):
        raise ValueError("RECORDS: configuration prune_from must be a nonnegative integer")
    problems = []
    derived = chain_checker().derive(config, summary, reach, problems)
    if problems:
        raise ValueError("RECORDS: " + "; ".join(problems))
    entries = {(e["n"], e["m"]): e for e in summary["levels"]}
    for n, m in derived["required"]:
        entry = entries[n, m]
        kind = "seed" if n == derived["seed_n"] else "augmentation"
        if entry.get("kind") != kind:
            raise ValueError(f"RECORDS: {n}-{m}: required {kind} record is missing")
        need = (["reach"] if config.get("reach") else [])
        if derived["prune_from"] is not None and n >= derived["prune_from"]:
            need.append("prune")
        if config.get("verify_stages"):
            need.append("verify")
        for name in need:
            if not isinstance(entry.get(name), dict) or (name == "prune" and not isinstance(entry[name].get("counts"), dict)):
                raise ValueError(f"RECORDS: {n}-{m}: required {name} record is missing")
        if "verify" in need:
            stage = "keep" if "prune" in need else "reach" if "reach" in need else "full"
            if entry["verify"].get("stage_kind") != stage:
                raise ValueError(f"RECORDS: {n}-{m}: verification must read {stage}")
        if "reach" in need:
            parameter_equal(f"{n}-{m} reach k", entry["reach"].get("k"), derived["table"][n][m])
        if "prune" in need:
            source = entry["prune"].get("source")
            # Summaries preserve absolute producer paths even after the bundle is moved.
            # Its cell and input stage, like replay stage_fields(), must still be derived.
            name = Path(source).name if isinstance(source, str) else source
            parameter_equal(f"{n}-{m} prune source", name, f"{n}-{m}" + (".reach.g6" if "reach" in need else ".g6"))
        if kind == "augmentation":
            if "reach_k" in entry:
                parameter_equal(f"{n}-{m} reach_k", entry["reach_k"],
                                derived["table"][n][m] if config["reach"] else None)
            if "parent_edge_counts" in entry:
                parameter_equal(f"{n}-{m} parent_edge_counts", entry["parent_edge_counts"], derived["allowed"][n, m])
            if "parent_sources" in entry:
                pn = n - 1
                stage = ("keep" if derived["prune_from"] is not None and pn >= derived["prune_from"]
                         else "reach" if config["reach"] else "full")
                if config.get("slice") and pn == config["slice"][0]:
                    stage += "+slice"
                sources = [{"level": [pn, pm], "kind": stage} for pm in derived["allowed"][n, m]]
                recorded = [{k: s.get(k) for k in ("level", "kind")} for s in entry["parent_sources"]]
                parameter_equal(f"{n}-{m} parent stages", recorded, sources)
    return derived


def parameter_equal(where, claimed, derived):
    # JSON equality also distinguishes booleans/floats from integer parameters.
    if json.dumps(claimed, sort_keys=True) != json.dumps(derived, sort_keys=True):
        raise ValueError(f"PARAMETERS: {where}: metadata {claimed!r} != derived {derived!r}")


def load(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def count_equal(where, claimed, actual):
    if type(claimed) is not int or claimed < 0 or claimed != actual:
        raise ValueError(f"COUNTS: {where}: metadata {claimed!r} != checked files {actual}")


class Files:
    def __init__(self, run):
        self.run = run
        self.rows = {}

    def read(self, name):
        if name not in self.rows:
            path = self.run / name
            h, size, count = hashlib.sha256(), 0, 0
            with path.open("rb") as stream:
                for raw in stream:
                    h.update(raw)
                    size += len(raw)
                    count += 1
                    if not raw.endswith(b"\n"):
                        raise ValueError(f"COUNTS: {name}: missing final newline")
            self.rows[name] = {"sha256": h.hexdigest(), "bytes": size, "records": count}
        return self.rows[name]

    def count(self, name):
        return self.read(name)["records"]


def hash_records(run, result, files=None):
    files = files or Files(run)
    config = load(run / "run-config.json")
    tn = config["target"][0]
    level = config["slice"][0]
    names = sorted(p.name for p in run.glob("*.g6") if ".slice-" not in p.name
                   and (int(p.name.split("-")[0]) <= level or int(p.name.split("-")[0]) >= tn - 2))
    stored = load(result / "hashes.json")
    if stored["slice"] != config["slice"]:
        raise ValueError("RESULT BINDING: hashes.json names another slice")
    if set(names) != set(stored["files"]):
        raise ValueError("RESULT BINDING: hashes.json file set differs from the runbook selection")
    h = hashlib.sha256()
    for name in names:
        actual = files.read(name)
        count_equal(f"hashes.json {name} records", stored["files"][name].get("records"), actual["records"])
        if stored["files"][name].get("sha256") != actual["sha256"]:
            raise ValueError(f"RESULT BINDING: hashes.json {name} sha256 differs from checked file")
        h.update(f"{name} {actual['sha256']}\n".encode())
    return f"{len(names)} files, sha256 {h.hexdigest()}"


def retained_files(run, result):
    """The runbook's result-copy selection, including its verification manifests."""
    config, reach = load(run / "run-config.json"), load(run / "reach.json")
    tn, tm = config["target"]
    names = {"run-summary.json", "run-config.json", "reach.json"}
    cells = [(tn, tm), *((tn - 1, int(m)) for m in reach["table"][str(tn - 1)])]
    for n, m in cells:
        for suffix in RETAIN_SUFFIXES:
            name = f"{n}-{m}{suffix}"
            path = run / name
            if path.is_file() and path.stat().st_size < 4_000_000:
                names.add(name)
    names.update("verify/" + p.name for p in run.glob("*.verify.manifest.json"))
    expected = names | {"hashes.json", "counts.json"}
    present = {p.relative_to(result).as_posix() for p in result.rglob("*")
               if p.is_file() and p.relative_to(result).parts[0] not in ("replay", "history")}
    if expected != present:
        raise ValueError(f"RESULT BINDING: retained file set differs: missing {sorted(expected - present)}, extra {sorted(present - expected)}")
    for name in sorted(names):
        source = run / (Path(name).name if name.startswith("verify/") else name)
        if sha(source) != sha(result / name):
            raise ValueError(f"RESULT BINDING: retained {name} differs from checked file")
    counts = [[e["n"], e["m"], e.get("children"), (e.get("prune") or {}).get("counts")]
              for e in load(run / "run-summary.json")["levels"]]
    if json.dumps(load(result / "counts.json"), sort_keys=True) != json.dumps(counts, sort_keys=True):
        raise ValueError("COUNTS: counts.json differs from the checked run-summary.json")
    return {name: sha(result / name) for name in sorted(expected)}


def prune_counts(run, cell, files, rule, prefix_counts=None, source=None):
    count = Counter()
    witness = {"triangles": "tri", "rhombus": "rhombus"}.get(rule)
    with (run / f"{cell}.certs.jsonl").open() as stream:
        for raw in stream:
            record = json.loads(raw)
            verdict = record["verdict"]
            if verdict not in ("tu", "refuted", "embedded", "unknown"):
                raise ValueError(f"COUNTS: {cell}: unknown certificate verdict {verdict!r}")
            count[verdict] += 1
            if witness and witness in (record.get("witness") or {}):
                count[f"{witness}_{verdict}"] += 1
    total = files.count(f"{cell}.certs.jsonl")
    source = source or (f"{cell}.reach.g6" if (run / f"{cell}.reach.g6").exists() else f"{cell}.g6")
    count_equal(f"{cell} certificate records", total, files.count(source))
    count_equal(f"{cell} keep records", files.count(f"{cell}.keep.g6"), count["embedded"] + count["unknown"])
    count_equal(f"{cell} UNKNOWN records", files.count(f"{cell}.UNKNOWN.g6"), count["unknown"])
    native_tu = count["tu"] - count[f"{witness}_tu"] if witness else count["tu"]
    native_refuted = count["refuted"] - count[f"{witness}_refuted"] if witness else count["refuted"]
    out = {"input": total, "tu": native_tu, "survivors": total - native_tu,
           "embedded": count["embedded"], "refuted": native_refuted, "unknown": count["unknown"],
           "kept": files.count(f"{cell}.keep.g6"), "pruned": count["tu"] + count["refuted"]}
    if witness:
        out.update({f"{witness}_tu": count[f"{witness}_tu"], f"{witness}_refuted": count[f"{witness}_refuted"],
                    f"{witness}_survivors": total - count["tu"] - count[f"{witness}_refuted"]})
        # Silent passes leave no distinguishing certificate. Their evidence is the prover's
        # per-part diagnostics, preserved by the inventory and counted before deleting them.
        paths = sorted((run / "_prune" / cell).glob(f"{rule}-*.stderr"))
        fields = ("budget", "verify_fail", "lift_fail", "internal") if rule == "triangles" else ("certificate_failures",)
        silent, graphs = 0, 0
        for path in paths:
            lines = path.read_text().strip().splitlines()
            if not lines:
                raise ValueError(f"COUNTS: {cell}: missing prover diagnostic counts")
            if lines[-1].startswith("{"):
                stats = json.loads(lines[-1])
                if len(stats) == 1 and isinstance(next(iter(stats.values())), dict):
                    stats = next(iter(stats.values()))
            else:
                stats = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", lines[-1])}
            if any(type(stats.get(k)) is not int or stats[k] < 0 for k in (*fields, "graphs")):
                raise ValueError(f"COUNTS: {cell}: missing prover diagnostic counts")
            silent += sum(stats[k] for k in fields)
            graphs += stats["graphs"]
            files.read(path.relative_to(run).as_posix())
        if not paths and prefix_counts is not None:
            silent = prefix_counts[f"{witness}_silent_passes"]
        else:
            count_equal(f"{cell} prover diagnostic graphs", graphs, out["survivors"])
        out[f"{witness}_silent_passes"] = silent
    return out


def structural_entry(run, entry, files, preserve, archive=None):
    cell = f"{entry['n']}-{entry['m']}"
    required = ("parent_edge_counts", "reach_k", "parent_sources", "parents", "shards")
    try:
        manifest_path = run / f"{cell}.manifest.json"
        manifest = load(manifest_path) if archive is None else archive[f"{cell}.manifest.json"]
        count_equal(f"{cell} manifest children", manifest.get("children_written"), files.count(f"{cell}.g6"))
        if manifest.get("children_file_sha256") != files.read(f"{cell}.g6")["sha256"]:
            raise ValueError("aggregate children hash differs")
        sources = []
        for s in manifest["parent_sources"]:
            if not isinstance(s["level"], list) or len(s["level"]) != 2 or any(type(v) is not int or v < 0 for v in s["level"]):
                raise ValueError("parent source level is not a pair of nonnegative integers")
            name = Path(s["file"]).name
            count = files.count(name)
            count_equal(f"{cell} manifest parent {name}", s["records"], count)
            if files.read(name)["sha256"] != s["sha256"]:
                raise ValueError("parent source hash differs")
            sources.append({"level": s["level"], "kind": s["kind"], "records": count})
        parents = files.count(f"_parents/{cell}.g6")
        if manifest.get("inputs_sha256", {}).get(manifest.get("parent_file")) != files.read(f"_parents/{cell}.g6")["sha256"]:
            raise ValueError("aggregate parent hash differs")
        count_equal(f"{cell} parent sources", sum(s["records"] for s in sources), parents)
        if manifest["parent_range"] != [0, parents] or any(type(v) is not int for v in manifest["parent_range"]):
            raise ValueError("aggregate parent range differs")
        shards, manifests = [], [manifest_path]
        paths = ((run / "shards" / cell).glob("*.manifest.json") if archive is None else
                 (run / name for name in archive if re.fullmatch(rf"shards/{cell}/[^/]+\.manifest\.json", name)))
        for path in paths:
            sm = load(path) if archive is None else archive[path.relative_to(run).as_posix()]
            span = sm.get("parent_range")
            if (not isinstance(span, list) or len(span) != 2 or any(type(v) is not int or v < 0 for v in span)
                    or span[0] > span[1]):
                raise ValueError("shard range is not an ordered pair of nonnegative integers")
            name = path.with_suffix("").with_suffix(".g6").relative_to(run).as_posix()
            children = files.count(name)
            count_equal(f"{cell} shard {Path(name).name} children", sm["children_written"], children)
            if sm["children_file_sha256"] != files.read(name)["sha256"]:
                raise ValueError("shard children hash differs")
            shards.append({"range": sm["parent_range"], "children": children})
            manifests.append(path)
        shards.sort(key=lambda s: s["range"])
        if (not shards or shards[0]["range"][0] != 0 or shards[-1]["range"][1] != parents
                or any(a["range"][1] != b["range"][0] for a, b in zip(shards, shards[1:]))):
            raise ValueError("shards do not tile parents")
        count_equal(f"{cell} shard children total", sum(s["children"] for s in shards), files.count(f"{cell}.g6"))
        actual = {"parent_edge_counts": [s["level"][1] for s in sources], "reach_k": manifest.get("reach", {}).get("k"),
                  "parent_sources": sources, "parents": parents, "shards": shards}
        if "parents" in entry:
            count_equal(f"{cell} parents", entry["parents"], parents)
        for claimed, source in zip(entry.get("parent_sources", []), sources):
            count_equal(f"{cell} parent source {source['level']} records", claimed.get("records"), source["records"])
        for claimed, shard in zip(entry.get("shards", []), shards):
            count_equal(f"{cell} shard {shard['range']} children", claimed.get("children"), shard["children"])
        for key in required:
            if key not in entry and entry.get("resumed"):
                continue
            claimed = entry.get(key)
            if key == "shards" and isinstance(claimed, list):
                claimed = [{"range": s["range"], "children": s["children"]} for s in claimed]
            if json.dumps(claimed, sort_keys=True) != json.dumps(actual[key], sort_keys=True):
                raise ValueError(f"COUNTS: {cell} {key}: metadata differs from checked files")
        if archive is None:
            for p in manifests:
                preserve[p.relative_to(run).as_posix()] = {"sha256": sha(p), "text": p.read_text()}
        return dict(entry, **actual, resumed=False)
    except (OSError, KeyError, TypeError, ValueError) as error:
        if entry.get("resumed"):
            raise ValueError(f"STRUCTURE: {cell}: cannot export resumed parent sources, parent count and shards: {error}") from error
        raise


def checked_prune(run, entry, files, rule, previous=None):
    cell = f"{entry['n']}-{entry['m']}"
    counts = prune_counts(run, cell, files, rule, previous)
    if set(entry["prune"]["counts"]) != set(counts):
        raise ValueError(f"COUNTS: {cell} prune count keys differ from checked files")
    for key, value in counts.items():
        count_equal(f"{cell} prune {key}", entry["prune"]["counts"][key], value)
    return counts


def require_structure(summary, exported):
    entries = {(e["n"], e["m"]): e for e in exported["levels"]}
    for e in summary["levels"]:
        if e["kind"] != "augmentation":
            continue
        cell = (e["n"], e["m"])
        found = entries.get(cell, {})
        if found.get("resumed") or any(k not in found for k in
                ("parent_sources", "parent_edge_counts", "reach_k", "parents", "shards")):
            raise ValueError(f"STRUCTURE: {cell[0]}-{cell[1]}: resumed cell has no exported parent sources, parent count and shards")


def reconcile(run, result, first=10, prefix=None):
    files = Files(run)
    summary = load(run / "run-summary.json")
    config = load(run / "run-config.json")
    requirements(config, summary, load(run / "reach.json"))
    digest = hash_records(run, result, files)
    retained = retained_files(run, result)
    target = "-".join(map(str, config["target"]))
    missing = [target + suffix for suffix in (".g6", ".keep.g6", ".certs.jsonl", ".UNKNOWN.g6")
               if target + suffix not in retained]
    if missing:
        raise ValueError(f"RESULT BINDING: target files required for receipt measurements are not retained: {missing}")
    normalized = copy.deepcopy(summary)
    rule = "triangles" if config.get("triangles") else "rhombus" if config.get("rhombus") else None
    prefix_entries = {(e["n"], e["m"]): e for e in prefix["summary"]["levels"]} if prefix else {}
    if prefix and (prefix.get("schema") != SCHEMA or prefix.get("result") != "OK"):
        raise ValueError("STRUCTURE: prefix receipt did not pass")
    manifests = {name: row for name, row in (prefix or {}).get("manifests", {}).items()
                 if int(Path(name).name.split("-")[0]) < first}
    recovered, counts_by_cell = [], {}
    for entry in normalized["levels"]:
        n, m = entry["n"], entry["m"]
        cell = f"{n}-{m}"
        inherited = prefix_entries.get((n, m)) if n < first else None
        children = files.count(f"{cell}.g6")
        count_equal(f"{cell} children", entry.get("children"), children)
        if "reach" in entry:
            counts = {"input": children, "kept": files.count(f"{cell}.reach.g6")}
            counts["dropped"] = counts["input"] - counts["kept"]
            for key, value in counts.items():
                if key in entry["reach"] or not entry["reach"].get("resumed") or key == "kept":
                    count_equal(f"{cell} reach {key}", entry["reach"].get(key), value)
        if "prune" in entry:
            previous = (inherited.get("prune") or {}).get("counts") if inherited else None
            counts_by_cell[cell] = checked_prune(run, entry, files, rule, previous)
        if "verify" in entry:
            kind = entry["verify"]["stage_kind"]
            stage = f"{cell}" + ({"full": ".g6", "reach": ".reach.g6", "keep": ".keep.g6"}[kind])
            count_equal(f"{cell} verify records", entry["verify"].get("records"), files.count(stage))
            if "parts" in entry["verify"]:
                count_equal(f"{cell} verify parts", entry["verify"]["parts"], len(load(run / f"{cell}.verify.manifest.json")["parts"]))
        if entry["kind"] == "augmentation":
            if n < first:
                if inherited is None:
                    raise ValueError(f"STRUCTURE: {cell}: missing whole-checked prefix receipt")
                for key in ("parent_edge_counts", "reach_k", "parent_sources", "parents", "shards"):
                    if key in entry and entry[key] != inherited[key]:
                        raise ValueError(f"STRUCTURE: {cell}: prefix {key} differs from whole-checked receipt")
                    entry[key] = inherited[key]
                entry["resumed"] = False
            else:
                if entry.get("resumed"):
                    recovered.append(cell)
                entry.update(structural_entry(run, entry, files, manifests))
    require_structure(summary, normalized)
    target_files = {suffix: files.read(target + suffix) for suffix in
                    (".g6", ".reach.g6", ".keep.g6", ".certs.jsonl", ".UNKNOWN.g6")}
    return {"schema": SCHEMA, "target": config["target"], "slice": config["slice"], "result": "OK",
            "run_summary_sha256": sha(run / "run-summary.json"), "files_digest": digest,
            "target_files": target_files, "target_counts": counts_by_cell[target],
            "file_counts": files.rows, "retained": retained, "summary": normalized,
            "recovered_cells": recovered, "manifests": manifests}


def replay_fingerprint(run, settings, lo, hi):
    h = hashlib.sha256(settings.encode())
    for tool in ("enum2.py", "replay-398.py"):
        h.update(bytes.fromhex(sha(CHECKER.parent.parent / "enum2" / tool)))
    for path in sorted(run.glob("*.manifest.json")):
        match = re.fullmatch(r"(\d+)-(\d+)\.manifest\.json", path.name)
        if match and lo <= int(match[1]) <= hi:
            info = load(path)
            parent = info.get("inputs_sha256", {}).get(info.get("parent_file"))
            h.update(f"{path.name} {info.get('children_file_sha256')} {parent}\n".encode())
    return h.hexdigest()


@lru_cache(None)
def fleet_judge():
    """Reuse the fleet's scope checks and its pinned sample_indices, without running a replay."""
    path = ROOT / "research/unit-distance-23/tools/target_check.py"
    spec = importlib.util.spec_from_file_location("u24_fleet_scope", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay_scope(result, structure, sm, fp, config, reach):
    d = requirements(config, structure["summary"], reach)
    entries = {(e["n"], e["m"]): e for e in structure["summary"]["levels"]}
    lo = d["seed_n"] + 1 if fp["mode"] == "full" else structure["slice"][0] + 1
    expected = {f"{n}-{m}" for n, m in d["required"] if lo <= n <= d["target"][0]
                and entries[n, m]["parents"] > 0}
    rows = sm.get("per_cell")
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("G4: per_cell must be a list of replay records")
    names = [r.get("cell") for r in rows]
    if any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise ValueError("G4: replay cells must be distinct cell names")
    if set(names) != expected:
        raise ValueError(f"G4: replay cells differ: expected {len(expected)} populated cells, got {len(names)}; "
                         f"missing {sorted(expected - set(names))[:3]}, extra {sorted(set(names) - expected)[:3]}")
    judge = fleet_judge()
    ev = {"parents": {}, "shards": {}, "shard_children": {}, "sources": {}, "counts": {}, "children": {}}
    for cell in d["required"]:
        e = entries[cell]
        ev["counts"][cell] = (e["children"], (e.get("reach") or {}).get("kept"),
                               (e.get("prune") or {}).get("counts", {}).get("kept"))
        ev["children"][cell] = e["children"]
        if cell[0] == d["seed_n"]:
            continue
        ev["parents"][cell] = e["parents"]
        ev["shards"][cell] = judge.ranges_of(e["shards"])
        ev["shard_children"][cell] = tuple(s["children"] for s in sorted(e["shards"], key=lambda s: s["range"]))
        ev["sources"][cell] = {(tuple(s["level"]), s["kind"]): s["records"] for s in e["parent_sources"]}
    # The old judge takes its run identity and red.json location from a canonical result path.
    # Supply that small view so arbitrary staging directory names do not change replay identity.
    with tempfile.TemporaryDirectory(prefix="u24-g4-scope-") as tmp:
        n, m = structure["target"]
        level, index, count = structure["slice"]
        view = Path(tmp) / f"{n}-{m}-L{level}-tri-pf74" / f"s{index}of{count}"
        (view / "replay").mkdir(parents=True)
        if (result / "replay/red.json").exists():
            (view / "replay/red.json").write_bytes((result / "replay/red.json").read_bytes())
        c = {"dir": view, "rep": sm, "replay_mode": fp["mode"], "audit": ev,
             "slice": index, "reach_table": reach["table"],
             "seeds10": [f"{a}-{b}" for a, b in d["required"] if a == d["seed_n"]]}
        saved = judge.REPLAY_PINS
        try:
            judge.REPLAY_PINS = dict(saved, **{k: sm[k] for k in
                                    ("fraction", "seed", "min_per_shard", "whole_max", "max_per_shard")})
            why = judge.replay_scope(c, ev, n)
        finally:
            judge.REPLAY_PINS = saved
    if why:
        raise ValueError("G4 SCOPE: " + "; ".join(why))


def replay_mode(fp, whole, prefix):
    """The checked scope chooses the mode; a recorded mode cannot reduce that scope.

    prefix is the caller's accepted whole-check bundle (current audit or a marker
    from this implementation), never a prefix selected by the replay being checked.
    """
    if whole:
        if fp.get("mode") != "full":
            raise ValueError("G4: whole check requires a full-mode replay")
    else:
        if fp.get("mode") != "slice":
            raise ValueError("G4: prefix-bound check requires a slice-mode replay")
        prior = (prefix or {}).get("g4", {})
        if ((prefix or {}).get("result") != "OK" or prior.get("mode") != "full"
                or prior.get("result") != "PASS"):
            raise ValueError("G4: slice-mode replay requires a passed full-mode prefix replay")
        digest = fp.get("prefix_fingerprint")
        if (not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest)
                or digest != prior.get("prefix_fingerprint")):
            raise ValueError("G4: slice-mode prefix fingerprint differs from passed full replay")


def g4(run, result, structure, *, whole=True, prefix=None):
    path = result / "replay/summary.json"
    if not path.is_file():
        raise ValueError("G4: replay/summary.json is required")
    sm, fp = load(path), load(result / "replay/fingerprint.json")
    if sm.get("fraction") != 0.002:
        raise ValueError("G4: replay summary fraction must be 0.002")
    if type(sm.get("mismatching_parents")) is not int or sm["mismatching_parents"] != 0:
        raise ValueError("G4: replay summary mismatching_parents must be 0")
    if fp.get("result") != "EMPTY" and (type(sm.get("sampled_parents")) is not int or sm["sampled_parents"] <= 0):
        raise ValueError("G4: PASS requires sampled_parents above 0")
    settings = f"set=398 fraction=0.002 seed={sm.get('seed')} min-per-shard=2 whole-max={sm.get('whole_max')}"
    if (fp.get("settings") != settings or sm.get("forbidden_set") != "398" or sm.get("min_per_shard") != 2
            or sm.get("max_per_shard") is not None or "max_per_shard" not in sm
            or type(sm.get("whole_max")) is not int or sm["whole_max"] < 0
            or not isinstance(sm.get("seed"), str) or not sm["seed"]):
        raise ValueError("G4: fingerprint settings differ from replay summary")
    level, index, count = structure["slice"]
    tn = structure["target"][0]
    if fp.get("slice") != f"s{index}of{count}" or fp.get("mode") not in ("full", "slice"):
        raise ValueError("G4: fingerprint slice or mode differs")
    replay_mode(fp, whole, prefix)
    lo = 0 if fp["mode"] == "full" else level + 1
    if sm.get("levels") != ("" if lo == 0 else f"{lo}-{tn}"):
        raise ValueError("G4: replay summary levels differ from fingerprint mode")
    if run is not None and (fp.get("fingerprint") != replay_fingerprint(run, settings, lo, tn)
            or fp.get("prefix_fingerprint") != replay_fingerprint(run, settings, 0, level)):
        raise ValueError("G4: fingerprint differs from checked manifests, tools or settings")
    for key, tool in (("tool_sha256", "replay-398.py"), ("enum2_sha256", "enum2.py")):
        if sm.get(key) != sha(CHECKER.parent.parent / "enum2" / tool):
            raise ValueError("G4: replay summary tool hashes differ from fingerprint tools")
    # Reuse the reviewed detail-derived PASS/EMPTY rules, including EMPTY's parent evidence.
    checker = chain_checker()
    entries = {(e["n"], e["m"]): e for e in structure["summary"]["levels"]}
    shares = {int(re.fullmatch(r"\d+-(\d+)\.slice-\d+-of-\d+\.g6", name)[1]): row["records"]
              for name, row in structure["file_counts"].items() if ".slice-" in name}
    verdict, reasons = checker.g4_verdict(fp, sm, structure["slice"], {"required": entries}, entries, shares)
    if verdict not in ("PASS", "EMPTY") or verdict != fp.get("result") or fp.get("reasons") != []:
        raise ValueError(f"G4: replay evidence verdict {verdict}: {'; '.join(reasons)}")
    for row in sm["per_cell"]:
        cell = (row["n"], row["m"])
        if cell not in entries or row.get("parents_in_cell") != entries[cell].get("parents"):
            raise ValueError(f"G4: replay parent count differs from checked files at {row['cell']}")
    replay_scope(result, structure, sm, fp, load(result / "run-config.json"), load(result / "reach.json"))
    return fp


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("result", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--first", type=int, default=10)
    ap.add_argument("--prefix", type=Path)
    a = ap.parse_args()
    try:
        config = load(a.run / "run-config.json")
        if a.first not in (config["seed_n"], config["slice"][0] + 1):
            raise ValueError("G4: evidence check must start at the seed or immediately above the prefix")
        whole = a.first == config["seed_n"]
        prefix = None
        if a.prefix:
            # Recheck the bound bundle before using its replay as a prefix anchor.
            # This also makes standalone evidence.py obey the worker's upgrade rule.
            import receipt_audit
            prior = load(a.prefix)
            index, count = prior["slice"][1:]
            text = a.prefix.with_name(a.prefix.name.removesuffix(".structure.json") + ".txt")
            prefix = receipt_audit.validate(a.result.parent / f"s{index}of{count}", text)
        structure = reconcile(a.run, a.result, a.first, prefix)
        structure["g4"] = g4(a.run, a.result, structure, whole=whole, prefix=prefix)
        structure["retained"].update({p.relative_to(a.result).as_posix(): sha(p)
                                      for p in (a.result / "replay").rglob("*") if p.is_file()})
        if a.prefix:
            structure["prefix_receipt"] = {"name": a.prefix.name, "sha256": sha(a.prefix)}
        print(f"EVIDENCE OK: counts reconciled; retained files identical; G4 {structure['g4']['result']}; "
              f"{len(structure['recovered_cells'])} resumed cells exported")
    except (OSError, ValueError, KeyError, TypeError) as error:
        structure = {"schema": SCHEMA, "result": "FAIL", "error": str(error)}
        print(f"EVIDENCE FAIL: {error}")
    a.out.write_text(json.dumps(structure, sort_keys=True, indent=1) + "\n")
    return 0 if structure["result"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
