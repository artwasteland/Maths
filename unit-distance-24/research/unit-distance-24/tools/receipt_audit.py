#!/usr/bin/env python3
"""Validate four receipts and stage a result copy for the unchanged fleet summary audit.

Usage: receipt_audit.py RESULT TEXT_RECEIPT --out NEW_DIRECTORY
Then pass the staged directories to verify-chain-u24.py --summary-only.
The source result copy stays unchanged; exported records enter through history/INDEX.json.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil

import evidence
import worker


def safe_name(name):
    return (isinstance(name, str) and bool(name) and not Path(name).is_absolute()
            and ".." not in Path(name).parts and Path(name).as_posix() == name)


def typed_row(name, row, records="records"):
    if (not safe_name(name) or not isinstance(row, dict)
            or any(type(row.get(k)) is not int or row[k] < 0 for k in ("bytes", records))
            or not isinstance(row.get("sha256"), str) or not re.fullmatch("[0-9a-f]{64}", row["sha256"])):
        raise ValueError(f"RECEIPT: incomplete or untyped file record: {name}")


class InventoryFiles:
    """The worker's measured files; retained bytes replace these rows after remeasurement."""
    def __init__(self, path, structure):
        self.rows, self.inventory = {}, {}
        with gzip.open(path, "rt") as stream:
            header = json.loads(next(stream))
            self.header = header
            if (header.get("prefix_through") != 12 or any(type(header.get(k)) is not int or header[k] < 0
                                                        for k in ("files", "bytes"))
                    or not re.fullmatch("[0-9a-f]{64}", str(header.get("sha256")))):
                raise ValueError("RECEIPT: incomplete prefix inventory")
            for line in stream:
                row = json.loads(line)
                name = row.get("path")
                typed_row(name, row, "newlines")
                if name in self.inventory:
                    raise ValueError(f"RECEIPT: duplicate inventory path: {name}")
                self.inventory[name] = row
                self.rows[name] = {"bytes": row["bytes"], "records": row["newlines"], "sha256": row["sha256"]}
        # v1 inventories compacted the prefix; its whole-checked file measurements remain
        # in file_counts. Never use this compatibility path for an upper or slice file.
        for name, row in structure["file_counts"].items():
            typed_row(name, row)
            match = re.match(r"(?:shards/|_parents/)?(\d+)-\d+(?:[./]|$)", name)
            if name not in self.rows and match and int(match[1]) <= 12 and ".slice-" not in name:
                self.rows[name] = row

    def read(self, name):
        if name not in self.rows:
            raise ValueError(f"RECEIPT: required inventory row missing: {name}")
        return self.rows[name]

    def count(self, name):
        return self.read(name)["records"]

    def measure(self, name, actual):
        saved = self.read(name)
        evidence.count_equal(f"inventory {name} records", saved["records"], actual["records"])
        if any(saved[k] != actual[k] for k in ("bytes", "sha256")):
            raise ValueError(f"RECEIPT: inventory {name} differs from retained bytes")
        self.rows[name] = actual


def required_retained(config, reach, derived, files, mode):
    names = {"run-config.json", "run-summary.json", "reach.json", "counts.json", "hashes.json",
             "replay/summary.json", "replay/fingerprint.json"}
    if mode == "full":
        names.add("replay/red.json")
    tn, tm = config["target"]
    for n, m in [(tn, tm), *((tn - 1, int(m)) for m in reach["table"][str(tn - 1)])]:
        for suffix in evidence.RETAIN_SUFFIXES:
            name = f"{n}-{m}{suffix}"
            if name in files.inventory and files.read(name)["bytes"] < 4_000_000:
                names.add(name)
    if config.get("verify_stages"):
        names.update(f"verify/{n}-{m}.verify.manifest.json" for n, m in derived["required"])
    names.update("verify/" + name for name in files.inventory if re.fullmatch(r"\d+-\d+\.verify\.manifest\.json", name))
    return names


def measure_target(result, config, files, structure, summaries, measured):
    cell = "-".join(map(str, config["target"]))
    # Certificates preserve the exact reach input in order; the runbook does not copy .reach.g6.
    h, size, count = hashlib.sha256(), 0, 0
    stage_hashes = {".keep.g6": hashlib.sha256(), ".UNKNOWN.g6": hashlib.sha256()}
    with (result / (cell + ".certs.jsonl")).open() as stream:
        for raw in stream:
            rec = json.loads(raw)
            line = (rec["g6"] + "\n").encode()
            h.update(line)
            size += len(line)
            count += 1
            if rec["verdict"] in ("embedded", "unknown"):
                stage_hashes[".keep.g6"].update(line)
            if rec["verdict"] == "unknown":
                stage_hashes[".UNKNOWN.g6"].update(line)
    measured.rows[cell + ".reach.g6"] = {"bytes": size, "records": count, "sha256": h.hexdigest()}
    suffixes = {".g6", ".reach.g6", ".keep.g6", ".certs.jsonl", ".UNKNOWN.g6"}
    if set(structure["target_files"]) != suffixes:
        raise ValueError("RECEIPT: missing target file counts")
    for suffix in sorted(suffixes):
        name = cell + suffix
        actual = measured.read(name)
        files.measure(name, actual)
        row = structure["target_files"][suffix]
        typed_row(name, row)
        evidence.count_equal(f"structure {name} records", row["records"], actual["records"])
        if row != actual:
            raise ValueError(f"RECEIPT: target {name} differs from retained bytes")
        if suffix in stage_hashes and actual["sha256"] != stage_hashes[suffix].hexdigest():
            raise ValueError(f"RECEIPT: target {name} differs from retained certificates")
    rule = "triangles" if config.get("triangles") else "rhombus" if config.get("rhombus") else None
    manifest = evidence.load(result / (cell + ".prune.manifest.json"))
    silent = {}
    if rule:
        fields = ("budget", "verify_fail", "lift_fail", "internal") if rule == "triangles" else ("certificate_failures",)
        stats = manifest[rule + "_stats"]
        if any(type(stats.get(k)) is not int or stats[k] < 0 for k in fields):
            raise ValueError("RECEIPT: missing target prover diagnostic counts")
        silent[("tri" if rule == "triangles" else rule) + "_silent_passes"] = sum(stats[k] for k in fields)
    counts = evidence.prune_counts(result, cell, measured, rule, silent, cell + ".reach.g6")
    for summary in summaries:
        e = next(e for e in summary["levels"] if [e["n"], e["m"]] == config["target"])
        evidence.count_equal(f"{cell} children", e.get("children"), measured.count(cell + ".g6"))
        for key, value in counts.items():
            evidence.count_equal(f"{cell} prune {key}", e["prune"]["counts"].get(key), value)
    for label, claimed in (("structure target", structure["target_counts"]), ("target manifest", manifest["counts"])):
        if set(claimed) != set(counts):
            raise ValueError(f"COUNTS: {label} prune count keys differ from checked files")
        for key, value in counts.items():
            evidence.count_equal(f"{label} {key}", claimed[key], value)
    # Return only measurements to callers and to the CLI's survivor figure.
    return {suffix: measured.read(cell + suffix) for suffix in suffixes}, counts


def measure_retained(result, files, structure, measured):
    """Bind every retained level output to measured records and its producers."""
    names = sorted(name for name in structure["retained"]
                   if re.fullmatch(r"\d+-\d+(?:(?:\.(?:keep|UNKNOWN))?\.g6|\.certs\.jsonl)", name))
    for name in names:
        actual = measured.read(name)
        files.measure(name, actual)
        row = structure["file_counts"].get(name)
        typed_row(name, row)
        evidence.count_equal(f"structure file_counts {name} records", row["records"], actual["records"])
        if row != actual:
            raise ValueError(f"RECEIPT: file_counts {name} differs from retained bytes")
        if structure["retained"][name] != actual["sha256"]:
            raise ValueError(f"RECEIPT: retained {name} differs from checked result")

    # Producer paths remain absolute after relocation; bind their basenames, as
    # the copy policy does. Check every naming manifest, including repeated names.
    outputs, prunes = {}, {}
    for name in sorted(structure["retained"]):
        if not name.endswith("manifest.json"):
            continue
        manifest = evidence.load(result / name)
        for output, digest in (manifest.get("outputs_sha256") or {}).items():
            outputs.setdefault(Path(output).name, []).append((name, digest))
        match = re.fullmatch(r"(\d+)-(\d+)\.prune\.manifest\.json", name)
        if match and manifest.get("kind") == "prune" and manifest.get("level") == [int(v) for v in match.groups()]:
            prunes[name[:-len(".prune.manifest.json")]] = (name, manifest)
    counts = {f"{row[0]}-{row[1]}": row[-1] for row in evidence.load(result / "counts.json")}
    kinds = {".certs.jsonl": "input", ".keep.g6": "kept", ".UNKNOWN.g6": "unknown"}
    keys = ("input", "kept", "unknown", "pruned")
    prune_counts = {}
    for name in names:
        actual = measured.read(name)
        for producer, digest in outputs.get(name, []):
            if digest != actual["sha256"]:
                raise ValueError(f"RECEIPT: retained {name} sha256 differs from {producer} outputs_sha256")
        suffix = next((suffix for suffix in kinds if name.endswith(suffix)), None)
        if suffix is None:
            continue
        cell = name[:-len(suffix)]
        producer, manifest = prunes.get(cell, (None, {}))
        if producer is None or name not in {Path(p).name for p in (manifest.get("outputs_sha256") or {})}:
            raise ValueError(f"RECEIPT: retained {name} has no prune manifest naming it")
        claimed = manifest.get("counts", {})
        if not isinstance(claimed, dict) or any(type(claimed.get(k)) is not int or claimed[k] < 0 for k in keys):
            raise ValueError(f"COUNTS: {producer}: missing or untyped prune counts")
        evidence.count_equal(f"{producer} {kinds[suffix]}", claimed[kinds[suffix]], actual["records"])
        prune_counts[cell] = claimed
    for cell, claimed in sorted(prune_counts.items()):
        row = counts.get(cell)
        if not isinstance(row, dict):
            raise ValueError(f"COUNTS: counts.json cell {cell} is missing")
        for key in keys:
            evidence.count_equal(f"counts.json {cell} prune {key}", row.get(key), claimed[key])


def check_summary_counts(summary, config, derived, files, result):
    for entry in summary["levels"]:
        n, m = entry["n"], entry["m"]
        if (n, m) not in derived["required"]:
            continue
        cell = f"{n}-{m}"
        children = files.count(cell + ".g6")
        evidence.count_equal(f"{cell} children", entry.get("children"), children)
        if config.get("reach"):
            kept = files.count(cell + ".reach.g6")
            for key, value in {"input": children, "kept": kept, "dropped": children - kept}.items():
                if key in entry["reach"] or key == "kept" or not entry["reach"].get("resumed"):
                    evidence.count_equal(f"{cell} reach {key}", entry["reach"].get(key), value)
        if derived["prune_from"] is not None and n >= derived["prune_from"]:
            stage = files.count(cell + (".reach.g6" if config.get("reach") else ".g6"))
            keep, unknown = files.count(cell + ".keep.g6"), files.count(cell + ".UNKNOWN.g6")
            evidence.count_equal(f"{cell} certificates", files.count(cell + ".certs.jsonl"), stage)
            for key, value in {"input": stage, "kept": keep, "unknown": unknown, "pruned": stage - keep}.items():
                evidence.count_equal(f"{cell} prune {key}", entry["prune"]["counts"].get(key), value)
        if config.get("verify_stages"):
            vm = evidence.load(result / f"verify/{cell}.verify.manifest.json")
            kind = entry["verify"]["stage_kind"]
            stage = files.read(cell + {"keep": ".keep.g6", "reach": ".reach.g6", "full": ".g6"}[kind])
            for label, row in (("verify", entry["verify"]), ("verify manifest", vm)):
                evidence.count_equal(f"{cell} {label} records", row.get("records"), stage["records"])
            if vm.get("stage_kind") != kind or vm.get("stage_sha256") != stage["sha256"]:
                raise ValueError(f"RECEIPT: {cell} verification differs from checked stage")


def checked_value(where, claimed, actual):
    if json.dumps(claimed, sort_keys=True) != json.dumps(actual, sort_keys=True):
        raise ValueError(f"RECEIPT: {where} differs from checked files")


def referenced_name(path, rows):
    # Prefer the longest inventory suffix: _parents/24-69.g6 is not 24-69.g6.
    matches = [name for name in rows if isinstance(path, str) and (path == name or path.endswith("/" + name))]
    return max(matches, key=len, default=None)


def check_retained_claims(result, config, derived, files, structure, measured):
    """Remeasure metadata too, and bind every retained producer's content claims.

    Deleted inputs stay historical inventory evidence unless retained certificates
    or parent sources reconstruct their exact ordered bytes. Diagnostics that do
    not distinguish certificate records cannot be independently recovered here.
    """
    retained = structure["retained"]
    summaries = (evidence.load(result / "run-summary.json"), structure["summary"])
    entries = [{(v["n"], v["m"]): v for v in sm["levels"]} for sm in summaries]
    overrides = evidence.load(result / "reach.json").get("ubar_override", {})
    checked_value("config ubar_override", config.get("ubar_override", {}), overrides)
    for sm in summaries:
        checked_value("summary ubar_override", sm.get("ubar_override", {}), overrides)
        for key in ("forbidden_set", "prune_filter_set", "triangles", "verify_stages"):
            checked_value(f"summary {key}", sm.get(key), config.get(key))
        checked_value("summary reach enabled", sm["reach"].get("enabled"), config["reach"])
        checked_value("summary prune_filter_only", sm["prune"].get("prune_filter_only"), config["prune_filter_only"])
    for name in sorted(retained):
        raw = (result / name).read_bytes()
        row = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "records": raw.count(b"\n")}
        measured.rows[name] = row
        source = Path(name).name if name.startswith("verify/") else name
        if source in files.inventory:
            files.measure(source, row)
        if source in structure["file_counts"]:
            checked_value(f"file_counts {source}", structure["file_counts"][source], row)

    stages = {name[:-len(".manifest.json")]: evidence.load(result / name)
              for name in retained if re.fullmatch(r"\d+-\d+\.manifest\.json", name)}
    full = {name[:-3] for name in retained if re.fullmatch(r"\d+-\d+\.g6", name)}
    for cell in sorted(stages.keys() - full):
        raise ValueError(f"RECEIPT: {cell}.manifest.json describes a level file that is not retained")
    for cell in sorted(full - stages.keys()):
        raise ValueError(f"RECEIPT: retained {cell}.g6 has no stage manifest")
    for cell, manifest in sorted(stages.items()):
        name, output = cell + ".manifest.json", measured.read(cell + ".g6")
        evidence.count_equal(f"{name} children_written", manifest.get("children_written"), output["records"])
        checked_value(f"{name} children_file_sha256", manifest.get("children_file_sha256"), output["sha256"])
        checked_value(f"{name} exit_status", manifest.get("exit_status"), 0)
        checked_value(f"{name} forbidden_set", manifest.get("forbidden_set"), config["forbidden_set"])
        for key, value in {"enabled": config["prune"], "prune_from": config["prune_from"],
                           "prune_filter_only": config["prune_filter_only"], "triangles": config["triangles"],
                           "filter_set": config["prune_filter_set"]}.items():
            checked_value(f"{name} pruning {key}", manifest.get("pruning", {}).get(key), value)
        n, m = map(int, cell.split("-"))
        if (n, m) not in derived["allowed"]:
            continue
        sources = manifest.get("parent_sources", [])
        expected = entries[1][n, m]["parent_sources"]
        checked_value(f"{name} parent stages", [{k: s.get(k) for k in ("level", "kind")} for s in sources],
                      [{k: s[k] for k in ("level", "kind")} for s in expected])
        parent_names = []
        for source in sources:
            pn, pm = source["level"]
            suffix = {"keep": ".keep.g6", "reach": ".reach.g6", "full": ".g6"}[source["kind"]]
            parent = f"{pn}-{pm}{suffix}"
            checked_value(f"{name} parent file", Path(source["file"]).name, parent)
            evidence.count_equal(f"{name} parent d", source.get("d"), m - pm)
            row = files.read(parent)
            evidence.count_equal(f"{name} parent {parent} records", source.get("records"), row["records"])
            checked_value(f"{name} parent {parent} sha256", source.get("sha256"), row["sha256"])
            parent_names.append(parent)
        parent_file = f"_parents/{cell}.g6"
        checked_value(f"{name} parent_file", referenced_name(manifest.get("parent_file", ""), files.rows), parent_file)
        if all(parent in retained for parent in parent_names):
            raw = b"".join((result / parent).read_bytes() for parent in parent_names)
            actual = {"bytes": len(raw), "records": raw.count(b"\n"), "sha256": hashlib.sha256(raw).hexdigest()}
            files.measure(parent_file, actual)
            measured.rows[parent_file] = actual
        checked_value(f"{name} parent_range", manifest.get("parent_range"), [0, files.count(parent_file)])
        reach = manifest.get("reach", {})
        for key, value in {"enabled": config["reach"], "k": derived["table"][n][m],
                           "reach_json_sha256": measured.read("reach.json")["sha256"],
                           "table_level": {str(k): v for k, v in derived["table"][n].items()},
                           "table_parent_level": {str(k): v for k, v in derived["table"][n-1].items()}}.items():
            checked_value(f"{name} reach {key}", reach.get(key), value)

    rule = "triangles" if config.get("triangles") else "rhombus" if config.get("rhombus") else None
    prefix = {"triangles": "tri", "rhombus": "rhombus"}.get(rule)
    for cell in sorted(full):
        name = cell + ".prune.manifest.json"
        if name not in retained:
            continue
        manifest = evidence.load(result / name)
        records = [json.loads(line) for line in (result / (cell + ".certs.jsonl")).read_text().splitlines()]
        hashes = {suffix: hashlib.sha256() for suffix in (".reach.g6", ".keep.g6", ".UNKNOWN.g6")}
        size = 0
        verified = {k: 0 for k in ("records", "tu", "refuted", "embedded", "unknown", "kept")}
        checker = dict(verified, forbidden=0, proof_nodes=0)
        del checker["kept"]
        checker.update({f"{p}_{v}": 0 for p in ("tri", "rhombus") for v in ("tu", "refuted")})
        if prefix:
            verified.update({prefix + "_tu": 0, prefix + "_refuted": 0})
        for record in records:
            verdict, witness = record["verdict"], record.get("witness") or {}
            raw = (record["g6"] + "\n").encode()
            hashes[".reach.g6"].update(raw)
            size += len(raw)
            verified["records"] += 1
            verified[verdict] += 1
            checker["records"] += 1
            checker[verdict] += 1
            if verdict in ("embedded", "unknown"):
                verified["kept"] += 1
                hashes[".keep.g6"].update(raw)
            if verdict == "unknown":
                hashes[".UNKNOWN.g6"].update(raw)
            for p in ("tri", "rhombus"):
                if p in witness:
                    checker[p + "_" + verdict] += 1
                    if p == prefix:
                        verified[p + "_" + verdict] += 1
            if verdict == "refuted" and "tree" in witness:
                stack = [witness["tree"]]
                while stack:
                    node = stack.pop()
                    checker["proof_nodes"] += 1
                    stack.extend(node["children"])
        source = cell + (".reach.g6" if config["reach"] else ".g6")
        checked_value(f"{name} level_file", Path(manifest.get("level_file", "")).name, source)
        for key in ("target", "forbidden_set", "triangles"):
            checked_value(f"{name} {key}", manifest.get(key), config[key])
        checked_value(f"{name} filter_set", manifest.get("filter_set"), config["prune_filter_set"])
        for key, value in {"exit_status": 0, "problems": [], "mutation": {"unknown_as_pruned": False}}.items():
            checked_value(f"{name} {key}", manifest.get(key), value)
        for key in ("skipped", "filter_only"):
            checked_value(f"{name} embedder {key}", manifest.get("embedder", {}).get(key), config["prune_filter_only"])
        # check_accept pins this audit's target to (24,69), whose TU producer
        # records the proved bound 69 (the reach u-bar is a different bound).
        bound = config["target"][1]
        for key, value in {"n": config["target"][0], "proved_upper_bound": bound}.items():
            checked_value(f"{name} tu_rule_bound {key}", manifest.get("tu_rule_bound", {}).get(key), value)
        actual = {"bytes": size, "records": len(records), "sha256": hashes[".reach.g6"].hexdigest()}
        files.measure(source, actual)
        measured.rows[source] = actual
        if source in structure["file_counts"]:
            checked_value(f"file_counts {source}", structure["file_counts"][source], actual)
        for suffix in (".keep.g6", ".UNKNOWN.g6"):
            checked_value(f"retained {cell + suffix} certificate sha256", measured.read(cell + suffix)["sha256"], hashes[suffix].hexdigest())
        silent = {}
        if rule:
            stats = manifest[rule + "_stats"]
            fields = ("budget", "verify_fail", "lift_fail", "internal") if rule == "triangles" else ("certificate_failures",)
            for key in fields:
                if type(stats.get(key)) is not int or stats[key] < 0:
                    raise ValueError(f"COUNTS: {name}: missing prover diagnostic {key}")
            silent[prefix + "_silent_passes"] = sum(stats[k] for k in fields)
        counts = evidence.prune_counts(result, cell, measured, rule, silent, source)
        for label, claimed in ((name + " counts", manifest["counts"]), (name + " verified_counts", manifest["verified_counts"])):
            wanted = counts if label.endswith(" counts") else verified
            checked_value(label + " keys", sorted(claimed), sorted(wanted))
            for key, value in wanted.items():
                evidence.count_equal(label + " " + key, claimed.get(key), value)
        for rows in entries:
            entry = rows[tuple(map(int, cell.split("-")))]
            for key, value in counts.items():
                evidence.count_equal(f"{cell} prune {key}", entry["prune"]["counts"].get(key), value)
            if "checker" in entry["prune"]:
                checked_value(f"{cell} summary prune checker", entry["prune"]["checker"], manifest["checker"])
        said = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", manifest.get("checker", ""))}
        checked_value(f"{name} checker result", manifest.get("checker", "").startswith("ACCEPT certificates "), True)
        for key, value in checker.items():
            if key in said or key in ("records", "tu", "embedded", "refuted", "unknown", "proof_nodes", "forbidden"):
                evidence.count_equal(f"{name} checker {key}", said.get(key), value)
        if rule:
            for key, value in {"graphs": counts["survivors"], "tu": counts[prefix + "_tu"],
                               "refuted": counts[prefix + "_refuted"], "pass": counts[prefix + "_survivors"]}.items():
                evidence.count_equal(f"{name} {rule}_stats {key}", manifest[rule + "_stats"].get(key), value)
            evidence.count_equal(f"{name} {rule}_silent_passes", manifest.get(rule + "_silent_passes"), counts[prefix + "_silent_passes"])
            checked_value(f"{name} {rule}_prover witness", manifest.get(rule + "_prover", {}).get("witness"), prefix)
            if rule == "triangles":
                checked_value(f"{name} triangles_checker command", evidence.fleet_judge().checker_command_ok(result, cell, manifest), True)
        if "survivors" in manifest.get("embedder", {}):
            evidence.count_equal(f"{name} embedder survivors", manifest["embedder"]["survivors"],
                                 counts[prefix + "_survivors"] if prefix else counts["survivors"])

    # Every naming map is checked, including exported aggregates. Reconstructed
    # deleted inputs count as measured; other deleted names remain historical.
    manifests = {name: evidence.load(result / name) for name in retained if name.endswith("manifest.json")}
    manifests.update({"export " + name: json.loads(row["text"]) for name, row in structure["manifests"].items()})
    for name, manifest in sorted(manifests.items()):
        for field in ("inputs_sha256", "outputs_sha256"):
            for path, digest in manifest.get(field, {}).items():
                source = referenced_name(path, files.rows.keys() | measured.rows.keys())
                if source in measured.rows:
                    checked_value(f"{name} {field} {source}", digest, measured.read(source)["sha256"])
                elif field == "inputs_sha256" and Path(path).name in ("forbidden-398.json", "forbidden-74.json", "tu-gadgets.json"):
                    data = evidence.CHECKER.parent.parent / "data" / Path(path).name
                    checked_value(f"{name} {field} {data.name}", digest, evidence.sha(data))
        if not name.startswith("verify/"):
            continue
        cell = Path(name).name[:-len(".verify.manifest.json")]
        kind = manifest["stage_kind"]
        stage = cell + {"keep": ".keep.g6", "reach": ".reach.g6", "full": ".g6"}[kind]
        checked_value(f"{name} stage_file", Path(manifest.get("stage_file", "")).name, stage)
        n, m = map(int, cell.split("-"))
        for key, value in {"kind": "verify", "level": [n, m], "exit_status": 0, "forbidden_set": config["forbidden_set"],
                           "check": evidence.fleet_judge().VERIFY_CHECK, "udenum_target": [n+1, m+n],
                           "forbidden_sha256": evidence.sha(evidence.CHECKER.parent.parent / "data/forbidden-398.json")}.items():
            checked_value(f"{name} {key}", manifest.get(key), value)
        # All retained verification manifests are counted against their bound
        # inventory stage, even when that stage itself has since been deleted.
        count = files.count(stage)
        evidence.count_equal(f"{name} parents_seen", manifest.get("parents_seen"), count)
        cursor = 0
        for index, part in enumerate(manifest.get("parts", [])):
            span = part.get("range")
            if (not isinstance(span, list) or len(span) != 2 or any(type(v) is not int for v in span)
                    or span[0] != cursor or span[1] < span[0] or span[1] > count):
                raise ValueError(f"RECEIPT: {name} parts do not tile checked stage")
            cursor = span[1]
            evidence.count_equal(f"{name} part {index} parents_seen", part.get("udenum_stats", {}).get("parents_seen"), span[1]-span[0])
            for key, value in {"parents_degree_skipped": span[1]-span[0], "parents_processed": 0, "children_written": 0,
                               "bad_sets": 0, "neighbourhoods": 0, "neighbourhood_orbit_reps": 0,
                               "neighbourhoods_bad": 0, "child_orbit_rejected": 0}.items():
                evidence.count_equal(f"{name} part {index} {key}", part.get("udenum_stats", {}).get(key), value)
        if not manifest.get("parts") or cursor != count:
            raise ValueError(f"RECEIPT: {name} parts do not tile checked stage")
        for rows in entries:
            entry = rows[tuple(map(int, cell.split("-")))]
            if "parts" in entry["verify"]:
                evidence.count_equal(f"{cell} summary verify parts", entry["verify"]["parts"], len(manifest["parts"]))


def check_text_claims(text, paths, structure, files):
    def claim(label):
        lines = [line[len('# ' + label + ': '):] for line in text.splitlines() if line.startswith('# ' + label + ': ')]
        if len(lines) != 1:
            raise ValueError(f"RECEIPT: missing or repeated {label}")
        return lines[0]

    for kind, path in paths.items():
        label = 'inventory' if kind == 'inventory' else kind + ' receipt'
        head = claim(label).split('; ', 1)[0]
        checked_value(f"text {label} bytes", head, f"sha256 {evidence.sha(path)}, {path.stat().st_size} bytes")
    inv = json.loads(claim('inventory').split('; ', 1)[1])
    for key, value in {'sha256': evidence.sha(paths['inventory']), 'bytes': paths['inventory'].stat().st_size,
                       'prefix': files.header}.items():
        checked_value(f"text inventory {key}", inv.get(key), value)
    checked_value('text level files checked', claim("level files checked (the runbook's hashes.json rule)"), structure['files_digest'])
    checked_value('text target records', json.loads(claim('target records from checked files')), structure['target_files'])
    checked_value('text target counts', json.loads(claim('target counts from checked files')), structure['target_counts'])


def check_structure(structure, original, config, derived, files):
    archive = {}
    for name, row in structure["manifests"].items():
        if not safe_name(name) or not isinstance(row.get("text"), str):
            raise ValueError(f"RECEIPT: invalid exported manifest {name}")
        raw = row["text"].encode()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != row.get("sha256"):
            raise ValueError(f"RECEIPT: exported manifest {name} hash differs")
        saved = files.read(name)
        if saved != {"sha256": digest, "bytes": len(raw), "records": raw.count(b"\n")}:
            raise ValueError(f"RECEIPT: exported manifest {name} differs from inventory")
        archive[name] = json.loads(raw)
    evidence.require_structure(original, structure["summary"])
    raw_entries = {(e["n"], e["m"]): e for e in original["levels"]}
    for entry in structure["summary"]["levels"]:
        n, m = entry["n"], entry["m"]
        if (n, m) not in derived["allowed"]:
            continue
        cell = f"{n}-{m}"
        # A resumed upper cell must supply its own aggregate and every shard manifest.
        resumed = raw_entries[n, m].get("resumed") and n > config["slice"][0]
        if resumed or cell + ".manifest.json" in archive:
            required = {cell + ".manifest.json"} | {name[:-3] + ".manifest.json" for name in files.rows
                        if re.fullmatch(rf"shards/{cell}/[^/]+\.g6", name)}
            if not required <= archive.keys():
                raise ValueError(f"STRUCTURE: {cell}: required preserved manifests missing: {sorted(required - archive.keys())}")
            evidence.structural_entry(Path("."), entry, files, {}, archive)
        sources = []
        for pm in derived["allowed"][n, m]:
            pn = n - 1
            kind = "keep" if derived["prune_from"] is not None and pn >= derived["prune_from"] else "reach" if config.get("reach") else "full"
            suffix = {"keep": ".keep.g6", "reach": ".reach.g6", "full": ".g6"}[kind]
            if pn == config["slice"][0]:
                suffix = f".slice-{config['slice'][1]}-of-{config['slice'][2]}.g6"
                kind += "+slice"
            sources.append({"level": [pn, pm], "kind": kind, "records": files.count(f"{pn}-{pm}{suffix}")})
        parents = sum(s["records"] for s in sources)
        # Whole receipts measured these files; partial receipts inherit checked prefix structure.
        if n > config["slice"][0] or f"_parents/{cell}.g6" in files.rows:
            evidence.count_equal(f"{cell} parent file", files.count(f"_parents/{cell}.g6"), parents)
        shards = []
        for name in files.rows:
            match = re.fullmatch(rf"shards/{cell}/{cell}-(\d+)-(\d+)\.g6", name)
            if match:
                shards.append({"range": [int(match[1]), int(match[2])], "children": files.count(name)})
        shards.sort(key=lambda s: s["range"])
        if not shards and n <= config["slice"][0]:
            shards = entry["shards"]  # validated against the recursively checked whole receipt below
        if (not shards or shards[0]["range"][0] != 0 or shards[-1]["range"][1] != parents
                or any(a["range"][1] != b["range"][0] for a, b in zip(shards, shards[1:]))):
            raise ValueError(f"STRUCTURE: {cell}: inventory shards do not tile parents")
        actual = {"parent_edge_counts": derived["allowed"][n, m], "parent_sources": sources, "parents": parents,
                  "reach_k": derived["table"][n][m], "shards": shards}
        for key, value in actual.items():
            if json.dumps(entry.get(key), sort_keys=True) != json.dumps(value, sort_keys=True):
                raise ValueError(f"STRUCTURE: {cell}: exported {key} differs from checked manifests and inventory")
            raw = raw_entries[n, m]
            if key not in raw and raw.get("resumed"):
                continue
            claimed = raw.get(key)
            if key == "shards" and isinstance(claimed, list):
                claimed = [{"range": s["range"], "children": s["children"]} for s in claimed]
            if json.dumps(claimed, sort_keys=True) != json.dumps(value, sort_keys=True):
                raise ValueError(f"STRUCTURE: {cell}: summary {key} differs from checked manifests and inventory")
        evidence.count_equal(f"{cell} shard children total", sum(s["children"] for s in shards), files.count(cell + ".g6"))


def validate(result, text_path, seen=None, measurements=None):
    seen = set() if seen is None else seen
    identity = text_path.resolve()
    if identity in seen:
        raise ValueError("RECEIPT: cyclic prefix receipt binding")
    seen.add(identity)
    text = text_path.read_text()
    if "# u24-worker verdict: pass" not in text.splitlines():
        raise ValueError("RECEIPT: worker did not pass")
    if f"sha256 {evidence.sha(worker.CHECKER)}" not in text:
        raise ValueError("RECEIPT: checker pin differs")
    stem = text_path.with_suffix("")
    paths = {kind: Path(str(stem) + suffix) for kind, suffix in
             (("known", ".known.json"), ("inventory", ".inventory.jsonl.gz"), ("structure", ".structure.json"))}
    for kind, path in paths.items():
        label = "inventory" if kind == "inventory" else kind + " receipt"
        if not re.search(rf"^# {label}: sha256 {evidence.sha(path)},", text, re.M):
            raise ValueError(f"RECEIPT: {kind} sha256 is not bound by text receipt")
    structure = evidence.load(paths["structure"])
    if structure.get("schema") != evidence.SCHEMA or structure.get("result") != "OK":
        raise ValueError("RECEIPT: structure audit did not pass")
    config = evidence.load(result / "run-config.json")
    if structure["slice"] != config["slice"] or structure["target"] != config["target"]:
        raise ValueError("RECEIPT: structure slice or target differs from result")
    whole = "CHAIN OK" in text.splitlines()
    if worker.check_accept(text, 0 if whole else 3, config["slice"][1], whole):
        raise ValueError("RECEIPT: checker output is not an accepted whole or prefix-bound check")
    known = evidence.load(paths["known"])
    if (known.get("result") != "OK" or known.get("problems") != []
            or known.get("slice") != config["slice"] or known.get("target") != config["target"]):
        raise ValueError("RECEIPT: known-graph control did not pass for this slice")
    prefix, prefix_files = None, {}
    if not whole:
        binding = structure.get("prefix_receipt", {})
        name = binding.get("name", "")
        if Path(name).name != name or not name.endswith(".structure.json"):
            raise ValueError("RECEIPT: missing whole-check prefix binding")
        prefix_path = text_path.parent / name
        if evidence.sha(prefix_path) != binding.get("sha256"):
            raise ValueError("RECEIPT: prefix structure hash differs")
        prefix_text = prefix_path.with_name(name[:-len(".structure.json")] + ".txt")
        body = prefix_text.read_text()
        if "CHAIN OK" not in body.splitlines():
            raise ValueError("RECEIPT: prefix maker has no whole check")
        current_hash = re.search(r"^# shared prefix digest: ([0-9a-f]{64});", text, re.M)
        prefix_hash = re.search(r"^# shared prefix digest: ([0-9a-f]{64});", body, re.M)
        if not current_hash or not prefix_hash or current_hash[1] != prefix_hash[1]:
            raise ValueError("RECEIPT: shared prefix digest differs from whole check")
        prefix = evidence.load(prefix_path)
        index, count = prefix["slice"][1:]
        prefix = validate(result.parent / f"s{index}of{count}", prefix_text, seen, prefix_files)
    if structure["run_summary_sha256"] != evidence.sha(result / "run-summary.json"):
        raise ValueError("RECEIPT: exported structure names another run-summary.json")
    summary, reach = evidence.load(result / "run-summary.json"), evidence.load(result / "reach.json")
    derived = evidence.requirements(config, summary, reach)
    evidence.requirements(config, structure["summary"], reach)
    files = InventoryFiles(paths["inventory"], structure)
    for name, row in prefix_files.items():
        match = re.match(r"(?:shards/|_parents/)?(\d+)-\d+(?:[./]|$)", name)
        if match and int(match[1]) <= config["slice"][0] and ".slice-" not in name:
            if name in files.rows and files.rows[name] != row:
                raise ValueError(f"RECEIPT: prefix file {name} differs from whole check")
            files.rows[name] = row
    for n, m in derived["required"]:
        suffixes = [".g6"] + ([".reach.g6"] if config.get("reach") else [])
        if derived["prune_from"] is not None and n >= derived["prune_from"]:
            suffixes += [".keep.g6", ".UNKNOWN.g6", ".certs.jsonl"]
        if n > config["slice"][0]:
            suffixes += [".manifest.json"]
            if config.get("prune") and n >= derived["prune_from"]:
                suffixes += [".prune.manifest.json"]
        for suffix in suffixes:
            files.read(f"{n}-{m}{suffix}")
    fp = evidence.load(result / "replay/fingerprint.json")
    expected = required_retained(config, reach, derived, files, fp.get("mode"))
    declared = set(structure["retained"])
    present = {p.relative_to(result).as_posix() for p in result.rglob("*")
               if p.is_file() and p.relative_to(result).parts[0] != "history"}
    if expected != declared or expected != present:
        raise ValueError(f"RECEIPT: retained file set differs from copy policy: "
                         f"missing {sorted(expected - (declared & present))}, extra {sorted((declared | present) - expected)}")
    measured = evidence.Files(result)
    target_files, target_counts = measure_target(result, config, files, structure, (summary, structure["summary"]), measured)
    measure_retained(result, files, structure, measured)
    for sm in (summary, structure["summary"]):
        check_summary_counts(sm, config, derived, files, result)
    for name, row in structure["file_counts"].items():
        saved = files.read(name)
        evidence.count_equal(f"structure file_counts {name} records", row["records"], saved["records"])
        if row != saved:
            raise ValueError(f"RECEIPT: file_counts {name} differs from measured inventory")
    check_structure(structure, summary, config, derived, files)
    if prefix:
        old = {(e["n"], e["m"]): e for e in prefix["summary"]["levels"]}
        for e in structure["summary"]["levels"]:
            if config["seed_n"] < e["n"] <= config["slice"][0]:
                for key in ("parent_sources", "parent_edge_counts", "parents", "reach_k", "shards"):
                    if e[key] != old[e["n"], e["m"]][key]:
                        raise ValueError(f"STRUCTURE: {e['n']}-{e['m']}: prefix {key} differs from whole check")
    hashes = evidence.load(result / "hashes.json")
    names = {name for name in files.rows if re.fullmatch(r"\d+-\d+(?:\.(?:reach|keep|UNKNOWN))?\.g6", name)
             and (int(name.split("-")[0]) <= config["slice"][0] or int(name.split("-")[0]) >= config["target"][0] - 2)}
    if hashes.get("slice") != config["slice"] or set(hashes["files"]) != names:
        raise ValueError("RECEIPT: hashes.json file set or slice differs from copy policy")
    digest = hashlib.sha256()
    for name in sorted(names):
        row = files.read(name)
        evidence.count_equal(f"hashes.json {name} records", hashes["files"][name].get("records"), row["records"])
        if hashes["files"][name].get("sha256") != row["sha256"]:
            raise ValueError(f"RECEIPT: hashes.json {name} differs from measured inventory")
        digest.update(f"{name} {row['sha256']}\n".encode())
    if structure["files_digest"] != f"{len(names)} files, sha256 {digest.hexdigest()}":
        raise ValueError("RECEIPT: files digest differs from measured inventory")
    counts = [[e["n"], e["m"], e.get("children"), (e.get("prune") or {}).get("counts")] for e in summary["levels"]]
    if json.dumps(evidence.load(result / "counts.json"), sort_keys=True) != json.dumps(counts, sort_keys=True):
        raise ValueError("COUNTS: counts.json differs from the checked run-summary.json")
    for name in sorted(expected):
        if evidence.sha(result / name) != structure["retained"][name]:
            raise ValueError(f"RECEIPT: retained {name} differs from checked result")
        source = Path(name).name if name.startswith("verify/") else name
        if source in files.inventory and evidence.sha(result / name) != files.read(source)["sha256"]:
            raise ValueError(f"RECEIPT: retained {name} differs from measured inventory")
    if structure.get("g4") != fp:
        raise ValueError("RECEIPT: G4 fingerprint differs from checked result")
    evidence.g4(None, result, structure, whole=whole, prefix=prefix)
    check_retained_claims(result, config, derived, files, structure, measured)
    check_text_claims(text, paths, structure, files)
    structure["target_files"], structure["target_counts"] = target_files, target_counts
    if measurements is not None:
        measurements.update(files.rows)
    return structure


def prepare(result, text_path, dest):
    structure = validate(result, text_path)
    if dest.exists():
        raise ValueError("RECEIPT: staging destination must not exist")
    shutil.copytree(result, dest)
    history = dest / "history"
    history.mkdir(exist_ok=True)
    name = "receipt-" + evidence.sha(Path(str(text_path.with_suffix("")) + ".structure.json"))
    (history / (name + ".json")).write_text(json.dumps(structure["summary"]) + "\n")
    index = history / "INDEX.json"
    old = evidence.load(index)["commits"] if index.exists() else []
    index.write_text(json.dumps({"commits": [name, *old]}) + "\n")
    return structure


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("result", type=Path)
    ap.add_argument("receipt", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    try:
        structure = prepare(a.result, a.receipt, a.out)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"RECEIPT FAIL: {error}")
        return 1
    print(f"RECEIPT OK: slice {structure['slice'][1]}, target survivors {structure['target_files']['.keep.g6']['records']}, "
          f"{len(structure['recovered_cells'])} resumed cells exported; summary input {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
