#!/usr/bin/env python3
"""GP-11 certificate workers. See RUNBOOK.txt; no classification claim is made."""
from common import *
import argparse
import gzip
import random
import shutil
import sqlite3
from poset import build, Poset, validate
from store import Store
from stages import POLICIES, run
from tu import TU
from export import export, replay_bundle


def select(poset, args):
    if args.input:
        codes = args.input.read_text().splitlines()
        if codes != sorted(set(codes)) or any(code not in poset.ids for code in codes):
            raise ValueError("input_not_sorted_B11_subset")
        ids = [poset.ids[code] for code in codes]
    elif args.sample:
        ids = sorted(random.Random(args.seed).sample(range(len(poset.codes)), args.sample))
    else:
        ids = list(range(len(poset.codes)))
    return [gid for gid in ids if int.from_bytes(hashlib.sha256(poset.codes[gid].encode()).digest()[:8], "big") % args.shard_count == args.shard_index]


def intake(store, paths, tu):
    # Incoming records have no accepted status until their dependencies and proofs pass.
    db = sqlite3.connect(store.directory / "incoming.sqlite")
    db.executescript("DROP TABLE IF EXISTS incoming; CREATE TABLE incoming(g6 TEXT PRIMARY KEY,raw TEXT,done INTEGER DEFAULT 0);")
    for path in paths:
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt") as stream:
            for line in stream:
                if len(line.encode()) > MAX_RECORD:
                    raise ValueError("record_size_cap")
                record = store.ck.loads(line)
                if record["verdict"] == "unknown":
                    store.verify(record)
                    gid = store.poset.ids.get(record["g6"])
                    stages = record["cert"]["budget"].get("stages")
                    if gid in store.assigned and isinstance(stages, list):
                        identity = hashlib.sha256(compact(record).encode()).hexdigest()
                        store.db.execute("INSERT OR IGNORE INTO history VALUES (?,?,?)", (gid, identity, compact(stages)))
                    continue
                previous = db.execute("SELECT raw FROM incoming WHERE g6=?", (record["g6"],)).fetchone()
                if previous:
                    if json.loads(previous[0])["verdict"] != record["verdict"]:
                        raise store.ck.Rejection("embedded_refuted_conflict", record["g6"])
                    # Stable selection: shortest encoding, then exact bytes.
                    if (len(line), line) >= (len(previous[0]), previous[0]):
                        continue
                db.execute("INSERT OR REPLACE INTO incoming(g6,raw) VALUES (?,?)", (record["g6"], line))
        db.commit()
    while True:
        count = 0
        pending = 0
        for code, raw in db.execute("SELECT g6,raw FROM incoming WHERE done=0 ORDER BY g6"):
            store.guard.check()
            record = store.ck.loads(raw)
            dependency, _ = store.check.verify(record)
            if dependency and not store.has(dependency):
                if not db.execute("SELECT 1 FROM incoming WHERE g6=?", (dependency,)).fetchone():
                    tu.endpoint(dependency, store)
                else:
                    pending += 1
                    continue
            store.accept(record, "intake")
            db.execute("UPDATE incoming SET done=1 WHERE g6=?", (code,))
            count += 1
        db.commit()
        if not pending:
            break
        if not count:
            raise ValueError("intake_dependency_cycle")
    db.close()
    for (code,) in store.db.execute("SELECT g6 FROM accepted WHERE origin!='propagation' ORDER BY seq").fetchall():
        store.propagate(code)
    tu.drain(store)
    store.db.commit()
    store.coverage()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="validate the pinned environment before assigning work")
    pre.add_argument("--scratch", type=Path, required=True)
    b = sub.add_parser("build", help="build the complete B11 deletion order once per worker")
    b.add_argument("--index", type=Path, required=True)
    b.add_argument("--validate", action="store_true")
    r = sub.add_parser("run", help="run or resume one assigned shard")
    r.add_argument("--index", type=Path, required=True)
    r.add_argument("--state", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    r.add_argument("--input", type=Path)
    r.add_argument("--sample", type=int)
    r.add_argument("--seed", type=int, default=20261004)
    r.add_argument("--shard-count", type=int, default=1)
    r.add_argument("--shard-index", type=int, default=0)
    r.add_argument("--policy", choices=POLICIES, default="full")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--bundle", type=Path, action="append", default=[])
    r.add_argument("--records", type=Path, action="append", default=[])
    r.add_argument("--intake-only", action="store_true")
    r.add_argument("--require-complete-union", action="store_true")
    c = sub.add_parser("replay", help="recheck a portable result independently")
    c.add_argument("directory", type=Path)
    c.add_argument("--index", type=Path, required=True)
    c.add_argument("--scratch", type=Path, required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    scratch = (args.state / "scratch") if args.command == "run" else (args.index / "scratch" if args.command == "build" else args.scratch)
    limits(scratch)
    guard = Guard()
    guard.start()
    store = None
    start = time.monotonic()
    try:
        if args.command == "preflight":
            from preflight import run as check_environment
            print(compact(check_environment(scratch)))
            return 0
        if args.command == "build":
            poset = build(args.index, guard)
            if args.validate:
                report = validate(poset, (GP11 / "design/prototypes/sample.g6").read_text().splitlines())
                write_json(args.index / "validation.json", report)
                print(compact(report), flush=True)
            return 0
        poset = Poset(args.index)
        if args.command == "replay":
            print(compact(replay_bundle(args.directory, checker(scratch), scratch, poset)))
            return 0
        if args.input and args.sample or not 0 <= args.shard_index < args.shard_count:
            raise ValueError("selection_parameters")
        assigned = select(poset, args)
        if not assigned:
            raise ValueError("empty_assignment")
        config = {"schema": 1, "population_sha256": B11_SHA, "assigned_ids": assigned,
                  "shard_count": args.shard_count, "shard_index": args.shard_index,
                  "selection": {"input_sha256": digest(args.input) if args.input else None,
                                "sample": args.sample, "seed": args.seed},
                  "policy": args.policy, "stages": [stage.budget() for stage in POLICIES[args.policy]],
                  "sources": source_hashes(), "intake_only": args.intake_only,
                  "inputs": {str(path.resolve()): digest(path) for path in args.records},
                  "bundles": {str(path.resolve()): digest(path / "summary.json") for path in args.bundle}}
        if (args.output / "job.json").exists() and json.loads((args.output / "job.json").read_text()) != config:
            raise ValueError("output_job_mismatch")
        store = Store(args.state, poset, assigned, config, guard, args.resume)
        tu = TU(poset)
        if args.resume:
            store.replay()
        paths = list(args.records)
        union = set()
        for directory in sorted(args.bundle):
            replay_bundle(directory, store.ck, scratch, poset)
            codes = set((directory / "assigned.g6").read_text().splitlines())
            if args.require_complete_union and union & codes:
                raise ValueError("shard_union_duplicate")
            union.update(codes)
            paths.append(directory / "records.jsonl.gz")
        if args.require_complete_union and union != set(poset.codes):
            raise ValueError("shard_union_coverage")
        if paths and not store.db.execute("SELECT 1 FROM completed WHERE stage='intake'").fetchone():
            intake(store, paths, tu)
            store.db.execute("INSERT INTO completed VALUES ('intake')")
            store.db.commit()
        if not args.intake_only:
            run(store, tu, args.policy)
        if source_hashes() != config["sources"]:
            raise ValueError("source_changed_during_run")
        report = export(store, tu, args.output)
        report.update(wall_seconds_this_invocation=time.monotonic()-start,
                      max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        write_json(args.output / "metrics.json", {key: report[key] for key in
                   ("wall_seconds_this_invocation", "max_rss_kib", "minimum_available_kib", "stage_seconds")})
        print(compact(report), flush=True)
        return 0
    except (MemoryFloor, Interrupted) as exc:
        if args.command == "run":
            write_json(args.state / "STOP.json", {"reason": type(exc).__name__, "detail": str(exc),
                                                 "minimum_available_kib": guard.minimum_kib})
        print(compact({"status": "STOP", "reason": type(exc).__name__, "resume": True}), flush=True)
        return 75
    finally:
        guard.stop.set()
        if store:
            store.close()


if __name__ == "__main__":
    sys.exit(main())
