#!/usr/bin/env python3
"""Retained-output G1 controls; exact errors and untouched receipts after every red.

No enumeration or git writes. Use --audit-code ORIGINAL_RECEIPT_AUDIT.py with
--expect-unpatched to prove the same mutations are accepted without the fix.
The production fixtures have empty level-23 keeps, so the dropped-graph control
starts with a separately labelled synthetic, consistent measurement fixture.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import evidence as e
import judge
import receipt_audit as audit
from rereview_controls import dump, inventory, replay_totals, seal, write_inventory


CELL = "23-64"


def paths(root, index=1907):
    return (root / f"res/24-69-L12-tri-pf74/s{index}of1920",
            root / f"res/check/s{index}of1920-fixcheck.txt")


def refresh(result, text, changed, *, records=True):
    """Reseal hashes/bytes; optionally preserve the probe's stale record claims."""
    sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
    s, rows = e.load(sp), inventory(ip)
    hashes = e.load(result / "hashes.json")
    for name in changed:
        raw = (result / name).read_bytes()
        actual = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), records=raw.count(b"\n"))
        s["retained"][name] = actual["sha256"]
        source = Path(name).name if name.startswith("verify/") else name
        for row in rows:
            if row.get("path") == source:
                row.update(bytes=actual["bytes"], sha256=actual["sha256"])
                if records:
                    row["newlines"] = actual["records"]
        if source in s["file_counts"]:
            row = s["file_counts"][source]
            row.update(bytes=actual["bytes"], sha256=actual["sha256"])
            if records:
                row["records"] = actual["records"]
        if source in s["manifests"]:
            s["manifests"][source] = dict(text=raw.decode(), sha256=actual["sha256"])
        if name in hashes["files"]:
            hashes["files"][name]["sha256"] = actual["sha256"]
            if records:
                hashes["files"][name]["records"] = actual["records"]
    dump(result / "hashes.json", hashes)
    s["retained"]["hashes.json"] = e.sha(result / "hashes.json")
    digest = hashlib.sha256("".join(f"{name} {row['sha256']}\n" for name, row in sorted(hashes["files"].items())).encode())
    s["files_digest"] = f"{len(hashes['files'])} files, sha256 {digest.hexdigest()}"
    s["run_summary_sha256"] = e.sha(result / "run-summary.json")
    if {"run-config.json", "reach.json"} & set(changed):
        kp = text.with_suffix(".known.json")
        known = e.load(kp)
        known.update(run_config_sha256=e.sha(result / "run-config.json"), reach_sha256=e.sha(result / "reach.json"))
        dump(kp, known)
    write_inventory(ip, rows)
    dump(sp, s)
    seal(text, sp, ip)


def producer(result, edit):
    path = result / (CELL + ".prune.manifest.json")
    manifest = e.load(path)
    edit(manifest)
    dump(path, manifest)


def rebind(manifest, result, name):
    keys = [k for k in manifest["outputs_sha256"] if Path(k).name == name]
    assert keys, name
    for key in keys:
        manifest["outputs_sha256"][key] = e.sha(result / name)


def synthetic_keep(result, text, kept):
    """One certificate/input graph; adjust its keep and dependent count evidence.

    These are synthetic measurement bytes, not a claimed enumeration or a new
    mathematical result. All producer counts/hashes are fixed at the initial
    one-record baseline; dropping the keep refreshes the other measured metadata.
    """
    graph = "V" + "?" * 43 + "\n"
    for suffix in (".g6", ".UNKNOWN.g6"):
        (result / (CELL + suffix)).write_text(graph)
    dump(result / (CELL + ".certs.jsonl"), dict(g6=graph.strip(), verdict="unknown", witness=None))
    (result / (CELL + ".keep.g6")).write_text(graph if kept else "")
    sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
    s, raw, rows = e.load(sp), e.load(result / "run-summary.json"), inventory(ip)
    by_name = {r["path"]: r for r in rows if "path" in r}
    hashes = e.load(result / "hashes.json")

    def measured_claim(name, data):
        row = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), records=data.count(b"\n"))
        by_name[name].update(bytes=row["bytes"], sha256=row["sha256"], newlines=row["records"])
        s["file_counts"][name] = row
        if name in hashes["files"]:
            hashes["files"][name] = dict(sha256=row["sha256"], records=row["records"])

    measured_claim(CELL + ".reach.g6", graph.encode())
    measured_claim("_parents/24-69.g6", graph.encode() if kept else b"")
    shard = next(name for name in by_name if name.startswith("shards/23-64/") and name.endswith(".g6"))
    measured_claim(shard, graph.encode())
    shard = next(name for name in by_name if name.startswith("shards/24-69/") and name.endswith(".g6"))
    new_name = f"shards/24-69/24-69-0-{kept}.g6"
    by_name[shard]["path"] = new_name
    s["file_counts"][new_name] = s["file_counts"].pop(shard)
    for summary in (raw, s["summary"]):
        entry = next(v for v in summary["levels"] if v["n"] == 23)
        entry["children"] = entry["shards"][0]["children"] = 1
        entry["verify"]["records"] = kept
        entry["reach"].update(input=1, kept=1, dropped=0)
        entry["prune"]["counts"].update(input=1, unknown=1, kept=kept, pruned=1-kept, survivors=1, tri_survivors=1)
        entry = next(v for v in summary["levels"] if v["n"] == 24)
        entry["parents"] = entry["parent_sources"][0]["records"] = kept
        entry["shards"][0]["range"] = [0, kept]
    dump(result / "run-summary.json", raw)
    dump(result / "counts.json", [[v["n"], v["m"], v.get("children"), (v.get("prune") or {}).get("counts")]
                                  for v in raw["levels"]])
    verify = e.load(result / "verify/23-64.verify.manifest.json")
    verify.update(records=kept, stage_sha256=e.sha(result / (CELL + ".keep.g6")))
    dump(result / "verify/23-64.verify.manifest.json", verify)
    sm, fp = e.load(result / "replay/summary.json"), e.load(result / "replay/fingerprint.json")
    sm["per_cell"] = [v for v in sm["per_cell"] if v["n"] != 24]
    if kept:
        sm["per_cell"].append(dict(sm["per_cell"][-1], cell="24-69", n=24, m=69, sampled=1, processed=1,
                                   production_children=0, enum2_children=0, parents_in_cell=1, d_values=[5]))
    for stage in sm["stages"]:
        if stage["level"] == [23, 64]:
            assert stage["kind"] == "keep"
            stage.update(input_records=1, records=kept, pruned=1-kept)
    replay_totals(sm, fp)
    dump(result / "replay/summary.json", sm)
    dump(result / "replay/fingerprint.json", fp)
    s["g4"] = fp
    dump(result / "hashes.json", hashes)
    write_inventory(ip, rows)
    dump(sp, s)
    changed = [CELL + suffix for suffix in (".g6", ".keep.g6", ".UNKNOWN.g6", ".certs.jsonl")]
    changed += ["run-summary.json", "counts.json", "verify/23-64.verify.manifest.json",
                "replay/summary.json", "replay/fingerprint.json"]
    if kept:
        def initial(m):
            m["counts"].update(input=1, unknown=1, kept=1, pruned=0, survivors=1, tri_survivors=1)
            for suffix in (".certs.jsonl", ".keep.g6", ".UNKNOWN.g6"):
                rebind(m, result, CELL + suffix)
            m["inputs_sha256"][m["level_file"]] = e.sha(result / (CELL + ".g6"))
            m["verified_counts"].update(records=1, unknown=1, kept=1)
            m["triangles_stats"].update(graphs=1, **{"pass": 1})
            m["embedder"]["survivors"] = 1
            m["checker"] = m["checker"].replace("records=0", "records=1").replace("unknown=0", "unknown=1")
        producer(result, initial)
        changed.append(CELL + ".prune.manifest.json")
        for summary in (raw, s["summary"]):
            entry = next(v for v in summary["levels"] if v["n"] == 23)
            entry["prune"]["checker"] = e.load(result / (CELL + ".prune.manifest.json"))["checker"]
        dump(result / "run-summary.json", raw)
        dump(sp, s)
        stage = e.load(result / (CELL + ".manifest.json"))
        stage.update(children_written=1, children_file_sha256=e.sha(result / (CELL + ".g6")))
        dump(result / (CELL + ".manifest.json"), stage)
        stage = e.load(result / "24-69.manifest.json")
        stage["parent_range"] = [0, 1]
        stage["parent_sources"][0].update(records=1, sha256=e.sha(result / (CELL + ".keep.g6")))
        stage["inputs_sha256"][stage["parent_file"]] = e.sha(result / (CELL + ".keep.g6"))
        dump(result / "24-69.manifest.json", stage)
        verify.update(parents_seen=1)
        verify["parts"][0]["range"] = [0, 1]
        verify["parts"][0]["udenum_stats"]["parents_seen"] = 1
        verify["parts"][0]["udenum_stats"]["parents_degree_skipped"] = 1
        dump(result / "verify/23-64.verify.manifest.json", verify)
        changed += [CELL + ".manifest.json", "24-69.manifest.json"]
    refresh(result, text, changed)


def round2(args, setup, control, accept):
    """Each case has one deliberately false claim and otherwise fresh envelopes."""
    stage, prune, verify = CELL + ".manifest.json", CELL + ".prune.manifest.json", "verify/23-64.verify.manifest.json"
    expanded, _, text = setup("r2-expanded-honest", args.expanded)
    seal(text, text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz"))
    accept(expanded)
    print("G1 GREEN: expanded receipt with refreshed duplicate envelopes accepted", flush=True)

    def manifest_case(name, file, edit, want, source=None, remove_export=False):
        root, result, text = setup("r2-" + name, source)
        if remove_export:
            sp = text.with_suffix(".structure.json")
            s = e.load(sp)
            del s["manifests"][stage]
            dump(sp, s)
        value = e.load(result / file)
        old_checker = value.get("checker")
        edit(value)
        dump(result / file, value)
        changed = [file]
        if file == prune and value.get("checker") != old_checker:
            sp = text.with_suffix(".structure.json")
            s, raw = e.load(sp), e.load(result / "run-summary.json")
            for sm in (raw, s["summary"]):
                next(v for v in sm["levels"] if v["n"] == 23)["prune"]["checker"] = value["checker"]
            dump(sp, s)
            dump(result / "run-summary.json", raw)
            changed.append("run-summary.json")
        refresh(result, text, changed)
        control("r2-" + name, root, want)

    for key, value, want in (
            ("children_written", 777, "COUNTS: 23-64.manifest.json children_written: metadata 777 != checked files 0"),
            ("children_file_sha256", "0" * 64, "RECEIPT: 23-64.manifest.json children_file_sha256 differs from checked files")):
        manifest_case(key, stage, lambda m, k=key, v=value: m.update({k: v}), want)
        # The expanded countercheck is kept honest, including its duplicate byte envelopes.
        manifest_case("export-removed-" + key, stage, lambda m, k=key, v=value: m.update({k: v}),
                      want, expanded, True)
        accept(expanded)
    for remove, want in ((stage, "RECEIPT: retained 23-64.g6 has no stage manifest"),
                         (CELL + ".g6", "RECEIPT: 23-64.manifest.json describes a level file that is not retained")):
        root, result, text = setup("r2-missing-" + remove)
        sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
        s, rows = e.load(sp), inventory(ip)
        (result / remove).unlink()
        del s["retained"][remove]
        if remove in s["file_counts"]:
            s["file_counts"][remove]["bytes"] = 4_000_000
        for row in rows:
            if row.get("path") == remove:
                row["bytes"] = 4_000_000
        write_inventory(ip, rows)
        dump(sp, s)
        seal(text, sp, ip)
        control("r2-missing-" + remove, root, want)

    def replace_nested(keys, value):
        def edit(m):
            for key in keys[:-1]:
                m = m[key]
            m[keys[-1]] = value
        return edit

    for key, value in (("parent_file", "wrong.g6"), ("parent_range", [0, 777])):
        manifest_case(key, stage, lambda m, k=key, v=value: m.update({k: v}),
                      f"RECEIPT: {stage} {key} differs from checked files")
    for key, value in (("exit_status", 1), ("forbidden_set", 74)):
        manifest_case('stage-' + key, stage, lambda m, k=key, v=value: m.update({k: v}),
                      f"RECEIPT: {stage} {key} differs from checked files")
    for key, value in (("enabled", False), ("prune_from", 99), ("prune_filter_only", False),
                       ("triangles", False), ("filter_set", 398)):
        manifest_case('stage-pruning-' + key, stage, replace_nested(['pruning', key], value),
                      f"RECEIPT: {stage} pruning {key} differs from checked files")
    for key, value, want in (
            ("level", [21, 59], f"RECEIPT: {stage} parent stages differs from checked files"),
            ("kind", "full", f"RECEIPT: {stage} parent stages differs from checked files"),
            ("file", "wrong.g6", f"RECEIPT: {stage} parent file differs from checked files"),
            ("d", 777, f"COUNTS: {stage} parent d: metadata 777 != checked files 5"),
            ("records", 777, f"COUNTS: {stage} parent 22-59.keep.g6 records: metadata 777 != checked files 0"),
            ("sha256", "0" * 64, f"RECEIPT: {stage} parent 22-59.keep.g6 sha256 differs from checked files")):
        manifest_case("parent-" + key, stage, replace_nested(["parent_sources", 0, key], value), want)
    for key, value in (("enabled", False), ("k", 777), ("reach_json_sha256", "0" * 64),
                       ("table_level", {"64": 777}), ("table_parent_level", {"59": 777, "60": 3})):
        manifest_case("reach-" + key, stage, replace_nested(["reach", key], value),
                      f"RECEIPT: {stage} reach {key} differs from checked files")
    for file, field, source in ((stage, "inputs_sha256", "reach.json"),
                                (prune, "inputs_sha256", CELL + ".reach.g6")):
        def edit(m, source=source, field=field):
            m[field].update({k: "0" * 64 for k in m[field] if Path(k).name == source})
        manifest_case(file + "-" + field, file, edit,
                      f"RECEIPT: {file} {field} {source} differs from checked files")
    manifest_case("metadata-output-hash", stage, lambda m: m.update(outputs_sha256={"reach.json": "0" * 64}),
                  f"RECEIPT: {stage} outputs_sha256 reach.json differs from checked files")
    manifest_case("level_file", prune, lambda m: m.update(level_file="wrong.g6"),
                  f"RECEIPT: {prune} level_file differs from checked files")
    for key, value in (("target", [24, 70]), ("forbidden_set", 74), ("triangles", False),
                       ("filter_set", 398), ("exit_status", 1), ("problems", ['probe']),
                       ("mutation", {'unknown_as_pruned': True})):
        manifest_case('prune-' + key, prune, lambda m, k=key, v=value: m.update({k: v}),
                      f"RECEIPT: {prune} {key} differs from checked files")
    for field, key, value in (("embedder", "skipped", False), ("embedder", "filter_only", False),
                              ("tu_rule_bound", "n", 23), ("tu_rule_bound", "proved_upper_bound", 70),
                              ("triangles_prover", "witness", 'rhombus')):
        label = field + ' ' + key
        manifest_case(label, prune, replace_nested([field, key], value), f"RECEIPT: {prune} {label} differs from checked files")
    for key, value in (("command", 'false'), ("path", 'wrong.py'), ("from_environment", True)):
        manifest_case('checker-description-' + key, prune, replace_nested(['triangles_checker', key], value),
                      f"RECEIPT: {prune} triangles_checker command differs from checked files")
    manifest_case('checker-result', prune, lambda m: m.update(checker=m['checker'].replace('ACCEPT', 'REJECT', 1)),
                  f"RECEIPT: {prune} checker result differs from checked files")
    for field in ('counts', 'verified_counts'):
        manifest_case(field + '-keys', prune, lambda m, f=field: m[f].update(extra=777),
                      f"RECEIPT: {prune} {field} keys differs from checked files")
    for data_name in ('forbidden-398.json', 'forbidden-74.json', 'tu-gadgets.json'):
        def edit(m, data_name=data_name):
            m['inputs_sha256'].update({k: '0'*64 for k in m['inputs_sha256'] if Path(k).name == data_name})
        manifest_case('data-sha-' + data_name, prune, edit,
                      f"RECEIPT: {prune} inputs_sha256 {data_name} differs from checked files")
    for field, keys in (("counts", ("tu", "survivors", "embedded", "refuted", "tri_tu", "tri_refuted", "tri_survivors", "tri_silent_passes")),
                        ("verified_counts", tuple(e.load(paths(args.source)[0] / prune)["verified_counts"])),
                        ("triangles_stats", ("graphs", "tu", "refuted", "pass")), ("embedder", ("survivors",))):
        for key in keys:
            manifest_case(field + "-" + key, prune, replace_nested([field, key], 777),
                          f"COUNTS: {prune} {field} {key}: metadata 777 != checked files 0")
    manifest_case("triangles_silent_passes", prune, lambda m: m.update(triangles_silent_passes=777),
                  f"COUNTS: {prune} triangles_silent_passes: metadata 777 != checked files 0")
    for key in ("records", "forbidden", "tu", "embedded", "refuted", "unknown", "proof_nodes", "rhombus_tu", "rhombus_refuted", "tri_tu", "tri_refuted"):
        manifest_case("checker-" + key, prune, lambda m, k=key: m.update(checker=m["checker"].replace(k + "=0", k + "=777")),
                      f"COUNTS: {prune} checker {key}: metadata 777 != checked files 0")
    for key, value, want in (("stage_file", "wrong.g6", f"RECEIPT: {verify} stage_file differs from checked files"),
                            ("parents_seen", 777, f"COUNTS: {verify} parents_seen: metadata 777 != checked files 0"),
                            ("parts", [], f"RECEIPT: {verify} parts do not tile checked stage")):
        manifest_case("verify-" + key, verify, lambda m, k=key, v=value: m.update({k: v}), want)
    manifest_case("verify-range", verify, replace_nested(["parts", 0, "range"], [0, 777]),
                  f"RECEIPT: {verify} parts do not tile checked stage")
    manifest_case("verify-part-parents", verify, replace_nested(["parts", 0, "udenum_stats", "parents_seen"], 777),
                  f"COUNTS: {verify} part 0 parents_seen: metadata 777 != checked files 0")
    for key, value in (("kind", 'wrong'), ("level", [23, 65]), ("exit_status", 1), ("forbidden_set", 74),
                       ("check", 'unchecked'), ("udenum_target", [24, 69]), ("forbidden_sha256", '0'*64)):
        manifest_case('verify-identity-' + key, verify, lambda m, k=key, v=value: m.update({k: v}),
                      f"RECEIPT: {verify} {key} differs from checked files")
    for key in ("parents_degree_skipped", "parents_processed", "children_written", "bad_sets", "neighbourhoods",
                "neighbourhood_orbit_reps", "neighbourhoods_bad", "child_orbit_rejected"):
        manifest_case('verify-part-' + key, verify, replace_nested(['parts', 0, 'udenum_stats', key], 777),
                      f"COUNTS: {verify} part 0 {key}: metadata 777 != checked files 0")
    # Bind summary duplicates: the raw summary and structure's normalized summary
    # are separate claims, not two independent measurements.
    for container in ("raw", "structure"):
        fields = [("checker", "ACCEPT certificates records=777", "RECEIPT: 23-64 summary prune checker differs from checked files")]
        fields += [("counts." + key, 777, f"COUNTS: 23-64 prune {key}: metadata 777 != checked files 0")
                   for key in ("tu", "survivors", "embedded", "refuted", "tri_tu", "tri_refuted", "tri_survivors", "tri_silent_passes")]
        fields.append(("verify.parts", 777, "COUNTS: 23-64 summary verify parts: metadata 777 != checked files 1"))
        for field, value, want in fields:
            root, result, text = setup("r2-summary-" + container + "-" + field)
            sp = text.with_suffix(".structure.json")
            s, raw = e.load(sp), e.load(result / "run-summary.json")
            sm = raw if container == "raw" else s["summary"]
            entry = next(v for v in sm["levels"] if v["n"] == 23)
            if field == "verify.parts":
                entry["verify"]["parts"] = value
            elif field == "checker":
                entry["prune"]["checker"] = value
            else:
                entry["prune"]["counts"][field.split('.')[1]] = value
            dump(result / "run-summary.json", raw)
            dump(result / "counts.json", [[v['n'], v['m'], v.get('children'), (v.get('prune') or {}).get('counts')] for v in raw['levels']])
            dump(sp, s)
            refresh(result, text, ["run-summary.json", "counts.json"])
            control("r2-summary-" + container + "-" + field, root, want)
        for field, value in (("forbidden_set", 74), ("prune_filter_set", 398), ("triangles", False),
                             ("verify_stages", False), ("reach.enabled", False), ("prune.prune_filter_only", False)):
            root, result, text = setup('r2-summary-' + container + '-parameter-' + field)
            sp = text.with_suffix('.structure.json')
            s, raw = e.load(sp), e.load(result / 'run-summary.json')
            sm = raw if container == 'raw' else s['summary']
            replace_nested(field.split('.'), value)(sm)
            dump(sp, s)
            dump(result / 'run-summary.json', raw)
            refresh(result, text, ['run-summary.json'])
            label = 'summary ' + field if '.' not in field else ('summary reach enabled' if field == 'reach.enabled' else 'summary prune_filter_only')
            control('r2-summary-' + container + '-parameter-' + field, root, f"RECEIPT: {label} differs from checked files")
        for key in ('builtin', 'value'):
            root, result, text = setup('r2-summary-' + container + '-ubar-' + key)
            sp = text.with_suffix('.structure.json')
            s, raw = e.load(sp), e.load(result / 'run-summary.json')
            sm = raw if container == 'raw' else s['summary']
            sm['ubar_override']['23'][key] = 777
            dump(sp, s)
            dump(result / 'run-summary.json', raw)
            refresh(result, text, ['run-summary.json'])
            control('r2-summary-' + container + '-ubar-' + key, root, 'RECEIPT: summary ubar_override differs from checked files')
    for key in ('builtin', 'value'):
        manifest_case('config-ubar-' + key, 'run-config.json', replace_nested(['ubar_override', '23', key], 777),
                      'RECEIPT: config ubar_override differs from checked files')
    for key in ("bytes", "newlines"):
        root, result, text = setup("r2-inventory-metadata-" + key)
        sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
        s, rows = e.load(sp), inventory(ip)
        name = "reach.json"
        row = next(r for r in rows if r.get("path") == name)
        actual = row[key]
        row[key] += 777
        if name in s['file_counts']:
            s['file_counts'][name]['bytes' if key == 'bytes' else 'records'] += 777
        write_inventory(ip, rows)
        dump(sp, s)
        seal(text, sp, ip)
        want = (f"COUNTS: inventory {name} records: metadata {actual+777} != checked files {actual}" if key == 'newlines'
                else f"RECEIPT: inventory {name} differs from retained bytes")
        control("r2-inventory-metadata-" + key, root, want)
    for label, want in (("inventory", "text inventory bytes"), ("known receipt", "text known receipt bytes"),
                        ("structure receipt", "text structure receipt bytes"),
                        ("level files checked (the runbook's hashes.json rule)", "text level files checked")):
        root, result, text = setup("r2-text-" + label.split()[0])
        lines = text.read_text().splitlines()
        prefix_line = '# ' + label + ': '
        lines = [line.replace(' bytes', '0 bytes', 1) if line.startswith(prefix_line) and 'bytes' in line
                 else (prefix_line + '777 files, sha256 ' + '0'*64 if line.startswith(prefix_line) else line) for line in lines]
        text.write_text('\n'.join(lines) + '\n')
        control("r2-text-" + label, root, f"RECEIPT: {want} differs from checked files")
    for field in ("sha256", "bytes", "prefix"):
        root, result, text = setup("r2-text-inventory-json-" + field)
        lines = text.read_text().splitlines()
        for index, line in enumerate(lines):
            if line.startswith('# inventory:'):
                head, payload = line.split('; ', 1)
                payload = json.loads(payload)
                payload[field] = '0'*64 if field == 'sha256' else (777 if field == 'bytes' else {})
                lines[index] = head + '; ' + json.dumps(payload)
        text.write_text('\n'.join(lines) + '\n')
        control("r2-text-inventory-json-" + field, root, f"RECEIPT: text inventory {field} differs from checked files")
    for key in ("bytes", "sha256"):
        root, result, text = setup("r2-parent-inventory-" + key)
        sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
        s, rows = e.load(sp), inventory(ip)
        name = "_parents/24-69.g6"
        row = next(r for r in rows if r.get('path') == name)
        row[key] = 777 if key == 'bytes' else '0'*64
        s['file_counts'][name][key] = row[key]
        write_inventory(ip, rows)
        dump(sp, s)
        seal(text, sp, ip)
        control("r2-parent-inventory-" + key, root, f"RECEIPT: inventory {name} differs from retained bytes")
    manifest_case("parent-input-sha", "24-69.manifest.json",
                  lambda m: m['inputs_sha256'].update({m['parent_file']: '0'*64}),
                  "RECEIPT: 24-69.manifest.json inputs_sha256 _parents/24-69.g6 differs from checked files")
    root, result, text = setup("r2-export-input-sha", expanded)
    sp, ip = text.with_suffix('.structure.json'), text.with_suffix('.inventory.jsonl.gz')
    s, rows = e.load(sp), inventory(ip)
    name = next(name for name in sorted(s['manifests']) if name.startswith('13-') and '/' not in name)
    m = json.loads(s['manifests'][name]['text'])
    m['inputs_sha256']['reach.json'] = '0'*64
    raw = (json.dumps(m, sort_keys=True) + '\n').encode()
    sha = hashlib.sha256(raw).hexdigest()
    s['manifests'][name] = dict(text=raw.decode(), sha256=sha)
    for row in rows:
        if row.get('path') == name:
            row.update(bytes=len(raw), newlines=raw.count(b'\n'), sha256=sha)
    if name in s['file_counts']:
        s['file_counts'][name] = dict(bytes=len(raw), records=raw.count(b'\n'), sha256=sha)
    write_inventory(ip, rows)
    dump(sp, s)
    seal(text, sp, ip)
    control("r2-export-input-sha", root, f"RECEIPT: export {name} inputs_sha256 reach.json differs from checked files")
    synthetic, result, text = setup('r2-synthetic-certificate-order')
    synthetic_keep(result, text, 1)
    accept(synthetic)
    for suffix in ('.certs.jsonl', '.keep.g6', '.UNKNOWN.g6'):
        root, result, text = setup('r2-certificate-order' + suffix, synthetic)
        path = result / (CELL + suffix)
        path.write_bytes(path.read_bytes().replace(b'?'*43, b'?'*42 + b'@'))
        producer(result, lambda m: rebind(m, result, path.name))
        changed = [path.name, prune]
        if suffix == '.keep.g6':
            m = e.load(result / '24-69.manifest.json')
            m['parent_sources'][0]['sha256'] = e.sha(path)
            m['inputs_sha256'][m['parent_file']] = e.sha(path)
            dump(result / '24-69.manifest.json', m)
            vm = e.load(result / verify)
            vm['stage_sha256'] = e.sha(path)
            dump(result / verify, vm)
            changed += ['24-69.manifest.json', verify]
            sp, ip = text.with_suffix('.structure.json'), text.with_suffix('.inventory.jsonl.gz')
            s, rows = e.load(sp), inventory(ip)
            for row in rows:
                if row.get('path') == '_parents/24-69.g6':
                    row['sha256'] = e.sha(path)
            s['file_counts']['_parents/24-69.g6']['sha256'] = e.sha(path)
            write_inventory(ip, rows)
            dump(sp, s)
        refresh(result, text, changed)
        want = ("RECEIPT: inventory 23-64.reach.g6 differs from retained bytes" if suffix == '.certs.jsonl' else
                f"RECEIPT: retained {CELL + suffix} certificate sha256 differs from checked files")
        control('r2-certificate-order' + suffix, root, want)
        accept(synthetic)
    for label, fields in (("target records from checked files", ("bytes", "records", "sha256")),
                          ("target counts from checked files", tuple(e.load(paths(args.source)[1].with_suffix('.structure.json'))['target_counts']))):
        for field in fields:
            root, result, text = setup("r2-text-target-" + label.split()[1] + '-' + field)
            lines = text.read_text().splitlines()
            for index, line in enumerate(lines):
                if line.startswith('# ' + label + ': '):
                    payload = json.loads(line.split(': ', 1)[1])
                    row = payload['.keep.g6'] if 'records' in label else payload
                    row[field] = '0'*64 if field == 'sha256' else 777
                    lines[index] = '# ' + label + ': ' + json.dumps(payload)
            text.write_text('\n'.join(lines) + '\n')
            want = 'text target records' if 'records' in label else 'text target counts'
            control("r2-text-target-" + label.split()[1] + '-' + field, root, f"RECEIPT: {want} differs from checked files")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=Path("/tmp/u24-fixes-yE1TRr/worker"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--audit-code", type=Path)
    ap.add_argument("--expect-unpatched", action="store_true")
    ap.add_argument("--round2-only", action="store_true", help="only controls newly added after round 1")
    ap.add_argument("--expanded", type=Path, default=Path("/tmp/u24-rereview-fixes-xJ9521/fresh-whole"))
    args = ap.parse_args()
    selected = audit
    if args.audit_code:
        spec = importlib.util.spec_from_file_location("g1_selected_audit", args.audit_code)
        selected = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(selected)
    args.out.mkdir(parents=True, exist_ok=False)
    reports = []

    def accept(root, index=1907, staged=None):
        result, text = paths(root, index)
        s = selected.prepare(result, text, staged) if staged else selected.validate(result, text)
        assert s["result"] == "OK"
        judge.accepted_copy(dict(dir=result, receipt=text, slice=index, tag="fixcheck"), s, text.read_text())

    def green():
        for index in (1907, 1444):
            accept(args.source, index)
        print("G1 GREEN: untouched whole and partial receipts accepted", flush=True)

    def setup(name, source=None):
        root = args.out / name
        shutil.copytree((source or args.source) / "res", root / "res")
        return root, *paths(root)

    def control(name, root, want):
        try:
            accept(root, staged=root / "staged")
        except ValueError as error:
            assert not args.expect_unpatched, (name, "unpatched rejected", str(error))
            assert str(error) == want, (name, want, str(error))
            verdict = str(error)
            print("G1 RED: " + name + ": " + verdict, flush=True)
        else:
            assert args.expect_unpatched, name + ": mutation accepted"
            verdict = "ACCEPTED by prepare and judge.accepted_copy"
            print("G1 UNPATCHED: " + name + ": " + verdict, flush=True)
        green()
        reports.append(dict(control=name, output=verdict, expected_error=want))

    green()
    if args.round2_only:
        round2(args, setup, control, accept)
        dump(args.out / "g1-controls.json", dict(audit_sha256=e.sha(Path(selected.__file__)), unpatched=args.expect_unpatched,
                                               controls=reports))
        print(f"G1 ROUND2 OK: {len(reports)} controls; untouched receipts accepted after each", flush=True)
        return
    for rebound in (False, True):
        name = "certificate-added" + ("-producer-rebound" if rebound else "")
        root, result, text = setup(name)
        assert (result / (CELL + ".certs.jsonl")).read_bytes() == b""
        dump(result / (CELL + ".certs.jsonl"), dict(g6="V" + "?" * 43, verdict="unknown", witness=None))
        changed = [CELL + ".certs.jsonl"]
        if rebound:
            producer(result, lambda m: rebind(m, result, changed[0]))
            changed.append(CELL + ".prune.manifest.json")
        refresh(result, text, changed, records=False)
        control(name, root, "COUNTS: inventory 23-64.certs.jsonl records: metadata 0 != checked files 1")

    for suffix in (".g6", ".keep.g6", ".UNKNOWN.g6"):
        name = "record-added" + suffix
        root, result, text = setup(name)
        path = result / (CELL + suffix)
        assert path.read_bytes() == b""
        path.write_text("V" + "?" * 43 + "\n")
        refresh(result, text, [path.name], records=False)
        if suffix == ".keep.g6":
            verify_name = "verify/23-64.verify.manifest.json"
            verify = e.load(result / verify_name)
            verify["stage_sha256"] = e.sha(path)
            dump(result / verify_name, verify)
            refresh(result, text, [verify_name])
        control(name, root, f"COUNTS: inventory {path.name} records: metadata 0 != checked files 1")

    baseline, result, text = setup("synthetic-one-keep")
    synthetic_keep(result, text, 1)
    accept(baseline)
    print("G1 SYNTHETIC: consistent one-record measurement baseline accepted", flush=True)
    root, result, text = setup("keep-one-short", baseline)
    assert (result / (CELL + ".keep.g6")).read_bytes().count(b"\n") == 1
    synthetic_keep(result, text, 0)
    control("keep-one-short", root,
            "RECEIPT: retained 23-64.keep.g6 sha256 differs from 23-64.prune.manifest.json outputs_sha256")
    accept(baseline)

    cases = [
        ("producer-hash", lambda m: m["outputs_sha256"].update({k: "0" * 64 for k in m["outputs_sha256"]
                                                               if Path(k).name == CELL + ".certs.jsonl"}),
         "RECEIPT: retained 23-64.certs.jsonl sha256 differs from 23-64.prune.manifest.json outputs_sha256"),
        ("producer-input", lambda m: m["counts"].update(input=1),
         "COUNTS: 23-64.prune.manifest.json input: metadata 1 != checked files 0"),
        ("producer-kept", lambda m: m["counts"].update(kept=1),
         "COUNTS: 23-64.prune.manifest.json kept: metadata 1 != checked files 0"),
        ("producer-unknown", lambda m: m["counts"].update(unknown=1),
         "COUNTS: 23-64.prune.manifest.json unknown: metadata 1 != checked files 0"),
        ("producer-pruned", lambda m: m["counts"].update(pruned=1),
         "COUNTS: counts.json 23-64 prune pruned: metadata 0 != checked files 1"),
    ]
    for suffix in (".certs.jsonl", ".keep.g6", ".UNKNOWN.g6"):
        def remove(m, suffix=suffix):
            m["outputs_sha256"] = {k: v for k, v in m["outputs_sha256"].items() if Path(k).name != CELL + suffix}
        cases.append(("unnamed" + suffix, remove, f"RECEIPT: retained {CELL + suffix} has no prune manifest naming it"))
    for name, edit, want in cases:
        root, result, text = setup(name)
        producer(result, edit)
        refresh(result, text, [CELL + ".prune.manifest.json"])
        control(name, root, want)
    root, result, text = setup("other-producer-hash")
    manifest = e.load(result / (CELL + ".manifest.json"))
    manifest["outputs_sha256"] = {CELL + ".certs.jsonl": "0" * 64}
    dump(result / (CELL + ".manifest.json"), manifest)
    refresh(result, text, [CELL + ".manifest.json"])
    control("other-producer-hash", root,
            "RECEIPT: retained 23-64.certs.jsonl sha256 differs from 23-64.manifest.json outputs_sha256")
    round2(args, setup, control, accept)
    dump(args.out / "g1-controls.json", dict(audit_sha256=e.sha(Path(selected.__file__)), unpatched=args.expect_unpatched,
                                           controls=reports))
    print(f"G1 CONTROLS OK: {len(reports)} controls; untouched receipts accepted after each", flush=True)


if __name__ == "__main__":
    main()
