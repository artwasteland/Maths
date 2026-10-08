#!/usr/bin/env python3
"""Assemble certificate streams by priority, without checking their mathematics.

Usage: lean_assemble11.py [--input INPUT.g6] --out NEW_DIR SEED [SEED ...]
       lean_assemble11.py --check OUT_DIR [--input INPUT.g6]

SEED is a bundle directory, a JSONL file (optionally gzip compressed), or a live
pipeline state directory. State metadata is snapshotted read-only; committed
certificate blobs are read and hash-checked in place, never copied to the spool.
Only graph IDs, verdicts, dependencies and disk offsets survive a record read.
Alternatives live in scratch SQLite; certificate bytes live in a scratch spool.
The first usable decided record wins. Conflicting decided claims are fatal,
including claims outside INPUT. Unparseable lines, malformed record headers and
oversized lines are skipped. A valid decided header is compared for conflicts
before certificate-shape or outside-input filtering.

records.jsonl contains decisions only. A checker manifest must ALSO include
unknown-records.jsonl, and must name hosts.jsonl as its hosts file. The required
fields are supplied in assembly.json; B11 controls remain the caller's job.
Only direct exact embeddings outside INPUT can be hosts. Other outside proofs
cannot be imported under the frozen coverage rule.

--rewrite-outside-ends replaces only refuted TU/sub references to outside
refuted support with an indexed F10 witness. F10 and canonical graph6 codes come
from the frozen B11 Checker. Search is deterministic, bounded and cached by D.
--forbidden-limit (default 10) restricts the rewrite's target profile. Legacy
sample has only F9; use fixture11, limit 10, to replay F10 rewrites on a subset.

--propagate uses the pipeline's read-only cover index, restricted to INPUT and
available exact hosts. It is opt-in; --no-propagate explicitly disables it.
--check checks structure only, never coordinates, maps or refutation identities.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, deque
from contextlib import ExitStack
import gzip
import hashlib
import io
import importlib.util
import json
import math
import mmap
import os
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE.parent / "data/B11.g6"
MAX_LINE = 8 * 1024 * 1024  # Frozen gp10check.py:41,124-129; includes the newline.
VERDICTS = ("unknown", "embedded", "refuted")
PAYLOADS = ("records.jsonl", "UNKNOWN.g6", "unknown-records.jsonl", "hosts.jsonl")


class AssemblyError(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise AssemblyError(reason)


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def unique_keys(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def finite_float(value):
    number = float(value)
    require(math.isfinite(number), "json_constant")
    return number


def parse(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_keys, parse_float=finite_float,
                          parse_constant=lambda _: require(False, "json_constant"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AssemblyError("invalid_json") from exc


def graph_string(code):
    # Canonicalization and graph decoding belong to the final checker.
    require(isinstance(code, str) and bool(code) and not code.startswith(">>")
            and all(63 <= ord(c) <= 126 for c in code), "invalid_graph_string")
    return code


def header(record):
    require(isinstance(record, dict) and set(record) == {"g6", "verdict", "cert"}, "record_schema")
    graph_string(record["g6"])
    require(isinstance(record["verdict"], str) and record["verdict"] in VERDICTS, "invalid_verdict")
    return record["g6"], VERDICTS.index(record["verdict"])


def dependency(record):
    """All graph dependencies returned by frozen Checker.verify():524-606.

    This deliberately does not inspect polynomial rows or tree witness content:
    neither branch asks Run.resolve() to resolve a graph. Unknown certificate
    kinds fail closed. Direct certificate bodies remain the checker's obligation.
    """
    verdict, cert = record["verdict"], record["cert"]
    require(isinstance(cert, dict), "certificate_schema")
    if verdict == "unknown":
        require(set(cert) == {"reason", "budget"} and isinstance(cert["reason"], str)
                and bool(cert["reason"].strip()) and isinstance(cert["budget"], dict), "unknown_schema")
        return None
    kind = cert.get("type")
    require(isinstance(kind, str), "certificate_type")
    if verdict == "embedded":
        if kind == "exact":
            return None
        require(kind == "super", "unsupported_certificate")
        require(set(cert) == {"type", "g6", "map"} and isinstance(cert["map"], list), "pointer_schema")
        return graph_string(cert["g6"])
    if kind in ("tree", "null", "real", "null-dag", "real-dag"):
        return None
    if kind == "sub":
        require({"type", "g6", "map"} <= set(cert) <= {"type", "g6", "map", "index"}
                and isinstance(cert["map"], list), "pointer_schema")
        graph_string(cert["g6"])
        if "index" in cert:
            require(type(cert["index"]) is int, "index_schema")
            return None
        return cert["g6"]
    require(kind == "tu", "unsupported_certificate")
    require(set(cert) == {"type", "steps", "end"} and isinstance(cert["steps"], list)
            and bool(cert["steps"]) and isinstance(cert["end"], dict), "tu_schema")
    end = cert["end"]
    require(isinstance(end.get("map"), list), "tu_end_schema")
    if set(end) == {"forbidden", "map"}:
        require(type(end["forbidden"]) is int, "index_schema")
        return None
    require(set(end) == {"refuted", "map"}, "tu_end_schema")
    return graph_string(end["refuted"])


def bounded_lines(stream):
    """Drain an oversized physical line in bounded pieces, then resume framing."""
    number = 0
    while True:
        raw = stream.readline(MAX_LINE + 1)
        if not raw:
            return
        number += 1
        if len(raw) > MAX_LINE:
            while not raw.endswith(b"\n"):
                raw = stream.readline(MAX_LINE + 1)
                if not raw:
                    break
            yield number, None, "over_line_limit"
        elif not raw.endswith(b"\n") or raw == b"\n":
            yield number, None, "line_format"
        else:
            yield number, raw, None


class HashReader(io.RawIOBase):
    """Hash original bytes below gzip, including skipped physical lines."""
    def __init__(self, stream):
        self.stream = stream
        self.sha = hashlib.sha256()
        self.count = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        count = self.stream.readinto(buffer)
        if count:
            self.sha.update(memoryview(buffer)[:count])
            self.count += count
        return count


class Graphs:
    def __init__(self):
        self.codes, self.ids = [], {}
        self.verdict = bytearray()
        self.first_seed, self.first_line = array("q"), array("q")
        self.first, self.chosen, self.dep = array("q"), array("q"), array("q")

    def intern(self, code):
        found = self.ids.get(code)
        if found is not None:
            return found
        gid = len(self.codes)
        self.codes.append(code)
        self.ids[code] = gid
        self.verdict.append(0)
        for values in (self.first_seed, self.first_line, self.first, self.chosen, self.dep):
            values.append(-1)
        return gid

    def load_input(self, path):
        previous = None
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for number, raw, error in bounded_lines(stream):
                require(not error, f"input_{error}:{path}:{number}")
                try:
                    code = graph_string(raw[:-1].decode("ascii"))
                except UnicodeError as exc:
                    raise AssemblyError("input_non_ascii") from exc
                require(previous is None or previous < code, "input_sorted_unique")
                self.intern(code)
                previous = code
                sha.update(raw)
        self.ninput = len(self.codes)
        return {"path": str(path), "sha256": sha.hexdigest(), "count": self.ninput}


def cycles(chosen, deps):
    """Iterative functional-graph walk. Return cycles and a grounded-node bitmap."""
    color = bytearray(len(chosen))
    grounded = bytearray(len(chosen))
    found = []
    for start in range(len(chosen)):
        if chosen[start] < 0 or color[start]:
            continue
        path, current = [], start
        while current >= 0 and chosen[current] >= 0 and color[current] == 0:
            color[current] = 1
            path.append(current)
            current = deps[current]
        if current >= 0 and color[current] == 1:
            found.append(path[path.index(current):])
        rooted = current < 0 or bool(grounded[current])
        for gid in path:
            color[gid] = 2
            grounded[gid] = rooted
    return found, grounded


class SearchBound(Exception):
    pass


class OutsideEnds:
    """Producer search only. The frozen checker still judges every output map.

    Necessary order/edge/degree filters never reorder F10. The first VF2 witness
    in original index order wins. Node and edge insertion order are sorted.
    A deterministic budget of two million VF2 feasibility attempts per D bounds
    unsuccessful searches; targets above order 64 and cache entries above 10,000
    are refused conservatively. An exhausted search is never called F10-free.
    """
    def __init__(self, limit):
        pinned = Path.home() / "tools/pyenv-gp10/bin/python"
        require(Path(sys.executable) == pinned, "rewrite_requires_pinned_interpreter:" + str(pinned))
        spec = importlib.util.spec_from_file_location("lean11_frozen_wrapper", HERE.parent / "check/gp11check.py")
        self.ck = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.ck
        spec.loader.exec_module(self.ck)
        self.checker = self.ck.Checker(limit)
        self.cache, self.canonical_maps = {}, {}
        self.patterns = [self.ordered(p) for p in self.checker.forbidden]
        self.degrees = [sorted(d for _, d in p.degree()) for p in self.patterns]
        self.stats = Counter()
        self.receipt = {"enabled": True, "forbidden_limit": limit, "choice": "first original F10 index",
                        "max_feasibility_attempts_per_D": 2000000, "max_target_order": 64,
                        "max_cached_targets": 10000, "forbidden_sha256": digest(self.ck.U22 / "data/forbidden-398.json"),
                        "wrapper_sha256": digest(HERE.parent / "check/gp11check.py"),
                        "checker_sha256": digest(self.ck.GP10 / "check/gp10check.py"),
                        "labelg_sha256": digest(self.ck.base.LABELG)}

    def ordered(self, graph):
        result = self.ck.base.nx.Graph()
        result.add_nodes_from(range(graph.n))
        result.add_edges_from(sorted(graph.edges))
        return result

    def find(self, code):
        if code in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[code]
        self.stats["distinct_targets"] += 1
        if len(self.cache) >= 10000:
            return None, "rewrite_cache_bound"
        # Reject large encodings before decode allocates a graph.
        if len(code) > 340:
            answer = None, "rewrite_target_order_bound"
        else:
            graph = self.ck.base.decode(code)
            if graph.n > 64:
                answer = None, "rewrite_target_order_bound"
            else:
                target = self.ordered(graph)
                degrees = sorted(d for _, d in target.degree())
                attempts = [0]

                class Matcher(self.ck.base.nx.algorithms.isomorphism.GraphMatcher):
                    def syntactic_feasibility(self, a, b):
                        attempts[0] += 1
                        if attempts[0] > 2000000:
                            raise SearchBound()
                        return super().syntactic_feasibility(a, b)

                answer = None, "rewrite_no_F10_member"
                try:
                    for idx, pattern in enumerate(self.patterns):
                        n = len(pattern)
                        if (n > graph.n or pattern.number_of_edges() > len(graph.edges)
                                or any(a > b for a, b in zip(self.degrees[idx], degrees[-n:]))):
                            self.stats["prefiltered_patterns"] += 1
                            continue
                        self.stats["searched_patterns"] += 1
                        inverse = next(Matcher(target, pattern).subgraph_monomorphisms_iter(), None)
                        if inverse is not None:
                            phi = [None] * n
                            for vertex, label in inverse.items():
                                phi[label] = vertex
                            answer = (idx, phi), None
                            break
                except SearchBound:
                    answer = None, "rewrite_search_bound"
                self.stats["feasibility_attempts"] += attempts[0]
        self.cache[code] = answer
        if len(self.cache) % 25 == 0:
            print("REWRITE SEARCH " + compact(dict(self.stats)), flush=True)
        return answer

    def rewrite(self, record, target):
        match, error = self.find(target)
        if error:
            return None, {"reason": error}
        idx, phi = match
        try:
            self.checker.in_force(idx)
        except self.ck.base.Rejection as exc:
            raise AssemblyError(f"rewrite_forbidden_not_in_force: D={target} idx={idx} "
                                f"limit={self.checker.forbidden_limit}") from exc
        cert = record["cert"]
        kind = cert["type"]
        old_map = cert["end"]["map"] if kind == "tu" else cert["map"]
        n = self.ck.base.decode(target).n
        if len(old_map) != n or any(type(x) is not int or x < 0 for x in old_map):
            return None, {"reason": "rewrite_endpoint_map_schema"}
        info = {"D": target, "idx": idx, "phi": phi, "rule": "tu_stored" if kind == "tu" else "sub_canonical"}
        if kind == "tu":
            cert["end"] = {"forbidden": idx, "map": [old_map[phi[j]] for j in range(len(phi))]}
        else:
            # canonical_many() / nauty produced the normative code in Checker.
            # The checker exposes no permutation. An isomorphism identifies its
            # canonical labels with stored labels; any automorphism is harmless.
            code = self.checker.forbidden_codes[idx]
            if idx not in self.canonical_maps:
                canonical = self.ordered(self.ck.base.decode(code))
                iso = next(self.ck.base.nx.algorithms.isomorphism.GraphMatcher(
                    canonical, self.patterns[idx]).isomorphisms_iter())
                self.canonical_maps[idx] = [iso[j] for j in range(len(phi))]
            labels = self.canonical_maps[idx]
            cert.clear()
            cert.update(type="sub", g6=code, index=idx, map=[old_map[phi[j]] for j in labels])
            info["canonical_to_stored"] = labels
            info["canonical_g6"] = code
        return record, info


class Assembler:
    def __init__(self, scratch, input_path):
        self.graphs = Graphs()
        self.input = self.graphs.load_input(input_path)
        self.db = sqlite3.connect(scratch / "metadata.sqlite")
        self.db.executescript("""
            PRAGMA cache_size=-8192; PRAGMA temp_store=FILE; PRAGMA journal_mode=OFF;
            CREATE TABLE candidates(id INTEGER PRIMARY KEY, graph INTEGER, seed INTEGER,
                offset INTEGER, size INTEGER, line INTEGER, dep INTEGER,
                external INTEGER DEFAULT 0, hash TEXT);
            CREATE TABLE events(kind TEXT, data TEXT);
            CREATE TABLE snapshots(seed INTEGER, seq INTEGER, g6 TEXT, verdict TEXT,
                hash TEXT, dep TEXT, origin TEXT, offset INTEGER, size INTEGER);
        """)
        self.scratch = scratch
        self.spool = (scratch / "certificates.bin").open("w+b")
        self.external = {}
        self.sources = []
        self.skipped = Counter()
        self.event_counts = Counter()
        self.viable = bytearray()
        self.rewrite_receipt = {"enabled": False}
        self.baseline = None

    def close(self):
        for stream in self.external.values():
            stream.close()
        self.spool.close()
        self.db.close()

    def event(self, kind, value):
        self.event_counts[kind] += 1
        self.db.execute("INSERT INTO events VALUES (?,?)", (kind, compact(value)))

    def skip(self, receipt, number, reason):
        self.skipped[reason] += 1
        receipt["skipped"][reason] += 1
        if len(receipt["skip_examples"]) < 8:
            receipt["skip_examples"].append({"line": number, "reason": reason})

    def location(self, seed, line):
        return f"seed[{seed}] {self.sources[seed]['path']}:{line}" if seed >= 0 else "propagation"

    def source(self, cid):
        if cid < 0:
            return None
        seed, line = self.db.execute("SELECT seed,line FROM candidates WHERE id=?", (cid,)).fetchone()
        return {"seed": seed, "line": line}

    def add(self, gid, seed, line, dep, raw, external=None):
        if external is None:
            self.spool.seek(0, 2)
            offset, expected = self.spool.tell(), None
            self.spool.write(raw)
        else:
            offset, expected = external
        cid = self.db.execute("INSERT INTO candidates(graph,seed,offset,size,line,dep,external,hash) "
                              "VALUES (?,?,?,?,?,?,?,?)",
                              (gid, seed, offset, len(raw), line, dep, external is not None, expected)).lastrowid
        if self.graphs.first[gid] < 0:
            self.graphs.first[gid] = cid
            self.graphs.chosen[gid], self.graphs.dep[gid] = cid, dep
        return cid

    def read_candidate(self, cid):
        seed, offset, size, external, expected = self.db.execute(
            "SELECT seed,offset,size,external,hash FROM candidates WHERE id=?", (cid,)).fetchone()
        stream = self.external[seed] if external else self.spool
        stream.seek(offset)
        raw = stream.read(size)
        require(len(raw) == size and size <= MAX_LINE and raw.endswith(b"\n"), "candidate_framing")
        if external:
            require(hashlib.sha256(raw).hexdigest() == expected, "state_blob_hash_changed")
        return seed, raw

    def ingest_record(self, receipt, number, raw, external=None, state_row=None):
        g, seed = self.graphs, receipt["seed"]
        try:
            record = parse(raw)
            code, verdict = header(record)
        except AssemblyError as exc:
            self.skip(receipt, number, str(exc))
            return
        if not verdict:
            self.skip(receipt, number, "not_decided")
            return
        gid = g.intern(code)
        if g.verdict[gid] and g.verdict[gid] != verdict:
            raise AssemblyError(f"contradiction {code}: {VERDICTS[g.verdict[gid]]} at "
                                f"{self.location(g.first_seed[gid], g.first_line[gid])}; "
                                f"{VERDICTS[verdict]} at {self.location(seed, number)}")
        if not g.verdict[gid]:
            g.verdict[gid], g.first_seed[gid], g.first_line[gid] = verdict, seed, number
        try:
            target = dependency(record)
        except AssemblyError as exc:
            self.skip(receipt, number, str(exc))
            return
        if state_row is not None:
            require((code, VERDICTS[verdict], target) == state_row, "state_record_metadata_mismatch")
        if gid >= g.ninput:
            if verdict == 2:
                self.skip(receipt, number, "outside_refuted")
                return
            if record["cert"]["type"] != "exact":
                self.skip(receipt, number, "outside_non_exact")
                return
        dep = -1 if target is None else g.intern(target)
        self.add(gid, seed, number, dep, raw, external)
        receipt["candidates"] += 1

    def ingest_state(self, directory, receipt):
        """Hold a WAL read transaction only while copying small row metadata.

        No writer API, lock file, backup, checkpoint, or certificate copy. A
        logical snapshot and a committed byte-prefix hash identify the live seed.
        Per-blob hashes are checked both on ingestion and on output reads.
        """
        seed = receipt["seed"]
        path = directory / "state.sqlite"
        blob = directory / "certificates.jsonl"
        metadata = self.scratch / f"seed-{seed}-snapshot.jsonl"
        source = sqlite3.connect(path.as_uri() + "?mode=ro", timeout=10)
        prefix, count, max_seq = 0, 0, 0
        origins = Counter()
        snap_start = time.monotonic()
        try:
            source.execute("PRAGMA query_only=ON")
            source.execute("PRAGMA cache_size=-8192")
            source.execute("BEGIN")
            with metadata.open("wb") as saved:
                rows = source.execute("SELECT a.seq,a.g6,a.verdict,a.hash,a.dep,a.origin,b.offset,b.size "
                                      "FROM accepted a LEFT JOIN blobs b ON b.hash=a.hash ORDER BY a.seq")
                for row in rows:
                    seq, code, verdict, expected, dep, origin, offset, size = row
                    require(type(offset) is int and type(size) is int and offset >= 0 and size > 0,
                            "state_blob_metadata")
                    self.db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)", (seed, *row))
                    saved.write((compact(list(row)) + "\n").encode())
                    origins[origin] += 1
                    count += 1
                    max_seq = seq
                    prefix = max(prefix, offset + size)
        finally:
            source.rollback()
            source.close()
        self.db.commit()
        receipt.update(kind="pipeline_state", database=str(path), path=str(blob), snapshot_rows=count,
                       snapshot_max_seq=max_seq, snapshot_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       snapshot_seconds=round(time.monotonic() - snap_start, 3), origins=dict(origins),
                       snapshot_file=metadata.name, snapshot_sha256=digest(metadata),
                       snapshot_columns=["seq", "g6", "verdict", "hash", "dep", "origin", "offset", "size"],
                       sha256_scope="committed byte prefix [0, bytes); live file can append", bytes=prefix)
        stream = blob.open("rb")
        self.external[seed] = stream
        stat = os.fstat(stream.fileno())
        require(stat.st_size >= prefix, "state_blob_truncated")
        receipt["blob_identity"] = {"device": stat.st_dev, "inode": stat.st_ino}
        hashing = hashlib.sha256()
        left = prefix
        while left:
            raw = stream.read(min(left, 1024 * 1024))
            require(bool(raw), "state_blob_truncated")
            hashing.update(raw)
            left -= len(raw)
        receipt["sha256"] = hashing.hexdigest()
        print("STATE SNAPSHOT " + compact({k: receipt[k] for k in
              ("snapshot_rows", "snapshot_max_seq", "snapshot_utc", "snapshot_seconds", "bytes")}), flush=True)
        for seq, code, verdict, expected, dep, offset, size in self.db.execute(
                "SELECT seq,g6,verdict,hash,dep,offset,size FROM snapshots WHERE seed=? ORDER BY seq", (seed,)):
            receipt["lines"] += 1
            if size > MAX_LINE:
                self.skip(receipt, seq, "over_line_limit")
                continue
            stream.seek(offset)
            raw = stream.read(size)
            require(len(raw) == size and raw.endswith(b"\n") and b"\n" not in raw[:-1], "state_blob_framing")
            require(hashlib.sha256(raw).hexdigest() == expected, "state_blob_hash_changed")
            self.ingest_record(receipt, seq, raw, (offset, expected), (code, verdict, dep))

    def ingest(self, seeds):
        for seed, argument in enumerate(seeds):
            path = argument.resolve()
            state = path.is_dir() and (path / "state.sqlite").is_file() and not any(
                (path / name).exists() for name in ("records.jsonl", "records.jsonl.gz"))
            if path.is_dir():
                # Portable bundles name the compressed stream. Do not trust their summaries.
                if not state:
                    path = path / ("records.jsonl.gz" if (path / "records.jsonl.gz").exists() else "records.jsonl")
            receipt = {"seed": seed, "argument": str(argument), "path": str(path), "lines": 0,
                       "candidates": 0, "skipped": Counter(), "skip_examples": []}
            self.sources.append(receipt)
            if state:
                self.ingest_state(path, receipt)
                self.db.commit()
                continue
            with ExitStack() as stack:
                original = stack.enter_context(path.open("rb"))
                hashing = HashReader(original)
                buffered = stack.enter_context(io.BufferedReader(hashing))
                stream = stack.enter_context(gzip.GzipFile(fileobj=buffered)) if path.suffix == ".gz" else buffered
                for number, raw, error in bounded_lines(stream):
                    receipt["lines"] = number
                    if error:
                        self.skip(receipt, number, error)
                        continue
                    self.ingest_record(receipt, number, raw)
                    raw = None
                receipt.update(sha256=hashing.sha.hexdigest(), bytes=hashing.count)
            self.db.commit()
        self.db.executescript("CREATE INDEX candidate_graph ON candidates(graph,id);"
                              "CREATE INDEX candidate_dep ON candidates(dep,id);")

    def rewrite_outside(self, limit):
        g = self.graphs
        self.baseline = self.reachable()
        rewriter = OutsideEnds(limit)
        self.rewrite_receipt = rewriter.receipt
        # Do not retain a cursor over the dep index while changing that index.
        after = 0
        attempted = 0
        while True:
            row = self.db.execute("SELECT id,graph,dep FROM candidates WHERE id>? AND dep>=? "
                                  "ORDER BY id LIMIT 1", (after, g.ninput)).fetchone()
            if row is None:
                break
            cid, gid, dep = row
            after = cid
            if g.verdict[gid] != 2 or g.verdict[dep] != 2:
                continue
            seed, raw = self.read_candidate(cid)
            record = parse(raw)
            # dependency() has already excluded indexed sub and forbidden TU.
            require(record["cert"]["type"] in ("tu", "sub"), "internal_rewrite_kind")
            attempted += 1
            rewritten, info = rewriter.rewrite(record, g.codes[dep])
            evidence = {"g6": g.codes[gid], "D": g.codes[dep], "candidate": cid,
                        "source": self.source(cid), "original_record_sha256": hashlib.sha256(raw).hexdigest(), **info}
            if rewritten is None:
                self.event("rewrite_failures", evidence)
                print("REWRITE UNRESOLVED " + compact(evidence), file=sys.stderr, flush=True)
                continue
            new = (compact(rewritten) + "\n").encode()
            require(len(new) <= MAX_LINE, "rewrite_line_limit")
            self.spool.seek(0, 2)
            offset = self.spool.tell()
            self.spool.write(new)
            self.db.execute("UPDATE candidates SET offset=?,size=?,dep=-1,external=0,hash=NULL WHERE id=?",
                            (offset, len(new), cid))
            if g.chosen[gid] == cid:
                g.dep[gid] = -1
            self.event("rewrites", {**evidence, "new_record_sha256": hashlib.sha256(new).hexdigest()})
        self.rewrite_receipt.update(attempted_candidates=attempted, **rewriter.stats)
        self.db.commit()

    def options(self, gid):
        return self.db.execute("SELECT id,dep FROM candidates WHERE graph=? ORDER BY id", (gid,))

    def usable(self, gid, dep):
        return dep < 0 or (self.viable[dep] and self.graphs.verdict[gid] == self.graphs.verdict[dep])

    def failure(self, gid, dep):
        g = self.graphs
        if dep < 0:
            return "no_usable_candidate"
        if g.verdict[dep] and g.verdict[gid] != g.verdict[dep]:
            return "dependency_verdict"
        if dep >= g.ninput and g.verdict[dep] == 2:
            return "outside_refuted_support"
        if g.first[dep] < 0:
            return "outside_non_exact_support" if dep >= g.ninput and g.verdict[dep] == 1 else "dependency_missing"
        return "dependency_unrooted"

    def replace(self, gid, cid, dep, reason):
        g = self.graphs
        if g.chosen[gid] != cid:
            self.event("replacements", {"g6": g.codes[gid], "from": self.source(g.chosen[gid]),
                                        "to": self.source(cid), "reason": reason})
        g.chosen[gid], g.dep[gid] = cid, dep

    def escape(self, start, forbidden, grounded):
        """Find a simple rooted path through alternatives, excluding this cycle.

        Iterative DFS tries candidates in priority order. Visiting each graph once
        suffices for reachability, even when an escape needs alternatives in nodes
        outside the original cycle. Nothing is changed until a whole path exists.
        """
        seen = {start}
        # Store the last candidate ID, not a live SQLite cursor per stack frame.
        # Long escape paths must not retain thousands of prepared statements.
        stack = [(start, 0)]
        path = []
        while stack:
            gid, after = stack[-1]
            option = self.db.execute("SELECT id,dep FROM candidates WHERE graph=? AND id>? ORDER BY id LIMIT 1",
                                     (gid, after)).fetchone()
            if option is None:
                stack.pop()
                if path:
                    path.pop()
                continue
            cid, dep = option
            stack[-1] = (gid, cid)
            if not self.usable(gid, dep) or dep in forbidden:
                continue
            if dep < 0 or grounded[dep]:
                return path + [(gid, cid, dep)]
            if dep not in seen:
                seen.add(dep)
                path.append((gid, cid, dep))
                stack.append((dep, 0))
        return None

    def reachable(self):
        g = self.graphs
        viable = bytearray(len(g.codes))
        queue = deque()
        for (gid,) in self.db.execute("SELECT graph FROM candidates WHERE dep=-1 ORDER BY id"):
            if not viable[gid]:
                viable[gid] = 1
                queue.append(gid)
        # A graph is viable iff some same-verdict path in the union of alternatives
        # ends at a direct record (or an eligible exact host).
        while queue:
            target = queue.popleft()
            for (gid,) in self.db.execute("SELECT graph FROM candidates WHERE dep=? ORDER BY id", (target,)):
                if not viable[gid] and g.verdict[gid] == g.verdict[target]:
                    viable[gid] = 1
                    queue.append(gid)
        return viable

    def select(self):
        g = self.graphs
        initial_cycles, _ = cycles(g.chosen, g.dep)
        self.viable = self.reachable()
        for gid in range(len(g.codes)):
            if not self.viable[gid]:
                if g.chosen[gid] >= 0:
                    self.event("unresolved", {"g6": g.codes[gid], "source": self.source(g.chosen[gid]),
                                              "reason": self.failure(gid, g.dep[gid]),
                                              "dependency": g.codes[g.dep[gid]] if g.dep[gid] >= 0 else None})
                g.chosen[gid] = -1
                continue
            for cid, dep in self.options(gid):
                if self.usable(gid, dep):
                    self.replace(gid, cid, dep, self.failure(gid, g.dep[gid]))
                    break
        pending, grounded = cycles(g.chosen, g.dep)
        for cycle in initial_cycles:
            if not self.viable[cycle[0]]:
                self.event("broken_cycles", {"graphs": [g.codes[x] for x in cycle], "action": "omitted"})
        for cycle in pending:
            if any(grounded[x] for x in cycle):
                for gid in cycle:
                    grounded[gid] = 1
                continue
            for member in sorted(cycle):
                path = self.escape(member, set(cycle), grounded)
                if path is not None:
                    for gid, cid, dep in reversed(path):
                        self.replace(gid, cid, dep, "cycle_escape")
                        grounded[gid] = 1
                    for gid in cycle:
                        grounded[gid] = 1
                    self.event("broken_cycles", {"graphs": [g.codes[x] for x in cycle], "action": "replaced",
                                                 "member": g.codes[member]})
                    break
            else:
                raise AssemblyError("internal_escape_failure")
        require(not cycles(g.chosen, g.dep)[0], "internal_cycle")

    def propagate(self, directory):
        g = self.graphs
        with Covers(directory) as covers:
            queue = deque(i for i, cid in enumerate(g.chosen) if cid >= 0 and g.codes[i] in covers.ids)
            generated = 0
            while queue:
                target = queue.popleft()
                verdict = g.verdict[target]
                for code, mapping in covers.neighbours(g.codes[target], verdict):
                    gid = g.ids.get(code)
                    if gid is None or gid >= g.ninput:
                        continue
                    if g.verdict[gid] and g.verdict[gid] != verdict:
                        raise AssemblyError(f"propagation_contradiction {code}: "
                                            f"{self.location(g.first_seed[gid], g.first_line[gid])}; "
                                            f"{VERDICTS[verdict]} from {g.codes[target]}")
                    if g.chosen[gid] >= 0:
                        continue
                    record = {"g6": code, "verdict": VERDICTS[verdict], "cert": {
                        "type": "super" if verdict == 1 else "sub", "g6": g.codes[target], "map": mapping}}
                    raw = (compact(record) + "\n").encode()
                    cid = self.add(gid, -1, 0, target, raw)
                    g.verdict[gid], g.chosen[gid], g.dep[gid] = verdict, cid, target
                    generated += 1
                    queue.append(gid)
            return {"enabled": True, "generated": generated, "index": covers.receipt}

    def emit(self, out, propagation):
        g = self.graphs
        used_hosts = {g.dep[i] for i in range(g.ninput) if g.chosen[i] >= 0 and g.dep[i] >= g.ninput}
        counts = Counter({v: 0 for v in VERDICTS})
        by_seed = [{"seed": i, "embedded": 0, "refuted": 0, "hosts": 0} for i in range(len(self.sources))]
        propagated = Counter()

        def write_record(gid, stream, host=False):
            seed, raw = self.read_candidate(g.chosen[gid])
            stream.write(raw)
            if seed >= 0:
                by_seed[seed]["hosts" if host else VERDICTS[g.verdict[gid]]] += 1
            else:
                propagated[VERDICTS[g.verdict[gid]]] += 1

        with (out / "records.jsonl").open("wb") as records, (out / "UNKNOWN.g6").open("wb") as unknown, \
                (out / "unknown-records.jsonl").open("wb") as unknown_records, (out / "hosts.jsonl").open("wb") as hosts:
            for gid in range(g.ninput):
                if g.chosen[gid] >= 0:
                    counts[VERDICTS[g.verdict[gid]]] += 1
                    write_record(gid, records)
                else:
                    counts["unknown"] += 1
                    unknown.write((g.codes[gid] + "\n").encode("ascii"))
                    reason = self.failure(gid, g.dep[gid]) if g.first[gid] >= 0 else "no_decided_record"
                    record = {"g6": g.codes[gid], "verdict": "unknown", "cert": {
                        "reason": "assembly: " + reason, "budget": {"assembly_only": True}}}
                    unknown_records.write((compact(record) + "\n").encode())
            for gid in sorted(used_hosts, key=lambda i: g.codes[i]):
                require(g.chosen[gid] >= 0 and g.verdict[gid] == 1 and g.dep[gid] < 0, "internal_host")
                write_record(gid, hosts, host=True)
        outputs = list(PAYLOADS)
        for source in self.sources:
            if source.get("kind") == "pipeline_state":
                name = source["snapshot_file"]
                (self.scratch / name).replace(out / name)
                outputs.append(name)
        if self.baseline is not None:
            before, restored = Counter({v: 0 for v in VERDICTS}), Counter()
            for i in range(g.ninput):
                before[VERDICTS[g.verdict[i]] if self.baseline[i] else "unknown"] += 1
                if g.chosen[i] >= 0 and not self.baseline[i]:
                    restored[VERDICTS[g.verdict[i]]] += 1
            selected_rewrites = 0
            for (data,) in self.db.execute("SELECT data FROM events WHERE kind='rewrites'"):
                event = json.loads(data)
                selected_rewrites += g.chosen[g.ids[event["g6"]]] == event["candidate"]
            self.rewrite_receipt.update(baseline_counts=dict(before), restored_by_verdict=dict(restored),
                                        selected_rewrites=selected_rewrites,
                                        restored_scope="same seed snapshot; includes optional propagation if enabled")
        report = {"format": 1, "scope": "structural assembly, certificates unchecked", "input": self.input,
                  "counts": dict(counts), "hosts": len(used_hosts), "by_source_seed": by_seed,
                  "propagated_verdicts": dict(propagated), "propagation": propagation,
                  "rewrite_outside_ends": self.rewrite_receipt,
                  "seeds": self.sources, "skipped_lines": dict(self.skipped), "event_counts": dict(self.event_counts),
                  "event_stage": "Seed selection, before optional propagation; unresolved seeds may later be propagated.",
                  "unused_candidates": self.db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
                                       - (g.ninput - counts["unknown"] + len(used_hosts)),
                  "outside_input_policy": "Only needed direct exact embedded hosts; refuted and non-exact support omitted.",
                  "outputs": {name: {"sha256": digest(out / name), "bytes": (out / name).stat().st_size} for name in outputs},
                  "hash_scope": "Payload hashes here; assembly.json hash in assembly.json.sha256. The checksum receipt is not self-hashed.",
                  "run_fields": {"input": self.input["path"], "input_sha256": self.input["sha256"],
                                 "records": ["records.jsonl", "unknown-records.jsonl"],
                                 "hosts": "hosts.jsonl", "unknown": "UNKNOWN.g6"}}
        # Events can be numerous on a population run. Serialize from SQLite, not a list.
        with (out / "assembly.json").open("w") as stream:
            stream.write(compact(report)[:-1])
            for kind in ("replacements", "broken_cycles", "unresolved", "rewrites", "rewrite_failures"):
                stream.write("," + json.dumps(kind) + ":[")
                separator = ""
                for (data,) in self.db.execute("SELECT data FROM events WHERE kind=? ORDER BY rowid", (kind,)):
                    if kind in ("rewrites", "rewrite_failures"):
                        event = json.loads(data)
                        event["selected"] = g.chosen[g.ids[event["g6"]]] == event["candidate"]
                        data = compact(event)
                    stream.write(separator + data)
                    separator = ","
                stream.write("]")
            stream.write("}\n")
        (out / "assembly.json.sha256").write_text(digest(out / "assembly.json") + "  assembly.json\n")
        return {"input": g.ninput, **counts, "hosts": len(used_hosts), **self.event_counts}


class Covers:
    """The pipeline/poset.py packed 19-byte rows, opened without producer imports."""
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.stack = ExitStack()

    def __enter__(self):
        try:
            manifest_path = self.directory / "index.json"
            manifest = json.loads(manifest_path.read_text())
            require(digest(DEFAULT_INPUT) == manifest["population_sha256"], "index_population_hash")
            self.codes = DEFAULT_INPUT.read_text().splitlines()
            self.ids = {code: i for i, code in enumerate(self.codes)}
            require(len(self.codes) == manifest["vertices"], "index_vertex_count")
            self.maps = {}
            consumed = {"index.json": digest(manifest_path)}
            for name in ("relations.bin", "down.u32", "up.u32", "reverse.u32"):
                path = self.directory / name
                consumed[name] = digest(path)
                require(consumed[name] == manifest["files"][name], "index_artifact_hash:" + name)
                stream = self.stack.enter_context(path.open("rb"))
                self.maps[name] = self.stack.enter_context(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
            n, m = len(self.codes), manifest["relations"]
            for name, size in (("relations.bin", 19 * m), ("down.u32", 4 * (n + 1)),
                               ("up.u32", 4 * (n + 1)), ("reverse.u32", 4 * m)):
                require(len(self.maps[name]) == size, "index_size:" + name)
            self.receipt = {"path": str(self.directory), "sha256": consumed,
                            "population_sha256": manifest["population_sha256"]}
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def neighbours(self, code, verdict):
        gid = self.ids[code]
        offsets = self.maps["down.u32" if verdict == 1 else "up.u32"]
        start, stop = struct.unpack_from("<II", offsets, gid * 4)
        for i in range(start, stop):
            row = i if verdict == 1 else struct.unpack_from("<I", self.maps["reverse.u32"], i * 4)[0]
            parent, child, *mapping = struct.unpack_from("<II11B", self.maps["relations.bin"], row * 19)
            require((parent if verdict == 1 else child) == gid, "index_adjacency")
            yield self.codes[child if verdict == 1 else parent], mapping


def structural_check(out, input_path):
    g = Graphs()
    g.load_input(input_path)
    counts = Counter({v: 0 for v in VERDICTS})
    previous_input = -1
    for name, host in (("records.jsonl", False), ("hosts.jsonl", True)):
        with (out / name).open("rb") as stream:
            for number, raw, error in bounded_lines(stream):
                require(not error, f"{error}:{name}:{number}")
                record = parse(raw)
                code, verdict = header(record)
                require(verdict != 0, "decision_required:" + code)
                gid = g.intern(code)
                require((gid >= g.ninput) == host, "host_input_overlap" if host else "outside_input_record")
                require(g.chosen[gid] < 0, "duplicate_record:" + code)
                if not host:
                    require(gid > previous_input, "record_input_order:" + code)
                    previous_input = gid
                dep = dependency(record)
                if host:
                    require(verdict == 1 and record["cert"]["type"] == "exact", "host_not_exact:" + code)
                g.chosen[gid], g.verdict[gid] = number, verdict
                g.dep[gid] = -1 if dep is None else g.intern(dep)
                if not host:
                    counts[VERDICTS[verdict]] += 1
                record = raw = None
    for gid, cid in enumerate(g.chosen):
        if cid < 0 or g.dep[gid] < 0:
            continue
        target = g.dep[gid]
        require(g.chosen[target] >= 0, "dependency_missing:" + g.codes[gid] + ":" + g.codes[target])
        require(g.verdict[gid] == g.verdict[target], "dependency_verdict:" + g.codes[gid])
    found, _ = cycles(g.chosen, g.dep)
    require(not found, "dependency_cycle:" + (",".join(g.codes[i] for i in found[0][:20]) if found else ""))
    for name in ("UNKNOWN.g6", "unknown-records.jsonl"):
        expected = (g.codes[i] for i in range(g.ninput) if g.chosen[i] < 0)
        with (out / name).open("rb") as stream:
            for number, raw, error in bounded_lines(stream):
                require(not error, f"{error}:{name}:{number}")
                if name == "UNKNOWN.g6":
                    code = raw[:-1].decode("ascii")
                    counts["unknown"] += 1
                else:
                    record = parse(raw)
                    code, verdict = header(record)
                    require(verdict == 0, "unknown_verdict:" + code)
                    dependency(record)
                require(code == next(expected, None), "unknown_exactness:" + name)
            require(next(expected, None) is None, "unknown_exactness:" + name)
    return {"input": g.ninput, **counts,
            "hosts": sum(g.chosen[i] >= 0 for i in range(g.ninput, len(g.codes)))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="defaults to frozen B11.g6 in both modes")
    parser.add_argument("--out", type=Path, help="new or empty output directory")
    parser.add_argument("--check", type=Path, metavar="OUT_DIR")
    propagation = parser.add_mutually_exclusive_group()
    propagation.add_argument("--propagate", dest="propagate", action="store_true", help="use B11 cover index (opt-in)")
    propagation.add_argument("--no-propagate", dest="propagate", action="store_false")
    parser.set_defaults(propagate=False)
    parser.add_argument("--index", type=Path, default=Path("/tmp/gp11-index"))
    parser.add_argument("--rewrite-outside-ends", action="store_true", help="replace outside TU/sub ends by F10 witnesses")
    parser.add_argument("--forbidden-limit", type=int, choices=range(11), default=10,
                        help="rewrite target limit, B11/fixture11 default 10; legacy sample cannot use F10")
    parser.add_argument("--scratch", type=Path, help="scratch parent, defaults to system temporary directory")
    parser.add_argument("seeds", nargs="*", type=Path)
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        if args.check:
            require(not args.out and not args.seeds and not args.propagate and not args.rewrite_outside_ends,
                    "check_arguments")
            counts = structural_check(args.check, args.input.resolve())
            print("STRUCTURE OK " + compact({**counts, "seconds": round(time.monotonic() - started, 3)}))
        else:
            require(args.out is not None and bool(args.seeds), "require_out_and_seeds")
            out = args.out.resolve()
            require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "output_not_empty")
            out.parent.mkdir(parents=True, exist_ok=True)
            # Build privately. A contradiction or interruption does not publish partial output.
            with tempfile.TemporaryDirectory(prefix="lean11-stage-", dir=out.parent) as staging, \
                    tempfile.TemporaryDirectory(prefix="lean11-scratch-", dir=args.scratch) as scratch:
                assembler = Assembler(Path(scratch), (args.input or DEFAULT_INPUT).resolve())
                try:
                    assembler.ingest(args.seeds)
                    if args.rewrite_outside_ends:
                        assembler.rewrite_outside(args.forbidden_limit)
                    assembler.select()
                    prop = assembler.propagate(args.index) if args.propagate else {"enabled": False, "generated": 0}
                    counts = assembler.emit(Path(staging), prop)
                finally:
                    assembler.close()
                Path(staging).replace(out)
            print("ASSEMBLY WRITTEN " + compact({**counts, "seconds": round(time.monotonic() - started, 3)}))
        return 0
    except (AssemblyError, OSError, ValueError, KeyError, TypeError, sqlite3.Error, EOFError) as exc:
        print(("STRUCTURE ERROR " if args.check else "ASSEMBLY ERROR ") + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
