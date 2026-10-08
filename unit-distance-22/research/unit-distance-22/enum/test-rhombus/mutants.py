#!/usr/bin/env python3
"""Red controls: four compile-time mutants of filter/udrhombus.c must be caught.

  -DRHOMBUS_MUTANT=1  3-edge paths u-v-w-x (xu not required) taken as 4-cycles
  -DRHOMBUS_MUTANT=2  the distinct-vertex test dropped: [u, v, w, v] taken as a 4-cycle
  -DRHOMBUS_MUTANT=3  sign flip in R2: target s (e_a - e_b + e_p - e_q) with the edge reported as [p, q]
  -DRHOMBUS_MUTANT=4  wrong pairing in Lemma R: r(C) = e_u + e_v - e_w - e_x
A mutant's self-check shares its mutated notion, so it writes its wrong certificates (as a prover
with that misunderstanding would).

Positive controls: AMP's 56 known densest graphs (every flag there is false: they are the full
unit-distance graphs of their point sets) and GP-10's 32,653 embedded B10 graphs (a refutation there
is false; a tu is false unless the correct prover finds a forced pair in the same graph).

PASS iff for EVERY mutant
  M1 it flags at least one positive-control graph;
  M2 the dev replay rejects every certificate it writes on a false flag (all known56 flags, every
     B10 refutation, every B10 tu on a graph the correct prover passes), and for mutants 1, 2 and 4
     there is at least one false flag;
  M3 for the sign-flip mutant 3, the dev replay rejects EVERY certificate it writes (they all carry
     the wrong sign), and there is at least one;
  M4 the verdict comparison of agreement.py is sensitive: on the level-15 and level-17 samples the
     mutant's verdict classes differ from the correct prover's on at least one graph (mutants 1, 2, 4;
     mutant 3 only moves signs, so its classes may agree);
  M5 prune.py refuses to run a mutant build (its statistics line names the mutant).
  M6 the fallback (SPEC amendment 2, silent passes counted): -DRHOMBUS_MUTANT=5 corrupts every solved
     certificate before the self-check; it must write pass for every graph and count exactly the
     correct prover's detections as certificate_failures (all of kind self_check).

usage: mutants.py
"""
from __future__ import annotations

import collections
import gzip
import json
import subprocess
import sys

from rhlib import FILTER, HERE, REPO, UD, g6_lines, known_graphs, log, replay, run_prover

BIN = HERE / "bin"
RECORDS = REPO / "research" / "gp-10" / "cloud" / "lean3" / "records.jsonl.gz"


def build(k: int):
    BIN.mkdir(exist_ok=True)
    out = BIN / f"udrhombus-mutant-{k}"
    subprocess.run(["cc", "-std=c17", "-O3", "-Wall", "-Wextra", "-Wpedantic", f"-DRHOMBUS_MUTANT={k}", "-o", str(out),
                    str(FILTER / "udrhombus.c")], check=True)
    return out


def main() -> int:
    problems: list[str] = []
    known = known_graphs()
    with gzip.open(RECORDS, "rt") as f:
        b10 = [r["g6"] for r in map(json.loads, f) if r["verdict"] == "embedded"]
    correct_b10, _, _ = run_prover(b10)
    correct_flag = [r["verdict"] != "pass" for r in correct_b10]
    samples = [HERE / "samples" / "w1-measure-15.g6", HERE / "samples" / "w1-measure-17.g6"]
    sample_lines = [g for s in samples for g in g6_lines(s)]
    correct_samples, _, _ = run_prover(sample_lines)
    log(f"positive controls: {len(known)} known graphs, {len(b10)} embedded B10 graphs (correct prover flags "
        f"{sum(correct_flag)} of them, all tu); agreement samples {len(sample_lines)} graphs")
    for k in (1, 2, 3, 4):
        binary = build(k)
        kr, kstats, _ = run_prover(known, binary)
        br, bstats, _ = run_prover(b10, binary)
        if kstats.get("mutant") != k:
            problems.append(f"mutant {k}: the build does not report itself as mutant {k}")
        flags = collections.Counter()
        false_flags = accepted_false = 0
        accepted_all = rejected_all = 0
        example = None
        for code, r, cflag in [(c, r, False) for c, r in zip(known, kr)] + list(zip(b10, br, correct_flag)):
            if r["verdict"] == "pass":
                continue
            flags[r["verdict"]] += 1
            ok, why = replay(code, r)
            accepted_all += ok
            rejected_all += not ok
            false = r["verdict"] == "refuted" or not cflag
            if false:
                false_flags += 1
                accepted_false += ok
                if example is None:
                    example = (code, r["verdict"], why)
        known_flags = sum(1 for r in kr if r["verdict"] != "pass")
        log(f"mutant {k}: flags {known_flags} of {len(known)} known graphs and "
            f"{sum(1 for r in br if r['verdict'] != 'pass')} of {len(b10)} B10 graphs ({dict(flags)}); false flags "
            f"{false_flags}, of which the dev replay accepts {accepted_false}; all certificates: accepted {accepted_all}, "
            f"rejected {rejected_all}; certificate failures {kstats.get('certificate_failures', 0) + bstats.get('certificate_failures', 0)}")
        if example:
            log(f"   e.g. {example[0]} ({example[1]}): {example[2][:150]}")
        if not flags:
            problems.append(f"M1 mutant {k}: flags no positive-control graph")
        if accepted_false:
            problems.append(f"M2 mutant {k}: the dev replay accepted {accepted_false} certificates of false flags")
        if k in (1, 2, 4) and not false_flags:
            problems.append(f"M2 mutant {k}: no false flag on the positive controls")
        if k == 3 and (accepted_all or not rejected_all):
            problems.append(f"M3 mutant 3: accepted {accepted_all}, rejected {rejected_all} (all must be rejected)")
        mr, _, _ = run_prover(sample_lines, binary)
        differ = sum(1 for a, b in zip(mr, correct_samples) if a["verdict"] != b["verdict"])
        log(f"   agreement-style comparison on {len(sample_lines)} sample graphs: verdict classes differ on {differ}")
        if k in (1, 2, 4) and not differ:
            problems.append(f"M4 mutant {k}: the verdict comparison does not see it")
        # M5: prune.py must refuse the build
        work = HERE / "scratch" / f"mutant-{k}"
        work.mkdir(parents=True, exist_ok=True)
        level = work / "17-43.g6"
        level.write_text(g6_lines(UD / "enum" / "out-prune" / "dag-17-43-prune16" / "17-43.g6")[0] + "\n")
        p = subprocess.run([sys.executable, str(UD / "enum" / "prune.py"), "--level", str(level), "--target-n", "17",
                            "--target-m", "43", "--filter-only", "--rhombus", "--udrhombus", str(binary), "--overwrite"],
                           capture_output=True, text=True)
        refused = p.returncode == 2 and "red-control build" in p.stderr
        log(f"   prune.py --rhombus --udrhombus <mutant {k}>: exit {p.returncode}: {p.stderr.strip()[-110:]}")
        if not refused:
            problems.append(f"M5 mutant {k}: prune.py did not refuse the mutant build")
    # M6: the fallback of a failed self-check is a counted pass
    binary = build(5)
    correct_known, _, _ = run_prover(known)
    for label, inputs, correct in (("known56", known, correct_known), ("B10", b10, correct_b10)):
        recs, stats, _ = run_prover(inputs, binary)
        detections = sum(1 for r in correct if r["verdict"] != "pass")
        flagged = sum(1 for r in recs if r["verdict"] != "pass")
        log(f"mutant 5 on {label}: flags {flagged}; certificate_failures {stats.get('certificate_failures')} "
            f"(self_check {stats.get('failure_self_check')}); the correct prover's detections {detections}")
        if flagged or stats.get("certificate_failures") != detections or stats.get("failure_self_check") != detections:
            problems.append(f"M6 mutant 5 on {label}: the fallback is not a counted pass")
    for p in problems:
        log("PROBLEM:", p)
    log("MUTANTS", "PASS" if not problems else f"FAIL ({len(problems)})")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
