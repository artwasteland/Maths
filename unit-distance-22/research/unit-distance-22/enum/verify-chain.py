#!/usr/bin/env python3
"""The stranger's check of a pruned DAG directory (enum/PRUNING.md, Section 3).

Trusting nothing but the files, it verifies, for a run-dag2.py output directory:
  (k) COVERAGE, derived here from the target alone and never from run-summary.json: the u-bar table
      ((g): AMP's, or a recorded and justified lowering), Schade's windows from the target down to the
      seed level (which must lie in 1..N-1, as run-dag2.py requires), and with --reach the L4 table
      recomputed from its root k, which must itself be justified (at most Schade's bound
      target_m - u-bar(target_n - 1), or a recorded lemma); a stored reach.json table that differs is
      refused. These give the REQUIRED CELLS (every (n, m) of the table, or of the windows without
      --reach, from the seed level to the target; the target cell always among them) and each cell's
      ALLOWED PARENTS (L4(ii): the parent edge counts in the derived window with m - m' >= k(n, m)).
      --expect-target N M, --expect-seed S and --expect-slices LEVEL COUNT pin the configuration the run
      must have, so that it is judged against the caller's target, seed and slicing, not its own files'.
      run-config.json, run-summary.json and reach.json must name the same target, seed level, root and
      slice; the summary's windows and reach levels must be the derived ones; every required cell must
      be listed in the summary exactly once (and no other cell), the run must be complete
      (completed_through_n = the target's n), and every required cell's files must be present and pass
      (b) to (f), its parent sources being exactly its allowed parents;
  (c) reach.json's table follows from its root by the L4 recursion, and every
      <n>-<m>.reach.g6 equals <n>-<m>.g6 minus the graphs of minimum degree below k(n, m);
  (b) every <n>-<m>.keep.g6 equals, in order, the records of <n>-<m>.certs.jsonl with verdict
      embedded or unknown, the certs list equals the stage input, and every pruned graph has a
      tu or refuted witness object;
  (d) every _parents/<n>-<m>.g6 is the byte concatenation of the parent sources listed in the
      aggregate manifest, with the listed hashes, and those sources are exactly the stage files
      of the parents L4 allows (or Schade's window without --reach), computed as in (k);
  (e) every shard manifest hashes the parent file it names and the shard ranges tile it;
  (a) with --check, check/udcheck.py replays every certs file against its stage input
      (check/udcheck398.py for a forbidden-set-398 run);
  (f) the forbidden set of run-config.json (74 when absent): every seed, aggregate, shard and
      prune manifest hashes that set's forbidden file with its pinned sha256, set-398 manifests
      say forbidden_set 398, and with verify_stages every level has a clean
      <n>-<m>.verify.manifest.json for its current stage file;
  (g) reach.json's u-bar table is the built-in one (AMP) except for recorded overrides, each
      below the built-in value, not below the best known lower bound on u(n), and justified;
  (i) the linear rules (RHOMBUS-SPEC.md amendment 2): a run made with one (run-config.json
      "rhombus": true from run-dag2.py --rhombus, or "triangles": true) has it recorded in every
      prune manifest and every aggregate manifest, and --check replays every certs file with
      check/udcheck_rhombus.py (--udcheck-rhombus PATH names another copy) with --data-dir and
      --forbidden-set; a run whose manifests record no rule has none in any manifest. With or
      without --check, a certs file holding a "rhombus" or "tri" witness in a run whose manifests
      do not record that rule (--rhombus, --triangles) is REFUSED;
  (j) every prune manifest names the run's target, and that target (N, M) has M >= u(N) proved (the
      checkers never see the target; a tu record prunes only at such a target, PRUNING.md L2, L5).
It does not verify the generator itself (CONTRACT 3.6 controls do that).

Verdicts (the last line) and exit codes:
  CHAIN OK        exit 0, only when the check was EXHAUSTIVE for this run: every required cell inspected
                  (no --from-n), every pruned cell's certificates replayed (--check), no problem; the line
                  before it says "COVERAGE exhaustive". A sliced run is one slice of its fleet: the fleet
                  needs every slice.
  CHAIN PARTIAL   exit 3: no problem found, but the check was not exhaustive (--from-n, no --check, or
                  --summary-only); the reasons are on the line.
  CHAIN FAIL      exit 1: problems (each on a PROBLEM line). Exit 2: the check could not run.

--summary-only RUN [RUN ...]: a coverage audit for run directories that are gone, from their pushed
run-config.json, run-summary.json and reach.json (and the summary's pushed history/, the runbook's
hashes.json and replay/ when present; no level, keep or certificate file is read): the pins and (k)
above; each summary entry's parent edge counts, parent sources, shards and counts against the derivation,
every cell, level and count a nonnegative integer (the G4 replay's per-cell counts too, before they are
compared); hashes.json naming the run's slice and holding the summary's record
counts; the G4 replay's verdict derived here from its own evidence (every aggregate recomputed from the
detailed records it summarises, per_cell, per_level, stages, seeds and red controls, and any disagreement a
failure; every seed level identical, no mismatch, every stage re-derived, full-mode red controls red; EMPTY
decided first, from verified emptiness: a slice-mode replay that exited nonzero having sampled nothing, of a
slice with no parent above the slice level and every share 0; PASS only with exit 0, parents sampled and
all identical) and equal to the PASS or EMPTY its label says, of this slice, its re-derived slice files the
sizes the summary records. With several slices of one fleet: every slice index 0..COUNT-1 present
(COUNT >= 1), the shared prefix's files identical in every slice and copy (hashes.json: every worker
computes the prefix itself, so this is also a determinism check), copies of one slice identical and their
shares merged (a share two copies record differently fails), the G4 replays' prefix fingerprints one, and
every present slice recording its share of every slice-level parent cell, each at most the cell, adding up
to it. --require-hashes and --require-g4 make those files compulsory. Verdicts:
contradictions give COVERAGE (summary only) FAIL and CHAIN FAIL (exit 1); anything coverage needs that
the summaries do not record (a resumed cell whose parents no pushed version records, a present slice's
missing share) gives COVERAGE (summary only) UNRESOLVED and CHAIN PARTIAL (exit 4); only a fully recorded
fleet gives COVERAGE (summary only) OK and CHAIN PARTIAL (exit 3). Never CHAIN OK.

usage: verify-chain.py RUN_DIR [--check] [--from-n N] [--udcheck-rhombus PATH] [--expect-target N M]
                       [--expect-seed S] [--expect-slices LEVEL COUNT]
       verify-chain.py --summary-only RUN_DIR [RUN_DIR ...] [--expect-...] [--require-hashes] [--require-g4]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PYTHON = Path("~/tools/pyenv-maths/bin/python").expanduser()

# u-bar(n): AMP Table 1 (u(n) exactly for n <= 21), AMP's u-bar(22) = 62 and u-bar(23) = 66.
UBAR_BUILTIN = {0: 0, 1: 0, 2: 1, 3: 3, 4: 5, 5: 7, 6: 9, 7: 12, 8: 14, 9: 18, 10: 20, 11: 23,
                12: 27, 13: 30, 14: 33, 15: 37, 16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57,
                22: 62, 23: 66}
# best known lower bounds on u(n), each attained by a known unit-distance graph
UBAR_LOWER = {**{n: v for n, v in UBAR_BUILTIN.items() if n <= 21}, 22: 60, 23: 64}
FORBIDDEN_SHA256 = {74: "ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a",
                    398: "8e8a81a145f75a6599332f50258f1bd28b5f439d19a3ed53351cbbba1b6adc7c"}
# linear rules: the flag run-dag2.py and prune.py record -> the witness key of its certificates
RULE_WITNESS = {"rhombus": "rhombus", "triangles": "tri"}
# Proved upper bounds on u(n) (prune.py UPPER: AMP Theorem 1 for n <= 22; u(23) <= 65 from u(22) = 60 and
# Schade's lemma). The certificate checkers never see the target, so a tu record (a gadget, L2, or a
# rhombus R2 certificate) prunes soundly only at a target (N, M) with M >= u(N) proved: checked here.
PROVED_UPPER = {16: 41, 17: 43, 18: 46, 19: 50, 20: 54, 21: 57, 22: 61, 23: 65}
# Root minimum-degree bounds proved by a lemma beyond Schade's bound (run-dag2.py ROOT_K_LEMMAS).
ROOT_K_LEMMAS = {(22, 61): 5}   # delta4/RESULT.md Lemma D4: every (22,61) unit-distance graph has minimum degree 5


class Bad(Exception):
    pass


def nonneg(value: object) -> bool:
    """A count: a nonnegative integer (not a bool)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_pins(config: dict, pins: dict, problems: list[str], where: str = "") -> None:
    """What the caller pins on the command line (--expect-target, --expect-seed, --expect-slices), against the
    run's own run-config.json: a run is judged against the configuration it is meant to have, not the one it
    states."""
    if pins.get("target") is not None and config.get("target") != list(pins["target"]):
        problems.append(f"{where}run-config.json target {config.get('target')} is not the pinned {list(pins['target'])}")
    if pins.get("seed") is not None and config.get("seed_n") != pins["seed"]:
        problems.append(f"{where}run-config.json seed level {config.get('seed_n')} is not the pinned {pins['seed']}")
    if pins.get("slices") is not None:
        level, count = pins["slices"]
        s = config.get("slice")
        if not (isinstance(s, list) and len(s) == 3 and s[0] == level and s[2] == count):
            problems.append(f"{where}run-config.json slice {s} is not a slice of the pinned {count} at level {level}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise Bad(f"{path}: missing final newline")
    return raw.decode("ascii").split("\n")[:-1] if raw else []


def graph6(code: str) -> tuple[int, int, int]:
    n = ord(code[0]) - 63
    bits = "".join(f"{ord(c) - 63:06b}" for c in code[1:])
    deg = [0] * n
    k = 0
    for j in range(1, n):
        for i in range(j):
            if bits[k] == "1":
                deg[i] += 1
                deg[j] += 1
            k += 1
    return n, sum(deg) // 2, (min(deg) if n else 0)


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def schade_windows(tn: int, tm: int, seed_n: int, ubar: dict[int, int]) -> dict[int, tuple[int, int]]:
    """Schade's windows: an (n, m) graph's induced subgraphs on n - 1 vertices have at least
    ceil(m (n - 2) / n) edges, and at most u-bar(n - 1)."""
    windows = {tn: (tm, tm)}
    for n in range(tn, seed_n, -1):
        low, high = windows[n]
        lower, upper = ceil_div(low * (n - 2), n), min(ubar[n - 1], high)
        if lower > upper:
            raise Bad(f"empty induced-parent window at order {n - 1}")
        windows[n - 1] = (lower, upper)
    return windows


def recompute_reach(tn: int, tm: int, root_k: int, seed_n: int, ubar: dict[int, int]) -> dict[int, dict[int, int]]:
    """The L4 table R(n) = {m: k}, backward from the target's root k."""
    table = {tn: {tm: root_k}}
    for n in range(tn - 1, seed_n - 1, -1):
        level: dict[int, int] = {}
        for cm, k in table[n + 1].items():
            for d in range(k, min(n, (2 * cm) // (n + 1)) + 1):
                m = cm - d
                if 0 <= m <= ubar[n]:
                    level[m] = min(level.get(m, d), max(0, d - 1))
        table[n] = level
    return table


def check_ubar(reach: dict) -> list[str]:
    """(g) reach.json's u-bar: the built-in table, or a recorded, justified override that lowers
    an entry to no less than the best known lower bound."""
    problems = []
    ubar = {int(k): v for k, v in reach["ubar"].items()}
    overrides = reach.get("ubar_override") or {}
    if set(ubar) != set(UBAR_BUILTIN):
        problems.append(f"reach.json u-bar covers {sorted(ubar)}, not {sorted(UBAR_BUILTIN)}")
    for key in overrides:
        if not key.isdigit() or int(key) not in UBAR_BUILTIN:
            problems.append(f"reach.json overrides an unknown u-bar({key})")
    for n, builtin in UBAR_BUILTIN.items():
        o = overrides.get(str(n))
        if o is None:
            if ubar.get(n) != builtin:
                problems.append(f"reach.json u-bar({n}) = {ubar.get(n)} is not the built-in {builtin} and no "
                                f"override is recorded")
        elif (o.get("builtin") != builtin or ubar.get(n) != o.get("value") or
              not isinstance(o.get("value"), int) or not UBAR_LOWER[n] <= o["value"] < builtin):
            problems.append(f"reach.json override of u-bar({n}) {o} is not a lowering of {builtin} to at "
                            f"least the known lower bound {UBAR_LOWER[n]}")
    if overrides and not str(reach.get("ubar_justification") or "").strip():
        problems.append("reach.json overrides u-bar without a justification")
    return problems


def derive(config: dict, summary: dict, reach: dict | None, problems: list[str]) -> dict:
    """(k): what the target prescribes, from the target, seed level, root k and u-bar table alone,
    and the run's own records (run-config.json, run-summary.json, reach.json) checked against it."""
    tn, tm = config["target"]
    seed_n = config["seed_n"]
    if not (nonneg(tn) and nonneg(tm) and tn in UBAR_BUILTIN and tn >= 2):
        raise Bad(f"run-config.json target {config['target']!r} is not a target of the u-bar table")
    # run-dag2.py's range: a seed level at or above the target leaves no level to derive (G5 round 2, finding 2:
    # seed 24 for (23,65) gave 0 required cells and CHAIN OK)
    if not nonneg(seed_n) or not 1 <= seed_n < tn:
        problems.append(f"run-config.json seed level {seed_n!r} is not in 1..{tn - 1} (run-dag2.py's range)")
        seed_n = min(max(seed_n, 1), tn - 1) if nonneg(seed_n) else tn - 1   # derive from a legal seed level
    slice_cfg = config.get("slice")
    if slice_cfg is not None and not (isinstance(slice_cfg, list) and len(slice_cfg) == 3 and
                                      all(nonneg(v) for v in slice_cfg) and slice_cfg[2] >= 1 and
                                      slice_cfg[1] < slice_cfg[2] and seed_n <= slice_cfg[0] < tn):
        problems.append(f"run-config.json slice {slice_cfg!r} is not [level, index, count] with count >= 1, "
                        f"0 <= index < count and seed level <= level < target n")
    if summary.get("target") != [tn, tm] or summary.get("seed_n") != config["seed_n"]:
        problems.append(f"run-summary.json target {summary.get('target')} / seed {summary.get('seed_n')} is not "
                        f"run-config.json's {[tn, tm]} / {seed_n}")
    if summary.get("slice") != config.get("slice"):
        problems.append(f"run-summary.json slice {summary.get('slice')} is not run-config.json's {config.get('slice')}")
    prune_from = config["prune_from"] if config.get("prune") else None
    sp = summary.get("prune") or {}
    if bool(sp.get("enabled")) != bool(config.get("prune")) or sp.get("prune_from") != prune_from:
        problems.append(f"run-summary.json prune {sp} is not run-config.json's (prune {config.get('prune')}, "
                        f"from {prune_from})")
    root_k = None
    if config.get("reach"):
        if reach is None:
            raise Bad("run-config.json says reach but there is no reach.json")
        ubar_problems = check_ubar(reach)
        problems.extend(ubar_problems)
        # the derivation uses reach.json's u-bar only when it is the built-in table or a justified lowering
        ubar = dict(UBAR_BUILTIN) if ubar_problems else {int(k): v for k, v in reach["ubar"].items()}
        root_k = reach["root_k"]
        if reach.get("target") != [tn, tm] or reach.get("seed_n") != seed_n:
            problems.append(f"reach.json target {reach.get('target')} / seed {reach.get('seed_n')} is not the run's "
                            f"{[tn, tm]} / {seed_n}")
        if config.get("reach_root_k") != root_k:
            problems.append(f"reach.json root k {root_k} is not run-config.json's {config.get('reach_root_k')}")
        if (summary.get("reach") or {}).get("root_k") != root_k:
            problems.append(f"run-summary.json root k {(summary.get('reach') or {}).get('root_k')} is not "
                            f"reach.json's {root_k}")
        # the root must be justified: a larger k than proved drops reach levels and graphs that can reach
        # the target (a (16,41) run with root k 5 loses AMP's (16,41) graph, of minimum degree 4)
        schade = max(0, tm - ubar[tn - 1])
        lemma = ROOT_K_LEMMAS.get((tn, tm))
        if not isinstance(root_k, int) or isinstance(root_k, bool) or root_k < 0 or \
                root_k > max(schade, lemma if lemma is not None else 0):
            problems.append(f"reach.json root k {root_k!r} is not justified: Schade's bound is "
                            f"{tm} - u-bar({tn - 1}) = {schade}" + (f", Lemma D4's {lemma}" if lemma is not None else
                                                                   f", and no lemma is recorded for ({tn},{tm})"))
            root_k = max(schade, lemma if lemma is not None else 0)   # derive the cells from the justified root
        if (tn, tm) == (22, 61) and reach.get("root_k") != 5 and "D4" in str(reach.get("root_k_source")):
            problems.append("reach.json claims D4 but root_k is not 5")
    else:
        if reach is not None:
            problems.append("reach.json present but run-config.json does not say reach")
        ubar = dict(UBAR_BUILTIN)
    windows = schade_windows(tn, tm, seed_n, ubar)
    table = recompute_reach(tn, tm, root_k, seed_n, ubar) if config.get("reach") else None
    if table is not None:
        stored = {int(n): {int(m): k for m, k in lv.items()} for n, lv in reach["table"].items()}
        if stored != table:
            problems.append("reach.json table does not follow from the target's root by the L4 recursion")
        if {int(k): tuple(v) for k, v in (reach.get("schade_windows") or {}).items()} != windows:
            problems.append("reach.json schade_windows are not the target's Schade windows")
        for n, level in table.items():
            for m in level:
                if not windows[n][0] <= m <= windows[n][1]:
                    problems.append(f"reach level ({n},{m}) lies outside Schade's window {windows[n]}")
        recorded = (summary.get("reach") or {}).get("levels")
        if recorded != {str(n): sorted(level) for n, level in sorted(table.items())}:
            problems.append("run-summary.json reach levels are not the recomputed table's")
    elif (summary.get("reach") or {}).get("enabled"):
        problems.append("run-summary.json says reach but run-config.json does not")
    if {int(k): tuple(v) for k, v in (summary.get("windows") or {}).items()} != windows:
        problems.append(f"run-summary.json windows {summary.get('windows')} are not the target's Schade windows "
                        f"{ {str(k): list(v) for k, v in sorted(windows.items())} }")
    required = [(n, m) for n in range(seed_n, tn + 1)
                for m in (sorted(table[n]) if table is not None else range(windows[n][0], windows[n][1] + 1))]
    required_set = set(required)
    if (tn, tm) not in required_set:
        problems.append(f"the target cell ({tn},{tm}) is not among the derived cells")
        required.append((tn, tm))
        required_set.add((tn, tm))
    allowed: dict[tuple[int, int], list[int]] = {}
    for n, m in required:
        if n == seed_n:
            continue
        lower = max(ceil_div(m * (n - 2), n), windows[n - 1][0])
        upper = min(ubar[n - 1], m, windows[n - 1][1])
        k = table[n][m] if table is not None else 0
        allowed[(n, m)] = [pm for pm in range(lower, upper + 1) if m - pm >= k]
        for pm in allowed[(n, m)]:
            if (n - 1, pm) not in required_set:
                problems.append(f"({n - 1},{pm}) is an allowed parent of ({n},{m}) but not a required cell")
    # a level entry names its cell with nonnegative integers, or it is a problem and not listed: summary_audit audits
    # only such entries, so an entry written (23, 65.0) counted as listed here (65.0 == 65) and was never audited (G5
    # round 8, hunting the family: the target entry with m 65.0 and one child passed, the target reported empty)
    named = [(l, (l["n"], l["m"]) if isinstance(l, dict) and nonneg(l.get("n")) and nonneg(l.get("m")) else None)
             for l in summary.get("levels", [])]
    malformed = [(l.get("n"), l.get("m")) if isinstance(l, dict) else l for l, cell in named if cell is None]
    if malformed:
        problems.append(f"run-summary.json level entries whose n and m are not nonnegative integers: "
                        f"{str(malformed[:4])[:200]}")
    listed = [cell for _, cell in named if cell is not None and cell[0] >= seed_n]
    counts: dict[tuple, int] = defaultdict(int)
    for cell in listed:
        counts[cell] += 1
    missing = [c for c in required if c not in counts]
    extra = sorted(c for c in counts if c not in required_set)
    twice = sorted(c for c, v in counts.items() if v > 1)
    if missing:
        problems.append(f"{len(missing)} required cell(s) of ({tn},{tm}) not in run-summary.json: "
                        f"{[list(c) for c in missing[:12]]}")
    if extra:
        problems.append(f"run-summary.json lists cells the target does not prescribe: {[list(c) for c in extra[:12]]}")
    if twice:
        problems.append(f"run-summary.json lists cells more than once: {[list(c) for c in twice[:12]]}")
    if summary.get("completed_through_n") != tn:
        problems.append(f"run-summary.json completed_through_n {summary.get('completed_through_n')} is not the "
                        f"target's n {tn}: the run is incomplete")
    return {"target": (tn, tm), "seed_n": seed_n, "ubar": ubar, "windows": windows, "table": table,
            "root_k": root_k, "required": required, "allowed": allowed, "prune_from": prune_from,
            "slice": config.get("slice")}


def verdict(problems: list[str], partial: list[str], exhaustive_line: str) -> int:
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        print(f"CHAIN FAIL ({len(problems)} problems)")
        return 1
    if partial:
        print("COVERAGE partial: " + "; ".join(partial))
        print("CHAIN PARTIAL (" + "; ".join(partial) + ")")
        return 3
    print(exhaustive_line)
    print("CHAIN OK")
    return 0


def main_run(a: argparse.Namespace) -> int:
    run = a.run[0].resolve()
    config = json.loads((run / "run-config.json").read_text())
    summary = json.loads((run / "run-summary.json").read_text())
    reach = json.loads((run / "reach.json").read_text()) if (run / "reach.json").is_file() else None
    problems: list[str] = []
    check_pins(config, a.pins, problems)
    d = derive(config, summary, reach, problems)
    tn, tm = d["target"]
    seed_n, table, windows, ubar = d["seed_n"], d["table"], d["windows"], d["ubar"]
    required, allowed, prune_from = d["required"], d["allowed"], d["prune_from"]
    checked = {"required_cells": len(required), "reach_files": 0, "keep_files": 0, "parent_files": 0,
               "shards": 0, "certs_replayed": 0}
    # (f) the forbidden set: its pinned file must be hashed by every manifest of the run
    forbidden_set = config.get("forbidden_set", 74)
    forbidden_hash = FORBIDDEN_SHA256.get(forbidden_set)
    if forbidden_hash is None:
        problems.append(f"run-config.json names an unknown forbidden set {forbidden_set}")
    checker = ROOT / "check" / ("udcheck.py" if forbidden_set == 74 else "udcheck398.py")
    verify_stages = bool(config.get("verify_stages"))
    tu_target_ok = tn in PROVED_UPPER and tm >= PROVED_UPPER[tn]
    # run-dag2.py --prune-filter-set 74 in a set-398 run: the prune step re-checks only the 74, so the
    # stage verification must be on (it is then the only re-check of the 324; PRUNING.md 5.6)
    filter_set = config.get("prune_filter_set")
    if filter_set is not None:
        checked["prune_filter_set"] = filter_set
        if not config.get("verify_stages"):
            problems.append(f"run-config.json: prune_filter_set {filter_set} without verify_stages")
    rules = [flag for flag in RULE_WITNESS if config.get(flag) is True]
    if len(rules) > 1:
        problems.append(f"run-config.json records more than one linear rule: {rules}")
    allowed_witness = {RULE_WITNESS[flag] for flag in rules}
    witness_flag = {key: flag for flag, key in RULE_WITNESS.items()}
    if forbidden_set != 74:
        checked["forbidden_set"] = forbidden_set
    if rules:
        checked["rules"] = rules
        checker = a.udcheck_rhombus.resolve()

    def rules_recorded(info: dict, what: str) -> None:
        for flag in RULE_WITNESS:
            if (info.get(flag) is True) != (flag in rules):
                problems.append(f"{what}: {flag} setting {info.get(flag)} is not the run's {flag in rules}")
    if verify_stages:
        checked["verify_manifests"] = 0

    def names_forbidden(info: dict, what: str) -> None:
        inputs = info.get("inputs_sha256")
        if not isinstance(inputs, dict) or forbidden_hash not in inputs.values():
            problems.append(f"{what}: does not hash the set-{forbidden_set} forbidden file")
        if forbidden_set != 74 and info.get("forbidden_set", forbidden_set) != forbidden_set:
            problems.append(f"{what}: records forbidden set {info.get('forbidden_set')}")

    def stage(n: int, m: int) -> tuple[Path, str]:
        if prune_from is not None and n >= prune_from:
            return run / f"{n}-{m}.keep.g6", "keep"
        if table is not None:
            return run / f"{n}-{m}.reach.g6", "reach"
        return run / f"{n}-{m}.g6", "full"

    # (h) a sliced run (run-dag2.py --slice-level L): at level L the file that serves as a parent
    # is the slice of the stage file, i.e. its records whose sha256 (first 8 bytes, big-endian)
    # is the slice index mod the slice count, in order; recomputed here from the rule
    slice_cfg = config.get("slice")

    def parent_stage(n: int, m: int) -> tuple[Path, str]:
        path, kind = stage(n, m)
        if slice_cfg and n == slice_cfg[0]:
            i, count = slice_cfg[1], slice_cfg[2]
            return run / f"{n}-{m}.slice-{i}-of-{count}.g6", f"{kind}+slice"
        return path, kind

    if slice_cfg:
        checked["slice_files"] = 0
        level, i, count = slice_cfg
        for s_n, s_m in [c for c in required if c[0] == level]:
            try:
                source, _ = stage(s_n, s_m)
                sliced, _ = parent_stage(s_n, s_m)
                want = [c for c in lines(source)
                        if int.from_bytes(hashlib.sha256(c.encode("ascii")).digest()[:8], "big") % count == i]
                if not sliced.is_file() or lines(sliced) != want:
                    problems.append(f"{sliced.name}: is not the records of {source.name} in slice {i} of {count}")
            except (Bad, OSError, KeyError, ValueError) as error:
                problems.append(f"slice file of ({s_n},{s_m}): {error!r}")
            checked["slice_files"] += 1

    first = max(a.from_n, seed_n)
    inspected = [c for c in required if c[0] >= first]
    for n, m in required:
        if n >= first:
            continue
        # below --from-n only presence: the level file and its stage file exist
        for path in (run / f"{n}-{m}.g6", stage(n, m)[0]):
            if not path.is_file():
                problems.append(f"required cell ({n},{m}): {path.name} is missing")
    for n, m in inspected:
        try:
            inspect_cell(run, n, m, d, a, checker, rules, allowed_witness, witness_flag, forbidden_set, forbidden_hash,
                         filter_set, verify_stages, tu_target_ok, stage, parent_stage, names_forbidden, rules_recorded,
                         problems, checked)
        except (Bad, OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            problems.append(f"required cell ({n},{m}) could not be checked: {error!r}")
    pruned = [c for c in inspected if prune_from is not None and c[0] >= prune_from]
    if a.check and checked["certs_replayed"] != len(pruned):
        problems.append(f"{checked['certs_replayed']} certificate files replayed, {len(pruned)} pruned cells inspected")
    partial = []
    if first > seed_n:
        partial.append(f"levels below {first} not inspected (--from-n {a.from_n})")
    if pruned and not a.check:
        partial.append(f"the certificates of {len(pruned)} pruned cells not replayed (no --check)")
    coverage = "partial" if partial else "exhaustive"
    pinned = {k: v for k, v in a.pins.items() if v is not None}
    print(json.dumps({"run": str(run), "target": [tn, tm], "seed_n": config.get("seed_n"),
                      "levels_inspected": len(inspected), "pruned_cells_inspected": len(pruned), **checked,
                      "coverage": coverage, "pinned": pinned, **({"slice": slice_cfg} if slice_cfg else {})}))
    where = (f" (slice {slice_cfg[1]} of {slice_cfg[2]} at level {slice_cfg[0]}: the fleet needs all "
             f"{slice_cfg[2]} slices)" if slice_cfg else "")
    unpinned = [name for name in ("target", "seed") if name not in pinned]
    return verdict(problems, partial,
                   f"COVERAGE exhaustive: all {len(required)} required cells of ({tn},{tm}) from seed level "
                   f"{seed_n} present and checked, their parent sources exactly as L4 allows, the certificates of "
                   f"all {len(pruned)} pruned cells replayed{where}"
                   + (f"; {' and '.join(unpinned)} as the run's files state them (pin with --expect-target, "
                      f"--expect-seed)" if unpinned else ""))


def inspect_cell(run, n, m, d, a, checker, rules, allowed_witness, witness_flag, forbidden_set, forbidden_hash,
                 filter_set, verify_stages, tu_target_ok, stage, parent_stage, names_forbidden, rules_recorded,
                 problems, checked) -> None:
    tn, tm = d["target"]
    seed_n, table, prune_from = d["seed_n"], d["table"], d["prune_from"]
    full = run / f"{n}-{m}.g6"
    codes = lines(full)
    for code in codes:
        vn, vm, _ = graph6(code)
        if (vn, vm) != (n, m):
            problems.append(f"{full.name}: graph {code} is ({vn},{vm})")
            break
    # (c) reach file
    if table is not None:
        k = table[n][m]
        reach_file = run / f"{n}-{m}.reach.g6"
        expected = [c for c in codes if graph6(c)[2] >= k]
        if lines(reach_file) != expected:
            problems.append(f"{reach_file.name}: is not the level file minus minimum degree < {k}")
        rm = json.loads((run / f"{n}-{m}.reach.manifest.json").read_text())
        if rm.get("k") != k or rm.get("output_sha256") != sha256(reach_file) or rm.get("input_sha256") != sha256(full):
            problems.append(f"{reach_file.name}: reach manifest hashes or k do not match")
        checked["reach_files"] += 1
    # (b) keep file
    if prune_from is not None and n >= prune_from:
        source = run / (f"{n}-{m}.reach.g6" if table is not None else f"{n}-{m}.g6")
        certs = run / f"{n}-{m}.certs.jsonl"
        keep = run / f"{n}-{m}.keep.g6"
        unknown = run / f"{n}-{m}.UNKNOWN.g6"
        records = [json.loads(l) for l in lines(certs)]
        if [r["g6"] for r in records] != lines(source):
            problems.append(f"{certs.name}: record list is not the stage input {source.name}")
        if lines(keep) != [r["g6"] for r in records if r["verdict"] in ("embedded", "unknown")]:
            problems.append(f"{keep.name}: is not the embedded and unknown records in order")
        if lines(unknown) != [r["g6"] for r in records if r["verdict"] == "unknown"]:
            problems.append(f"{unknown.name}: is not the unknown records in order")
        for r in records:
            if r["verdict"] in ("tu", "refuted") and not isinstance(r.get("witness"), dict):
                problems.append(f"{certs.name}: pruned graph {r['g6']} has no witness")
                break
            if r["verdict"] not in ("tu", "refuted", "embedded", "unknown"):
                problems.append(f"{certs.name}: verdict {r['verdict']} for {r['g6']}")
                break
        # a linear rule's witness in a run whose manifests do not record that rule: refused
        foreign = [(r["g6"], key) for r in records if isinstance(r.get("witness"), dict)
                   for key in r["witness"] if key in witness_flag and key not in allowed_witness]
        if foreign:
            g6, key = foreign[0]
            problems.append(f"{certs.name}: {len(foreign)} record(s) carry a {key!r} witness (first {g6}) but the "
                            f"run's manifests do not record --{witness_flag[key]}: refused")
        pm = json.loads((run / f"{n}-{m}.prune.manifest.json").read_text())
        if pm.get("exit_status") != 0 or any(pm.get("mutation", {}).values()):
            problems.append(f"{n}-{m}: prune manifest is not a clean success")
        names_forbidden(pm, f"{n}-{m}.prune.manifest.json")
        if forbidden_set != 74 and pm.get("forbidden_set") != forbidden_set:
            problems.append(f"{n}-{m}.prune.manifest.json: does not say forbidden_set {forbidden_set}")
        rules_recorded(pm, f"{n}-{m}.prune.manifest.json")
        if pm.get("filter_set") != filter_set:
            problems.append(f"{n}-{m}.prune.manifest.json: filter set {pm.get('filter_set')} is not the run's "
                            f"{filter_set}")
        if pm.get("target") != [tn, tm]:
            problems.append(f"{n}-{m}.prune.manifest.json: target {pm.get('target')} is not the run's {[tn, tm]}")
        if not tu_target_ok:
            problems.append(f"{n}-{m}.prune.manifest.json: tu records prune only at a target (N, M) with "
                            f"M >= u(N) proved; ({tn},{tm}) is below the proved bound {PROVED_UPPER.get(tn)}")
        for path in (certs, keep, unknown):
            if pm.get("outputs_sha256", {}).get(str(path)) != sha256(path):
                problems.append(f"{path.name}: hash differs from the prune manifest")
        if pm.get("inputs_sha256", {}).get(str(source)) != sha256(source):
            problems.append(f"{source.name}: hash differs from the prune manifest input")
        checked["keep_files"] += 1
        if a.check:
            cmd = [str(PYTHON), str(checker), "--expect-n", str(n), "--expect-m", str(m),
                   "--graphs", str(source), "--unknown-file", str(unknown), str(certs)]
            if rules:
                cmd[-1:-1] = ["--data-dir", str(ROOT / "data"), "--forbidden-set", str(forbidden_set)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 or not res.stdout.startswith("ACCEPT certificates"):
                problems.append(f"{certs.name}: udcheck did not accept: {res.stderr.strip()[:200]}")
            checked["certs_replayed"] += 1
    # (f) the stage verification of this level
    if verify_stages:
        path, _ = stage(n, m)
        vpath = run / f"{n}-{m}.verify.manifest.json"
        if not vpath.is_file():
            problems.append(f"{n}-{m}: no stage verification manifest")
        else:
            vm = json.loads(vpath.read_text())
            records = len(lines(path))
            parts = vm.get("parts") or []
            ranges = [tuple(p.get("range", ())) for p in parts]
            tiled = (bool(ranges) and ranges[0][0] == 0 and ranges[-1][1] == records and
                     all(ranges[i][1] == ranges[i + 1][0] for i in range(len(ranges) - 1)) and
                     all((p.get("udenum_stats") or {}).get("parents_seen") == hi - lo and
                         (p.get("udenum_stats") or {}).get("children_written") == 0
                         for p, (lo, hi) in zip(parts, ranges)))
            if (vm.get("exit_status") != 0 or vm.get("forbidden_set") != forbidden_set or
                    vm.get("forbidden_sha256") != forbidden_hash or
                    vm.get("stage_sha256") != sha256(path) or vm.get("records") != records or not tiled):
                problems.append(f"{n}-{m}: stage verification manifest does not cover the current stage file "
                                f"{path.name} in set {forbidden_set}")
            checked["verify_manifests"] += 1
    if n == seed_n:
        sm = json.loads((run / f"{n}-{m}.manifest.json").read_text())
        names_forbidden(sm, f"{n}-{m}.manifest.json")
        if sm.get("exit_status") != 0 or sm.get("children_file_sha256") != sha256(full):
            problems.append(f"{n}-{m}.manifest.json: the seed level is not a clean success for {full.name}")
    # (d) parent file of this level and (e) shards
    if n > seed_n:
        am = json.loads((run / f"{n}-{m}.manifest.json").read_text())
        if am.get("exit_status") != 0:
            problems.append(f"{n}-{m}.manifest.json: the level is not a clean success")
        names_forbidden(am, f"{n}-{m}.manifest.json")
        rules_recorded(am.get("pruning") or {}, f"{n}-{m}.manifest.json pruning")
        if (am.get("pruning") or {}).get("filter_set") != filter_set:
            problems.append(f"{n}-{m}.manifest.json: pruning filter_set {(am.get('pruning') or {}).get('filter_set')} "
                            f"is not the run's {filter_set}")
        if forbidden_set != 74 and am.get("forbidden_set") != forbidden_set:
            problems.append(f"{n}-{m}.manifest.json: does not say forbidden_set {forbidden_set}")
        parent_file = Path(am["parent_file"])
        allowed = d["allowed"][(n, m)]
        listed = am.get("parent_sources")
        if listed is None:
            problems.append(f"{n}-{m}: aggregate manifest lists no parent_sources")
            return
        if [s["level"][1] for s in listed] != allowed or any(s["level"][0] != n - 1 for s in listed):
            problems.append(f"{n}-{m}: listed parent levels {[s['level'] for s in listed]} are not the allowed "
                            f"{[[n - 1, pm_] for pm_ in allowed]} (L4 from the target)")
        blob = b""
        for s in listed:
            path, kind = parent_stage(n - 1, s["level"][1])
            if Path(s["file"]) != path or s["kind"] != kind:
                problems.append(f"{n}-{m}: parent source {s['file']} ({s['kind']}) is not the stage file {path} ({kind})")
            if not path.is_file() or sha256(path) != s["sha256"]:
                problems.append(f"{n}-{m}: parent source {path.name} hash differs from the manifest")
                continue
            blob += path.read_bytes()
        if not parent_file.is_file() or hashlib.sha256(blob).hexdigest() != sha256(parent_file):
            problems.append(f"{n}-{m}: {parent_file.name} is not the concatenation of the listed sources")
        if am["inputs_sha256"].get(str(parent_file)) != sha256(parent_file):
            problems.append(f"{n}-{m}: aggregate manifest does not hash its parent file")
        if am.get("children_file_sha256") != sha256(full):
            problems.append(f"{n}-{m}: aggregate manifest does not hash its level file")
        if table is not None and am.get("reach", {}).get("reach_json_sha256") != sha256(run / "reach.json"):
            problems.append(f"{n}-{m}: aggregate manifest does not hash reach.json")
        count = len(lines(parent_file))
        ranges = []
        for sm in sorted((run / "shards" / f"{n}-{m}").glob("*.manifest.json")):
            info = json.loads(sm.read_text())
            if info.get("exit_status") != 0 or Path(info["parent_file"]) != parent_file:
                problems.append(f"{sm.name}: bad status or parent file")
            if info["inputs_sha256"].get(str(parent_file)) != sha256(parent_file):
                problems.append(f"{sm.name}: does not hash the parent file")
            names_forbidden(info, sm.name)
            if table is not None and info["software_sha256"].get("reach.json") != sha256(run / "reach.json"):
                problems.append(f"{sm.name}: does not hash reach.json")
            ranges.append(tuple(info["parent_range"]))
            checked["shards"] += 1
        ranges.sort()
        if count and (not ranges or ranges[0][0] != 0 or ranges[-1][1] != count or
                      any(ranges[i][1] != ranges[i + 1][0] for i in range(len(ranges) - 1))):
            problems.append(f"{n}-{m}: shard ranges {ranges} do not tile the parent file of {count} records")
        checked["parent_files"] += 1


# ---------------------------------------------------------------- --summary-only
def read_json(path: Path):
    return json.loads(path.read_text())


def g4_verdict(fp: dict, sm: dict, slice_cfg, d: dict, evidence: dict, shares: dict) -> tuple[str, list[str]]:
    """The verdict a slice's G4 replay evidence supports (the runbook's rule, coordination/cloud-workers/
    u23-slice.sh g4_replay), from replay/summary.json and the replay's exit status in replay/fingerprint.json,
    independently of the label the runbook wrote.

    First every aggregate the verdict reads is recomputed from the detailed records it summarises
    (enum2/replay-398.py summarize() and main()): sampled, processed, production and enum2 children and mismatches
    summed over per_cell, per_level the per-cell sums of its level, stages_checked and stages_ok from stages, red_all
    from red_controls, all_identical from those; an aggregate that disagrees with its details is a FAIL (G5 round 4:
    a mismatch in per_cell, or a red control that did not go red, under clean aggregates). Then: FAIL on any
    mismatch, unreplayable cell, stage file that does not re-derive, seed level that differs, (full mode) a red
    control that did not go red or no seed level recomputed. EMPTY is decided before the positive-sample
    requirement, from verified emptiness: a slice-mode replay that exited nonzero having sampled nothing, with no
    per-cell record, its stage checks all passed, of a slice whose every cell above the slice level has no parent
    and whose every share is 0 (all_identical is false there by the producer's definition, bool(entries)). The
    parents are read from `evidence`, the parent record summary_audit accepted for each cell (the final entry, or
    for a resumed cell the pushed earlier version it was recovered from): a cell without one is unconfirmed, and a
    record with parents makes the slice not empty. PASS: exit
    0, parents sampled, all_identical. Anything else FAIL."""
    if not sm:
        return "FAIL", ["no replay/summary.json"]
    reasons: list[str] = []
    mode = fp.get("mode")
    if mode not in ("full", "slice"):
        reasons.append(f"mode {mode!r}")

    def listed(key: str) -> list | None:
        return sm.get(key) if isinstance(sm.get(key), list) else None
    per_cell, per_level, stages, seeds = listed("per_cell"), listed("per_level"), listed("stages"), listed("seeds")
    reds = listed("red_controls")
    keys = ("sampled", "processed", "production_children", "enum2_children", "mismatches")
    if per_cell is None or per_level is None or stages is None or seeds is None:
        return "FAIL", [f"missing detail records: per_cell {per_cell is not None}, per_level {per_level is not None}, "
                        f"stages {stages is not None}, seeds {seeds is not None}"]
    bad_rows = [r for r in per_cell if not (isinstance(r, dict) and all(nonneg(r.get(k)) for k in keys) and
                                            nonneg(r.get("n")))]
    if bad_rows:
        return "FAIL", [f"per_cell rows that are not counts: {str(bad_rows[:2])[:200]}"]
    for r in per_cell:
        if r["processed"] > r["sampled"] or r["mismatches"] > r["sampled"] or \
                (r["mismatches"] == 0 and r["production_children"] != r["enum2_children"]):
            reasons.append(f"per_cell {r.get('cell')}: sampled {r['sampled']}, processed {r['processed']}, children "
                           f"{r['production_children']} / {r['enum2_children']}, mismatches {r['mismatches']}")
    # the aggregates, recomputed from the details
    derived = {"sampled_parents": sum(r["sampled"] for r in per_cell),
               "processed_parents": sum(r["processed"] for r in per_cell),
               "production_children_compared": sum(r["production_children"] for r in per_cell),
               "enum2_children_compared": sum(r["enum2_children"] for r in per_cell),
               "mismatching_parents": sum(r["mismatches"] for r in per_cell),
               "stages_checked": len(stages),
               "stages_ok": all(isinstance(st, dict) and st.get("ok") is True for st in stages)}
    for key, value in derived.items():
        if sm.get(key) != value:
            reasons.append(f"aggregate {key} {sm.get(key)!r} is not the {value!r} its details give")
    levels: dict = {}
    for r in per_cell:   # LOCAL BY DESIGN: per_level against per_cell is the replay summary's own consistency
        lv = levels.setdefault(r["n"], {"cells": 0, "parents": 0, **{k: 0 for k in keys}})
        lv["cells"] += 1
        lv["parents"] += r.get("parents_in_cell") or 0
        for k in keys:
            lv[k] += r[k]
    recorded_levels = {lv.get("n"): lv for lv in per_level if isinstance(lv, dict)}
    if set(recorded_levels) != set(levels) or len(recorded_levels) != len(per_level) or \
            any(recorded_levels[n].get(k) != v for n, lv in levels.items() for k, v in lv.items()):
        reasons.append("per_level is not the per-level sums of per_cell")
    seed_ok = all(isinstance(s, dict) and s.get("identical") is True for s in seeds)
    if not seed_ok:
        reasons.append("seed levels that differ: " + ", ".join(str(s.get("cell")) for s in seeds
                                                              if not (isinstance(s, dict) and s.get("identical") is True)))
    unreplayable = sm.get("unreplayable_cells")
    if unreplayable:
        reasons.append(f"{len(unreplayable)} unreplayable cells")
    if derived["mismatching_parents"]:
        reasons.append(f"{derived['mismatching_parents']} mismatching parents in per_cell")
    if not stages or not derived["stages_ok"]:
        reasons.append("no stage file checked" if not stages else "stage files that do not re-derive")
    if mode == "full":
        red_all = bool(reds) and all(isinstance(r, dict) and r.get("went_red") is True for r in reds)
        if sm.get("red_all") != red_all:
            reasons.append(f"aggregate red_all {sm.get('red_all')!r} is not the {red_all} its red controls give")
        if not red_all:
            reasons.append("red controls that did not go red: " + ", ".join(
                str(r.get("id")) for r in (reds or []) if not (isinstance(r, dict) and r.get("went_red") is True)))
        if not seeds:
            reasons.append("a full replay that recomputed no seed level")
    elif reds:
        reasons.append("red controls in a slice-mode replay")
    all_identical = (derived["sampled_parents"] > 0 and derived["mismatching_parents"] == 0 and not unreplayable
                     and seed_ok and derived["stages_ok"])
    if sm.get("all_identical") != all_identical:
        reasons.append(f"aggregate all_identical {sm.get('all_identical')!r} is not the {all_identical} its details give")
    for key in ("sampled_parents", "production_children_compared", "mismatching_parents", "stages_checked", "red_all"):
        if key in fp and fp[key] != sm.get(key):
            reasons.append(f"the fingerprint's {key} {fp[key]!r} is not the summary's {sm.get(key)!r}")
    if reasons:
        return "FAIL", reasons
    code = fp.get("replay_exit")
    # EMPTY first, from verified emptiness (independent of all_identical, false by definition when nothing is sampled)
    if mode == "slice" and isinstance(code, int) and not isinstance(code, bool) and code != 0 and \
            derived["sampled_parents"] == 0 and not per_cell:
        level = slice_cfg[0] if slice_cfg else None
        above = [c for c in d["required"] if level is not None and c[0] > level]
        # the parent records summary_audit accepted (fresh, or recovered from a pushed earlier version): a cell without
        # one (resumed and not recovered) is unconfirmed, a cell whose record has parents is not empty. LOCAL BY
        # DESIGN, and only to REFUTE: a record with parents, or a share, contradicts EMPTY whatever other copies say;
        # EMPTY itself is confirmed in the fleet pass from the records of every copy
        unconfirmed = [c for c in above if c not in evidence]
        with_parents = [c for c in above if c in evidence and evidence[c].get("parents") != 0]
        if level is not None and above and not with_parents and all(v == 0 for v in shares.values()):
            if not unconfirmed:
                return "EMPTY", []
            # only unconfirmed cells stand in the way: PENDING, decided with the fleet once the parent records of every
            # copy of the slice are merged (G5 round 6: complementary copies of an empty slice were refused)
            return "PENDING", [f"unconfirmed {[list(c) for c in unconfirmed]}"]
        return "FAIL", [f"an empty replay (exit {code}, nothing sampled) of a slice that is not shown empty: cells with "
                        f"parents {[list(c) for c in with_parents[:4]]}, shares "
                        f"{ {pm: v for pm, v in list(shares.items())[:4]} }, unconfirmed {[list(c) for c in unconfirmed[:4]]}"]
    if code == 0 and derived["sampled_parents"] > 0 and all_identical:
        return "PASS", []
    return "FAIL", [f"replay exit {code!r} with {derived['sampled_parents']} parents sampled ({mode} mode), "
                    f"all_identical {all_identical}"]


def summary_audit(run: Path, a: argparse.Namespace, problems: list[str], unresolved: list[str]) -> dict:
    """One run from its pushed files: the pins, (k), each summary entry against the derivation (every count a
    nonnegative integer; parents as L4 allows; sums and tilings), hashes.json bound to the summary's counts, and
    the G4 replay's verdict bound to this slice and to the slice-level shares its summary records."""
    config = read_json(run / "run-config.json")
    summary = read_json(run / "run-summary.json")
    reach = read_json(run / "reach.json") if (run / "reach.json").is_file() else None
    local: list[str] = []
    local_unresolved: list[str] = []
    check_pins(config, a.pins, local)
    d = derive(config, summary, reach, local)
    table, prune_from, seed_n = d["table"], d["prune_from"], d["seed_n"]
    raw_slice = config.get("slice")
    slice_cfg = raw_slice if (isinstance(raw_slice, list) and len(raw_slice) == 3 and all(nonneg(v) for v in raw_slice)
                              and raw_slice[2] >= 1 and raw_slice[1] < raw_slice[2]) else None
    entries = {(l["n"], l["m"]): l for l in summary.get("levels", [])
               if isinstance(l, dict) and nonneg(l.get("n")) and nonneg(l.get("m"))}
    # Earlier pushed versions of this run-summary.json (history/INDEX.json lists them newest first): a cell the
    # final summary lists as resumed was made by an earlier invocation, whose summary recorded its parents. Such
    # a record is used only when its counts (children, reach kept, prune kept) equal the final entry's.
    history = []
    index = run / "history" / "INDEX.json"
    if index.is_file():
        for commit in read_json(index)["commits"]:
            old = read_json(run / "history" / f"{commit}.json")
            history.append((commit, {(l["n"], l["m"]): l for l in old.get("levels", [])
                                     if isinstance(l, dict) and nonneg(l.get("n")) and nonneg(l.get("m"))}))

    def counts_key(e: dict) -> tuple:
        return (e.get("children"), (e.get("reach") or {}).get("kept"),
                ((e.get("prune") or {}).get("counts") or {}).get("kept"))

    def recover(cell: tuple, e: dict) -> tuple[str, dict] | None:
        for commit, old in history:
            o = old.get(cell)
            if o is not None and not o.get("resumed") and counts_key(o) == counts_key(e):
                return commit, o
        return None

    def stage_count(n: int, m: int) -> int | None:
        e = entries.get((n, m))
        if e is None:
            return None
        if prune_from is not None and n >= prune_from:
            value = ((e.get("prune") or {}).get("counts") or {}).get("kept")
        elif table is not None:
            value = (e.get("reach") or {}).get("kept")
        else:
            value = e.get("children")
        return value if nonneg(value) else None

    def counts_ok(where: str, pairs: list[tuple[str, object]]) -> bool:
        bad = [(name, value) for name, value in pairs if not nonneg(value)]
        if bad:
            local.append(f"{where}: counts that are not nonnegative integers: {bad}")
        return not bad

    recovered: dict[str, int] = defaultdict(int)
    fresh_cells: set = set()
    resumed_cells: set = set()             # resumed, and no pushed version of this summary records their parents
    # the parent record each cell's checks accepted: the final entry, or for a resumed cell the pushed earlier version
    # it was recovered from (the G4 EMPTY decision reads these, not the final entries; G5 round 5)
    parent_evidence: dict[tuple, dict] = {}
    shares: dict[int, int] = {}            # this slice's records of each slice-level parent cell
    for n, m in d["required"]:
        e = entries.get((n, m))
        if e is None:
            continue   # a missing cell is already a problem
        where = f"({n},{m})"
        counts_ok(where, [("children", e.get("children"))])
        if table is not None:
            r = e.get("reach") if isinstance(e.get("reach"), dict) else {}
            if r.get("k") != table[n][m] or not counts_ok(where + " reach", [("kept", r.get("kept"))]):
                local.append(f"{where}: reach entry {r} does not apply k = {table[n][m]}")
            elif not r.get("resumed"):
                if counts_ok(where + " reach", [("input", r.get("input")), ("dropped", r.get("dropped"))]) and \
                        (r["input"] != e.get("children") or r["kept"] + r["dropped"] != r["input"]):
                    local.append(f"{where}: reach counts {r} do not add up to the {e.get('children')} children")
            elif nonneg(e.get("children")) and r["kept"] > e["children"]:
                local.append(f"{where}: reach keeps {r['kept']} of {e['children']} children")
        if prune_from is not None and n >= prune_from:
            c = (e.get("prune") or {}).get("counts")
            stage_in = (e.get("reach") or {}).get("kept") if table is not None else e.get("children")
            if not isinstance(c, dict):
                local.append(f"{where}: a pruned cell without a prune record")
            elif counts_ok(where + " prune", [(k, c.get(k)) for k in ("input", "kept", "pruned", "unknown")]):
                if c["input"] != stage_in or c["kept"] + c["pruned"] != c["input"] or c["unknown"] > c["kept"]:
                    local.append(f"{where}: prune counts {c} do not partition the stage input of {stage_in}")
        if n == seed_n or (n, m) not in d["allowed"]:
            continue
        if e.get("resumed"):
            found = recover((n, m), e)
            if found is None:
                resumed_cells.add((n, m))
                continue
            recovered[found[0]] += 1
            e = found[1]
            where += f" (recorded by {found[0][:10]})"
        fresh_cells.add((n, m))
        allowed = d["allowed"][(n, m)]
        sources = e.get("parent_sources") if isinstance(e.get("parent_sources"), list) else []
        levels_read = [s.get("level") if isinstance(s, dict) else None for s in sources]
        # equal AND integers (G5 round 8, the family): a source level [12, 20.0] equalled [12, 20], and its float
        # became the share's key and the slice file's name, so the G4 record of that file was never compared
        if e.get("parent_edge_counts") != allowed or levels_read != [[n - 1, pm] for pm in allowed] or \
                not all(nonneg(v) for v in e["parent_edge_counts"] + [x for lv in levels_read for x in lv]):
            local.append(f"{where}: recorded parents {e.get('parent_edge_counts')} / "
                         f"{[s.get('level') if isinstance(s, dict) else s for s in sources]} are not the allowed "
                         f"{allowed} (L4 from the target)")
            continue
        if table is not None and e.get("reach_k") != table[n][m]:
            local.append(f"{where}: reach_k {e.get('reach_k')} is not {table[n][m]}")
        # LOCAL BY DESIGN: a record is validated (domains, its sources' sum, shards, kinds, stage counts) before it
        # becomes evidence; the bindings that USE evidence run in the fleet pass against every copy's records
        if not counts_ok(where, [("parents", e.get("parents"))] +
                         [(f"records of {s['level']}", s.get("records")) for s in sources]):
            continue
        if e["parents"] != sum(s["records"] for s in sources):
            local.append(f"{where}: parents {e['parents']} is not the sum of its sources' records")
        else:
            parent_evidence[(n, m)] = e
        shards = e.get("shards") if isinstance(e.get("shards"), list) else []
        ranges = [tuple(s.get("range", ())) if isinstance(s, dict) else () for s in shards]
        if not ranges or any(len(r) != 2 or not nonneg(r[0]) or not nonneg(r[1]) or r[0] > r[1] for r in ranges) or \
                not counts_ok(where + " shards", [("children", s.get("children")) for s in shards]):
            local.append(f"{where}: shards {ranges} are not ranges of nonnegative integers with children")
        else:
            ranges.sort()
            if ranges[0][0] != 0 or ranges[-1][1] != e["parents"] or \
                    any(ranges[i][1] != ranges[i + 1][0] for i in range(len(ranges) - 1)) or \
                    sum(s["children"] for s in shards) != e.get("children"):
                local.append(f"{where}: shards {ranges} do not tile the {e['parents']} parents into its "
                             f"{e.get('children')} children")
        for s in sources:
            pn, pm = s["level"]
            expect_kind = ("keep" if prune_from is not None and pn >= prune_from else
                           "reach" if table is not None else "full")
            whole = stage_count(pn, pm)
            if slice_cfg and pn == slice_cfg[0]:
                expect_kind += "+slice"
                # collected here, merged over the slice's copies (with conflicts) and bound in the fleet pass; the
                # comparison with this summary's own stage count below is LOCAL BY DESIGN (the prefix counts are the
                # same in every slice, checked there)
                previous = shares.setdefault(pm, s["records"])
                if previous != s["records"]:
                    local.append(f"{where}: its slice of ({pn},{pm}) is recorded with {s['records']} and {previous} records")
                if whole is None or s["records"] > whole:
                    local.append(f"{where}: its slice of ({pn},{pm}) holds {s['records']} records, the stage file "
                                 f"{whole}")
            elif s["records"] != whole:
                local.append(f"{where}: parent ({pn},{pm}) recorded with {s['records']} records, its stage count in "
                             f"the summary is {whole}")
            if s.get("kind") != expect_kind:
                local.append(f"{where}: parent ({pn},{pm}) kind {s.get('kind')} is not {expect_kind}")
    # cells above the slice level are this slice's own (another copy of the slice may record them: judged with the
    # fleet); the prefix is shared by the whole fleet and judged there; an unsliced run's are unresolved here
    if not slice_cfg and resumed_cells:
        local_unresolved.append(f"{len(resumed_cells)} resumed cells record no parent choice in the summary or its "
                                f"pushed history (levels {levels_of(resumed_cells)})")
    # hashes.json (the runbook's): the prefix's files, bound to this summary's counts
    files = None
    if (run / "hashes.json").is_file():
        h = read_json(run / "hashes.json")
        files = h.get("files") if isinstance(h.get("files"), dict) else {}
        if h.get("slice") != raw_slice:
            local.append(f"hashes.json slice {h.get('slice')} is not run-config.json's {raw_slice}")
        for name, v in files.items():
            if not (isinstance(v, dict) and isinstance(v.get("sha256"), str) and len(v["sha256"]) == 64 and
                    nonneg(v.get("records"))):
                local.append(f"hashes.json {name}: {v} is not a sha256 and a record count")
        stage_names = {".g6": lambda e: e.get("children"),
                       ".reach.g6": lambda e: (e.get("reach") or {}).get("kept"),
                       ".keep.g6": lambda e: ((e.get("prune") or {}).get("counts") or {}).get("kept"),
                       ".UNKNOWN.g6": lambda e: ((e.get("prune") or {}).get("counts") or {}).get("unknown")}
        for (n, m), e in entries.items():
            for suffix, value in stage_names.items():
                v = files.get(f"{n}-{m}{suffix}")
                if isinstance(v, dict) and v.get("records") != value(e):
                    local.append(f"hashes.json {n}-{m}{suffix} holds {v.get('records')} records, the summary says "
                                 f"{value(e)}")
        if slice_cfg:
            for n, m in d["required"]:
                if n > slice_cfg[0]:
                    continue
                wanted = [".g6"] + ([".reach.g6"] if table is not None else []) + \
                    ([".keep.g6", ".UNKNOWN.g6"] if prune_from is not None and n >= prune_from else [])
                absent = [s for s in wanted if f"{n}-{m}{s}" not in files]
                if absent:
                    local.append(f"hashes.json does not hash the prefix cell ({n},{m}) files {absent}")
    elif "hashes" in a.require:
        local.append("no hashes.json")
    # the G4 replay (the runbook's replay/fingerprint.json and replay/summary.json): its verdict, bound to this slice
    # and to the slice-level shares the summary records
    g4 = None
    fp_path, sm_path = run / "replay" / "fingerprint.json", run / "replay" / "summary.json"
    if fp_path.is_file() or sm_path.is_file():
        fp = read_json(fp_path) if fp_path.is_file() else {}
        sm = read_json(sm_path) if sm_path.is_file() else {}
        tag = f"s{slice_cfg[1]}of{slice_cfg[2]}" if slice_cfg else None
        if tag and fp.get("slice") != tag:
            local.append(f"G4 fingerprint names slice {fp.get('slice')}, not {tag}")
        # the verdict is derived here from the replay's own evidence (the runbook's rule), and the label must be it:
        # PASS = nothing wrong and the replay exited 0 having sampled parents; EMPTY = nothing wrong, a slice-mode
        # replay that exited nonzero because it sampled nothing, of a slice whose cells above the slice level have no
        # parent; anything else FAIL (G5 round 3: a PASS label over a seed that differs, and an EMPTY label over a
        # slice holding 734 graphs of (12,20), were accepted)
        # LOCAL BY DESIGN: the verdict from this replay's own records; its EMPTY is only a candidate here (local
        # evidence can refute emptiness, never confirm it), decided in the fleet pass with the merged evidence
        derived = g4_verdict(fp, sm, slice_cfg, d, parent_evidence, shares)
        empty_candidate = None
        if derived[0] in ("EMPTY", "PENDING") and fp.get("result") == "EMPTY" and slice_cfg:
            empty_candidate = True
        elif derived[0] not in ("PASS", "EMPTY") or fp.get("result") != derived[0]:
            local.append(f"G4 replay says {fp.get('result')!r} but its evidence gives {derived[0]}: "
                         f"{'; '.join(derived[1]) or 'no fault found'} (its reasons {fp.get('reasons')})")
        rows: list[tuple[tuple, int]] = []              # (cell, parents_in_cell), counts only: bound in the fleet pass
        slice_stages: dict[str, list[dict]] = {}        # a slice file's G4 stage records: bound in the fleet pass
        if not sm:
            local.append("no G4 replay/summary.json")
        else:
            stages = sm.get("stages") if isinstance(sm.get("stages"), list) else []
            run_dirs = sm.get("run_dirs") if isinstance(sm.get("run_dirs"), list) else []
            # LOCAL BY DESIGN: which run the replay read is a fact of this copy
            if tag and (not run_dirs or any(not str(x).endswith(f"-{tag}") for x in run_dirs)):
                local.append(f"G4 replay of {run_dirs}, not of slice {tag}")
            for row in sm.get("per_cell") if isinstance(sm.get("per_cell"), list) else []:
                cell = tuple(int(x) for x in str(row.get("cell", "")).split("-")) if \
                    re.fullmatch(r"\d+-\d+", str(row.get("cell", ""))) else None
                # LOCAL BY DESIGN: facts of the replay row itself (a required cell, no prefix cell in a slice-mode
                # replay, its parent and sample counts nonnegative integers, no more sampled than the row's own parent
                # count)
                if cell is None or cell not in d["required"]:
                    local.append(f"G4 per_cell row of {row.get('cell')!r}, not a required cell")
                    continue
                if fp.get("mode") == "slice" and slice_cfg and cell[0] <= slice_cfg[0]:
                    local.append(f"G4 slice-mode replay of the prefix cell {cell}")
                # both counts are checked before either comparison: a float or boolean parent count skipped the bound
                # and then equalled the accepted record in the binding (31127.0 == 31127, True == 1; G5 round 8: 31,128
                # samples of (11,17)'s 31,127 parents passed). Such a row is neither bounded nor bound
                if not (nonneg(row.get("parents_in_cell")) and nonneg(row.get("sampled"))):
                    local.append(f"G4 per_cell row of {cell}: parents_in_cell {row.get('parents_in_cell')!r} and sampled "
                                 f"{row.get('sampled')!r} are not both nonnegative integers")
                    continue
                if row["sampled"] > row["parents_in_cell"]:
                    local.append(f"G4 sampled {row['sampled']} of the {row['parents_in_cell']} parents of {cell}")
                rows.append((cell, row["parents_in_cell"]))
            for st in stages:
                if isinstance(st, dict) and ".slice-" in str(st.get("source")):
                    slice_stages.setdefault(str(st["source"]), []).append(st)
        g4 = {"result": fp.get("result"), "mode": fp.get("mode"), "prefix_fingerprint": fp.get("prefix_fingerprint"),
              "fingerprint": fp.get("fingerprint"), "empty_candidate": empty_candidate, "rows": rows,
              "slice_stages": slice_stages}
    elif "g4" in a.require:
        local.append("no G4 replay (replay/fingerprint.json)")
    problems.extend(f"{run.name}: {p}" for p in local)
    unresolved.extend(f"{run.name}: {u}" for u in local_unresolved)
    return {"d": d, "entries": entries, "shares": shares, "stage_count": stage_count, "config": config,
            "slice": slice_cfg, "recovered": dict(recovered), "fresh_cells": fresh_cells, "resumed_cells": resumed_cells,
            "parent_evidence": parent_evidence, "files": files, "g4": g4, "run": run}


def levels_of(cells: set) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for n, _ in cells:
        counts[n] += 1
    return dict(sorted(counts.items()))


def main_summary_only(a: argparse.Namespace) -> int:
    problems: list[str] = []
    unresolved: list[str] = []
    audits = []
    for run in a.run:
        run = run.resolve()
        try:
            audits.append(summary_audit(run, a, problems, unresolved))
        except (Bad, OSError, KeyError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as error:
            problems.append(f"{run.name}: could not be audited: {error!r}")
    report: dict = {"mode": "summary-only", "runs": len(a.run), "audited": len(audits),
                    "pinned": {k: v for k, v in a.pins.items() if v is not None}, "required": sorted(a.require)}
    common = Path(os.path.commonpath([str(x["run"]) for x in audits])) if len(audits) > 1 else None

    def label(x: dict) -> str:
        """A run's path below the audited runs' common directory, first and last parts (its worker and slice, in a
        fleet's results)."""
        if common is None:
            return x["run"].name
        parts = x["run"].relative_to(common).parts
        return "/".join(parts) if len(parts) <= 2 else f"{parts[0]}/{parts[-1]}"
    fleets: dict = defaultdict(list)
    for x in audits:
        cfg = dict(x["config"])
        s = cfg.pop("slice", None)
        key = json.dumps({**cfg, "slice_level": s[0] if x["slice"] else None, "slice_count": s[2] if x["slice"] else None},
                         sort_keys=True)
        fleets[key].append(x)
    if a.pins.get("slices") is not None and len(fleets) > 1:
        problems.append(f"the runs form {len(fleets)} different configurations, not one pinned fleet")
    for key, members in fleets.items():
        cfg = json.loads(key)
        d0 = members[0]["d"]
        tn, tm = d0["target"]
        if cfg["slice_count"] is None:
            # LOCAL BY DESIGN: the audit pairs copies only by slice, and an unsliced run shares no prefix, so its rows are
            # bound to its own accepted records; a row without one stays UNRESOLVED
            for x in members:
                for cell, parents_in_cell in (x["g4"] or {}).get("rows", []):
                    record = x["parent_evidence"].get(cell)
                    if record is None:
                        unresolved.append(f"{label(x)}: G4 replayed {cell} with {parents_in_cell} parents, and the run "
                                          f"records no parents for it")
                    elif record.get("parents") != parents_in_cell:
                        problems.append(f"{label(x)}: G4 replayed {cell} with {parents_in_cell} parents, the accepted "
                                        f"record says {record.get('parents')}")
            continue
        level, count = cfg["slice_level"], cfg["slice_count"]
        by_index: dict = defaultdict(list)
        for x in members:
            by_index[x["slice"][1]].append(x)
        missing = [i for i in range(count) if i not in by_index]
        fleet = {"target": [tn, tm], "slice_level": level, "slice_count": count, "summaries": len(members),
                 "slice_indices": len(by_index), "missing_slices": len(missing)}
        if missing:
            problems.append(f"fleet ({tn},{tm}) sliced {count} ways at level {level}: {len(missing)} slices have no "
                            f"summary ({missing[:20]}{' ...' if len(missing) > 20 else ''})")
        prefix_cells = [c for c in d0["required"] if c[0] <= level]

        def counts_of(x: dict, cell: tuple) -> tuple:
            e = x["entries"].get(cell) or {}
            return (e.get("children"), (e.get("reach") or {}).get("kept"),
                    ((e.get("prune") or {}).get("counts") or {}).get("kept"))
        reference = members[0]
        # the shared prefix: its files' hashes (hashes.json) identical in every slice and on every worker (each
        # worker computes it independently, so this is also a determinism check), and its counts
        hashed = [x for x in members if x["files"] is not None]
        prefix_names = sorted({name for x in hashed for name in x["files"]
                               if name.split("-")[0].isdigit() and int(name.split("-")[0]) <= level})
        differing = []
        for name in prefix_names:
            values = defaultdict(list)
            for x in hashed:
                values[(x["files"].get(name) or {}).get("sha256")].append(label(x))
            if len(values) > 1:
                differing.append((name, {str(k)[:12]: v[:3] + (["..."] if len(v) > 3 else []) for k, v in values.items()}))
        fleet["prefix_files_hashed"] = len(prefix_names)
        fleet["prefix_files_identical_in"] = len(hashed)
        if differing:
            problems.append(f"fleet ({tn},{tm}): {len(differing)} prefix files differ between slices or workers, "
                            f"e.g. {differing[:3]}")
        differing_counts = sorted({c for x in members for c in prefix_cells if counts_of(x, c) != counts_of(reference, c)})
        if differing_counts:
            problems.append(f"fleet ({tn},{tm}): the shared prefix cells {[list(c) for c in differing_counts[:8]]} have "
                            f"different counts in different slice summaries")
        # MERGED EVIDENCE. Every binding of a replay (or of emptiness) to a cell's parent record is made here, against
        # the records every copy accepted: for a cell above the slice level, the accepted records of all copies of its
        # slice; for a prefix cell, the accepted records of every slice (the prefix is the same in all of them). Records
        # that disagree fail; a binding with no record anywhere stays UNRESOLVED (G5 round 7: a copy that resumed the
        # cell escaped the check although another copy recorded it).
        def evidence_key(record: dict) -> tuple:
            return (record.get("parents"),
                    tuple(s.get("records") for s in record.get("parent_sources") or [] if isinstance(s, dict)))
        prefix_evidence: dict = {}
        for x in members:
            for cell, record in sorted(x["parent_evidence"].items()):
                if cell[0] <= level:
                    key_ = evidence_key(record)
                    if cell in prefix_evidence and prefix_evidence[cell] != key_:
                        problems.append(f"fleet ({tn},{tm}): slices record different parents for the prefix cell "
                                        f"{cell}: {prefix_evidence[cell]} and {key_} ({label(x)})")
                    prefix_evidence.setdefault(cell, key_)
        merged: dict[int, dict[int, int]] = {}
        for i, xs in sorted(by_index.items()):
            slice_evidence: dict = {}
            shares_i: dict[int, int] = {}
            for x in xs:
                for cell, record in sorted(x["parent_evidence"].items()):
                    if cell[0] > level:
                        key_ = evidence_key(record)
                        if cell in slice_evidence and slice_evidence[cell] != key_:
                            problems.append(f"fleet ({tn},{tm}): the copies of slice {i} record different parents for "
                                            f"{cell}: {slice_evidence[cell]} and {key_} ({label(x)})")
                        slice_evidence.setdefault(cell, key_)
                # each slice's shares, merged over all its copies: two different values for one share contradict
                # deterministic slicing (G5 round 3)
                for pm, share in sorted(x["shares"].items()):
                    if pm in shares_i and shares_i[pm] != share:
                        problems.append(f"fleet ({tn},{tm}): the copies of slice {i} record different shares of "
                                        f"({level},{pm}): {shares_i[pm]} and {share} ({label(x)})")
                    shares_i.setdefault(pm, share)
            merged[i] = shares_i
            results = sorted({str((x["g4"] or {}).get("result")) for x in xs if x["g4"] is not None})
            if len(results) > 1:
                problems.append(f"fleet ({tn},{tm}): the copies of slice {i} have different G4 results {results}")
            prints_by_mode: dict = defaultdict(set)
            for x in xs:
                if x["g4"] is not None:
                    prints_by_mode[x["g4"].get("mode")].add(x["g4"].get("fingerprint"))
            for mode_, prints_ in sorted(prints_by_mode.items(), key=str):
                if len(prints_) > 1:
                    problems.append(f"fleet ({tn},{tm}): the copies of slice {i} replayed in {mode_} mode read different "
                                    f"runs ({len(prints_)} fingerprints)")
            above = [c for c in d0["required"] if c[0] > level]
            for x in xs:
                g = x["g4"]
                if g is None:
                    continue
                # each replayed cell's parent count is the merged record's
                for cell, parents_in_cell in g["rows"]:
                    ev = prefix_evidence.get(cell) if cell[0] <= level else slice_evidence.get(cell)
                    if ev is None:
                        unresolved.append(f"{label(x)}: G4 replayed {cell} with {parents_in_cell} parents, and no copy "
                                          f"of the slice{' nor any slice' if cell[0] <= level else ''} records its parents")
                    elif ev[0] != parents_in_cell:
                        problems.append(f"{label(x)}: G4 replayed {cell} with {parents_in_cell} parents, the accepted "
                                        f"records say {ev[0]}")
                # each slice file G4 re-derived is the merged share of it
                for pm, share in sorted(shares_i.items()):
                    name = f"{level}-{pm}.slice-{i}-of-{count}.g6"
                    found = g["slice_stages"].get(name, [])
                    if not found:
                        unresolved.append(f"{label(x)}: G4 re-derived no {name} (the share of ({level},{pm}))")
                    whole = x["stage_count"](level, pm)
                    for st in found:
                        if not (st.get("status") == "re-derived" and st.get("ok") and st.get("slice") == [i, count]
                                and st.get("records") == share and st.get("derived_records") == share
                                and st.get("input_records") == whole):
                            problems.append(f"{label(x)}: G4's {name} ({st.get('status')}, {st.get('records')} records "
                                            f"re-derived as {st.get('derived_records')} from {st.get('input_records')}) "
                                            f"is not the slice's share of {share} records of {whole}")
                # an EMPTY is confirmed only by the merged records: every cell above the slice level recorded, with no
                # parent, and every share 0 (G5 round 6: complementary copies)
                if g.get("empty_candidate"):
                    still = [c for c in above if c not in slice_evidence]
                    with_parents = [c for c in above if c in slice_evidence and slice_evidence[c][0] != 0]
                    nonzero = {pm: v for pm, v in shares_i.items() if v != 0}
                    if still or with_parents or nonzero:
                        problems.append(f"{label(x)}: G4 replay says 'EMPTY' but its evidence gives FAIL: an empty replay "
                                        f"of a slice that is not shown empty with every copy's records: unconfirmed "
                                        f"{[list(c) for c in still[:4]]}, cells with parents "
                                        f"{[list(c) for c in with_parents[:4]]}, shares {nonzero}")
        # each slice's own cells (above the slice level): the parents recorded by at least one copy of the slice
        for i, xs in sorted(by_index.items()):
            own = {c for x in xs for c in x["resumed_cells"] if c[0] > level} - set().union(*(x["fresh_cells"] for x in xs))
            if own:
                unresolved.append(f"slice {i}: {len(own)} resumed cells above the slice level whose parents no copy "
                                  f"of the slice records, nor its pushed history (levels {levels_of(own)})")
        # copies of one slice: the same files (hashes.json) and the same counts
        for i, xs in sorted(by_index.items()):
            for y in xs[1:]:
                if (xs[0]["files"] is not None and y["files"] is not None and xs[0]["files"] != y["files"]) or \
                        {c: counts_of(y, c) for c in d0["required"]} != {c: counts_of(xs[0], c) for c in d0["required"]}:
                    problems.append(f"fleet ({tn},{tm}): the copies of slice {i} ({label(xs[0])}, {label(y)}) differ")
        # the G4 replays' prefix fingerprints (what each replay read of the prefix, with the tools and settings)
        prints = defaultdict(list)
        for x in members:
            if x["g4"] is not None:
                prints[x["g4"].get("prefix_fingerprint")].append(x["slice"][1])
        fleet["g4_results"] = dict(sorted(((r, sum(1 for x in members if (x["g4"] or {}).get("result") == r))
                                           for r in {(x["g4"] or {}).get("result") for x in members}), key=str))
        if len(prints) > 1:
            problems.append(f"fleet ({tn},{tm}): the G4 replays read {len(prints)} different prefixes "
                            f"({ {str(k)[:12]: len(v) for k, v in prints.items()} })")
        # the slices partition each slice-level parent cell: every present slice records its share, every share is
        # at most the cell, and the shares add up to the cell when all slices are present
        parent_cells = sorted({pm for (n, m) in d0["required"] if n == level + 1 for pm in d0["allowed"].get((n, m), [])})
        # (the shares, merged over each slice's copies above)
        partition = {}
        for pm in parent_cells:
            whole = reference["stage_count"](level, pm)
            recorded = {i: merged[i][pm] for i in by_index if pm in merged[i]}
            absent = sorted(i for i in by_index if i not in recorded)
            total = sum(recorded.values())
            partition[pm] = {"stage_file": whole, "slices_recording": len(recorded), "sum": total}
            if absent:
                partition[pm]["present_slices_without_a_share"] = absent[:20]
                unresolved.append(f"fleet ({tn},{tm}): slices {absent[:20]}{' ...' if len(absent) > 20 else ''} record "
                                  f"no share of ({level},{pm})")
            if whole is None or total > whole or (len(recorded) == count and total != whole):
                problems.append(f"fleet ({tn},{tm}): the {len(recorded)} recorded shares of ({level},{pm}) add up to "
                                f"{total}, the cell holds {whole}")
        fleet["slice_partition"] = partition
        # the shared prefix's parent choices: recorded fresh by at least one summary (or its history)
        fresh_prefix = set().union(*(x["fresh_cells"] for x in members))
        unrecorded = [c for c in prefix_cells if c[0] > d0["seed_n"] and c not in fresh_prefix]
        fleet["prefix_cells"] = len([c for c in prefix_cells if c[0] > d0["seed_n"]])
        fleet["prefix_cells_with_parents_recorded"] = fleet["prefix_cells"] - len(unrecorded)
        if unrecorded:
            unresolved.append(f"fleet ({tn},{tm}): the parents of the prefix cells {[list(c) for c in unrecorded]} "
                              f"are recorded by no slice summary nor its pushed history")
        fleet["cells_recovered_from_history"] = sum(sum(x["recovered"].values()) for x in members)
        target_cell = (tn, tm)
        firsts = [xs[0] for xs in by_index.values()]
        fleet["target_cell"] = {
            "children": sum(counts_of(x, target_cell)[0] or 0 for x in firsts),
            "kept": sum((counts_of(x, target_cell)[2] or 0) for x in firsts),
            "slices_with_children": sorted(x["slice"][1] for x in firsts if (counts_of(x, target_cell)[0] or 0) > 0)}
        report.setdefault("fleets", []).append(fleet)
    report["problems"], report["unresolved"] = len(problems), len(unresolved)
    print(json.dumps(report))
    for u in unresolved:
        print("UNRESOLVED:", u)
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        print(f"COVERAGE (summary only) FAIL ({len(problems)} problems, {len(unresolved)} unresolved)")
        print(f"CHAIN FAIL ({len(problems)} problems)")
        return 1
    if unresolved:
        print(f"COVERAGE (summary only) UNRESOLVED ({len(unresolved)}): the summaries contradict nothing, but they do "
              f"not record everything coverage needs")
        print(f"CHAIN PARTIAL (summary only; coverage unresolved in {len(unresolved)} places)")
        return 4
    print("COVERAGE (summary only) OK: every run's required cells are listed and recorded with the parents L4 allows, "
          "every count is consistent, and every fleet's slices are all present with their shares")
    print("CHAIN PARTIAL (summary only: no level, keep, parent or certificate file was read)")
    return 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, nargs="+")
    ap.add_argument("--check", action="store_true", help="replay every certs file with udcheck.py")
    ap.add_argument("--from-n", type=int, default=0, help="only inspect levels with n >= this (a PARTIAL check)")
    ap.add_argument("--udcheck-rhombus", type=Path, default=ROOT / "check" / "udcheck_rhombus.py",
                    help="the checker of a rhombus run's certs files (default check/udcheck_rhombus.py)")
    ap.add_argument("--summary-only", action="store_true",
                    help="coverage audit of pushed run-summary.json, run-config.json and reach.json only")
    ap.add_argument("--expect-target", type=int, nargs=2, metavar=("N", "M"),
                    help="the target the run (every run) must have")
    ap.add_argument("--expect-seed", type=int, metavar="S", help="the seed level the run (every run) must have")
    ap.add_argument("--expect-slices", type=int, nargs=2, metavar=("LEVEL", "COUNT"),
                    help="the slicing the run (every run of the fleet) must have: every index 0..COUNT-1")
    ap.add_argument("--require-hashes", action="store_true",
                    help="--summary-only: every run must have the runbook's hashes.json")
    ap.add_argument("--require-g4", action="store_true",
                    help="--summary-only: every run must have the runbook's G4 replay (replay/fingerprint.json)")
    a = ap.parse_args()
    a.pins = {"target": a.expect_target, "seed": a.expect_seed, "slices": a.expect_slices}
    a.require = {name for name, on in (("hashes", a.require_hashes), ("g4", a.require_g4)) if on}
    if a.summary_only:
        if a.check or a.from_n:
            ap.error("--summary-only reads no files to replay or skip")
        return main_summary_only(a)
    if a.require:
        ap.error("--require-hashes and --require-g4 apply to --summary-only")
    if len(a.run) != 1:
        ap.error("one run directory (several only with --summary-only)")
    return main_run(a)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Bad, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"verify-chain.py: {error!r}", file=sys.stderr)
        sys.exit(2)
