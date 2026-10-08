#!/usr/bin/env python3
"""refine_check.py: the u23-refine judge (the ## u23-refine entry of coordination/cloud-workers/JOBS.md).

usage: python refine_check.py [--root DIR] [--fleet-root DIR] [--plan FILE] [--fetch] [--self-test]

A heavy (23,65) slice i of 1920, which in the full re-run only the memory-bounded verify-chain-lean.py could check, is
credited to the unchanged G5 checker when every piece of its refinement passes. The plan
(coordination/cloud-workers/u23-refine-plan.json) gives each worker's parent slice i and its pieces, the indices
i + 1920 j (j = 0..K-1) of count 1920 K. run-dag2.py puts a level-12 record in slice sha256(record)[:8] mod count, so
those pieces partition slice i's level-12 parents exactly, and (one canonical parent per graph) its tree above them.
Every requirement is re-derived from the files the workers pushed (--fetch extracts their branches into --root):
  1. the partition: the worker's pieces are exactly the plan's K indices of its count, each once, with the parent's
     residue (index mod 1920 is i);
  2. each piece's G5 check output passes by verify_sample.py's own rules (judge_output, record_scope), with the slice
     count set to the piece's: the pinned G5 checker (commit and sha256) and its record of this piece's run (slice
     [12, r, count], target, seed, pins); every inspected pruned cell's certificates replayed; no PROBLEM line; the
     digest of the level files it checked equal to the piece's result copy's; the first piece whole (CHAIN OK,
     COVERAGE exhaustive), every later piece from level 13 (CHAIN PARTIAL for that reason alone) with its prefix
     identical, file for file, to the first piece's; no memory-fallback (lean) output at all (u23-refine.sh turns the
     fallback off);
  3. each piece's G4 replay audited by target_check.py (the pinned audit and its scope rules, the count set to the
     piece's): no problem for the piece, none global (so every slice-mode prefix is covered by a passing full-mode
     replay: the first piece's);
  4. each piece's result copy against the fleet's copy of slice i: the same prefix (levels <= 12) and input hashes,
     the same software (the G5-closed run-dag2.py allowed, as in the full re-run; the interpreter excepted), the same
     options (run-summary header and run-config, the slice removed), completed through the target, its own G4 replay
     passed;
  5. the roots: each piece's level-12 slice files, from its evidence bundle, hash as its inventory says, and hold only
     records of the piece's residue; the G5 check recomputed each of them from the prefix's keep file (its check (h),
     which runs whatever --from-n); together they hold, cell by cell, as many records as slice i drew (the fleet
     copy's parent sources at level 13), and each piece's own parent sources say what its files hold;
  6. the counts: at every cell above level 12 the pieces' counts rows add up, key by key, to the fleet copy's row for
     slice i; at every level <= 12 each piece's row is the fleet copy's; each level file the copies ship at levels
     >= N-2 has as many records in the pieces together as in the fleet copy; the pieces' kept graphs at the target
     are, as a multiset, the fleet copy's.
A piece whose G5 check was killed for memory is reported as such (the slice is then not credited, and that piece is
refined further). The last line is REFINE-CHECK OK or REFINE-CHECK FAIL. --self-test shows every requirement can fail,
each on its own line.
"""
import argparse, contextlib, copy, gzip, hashlib, json, re, subprocess, sys, tarfile, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import aggregate_fleet as af   # noqa: E402  read_copy, choose, get: one notion of a result copy
import fleet_status as fs      # noqa: E402
import target_check as tc      # noqa: E402  the pinned G4 audit and scope rules
import verify_sample as vsm    # noqa: E402  the check-output rules of the full re-run

REPO = HERE.parents[3]
PLAN = REPO / "coordination/cloud-workers/u23-refine-plan.json"
ROOT = Path("<scratch>/scratchpad/refine-results")
FLEET_ROOT = vsm.FLEET_ROOT
SUB = "refine"
TOP_LEVEL = REPO / "research/unit-distance-23/results/u23/top-level"


@contextlib.contextmanager
def counted(n: int):
    """The shared tools with their slice count set to n (their module constants), restored after."""
    old = (tc.COUNT, vsm.COUNT, fs.C)
    tc.COUNT = vsm.COUNT = fs.C = n
    try:
        yield
    finally:
        tc.COUNT, vsm.COUNT, fs.C = old


def slice_of(code: str, count: int) -> int:
    """run-dag2.py's slice_of, restated."""
    return int.from_bytes(hashlib.sha256(code.encode("ascii")).digest()[:8], "big") % count


def fetch(root: Path, pattern: str = "h*") -> None:
    out = subprocess.run(["git", "-c", "gc.auto=0", "ls-remote", "origin", f"refs/heads/claude/answering-alexeev-u22-cloud-u23-{pattern}"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    for line in filter(None, (x.strip() for x in out)):
        _, ref = line.split()
        name = ref.split("cloud-u23-", 1)[1]
        local = f"refs/u23refine/{name}"
        subprocess.run(["git", "-c", "gc.auto=0", "fetch", "-q", "--no-write-fetch-head", "origin", f"+{ref}:{local}"], cwd=REPO,
                       check=True)
        dst = root / name
        dst.mkdir(parents=True, exist_ok=True)
        arch = subprocess.run(["git", "-c", "gc.auto=0", "archive", local, f"research/unit-distance-23/results/{SUB}"], cwd=REPO,
                              capture_output=True)
        if arch.returncode == 0 and arch.stdout:
            subprocess.run(["tar", "-x", "-C", str(dst)], input=arch.stdout, check=True)


def evidence(e: Path, run_name: str) -> dict:
    """A piece's evidence bundle (u23-refine.sh, refine_probe.py): its verdict line, memory record, and its level-12
    slice files with their inventory entries."""
    out = {"done": None, "memory": None, "roots": {}, "manifests": {}, "inventory": {}, "why": []}
    try:
        out["done"] = (e / "done.txt").read_text().strip()
    except OSError:
        out["why"].append("no done.txt in its evidence")
    try:
        out["memory"] = json.loads((e / "memory.json").read_text())
    except (OSError, ValueError):
        out["why"].append("no readable memory.json in its evidence")
    try:
        with gzip.open(e / "inventory.jsonl.gz", "rt") as f:
            out["inventory"] = {r["path"]: r for r in map(json.loads, f)}
    except (OSError, ValueError, KeyError):
        out["why"].append("no readable inventory in its evidence")
    try:
        with tarfile.open(e / "meta.tar.gz") as tar:
            for m in tar.getmembers():
                mm = re.fullmatch(rf"{re.escape(run_name)}/12-(\d+)\.slice-(\d+)-of-(\d+)(\.g6|\.manifest\.json)", m.name)
                if mm and m.isfile():
                    data = tar.extractfile(m).read()
                    key = (int(mm.group(1)), int(mm.group(2)), int(mm.group(3)))
                    if mm.group(4) == ".g6":
                        out["roots"][key] = data
                    else:
                        out["manifests"][key] = json.loads(data)
    except (OSError, ValueError, tarfile.TarError) as x:
        out["why"].append(f"no readable metadata bundle in its evidence ({type(x).__name__})")
    return out


def collect(root: Path, plan: dict, fleet_root: Path) -> dict:
    count, base, tn, tm = plan["count"], plan["base_count"], plan["target"][0], plan["target"][1]
    kind = f"{tn}-{tm}-L{vsm.LEVEL}-tri-pf74"
    data = {"outputs": {}, "copies": {}, "evid": {}, "summary": {}, "fleet": {}}
    for d in sorted(x for x in root.glob("*") if x.is_dir()):
        tag = d.name.split("-")[0]
        res = d / "research/unit-distance-23/results" / SUB
        for p in sorted((res / "verify").glob(f"s*of{count}-*.txt")):
            mm = re.fullmatch(rf"s(\d+)of{count}-{tag}(\.lean)?\.txt", p.name)
            if mm:
                o = vsm.parse_output(p.read_text())
                o["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                o["file_kind"] = "lean" if mm.group(2) else "g5"
                data["outputs"].setdefault((tag, int(mm.group(1))), []).append(o)
        with counted(count):
            for c in sorted((res / kind).glob(f"s*of{count}")):
                try:
                    cp = af.read_copy(c, root)
                except af.Incomplete as x:
                    data["copies"].setdefault((tag, int(c.name[1:].split("of")[0])), []).append({"incomplete": str(x)})
                    continue
                data["copies"].setdefault((tag, cp["slice"]), []).append(cp)
        for e in sorted((res / "evidence").glob(f"s*of{count}")):
            r = int(e.name[1:].split("of")[0])
            data["evid"].setdefault((tag, r), []).append(evidence(e, f"dag-{kind}-s{r}of{count}"))
        if (res / "evidence" / "SUMMARY.txt").is_file():
            data["summary"][tag] = (res / "evidence" / "SUMMARY.txt").read_text()
    with counted(base):   # the fleet's copies of the parent slices, chosen as the full re-run's judge chooses
        for i in sorted(set(plan["parents"].values())):
            cands = []
            for d in sorted(fleet_root.glob(f"*/research/unit-distance-23/results/u23/{kind}/s{i}of{base}")):
                try:
                    c = af.read_copy(d, fleet_root)
                except af.Incomplete:
                    continue
                if c["ctn"] == c["target"][0]:
                    cands.append(c)
            if cands:
                data["fleet"][i] = af.choose(cands)
    return data


def replay_audit(root: Path, plan: dict) -> dict:
    """The pieces' G4 replays judged by target_check.py's pinned audit and scope rules, with the count set to theirs:
    {"per_slice": {r: [why]}, "global": [why], "shards": {r: {cell: n}}}."""
    count, (tn, tm) = plan["count"], plan["target"]
    pat = f"*/research/unit-distance-23/results/{SUB}/{tn}-{tm}-L{vsm.LEVEL}-tri-pf74/s*of{count}"
    with counted(count):
        dirs = sorted(root.glob(pat))
        aud = tc.audit(dirs, tn, tm)
        per = {i: list(ws) for i, ws in aud["per_slice"].items()}
        per_copy, _, glob, shards = tc.scope_problems(root, SUB, tn, tm,
                                                      failed_slices={i for i, ws in aud["per_slice"].items() if ws})
    for i, label, ws in per_copy:
        per.setdefault(i, []).extend(f"its replay ({label}): {w}" for w in ws)
    return {"per_slice": per, "global": aud["global"] + glob, "shards": shards}


def parent_draws(c: dict) -> tuple[dict, list]:
    """How many records a copy's slice drew from each level-12 cell: its run-summary's parent sources at level 13
    ({m: records}), and why they cannot be read as one number per cell."""
    rs = json.loads((c["dir"] / "run-summary.json").read_text())
    draws, why = {}, []
    for lv in rs.get("levels") or []:
        if lv.get("n") != vsm.LEVEL + 1:
            continue
        for s in lv.get("parent_sources") or []:
            lvl = s.get("level") or [None, None]
            if lvl[0] != vsm.LEVEL:
                continue
            if s.get("kind") != "keep+slice":
                why.append(f"a level-13 parent source of ({lvl[0]},{lvl[1]}) is {s.get('kind')}, not keep+slice")
            prev = draws.setdefault(lvl[1], s.get("records"))
            if prev != s.get("records"):
                why.append(f"its level-13 parent sources disagree on ({lvl[0]},{lvl[1]}): {prev} and {s.get('records')}")
    return draws, why


def add_rows(rows: list) -> dict | None:
    """Rows (aggregate_fleet.row) added key by key, as {"children": n, key: total, ...}; a cell a piece does not reach
    is a row of no children and no counts, which adds nothing. None when a row is missing altogether."""
    if any(r is None for r in rows):
        return None
    keys = sorted({k for r in rows if r[1] for k in r[1]})
    return {"children": sum(r[0] or 0 for r in rows), **{k: sum(af.get(r, k) for r in rows) for k in keys}}


def rows_equal(total: dict | None, frow) -> bool:
    """The pieces' sum equals the fleet copy's row: the same children, and every count key the same, a key one side
    lacks read as 0 (aggregate_fleet.get's rule)."""
    if total is None or frow is None:
        return total is None and frow is None
    keys = set(total) - {"children"} | set(frow[1] or ())
    return total["children"] == (frow[0] or 0) and all(total.get(k, 0) == af.get(frow, k) for k in keys)


def killed_ok(o: dict | None, tag: str, r: int, count: int) -> list:
    """A memory kill stands as a piece's outcome only when it is the pinned G5 checker's own check of this piece that
    died (u23-verify.sh's rule: exit 137, or a MemoryError, with no result printed), under the wrapper's FAIL."""
    h = (o or {}).get("head") or {}
    why = []
    if not h.get("id") or h["id"][0] != tag or int(h["id"][1]) != r or int(h["id"][2]) != count:
        why.append(f"its killed check's header names another check: {h.get('id')}")
    if h.get("checker") != (vsm.G5_COMMIT, vsm.G5_SHA256) or (h.get("cname") or (None,))[0] != "g5":
        why.append(f"its killed check was not the pinned G5 checker's: {h.get('checker')}")
    if h.get("verdict") != ("FAIL",):
        why.append(f"its killed check's wrapper verdict is {h.get('verdict')}, not FAIL")
    return why


def evaluate(plan: dict, data: dict, replay: dict) -> tuple:
    problems, lines = [], []
    count, k, parents, BASE = plan["count"], plan["k"], plan["parents"], plan["base_count"]
    tn, tm = plan["target"]
    if count != BASE * k:
        problems.append(f"the plan's count {count} is not {BASE} x its K {k}")
    problems += [f"the pieces' G4 audit: {w}" for w in replay.get("global") or []]
    slices = {}
    # pass 1: every piece on its own
    for tag, pieces in sorted(plan["tasks"].items()):
        i = parents.get(tag)
        why_slice = []
        want = [i + BASE * j for j in range(k)] if i is not None else None
        if want is None or pieces != want:
            why_slice.append(f"its pieces are not the {k} indices {i} + {BASE} j of {count}, each once: {pieces[:4]}...")
        f = data["fleet"].get(i)
        if f is None:
            why_slice.append(f"no complete fleet copy of s{i}of{BASE} to compare with")
        first = pieces[0] if pieces else None
        results = []
        for r in pieces:
            why = []
            outs = data["outputs"].get((tag, r)) or [None]
            leans = [o for o in outs if o is not None and o.get("file_kind") == "lean"]
            g5s = [o for o in outs if o is None or o.get("file_kind") == "g5"] or [None]
            if leans:
                why.append("a memory-fallback (lean) output exists, but u23-refine.sh runs with the fallback off")
            # a piece whose one G5 check died of memory has no verdict to judge: it is reported, never credited
            killed = len(g5s) == 1 and g5s[0] is not None and g5s[0]["killed"]
            copies = data["copies"].get((tag, r)) or [None]
            with counted(count):
                if killed:
                    why += killed_ok(g5s[0], tag, r, count)
                else:
                    why += [f"check output {n + 1}: {w}" if len(g5s) > 1 else w
                            for n, o in enumerate(g5s) for w in vsm.judge_output(o, tag, r, first, {})]
                    shards = (replay.get("shards") or {}).get(r)
                    for o in g5s:
                        for c in copies:
                            if c is not None and "incomplete" not in c:
                                why += vsm.record_scope(o, c, r == first, shards)
            why += [f"its G4 replay: {w}" for w in (replay.get("per_slice") or {}).get(r, [])]
            for c in copies:
                if c is None:
                    why.append("no result copy")
                    continue
                if "incomplete" in c:
                    why.append(f"its result copy is incomplete: {c['incomplete']}")
                    continue
                for o in g5s:
                    if not killed and o and o["head"]["digest"] and tuple(o["head"]["digest"]) != vsm.copy_digest(c):
                        why.append(f"the digest of the files checked is not its copy's ({vsm.copy_digest(c)[0]} files)")
                if f is not None:
                    fc = dict(f, software={(s, kk, vsm.FLEET_RUNDAG if kk == "run-dag2.py" and h == vsm.G5_RUNDAG else h)
                                           for s, kk, h in f["software"]})
                    cc = dict(c, software={(s, kk, vsm.FLEET_RUNDAG if kk == "run-dag2.py" and h == vsm.G5_RUNDAG else h)
                                           for s, kk, h in c["software"]})
                    rp = c.get("replay") or {}
                    if not (rp.get("verdict") == "PASS" and rp.get("runbook_result") == "PASS"
                            and rp.get("stages_ok") is True
                            and (rp.get("red_all") is True if rp.get("mode") == "full" else rp.get("red_all") in (True, None))):
                        why.append(f"its own G4 replay did not pass: {rp.get('verdict')}, {rp.get('runbook_result')}")
                    for key in ("prefix", "inputs", "options"):
                        if c[key] != f[key]:
                            why.append(f"its {key} differ from the fleet's copy of s{i} ({f['worker']})")
                    if {x for x in cc["software"] if x[1] != "python"} != {x for x in fc["software"] if x[1] != "python"}:
                        why.append(f"its software hashes differ from the fleet's copy of s{i}")
                    if c["ctn"] != f["ctn"] or c["slice_field"] != [vsm.LEVEL, r, count]:
                        why.append(f"completed through {c['ctn']} (the fleet's {f['ctn']}), slice {c['slice_field']}")
            ev = data["evid"].get((tag, r)) or [None]
            if ev[0] is None or len(ev) != 1:
                why.append(f"{len(ev) if ev[0] else 0} evidence bundles, not one")
            else:
                e = ev[0]
                why += e["why"]
                run = f"dag-{tn}-{tm}-L{vsm.LEVEL}-tri-pf74-s{r}of{count}"
                for (m, rr, cnt), blob in sorted(e["roots"].items()):
                    inv = e["inventory"].get(f"12-{m}.slice-{rr}-of-{cnt}.g6")
                    if (rr, cnt) != (r, count):
                        why.append(f"its bundle holds another piece's slice file 12-{m}.slice-{rr}-of-{cnt}.g6")
                    elif inv is None or inv.get("sha256") != hashlib.sha256(blob).hexdigest():
                        why.append(f"12-{m}.slice-{r}-of-{count}.g6 is not the file its inventory hashes")
                    bad = [x for x in blob.decode("ascii", "replace").splitlines() if x and slice_of(x, count) != r]
                    if bad:
                        why.append(f"12-{m}.slice-{r}-of-{count}.g6 holds {len(bad)} record(s) of another piece")
                if not e["roots"]:
                    why.append(f"its bundle holds no level-12 slice files ({run})")
            results.append({"r": r, "why": why, "killed": killed, "copies": copies, "ev": ev[0], "o": g5s[0],
                            "whole": r == first and not killed})
        slices[tag] = (i, f, first, why_slice, results)
    # a prefix (levels <= 12) is sound only as the prefix of a piece that passed its whole check (any worker's):
    # G5 round 10's rule for the full re-run, here for the pieces (a worker whose own first piece died of memory
    # compared its prefix byte for byte with that piece's, and the identical prefix passed whole elsewhere)
    wholes = {c["prefix"] for (_, _, _, _, rs) in slices.values() for x in rs if x["whole"] and not x["why"]
              for c in x["copies"] if c and "incomplete" not in c}
    for (_, _, _, _, rs) in slices.values():
        for x in rs:
            if any(c and "incomplete" not in c and c["prefix"] not in wholes for c in x["copies"]):
                x["why"].append("its prefix (levels <= 12, by its copy's hashes) is not the prefix of any piece that "
                                "passed a whole check")
    # pass 2: each slice as the union of its pieces
    credited, partial = [], []
    for tag, (i, f, first, why_slice, results) in sorted(slices.items()):
        complete = results and all(x["copies"][0] is not None and "incomplete" not in x["copies"][0]
                                   and x["ev"] is not None for x in results)
        if f is not None and complete:
            # 5. the roots together: as many per level-12 cell as slice i drew; each piece's parent sources its files
            fdraw, fwhy = parent_draws(f)
            why_slice += [f"the fleet copy: {w}" for w in fwhy]
            tot = {}
            for x in results:
                pdraw, pwhy = parent_draws(x["copies"][0])
                held = {m: len([y for y in blob.decode("ascii").splitlines() if y])
                        for (m, _, _), blob in x["ev"]["roots"].items()}
                if pwhy or {m: v for m, v in pdraw.items() if v} != {m: v for m, v in held.items() if v}:
                    x["why"].append(f"its parent sources ({pdraw}) are not what its slice files hold ({held})")
                for m, v in held.items():
                    tot[m] = tot.get(m, 0) + v
            if {m: v for m, v in tot.items() if v} != {m: v for m, v in fdraw.items() if v}:
                why_slice.append(f"the pieces' roots ({dict(sorted(tot.items()))}) are not what s{i} drew "
                                 f"({dict(sorted(fdraw.items()))})")
            # 6. the counts, every piece's (a killed piece's run finished; only its check died)
            cells = set(f["counts"])
            for x in results:
                cells |= set(x["copies"][0]["counts"])
            for cell in sorted(cells):
                rows = [x["copies"][0]["counts"].get(cell) for x in results]
                if cell[0] <= vsm.LEVEL:
                    if any(rw != f["counts"].get(cell) for rw in rows):
                        why_slice.append(f"({cell[0]},{cell[1]}): a piece's row is not the fleet copy's")
                elif not rows_equal(add_rows(rows), f["counts"].get(cell)):
                    why_slice.append(f"({cell[0]},{cell[1]}): the pieces add up to {add_rows(rows)}, the fleet copy "
                                     f"has {af.cell_json(f['counts'].get(cell))}")
            for name in sorted(set(f["upper"]) | {n for x in results for n in x["copies"][0]["upper"]}):
                recs = [x["copies"][0]["upper"].get(name, (None, None))[1] for x in results]
                if None in recs or sum(recs) != f["upper"].get(name, (None, None))[1]:
                    why_slice.append(f"{name}: the pieces hold {recs} records, the fleet copy "
                                     f"{f['upper'].get(name, (None, None))[1]}")
            kept = sorted(y for x in results for y in (x["copies"][0]["keep_lines"] or ()))
            if kept != sorted(f["keep_lines"] or ()):
                why_slice.append(f"the pieces' kept graphs at the target are not the fleet copy's ({len(kept)}, "
                                 f"{len(f['keep_lines'] or ())})")
            # a graph kept at the target is refuted by its top-level record (top_level_check.py replays the record's
            # certificate with both checkers); here the pieces' kept graphs must be that record's graphs
            if kept:
                rec = TOP_LEVEL / f"s{i}of{BASE}" / f"{tn}-{tm}.g6"
                have = sorted(x.strip() for x in rec.read_text().splitlines() if x.strip()) if rec.is_file() else None
                if have != kept:
                    why_slice.append(f"the pieces keep {len(kept)} graph(s) at the target, and the top-level record "
                                     f"{rec.relative_to(REPO)} holds {have if have is None else len(have)} other(s)")
        elif f is not None:
            why_slice.append("not every piece has a complete result copy and one evidence bundle, so the union is not "
                             "checked")
        n_killed = sum(x["killed"] for x in results)
        verified = sum(1 for x in results if not x["why"] and not x["killed"])
        for x in results:
            peak = ((x["ev"] or {}).get("memory") or {}).get("checker_peak_kb")
            state = "NOT verified" if x["why"] else "killed for memory (no verdict)" if x["killed"] else \
                ("whole, CHAIN OK" if x["r"] == first else f"from level {vsm.FROM}, CHAIN PARTIAL, prefix identical")
            lines.append(f"s{x['r']}of{count} {tag} (piece of s{i}of{BASE}): {state}; G5 checker peak "
                         f"{peak if peak is not None else '?'} kB")
            problems += [f"s{x['r']}of{count} ({tag}): {w}" for w in x["why"]]
        problems += [f"s{i}of{BASE} ({tag}): {w}" for w in why_slice]
        clean = not why_slice and all(not x["why"] for x in results) and not (replay.get("global") or [])
        if clean and not n_killed:
            credited.append(i)
            state = "CREDITED to the G5 checker"
        elif clean:
            partial.append(i)
            state = "PARTIAL"
        else:
            state = "not credited"
        killed_names = ", ".join(f"s{x['r']}of{count}" for x in results if x["killed"])
        lines.append(f"s{i}of{BASE} ({tag}): {state}: {verified} of {len(results)} pieces verified by the G5 checker"
                     + (f"; {n_killed} killed for memory ({killed_names})" if n_killed else "")
                     + ("; roots, counts and kept graphs reconciled with the fleet's copy" if clean else ""))
    return problems, lines, {"parents": sorted(parents.values()), "credited": sorted(credited),
                             "partial": sorted(partial), "count": count}


def report(problems: list, lines: list, s: dict) -> int:
    for x in lines:
        print(x)
    for p in problems:
        print(f"PROBLEM: {p}")
    if problems or sorted(s["credited"] + s["partial"]) != s["parents"]:
        verdict, code = "FAIL", 1
    elif s["partial"]:
        verdict, code = "PARTIAL", 3
    else:
        verdict, code = "OK", 0
    print(f"REFINE-CHECK {verdict}: {len(s['credited'])} of {len(s['parents'])} heavy slice(s) credited to the G5 "
          f"checker by their pieces of {s['count']} ({', '.join(f's{i}' for i in s['credited']) or 'none'}); "
          f"{len(s['partial'])} partly ({', '.join(f's{i}' for i in s['partial']) or 'none'}: a piece killed for "
          f"memory, every other rule met); {len(problems)} problem(s)")
    return code


def self_test(plan: dict, data: dict, replay: dict) -> int:
    """Each requirement must fail on its own in-memory mutation, on its own line."""
    base_p, _, base_s = evaluate(plan, data, replay)
    if base_p:
        print(f"SELF-TEST: the unchanged data has {len(base_p)} problem(s); the controls need a passing base")
        return 1
    tag = sorted(plan["tasks"])[0]
    pieces = plan["tasks"][tag]
    r0, r1 = pieces[0], pieces[1]
    i = plan["parents"][tag]
    results = []

    def expect(name, P, D, R, must):
        """Caught when the mutation adds a problem that must accepts (the base has none), so that the slice falls
        out of both the credited and the partly credited lists."""
        p, _, s = evaluate(P, D, R)
        hit = [x for x in p if must(x)]
        ok = bool(hit) and (s["credited"] + s["partial"]) != (base_s["credited"] + base_s["partial"])
        results.append(ok)
        print(f"{'ok  ' if ok else 'MISS'} self-test, {name}: {(hit or p or ['(no problem)'])[0][:200]}")

    def mut(fn):
        D = copy.copy(data)
        D = {k2: (copy.deepcopy(v) if k2 != "fleet" else dict(v)) for k2, v in data.items()}
        fn(D)
        return D

    P = copy.deepcopy(plan)
    P["tasks"][tag] = pieces[:-1]
    expect("a piece left out of the plan", P, data, replay, lambda x: "are not the" in x)
    P = copy.deepcopy(plan)
    P["tasks"][tag] = pieces[:-1] + [pieces[0]]
    expect("a piece twice, one left out", P, data, replay, lambda x: "are not the" in x)
    expect("a piece's check output removed", plan, mut(lambda D: D["outputs"].pop((tag, r1))), replay,
           lambda x: f"s{r1}of" in x and "no check output" in x)

    def chain(D):
        o = D["outputs"][(tag, r1)][0]
        o["chain"] = "CHAIN OK"
    expect("a later piece's CHAIN line changed", plan, mut(chain), replay, lambda x: f"s{r1}of" in x and "did not pass" in x)

    def lean(D):
        o = copy.deepcopy(D["outputs"][(tag, r1)][0])
        o["file_kind"] = "lean"
        D["outputs"][(tag, r1)].append(o)
    expect("a lean output beside a piece's", plan, mut(lean), replay, lambda x: "memory-fallback (lean)" in x)

    def prefix(D):
        h = D["outputs"][(tag, r1)][0]["head"]
        h["prefix"] = (h["prefix"][0], h["prefix"][1], "differs: 12-20.g6")
    expect("a later piece's prefix not identical", plan, mut(prefix), replay, lambda x: "prefix is not shown identical" in x)
    expect("a piece's result copy removed", plan, mut(lambda D: D["copies"].pop((tag, r1))), replay,
           lambda x: f"s{r1}of" in x and "no result copy" in x)

    def counts(D):
        c = D["copies"][(tag, r1)][0]
        cell = max(x for x in c["counts"] if x[0] > vsm.LEVEL and (c["counts"][x][0] or 0) > 0)
        rw = c["counts"][cell]
        c["counts"] = dict(c["counts"])
        c["counts"][cell] = af.row((rw[0] or 0) + 1, dict(zip(rw[1], rw[2])) if rw[1] else None)
    expect("a piece's counts row changed (its checked files unchanged)", plan, mut(counts), replay,
           lambda x: "the pieces add up to" in x)

    def fleet_counts(D):
        f = copy.deepcopy(D["fleet"][i])
        cell = max(x for x in f["counts"] if x[0] > vsm.LEVEL and (f["counts"][x][0] or 0) > 0)
        rw = f["counts"][cell]
        f["counts"][cell] = af.row((rw[0] or 0) - 1, dict(zip(rw[1], rw[2])) if rw[1] else None)
        D["fleet"][i] = f
    expect("the fleet copy's counts row changed", plan, mut(fleet_counts), replay, lambda x: "the pieces add up to" in x)

    def prefix_hash(D):
        c = D["copies"][(tag, r1)][0]
        c["prefix"] = tuple((n, "0" * 64) if k2 == 0 else (n, h) for k2, (n, h) in enumerate(c["prefix"]))
    expect("a piece's prefix hash changed", plan, mut(prefix_hash), replay, lambda x: "its prefix differ" in x)

    def root_other(D):
        e = D["evid"][(tag, r1)][0]
        m, rr, cnt = next(iter(e["roots"]))
        other = next(y for y in (f"x{n}" for n in range(100000)) if slice_of(y, cnt) != rr)
        e["roots"][(m, rr, cnt)] = e["roots"][(m, rr, cnt)] + (other + "\n").encode()
    expect("a root of another piece in a piece's slice file", plan, mut(root_other), replay,
           lambda x: "record(s) of another piece" in x)

    def root_drop(D):
        e = D["evid"][(tag, r1)][0]
        key = max(e["roots"], key=lambda kk: len(e["roots"][kk]))
        e["roots"][key] = b"".join(x + b"\n" for x in e["roots"][key].splitlines()[1:])
        e["inventory"][f"12-{key[0]}.slice-{key[1]}-of-{key[2]}.g6"]["sha256"] = hashlib.sha256(e["roots"][key]).hexdigest()
    expect("a root dropped from a piece's slice file (inventory rehashed)", plan, mut(root_drop), replay,
           lambda x: "are not what its slice files hold" in x)
    expect("a piece's evidence removed", plan, mut(lambda D: D["evid"].pop((tag, r1))), replay,
           lambda x: "evidence bundles, not one" in x)
    expect("no fleet copy of the parent", plan, mut(lambda D: D["fleet"].pop(i)), replay,
           lambda x: "no complete fleet copy" in x)
    R = copy.deepcopy(replay)
    R.setdefault("per_slice", {}).setdefault(r1, []).append("audit: planted")
    expect("a piece's G4 audit problem", plan, data, R, lambda x: "its G4 replay: audit: planted" in x)
    R = copy.deepcopy(replay)
    R["global"] = list(R.get("global") or []) + ["planted"]
    expect("a global G4 audit problem", plan, data, R, lambda x: "the pieces' G4 audit: planted" in x)
    # a memory kill must be the pinned G5 checker's own check of this piece
    kt = next(((tg, x) for (tg, x), outs in sorted(data["outputs"].items()) if outs and outs[0] and outs[0]["killed"]),
              None)
    if kt:
        def other_checker(D):
            h = D["outputs"][kt][0]["head"]
            h["checker"] = (h["checker"][0], "0" * 64) if h.get("checker") else ("0" * 40, "0" * 64)
        expect(f"s{kt[1]}'s memory kill by a checker other than the pinned G5 one", plan, mut(other_checker), replay,
               lambda x: "was not the pinned G5 checker's" in x)
    else:
        results.append(False)
        print("MISS self-test, no piece was killed for memory, so the killed-check rule was not exercised")
    # the pieces' kept graphs at the target are the top-level record's
    kg = next(((tg, x) for (tg, x), cs in sorted(data["copies"].items()) if cs and cs[0] and "incomplete" not in cs[0]
               and cs[0]["keep_lines"]), None)
    if kg:
        def other_kept(D):
            c = D["copies"][kg][0]
            c["keep_lines"] = tuple(c["keep_lines"][:-1]) + ("V?????????????????????",)
            f = dict(D["fleet"][plan["parents"][kg[0]]])
            f["keep_lines"] = c["keep_lines"]
            D["fleet"][plan["parents"][kg[0]]] = f
        expect(f"s{kg[1]}'s kept graph at the target replaced, in its copy and the fleet's alike", plan, mut(other_kept),
               replay, lambda x: "the top-level record" in x)
    else:
        results.append(False)
        print("MISS self-test, no piece keeps a graph at the target, so the top-level binding was not exercised")
    # every prefix is the prefix of a piece that passed a whole check
    def lone_prefix(D):
        c = D["copies"][(tag, r1)][0]
        c["prefix"] = tuple((n, "f" * 64) if k2 == 0 else (n, h) for k2, (n, h) in enumerate(c["prefix"]))
    expect("a piece's prefix no whole check covered", plan, mut(lone_prefix), replay,
           lambda x: "not the prefix of any piece that passed a whole check" in x)
    n = sum(results)
    print(f"SELF-TEST {'passed' if n == len(results) else 'FAILED'}: {n} of {len(results)} controls caught")
    return 0 if n == len(results) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--fleet-root", type=Path, default=FLEET_ROOT)
    ap.add_argument("--plan", type=Path, default=PLAN)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    plan.setdefault("target", [23, 65])
    if a.fetch:
        a.root.mkdir(parents=True, exist_ok=True)
        fetch(a.root)
    data = collect(a.root, plan, a.fleet_root)
    replay = replay_audit(a.root, plan)
    code = self_test(plan, data, replay) if a.self_test else 0
    return report(*evaluate(plan, data, replay)) or code


if __name__ == "__main__":
    sys.exit(main())
