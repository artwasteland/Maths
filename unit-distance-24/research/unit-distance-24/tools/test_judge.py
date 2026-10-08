#!/usr/bin/env python3
"""Rule-specific fleet controls made from the retained whole/partial receipts.

Run with the maths Python and --out NEW_DIRECTORY. Heavy work is sequential;
the outer worker.measured guard stops the process group below 1536 MiB available.
Every red is followed by a full re-judgement of the unchanged honest fleet.
No checker, receipt audit, prediction, or fleet rule is mocked.
"""
import argparse
import copy
from contextlib import redirect_stderr, redirect_stdout
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
import judge
import evidence as e
import receipt_audit
import worker


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def measurement(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "records": raw.count(b"\n")}


def bundle(root, branch="legacy", index=1444, tag="fixcheck"):
    base = root / branch / judge.SUB
    return base / judge.KIND / f"s{index}of1920", base / "check" / f"s{index}of1920-{tag}.txt"


def seal(result, text, false_zero=False):
    """Refresh all hash envelopes, not semantic claims. No wrong-control hash failures."""
    sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
    structure = e.load(sp)
    with gzip.open(ip, "rt") as stream:
        header = json.loads(next(stream))
        rows = {r["path"]: r for r in map(json.loads, stream)}
    def reach_envelopes(manifest):
        reach_sha = e.sha(result / "reach.json")
        for key in manifest.get("inputs_sha256", {}):
            if Path(key).name == "reach.json":
                manifest["inputs_sha256"][key] = reach_sha
        if "reach_json_sha256" in manifest.get("reach", {}):
            manifest["reach"]["reach_json_sha256"] = reach_sha
    for path in result.glob("*.manifest.json"):
        manifest = e.load(path)
        reach_envelopes(manifest)
        dump(path, manifest)
    for name, row in structure["manifests"].items():
        manifest = json.loads(row["text"])
        reach_envelopes(manifest)
        if (result / name).is_file():
            row["text"] = (result / name).read_text()
        else:
            row["text"] = json.dumps(manifest, sort_keys=True) + "\n"
        raw = row["text"].encode()
        m = measurement(raw)
        row["sha256"] = m["sha256"]
        rows[name] = dict(path=name, bytes=m["bytes"], sha256=m["sha256"], newlines=m["records"])
        if name in structure["file_counts"]:
            structure["file_counts"][name] = m
    for path in result.rglob("*"):
        if not path.is_file() or "history" in path.relative_to(result).parts:
            continue
        name = path.relative_to(result).as_posix()
        raw, source = path.read_bytes(), path.name if name.startswith("verify/") else name
        m = measurement(raw)
        structure["retained"][name] = m["sha256"]
        if source in rows:
            rows[source] = dict(path=source, bytes=m["bytes"], sha256=m["sha256"], newlines=m["records"])
        if source in structure["file_counts"]:
            structure["file_counts"][source] = m
    structure["run_summary_sha256"] = e.sha(result / "run-summary.json")
    structure["g4"] = e.load(result / "replay/fingerprint.json")
    hashes = e.load(result / "hashes.json")["files"]
    digest = hashlib.sha256("".join(f"{name} {row['sha256']}\n" for name, row in sorted(hashes.items())).encode()).hexdigest()
    structure["files_digest"] = f"{len(hashes)} files, sha256 {digest}"
    if false_zero:
        rows["24-69.keep.g6"]["newlines"] = 0
        structure["file_counts"]["24-69.keep.g6"]["records"] = 0
        structure["target_files"][".keep.g6"] = dict(measurement((result / "24-69.keep.g6").read_bytes()), records=0)
    with gzip.open(ip, "wt") as stream:
        for row in [header, *rows.values()]:
            stream.write(json.dumps(row) + "\n")
    kp = text.with_suffix(".known.json")
    known = e.load(kp)
    known["reach_sha256"] = e.sha(result / "reach.json")
    known["run_config_sha256"] = e.sha(result / "run-config.json")
    dump(kp, known)
    dump(sp, structure)
    body = text.read_text()
    for label, path in (("structure receipt", sp), ("inventory", ip), ("known receipt", kp)):
        body = re.sub(r"^# " + label + r": sha256 [0-9a-f]{64},", "# " + label + ": sha256 " + e.sha(path) + ",", body, flags=re.M)
    text.write_text(body)
    from rereview_controls import seal as seal_envelopes
    seal_envelopes(text, sp, ip)


def relabel(root, old, new):
    """Synthetic whole receipt under another slice identity, with every binding resealed.

    The graph bytes stay those of the source. This is deliberately false partition
    evidence; only the independently predicted Engel membership should expose it.
    """
    result, text = bundle(root, index=old)
    def rewrite(value):
        if isinstance(value, str):
            return value.replace(f"s{old}of1920", f"s{new}of1920").replace(f".slice-{old}-of-1920", f".slice-{new}-of-1920")
        if isinstance(value, list):
            if value == [12, old, 1920]:
                return [12, new, 1920]
            if value == [old, 1920]:
                return [new, 1920]
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {rewrite(k): rewrite(v) for k, v in value.items()}
        return value
    for path in result.rglob("*.json"):
        dump(path, rewrite(e.load(path)))
    sp, ip = text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz")
    structure = rewrite(e.load(sp))
    for row in structure["manifests"].values():
        row["text"] = json.dumps(rewrite(json.loads(row["text"]))) + "\n"
    dump(sp, structure)
    kp = text.with_suffix(".known.json")
    dump(kp, rewrite(e.load(kp)))
    with gzip.open(ip, "rt") as stream:
        rows = [rewrite(json.loads(line)) for line in stream]
    with gzip.open(ip, "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    lines = []
    for line in text.read_text().splitlines():
        lines.append(json.dumps(rewrite(json.loads(line))) if line.startswith("{") else rewrite(line))
    text.write_text("\n".join(lines) + "\n")
    new_result = result.with_name(f"s{new}of1920")
    result.rename(new_result)
    for suffix in judge.SUFFIXES:
        path = text.with_suffix(suffix)
        path.rename(path.with_name(path.name.replace(f"s{old}of1920", f"s{new}of1920")))
    new_text = text.with_name(text.name.replace(f"s{old}of1920", f"s{new}of1920"))
    # The G4 policy includes the run name in its seed. Keep this synthetic
    # receipt's red controls in that new sample, so G4 does not mask KNOWN.
    scope = e.fleet_judge()
    draw = scope.policy_sample()
    sm = e.load(new_result / "replay/summary.json")
    entries = {f"{v['n']}-{v['m']}": v for v in structure["summary"]["levels"]}
    for red in sm["red_controls"]:
        cell = red["cell"]
        entry = entries[cell]
        sampled = draw(sm["seed"], f"dag-{judge.KIND}-s{new}of1920", cell, entry["parents"],
                       sm["fraction"], sm["min_per_shard"], sm["whole_max"], sm["max_per_shard"],
                       list(scope.ranges_of(entry["shards"])))
        red["index"] = min(sampled)
    dump(new_result / "replay/summary.json", sm)
    dump(new_result / "replay/red.json", sm["red_controls"])
    seal(new_result, new_text)
    return new_result, new_text


def run(out, legacy, expanded):
    fleet = out / "honest"
    for branch, source in (("legacy", legacy), ("expanded", expanded)):
        shutil.copytree(source, fleet / branch / judge.SUB)
        # Older expanded controls resealed SHA256 but left duplicate sizes stale.
        # Repair only those envelopes in this private copy, before its green check.
        from rereview_controls import seal as seal_envelopes
        for index in (1907, 1444):
            _, text = bundle(fleet, branch=branch, index=index)
            seal_envelopes(text, text.with_suffix(".structure.json"), text.with_suffix(".inventory.jsonl.gz"))
    plan = {"job": "u24-two-slice-control", "target": [24, 69], "slice_level": 12, "count": 1920,
            "slices": [1907, 1444], "tasks": {"fixcheck": [1907, 1444]}}
    dump(out / "plan.json", plan)
    reports = []
    def evaluate(root=fleet, p=plan):
        with tempfile.TemporaryDirectory(prefix="audit-", dir=out) as tmp:
            return judge.judge(root, p, Path(tmp))
    original = evaluate()
    assert original["verdict"] == "OK", original["problems"]
    assert original["accepted_copies"] == 4 and len(original["duplicates"]) == 2
    assert original["summary"]["status"] == "per-slice OK" and not original["survivors"]
    dump(out / "honest.json", original)
    (out / "honest.log").write_text(judge.render(original) + "\n")
    print(judge.render(original), flush=True)
    def green(name):
        r = evaluate()
        assert r == original, (name, r["problems"])
        print(f"GREEN: {name}: original JUDGE OK restored (4 accepted copies)", flush=True)
    def record(name, messages):
        for message in messages:
            print(f"RED: {message}", flush=True)
        reports.append({"control": name, "messages": messages})
        green(name)
    def clone(name):
        return Path(shutil.copytree(fleet, out / name))

    p = copy.deepcopy(plan)
    p["tasks"]["fixcheck"].remove(1444)
    want = "PLAN: tasks do not cover the declared slices exactly once; missing [1444], extra []"
    try:
        evaluate(p=p)
    except ValueError as error:
        assert str(error) == want, error
    else:
        raise AssertionError("bad plan accepted")
    record("plan coverage", [want])

    missing = clone("missing")
    for branch in ("legacy", "expanded"):
        d, t = bundle(missing, branch)
        shutil.rmtree(d)
        for suffix in judge.SUFFIXES:
            t.with_suffix(suffix).unlink()
    r = evaluate(missing)
    want = "COVERAGE: slice 1444: no accepted copy"
    assert r["verdict"] == "PARTIAL" and r["exit"] == 3 and want in r["pending"] and not r["problems"], r
    record("absent evidence is partial", [want])

    # 2026-10-01 (judge follow-up 2): a bare result directory beside an accepted copy of the same slice is
    # reported as unreceipted, not pending (killed cloud workers leave these); its survivors are still read.
    bare = "legacy/research/unit-distance-24/results/u24/24-69-L12-tri-pf74/s1444of1920"
    unreceipted = clone("unreceipted-copy")
    d, t = bundle(unreceipted)
    for suffix in judge.SUFFIXES:
        t.with_suffix(suffix).unlink()
    r = evaluate(unreceipted)
    assert (r["verdict"] == "OK" and r["accepted_copies"] == 3 and not r["missing"] and not r["pending"]
            and [u["copy"] for u in r["unreceipted"]] == [bare]), r
    print(f"OK: unreceipted duplicate reported, not pending ({bare})", flush=True)
    hidden = clone("unreceipted-survivor")
    d, t = bundle(hidden)
    for suffix in judge.SUFFIXES:
        t.with_suffix(suffix).unlink()
    graph = (Path(__file__).resolve().parents[1] / "fixtures/nonempty24/24-69.g6").read_bytes()
    (d / "24-69.keep.g6").write_bytes(graph)
    r = evaluate(hidden)
    want = f"TARGET: survivor in a non-accepted copy only: slice 1444: graph6 {graph.decode().strip()}"
    assert r["verdict"] == "FAIL" and want in r["problems"], r["problems"]
    record("survivor in an unreceipted copy only", [want])

    different = clone("different-count")
    d, t = bundle(different)
    sm, st = e.load(d / "run-summary.json"), e.load(t.with_suffix(".structure.json"))
    for summary in (sm, st["summary"]):
        next(v for v in summary["levels"] if (v["n"], v["m"]) == (17, 37))["prune"]["counts"]["tri_silent_passes"] += 1
    dump(d / "run-summary.json", sm)
    dump(d / "counts.json", [[v["n"], v["m"], v.get("children"), (v.get("prune") or {}).get("counts")] for v in sm["levels"]])
    dump(t.with_suffix(".structure.json"), st)
    seal(d, t)
    receipt_audit.validate(d, t)  # essential: both contradictory copies are accepted
    r = evaluate(different)
    want = ("COPIES: slice 1444: accepted copies disagree on counts "
            "(expanded/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt, "
            "legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)")
    assert r["verdict"] == "FAIL" and r["accepted_copies"] == 4 and r["problems"] == [want], r["problems"]
    record("accepted copies disagree", [want])

    borrowed = clone("borrowed-prefix")
    first, ft = bundle(borrowed, index=1907)
    for suffix in judge.SUFFIXES:
        src = ft.with_suffix(suffix)
        shutil.copyfile(src, src.with_name(src.name.replace("fixcheck", "borrowed")))
    bt = ft.with_name(ft.name.replace("fixcheck", "borrowed"))
    bt.write_text(bt.read_text().replace("# u24-worker fixcheck,", "# u24-worker borrowed,"))
    d, t = bundle(borrowed)
    st = e.load(t.with_suffix(".structure.json"))
    st["prefix_receipt"]["name"] = "s1907of1920-borrowed.structure.json"
    dump(t.with_suffix(".structure.json"), st)
    seal(d, t)
    receipt_audit.validate(d, t)  # the old receipt audit permits this cross-worker binding
    r = evaluate(borrowed)
    want = ("REJECTED: slice 1444: PREFIX: slice 1444: later slice is not bound to a whole check of worker fixcheck "
            "(legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)")
    assert r["verdict"] == "FAIL" and want in r["problems"], r["problems"]
    record("same-worker whole binding", [want])

    # A small predicted slice makes the missing-control output readable. The
    # locally computed prediction is unmodified, not a test-provided expected map.
    cells, predicted = judge.reference()
    dest_index = min((i for i in predicted if predicted[i]), key=lambda i: (len(predicted[i]), i))
    known_fleet = clone("missing-known")
    shutil.rmtree(known_fleet / "expanded")
    d, t = bundle(known_fleet)
    shutil.rmtree(d)
    for suffix in judge.SUFFIXES:
        t.with_suffix(suffix).unlink()
    d, t = relabel(known_fleet, 1907, dest_index)
    receipt_audit.validate(d, t)
    known_plan = dict(plan, slices=[dest_index], tasks={"fixcheck": [dest_index]})
    r = evaluate(known_fleet, known_plan)
    wants = [f"KNOWN: slice {dest_index}: missing predicted Engel graph ({n},{m}) #{index}" for n, m, index in sorted(predicted[dest_index])]
    assert r["verdict"] == "FAIL" and r["accepted_copies"] == 1 and r["problems"] == wants, r["problems"]
    record("predicted graph absent", wants)

    false_zero = clone("false-zero")
    d, t = bundle(false_zero)
    graph = (Path(__file__).resolve().parents[1] / "fixtures/nonempty24/24-69.g6").read_bytes()
    (d / "24-69.keep.g6").write_bytes(graph)
    hj = e.load(d / "hashes.json")
    hj["files"]["24-69.keep.g6"]["sha256"] = hashlib.sha256(graph).hexdigest()
    dump(d / "hashes.json", hj)
    seal(d, t, false_zero=True)
    r = evaluate(false_zero)
    want = ("REJECTED: slice 1444: COUNTS: inventory 24-69.keep.g6 records: metadata 0 != checked files 1 "
            "(legacy/research/unit-distance-24/results/u24/check/s1444of1920-fixcheck.txt)")
    assert r["verdict"] == "FAIL" and want in r["problems"], r["problems"]
    assert r["survivors"][0]["graph6"] == graph.decode().strip() and r["survivors"][0]["slices"] == [1444]
    line, = [line for line in judge.render(r).splitlines() if line.startswith("SURVIVOR:")]
    record("false zero exposes survivor", [want, line])

    # Direct cost checks use real pushed timings, including an unfinished copy.
    sample, baseline = e.load(judge.PILOT), e.load(judge.BASELINE)
    d, t = bundle(fleet)
    c = {"dir": d, "receipt": t, "worker": "unfinished", "accepted": False}
    random_index = sample["random"][0]
    cost = judge.cost_report({random_index: [c]}, baseline, sample)
    empty = judge.cost_report({}, baseline, sample)
    timed = cost["chosen"][str(random_index)]
    assert timed["lower_bound"] and cost["estimates"]["step"]["lower_bound"]
    assert abs(cost["estimates"]["step"]["T24_seconds"] - empty["estimates"]["step"]["T24_seconds"] - 1910/32 * timed["step_seconds"]) < 1e-6
    assert abs(cost["overheads"]["check"]["weighted_seconds"] - 1910/32 * timed["check_seconds"]) < 1e-6
    assert cost["projected_multiplier"] is None
    pilot_expected = sum(len(predicted[i]) for i in judge.plan_check(sample))
    assert pilot_expected == 82582, pilot_expected
    print("COST OK: matched definitions; unfinished and absent lower bounds; 1910/32 overhead; no ratio of bounds", flush=True)
    print("KNOWN PREDICTION OK: pilot 82582; whole fleet 97912, each once", flush=True)
    green("cost and pilot predictions")

    # Exercise the reused fleet-control partition boundary independently of the
    # per-slice predicted-membership rule (which also rejects wrong placement).
    one = e.load(bundle(fleet, index=1907)[1].with_suffix(".known.json"))
    two = copy.deepcopy(one)
    two["slice"][1] = 1444
    for receipt in (one, two):
        for stage in receipt["cells"]["16-35"]["files"].values():
            stage.update(records=1, indices=[84])
    partition = judge.known.fleet_control([one, two], cells)
    want = "PARTITION 16-35: eligible Engel index 84 kept in slices 1907 and 1444"
    assert partition["result"] == "FAIL" and partition["problems"] == [want], partition
    record("fleet-control partition boundary", [want])

    # The actual argument parser, JSON writer, renderer and return codes, with
    # the already-running real memory guard and already-computed prediction.
    for name, root, code in (("ok", fleet, 0), ("partial", missing, 3), ("fail", different, 1)):
        saved = sys.argv
        output = io.StringIO()
        try:
            sys.argv = [str(Path(judge.__file__)), str(root), "--plan", str(out / "plan.json"),
                        "--out", str(out / f"cli-{name}.json"), "--guarded"]
            with redirect_stdout(output), redirect_stderr(output):
                actual = judge.main()
        finally:
            sys.argv = saved
        (out / f"cli-{name}.log").write_text(output.getvalue())
        assert actual == code and e.load(out / f"cli-{name}.json")["exit"] == code, output.getvalue()
        assert output.getvalue().splitlines()[-1] == "JUDGE " + name.upper(), output.getvalue()
        print(f"CLI OK: {name}: exit {code}; JSON and final verdict agree", flush=True)
    bad_plan = copy.deepcopy(plan)
    bad_plan["tasks"]["fixcheck"].remove(1444)
    dump(out / "bad-plan.json", bad_plan)
    dump(out / "cli-bad-plan.json", original)
    saved, output = sys.argv, io.StringIO()
    try:
        sys.argv = [str(Path(judge.__file__)), str(fleet), "--plan", str(out / "bad-plan.json"),
                    "--out", str(out / "cli-bad-plan.json"), "--guarded"]
        with redirect_stdout(output), redirect_stderr(output):
            code = judge.main()
    finally:
        sys.argv = saved
    assert code == 1 and e.load(out / "cli-bad-plan.json")["verdict"] == "FAIL", output.getvalue()
    print("CLI OK: setup error replaces stale OK JSON with FAIL", flush=True)
    green("CLI exits and reports")
    dump(out / "controls.json", reports)
    print(f"JUDGE CONTROLS OK: {len(reports)} exact controls, honest fleet rechecked after each", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--legacy", type=Path, default=Path("/tmp/u24-fixes-yE1TRr/worker/res"))
    ap.add_argument("--expanded", type=Path, default=Path("/tmp/u24-rereview-fixes-xJ9521/fresh-whole/res"))
    ap.add_argument("--guarded", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if not a.guarded:
        a.out.mkdir(parents=True, exist_ok=False)
        os.environ["U24_MIN_AVAILABLE_MB"] = "1536"
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--out", str(a.out.resolve()),
                   "--legacy", str(a.legacy.resolve()), "--expanded", str(a.expanded.resolve()), "--guarded"]
        measured = worker.measured(command, a.out / "controls.log", timed=True)
        dump(a.out / "measurement.json", measured)
        print((a.out / "controls.log").read_text())
        print(json.dumps(measured))
        return measured["exit"]
    run(a.out, a.legacy, a.expanded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
