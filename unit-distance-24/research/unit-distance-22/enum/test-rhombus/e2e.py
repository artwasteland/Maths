#!/usr/bin/env python3
"""End to end: run-dag2.py --reach --prune --prune-filter-only [--rhombus] on small targets.

The rhombus checker is the REAL one: check/udcheck_rhombus.py (written blind by another agent from
RHOMBUS-SPEC.md, landed 81ff2c66e), copied into the scratch tree with its pinned kernels and checked by
sha256 against the tree's; PRUNE_UDCHECK_RHOMBUS is removed from every environment here, and each prune
manifest records the checker ("rhombus_checker": {"from_environment": false, ...}). (An earlier run of
this suite, runs/e2e-base-f2b9e38e4.txt, substituted the dev replay dev_replay_rhombus.py.)

All runs execute from a scratch copy of the tree, scratch/tree/research/unit-distance-22 (enum/
run-dag2.py, prune.py, udenum; filter/udfilter, udrhombus; check/; data/; embed/udembed.py and
exact_verify.py), so that the landed scripts (git BASE_COMMIT) and this tree's can be run at the
same paths into the same output directory, one after the other, and their outputs compared file by
file. The copies of the new scripts and binaries are checked by sha256 against this tree's.

I  Default off: without --rhombus the new scripts change nothing. Target (16,41), in Mode 398 with
   the runbook's options (--reach, --prune --prune-from 12 --prune-filter-only, --verify-stages) and
   in Mode 74 (the u(22) options). The landed scripts run into OUT, OUT is renamed, the new scripts
   run into OUT again. PASS iff the two directories hold the same files, every non-JSON file is
   byte-identical (level, reach, keep, UNKNOWN, certs, parent, shard, slice files), and every JSON
   file (manifests, run-config, run-summary, reach.json, stats, prune logs) is identical after
   removing only the fields that must differ: timestamps and timings (started, finished,
   *wall_seconds, cpu_seconds, max_rss_kib) and the sha256 of prune.py and run-dag2.py themselves.
   Every normalised field is counted and listed, so nothing else can hide there.
IR Red controls on I's comparison (phase_identity_red), each planted in a copy of the new Mode 74
   directory: a keep file one line short (alone, and consistently, with its prune manifest's hash of
   it updated as a real change would), a tu certificate turned unknown (consistently), a new key and a
   changed count in a prune manifest. Each must be reported, and in the consistent cases the manifest
   too: the hash renaming applies only to hashes of files already shown equivalent, so it cannot mask
   a real difference.
C  Controls with the rules: (16,41) in both modes, (17,43) and (18,46) in Mode 74 (prune from 12),
   each without a rule, with --rhombus and with --triangles, reporting wall times. PASS iff every
   run exits 0, every known extremal graph of the target order (sources/amp/anc/graph6.txt,
   canonical form: 1, 7 and 16) is in the top level's keep file in all three runs, the keep files
   are nested at every level, keep(--triangles) <= keep(--rhombus) <= keep(none) as sets (the rules
   only remove, and udtriangle's verdicts contain udrhombus's), every prune manifest of a rule run
   names the rule and the real checker (not from the environment) and no prover failure (rhombus: no
   silent pass; triangles: triangles_stats has refuted, tu, pass, open, budget, verify_fail,
   lift_fail and internal, the last three 0, and tri_silent_passes counts budget + failures), and
   verify-chain.py --check (which replays rule runs with check/udcheck_rhombus.py, tri records
   through its pinned tri_verify.py) says CHAIN OK for all twelve runs.
R  Red controls, on the (17,43) rhombus run, each restored byte for byte afterwards:
   R1 a coefficient of one rhombus certificate changed: verify-chain --check must fail;
   R2 the prune manifest of a level with its "rhombus" flag removed: verify-chain must fail;
   R3 prune.py --rhombus with a wrapper prover that corrupts one certificate: prune.py must go RED
      (exit 1, the checker's rejection in the manifest's problems);
   R4 run-dag2.py --rhombus without --prune, and --resume of a no-rhombus directory with --rhombus:
      both refused before any work.
   The chain checker both ways (SPEC amendment 2): C shows verify-chain --check replaying rhombus runs
   with the rules' checker; and it must REFUSE, with and without --check,
   R5 the (17,43) rhombus run with the flag removed from run-config.json and from every prune and
      aggregate manifest (the certs files still hold rhombus witnesses the manifests do not record);
   R6 the rhombus run with one rhombus witness renamed "tri" (a rule the run does not record);
   R7 the plain (17,43) run with one gadget witness replaced by a rhombus witness.
   R8 silent passes are counted (SPEC amendment 2): prune.py --rhombus with a prover wrapper that turns
      two detections into passes and reports them as certificate failures must exit 0, keep the two
      graphs, record rhombus_silent_passes = 2 in the manifest and its counts, and warn on stderr.
   R9 the target (the checker never sees it): prune.py --rhombus at (18,45), below u(18) <= 46, and at
      (13,30), with no proved bound, must exit 2 before writing anything; verify-chain must refuse the
      (17,43) rhombus run with its target lowered to (17,42) (in run-config.json, run-summary.json and
      reach.json alike), with and without --check.
   R10 the (17,43) triangles run with one tri witness replaced by a rhombus witness (a rule the run does
      not record): verify-chain must refuse, with and without --check.
   R11 --rhombus with --triangles: run-dag2.py and prune.py refuse before any work.

usage: e2e.py [--phases I,C,R] [--jobs 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from rhlib import HERE, REPO, SCRATCH, UD, canonical, decode_g6, g6_lines, known_graphs, log

BASE_COMMIT = "81ff2c66e"          # origin/claude/answering-alexeev-u22 under this work (was f2b9e38e4 at first)
CHECKER_REL = "check/udcheck_rhombus.py"   # the real checker, copied into the scratch tree
MATHS_PY = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"
TREE = SCRATCH / "tree" / "research" / "unit-distance-22"
RUNS = SCRATCH / "e2e"
VOLATILE = {"started", "finished", "wall_seconds", "step_wall_seconds", "geng_wall_seconds",
            "filter_wall_seconds", "outer_wall_seconds", "cpu_seconds", "max_rss_kib"}
problems: list[str] = []


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_env() -> dict:
    env = dict(os.environ)
    env.pop("PRUNE_UDCHECK_RHOMBUS", None)
    return env


def git_show(rel: str) -> bytes:
    return subprocess.run(["git", "show", f"{BASE_COMMIT}:research/unit-distance-22/{rel}"], cwd=REPO,
                          capture_output=True, check=True).stdout


def build_tree() -> None:
    if TREE.exists():
        shutil.rmtree(TREE.parent.parent)
    for rel in ("enum/udenum", "filter/udfilter", "filter/udrhombus", "check/udcheck.py", "check/udcheck398.py",
                CHECKER_REL, "check/tri_verify.py", "filter/udtriangle", "embed/udembed.py", "embed/exact_verify.py"):
        (TREE / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(UD / rel, TREE / rel)
    shutil.copytree(UD / "data", TREE / "data")
    install_scripts("new")


def install_scripts(which: str) -> None:
    for rel in ("enum/run-dag2.py", "enum/prune.py"):
        data = git_show(rel) if which == "base" else (UD / rel).read_bytes()
        (TREE / rel).write_bytes(data)
    for rel in ("enum/udenum", "filter/udfilter", "filter/udrhombus", "check/udcheck.py", "check/udcheck398.py",
                CHECKER_REL, "check/tri_verify.py", "filter/udtriangle", "data/forbidden-398.json"):
        if sha256(TREE / rel) != sha256(UD / rel):
            raise SystemExit(f"scratch tree copy of {rel} differs from the tree's")


def run_dag(out: Path, target: tuple[int, int], mode: int, rule, jobs: int, extra=(),
            expect_ok: bool = True) -> tuple[int, float, str]:
    """rule: None or False (no linear rule), True or "rhombus", or "triangles"."""
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "run-dag2.py"), "--target-n", str(target[0]),
           "--target-m", str(target[1]), "--output-dir", str(out), "--jobs", str(jobs), "--reach",
           "--prune", "--prune-from", "12", "--prune-filter-only", "--prune-python", str(MATHS_PY), *extra]
    if mode == 398:
        cmd += ["--forbidden-set", "398", "--verify-stages"]
    if rule:
        cmd += ["--rhombus" if rule is True else f"--{rule}"]
    env = dict(os.environ)
    env.pop("PRUNE_UDCHECK_RHOMBUS", None)   # the real checker, prune.py's default
    t0 = time.monotonic()
    logf = out.parent / f"{out.name}.log"
    with logf.open("w") as stream:
        p = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    tail = logf.read_text().strip().splitlines()
    if expect_ok and p.returncode != 0:
        problems.append(f"run {out.name}: exit {p.returncode}: {tail[-1] if tail else ''}")
    return p.returncode, wall, tail[-1] if tail else ""


def normalise(obj, hashes: dict, counter: dict, path: str = ""):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in VOLATILE:
                counter[k] = counter.get(k, 0) + 1
                continue
            out[k] = normalise(v, hashes, counter, f"{path}.{k}")
        return out
    if isinstance(obj, list):
        return [normalise(v, hashes, counter, path) for v in obj]
    if isinstance(obj, str) and obj in hashes:
        counter[hashes[obj]] = counter.get(hashes[obj], 0) + 1
        return hashes[obj]
    return obj


def load_json_or_lines(path: Path):
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(x) for x in text.splitlines() if x.strip()]


def compare_dirs(base: Path, new: Path, hashes: dict) -> dict:
    """Byte comparison, then JSON comparison modulo VOLATILE keys and hash renaming, to a fixed point.

    A manifest hashes other files (shard manifests, udenum's verification manifests), and those
    files hold timestamps, so their hashes differ between two runs even when nothing else does. A
    pair of files found equivalent (byte-identical, or JSON-equal after normalising) contributes the
    renaming {sha256(base file) -> <file>, sha256(new file) -> <file>}; files are compared again
    until nothing changes. Only hashes of files PROVED equivalent are renamed, so a real difference
    in any output keeps every manifest that hashes it different too."""
    files_b = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
    files_n = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
    only_b, only_n = sorted(files_b - files_n), sorted(files_n - files_b)
    renaming = dict(hashes)
    status: dict = {}
    counter: dict = {}
    pending = sorted(files_b & files_n)
    changed = True
    while changed:
        changed = False
        for rel in pending:
            if rel in status:
                continue
            b, n = (base / rel).read_bytes(), (new / rel).read_bytes()
            kind = None
            if b == n:
                kind = "bytes"
            elif rel.suffix in (".json", ".log"):
                try:
                    local: dict = {}
                    if normalise(load_json_or_lines(base / rel), renaming, local) == \
                            normalise(load_json_or_lines(new / rel), renaming, local):
                        kind = "json"
                        for k, v in local.items():
                            counter[k] = counter.get(k, 0) + v
                except json.JSONDecodeError:
                    pass
            if kind:
                status[rel] = kind
                name = f"<sha256 of {rel}>"
                renaming[hashlib.sha256(b).hexdigest()] = name
                renaming[hashlib.sha256(n).hexdigest()] = name
                changed = True
    differ = [str(rel) for rel in pending if rel not in status]
    return {"files": len(files_b), "only_base": [str(x) for x in only_b[:10]], "only_new": [str(x) for x in only_n[:10]],
            "byte_identical": sum(1 for v in status.values() if v == "bytes"),
            "json_equal_after_normalising": sum(1 for v in status.values() if v == "json"),
            "different": differ[:20], "normalised": {k: v for k, v in counter.items() if not k.startswith("<sha256 of")},
            "hashes_of_equivalent_files_renamed": sum(v for k, v in counter.items() if k.startswith("<sha256 of"))}


def known_at(n: int, m: int) -> list[str]:
    return canonical([g for g in known_graphs() if decode_g6(g)[0] == n and len(decode_g6(g)[1]) == m])


def phase_identity(jobs: int) -> dict:
    RUNS.mkdir(parents=True, exist_ok=True)
    walls = {}
    hashes = {}
    for which in ("base", "new"):
        install_scripts(which)
        for rel in ("enum/prune.py", "enum/run-dag2.py"):
            hashes[sha256(TREE / rel)] = f"<{Path(rel).name} sha256>"
    for mode in (398, 74):
        out = RUNS / f"id-16-41-f{mode}"
        for which in ("base", "new"):
            install_scripts(which)
            shutil.rmtree(out, ignore_errors=True)
            code, wall, last = run_dag(out, (16, 41), mode, False, jobs)
            walls[f"16-41 mode {mode} {which}"] = round(wall, 1)
            log(f"I (16,41) mode {mode} {which} scripts: exit {code} after {wall:.0f} s")
            dest = RUNS / f"id-16-41-f{mode}-{which}"
            shutil.rmtree(dest, ignore_errors=True)
            out.rename(dest)
            (RUNS / f"{out.name}.log").rename(RUNS / f"{dest.name}.log")
        result = compare_dirs(RUNS / f"id-16-41-f{mode}-base", RUNS / f"id-16-41-f{mode}-new", hashes)
        log(f"I (16,41) mode {mode}: {json.dumps(result)}")
        if result["only_base"] or result["only_new"] or result["different"] or not result["files"]:
            problems.append(f"I mode {mode}: the new scripts without --rhombus changed the outputs: {result}")
    install_scripts("new")
    return walls


def phase_identity_red() -> None:
    """IR: the comparison of phase I must see a real difference. A copy of the Mode 74 'new'
    directory (the files hold absolute paths of OUT, like the original, so copying changes nothing
    the comparison reads) gets one change at a time: (a) the last line of a keep file dropped;
    (b) one certificate record's verdict tu -> unknown; (c) a new key in one prune manifest; (d) a
    changed count in one prune manifest. Each must be reported, (a) and (b) together with the
    manifests that hash the changed file."""
    base = RUNS / "id-16-41-f74-base"
    new = RUNS / "id-16-41-f74-new"
    hashes = {}
    for which in ("base", "new"):
        install_scripts(which)
        for rel in ("enum/prune.py", "enum/run-dag2.py"):
            hashes[sha256(TREE / rel)] = f"<{Path(rel).name} sha256>"
    install_scripts("new")
    keep = sorted(new.glob("*.keep.g6"), key=lambda p: -p.stat().st_size)[0]
    stem = keep.name.split(".")[0]

    def drop_last(p: Path) -> None:
        lines = p.read_text().splitlines(keepends=True)
        p.write_text("".join(lines[:-1]))

    def tu_to_unknown(p: Path) -> None:
        lines = p.read_text().splitlines(keepends=True)
        i = next(k for k, x in enumerate(lines) if '"verdict":"tu"' in x)
        r = json.loads(lines[i])
        lines[i] = json.dumps({"g6": r["g6"], "verdict": "unknown"}, separators=(",", ":"), sort_keys=True) + "\n"
        p.write_text("".join(lines))

    def new_key(p: Path) -> None:
        v = json.loads(p.read_text())
        v["rhombus"] = True
        p.write_text(json.dumps(v, indent=2) + "\n")

    def count_changed(p: Path) -> None:
        v = json.loads(p.read_text())
        v["counts"]["kept"] += 1
        p.write_text(json.dumps(v, indent=2) + "\n")
    manifest = f"{stem}.prune.manifest.json"
    for label, rel, fn, consistent in (("a keep file one line short", keep.name, drop_last, False),
                                       ("a keep file one line short, and its manifest's hash of it updated",
                                        keep.name, drop_last, True),
                                       ("a tu certificate turned unknown, and its manifest's hash of it updated",
                                        f"{stem}.certs.jsonl", tu_to_unknown, True),
                                       ("a new key in a prune manifest", manifest, new_key, False),
                                       ("a changed count in a prune manifest", manifest, count_changed, False)):
        copy = RUNS / "id-red-copy"
        shutil.rmtree(copy, ignore_errors=True)
        shutil.copytree(new, copy)
        old_hash = sha256(copy / rel)
        fn(copy / rel)
        if consistent:   # a real output change: the manifest names the changed file's new hash
            text = (copy / manifest).read_text()
            if old_hash not in text:
                raise SystemExit(f"IR: {manifest} does not hash {rel}")
            (copy / manifest).write_text(text.replace(old_hash, sha256(copy / rel)))
        result = compare_dirs(base, copy, hashes)
        seen = rel in result["different"]
        others = [x for x in result["different"] if x != rel]
        log(f"IR {label} ({rel}): reported {seen}; also reported: {others[:6]}")
        # the hash renaming must never mask a consistent change: the manifest that names the changed
        # file's new hash is reported too (a hash of a file NOT shown equivalent is never renamed)
        if not seen or (consistent and manifest not in others):
            problems.append(f"IR {label}: the comparison did not report the change"
                            f"{' and the manifest naming its new hash' if consistent else ''}")
    shutil.rmtree(RUNS / "id-red-copy", ignore_errors=True)


def top_keep_check(out: Path, n: int, m: int, label: str) -> None:
    keep = out / f"{n}-{m}.keep.g6"
    kept = set(g6_lines(keep)) if keep.is_file() else set()
    known = known_at(n, m)
    present = sum(1 for g in known if g in kept)
    log(f"C {label}: top keep {n}-{m}: {len(kept)} graphs; known ({n},{m}) graphs present {present}/{len(known)}")
    if present != len(known) or not known:
        problems.append(f"C {label}: a known extremal graph is missing from the top keep file")


def chain(out: Path, label: str) -> None:
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "verify-chain.py"), str(out), "--check"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    lines = p.stdout.strip().splitlines()
    log(f"C {label}: verify-chain --check: exit {p.returncode}: {lines[-1] if lines else p.stderr.strip()[-200:]}; "
        f"{lines[0][:260] if lines else ''}")
    if p.returncode != 0 or not lines or lines[-1] != "CHAIN OK":
        problems.append(f"C {label}: verify-chain: {[x for x in lines if x.startswith('PROBLEM')][:3]}")


RULE_FIELDS = {"rhombus": ("rhombus", ("certificate_failures",)),
               "triangles": ("tri", ("verify_fail", "lift_fail", "internal"))}   # count prefix, failure fields
TRI_STATS = ("refuted", "tu", "pass", "open", "budget", "verify_fail", "lift_fail", "internal")


def phase_controls(jobs: int) -> dict:
    RUNS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(UD / "enum" / "verify-chain.py", TREE / "enum" / "verify-chain.py")
    install_scripts("new")
    walls = {}
    for target, mode in (((16, 41), 398), ((16, 41), 74), ((17, 43), 74), ((18, 46), 74)):
        base = f"c-{target[0]}-{target[1]}-f{mode}"
        runs = {None: RUNS / base, "rhombus": RUNS / f"{base}-rh", "triangles": RUNS / f"{base}-tri"}
        for rule, out in runs.items():
            shutil.rmtree(out, ignore_errors=True)
            code, wall, last = run_dag(out, target, mode, rule, jobs)
            walls[out.name] = round(wall, 1)
            log(f"C {out.name}: exit {code} after {wall:.0f} s")
            top_keep_check(out, *target, out.name)
        # per level: keep(tri) <= keep(rh) <= keep(plain), since udtriangle's verdicts contain udrhombus's and
        # both only remove; every prune manifest of a rule run names the rule, the real checker and no failure
        rows = []
        for keep in sorted(runs[None].glob("*.keep.g6"), key=lambda q: tuple(map(int, q.name.split(".")[0].split("-")))):
            stem = keep.name.split(".")[0]
            sets = {rule: (set(g6_lines(out / keep.name)) if (out / keep.name).is_file() else set())
                    for rule, out in runs.items()}
            detail = []
            for rule in ("rhombus", "triangles"):
                out = runs[rule]
                prefix, failures = RULE_FIELDS[rule]
                mpath = out / f"{stem}.prune.manifest.json"
                pm = json.loads(mpath.read_text()) if mpath.is_file() else {}
                c = pm.get("counts", {})
                stats = pm.get(f"{rule}_stats", {})
                detail.append(f"{rule} keep {len(sets[rule])} ({prefix}_tu {c.get(f'{prefix}_tu')}, "
                              f"{prefix}_refuted {c.get(f'{prefix}_refuted')}, silent {c.get(f'{prefix}_silent_passes')})")
                if not pm:
                    continue
                checker = pm.get(f"{rule}_checker", {})
                if pm.get(rule) is not True or checker.get("from_environment") is not False or \
                        checker.get("path") != str(TREE / CHECKER_REL):
                    problems.append(f"C {out.name} {stem}: prune manifest does not record the rule and the real checker")
                if any(stats.get(f, 0) for f in failures):
                    problems.append(f"C {out.name} {stem}: prover failures {[(f, stats.get(f)) for f in failures]}")
                if rule == "rhombus" and (pm.get("rhombus_silent_passes") != 0 or c.get("rhombus_silent_passes") != 0):
                    problems.append(f"C {out.name} {stem}: silent passes {pm.get('rhombus_silent_passes')} (expected 0)")
                if rule == "triangles" and (any(f not in stats for f in TRI_STATS) or
                                            c.get("tri_silent_passes") != stats.get("budget", 0) + sum(stats.get(f, 0) for f in failures)):
                    problems.append(f"C {out.name} {stem}: triangles_stats {stats} lacks a field or the silent count")
            chain_ok = sets["triangles"] <= sets["rhombus"] <= sets[None]
            rows.append(f"{stem}: plain keep {len(sets[None])}; " + "; ".join(detail) + f"; tri <= rh <= plain {chain_ok}")
            if not chain_ok:
                problems.append(f"C {base} {stem}: the keep files are not nested tri <= rh <= plain")
        for row in rows:
            log("   ", row)
        for rule, out in runs.items():
            chain(out, out.name)
    return walls


def tamper(path: Path, fn, label: str, run_dir: Path, expect: str) -> None:
    original = path.read_bytes()
    try:
        path.write_bytes(fn(original))
        p = subprocess.run(["nice", "-n", "10", sys.executable, str(TREE / "enum" / "verify-chain.py"), str(run_dir),
                            "--check"], capture_output=True, text=True, env=clean_env())
        lines = p.stdout.strip().splitlines()
        probs = [x for x in lines if x.startswith("PROBLEM")]
        log(f"R {label}: verify-chain exit {p.returncode}: {lines[-1] if lines else ''}; {probs[:2]}")
        if p.returncode == 0 or not any(expect in x for x in probs):
            problems.append(f"R {label}: verify-chain did not fail as expected ({expect})")
    finally:
        path.write_bytes(original)
    if path.read_bytes() != original:
        problems.append(f"R {label}: {path} not restored")


def phase_red(jobs: int) -> None:
    rh = RUNS / "c-17-43-f74-rh"
    shutil.copy2(UD / "enum" / "verify-chain.py", TREE / "enum" / "verify-chain.py")
    install_scripts("new")
    # R1: a coefficient of the first rhombus certificate found
    target = None
    for certs in sorted(rh.glob("*.certs.jsonl")):
        for i, line in enumerate(certs.read_text().splitlines()):
            if '"rhombus"' in line:
                target = (certs, i)
                break
        if target:
            break
    certs, index = target

    def bump(data: bytes) -> bytes:
        lines = data.decode().split("\n")
        r = json.loads(lines[index])
        r["witness"]["rhombus"]["coefficients"][0] += 1 if r["witness"]["rhombus"]["coefficients"][0] != -1 else 2
        lines[index] = json.dumps(r, separators=(",", ":"), sort_keys=True)
        return "\n".join(lines).encode()
    stem = certs.name.split(".")[0]
    tamper(certs, bump, f"R1 {certs.name} line {index + 1} coefficient changed", rh, "did not accept")
    # R2: the rhombus flag removed from that level's prune manifest
    pm = rh / f"{stem}.prune.manifest.json"

    def unflag(data: bytes) -> bytes:
        v = json.loads(data)
        v.pop("rhombus")
        return (json.dumps(v, indent=2) + "\n").encode()
    tamper(pm, unflag, f"R2 {pm.name} without its rhombus flag", rh, "rhombus setting")
    # R3: prune.py with a prover wrapper that corrupts the first certificate it writes
    work = RUNS / "red-r3"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    source = rh / f"{stem}.reach.g6"
    level = work / source.name
    shutil.copy2(source, level)
    wrapper = work / "udrhombus-corrupt.py"
    wrapper.write_text(f"""#!{sys.executable}
import json, subprocess, sys
p = subprocess.run([{str(TREE / 'filter' / 'udrhombus')!r}], stdin=sys.stdin.buffer, capture_output=True)
done = False
for line in p.stdout.decode().splitlines():
    r = json.loads(line)
    if not done and r["verdict"] != "pass":
        r["witness"]["rhombus"]["scale"] *= 2
        done = True
    sys.stdout.write(json.dumps(r, separators=(",", ":")) + "\\n")
sys.stderr.write(p.stderr.decode())
sys.exit(p.returncode)
""")
    wrapper.chmod(0o755)
    env = clean_env()
    n, m = map(int, stem.split("-"))
    p = subprocess.run(["nice", "-n", "10", sys.executable, str(TREE / "enum" / "prune.py"), "--level", str(level),
                        "--target-n", "17", "--target-m", "43", "--jobs", "1", "--filter-only", "--rhombus",
                        "--udrhombus", str(wrapper), "--python", str(MATHS_PY)], capture_output=True, text=True, env=env)
    man = json.loads((work / f"{stem}.prune.manifest.json").read_text()) if (work / f"{stem}.prune.manifest.json").is_file() else {}
    log(f"R3 prune.py with a corrupting prover wrapper: exit {p.returncode}; manifest exit_status "
        f"{man.get('exit_status')}; problems {str(man.get('problems'))[:220]}")
    if p.returncode != 1 or man.get("exit_status") != 1 or "REJECT" not in str(man.get("problems")):
        problems.append("R3: prune.py did not go red on a corrupted rhombus certificate")
    # R4: refusals
    out = RUNS / "red-r4"
    shutil.rmtree(out, ignore_errors=True)
    cmd = [sys.executable, str(TREE / "enum" / "run-dag2.py"), "--target-n", "17", "--target-m", "43",
           "--output-dir", str(out), "--reach", "--rhombus"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    log(f"R4 --rhombus without --prune: exit {p.returncode}: {p.stderr.strip()[-120:]}; directory made {out.exists()}")
    if p.returncode != 2 or out.exists():
        problems.append("R4: --rhombus without --prune was not refused before any work")
    plain = RUNS / "c-17-43-f74"
    before = {q: q.stat().st_mtime_ns for q in plain.rglob("*") if q.is_file()}
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "run-dag2.py"), "--target-n", "17", "--target-m", "43",
           "--output-dir", str(plain), "--reach", "--prune", "--prune-from", "12", "--prune-filter-only",
           "--prune-python", str(MATHS_PY), "--rhombus", "--resume"]
    p = subprocess.run(cmd, capture_output=True, text=True, env=clean_env())
    after = {q: q.stat().st_mtime_ns for q in plain.rglob("*") if q.is_file()}
    log(f"R4 --resume of a no-rhombus directory with --rhombus: exit {p.returncode}: {p.stderr.strip()[-120:]}; "
        f"files touched {sum(1 for q in after if before.get(q) != after[q])}")
    if p.returncode != 2 or before != after:
        problems.append("R4: a no-rhombus directory was resumed with --rhombus")
    red_chain(rh, plain)
    red_silent(rh)
    red_target(rh)
    red_rules(rh, RUNS / "c-17-43-f74-tri")


def red_rules(rh: Path, tri: Path) -> None:
    """R10, R11: the two rules do not mix."""
    newline = chr(10)
    rcerts, rindex = first_rhombus_record(rh)
    rh_witness = json.loads(rcerts.read_text().split(newline)[rindex])["witness"]
    target = None
    for certs in sorted(tri.glob("*.certs.jsonl")):
        for i, line in enumerate(certs.read_text().split(newline)):
            if '"tri"' in line:
                target = (certs, i)
                break
        if target:
            break
    certs, index = target

    def swap(data: bytes) -> bytes:
        lines = data.decode().split(newline)
        r = json.loads(lines[index])
        r["witness"] = rh_witness
        lines[index] = json.dumps(r, separators=(",", ":"), sort_keys=True)
        return newline.join(lines).encode()
    tamper_many({certs: swap}, f"R10 a rhombus witness in the triangles run's {certs.name}", tri,
                "do not record --rhombus: refused")
    red = RUNS / "red-r11"
    shutil.rmtree(red, ignore_errors=True)
    p = subprocess.run([sys.executable, str(TREE / "enum" / "run-dag2.py"), "--target-n", "17", "--target-m", "43",
                        "--output-dir", str(red), "--reach", "--prune", "--rhombus", "--triangles"],
                       capture_output=True, text=True, env=clean_env())
    log(f"R11 run-dag2.py --rhombus --triangles: exit {p.returncode}: {p.stderr.strip()[-120:]}; directory made {red.exists()}")
    if p.returncode != 2 or red.exists() or "at most one linear rule" not in p.stderr:
        problems.append("R11: run-dag2.py accepted --rhombus with --triangles")
    level = RUNS / "red-r11-prune" / "12-22.reach.g6"
    level.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rh / "12-22.reach.g6", level)
    p = subprocess.run([sys.executable, str(TREE / "enum" / "prune.py"), "--level", str(level), "--target-n", "17",
                        "--target-m", "43", "--filter-only", "--rhombus", "--triangles"], capture_output=True, text=True,
                       env=clean_env())
    written = sorted(q.name for q in level.parent.iterdir() if q.name != level.name)
    log(f"R11 prune.py --rhombus --triangles: exit {p.returncode}: {p.stderr.strip()[-100:]}; files written {written}")
    if p.returncode != 2 or "at most one linear rule" not in p.stderr or written:
        problems.append("R11: prune.py accepted --rhombus with --triangles")


def red_target(rh: Path) -> None:
    """R9: the checker never sees the target, so prune.py must refuse --rhombus at a target without a
    proved bound, and verify-chain must refuse a run whose target is below it."""
    work = RUNS / "red-r9"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    level = work / "12-22.reach.g6"
    shutil.copy2(rh / "12-22.reach.g6", level)
    for target, why in (((18, 45), "lies below the proved bound"), ((13, 30), "no proved upper bound")):
        p = subprocess.run(["nice", "-n", "10", sys.executable, str(TREE / "enum" / "prune.py"), "--level", str(level),
                            "--target-n", str(target[0]), "--target-m", str(target[1]), "--filter-only", "--rhombus",
                            "--python", str(MATHS_PY)], capture_output=True, text=True, env=clean_env())
        written = sorted(q.name for q in work.iterdir() if q.name != level.name)
        log(f"R9 prune.py --rhombus at target {target}: exit {p.returncode}: {p.stderr.strip()[-110:]}; "
            f"files written {written}")
        if p.returncode != 2 or why not in p.stderr or written:
            problems.append(f"R9: prune.py --rhombus was not refused at target {target}")

    def lower(data: bytes) -> bytes:
        v = json.loads(data)
        v["target"] = [17, 42]
        return (json.dumps(v, indent=2) + "\n").encode()
    # the target lowered in all three files that name it (verify-chain.py derives the cells from run-config.json's
    # target and refuses a summary or reach.json that names another)
    tamper_many({rh / name: lower for name in ("run-config.json", "run-summary.json", "reach.json")},
                "R9 the run's target lowered to (17,42) in run-config.json, run-summary.json and reach.json", rh,
                "below the proved bound")


def verify_chain_run(run_dir: Path, check: bool) -> tuple[int, list[str]]:
    cmd = ["nice", "-n", "10", sys.executable, str(TREE / "enum" / "verify-chain.py"), str(run_dir)] + \
        (["--check"] if check else [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=clean_env())
    return p.returncode, p.stdout.strip().splitlines()


def tamper_many(edits: dict, label: str, run_dir: Path, expect: str) -> None:
    """Apply {path: function(bytes) -> bytes} together, run verify-chain without and with --check,
    restore every file byte for byte. Both runs must fail with a problem containing `expect`."""
    originals = {path: path.read_bytes() for path in edits}
    try:
        for path, fn in edits.items():
            path.write_bytes(fn(originals[path]))
        for check in (False, True):
            code, lines = verify_chain_run(run_dir, check)
            probs = [x for x in lines if x.startswith("PROBLEM")]
            hit = [x for x in probs if expect in x]
            log(f"R {label} ({'--check' if check else 'no --check'}): verify-chain exit {code}: "
                f"{lines[-1] if lines else ''}; {len(probs)} problems; e.g. {(hit or probs or [''])[0][:230]}")
            if code == 0 or not hit:
                problems.append(f"R {label}: verify-chain did not refuse ({'with' if check else 'without'} --check)")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)
    if any(path.read_bytes() != data for path, data in originals.items()):
        problems.append(f"R {label}: files not restored")


def red_chain(rh: Path, plain: Path) -> None:
    def unflag(data: bytes) -> bytes:
        v = json.loads(data)
        v.pop("rhombus", None)
        if isinstance(v.get("pruning"), dict):
            v["pruning"].pop("rhombus", None)
        return (json.dumps(v, indent=2) + "\n").encode()
    manifests = [rh / "run-config.json", *sorted(rh.glob("*.prune.manifest.json")),
                 *[p for p in sorted(rh.glob("*.manifest.json")) if not p.name.endswith((".prune.manifest.json",
                   ".reach.manifest.json", ".verify.manifest.json")) and "slice" not in p.name
                   and "pruning" in json.loads(p.read_text())]]
    tamper_many({p: unflag for p in manifests}, f"R5 the rhombus flag removed from {len(manifests)} manifests",
                rh, "do not record --rhombus: refused")

    certs, index = first_rhombus_record(rh)

    def to_tri(data: bytes) -> bytes:
        lines = data.decode().split("\n")
        r = json.loads(lines[index])
        r["witness"] = {"tri": r["witness"]["rhombus"]}
        lines[index] = json.dumps(r, separators=(",", ":"), sort_keys=True)
        return "\n".join(lines).encode()
    tamper_many({certs: to_tri}, f"R6 a rhombus witness renamed tri in {certs.name}", rh,
                "do not record --triangles: refused")

    # R7: the plain run's first gadget-tu record of a level also present in the rhombus run gets that
    # run's rhombus witness for the same graph if it has one, else any rhombus witness
    rh_witness = json.loads(certs.read_text().split("\n")[index])["witness"]
    target = None
    for pc in sorted(plain.glob("*.certs.jsonl")):
        for i, line in enumerate(pc.read_text().split("\n")):
            if '"verdict":"tu"' in line:
                target = (pc, i)
                break
        if target:
            break
    pc, i = target

    def plant(data: bytes) -> bytes:
        lines = data.decode().split("\n")
        r = json.loads(lines[i])
        r["witness"] = rh_witness
        lines[i] = json.dumps(r, separators=(",", ":"), sort_keys=True)
        return "\n".join(lines).encode()
    tamper_many({pc: plant}, f"R7 a rhombus witness planted in the plain run's {pc.name}", plain,
                "do not record --rhombus: refused")


def first_rhombus_record(run_dir: Path) -> tuple[Path, int]:
    for certs in sorted(run_dir.glob("*.certs.jsonl")):
        for i, line in enumerate(certs.read_text().split("\n")):
            if '"rhombus"' in line:
                return certs, i
    raise SystemExit(f"no rhombus record in {run_dir}")


def red_silent(rh: Path) -> None:
    work = RUNS / "red-r8"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    stem = "12-22"
    level = work / f"{stem}.reach.g6"
    shutil.copy2(rh / f"{stem}.reach.g6", level)
    wrapper = work / "udrhombus-silent.py"
    wrapper.write_text(f"""#!{sys.executable}
import json, subprocess, sys
p = subprocess.run([{str(TREE / 'filter' / 'udrhombus')!r}], stdin=sys.stdin.buffer, capture_output=True)
out, done = [], 0
for line in p.stdout.decode().splitlines():
    r = json.loads(line)
    if done < 2 and r["verdict"] != "pass":
        stats_key = r["verdict"]
        r = {{"verdict": "pass"}}
        done += 1
        out.append((json.dumps(r, separators=(",", ":")), stats_key))
    else:
        out.append((json.dumps(r, separators=(",", ":")), None))
for line, _ in out:
    sys.stdout.write(line + "\\n")
lines = p.stderr.decode().strip().splitlines()
s = json.loads(lines[-1])
st = s["udrhombus_stats"]
for _, key in out:
    if key:
        st[key] -= 1; st["pass"] += 1; st["certificate_failures"] += 1; st["failure_self_check"] += 1
sys.stderr.write("\\n".join(lines[:-1] + [json.dumps(s, separators=(",", ":"))]) + "\\n")
sys.exit(p.returncode)
""")
    wrapper.chmod(0o755)
    env = clean_env()
    p = subprocess.run(["nice", "-n", "10", sys.executable, str(TREE / "enum" / "prune.py"), "--level", str(level),
                        "--target-n", "17", "--target-m", "43", "--jobs", "1", "--filter-only", "--rhombus",
                        "--udrhombus", str(wrapper), "--python", str(MATHS_PY)], capture_output=True, text=True, env=env)
    man = json.loads((work / f"{stem}.prune.manifest.json").read_text())
    plain_man = json.loads((rh / f"{stem}.prune.manifest.json").read_text())
    kept_more = man["counts"]["kept"] - plain_man["counts"]["kept"]
    log(f"R8 prune.py with a prover that passes 2 detections silently: exit {p.returncode}; "
        f"rhombus_silent_passes {man.get('rhombus_silent_passes')} (counts {man['counts'].get('rhombus_silent_passes')}); "
        f"kept {man['counts']['kept']} = the real run's {plain_man['counts']['kept']} + {kept_more}; "
        f"warning on stderr {'WARNING' in p.stderr}; checker {man.get('checker', '')[:120]}")
    if (p.returncode != 0 or man.get("rhombus_silent_passes") != 2 or man["counts"].get("rhombus_silent_passes") != 2
            or kept_more != 2 or "WARNING" not in p.stderr):
        problems.append("R8: silent passes are not counted into the manifest")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phases", default="I,C,R")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--keep-tree", action="store_true")
    a = ap.parse_args()
    phases = a.phases.split(",")
    if not a.keep_tree or not TREE.exists():
        build_tree()
    log(f"scratch tree {TREE}: new scripts prune.py {sha256(UD / 'enum/prune.py')[:12]}, run-dag2.py "
        f"{sha256(UD / 'enum/run-dag2.py')[:12]}; landed ({BASE_COMMIT}) prune.py "
        f"{hashlib.sha256(git_show('enum/prune.py')).hexdigest()[:12]}, run-dag2.py "
        f"{hashlib.sha256(git_show('enum/run-dag2.py')).hexdigest()[:12]}; the rhombus checker is {CHECKER_REL} (sha256 {sha256(UD / CHECKER_REL)[:12]}, the real one)")
    walls = {}
    if "I" in phases:
        walls.update(phase_identity(a.jobs))
    if "IR" in phases:
        phase_identity_red()
    if "C" in phases:
        walls.update(phase_controls(a.jobs))
    if "R" in phases:
        phase_red(a.jobs)
    log(f"wall seconds: {json.dumps(walls)}")
    for p in problems:
        log("PROBLEM:", p)
    log("E2E", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
