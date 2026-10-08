"""Transactional scheduler and a hash-addressed, append-only certificate file."""
from common import *
from collections import deque
import fcntl
import sqlite3
import numpy as np


class Store:
    def __init__(self, directory, poset, assigned, config, guard, resume=False):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = (self.directory / ".lock").open("a")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.poset = poset
        self.guard = guard
        self.assigned = set(assigned)
        self.ck = checker(self.directory / "scratch/check")
        self.check = self.ck.Checker(9)
        self.config = config
        manifest = self.directory / "job.json"
        if manifest.exists():
            if not resume:
                raise ValueError("resume_required")
            if json.loads(manifest.read_text()) != config:
                raise ValueError("resume_input_source_or_budget_changed")
        else:
            write_json(manifest, config)
        self.db = sqlite3.connect(self.directory / "state.sqlite")
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          PRAGMA synchronous=FULL;
          PRAGMA cache_size=-16384;
          PRAGMA temp_store=FILE;
          CREATE TABLE IF NOT EXISTS blobs(hash TEXT PRIMARY KEY, offset INTEGER, size INTEGER);
          CREATE TABLE IF NOT EXISTS accepted(seq INTEGER PRIMARY KEY, g6 TEXT UNIQUE,
            verdict TEXT, hash TEXT, dep TEXT, origin TEXT);
          CREATE TABLE IF NOT EXISTS assigned(gid INTEGER PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS attempts(gid INTEGER, stage TEXT, hash TEXT,
            outcome TEXT, reason TEXT, budget TEXT, seconds REAL, detail TEXT,
            PRIMARY KEY(gid,stage));
          CREATE TABLE IF NOT EXISTS leases(gid INTEGER, stage TEXT, token TEXT UNIQUE,
            deadline REAL, generation INTEGER, PRIMARY KEY(gid,stage));
          CREATE TABLE IF NOT EXISTS lease_events(token TEXT PRIMARY KEY, reason TEXT);
          CREATE TABLE IF NOT EXISTS completed(stage TEXT PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS tu_classes(gid INTEGER PRIMARY KEY,closure TEXT,info TEXT);
          CREATE INDEX IF NOT EXISTS tu_closure_index ON tu_classes(closure);
          CREATE TABLE IF NOT EXISTS history(gid INTEGER,source TEXT,stages TEXT,PRIMARY KEY(gid,source));
          CREATE INDEX IF NOT EXISTS accepted_dependency ON accepted(dep);
        """)
        previous = {row[0] for row in self.db.execute("SELECT gid FROM assigned")}
        if previous and previous != self.assigned:
            raise ValueError("shard_assignment_changed")
        self.db.executemany("INSERT OR IGNORE INTO assigned VALUES (?)", ((gid,) for gid in sorted(self.assigned)))
        self.db.commit()
        self.stream = (self.directory / "certificates.jsonl").open("a+b")
        end = self.db.execute("SELECT COALESCE(MAX(offset+size),0) FROM blobs").fetchone()[0]
        self.stream.seek(0, os.SEEK_END)
        if self.stream.tell() < end:
            raise ValueError("certificate_store_truncated")
        # A killed writer may leave bytes that no committed transaction references.
        self.stream.truncate(end)
        self.stream.flush()
        self.seen = np.zeros(len(poset.codes), dtype="u1")
        self.routes = np.zeros((len(poset.codes), 11), dtype="u1")
        self.roots = np.full(len(poset.codes), -1, dtype="i4")
        self.pending_tu = deque()
        self.decided = {row[0]: row[1] for row in self.db.execute("SELECT g6,verdict FROM accepted")}
        self.scope_counts = self._count_scope()
        # Re-read and hash every retained byte on resume; a receipt never repairs corruption.
        for (value,) in self.db.execute("SELECT hash FROM blobs"):
            self.read(value)
        self.requeue_all()

    def close(self):
        self.stream.close()
        self.db.close()
        self.lock.close()

    def read(self, value):
        row = self.db.execute("SELECT offset,size FROM blobs WHERE hash=?", (value,)).fetchone()
        if row is None:
            raise ValueError("certificate_hash_missing")
        self.stream.seek(row[0])
        raw = self.stream.read(row[1])
        if hashlib.sha256(raw).hexdigest() != value:
            raise ValueError("certificate_hash_mismatch")
        return self.ck.loads(raw)

    def append(self, record):
        raw = (compact(record) + "\n").encode()
        if len(raw) > MAX_RECORD:
            raise ValueError("record_size_cap")
        value = hashlib.sha256(raw).hexdigest()
        if self.db.execute("SELECT 1 FROM blobs WHERE hash=?", (value,)).fetchone():
            return value
        self.stream.seek(0, os.SEEK_END)
        offset = self.stream.tell()
        self.stream.write(raw)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.db.execute("INSERT INTO blobs VALUES (?,?,?)", (value, offset, len(raw)))
        return value

    def has(self, code):
        return code in self.decided

    def record(self, code):
        row = self.db.execute("SELECT hash FROM accepted WHERE g6=?", (code,)).fetchone()
        return self.read(row[0]) if row else None

    def verify(self, record):
        self.guard.check()
        if len((compact(record)+"\n").encode()) > MAX_RECORD:
            raise ValueError("record_size_cap")
        if record["g6"] in self.decided and record["verdict"] not in ("unknown", self.decided[record["g6"]]):
            raise self.ck.Rejection("embedded_refuted_conflict", record["g6"])
        # B11's exact bytes are pinned and canonicality was established at G0.
        if record["g6"] not in self.poset.ids:
            self.ck.check_canonical([record["g6"]])
        dependency, _ = self.check.verify(record)
        if dependency is not None:
            self.ck.need(dependency in self.decided, "pointer_target_missing", dependency)
            self.ck.need(self.decided[dependency] == record["verdict"],
                         "pointer_target_not_accepted_" + record["verdict"], dependency)
        return dependency

    def accept(self, record, origin):
        dependency = self.verify(record)
        return self._insert(record, origin, dependency)

    def _insert(self, record, origin, dependency):
        if record["verdict"] == "unknown":
            return None
        if self.has(record["g6"]):
            return self.db.execute("SELECT hash FROM accepted WHERE g6=?", (record["g6"],)).fetchone()[0]
        value = self.append(record)
        self.db.execute("INSERT INTO accepted(g6,verdict,hash,dep,origin) VALUES (?,?,?,?,?)",
                        (record["g6"], record["verdict"], value, dependency, origin))
        self.db.commit()
        self.decided[record["g6"]] = record["verdict"]
        if self.poset.ids.get(record["g6"]) in self.assigned:
            self.scope_counts["unknown"] -= 1
            self.scope_counts[record["verdict"]] += 1
        return value

    def finish(self, gid, stage, token, record, budget, seconds, detail):
        row = self.db.execute("SELECT token FROM leases WHERE gid=? AND stage=?", (gid, stage)).fetchone()
        if row != (token,):
            raise ValueError("stale_lease")
        if record["g6"] != self.poset.codes[gid]:
            raise ValueError("task_graph_mismatch")
        dependency = self.verify(record)
        reason = record["cert"].get("reason", "verified")
        encoded_budget = compact(budget)
        encoded_detail = compact(detail)
        new = record["verdict"] != "unknown" and not self.has(record["g6"])
        try:
            value = self.append(record)
            if new:
                self.db.execute("INSERT INTO accepted(g6,verdict,hash,dep,origin) VALUES (?,?,?,?,?)",
                                (record["g6"], record["verdict"], value, dependency, stage))
            self.db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",
                            (gid, stage, value, record["verdict"], reason, encoded_budget, seconds, encoded_detail))
            self.db.execute("DELETE FROM leases WHERE gid=? AND stage=?", (gid, stage))
            # A decision and its attempt must survive together, including a kill
            # between inserting the certificate and clearing its lease.
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        if new:
            self.decided[record["g6"]] = record["verdict"]
            self.scope_counts["unknown"] -= 1
            self.scope_counts[record["verdict"]] += 1

    def lease(self, gid, stage, seconds):
        self.expire()
        if self.db.execute("SELECT 1 FROM attempts WHERE gid=? AND stage=?", (gid, stage)).fetchone():
            raise ValueError("task_already_complete")
        if self.db.execute("SELECT 1 FROM leases WHERE gid=? AND stage=?", (gid, stage)).fetchone():
            raise ValueError("task_already_leased")
        generation = self.db.execute("SELECT COUNT(*) FROM lease_events").fetchone()[0]
        token = hashlib.sha256(f"{gid}:{stage}:{generation}".encode()).hexdigest()
        self.db.execute("INSERT INTO leases VALUES (?,?,?,?,?)", (gid, stage, token, time.time()+seconds, generation))
        self.db.commit()
        return token

    def expire(self, all_leases=False):
        query = "SELECT token FROM leases" + ("" if all_leases else " WHERE deadline<=?")
        rows = self.db.execute(query, () if all_leases else (time.time(),)).fetchall()
        for (token,) in rows:
            self.db.execute("INSERT OR IGNORE INTO lease_events VALUES (?,?)", (token, "requeued"))
            self.db.execute("DELETE FROM leases WHERE token=?", (token,))
        self.db.commit()
        return len(rows)

    def requeue_all(self):
        # The exclusive directory lock proves the previous local owner has gone.
        return self.expire(all_leases=True)

    def propagate(self, code):
        if code not in self.poset.ids:
            return
        root = self.poset.ids[code]
        verdict = self.decided[code]
        flag = 1 if verdict == "embedded" else 2
        if self.seen[root]:
            if self.seen[root] != flag:
                raise self.ck.Rejection("embedded_refuted_conflict", code)
            return
        self.seen[root] = flag
        self.roots[root] = root
        self.routes[root] = np.arange(11)
        if flag == 2:
            self.pending_tu.append(code)
        todo = deque([root])
        count = 0
        while todo:
            parent = todo.popleft()
            old_map = self.routes[parent].tolist()
            for child, mapping in self.poset.neighbours(parent, verdict):
                if self.seen[child]:
                    if self.seen[child] != flag:
                        raise self.ck.Rejection("embedded_refuted_conflict", self.poset.codes[child])
                    continue
                # Downward: child -> parent -> root. Upward: root -> child -> parent.
                composed = [old_map[v] for v in mapping] if flag == 1 else [mapping[v] for v in old_map]
                self.routes[child] = composed
                self.roots[child] = root
                self.seen[child] = flag
                if flag == 2:
                    self.pending_tu.append(self.poset.codes[child])
                todo.append(child)
                if child in self.assigned:
                    record = {"g6": self.poset.codes[child], "verdict": verdict,
                              "cert": {"type": "super" if flag == 1 else "sub", "g6": code, "map": composed}}
                    # Unassigned reach is a scheduling hint. Only this check creates a decision.
                    if self.has(record["g6"]):
                        if self.decided[record["g6"]] != verdict:
                            raise self.ck.Rejection("embedded_refuted_conflict", record["g6"])
                    else:
                        self.accept(record, "propagation")
            count += 1
            if count % 1024 == 0:
                self.guard.check()

    def replay(self):
        # The accepted dependency graph was committed in topological order.
        rows = self.db.execute("SELECT g6,hash,origin FROM accepted ORDER BY seq").fetchall()
        original = self.decided
        self.decided = {}
        for code, value, _ in rows:
            record = self.read(value)
            self.verify(record)
            self.decided[code] = record["verdict"]
        if self.decided != original:
            raise ValueError("accepted_index_mismatch")
        for code, _, origin in rows:
            if origin != "propagation":
                self.propagate(code)

    def order(self, stage, direction="down"):
        done = {row[0] for row in self.db.execute("SELECT gid FROM attempts WHERE stage=?", (stage,))}
        remaining = [gid for gid in self.assigned if gid not in done and not self.has(self.poset.codes[gid])]
        return sorted(remaining, key=lambda gid: ((-1 if direction == "down" else 1)*int(self.poset.edges[gid]), gid))

    def counts(self):
        return dict(self.scope_counts)

    def _count_scope(self):
        values = {"embedded": 0, "refuted": 0, "unknown": 0}
        for gid in self.assigned:
            values[self.decided.get(self.poset.codes[gid], "unknown")] += 1
        return values

    def unknown_record(self, gid):
        stages = []
        for source, raw in self.db.execute("SELECT source,stages FROM history WHERE gid=? ORDER BY source", (gid,)):
            stages.extend(dict(row, prior_run=source) for row in json.loads(raw))
        stages += [{"stage": stage, "outcome": outcome, "reason": reason, "budget": json.loads(budget)}
                  for stage, outcome, reason, budget in self.db.execute(
                      "SELECT stage,outcome,reason,budget FROM attempts WHERE gid=? ORDER BY rowid", (gid,))]
        return unknown(self.poset.codes[gid], "stages_exhausted" if stages else "not_attempted",
                       {"stages": stages, "policy": self.config["policy"]})

    def coverage(self):
        rows = {row[0] for row in self.db.execute("SELECT gid FROM assigned")}
        if rows != self.assigned or self.counts() != self._count_scope() or sum(self.counts().values()) != len(rows):
            raise ValueError("shard_coverage")
        return self.counts()
