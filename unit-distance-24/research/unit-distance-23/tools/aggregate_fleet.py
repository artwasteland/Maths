#!/usr/bin/env python3
"""Aggregate the u(23) fleet's pushed slice results into one record, read-only. Gate G6 wants the write-up generated
from checker and manifest output only, so every number this prints is read from, or summed over, the workers' files.

usage: python aggregate_fleet.py [--root DIR] [--out FILE] [--self-check [--perturb SLICE[:MODE]]]
                                 [--no-top-level-check]

The u(22) fleet's research/unit-distance-22/results/u22/aggregate-slices.py (coverage, level totals, duplicated slices
compared cell by cell) and finalize-result.py (the write-up filled from a record) did this job before. Here the input is
the extraction fleet_status.py --fetch makes, default --root below: every copy of every slice,
<root>/<worker>/research/unit-distance-23/results/u23/<fleet_status.KIND>/s<i>of<C>/ with run-summary.json,
counts.json, hashes.json, run-config.json, replay/summary.json, replay/fingerprint.json and the top-level manifests.
Re-fired workers and reruns of slices with resumed cells make several copies of a slice. Nothing is written under the
root. A background collector rewrites it, so a copy with a required file missing or unparseable is skipped and counted.

Reported as JSON (--out) and as a markdown summary on stdout:
  1. coverage: the slices with a complete copy (completed_through_n = the target's n), the missing ones, the ones
     whose every copy has resumed cells (they need a fresh rerun), the ones with several copies and whether the
     copies agree (counts.json rows, and the hashes of the slice's shipped level files);
  2. the tree above the slice level, one copy per slice (without resumed cells if one exists, then a PASS/EMPTY replay,
     then by worker directory name): per cell (n, m) the children, kept, pruned, and pruned by kind. The kinds are the
     prune counts' own keys that name a prune verdict (tu, refuted, forbidden, <rule>_tu, <rule>_refuted), whichever
     are present; the other keys are summed as they are. Given per cell, per level n, and for the target cell;
  3. the target cell: children, kept, the slices that kept anything and their graphs, the records under
     results/u23/top-level, and top_level_check.py's verdict (run unless --no-top-level-check; it decides the kept
     graphs, this tool only reports);
  4. G4: replay verdicts by fleet_status.py's rule, the summed replay counts, the slices not PASS/EMPTY;
  5. cost: the slices' own step timings by fleet_status.py's rule (cells above the slice level, none resumed), summed
     over the slices whose chosen copy has no resumed cell; median, 90th percentile (nearest rank), max, heaviest 5;
  6. provenance: the prefix (levels <= slice level) in every copy's hashes.json, the software and data hashes in every
     manifest and replay summary, the run options, and the worker directories.
Exit 1 on a problem (copies that disagree, a misfiled copy, chosen copies with different cells or a cell without prune
counts, prefix, software or run-option hashes that differ, a replay not PASS/EMPTY, top_level_check.py not OK, a failed
self-check), else 0. Skipped, unfinished and missing slices are status, not problems ("final" in the JSON is true only
when all C slices are complete, none needs a rerun and there is no problem).

--self-check recomputes the record's identities, each by a second path or from a second source, and fails loudly:
complete + missing = C; kept + pruned = children - reach-dropped and pruned = the sum of its kinds in every cell;
counts.json = run-summary.json; the record counts of the shipped level files (hashes.json, the target's keep file, the
prune manifests' counts and verified_counts) = counts.json; the totals re-summed slice by slice; duplicated copies
identical; fleet_status.py's slice_record and its selection over the same directories (slices done, the target cell's
kept total, and per chosen copy the target cell, timing, resumed cells and replay verdict).
--perturb SLICE[:MODE] (needs --self-check, refuses --out) first changes that slice's chosen copy's counts IN MEMORY
(no file is touched), to show the self-check can fail: phantom (default) one more graph kept at the target cell,
carried consistently through every count; kept: kept + 1 at the target cell alone; move: one udfilter TU prune booked
to the rule (<rule>_tu, else refuted) instead, in the first cell above the slice level that has one.
"""
import argparse, collections, hashlib, json, math, re, statistics, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode = True   # importing fleet_status must not write a __pycache__ into the checkout
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import fleet_status as fs   # noqa: E402  the plan (fs.W workers, fs.C slices, fs.KIND) and the rules checked against

ROOT = Path("<scratch>/scratchpad/fleet/results")
RECORDS = fs.REPO / "research/unit-distance-23/results/u23/top-level"   # top_level_check.py's default --records
VERDICT_KEY = re.compile(r"tu|refuted|forbidden|[a-z0-9]+_(tu|refuted)")   # prune count keys naming a prune verdict
LEVEL = re.compile(r"(\d+)-(\d+)\.")                  # a level file name: <n>-<m>.<suffix>
LEVELISH = re.compile(r"\d+-\d+[-.]")                 # level, shard and parent files (they differ per slice)
FILE_KEY = {".g6": "children", ".reach.g6": "input", ".keep.g6": "kept", ".UNKNOWN.g6": "unknown"}
OK_REPLAY = ("PASS", "EMPTY")
REPLAY_SUMS = ("sampled_parents", "processed_parents", "production_children_compared", "mismatching_parents",
               "stages_checked")
_interned: dict = {}
OPTIONS: dict = {}   # run-options digest -> the options (run-summary header and run-config.json, slice removed)


def intern(x):
    return _interned.setdefault(x, x)


class Incomplete(Exception):
    """A copy the collector may be rewriting (a required file missing or unparseable): skipped and counted."""


def load(path: Path):
    try:
        return json.loads(path.read_bytes())
    except FileNotFoundError:
        raise Incomplete(f"{path.relative_to(path.parents[1])} missing") from None
    except (OSError, ValueError) as e:
        raise Incomplete(f"{path.relative_to(path.parents[1])} unreadable ({type(e).__name__})") from None


def row(children, counts):
    """A cell as stored: (children, the prune counts' keys in file order, their values), None, None without counts."""
    if not isinstance(counts, dict):
        return intern((children, None, None))
    return intern((children, intern(tuple(counts)), intern(tuple(counts.values()))))


def get(r, key):
    """A count of a stored cell: 'children', or a prune count key (0 when absent)."""
    if key == "children":
        return r[0] or 0
    return r[2][r[1].index(key)] if r[1] and key in r[1] else 0


def rows_digest(rows: dict) -> str:
    canon = sorted((cell, r[0], tuple(sorted(zip(r[1], r[2]))) if r[1] else None) for cell, r in rows.items())
    return hashlib.sha256(repr(canon).encode()).hexdigest()


def replay_verdict(failed: bool, s: dict | None) -> str:
    """fleet_status.py's rule (slice_record), restated; the self-check compares the two on every chosen copy."""
    if failed:
        return "FAILED"
    if s is None:
        return "missing"
    if s.get("mismatching_parents", 0) or 0:
        return "MISMATCH"
    if s.get("unreplayable_cells") or []:
        return "UNREPLAYABLE"
    return "EMPTY" if (s.get("processed_parents", 0) or 0) == 0 else "PASS"


def read_copy(d: Path, root: Path) -> dict:
    named = re.fullmatch(rf"s(\d+)of{fs.C}", d.name)
    if not named:
        raise Incomplete(f"directory name is not s<i>of{fs.C}")
    rs, rows, hashes = load(d / "run-summary.json"), load(d / "counts.json"), load(d / "hashes.json")
    config, fp = load(d / "run-config.json"), load(d / "replay" / "fingerprint.json")
    failed = (d / "replay" / "FAILED").exists()
    rsum = load(d / "replay" / "summary.json") if not failed or (d / "replay" / "summary.json").exists() else None
    try:
        sl, target = list(rs["slice"]), tuple(rs["target"])
        L, (tn, tm) = sl[0], target
        counts = {(n, m): row(ch, pc) for n, m, ch, pc in rows}
        levels = list(rs["levels"])
    except (KeyError, TypeError, ValueError) as e:
        raise Incomplete(f"unexpected shape ({type(e).__name__}: {e})") from None
    srows, reach_dropped, partial = {}, {}, []
    known, resumed = 0.0, 0
    for lv in levels:
        n, m = lv.get("n"), lv.get("m")
        p, r, v = lv.get("prune") or {}, lv.get("reach") or {}, lv.get("verify") or {}
        srows[(n, m)] = row(lv.get("children"), p.get("counts"))
        if (n or 0) <= L:
            continue
        if r.get("kept") is not None and (lv.get("children") or 0) != r["kept"]:
            reach_dropped[(n, m)] = (lv.get("children") or 0) - r["kept"]
        if lv.get("resumed") or p.get("resumed"):   # fleet_status.py: a resumed cell's time is unknown, not zero
            resumed += 1
            continue
        walls = [x.get("wall_seconds", 0) or 0 for x in lv.get("shards") or []]
        known += max(max(walls, default=0), sum(walls) / 4) + (p.get("step_wall_seconds") or 0) \
            + (v.get("wall_seconds") or 0)
        if any(x.get("resumed") for x in lv.get("shards") or []) or r.get("resumed") or v.get("resumed"):
            partial.append([n, m])   # a resumed shard/reach/verify step in a cell the rule times: its time is missing
    files = hashes.get("files") or {}
    prefix, upper = [], {}
    for name, h in files.items():
        mt = LEVEL.match(name)
        if mt and int(mt.group(1)) <= L:
            prefix.append((name, h.get("sha256")))
        elif mt:
            upper[name] = (h.get("sha256"), h.get("records"))
    software, inputs, manifest_counts = set(), set(), {}
    for mf in sorted(d.glob("*.manifest.json")):
        mt = re.fullmatch(r"(\d+)-(\d+)\.(prune\.)?manifest\.json", mf.name)
        if not mt:
            continue
        x, src = load(mf), "prune manifest" if mt.group(3) else "aggregate manifest"
        software.update((src, k, str(val)) for k, val in (x.get("software_sha256") or {}).items())
        inputs.update((src, Path(k).name, str(val)) for k, val in (x.get("inputs_sha256") or {}).items()
                      if not LEVELISH.match(Path(k).name))
        if mt.group(3):
            manifest_counts[(int(mt.group(1)), int(mt.group(2)))] = (x.get("counts"), x.get("verified_counts"))
    verify_manifests = 0
    for vf in sorted((d / "verify").glob("*.verify.manifest.json")):
        x = load(vf)
        verify_manifests += 1
        software.update(("verify manifest", k, str(val)) for k, val in (x.get("software_sha256") or {}).items())
        if x.get("forbidden_sha256"):
            inputs.add(("verify manifest", Path(str(x.get("forbidden_file"))).name, x["forbidden_sha256"]))
    if rsum:
        software.update(("replay summary", name, rsum[k]) for k, name in
                        (("tool_sha256", "replay-398.py"), ("enum2_sha256", "enum2.py")) if rsum.get(k))
        if rsum.get("forbidden_sha256"):
            inputs.add(("replay summary", "forbidden", rsum["forbidden_sha256"]))
    keep = d / f"{tn}-{tm}.keep.g6"
    try:
        keep_lines = tuple(x.strip() for x in keep.read_text().splitlines() if x.strip()) if keep.exists() else None
    except (OSError, UnicodeDecodeError) as e:
        raise Incomplete(f"{keep.name} unreadable ({type(e).__name__})") from None
    header = {k: val for k, val in rs.items() if k not in ("slice", "levels", "completed_through_n")}
    cfg = {k: val for k, val in config.items() if k != "slice"}
    options = hashlib.sha256(json.dumps([header, cfg], sort_keys=True).encode()).hexdigest()
    OPTIONS.setdefault(options, {"run_summary": header, "run_config": cfg})
    replay = {"verdict": replay_verdict(failed, rsum), "mode": fp.get("mode"), "runbook_result": fp.get("result"),
              "failed_marker": failed, **{k: (rsum or {}).get(k) for k in REPLAY_SUMS},
              "stages_ok": (rsum or {}).get("stages_ok"), "red_all": (rsum or {}).get("red_all"),
              "run_dag2_wall_seconds": fp.get("run_dag2_wall_seconds"),
              "replay_wall_seconds": fp.get("replay_wall_seconds")}
    return {"dir": d, "worker": d.relative_to(root).parts[0], "slice": int(named.group(1)),
            "slice_field": sl, "hashes_slice": hashes.get("slice"), "target": target, "slice_level": L,
            "ctn": rs.get("completed_through_n"), "counts": counts, "summary_digest": rows_digest(srows),
            "reach_dropped": reach_dropped, "seconds_known": round(known, 1), "resumed_cells": resumed,
            "partial": partial, "replay": replay, "prefix": intern(tuple(sorted(prefix))), "upper": upper,
            "software": intern(tuple(sorted(software))), "inputs": intern(tuple(sorted(inputs))),
            "manifest_counts": manifest_counts, "verify_manifests": verify_manifests, "keep_lines": keep_lines,
            "options": options}


def scan(root: Path):
    copies, skipped = [], []
    for d in sorted(root.glob(f"*/research/unit-distance-23/results/u23/{fs.KIND}/s*of{fs.C}")):
        if not d.is_dir():
            continue
        try:
            copies.append(read_copy(d, root))
        except Incomplete as e:
            skipped.append({"worker": d.relative_to(root).parts[0], "dir": d.name, "reason": str(e)})
    return copies, skipped


def owner(i: int) -> str:
    return f"f{i % fs.W + 1:02d}"   # the plan: worker fNN owns NN-1, NN-1+W, ... (fleet_status.py)


def choose(cands: list) -> dict:
    return min(cands, key=lambda c: (c["resumed_cells"] > 0, c["replay"]["verdict"] not in OK_REPLAY, c["worker"]))


def compare_copies(a: dict, b: dict) -> list:
    """Where two complete copies of a slice differ: counts rows, the shipped level files, the target's kept graphs."""
    diff = []
    if a["counts"] != b["counts"]:
        for cell in sorted(set(a["counts"]) | set(b["counts"])):
            ra, rb = a["counts"].get(cell), b["counts"].get(cell)
            if ra != rb:
                diff.append({"cell": list(cell), a["worker"]: cell_json(ra), b["worker"]: cell_json(rb)})
    if a["upper"] != b["upper"]:
        for name in sorted(set(a["upper"]) | set(b["upper"])):
            if a["upper"].get(name) != b["upper"].get(name):
                diff.append({"file": name, a["worker"]: a["upper"].get(name), b["worker"]: b["upper"].get(name)})
    if set(a["keep_lines"] or ()) != set(b["keep_lines"] or ()):
        diff.append({"kept_graphs": True, a["worker"]: a["keep_lines"], b["worker"]: b["keep_lines"]})
    return diff


def cell_json(r):
    return None if r is None else {"children": r[0], **(dict(zip(r[1], r[2])) if r[1] else {})}


def perturb(c: dict, mode: str, target: tuple, L: int) -> str:
    rows = dict(c["counts"])   # a copy of the mapping; the file on disk is never touched
    def bump(cell, deltas):
        ch, keys, vals = rows[cell]
        if keys is None or any(k != "children" and k not in keys for k in deltas):
            raise SystemExit(f"--perturb {mode}: cell {cell} has no prune count keys {sorted(deltas)}")
        d = dict(zip(keys, vals))
        for k, dv in deltas.items():
            if k == "children":
                ch += dv
            else:
                d[k] += dv
        rows[cell] = (ch, keys, tuple(d[k] for k in keys))
    keys = rows[target][1] or ()
    if mode == "phantom":
        bump(target, {"children": 1, **{k: 1 for k in keys if k in ("input", "survivors", "unknown", "kept")
                                        or k.endswith("_survivors")}})
        what = f"one more graph kept at {target}, consistently: children, " + ", ".join(
            k for k in keys if k in ("input", "survivors", "unknown", "kept") or k.endswith("_survivors")) + " + 1"
    elif mode == "kept":
        bump(target, {"kept": 1})
        what = f"kept + 1 at {target}"
    elif mode == "move":
        cell = next(cl for cl in sorted(rows) if cl[0] > L and get(rows[cl], "tu") > 0)
        rule = next((k for k in rows[cell][1] if k != "tu" and k.endswith("_tu")), "refuted")
        bump(cell, {"tu": -1, rule: 1})
        what = f"one tu prune booked to {rule} at {cell}"
    else:
        raise SystemExit(f"--perturb: unknown mode {mode!r} (phantom, kept, move)")
    c["counts"] = rows
    return what


def percentile(sorted_vals: list, q: float):
    return sorted_vals[max(0, math.ceil(q * len(sorted_vals)) - 1)] if sorted_vals else None


def aggregate(chosen: dict, L: int, target: tuple):
    cells, key_sets = {}, {}
    for i in sorted(chosen):
        for (n, m), r in chosen[i]["counts"].items():
            if n <= L:
                continue
            t = cells.setdefault((n, m), {"slices": 0, "children": 0, "without_prune_counts": 0,
                                          "counts": collections.Counter()})
            t["slices"] += 1
            t["children"] += r[0] or 0
            if r[1] is None:
                t["without_prune_counts"] += 1
            else:
                key_sets[r[1]] = None
                t["counts"].update(dict(zip(r[1], r[2])))
    keys = list(dict.fromkeys(k for ks in key_sets for k in ks))
    kinds = [k for k in keys if VERDICT_KEY.fullmatch(k)]
    def entry(t, **head):
        c = t["counts"]
        return {**head, "slices": t["slices"], "children": t["children"], "kept": c["kept"], "pruned": c["pruned"],
                "pruned_by_kind": {k: c[k] for k in kinds},
                "reach_dropped": t["children"] - c["input"] if not t["without_prune_counts"] else None,
                "without_prune_counts": t["without_prune_counts"], "counts": {k: c[k] for k in keys}}
    per_level = {}
    for (n, m), t in cells.items():
        lv = per_level.setdefault(n, {"cells": 0, "slices": 0, "children": 0, "without_prune_counts": 0,
                                      "counts": collections.Counter()})
        lv["cells"] += 1
        lv["slices"] = max(lv["slices"], t["slices"])
        lv["children"] += t["children"]
        lv["without_prune_counts"] += t["without_prune_counts"]
        lv["counts"].update(t["counts"])
    table = {"kinds": kinds, "count_keys": keys,
             "cells": [entry(cells[c], n=c[0], m=c[1]) for c in sorted(cells)],
             "levels": [entry(per_level[n], n=n, cells=per_level[n]["cells"]) for n in sorted(per_level)],
             "top_cell": entry(cells[target], n=target[0], m=target[1]) if target in cells else None}
    return table, cells


def self_check(ctx: dict) -> list:
    C, L, target, chosen, table = ctx["C"], ctx["L"], ctx["target"], ctx["chosen"], ctx["table"]
    kinds, out = table["kinds"], []
    def check(name, what, fails):
        out.append({"check": name, "ok": not fails, "what": what, "failures": len(fails), "examples": fails[:6]})
    upper_cells = [(i, cell, r) for i in sorted(chosen) for cell, r in chosen[i]["counts"].items() if cell[0] > L]
    # 1. coverage
    done, missing = set(chosen), set(ctx["missing"])
    fails = [f"complete {len(done)} + missing {len(missing)} != {C}"] if len(done) + len(missing) != C else []
    fails += [f"slice {i} is both complete and missing" for i in sorted(done & missing)]
    fails += [f"slice {i} is outside 0..{C - 1}" for i in sorted((done | missing) - set(range(C)))]
    check("coverage", f"complete {len(done):,} + missing {len(missing):,} = {C:,}, each of 0..{C - 1:,} once", fails)
    # 2. kept + pruned = children - reach-dropped (the reach step's own children - kept, from run-summary.json)
    fails, dropped = [], 0
    for i, cell, r in upper_cells:
        rd = chosen[i]["reach_dropped"].get(cell, 0)
        dropped += rd
        if get(r, "kept") + get(r, "pruned") != (r[0] or 0) - rd or r[1] is None:
            fails.append(f"s{i} {cell}: kept {get(r, 'kept')} + pruned {get(r, 'pruned')} != children {r[0]}"
                         f" - reach-dropped {rd}" + (" (no prune counts)" if r[1] is None else ""))
    check("cell_partition", f"kept + pruned = children - reach-dropped in all {len(upper_cells):,} cells above level "
          f"{L} of {len(chosen):,} slices (reach dropped {dropped:,} there, per run-summary.json)", fails)
    # 3. pruned = the sum of its kinds
    fails = [f"s{i} {cell}: pruned {get(r, 'pruned')} != " + " + ".join(f"{k} {get(r, k)}" for k in kinds)
             for i, cell, r in upper_cells if get(r, "pruned") != sum(get(r, k) for k in kinds)]
    check("pruned_by_kind", f"pruned = {' + '.join(kinds)} in every such cell", fails)
    # 4. counts.json = run-summary.json (digested when read; the differing cells are re-read from disk)
    fails = []
    for i in sorted(chosen):
        c = chosen[i]
        if rows_digest(c["counts"]) != c["summary_digest"]:
            try:
                rs = json.loads((c["dir"] / "run-summary.json").read_bytes())
                srows = {(lv.get("n"), lv.get("m")): row(lv.get("children"), (lv.get("prune") or {}).get("counts"))
                         for lv in rs["levels"]}
            except (OSError, ValueError, KeyError, TypeError) as e:
                fails.append(f"s{i} ({c['worker']}): counts.json differs from run-summary.json, which cannot be "
                             f"re-read now ({type(e).__name__})")
                continue
            bad = [cell for cell in sorted(set(srows) | set(c["counts"])) if srows.get(cell) != c["counts"].get(cell)]
            fails.append(f"s{i} ({c['worker']}): counts.json differs from run-summary.json at {bad[:4]}: "
                         f"{cell_json(c['counts'].get(bad[0])) if bad else ''} vs {cell_json(srows.get(bad[0])) if bad else ''}")
    check("counts_vs_summary", f"counts.json = run-summary.json (children and prune counts, every cell) in "
          f"{len(chosen):,} chosen copies", fails)
    # 5. the shipped files' record counts = counts.json
    fails, compared = [], 0
    for i in sorted(chosen):
        c = chosen[i]
        for cell, r in c["counts"].items():
            if cell[0] <= L:
                continue
            for suffix, key in FILE_KEY.items():
                h = c["upper"].get(f"{cell[0]}-{cell[1]}{suffix}")
                if h is not None and (key == "children" or (r[1] and key in r[1])):
                    compared += 1
                    if h[1] != get(r, key):
                        fails.append(f"s{i} {cell}: hashes.json {cell[0]}-{cell[1]}{suffix} has {h[1]} records, "
                                     f"counts.json {key} {get(r, key)}")
            mc = c["manifest_counts"].get(cell)
            if mc:
                compared += 1
                pc, vc = mc
                if pc != (dict(zip(r[1], r[2])) if r[1] else None):
                    fails.append(f"s{i} {cell}: {cell[0]}-{cell[1]}.prune.manifest.json counts {pc} != counts.json "
                                 f"{cell_json(r)}")
                if not vc or vc.get("records") != get(r, "input") or vc.get("kept") != get(r, "kept"):
                    fails.append(f"s{i} {cell}: verified_counts {vc} != counts.json input {get(r, 'input')}, "
                                 f"kept {get(r, 'kept')}")
        top = c["counts"].get(target)
        if top is not None:
            compared += 1
            if c["keep_lines"] is None or len(c["keep_lines"]) != get(top, "kept"):
                fails.append(f"s{i}: {target[0]}-{target[1]}.keep.g6 has "
                             f"{'no file' if c['keep_lines'] is None else len(c['keep_lines'])} graphs, counts.json "
                             f"kept {get(top, 'kept')}")
    check("counts_vs_files", f"{compared:,} record counts of the shipped level files (hashes.json, the target's keep "
          f"file, the prune manifests' counts and verified_counts) = counts.json", fails)
    # 6. the totals, re-summed slice by slice against the cell, level and target tables
    keys = ["children"] + table["count_keys"]
    by_slice, by_level_slices, top_sum = collections.Counter(), collections.defaultdict(collections.Counter), \
        collections.Counter()
    for i, cell, r in upper_cells:
        vals = collections.Counter({"children": r[0] or 0, **(dict(zip(r[1], r[2])) if r[1] else {})})
        by_slice.update(vals)
        by_level_slices[cell[0]].update(vals)
        if cell == target:
            top_sum.update(vals)
    fails, by_cell, by_level = [], collections.Counter(), collections.Counter()
    for e in table["cells"]:
        by_cell.update({"children": e["children"], **e["counts"]})
    for e in table["levels"]:
        lv = collections.Counter({"children": e["children"], **e["counts"]})
        by_level.update(lv)
        if lv != by_level_slices[e["n"]]:
            fails.append(f"level {e['n']}: table {dict(lv)} != re-summed {dict(by_level_slices[e['n']])}")
    fails += [f"{k}: per slice {by_slice[k]:,}, per cell {by_cell[k]:,}, per level {by_level[k]:,}"
              for k in keys if not by_slice[k] == by_cell[k] == by_level[k]]
    tc = table["top_cell"] or {"children": 0, "counts": {}}
    if collections.Counter({"children": tc["children"], **tc["counts"]}) != top_sum:
        fails.append(f"target cell: table {tc['children']} children, {tc['counts']} != re-summed {dict(top_sum)}")
    check("totals", f"every count summed per slice = per cell = per level ({len(keys)} keys), and the target cell", fails)
    # 7. duplicated copies identical, recomputed pair by pair (a perturbed chosen copy must show here too)
    fails, multi = [], [i for i in sorted(chosen) if len(ctx["complete_copies"][i]) > 1]
    for i in multi:
        for other in ctx["complete_copies"][i]:
            dd = compare_copies(chosen[i], other) if other is not chosen[i] else []
            if dd:
                fails.append(f"s{i}: {chosen[i]['worker']} and {other['worker']} differ: {dd[:2]}")
    check("copies_agree", f"the {len(multi)} slices with several complete copies: every copy's counts.json rows, "
          f"shipped level files and kept graphs identical", fails)
    # 8. fleet_status.py: its slice_record on the same directories, its selection, its report's numbers
    fails, fs_slices = [], {}
    for d in ctx["dirs"]:
        named = re.fullmatch(rf"s(\d+)of{C}", d.name)
        try:
            if not named or not (d / "run-summary.json").exists():
                continue
            rec = fs.slice_record(d)
        except (OSError, ValueError, KeyError, TypeError) as e:
            fails.append(f"{d.relative_to(ctx['root']).parts[0]}/{d.name}: fleet_status.slice_record failed ({e})")
            continue
        idx = int(named.group(1))
        rec["worker_dir"] = d.relative_to(ctx["root"]).parts[0]
        prev = fs_slices.get(idx)   # fleet_status.main's selection: the last copy with the highest completed_through_n
        if prev is None or (rec["completed_through_n"] or 0) >= (prev["completed_through_n"] or 0):
            fs_slices[idx] = rec
        c = ctx["by_dir"].get(d)
        if c is not None and chosen.get(c["slice"]) is c:
            mine = {"completed_through_n": c["ctn"], "top_kept": get(c["counts"][target], "kept")
                    if target in c["counts"] else None, "seconds_known": c["seconds_known"],
                    "resumed_cells": c["resumed_cells"], "verdict": c["replay"]["verdict"]}
            theirs = {**{k: rec[k] for k in ("completed_through_n", "top_kept", "seconds_known", "resumed_cells")},
                      "verdict": rec["replay"]["verdict"]}
            if mine != theirs:
                fails.append(f"s{c['slice']} ({c['worker']}): here {mine}, fleet_status.slice_record {theirs}")
    fs_done = {i for i, r in fs_slices.items() if r["completed_through_n"] == target[0]}
    fs_top = {i: r["top_kept"] for i, r in fs_slices.items() if r["top_kept"]}
    my_top = {i: get(c["counts"][target], "kept") for i, c in chosen.items()
              if target in c["counts"] and get(c["counts"][target], "kept")}
    if fs_done != done:
        torn = {s["dir"]: s["reason"] for s in ctx["skipped"]}
        fails.append(f"fleet_status.py counts {len(fs_done):,} slices done, this record {len(done):,}: only there "
                     f"{sorted(fs_done - done)[:10]}, only here {sorted(done - fs_done)[:10]}"
                     + (f"; skipped here as incomplete (a copy being rewritten? re-run): {torn}" if torn else ""))
    if sum(fs_top.values()) != (table["top_cell"] or {}).get("kept", 0) or fs_top != my_top:
        fails.append(f"target cell kept: fleet_status.py {sum(fs_top.values())} {fs_top}, this record "
                     f"{(table['top_cell'] or {}).get('kept', 0)} {my_top}")
    ctx["fleet_status"] = {"slices_done": len(fs_done), "top_level_nonempty": fs_top,
                           "top_kept_total": sum(fs_top.values()),
                           "replay_not_pass": {i: r["replay"]["verdict"] for i, r in fs_slices.items()
                                               if i in fs_done and r["replay"]["verdict"] not in OK_REPLAY}}
    check("fleet_status", f"fleet_status.py's slice_record and selection over the same {len(ctx['dirs']):,} "
          f"directories: {len(fs_done):,} slices done, target cell kept {sum(fs_top.values())}; per chosen copy "
          f"the target cell's kept, timing, resumed cells and replay verdict", fails)
    return out


def ranges(xs) -> str:
    xs, out = sorted(xs), []
    for x in xs:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in out)


def run_top_level_check(root: Path) -> dict:
    cmd = [sys.executable, str(HERE.parent / "top_level_check.py"), str(root)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=fs.REPO, timeout=3600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ran": False, "error": str(e)}
    lines = r.stdout.strip().splitlines()
    return {"ran": True, "command": "python3 research/unit-distance-23/tools/top_level_check.py <root>",
            "exit": r.returncode, "verdict": next((x for x in reversed(lines) if x.startswith("TOP-LEVEL")), None),
            "lines": lines, "stderr": r.stderr.strip()[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT, help="the fleet's extracted results root (read-only)")
    ap.add_argument("--out", type=Path, help="write the JSON record here")
    ap.add_argument("--self-check", action="store_true", help="recompute the identities; exit 1 if one breaks")
    ap.add_argument("--perturb", metavar="SLICE[:MODE]", help="self-check control: perturb one slice's counts in memory")
    ap.add_argument("--no-top-level-check", action="store_true", help="do not run top_level_check.py")
    a = ap.parse_args()
    if a.perturb and (not a.self_check or a.out):
        ap.error("--perturb is a control for --self-check and writes no record: pass --self-check, not --out")
    root = a.root.resolve()
    if not root.is_dir():
        ap.error(f"no extraction at {root}")
    t0 = time.monotonic()
    copies, skipped = scan(root)
    C = fs.C
    problems = []
    levels_seen = collections.Counter(c["slice_level"] for c in copies)
    targets = collections.Counter(c["target"] for c in copies)
    if not copies:
        print(f"no slice copies under {root}", file=sys.stderr)
        return 1
    L, target = levels_seen.most_common(1)[0][0], targets.most_common(1)[0][0]
    misfiled, good = [], []
    for c in copies:
        want = [L, c["slice"], C]
        if c["slice_field"] != want or c["hashes_slice"] != want or c["target"] != target or not 0 <= c["slice"] < C:
            misfiled.append({"worker": c["worker"], "dir": c["dir"].name, "run_summary_slice": c["slice_field"],
                             "hashes_slice": c["hashes_slice"], "target": list(c["target"])})
        else:
            good.append(c)
    if misfiled:
        problems.append(f"{len(misfiled)} copies whose slice or target fields do not match their directory or the "
                        f"fleet (slice level {L}, {C} slices, target {target}): excluded")
    by_slice = collections.defaultdict(list)
    for c in good:
        by_slice[c["slice"]].append(c)
    complete = {i: [c for c in cs if c["ctn"] == target[0]] for i, cs in by_slice.items()}
    complete = {i: cs for i, cs in complete.items() if cs}
    unfinished = [{"worker": c["worker"], "slice": c["slice"], "completed_through_n": c["ctn"]}
                  for c in good if c["ctn"] != target[0]]
    chosen = {i: choose(cs) for i, cs in complete.items()}
    perturbed = None
    if a.perturb:
        s, _, mode = a.perturb.partition(":")
        if not s.isdigit() or int(s) not in chosen:
            ap.error(f"--perturb {a.perturb}: slice {s} has no complete copy")
        perturbed = {"slice": int(s), "worker": chosen[int(s)]["worker"],
                     "what": perturb(chosen[int(s)], mode or "phantom", target, L)}
    missing = sorted(set(range(C)) - set(chosen))
    needs_rerun = sorted(i for i, cs in complete.items() if all(c["resumed_cells"] for c in cs))
    duplicates = {}
    for i, cs in sorted(complete.items()):
        if len(by_slice[i]) > 1:
            diffs = [{"other": o["worker"], "differences": dd} for o in cs if o is not chosen[i]
                     for dd in [compare_copies(chosen[i], o)] if dd]
            duplicates[i] = {"copies": [c["worker"] for c in by_slice[i]], "chosen": chosen[i]["worker"],
                             "complete_copies": len(cs), "differences": diffs}
    disagree = {i: d for i, d in duplicates.items() if d["differences"]}
    if disagree:
        problems.append(f"copies disagree in {len(disagree)} slices: {ranges(disagree)}")

    # 2-3. the tree and its target cell
    table, _ = aggregate(chosen, L, target)
    cell_sets = collections.Counter(tuple(sorted(cl for cl in c["counts"] if cl[0] > L)) for c in chosen.values())
    if len(cell_sets) > 1:
        problems.append(f"the chosen copies have {len(cell_sets)} different sets of cells above level {L}")
    lacking = [e for e in table["cells"] if e["without_prune_counts"]]
    if lacking:
        problems.append(f"{len(lacking)} cells above level {L} lack prune counts in some slice")
    tn, tm = target
    top_slices = {i: get(c["counts"][target], "kept") for i, c in chosen.items()
                  if target in c["counts"] and get(c["counts"][target], "kept")}
    records = sorted(int(p.name[1:].split("of")[0]) for p in RECORDS.glob(f"s*of{C}")
                     if re.fullmatch(rf"s\d+of{C}", p.name) and (p / f"{tn}-{tm}.g6").exists()
                     and (p / f"{tn}-{tm}.certs.jsonl").exists())
    top_level = {"cell": [tn, tm], "children": (table["top_cell"] or {}).get("children"),
                 "kept": (table["top_cell"] or {}).get("kept"), "pruned": (table["top_cell"] or {}).get("pruned"),
                 "slices_with_children": sorted(i for i, c in chosen.items()
                                                if target in c["counts"] and c["counts"][target][0]),
                 "slices_kept": top_slices, "kept_graphs": {i: list(chosen[i]["keep_lines"] or ()) for i in top_slices},
                 "records_dir": str(RECORDS.relative_to(fs.REPO)), "records": records,
                 "kept_without_record": sorted(set(top_slices) - set(records)), "top_level_check": None}

    # 4. G4
    rep = [c["replay"] for c in chosen.values()]
    replays = {"rule": "fleet_status.py slice_record: FAILED marker, else MISMATCH, UNREPLAYABLE, EMPTY "
                       "(processed_parents 0), PASS",
               "verdicts": dict(collections.Counter(r["verdict"] for r in rep)),
               "modes": dict(collections.Counter(r["mode"] for r in rep)),
               "full_mode_red_all": sum(1 for r in rep if r["mode"] == "full" and r["red_all"] is True),
               "totals": {k: sum(r[k] or 0 for r in rep) for k in REPLAY_SUMS},
               "not_pass_or_empty": {i: c["replay"]["verdict"] for i, c in sorted(chosen.items())
                                     if c["replay"]["verdict"] not in OK_REPLAY},
               "runbook_verdict_differs": {i: [c["replay"]["verdict"], c["replay"]["runbook_result"]]
                                           for i, c in sorted(chosen.items())
                                           if c["replay"]["verdict"] != c["replay"]["runbook_result"]},
               "other_copies_not_pass_or_empty": [{"slice": c["slice"], "worker": c["worker"],
                                                   "verdict": c["replay"]["verdict"]} for c in good
                                                  if c["replay"]["verdict"] not in OK_REPLAY
                                                  and chosen.get(c["slice"]) is not c]}
    if replays["not_pass_or_empty"] or replays["other_copies_not_pass_or_empty"]:
        problems.append(f"G4 replays not PASS/EMPTY: chosen {replays['not_pass_or_empty']}, other copies "
                        f"{replays['other_copies_not_pass_or_empty']}")

    # 5. cost
    timed = {i: c["seconds_known"] for i, c in chosen.items() if not c["resumed_cells"]}
    vals = sorted(timed.values())
    heavy = sorted(timed, key=lambda i: (-timed[i], i))[:5]
    cost = {"rule": "fleet_status.py slice_record: per cell above the slice level not resumed (neither the cell nor "
                    "its prune step), max(longest shard, shards summed / 4) + prune step + stage verification",
            "slices_timed": len(timed), "slices_excluded_resumed": sorted(i for i, c in chosen.items()
                                                                          if c["resumed_cells"]),
            "seconds_total": round(sum(vals), 1), "hours_total": round(sum(vals) / 3600, 2),
            "per_slice": {"median": round(statistics.median(vals), 2) if vals else None, "p90": percentile(vals, 0.9),
                          "max": vals[-1] if vals else None, "p90_method": "nearest rank"},
            "heaviest": [{"slice": i, "worker": chosen[i]["worker"], "seconds": timed[i]} for i in heavy],
            "cells_with_a_resumed_step_the_rule_times": {i: c["partial"] for i, c in sorted(chosen.items())
                                                          if c["partial"]},
            "timed_slices_with_such_a_cell": sorted(i for i in timed if chosen[i]["partial"]),
            "runbook_clocks": {"copies": len(chosen),
                               "run_dag2_wall_seconds": sum(c["replay"]["run_dag2_wall_seconds"] or 0
                                                            for c in chosen.values()),
                               "replay_wall_seconds": sum(c["replay"]["replay_wall_seconds"] or 0
                                                          for c in chosen.values()),
                               "source": "replay/fingerprint.json (the runbook's clock around run-dag2.py and the G4 "
                                         "replay; after a restart it covers the last session only)"}}

    # 6. provenance
    prefix_sets = collections.Counter(c["prefix"] for c in good)
    per_name = collections.defaultdict(collections.Counter)
    for pset, k in prefix_sets.items():
        for name, sha in pset:
            per_name[name][sha] += k
    prefix = {"files": len(per_name), "copies": len(good), "agree": len(prefix_sets) == 1,
              "differing_files": {n: dict(v) for n, v in per_name.items() if len(v) > 1 or sum(v.values()) != len(good)}}
    if not prefix["agree"]:
        problems.append(f"the prefix (levels <= {L}) differs between copies: {len(prefix_sets)} different sets")
    def hash_table(field):
        tab = collections.defaultdict(collections.Counter)
        for tup, k in collections.Counter(c[field] for c in good).items():
            for src, name, sha in tup:
                tab[(src, name)][sha] += k
        return {f"{src}: {name}": {"values": dict(v), "copies": sum(v.values())} for (src, name), v in sorted(tab.items())}
    software, inputs = hash_table("software"), hash_table("inputs")
    odd = [k for k, v in {**software, **inputs}.items() if len(v["values"]) > 1 or v["copies"] != len(good)]
    if odd:
        problems.append(f"software or data hashes that differ between copies, or are missing from some: {odd}")
    opts = collections.Counter(c["options"] for c in good)
    if len(opts) > 1:
        problems.append(f"{len(opts)} different sets of run options among the copies")
    workers = collections.Counter(c["worker"] for c in good)
    chosen_w = collections.Counter(c["worker"] for c in chosen.values())
    all_dirs = sorted(p.name for p in root.iterdir() if p.is_dir())
    tags = collections.defaultdict(list)
    for w in all_dirs:
        tags[w.split("-")[0]].append(w)
    provenance = {"prefix": prefix, "software": software, "inputs": inputs,
                  "software_all_same": not odd, "verify_manifests_read": sum(c["verify_manifests"] for c in good),
                  "run_options_identical": len(opts) == 1, "run_options": OPTIONS[opts.most_common(1)[0][0]],
                  "workers": {w: {"copies": workers.get(w, 0), "chosen": chosen_w.get(w, 0)} for w in all_dirs},
                  "worker_dirs_with_copies": len(workers), "worker_dirs_without_copies": [w for w in all_dirs
                                                                                          if not workers.get(w)],
                  "worker_tags_with_several_dirs": {t: sorted(ws) for t, ws in sorted(tags.items()) if len(ws) > 1},
                  "copies_outside_plan_owner": dict(collections.Counter(
                      c["worker"] for c in good if c["worker"].split("-")[0] != owner(c["slice"])))}

    tlc = None
    if not a.no_top_level_check:
        tlc = run_top_level_check(root)
        top_level["top_level_check"] = tlc
        if not tlc.get("ran") or tlc.get("exit") != 0:
            problems.append(f"top_level_check.py: {tlc.get('verdict') or tlc.get('error')} (exit {tlc.get('exit')})")

    ctx = {"C": C, "L": L, "target": target, "chosen": chosen, "table": table, "missing": missing,
           "duplicates": duplicates, "complete_copies": complete, "root": root, "skipped": skipped,
           "dirs": [c["dir"] for c in copies] + [root / s["worker"] / "research/unit-distance-23/results/u23" /
                                                 fs.KIND / s["dir"] for s in skipped],
           "by_dir": {c["dir"]: c for c in good}}
    checks = self_check(ctx) if a.self_check else None
    if checks and not all(x["ok"] for x in checks):
        problems.append("SELF-CHECK FAILED: " + ", ".join(x["check"] for x in checks if not x["ok"]))

    coverage = {"slices": C, "complete": len(chosen), "missing": len(missing), "missing_slices": missing,
                "missing_by_plan_owner": dict(sorted(collections.Counter(owner(i) for i in missing).items())),
                "every_copy_resumed": needs_rerun, "several_copies": duplicates,
                "several_copies_agree": not disagree, "copies_read": len(copies), "copies_skipped": skipped,
                "copies_misfiled": misfiled, "copies_unfinished": unfinished}
    record = {"tool": str(HERE.relative_to(fs.REPO)), "tool_sha256": hashlib.sha256(HERE.read_bytes()).hexdigest(),
              "root": str(root), "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "plan": {"kind": fs.KIND, "slices": C, "workers": fs.W, "slice_level": L, "target": list(target)},
              "final": not missing and not needs_rerun and not problems,
              "coverage": coverage, "tree": table, "top_level": top_level, "replays": replays, "cost": cost,
              "provenance": provenance,
              "slices": {i: {"chosen": chosen[i]["worker"] if i in chosen else None,
                             "copies": [{"worker": c["worker"], "completed_through_n": c["ctn"],
                                         "resumed_cells": c["resumed_cells"], "replay": c["replay"]["verdict"]}
                                        for c in by_slice[i]],
                             **({"seconds_known": chosen[i]["seconds_known"], "resumed_cells": chosen[i]["resumed_cells"],
                                 "target_cell": cell_json(chosen[i]["counts"].get(target)),
                                 "replay": chosen[i]["replay"]} if i in chosen else {})}
                         for i in sorted(by_slice)},
              "problems": problems, "self_check": checks, "perturbed": perturbed,
              "fleet_status": ctx.get("fleet_status"), "seconds": round(time.monotonic() - t0, 1)}
    if a.out:
        a.out.write_text(json.dumps(record, indent=1, default=str) + "\n")
    print(markdown(record))
    if checks and not all(x["ok"] for x in checks):
        print(f"SELF-CHECK FAILED: {', '.join(x['check'] for x in checks if not x['ok'])}", file=sys.stderr)
    return 1 if problems else 0


def num(x) -> str:
    return "-" if x is None else f"{x:,.1f}"


def markdown(r: dict) -> str:
    P, cov, tree, top, rep, cost, prov = (r[k] for k in ("plan", "coverage", "tree", "top_level", "replays", "cost",
                                                          "provenance"))
    L, (tn, tm), kinds = P["slice_level"], P["target"], tree["kinds"]
    dups = collections.defaultdict(list)
    for i, d in cov["several_copies"].items():
        dups[tuple(d["copies"])].append(i)
    o = [f"# u(23) fleet aggregate, {P['kind']}" + ("  (PERTURBED IN MEMORY: not a record)" if r["perturbed"] else ""),
         f"`{r['root']}`: {cov['copies_read']:,} slice copies read in {prov['worker_dirs_with_copies']:,} worker directories, "
         f"{len(cov['copies_skipped'])} skipped as incomplete, {len(cov['copies_misfiled'])} misfiled, "
         f"{len(cov['copies_unfinished'])} unfinished; {r['seconds']} s",
         "", f"## 1. Coverage ({P['slices']:,} slices at level {L}, target ({tn},{tm}))",
         f"- complete: **{cov['complete']:,}**; missing: **{cov['missing']:,}**" + (
             " (by plan owner: " + ", ".join(f"{w} {k}" for w, k in sorted(
                 cov["missing_by_plan_owner"].items(), key=lambda x: (-x[1], x[0]))) + ")" if cov["missing"] else ""),
         f"- every copy has resumed cells (fresh rerun needed): {len(cov['every_copy_resumed'])}"
         + (f": {ranges(cov['every_copy_resumed'])}" if cov["every_copy_resumed"] else ""),
         f"- several copies: {len(cov['several_copies'])}" + (": " + "; ".join(
             f"{ranges(ix)} in {' + '.join(pair)}" for pair, ix in dups.items()) if dups else "")
         + f"; counts, shipped files and kept graphs agree: {'yes' if cov['several_copies_agree'] else '**NO**'}"]
    if cov["copies_skipped"]:
        o.append("- skipped: " + "; ".join(f"{s['worker']}/{s['dir']} ({s['reason']})" for s in cov["copies_skipped"][:8]))
    o += ["", f"## 2. Tree above level {L} ({cov['complete']:,} slices, one copy each)",
          "| n | cells | children | kept | pruned | " + " | ".join(kinds) + " | % pruned |",
          "|---|---:|---:|---:|---:|" + "---:|" * len(kinds) + "---:|"]
    for e in tree["levels"]:
        o.append(f"| {e['n']} | {e['cells']} | {e['children']:,} | {e['kept']:,} | {e['pruned']:,} | " + " | ".join(
            f"{e['pruned_by_kind'][k]:,}" for k in kinds) + " | "
            + (f"{100 * e['pruned'] / e['children']:.1f} |" if e["children"] else "- |"))
    tc = tree["top_cell"] or {}
    if tc:
        o.append(f"| ({tn},{tm}) | 1 | {tc['children']:,} | {tc['kept']:,} | {tc['pruned']:,} | " + " | ".join(
            f"{tc['pruned_by_kind'][k]:,}" for k in kinds) + " | "
            + (f"{100 * tc['pruned'] / tc['children']:.1f} |" if tc["children"] else "- |"))
    other = [k for k in tree["count_keys"] if k not in kinds and k not in ("kept", "pruned")]
    tot = collections.Counter()
    for e in tree["levels"]:
        tot.update(e["counts"])
    reach = sum(e["reach_dropped"] or 0 for e in tree["levels"])
    o.append(f"Other count keys summed over these cells: " + ", ".join(f"{k} {tot[k]:,}" for k in other)
             + f". Children minus prune input (the reach filter's drops): {reach:,}.")
    tlc = top["top_level_check"]
    o += ["", f"## 3. Top level ({tn},{tm})",
          f"- children **{top['children']:,}**, kept **{top['kept']:,}**; slices with children: "
          f"{ranges(top['slices_with_children']) or 'none'}; slices that kept anything: "
          + (", ".join(f"{i} ({k}: " + ", ".join(f"`{g}`" for g in top["kept_graphs"][i][:3])
                       + (", ..." if len(top["kept_graphs"][i]) > 3 else "") + ")"
                       for i, k in top["slices_kept"].items()) or "none"),
          f"- records under {top['records_dir']}: {ranges(top['records']) or 'none'}"
          + (f"; kept without a record: {top['kept_without_record']}" if top["kept_without_record"] else ""),
          "- top_level_check.py: " + (f"{tlc['verdict']} (exit {tlc['exit']})" if tlc and tlc.get("ran") else
                                      "not run" if tlc is None else f"could not run ({tlc.get('error')})")]
    t = rep["totals"]
    o += ["", "## 4. G4 replays (fleet_status.py's rule, chosen copies)",
          "- verdicts: " + ", ".join(f"{k} {v:,}" for k, v in sorted(rep["verdicts"].items()))
          + "; modes: " + ", ".join(f"{k} {v:,}" for k, v in sorted(rep["modes"].items(), key=str))
          + f"; full-mode replays with every red control red: {rep['full_mode_red_all']:,}",
          f"- parents sampled {t['sampled_parents']:,}, processed {t['processed_parents']:,}; production children "
          f"compared {t['production_children_compared']:,}; mismatching parents {t['mismatching_parents']:,}; stage "
          f"files re-derived {t['stages_checked']:,}",
          f"- not PASS/EMPTY: {rep['not_pass_or_empty'] or 'none'}; other copies: "
          f"{rep['other_copies_not_pass_or_empty'] or 'none'}; runbook verdict differs from the rule: "
          f"{len(rep['runbook_verdict_differs'])}"]
    ps = cost["per_slice"]
    o += ["", f"## 5. Cost (fleet_status.py's rule: step timings of the cells above level {L}, none resumed)",
          f"- {cost['slices_timed']:,} slices timed, {len(cost['slices_excluded_resumed'])} excluded for resumed cells: "
          f"**{cost['seconds_total']:,.1f} s** ({cost['hours_total']:,.2f} h)",
          f"- per slice: median {num(ps['median'])} s, p90 {num(ps['p90'])} s, max {num(ps['max'])} s; heaviest: "
          + ", ".join(f"s{h['slice']} {h['seconds']:,.1f} s ({h['worker']})" for h in cost["heaviest"]),
          f"- runbook clocks over {cost['runbook_clocks']['copies']:,} chosen copies (replay/fingerprint.json): "
          f"run-dag2.py {cost['runbook_clocks']['run_dag2_wall_seconds']:,} s, G4 replay "
          f"{cost['runbook_clocks']['replay_wall_seconds']:,} s"
          + (f"\n- a cell the rule times has a resumed shard, reach or verify step (its time is missing) in "
             f"{len(cost['cells_with_a_resumed_step_the_rule_times'])} slices: "
             f"{ranges(cost['cells_with_a_resumed_step_the_rule_times'])}; timed among them: "
             f"{ranges(cost['timed_slices_with_such_a_cell']) or 'none'}"
             if cost["cells_with_a_resumed_step_the_rule_times"] else "")]
    pre = prov["prefix"]
    tools = {}
    for k, v in prov["software"].items():
        name = k.split(": ", 1)[1]
        tools.setdefault(name, set()).update(v["values"])
    o += ["", "## 6. Provenance",
          f"- prefix (levels <= {L}, hashes.json): {pre['files']} files, "
          + (f"identical sha256 in all {pre['copies']:,} copies" if pre["agree"] else
             f"**DIFFERS**: {list(pre['differing_files'])[:5]}"),
          f"- software ({len(prov['software'])} source/tool entries from the aggregate, prune and "
          f"{prov['verify_manifests_read']:,} verify manifests and the replay summaries) and data inputs "
          f"({len(prov['inputs'])}): " + ("one hash each in every copy" if prov["software_all_same"] else "**DIFFER**")
          + "; " + ", ".join(f"{n} {'/'.join(sorted(x[:8] if re.fullmatch('[0-9a-f]{64}', x) else x for x in s))}"
                             for n, s in sorted(tools.items())),
          f"- run options (run-summary header, run-config.json) identical in every copy: "
          f"{'yes' if prov['run_options_identical'] else '**NO**'}",
          f"- worker directories: {prov['worker_dirs_with_copies']} of {len(prov['workers'])} hold slice copies"
          + (f"; none in {', '.join(prov['worker_dirs_without_copies'])}" if prov["worker_dirs_without_copies"] else "")
          + "; plan tags with several directories: " + (", ".join(
              f"{t} ({' '.join(ws)})" for t, ws in prov["worker_tags_with_several_dirs"].items()) or "none")
          + (f"; copies outside the plan's owner: {prov['copies_outside_plan_owner']}"
             if prov["copies_outside_plan_owner"] else "")]
    if r["self_check"] is not None:
        o += ["", "## Self-check" + (f" (PERTURBED: s{r['perturbed']['slice']} {r['perturbed']['worker']}: "
                                     f"{r['perturbed']['what']})" if r["perturbed"] else "")]
        for x in r["self_check"]:
            o.append(f"- {'PASS' if x['ok'] else '**FAIL**'} {x['check']}: {x['what']}"
                     + ("".join(f"\n    - {e}" for e in x["examples"]) + (f"\n    - ... {x['failures']} in all"
                                                                           if x["failures"] > len(x["examples"]) else "")
                        if not x["ok"] else ""))
        bad = [x["check"] for x in r["self_check"] if not x["ok"]]
        o.append(f"SELF-CHECK {'OK' if not bad else 'FAILED'}: {len(r['self_check']) - len(bad)} of "
                 f"{len(r['self_check'])} identities hold" + (f"; broken: {', '.join(bad)}" if bad else ""))
    o += ["", "Problems: " + ("none" if not r["problems"] else "\n" + "\n".join(f"- {p}" for p in r["problems"]))]
    return "\n".join(o)


if __name__ == "__main__":
    sys.exit(main())
