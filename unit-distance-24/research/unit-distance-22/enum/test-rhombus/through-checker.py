#!/usr/bin/env python3
"""The binding controls of RHOMBUS-SPEC.md amendment 2, run THROUGH A CHECKER (not the prover's counts).

Certificate files in the checker's schema are assembled from udrhombus's output, one file per (n, m)
(the checker contract names --expect-n and --expect-m), with canonical graph6 (nauty-labelg; the prover
runs on the canonical form), a pass written as "unknown" and listed in the file's UNKNOWN list, and the
checker's command line of prune.py:
    <python> <checker> --expect-n n --expect-m m --graphs LIST --unknown-file UNKNOWN --data-dir DATA
                       --forbidden-set 74 CERTS
PASS iff
  T1 AMP's 56 known densest graphs: every file ACCEPTED, and no graph flagged at all (tu = refuted = 0,
     rhombus_tu = rhombus_refuted = 0, unknown = all of them);
  T2 GP-10's 32,653 embedded B10 graphs: every file ACCEPTED, refuted = rhombus_refuted = 0, and
     rhombus_tu = the prover's tu count (9,712; b10.py follows every one of them through GP-10's exact
     embedding to a unit distance);
  T3 red: for each compile-time mutant 1 to 4 (mutants.py builds them in bin/), certificate files holding
     only its FALSE flags (every flag on the 56, every B10 refutation, every B10 tu on a graph the
     correct prover passes; for the sign-flip mutant 3 all its flags, whose certificates all carry the
     wrong sign) are REJECTED, both grouped and one record per file for a sample of up to 25 records;
  T4 red: an "int64 checker" certificate (amendment 2): K2,3's true certificate plus four copies of one
     more cycle with coefficients 2^62 - 1 and one with 4, which adds 2^64 r(C) (a sum that exceeds 2^63:
     wrong in exact integers, right modulo 2^64) must be REJECTED;
  T5 red: a repeated vertex in a cycle (mutant 2's first false certificate) is REJECTED on its own.
  T6 every certificate the prover writes on the (23,65) descent samples (samples/*.g6: w1, w2, w3 at
     levels 13 to 18 and w1 at 19) is ACCEPTED, and the checker's rhombus_tu and rhombus_refuted equal
     the prover's counts;
  T7 K2,3 and the six TU gadgets, in canonical form: ACCEPTED, K2,3 as refuted and every gadget as tu;
  T8 red: the tampered certificates of units.py U6, made on canonical K2,3 and gadget 0, are each
     REJECTED on their own (the checker's reason is logged).

usage: through-checker.py [--checker PATH]    default: check/udcheck_rhombus.py if it exists, else the
                                              DEV REPLAY dev_replay_rhombus.py (and the output says so)
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

from rhlib import DATA, HERE, REPO, SCRATCH, UD, canonical, decode_g6, encode_g6, known_graphs, log, run_prover

MATHS_PY = Path.home() / "tools" / "pyenv-maths" / "bin" / "python"
RECORDS = REPO / "research" / "gp-10" / "cloud" / "lean3" / "records.jsonl.gz"
WORK = SCRATCH / "through-checker"
problems: list[str] = []


def checker_run(checker: Path, n: int, m: int, records: list[dict], tag: str) -> tuple[bool, dict, str]:
    d = WORK / tag
    d.mkdir(parents=True, exist_ok=True)
    certs, graphs, unknown = d / f"{n}-{m}.certs.jsonl", d / f"{n}-{m}.g6", d / f"{n}-{m}.UNKNOWN.g6"
    certs.write_text("".join(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n" for r in records))
    graphs.write_text("".join(r["g6"] + "\n" for r in records))
    unknown.write_text("".join(r["g6"] + "\n" for r in records if r["verdict"] == "unknown"))
    cmd = ["nice", "-n", "10", str(MATHS_PY), str(checker), "--expect-n", str(n), "--expect-m", str(m),
           "--graphs", str(graphs), "--unknown-file", str(unknown), "--data-dir", str(DATA),
           "--forbidden-set", "74", str(certs)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    accept = [x for x in p.stdout.splitlines() if x.startswith("ACCEPT certificates")]
    counts = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", accept[0])} if accept else {}
    return p.returncode == 0 and len(accept) == 1, counts, p.stderr.strip()[-200:]


def records_for(codes: list[str], outs: list[dict]) -> list[dict]:
    recs = []
    for code, r in zip(codes, outs):
        recs.append({"g6": code, "verdict": "unknown"} if r["verdict"] == "pass" else
                    {"g6": code, "verdict": r["verdict"], "witness": r["witness"]})
    return recs


def by_size(recs: list[dict]) -> dict:
    groups = collections.defaultdict(list)
    for r in recs:
        n, edges = decode_g6(r["g6"])
        groups[(n, len(edges))].append(r)
    return groups


def run_groups(checker: Path, recs: list[dict], tag: str) -> tuple[int, int, dict]:
    accepted = rejected = 0
    total = collections.Counter()
    for (n, m), group in sorted(by_size(recs).items()):
        ok, counts, why = checker_run(checker, n, m, group, f"{tag}/{n}-{m}")
        accepted += ok
        rejected += not ok
        total.update(counts)
    return accepted, rejected, dict(total)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checker", type=Path, default=None)
    a = ap.parse_args()
    real = UD / "check" / "udcheck_rhombus.py"
    checker = a.checker or (real if real.is_file() else HERE / "dev_replay_rhombus.py")
    log(f"checker: {checker}{'  (THE DEV REPLAY, not check/udcheck_rhombus.py)' if checker.name == 'dev_replay_rhombus.py' else ''}")
    shutil.rmtree(WORK, ignore_errors=True)

    # T1
    known = [g for g in canonical(known_graphs()) if decode_g6(g)[0] >= 1]
    kout, _, _ = run_prover(known)
    krecs = records_for(known, kout)
    acc, rej, total = run_groups(checker, krecs, "t1")
    flagged = sum(1 for r in krecs if r["verdict"] != "unknown")
    log(f"T1 {len(known)} known graphs (canonical, order >= 1) in {acc + rej} files: accepted {acc}, rejected {rej}; "
        f"prover flags {flagged}; checker totals {total}")
    if rej or flagged or total.get("tu") or total.get("refuted") or total.get("rhombus_tu") or \
            total.get("rhombus_refuted") or total.get("unknown") != len(known):
        problems.append("T1: the known graphs are not all accepted as unflagged")

    # T2
    with gzip.open(RECORDS, "rt") as f:
        b10 = [r["g6"] for r in map(json.loads, f) if r["verdict"] == "embedded"]
    if canonical(b10) != b10:
        problems.append("T2: the B10 graph6 strings are not canonical")
    bout, bstats, _ = run_prover(b10)
    brecs = records_for(b10, bout)
    acc, rej, total = run_groups(checker, brecs, "t2")
    log(f"T2 {len(b10)} embedded B10 graphs in {acc + rej} files: accepted {acc}, rejected {rej}; prover tu "
        f"{bstats.get('tu')}, refuted {bstats.get('refuted')}; checker totals {total}")
    if rej or total.get("refuted") or total.get("rhombus_refuted") or total.get("rhombus_tu") != bstats.get("tu"):
        problems.append("T2: the B10 certificates are not accepted exactly as the prover counts them")

    # T3
    correct_b10 = {code: r["verdict"] for code, r in zip(b10, bout)}
    rng = random.Random(20260926)
    first_repeated = None
    for k in (1, 2, 3, 4):
        binary = HERE / "bin" / f"udrhombus-mutant-{k}"
        if not binary.is_file():
            problems.append(f"T3: {binary} missing (run mutants.py first)")
            continue
        mk, _, _ = run_prover(known, binary)
        mb, _, _ = run_prover(b10, binary)
        false = [r for r in records_for(known, mk) if r["verdict"] != "unknown"]
        false += [r for r in records_for(b10, mb) if r["verdict"] == "refuted" or
                  (r["verdict"] == "tu" and (k == 3 or correct_b10[r["g6"]] == "pass"))]
        acc, rej, _ = run_groups(checker, false, f"t3-{k}")
        sample = rng.sample(false, min(25, len(false)))
        single_rej = 0
        for i, r in enumerate(sample):
            n, edges = decode_g6(r["g6"])
            ok, _, _ = checker_run(checker, n, len(edges), [r], f"t3-{k}-single/{i}")
            single_rej += not ok
        if k == 2 and false:
            first_repeated = false[0]
        log(f"T3 mutant {k}: {len(false)} false flags in {acc + rej} files: rejected {rej}, accepted {acc}; "
            f"one record per file: {single_rej} of {len(sample)} rejected")
        if acc or single_rej != len(sample) or not false:
            problems.append(f"T3 mutant {k}: a false-flag certificate file was accepted")

    # T4
    k23 = canonical([encode_g6(5, [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)])])[0]
    (r,), _, _ = run_prover([k23])
    rh = r["witness"]["rhombus"]
    n, edges = decode_g6(k23)
    adj = {v: {u for e in edges for u in e if v in e and u != v} for v in range(n)}
    extra = next([u, v, w, x] for u in range(n) for w in range(u + 1, n) for v in sorted(adj[u] & adj[w])
                 for x in sorted(adj[u] & adj[w]) if v < x)
    wrapped = {"cycles": rh["cycles"] + [extra] * 5,
               "coefficients": rh["coefficients"] + [2 ** 62 - 1] * 4 + [4],
               "scale": rh["scale"], "pair": rh["pair"]}
    ok, _, why = checker_run(checker, n, len(edges), [{"g6": k23, "verdict": "refuted", "witness": {"rhombus": wrapped}}],
                             "t4")
    log(f"T4 the int64-wrap certificate for K2,3 (sum exceeds 2^63; equal to the target modulo 2^64): "
        f"{'ACCEPTED (bug)' if ok else 'rejected: ' + why[-150:]}")
    if ok:
        problems.append("T4: the int64-wrap certificate was accepted")

    # T5
    if first_repeated is not None:
        n, edges = decode_g6(first_repeated["g6"])
        ok, _, why = checker_run(checker, n, len(edges), [first_repeated], "t5")
        log(f"T5 a repeated vertex in a cycle (mutant 2, {first_repeated['g6']}): "
            f"{'ACCEPTED (bug)' if ok else 'rejected: ' + why[-150:]}")
        if ok:
            problems.append("T5: a repeated-vertex certificate was accepted")
    # T6
    samples = sorted((HERE / "samples").glob("*.g6"))
    codes = [g for f in samples for g in f.read_text().split("\n") if g]
    if canonical(codes) != codes:
        problems.append("T6: the descent samples are not in canonical form")
    sout, sstats, _ = run_prover(codes)
    acc, rej, total = run_groups(checker, records_for(codes, sout), "t6")
    log(f"T6 {len(codes)} descent sample graphs ({len(samples)} files) in {acc + rej} checker files: accepted {acc}, "
        f"rejected {rej}; prover tu {sstats.get('tu')} refuted {sstats.get('refuted')}; checker totals {total}")
    if rej or total.get("rhombus_tu") != sstats.get("tu") or total.get("rhombus_refuted") != sstats.get("refuted"):
        problems.append("T6: the descent-sample certificates are not all accepted with the prover's counts")

    # T7
    from rhlib import gadgets
    small = canonical([k23] + [encode_g6(g["n"], g["edges"]) for g in gadgets()])
    tout, _, _ = run_prover(small)
    verdicts = []
    for code, r in zip(small, tout):
        n, edges = decode_g6(code)
        rec = records_for([code], [r])[0]
        ok, counts, why = checker_run(checker, n, len(edges), [rec], f"t7/{len(verdicts)}")
        verdicts.append((r["verdict"], ok))
    log(f"T7 K2,3 and the six gadgets (canonical): prover/checker {verdicts}")
    if verdicts[0] != ("refuted", True) or any(v != ("tu", True) for v in verdicts[1:]):
        problems.append("T7: K2,3 or a gadget is not accepted with the expected verdict")

    # T8
    import copy
    k_code, g_code = small[0], small[1]
    k_rec, g_rec = records_for([k_code], [tout[0]])[0], records_for([g_code], [tout[1]])[0]
    g_edges = decode_g6(g_code)[1]

    def tampered(rec, fn):
        bad = copy.deepcopy(rec)
        fn(bad, bad["witness"]["rhombus"])
        return bad
    non_edge = next([u, v] for u in range(7) for v in range(u + 1, 7) if (u, v) not in g_edges)
    cases = [
        ("coefficient changed", k_rec, lambda r, w: w["coefficients"].__setitem__(0, w["coefficients"][0] + 2)),
        ("scale doubled", k_rec, lambda r, w: w.__setitem__("scale", 2 * w["scale"])),
        ("float coefficient", k_rec, lambda r, w: w["coefficients"].__setitem__(0, float(w["coefficients"][0]))),
        ("boolean coefficient", k_rec, lambda r, w: w["coefficients"].__setitem__(1, True)),
        ("extra key", k_rec, lambda r, w: w.__setitem__("note", 1)),
        ("pair reversed", k_rec, lambda r, w: w.__setitem__("pair", w["pair"][::-1])),
        ("repeated vertex", k_rec, lambda r, w: w["cycles"][0].__setitem__(2, w["cycles"][0][0])),
        ("verdict tu without edge", k_rec, lambda r, w: r.__setitem__("verdict", "tu")),
        ("coefficient 0", k_rec, lambda r, w: w["coefficients"].__setitem__(0, 0)),
        ("coefficient 2^62", k_rec, lambda r, w: w["coefficients"].__setitem__(0, 2 ** 62)),
        ("edge reversed", g_rec, lambda r, w: w.__setitem__("edge", w["edge"][::-1])),
        ("pair made an edge", g_rec, lambda r, w: w.__setitem__("pair", list(sorted(g_edges)[0]))),
        ("edge made a non-edge", g_rec, lambda r, w: w.__setitem__("edge", non_edge)),
        ("edge key dropped", g_rec, lambda r, w: w.pop("edge")),
        ("verdict refuted with an edge", g_rec, lambda r, w: r.__setitem__("verdict", "refuted")),
        ("witness key tri", g_rec, lambda r, w: r.__setitem__("witness", {"tri": w})),
    ]
    for i, (label, rec, fn) in enumerate(cases):
        bad = tampered(rec, fn)
        n, edges = decode_g6(bad["g6"])
        ok, _, why = checker_run(checker, n, len(edges), [bad], f"t8/{i}")
        log(f"T8 {label}: {'ACCEPTED (bug)' if ok else 'rejected: ' + why[-140:]}")
        if ok:
            problems.append(f"T8: a tampered certificate ({label}) was accepted")

    for p in problems:
        log("PROBLEM:", p)
    log("THROUGH-CHECKER", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
