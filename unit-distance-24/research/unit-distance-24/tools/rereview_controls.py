#!/usr/bin/env python3
"""The six ccfce9dc5f rereview reproductions, with resealed envelopes and exact semantic refusals.

No enumeration, git mutation, or red_controls.py execution. Use --worker to also
repeat the real omitted-prune worker reproduction and its restored green run.
All mutations are scratch copies; a passing original is required after every red.
"""
import argparse
import copy
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import sys
from unittest.mock import patch

import evidence as e
import receipt_audit as audit
import worker


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def seal(text, structure, inventory_path):
    body = text.read_text()
    kp = text.with_suffix(".known.json")
    for label, path in (("structure receipt", structure), ("inventory", inventory_path), ("known receipt", kp)):
        body = re.sub(r"^# " + label + r": sha256 [0-9a-f]{64}, \d+ bytes",
                      f"# {label}: sha256 {e.sha(path)}, {path.stat().st_size} bytes", body, flags=re.M)
    # These are duplicate envelopes, not semantic claims. Keep them current when
    # constructing a resealed control; the audit now checks every duplicate.
    rows = inventory(inventory_path)
    def inventory_info(match):
        info = json.loads(match[1])
        info.update(sha256=e.sha(inventory_path), bytes=inventory_path.stat().st_size, prefix=rows[0])
        return "; " + json.dumps(info, sort_keys=True)
    body = re.sub(r"(?<=bytes); (\{.*\})$", inventory_info, body, flags=re.M)
    s = e.load(structure)
    for label, value in (("level files checked (the runbook's hashes.json rule)", s["files_digest"]),
                         ("target records from checked files", json.dumps(s["target_files"], sort_keys=True)),
                         ("target counts from checked files", json.dumps(s["target_counts"], sort_keys=True))):
        body = re.sub(r"^# " + re.escape(label) + r": .*$", lambda _: "# " + label + ": " + value, body, flags=re.M)
    text.write_text(body)
    for label, path in (("structure receipt", structure), ("inventory", inventory_path)):
        assert re.search(r"^# " + label + ": sha256 " + e.sha(path) + ",", body, re.M)


def inventory(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def write_inventory(path, rows):
    with gzip.open(path, "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def replay_totals(sm, fp):
    groups = {}
    keys = ("sampled", "processed", "production_children", "enum2_children", "mismatches")
    for row in sm["per_cell"]:
        group = groups.setdefault(row["n"], dict(n=row["n"], cells=0, parents=0, **{k: 0 for k in keys}))
        group["cells"] += 1
        group["parents"] += row["parents_in_cell"]
        for key in keys:
            group[key] += row[key]
    sm["per_level"] = [groups[n] for n in sorted(groups)]
    for out, inside in (("sampled_parents", "sampled"), ("processed_parents", "processed"),
                        ("production_children_compared", "production_children"), ("enum2_children_compared", "enum2_children"),
                        ("mismatching_parents", "mismatches")):
        sm[out] = sum(row[inside] for row in sm["per_cell"])
    for key in ("sampled_parents", "production_children_compared", "mismatching_parents"):
        fp[key] = sm[key]


def atomic_replace(path, data):
    temp = path.with_name(path.name + ".control-tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def worker_case(source, dest):
    """Same hardlink/rebase reproduction as worker_omission.py, with real checker/control."""
    out, res = dest / "out", dest / "res"
    out.mkdir(parents=True)
    shutil.copytree(source / "res", res)
    shutil.copytree(source / "out/prefix-24-69-L12-tri-pf74", out / "prefix-24-69-L12-tri-pf74", copy_function=os.link)
    shutil.copyfile(source / "out/checked-prefix-24-69-L12-tri-pf74.json", out / "checked-prefix-24-69-L12-tri-pf74.json")
    original = source / "out/dag-24-69-L12-tri-pf74-s1444of1920"
    run = out / original.name
    shutil.copytree(original, run, copy_function=os.link)
    for path in run.rglob("*.json"):
        raw = path.read_bytes()
        new = raw.replace(str(original).encode(), str(run).encode())
        if new != raw:
            atomic_replace(path, new)
    result = res / "24-69-L12-tri-pf74/s1444of1920"
    good = (run / "run-summary.json").read_bytes()

    def sync():
        for path in result.iterdir():
            if path.is_file() and (run / path.name).is_file():
                shutil.copyfile(run / path.name, path)
        for path in run.glob("*.verify.manifest.json"):
            shutil.copyfile(path, result / "verify" / path.name)
        sm = e.load(run / "run-summary.json")
        dump(result / "counts.json", [[v["n"], v["m"], v.get("children"), (v.get("prune") or {}).get("counts")]
                                      for v in sm["levels"]])

    env = dict(TAG="rereview", U23_OUT=str(out), U23_RES=str(res), U24_CHECK_RES=str(res / "check"),
               U23_PUSH="0", U23_TOOLCHAIN="0", U24_KEEP_RUNS="1", U24_SKIP_RUNBOOK="1",
               U24_MIN_AVAILABLE_MB="1536", U24_CHECKER_SHA256=e.sha(worker.CHECKER), PYTHONDONTWRITEBYTECODE="1")
    sm = json.loads(good)
    del next(v for v in sm["levels"] if (v["n"], v["m"]) == (20, 49))["prune"]
    atomic_replace(run / "run-summary.json", (json.dumps(sm) + "\n").encode())
    sync()
    with patch.dict(os.environ, env), patch.object(sys, "argv", ["worker.py", "1444"]):
        assert worker.main() == 7
        rule = "RECORDS: 20-49: required prune record is missing"
        assert e.load(res / "check/s1444of1920-rereview.structure.json")["error"] == rule
        assert run.is_dir() and not (out / "checked-24-69-L12-tri-pf74-s1444of1920.json").exists()
        print("REREVIEW WORKER red: EVIDENCE FAIL: " + rule, flush=True)
        atomic_replace(run / "run-summary.json", good)
        sync()
        assert worker.main() == 0
    # The original whole receipt still anchors this copied prefix. The new receipt
    # must also pass the coordinator, not merely have a worker pass label.
    audit.validate(result, res / "check/s1444of1920-rereview.txt")
    print("REREVIEW WORKER green: real checker, control, evidence audit and receipt audit accept restored 1444", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/tmp/u24-fixes-yE1TRr/worker"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    p, reports = args.source, []

    def green(index=1907):
        if worker.available_mb() < 1536:
            raise RuntimeError("MEMORY STOP: MemAvailable below 1536 MiB")
        got = audit.validate(p / f"res/24-69-L12-tri-pf74/s{index}of1920", p / f"res/check/s{index}of1920-fixcheck.txt")
        assert got["target_files"][".keep.g6"]["records"] == 0
        return got

    def red(name, action, want, index=1907):
        try:
            action()
        except ValueError as error:
            assert str(error) == want, (name, want, str(error))
        else:
            raise AssertionError(name + ": mutation accepted")
        print("REREVIEW red: " + want, flush=True)
        green(index)
        print(f"REREVIEW green: {name}: original {index} receipts pass, measured survivors 0", flush=True)
        reports.append({"control": name, "output": want})

    def setup(name, index=1907):
        root = args.out / name
        shutil.copytree(p / "res", root / "res")
        result = root / f"res/24-69-L12-tri-pf74/s{index}of1920"
        text = root / f"res/check/s{index}of1920-fixcheck.txt"
        return result, text, text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")

    green(); green(1444)
    result, text, sp, ip = setup("false-count")
    s = e.load(sp); s["target_files"][".keep.g6"]["records"] = 777; dump(sp, s)
    rows = inventory(ip)
    next(r for r in rows if r.get("path") == "24-69.keep.g6")["newlines"] = 777
    write_inventory(ip, rows); seal(text, sp, ip)
    red("reported 777 on empty keep", lambda: audit.validate(result, text),
        "COUNTS: inventory 24-69.keep.g6 records: metadata 777 != checked files 0")

    result, text, sp, ip = setup("false-summary")
    s, raw = e.load(sp), e.load(result / "run-summary.json")
    for sm in (raw, s["summary"]):
        row = next(v for v in sm["levels"] if (v["n"], v["m"]) == (24, 69))
        row["children"] = 777
        row["reach"].update(input=777, kept=777, dropped=0)
        row["prune"]["counts"].update(input=777, kept=777, unknown=777, survivors=777, tri_survivors=777)
        row["shards"][0]["children"] = 777
        row["verify"]["records"] = 777
    hashes = e.load(result / "hashes.json")
    for name, row in hashes["files"].items():
        if name.startswith("24-69."):
            row["records"] = 777
    for name, obj in (("run-summary.json", raw), ("hashes.json", hashes),
                      ("counts.json", [[v["n"], v["m"], v.get("children"), (v.get("prune") or {}).get("counts")] for v in raw["levels"]])):
        dump(result / name, obj); s["retained"][name] = e.sha(result / name)
    s["run_summary_sha256"] = e.sha(result / "run-summary.json"); dump(sp, s); seal(text, sp, ip)
    red("summary and hashes claim 777", lambda: audit.validate(result, text),
        "COUNTS: 24-69 children: metadata 777 != checked files 0")

    result, text, sp, ip = setup("null-count")
    s = e.load(sp); s["target_files"][".keep.g6"] = dict(bytes=None, records=None, sha256=None); dump(sp, s)
    write_inventory(ip, [r for r in inventory(ip) if r.get("path") != "24-69.keep.g6"]); seal(text, sp, ip)
    red("null equals missing", lambda: audit.validate(result, text), "RECEIPT: required inventory row missing: 24-69.keep.g6")

    for field in ("bytes", "newlines", "sha256"):
        result, text, sp, ip = setup("untyped-" + field)
        rows = inventory(ip); next(r for r in rows if r.get("path") == "24-69.keep.g6")[field] = None
        write_inventory(ip, rows); seal(text, sp, ip)
        red("untyped inventory " + field, lambda: audit.validate(result, text), "RECEIPT: incomplete or untyped file record: 24-69.keep.g6")

    result, text, sp, ip = setup("duplicate-inventory")
    rows = inventory(ip); rows.append(next(r for r in rows if r.get("path") == "24-69.keep.g6"))
    write_inventory(ip, rows); seal(text, sp, ip)
    red("duplicate inventory", lambda: audit.validate(result, text), "RECEIPT: duplicate inventory path: 24-69.keep.g6")

    result, text, sp, ip = setup("false-hashes-only")
    s, hashes = e.load(sp), e.load(result / "hashes.json")
    hashes["files"]["24-69.keep.g6"]["records"] = 777
    dump(result / "hashes.json", hashes); s["retained"]["hashes.json"] = e.sha(result / "hashes.json")
    dump(sp, s); seal(text, sp, ip)
    red("hashes count independently wrong", lambda: audit.validate(result, text),
        "COUNTS: hashes.json 24-69.keep.g6 records: metadata 777 != checked files 0")

    # Same omitted summary fields as the real worker reproduction, with all graph bytes intact.
    for field in ("prune", "reach", "verify"):
        result, text, sp, ip = setup("missing-" + field, 1444)
        s, raw = e.load(sp), e.load(result / "run-summary.json")
        for sm in (raw, s["summary"]):
            del next(v for v in sm["levels"] if (v["n"], v["m"]) == (20, 49))[field]
        dump(result / "run-summary.json", raw)
        dump(result / "counts.json", [[v["n"], v["m"], v.get("children"), (v.get("prune") or {}).get("counts")] for v in raw["levels"]])
        for name in ("run-summary.json", "counts.json"):
            s["retained"][name] = e.sha(result / name)
        s["run_summary_sha256"] = e.sha(result / "run-summary.json"); dump(sp, s); seal(text, sp, ip)
        want = f"RECORDS: 20-49: required {field} record is missing"
        red("missing " + field, lambda: audit.validate(result, text), want, 1444)
        red("worker missing " + field, lambda: e.requirements(e.load(result / "run-config.json"), raw, e.load(result / "reach.json")), want, 1444)

    raw = e.load(p / "res/24-69-L12-tri-pf74/s1444of1920/run-summary.json")
    raw["levels"] = [v for v in raw["levels"] if (v["n"], v["m"]) != (20, 49)]
    red("missing required cell", lambda: e.requirements(e.load(result / "run-config.json"), raw, e.load(result / "reach.json")),
        "RECORDS: 1 required cell(s) of (24,69) not in run-summary.json: [[20, 49]]", 1444)

    for single in (True, False):
        result, text, sp, ip = setup("g4-one-cell" if single else "g4-small-sample")
        s, sm, fp = e.load(sp), e.load(result / "replay/summary.json"), e.load(result / "replay/fingerprint.json")
        if single:
            sm["per_cell"] = [copy.deepcopy(min(sm["per_cell"], key=lambda r: r["sampled"]))]
            want = "G4: replay cells differ: expected 41 populated cells, got 1; missing ['11-17', '11-18', '11-19'], extra []"
        else:
            sm["per_cell"][0]["sampled"] -= 1
            want = "G4 SCOPE: a full G4 replay whose row of 11-17 has parents 31127, sampled 62 over 4 shards, for 31127 audited parents in 4 shards (the policy samples 63)"
        replay_totals(sm, fp)
        for name, value in (("summary.json", sm), ("fingerprint.json", fp)):
            dump(result / "replay" / name, value); s["retained"]["replay/" + name] = e.sha(result / "replay" / name)
        s["g4"] = fp; dump(sp, s); seal(text, sp, ip)
        red("G4 scope receipt " + str(single), lambda: audit.validate(result, text), want)
        red("G4 scope worker " + str(single), lambda: e.g4(p / "out/dag-24-69-L12-tri-pf74-s1907of1920", result, s), want)

    result, text, sp, ip = setup("false-export", 1444)
    s = e.load(sp); row = next(v for v in s["summary"]["levels"] if (v["n"], v["m"]) == (17, 37))
    assert [r["children"] for r in row["shards"][:2]] == [819, 638]
    row["shards"][0]["children"] -= 1; row["shards"][1]["children"] += 1
    dump(sp, s); seal(text, sp, ip)
    red("compensating resumed shard counts", lambda: audit.validate(result, text),
        "COUNTS: 17-37 shard [0, 10000] children: metadata 818 != checked files 819", 1444)

    for key, value, want in (
            ("parents", 115601, "COUNTS: 17-37 parents: metadata 115601 != checked files 115600"),
            ("parent_sources", [{"kind": "keep", "level": [16, 33], "records": 114558},
                                {"kind": "keep", "level": [16, 34], "records": 1042}],
             "COUNTS: 17-37 parent source [16, 33] records: metadata 114558 != checked files 114557"),
            ("shards", [dict(row["shards"][0], children=819, range=[0, 9999]),
                        dict(row["shards"][1], children=638, range=[9999, 20000]), *row["shards"][2:]],
             "COUNTS: 17-37 shards: metadata differs from checked files")):
        result, text, sp, ip = setup("false-export-" + key, 1444)
        s = e.load(sp)
        next(v for v in s["summary"]["levels"] if (v["n"], v["m"]) == (17, 37))[key] = value
        dump(sp, s); seal(text, sp, ip)
        red("resumed " + key, lambda: audit.validate(result, text), want, 1444)

    result, text, sp, ip = setup("missing-retained")
    s = e.load(sp); del s["retained"]["24-69.certs.jsonl"]; dump(sp, s)
    (result / "24-69.certs.jsonl").unlink(); seal(text, sp, ip)
    red("receipt omits retained certificate", lambda: audit.validate(result, text),
        "RECEIPT: retained file set differs from copy policy: missing ['24-69.certs.jsonl'], extra []")

    root = args.out / "marker-relabel"; (root / "out").mkdir(parents=True); (root / "res").mkdir()
    marker = e.load(p / "out/checked-24-69-L12-tri-pf74-s1907of1920.json")
    marker.update(slice=[12, 1445, 1920], runbook_skipped=False, run=str(root / "out/dag-24-69-L12-tri-pf74-s1445of1920"))
    mp = root / "out/checked-24-69-L12-tri-pf74-s1445of1920.json"; dump(mp, marker)
    with patch.dict(os.environ, {"TAG": "rereview", "U23_OUT": str(root / "out"), "U23_RES": str(root / "res"),
                                "U23_PUSH": "0", "U23_TOOLCHAIN": "0", "U24_KEEP_RUNS": "1", "U24_SKIP_RUNBOOK": "0",
                                "U24_CHECKER_SHA256": e.sha(worker.CHECKER)}), \
            patch.object(sys, "argv", ["worker.py", "1445"]), \
            patch.object(worker, "measured", side_effect=AssertionError("must refuse before enumeration")):
        red("marker reuses another slice", worker.main, "MARKER: receipts do not name requested slice [12, 1445, 1920]")
    assert not Path(marker["run"]).exists()
    for index in (1907, 1444):
        worker.verified_marker(p / f"out/checked-24-69-L12-tri-pf74-s{index}of1920.json", e.sha(worker.CHECKER), False, [12, index, 1920])
    result, text, sp, ip = setup("marker-failed-verdict")
    text.write_text(text.read_text().replace("# u24-worker verdict: pass", "# u24-worker verdict: FAIL"))
    marker = e.load(p / "out/checked-24-69-L12-tri-pf74-s1907of1920.json")
    marker.update(text_receipt=str(text), structure_receipt=str(sp),
                  receipts={str(path): e.sha(path) for path in (text, sp, ip, text.with_suffix(".known.json"))})
    mp = text.parent / "failed-marker.json"; dump(mp, marker)
    red("marker failed verdict", lambda: worker.verified_marker(mp, e.sha(worker.CHECKER), False, [12, 1907, 1920]),
        "MARKER: receipts do not record an accepted verdict for slice [12, 1907, 1920]")
    if args.worker:
        worker_case(p, args.out / "real-worker")
    dump(args.out / "rereview-controls.json", reports)
    print(f"REREVIEW CONTROLS OK: {len(reports)} exact semantic refusals; original evidence passed after every red", flush=True)


if __name__ == "__main__":
    main()
