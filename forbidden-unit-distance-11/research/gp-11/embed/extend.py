#!/usr/bin/env python3
"""Extend frozen exact GP-10 embeddings by a degree-two vertex.

Only ordinary E-exact certificates leave this producer. Missing block
embeddings and exhausted placements are UNKNOWN, not nonexistence proofs.
Run with the frozen GP-10 Python; see EXTEND-RUNBOOK.md for sharding/resume.
"""
from __future__ import annotations

import ast
from collections import Counter
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["SYMPY_GROUND_TYPES"] = "python"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from index import EmbeddingIndex

HERE = Path(__file__).resolve().parent
GP10 = HERE.parent.parent / "gp-10"
CHECKER_PATH = GP10 / "check/gp10check.py"
CHECKER_SHA256 = "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04"
MEMORY_FLOOR_KIB = 1572864
MEMORY_CAP_BYTES = 1024000000
MAX_RECORD_BYTES = 8 * 1024 * 1024


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Isolated names avoid the embed/refute modules that share GP-10 filenames.
graphs = load_module("gp11_extension_graph6", GP10 / "drive/graph6.py")


def load_checker():
    if digest(CHECKER_PATH) != CHECKER_SHA256:
        raise RuntimeError("frozen_checker_hash")
    return load_module("gp11_extension_frozen_checker", CHECKER_PATH)


def compact(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def seed_for(code):
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big")


def cpu_seconds():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


class ExtensionFailure(Exception):
    pass


class Deadline(Exception):
    pass


class MemoryFloor(Exception):
    pass


class Interrupted(Exception):
    pass


class Guard:
    """One Python process plus at most one child, with a live RAM floor."""

    def __init__(self):
        self.minimum_kib = None

    def check(self):
        with open("/proc/meminfo") as stream:
            available = next(int(line.split()[1]) for line in stream
                             if line.startswith("MemAvailable:"))
        self.minimum_kib = min(self.minimum_kib or available, available)
        if available < MEMORY_FLOOR_KIB:
            raise MemoryFloor("MemAvailable below 1.5 GiB")

    @contextmanager
    def watch(self, seconds=None):
        end = None if seconds is None else time.monotonic() + seconds

        def tick(*_):
            self.check()
            if end is not None and time.monotonic() >= end:
                raise Deadline("graph_seconds")

        self.check()
        old = signal.signal(signal.SIGALRM, tick)
        signal.setitimer(signal.ITIMER_REAL, 0.1, 0.1)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)


def limits():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MEMORY_CAP_BYTES if hard == resource.RLIM_INFINITY else min(hard, MEMORY_CAP_BYTES)
    resource.setrlimit(resource.RLIMIT_AS, (min(soft, cap) if soft > 0 else cap, cap))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.nice(max(0, 15 - os.getpriority(os.PRIO_PROCESS, 0)))


def rational_text(value):
    value = Fraction(value)
    return f"{value.numerator}/{value.denominator}"


def gp_poly(coefficients):
    # Parsing and reserializing rationals prevents GP source injection.
    return "+".join(f"({rational_text(c)})*t^{i}" for i, c in enumerate(coefficients))


def parse_array(source):
    """PARI's list of exact rationals, with no eval or expression imports."""
    def visit(node):
        if isinstance(node, ast.List):
            return [visit(item) for item in node.elts]
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return Fraction(visit(node.left), visit(node.right))
        raise ExtensionFailure("pari:output_syntax")

    return visit(ast.parse(source, mode="eval").body)


def program(code, cert, vertex, keep, neighbours, degree_cap):
    ids = [[0, 0] for _ in range(len(keep) + 1)]
    lo, hi = map(rational_text, cert["field"]["interval"])
    statements = [f"DEGREE_CAP={int(degree_cap)};", f"setrand({seed_for(code)});",
                  f"selectbase({gp_poly(cert['field']['minpoly'])},{lo},{hi});",
                  "R=List();"]
    k = 0
    for old, point in zip(keep, cert["coords"]):
        for axis in (0, 1):
            k += 1
            ids[old][axis] = k
            statements.append(f"push({gp_poly(point[axis])});")
    statements.append("reducefield();")
    ax, ay = ids[neighbours[0]]
    bx, by = ids[neighbours[1]]
    statements.extend([f"push(R[{bx}]-R[{ax}]);", f"push(R[{by}]-R[{ay}]);",
                       f"push((R[{ax}]+R[{bx}])/2);", f"push((R[{ay}]+R[{by}])/2);"])
    dx, dy, mx, my, root = k + 1, k + 2, k + 3, k + 4, k + 5
    statements.extend([
        f"dd=R[{dx}]^2+R[{dy}]^2;",
        'if(dd==0,error("extension:base_collision"));',
        "zz=1/dd-1/4;",
        'if(zz!=0 && value(zz)<=0,error("extension:far"));',
        'if(zz==0,print("GP_TANGENT 1"));',
        "push(rootfield(zz));",
        "chosen=0;",
        "forstep(s=1,-1,-2,"
        f"px=R[{mx}]+s*R[{dy}]*R[{root}];py=R[{my}]-s*R[{dx}]*R[{root}];"
        "occupied=0;"
        f"for(j=1,{len(keep)},if(px==R[2*j-1] && py==R[2*j],occupied=j;break));"
        'print("GP_BRANCH ",[s,occupied]);'
        "if(!occupied,chosen=s;break));",
        'if(!chosen,error("extension:collision"));',
        "push(px);", "push(py);"])
    ids[vertex] = [k + 6, k + 7]
    flat = [item for point in ids for item in point]
    statements.append(f"finish({flat});")
    return (HERE / "extension.gp").read_text() + "\nmain()={\n" + "\n".join(statements) + "\n};\nmain();\nquit;\n"


def extend_exact(code, cert, vertex, keep, neighbours, scratch, degree_cap=256, seconds=None):
    """Return a proposed certificate and exact branch diagnostics."""
    source = program(code, cert, vertex, keep, neighbours, degree_cap)
    path = Path(scratch) / "extension.gp"
    path.write_text(source)
    # GP can print an error and still exit zero. Require its final success
    # marker, then independently check the resulting ordinary certificate.
    child = subprocess.Popen(["gp", "-fq", "-s", "64000000", str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = child.communicate(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        raise ExtensionFailure("attempt_timeout") from exc
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
    diagnostics = {"branches": [parse_array(line[10:]) for line in stdout.splitlines()
                                if line.startswith("GP_BRANCH ")],
                   "tangent": "GP_TANGENT 1" in stdout}
    if child.returncode or not stdout.splitlines() or stdout.splitlines()[-1] != "GP_FIELD_OK":
        match = re.findall(r"(?:extension|field):[a-z_]+", stderr)
        reason = match[-1] if match else "pari:missing_exact_success"
        error = ExtensionFailure(reason)
        error.diagnostics = diagnostics
        error.detail = stderr[-1000:]
        raise error

    def item(label):
        rows = [line[len(label):] for line in stdout.splitlines() if line.startswith(label)]
        if len(rows) != 1:
            raise ExtensionFailure("pari:output_field")
        return parse_array(rows[0])

    polynomial = item("GP_FIELD_POLY ")
    if any(type(c) is not int for c in polynomial):
        raise ExtensionFailure("pari:noninteger_polynomial")
    coords = item("GP_FIELD_COORDS ")
    result = {"type": "exact",
              "field": {"minpoly": polynomial,
                        "interval": [rational_text(v) for v in item("GP_FIELD_INTERVAL ")]},
              "coords": [[[rational_text(v) for v in coords[2 * i + axis]]
                          for axis in (0, 1)] for i in range(len(keep) + 1)]}
    return result, diagnostics


class Extender:
    def __init__(self, index, checker, scratch, guard=None, seconds=3.0, degree_cap=256,
                 attempt_seconds=1.0):
        self.index = index
        self.checker = checker
        self.scratch = scratch
        self.guard = guard or Guard()
        self.seconds = seconds
        self.degree_cap = degree_cap
        self.attempt_seconds = attempt_seconds

    def unknown(self, code, reason):
        return {"g6": code, "verdict": "unknown", "cert": {
            "reason": reason, "budget": {"seconds": self.seconds, "degree_cap": self.degree_cap,
                                         "attempt_seconds": self.attempt_seconds,
                                         "base_placements": 1, "block_gluing": False}}}

    def run(self, code):
        started = time.monotonic()
        cpu_started = cpu_seconds()
        stats = {"g6": code, "seed": seed_for(code), "attempts": [], "degree2_vertices": 0,
                 "check_seconds": 0.0}
        record = None
        try:
            with self.guard.watch(self.seconds):
                n, mask = graphs.decode_graph6(code)
                if n != 11:
                    raise ExtensionFailure("unsupported_order")
                if graphs.canonicalize(n, mask).g6 != code:
                    raise ExtensionFailure("noncanonical_input")
                adjacency = graphs.adjacency_dict(n, mask)
                vertices = [v for v in range(n) if len(adjacency[v]) == 2]
                stats["degree2_vertices"] = len(vertices)
                for vertex in vertices:
                    attempt = {"vertex": vertex}
                    stats["attempts"].append(attempt)
                    attempt_start = time.monotonic()
                    keep = [u for u in range(n) if u != vertex]
                    reverse = {old: new for new, old in enumerate(keep)}
                    base_mask = sum(1 << graphs.pair_index(10, reverse[u], reverse[v])
                                    for u, v in graphs.iter_edges(n, mask) if vertex not in (u, v))
                    base = graphs.canonicalize(10, base_mask)
                    attempt["base"] = base.g6
                    if not graphs.is_biconnected(10, base_mask):
                        attempt["reason"] = "base_not_biconnected"
                        continue
                    try:
                        exact = self.index.resolve(base.g6)
                    except KeyError:
                        attempt["reason"] = "base_not_indexed"
                        continue
                    # The first map is deletion label -> canonical base label;
                    # index.resolve already composed the base's E-ptr chain.
                    relabelled = {"type": "exact", "field": exact["field"],
                                  "coords": [exact["coords"][base.old_to_new[u]] for u in range(10)]}
                    try:
                        candidate, diagnostics = extend_exact(
                            code, relabelled, vertex, keep, adjacency[vertex], self.scratch, self.degree_cap,
                            self.attempt_seconds if vertex != vertices[-1] else self.seconds)
                        attempt.update(diagnostics)
                        check_start = time.monotonic()
                        try:
                            self.checker.exact_embedding(self.checker.decode(code), candidate)
                        finally:
                            stats["check_seconds"] += time.monotonic() - check_start
                        proposed = {"g6": code, "verdict": "embedded", "cert": candidate}
                        if len(compact(proposed).encode()) + 1 > MAX_RECORD_BYTES:
                            raise ExtensionFailure("record_size_cap")
                        attempt["reason"] = "embedded"
                        attempt["degree"] = len(candidate["field"]["minpoly"]) - 1
                        record = proposed
                    except ExtensionFailure as exc:
                        attempt["reason"] = str(exc)
                        attempt.update(getattr(exc, "diagnostics", {}))
                        if getattr(exc, "detail", ""):
                            attempt["detail"] = exc.detail
                    except self.checker.Rejection as exc:
                        attempt["reason"] = "checker:" + exc.reason
                        attempt["detail"] = str(exc)
                    finally:
                        attempt["seconds"] = time.monotonic() - attempt_start
                    if record is not None:
                        break
                if record is None:
                    reasons = Counter(a["reason"] for a in stats["attempts"])
                    if not vertices:
                        reason = "no_degree_two_vertex"
                    elif len(reasons) == 1:
                        reason = next(iter(reasons))
                    else:
                        reason = "placements_exhausted"
                    record = self.unknown(code, reason)
                    record["cert"]["budget"]["attempt_reasons"] = dict(sorted(reasons.items()))
        except (Deadline, MemoryFloor, Interrupted) as exc:
            reason = {Deadline: "graph_timeout", MemoryFloor: "memory_floor", Interrupted: "interrupted"}[type(exc)]
            record = self.unknown(code, reason)
            if stats["attempts"] and "reason" not in stats["attempts"][-1]:
                stats["attempts"][-1]["reason"] = reason
            stats["stop"] = reason in ("memory_floor", "interrupted")
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ExtensionFailure) else "producer_exception:" + type(exc).__name__
            record = self.unknown(code, reason)
            stats["error"] = str(exc)[:1000]
        stats["seconds"] = time.monotonic() - started
        stats["cpu_seconds"] = cpu_seconds() - cpu_started
        stats["verdict"] = record["verdict"]
        if record["verdict"] == "unknown":
            stats["reason"] = record["cert"]["reason"]
        # Bound the inherited driver's large canonical cache on full B11.
        graphs._canonicalize_cached.cache_clear()
        return record, stats


if __name__ == "__main__":
    from extend_run import main
    sys.exit(main(sys.modules[__name__]))
