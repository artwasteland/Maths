#!/usr/bin/env python3
"""Implementation of u24-worker.sh; use the shell entry point for pinned production settings.

The prefix maker gets a whole check. Later slices need its accepted receipt and
the unchanged prefix digest, as well as a successful byte comparison. This also
catches corruption of an inode shared by both sides of the byte comparison.
Failed checks have no memory fallback and never authorize deletion.
"""
from __future__ import annotations

import filecmp
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

import evidence

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "research/unit-distance-22/enum/verify-chain-u24.py"
CONTROL = Path(__file__).with_name("known_graphs.py")
RUNBOOK = ROOT / "coordination/cloud-workers/u23-slice.sh"
KEY = "-L12-tri-pf74"
LEVEL_RE = re.compile(r"^(\d+)-(\d+)(\.reach|\.keep|\.UNKNOWN)?\.g6$|^(\d+)-(\d+)\.certs\.jsonl$")
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] u24-worker {os.getenv('TAG', '?')}: {message}", flush=True)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=1) + "\n")
    os.replace(tmp, path)


def names_digest(root: Path, names) -> str:
    h = hashlib.sha256()
    for name in sorted(names):
        h.update(f"{name} {sha(root / name)}\n".encode())
    return h.hexdigest()


def prefix_diff(first: Path, run: Path) -> str:
    # u23-verify.sh's comparison: names and bytes, never cached stat equality.
    def names(root):
        return {p.name for p in root.iterdir() if p.is_file()
                and (m := LEVEL_RE.match(p.name)) and int(m.group(1) or m.group(4)) <= 12}
    a, b = names(first), names(run)
    problems = []
    if a - b:
        problems.append(f"only in the first slice: {sorted(a - b)}")
    if b - a:
        problems.append(f"only in this slice: {sorted(b - a)}")
    filecmp.clear_cache()
    problems += [f"differs: {name}" for name in sorted(a & b) if not filecmp.cmp(first / name, run / name, shallow=False)]
    if not a:
        problems.append("no prefix files in the first slice")
    if problems:
        raise ValueError("PREFIX: " + "; ".join(problems))
    return f"identical, file for file ({len(a)} files)"


def shared_prefix(prefix: Path, run: Path) -> tuple[dict, str]:
    info = load(prefix / "prefix.json")
    files = info["files"]
    if info["slice_level"] != 12 or not files:
        raise ValueError("PREFIX: empty or wrong level in prefix.json")
    for name, size in files.items():
        if Path(name).name != name or name == "prefix.json":
            raise ValueError("PREFIX: unsafe file name in prefix.json")
        if (prefix / name).stat().st_size != size or (run / name).stat().st_size != size:
            raise ValueError(f"PREFIX: size differs: {name}")
    got = names_digest(prefix, files)
    if names_digest(run, files) != got:
        raise ValueError("PREFIX: shared files differ from PREFIXDIR")
    return info, got


def inventory(run: Path, dest: Path) -> dict:
    # All regular files, recursively; partition-specific level-12 slice files stay explicit.
    prefix, upper, total_bytes, directory_bytes = [], [], 0, run.stat().st_size
    for path in sorted(run.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"INVENTORY: symlink in run directory: {path.relative_to(run)}")
        if path.is_dir():
            directory_bytes += path.stat().st_size
        if not path.is_file():
            continue
        rel = path.relative_to(run).as_posix()
        parts = Path(rel).parts
        level = re.match(r"^(\d+)-\d+(?:\.|$)", parts[1] if parts[0] in ("shards", "_parents") and len(parts) > 1 else parts[0])
        h, size, newlines = hashlib.sha256(), 0, 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                h.update(block)
                size += len(block)
                newlines += block.count(b"\n")
        total_bytes += size
        row = {"path": rel, "bytes": size, "sha256": h.hexdigest(), "newlines": newlines}
        if level and int(level.group(1)) <= 12 and ".slice-" not in rel:
            prefix.append(row)
        else:
            upper.append(row)
    lines = "".join(f"{r['path']} {r['sha256']}\n" for r in prefix)
    summary = {"prefix_through": 12, "files": len(prefix), "bytes": sum(r["bytes"] for r in prefix),
               "sha256": hashlib.sha256(lines.encode()).hexdigest()}
    tmp = dest.with_name(dest.name + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        for row in [summary, *prefix, *upper]:
            gz.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    os.replace(tmp, dest)
    return {"files": len(prefix) + len(upper), "file_bytes": total_bytes,
            "directory_bytes": total_bytes + directory_bytes, "prefix": summary,
            "sha256": sha(dest), "bytes": dest.stat().st_size}


def files_digest(run: Path, result: Path) -> str:
    digest = evidence.hash_records(run, result)
    evidence.retained_files(run, result)
    return digest


def check_accept(body: str, code: int, index: int, whole: bool) -> list[str]:
    problems = []
    lines = body.splitlines()
    chain = [l for l in lines if l.startswith("CHAIN ")]
    want = "CHAIN OK" if whole else "CHAIN PARTIAL (levels below 13 not inspected (--from-n 13))"
    if code != (0 if whole else 3) or chain != [want] or any(l.startswith("PROBLEM") for l in lines):
        problems.append(f"CHECK: expected exit {0 if whole else 3} and exactly {want}, without PROBLEM")
    if whole and not any(l.startswith("COVERAGE exhaustive") for l in lines):
        problems.append("CHECK: no COVERAGE exhaustive")
    try:
        rows = [json.loads(l) for l in lines if l.startswith("{")]
        if len(rows) != 1:
            raise ValueError("expected one checker JSON record")
        r = rows[0]
        if (r.get("certs_replayed", 0) <= 0 or r.get("certs_replayed") != r.get("pruned_cells_inspected")
                or r.get("target") != [24, 69] or r.get("seed_n") != 10 or r.get("slice") != [12, index, 1920]
                or r.get("pinned") != {"target": [24, 69], "seed": 10, "slices": [12, 1920]}):
            problems.append("CHECK: certificates not all replayed, or wrong target, seed, slice or pins")
    except (ValueError, TypeError, KeyError) as error:
        problems.append(f"CHECK: cannot read replay counts: {error}")
    return problems


def available_mb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024
    raise ValueError("cannot read MemAvailable")


def group_rss_kib(group: int) -> int:
    total = 0
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            stat = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            if int(stat[2]) == group:
                total += int(stat[21]) * os.sysconf("SC_PAGE_SIZE") // 1024
        except (OSError, ValueError, IndexError):
            pass
    return total


def measured(command: list[str], output: Path, timed: bool = False) -> dict:
    limit = int(os.getenv("U24_MIN_AVAILABLE_MB", "0"))
    timefile = output.with_name(output.name + ".time")
    use_time = timed and os.access("/usr/bin/time", os.X_OK)
    argv = ["/usr/bin/time", "-v", "-o", str(timefile), *command] if use_time else command
    start, peak, stopped = time.monotonic(), 0, False
    with output.open("wb") as out:
        if limit and available_mb() < limit:
            out.write(f"MEMORY STOP: MemAvailable below {limit} MiB before starting\n".encode())
            return {"exit": 137, "seconds": 0, "peak_rss_kib": 0, "memory_stop": True}
        p = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
        try:
            while p.poll() is None:
                # The sampler also survives a killed time process with no final report.
                if timed:
                    peak = max(peak, group_rss_kib(p.pid))
                if limit and available_mb() < limit:
                    stopped = True
                    out.write(f"MEMORY STOP: MemAvailable below {limit} MiB\n".encode())
                    out.flush()
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                    # Descendants can outlive their shell; stop the whole group.
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.25)
            p.wait()
        except BaseException:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            p.wait()
            raise
    peak_method = "process-group RSS sampler (250 ms)"
    if use_time and timefile.exists():
        m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", timefile.read_text())
        if m:
            peak = int(m[1])
            peak_method = "/usr/bin/time -v"
    return {"exit": 137 if stopped else (p.returncode if p.returncode >= 0 else 128 - p.returncode),
            "seconds": round(time.monotonic() - start, 3), "peak_rss_kib": peak,
            "peak_method": peak_method, "memory_stop": stopped}


def git(*args) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def push_receipt(paths: list[Path], message: str) -> bool:
    # Only receipt paths belong in this commit; unrelated staged work is not ours.
    names = [str(p) for p in paths]
    try:
        subprocess.run(["git", "add", "-f", "--", *names], cwd=ROOT, check=True)
        changed = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *names], cwd=ROOT).returncode
        if changed == 1:
            subprocess.run(["git", "commit", "-q", "--only", "-m", message, "--", *names], cwd=ROOT, check=True)
        elif changed:
            return False
    except subprocess.CalledProcessError:
        return False
    for attempt in range(3):
        if subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=ROOT).returncode == 0:
            return True
        if attempt < 2:
            time.sleep(30)
    log("push failed three times")
    return False


def implementation_hashes() -> dict:
    return {"worker_sha256": SOURCE_SHA256, "evidence_sha256": evidence.SOURCE_SHA256}


def verified_marker(path: Path, pin: str, push: bool, expected_slice=None, result_root=None) -> dict:
    marker = load(path)
    if marker.get("schema") != "u24-checked-v2" or len(marker.get("receipts", {})) != 4:
        raise ValueError(f"MARKER: four bound v2 receipts required: {path}")
    if marker["checker_sha256"] != pin or marker["target"] != [24, 69] or (push and not marker["pushed"]):
        raise ValueError(f"MARKER: wrong checker, target or push status: {path}")
    for name, checksum in marker["receipts"].items():
        if sha(Path(name)) != checksum:
            raise ValueError(f"MARKER: receipt changed: {name}")
    requested = marker["slice"] if expected_slice is None else expected_slice
    if marker.get("slice") != requested:
        raise ValueError("MARKER: wrong slice")
    text_path = Path(marker["text_receipt"])
    paths = {"text": text_path, **{kind: text_path.with_suffix(suffix) for kind, suffix in
             (("known", ".known.json"), ("inventory", ".inventory.jsonl.gz"), ("structure", ".structure.json"))}}
    if set(marker["receipts"]) != {str(p) for p in paths.values()} or marker["structure_receipt"] != str(paths["structure"]):
        raise ValueError("MARKER: receipt paths do not form one bound receipt set")
    structure, known = load(paths["structure"]), load(paths["known"])
    if any(r.get("slice") != requested or r.get("target") != [24, 69] for r in (structure, known)):
        raise ValueError(f"MARKER: receipts do not name requested slice {requested}")
    text = text_path.read_text()
    if ("# u24-worker verdict: pass" not in text.splitlines() or structure.get("result") != "OK"
            or known.get("result") != "OK" or known.get("problems") != []
            or structure.get("g4", {}).get("result") not in ("PASS", "EMPTY")
            or check_accept(text, 0 if marker["whole"] else 3, requested[1], marker["whole"])):
        raise ValueError(f"MARKER: receipts do not record an accepted verdict for slice {requested}")
    if any(marker.get(key) != value for key, value in implementation_hashes().items()):
        # Old hashes (including absent hashes) attest only to the old acceptance
        # rules. Their retained bundle must satisfy the rules running now.
        import receipt_audit
        if result_root is not None:
            result = Path(result_root) / f"24-69{KEY}" / f"s{requested[1]}of{requested[2]}"
        else:
            result = Path(marker["result"]) if "result" in marker else (
                text_path.parent.parent / f"24-69{KEY}" / f"s{requested[1]}of{requested[2]}")
        try:
            receipt_audit.validate(result, text_path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError("MARKER: worker/evidence hashes differ; current receipt audit rejected bound bundle: "
                             + str(error)) from error
    return marker


def committed_result(result: Path, retained: dict) -> str:
    commit = git("rev-parse", "HEAD")
    for name, digest in retained.items():
        path = (result / name).relative_to(ROOT).as_posix()
        raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"RESULT BINDING: committed {name} differs from checked result")
    return commit


def main() -> int:
    tag = os.getenv("TAG", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise ValueError("set TAG to a word of letters, digits, dot, underscore or hyphen")
    if not sys.argv[1:] or any(not re.fullmatch(r"0|[1-9][0-9]*", s) or int(s) >= 1920 for s in sys.argv[1:]):
        raise ValueError("usage: TAG=uNN bash u24-worker.sh <slice 0..1919> [<slice> ...]")
    for name in ("U23_PUSH", "U23_TOOLCHAIN", "U24_KEEP_RUNS", "U24_SKIP_RUNBOOK"):
        if os.getenv(name, "0") not in ("0", "1"):
            raise ValueError(f"{name} must be 0 or 1")
    skipped = os.getenv("U24_SKIP_RUNBOOK", "0") == "1"
    if skipped and os.getenv("U24_KEEP_RUNS", "0") != "1":
        raise ValueError("RUNBOOK: U24_SKIP_RUNBOOK=1 requires U24_KEEP_RUNS=1")
    pin = os.environ["U24_CHECKER_SHA256"]
    if sha(CHECKER) != pin:
        raise ValueError(f"checker sha256 {sha(CHECKER)} is not pinned {pin}")
    if os.getenv("U23_RHOMBUS_CHECKER"):
        raise ValueError("U23_RHOMBUS_CHECKER is a test override, not a production checker")
    out = Path(os.environ["U23_OUT"]).resolve()
    res = Path(os.environ["U23_RES"]).resolve()
    receipts = Path(os.getenv("U24_CHECK_RES", str(res / "check"))).resolve()
    push = os.environ["U23_PUSH"] == "1"
    if push and any(not p.is_relative_to(ROOT) for p in (res, receipts)):
        raise ValueError("pushed result and receipt paths must be inside the repository")
    for p in (out, res, receipts):
        p.mkdir(parents=True, exist_ok=True)
    python = Path.home() / "tools/pyenv-maths/bin/python"
    if not python.exists():
        python.parent.mkdir(parents=True, exist_ok=True)
        python.symlink_to(shutil.which("python3"))
    prefix = out / f"prefix-24-69{KEY}"
    prefix_state = out / f"checked-prefix-24-69{KEY}.json"
    bad, push_bad = [], []
    for arg in sys.argv[1:]:
        index, slice_name = int(arg), f"s{arg}of1920"
        run = out / f"dag-24-69{KEY}-{slice_name}"
        result = res / f"24-69{KEY}" / slice_name
        marker_path = out / f"checked-24-69{KEY}-{slice_name}.json"
        if marker_path.exists():
            marker = verified_marker(marker_path, pin, push, [12, index, 1920], res)
            if not skipped and marker.get("runbook_skipped"):
                raise ValueError("MARKER: retained-evidence check cannot replace a production runbook pass")
            if marker["slice"] != [12, index, 1920]:
                raise ValueError("MARKER: wrong slice")
            log(f"{slice_name}: checked marker exists; skipped")
            continue
        run_log = out / f"{slice_name}-{tag}.worker-runbook.log"
        if os.getenv("U24_SKIP_RUNBOOK", "0") == "1":
            log(f"{slice_name}: runbook skipped; checking retained evidence")
            run_time = {"exit": 0, "seconds": 0, "skipped": True}
        else:
            log(f"{slice_name}: runbook starting (JOBS={os.getenv('JOBS', 'nproc')})")
            run_time = measured(["bash", str(RUNBOOK), "1920", arg], run_log)
        if run_time["exit"]:
            log(f"{slice_name}: runbook exited {run_time['exit']}; no check runs; directories kept; {run_log}")
            return run_time["exit"]
        if not run.is_dir():
            raise ValueError(f"runbook left no run directory: {run}")
        problems, pdiff, prefix_hash, whole, info = [], "NO RESULT", "", False, {}
        prefix_structure = None
        result_push_failed = (not run_time.get("skipped") and push
                              and f"commit/push of {slice_name} results failed" in run_log.read_text())
        try:
            info = load(prefix / "prefix.json")
            whole = Path(info["made_from"]).resolve() == run
            pdiff = prefix_diff(prefix, run)
            info, prefix_hash = shared_prefix(prefix, run)
            if not whole:
                state = verified_marker(prefix_state, pin, push, result_root=res)
                if (state["shared_prefix_sha256"] != prefix_hash or not state["whole"]
                        or state["run"] != info["made_from"]):
                    raise ValueError("PREFIX: digest or source differs from the whole-checked prefix")
                if check_accept(Path(state["text_receipt"]).read_text(), 0, state["slice"][1], True):
                    raise ValueError("PREFIX: the maker's receipt does not show an exhaustive check")
                prefix_structure = Path(state["structure_receipt"])
                if str(prefix_structure) not in state["receipts"]:
                    raise ValueError("PREFIX: structure receipt is not bound by the whole check")
        except (OSError, ValueError, KeyError, TypeError) as error:
            problems.append(f"PREFIX FAIL: {error}")
            pdiff = f"comparison/binding failed: {error}"
        if sha(CHECKER) != pin:
            raise ValueError("checker changed after preflight")
        args = ["--check", "--expect-target", "24", "69", "--expect-seed", "10", "--expect-slices", "12", "1920"]
        if not whole:
            args += ["--from-n", "13"]
        check_log = out / f"{slice_name}-{tag}.checker.log"
        log(f"{slice_name}: checker {'whole' if whole else 'from level 13'}; prefix: {pdiff}")
        check_time = measured([sys.executable, str(CHECKER), str(run), *args], check_log, timed=True)
        body = check_log.read_text(errors="replace")
        problems += check_accept(body, check_time["exit"], index, whole)
        text_path = receipts / f"{slice_name}-{tag}.txt"
        known_path = receipts / f"{slice_name}-{tag}.known.json"
        inv_path = receipts / f"{slice_name}-{tag}.inventory.jsonl.gz"
        structure_path = receipts / f"{slice_name}-{tag}.structure.json"
        control_log = out / f"{slice_name}-{tag}.control.log"
        log(f"{slice_name}: known-graph control starting")
        known_path.unlink(missing_ok=True)
        control_time = measured([sys.executable, str(CONTROL), "slice", str(run), "--out", str(known_path)], control_log)
        control_body = control_log.read_text(errors="replace")
        try:
            known = load(known_path)
            if (control_time["exit"] or known["result"] != "OK" or known["problems"]
                    or not any(l.startswith("KNOWN-GRAPHS OK:") for l in control_body.splitlines())):
                raise ValueError("known-graph control did not pass")
        except (OSError, ValueError, KeyError, TypeError) as error:
            problems.append(f"CONTROL: {error}")
            if not known_path.exists():
                atomic_json(known_path, {"result": "FAIL", "problems": [str(error)], "exit": control_time["exit"]})
        evidence_log = out / f"{slice_name}-{tag}.evidence.log"
        audit_args = [sys.executable, str(Path(evidence.__file__)), str(run), str(result), "--out", str(structure_path),
                      "--first", "10" if whole else "13"]
        if prefix_structure:
            audit_args += ["--prefix", str(prefix_structure)]
        structure_path.unlink(missing_ok=True)
        log(f"{slice_name}: reconciling counts, retained files, resumed records and G4 evidence")
        evidence_time = measured(audit_args, evidence_log)
        evidence_body = evidence_log.read_text(errors="replace")
        fdig, inv, fp, structure, snapshot = "NO RESULT", {}, {}, {}, None
        try:
            structure = load(structure_path)
            if evidence_time["exit"] or structure["result"] != "OK":
                raise ValueError(structure.get("error", "count/retention/structure/G4 audit did not pass"))
            fdig, fp = structure["files_digest"], structure["g4"]
            if push and not skipped and not result_push_failed:
                snapshot = committed_result(result, structure["retained"])
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
            problems.append(f"EVIDENCE: {error}")
            if not structure_path.exists():
                atomic_json(structure_path, {"schema": evidence.SCHEMA, "result": "FAIL", "error": str(error)})
        try:
            inv = inventory(run, inv_path)
        except (OSError, ValueError, KeyError) as error:
            problems.append(f"INVENTORY: {error}")
            # A failed inventory is still an explicit receipt, never a deletion permit.
            with gzip.open(inv_path, "wt") as f:
                f.write(json.dumps({"error": str(error)}) + "\n")
        passed = not problems
        timings = {"runbook": run_time, "run_dag2_seconds": fp.get("run_dag2_wall_seconds"),
                   "g4_seconds": fp.get("replay_wall_seconds"), "check": check_time, "control": control_time,
                   "evidence": evidence_time}
        header = [f"# u24-worker {tag}, slice {slice_name}, checked {'whole' if whole else 'from level 13'}: verify-chain-u24.py {' '.join(args)}",
                  f"# run directory: {run} ({inv.get('file_bytes', '?')} regular-file bytes)",
                  f"# checker: {CHECKER.relative_to(ROOT)}, sha256 {pin}",
                  f"# control sha256: {sha(CONTROL)}; worker sha256: {sha(Path(__file__))}; launcher sha256: {sha(ROOT / 'coordination/cloud-workers/u24-worker.sh')}",
                  f"# evidence tool sha256: {sha(Path(evidence.__file__))}",
                  f"# fleet branch HEAD: {git('rev-parse', 'HEAD')}; runbook sha256 {sha(RUNBOOK)}",
                  f"# python: {sys.version.split()[0]} ({python.resolve()}); host {os.uname().nodename}",
                  f"# measured: {json.dumps(timings, sort_keys=True)}",
                  f"# level files checked (the runbook's hashes.json rule): {fdig}",
                  f"# prefix (levels <= 12) against {prefix}: {pdiff}",
                  f"# shared prefix digest: {prefix_hash}; made from {info.get('made_from', '?')}",
                  f"# inventory: sha256 {sha(inv_path)}, {inv_path.stat().st_size} bytes; {json.dumps(inv, sort_keys=True)}",
                  f"# known receipt: sha256 {sha(known_path)}, {known_path.stat().st_size} bytes",
                  f"# structure receipt: sha256 {sha(structure_path)}, {structure_path.stat().st_size} bytes",
                  f"# target records from checked files: {json.dumps(structure.get('target_files', {}), sort_keys=True)}",
                  f"# target counts from checked files: {json.dumps(structure.get('target_counts', {}), sort_keys=True)}",
                  f"# retained result snapshot: {snapshot or 'local only'}",
                  f"# runbook result push: {'skipped; evidence retained' if skipped else 'FAIL' if result_push_failed else 'completed' if push else 'disabled'}",
                  f"# u24-worker verdict: {'pass' if passed else 'FAIL'}"]
        text_path.write_text("\n".join(header) + "\n" + body + control_body + evidence_body
                             + "".join(f"WORKER FAIL: {p}\n" for p in problems))
        receipt_paths = [text_path, known_path, inv_path, structure_path]
        sizes = {p.name: p.stat().st_size for p in receipt_paths}
        log(f"{slice_name}: runbook {run_time['seconds']} s; run {fp.get('run_dag2_wall_seconds')} s; G4 {fp.get('replay_wall_seconds')} s; check {check_time['seconds']} s, peak {check_time['peak_rss_kib']} KiB; control {control_time['seconds']} s")
        log(f"{slice_name}: {'pass' if passed else 'FAIL'}; receipts {sizes} ({sum(sizes.values())} bytes total)")
        for line in (body + control_body).splitlines():
            if line.startswith(("CHAIN ", "KNOWN-GRAPHS ")):
                log(f"{slice_name}: {line}")
        if not passed:
            bad.append(slice_name)
        receipt_pushed = not push or push_receipt(receipt_paths, f"u24-worker {tag}: {slice_name} {'pass' if passed else 'FAIL'}")
        if not receipt_pushed or result_push_failed:
            push_bad.append(slice_name)
            log(f"{slice_name}: commit/push failed; run directory kept")
        elif passed:
            if push and not skipped:
                committed_result(result, structure["retained"])
            if implementation_hashes() != {"worker_sha256": sha(Path(__file__)), "evidence_sha256": sha(Path(evidence.__file__))}:
                raise ValueError("MARKER: worker/evidence changed during check")
            marker = {"schema": "u24-checked-v2", "target": [24, 69], "slice": [12, index, 1920], "checker_sha256": pin,
                      **implementation_hashes(), "result": str(result),
                      "run": str(run), "whole": whole, "shared_prefix_sha256": prefix_hash,
                      "text_receipt": str(text_path), "structure_receipt": str(structure_path),
                      "receipts": {str(p): sha(p) for p in receipt_paths}, "runbook_skipped": skipped,
                      "pushed": push, "commit": git("rev-parse", "HEAD") if push else None}
            if whole:
                atomic_json(prefix_state, marker)
            atomic_json(marker_path, marker)
            if os.getenv("U24_KEEP_RUNS", "0") != "1":
                shutil.rmtree(run)
                shutil.rmtree(Path(str(run) + ".replay"), ignore_errors=True)
                log(f"{slice_name}: checked marker written; run and replay directories deleted; prefix kept")
            else:
                log(f"{slice_name}: checked marker written; U24_KEEP_RUNS=1 keeps the evidence")
        else:
            log(f"{slice_name}: check/control failed; run and replay directories kept")
        if check_time.get("memory_stop") or control_time.get("memory_stop") or evidence_time.get("memory_stop"):
            log("memory guard stopped the worker; remaining slices not started")
            return 8 if push_bad else 7
    log(f"finished: checks failed {bad}; pushes failed {push_bad}")
    return 8 if push_bad else 7 if bad else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        log(f"precondition/receipt error: {error}; run directories kept")
        raise SystemExit(2)
