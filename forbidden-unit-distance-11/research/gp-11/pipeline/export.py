"""Self-contained shard replay, exact coverage, and analyst frontier packets."""
from common import *
from contextlib import contextmanager
from itertools import combinations
import gzip
import shutil
import sqlite3
import random
from graph6 import canonicalize, decode_graph6, iter_edges, pair_index, is_connected


@contextmanager
def zipped(path):
    with Path(path).open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as output:
            yield output
        raw.flush()
        os.fsync(raw.fileno())


def analyst_hints(store, gid):
    from late_stage import analyst_hint
    hints = []
    for source, raw in store.db.execute("SELECT source,stages FROM history WHERE gid=? ORDER BY source", (gid,)):
        for row in json.loads(raw):
            if row.get("analyst_hints"):
                hints.append({"stage": row["stage"], "prior_run": source, **row["analyst_hints"]})
    for stage, raw in store.db.execute("SELECT stage,detail FROM attempts WHERE gid=? ORDER BY rowid", (gid,)):
        if stage not in ("esc-branch-refute", "esc-subfield"):
            continue
        detail = json.loads(raw)
        hints.append({"stage": stage, **analyst_hint(detail)})
    return hints


def frontier(store, tu, output):
    unresolved = [gid for gid in sorted(store.assigned) if not store.has(store.poset.codes[gid])]
    path = store.directory / "frontier.sqlite"
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript("PRAGMA cache_size=-8192; PRAGMA temp_store=FILE;"
                     "CREATE TABLE cores(core TEXT,gid INTEGER,removed TEXT,n INTEGER,m INTEGER,PRIMARY KEY(core,gid));")
    with zipped(output / "frontier.jsonl.gz") as stream:
        for number, gid in enumerate(unresolved):
            store.guard.check()
            code = store.poset.codes[gid]
            n, mask = decode_graph6(code)
            edges = list(iter_edges(n, mask))
            degree = [sum(v in edge for edge in edges) for v in range(n)]
            closure = tu.closure(code)
            row = {"id": gid, "g6": code, "edges": edges, "degrees": degree,
                   "degree_sequence": sorted(degree, reverse=True), "tu_closure": closure,
                   "stages_tried": store.unknown_record(gid)["cert"]["budget"]["stages"]}
            row["analyst_hints"] = analyst_hints(store, gid)
            numeric = store.directory / "scratch/numeric" / hashlib.sha256(code.encode()).hexdigest()[:16] / "numeric.json"
            if numeric.exists():
                evidence = json.loads(numeric.read_text())
                row["numeric_evidence_only"] = {key: evidence.get(key) for key in
                    ("coords", "best_gap", "best_residual", "collision_pairs", "starts", "converged")}
            stream.write((compact(row)+"\n").encode())
            for size in (1, 2):
                for removed in combinations(range(n), size):
                    keep = [v for v in range(n) if v not in removed]
                    mapping = {v: i for i, v in enumerate(keep)}
                    small = sum(1 << pair_index(len(keep), mapping[a], mapping[b]) for a, b in edges if a in mapping and b in mapping)
                    if not is_connected(len(keep), small):
                        continue
                    core = canonicalize(len(keep), small)
                    db.execute("INSERT OR IGNORE INTO cores VALUES (?,?,?,?,?)",
                               (core.g6, gid, compact(removed), len(keep), small.bit_count()))
            if number % 100 == 0:
                db.commit()
                from graph6 import _canonicalize_cached
                _canonicalize_cached.cache_clear()
    db.commit()
    db.execute("CREATE INDEX core_group ON cores(core)")
    remaining = set(unresolved)
    count = 0
    with zipped(output / "packets.jsonl.gz") as stream:
        for core, n, m in db.execute("SELECT core,n,m FROM cores GROUP BY core HAVING COUNT(*)>1 ORDER BY n DESC,m DESC,core"):
            members = [(gid, json.loads(removed)) for gid, removed in db.execute("SELECT gid,removed FROM cores WHERE core=? ORDER BY gid", (core,)) if gid in remaining]
            while len(members) >= 2:
                group, members = members[:5], members[5:]
                count += 1
                record = {"id": f"P{count:06d}", "graphs": [store.poset.codes[gid] for gid, _ in group],
                          "ids": [gid for gid, _ in group], "common_connected_induced_core": core,
                          "core_vertices": n, "core_edges": m,
                          "deletions": {store.poset.codes[gid]: removed for gid, removed in group},
                          "independent_certificate_obligations": len(group), "route": "analyst",
                          "grouping_is_a_verdict_equivalence": False}
                record["analyst_hints"] = {store.poset.codes[gid]: analyst_hints(store, gid) for gid, _ in group}
                stream.write((compact(record)+"\n").encode())
                remaining.difference_update(gid for gid, _ in group)
        for gid in sorted(remaining):
            count += 1
            stream.write((compact({"id": f"P{count:06d}", "graphs": [store.poset.codes[gid]], "ids": [gid],
                                   "independent_certificate_obligations": 1, "route": "analyst",
                                   "analyst_hints": {store.poset.codes[gid]: analyst_hints(store, gid)}})+"\n").encode())
    db.close()
    return {"unknown": len(unresolved), "packets": count}


def export(store, tu, output):
    output = Path(output).resolve()
    if output == store.directory or output.is_relative_to(store.directory / "scratch"):
        raise ValueError("export_state_collision")
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").unlink(missing_ok=True)
    store.coverage()
    codes = {store.poset.codes[gid] for gid in store.assigned}
    todo = list(sorted(codes))
    for code in todo:
        row = store.db.execute("SELECT dep FROM accepted WHERE g6=?", (code,)).fetchone()
        if row and row[0] and row[0] not in codes:
            codes.add(row[0])
            todo.append(row[0])
    with tempfile.TemporaryDirectory(prefix="export-", dir=store.directory / "scratch") as temp:
        replay = Path(temp)
        atomic(output / "assigned.g6", "".join(store.poset.codes[gid]+"\n" for gid in sorted(store.assigned)))
        atomic(output / "input.g6", "".join(code+"\n" for code in sorted(codes)))
        atomic(output / "UNKNOWN.g6", "".join(code+"\n" for code in sorted(codes) if not store.has(code)))
        with (replay / "records.jsonl").open("wb") as plain, zipped(output / "records.jsonl.gz") as compressed:
            for code in sorted(codes):
                record = store.record(code)
                if record is None:
                    if code not in store.poset.ids or store.poset.ids[code] not in store.assigned:
                        raise ValueError("export_dependency_missing")
                    record = store.unknown_record(store.poset.ids[code])
                raw = (compact(record)+"\n").encode()
                plain.write(raw)
                compressed.write(raw)
        manifest = {"profile": "sample", "input": "input.g6", "input_sha256": digest(output / "input.g6"),
                    "records": ["records.jsonl"], "forbidden_limit": 9, "derive": False}
        write_json(output / "run.json", manifest)
        write_json(output / "job.json", store.config)
        for name in ("input.g6", "UNKNOWN.g6", "run.json"):
            shutil.copyfile(output / name, replay / name)
        with (replay / "checker.log").open("w") as log:
            report = store.ck.Run(replay, emit=lambda line: log.write(line+"\n")).execute()
        if report["status"] != "ACCEPT":
            write_json(output / "REJECT.json", report)
            raise ValueError("export_checker:" + report.get("reason", "unknown"))
        # The frozen report includes absolute temporary paths; retain them as evidence,
        # while the portable receipt below binds the returned compressed bytes.
        write_json(output / "checker-report.json", report)
        with zipped(output / "checker.log.gz") as target, (replay / "checker.log").open("rb") as source:
            shutil.copyfileobj(source, target)
        record_hash = digest(replay / "records.jsonl")
    packets = frontier(store, tu, output)
    with zipped(output / "attempts.jsonl.gz") as target:
        for gid, stage, value, outcome, reason, budget in store.db.execute(
                "SELECT gid,stage,hash,outcome,reason,budget FROM attempts ORDER BY gid,rowid"):
            target.write((compact({"id": gid, "stage": stage, "record": store.read(value),
                                   "outcome": outcome, "reason": reason, "budget": json.loads(budget)})+"\n").encode())
    summary = {"completed": True, "checker_status": "ACCEPT", "claim_authorized": False,
               "assigned_count": len(store.assigned), "counts": store.counts(), "supporting_records": len(codes)-len(store.assigned),
               "records_sha256": record_hash, "frontier": packets,
               "minimum_available_kib": store.guard.minimum_kib,
               "stage_seconds": {stage: seconds for stage, seconds in store.db.execute("SELECT stage,SUM(seconds) FROM attempts GROUP BY stage")},
               "artifacts": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name not in ("summary.json", "REJECT.json", "metrics.json")}}
    summary["payload_bytes"] = sum((output / name).stat().st_size for name in summary["artifacts"])
    summary["push_ready"] = summary["payload_bytes"] < 45000000
    write_json(output / "summary.json", summary)
    return summary


def replay_bundle(directory, ck, scratch, poset=None):
    directory = Path(directory).resolve()
    summary = json.loads((directory / "summary.json").read_text())
    if not summary.get("completed") or summary.get("checker_status") != "ACCEPT":
        raise ValueError("incomplete_bundle")
    for name, expected in summary["artifacts"].items():
        if Path(name).name != name or digest(directory / name) != expected:
            raise ValueError("bundle_artifact_hash:" + name)
    config = json.loads((directory / "job.json").read_text())
    if config.get("population_sha256") != B11_SHA:
        raise ValueError("bundle_population_hash")
    actual = (directory / "assigned.g6").read_text().splitlines()
    if len(actual) != len(set(actual)) or actual != sorted(actual):
        raise ValueError("shard_coverage")
    if poset is not None:
        expected = [poset.codes[gid] for gid in config["assigned_ids"]]
        if actual != expected:
            raise ValueError("shard_coverage")
        selection = config["selection"]
        if selection["input_sha256"] is None:
            ids = (sorted(random.Random(selection["seed"]).sample(range(len(poset.codes)), selection["sample"]))
                   if selection["sample"] is not None else range(len(poset.codes)))
            expected = [poset.codes[gid] for gid in ids
                        if int.from_bytes(hashlib.sha256(poset.codes[gid].encode()).digest()[:8], "big")
                        % config["shard_count"] == config["shard_index"]]
            if actual != expected:
                raise ValueError("shard_coverage")
        elif config["shard_count"] == 1 and digest(directory / "assigned.g6") != selection["input_sha256"]:
            raise ValueError("shard_coverage")
    with tempfile.TemporaryDirectory(prefix="replay-", dir=scratch) as tmp:
        tmp = Path(tmp)
        for name in ("input.g6", "UNKNOWN.g6", "run.json"):
            shutil.copyfile(directory / name, tmp / name)
        with gzip.open(directory / "records.jsonl.gz", "rb") as source, (tmp / "records.jsonl").open("wb") as target:
            shutil.copyfileobj(source, target, 1024*1024)
        if digest(tmp / "records.jsonl") != summary["records_sha256"]:
            raise ValueError("bundle_record_hash")
        if not set(actual) <= set((tmp / "input.g6").read_text().splitlines()):
            raise ValueError("shard_coverage")
        report = ck.Run(tmp, emit=lambda _: None).execute()
        if report["status"] != "ACCEPT":
            raise ValueError("bundle_checker:" + report["reason"])
        counts = {"embedded": 0, "refuted": 0, "unknown": 0}
        assigned = set(actual)
        with (tmp / "records.jsonl").open() as stream:
            for line in stream:
                record = ck.loads(line)
                if record["g6"] in assigned:
                    counts[record["verdict"]] += 1
        if counts != summary["counts"] or sum(counts.values()) != summary["assigned_count"]:
            raise ValueError("shard_coverage")
    return report
