"""TU proposal generation; ten-vertex endpoints are replayed, never axioms."""
from common import *
import ctypes
import gzip
import sqlite3
from graph6 import canonicalize, decode_graph6, pair_index


class TU:
    def __init__(self, poset):
        self.library = ctypes.CDLL(str(poset.directory / "tu.so"))
        self.library.init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.library.closure.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        data = ROOT / "research/unit-distance-22/data"
        if not self.library.init(str(data / "forbidden-398.json").encode(), str(data / "tu-gadgets.json").encode()):
            raise ValueError("tu_database")
        self.forbidden = []
        for edges in json.loads((data / "forbidden-398.json").read_text()):
            n = 1 + max(max(edge) for edge in edges)
            self.forbidden.append(canonicalize(n, sum(1 << pair_index(n, *edge) for edge in edges)))
        self.refutations = None

    def closure(self, code):
        memory = (ctypes.c_int * 4096)()
        length = self.library.closure(code.encode(), memory, len(memory))
        if length <= 0:
            raise ValueError("tu_engine:" + str(length))
        offset = 1
        steps = []
        n, mask = decode_graph6(code)
        for _ in range(memory[0]):
            if memory[offset] != 2:
                raise ValueError("tu_engine_step")
            index, size = memory[offset+1:offset+3]
            mapping = list(memory[offset+3:offset+3+size])
            pair = sorted(memory[offset+3+size:offset+5+size])
            steps.append({"gadget": index, "map": mapping, "pair": pair})
            mask |= 1 << pair_index(n, *pair)
            offset += 5 + size
        closure = canonicalize(n, mask)
        end = None
        if memory[offset] == 1:
            index, size = memory[offset+1:offset+3]
            mapping = list(memory[offset+3:offset+3+size])
            if index < 74:
                end = {"forbidden": index, "map": mapping}
            else:
                target = self.forbidden[index]
                end = {"refuted": target.g6, "map": [mapping[v] for v in target.new_to_old]}
        return {"steps": steps, "end": end, "g6": closure.g6,
                "old_to_new": list(closure.old_to_new), "fixed_point": end is None}

    def endpoint(self, code, store):
        if store.has(code):
            return
        if self.refutations is None:
            self.refutations = sqlite3.connect(store.directory / "gp10-endpoints.sqlite")
            self.refutations.executescript("PRAGMA cache_size=-4096; CREATE TABLE IF NOT EXISTS records(g6 TEXT PRIMARY KEY,raw TEXT);"
                                          "CREATE TABLE IF NOT EXISTS ready(done INTEGER);")
            if not self.refutations.execute("SELECT 1 FROM ready").fetchone():
                with gzip.open(GP / "cloud/lean3/records.jsonl.gz", "rt") as stream:
                    for line in stream:
                        record = json.loads(line)
                        if record["verdict"] == "refuted":
                            self.refutations.execute("INSERT OR REPLACE INTO records VALUES (?,?)", (record["g6"], line))
                self.refutations.execute("INSERT INTO ready VALUES (1)")
                self.refutations.commit()
        todo = [(code, False)]
        visiting = set()
        while todo:
            current, ready = todo.pop()
            if store.has(current):
                continue
            saved = self.refutations.execute("SELECT raw FROM records WHERE g6=?", (current,)).fetchone()
            if saved is None:
                raise ValueError("tu_endpoint_missing:" + current)
            record = json.loads(saved[0])
            dependency, _ = store.check.verify(record)
            if ready or dependency is None or store.has(dependency):
                store.accept(record, origin="gp10_endpoint")
                visiting.discard(current)
            else:
                if current in visiting:
                    raise ValueError("tu_endpoint_cycle")
                visiting.add(current)
                todo.extend([(current, True), (dependency, False)])

    def propose(self, code, store):
        closure = self.closure(code)
        if closure["steps"] and closure["end"] is None:
            store.db.execute("INSERT OR REPLACE INTO tu_classes VALUES (?,?,?)",
                             (store.poset.ids[code], closure["g6"], compact(closure)))
            transported = self.transport(code, closure, store)
            if transported is not None:
                return transported, closure
        if closure["end"] is None:
            return unknown(code, "tu_no_checked_endpoint", {"fixed_point": True, "steps": len(closure["steps"])}), closure
        if "refuted" in closure["end"]:
            self.endpoint(closure["end"]["refuted"], store)
        if not closure["steps"]:
            raise ValueError("B11_contains_frozen_forbidden")
        return {"g6": code, "verdict": "refuted", "cert": {
            "type": "tu", "steps": closure["steps"], "end": closure["end"]}}, closure

    def transport(self, code, closure, store):
        target = closure["g6"]
        if not store.has(target) and target in store.poset.ids:
            gid = store.poset.ids[target]
            if store.seen[gid] == 2:
                root = store.poset.codes[int(store.roots[gid])]
                store.accept({"g6": target, "verdict": "refuted", "cert": {
                    "type": "sub", "g6": root, "map": store.routes[gid].tolist()}}, "tu_reuse:endpoint")
        if not store.has(target):
            return None
        if store.decided[target] == "embedded":
            return {"g6": code, "verdict": "embedded", "cert": {
                "type": "super", "g6": target, "map": closure["old_to_new"]}}
        return {"g6": code, "verdict": "refuted", "cert": {"type": "tu", "steps": closure["steps"],
                "end": {"refuted": target, "map": [closure["old_to_new"].index(v) for v in range(11)]}}}

    def drain(self, store):
        # Index the reverse TU obligations so each newly reached closure is visited once.
        while store.pending_tu:
            target = store.pending_tu.popleft()
            rows = store.db.execute("SELECT gid,info FROM tu_classes WHERE closure=? ORDER BY gid", (target,)).fetchall()
            for gid, info in rows:
                code = store.poset.codes[gid]
                if store.has(code):
                    continue
                record = self.transport(code, json.loads(info), store)
                if record:
                    store.accept(record, "tu_reuse")
                    store.propagate(code)
