#!/usr/bin/env python3
"""udfilter with UDF_MAX_VERTICES = 24 (hosts of the u(23) top level): controls.

The change is one constant (22 -> 24) plus two static assertions. Every host structure is a
row of uint32_t bitmasks, so hosts of up to 32 vertices fit; nothing else is sized by it.

Part 1, byte identity on every host of at most 22 vertices. Binaries: NEW (this tree), BASE (the
landed Mode-398 build b0947a10, REPORT-398.md) and ORIG (the u(22) production build d4ccae3f,
enum/test-398/old). PASS iff, on every input, NEW, NEW -s 74, BASE, BASE -s 74 and ORIG write
the same bytes, and NEW -s 398 writes the same bytes as BASE -s 398. Inputs: B10 (33,162),
AMP's 56 known graphs, the parent and child files of the 21 cells of REPORT-398.md Section 4.2
(out-22/dag-22-61 levels 11-12, out-sup/dag-18-46 levels 15-18), the 743 level-21 keep graphs
and the 4 (22,61) graphs of the 48 u(22) slices, and the 20,000-graph (13,23) sample.

Part 2, filter/selfcheck.py on NEW: output identical to the recorded output of the landed build
(enum/test-398/runs/filter-selfcheck-new-binary.txt).

Part 3, hosts of 23 and 24 vertices (BASE must refuse every one of them: exit 2):
  3a lifted: every Part-1 host of the u(22) top cells, AMP's graphs and a cell sample, with
     isolated vertices appended to reach 23 and 24 vertices: NEW's record must equal its record
     for the original host (verdict and witness), in both sets. An isolated vertex is never a
     candidate (every pattern vertex has degree >= 1), so the search must be the same.
  3b relabelled: the lifted 23-vertex hosts under a seeded random permutation: same verdict
     class, and every witness re-verified in Python.
  3c dense 23-vertex hosts: each (22,61) graph plus a vertex of degree 4 or 5, each (21,56)
     keep graph plus two vertices, and random 23-vertex graphs with 60 to 66 edges. Decided
     independently: forbidden by GP-10's matcher widened to 31 vertices (matcher32, chained over
     chunks of <= 128 patterns, as in REPORT-398.md), then tu by a Python monomorphism search
     with the pair constraint written here; verdict and member/gadget index must equal NEW's,
     and every NEW witness is re-verified in Python. (Measured: every one of these hosts is
     forbidden in both sets, so 3c exercises only the forbidden path; Part 5 covers the rest.)
Part 5, hosts of 23 and 24 vertices free of the 398 by construction: unit-distance graphs of
  patches of the triangular lattice with a random share of edges deleted (so TU gadgets lose their
  forced pairs), a tenth with one extra edge. Decided independently as in 3c.
Part 4, an ASAN + UBSan build of NEW on all Part-3 and Part-5 hosts in both sets: exit 0, no
report, and the same bytes as NEW.

usage: filter-limit.py --baseline <landed udfilter> --slices <dir holding s0of48..s47of48>
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from u23lib import (DATA, ENUM, F398_G6, KNOWN, REPO, SCRATCH, UD, UDFILTER, decode_g6, encode_g6,
                    g6_lines, log, run_matcher, sha256, witness_ok, write_lines)

BASE_SHA256 = "b0947a10659b78059013d3d99ba22b8ddc116e9add7d3ce0c4e34c098407a09e"
ORIG = ENUM / "test-398" / "old" / "filter" / "udfilter"
ORIG_SHA256 = "d4ccae3ff45dcd2d45a64087bebb9519e901110c07fabd1661995b148cee600a"
F74_G6 = DATA / "forbidden-74.g6"
WORK = SCRATCH / "filter-limit"
F = {74: json.loads((DATA / "forbidden-74.json").read_text()),
     398: json.loads((DATA / "forbidden-398.json").read_text())}
T = json.loads((DATA / "tu-gadgets.json").read_text())
problems: list[str] = []


def flags(forbidden_set: int | None) -> list[str]:
    tu = ["-t", str(DATA / "tu-gadgets.json")]
    if forbidden_set is None:
        return ["-f", str(DATA / "forbidden-74.json"), *tu]
    return ["-s", str(forbidden_set), "-f", str(DATA / f"forbidden-{forbidden_set}.json"), *tu]


def run_filter(binary: Path, forbidden_set: int | None, hosts: Path, out: Path) -> tuple[int, str]:
    with hosts.open("rb") as stdin, out.open("wb") as stdout:
        p = subprocess.run(["nice", "-n", "15", str(binary), *flags(forbidden_set)], stdin=stdin,
                           stdout=stdout, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode(errors="replace").strip()


def records(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_bytes().split(b"\n") if x]


def part1(base: Path, slices: Path) -> dict[str, Path]:
    groups: dict[str, list[bytes]] = {}
    groups["B10"] = g6_lines(REPO / "research" / "gp-10" / "data" / "B10.g6")
    groups["known56"] = g6_lines(KNOWN)
    cells = []
    for d, names in ((ENUM / "out-22" / "dag-22-61", ["11-19", "11-20", "11-21", "11-22", "11-23",
                                                      "12-23", "12-24", "12-25", "12-26", "12-27"]),
                     (ENUM / "out-sup" / "dag-18-46", ["15-34", "15-35", "15-36", "15-37", "16-38", "16-39",
                                                       "16-40", "16-41", "17-42", "17-43", "18-46"])):
        for name in names:
            cells += g6_lines(d / "_parents" / f"{name}.g6") + g6_lines(d / f"{name}.g6")
    groups["cells"] = cells
    top = []
    for s in range(48):
        top += g6_lines(slices / f"s{s}of48" / "21-56.keep.g6") + g6_lines(slices / f"s{s}of48" / "22-61.g6")
    groups["u22top"] = top
    groups["sample-13-23"] = g6_lines(UD / "results" / "u22" / "sample-13-23-unpruned.g6")
    paths = {}
    for name, lines in groups.items():
        path = WORK / "p1" / f"{name}.g6"
        write_lines(path, lines)
        paths[name] = path
        orders = sorted({decode_g6(x)[0] for x in lines})
        outs = {}
        start = time.monotonic()
        for label, binary, s in (("NEW", UDFILTER, None), ("NEW-s74", UDFILTER, 74), ("BASE", base, None),
                                 ("BASE-s74", base, 74), ("ORIG", ORIG, None), ("NEW-s398", UDFILTER, 398),
                                 ("BASE-s398", base, 398)):
            out = WORK / "p1" / f"{name}.{label}.jsonl"
            code, err = run_filter(binary, s, path, out)
            if code != 0:
                problems.append(f"P1 {name}: {label} exited {code}: {err}")
            outs[label] = out.read_bytes()
        same74 = len({outs[k] for k in ("NEW", "NEW-s74", "BASE", "BASE-s74", "ORIG")}) == 1
        same398 = outs["NEW-s398"] == outs["BASE-s398"]
        if not same74:
            problems.append(f"P1 {name}: set-74 outputs differ between NEW, BASE and ORIG")
        if not same398:
            problems.append(f"P1 {name}: set-398 outputs differ between NEW and BASE")
        counts = {}
        for label in ("NEW", "NEW-s398"):
            c: dict[str, int] = {}
            for r in records(WORK / "p1" / f"{name}.{label}.jsonl"):
                c[r["verdict"]] = c.get(r["verdict"], 0) + 1
            counts[label] = c
        if sum(counts["NEW"].values()) != len(lines):
            problems.append(f"P1 {name}: NEW wrote {sum(counts['NEW'].values())} records for {len(lines)} hosts")
        log(f"P1 {name}: {len(lines)} hosts, orders {orders[0]}..{orders[-1]}; set 74 identical x5 {same74} "
            f"{counts['NEW']}; set 398 identical {same398} {counts['NEW-s398']} ({time.monotonic() - start:.0f} s)")
    return paths


def part2() -> None:
    # from filter/: udfilter's default data paths (-f, -t) are relative to the working directory
    p = subprocess.run([sys.executable, str(UD / "filter" / "selfcheck.py")], capture_output=True, text=True,
                       cwd=UD / "filter")
    recorded = (ENUM / "test-398" / "runs" / "filter-selfcheck-new-binary.txt").read_text()
    same = p.returncode == 0 and p.stdout == recorded
    if not same:
        problems.append(f"P2 selfcheck.py: exit {p.returncode}, output identical {p.stdout == recorded}")
    log(f"P2 filter/selfcheck.py on NEW: exit {p.returncode}; output identical to the recorded one: {same}")


def lift(line: bytes, n_new: int) -> bytes:
    n, edges = decode_g6(line)
    return encode_g6(n_new, edges)


def permute(line: bytes, rng: random.Random) -> bytes:
    n, edges = decode_g6(line)
    perm = list(range(n))
    rng.shuffle(perm)
    return encode_g6(n, [(perm[a], perm[b]) for a, b in edges])


def verify_record(host: bytes, record: dict, forbidden_set: int) -> bool:
    """Independent witness check: forbidden against the set's JSON; tu with its non-adjacent pair."""
    w = record.get("witness")
    if record["verdict"] == "pass":
        return w is None
    if record["verdict"] == "forbidden":
        idx = w["index"]
        return 0 <= idx < len(F[forbidden_set]) and witness_ok(host, F[forbidden_set][idx], w["map"])
    if record["verdict"] == "tu":
        g = T[w["index"]]
        if w.get("pair") != g["pair"] or not witness_ok(host, g["edges"], w["map"]):
            return False
        _, edges = decode_g6(host)
        a, b = w["map"][g["pair"][0]], w["map"][g["pair"][1]]
        return tuple(sorted((a, b))) not in edges
    return False


TU_CACHE: dict[bytes, tuple[int, list[int]] | None] = {}


def tu_search(line: bytes) -> tuple[int, list[int]] | None:
    if line not in TU_CACHE:
        TU_CACHE[line] = tu_search_uncached(line)
    return TU_CACHE[line]


def tu_search_uncached(line: bytes) -> tuple[int, list[int]] | None:
    """Lowest-index TU gadget with a non-adjacent pair, by a plain backtracking monomorphism
    search (no code shared with udfilter)."""
    n, edges = decode_g6(line)
    adj = [0] * n
    for a, b in edges:
        adj[a] |= 1 << b
        adj[b] |= 1 << a
    hdeg = [bin(x).count("1") for x in adj]
    for gi, g in enumerate(T):
        gn = g["n"]
        gadj = [0] * gn
        for a, b in g["edges"]:
            gadj[a] |= 1 << b
            gadj[b] |= 1 << a
        gdeg = [bin(x).count("1") for x in gadj]
        pa, pb = g["pair"]
        order, placed = [], 0
        while len(order) < gn:
            v = max((v for v in range(gn) if not (placed >> v) & 1),
                    key=lambda v: (bin(gadj[v] & placed).count("1"), gdeg[v], -v))
            order.append(v)
            placed |= 1 << v
        mp = [-1] * gn
        state = {"used": 0}

        def rec(k: int) -> bool:
            if k == gn:
                return True
            v = order[k]
            cand = ((1 << n) - 1) & ~state["used"]
            for u in range(gn):
                if mp[u] >= 0 and (gadj[v] >> u) & 1:
                    cand &= adj[mp[u]]
            while cand:
                h = (cand & -cand).bit_length() - 1
                cand &= cand - 1
                if hdeg[h] < gdeg[v]:
                    continue
                if v == pa and mp[pb] >= 0 and (adj[h] >> mp[pb]) & 1:
                    continue
                if v == pb and mp[pa] >= 0 and (adj[h] >> mp[pa]) & 1:
                    continue
                mp[v] = h
                state["used"] |= 1 << h
                if rec(k + 1):
                    return True
                mp[v] = -1
                state["used"] &= ~(1 << h)
            return False

        if rec(0):
            return gi, list(mp)
    return None


def part3(base: Path, paths: dict[str, Path], slices: Path) -> list[Path]:
    rng = random.Random(20260925)
    source = g6_lines(paths["u22top"]) + g6_lines(paths["known56"])
    cell_hosts = g6_lines(paths["cells"])
    source += rng.sample(cell_hosts, 3000)
    host_files = []
    # 3a lifted
    for n_new in (23, 24):
        lifted = [lift(x, n_new) for x in source]
        orig_path = WORK / "p3" / "source.g6"
        lifted_path = WORK / "p3" / f"lifted-{n_new}.g6"
        write_lines(orig_path, source)
        write_lines(lifted_path, lifted)
        host_files.append(lifted_path)
        code, err = run_filter(base, 398, lifted_path, WORK / "p3" / f"lifted-{n_new}.BASE.jsonl")
        if code != 2:
            problems.append(f"P3a: BASE did not refuse the {n_new}-vertex hosts (exit {code})")
        for s in (74, 398):
            run_filter(UDFILTER, s, orig_path, WORK / "p3" / f"source.{s}.jsonl")
            code, err = run_filter(UDFILTER, s, lifted_path, WORK / "p3" / f"lifted-{n_new}.{s}.jsonl")
            a = records(WORK / "p3" / f"source.{s}.jsonl")
            b = records(WORK / "p3" / f"lifted-{n_new}.{s}.jsonl")
            bad = sum(1 for x, y in zip(a, b)
                      if (x["verdict"], x.get("witness")) != (y["verdict"], y.get("witness")))
            if code != 0 or len(a) != len(b) or len(b) != len(source) or bad:
                problems.append(f"P3a: {n_new} vertices set {s}: exit {code}, {bad} records differ")
            verdicts: dict[str, int] = {}
            for y in b:
                verdicts[y["verdict"]] = verdicts.get(y["verdict"], 0) + 1
            log(f"P3a lifted to {n_new} vertices, set {s}: {len(b)} hosts, BASE refuses them (exit 2), "
                f"NEW records equal the originals' in verdict and witness: {bad == 0} {verdicts}")
    # 3b relabelled
    lifted23 = g6_lines(WORK / "p3" / "lifted-23.g6")
    perm = [permute(x, rng) for x in lifted23]
    perm_path = WORK / "p3" / "permuted-23.g6"
    write_lines(perm_path, perm)
    host_files.append(perm_path)
    for s in (74, 398):
        run_filter(UDFILTER, s, perm_path, WORK / "p3" / f"permuted-23.{s}.jsonl")
        a = records(WORK / "p3" / f"lifted-23.{s}.jsonl")
        b = records(WORK / "p3" / f"permuted-23.{s}.jsonl")
        differ = sum(1 for x, y in zip(a, b) if x["verdict"] != y["verdict"])
        unverified = sum(1 for h, y in zip(perm, b) if not verify_record(h, y, s))
        if len(b) != len(perm) or differ or unverified:
            problems.append(f"P3b set {s}: {differ} verdicts changed under relabelling, {unverified} witnesses fail")
        log(f"P3b relabelled 23-vertex hosts, set {s}: {len(b)} hosts, verdict classes unchanged: {differ == 0}, "
            f"witnesses re-verified: {len(b) - unverified}/{len(b)}")
    # 3c realistic 23-vertex hosts, decided independently
    hosts = []
    for x in g6_lines(slices.parent / "all-22-61.g6"):
        n, edges = decode_g6(x)
        for _ in range(60):
            nb = rng.sample(range(n), rng.choice((4, 5)))
            hosts.append(encode_g6(23, list(edges) + [(v, 22) for v in nb]))
    for x in g6_lines(slices.parent / "all-21-56.keep.g6"):
        n, edges = decode_g6(x)
        e = list(edges) + [(v, 21) for v in rng.sample(range(21), rng.choice((4, 5)))]
        e += [(v, 22) for v in rng.sample(range(22), rng.choice((4, 5)))]
        hosts.append(encode_g6(23, e))
    all_pairs = [(i, j) for j in range(1, 23) for i in range(j)]
    for _ in range(600):
        hosts.append(encode_g6(23, rng.sample(all_pairs, rng.randint(60, 66))))
    real_path = WORK / "p3" / "realistic-23.g6"
    write_lines(real_path, hosts)
    host_files.append(real_path)
    for s, patterns in ((398, F398_G6), (74, F74_G6)):
        code, err = run_filter(UDFILTER, s, real_path, WORK / "p3" / f"realistic-23.{s}.jsonl")
        new = records(WORK / "p3" / f"realistic-23.{s}.jsonl")
        matched = run_matcher(patterns, real_path, WORK / "p3" / f"matcher-{s}")
        disagree, unverified, verdicts = [], 0, {}
        for h, r in zip(hosts, new):
            if h in matched["removed"]:
                expected = ("forbidden", matched["removed"][h][0])
            else:
                found = tu_search(h)
                expected = ("tu", found[0]) if found else ("pass", None)
            got = (r["verdict"], r["witness"]["index"] if r.get("witness") else None)
            verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
            if got != expected:
                disagree.append((h.decode(), got, expected))
            if not verify_record(h, r, s):
                unverified += 1
        if code != 0 or len(new) != len(hosts) or disagree or unverified:
            problems.append(f"P3c set {s}: exit {code}, {len(disagree)} disagreements {disagree[:3]}, "
                            f"{unverified} witnesses fail")
        log(f"P3c realistic 23-vertex hosts, set {s}: {len(hosts)} hosts {verdicts}; matcher32 + Python TU search "
            f"agree on verdict and index: {len(hosts) - len(disagree)}/{len(hosts)}; witnesses re-verified: "
            f"{len(new) - unverified}/{len(new)}")
    return host_files


def lattice_hosts(rng: random.Random, count: int, n: int) -> list[bytes]:
    """Unit-distance graphs on n points of the triangular lattice Z[w] (a + b w is at unit distance
    from its six neighbours, and from nothing else in the lattice), so every one is free of the 398
    and the filter must say tu or pass; a random share of the edges is deleted so that TU gadgets
    lose their forced pairs. A tenth of them get one extra edge between two non-adjacent points."""
    radius = 5
    pts = [(a, b) for a in range(-radius, radius + 1) for b in range(-radius, radius + 1) if abs(a + b) <= radius]
    pts_set = set(pts)
    units = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
    hosts = []
    for index in range(count):
        chosen = [rng.choice(pts)]
        chosen_set = set(chosen)
        while len(chosen) < n:
            frontier = sorted({(p[0] + du, p[1] + dv) for p in chosen for du, dv in units
                               if (p[0] + du, p[1] + dv) in pts_set and (p[0] + du, p[1] + dv) not in chosen_set})
            q = rng.choice(frontier) if frontier and rng.random() < 0.9 else \
                rng.choice([p for p in pts if p not in chosen_set])
            chosen.append(q)
            chosen_set.add(q)
        rng.shuffle(chosen)
        edges = [(i, j) for j in range(n) for i in range(j)
                 if (chosen[j][0] - chosen[i][0], chosen[j][1] - chosen[i][1]) in units]
        keep = rng.choice((1.0, 0.95, 0.9, 0.85, 0.75))
        edges = [e for e in edges if rng.random() < keep]
        if index % 10 == 9:
            present = set(edges)
            non = [(i, j) for j in range(n) for i in range(j) if (i, j) not in present]
            edges.append(rng.choice(non))
        hosts.append(encode_g6(n, edges))
    return hosts


def part5() -> list[Path]:
    """Hosts of 23 and 24 vertices on which set 398 must say tu or pass (most of them), decided
    independently as in 3c: exercises the TU search and the pass verdict at the new sizes."""
    rng = random.Random(202609251)
    files = []
    for n in (23, 24):
        hosts = lattice_hosts(rng, 800, n)
        path = WORK / "p3" / f"lattice-{n}.g6"
        write_lines(path, hosts)
        files.append(path)
        for s, patterns in ((398, F398_G6), (74, F74_G6)):
            code, err = run_filter(UDFILTER, s, path, WORK / "p3" / f"lattice-{n}.{s}.jsonl")
            new = records(WORK / "p3" / f"lattice-{n}.{s}.jsonl")
            matched = run_matcher(patterns, path, WORK / "p3" / f"matcher-lattice-{n}-{s}")
            disagree, unverified, verdicts = [], 0, {}
            for h, r in zip(hosts, new):
                if h in matched["removed"]:
                    expected = ("forbidden", matched["removed"][h][0])
                else:
                    found = tu_search(h)
                    expected = ("tu", found[0]) if found else ("pass", None)
                got = (r["verdict"], r["witness"]["index"] if r.get("witness") else None)
                verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
                if got != expected:
                    disagree.append((h.decode(), got, expected))
                if not verify_record(h, r, s):
                    unverified += 1
            if code != 0 or len(new) != len(hosts) or disagree or unverified:
                problems.append(f"P5 {n} vertices set {s}: exit {code}, {len(disagree)} disagreements "
                                f"{disagree[:3]}, {unverified} witnesses fail")
            log(f"P5 lattice unit-distance hosts, {n} vertices, set {s}: {len(hosts)} hosts {verdicts}; matcher32 + "
                f"Python TU search agree on verdict and index: {len(hosts) - len(disagree)}/{len(hosts)}; "
                f"witnesses re-verified: {len(new) - unverified}/{len(new)}")
    return files


def part4(host_files: list[Path]) -> None:
    build = WORK / "asan"
    shutil.rmtree(build, ignore_errors=True)
    build.mkdir(parents=True)
    src = UD / "filter"
    for name in ("udfilter.c", "udfilter.h", "udfilter-cli.c"):
        shutil.copy2(src / name, build / name)
    binary = build / "udfilter-asan"
    subprocess.run(["nice", "-n", "15", "cc", "-std=c17", "-O1", "-g", "-fsanitize=address,undefined",
                    "-fno-sanitize-recover=all", "-Wall", "-Wextra", "-o", str(binary),
                    str(build / "udfilter.c"), str(build / "udfilter-cli.c")], check=True)
    total = 0
    for path in host_files:
        for s in (74, 398):
            out = build / f"{path.stem}.{s}.jsonl"
            code, err = run_filter(binary, s, path, out)
            same = out.read_bytes() == (WORK / "p3" / f"{path.stem}.{s}.jsonl").read_bytes()
            if code != 0 or err or not same:
                problems.append(f"P4 {path.name} set {s}: exit {code}, same {same}, stderr {err[:200]}")
            total += len(g6_lines(path))
    log(f"P4 ASAN + UBSan build on every Part-3 host file in both sets ({total} runs of a host): "
        f"{'clean and identical' if not any(p.startswith('P4') for p in problems) else 'FAILED'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--slices", type=Path, required=True)
    ap.add_argument("--parts", default="12354", help="which parts to run (4, the sanitizer build, reads every "
                                                        "host file of parts 3 and 5); 3 reuses part 1's host files")
    a = ap.parse_args()
    for path, want in ((a.baseline, BASE_SHA256), (ORIG, ORIG_SHA256)):
        if sha256(path) != want:
            print(f"{path} is not the expected build {want}", file=sys.stderr)
            return 2
    log(f"NEW udfilter {sha256(UDFILTER)}; BASE {BASE_SHA256[:8]}; ORIG {ORIG_SHA256[:8]}")
    WORK.mkdir(parents=True, exist_ok=True)
    write_lines(a.slices.parent / "all-22-61.g6",
                [x for s in range(48) for x in g6_lines(a.slices / f"s{s}of48" / "22-61.g6")])
    write_lines(a.slices.parent / "all-21-56.keep.g6",
                [x for s in range(48) for x in g6_lines(a.slices / f"s{s}of48" / "21-56.keep.g6")])
    if "1" in a.parts:
        paths = part1(a.baseline, a.slices)
    else:
        paths = {p.stem: p for p in (WORK / "p1").glob("*.g6")}
    if "2" in a.parts:
        part2()
    host_files = [WORK / "p3" / f"{name}.g6" for name in ("lifted-23", "lifted-24", "permuted-23", "realistic-23")]
    if "3" in a.parts:
        host_files = part3(a.baseline, paths, a.slices)
    if "5" in a.parts:
        host_files += part5()
    elif (WORK / "p3" / "lattice-23.g6").is_file():
        host_files += [WORK / "p3" / "lattice-23.g6", WORK / "p3" / "lattice-24.g6"]
    if "4" in a.parts:
        part4(host_files)
    for p in problems:
        log("PROBLEM:", p)
    log("FILTER-LIMIT", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
