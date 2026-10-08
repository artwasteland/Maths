#!/usr/bin/env python3
"""refine_probe.py: measurements and evidence for coordination/cloud-workers/u23-refine.sh (the ## u23-refine entry of
coordination/cloud-workers/JOBS.md). Nothing here decides a verdict: each piece's verdict is the G5 checker's own
output, written by the unchanged u23-verify.sh.

  refine_probe.py run --out DIR -- CMD...
      Run CMD. Meanwhile, once a second, sample the memory cgroup's usage and every descendant of CMD over 16 MB, and
      every descendant whose command line names verify-chain (its VmRSS and VmHWM, the kernel's own high-water mark of
      the process). Write DIR/memory.json (the cgroup's files before and
      after, each process's peak, the G5 checker's peak, getrusage's largest descendant) and DIR/memory-samples.jsonl.gz.
      Exit with CMD's status (128 + N for a signal N).
  refine_probe.py collect --run RUN --out DIR
      The run directory's evidence, which the result copies do not keep:
      inventory.jsonl.gz  every file under RUN: path, bytes, sha256, newline count, link count and inode;
      certs.json          per certificate file and verdict: records, bytes, the longest line, the witness keys;
      meta.tar.gz         the metadata files under RUN (manifests, stats, logs, captured stderr: every .json, .log
                          and .stderr), the level-12 slice files (the piece's roots) and, beside RUN, the run log, the
                          G4 replay's log and its records (RUN.replay/: replay.jsonl, summary.json, ...); not the
                          payloads (.g6 level, shard, part and parent files, .jsonl certificate and prune records),
                          which inventory.jsonl.gz lists by sha256; a member over 8 MB is left out and listed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import resource
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

MB = 1 << 20


def cgroup_dir() -> tuple[str | None, Path | None]:
    """The memory cgroup of this process: (v1|v2, its directory), or (None, None)."""
    cands = []
    try:
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            _, ctrls, path = line.split(":", 2)
            if ctrls == "":
                cands.append(("v2", Path("/sys/fs/cgroup") / path.lstrip("/")))
            elif "memory" in ctrls.split(","):
                cands.append(("v1", Path("/sys/fs/cgroup/memory") / path.lstrip("/")))
    except (OSError, ValueError):
        pass
    cands += [("v1", Path("/sys/fs/cgroup/memory")), ("v2", Path("/sys/fs/cgroup"))]
    for v, d in cands:
        if (d / ("memory.usage_in_bytes" if v == "v1" else "memory.current")).is_file():
            return v, d
    return None, None


V1 = ("memory.usage_in_bytes", "memory.max_usage_in_bytes", "memory.limit_in_bytes", "memory.failcnt",
      "memory.memsw.usage_in_bytes", "memory.memsw.limit_in_bytes", "memory.oom_control", "memory.stat")
V2 = ("memory.current", "memory.peak", "memory.max", "memory.swap.current", "memory.swap.max", "memory.events",
      "memory.stat")


def snapshot(v: str | None, d: Path | None) -> dict:
    out = {}
    for name in (V1 if v == "v1" else V2 if v == "v2" else ()):
        try:
            out[name] = (d / name).read_text().strip()
        except OSError as e:
            out[name] = f"unreadable: {e.strerror}"
    return out


def usage(v: str | None, d: Path | None) -> int | None:
    try:
        return int((d / ("memory.usage_in_bytes" if v == "v1" else "memory.current")).read_text())
    except (OSError, ValueError, TypeError):
        return None


def processes(root: int, min_kb: int = 16 * 1024):
    """(pid, ppid, comm, cmdline, VmRSS kB, VmHWM kB) of every descendant of process root over min_kb, and of every
    descendant whose command line names verify-chain whatever its size (the machine's other processes are left out)."""
    info = {}
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            st = {}
            for line in (p / "status").read_text().splitlines():
                k, _, val = line.partition(":")
                if k in ("PPid", "VmRSS", "VmHWM", "Name"):
                    st[k] = val.strip()
            info[int(p.name)] = (int(st.get("PPid", 0)), st.get("Name", "?"),
                                 int(st.get("VmRSS", "0 kB").split()[0]), int(st.get("VmHWM", "0 kB").split()[0]))
        except (OSError, ValueError, IndexError):
            continue
    kids: dict[int, list] = {}
    for pid, (ppid, *_rest) in info.items():
        kids.setdefault(ppid, []).append(pid)
    todo, seen = [root], set()
    while todo:
        q = todo.pop()
        for c in kids.get(q, []):
            if c not in seen:
                seen.add(c)
                todo.append(c)
    for pid in sorted(seen):
        ppid, comm, rss, hwm = info[pid]
        try:
            cmd = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        cmd = cmd.strip()[:200]
        if rss >= min_kb or "verify-chain" in cmd:
            yield pid, ppid, comm, cmd, rss, hwm


def run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd:
        print("refine_probe.py run: no command", file=sys.stderr)
        return 2
    v, d = cgroup_dir()
    before = snapshot(v, d)
    reset = None
    if v == "v1":   # the lifetime high-water mark, reset if the interface allows it
        try:
            (d / "memory.max_usage_in_bytes").write_text("0")
            reset = "reset to 0 before the command"
        except OSError as e:
            reset = f"not resettable ({e.strerror}): a lifetime high-water mark"
    peaks: dict[tuple, dict] = {}
    state = {"samples": 0, "usage_max": None}
    stop = threading.Event()
    sfile = gzip.open(out / "memory-samples.jsonl.gz", "wt")

    def sample(root):
        while not stop.is_set():
            t = round(time.time(), 1)
            u = usage(v, d)
            if u is not None and (state["usage_max"] is None or u > state["usage_max"]):
                state["usage_max"] = u
            rows = []
            for pid, ppid, comm, cmd_, rss, hwm in processes(root):
                rows.append([pid, rss, hwm])
                # keyed by pid and command line: a pid reused by another process over hours is another entry
                e = peaks.setdefault((pid, cmd_), {"pid": pid, "ppid": ppid, "comm": comm, "cmd": cmd_,
                                                   "rss_max_kb": 0, "hwm_kb": 0, "first": t, "last": t})
                e["rss_max_kb"] = max(e["rss_max_kb"], rss)
                e["hwm_kb"] = max(e["hwm_kb"], hwm)
                e["last"] = t
            sfile.write(json.dumps([t, u, rows]) + "\n")
            state["samples"] += 1
            stop.wait(a.interval)

    child = subprocess.Popen(cmd)
    th = threading.Thread(target=sample, args=(child.pid,), daemon=True)
    t0 = time.time()
    th.start()
    code = child.wait()
    stop.set()
    th.join(10)
    sfile.close()
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    after = snapshot(v, d)
    status = code if code >= 0 else 128 - code
    checker = [e for e in peaks.values() if "verify-chain" in e["cmd"]]
    rec = {
        "command": cmd, "exit": status, "seconds": round(time.time() - t0, 1), "interval_s": a.interval,
        "samples": state["samples"],
        "checker_peak_kb": max((e["hwm_kb"] for e in checker), default=None),
        "checker_note": "VmHWM of each process whose command line names verify-chain, as last sampled (a process's "
                        "growth in its final interval before it exits is not seen)",
        "rusage_children_maxrss_kb": ru.ru_maxrss,
        "rusage_note": "getrusage(RUSAGE_CHILDREN).ru_maxrss: the largest single waited-for descendant, any command",
        "cgroup": {"version": v, "dir": str(d) if d else None, "peak": reset, "sampled_usage_max_bytes":
                   state["usage_max"], "before": before, "after": after},
        "processes": sorted(peaks.values(), key=lambda e: -e["hwm_kb"])[:40],
    }
    (out / "memory.json").write_text(json.dumps(rec, indent=1) + "\n")
    return status


def sha256_file(p: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * MB), b""):
            h.update(chunk)
            n += chunk.count(b"\n")
    return h.hexdigest(), n


def metadata_file(name: str) -> bool:
    """A metadata file of a run directory: a manifest, stats or other .json, a log, a captured stderr, or a level-12
    slice file (the piece's roots); not a level, certificate, shard, part, parent or prune payload (.g6, .jsonl)."""
    return name.endswith((".json", ".log", ".stderr")) or (".slice-" in name and name.endswith(".g6"))


def collect(a) -> int:
    run_dir, out = Path(a.run), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in run_dir.rglob("*") if p.is_file())
    with gzip.open(out / "inventory.jsonl.gz", "wt") as inv:
        for p in files:
            st = p.stat()
            digest, lines = sha256_file(p)
            inv.write(json.dumps({"path": str(p.relative_to(run_dir)), "bytes": st.st_size, "sha256": digest,
                                  "newlines": lines, "nlink": st.st_nlink, "inode": st.st_ino}) + "\n")
    certs = {}
    for p in files:
        if not p.name.endswith(".certs.jsonl"):
            continue
        per: dict[str, dict] = {}
        bad = 0
        with p.open("rb") as f:
            for raw in f:
                try:
                    r = json.loads(raw)
                    verdict = str(r.get("verdict"))
                    keys = sorted(r["witness"]) if isinstance(r.get("witness"), dict) else []
                except (ValueError, AttributeError):
                    bad += 1
                    continue
                e = per.setdefault(verdict, {"records": 0, "bytes": 0, "longest": 0, "witness_keys": {}})
                e["records"] += 1
                e["bytes"] += len(raw)
                e["longest"] = max(e["longest"], len(raw))
                for k in keys:
                    e["witness_keys"][k] = e["witness_keys"].get(k, 0) + 1
        certs[str(p.relative_to(run_dir))] = {"bytes": p.stat().st_size, "unparsed_lines": bad, "by_verdict": per}
    (out / "certs.json").write_text(json.dumps(certs, indent=1, sort_keys=True) + "\n")
    members = [(p, str(p.relative_to(run_dir.parent))) for p in files if metadata_file(p.name)]
    for side in (Path(str(run_dir) + ".log"), Path(str(run_dir) + ".replay.log")):
        if side.is_file():
            members.append((side, side.name))
    rdir = Path(str(run_dir) + ".replay")
    if rdir.is_dir():
        members += [(p, str(p.relative_to(run_dir.parent))) for p in sorted(rdir.rglob("*")) if p.is_file()]
    left_out = [{"path": arc, "bytes": p.stat().st_size} for p, arc in members if p.stat().st_size > 8 * MB]
    with tarfile.open(out / "meta.tar.gz", "w:gz") as tar:
        for p, arc in members:
            if p.stat().st_size <= 8 * MB:
                tar.add(p, arcname=arc, recursive=False)
    (out / "meta-left-out.json").write_text(json.dumps(left_out, indent=1) + "\n")
    total = sum((out / n).stat().st_size for n in ("inventory.jsonl.gz", "certs.json", "meta.tar.gz"))
    print(f"refine_probe.py collect: {len(files)} files inventoried, {len(certs)} certificate files, "
          f"{len(members) - len(left_out)} metadata files ({len(left_out)} over 8 MB left out); {total} bytes of evidence")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--interval", type=float, default=1.0)
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    c = sub.add_parser("collect")
    c.add_argument("--run", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    return run(a) if a.what == "run" else collect(a)


if __name__ == "__main__":
    sys.exit(main())
