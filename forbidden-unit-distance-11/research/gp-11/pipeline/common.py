"""Shared paths and resource guards; no mathematical decisions live here."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
GP11 = HERE.parent
GP = GP11.parent / "gp-10"
ROOT = GP11.parents[1]
B11 = GP11 / "data/B11.g6"
B11_SHA = "ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f"
CHECKER_SHA = "d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04"
FLOOR_KIB = 1572864
MAX_RECORD = 8 * 1024 * 1024
sys.dont_write_bytecode = True
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ.update(SYMPY_GROUND_TYPES="python", PYTHONDONTWRITEBYTECODE="1")
for part in ("check", "drive", "refute", "embed"):
    sys.path.insert(0, str(GP / part))
sys.path.insert(0, str(HERE))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data.encode() if isinstance(data, str) else data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json(path, value):
    atomic(path, compact(value) + "\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def checker(scratch):
    if digest(GP / "check/gp10check.py") != CHECKER_SHA:
        raise ValueError("frozen_checker_hash")
    # The GP-11 profile checks all external pins, including F9/F10 and gadgets.
    # Its unchanged base still supplies the sample profile with only F9 in force.
    profile = load("pipeline_profile", GP11 / "check/gp11check.py")
    module = profile.base
    module.SCRATCH = Path(scratch)
    module.SCRATCH.mkdir(parents=True, exist_ok=True)
    return module


class Deadline(BaseException):
    pass


class MemoryFloor(BaseException):
    pass


class Interrupted(BaseException):
    pass


@contextmanager
def timer(seconds):
    def expire(*_):
        raise Deadline("wall_budget")
    old = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, max(.001, seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class Guard:
    def __init__(self):
        self.minimum_kib = 1 << 60
        self.stop = threading.Event()
        self.owner = os.getpid()

    def check(self):
        with open("/proc/meminfo") as stream:
            value = next(int(line.split()[1]) for line in stream if line.startswith("MemAvailable:"))
        self.minimum_kib = min(self.minimum_kib, value)
        if value < FLOOR_KIB:
            raise MemoryFloor("MemAvailable below 1.5 GiB")

    def start(self):
        self.check()
        def stop_memory(*_):
            raise MemoryFloor("MemAvailable below 1.5 GiB")
        def stop_signal(*_):
            raise Interrupted("signal")
        signal.signal(signal.SIGUSR1, stop_memory)
        signal.signal(signal.SIGTERM, stop_signal)
        signal.signal(signal.SIGINT, stop_signal)
        def monitor():
            while not self.stop.wait(.1):
                try:
                    self.check()
                except MemoryFloor:
                    # Kill native children too: Python cannot interrupt a C call immediately.
                    for pid in descendants(self.owner):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    os.kill(self.owner, signal.SIGUSR1)
                    if not self.stop.wait(1):
                        # A native call may not return to Python's signal handler.
                        # The journal protocol is also safe under this hard stop.
                        os._exit(75)
                    return
        threading.Thread(target=monitor, daemon=True).start()


def descendants(pid):
    found = set()
    todo = [pid]
    for parent in todo:
        try:
            for task in Path(f"/proc/{parent}/task").iterdir():
                for raw in (task / "children").read_text().split():
                    child = int(raw)
                    if child not in found:
                        found.add(child)
                        todo.append(child)
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def limits(scratch):
    os.nice(max(0, 15 - os.getpriority(os.PRIO_PROCESS, 0)))
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = 2048000000 if hard == resource.RLIM_INFINITY else min(hard, 2048000000)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    os.environ.update(TMPDIR=str(scratch), SQLITE_TMPDIR=str(scratch))
    tempfile.tempdir = str(scratch)


def redirect(scratch):
    for name in ("graphs", "algebra", "gp10refute", "gp10check", "msolve_exact"):
        module = sys.modules.get(name)
        if module and hasattr(module, "SCRATCH"):
            module.SCRATCH = Path(scratch)


def unknown(code, reason, budget):
    return {"g6": code, "verdict": "unknown", "cert": {"reason": reason, "budget": budget}}


def source_hashes():
    paths = [p for p in HERE.glob("*.py") if not p.name.startswith("test_")] + list(HERE.glob("*.c"))
    paths += list((GP11 / "embed").glob("*.py")) + list((GP11 / "embed").glob("*.gp"))
    for part in ("embed", "refute", "drive", "check"):
        paths += list((GP / part).glob("*.py"))
    paths += [GP11 / "CONTRACT.md", GP11 / "PROOFS.md", GP11 / "check/gp11check.py", GP / "embed/msolve_seed.c",
              GP / "embed/host_sources.json", GP / "embed/host_certificates.json",
              GP / "cloud/lean3/records.jsonl.gz", GP / "data/B10.g6",
              ROOT / "research/unit-distance-22/check/udcheck.py"]
    paths += [ROOT / "research/unit-distance-22/data" / name for name in
              ("forbidden-74.json", "forbidden-398.json", "tu-gadgets.json")]
    paths += [ROOT / "research/unit-distance-22/filter" / name for name in ("udfilter.c", "udfilter.h")]
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
